"""JSON Schema loading and validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from papermatrix.core.errors import SchemaValidationError


class SchemaRegistry:
    def __init__(self, schema_root: Path) -> None:
        self._schema_root = schema_root.resolve()
        self._validators: dict[str, Draft202012Validator] = {}

    def validate(self, schema_name: str, data: dict[str, Any]) -> None:
        validator = self._validators.get(schema_name)
        if validator is None:
            schema_path = self._schema_root / f"{schema_name}.schema.json"
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            validator = Draft202012Validator(schema)
            self._validators[schema_name] = validator

        errors = sorted(validator.iter_errors(data), key=lambda error: list(error.path))
        if errors:
            first = errors[0]
            location = ".".join(str(part) for part in first.path) or "<root>"
            raise SchemaValidationError(
                f"文件不符合 {schema_name} schema。",
                details={"field": location, "reason": first.message},
            )
