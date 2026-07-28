"""Assemble the real-time literature matrix from authoritative paper YAML."""

from __future__ import annotations

from uuid import UUID

from papermatrix.core.errors import AnalysisScopeNotFoundError
from papermatrix.core.schema_registry import SchemaRegistry
from papermatrix.domain.analysis_scope import AnalysisScope
from papermatrix.domain.literature_matrix import (
    AnalysisReadiness,
    LiteratureMatrix,
    LiteratureMatrixRow,
)
from papermatrix.domain.paper import AnalysisItem, Paper
from papermatrix.repositories.analysis_scope_repository import AnalysisScopeRepository
from papermatrix.repositories.paper_repository import PaperRepository
from papermatrix.repositories.project_repository import ProjectRepository
from papermatrix.services.workspace_service import WorkspaceService

METHOD_KINDS = {"method", "method_component", "mechanism", "contribution"}
LIMITATION_KINDS = {"author_limitation", "reviewer_limitation"}


class LiteratureMatrixService:
    def __init__(self, workspace: WorkspaceService, schemas: SchemaRegistry) -> None:
        self._workspace = workspace
        self._schemas = schemas

    def get(self, project_id: UUID, *, scope_id: UUID | None) -> LiteratureMatrix:
        self._workspace.require_workspace()
        ProjectRepository(self._workspace.root, self._schemas).load(project_id)
        papers = PaperRepository(self._workspace.root, self._schemas).list(project_id)
        paper_map = {paper.paper_id: paper for paper in papers}
        scope: AnalysisScope | None = None
        missing: list[UUID] = []
        if scope_id is not None:
            document = AnalysisScopeRepository(self._workspace.root, self._schemas).load(project_id)
            scope = next(
                (candidate for candidate in document.scopes if candidate.scope_id == scope_id),
                None,
            )
            if scope is None:
                raise AnalysisScopeNotFoundError()
            ordered_papers = [
                paper_map[paper_id] for paper_id in scope.paper_ids if paper_id in paper_map
            ]
            missing = [paper_id for paper_id in scope.paper_ids if paper_id not in paper_map]
        else:
            ordered_papers = sorted(
                papers,
                key=lambda paper: (paper.bibliography.title.casefold(), str(paper.paper_id)),
            )
        rows = [self._row(paper) for paper in ordered_papers]
        return LiteratureMatrix(
            project_id=project_id,
            scope_id=scope.scope_id if scope else None,
            scope_name=scope.name if scope else None,
            rows=rows,
            missing_paper_ids=missing,
            total=len(rows),
        )

    def _row(self, paper: Paper) -> LiteratureMatrixRow:
        items = paper.structured_summary.items
        method_ready = any(item.kind in METHOD_KINDS for item in items)
        experiment_ready = any(item.kind == "experiment" for item in items)
        limitation_ready = any(item.kind in LIMITATION_KINDS for item in items)
        evidence_ready = bool(paper.structured_summary.evidence_catalog) and any(
            item.evidence_ids for item in items
        )
        missing = [
            label
            for ready, label in (
                (method_ready, "方法"),
                (experiment_ready, "实验"),
                (limitation_ready, "局限"),
                (evidence_ready, "证据"),
            )
            if not ready
        ]
        return LiteratureMatrixRow(
            paper_id=paper.paper_id,
            title=paper.bibliography.title,
            short_title=paper.bibliography.short_title,
            authors=paper.bibliography.authors,
            year=paper.bibliography.year,
            venue=paper.bibliography.venue,
            group=paper.organization.group,
            reading_status=paper.organization.reading_status,
            source_status=paper.source.status,
            importance_score=paper.organization.importance_score,
            one_sentence_summary=paper.organization.one_sentence_summary,
            keywords=paper.bibliography.keywords,
            background=self._summaries(items, {"background", "scenario"}),
            research_problems=self._summaries(items, {"research_problem"}),
            related_work=self._summaries(items, {"related_work"}),
            methods=self._summaries(items, METHOD_KINDS),
            challenges=self._summaries(items, {"challenge"}),
            innovations=self._summaries(items, {"innovation"}),
            experiments=self._summaries(items, {"experiment"}),
            findings=self._summaries(items, {"finding"}),
            limitations=self._summaries(items, LIMITATION_KINDS),
            conditions=self._summaries(items, {"condition"}),
            evidence_count=len(paper.structured_summary.evidence_catalog),
            readiness=AnalysisReadiness(
                method_ready=method_ready,
                experiment_ready=experiment_ready,
                limitation_ready=limitation_ready,
                evidence_ready=evidence_ready,
                ready_count=4 - len(missing),
                missing_categories=missing,
            ),
            revision=paper.revision,
        )

    @staticmethod
    def _summaries(items: list[AnalysisItem], kinds: set[str]) -> list[str]:
        return [
            item.summary.strip() or item.title
            for item in items
            if item.kind in kinds and (item.summary.strip() or item.title.strip())
        ]
