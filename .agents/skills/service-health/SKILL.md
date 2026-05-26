---
name: service-health
description: skywork/agent 项目核心 8 件套（gateway / chat / creation / oh-my-agent / ockernel / channels / user_center / mis）的端到端健康检查。覆盖运行时部署真相（SLS image_name 分布 + ARMS pod image，不以 Jenkins 状态为唯一标准）、SLS ERROR/WARN pattern 分析（抽样自归类，给 top 3-5 模式 + 占比 + 样例）、部署前后对比（pattern 新增 / CPU 内存差异 / QPS 差异）、ARMS pod CPU/内存（按 ReplicaSet 分组）、RDS/Redis 实例 CPU/QPS/连接数（不查数据）。多服务并行用子代理。当用户说 "健康检查 / 查看服务状态 / check 服务 / service health / 看一下 X 服务是否正常 / X 服务怎么样 / 巡检 / 体检" 等场景时使用，无论是否带具体服务名。
---

# Service Health Check

## 何时触发

用户说：健康检查 / 巡检 / 体检 / 查看服务状态 / `service-health <服务>` / "X 服务正常吗" / "chat 怎么样" 等。

入参形式：
- `服务名` 列表，例如 `gateway chat creation`
- `服务名@环境`，例如 `gateway@us-test`（默认 us-test，可省略 @env）
- 不带参数 → 询问用户要检查什么

## 工作流概览

```
1. 解析参数（服务列表 + 环境）
2. 单服务  → 直接顺序跑 7 项检查 (§ 1.1-1.7 必做；§ 1.8 ERROR 根因深挖条件触发)
   多服务  → 每服务 1 个子代理并行（subagent_type: general-purpose）
3. 主 agent 汇总 → 多服务时输出总览表 + 异常详情
```

## 第 0 步：参数解析

支持格式：
- 服务别名（按 SSOT § 2 列表）：`gateway` / `chat` / `creation` / `oh-my-agent` / `ockernel` / `channels` / `user_center` / `mis`
- 环境后缀：`@us-dev` / `@us-test` / `@us-pre` / `@us-prod` / `@cn-test` / `@cn-pre` / `@cn-prod`
- 默认环境 = `us-test`

如用户问 "线上有问题吗" / "prod 健康吗" 等模糊请求 → 默认 prod 双区（us-prod + cn-prod）。

## 第 1 步：检查项（每服务 × 7 项，含 1 项条件触发）

主 agent / 子代理执行下列检查，**全部用 brain/tools/ 下的工具**，不要直接连服务或 DB。
§ 1.1-1.7 必做；§ 1.8（ERROR 根因深挖）只在严重 ERROR / 部署窗口内突增 / 用户明确询问时触发。

> **核心理念**：Jenkins 状态只是一个信号，不是真相。真相在 SLS 的 `_image_name_` 字段和 ARMS 的 pod image 上 — 它们反映的是"线上现在真的在跑什么版本"。先看运行时（§ 1.1），再看 Jenkins 辅助（§ 1.2）。

### 1.1 运行时部署证据（最优先 — 决定后续判定基调）

**目标**：判定"用户说的部署到底有没有真的发生 / 完成"。

#### 1.1.a SLS image_name 时间序列

```bash
bash brain/tools/sls-query.sh <service> <env> '*' --hours 2 --lines 200
# cn-prod 加 --cn
```

从返回的样本中**抽 `_image_name_` 字段**，统计：
- 出现过哪些 image_tag（格式 `<service>:v_{buildnum}_{branch}_{commit_hash[:8]}`）
- 每个 image_tag 的最早出现时间和最晚出现时间
- 占比（按条数）

判定：
- **新 image_tag 在最近 30min 内首次出现 + 占比 ≥ 50%** → 新版本已接管主流量 ✓
- **新旧 image_tag 各占一半，最近 10min 都还在产日志** → 滚动进行中 ▷
- **只看到旧 image_tag** → 部署未真实生效（即使 Jenkins 报 SUCCESS）
- **完全没新 image_tag 出现，但 Jenkins 在 1h 内有 deploy 触发** → 同 commit 重发或 rollout 失败

#### 1.1.b ARMS pod 当前 image

```bash
bash brain/tools/arms-pod-metrics.py <env>-<service>-<region> --window 1h
```

工具会列出当前所有 pod，从输出抽：
- 每个 pod 的 image tag
- 按 ReplicaSet hash 分组（pod name 中段如 `prod-chat-us-77646dd778-xxx`）
- 每个 RS 的 pod 数量、启动时长（uptime）

判定：
- **新 RS pod 全部 Running 且 uptime 一致** → rollout 完成
- **新旧 RS 共存 + 旧 RS 出现 Terminating** → 滚动收尾阶段
- **新旧 RS 共存 > 30min** → rollout 卡住，readinessProbe 可能没过

