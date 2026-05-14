# Monthly Review/Plan 流程

每月一次，做月底回顾 + 下月计划。视野从「事件」升到「趋势」。

## Mode + 触发时机

入参 `/obsidian-review monthly [<mode>]`，mode 缺省 = Review + Plan 连贯。

| Mode | 走什么 |
|---|---|
| 缺省 | **Review 上月 + Plan 本月** 连贯（推荐月初前 3 天） |
| `review` | 只 Review 上月 |
| `plan` | 只 Plan 本月（仍读上月 review 数据作为输入） |

Review 段额外数据源：
- 本月所有 weekly 的 frontmatter + 「本周关键收获」「下周重点」「值得庆祝」「可以做得更好」「本周感悟」
- 本月所有 daily 的 8 习惯打卡聚合
- 本月完成 tasks（[tasks-query.md](tasks-query.md) Q3/Q5/Q6）+ 按周分布
- **本月跨 repo git 提交**（Q10）
- 上月数据用于对比

Plan 段额外数据源：
- 上月 monthly 的 `need to Improve` / `what I learned`
- 本季 quarterly 的 focus（保持目标对齐）
- 未完成任务池（Q11，挑本月行动清单的素材）

---

## 目标文件结构

`<VAULT>/1-plan/3-monthly/YYYY-MM.md`

### Frontmatter 字段切分

| 字段 | 类型 | 段 | 说明 |
|---|---|---|---|
| `theme` | string | **Plan** | 本月主题（如「专注交付」「修复健康」） |
| `what will make this month awesome` | string | **Plan** | 让本月精彩的事 |
| `need to Improve` | string | **Plan** | 基于上月 review 承诺的本月改善方向 |
| `gratitude` | string | Review | 感激 |
| `celebrations` | string | Review | 庆祝 |
| `can do better` | string | Review | 可改善 |
| `what I learned` | string | Review | 本月学到的 |

### 正文 section

模板里有大量 section，按流程归类：

**月初规划部分**（PLANNING）：
- `# 🎯 本月主题`（包含上月启示引用）
- `## 📍 本月核心目标`（工作产出 / 个人系统 / 健康习惯 / 家庭生活 四类）
- `## 📊 本月关键指标（SMART）` 表格
- `## 🚧 上月遗留问题与本月对策` 表格
- `## 📋 本月行动清单` 四类 task list

**月末回顾部分**（REVIEW）：
- `## 🏃 健康习惯打卡统计（全月）`
- `## 📊 任务完成情况（月底统计）`
- `## Who / what I'm grateful for`
- `## What went well this month`（含 💼/🛠️/👨‍👩‍👧 三子段）
- `## What didn't go well?`（健康/习惯/工作三子段）
- `## What I'd like to improve`（健康/习惯/系统/平衡四子段）
- `## What I learned this month`（技术/方法/智慧/洞察四子段）
- `## 🎯 下季度改进方向`（这个其实是季度的，但模板放这了 — 不动）

**自动渲染部分**（Base/Dataview，**不动**）：
- `# Milestones + Events + Highlights` (Highlight base)
- `# READING + LEARNING` (Notes base)
- `## Weeks` (Base 表格)
- `## Review and update Life Goals` / Project List / Areas / 等 GTD review checklist

---

## 路由：回顾还是规划？

- 月底（月份最后 3 天）→ 默认走**月末回顾**
- 月初（月份前 3 天）→ 默认走**月初规划**（同时引用上月启示）
- 月中 → 问用户："想做月初规划补完，还是月中复盘？"

---

## 月末回顾流程

### 第 1 步：聚合本月数据

**1.1 读本月所有 weekly**：本月通常 4-5 个 weekly 文件，用 obsidian-cli 拿这些 weekly 的 frontmatter（`effectiveness` / `celebrations` / `can do better` / `need to Improve` / `what I learned`）+ 正文「💡 本周关键收获」「⏭️ 下周重点」「值得庆祝」「可以做得更好」「本周感悟」

**1.2 习惯打卡聚合**：用 obsidian-cli 批量读本月 daily（约 28-31 个）的 8 个习惯 bool，算出每个习惯的「完成天数 / 总天数 / 完成率」。

**1.3 任务完成情况**（见 [tasks-query.md](tasks-query.md)）：
- **Q3 本月完成的任务**：`✅ 2026-MM-`，**全 vault 范围**（不只 daily 文件，还包括项目页、weekly、monthly 行动清单）
- **Q5 按 area 分组**：算 work / learning / health / family / technique 各完成多少
- **按周分布**：把本月完成任务按 ISO 周拆开，看 W1/W2/W3/W4 完成数节奏（哪几周高峰/低谷）
- **Q6 项目页本月推进**：仅扫 `2-task_management/1-projects/`，列出每个项目本月完成 task 数，找出 0 推进的项目
- **Q7 积压**：本月仍未完成且截止已过的任务，按 area / 项目分组
- 拿上月同样数据用于对比

**1.4 上月数据**（用于对比）：拿上月 monthly 的「关键指标」表和「健康习惯打卡统计」表（如果有）。

**1.5 主题印证**：读月初设的 `theme` 和 `what will make this month awesome`，看本月实际发生的事是否对得上。

### 第 2 步：组织数据展示

**展示 A：本月主题回看**
```
月初设的 theme: "{X}"
"让这个月精彩的事": "{Y}"

📊 实际发生：
- 4 周关键词序列：紧张/破壁/通透 → 焦灼/突破 → 平稳/小修 → 收尾/反思
- 4 周的 win 完成率：3/4 拿下
```

