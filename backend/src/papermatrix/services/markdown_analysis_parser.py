"""Conservative parser for the headings, lists and tables in the note template."""

from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
from uuid import NAMESPACE_URL, UUID, uuid5

from papermatrix.domain.note_analysis import NoteAnalysisCandidate
from papermatrix.domain.paper import AnalysisItem, AnalysisItemKind
from papermatrix.domain.paper_content import EvidenceReference

_HEADING = re.compile(r"^(#{2,4})\s+(.+?)\s*$")
_LIST_ITEM = re.compile(r"^\s*(?:[-*]\s*|\d+\.(?:\s+|$))(.*?)\s*$")
_NUMBERING = re.compile(r"^\d+(?:\.\d+)*(?:[.、]\s*|\s+)?")
_SECTION_NUMBER = re.compile(r"^(\d+)(?:[.、]\s*|\s+)")
_ITEM_ANCHOR = re.compile(r"<!--\s*papermatrix:item:([0-9a-fA-F-]{36})\s*-->")
_ATTRIBUTE_KEY = re.compile(r"^[^:\uff1a\n]{1,60}$")
_EVIDENCE_CODE = re.compile(r"\bE-\d{3,}\b", re.IGNORECASE)
_PLACEHOLDER_VALUES = {
    "",
    "______",
    "类别 a",
    "类别 b",
    "类别 c",
    "模块 a",
    "模块 b",
    "模块 c",
    "主实验",
    "消融实验",
    "泛化实验",
    "效率/成本实验",
    "输入 → 模块 a → 模块 b → 模块 c → 输出",
    "记录删除后可能导致方案失效或实验不可复现的细节。",
    "公开 / 未公开 / 部分公开",
    "公开 / 未公开",
    "开源 / 闭源",
    "可构建 / 难构建",
    "低 / 中 / 高",
    "待补充",
    "待填写",
    "待查询",
    "待核对",
    "待回看 pdf",
}
_PLACEHOLDER_PREFIXES = ("待补充", "待填写", "待查询", "待核对", "待回看")


@dataclass(frozen=True)
class _Block:
    heading: str
    level: int
    start: int
    end: int
    lines: list[str]
    section_key: str
    section_title: str
    anchor_id: UUID | None


def parse_note_candidates(
    paper_id: UUID,
    markdown: str,
    existing_items: list[AnalysisItem],
) -> list[NoteAnalysisCandidate]:
    blocks = _blocks(markdown)
    evidence = _parse_evidence(blocks, paper_id)
    candidates: list[NoteAnalysisCandidate] = []
    for block in blocks:
        if block.level < 3:
            continue
        if block.level == 3 and _is_representative_work_heading(block.heading):
            continue
        kind = (
            "related_work"
            if _is_representative_work_child(block, blocks)
            else _kind_for_heading(block.heading)
        )
        if kind is None:
            continue
        candidate = _block_candidate(
            paper_id,
            block,
            kind,
            existing_items,
            allow_empty=block.anchor_id is not None and _is_repeatable_item_block(block, blocks),
        )
        if candidate is not None:
            candidates.append(candidate)

    section_counts: dict[str, int] = {}
    ordered: list[NoteAnalysisCandidate] = []
    for candidate in sorted(candidates, key=lambda item: item.source_line_start):
        section_counts[candidate.section_key] = section_counts.get(candidate.section_key, 0) + 1
        ordered.append(
            candidate.model_copy(update={"section_order": section_counts[candidate.section_key]})
        )
    candidates = [_attach_evidence(candidate, evidence) for candidate in ordered]
    fingerprinted = [
        candidate.model_copy(
            update={"source_fingerprint": _source_fingerprint(markdown, candidate)}
        )
        for candidate in candidates
    ]
    return [_mark_duplicate(candidate, existing_items) for candidate in fingerprinted]


