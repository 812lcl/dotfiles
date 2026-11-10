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

本机映射在 `~/.local/state/agent-runtime/profiles.json`。运行报告、快照与精确回退记录位于该私有 state 目录，源码仓库不包含凭据或实际 Brain 内容。`init` 只创建新映射，已存在时拒绝覆盖。

## Codex 基准

```bash
python3.14 -B runtime.py baseline capture --vault-root '<实际 Vault 根>' --output '<state目录>/baseline.json'
python3.14 -B runtime.py baseline check --snapshot '<state目录>/baseline.json' --output '<state目录>/check.json'
```

快照记录类型、权限、软链目标和内容 hash，不保存文件原文。认证、native memories、会话、日志、数据库等动态运行数据不扫描，也不是写入目标。已确定版本的插件静态源可通过重复 `--extra-source` 单独纳入。

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

本期支持 Codex 基准和 Claude 接入。其他客户端仍待逐一适配、实际启动和接力验收。
