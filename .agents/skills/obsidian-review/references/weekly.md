# Weekly Review/Plan 流程

每周一次的回顾 + 下周计划，最佳时机周日晚或周一晨。**这是 review 链路里产出最丰富的一层**，因为周报有现成的 weekly-report skill 可复用。

## Mode + 触发时机

入参 `/obsidian-review weekly [<mode>]`，mode 缺省 = Review + Plan 连贯。

| Mode | 走什么 |
|---|---|
| 缺省 | **Review 上周 + Plan 本周** 连贯（推荐周日晚 / 周一晨） |
| `review` | 只 Review 上周 |
| `plan` | 只 Plan 本周（仍读上周 review 数据作为输入） |

Review 段额外数据源（除下面表格列出的字段外）：
- 本周 7 个 daily 的 frontmatter + 笔记 + 任务
- 本周完成 tasks（[tasks-query.md](tasks-query.md) Q3/Q5/Q6）
- **本周跨 repo git 提交**（Q10，工程师必查）
- weekly-report skill 产出（作为「💼 工作」段内容）

Plan 段额外数据源：
- 上月 monthly 的 theme（保持目标对齐）
- 未完成任务池（Q11，挑下周重点的素材库）

---

## 目标文件结构

`<VAULT>/1-plan/2-weekly/YYYY-Www.md`（ISO 周编号，如 `2026-W20`）。

### Frontmatter 字段切分（用 Edit 替换单行写入，**不要用 obsidian-cli --edit**）

| 字段 | 类型 | 段 | 说明 |
|---|---|---|---|
| `objectives` | string | **Plan** | 本周目标（≤3 个） |
| `need to Improve` | string | **Plan** | 基于上周 review 承诺的下阶段改善方向 |
| `effectiveness` | string | Review | 整周效能感 |
| `reading` | string | Review | 本周阅读**内容**（从 `4-knowledge_hub/Clippings/` 本周新增 + readwise archive 提取主题分组，**不是天数**）|
| `gratitude` | string | Review | 感激 |
| `celebrations` | string | Review | 庆祝 |
| `can do better` | string | Review | 可改善 |
| `what I learned` | string | Review | 学到的 |

⚠️ **写入前先 Read 上 1-2 周 weekly 文件对齐字段历史格式约定**。不同字段历史值风格差异大：
- `effectiveness` 历史值是星级评分（如 `⭑⭑⭑⭑⭑`），**不要填文字描述**
- `reading` 历史可能是 `X/N 天`，新约定是阅读内容主题分组
- 多数字段是 1 句 20-40 字精炼描述，不是段落

### 正文 section（用 Edit 替换/追加）

正文里有 Dataview/Base 自动渲染的「Days」「剩余和逾期任务」「已完成的任务」section，**skill 不要动这些代码块**。需要写入的 section（全在「📊 本周总结（周末回顾时填写）」标题之下）：

1. **每日关键词表格** — 7 行表格，填 `日期 / 关键词 / 效率 / 感受 / Win the Day`
2. **核心成就**（4 个子标题）：
   - `### 💼 工作` — 调用 weekly-report skill 自动填
   - `### 🛠️ 技术探索` — 对话产出
   - `### 📚 学习成长` — 对话产出
   - `### 👨‍👩‍👧 家庭生活` — 对话产出
3. **🏃 健康习惯打卡表格** — 8 行 × 7 天 + 完成率
4. **运动记录** — 简短文字
5. **本周笔记与反思** 下 4 个子段：值得庆祝 / 可以做得更好 / 本周感悟 / 家庭笔记
6. **💡 本周关键收获** — 1-3 条关键收获
7. **⏭️ 下周重点** — 下周 win 候选（可留空 1-2 个关键词；Plan 段会直接做 W+1 完整「本周计划」section）

### Plan 段需补 W+1 顶部「本周计划」section（模板没有，必须 skill 起草）