> 注：`arms-pod-metrics.py` 当前**只有 us-prod 集群 token**。其他环境标 ❓ 跳过这一子项，但 1.1.a SLS image_name 仍然必须做。

#### 1.1.c 综合部署判定

结合 SLS image 分布 + ARMS pod RS 状态 + Jenkins 状态（§ 1.2），按下表给结论：

| SLS image_name | ARMS RS | Jenkins | 结论符号 | 说明 |
|---|---|---|---|---|
| 新 tag ≥ 50% | 新 RS Running | SUCCESS | `↑✓` | 真部署成功 |
| 新 tag ≥ 50% | 新 RS Running | FAILURE | `↑✗⚠` | 部署成功但 Jenkins 脚本误报 |
| 新旧混跑 | 双 RS 共存 | SUCCESS | `↑▷` | 滚动进行中 |
| 仅旧 tag | 仅旧 RS | SUCCESS（同 commit） | `↑↻` | 容器未真更新（同 commit 重发） |
| 仅旧 tag | 仅旧 RS | 1h 无触发 | `—` | 部署未发生（即使用户说部署了） |
| 仅旧 tag | 仅旧 RS | FAILURE | `↑✗` | 部署真失败，已回滚 |
| 新 tag 但 < 30% | 新旧混跑 > 30min | 任意 | `↑⏸` | rollout 卡住，需查 readiness |

**关键纪律**：用户口头说"刚部署完"也要验证。如果 SLS image_name 全是旧的，主动反馈"运行时未见新版本，确认是否真触发了部署？"

### 1.2 Jenkins 辅助信息（不再决定成败）

```bash
bash brain/tools/jenkins.sh status deploy-<service-alias>-<region>-<env>      # 最近一次
bash brain/tools/jenkins.sh status deploy-<service-alias>-<region>-<env> <N-1>  # 前一次
```

服务的 Jenkins job 命名 → `brain/knowledge/infra-env-ssot.md § 1.8`。

**Jenkins 只贡献 3 条信息**：
1. **是谁触发的**：`bash brain/tools/jenkins.sh log <job> <N> | grep -E "Started by|cause"`
2. **触发时间和构建号**：用于关联 SLS image_name 的首次出现时刻
3. **image_tag 前后对比**：抽 `commit_hash[:8]`，用于决定是否要拉 git commit 摘要（§ 1.6）

**忽略**：Jenkins 的 SUCCESS / FAILURE 不作为部署成败的最终结论 — 看 § 1.1 综合判定表。

### 1.3 SLS 日志计数 + Pattern 分析

#### 1.3.a 三项基础计数（先做）

```bash
bash brain/tools/sls-query.sh <service> <env> 'ERROR' --hours 1 --count
bash brain/tools/sls-query.sh <service> <env> 'WARN'  --hours 1 --count
bash brain/tools/sls-query.sh <service> <env> '*'     --hours 1 --count
```

**service 别名**（已对齐 SSOT § 2 / 1.4）：
- `gateway` / `agent-gateway` / `chat` / `creation` / `channels` / `usercenter` (`user_center`) / `mis` (`oms`)
- `oh-my-agent-router` / `oh-my-agent-normal` / `oh-my-agent-sandbox` 分别对应 router/normal/sandbox logstore
- 国内环境用 `--cn`，跑出 `--region cn-beijing`

#### 1.3.b 关键字误命中复查

如果 `ERROR` 关键字查出的条数 / 总日志条数 > 10%，说明可能是关键字误命中（INFO 日志里 `error=None`、`error_msg=""` 等字段被全文匹配）。此时**必须复查**：

```bash
bash brain/tools/sls-query.sh <service> <env> 'level=error' --hours 1 --count
```

如果 `level=error` 的数远少于 `ERROR` 关键字数 → 在报告中标"⚠ 全文 ERROR 关键字含 INFO 误中，真实 level=error 仅 N 条"，并用 `level=error` 的数字判定。

#### 1.3.c Top ERROR Pattern（核心新增）

抽样本：
```bash
bash brain/tools/sls-query.sh <service> <env> 'level=error' --hours 1 --lines 50
# 若 level=error 抽不到样本，退回 ERROR 关键字
```

**子代理在 prompt 内做归类**（不依赖工具扩展）：
- 取每条日志的 message / msg / content 字段前 80 字符，或 stacktrace 顶端类名
- 按相似度归类（前缀相同 / 关键 token 相同视为同一 pattern）
- 列 top 3-5 pattern：占比 + 一条代表性样例（截断到 200 字符）
- 标注：根因猜测（业务噪声 / 系统故障 / 配置错误 / 依赖失效）

#### 1.3.d Top WARN Pattern

同 1.3.c，但抽 30 条 WARN 样本。WARN 通常没有 ERROR 急迫，但 WARN 出现新 pattern 是早期信号。

