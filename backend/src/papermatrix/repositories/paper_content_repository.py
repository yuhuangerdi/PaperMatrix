"""File-backed note and question repositories."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import yaml
from pydantic import BaseModel, ValidationError

from papermatrix.core.atomic_io import (
    atomic_write_markdown,
    atomic_write_yaml,
    read_markdown,
    read_yaml,
)
from papermatrix.core.errors import FileContentError
from papermatrix.core.schema_registry import SchemaRegistry
from papermatrix.domain.paper_content import PaperNote, QuestionsDocument
from papermatrix.domain.question_migrations import migrate_questions


class _NoteFrontMatter(BaseModel):
    schema_version: int
    paper_id: UUID
    revision: int
    updated_at: datetime
    template_version: int


class PaperContentRepository:
    def __init__(self, workspace_root: Path, schemas: SchemaRegistry) -> None:
        self._projects_root = workspace_root / "projects"
        self._schemas = schemas

    def _note_file(self, project_id: UUID, paper_id: UUID) -> Path:
        return self._projects_root / str(project_id) / "notes" / f"{paper_id}.md"

    def _supplement_file(self, project_id: UUID, paper_id: UUID) -> Path:
        return self._projects_root / str(project_id) / "notes" / f"{paper_id}.supplement.md"

    def _questions_file(self, project_id: UUID, paper_id: UUID) -> Path:
        return self._projects_root / str(project_id) / "questions" / f"{paper_id}.yaml"

    def load_note(self, project_id: UUID, paper_id: UUID) -> PaperNote | None:
        return self._load_markdown_note(self._note_file(project_id, paper_id), paper_id)

    def save_note(
        self,
        project_id: UUID,
        note: PaperNote,
        *,
        expected_revision: int,
    ) -> PaperNote:
        self._save_markdown_note(
            self._note_file(project_id, note.paper_id),
            note,
            expected_revision=expected_revision,
        )
        return note

    def load_supplement(self, project_id: UUID, paper_id: UUID) -> PaperNote | None:
        return self._load_markdown_note(self._supplement_file(project_id, paper_id), paper_id)

    def save_supplement(
        self,
        project_id: UUID,
        note: PaperNote,
        *,
        expected_revision: int,
    ) -> PaperNote:
        self._save_markdown_note(
            self._supplement_file(project_id, note.paper_id),
            note,
            expected_revision=expected_revision,
        )
        return note

    def load_questions(self, project_id: UUID, paper_id: UUID) -> QuestionsDocument:
        path = self._questions_file(project_id, paper_id)
        if not path.is_file():
            return QuestionsDocument.empty(paper_id)
        data = migrate_questions(read_yaml(path))
        self._schemas.validate("questions", data)
        document = QuestionsDocument.model_validate(data)
        if document.paper_id != paper_id:
            raise FileContentError(
                "问题清单中的 paper_id 与文件名不一致。",
                details={"file": path.name},
            )
        return document

    def save_questions(
        self,
        project_id: UUID,
        document: QuestionsDocument,
        *,
        expected_revision: int,
    ) -> QuestionsDocument:
        atomic_write_yaml(
            self._questions_file(project_id, document.paper_id),
            document.model_dump(mode="json"),
            validator=lambda value: self._schemas.validate("questions", migrate_questions(value)),
            expected_revision=expected_revision,
        )
        return document

    def _load_markdown_note(self, path: Path, paper_id: UUID) -> PaperNote | None:
        if not path.is_file():
            return None
        front_matter, body = self._parse_note(read_markdown(path))
        if front_matter.paper_id != paper_id:
            raise FileContentError(
                "笔记中的 paper_id 与文件名不一致。",
                details={"file": path.name},
            )
        return PaperNote(
            paper_id=paper_id,
            markdown=body,
            revision=front_matter.revision,
            updated_at=front_matter.updated_at,
        )

    def _save_markdown_note(
        self,
        path: Path,
        note: PaperNote,
        *,
        expected_revision: int,
    ) -> None:
        atomic_write_markdown(
            path,
            self._serialize_note(note),
            expected_revision=expected_revision,
            revision_reader=lambda value: self._parse_note(value)[0].revision,
        )

    @staticmethod
    def _parse_note(content: str) -> tuple[_NoteFrontMatter, str]:
        lines = content.splitlines()
        if not lines or lines[0].strip() != "---":
            raise FileContentError("笔记缺少 YAML front matter。")
        try:
            closing = lines.index("---", 1)
        except ValueError as exc:
            raise FileContentError("笔记的 YAML front matter 未闭合。") from exc
        try:
            raw: Any = yaml.safe_load("\n".join(lines[1:closing]))
            front_matter = _NoteFrontMatter.model_validate(raw)
        except (yaml.YAMLError, ValidationError) as exc:
            raise FileContentError(
                "笔记的 YAML front matter 无法解析。",
                details={"reason": str(exc)},
            ) from exc
        body = "\n".join(lines[closing + 1 :]).lstrip("\n")
        return front_matter, body

    @staticmethod
    def _serialize_note(note: PaperNote) -> str:
        front_matter = {
            "schema_version": 1,
            "paper_id": str(note.paper_id),
            "revision": note.revision,
            "updated_at": note.updated_at.isoformat().replace("+00:00", "Z"),
            "template_version": 2,
        }
        yaml_text = yaml.safe_dump(front_matter, allow_unicode=True, sort_keys=False).strip()
        return f"---\n{yaml_text}\n---\n\n{note.markdown.rstrip()}\n"