def _blocks(markdown: str) -> list[_Block]:
    lines = markdown.splitlines()
    headings: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines):
        match = _HEADING.match(line)
        if match:
            headings.append((index, len(match.group(1)), match.group(2).strip()))
    blocks: list[_Block] = []
    current_section_key = "unsectioned"
    current_section_title = "未分节"
    for position, (index, level, heading) in enumerate(headings):
        if level == 2:
            current_section_key, current_section_title = _section_identity(heading)
        if _is_representative_work_heading(heading):
            end = next(
                (
                    next_index
                    for next_index, next_level, _ in headings[position + 1 :]
                    if next_level <= level
                ),
                len(lines),
            )
        else:
            end = headings[position + 1][0] if position + 1 < len(headings) else len(lines)
        if end > index + 1 and _ITEM_ANCHOR.fullmatch(lines[end - 1].strip()):
            end -= 1
        blocks.append(
            _Block(
                heading=heading,
                level=level,
                start=index + 1,
                end=max(index + 1, end),
                lines=lines[index + 1 : end],
                section_key=current_section_key,
                section_title=current_section_title,
                anchor_id=_anchor_from_line(lines[index - 1]) if index > 0 else None,
            )
        )
    return blocks


def _kind_for_heading(heading: str) -> AnalysisItemKind | None:
    cleaned = _NUMBERING.sub("", heading).strip()
    rules: list[tuple[tuple[str, ...], AnalysisItemKind]] = [
        (("研究背景", "为什么重要", "问题的重要性"), "background"),
        (("具体问题", "问题形式化"), "research_problem"),
        (("实际应用场景",), "scenario"),
        (("代表性顶会顶刊文献",), "related_work"),
        (("现有方法分类", "本文切入点", "核心思路", "整体框架", "大致流程"), "method"),
        (("框架组成",), "method_component"),
        (
            (
                "输入与预处理",
                "任务规划",
                "知识检索或 RAG",
                "Agent / 模型决策",
                "工具调用",
                "环境反馈处理",
                "结果验证",
                "失败恢复与重新规划",
                "输出结果",
                "具体流程和技术细节",
            ),
            "method_component",
        ),
        (("核心区别", "关键实现细节"), "mechanism"),
        (("现有方案的共同不足", "挑战"), "challenge"),
        (("创新点",), "innovation"),
        (("附加贡献", "论文优点及证据"), "contribution"),
        (
            (
                "实验研究问题",
                "数据集与实验环境",
                "对比基线",
                "评价指标",
                "开源情况",
            ),
            "experiment",
        ),
        (("主要实验结果", "失败案例"), "finding"),
        (("作者承认的局限",), "author_limitation"),
        (("我发现的局限",), "reviewer_limitation"),
        (("结论成立的条件", "可靠性检查"), "condition"),
    ]
    for needles, kind in rules:
        if any(needle in cleaned for needle in needles):
            return kind
    return None


def _block_candidate(
    paper_id: UUID,
    block: _Block,
    kind: AnalysisItemKind,
    existing_items: list[AnalysisItem],
    *,
    allow_empty: bool = False,
) -> NoteAnalysisCandidate | None:
    nested_attributes = _nested_heading_attributes(block.lines)
    attributes: dict[str, str] = {}
    prose: list[str] = []
    for raw in block.lines:
        line = raw.strip()
        if (
            not line
            or line == "---"
            or line.startswith("|")
            or line.startswith("#### ")
            or _ITEM_ANCHOR.fullmatch(line)
        ):
            continue
        if nested_attributes:
            continue
        match = _LIST_ITEM.match(line)
        value = match.group(1).strip() if match else line
        if not _meaningful(value):
            continue
        attribute = _attribute(value)
        if attribute is not None:
            key, content = attribute
            if _meaningful(content):
                attributes[key] = content
            continue
        prose.append(value)
    attributes.update(nested_attributes)
    attributes.update(_table_attributes(block.lines))
    if not attributes and not prose and not allow_empty:
        return None
    heading = _NUMBERING.sub("", block.heading).strip()
    title = _repeatable_item_title(heading)
    if re.fullmatch(r"(挑战|创新点)\s*\d+", heading) and prose:
        title = prose[0][:300]
    summary = "\n".join(prose)
    return _candidate(
        paper_id,
        kind,
        title,
        summary,
        attributes,
        block.heading,
        block.section_key,
        block.section_title,
        block.anchor_id,
        block.start,
        block.end,
        _superseded_item_ids(block, existing_items),
    )