**展示 B：习惯打卡月度统计 + 与上月对比**
```
习惯       本月完成   上月完成   变化
🧘‍♂️ 冥想    22/30      20/31      ↑
💪 运动     14/30      18/31      ↓ (-4)
...
```
（这就是模板里要的表格）

**展示 C：任务完成 + Area 分布**（全 vault 范围）
```
本月完成任务：X 条（上月 Y 条，变化 ±Z）

按 Area:
  work: ... ← 大头
  learning: ...
  health: ... ← 异常项标出
  family / technique / ...

按周节奏（看节奏感）:
  W1: 18 条  W2: 22 条  W3: 8 条 ← 低谷  W4: 15 条

项目维度（本月推进，仅 1-projects/）:
  ✅ 推进活跃：{项目 A 14 条 / 项目 B 9 条 / ...}
  ⚪️ 完全没动：{项目 C / 项目 D} ← 拖了一个月

积压（已逾期未完成）:
  本月新增逾期：{N} 条
  跨月积压：{N} 条
```

**展示 D：4 周关键收获串联**
列出 4 周的「💡 本周关键收获」原文，问用户哪几条是本月级别的 insight（不是一时的）。

**展示 E：观察到的模式**（关键）
```
🔍 我注意到：
- 上月计划要解决的 X 问题，本月对策提了 Y 但没有 task 真的完成
- 健康类任务从 70% 降到 48%，主要发生在月中（W3 W4）
- 4 周里只有 W2 写了"本周感悟"，其他 3 周空着
- 月初的 win "{X}" 和实际 4 周的 win 看起来对得上
```

### 第 3 步：苏格拉底式追问 2-3 个

围绕**月度级模式**而不是单周细节：

- 主题对得上 → "月初的主题 {theme} 看起来贯穿了，下月想换主题还是延续？"
- 主题对不上 → "月初想做 {X}，结果实际重心在 {Y}。这是优先级错估，还是 {Y} 本来就更重要被你低估了？"
- 习惯连续下滑 → "运动从 18 天降到 14 天，发生在月中。生活/工作里有什么变化拉走了那段时间？"
- 上月对策没落地 → "上月你说要 {对策}，本月行动清单里也写了，但完成度低。是这事其实没那么重要，还是没切到具体动作？"
- 4 周节奏对比 → "W1 W2 看起来高强度，W3 收尾 W4 反思。这个节奏你想保持还是想调？"

**避免**：
- 不要重复 weekly 已经问过的问题
- 不要纠结某一周的具体小事

### 第 4 步：分段确认 + 写入

按以下顺序，每段单独确认：

**4.1 健康习惯打卡统计表格**（展示 B）
→ Edit 替换模板中 `| 🧘‍♂️ 冥想 | | | | | |` 等 8 行
→ 同时填写「习惯趋势分析」callout 的 4 个子点（工作日 vs 周末 / 重点改进 / 保持优势 / 与上月对比）

**4.2 任务完成情况**（展示 C）
→ Edit 替换 4 行 `- **总任务数** / **完成率** / **平均每日** / **与上月对比**`

**4.3 Grateful / Went well / Didn't go well / Like to improve / Learned**
→ 5 大段，每段都有子标题（💼/🛠️/👨‍👩‍👧 等），逐段对话产出 → Edit 写入
→ 内容**应该是月度级**的归纳，不要简单 copy 4 周的 weekly 段落

**4.4 上月遗留问题与本月对策**表格（如果月初没填）
→ 4 周的「can do better」聚类成「上月问题」，对话产出根因和下月对策

**4.5 Frontmatter**（用 Edit 逐个替换单行）
- `gratitude` / `celebrations` / `can do better` / `need to Improve` / `what I learned`

---

## 月初规划流程

### 第 1 步：聚合上月数据

读取**上月 monthly 文件**的：
- `what I learned`、`celebrations`、`can do better`
- 「What I learned this month」段（4 子段）
- 上月「📋 本月行动清单」中未完成的 task → 候选搬到本月
- 上月「🎯 下季度改进方向」如果在月份转季度时

### 第 2 步：组织展示

```
📜 上月启示（{YYYY-MM}）:
- Theme 是 {X}
- 你写的核心收获：{1-3 条精选 from "what I learned"}
- 庆祝：{1 条}
- 可改善：{1 条}
- 上月未完成 task：{列 5-10 条用户挑}

📅 本月日历（粗看）:
- 重要节点：{从已有日历/项目页提取}
- 习惯打卡上月底的趋势：{N 项达标，M 项未达}
```

### 第 3 步：苏格拉底式追问 2-3 个

- "上月学到的 {X} 看起来很重要，下月你想怎么把它变成行为？"
- "上月 {未完成 task} 还要继续推进吗，还是放弃/降级？"
- "下月最让你期待的一件事是什么？这件事能不能成为 theme？"

### 第 4 步：分段确认 + 写入

**4.1 `# 🎯 本月主题`** — 一句话主题
→ Edit `## 📍 本月核心目标` 四类的目标

**4.2 「上月启示」callout**
→ Edit 替换 `> "引用上月关键收获"`

**4.3 `## 📊 本月关键指标（SMART）` 表格**
→ Edit 6 行的「上月基线」「本月目标」（用 1.1 拿到的上月习惯完成天数）

**4.4 `## 🚧 上月遗留问题与本月对策` 表格**
→ 对话产出 → Edit 替换 `| | | |`

**4.5 `## 📋 本月行动清单`**
→ 四类各 3-7 条 `- [ ]`，用户挑/对话产出

**4.6 Frontmatter**
- `theme`: 一句话主题
- `what will make this month awesome`: 让本月精彩的事
