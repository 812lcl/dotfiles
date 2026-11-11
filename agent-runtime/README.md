# Agent runtime 兼容层

本目录提供可选的本机配置适配、受保护基准、显式分库上下文及跨客户端任务交接。工具复用现有客户端入口，不切换 provider、登录或原生记忆，不设置全局 PATH／BRAIN_DIR。

需要 Python 3.11+。以下命令从本目录执行；也可将 `runtime.py` 换成安装目录中的绝对路径。配置映射、运行报告、验收记录及回滚快照保存在私有 state 目录，不纳入源码仓库。

## 配置归属

| 内容 | 维护入口 | 工具职责 |
|---|---|---|
| 客户端订阅、模型和登录 | 各自客户端或用户选择的 provider 管理器 | 不自动替换 |
| MCP、共享 Skills 和生命周期入口 | Magpie Library 或明确的原生配置 | 按登记范围分发，不争抢同一条目的所有权 |
| Skill 正文与资源 | 各自 Git 权威来源或原安装器 | 复用源文件，不复制第二套业务正文 |
| 不同范围的 Brain | 各自独立仓库 | 显式选库，原文不复制进运行报告 |
| 客户端独有工具 | 各自客户端 | 保留，不要求所有客户端能力相同 |

本机映射在 `~/.local/state/agent-runtime/profiles.json`。`init` 只创建新映射，已存在时拒绝覆盖。凭据及实际 Brain 内容不纳入源码仓库。

Readwise 使用本机 `readwise` CLI，具体命令见对应 Skill。Skills 分发与模型请求链路分开管理，资源经过 Magpie 不代表模型也必须经过它。

## Skills 来源与加载

项目 Skills 可登记为 Magpie Library 的 `folder` 来源，正文留在权威目录，项目专属项的全局 `agents` 为空。删除的项目与 Skills 不从锁文件、旧计划或备份恢复。

Claude 使用独立的 `.claude/skills/` 目录，共享读取者使用 `.agents/skills/`；Magpie 按勾选管理逐项链接，两边指向同一份源码，不使用整目录互链。Claude 可以单独开关，共享目录中的同一入口则为所有读取者共同提供。OpenCode 还会兼容读取 Claude 目录，因此不能据此承诺 OpenCode 与 Claude 双向隔离。

worktree 的运行来源遵循该项目明确的源码策略，不自动合并或覆盖旧分支正文。生成的加载入口与 Git 源码目录分开，关闭后不要用安装脚本或手动软链补回。当前来源与勾选以 Magpie 中的登记为准。

全局 `~/.agents` 与 dotfiles 源码分离，Magpie 管理运行链接。第三方升级仍使用 `.agents/safe-skills-update.sh`，在源码仓执行 npx 项目模式，详见 `.agents/README.md`。系统 Skills、官方插件缓存及独立安装器维护的副本保留原生管理。

Magpie 0.1.3733 的资源库“仅在此设备关闭”只影响全局分发，不会撤销 Projects 分发。项目项需要使用 Projects 中的对应开关。

## Skills 自动分组

`skill_groups.py` 只维护 Library 的 `skillGroups` 显示元数据。来源标签取 `.pluginName-overrides.json`、`.skill-lock.json` 的 `pluginName`，以及私有 `skill-group-policy.json` 明确登记的本地来源。

```bash
python3 -B skill_groups.py          # 只预览
python3 -B skill_groups.py --apply  # 同步显示分组
python3 -B install_skill_groups.py  # 生成私有策略和用户 LaunchAgent
```

只遍历当前 `library.skills`；不会从锁文件或备份重新导入删除项。没有标签的项保留来源展示或既有手工分组。脚本不修改 agents、关闭状态、路由、MCP、hooks 或应用所有权，不运行模型、网络、npx 更新或 Library sync。

用户任务合并文件事件并定期补查。无变化不重写 Library，仅在实际变化时保存私有备份。写入前后核对输入指纹，发现并发变化则跳过，不恢复旧配置。该机制是乐观并发保护，不提供跨进程事务隔离。安装不会覆盖已有私有策略。

## Codex 基准

```bash
python3 -B runtime.py baseline capture --vault-root '<笔记库根目录>' --output '<state目录>/baseline.json'
python3 -B runtime.py baseline check --snapshot '<state目录>/baseline.json' --output '<state目录>/check.json'
```

快照记录类型、权限、软链目标和内容 hash，不保存原文。认证、原生记忆、会话、日志、数据库等动态数据不扫描，也不是写入目标。已固定版本的插件静态源可用重复的 `--extra-source` 纳入。

`config_policy` 的语义 hash 只忽略顶层 `model` 与 `model_reasoning_effort`，其余配置和文件元数据继续受保护。旧快照缺少分字段证据时做完整比较，不能据当前值推断旧配置。