#### 1.3.e 部署前后 SLS 对比（仅当 § 1.1 判定为 `↑✓` / `↑▷` / `↑↻` 时做）

确认部署时刻 T（从 SLS image_name 首次出现的时刻取，比 Jenkins 时间更准）。然后分两段查：

```bash
# 部署前 30min
bash brain/tools/sls-query.sh <service> <env> 'level=error' --from <T-1800> --hours 0.5 --count
# 部署后 30min
bash brain/tools/sls-query.sh <service> <env> 'level=error' --from <T> --hours 0.5 --count
```

对比 ERROR/min 变化：
- 持平 ±20% → 部署无回归 ✓
- 上升 50%-200% → 有回归风险 ⚠，深挖部署后新出现的 pattern
- 上升 > 200% → 强回归信号 ✗，建议考虑回滚

**新增 pattern 检测**：分别抽部署前/后各 30 条 ERROR，对比是否有"只在部署后出现"的 pattern。这种 pattern 是回归的直接证据。

### 1.4 ARMS Pod CPU/内存（按 RS 分组 + 部署前后对比）

```bash
bash brain/tools/arms-pod-metrics.py <env>-<service>-<region> --window 1h
```

**新增报告要点**：
- pod 列表按 ReplicaSet hash 分组（从 pod name 抽，如 `prod-chat-us-77646dd778-*`）
- 每个 RS 列：pod 数量、image_tag、CPU/MEM 范围、最长/最短 uptime
- 标识异常 pod：CPU 或 MEM 偏离同 RS 均值 2σ 的列出来

**部署前后对比**（仅当 § 1.1 判定为 `↑✓` / `↑▷` 时）：
- 旧 RS 部署前 30min 的 CPU/MEM 均值
- 新 RS 当前 CPU/MEM 均值
- 对比是否有显著上升（如新版本 MEM 比旧版本高 50%+ → 可能内存泄漏 / 新引入依赖膨胀）

> 注：`arms-pod-metrics.py` 当前**只 us-prod 有 token**。其他集群失败标"❓ ARMS 无 token"跳过。

### 1.5 RDS / PolarDB-X 实例指标 + 部署前后对比

```bash
brain/tools/aliyun-rds-metrics.py <instance-id> --hours 2
```

工具自动按实例前缀分支：
- `rm-*` → 走 cms（CPU/MEM/IOPS/Conn/QPS/TPS/Sessions 全有）
- `pxc-*` → 走 polardbx `DescribeDBNodePerformance`（**只有 active_connection 可用**，CPU/MEM 给控制台链接）

**Region 自动推断**（不用传 `--region`）：
- `rm-0xi*` / `pxc-vgr*` → us-east-1
- `rm-2ze*` / `pxc-bjr*` → cn-beijing

从 SSOT § 2 拿对应环境的 DB host 第一段（如 `pxc-bjrghp1e9u97tk.polarx.rds.aliyuncs.com` → `pxc-bjrghp1e9u97tk`）。

**部署前后对比**：取 2h 窗口（默认），分别计算部署前后 30min 的 active_connection / QPS / CPU 均值，对比变化。

### 1.6 Redis 实例指标 + 部署前后对比

```bash
brain/tools/aliyun-redis-metrics.py <redis-instance-id> --hours 2
```

走 r-kvstore 原生 `DescribeHistoryMonitorValues` API（**兼容 standard / cluster / sharding 全架构**）。

**Region 自动推断**：`r-0xi*` → us-east-1，`r-2ze*` → cn-beijing。

从 SSOT § 3 "跨服务 Redis 实例对照" 拿对应环境的 Redis 实例 ID。

**部署前后对比**：取 2h 窗口，对比部署前后 30min 的 CPU / QPS / Conn 均值。Redis QPS 突变 > 3× 是强信号（可能新版本改了缓存策略或缓存击穿）。

**共享实例提示**：多服务共享同一 Redis 时（如 chat / creation / user_center / mis / channels US prod 都用 `r-0xihvfxq1oc2ps1ryv`），主 agent 汇总时注释"共享实例已在 X 服务下检查"避免重复展示。

### 1.7 部署变更的 git commit 摘要

仅当 § 1.1 判定为 `↑✓` / `↑▷` 且 § 1.2 显示 commit hash 不同时执行：

```bash
cd <service-repo-path>
git fetch origin --quiet
git log <prev_commit_hash>..<curr_commit_hash> \
  --pretty=format:'  - %h | %an | %s' \
  --no-merges
```

`prev_commit_hash` / `curr_commit_hash` 从 image_tag 末尾抽，例如 `v_405_master_0723a890` → `0723a890`。

提取作者 + 主题，分组：
- **feature**：标题含 `feat:` / `feature:`
- **bugfix**：标题含 `fix:` / `bugfix:` / `hotfix:`
- **其他**：merge / chore / 配置等

