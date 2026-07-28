# ruff: noqa: RUF001

import hashlib
from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from papermatrix.core.config import Settings
from papermatrix.main import create_app


def make_pdf(path: Path, *, title: str = "Reliable Agents") -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=300)
    writer.add_metadata({"/Title": title, "/Author": "Researcher"})
    with path.open("wb") as handle:
        writer.write(handle)


def initialized_client(tmp_path: Path) -> tuple[TestClient, Path, Path, str]:
    repository_root = Path(__file__).resolve().parents[2]
    app = create_app(
        Settings(
            workspace_root=tmp_path / "default-workspace",
            max_upload_bytes=1024 * 1024,
        ),
        schema_root=repository_root / "contracts" / "schemas",
        local_config_path=tmp_path / "papermatrix.local.yaml",
    )
    client = TestClient(app)
    workspace_root = tmp_path / "workspace"
    paper_root = tmp_path / "library"
    paper_root.mkdir()
    response = client.post(
        "/api/v1/workspace/initialize",
        json={
            "root_path": str(workspace_root),
            "name": "研究",
            "allowed_paper_roots": [str(paper_root)],
        },
    )
    assert response.status_code == 201
    project = client.post(
        "/api/v1/projects",
        json={"name": "Agents", "topic": "", "description": "", "tags": []},
    ).json()
    return client, workspace_root, paper_root, project["project_id"]


