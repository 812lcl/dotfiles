---
name: obsidian-review
description: Obsidian vault 中 Daily/Weekly/Monthly/Quarterly/Yearly review 与 plan 的总入口。Review 段先聚合上一周期数据（含 vault 文件 + 完成 tasks + 跨 repo git 提交 + brain memo）→ 苏格拉底追问 → 写回 review 字段；Plan 段从任务池（四象限 + backlink 两视图）筛 → 用户挑序号 → 自动 ⏳ schedule + 写入 plan 字段。Use when the user invokes `/obsidian-review`, `/obsidian-review daily|weekly|monthly|quarterly|yearly [review|plan]`, or asks for 日回顾 / 周回顾 / 月回顾 / 季回顾 / 年回顾 / 日计划 / 周计划 / 月计划 / 季计划 / 年计划 / daily review / weekly review 等场景。
---

# Obsidian Review

帮用户在自己的 Obsidian vault 中完成 Daily/Weekly/Monthly/Quarterly/Yearly 的 review and plan。

**核心理念**：不是无脑代写，而是「先聚合数据 → 用苏格拉底式追问帮用户发现 insight → 用户确认后再写回」。

---

## Vault 基本事实

- **Vault 根目录**：`/Users/liuchunlei/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian Vault`（下文简称 `<VAULT>`）。也可从环境变量 `OBSIDIAN_VAULT_PATH` 取，或从用户 CWD 推断（若 CWD 已在 vault 内）。
- **plan 文件位置**：
  - Daily: `<VAULT>/1-plan/1-daily/YYYY-MM-DD.md`
  - Weekly: `<VAULT>/1-plan/2-weekly/YYYY-Www.md`（ISO 周编号，如 `2026-W20`）
  - Monthly: `<VAULT>/1-plan/3-monthly/YYYY-MM.md`
  - Quarterly: `<VAULT>/1-plan/4-quarterly/YYYY-QN.md`（如 `2026-Q2`）
  - Yearly: `<VAULT>/1-plan/5-yearly/YYYY.md`
- **模板位置**：`<VAULT>/assets/templates/plan/{Daily,Weekly,Monthly,Quarterly,Yearly}.md`。模板里的 `<%* ... %>` 是 Templater 语法，**新建文件时由 Obsidian 自动展开**（不是 skill 的事）。

---

## 路由：层级 + mode

入参格式：`/obsidian-review [<level>] [<mode>]`，如 `/obsidian-review daily review`。

### 层级（level）

- 显式：`daily` / `weekly` / `monthly` / `quarterly` / `yearly` 或中文 `日 / 周 / 月 / 季 / 年`
- 缺省 → 默认 daily（最高频）。如果今天是周日 / 月末 / 季末 / 年末，**提示用户**是否顺带做对应层级，不要自动选

### Mode（决定走 review 还是 plan）

- `review` — 只 review 上一周期，不进 plan
- `plan` — 跳过 review，直接 plan 当前周期（仍要读上一周期的 review 数据作为输入）
- 缺省（**默认**） — **Review 段 + Plan 段连贯走**

### 默认 mode 行为（按层级 + 触发时机）

| 层级 | 缺省 mode 走什么 |
|---|---|
| Daily | **昨天 review + 今天 plan**（用户早上做日 review 的典型姿势）。如果用户明显是晚上触发（昨天 review 已填、今天 plan 已填）→ 默认 = 今天 review |
| Weekly | 上周 review + 本周 plan（周日晚 / 周一晨） |
| Monthly | 上月 review + 本月 plan（月初前几天） |
| Quarterly | 上季 review + 本季 plan（季初前两周） |
| Yearly | 上年 review + 本年 plan（年初前两周） |

**例外**：用户明说"做昨天 review" / "plan 明天" / "做今天 review"（晚上做）→ 显式遵循，不走默认。

如果触发时机不典型（比如月中做 monthly），问用户："想做上月回顾、本月规划、还是本月中期复盘？"

**目标文件**：不存在则用 obsidian-cli 触发对应 Templater 模板创建（详见各 reference）。

---

## 通用工作流（两阶段 × 4 步）

每层都遵循「Review 段 → Plan 段」骨架，**细节在 `references/<level>.md`**。Mode=review 跳过 Plan 段；mode=plan 跳过 Review 段（但仍读上一周期的 review 数据作为输入）。

