"""API dependency resolvers.

Thin callables that read from application state. One per injectable
dependency. Route handlers use `Depends(get_session_context)` etc.
"""

from fastapi import Request
from fastapi.exceptions import HTTPException

from app.core.config import Settings, get_settings


def get_settings_dependency() -> Settings:
    """Return the validated settings singleton."""
    return get_settings()


def get_container(request: Request) -> object:
    """Return the application container from request state."""
    container = getattr(request.app.state, "container", None)
    if container is None:
        raise HTTPException(status_code=503, detail="Application not ready")
    return container


def get_automation_gateway(request: Request) -> object | None:
    """Return the automation gateway from the application container.

    The gateway implementation (Mock vs N8n) is determined by the
    N8N_ENABLED configuration setting. Route handlers use this
    dependency to process consultation turns.

    Returns None if the container is not initialised (e.g. during
    testing), and the caller should fall back to the orchestrator.
    """
    container = getattr(request.app.state, "container", None)
    if container is None:
        return None
    gateway = getattr(container, "automation_gateway", None)
    return gateway
