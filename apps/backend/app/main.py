"""ASGI application entry point.

Wires middleware, mounts routers, and attaches lifespan handlers.
No business logic lives here — this is pure composition.
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.api.router import api_router
from app.api.errors import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown."""
    settings = get_settings()

    # Startup
    configure_logging(settings)
    app.state.settings = settings

    # TODO: Initialize container, providers, vector store, prompt registry
    # See apps/backend/app/lifespan.py for the full startup sequence

    yield

    # Shutdown
    # TODO: Flush session state, close HTTPX clients, persist dead letters


def create_app() -> FastAPI:
    """Build and return a fully configured FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="TASC API",
        description="Trizen AI Solutions Consultant — Backend API",
        version="1.0.0",
        docs_url=f"{settings.API_PREFIX}/docs" if settings.DOCS_ENABLED else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    # --- Middleware stack (outermost first) ---
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.TRUSTED_HOSTS,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    app.add_middleware(
        GZipMiddleware,
        minimum_size=1000,
    )

    # --- Exception handlers ---
    register_exception_handlers(app)

    # --- Routers ---
    app.include_router(api_router, prefix=settings.API_PREFIX)

    return app


app = create_app()
