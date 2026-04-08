#!/usr/bin/env bash
# Fetch a URL as Markdown via proxy cascade.
# Special thanks to joeseesun for the excellent qiaomu-markdown-proxy project,
# which inspired the proxy cascade design and fallback logic in this script.
# https://github.com/joeseesun/qiaomu-markdown-proxy
# Usage: fetch.sh <url> [proxy_url]
# Example: fetch.sh https://example.com http://127.0.0.1:7890
set -euo pipefail

URL="${1:?Usage: fetch.sh <url> [proxy_url]}"
PROXY="${2:-}"

_curl() {
  if [ -n "$PROXY" ]; then
    https_proxy="$PROXY" http_proxy="$PROXY" curl -sL "$@"
  else
    curl -sL "$@"
  fi
}

_has_content() {
  [ "$(echo "$1" | wc -l)" -gt 5 ] && echo "$1" | grep -qv "Don't miss what's happening"
}

# 1. defuddle.md - cleaner output with YAML frontmatter
OUT=$(_curl "https://defuddle.md/$URL" 2>/dev/null || true)
if _has_content "$OUT"; then echo "$OUT"; exit 0; fi

# 2. r.jina.ai - wide coverage, preserves image links
OUT=$(_curl "https://r.jina.ai/$URL" 2>/dev/null || true)
if _has_content "$OUT"; then echo "$OUT"; exit 0; fi

# 3. agent-fetch - last resort local tool
OUT=$(npx --yes agent-fetch "$URL" --json 2>/dev/null || true)
if [ -n "$OUT" ]; then echo "$OUT"; exit 0; fi

echo "ERROR: All fetch methods failed for: $URL" >&2
exit 1
