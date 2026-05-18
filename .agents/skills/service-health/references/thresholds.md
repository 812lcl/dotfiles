# 健康检查阈值判定

> 这些阈值是经验值，**仅作触发关注的信号**，不是硬性 SLA。
> 发现异常时优先看趋势（突变 / 持续）而不是绝对值。

## 1. 部署判定（核心改版）

部署成败**不以 Jenkins 状态为唯一标准**。综合 SLS image_name 分布 + ARMS pod image + Jenkins 状态：

| SLS image_name | ARMS RS | Jenkins | 结论符号 | 说明 |
|---|---|---|---|---|
| 新 tag ≥ 50% | 新 RS Running | SUCCESS | `↑✓` | 真部署成功 |
| 新 tag ≥ 50% | 新 RS Running | FAILURE | `↑✗⚠` | 部署成功但 Jenkins 脚本误报（gateway us-prod 案例） |
| 新旧混跑 | 双 RS 共存 < 30min | SUCCESS | `↑▷` | 滚动进行中（chat us-prod 案例） |
| 仅旧 tag | 仅旧 RS | SUCCESS（同 commit） | `↑↻` | 容器未真更新 / 同 commit 重发（chat cn-prod 案例） |
| 仅旧 tag | 仅旧 RS | 1h 无触发 | `—` | 部署未发生（用户说部署了但 Jenkins 没动 — channels cn-prod 案例） |
| 仅旧 tag | 仅旧 RS | FAILURE | `↑✗` | 部署真失败，已回滚 |
| 新 tag < 30% | 新旧混跑 > 30min | 任意 | `↑⏸` | rollout 卡住（readiness 不过 / preStop hook 异常） |

**关键纪律**：用户口头说"刚部署完"也要验证。SLS image_name 全是旧的时，必须主动反馈"运行时未见新版本"。

## 2. SLS 日志

按服务**每分钟**基线（取过去 24h P50，或参考 `--hours 24 --count` 除以 1440）：

| 指标 | 健康 ✓ | 警告 ⚠ | 异常 ✗ |
|---|---|---|---|
| level=error / min | < 5 | 5-30 | > 30 或 突增 > 5× 基线 |
| WARN / min | < 30 | 30-100 | > 100 |
| Total 日志量 | 与基线 ±30% | ±50% | 突降 > 80%（疑似服务挂）或 突增 > 5× |

**关键字误命中复查（必做）**：
- 全文 query `ERROR` 的条数 / 总日志 > 10% → 用 `level=error` 复查
- 如果 `level=error` 远少于 `ERROR` 关键字数 → 报告中明确标"⚠ 全文 ERROR 含 INFO 字段误中"，按 `level=error` 判定

**特别注意**：日志量**突然降到 0** 比"全是 ERROR"更可疑 — 可能 pod 挂了或 SLS 采集断了。

## 3. SLS ERROR / WARN Pattern 分析（新增）

抽 30-50 条样本，**子代理在 prompt 内手工归类**（不依赖工具扩展）：

| 步骤 | 操作 |
|---|---|
| 抽样 | `sls-query.sh ... 'level=error' --hours 1 --lines 50`；若空回退 `'ERROR' --lines 50` |
| 归类维度 | message/msg/content 前 60-80 字符，或 stacktrace 顶端类名 |
| 合并 | 前缀相同 / 关键 token 相同视为同一 pattern |
| 输出 | top 3-5 pattern：占比 + 一条代表性样例（截断到 200 字符） |
| 根因猜测 | 业务噪声 / 系统故障 / 配置错误 / 依赖失效 之一 |

**根因猜测启发**：
- "Data not exist" / "user not found" / "permission denied" → 业务噪声
- "connection refused" / "timeout" / "EOF" → 依赖失效
- "InvalidAccessKeyId" / "TokenExpired" / "Auth failed" → 凭证 / 配置错误
- "OutOfMemory" / "panic" / "stack overflow" → 系统故障

## 4. 部署前后对比（新增）

仅当 § 1 判定为 `↑✓` / `↑▷` / `↑↻` 时做。取部署时刻 T（从 SLS image_name 首次出现时刻取，比 Jenkins 时间准）。

