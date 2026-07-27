# API 设计说明

完整初始契约见 `contracts/openapi.yaml`。

## 1. 基本约定

- 前缀：`/api/v1`
- JSON 字段：snake_case
- 时间：UTC ISO 8601
- ID：UUID 字符串
- 分页：`page`、`page_size`，响应包含 `total`
- 排序：`sort=field` 或 `sort=-field`
- 更新冲突：请求体或 `If-Match` 提供 revision
- 错误：统一 Problem Details 风格并包含 PaperMatrix 错误码

## 2. 错误响应

```json
{
  "error": {
    "code": "PM-PATH-002",
    "message": "该路径不在允许的论文目录中。",
    "details": {"field": "directory"},
    "action": "请先在设置中添加允许目录。",
    "request_id": "..."
  }
}
```

生产日志不记录完整论文路径；API 在必要时只向本地用户返回规范化路径。

## 3. 资源

### 系统

- `GET /health`
- `GET /version`
- `GET /diagnostics`

### 工作区

- `GET /workspace`
- `POST /workspace/initialize`
- `PATCH /workspace`
- `POST /workspace/validate-path`

### 项目

- `GET /projects`
- `POST /projects`
- `GET /projects/{project_id}`
- `PATCH /projects/{project_id}`
- `POST /projects/{project_id}/archive`
- `DELETE /projects/{project_id}`

### 论文候选与导入

- `POST /paper-sources/scan`
- `POST /projects/{project_id}/papers/import`
- `POST /projects/{project_id}/papers/upload`
- `POST /projects/{project_id}/papers/link`
- `POST /projects/{project_id}/papers/manual`
- `GET /projects/{project_id}/papers`
- `GET /projects/{project_id}/papers/{paper_id}`
- `PATCH /projects/{project_id}/papers/{paper_id}`
- `POST /projects/{project_id}/papers/{paper_id}/relink`
- `DELETE /projects/{project_id}/papers/{paper_id}`

论文列表响应中的 `items` 只包含可通过迁移和当前 Schema 校验的记录；`invalid_items` 单独返回无法读取的记录 ID、可识别标题、Schema 版本和原因。无效记录不参与搜索、筛选、排序或正常论文总数，但必须始终可见，并复用仅删除 PaperMatrix 元数据的确认删除端点。不得在列表读取时自动改写无效文件。

### 笔记

- `GET /projects/{project_id}/papers/{paper_id}/note`
- `PUT /projects/{project_id}/papers/{paper_id}/note`

未持久化的模板笔记返回 `revision: 0`，首次保存写入 `notes/<paper-id>.md` 并返回 revision 1。Markdown 文件包含 YAML front matter；API 的 `markdown` 字段只返回正文。

### 问题

- `GET/POST /projects/{project_id}/papers/{paper_id}/questions`
- `PATCH/DELETE /projects/{project_id}/papers/{paper_id}/questions/{question_id}`

未持久化的问题清单返回 revision 0。标记为 `answered` 时答案不能为空；open 和 deferred 可以保留空答案。证据支持印刷页码、PDF 物理页、章节、图、表、定位说明和未来结构化条目 ID。

### 单篇分析条目

- `GET /projects/{project_id}/papers/{paper_id}/analysis`
- `POST /projects/{project_id}/papers/{paper_id}/analysis/items`
- `PATCH/DELETE /projects/{project_id}/papers/{paper_id}/analysis/items/{item_id}`

分析条目写回论文 YAML 的 `structured_summary.items`，与论文共用 revision、文件锁和原子替换。服务端固定证据的 `paper_id` 为当前论文；缺少证据允许保存并由界面标记“待补证据”。

结构化笔记解析使用两个独立动作：

- `POST .../analysis/parse-note` 读取当前笔记，返回候选、来源标题、行号、证据和重复状态，不写任何文件；
- `POST .../analysis/import-candidates` 同时校验预览时的笔记 revision 与论文 revision，重新解析并验证候选 ID，再为选中且非重复的条目写入 Markdown 稳定锚点和论文 YAML 投影；响应同时返回更新后的笔记，客户端必须同步正文与 revision。

尚未保存的默认模板返回 revision 0、空候选和填写提示。解析器必须忽略模板自带的示例流程、占位模块和填写说明，不得将脚手架内容写入论文分析投影。

候选在论文详情加载和每次笔记保存后的 `GET .../note/items` 中自动生成，该响应同时包含 `candidates`、`warnings` 和待审阅数量。用户打开审阅窗口不会触发首次解析，只读取这份自动解析结果；手动 `parse-note` 端点保留用于兼容和显式刷新。

默认粒度以三级/四级语义标题块为一条，块内段落、列表和键值保持在同一条目；结构化表格按每个有效数据行形成一条。第 0、9、10、11、12 节分别作为元数据、关系候选、写作用途、证据和阅读问题来源，不复制成普通分析条目。

