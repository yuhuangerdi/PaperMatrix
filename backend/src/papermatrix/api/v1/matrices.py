"""Derived project matrix API."""

from __future__ import annotations

from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Query, Request

from papermatrix.domain.literature_matrix import LiteratureMatrix
from papermatrix.services.literature_matrix_service import LiteratureMatrixService

router = APIRouter(tags=["matrices"])


def _service(request: Request) -> LiteratureMatrixService:
    return cast(LiteratureMatrixService, request.app.state.literature_matrix_service)


@router.get(
    "/projects/{project_id}/matrices/literature",
    response_model=LiteratureMatrix,
)
def get_literature_matrix(
    project_id: UUID,
    request: Request,
    scope_id: Annotated[UUID | None, Query()] = None,
) -> LiteratureMatrix:
    return _service(request).get(project_id, scope_id=scope_id)
