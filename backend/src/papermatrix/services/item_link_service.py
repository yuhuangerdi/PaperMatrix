"""Orchestration for project-level structured-item links."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from papermatrix.core.errors import (
    ItemLinkNotFoundError,
    ItemReferenceNotFoundError,
    PaperMatrixError,
)
from papermatrix.core.schema_registry import SchemaRegistry
from papermatrix.domain.item_links import (
    ItemLink,
    ItemLinkImpact,
    ItemLinksViewDocument,
    ItemLinkType,
    ItemLinkView,
    ItemReference,
    ItemReferenceView,
    ProjectAnalysisItem,
    ProjectAnalysisItemCatalog,
)
from papermatrix.domain.paper import AnalysisItem, Paper
from papermatrix.repositories.item_link_repository import ItemLinkRepository
from papermatrix.repositories.paper_repository import PaperRepository
from papermatrix.repositories.project_repository import ProjectRepository
from papermatrix.services.workspace_service import WorkspaceService


class ItemLinkService:
    def __init__(self, workspace: WorkspaceService, schemas: SchemaRegistry) -> None:
        self._workspace = workspace
        self._schemas = schemas

    def _repositories(
        self,
    ) -> tuple[ProjectRepository, PaperRepository, ItemLinkRepository]:
        self._workspace.require_workspace()
        return (
            ProjectRepository(self._workspace.root, self._schemas),
            PaperRepository(self._workspace.root, self._schemas),
            ItemLinkRepository(self._workspace.root, self._schemas),
        )

    def list_items(self, project_id: UUID) -> ProjectAnalysisItemCatalog:
        projects, papers, _ = self._repositories()
        projects.load(project_id)
        items = [
            ProjectAnalysisItem(
                paper_id=paper.paper_id,
                paper_title=paper.bibliography.title,
                item=item,
            )
            for paper in papers.list(project_id)
            for item in paper.structured_summary.items
        ]
        return ProjectAnalysisItemCatalog(project_id=project_id, items=items)

    def get_item(
        self,
        project_id: UUID,
        paper_id: UUID,
        item_id: UUID,
    ) -> ProjectAnalysisItem:
        projects, papers, _ = self._repositories()
        projects.load(project_id)
        paper = papers.load(project_id, paper_id)
        item = self._find_item(paper, item_id)
        if item is None:
            raise ItemReferenceNotFoundError(endpoint="target")
        return ProjectAnalysisItem(
            paper_id=paper_id,
            paper_title=paper.bibliography.title,
            item=item,
        )

    def list_links(self, project_id: UUID) -> ItemLinksViewDocument:
        projects, papers, links = self._repositories()
        projects.load(project_id)
        document = links.load(project_id)
        paper_map = {paper.paper_id: paper for paper in papers.list(project_id)}
        views = [self._view(link, paper_map) for link in document.links]
        return ItemLinksViewDocument(
            document=document,
            links=views,
            dangling_count=sum(
                view.source.status != "available" or view.target.status != "available"
                for view in views
            ),
        )

    def create(
        self,
        project_id: UUID,
        *,
        source: ItemReference,
        target: ItemReference,
        type: ItemLinkType,
        description: str,
        expected_revision: int,
    ) -> ItemLinksViewDocument:
        projects, papers, links = self._repositories()
        projects.load(project_id)
        self._require_reference(papers, project_id, source, endpoint="source")
        self._require_reference(papers, project_id, target, endpoint="target")
        current = links.load(project_id)
        created = ItemLink.create(
            source=source,
            target=target,
            type=type,
            description=description,
        )
        updated = current.model_copy(
            update={
                "revision": current.revision + 1,
                "updated_at": datetime.now(UTC),
                "links": [*current.links, created],
            }
        )
        links.save(updated, expected_revision=expected_revision)
        return self.list_links(project_id)

    def update(
        self,
        project_id: UUID,
        link_id: UUID,
        *,
        type: ItemLinkType,
        description: str,
        expected_revision: int,
    ) -> ItemLinksViewDocument:
        projects, _, links = self._repositories()
        projects.load(project_id)
        current = links.load(project_id)
        existing = next((link for link in current.links if link.link_id == link_id), None)
        if existing is None:
            raise ItemLinkNotFoundError()
        updated_link = existing.update(type=type, description=description)
        updated = current.model_copy(
            update={
                "revision": current.revision + 1,
                "updated_at": datetime.now(UTC),
                "links": [
                    updated_link if link.link_id == link_id else link for link in current.links
                ],
            }
        )
        links.save(updated, expected_revision=expected_revision)
        return self.list_links(project_id)

    def delete(
        self,
        project_id: UUID,
        link_id: UUID,
        *,
        expected_revision: int,
    ) -> ItemLinksViewDocument:
        projects, _, links = self._repositories()
        projects.load(project_id)
        current = links.load(project_id)
        if not any(link.link_id == link_id for link in current.links):
            raise ItemLinkNotFoundError()
        updated = current.model_copy(
            update={
                "revision": current.revision + 1,
                "updated_at": datetime.now(UTC),
                "links": [link for link in current.links if link.link_id != link_id],
            }
        )
        links.save(updated, expected_revision=expected_revision)
        return self.list_links(project_id)

    def impacts(
        self,
        project_id: UUID,
        references: list[ItemReference],
    ) -> ItemLinkImpact:
        view = self.list_links(project_id)
        selected = {(reference.paper_id, reference.item_id) for reference in references}
        affected = [
            link
            for link in view.links
            if (link.link.source.paper_id, link.link.source.item_id) in selected
            or (link.link.target.paper_id, link.link.target.item_id) in selected
        ]
        return ItemLinkImpact(references=references, affected_links=affected)

    @staticmethod
    def _find_item(paper: Paper, item_id: UUID) -> AnalysisItem | None:
        return next(
            (item for item in paper.structured_summary.items if item.item_id == item_id),
            None,
        )

    def _require_reference(
        self,
        papers: PaperRepository,
        project_id: UUID,
        reference: ItemReference,
        *,
        endpoint: str,
    ) -> None:
        try:
            paper = papers.load(project_id, reference.paper_id)
        except PaperMatrixError as exc:
            raise ItemReferenceNotFoundError(endpoint=endpoint) from exc
        if self._find_item(paper, reference.item_id) is None:
            raise ItemReferenceNotFoundError(endpoint=endpoint)

    def _view(self, link: ItemLink, papers: dict[UUID, Paper]) -> ItemLinkView:
        return ItemLinkView(
            link=link,
            source=self._reference_view(link.source, papers),
            target=self._reference_view(link.target, papers),
        )

    def _reference_view(
        self,
        reference: ItemReference,
        papers: dict[UUID, Paper],
    ) -> ItemReferenceView:
        paper = papers.get(reference.paper_id)
        if paper is None:
            return ItemReferenceView(reference=reference, status="missing_paper")
        item = self._find_item(paper, reference.item_id)
        if item is None:
            return ItemReferenceView(
                reference=reference,
                status="missing_item",
                paper_title=paper.bibliography.title,
            )
        return ItemReferenceView(
            reference=reference,
            status="available",
            paper_title=paper.bibliography.title,
            item_title=item.title,
            item_kind=item.kind,
        )
