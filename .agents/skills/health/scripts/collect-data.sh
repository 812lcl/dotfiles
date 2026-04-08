#!/usr/bin/env bash
# Collect Claude Code configuration data for health audit.
# Outputs labeled sections for each data source.
# Run from any directory; uses pwd as the project root.
set -euo pipefail

P=$(pwd)
SETTINGS="$P/.claude/settings.local.json"

echo "[1/10] Tier metrics..."
echo "=== TIER METRICS ==="
echo "project_files: $(git -C "$P" ls-files 2>/dev/null | wc -l || find "$P" -type f -not -path "*/.git/*" -not -path "*/node_modules/*" -not -path "*/dist/*" -not -path "*/build/*" | wc -l)"
echo "contributors: $(git -C "$P" log -n 500 --format='%ae' 2>/dev/null | sort -u | wc -l)"
echo "ci_workflows:  $(ls "$P/.github/workflows/"*.yml "$P/.github/workflows/"*.yaml 2>/dev/null | wc -l)"
echo "skills:        $(find "$P/.claude/skills" -name "SKILL.md" 2>/dev/null | grep -v '/health/SKILL.md' | wc -l)"
echo "claude_md_lines: $(wc -l < "$P/CLAUDE.md" 2>/dev/null)"

echo "[2/10] CLAUDE.md (global + local)..."
echo "=== CLAUDE.md (global) ===" ; cat ~/.claude/CLAUDE.md 2>/dev/null || echo "(none)"
echo "=== CLAUDE.md (local) ===" ; cat "$P/CLAUDE.md" 2>/dev/null || echo "(none)"

echo "[3/10] Settings, hooks, MCP..."
echo "=== settings.local.json ===" ; cat "$SETTINGS" 2>/dev/null || echo "(none)"

echo "[4/10] Rules + skill descriptions..."
echo "=== rules/ ===" ; find "$P/.claude/rules" -name "*.md" 2>/dev/null | while IFS= read -r f; do echo "--- $f ---"; cat "$f"; done
echo "=== skill descriptions ===" ; { [ -d "$P/.claude/skills" ] && grep -r "^description:" "$P/.claude/skills" 2>/dev/null; grep -r "^description:" ~/.claude/skills 2>/dev/null; } | sort -u

echo "[5/10] Context budget estimate..."
echo "=== STARTUP CONTEXT ESTIMATE ==="
echo "global_claude_words: $(wc -w < ~/.claude/CLAUDE.md 2>/dev/null | tr -d ' ' || echo 0)"
echo "local_claude_words: $(wc -w < "$P/CLAUDE.md" 2>/dev/null | tr -d ' ' || echo 0)"
echo "rules_words: $(find "$P/.claude/rules" -name "*.md" 2>/dev/null | while IFS= read -r f; do cat "$f"; done | wc -w | tr -d ' ')"
echo "skill_desc_words: $({ [ -d "$P/.claude/skills" ] && grep -r "^description:" "$P/.claude/skills" 2>/dev/null; grep -r "^description:" ~/.claude/skills 2>/dev/null; } | wc -w | tr -d ' ')"
python3 -c "
import json, sys
try:
    d = json.load(open('$SETTINGS'))
except Exception as e:
    msg = '(unavailable: settings.local.json missing or malformed)'
    print('=== hooks ==='); print(msg)
    print('=== MCP ==='); print(msg)
    print('=== MCP FILESYSTEM ==='); print(msg)
    print('=== allowedTools count ==='); print(msg)
    sys.exit(0)

print('=== hooks ===')
print(json.dumps(d.get('hooks', {}), indent=2))

print('=== MCP ===')
s = d.get('mcpServers', d.get('enabledMcpjsonServers', {}))
names = list(s.keys()) if isinstance(s, dict) else list(s)
n = len(names)
print(f'servers({n}):', ', '.join(names))
est = n * 25 * 200
print(f'est_tokens: ~{est} ({round(est/2000)}% of 200K)')

print('=== MCP FILESYSTEM ===')
if isinstance(s, list):
    print('filesystem_present: (array format -- check .mcp.json)')
    print('allowedDirectories: (not detectable)')
else:
    fs = s.get('filesystem') if isinstance(s, dict) else None; a = []
    if isinstance(fs, dict):
        a = fs.get('allowedDirectories') or (fs.get('config', {}).get('allowedDirectories') if isinstance(fs.get('config'), dict) else [])
        if not a and isinstance(fs.get('args'), list):
            args = fs['args']
            for i, v in enumerate(args):
                if v in ('--allowed-directories', '--allowedDirectories') and i+1 < len(args): a = [args[i+1]]; break
            if not a: a = [v for v in args if v.startswith('/') or (v.startswith('~') and len(v) > 1)]
    print('filesystem_present:', 'yes' if fs else 'no')
    print('allowedDirectories:', a or '(missing or not detected)')

print('=== allowedTools count ===')
print(len(d.get('permissions', {}).get('allow', [])))
" 2>/dev/null || echo "(unavailable)"
echo "[6/10] Nested CLAUDE.md + gitignore..."
echo "=== NESTED CLAUDE.md ===" ; find "$P" -maxdepth 4 -name "CLAUDE.md" -not -path "$P/CLAUDE.md" -not -path "*/.git/*" -not -path "*/node_modules/*" 2>/dev/null || echo "(none)"
echo "=== GITIGNORE ==="
_GITIGNORE_HIT=$(git -C "$P" check-ignore -v .claude/settings.local.json 2>/dev/null || true)
if [ -n "$_GITIGNORE_HIT" ]; then
  _GITIGNORE_SOURCE=${_GITIGNORE_HIT%%:*}
  case "$_GITIGNORE_SOURCE" in
    .gitignore|.claude/.gitignore)
      echo "settings.local.json: gitignored"
      ;;
    *)
      echo "settings.local.json: ignored only by non-project rule ($_GITIGNORE_SOURCE) -- add a repo-local ignore rule"
      ;;
  esac
else
  echo "settings.local.json: NOT gitignored -- risk of committing tokens/credentials"
fi
echo "[7/10] HANDOFF.md + MEMORY.md..."
echo "=== HANDOFF.md ===" ; cat "$P/HANDOFF.md" 2>/dev/null || echo "(none)"
echo "=== MEMORY.md ===" ; cat "$HOME/.claude/projects/-$(pwd | sed 's|[/_]|-|g; s|^-||')/memory/MEMORY.md" 2>/dev/null | head -50 || echo "(none)"

echo "[8/10] Conversation extract (up to 2 recent sessions)..."
echo "=== CONVERSATION FILES ==="
PROJECT_PATH=$(pwd | sed 's|[/_]|-|g; s|^-||')
CONVO_DIR=~/.claude/projects/-${PROJECT_PATH}
ls -lhS "$CONVO_DIR"/*.jsonl 2>/dev/null | head -10

echo "=== CONVERSATION EXTRACT (up to 2 most recent, confidence improves with more files) ==="
# Skip the active session, it may still be incomplete.
_PREV_FILES=$(ls -t "$CONVO_DIR"/*.jsonl 2>/dev/null | tail -n +2 | head -2)
if [ -n "$_PREV_FILES" ]; then
  echo "$_PREV_FILES" | while IFS= read -r F; do
    [ -f "$F" ] || continue
    echo "--- file: $F ---"
    head -c 512000 "$F" | jq -r '
      if .type == "user" then "USER: " + ((.message.content // "") | if type == "array" then map(select(.type == "text") | .text) | join(" ") else . end)
      elif .type == "assistant" then
        "ASSISTANT: " + ((.message.content // []) | map(select(.type == "text") | .text) | join("\n"))
      else empty
      end
    ' 2>/dev/null | grep -v "^ASSISTANT: $" | head -150 || echo "(unavailable: jq not installed or parse error)"
  done
else
  echo "(no conversation files)"
fi

echo "=== MCP ACCESS DENIALS ==="
ls -t "$CONVO_DIR"/*.jsonl 2>/dev/null | head -5 | while IFS= read -r F; do
  head -c 1048576 "$F" | grep -Em 2 'Access denied - path outside allowed directories|tool-results/.+ not in ' 2>/dev/null
done | head -20

# --- Skill scan ---
# Exclude self by frontmatter name, stable across install paths.
SELF_SKILL=$( (grep -rl '^name: health$' "$P/.claude/skills" "$HOME/.claude/skills" 2>/dev/null || true) | grep 'SKILL.md' | head -1)
[ -z "$SELF_SKILL" ] && SELF_SKILL="health/SKILL.md"

echo "[9/10] Skill inventory + frontmatter + provenance..."
echo "=== SKILL INVENTORY ==="
for DIR in "$P/.claude/skills" "$HOME/.claude/skills"; do
  [ -d "$DIR" ] || continue
  find -L "$DIR" -maxdepth 4 -name "SKILL.md" 2>/dev/null | grep -v "$SELF_SKILL" | while IFS= read -r f; do
    WORDS=$(wc -w < "$f" | tr -d ' ')
    IS_LINK="no"; LINK_TARGET=""
    SKILL_DIR=$(dirname "$f")
    if [ -L "$SKILL_DIR" ]; then
      IS_LINK="yes"; LINK_TARGET=$(readlink -f "$SKILL_DIR")
    fi
    echo "path=$f words=$WORDS symlink=$IS_LINK target=$LINK_TARGET"
  done
done

echo "=== SKILL FRONTMATTER ==="
for DIR in "$P/.claude/skills" "$HOME/.claude/skills"; do
  [ -d "$DIR" ] || continue
  find -L "$DIR" -maxdepth 4 -name "SKILL.md" 2>/dev/null | grep -v "$SELF_SKILL" | while IFS= read -r f; do
    if head -1 "$f" | grep -q '^---'; then
      echo "frontmatter=yes path=$f"
      sed -n '2,/^---$/p' "$f" | head -10
    else
      echo "frontmatter=MISSING path=$f"
    fi
  done
done

echo "=== SKILL SYMLINK PROVENANCE ==="
for DIR in "$P/.claude/skills" "$HOME/.claude/skills"; do
  [ -d "$DIR" ] || continue
  find "$DIR" -maxdepth 1 -type l 2>/dev/null | while IFS= read -r link; do
    TARGET=$(readlink -f "$link")
    echo "link=$(basename "$link") target=$TARGET"
    GIT_ROOT=$(git -C "$TARGET" rev-parse --show-toplevel 2>/dev/null || echo "")
    if [ -n "$GIT_ROOT" ]; then
      REMOTE=$(git -C "$GIT_ROOT" remote get-url origin 2>/dev/null || echo "unknown")
      COMMIT=$(git -C "$GIT_ROOT" rev-parse --short HEAD 2>/dev/null || echo "unknown")
      echo "  git_remote=$REMOTE commit=$COMMIT"
    fi
  done
done

echo "[10/10] Skill content sample + security scan..."
echo "=== SKILL FULL CONTENT (sample: up to 3 skills, 60 lines each) ==="
{ for DIR in "$P/.claude/skills" "$HOME/.claude/skills"; do
    [ -d "$DIR" ] || continue
    find -L "$DIR" -maxdepth 4 -name "SKILL.md" 2>/dev/null | grep -v "$SELF_SKILL"
  done
} | head -3 | while IFS= read -r f; do
  echo "--- FULL: $f ---"
  head -60 "$f"
done
