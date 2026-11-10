"""Install additive native hooks, preserving Claude/Codex and unrelated handlers."""
import json
from pathlib import Path
import shlex
import sys
import tomllib

import handoff
import runtime


def install(run_dir, home=Path.home(), source=None):
    source = source or home / 'Code/dotfiles/agent-runtime'
    command = shlex.join([sys.executable, '-B', str(source / 'brain_hooks.py')])
    run_dir = runtime.state_path(run_dir, runtime.DEFAULT_STATE)
    run_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    cursor = home / '.cursor/hooks.json'
    before = json.loads(cursor.read_text())
    after = json.loads(json.dumps(before))
    for event in ('sessionStart', 'preToolUse', 'stop'):
        entry = {'command': command + ' cursor ' + event, 'timeout': 30}
        handlers = after.setdefault('hooks', {}).setdefault(event, [])
        if entry not in handlers:
            handlers.append(entry)

    claude = json.loads((home / '.claude/settings.json').read_text())
    config_file = home / '.grok/config.toml'
    config = tomllib.loads(config_file.read_text()) if config_file.exists() else {}
    inherited = config.get('compat', {}).get('claude', {}).get('hooks', True) and any(
        'brain-lifecycle.py' in hook.get('command', '')
        for group in claude.get('hooks', {}).get('Stop', []) for hook in group.get('hooks', []))
    events = ['PreToolUse'] + ([] if inherited else ['Stop'])
    grok = home / '.grok/hooks/agent-runtime-brain.json'
    target = {'hooks': {event: [{'hooks': [{'type': 'command',
              'command': command + ' grok ' + event, 'timeout': 30}]}] for event in events}}
    if grok.exists() and json.loads(grok.read_text()) != target:
        raise ValueError('Existing Grok Brain file differs; inspect before replacement')

    plugin = home / '.config/opencode/plugins/agent-runtime-brain.js'
    expected = source / 'opencode-brain.js'
    if plugin.is_symlink():
        if plugin.resolve() != expected.resolve():
            raise ValueError('Unexpected existing OpenCode Brain plugin')
    elif plugin.exists():
        raise ValueError('Existing OpenCode Brain plugin needs inspection')
    # Validate all destinations before making any runtime changes.
    backup = run_dir / 'cursor-hooks-before.json'
    if not backup.exists():
        handoff.atomic_json(backup, before)
    handoff.atomic_json(cursor, after)
    grok.parent.mkdir(parents=True, exist_ok=True)
    handoff.atomic_json(grok, target)
    if not plugin.is_symlink():
        plugin.parent.mkdir(parents=True, exist_ok=True)
        plugin.symlink_to(expected)
    result = {'cursor': str(cursor), 'grok': str(grok), 'opencode': str(plugin),
              'grok_stop_inherited_from_claude': bool(inherited),
              'claude_modified': False, 'codex_modified': False}
    handoff.atomic_json(run_dir / 'hook-installation.json', result)
    return result


if __name__ == '__main__':
    print(json.dumps(install(Path(sys.argv[1])), indent=2))
