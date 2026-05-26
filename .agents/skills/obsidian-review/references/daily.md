# Daily Review/Plan 流程

Daily 主要由用户**手写**。skill 负责两件事：

1. **Review 段**：聚合 target_day 数据（vault 文件 + 完成 tasks + ⏳ 当日落地 + 跨 repo git + brain memo）→ 苏格拉底追问 → 写回 review 类字段
2. **Plan 段**：基于 review insight + 任务池筛选 → 设 intention/win the day → 把用户选中的 task 自动 ⏳ schedule 到 target_day

**习惯打卡（8 个 bool）用户自己标，skill 不写。** 笔记四段（健康/家庭/个人/工作）也是用户日常手写，skill 在 review 时只读不写（除非用户对话产出明确要追加）。

---

## 目标文件结构

`<VAULT>/1-plan/1-daily/YYYY-MM-DD.md`

如果文件不存在 → 用 obsidian-cli 触发 Daily 模板创建：
```bash
obsidian-cli --vault "Obsidian Vault" create "1-plan/1-daily/YYYY-MM-DD" --template "assets/templates/plan/Daily"
```

### Frontmatter 字段切分

**Plan 段字段**（晨间设的）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `intention` | string | 今日意图（一句话） |
| `win the day` | string | 让今天有效的一件事 |

**Review 段字段**（当晚或次日晨补的）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `3 words` | string list | 三个词总结 |
| `effectiveness` | string | 效能感（⭑⭑⭑⭑⭑ 或自定义短语） |
| `feeling` | string | 当天心情关键词 |
| `gratitude` | string | 感激的人/事 |
| `celebrations` | string | 值得庆祝 |
| `can do better` | string | 可以做得更好 |
| `highlights/milestone` | string | 当天高光时刻（可空） |
| `workout` | string list | 运动记录（可空） |
| `flomo` | string | flomo 节选（可空） |

**用户自己标的字段**（skill **不写**）：

- 8 个习惯打卡 bool：`🧘‍♂️ 冥想` / `💪🏼 运动` / `👶🏻 育儿` / `📚 读书` / `💧 喝水` / `😴 早睡` / `🇬🇧 英语启蒙` / `🥣 健康饮食`

### 正文 callout 块

**Plan 段**：「清晨 3 分钟」`> [!success]` 两段
- `🌄 我要让这一天变得很棒的方法：` 下的 `> - `
- `🌄 正向自我肯定：` 下的 `> - `

**Review 段**：「晚间 3 分钟」`> [!summary]` 三段
- `🌃 我今天经历的美好事／幸福时刻：` 下的 `> - `
- `🌃 我今天做的好事：` 下的 `> - `
- `🌃 我要如何改善：` 下的 `> - `

**笔记**：`> [!note]` 四段（健康/家庭/个人/工作） — 用户日常手写，skill **只在 review 时读，不主动写**（除非对话产出明确要追加，且用户认可）。

---

## Mode + Target_day 判断

| 用户输入 | 走什么 | target_day（review） / target_day（plan） |
|---|---|---|
| `daily`（默认） | Review + Plan 连贯 | 昨天 / 今天（用户早上做 daily 的典型习惯） |
| `daily` 晚上触发（**昨天 daily 已写完晚间 3 分钟、今天 plan 已写完**） | 只 Review 今天 | 今天 / — |
| `daily review` | 只 Review | 昨天（用户明说"做今天 review"则今天） |
| `daily plan` | 只 Plan | — / 今天（用户明说"plan 明天"则明天） |
| `做昨天的晚间回顾` / `做昨天 review` | 只 Review 昨天 | 昨天 / — |

判断当前文件状态用 obsidian-cli + Read，关键字段：
- 昨天 daily 的「晚间 3 分钟」三段是否都填了 → 没填 = 默认补 review 昨天
- 今天 daily 的 `intention` / `win the day` / 清晨 3 分钟 是否填了 → 没填 = 默认 plan 今天

---

## Review 段流程

target_day 默认是「昨天」（早上做 daily 时），晚间触发或用户明说则为「今天」。

### A.1 聚合数据

**A.1.1 读 target_day 的 daily 文件全文**（用 Read）：
- frontmatter（intention / win the day / review 类字段 / 习惯打卡 / 笔记四段是否填了）
- 「清晨 3 分钟」两条（早上设的）
- 「晚间 3 分钟」三条（是否已填）
- 「笔记」四段已写内容（健康/家庭/个人/工作）
- day planner 勾选 vs 未勾选