⚠️ **Weekly 模板只覆盖 frontmatter + Days + 任务概览 + 周末总结**，没有顶部「本周计划」section（这是用户实际使用时手动加的）。skill 创建新 weekly 文件后，**必须**在 nav 行之后、`# Days` 之前补这一段。结构参考上一周 weekly 文件，骨架：

```
# 本周计划 📝

> [!info] 本周目标（YYYY-MM-DD 至 YYYY-MM-DD）
> 本周重心 ...

> [!note] 上周遗留 & 延续事项
> - ...（来自 review insight + 标 ❌/⏩ 的 task）

## 💼 工作（第一优先级）
本周聚焦方向（**主题方向 + 项目页 wikilink，不复制具体 task**）：
- **主题 1** — 简述 → [[项目页]]
- **主题 2** → [[项目页]]

## 🏃 健康 & 家庭（红线）
- [ ] 周级承诺 task（高 level，如「读书 ≥3/7」「周末不加班」）

## 📚 学习与成长
本周聚焦方向（同 💼 工作风格）：
- **主题 1** → [[项目页]]

## ⚠️ 红线
- 红线条目

## 💡 上周关键提醒
> [!tip] 三条延续认知
> 1. ...
```

**关键风格原则**：

- **「💼 工作」/「📚 学习与成长」是主题方向**（无 `- [ ]` 勾选 + 用 `→ [[项目页]]` wikilink），**不复制项目页具体 task**。具体 task 留在项目页（已 ⏳ schedule），会被「本周任务概览」dataviewjs 自动归集到本周 weekly 视图。
- **「🏃 健康 & 家庭」是周级承诺**（如「读书 ≥3/7」「英语启蒙 ≥4/7」），是 weekly 自带的 task，用 `- [ ]` 勾选。
- **写完后**周末 Review 时**逐条结清**「💼/🏃/📚」三段的 task（done / cancel / 迁下周）— 见工作流第 4 步 4.9。

---

## 时机判断

- 若本周文件不存在 → 用 obsidian-cli 触发 `Weekly` 模板创建
- 若文件存在但「📊 本周总结」整段空 → 进入完整回顾流程
- 若部分填了部分没填 → 列出已填和未填段落给用户，问"想补哪几段"
- 若用户明说"周计划" → 跳过总结环节，只做下周 objectives 和重点

---

## 工作流（完整周回顾约 15-25 分钟）

### 第 1 步：批量聚合 7 天 daily 数据

用 obsidian-cli 高效拿数据，**不要一次 Read 7 个完整文件**。

**1.1 算出本周日期范围**（周一到周日，ISO 周）。

**1.2 拿 7 天 frontmatter**（一次性，循环调 `obsidian-cli --vault "Obsidian Vault" frontmatter "1-plan/1-daily/YYYY-MM-DD" --print` 拿每天的 properties）：
```
对 YYYY-MM-DD（周一到周日）的每个 daily 文件，取以下 frontmatter：
3 words, feeling, effectiveness, intention, win the day,
celebrations, can do better, gratitude,
🧘‍♂️ 冥想, 💪🏼 运动, 👶🏻 育儿, 📚 读书, 💧 喝水, 😴 早睡, 🇬🇧 英语启蒙, 🥣 健康饮食
```

**1.3 拿本周全 vault 任务完成情况**（见 [tasks-query.md](tasks-query.md)）：
- **Q3 本周完成的任务**：`✅ 本周日期范围`，全 vault 范围（daily + weekly + monthly + 项目页 + 任务清单都覆盖），不只 7 个 daily 文件
- **Q5 按 area 分组统计**：算出 work / learning / health / family / technique 各完成多少条
- **Q6 项目页本周新增进展**：仅扫 `2-task_management/1-projects/`，看哪几个项目这周真正推动了
- **Q7 长期未完成**（积压）：本周遗留的 `- [ ]` 任务，特别是带 `📅` 早于本周的（已逾期）
- 同时**对比上周**（W19）的完成数 + area 分布，用于展示 C 的同比变化

