"""Workspace domain model."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class WorkspaceSettings(BaseModel):
    language: Literal["zh-CN", "en-US"] = "zh-CN"
    default_export_format: Literal["xlsx", "csv"] = "xlsx"
    strict_hashing: bool = False


class Workspace(BaseModel):
    schema_version: Literal[1] = 1
    workspace_id: UUID
    name: str = Field(min_length=1, max_length=120)
    created_at: datetime
    updated_at: datetime
    revision: int = Field(ge=1)
    allowed_paper_roots: list[str]
    settings: WorkspaceSettings

    @classmethod
    def create(cls, name: str, allowed_roots: tuple[Path, ...]) -> Workspace:
        now = datetime.now(UTC)
        return cls(
            workspace_id=uuid4(),
            name=name,
            created_at=now,
            updated_at=now,
            revision=1,
            allowed_paper_roots=[str(path.resolve(strict=False)) for path in allowed_roots],
            settings=WorkspaceSettings(),
        )

    def update(self, *, name: str, allowed_roots: tuple[Path, ...]) -> Workspace:
        return self.model_copy(
            update={
                "name": name,
                "allowed_paper_roots": [str(path) for path in allowed_roots],
                "updated_at": datetime.now(UTC),
                "revision": self.revision + 1,
            }
        )
