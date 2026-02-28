#!/usr/bin/env bash
# Claude Code statusline command
# Displays: [user@host dir] branch model [ctx] [tokens] [git-diff-summary] | IDE:file

input=$(cat)

# --- Basic info ---
cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd')
dir=$(basename "$cwd")
model=$(echo "$input" | jq -r '.model.display_name // "Unknown"')
session_id=$(echo "$input" | jq -r '.session_id // empty')

# --- Git info ---
git_info=""
git_diff_summary=""
if git -C "$cwd" rev-parse --git-dir > /dev/null 2>&1; then
  branch=$(git -C "$cwd" --no-optional-locks branch --show-current 2>/dev/null)
  if [ -n "$branch" ]; then
    if ! git -C "$cwd" --no-optional-locks diff --quiet 2>/dev/null || \
       ! git -C "$cwd" --no-optional-locks diff --cached --quiet 2>/dev/null; then
      git_info=$(printf ' \033[1;36m⎇:(\033[0;31m%s\033[1;36m) \033[0;33m✗\033[0m' "$branch")
    else
      git_info=$(printf ' \033[1;36m⎇:(\033[0;31m%s\033[1;36m)\033[0m' "$branch")
    fi
  fi

  # --- Git diff summary (inserted/deleted lines, unstaged + staged combined) ---
  diff_numstat=$(git -C "$cwd" --no-optional-locks diff --numstat 2>/dev/null)
  diff_cached_numstat=$(git -C "$cwd" --no-optional-locks diff --cached --numstat 2>/dev/null)
  combined_numstat=$(printf '%s\n%s\n' "$diff_numstat" "$diff_cached_numstat")

  ins=0
  del=0
  while IFS=$'\t' read -r added removed _file; do
    # skip binary files (shown as "-")
    case "$added" in ''|-) continue ;; esac
    ins=$((ins + added))
    del=$((del + removed))
  done <<EOF
$combined_numstat
EOF

  untracked_count=$(git -C "$cwd" --no-optional-locks ls-files --others --exclude-standard 2>/dev/null | wc -l | tr -d ' ')

  total_changes=$((ins + del + untracked_count))
  if [ "$total_changes" -gt 0 ]; then
    parts=""
    [ "$ins" -gt 0 ] && parts=$(printf '\033[0;32m+%d\033[0m' "$ins")
    if [ "$del" -gt 0 ]; then
      [ -n "$parts" ] && parts="$parts $(printf '\033[0;31m-%d\033[0m' "$del")" \
                      || parts=$(printf '\033[0;31m-%d\033[0m' "$del")
    fi
    if [ "$untracked_count" -gt 0 ]; then
      [ -n "$parts" ] && parts="$parts $(printf '\033[0;90m?%d\033[0m' "$untracked_count")" \
                      || parts=$(printf '\033[0;90m?%d\033[0m' "$untracked_count")
    fi
    git_diff_summary=$(printf ' \033[1;90m[%s\033[1;90m]\033[0m' "$parts")
  fi
fi

# --- Context window info ---
ctx_info=""
used=$(echo "$input" | jq -r '.context_window.used_percentage // empty')
ctx_size=$(echo "$input" | jq -r '.context_window.context_window_size // empty')
if [ -n "$used" ] && [ -n "$ctx_size" ]; then
  ctx_size_k=$((ctx_size / 1000))
  ctx_info=$(printf ' \033[1;90m[ctx: %.0f%%/%dK]\033[0m' "$used" "$ctx_size_k")
fi

# --- Current token usage ---
current_usage=""
current_in=$(echo "$input" | jq -r '.context_window.current_usage.input_tokens // empty')
current_out=$(echo "$input" | jq -r '.context_window.current_usage.output_tokens // empty')
if [ -n "$current_in" ] && [ -n "$current_out" ]; then
  current_usage=$(printf ' \033[1;90m[in:%d out:%d]\033[0m' "$current_in" "$current_out")
fi

# --- IDE current file ---
# Claude Code IDE integration writes active file info to ~/.claude/ide/<session_id>/active_file
# when an IDE (VS Code / JetBrains) is connected.
ide_info=""
if [ -n "$session_id" ]; then
  ide_file="/Users/liuchunlei/.claude/ide/${session_id}/active_file"
  if [ -f "$ide_file" ]; then
    active_file=$(cat "$ide_file" 2>/dev/null)
    if [ -n "$active_file" ]; then
      file_name=$(basename "$active_file")
      ide_info=$(printf ' \033[1;90m|\033[0m \033[1;34m%s\033[0m' "$file_name")
    fi
  fi
fi

# --- Render ---
printf '\033[1;31m[\033[1;33m%s\033[1;32m@\033[1;34m%s \033[1;35m%s\033[1;31m]\033[0m%s \033[1;95m%s\033[0m%s%s%s%s' \
  "$(whoami)" "$(hostname -s)" "$dir" \
  "$git_info" "$model" \
  "$ctx_info" "$current_usage" "$git_diff_summary" \
  "$ide_info"
