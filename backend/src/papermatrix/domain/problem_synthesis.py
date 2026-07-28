"""Field-problem synthesis boards and paper contribution judgments."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

from papermatrix.domain.item_links import ItemReference

ResolutionLevel = Literal[
    "resolved",
    "partially_resolved",
    "indirectly_mitigated",
    "not_resolved",
    "not_addressed",
    "not_applicable",
    "unknown",
]
FieldProblemStatus = Literal["active", "archived"]


class ProblemBoard(BaseModel):
    board_id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=120)
    purpose: str = Field(default="", max_length=5000)
    scope_id: UUID
    problem_ids: list[UUID] = Field(default_factory=list)
    paper_ids: list[UUID] = Field(min_length=1)
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def ordered_ids_must_be_unique(self) -> ProblemBoard:
        if len(self.problem_ids) != len(set(self.problem_ids)):
            raise ValueError("problem board problem IDs must be unique")
        if len(self.paper_ids) != len(set(self.paper_ids)):
            raise ValueError("problem board paper IDs must be unique")
        return self

    @classmethod
    def create(
        cls,
        *,
        name: str,
        purpose: str,
        scope_id: UUID,
        problem_ids: list[UUID],
        paper_ids: list[UUID],
    ) -> ProblemBoard:
        now = datetime.now(UTC)
        return cls(
            name=name.strip(),
            purpose=purpose.strip(),
            scope_id=scope_id,
            problem_ids=problem_ids,
            paper_ids=paper_ids,
            created_at=now,
            updated_at=now,
        )

    def update(
        self,
        *,
        name: str,
        purpose: str,
        scope_id: UUID,
        problem_ids: list[UUID],
        paper_ids: list[UUID],
    ) -> ProblemBoard:
        return self.model_copy(
            update={
                "name": name.strip(),
                "purpose": purpose.strip(),
                "scope_id": scope_id,
                "problem_ids": problem_ids,
                "paper_ids": paper_ids,
                "updated_at": datetime.now(UTC),
            }
        )


class FieldProblem(BaseModel):
    problem_id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=300)
    definition: str = Field(min_length=1, max_length=20000)
    scope_note: str = Field(default="", max_length=10000)
    aliases: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    status: FieldProblemStatus = "active"
    source_problem_refs: list[ItemReference] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def source_refs_must_be_unique(self) -> FieldProblem:
        keys = [(ref.paper_id, ref.item_id) for ref in self.source_problem_refs]
        if len(keys) != len(set(keys)):
            raise ValueError("field problem source references must be unique")
        return self

    @classmethod
    def create(
        cls,
        *,
        name: str,
        definition: str,
        scope_note: str,
        aliases: list[str],
        tags: list[str],
        status: FieldProblemStatus,
        source_problem_refs: list[ItemReference],
    ) -> FieldProblem:
        now = datetime.now(UTC)
        return cls(
            name=name.strip(),
            definition=definition.strip(),
            scope_note=scope_note.strip(),
            aliases=list(dict.fromkeys(value.strip() for value in aliases if value.strip())),
            tags=list(dict.fromkeys(value.strip() for value in tags if value.strip())),
            status=status,
            source_problem_refs=source_problem_refs,
            created_at=now,
            updated_at=now,
        )

    def update(
        self,
        *,
        name: str,
        definition: str,
        scope_note: str,
        aliases: list[str],
        tags: list[str],
        status: FieldProblemStatus,
        source_problem_refs: list[ItemReference],
    ) -> FieldProblem:
        return self.model_copy(
            update={
                "name": name.strip(),
                "definition": definition.strip(),
                "scope_note": scope_note.strip(),
                "aliases": list(dict.fromkeys(value.strip() for value in aliases if value.strip())),
                "tags": list(dict.fromkeys(value.strip() for value in tags if value.strip())),
                "status": status,
                "source_problem_refs": source_problem_refs,
                "updated_at": datetime.now(UTC),
            }
        )


class PaperContribution(BaseModel):
    contribution_id: UUID = Field(default_factory=uuid4)
    problem_id: UUID
    paper_id: UUID
    research_problem_item_id: UUID
    method_item_id: UUID | None = None
    experiment_item_id: UUID | None = None
    resolution_level: ResolutionLevel = "unknown"
    rationale: str = Field(default="", max_length=20000)
    supporting_evidence_ids: list[UUID] = Field(default_factory=list)
    counter_evidence: str = Field(default="", max_length=20000)
    conditions: str = Field(default="", max_length=20000)
    user_judgment: str = Field(default="", max_length=20000)
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
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
    ) -> PaperContribution:
        now = datetime.now(UTC)
        return cls(
            problem_id=problem_id,
            paper_id=paper_id,
            research_problem_item_id=research_problem_item_id,
            method_item_id=method_item_id,
            experiment_item_id=experiment_item_id,
            resolution_level=resolution_level,
            rationale=rationale.strip(),
            supporting_evidence_ids=list(dict.fromkeys(supporting_evidence_ids)),
            counter_evidence=counter_evidence.strip(),
            conditions=conditions.strip(),
            user_judgment=user_judgment.strip(),
            created_at=now,
            updated_at=now,
        )

    def update(
        self,
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
    ) -> PaperContribution:
        return self.model_copy(
            update={
                "problem_id": problem_id,
                "paper_id": paper_id,
                "research_problem_item_id": research_problem_item_id,
                "method_item_id": method_item_id,
                "experiment_item_id": experiment_item_id,
                "resolution_level": resolution_level,
                "rationale": rationale.strip(),
                "supporting_evidence_ids": list(dict.fromkeys(supporting_evidence_ids)),
                "counter_evidence": counter_evidence.strip(),
                "conditions": conditions.strip(),
                "user_judgment": user_judgment.strip(),
                "updated_at": datetime.now(UTC),
            }
        )


class ProblemSynthesesDocument(BaseModel):
    schema_version: Literal[1] = 1
    project_id: UUID
    revision: int = Field(ge=0)
    updated_at: datetime
    boards: list[ProblemBoard] = Field(default_factory=list)
    field_problems: list[FieldProblem] = Field(default_factory=list)
    paper_contributions: list[PaperContribution] = Field(default_factory=list)

    @model_validator(mode="after")
    def ids_and_contribution_cells_must_be_unique(self) -> ProblemSynthesesDocument:
        for values, label in (
            ([board.board_id for board in self.boards], "problem board"),
            ([problem.problem_id for problem in self.field_problems], "field problem"),
            (
                [contribution.contribution_id for contribution in self.paper_contributions],
                "paper contribution",
            ),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"{label} IDs must be unique")
        cells = [
            (contribution.problem_id, contribution.paper_id)
            for contribution in self.paper_contributions
        ]
        if len(cells) != len(set(cells)):
            raise ValueError("only one contribution is allowed per problem and paper")
        return self

    @classmethod
    def empty(cls, project_id: UUID) -> ProblemSynthesesDocument:
        return cls(project_id=project_id, revision=0, updated_at=datetime.now(UTC))


ReferenceStatus = Literal["available", "missing_paper", "missing_item"]


class ProblemItemView(BaseModel):
    paper_id: UUID
    item_id: UUID
    status: ReferenceStatus
    paper_title: str | None = None
    item_title: str | None = None


class ProblemBoardView(BaseModel):
    board: ProblemBoard
    scope_status: Literal["available", "missing"]
    missing_problem_ids: list[UUID]
    missing_paper_ids: list[UUID]


class FieldProblemView(BaseModel):
    problem: FieldProblem
    source_items: list[ProblemItemView]


class ProblemSynthesesViewDocument(BaseModel):
    document: ProblemSynthesesDocument
    boards: list[ProblemBoardView]
    field_problems: list[FieldProblemView]
    dangling_reference_count: int = Field(ge=0)


class ProblemMatrixPaper(BaseModel):
    paper_id: UUID
    title: str


class ProblemMatrixCell(BaseModel):
    paper_id: UUID
    contribution: PaperContribution | None
    research_problem: ProblemItemView | None
    method: ProblemItemView | None
    experiment: ProblemItemView | None
    missing_evidence_ids: list[UUID] = Field(default_factory=list)


class ProblemMatrixRow(BaseModel):
    problem: FieldProblem
    cells: list[ProblemMatrixCell]


class ProblemSynthesisMatrix(BaseModel):
    project_id: UUID
    source_revision: int
    board: ProblemBoard
    papers: list[ProblemMatrixPaper]
    rows: list[ProblemMatrixRow]
    warnings: list[str] = Field(default_factory=list)
