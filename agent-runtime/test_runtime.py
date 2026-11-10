import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import runtime


class RuntimePathTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.home = self.base / "home"
        self.home.mkdir()
        self.state = self.base / "state"
        self.state.mkdir()
        self.snapshot = self.state / "baseline.json"
        self.snapshot.write_text(json.dumps({
            "schema_version": 1, "roots": [], "entries": {}, "errors": [],
        }))

    def cli(self, *arguments, state=None):
        stdout = io.StringIO()
        with patch.object(runtime.Path, "home", return_value=self.home), \
                patch("sys.argv", ["runtime", "--state-dir", str(state or self.state), *arguments]), \
                contextlib.redirect_stdout(stdout):
            result = runtime.main()
        return result, json.loads(stdout.getvalue())

    def check(self, output, **kwargs):
        return self.cli("baseline", "check", "--snapshot", str(self.snapshot),
                        "--output", str(output), **kwargs)

    def test_baseline_check_cannot_overwrite_input_or_hardlink_alias(self):
        before = self.snapshot.read_bytes()
        code, _ = self.check(self.snapshot)
        self.assertEqual(code, 2)
        alias = self.state / "snapshot-hardlink.json"
        os.link(self.snapshot, alias)
        code, _ = self.check(alias)
        self.assertEqual(code, 2)
        self.assertEqual(self.snapshot.read_bytes(), before)
        self.assertEqual(alias.read_bytes(), before)

    def test_output_outside_state_is_not_created_or_overwritten(self):
        outside = self.base / "outside.json"
        outside.write_text("user sentinel")
        code, _ = self.check(outside)
        self.assertEqual(code, 2)
        self.assertEqual(outside.read_text(), "user sentinel")
        missing = self.base / "new-dir" / "report.json"
        code, _ = self.check(missing)
        self.assertEqual(code, 2)
        self.assertFalse(missing.parent.exists())

    def test_parent_symlink_escape_is_rejected(self):
        external = self.base / "external"
        external.mkdir()
        alias = self.state / "escape"
        alias.symlink_to(external, target_is_directory=True)
        code, _ = self.check(alias / "report.json")
        self.assertEqual(code, 2)
        self.assertEqual(list(external.iterdir()), [])

    def test_codex_source_is_protected_even_with_home_as_state_dir(self):
        protected = self.home / ".codex/hooks.json"
        protected.parent.mkdir()
        protected.write_text("codex sentinel")
        code, _ = self.check(protected, state=self.home)
        self.assertEqual(code, 2)
        self.assertEqual(protected.read_text(), "codex sentinel")
        code, _ = self.cli("init", state=protected.parent)
        self.assertEqual(code, 2)
        self.assertFalse((protected.parent / "profiles.json").exists())

    def test_symlink_to_shared_sources_is_protected_for_initialization(self):
        shared = self.home / "Code/dotfiles/.agents"
        shared.mkdir(parents=True)
        (self.home / ".agents").symlink_to(shared, target_is_directory=True)
        state_alias = self.base / "shared-alias"
        state_alias.symlink_to(shared, target_is_directory=True)
        code, _ = self.cli("init", state=state_alias)
        self.assertEqual(code, 2)
        self.assertFalse((shared / "profiles.json").exists())

    def test_handoff_outside_state_fails_before_any_lock_creation(self):
        outside = self.base / "task.json"
        code, _ = self.cli("handoff", "create", "--file", str(outside),
                           "--root", str(self.base), "--owner", "codex",
                           "--goal", "fixture", "--next-step", "continue", "--scope", "work")
        self.assertEqual(code, 2)
        self.assertFalse(outside.exists())
        self.assertFalse(Path(str(outside) + ".lock").exists())

    def test_backup_outside_state_is_rejected_before_adapter_runs(self):
        outside = self.base / "backups"
        with patch.object(runtime.claude_adapter, "apply") as apply:
            code, _ = self.cli("claude-mcp", "apply", "--backup-dir", str(outside))
        self.assertEqual(code, 2)
        apply.assert_not_called()
        self.assertFalse(outside.exists())

    def test_valid_report_preserves_baseline_and_has_private_permissions(self):
        before = self.snapshot.read_bytes()
        output = self.state / "reports/check.json"
        code, result = self.check(output)
        self.assertEqual(code, 0)
        self.assertTrue(result["ok"])
        self.assertTrue(json.loads(output.read_text())["ok"])
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.snapshot.read_bytes(), before)

    def test_new_baseline_ignores_model_selectors_but_detects_mcp_change(self):
        config = self.home / ".codex/config.toml"
        config.parent.mkdir(parents=True)
        original = 'model="first"\nmodel_reasoning_effort="high"\n[mcp_servers.test]\ncommand="tool"\n'
        config.write_text(original)
        snapshot = self.state / "policy.json"
        code, _ = self.cli("baseline", "capture", "--vault-root", str(self.base / "vault"),
                           "--output", str(snapshot))
        self.assertEqual(code, 0)
        config.write_text(original.replace('first', 'second').replace('high', 'medium'))
        code, result = self.cli("baseline", "check", "--snapshot", str(snapshot))
        self.assertEqual(code, 0)
        self.assertTrue(result["codex_config_policy"]["ok"])
        self.assertIn(str(config), result["observed_raw_changed"])
        config.write_text(original.replace('command="tool"', 'command="different"'))
        code, result = self.cli("baseline", "check", "--snapshot", str(snapshot))
        self.assertEqual(code, 2)
        self.assertIn(str(config), result["changed"])


if __name__ == "__main__":
    unittest.main()
