"""Paper note and reading-question orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from papermatrix.core.errors import (
    AnalysisCandidateSelectionError,
    AnalysisItemNotFoundError,
    AnalysisItemSourceError,
    AnalysisPreviewStaleError,
    QuestionNotFoundError,
)
from papermatrix.core.schema_registry import SchemaRegistry
from papermatrix.domain.note_analysis import (
    CandidateImportResult,
    NoteAnalysisCandidate,
    NoteItemDocument,
    NoteItemSource,
    NoteItemUpdateResult,
    NoteParsePreview,
)
from papermatrix.domain.paper import AnalysisItem, Paper, PaperAnalysisDocument
from papermatrix.domain.paper_content import (
    EvidenceReference,
    PaperNote,
    QuestionsDocument,
    QuestionStatus,
    ReadingQuestion,
)
from papermatrix.repositories.paper_content_repository import PaperContentRepository
from papermatrix.repositories.paper_repository import PaperRepository
from papermatrix.repositories.project_repository import ProjectRepository
from papermatrix.services.markdown_analysis_parser import (
    add_item_anchors,
    note_item_fragment,
    parse_note_candidates,
    replace_note_item_fragment,
)
from papermatrix.services.workspace_service import WorkspaceService


class PaperContentService:
    def __init__(
        self,
        workspace: WorkspaceService,
        schemas: SchemaRegistry,
        note_template_path: Path,
    ) -> None:
        self._workspace = workspace
        self._schemas = schemas
        self._note_template_path = note_template_path

    def _repositories(
        self,
    ) -> tuple[ProjectRepository, PaperRepository, PaperContentRepository]:
        self._workspace.require_workspace()
        return (
            ProjectRepository(self._workspace.root, self._schemas),
            PaperRepository(self._workspace.root, self._schemas),
            PaperContentRepository(self._workspace.root, self._schemas),
        )

    def get_note(self, project_id: UUID, paper_id: UUID) -> PaperNote:
        projects, papers, content = self._repositories()
        projects.load(project_id)
        paper = papers.load(project_id, paper_id)
        existing = content.load_note(project_id, paper_id)
        if existing is not None:
            return existing
        return PaperNote(
            paper_id=paper_id,
            markdown=self._initial_note_body(
                paper_id=paper_id,
                title=paper.bibliography.short_title or paper.bibliography.title,
            ),
            revision=0,
            updated_at=datetime.now(UTC),
        )

    def save_note(
        self,
        project_id: UUID,
        paper_id: UUID,
        *,
        markdown: str,
        expected_revision: int,
    ) -> PaperNote:
        projects, papers, content = self._repositories()
        projects.load(project_id)
        papers.load(project_id, paper_id)
        note = PaperNote(
            paper_id=paper_id,
            markdown=markdown,
            revision=expected_revision + 1,
            updated_at=datetime.now(UTC),
        )
        return content.save_note(project_id, note, expected_revision=expected_revision)

    def get_supplement(self, project_id: UUID, paper_id: UUID) -> PaperNote:
        projects, papers, content = self._repositories()
        projects.load(project_id)
        papers.load(project_id, paper_id)
        existing = content.load_supplement(project_id, paper_id)
        if existing is not None:
            return existing
        return PaperNote(
            paper_id=paper_id,
            markdown="",
            revision=0,
            updated_at=datetime.now(UTC),
        )

    def save_supplement(
        self,
        project_id: UUID,
        paper_id: UUID,
        *,
        markdown: str,
        expected_revision: int,
    ) -> PaperNote:
        projects, papers, content = self._repositories()
        projects.load(project_id)
        papers.load(project_id, paper_id)
        note = PaperNote(
            paper_id=paper_id,
            markdown=markdown,
            revision=expected_revision + 1,
            updated_at=datetime.now(UTC),
        )
        return content.save_supplement(project_id, note, expected_revision=expected_revision)

    def get_questions(self, project_id: UUID, paper_id: UUID) -> QuestionsDocument:
        projects, papers, content = self._repositories()
        projects.load(project_id)
        papers.load(project_id, paper_id)
        return content.load_questions(project_id, paper_id)

    def preview_note_analysis(self, project_id: UUID, paper_id: UUID) -> NoteParsePreview:
        projects, papers, content = self._repositories()
        projects.load(project_id)
        paper = papers.load(project_id, paper_id)
        note = content.load_note(project_id, paper_id)
        warnings: list[str] = []
        if note is None:
            note = self.get_note(project_id, paper_id)
            warnings.append("当前显示尚未保存的默认模板。请先填写并保存笔记后再解析分析候选。")
        candidates = parse_note_candidates(
            paper_id,
            note.markdown,
            paper.structured_summary.items,
        )
        if not candidates and not warnings:
            warnings.append("没有找到已填写的结构化内容, 请检查模板标题和内容。")
        return NoteParsePreview(
            paper_id=paper_id,
            note_revision=note.revision,
            paper_revision=paper.revision,
            candidates=candidates,
            warnings=warnings,
        )

    def get_note_items(self, project_id: UUID, paper_id: UUID) -> NoteItemDocument:
        projects, papers, content = self._repositories()
        projects.load(project_id)
        paper = papers.load(project_id, paper_id)
        persisted_note = content.load_note(project_id, paper_id)
        note = persisted_note or self.get_note(project_id, paper_id)
        candidates = parse_note_candidates(
            paper_id,
            note.markdown,
            paper.structured_summary.items,
        )
        warnings: list[str] = []
        if persisted_note is None:
            warnings.append("当前显示尚未保存的默认模板。请先填写并保存笔记后再审阅分析候选。")
        elif not candidates:
            warnings.append("没有找到已填写的结构化内容。")
        by_id = {candidate.candidate_id: candidate for candidate in candidates}
        sources: list[NoteItemSource] = []
        for item in paper.structured_summary.items:
            candidate = by_id.get(item.item_id)
            if candidate is None:
                sources.append(
                    NoteItemSource(
                        item_id=item.item_id,
                        kind=item.kind,
                        title=item.title,
                        section_key=item.section_key,
                        section_title=item.section_title,
                        section_order=item.section_order,
                        markdown="",
                        source_fingerprint=item.source_fingerprint,
                        sync_status="missing",
                    )
                )
                continue
            sources.append(
                NoteItemSource(
                    item_id=item.item_id,
                    kind=item.kind,
                    title=item.title,
                    section_key=item.section_key,
                    section_title=item.section_title,
                    section_order=item.section_order,
                    markdown=note_item_fragment(note.markdown, candidate),
                    source_fingerprint=candidate.source_fingerprint,
                    sync_status=(
                        "synced"
                        if item.source_fingerprint == candidate.source_fingerprint
                        else "review_required"
                    ),
                )
            )
        pending = sum(candidate.sync_status != "unchanged" for candidate in candidates)
        return NoteItemDocument(
            paper_id=paper_id,
            note_revision=note.revision,
            paper_revision=paper.revision,
            items=sources,
            candidates=candidates,
            warnings=warnings,
            pending_candidate_count=pending,
        )

    def update_note_item(
        self,
        project_id: UUID,
        paper_id: UUID,
        item_id: UUID,
        *,
        markdown: str,
        expected_note_revision: int,
        expected_paper_revision: int,
        expected_source_fingerprint: str,
    ) -> NoteItemUpdateResult:
        projects, papers, content = self._repositories()
        projects.load(project_id)
        paper = papers.load(project_id, paper_id)
        if paper.revision != expected_paper_revision:
            raise AnalysisPreviewStaleError(
                resource="paper",
                expected=expected_paper_revision,
                actual=paper.revision,
            )
        existing = next(
            (item for item in paper.structured_summary.items if item.item_id == item_id),
            None,
        )
        if existing is None:
            raise AnalysisItemNotFoundError()
        note = content.load_note(project_id, paper_id)
        if note is None:
            raise AnalysisItemSourceError("结构化笔记尚未保存, 无法编辑条目来源。")
        if note.revision != expected_note_revision:
            raise AnalysisPreviewStaleError(
                resource="note",
                expected=expected_note_revision,
                actual=note.revision,
            )
        candidates = parse_note_candidates(
            paper_id,
            note.markdown,
            paper.structured_summary.items,
        )
        current = next(
            (candidate for candidate in candidates if candidate.candidate_id == item_id),
            None,
        )
        if current is None:
            raise AnalysisItemSourceError()
        if current.source_fingerprint != expected_source_fingerprint:
            raise AnalysisPreviewStaleError(
                resource="item_source",
                expected=expected_note_revision,
                actual=note.revision,
            )

        updated_markdown = replace_note_item_fragment(note.markdown, item_id, markdown)
        if updated_markdown == note.markdown and markdown.strip() != note_item_fragment(
            note.markdown, current
        ):
            raise AnalysisItemSourceError()
        parsed = parse_note_candidates(
            paper_id,
            updated_markdown,
            paper.structured_summary.items,
        )
        updated_candidate = next(
            (candidate for candidate in parsed if candidate.candidate_id == item_id),
            None,
        )
        if updated_candidate is None or updated_candidate.kind != existing.kind:
            raise AnalysisItemSourceError("条目修改后无法保留原类型和稳定 ID, 未写入任何文件。")

        updated_note = content.save_note(
            project_id,
            note.model_copy(
                update={
                    "markdown": updated_markdown,
                    "revision": note.revision + 1,
                    "updated_at": datetime.now(UTC),
                }
            ),
            expected_revision=expected_note_revision,
        )
        updated_item = self._item_from_candidate(
            existing,
            updated_candidate,
            source_note_revision=updated_note.revision,
        )
        items = [
            updated_item if item.item_id == item_id else item
            for item in paper.structured_summary.items
        ]
        updated_paper = paper.model_copy(
            update={
                "structured_summary": paper.structured_summary.model_copy(update={"items": items}),
                "revision": paper.revision + 1,
                "updated_at": datetime.now(UTC),
            }
        )
        updated_paper = papers.save(updated_paper, expected_revision=expected_paper_revision)
        return NoteItemUpdateResult(
            note=updated_note,
            analysis=self._analysis_document(updated_paper),
            item=updated_item,
        )

    def import_note_candidates(
        self,
        project_id: UUID,
        paper_id: UUID,
        *,
        candidate_ids: list[UUID],
        expected_note_revision: int,
        expected_paper_revision: int,
    ) -> CandidateImportResult:
        projects, papers, content = self._repositories()
        projects.load(project_id)
        paper = papers.load(project_id, paper_id)
        if paper.revision != expected_paper_revision:
            raise AnalysisPreviewStaleError(
                resource="paper",
                expected=expected_paper_revision,
                actual=paper.revision,
            )
        note = content.load_note(project_id, paper_id)
        actual_note_revision = note.revision if note else 0
        if actual_note_revision != expected_note_revision:
            raise AnalysisPreviewStaleError(
                resource="note",
                expected=expected_note_revision,
                actual=actual_note_revision,
            )
        if note is None:
            note = self.get_note(project_id, paper_id)
        candidates = parse_note_candidates(
            paper_id,
            note.markdown,
            paper.structured_summary.items,
        )
        by_id = {candidate.candidate_id: candidate for candidate in candidates}
        unknown = [str(candidate_id) for candidate_id in candidate_ids if candidate_id not in by_id]
        if unknown:
            raise AnalysisCandidateSelectionError(unknown)

        imported: list[AnalysisItem] = []
        skipped: list[UUID] = []
        existing_ids = {item.item_id for item in paper.structured_summary.items}
        selected_candidates = []
        synchronized: list[tuple[AnalysisItem, NoteAnalysisCandidate]] = []
        for candidate_id in dict.fromkeys(candidate_ids):
            candidate = by_id[candidate_id]
            existing = next(
                (item for item in paper.structured_summary.items if item.item_id == candidate_id),
                None,
            )
            if existing is not None and candidate.sync_status == "modified":
                synchronized.append((existing, candidate))
                continue
            if candidate.duplicate_item_id is not None or candidate_id in existing_ids:
                skipped.append(candidate_id)
                continue
            selected_candidates.append(candidate)
        anchored_markdown = add_item_anchors(note.markdown, selected_candidates)
        if anchored_markdown != note.markdown:
            note = content.save_note(
                project_id,
                note.model_copy(
                    update={
                        "markdown": anchored_markdown,
                        "revision": note.revision + 1,
                        "updated_at": datetime.now(UTC),
                    }
                ),
                expected_revision=expected_note_revision,
            )
        for candidate in selected_candidates:
            now = datetime.now(UTC)
            imported.append(
                AnalysisItem(
                    item_id=candidate.candidate_id,
                    kind=candidate.kind,
                    title=candidate.title,
                    summary=candidate.summary,
                    section_key=candidate.section_key,
                    section_title=candidate.section_title,
                    section_order=candidate.section_order,
                    source_anchor=candidate.source_anchor,
                    source_note_revision=note.revision,
                    source_fingerprint=candidate.source_fingerprint,
                    attributes=candidate.attributes,
                    evidence_refs=candidate.evidence_refs,
                    tags=["笔记解析"],
                    writing_uses=[],
                    created_at=now,
                    updated_at=now,
                )
            )
        synchronized_items = [
            self._item_from_candidate(existing, candidate, source_note_revision=note.revision)
            for existing, candidate in synchronized
        ]
        if imported or synchronized_items:
            synchronized_by_id = {item.item_id: item for item in synchronized_items}
            existing_items = [
                synchronized_by_id.get(item.item_id, item)
                for item in paper.structured_summary.items
            ]
            updated = paper.model_copy(
                update={
                    "structured_summary": paper.structured_summary.model_copy(
                        update={"items": [*existing_items, *imported]}
                    ),
                    "revision": paper.revision + 1,
                    "updated_at": datetime.now(UTC),
                }
            )
            paper = papers.save(updated, expected_revision=expected_paper_revision)
        return CandidateImportResult(
            analysis=self._analysis_document(paper),
            note=note,
            imported_items=imported,
            synchronized_items=synchronized_items,
            skipped_candidate_ids=skipped,
        )

    @staticmethod
    def _item_from_candidate(
        existing: AnalysisItem,
        candidate: NoteAnalysisCandidate,
        *,
        source_note_revision: int,
    ) -> AnalysisItem:
        return existing.model_copy(
            update={
                "kind": candidate.kind,
                "title": candidate.title,
                "summary": candidate.summary,
                "section_key": candidate.section_key,
                "section_title": candidate.section_title,
                "section_order": candidate.section_order,
                "source_anchor": candidate.source_anchor,
                "source_note_revision": source_note_revision,
                "source_fingerprint": candidate.source_fingerprint,
                "attributes": candidate.attributes,
                "evidence_refs": candidate.evidence_refs,
                "updated_at": datetime.now(UTC),
            }
        )

    def create_question(
        self,
        project_id: UUID,
        paper_id: UUID,
        *,
        question: str,
        status: QuestionStatus,
        answer: str,
        evidence: list[EvidenceReference],
        tags: list[str],
        expected_revision: int,
    ) -> QuestionsDocument:
        document, content = self._question_context(project_id, paper_id)
        item = ReadingQuestion.create(
            paper_id=paper_id,
            question=question,
            status=status,
            answer=answer,
            evidence=self._normalize_evidence(paper_id, evidence),
            tags=self._clean_tags(tags),
        )
        updated = document.model_copy(
            update={
                "questions": [*document.questions, item],
                "revision": document.revision + 1,
                "updated_at": datetime.now(UTC),
            }
        )
        return content.save_questions(project_id, updated, expected_revision=expected_revision)

    def update_question(
        self,
        project_id: UUID,
        paper_id: UUID,
        question_id: UUID,
        *,
        question: str,
        status: QuestionStatus,
        answer: str,
        evidence: list[EvidenceReference],
        tags: list[str],
        expected_revision: int,
    ) -> QuestionsDocument:
        document, content = self._question_context(project_id, paper_id)
        found = False
        questions: list[ReadingQuestion] = []
        for item in document.questions:
            if item.question_id != question_id:
                questions.append(item)
                continue
            found = True
            questions.append(
                ReadingQuestion.model_validate(
                    {
                        **item.model_dump(),
                        "question": question.strip(),
                        "status": status,
                        "answer": answer.strip(),
                        "evidence": self._normalize_evidence(paper_id, evidence),
                        "tags": self._clean_tags(tags),
                        "updated_at": datetime.now(UTC),
                    }
                )
            )
        if not found:
            raise QuestionNotFoundError()
        updated = document.model_copy(
            update={
                "questions": questions,
                "revision": document.revision + 1,
                "updated_at": datetime.now(UTC),
            }
        )
        return content.save_questions(project_id, updated, expected_revision=expected_revision)

    def delete_question(
        self,
        project_id: UUID,
        paper_id: UUID,
        question_id: UUID,
        *,
        expected_revision: int,
    ) -> QuestionsDocument:
        document, content = self._question_context(project_id, paper_id)
        questions = [item for item in document.questions if item.question_id != question_id]
        if len(questions) == len(document.questions):
            raise QuestionNotFoundError()
        updated = document.model_copy(
            update={
                "questions": questions,
                "revision": document.revision + 1,
                "updated_at": datetime.now(UTC),
            }
        )
        return content.save_questions(project_id, updated, expected_revision=expected_revision)

    def _question_context(
        self, project_id: UUID, paper_id: UUID
    ) -> tuple[QuestionsDocument, PaperContentRepository]:
        projects, papers, content = self._repositories()
        projects.load(project_id)
        papers.load(project_id, paper_id)
        return content.load_questions(project_id, paper_id), content

    def _initial_note_body(self, *, paper_id: UUID, title: str) -> str:
        template = self._note_template_path.read_text(encoding="utf-8")
        _, body = PaperContentRepository._parse_note(
            template.replace("{{ paper_id }}", str(paper_id))
            .replace("{{ updated_at }}", datetime.now(UTC).isoformat())
            .replace("{{ short_title }}", title)
        )
        return body

    @staticmethod
    def _clean_tags(tags: list[str]) -> list[str]:
        return list(dict.fromkeys(tag.strip() for tag in tags if tag.strip()))

    @staticmethod
    def _normalize_evidence(
        paper_id: UUID, evidence: list[EvidenceReference]
    ) -> list[EvidenceReference]:
        return [item.model_copy(update={"paper_id": paper_id}) for item in evidence]

    @staticmethod
    def _analysis_document(paper: Paper) -> PaperAnalysisDocument:
        return PaperAnalysisDocument(
            paper_id=paper.paper_id,
            revision=paper.revision,
            updated_at=paper.updated_at,
            items=paper.structured_summary.items,
        )
