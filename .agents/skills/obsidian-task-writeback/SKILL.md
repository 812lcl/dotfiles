---
name: obsidian-task-writeback
description: Fill evidence-backed Obsidian Tasks into the user's project pages from git commits, Codex session/brain notes, and daily context. Use this whenever the user asks to 根据今天/昨天 git、Codex session、工作总结补充 Obsidian task, 填充 Day Planner 空余时间块, defer unfinished work tasks, or add `[area::work]` tasks while avoiding schedule overlap. This skill is especially important for Code Agent / skywork/agent daily work logs.
---

# Obsidian Task Writeback

Use this skill to turn real work evidence into Obsidian Tasks in the right project page, with correct date markers, `[area::work]`, and non-overlapping time blocks.

The user's intent is usually: "based on today's/yesterday's git and Codex sessions, add completed work tasks to the relevant Obsidian project pages and list what was added." Treat this as an evidence-backed writeback task, not freeform journaling.

## Scope

- Vault root: `/Users/liuchunlei/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian Vault`
- Main work repo root: `/Users/liuchunlei/Code/skywork/agent`
- Project pages: `2-task_management/1-projects/*.md`
- Daily notes: `1-plan/1-daily/YYYY-MM-DD.md`
- Routine work tasks: `2-task_management/2-tasks/工作日常任务.md`
- Default work project for Code Native / Gateway / chat-sdk / skywork-cli evidence: `2-task_management/1-projects/Code Agent.md`

## Trigger Patterns

Use this skill for prompts like:

- "根据今天 git、codex session 等内容，在相应 project 中增加 obsidian task"
- "根据昨日工作总结补充昨天完成的 tasks，填充 Day Planner 空余时间块"
- "把这些工作任务 defer 到明天"
- "仅添加工作相关任务，标上 [area::work]，不要时间重叠"
- "回复列出来你添加的任务"

If the user asks for review/planning rather than evidence-backed task writeback, use `obsidian-review` instead.

## Operating Principles

- Preserve the user's dirty worktree. Run `git status --short` first, and never revert unrelated files.
- Keep edits scoped to the relevant project page unless the user explicitly asks to change daily notes or routine task files.
- Only write work tasks when the user asked for `[area::work]`; do not include health, family, house-buying, finance, or personal admin.
- Prefer completing an existing semantically matching placeholder task over adding a duplicate.
- Do not move or re-date existing deferred tasks unless that is explicitly part of the request.
- Add tasks as Obsidian Tasks lines, usually:
  `- [x] HH:MM - HH:MM Task title [area::work] ⏳ YYYY-MM-DD ✅ YYYY-MM-DD`
- For planned/deferred unfinished tasks, use:
  `- [ ] Task title [area::work] ⏳ YYYY-MM-DD`
- The `⏳` date is the schedule date. The `✅` date is the completed date. Completed work usually has both.
- Avoid overlapping time blocks with the target daily note, project-page tasks, and routine work tasks.
- In the final reply, list exactly the tasks added or completed, with times.

## Workflow

### 1. Establish Target Date and Scope

1. Resolve relative dates in Asia/Shanghai:
   - "今天" = current local date.
   - "昨天" = current local date minus one day.
   - If the user gives an exact date, use it.
2. Run `brain brief`.
3. If the user names themes, bugs, projects, or "Codex session", run targeted `brain search` queries for those terms.
4. Run `git status --short` in the vault root and note pre-existing dirty files.
5. Read the target daily note and collect its `# Day planner` timed blocks.
6. Read likely project pages and the routine task file:
   - Always inspect `Code Agent.md` for skywork/agent Code Native work.
   - Inspect other project pages if evidence clearly belongs elsewhere.
   - Search for existing tasks on the target date and for topic keywords.

### 2. Collect Evidence

Use at least two evidence channels when practical:

- Git commits in `/Users/liuchunlei/Code/skywork/agent`, filtered to the target date and user's author names such as `chunlei`.
- Brain notes and memos for the target date.
- Current Codex session context, when available from the conversation.
- Existing Obsidian daily/project tasks, to avoid duplicates and understand time constraints.

Useful git command pattern:

```bash
git -C /Users/liuchunlei/Code/skywork/agent/<repo> log \
  --author=chunlei \
  --since='YYYY-MM-DD 00:00:00' \
  --until='YYYY-MM-DD +1 day 00:00:00' \
  --date=local \
  --pretty=format:'%h %an %ad %s' \
  --date=format:'%Y-%m-%d %H:%M' \
  --all --max-count=50
```

For broad discovery, scan repos but stop if output becomes noisy. Prefer known repos from the user's themes: `gateway`, `skyclaw/frontend/skywork-agent-web`, `fe-monorepo`, `skywork-cli`, `creation`, `oma`, `memory-service`, etc.

