---
name: weekly-report
description: 按功能主题聚合生成每周工作周报（一级功能名 + 分层 bullet，每条写清背景、动作和结果），跨 repo 合并同一功能主题的工作。覆盖 skywork/agent 各子项目 git 提交、Obsidian area::work 完成任务、brain 中 quest/memo/notes 进展。Use when the user asks for 周报 / 本周工作总结 / 周五总结 / weekly report / weekly summary, especially around end-of-week or when explicitly invoked.
---

# Weekly Report

**按功能/产品主题聚合**写周报。**一级标题是功能主题名**，下面用分层 bullet 展开说明，不写二级粗体类型。输出直接到 chat，不写文件。

核心区别：一个功能主题（如 Code Native、附件与工作区、发布与稳定性）可能跨 gateway / fe / cli / memory-service 多个 repo；一个 repo（如 gateway）也可能服务多个功能主题。周报必须用功能视角合并，不能照搬 repo 分组。

## 工作流（一次性，按顺序）

1. 调用 `scripts/week_range.py both` 拿到 `<本周一>\t<现在>`，把本周一 ISO 日期记为 `$SINCE`
2. **并行**跑三个 collector（同一条消息里多个 Bash 调用）：
   - `scripts/collect_git.sh $SINCE` — 各 repo 我的提交
   - `scripts/collect_obsidian.sh $SINCE` — 本周完成的 area::work 任务
   - `scripts/collect_brain.sh $SINCE` — quest dashboard + 本周 memo + 最近 notes
3. 综合三路数据，按下文「合成规则」生成 Markdown，输出到 chat

不需要写文件、不需要再问用户。所有数据源默认从 `$HOME/Code/skywork/agent` 取（脚本默认值，无需传 root 参数）。

## 数据源说明

| 数据源 | 信号价值 | 注意 |
|---|---|---|
| git 提交 | 最权威的"做了什么"，按 repo 天然分组 | brain repo 的提交是日志归档，不算工作产出；`skyclaw` 和 `skyclaw-1` 是同名镜像，合并去重 |
| Obsidian area::work | 真实时间投入 + 沟通/评审/排查类工作（git 看不到） | 文件路径里 `1-daily/` 是当天时间块，`1-projects/` 是项目维度 |
| brain memo | 每日"做了什么 / 关键决策 / 待跟进" — 周报最高密度信息源 | 每个 daily memo 已结构化，可直接复用工作分类 |
| brain quests | 主线任务状态（进行中/已完成） | "已完成" 中本周日期的 quest 是关键进展 |
| brain notes | 本周新增/修改的设计文档、分析报告 | 反映"做过的深度思考" |
| Plane 缺陷 / Obsidian tasks | 缺陷定位、修复动作、验收结果 | 先按功能主题归并，再并入对应一级条目；不要单独堆成缺陷清单 |

## 合成规则

### 第一步：先识别本周的「功能主题」清单（关键步骤）

不要直接按 git repo 分组。先从 Obsidian 任务和 brain memo 里抽出本周的功能主题维度：

1. **Obsidian projects 文件路径**：`2-task_management/1-projects/<XXX>.md` 里的 `XXX` 就是功能/产品主题名。本周如果某项目文件下有完成任务，就是一个候选一级条目。常见例子（从用户 vault 已知）：
   - 「万能框」（统一入口产品，跨 gateway/oh-my-agent/chat 多 repo）
   - 「架构重构」（gateway 底盘改造，i18n / 模板 / 产物列表 / 通知 / 撞墙 / 软拦截 等子主题）
   - 「GeneralAgent channel 设计」（IM 渠道相关，channels + gateway）
   - 「2026 工作」（年度汇总，里面条目要再按主题拆给具体功能主题，不要叫"2026 工作"）
   - 「学习使用 Claude Code & Codex」（工具学习，一般归"其他"）
2. **brain memo / notes 重复主题词**：每天 memo 里 `### gateway` / `### channels` / 自由主题 标题，以及"做了什么"段落里反复出现的功能词（code-native、附件、文件树、monitoring、发布、Codex、MTVM、Plane 缺陷主题等）。
3. **git commit message 主题前缀**：`feat(oma-extra)` → 万能框路由；`feat(i18n)` → 架构重构 i18n；`fix(notifications)` → 架构重构产物通知；`feat(sessions)` → 架构重构会话列表；等等。