若是同 commit 重发（§ 1.1 判定为 `↑↻`），跳过 git log，但要**主动询问**最近一次操作者：`bash brain/tools/jenkins.sh log <job> <N>` 抓 `Started by user ...`。

### 1.8 ERROR 根因深挖（条件触发，定位代码 + git blame + 修复建议）

> **触发条件**（满足任一即做）：
> 1. 某 Top ERROR pattern 占比 > 50%（业务噪声除外）
> 2. 某 Top ERROR pattern 在部署窗口内 **+100% 突增**（部署前后对比）
> 3. 用户在 prompt 里明确说"是谁引入的 / 修复建议 / 怎么修"
> 4. 部署判定为 `↑✗`（部署真失败）

不触发就跳过这一项，避免无脑往代码里钻。

#### 1.8.a 定位代码位置

从 § 1.3.c 抽出的 ERROR 样本里找最有线索的一条：
- **首选**：日志里的 `caller` 字段、`stacktrace`、`file:line` 格式（如 `lib/oss/oss.go:137`）
- **次选**：日志里的方法名 / 函数名（如 `GetInternalContent`、`UploadToOSS`），需要 grep 搜
- **下下选**：日志的关键字（如 `InvalidAccessKeyId`），grep 全 repo

#### 1.8.b 在 repo 内查代码 + git blame

服务对应的 repo 路径默认是 `/Users/liuchunlei/Code/skywork/agent/<service>`（agent-gateway 是 `gateway/`，详见 SSOT）。

```bash
cd /Users/liuchunlei/Code/skywork/agent/<service>
git fetch origin --quiet

# 1. 先看这一行/段代码现状
sed -n '<line-10>,<line+5>p' <file>
# 或 grep 'InvalidAccessKeyId' -rn .

# 2. git blame 看是谁、哪个 commit 引入的
git blame -L <line>,<line> <file> | head -1
# 或 git log --all --oneline -S '<关键字符串>' -- <file>   （字符串首次出现的 commit）

# 3. 看那次 commit 的上下文（不要 diff，太大）
git show <commit_hash> --stat
git log <commit_hash> -1 --pretty=format:'%h | %an | %ae | %ad | %s' --date=short
```

#### 1.8.c 给出修复建议（分类）

按 pattern 根因分类（沿用 § 1.3.c 的根因猜测）：

| 根因类型 | 修复建议范式 |
|---|---|
| **凭证 / 配置错误**（OSS AK / Token / Auth） | "不是代码 bug。需要运维操作：1) 找 X 团队确认 AK 是被禁还是过期；2) 更新 Nacos 配置 `<dataId>` 或 toml 配置 `<key>`；3) 重启或热加载 pod" — **不要建议 revert commit**，因为问题不在代码 |
| **代码 bug**（NPE / Unmarshal / 越界 / 逻辑错） | "可能是 commit `<hash>` by `<author>` (`<date>`) 引入的。建议：1) review 该 commit 看是否符合预期；2) 如果是回归，发 revert MR；3) 否则加错误处理（具体代码改动建议）" — 必须给具体的代码修改方向 |
| **依赖失效**（上游超时 / 服务 down / DNS 解析失败） | "代码侧 git blame 显示这是历史代码，不是新引入。问题在上游 `<service>`。建议：1) 联系 `<上游 owner>` 看上游是否有变更；2) 在本服务侧加超时 / 重试 / 熔断（如果还没有）" |
| **业务噪声** | "正常业务现象，无需修复。如果想降噪，调日志级别或改采样" — 不要去 git blame |

#### 1.8.d 输出格式

在报告"Top ERROR Pattern"段下增加"根因深挖"子段：

```
根因深挖 (仅触发条件满足时):
  Pattern: <pattern 描述>
  代码位置: <file>:<line>
  当前代码片段:
    <3-5 行 sed 输出>
  Git blame:
    commit <hash> | <author> | <date> | <subject>
  根因类型: 凭证/配置错误 (示例)
  修复建议:
    1. <具体动作 1>
    2. <具体动作 2>
    3. <具体动作 3>
```

#### 1.8.e 重要纪律

- **不要每次都做**：触发条件不满足就跳过。强行 git blame 业务噪声只会浪费 token 和制造误判。
- **git blame 只看一行/一段**：不要 git blame 整个文件，否则输出爆炸。
- **不要试图修代码**：只给修复建议（怎么改），不要 Edit 代码。健康检查是只读流程。
- **commit author 是线索不是判决**：blame 显示 "Alice 三周前写的"，不代表 Alice 现在要负责修。结合 git log 看是否近期改过、是否有相关 review。

### 1.9 业务 Grafana dashboard 关键 panel（必做）