**A.1.2 任务数据**（见 [tasks-query.md](tasks-query.md)）：
- **Q1** 当日全 vault 完成的 task（`✅ <target_day>`）
- **Q9 done 版** ⏳ 当日中已完成的（看 win 落地）
- **Q9 todo 版** ⏳ 当日中仍未完成（看 backlog 漂移）
- **Q4** 按 area 分组（work / learning / health / family / technique）
- 不要把日常生活 task（吃饭/通勤/洗漱）当成实质推进

**A.1.3 跨 repo git 提交** ⭐（见 [tasks-query.md](tasks-query.md) Q10）：
- 遍历 `$MONOREPO_ROOTS`（默认 `~/Code/skywork/agent`）拉 target_day 当日 commits
- 按 repo 分组展示 `[hash|HH:MM] commit message`
- **vault 内 brain repo** 单独查
- **工程师用户必查** — 实际工作量往往远超 day planner 颗粒度

**A.1.4 brain memo 当日新增**：
- 读 `<VAULT>/brain/memo/<target_day>.md`（如存在）取关键段
- `git -C <VAULT>/brain log --since/--until <target_day>` 看当日 brain commits

**A.1.5 最近 3 天 daily** 的 `feeling` / `3 words` / `effectiveness` 序列（看连续模式）

### A.2 组织数据展示

精简结构 < 500 字，按以下顺序：

```
🌃 {target_day} 回顾

晨间设的：
- intention: {X}
- win the day: {Y}

📦 全 vault 完成的实质推进（除日常）：
- 💼 work: {1-3 条精选}
- 📚 learning: {...}
- 🛠️ technique: {...}

📋 ⏳ {target_day} scheduled 落地：N/M（X% 兑现）
- ✅ 已完成 N 条
- ❌ 未推 {N} 条（带优先级标记）：{挑 ⏫/🔺 的 3 条}

📦 跨 repo git 提交（实际工作量）：
- {repo1}: {N} commits
  - HH:MM commit message
  - ...
- {repo2}: ...

🧠 brain 同步沉淀：
- {N} 条 memo / knowledge / lessons：{1-3 条精选标题}

笔记四段已写：
- 健康/家庭/个人/工作 各 1 行摘要（空段省略）

习惯打卡当前状态：{✅ 列已打卡} / {⚪️ 未打卡}

最近 3 天 feeling 序列：{X → Y → Z → 今天？}

🔍 我注意到：
- {1-2 个张力点，来自数据，不要泛泛}
```

### A.3 苏格拉底追问（按需，目标是填完待写字段）

**优先从数据里的张力点**生成问题：

- Win 落地 → "win 拿下了，是什么让你今天能聚焦在这件事上？想下次复制"
- Win 未落地 → "win 没拿下，是被什么截胡了？临时任务、状态、还是 win 本身不合理？"
- 连续 N 天 feeling 偏低 → "已经连续 N 天写「{某情绪}」了，是某件具体的事还是更弥散的状态？"
- ⏳ scheduled 落地率 < 30% → "今天 ⏳ 的 ticket 大部分没动，是被什么挤掉的？"
- 笔记空但 day planner 全勾 → "工作时段都打勾了但没在笔记留痕，没东西可写，还是没空写？"
- 某习惯连续 N 天没打 → "{习惯}最近 N 天没打卡，对你重要吗？还是这个习惯已经不适合现在？"
- git commits 多 / 笔记空 → "今天写了 N 个 commit 但工作笔记空白，是临时救火没空记，还是觉得这些不值得写？"

**通用追问可用**（择 1）：
- "今天最让你有「活着」感的瞬间是什么？"
- "如果重来一遍，会有哪一件事换种做法？"
- "明天如果继承今天的状态，最想保留什么、最想换掉什么？"

**一次一个**，等用户答完再问下一个。**不设硬上限** — 目标是 review 字段（feeling / gratitude / celebrations / can do better / 晚间 3 分钟三段）都有素材；用户随时可说"跳过 X / X 留空"。

### A.4 写回 Review 字段

**Frontmatter（Review 字段）** — Edit 替换单行 `字段名:` → `字段名: 值`：

- `3 words`：3 个词（list 形式，每行 `  - 词`）
- `effectiveness`：效能（list 形式）
- `feeling`：心情（list 形式）
- `gratitude`：感激（原话）
- `celebrations`：庆祝（原话）
- `can do better`：改善（原话）
- `highlights/milestone`：高光（如有）
- `workout` / `flomo`：可空（用户自填）

