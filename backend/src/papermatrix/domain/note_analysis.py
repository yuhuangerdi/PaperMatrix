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
    superseded_item_ids: list[UUID] = Field(default_factory=list)


class NoteAnalysisRemoval(BaseModel):
    item_id: UUID
    kind: AnalysisItemKind
    title: str = Field(min_length=1, max_length=300)
    section_key: str | None = Field(default=None, max_length=40)
    section_title: str | None = Field(default=None, max_length=300)
    section_order: int | None = Field(default=None, ge=1)


class NoteParsePreview(BaseModel):
    paper_id: UUID
    note_revision: int = Field(ge=0)
    paper_revision: int = Field(ge=1)
    candidates: list[NoteAnalysisCandidate]
    removals: list[NoteAnalysisRemoval] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CandidateImportResult(BaseModel):
    analysis: PaperAnalysisDocument
    note: PaperNote
    imported_items: list[AnalysisItem]
    synchronized_items: list[AnalysisItem]
    skipped_candidate_ids: list[UUID]
    superseded_item_ids: list[UUID] = Field(default_factory=list)
    deleted_item_ids: list[UUID] = Field(default_factory=list)


class NoteItemSource(BaseModel):
    item_id: UUID
    kind: AnalysisItemKind
    display_label: str | None
    title: str
    section_key: str | None
    section_title: str | None
    section_order: int | None
    markdown: str
    source_fingerprint: str | None
    sync_status: Literal["synced", "review_required", "missing"]
    is_favorite: bool


class NoteItemTemplate(BaseModel):
    template_key: str = Field(max_length=40)
    chapter: int = Field(ge=1, le=8)
    kind: AnalysisItemKind
    label: str = Field(max_length=120)
    description: str = Field(default="", max_length=300)
    heading: str = Field(default="", max_length=300)
    heading_level: Literal[2, 3, 4] = 3
    repeatable: bool = False
    child_heading_prefix: str = Field(default="", max_length=80)
    insert_before_heading: str | None = Field(default=None, max_length=300)
    body_template: str = Field(default="", max_length=20_000)


class NoteItemSlot(BaseModel):
    slot_key: str = Field(max_length=80)
    template_key: str = Field(max_length=40)
    kind: AnalysisItemKind
    label: str = Field(max_length=120)
    description: str = Field(default="", max_length=300)
    section_title: str = Field(max_length=300)
    markdown: str = Field(default="", max_length=200_000)
    item_id: UUID | None = None
    source_fingerprint: str | None = None
    sync_status: Literal["empty", "synced", "review_required", "missing"]
    is_favorite: bool = False
    repeatable: bool = False
    repeatable_template_key: str | None = Field(default=None, max_length=40)
    can_delete: bool = False


class NoteItemDocument(BaseModel):
    paper_id: UUID
    note_revision: int = Field(ge=0)
    paper_revision: int = Field(ge=1)
    item_templates: list[NoteItemTemplate]
    slots: list[NoteItemSlot]
    evidence_catalog: list[EvidenceReference]
    items: list[NoteItemSource]
    candidates: list[NoteAnalysisCandidate]
    removals: list[NoteAnalysisRemoval] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    pending_candidate_count: int = Field(ge=0)


class NoteItemUpdateResult(BaseModel):
    note: PaperNote
    analysis: PaperAnalysisDocument
    item: AnalysisItem


class NoteSlotUpdateResult(BaseModel):
    note: PaperNote
    analysis: PaperAnalysisDocument
    slot: NoteItemSlot
    item: AnalysisItem | None = None


class EvidenceCreateResult(BaseModel):
    note: PaperNote
    analysis: PaperAnalysisDocument
    evidence: EvidenceReference
    item: AnalysisItem | None = None


class NoteItemFavoriteUpdateResult(BaseModel):
    analysis: PaperAnalysisDocument
    item: AnalysisItem


class NoteItemDeleteResult(BaseModel):
    note: PaperNote
    analysis: PaperAnalysisDocument
    deleted_item_ids: list[UUID]
    deleted_slot_keys: list[str] = Field(default_factory=list)
