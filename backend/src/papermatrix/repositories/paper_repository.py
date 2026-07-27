"""File-backed paper record repository."""

from __future__ import annotations

import builtins
from pathlib import Path
from uuid import UUID

from filelock import FileLock, Timeout
from pydantic import ValidationError

from papermatrix.core.atomic_io import atomic_write_yaml, read_yaml
from papermatrix.core.errors import (
    FileLockTimeoutError,
    PaperMatrixError,
    PaperNotFoundError,
)
from papermatrix.core.schema_registry import SchemaRegistry
from papermatrix.domain.paper import InvalidPaperRecord, Paper
from papermatrix.domain.paper_migrations import migrate_paper


class _RecordIdentityError(ValueError):
    pass


class PaperRepository:
    def __init__(self, workspace_root: Path, schemas: SchemaRegistry) -> None:
        self._projects_root = workspace_root / "projects"
        self._schemas = schemas

    def _paper_file(self, project_id: UUID, paper_id: UUID) -> Path:
        return self._projects_root / str(project_id) / "papers" / f"{paper_id}.yaml"

    def _note_file(self, project_id: UUID, paper_id: UUID) -> Path:
        return self._projects_root / str(project_id) / "notes" / f"{paper_id}.md"

    def _questions_file(self, project_id: UUID, paper_id: UUID) -> Path:
        return self._projects_root / str(project_id) / "questions" / f"{paper_id}.yaml"

    def _supplement_file(self, project_id: UUID, paper_id: UUID) -> Path:
        return self._projects_root / str(project_id) / "notes" / f"{paper_id}.supplement.md"

    def create(self, paper: Paper) -> Paper:
        atomic_write_yaml(
            self._paper_file(paper.project_id, paper.paper_id),
            paper.model_dump(mode="json"),
            validator=lambda value: self._schemas.validate("paper", value),
        )
        return paper

    def load(self, project_id: UUID, paper_id: UUID) -> Paper:
        path = self._paper_file(project_id, paper_id)
        if not path.is_file():
            raise PaperNotFoundError()
        data = migrate_paper(read_yaml(path))
        self._schemas.validate("paper", data)
        return Paper.model_validate(data)

    def list(self, project_id: UUID) -> builtins.list[Paper]:
        papers, _ = self.list_with_invalid(project_id)
        return papers

    def list_with_invalid(
        self, project_id: UUID
    ) -> tuple[builtins.list[Paper], builtins.list[InvalidPaperRecord]]:
        papers_dir = self._projects_root / str(project_id) / "papers"
        if not papers_dir.is_dir():
            return [], []
        papers: builtins.list[Paper] = []
        invalid_records: builtins.list[InvalidPaperRecord] = []
        for path in sorted(papers_dir.glob("*.yaml")):
            try:
                record_id = UUID(path.stem)
            except ValueError:
                continue
            raw: dict[str, object] | None = None
            try:
                raw = read_yaml(path)
                data = migrate_paper(raw)
                self._schemas.validate("paper", data)
                paper = Paper.model_validate(data)
                if paper.paper_id != record_id or paper.project_id != project_id:
                    raise _RecordIdentityError("record identity does not match its project path")
            except (
                PaperMatrixError,
                ValidationError,
                AttributeError,
                KeyError,
                TypeError,
                UnicodeError,
                ValueError,
            ) as exc:
                invalid_records.append(self._invalid_record(record_id, raw=raw, error=exc))
            else:
                papers.append(paper)
        return papers, invalid_records

    def save(self, paper: Paper, *, expected_revision: int) -> Paper:
        atomic_write_yaml(
            self._paper_file(paper.project_id, paper.paper_id),
            paper.model_dump(mode="json"),
            validator=lambda value: self._schemas.validate("paper", migrate_paper(value)),
            expected_revision=expected_revision,
        )
        return paper

    def delete(self, project_id: UUID, paper_id: UUID) -> builtins.list[str]:
        paper_path = self._paper_file(project_id, paper_id)
        if not paper_path.is_file():
            raise PaperNotFoundError()
        lock = FileLock(str(paper_path.with_suffix(".yaml.lock")), timeout=5)
        removed = []
        try:
            with lock:
                paper_path.unlink()
                removed.append(paper_path.name)
                note_path = self._note_file(project_id, paper_id)
                if note_path.is_file():
                    note_path.unlink()
                    removed.append(note_path.name)
                note_path.with_suffix(".md.lock").unlink(missing_ok=True)
                supplement_path = self._supplement_file(project_id, paper_id)
                if supplement_path.is_file():
                    supplement_path.unlink()
                    removed.append(supplement_path.name)
                supplement_path.with_suffix(".md.lock").unlink(missing_ok=True)
                questions_path = self._questions_file(project_id, paper_id)
                if questions_path.is_file():
                    questions_path.unlink()
                    removed.append(questions_path.name)
                questions_path.with_suffix(".yaml.lock").unlink(missing_ok=True)
        except Timeout as exc:
            raise FileLockTimeoutError() from exc
        paper_path.with_suffix(".yaml.lock").unlink(missing_ok=True)
        return removed

    def _validated_data(self, path: Path) -> dict[str, object]:
        data = migrate_paper(read_yaml(path))
        self._schemas.validate("paper", data)
        return data

    @staticmethod
    def _invalid_record(
        paper_id: UUID,
        *,
        raw: dict[str, object] | None,
        error: Exception,
    ) -> InvalidPaperRecord:
        schema_version = raw.get("schema_version") if raw else None
        normalized_version = schema_version if isinstance(schema_version, int) else None
        bibliography = raw.get("bibliography") if raw else None
        title = (
            bibliography.get("title")
            if isinstance(bibliography, dict) and isinstance(bibliography.get("title"), str)
            else None
        )
        if normalized_version is not None and normalized_version not in {1, 2, 3, 4, 5, 6}:
            reason = f"Schema 版本 {normalized_version} 暂不支持"
        elif raw is None:
            reason = "记录文件无法读取"
        elif isinstance(error, _RecordIdentityError):
            reason = "记录身份与项目目录不一致"
        else:
            reason = "记录内容不符合当前 Paper Schema"
        return InvalidPaperRecord(
            paper_id=paper_id,
            title=title.strip() if title and title.strip() else "无法读取标题",
            schema_version=normalized_version,
            reason=reason,
        )
