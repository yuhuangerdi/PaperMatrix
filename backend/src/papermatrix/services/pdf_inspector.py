"""Read-only PDF metadata inspection."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

from pypdf import PdfReader

from papermatrix.domain.paper import PaperSource


@dataclass(frozen=True)
class PdfMetadata:
    title: str | None
    authors: list[str]
    page_count: int | None
    readable: bool


def _read_metadata(stream: BinaryIO) -> PdfMetadata:
    try:
        reader = PdfReader(stream, strict=False)
        metadata = reader.metadata
        title = str(metadata.title).strip() if metadata and metadata.title else None
        raw_author = str(metadata.author).strip() if metadata and metadata.author else ""
        authors = [raw_author] if raw_author else []
        return PdfMetadata(
            title=title,
            authors=authors,
            page_count=len(reader.pages),
            readable=True,
        )
    except Exception:
        return PdfMetadata(title=None, authors=[], page_count=None, readable=False)


def inspect_path(path: Path, *, strict_hashing: bool) -> tuple[PaperSource, PdfMetadata]:
    stat = path.stat()
    sha256 = None
    if strict_hashing:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        sha256 = digest.hexdigest()
    with path.open("rb") as handle:
        metadata = _read_metadata(handle)
    source = PaperSource(
        path=str(path),
        path_mode="absolute",
        original_filename=path.name,
        size_bytes=stat.st_size,
        modified_at=datetime.fromtimestamp(stat.st_mtime, UTC),
        fingerprint=f"{stat.st_size}:{stat.st_mtime_ns}",
        sha256=sha256,
        page_count=metadata.page_count,
        status="available" if metadata.readable else "unreadable",
    )
    return source, metadata


def inspect_upload(filename: str, content: bytes) -> tuple[PaperSource, PdfMetadata]:
    metadata = _read_metadata(BytesIO(content))
    sha256 = hashlib.sha256(content).hexdigest()
    source = PaperSource(
        original_filename=Path(filename).name,
        size_bytes=len(content),
        fingerprint=f"sha256:{sha256}",
        sha256=sha256,
        page_count=metadata.page_count,
        status="unlinked",
    )
    return source, metadata
