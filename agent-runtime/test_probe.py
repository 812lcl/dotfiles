import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import probe


def stream(*events):
    return "\n".join(json.dumps(event) for event in events)


class ProbeTests(unittest.TestCase):
    def test_allowlisted_evidence_links_tool_result_without_secret_content(self):
        secret = "DO-NOT-KEEP-secret-provider-payload"
        output = stream(
            {"type": "system", "subtype": "init", "cwd": "/tmp/fixture",
             "model": "fixture-model", "claude_code_version": "fixture-version",
             "skills": ["brain", "multi-repo-maintenance"], "tools": ["Read"],
             "slash_commands": ["brain"], "apiKeySource": secret,
             "mcp_servers": [{"name": "fixture", "status": "connected", "auth": secret}],
             "plugins": [{"name": "fixture-plugin", "path": secret}]},
            {"type": "assistant", "message": {"content": [
                {"type": "text", "text": secret},
                {"type": "tool_use", "id": "call-1", "name": "Read", "input": {"file": secret}}]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "call-1", "content": secret, "is_error": False}]}},
            {"type": "result", "subtype": "success", "is_error": False,
             "duration_ms": 12, "num_turns": 2, "total_cost_usd": 0.01, "result": secret})
        evidence = probe.parse_stream(output)
        self.assertNotIn(secret, json.dumps(evidence))
        self.assertEqual(evidence["tool_calls_succeeded"], 1)
        self.assertTrue(evidence["tool_results"][0]["matched"])
        self.assertEqual(evidence["tool_results"][0]["name"], "Read")
        self.assertEqual(len(evidence["tool_uses"][0]["input_sha256"]), 64)
        self.assertEqual(evidence["init"]["plugins"], ["fixture-plugin"])
        self.assertEqual(probe._status(evidence, 0, False), "completed")

    def test_init_alone_and_unmatched_results_are_not_call_success(self):
        evidence = probe.parse_stream(stream(
            {"type": "system", "subtype": "init", "skills": ["brain"]},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "missing", "content": "ok"}]}}))
        self.assertTrue(evidence["initialized"])
        self.assertEqual(evidence["tool_calls_succeeded"], 0)
        self.assertEqual(evidence["unmatched_tool_results"], 1)
        self.assertEqual(probe._status(evidence, 0, False), "incomplete")

    def test_runtime_errors_permission_denial_and_non_json_are_explicit_and_redacted(self):
        for event, status in [
            ({"type": "result", "subtype": "error_during_execution", "is_error": True,
              "errors": ["secret-api-key"]}, "runtime_error"),
            ({"type": "result", "subtype": "error_max_turns", "is_error": True}, "turn_limit"),
            ({"type": "result", "subtype": "error_max_budget_usd", "is_error": True}, "budget_limit"),
            ({"type": "refusal", "message": "secret-api-key"}, "refused"),
            ({"type": "result", "subtype": "success", "permission_denials": [
                {"tool_input": "secret-api-key"}]}, "permission_denied"),
        ]:
            with self.subTest(status=status):
                evidence = probe.parse_stream(stream(event))
                self.assertEqual(probe._status(evidence, 0, False), status)
                self.assertNotIn("secret-api-key", json.dumps(evidence))
        evidence = probe.parse_stream("secret-api-key\n" + stream({"type": "result", "subtype": "success"}))
        self.assertEqual(probe._status(evidence, 0, False), "protocol_error")
        self.assertNotIn("secret-api-key", json.dumps(evidence))

    def test_optional_fixture_text_is_bounded(self):
        evidence = probe.parse_stream(stream({"type": "result", "subtype": "success", "result": "x" * 5000}), capture_text=True)
        self.assertEqual(len(evidence["result"]["text"]), 4000)
        self.assertTrue(evidence["result"]["text_truncated"])

    def test_launch_uses_stdin_session_overlay_and_no_environment_override(self):
        child = Mock(pid=1234, returncode=0)
        child.communicate.return_value = (stream({"type": "result", "subtype": "success"}), "secret-stderr")
        with tempfile.TemporaryDirectory() as cwd, patch.object(probe.subprocess, "Popen", return_value=child) as spawn:
            evidence = probe.run_claude("secret-prompt", cwd, ["Read"], ["Read"], ["mcp__*"], claude_path="/fixture/claude")
        command = spawn.call_args.args[0]
        self.assertNotIn("secret-prompt", command)
        self.assertNotIn("--bare", command)
        self.assertNotIn("--safe-mode", command)
        self.assertNotIn("env", spawn.call_args.kwargs)
        self.assertTrue(spawn.call_args.kwargs["start_new_session"])
        self.assertEqual(json.loads(command[command.index("--settings") + 1]),
                         {"disableAllHooks": True, "autoMemoryEnabled": False})
        self.assertEqual(child.communicate.call_args.kwargs["input"], "secret-prompt")
        self.assertEqual(evidence["status"], "completed")
        self.assertTrue(evidence["stderr_present"])
        self.assertNotIn("secret", json.dumps(evidence))

    def test_timeout_escalates_only_own_process_group_and_retains_timeout_status(self):
        child = Mock(pid=43210, returncode=-9)
        child.communicate.side_effect = [
            subprocess.TimeoutExpired("fixture", 0.1),
            subprocess.TimeoutExpired("fixture", 2),
            (stream({"type": "result", "subtype": "success"}), "private failure"),
        ]
        with tempfile.TemporaryDirectory() as cwd, patch.object(probe.subprocess, "Popen", return_value=child), patch.object(probe.os, "killpg") as kill:
            evidence = probe.run_claude("fixture", cwd, [], [], timeout_seconds=0.1, claude_path="/fixture/claude")
        self.assertEqual(kill.call_args_list[0].args, (43210, signal.SIGTERM))
        self.assertTrue(any(call.args == (43210, signal.SIGKILL) for call in kill.call_args_list))
        self.assertTrue(all(call.args[0] == 43210 for call in kill.call_args_list))
        self.assertEqual(evidence["status"], "timeout")
        self.assertTrue(evidence["timed_out"])
        self.assertEqual(child.communicate.call_count, 3)

    def test_failed_tool_is_not_success_and_duplicate_results_do_not_double_count(self):
        evidence = probe.parse_stream(stream(
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "x", "name": "Read", "input": {}}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "x", "is_error": True, "content": "private"}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "x", "content": "private"}]}},
            {"type": "result", "subtype": "success"}))
        self.assertEqual(evidence["tool_calls_succeeded"], 0)
        self.assertEqual(evidence["tool_calls_failed"], 1)
        self.assertIn("duplicate_tool_result", evidence["errors"])

    def test_spawn_failure_does_not_expose_exception_text(self):
        with tempfile.TemporaryDirectory() as cwd, patch.object(probe.subprocess, "Popen", side_effect=OSError("secret")):
            evidence = probe.run_claude("fixture", cwd, [], [], claude_path="/fixture/claude")
        self.assertEqual(evidence["status"], "spawn_error")
        self.assertNotIn("secret", json.dumps(evidence))

    def test_real_fake_executable_reads_stdin_and_returns_redacted_evidence(self):
        with tempfile.TemporaryDirectory() as cwd:
            fake = Path(cwd) / "fake-claude"
            fake.write_text(
                f"#!{sys.executable}\n"
                "import json, sys\n"
                "prompt = sys.stdin.read()\n"
                "print(json.dumps({'type':'system','subtype':'init','skills':['brain'],'tools':['Read']}))\n"
                "print(json.dumps({'type':'assistant','message':{'content':[{'type':'tool_use','id':'fixture-1','name':'Read','input':{'value':prompt}}]}}))\n"
                "print(json.dumps({'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':'fixture-1','content':prompt}]}}))\n"
                "print(json.dumps({'type':'result','subtype':'success','num_turns':2,'result':prompt}))\n")
            fake.chmod(0o700)
            evidence = probe.run_claude("fixture-private-text", cwd, ["Read"], ["Read"], claude_path=fake)
        self.assertEqual(evidence["status"], "completed")
        self.assertTrue(evidence["initialized"])
        self.assertEqual(evidence["tool_calls_succeeded"], 1)
        self.assertEqual(evidence["tool_results"][0]["result_sha256"], probe._sha("fixture-private-text"))
        self.assertNotIn("fixture-private-text", json.dumps(evidence))


if __name__ == "__main__":
    unittest.main()
