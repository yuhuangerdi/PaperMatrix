"""Paper note and reading-question APIs."""

from __future__ import annotations

from typing import Literal, cast
from uuid import UUID

from fastapi import APIRouter, Query, Request, status
from pydantic import BaseModel, Field, model_validator

from papermatrix.domain.note_analysis import (
    CandidateImportResult,
    NoteItemDocument,
    NoteItemUpdateResult,
    NoteParsePreview,
)
from papermatrix.domain.paper_content import (
    EvidenceReference,
    PaperNote,
    QuestionsDocument,
)
from papermatrix.services.paper_content_service import PaperContentService

router = APIRouter(tags=["paper-content"])


def _service(request: Request) -> PaperContentService:
    return cast(PaperContentService, request.app.state.paper_content_service)


class NoteUpdate(BaseModel):
    markdown: str = Field(max_length=2_000_000)
    expected_revision: int = Field(ge=0)


class CandidateImportRequest(BaseModel):
    candidate_ids: list[UUID] = Field(min_length=1)
    expected_note_revision: int = Field(ge=0)
    expected_paper_revision: int = Field(ge=1)


class NoteItemUpdate(BaseModel):
    markdown: str = Field(min_length=1, max_length=200_000)
    expected_note_revision: int = Field(ge=0)
    expected_paper_revision: int = Field(ge=1)
    expected_source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class QuestionInput(BaseModel):
    question: str = Field(min_length=1, max_length=5000)
    status: Literal["open", "answered", "deferred"] = "open"
    answer: str = Field(default="", max_length=50000)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    expected_revision: int = Field(ge=0)

    @model_validator(mode="after")
    def answered_question_has_an_answer(self) -> QuestionInput:
        if self.status == "answered" and not self.answer.strip():
            raise ValueError("answered questions require a non-empty answer")
        return self


@router.get("/projects/{project_id}/papers/{paper_id}/note", response_model=PaperNote)
def get_note(project_id: UUID, paper_id: UUID, request: Request) -> PaperNote:
    return _service(request).get_note(project_id, paper_id)


@router.put("/projects/{project_id}/papers/{paper_id}/note", response_model=PaperNote)
def save_note(
    project_id: UUID,
    paper_id: UUID,
    payload: NoteUpdate,
    request: Request,
) -> PaperNote:
    return _service(request).save_note(project_id, paper_id, **payload.model_dump())


@router.get("/projects/{project_id}/papers/{paper_id}/note/supplement", response_model=PaperNote)
def get_supplement(project_id: UUID, paper_id: UUID, request: Request) -> PaperNote:
    return _service(request).get_supplement(project_id, paper_id)


@router.put("/projects/{project_id}/papers/{paper_id}/note/supplement", response_model=PaperNote)
def save_supplement(
    project_id: UUID,
    paper_id: UUID,
    payload: NoteUpdate,
    request: Request,
) -> PaperNote:
    return _service(request).save_supplement(project_id, paper_id, **payload.model_dump())


@router.post(
    "/projects/{project_id}/papers/{paper_id}/analysis/parse-note",
    response_model=NoteParsePreview,
)
def preview_note_analysis(
    project_id: UUID,
    paper_id: UUID,
    request: Request,
) -> NoteParsePreview:
    return _service(request).preview_note_analysis(project_id, paper_id)


@router.post(
    "/projects/{project_id}/papers/{paper_id}/analysis/import-candidates",
    response_model=CandidateImportResult,
)
def import_note_candidates(
    project_id: UUID,
    paper_id: UUID,
    payload: CandidateImportRequest,
    request: Request,
) -> CandidateImportResult:
    return _service(request).import_note_candidates(
        project_id,
        paper_id,
        **payload.model_dump(),
    )


@router.get(
    "/projects/{project_id}/papers/{paper_id}/note/items",
    response_model=NoteItemDocument,
)
def get_note_items(
    project_id: UUID,
    paper_id: UUID,
    request: Request,
) -> NoteItemDocument:
    return _service(request).get_note_items(project_id, paper_id)


@router.put(
    "/projects/{project_id}/papers/{paper_id}/note/items/{item_id}",
    response_model=NoteItemUpdateResult,
)
def update_note_item(
    project_id: UUID,
    paper_id: UUID,
    item_id: UUID,
    payload: NoteItemUpdate,
    request: Request,
) -> NoteItemUpdateResult:
    return _service(request).update_note_item(
        project_id,
        paper_id,
        item_id,
        **payload.model_dump(),
    )


@router.get(
    "/projects/{project_id}/papers/{paper_id}/questions",
    response_model=QuestionsDocument,
)
def get_questions(project_id: UUID, paper_id: UUID, request: Request) -> QuestionsDocument:
    return _service(request).get_questions(project_id, paper_id)


@router.post(
    "/projects/{project_id}/papers/{paper_id}/questions",
    response_model=QuestionsDocument,
    status_code=status.HTTP_201_CREATED,
)
def create_question(
    project_id: UUID,
    paper_id: UUID,
    payload: QuestionInput,
    request: Request,
) -> QuestionsDocument:
    return _service(request).create_question(
        project_id,
        paper_id,
        question=payload.question,
        status=payload.status,
        answer=payload.answer,
        evidence=payload.evidence,
        tags=payload.tags,
        expected_revision=payload.expected_revision,
    )


@router.patch(
    "/projects/{project_id}/papers/{paper_id}/questions/{question_id}",
    response_model=QuestionsDocument,
)
def update_question(
    project_id: UUID,
    paper_id: UUID,
    question_id: UUID,
    payload: QuestionInput,
    request: Request,
) -> QuestionsDocument:
    return _service(request).update_question(
        project_id,
        paper_id,
        question_id,
        question=payload.question,
        status=payload.status,
        answer=payload.answer,
        evidence=payload.evidence,
        tags=payload.tags,
        expected_revision=payload.expected_revision,
    )


@router.delete(
    "/projects/{project_id}/papers/{paper_id}/questions/{question_id}",
    response_model=QuestionsDocument,
)
def delete_question(
    project_id: UUID,
    paper_id: UUID,
    question_id: UUID,
    request: Request,
    expected_revision: int = Query(ge=0),
) -> QuestionsDocument:
    return _service(request).delete_question(
        project_id,
        paper_id,
        question_id,
        expected_revision=expected_revision,
    )
