"""API dependency resolvers.

Thin callables that read from application state. One per injectable
dependency. Route handlers use `Depends(get_session_context)` etc.
"""

from fastapi import Request, Depends
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
