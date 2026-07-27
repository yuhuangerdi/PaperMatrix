"""Paper scanning, registration and source-state orchestration."""

from __future__ import annotations

import builtins
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID, uuid4

from papermatrix.core.errors import (
    AnalysisItemNotFoundError,
    PaperConflictError,
    PaperUploadTooLargeError,
)
from papermatrix.core.paths import PathPolicy
from papermatrix.core.schema_registry import SchemaRegistry
from papermatrix.domain.paper import (
    AnalysisItem,
    AnalysisItemKind,
    Paper,
    PaperAnalysisDocument,
    PaperList,
    PaperSource,
    PaperSummary,
    SourceStatus,
    WritingUse,
)
from papermatrix.domain.paper_content import EvidenceReference
from papermatrix.repositories.paper_repository import PaperRepository
from papermatrix.repositories.project_repository import ProjectRepository
from papermatrix.services.paper_content_service import PaperContentService
from papermatrix.services.pdf_inspector import inspect_path, inspect_upload
from papermatrix.services.workspace_service import WorkspaceService


@dataclass(frozen=True)
class ScanCandidate:
    candidate_id: str
    display_path: str
    filename: str
    title: str
    page_count: int | None
    size_bytes: int
    readable: bool


class PaperService:
    def __init__(
        self,
        workspace: WorkspaceService,
        schemas: SchemaRegistry,
        content: PaperContentService,
        *,
        max_scan_files: int,
        max_upload_bytes: int,
    ) -> None:
        self._workspace = workspace
        self._schemas = schemas
        self._content = content
        self._max_scan_files = max_scan_files
        self._max_upload_bytes = max_upload_bytes
        self._scans: dict[str, dict[str, Path]] = {}

    def _repositories(self) -> tuple[ProjectRepository, PaperRepository]:
        self._workspace.require_workspace()
        return (
            ProjectRepository(self._workspace.root, self._schemas),
            PaperRepository(self._workspace.root, self._schemas),
        )

    def _path_policy(self) -> PathPolicy:
        workspace = self._workspace.require_workspace()
        return PathPolicy(tuple(Path(path) for path in workspace.allowed_paper_roots))

    def scan(
        self, *, directory: str, recursive: bool
    ) -> tuple[str, list[ScanCandidate], list[str]]:
        policy = self._path_policy()
        root = policy.validate_scan_directory(directory)
        paths = root.rglob("*") if recursive else root.iterdir()
        pdf_paths = sorted(
            (path for path in paths if path.is_file() and path.suffix.lower() == ".pdf"),
            key=lambda path: path.name.casefold(),
        )
        warnings: list[str] = []
        if len(pdf_paths) > self._max_scan_files:
            pdf_paths = pdf_paths[: self._max_scan_files]
            warnings.append(f"候选超过上限, 仅显示前 {self._max_scan_files} 个文件。")

        scan_token = str(uuid4())
        stored: dict[str, Path] = {}
        candidates: list[ScanCandidate] = []
        strict_hashing = self._workspace.require_workspace().settings.strict_hashing
        for raw_path in pdf_paths:
            path = policy.validate_pdf(raw_path)
            source, metadata = inspect_path(path, strict_hashing=strict_hashing)
            candidate_id = str(uuid4())
            stored[candidate_id] = path
            candidates.append(
                ScanCandidate(
                    candidate_id=candidate_id,
                    display_path=PathPolicy.redact(path),
                    filename=path.name,
                    title=metadata.title or path.stem,
                    page_count=source.page_count,
                    size_bytes=source.size_bytes or 0,
                    readable=metadata.readable,
                )
            )
        self._scans = {scan_token: stored}
        return scan_token, candidates, warnings

    def import_candidates(
        self, project_id: UUID, *, scan_token: str, candidate_ids: list[str]
    ) -> tuple[list[Paper], list[dict[str, str]]]:
        scan = self._scans.get(scan_token)
        if scan is None:
            raise PaperConflictError("扫描结果已失效, 请重新扫描。")
        imported: list[Paper] = []
        skipped: list[dict[str, str]] = []
        for candidate_id in candidate_ids:
            path = scan.get(candidate_id)
            if path is None:
                skipped.append({"candidate_id": candidate_id, "reason": "候选不存在"})
                continue
            try:
                imported.append(self.link_path(project_id, str(path)))
            except PaperConflictError:
                skipped.append({"candidate_id": candidate_id, "reason": "项目中已登记"})
        return imported, skipped

    def link_path(self, project_id: UUID, raw_path: str) -> Paper:
        projects, papers = self._repositories()
        projects.load(project_id)
        path = self._path_policy().validate_pdf(raw_path)
        if any(item.source.path == str(path) for item in papers.list(project_id)):
            raise PaperConflictError()
        source, metadata = inspect_path(
            path,
            strict_hashing=self._workspace.require_workspace().settings.strict_hashing,
        )
        return self._create_with_initial_note(
            papers,
            Paper.create(
                project_id=project_id,
                source=source,
                title=metadata.title or path.stem,
                authors=metadata.authors,
            ),
        )

    def upload(
        self,
        project_id: UUID,
        *,
        filename: str,
        content: bytes,
        title: str | None = None,
    ) -> Paper:
        projects, papers = self._repositories()
        projects.load(project_id)
        if len(content) > self._max_upload_bytes:
            raise PaperUploadTooLargeError(self._max_upload_bytes)
        if Path(filename).suffix.lower() != ".pdf":
            raise PaperConflictError("只能上传 PDF 文件。")
        source, metadata = inspect_upload(filename, content)
        return self._create_with_initial_note(
            papers,
            Paper.create(
                project_id=project_id,
                source=source,
                title=(
                    title.strip()
                    if title and title.strip()
                    else metadata.title or Path(filename).stem
                ),
                authors=metadata.authors,
            ),
        )

    def create_manual(self, project_id: UUID, *, title: str) -> Paper:
        projects, papers = self._repositories()
        projects.load(project_id)
        return self._create_with_initial_note(
            papers,
            Paper.create(
                project_id=project_id,
                source=PaperSource(status="unlinked"),
                title=title.strip(),
            ),
        )

    def _create_with_initial_note(
        self,
        papers: PaperRepository,
        paper: Paper,
    ) -> Paper:
        created = papers.create(paper)
        self._content.initialize_note(created.project_id, created)
        return created

    def get(self, project_id: UUID, paper_id: UUID) -> Paper:
        projects, papers = self._repositories()
        projects.load(project_id)
        return self._with_current_status(papers.load(project_id, paper_id))

    def list(
        self,
        project_id: UUID,
        *,
        query: str,
        source_status: SourceStatus | None,
        group: str | None,
        sort: str,
        page: int,
        page_size: int,
    ) -> PaperList:
        projects, papers = self._repositories()
        projects.load(project_id)
        valid_records, invalid_records = papers.list_with_invalid(project_id)
        records = [self._with_current_status(item) for item in valid_records]
        normalized = query.strip().casefold()
        if normalized:
            records = [
                item
                for item in records
                if normalized
                in " ".join(
                    [
                        item.bibliography.title,
                        item.bibliography.short_title,
                        *item.bibliography.authors,
                        *item.organization.topics,
                        *item.organization.tags,
                    ]
                ).casefold()
            ]
        if source_status:
            records = [item for item in records if item.source.status == source_status]
        if group:
            records = [item for item in records if item.organization.group == group]
        reverse = sort.startswith("-")
        field = sort.removeprefix("-")
        if field == "title":
            records.sort(key=lambda item: item.bibliography.title.casefold(), reverse=reverse)
        elif field == "year":
            records.sort(key=lambda item: item.bibliography.year or 0, reverse=reverse)
        else:
            records.sort(key=lambda item: item.updated_at, reverse=reverse)
        total = len(records)
        start = (page - 1) * page_size
        items = [self._summary(item) for item in records[start : start + page_size]]
        return PaperList(
            items=items,
            invalid_items=invalid_records,
            total=total,
            invalid_total=len(invalid_records),
            page=page,
            page_size=page_size,
        )

    def update_basic_information(
        self,
        project_id: UUID,
        paper_id: UUID,
        *,
        title: str,
        authors: builtins.list[str],
        affiliations: builtins.list[str],
        venue: str | None,
        publication_date: date | None,
        reading_date: date | None,
        citation_count: int | None,
        language: str | None,
        keywords: builtins.list[str],
        abstract_text: str,
        group: str | None,
        expected_revision: int,
    ) -> Paper:
        projects, papers = self._repositories()
        projects.load(project_id)
        current = papers.load(project_id, paper_id)
        updated = current.update_basic_information(
            title=title.strip(),
            authors=self._clean_list(authors),
            affiliations=self._clean_list(affiliations),
            venue=self._clean_optional(venue),
            publication_date=publication_date,
            reading_date=reading_date,
            citation_count=citation_count,
            language=self._clean_optional(language),
            keywords=self._clean_list(keywords),
            abstract_text=abstract_text.strip(),
            group=self._clean_optional(group),
        )
        return papers.save(updated, expected_revision=expected_revision)

    def get_analysis(self, project_id: UUID, paper_id: UUID) -> PaperAnalysisDocument:
        projects, papers = self._repositories()
        projects.load(project_id)
        paper = papers.load(project_id, paper_id)
        return self._analysis_document(paper)

    def create_analysis_item(
        self,
        project_id: UUID,
        paper_id: UUID,
        *,
        kind: AnalysisItemKind,
        title: str,
        summary: str,
        attributes: dict[str, str],
        evidence_refs: builtins.list[EvidenceReference],
        tags: builtins.list[str],
        writing_uses: builtins.list[WritingUse],
        expected_revision: int,
    ) -> PaperAnalysisDocument:
        projects, papers = self._repositories()
        projects.load(project_id)
        current = papers.load(project_id, paper_id)
        item = AnalysisItem.create(
            kind=kind,
            title=title,
            summary=summary,
            attributes=self._clean_attributes(attributes),
            evidence_refs=self._normalize_evidence(paper_id, evidence_refs),
            tags=self._clean_list(tags),
            writing_uses=builtins.list(dict.fromkeys(writing_uses)),
        )
        updated = self._replace_analysis_items(
            current,
            [*current.structured_summary.items, item],
        )
        return self._analysis_document(papers.save(updated, expected_revision=expected_revision))

    def update_analysis_item(
        self,
        project_id: UUID,
        paper_id: UUID,
        item_id: UUID,
        *,
        kind: AnalysisItemKind,
        title: str,
        summary: str,
        attributes: dict[str, str],
        evidence_refs: builtins.list[EvidenceReference],
        tags: builtins.list[str],
        writing_uses: builtins.list[WritingUse],
        expected_revision: int,
    ) -> PaperAnalysisDocument:
        projects, papers = self._repositories()
        projects.load(project_id)
        current = papers.load(project_id, paper_id)
        existing = next(
            (item for item in current.structured_summary.items if item.item_id == item_id),
            None,
        )
        if existing is None:
            raise AnalysisItemNotFoundError()
        updated_item = existing.model_copy(
            update={
                "kind": kind,
                "title": title.strip(),
                "summary": summary.strip(),
                "attributes": self._clean_attributes(attributes),
                "evidence_refs": self._normalize_evidence(paper_id, evidence_refs),
                "tags": self._clean_list(tags),
                "writing_uses": builtins.list(dict.fromkeys(writing_uses)),
                "updated_at": datetime.now(UTC),
            }
        )
        items = [
            updated_item if item.item_id == item_id else item
            for item in current.structured_summary.items
        ]
        updated = self._replace_analysis_items(current, items)
        return self._analysis_document(papers.save(updated, expected_revision=expected_revision))

    def delete_analysis_item(
        self,
        project_id: UUID,
        paper_id: UUID,
        item_id: UUID,
        *,
        expected_revision: int,
    ) -> PaperAnalysisDocument:
        projects, papers = self._repositories()
        projects.load(project_id)
        current = papers.load(project_id, paper_id)
        items = [item for item in current.structured_summary.items if item.item_id != item_id]
        if len(items) == len(current.structured_summary.items):
            raise AnalysisItemNotFoundError()
        updated = self._replace_analysis_items(current, items)
        return self._analysis_document(papers.save(updated, expected_revision=expected_revision))

    def relink(
        self,
        project_id: UUID,
        paper_id: UUID,
        *,
        new_path: str,
        expected_revision: int,
    ) -> Paper:
        projects, papers = self._repositories()
        projects.load(project_id)
        current = papers.load(project_id, paper_id)
        path = self._path_policy().validate_pdf(new_path)
        if any(
            item.paper_id != paper_id and item.source.path == str(path)
            for item in papers.list(project_id)
        ):
            raise PaperConflictError()
        source, _ = inspect_path(
            path,
            strict_hashing=self._workspace.require_workspace().settings.strict_hashing,
        )
        return papers.save(current.relink(source), expected_revision=expected_revision)

    def delete(self, project_id: UUID, paper_id: UUID, *, confirmed: bool) -> builtins.list[str]:
        if not confirmed:
            raise PaperConflictError("移除论文记录需要明确确认。")
        projects, papers = self._repositories()
        projects.load(project_id)
        return papers.delete(project_id, paper_id)

    def _with_current_status(self, paper: Paper) -> Paper:
        source = paper.source
        if source.path is None:
            status: SourceStatus = "unlinked"
        else:
            try:
                path = self._path_policy().validate_pdf(source.path)
            except Exception:
                status = "missing"
            else:
                stat = path.stat()
                current_fingerprint = f"{stat.st_size}:{stat.st_mtime_ns}"
                status = "changed" if current_fingerprint != source.fingerprint else source.status
        return paper.model_copy(update={"source": source.model_copy(update={"status": status})})

    @staticmethod
    def _summary(paper: Paper) -> PaperSummary:
        return PaperSummary(
            paper_id=paper.paper_id,
            project_id=paper.project_id,
            title=paper.bibliography.title,
            short_title=paper.bibliography.short_title,
            authors=paper.bibliography.authors,
            affiliations=paper.bibliography.affiliations,
            year=paper.bibliography.year,
            venue=paper.bibliography.venue,
            publication_date=paper.bibliography.publication_date,
            reading_date=paper.organization.reading_date,
            citation_count=paper.bibliography.citation_count,
            language=paper.bibliography.language,
            keywords=paper.bibliography.keywords,
            group=paper.organization.group,
            topics=paper.organization.topics,
            tags=paper.organization.tags,
            reading_status=paper.organization.reading_status,
            importance_score=paper.organization.importance_score,
            writing_uses=builtins.list(paper.organization.writing_uses),
            source_status=paper.source.status,
            source_filename=paper.source.original_filename,
            page_count=paper.source.page_count,
            one_sentence_summary=paper.organization.one_sentence_summary,
            updated_at=paper.updated_at,
            revision=paper.revision,
        )

    @staticmethod
    def _analysis_document(paper: Paper) -> PaperAnalysisDocument:
        return PaperAnalysisDocument(
            paper_id=paper.paper_id,
            revision=paper.revision,
            updated_at=paper.updated_at,
            items=paper.structured_summary.items,
        )

    @staticmethod
    def _replace_analysis_items(
        paper: Paper,
        items: builtins.list[AnalysisItem],
    ) -> Paper:
        return paper.model_copy(
            update={
                "structured_summary": paper.structured_summary.model_copy(update={"items": items}),
                "updated_at": datetime.now(UTC),
                "revision": paper.revision + 1,
            }
        )

    @staticmethod
    def _normalize_evidence(
        paper_id: UUID,
        evidence_refs: builtins.list[EvidenceReference],
    ) -> builtins.list[EvidenceReference]:
        return [item.model_copy(update={"paper_id": paper_id}) for item in evidence_refs]

    @staticmethod
    def _clean_attributes(values: dict[str, str]) -> dict[str, str]:
        return {
            key.strip(): value.strip()
            for key, value in values.items()
            if key.strip() and value.strip()
        }

    @staticmethod
    def _clean_list(values: builtins.list[str]) -> builtins.list[str]:
        return builtins.list(dict.fromkeys(value.strip() for value in values if value.strip()))

    @staticmethod
    def _clean_optional(value: str | None) -> str | None:
        cleaned = value.strip() if value else ""
        return cleaned or None
