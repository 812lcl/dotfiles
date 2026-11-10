import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import brain_hooks


class BrainHookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ('vault', 'work', 'elsewhere'):
            (self.root / name).mkdir()
        self.profiles = {'cursor': {'workspaces': {
            'vault': {'root': str(self.root / 'vault'), 'brain_scope': 'personal'},
            'work': {'root': str(self.root / 'work'), 'brain_scope': 'work'}}},
            'brain': {'personal': {'root': str(self.root / 'vault')},
                      'work': {'root': str(self.root / 'work')}}}

    def test_unknown_and_mixed_roots_never_fall_back(self):
        for paths in ([], [str(self.root / 'elsewhere')], ['relative'],
                      [str(self.root / 'vault'), str(self.root / 'work')]):
            with self.assertRaises(ValueError):
                brain_hooks.scope_for(paths, self.profiles)

    def test_scopes_and_subdirectories(self):
        child = self.root / 'work/sub'; child.mkdir()
        self.assertEqual(brain_hooks.scope_for([str(child)], self.profiles), 'work')
        self.assertEqual(brain_hooks.scope_for([str(self.root / 'vault')], self.profiles), 'personal')

    def test_linked_worktree_uses_owning_project(self):
        repo = self.root / 'work/repo'
        subprocess.run(['git', 'init', '-q', str(repo)], check=True)
        subprocess.run(['git', '-C', str(repo), '-c', 'user.name=Fixture', '-c',
                        'user.email=fixture@example.invalid', 'commit', '-qm', 'empty', '--allow-empty'], check=True)
        linked = self.root / 'linked'
        subprocess.run(['git', '-C', str(repo), 'worktree', 'add', '-qb', 'fixture', str(linked)], check=True)
        self.assertEqual(brain_hooks.scope_for([str(linked)], self.profiles), 'work')

    def handle(self, client, event, scope='work'):
        payload = {'cwd': str(self.root / ('work' if scope == 'work' else 'vault'))}
        with patch.object(brain_hooks.runtime, 'profiles', return_value=self.profiles), \
             patch.object(brain_hooks.runtime, 'brain_call'), \
             patch.object(brain_hooks, 'context', return_value='SCOPED-CONTEXT'), \
             patch.object(brain_hooks, 'brain_command') as command:
            result = brain_hooks.handle(client, event, payload)
        return result, command

    def test_context_uses_native_client_vocabulary(self):
        self.assertEqual(self.handle('cursor', 'sessionStart')[0], {'additional_context': 'SCOPED-CONTEXT'})
        self.assertEqual(self.handle('opencode', 'context')[0], {'context': 'SCOPED-CONTEXT'})
        self.assertEqual(self.handle('grok', 'PreToolUse')[0]['hookSpecificOutput']['hookEventName'], 'PreToolUse')

    def test_stop_is_nonblocking_and_only_invokes_selected_brain(self):
        for client in ('cursor', 'grok', 'opencode'):
            result, command = self.handle(client, 'stop')
            self.assertEqual(result, {})
            command.assert_called_once_with((self.root / 'work').resolve(), 'stop')

    def test_stale_environment_cannot_redirect_brain(self):
        response = subprocess.CompletedProcess([], 0, '{}', '')
        with patch.dict(brain_hooks.os.environ, {'BRAIN_DIR': '/wrong'}), \
             patch.object(brain_hooks.subprocess, 'run', return_value=response) as run:
            brain_hooks.brain_command(self.root / 'work', 'stop')
        self.assertEqual(run.call_args.kwargs['env']['BRAIN_DIR'], str(self.root / 'work'))
        self.assertIn(str(self.root / 'work'), run.call_args.args[0])

    def test_routing_verification_failure_prevents_sync(self):
        with patch.object(brain_hooks.runtime, 'profiles', return_value=self.profiles), \
             patch.object(brain_hooks.runtime, 'brain_call', side_effect=ValueError('mismatch')), \
             patch.object(brain_hooks, 'brain_command') as command:
            with self.assertRaises(ValueError):
                brain_hooks.handle('cursor', 'stop', {'workspace_roots': [str(self.root / 'work')]})
            command.assert_not_called()


if __name__ == '__main__':
    unittest.main()
