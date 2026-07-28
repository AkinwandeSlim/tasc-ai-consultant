"""Exception handlers — maps domain exceptions to HTTP error envelopes.

Every non-2xx response uses a single error envelope shape
(Backend Blueprint Section 6.9).

If the CorrelationIdMiddleware has run, request.state.correlation_id
is available. Otherwise the ID is read from the request header.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.constants import HEADER_CORRELATION_ID
from app.core.exceptions import TASCError


def _correlation_id(request: Request) -> str:
    """Return the correlation ID from request state, scope, or header."""
    # Try request.state (set by CorrelationIdMiddleware)
    try:
        state = request.state
        if hasattr(state, "correlation_id") and state.correlation_id:
            return state.correlation_id
    except (AttributeError, KeyError):
        pass

    # Try scope directly
    try:
        scope_state = request.scope.get("state", {})
        if isinstance(scope_state, dict) and scope_state.get("correlation_id"):
            return scope_state["correlation_id"]
    except Exception:
        pass

    # Fall back to request header
    return request.headers.get(HEADER_CORRELATION_ID, "")


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
    return JSONResponse(
        status_code=exc.http_status,
        content=_error_envelope(
            code=exc.code,
            message=exc.message,
            correlation_id=_correlation_id(request),
            retryable=exc.retryable,
            details=getattr(exc, "details", None),
        ),
    )


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle Pydantic/FastAPI validation errors."""
    correlation_id = _correlation_id(request)
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
    correlation_id = _correlation_id(request)
    return JSONResponse(
        status_code=500,
        content=_error_envelope(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred.",
            correlation_id=correlation_id,
            retryable=True,
        ),
    )


async def http404_handler(request: Request, _: Exception) -> JSONResponse:
    """Handle 404 Not Found — returns standard error envelope."""
    return JSONResponse(
        status_code=404,
        content=_error_envelope(
            code="NOT_FOUND",
            message="The requested resource was not found.",
            correlation_id=_correlation_id(request),
            retryable=False,
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI application."""
    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException

    app.add_exception_handler(TASCError, tasc_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http404_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
