---
name: knowledge-clip
description: Clip external content (podcasts, articles, videos, tweets, PDFs, local files) into the user's Obsidian vault as structured Markdown notes following the Knowledge.md template. Triggers when the user pastes a URL or asks to clip / save / archive / 剪藏 / 收藏 / 存到知识库 / 加到 Obsidian / 收进知识库 with a URL or file path. Auto-detects source type (小宇宙, YouTube, B站, X, 微信公众号, 少数派, PDF, local), fetches content (defuddle for web, yt-dlp for video, autocli for X and B站), generates AI summary plus key points plus category plus tags, then writes to the vault path 4-knowledge_hub/Clippings/ with file name "[type] title.md". After clipping, if the vault has a 5-wiki/ directory, asks the user once whether to also run /wiki-ingest on the clip to feed it into the LLM Wiki. Supports running across projects and other agents via OBSIDIAN_VAULT_PATH env var.
---

# Knowledge Clip

Pulls an external resource (URL or local file) into the user's Obsidian vault as a structured clip note. One slash through the pipeline: detect → fetch → AI-enrich → write.

## When to trigger

Activate when the user does any of:

- pastes a URL (with or without a verb)
- says **剪藏 / 收藏 / 存到 / 加进 / 收进 / 归档 / clip / save** in the same turn as a URL or file path
- explicitly invokes `/knowledge-clip <url>` or similar

If the user pastes a URL with **no clear ask**, ask once: "要把这个剪藏到知识库吗？"

## Resources

Read these on demand:

- **[references/frontmatter-spec.md](references/frontmatter-spec.md)** — exact YAML field rules, status/type/media enums, examples
- **[references/source-handlers.md](references/source-handlers.md)** — per-source fetching recipe (commands, fallback strategy)
- **[references/category-pool.md](references/category-pool.md)** — existing category vocabulary; pick from here first

## Tools

Helper scripts under `scripts/`:

- `find_vault.py` — locate vault root + Clippings dir (env-var or `.obsidian/` discovery)
- `detect_source.py <url-or-path>` — classify source → JSON `{type, media, handler, url_or_path}`
- `sanitize_filename.py <type> <title>` — produce `[<type>] <safe-title>.md`
- `check_duplicate.py <source>` — check if URL/path already clipped (two-stage: frontmatter `source:`/`url:` exact match + URL fingerprint grep for legacy notes)
- `xiaoyuzhou_meta.py <episode-url>` — extract episode-level metadata (cover/title/pub_date/podcast/duration) from xiaoyuzhou page; **always use this instead of defuddle for xiaoyuzhou metadata** (defuddle returns podcast-level cover, identical for every episode)

External CLI dependencies (only checked when used):
- `defuddle` (default web/podcast fetcher) — `npm i -g defuddle`
- `yt-dlp` (videos)
- `pdftotext` from poppler (PDF)
- `autocli` (X / Bilibili)

## Workflow

### Step 1 — Resolve vault

```bash
python3 scripts/find_vault.py --json
```

If exit 1: ask the user for vault path, suggest setting `OBSIDIAN_VAULT_PATH` permanently.

### Step 2 — Detect source

```bash
python3 scripts/detect_source.py "<url-or-path>"
```

Returns `{type, media, handler, url_or_path}`. Branch on `handler`.

### Step 3 — Check duplicate

```bash
python3 scripts/check_duplicate.py "<url-or-path>"
```

If `duplicate: true`, **stop and ask the user** before proceeding:
- (a) 覆盖现有文件
- (b) 新建带 `(2)` 后缀的副本
- (c) 取消

### Step 4 — Fetch content

Follow [references/source-handlers.md](references/source-handlers.md) for the matching `handler`. Collect:

- `original_content` (markdown body)
- `title`, `author`, `published`, `cover` (best effort)

**Special: podcast default = defuddle (fast), NOT transcriber.** Only run xiaoyuzhou-podcast-transcriber when the user explicitly asks for full transcript / 逐字稿 / `--full`.

### Step 5 — AI enrich

Generate from `original_content`:

- **summary** — 100-300 字 一段，第三人称
- **comment** — 5-10 条 bullet 要点（金句优先）
- **category** — 1-3 项，**先在 [references/category-pool.md](references/category-pool.md) 里选**；不在池里才允许新增（并在最终回复用 `> [!note]` 提示）
- **tags** — `clippings` 兜底 + 1-5 个内容关键词

See [references/frontmatter-spec.md](references/frontmatter-spec.md) for field semantics and length limits.

### Step 6 — Build file

Filename:
```bash
python3 scripts/sanitize_filename.py "<type>" "<title>"
```

Body: use `assets/note_template.md`, fill all placeholders, ensure frontmatter order matches [references/frontmatter-spec.md](references/frontmatter-spec.md).

### Step 7 — Write to disk

```
<clippings_dir>/[<type>] <safe-title>.md
```

Use the Write tool. Do not overwrite without explicit user consent (Step 3 covers that).

### Step 8 — Git commit (vault repo)

Commit the new clip into the vault's git repo. **Do not push.**

```bash
VAULT="$(python3 scripts/find_vault.py --vault)"
cd "$VAULT"

# Skip silently if vault isn't a git repo
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

git add -- "<absolute path to the new/modified clip file>"
git commit -m "feat(clippings): <type> - <title>"
```

**Rules**:

