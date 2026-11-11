import copy
import json
from pathlib import Path
import plistlib
import sys
import tempfile
import unittest
from unittest.mock import patch

import install_skill_groups
import skill_groups


class GroupPlanTests(unittest.TestCase):
    def test_lock_plugin_name_and_update_override(self):
        lib = {'skills': [{'name': 'reader', 'agents': ['codex']}]}
        lock = {'skills': {'reader': {'source': 'owner/repo', 'pluginName': 'old'}}}
        self.assertEqual(skill_groups.grouped(lib, lock, {}, {}), [
            {'name': 'old', 'skills': ['reader']}])
        self.assertEqual(skill_groups.grouped(lib, lock, {'owner/repo': 'new'}, {}), [
            {'name': 'new', 'skills': ['reader']}])

    def test_fresh_import_from_repository_works_without_lock_entry(self):
        for source in ({'kind': 'github', 'repo': 'owner/repo'},
                       {'kind': 'git', 'repo': 'https://github.com/owner/repo.git'}):
            lib = {'skills': [{'name': 'new', 'source': source, 'agents': []}]}
            self.assertEqual(skill_groups.grouped(lib, {}, {'owner/repo': 'pack'}, {}), [
                {'name': 'pack', 'skills': ['new']}])

    def test_stale_same_name_lock_cannot_override_explicit_new_source(self):
        lib = {'skills': [{'name': 'same', 'from': 'different/repo', 'agents': []}]}
        lock = {'skills': {'same': {'source': 'old/repo', 'pluginName': 'old'}}}
        self.assertEqual(skill_groups.grouped(lib, lock, {}, {}), [])

    def test_well_known_source_uses_configured_host_group(self):
        lib = {'skills': [{'name': 'new-lark', 'from': 'https://open.feishu.cn/lark-cli/skills/regular', 'agents': []}]}
        self.assertEqual(skill_groups.grouped(lib, {}, {'open.feishu.cn': 'lark-cli'}, {}), [
            {'name': 'lark-cli', 'skills': ['new-lark']}])

    def test_deletion_prunes_members_but_never_resurrects_lock_entries(self):
        lib = {'skills': [{'name': 'kept', 'agents': ['claude']}], 'skillGroups': [
            {'name': 'pack', 'skills': ['deleted', 'kept']}]}
        lock = {'skills': {'deleted': {'pluginName': 'pack'}, 'kept': {'pluginName': 'pack'}}}
        before = copy.deepcopy(lib)
        self.assertEqual(skill_groups.grouped(lib, lock, {}, {}), [{'name': 'pack', 'skills': ['kept']}])
        self.assertEqual(lib, before)

    def test_updated_plugin_moves_only_the_display_membership(self):
        lib = {'skills': [{'name': 'moved', 'agents': []}, {'name': 'custom', 'agents': ['grok']}],
               'skillGroups': [{'name': 'old', 'skills': ['moved']},
                               {'name': 'manual', 'skills': ['custom'], 'extra': 'preserve'}]}
        lock = {'skills': {'moved': {'pluginName': 'new'}}}
        self.assertEqual(skill_groups.grouped(lib, lock, {}, {}), [
            {'name': 'manual', 'skills': ['custom'], 'extra': 'preserve'},
            {'name': 'new', 'skills': ['moved']}])

    def test_folder_policy_applies_to_new_local_skills_after_known_metadata(self):
        lib = {'skills': [{'name': 'local', 'source': {'kind': 'folder', 'dir': '/fixtures/work/new'}, 'agents': []}]}
        policy = {'folder_groups': [{'path': '/fixtures/work', 'group': 'Work'}]}
        self.assertEqual(skill_groups.grouped(lib, {}, {}, policy), [{'name': 'Work', 'skills': ['local']}])
        lock = {'skills': {'local': {'pluginName': 'known'}}}
        self.assertEqual(skill_groups.grouped(lib, lock, {}, policy), [{'name': 'known', 'skills': ['local']}])

    def test_missing_plugin_preserves_existing_group_or_source_display(self):
        lib = {'skills': [{'name': 'unmapped'}, {'name': 'custom'}],
               'skillGroups': [{'name': 'manual', 'skills': ['custom']}]}
        self.assertEqual(skill_groups.grouped(lib, {}, {}, {}), lib['skillGroups'])


class GroupWriteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.library, self.lock, self.overrides, self.policy = [self.home / n for n in (
            'library.json', 'lock.json', 'overrides.json', 'policy.json')]
        self.state = self.home / 'state'
        self.original = {'skills': [{'name': 'kept', 'agents': ['codex'], 'offHere': True,
                                    'router': 'direct', 'note': 'keep'}],
                         'mcp': [{'name': 'existing', 'agents': ['grok']}],
                         'hooks': [{'name': 'brain-stop', 'agents': ['claude']}],
                         'applied': {'codex': {'skills': ['kept']}}, 'futureField': {'secret': 'do-not-log'}}
        self.library.write_text(json.dumps(self.original))
        self.lock.write_text(json.dumps({'skills': {'kept': {'pluginName': 'Work'},
                                                    'deleted': {'pluginName': 'Work'}}}))
        self.overrides.write_text('{}'); self.policy.write_text('{}')

    def run_sync(self, **kw):
        return skill_groups.reconcile(self.library, self.lock, self.overrides, self.policy, self.state, **kw)

    def test_apply_changes_only_groups_and_preserves_distribution_and_mode(self):
        self.library.chmod(0o600)
        result = self.run_sync(apply=True)
        after = json.loads(self.library.read_text())
        self.assertEqual(after.pop('skillGroups'), [{'name': 'Work', 'skills': ['kept']}])
        self.assertEqual(after, self.original)
        self.assertTrue(result['changed'])
        self.assertEqual(self.library.stat().st_mode & 0o777, 0o600)
        self.assertEqual(len(list((self.state / 'backups').glob('*.json'))), 1)
        self.assertNotIn('do-not-log', (self.state / 'last-run.json').read_text())

    def test_noop_does_not_rewrite_library_or_create_more_backups(self):
        self.run_sync(apply=True)
        before = self.library.stat().st_mtime_ns
        self.assertFalse(self.run_sync(apply=True)['changed'])
        self.assertEqual(self.library.stat().st_mtime_ns, before)
        self.assertEqual(len(list((self.state / 'backups').glob('*.json'))), 1)

    def test_dry_run_and_missing_library_never_import(self):
        before = self.library.read_bytes()
        self.assertTrue(self.run_sync()['changed'])
        self.assertEqual(before, self.library.read_bytes())
        self.library.unlink()
        self.assertEqual(self.run_sync(apply=True)['status'], 'library-absent')
        self.assertFalse(self.library.exists())

    def test_concurrent_user_deletion_and_assignment_change_are_not_overwritten(self):
        original_write = skill_groups.atomic_write
        concurrent = copy.deepcopy(self.original)
        concurrent['skills'] = []
        concurrent['mcp'][0]['agents'] = ['cursor']

        def write(path, *args, **kw):
            if path == self.library:
                self.library.write_text(json.dumps(concurrent))
            return original_write(path, *args, **kw)

        with patch.object(skill_groups, 'atomic_write', side_effect=write):
            with self.assertRaises(skill_groups.ConcurrentEdit):
                self.run_sync(apply=True)
        self.assertEqual(json.loads(self.library.read_text()), concurrent)
        self.assertEqual(list(self.home.glob('.library.json-*')), [])

    def test_invalid_json_and_invalid_groups_are_left_untouched(self):
        for text in ('{bad-json', json.dumps(dict(self.original, skillGroups=[{'name': 'bad', 'skills': 'wrong'}]))):
            self.library.write_text(text)
            with self.assertRaises(ValueError):
                self.run_sync(apply=True)
            self.assertEqual(self.library.read_text(), text)

    def test_installer_preserves_policy_and_does_not_touch_library(self):
        state = self.home / '.local/state/agent-runtime'
        state.mkdir(parents=True)
        (state / 'profiles.json').write_text(json.dumps({'brain': {
            'work': {'root': str(self.home / 'private')}, 'vault_root': str(self.home / 'vault')}}))
        policy = state / 'skill-group-policy.json'
        policy.write_text('{"skills":{"custom":"mine"}}')
        installed = install_skill_groups.install(self.home, self.home / 'source', Path(sys.executable))
        job = plistlib.loads(installed.read_bytes())
        self.assertEqual(job['StartInterval'], 60)
        self.assertEqual(len(job['WatchPaths']), 4)
        self.assertIn('--apply', job['ProgramArguments'])
        self.assertEqual(policy.read_text(), '{"skills":{"custom":"mine"}}')
        self.assertEqual(json.loads(self.library.read_text()), self.original)


if __name__ == '__main__':
    unittest.main()
