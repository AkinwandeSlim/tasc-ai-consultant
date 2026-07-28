"""Pytest configuration and shared fixtures."""

from collections.abc import AsyncIterator

import pytest


@pytest.fixture
def sample_settings():
    """Return a minimal settings object for testing."""
    from app.core.config import Settings
    return Settings(APP_ENV="local", OPENAI_API_KEY="test")


@pytest.fixture
def sample_session_id() -> str:
    """Return a fixed session ID for testing."""
    return "01J9XK7T2ZQ8V3N5B4C6D7E8F9"


@pytest.fixture
def sample_consultation_id() -> str:
    """Return a fixed consultation ID for testing."""
    return "01J9XKB2M7QF0R1S2T3U4V5W6X"
