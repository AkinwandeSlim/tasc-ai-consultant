"""Tests for configuration layer."""
from app.core.config import LLMProvider, Settings


class TestSettings:
    """Settings validation tests."""

    def test_defaults_are_valid(self) -> None:
        """Default settings should load without error."""
        settings = Settings(LLM_API_KEY="test")
        assert settings.APP_ENV == "local"
        assert settings.API_PREFIX == "/api"
        assert settings.LLM_MODEL == "gpt-4.1-mini"

    def test_cors_parsing(self) -> None:
        """CORS origins should parse from comma-separated string."""
        settings = Settings(
            LLM_API_KEY="test",
            CORS_ALLOWED_ORIGINS="http://a.com,http://b.com",
        )
        assert len(settings.CORS_ALLOWED_ORIGINS) == 2
        assert "http://a.com" in settings.CORS_ALLOWED_ORIGINS

    def test_llm_enabled_without_api_key_does_not_crash(self) -> None:
        """LLM_ENABLED=true with empty API key should not raise.

        The container handles missing API keys gracefully by falling
        back to the deterministic engine. This test confirms the
        config layer is permissive; the runtime decides availability.
        """
        settings = Settings(
            APP_ENV="local",
            LLM_API_KEY="",
            LLM_ENABLED=True,
        )
        assert settings.LLM_ENABLED is True
        assert settings.LLM_API_KEY.get_secret_value() == ""

    def test_llm_enabled_with_api_key_loads(self) -> None:
        """LLM_ENABLED=true with a valid-looking API key."""
        settings = Settings(
            APP_ENV="local",
            LLM_API_KEY="sk-test-key",
            LLM_ENABLED=True,
        )
        assert settings.LLM_ENABLED is True
        assert settings.LLM_API_KEY.get_secret_value() == "sk-test-key"

    # ── Generic provider config ─────────────────────────────────────────

    def test_legacy_openai_api_key_alias_still_works(self) -> None:
        """The legacy OPENAI_API_KEY spelling maps onto LLM_API_KEY."""
        settings = Settings(OPENAI_API_KEY="sk-legacy-key")
        assert settings.LLM_API_KEY.get_secret_value() == "sk-legacy-key"

    def test_legacy_llm_chat_model_alias_still_works(self) -> None:
        """The legacy LLM_CHAT_MODEL spelling maps onto LLM_MODEL."""
        settings = Settings(LLM_CHAT_MODEL="gpt-4o")
        assert settings.LLM_MODEL == "gpt-4o"

    def test_legacy_openai_base_url_alias_still_works(self) -> None:
        """The legacy OPENAI_BASE_URL spelling maps onto LLM_BASE_URL."""
        settings = Settings(OPENAI_BASE_URL="https://example.com/v1")
        assert settings.LLM_BASE_URL == "https://example.com/v1"

    def test_generic_llm_provider_config_loads(self) -> None:
        """Generic LLM_PROVIDER / LLM_BASE_URL / LLM_MODEL are honoured."""
        settings = Settings(
            LLM_PROVIDER="groq",
            LLM_API_KEY="sk-groq-key",
            LLM_BASE_URL="https://api.groq.com/openai/v1",
            LLM_MODEL="llama-3.3-70b-versatile",
        )
        assert settings.LLM_PROVIDER == LLMProvider.GROQ
        assert settings.LLM_API_KEY.get_secret_value() == "sk-groq-key"
        assert settings.LLM_BASE_URL == "https://api.groq.com/openai/v1"
        assert settings.LLM_MODEL == "llama-3.3-70b-versatile"

    def test_supported_providers_enum(self) -> None:
        """OpenAI, OpenRouter and Groq are supported provider values."""
        assert LLMProvider.OPENAI.value == "openai"
        assert LLMProvider.OPENROUTER.value == "openrouter"
        assert LLMProvider.GROQ.value == "groq"
