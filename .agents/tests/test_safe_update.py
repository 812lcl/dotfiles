import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'safe-skills-update.sh'


class SafeUpdateTests(unittest.TestCase):
    def run_update(self, root, *args):
        bins = root / 'bin'
        bins.mkdir(exist_ok=True)
        mock = bins / 'npx'
        mock.write_text('#!/bin/sh\npwd > "$UPDATE_TRACE"\nprintf "%s\\n" "$@" >> "$UPDATE_TRACE"\nexit "${UPDATE_EXIT:-0}"\n')
        mock.chmod(0o755)
        env = {**os.environ, 'SKILL_SOURCE_ROOT': str(root),
               'UPDATE_TRACE': str(root / 'trace'), 'PATH': str(bins) + os.pathsep + os.environ['PATH']}
        return subprocess.run(['bash', str(SCRIPT), *args], env=env, capture_output=True, text=True)

    def test_updates_source_in_project_scope_and_passes_skill_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'skills-lock.json').write_text(json.dumps({'version': 2, 'skills': {}}))
            result = self.run_update(root, 'book-review', '--yes')
            self.assertEqual(result.returncode, 0, result.stderr)
            trace = (root / 'trace').read_text().splitlines()
            self.assertEqual(Path(trace[0]).resolve(), root.resolve())
            self.assertEqual(trace[1:], ['skills', 'update', '--project', 'book-review', '--yes'])

    def test_missing_source_lock_never_falls_back_to_global(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertNotEqual(self.run_update(root).returncode, 0)
            self.assertFalse((root / 'trace').exists())

    def test_rejects_global_scope_before_starting_npx(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'skills-lock.json').write_text('{}')
            self.assertEqual(self.run_update(root, '--global').returncode, 2)
            self.assertFalse((root / 'trace').exists())


if __name__ == '__main__':
    unittest.main()
