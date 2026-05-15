# 任务数据查询（共享 reference）

Daily / Weekly / Monthly / Quarterly / Yearly review 都需要从 vault 收集任务数据（完成的 / 未完成的 / 按 area 分组等）。本文件统一定义工具选择、vault 任务格式、按时间窗口的查询模板。

各层 reference 只在「第 1 步：聚合数据」里 link 本文件 + 指明本层用哪几个查询。**不在每层重复抄查询命令。**

---

## 工具选择（双轨）

### 优先：`obsidian` 官方 CLI（Obsidian.app 内置）

直读 Tasks 插件数据库，最准确。文档见 `obsidian-cli` skill 的 tasks 段落（如 `obsidian tasks daily todo`）。

### Fallback：`rg`（ripgrep）

直接 grep vault 文件，正则匹配 Tasks 语法。任何机器立即可用，缺点是拿到的是字符串行，需自己解析。

### 检测哪个可用

```bash
obsidian tasks daily todo 2>&1 | head -3
```

- 输出**实际任务列表** → 用 `obsidian tasks ...`，具体命令查 `obsidian-cli` skill
- 输出 `Your Obsidian installer is out of date...` 或类似警告 → 降级用 `rg`
- 输出报错或 `unknown command` → 降级用 `rg`

**注意**：Go 写的 `obsidian-cli`（`/opt/homebrew/bin/obsidian-cli`，v0.2.x）**没有** tasks 子命令，不要和官方 `obsidian` 命令混淆。

---

## Vault 任务格式（Tasks 插件语法）

- `- [ ]` 未完成 / `- [x]` 已完成
- Emoji 元数据：
  - `📅 YYYY-MM-DD` — 截止日期（due）
  - `✅ YYYY-MM-DD` — 完成日期（completion）
  - `⏳ YYYY-MM-DD` — 计划日期（scheduled）
  - `🛫 YYYY-MM-DD` — 开始日期（start）
  - `⏫` 高 / `🔼` 中 / `🔽` 低 优先级
- 内联属性：`[area::work|learning|health|family|entertainment|technique]`

例：`- [x] 06:45 - 07:30 了解 Skills 加载 [area::technique] 🔼 ⏳ 2026-05-13 ✅ 2026-05-13`

---

## 任务文件位置

| 路径 | 用途 |
|---|---|
| `1-plan/1-daily/YYYY-MM-DD.md` | daily 文件的 day planner（**主要任务来源**） |
| `1-plan/2-weekly/YYYY-Www.md` | 本周计划任务 |
| `1-plan/3-monthly/YYYY-MM.md` | 本月行动清单 |
| `2-task_management/1-projects/*.md` | 项目页任务（如「架构重构」「OpenClaw 养成」） |
| `2-task_management/2-tasks/*.md` | 长期任务清单（工作 / 个人日常） |

---

## 排除规则

收集任务时**默认排除**：

- `assets/templates/` — 模板里的 `- [ ]` 示例（rg 加 `-g '!assets/templates/**'`）
- `_archive/` — 归档
- `4-knowledge_hub/` — 知识库剪藏里偶尔出现的 `- [ ]` 不是用户的任务

---

## rg 查询模板

下面所有命令的 `<DATE>` 替换为目标日期（如 `2026-05-13`），`<VAULT>` 是 vault 根目录。

> 实操时先 `cd "<VAULT>"`，避免每条命令都拼绝对路径。

### Q1 - 指定日期完成的任务（全 vault）

```bash
rg "^- \[x\].*✅ <DATE>" --type md -g '!assets/templates/**' -g '!_archive/**'
```

### Q2 - 指定日期逾期未完成（截止 ≤ 今天且未勾）

按月构造正则，匹配截止日期早于或等于今天的未完成任务：

```bash
# 例：今天 2026-05-13，逾期 = 截止 ≤ 05-13
rg "^- \[ \].*📅 (2026-05-(0[1-9]|1[0-3])|2026-0[1-4]-..|2025-..-..)" --type md
```

更简单：直接拉所有未完成任务再让 LLM 过滤日期。

```bash
rg "^- \[ \].*📅 \d{4}-\d{2}-\d{2}" --type md -g '!assets/templates/**' -g '!_archive/**'
```

### Q3 - 时间窗口完成的任务

