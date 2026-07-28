"""Reproducible analysis-scope API."""

from __future__ import annotations

from typing import cast
from uuid import UUID

from fastapi import APIRouter, Request, status
from pydantic import BaseModel, Field

from papermatrix.domain.analysis_scope import AnalysisScopesViewDocument
from papermatrix.services.analysis_scope_service import AnalysisScopeService

router = APIRouter(tags=["analysis-scopes"])


def _service(request: Request) -> AnalysisScopeService:
    return cast(AnalysisScopeService, request.app.state.analysis_scope_service)


class AnalysisScopeInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    purpose: str = Field(default="", max_length=5000)
    paper_ids: list[UUID] = Field(min_length=1)
    source_filter_snapshot: dict[str, str] = Field(default_factory=dict)
    expected_revision: int = Field(ge=0)


class AnalysisScopeUpdate(AnalysisScopeInput):
    expected_revision: int = Field(ge=1)


class AnalysisScopeDelete(BaseModel):
    expected_revision: int = Field(ge=1)


@router.get(
    "/projects/{project_id}/analysis-scopes",
    response_model=AnalysisScopesViewDocument,
)
def list_analysis_scopes(
    project_id: UUID,
    request: Request,
) -> AnalysisScopesViewDocument:
    return _service(request).list_scopes(project_id)


@router.post(
    "/projects/{project_id}/analysis-scopes",
    response_model=AnalysisScopesViewDocument,
    status_code=status.HTTP_201_CREATED,
)
def create_analysis_scope(
    project_id: UUID,
    payload: AnalysisScopeInput,
    request: Request,
) -> AnalysisScopesViewDocument:
    return _service(request).create(project_id, **payload.model_dump())


@router.patch(
    "/projects/{project_id}/analysis-scopes/{scope_id}",
    response_model=AnalysisScopesViewDocument,
)
def update_analysis_scope(
    project_id: UUID,
    scope_id: UUID,
    payload: AnalysisScopeUpdate,
    request: Request,
) -> AnalysisScopesViewDocument:
    return _service(request).update(project_id, scope_id, **payload.model_dump())


@router.delete(
    "/projects/{project_id}/analysis-scopes/{scope_id}",
    response_model=AnalysisScopesViewDocument,
)
def delete_analysis_scope(
    project_id: UUID,
    scope_id: UUID,
    payload: AnalysisScopeDelete,
    request: Request,
) -> AnalysisScopesViewDocument:
    return _service(request).delete(project_id, scope_id, **payload.model_dump())
