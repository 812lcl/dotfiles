import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import handoff


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.repo = self.base / "repo"
        self.repo.mkdir()
        self.state = self.base / "state" / "task.json"
        self.git("init", "-q")
        (self.repo / "code.py").write_text("answer = 0\n")
        (self.repo / "user.txt").write_text("user-owned sentinel\n")
        self.git("add", ".")
        self.git("-c", "user.name=Runtime Fixture", "-c", "user.email=fixture@localhost", "commit", "-qm", "fixture")

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], stderr=subprocess.DEVNULL)

    def create(self):
        return handoff.create(self.state, self.repo, "codex", "finish fixture", "set answer", "work", ["user.txt"])

    def test_dirty_and_untracked_round_trip_without_git_mutations(self):
        initial_head = self.git("rev-parse", "HEAD")
        (self.repo / "code.py").write_text("answer = 1\n")
        (self.repo / "untracked.txt").write_text("keep me\n")
        self.create()
        handoff.release(self.state, "codex", 1)
        handoff.claim(self.state, "claude", 2)
        (self.repo / "code.py").write_text("answer = 2\n")
        handoff.release(self.state, "claude", 3, "review answer")
        handoff.claim(self.state, "codex", 4)
        self.assertTrue(handoff.inspect(self.state)["ok"])
        self.assertEqual(self.git("rev-parse", "HEAD"), initial_head)
        self.assertTrue((self.repo / "untracked.txt").is_file())
        self.assertNotIn("keep me", self.state.read_text())

    def test_owner_and_revision_conflicts(self):
        self.create()
        for operation in [lambda: handoff.claim(self.state, "claude", 1),
                          lambda: handoff.release(self.state, "claude", 1),
                          lambda: handoff.release(self.state, "codex", 99)]:
            with self.assertRaises(handoff.HandoffError):
                operation()

    def test_repeated_release_does_not_recapture_new_work(self):
        self.create()
        handoff.release(self.state, "codex", 1)
        before = self.state.read_bytes()
        (self.repo / "code.py").write_text("unexpected post-release change\n")
        with self.assertRaises(handoff.HandoffError):
            handoff.release(self.state, "codex", 2)
        self.assertEqual(self.state.read_bytes(), before)

    def test_moved_state_is_rejected_before_creating_repo_lock(self):
        self.create()
        moved = self.repo / "moved-task.json"
        self.state.rename(moved)
        before = moved.read_bytes()
        with self.assertRaises(handoff.HandoffError):
            handoff.release(moved, "codex", 1)
        self.assertEqual(moved.read_bytes(), before)
        self.assertFalse(Path(str(moved) + ".lock").exists())

    def test_claim_rejects_repo_state_through_parent_symlink_without_lock(self):
        self.create()
        handoff.release(self.state, "codex", 1)
        moved = self.repo / "moved-task.json"
        self.state.rename(moved)
        alias = self.base / "repo-alias"
        alias.symlink_to(self.repo, target_is_directory=True)
        before = moved.read_bytes()
        with self.assertRaises(handoff.HandoffError):
            handoff.claim(alias / moved.name, "claude", 2)
        self.assertEqual(moved.read_bytes(), before)
        self.assertFalse(Path(str(moved) + ".lock").exists())

    def test_concurrent_file_drift_refuses_claim(self):
        self.create()
        handoff.release(self.state, "codex", 1)
        (self.repo / "code.py").write_text("unexpected concurrent change\n")
        with self.assertRaises(handoff.HandoffError):
            handoff.claim(self.state, "claude", 2)
        self.assertEqual(handoff.load(self.state)["owner"], "codex")

    def test_protected_user_file_cannot_be_released_as_agent_work(self):
        self.create()
        (self.repo / "user.txt").write_text("changed\n")
        with self.assertRaises(handoff.HandoffError):
            handoff.release(self.state, "codex", 1)

    def test_symlinks_are_recorded_without_reading_target_content(self):
        target = self.base / "private.txt"
        target.write_text("PRIVATE-SENTINEL")
        (self.repo / "link.txt").symlink_to(target)
        self.create()
        data = handoff.load(self.state)
        self.assertEqual(data["snapshot"]["files"]["link.txt"]["kind"], "symlink")
        self.assertNotIn("PRIVATE-SENTINEL", self.state.read_text())

    def test_state_outside_worktree_and_private_permissions(self):
        with self.assertRaises(handoff.HandoffError):
            handoff.create(self.repo / "task.json", self.repo, "codex", "goal", "next", "work")
        self.create()
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
