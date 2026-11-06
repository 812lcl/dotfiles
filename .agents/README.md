# `~/.agents/` — Skills 管理 Cheatsheet

`~/.agents/` 是 `npx skills` CLI 的全局根目录（实际指向 `~/Code/dotfiles/.agents/` 的 symlink）。
`skills/` 保存发现入口（可以软链到 Vault 或私有工作仓的唯一源码），元数据 lock 放 `.skill-lock.json`。

最近一次大整理：**2026-05-09**

---

## 1. 日常更新（最常用）

```bash
~/.agents/safe-skills-update.sh
```

**不要直接 `npx skills update -g`** —— 会破坏两件事，原因都是 CLI 把 lock entry 整体覆盖、不会保留人工设置：

| 风险 | 后果 |
|---|---|
| OpenClaw 的 copy 模式被翻成 symlink | 本机发现根策略可能拒绝越界软链；保留复制分发，实际文件访问权限另行核对 |
| 自定义 `pluginName` 被清空 | `lark/waza/baoyu-skills/obsidian-skills/readwise-skills/chrome-devtools` 退化成上游零散名 |

包装脚本 `safe-skills-update.sh` 干的：

1. 快照 `~/.openclaw/skills/` 当前条目
2. 跑 `npx skills update -g` 透传 `$@`
3. 任何变成 symlink 的 openclaw 项 → 删掉 + 从 canonical `cp -R` 回 copy
4. 调 `apply-pluginName-overrides.py`，按 `.pluginName-overrides.json` 重写自定义命名
5. 恢复既有 Work manifest 和入口
6. 对 knowledge-clip 运行同一复制适配步骤，保持后续更新一致

### 只同步 OpenClaw 的 knowledge-clip（不运行全量更新）

```bash
~/.agents/safe-skills-update.sh --sync-openclaw --skill knowledge-clip --dry-run
~/.agents/safe-skills-update.sh --sync-openclaw --skill knowledge-clip --apply
```

此分支不执行 npx、不改 `.skill-lock.json`/pluginName/Work manifest、不碰其他技能、配置或服务。必须明确 `--skill`；不带 `--apply` 只预览。内部 `openclaw-copy-adapter.py` 由同一个日常入口调用，不是第二套同步入口。当前适配仅支持 knowledge-clip；clawfeed 不进入此机制。

它复制完整 skill（排除运行缓存），保留 source YAML 标识和 OpenClaw `.clawhub` 元数据，再生成两个适配点：SKILL 正文的明确路径说明、`scripts/clip_flow.py` 薄委派。后者用已验证的 Python/PyYAML 运行 Vault 中的 canonical clip_flow，避免原样复制后按错误目录层级找 guard。共享工具、Wiki 正文、索引入口、契约、profile、Properties、schema/ledger仍从明确 Vault 读取，不复制业务笔记或权限配置。

同步会校验所选 Python ≥3.10 且已有 PyYAML 6.x；不自动安装依赖。若当前 PATH 的 `python3` 缺依赖，定向命令可加 `--python /opt/homebrew/opt/python@3.14/bin/python3.14`。已生成的 clip 执行入口固定使用验证过的解释器，运行目录和普通 `python3` 的变化不会让它误用系统 Python。

`.openclaw-copy.json` 记录来源与本机制管理的文件 hash（不修改原锁映射）。重复同步为 no-op；canonical 更新后重建同一适配。发现本地人工修改/未知文件、断依赖或并发变化就停止，不强制覆盖。实际文件访问若被 OpenClaw 拒绝，必须报告，不能用 exec/其他路径绕过；发现根限制不等于已获得访问权限。

每次有变化的定向同步先把完整旧副本与权限/hash保存到 `~/.openclaw/backups/skill-sync/`；可用 `--backup-dir <绝对目录>` 指定本机归档位置。无变化不生成新备份。正常 `safe-skills-update.sh` 全局更新前做预检、更新后复用此适配步骤，即使 knowledge-clip 始终是 copy 也会刷新，所以下次同步不会丢掉适配。上游更新失败时仍尝试既有 copy/pluginName/Work 恢复和 clip 适配，并保留失败退出码。

