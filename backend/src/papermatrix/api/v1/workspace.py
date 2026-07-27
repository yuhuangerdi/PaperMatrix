"""Workspace API."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Request, status
from pydantic import BaseModel, Field

from papermatrix.domain.workspace import Workspace

router = APIRouter(tags=["workspace"])


class WorkspaceView(BaseModel):
    workspace_id: str
    name: str
    root_path: str
    allowed_paper_roots: list[str]
    revision: int


class WorkspaceInitialize(BaseModel):
    root_path: str
    name: str = Field(min_length=1, max_length=120)
    allowed_paper_roots: list[str] = Field(default_factory=list)


class WorkspaceUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    allowed_paper_roots: list[str]
    expected_revision: int = Field(ge=1)


class PathValidationRequest(BaseModel):
    path: str
    purpose: Literal["workspace", "paper_root", "scan_directory", "registered_pdf"]


class PathValidationResponse(BaseModel):
    valid: bool
    normalized_path: str
    readable: bool
    writable: bool
    reason: str | None


def _view(workspace: Workspace, root_path: str) -> WorkspaceView:
    return WorkspaceView(
        workspace_id=str(workspace.workspace_id),
        name=workspace.name,
        root_path=root_path,
        allowed_paper_roots=workspace.allowed_paper_roots,
        revision=workspace.revision,
    )


@router.get("/workspace", response_model=WorkspaceView)
def get_workspace(request: Request) -> WorkspaceView:
    service = request.app.state.workspace_service
    return _view(service.require_workspace(), str(service.root))


@router.post(
    "/workspace/initialize",
    response_model=WorkspaceView,
    status_code=status.HTTP_201_CREATED,
)
def initialize_workspace(payload: WorkspaceInitialize, request: Request) -> WorkspaceView:
    service = request.app.state.workspace_service
    workspace = service.initialize(**payload.model_dump())
    return _view(workspace, str(service.root))


@router.patch("/workspace", response_model=WorkspaceView)
def update_workspace(payload: WorkspaceUpdate, request: Request) -> WorkspaceView:
    service = request.app.state.workspace_service
    workspace = service.update(**payload.model_dump())
    return _view(workspace, str(service.root))


@router.post("/workspace/validate-path", response_model=PathValidationResponse)
def validate_path(payload: PathValidationRequest, request: Request) -> PathValidationResponse:
    result = request.app.state.workspace_service.validate_path(**payload.model_dump())
    return PathValidationResponse.model_validate(result)