把 git commits、Obsidian 任务、brain memo / notes / Plane 缺陷三路信号都**归属到这些功能主题**。一个 commit 跨多个 repo 也只算到一个功能主题里。

### 第二步：何时按 repo 聚合（兜底）

只有当某个产出**没有明确功能主题归属**时，才按 repo 单列。典型场景：
- 新建一个独立的工程仓库（如本周的 `Pyinfralib`）— 仓库本身就是项目
- 纯粹一个 repo 的小修复，没有对应 Obsidian/memo 主题（如 `trace-my-agent` 单 commit 配置补充） — 进"其他"段
- 一个 repo 承载本周主要工作且没有更细的产品项目区分（如 `Skyclaw` 前端整周做产物浮层）

### 结构（只有一级）

```
{功能主题名}{可选状态备注}
- {短标题 1}
  - {背景 / 动作 / 结果}
- {短标题 2}
  - {背景 / 动作 / 结果}
- ...

{下一功能主题}
- ...

其他
- {bullet 主题 1}
- {bullet 主题 2}
- ...
```

- **一级 = 功能主题名**：裸文本，不加 `#`、不加 `**` 粗体、不加 "项目" 后缀。直接 `Code Native` / `附件与工作区` / `前端与 Chat SDK` / `MTVM` 即可。
- **状态备注**（可选）：项目名后括号补关键状态，如 `Gateway(已上线，等待前端上线后开启流量）`。仅在明确上线/灰度/暂停状态时加。
- **没有二级粗体**。不要写 `**WebSocket 会话管理**` 这种小标题。
- **一级条目 = 一个完整功能主题**：标题尽量短，后面用 1-3 个缩进 bullet 解释背景、改动和结果；如果主题更复杂，再缩进一层拆开。优先写成“问题是什么 / 做了什么 / 结果如何”。
  - 例：
    - `goal mode 的中断与恢复链路继续收口`
      - 修了 pause goal、child goal notification、goal defer bootstrap 等边界，避免前端/后端对同一轮任务状态理解不一致。
      - `Plane` 和 Obsidian 里相关缺陷、任务再归并到同一主题下。
  - 例：
    - `uploaded_files 路径可见性修复`
      - 把用户上传文件统一放到前端和 runtime 都能理解的位置，解决“文件实际存在但 UI/工具看不到”的问题。
      - 如果还涉及兜底方案，可继续补一层说明上传失败时的替代路径。

### 条目尺度（重要）

- **粒度要粗**：一个功能主题通常 3-5 个一级条目，不要超过 6 个。多个相关 commit 必须并成一条。
- **每个一级条目下面 1-3 个缩进 bullet**，必要时再缩进一层；说明里可以写更完整的背景、动作、效果。
- **标题尽量短**，说明可以稍长，但不要堆 commit 细节、行号、文件名。
- **可以**：协议/产品名词、关键效果括号补充、并列主题用顿号
- **不要**：commit hash、MR 编号、文件路径、行号、内部 ID、变量名
- **形式自由**：标题不一定是动词起头，关键是能看出功能主题。

### "其他" 段（倒数第二段，可选）

零散工作（独立的评审、沟通、例行上线、跨项目讨论、问题排查、工具沉淀）不要单独成功能主题。用 `其他` 一级标题，下面**用 bullet list**，每条一个独立主题；如果需要，也可以加 1 条缩进说明。范例：

```
其他
- 商业化改版评审 + gateway 重构汇报
  - 说明评审结论、协作对象和对后续实现的约束。
- release 分支两次例行上线
- feishu/lark 渠道拆分讨论
- pull-all.sh 集成 code-review-graph 增量刷新（工具沉淀）
```

注意：每条 bullet 是独立主题，**不要**把无关事项用顿号串到同一条里。如果本周这类事项不多（< 3 件），可以不写"其他"段。

### "下周计划" 段（最后一段，独立章节，可选）

