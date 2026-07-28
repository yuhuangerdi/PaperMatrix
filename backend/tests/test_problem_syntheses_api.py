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


def create_project(client: TestClient, name: str = "Problem synthesis") -> str:
    response = client.post(
        "/api/v1/projects",
        json={"name": name, "topic": "", "description": "", "tags": []},
    )
    assert response.status_code == 201
    return response.json()["project_id"]


def create_paper_with_items(
    client: TestClient, project_id: str, title: str
) -> tuple[str, dict[str, str]]:
    response = client.post(
        f"/api/v1/projects/{project_id}/papers/manual",
        json={"title": title},
    )
    assert response.status_code == 201
    paper = response.json()
    revision = paper["revision"]
    item_ids: dict[str, str] = {}
    for kind, item_title in (
        ("research_problem", f"{title} problem"),
        ("method", f"{title} method"),
        ("experiment", f"{title} experiment"),
    ):
        created = client.post(
            f"/api/v1/projects/{project_id}/papers/{paper['paper_id']}/analysis/items",
            json={
                "kind": kind,
                "display_label": None,
                "title": item_title,
                "summary": "",
                "attributes": {},
                "tags": [],
                "writing_uses": [],
                "expected_revision": revision,
            },
        )
        assert created.status_code == 201
        analysis = created.json()
        revision = analysis["revision"]
        item_ids[kind] = analysis["items"][-1]["item_id"]
    return paper["paper_id"], item_ids


def create_scope(client: TestClient, project_id: str, paper_ids: list[str]) -> str:
    response = client.post(
        f"/api/v1/projects/{project_id}/analysis-scopes",
        json={
            "name": "核心集合",
            "purpose": "比较问题贡献",
            "paper_ids": paper_ids,
            "source_filter_snapshot": {},
            "expected_revision": 0,
        },
    )
    assert response.status_code == 201
    return response.json()["document"]["scopes"][0]["scope_id"]


def contribution_payload(
    *,
    problem_id: str,
    paper_id: str,
    items: dict[str, str],
    expected_revision: int,
) -> dict[str, object]:
    return {
        "problem_id": problem_id,
        "paper_id": paper_id,
        "research_problem_item_id": items["research_problem"],
        "method_item_id": items["method"],
        "experiment_item_id": items["experiment"],
        "resolution_level": "partially_resolved",
        "rationale": "只覆盖部分条件。",
        "supporting_evidence_ids": [],
        "counter_evidence": "长任务仍失败。",
        "conditions": "在固定工具集合下成立。",
        "user_judgment": "人工复核。",
        "expected_revision": expected_revision,
    }


def test_problem_board_contribution_crud_and_double_column_matrix(tmp_path):
    client = initialized_client(tmp_path)
    project_id = create_project(client)
    first_paper, first_items = create_paper_with_items(client, project_id, "Paper A")
    second_paper, second_items = create_paper_with_items(client, project_id, "Paper B")
    scope_id = create_scope(client, project_id, [first_paper, second_paper])

    empty = client.get(f"/api/v1/projects/{project_id}/problem-syntheses")
    assert empty.status_code == 200
    assert empty.json()["document"]["revision"] == 0

    problem_response = client.post(
        f"/api/v1/projects/{project_id}/field-problems",
        json={
            "name": "长程任务中的恢复",
            "definition": "智能体能否从中间失败恢复并继续完成任务。",
            "scope_note": "只讨论执行期故障。",
            "aliases": ["失败恢复"],
            "tags": ["agent"],
            "status": "active",
            "source_problem_refs": [
                {
                    "paper_id": first_paper,
                    "item_id": first_items["research_problem"],
                },
                {
                    "paper_id": second_paper,
                    "item_id": second_items["research_problem"],
                },
            ],
            "expected_revision": 0,
        },
    )
    assert problem_response.status_code == 201
    problem_id = problem_response.json()["document"]["field_problems"][0]["problem_id"]

    board_response = client.post(
        f"/api/v1/projects/{project_id}/problem-boards",
        json={
            "name": "恢复能力归纳",
            "purpose": "比较两篇论文如何处理失败恢复。",
            "scope_id": scope_id,
            "problem_ids": [problem_id],
            "paper_ids": [second_paper, first_paper],
            "expected_revision": 1,
        },
    )
    assert board_response.status_code == 201
    board = board_response.json()["document"]["boards"][0]
    assert board["paper_ids"] == [second_paper, first_paper]

    contribution_response = client.post(
        f"/api/v1/projects/{project_id}/paper-contributions",
        json=contribution_payload(
            problem_id=problem_id,
            paper_id=first_paper,
            items=first_items,
            expected_revision=2,
        ),
    )
    assert contribution_response.status_code == 201
    contribution = contribution_response.json()["document"]["paper_contributions"][0]

    matrix = client.get(
        f"/api/v1/projects/{project_id}/matrices/problems",
        params={"board_id": board["board_id"]},
    )
    assert matrix.status_code == 200
    body = matrix.json()
    assert [paper["paper_id"] for paper in body["papers"]] == [
        second_paper,
        first_paper,
    ]
    assert len(body["rows"][0]["cells"]) == 2
    assert body["rows"][0]["cells"][0]["contribution"] is None
    first_cell = body["rows"][0]["cells"][1]
    assert first_cell["method"]["item_title"] == "Paper A method"
    assert first_cell["contribution"]["resolution_level"] == "partially_resolved"
    assert first_cell["contribution"]["rationale"] == "只覆盖部分条件。"

    update_payload = contribution_payload(
        problem_id=problem_id,
        paper_id=first_paper,
        items=first_items,
        expected_revision=3,
    )
    update_payload["resolution_level"] = "not_resolved"
    update_payload["rationale"] = "论文尝试了恢复, 但未解决。"
    updated = client.patch(
        f"/api/v1/projects/{project_id}/paper-contributions/{contribution['contribution_id']}",
        json=update_payload,
    )
    assert updated.status_code == 200
    assert (
        updated.json()["document"]["paper_contributions"][0]["resolution_level"] == "not_resolved"
    )

    blocked_delete = client.request(
        "DELETE",
        f"/api/v1/projects/{project_id}/field-problems/{problem_id}",
        json={"expected_revision": 4},
    )
    assert blocked_delete.status_code == 422
    assert blocked_delete.json()["error"]["code"] == "PM-PROBLEM-002"

    removed = client.request(
        "DELETE",
        f"/api/v1/projects/{project_id}/paper-contributions/{contribution['contribution_id']}",
        json={"expected_revision": 4},
    )
    assert removed.status_code == 200
    assert removed.json()["document"]["revision"] == 5