| 维度 | 前 30min | 后 30min | 判定 |
|---|---|---|---|
| level=error/min | A | B | 持平 ±20% ✓ / +50%-200% ⚠ / > 200% ✗ |
| 新增 ERROR pattern | - | 部署后才出现的 pattern | 有 → 强回归证据，立刻列出来 |
| 新 RS CPU 均值 | 旧 RS A | 新 RS B | +30% ⚠ / +60% ✗ |
| 新 RS MEM 均值 | 旧 RS A | 新 RS B | +30% ⚠ / +60% ✗（可能内存泄漏） |
| DB QPS | A | B | 与基线 ±50% ✓ / ±2× ⚠ / >5× ✗ |
| Redis QPS | A | B | ±50% ✓ / ±3× ⚠ / >10× ✗（可能缓存击穿） |

## 5. ARMS Pod 指标

| 指标 | 健康 ✓ | 警告 ⚠ | 异常 ✗ |
|---|---|---|---|
| CPU 使用率 | < 60% | 60-80% | > 80% 持续 >5min |
| 内存使用率 | < 70% | 70-85% | > 85% 或接近 limit |
| 内存与 limit 比 | < 0.7 | 0.7-0.85 | > 0.85（OOM 风险）|

**按 RS 分组列出**：
- 每个 RS 标 image_tag、pod 数、CPU/MEM 范围、最长/最短 uptime
- 异常 pod（偏离同 RS 均值 2σ）单独列

**注意**：`arms-pod-metrics.py` 当前**只 us-prod 有 token**，其他集群标 `❓`。

## 6. RDS / PolarDB-X

| 指标 | 健康 ✓ | 警告 ⚠ | 异常 ✗ |
|---|---|---|---|
| CPU % | < 50% | 50-70% | > 70% |
| 内存 % | < 75% | 75-85% | > 85% |
| IOPS % | < 60% | 60-80% | > 80% |
| Conn % | < 50% | 50-70% | > 70% |
| QPS 突增 | 与基线 ±50% | ±2× | > 5× |

**PolarDB-X 注意**：aliyun CLI 只暴露 active_connection；CPU/MEM/IOPS 走控制台。CN（计算节点）和 DN（数据节点）的连接数都看 — CN 高 = SQL 解析压力大，DN 高 = 存储 IO 压力大。

## 7. Redis / Tair

| 指标 | 健康 ✓ | 警告 ⚠ | 异常 ✗ |
|---|---|---|---|
| CPU % | < 50% | 50-70% | > 70% |
| 内存 % | < 70% | 70-85% | > 85%（接近 OOM evict）|
| 连接数 % | < 50% | 50-70% | > 70% |
| QPS 突增 | 与基线 ±50% | ±3× | > 10% |
| Failed Cmds | < 1/min | 1-10/min | > 10/min |

**Redis 共享实例（多服务）**：CPU/QPS 飙高时不能光从一个服务断定根因，需要看哪个 key/db 在打。临时跳过 — 把告警写出来即可，根因排查另起。

## 8. ERROR 根因深挖（条件触发，§ 1.8）

### 触发条件（满足任一就做）

| 条件 | 含义 |
|---|---|
| Top ERROR pattern 占比 > 50% | 主导 pattern 不是业务噪声，值得查代码 |
| Top ERROR pattern 部署窗口内 +100% 突增 | 部署引入或放大了问题 |
| 部署判定 `↑✗` | 部署真失败，必须查失败原因 |
| 用户明确询问"是谁引入的" / "怎么修" / "修复建议" | 用户在 prompt 里直接要这个能力 |

不触发就跳过，避免无脑 git blame 浪费 token。

### 根因分类与修复建议范式

