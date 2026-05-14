# 健康检查阈值判定

> 这些阈值是经验值，**仅作触发关注的信号**，不是硬性 SLA。
> 发现异常时优先看趋势（突变 / 持续）而不是绝对值。

## 1. Jenkins 部署

| 状态 | 判定 |
|---|---|
| `-` 无变更 | 最近 1h 内没有 deploy job 触发 |
| `↑` 部署中 | `BUILDING` 状态，或 `now - timestamp < duration` |
| `↑✓` 刚完成 | 1h 内有 SUCCESS 部署，前后版本拉到 |
| `↑↻` 同 commit 重发 | 1h 内 SUCCESS 部署但 image_tag 的 commit hash 跟前一次相同（如 `v_404_master_0723a890` → `v_405_master_0723a890`）— **可疑信号**，通常是手动重启/补救/回滚，需要主动询问操作者 |
| `↑✗` 失败 | 1h 内有 FAILURE / ABORTED — **直接红，优先告警** |
| `↑build✗` build 失败 | `build-<service>` job 失败但未 deploy — **黄**，下次部署会卡 |

## 2. SLS 日志

按服务**每分钟**基线计算（取过去 24h P50 当基线，简化版本可写死）：

| 指标 | 健康 ✓ | 警告 ⚠ | 异常 ✗ |
|---|---|---|---|
| ERROR / min | < 5 | 5-30 | > 30 或 突增 > 5× 基线 |
| WARN / min | < 30 | 30-100 | > 100 |
| Total 日志量 | 与基线 ±30% | ±50% | 突降 > 80%（疑似服务挂）或 突增 > 5× |

**特别注意**：日志量**突然降到 0** 比"全是 ERROR"更可疑 — 可能 pod 挂了或 SLS 采集断了。

## 3. ARMS Pod 指标

| 指标 | 健康 ✓ | 警告 ⚠ | 异常 ✗ |
|---|---|---|---|
| CPU 使用率 | < 60% | 60-80% | > 80% 持续 >5min |
| 内存使用率 | < 70% | 70-85% | > 85% 或接近 limit |
| 内存与 limit 比 | < 0.7 | 0.7-0.85 | > 0.85（OOM 风险）|

**注意**：`arms-pod-metrics.py` 当前**只有 us-prod 集群 token**（见 brain/tools/README.md），其他集群会返回 token 错误。在这些环境下标 `❓`，不视为异常。

## 4. RDS / PolarDB-X

| 指标 | 健康 ✓ | 警告 ⚠ | 异常 ✗ |
|---|---|---|---|
| CPU % | < 50% | 50-70% | > 70% |
| 内存 % | < 75% | 75-85% | > 85% |
| IOPS % | < 60% | 60-80% | > 80% |
| Conn % | < 50% | 50-70% | > 70% |
| QPS 突增 | 与基线 ±50% | ±2× | > 5× |

**PolarDB-X 注意**：分别看 CN（计算节点）和 DN（数据节点）的 CPU；CN 高 = SQL 解析压力大，DN 高 = 存储 IO 压力大。

## 5. Redis / Tair

| 指标 | 健康 ✓ | 警告 ⚠ | 异常 ✗ |
|---|---|---|---|
| CPU % | < 50% | 50-70% | > 70% |
| 内存 % | < 70% | 70-85% | > 85%（接近 OOM evict）|
| 连接数 % | < 50% | 50-70% | > 70% |
| QPS 突增 | 与基线 ±50% | ±3× | > 10× |
| Failed Cmds | < 1/min | 1-10/min | > 10/min |

**Redis 共享实例（多服务）**：CPU/QPS 飙高时不能光从一个服务断定根因，需要看哪个 key/db 在打。临时跳过 — 把告警写出来即可，根因排查另起。

## 6. Nacos 配置变更

| 状态 | 含义 |
|---|---|
| `-` 无变更 | 近 1h 没有 dataId 修改 |
| `<N>` N 条变更 | 列出 dataId / 操作类型 / 修改人 IP / 时间，让用户判断是否合理 |
| `❓` 权限不足 | `mse:ListConfigTrack` 未授权，标 ❓ 不阻塞 |

**结合 SLS 异常**：服务 SLS ERROR 突增 + Nacos 同时有 dataId 变更 = 强相关，**汇报时把这两条放在一起**。

