# 文件系统与数据模型

## 1. 工作区布局

```text
<workspace-root>/
├── workspace.yaml
├── projects/
│   └── <project-id>/
│       ├── project.yaml
│       ├── papers/
│       │   └── <paper-id>.yaml
│       ├── notes/
│       │   ├── <paper-id>.md
│       │   └── <paper-id>.supplement.md
│       ├── questions/               # 阶段 3
│       │   └── <paper-id>.yaml
│       ├── analyses/                # 阶段 4 项目级权威分析
│       │   ├── scopes.yaml
│       │   ├── item-links.yaml
│       │   ├── problem-syntheses.yaml
│       │   ├── taxonomies.yaml
│       │   ├── relations.yaml
│       │   ├── claims.yaml
│       │   ├── research-gaps.yaml
│       │   ├── views.yaml
│       │   └── syntheses/
│       │       └── <scope-id>.md
│       ├── artifacts/
│       │   └── matrices/            # 可重新生成的内部派生文件
│       └── exports/
└── .papermatrix/
    ├── locks/
    └── diagnostics/
```

说明：

- `papers/*.yaml` 与 `notes/*.md` 是核心权威数据；
- `analyses/` 下的范围、分类、关系、主张、研究空白和综合分析是项目级权威文件；
- XLSX/CSV 是可重新生成的派生文档；
- `exports/` 保存用户主动导出的快照；
- `.papermatrix/locks` 只保存运行锁，不保存业务数据库或隐蔽缓存。

## 2. workspace.yaml

关键字段：

- `schema_version`
- `workspace_id`
- `name`
- `created_at`
- `updated_at`
- `allowed_paper_roots`
- `settings`

`allowed_paper_roots` 是后端可读取 PDF 的目录白名单。工作区移动后，支持更新根路径。

## 3. project.yaml

关键字段：

- `project_id`
- `name`
- `slug`
- `topic`
- `description`
- `tags`
- `status`
- `created_at`
- `updated_at`
- `revision`

项目 ID 使用 UUID，不以目录名作为身份。slug 仅用于可读路径，可在冲突时追加短 ID。

## 4. paper.yaml（当前 schema_version: 8）

论文文件保存：

### 身份和来源

- `paper_id`
- `project_id`
- `source.path`：可为空；为空表示论文记录尚未关联可访问的原 PDF
- `source.path_mode`：absolute、workspace_relative 或 null
- `source.original_filename`：单文件读取时保留的原文件名，可为空
- `source.size_bytes`、`source.modified_at`、`source.fingerprint`：来源观测值，可为空
- `source.status`：available、missing、changed、unreadable、unlinked

指纹建议：默认 `size + mtime_ns` 快速指纹；用户要求严格去重时可计算 SHA-256。严禁修改源 PDF。

浏览器上传只在请求期间读取 PDF 元数据和指纹，不把 PDF 写入工作区。由于浏览器不会提供可长期访问的绝对路径，此类记录保存 `source.path: null` 并标记 `unlinked`。v1–v6 记录读取时通过纯函数迁移到 v7 内存模型，后续正常保存时写回 v7；旧版松散结构化摘要、既有条目内容和来源字段保持不变。

### 书目信息

- `title`
- `short_title`
- `authors`
- `year`
- `venue`
- `affiliations`
- `publication_date`
- `citation_count`
- `language`
- `keywords`
- `abstract_text`
- `publication_type`
- `doi`
- `arxiv_id`
- `urls`
- `code_url`
- `data_url`

### 整理信息

- `topics`
- `tags`
- `group`：项目内论文分组，不改变原 PDF 的目录
- `reading_date`
- `reading_status`
- `priority`
- `importance_score`
- `confidence_score`
- `reproduction_value`
- `writing_uses`
- `one_sentence_summary`

### 老师要求的结构化摘要

- `background.problem`
- `background.importance`
- `background.scenario`
- `related_work.categories`
- `related_work.classic_papers`
- `approach.core_idea`
- `approach.framework`
- `challenges`
- `innovations`：3 项核心创新
- `additional_contribution`：+1
- `experiment.summary`
- `experiment.open_source`
- `experiment.open_data`

详细内容仍写入 Markdown 笔记，YAML 保存适合筛选和矩阵的摘要字段。

阶段 3 为阶段 4 准备的可分析条目保存在 `structured_summary.items[]`。阶段 4A 将该投影扩展为包含稳定 `item_id`、固定模板 `section_key`、章节内顺序、来源锚点、来源笔记 revision、`kind`、标题、摘要、结构化属性、标签、写作用途、时间戳和统一 `evidence_refs`。类型覆盖论文研究问题、场景、方法、组件、机制、挑战、创新、贡献、实验研究问题、实验、发现、两类局限、成立条件和写作材料。

