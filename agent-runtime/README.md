# Agent runtime 兼容层

本目录是可选的本机适配与交接工具。Codex 继续使用原启动入口，默认作为受保护基准；经用户明确授权的 Magpie 资源／hook 分发另行精确记录变更范围。适配工具不切换 Codex provider、登录或原生记忆，不设置全局 PATH／BRAIN_DIR。

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

## Skills 自动分组

`skill_groups.py` 只维护 Magpie `library.json` 的 `skillGroups` 显示元数据。来源标签取既有 `.pluginName-overrides.json`、`.skill-lock.json` 的 `pluginName`，以及私有 `skill-group-policy.json` 中明确登记的工作／个人本地来源。GitHub 新导入项即使尚未进入 skills CLI 锁文件，也可按源仓映射分组；更新清掉锁文件中的标签时，既有来源覆盖仍有效。没有标签或规则的项保持原来源展示。

只遍历当前 `library.skills`：删除后不会从锁文件、旧分组、备份或磁盘重新导入。现有的 `agents`、关闭状态、路由、MCP、hooks、应用所有权均不修改，也不执行 `magpie library sync` 或 `npx skills update`。有明确标签的项按标签归组；没有标签的手工分组保留。分组中的已删除成员会清理掉。用户手动修改分组，但原 `pluginName` 仍有效时，下次会重新按该标签归组；已有来源的覆盖在 `.pluginName-overrides.json` 调整，缺少来源标签的本地项可在私有 policy 补充。

```bash
python3.14 -B skill_groups.py          # 只预览
python3.14 -B skill_groups.py --apply  # 立即同步显示分组
python3.14 -B install_skill_groups.py  # 生成私有策略与用户 LaunchAgent；不覆盖已有策略
```

本机已加载 `com.liuchunlei.agent-runtime.skill-groups` 用户任务，监听 Library、Skills 锁文件、标签覆盖和私有 policy；事件合并时每60秒补查。Magpie UI 导入／更新、skills CLI 更新元数据均由此覆盖，不需要更换启动入口。脚本无第三方依赖，不调用模型或网络。无变化不重写 Library，后台仅记录变化与错误；`~/.local/state/agent-runtime/skill-groups/last-run.json` 保留最近检查结果。

写入前等待输入稳定并在最终 rename 前再次检查，检测到并发编辑则跳过，等下一次触发重试，不恢复旧配置。Magpie 没有跨进程事务，这只是乐观并发保护。只在确有分组变化时备份原 Library，备份0600、私有目录0700，最多20份。Library 被删除或 Magpie 卸载后不重建其目录。停用时卸载该用户 LaunchAgent 即可，现有分组与分发不回滚。

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

Magpie Library 使用5个定义分发13个原生事件入口，所有命令共用 Git 中的 `brain_hooks.py portable <event>`，命令不带客户端名称：

| Library 名称 | 事件 | 分发对象 |
|---|---|---|
| brain-stop | turn-end | Claude、Codex、Cursor、Grok、Gemini |
| brain-prompt | prompt | Claude、Codex、Gemini |
| brain-before-tool | before-tool | Cursor、Grok |
| brain-session-start | session-start | Claude、Cursor |
| brain-codex-session-start | codex:SessionStart，matcher `^(startup|compact)$` | Codex |

最后一条复用同一个 `portable session-start` 命令，只单列 Codex 原有的启动条件。Magpie 负责原生事件名称、配置格式和 Gemini 毫秒超时换算；所有定义的外层超时统一为30秒。共享入口只接受已核对的 `hook_event_name`，不猜测进程或模型来源。Cursor 启动返回 `additional_context`，标准 SessionStart 返回偏好列表的 `hookSpecificOutput`；查询和工具前事件返回各自协议的上下文；结束统一显式选库并返回空对象，不改变权限或追加 follow-up。Claude／Codex 不再各自调用旧生命周期／direnv 命令。

分库注册表保存在私有 profiles 中，由用户明确登记项目范围和关联 Git worktree；未知或混合范围跳过，不回退默认库。

