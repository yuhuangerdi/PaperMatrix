"""Pure, in-memory question schema migrations."""

from __future__ import annotations

from typing import Any


def migrate_questions(data: dict[str, Any]) -> dict[str, Any]:
    if data.get("schema_version") != 1:
        return data

    migrated = dict(data)
    migrated["questions"] = [
        {
            **question,
            "evidence": [
                {key: value for key, value in evidence.items() if key != "source_item_id"}
                for evidence in question.get("evidence", [])
                if isinstance(evidence, dict)
            ],
        }
        for question in data.get("questions", [])
        if isinstance(question, dict)
    ]
    migrated["schema_version"] = 2
    return migrated
