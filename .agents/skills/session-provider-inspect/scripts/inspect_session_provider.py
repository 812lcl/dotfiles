#!/usr/bin/env python3
"""Inspect provider/model metadata recorded in a Codex session JSONL."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Sequence


SESSION_ID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


@dataclass(frozen=True)
class SessionCandidate:
    path: Path
    metadata_timestamp: str | None
    mtime_ns: int


def _is_session_id(value: str) -> bool:
    return bool(SESSION_ID_RE.fullmatch(value))


def _codex_runtime_marker() -> str | None:
    """Return the Codex environment marker, or None for non-Codex runtimes."""
    for env_name in ("CODEX_SESSION_ID", "CODEX_THREAD_ID"):
        if os.environ.get(env_name):
            return env_name
    return None


def _record_timestamp(record: dict[str, Any]) -> str | None:
    value = record.get("timestamp")
    return value if isinstance(value, str) else None


def _iter_records(path: Path, warnings: list[str]) -> Iterator[tuple[int, dict[str, Any]]]:
    try:
        handle = path.open("r", encoding="utf-8", errors="replace")
    except OSError as exc:
        warnings.append(f"cannot_read_session_file: {exc}")
        return

    with handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                warnings.append(f"malformed_jsonl_line:{line_number}")
                continue
            if isinstance(record, dict):
                yield line_number, record
            else:
                warnings.append(f"non_object_jsonl_line:{line_number}")


def _read_session_meta(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Read only enough of a file to obtain its session_meta timestamp."""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if (
                    isinstance(record, dict)
                    and record.get("type") == "session_meta"
                    and isinstance(record.get("payload"), dict)
                ):
                    payload = record["payload"]
                    timestamp = payload.get("timestamp")
                    return payload, timestamp if isinstance(timestamp, str) else None
    except OSError:
        return None, None
    return None, None


def _candidate_sort_key(candidate: SessionCandidate) -> tuple[int, str, int]:
    # Prefer a session metadata timestamp when available, then file mtime.
    return (
        1 if candidate.metadata_timestamp else 0,
        candidate.metadata_timestamp or "",
        candidate.mtime_ns,
    )


def find_session_files(codex_home: Path, session_id: str) -> list[Path]:
    """Return matching JSONL files without opening auth/config files."""
    sessions_root = codex_home / "sessions"
    if not sessions_root.is_dir():
        return []
    exact: list[Path] = []
    for path in sessions_root.rglob("*.jsonl"):
        if session_id in path.name:
            exact.append(path)
    return exact


def choose_session_file(
    codex_home: Path,
    session_id: str,
    warnings: list[str],
) -> tuple[Path | None, str]:
    candidates = find_session_files(codex_home, session_id)
    if not candidates:
        return None, "not_found"

    decorated: list[SessionCandidate] = []
    for path in candidates:
        metadata, metadata_timestamp = _read_session_meta(path)
        try:
            mtime_ns = path.stat().st_mtime_ns
        except OSError:
            mtime_ns = 0
        decorated.append(SessionCandidate(path, metadata_timestamp, mtime_ns))

    decorated.sort(key=_candidate_sort_key, reverse=True)
    if len(decorated) > 1:
        warnings.append(f"multiple_session_files:{len(decorated)}")
    selected = decorated[0].path
    return selected, "exact_filename_match"


def _latest_session_file(codex_home: Path, warnings: list[str]) -> Path | None:
    sessions_root = codex_home / "sessions"
    if not sessions_root.is_dir():
        return None
    candidates = list(sessions_root.rglob("*.jsonl"))
    if not candidates:
        return None
    candidates.sort(
        key=lambda path: path.stat().st_mtime_ns if path.exists() else 0,
        reverse=True,
    )
    warnings.append("session_id_source:fallback_newest_session_file")
    return candidates[0]


def resolve_session_id(
    explicit_session_id: str | None,
    codex_home: Path,
    warnings: list[str],
) -> tuple[str | None, Path | None, str]:
    if explicit_session_id:
        return explicit_session_id, None, "explicit"

    for env_name in ("CODEX_SESSION_ID", "CODEX_THREAD_ID"):
        value = os.environ.get(env_name)
        if value:
            return value, None, f"env:{env_name}"

    fallback_path = _latest_session_file(codex_home, warnings)
    if fallback_path is None:
        return None, None, "none"
    metadata, _ = _read_session_meta(fallback_path)
    if metadata:
        value = metadata.get("session_id") or metadata.get("id")
        if isinstance(value, str) and value:
            return value, fallback_path, "fallback_newest_session_file"
    match = re.search(
        r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12})",
        fallback_path.name,
    )
    if match:
        return match.group(1), fallback_path, "fallback_newest_session_file"
    return None, fallback_path, "fallback_newest_session_file"


def _thread_setting(record: dict[str, Any]) -> dict[str, Any] | None:
    payload = record.get("payload")
    if not isinstance(payload, dict) or payload.get("type") != "thread_settings_applied":
        return None
    settings = payload.get("thread_settings")
    return settings if isinstance(settings, dict) else None


