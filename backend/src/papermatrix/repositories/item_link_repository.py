"""File-backed repository for project-level structured-item links."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from papermatrix.core.atomic_io import atomic_write_yaml, read_yaml
from papermatrix.core.errors import FileContentError
from papermatrix.core.schema_registry import SchemaRegistry
from papermatrix.domain.item_links import ItemLinksDocument


class ItemLinkRepository:
    def __init__(self, workspace_root: Path, schemas: SchemaRegistry) -> None:
        self._projects_root = workspace_root / "projects"
        self._schemas = schemas

    def _item_links_file(self, project_id: UUID) -> Path:
        return self._projects_root / str(project_id) / "analyses" / "item-links.yaml"

    def load(self, project_id: UUID) -> ItemLinksDocument:
        path = self._item_links_file(project_id)
        if not path.is_file():
            return ItemLinksDocument.empty(project_id)
        data = read_yaml(path, lambda value: self._schemas.validate("item-links", value))
        document = ItemLinksDocument.model_validate(data)
        if document.project_id != project_id:
            raise FileContentError(
                "条目关系中的 project_id 与项目目录不一致。",
                details={"file": path.name},
            )
        return document

    def save(
        self,
        document: ItemLinksDocument,
        *,
        expected_revision: int,
    ) -> ItemLinksDocument:
        if document.revision < 1:
            raise ValueError("a persisted item-links document must have revision 1 or greater")
        atomic_write_yaml(
            self._item_links_file(document.project_id),
            document.model_dump(mode="json"),
            validator=lambda value: self._schemas.validate("item-links", value),
            expected_revision=expected_revision,
        )
        return document