源漂移与本工具写入分开判断。保留原始快照和差异，不自动恢复外部修改，也不通过重新拍摄基准掩盖差异。输出不得覆盖输入或受保护源。

## Claude MCP

```bash
python3 -B runtime.py claude-mcp plan
python3 -B runtime.py claude-mcp apply --backup-dir '<state目录>/backups'
python3 -B runtime.py claude-mcp rollback --manifest '<返回的manifest绝对路径>'
```

只处理 profile 中明确列出的、Magpie 已分配给 Claude 的服务。已有不同配置会报冲突。落盘前再次核对并私有备份；回退只移除本次新增且仍匹配 hash 的项，保留其他配置和后续修改。

`launch_overrides` 仅适配已选 stdio 服务的启动命令和参数，并校验入口 hash，不覆盖 provider、凭据、远程地址或其他客户端。缓存缺失或版本改变时明确失败，不静默安装或回退。

## Brain 范围

```bash
python3 -B runtime.py brain --scope personal verify
python3 -B runtime.py brain --scope work verify
python3 -B runtime.py brain --scope work --metadata-only read '<来源相对路径>' --sha256 '<已核验hash>'
```

调用已有 `brain-context` 并传入明确根目录、scope 和 profile。不调用会自动同步的 Brain CLI；范围冲突、缺 profile、来源 hash 不符时失败，不回退全局库。`--metadata-only` 不输出记忆正文。长期内容写入遵循目标库自己的约定与授权。

## 任务交接

```bash
python3 -B runtime.py handoff create --file '<state目录>/task.json' --root '<项目绝对路径>' --owner codex --scope work --goal '<目标>' --next-step '<下一步>' --protect '<已有文件相对路径>'
python3 -B runtime.py handoff release --file '<state目录>/task.json' --owner codex --revision 1
python3 -B runtime.py handoff verify --file '<state目录>/task.json'
python3 -B runtime.py handoff claim --file '<state目录>/task.json' --owner claude --revision 2
```

接收者先 verify，再按实际 revision claim；完成后 release。可通过 `--verification-json` 附带验证记录，但接收者仍需独立检查代码、测试和保护文件。

交接记录包含 Git 根、common-dir、HEAD、分支、diff hash、文件指纹、owner/revision、进程检查状态及下一步，不保存代码原文。记录必须位于工作区外的显式 state 目录。

发现漂移时拒绝接管，不自动 stash、reset、提交或切分支。重要的 ignored 文件须显式 `--protect`；未核验的后台进程不能写成已确认安全。并行修改使用独立 worktree，不合并客户端会话数据库。

## 客户端与生命周期适配

- Claude 探针加载真实配置，但只对探针进程禁用 hooks、自动记忆和会话持久化，避免验证触发同步。
- Cursor 使用明确的 `cursor-agent` 入口；通用 `agent` 命令可能属于其他客户端。规则模板安装前核对现有文件，不覆盖不同内容。
- Grok 使用明确的 `grok` 入口。静态 inspect 只能证明发现配置，不能证明插件或工具在会话中可用。
- OpenCode V2 使用原生 API 创建受限验证会话；按 session location 选库，不使用服务进程 cwd 代替实际位置。会话权限不写回全局配置。

Magpie 可按原生事件分发 `brain_hooks.py portable <event>`。工作区到 scope、Brain 根和 profile 的映射保存在私有配置；未知或混合范围跳过，不猜测目录或回退默认库。脚本不自动编写 note 或 memo。

使用 `brain_hooks.materialized_by = magpie.library` 标记分发归属后，旧安装器拒绝重复写入，恢复入口为 `magpie library sync`。首次移交前备份并精确撤回旧入口，不伪造 applied/ownership。需要信任的 hook 按当前内容重新核验，不关闭客户端信任检查。

客户端不支持的事件、返回协议或插件条件不能通过删字段伪装成兼容。继承入口与原生入口须去重；长驻进程加载行为需要另行验证，不自动重启用户服务。

## 验证与证据边界

```bash
python3 -B -m unittest discover -s . -p 'test_*.py' -v
```

验证区分源码审计、配置发现、真实工具调用、任务交接、生命周期事件及远端同步。初始化列表、模型自述、事件被调用或 API 返回空正文，均不能替代对应阶段的验收。

探针只保留工具名称、输入／结果 hash、状态、费用估算与步骤元数据，不保存原始提示、工具正文、thinking 或错误原文。预算是客户端估算，不是账单硬上限。具体接入、排障和验收经过仅保存在私有运行记录中。

测试进程可设置 `AGENT_RUNTIME_HOOK_AUDIT` 输出事件、scope、状态及 hash；正常启动无需设置。结束适配采用 best-effort 后台同步，调用成功不代表远端同步成功。
