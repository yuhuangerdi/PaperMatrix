# ruff: noqa: RUF001

from pathlib import Path

from fastapi.testclient import TestClient

from papermatrix.core.config import Settings
from papermatrix.main import create_app


def initialized_paper(tmp_path: Path) -> tuple[TestClient, Path, str, str]:
    repository_root = Path(__file__).resolve().parents[2]
    app = create_app(
        Settings(workspace_root=tmp_path / "default-workspace"),
        schema_root=repository_root / "contracts" / "schemas",
        local_config_path=tmp_path / "papermatrix.local.yaml",
    )
    client = TestClient(app)
    workspace_root = tmp_path / "workspace"
    paper_root = tmp_path / "library"
    paper_root.mkdir()
    initialized = client.post(
        "/api/v1/workspace/initialize",
        json={
            "root_path": str(workspace_root),
            "name": "研究",
            "allowed_paper_roots": [str(paper_root)],
        },
    )
    assert initialized.status_code == 201
    project = client.post(
        "/api/v1/projects",
        json={"name": "Evidence", "topic": "", "description": "", "tags": []},
    ).json()
    paper = client.post(
        f"/api/v1/projects/{project['project_id']}/papers/manual",
        json={"title": "Evidence First Research"},
    ).json()
    return client, workspace_root, project["project_id"], paper["paper_id"]


