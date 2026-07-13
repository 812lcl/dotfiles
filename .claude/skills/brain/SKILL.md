---
name: brain
description: "Personal knowledge base CLI — your long-term memory across sessions. Use when the user asks about 记录, 知识库, memo, note, dsat, insight, knowledge, preference, todo, checkpoint, or any persistent capture/recall task. Also load at the start of any non-trivial task and run brain brief to absorb recent project-grouped context in one shot."
---

# Brain Knowledge System

The `brain` CLI manages your personal knowledge base. Paths printed by commands are always relative to the brain root — never reveal or assume an absolute filesystem location.

## Session Start

Before any non-trivial task:

1. `brain brief` — recent memo / notes / open todos, grouped by project.
2. `brain search "<topic>"` whenever the user references prior work.
3. Read `BRAIN.md` when uncertain about brain rules, conventions, or trigger words.

If SKILL.md (this file) and BRAIN.md disagree, **BRAIN.md wins** — it
carries user-owned rules.

## Trigger Words

| User says... | Do this |
|--------------|---------|
| "checkpoint" / "存档" / "记一下" | Run `brain checkpoint` — it prints the routing playbook, including note-first process records, memo `--ref` back, slug rules, and recent slugs for reuse. Follow its output. |
| "preference" / "from now on" / "以后..." | 先过门槛：**跨项目通用**才写 `brain preference add -s <slug> -m "<rule>"`；只对某项目/仓库成立 → `brain knowledge add`（自带 project 标签） |
| "todo" / "记个 TODO" | `brain todo add -s <slug> -m "..." -p P1` |
| Hits an anti-pattern / mistake | `brain dsat add -m "..." -t <tag>` — immediate, don't defer |
| Non-obvious finding | `brain insight add -s <slug>` |
| "what did we...", "last time..." | `brain search "<topic>"` first; cite slugs. **Search is rg literal/regex** — use `'a\|b\|中文'` or repeatable `-e` for synonyms; fall back to `<layer> list --since 7d`. |
| Stable conclusion ready | `brain knowledge add -c <cat> -n <name>` |

## Commands

| Task | Command |
|------|---------|
| Session brief (this-project vs other-projects) | `brain brief [--since 7d] [--limit 20]` |
| Sedimentation playbook + recent slugs | `brain checkpoint` — run when a turn is worth recording; follow its output |
| Non-trivial process record | `brain note add -s slug` first, then `brain memo add -s slug -m "..." --ref notes/<path>` |
| Trivial / quick capture | `brain memo add -s slug -m "..." -t tag` |
| Process doc / debug log | `brain note add -s "slug"` — appends to the most recent note with this slug (across days); `-w` forces a fresh today's file |
| Mistake / anti-pattern | `brain dsat add -m "..." -t tag` |
| Non-obvious finding | `brain insight add -s "slug"` |
| Stable conclusion | `brain knowledge add -c category -n name [--from file]` |
| Durable **cross-project** collab rule (project-specific → knowledge) | `brain preference add -s slug -m "rule"` |
| Task tracking | `brain todo add -s slug -m "..." -p P1 -t tag` |
| Todo events | `brain todo block|resume|log|label|assign|priority|show <slug> ...` |
| List a layer (filter by project) | `brain <layer> list [--since 7d] [-t tag] [-P project] [--limit N]` (`-P .` = current dir's project) |
| Show full content for a slug | `brain <memo|note|dsat|insight> show <slug>` (all timestamped files, chronological) |
| List knowledge w/ titles | `brain knowledge list [-c category] [-t tag] [-P project] [--since 7d] [--limit N]` |
| List tools w/ descriptions | `brain tools list` |
| Search (rg literal/regex; OR via -e or \|; grouped by project+slug with hits=N) | `brain search "q1" [-e q2 -e q3] [-l layer]` |
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
2. Run `brain brief` at the start of non-trivial work; read BRAIN.md when uncertain; BRAIN.md > SKILL.md on conflict.
3. UserPromptSubmit hook injects a query-start reminder to run `brain brief` for non-trivial tasks; the Stop hook runs `brain sync --quiet --background` silently at turn end.
4. memo vs note routing. Record only useful information worth sedimenting. For non-trivial work that produced durable value, write `brain note` as the process record (what changed, decisions, debug trail, caveats), then write `brain memo` as the short "what was done" index (≤200 chars) with `--ref notes/<path>`. For trivial work, either a memo alone is enough or nothing should be written.
5. "checkpoint" trigger (user-initiated) runs the same `brain checkpoint` command and follows the same routing.
6. Structured adds (memo/dsat/insight/todo/preference/note) auto-sync (write-through)
7. Read / list / remove / run tools go through `brain exec <cmd>` (full shell, pipes, globs) OR the shortcuts `brain cat` / `brain ls` / `brain rm` / `brain python` (=python3) / `brain bash` (args verbatim, no shell re-parse). Both inherit auto-sync + lint.
8. For knowledge/ and tools/ — edit files directly (via `brain exec $EDITOR` or your IDE), then `brain commit`
9. `brain cp` validates frontmatter on copy to structured layers
10. Full reference: `brain cat BRAIN.md`
