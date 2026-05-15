# `~/.agents/` — Skills 管理 Cheatsheet

`~/.agents/` 是 `npx skills` CLI 的全局根目录（实际指向 `~/Documents/Code/dotfiles/.agents/` 的 symlink）。
canonical skill 文件放 `skills/`，元数据 lock 放 `.skill-lock.json`。

最近一次大整理：**2026-05-09**

---

## 1. 日常更新（最常用）

```bash
~/.agents/safe-skills-update.sh
```

**不要直接 `npx skills update -g`** —— 会破坏两件事，原因都是 CLI 把 lock entry 整体覆盖、不会保留人工设置：

| 风险 | 后果 |
|---|---|
| OpenClaw 的 copy 模式被翻成 symlink | OpenClaw 加载不出 skill（symlink 时有目录权限/解析故障，2026-05-08 实测） |
| 自定义 `pluginName` 被清空 | `lark/waza/baoyu-skills/obsidian-skills/readwise-skills/chrome-devtools` 退化成上游零散名 |

包装脚本 `safe-skills-update.sh` 干的：

1. 快照 `~/.openclaw/skills/` 当前条目
2. 跑 `npx skills update -g` 透传 `$@`
3. 任何变成 symlink 的 openclaw 项 → 删掉 + 从 canonical `cp -R` 回 copy
4. 调 `apply-pluginName-overrides.py`，按 `.pluginName-overrides.json` 重写自定义命名

---

## 2. 场景速查

| 场景 | 命令 |
|---|---|
| 检查并应用更新 | `~/.agents/safe-skills-update.sh` |
| 只看有没有更新（不动文件） | `npx skills update -g` 然后看输出 `Found N updates` |
| 列出所有 skill 及 agent 归属 | `npx skills ls -g -a` |
| 装新 skill 到非-OpenClaw agent | `npx skills add <source> -g -a <agent> -s <name1> [name2 ...] -y`<br>⚠️ 单 agent 单 skill 会被强制 copy，需手动转 symlink（见下） |
| 装新 skill 到 OpenClaw | `npx skills add <source> -g -a openclaw -s <names> -y --copy --dangerously-accept-openclaw-risks` |
| 删 skill | `npx skills remove <name> -g -y` |
| 改 pluginName 规则 | 编辑 `~/.agents/.pluginName-overrides.json`，下次 update 自动生效 |
| 注册一个本地自建 skill（无 github source）| 详见下方「本地自建 skill 注册」段 |

### 本地自建 skill 注册（Personal 分组）

直接把 skill 目录放到 `~/.agents/skills/<name>/` 后，`npx skills ls -g` 默认会把它扔到 `General` 兜底分组。如果想归到 `Personal`（或别的）分组，给 `.skill-lock.json` 手加一条 entry：

```jsonc
"<name>": {
  "source": "812lcl/personal-skills",   // 占位，本地无远端
  "sourceType": "local",                // CLI 见 local 不会拉远端
  "sourceUrl": "",
  "skillPath": "SKILL.md",              // 或 skill.md，按真实文件
  "skillFolderHash": "<sha1 of SKILL.md>",
  "installedAt": "<ISO ts>",
  "updatedAt": "<ISO ts>",
  "pluginName": "Personal"
}
```

实测过 `safe-skills-update.sh`：local entry 被 update 循环跳过、pluginName 保留、不会被清理（2026-05-15）。当前已注册：`knowledge-clip` / `obsidian-review` / `service-health` / `weekly-report`。

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
