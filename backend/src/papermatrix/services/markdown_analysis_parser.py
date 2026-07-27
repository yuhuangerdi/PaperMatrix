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
_LIST_ITEM = re.compile(r"^\s*(?:[-*]|\d+\.)\s*(.*?)\s*$")
_NUMBERING = re.compile(r"^\d+(?:\.\d+)*(?:[.、]\s*|\s+)?")
_SECTION_NUMBER = re.compile(r"^(\d+)(?:[.、]\s*|\s+)")
_ITEM_ANCHOR = re.compile(r"<!--\s*papermatrix:item:([0-9a-fA-F-]{36})\s*-->")
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
}


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
        kind = _kind_for_heading(block.heading)
        if kind is None:
            continue
        if "框架组成" in block.heading or "主要实验结果" in block.heading:
            candidates.extend(_table_candidates(paper_id, block, kind))
            continue
        candidate = _block_candidate(paper_id, block, kind)
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
        end = len(lines)
        for next_index, next_level, _ in headings[position + 1 :]:
            if next_level <= level:
                end = next_index
                break
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
        (("具体问题", "问题形式化"), "research_problem"),
        (("实际应用场景",), "scenario"),
        (("核心思路", "整体框架"), "method"),
        (("框架组成",), "method_component"),
        (("核心区别", "关键实现细节"), "mechanism"),
        (("挑战",), "challenge"),
        (("创新点",), "innovation"),
        (("附加贡献",), "contribution"),
        (("实验研究问题", "数据集与实验环境", "对比基线", "评价指标"), "experiment"),
        (("主要实验结果", "失败案例"), "finding"),
        (("作者承认的局限",), "author_limitation"),
        (("我发现的局限",), "reviewer_limitation"),
        (("结论成立的条件",), "condition"),
    ]
    for needles, kind in rules:
        if any(needle in cleaned for needle in needles):
            return kind
    return None


def _block_candidate(
    paper_id: UUID,
    block: _Block,
    kind: AnalysisItemKind,
) -> NoteAnalysisCandidate | None:
    attributes: dict[str, str] = {}
    prose: list[str] = []
    for raw in block.lines:
        line = raw.strip()
        if not line or line == "---" or line.startswith("|") or _ITEM_ANCHOR.fullmatch(line):
            continue
        match = _LIST_ITEM.match(line)
        value = match.group(1).strip() if match else line
        if not _meaningful(value):
            continue
        if "\uff1a" in value:
            key, content = value.split("\uff1a", 1)
            if _meaningful(content):
                attributes[key.strip()] = content.strip()
            continue
        if ":" in value:
            key, content = value.split(":", 1)
            if _meaningful(content):
                attributes[key.strip()] = content.strip()
            continue
        prose.append(value)
    if not attributes and not prose:
        return None
    heading = _NUMBERING.sub("", block.heading).strip()
    title = heading
    if re.fullmatch(r"(挑战|创新点)\s*\d+", heading) and prose:
        title = prose[0][:300]
    summary_parts = [*prose, *[f"{key}: {value}" for key, value in attributes.items()]]
    summary = "\n".join(summary_parts)
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
    )


def _table_candidates(
    paper_id: UUID,
    block: _Block,
    kind: AnalysisItemKind,
) -> list[NoteAnalysisCandidate]:
    rows = _table_rows(block.lines)
    if len(rows) < 2:
        return []
    headers = rows[0][1]
    result: list[NoteAnalysisCandidate] = []
    for offset, values in rows[1:]:
        marker_id, title = _strip_anchor(values[0] if values else "")
        details = {
            headers[index]: value
            for index, value in enumerate(values[1:], start=1)
            if index < len(headers) and _meaningful(value)
        }
        if not title.strip() or (title.casefold() in _PLACEHOLDER_VALUES and not details):
            continue
        summary = "\n".join(f"{key}: {value}" for key, value in details.items())
        result.append(
            _candidate(
                paper_id,
                kind,
                title,
                summary,
                details,
                block.heading,
                block.section_key,
                block.section_title,
                marker_id,
                block.start + offset,
                block.start + offset,
            )
        )
    return result


def _parse_evidence(blocks: list[_Block], paper_id: UUID) -> list[tuple[str, EvidenceReference]]:
    block = next((item for item in blocks if "关键引用、页码与证据" in item.heading), None)
    if block is None:
        return []
    rows = _table_rows(block.lines)
    result: list[tuple[str, EvidenceReference]] = []
    for _, values in rows[1:]:
        padded = [*values, *[""] * (7 - len(values))]
        source_id, evidence_type, claim, page, pdf_page, figure_table, note = padded[:7]
        if not _meaningful(claim):
            continue
        try:
            page_index = int(pdf_page) if pdf_page.strip() else None
        except ValueError:
            page_index = None
        figure = figure_table if figure_table.lower().startswith(("fig", "图")) else None
        table = figure_table if figure_table.lower().startswith(("table", "表")) else None
        evidence_id = uuid5(
            NAMESPACE_URL,
            f"papermatrix:evidence:{paper_id}:{source_id}:{claim}:{page}:{pdf_page}",
        )
        result.append(
            (
                evidence_type,
                EvidenceReference(
                    evidence_id=evidence_id,
                    paper_id=paper_id,
                    page_label=page or None,
                    pdf_page_index=page_index,
                    figure=figure,
                    table=table,
                    locator_note=note or claim,
                    source_item_id=source_id or None,
                ),
            )
        )
    return result


def _attach_evidence(
    candidate: NoteAnalysisCandidate,
    evidence: list[tuple[str, EvidenceReference]],
) -> NoteAnalysisCandidate:
    kind_terms: dict[AnalysisItemKind, tuple[str, ...]] = {
        "research_problem": ("背景", "问题"),
        "method": ("方法",),
        "method_component": ("方法",),
        "mechanism": ("方法",),
        "challenge": ("挑战",),
        "innovation": ("创新",),
        "contribution": ("贡献",),
        "experiment": ("实验",),
        "finding": ("结果", "发现"),
        "author_limitation": ("局限",),
        "reviewer_limitation": ("局限",),
        "condition": ("条件",),
        "scenario": ("场景",),
    }
    matches = [
        item
        for evidence_type, item in evidence
        if any(term in evidence_type for term in kind_terms[candidate.kind])
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
    return bool(normalized.strip("_ -\uff1a:"))


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
        level = len(heading.group(1))
        end = len(lines)
        for index in range(heading_index + 1, len(lines)):
            match = _HEADING.match(lines[index])
            if match and len(match.group(1)) <= level:
                end = index
                break
        lines[heading_index:end] = replacement_lines

    suffix = "\n" if markdown.endswith("\n") else ""
    return "\n".join(lines) + suffix


def _source_fingerprint(markdown: str, candidate: NoteAnalysisCandidate) -> str:
    fragment = note_item_fragment(markdown, candidate)
    return sha256(fragment.encode("utf-8")).hexdigest()
