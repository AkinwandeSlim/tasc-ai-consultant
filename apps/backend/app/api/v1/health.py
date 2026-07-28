"""Health check endpoints.

GET /health/live     — liveness (always 200)
GET /health/ready    — readiness (no third-party calls)
GET /health          — full diagnostics
"""

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


# TODO: Implement route handlers
