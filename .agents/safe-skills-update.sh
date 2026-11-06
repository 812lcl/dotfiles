#!/usr/bin/env bash
# safe-skills-update.sh
# Preserve this installation's OpenClaw copy distribution after global updates.
# Skill discovery-root policy and actual file-access permissions are separate;
# this adapter does not change or bypass either policy.
#
# Mechanism:
#   1. Snapshot current openclaw entries (these are the skills we must keep as copy).
#   2. Run `npx skills update -g "$@"`.
#   3. For each snapshotted entry that is now a symlink (CLI default after update),
#      replace it with a fresh copy from the canonical ~/.agents/skills/<name>/.
#
# Targeted copy/adaptation (no npx, lock/config edits, service calls):
#   bash ~/.agents/safe-skills-update.sh --sync-openclaw --skill knowledge-clip --dry-run
#   bash ~/.agents/safe-skills-update.sh --sync-openclaw --skill knowledge-clip --apply
# Otherwise, extra args are forwarded to the original global skills update.
set -euo pipefail

AGENTS_SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
OPENCLAW_ADAPTER="$AGENTS_SCRIPT_DIR/openclaw-copy-adapter.py"
if [ "${1:-}" = "--sync-openclaw" ]; then
  shift
  exec python3 "$OPENCLAW_ADAPTER" "$@"
fi

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

# Fail before the upstream update when the installed local clip cannot be adapted safely.
if [ -d "$OC_DIR/knowledge-clip" ] && [ ! -L "$OC_DIR/knowledge-clip" ]; then
  python3 "$OPENCLAW_ADAPTER" --skill knowledge-clip --dry-run
fi
status=0
npx skills update -g "$@" || status=$?

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
    src="$(cd "$src" && pwd -P)"
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

# Re-apply private Work skill entries and symlink entrypoints when available.
WORK_LOCK_SYNC="$HOME/.brain/.agents/sync-work-skill-lock.py"
if [ -f "$WORK_LOCK_SYNC" ]; then
  python3 "$WORK_LOCK_SYNC" --apply || true
fi

# The same adapter runs after every regular update, even when knowledge-clip
# remained a copy (local skills are skipped by npx). Never refresh unrelated copies.
if [ -d "$OC_DIR/knowledge-clip" ] && [ ! -L "$OC_DIR/knowledge-clip" ]; then
  adapter_status=0
  python3 "$OPENCLAW_ADAPTER" --skill knowledge-clip --post-update --apply || adapter_status=$?
  if [ "$adapter_status" -ne 0 ] && [ "$status" -eq 0 ]; then
    status="$adapter_status"
  fi
fi

exit "$status"
