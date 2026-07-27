"""Paper records and source-state models."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from papermatrix.domain.paper_content import EvidenceReference

SourceStatus = Literal["available", "missing", "changed", "unreadable", "unlinked"]
ReadingStatus = Literal["unread", "skimmed", "deep_read", "summarized", "reported"]
WritingUse = Literal[
    "INTRO",
    "RELATED",
    "METHOD",
    "BASELINE",
    "DATASET",
    "METRIC",
    "LIMITATION",
    "DISCUSSION",
    "FUTURE",
]
AnalysisItemKind = Literal[
    "research_problem",
    "scenario",
    "method",
    "method_component",
    "mechanism",
    "challenge",
    "innovation",
    "contribution",
    "experiment",
    "finding",
    "author_limitation",
    "reviewer_limitation",
    "condition",
]


class PaperSource(BaseModel):
    path: str | None = None
    path_mode: Literal["absolute", "workspace_relative"] | None = None
    original_filename: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)
    modified_at: datetime | None = None
    fingerprint: str | None = None
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    page_count: int | None = Field(default=None, ge=1)
    status: SourceStatus


class Bibliography(BaseModel):
    title: str = Field(min_length=1, max_length=1000)
    short_title: str = Field(default="", max_length=200)
    authors: list[str] = Field(default_factory=list)
    affiliations: list[str] = Field(default_factory=list)
    year: int | None = Field(default=None, ge=1800, le=2200)
    venue: str | None = Field(default=None, max_length=300)
    publication_date: date | None = None
    citation_count: int | None = Field(default=None, ge=0)
    language: str | None = Field(default=None, max_length=50)
    keywords: list[str] = Field(default_factory=list)
    abstract_text: str = Field(default="", max_length=20000)
    publication_type: Literal["conference", "journal", "preprint", "thesis", "report", "other"] = (
        "other"
    )
    doi: str | None = None
    arxiv_id: str | None = None
    urls: list[str] = Field(default_factory=list)
    code_url: str | None = None
    data_url: str | None = None


class Organization(BaseModel):
    topics: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    group: str | None = Field(default=None, max_length=120)
    reading_date: date | None = None
    reading_status: ReadingStatus = "unread"
    priority: Literal["A", "B", "C", "D"] | None = None
    importance_score: int | None = Field(default=None, ge=1, le=5)
    confidence_score: int | None = Field(default=None, ge=1, le=5)
    reproduction_value: int | None = Field(default=None, ge=1, le=5)
    writing_uses: list[WritingUse] = Field(default_factory=list)
    one_sentence_summary: str = ""


class AnalysisItem(BaseModel):
    item_id: UUID = Field(default_factory=uuid4)
    kind: AnalysisItemKind
    title: str = Field(min_length=1, max_length=300)
    summary: str = Field(default="", max_length=20000)
    section_key: str | None = Field(default=None, max_length=40)
    section_title: str | None = Field(default=None, max_length=300)
    section_order: int | None = Field(default=None, ge=1)
    source_anchor: str | None = Field(default=None, max_length=80)
    source_note_revision: int | None = Field(default=None, ge=1)
    attributes: dict[str, str] = Field(default_factory=dict)
    evidence_refs: list[EvidenceReference] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    writing_uses: list[WritingUse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        kind: AnalysisItemKind,
        title: str,
        summary: str,
        attributes: dict[str, str],
        evidence_refs: list[EvidenceReference],
        tags: list[str],
        writing_uses: list[WritingUse],
    ) -> AnalysisItem:
        now = datetime.now(UTC)
        return cls(
            kind=kind,
            title=title.strip(),
            summary=summary.strip(),
            attributes=attributes,
            evidence_refs=evidence_refs,
            tags=tags,
            writing_uses=writing_uses,
            created_at=now,
            updated_at=now,
        )


class StructuredSummary(BaseModel):
    background: dict[str, object] = Field(default_factory=dict)
    related_work: dict[str, object] = Field(default_factory=dict)
    approach: dict[str, object] = Field(default_factory=dict)
    challenges: list[dict[str, object]] = Field(default_factory=list)
    innovations: list[dict[str, object]] = Field(default_factory=list, max_length=3)
    additional_contribution: dict[str, object] = Field(default_factory=dict)
    experiment: dict[str, object] = Field(default_factory=dict)
    evaluation: dict[str, object] = Field(default_factory=dict)
    items: list[AnalysisItem] = Field(default_factory=list)


class Paper(BaseModel):
    schema_version: Literal[5] = 5
    paper_id: UUID
    project_id: UUID
    source: PaperSource
    bibliography: Bibliography
    organization: Organization = Field(default_factory=Organization)
    structured_summary: StructuredSummary = Field(default_factory=StructuredSummary)
    created_at: datetime
    updated_at: datetime
    revision: int = Field(ge=1)

    @classmethod
    def create(
        cls,
        *,
        project_id: UUID,
        source: PaperSource,
        title: str,
        authors: list[str] | None = None,
    ) -> Paper:
        now = datetime.now(UTC)
        return cls(
            paper_id=uuid4(),
            project_id=project_id,
            source=source,
            bibliography=Bibliography(title=title, authors=authors or []),
            created_at=now,
            updated_at=now,
            revision=1,
        )

    def relink(self, source: PaperSource) -> Paper:
        return self.model_copy(
            update={
                "source": source,
                "updated_at": datetime.now(UTC),
                "revision": self.revision + 1,
            }
        )

    def update_basic_information(
        self,
        *,
        title: str,
        authors: list[str],
        affiliations: list[str],
        venue: str | None,
        publication_date: date | None,
        reading_date: date | None,
        citation_count: int | None,
        language: str | None,
        keywords: list[str],
        abstract_text: str,
        group: str | None,
    ) -> Paper:
        return self.model_copy(
            update={
                "bibliography": self.bibliography.model_copy(
                    update={
                        "title": title,
                        "authors": authors,
                        "affiliations": affiliations,
                        "venue": venue,
                        "publication_date": publication_date,
                        "citation_count": citation_count,
                        "language": language,
                        "keywords": keywords,
                        "abstract_text": abstract_text,
                    }
                ),
                "organization": self.organization.model_copy(
                    update={"reading_date": reading_date, "group": group}
                ),
                "updated_at": datetime.now(UTC),
                "revision": self.revision + 1,
            }
        )


class PaperAnalysisDocument(BaseModel):
    paper_id: UUID
    revision: int = Field(ge=1)
    updated_at: datetime
    items: list[AnalysisItem]


class PaperSummary(BaseModel):
    paper_id: UUID
    project_id: UUID
    title: str
    short_title: str
    authors: list[str]
    affiliations: list[str]
    year: int | None
    venue: str | None
    publication_date: date | None
    reading_date: date | None
    citation_count: int | None
    language: str | None
    keywords: list[str]
    group: str | None
    topics: list[str]
    tags: list[str]
    reading_status: ReadingStatus
    importance_score: int | None
    writing_uses: list[str]
    source_status: SourceStatus
    source_filename: str | None
    page_count: int | None
    one_sentence_summary: str
    updated_at: datetime
    revision: int


class PaperList(BaseModel):
    items: list[PaperSummary]
    total: int
    page: int
    page_size: int