def parse_session(path: Path) -> dict[str, Any]:
    warnings: list[str] = []
    session_meta: dict[str, Any] | None = None
    thread_settings: list[dict[str, Any]] = []
    thread_events: list[tuple[str | None, dict[str, Any]]] = []

    for _, record in _iter_records(path, warnings):
        if record.get("type") == "session_meta" and isinstance(record.get("payload"), dict):
            if session_meta is None:
                session_meta = record["payload"]
        settings = _thread_setting(record)
        if settings is not None:
            thread_settings.append(settings)
            thread_events.append((_record_timestamp(record), settings))

    if session_meta is None:
        warnings.append("missing_session_meta")

    first_settings = thread_settings[0] if thread_settings else None
    last_event = thread_events[-1] if thread_events else (None, None)
    last_timestamp, last_settings = last_event

    created_provider = session_meta.get("model_provider") if session_meta else None
    created_model = session_meta.get("model") if session_meta else None
    created_model_source = "session_meta"
    if not isinstance(created_model, str) or not created_model:
        created_model = first_settings.get("model") if first_settings else None
        created_model_source = (
            "first_thread_settings_applied" if created_model else "missing"
        )
        if created_model:
            warnings.append("creation_model_inferred_from_first_thread_settings")

    if not isinstance(created_provider, str) or not created_provider:
        created_provider = first_settings.get("model_provider_id") if first_settings else None
        if created_provider:
            warnings.append("creation_provider_inferred_from_first_thread_settings")

    recent_provider = last_settings.get("model_provider_id") if last_settings else None
    recent_model = last_settings.get("model") if last_settings else None
    if not thread_settings:
        warnings.append("missing_thread_settings_applied")

    if not created_provider:
        warnings.append("missing_creation_provider")
    if not created_model:
        warnings.append("missing_creation_model")
    if not recent_provider:
        warnings.append("missing_recent_provider")
    if not recent_model:
        warnings.append("missing_recent_model")

    provider_changed = (
        bool(created_provider)
        and bool(recent_provider)
        and created_provider != recent_provider
    )
    model_changed = (
        bool(created_model) and bool(recent_model) and created_model != recent_model
    )

    return {
        "session_id": (
            session_meta.get("session_id") or session_meta.get("id")
            if session_meta
            else None
        ),
        "created": {
            "timestamp": session_meta.get("timestamp") if session_meta else None,
            "provider": created_provider,
            "model": created_model,
            "model_source": created_model_source,
        },
        "recent": {
            "timestamp": last_timestamp,
            "provider": recent_provider,
            "model": recent_model,
            "source": "latest_thread_settings_applied" if last_settings else None,
        },
        "changed": {
            "provider": provider_changed,
            "model": model_changed,
            "any": provider_changed or model_changed,
        },
        "warnings": warnings,
    }


def summarize_session(
    path: Path,
    requested_session_id: str,
    session_id_source: str,
    show_path: bool = False,
) -> dict[str, Any]:
    result = parse_session(path)
    result["session_id"] = result.get("session_id") or requested_session_id
    result["session_file_source"] = session_id_source
    if show_path:
        result["session_file"] = str(path)
    return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect provider/model metadata recorded in a Codex session."
    )
    parser.add_argument("session_id", nargs="?", help="Codex session UUID")
    parser.add_argument("--session-id", dest="session_id_option", help="Codex session UUID")
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")),
        help="Codex home (default: CODEX_HOME or ~/.codex)",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    parser.add_argument("--json", action="store_true", help="Explicitly request JSON output")
    parser.add_argument(
        "--show-path",
        action="store_true",
        help="Include the selected local session file path",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.session_id and args.session_id_option and args.session_id != args.session_id_option:
        parser.error("positional session_id and --session-id disagree")
    explicit = args.session_id_option or args.session_id
    if explicit and not _is_session_id(explicit):
        parser.error("session_id must be a UUID")

    if _codex_runtime_marker() is None:
        print(
            json.dumps(
                {
                    "error": "codex_runtime_required",
                    "message": (
                        "session-provider-inspect only runs in Codex; "
                        "requires CODEX_SESSION_ID or CODEX_THREAD_ID from a Codex runtime"
                    ),
                    "warnings": [],
                },
                ensure_ascii=False,
                indent=2 if args.pretty else None,
            ),
            file=sys.stderr,
        )
        return 1

    codex_home = args.codex_home.expanduser()
    warnings: list[str] = []
    session_id, fallback_path, id_source = resolve_session_id(explicit, codex_home, warnings)
    if not session_id:
        print(
            json.dumps(
                {
                    "error": "cannot_resolve_session_id",
                    "warnings": warnings,
                },
                ensure_ascii=False,
                indent=2 if args.pretty else None,
            ),
            file=sys.stderr,
        )
        return 1

    if fallback_path is not None:
        path = fallback_path
        file_source = "fallback_newest_session_file"
    else:
        path, file_source = choose_session_file(codex_home, session_id, warnings)
    if path is None:
        print(
            json.dumps(
                {
                    "session_id": session_id,
                    "error": "session_file_not_found",
                    "warnings": warnings,
                },
                ensure_ascii=False,
                indent=2 if args.pretty else None,
            ),
            file=sys.stderr,
        )
        return 1

    result = summarize_session(path, session_id, file_source, args.show_path)
    result["session_id_source"] = id_source
    if warnings:
        result["warnings"] = warnings + result.get("warnings", [])
    if result.get("session_id") != session_id:
        result["warnings"].append("session_id_mismatch")

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2 if args.pretty else None,
            sort_keys=False,
        )
    )
    required = (
        result["created"].get("provider"),
        result["created"].get("model"),
        result["recent"].get("provider"),
        result["recent"].get("model"),
    )
    return 0 if all(required) else 1


if __name__ == "__main__":
    raise SystemExit(main())
