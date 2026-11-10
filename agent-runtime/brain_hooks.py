"""Scoped, fail-open lifecycle adapter. Never resolves Brain from global defaults."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

import runtime


def audit(record):
    """Explicit acceptance logging only; no prompt, paths, or tool contents."""
    if path := os.environ.get('AGENT_RUNTIME_HOOK_AUDIT'):
        try:
            fd = os.open(path, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
            with os.fdopen(fd, 'w') as stream:
                stream.write(json.dumps(record) + '\n')
        except OSError:
            pass  # Acceptance logging must never change hook control flow.


def git_common(path):
    result = subprocess.run(['git', '--no-optional-locks', '-C', str(path), 'rev-parse',
                             '--path-format=absolute', '--git-common-dir'],
                            capture_output=True, text=True, timeout=3)
    return Path(result.stdout.strip()).resolve() if result.returncode == 0 else None


def scope_for(paths, profiles):
    """All supplied roots must have the same explicit owner; mixed scopes fail open."""
    selected = set()
    for raw in paths:
        if not isinstance(raw, str) or not Path(raw).is_absolute():
            raise ValueError('Absolute workspace required')
        path = Path(raw).resolve(strict=True)
        common = git_common(path)
        owner = common.parent if common and common.name == '.git' else path
        matches = set()
        for workspace in profiles['cursor']['workspaces'].values():
            root = Path(workspace['root']).resolve(strict=True)
            if path.is_relative_to(root) or owner.is_relative_to(root):
                matches.add(workspace['brain_scope'])
        if len(matches) != 1:
            raise ValueError('Unknown or ambiguous workspace')
        selected.update(matches)
    if len(selected) != 1:
        raise ValueError('Mixed or absent workspace scopes')
    return selected.pop()


def brain_command(root, event):
    env = dict(os.environ, BRAIN_DIR=str(root))
    result = subprocess.run(['brain', '--brain-dir', str(root), 'hook', event],
                            input='{}', text=True, capture_output=True, timeout=20, env=env)
    if result.returncode:
        raise ValueError('Brain hook failed')
    return result.stdout


def context(scope, profiles):
    root = Path(profiles['brain'][scope]['root']).resolve(strict=True)
    prefix = 'brain --brain-dir ' + shlex.quote(str(root))
    if scope == 'personal':
        vault = Path(profiles['brain']['vault_root'])
        policy = (vault / '.agents/contracts/brain-recall.md').read_text()
    else:
        output = json.loads(brain_command(root, 'user-prompt-submit'))
        policy = output.get('hookSpecificOutput', {}).get('additionalContext', '')
        if not policy:
            raise ValueError('Brain did not provide query-start guidance')
    return ('Brain lifecycle [' + scope + ']\n' + policy.rstrip() + '\n'
            '已核验命令前缀：' + prefix + '。不回退全局库、不跨库聚合。'
            '有保留价值的工作先写 note，再用 memo --ref 索引；hook 不自动生成记忆正文。')


def handle(client, event, payload, state=runtime.DEFAULT_STATE):
    profiles = runtime.profiles(state)
    paths = payload.get('workspace_roots') if client == 'cursor' else None
    if not paths:
        paths = [payload.get('cwd')]
    scope = scope_for(paths, profiles)
    verified = runtime.brain_call(state, scope, 'verify', metadata_only=True)['selection']
    root = Path(profiles['brain'][scope]['root']).resolve(strict=True)
    if verified['scope'] != scope or Path(verified['brain_root']).resolve(strict=True) != root:
        raise ValueError('Brain profile changed during routing')
    stop = event in ('stop', 'Stop')
    if stop:
        brain_command(root, 'stop')
        output = {}
    else:
        text = context(scope, profiles)
        if client == 'cursor':
            output = {'additional_context': text}
        elif client == 'grok':
            output = {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'additionalContext': text}}
        else:
            output = {'context': text}
    # Opt-in, metadata-only evidence for explicit acceptance processes.
    audit({'client': client, 'event': event, 'scope': scope, 'ok': True,
           'context_sha256': hashlib.sha256(json.dumps(output).encode()).hexdigest()})
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('client', choices=['cursor', 'grok', 'opencode'])
    parser.add_argument('event', choices=['sessionStart', 'preToolUse', 'PreToolUse', 'context', 'stop', 'Stop'])
    args = parser.parse_args()
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError('Hook payload must be an object')
        audit({'client': args.client, 'event': args.event, 'stage': 'received',
               'has_cwd': bool(payload.get('cwd')), 'has_roots': bool(payload.get('workspace_roots'))})
        output = handle(args.client, args.event, payload)
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        audit({'client': args.client, 'event': args.event, 'ok': False, 'error': type(error).__name__})
        print('Brain lifecycle: skipped; no verified single-scope workspace.', file=sys.stderr)
        output = {}
    print(json.dumps(output, ensure_ascii=False))


if __name__ == '__main__':
    main()
