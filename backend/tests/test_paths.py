from pathlib import Path

import pytest

from papermatrix.core.errors import (
    InvalidPathError,
    PathOutsideAllowedRootsError,
    SymlinkEscapeError,
)
from papermatrix.core.paths import PathPolicy


def test_allows_pdf_inside_configured_root(tmp_path):
    root = tmp_path / "papers"
    root.mkdir()
    paper = root / "paper.pdf"
    paper.write_bytes(b"%PDF-1.4\n")

    assert PathPolicy((root,)).validate_pdf(paper) == paper.resolve()


def test_rejects_relative_path(tmp_path):
    with pytest.raises(InvalidPathError):
        PathPolicy((tmp_path,)).validate_pdf(Path("paper.pdf"))


def test_rejects_path_outside_configured_root(tmp_path):
    root = tmp_path / "papers"
    root.mkdir()
    outside = tmp_path / "private.pdf"
    outside.write_bytes(b"%PDF-1.4\n")

    with pytest.raises(PathOutsideAllowedRootsError):
        PathPolicy((root,)).validate_pdf(outside)


def test_rejects_symlink_escape(tmp_path):
    root = tmp_path / "papers"
    root.mkdir()
    outside = tmp_path / "private.pdf"
    outside.write_bytes(b"%PDF-1.4\n")
    link = root / "linked.pdf"
    link.symlink_to(outside)

    with pytest.raises(SymlinkEscapeError):
        PathPolicy((root,)).validate_pdf(link)
