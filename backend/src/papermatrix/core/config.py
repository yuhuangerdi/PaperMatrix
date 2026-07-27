"""Application configuration with local-only defaults."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator


class Settings(BaseModel):
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    workspace_root: Path = Path("./workspace")
    allowed_paper_roots: tuple[Path, ...] = ()
    log_level: str = "INFO"
    diagnostic_mode: bool = False
    max_scan_files: int = Field(default=1000, ge=1, le=10000)
    max_upload_bytes: int = Field(default=50 * 1024 * 1024, ge=1024)

    @field_validator("host")
    @classmethod
    def require_local_host(cls, value: str) -> str:
        if value not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("MVP backend must bind to localhost")
        return value

    @classmethod
    def from_environment(cls, local_config_path: Path | None = None) -> Settings:
        local_workspace_root: str | None = None
        if local_config_path is not None and local_config_path.is_file():
            parsed = yaml.safe_load(local_config_path.read_text(encoding="utf-8"))
            if isinstance(parsed, dict) and isinstance(parsed.get("workspace_root"), str):
                local_workspace_root = parsed["workspace_root"]
        workspace_root = Path(
            os.getenv("PAPERMATRIX_WORKSPACE_ROOT", local_workspace_root or "./workspace")
        )
        raw_roots = os.getenv("PAPERMATRIX_ALLOWED_ROOTS", "")
        roots = tuple(Path(item) for item in raw_roots.split(os.pathsep) if item.strip())
        return cls(
            host=os.getenv("PAPERMATRIX_HOST", "127.0.0.1"),
            port=int(os.getenv("PAPERMATRIX_PORT", "8000")),
            workspace_root=workspace_root,
            allowed_paper_roots=roots,
            log_level=os.getenv("PAPERMATRIX_LOG_LEVEL", "INFO"),
            diagnostic_mode=os.getenv("PAPERMATRIX_DIAGNOSTIC_MODE", "false").lower()
            in {"1", "true", "yes"},
            max_scan_files=int(os.getenv("PAPERMATRIX_MAX_SCAN_FILES", "1000")),
            max_upload_bytes=int(os.getenv("PAPERMATRIX_MAX_UPLOAD_BYTES", str(50 * 1024 * 1024))),
        )