**目标**：拿到服务侧的业务可观测信号（HTTP rate / latency p95-p99 / 业务核心计数器），比 SLS 日志条数更直观。

**工具**：`brain/tools/grafana-dashboard.py <URL>`。dashboard JSON 已缓存进 `brain/knowledge/`，**panel 跑指标只依赖 promql.py + ARMS Prometheus，不依赖 Grafana cookie**。cookie 仅 fetch / `--refresh` JSON 时需要。

**服务 → dashboard 映射**：查 `brain/knowledge/infra-env-ssot.md § 1.6` 的「业务 dashboard」表，唯一来源，**不要在 SKILL 里硬编码 UID / 路径**。SSOT 已列：每个服务对应 host (saiali / saius / aliyun-cn) + UID + Knowledge 缓存路径 + 模板变量。SSOT 未列的服务（如 user_center / mis / ockernel）= 无独立业务 dashboard，此步标 `—` 跳过。

**执行流程**：

1. 在 SSOT § 1.6 查目标服务的 dashboard UID + host
2. `brain/tools/grafana-dashboard.py <uid> --host <host> --list`，看当前 dashboard panel 标题
3. **挑 3-5 个核心 panel**（标题/语义匹配下列任一关键词即可，不强求每类都有）：
   - 流量类：`HTTP rate` / `QPS` / `request_count` / `messages_*`
   - 错误类：`5xx` / `4xx ratio` / `non_200_rate` / `error_*`
   - 时延类：`latency p95` / `p99` / `Time Cost`
   - 业务核心计数器：`active connections` / `consumer exit reason` / `Finish Card Delay` 等服务特有指标
4. 用 URL（带 `var-Datasource` / `var-source` 等，从 SSOT § 1.6 拼出对应 prod/test 集群的 datasource 名）+ `--panels <id1,id2,...>` 跑出来
5. 部署前后看趋势：再跑 `--since 1h` 看 panel 在 T 时刻前后是否有阶跃

**判定**：
- 各 panel 拿到数值且在该 dashboard 历史基线范围内 → ✓
- panel 返回 "no series" → ⚠（该指标可能在该环境未采集，结合 SSOT § 1.4 SLS logstore 缺失情况判定）
- promql.py 报错 → 见 `brain/tools/README.md § promql.py` 排错
- dashboard JSON 缺失且 cookie 过期 → ❓ 跳过，**不阻塞其它检查**

### 1.10 K8s deployment / pod 资源健康（部署后必做）

**目标**：部署后看新 RS 的 pod 真的 Ready 起来了没、有没有 restart / OOM / probe failure / CPU throttle。

**工具**：`brain/tools/grafana-dashboard.py` 走 aliyun-cn Grafana 的**通用 k8s dashboard**（一套面向所有 ACK 集群，按 `var-datasource` 切集群、按 `var-namespace` / `var-name` / `var-pod` 切目标）。

**触发条件**：§ 1.1 判定为 `↑✓` / `↑▷` 时必做；非部署窗口可选。

**Dashboard 列表 + UID + 缓存**：见 `brain/knowledge/infra-env-ssot.md § 1.6` 「通用 k8s dashboard」表（cluster / namespace / node / workload / deployment / pod 6 张），SKILL 不硬编码。本步主要用其中 2 张：
- **Deployment**（看 desired/available 副本、rollout 进度）
- **Pod**（看 restart count、probe failure、CPU vs limit、MEM vs limit）

**调用方式**：用裸 UID + `--host` 走工具，参数从 SSOT 拿，**不要在 SKILL 里写死 URL / host / cluster_id**：

```
grafana-dashboard.py <UID> --host <host_key> --panels <ids> \
  --var datasource=<ds> --var namespace=<ns> --var name=<dep> --var pod=<pod>
```

- `<UID>` / `<host_key>`：查 SSOT § 1.6 「通用 k8s dashboard」表
- `<ds>`：查 SSOT § 1.6 「ARMS Prometheus 公网 endpoint」表（按目标环境取 datasource 名）
- `<ns>`：查 SSOT § 1.2 Namespace 表（按服务取目标 namespace）
- `<dep>` / `<pod>`：从 § 1.4 ARMS pod 列表抽，deployment 名 = `<env>-<service>-<region>`，pod 名再加 `-<rs-hash>-<suffix>`

**关键 panel 名（按标题语义匹配，id 跑 `--list` 看实际）**：

| 维度 | panel 标题关键词 | 用途 |
|---|---|---|
| Pod | Restart Count | 部署窗口外应为 0 |
| Pod | Warning Events | 探针失败 / 调度失败等异常事件 |
| Pod | CPU Usage Percent / CPU Throttled Percent | CPU 用量 vs limit |
| Pod | Memory Percent / Memory Failcnt | MEM 用量 + OOMKilled 信号 |
| Deployment | Replicas（desired / available / unavailable）| rollout 进度 |