**1.4 拿 7 天笔记主体的关键 callout**：Read 每个 daily 的「笔记」callout 块（健康/家庭/个人/工作 四段），只提**非空**的条目作为素材。

**1.5 工作部分**（最重要）：**直接调用 weekly-report skill**。
- 用 Skill 工具调用 `weekly-report` skill，让它输出按产品项目聚合的周报 Markdown
- 不要重新跑 weekly-report 的 collector 脚本，直接用 skill 产出
- 拿到产出后**原样**作为 `### 💼 工作` 的内容（不要重新组织）
- ⚠️ weekly-report 产出末尾的「下周计划」段**只作为 Plan 段的输入参考**，**不**直接复制到本周 review 文件；下周计划由 Plan 段从任务池挑统一产出（避免多来源冲突）

**1.6 盘点上周顶部「本周计划」section 的 task**（⭐ Review 段必查）：Read 上周 weekly 文件顶部「本周计划」section（💼 工作 / 🏃 健康 & 家庭 / 📚 学习与成长），列出所有 `- [ ]` task，准备在第 4.9 步跟用户对每条结清（done / cancel / 迁移）。

### 第 2 步：组织数据展示（按表格）

把第 1 步的数据整理成几张可读的「快照」给用户看：

**展示 A：每日关键词表格**
```
日期 | 关键词 (3 words)         | 效率 (effectiveness) | 感受 (feeling) | Win the Day
周一 2026-05-04 | 紧张/破壁/通透 | high                 | 平静            | 完成 X 评审
周二 ...
```
（直接是 weekly 模板里要的表格，用户后面只需确认）

**展示 B：习惯打卡矩阵**
```
习惯        | 一 | 二 | 三 | 四 | 五 | 六 | 日 | 完成率
🧘‍♂️ 冥想    | ✅ | ✅ | ⚪️ | ✅ | ✅ | ⚪️ | ✅ | 5/7
...
```
后面再加一行**与上周对比**（用 obsidian-cli 读上周 weekly 的同张表）。

**展示 C：任务完成统计**（全 vault 范围）
```
本周完成任务：X 条（上周 Y 条，变化 ±Z）
按 area 分布：
  - work: 12 条（上周 15，↓3）
  - learning: 5 条（上周 3，↑2）
  - health: 3 条（上周 7，↓4 ← 异常）
  - family: ...

项目维度本周推进（仅项目页）：
  - 项目 A: {N 条完成} — 关键里程碑：{...}
  - 项目 B: {N 条完成}
  - 项目 C: 0 条 — 本周完全没动 ⚠️

未完成 / 积压：
  - 本周新增未完成：{N} 条
  - 历史逾期（截止已过仍未勾）：{N} 条，主要在 {area / 项目}
```

数字只用一行总结，**不要把任务原文全贴出来**（rg 结果可能 50+ 条）。挑值得复盘的：项目推进、积压、area 失衡。

**展示 D：本周工作（来自 weekly-report skill）**
原样把 weekly-report 产出贴出来。

**展示 E：观察到的模式**（这是 skill 的关键价值）
```
🔍 我注意到：
- 健康类任务完成率 43%，比上周（71%）显著下降
- "感受" 字段连续 4 天写"累"，但 "win the day" 都完成了
- 周三周四没写「笔记 / 工作」callout，但 day planner 全勾
- 上周「下周重点」是 X，本周看起来只推进了一半
```

### 第 3 步：苏格拉底式追问（按需，目标是填完待写字段）

**问题要从展示 E 的"模式"里来**，针对张力点：

- 张力：完成度高但情绪差 → "win 都拿下了但你写了 4 次'累'，是任务量重还是某类型的任务消耗大？比如沟通/评审 vs 编码/思考？"
- 张力：某 area 任务完成率显著下降 → "健康类任务从 71% 降到 43%，发生了什么？是被工作挤压，还是这周这些任务本身定得太理想？"
- 张力：上周计划未完成 → "上周说要推进 X，这周看到只动了一半。是优先级错估，还是中途有更紧急的事？"
- 张力：写了但没勾的事项 → "你 day planner 全勾但「工作笔记」是空的，是这周记录习惯没坚持，还是没东西可记？"

