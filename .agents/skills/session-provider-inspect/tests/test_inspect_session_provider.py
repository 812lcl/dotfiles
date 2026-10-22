import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import inspect_session_provider as inspector  # noqa: E402


def write_session(root: Path, session_id: str, records: list[dict]) -> Path:
    path = root / "sessions" / "2026" / "09" / f"rollout-2026-09-24T00-00-00-{session_id}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")
    return path


def meta(session_id: str, provider: str, model: str | None = None) -> dict:
    payload = {
        "session_id": session_id,
        "id": session_id,
        "timestamp": "2026-09-24T00:00:00.000Z",
        "model_provider": provider,
    }
    if model is not None:
        payload["model"] = model
    return {"timestamp": "2026-09-24T00:00:01.000Z", "type": "session_meta", "payload": payload}


def settings(provider: str, model: str, timestamp: str) -> dict:
    return {
        "timestamp": timestamp,
        "type": "event_msg",
        "payload": {
            "type": "thread_settings_applied",
            "thread_settings": {
                "model": model,
                "model_provider_id": provider,
            },
        },
    }


class InspectSessionProviderTests(unittest.TestCase):
    def test_provider_and_model_unchanged(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sid = "01a0d20e-ca6b-7b30-b6fe-4a4c12736b67"
            path = write_session(root, sid, [meta(sid, "sky_router"), settings("sky_router", "gpt-6-sol", "2026-09-24T00:01:00Z")])
            result = inspector.parse_session(path)
            self.assertEqual(result["created"]["model"], "gpt-6-sol")
            self.assertFalse(result["changed"]["any"])

    def test_provider_and_model_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sid = "01a0d20e-ca6b-7b30-b6fe-4a4c12736b67"
            path = write_session(
                root,
                sid,
                [
                    meta(sid, "openai", "gpt-5"),
                    settings("openai", "gpt-5", "2026-09-24T00:01:00Z"),
                    settings("sky_router", "gpt-6-sol", "2026-09-24T00:02:00Z"),
                ],
            )
            result = inspector.parse_session(path)
            self.assertTrue(result["changed"]["provider"])
            self.assertTrue(result["changed"]["model"])
            self.assertTrue(result["changed"]["any"])

    def test_provider_only_change_is_reported_separately(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sid = "01a0d20e-ca6b-7b30-b6fe-4a4c12736b67"
            path = write_session(
                root,
                sid,
                [
                    meta(sid, "openai", "gpt-5"),
                    settings("openai", "gpt-5", "2026-09-24T00:01:00Z"),
                    settings("sky_router", "gpt-5", "2026-09-24T00:02:00Z"),
                ],
            )
            result = inspector.parse_session(path)
            self.assertTrue(result["changed"]["provider"])
            self.assertFalse(result["changed"]["model"])
            self.assertTrue(result["changed"]["any"])

    def test_model_only_change_is_reported_separately(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sid = "01a0d20e-ca6b-7b30-b6fe-4a4c12736b67"
            path = write_session(
                root,
                sid,
                [
                    meta(sid, "openai", "gpt-5"),
                    settings("openai", "gpt-5", "2026-09-24T00:01:00Z"),
                    settings("openai", "gpt-6-sol", "2026-09-24T00:02:00Z"),
                ],
            )
            result = inspector.parse_session(path)
            self.assertFalse(result["changed"]["provider"])
            self.assertTrue(result["changed"]["model"])
            self.assertTrue(result["changed"]["any"])

    def test_creation_model_can_be_inferred(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sid = "01a0d20e-ca6b-7b30-b6fe-4a4c12736b67"
            path = write_session(root, sid, [meta(sid, "sky_router"), settings("sky_router", "gpt-6-sol", "2026-09-24T00:01:00Z")])
            result = inspector.parse_session(path)
            self.assertEqual(result["created"]["model_source"], "first_thread_settings_applied")
            self.assertIn("creation_model_inferred_from_first_thread_settings", result["warnings"])

    def test_malformed_line_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sid = "01a0d20e-ca6b-7b30-b6fe-4a4c12736b67"
            path = write_session(root, sid, [meta(sid, "sky_router", "gpt-6-sol")])
            with path.open("a", encoding="utf-8") as handle:
                handle.write("{not-json}\n")
            result = inspector.parse_session(path)
            self.assertIn("malformed_jsonl_line:2", result["warnings"])

    def test_missing_thread_settings_is_incomplete(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sid = "01a0d20e-ca6b-7b30-b6fe-4a4c12736b67"
            path = write_session(root, sid, [meta(sid, "sky_router", "gpt-6-sol")])
            result = inspector.parse_session(path)
            self.assertIn("missing_thread_settings_applied", result["warnings"])
            self.assertIsNone(result["recent"]["provider"])

    def test_environment_resolves_current_session_first(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sid = "01a0d20e-ca6b-7b30-b6fe-4a4c12736b67"
            with mock.patch.dict(os.environ, {"CODEX_SESSION_ID": sid, "CODEX_THREAD_ID": "bad"}, clear=False):
                resolved, path, source = inspector.resolve_session_id(None, root, [])
            self.assertEqual(resolved, sid)
            self.assertIsNone(path)
            self.assertEqual(source, "env:CODEX_SESSION_ID")

    def test_cli_fails_closed_without_codex_runtime_marker(self):
        with tempfile.TemporaryDirectory() as temp:
            sid = "01a0d20e-ca6b-7b30-b6fe-4a4c12736b67"
            with mock.patch.dict(
                os.environ,
                {"CODEX_SESSION_ID": "", "CODEX_THREAD_ID": ""},
                clear=False,
            ):
                result = inspector.main([sid, "--codex-home", temp])
            self.assertEqual(result, 1)

    def test_explicit_session_file_lookup(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sid = "01a0d20e-ca6b-7b30-b6fe-4a4c12736b67"
            path = write_session(root, sid, [meta(sid, "sky_router", "gpt-6-sol")])
            warnings = []
            selected, source = inspector.choose_session_file(root, sid, warnings)
            self.assertEqual(selected, path)
            self.assertEqual(source, "exact_filename_match")


if __name__ == "__main__":
    unittest.main()
