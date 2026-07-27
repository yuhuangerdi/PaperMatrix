# Contributing

## 工作方式

1. 从一个明确的 `.codex-prompts/TASKS.md` 条目开始，并核对 `.codex-prompts/DESIGN.md` 中的对应工作流。
2. 先更新或确认契约与验收标准。
3. 用小而可审查的改动完成垂直切片。
4. 增加测试并运行完整验证。
5. 更新文档和 Changelog。

## 提交建议

采用 Conventional Commits，例如：

- `feat(projects): add file-backed project creation`
- `fix(storage): prevent symlink escape from allowed roots`
- `test(import): cover duplicate PDF registration`
- `docs(adr): record derived spreadsheet decision`

## 数据安全审查

任何涉及文件写入、删除、路径处理、导入和导出的改动必须回答：

- 会不会触碰源 PDF？
- 能否越过允许目录？
- 中断时是否可能留下半写文件？
- 并发操作是否会丢失数据？
- 是否有回归测试？
