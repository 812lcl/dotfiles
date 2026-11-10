import json
import unittest

import cursor_probe


class CursorEvidenceTests(unittest.TestCase):
    def stream(self, *events):
        return "\n".join(json.dumps(e) for e in events)

    def tool(self, subtype, result=None, ident="t", args=None):
        value = {"args": args or {"command": "verify"}}
        if result is not None:
            value["result"] = result
        return {"type": "tool_call", "subtype": subtype, "call_id": ident,
                "tool_call": {"shellToolCall": value}}

    def test_private_results_and_thinking_are_not_persisted(self):
        raw = self.stream({"type": "thinking", "text": "PRIVATE-THINKING"},
                          self.tool("started"),
                          self.tool("completed", {"success": {"output": "PRIVATE-MEMORY", "exitCode": 0}}),
                          {"type": "result", "subtype": "success", "result": "PRIVATE-ANSWER"})
        data = cursor_probe.parse_stream(raw)
        self.assertEqual(data["tool_calls_succeeded"], 1)
        self.assertNotIn("PRIVATE-", json.dumps(data))

    def test_shell_nonzero_is_a_failure_even_with_success_envelope(self):
        data = cursor_probe.parse_stream(self.stream(
            self.tool("started"), self.tool("completed", {"success": {"exitCode": 3}})))
        self.assertEqual(data["tool_calls_failed"], 1)

    def test_unmatched_or_duplicate_result_is_not_trusted(self):
        end = self.tool("completed", {"success": {}})
        for events in [(end,), (self.tool("started"), end, end)]:
            data = cursor_probe.parse_stream(self.stream(*events))
            self.assertGreater(data["protocol_errors"], 0)

    def test_changed_input_is_not_a_matching_result(self):
        data = cursor_probe.parse_stream(self.stream(self.tool("started"),
            self.tool("completed", {"success": {}}, args={"command": "other"})))
        self.assertEqual(data["protocol_errors"], 1)

    def test_unknown_envelope_cannot_be_called_success(self):
        data = cursor_probe.parse_stream(self.stream(self.tool("started"),
                                                    self.tool("completed", {"unexpected": {}})))
        self.assertEqual(data["unknown_tool_results"], 1)
        self.assertEqual(data["tool_calls_succeeded"], 0)

    def test_prose_claim_without_runtime_result_is_incomplete(self):
        data = cursor_probe.parse_stream(self.stream({"type": "assistant", "message": {"content": "passed"}}))
        self.assertEqual(cursor_probe.status(data, 0, False), "incomplete")

    def test_timeout_overrides_a_success_event(self):
        data = cursor_probe.parse_stream(self.stream({"type": "result", "subtype": "success"}))
        self.assertEqual(cursor_probe.status(data, 0, True), "timeout")


if __name__ == "__main__":
    unittest.main()
