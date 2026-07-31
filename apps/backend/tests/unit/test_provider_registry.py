"""Tests for provider registry — provider selection by configuration."""

from __future__ import annotations

from app.core.config import Settings
from app.infrastructure.providers.registry import create_chat_provider


class TestChatProviderSelection:
    """Verify create_chat_provider resolves providers from config."""

    def test_returns_none_without_api_key(self) -> None:
        """No API key configured means no chat provider (deterministic fallback)."""
        settings = Settings(LLM_ENABLED=True, LLM_API_KEY="")
        assert create_chat_provider(settings) is None

    def test_openai_selects_openai_compatible_adapter(self) -> None:
        """OpenAI provider resolves to the OpenAI-compatible adapter."""
        settings = Settings(LLM_PROVIDER="openai", LLM_API_KEY="sk-openai")
        provider = create_chat_provider(settings)
        assert provider is not None
        assert type(provider).__name__ == "OpenAIChatProvider"
        assert provider._model == "gpt-4.1-mini"

    def test_openrouter_selects_openai_compatible_adapter(self) -> None:
        """OpenRouter is served by the same OpenAI-compatible adapter."""
        settings = Settings(LLM_PROVIDER="openrouter", LLM_API_KEY="sk-or")
        provider = create_chat_provider(settings)
        assert provider is not None
        assert type(provider).__name__ == "OpenAIChatProvider"
        # OpenRouter default base URL applied when not overridden
        assert provider._base_url == "https://openrouter.ai/api/v1"

    def test_groq_selects_openai_compatible_adapter(self) -> None:
        """Groq is served by the same OpenAI-compatible adapter."""
        settings = Settings(LLM_PROVIDER="groq", LLM_API_KEY="sk-groq")
        provider = create_chat_provider(settings)
        assert provider is not None
        assert type(provider).__name__ == "OpenAIChatProvider"
        assert provider._base_url == "https://api.groq.com/openai/v1"

    def test_custom_base_url_overrides_provider_default(self) -> None:
        """LLM_BASE_URL takes precedence over the provider default."""
        settings = Settings(
            LLM_PROVIDER="openrouter",
            LLM_API_KEY="sk-or",
            LLM_BASE_URL="https://proxy.example.com/v1",
        )
        provider = create_chat_provider(settings)
        assert provider is not None
        assert provider._base_url == "https://proxy.example.com/v1"

    def test_custom_model_applied(self) -> None:
        """LLM_MODEL is passed through to the provider."""
        settings = Settings(
            LLM_PROVIDER="groq",
            LLM_API_KEY="sk-groq",
            LLM_MODEL="llama-3.3-70b-versatile",
        )
        provider = create_chat_provider(settings)
        assert provider is not None
        assert provider._model == "llama-3.3-70b-versatile"

    def test_unknown_provider_rejected_at_config(self) -> None:
        """An unrecognised provider name is rejected at config validation."""
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Settings(LLM_PROVIDER="anthropic", LLM_API_KEY="sk-test")
