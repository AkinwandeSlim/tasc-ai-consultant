"""Tests for the ChatProvider protocol and OpenAI adapter (Sprint 6.3).

Verifies:
  ✓ ChatProvider protocol is properly defined
  ✓ Mock/Fake provider implements the protocol
  ✓ OpenAIChatProvider constructs correctly
  ✓ complete() calls OpenAI SDK and maps response
  ✓ complete_structured() validates schema and returns StructuredResult
  ✓ Error mapping: timeout, rate limit, connection, API errors
  ✓ ProviderUnavailableError is raised on SDK failures
  ✓ Provider construction without API key

References: Sprint 6.3 requirement, Backend Blueprint §5
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import ProviderUnavailableError
from app.infrastructure.providers.base import (
    ChatDelta,
    ChatProvider,
    ChatRequest,
    ChatResult,
    ProviderCapabilities,
    StructuredResult,
    TokenUsage,
)

# ── Fake Provider for Protocol Tests ─────────────────────────────────


class FakeChatProvider:
    """A fake ChatProvider for testing the protocol."""

    def __init__(self, fail: bool = False, latency: float = 0.0) -> None:
        self._fail = fail
        self._latency = latency
        self._call_count = 0

    async def complete(self, request: ChatRequest) -> ChatResult:
        self._call_count += 1
        if self._fail:
            raise ProviderUnavailableError("Simulated failure")
        return ChatResult(
            content="This is a fake response.",
            usage=TokenUsage(input_tokens=10, output_tokens=5),
        )

    async def complete_stream(self, request: ChatRequest) -> AsyncIterator[ChatDelta]:
        self._call_count += 1
        if self._fail:
            raise ProviderUnavailableError("Simulated failure")
        yield ChatDelta(delta="fake ", finish_reason=None)
        yield ChatDelta(delta="response", finish_reason="stop")

    async def complete_structured(
        self,
        request: ChatRequest,
        schema: type,
    ) -> StructuredResult:
        self._call_count += 1
        if self._fail:
            raise ProviderUnavailableError("Simulated failure")
        return StructuredResult(
            content={"assistant_message": "test", "conversation_phase": "discovery"},
            usage=TokenUsage(input_tokens=10, output_tokens=5),
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities()

    @property
    def call_count(self) -> int:
        return self._call_count


# ── Protocol Definition Tests ────────────────────────────────────────


class TestChatProviderProtocol:
    """Verify the ChatProvider protocol is properly defined."""

    def test_protocol_has_required_methods(self):
        """The protocol should define all required methods."""
        assert hasattr(ChatProvider, "complete")
        assert hasattr(ChatProvider, "complete_stream")
        assert hasattr(ChatProvider, "complete_structured")
        assert hasattr(ChatProvider, "capabilities")

    def test_fake_provider_satisfies_protocol(self):
        """FakeChatProvider should satisfy the ChatProvider protocol."""
        from typing import cast

        provider: ChatProvider = cast(ChatProvider, FakeChatProvider())
        assert provider is not None


class TestFakeChatProvider:
    """Verify the fake provider works correctly for testing."""

    @pytest.mark.asyncio
    async def test_complete_returns_result(self):
        """complete() should return a ChatResult."""
        provider = FakeChatProvider()
        request = ChatRequest(messages=[{"role": "user", "content": "Hello"}])
        result = await provider.complete(request)
        assert isinstance(result, ChatResult)
        assert result.content == "This is a fake response."
        assert result.usage.input_tokens == 10

    @pytest.mark.asyncio
    async def test_complete_stream_yields_deltas(self):
        """complete_stream() should yield ChatDelta objects."""
        provider = FakeChatProvider()
        request = ChatRequest(messages=[{"role": "user", "content": "Hello"}])
        deltas = []
        async for delta in provider.complete_stream(request):
            deltas.append(delta)
        assert len(deltas) == 2
        assert all(isinstance(d, ChatDelta) for d in deltas)

    @pytest.mark.asyncio
    async def test_complete_structured_returns_result(self):
        """complete_structured() should return a StructuredResult."""
        provider = FakeChatProvider()

        from pydantic import BaseModel

        class TestSchema(BaseModel):
            assistant_message: str
            conversation_phase: str

        request = ChatRequest(messages=[{"role": "user", "content": "Hello"}])
        result = await provider.complete_structured(request, TestSchema)
        assert isinstance(result, StructuredResult)
        assert result.content["assistant_message"] == "test"

    @pytest.mark.asyncio
    async def test_complete_raises_on_failure(self):
        """complete() should propagate ProviderUnavailableError."""
        provider = FakeChatProvider(fail=True)
        request = ChatRequest(messages=[{"role": "user", "content": "Hello"}])
        with pytest.raises(ProviderUnavailableError):
            await provider.complete(request)

    def test_capabilities_returned(self):
        """capabilities() should return a ProviderCapabilities."""
        provider = FakeChatProvider()
        caps = provider.capabilities()
        assert isinstance(caps, ProviderCapabilities)


# ── OpenAIChatProvider Tests ─────────────────────────────────────────


class TestOpenAIChatProviderConstruction:
    """Verify OpenAIChatProvider constructs correctly."""

    def test_constructs_with_valid_key(self):
        """Provider should construct with a valid API key."""
        from app.infrastructure.providers.openai_chat import OpenAIChatProvider

        provider = OpenAIChatProvider(api_key="sk-test")
        assert provider is not None
        assert provider._model == "gpt-4.1-mini"

    def test_constructs_with_empty_key(self):
        """Provider should construct (with warning) with an empty key."""
        from app.infrastructure.providers.openai_chat import OpenAIChatProvider

        provider = OpenAIChatProvider(api_key="")
        assert provider is not None

    def test_constructs_with_custom_model(self):
        """Provider should accept a custom model name."""
        from app.infrastructure.providers.openai_chat import OpenAIChatProvider

        provider = OpenAIChatProvider(api_key="sk-test", model="gpt-4o")
        assert provider._model == "gpt-4o"


class TestOpenAIChatProviderComplete:
    """Verify OpenAIChatProvider.complete() works correctly."""

    @pytest.mark.asyncio
    async def test_complete_returns_chat_result(self):
        """complete() should return ChatResult with content."""
        from app.infrastructure.providers.openai_chat import OpenAIChatProvider

        # Mock the OpenAI SDK response
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Hello! How can I help you today?"
        mock_response.choices = [mock_choice]
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 15
        mock_usage.completion_tokens = 8
        mock_response.usage = mock_usage

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        provider = OpenAIChatProvider(api_key="sk-test")
        provider._client = mock_client

        request = ChatRequest(
            messages=[{"role": "system", "content": "Be helpful."}, {"role": "user", "content": "Hi"}],
        )
        result = await provider.complete(request)

        assert isinstance(result, ChatResult)
        assert result.content == "Hello! How can I help you today?"
        assert result.usage.input_tokens == 15
        assert result.usage.output_tokens == 8

        # Verify the SDK was called correctly
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4.1-mini"
        assert len(call_kwargs["messages"]) == 2

    @pytest.mark.asyncio
    async def test_complete_maps_timeout_error(self):
        """A timeout error should map to ProviderUnavailableError."""
        from openai import APITimeoutError

        from app.infrastructure.providers.openai_chat import OpenAIChatProvider

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=APITimeoutError("Request timed out"),
        )

        provider = OpenAIChatProvider(api_key="sk-test")
        provider._client = mock_client

        request = ChatRequest(messages=[{"role": "user", "content": "Hi"}])
        with pytest.raises(ProviderUnavailableError) as exc_info:
            await provider.complete(request)
        assert exc_info.value.code == "PROVIDER_TIMEOUT"

    @pytest.mark.asyncio
    async def test_complete_maps_rate_limit_error(self):
        """A rate limit error should map to ProviderUnavailableError."""
        from openai import RateLimitError

        from app.infrastructure.providers.openai_chat import OpenAIChatProvider

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=RateLimitError(
                message="Rate limited",
                response=MagicMock(status_code=429),
                body=None,
            ),
        )

        provider = OpenAIChatProvider(api_key="sk-test")
        provider._client = mock_client

        request = ChatRequest(messages=[{"role": "user", "content": "Hi"}])
        with pytest.raises(ProviderUnavailableError) as exc_info:
            await provider.complete(request)
        assert exc_info.value.code == "PROVIDER_RATE_LIMITED"

    @pytest.mark.asyncio
    async def test_complete_maps_connection_error(self):
        """A connection error should map to ProviderUnavailableError."""
        from openai import APIConnectionError

        from app.infrastructure.providers.openai_chat import OpenAIChatProvider

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=APIConnectionError(message="Connection failed", request=MagicMock()),
        )

        provider = OpenAIChatProvider(api_key="sk-test")
        provider._client = mock_client

        request = ChatRequest(messages=[{"role": "user", "content": "Hi"}])
        with pytest.raises(ProviderUnavailableError) as exc_info:
            await provider.complete(request)
        assert exc_info.value.code == "PROVIDER_CONNECTION_ERROR"


class TestOpenAIChatProviderStructuredOutput:
    """Verify OpenAIChatProvider.complete_structured() works correctly."""

    @pytest.mark.asyncio
    async def test_structured_returns_validated_result(self):
        """complete_structured() should validate and return StructuredResult."""
        from pydantic import BaseModel

        from app.infrastructure.providers.openai_chat import OpenAIChatProvider

        class TestOutput(BaseModel):
            assistant_message: str
            score: int = 0

        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = '{"assistant_message": "Hello!", "score": 75}'
        mock_response.choices = [mock_choice]
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 20
        mock_usage.completion_tokens = 10
        mock_response.usage = mock_usage

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        provider = OpenAIChatProvider(api_key="sk-test")
        provider._client = mock_client

        request = ChatRequest(messages=[{"role": "user", "content": "Analyze this"}])
        result = await provider.complete_structured(request, TestOutput)

        assert isinstance(result, StructuredResult)
        assert result.content["assistant_message"] == "Hello!"
        assert result.content["score"] == 75

        # Verify response_format was passed
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert "response_format" in call_kwargs
        assert call_kwargs["response_format"]["type"] == "json_schema"

    @pytest.mark.asyncio
    async def test_structured_handles_invalid_json(self):
        """Invalid JSON from the API should raise ProviderUnavailableError."""
        from pydantic import BaseModel

        from app.infrastructure.providers.openai_chat import OpenAIChatProvider

        class TestOutput(BaseModel):
            assistant_message: str

        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "not-json{{{"
        mock_response.choices = [mock_choice]
        mock_response.usage = None

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        provider = OpenAIChatProvider(api_key="sk-test")
        provider._client = mock_client

        request = ChatRequest(messages=[{"role": "user", "content": "Hi"}])
        with pytest.raises(ProviderUnavailableError) as exc_info:
            await provider.complete_structured(request, TestOutput)
        assert exc_info.value.code == "PROVIDER_INVALID_JSON"

    @pytest.mark.asyncio
    async def test_structured_validates_schema(self):
        """Output that doesn't match the schema should raise ProviderUnavailableError."""
        from pydantic import BaseModel

        from app.infrastructure.providers.openai_chat import OpenAIChatProvider

        class TestOutput(BaseModel):
            assistant_message: str  # Required field

        # Missing required field "assistant_message"
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = '{"wrong_field": "hello"}'
        mock_response.choices = [mock_choice]
        mock_response.usage = None

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        provider = OpenAIChatProvider(api_key="sk-test")
        provider._client = mock_client

        request = ChatRequest(messages=[{"role": "user", "content": "Hi"}])
        with pytest.raises(ProviderUnavailableError) as exc_info:
            await provider.complete_structured(request, TestOutput)
        assert exc_info.value.code == "PROVIDER_SCHEMA_MISMATCH"