不自动 commit/push，不重启 Gateway、不关闭会话、不发送消息。同步完成仍需核验 loader 的文件来源；既有会话已经读入的旧正文需要新会话验证，不能仅凭文件同步宣称微信端到端成功。

---

## 2. 场景速查

| 场景 | 命令 |
|---|---|
| 检查并应用更新 | `~/.agents/safe-skills-update.sh` |
| 只预览本次 OpenClaw clip 同步（不动文件） | `~/.agents/safe-skills-update.sh --sync-openclaw --skill knowledge-clip --dry-run`；`npx skills update -g` 会更新，不是只读检查 |
| 列出所有 skill 及 agent 归属 | `npx skills ls -g -a` |
| 装新 skill 到非-OpenClaw agent | `npx skills add <source> -g -a <agent> -s <name1> [name2 ...] -y`<br>⚠️ 单 agent 单 skill 会被强制 copy，需手动转 symlink（见下） |
| 装新 skill 到 OpenClaw | `npx skills add <source> -g -a openclaw -s <names> -y --copy --dangerously-accept-openclaw-risks` |
| 删 skill | `npx skills remove <name> -g -y` |
| 改 pluginName 规则 | 编辑 `~/.agents/.pluginName-overrides.json`，下次 update 自动生效 |
| 注册一个本地自建 skill（无 github source）| 详见下方「本地自建 skill 注册」段 |

### 本地自建 skill 注册（Personal / Work 分组）

直接把 skill 目录放到 `~/.agents/skills/<name>/` 后，`npx skills ls -g` 默认会把它扔到 `General` 兜底分组。如果想归到 `Personal` / `Work`（或别的）分组，给 `.skill-lock.json` 手加一条 entry：

```jsonc
"<name>": {
  "source": "812lcl/personal-skills",   // 或 812lcl/work-skills；本地无远端
  "sourceType": "local",                // CLI 见 local 不会拉远端
  "sourceUrl": "",
  "skillPath": "SKILL.md",              // 或 skill.md，按真实文件
  "skillFolderHash": "<sha1 of SKILL.md>",
  "installedAt": "<ISO ts>",
  "updatedAt": "<ISO ts>",
  "pluginName": "Personal"              // 或 Work
}
```

实测过 `safe-skills-update.sh`：local entry 被 update 循环跳过、pluginName 保留、不会被清理（2026-05-15）。

工作特有 skill 不放进 public dotfiles 仓库维护；真实内容放在私有工作仓库：

```bash
~/.brain/.agents/.skill-lock.json
~/.brain/.agents/skills/<name>/
~/.agents/skills/<name> -> ~/.brain/.agents/skills/<name>
```

dotfiles 中只保留 `.skill-lock.json` 的 local entry 和被 `.gitignore` 忽略的本机 symlink 入口。若新增工作 skill，先更新私有 manifest，再执行：

```bash
python3 ~/.brain/.agents/sync-work-skill-lock.py --apply
```

`safe-skills-update.sh` 会在 `npx skills update -g` 后自动尝试执行这个同步脚本。若新增新的 local source，再同步更新 `.pluginName-overrides.json` 中的映射；当前 `812lcl/work-skills -> Work` 已覆盖工作 skill。

### CLI 单 agent 强制 copy 的问题 + 修复模板

`cli.mjs:2689` 有这条：

```js
} else if (uniqueDirs.size <= 1) installMode = "copy";
```

也就是当 `-a` 只指定 1 个非 universal agent + `-y` 时，无论你传不传 `--copy`，都被强制 copy。修复：

```bash
NAME=defuddle
AGENT_DIR="$HOME/.claude/skills"   # 改成对应 agent 的 skills 目录
P="$AGENT_DIR/$NAME"
[ -d "$P" ] && [ ! -L "$P" ] && rm -rf "$P" && ln -s "../../.agents/skills/$NAME" "$P"
```

或者批量：用 `~/.agents/.skill-install-snapshot.<日期>.json` 当目标状态喂给 `restore-symlinks.py`（脚本现在在 `/tmp/`，需要恢复时翻 git/刚才的 session 拷贝过来）。

---

## 3. 关键文件

