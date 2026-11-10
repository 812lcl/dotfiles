"""Native OpenCode V2 verification with per-session permissions and private evidence."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def exit_codes(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in ("exit", "exitCode", "exit_code") and type(child) is int:
                yield child
            elif isinstance(child, (dict, list)):
                yield from exit_codes(child)
    elif isinstance(value, list):
        for child in value:
            yield from exit_codes(child)


def parse_stream(stdout, capture_text=False):
    data = {"initialized": False, "calls": [], "steps": [], "protocol_errors": 0,
            "runtime_errors": 0, "tool_calls_succeeded": 0, "tool_calls_failed": 0}
    completed, pending, texts = set(), set(), {}
    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except ValueError:
            data["protocol_errors"] += 1
            continue
        if not isinstance(event, dict):
            data["protocol_errors"] += 1
            continue
        kind, part = event.get("type"), event.get("part", {})
        if kind == "step_start":
            data["initialized"] = True
        elif kind == "tool_use" and isinstance(part, dict):
            ident = part.get("partID", part.get("id"))
            state = part.get("state", {})
            if not isinstance(ident, str) or not isinstance(state, dict):
                data["protocol_errors"] += 1
                continue
            status = state.get("status")
            if status not in ("completed", "error", "cancelled"):
                pending.add(ident)
                continue
            if ident in completed:
                data["protocol_errors"] += 1
                continue
            completed.add(ident)
            pending.discard(ident)
            metadata, args = state.get("metadata", {}), state.get("input", {})
            codes = list(exit_codes(metadata.get("metadata", metadata) if isinstance(metadata, dict) else metadata))
            ok = status == "completed" and not state.get("error") and all(x == 0 for x in codes)
            call = {"id": ident, "name": part.get("tool"), "status": status, "success": ok,
                    "input_sha256": digest(args), "output_sha256": digest(state.get("output", state.get("error"))),
                    "metadata_sha256": digest(metadata), "exit_codes": codes}
            if part.get("tool") == "read" and isinstance(args, dict):
                call["path"] = args.get("path")
            data["calls"].append(call)
            data["tool_calls_succeeded" if ok else "tool_calls_failed"] += 1
        elif kind == "text" and capture_text and isinstance(part.get("text"), str):
            texts[part.get("id", str(len(texts)))] = part["text"][:4000]
        elif kind == "step_finish":
            data["steps"].append({k: part.get(k) for k in ("reason", "cost", "tokens")})
        elif kind in ("error", "session.error"):
            data["runtime_errors"] += 1
    data["pending_calls"] = len(pending)
    if capture_text:
        data["text"] = "\n".join(texts.values())[:4000]
    return data


def status(data, code, timeout):
    if timeout:
        return "timeout"
    if data["protocol_errors"]:
        return "protocol_error"
    if code != 0 or data["runtime_errors"]:
        return "runtime_error"
    if not data["initialized"] or not data["steps"] or data["pending_calls"]:
        return "incomplete"
    if data["steps"][-1]["reason"] != "stop":
        return "runtime_limit_or_error"
    return "completed_with_tool_errors" if data["tool_calls_failed"] else "completed"


SESSION_PERMISSIONS = [{"action": "*", "resource": "*", "effect": "deny"}] + [
    {"action": name, "resource": "*", "effect": "allow"}
    for name in ("read", "shell", "edit", "skill", "glob", "grep")
]


def api(executable, operation, cwd, *, data=None, parameters=()):
    command = [executable, "api", operation, "--standalone"]
    if data is not None:
        command += ["--data", json.dumps(data)]
    for parameter in parameters:
        command += ["--param", parameter]
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=40)
    if result.returncode:
        raise ValueError("Native OpenCode API failed: " + operation)
    if not result.stdout.strip():
        return None  # Native PATCH endpoints may successfully return no content.
    value = json.loads(result.stdout)
    return value.get("data", value) if isinstance(value, dict) else value


def run_opencode(prompt, workspace, *, timeout_seconds=240, capture_text=False,
                 executable="/Users/liuchunlei/.local/bin/opencode"):
    root = Path(workspace)
    if not root.is_absolute() or not root.is_dir() or not prompt.strip() or timeout_seconds <= 0:
        raise ValueError("An existing absolute workspace, prompt and positive timeout are required")
    session = api(executable, "session.create", root, data={
        "title": "Agent runtime verification", "location": {"directory": str(root)},
        "permissions": SESSION_PERMISSIONS})
    sid = session["id"]
    api(executable, "session.update", root, parameters=["sessionID=" + sid], data={"archived": True})
    command = [executable, "run", "--standalone", "--archived", "--auto", "--format", "json",
               "--session", sid, prompt]
    start = time.monotonic()
    process = subprocess.Popen(command, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, start_new_session=True)
    timeout = False
    try:
        try:
            out, err = process.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timeout = True
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                out, err = process.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                out, err = process.communicate(timeout=3)
    finally:
        api(executable, "session.update", root,
            parameters=["sessionID=" + sid], data={"archived": True})
        archived = api(executable, "session.get", root, parameters=["sessionID=" + sid])
    data = parse_stream(out, capture_text)
    permissions_ok = archived.get("permissions") == SESSION_PERMISSIONS
    data.update({"status": status(data, process.returncode, timeout), "returncode": process.returncode,
                 "timed_out": timeout, "wall_seconds": round(time.monotonic() - start, 3),
                 "stderr_present": bool(err), "session_id": sid,
                 "session_permissions_preserved": permissions_ok, "native_model_override": False,
                 "standalone_server": True, "test_session_archived": True,
                 "persistent_permission_configuration_modified": False})
    if not permissions_ok:
        data["status"] = "session_policy_changed"
    return data