---

### 阶段 A：Review 段（target = 上一周期）

#### A.1 聚合数据

各层 reference 定义具体查询。所有层共享的数据源（见 [references/tasks-query.md](references/tasks-query.md)）：

- **vault 文件本身**：target_day frontmatter / 笔记 callout / 习惯打卡
- **完成的 tasks**（Q1 / Q3 / Q4 / Q5 / Q9 done 版）：全 vault 范围，含项目页、weekly、monthly 行动清单
- **跨 repo git 提交**（Q10）⭐：遍历 `$MONOREPO_ROOTS`（默认 `~/Code/skywork/agent`）拉 target_day 当日 commits — 工程师用户日常工作很多落在 git 而非 task 勾选，**必查**
- **brain memo / knowledge 当日新增**：读 `brain/memo/<target_day>.md`（如存在）+ `git -C brain log --since/--until` 当日 commits

首选 obsidian-cli + obsidian 官方 tasks 命令，需要原文细节时用 Read。

#### A.2 组织数据展示

客观事实（任务完成数 / 习惯打卡 / git commit / 关键词） + 显著模式 + 与上一周期对比。**精简、不照搬全文**：daily <500 字，weekly <800 字，monthly+ 可更长但仍要分块。

#### A.3 苏格拉底追问（按需，目标是填完待写字段）

- 紧扣数据里的张力点（连续 N 天写"累"、某习惯下滑、某项目零推进、win 完成但情绪差…），或针对某个待填字段（gratitude / celebrations / can do better / 等）针对性追问素材
- 问"为什么"和"如何"，不问"是不是"
- **一次一个**，等用户答完再问下一个
- **不设硬上限**：目标是把本阶段要写的 frontmatter + 正文 callout 待填项的素材都凑齐。数据展示 + 2-3 个问题就够就停；不够继续追
- 用户随时可说"跳过 X" / "X 留空"，那个字段不再追问，直接留空
- 不要替用户写情绪/感悟字段（但可以追问到他说出口）；避免同一字段反复换问法、避免用户已明确表态后继续追问

#### A.4 写回 Review 字段

每层模板的 frontmatter / 正文 callout 分为 **Review 字段** 和 **Plan 字段**（见各 reference 表格）。Review 段只写 review 字段，不碰 plan 字段。

- 写入前必 Read，逐字段确认（"准备写 `feeling: 忙碌`，OK？"）
- 用户说"OK"/"写"才动 Edit
- **不要替用户写情绪/感悟字段** — 这是用户自我反思的产物

---

### 阶段 B：Plan 段（target = 当前周期）

#### B.1 聚合数据

- **Review 段 insight**（连贯模式下直接传递；mode=plan 时主动读上一周期文件）
- 上一周期"给当前周期的方向"：weekly 的 `need to Improve` / monthly 的 `need to Improve` / quarterly 的 `commit to improve` / yearly 的 vision
- 上层目标（daily 看 weekly objectives / weekly 看 monthly theme / monthly 看 quarterly focus / quarterly 看 yearly vision）
- **未完成任务池**（Q11 ⭐）：复用用户「任务列表.md」「四象限.canvas」过滤规则
- Q2 逾期任务

#### B.2 组织数据展示 — 任务池两视图

