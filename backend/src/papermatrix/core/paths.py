"""Central path validation for workspace and read-only PDF access."""

from __future__ import annotations

import os
from pathlib import Path

from papermatrix.core.errors import (
    InvalidPathError,
    PathAccessError,
    PathNotFoundError,
    PathOutsideAllowedRootsError,
    SymlinkEscapeError,
)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


class PathPolicy:
    def __init__(self, allowed_roots: tuple[Path, ...]) -> None:
        self._allowed_roots = tuple(
            root.expanduser().resolve(strict=False) for root in allowed_roots
        )

    @property
    def allowed_roots(self) -> tuple[Path, ...]:
        return self._allowed_roots

    def validate_pdf(self, raw_path: str | Path) -> Path:
        if not self._allowed_roots:
            raise PathOutsideAllowedRootsError()

        candidate = Path(raw_path).expanduser()
        if not candidate.is_absolute():
            raise InvalidPathError("论文路径必须是绝对路径。")

        lexical_path = Path(os.path.abspath(candidate))
        lexical_root = next(
            (root for root in self._allowed_roots if _is_within(lexical_path, root)),
            None,
        )
        if lexical_root is None:
            raise PathOutsideAllowedRootsError()
        if not candidate.exists():
            raise PathNotFoundError()

        real_path = candidate.resolve(strict=True)
        if not _is_within(real_path, lexical_root):
            raise SymlinkEscapeError()
        if not real_path.is_file() or real_path.suffix.lower() != ".pdf":
            raise InvalidPathError("只允许读取 PDF 文件。")
        return real_path

    def validate_scan_directory(self, raw_path: str | Path) -> Path:
        if not self._allowed_roots:
            raise PathOutsideAllowedRootsError()
        candidate = Path(raw_path).expanduser()
        if not candidate.is_absolute():
            raise InvalidPathError("扫描目录必须是绝对路径。")
        lexical_path = Path(os.path.abspath(candidate))
        lexical_root = next(
            (root for root in self._allowed_roots if _is_within(lexical_path, root)),
            None,
        )
        if lexical_root is None:
            raise PathOutsideAllowedRootsError()
        if not candidate.exists():
            raise PathNotFoundError()
        real_path = candidate.resolve(strict=True)
        if not _is_within(real_path, lexical_root):
            raise SymlinkEscapeError()
        if not real_path.is_dir():
            raise InvalidPathError("扫描路径必须是目录。")
        return real_path

    @staticmethod
    def validate_workspace_destination(raw_path: str | Path) -> Path:
        candidate = Path(raw_path).expanduser()
        if not candidate.is_absolute():
            raise InvalidPathError("工作区路径必须是绝对路径。")

        normalized = candidate.resolve(strict=False)
        if candidate.exists():
            real_path = candidate.resolve(strict=True)
            if not real_path.is_dir():
                raise InvalidPathError("工作区路径必须是目录。")
            if not os.access(real_path, os.R_OK | os.W_OK | os.X_OK):
                raise PathAccessError(
                    "工作区目录不可读写。",
                    action="请选择具有读写权限的目录。",
                )
            return real_path

        parent = normalized.parent
        while not parent.exists() and parent != parent.parent:
            parent = parent.parent
        if not parent.is_dir() or not os.access(parent, os.W_OK | os.X_OK):
            raise PathAccessError(
                "无法创建工作区目录。",
                action="请选择具有写权限的上级目录。",
            )
        return normalized

    @staticmethod
    def validate_paper_root(raw_path: str | Path) -> Path:
        candidate = Path(raw_path).expanduser()
        if not candidate.is_absolute():
            raise InvalidPathError("论文根目录必须是绝对路径。")
        if not candidate.exists():
            raise PathNotFoundError()
        real_path = candidate.resolve(strict=True)
        if not real_path.is_dir():
            raise InvalidPathError("论文根路径必须是目录。")
        if not os.access(real_path, os.R_OK | os.X_OK):
            raise PathAccessError(
                "论文根目录不可读取。",
                action="请选择具有读取权限的目录。",
            )
        return real_path

    @staticmethod
    def redact(path: Path) -> str:
        parts = path.parts
        if len(parts) <= 2:
            return path.name
        return str(Path("…") / parts[-2] / parts[-1])
