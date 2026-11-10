import json
from pathlib import Path
import tempfile
import unittest

import baseline


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.addCleanup(self.temp.cleanup)

    def test_content_membership_and_mode_changes_are_detected(self):
        folder = self.root / "skills"
        folder.mkdir()
        source = folder / "SKILL.md"
        source.write_text("private contents are never copied into the report")
        before = baseline.capture([folder])
        self.assertTrue(baseline.compare(before, baseline.capture([folder]))["ok"])
        self.assertNotIn("private contents", json.dumps(before))
        source.write_text("new contents")
        self.assertIn(str(source), baseline.compare(before, baseline.capture([folder]))["changed"])
        before = baseline.capture([folder])
        source.chmod(0o700)
        self.assertIn(str(source), baseline.compare(before, baseline.capture([folder]))["changed"])
        added = folder / "new.py"
        added.write_text("pass\n")
        self.assertIn(str(added), baseline.compare(before, baseline.capture([folder]))["added"])
        source.unlink()
        self.assertIn(str(source), baseline.compare(before, baseline.capture([folder]))["removed"])

    def test_missing_root_creation_is_detected(self):
        missing = self.root / "not-installed"
        before = baseline.capture([missing])
        self.assertEqual(before["entries"][str(missing)]["type"], "missing")
        self.assertFalse(before["errors"])
        missing.write_text("now configured")
        self.assertIn(str(missing), baseline.compare(before, baseline.capture([missing]))["changed"])

    def test_symlink_content_target_and_target_permissions_are_protected(self):
        first, second = self.root / "first", self.root / "second"
        first.mkdir(); second.mkdir()
        for folder in (first, second):
            (folder / "SKILL.md").write_text("same text")
        alias = self.root / "alias"
        alias.symlink_to(first, target_is_directory=True)
        before = baseline.capture([alias])
        self.assertIn(str(alias / "SKILL.md"), before["entries"])
        (first / "SKILL.md").write_text("edited")
        self.assertIn(str(alias / "SKILL.md"), baseline.compare(before, baseline.capture([alias]))["changed"])
        alias.unlink(); alias.symlink_to(second, target_is_directory=True)
        self.assertIn(str(alias), baseline.compare(before, baseline.capture([alias]))["changed"])
        before = baseline.capture([alias])
        second.chmod(0o700)
        self.assertIn(str(alias), baseline.compare(before, baseline.capture([alias]))["changed"])

    def test_ancestor_alias_is_recorded_without_scanning_unrelated_children(self):
        canonical = self.root / "canonical"
        (canonical / "skills").mkdir(parents=True)
        (canonical / "skills/SKILL.md").write_text("a skill")
        (canonical / "not-in-scope.txt").write_text("unrelated")
        alias = self.root / "agents"
        alias.symlink_to(canonical, target_is_directory=True)
        snapshot = baseline.capture([alias / "skills"])
        self.assertEqual(snapshot["entries"][str(alias)]["type"], "symlink")
        self.assertNotIn(str(alias / "not-in-scope.txt"), snapshot["entries"])

    def test_broken_links_and_directory_cycles_fail_closed(self):
        broken = self.root / "broken"
        broken.symlink_to(self.root / "missing")
        result = baseline.capture([broken])
        self.assertTrue(result["errors"])
        self.assertFalse(baseline.compare(result, result)["ok"])
        folder = self.root / "cycle"
        folder.mkdir()
        (folder / "back").symlink_to(folder, target_is_directory=True)
        result = baseline.capture([folder])
        self.assertTrue(any(item["code"] == "directory_cycle" for item in result["errors"]))

    def test_pycache_and_git_changes_are_ignored(self):
        folder = self.root / "source"
        folder.mkdir()
        (folder / "code.py").write_text("pass\n")
        before = baseline.capture([folder])
        for name in ("__pycache__", ".git", ".cache"):
            (folder / name).mkdir()
            (folder / name / "transient").write_text("runtime")
        (folder / "old.pyc").write_bytes(b"compiled")
        (folder / ".DS_Store").write_bytes(b"finder")
        self.assertTrue(baseline.compare(before, baseline.capture([folder]))["ok"])

    def test_scope_changes_are_not_silently_accepted(self):
        a, b = self.root / "a", self.root / "b"
        result = baseline.compare(baseline.capture([a]), baseline.capture([b]))
        self.assertFalse(result["ok"])
        self.assertTrue(any(item.get("code") == "capture_scope_changed" for item in result["errors"]))

    def test_default_scope_does_not_scan_dynamic_codex_data(self):
        home, vault = self.root / "home", self.root / "vault"
        roots = baseline.default_codex_paths(home, vault)
        self.assertIn(home / ".codex/config.toml", roots)
        self.assertIn(home / ".agents/skills", roots)
        self.assertNotIn(home / ".codex", roots)
        self.assertFalse(any(path.name in {"auth.json", "sessions", "memories_v2", "plugins"}
                             for path in roots))


if __name__ == "__main__":
    unittest.main()
