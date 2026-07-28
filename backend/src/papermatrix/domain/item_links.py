"""Project-level directed links between structured note items."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

from papermatrix.domain.paper import AnalysisItem, AnalysisItemKind

ItemLinkType = Literal[
    "addresses",
    "partially_addresses",
    "depends_on",
    "enables",
    "evaluates",
    "supports",
    "contradicts",
    "extends",
    "related_to",
]


class ItemReference(BaseModel):
    paper_id: UUID
    item_id: UUID


class ItemLink(BaseModel):
    link_id: UUID = Field(default_factory=uuid4)
    source: ItemReference
    target: ItemReference
    type: ItemLinkType
    description: str = Field(default="", max_length=5000)
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def endpoints_must_differ(self) -> ItemLink:
        if self.source == self.target:
            raise ValueError("an item link cannot point to the same item")
        return self

    @classmethod
    def create(
        cls,
        *,
        source: ItemReference,
        target: ItemReference,
        type: ItemLinkType,
        description: str = "",
    ) -> ItemLink:
        now = datetime.now(UTC)
        return cls(
            source=source,
            target=target,
            type=type,
            description=description.strip(),
            created_at=now,
            updated_at=now,
        )

    def update(self, *, type: ItemLinkType, description: str) -> ItemLink:
        return self.model_copy(
            update={
                "type": type,
                "description": description.strip(),
                "updated_at": datetime.now(UTC),
            }
        )


class ItemLinksDocument(BaseModel):
    schema_version: Literal[1] = 1
    project_id: UUID
    revision: int = Field(ge=0)
    updated_at: datetime
    links: list[ItemLink] = Field(default_factory=list)

    @model_validator(mode="after")
    def link_ids_must_be_unique(self) -> ItemLinksDocument:
        link_ids = [link.link_id for link in self.links]
        if len(link_ids) != len(set(link_ids)):
            raise ValueError("item link IDs must be unique")
        return self

    @classmethod
    def empty(cls, project_id: UUID) -> ItemLinksDocument:
        return cls(project_id=project_id, revision=0, updated_at=datetime.now(UTC))


ItemReferenceStatus = Literal["available", "missing_paper", "missing_item"]


class ProjectAnalysisItem(BaseModel):
    paper_id: UUID
    paper_title: str
    item: AnalysisItem


class ProjectAnalysisItemCatalog(BaseModel):
    project_id: UUID
    items: list[ProjectAnalysisItem]


class ItemReferenceView(BaseModel):
    reference: ItemReference
    status: ItemReferenceStatus
    paper_title: str | None = None
    item_title: str | None = None
    item_kind: AnalysisItemKind | None = None


class ItemLinkView(BaseModel):
    link: ItemLink
    source: ItemReferenceView
    target: ItemReferenceView


class ItemLinksViewDocument(BaseModel):
    document: ItemLinksDocument
    links: list[ItemLinkView]
    dangling_count: int = Field(ge=0)


class ItemLinkImpact(BaseModel):
    references: list[ItemReference]
    affected_links: list[ItemLinkView]
