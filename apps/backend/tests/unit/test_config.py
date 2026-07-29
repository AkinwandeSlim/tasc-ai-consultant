"""Tests for configuration layer."""
from app.core.config import Settings


class TestSettings:
    """Settings validation tests."""

    def test_defaults_are_valid(self) -> None:
        """Default settings should load without error."""
        settings = Settings(OPENAI_API_KEY="test")
        assert settings.APP_ENV == "local"
        assert settings.API_PREFIX == "/api"
        assert settings.LLM_CHAT_MODEL == "gpt-4.1-mini"

    def test_cors_parsing(self) -> None:
        """CORS origins should parse from comma-separated string."""
        settings = Settings(
            OPENAI_API_KEY="test",
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
            OPENAI_API_KEY="",
            LLM_ENABLED=True,
        )
        assert settings.LLM_ENABLED is True
        assert settings.OPENAI_API_KEY.get_secret_value() == ""

    def test_llm_enabled_with_api_key_loads(self) -> None:
        """LLM_ENABLED=true with a valid-looking API key."""
        settings = Settings(
            APP_ENV="local",
            OPENAI_API_KEY="sk-test-key",
            LLM_ENABLED=True,
        )
        assert settings.LLM_ENABLED is True
        assert settings.OPENAI_API_KEY.get_secret_value() == "sk-test-key"