**也可以问一些聚焦未来的问题**：
- "如果只能挑一件下周必须完成的事让你觉得这周没白活，是什么？"
- "本周你已经做了 {weekly-report 顶部那个项目}，下周这个项目还要继续投入吗？"

**避免**：
- 不要问"你这周开心吗" 这种空泛的
- 一次问一个，但**不设硬上限** — 目标是 review 字段（effectiveness / gratitude / celebrations / can do better / need to Improve / what I learned 等）+ 正文反思四段（值得庆祝/可改善/感悟/家庭笔记）都有素材
- 用户随时可说"跳过 X / X 留空"，那个字段不再追问
- 不要替用户得结论。用户答完后用他的话整理

### 第 4 步：分段确认 + 写入

写入按以下顺序，**每写一段都先 chat 里确认**：

**4.1 每日关键词表格**（直接基于第 2 步展示 A，用户基本只需确认）
→ Edit 替换 weekly 文件的 `| 周一 | | | | |` 那 7 行

**4.2 工作部分**（来自 weekly-report）
→ Edit 在 `### 💼 工作` 标题下方插入 weekly-report 产出

**4.3 技术探索 / 学习成长 / 家庭生活**（来自对话整理）
→ Edit 在对应小标题下方插入用户认可的 bullet list

**4.4 健康习惯打卡表格**（基于展示 B）
→ Edit 替换 `| 🧘‍♂️ 冥想 | | | | | | | | /7 |` 等 8 行
→ "运动记录"单独追加 1 行

**4.5 本周笔记与反思**（值得庆祝/可改善/感悟/家庭笔记）
→ Edit 4 段 → 内容来自对话和 daily frontmatter 的 celebrations/can do better/gratitude 聚合
→ 不要全 copy daily 原文，要**归纳**

**4.6 本周关键收获**（1-3 条，对话产出）
→ Edit 在 `## 💡 本周关键收获` 下

**4.7 下周重点**（对话产出，至少 1 个 win）
→ Edit 在 `## ⏭️ 下周重点` 下

**4.8 Frontmatter**（用 Edit 逐个替换单行）
- `objectives`: 4.7 整理出的下周重点
- `effectiveness`: 整周效能感（**纯星级评分如 ⭑⭑⭑⭑⭑，不填文字描述**）
- `reading`: 本周阅读**内容**（从 knowledge_hub Clippings + readwise archive 抽主题分组，不是天数）
- `gratitude` / `celebrations` / `can do better` / `need to Improve` / `what I learned`: 来自对话和 daily 聚合，1-2 句精炼，不啰嗦

**4.9 结清上周顶部「本周计划」section 的 task**（⭐ Review 段必做收尾）：基于 1.6 盘点结果，逐条跟用户决策标记方式：

| 用户决策 | 标记方式 |
|---|---|
| ✅ Done（已达成）| `- [x] ... ✅ <今天日期>` |
| ❌ Cancel（未达成 / 主动放弃）| `- [-] ... ❌ <今天日期> (备注原因)` |
| ⏩ 迁 W+1 | 当前留 `- [-]` cancel + 备注「迁 W+1」；同时在 W+1 的「本周计划」section 重新写一条 |
| ⏳ 持续中（无明确结果）| 保留 `- [ ]` 不动 |

skill 一次列全，用户回复每条决策后**并行 Edit** 批量改 W 文件的 task 行。

---

## weekly-report skill 集成细节

调用方式：
```
通过 Skill 工具调用 weekly-report skill，不传额外参数
```

weekly-report 会输出形如：
```
万能框
- WebSocket 会话管理 ...
- ...

架构重构
- i18n 接入 ...
- ...

其他
- ...
```

