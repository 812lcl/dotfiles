---
name: brain
description: "Personal knowledge base CLI — your long-term memory across sessions. Use when the user asks about 记录, 知识库, memo, note, dsat, insight, knowledge, preference, todo, checkpoint, or any persistent capture/recall task. Also load at the start of any non-trivial task and run brain brief to absorb durable preferences and recent context in one shot."
---

# Brain Knowledge System

Pure-data CLI for capture + search across sessions. No LLM calls — intelligence
comes from this agent.

## Session Start

Before any non-trivial task:
1. `brain cat BRAIN.md` — philosophy, triggers, user-owned rules. **BRAIN.md is part of memory, not just a command reference.** Re-read when uncertain or when the user mentions a trigger word.
2. `brain brief` — preferences + recent memo / notes / open todos.
3. `brain search "<topic>"` whenever the user references prior work.

If SKILL.md (this file) and BRAIN.md disagree, **BRAIN.md wins**.

## Trigger Words

| User says... | Do this |
|--------------|---------|
| "checkpoint" / "存档" / "记一下" | Run `brain checkpoint` — it prints the routing playbook (memo mandatory, note for long content, `--ref` back, slug rules) plus recent slugs for reuse. Follow its output. |
| "preference" / "from now on" / "以后..." | `brain preference add -s <slug> -m "<rule>"` |
| "todo" / "记个 TODO" | `brain todo add -s <slug> -m "..." -p P1` |
| Hits an anti-pattern / mistake | `brain dsat add -m "..." -t <tag>` immediately |
| Non-obvious finding | `brain insight add -s <slug>` |
| "what did we...", "last time..." | `brain search` first; cite slugs. **Search is rg literal/regex** — cover synonyms via `'a\|b\|中文'` or repeatable `-e`; fall back to `<layer> list --since 7d` if nothing hits. |
| Stable conclusion ready | `brain knowledge add -c <cat> -n <name>` |

## Commands

| Task | Command |
|------|---------|
| Session brief (preferences + recent activity) | `brain brief [--since 7d] [--limit 20]` |
| Sedimentation playbook + recent slugs | `brain checkpoint` — run when a turn is worth recording; follow its output |
| Quick capture (≤5 lines) | `brain memo add -s slug -m "..." -t tag` |
| Process doc / debug log | `brain note add -s "slug"` — appends to existing slug across days; `-w` forces fresh |
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
| Write / append / cp / diff / commit | `brain <op> <path>` — writes auto-sync |
| Shell ops (full shell, pipes, globs) | `brain exec <cmd...>` — $SHELL -c at brain root, auto-syncs + lints |
| Sandboxed shortcuts (brain root only) | `brain cat` / `brain ls` / `brain rm` |
| Raw shortcuts (arbitrary code; no path sandbox) | `brain python` (=python3) / `brain bash` |
| Mark old entries superseded (dream prune) | `brain supersede <new-path> <old-path>... [--force]` |
| Validate frontmatter | `brain lint` |

## TODO Lifecycle

`brain todo add` → `brain todo start <slug>` → `brain todo done <slug>`

## Session lifecycle

Codex's Stop hook (installed by `brain install codex`) tells you to run `brain checkpoint` at session end. Its output leads with the **worth sedimenting?** judgment — if not worth it (pure Q&A, reading files, confirming config), write nothing and just stop; don't write a junk memo. If worth it, follow the playbook (memo/note routing, slug rules, recent slugs for reuse). After recording, just stop. The memo is the record; no extra summary to the user.

## Rules

1. Paths are relative to brain root — works from any CWD; never print or assume the brain's absolute filesystem location
2. Read BRAIN.md at session start and whenever uncertain; BRAIN.md > SKILL.md on conflict.
3. memo vs note routing. `brain memo` = one-line "what was done" (≤200 chars). `brain note` = substantive long content (narrative/decisions/debug/analysis/code excerpts) — write it when it exists, otherwise skip. When paired: write the note first, then the memo with `--ref notes/<path>`, same slug.
4. "checkpoint" trigger (user-initiated) runs the same `brain checkpoint` command and follows the same routing.
5. Structured adds (memo/dsat/insight/todo/preference/note) auto-sync (write-through)
5. For knowledge/ and tools/ — edit files directly, then `brain commit`
6. `brain cp` validates frontmatter on copy to structured layers
7. Full reference: `brain cat BRAIN.md`

## Shell delegation

Read, list, remove, and tool execution all delegate to the user's shell via
`brain exec`:

  brain exec cat knowledge/code-gateway.md
  brain exec ls -la memo/2026/06/
  brain exec rm memo/2026/06/02/foo.md
  brain exec ./tools/xray.py UID

After the command exits, brain runs `brain lint` (silent if clean,
surfaces findings if structured-layer frontmatter is broken) and auto-syncs.

For common cases there are also direct shortcuts that pass args verbatim
(no shell re-parse) and inherit the same lint + auto-sync:

  brain cat <path>
  brain ls  [path]
  brain rm  <path>
  brain python <args>     # runs python3 (e.g. brain python ./tools/xray.py UID)
  brain bash <args>
