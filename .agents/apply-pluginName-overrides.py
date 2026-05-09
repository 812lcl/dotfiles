#!/usr/bin/env python3
"""Re-apply per-source pluginName overrides to ~/.agents/.skill-lock.json.

CLI's `npx skills add` (also called by `update`) overwrites the entire lock
entry, so any manual pluginName tweak is wiped on each install. Run this after
every install/update to restore the canonical names.

Override rules live in ~/.agents/.pluginName-overrides.json
"""
import json
from pathlib import Path

HOME = Path.home()
LOCK = HOME / ".agents/.skill-lock.json"
RULES = HOME / ".agents/.pluginName-overrides.json"

lock = json.loads(LOCK.read_text())
rules = {k: v for k, v in json.loads(RULES.read_text()).items() if not k.startswith("_")}

changed = 0
for name, entry in lock["skills"].items():
    want = rules.get(entry["source"])
    if want is None:
        continue
    if entry.get("pluginName") != want:
        entry["pluginName"] = want
        changed += 1

LOCK.write_text(json.dumps(lock, indent=2) + "\n")
print(f"Re-applied pluginName on {changed} entries")
