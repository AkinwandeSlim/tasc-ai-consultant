"""Provider registry — constructs provider instances by name.

Resolves the configured LLM provider (e.g. "openai") to a concrete
adapter implementing the ChatProvider protocol.

Extensible for future providers via configuration (NFR-25).

References: Sprint 6.3 requirement, Backend Blueprint §5
"""

from __future__ import annotations

import logging

from app.core.config import Settings
from app.infrastructure.providers.base import ChatProvider, EmbeddingProvider

logger = logging.getLogger(__name__)


def create_chat_provider(settings: Settings) -> ChatProvider | None:
    """Construct a ChatProvider from the application settings.

    Returns None if no API key is configured (the caller should use
    the deterministic engine as fallback).

    Args:
        settings: Validated application settings.

    Returns:
        A ChatProvider instance, or None if not configured.
    """
    api_key = settings.OPENAI_API_KEY.get_secret_value()
    if not api_key:
        logger.info("No OpenAI API key configured — chat provider disabled")
        return None

    provider_name = settings.LLM_PROVIDER

    if provider_name == "openai":
        from app.infrastructure.providers.openai_chat import OpenAIChatProvider

        provider: ChatProvider = OpenAIChatProvider(
            api_key=api_key,
            model=settings.LLM_CHAT_MODEL,
            base_url=settings.OPENAI_BASE_URL,
            temperature=settings.LLM_TEMPERATURE_CONVERSATION,
            structured_temperature=settings.LLM_TEMPERATURE_STRUCTURED,
            max_tokens=settings.LLM_MAX_OUTPUT_TOKENS,
            timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
            connect_timeout_seconds=settings.LLM_CONNECT_TIMEOUT_SECONDS,
            max_retries=settings.LLM_MAX_RETRIES,
        )
        return provider

    logger.warning("Unknown LLM provider: %s", provider_name)
    return None


def create_embedding_provider(settings: Settings) -> EmbeddingProvider | None:
    """Construct an EmbeddingProvider from the application settings.

    Returns None if no API key is configured.

    Args:
        settings: Validated application settings.

    Returns:
        An EmbeddingProvider instance, or None if not configured.
    """
    api_key = settings.OPENAI_API_KEY.get_secret_value()
    if not api_key:
        logger.info("No OpenAI API key configured — embedding provider disabled")
        return None

    # TODO: Implement when embedding/RAG pipeline is wired (Sprint 6.3+)
    logger.info("Embedding provider not yet implemented — returning None")
    return None