## 7. 综合状态判定

| 整体颜色 | 触发条件 |
|---|---|
| 🟢 | 所有项 ✓ 或仅有 `-` / `❓` |
| 🟡 | 任一项 ⚠，**或** Jenkins `↑↻` 同 commit 重发，**或** `build-<service>` build 失败 |
| 🔴 | 任一项 ✗，**或** Jenkins 部署失败 (`↑✗`)，**或** Total 日志量突降 > 80% |

## 输出格式范例

### 单服务（同 commit 重发示例）

```
🟡 gateway@us-test  (1h)
─────────────────────────────────────
Jenkins:    ↑↻ 同 commit 重发（21min 前）
  #289  18:09:26 SUCCESS  v_405_master_0723a890
  #288  17:57:22 SUCCESS  v_404_master_0723a890   ← 同 commit (0723a890)
  → 可疑：通常是手动重启/补救/回滚，需要问操作者
  → 建议: bash brain/tools/jenkins.sh log deploy-agent-gateway-us-test 289 | grep "Started by"
SLS:        ERROR 167 / WARN 0 / Total 244k (last 1h) ✓
DB:         CPU 0.7%, MEM 35%, QPS 22  ✓
Redis:      CPU 0.3%, MEM 170MiB, QPS 34, Conn 33  ✓
ARMS:       ❓ test-us 集群无 token
Nacos:      ❓ 待运维授权 mse:ListConfigTrack
```

### 单服务（异常示例）

```
🟡 chat@us-test  (1.5h)
─────────────────────────────────────
Jenkins:    近 1h 无部署
SLS:        ERROR 87 (⚠ 基线 12)  WARN 245  Total 14.2k
ARMS:       CPU 42%  MEM 1.8GiB
DB:         CPU 35%  Conn 23%  QPS 850
Redis:      CPU 12%  MEM 7.8%  Conn 99
Nacos:      ❓ 待运维授权

⚠ 根因猜测: ERROR 量是基线 7x，集中在 "redis timeout" 关键词
建议: bash brain/tools/sls-query.sh chat test 'redis AND timeout' --hours 1 --lines 50
```

### 多服务汇总（5 服务示例）

```
近 1h 健康检查 (us-test)
==========================================

| 服务      | 状态 | Jenkins | SLS | ARMS | DB  | Redis | Nacos |
|-----------|------|---------|-----|------|-----|-------|-------|
| gateway   | 🟢   | -       | ✓   | ❓   | ✓   | ✓     | ❓    |
| chat      | 🟡   | -       | ⚠   | ❓   | ✓   | ✓     | ❓    |
| creation  | 🔴   | ↑✗      | ✗   | ❓   | ⚠   | ✓     | 3     |
| channels  | 🟢   | -       | ✓   | ❓   | ✓   | ✓     | ❓    |
| oh-my-agent| 🟢   | -       | ✓   | ❓   | -   | ✓     | ❓    |

异常详情:
─────────────────────────────────────
🔴 creation@us-test
  Jenkins: build #142 FAILED at 18:23 (build_version=feat/x-by-alice)
           前一次 #141 SUCCESS (build_version=master)
  SLS:     ERROR 230 (基线 8)
  Nacos:   3 changes
    18:21  Update  document-config  creation  10.42.x.x
    18:22  Update  ppt-config       creation  10.42.x.x
    18:23  Update  home-config      creation  10.42.x.x

  ⚠ 强相关: Nacos 三次连续修改 + Jenkins 部署失败 + ERROR 暴增 = 配置变更引起回滚需求
  建议: 1) jenkins.sh log deploy-doccie-creation-us-test 查失败原因
        2) 与 alice 确认是否需要回滚 Nacos 三条变更

🟡 chat@us-test
  SLS:     ERROR 87 (基线 12)，关键词 "redis timeout"
  建议: sls-query.sh chat test 'redis AND timeout' --hours 1
```

## 备注

- 阈值是**起点**，发现异常后按用户经验调；本文件可随时修改
- 若某服务在某环境的基线已知（如 chat us-prod ERROR 基线 100），在此文件添加例外规则
- 子代理无状态，每次检查重新算基线（简化版可用固定阈值，复杂版从 SLS query 拉 24h P50）
