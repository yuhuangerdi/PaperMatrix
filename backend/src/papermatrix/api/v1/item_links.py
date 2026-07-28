"""Project-level structured-item link API."""

from __future__ import annotations

from typing import cast
from uuid import UUID

from fastapi import APIRouter, Request, status
from pydantic import BaseModel, Field

from papermatrix.domain.item_links import (
    ItemLinkImpact,
    ItemLinksViewDocument,
    ItemLinkType,
    ItemReference,
    ProjectAnalysisItem,
    ProjectAnalysisItemCatalog,
)
from papermatrix.services.item_link_service import ItemLinkService

router = APIRouter(tags=["item-links"])


def _service(request: Request) -> ItemLinkService:
    return cast(ItemLinkService, request.app.state.item_link_service)


class ItemLinkCreate(BaseModel):
    source: ItemReference
    target: ItemReference
    type: ItemLinkType
    description: str = Field(default="", max_length=5000)
    expected_revision: int = Field(ge=0)


class ItemLinkUpdate(BaseModel):
    type: ItemLinkType
    description: str = Field(default="", max_length=5000)
    expected_revision: int = Field(ge=1)


class ItemLinkDelete(BaseModel):
    expected_revision: int = Field(ge=1)


class ItemLinkImpactRequest(BaseModel):
    references: list[ItemReference] = Field(min_length=1)


@router.get(
    "/projects/{project_id}/analysis/items",
    response_model=ProjectAnalysisItemCatalog,
)
def list_project_analysis_items(
    project_id: UUID,
    request: Request,
) -> ProjectAnalysisItemCatalog:
    return _service(request).list_items(project_id)


@router.get(
    "/projects/{project_id}/papers/{paper_id}/analysis/items/{item_id}/location",
    response_model=ProjectAnalysisItem,
)
def resolve_analysis_item(
    project_id: UUID,
    paper_id: UUID,
    item_id: UUID,
    request: Request,
) -> ProjectAnalysisItem:
    return _service(request).get_item(project_id, paper_id, item_id)


@router.get(
    "/projects/{project_id}/item-links",
    response_model=ItemLinksViewDocument,
)
def list_item_links(project_id: UUID, request: Request) -> ItemLinksViewDocument:
    return _service(request).list_links(project_id)


@router.post(
    "/projects/{project_id}/item-links",
    response_model=ItemLinksViewDocument,
    status_code=status.HTTP_201_CREATED,
)
def create_item_link(
    project_id: UUID,
    payload: ItemLinkCreate,
    request: Request,
) -> ItemLinksViewDocument:
    return _service(request).create(
        project_id,
        source=payload.source,
        target=payload.target,
        type=payload.type,
        description=payload.description,
        expected_revision=payload.expected_revision,
    )


@router.patch(
    "/projects/{project_id}/item-links/{link_id}",
    response_model=ItemLinksViewDocument,
)
def update_item_link(
    project_id: UUID,
    link_id: UUID,
    payload: ItemLinkUpdate,
    request: Request,
) -> ItemLinksViewDocument:
    return _service(request).update(project_id, link_id, **payload.model_dump())


@router.delete(
    "/projects/{project_id}/item-links/{link_id}",
    response_model=ItemLinksViewDocument,
)
def delete_item_link(
    project_id: UUID,
    link_id: UUID,
    payload: ItemLinkDelete,
    request: Request,
) -> ItemLinksViewDocument:
    return _service(request).delete(project_id, link_id, **payload.model_dump())


@router.post(
    "/projects/{project_id}/item-links/impacts",
    response_model=ItemLinkImpact,
)
def inspect_item_link_impacts(
    project_id: UUID,
    payload: ItemLinkImpactRequest,
    request: Request,
) -> ItemLinkImpact:
    return _service(request).impacts(project_id, payload.references)