```bash
# 本周（如 W20 = 2026-05-11 ~ 2026-05-17）
rg "^- \[x\].*✅ 2026-05-1[1-7]" --type md

# 本月（2026-05）
rg "^- \[x\].*✅ 2026-05-" --type md

# 本季（Q2 = 04, 05, 06）
rg "^- \[x\].*✅ 2026-0[456]-" --type md

# 本年（2026）
rg "^- \[x\].*✅ 2026-" --type md
```

### Q4 - 按 area 过滤

```bash
# 本周 work 完成
rg "^- \[x\].*✅ 2026-05-1[1-7].*\[area::work\]" --type md

# 本月 health 完成
rg "^- \[x\].*✅ 2026-05-.*\[area::health\]" --type md
```

### Q5 - 按 area 分组统计

```bash
rg "^- \[x\].*✅ 2026-05-1[1-7]" --type md -o | rg -o "\[area::\w+\]" | sort | uniq -c | sort -rn
```

输出形如：
```
  12 [area::work]
   5 [area::learning]
   3 [area::health]
   ...
```

### Q6 - 项目页本期新增 / 完成任务

项目页里的 task 完成日期可以跨整个项目周期。要"本周/本月在项目页有新进展"：

```bash
# 本周项目页里完成的任务
rg "^- \[x\].*✅ 2026-05-1[1-7]" --type md 2-task_management/1-projects/
```

### Q7 - 长期未完成（积压）

某项目 / 某 area 的未完成 task，不限日期：

```bash
# 项目页所有未完成
rg "^- \[ \]" --type md 2-task_management/1-projects/

# 整个 vault 未完成 work 任务
rg "^- \[ \].*\[area::work\]" --type md -g '!assets/templates/**'
```

### Q8 - 计数（只要数量）

```bash
rg "^- \[x\].*✅ 2026-05-" --type md -c | awk -F: '{sum+=$2} END {print sum}'
```

### Q9 - 指定日期 scheduled 的活跃 task（跨文件）⭐ 晨间必查

用户的工作 / 学习 task 散布在 daily / weekly / 项目页（`2-task_management/1-projects/*.md`）/ 5-wiki 等多个文件，统一通过 `⏳ YYYY-MM-DD` 调度到目标日期。**不能只查 daily 的 day planner**，那里只有「时段安排」(吃饭/通勤/陪娃 等)，工作 ticket 不在里面。

**按时间筛、不按 file 筛**，一次性收集全 vault 所有 schedule 到今天的活跃 ticket：

```bash
# 优先：obsidian 官方 CLI 全 vault todo + grep 时间
obsidian tasks todo --vault "Obsidian Vault" | rg "⏳ <DATE>"

# Fallback：rg 全 vault（排除模板/归档/知识库/brain）
rg "^- \[ \].*⏳ <DATE>" --type md -g '!assets/templates/**' -g '!_archive/**' -g '!4-knowledge_hub/**' -g '!brain/**'

# 晚间版：看 ⏳ 今天 中已完成的有几条（落地核对）
obsidian tasks done --vault "Obsidian Vault" | rg "⏳ <DATE>"
```

⚠️ **不要用 `obsidian tasks file="<项目页名>" todo`**：
- file= 只接单个文件，要逐项目轮询
- path= 不接受文件夹（会报错 `is a folder, not a file`）
- 用户可能新增项目页，写死文件名会漏

按时间筛是唯一正确做法。

### Q10 - 跨 repo git 提交（vault 外数据源）⭐ Review 必查

工程师用户日常工作很多落在 git commit 而非 task 勾选。Review 时**必须**扫一遍 monorepo 子目录今日 commits，否则会大幅低估实际工作量。

**配置**：
- 默认 monorepo root：`$HOME/Code/skywork/agent`
- 可通过环境变量 `MONOREPO_ROOTS` 覆盖（多个用 `:` 分隔）：`export MONOREPO_ROOTS=$HOME/Code/skywork/agent:$HOME/Code/other-org/repos`

```bash
MONOREPO_ROOTS="${MONOREPO_ROOTS:-$HOME/Code/skywork/agent}"
DATE="<DATE>"
NEXT_DATE=$(date -j -v+1d -f "%Y-%m-%d" "$DATE" "+%Y-%m-%d")

# 拿邮箱（从任意一个子 repo 读 git config）
EMAIL=""
for root in $(echo "$MONOREPO_ROOTS" | tr ':' '\n'); do
  for d in "$root"/*/; do
    if [ -d "$d/.git" ]; then
      EMAIL=$(git -C "$d" config user.email 2>/dev/null)
      [ -n "$EMAIL" ] && break 2
    fi
  done
done

# 遍历所有 monorepo + 子目录拉当日 commits
for root in $(echo "$MONOREPO_ROOTS" | tr ':' '\n'); do
  for d in "$root"/*/; do
    name=$(basename "$d")
    if [ -d "$d/.git" ]; then
      commits=$(git -C "$d" log --since="$DATE 00:00" --until="$NEXT_DATE 00:00" --author="$EMAIL" --pretty=format:"  [%h|%ad] %s" --date=format:"%H:%M" 2>/dev/null)
      if [ -n "$commits" ]; then
        echo "=== $name ==="
        echo "$commits"
      fi
    fi
  done
done
```