_REPEATABLE_HEADING_PREFIXES = (
    "挑战",
    "创新点",
)


def _repeatable_item_title(heading: str) -> str:
    for prefix in _REPEATABLE_HEADING_PREFIXES:
        for separator in (":", "\uff1a"):
            marker = f"{prefix}{separator}"
            if heading.startswith(marker) and heading[len(marker) :].strip():
                return heading[len(marker) :].strip()
    return heading


def _is_repeatable_item_block(block: _Block, blocks: list[_Block]) -> bool:
    if _is_representative_work_child(block, blocks):
        return True
    heading = _NUMBERING.sub("", block.heading).strip()
    return any(
        heading.startswith((f"{prefix}:", f"{prefix}\uff1a"))
        for prefix in _REPEATABLE_HEADING_PREFIXES
    )


def _table_attributes(lines: list[str]) -> dict[str, str]:
    rows = _table_rows(lines)
    if len(rows) < 2:
        return {}
    headers = rows[0][1]
    result: dict[str, str] = {}
    for _, values in rows[1:]:
        _, title = _strip_anchor(values[0] if values else "")
        details = {
            headers[index]: value
            for index, value in enumerate(values[1:], start=1)
            if index < len(headers) and _meaningful(value)
        }
        if not title.strip() or not details:
            continue
        key = title
        suffix = 2
        while key in result:
            key = f"{title} ({suffix})"
            suffix += 1
        result[key] = "; ".join(f"{header}: {value}" for header, value in details.items())
    return result


