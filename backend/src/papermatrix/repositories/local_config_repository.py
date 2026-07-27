"""Atomic local application configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from papermatrix.core.atomic_io import atomic_write_yaml
from papermatrix.core.errors import SchemaValidationError


def _validate_local_config(data: dict[str, Any]) -> None:
    if set(data) != {"workspace_root"} or not isinstance(data["workspace_root"], str):
        raise SchemaValidationError("本地配置格式无效。")


class LocalConfigRepository:
    def __init__(self, path: Path) -> None:
        self._path = path

    def save_workspace_root(self, root: Path) -> None:
        atomic_write_yaml(
            self._path,
            {"workspace_root": str(root)},
            validator=_validate_local_config,
        )
