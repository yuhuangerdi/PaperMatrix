"""FastAPI application factory."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from papermatrix import __version__
from papermatrix.api.errors import papermatrix_error_handler
from papermatrix.api.v1.health import router as health_router
from papermatrix.api.v1.item_links import router as item_links_router
from papermatrix.api.v1.paper_content import router as paper_content_router
from papermatrix.api.v1.papers import router as papers_router
from papermatrix.api.v1.projects import router as projects_router
from papermatrix.api.v1.workspace import router as workspace_router
from papermatrix.core.config import Settings
from papermatrix.core.errors import PaperMatrixError
from papermatrix.core.logging import configure_logging
from papermatrix.core.schema_registry import SchemaRegistry
from papermatrix.repositories.local_config_repository import LocalConfigRepository
from papermatrix.services.item_link_service import ItemLinkService
from papermatrix.services.paper_content_service import PaperContentService
from papermatrix.services.paper_service import PaperService
from papermatrix.services.project_service import ProjectService
from papermatrix.services.workspace_service import WorkspaceService


def create_app(
    settings: Settings | None = None,
    *,
    schema_root: Path | None = None,
    local_config_path: Path | None = None,
) -> FastAPI:
    repository_root = Path(__file__).resolve().parents[3]
    config_path = local_config_path or Path(
        os.getenv(
            "PAPERMATRIX_LOCAL_CONFIG",
            str(repository_root / "papermatrix.local.yaml"),
        )
    )
    active_settings = settings or Settings.from_environment(config_path)
    configure_logging(active_settings.log_level)
    schemas = SchemaRegistry(schema_root or repository_root / "contracts" / "schemas")
    workspace_service = WorkspaceService(
        active_settings.workspace_root,
        schemas,
        LocalConfigRepository(config_path),
    )

    app = FastAPI(
        title="PaperMatrix API",
        version=__version__,
        docs_url="/api/docs",
        redoc_url=None,
    )
    app.state.settings = active_settings
    app.state.workspace_service = workspace_service
    app.state.project_service = ProjectService(workspace_service, schemas)
    app.state.item_link_service = ItemLinkService(workspace_service, schemas)
    app.state.paper_content_service = PaperContentService(
        workspace_service,
        schemas,
        repository_root / "templates" / "paper-note-template.md",
    )
    app.state.paper_service = PaperService(
        workspace_service,
        schemas,
        app.state.paper_content_service,
        max_scan_files=active_settings.max_scan_files,
        max_upload_bytes=active_settings.max_upload_bytes,
    )
    app.add_exception_handler(PaperMatrixError, papermatrix_error_handler)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "If-Match", "X-Request-ID"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):  # type: ignore[no-untyped-def]
        started = perf_counter()
        request.state.request_id = request.headers.get("X-Request-ID", str(uuid4()))
        response = await call_next(request)
        duration_ms = (perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["Server-Timing"] = f"app;dur={duration_ms:.2f}"
        logging.getLogger("papermatrix.request").info(
            "request_complete",
            extra={
                "request_id": request.state.request_id,
                "method": request.method,
                "route": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )
        return response

    app.include_router(health_router, prefix="/api/v1")
    app.include_router(workspace_router, prefix="/api/v1")
    app.include_router(projects_router, prefix="/api/v1")
    app.include_router(item_links_router, prefix="/api/v1")
    app.include_router(papers_router, prefix="/api/v1")
    app.include_router(paper_content_router, prefix="/api/v1")
    return app


app = create_app()