def test_problem_synthesis_rejects_wrong_item_kind_and_out_of_scope_paper(tmp_path):
    client = initialized_client(tmp_path)
    project_id = create_project(client)
    paper_id, items = create_paper_with_items(client, project_id, "Included")
    other_paper, other_items = create_paper_with_items(client, project_id, "Excluded")
    scope_id = create_scope(client, project_id, [paper_id])

    invalid_problem = client.post(
        f"/api/v1/projects/{project_id}/field-problems",
        json={
            "name": "错误映射",
            "definition": "验证条目类型。",
            "source_problem_refs": [{"paper_id": paper_id, "item_id": items["method"]}],
            "expected_revision": 0,
        },
    )
    assert invalid_problem.status_code == 422
    assert invalid_problem.json()["error"]["code"] == "PM-PROBLEM-002"

    problem = client.post(
        f"/api/v1/projects/{project_id}/field-problems",
        json={
            "name": "有效问题",
            "definition": "有效定义。",
            "source_problem_refs": [{"paper_id": paper_id, "item_id": items["research_problem"]}],
            "expected_revision": 0,
        },
    ).json()["document"]["field_problems"][0]

    invalid_board = client.post(
        f"/api/v1/projects/{project_id}/problem-boards",
        json={
            "name": "越界集合",
            "scope_id": scope_id,
            "problem_ids": [problem["problem_id"]],
            "paper_ids": [paper_id, other_paper],
            "expected_revision": 1,
        },
    )
    assert invalid_board.status_code == 422
    assert invalid_board.json()["error"]["code"] == "PM-PROBLEM-002"

    invalid_contribution = client.post(
        f"/api/v1/projects/{project_id}/paper-contributions",
        json={
            **contribution_payload(
                problem_id=problem["problem_id"],
                paper_id=paper_id,
                items=items,
                expected_revision=1,
            ),
            "method_item_id": other_items["method"],
        },
    )
    assert invalid_contribution.status_code == 422
    assert invalid_contribution.json()["error"]["code"] == "PM-PROBLEM-002"


def test_problem_synthesis_revision_conflict(tmp_path):
    client = initialized_client(tmp_path)
    project_id = create_project(client)
    paper_id, items = create_paper_with_items(client, project_id, "Paper")

    first = client.post(
        f"/api/v1/projects/{project_id}/field-problems",
        json={
            "name": "问题一",
            "definition": "定义一。",
            "source_problem_refs": [{"paper_id": paper_id, "item_id": items["research_problem"]}],
            "expected_revision": 0,
        },
    )
    assert first.status_code == 201

    conflict = client.post(
        f"/api/v1/projects/{project_id}/field-problems",
        json={
            "name": "问题二",
            "definition": "定义二。",
            "source_problem_refs": [],
            "expected_revision": 0,
        },
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "PM-CONFLICT-001"
