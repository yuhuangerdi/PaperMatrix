"""Validate PaperMatrix JSON specifications and basic repository invariants.

Run from the repository root:
    python scripts/validate_specs.py

PyYAML is optional; when installed, YAML and OpenAPI syntax are also checked.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORED_GENERATED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "coverage",
    "dist",
    "node_modules",
}


def main() -> int:
    failures: list[str] = []

    for path in sorted((ROOT / "contracts" / "schemas").glob("*.json")):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - validation script reports all files
            failures.append(f"JSON invalid: {path.relative_to(ROOT)}: {exc}")

    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        print("PyYAML not installed; skipped YAML syntax validation.")
    else:
        yaml_paths = [ROOT / "contracts" / "openapi.yaml"]
        yaml_paths.extend((ROOT / "examples").rglob("*.yaml"))
        for path in yaml_paths:
            try:
                yaml.safe_load(path.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                failures.append(f"YAML invalid: {path.relative_to(ROOT)}: {exc}")

    required = [
        ".codex-prompts/prompt.md",
        "AGENTS.md",
        ".codex-prompts/PLANS.md",
        ".codex-prompts/DESIGN.md",
        "docs/01-PRD.md",
        "docs/05-filesystem-data-model.md",
        "docs/12-acceptance-criteria.md",
        "contracts/openapi.yaml",
        "templates/PaperMatrix_文献整理模板.xlsx",
    ]
    for relative in required:
        if not (ROOT / relative).exists():
            failures.append(f"Missing required file: {relative}")

    forbidden_suffixes = {".db", ".sqlite", ".sqlite3"}
    for path in ROOT.rglob("*"):
        relative_path = path.relative_to(ROOT)
        if any(part in IGNORED_GENERATED_DIRS for part in relative_path.parts):
            continue
        if path.is_file() and path.suffix.lower() in forbidden_suffixes:
            failures.append(f"Forbidden database artifact: {path.relative_to(ROOT)}")

    if failures:
        print("Validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("PaperMatrix specification package is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
