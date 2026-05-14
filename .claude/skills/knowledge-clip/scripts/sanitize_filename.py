#!/usr/bin/env python3
"""
Build a safe filename for a clip note.

Convention: "[<类型>] <清洗后的标题>.md"

  - Replace cross-platform illegal chars  / \\ : * ? " < > |  with full-width equivalents
  - Collapse whitespace
  - Strip leading/trailing dots and spaces
  - Truncate to 120 chars (excluding the prefix and `.md`)

Usage:
  sanitize_filename.py "<type>" "<title>"
"""

import re
import sys

ILLEGAL = {
    "/": "／",
    "\\": "＼",
    ":": "：",
    "*": "＊",
    "?": "？",
    "\"": "＂",
    "<": "＜",
    ">": "＞",
    "|": "｜",
}


def sanitize_title(title: str, max_len: int = 120) -> str:
    for bad, good in ILLEGAL.items():
        title = title.replace(bad, good)
    # collapse whitespace
    title = re.sub(r"\s+", " ", title).strip()
    # strip leading/trailing dots and spaces (macOS / Windows)
    title = title.strip(". ")
    if not title:
        title = "未命名"
    if len(title) > max_len:
        title = title[:max_len].rstrip()
    return title


def build_filename(clip_type: str, title: str) -> str:
    return f"[{clip_type}] {sanitize_title(title)}.md"


def main():
    if len(sys.argv) != 3:
        sys.stderr.write("usage: sanitize_filename.py <type> <title>\n")
        sys.exit(2)
    print(build_filename(sys.argv[1], sys.argv[2]))


if __name__ == "__main__":
    main()
