"""Exception handlers — maps domain exceptions to HTTP error envelopes.

Every non-2xx response uses a single error envelope shape
(Backend Blueprint Section 6.9).
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.constants import HEADER_CORRELATION_ID
from app.core.exceptions import TASCError


def _error_envelope(
    code: str,
    message: str,
    correlation_id: str,
    retryable: bool = False,
    details: dict | None = None,
) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "correlation_id": correlation_id,
            "retryable": retryable,
            "details": details,
        }
    }


async def tasc_error_handler(request: Request, exc: TASCError) -> JSONResponse:
    """Handle TASCError subclasses with the standard error envelope."""
    correlation_id = request.headers.get(HEADER_CORRELATION_ID, "")
    return JSONResponse(
        status_code=exc.http_status,
        content=_error_envelope(
            code=exc.code,
            message=exc.message,
            correlation_id=correlation_id,
            retryable=exc.retryable,
            details=getattr(exc, "details", None),
        ),
    )


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle Pydantic/FastAPI validation errors."""
    # FastAPI's RequestValidationError is handled here
    correlation_id = request.headers.get(HEADER_CORRELATION_ID, "")
    return JSONResponse(
        status_code=422,
        content=_error_envelope(
            code="VALIDATION_ERROR",
            message="The request body was invalid.",
            correlation_id=correlation_id,
            retryable=False,
            details={"fields": getattr(exc, "errors", lambda: None)()},
        ),
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions — never leaks a stack trace."""
    correlation_id = request.headers.get(HEADER_CORRELATION_ID, "")
    return JSONResponse(
        status_code=500,
        content=_error_envelope(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred.",
            correlation_id=correlation_id,
            retryable=True,
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI application."""
    from fastapi.exceptions import RequestValidationError

    app.add_exception_handler(TASCError, tasc_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
