"""Paper note and reading-question models."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

QuestionStatus = Literal["open", "answered", "deferred"]


class EvidenceReference(BaseModel):
    evidence_id: UUID = Field(default_factory=uuid4)
    evidence_code: str | None = Field(default=None, max_length=40)
    paper_id: UUID
    page_label: str | None = Field(default=None, max_length=40)
    pdf_page_index: int | None = Field(default=None, ge=1)
    section: str | None = Field(default=None, max_length=200)
    figure: str | None = Field(default=None, max_length=80)
    table: str | None = Field(default=None, max_length=80)
    locator_note: str = Field(default="", max_length=2000)


class PaperNote(BaseModel):
    paper_id: UUID
    markdown: str
    revision: int = Field(ge=0)
    updated_at: datetime


class ReadingQuestion(BaseModel):
    question_id: UUID = Field(default_factory=uuid4)
    paper_id: UUID
    question: str = Field(min_length=1, max_length=5000)
    status: QuestionStatus = "open"
    answer: str = Field(default="", max_length=50000)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def answered_question_has_an_answer(self) -> ReadingQuestion:
        if self.status == "answered" and not self.answer.strip():
            raise ValueError("answered questions require a non-empty answer")
        return self

    @classmethod
    def create(
        cls,
        *,
        paper_id: UUID,
        question: str,
        status: QuestionStatus,
        answer: str,
        evidence: list[EvidenceReference],
        tags: list[str],
    ) -> ReadingQuestion:
        now = datetime.now(UTC)
        return cls(
            paper_id=paper_id,
            question=question.strip(),
            status=status,
            answer=answer.strip(),
            evidence=evidence,
            tags=tags,
            created_at=now,
            updated_at=now,
        )


class QuestionsDocument(BaseModel):
    schema_version: Literal[2] = 2
    paper_id: UUID
    revision: int = Field(ge=0)
    updated_at: datetime
    questions: list[ReadingQuestion] = Field(default_factory=list)

    @classmethod
    def empty(cls, paper_id: UUID) -> QuestionsDocument:
        return cls(paper_id=paper_id, revision=0, updated_at=datetime.now(UTC))
