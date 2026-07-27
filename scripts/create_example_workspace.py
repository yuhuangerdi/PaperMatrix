"""Create an idempotent synthetic PaperMatrix workspace."""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from papermatrix.core.schema_registry import SchemaRegistry
from papermatrix.repositories.workspace_repository import WorkspaceRepository


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()

    destination = args.destination.resolve(strict=False)
    paper_root = destination / "sample-papers"
    paper_root.mkdir(parents=True, exist_ok=True)
    repository = WorkspaceRepository(
        destination,
        SchemaRegistry(ROOT / "contracts" / "schemas"),
    )
    workspace = repository.initialize("PaperMatrix 示例工作区", (paper_root,))
    reloaded = repository.load()
    if workspace != reloaded:
        raise RuntimeError("Workspace did not round-trip")
    print(f"Created workspace {workspace.workspace_id} at {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
