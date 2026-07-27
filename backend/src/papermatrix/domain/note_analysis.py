"""Models for reviewing analysis candidates parsed from a paper note."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from papermatrix.domain.paper import AnalysisItem, AnalysisItemKind, PaperAnalysisDocument
from papermatrix.domain.paper_content import EvidenceReference, PaperNote


class NoteAnalysisCandidate(BaseModel):
    candidate_id: UUID
    kind: AnalysisItemKind
    title: str = Field(min_length=1, max_length=300)
    summary: str = Field(default="", max_length=20000)
    attributes: dict[str, str] = Field(default_factory=dict)
    evidence_refs: list[EvidenceReference] = Field(default_factory=list)
    section_key: str = Field(max_length=40)
    section_title: str = Field(max_length=300)
    section_order: int = Field(ge=1)
    source_anchor: str = Field(max_length=80)
    source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    sync_status: Literal["new", "unchanged", "modified"] = "new"
    source_section: str = Field(max_length=300)
    source_line_start: int = Field(ge=1)
    source_line_end: int = Field(ge=1)
    duplicate_item_id: UUID | None = None


class NoteParsePreview(BaseModel):
    paper_id: UUID
    note_revision: int = Field(ge=0)
    paper_revision: int = Field(ge=1)
    candidates: list[NoteAnalysisCandidate]
    warnings: list[str] = Field(default_factory=list)


class CandidateImportResult(BaseModel):
    analysis: PaperAnalysisDocument
    note: PaperNote
    imported_items: list[AnalysisItem]
    synchronized_items: list[AnalysisItem]
    skipped_candidate_ids: list[UUID]


class NoteItemSource(BaseModel):
    item_id: UUID
    kind: AnalysisItemKind
    title: str
    section_key: str | None
    section_title: str | None
    section_order: int | None
    markdown: str
    source_fingerprint: str | None
    sync_status: Literal["synced", "review_required", "missing"]


class NoteItemDocument(BaseModel):
    paper_id: UUID
    note_revision: int = Field(ge=0)
    paper_revision: int = Field(ge=1)
    items: list[NoteItemSource]
    candidates: list[NoteAnalysisCandidate]
    warnings: list[str] = Field(default_factory=list)
    pending_candidate_count: int = Field(ge=0)


class NoteItemUpdateResult(BaseModel):
    note: PaperNote
    analysis: PaperAnalysisDocument
    item: AnalysisItem