证据包含 `paper_id`、可选 `page_label`、从 1 开始的 `pdf_page_index`、章节、图、表、定位说明和来源条目 ID。缺少证据允许保存，但状态必须可被矩阵识别为待补证据。Markdown 解析候选不是权威数据，只有用户确认后才创建 `item_id` 并进入本数组。

## 5. note.md

使用 YAML front matter：

```markdown
---
schema_version: 1
paper_id: "..."
revision: 1
updated_at: "2026-07-26T10:00:00Z"
template_version: 1
---

# 论文简称
...
```

Markdown 正文遵循 `templates/paper-note-template.md`。保存时不应重排用户无关段落。

论文登记时立即创建 revision 1 的默认笔记，并仅在这次创建中把已有书目信息写入第 0 节。后续论文基础信息编辑与 Markdown 分别维护，不能覆盖用户已经修改的笔记；旧记录缺少笔记文件时仍可按 revision 0 的兼容流程首次保存。

结构化笔记始终保留模板第 0–12 节和完整、连续的 Markdown，不为每个条目创建单独文件。经确认条目在 Markdown 中具有不影响正常渲染的 `<!-- papermatrix:item:<uuid> -->` 稳定来源锚点；标记统一位于语义标题前，标题下的段落、列表、键值和整张表格属于同一条目。2.2 代表性文献使用三级父标题作为唯一条目边界，四级文献标题保留为内部结构。Markdown 正文和顺序为权威内容，`paper.yaml` 中的条目是可重建、经确认的检索与分析投影。

完整文档模式和条目模式编辑同一份 Markdown。条目更新根据稳定锚点只替换对应标题区块，保留标记、其他章节、空行和段落顺序。旧版本已经按表格行或 2.2 四级文献确认的投影在读取时保持可诊断；用户确认新的组合候选后，服务端移除旧锚点、合并人工标签/写作用途/证据，并以父标题块条目替换旧投影。投影记录来源笔记 revision 及来源片段 SHA-256 指纹；指纹或 revision 不一致时进入候选审阅或待同步状态。正文删除会形成待确认删除项，不会静默删除投影；条目模式的单条或批量删除会同时删除对应 Markdown 标题块和投影。确认条目的 `is_favorite` 是本地阅读视图的重点收藏状态，保存在同一条目投影中，不写入 Markdown；重解析、正文同步和旧条目合并均保持该状态。

### 5.1 supplement.md

`notes/<paper-id>.supplement.md` 保存个人自由笔记，使用与主笔记相同的 front matter 基础字段、revision、文件锁和原子替换。它不使用固定模板，不直接进入矩阵；用户可把其中内容手动整理进结构化笔记。导出时可以把两份 Markdown 合并为快照，但不能回写或覆盖任一源文件。

## 6. scopes.yaml（阶段 4）

本节至 `views.yaml` 描述阶段 4 的目标模型。对应 JSON Schema、迁移和运行时代码将在 4A–4E 各垂直切片中同步落地；在此之前以 `contracts/schemas/` 的当前版本为运行时契约。

保存项目内分析集合。每个集合至少包含：

- `scope_id`
- `name`
- `purpose`
- `paper_ids`
- `source_filter_snapshot`
- `created_at`
- `updated_at`

保存时固定解析出的论文 ID 以保证可复现。论文记录消失后保留缺失 ID，不自动改变分析范围。

## 7. taxonomies.yaml（阶段 4）

保存用户维护的方法/问题分类及论文归类：

- 分类名称、定义、纳入条件、排除条件和父分类；
- 论文归类、说明和证据引用；
- 分类与归类使用稳定 ID。

## 7A. item-links.yaml（阶段 4A）

保存同一论文或不同论文中两个结构化条目之间的有向关系。文档包含 `schema_version`、`project_id`、`revision` 和 `links[]`。每条至少包含 `link_id`、来源 paper/item、目标 paper/item、固定关系类型、描述和时间戳。

关系类型为 `addresses`、`partially_addresses`、`depends_on`、`enables`、`evaluates`、`supports`、`contradicts`、`extends`、`related_to`。删除被引用条目时保留悬空引用并标记缺失，不能静默删除跨论文判断。

## 7B. problem-syntheses.yaml（阶段 4B）

保存：

- `boards[]`：问题归纳板，包含 `board_id`、名称、目的、`scope_id`、领域问题顺序和论文显示顺序；
- `field_problems[]`：领域问题，包含稳定 ID、定义、范围、别名、标签、状态和来源论文研究问题条目；
- `paper_contributions[]`：领域问题与论文的贡献记录。

每条论文贡献至少包含 `contribution_id`、`problem_id`、`paper_id`、问题条目 ID、方法条目 ID、实验条目 ID、`resolution_level`、判断理由、支持证据、反证、成立条件和用户判断。

