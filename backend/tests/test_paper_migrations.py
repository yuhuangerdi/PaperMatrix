from pathlib import Path
from uuid import UUID

import yaml

from papermatrix.core.schema_registry import SchemaRegistry
from papermatrix.domain.paper_migrations import migrate_paper
from papermatrix.repositories.paper_repository import PaperRepository


def test_migrates_v1_source_and_optional_bibliography_fields() -> None:
    migrated = migrate_paper(
        {
            "schema_version": 1,
            "source": {
                "path": "/papers/example.pdf",
                "path_mode": "absolute",
                "size_bytes": 12,
                "modified_at": "2026-07-27T00:00:00Z",
                "fingerprint": "12:1",
                "page_count": None,
                "status": "available",
            },
            "bibliography": {"title": "Example"},
        }
    )

    assert migrated["schema_version"] == 5
    assert migrated["source"]["original_filename"] == "example.pdf"
    assert migrated["source"]["sha256"] is None
    assert migrated["bibliography"]["doi"] is None
    assert migrated["bibliography"]["affiliations"] == []
    assert migrated["organization"]["group"] is None
    assert migrated["structured_summary"]["items"] == []


def test_repository_saves_an_edited_v2_record_as_v3(tmp_path: Path) -> None:
    project_id = UUID("5d3351ce-408c-4c36-b11f-bb8a19f72000")
    paper_id = UUID("4abf5d15-1692-44e1-8073-27cedfa92500")
    paper_path = tmp_path / "projects" / str(project_id) / "papers" / f"{paper_id}.yaml"
    paper_path.parent.mkdir(parents=True)
    paper_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 2,
                "paper_id": str(paper_id),
                "project_id": str(project_id),
                "source": {
                    "path": None,
                    "path_mode": None,
                    "original_filename": None,
                    "size_bytes": None,
                    "modified_at": None,
                    "fingerprint": None,
                    "sha256": None,
                    "page_count": None,
                    "status": "unlinked",
                },
                "bibliography": {
                    "title": "Legacy paper",
                    "short_title": "",
                    "authors": [],
                    "year": None,
                    "venue": None,
                    "publication_type": "other",
                    "doi": None,
                    "arxiv_id": None,
                    "urls": [],
                    "code_url": None,
                    "data_url": None,
                },
                "organization": {
                    "topics": [],
                    "tags": [],
                    "reading_status": "unread",
                    "priority": None,
                    "importance_score": None,
                    "confidence_score": None,
                    "reproduction_value": None,
                    "writing_uses": [],
                    "one_sentence_summary": "",
                },
                "structured_summary": {
                    "background": {},
                    "related_work": {},
                    "approach": {},
                    "challenges": [],
                    "innovations": [],
                    "additional_contribution": {},
                    "experiment": {},
                    "evaluation": {},
                },
                "created_at": "2026-07-27T00:00:00Z",
                "updated_at": "2026-07-27T00:00:00Z",
                "revision": 1,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    schemas = SchemaRegistry(Path(__file__).parents[2] / "contracts" / "schemas")
    repository = PaperRepository(tmp_path, schemas)
    migrated = repository.load(project_id, paper_id)

    saved = repository.save(
        migrated.update_basic_information(
            title="Legacy paper",
            authors=[],
            affiliations=["Example University"],
            venue="Example Journal",
            publication_date=None,
            reading_date=None,
            citation_count=3,
            language="English",
            keywords=[],
            abstract_text="",
            group="核心文献",
        ),
        expected_revision=1,
    )

    assert saved.schema_version == 5
    assert repository.load(project_id, paper_id).organization.group == "核心文献"


def test_migrates_v3_analysis_without_losing_legacy_summary() -> None:
    migrated = migrate_paper(
        {
            "schema_version": 3,
            "structured_summary": {
                "background": {"problem": "Legacy problem"},
                "related_work": {},
                "approach": {},
                "challenges": [],
                "innovations": [],
                "additional_contribution": {},
                "experiment": {},
                "evaluation": {},
            },
        }
    )

    assert migrated["schema_version"] == 5
    assert migrated["structured_summary"]["background"] == {"problem": "Legacy problem"}
    assert migrated["structured_summary"]["items"] == []


def test_migrates_v4_items_with_empty_note_source_metadata() -> None:
    migrated = migrate_paper(
        {
            "schema_version": 4,
            "structured_summary": {
                "items": [
                    {
                        "item_id": "11111111-1111-4111-8111-111111111111",
                        "kind": "method",
                        "title": "Legacy method",
                    }
                ]
            },
        }
    )

    item = migrated["structured_summary"]["items"][0]
    assert migrated["schema_version"] == 5
    assert item["title"] == "Legacy method"
    assert item["section_key"] is None
    assert item["source_note_revision"] is None
