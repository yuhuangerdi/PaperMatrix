"""File-backed repository for reproducible analysis scopes."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from papermatrix.core.atomic_io import atomic_write_yaml, read_yaml
from papermatrix.core.errors import FileContentError
from papermatrix.core.schema_registry import SchemaRegistry
from papermatrix.domain.analysis_scope import AnalysisScopesDocument


class AnalysisScopeRepository:
    def __init__(self, workspace_root: Path, schemas: SchemaRegistry) -> None:
        self._projects_root = workspace_root / "projects"
        self._schemas = schemas

    def _file(self, project_id: UUID) -> Path:
        return self._projects_root / str(project_id) / "analyses" / "scopes.yaml"

    def load(self, project_id: UUID) -> AnalysisScopesDocument:
        path = self._file(project_id)
        if not path.is_file():
            return AnalysisScopesDocument.empty(project_id)
        data = read_yaml(path, lambda value: self._schemas.validate("scopes", value))
        document = AnalysisScopesDocument.model_validate(data)
        if document.project_id != project_id:
            raise FileContentError(
                "分析集合中的 project_id 与项目目录不一致。",
                details={"file": path.name},
            )
        return document

    def save(
        self,
        document: AnalysisScopesDocument,
        *,
        expected_revision: int,
    ) -> AnalysisScopesDocument:
        if document.revision < 1:
            raise ValueError("a persisted scopes document must have revision 1 or greater")
        atomic_write_yaml(
            self._file(document.project_id),
            document.model_dump(mode="json"),
            validator=lambda value: self._schemas.validate("scopes", value),
            expected_revision=expected_revision,
        )
        return document
