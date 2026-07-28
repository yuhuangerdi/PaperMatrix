"""Derived literature-matrix and analysis-readiness models."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from papermatrix.domain.paper import ReadingStatus, SourceStatus


class AnalysisReadiness(BaseModel):
    method_ready: bool
    experiment_ready: bool
    limitation_ready: bool
    evidence_ready: bool
    ready_count: int = Field(ge=0, le=4)
    missing_categories: list[str]


class LiteratureMatrixRow(BaseModel):
    paper_id: UUID
    title: str
    short_title: str
    authors: list[str]
    year: int | None
    venue: str | None
    group: str | None
    reading_status: ReadingStatus
    source_status: SourceStatus
    importance_score: int | None
    one_sentence_summary: str
    keywords: list[str]
    background: list[str]
    research_problems: list[str]
    related_work: list[str]
    methods: list[str]
    challenges: list[str]
    innovations: list[str]
    experiments: list[str]
    findings: list[str]
    limitations: list[str]
    conditions: list[str]
    evidence_count: int = Field(ge=0)
    readiness: AnalysisReadiness
    revision: int = Field(ge=1)


class LiteratureMatrix(BaseModel):
    project_id: UUID
    scope_id: UUID | None = None
    scope_name: str | None = None
    rows: list[LiteratureMatrixRow]
    missing_paper_ids: list[UUID]
    total: int = Field(ge=0)
