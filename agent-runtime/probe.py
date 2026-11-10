"""Bounded Claude runtime probes with metadata-only evidence by default.

This module does not edit agent configuration or choose a provider/model. The
per-process settings overlay disables lifecycle hooks and native auto memory;
other normal user/project/local discovery remains enabled. An initialization
event proves discovery, never a successful tool invocation.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time
from typing import Iterable


_OVERLAY = {"disableAllHooks": True, "autoMemoryEnabled": False}
_IDENTIFIER = re.compile(r"^[a-zA-Z0-9_.:-]{1,160}$")
_FINAL_TEXT_LIMIT = 4000


def _sha(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _text(value: object, limit: int = 512) -> str | None:
    return value[:limit] if isinstance(value, str) else None


def _names(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item[:512] for item in value if isinstance(item, str)]


def _number(value: object) -> int | float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value if math.isfinite(value) and value >= 0 else None
    return None


def parse_stream(stdout: str, *, capture_text: bool = False) -> dict:
    """Keep an allowlist of structured events; hash tool inputs/results.

    The caller must separately account for process exit and timeout. Unknown
    events are counted, not retained. Provider error strings and assistant
    prose are discarded, except an explicitly requested fixture final text.
    """
    evidence = {
        "initialized": False, "init": None, "tool_uses": [],
        "tool_results": [], "tool_calls_succeeded": 0,
        "tool_calls_failed": 0, "unmatched_tool_results": 0,
        "non_json_lines": 0, "ignored_events": 0,
        "result": None, "permission_denials": 0,
        "structured_refusal": False, "errors": [],
    }
    calls: dict[str, str | None] = {}
    completed_calls: set[str] = set()
    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except (ValueError, TypeError):
            evidence["non_json_lines"] += 1
            continue
        if not isinstance(event, dict):
            evidence["non_json_lines"] += 1
            continue
        kind = event.get("type")
        if kind == "system" and event.get("subtype") == "init":
            servers = event.get("mcp_servers", [])
            plugins = event.get("plugins", [])
            evidence["initialized"] = True
            evidence["init"] = {
                "model": _text(event.get("model")),
                "version": _text(event.get("claude_code_version")),
                "cwd": _text(event.get("cwd"), 4096),
                "skills": _names(event.get("skills")),
                "slash_commands": _names(event.get("slash_commands")),
                "tools": _names(event.get("tools")),
                "mcp_servers": [
                    {"name": _text(server.get("name")),
                     "status": _text(server.get("status"))}
                    for server in servers if isinstance(server, dict)
                ] if isinstance(servers, list) else [],
                "plugins": [plugin["name"][:512] for plugin in plugins
                            if isinstance(plugin, dict)
                            and isinstance(plugin.get("name"), str)]
                if isinstance(plugins, list) else [],
            }
        elif kind in ("assistant", "user"):
            message = event.get("message", {})
            if not isinstance(message, dict):
                evidence["ignored_events"] += 1
                continue
            if message.get("stop_reason") == "refusal":
                evidence["structured_refusal"] = True
            if event.get("error") or message.get("error"):
                evidence["errors"].append("assistant_error")
            content = message.get("content", [])
            for block in content if isinstance(content, list) else []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "refusal":
                    evidence["structured_refusal"] = True
                elif block.get("type") == "tool_use":
                    tool_id = _text(block.get("id"))
                    name = _text(block.get("name"))
                    if tool_id and tool_id in calls:
                        evidence["errors"].append("duplicate_tool_use_id")
                    elif tool_id:
                        calls[tool_id] = name
                    evidence["tool_uses"].append({
                        "id": tool_id, "name": name,
                        "input_sha256": _sha(block.get("input")),
                    })
                elif block.get("type") == "tool_result":
                    tool_id = _text(block.get("tool_use_id"))
                    matched = bool(tool_id and tool_id in calls)
                    is_error = bool(block.get("is_error", False))
                    evidence["tool_results"].append({
                        "tool_use_id": tool_id,
                        "name": calls.get(tool_id) if tool_id else None,
                        "matched": matched, "is_error": is_error,
                        "result_sha256": _sha(block.get("content")),
                    })
                    if not matched:
                        evidence["unmatched_tool_results"] += 1
                    elif tool_id in completed_calls:
                        evidence["errors"].append("duplicate_tool_result")
                    else:
                        completed_calls.add(tool_id)
                        key = "tool_calls_failed" if is_error else "tool_calls_succeeded"
                        evidence[key] += 1
        elif kind == "result":
            raw_subtype = event.get("subtype")
            subtype = raw_subtype if isinstance(raw_subtype, str) and _IDENTIFIER.fullmatch(raw_subtype) else "unknown"
            denials = event.get("permission_denials")
            if isinstance(denials, list):
                evidence["permission_denials"] += len(denials)
            if "refus" in subtype:
                evidence["structured_refusal"] = True
            evidence["result"] = {
                "subtype": subtype,
                "is_error": bool(event.get("is_error", False)),
                "duration_ms": _number(event.get("duration_ms")),
                "num_turns": _number(event.get("num_turns")),
                "estimated_cost_usd": _number(event.get("total_cost_usd", event.get("cost_usd"))),
            }
            if event.get("errors"):
                evidence["errors"].append("runtime_reported_error")
            if capture_text and isinstance(event.get("result"), str):
                evidence["result"]["text"] = event["result"][:_FINAL_TEXT_LIMIT]
                evidence["result"]["text_truncated"] = len(event["result"]) > _FINAL_TEXT_LIMIT
        elif kind in ("error", "permission_denied", "refusal"):
            if kind == "permission_denied":
                evidence["permission_denials"] += 1
            elif kind == "refusal":
                evidence["structured_refusal"] = True
            else:
                evidence["errors"].append("runtime_error_event")
        else:
            evidence["ignored_events"] += 1
    evidence["errors"] = sorted(set(evidence["errors"]))
    evidence["pending_tool_calls"] = len(set(calls) - completed_calls)
    return evidence


def _signal_group(pid: int, sig: int) -> None:
    try:
        os.killpg(pid, sig)
    except ProcessLookupError:
        pass


def _stop_group(process: subprocess.Popen, grace_seconds: float = 2.0) -> tuple[str, str]:
    """Stop only the group created for this probe; reap its direct process."""
    _signal_group(process.pid, signal.SIGTERM)
    try:
        output = process.communicate(timeout=grace_seconds)
    except subprocess.TimeoutExpired:
        _signal_group(process.pid, signal.SIGKILL)
        output = process.communicate(timeout=grace_seconds)
    finally:
        # A cooperative leader can exit while its child still holds the group.
        _signal_group(process.pid, signal.SIGKILL)
    return output


def _status(evidence: dict, returncode: int | None, timed_out: bool) -> str:
    if timed_out:
        return "timeout"
    if evidence["non_json_lines"]:
        return "protocol_error"
    if evidence["permission_denials"]:
        return "permission_denied"
    if evidence["structured_refusal"]:
        return "refused"
    result = evidence["result"]
    if result and result["subtype"] == "error_max_turns":
        return "turn_limit"
    if result and result["subtype"] == "error_max_budget_usd":
        return "budget_limit"
    if returncode != 0 or evidence["errors"] or (result and result["is_error"]):
        return "runtime_error"
    if result is None:
        return "incomplete"
    if result["subtype"] != "success":
        return "runtime_error"
    if evidence["tool_calls_failed"]:
        return "completed_with_tool_errors"
    if evidence["pending_tool_calls"] or evidence["unmatched_tool_results"]:
        return "incomplete"
    return "completed"


def run_claude(prompt: str, cwd: str | Path, tools: Iterable[str],
               allowed_tools: Iterable[str], disallowed_tools: Iterable[str] = (),
               max_turns: int = 2, budget_usd: float = 0.5,
               timeout_seconds: float = 120, capture_text: bool = False,
               *, claude_path: str | Path | None = None) -> dict:
    """Run one bounded prompt without exposing its raw content in evidence.

    ``tools`` limits built-ins only; use ``disallowed_tools`` to deny MCP tools
    for discovery-only runs. Budget enforcement is Claude's cost estimate, not
    a hard cap on a third-party provider's bill. No global settings are written.
    ``capture_text`` is reserved for non-private acceptance fixtures.
    """
    cwd = Path(cwd)
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt must be nonempty text")
    if not cwd.is_absolute() or not cwd.is_dir():
        raise ValueError("cwd must be an existing absolute directory")
    if not isinstance(max_turns, int) or isinstance(max_turns, bool) or max_turns < 1:
        raise ValueError("max_turns must be a positive integer")
    if _number(budget_usd) is None or budget_usd <= 0:
        raise ValueError("budget_usd must be positive and finite")
    if _number(timeout_seconds) is None or timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive and finite")
    tool_lists = []
    for values in (tools, allowed_tools, disallowed_tools):
        if isinstance(values, str):
            raise ValueError("tool lists must be iterables of names, not strings")
        values = list(values)
        if any(not isinstance(value, str) or not value or "\0" in value for value in values):
            raise ValueError("tool names must be nonempty strings")
        tool_lists.append(values)
    executable = str(claude_path) if claude_path is not None else shutil.which("claude")
    evidence = parse_stream("")
    evidence.update({"status": "spawn_error", "returncode": None,
                     "timed_out": False, "stderr_present": False,
                     "wall_duration_seconds": 0.0, "cost_is_estimate": True,
                     "hooks_disabled_for_probe": True,
                     "native_auto_memory_disabled_for_probe": True})
    if not executable or not Path(executable).is_absolute():
        evidence["errors"] = ["claude_executable_unavailable"]
        return evidence
    command = [executable, "-p", "--verbose", "--output-format", "stream-json",
               "--no-session-persistence", "--permission-mode", "dontAsk",
               "--permission-prompts", "none", "--max-turns", str(max_turns),
               "--max-budget-usd", str(budget_usd), "--settings",
               json.dumps(_OVERLAY, separators=(",", ":")),
               "--tools", ",".join(tool_lists[0])]
    if tool_lists[1]:
        command.extend(["--allowedTools", *tool_lists[1]])
    if tool_lists[2]:
        command.extend(["--disallowedTools", *tool_lists[2]])
    started = time.monotonic()
    try:
        process = subprocess.Popen(command, cwd=str(cwd), stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, encoding="utf-8", errors="replace",
                                   start_new_session=True)
    except OSError:
        evidence["errors"] = ["claude_spawn_failed"]
        return evidence
    timed_out = False
    try:
        stdout, stderr = process.communicate(input=prompt, timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            stdout, stderr = _stop_group(process)
        except (OSError, subprocess.TimeoutExpired):
            evidence.update({"status": "timeout", "timed_out": True,
                             "errors": ["probe_cleanup_incomplete"],
                             "returncode": process.returncode,
                             "wall_duration_seconds": round(time.monotonic() - started, 3)})
            return evidence
    except BaseException:
        _stop_group(process)
        raise
    parsed = parse_stream(stdout, capture_text=capture_text)
    evidence.update(parsed)
    evidence.update({"status": _status(parsed, process.returncode, timed_out),
                     "returncode": process.returncode, "timed_out": timed_out,
                     "stderr_present": bool(stderr),
                     "wall_duration_seconds": round(time.monotonic() - started, 3)})
    return evidence
