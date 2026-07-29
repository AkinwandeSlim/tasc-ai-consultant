"""Vector store protocol."""

from __future__ import annotations

from typing import Any, Protocol


class VectorStore(Protocol):
    """Protocol for vector store implementations."""

    async def similarity_search(
        self, query_vector: list[float], top_k: int = 5, filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]: ...

    async def count(self) -> int: ...

    async def health(self) -> bool: ...
