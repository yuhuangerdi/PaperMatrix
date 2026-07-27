"""Project CRUD API."""

from __future__ import annotations

from typing import Literal, cast
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response, status
from pydantic import BaseModel, Field

from papermatrix.domain.project import Project, ProjectSummary
from papermatrix.services.project_service import ProjectService

router = APIRouter(tags=["projects"])


def _service(request: Request) -> ProjectService:
    return cast(ProjectService, request.app.state.project_service)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    topic: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=5000)
    tags: list[str] = Field(default_factory=list)


class ProjectUpdate(ProjectCreate):
    status: Literal["active", "archived"]
    expected_revision: int = Field(ge=1)


class ProjectList(BaseModel):
    items: list[ProjectSummary]
    total: int


@router.get("/projects", response_model=ProjectList)
def list_projects(
    request: Request,
    include_archived: bool = Query(default=False),
) -> ProjectList:
    items = _service(request).list_projects(include_archived=include_archived)
    return ProjectList(items=items, total=len(items))


@router.post("/projects", response_model=Project, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, request: Request) -> Project:
    return _service(request).create(**payload.model_dump())


@router.get("/projects/{project_id}", response_model=Project)
def get_project(project_id: UUID, request: Request) -> Project:
    return _service(request).get(project_id)


@router.patch("/projects/{project_id}", response_model=Project)
def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    request: Request,
) -> Project:
    return _service(request).update(project_id, **payload.model_dump())


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: UUID,
    request: Request,
    confirm: bool = Query(...),
) -> Response:
    _service(request).delete(project_id, confirmed=confirm)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
