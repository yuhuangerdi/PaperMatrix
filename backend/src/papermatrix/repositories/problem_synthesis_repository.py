"""File-backed repository for field-problem synthesis judgments."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from papermatrix.core.atomic_io import atomic_write_yaml, read_yaml
from papermatrix.core.errors import FileContentError
from papermatrix.core.schema_registry import SchemaRegistry
from papermatrix.domain.problem_synthesis import ProblemSynthesesDocument


class ProblemSynthesisRepository:
    def __init__(self, workspace_root: Path, schemas: SchemaRegistry) -> None:
        self._projects_root = workspace_root / "projects"
        self._schemas = schemas

    def _path(self, project_id: UUID) -> Path:
        return self._projects_root / str(project_id) / "analyses" / "problem-syntheses.yaml"

    def load(self, project_id: UUID) -> ProblemSynthesesDocument:
        path = self._path(project_id)
        if not path.is_file():
            return ProblemSynthesesDocument.empty(project_id)
        data = read_yaml(path, lambda value: self._schemas.validate("problem-syntheses", value))
        document = ProblemSynthesesDocument.model_validate(data)
        if document.project_id != project_id:
            raise FileContentError(
                "问题归纳中的 project_id 与项目目录不一致。",
                details={"file": path.name},
            )
        return document

    def save(
        self,
        document: ProblemSynthesesDocument,
        *,
        expected_revision: int,
    ) -> ProblemSynthesesDocument:
        if document.revision < 1:
            raise ValueError("a persisted problem-syntheses document needs revision >= 1")
        atomic_write_yaml(
            self._path(document.project_id),
            document.model_dump(mode="json"),
            validator=lambda value: self._schemas.validate("problem-syntheses", value),
            expected_revision=expected_revision,
        )
        return document
