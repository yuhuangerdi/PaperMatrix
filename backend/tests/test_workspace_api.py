from pathlib import Path

from fastapi.testclient import TestClient

from papermatrix.core.config import Settings
from papermatrix.main import create_app


def create_client(tmp_path: Path) -> TestClient:
    repository_root = Path(__file__).resolve().parents[2]
    app = create_app(
        Settings(workspace_root=tmp_path / "default-workspace"),
        schema_root=repository_root / "contracts" / "schemas",
        local_config_path=tmp_path / "papermatrix.local.yaml",
    )
    return TestClient(app)


def test_initialize_get_and_update_workspace(tmp_path):
    client = create_client(tmp_path)
    workspace_root = tmp_path / "research"
    paper_root = tmp_path / "papers"
    paper_root.mkdir()

    created = client.post(
        "/api/v1/workspace/initialize",
        json={
            "root_path": str(workspace_root),
            "name": "我的工作区",
            "allowed_paper_roots": [str(paper_root)],
        },
    )

    assert created.status_code == 201
    assert created.json()["revision"] == 1
    assert (workspace_root / "workspace.yaml").is_file()
    assert (workspace_root / "projects").is_dir()
    assert (workspace_root / ".papermatrix" / "locks").is_dir()
    assert client.get("/api/v1/health").json()["workspace_initialized"] is True
    assert client.get("/api/v1/workspace").json()["name"] == "我的工作区"

    updated = client.patch(
        "/api/v1/workspace",
        json={
            "name": "更新后的工作区",
            "allowed_paper_roots": [str(paper_root)],
            "expected_revision": 1,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["revision"] == 2
    assert updated.json()["name"] == "更新后的工作区"


def test_initialize_rejects_nonempty_unmanaged_directory(tmp_path):
    client = create_client(tmp_path)
    workspace_root = tmp_path / "occupied"
    workspace_root.mkdir()
    sentinel = workspace_root / "keep.txt"
    sentinel.write_text("untouched", encoding="utf-8")

    response = client.post(
        "/api/v1/workspace/initialize",
        json={"root_path": str(workspace_root), "name": "No", "allowed_paper_roots": []},
    )

    assert response.status_code == 409
    assert sentinel.read_text(encoding="utf-8") == "untouched"
    assert not (workspace_root / "workspace.yaml").exists()


def test_corrupted_workspace_is_never_overwritten(tmp_path):
    client = create_client(tmp_path)
    workspace_root = tmp_path / "broken"
    workspace_root.mkdir()
    workspace_file = workspace_root / "workspace.yaml"
    original = "schema_version: [broken\n"
    workspace_file.write_text(original, encoding="utf-8")

    response = client.post(
        "/api/v1/workspace/initialize",
        json={"root_path": str(workspace_root), "name": "No", "allowed_paper_roots": []},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "PM-CONFIG-002"
    assert workspace_file.read_text(encoding="utf-8") == original


def test_validate_workspace_path_reports_normalized_destination(tmp_path):
    client = create_client(tmp_path)
    destination = tmp_path / "new-workspace"

    response = client.post(
        "/api/v1/workspace/validate-path",
        json={"path": str(destination), "purpose": "workspace"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "valid": True,
        "normalized_path": str(destination),
        "readable": False,
        "writable": True,
        "reason": None,
    }


def test_local_config_restores_workspace_after_restart(tmp_path):
    repository_root = Path(__file__).resolve().parents[2]
    local_config = tmp_path / "papermatrix.local.yaml"
    app = create_app(
        Settings(workspace_root=tmp_path / "default"),
        schema_root=repository_root / "contracts" / "schemas",
        local_config_path=local_config,
    )
    client = TestClient(app)
    workspace_root = tmp_path / "persistent-workspace"
    assert (
        client.post(
            "/api/v1/workspace/initialize",
            json={
                "root_path": str(workspace_root),
                "name": "Persistent",
                "allowed_paper_roots": [],
            },
        ).status_code
        == 201
    )

    restarted = TestClient(
        create_app(
            schema_root=repository_root / "contracts" / "schemas",
            local_config_path=local_config,
        )
    )

    response = restarted.get("/api/v1/workspace")
    assert response.status_code == 200
    assert response.json()["root_path"] == str(workspace_root)
