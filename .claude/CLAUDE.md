<!-- User preferences (senior engineer style / 简洁优先 / Chinese reply / pursue elegance)
     已沉淀到 brain preference 层，brain brief 启动自动加载 -->

## Claude Code 特有偏好

### 子代理策略
- 灵活大量使用子代理，保持主对话上下文窗口整洁
- 将调研、探索、并行分析类工作分流给子代理执行
- 针对复杂问题，通过子代理投入更多算力解决
- 单个子代理仅负责一项任务，保证执行聚焦

### 自动化缺陷修复
- 收到缺陷报告后直接修复，无需额外的手把手指导
- 定位日志、报错信息、未通过的测试用例，完成问题修复
- 无需用户进行任何上下文切换
- 无需额外指令，主动修复未通过的 CI（持续集成）测试

### Compact Instructions 保留优先级
- 架构决策，不得摘要
- 已修改文件和关键变更
- 验证状态，pass/fail
- 未解决的 TODO 和回滚笔记
- 工具输出，可删，只保留 pass/fail 结论

# graphify
- **graphify** (`~/.claude/skills/graphify/SKILL.md`) - any input to knowledge graph. Trigger: `/graphify`
When the user types `/graphify`, invoke the Skill tool with `skill: "graphify"` before doing anything else.