首次候选 ID 由论文、类型、来源和内容确定性生成。确认后的 `item_id` 复用该 ID，并写入不影响渲染的来源锚点；后续解析优先从锚点恢复 ID，因此正文编辑不会改变条目身份。投影保存固定章节、章节内顺序和来源笔记 revision，但不会覆盖用户之后的人工修改。

完整文档/条目双模式使用以下端点：

- `GET .../note/items` 自动解析当前 Markdown，返回候选、警告、待审阅数量，以及确认条目的当前片段、来源指纹和 `synced`、`review_required` 或 `missing` 状态；
- `PUT .../note/items/{item_id}` 同时校验两份 revision 与来源指纹，只替换该稳定锚点对应片段，再保存 Markdown 和论文 YAML 投影；
- 外部 Markdown 修改由 `parse-note` 返回 `new`、`modified` 或 `unchanged` 候选，`import-candidates` 只同步用户明确选择的新增或修改候选，并返回新增及已同步条目 ID。

### 关系和研究空白

- `GET/PUT /projects/{project_id}/relations`
- `GET/POST /projects/{project_id}/research-gaps`
- `PATCH/DELETE /projects/{project_id}/research-gaps/{gap_id}`

阶段 4 实现时按 `docs/17-analysis-core.md` 将上述初始占位契约细化为分析集合、分类、关系、主张、研究空白和综合分析资源。每个垂直切片落地前必须先同步 `contracts/openapi.yaml`、Schema、前端类型和测试，未实现端点不得仅凭本文档视为可用。

阶段 4A/4B 还需要在实现切片中增加以下资源，但本设计更新不把未实现端点写入当前运行时 OpenAPI：

- 个人补充笔记读取与带 revision 保存；
- 完整笔记的项目级稳定跳转解析；
- 项目级条目关系 CRUD、反向引用和悬空引用诊断；
- 问题归纳板、领域问题及论文贡献 CRUD；
- 以领域问题为行、每篇论文含“方法/解决程度”两个子列的归纳矩阵查询。

问题归纳写接口必须分别接收方法条目和解决程度/理由，不得把自由显示文本当成唯一来源；所有目标 paper/item ID 必须限定在当前项目内。

目标资源：

- `GET/POST /projects/{project_id}/analysis-scopes`
- `GET/PATCH/DELETE /projects/{project_id}/analysis-scopes/{scope_id}`
- `GET/PUT /projects/{project_id}/taxonomies`
- `GET/POST/PATCH/DELETE /projects/{project_id}/relations`
- `GET/POST /projects/{project_id}/claims`
- `PATCH/DELETE /projects/{project_id}/claims/{claim_id}`
- `GET/POST /projects/{project_id}/research-gaps`
- `PATCH/DELETE /projects/{project_id}/research-gaps/{gap_id}`
- `GET/PUT /projects/{project_id}/syntheses/{scope_id}`

### 矩阵与导出

- `GET /projects/{project_id}/matrices/literature`
- `GET /projects/{project_id}/matrices/methods`
- `GET /projects/{project_id}/matrices/challenges`
- `GET /projects/{project_id}/matrices/experiments`
- `GET /projects/{project_id}/graphs/relations`
- `GET /projects/{project_id}/graphs/claims`
- `POST /projects/{project_id}/exports`
- `GET /projects/{project_id}/exports/{export_id}`

所有矩阵和图接口接收 `scope_id`，响应包含范围 revision、来源 revision、缺失论文和待补证据警告。图接口只返回当前筛选子图；不得把完整 1,000 篇项目图无条件传给前端。

## 4. 扫描与导入分离

扫描接口只返回候选，不写文件。导入接口只接收扫描结果中的受控 path token 或再次验证的路径。不要让客户端伪造任意路径绕过允许根验证。

单文件上传接口使用 multipart，但只在请求期读取元数据，不保存 PDF 字节；生成的记录为 `unlinked`。`link` 只接受允许根目录中的单个 PDF 绝对路径。`manual` 允许只用标题创建记录。

## 5. PDF 访问

MVP 可先使用系统默认 PDF 查看器打开源文件。若实现内置预览：

- 只允许通过已注册 `paper_id` 访问；
- 后端解析注册路径，不接受路径 query 参数；
- 支持 HTTP Range；
- 设置 `Content-Disposition: inline`；
- 禁止目录遍历和 MIME 嗅探。

## 6. 幂等性

- 项目创建可接受客户端生成的 `request_id`；
- 重复导入同一路径应返回已有记录或明确冲突，不创建重复 YAML；
- 导出请求可根据内容 hash 生成新快照，也可由用户选择覆盖同名文件；默认不覆盖。
