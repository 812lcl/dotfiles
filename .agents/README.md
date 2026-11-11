# 全局 Skill 的源码

本仓库 `.agents/skills/` 是第三方 Skill 的 Git 维护源，继续使用 npx skills 升级。用户级 `~/.agents` 是独立的运行目录，不再把整个目录链接到本仓库；其中的 `skills/` 由 Magpie 管理。

升级在源码仓内执行项目模式，防止 npx 重新创建全局的非托管入口：

```sh
cd /Users/liuchunlei/Code/dotfiles
npx skills update --project
```

`skills-lock.json` 保存现存第三方 Skill 的升级来源与原生内容 hash；`.agents/.skill-lock.json` 保留原安装来源、pluginName 等历史元数据。新增、移除或升级后审查 Git diff，再将需要的新项登记到 Magpie；不自动恢复曾删除的 Skill、不自动扩大 agent 勾选。

Magpie 内安装的 Skill 仍由 Magpie 升级；Brain 与工作 CLI 的自维护 Skill 继续在各自 Git 仓库维护。Magpie 使用这些目录作为 source，只负责创建和撤销加载链接。关闭共享目录组时须取消组内全部接收者，否则链接仍为其他成员保留。
