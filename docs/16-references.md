# 参考资料

本规格包的代理协作结构参考 OpenAI 官方 Codex 文档：

- Codex 最佳实践：使用简短、准确的 `AGENTS.md` 保存仓库布局、运行命令、工程约束和完成定义。
  - https://developers.openai.com/codex/learn/best-practices
- `AGENTS.md` 的发现和作用域规则。
  - https://developers.openai.com/codex/agent-configuration/agents-md
- Codex 自定义概览：AGENTS.md、skills、MCP 和子代理各自承担不同层次的上下文与工作流。
  - https://developers.openai.com/codex/customization/overview
- Codex 子代理：适合把独立部分并行处理，主线程负责汇总和审查。
  - https://developers.openai.com/codex/subagents
- OpenAI 如何使用 Codex：以 AGENTS.md 提供持续项目上下文。
  - https://openai.com/business/guides-and-resources/how-openai-uses-codex/

工程技术的具体实现应以项目锁定版本对应的官方文档为准：

- Vue：https://vuejs.org/
- Vite：https://vite.dev/
- FastAPI：https://fastapi.tiangolo.com/
- Pydantic：https://docs.pydantic.dev/
- Python pathlib：https://docs.python.org/3/library/pathlib.html