### 3. Synthesize Candidate Tasks

Group evidence by work theme, not by individual commit. One task should represent a real time block and a coherent unit of work:

- Good: "Gateway completed fence 错误拦截 Workflow 消息修复：post-turn delivery MR !2392 合入"
- Too granular: one task for every tiny test commit.
- Too vague: "修 bug" or "处理工作".

Map each task to the correct project section:

- Code Native / Gateway stability -> `Code Agent.md` `### Gateway 分布式稳定性`
- chat-sdk / FE SDK release -> `Code Agent.md` `### Skywork-web`
- CLI/tooling -> `Code Agent.md` `### Plugins + Cli`
- memory-service / OMA migration -> `Code Agent.md` `### OMA 迁移 Code`
- Generic Code Agent implementation -> `Code Agent.md` `### Agent 基础` or the nearest matching section.
- Work not specific to Code Agent may belong in `2026 工作.md` or another explicit project page, but avoid using it as a dumping ground.

Duplicate handling:

1. Search the project page for the topic and target date.
2. If an incomplete task is semantically the same, convert it to completed and add the time range instead of adding a duplicate.
3. If an existing completed task already covers the same work, do not add another.
4. If the topic is adjacent but materially different, add a new more specific task.

### 4. Allocate Non-Overlapping Time Blocks

Build a timeline from:

- Target daily note timed tasks.
- Target-date timed tasks in the project page(s) being edited.
- Target-date timed tasks in `2-task_management/2-tasks/工作日常任务.md`.
- Other project pages only if they have target-date work tasks that could overlap.

Pick free blocks that match the evidence and the user's known working day. Respect personal/health/family blocks from Day Planner.

If exact task duration is unclear, use conservative 30, 45, 60, 75, or 120 minute blocks. Adjacent blocks are fine; overlapping blocks are not.

Use the bundled script after editing:

```bash
python /Users/liuchunlei/Documents/Code/dotfiles/.agents/skills/obsidian-task-writeback/scripts/check_task_timeline.py \
  --date YYYY-MM-DD \
  --vault "/Users/liuchunlei/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian Vault" \
  --files "2-task_management/1-projects/Code Agent.md" \
  --files "2-task_management/2-tasks/工作日常任务.md"
```

Add more `--files` for other project pages you edited.

### 5. Edit Carefully

Before file edits, explain briefly what you are about to change.

Use `apply_patch` for manual edits. Do not use ad hoc shell writes for Markdown edits.

When adding a task:

- Insert under the most relevant existing heading.
- Preserve existing order where possible, but do not reorder large sections just to sort by date.
- Keep the original task text if completing a placeholder, and add specificity only when it improves traceability.
- Retain existing priority markers such as `🔼` / `⏫` when completing a placeholder.

When deferring unfinished work:

- Only defer tasks requested by the user or proven unfinished by evidence.
- Update `⏳` to the new date.
- Do not mark as completed.

### 6. Validate

Run these before final:

```bash
git diff --check -- '<edited project file>'
python /Users/liuchunlei/Documents/Code/dotfiles/.agents/skills/obsidian-task-writeback/scripts/check_task_timeline.py --date YYYY-MM-DD --vault "<VAULT>" --files "<edited project file>" --files "2-task_management/2-tasks/工作日常任务.md"
```

Also inspect the diff to catch accidental unrelated changes:

```bash
git diff -- '<edited project file>'
```

If validation reports an overlap, adjust times and rerun.

### 7. Persist Process Record

For durable writebacks, leave a concise brain process record:

```bash
brain note add -s obsidian-task-writeback-YYYYMMDD -t obsidian,work-log
brain memo add -s obsidian-task-writeback-YYYYMMDD -m "..." --ref notes/YYYY-MM-DD-obsidian-task-writeback-YYYYMMDD.md -t obsidian,work-log
```

Brain may auto-commit; check its status. Do not create empty commits.

### 8. Final Reply

Reply in Chinese. Include:

- Which project page(s) changed.
- A bullet list of tasks added/completed, with times.
- Validation summary: `git diff --check` and timeline overlap result.
- Mention any important preservation note, such as unrelated dirty files left untouched.

Keep it concise. Do not include raw command dumps.

## Common Pitfalls

- Accidentally replacing an existing deferred date with the repository HEAD date. Treat the current working tree as authoritative unless the user asks for a revert.
- Adding Code Agent work into the daily note instead of the project page.
- Duplicating an unfinished placeholder instead of completing it.
- Counting routine release tasks twice: if `工作日常任务.md` already has the timed recurring release task, avoid adding an identical release task unless the evidence is a separate project-specific release.
- Treating broad git merge commits as separate tasks when they are just the closeout of the same work theme.
- Including personal tasks just because they appear in the daily note.

