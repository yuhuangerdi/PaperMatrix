"""API error handlers."""

from __future__ import annotations

from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse

from papermatrix.core.errors import PaperMatrixError


async def papermatrix_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, PaperMatrixError):
        raise exc
    request_id = getattr(request.state, "request_id", str(uuid4()))
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "action": exc.action,
                "request_id": request_id,
            }
        },
    )
