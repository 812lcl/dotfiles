"""Render explicitly selected Magpie MCP entries into Claude's user config.

Plans and private manifests can contain credentials. Only the summaries returned
by apply/rollback are suitable for logs. This module never contacts an MCP server.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import uuid


class AdapterError(ValueError):
    """A configuration or ownership check failed; messages omit config values."""


class ConflictError(AdapterError):
    """Existing or concurrently changed data cannot safely be overwritten."""


def _sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _json_bytes(value) -> bytes:
    try:
        return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                           indent=2, allow_nan=False) + "\n").encode()
    except (TypeError, ValueError) as exc:
        raise AdapterError("Configuration must contain JSON-compatible values") from exc


def _entry_sha(value) -> str:
    return _sha(_json_bytes(value))


def _object(blob: bytes) -> dict:
    try:
        value = json.loads(blob)
    except (ValueError, UnicodeError) as exc:
        raise AdapterError("Configuration is not valid JSON") from exc
    if not isinstance(value, dict):
        raise AdapterError("Configuration must be a JSON object")
    return value


def _snapshot(path: Path) -> dict:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return {"exists": False, "bytes": None, "sha256": None, "mode": None}
    if not stat.S_ISREG(info.st_mode):
        raise AdapterError("Configuration must be a regular file, not a symlink")
    # O_NOFOLLOW also refuses a symlink introduced after lstat.
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode):
            raise AdapterError("Configuration must be a regular file")
        blob = stream.read()
    return {"exists": True, "bytes": blob, "sha256": _sha(blob),
            "mode": stat.S_IMODE(opened.st_mode)}


def _same_snapshot(left: dict, right: dict) -> bool:
    return all(left[key] == right[key] for key in ("exists", "sha256", "mode"))


def _servers(config: dict) -> dict:
    value = config.get("mcpServers", {})
    if not isinstance(value, dict):
        raise AdapterError("mcpServers must be a JSON object")
    return value


def _launch_override(server: dict, override: dict) -> dict:
    """Allow a verified local stdio launcher without changing source credentials."""
    required = {"command", "args", "entry_sha256"}
    if not isinstance(override, dict) or set(override) != required:
        raise AdapterError("Launch override requires only command, args, and entry_sha256")
    if server["type"] != "stdio":
        raise AdapterError("Launch overrides are supported only for stdio MCP entries")
    command, args, expected = override["command"], override["args"], override["entry_sha256"]
    if (not isinstance(command, str) or not Path(command).is_absolute()
            or not Path(command).is_file() or not os.access(command, os.X_OK)):
        raise AdapterError("Launch override command must be an existing absolute executable")
    if (not isinstance(args, list) or not args
            or not all(isinstance(arg, str) for arg in args)
            or not Path(args[0]).is_absolute()):
        raise AdapterError("Launch override args must begin with an absolute entry file")
    if (not isinstance(expected, str) or len(expected) != 64
            or any(char not in "0123456789abcdefABCDEF" for char in expected)):
        raise AdapterError("Launch override entry_sha256 must be a SHA-256 digest")
    entry = _snapshot(Path(args[0]))
    if not entry["exists"] or entry["sha256"] != expected.lower():
        raise AdapterError("Launch override entry file is missing or its hash does not match")
    result = copy.deepcopy(server)
    result["command"] = command
    result["args"] = list(args)
    return result


def load_magpie_servers(library: Path, names: list[str], launch_overrides: dict | None = None) -> dict:
    """Read Claude-enabled entries and optional verified, local stdio launchers.

    Overrides affect command/args only. Source env remains intact, and validation
    metadata is not emitted to Claude. The returned dict may contain secrets.
    """
    if not names or len(set(names)) != len(names):
        raise AdapterError("Select one or more distinct MCP names")
    if launch_overrides is None:
        launch_overrides = {}
    if not isinstance(launch_overrides, dict) or any(
            name not in names for name in launch_overrides):
        raise AdapterError("Launch overrides must refer only to selected MCP names")
    data = _object(Path(library).read_bytes())
    entries = data.get("mcp")
    if not isinstance(entries, list):
        raise AdapterError("Magpie library has no MCP list")
    selected = {}
    for name in names:
        matches = [entry for entry in entries
                   if isinstance(entry, dict) and entry.get("name") == name]
        if len(matches) != 1:
            raise AdapterError("Selected MCP name is missing or duplicated")
        entry = matches[0]
        if "claude" not in entry.get("agents", []):
            raise AdapterError("Selected MCP entry is not assigned to Claude")
        transport = entry.get("transport")
        if transport == "stdio":
            command = entry.get("command")
            args, env = entry.get("args", []), entry.get("env", {})
            if not isinstance(command, str) or not command.strip():
                raise AdapterError("stdio MCP requires a command")
            if not isinstance(args, list) or not all(isinstance(v, str) for v in args):
                raise AdapterError("stdio MCP args must be a string list")
            if not isinstance(env, dict) or not all(
                    isinstance(k, str) and isinstance(v, str) for k, v in env.items()):
                raise AdapterError("stdio MCP env must be a string mapping")
            rendered = {"type": "stdio", "command": command}
            for key in ("args", "env"):
                if key in entry:
                    rendered[key] = copy.deepcopy(entry[key])
        elif transport in ("http", "sse"):
            if not isinstance(entry.get("url"), str) or not entry["url"].strip():
                raise AdapterError("Remote MCP requires a URL")
            rendered = {"type": transport, "url": entry["url"]}
            if "headers" in entry:
                headers = entry["headers"]
                if not isinstance(headers, dict) or not all(
                        isinstance(k, str) and isinstance(v, str)
                        for k, v in headers.items()):
                    raise AdapterError("MCP headers must be a string mapping")
                rendered["headers"] = copy.deepcopy(headers)
        else:
            raise AdapterError("Unsupported MCP transport")
        selected[name] = (_launch_override(rendered, launch_overrides[name])
                          if name in launch_overrides else rendered)
    return selected


def plan(config: Path, servers: dict) -> dict:
    """Prepare additions only; same entries are no-ops, conflicts are refused."""
    path = Path(config).expanduser().absolute()
    if not isinstance(servers, dict) or not servers:
        raise AdapterError("Expected one or more MCP entries")
    if not all(isinstance(k, str) and k and isinstance(v, dict)
               for k, v in servers.items()):
        raise AdapterError("MCP entries must map names to objects")
    _json_bytes(servers)
    before = _snapshot(path)
    original = _object(before["bytes"]) if before["exists"] else {}
    existing = _servers(original)
    conflicts = [name for name, entry in servers.items()
                 if name in existing and existing[name] != entry]
    if conflicts:
        raise ConflictError("Existing MCP entries conflict with the selected source")
    changed = [name for name in servers if name not in existing]
    after = copy.deepcopy(original)
    if changed:
        after.setdefault("mcpServers", {}).update(copy.deepcopy(servers))
    return {"schema_version": 1, "config_path": str(path), "before": before,
            "original": original, "after": after, "servers": copy.deepcopy(servers),
            "changed_names": sorted(changed), "selected_names": sorted(servers)}


def _private_dir(path: Path) -> None:
    missing = []
    cursor = path
    while not cursor.exists():
        if cursor.is_symlink():
            raise AdapterError("Private state directory contains a broken symlink")
        missing.append(cursor)
        if cursor == cursor.parent:
            raise AdapterError("Cannot create private state directory")
        cursor = cursor.parent
    for directory in reversed(missing):
        directory.mkdir(mode=0o700)
    if path.is_symlink() or not path.is_dir():
        raise AdapterError("Private state must be a real directory")
    path.chmod(0o700)


def _private_file(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def _replace(path: Path, blob: bytes, mode: int, expected: dict) -> None:
    """Check current bytes/mode immediately before an atomic replacement."""
    fd, raw = tempfile.mkstemp(prefix=".agent-runtime-", dir=path.parent)
    temp = Path(raw)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(blob)
            stream.flush()
            os.fchmod(stream.fileno(), mode)
            os.fsync(stream.fileno())
        if not _same_snapshot(_snapshot(path), expected):
            raise ConflictError("Configuration changed since it was read")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def apply(prepared: dict, backup_dir: Path) -> dict:
    """Apply a plan, returning only a safe summary and a private manifest path."""
    if prepared.get("schema_version") != 1:
        raise AdapterError("Unsupported plan schema")
    path = Path(prepared["config_path"])
    before = prepared["before"]
    if not _same_snapshot(_snapshot(path), before):
        raise ConflictError("Configuration changed since planning")
    changed = prepared["changed_names"]
    if not changed:
        return {"status": "unchanged", "names": prepared["selected_names"],
                "before_sha256": before["sha256"], "after_sha256": before["sha256"],
                "manifest": None}
    # Rebuild from the original input so a caller cannot add unrelated edits.
    expected_plan = plan(path, prepared["servers"])
    if expected_plan != prepared:
        raise AdapterError("Plan contents were altered")
    directory = Path(backup_dir).expanduser().absolute() / ("claude-mcp-" + uuid.uuid4().hex)
    _private_dir(directory)
    backup = directory / "config.before.json"
    if before["exists"]:
        _private_file(backup, before["bytes"])
    after_blob = _json_bytes(prepared["after"])
    manifest = {
        "schema_version": 1, "config_path": str(path),
        "before_exists": before["exists"], "before_mode": before["mode"],
        "before_sha256": before["sha256"], "after_sha256": _sha(after_blob),
        "before_mcp_present": "mcpServers" in prepared["original"],
        "entries": {name: {"before_present": False,
                           "installed_sha256": _entry_sha(prepared["servers"][name])}
                    for name in changed},
    }
    manifest_path = directory / "manifest.json"
    _private_file(manifest_path, _json_bytes(manifest))
    if not path.parent.is_dir():
        raise AdapterError("Configuration parent directory does not exist")
    _replace(path, after_blob, before["mode"] if before["exists"] else 0o600, before)
    return {"status": "applied", "names": changed,
            "before_sha256": before["sha256"], "after_sha256": _sha(after_blob),
            "manifest": str(manifest_path)}


def rollback(manifest: Path) -> dict:
    """Undo owned additions only; reject changed entries and preserve other edits."""
    data = _object(Path(manifest).read_bytes())
    if data.get("schema_version") != 1 or not isinstance(data.get("entries"), dict):
        raise AdapterError("Unsupported rollback manifest")
    path = Path(data["config_path"])
    current = _snapshot(path)
    original = _object(current["bytes"]) if current["exists"] else {}
    existing = _servers(original)
    names = sorted(data["entries"])
    conflicts = [name for name in names if name in existing and
                 _entry_sha(existing[name]) != data["entries"][name]["installed_sha256"]]
    if conflicts:
        raise ConflictError("An installed MCP entry changed; rollback refused")
    # Absence is already the desired original state for addition-only plans.
    if not any(name in existing for name in names):
        return {"status": "unchanged", "names": names, "sha256": current["sha256"]}
    after = copy.deepcopy(original)
    for name in names:
        after["mcpServers"].pop(name, None)
    if not after["mcpServers"] and not data["before_mcp_present"]:
        del after["mcpServers"]
    if not after and not data["before_exists"]:
        if not _same_snapshot(_snapshot(path), current):
            raise ConflictError("Configuration changed during rollback")
        path.unlink()
        return {"status": "rolled_back", "names": names, "sha256": None}
    blob = _json_bytes(after)
    _replace(path, blob, current["mode"], current)
    return {"status": "rolled_back", "names": names, "sha256": _sha(blob)}
