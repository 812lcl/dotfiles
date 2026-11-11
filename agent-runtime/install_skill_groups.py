"""Install a user-level, metadata-only Magpie grouping job (no app restarts)."""
import argparse
import json
from pathlib import Path
import plistlib
import sys

from skill_groups import atomic_write


LABEL = 'com.liuchunlei.agent-runtime.skill-groups'


def install(home, source, python):
    state = home / '.local/state/agent-runtime'
    state.mkdir(parents=True, mode=0o700, exist_ok=True)
    policy = state / 'skill-group-policy.json'
    if not policy.exists():
        profiles = json.loads((state / 'profiles.json').read_text())
        data = {'skills': {'multi-repo-maintenance': 'Work'}, 'folder_groups': [
            {'path': str(Path(profiles['brain']['work']['root']) / '.agents/skills'), 'group': 'Work'},
            {'path': str(Path(profiles['brain']['vault_root']) / '.agents/skills'), 'group': 'Personal'}]}
        atomic_write(policy, (json.dumps(data, indent=2) + '\n').encode())
    library = home / '.config/magpie/library.json'
    lock = home / '.agents/.skill-lock.json'
    overrides = home / '.agents/.pluginName-overrides.json'
    worker = state / 'skill-groups'
    worker.mkdir(mode=0o700, exist_ok=True)
    agent = {'Label': LABEL, 'ProgramArguments': [str(python), '-B', str(source / 'skill_groups.py'),
             '--library', str(library), '--lock', str(lock), '--overrides', str(overrides),
             '--policy', str(policy), '--state', str(worker), '--apply', '--quiet'],
             'WatchPaths': [str(p) for p in (library, lock, overrides, policy)],
             'RunAtLoad': True, 'StartInterval': 60, 'ThrottleInterval': 5,
             'StandardOutPath': str(worker / 'worker.log'),
             'StandardErrorPath': str(worker / 'worker-error.log')}
    folder = home / 'Library/LaunchAgents'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (LABEL + '.plist')
    raw = plistlib.dumps(agent, sort_keys=True)
    if not path.exists() or path.read_bytes() != raw:
        atomic_write(path, raw)
    return path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path.home())
    parser.add_argument('--source', type=Path, default=Path.home() / 'Code/dotfiles/agent-runtime')
    args = parser.parse_args()
    print(install(args.home, args.source, Path(sys.executable)))
