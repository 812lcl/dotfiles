#!/usr/bin/env bash
# Claude Code statusline command
# Displays: [user@host dir] branch [git-diff-summary] model [ctx] [tokens] | IDE:file

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

# --- Current token usage + totals + cache hit rate ---
# Format: [↑1.2K↓0.3K | Σ↑45K↓12K | $87%]
current_usage=""
current_in=$(echo "$input" | jq -r '.context_window.current_usage.input_tokens // empty')
current_cache_read=$(echo "$input" | jq -r '.context_window.current_usage.cache_read_input_tokens // 0')
current_out=$(echo "$input" | jq -r '.context_window.current_usage.output_tokens // empty')
total_in_all=$(echo "$input" | jq -r '.context_window.total_input_tokens // empty')
total_out_all=$(echo "$input" | jq -r '.context_window.total_output_tokens // empty')
if [ -n "$current_in" ] && [ -n "$current_out" ]; then
  # Current round: input + cache_read as effective input
  round_in=$((current_in + current_cache_read))
  round_in_k=$(awk "BEGIN { printf \"%.1f\", $round_in / 1000 }")
  round_out_k=$(awk "BEGIN { printf \"%.1f\", $current_out / 1000 }")

  # Cache hit rate: cache_read / (input + cache_read)
  cache_pct=$(awk "BEGIN { if ($round_in > 0) printf \"%.0f\", $current_cache_read * 100 / $round_in; else print \"0\" }")

  # Build usage string
  usage_str=$(printf '↑%sK↓%sK' "$round_in_k" "$round_out_k")

  # Totals (if available)
  if [ -n "$total_in_all" ] && [ -n "$total_out_all" ]; then
    total_in_k=$(awk "BEGIN { printf \"%.1f\", $total_in_all / 1000 }")
    total_out_k=$(awk "BEGIN { printf \"%.1f\", $total_out_all / 1000 }")
    usage_str=$(printf '%s | Σ↑%sK↓%sK' "$usage_str" "$total_in_k" "$total_out_k")
  fi

  # Cache hit rate
  usage_str=$(printf '%s | $%s%%' "$usage_str" "$cache_pct")

  current_usage=$(printf ' \033[1;90m[%s]\033[0m' "$usage_str")
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

# --- Token/Cost statistics via ccusage ---
fmt_tokens() {
  local n="$1"
  awk "BEGIN {
    n = $n + 0
    if (n >= 1000000) { printf \"%.1fM\", n/1000000 }
    else if (n >= 1000) { printf \"%.1fK\", n/1000 }
    else { printf \"%d\", n }
  }"
}

usage_stats_line=""
if command -v ccusage >/dev/null 2>&1; then
  TODAY=$(date +%Y%m%d)
  WEEK_AGO=$(date -v-6d +%Y%m%d)
  MONTH_AGO=$(date -v-29d +%Y%m%d)

  t_json=$(ccusage daily --since "$TODAY"     --json 2>/dev/null)
  w_json=$(ccusage daily --since "$WEEK_AGO"  --json 2>/dev/null)
  m_json=$(ccusage daily --since "$MONTH_AGO" --json 2>/dev/null)

  sum_json() {
    echo "$1" | jq -r '[.daily[]] | { t: ([.[].totalTokens] | add // 0), c: ([.[].totalCost] | add // 0) } | "\(.t)|\(.c)"' 2>/dev/null
  }

  t_raw=$(sum_json "$t_json")
  w_raw=$(sum_json "$w_json")
  m_raw=$(sum_json "$m_json")

  if [ -n "$t_raw" ] && [ -n "$w_raw" ] && [ -n "$m_raw" ]; then
    IFS='|' read -r t_tkns t_cost <<< "$t_raw"
    IFS='|' read -r w_tkns w_cost <<< "$w_raw"
    IFS='|' read -r m_tkns m_cost <<< "$m_raw"

    t_tkns_fmt=$(fmt_tokens "${t_tkns:-0}")
    t_cost_fmt=$(awk "BEGIN { printf \"\$%.2f\", ${t_cost:-0} }")
    w_tkns_fmt=$(fmt_tokens "${w_tkns:-0}")
    w_cost_fmt=$(awk "BEGIN { printf \"\$%.2f\", ${w_cost:-0} }")
    m_tkns_fmt=$(fmt_tokens "${m_tkns:-0}")
    m_cost_fmt=$(awk "BEGIN { printf \"\$%.2f\", ${m_cost:-0} }")

    usage_stats_line=$(printf '\033[1;90mToday: \033[0;37m%s %s\033[1;90m | 7d: \033[0;37m%s %s\033[1;90m | 30d: \033[0;37m%s %s\033[0m' \
      "$t_tkns_fmt" "$t_cost_fmt" \
      "$w_tkns_fmt" "$w_cost_fmt" \
      "$m_tkns_fmt" "$m_cost_fmt")
  fi
fi

# --- Render ---
printf '\033[1;31m[\033[1;33m%s\033[1;32m@\033[1;34m%s \033[1;35m%s\033[1;31m]\033[0m%s%s \033[1;95m%s\033[0m%s%s%s' \
  "$(whoami)" "$(hostname -s)" "$dir" \
  "$git_info" "$git_diff_summary" "$model" \
  "$ctx_info" "$current_usage" \
  "$ide_info"

# Second line: token/cost stats
if [ -n "$usage_stats_line" ]; then
  printf '\n%s' "$usage_stats_line"
fi
