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
