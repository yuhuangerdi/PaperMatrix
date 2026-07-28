from pathlib import Path

from fastapi.testclient import TestClient

from papermatrix.core.config import Settings
from papermatrix.main import create_app


def initialized_client(tmp_path: Path) -> tuple[TestClient, Path]:
    repository_root = Path(__file__).resolve().parents[2]
    app = create_app(
        Settings(workspace_root=tmp_path / "default-workspace"),
        schema_root=repository_root / "contracts" / "schemas",
        local_config_path=tmp_path / "papermatrix.local.yaml",
    )
    client = TestClient(app)
    workspace = tmp_path / "workspace"
    assert (
        client.post(
            "/api/v1/workspace/initialize",
            json={"root_path": str(workspace), "name": "研究", "allowed_paper_roots": []},
        ).status_code
        == 201
    )
    return client, workspace


def create_project(client: TestClient) -> str:
    return client.post(
        "/api/v1/projects",
        json={"name": "Scopes", "topic": "", "description": "", "tags": []},
    ).json()["project_id"]


def create_paper(client: TestClient, project_id: str, title: str) -> str:
    return client.post(
        f"/api/v1/projects/{project_id}/papers/manual",
        json={"title": title},
    ).json()["paper_id"]


def test_analysis_scope_crud_persists_filter_snapshot(tmp_path):
    client, workspace = initialized_client(tmp_path)
    project_id = create_project(client)
    paper_a = create_paper(client, project_id, "Paper A")
    paper_b = create_paper(client, project_id, "Paper B")

    empty = client.get(f"/api/v1/projects/{project_id}/analysis-scopes")
    assert empty.status_code == 200
    assert empty.json()["document"]["revision"] == 0

    created = client.post(
        f"/api/v1/projects/{project_id}/analysis-scopes",
        json={
            "name": "核心基线",
            "purpose": "比较长链任务方法。",
            "paper_ids": [paper_a, paper_b],
            "source_filter_snapshot": {
                "q": "agent",
                "group": "核心",
                "sort": "-year",
            },
            "expected_revision": 0,
        },
    )
    assert created.status_code == 201
    view = created.json()
    assert view["document"]["revision"] == 1
    assert view["scopes"][0]["available_paper_ids"] == [paper_a, paper_b]
    assert view["scopes"][0]["missing_paper_ids"] == []
    assert view["scopes"][0]["scope"]["source_filter_snapshot"]["q"] == "agent"
    scope_id = view["scopes"][0]["scope"]["scope_id"]
    assert (workspace / "projects" / project_id / "analyses" / "scopes.yaml").is_file()

    updated = client.patch(
        f"/api/v1/projects/{project_id}/analysis-scopes/{scope_id}",
        json={
            "name": "核心方法",
            "purpose": "",
            "paper_ids": [paper_b],
            "source_filter_snapshot": {},
            "expected_revision": 1,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["document"]["revision"] == 2
    assert updated.json()["scopes"][0]["scope"]["paper_ids"] == [paper_b]

    deleted = client.request(
        "DELETE",
        f"/api/v1/projects/{project_id}/analysis-scopes/{scope_id}",
        json={"expected_revision": 2},
    )
    assert deleted.status_code == 200
    assert deleted.json()["document"]["revision"] == 3
    assert deleted.json()["scopes"] == []


def test_analysis_scope_preserves_deleted_paper_id_as_missing(tmp_path):
    client, _ = initialized_client(tmp_path)
    project_id = create_project(client)
    paper_id = create_paper(client, project_id, "Temporary")
    created = client.post(
        f"/api/v1/projects/{project_id}/analysis-scopes",
        json={
            "name": "Snapshot",
            "purpose": "",
            "paper_ids": [paper_id],
            "source_filter_snapshot": {},
            "expected_revision": 0,
        },
    )
    assert created.status_code == 201
    assert (
        client.delete(
            f"/api/v1/projects/{project_id}/papers/{paper_id}?confirm_metadata_only=true"
        ).status_code
        == 200
    )

    view = client.get(f"/api/v1/projects/{project_id}/analysis-scopes").json()

    assert view["document"]["scopes"][0]["paper_ids"] == [paper_id]
    assert view["scopes"][0]["available_paper_ids"] == []
    assert view["scopes"][0]["missing_paper_ids"] == [paper_id]


def test_analysis_scope_rejects_paper_from_another_project(tmp_path):
    client, _ = initialized_client(tmp_path)
    project_id = create_project(client)
    other = client.post(
        "/api/v1/projects",
        json={"name": "Other", "topic": "", "description": "", "tags": []},
    ).json()["project_id"]
    other_paper = create_paper(client, other, "Other")

    response = client.post(
        f"/api/v1/projects/{project_id}/analysis-scopes",
        json={
            "name": "Invalid",
            "purpose": "",
            "paper_ids": [other_paper],
            "source_filter_snapshot": {},
            "expected_revision": 0,
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "PM-SCOPE-002"