| 文件 | 作用 |
|---|---|
| `.skill-lock.json` | npx skills 的真相源，每条 skill 一个 entry |
| `~/.brain/.agents/.skill-lock.json` | 私有 Work skills 的源头 manifest |
| `~/.brain/.agents/sync-work-skill-lock.py` | 把 Work manifest 同步/校验到全局 lock 和 symlink 入口 |
| `safe-skills-update.sh` | **日常入口**：update + openclaw 守护 + pluginName 守护 |
| `apply-pluginName-overrides.py` | 按规则表重写 lock 里的 pluginName |
| `.pluginName-overrides.json` | pluginName 规则表（per source） |
| `.skill-install-snapshot.*.json` | 历史快照（重装前 agent × mode 矩阵），用于事故回滚 |
| `.skill-lock.json.bak.*` | 历次 lock 备份 |

---

## 4. 设计约束（别破坏）

| 约束 | 原因 |
|---|---|
| OpenClaw 的 skill 必须是 **copy**，不能 symlink | 2026-05-08 实测 symlink 触发权限/路径解析失败 |
| 其他所有 agent（claude-code/kiro-cli/qwen-code/trae/windsurf/antigravity）默认 **symlink** | 单一真相源，update 不需要逐个 agent 同步 |
| Warp 共用 `~/.agents/skills/` | CLI 把 warp 当 universal agent，没有独立目录 |
| canonical（`~/.agents/skills/<name>`）必须存在，名字必须 = SKILL.md frontmatter `name` | symlink/copy 都依赖 canonical |

---

## 5. 不要做

- ❌ `rm -rf ~/.agents/skills/<name>` —— lock 和文件系统脱钩
- ❌ 重命名 `~/.agents/skills/` 下任何目录
- ❌ 给 OpenClaw 建 symlink 装 skill
- ❌ 用 `--copy` 装到非-OpenClaw agent
- ❌ 直接编辑 `.skill-lock.json` 的 `skillFolderHash` 字段（hash 是上游 git tree SHA，本地算不出，会让 update 误判 stale）

---

## 6. 故障排查

| 症状 | 排查 |
|---|---|
| Claude Code skill 列表出现 `<name> 2`/`<name> 3` 后缀 | `~/.claude/skills/` 里有同名 symlink 重复，`ls "$HOME/.claude/skills" \| grep " 2$"` 然后 `rm` |
| OpenClaw 加载不出某 skill | 看是不是 symlink：`ls -la ~/.openclaw/skills/<name>`，是 symlink 就 `rm` 后 `cp -R ~/.agents/skills/<name> ~/.openclaw/skills/<name>` |
| `npx skills update -g` 只检查 13/64 | 大量 entry `skillFolderHash` 为空，重装该 source 一次：`npx skills add <source> -g -a <agent1> [agent2 ...] -y`（多 agent 才会保 symlink） |
| pluginName 被改回上游名（特别是 waza/obsidian） | 跑 `python3 ~/.agents/apply-pluginName-overrides.py` |
| canonical 缺失但 agent 目录还有 symlink → 死链 | `find ~/.claude/skills ~/.openclaw/skills ~/.kiro/skills ~/.qwen/skills ~/.trae/skills ~/.codeium/windsurf/skills -type l ! -exec test -e {} \; -print` 找出来后删 |

---

## 7. 各 agent 的 skills 目录

| Agent | 目录 | 默认模式 |
|---|---|---|
| Warp | `~/.agents/skills/`（共享 canonical） | universal（无 link/copy） |
| Claude Code | `~/.claude/skills/` | symlink |
| Kiro CLI | `~/.kiro/skills/` | symlink |
| Qwen Code | `~/.qwen/skills/` | symlink |
| Trae | `~/.trae/skills/` | symlink |
| Windsurf | `~/.codeium/windsurf/skills/` | symlink |
| Antigravity | `~/.gemini/antigravity/skills/` | symlink |
| **OpenClaw** | `~/.openclaw/skills/` | **copy（强制约束）** |
| Codex | `~/.codex/skills/` | 由 Codex 自管，不归 npx skills |

`graphify`（Claude Code-only）和 `clawfeed`（OpenClaw-only）不归 `npx skills` 管，是各自 agent 直接装的，audit 脚本已知白名单。
