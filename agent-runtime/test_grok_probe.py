import json
from pathlib import Path
import tempfile
import unittest

import grok_probe


class GrokEvidenceTests(unittest.TestCase):
    def stream(self, *events):
        return "\n".join(json.dumps(x) for x in events)

    def call(self):
        return {"type": "tool_call", "toolCallId": "t", "toolName": "bash",
                "rawInput": {"command": "PRIVATE-COMMAND"}}

    def done(self, status="completed", output=None):
        return {"type": "tool_call_update", "toolCallId": "t", "status": status,
                "rawOutput": output or {"Bash": {"exit_code": 0, "stdout": "PRIVATE-BODY"}}}

    def test_raw_outputs_signatures_and_thoughts_are_discarded(self):
        d = grok_probe.parse_stream(self.stream(self.call(), self.done(),
            {"type": "thought", "data": "PRIVATE-THOUGHT"},
            {"type": "usage", "signature": "PRIVATE-SIGNATURE"},
            {"type": "text", "data": "PRIVATE-ANSWER"}))
        self.assertEqual(d["tool_calls_succeeded"], 1)
        self.assertNotIn("PRIVATE-", json.dumps(d))

    def test_nonzero_shell_exit_and_failed_status_cannot_succeed(self):
        for end in [self.done(output={"Bash": {"exit_code": 1}}), self.done(status="failed")]:
            d = grok_probe.parse_stream(self.stream(self.call(), end))
            self.assertEqual(d["tool_calls_failed"], 1)

    def test_partial_update_is_not_a_completed_call(self):
        d = grok_probe.parse_stream(self.stream(self.call(), self.done(status=None)))
        self.assertEqual(d["pending_calls"], 1)
        self.assertEqual(d["tool_calls_succeeded"], 0)

    def test_duplicate_and_unmatched_updates_are_protocol_errors(self):
        for events in [(self.done(),), (self.call(), self.done(), self.done())]:
            d = grok_probe.parse_stream(self.stream(*events))
            self.assertGreater(d["protocol_errors"], 0)

    def test_model_prose_cannot_replace_completion(self):
        d = grok_probe.parse_stream(self.stream({"type": "text", "data": "all passed"}))
        self.assertEqual(grok_probe.status(d, 0, False), "incomplete")

    def test_turn_limit_is_not_a_success(self):
        d = grok_probe.parse_stream(self.stream({"type": "available_commands", "commands": []},
            {"type": "end", "stopReason": "max_turns"}))
        self.assertEqual(grok_probe.status(d, 0, False), "runtime_limit_or_error")

    def test_timeout_takes_precedence_over_completion(self):
        d = grok_probe.parse_stream(self.stream({"type": "end", "stopReason": "end_turn"}))
        self.assertEqual(grok_probe.status(d, 0, True), "timeout")

    def test_unsupported_additional_roots_are_rejected_before_starting(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "additionalDirectories"):
                grok_probe.run_grok("verify", Path(directory), add_dirs=[directory])


if __name__ == "__main__":
    unittest.main()