| 根因类型 | 关键字 | 修复建议范式 |
|---|---|---|
| **凭证 / 配置错误** | `InvalidAccessKeyId` / `TokenExpired` / `Auth failed` / `Permission denied` | **不是代码 bug，不要建议 revert**。给出：1) 谁负责重置凭证；2) 改哪个配置（Nacos dataId / toml key）；3) 是否需要重启 |
| **代码 bug** | `nil pointer` / `NPE` / `panic` / `Unmarshal failed` / `index out of range` / 逻辑错误 | **必须给具体代码改动方向**。给出：1) `git blame` 显示的 commit `<hash>` by `<author>`；2) 该 commit 是否近期改动（看日期）；3) 具体改动建议（加 nil 检查 / 改算法 / revert） |
| **依赖失效** | `connection refused` / `timeout` / `EOF` / `DNS resolution failed` / `503` | **代码侧通常不需要改**。给出：1) git blame 显示代码是历史代码，问题在上游；2) 联系上游 `<service>` owner；3) 本服务侧补强（超时 / 重试 / 熔断） |
| **业务噪声** | `Data not exist` / `user not found` / `not authorized` (业务级 401) | **不要 git blame**。提示这是正常业务现象，可调日志级别 / 改采样 |

### 输出格式

在 Top ERROR Pattern 段下面新增子段：

```
根因深挖 (满足触发条件):
  Pattern: <pattern 描述>
  代码位置: <file>:<line>
  当前代码片段:
    <line-2>: ...
    <line-1>: ...
    <line>  : ...  ← 报错行
    <line+1>: ...
  Git blame:
    commit <hash> | <author> | <date> | <subject>
    [可选] 该行最近修改: <date>，距今 <N> 天
  根因类型: <凭证/配置错误 | 代码 bug | 依赖失效 | 业务噪声>
  修复建议:
    1. <第一步具体动作>
    2. <第二步具体动作>
    3. <第三步具体动作（可选）>
```

### 重要纪律

- 不要每次都做 — 触发条件不满足跳过
- git blame 只看一行/一段，不要 blame 整个文件
- 不要试图修代码 — 健康检查是只读流程，只给建议
- commit author 是线索不是判决 — 旧代码可能不是当前作者的问题

### 范例（chat@cn-prod OSS AK 失效）

```
根因深挖:
  Pattern: [HIGH][Business]UploadToOSS failed: InvalidAccessKeyId (80% 占比)
  代码位置: chat/lib/oss/oss.go:137
  当前代码片段:
    135: client, err := oss.New(endpoint, accessKey, accessSecret)
    136: bucket, err := client.Bucket(bucketName)
    137: err = bucket.PutObject(objectKey, reader)  ← 报错行
    138: if err != nil {
    139:     logger.Errorf("[HIGH][Business]UploadToOSS failed: %v", err)
  Git blame:
    commit a7b8c9d | alice@x.com | 2025-09-12 | feat(oss): add archive upload
    该行最近修改: 8 个月前，与本次故障无时间相关性
  根因类型: 凭证/配置错误
  修复建议:
    1. **不是代码问题**，不要 revert commit a7b8c9d
    2. 联系运维确认 OSS AccessKey `LTAI5tDR6...` 被禁原因（泄漏 / 主动轮换 / 触发风控？）
    3. 拿到新 AK 后，更新 Nacos `chat-oss-config` 中的 `access_key_id` / `access_key_secret`
       （或 chat/conf/prod.toml 的 [oss] 段，看实际配置加载路径）
    4. 不需要重启 — chat 走 Nacos 热加载（如果走 toml 则需重启 pod）
```

## 9. 综合状态判定

| 整体颜色 | 触发条件 |
|---|---|
| 🟢 | 所有项 ✓ 或仅有 `-` / `❓`；部署判定 `↑✓` |
| 🟡 | 任一项 ⚠，**或** 部署判定 `↑▷` / `↑↻` / `↑✗⚠`，**或** SLS pattern 出现新增但占比 < 30% |
| 🔴 | 任一项 ✗，**或** 部署判定 `↑✗` / `↑⏸`，**或** Total 日志量突降 > 80%，**或** ERROR/min > 200% 基线 |

## 输出格式范例

### 单服务（部署判定异常示例）