def _nested_heading_attributes(lines: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    title: str | None = None
    values: list[str] = []

    def flush() -> None:
        if title is None:
            return
        meaningful = [value for value in values if _meaningful(value)]
        if meaningful:
            result[title] = "; ".join(meaningful)

    for raw in lines:
        line = raw.strip()
        heading = _HEADING.match(line)
        if heading and len(heading.group(1)) == 4:
            flush()
            title = _NUMBERING.sub("", heading.group(2)).strip()
            values = []
            continue
        if title is None or not line or _ITEM_ANCHOR.fullmatch(line):
            continue
        match = _LIST_ITEM.match(line)
        value = match.group(1).strip() if match else line
        separator = "\uff1a" if "\uff1a" in value else ":" if ":" in value else None
        if separator is not None:
            key, content = value.split(separator, 1)
            if not _meaningful(content):
                continue
            value = f"{key.strip()}{separator}{content.strip()}"
        if _meaningful(value):
            values.append(value)
    flush()
    return result


def _is_representative_work_heading(heading: str) -> bool:
    return "代表性顶会顶刊文献" in _NUMBERING.sub("", heading).strip()


def _is_representative_work_child(block: _Block, blocks: list[_Block]) -> bool:
    if block.level != 4:
        return False
    parent = next(
        (
            candidate
            for candidate in reversed(blocks)
            if candidate.start < block.start and candidate.level == 3
        ),
        None,
    )
    return parent is not None and _is_representative_work_heading(parent.heading)


def _superseded_item_ids(
    block: _Block,
    existing_items: list[AnalysisItem],
) -> list[UUID]:
    existing_ids = {item.item_id for item in existing_items}
    ids: list[UUID] = []
    for line in block.lines:
        for match in _ITEM_ANCHOR.finditer(line):
            item_id = UUID(match.group(1))
            if item_id in existing_ids and item_id != block.anchor_id and item_id not in ids:
                ids.append(item_id)
    return ids


def _parse_evidence(blocks: list[_Block], paper_id: UUID) -> list[EvidenceReference]:
    block = next(
        (
            item
            for item in blocks
            if any(
                title in item.heading for title in ("关键引用、页码与证据", "关键证据与页码定位")
            )
        ),
        None,
    )
    if block is None:
        return []
    rows = _table_rows(block.lines)
    result: list[EvidenceReference] = []
    for _, values in rows[1:]:
        padded = [*values, *[""] * (7 - len(values))]
        evidence_code, _evidence_type, claim, page, pdf_page, figure_table, note = padded[:7]
        if not _meaningful(claim):
            continue
        normalized_code = evidence_code.strip().upper()
        if _EVIDENCE_CODE.fullmatch(normalized_code) is None:
            continue
        try:
            page_index = int(pdf_page) if _meaningful(pdf_page) else None
        except ValueError:
            page_index = None
        figure = (
            figure_table
            if _meaningful(figure_table) and figure_table.lower().startswith(("fig", "图"))
            else None
        )
        table = (
            figure_table
            if _meaningful(figure_table) and figure_table.lower().startswith(("table", "表"))
            else None
        )
        evidence_id = uuid5(
            NAMESPACE_URL,
            f"papermatrix:evidence:{paper_id}:{normalized_code}",
        )
        result.append(
            EvidenceReference(
                evidence_id=evidence_id,
                evidence_code=normalized_code,
                paper_id=paper_id,
                page_label=page if _meaningful(page) else None,
                pdf_page_index=page_index,
                section=note if _meaningful(note) else None,
                figure=figure,
                table=table,
                locator_note=claim,
            )
        )
    return result


def _attach_evidence(
    candidate: NoteAnalysisCandidate,
    evidence: list[EvidenceReference],
) -> NoteAnalysisCandidate:
    referenced_codes = {
        code.upper()
        for value in [candidate.summary, *candidate.attributes.values()]
        for code in _EVIDENCE_CODE.findall(value)
    }
    matches = [
        item
        for item in evidence
        if item.evidence_code is not None and item.evidence_code.upper() in referenced_codes
    ]
    return candidate.model_copy(update={"evidence_refs": matches})


def _candidate(
    paper_id: UUID,
    kind: AnalysisItemKind,
    title: str,
    summary: str,
    attributes: dict[str, str],
    source_section: str,
    section_key: str,
    section_title: str,
    explicit_id: UUID | None,
    line_start: int,
    line_end: int,
    superseded_item_ids: list[UUID] | None = None,
) -> NoteAnalysisCandidate:
    candidate_id = explicit_id or uuid5(
        NAMESPACE_URL,
        f"papermatrix:candidate:{paper_id}:{kind}:{source_section}:{title}:{summary}",
    )
    return NoteAnalysisCandidate(
        candidate_id=candidate_id,
        kind=kind,
        title=title[:300],
        summary=summary,
        attributes=attributes,
        section_key=section_key,
        section_title=section_title,
        section_order=1,
        source_anchor=f"papermatrix:item:{candidate_id}",
        source_fingerprint="0" * 64,
        source_section=source_section,
        source_line_start=line_start,
        source_line_end=max(line_start, line_end),
        superseded_item_ids=superseded_item_ids or [],
    )


def _table_rows(lines: list[str]) -> list[tuple[int, list[str]]]:
    rows: list[tuple[int, list[str]]] = []
    for index, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line.startswith("|") or not line.endswith("|"):
            continue
        values = [cell.strip() for cell in line.strip("|").split("|")]
        if values and all(re.fullmatch(r":?-{3,}:?", value) for value in values):
            continue
        rows.append((index, values))
    return rows


def _meaningful(value: str) -> bool:
    normalized = value.strip().casefold()
    if normalized in _PLACEHOLDER_VALUES:
        return False
    if normalized.startswith(_PLACEHOLDER_PREFIXES):
        return False
    return bool(normalized.strip("_ -\uff1a:"))


def _attribute(value: str) -> tuple[str, str] | None:
    """Return a real short key/value field, never prose containing an URL."""
    separator = "\uff1a" if "\uff1a" in value else ":" if ":" in value else None
    if separator is None or value.startswith(("http://", "https://")):
        return None
    key, content = value.split(separator, 1)
    key = key.strip()
    content = content.strip()
    if not _ATTRIBUTE_KEY.fullmatch(key) or any(
        marker in key for marker in ("\u3002", "\uff01", "\uff1f", "(", ")", "[", "]")
    ):
        return None
    return key, content


def add_item_anchors(
    markdown: str,
    candidates: list[NoteAnalysisCandidate],
) -> str:
    """Insert invisible stable markers without reformatting unrelated Markdown."""
    lines = markdown.splitlines()
    for candidate in sorted(candidates, key=lambda item: item.source_line_start, reverse=True):
        marker = f"<!-- {candidate.source_anchor} -->"
        index = candidate.source_line_start - 1
        if index < 0 or index >= len(lines):
            continue
        if _ITEM_ANCHOR.search(lines[index]):
            continue
        if lines[index].lstrip().startswith("|"):
            pipe = lines[index].find("|")
            lines[index] = f"{lines[index][: pipe + 1]} {marker}{lines[index][pipe + 1 :]}"
            continue
        if index > 0 and _ITEM_ANCHOR.fullmatch(lines[index - 1].strip()):
            continue
        lines.insert(index, marker)
    suffix = "\n" if markdown.endswith("\n") else ""
    return "\n".join(lines) + suffix


def remove_item_anchors(markdown: str, item_ids: set[UUID]) -> str:
    """Remove legacy heading or table-row markers selected for explicit consolidation."""
    if not item_ids:
        return markdown
    markers = {f"papermatrix:item:{item_id}" for item_id in item_ids}
    lines: list[str] = []
    for raw in markdown.splitlines():
        matches = list(_ITEM_ANCHOR.finditer(raw))
        if not matches:
            lines.append(raw)
            continue
        updated = raw
        for match in reversed(matches):
            if f"papermatrix:item:{match.group(1)}" in markers:
                updated = f"{updated[: match.start()]}{updated[match.end() :]}"
        if updated.strip():
            lines.append(updated)
    suffix = "\n" if markdown.endswith("\n") else ""
    return "\n".join(lines) + suffix


def remove_note_item_fragments(markdown: str, item_ids: set[UUID]) -> str:
    """Remove anchored heading blocks or table rows selected by the user."""
    if not item_ids:
        return markdown
    lines = markdown.splitlines()
    ranges: list[tuple[int, int]] = []
    for marker_index, line in enumerate(lines):
        match = _ITEM_ANCHOR.search(line)
        if match is None or UUID(match.group(1)) not in item_ids:
            continue
        if line.lstrip().startswith("|"):
            ranges.append((marker_index, marker_index + 1))
            continue
        heading_index = marker_index + 1
        if heading_index >= len(lines):
            ranges.append((marker_index, marker_index + 1))
            continue
        heading = _HEADING.match(lines[heading_index])
        if heading is None:
            ranges.append((marker_index, marker_index + 1))
            continue
        level = len(heading.group(1))
        end = len(lines)
        for index in range(heading_index + 1, len(lines)):
            next_heading = _HEADING.match(lines[index])
            if next_heading and len(next_heading.group(1)) <= level:
                end = (
                    index - 1
                    if index > heading_index and _ITEM_ANCHOR.fullmatch(lines[index - 1].strip())
                    else index
                )
                break
        ranges.append((marker_index, end))
    for start, end in reversed(ranges):
        del lines[start:end]
    suffix = "\n" if markdown.endswith("\n") else ""
    return "\n".join(lines) + suffix


def _section_identity(heading: str) -> tuple[str, str]:
    match = _SECTION_NUMBER.match(heading.strip())
    if match is None:
        return "unsectioned", heading.strip()
    return f"section-{match.group(1)}", heading.strip()


def _anchor_from_line(line: str) -> UUID | None:
    match = _ITEM_ANCHOR.fullmatch(line.strip())
    return UUID(match.group(1)) if match else None


def _strip_anchor(value: str) -> tuple[UUID | None, str]:
    match = _ITEM_ANCHOR.search(value)
    if match is None:
        return None, value
    return UUID(match.group(1)), _ITEM_ANCHOR.sub("", value).strip()


def _mark_duplicate(
    candidate: NoteAnalysisCandidate,
    existing_items: list[AnalysisItem],
) -> NoteAnalysisCandidate:
    duplicate = next(
        (
            item
            for item in existing_items
            if item.item_id == candidate.candidate_id
            or (
                item.kind == candidate.kind
                and _normalize(item.title) == _normalize(candidate.title)
                and _normalize(item.summary) == _normalize(candidate.summary)
            )
        ),
        None,
    )
    if duplicate is None:
        return candidate
    if duplicate.item_id != candidate.candidate_id:
        return candidate.model_copy(
            update={
                "duplicate_item_id": duplicate.item_id,
                "sync_status": "unchanged",
            }
        )
    status = (
        "unchanged" if duplicate.source_fingerprint == candidate.source_fingerprint else "modified"
    )
    return candidate.model_copy(
        update={"duplicate_item_id": duplicate.item_id, "sync_status": status}
    )


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())


