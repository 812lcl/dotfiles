#!/usr/bin/env python3
"""Claude lifecycle hooks: resolve a project-owned Brain, never the CLI default."""
import json
import os
import shlex
from pathlib import Path
import subprocess
import sys


def git_output(cwd, *args):
    p = subprocess.run(['git', '-C', str(cwd), *args], capture_output=True,
                       text=True, timeout=5)
    return p.stdout.strip() if p.returncode == 0 else None


def verified_root(path):
    path = path.resolve()
    if not (path / 'BRAIN.md').is_file():
        return None
    top = git_output(path, 'rev-parse', '--show-toplevel')
    return path if top and Path(top).resolve() == path else None


def select_brain(cwd):
    """Nearest project Brain, then the owning checkout for a linked worktree."""
    cwd = Path(cwd)
    if not cwd.is_absolute() or not cwd.is_dir():
        return None
    cwd = cwd.resolve()
    contexts = [cwd]
    common = git_output(cwd, 'rev-parse', '--path-format=absolute', '--git-common-dir')
    if common and Path(common).name == '.git':
        owner = Path(common).resolve().parent
        if owner not in contexts:
            contexts.append(owner)
    for context in contexts:
        # Check the complete ancestor chain rather than assuming cwd is the root.
        for parent in [context, *context.parents]:
            # A session inside a Brain repository belongs to that repository.
            if parent.name == 'brain' or parent.name == '.brain':
                root = verified_root(parent)
                if root:
                    return root
            # The project explicitly owns this nested repository or symlink.
            child = parent / 'brain'
            if child.exists():
                root = verified_root(child)
                if not root:
                    raise ValueError('project Brain exists but is not an independent Git root')
                return root
    return None


def handle(payload):
    event = payload.get('hook_event_name')
    if event not in ('SessionStart', 'UserPromptSubmit', 'Stop'):
        return
    root = select_brain(payload.get('cwd', ''))
    if root is None:
        if event == 'SessionStart':
            print('Brain：当前目录没有可核验的项目 Brain；先显式确认范围，不回退全局默认库。')
        return
    env = os.environ.copy()
    # Both explicit flag and env point at the verified project root. A stale
    # inherited BRAIN_DIR from another project cannot redirect this hook.
    env['BRAIN_DIR'] = str(root)
    command = ['brain', '--brain-dir', str(root)]
    if event == 'SessionStart':
        command += ['preference', 'list', '--limit', '20']
    elif event == 'UserPromptSubmit':
        command += ['hook', 'user-prompt-submit']
    else:
        command += ['hook', 'stop']
    result = subprocess.run(command, input=json.dumps(payload), text=True,
                            capture_output=True, env=env, timeout=20)
    if result.returncode:
        # Avoid exposing credentials or arbitrary CLI stderr to model context.
        print('Brain lifecycle: command failed; project routing was preserved.', file=sys.stderr)
        return
    if event == 'UserPromptSubmit':
        output = json.loads(result.stdout)
        context = output.setdefault('hookSpecificOutput', {})
        context['additionalContext'] = context.get('additionalContext', '') + (
            '\nVerified project Brain command prefix: brain --brain-dir ' + shlex.quote(str(root)) +
            '. Use this explicit root for this project; a business workflow selecting a work '
            'profile must verify that separate root. Never fall back to the CLI global default.')
        print(json.dumps(output, ensure_ascii=False))
    elif event == 'SessionStart':
        print(result.stdout, end='')


def main():
    try:
        handle(json.load(sys.stdin))
    except (OSError, ValueError, subprocess.TimeoutExpired):
        print('Brain lifecycle: skipped because project routing could not be verified.', file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
