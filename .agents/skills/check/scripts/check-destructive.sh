#!/usr/bin/env bash
# Block destructive commands during /check review sessions.
# Called by the PreToolUse hook on Bash.
# Exit 0 = allow, exit 2 = block with message.
set -euo pipefail

INPUT="${CLAUDE_TOOL_INPUT:-}"

# Patterns that must never run during code review
DESTRUCTIVE_PATTERNS=(
  'git push --force'
  'git push -f '
  'rm -rf /'
  'DROP TABLE'
  'DROP DATABASE'
  'TRUNCATE '
  '--no-verify'
  'git reset --hard'
  'git checkout \.'
  'git clean -f'
)

for pattern in "${DESTRUCTIVE_PATTERNS[@]}"; do
  if echo "$INPUT" | grep -qF "$pattern"; then
    echo "BLOCK: Destructive command detected during /check review: $pattern" >&2
    echo "Confirm with user before proceeding." >&2
    exit 2
  fi
done

exit 0
