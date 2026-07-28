"""Analysis-scope orchestration and missing-paper diagnostics."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from papermatrix.core.errors import AnalysisScopeNotFoundError, AnalysisScopePaperError
from papermatrix.core.schema_registry import SchemaRegistry
from papermatrix.domain.analysis_scope import (
    AnalysisScope,
    AnalysisScopesViewDocument,
    AnalysisScopeView,
)
from papermatrix.repositories.analysis_scope_repository import AnalysisScopeRepository
from papermatrix.repositories.paper_repository import PaperRepository
from papermatrix.repositories.project_repository import ProjectRepository
from papermatrix.services.workspace_service import WorkspaceService


class AnalysisScopeService:
    def __init__(self, workspace: WorkspaceService, schemas: SchemaRegistry) -> None:
        self._workspace = workspace
        self._schemas = schemas

    def _repositories(
        self,
    ) -> tuple[ProjectRepository, PaperRepository, AnalysisScopeRepository]:
        self._workspace.require_workspace()
        return (
            ProjectRepository(self._workspace.root, self._schemas),
            PaperRepository(self._workspace.root, self._schemas),
            AnalysisScopeRepository(self._workspace.root, self._schemas),
        )

    def list_scopes(self, project_id: UUID) -> AnalysisScopesViewDocument:
        projects, papers, scopes = self._repositories()
        projects.load(project_id)
        document = scopes.load(project_id)
        available = {paper.paper_id for paper in papers.list(project_id)}
        return AnalysisScopesViewDocument(
            document=document,
            scopes=[
                AnalysisScopeView(
                    scope=scope,
                    available_paper_ids=[
                        paper_id for paper_id in scope.paper_ids if paper_id in available
                    ],
                    missing_paper_ids=[
                        paper_id for paper_id in scope.paper_ids if paper_id not in available
                    ],
                )
                for scope in document.scopes
            ],
        )

    def create(
        self,
        project_id: UUID,
        *,
        name: str,
        purpose: str,
        paper_ids: list[UUID],
        source_filter_snapshot: dict[str, str],
        expected_revision: int,
    ) -> AnalysisScopesViewDocument:
        projects, papers, scopes = self._repositories()
        projects.load(project_id)
        self._validate_papers(papers, project_id, paper_ids)
        current = scopes.load(project_id)
        created = AnalysisScope.create(
            name=name,
            purpose=purpose,
            paper_ids=paper_ids,
            source_filter_snapshot=source_filter_snapshot,
        )
        updated = current.model_copy(
            update={
                "revision": current.revision + 1,
                "updated_at": datetime.now(UTC),
                "scopes": [*current.scopes, created],
            }
        )
        scopes.save(updated, expected_revision=expected_revision)
        return self.list_scopes(project_id)

    def update(
        self,
        project_id: UUID,
        scope_id: UUID,
        *,
        name: str,
        purpose: str,
        paper_ids: list[UUID],
        source_filter_snapshot: dict[str, str],
        expected_revision: int,
    ) -> AnalysisScopesViewDocument:
        projects, papers, scopes = self._repositories()
        projects.load(project_id)
        self._validate_papers(papers, project_id, paper_ids)
        current = scopes.load(project_id)
        existing = next((scope for scope in current.scopes if scope.scope_id == scope_id), None)
        if existing is None:
            raise AnalysisScopeNotFoundError()
        replacement = existing.update(
            name=name,
            purpose=purpose,
            paper_ids=paper_ids,
            source_filter_snapshot=source_filter_snapshot,
        )
        updated = current.model_copy(
            update={
                "revision": current.revision + 1,
                "updated_at": datetime.now(UTC),
                "scopes": [
                    replacement if scope.scope_id == scope_id else scope for scope in current.scopes
                ],
            }
        )
        scopes.save(updated, expected_revision=expected_revision)
        return self.list_scopes(project_id)

    def delete(
        self,
        project_id: UUID,
        scope_id: UUID,
        *,
        expected_revision: int,
    ) -> AnalysisScopesViewDocument:
        projects, _, scopes = self._repositories()
        projects.load(project_id)
        current = scopes.load(project_id)
        if not any(scope.scope_id == scope_id for scope in current.scopes):
            raise AnalysisScopeNotFoundError()
        updated = current.model_copy(
            update={
                "revision": current.revision + 1,
                "updated_at": datetime.now(UTC),
                "scopes": [scope for scope in current.scopes if scope.scope_id != scope_id],
            }
        )
        scopes.save(updated, expected_revision=expected_revision)
        return self.list_scopes(project_id)

    @staticmethod
    def _validate_papers(
        papers: PaperRepository,
        project_id: UUID,
        paper_ids: list[UUID],
    ) -> None:
        available = {paper.paper_id for paper in papers.list(project_id)}
        invalid = [str(paper_id) for paper_id in paper_ids if paper_id not in available]
        if invalid:
            raise AnalysisScopePaperError(invalid)
