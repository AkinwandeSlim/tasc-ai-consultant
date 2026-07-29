"""Provider interfaces — ChatProvider and EmbeddingProvider protocols.

All domain code depends on these protocols, never on concrete SDK types (BP-03).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class TokenUsage:
    """Token usage statistics for a model call."""

    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class ProviderCapabilities:
    """Capabilities reported by a provider implementation."""

    supports_streaming: bool = True
    supports_native_schema: bool = True
    supports_json_mode: bool = True
    max_context_tokens: int = 128000
    embedding_dimension: int = 1536


@dataclass
class ChatRequest:
    """Domain-owned request type for chat completions."""

    messages: list[dict[str, str]]
    model: str = ""
    temperature: float = 0.3
    max_tokens: int = 700
    timeout: float = 30.0
    correlation_id: str = ""
    prompt_version: str = ""


@dataclass
class ChatResult:
    """Domain-owned result type for non-streaming chat completions."""

    content: str
    usage: TokenUsage = field(default_factory=TokenUsage)


@dataclass
class ChatDelta:
    """A single chunk from a streaming response."""

    delta: str = ""
    finish_reason: str | None = None


@dataclass
class StructuredResult:
    """Domain-owned result type for structured output completions."""

    content: dict[str, Any]
    usage: TokenUsage = field(default_factory=TokenUsage)


@dataclass
class EmbeddingResult:
    """Domain-owned result type for embedding calls."""

    vectors: list[list[float]]
    model: str = ""
    usage: TokenUsage = field(default_factory=TokenUsage)


class ChatProvider(Protocol):
    """Protocol for chat completion providers."""

    async def complete(self, request: ChatRequest) -> ChatResult: ...

    async def complete_stream(self, request: ChatRequest) -> AsyncIterator[ChatDelta]: ...

    async def complete_structured(
        self, request: ChatRequest, schema: type
    ) -> StructuredResult: ...

    def capabilities(self) -> ProviderCapabilities: ...


class EmbeddingProvider(Protocol):
    """Protocol for embedding providers."""

    async def embed(self, texts: list[str]) -> EmbeddingResult: ...

    def dimension(self) -> int: ...

    def model_id(self) -> str: ...