```
🔴 chat@cn-prod  (近 1h)
─────────────────────────────────────
部署判定:    ↑↻ 同 commit 重发，容器未真更新
            理由: SLS image_name 全为 v_1834_master_f0d5f472（旧版），
                  Jenkins #10 报 SUCCESS 但 image_tag 与 #9 同 commit
            触发: build #10 by chunlei.liu at 09:45:55

SLS 计数:    ERROR 707,799 / WARN 0 / Total 18.49M
            ⚠ 全文 ERROR 含字段误中，真实 level=error: 711,786

Top ERROR Pattern:
  1. [79%] OSS InvalidAccessKeyId: lib/oss/oss.go:137 GetInternalContent failed
     样例: AK=LTAI5tDR6dMKXa4Vcba8QZKH (disabled), bucket=home-recommend...
     根因: 凭证失效 — OSS AccessKey 被禁用
  2. [12%] skynet api error 7021 check user token failed
     样例: user 0 token expired at /chat/history_v2
     根因: 业务噪声 — 用户 token 失效
  3. [...]

Top WARN Pattern:
  1. [...]

部署前后对比 (T = 09:45:55):
  level=error/min: 前 12,300 → 后 11,797 (持平 -4%)
  新增 pattern: 无（OSS AK 错误从部署前就有）
  → 部署未引入新问题，但既存问题未解决

ARMS Pod:      ❓ cn-prod 集群无 token

DB:            pxc-bjrjm8im745cdc CN 节点 active_conn avg 13-21, max ≤30 ✓
Redis (main):  r-2zekotjcibhtv0hnr4 CPU 5.13%, MEM 12.88 GiB, QPS 5667 ✓
Redis (queue): r-2zexikb6b3jtww6c7y CPU 0.38%, MEM 5.57 GiB, QPS 248 ✓

────────────────────────────────────────────────────────────
⚠ 根因: OSS AccessKey LTAI5tDR6dMKXa4Vcba8QZKH 被禁用
   chat/lib/oss/oss.go:137 每次请求 /chat/history_v2 都失败
   本次部署 #10 是同 commit 重发，未引入新代码，无法解决问题

✗ 建议:
   1. 立刻找运维确认 AK 被禁原因 + 更新 Nacos 配置
   2. bash brain/tools/jenkins.sh log deploy-chat-cn-prod 10 | grep "Started by"
   3. 验证 pod 是否拿到新配置（如果走 Nacos 热加载）
```

### 多服务总览（4 服务 × 2 环境示例）

```
近 1h 健康检查 (us-prod + cn-prod)
==========================================

| 服务      | Env      | 状态 | 部署判定 | SLS Pattern      | ARMS | DB   | Redis |
|-----------|----------|------|----------|------------------|------|------|-------|
| gateway   | us-prod  | 🟡   | ↑✗⚠      | ✓ 仅 noise       | ✓    | ✓    | ✓     |
| gateway   | cn-prod  | 🟢   | ↑✓       | ⚠ 部署后 ↑16%    | ❓   | ✓    | ✓     |
| chat      | us-prod  | 🟡   | ↑▷ 滚动中| ⚠ 业务噪声 48k    | ✓    | ✓    | ✓     |
| chat      | cn-prod  | 🔴   | ↑↻ 重发  | ✗ OSS AK 失效     | ❓   | ✓    | ✓     |
| creation  | us-prod  | 🟢   | ↑✓       | ✓ 基线           | ✓    | ✓    | ✓     |
| creation  | cn-prod  | 🟢   | ↑✓       | ✓ 业务噪声        | ❓   | ✓    | ✓     |
| channels  | us-prod  | 🟢   | ↑✓       | ✓ 关键字误中      | ✓    | ✓    | ✓     |
| channels  | cn-prod  | 🟡   | —        | ✓                | ❓   | ✓    | ✓     |

异常详情按服务展开（仅 🟡/🔴）：
🔴 chat@cn-prod: <详细同上>
🟡 chat@us-prod: <...>
🟡 gateway@us-prod: <Jenkins 误报 + 新 RS 实际接管>
🟡 channels@cn-prod: <用户说部署但 Jenkins 1h 无触发 — 请确认>
```

## 备注

- 阈值是**起点**，发现异常后按用户经验调
- 若某服务在某环境的基线已知（如 chat us-prod ERROR 基线 100），在此文件添加例外规则
- 子代理无状态，每次检查重新算基线
