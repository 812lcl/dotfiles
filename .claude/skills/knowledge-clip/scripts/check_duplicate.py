#!/usr/bin/env python3
"""
Check whether a given source URL/path has already been clipped.

Two-stage match (covers legacy notes with non-standard frontmatter):

  Stage 1 — frontmatter fields:
    look for `source:` OR `url:` lines in the first --- block

  Stage 2 — URL fingerprint:
    extract the longest path segment (or query value) >= 6 chars and
    grep the entire file content. Catches legacy notes where the URL
    only appears in body or in a non-standard frontmatter field.

Usage:
  check_duplicate.py <source-url-or-path> [<clippings-dir>]

If <clippings-dir> omitted, calls find_vault.py to resolve it.

Output JSON:
  {"duplicate": false}
  {"duplicate": true, "files": ["/abs/path1.md", ...], "matched_by": "frontmatter|fingerprint"}
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urlparse


def resolve_clippings_dir() -> Path:
    here = Path(__file__).resolve().parent
    out = subprocess.run(
        ["python3", str(here / "find_vault.py")],
        check=True, capture_output=True, text=True,
    )
    return Path(out.stdout.strip())


def url_fingerprint(src: str) -> Optional[str]:
    """Return a unique-enough substring for fuzzy match, or None for local paths."""
    if not src.startswith(("http://", "https://")):
        return None
    parsed = urlparse(src)
    segments = [s for s in parsed.path.split("/") if len(s) >= 6]
    if segments:
        return segments[-1]
    if parsed.query:
        for pair in parsed.query.split("&"):
            if "=" in pair:
                _, v = pair.split("=", 1)
                if len(v) >= 6:
                    return v
    return None


def extract_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    return text[:end] if end > 0 else ""


_FIELD_RE = re.compile(r"^(source|url)\s*:\s*(.+?)\s*$", re.MULTILINE | re.IGNORECASE)


def find_matches(src: str, clippings: Path) -> Tuple[List[Path], str]:
    if not clippings.is_dir():
        return [], ""

    frontmatter_hits: List[Path] = []
    fingerprint_hits: List[Path] = []
    fp = url_fingerprint(src)

    for md in clippings.glob("*.md"):
        try:
            text = md.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        # Stage 1: frontmatter source/url fields
        front = extract_frontmatter(text)
        for m in _FIELD_RE.finditer(front):
            value = m.group(2).strip().strip('"\'')
            if value == src:
                frontmatter_hits.append(md)
                break
        else:
            # Stage 2: fingerprint grep on full file (only if not already in stage-1)
            if fp and fp in text:
                fingerprint_hits.append(md)

    if frontmatter_hits:
        return frontmatter_hits, "frontmatter"
    if fingerprint_hits:
        return fingerprint_hits, "fingerprint"
    return [], ""


def main():
    if len(sys.argv) < 2:
        sys.stderr.write("usage: check_duplicate.py <source> [<clippings-dir>]\n")
        sys.exit(2)
    src = sys.argv[1]
    clippings = Path(sys.argv[2]) if len(sys.argv) >= 3 else resolve_clippings_dir()
    matches, how = find_matches(src, clippings)
    if matches:
        print(json.dumps({
            "duplicate": True,
            "matched_by": how,
            "files": [str(m) for m in matches],
        }, ensure_ascii=False))
    else:
        print(json.dumps({"duplicate": False}))


if __name__ == "__main__":
    main()
