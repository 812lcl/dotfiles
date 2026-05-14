#!/usr/bin/env bash
# Collect my commits across all sub-repos under a parent directory.
#
# Usage: collect_git.sh <since-iso> [root]
#   since-iso: e.g. 2026-05-11 (inclusive lower bound, git log --since)
#   root: parent dir containing sub-repos (default: $HOME/Code/skywork/agent)
#
# For each sub-repo containing .git, prints:
#   ### <repo-name>  (branch=<branch>)
#   <YYYY-MM-DD> <short-sha> <subject>
#   ...
# Repos with zero commits in the window are skipped.

set -euo pipefail

SINCE="${1:?usage: collect_git.sh <since-iso> [root]}"
ROOT="${2:-$HOME/Code/skywork/agent}"

if [ ! -d "$ROOT" ]; then
  echo "error: root not found: $ROOT" >&2
  exit 1
fi

# Use global email as the primary author filter. Fall back to repo-local
# config if global is unset.
PRIMARY_EMAIL="$(git config --global user.email 2>/dev/null || true)"

echo "# Git commits since $SINCE"
echo "# Root: $ROOT"
echo "# Author primary: ${PRIMARY_EMAIL:-<unset>}"
echo

shopt -s nullglob
for dir in "$ROOT"/*/; do
  [ -d "$dir/.git" ] || [ -f "$dir/.git" ] || continue
  name="$(basename "$dir")"

  # Prefer repo-local email; fall back to global.
  email="$(git -C "$dir" config user.email 2>/dev/null || true)"
  email="${email:-$PRIMARY_EMAIL}"
  [ -z "$email" ] && continue

  # Collect commits authored OR committed by me (covers rebases/cherry-picks).
  # Exclude pure merge commits — they bloat the report without adding info.
  log=$(git -C "$dir" log \
    --since="$SINCE 00:00:00" \
    --no-merges \
    --author="$email" \
    --format="%cs %h %s" \
    --all 2>/dev/null || true)

  [ -z "$log" ] && continue

  branch=$(git -C "$dir" symbolic-ref --short HEAD 2>/dev/null || echo '?')

  echo "### $name  (branch=$branch)"
  echo "$log"
  echo
done
