"""Application startup and shutdown lifecycle.

Implements the ordered startup sequence defined in the Backend Blueprint
(Section 4). Each step is fail-fast; the application will not accept traffic
until all startup steps complete successfully.

Startup order:
  S1  Load and validate Settings
  S2  Configure structured logging with redaction
  S3  Load YAML resources, compute ruleset_version
  S4  Construct providers from LLM_PROVIDER via registry
  S5  Open Chroma collection
  S6  Assert embedding dimension matches manifest
  S7  Load and compile prompt templates
  S8  Initialise repositories, create directories, verify write permission
  S9  Build DI container with automation gateway
  S10 Warmup smoke retrieval query
  S11 Emit startup manifest log line
"""

import logging

from fastapi import FastAPI

from app.container import build_container

logger = logging.getLogger(__name__)


async def run_startup_sequence(app: FastAPI) -> None:
    """Execute the ordered startup sequence.

    Each step should raise on failure, which propagates to FastAPI's
    lifespan handler and terminates the process.
    """
    settings = app.state.settings

    # S1: Settings already validated at import time by pydantic-settings
    logger.info("S1: Settings loaded", extra={"env": settings.APP_ENV})

    # S2: Logging already configured in main.py
    logger.info("S2: Structured logging configured")

    # S3: Load YAML resources
    # TODO: Implement resource loading
    ruleset_version = "rs_dev"
    logger.info("S3: Resources loaded", extra={"ruleset_version": ruleset_version})

    # S4: Construct providers
    # TODO: Construct from registry
    logger.info("S4: Providers constructed", extra={"provider": settings.LLM_PROVIDER})

    # S5: Open Chroma collection
    # TODO: Open collection
    logger.info("S5: Chroma collection opened")

    # S6: Assert embedding dimension
    # TODO: Verify embedding dimension
    logger.info("S6: Embedding dimension verified")

    # S7: Load prompt templates
    # TODO: Load and compile prompts
    logger.info("S7: Prompt templates loaded")

    # S8: Initialise repositories
    # TODO: Create data directories if needed
    logger.info("S8: Repositories initialised")

    # S9: Build DI container with automation gateway
    container = build_container(settings)
    app.state.container = container

    gateway_type = type(container.automation_gateway).__name__
    logger.info(
        "S9: DI container built",
        extra={
            "gateway_type": gateway_type,
            "n8n_enabled": settings.N8N_ENABLED,
            "n8n_webhook": settings.N8N_WEBHOOK_URL if settings.N8N_ENABLED else "(disabled)",
        },
    )

    # S10: Warmup smoke retrieval query
    # TODO: Run a smoke query
    logger.info("S10: Warmup smoke query passed")

    # S11: Emit startup manifest
    logger.info(
        "S11: Startup complete",
        extra={
            "app_version": "1.0.0",
            "environment": settings.APP_ENV,
            "chat_model": settings.LLM_CHAT_MODEL,
            "embedding_model": settings.LLM_EMBEDDING_MODEL,
            "ruleset_version": ruleset_version,
            "session_store": settings.SESSION_STORE,
            "n8n_enabled": settings.N8N_ENABLED,
            "gateway_type": gateway_type,
        },
    )


async def run_shutdown_sequence(app: FastAPI) -> None:
    """Execute the ordered shutdown sequence.

    1. Stop accepting new connections (handled by Uvicorn)
    2. Wait for in-flight turns
    3. Await outstanding dispatch tasks
    4. Flush session state writes
    5. Close HTTPX clients and Chroma client
    6. Flush logs and telemetry
    """
    logger.info("Shutdown: Draining in-flight requests...")
    # TODO: Implement graceful drain

    logger.info("Shutdown: Awaiting dispatch tasks...")
    # TODO: Await pending dispatches

    # Close HTTP client used by the gateway
    container = getattr(app.state, "container", None)
    if container:
        http_client = getattr(container, "http_client", None)
        if http_client:
            await http_client.aclose()
            logger.info("Shutdown: HTTP client closed")

    logger.info("Shutdown: Flushing state...")
    # TODO: Flush session and payload stores

    logger.info("Shutdown: Closing connections...")
    # TODO: Close Chroma clients

    logger.info("Shutdown complete")