def note_item_fragment(markdown: str, candidate: NoteAnalysisCandidate) -> str:
    """Return the exact editable Markdown fragment without its stable marker."""
    lines = markdown.splitlines()
    start = candidate.source_line_start - 1
    end = candidate.source_line_end
    if start < 0 or end > len(lines):
        return ""
    fragment = "\n".join(lines[start:end])
    return _ITEM_ANCHOR.sub("", fragment).strip()


def replace_note_item_fragment(
    markdown: str,
    item_id: UUID,
    replacement: str,
) -> str:
    """Replace one anchored fragment while preserving unrelated Markdown."""
    marker = f"<!-- papermatrix:item:{item_id} -->"
    lines = markdown.splitlines()
    marker_index = next((index for index, line in enumerate(lines) if marker in line), None)
    if marker_index is None:
        return markdown

    if lines[marker_index].lstrip().startswith("|"):
        if "\n" in replacement.strip() or not replacement.strip().startswith("|"):
            return markdown
        cleaned = _ITEM_ANCHOR.sub("", replacement.strip())
        pipe = cleaned.find("|")
        lines[marker_index] = f"{cleaned[: pipe + 1]} {marker}{cleaned[pipe + 1 :]}"
    else:
        heading_index = marker_index + 1
        if heading_index >= len(lines):
            return markdown
        heading = _HEADING.match(lines[heading_index])
        replacement_lines = replacement.strip().splitlines()
        replacement_heading = _HEADING.match(replacement_lines[0]) if replacement_lines else None
        if heading is None or replacement_heading is None:
            return markdown
        end = len(lines)
        heading_level = len(heading.group(1))
        for index in range(heading_index + 1, len(lines)):
            match = _HEADING.match(lines[index])
            if match and len(match.group(1)) <= heading_level:
                end = (
                    index - 1
                    if index > heading_index and _ITEM_ANCHOR.fullmatch(lines[index - 1].strip())
                    else index
                )
                break
        lines[heading_index:end] = replacement_lines

    suffix = "\n" if markdown.endswith("\n") else ""
    return "\n".join(lines) + suffix


