#!/usr/bin/env python3
"""
Fetch episode-level metadata from a 小宇宙 page that defuddle can't reach.

defuddle's `-p image` returns the og:image meta tag, which on 小宇宙 is the
podcast-level cover (same for every episode of a show). The episode-specific
cover lives in an embedded JSON blob earlier in the HTML — extract it.

Output JSON:
  {"cover": "...", "title": "...", "pub_date": "...", "podcast": "...", "duration_sec": N}

Usage:
  xiaoyuzhou_meta.py <episode-url>
"""

import json
import re
import sys
import urllib.request


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def _decode_json_str(raw_with_quotes: str) -> str:
    try:
        return json.loads(raw_with_quotes)
    except Exception:
        return raw_with_quotes.strip('"')


def parse(html: str) -> dict:
    out: dict = {}

    # episode-level cover: first occurrence of image.picUrl (episode), the
    # second occurrence is podcast-level
    m = re.search(r'"image":\s*\{\s*"picUrl":\s*"([^"]+)"', html)
    if m:
        out["cover"] = m.group(1)

    # first JSON-encoded "title" — this is the episode title in 小宇宙's data
    m = re.search(r'"title":\s*("(?:\\.|[^"\\])*")', html)
    if m:
        out["title"] = _decode_json_str(m.group(1))

    m = re.search(r'"pubDate":\s*"([^"]+)"', html)
    if m:
        out["pub_date"] = m.group(1)

    m = re.search(r'"duration":\s*(\d+)', html)
    if m:
        out["duration_sec"] = int(m.group(1))

    # podcast title — look for a "podcast" object near top
    m = re.search(r'"podcast":\s*\{[^}]*?"title":\s*("(?:\\.|[^"\\])*")', html)
    if m:
        out["podcast"] = _decode_json_str(m.group(1))

    return out


def main():
    if len(sys.argv) != 2:
        sys.stderr.write("usage: xiaoyuzhou_meta.py <episode-url>\n")
        sys.exit(2)
    print(json.dumps(parse(fetch(sys.argv[1])), ensure_ascii=False))


if __name__ == "__main__":
    main()
