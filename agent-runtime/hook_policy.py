"""Remove Orca/Paseo command hooks without dropping neighbouring handlers."""
import copy
import re


BRIDGE_COMMAND = re.compile(r'(?i)(?:\.orca[/\\]|\bORCA_[A-Z_]+|orca-agent-hook|'
                            r'\bpaseo\b|\bPASEO_[A-Z_]+)')


def is_bridge(handler):
    return isinstance(handler, dict) and any(
        isinstance(handler.get(key), str) and BRIDGE_COMMAND.search(handler[key])
        for key in ('command', 'commandWindows'))


def without_bridges(config):
    """Pure operation; return the cleaned document and removed handler count."""
    result, removed = copy.deepcopy(config), 0
    hooks = result.get('hooks', {})
    for event, groups in list(hooks.items()):
        if not isinstance(groups, list):
            continue
        kept = []
        for group in groups:
            if is_bridge(group):
                removed += 1
            elif isinstance(group, dict) and isinstance(group.get('hooks'), list):
                before = group['hooks']
                group['hooks'] = [h for h in before if not is_bridge(h)]
                removed += len(before) - len(group['hooks'])
                if group['hooks'] or not before:
                    kept.append(group)
            else:
                kept.append(group)
        if kept:
            hooks[event] = kept
        elif groups:
            del hooks[event]
    return result, removed