把下周可推进的事项单独成段，**放在整份周报的最后**。一级标题用 `下周计划`，下面 bullet list，每条一个清晰可执行的事项；如果有背景，再补一层说明。范例：

```
下周计划
- 修复 soft_intercept 边界（mark_balance ≤ 0 应硬拦截）
- 修复 oh-my-agent artifact 归并 bug（降级逻辑收紧）
- 推进 VNC 下游 deadline 机制（与 oh-my-agent 团队对齐）
- 推进 us prod gateway 上线
```

线索来源：brain memo 的"待跟进"、quest dashboard 的"进行中"、本周遗留 issue。没有清晰线索就**省略整段**，不要硬编。

### 排序

- 功能主题顺序：本周工作量从大到小（综合 Obsidian 任务数 + commits 数 + memo 着墨）。
- 项目内 bullet 顺序：核心功能 → 优化 → 修复，影响面大的在前。

### 去重与降噪

- 跨 repo 的同一功能主题工作 → 必须合并到同一个功能主题下，不要拆 repo 列。
- `skyclaw` 与 `skyclaw-1` 内容相同 → 只保留一个。
- 多个 commit 实现同一主题 → 必须并成一条。i18n / VNC / 模板系统 / 通知 等大主题一条搞定，不分拆。
- 纯 `chore: bump submodule` / `chore: rename` → 不写，除非整周只有这类。
- Obsidian 里时间打卡型任务（"09:00-10:00 看消息"、"提交报销"）→ 不进周报。
- 跨项目元工作（工具沉淀、知识归档）→ 放"其他"段，不单独成功能主题。
- 项目内**不写 Next 小节**。下周计划放整篇最后的「下周计划」独立段，不要混到"其他"里。

## 输出范例（必须严格对照风格）

```markdown
Channels
- chat 链路从 legacy 全量切到 gateway-ws（test 已切，pre/prod 灰度中）
- WhatsApp Baileys 多账号串号、扫码失败死循环、错误凭据伪装 active 等顽疾集中修复
- bot disable/enable 跨 pod 实时广播；artifact 投递规则按产品重定义

Gateway(已上线，等待前端上线后开启流量）
- 优雅停机 + cancel 端到端传播，告别 orphan turn
- 日志/指标全链路打通（trace_id、W3C traceparent、Prometheus + Grafana）
- 断线重连复用 live consumer，多 tab/刷新场景流式顺序正确
- IM 会话元信息持久化与回填，能与 web 会话区分
- 商业化撞墙落地（cost 上报、benefits 透传、user_abort 卡）
- 数据治理：主键统一 Snowflake，对数据分析师可用

Skyclaw
- WS 断线重连 + 顶栏状态 banner，刷新/抖动/重启都能续上
- Sessions Tab 全屏视图（筛选/搜索/产物计数）
- 资源面板支持从老系统导入文件
- 会话分享 + 匿名重放页
- 卡片类型补全（session_title、plan_update、user_abort 等）

其他
商业化改版评审、gateway 重构汇报、release 分支两次例行上线、feishu/lark 渠道拆分。
```

## 自检清单（输出前）

- [ ] 一级标题用的是**功能主题**名，不是 repo 名（除非这个 repo 本身就是一个独立工程项目）
- [ ] 同一功能主题跨多个 repo 的工作已合并到一起，没有按 repo 拆开
- [ ] 没有任何二级粗体标题 / `**xxx**` 子分类
- [ ] 项目名后不带 "项目" 二字（写 `万能框` 不写 `万能框 项目`）
- [ ] 每个功能主题 ≤ 6 个一级条目
- [ ] 同一大主题（i18n、通知、VNC、模板等）合成一条
- [ ] 没有 commit hash / MR 号 / 文件路径 / 行号
- [ ] 没有 `**Next**` 小节（下周计划必须单独成段，放整篇最后）
- [ ] "其他"段是 bullet list，每条独立主题（不用顿号串无关事项），且不混下周计划
- [ ] 如果有下周计划，单独以 `下周计划` 作为最后一个一级标题
- [ ] skyclaw / skyclaw-1 已合并
- [ ] brain 提交未单独成项目
- [ ] 整篇 ≤ 35 行
