"""Health endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from papermatrix import __version__

router = APIRouter(tags=["diagnostics"])


class HealthResponse(BaseModel):
    status: str
    version: str
    workspace_initialized: bool


@router.get("/health", response_model=HealthResponse)
def get_health(request: Request) -> HealthResponse:
    repository = request.app.state.workspace_service.repository
    return HealthResponse(
        status="ok",
        version=__version__,
        workspace_initialized=repository.exists(),
    )
