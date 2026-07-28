from pathlib import Path

from fastapi.testclient import TestClient

from papermatrix.core.config import Settings
from papermatrix.main import create_app


def initialized_client(tmp_path: Path) -> TestClient:
    repository_root = Path(__file__).resolve().parents[2]
    app = create_app(
        Settings(workspace_root=tmp_path / "default-workspace"),
        schema_root=repository_root / "contracts" / "schemas",
        local_config_path=tmp_path / "papermatrix.local.yaml",
    )
    client = TestClient(app)
    response = client.post(
        "/api/v1/workspace/initialize",
        json={
            "root_path": str(tmp_path / "workspace"),
            "name": "研究",
            "allowed_paper_roots": [],
        },
    )
    assert response.status_code == 201
    return client


def create_project(client: TestClient, name: str = "Relations") -> str:
    response = client.post(
        "/api/v1/projects",
        json={"name": name, "topic": "", "description": "", "tags": []},
    )
    assert response.status_code == 201
    return response.json()["project_id"]


def create_paper_item(
    client: TestClient,
    project_id: str,
    *,
    paper_title: str,
    item_title: str,
    kind: str,
) -> tuple[str, str, int]:
    paper = client.post(
        f"/api/v1/projects/{project_id}/papers/manual",
        json={"title": paper_title},
    ).json()
    response = client.post(
        f"/api/v1/projects/{project_id}/papers/{paper['paper_id']}/analysis/items",
        json={
            "kind": kind,
            "display_label": None,
            "title": item_title,
            "summary": "",
            "attributes": {},
            "tags": [],
            "writing_uses": [],
            "expected_revision": paper["revision"],
        },
    )
    assert response.status_code == 201
    analysis = response.json()
    return paper["paper_id"], analysis["items"][0]["item_id"], analysis["revision"]


def test_item_link_crud_reverse_lookup_and_stable_location(tmp_path):
    client = initialized_client(tmp_path)
    project_id = create_project(client)
    source_paper, source_item, _ = create_paper_item(
        client,
        project_id,
        paper_title="Method Paper",
        item_title="Planning method",
        kind="method",
    )
    target_paper, target_item, _ = create_paper_item(
        client,
        project_id,
        paper_title="Problem Paper",
        item_title="Long-horizon failure",
        kind="research_problem",
    )

    catalog = client.get(f"/api/v1/projects/{project_id}/analysis/items")
    assert catalog.status_code == 200
    assert len(catalog.json()["items"]) == 2

    created = client.post(
        f"/api/v1/projects/{project_id}/item-links",
        json={
            "source": {"paper_id": source_paper, "item_id": source_item},
            "target": {"paper_id": target_paper, "item_id": target_item},
            "type": "addresses",
            "description": "方法解决该问题。",
            "expected_revision": 0,
        },
    )
    assert created.status_code == 201
    view = created.json()
    assert view["document"]["revision"] == 1
    assert view["links"][0]["source"]["item_title"] == "Planning method"
    assert view["links"][0]["target"]["item_title"] == "Long-horizon failure"
    assert view["dangling_count"] == 0
    link_id = view["document"]["links"][0]["link_id"]

    impacts = client.post(
        f"/api/v1/projects/{project_id}/item-links/impacts",
        json={"references": [{"paper_id": target_paper, "item_id": target_item}]},
    )
    assert impacts.status_code == 200
    assert impacts.json()["affected_links"][0]["link"]["link_id"] == link_id

    location = client.get(
        f"/api/v1/projects/{project_id}/papers/{target_paper}/analysis/items/{target_item}/location"
    )
    assert location.status_code == 200
    assert location.json()["item"]["section_key"] is None
    assert "path" not in location.json()

    updated = client.patch(
        f"/api/v1/projects/{project_id}/item-links/{link_id}",
        json={
            "type": "partially_addresses",
            "description": "只处理部分场景。",
            "expected_revision": 1,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["document"]["revision"] == 2
    assert updated.json()["document"]["links"][0]["type"] == "partially_addresses"

    deleted = client.request(
        "DELETE",
        f"/api/v1/projects/{project_id}/item-links/{link_id}",
        json={"expected_revision": 2},
    )
    assert deleted.status_code == 200
    assert deleted.json()["document"]["revision"] == 3
    assert deleted.json()["links"] == []


def test_deleted_item_keeps_link_as_dangling_reference(tmp_path):
    client = initialized_client(tmp_path)
    project_id = create_project(client)
    source_paper, source_item, source_revision = create_paper_item(
        client,
        project_id,
        paper_title="Method",
        item_title="Agent",
        kind="method",
    )
    target_paper, target_item, _ = create_paper_item(
        client,
        project_id,
        paper_title="Finding",
        item_title="Improvement",
        kind="finding",
    )
    created = client.post(
        f"/api/v1/projects/{project_id}/item-links",
        json={
            "source": {"paper_id": source_paper, "item_id": source_item},
            "target": {"paper_id": target_paper, "item_id": target_item},
            "type": "supports",
            "description": "",
            "expected_revision": 0,
        },
    )
    assert created.status_code == 201

    removed = client.delete(
        f"/api/v1/projects/{project_id}/papers/{source_paper}/analysis/items/{source_item}"
        f"?expected_revision={source_revision}"
    )
    assert removed.status_code == 200

    view = client.get(f"/api/v1/projects/{project_id}/item-links")
    assert view.status_code == 200
    assert view.json()["document"]["revision"] == 1
    assert view.json()["links"][0]["source"]["status"] == "missing_item"
    assert view.json()["dangling_count"] == 1


def test_item_link_rejects_reference_from_another_project(tmp_path):
    client = initialized_client(tmp_path)
    project_id = create_project(client, "Current")
    other_project_id = create_project(client, "Other")
    source_paper, source_item, _ = create_paper_item(
        client,
        project_id,
        paper_title="Current paper",
        item_title="Current method",
        kind="method",
    )
    target_paper, target_item, _ = create_paper_item(
        client,
        other_project_id,
        paper_title="Other paper",
        item_title="Other finding",
        kind="finding",
    )

    response = client.post(
        f"/api/v1/projects/{project_id}/item-links",
        json={
            "source": {"paper_id": source_paper, "item_id": source_item},
            "target": {"paper_id": target_paper, "item_id": target_item},
            "type": "supports",
            "description": "",
            "expected_revision": 0,
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "PM-ITEM-LINK-002"
