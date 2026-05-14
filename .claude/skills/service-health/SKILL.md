---
name: service-health
description: skywork/agent 项目核心 8 件套（gateway / chat / creation / oh-my-agent / ockernel / channels / user_center / mis）的端到端健康检查。覆盖 Jenkins 最近 1h 部署变更 + 部署前后版本对比 + 涉及 git commit 总结、SLS 日志计数（error/warn/total）、ARMS pod CPU/内存、RDS/Redis 实例 CPU/QPS/连接数（不查数据）、Nacos 最近配置变更。多服务并行用子代理（每服务一个）汇总后给总览表。当用户说 "健康检查 / 查看服务状态 / check 服务 / service health / 看一下 X 服务是否正常 / X 服务怎么样 / 巡检 / 体检" 等场景时使用，无论是否带具体服务名。
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
2. 单服务  → 直接顺序跑 7 项检查
   多服务  → 每服务 1 个子代理并行（subagent_type: general-purpose）
3. 主 agent 汇总 → 多服务时输出总览表 + 异常详情
```

## 第 0 步：参数解析

支持格式：
- 服务别名（按 SSOT § 2 列表）：`gateway` / `chat` / `creation` / `oh-my-agent` / `ockernel` / `channels` / `user_center` / `mis`
- 环境后缀：`@us-dev` / `@us-test` / `@us-pre` / `@us-prod` / `@cn-test` / `@cn-pre` / `@cn-prod`
- 默认环境 = `us-test`

如用户问 "线上有问题吗" / "prod 健康吗" 等模糊请求 → 默认 prod 双区（us-prod + cn-prod）

## 第 1 步：检查项（每服务 × 7 项）

主 agent / 子代理执行下列 7 项检查，**全部用 brain/tools/ 下的工具**，不要直接连服务或 DB：

### 1.1 Jenkins 最近 1h 部署

```bash
bash brain/tools/jenkins.sh status deploy-<service-alias>-<region>-<env>      # 最近一次
bash brain/tools/jenkins.sh status deploy-<service-alias>-<region>-<env> <N-1>  # 前一次
```

服务的 Jenkins job 命名 → `brain/knowledge/infra-env-ssot.md § 1.8`。

判定逻辑：
- 拿最近一次部署的 `timestamp` 和 `duration`，若 `now - timestamp - duration < 3600s` → **有近 1h 部署**
- 拉前一次部署对比 `image_tag`：
  - image_tag 格式形如 `v_{buildnum}_{branch}_{commit_hash[:8]}`（如 `v_405_master_0723a890`）
  - **同 commit 重发判定**：两次 `image_tag` 的 commit hash（最后一段）相同，仅 buildnum 不同 → **可疑信号**：通常是回滚 / 修配置 / pod 卡死强重启，需要给操作者备注
  - **真实变更**：commit hash 不同 → 走 1.7 拉 git commit 摘要
- Jenkins **build job 失败也要看**：`bash brain/tools/jenkins.sh status build-<service-alias>` 若 last build 失败 ⚠️

### 1.2 SLS 日志计数

```bash
bash brain/tools/sls-query.sh <service> <env> 'ERROR' --hours 1 --count
bash brain/tools/sls-query.sh <service> <env> 'WARN'  --hours 1 --count
bash brain/tools/sls-query.sh <service> <env> '*'     --hours 1 --count
```

**service 别名**（已对齐 SSOT § 2 / 1.4）：
- `gateway` / `agent-gateway` / `chat` / `creation` / `channels` / `usercenter` (`user_center`) / `mis` (`oms`)
- `oh-my-agent-router` / `oh-my-agent-normal` / `oh-my-agent-sandbox` 分别对应 router/normal/sandbox logstore
- 国内环境用 `--cn`，跑出 `--region cn-beijing`

`--count` 输出形如 `[{"c": "167"}]`。判定阈值见 `references/thresholds.md`。

### 1.3 ARMS Pod CPU/内存

```bash
bash brain/tools/arms-pod-metrics.py <env>-<service>-<region> --window 1h
```

**注意**：`arms-pod-metrics.py` **目前只 us-prod 有 token**（见 brain/tools/README.md），其他集群会失败。如果失败，跳过此项并在汇报中标"❓ ARMS 无 token"。

### 1.4 RDS / PolarDB-X 实例指标

```bash
brain/tools/aliyun-rds-metrics.py <instance-id> --hours 1
```

工具自动按实例前缀分支：
- `rm-*` → 走 cms（CPU/MEM/IOPS/Conn/QPS/TPS/Sessions 全有）
- `pxc-*` → 走 polardbx `DescribeDBNodePerformance`（**只有 active_connection 可用**，CPU/MEM 给控制台链接）

**Region 自动推断**（不用传 `--region`）：
- `rm-0xi*` / `pxc-vgr*` → us-east-1
- `rm-2ze*` / `pxc-bjr*` → cn-beijing

从 SSOT § 2 拿对应环境的 DB host 第一段（如 `pxc-bjrghp1e9u97tk.polarx.rds.aliyuncs.com` → `pxc-bjrghp1e9u97tk`）。

### 1.5 Redis 实例指标

```bash
brain/tools/aliyun-redis-metrics.py <redis-instance-id> --hours 1
```

走 r-kvstore 原生 `DescribeHistoryMonitorValues` API（**兼容 standard / cluster / sharding 全架构**）。

**Region 自动推断**：`r-0xi*` → us-east-1，`r-2ze*` → cn-beijing。

从 SSOT § 3 "跨服务 Redis 实例对照" 拿对应环境的 Redis 实例 ID。

**优化**：多服务共享同一 Redis 时（如 chat / creation / user_center / mis / channels US test 都用 `r-0xin6dch2runb321pl`），子代理之间无法去重 — 主 agent 汇总时可注释"共享实例已在 X 服务下检查"避免重复展示。

### 1.6 Nacos 最近配置变更

```bash
brain/tools/nacos-recent-changes.py <cluster> <namespace-uuid> --hours 1
```

**Region 自动推断**：SSOT § 1.3 的 4 个 MSE cluster 自动映射（mse-6dff67e7/mse-ba8fadc7 → us-east-1，mse-829f85e2/mse-d32c23d2 → cn-beijing）。

从 SSOT § 1.3 拿 cluster + namespace。如返回 NoPermission，标"❓ 待运维授权 mse:ListConfigTrack"，不视为致命错误。

### 1.7 部署变更的 git commit 摘要

仅当步骤 1.1 检测到 1h 内**有真实 commit 变更**时执行（同 commit 重发跳过）：

```bash
cd <service-repo-path>
git fetch origin --quiet
git log <prev_commit_hash>..<curr_commit_hash> \
  --pretty=format:'  - %h | %an | %s' \
  --no-merges
