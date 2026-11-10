"""Bounded native Cursor CLI verification; persist metadata, never tool bodies."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def parse_stream(stdout, capture_text=False):
    data = {"initialized": False, "init": None, "calls": [], "result": None,
            "tool_calls_succeeded": 0, "tool_calls_failed": 0,
            "protocol_errors": 0, "unknown_tool_results": 0}
    started, completed = {}, set()
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
        kind = event.get("type")
        if kind == "system" and event.get("subtype") == "init":
            data["initialized"] = True
            data["init"] = {k: event.get(k) for k in ("cwd", "model", "permissionMode", "apiKeySource")}
        elif kind == "tool_call":
            call_id = event.get("call_id")
            call = event.get("tool_call", {})
            candidates = [(k, v) for k, v in call.items()
                          if k.endswith("ToolCall") and isinstance(v, dict)] if isinstance(call, dict) else []
            if len(candidates) != 1 or not isinstance(call_id, str):
                data["protocol_errors"] += 1
                continue
            name, value = candidates[0]
            args = value.get("args", {})
            subtype = event.get("subtype")
            if subtype == "started":
                if call_id in started:
                    data["protocol_errors"] += 1
                started[call_id] = (name, sha(args))
            elif subtype == "completed":
                if call_id in completed or started.get(call_id) != (name, sha(args)):
                    data["protocol_errors"] += 1
                completed.add(call_id)
                result = value.get("result", {})
                ok = isinstance(result, dict) and "success" in result and not result.get("error")
                payload = result.get("success") if isinstance(result, dict) else None
                exit_code = payload.get("exitCode") if isinstance(payload, dict) else None
                if exit_code is not None and exit_code != 0:
                    ok = False
                if not isinstance(result, dict) or not any(k in result for k in ("success", "error", "rejected")):
                    data["unknown_tool_results"] += 1
                    ok = False
                record = {"id": call_id, "name": name, "input_sha256": sha(args),
                          "result_sha256": sha(result), "success": ok, "exit_code": exit_code,
                          "result_keys": list(result) if isinstance(result, dict) else [],
                          "success_keys": list(payload) if isinstance(payload, dict) else []}
                if name == "readToolCall" and isinstance(args, dict):
                    record["path"] = args.get("path")
                data["calls"].append(record)
                data["tool_calls_succeeded" if ok else "tool_calls_failed"] += 1
        elif kind == "result":
            data["result"] = {k: event.get(k) for k in ("subtype", "is_error", "duration_ms", "usage")}
            if capture_text and isinstance(event.get("result"), str):
                data["result"]["text"] = event["result"][:4000]
    data["pending_calls"] = len(set(started) - completed)
    return data


def status(data, returncode, timed_out):
    if timed_out:
        return "timeout"
    if data["protocol_errors"] or data["unknown_tool_results"]:
        return "protocol_error"
    if returncode != 0 or (data["result"] and data["result"].get("is_error")):
        return "runtime_error"
    if not data["initialized"] or not data["result"] or data["pending_calls"]:
        return "incomplete"
    if data["result"].get("subtype") != "success":
        return "runtime_error"
    if data["tool_calls_failed"]:
        return "completed_with_tool_errors"
    return "completed"


def run_cursor(prompt, workspace, *, timeout_seconds=180, force=False,
               add_dirs=(), capture_text=False,
               executable="/Users/liuchunlei/.local/bin/cursor-agent"):
    root = Path(workspace)
    if not root.is_absolute() or not root.is_dir() or not prompt.strip():
        raise ValueError("An existing absolute workspace and nonempty prompt are required")
    if timeout_seconds <= 0:
        raise ValueError("Timeout must be positive")
    command = [executable, "--print", "--output-format", "stream-json", "--trust",
               "--workspace", str(root)]
    if force:
        command.append("--force")
    for directory in add_dirs:
        p = Path(directory)
        if not p.is_absolute() or not p.is_dir():
            raise ValueError("Additional workspace directories must exist and be absolute")
        command += ["--add-dir", str(p)]
    command.append(prompt)
    start = time.monotonic()
    process = subprocess.Popen(command, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, start_new_session=True)
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGTERM)
        try:
            stdout, stderr = process.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate(timeout=3)
    data = parse_stream(stdout, capture_text)
    data.update({"status": status(data, process.returncode, timed_out),
                 "returncode": process.returncode, "timed_out": timed_out,
                 "wall_seconds": round(time.monotonic() - start, 3),
                 "stderr_nonempty": bool(stderr), "force_for_this_probe": force,
                 "native_hooks_preserved": True, "native_session_persistence_preserved": True})
    return data
