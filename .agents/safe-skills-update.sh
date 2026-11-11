#!/usr/bin/env bash
# Upgrade Git-maintained sources; Magpie alone writes loading entries.
set -euo pipefail
AGENTS_SCRIPT_DIR="$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve().parent)' "${BASH_SOURCE[0]}")"
OPENCLAW_ADAPTER="$AGENTS_SCRIPT_DIR/openclaw-copy-adapter.py"
if [ "${1:-}" = "--sync-openclaw" ]; then
  shift
  exec python3 "$OPENCLAW_ADAPTER" "$@"
fi
SKILL_SOURCE_ROOT="${SKILL_SOURCE_ROOT:-$(dirname "$AGENTS_SCRIPT_DIR")}"
if [ ! -f "$SKILL_SOURCE_ROOT/skills-lock.json" ]; then
  echo '[safe-update] source skills-lock.json missing; refusing global fallback' >&2
  exit 1
fi
for arg in "$@"; do
  case "$arg" in
    -g|--global) echo '[safe-update] global entries belong to Magpie; omit --global' >&2; exit 2 ;;
  esac
done
status=0
(cd "$SKILL_SOURCE_ROOT" && npx skills update --project "$@") || status=$?
if [ -f "$AGENTS_SCRIPT_DIR/.pluginName-overrides.json" ]; then
  python3 "$AGENTS_SCRIPT_DIR/apply-pluginName-overrides.py" --lock "$SKILL_SOURCE_ROOT/skills-lock.json" --rules "$AGENTS_SCRIPT_DIR/.pluginName-overrides.json"
fi
exit "$status"
