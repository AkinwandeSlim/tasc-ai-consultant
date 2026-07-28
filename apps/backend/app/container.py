"""Composition root — dependency injection container.

Constructs concrete adapters and injects them into domain services.
FastAPI dependencies in app/api/deps.py resolve from here.

This module is the only place where the full dependency graph is assembled.
The lifespan module calls container construction after startup checks pass.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.config import Settings


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
    """
    container = Container(settings=settings)

    # TODO: Construct and wire all dependencies following the blueprint:
    #   1. Providers (ChatProvider, EmbeddingProvider)
    #   2. Vector store (ChromaDB adapter)
    #   3. Prompt registry (load templates)
    #   4. Repositories (session, payload, deadletter)
    #   5. Domain services (scoring engine, recommendation engine, etc.)
    #   6. Orchestrator (composed from domain services)

    return container
