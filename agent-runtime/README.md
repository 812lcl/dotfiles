# Agent runtime 兼容层

本目录是可选的本机适配与交接工具。Codex 是只读基准，继续使用原启动入口；工具不修改 Codex 的配置、hooks、MCP、共享 Skills、登录或原生记忆，不设置全局 PATH／BRAIN_DIR。

需要 Python 3.11+。本机验收使用 `/opt/homebrew/opt/python@3.14/bin/python3.14`，不依赖 shell 中可能不同的 `python3`。下面命令从本目录执行；可将 `runtime.py` 换成安装目录中的绝对路径。

## 配置归属

| 内容 | 维护入口 | 本工具的职责 |
|---|---|---|
| Codex／Skywork／Cursor／Grok 订阅 | 各自客户端 | 不改登录或 provider |
| 其他客户端 provider | Magpie | 不改模型或鉴权 |
| 分配给 Claude 的 MCP | Magpie library | 仅将选中的定义落到 Claude 用户配置；必要的本机启动差异使用 Claude 专用适配 |
| 共同规则和 Skills | 现有权威文件 | 只读复用，不为兼容其他客户端修改 Codex 消费的源 |
| 个人／工作 Brain | 各自独立仓库 | 显式范围的只读适配，原文不复制到运行报告 |
| 客户端独有能力 | 各自客户端 | 单独登记，不要求补齐，例如 Codex computer use |
| CC Switch | 已停用 | 不读取其旧状态作为配置权威，不参与同步 |

Readwise 统一使用本机 `readwise` CLI，命令与参数见共享 `readwise-cli` Skill；不再纳入 MCP 下发清单。此选择同时覆盖 Readwise Highlights 和 Reader，客户端当前会话中残留的 Readwise MCP 工具不再使用。

本机映射在 `~/.local/state/agent-runtime/profiles.json`。运行报告、快照与精确回退记录位于该私有 state 目录，源码仓库不包含凭据或实际 Brain 内容。`init` 只创建新映射，已存在时拒绝覆盖。

## Codex 基准

```bash
python3.14 -B runtime.py baseline capture --vault-root '<实际 Vault 根>' --output '<state目录>/baseline.json'
python3.14 -B runtime.py baseline check --snapshot '<state目录>/baseline.json' --output '<state目录>/check.json'
```

快照记录类型、权限、软链目标和内容 hash，不保存文件原文。认证、native memories、会话、日志、数据库等动态运行数据不扫描，也不是写入目标。已确定版本的插件静态源可通过重复 `--extra-source` 单独纳入。

用户会在日常使用中切换 Codex 默认模型与推理等级。新建快照同时记录 `config_policy` 的只读语义 hash：只忽略顶层 `model` 和 `model_reasoning_effort`，其余配置及文件元数据继续受保护。检查保留原始 hash 变化，再判断是否只是允许的选择器／格式变化；不排除整份 config.toml。旧快照缺少分字段证据时继续做完整比较，不据当前值推断旧配置。

源漂移与本任务写入是不同判断。保留原始快照和完整差异；外部插件缓存变化单独报告，不自动恢复，也不重新拍摄基准掩盖差异。若派生核心快照，保留原快照 hash、固定范围和排除原因。输出禁止覆盖输入快照或任何受保护源。

## Claude MCP

```bash
python3.14 -B runtime.py claude-mcp plan
python3.14 -B runtime.py claude-mcp apply --backup-dir '<state目录>/backups'
python3.14 -B runtime.py claude-mcp rollback --manifest '<本次返回的manifest绝对路径>'
```

只处理 profile 中明确列出的、Magpie 已分配给 Claude 的服务。已有不同配置会报冲突，不能直接覆盖。落盘前再次核对文件，备份为 `0600`；回退仅移除本次新增且仍匹配安装 hash 的项，保留其他配置及后续修改。私有备份不可提交到 Git。

可选 `launch_overrides` 只适配已选 stdio 服务的本机启动命令／参数，并校验入口 hash；不覆盖 provider、凭据、远程地址或其他客户端。缓存缺失或版本内容变化时明确失败，不静默安装、更新或回退。

## Brain

```bash
python3.14 -B runtime.py brain --scope personal verify
python3.14 -B runtime.py brain --scope work verify
python3.14 -B runtime.py brain --scope work --metadata-only read '<来源相对路径>' --sha256 '<已核验hash>'
```

调用现有 `brain-context`，完整传入 Vault 根、scope、Brain 根和 work profile。它不调用 Brain CLI，不触发 sync。scope/root 冲突、缺 work profile、来源 hash 不符均失败；继承的旧 `BRAIN_DIR` 不能改向。`--metadata-only` 不向接收 agent 输出记忆正文。写入长期记忆继续遵循原有范围与授权规则，不由本工具自动执行。

