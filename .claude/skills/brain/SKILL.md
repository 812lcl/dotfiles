---
name: brain
description: "Personal knowledge base CLI — your long-term memory across sessions. Use when the user asks about 记录, 知识库, memo, note, dsat, insight, knowledge, preference, todo, checkpoint, or any persistent capture/recall task. Also load at the start of any non-trivial task and run brain brief to absorb durable preferences and recent context in one shot."
---

# Brain Knowledge System

The `brain` CLI manages your personal knowledge base. Paths printed by commands are always relative to the brain root — never reveal or assume an absolute filesystem location.

## Session Start

At the start of any non-trivial task:

1. `brain cat BRAIN.md` — read the brain's philosophy, triggers, and user-owned rules. **BRAIN.md is part of the memory, not just a command reference.** Re-read whenever you're uncertain about brain conventions or when the user mentions "rules", "philosophy", or any trigger word.
2. `brain brief` — preferences + recent memo / notes / open todos.
3. `brain search` whenever the user references prior work.

If SKILL.md (this file) and BRAIN.md disagree, **BRAIN.md wins** — it
carries user-owned rules.

## Trigger Words

| User says... | Do this |
|--------------|---------|
| "checkpoint" / "存档" / "记一下" | 写一条 episodic 记录：`brain memo add -s <slug> -m "..."` (≤200 chars, past tense). If there's substantive long content worth re-reading (narrative / decisions / debug / analysis / code excerpts), write the note FIRST: `brain note add -s <slug>` (body from stdin or $EDITOR), THEN add `--ref notes/<path>` to the memo so it points back. Same slug across the pair. |
| "preference" / "from now on" / "以后..." | `brain preference add -s <slug> -m "<rule>"` |
| "todo" / "记个 TODO" | `brain todo add -s <slug> -m "..." -p P1` |
| Hits an anti-pattern / mistake | `brain dsat add -m "..." -t <tag>` — immediate, don't defer |
| Non-obvious finding | `brain insight add -s <slug>` |
| "what did we...", "last time..." | `brain search "<topic>"` first; cite slugs. **Search is rg literal/regex** — use `'a\|b\|中文'` or repeatable `-e` for synonyms; fall back to `<layer> list --since 7d`. |
| Stable conclusion ready | `brain knowledge add -c <cat> -n <name>` |

## Commands

| Task | Command |
|------|---------|
| Session brief (preferences + recent activity) | `brain brief [--since 7d] [--limit 20]` |
| Quick capture (≤5 lines) | `brain memo add -s slug -m "..." -t tag` |
| Process doc / debug log | `brain note add -s "slug"` — appends to the most recent note with this slug (across days); `-w` forces a fresh today's file |
| Mistake / anti-pattern | `brain dsat add -m "..." -t tag` |
| Non-obvious finding | `brain insight add -s "slug"` |
| Stable conclusion | `brain knowledge add -c category -n name [--from file]` |
| Durable collab rule | `brain preference add -s slug -m "rule"` |
| Task tracking | `brain todo add -s slug -m "..." -p P1 -t tag` |
| Todo events | `brain todo block|resume|log|label|assign|priority|show <slug> ...` |
| List a layer | `brain <layer> list [--since 7d] [-t tag] [--limit N]` |
| Show full content for a slug | `brain <memo|note|dsat|insight> show <slug>` (all timestamped files, chronological) |
| List knowledge w/ titles | `brain knowledge list [-c category] [-t tag] [--since 7d] [--limit N]` |
| List tools w/ descriptions | `brain tools list` |
| Search (rg literal/regex; OR via -e or \|) | `brain search "q1" [-e q2 -e q3] [-l layer]` |
| Write file | `echo content | brain write <path>` (auto-sync) |
| Append to file | `echo update | brain append <path>` (auto-sync) |
| Copy local file in | `brain cp ./file <brain-path>` (frontmatter-validated) |
| Run shell cmd (pipes, globs) | `brain exec <cmd...>` — auto-sync + lint after |
| Sandboxed shortcuts (path-confined to brain root) | `brain cat` / `brain ls` / `brain rm` — rejects `../` and absolute paths outside brain |
| Raw shortcuts (no path sandbox) | `brain python` (=python3) / `brain bash` — can execute arbitrary code; sandbox would be theatre |
| Mark old entries superseded (dream prune) | `brain supersede <new-path> <old-path>... [--force]` — appends `superseded-by:` frontmatter; idempotent; refuses to overwrite a different target unless `--force` |
| Frontmatter check | `brain lint` |
| Show changes | `brain diff` |
| Commit + push | `brain commit "message"` |

## TODO Lifecycle

`brain todo add` → `brain todo start <slug>` → `brain todo done <slug>`

## Rules

1. Paths are relative to brain root — works from any CWD; never hard-code or print the brain's absolute filesystem location
2. **Read BRAIN.md** at session start and whenever uncertain; it carries the philosophy, triggers, and user-owned rules. BRAIN.md > SKILL.md on conflict.
3. Session end Stop hook prompts you to judge if this turn is **worth sedimenting** — decisions, mistakes, plans, unfinished work, non-obvious findings. Pure Q&A / reading files / confirming config is NOT worth sedimenting; just stop. When it is worth it, write the memo (and a note for substantive long content). Reuse the same slug across turns of the same topic (multiple timestamped memos group by slug; `brain append memo/<path>` extends an existing file). Change slug only when topic shifts. slug describes the task (fix-xxx / import-yyy / review-mr-zzz), never a timestamp. After recording, just stop — don't surface a summary to the user. Hook also auto-commits and pushes.
4. memo vs note routing. `brain memo` carries the one-line "what was done" (≤200 chars) and is the index. `brain note` carries the substantive long content worth re-reading (process narrative, decisions, debug trail, analysis, code excerpts). When both exist, write the note FIRST, then add `--ref notes/<path>` to the memo so it points back. Both share the same slug. Skip the note when there is nothing worth narrating beyond the memo.
5. "checkpoint" trigger (user-initiated) follows the same routing: memo always, note when there is long content, memo `--ref`s the note.
6. Structured adds (memo/dsat/insight/todo/preference/note) auto-sync (write-through)
7. Read / list / remove / run tools go through `brain exec <cmd>` (full shell, pipes, globs) OR the shortcuts `brain cat` / `brain ls` / `brain rm` / `brain python` (=python3) / `brain bash` (args verbatim, no shell re-parse). Both inherit auto-sync + lint.
8. For knowledge/ and tools/ — edit files directly (via `brain exec $EDITOR` or your IDE), then `brain commit`
9. `brain cp` validates frontmatter on copy to structured layers
10. Full reference: `brain cat BRAIN.md`
