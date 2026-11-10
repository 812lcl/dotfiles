import json
import subprocess
import unittest
from unittest.mock import patch

import opencode_probe


class OpenCodeEvidenceTests(unittest.TestCase):
    def tool(self, status="completed", metadata=None):
        return {"type": "tool_use", "part": {"partID": "t", "type": "tool", "tool": "shell",
                "state": {"status": status, "input": {"command": "PRIVATE-INPUT"},
                          "output": "PRIVATE-OUTPUT", "metadata": metadata or {}}}}

    def parse(self, *events, **kwargs):
        return opencode_probe.parse_stream("\n".join(json.dumps(x) for x in events), **kwargs)

    def test_private_content_and_reasoning_are_discarded(self):
        d = self.parse(self.tool(), {"type": "reasoning", "part": {"text": "PRIVATE-THOUGHT"}},
                       {"type": "text", "part": {"text": "PRIVATE-ANSWER"}})
        self.assertEqual(d["tool_calls_succeeded"], 1)
        self.assertNotIn("PRIVATE-", json.dumps(d))

    def test_nonzero_shell_exit_cannot_be_success(self):
        d = self.parse(self.tool(metadata={"metadata": {"exitCode": 3}}))
        self.assertEqual(d["tool_calls_failed"], 1)

    def test_tool_error_is_not_hidden_by_stop(self):
        d = self.parse({"type": "step_start"}, self.tool(status="error"),
                       {"type": "step_finish", "part": {"reason": "stop"}})
        self.assertEqual(opencode_probe.status(d, 0, False), "completed_with_tool_errors")

    def test_duplicate_completion_is_a_protocol_error(self):
        self.assertEqual(self.parse(self.tool(), self.tool())["protocol_errors"], 1)

    def test_unfinished_tool_and_no_final_step_are_incomplete(self):
        d = self.parse({"type": "step_start"}, self.tool(status="running"))
        self.assertEqual(opencode_probe.status(d, 0, False), "incomplete")

    def test_tool_call_step_is_not_final_completion(self):
        d = self.parse({"type": "step_start"}, {"type": "step_finish", "part": {"reason": "tool-calls"}})
        self.assertEqual(opencode_probe.status(d, 0, False), "runtime_limit_or_error")

    def test_timeout_overrides_normal_finish(self):
        d = self.parse({"type": "step_start"}, {"type": "step_finish", "part": {"reason": "stop"}})
        self.assertEqual(opencode_probe.status(d, 0, True), "timeout")

    def test_probe_permissions_use_v2_rules_and_no_subagents(self):
        rules = opencode_probe.SESSION_PERMISSIONS
        self.assertEqual(rules[0], {"action": "*", "resource": "*", "effect": "deny"})
        self.assertNotIn("subagent", [x["action"] for x in rules[1:]])
        self.assertIn("skill", [x["action"] for x in rules[1:]])

    def test_successful_no_content_api_response_is_valid(self):
        result = subprocess.CompletedProcess([], 0, "", "")
        with patch.object(opencode_probe.subprocess, "run", return_value=result):
            self.assertIsNone(opencode_probe.api("opencode", "session.update", "/tmp"))

    def test_api_failure_does_not_expose_stderr_or_credentials(self):
        result = subprocess.CompletedProcess([], 1, "", "PRIVATE-TOKEN")
        with patch.object(opencode_probe.subprocess, "run", return_value=result):
            with self.assertRaises(ValueError) as error:
                opencode_probe.api("opencode", "session.create", "/tmp")
        self.assertNotIn("PRIVATE-", str(error.exception))


if __name__ == "__main__":
    unittest.main()