def test_note_template_save_and_revision_conflict(tmp_path: Path) -> None:
    client, workspace_root, project_id, paper_id = initialized_paper(tmp_path)
    endpoint = f"/api/v1/projects/{project_id}/papers/{paper_id}/note"

    initial = client.get(endpoint)
    assert initial.status_code == 200
    assert initial.json()["revision"] == 1
    assert "# Evidence First Research" in initial.json()["markdown"]
    assert "- 完整标题：Evidence First Research" in initial.json()["markdown"]
    assert list((workspace_root / "projects" / project_id / "notes").glob("*.md"))

    saved = client.put(
        endpoint,
        json={"markdown": "# My note\n\nEvidence on page 3.", "expected_revision": 1},
    )
    assert saved.status_code == 200
    assert saved.json()["revision"] == 2
    note_path = workspace_root / "projects" / project_id / "notes" / f"{paper_id}.md"
    persisted = note_path.read_text(encoding="utf-8")
    assert "revision: 2" in persisted
    assert "# My note" in persisted

    stale = client.put(
        endpoint,
        json={"markdown": "stale overwrite", "expected_revision": 1},
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "PM-CONFLICT-001"
    assert "stale overwrite" not in note_path.read_text(encoding="utf-8")


def test_persisted_default_note_does_not_expose_template_examples_as_candidates(
    tmp_path: Path,
) -> None:
    client, workspace_root, project_id, paper_id = initialized_paper(tmp_path)
    analysis_endpoint = f"/api/v1/projects/{project_id}/papers/{paper_id}/analysis"

    preview = client.post(f"{analysis_endpoint}/parse-note")

    assert preview.status_code == 200
    payload = preview.json()
    assert payload["note_revision"] == 1
    assert payload["candidates"] == []
    assert payload["removals"] == []
    assert payload["warnings"] == ["没有找到已填写的结构化内容, 请检查模板标题和内容。"]
    item_document = client.get(f"/api/v1/projects/{project_id}/papers/{paper_id}/note/items").json()
    assert item_document["candidates"] == []
    assert item_document["pending_candidate_count"] == 0
    assert item_document["warnings"] == ["没有找到已填写的结构化内容。"]
    assert list((workspace_root / "projects" / project_id / "notes").glob("*.md"))


def test_saved_note_is_automatically_parsed_by_note_items_endpoint(tmp_path: Path) -> None:
    client, _, project_id, paper_id = initialized_paper(tmp_path)
    note_endpoint = f"/api/v1/projects/{project_id}/papers/{paper_id}/note"
    markdown = """# Evidence

## 3. 本文解决思路和整体框架
### 3.1 核心思路
使用状态检查点恢复失败任务。

## 6. 具体流程和技术细节
### 6.2 任务规划
- 输入: 失败状态
- 输出: 恢复计划
"""
    saved = client.put(
        note_endpoint,
        json={"markdown": markdown, "expected_revision": 1},
    )
    assert saved.status_code == 200

    document = client.get(f"{note_endpoint}/items")

    assert document.status_code == 200
    payload = document.json()
    assert payload["note_revision"] == 2
    assert payload["pending_candidate_count"] == 2
    assert payload["warnings"] == []
    assert [candidate["kind"] for candidate in payload["candidates"]] == [
        "method",
        "method_component",
    ]
    assert payload["items"] == []


def test_confirming_grouped_table_candidate_consolidates_legacy_row_items(
    tmp_path: Path,
) -> None:
    client, _, project_id, paper_id = initialized_paper(tmp_path)
    analysis_endpoint = f"/api/v1/projects/{project_id}/papers/{paper_id}/analysis"
    note_endpoint = f"/api/v1/projects/{project_id}/papers/{paper_id}/note"
    first = client.post(
        f"{analysis_endpoint}/items",
        json={
            "kind": "method",
            "title": "规则工具",
            "summary": "旧版逐行投影",
            "attributes": {},
            "evidence_refs": [
                {
                    "paper_id": paper_id,
                    "page_label": "6",
                    "pdf_page_index": 7,
                    "section": "Related Work",
                    "figure": None,
                    "table": "Table 1",
                    "locator_note": "方法分类",
                    "source_item_id": None,
                }
            ],
            "tags": ["经典方法"],
            "writing_uses": ["RELATED"],
            "expected_revision": 1,
        },
    ).json()["items"][0]
    second = client.post(
        f"{analysis_endpoint}/items",
        json={
            "kind": "method",
            "title": "Agent",
            "summary": "旧版逐行投影",
            "attributes": {},
            "evidence_refs": [],
            "tags": ["动态规划"],
            "writing_uses": ["METHOD"],
            "expected_revision": 2,
        },
    ).json()["items"][1]
    markdown = f"""## 2. 现有方案分类和经典文献
### 2.1 现有方法分类
| 类别 | 核心思路 | 优点 | 缺点 |
|---|---|---|---|
| <!-- papermatrix:item:{first["item_id"]} --> 规则工具 | 固定工作流 | 可复现 | 泛化较弱 |
| <!-- papermatrix:item:{second["item_id"]} --> Agent | 动态规划 | 适应性强 | 状态可能漂移 |
"""
    saved = client.put(
        note_endpoint,
        json={"markdown": markdown, "expected_revision": 1},
    )
    assert saved.status_code == 200

    document = client.get(f"{note_endpoint}/items").json()
    assert document["pending_candidate_count"] == 1
    assert document["items"] == []
    candidate = document["candidates"][0]
    assert candidate["title"] == "现有方法分类"
    assert set(candidate["superseded_item_ids"]) == {
        first["item_id"],
        second["item_id"],
    }
    assert "旧版表格行条目" in document["warnings"][0]

    imported = client.post(
        f"{analysis_endpoint}/import-candidates",
        json={
            "candidate_ids": [candidate["candidate_id"]],
            "expected_note_revision": 2,
            "expected_paper_revision": 3,
        },
    )
    assert imported.status_code == 200
    result = imported.json()
    assert set(result["superseded_item_ids"]) == {
        first["item_id"],
        second["item_id"],
    }
    assert len(result["analysis"]["items"]) == 1
    grouped = result["analysis"]["items"][0]
    assert grouped["title"] == "现有方法分类"
    assert grouped["tags"] == ["经典方法", "动态规划"]
    assert grouped["writing_uses"] == ["RELATED", "METHOD"]
    assert grouped["evidence_refs"][0]["table"] == "Table 1"
    assert result["note"]["markdown"].count("papermatrix:item:") == 1
    assert first["item_id"] not in result["note"]["markdown"]
    assert second["item_id"] not in result["note"]["markdown"]

    refreshed = client.get(f"{note_endpoint}/items").json()
    assert refreshed["pending_candidate_count"] == 0
    assert refreshed["items"][0]["sync_status"] == "synced"


def test_supplement_is_saved_independently_with_revision_conflicts(tmp_path: Path) -> None:
    client, workspace_root, project_id, paper_id = initialized_paper(tmp_path)
    endpoint = f"/api/v1/projects/{project_id}/papers/{paper_id}/note/supplement"

    initial = client.get(endpoint)
    assert initial.status_code == 200
    assert initial.json()["markdown"] == ""
    assert initial.json()["revision"] == 0

    saved = client.put(
        endpoint,
        json={"markdown": "# 我的补充\n\n自由记录。", "expected_revision": 0},
    )
    assert saved.status_code == 200
    assert saved.json()["revision"] == 1
    supplement_file = (
        workspace_root / "projects" / project_id / "notes" / f"{paper_id}.supplement.md"
    )
    assert supplement_file.is_file()
    assert f"paper_id: {paper_id}" in supplement_file.read_text(encoding="utf-8")
    assert (workspace_root / "projects" / project_id / "notes" / f"{paper_id}.md").exists()

    conflict = client.put(endpoint, json={"markdown": "过期草稿", "expected_revision": 0})
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "PM-CONFLICT-001"


def test_question_create_answer_evidence_conflict_and_delete(tmp_path: Path) -> None:
    client, workspace_root, project_id, paper_id = initialized_paper(tmp_path)
    endpoint = f"/api/v1/projects/{project_id}/papers/{paper_id}/questions"

    initial = client.get(endpoint)
    assert initial.status_code == 200
    assert initial.json()["revision"] == 0
    assert initial.json()["questions"] == []

    created = client.post(
        endpoint,
        json={
            "question": "主要结论由哪项实验支持?",
            "status": "open",
            "answer": "",
            "evidence": [],
            "tags": ["experiment", "experiment"],
            "expected_revision": 0,
        },
    )
    assert created.status_code == 201
    document = created.json()
    assert document["revision"] == 1
    assert document["questions"][0]["tags"] == ["experiment"]
    question_id = document["questions"][0]["question_id"]

    answered = client.patch(
        f"{endpoint}/{question_id}",
        json={
            "question": "主要结论由哪项实验支持?",
            "status": "answered",
            "answer": "由表 3 的主实验支持。",
            "evidence": [
                {
                    "paper_id": paper_id,
                    "page_label": "8",
                    "pdf_page_index": 9,
                    "section": "Evaluation",
                    "figure": None,
                    "table": "Table 3",
                    "locator_note": "主结果",
                    "source_item_id": None,
                }
            ],
            "tags": ["experiment"],
            "expected_revision": 1,
        },
    )
    assert answered.status_code == 200
    assert answered.json()["revision"] == 2
    item = answered.json()["questions"][0]
    assert item["status"] == "answered"
    assert item["evidence"][0]["paper_id"] == paper_id
    assert item["evidence"][0]["table"] == "Table 3"

    stale = client.patch(
        f"{endpoint}/{question_id}",
        json={
            "question": "过期修改",
            "status": "open",
            "answer": "",
            "evidence": [],
            "tags": [],
            "expected_revision": 1,
        },
    )
    assert stale.status_code == 409

    deleted = client.delete(f"{endpoint}/{question_id}?expected_revision=2")
    assert deleted.status_code == 200
    assert deleted.json()["revision"] == 3
    assert deleted.json()["questions"] == []
    questions_path = workspace_root / "projects" / project_id / "questions" / f"{paper_id}.yaml"
    assert questions_path.is_file()
    assert "revision: 3" in questions_path.read_text(encoding="utf-8")


def test_answered_question_requires_answer(tmp_path: Path) -> None:
    client, _, project_id, paper_id = initialized_paper(tmp_path)
    response = client.post(
        f"/api/v1/projects/{project_id}/papers/{paper_id}/questions",
        json={
            "question": "是否回答?",
            "status": "answered",
            "answer": "",
            "evidence": [],
            "tags": [],
            "expected_revision": 0,
        },
    )
    assert response.status_code == 422


def test_analysis_item_crud_evidence_and_revision_conflict(tmp_path: Path) -> None:
    client, _, project_id, paper_id = initialized_paper(tmp_path)
    endpoint = f"/api/v1/projects/{project_id}/papers/{paper_id}/analysis"

    initial = client.get(endpoint)
    assert initial.status_code == 200
    assert initial.json()["revision"] == 1
    assert initial.json()["items"] == []

    created = client.post(
        f"{endpoint}/items",
        json={
            "kind": "method",
            "title": "Evidence-guided planning",
            "summary": "The planner links decisions to observations.",
            "attributes": {"architecture": "planner-executor"},
            "evidence_refs": [
                {
                    "paper_id": "00000000-0000-4000-8000-000000000000",
                    "page_label": "6",
                    "pdf_page_index": 7,
                    "section": "Method",
                    "figure": "Figure 2",
                    "table": None,
                    "locator_note": "Architecture overview",
                    "source_item_id": None,
                }
            ],
            "tags": ["agent", "agent"],
            "writing_uses": ["METHOD", "METHOD"],
            "expected_revision": 1,
        },
    )
    assert created.status_code == 201
    document = created.json()
    assert document["revision"] == 2
    item = document["items"][0]
    assert item["tags"] == ["agent"]
    assert item["writing_uses"] == ["METHOD"]
    assert item["evidence_refs"][0]["paper_id"] == paper_id
    item_id = item["item_id"]

    updated = client.patch(
        f"{endpoint}/items/{item_id}",
        json={
            "kind": "finding",
            "title": "Evidence improves recovery",
            "summary": "The ablation reports fewer unrecovered failures.",
            "attributes": {"metric": "recovery rate"},
            "evidence_refs": [],
            "tags": ["result"],
            "writing_uses": ["DISCUSSION"],
            "expected_revision": 2,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["revision"] == 3
    assert updated.json()["items"][0]["kind"] == "finding"

    stale = client.patch(
        f"{endpoint}/items/{item_id}",
        json={
            "kind": "finding",
            "title": "Stale overwrite",
            "summary": "",
            "attributes": {},
            "evidence_refs": [],
            "tags": [],
            "writing_uses": [],
            "expected_revision": 2,
        },
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "PM-CONFLICT-001"

    deleted = client.delete(f"{endpoint}/items/{item_id}?expected_revision=3")
    assert deleted.status_code == 200
    assert deleted.json()["revision"] == 4
    assert deleted.json()["items"] == []


def test_note_item_favorite_is_revision_safe_and_survives_markdown_synchronization(
    tmp_path: Path,
) -> None:
    client, _, project_id, paper_id = initialized_paper(tmp_path)
    note_endpoint = f"/api/v1/projects/{project_id}/papers/{paper_id}/note"
    analysis_endpoint = f"/api/v1/projects/{project_id}/papers/{paper_id}/analysis"
    markdown = """## 3. 本文解决思路和整体框架
### 3.1 核心思路
使用状态检查点恢复失败任务。
"""
    assert (
        client.put(note_endpoint, json={"markdown": markdown, "expected_revision": 1}).status_code
        == 200
    )
    preview = client.post(f"{analysis_endpoint}/parse-note").json()
    item_id = preview["candidates"][0]["candidate_id"]
    imported = client.post(
        f"{analysis_endpoint}/import-candidates",
        json={
            "candidate_ids": [item_id],
            "expected_note_revision": 2,
            "expected_paper_revision": 1,
        },
    ).json()

    favorite = client.patch(
        f"{note_endpoint}/items/{item_id}/favorite",
        json={"is_favorite": True, "expected_paper_revision": imported["analysis"]["revision"]},
    )
    assert favorite.status_code == 200
    assert favorite.json()["item"]["is_favorite"] is True
    assert favorite.json()["analysis"]["revision"] == 3
    assert client.get(f"{note_endpoint}/items").json()["items"][0]["is_favorite"] is True

    changed_markdown = imported["note"]["markdown"].replace(
        "使用状态检查点恢复失败任务。",
        "使用可验证检查点恢复失败任务。",
    )
    assert (
        client.put(
            note_endpoint,
            json={"markdown": changed_markdown, "expected_revision": imported["note"]["revision"]},
        ).status_code
        == 200
    )
    synchronized = client.post(
        f"{analysis_endpoint}/import-candidates",
        json={
            "candidate_ids": [item_id],
            "expected_note_revision": 4,
            "expected_paper_revision": 3,
        },
    )
    assert synchronized.status_code == 200
    assert synchronized.json()["synchronized_items"][0]["is_favorite"] is True

    stale = client.patch(
        f"{note_endpoint}/items/{item_id}/favorite",
        json={"is_favorite": False, "expected_paper_revision": 3},
    )
    assert stale.status_code == 409


def test_note_candidate_preview_confirm_duplicate_and_stale_protection(tmp_path: Path) -> None:
    client, workspace_root, project_id, paper_id = initialized_paper(tmp_path)
    note_endpoint = f"/api/v1/projects/{project_id}/papers/{paper_id}/note"
    analysis_endpoint = f"/api/v1/projects/{project_id}/papers/{paper_id}/analysis"
    markdown = """# Evidence

## 3. 本文解决思路和整体框架
### 3.1 核心思路
使用证据反馈重新规划失败任务。

## 8. 批判性评价
### 8.2 作者承认的局限
只在三个公开基准上验证。
"""
    saved = client.put(
        note_endpoint,
        json={"markdown": markdown, "expected_revision": 1},
    )
    assert saved.status_code == 200
    note_path = workspace_root / "projects" / project_id / "notes" / f"{paper_id}.md"
    note_before = note_path.read_bytes()
    paper_path = workspace_root / "projects" / project_id / "papers" / f"{paper_id}.yaml"
    paper_before = paper_path.read_bytes()

    preview = client.post(f"{analysis_endpoint}/parse-note")
    assert preview.status_code == 200
    body = preview.json()
    assert body["note_revision"] == 2
    assert body["paper_revision"] == 1
    assert [item["kind"] for item in body["candidates"]] == ["method", "author_limitation"]
    assert note_path.read_bytes() == note_before
    assert paper_path.read_bytes() == paper_before

    selected_id = body["candidates"][0]["candidate_id"]
    imported = client.post(
        f"{analysis_endpoint}/import-candidates",
        json={
            "candidate_ids": [selected_id],
            "expected_note_revision": 2,
            "expected_paper_revision": 1,
        },
    )
    assert imported.status_code == 200
    result = imported.json()
    assert result["analysis"]["revision"] == 2
    assert result["imported_items"][0]["item_id"] == selected_id
    item = result["imported_items"][0]
    assert item["section_key"] == "section-3"
    assert item["section_title"] == "3. 本文解决思路和整体框架"
    assert item["section_order"] == 1
    assert item["source_anchor"] == f"papermatrix:item:{selected_id}"
    assert item["source_note_revision"] == 3
    assert result["note"]["revision"] == 3
    assert f"<!-- papermatrix:item:{selected_id} -->" in result["note"]["markdown"]
    assert "使用证据反馈重新规划失败任务。" in result["note"]["markdown"]
    assert note_path.read_bytes() != note_before

    duplicate_preview = client.post(f"{analysis_endpoint}/parse-note").json()
    duplicate = next(
        item for item in duplicate_preview["candidates"] if item["candidate_id"] == selected_id
    )
    assert duplicate["duplicate_item_id"] == selected_id
    skipped = client.post(
        f"{analysis_endpoint}/import-candidates",
        json={
            "candidate_ids": [selected_id],
            "expected_note_revision": 3,
            "expected_paper_revision": 2,
        },
    )
    assert skipped.status_code == 200
    assert skipped.json()["analysis"]["revision"] == 2
    assert skipped.json()["skipped_candidate_ids"] == [selected_id]

    changed_note = client.put(
        note_endpoint,
        json={"markdown": f"{result['note']['markdown']}\n更新", "expected_revision": 3},
    )
    assert changed_note.status_code == 200
    stale = client.post(
        f"{analysis_endpoint}/import-candidates",
        json={
            "candidate_ids": [body["candidates"][1]["candidate_id"]],
            "expected_note_revision": 3,
            "expected_paper_revision": 2,
        },
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "PM-ANALYSIS-002"
    assert stale.json()["error"]["details"]["resource"] == "note"
    assert client.get(analysis_endpoint).json()["revision"] == 2


def test_note_item_mode_updates_only_anchored_fragment_and_rejects_stale_edit(
    tmp_path: Path,
) -> None:
    client, _, project_id, paper_id = initialized_paper(tmp_path)
    note_endpoint = f"/api/v1/projects/{project_id}/papers/{paper_id}/note"
    analysis_endpoint = f"/api/v1/projects/{project_id}/papers/{paper_id}/analysis"
    markdown = """# Evidence

## 3. 本文解决思路和整体框架
### 3.1 核心思路
使用证据反馈重新规划失败任务。

## 8. 批判性评价
### 8.2 作者承认的局限
只在三个公开基准上验证。
"""
    client.put(note_endpoint, json={"markdown": markdown, "expected_revision": 1})
    preview = client.post(f"{analysis_endpoint}/parse-note").json()
    method_id = preview["candidates"][0]["candidate_id"]
    imported = client.post(
        f"{analysis_endpoint}/import-candidates",
        json={
            "candidate_ids": [method_id],
            "expected_note_revision": 2,
            "expected_paper_revision": 1,
        },
    ).json()

    item_endpoint = f"{note_endpoint}/items"
    document = client.get(item_endpoint)
    assert document.status_code == 200
    source = document.json()["items"][0]
    assert source["sync_status"] == "synced"
    assert source["markdown"].startswith("### 3.1 核心思路")

    replacement = "### 3.1 核心思路\n使用检查点恢复失败任务。"
    updated = client.put(
        f"{item_endpoint}/{method_id}",
        json={
            "markdown": replacement,
            "expected_note_revision": imported["note"]["revision"],
            "expected_paper_revision": imported["analysis"]["revision"],
            "expected_source_fingerprint": source["source_fingerprint"],
        },
    )
    assert updated.status_code == 200
    result = updated.json()
    assert result["note"]["revision"] == 4
    assert result["analysis"]["revision"] == 3
    assert result["item"]["summary"] == "使用检查点恢复失败任务。"
    assert "只在三个公开基准上验证。" in result["note"]["markdown"]
    assert result["note"]["markdown"].count(f"papermatrix:item:{method_id}") == 1

    stale = client.put(
        f"{item_endpoint}/{method_id}",
        json={
            "markdown": "### 3.1 核心思路\n过期覆盖。",
            "expected_note_revision": 3,
            "expected_paper_revision": 2,
            "expected_source_fingerprint": source["source_fingerprint"],
        },
    )
    assert stale.status_code == 409
    assert "过期覆盖" not in client.get(note_endpoint).json()["markdown"]


def test_external_markdown_change_requires_review_before_projection_sync(tmp_path: Path) -> None:
    client, _, project_id, paper_id = initialized_paper(tmp_path)
    note_endpoint = f"/api/v1/projects/{project_id}/papers/{paper_id}/note"
    analysis_endpoint = f"/api/v1/projects/{project_id}/papers/{paper_id}/analysis"
    markdown = """# Evidence

## 3. 本文解决思路和整体框架
### 3.1 核心思路
使用证据反馈重新规划失败任务。
"""
    client.put(note_endpoint, json={"markdown": markdown, "expected_revision": 1})
    preview = client.post(f"{analysis_endpoint}/parse-note").json()
    method_id = preview["candidates"][0]["candidate_id"]
    imported = client.post(
        f"{analysis_endpoint}/import-candidates",
        json={
            "candidate_ids": [method_id],
            "expected_note_revision": 2,
            "expected_paper_revision": 1,
        },
    ).json()
    externally_changed = imported["note"]["markdown"].replace(
        "使用证据反馈重新规划失败任务。",
        "外部编辑器改为使用状态检查点。",
    )
    saved = client.put(
        note_endpoint,
        json={"markdown": externally_changed, "expected_revision": 3},
    )
    assert saved.status_code == 200

    item_document = client.get(f"{note_endpoint}/items").json()
    assert item_document["items"][0]["sync_status"] == "review_required"
    assert item_document["pending_candidate_count"] == 1
    changed_preview = client.post(f"{analysis_endpoint}/parse-note").json()
    changed = changed_preview["candidates"][0]
    assert changed["candidate_id"] == method_id
    assert changed["sync_status"] == "modified"

    synchronized = client.post(
        f"{analysis_endpoint}/import-candidates",
        json={
            "candidate_ids": [method_id],
            "expected_note_revision": 4,
            "expected_paper_revision": 2,
        },
    )
    assert synchronized.status_code == 200
    result = synchronized.json()
    assert result["imported_items"] == []
    assert result["synchronized_items"][0]["item_id"] == method_id
    assert result["synchronized_items"][0]["summary"] == "外部编辑器改为使用状态检查点。"
    assert result["note"]["revision"] == 4
    assert client.get(f"{note_endpoint}/items").json()["items"][0]["sync_status"] == "synced"


def test_removed_source_can_be_deleted_in_review_and_items_support_batch_delete(
    tmp_path: Path,
) -> None:
    client, _, project_id, paper_id = initialized_paper(tmp_path)
    note_endpoint = f"/api/v1/projects/{project_id}/papers/{paper_id}/note"
    analysis_endpoint = f"/api/v1/projects/{project_id}/papers/{paper_id}/analysis"
    markdown = """# Evidence

## 3. 本文解决思路和整体框架
### 3.1 核心思路
使用状态检查点恢复失败任务。

## 8. 批判性评价
### 8.2 作者承认的局限
只在公开基准上验证。
"""
    saved = client.put(
        note_endpoint,
        json={"markdown": markdown, "expected_revision": 1},
    )
    assert saved.status_code == 200
    preview = client.post(f"{analysis_endpoint}/parse-note").json()
    candidate_ids = [item["candidate_id"] for item in preview["candidates"]]
    imported = client.post(
        f"{analysis_endpoint}/import-candidates",
        json={
            "candidate_ids": candidate_ids,
            "expected_note_revision": 2,
            "expected_paper_revision": 1,
        },
    ).json()
    method_id, limitation_id = candidate_ids
    method_fragment = (
        f"<!-- papermatrix:item:{method_id} -->\n### 3.1 核心思路\n使用状态检查点恢复失败任务。\n\n"
    )
    changed_markdown = imported["note"]["markdown"].replace(method_fragment, "")
    changed = client.put(
        note_endpoint,
        json={"markdown": changed_markdown, "expected_revision": 3},
    )
    assert changed.status_code == 200

    review = client.get(f"{note_endpoint}/items").json()
    assert review["pending_candidate_count"] == 1
    assert review["removals"] == [
        {
            "item_id": method_id,
            "kind": "method",
            "title": "核心思路",
            "section_key": "section-3",
            "section_title": "3. 本文解决思路和整体框架",
            "section_order": 1,
        }
    ]
    deleted_in_review = client.post(
        f"{analysis_endpoint}/import-candidates",
        json={
            "candidate_ids": [],
            "removal_item_ids": [method_id],
            "expected_note_revision": 4,
            "expected_paper_revision": 2,
        },
    )
    assert deleted_in_review.status_code == 200
    reviewed = deleted_in_review.json()
    assert reviewed["deleted_item_ids"] == [method_id]
    assert [item["item_id"] for item in reviewed["analysis"]["items"]] == [limitation_id]

    batch_deleted = client.post(
        f"{note_endpoint}/items/delete",
        json={
            "item_ids": [limitation_id],
            "expected_note_revision": 4,
            "expected_paper_revision": 3,
        },
    )
    assert batch_deleted.status_code == 200
    result = batch_deleted.json()
    assert result["deleted_item_ids"] == [limitation_id]
    assert result["analysis"]["items"] == []
    assert result["note"]["revision"] == 5
    assert "作者承认的局限" not in result["note"]["markdown"]
