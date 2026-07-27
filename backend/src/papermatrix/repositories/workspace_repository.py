"""File-backed workspace repository."""

from __future__ import annotations

from pathlib import Path

from papermatrix.core.atomic_io import atomic_write_yaml, read_yaml
from papermatrix.core.errors import WorkspaceCorruptedError
from papermatrix.core.schema_registry import SchemaRegistry
from papermatrix.domain.workspace import Workspace


class WorkspaceRepository:
    def __init__(self, root: Path, schemas: SchemaRegistry) -> None:
        self.root = root.resolve(strict=False)
        self._workspace_file = self.root / "workspace.yaml"
        self._schemas = schemas

    def exists(self) -> bool:
        return self._workspace_file.is_file()

    def load(self) -> Workspace:
        try:
            data = read_yaml(
                self._workspace_file,
                lambda value: self._schemas.validate("workspace", value),
            )
            return Workspace.model_validate(data)
        except Exception as exc:
            if isinstance(exc, WorkspaceCorruptedError):
                raise
            raise WorkspaceCorruptedError(reason=str(exc)) from exc

    def initialize(self, name: str, allowed_roots: tuple[Path, ...]) -> Workspace:
        if self.exists():
            return self.load()

        workspace = Workspace.create(name, allowed_roots)
        data = workspace.model_dump(mode="json")
        atomic_write_yaml(
            self._workspace_file,
            data,
            validator=lambda value: self._schemas.validate("workspace", value),
        )
        for relative in ("projects", ".papermatrix/locks", ".papermatrix/diagnostics"):
            (self.root / relative).mkdir(parents=True, exist_ok=True)
        return workspace

    def save(self, workspace: Workspace, *, expected_revision: int) -> Workspace:
        data = workspace.model_dump(mode="json")
        atomic_write_yaml(
            self._workspace_file,
            data,
            validator=lambda value: self._schemas.validate("workspace", value),
            expected_revision=expected_revision,
        )
        return workspace