- Stage **only** the clip file (specific path), never `git add -A`. Other work-in-progress in the vault must not be swept in.
- Commit message convention: `feat(clippings): <type> - <title>` for new clips; `fix(clippings): update <type> - <title>` for duplicate-overwrite.
- This is **pre-authorized** by the user as part of the skill workflow — do NOT ask for additional confirmation per clip.
- If `git commit` fails (e.g. pre-commit hook), report the error verbatim, do **not** retry, do **not** amend, do **not** `--no-verify`. The clip file stays on disk; user can retry commit later.
- Never `git push`. Never `git push --force`. Never run destructive git commands.

### Step 9 — Report back

End the turn with a 5-line confirmation:

```
✅ 已剪藏到 <relative-path>
   类型 / 来源：播客 / 小宇宙
   分类：个人成长-认知思维, 心智与方法
   原文 N 字 + AI 摘要 / 5 条要点
   📝 已提交 <short-hash>: feat(clippings): 播客 - <title>
```

If commit was skipped (not a repo) or failed, replace the last line with the reason.

If new category introduced:
```
> [!note] 本次新增 category 候选：`xxx-yyy`，是否加入 references/category-pool.md？
```

### Step 10 — Ingest 到 5-wiki（条件触发，opt-in）

剪藏完成后，若当前 vault 启用了 LLM Wiki 体系（即存在 `<vault>/5-wiki/` 目录），询问用户一次：

> 是否把这次剪藏 ingest 到 5-wiki？(y/n)

- **yes** → 按 `<vault>/.claude/commands/wiki-ingest.md` 的四阶段工作流执行，目标参数（即该命令里的 `$ARGUMENTS`）= 本次剪藏文件的 vault 相对路径，例如 `4-knowledge_hub/Clippings/[文章] Foo.md`。等价于用户主动键入 `/wiki-ingest <path>`。读取该命令文件并遵循其阶段 1→4，不要在本 skill 里复述其逻辑。
- **no** 或 `5-wiki/` 不存在 → 静默跳过，本步骤结束。

设计要点（说明 *为什么* 这样做，便于未来在边界场景做判断）：

- **opt-in 而非自动**：并非所有剪藏都值得入图谱（临时收藏、轻量信息会污染 wiki）。把决定权留给用户，也避免 ingest 阶段 2 "提炼为空 → 建议跳过" 的重复对话。
- **条件触发**：5-wiki 是本 vault 特有的 LLM Wiki 子系统；其他 vault 没有这套结构，强行 ingest 会失败。检测目录存在与否是最便宜的 portability 判据。
- **复用而非复制**：`/wiki-ingest` 是 4 阶段交互式工作流（多次用户确认 + ledger/topic 同步），由 Claude 解释执行。直接读取该命令文件并按其指令走即可，无需在 knowledge-clip 里重复实现。
- **不要静默吞重复**：若用户选 yes 而 ledger 已有相同 hash → 让 `/wiki-ingest` 阶段 1 自行报告"已 ingest 过，跳过"，知识链路保持单一真源。

## Portability

This skill works across vaults / projects / agents via three env vars (all optional):

| Env | Purpose | Default |
|---|---|---|
| `OBSIDIAN_VAULT_PATH` | vault root | auto-detect via `.obsidian/` |
| `OBSIDIAN_CLIPPINGS_SUBPATH` | sub-path under vault | `4-knowledge_hub/Clippings` |
| `OBSIDIAN_CLIPPINGS_DIR` | full override (skips both above) | — |

Recommend the user add to shell rc:
```bash
export OBSIDIAN_VAULT_PATH="$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian Vault"
```

## Hard rules

- Never write outside `<clippings_dir>`.
- Never silently overwrite. Duplicate handling always requires explicit user choice.
- `status` is **always** `In Progress` on first clip. Never set `Done`.
- `rating` is **always left empty** — user fills it later.
- `completed` defaults to the **clip-message timestamp** (current time, `YYYY-MM-DD HH:MM`). User may overwrite if they consumed earlier (e.g. "五天前听完的" → fill the date they actually finished).
- `tags` always includes `clippings`.
- Filename always starts with `[<type>] `, no exceptions.
- AI summary failure → write `summary: (待补充)`, keep original content, proceed (don't abort).
- `summary` field **must** use YAML folded block (`summary: >-` then 2-space indented paragraph). Plain-scalar summaries containing ` : ` (e.g. "Pre-train : Post-train") break Obsidian's properties parser silently.
- After writing the clip file, **always** commit via Step 8 (vault git repo). Stage the specific clip file only, never `git add -A`. Never push.
- Step 10 (5-wiki ingest) is **opt-in per clip** — 必须显式询问用户一次，禁止自动触发；用户未明确同意前不得进入 `/wiki-ingest` 工作流。

## Common failures

| Symptom | Fix |
|---|---|
| `find_vault.py` exits 1 | Tell user to set `OBSIDIAN_VAULT_PATH` or cd into vault |
| defuddle not installed | `npm install -g defuddle` |
| yt-dlp missing | `brew install yt-dlp` or `pip install yt-dlp` |
| Podcast show notes too short | Ask user: 用 description / 升级到 transcriber (慢) |
| 重复剪藏 | Stop, present 3 choices to user |
| Step 10 询问后用户没明确表态 | 视为 no，跳过 ingest，不要默认执行 |
| `5-wiki/` 不存在但用户主动要求 ingest | 告知"当前 vault 未启用 5-wiki，跳过该步骤" |
