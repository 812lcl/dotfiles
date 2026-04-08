---
name: write
description: Invoke only when explicitly asked to write, edit, or polish prose in Chinese or English. Strips AI writing patterns and rewrites to sound natural. Not for code comments, commit messages, or inline docs.
version: 3.2.0
disable-model-invocation: true
---

# 写作风格 / Writing Style

检测**被编辑文本**（不是用户的指令）的语言：
- 含中文字符 → 加载 `references/write-zh.md`
- 否则（英文、混合、不确定）→ load `references/write-en.md`

如果受众不明确（博客读者？RFC？邮件？），先问清楚再编辑。同一内容写给初级工程师和写给高级架构师，读起来应该完全不同。

执行顺序: 读取对应规则文件，严格按规则处理，输出修改后的内容。

输出修改后的内容后，停止。除非用户主动询问，否则不解释改动。