def append_note_item_fragment(
    markdown: str,
    *,
    item_id: UUID,
    chapter: int,
    label: str,
    title: str,
    body: str,
) -> str:
    """Append one anchored template item to its numbered chapter."""
    lines = markdown.splitlines()
    chapter_heading = re.compile(rf"^##\s+{chapter}(?:[.、]\s*|\s+)")
    start = next(
        (index for index, line in enumerate(lines) if chapter_heading.match(line.strip())),
        None,
    )
    if start is None:
        return markdown
    end = next(
        (
            index
            for index in range(start + 1, len(lines))
            if re.match(r"^##\s+\d+(?:[.、]\s*|\s+)", lines[index].strip())
        ),
        len(lines),
    )
    insertion = end
    while insertion > start + 1 and not lines[insertion - 1].strip():
        insertion -= 1
    if insertion > start + 1 and lines[insertion - 1].strip() == "---":
        insertion -= 1
        while insertion > start + 1 and not lines[insertion - 1].strip():
            insertion -= 1
    safe_title = " ".join(title.split())
    fragment = [
        "",
        f"<!-- papermatrix:item:{item_id} -->",
        f"### {label}: {safe_title}",
        "",
        body.strip(),
        "",
    ]
    lines[insertion:insertion] = fragment
    suffix = "\n" if markdown.endswith("\n") else ""
    return "\n".join(lines) + suffix


