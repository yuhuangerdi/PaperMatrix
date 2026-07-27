"""File-backed project repository."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from papermatrix.core.atomic_io import atomic_write_yaml, read_yaml
from papermatrix.core.errors import ProjectNotEmptyError, ProjectNotFoundError
from papermatrix.core.schema_registry import SchemaRegistry
from papermatrix.domain.project import Project, ProjectSummary


class ProjectRepository:
    def __init__(self, workspace_root: Path, schemas: SchemaRegistry) -> None:
        self._projects_root = workspace_root / "projects"
        self._schemas = schemas

    def _project_dir(self, project_id: UUID) -> Path:
        return self._projects_root / str(project_id)

    def _project_file(self, project_id: UUID) -> Path:
        return self._project_dir(project_id) / "project.yaml"

    def create(self, project: Project) -> Project:
        project_dir = self._project_dir(project.project_id)
        project_dir.mkdir(parents=True, exist_ok=False)
        try:
            for relative in ("papers", "notes", "questions", "artifacts", "exports"):
                (project_dir / relative).mkdir()
            atomic_write_yaml(
                self._project_file(project.project_id),
                project.model_dump(mode="json"),
                validator=lambda value: self._schemas.validate("project", value),
            )
        except Exception:
            self._project_file(project.project_id).unlink(missing_ok=True)
            (project_dir / "project.yaml.lock").unlink(missing_ok=True)
            self._remove_directory_if_empty(project_dir)
            raise
        return project

    def load(self, project_id: UUID) -> Project:
        path = self._project_file(project_id)
        if not path.is_file():
            raise ProjectNotFoundError()
        data = read_yaml(path, lambda value: self._schemas.validate("project", value))
        return Project.model_validate(data)

    def list(self, *, include_archived: bool) -> list[ProjectSummary]:
        if not self._projects_root.exists():
            return []
        projects: list[ProjectSummary] = []
        for project_file in sorted(self._projects_root.glob("*/project.yaml")):
            data = read_yaml(
                project_file,
                lambda value: self._schemas.validate("project", value),
            )
            project = Project.model_validate(data)
            if project.status == "archived" and not include_archived:
                continue
            projects.append(self._summary(project))
        return sorted(projects, key=lambda item: item.updated_at, reverse=True)

    def save(self, project: Project, *, expected_revision: int) -> Project:
        atomic_write_yaml(
            self._project_file(project.project_id),
            project.model_dump(mode="json"),
            validator=lambda value: self._schemas.validate("project", value),
            expected_revision=expected_revision,
        )
        return project

    def delete_empty(self, project_id: UUID) -> None:
        project_dir = self._project_dir(project_id)
        if not self._project_file(project_id).is_file():
            raise ProjectNotFoundError()
        allowed_files = {
            project_dir / "project.yaml",
            project_dir / "project.yaml.lock",
        }
        allowed_directories = {
            project_dir / "papers",
            project_dir / "notes",
            project_dir / "questions",
            project_dir / "artifacts",
            project_dir / "exports",
        }
        unexpected_paths = {
            path
            for path in project_dir.rglob("*")
            if path not in allowed_files and path not in allowed_directories
        }
        if unexpected_paths:
            raise ProjectNotEmptyError()

        self._project_file(project_id).unlink()
        lock_file = project_dir / "project.yaml.lock"
        lock_file.unlink(missing_ok=True)
        self._remove_directory_if_empty(project_dir)

    def name_exists(self, name: str, *, excluding: UUID | None = None) -> bool:
        normalized = name.strip().casefold()
        return any(
            project.name.strip().casefold() == normalized and project.project_id != excluding
            for project in self.list(include_archived=True)
        )

    def _summary(self, project: Project) -> ProjectSummary:
        papers_dir = self._project_dir(project.project_id) / "papers"
        paper_count = 0
        deep_read_count = 0
        reported_count = 0
        for paper_file in papers_dir.glob("*.yaml"):
            data = read_yaml(paper_file)
            paper_count += 1
            organization = data.get("organization", {})
            status = organization.get("reading_status") if isinstance(organization, dict) else None
            if status in {"deep_read", "summarized", "reported"}:
                deep_read_count += 1
            if status == "reported":
                reported_count += 1
        return ProjectSummary(
            **project.model_dump(),
            paper_count=paper_count,
            deep_read_count=deep_read_count,
            reported_count=reported_count,
        )

    @staticmethod
    def _remove_directory_if_empty(project_dir: Path) -> None:
        for name in ("papers", "notes", "questions", "artifacts", "exports"):
            directory = project_dir / name
            if directory.exists():
                directory.rmdir()
        project_dir.rmdir()
