"""Paper source and project paper APIs."""

from __future__ import annotations

from datetime import date
from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, File, Form, Query, Request, UploadFile, status
from pydantic import BaseModel, Field

from papermatrix.domain.paper import (
    AnalysisItemKind,
    Paper,
    PaperAnalysisDocument,
    PaperList,
    SourceStatus,
    WritingUse,
)
from papermatrix.domain.paper_content import EvidenceReference
from papermatrix.services.paper_service import PaperService, ScanCandidate

router = APIRouter(tags=["papers"])


def _service(request: Request) -> PaperService:
    return cast(PaperService, request.app.state.paper_service)


class ScanRequest(BaseModel):
    directory: str
    recursive: bool = False


class ScanResponse(BaseModel):
    scan_token: str
    items: list[ScanCandidate]
    warnings: list[str]


class ImportRequest(BaseModel):
    scan_token: str
    candidate_ids: list[str] = Field(min_length=1)


class ImportResponse(BaseModel):
    imported: list[Paper]
    skipped: list[dict[str, str]]


class LinkRequest(BaseModel):
    path: str


class ManualPaperRequest(BaseModel):
    title: str = Field(min_length=1, max_length=1000)


class RelinkRequest(BaseModel):
    new_path: str
    expected_revision: int = Field(ge=1)


class PaperBasicInformationUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=1000)
    authors: list[str] = Field(default_factory=list)
    affiliations: list[str] = Field(default_factory=list)
    venue: str | None = Field(default=None, max_length=300)
    publication_date: date | None = None
    reading_date: date | None = None
    citation_count: int | None = Field(default=None, ge=0)
    language: str | None = Field(default=None, max_length=50)
    keywords: list[str] = Field(default_factory=list)
    abstract_text: str = Field(default="", max_length=20000)
    group: str | None = Field(default=None, max_length=120)
    expected_revision: int = Field(ge=1)


class DeleteResponse(BaseModel):
    source_pdf_untouched: bool = True
    removed_files: list[str]


class AnalysisItemInput(BaseModel):
    kind: AnalysisItemKind
    title: str = Field(min_length=1, max_length=300)
    summary: str = Field(default="", max_length=20000)
    attributes: dict[str, str] = Field(default_factory=dict)
    evidence_refs: list[EvidenceReference] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    writing_uses: list[WritingUse] = Field(default_factory=list)
    expected_revision: int = Field(ge=1)


@router.post("/paper-sources/scan", response_model=ScanResponse)
def scan_paper_sources(payload: ScanRequest, request: Request) -> ScanResponse:
    token, items, warnings = request.app.state.paper_service.scan(**payload.model_dump())
    return ScanResponse(scan_token=token, items=items, warnings=warnings)


