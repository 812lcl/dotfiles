---
name: brain
description: "Personal knowledge base CLI — your long-term memory across sessions. Use when the user asks about 记录, 知识库, memo, note, dsat, insight, knowledge, preference, todo, checkpoint, or any persistent capture/recall task. Also load at the start of any non-trivial task and run brain brief to absorb recent project-grouped context in one shot."
---

# Brain Knowledge System

Pure-data CLI for capture + search across sessions. No LLM calls — intelligence
comes from this agent.

## Session Start

Before any non-trivial task:
1. `brain brief` — recent memo / notes / open todos, grouped by project.
2. `brain search "<topic>"` whenever the user references prior work.
3. Read `BRAIN.md` when uncertain about brain rules, conventions, or trigger words.

If SKILL.md (this file) and BRAIN.md disagree, **BRAIN.md wins**.

## Trigger Words

| User says... | Do this |
|--------------|---------|
| "checkpoint" / "存档" / "记一下" | Run `brain checkpoint` — it prints the routing playbook, including note-first process records, memo `--ref` back, slug rules, and recent slugs for reuse. Follow its output. |
| "preference" / "from now on" / "以后..." | 先过门槛：**跨项目通用**才写 `brain preference add -s <slug> -m "<rule>"`；只对某项目/仓库成立 → `brain knowledge add`（自带 project 标签） |
| "todo" / "记个 TODO" | `brain todo add -s <slug> -m "..." -p P1` |
| Hits an anti-pattern / mistake | `brain dsat add -m "..." -t <tag>` immediately |
| Non-obvious finding | `brain insight add -s <slug>` |
| "what did we...", "last time..." | `brain search` first; cite slugs. **Search is rg literal/regex** — cover synonyms via `'a\|b\|中文'` or repeatable `-e`; fall back to `<layer> list --since 7d` if nothing hits. |
| Stable conclusion ready | `brain knowledge add -c <cat> -n <name>` |

## Commands

| Task | Command |
|------|---------|
| Session brief (this-project vs other-projects) | `brain brief [--since 7d] [--limit 20]` |
| Sedimentation playbook + recent slugs | `brain checkpoint` — run when a turn is worth recording; follow its output |
| Non-trivial process record | `brain note add -s slug` first, then `brain memo add -s slug -m "..." --ref notes/<path>` |
| Trivial / quick capture | `brain memo add -s slug -m "..." -t tag` |
| Process doc / debug log | `brain note add -s "slug"` — appends to existing slug across days; `-w` forces fresh |
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
| Write / append / cp / diff / commit | `brain <op> <path>` — writes auto-sync |
| Shell ops (full shell, pipes, globs) | `brain exec <cmd...>` — $SHELL -c at brain root, auto-syncs + lints |
| Sandboxed shortcuts (brain root only) | `brain cat` / `brain ls` / `brain rm` |
| Raw shortcuts (arbitrary code; no path sandbox) | `brain python` (=python3) / `brain bash` |
| Mark old entries superseded (dream prune) | `brain supersede <new-path> <old-path>... [--force]` |
| Validate frontmatter | `brain lint` |

## TODO Lifecycle

`brain todo add` → `brain todo start <slug>` → `brain todo done <slug>`

## Query-start context

The UserPromptSubmit hook installed by `brain install codex` injects a short reminder at the start of each user prompt: run `brain brief` for non-trivial tasks, understand that brief provides recent memo / notes / open todos grouped by project, and search when prior work matters. The Stop hook runs `brain sync --quiet --background` at turn end without blocking or injecting model context. If `~/.skywork` exists, `brain install codex` installs the same hooks into `~/.skywork/config.toml`; `brain install skywork` can refresh just those hooks.

## Rules

1. Paths are relative to brain root — works from any CWD; never print or assume the brain's absolute filesystem location
2. Run `brain brief` at the start of non-trivial work; read BRAIN.md when uncertain; BRAIN.md > SKILL.md on conflict.
3. memo vs note routing. Record only useful information worth sedimenting. For non-trivial work that produced durable value, write `brain note` as the process record (what changed, decisions, debug trail, caveats), then write `brain memo` as the short "what was done" index (≤200 chars) with `--ref notes/<path>`. For trivial work, either a memo alone is enough or nothing should be written.
4. "checkpoint" trigger (user-initiated) runs the same `brain checkpoint` command and follows the same routing.
5. Structured adds (memo/dsat/insight/todo/preference/note) auto-sync (write-through)
6. For knowledge/ and tools/ — edit files directly, then `brain commit`
7. `brain cp` validates frontmatter on copy to structured layers
8. Full reference: `brain cat BRAIN.md`

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