def note_template_slot_fragment(
    markdown: str,
    *,
    heading: str,
    heading_level: int,
) -> str:
    """Return only the editable body belonging to one fixed template heading."""
    lines = markdown.splitlines()
    location = _heading_block_range(lines, heading=heading, heading_level=heading_level)
    if location is None:
        return ""
    heading_index, end = location
    body, _ = _split_template_tail(lines[heading_index + 1 : end])
    return "\n".join(body).strip()


def replace_note_template_slot(
    markdown: str,
    *,
    heading: str,
    heading_level: int,
    item_id: UUID,
    body: str,
) -> str:
    """Update a fixed template slot without moving or renaming its heading."""
    lines = markdown.splitlines()
    location = _heading_block_range(lines, heading=heading, heading_level=heading_level)
    if location is None:
        return markdown
    heading_index, end = location
    marker = f"<!-- papermatrix:item:{item_id} -->"
    if heading_index == 0 or lines[heading_index - 1].strip() != marker:
        lines.insert(heading_index, marker)
        heading_index += 1
        end += 1
    current_body, preserved_tail = _split_template_tail(lines[heading_index + 1 : end])
    del current_body
    replacement = body.strip().splitlines() if body.strip() else []
    formatted_body = ["", *replacement, ""] if replacement else [""]
    lines[heading_index + 1 : end] = [*formatted_body, *preserved_tail]
    suffix = "\n" if markdown.endswith("\n") else ""
    return "\n".join(lines) + suffix


def append_repeatable_note_item(
    markdown: str,
    *,
    parent_heading: str,
    parent_heading_level: int,
    item_id: UUID,
    title: str,
    body: str,
    child_heading_prefix: str = "",
    insert_before_heading: str | None = None,
) -> str:
    """Insert one independently addressable child at its semantic template position."""
    lines = markdown.splitlines()
    location = _heading_block_range(
        lines,
        heading=parent_heading,
        heading_level=parent_heading_level,
    )
    if location is None:
        return markdown
    parent_index, end = location
    if insert_before_heading:
        insertion = next(
            (
                index
                for index in range(parent_index + 1, end)
                if (match := _HEADING.match(lines[index]))
                and len(match.group(1)) == parent_heading_level + 1
                and match.group(2).strip() == insert_before_heading
            ),
            end,
        )
        if insertion > parent_index + 1 and _ITEM_ANCHOR.fullmatch(lines[insertion - 1].strip()):
            insertion -= 1
    else:
        insertion = end
        while insertion > parent_index + 1 and not lines[insertion - 1].strip():
            insertion -= 1
        if insertion > parent_index + 1 and lines[insertion - 1].strip() == "---":
            insertion -= 1
            while insertion > parent_index + 1 and not lines[insertion - 1].strip():
                insertion -= 1
    safe_title = " ".join(title.split())
    heading_text = f"{child_heading_prefix}: {safe_title}" if child_heading_prefix else safe_title
    child_heading_level = parent_heading_level + 1
    fragment = [
        "",
        f"<!-- papermatrix:item:{item_id} -->",
        f"{'#' * child_heading_level} {heading_text}",
        "",
        body.strip(),
        "",
    ]
    lines[insertion:insertion] = fragment
    suffix = "\n" if markdown.endswith("\n") else ""
    return "\n".join(lines) + suffix