## 工作区交接

```bash
python3.14 -B runtime.py handoff create --file '<state目录>/task.json' --root '<工作区绝对路径>' --owner codex --scope work --goal '<目标与范围>' --next-step '<下一步>' --protect '<用户已有文件相对路径>'
python3.14 -B runtime.py handoff release --file '<state目录>/task.json' --owner codex --revision 1
python3.14 -B runtime.py handoff verify --file '<state目录>/task.json'
python3.14 -B runtime.py handoff claim --file '<state目录>/task.json' --owner claude --revision 2
```

完成后由当前 owner 用实际 revision 再 `release`，下一位检查后 `claim`。可用 `--verification-json` 附带验证命令与结果记录；接收者仍需核对证据，不能把 agent 的自述当成独立验证。

| 步骤 | owner / revision | 实际动作 |
|---|---|---|
| 创建 | Codex / 1 | 记录目标、下一步、Git 现场和用户保护文件指纹 |
| 释放 | Codex / 2，released | 再拍现场并允许接管 |
| 接收 | 接收 agent / 3，owned | verify 无漂移后 claim，重新读代码和所需 Brain 来源 |
| 交回 | 接收 agent / 4，released | 完成修改、运行验证、写下一步并 release |
| 验收 | Codex / 5，owned | 独立核查代码、测试和保护文件后 claim |

记录包含目标、约束、范围、Git 根/common-dir、HEAD、分支、staged／unstaged diff hash、dirty／untracked 文件指纹、保护文件、进程检查状态、下一步、owner 和 revision。代码原文不放进交接 JSON，新 agent 重新读取现场。状态文件必须位于工作区外，位于显式 state 目录内。

- 单一写入者与状态文件锁是协作约定，不阻止其他编辑器或进程改文件。发现漂移时拒绝接管，不自动 stash、reset、提交或切分支。
- 用户已有文件用重复 `--protect` 明确登记。ignored 文件不会自动枚举，重要的 ignored 内容必须显式保护。
- `processes` 默认是未核验；交接者需单独核对后台测试、服务和其他运行任务。
- 本期不接续冲突或已修改 submodule，不合并客户端原生会话数据库。并行修改使用独立工作区。

## 验证与证据边界

```bash
python3.14 -B -m unittest discover -s . -p 'test_*.py' -v
```

`probe.py` 启动正常 Claude CLI 并加载真实用户／项目配置，但单次进程禁用 hooks、自动记忆和会话持久化，避免测试触发 Brain 同步。工具、轮次、估算预算和进程超时单独限制。预算是客户端估算，不是 Magpie 账单的硬上限。

证据区分已配置、运行时发现、实际调用和完成接力。默认仅保留工具名称、输入／结果 hash、成功状态及费用估算，不保存原始提示、工具正文或错误原文。只有无隐私验收案例使用限长最终回答。生命周期 hook 通过独立 fixture 测试核验，不能以禁用 hooks 的探针声称真实自动同步已验收。

Claude 的 MCP 可按需加载，初始化的 `pending` 不代表调用失败。受限探针需要保留 `ToolSearch`，先发现目标工具再调用；只看到模型最终回答也不能代替 `tool_use`／`tool_result` 的成功证据。

## Cursor

Cursor 使用自己的订阅、登录、模型选择及 MCP，不经 Magpie。启动时使用明确的 `cursor-agent` 入口；本机通用 `agent` 软链可能属于 Grok Build，不能靠命令名推断客户端。

Cursor 原生读取项目 `AGENTS.md` 与 `.agents/skills/`。`cursor-runtime.mdc.template` 只为两个实际工作区补充显式 Brain 和交接入口，分别替换 workspace、scope、runtime 后安装到 `.cursor/rules/agent-runtime.mdc`。已有不同内容先审查，不能直接覆盖。此规则仅供 Cursor 消费，不修改 Codex 的源。

`cursor_probe.run_cursor` 验证真实本机 CLI，记录工具输入／结果 hash、成功状态、读文件路径和 token 用量，不保存工具正文或 thinking。默认不启用 `force`；需要执行已授权的独立验收代码任务时可对单次进程启用，不写入全局权限。Cursor 的原生 hooks 和会话持久化保持原样，因此验收 prompt 只允许显式范围的只读 Brain 适配，不能据此声称自动记忆／sync 已统一。

