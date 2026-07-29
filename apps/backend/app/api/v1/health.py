"""Health check endpoints.

GET /health          — full diagnostics (status, version, simulation_mode, timestamp)
GET /health/live     — liveness (always 200)
GET /health/ready    — readiness (no third-party dependencies for Sprint 4)

References: Backend Blueprint Section 6.5
"""

from __future__ import annotations

import datetime

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check() -> dict:
    """Full health diagnostics.

    Returns application status, version, simulation mode, and timestamp.
    """
    settings = get_settings()
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "simulation_mode": settings.SIMULATION_MODE,
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
    }


@router.get("/live")
async def liveness() -> dict:
    """Liveness probe — always returns 200."""
    return {"status": "alive"}


@router.get("/ready")
async def readiness() -> dict:
    """Readiness probe — for Sprint 4 always returns ready."""
    return {"status": "ready"}