替换旧库条目后，必须核对 `applied.<client>.hooks` 所有权及原生入口数量，防止旧定义和通用定义并存。Codex 的命令改变会触发重新信任：仅核对本次共享脚本和 matcher 后，用本机 app-server 更新这些 Brain hooks 的当前 hash；不关闭信任检查、不授予其他 hooks 权限。
OpenCode 继续使用原生插件；Hermes／WorkBuddy／DeepSeek Harness 当前不属于 Magpie Hooks 支持范围。各客户端的 Orca／Paseo 命令 hooks 按用户要求移除，OpenCode 对应活动桥接插件退出加载，Hermes 的 Orca 状态插件停用；不卸载这两个应用，也不改变其他插件。Codex 中仅移除这两类桥接的信任记录，Brain 事件的组索引仍为零。若外部应用后续自行重新安装 hooks，应重新检查来源，不由 Brain 安装器反复争抢配置。

私有 profiles 的 `brain_hooks.materialized_by = magpie.library` 表示分发归属；旧 `install_brain_hooks.py` 此时拒绝写入，日常恢复入口使用 `magpie library sync`。首次迁移需先备份并精确移除旧 Brain 入口，再让 Magpie 原生同步写入并记录所有权；仅添加相同命令不会接管已有入口。库中取消分配只撤销 Magpie 自己写入且尚未被修改的项。不要将同一客户端同时分配继承入口和原生入口。

`brain_hooks.py` 仅处理私有配置明确登记的根及其 Git worktrees；scope 或来源核验失败时跳过，不猜测默认库。

生命周期提醒与结束事件需按客户端当前版本单独验证，具体验收记录保存在私有 state 目录。

Cursor/Grok 提问事件不能作为可靠的上下文注入入口，因此使用受支持的启动/工具前事件；工具前提醒可能在同一轮重复。OpenCode 插件接入 V2 `setup`，不依赖旧版插件 SDK。结束适配调用显式选库的 `brain hook stop`，只启动 best-effort 后台同步，不阻止结束、不发送 follow-up。调用成功不证明远端 Git 同步成功。

Grok 的 Cursor hooks 兼容扫描默认开启，但当前安装版拒绝 Cursor 直接 handler 的返回协议，会在 `/hooks` 显示 “won't run until Grok reads Cursor hook replies”。本机已在 `~/.grok/config.toml` 设置 `[compat.cursor] hooks = false`；仅停止重复扫描 Cursor hooks，不关闭 Cursor 的 rules/skills/agents/MCP，也不改 Cursor 自己的 hooks。迁移后 Grok 加载原生 Brain PreToolUse／Stop，同时关闭 Claude hooks 继承。`grok inspect --json` 可核验静态加载，不能代替完整会话内插件加载验收。

Claude 插件还可能有独立兼容边界：`security-guidance` 的 `asyncRewake`/条件字段及 Warp 的 `PermissionRequest` 尚不被当前 Grok 支持。2026-11-11 用户明确要求从 Cursor/Grok 去掉报错项后，本机仅在 Grok 的 `[plugins] disabled = ["warp", "security-guidance"]` 中排除这两个插件，不改共享 Claude 插件缓存或 Claude 启用设置。Cursor 的 Customize 用户插件及 hooks 界面未发现这两个插件条目，无需删除；当时保留其他 hooks；后续 Orca/Paseo 清理见本节前文。不要删除条件字段伪装成等价适配。启动过的 Grok 会话应新开会话以反映插件过滤配置。

旧安装入口：`python3.14 -B install_brain_hooks.py <私有 state/runs/本次目录>`。仅用于尚未登记 Magpie 所有权的旧安装；完成迁移后该入口拒绝写入，使用 `magpie library sync` 恢复通用定义。新开会话后加载，已有长驻 OpenCode 服务可能需要在方便时重新加载插件，不自动重启用户服务。

验收时可仅在测试进程设置 `AGENT_RUNTIME_HOOK_AUDIT`，输出事件、scope、状态及 hash，不记录提示、工具正文或 reasoning。正常启动无需设置。结束入口验收使用任务私有 CLI observer 阻止真实同步，核验 native harness 调用了正确 Brain 的 Stop；它不代表远端同步已成功。
