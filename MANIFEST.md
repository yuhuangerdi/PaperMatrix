# 文件清单

## `.codex-prompts/`（本地忽略）

- `.codex-prompts/prompt.md`：交给 Codex 的总开发提示词；包含目标、技术栈、硬约束、当前实施基线和完成格式。
- `.codex-prompts/PLANS.md`：从工程基础到可选 AI 模块的阶段计划。
- `.codex-prompts/TASKS.md`：当前迭代与已完成工作的可执行任务看板。
- `.codex-prompts/DESIGN.md`：论文知识库功能、字段、阅读流程和原型设计参考。

## 根目录

- `AGENTS.md`：每次编码都适用、供 Codex 自动发现的持久工程规则（本地忽略）。
- `README.md`：使用说明。
- `CHANGELOG.md`：变更记录模板。
- `CONTRIBUTING.md`：协作和审查规则。
- `Makefile`：启动开发服务并运行完整质量检查。
- `environment.yml`：创建 `Paper` Conda Python 3.12 环境。

## docs

- 产品愿景、PRD、功能分级、用户故事；
- 系统架构、文件模型、API、前后端和 UI 规范；
- 安全隐私、测试质量、验收标准、开发工作流、错误码；
- 开放问题、官方参考资料、跨论文分析核心设计和 4 个 ADR。

## contracts

- `openapi.yaml`：API 初始契约；
- `schemas/`：工作区、项目、论文、问题、条目关系、问题归纳和研究空白 JSON Schema。

## templates

- 单篇论文结构化笔记模板；
- 一页汇报摘要模板；
- 跨论文综合分析模板；
- 研究空白 CSV 模板；
- 包含 7 张工作表的 Excel 整理模板。

## examples

- 一个不含真实 PDF 的演示工作区；
- 展示 YAML、Markdown、关系和研究空白的预期文件布局。

## frontend / backend / tests

- `backend/`：FastAPI 应用、文件安全基础设施和 pytest 测试。
- `frontend/`：Vue 3 工作台、API 客户端、状态管理和 Vitest 测试。
- `tests/`：预留跨端和端到端测试目录。

## design-system

- PaperMatrix 的颜色、排版、组件和无障碍设计规则。
