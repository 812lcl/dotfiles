#!/usr/bin/env bash
# safe-skills-update.sh
# Wraps `npx skills update -g` and forces ~/.openclaw/skills/* back to copy mode
# afterward, because OpenClaw cannot load symlinked skills (permission/path issue
# discovered 2026-05-08; see ~/.claude/.../memory/feedback_openclaw_skills_copy_mode.md).
#
# Mechanism:
#   1. Snapshot current openclaw entries (these are the skills we must keep as copy).
#   2. Run `npx skills update -g "$@"`.
#   3. For each snapshotted entry that is now a symlink (CLI default after update),
#      replace it with a fresh copy from the canonical ~/.agents/skills/<name>/.
#
# Usage: bash ~/.agents/safe-skills-update.sh [extra args forwarded to skills update]
set -euo pipefail

OC_DIR="$HOME/.openclaw/skills"
CANON_DIR="$HOME/.agents/skills"

if [ ! -d "$OC_DIR" ]; then
  echo "[safe-update] no $OC_DIR — nothing openclaw-specific to guard"
  exec npx skills update -g "$@"
fi

WATCH=()
while IFS= read -r line; do
  WATCH+=("$line")
done < <(ls -1 "$OC_DIR")
echo "[safe-update] guarding ${#WATCH[@]} openclaw skill(s) for copy-mode preservation"

npx skills update -g "$@"
status=$?

restored=0
missing_canon=()
for name in "${WATCH[@]}"; do
  target="$OC_DIR/$name"
  src="$CANON_DIR/$name"
  if [ -L "$target" ]; then
    if [ ! -d "$src" ]; then
      missing_canon+=("$name")
      continue
    fi
    rm "$target"
    cp -R "$src" "$target"
    restored=$((restored + 1))
  fi
done

if [ "$restored" -gt 0 ]; then
  echo "[safe-update] restored $restored openclaw skill(s) symlink → copy"
fi
if [ "${#missing_canon[@]}" -gt 0 ]; then
  echo "[safe-update] WARN: canonical missing for: ${missing_canon[*]} (skipped)" >&2
fi

# Re-apply per-source pluginName overrides (CLI add/update wipes them)
python3 "$HOME/.agents/apply-pluginName-overrides.py" || true

exit "$status"
