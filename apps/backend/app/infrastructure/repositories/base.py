"""Repository protocols."""

from __future__ import annotations

from typing import Protocol, Any


class SessionRepository(Protocol):
    """Protocol for session persistence."""

    async def save(self, session: Any) -> None: ...

    async def load(self, session_id: str) -> Any | None: ...

    async def delete(self, session_id: str) -> None: ...

    async def exists(self, session_id: str) -> bool: ...


class PayloadRepository(Protocol):
    """Protocol for consultation payload persistence."""

    async def save(self, consultation_id: str, payload: Any) -> None: ...

    async def load(self, consultation_id: str) -> Any | None: ...

    async def exists(self, consultation_id: str) -> bool: ...
