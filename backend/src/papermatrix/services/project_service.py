"""Project lifecycle orchestration."""

from __future__ import annotations

import re
import unicodedata
from typing import Literal
from uuid import UUID

from papermatrix.core.errors import ProjectConflictError
from papermatrix.core.schema_registry import SchemaRegistry
from papermatrix.domain.project import Project, ProjectSummary
from papermatrix.repositories.project_repository import ProjectRepository
from papermatrix.services.workspace_service import WorkspaceService


def make_slug(name: str, fallback: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")[:80]
    return slug or f"project-{fallback}"


class ProjectService:
    def __init__(self, workspace: WorkspaceService, schemas: SchemaRegistry) -> None:
        self._workspace = workspace
        self._schemas = schemas

    def _repository(self) -> ProjectRepository:
        self._workspace.require_workspace()
        return ProjectRepository(self._workspace.root, self._schemas)

    def list_projects(self, *, include_archived: bool) -> list[ProjectSummary]:
        return self._repository().list(include_archived=include_archived)

    def get(self, project_id: UUID) -> Project:
        return self._repository().load(project_id)

    def create(
        self,
        *,
        name: str,
        topic: str,
        description: str,
        tags: list[str],
    ) -> Project:
        repository = self._repository()
        cleaned_name = name.strip()
        if repository.name_exists(cleaned_name):
            raise ProjectConflictError()
        project = Project.create(
            name=cleaned_name,
            slug="project-pending",
            topic=topic.strip(),
            description=description.strip(),
            tags=list(dict.fromkeys(tag.strip() for tag in tags if tag.strip())),
        )
        project = project.model_copy(
            update={"slug": make_slug(cleaned_name, str(project.project_id)[:8])}
        )
        return repository.create(project)

    def update(
        self,
        project_id: UUID,
        *,
        name: str,
        topic: str,
        description: str,
        tags: list[str],
        status: Literal["active", "archived"],
        expected_revision: int,
    ) -> Project:
        repository = self._repository()
        current = repository.load(project_id)
        cleaned_name = name.strip()
        if repository.name_exists(cleaned_name, excluding=project_id):
            raise ProjectConflictError()
        updated = current.update(
            name=cleaned_name,
            slug=make_slug(cleaned_name, str(project_id)[:8]),
            topic=topic.strip(),
            description=description.strip(),
            tags=list(dict.fromkeys(tag.strip() for tag in tags if tag.strip())),
            status=status,
        )
        return repository.save(updated, expected_revision=expected_revision)

    def delete(self, project_id: UUID, *, confirmed: bool) -> None:
        if not confirmed:
            raise ProjectConflictError("删除项目需要明确确认。")
        self._repository().delete_empty(project_id)
