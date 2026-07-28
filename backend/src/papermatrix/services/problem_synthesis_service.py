"""Orchestration for user-authored field-problem synthesis boards."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from papermatrix.core.errors import (
    PaperMatrixError,
    ProblemContributionConflictError,
    ProblemSynthesisNotFoundError,
    ProblemSynthesisReferenceError,
)
from papermatrix.core.schema_registry import SchemaRegistry
from papermatrix.domain.analysis_scope import AnalysisScope
from papermatrix.domain.item_links import ItemReference
from papermatrix.domain.paper import AnalysisItem, Paper
from papermatrix.domain.problem_synthesis import (
    FieldProblem,
    FieldProblemStatus,
    FieldProblemView,
    PaperContribution,
    ProblemBoard,
    ProblemBoardView,
    ProblemItemView,
    ProblemMatrixCell,
    ProblemMatrixPaper,
    ProblemMatrixRow,
    ProblemSynthesesDocument,
    ProblemSynthesesViewDocument,
    ProblemSynthesisMatrix,
    ResolutionLevel,
)
from papermatrix.repositories.analysis_scope_repository import AnalysisScopeRepository
from papermatrix.repositories.paper_repository import PaperRepository
from papermatrix.repositories.problem_synthesis_repository import ProblemSynthesisRepository
from papermatrix.repositories.project_repository import ProjectRepository
from papermatrix.services.workspace_service import WorkspaceService

METHOD_KINDS = {"method", "method_component", "mechanism", "innovation"}
EXPERIMENT_KINDS = {"experiment", "finding"}


class ProblemSynthesisService:
    def __init__(self, workspace: WorkspaceService, schemas: SchemaRegistry) -> None:
        self._workspace = workspace
        self._schemas = schemas

    def _repositories(
        self,
    ) -> tuple[
        ProjectRepository,
        PaperRepository,
        AnalysisScopeRepository,
        ProblemSynthesisRepository,
    ]:
        self._workspace.require_workspace()
        return (
            ProjectRepository(self._workspace.root, self._schemas),
            PaperRepository(self._workspace.root, self._schemas),
            AnalysisScopeRepository(self._workspace.root, self._schemas),
            ProblemSynthesisRepository(self._workspace.root, self._schemas),
        )

    def get(self, project_id: UUID) -> ProblemSynthesesViewDocument:
        projects, papers, scopes, syntheses = self._repositories()
        projects.load(project_id)
        document = syntheses.load(project_id)
        paper_map = {paper.paper_id: paper for paper in papers.list(project_id)}
        scope_ids = {scope.scope_id for scope in scopes.load(project_id).scopes}
        problem_ids = {problem.problem_id for problem in document.field_problems}
        board_views = [
            ProblemBoardView(
                board=board,
                scope_status="available" if board.scope_id in scope_ids else "missing",
                missing_problem_ids=[
                    problem_id for problem_id in board.problem_ids if problem_id not in problem_ids
                ],
                missing_paper_ids=[
                    paper_id for paper_id in board.paper_ids if paper_id not in paper_map
                ],
            )
            for board in document.boards
        ]
        field_views = [
            FieldProblemView(
                problem=problem,
                source_items=[
                    self._item_view(reference.paper_id, reference.item_id, paper_map)
                    for reference in problem.source_problem_refs
                ],
            )
            for problem in document.field_problems
        ]
        contribution_views = [
            view
            for contribution in document.paper_contributions
            for view in self._contribution_item_views(contribution, paper_map)
        ]
        dangling = sum(
            view.status != "available" for field in field_views for view in field.source_items
        ) + sum(view.status != "available" for view in contribution_views)
        return ProblemSynthesesViewDocument(
            document=document,
            boards=board_views,
            field_problems=field_views,
            dangling_reference_count=dangling,
        )

    def create_board(
        self,
        project_id: UUID,
        *,
        name: str,
        purpose: str,
        scope_id: UUID,
        problem_ids: list[UUID],
        paper_ids: list[UUID],
        expected_revision: int,
    ) -> ProblemSynthesesViewDocument:
        _, papers, scopes, syntheses = self._repositories()
        current = self._require_project_and_load(project_id, syntheses)
        self._validate_board(project_id, current, papers, scopes, scope_id, problem_ids, paper_ids)
        board = ProblemBoard.create(
            name=name,
            purpose=purpose,
            scope_id=scope_id,
            problem_ids=problem_ids,
            paper_ids=paper_ids,
        )
        self._save(
            syntheses,
            current,
            expected_revision,
            lambda document: document.model_copy(update={"boards": [*document.boards, board]}),
        )
        return self.get(project_id)

    def update_board(
        self,
        project_id: UUID,
        board_id: UUID,
        *,
        name: str,
        purpose: str,
        scope_id: UUID,
        problem_ids: list[UUID],
        paper_ids: list[UUID],
        expected_revision: int,
    ) -> ProblemSynthesesViewDocument:
        _, papers, scopes, syntheses = self._repositories()
        current = self._require_project_and_load(project_id, syntheses)
        existing = self._find_board(current, board_id)
        self._validate_board(project_id, current, papers, scopes, scope_id, problem_ids, paper_ids)
        replacement = existing.update(
            name=name,
            purpose=purpose,
            scope_id=scope_id,
            problem_ids=problem_ids,
            paper_ids=paper_ids,
        )
        self._save(
            syntheses,
            current,
            expected_revision,
            lambda document: document.model_copy(
                update={
                    "boards": [
                        replacement if board.board_id == board_id else board
                        for board in document.boards
                    ]
                }
            ),
        )
        return self.get(project_id)

    def delete_board(
        self, project_id: UUID, board_id: UUID, *, expected_revision: int
    ) -> ProblemSynthesesViewDocument:
        *_, syntheses = self._repositories()
        current = self._require_project_and_load(project_id, syntheses)
        self._find_board(current, board_id)
        self._save(
            syntheses,
            current,
            expected_revision,
            lambda document: document.model_copy(
                update={
                    "boards": [board for board in document.boards if board.board_id != board_id]
                }
            ),
        )
        return self.get(project_id)

    def create_problem(
        self,
        project_id: UUID,
        *,
        name: str,
        definition: str,
        scope_note: str,
        aliases: list[str],
        tags: list[str],
        status: FieldProblemStatus,
        source_problem_refs: list[ItemReference],
        expected_revision: int,
    ) -> ProblemSynthesesViewDocument:
        _, papers, _, syntheses = self._repositories()
        current = self._require_project_and_load(project_id, syntheses)
        self._validate_problem_refs(papers, project_id, source_problem_refs)
        problem = FieldProblem.create(
            name=name,
            definition=definition,
            scope_note=scope_note,
            aliases=aliases,
            tags=tags,
            status=status,
            source_problem_refs=source_problem_refs,
        )
        self._save(
            syntheses,
            current,
            expected_revision,
            lambda document: document.model_copy(
                update={"field_problems": [*document.field_problems, problem]}
            ),
        )
        return self.get(project_id)

    def update_problem(
        self,
        project_id: UUID,
        problem_id: UUID,
        *,
        name: str,
        definition: str,
        scope_note: str,
        aliases: list[str],
        tags: list[str],
        status: FieldProblemStatus,
        source_problem_refs: list[ItemReference],
        expected_revision: int,
    ) -> ProblemSynthesesViewDocument:
        _, papers, _, syntheses = self._repositories()
        current = self._require_project_and_load(project_id, syntheses)
        existing = self._find_problem(current, problem_id)
        self._validate_problem_refs(papers, project_id, source_problem_refs)
        replacement = existing.update(
            name=name,
            definition=definition,
            scope_note=scope_note,
            aliases=aliases,
            tags=tags,
            status=status,
            source_problem_refs=source_problem_refs,
        )
        self._save(
            syntheses,
            current,
            expected_revision,
            lambda document: document.model_copy(
                update={
                    "field_problems": [
                        replacement if problem.problem_id == problem_id else problem
                        for problem in document.field_problems
                    ]
                }
            ),
        )
        return self.get(project_id)

    def delete_problem(
        self, project_id: UUID, problem_id: UUID, *, expected_revision: int
    ) -> ProblemSynthesesViewDocument:
        *_, syntheses = self._repositories()
        current = self._require_project_and_load(project_id, syntheses)
        self._find_problem(current, problem_id)
        if any(problem_id in board.problem_ids for board in current.boards) or any(
            contribution.problem_id == problem_id for contribution in current.paper_contributions
        ):
            raise ProblemSynthesisReferenceError("problem_id", "领域问题仍被归纳板或论文贡献引用")
        self._save(
            syntheses,
            current,
            expected_revision,
            lambda document: document.model_copy(
                update={
                    "field_problems": [
                        problem
                        for problem in document.field_problems
                        if problem.problem_id != problem_id
                    ]
                }
            ),
        )
        return self.get(project_id)

    def create_contribution(
        self,
        project_id: UUID,
        *,
        problem_id: UUID,
        paper_id: UUID,
        research_problem_item_id: UUID,
        method_item_id: UUID | None,
        experiment_item_id: UUID | None,
        resolution_level: ResolutionLevel,
        rationale: str,
        supporting_evidence_ids: list[UUID],
        counter_evidence: str,
        conditions: str,
        user_judgment: str,
        expected_revision: int,
    ) -> ProblemSynthesesViewDocument:
        _, papers, _, syntheses = self._repositories()
        current = self._require_project_and_load(project_id, syntheses)
        if any(
            value.problem_id == problem_id and value.paper_id == paper_id
            for value in current.paper_contributions
        ):
            raise ProblemContributionConflictError()
        self._validate_contribution(
            project_id,
            current,
            papers,
            problem_id=problem_id,
            paper_id=paper_id,
            research_problem_item_id=research_problem_item_id,
            method_item_id=method_item_id,
            experiment_item_id=experiment_item_id,
            supporting_evidence_ids=supporting_evidence_ids,
        )
        contribution = PaperContribution.create(
            problem_id=problem_id,
            paper_id=paper_id,
            research_problem_item_id=research_problem_item_id,
            method_item_id=method_item_id,
            experiment_item_id=experiment_item_id,
            resolution_level=resolution_level,
            rationale=rationale,
            supporting_evidence_ids=supporting_evidence_ids,
            counter_evidence=counter_evidence,
            conditions=conditions,
            user_judgment=user_judgment,
        )
        self._save(
            syntheses,
            current,
            expected_revision,
            lambda document: document.model_copy(
                update={
                    "paper_contributions": [
                        *document.paper_contributions,
                        contribution,
                    ]
                }
            ),
        )
        return self.get(project_id)

    def update_contribution(
        self,
        project_id: UUID,
        contribution_id: UUID,
        *,
        problem_id: UUID,
        paper_id: UUID,
        research_problem_item_id: UUID,
        method_item_id: UUID | None,
        experiment_item_id: UUID | None,
        resolution_level: ResolutionLevel,
        rationale: str,
        supporting_evidence_ids: list[UUID],
        counter_evidence: str,
        conditions: str,
        user_judgment: str,
        expected_revision: int,
    ) -> ProblemSynthesesViewDocument:
        _, papers, _, syntheses = self._repositories()
        current = self._require_project_and_load(project_id, syntheses)
        existing = self._find_contribution(current, contribution_id)
        if any(
            value.contribution_id != contribution_id
            and value.problem_id == problem_id
            and value.paper_id == paper_id
            for value in current.paper_contributions
        ):
            raise ProblemContributionConflictError()
        self._validate_contribution(
            project_id,
            current,
            papers,
            problem_id=problem_id,
            paper_id=paper_id,
            research_problem_item_id=research_problem_item_id,
            method_item_id=method_item_id,
            experiment_item_id=experiment_item_id,
            supporting_evidence_ids=supporting_evidence_ids,
        )
        replacement = existing.update(
            problem_id=problem_id,
            paper_id=paper_id,
            research_problem_item_id=research_problem_item_id,
            method_item_id=method_item_id,
            experiment_item_id=experiment_item_id,
            resolution_level=resolution_level,
            rationale=rationale,
            supporting_evidence_ids=supporting_evidence_ids,
            counter_evidence=counter_evidence,
            conditions=conditions,
            user_judgment=user_judgment,
        )
        self._save(
            syntheses,
            current,
            expected_revision,
            lambda document: document.model_copy(
                update={
                    "paper_contributions": [
                        replacement
                        if contribution.contribution_id == contribution_id
                        else contribution
                        for contribution in document.paper_contributions
                    ]
                }
            ),
        )
        return self.get(project_id)

    def delete_contribution(
        self,
        project_id: UUID,
        contribution_id: UUID,
        *,
        expected_revision: int,
    ) -> ProblemSynthesesViewDocument:
        *_, syntheses = self._repositories()
        current = self._require_project_and_load(project_id, syntheses)
        self._find_contribution(current, contribution_id)
        self._save(
            syntheses,
            current,
            expected_revision,
            lambda document: document.model_copy(
                update={
                    "paper_contributions": [
                        contribution
                        for contribution in document.paper_contributions
                        if contribution.contribution_id != contribution_id
                    ]
                }
            ),
        )
        return self.get(project_id)

    def matrix(self, project_id: UUID, board_id: UUID) -> ProblemSynthesisMatrix:
        projects, papers, _, syntheses = self._repositories()
        projects.load(project_id)
        document = syntheses.load(project_id)
        board = self._find_board(document, board_id)
        paper_map = {paper.paper_id: paper for paper in papers.list(project_id)}
        problem_map = {problem.problem_id: problem for problem in document.field_problems}
        contribution_map = {
            (value.problem_id, value.paper_id): value for value in document.paper_contributions
        }
        warnings: list[str] = []
        available_paper_ids = [paper_id for paper_id in board.paper_ids if paper_id in paper_map]
        for paper_id in board.paper_ids:
            if paper_id not in paper_map:
                warnings.append(f"论文 {paper_id} 已缺失, 未生成对应列。")
        rows: list[ProblemMatrixRow] = []
        for problem_id in board.problem_ids:
            problem = problem_map.get(problem_id)
            if problem is None:
                warnings.append(f"领域问题 {problem_id} 已缺失, 未生成对应行。")
                continue
            cells: list[ProblemMatrixCell] = []
            for paper_id in available_paper_ids:
                contribution = contribution_map.get((problem_id, paper_id))
                paper = paper_map[paper_id]
                evidence_ids = {
                    evidence.evidence_id for evidence in paper.structured_summary.evidence_catalog
                }
                cells.append(
                    ProblemMatrixCell(
                        paper_id=paper_id,
                        contribution=contribution,
                        research_problem=self._optional_item_view(
                            paper_id,
                            contribution.research_problem_item_id if contribution else None,
                            paper_map,
                        ),
                        method=self._optional_item_view(
                            paper_id,
                            contribution.method_item_id if contribution else None,
                            paper_map,
                        ),
                        experiment=self._optional_item_view(
                            paper_id,
                            contribution.experiment_item_id if contribution else None,
                            paper_map,
                        ),
                        missing_evidence_ids=[
                            evidence_id
                            for evidence_id in (
                                contribution.supporting_evidence_ids if contribution else []
                            )
                            if evidence_id not in evidence_ids
                        ],
                    )
                )
            rows.append(ProblemMatrixRow(problem=problem, cells=cells))
        return ProblemSynthesisMatrix(
            project_id=project_id,
            source_revision=document.revision,
            board=board,
            papers=[
                ProblemMatrixPaper(
                    paper_id=paper_id,
                    title=paper_map[paper_id].bibliography.title,
                )
                for paper_id in available_paper_ids
            ],
            rows=rows,
            warnings=warnings,
        )

    def _require_project_and_load(
        self, project_id: UUID, syntheses: ProblemSynthesisRepository
    ) -> ProblemSynthesesDocument:
        projects, *_ = self._repositories()
        projects.load(project_id)
        return syntheses.load(project_id)

    @staticmethod
    def _save(
        repository: ProblemSynthesisRepository,
        current: ProblemSynthesesDocument,
        expected_revision: int,
        mutate: Callable[[ProblemSynthesesDocument], ProblemSynthesesDocument],
    ) -> None:
        updated = mutate(current).model_copy(
            update={
                "revision": current.revision + 1,
                "updated_at": datetime.now(UTC),
            }
        )
        repository.save(updated, expected_revision=expected_revision)

    @staticmethod
    def _find_board(document: ProblemSynthesesDocument, board_id: UUID) -> ProblemBoard:
        value = next((board for board in document.boards if board.board_id == board_id), None)
        if value is None:
            raise ProblemSynthesisNotFoundError("board")
        return value

    @staticmethod
    def _find_problem(document: ProblemSynthesesDocument, problem_id: UUID) -> FieldProblem:
        value = next(
            (problem for problem in document.field_problems if problem.problem_id == problem_id),
            None,
        )
        if value is None:
            raise ProblemSynthesisNotFoundError("field_problem")
        return value

    @staticmethod
    def _find_contribution(
        document: ProblemSynthesesDocument, contribution_id: UUID
    ) -> PaperContribution:
        value = next(
            (
                contribution
                for contribution in document.paper_contributions
                if contribution.contribution_id == contribution_id
            ),
            None,
        )
        if value is None:
            raise ProblemSynthesisNotFoundError("paper_contribution")
        return value

    def _validate_board(
        self,
        project_id: UUID,
        document: ProblemSynthesesDocument,
        papers: PaperRepository,
        scopes: AnalysisScopeRepository,
        scope_id: UUID,
        problem_ids: list[UUID],
        paper_ids: list[UUID],
    ) -> None:
        scope = next(
            (scope for scope in scopes.load(project_id).scopes if scope.scope_id == scope_id),
            None,
        )
        if scope is None:
            raise ProblemSynthesisReferenceError("scope_id", "分析集合不存在")
        known_problems = {problem.problem_id for problem in document.field_problems}
        if invalid := [
            str(problem_id) for problem_id in problem_ids if problem_id not in known_problems
        ]:
            raise ProblemSynthesisReferenceError("problem_ids", f"不存在: {invalid}")
        self._require_scope_papers(project_id, papers, scope, paper_ids)

    @staticmethod
    def _require_scope_papers(
        project_id: UUID,
        papers: PaperRepository,
        scope: AnalysisScope,
        paper_ids: list[UUID],
    ) -> None:
        available = {paper.paper_id for paper in papers.list(project_id)}
        scope_ids = set(scope.paper_ids)
        invalid = [
            str(paper_id)
            for paper_id in paper_ids
            if paper_id not in scope_ids or paper_id not in available
        ]
        if invalid:
            raise ProblemSynthesisReferenceError(
                "paper_ids", f"论文不在分析集合或当前项目中: {invalid}"
            )

    def _validate_problem_refs(
        self,
        papers: PaperRepository,
        project_id: UUID,
        references: list[ItemReference],
    ) -> None:
        for reference in references:
            paper = self._load_paper(papers, project_id, reference.paper_id, "source_problem_refs")
            self._require_item_kind(
                paper,
                reference.item_id,
                {"research_problem"},
                "source_problem_refs",
            )

    def _validate_contribution(
        self,
        project_id: UUID,
        document: ProblemSynthesesDocument,
        papers: PaperRepository,
        *,
        problem_id: UUID,
        paper_id: UUID,
        research_problem_item_id: UUID,
        method_item_id: UUID | None,
        experiment_item_id: UUID | None,
        supporting_evidence_ids: list[UUID],
    ) -> None:
        self._find_problem(document, problem_id)
        paper = self._load_paper(papers, project_id, paper_id, "paper_id")
        self._require_item_kind(
            paper,
            research_problem_item_id,
            {"research_problem"},
            "research_problem_item_id",
        )
        if method_item_id is not None:
            self._require_item_kind(paper, method_item_id, METHOD_KINDS, "method_item_id")
        if experiment_item_id is not None:
            self._require_item_kind(
                paper, experiment_item_id, EXPERIMENT_KINDS, "experiment_item_id"
            )
        known_evidence = {
            evidence.evidence_id for evidence in paper.structured_summary.evidence_catalog
        }
        missing = [
            str(evidence_id)
            for evidence_id in supporting_evidence_ids
            if evidence_id not in known_evidence
        ]
        if missing:
            raise ProblemSynthesisReferenceError(
                "supporting_evidence_ids", f"证据不存在: {missing}"
            )

    @staticmethod
    def _load_paper(papers: PaperRepository, project_id: UUID, paper_id: UUID, field: str) -> Paper:
        try:
            return papers.load(project_id, paper_id)
        except PaperMatrixError as exc:
            raise ProblemSynthesisReferenceError(field, "论文不属于当前项目") from exc

    @staticmethod
    def _require_item_kind(
        paper: Paper,
        item_id: UUID,
        kinds: set[str],
        field: str,
    ) -> AnalysisItem:
        item = next(
            (value for value in paper.structured_summary.items if value.item_id == item_id),
            None,
        )
        if item is None or item.kind not in kinds:
            raise ProblemSynthesisReferenceError(field, f"条目不存在或类型应为 {sorted(kinds)}")
        return item

    @staticmethod
    def _item_view(paper_id: UUID, item_id: UUID, papers: dict[UUID, Paper]) -> ProblemItemView:
        paper = papers.get(paper_id)
        if paper is None:
            return ProblemItemView(paper_id=paper_id, item_id=item_id, status="missing_paper")
        item = next(
            (value for value in paper.structured_summary.items if value.item_id == item_id),
            None,
        )
        if item is None:
            return ProblemItemView(
                paper_id=paper_id,
                item_id=item_id,
                status="missing_item",
                paper_title=paper.bibliography.title,
            )
        return ProblemItemView(
            paper_id=paper_id,
            item_id=item_id,
            status="available",
            paper_title=paper.bibliography.title,
            item_title=item.title,
        )

    def _optional_item_view(
        self,
        paper_id: UUID,
        item_id: UUID | None,
        papers: dict[UUID, Paper],
    ) -> ProblemItemView | None:
        if item_id is None:
            return None
        return self._item_view(paper_id, item_id, papers)

    def _contribution_item_views(
        self, contribution: PaperContribution, papers: dict[UUID, Paper]
    ) -> list[ProblemItemView]:
        ids = [
            contribution.research_problem_item_id,
            contribution.method_item_id,
            contribution.experiment_item_id,
        ]
        return [
            self._item_view(contribution.paper_id, item_id, papers)
            for item_id in ids
            if item_id is not None
        ]
