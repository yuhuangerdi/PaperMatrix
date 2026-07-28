from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from papermatrix.core.errors import FileContentError, RevisionConflictError, SchemaValidationError
from papermatrix.core.schema_registry import SchemaRegistry
from papermatrix.domain.item_links import ItemLink, ItemLinksDocument, ItemReference
from papermatrix.repositories.item_link_repository import ItemLinkRepository


def repository(tmp_path: Path) -> ItemLinkRepository:
    schema_root = Path(__file__).resolve().parents[2] / "contracts" / "schemas"
    return ItemLinkRepository(tmp_path, SchemaRegistry(schema_root))


def schema_registry() -> SchemaRegistry:
    schema_root = Path(__file__).resolve().parents[2] / "contracts" / "schemas"
    return SchemaRegistry(schema_root)


def test_missing_item_links_document_is_an_unpersisted_empty_document(tmp_path):
    project_id = uuid4()

    document = repository(tmp_path).load(project_id)

    assert document.project_id == project_id
    assert document.revision == 0
    assert document.links == []
    assert not (tmp_path / "projects" / str(project_id) / "analyses" / "item-links.yaml").exists()


def test_item_links_round_trip_supports_same_and_cross_paper_links(tmp_path):
    project_id = uuid4()
    paper_a = uuid4()
    paper_b = uuid4()
    source = ItemReference(paper_id=paper_a, item_id=uuid4())
    same_paper_target = ItemReference(paper_id=paper_a, item_id=uuid4())
    cross_paper_target = ItemReference(paper_id=paper_b, item_id=uuid4())
    document = ItemLinksDocument(
        project_id=project_id,
        revision=1,
        updated_at=datetime.now(UTC),
        links=[
            ItemLink.create(
                source=source,
                target=same_paper_target,
                type="depends_on",
                description="同篇方法依赖该组件。",
            ),
            ItemLink.create(
                source=source,
                target=cross_paper_target,
                type="extends",
                description="跨篇扩展。",
            ),
        ],
    )
    item_links = repository(tmp_path)

    item_links.save(document, expected_revision=0)

    assert item_links.load(project_id) == document


def test_item_links_revision_conflict_preserves_current_document(tmp_path):
    project_id = uuid4()
    item_links = repository(tmp_path)
    initial = ItemLinksDocument(
        project_id=project_id,
        revision=1,
        updated_at=datetime.now(UTC),
    )
    item_links.save(initial, expected_revision=0)
    changed = initial.model_copy(update={"revision": 2, "updated_at": datetime.now(UTC)})

    with pytest.raises(RevisionConflictError):
        item_links.save(changed, expected_revision=0)

    assert item_links.load(project_id) == initial


def test_item_links_reject_invalid_type_without_overwriting_current_document(tmp_path):
    project_id = uuid4()
    item_links = repository(tmp_path)
    initial = ItemLinksDocument(
        project_id=project_id,
        revision=1,
        updated_at=datetime.now(UTC),
    )
    item_links.save(initial, expected_revision=0)
    invalid = initial.model_dump(mode="json")
    invalid["revision"] = 2
    invalid["links"] = [
        {
            "link_id": str(uuid4()),
            "source": {"paper_id": str(uuid4()), "item_id": str(uuid4())},
            "target": {"paper_id": str(uuid4()), "item_id": str(uuid4())},
            "type": "similar_to",
            "description": "",
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
    ]

    with pytest.raises(SchemaValidationError):
        schema_registry().validate("item-links", invalid)

    assert item_links.load(project_id) == initial


def test_item_links_project_identity_mismatch_is_rejected(tmp_path):
    requested_project_id = uuid4()
    stored_project_id = uuid4()
    path = tmp_path / "projects" / str(requested_project_id) / "analyses" / "item-links.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(
        "\n".join(
            [
                "schema_version: 1",
                f"project_id: {stored_project_id}",
                "revision: 1",
                f'updated_at: "{datetime.now(UTC).isoformat()}"',
                "links: []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(FileContentError):
        repository(tmp_path).load(requested_project_id)


def test_item_links_reject_self_links_and_duplicate_ids():
    reference = ItemReference(paper_id=uuid4(), item_id=uuid4())
    with pytest.raises(ValidationError):
        ItemLink.create(source=reference, target=reference, type="related_to")

    link = ItemLink.create(
        source=reference,
        target=ItemReference(paper_id=uuid4(), item_id=uuid4()),
        type="supports",
    )
    with pytest.raises(ValidationError):
        ItemLinksDocument(
            project_id=uuid4(),
            revision=1,
            updated_at=datetime.now(UTC),
            links=[link, link],
        )
