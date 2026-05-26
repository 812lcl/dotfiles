# Quarterly Review/Plan 流程

每季度一次，做季末回顾 + 下季计划。视野从「趋势」升到「战略」。这是节奏最慢、对话密度最高、价值最大的一层。

## Mode + 触发时机

入参 `/obsidian-review quarterly [<mode>]`，mode 缺省 = Review + Plan 连贯。

| Mode | 走什么 |
|---|---|
| 缺省 | **Review 上季 + Plan 本季** 连贯（推荐季初前 2 周，可分 2-3 次完成） |
| `review` | 只 Review 上季 |
| `plan` | 只 Plan 本季（仍读上季 review 数据作为输入） |

Review 段额外数据源：
- 本季 3 个 monthly 的 frontmatter + 5 大段
- 本季所有 weekly 的「💡 本周关键收获」
- 本季所有 daily 的 8 习惯打卡（季度统计）
- 本季完成 tasks（[tasks-query.md](tasks-query.md) Q3/Q5/Q6/Q7）+ 按月分布
- **本季跨 repo git 提交**（Q10）
- 上季 quarterly 数据用于对比
- 项目里程碑（`2-task_management/1-projects/`）+ OKR 进展（`0-okr/`）

Plan 段额外数据源：
- 上季 quarterly 的 `commit to improve` / `top 3 learnings` / 「下季度改进方向」
- 上一年同季 quarterly（看季节性模式）
- 本年 yearly 的 theme + vision（保持目标对齐）
- 未完成任务池（Q11，挑核心项目里程碑的素材）

---

## 目标文件结构

`<VAULT>/1-plan/4-quarterly/YYYY-QN.md`（如 `2026-Q2`）

### Frontmatter 字段切分

| 字段 | 类型 | 段 | 说明 |
|---|---|---|---|
| `theme` | string | **Plan** | 季度主题 |
| `focus` | string | **Plan** | 季度聚焦点（≤3 个） |
| `commit to improve` | string | **Plan** | 基于上季 review 承诺下季改进 |
| `celebrations` | string | Review | 庆祝 |
| `can do better` | string | Review | 可改善 |
| `top 3 learnings` | string | Review | 季度 Top 3 收获 |

### 正文 section

**季初规划**（PLANNING AHEAD）：
- `## 🎯 本季度主题`（含上季度启示引用）
- `## 📍 季度关键指标` 6 行表格
- `## 🚀 核心项目与里程碑`（项目 1/2/...）

**季末回顾**（LOOKING BACK）：
- `## 💡 季度关键洞察` 4 个子段：biggest win / wasn't able to accomplish / Top 3 learnings / committing to improve
- `## 📈 季度对比分析`：健康习惯对比表 / 工作产出对比 / 个人系统对比 / 关键指标达成情况表
- `## 🎯 下季度改进方向`：待改进项 3 / 新增目标 3

**自动渲染**（**不动**）：
- `# PLANNING AHEAD` 下的 projects base / OKR base
- `## Months` 下的 base
- 各种 base 块

---

## 路由：回顾还是规划？

- 季末（季度最后 2 周内）→ 默认季末回顾
- 季初（季度前 2 周内）→ 默认季初规划
- 中间 → 问用户

---

## 季末回顾流程

### 第 1 步：聚合本季度数据

**1.1 读本季 3 个 monthly**（M1/M2/M3）的：
- Frontmatter（theme / celebrations / can do better / need to Improve / what I learned）
- 「What went well / didn't go well / I'd like to improve / I learned」5 大段
- 「关键指标」表格的实际达成

**1.2 读本季所有 weekly**（约 13 个）的「💡 本周关键收获」（不读全文，只读这一段）。

**1.3 习惯打卡季度统计**：用 obsidian-cli 批量读本季所有 daily（约 90 个），算每个习惯的「完成天数 / 季度总天数 / 完成率」。
- 同时拿上季度同样数据用于对比

**1.4 任务完成情况**（见 [tasks-query.md](tasks-query.md)）：
- **Q3 本季完成任务**：`✅ 2026-0[456]-`（按本季月份调整），**全 vault 范围**
- **Q5 按 area 分组** + 按月细分（3 个月的趋势比单数字更有信号）
- **Q6 项目维度**：扫 `2-task_management/1-projects/`，每个项目本季完成 task 数 + 关键里程碑
- **Q7 跨季积压**：截止日期早于本季首日仍未完成的任务（这是真正的"长期拖延"）
- 同样拿上季度数据用于对比

**1.5 项目里程碑**：读 `<VAULT>/2-task_management/1-projects/` 下本季有更新的项目文件，看哪些 milestone 命中。

**1.6 OKR 进展**：如果用户用 `<VAULT>/0-okr/`，读对应 quarter 的 KR 文件，看进展。

### 第 2 步：组织数据展示

季度展示**比月度更宏观**。3-5 张快照：

**展示 A：3 个月主题串联**
```
本季 3 个 monthly theme：
- M1 (YYYY-MM): {X}
- M2 (YYYY-MM): {Y}
- M3 (YYYY-MM): {Z}

季初设的 theme: "{季度主题}"
你的 focus: "{focus}"

→ 是否对得上？
```

