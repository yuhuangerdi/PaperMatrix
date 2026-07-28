"""Pure, in-memory paper schema migrations."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5


def migrate_paper(data: dict[str, Any]) -> dict[str, Any]:
    version = data.get("schema_version")
    if version == 11:
        return data
    if version not in {1, 2, 3, 4, 5, 6, 7, 8, 9, 10}:
        return data

    migrated = dict(data)
    if version == 1:
        source = dict(migrated.get("source", {}))
        raw_path = source.get("path")
        source["original_filename"] = Path(raw_path).name if isinstance(raw_path, str) else None
        source.setdefault("sha256", None)
        migrated["source"] = source

    bibliography = dict(migrated.get("bibliography", {}))
    for field in ("doi", "arxiv_id", "code_url", "data_url"):
        bibliography.setdefault(field, None)
    bibliography.setdefault("affiliations", [])
    bibliography.setdefault("publication_date", None)
    bibliography.setdefault("citation_count", None)
    bibliography.setdefault("language", None)
    bibliography.setdefault("keywords", [])
    bibliography.setdefault("abstract_text", "")
    migrated["bibliography"] = bibliography

    organization = dict(migrated.get("organization", {}))
    organization.setdefault("group", None)
    organization.setdefault("reading_date", None)
    migrated["organization"] = organization

    structured_summary = dict(migrated.get("structured_summary", {}))
    structured_summary.setdefault("background", {})
    structured_summary.setdefault("related_work", {})
    structured_summary.setdefault("approach", {})
    structured_summary.setdefault("challenges", [])
    structured_summary.setdefault("innovations", [])
    structured_summary.setdefault("additional_contribution", {})
    structured_summary.setdefault("experiment", {})
    structured_summary.setdefault("evaluation", {})
    structured_summary.setdefault("evidence_catalog", [])
    structured_summary.setdefault("items", [])
    evidence_catalog = [
        {key: value for key, value in reference.items() if key != "source_item_id"}
        for reference in structured_summary["evidence_catalog"]
        if isinstance(reference, dict)
    ]
    known_evidence_ids = {
        str(reference.get("evidence_id"))
        for reference in evidence_catalog
        if isinstance(reference, dict) and reference.get("evidence_id")
    }
    migrated_items: list[dict[str, Any]] = []
    for index, raw_item in enumerate(structured_summary["items"], start=1):
        item = dict(raw_item)
        evidence_ids = list(item.get("evidence_ids", []))
        for evidence_index, raw_reference in enumerate(item.get("evidence_refs", []), start=1):
            reference = dict(raw_reference)
            reference.pop("source_item_id", None)
            evidence_id = str(
                reference.get("evidence_id")
                or uuid5(
                    NAMESPACE_URL,
                    f"papermatrix:legacy-evidence:{index}:{evidence_index}:{reference}",
                )
            )
            reference["evidence_id"] = evidence_id
            reference.setdefault("evidence_code", f"E-{len(evidence_catalog) + 1:03d}")
            if evidence_id not in known_evidence_ids:
                evidence_catalog.append(reference)
                known_evidence_ids.add(evidence_id)
            evidence_ids.append(evidence_id)
        item.pop("evidence_refs", None)
        migrated_items.append(
            {
                **item,
                "section_key": item.get("section_key"),
                "section_title": item.get("section_title"),
                "section_order": item.get("section_order"),
                "source_anchor": item.get("source_anchor"),
                "source_note_revision": item.get("source_note_revision"),
                "source_fingerprint": item.get("source_fingerprint"),
                "is_favorite": item.get("is_favorite", False),
                "display_label": item.get("display_label"),
                "evidence_ids": list(dict.fromkeys(evidence_ids)),
            }
        )
    structured_summary["items"] = migrated_items
    structured_summary["evidence_catalog"] = evidence_catalog
    migrated["structured_summary"] = structured_summary
    migrated["schema_version"] = 11
    return migrated