**判定**：

| 指标 | ✓ | ⚠ | ✗ |
|---|---|---|---|
| Pod restart count（部署窗口外）| 0 | 1-2 | > 2 |
| Probe failure rate | 0 | 偶发 | 持续 |
| CPU usage / limit | < 70% | 70%-90% | > 90% throttle 风险 |
| MEM usage / limit | < 70% | 70%-85% | > 85% OOMKilled 风险 |
| desired ≠ available（rollout 时段外）| — | 短暂 | 持续 5min+ |

**纪律**：
- aliyun-cn cookie 过期会 fallback 到 stale dashboard 缓存（仍能跑 PromQL）；完全无缓存才标 ❓ 跳过
- 这一项**只看 pod 健康编排面**，不重复 § 1.4 ARMS pod CPU/MEM 的内容；§ 1.4 看单 pod 性能曲线，§ 1.10 看 restart / probe / rollout 异常

## 第 2 步：多服务并行（subagent）

若服务数 ≥ 2，**每服务一个子代理**：

```
Agent({
  description: "健康检查 <service>",
  subagent_type: "general-purpose",
  prompt: "你需要对服务 <service>@<env> 做健康检查。

  执行 ~/.agents/skills/service-health/SKILL.md 的 10 项检查流程，使用以下工具：
  - brain/tools/jenkins.sh
  - brain/tools/sls-query.sh
  - brain/tools/arms-pod-metrics.py
  - brain/tools/aliyun-rds-metrics.py
  - brain/tools/aliyun-redis-metrics.py
  - brain/tools/promql.py             # 任意 ARMS PromQL（4 集群已接入）
  - brain/tools/grafana-dashboard.py  # 业务 dashboard 关键 panel + k8s 通用 dashboard

  **关键纪律**：先做 § 1.1 运行时部署证据（SLS image_name 分布 + ARMS pod image），
  得出综合部署判定后再看 Jenkins。Jenkins 状态只是辅助信号。

  报告必填以下内容：
  1) 综合部署判定（↑✓/↑✗⚠/↑▷/↑↻/—/↑✗/↑⏸ 之一 + 一句话理由）
  2) Top 3-5 ERROR pattern（占比 + 样例 + 根因猜测）
  3) Top 3-5 WARN pattern
  4) 部署前后对比（如果有部署）：ERROR/min 变化、新增 pattern、新 RS vs 旧 RS CPU/MEM、DB/Redis QPS 变化
  5) ARMS pod 按 RS 分组列表
  6) **业务 dashboard 关键 panel（§ 1.9，必做）**：按服务→dashboard 映射跑 3-5 个核心 panels（HTTP rate / 5xx / latency p95 / 业务计数器），给当前值与基线偏离判定。dashboard JSON 已在 brain/knowledge/ 缓存，**Grafana cookie 过期不影响 panel 查询**（PromQL 走 ARMS）。
  7) **K8s deployment / pod 资源（§ 1.10）**：仅当部署判定 ↑✓ / ↑▷ 时做。从 § 1.4 抽 1-2 个新 RS pod name，跑 aliyun-cn k8s-pod dashboard 看 restart count / probe failure / CPU vs limit / MEM vs limit。
  8) **ERROR 根因深挖（§ 1.8）**：仅当某 pattern 占比 > 50% 非业务噪声 / 部署后 +100% 突增 / 部署判定 ↑✗ 时触发。
     用 git blame 定位代码 + commit author，按根因类型（凭证 / 代码 bug / 依赖失效）给修复建议。

  从 brain/knowledge/infra-env-ssot.md 查该服务的：
  - Jenkins job 名（§ 1.8）
  - SLS service 名（§ 2.X）
  - DB host + Redis 实例（§ 2.X 和 § 3）
  - 业务 dashboard URL / UID（§ 1.6 + 本 SKILL § 1.9 服务映射表）
  - K8s 通用 dashboard URL（本 SKILL § 1.10 模板）

  阈值判定见 ~/.agents/skills/service-health/references/thresholds.md。

  按 thresholds.md 中的输出格式返回单服务报告，**600 行内**。
  如果发现 CRIT 级异常，把根因猜测 + 下一步建议放在最前面。"
})
```

**并行调度**：N 个子代理在一个 message 里发出，Claude 会自动并行。

## 第 3 步：汇报

### 报告设计原则

