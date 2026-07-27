"""File-backed paper record repository."""

from __future__ import annotations

import builtins
from pathlib import Path
from uuid import UUID

from filelock import FileLock, Timeout

from papermatrix.core.atomic_io import atomic_write_yaml, read_yaml
from papermatrix.core.errors import FileLockTimeoutError, PaperNotFoundError
from papermatrix.core.schema_registry import SchemaRegistry
from papermatrix.domain.paper import Paper
from papermatrix.domain.paper_migrations import migrate_paper


class PaperRepository:
    def __init__(self, workspace_root: Path, schemas: SchemaRegistry) -> None:
        self._projects_root = workspace_root / "projects"
        self._schemas = schemas

    def _paper_file(self, project_id: UUID, paper_id: UUID) -> Path:
        return self._projects_root / str(project_id) / "papers" / f"{paper_id}.yaml"

    def _note_file(self, project_id: UUID, paper_id: UUID) -> Path:
        return self._projects_root / str(project_id) / "notes" / f"{paper_id}.md"

    def _questions_file(self, project_id: UUID, paper_id: UUID) -> Path:
        return self._projects_root / str(project_id) / "questions" / f"{paper_id}.yaml"

    def create(self, paper: Paper) -> Paper:
        atomic_write_yaml(
            self._paper_file(paper.project_id, paper.paper_id),
            paper.model_dump(mode="json"),
            validator=lambda value: self._schemas.validate("paper", value),
        )
        return paper

    def load(self, project_id: UUID, paper_id: UUID) -> Paper:
        path = self._paper_file(project_id, paper_id)
        if not path.is_file():
            raise PaperNotFoundError()
        data = migrate_paper(read_yaml(path))
        self._schemas.validate("paper", data)
        return Paper.model_validate(data)

    def list(self, project_id: UUID) -> list[Paper]:
        papers_dir = self._projects_root / str(project_id) / "papers"
        if not papers_dir.is_dir():
            return []
        return [
            Paper.model_validate(self._validated_data(path))
            for path in sorted(papers_dir.glob("*.yaml"))
        ]

    def save(self, paper: Paper, *, expected_revision: int) -> Paper:
        atomic_write_yaml(
            self._paper_file(paper.project_id, paper.paper_id),
            paper.model_dump(mode="json"),
            validator=lambda value: self._schemas.validate("paper", migrate_paper(value)),
            expected_revision=expected_revision,
        )
        return paper

    def delete(self, project_id: UUID, paper_id: UUID) -> builtins.list[str]:
        paper_path = self._paper_file(project_id, paper_id)
        if not paper_path.is_file():
            raise PaperNotFoundError()
        lock = FileLock(str(paper_path.with_suffix(".yaml.lock")), timeout=5)
        removed = []
        try:
            with lock:
                paper_path.unlink()
                removed.append(paper_path.name)
                note_path = self._note_file(project_id, paper_id)
                if note_path.is_file():
                    note_path.unlink()
                    removed.append(note_path.name)
                note_path.with_suffix(".md.lock").unlink(missing_ok=True)
                questions_path = self._questions_file(project_id, paper_id)
                if questions_path.is_file():
                    questions_path.unlink()
                    removed.append(questions_path.name)
                questions_path.with_suffix(".yaml.lock").unlink(missing_ok=True)
        except Timeout as exc:
            raise FileLockTimeoutError() from exc
        paper_path.with_suffix(".yaml.lock").unlink(missing_ok=True)
        return removed

    def _validated_data(self, path: Path) -> dict[str, object]:
        data = migrate_paper(read_yaml(path))
        self._schemas.validate("paper", data)
        return data
