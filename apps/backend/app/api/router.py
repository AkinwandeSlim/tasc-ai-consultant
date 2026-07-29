"""API layer — route registration and aggregation.

Mounts all versioned routers under the configured API prefix.
No business logic lives here — this is pure routing.
"""

from fastapi import APIRouter

from app.api.v1.chat import router as chat_router
from app.api.v1.demo import router as demo_router
from app.api.v1.health import router as health_router
from app.api.v1.sessions import router as sessions_router

api_router = APIRouter()

# Mount versioned routers
api_router.include_router(sessions_router, prefix="/v1")
api_router.include_router(chat_router, prefix="/v1")
api_router.include_router(demo_router, prefix="/v1")
api_router.include_router(health_router)
