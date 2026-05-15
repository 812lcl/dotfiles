#!/usr/bin/env bash
# Surface this week's brain context: memo entries, quest dashboard, fresh notes.
#
# Usage: collect_brain.sh <since-iso> [agent-root]
#   since-iso: e.g. 2026-05-11
#   agent-root: parent dir containing brain/ (default: $HOME/Code/skywork/agent)
#
# Outputs three sections:
#   ## Quest dashboard   (full text, gives big-picture context)
#   ## This week memos   (each daily memo file from $SINCE through today)
#   ## Recently touched notes  (files in brain/notes/ modified since $SINCE)

set -euo pipefail

SINCE="${1:?usage: collect_brain.sh <since-iso> [agent-root]}"
ROOT="${2:-$HOME/Code/skywork/agent}"
BRAIN="$ROOT/brain"

if [ ! -d "$BRAIN" ]; then
  echo "# brain dir not found at $BRAIN — skipping" >&2
  exit 0
fi

echo "## Quest dashboard"
echo
if [ -f "$BRAIN/quests/_DASHBOARD.md" ]; then
  cat "$BRAIN/quests/_DASHBOARD.md"
else
  echo "(no dashboard found)"
fi
echo

echo "## This week memos (since $SINCE)"
echo
if [ -d "$BRAIN/memo" ]; then
  found=0
  for f in "$BRAIN/memo"/*.md; do
    [ -f "$f" ] || continue
    base="$(basename "$f" .md)"
    # Skip index files; only keep YYYY-MM-DD daily files within window.
    [[ "$base" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || continue
    if [[ "$base" > "$SINCE" || "$base" == "$SINCE" ]]; then
      found=1
      echo "### $base"
      cat "$f"
      echo
    fi
  done
  [ "$found" = "0" ] && echo "(no daily memos in window)"
else
  echo "(no memo dir)"
fi
echo

echo "## Recently touched notes (since $SINCE)"
echo
if [ -d "$BRAIN/notes" ]; then
  found=0
  # macOS find -newermt accepts ISO date; use 'YYYY-MM-DD 00:00:00'.
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    found=1
    rel="${f#$BRAIN/}"
    mod=$(stat -f '%Sm' -t '%Y-%m-%d' "$f" 2>/dev/null || echo '?')
    head1=$(grep -m1 '^# ' "$f" 2>/dev/null | sed 's/^# //')
    echo "- $mod  $rel  — ${head1:-(no h1)}"
  done < <(find "$BRAIN/notes" -type f -name '*.md' -newermt "$SINCE 00:00:00" 2>/dev/null | sort)
  [ "$found" = "0" ] && echo "(no notes touched in window)"
else
  echo "(no notes dir)"
fi
