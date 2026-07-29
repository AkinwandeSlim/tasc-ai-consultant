"""Session repository — persistence for consultation sessions.

Defines an abstract SessionRepository interface and provides an
in-memory implementation. Designed so Redis can replace the backing
store without changing callers: implement the same protocol.

References: Backend Blueprint Section 5.6, PRD Section 6.5
"""

from __future__ import annotations

import abc
import copy
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class SessionRepository(abc.ABC):
    """Abstract session repository.

    All operations are async to accommodate a future Redis/DB adapter
    without changing callers. The in-memory variant satisfies them
    synchronously under the async signature.
    """

    @abc.abstractmethod
    async def save(self, session_id: str, state: dict[str, Any]) -> None:
        """Persist a session state."""

    @abc.abstractmethod
    async def get(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve a session state by ID."""

    @abc.abstractmethod
    async def delete(self, session_id: str) -> bool:
        """Delete a session. Returns True if it existed."""

    @abc.abstractmethod
    async def exists(self, session_id: str) -> bool:
        """Check if a session exists."""

    @abc.abstractmethod
    async def list_active(self) -> list[str]:
        """Return IDs of all active sessions."""


class InMemorySessionStore(SessionRepository):
    """Lightweight in-memory session store.

    Uses a plain dict for storage. No TTL expiry is enforced — the
    caller (or a future Redis adapter) is responsible for eviction.

    Thread-safe for asyncio because all access is from a single event
    loop thread.
    """

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}
        self._created_at: dict[str, float] = {}

    async def save(self, session_id: str, state: dict[str, Any]) -> None:
        self._store[session_id] = copy.deepcopy(state)
        if session_id not in self._created_at:
            self._created_at[session_id] = time.time()
        logger.debug("Session %s saved (%d keys)", session_id, len(state))

    async def get(self, session_id: str) -> dict[str, Any] | None:
        raw = self._store.get(session_id)
        if raw is None:
            return None
        return copy.deepcopy(raw)

    async def delete(self, session_id: str) -> bool:
        existed = session_id in self._store
        self._store.pop(session_id, None)
        self._created_at.pop(session_id, None)
        if existed:
            logger.debug("Session %s deleted", session_id)
        return existed

    async def exists(self, session_id: str) -> bool:
        return session_id in self._store

    async def list_active(self) -> list[str]:
        return list(self._store.keys())

    @property
    def count(self) -> int:
        """Number of stored sessions."""
        return len(self._store)

    async def clear(self) -> None:
        """Remove all sessions (used in testing)."""
        self._store.clear()
        self._created_at.clear()
