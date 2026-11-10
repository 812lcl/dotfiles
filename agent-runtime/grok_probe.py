"""Bounded native Grok Build probes with ACP-style metadata-only evidence."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def exit_codes(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in ("exitCode", "exit_code") and isinstance(item, int):
                yield item
            elif isinstance(item, (dict, list)):
                yield from exit_codes(item)
    elif isinstance(value, list):
        for item in value:
            yield from exit_codes(item)


def parse_stream(stdout, capture_text=False):
    data = {"initialized": False, "available_tools": [], "available_commands": [],
            "calls": [], "tool_calls_succeeded": 0, "tool_calls_failed": 0,
            "protocol_errors": 0, "runtime_errors": 0, "end": None}
    calls, completed, text = {}, set(), ""
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
        if kind == "available_commands":
            data["initialized"] = True
            for key in ("tools", "commands"):
                data["available_" + key] = [x for x in event.get(key, []) if isinstance(x, str)]
        elif kind == "tool_call":
            ident = event.get("toolCallId")
            if not isinstance(ident, str) or ident in calls:
                data["protocol_errors"] += 1
                continue
            calls[ident] = {"id": ident, "name": event.get("toolName"),
                            "input_sha256": digest(event.get("rawInput"))}
            args = event.get("rawInput")
            if isinstance(args, dict) and isinstance(args.get("target_file"), str):
                calls[ident]["path"] = args["target_file"]
        elif kind == "tool_call_update" and event.get("status") in ("completed", "failed"):
            ident = event.get("toolCallId")
            if ident not in calls or ident in completed:
                data["protocol_errors"] += 1
                continue
            completed.add(ident)
            output = event.get("rawOutput")
            codes = list(exit_codes(output))
            ok = event["status"] == "completed" and all(code == 0 for code in codes)
            if isinstance(output, dict) and str(output.get("type", "")).lower() in ("error", "failure"):
                ok = False
            data["calls"].append({**calls[ident], "success": ok,
                                  "result_sha256": digest(output), "exit_codes": codes,
                                  "result_keys": list(output) if isinstance(output, dict) else []})
            data["tool_calls_succeeded" if ok else "tool_calls_failed"] += 1
        elif kind == "text" and capture_text and isinstance(event.get("data"), str):
            text = (text + event["data"])[:4000]
        elif kind == "error":
            data["runtime_errors"] += 1
        elif kind == "end":
            if data["end"] is not None:
                data["protocol_errors"] += 1
            data["end"] = {k: event.get(k) for k in ("stopReason", "cwd", "usage", "num_turns", "total_cost_usd", "modelUsage")}
    data["pending_calls"] = len(set(calls) - completed)
    if capture_text:
        data["text"] = text
    return data


def status(data, returncode, timeout):
    if timeout:
        return "timeout"
    if data["protocol_errors"]:
        return "protocol_error"
    if returncode != 0 or data["runtime_errors"]:
        return "runtime_error"
    if not data["initialized"] or not data["end"] or data["pending_calls"]:
        return "incomplete"
    if data["end"]["stopReason"] not in ("end_turn", "EndTurn"):
        return "runtime_limit_or_error"
    return "completed_with_tool_errors" if data["tool_calls_failed"] else "completed"


def run_grok(prompt, workspace, *, tools=("read_file", "run_terminal_cmd"),
             max_turns=18, timeout_seconds=240, add_dirs=(), approve=False,
             capture_text=False, executable="/Users/liuchunlei/.local/bin/grok"):
    root = Path(workspace)
    if not root.is_absolute() or not root.is_dir() or not prompt.strip():
        raise ValueError("An absolute existing workspace and prompt are required")
    if max_turns < 1 or timeout_seconds <= 0:
        raise ValueError("Positive turn and timeout limits are required")
    if add_dirs:
        raise ValueError("Installed Grok session backend rejects additionalDirectories; use explicit shell paths from the real cwd")
    command = [executable, "--cwd", str(root), "--no-subagents", "--disable-web-search",
               "--tools", ",".join(tools), "--max-turns", str(max_turns),
               "--output-format", "streaming-json"]
    if approve:
        command.append("--always-approve")
    command += ["-p", prompt]
    env = dict(os.environ)
    env["GROK_MEMORY"] = "0"  # Probe-only: never changes the user's native memory settings.
    start = time.monotonic()
    process = subprocess.Popen(command, cwd=root, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, start_new_session=True)
    timeout = False
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
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            out, err = process.communicate(timeout=3)
    data = parse_stream(out, capture_text)
    data.update({"status": status(data, process.returncode, timeout), "returncode": process.returncode,
                 "timed_out": timeout, "wall_seconds": round(time.monotonic() - start, 3),
                 "stderr_present": bool(err), "native_memory_disabled_for_probe": True,
                 "subagents_disabled_for_probe": True, "approve_for_this_probe": approve,
                 "native_hooks_preserved": True, "cost_is_estimate": True})
    return data