**两个视图都给**，编号 [#1] [#2] ... 跨视图共享（同一 task 在两个视图里编号一致），方便用户切换视角后用同一组序号选：

- **视图 A：四象限**（重要紧急 / 重要不紧急 / 不重要紧急 / 不重要不紧急）
- **视图 B：按 backlink 分组**（任务所在文件路径）

#### B.3 苏格拉底追问（按需，引出 Plan 字段）

引出 win the day / objectives / theme / intention 等 Plan 字段。**不设硬上限** — 目标是这些字段都有用户的明确回应，但 Plan 段一般比 Review 段更直接（用户已在 review 段表达过情绪），常见 1-3 个就够。用户说"跳过"的字段可留空。

#### B.4 用户挑序号 + 自动 schedule + 写回 Plan 字段

- 用户回复 task 序号（如 `#1 #3 #7`）→ skill **不二次确认**，直接用 W1（见 tasks-query.md）把这些 task 行的 `⏳` 改为 target_day
- 写回模板的 plan 字段（intention / win the day / objectives / theme 等）
- 用户口述写正文 callout / section

---

### 通用写入原则

- **frontmatter 全用 Edit 替换单行**（如 `intention:\n` → `intention: 值\n`）。**不要用 `obsidian-cli frontmatter --edit`**（实测会重排序字段 / 把 emoji key 转成 unicode escape / 空字符串变 null，破坏模板）
- 模板里 frontmatter 的空字段是 `字段名:`（无值），不是 `字段名: ""`
- callout 占位符 `> - ` 替换时保留 `> ` 前缀和 `[!note]` 等标签
- 多次写入同一文件，每次都 Read 最新内容（不要假设上次写入后状态不变）
- **不要覆盖用户已写的内容**：写入前若该字段已有内容 → 问"覆盖、追加、还是跳过？"

---

## 关键准则（所有层级共享）

**对话原则**：

- 中文交流（用户 CLAUDE.md 全局要求）
- skill 是「教练」不是「秘书」。不要主动替用户填情绪/感悟字段，那是用户自我反思的产物
- 每一步都要让用户有判断的余地，不要一次性甩出大段产出
- 不要假装在用户身边——观察到的数据要客观陈述，问题要诚恳，结论要等用户给

**写入原则**：

- 写入前必 Read，写入后不 verify（Edit 失败会自己抛错）
- **frontmatter 全用 Edit 替换单行**（如 `intention:\n` → `intention: 值\n`）。不用 obsidian-cli 写入（见上面副作用说明）
- 模板里 frontmatter 的空字段是 `字段名:`（无值），不是 `字段名: ""`。Edit 替换时保留这个风格
- callout 块里的占位符（如 `> - `）替换时，**保留 callout 标记**（`> ` 前缀和 `[!note]` 等标签）
- 多次写入同一文件时，每次写入都先 Read 最新内容（不要假设上次写入后状态不变）

**对接已有 skills**：

- Weekly review 的「工作」部分 → 调用 `weekly-report` skill（详见 `references/weekly.md`）
- **读** vault 数据优先用 `obsidian-cli`（print / search / search-content / list / frontmatter --print）
- **任务数据收集**（每层都用）→ 见 [references/tasks-query.md](references/tasks-query.md)。双轨：优先官方 `obsidian` CLI（Obsidian.app 内置，有 `tasks` 命令），fallback `rg` 正则。注意：官方 `obsidian` ≠ Go 写的 `obsidian-cli`，后者**没有** tasks 子命令
- **写** vault 数据全用 Edit（不要用 obsidian-cli frontmatter --edit）
- obsidian-cli 调用需带 `--vault "Obsidian Vault"` 参数（本机未设默认 vault）

**避免反模式**：

- ❌ 一上来就把所有问题甩给用户（要先展示数据）
- ❌ 替用户写情绪/感悟（要追问）
- ❌ 直接覆盖已填内容
- ❌ 把 7 天 daily 全文塞进 chat（要提炼）
- ❌ 一次 Edit 太多字段（分段确认）

---

## 各层级流程详见

执行任意层级前，**先读对应 reference**（每个 reference 都包含 Review 段 + Plan 段 + frontmatter 字段切分表）：

- **Daily** → 见 [references/daily.md](references/daily.md)
- **Weekly** → 见 [references/weekly.md](references/weekly.md)（含 `weekly-report` skill 集成）
- **Monthly** → 见 [references/monthly.md](references/monthly.md)
- **Quarterly** → 见 [references/quarterly.md](references/quarterly.md)
- **Yearly** → 见 [references/yearly.md](references/yearly.md)

**共享 reference**（所有层 Review/Plan 段都引用）：

- [references/tasks-query.md](references/tasks-query.md) — 任务查询 + git commit 查询 + schedule 写入。包含：
  - Q1-Q9：完成 tasks / 逾期 / area 分组 / scheduled 落地 等读查询
  - **Q10**：跨 repo git 提交（vault 外数据源，Review 必查）
  - **Q11**：未完成任务池（Plan 段挑选用，四象限 + backlink 两视图）
  - **W1**：批量写入 ⏳ schedule 时间（Plan 段尾巴自动执行）