def test_scan_import_duplicate_status_and_metadata_only_delete(tmp_path: Path) -> None:
    client, workspace_root, paper_root, project_id = initialized_client(tmp_path)
    source = paper_root / "agent.pdf"
    make_pdf(source)
    original_bytes = source.read_bytes()
    original_hash = hashlib.sha256(original_bytes).hexdigest()
    original_mtime_ns = source.stat().st_mtime_ns

    scanned = client.post(
        "/api/v1/paper-sources/scan",
        json={"directory": str(paper_root), "recursive": False},
    )
    assert scanned.status_code == 200
    scan = scanned.json()
    assert scan["items"][0]["title"] == "Reliable Agents"
    assert scan["items"][0]["page_count"] == 1

    payload = {
        "scan_token": scan["scan_token"],
        "candidate_ids": [scan["items"][0]["candidate_id"]],
    }
    imported = client.post(f"/api/v1/projects/{project_id}/papers/import", json=payload)
    assert imported.status_code == 201
    paper = imported.json()["imported"][0]
    assert paper["source"]["path"] == str(source.resolve())
    assert paper["source"]["status"] == "available"
    assert not list(workspace_root.rglob("*.pdf"))
    note_endpoint = f"/api/v1/projects/{project_id}/papers/{paper['paper_id']}/note"
    initial_note = client.get(note_endpoint).json()
    assert initial_note["revision"] == 1
    assert "- 完整标题：Reliable Agents" in initial_note["markdown"]
    assert "- 作者：Researcher" in initial_note["markdown"]

    updated = client.patch(
        f"/api/v1/projects/{project_id}/papers/{paper['paper_id']}",
        json={
            "title": "Reliable Agent Evaluation",
            "short_title": "ReliableAgent",
            "authors": ["Researcher"],
            "affiliations": ["Xidian University"],
            "venue": "USENIX Security",
            "publication_date": "2026-07-01",
            "reading_date": "2026-07-27",
            "citation_count": 12,
            "language": "en",
            "keywords": ["agent", "security"],
            "abstract_text": "Evaluation of agent reliability.",
            "urls": ["https://example.com/paper"],
            "code_url": "https://example.com/code",
            "data_url": "https://example.com/data",
            "group": "核心文献",
            "reading_status": "deep_read",
            "importance_score": 5,
            "one_sentence_summary": "本文评估 Agent 的可靠性。",
            "expected_revision": 1,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["bibliography"]["affiliations"] == ["Xidian University"]
    assert updated.json()["organization"]["group"] == "核心文献"
    assert updated.json()["organization"]["reading_status"] == "deep_read"
    assert updated.json()["bibliography"]["code_url"] == "https://example.com/code"
    assert updated.json()["revision"] == 2
    note_after_metadata_edit = client.get(note_endpoint).json()
    assert note_after_metadata_edit["revision"] == 2
    assert "# ReliableAgent" in note_after_metadata_edit["markdown"]
    assert "- 署名单位：Xidian University" in note_after_metadata_edit["markdown"]
    assert "- 摘要：Evaluation of agent reliability." in note_after_metadata_edit["markdown"]
    assert "- 阅读状态：精读" in note_after_metadata_edit["markdown"]
    assert "- 重要程度：5" in note_after_metadata_edit["markdown"]
    assert "- 论文链接：https://example.com/paper" in note_after_metadata_edit["markdown"]

    duplicate = client.post(f"/api/v1/projects/{project_id}/papers/import", json=payload)
    assert duplicate.status_code == 201
    assert duplicate.json()["imported"] == []
    assert duplicate.json()["skipped"][0]["reason"] == "项目中已登记"

    listed = client.get(
        f"/api/v1/projects/{project_id}/papers?q=reliable&sort=title&group=核心文献"
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["source_status"] == "available"
    assert listed.json()["items"][0]["citation_count"] == 12

    removed = client.delete(
        f"/api/v1/projects/{project_id}/papers/{paper['paper_id']}?confirm_metadata_only=true"
    )
    assert removed.status_code == 200
    assert removed.json()["source_pdf_untouched"] is True
    assert source.read_bytes() == original_bytes
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original_hash
    assert source.stat().st_mtime_ns == original_mtime_ns


def test_single_upload_creates_unlinked_record_without_storing_pdf(tmp_path: Path) -> None:
    client, workspace_root, paper_root, project_id = initialized_client(tmp_path)
    source = paper_root / "upload.pdf"
    make_pdf(source, title="Transient Upload")
    content = source.read_bytes()

    response = client.post(
        f"/api/v1/projects/{project_id}/papers/upload",
        files={"file": ("upload.pdf", content, "application/pdf")},
    )

    assert response.status_code == 201
    paper = response.json()
    assert paper["bibliography"]["title"] == "Transient Upload"
    assert paper["source"]["status"] == "unlinked"
    assert paper["source"]["path"] is None
    assert paper["source"]["page_count"] == 1
    assert not list(workspace_root.rglob("*.pdf"))


def test_manual_record_can_be_relinked_and_missing_record_is_reported(tmp_path: Path) -> None:
    client, workspace_root, paper_root, project_id = initialized_client(tmp_path)
    source = paper_root / "linked.pdf"
    make_pdf(source)

    manual = client.post(
        f"/api/v1/projects/{project_id}/papers/manual",
        json={"title": "No source yet"},
    )
    assert manual.status_code == 201
    paper = manual.json()
    assert paper["source"]["status"] == "unlinked"

    relinked = client.post(
        f"/api/v1/projects/{project_id}/papers/{paper['paper_id']}/relink",
        json={"new_path": str(source), "expected_revision": 1},
    )
    assert relinked.status_code == 200
    assert relinked.json()["source"]["status"] == "available"
    assert relinked.json()["revision"] == 2

    missing_id = "33333333-3333-4333-8333-333333333333"
    missing_record = workspace_root / "projects" / project_id / "papers" / f"{missing_id}.yaml"
    missing_record.write_text(
        f"""schema_version: 3
paper_id: {missing_id}
project_id: {project_id}
source:
  path: {paper_root / "gone.pdf"}
  path_mode: absolute
  original_filename: gone.pdf
  size_bytes: 10
  modified_at: '2026-07-27T00:00:00Z'
  fingerprint: '10:1'
  sha256: null
  page_count: null
  status: available
bibliography:
  title: Missing paper
  short_title: ''
  authors: []
  affiliations: []
  year: null
  venue: null
  publication_date: null
  citation_count: null
  language: null
  keywords: []
  abstract_text: ''
  publication_type: other
  doi: null
  arxiv_id: null
  urls: []
  code_url: null
  data_url: null
organization:
  topics: []
  tags: []
  group: null
  reading_date: null
  reading_status: unread
  priority: null
  importance_score: null
  confidence_score: null
  reproduction_value: null
  writing_uses: []
  one_sentence_summary: ''
structured_summary:
  background: {{}}
  related_work: {{}}
  approach: {{}}
  challenges: []
  innovations: []
  additional_contribution: {{}}
  experiment: {{}}
  evaluation: {{}}
created_at: '2026-07-27T00:00:00Z'
updated_at: '2026-07-27T00:00:00Z'
revision: 1
""",
        encoding="utf-8",
    )
    listed = client.get(f"/api/v1/projects/{project_id}/papers?source_status=missing").json()
    assert listed["total"] == 1
    assert listed["items"][0]["source_status"] == "missing"


def test_direct_path_link_rejects_outside_root_and_large_upload(tmp_path: Path) -> None:
    client, _, _, project_id = initialized_client(tmp_path)
    outside = tmp_path / "outside.pdf"
    make_pdf(outside)

    forbidden = client.post(
        f"/api/v1/projects/{project_id}/papers/link",
        json={"path": str(outside)},
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "PM-PATH-002"

    too_large = client.post(
        f"/api/v1/projects/{project_id}/papers/upload",
        files={"file": ("large.pdf", b"x" * (1024 * 1024 + 1), "application/pdf")},
    )
    assert too_large.status_code == 413
    assert too_large.json()["error"]["code"] == "PM-PAPER-005"


def test_invalid_paper_record_is_listed_and_can_be_deleted_without_touching_pdf(
    tmp_path: Path,
) -> None:
    client, workspace_root, paper_root, project_id = initialized_client(tmp_path)
    source = paper_root / "legacy.pdf"
    make_pdf(source, title="Legacy source")
    original_bytes = source.read_bytes()
    valid = client.post(
        f"/api/v1/projects/{project_id}/papers/manual",
        json={"title": "Valid record"},
    )
    assert valid.status_code == 201

    invalid_id = "44444444-4444-4444-8444-444444444444"
    papers_dir = workspace_root / "projects" / project_id / "papers"
    invalid_path = papers_dir / f"{invalid_id}.yaml"
    invalid_path.write_text(
        f"""schema_version: 5
paper_id: {invalid_id}
project_id: {project_id}
source:
  path: {source}
bibliography:
  title: Legacy incompatible record
revision: 1
""",
        encoding="utf-8",
    )
    note_path = workspace_root / "projects" / project_id / "notes" / f"{invalid_id}.md"
    note_path.write_text("# Legacy note\n", encoding="utf-8")
    supplement_path = (
        workspace_root / "projects" / project_id / "notes" / f"{invalid_id}.supplement.md"
    )
    supplement_path.write_text("# Legacy supplement\n", encoding="utf-8")

    listed = client.get(f"/api/v1/projects/{project_id}/papers")

    assert listed.status_code == 200
    payload = listed.json()
    assert payload["total"] == 1
    assert payload["items"][0]["title"] == "Valid record"
    assert payload["invalid_total"] == 1
    assert payload["invalid_items"] == [
        {
            "paper_id": invalid_id,
            "title": "Legacy incompatible record",
            "schema_version": 5,
            "reason": "记录内容不符合当前 Paper Schema",
        }
    ]

    removed = client.delete(
        f"/api/v1/projects/{project_id}/papers/{invalid_id}?confirm_metadata_only=true"
    )

    assert removed.status_code == 200
    assert removed.json()["source_pdf_untouched"] is True
    assert not invalid_path.exists()
    assert not note_path.exists()
    assert not supplement_path.exists()
    assert source.read_bytes() == original_bytes
    relisted = client.get(f"/api/v1/projects/{project_id}/papers").json()
    assert relisted["total"] == 1
    assert relisted["invalid_total"] == 0
