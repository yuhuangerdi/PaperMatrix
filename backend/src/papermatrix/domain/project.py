"""Project domain models."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Project(BaseModel):
    schema_version: Literal[1] = 1
    project_id: UUID
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,79}$")
    topic: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=5000)
    tags: list[str] = Field(default_factory=list)
    status: Literal["active", "archived"] = "active"
    created_at: datetime
    updated_at: datetime
    revision: int = Field(ge=1)

    @classmethod
    def create(
        cls,
        *,
        name: str,
        slug: str,
        topic: str = "",
        description: str = "",
        tags: list[str] | None = None,
    ) -> Project:
        now = datetime.now(UTC)
        return cls(
            project_id=uuid4(),
            name=name,
            slug=slug,
            topic=topic,
            description=description,
            tags=tags or [],
            created_at=now,
            updated_at=now,
            revision=1,
        )

    def update(
        self,
        *,
        name: str,
        slug: str,
        topic: str,
        description: str,
        tags: list[str],
        status: Literal["active", "archived"],
    ) -> Project:
        return self.model_copy(
            update={
                "name": name,
                "slug": slug,
                "topic": topic,
                "description": description,
                "tags": tags,
                "status": status,
                "updated_at": datetime.now(UTC),
                "revision": self.revision + 1,
            }
        )


class ProjectSummary(Project):
    paper_count: int = 0
    deep_read_count: int = 0
    reported_count: int = 0
