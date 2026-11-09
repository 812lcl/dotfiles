import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('lifecycle', Path(__file__).with_name('brain-lifecycle.py'))
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.vault = self.base / 'vault'
        self.vault.mkdir()
        self.brain = self.make_brain(self.vault / 'brain')
        self.work = self.base / 'work'
        self.work.mkdir()
        self.work_brain = self.make_brain(self.base / '.brain')
        (self.work / 'brain').symlink_to(self.work_brain)

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, cwd, *args):
        subprocess.run(['git', '-C', str(cwd), *args], check=True, capture_output=True)

    def make_brain(self, p):
        p.mkdir()
        self.git(p, 'init', '-q')
        (p / 'BRAIN.md').write_text('test\n')
        return p

    def test_personal_subdirectory(self):
        p = self.vault / 'notes'; p.mkdir()
        self.assertEqual(hook.select_brain(p), self.brain)

    def test_work_symlink(self):
        self.assertEqual(hook.select_brain(self.work), self.work_brain)

    def test_inherited_brain_cannot_redirect_work(self):
        with patch.dict(os.environ, {'BRAIN_DIR': str(self.brain)}):
            self.assertEqual(hook.select_brain(self.work), self.work_brain)

    def test_unknown_directory_does_not_use_global_or_env(self):
        p = self.base / 'unknown'; p.mkdir()
        with patch.dict(os.environ, {'BRAIN_DIR': str(self.brain)}):
            self.assertIsNone(hook.select_brain(p))

    def test_invalid_nested_brain_does_not_fall_back(self):
        p = self.vault / 'nested'; p.mkdir(); (p / 'brain').mkdir()
        with self.assertRaises(ValueError):
            hook.select_brain(p)

    def test_brain_must_be_independent_git_root(self):
        self.git(self.vault, 'init', '-q')
        bad = self.vault / 'nested'; bad.mkdir(); b = bad / 'brain'; b.mkdir()
        (b / 'BRAIN.md').write_text('not an independent repo')
        with self.assertRaises(ValueError):
            hook.select_brain(bad)

    def test_worktree_resolves_owning_checkout(self):
        self.git(self.vault, 'init', '-q')
        self.git(self.vault, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '--allow-empty', '-m', 'fixture')
        wt = self.base / 'linked'
        self.git(self.vault, 'worktree', 'add', '--detach', str(wt), 'HEAD')
        self.assertEqual(hook.select_brain(wt), self.brain)

    def test_lifecycle_passes_root_explicitly_and_stop_is_quiet(self):
        real_run = subprocess.run
        calls = []
        def fake_run(cmd, **kw):
            if cmd[0] != 'brain':
                return real_run(cmd, **kw)
            calls.append((cmd, kw))
            stdout = json.dumps({'hookSpecificOutput': {'additionalContext': 'reminder'}}) if cmd[-1] == 'user-prompt-submit' else 'preferences\n'
            return subprocess.CompletedProcess(cmd, 0, stdout, '')
        with patch.object(hook.subprocess, 'run', side_effect=fake_run):
            for event in ['SessionStart', 'UserPromptSubmit', 'Stop']:
                out = io.StringIO()
                with redirect_stdout(out):
                    hook.handle({'hook_event_name': event, 'cwd': str(self.work)})
                if event == 'UserPromptSubmit':
                    context = json.loads(out.getvalue())['hookSpecificOutput']['additionalContext']
                    self.assertIn(str(self.work_brain), context)
                    self.assertIn('reminder', context)
                else:
                    self.assertEqual(out.getvalue(), '' if event == 'Stop' else 'preferences\n')
        self.assertEqual(len(calls), 3)
        for cmd, kw in calls:
            self.assertEqual(cmd[:3], ['brain', '--brain-dir', str(self.work_brain)])
            self.assertEqual(kw['env']['BRAIN_DIR'], str(self.work_brain))
        self.assertEqual(calls[-1][0][3:], ['hook', 'stop'])


if __name__ == '__main__':
    unittest.main()
