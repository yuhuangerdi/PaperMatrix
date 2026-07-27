"""Workspace setup and update orchestration."""

from __future__ import annotations

import os
from pathlib import Path

from papermatrix.core.errors import ProjectConflictError, WorkspaceNotInitializedError
from papermatrix.core.paths import PathPolicy
from papermatrix.core.schema_registry import SchemaRegistry
from papermatrix.domain.workspace import Workspace
from papermatrix.repositories.local_config_repository import LocalConfigRepository
from papermatrix.repositories.workspace_repository import WorkspaceRepository


class WorkspaceService:
    def __init__(
        self,
        initial_root: Path,
        schemas: SchemaRegistry,
        local_config: LocalConfigRepository,
    ) -> None:
        self._schemas = schemas
        self._local_config = local_config
        self.repository = WorkspaceRepository(initial_root, schemas)

    @property
    def root(self) -> Path:
        return self.repository.root

    def require_workspace(self) -> Workspace:
        if not self.repository.exists():
            raise WorkspaceNotInitializedError()
        return self.repository.load()

    def initialize(
        self,
        *,
        root_path: str,
        name: str,
        allowed_paper_roots: list[str],
    ) -> Workspace:
        root = PathPolicy.validate_workspace_destination(root_path)
        roots = tuple(PathPolicy.validate_paper_root(path) for path in allowed_paper_roots)
        candidate = WorkspaceRepository(root, self._schemas)
        workspace_file = root / "workspace.yaml"
        if workspace_file.exists():
            workspace = candidate.load()
        else:
            if root.exists() and any(root.iterdir()):
                raise ProjectConflictError("所选目录非空且不是有效的 PaperMatrix 工作区。")
            root.mkdir(parents=True, exist_ok=True)
            workspace = candidate.initialize(name.strip(), roots)
        self.repository = candidate
        self._local_config.save_workspace_root(root)
        return workspace

    def update(
        self,
        *,
        name: str,
        allowed_paper_roots: list[str],
        expected_revision: int,
    ) -> Workspace:
        current = self.require_workspace()
        roots = tuple(PathPolicy.validate_paper_root(path) for path in allowed_paper_roots)
        updated = current.update(name=name.strip(), allowed_roots=roots)
        return self.repository.save(updated, expected_revision=expected_revision)

    def validate_path(self, path: str, purpose: str) -> dict[str, object]:
        try:
            if purpose == "workspace":
                normalized = PathPolicy.validate_workspace_destination(path)
                readable = normalized.exists() and os.access(normalized, os.R_OK)
                writable = True
            else:
                normalized = PathPolicy.validate_paper_root(path)
                readable = True
                writable = os.access(normalized, os.W_OK)
            return {
                "valid": True,
                "normalized_path": str(normalized),
                "readable": readable,
                "writable": writable,
                "reason": None,
            }
        except Exception as exc:
            return {
                "valid": False,
                "normalized_path": str(Path(path).expanduser().resolve(strict=False)),
                "readable": False,
                "writable": False,
                "reason": str(exc),
            }
