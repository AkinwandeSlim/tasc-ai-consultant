"""Correlation ID middleware.

Attaches a unique correlation ID to every request. If the client
provides one via the X-Correlation-Id header it is used as-is,
otherwise a new UUID is generated.

The ID is available on:
- request.state.correlation_id — for use in route handlers
- response.header X-Correlation-Id — so callers can correlate

References: Backend Blueprint Section 6.3, PRD Section 6.9
"""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.constants import HEADER_CORRELATION_ID


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware that ensures every request has a correlation ID."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        correlation_id: str = request.headers.get(
            HEADER_CORRELATION_ID, ""
        )
        if not correlation_id:
            correlation_id = uuid.uuid4().hex[:24]

        # Persist in both scope and state for broad compatibility
        request.scope[HEADER_CORRELATION_ID] = correlation_id
        if "state" not in request.scope:
            request.scope["state"] = {}
        request.scope["state"]["correlation_id"] = correlation_id

        # Also set on request.state if the property is available
        try:
            request.state.correlation_id = correlation_id
        except (AttributeError, KeyError, TypeError):
            pass

        response: Response = await call_next(request)

        # Set the correlation ID on the response
        response.headers[HEADER_CORRELATION_ID] = correlation_id

        return response
