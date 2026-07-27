# 后端设计规范

## 1. Python 包结构

采用 `src` 布局，`papermatrix` 为唯一顶级业务包。API、领域、服务、仓储和导出分层，不允许路由直接写 YAML。

## 2. 配置

使用 Pydantic Settings 或等价方案。配置来源优先级：环境变量 > 本地配置文件 > 安全默认值。

必要配置：

- host，默认 127.0.0.1；
- port；
- workspace root；
- allowed paper roots；
- log level；
- diagnostic mode；
- max scan files；
- max PDF size for metadata parsing。
- max single-upload bytes；上传仅瞬时解析，不持久化 PDF。

## 3. 路径安全

提供单一 `PathPolicy`：

- 规范化输入；
- 空路径和相对路径策略；
- 允许根判断；
- 符号链接解析；
- 文件类型检查；
- 只读打开；
- 对外脱敏显示。

不得在多个路由中复制路径判断逻辑。

## 4. 文件 I/O

提供：

- `read_yaml_validated(path, schema)`；
- `atomic_write_yaml(path, data, expected_revision)`；
- `read_markdown_with_frontmatter(path)`；
- `atomic_write_markdown(...)`；
- `resource_lock(resource_key)`。

临时文件必须位于目标文件同目录，保证原子替换语义。测试模拟写入中断。

结构化笔记与论文 YAML 投影同步时，服务层必须按固定顺序获取两个资源锁，在内存中同时完成 Markdown 与 YAML 校验，再分别原子替换。条目投影记录来源笔记 revision 和来源片段 SHA-256 指纹。条目写入必须校验稳定锚点、条目类型、两份 revision 与来源指纹，只替换锚点对应片段；部分写入失败时保留可诊断的待同步状态，不允许用旧投影覆盖较新 Markdown。

候选解析用当前片段指纹区分新增、未变化和外部修改。只有用户明确确认 `modified` 候选时才同步既有投影；同内容但不同锚点的重复候选不得借此覆盖已有条目。

## 5. Repository 契约

Repository 只接收已验证的项目标识和领域对象，不接收任意客户端路径。项目目录由 workspace repository 解析。

阶段 4A/4B 分别增加个人补充笔记、条目关系和问题归纳仓储。所有 paper/item/scope/problem 引用都必须验证属于当前项目；问题归纳矩阵由权威对象组装，不单独落盘为业务事实。

## 6. PDF 元数据

- 以二进制只读方式打开；
- 设置合理读取超时/大小限制；
- 解析异常不应阻止用户登记论文；
- 不执行 PDF 内脚本、附件或外部链接；
- 元数据仅作为候选，用户可修改；
- 不把 PDF 全文写入日志。

## 7. 删除安全

项目业务代码中禁止对 `paper.source.path` 调用 `unlink`、`remove`、`rmtree` 或 rename。可通过单元测试/静态检查确保。删除 PaperMatrix 记录时只允许删除解析出的项目内部路径。

## 8. 日志

- 每个请求有 request ID；
- INFO 记录资源 ID、操作类型、结果和耗时；
- 默认不记录论文完整路径、笔记正文和标题全文；
- ERROR 可记录异常类型和脱敏上下文；
- 诊断包需用户显式生成。

## 9. 错误映射

领域异常映射为稳定错误码：验证 400、未找到 404、冲突 409、路径禁止 403、文件损坏 422、锁超时 423、内部错误 500。

## 10. 测试结构

- unit：domain、path policy、atomic I/O、schema migration；
- repository：临时工作区真实文件测试；
- service：导入、重连、删除记录和导出；
- API：TestClient/httpx；
- property/fuzz（可选）：路径和 YAML 异常输入；
- e2e：真实启动后端并由前端测试访问。
