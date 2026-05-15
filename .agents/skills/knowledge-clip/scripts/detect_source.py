#!/usr/bin/env python3
"""
Detect the type of a clip source.

Input: a URL or a filesystem path (positional arg).
Output: JSON with {type, media, handler, url_or_path}

  type:    播客 | 文章 | 视频 | 推文 | PDF | 笔记
  media:   小宇宙 | 微信公众号 | 少数派 | 知乎 | 微博 | YouTube | B站 | X
           | Substack | Medium | 博客 | 本地
  handler: xiaoyuzhou | yt-dlp | autocli-twitter | autocli-bilibili
           | defuddle | pdf | local-text

Usage:
  detect_source.py "<url-or-path>"
"""

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


RULES = [
    # (regex on host+path, type, media, handler)
    (r"xiaoyuzhoufm\.com", "播客", "小宇宙", "xiaoyuzhou"),
    (r"(youtube\.com|youtu\.be)", "视频", "YouTube", "yt-dlp"),
    (r"(bilibili\.com|b23\.tv)", "视频", "B站", "autocli-bilibili"),
    (r"(twitter\.com|x\.com)", "推文", "X", "autocli-twitter"),
    (r"mp\.weixin\.qq\.com", "文章", "微信公众号", "defuddle"),
    (r"sspai\.com", "文章", "少数派", "defuddle"),
    (r"zhihu\.com", "文章", "知乎", "defuddle"),
    (r"weibo\.com", "文章", "微博", "defuddle"),
    (r"substack\.com", "文章", "Substack", "defuddle"),
    (r"medium\.com", "文章", "Medium", "defuddle"),
]


def detect(src: str) -> dict:
    # Local path?
    if not src.startswith(("http://", "https://")):
        p = Path(src).expanduser()
        suffix = p.suffix.lower()
        if suffix == ".pdf":
            return dict(type="PDF", media="本地", handler="pdf", url_or_path=str(p))
        if suffix in {".md", ".markdown", ".txt"}:
            return dict(type="笔记", media="本地", handler="local-text", url_or_path=str(p))
        return dict(type="笔记", media="本地", handler="local-text", url_or_path=str(p))

    parsed = urlparse(src)
    haystack = (parsed.netloc + parsed.path).lower()

    for pattern, _type, _media, _handler in RULES:
        if re.search(pattern, haystack):
            return dict(type=_type, media=_media, handler=_handler, url_or_path=src)

    # Generic web article fallback
    return dict(type="文章", media="博客", handler="defuddle", url_or_path=src)


def main():
    if len(sys.argv) != 2:
        sys.stderr.write("usage: detect_source.py <url-or-path>\n")
        sys.exit(2)
    print(json.dumps(detect(sys.argv[1]), ensure_ascii=False))


if __name__ == "__main__":
    main()