规则和 Skills 的证据应来自实际读取同一来源；初始化列表或模型自述不足以证明一致。接力测试从两个真实工作区启动，代码修改放在独立验收仓，接收的 Codex 再检查 HEAD、保护文件与测试结果，不以 Cursor 自述替代验证。

## 工作区验证

新客户端需在每个明确登记的范围独立验证规则、Skill、选库与交接；未覆盖的范围保留为未验证。

Claude 项目入口使用 `CLAUDE.md` 引用本地 `AGENTS.md`，项目 Skills 使用薄入口或软链复用共享源。项目配置不保存 provider、凭据或通用默认模型；这些值由用户级 Magpie 配置管理。排查异常时先核对当前 cwd 的项目配置，不能仅凭用户级文件判断实际请求经过了哪个代理。

## Grok Build

使用明确的原生 `grok` 入口，保留已有登录、模型选择和独有工具。本机版本的 `grok inspect --json` 能确认根规则、共享 Skills 和 Cursor 兼容面的发现结果；实际工具调用仍需另行验证。可复用两个工作区已有 `.cursor/rules/agent-runtime.mdc` 的显式 Brain／handoff 指引，不复制第二套 Skills，也不把 Grok 改接 Magpie。

`grok_probe.run_grok` 解析原生 streaming-json 的 tool_call / tool_call_update 和结束事件，丢弃原始工具正文、thinking 与 usage signature，保留输入／结果 hash、状态和 CLI 费用估算。探针单次设置 `GROK_MEMORY=0`，关闭自动原生记忆写入与 subagent；原有 hooks 保留。`--always-approve` 仅用于本次已授权验收，不修改持久权限。实际接力仍从两个真实 cwd 发起，在独立验收仓修改代码并交回 Codex 复核。

Cursor 规则兼容不代表 hooks 完全兼容：Grok 若明确报告某类 Cursor hooks 尚不支持，应保留现有配置、记录边界，不能声称自动同步已经统一，也不能静默复制 hooks 补齐。

## OpenCode V2

使用现有 OpenCode 登录、Magpie provider 和默认模型。项目 `opencode.json` 使用 `opencode-project.json` 的薄入口，只加入共享运行指引与 `.agents/skills`，不复制业务 Skill，不保存 provider、凭据或模型覆盖。V2 读取 `AGENTS.md`；不要假设它会把 `CLAUDE.md` 当作回退入口。

`opencode_probe.run_opencode` 通过原生 API 创建独立验收 session，再使用实际 CLI `run --standalone --session ...`。测试 session 临时只允许 read/shell/edit/skill/glob/grep，其他动作包括子agent和MCP均拒绝，不修改全局或项目权限。成功的 PATCH API 可返回空正文；验收后独立读回 session 核对权限并归档。CLI 的 `--auto` 只用于已授权的验收。

证据保留原生 tool_use 状态、输入／输出 hash、退出码和步骤元数据，丢弃工具正文及 reasoning。不能因为独立目录 API 返回空就判定 Skill 不存在；需要实际调用原生 `skill` 并读回权威源核验。本机两个目录已经完成此项验证。

## Brain 生命周期适配

`brain_hooks.py` 仅处理私有配置明确登记的根及其 Git worktrees；scope 或来源核验失败时跳过，不猜测默认库。

生命周期提醒与结束事件需按客户端当前版本单独验证，具体验收记录保存在私有 state 目录。

Cursor/Grok 提问事件不能作为可靠的上下文注入入口，因此使用受支持的启动/工具前事件；工具前提醒可能在同一轮重复。OpenCode 插件接入 V2 `setup`，不依赖旧版插件 SDK。结束适配调用显式选库的 `brain hook stop`，只启动 best-effort 后台同步，不阻止结束、不发送 follow-up。调用成功不证明远端 Git 同步成功。

安装：`python3.14 -B install_brain_hooks.py <私有 state/runs/本次目录>`。只追加 Cursor 的三个事件、Grok 专用提醒和 OpenCode 插件链接，保留 Orca/Paseo 等已有配置；首次 Cursor 配置备份不被重复安装覆盖。Codex 配置、Claude 配置及 provider/model/MCP 均不是写入目标。新开会话后加载，已有长驻 OpenCode 服务可能需要在方便时重新加载插件，不自动重启用户服务。

验收时可仅在测试进程设置 `AGENT_RUNTIME_HOOK_AUDIT`，输出事件、scope、状态及 hash，不记录提示、工具正文或 reasoning。正常启动无需设置。结束入口验收使用任务私有 CLI observer 阻止真实同步，核验 native harness 调用了正确 Brain 的 Stop；它不代表远端同步已成功。
