from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
import yaml

from papermatrix.core import atomic_io
from papermatrix.core.errors import RevisionConflictError


def validate_revision(data):
    assert isinstance(data.get("revision"), int)


def test_atomic_write_replaces_valid_file(tmp_path):
    target = tmp_path / "resource.yaml"
    atomic_io.atomic_write_yaml(target, {"revision": 1}, validator=validate_revision)

    atomic_io.atomic_write_yaml(
        target,
        {"revision": 2},
        validator=validate_revision,
        expected_revision=1,
    )

    assert yaml.safe_load(target.read_text()) == {"revision": 2}


def test_revision_conflict_preserves_current_file(tmp_path):
    target = tmp_path / "resource.yaml"
    atomic_io.atomic_write_yaml(target, {"revision": 2}, validator=validate_revision)

    with pytest.raises(RevisionConflictError):
        atomic_io.atomic_write_yaml(
            target,
            {"revision": 3},
            validator=validate_revision,
            expected_revision=1,
        )

    assert yaml.safe_load(target.read_text()) == {"revision": 2}


def test_replace_failure_preserves_old_file_and_cleans_temp_files(tmp_path, monkeypatch):
    target = tmp_path / "resource.yaml"
    target.write_text("revision: 1\n", encoding="utf-8")

    def fail_replace(source: Path, destination: Path) -> None:
        raise OSError("simulated interruption")

    monkeypatch.setattr(atomic_io.os, "replace", fail_replace)

    with pytest.raises(OSError, match="simulated interruption"):
        atomic_io.atomic_write_yaml(
            target,
            {"revision": 2},
            validator=validate_revision,
            expected_revision=1,
        )

    assert target.read_text(encoding="utf-8") == "revision: 1\n"
    assert not list(tmp_path.glob("*.tmp"))


def test_concurrent_revision_writes_allow_only_one_winner(tmp_path):
    target = tmp_path / "resource.yaml"
    atomic_io.atomic_write_yaml(target, {"revision": 1}, validator=validate_revision)

    def update(value):
        try:
            atomic_io.atomic_write_yaml(
                target,
                {"revision": 2, "writer": value},
                validator=validate_revision,
                expected_revision=1,
            )
        except RevisionConflictError:
            return "conflict"
        return "written"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(update, ("first", "second")))

    assert sorted(results) == ["conflict", "written"]
    assert yaml.safe_load(target.read_text())["revision"] == 2