**brain 仓库**（vault 内的独立 git repo）单独查：

```bash
git -C "<VAULT>/brain" log --since="<DATE> 00:00" --until="<NEXT_DATE> 00:00" --pretty=format:"  [%h|%ad] %s" --date=format:"%H:%M"
```

**对接展示**：按 repo 分组列出，每行 `[hash|HH:MM] commit message`。如果某 repo 当日 0 commits，跳过不列。

### Q11 - 未完成任务池（Plan 段挑选用）⭐ Plan 必查

复用用户「`0-dashboard/个人首页/任务管理/任务清单/任务列表.md`」「`0-dashboard/个人首页/任务管理/本周待办/{重要紧急,重要不紧急,不重要紧急,不重要不紧急}.md`」「`0-dashboard/个人首页/任务管理/任务提醒/{下周任务,下周以后的任务}.md`」的过滤规则。

**基础过滤规则**（所有视图共享）：
- `not done`（未勾）
- 文件不在 `assets/` `brain/` 文件夹
- 文件 frontmatter 没有 `status` property，**或** `status` 不在 `["待拆解", "暂停", "已结束"]`

**拉取 + 解析**（obsidian 官方 CLI 不支持按 task priority/scheduled 字段过滤，需 rg + LLM 解析）：

```bash
# Step 1: rg 拉所有未完成 task 行（带文件路径 + 行号）
rg "^- \[ \]" --type md \
  -g '!assets/**' -g '!brain/**' \
  -g '!_archive/**' -g '!4-knowledge_hub/**' \
  --no-heading -H -n
```

输出每行：`<file>:<lineno>:- [ ] <task text>`

**Step 2：LLM 解析每行**，提取：
- task text（去掉前缀 `- [ ] `）
- priority：`⏫` 或 `🔺` = 高 / `🔼` = 中高 / `🔽` = 低 / 无标记 = 无 → 归为 priority **>=medium** 阈值：`⏫/🔺/🔼`
- scheduled：`⏳ YYYY-MM-DD`（解析日期，对比 target_day 所在 ISO 周）
- due：`📅 YYYY-MM-DD`
- area：`[area::xxx]`
- backlink：`<file>` 路径

**Step 3：可选 frontmatter status 过滤**（对每个文件读 frontmatter，跳过 status 含已结束/暂停/待拆解 的文件）：

```bash
# 拿到候选文件列表后批量查 frontmatter
obsidian-cli --vault "Obsidian Vault" frontmatter --print "<file>" 2>/dev/null
# 检查 status 字段，若在 [待拆解, 暂停, 已结束] 中 → 跳过该文件所有 task
```

简化版（如果嫌慢）：直接跳过这一步，前端用人眼判断。

