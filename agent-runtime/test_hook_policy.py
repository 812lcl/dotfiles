import copy
import unittest

from hook_policy import without_bridges


class HookPolicyTests(unittest.TestCase):
    def test_mixed_group_keeps_brain_and_matcher(self):
        source = {'hooks': {'Stop': [{'matcher': '*', 'hooks': [
            {'command': 'brain hook stop'}, {'command': 'paseo hooks codex Stop'}]}]},
                  'model': 'native'}
        original = copy.deepcopy(source)
        result, count = without_bridges(source)
        self.assertEqual(count, 1)
        self.assertEqual(result['hooks']['Stop'], [
            {'matcher': '*', 'hooks': [{'command': 'brain hook stop'}]}])
        self.assertEqual(result['model'], 'native')
        self.assertEqual(source, original)

    def test_cursor_flat_handlers_and_windows_commands(self):
        result, count = without_bridges({'hooks': {'stop': [
            {'command': '/bin/sh "$HOME/.orca/agent-hooks/cursor-hook.sh"'},
            {'commandWindows': 'if defined PASEO_TERMINAL_ID exit'},
            {'command': 'python3 brain_hooks.py cursor stop'}]}})
        self.assertEqual(count, 2)
        self.assertEqual(len(result['hooks']['stop']), 1)
        self.assertEqual(without_bridges(result), (result, 0))

    def test_descriptions_and_non_hook_settings_are_not_removal_targets(self):
        source = {'description': 'orca and paseo', 'hooks': {'Stop': [
            {'description': 'paseo', 'hooks': [{'command': 'brain hook stop'}]}],
            'enabled': True}, 'mcpServers': {'paseo': {'command': 'keep'}}}
        self.assertEqual(without_bridges(source), (source, 0))


if __name__ == '__main__':
    unittest.main()
