# Frontmatter 字段规范

剪藏笔记必须使用此 frontmatter，**字段顺序固定**（便于 diff 和 Dataview 渲染）。

## 字段表

| 字段 | 类型 | 是否必填 | 来源 | 默认值 |
|---|---|---|---|---|
| `status` | enum | ✅ | 固定 | `In Progress` |
| `type` | enum | ✅ | 来源映射 | — |
| `category` | list | ✅ | AI 推断（见 category-pool.md） | — |
| `tags` | list | ✅ | AI + 兜底 | `[clippings]` |
| `summary` | string | ✅ | AI | — |
| `comment` | block | ✅ | AI（多行 `\|-` 块） | — |
| `media` | enum | ✅ | 来源映射 | — |
| `source` | url | ✅ | 原 URL/路径 | — |
| `rating` | enum | ⬜ 留空 | 用户手填 | (空) |
| `author` | list | ⬜ | 抓取 | — |
| `cover` | url | ⬜ | 抓取封面 | — |
| `completed` | datetime | ✅ | 系统 / 用户告知 | 见下方"completed 规则" |
| `published` | date | ⬜ | 抓取 | — |
| `created` | date | ✅ | 系统 | 剪藏当天 `YYYY-MM-DD` |

## status enum（用户已固定）

```yaml
status:        # 取值只能是下列之一
  - In Progress  # 默认：剪藏进入但尚未消化
  - Later        # 推迟，没排日程
  - Next         # 下一个要看
  - Now          # 当前正在看/听
  - Paused       # 暂停
  - Will Not Do  # 决定不再看
```

**skill 始终填 `In Progress`**。历史文件出现的 `Done` 兼容不报错，但 skill 不主动生成。

## type enum

```yaml
type:
  - 播客
  - 文章
  - 视频
  - 推文
  - PDF
  - 笔记      # 本地 markdown / 其他笔记
```

## media enum（来源平台）

```yaml
media:
  - 小宇宙
  - 微信公众号
  - 少数派
  - 知乎
  - 微博
  - YouTube
  - B站
  - X
  - Substack
  - Medium
  - 博客         # 通用，识别不出具体平台时
  - 本地         # 本地文件
```

新平台允许新增，但首次新增时在回复中提示。

## tags 约定

- 自动包含 `clippings`
- 加 1-5 个内容关键词（中英文均可，单词级，不带 `#`）
- 不要重复 category 已表达的信息

## completed 规则

按"知道多少精度就写多少精度"，**不要伪造**：

| 场景 | 写什么 | 例子 |
|---|---|---|
| 用户当下剪藏（隐含"刚听完/刚看完"） | `YYYY-MM-DD HH:MM`（剪藏时刻） | `2026-05-12 09:34` |
| 用户明确说"刚刚 / 现在 / X 分钟前" | `YYYY-MM-DD HH:MM`（消息时刻或回推） | `2026-05-12 09:30` |
| 用户说"昨天 / N 天前 / 上周" | 只写日期 `YYYY-MM-DD`（分钟未知，**不要补 12:00 也不要补 00:00**） | `2026-05-07` |
| Review 老文件时无任何时间线索 | 用原 `created` 字段做日期代理；分钟仍**不补** | `2026-04-15` |
| 完全不知道 | 留空 | (空) |

**Obsidian 显示约定**：用户 vault 把 `completed` property 配置为 datetime 类型，日期-only 的值会被渲染成 `2026-05-07 00:00`。这是**精度信号**——看到 `00:00` 就知道"分钟未知"，而不是真的凌晨。skill 不要试图通过补 12:00 等手段消除这个信号。

## summary 写法

- 100-300 字，一段
- 中文，第三人称视角
- 聚焦"这篇/这期讲了什么 + 核心结论"
- 不要"本文将讨论"这种引导句

**YAML 语法（重要）**：summary 必须用 `>-` folded block 写法，不要写成 plain scalar。

```yaml
summary: >-
  正文 ...（一段，可任意包含 :、{、[、" 等特殊字符）
```

为什么：plain scalar 里出现 `Pre-train : Post-train` 这种"**ASCII 冒号 + 空格**"会被 YAML 当成嵌套 mapping，导致整个 frontmatter 失效不渲染。folded block 不解析这些字符，最安全。

## comment 写法

```yaml
comment: |-
  - 第一条要点（金句或核心观点，一句话能立住）
  - 第二条要点
  - ...
```

- 5-10 条，每条独立成立，不依赖上下文
- 用 `|-` 块标量，避免转义麻烦
- 中文为主，可保留英文术语

## 示例（完整）

```yaml
---
status:
  - In Progress
type:
  - 播客
category:
  - 个人成长-认知思维
  - 心智与方法
tags:
  - clippings
  - AI
  - 心力
summary: >-
  孟岩与李继刚在播客中探讨了 AI 时代...
comment: |-
  - 投资的本质是利用现有资源换取未来世界财富占比的增加
  - 互联网通过编织连接获取价值，AI 公司通过构建深度的"井"服务用户
  - ...
media:
  - 小宇宙
source: https://www.xiaoyuzhoufm.com/episode/69a64629de29766da93331ec
rating:
author:
  - 无人知晓
cover: https://image.xyzcdn.net/...jpg
completed: 2026-05-12 09:34
published: 2026-03-03
created: 2026-05-12
---
```
