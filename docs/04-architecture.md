# 系统架构

## 1. 部署模型

MVP 采用本地自托管模式：

```text
浏览器（Vue） ──HTTP──> 本机 FastAPI ──文件系统──> PaperMatrix 工作区
                                           └──────> 用户论文目录（只读）
```

- 前端开发服务器和后端运行在同一台电脑；
- 生产 Web 形态可由 FastAPI 托管前端静态文件，或由单独静态服务器提供；
- 后端默认监听 `127.0.0.1`；
- 工作区和论文路径均是“后端所在机器”的路径；
- 远程多用户访问不属于 MVP。

## 2. 分层

### API 层

职责：HTTP 路由、请求解析、响应序列化、错误映射。不得直接操作文件。

### Domain 层

职责：Workspace、Project、Paper、AnalysisScope、Taxonomy、Relation、Claim、ResearchGap 等领域模型和不变量。不得依赖 FastAPI。

### Service 层

职责：编排导入、保存、删除记录、重新关联、完整笔记与条目投影同步、个人补充笔记、条目关系、分析集合、领域问题归纳、矩阵组装、可比性判定、关系子图、综合分析和导出。

### Repository 层

职责：把领域对象映射为 YAML/Markdown 文件；处理锁、原子写入、schema 校验和版本迁移。

### Exporter 层

职责：把领域对象生成 CSV、XLSX 和 Markdown。导出物不是唯一数据源。

### Frontend API 层

职责：统一 `fetch`、超时、错误码、类型映射和取消请求。

### Frontend State 层

Pinia 只保存界面状态和当前加载数据，不作为持久化数据源。

## 3. 后端建议模块

```text
backend/src/papermatrix/
├── main.py
├── api/
│   ├── deps.py
│   ├── errors.py
│   └── v1/
├── core/
│   ├── config.py
│   ├── logging.py
│   ├── paths.py
│   ├── atomic_io.py
│   ├── locks.py
│   └── schema_registry.py
├── domain/
│   ├── workspace.py
│   ├── project.py
│   ├── paper.py
│   ├── note.py
│   ├── analysis_scope.py
│   ├── taxonomy.py
│   ├── relation.py
│   ├── claim.py
│   └── gap.py
├── repositories/
│   ├── workspace_repository.py
│   ├── project_repository.py
│   ├── paper_repository.py
│   ├── analysis_repository.py
│   └── relation_repository.py
├── services/
│   ├── project_service.py
│   ├── paper_import_service.py
│   ├── note_service.py
│   ├── matrix_service.py
│   ├── comparison_service.py
│   ├── graph_service.py
│   ├── claim_service.py
│   ├── synthesis_service.py
│   └── diagnostics_service.py
└── exporters/
    ├── csv_exporter.py
    ├── xlsx_exporter.py
    └── markdown_exporter.py
```

## 4. 前端建议模块

```text
frontend/src/
├── api/
│   ├── client.ts
│   ├── errors.ts
│   └── modules/
├── components/
│   ├── common/
│   ├── papers/
│   ├── matrices/
│   ├── analysis/
│   ├── graphs/
│   └── notes/
├── composables/
├── layouts/
├── router/
├── stores/
├── types/
├── views/
└── utils/
```

## 5. 核心操作流程

### 导入论文

1. 前端提交目录路径和递归选项；
2. 后端规范化路径并验证其位于允许根目录；
3. 后端扫描 PDF，只返回候选列表；
4. 用户选择后提交登记请求；
5. 后端读取只读元数据和指纹；
6. 检查重复；
7. 创建 `paper.yaml` 和初始 `note.md`；
8. 返回新论文对象；
9. 不复制 PDF。

### 保存论文元数据

1. API 校验 `If-Match` 或 revision；
2. Service 应用业务校验；
3. Repository 获取文件锁；
4. 再次读取 revision，防止丢失更新；
5. 写临时 YAML；
6. 原子替换；
7. 返回新 revision。

### 生成跨论文分析视图

1. 前端提交项目 ID、分析集合 ID、分析镜头和筛选条件；
2. Service 读取集合并保留缺失论文引用；
3. Repository 批量读取所需论文 YAML 和项目级分析 YAML，不解析无关 Markdown 正文；
4. Service 组装矩阵、可比性、关系子图或主张证据链；
5. 响应携带分析集合 revision、来源文件 revision 和缺失/待补证据警告；
6. 前端编辑单篇事实时调用论文更新接口，编辑项目判断时调用对应分析资源接口；
7. 图布局和筛选不得写回关系数据，只有用户明确保存视图时更新 `views.yaml`。

### 删除论文记录

1. 前端明确展示“不会删除 PDF”；
2. 后端检查确认令牌或显式 `delete_metadata=true`；
3. 删除 PaperMatrix 的 `paper.yaml`、`note.md` 和问题文件，并把项目分析中的对应引用标记为缺失或按用户确认清理；
4. 不调用任何针对 `source.path` 的删除操作；
5. 返回被清理的 PaperMatrix 文件清单。

关系、主张和研究空白可能承载仍有价值的跨论文判断，因此删除论文记录时不能无提示地删除整条项目级分析；应先计算受影响引用，显示影响范围，再按资源规则清理或保留缺失标记。

## 6. 并发和冲突

MVP 假设单用户，但浏览器多标签页仍可能并发写入。每个可编辑文件包含 `revision` 和 `updated_at`。更新请求携带旧 revision；不一致时返回 `PM-CONFLICT-001`，前端保留本地内容并展示对比/重新加载选项。

## 7. Schema 演进

- 每个 YAML 顶层包含 `schema_version`；
- 读取时按版本验证；
- 旧版本通过纯函数迁移到当前内存模型；
- 只有用户确认后才写回升级；
- 不识别的新版本进入只读状态，防止旧程序覆盖新数据。

## 8. 未来 AI 模块边界

未来新增 `providers/`、`tasks/` 和 `proposals/`：模型输出先作为“候选提案”保存，不直接覆盖人工数据。每项提案保存模型、时间、输入范围、证据、置信度和确认状态。