把这段**原样**复制到 weekly 文件的 `### 💼 工作` 下方。**不要二次精简**，weekly-report 已经做了主题合并。

注意：weekly-report 的产出有"产品项目"层级，但 weekly 模板只有「工作」一个小标题。在 `### 💼 工作` 下方直接贴 weekly-report 的多级产品项目结构，不需要再加额外小标题。

如果 weekly-report 报错（如不在 Code/skywork/agent 目录下），降级方案：从本周 7 个 daily 的 `area::work` 已完成 task 中提取，按 daily 文件名提到的项目分组。明确告诉用户"weekly-report 跑不起来，用降级数据"。

---

## Plan 段补充流程（weekly 特定）

通用 Plan 段（任务池挑序号 + W1 schedule 写入）见 SKILL.md 主流程。weekly 特有的补充步骤：

### P.1 任务池清理建议（展示任务池前，可选）

任务池积压 > 20 条时，先做一轮清理再挑序号。skill 主动指出以下 4 类候选，让用户决策：

1. **疑似已完成但未标 ✅**：同 file 同名 / 近似名 task 历史已完成（grep 验证），但当前仍是 `- [ ]`
2. **重复 / 可合并**：多条 task 描述高度重叠（同主题，不同切面），询问是否合并成一条
3. **描述含混**：task 文本太宽（如「各 IM 稳定性优化」），询问是否细化、链接 wiki 或拆分
4. **高优 ⏫/🔺 但无 ⏳ schedule**：紧急但日期没定，询问 schedule 到哪一天

每条给具体建议（标完成 / 删 / 合并 / 细化 / schedule 哪天），让用户一次性回复批量决策，并行 Edit。

### P.2 「下周方向」补建议 — review 给的方向 vs 任务池

把上周 review 段 `need to Improve` + weekly-report「下周计划」段 + 用户口述方向，列出来跟任务池对比：

- 任务池里**有对应** task → 标记为本周聚焦，进入 P.3 schedule
- 任务池里**没对应** task → 用 N1 / N2 / N3 ... 编号问用户「要不要新建？在哪个项目页加？」

### P.3 Schedule 分配策略需显式告知

用户挑序号后，**先告知分配逻辑**再批量写入（不要直接默默分配到不同天）：

| 策略 | 适用 |
|---|---|
| 按 area 分散 | work 排工作日、learning 排工作日早晚、technique/finance 排周末 |
| 按 priority 集中 | ⏫ 排周一/二、🔼 排周中、无标 排周末 |
| 全 ⏳ 同一天 | 让用户在 daily plan 时再细化 |

如果用户挑 5+ 条没指定日期，给一个 area-based 默认方案，让用户认可或调整后再批量 Edit（W1 写入）。

### P.4 起草 W+1 顶部「本周计划」section（必做）

详见上方「目标文件结构 → Plan 段需补 W+1 顶部「本周计划」section」。这一步**和 frontmatter objectives 写入并行**，骨架包括：

- 本周目标（≤3 个高 level 关键词，呼应 frontmatter objectives）
- 上周遗留 & 延续事项（来自 review insight + 4.9 标 ❌/⏩ 的 task）
- 💼 工作 / 📚 学习与成长 的主题方向 + 项目页 wikilink（**不复制具体 task**）
- 🏃 健康 & 家庭的 `- [ ]` 周级承诺 task
- ⚠️ 红线
- 💡 上周关键提醒（3 条延续认知）

⚠️ 写入前 Read 上周（W）顶部「本周计划」section 的实际格式，对齐结构和风格。

---

## 退出条件

- 用户说"够了 / 大方向有了" → 把已确认的段落写入，未确认的留空（用户后续手动补）
- 中途用户跑题 → 跟随用户聊，不要硬拉回模板
- 一次没必要写完所有段落 → 可以分两次（第一次重点+工作，第二次反思+下周）