解决程度为 `resolved`、`partially_resolved`、`indirectly_mitigated`、`not_resolved`、`not_addressed`、`not_applicable`、`unknown`。其中 `not_resolved` 表示尝试但未解决，`not_addressed` 表示论文未涉及。方法和解决程度在界面中分为两个单元格，但共同写回同一贡献记录。

`questions/<paper-id>.yaml` 中的阅读问题不属于本文件。只有结构化笔记中的 `research_problem` 条目可以直接映射到领域问题。

## 8. relations.yaml

顶层：

- `schema_version`
- `project_id`
- `revision`
- `relations[]`

关系字段：

- `relation_id`
- `source_paper_id`
- `target_paper_id`
- `type`
- `description`
- `evidence_refs`
- `created_at`
- `updated_at`

关系是有向的；“使用相同数据集”等可在 UI 中表现为对称，但文件仍保存一个标准方向，避免重复。

## 9. claims.yaml（阶段 4）

每条跨论文主张字段：

- `claim_id`
- `statement`
- `kind`：consensus、dispute、hypothesis
- `scope_id`
- `scope_note`
- `supporting_evidence`
- `contradicting_evidence`
- `assessment`
- `confidence`
- `status`
- `created_at`
- `updated_at`

“共识”至少有两篇独立论文的支持证据。主张是用户确认的项目级判断，不从矩阵数字自动生成。

## 10. questions.yaml（阶段 3）

每篇论文的问题清单独立保存到 `questions/<paper-id>.yaml`。文档包含 `schema_version`、`paper_id`、`revision` 和 `questions[]`；尚未落盘时 API 返回 revision 0，首次保存后从 revision 1 开始。每个问题包含稳定 `question_id`、问题正文、open/answered/deferred 状态、回答、标签和时间戳；answered 状态必须填写回答。

每条证据使用稳定 `evidence_id`，可记录印刷页码、从 0 开始的 PDF 页序号、章节、图号、表号、定位说明和未来分析条目的 `source_item_id`。证据的 `paper_id` 固定为当前论文。该文件是问题清单的权威来源，笔记只保留需要长篇展开的问题索引，Excel 不重复维护问题答案。

## 11. research-gaps.yaml

每条研究空白字段：

- `gap_id`
- `title`
- `status`
- `problem_statement`
- `scope_id`
- `supporting_evidence`
- `counter_evidence`
- `current_approaches`
- `why_unsolved`
- `research_question`
- `potential_approach`
- `validation_plan`
- `failure_criteria`
- `feasibility`
- `risks`
- `notes`

## 12. views.yaml 与 syntheses（阶段 4）

`views.yaml` 只保存用户明确保存的分析视图，例如分析集合、启用关系类型、布局方式和固定节点位置；临时筛选不写入。

`syntheses/<scope-id>.md` 是用户编辑后的综合分析权威正文。重新生成默认创建预览或新版本，不能覆盖现有正文。

## 13. 权威与派生边界

- 单篇事实：`papers/*.yaml`
- 长篇解释：`notes/*.md`
- 个人补充笔记：`notes/*.supplement.md`
- 问题：`questions/*.yaml`
- 条目关系、领域问题、论文贡献、项目分类与跨篇判断：`analyses/*.yaml`
- 综合正文：`analyses/syntheses/*.md`
- 矩阵、图数据和内部缓存：按请求生成或位于 `artifacts/`
- 用户导出快照：`exports/`

矩阵内联编辑必须写回上述来源文件，禁止只修改派生 XLSX。

## 14. 路径存储规则

1. 先尝试保存相对于工作区或允许根目录的相对路径；
2. 无共同根时保存绝对路径；
3. Windows 路径比较不区分大小写，但原始显示保留；
4. 使用 `pathlib.Path.resolve(strict=False)` 规范化；
5. 对存在文件额外解析符号链接并验证真实路径仍在允许根；
6. API 不提供“读取任意路径”能力，只允许扫描已配置根或读取已注册论文。

## 15. 写入协议

- 写前 schema 校验；
- 获取逻辑资源锁；
- 检查 revision；
- 在同目录创建临时文件；
- 写入并刷新；
- 尽可能 fsync；
- `os.replace` 原子替换；
- 释放锁；
- 临时文件异常时清理。

不自动为 PDF 建备份。元数据可在未来提供可选版本历史，但不属于 MVP。

## 16. 外部编辑

用户可以直接编辑 YAML/Markdown，但应用必须：

- 检测文件 mtime/revision 变化；
- 重新验证后加载；
- 解析失败时展示错误位置并进入只读；
- 不用默认值静默覆盖未知字段；
- 尽量保留未知扩展字段，以支持向前兼容。
