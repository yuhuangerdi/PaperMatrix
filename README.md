# PaperMatrix

PaperMatrix 是一个面向研究生和科研人员的本地优先论文知识管理 Web 应用。它将论文档案、结构化阅读笔记、问题清单和证据条目组织在同一个项目工作流中，帮助用户完成文献整理、论文汇报、相关工作写作和跨论文分析。

PaperMatrix 不使用数据库。论文元数据保存在 YAML 中，长篇笔记保存在 Markdown 中，CSV 和 Excel 仅作为可重新生成的汇总与导出。用户的原始 PDF 始终保留在原位置，应用只记录经过允许的路径引用。

## 当前能力

- 创建、编辑、归档和管理研究项目；
- 通过目录扫描、文件路径、瞬时上传或手工方式登记论文；
- 搜索、筛选、排序论文并维护项目内分组；
- 单独列出无法通过当前 Schema 读取的论文记录，并可安全删除元数据而不影响其他论文或源 PDF；
- 在概览统一编辑模板第 0 节的全部信息，包括标题、作者、单位、发表信息、链接、关键词、摘要、阅读状态、重要程度和一句话总结；
- 使用第 0–11 节完整模板维护单篇结构化 Markdown 笔记，并在完整文档与确认条目之间切换编辑；
- 自动保存笔记，并通过 revision 防止并发修改静默覆盖；
- 独立维护个人补充笔记，支持自动保存、版本冲突提示和浏览器本地草稿恢复；
- 为每篇论文维护待回答、已回答和暂缓的问题及证据；
- 条目模式预载第 1–8 节的全部模板填写项（空项也显示），固定项原位填写；代表性文献、挑战和创新点等模板明确的一对多位置可新增独立条目；
- 在条目模式的独立证据栏维护带 `E-001` 编号的论文级证据目录，新增证据时可同时关联当前条目；
- 建立同篇或跨篇结构化条目关系，检查出向/反向引用和悬空目标，并稳定跳回完整笔记中的对应条目；
- 从论文矩阵勾选结果保存可复现分析集合，固定论文 ID、用途和筛选快照，并显示后续缺失的论文；
- 检测源 PDF 缺失或变化，重新关联时不移动原文件。

跨论文分析核心仍在持续开发。当前已经完成完整 Markdown 条目化、文档/条目双模式编辑、个人补充笔记、项目级条目关系、稳定跳转和可复现分析集合；后续将继续实现准备度、项目总矩阵和领域问题归纳。

## 数据安全原则

- 不复制、移动、重命名、修改或删除用户的源 PDF；
- 删除论文记录只删除 PaperMatrix 的元数据和笔记，并要求明确确认；
- 所有业务数据使用普通文件，不引入数据库、ORM 或迁移框架；
- 所有可变项目文件使用文件锁、revision 检查和原子替换；
- 只允许访问用户配置的论文根目录；
- 后端开发服务默认绑定 `127.0.0.1`；
- MVP 不向第三方上传论文，也不调用外部 AI 或翻译服务。

## 技术栈

- 前端：Vue 3、TypeScript、Vite、Pinia、Vue Router；
- 后端：Python 3.12+、FastAPI、Pydantic、PyYAML；
- 文件处理：pypdf、openpyxl、跨平台文件锁；
- 质量保障：pytest、Ruff、mypy、Vitest、ESLint、Prettier。

## 安装

推荐使用 Conda 创建项目环境：

```bash
conda env create -f environment.yml
npm --prefix frontend install
```

如果已经创建过环境，可以同步更新依赖：

```bash
conda env update -f environment.yml --prune
npm --prefix frontend ci
```

## 启动

分别在两个终端中启动后端和前端：

```bash
make dev-backend
```

```bash
make dev-frontend
```

浏览器访问 [http://127.0.0.1:5173](http://127.0.0.1:5173)。

首次打开后：

1. 在设置页选择一个可写目录作为 PaperMatrix 工作区；
2. 添加一个或多个允许读取 PDF 的本地根目录；
3. 创建研究项目；
4. 通过目录扫描、单文件路径、瞬时上传或手工记录添加论文。

瞬时上传只在请求期间读取 PDF 元数据，不会把上传文件保存到工作区。需要持续检测文件状态时，请使用允许目录中的文件路径进行登记。

## 验证

运行完整测试、静态检查和生产构建：

```bash
make verify
```

也可以分别运行：

```bash
make backend-check
make frontend-check
```

## 项目结构

```text
PaperMatrix/
├── backend/          # FastAPI 后端、领域服务和文件仓储
├── frontend/         # Vue 3 前端
├── contracts/        # OpenAPI 与 JSON Schema
├── docs/             # 产品、架构、安全和测试文档
├── templates/        # Markdown、CSV 和 Excel 模板
├── scripts/          # 示例工作区和规格校验工具
└── Makefile          # 开发与验证入口
```

## 数据布局

每个项目的数据位于工作区的独立目录中：

```text
projects/<project-id>/
├── project.yaml
├── papers/
│   └── <paper-id>.yaml
├── notes/
│   └── <paper-id>.md
├── questions/
│   └── <paper-id>.yaml
└── analyses/
```

PDF 不会出现在该目录中；`papers/*.yaml` 只保存受允许路径约束的来源引用。

## 文档

- [产品需求](docs/01-PRD.md)
- [系统架构](docs/04-architecture.md)
- [文件数据模型](docs/05-filesystem-data-model.md)
- [API 设计](docs/06-api-design.md)
- [安全与隐私](docs/10-security-privacy.md)
- [测试与质量](docs/11-testing-quality.md)
- [验收标准](docs/12-acceptance-criteria.md)
- [跨论文分析核心](docs/17-analysis-core.md)
- [结构化笔记条目模式](docs/18-note-item-mode.md)

## 贡献

提交修改前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)，并确保 `make verify` 完整通过。涉及数据模型、API 或模板的修改需要同步更新相应契约、测试和文档。