def _heading_block_range(
    lines: list[str],
    *,
    heading: str,
    heading_level: int,
) -> tuple[int, int] | None:
    heading_index = next(
        (
            index
            for index, line in enumerate(lines)
            if (match := _HEADING.match(line))
            and len(match.group(1)) == heading_level
            and match.group(2).strip() == heading
        ),
        None,
    )
    if heading_index is None:
        return None
    end = len(lines)
    for index in range(heading_index + 1, len(lines)):
        match = _HEADING.match(lines[index])
        if match and len(match.group(1)) <= heading_level:
            end = (
                index - 1
                if index > heading_index and _ITEM_ANCHOR.fullmatch(lines[index - 1].strip())
                else index
            )
            break
    return heading_index, end


def _split_template_tail(lines: list[str]) -> tuple[list[str], list[str]]:
    """Keep a chapter's trailing horizontal rule outside the editable slot."""
    last_content = len(lines) - 1
    while last_content >= 0 and not lines[last_content].strip():
        last_content -= 1
    if last_content < 0 or lines[last_content].strip() != "---":
        return lines, []
    tail_start = last_content
    while tail_start > 0 and not lines[tail_start - 1].strip():
        tail_start -= 1
    return lines[:tail_start], lines[tail_start:]


def append_evidence_row(
    markdown: str,
    evidence: EvidenceReference,
    *,
    evidence_type: str = "",
) -> str:
    """Append one evidence record to the chapter 11 Markdown table."""

    def cell(value: object | None) -> str:
        if value is None:
            return ""
        return " ".join(str(value).replace("|", r"\|").split())

    lines = markdown.splitlines()
    section = next(
        (
            index
            for index, line in enumerate(lines)
            if re.match(r"^##\s+11(?:[.、]\s*|\s+)", line.strip())
        ),
        None,
    )
    figure_table = evidence.figure or evidence.table or ""
    row = (
        f"| {cell(evidence.evidence_code)} | {cell(evidence_type)} | "
        f"{cell(evidence.locator_note)} | {cell(evidence.page_label)} | "
        f"{cell(evidence.pdf_page_index)} | {cell(figure_table)} | "
        f"{cell(evidence.section)} |"
    )
    if section is None:
        addition = [
            "",
            "---",
            "",
            "## 11. 关键证据与页码定位",
            "",
            "| 证据 ID | 类型 | 观点或证据 | 印刷页码 | PDF 页序号 | 图/表 | 备注 |",
            "|---|---|---|---|---:|---|---|",
            row,
            "",
        ]
        lines.extend(addition)
    else:
        table_start = next(
            (
                index
                for index in range(section + 1, len(lines))
                if lines[index].lstrip().startswith("|")
            ),
            None,
        )
        if table_start is None:
            lines[section + 1 : section + 1] = [
                "",
                "| 证据 ID | 类型 | 观点或证据 | 印刷页码 | PDF 页序号 | 图/表 | 备注 |",
                "|---|---|---|---|---:|---|---|",
                row,
            ]
        else:
            insertion = table_start
            while insertion < len(lines) and lines[insertion].lstrip().startswith("|"):
                insertion += 1
            lines.insert(insertion, row)
    suffix = "\n" if markdown.endswith("\n") else ""
    return "\n".join(lines) + suffix


def append_item_evidence_reference(
    markdown: str,
    candidate: NoteAnalysisCandidate,
    evidence_code: str,
) -> str:
    """Add an explicit evidence code reference to an anchored item."""
    fragment = note_item_fragment(markdown, candidate)
    if evidence_code.upper() in {code.upper() for code in _EVIDENCE_CODE.findall(fragment)}:
        return markdown
    replacement = f"{fragment.rstrip()}\n\n- 证据: {evidence_code}"
    return replace_note_item_fragment(markdown, candidate.candidate_id, replacement)


def _source_fingerprint(markdown: str, candidate: NoteAnalysisCandidate) -> str:
    fragment = note_item_fragment(markdown, candidate)
    return sha256(fragment.encode("utf-8")).hexdigest()
