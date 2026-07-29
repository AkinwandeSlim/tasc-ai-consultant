"""Composition root — dependency injection container.

Constructs concrete adapters and injects them into domain services.
FastAPI dependencies in app/api/deps.py resolve from here.

This module is the only place where the full dependency graph is assembled.
The lifespan module calls container construction after startup checks pass.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import Settings
from app.infrastructure.automation.mock_gateway import MockAutomationGateway
from app.infrastructure.automation.n8n_gateway import N8nAutomationGateway


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


def build_container(settings: Settings) -> Container:
    """Build the full dependency graph.

    Called during lifespan startup after all configuration and resources
    have been validated. Returns a fully wired Container instance.

    The automation gateway is selected based on N8N_ENABLED:
      - False: MockAutomationGateway (local deterministic engine)
      - True:  N8nAutomationGateway (forwards to external n8n webhook)
    """
    container = Container(settings=settings)

    # --- HTTP client for outbound calls ---
    container.http_client = httpx.AsyncClient(
        timeout=settings.N8N_TIMEOUT_SECONDS,
        limits=httpx.Limits(
            max_keepalive_connections=10,
            max_connections=20,
        ),
    )

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
        container.automation_gateway = MockAutomationGateway()

    # TODO: Construct and wire all remaining dependencies following the blueprint:
    #   1. Providers (ChatProvider, EmbeddingProvider)
    #   2. Vector store (ChromaDB adapter)
    #   3. Prompt registry (load templates)
    #   4. Repositories (session, payload, deadletter)
    #   5. Domain services (scoring engine, recommendation engine, etc.)
    #   6. Orchestrator (composed from domain services)

    return container