1. **第一屏决断**：顶部 3 行（状态徽章 / 部署判定 / 关注项汇总）让读者扫一眼就知道"有没有问题、是什么"。
2. **章节统一表格化**：所有指标都用 `指标名 │ 数值 │ 状态` 三列对齐，方便扫读。Status 列固定 `✓ / ⚠ / ✗ / — / ❓`。
3. **关注项独立提出**：所有 ⚠ / ✗ 在顶部「🔔 关注项」汇总，避免散落各章节里被忽略。
4. **emoji 章节锚点**：📦 部署 / 📊 SLS / 🖥️ ARMS / 🚢 K8s / 📈 Dashboard / 💾 DB / 🧠 Redis / ⏭ 下一步 — 视觉锚点便于快速跳读。
5. **数值列右对齐+单位贴近**：`2,444` / `31.69 /s` / `7.28%` 这种格式比纯数字更可读。

### 单服务：详细模式

```
╭─ 🟢 / 🟡 / 🔴 <service> @ <env>  ───────────────────────────────╮
│ 部署判定:  <symbol>  <一句话>  (#N, <relative-time>)           │
│ 总体评级:  🟢健康 / 🟡 N 项关注 / 🔴 N 项异常                  │
╰─────────────────────────────────────────────────────────────────╯

🔔 关注项  (无则写"无,各项正常")
  ⚠ <metric / 章节>      <value>           <一句话 → 建议下一步>
  ✗ <metric / 章节>      <value>           <一句话 → 建议下一步>

📦 部署                                    (§ 1.1 + § 1.2 + § 1.7)
  Jenkins         #N  SUCCESS @ <time>  (<dur>s)  by <user>
  image_tag       curr  v_NNN_branch_HHHHHHHH
                  prev  v_MMM_branch_HHHHHHHH
  Commits (<n>)   feat=N  fix=N  misc=N
                  fix   <hash>  <author>  <subject>
                  ...

📊 SLS  (1h, logstore=<logstore>)            (§ 1.3)
  指标                数值              状态
  ────────────────────────────────────────────
  Total              <n>              <rate>/min
  ERROR (full-text)  <n>              [✓/⚠]  <ratio>% 总日志
  level=[ERROR]      <n>              真实级别
  WARN               <n>              [✓/⚠]
  
  Top ERROR Pattern (从 N 条样本):
    1.[占比%]  [<level>] <module>::<func>
              "<message 前 120 字符>..."
              根因: <业务噪声/系统故障/配置错误/依赖失效>
    2.[占比%]  ...

🖥️  ARMS Pod  (<n>/<n> Running, <m> 个 RS)   (§ 1.1.b + § 1.4)
  指标                数值                          状态
  ──────────────────────────────────────────────────────
  RS                 <hash>  (image <tag>, <n> pods, uptime <h>h)
  CPU                <range> / <limit>  (~<%>)     [✓/⚠]
  MEM (含 cache)     <range> / <limit>             [✓/⚠] ARMS 含 cache,OOM 判定看 § K8s working_set
  rollout            <descr>                       [✓/⚠]
  异常 pod           <name/无>                     [✓/⚠]

🚢 K8s 资源  (aliyun-cn k8s-pod, 抽样 <pod>)  (§ 1.10, 仅部署后做)
  指标                数值              状态
  ────────────────────────────────────────────
  Replicas           <desired>/<avail> ✓
  Restart count 1h   <n>               [✓/⚠/✗]
  Warning events     <n>               [✓/⚠]
  CPU / limit        <%>               [✓/⚠/✗]
  MEM ws / limit     <%>               [✓/⚠/✗]  ← OOM 判定基准

📈 业务 Dashboard  (<host>/<uid> "<title>", cache <h>h)  (§ 1.9)
  Panel                                值                状态
  ─────────────────────────────────────────────────────────────
  [<id>] <title>                       <value with unit> [✓/⚠/✗/no series]
  [<id>] <title>                       <value>           [✓/⚠/✗]
  ...

💾 DB  <instance-id>  (<engine>, <region>, <scope>)  (§ 1.5)
  指标                数值                          状态
  ──────────────────────────────────────────────────────
  active_connection  avg <n> / max <n>             [✓/⚠]
  CPU/MEM/QPS        (aliyun CLI 不暴露 → 控制台)   —
  
  控制台: <url>

🧠 Redis  <instance-id>  (<scope>)               (§ 1.6)
  指标                数值              状态
  ────────────────────────────────────────────
  CPU                <%>               [✓/⚠]
  MEM used           <n>               [✓/⚠]
  Conn               <n> (<%>)         [✓/⚠]
  Total QPS          <n> ops/s         [✓/⚠]
    Get / Put        <n> / <n>
  New conn/s         <n>               [✓/⚠]

部署前后对比  (仅 ↑✓ / ↑▷ / ↑↻ 触发; T = <部署时刻>)
  指标                部署前 30min      部署后 30min     Δ        状态
  ──────────────────────────────────────────────────────────────────────
  ERROR/min          <a>               <b>             <±%>     [✓/⚠/✗]
  新增 pattern       —                 <list 或"无">    
  ARMS CPU avg       <a>%              <b>%            <±%>     [✓/⚠]
  ARMS MEM avg       <a> MiB           <b> MiB         <±%>     [✓/⚠]
  DB QPS             <a>               <b>             <±%>     [✓/⚠]
  Redis QPS          <a>               <b>             <±%>     [✓/⚠]

🔍 ERROR 根因深挖  (§ 1.8, 仅触发条件满足时)
  Pattern        <pattern 描述>
  代码位置       <file>:<line>
  代码片段       <3-5 行 sed 输出>
  Git blame      commit <hash> | <author> | <date> | <subject>
  根因类型       <凭证 / 代码 bug / 依赖失效 / 业务噪声>
  修复建议       1. <动作 1>
                2. <动作 2>
                3. <动作 3>

⏭ 下一步  (针对每个关注项给具体命令,可执行)
  1. <动作 1 一句话> →  <具体命令>
  2. <动作 2 一句话> →  <具体命令>
```

