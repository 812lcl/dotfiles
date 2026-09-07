#!/usr/bin/env python3
"""
Locate the user's Obsidian vault root and Clippings target directory.

Resolution order:
  1. OBSIDIAN_CLIPPINGS_DIR env var (absolute path; overrides everything)
  2. OBSIDIAN_VAULT_PATH env var + OBSIDIAN_CLIPPINGS_SUBPATH (default: 4-knowledge_hub/Clippings)
  3. Default vault path + OBSIDIAN_CLIPPINGS_SUBPATH
  4. Exit 1 with a hint message — skill should then ask the user.

Usage:
  find_vault.py              # prints clippings dir
  find_vault.py --vault      # prints vault root only
  find_vault.py --json       # {"vault": "...", "clippings": "..."}
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Tuple

DEFAULT_SUBPATH = "4-knowledge_hub/Clippings"
DEFAULT_VAULT = Path("/Users/liuchunlei/Code/Obsidian Vault")


def resolve() -> Tuple[Path, Path]:
    clippings_env = os.environ.get("OBSIDIAN_CLIPPINGS_DIR")
    if clippings_env:
        cdir = Path(clippings_env).expanduser().resolve()
        return cdir.parent.parent, cdir  # best-effort vault inference

    vault_env = os.environ.get("OBSIDIAN_VAULT_PATH")
    if vault_env:
        vault = Path(vault_env).expanduser().resolve()
    else:
        vault = DEFAULT_VAULT.resolve()

    if not vault or not vault.is_dir():
        hint = (
            "Cannot locate Obsidian vault.\n"
            "Set OBSIDIAN_VAULT_PATH env var, or create/use the default vault "
            "at /Users/liuchunlei/Code/Obsidian Vault.\n"
            "Optional: OBSIDIAN_CLIPPINGS_SUBPATH (default: 4-knowledge_hub/Clippings)\n"
            "Or set OBSIDIAN_CLIPPINGS_DIR for a full override."
        )
        sys.stderr.write(hint + "\n")
        sys.exit(1)

    subpath = os.environ.get("OBSIDIAN_CLIPPINGS_SUBPATH", DEFAULT_SUBPATH)
    clippings = (vault / subpath).resolve()
    return vault, clippings


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--vault", action="store_true", help="print vault root only")
    p.add_argument("--json", action="store_true", help="output JSON")
    args = p.parse_args()

    vault, clippings = resolve()

    if args.json:
        print(json.dumps({"vault": str(vault), "clippings": str(clippings)}, ensure_ascii=False))
    elif args.vault:
        print(vault)
    else:
        print(clippings)


if __name__ == "__main__":
    main()
