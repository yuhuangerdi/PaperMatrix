"""Stable domain errors exposed by the API."""

from __future__ import annotations

from typing import Any


class PaperMatrixError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int,
        action: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.action = action
        self.details = details or {}


class WorkspaceNotInitializedError(PaperMatrixError):
    def __init__(self) -> None:
        super().__init__(
            "PM-CONFIG-001",
            "工作区尚未初始化。",
            status_code=400,
            action="请先完成工作区设置。",
        )


class WorkspaceCorruptedError(PaperMatrixError):
    def __init__(self, *, reason: str) -> None:
        super().__init__(
            "PM-CONFIG-002",
            "工作区配置损坏, 未执行覆盖。",
            status_code=422,
            action="请检查 workspace.yaml 或从备份恢复。",
            details={"reason": reason},
        )


class InvalidPathError(PaperMatrixError):
    def __init__(self, message: str = "路径格式无效。") -> None:
        super().__init__(
            "PM-PATH-001",
            message,
            status_code=400,
            action="请检查输入的路径。",
        )


class PathOutsideAllowedRootsError(PaperMatrixError):
    def __init__(self) -> None:
        super().__init__(
            "PM-PATH-002",
            "路径不在已允许的论文目录中。",
            status_code=403,
            action="请在设置中添加论文根目录。",
        )


class SymlinkEscapeError(PaperMatrixError):
    def __init__(self) -> None:
        super().__init__(
            "PM-PATH-003",
            "符号链接指向了允许目录之外。",
            status_code=403,
            action="请选择允许目录中的真实文件。",
        )


class PathNotFoundError(PaperMatrixError):
    def __init__(self) -> None:
        super().__init__(
            "PM-PATH-004",
            "路径不存在。",
            status_code=404,
            action="请修正路径或重新关联文件。",
        )


class PathAccessError(PaperMatrixError):
    def __init__(self, message: str, *, action: str) -> None:
        super().__init__(
            "PM-PATH-005",
            message,
            status_code=403,
            action=action,
        )


class FileContentError(PaperMatrixError):
    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            "PM-FILE-001",
            message,
            status_code=422,
            action="请修复文件内容后重试。",
            details=details,
        )


class SchemaValidationError(PaperMatrixError):
    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            "PM-FILE-002",
            message,
            status_code=422,
            action="请修复不符合规范的字段。",
            details=details,
        )


class FileLockTimeoutError(PaperMatrixError):
    def __init__(self) -> None:
        super().__init__(
            "PM-FILE-003",
            "文件正被另一个操作使用。",
            status_code=423,
            action="请稍后重试或关闭其他编辑页面。",
        )


class RevisionConflictError(PaperMatrixError):
    def __init__(self, *, expected: int, actual: int) -> None:
        super().__init__(
            "PM-CONFLICT-001",
            "文件已被其他操作修改。",
            status_code=409,
            action="请重新加载并合并更改。",
            details={"expected_revision": expected, "actual_revision": actual},
        )


class ProjectNotFoundError(PaperMatrixError):
    def __init__(self) -> None:
        super().__init__(
            "PM-PROJECT-001",
            "项目不存在。",
            status_code=404,
            action="请返回项目列表并刷新。",
        )


class ProjectConflictError(PaperMatrixError):
    def __init__(self, message: str = "项目名称已存在。") -> None:
        super().__init__(
            "PM-PROJECT-002",
            message,
            status_code=409,
            action="请修改项目名称后重试。",
        )


class ProjectNotEmptyError(PaperMatrixError):
    def __init__(self) -> None:
        super().__init__(
            "PM-PROJECT-003",
            "项目包含论文或其他业务文件, 不能删除。",
            status_code=409,
            action="请先移除项目中的论文记录和分析数据, 或将项目归档。",
        )


class PaperNotFoundError(PaperMatrixError):
    def __init__(self) -> None:
        super().__init__(
            "PM-PAPER-001",
            "论文记录不存在。",
            status_code=404,
            action="请刷新论文列表。",
        )


class PaperConflictError(PaperMatrixError):
    def __init__(self, message: str = "该 PDF 已在项目中登记。") -> None:
        super().__init__(
            "PM-PAPER-002",
            message,
            status_code=409,
            action="请打开已有记录或选择其他文件。",
        )


class PaperUploadTooLargeError(PaperMatrixError):
    def __init__(self, maximum: int) -> None:
        super().__init__(
            "PM-PAPER-005",
            "上传的 PDF 超过单文件读取上限。",
            status_code=413,
            action="请改用允许目录中的文件路径登记。",
            details={"max_bytes": maximum},
        )


class QuestionNotFoundError(PaperMatrixError):
    def __init__(self) -> None:
        super().__init__(
            "PM-QUESTION-001",
            "问题记录不存在。",
            status_code=404,
            action="请刷新问题列表。",
        )


class AnalysisItemNotFoundError(PaperMatrixError):
    def __init__(self) -> None:
        super().__init__(
            "PM-ANALYSIS-001",
            "分析条目不存在。",
            status_code=404,
            action="请刷新论文分析条目。",
        )


class AnalysisPreviewStaleError(PaperMatrixError):
    def __init__(self, *, resource: str, expected: int, actual: int) -> None:
        super().__init__(
            "PM-ANALYSIS-002",
            "候选预览对应的内容已经更新。",
            status_code=409,
            action="请重新解析笔记并再次审阅候选。",
            details={
                "resource": resource,
                "expected_revision": expected,
                "actual_revision": actual,
            },
        )


class AnalysisCandidateSelectionError(PaperMatrixError):
    def __init__(self, unknown_ids: list[str]) -> None:
        super().__init__(
            "PM-ANALYSIS-003",
            "提交的候选条目不属于当前解析结果。",
            status_code=422,
            action="请重新解析笔记后再确认。",
            details={"unknown_candidate_ids": unknown_ids},
        )