### 多服务：总览表 + 异常展开

总览表（一行一服务×环境，扫一屏看完）：

```
| 服务         | Env      | 状态 | 部署 | SLS         | ARMS | DB | Redis | Dashboard | K8s |
|--------------|----------|------|------|-------------|------|----|----|-----------|-----|
| gateway      | us-prod  | 🟢   | ↑✓   | ✓ noise     | ✓    | ✓  | ✓   | ⚠ 2 项     | ✓   |
| chat         | us-prod  | 🟡   | ↑▷   | ⚠ noise 48k | ✓    | ✓  | ✓   | ⚠ p99 高   | ✓   |
| chat         | cn-prod  | 🔴   | ↑↻   | ✗ OSS AK失效| ❓   | ✓  | ✓   | ✗ 5xx 8%   | —   |
| creation     | us-prod  | 🟢   | ↑✓   | ✓ 基线      | ✓    | ✓  | ✓   | ✓         | ✓   |
```

**图例**：
- **状态**：🟢 健康 / 🟡 有关注项 / 🔴 有异常
- **部署**：`↑✓` 真实成功 / `↑✗⚠` 脚本误报但实际成功 / `↑▷` 滚动中 / `↑↻` 同 commit 重发 / `—` 部署未发生 / `↑✗` 部署失败 / `↑⏸` rollout 卡住
- **各列**：`✓` 健康 / `⚠ <一句话>` 关注 / `✗ <一句话>` 异常 / `❓` 拉不到 / `—` 该项跳过

**异常详情展开**：🟡 / 🔴 服务用"单服务详细模式"完整展开，🟢 服务略过。每个非 🟢 服务必须有「🔔 关注项」段 + 「⏭ 下一步」段。

## SSOT 参考

**所有环境信息查这里**：`brain/knowledge/infra-env-ssot.md`

- § 1.8 Jenkins job 命名
- § 2 各服务详情（Redis host / DB host / SLS logstore）
- § 3 跨服务 Redis 共享对照表

详细阈值判定 → `references/thresholds.md`

## 重要原则

1. **运行时为真**：部署成败看 SLS image_name 和 ARMS pod image，不看 Jenkins 状态。Jenkins 只回答"什么时候、谁触发"。
2. **只读，不影响线上**：严禁 PING/SELECT/INFO 直连，全部走 CloudMonitor API。
3. **失败不致命**：任何一项工具失败（权限缺失 / token 过期 / API timeout），跳过并标 ❓，**不阻塞其他项**。
4. **不假装健康**：拉不到数据时绝不写 "✓"，必须写 "❓"。
5. **不查数据本身**：DB/Redis 只查实例性能指标，不连库执行 SQL。
6. **抽样自归类**：ERROR/WARN pattern 分析不依赖工具扩展，子代理抽 30-50 条样本自己 group by 前 80 字符 / 栈顶关键字。
7. **关键字误命中复查**：当 `ERROR` 关键字查出条数 > 总日志 10% 时必须用 `level=error` 复查。
8. **部署前后对比**：检测到部署后必须做。ERROR/min 变化、新增 pattern、新 RS vs 旧 RS CPU/MEM、DB/Redis QPS 变化。
9. **基线漂移**：阈值是粗略的，发现明显异常 → 立刻给根因猜测 + 建议下一步。
10. **Dashboard cookie 与 PromQL 解耦**：业务 dashboard (§ 1.9) 和 k8s dashboard (§ 1.10) 的 panel 查询，**只要 dashboard JSON 已缓存到 brain/knowledge/，cookie 过期不影响查询**（PromQL 走 promql.py + ARMS，与 Grafana cookie 无关）。cookie 仅在首次 fetch / `--refresh` 时需要。所以 Grafana cookie 过期不能成为跳过这两项检查的借口 — 工具已在内部自动 fallback 到 stale 缓存。只有 dashboard JSON 完全没缓存时才标 ❓ 跳过。