**习惯打卡 8 个 bool — skill 不写**（用户在 Obsidian properties UI 中自己标）。

**正文「晚间 3 分钟」callout** — Edit 替换三个 `> - ` 占位符：
- 美好事/幸福时刻
- 今天做的好事
- 如何改善

**「笔记」四段** — 只在用户对话中明确产出对应内容且认可"加进笔记" 时才追加；默认不动。

---

## Plan 段流程

target_day 默认是「今天」。

### B.1 聚合数据

**B.1.1 上一日 Review insight**（连贯模式直接传递；mode=plan 时主动读昨天 daily）：
- 昨天 `feeling` / `3 words` / `effectiveness`
- 昨天 `can do better` 原话
- 昨天「晚间 3 分钟」「如何改善」那条

**B.1.2 本周 weekly objectives**：用 obsidian-cli 读本周 weekly 的 frontmatter `objectives` 和「下周重点」段（如有）

**B.1.3 任务池** ⭐（见 [tasks-query.md](tasks-query.md) Q11）：
- 复用「任务列表.md」「四象限.canvas」过滤规则
- 给两个视图：四象限 + 按 backlink，编号 [#1] [#2] ... 跨视图共享
- 数量多时优先列重要紧急 + 重要不紧急

**B.1.4 Q2 逾期任务**：截止 📅 ≤ target_day 但未勾，全 vault 范围

**B.1.5 项目页本周更新**（工作日）：`2-task_management/1-projects/` 当周有 mtime 更新的文件名，帮用户识别"今天可能在哪个项目上推进"

### B.2 组织数据展示

```
🌅 {target_day} Plan

昨天 review 提取的方向：
- 改善方向：{can do better 摘要}
- 启示：{晚间 3 分钟「如何改善」那条}

本周 win：{weekly objectives 摘要}

📋 任务池（编号跨视图共享）

【视图 A：四象限】

🔥 重要紧急（{N} 条）
  [#1] {task text} {priority} {⏳/📅 日期} ← {file basename}
  [#2] ...

⭐ 重要不紧急（{N} 条）
  [#7] ...

⚡ 不重要紧急（{N} 条）
  ...

🌊 不重要不紧急（{N} 条）
  ...

【视图 B：按文件】

📄 2026 工作.md
  [#1] ...
  [#3] ...

📄 OpenClaw 养成.md
  [#5] ...

📌 逾期（截止 ≤ {target_day} 未勾）：
- {挑 1-3 条关键的}

🔍 我注意到：
- {1-2 个观察，比如"5 条 tool_use 类已挂了 2 天" / "本周 win 是 X 但任务池里没相关 ticket"}
```

### B.3 苏格拉底追问（按需，引出 Plan 字段）

引出 win the day / intention。**不设硬上限**，但通常比 Review 段少（用户已在 review 段表达过情绪），常见 1-3 个就够。用户可"跳过"。候选：

- "如果今天只能完成一件事让你睡觉时觉得没白过，是什么？（给序号或新描述）"
- "本周 win 是 {Y}，今天能不能切出 30-60min 推动它？什么时段？"
- "昨晚你写「改善」是 {X}，今天怎么落到一个具体动作？"

### B.4 用户挑序号 + 写入

**用户回复 task 序号**（如 `#1 #3 #7`）+ win the day 原话 → skill：

**B.4.1 W1 批量写入 ⏳**（见 [tasks-query.md](tasks-query.md) W1）：
- 把选中 task 的 ⏳ 改为 target_day（无 ⏳ 标记则追加）
- **不二次确认**，直接执行
- 完成后简短回："已 schedule {N} 条到 {target_day}"+ 列改动 task title

**B.4.2 Frontmatter（Plan 字段）**：
- `intention`：用户口述（一句话）。**skill 可提建议但不替写**
- `win the day`：用户口述

**B.4.3 「清晨 3 分钟」callout** — Edit 替换两个 `> - `：
- 让这一天变棒的方法：一行具体动作（基于 win + 任务池选择拼）
- 正向自我肯定：用户原话，**不要美化**

每段写入前在 chat 里说："准备写：{字段}={值}，OK？"，逐段确认。

---

## 退出条件

- 用户说"够了 / 先这样 / 之后再补" → 当场停止
- 用户答非所问、明显烦躁 → 立刻收手，把目前为止的产出写入即可
- 连贯模式中用户在 Review 段后说"今天 plan 不用做" → 跳过 Plan 段，结束
- 写完不要 verify、不要总结一遍（用户能直接在 Obsidian 里看到）
