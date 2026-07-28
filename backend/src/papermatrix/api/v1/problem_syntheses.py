"""Field-problem synthesis CRUD and derived matrix API."""

from __future__ import annotations

from typing import cast
from uuid import UUID

from fastapi import APIRouter, Request, status
from pydantic import BaseModel, Field

from papermatrix.domain.item_links import ItemReference
from papermatrix.domain.problem_synthesis import (
    FieldProblemStatus,
    ProblemSynthesesViewDocument,
    ProblemSynthesisMatrix,
    ResolutionLevel,
)
from papermatrix.services.problem_synthesis_service import ProblemSynthesisService

router = APIRouter(tags=["problem-syntheses"])


def _service(request: Request) -> ProblemSynthesisService:
    return cast(ProblemSynthesisService, request.app.state.problem_synthesis_service)


class ExpectedRevision(BaseModel):
    expected_revision: int = Field(ge=1)


class ProblemBoardInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    purpose: str = Field(default="", max_length=5000)
    scope_id: UUID
    problem_ids: list[UUID] = Field(default_factory=list)
    paper_ids: list[UUID] = Field(min_length=1)
    expected_revision: int = Field(ge=0)


class ProblemBoardUpdate(ProblemBoardInput):
    expected_revision: int = Field(ge=1)


class FieldProblemInput(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    definition: str = Field(min_length=1, max_length=20000)
    scope_note: str = Field(default="", max_length=10000)
    aliases: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    status: FieldProblemStatus = "active"
    source_problem_refs: list[ItemReference] = Field(default_factory=list)
    expected_revision: int = Field(ge=0)


class FieldProblemUpdate(FieldProblemInput):
    expected_revision: int = Field(ge=1)


class PaperContributionInput(BaseModel):
    problem_id: UUID
    paper_id: UUID
    research_problem_item_id: UUID
    method_item_id: UUID | None = None
    experiment_item_id: UUID | None = None
    resolution_level: ResolutionLevel = "unknown"
    rationale: str = Field(default="", max_length=20000)
    supporting_evidence_ids: list[UUID] = Field(default_factory=list)
    counter_evidence: str = Field(default="", max_length=20000)
    conditions: str = Field(default="", max_length=20000)
    user_judgment: str = Field(default="", max_length=20000)
    expected_revision: int = Field(ge=0)


class PaperContributionUpdate(PaperContributionInput):
    expected_revision: int = Field(ge=1)


@router.get(
    "/projects/{project_id}/problem-syntheses",
    response_model=ProblemSynthesesViewDocument,
)
def get_problem_syntheses(project_id: UUID, request: Request) -> ProblemSynthesesViewDocument:
    return _service(request).get(project_id)


@router.post(
    "/projects/{project_id}/problem-boards",
    response_model=ProblemSynthesesViewDocument,
    status_code=status.HTTP_201_CREATED,
)
def create_problem_board(
    project_id: UUID, payload: ProblemBoardInput, request: Request
) -> ProblemSynthesesViewDocument:
    return _service(request).create_board(project_id, **payload.model_dump())


@router.patch(
    "/projects/{project_id}/problem-boards/{board_id}",
    response_model=ProblemSynthesesViewDocument,
)
def update_problem_board(
    project_id: UUID,
    board_id: UUID,
    payload: ProblemBoardUpdate,
    request: Request,
) -> ProblemSynthesesViewDocument:
    return _service(request).update_board(project_id, board_id, **payload.model_dump())


@router.delete(
    "/projects/{project_id}/problem-boards/{board_id}",
    response_model=ProblemSynthesesViewDocument,
)
def delete_problem_board(
    project_id: UUID, board_id: UUID, payload: ExpectedRevision, request: Request
) -> ProblemSynthesesViewDocument:
    return _service(request).delete_board(
        project_id, board_id, expected_revision=payload.expected_revision
    )


@router.post(
    "/projects/{project_id}/field-problems",
    response_model=ProblemSynthesesViewDocument,
    status_code=status.HTTP_201_CREATED,
)
def create_field_problem(
    project_id: UUID, payload: FieldProblemInput, request: Request
) -> ProblemSynthesesViewDocument:
    values = payload.model_dump(exclude={"source_problem_refs"})
    return _service(request).create_problem(
        project_id,
        source_problem_refs=payload.source_problem_refs,
        **values,
    )


@router.patch(
    "/projects/{project_id}/field-problems/{problem_id}",
    response_model=ProblemSynthesesViewDocument,
)
def update_field_problem(
    project_id: UUID,
    problem_id: UUID,
    payload: FieldProblemUpdate,
    request: Request,
) -> ProblemSynthesesViewDocument:
    values = payload.model_dump(exclude={"source_problem_refs"})
    return _service(request).update_problem(
        project_id,
        problem_id,
        source_problem_refs=payload.source_problem_refs,
        **values,
    )


@router.delete(
    "/projects/{project_id}/field-problems/{problem_id}",
    response_model=ProblemSynthesesViewDocument,
)
def delete_field_problem(
    project_id: UUID,
    problem_id: UUID,
    payload: ExpectedRevision,
    request: Request,
) -> ProblemSynthesesViewDocument:
    return _service(request).delete_problem(
        project_id, problem_id, expected_revision=payload.expected_revision
    )


@router.post(
    "/projects/{project_id}/paper-contributions",
    response_model=ProblemSynthesesViewDocument,
    status_code=status.HTTP_201_CREATED,
)
def create_paper_contribution(
    project_id: UUID, payload: PaperContributionInput, request: Request
) -> ProblemSynthesesViewDocument:
    return _service(request).create_contribution(project_id, **payload.model_dump())


@router.patch(
    "/projects/{project_id}/paper-contributions/{contribution_id}",
    response_model=ProblemSynthesesViewDocument,
)
def update_paper_contribution(
    project_id: UUID,
    contribution_id: UUID,
    payload: PaperContributionUpdate,
    request: Request,
) -> ProblemSynthesesViewDocument:
    return _service(request).update_contribution(
        project_id, contribution_id, **payload.model_dump()
    )


@router.delete(
    "/projects/{project_id}/paper-contributions/{contribution_id}",
    response_model=ProblemSynthesesViewDocument,
)
def delete_paper_contribution(
    project_id: UUID,
    contribution_id: UUID,
    payload: ExpectedRevision,
    request: Request,
) -> ProblemSynthesesViewDocument:
    return _service(request).delete_contribution(
        project_id,
        contribution_id,
        expected_revision=payload.expected_revision,
    )


@router.get(
    "/projects/{project_id}/matrices/problems",
    response_model=ProblemSynthesisMatrix,
)
def get_problem_matrix(
    project_id: UUID, board_id: UUID, request: Request
) -> ProblemSynthesisMatrix:
    return _service(request).matrix(project_id, board_id)
