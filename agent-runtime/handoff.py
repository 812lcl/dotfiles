"""Local, cooperative task handoff. Never commits, stashes, or resets a worktree."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile


class HandoffError(ValueError):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(data):
    return (json.dumps(data, ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode()


def git(root, *args):
    proc = subprocess.run(
        ["git", "--no-optional-locks", "-c", "core.fsmonitor=false", "-C", str(root), *args],
        capture_output=True, timeout=30,
    )
    if proc.returncode:
        raise HandoffError("Git inspection failed: " + args[0])
    return proc.stdout


def file_record(root, relative):
    path = Path(relative)
    if path.is_absolute() or not path.parts or any(p in ("..", ".git") for p in path.parts):
        raise HandoffError("File must be a repository-relative path outside .git")
    current = root
    for part in path.parts[:-1]:
        current /= part
        if current.is_symlink():
            raise HandoffError("Refusing to traverse a symlinked parent")
    path = root / path
    try:
        info = path.lstat()
    except FileNotFoundError:
        return {"kind": "missing"}
    mode = stat.S_IMODE(info.st_mode)
    if stat.S_ISLNK(info.st_mode):
        return {"kind": "symlink", "mode": mode, "target": os.readlink(path)}
    if stat.S_ISDIR(info.st_mode):
        # Git submodule content is inspected independently; do not imply it is unchanged.
        raise HandoffError("Changed directories/submodules need a separate handoff")
    if not stat.S_ISREG(info.st_mode):
        raise HandoffError("Unsupported changed file type")
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return {"kind": "file", "mode": mode, "size": info.st_size, "sha256": hasher.hexdigest()}


def snapshot(root):
    root = Path(root).expanduser().resolve(strict=True)
    top = Path(os.fsdecode(git(root, "rev-parse", "--show-toplevel")).strip()).resolve()
    if root != top:
        raise HandoffError("Use the exact worktree root")
    raw = git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    records = raw.split(b"\0")
    files = {}
    index = 0
    while index < len(records) and records[index]:
        entry = records[index]
        status_code = entry[:2].decode("ascii")
        name = os.fsdecode(entry[3:])
        if "U" in status_code or status_code in ("AA", "DD"):
            raise HandoffError("Resolve Git conflicts before transferring ownership")
        files[name] = {"status": status_code, **file_record(root, name)}
        if "R" in status_code or "C" in status_code:
            index += 1
            files[name]["original_path"] = os.fsdecode(records[index])
        index += 1
    state = {
        "root": str(root),
        "git_common_dir": os.fsdecode(git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")).strip(),
        "head": git(root, "rev-parse", "HEAD").decode().strip(),
        "branch": git(root, "branch", "--show-current").decode().strip(),
        "status_sha256": digest(raw),
        "staged_diff_sha256": digest(git(root, "diff", "--cached", "--binary", "--no-ext-diff", "--no-textconv")),
        "unstaged_diff_sha256": digest(git(root, "diff", "--binary", "--no-ext-diff", "--no-textconv")),
        "files": files,
    }
    return {**state, "fingerprint": digest(json_bytes(state))}


def atomic_json(path, data):
    path = Path(path).expanduser().absolute()
    if path.is_symlink():
        raise HandoffError("State file must not be a symlink")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=".handoff-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(json_bytes(data))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def locked(path):
    path = Path(path).expanduser().absolute()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(str(path) + ".lock", flags, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise HandoffError("Another handoff writer holds the lock") from exc
        yield path
    finally:
        os.close(fd)


def load(path):
    path = Path(path)
    if path.is_symlink():
        raise HandoffError("State file must not be a symlink")
    state = json.loads(path.read_text())
    if state.get("schema_version") != 1:
        raise HandoffError("Unsupported handoff version")
    return state


def stamp(state):
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    return state


def outside_worktree(path, root):
    """Validate before creating even a lock; parent aliases cannot enter repo."""
    requested = Path(path).expanduser().absolute()
    if requested.is_symlink():
        raise HandoffError("State file must not be a symlink")
    requested = requested.parent.resolve() / requested.name
    if requested.is_relative_to(Path(root).expanduser().resolve(strict=True)):
        raise HandoffError("Store handoff state outside the worktree")
    return requested


def existing_state_path(path):
    state = load(path)
    return outside_worktree(path, state["snapshot"]["root"])


def create(path, root, owner, goal, next_step, scope, protected=(), constraints=(), processes=None):
    if scope not in ("personal", "work"):
        raise HandoffError("Choose personal or work explicitly")
    if not owner or not goal or not next_step:
        raise HandoffError("Owner, goal, and next step are required")
    requested = outside_worktree(path, root)
    with locked(requested) as path:
        if path.exists():
            raise HandoffError("Handoff already exists")
        current = snapshot(root)
        # Keep state out of the repository: otherwise its own update changes the snapshot.
        outside_worktree(path, current["root"])
        state = stamp({
            "schema_version": 1, "revision": 1, "state": "owned", "owner": owner,
            "goal": goal, "next_step": next_step, "brain_scope": scope,
            "constraints": list(constraints), "snapshot": current,
            "protected_user_files": {str(p): file_record(Path(current["root"]), p) for p in protected},
            "processes": processes or {"status": "unverified", "items": []},
            "verification": [],
            "ownership_contract": "Cooperative single writer; does not block unrelated processes.",
        })
        atomic_json(path, state)
        return state


def protected_changes(state):
    root = Path(state["snapshot"]["root"])
    return [name for name, expected in state["protected_user_files"].items() if file_record(root, name) != expected]


def inspect(path):
    state = load(path)
    current = snapshot(state["snapshot"]["root"])
    protected = protected_changes(state)
    return {
        "ok": current["fingerprint"] == state["snapshot"]["fingerprint"] and not protected,
        "revision": state["revision"], "owner": state["owner"], "state": state["state"],
        "snapshot_matches": current["fingerprint"] == state["snapshot"]["fingerprint"],
        "protected_changes": protected, "current_fingerprint": current["fingerprint"],
    }


def release(path, owner, revision, next_step=None, verification=None):
    requested = existing_state_path(path)
    with locked(requested) as path:
        state = load(path)
        outside_worktree(path, state["snapshot"]["root"])
        if (state["state"] != "owned" or state["owner"] != owner
                or state["revision"] != revision):
            raise HandoffError("Owned state and owner/revision must match before release")
        if protected_changes(state):
            raise HandoffError("Protected user files changed; do not overwrite or reset them")
        state["snapshot"] = snapshot(state["snapshot"]["root"])
        state["state"] = "released"
        state["revision"] += 1
        if next_step:
            state["next_step"] = next_step
        if verification is not None:
            state["verification"] = verification
        atomic_json(path, stamp(state))
        return state


def claim(path, owner, revision):
    requested = existing_state_path(path)
    with locked(requested) as path:
        state = load(path)
        outside_worktree(path, state["snapshot"]["root"])
        if not owner or state["state"] != "released" or state["revision"] != revision:
            raise HandoffError("Handoff must be released at the expected revision")
        if not inspect(path)["ok"]:
            raise HandoffError("Worktree changed since release; inspect the new state before transfer")
        state["previous_owner"] = state["owner"]
        state["owner"] = owner
        state["state"] = "owned"
        state["revision"] += 1
        atomic_json(path, stamp(state))
        return state
