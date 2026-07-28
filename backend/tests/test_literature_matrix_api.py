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
    assert (
        client.post(
            "/api/v1/workspace/initialize",
            json={
                "root_path": str(tmp_path / "workspace"),
                "name": "研究",
                "allowed_paper_roots": [],
            },
        ).status_code
        == 201
    )
    return client


def create_project(client: TestClient) -> str:
    return client.post(
        "/api/v1/projects",
        json={"name": "Matrix", "topic": "", "description": "", "tags": []},
    ).json()["project_id"]


def create_paper(client: TestClient, project_id: str, title: str) -> dict[str, object]:
    return client.post(
        f"/api/v1/projects/{project_id}/papers/manual",
        json={"title": title},
    ).json()


def add_item(
    client: TestClient,
    project_id: str,
    paper: dict[str, object],
    *,
    kind: str,
    title: str,
    summary: str,
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/projects/{project_id}/papers/{paper['paper_id']}/analysis/items",
        json={
            "kind": kind,
            "display_label": None,
            "title": title,
            "summary": summary,
            "attributes": {},
            "tags": [],
            "writing_uses": [],
            "expected_revision": paper["revision"],
        },
    )
    assert response.status_code == 201
    updated = client.get(f"/api/v1/projects/{project_id}/papers/{paper['paper_id']}").json()
    return updated


def test_literature_matrix_derives_analysis_fields_and_readiness(tmp_path):
    client = initialized_client(tmp_path)
    project_id = create_project(client)
    paper = create_paper(client, project_id, "Agent Method")
    paper = add_item(
        client,
        project_id,
        paper,
        kind="research_problem",
        title="Long tasks fail",
        summary="长链任务容易中断。",
    )
    paper = add_item(
        client,
        project_id,
        paper,
        kind="method",
        title="Task tree",
        summary="使用任务树规划。",
    )
    paper = add_item(
        client,
        project_id,
        paper,
        kind="reviewer_limitation",
        title="Closed model",
        summary="只验证闭源模型。",
    )

    response = client.get(f"/api/v1/projects/{project_id}/matrices/literature")

    assert response.status_code == 200
    matrix = response.json()
    assert matrix["scope_id"] is None
    assert matrix["total"] == 1
    row = matrix["rows"][0]
    assert row["research_problems"] == ["长链任务容易中断。"]
    assert row["methods"] == ["使用任务树规划。"]
    assert row["limitations"] == ["只验证闭源模型。"]
    assert row["readiness"]["method_ready"] is True
    assert row["readiness"]["limitation_ready"] is True
    assert row["readiness"]["experiment_ready"] is False
    assert row["readiness"]["evidence_ready"] is False
    assert row["readiness"]["missing_categories"] == ["实验", "证据"]


def test_literature_matrix_uses_scope_order_and_reflects_paper_edits(tmp_path):
    client = initialized_client(tmp_path)
    project_id = create_project(client)
    paper_a = create_paper(client, project_id, "A")
    paper_b = create_paper(client, project_id, "B")
    scope = client.post(
        f"/api/v1/projects/{project_id}/analysis-scopes",
        json={
            "name": "Only B",
            "purpose": "",
            "paper_ids": [paper_b["paper_id"]],
            "source_filter_snapshot": {},
            "expected_revision": 0,
        },
    ).json()["scopes"][0]["scope"]

    full_b = client.get(f"/api/v1/projects/{project_id}/papers/{paper_b['paper_id']}").json()
    updated = client.patch(
        f"/api/v1/projects/{project_id}/papers/{paper_b['paper_id']}",
        json={
            "title": full_b["bibliography"]["title"],
            "short_title": full_b["bibliography"]["short_title"],
            "authors": full_b["bibliography"]["authors"],
            "affiliations": full_b["bibliography"]["affiliations"],
            "venue": None,
            "publication_date": None,
            "reading_date": None,
            "citation_count": None,
            "language": None,
            "keywords": [],
            "abstract_text": "",
            "urls": [],
            "code_url": None,
            "data_url": None,
            "group": "Core",
            "reading_status": "deep_read",
            "importance_score": 5,
            "one_sentence_summary": "核心论文。",
            "expected_revision": full_b["revision"],
        },
    )
    assert updated.status_code == 200

    response = client.get(
        f"/api/v1/projects/{project_id}/matrices/literature?scope_id={scope['scope_id']}"
    )

    assert response.status_code == 200
    matrix = response.json()
    assert matrix["scope_name"] == "Only B"
    assert matrix["total"] == 1
    assert matrix["rows"][0]["paper_id"] == paper_b["paper_id"]
    assert matrix["rows"][0]["group"] == "Core"
    assert matrix["rows"][0]["reading_status"] == "deep_read"
    assert matrix["rows"][0]["importance_score"] == 5
    assert paper_a["paper_id"] not in [row["paper_id"] for row in matrix["rows"]]