**展示 B：习惯打卡季度对比**（这是模板里要的表）
```
习惯       上季完成率   本季完成率   变化     评价
🧘‍♂️ 冥想   65%         73%         ↑8       稳步提升
💪 运动    72%         48%         ↓24      显著下滑 ← 高亮
...
```

**展示 C：季度关键指标达成**
```
指标          目标     实际    达成
早睡          每日     70%     部分
运动          每日     48%     未达
...
```

**展示 D：本季 Top 收获候选**（来自 1.1 + 1.2）
列出 3 个月 + 13 周积累的所有「学到的 / 关键收获」，去重 + 聚类，**让用户从这里挑出 Top 3**。

**展示 E：核心项目里程碑达成**（基于 1.5）
```
项目 1: {名称}
  - 计划：{milestone A B C}
  - 实际：A ✅ / B ⚠️ 部分 / C ❌

项目 2: ...
```

**展示 F：观察到的季度级模式**（关键）
```
🔍 我注意到：
- 习惯里有 N 项稳定 / M 项下滑，下滑都集中在某个时段
- 本季 win 是 {X 项目}，但 {Y 项目} 拖了 3 个月没动
- 季初 focus 是 {A}，但实际 3 个月真正在做的是 {B}
- 你在 weekly 反复写 {某主题} 出现 N 次，这可能是一个未命名的长期 thread
```

### 第 3 步：苏格拉底式追问（按需，目标是填完待写字段）

季度级问题**关注战略**：

- 主题对/不对得上 → "季度主题 {X} 看起来一直被打断 / 一直在贯穿。你觉得这个主题在 Q+1 还要延续吗？还是已经完成？"
- 长期未推进项 → "{Y 项目} 三个月都没真正动，是因为不重要、不紧急、还是不想做？"
- 大模式 → "你在多个 weekly 里反复写 {Z 主题}，但它从没成为正式 objective。要不要把它升级成 Q+1 focus？"
- 习惯系统性下滑 → "运动从 72% 降到 48%，本质卡点是什么——时间、动力、还是身体？想清楚才能选对策"

**避免**：
- 不要纠结某周/某月的细节
- 不要问"开心吗"
- 要让用户**自己说出** Top 3 learnings，不要替他选

### 第 4 步：分段确认 + 写入

**4.1 `## 💡 季度关键洞察` 4 个子段**
- biggest win this quarter: 1-2 条
- What I wasn't able to accomplish: 1-3 条（重要 + 诚实）
- Top 3 things I've learned: 用户自己挑/对话产出
- What I am committing to improve next quarter: 1-3 条
→ Edit 4 段

**4.2 `## 📈 季度对比分析`**
- 健康习惯对比表（展示 B）→ Edit 6 行
- 工作产出对比 → 1-2 行
- 个人系统对比 → 1-2 行
- 关键指标达成情况表 → Edit

**4.3 `## 🎯 下季度改进方向`**
- 待改进项 3 条
- 新增目标 3 条
→ Edit

**4.4 Frontmatter**
- `commit to improve` / `celebrations` / `can do better` / `top 3 learnings`

---

## 季初规划流程

### 第 1 步：聚合数据

**1.1 上季 quarterly**：
- Frontmatter 全部
- 「💡 季度关键洞察」（特别是 commit to improve / top 3 learnings）
- 「🎯 下季度改进方向」（这是上季给本季的输入）

**1.2 上一年同季 quarterly**（如果存在）：对比同期，看是否有季节性模式

**1.3 年度 yearly**（`<VAULT>/1-plan/5-yearly/YYYY.md`）的 `theme` 和 `vision`：保证季度对齐年度

### 第 2 步：组织展示

```
📜 上季启示：
- Theme: {X}
- Top 3 收获：{1, 2, 3}
- Commit to improve: {Y}
- 上季给本季的改进方向：{A, B, C}

🎯 本年 theme: {年度 theme}
🎯 本年 vision: {年度 vision}

→ 季度主题候选（基于上季 commit + 年度 vision 推导）：{1-3 个候选让你选}
```

### 第 3 步：苏格拉底式追问（按需，目标是填完待写字段）

- "上季 commit to improve 是 {Y}，本季想怎么具体落地？设个 SMART 指标？"
- "本年 vision {Z} 在过去半年/一季完成了多少？这季要推进哪一块？"
- "本季最大的不确定性是什么？提前留缓冲还是赌一把？"

### 第 4 步：分段确认 + 写入

**4.1 `## 🎯 本季度主题`** — 一句话
**4.2 「上季度核心启示」callout** — 引用上季 Top 3
**4.3 `## 📍 季度关键指标` 6 行表格** — 基于上季实际值 + 本季目标
**4.4 `## 🚀 核心项目与里程碑`** — 2-4 个项目，每个含目标 + 关键里程碑
**4.5 Frontmatter** — `theme` / `focus`

---

## 节奏建议

季回顾不是一次跑完的，**鼓励用户分 2-3 次完成**：
- 第 1 次（季度最后一个周末）：跑回顾数据聚合 + Top 3 learnings 对话 → 写完「关键洞察」段
- 第 2 次（季度第一周）：做季初规划 → 写完「关键指标」「核心项目」段
- 第 3 次（季度第二周中）：复盘第一周走得对不对，必要时调整 focus

skill 不主动管节奏，但如果用户说"先到这"，就只写已确认的段，留 placeholder 给后续。
