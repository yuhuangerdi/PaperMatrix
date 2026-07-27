"""Pure, in-memory paper schema migrations."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def migrate_paper(data: dict[str, Any]) -> dict[str, Any]:
    version = data.get("schema_version")
    if version == 6:
        return data
    if version not in {1, 2, 3, 4, 5}:
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
    structured_summary.setdefault("items", [])
    structured_summary["items"] = [
        {
            **item,
            "section_key": item.get("section_key"),
            "section_title": item.get("section_title"),
            "section_order": item.get("section_order"),
            "source_anchor": item.get("source_anchor"),
            "source_note_revision": item.get("source_note_revision"),
            "source_fingerprint": item.get("source_fingerprint"),
        }
        for item in structured_summary["items"]
    ]
    migrated["structured_summary"] = structured_summary
    migrated["schema_version"] = 6
    return migrated