**Step 4：两个视图**（同一组 task 编号一致 [#1] [#2] ...，方便跨视图引用）：

**视图 A — 四象限**（参考四象限.canvas 的 4 个文件过滤逻辑）：

| 象限 | priority | 时间窗 |
|---|---|---|
| 重要紧急 | ≥ medium（⏫/🔺/🔼） | 本周内 或 已逾期（happens in this week OR happens on or before today） |
| 重要不紧急 | ≥ medium | 本周后（happens after this week） |
| 不重要紧急 | < medium（🔽/无） | 本周内 或 已逾期 |
| 不重要不紧急 | < medium | 本周后 或 无 scheduled |

**视图 B — 按 backlink（来源文件）分组**：

直接按 file 路径分组展示，每组下列出该文件的所有 task（带编号）。

**展示模板**：

```
📋 任务池（编号跨视图共享）

【视图 A：四象限】

🔥 重要紧急（{N} 条）
  [#1] {task text} {priority} {⏳/📅 日期} ←{file basename}
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
```

数量太多时（>20）只显示**重要紧急 + 重要不紧急** 前 N 条；其余说"还有 M 条不重要的，要看吗？"

### W1 - 批量写入 ⏳ schedule 时间（Plan 段尾巴自动执行）⭐ 写入操作

用户在 Plan 段挑选 N 个 task 序号（如 `#1 #3 #7`）后，skill **不二次确认**直接把这些 task 行的 `⏳` 改为 target_day。

**流程**：

1. 从 Q11 输出里拿到选中 task 的元组 (file_path, line_no, task_original_full_line)
2. 对每个 task 行用 Edit：
   - 原行有 `⏳ YYYY-MM-DD` → Edit 替换该日期为 `⏳ <NEW_DATE>`
   - 原行无 `⏳` 标记 → Edit 在行末追加 ` ⏳ <NEW_DATE>`（注意空格分隔）
3. 写入完后**不要重新展示任务池**，只简短确认："已 schedule {N} 条到 {YYYY-MM-DD}" + 列改动的 task title

**Edit 锚点策略**：
- old_string 用**整行 task 原文**（包含 `- [ ]` 前缀和所有 emoji 元数据），保证唯一
- 如果同一文件里多条 task 内容完全相同（极少见），上下加 1-2 行做局部锚点
- 不需要 path/line_no 精确定位，rg 输出的 task text 已足够唯一

**示例**：

原文件 `2-task_management/1-projects/2026 工作.md` 第 42 行：
```
- [ ] publish_artifact 流式tool_use 根治产物卡顺序issue [area::work] 🔼 ⏳ 2026-05-13
```

用户选 `#3` 改为今天（2026-05-14）：
- old_string: `- [ ] publish_artifact 流式tool_use 根治产物卡顺序issue [area::work] 🔼 ⏳ 2026-05-13`
- new_string: `- [ ] publish_artifact 流式tool_use 根治产物卡顺序issue [area::work] 🔼 ⏳ 2026-05-14`

**注意**：Edit 操作要逐个 task 调用（同 file 多 task 可并行调用，但 old_string 必须互不重叠）。

---

## 输出整理建议

**给用户看的展示要精简**，不要把 rg 结果全文 dump 到 chat。原则：

1. **数字摘要优先**：`本周完成 X 条 / 未完成 Y 条 / 完成率 Z%`
2. **按 area 分组**：用 Q5 的统计，列前 3-5 个 area
3. **挑亮点**：从完成列表里挑 3-5 条**用户可能想庆祝**的（不是琐碎日常）
4. **挑张力**：从未完成列表里挑 1-3 条**已逾期或拖延多次**的（不是临时任务）
5. **跨项目分布**：从文件路径看任务集中在哪几个项目页

**不要做**：

- 把 30 条任务原文贴到 chat
- 把 daily 文件里的「吃饭 / 通勤 / 洗漱」也列出来（这些是 day planner 的"生活流"，不是值得复盘的任务）

---

## 与各层 review 的对接

| 层级 | 主要查询 | 重点 |
|---|---|---|
| Daily Review | Q1（当日完成） + **Q9 done 版（⏳ 当日落地）** + **Q10（跨 repo git）⭐** + brain memo 当日 | 看 win 是否落地 + 实际工作量 |
| Daily Plan | **Q11（任务池）⭐** + Q2（逾期） + 当日 day planner | 挑 win + W1 写入 schedule |
| Weekly Review | Q3（本周完成） + Q5（按 area） + Q6（项目页本周） + **Q10**（本周 git） | 模式、对比上周 |
| Weekly Plan | **Q11** + Q7（积压） | 下周 objectives |
| Monthly Review | Q3（本月） + Q5 + Q7（积压） + **Q10**（本月 git） | 趋势、积压 |
| Monthly Plan | **Q11** + 上月遗留 task | 本月行动清单 |
| Quarterly | Q3（本季 vs 上季） + Q7 + **Q10**（本季 git） | 战略级、长期未推进 |
| Yearly | Q3（全年 vs 上年） + Q7 + **Q10**（全年 git） | 项目维度、年度叙事 |
| Weekly | Q3（本周完成）+ Q5（按 area 分组）+ Q6（项目页本周） | 模式、对比上周 |
| Monthly | Q3（本月）+ Q5（按 area + 月内逐周）+ Q7（积压） | 趋势、积压 |
| Quarterly | Q3（本季 vs 上季）+ Q7（跨季积压） | 战略级、长期未推进 |
| Yearly | Q3（全年 vs 上年）+ Q7（年度积压 / 放弃） | 项目维度、年度叙事 |

各层 reference 在「第 1 步：聚合数据」会指明用哪几个查询。
