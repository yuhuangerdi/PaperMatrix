"""Reproducible project-level paper analysis scopes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator


class AnalysisScope(BaseModel):
    scope_id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=120)
    purpose: str = Field(default="", max_length=5000)
    paper_ids: list[UUID] = Field(min_length=1)
    source_filter_snapshot: dict[str, str] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def paper_ids_must_be_unique(self) -> AnalysisScope:
        if len(self.paper_ids) != len(set(self.paper_ids)):
            raise ValueError("analysis scope paper IDs must be unique")
        return self

    @classmethod
    def create(
        cls,
        *,
        name: str,
        purpose: str,
        paper_ids: list[UUID],
        source_filter_snapshot: dict[str, str],
    ) -> AnalysisScope:
        now = datetime.now(UTC)
        return cls(
            name=name.strip(),
            purpose=purpose.strip(),
            paper_ids=list(dict.fromkeys(paper_ids)),
            source_filter_snapshot={
                key: value for key, value in source_filter_snapshot.items() if value
            },
            created_at=now,
            updated_at=now,
        )

    def update(
        self,
        *,
        name: str,
        purpose: str,
        paper_ids: list[UUID],
        source_filter_snapshot: dict[str, str],
    ) -> AnalysisScope:
        return self.model_copy(
            update={
                "name": name.strip(),
                "purpose": purpose.strip(),
                "paper_ids": list(dict.fromkeys(paper_ids)),
                "source_filter_snapshot": {
                    key: value for key, value in source_filter_snapshot.items() if value
                },
                "updated_at": datetime.now(UTC),
            }
        )


class AnalysisScopesDocument(BaseModel):
    schema_version: Literal[1] = 1
    project_id: UUID
    revision: int = Field(ge=0)
    updated_at: datetime
    scopes: list[AnalysisScope] = Field(default_factory=list)

    @model_validator(mode="after")
    def scope_ids_must_be_unique(self) -> AnalysisScopesDocument:
        ids = [scope.scope_id for scope in self.scopes]
        if len(ids) != len(set(ids)):
            raise ValueError("analysis scope IDs must be unique")
        return self

    @classmethod
    def empty(cls, project_id: UUID) -> AnalysisScopesDocument:
        return cls(project_id=project_id, revision=0, updated_at=datetime.now(UTC))


class AnalysisScopeView(BaseModel):
    scope: AnalysisScope
    available_paper_ids: list[UUID]
    missing_paper_ids: list[UUID]


class AnalysisScopesViewDocument(BaseModel):
    document: AnalysisScopesDocument
    scopes: list[AnalysisScopeView]
