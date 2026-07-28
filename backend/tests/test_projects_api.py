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
    workspace_root = tmp_path / "workspace"
    response = client.post(
        "/api/v1/workspace/initialize",
        json={"root_path": str(workspace_root), "name": "研究", "allowed_paper_roots": []},
    )
    assert response.status_code == 201
    return client, workspace_root


def test_project_crud_and_statistics(tmp_path):
    client, workspace_root = initialized_client(tmp_path)

    created = client.post(
        "/api/v1/projects",
        json={
            "name": "Agent Security",
            "topic": "LLM agent security",
            "description": "Track the field.",
            "tags": ["agent", "security", "agent"],
        },
    )
    assert created.status_code == 201
    project = created.json()
    project_id = project["project_id"]
    project_dir = workspace_root / "projects" / project_id
    assert (project_dir / "project.yaml").is_file()
    assert (project_dir / "papers").is_dir()
    assert (project_dir / "analyses").is_dir()
    assert project["tags"] == ["agent", "security"]

    listed = client.get("/api/v1/projects")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["paper_count"] == 0

    updated = client.patch(
        f"/api/v1/projects/{project_id}",
        json={
            "name": "Agent Safety",
            "topic": "Updated",
            "description": "",
            "tags": ["safety"],
            "status": "archived",
            "expected_revision": 1,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["revision"] == 2
    assert updated.json()["status"] == "archived"
    assert client.get("/api/v1/projects").json()["total"] == 0
    assert client.get("/api/v1/projects?include_archived=true").json()["total"] == 1

    deleted = client.delete(f"/api/v1/projects/{project_id}?confirm=true")
    assert deleted.status_code == 204
    assert not project_dir.exists()
    assert workspace_root.exists()


def test_duplicate_project_name_is_rejected(tmp_path):
    client, _ = initialized_client(tmp_path)
    payload = {"name": "Same", "topic": "", "description": "", "tags": []}

    assert client.post("/api/v1/projects", json=payload).status_code == 201
    duplicate = client.post("/api/v1/projects", json=payload)

    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "PM-PROJECT-002"


def test_nonempty_project_is_not_deleted(tmp_path):
    client, workspace_root = initialized_client(tmp_path)
    created = client.post(
        "/api/v1/projects",
        json={"name": "Keep", "topic": "", "description": "", "tags": []},
    ).json()
    project_id = created["project_id"]
    paper_record = workspace_root / "projects" / project_id / "papers" / "record.yaml"
    paper_record.write_text("paper_id: sentinel\n", encoding="utf-8")

    response = client.delete(f"/api/v1/projects/{project_id}?confirm=true")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PM-PROJECT-003"
    assert paper_record.is_file()


def test_project_revision_conflict_preserves_current_version(tmp_path):
    client, _ = initialized_client(tmp_path)
    created = client.post(
        "/api/v1/projects",
        json={"name": "Revision", "topic": "", "description": "", "tags": []},
    ).json()
    project_id = created["project_id"]
    payload = {
        "name": "Revision two",
        "topic": "",
        "description": "",
        "tags": [],
        "status": "active",
        "expected_revision": 1,
    }
    assert client.patch(f"/api/v1/projects/{project_id}", json=payload).status_code == 200

    conflict = client.patch(f"/api/v1/projects/{project_id}", json=payload)
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "PM-CONFLICT-001"