```

`prev_commit_hash` / `curr_commit_hash` 从 image_tag 末尾抽，例如 `v_405_master_0723a890` → `0723a890`。

提取作者 + 主题，分组：
- **疑似 feature**：标题含 `feat:` / `feature:`
- **疑似 bugfix**：标题含 `fix:` / `bugfix:` / `hotfix:`
- **其他**

若是同 commit 重发，跳过 git log，但要**主动询问**最近一次操作者：`bash brain/tools/jenkins.sh log <job> <N>` 抓 `Started by user ...` 标注谁触发了重发。

## 第 2 步：多服务并行（subagent）

若服务数 ≥ 2，**每服务一个子代理**：

```
Agent({
  description: "健康检查 <service>",
  subagent_type: "general-purpose",
  prompt: "你需要对服务 <service>@<env> 做健康检查。

  执行 ~/.claude/skills/service-health/SKILL.md 的 7 项检查流程，使用以下工具：
  - brain/tools/jenkins.sh
  - brain/tools/sls-query.sh
  - brain/tools/arms-pod-metrics.py
  - brain/tools/aliyun-rds-metrics.py
  - brain/tools/aliyun-redis-metrics.py
  - brain/tools/nacos-recent-changes.py

  从 brain/knowledge/infra-env-ssot.md 查该服务的：
  - Jenkins job 名（§ 1.8）
  - SLS service 名（§ 2.X）
  - DB host + Redis 实例（§ 2.X 和 § 3）
  - Nacos cluster + namespace（§ 1.3 + § 2.X 的 dataId）

  阈值判定见 ~/.claude/skills/service-health/references/thresholds.md。

  按 thresholds.md 中的输出格式返回单服务报告，**500 行内**。如果发现 CRIT 级异常，把根因猜测 + 下一步建议放在最前面。"
})
```

**并行调度**：N 个子代理在一个 message 里发出，Claude 会自动并行。

## 第 3 步：汇报

### 单服务：详细模式

```
🟢 / 🟡 / 🔴 <service>@<env>
─────────────────────────────────────
Jenkins:    [近 1h 无部署 / 部署 build #N: <version> by <author>, <N-1>: <prev_version>]
SLS:        ERROR <n> / WARN <n> / Total <n> (基线 <baseline>)  [✓ / ⚠ / ✗]
ARMS:       CPU <%>, MEM <GiB>  [✓ / ⚠ / ✗]
DB:         CPU <%>, Conn <n/max>, QPS <n>  [✓ / ⚠ / ✗]
Redis:      CPU <%>, MEM <%>, Conn <n>, QPS <n>  [✓ / ⚠ / ✗]
Nacos:      <N changes> [近 1h 修改的 dataId]  / ❓ 无权限
Commits:    [若有部署]
  feat:
    - abc1234 | Alice | feat: 引入 X
  fix:
    - def5678 | Bob   | fix: Y 修复
```

### 多服务：总览表 + 异常展开

总览：

```
| 服务         | Env     | 总状态 | Jenkins | SLS  | ARMS | DB   | Redis | Nacos |
|--------------|---------|--------|---------|------|------|------|-------|-------|
| gateway      | us-test | 🟢     | -       | ✓    | ✓    | ✓    | ✓     | -     |
| chat         | us-test | 🟡     | ↑       | ⚠    | ✓    | ✓    | ✓     | -     |
| creation     | us-test | 🔴     | ↑       | ✗    | ✗    | ✓    | ✓     | 3     |
| ...          | ...     | ...    | ...     | ...  | ...  | ...  | ...   | ...   |
```

图例：`-` 无变更/正常  `↑` 近 1h 有部署  `✓` 健康  `⚠` 警告  `✗` 异常  `❓` 拉不到

异常详情展开（按服务）：仅展开 🟡/🔴 的服务，🟢 略过。

## SSOT 参考

**所有环境信息查这里**：`brain/knowledge/infra-env-ssot.md`

- § 1.3 Nacos cluster + namespace
- § 1.8 Jenkins job 命名
- § 2 各服务详情（Redis host / DB host / SLS logstore）
- § 3 跨服务 Redis 共享对照表

详细阈值判定 → `references/thresholds.md`

## 重要原则

1. **只读，不影响线上** — 严禁 PING/SELECT/INFO 直连，全部走 CloudMonitor API
2. **失败不致命** — 任何一项工具失败（权限缺失 / token 过期 / API timeout），跳过并标 ❓，**不阻塞其他项**
3. **不假装健康** — 拉不到数据时绝不写 "✓"，必须写 "❓"
4. **不查数据本身** — DB/Redis 只查实例性能指标，不连库执行 SQL
5. **基线漂移**：阈值是粗略的，发现明显异常 → 立刻给根因猜测 + 建议下一步（如 "近 1h 部署后 SLS ERROR 暴涨 5x，建议先 jenkins.sh log 看构建变更"）
