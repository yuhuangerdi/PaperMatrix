from pathlib import Path

import pytest

from papermatrix.core.errors import SchemaValidationError
from papermatrix.core.schema_registry import SchemaRegistry


def test_workspace_schema_accepts_valid_data():
    registry = SchemaRegistry(Path(__file__).resolve().parents[2] / "contracts" / "schemas")
    registry.validate(
        "workspace",
        {
            "schema_version": 1,
            "workspace_id": "11111111-1111-4111-8111-111111111111",
            "name": "Workspace",
            "created_at": "2026-07-26T10:00:00Z",
            "updated_at": "2026-07-26T10:00:00Z",
            "revision": 1,
            "allowed_paper_roots": ["/papers"],
            "settings": {
                "language": "zh-CN",
                "default_export_format": "xlsx",
                "strict_hashing": False,
            },
        },
    )


def test_workspace_schema_rejects_unknown_version():
    registry = SchemaRegistry(Path(__file__).resolve().parents[2] / "contracts" / "schemas")

    with pytest.raises(SchemaValidationError):
        registry.validate("workspace", {"schema_version": 99})
