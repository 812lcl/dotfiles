#!/usr/bin/env bash
# Collect this week's completed tasks tagged area::work from the Obsidian vault.
#
# Usage: collect_obsidian.sh <since-iso>
#   since-iso: e.g. 2026-05-11 (inclusive)
#
# Strategy:
#   The `obsidian` CLI exposes a `tasks` command, but in practice it returns no
#   payload over piped stdout on this host (only `total` returns a count). So
#   we go to the filesystem instead: read the vault path from Obsidian's
#   workspace config and grep markdown files for lines with both
#   `✅ YYYY-MM-DD` (Tasks plugin completion marker) and `area::work` (Dataview
#   inline field).
#
# Output: one line per matching task
#   <YYYY-MM-DD>\t<relative-path>:<line>\t<task text>

set -euo pipefail

SINCE="${1:?usage: collect_obsidian.sh <since-iso>}"
CONFIG="${OBSIDIAN_CONFIG:-$HOME/Library/Application Support/obsidian/obsidian.json}"

if [ ! -f "$CONFIG" ]; then
  echo "# obsidian config not found at $CONFIG — skipping" >&2
  exit 0
fi

VAULT="$(python3 - "$CONFIG" <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1]))
vaults = cfg.get("vaults", {})
# Prefer the open vault; fall back to most recent.
open_vaults = [v for v in vaults.values() if v.get("open")]
chosen = open_vaults[0] if open_vaults else (
    max(vaults.values(), key=lambda v: v.get("ts", 0)) if vaults else None
)
print(chosen["path"] if chosen else "")
PY
)"

if [ -z "$VAULT" ] || [ ! -d "$VAULT" ]; then
  echo "# vault path not found or unreadable — skipping" >&2
  exit 0
fi

echo "# Obsidian completed area::work tasks since $SINCE"
echo "# Vault: $VAULT"
echo

# Build an alternation regex of every ISO date from $SINCE through today.
DATES_RE="$(python3 - "$SINCE" <<'PY'
import sys
from datetime import date, timedelta
since = date.fromisoformat(sys.argv[1])
today = date.today()
dates = []
d = since
while d <= today:
    dates.append(d.isoformat())
    d += timedelta(days=1)
print("|".join(dates))
PY
)"

# grep for lines containing both the completion marker and the work tag.
# rg is faster + handles unicode cleanly; fall back to grep -r if unavailable.
PATTERN_DATE="✅ (${DATES_RE})"
PATTERN_AREA="area::work"

if command -v rg >/dev/null 2>&1; then
  rg --no-config -n --color never -e "$PATTERN_DATE" "$VAULT" \
    --glob '*.md' --glob '!.trash/**' --glob '!.obsidian/**' 2>/dev/null \
  | grep -F "$PATTERN_AREA" \
  | sed "s|^${VAULT}/||" \
  | python3 -c '
import re, sys
pat = re.compile(r"✅ (\d{4}-\d{2}-\d{2})")
for line in sys.stdin:
    line = line.rstrip("\n")
    # Format from rg: <path>:<line>:<content>
    parts = line.split(":", 2)
    if len(parts) < 3:
        continue
    path, lineno, content = parts
    m = pat.search(content)
    if not m:
        continue
    print(f"{m.group(1)}\t{path}:{lineno}\t{content.strip()}")
' | sort
else
  # Portable fallback: grep recursively.
  grep -rEn --include='*.md' --exclude-dir='.obsidian' --exclude-dir='.trash' \
    -e "$PATTERN_DATE" "$VAULT" 2>/dev/null \
  | grep -F "$PATTERN_AREA" \
  | sed "s|^${VAULT}/||"
fi
