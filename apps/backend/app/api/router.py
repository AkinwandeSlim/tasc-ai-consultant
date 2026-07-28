"""API layer — route registration and aggregation."""

from fastapi import APIRouter

from app.api.v1.sessions import router as sessions_router
from app.api.v1.health import router as health_router

api_router = APIRouter()

# Mount versioned routers
api_router.include_router(sessions_router, prefix="/v1")
api_router.include_router(health_router)
