from pathlib import Path
import json
import tempfile
import unittest

import config_policy


class ConfigPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "config.toml"

    def snap(self, value):
        self.path.write_text(value)
        return config_policy.capture(self.path)

    def test_only_top_level_model_and_reasoning_are_ignored(self):
        a = self.snap('model="first"\nmodel_reasoning_effort="high"\nservice_tier="default"\n')
        b = self.snap('model="second"\nmodel_reasoning_effort="medium"\nservice_tier="default"\n')
        self.assertTrue(config_policy.compare(a, b)["ok"])
        self.assertTrue(config_policy.compare(a, b)["raw_changed"])

    def test_provider_mcp_and_nested_model_changes_remain_protected(self):
        base = 'model="first"\n[provider]\nmodel="nested"\n[mcp_servers.test]\ncommand="tool"\n'
        a = self.snap(base)
        for replacement in [base.replace('nested', 'different'), base.replace('command="tool"', 'command="other"')]:
            b = self.snap(replacement)
            self.assertFalse(config_policy.compare(a, b)["ok"])

    def test_removing_model_selectors_and_formatting_do_not_change_policy(self):
        a = self.snap('model="first"\nmodel_reasoning_effort="high"\nservice_tier="default"\n')
        b = self.snap('# comment\nservice_tier = "default"\n')
        self.assertTrue(config_policy.compare(a, b)["ok"])

    def test_other_top_level_fields_and_permissions_are_protected(self):
        a = self.snap('service_tier="default"\n')
        b = self.snap('service_tier="fast"\n')
        self.assertFalse(config_policy.compare(a, b)["ok"])
        b = self.snap('service_tier="default"\n')
        b["mode"] ^= 0o100
        self.assertFalse(config_policy.compare(a, b)["ok"])

    def test_secret_values_are_not_persisted(self):
        a = self.snap('[mcp_servers.test.env]\nTOKEN="PRIVATE-SENTINEL"\n')
        self.assertNotIn('PRIVATE-SENTINEL', json.dumps(a))

    def test_snapshot_policy_preserves_raw_drift_and_filters_only_config(self):
        a = self.snap('model="first"\n')
        b = self.snap('model="second"\n')
        path = str(self.path)
        before = {"codex_config_policy": a, "entries": {path: {"type": "file", "sha256": "a", "mode": 0o600}}}
        after = {"codex_config_policy": b, "entries": {path: {"type": "file", "sha256": "b", "mode": 0o600}}}
        raw = {"ok": False, "added": [], "removed": [], "changed": [path], "errors": []}
        result = config_policy.apply_to_comparison(raw, before, after, self.path)
        self.assertTrue(result["ok"])
        self.assertEqual(result["observed_raw_changed"], [path])
        self.assertEqual(raw["changed"], [path])
        after["entries"][path]["mode"] = 0o644
        self.assertFalse(config_policy.apply_to_comparison(raw, before, after, self.path)["ok"])

    def test_old_snapshot_has_no_field_level_evidence(self):
        raw = {"ok": False, "changed": [str(self.path)]}
        self.assertEqual(config_policy.apply_to_comparison(raw, {}, {}, self.path), raw)


if __name__ == "__main__":
    unittest.main()
