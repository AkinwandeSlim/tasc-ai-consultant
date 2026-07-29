"""Composition root — dependency injection container.

Constructs concrete adapters and injects them into domain services.
FastAPI dependencies in app/api/deps.py resolve from here.

This module is the only place where the full dependency graph is assembled.
The lifespan module calls container construction after startup checks pass.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import Settings
from app.infrastructure.automation.mock_gateway import MockAutomationGateway
from app.infrastructure.automation.n8n_gateway import N8nAutomationGateway

logger = logging.getLogger(__name__)


@dataclass
class Container:
    """Application container holding all service instances.

    Services are populated during startup and accessed via app.state.container.
    """

    settings: Settings

    # Infrastructure
    chat_provider: Any = field(default=None)
    embedding_provider: Any = field(default=None)
    vector_store: Any = field(default=None)
    prompt_registry: Any = field(default=None)
    session_repository: Any = field(default=None)
    payload_repository: Any = field(default=None)
    deadletter_repository: Any = field(default=None)
    n8n_dispatcher: Any = field(default=None)

    # Gateway
    automation_gateway: Any = field(default=None)
    http_client: Any = field(default=None)

    # Domain services
    scoring_engine: Any = field(default=None)
    recommendation_engine: Any = field(default=None)
    retrieval_service: Any = field(default=None)
    conversation_manager: Any = field(default=None)

    # Orchestration
    orchestrator: Any = field(default=None)
    llm_engine: Any = field(default=None)


def build_container(settings: Settings) -> Container:
    """Build the full dependency graph.

    Called during lifespan startup after all configuration and resources
    have been validated. Returns a fully wired Container instance.

    The automation gateway is selected based on N8N_ENABLED:
      - False: MockAutomationGateway (local deterministic engine)
      - True:  N8nAutomationGateway (forwards to external n8n webhook)

    When LLM_ENABLED=True and N8N_ENABLED=False, the MockAutomationGateway
    uses LlmConsultationEngine instead of ConsultationOrchestrator, with
    automatic fallback to the deterministic engine on failure.
    """
    from app.orchestration.orchestrator import ConsultationOrchestrator

    container = Container(settings=settings)

    # --- HTTP client for outbound calls ---
    container.http_client = httpx.AsyncClient(
        timeout=settings.N8N_TIMEOUT_SECONDS,
        limits=httpx.Limits(
            max_keepalive_connections=10,
            max_connections=20,
        ),
    )

    # --- Deterministic orchestrator (always needed as fallback) ---
    deterministic_orchestrator = ConsultationOrchestrator()

    # --- Chat provider (LLM) ---
    if settings.LLM_ENABLED:
        from app.infrastructure.providers.registry import create_chat_provider

        chat_provider = create_chat_provider(settings)
        container.chat_provider = chat_provider

        if chat_provider is not None:
            from app.orchestration.llm.engine import LlmConsultationEngine

            container.llm_engine = LlmConsultationEngine(
                chat_provider=chat_provider,
                deterministic_engine=deterministic_orchestrator,
            )
            logger.info("LLM consultation engine created with provider=%s", type(chat_provider).__name__)
        else:
            container.llm_engine = None
            logger.info("LLM_ENABLED=True but no API key — LLM engine disabled, using deterministic")
    else:
        container.llm_engine = None

    # --- Automation gateway ---
    if settings.N8N_ENABLED:
        container.automation_gateway = N8nAutomationGateway(
            webhook_url=settings.N8N_WEBHOOK_URL,
            shared_secret=settings.N8N_SHARED_SECRET.get_secret_value()
            if settings.N8N_SHARED_SECRET else "",
            signing_secret=settings.N8N_SIGNING_SECRET.get_secret_value()
            if settings.N8N_SIGNING_SECRET else "",
            http_client=container.http_client,
            timeout_seconds=settings.N8N_TIMEOUT_SECONDS,
            max_retries=settings.N8N_MAX_ATTEMPTS,
            backoff_base_seconds=settings.N8N_BACKOFF_BASE_SECONDS,
        )
    else:
        # When LLM_ENABLED, inject LlmConsultationEngine into MockAutomationGateway
        engine_to_use: Any = deterministic_orchestrator
        if settings.LLM_ENABLED and container.llm_engine is not None:
            engine_to_use = container.llm_engine
            logger.info("MockAutomationGateway using LlmConsultationEngine")

        container.automation_gateway = MockAutomationGateway(
            orchestrator=engine_to_use,
        )

    # TODO: Construct and wire all remaining dependencies following the blueprint:
    #   1. Vector store (ChromaDB adapter)
    #   2. Prompt registry (load templates)
    #   3. Repositories (session, payload, deadletter)
    #   4. Domain services (scoring engine, recommendation engine, etc.)
    #   5. Orchestrator (composed from domain services)

    return container
