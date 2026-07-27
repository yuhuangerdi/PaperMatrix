"""Locked, validated, atomic YAML and Markdown file operations."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from filelock import FileLock, Timeout

from papermatrix.core.errors import (
    FileContentError,
    FileLockTimeoutError,
    RevisionConflictError,
)

Validator = Callable[[dict[str, Any]], None]


def read_yaml(path: Path, validator: Validator | None = None) -> dict[str, Any]:
    try:
        parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise FileContentError(
            "无法读取 YAML 文件。",
            details={"file": path.name, "reason": str(exc)},
        ) from exc
    if not isinstance(parsed, dict):
        raise FileContentError("YAML 顶层必须是对象。", details={"file": path.name})
    if validator is not None:
        validator(parsed)
    return parsed


def _atomic_replace(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        if hasattr(os, "O_DIRECTORY"):
            directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        temporary_path.unlink(missing_ok=True)


def atomic_write_yaml(
    path: Path,
    data: dict[str, Any],
    *,
    validator: Validator,
    expected_revision: int | None = None,
    lock_timeout: float = 5.0,
) -> None:
    validator(data)
    lock = FileLock(str(path.with_suffix(f"{path.suffix}.lock")), timeout=lock_timeout)
    try:
        with lock:
            if expected_revision is not None:
                actual_revision = 0
                if path.exists():
                    current = read_yaml(path, validator)
                    actual_revision = int(current.get("revision") or 0)
                if actual_revision != expected_revision:
                    raise RevisionConflictError(
                        expected=expected_revision,
                        actual=actual_revision,
                    )
            serialized = yaml.safe_dump(
                data,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
            )
            _atomic_replace(path, serialized)
    except Timeout as exc:
        raise FileLockTimeoutError() from exc


def read_markdown(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise FileContentError(
            "无法读取 Markdown 文件。",
            details={"file": path.name, "reason": str(exc)},
        ) from exc


def atomic_write_markdown(
    path: Path,
    content: str,
    *,
    expected_revision: int | None = None,
    revision_reader: Callable[[str], int] | None = None,
    lock_timeout: float = 5.0,
) -> None:
    lock = FileLock(str(path.with_suffix(f"{path.suffix}.lock")), timeout=lock_timeout)
    try:
        with lock:
            if expected_revision is not None:
                actual_revision = 0
                if path.exists():
                    if revision_reader is None:
                        raise ValueError("revision_reader is required for revision checks")
                    actual_revision = revision_reader(read_markdown(path))
                if actual_revision != expected_revision:
                    raise RevisionConflictError(
                        expected=expected_revision,
                        actual=actual_revision,
                    )
            _atomic_replace(path, content)
    except Timeout as exc:
        raise FileLockTimeoutError() from exc
