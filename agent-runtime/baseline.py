"""Read-only fingerprints for the stable files consumed by the current Codex.

Only metadata and digests leave this module. Native sessions, memories, auth,
logs, databases, and plugin caches are deliberately not default scan roots.
Callers may add known, versioned plugin manifests/skills; never pass the whole
Codex home or plugin cache as a substitute for an explicit source inventory.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
from typing import Iterable


SCHEMA_VERSION = 1
EXCLUDED_NAMES = frozenset({
    ".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".cache", ".DS_Store", "node_modules", ".venv", "venv", ".coverage",
})
EXCLUDED_SUFFIXES = (".pyc", ".pyo")


def _logical(path: Path) -> Path:
    # absolute(), unlike resolve(), retains the client-visible symlink path.
    return Path(os.path.abspath(os.path.expanduser(os.fspath(path))))


def default_codex_paths(home: Path, vault: Path) -> list[Path]:
    """Known static sources, including absent paths so later creation is seen.

    Plugins are intentionally caller-supplied: a configured plugin name alone
    does not establish which installed version the running host has loaded.
    The .agents ancestor symlink is recorded by capture without widening the
    scan to unrelated children of that directory.
    """
    home, vault = _logical(home), _logical(vault)
    return [
        home / ".codex/config.toml",
        home / ".codex/hooks.json",
        home / ".codex/AGENTS.md",
        home / ".codex/rules",
        home / ".codex/skywork-high-fidelity-compaction.md",
        home / ".codex/skills",
        home / ".agents/skills",
        home / ".agents/.skill-lock.json",
        home / ".agents/.pluginName-overrides.json",
        home / ".agents/safe-skills-update.sh",
        home / ".agents/openclaw-copy-adapter.py",
        home / ".agents/apply-pluginName-overrides.py",
        home / ".config/brain/config.toml",
        home / ".brain/AGENTS.md",
        home / ".brain/brain.md",
        home / ".brain/tools",
        home / ".zshrc",
        home / ".zprofile",
        vault / "AGENTS.md",
        vault / ".envrc",
        vault / ".agents/skills",
        vault / ".agents/contracts",
        vault / ".agents/tools",
        vault / "brain/brain.md",
    ]


def _excluded(path: Path) -> bool:
    return path.name in EXCLUDED_NAMES or path.name.endswith(EXCLUDED_SUFFIXES)


def _stat_identity(info: os.stat_result) -> tuple[int, ...]:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def _file_digest(path: Path) -> tuple[str, int]:
    with path.open("rb") as stream:
        before = os.fstat(stream.fileno())
        digest = hashlib.sha256()
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
        after = os.fstat(stream.fileno())
    if (_stat_identity(before) != _stat_identity(after)
            or _stat_identity(after) != _stat_identity(path.stat())):
        raise RuntimeError("changed_during_capture")
    return digest.hexdigest(), after.st_size


def capture(paths: Iterable[Path]) -> dict:
    """Fingerprint explicit sources, following symlinks with per-branch guards.

    Missing requested roots are valid observations. Broken links, unreadable
    paths, cycles, and files changing during capture are errors, never silently
    equivalent to an empty/missing source. Directory membership is represented
    by child entries, including empty directories; mtime/inodes are not stored.
    """
    roots = sorted({str(_logical(Path(path))) for path in paths})
    result: dict = {
        "schema_version": SCHEMA_VERSION,
        "roots": roots,
        "entries": {},
        "errors": [],
    }
    entries = result["entries"]
    error_keys: set[tuple[str, str]] = set()
    visited: set[str] = set()

    def error(path: Path, code: str) -> None:
        key = (str(path), code)
        if key not in error_keys:
            result["errors"].append({"path": str(path), "code": code})
            error_keys.add(key)

    def metadata(path: Path) -> tuple[dict, Path | None]:
        record = {
            "type": "missing", "mode": None, "link_target": None,
            "resolved_path": str(path.resolve(strict=False)),
            "sha256": None, "size": None,
        }
        try:
            info = path.lstat()
        except FileNotFoundError:
            return record, None
        record["mode"] = stat.S_IMODE(info.st_mode)
        if stat.S_ISLNK(info.st_mode):
            record["type"] = "symlink"
            record["link_target"] = os.readlink(path)
            try:
                target = path.resolve(strict=True)
                target_info = path.stat()
            except (OSError, RuntimeError):
                error(path, "broken_or_cyclic_symlink")
                record["resolved_path"] = None
                return record, None
            record["resolved_path"] = str(target)
            record["target_mode"] = stat.S_IMODE(target_info.st_mode)
            if stat.S_ISDIR(target_info.st_mode):
                record["target_type"] = "directory"
                return record, target
            if stat.S_ISREG(target_info.st_mode):
                record["target_type"] = "file"
                record["sha256"], record["size"] = _file_digest(path)
            else:
                record["target_type"] = "special"
                error(path, "unsupported_file_type")
        elif stat.S_ISDIR(info.st_mode):
            record["type"] = "directory"
            return record, path.resolve(strict=True)
        elif stat.S_ISREG(info.st_mode):
            record["type"] = "file"
            record["sha256"], record["size"] = _file_digest(path)
        else:
            record["type"] = "special"
            error(path, "unsupported_file_type")
        if _stat_identity(info) != _stat_identity(path.lstat()):
            raise RuntimeError("changed_during_capture")
        return record, None

    def observe(path: Path, ancestors: frozenset[Path], descend: bool = True) -> None:
        key = str(path)
        if descend and key in visited:
            return
        try:
            record, directory = metadata(path)
            entries[key] = record
            if not descend:
                return
            visited.add(key)
            if directory is None:
                return
            if directory in ancestors:
                error(path, "directory_cycle")
                return
            before = _stat_identity(path.stat())
            link_before = path.lstat() if record["type"] == "symlink" else None
            children = sorted((child for child in path.iterdir() if not _excluded(child)),
                              key=lambda item: item.name)
            for child in children:
                observe(child, ancestors | {directory})
            # Directory mtimes can change for ignored runtime files. Validate
            # identity and target only; child content/membership is checked above.
            after = _stat_identity(path.stat())
            names_after = sorted(child.name for child in path.iterdir() if not _excluded(child))
            link_changed = (link_before is not None and (
                _stat_identity(link_before) != _stat_identity(path.lstat())
                or os.readlink(path) != record["link_target"]))
            if (before[:3] != after[:3] or path.resolve(strict=True) != directory
                    or names_after != [child.name for child in children] or link_changed):
                error(path, "changed_during_capture")
        except PermissionError:
            error(path, "permission_denied")
        except FileNotFoundError:
            error(path, "disappeared_during_capture")
        except RuntimeError:
            error(path, "changed_or_cyclic_during_capture")
        except OSError:
            error(path, "read_failed")

    for value in roots:
        root = Path(value)
        # Record parent aliases (e.g. ~/.agents -> dotfiles/.agents) without
        # recursively scanning that parent's unrelated files.
        for parent in reversed(root.parents):
            if parent.is_symlink():
                observe(parent, frozenset(), descend=False)
        observe(root, frozenset())
    result["entries"] = dict(sorted(entries.items()))
    result["errors"] = sorted(result["errors"], key=lambda item: (item["path"], item["code"]))
    return result


def compare(before: dict, after: dict) -> dict:
    """Fail closed on source drift, changed scope, or either capture's errors."""
    errors = []
    for label, snapshot in (("before", before), ("after", after)):
        if snapshot.get("schema_version") != SCHEMA_VERSION:
            errors.append({"snapshot": label, "code": "unsupported_schema"})
        for item in snapshot.get("errors", []):
            errors.append({"snapshot": label, **item})
    if before.get("roots") != after.get("roots"):
        errors.append({"code": "capture_scope_changed"})
    old, new = before.get("entries", {}), after.get("entries", {})
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed = sorted(path for path in set(old) & set(new) if old[path] != new[path])
    return {
        "ok": not (added or removed or changed or errors),
        "added": added, "removed": removed, "changed": changed, "errors": errors,
    }