@router.get("/projects/{project_id}/papers", response_model=PaperList)
def list_papers(
    project_id: UUID,
    request: Request,
    q: str = "",
    source_status: SourceStatus | None = None,
    group: str | None = None,
    sort: str = "-updated_at",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> PaperList:
    return _service(request).list(
        project_id,
        query=q,
        source_status=source_status,
        group=group,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/projects/{project_id}/papers/import",
    response_model=ImportResponse,
    status_code=status.HTTP_201_CREATED,
)
def import_papers(project_id: UUID, payload: ImportRequest, request: Request) -> ImportResponse:
    imported, skipped = _service(request).import_candidates(project_id, **payload.model_dump())
    return ImportResponse(imported=imported, skipped=skipped)


@router.post(
    "/projects/{project_id}/papers/link",
    response_model=Paper,
    status_code=status.HTTP_201_CREATED,
)
def link_paper(project_id: UUID, payload: LinkRequest, request: Request) -> Paper:
    return _service(request).link_path(project_id, payload.path)


@router.post(
    "/projects/{project_id}/papers/manual",
    response_model=Paper,
    status_code=status.HTTP_201_CREATED,
)
def create_manual_paper(project_id: UUID, payload: ManualPaperRequest, request: Request) -> Paper:
    return _service(request).create_manual(project_id, title=payload.title)


@router.post(
    "/projects/{project_id}/papers/upload",
    response_model=Paper,
    status_code=status.HTTP_201_CREATED,
)
async def upload_paper(
    project_id: UUID,
    request: Request,
    file: Annotated[UploadFile, File(...)],
    title: Annotated[str | None, Form()] = None,
) -> Paper:
    content = await file.read(request.app.state.settings.max_upload_bytes + 1)
    return _service(request).upload(
        project_id,
        filename=file.filename or "paper.pdf",
        content=content,
        title=title,
    )


@router.get("/projects/{project_id}/papers/{paper_id}", response_model=Paper)
def get_paper(project_id: UUID, paper_id: UUID, request: Request) -> Paper:
    return _service(request).get(project_id, paper_id)


@router.patch("/projects/{project_id}/papers/{paper_id}", response_model=Paper)
def update_paper_basic_information(
    project_id: UUID,
    paper_id: UUID,
    payload: PaperBasicInformationUpdate,
    request: Request,
) -> Paper:
    return _service(request).update_basic_information(project_id, paper_id, **payload.model_dump())


@router.get(
    "/projects/{project_id}/papers/{paper_id}/analysis",
    response_model=PaperAnalysisDocument,
)
def get_paper_analysis(
    project_id: UUID,
    paper_id: UUID,
    request: Request,
) -> PaperAnalysisDocument:
    return _service(request).get_analysis(project_id, paper_id)


@router.post(
    "/projects/{project_id}/papers/{paper_id}/analysis/items",
    response_model=PaperAnalysisDocument,
    status_code=status.HTTP_201_CREATED,
)
def create_paper_analysis_item(
    project_id: UUID,
    paper_id: UUID,
    payload: AnalysisItemInput,
    request: Request,
) -> PaperAnalysisDocument:
    return _service(request).create_analysis_item(
        project_id,
        paper_id,
        kind=payload.kind,
        title=payload.title,
        summary=payload.summary,
        attributes=payload.attributes,
        evidence_refs=payload.evidence_refs,
        tags=payload.tags,
        writing_uses=payload.writing_uses,
        expected_revision=payload.expected_revision,
    )


@router.patch(
    "/projects/{project_id}/papers/{paper_id}/analysis/items/{item_id}",
    response_model=PaperAnalysisDocument,
)
def update_paper_analysis_item(
    project_id: UUID,
    paper_id: UUID,
    item_id: UUID,
    payload: AnalysisItemInput,
    request: Request,
) -> PaperAnalysisDocument:
    return _service(request).update_analysis_item(
        project_id,
        paper_id,
        item_id,
        kind=payload.kind,
        title=payload.title,
        summary=payload.summary,
        attributes=payload.attributes,
        evidence_refs=payload.evidence_refs,
        tags=payload.tags,
        writing_uses=payload.writing_uses,
        expected_revision=payload.expected_revision,
    )


@router.delete(
    "/projects/{project_id}/papers/{paper_id}/analysis/items/{item_id}",
    response_model=PaperAnalysisDocument,
)
def delete_paper_analysis_item(
    project_id: UUID,
    paper_id: UUID,
    item_id: UUID,
    request: Request,
    expected_revision: int = Query(ge=1),
) -> PaperAnalysisDocument:
    return _service(request).delete_analysis_item(
        project_id,
        paper_id,
        item_id,
        expected_revision=expected_revision,
    )


@router.post("/projects/{project_id}/papers/{paper_id}/relink", response_model=Paper)
def relink_paper(
    project_id: UUID,
    paper_id: UUID,
    payload: RelinkRequest,
    request: Request,
) -> Paper:
    return _service(request).relink(project_id, paper_id, **payload.model_dump())


@router.delete(
    "/projects/{project_id}/papers/{paper_id}",
    response_model=DeleteResponse,
)
def delete_paper(
    project_id: UUID,
    paper_id: UUID,
    request: Request,
    confirm_metadata_only: bool = Query(...),
) -> DeleteResponse:
    removed = _service(request).delete(project_id, paper_id, confirmed=confirm_metadata_only)
    return DeleteResponse(removed_files=removed)
