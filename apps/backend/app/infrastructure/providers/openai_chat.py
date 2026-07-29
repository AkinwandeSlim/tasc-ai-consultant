"""OpenAI chat provider — implements ChatProvider protocol.

Uses the openai SDK for chat completions and structured output.
All SDK types are isolated inside this adapter — domain code depends
only on the ChatProvider protocol (BP-03).

References: Backend Blueprint §5, Sprint 6.3 requirement
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    RateLimitError,
)
from pydantic import BaseModel

from app.core.exceptions import ProviderUnavailableError
from app.infrastructure.providers.base import (
    ChatDelta,
    ChatRequest,
    ChatResult,
    ProviderCapabilities,
    StructuredResult,
    TokenUsage,
)

logger = logging.getLogger(__name__)


class OpenAIChatProvider:
    """Chat completion provider backed by the OpenAI SDK.

    Wraps the openai.AsyncClient and maps its types to the domain-owned
    ChatRequest / ChatResult / StructuredResult types.

    The SDK client is created lazily on the first API call so that
    construction succeeds even without an API key (calls fail at runtime
    with a clear error instead).
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4.1-mini",
        base_url: str | None = None,
        temperature: float = 0.3,
        structured_temperature: float = 0.0,
        max_tokens: int = 700,
        timeout_seconds: float = 30.0,
        connect_timeout_seconds: float = 5.0,
        max_retries: int = 1,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._temperature = temperature
        self._structured_temperature = structured_temperature
        self._max_tokens = max_tokens
        self._timeout_seconds = timeout_seconds
        self._connect_timeout_seconds = connect_timeout_seconds
        self._max_retries = max_retries
        self._client: Any = None  # Lazily created

        if not api_key:
            logger.warning("OpenAIChatProvider constructed without an API key — calls will fail at runtime")

    # ── Lazy client property ────────────────────────────────────────────

    @property
    def _async_client(self) -> Any:
        """Lazily create the OpenAI AsyncClient."""
        if self._client is not None:
            return self._client

        from openai import AsyncOpenAI

        client_kwargs: dict[str, Any] = {
            "api_key": self._api_key,
            "max_retries": self._max_retries,
        }
        if self._base_url:
            client_kwargs["base_url"] = self._base_url

        # Build a structured timeout
        from httpx import Timeout as HttpxTimeout

        client_kwargs["timeout"] = HttpxTimeout(
            connect=self._connect_timeout_seconds,
            read=self._timeout_seconds,
            write=self._timeout_seconds,
            pool=self._timeout_seconds,
        )

        self._client = AsyncOpenAI(**client_kwargs)
        return self._client

    # ── ChatProvider protocol implementation ────────────────────────────

    async def complete(self, request: ChatRequest) -> ChatResult:
        """Standard non-streaming chat completion."""
        kwargs = self._build_completion_kwargs(request)
        try:
            response = await self._async_client.chat.completions.create(**kwargs)
        except Exception as exc:
            raise self._map_error(exc) from exc

        content = response.choices[0].message.content or ""
        return ChatResult(
            content=content,
            usage=TokenUsage(
                input_tokens=response.usage.prompt_tokens if response.usage else 0,
                output_tokens=response.usage.completion_tokens if response.usage else 0,
            ),
        )

    async def complete_stream(self, request: ChatRequest) -> AsyncIterator[ChatDelta]:
        """Streaming chat completion."""
        kwargs = self._build_completion_kwargs(request)
        kwargs["stream"] = True
        try:
            stream = await self._async_client.chat.completions.create(**kwargs)
        except Exception as exc:
            raise self._map_error(exc) from exc

        async for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                finish = chunk.choices[0].finish_reason
                yield ChatDelta(
                    delta=delta.content or "" if delta else "",
                    finish_reason=finish,
                )

    async def complete_structured(
        self,
        request: ChatRequest,
        schema: type[BaseModel],
    ) -> StructuredResult:
        """Structured output using response_format.

        Uses OpenAI's structured output via json_schema response_format.
        The raw JSON is parsed and validated against the provided schema.

        Args:
            request: Chat request with messages and parameters.
            schema: A Pydantic BaseModel subclass.

        Returns:
            StructuredResult with the validated dict content.
        """
        json_schema = schema.model_json_schema()
        kwargs = self._build_completion_kwargs(request)
        kwargs["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": schema.__name__,
                "schema": json_schema,
                "strict": True,
            },
        }
        # Always use structured temperature for schema-guided calls
        kwargs["temperature"] = self._structured_temperature

        try:
            response = await self._async_client.chat.completions.create(**kwargs)
        except Exception as exc:
            raise self._map_error(exc) from exc

        raw = response.choices[0].message.content or ""
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProviderUnavailableError(
                message="Received malformed JSON from the language model.",
                code="PROVIDER_INVALID_JSON",
            ) from exc

        # Validate against the schema
        try:
            validated = schema.model_validate(parsed)
        except Exception as exc:
            raise ProviderUnavailableError(
                message="Received output that did not match the expected schema.",
                code="PROVIDER_SCHEMA_MISMATCH",
            ) from exc

        return StructuredResult(
            content=validated.model_dump(),
            usage=TokenUsage(
                input_tokens=response.usage.prompt_tokens if response.usage else 0,
                output_tokens=response.usage.completion_tokens if response.usage else 0,
            ),
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_streaming=True,
            supports_native_schema=True,
            supports_json_mode=True,
            max_context_tokens=128000,
        )

    # ── Internal helpers ────────────────────────────────────────────────

    def _build_completion_kwargs(self, request: ChatRequest) -> dict[str, Any]:
        """Build the kwargs dict for the OpenAI chat completions API."""
        kwargs: dict[str, Any] = {
            "model": request.model or self._model,
            "messages": request.messages,
            "max_tokens": request.max_tokens or self._max_tokens,
        }
        if request.temperature is not None:
            kwargs["temperature"] = request.temperature
        else:
            kwargs["temperature"] = self._temperature
        return kwargs

    def _map_error(self, exc: Exception) -> ProviderUnavailableError:
        """Map OpenAI SDK exceptions to the project exception hierarchy."""
        logger.warning("OpenAI provider error: %s: %s", type(exc).__name__, exc)

        if isinstance(exc, APITimeoutError):
            return ProviderUnavailableError(
                message="The language model took too long to respond.",
                code="PROVIDER_TIMEOUT",
            )
        if isinstance(exc, APIConnectionError):
            return ProviderUnavailableError(
                message="Could not reach the language model provider.",
                code="PROVIDER_CONNECTION_ERROR",
            )
        if isinstance(exc, RateLimitError):
            return ProviderUnavailableError(
                message="The language model is currently rate-limited. Please try again.",
                code="PROVIDER_RATE_LIMITED",
            )
        if isinstance(exc, APIStatusError):
            return ProviderUnavailableError(
                message=f"The language model returned an error (HTTP {exc.status_code}).",
                code="PROVIDER_API_ERROR",
            )
        return ProviderUnavailableError(
            message="An unexpected error occurred while calling the language model.",
            code="PROVIDER_UNEXPECTED_ERROR",
        )
