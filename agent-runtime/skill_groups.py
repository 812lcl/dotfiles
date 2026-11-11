"""Maintain Magpie display groups from pluginName; never import or sync skills."""
import argparse
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
from urllib.parse import urlsplit


class ConcurrentEdit(ValueError):
    pass


def read(path, default):
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return copy.deepcopy(default), None
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError('Expected JSON object')
    return value, raw


def source_id(value):
    value = value or ''
    if value.startswith('git@github.com:'):
        value = value.removeprefix('git@github.com:')
    elif '://' in value:
        parsed = urlsplit(value)
        if parsed.hostname != 'github.com':
            return (parsed.hostname + parsed.path).rstrip('/') if parsed.hostname else value
        value = '/'.join(parsed.path.strip('/').split('/')[:2])
    value = value.removeprefix('github.com/')
    return value.rstrip('/').removesuffix('.git')


def source_group(source, rules):
    matches = [k for k in rules if source and (source == k or source.startswith(k + '/'))]
    return rules[max(matches, key=len)] if matches else None


def plugin_name(skill, locks, overrides, policy):
    name = skill['name']
    source = skill.get('source') or {}
    declared = source_id(source.get('repo') or skill.get('from'))
    locked = locks.get(name, {})
    locked_source = source_id(locked.get('source'))
    rules = {source_id(k): v for k, v in overrides.items() if not k.startswith('_')}
    group = source_group(declared, rules)
    if not group and (not declared or declared == locked_source):
        group = source_group(locked_source, rules) or locked.get('pluginName')
    if not group:
        group = policy.get('skills', {}).get(name)
    if not group and source.get('kind') == 'folder' and source.get('dir'):
        folder = Path(source['dir']).expanduser().resolve()
        for rule in policy.get('folder_groups', []):
            if folder.is_relative_to(Path(rule['path']).expanduser().resolve()):
                group = rule['group']
                break
    if group is not None and (not isinstance(group, str) or not group.strip()):
        raise ValueError('Invalid pluginName')
    return group


def grouped(library, lock, overrides, policy):
    """Only current library members are candidates; lock entries cannot add skills."""
    skills = library.get('skills', [])
    names = [s['name'] for s in skills]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate library skill names')
    present = set(names)
    desired = {s['name']: plugin_name(s, lock.get('skills', {}), overrides, policy) for s in skills}
    desired = {n: g for n, g in desired.items() if g}
    result, by_name, assigned = [], {}, set()
    for original in library.get('skillGroups', []):
        group = copy.deepcopy(original)
        label = group['name']
        if (not isinstance(label, str) or not label.strip()
                or not isinstance(group['skills'], list)
                or any(not isinstance(n, str) for n in group['skills'])):
            raise ValueError('Invalid skill group')
        if label in by_name:
            raise ValueError('Duplicate group names')
        group['skills'] = [n for n in group['skills'] if n in present and n not in assigned
                           and desired.get(n, label) == label]
        assigned.update(group['skills'])
        result.append(group)
        by_name[label] = group
    for name, label in desired.items():
        if name in assigned:
            continue
        if label not in by_name:
            by_name[label] = {'name': label, 'skills': []}
            result.append(by_name[label])
        by_name[label]['skills'].append(name)
        assigned.add(name)
    return [g for g in result if g['skills']]


def atomic_write(path, raw, mode=0o600, before_replace=None):
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if before_replace is not None:
            before_replace()
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def unchanged(inputs):
    for path, expected in inputs:
        try:
            actual = path.read_bytes()
        except FileNotFoundError:
            actual = None
        if actual != expected:
            raise ConcurrentEdit('Input changed; retry on the next event')


def reconcile(library_path, lock_path, overrides_path, policy_path, state, *, apply=False, settle=0):
    paths = (library_path, lock_path, overrides_path, policy_path)
    if any(p.resolve().is_relative_to(state.resolve()) for p in paths[:3]):
        raise ValueError('State must be separate from input resources')
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (state / 'worker.lock').open('a') as guard:
        fcntl.flock(guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
        library, raw = read(library_path, {})
        if raw is None:
            return {'status': 'library-absent', 'changed': False}
        lock, lock_raw = read(lock_path, {'skills': {}})
        overrides, overrides_raw = read(overrides_path, {})
        policy, policy_raw = read(policy_path, {})
        inputs = list(zip(paths, (raw, lock_raw, overrides_raw, policy_raw)))
        if settle:
            time.sleep(settle)
        unchanged(inputs)
        groups = grouped(library, lock, overrides, policy)
        changed = library.get('skillGroups', []) != groups
        result = {'status': 'updated' if changed and apply else 'planned' if changed else 'unchanged',
                  'changed': changed, 'skill_count': len(library.get('skills', [])),
                  'group_count': len(groups), 'grouped_count': sum(len(g['skills']) for g in groups)}
        if changed and apply:
            after = copy.deepcopy(library)
            after['skillGroups'] = groups
            data = (json.dumps(after, ensure_ascii=False, indent=2) + '\n').encode()
            # Prepare fully before the final optimistic check, keeping the rename window small.
            backup = state / 'backups'
            backup.mkdir(mode=0o700, exist_ok=True)
            name = hashlib.sha256(raw).hexdigest() + '.json'
            if not (backup / name).exists():
                atomic_write(backup / name, raw)
            unchanged(inputs)
            atomic_write(library_path, data, library_path.stat().st_mode & 0o777,
                         before_replace=lambda: unchanged(inputs))
            current, _ = read(library_path, {})
            if current != after:
                raise ConcurrentEdit('Post-write change; leave latest data and retry')
            for old in sorted(backup.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)[20:]:
                old.unlink()
        if apply:
            result['checked_at_ns'] = time.time_ns()
            atomic_write(state / 'last-run.json', (json.dumps(result) + '\n').encode())
        return result


def main():
    home = Path.home()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', type=Path, default=home / '.config/magpie/library.json')
    parser.add_argument('--lock', type=Path, default=home / '.agents/.skill-lock.json')
    parser.add_argument('--overrides', type=Path, default=home / '.agents/.pluginName-overrides.json')
    parser.add_argument('--policy', type=Path, default=home / '.local/state/agent-runtime/skill-group-policy.json')
    parser.add_argument('--state', type=Path, default=home / '.local/state/agent-runtime/skill-groups')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--quiet', action='store_true', help='Log changes and errors only')
    args = parser.parse_args()
    try:
        result = reconcile(args.library, args.lock, args.overrides, args.policy, args.state,
                           apply=args.apply, settle=0.5)
    except (ConcurrentEdit, BlockingIOError):
        result = {'status': 'concurrent-edit-skipped', 'changed': False}
    except (OSError, ValueError, KeyError, TypeError) as error:
        # JSON/MCP documents may contain secrets; never log exception text or input values.
        print(json.dumps({'status': 'error', 'type': type(error).__name__}))
        return 1
    if not args.quiet or result['status'] in ('updated', 'planned'):
        print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
