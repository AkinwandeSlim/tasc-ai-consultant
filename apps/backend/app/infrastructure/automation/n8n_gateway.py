"""N8n automation gateway — forwards consultation requests to n8n webhook.

Production implementation of the AutomationGateway protocol.
Responsible for:
  - HTTP POST with signed payload
  - Timeout handling (N8N_TIMEOUT_SECONDS)
  - Retry policy with exponential backoff (N8N_MAX_ATTEMPTS)
  - Structured logging of every request/response
  - Error handling for all failure modes
  - Response validation against the expected contract
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from app.core.exceptions import (
    GatewayConnectionError,
    GatewayInvalidResponseError,
    GatewayRejectedError,
    GatewayTimeoutError,
)
from app.domain.gateway.automation_gateway import (
    ConsultationRequest,
    ConsultationResult,
)
from app.infrastructure.automation.signing import build_signature_headers

logger = logging.getLogger(__name__)

# Expected acknowledgement structure from n8n
_N8N_ACK_SCHEMA = {"received", "consultation_id"}


class N8nAutomationGateway:
    """Gateway that forwards consultation requests to an n8n webhook.

    All external communication flows through this class. The rest of the
    application is isolated from n8n implementation details.

    Usage:
        gateway = N8nAutomationGateway(
            webhook_url="https://n8n.example.com/webhook/consult",
            shared_secret="s3cret",
            signing_secret="s1gn1ng",
            http_client=httpx.AsyncClient(),
        )
        result = await gateway.process_consultation(request)
    """

    def __init__(
        self,
        webhook_url: str,
        shared_secret: str,
        signing_secret: str,
        http_client: httpx.AsyncClient,
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
        backoff_base_seconds: float = 2.0,
    ) -> None:
        if not webhook_url:
            raise ValueError("webhook_url is required for N8nAutomationGateway")

        self._webhook_url = webhook_url
        self._shared_secret = shared_secret
        self._signing_secret = signing_secret
        self._client = http_client
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._backoff_base = backoff_base_seconds

    async def process_consultation(
        self,
        request: ConsultationRequest,
    ) -> ConsultationResult:
        """Forward a consultation turn to the n8n webhook.

        Implements retry with exponential backoff and jitter.
        Returns the parsed response or raises a GatewayError.

        Args:
            request: The consultation request with full session context.

        Returns:
            ConsultationResult parsed from the n8n response.

        Raises:
            GatewayConnectionError: If the webhook is unreachable.
            GatewayTimeoutError: If the request times out.
            GatewayInvalidResponseError: If the response is malformed.
            GatewayRejectedError: If the webhook returns a non-retryable 4xx.
        """
        payload = self._build_payload(request)
        raw_body = json.dumps(payload, default=str).encode("utf-8")

        correlation_id = request.structured_state.get("correlation_id", request.session_id)

        headers = build_signature_headers(
            payload=raw_body,
            shared_secret=self._shared_secret,
            signing_secret=self._signing_secret,
            correlation_id=correlation_id,
        )

        last_error: Exception | None = None
        attempt = 0

        while attempt < self._max_retries:
            attempt += 1
            start_time = time.monotonic()

            try:
                logger.info(
                    "N8n dispatch attempt %d/%d: session=%s webhook=%s",
                    attempt,
                    self._max_retries,
                    request.session_id,
                    self._webhook_url,
                )

                response = await self._client.post(
                    self._webhook_url,
                    content=raw_body,
                    headers=headers,
                    timeout=self._timeout,
                )

                duration = time.monotonic() - start_time
                status = response.status_code

                # Success (2xx) — parse and return
                if 200 <= status < 300:
                    return self._parse_response(
                        response=response,
                        session_id=request.session_id,
                        duration=duration,
                        attempt=attempt,
                    )

                # 409 Conflict (idempotency) — treat as success
                if status == 409:
                    logger.info(
                        "N8n idempotency match (409): session=%s duration=%.2fs",
                        request.session_id,
                        duration,
                    )
                    return self._build_idempotency_result(request)

                # 401 or 403 — auth failure, do not retry
                if status in (401, 403):
                    logger.error(
                        "N8n auth rejected (status=%d): session=%s duration=%.2fs",
                        status,
                        request.session_id,
                        duration,
                    )
                    raise GatewayRejectedError(
                        message=f"n8n webhook rejected the request with status {status}",
                    )

                # Other 4xx — client error, do not retry
                if 400 <= status < 500:
                    logger.error(
                        "N8n client error (status=%d): session=%s duration=%.2fs body=%s",
                        status,
                        request.session_id,
                        duration,
                        response.text[:500],
                    )
                    raise GatewayRejectedError(
                        message=f"n8n webhook returned status {status}",
                    )

                # 5xx — retryable
                duration = time.monotonic() - start_time
                logger.warning(
                    "N8n server error (status=%d): session=%s attempt=%d duration=%.2fs",
                    status,
                    request.session_id,
                    attempt,
                    duration,
                )
                last_error = GatewayConnectionError(
                    message=f"n8n webhook returned status {status}",
                )

            except httpx.TimeoutException:
                duration = time.monotonic() - start_time
                logger.warning(
                    "N8n timeout: session=%s attempt=%d duration=%.2fs",
                    request.session_id,
                    attempt,
                    duration,
                )
                last_error = GatewayTimeoutError(
                    message=f"n8n webhook timed out after {self._timeout}s",
                )

            except httpx.ConnectError as e:
                duration = time.monotonic() - start_time
                logger.error(
                    "N8n connection failed: session=%s attempt=%d duration=%.2fs error=%s",
                    request.session_id,
                    attempt,
                    duration,
                    str(e),
                )
                last_error = GatewayConnectionError(
                    message="Could not connect to the n8n webhook",
                )

            except (GatewayRejectedError, GatewayInvalidResponseError):
                # Non-retryable — re-raise immediately
                raise

            except Exception as e:
                duration = time.monotonic() - start_time
                logger.exception(
                    "N8n unexpected error: session=%s attempt=%d duration=%.2fs",
                    request.session_id,
                    attempt,
                    duration,
                )
                last_error = GatewayConnectionError(
                    message=f"Unexpected gateway error: {str(e)}",
                )

            # If we still have retries, wait with exponential backoff + jitter
            if attempt < self._max_retries:
                import random

                sleep_seconds = self._backoff_base * (2 ** (attempt - 1))
                jitter = random.uniform(0, 0.5 * sleep_seconds)  # noqa: S311
                total_sleep = sleep_seconds + jitter

                logger.debug(
                    "N8n retry in %.2fs: session=%s attempt=%d/%d",
                    total_sleep,
                    request.session_id,
                    attempt,
                    self._max_retries,
                )
                await self._async_sleep(total_sleep)

        # All retries exhausted
        logger.error(
            "N8n dispatch failed after %d attempts: session=%s",
            self._max_retries,
            request.session_id,
        )

        if last_error:
            raise last_error

        raise GatewayConnectionError(
            message="n8n webhook did not return a successful response",
        )

    def _build_payload(self, request: ConsultationRequest) -> dict[str, Any]:
        """Build the JSON payload to send to n8n.

        Includes all context needed for the n8n workflow to process
        the consultation turn.

        Args:
            request: The consultation request.

        Returns:
            Dict payload for the n8n webhook.
        """
        return {
            "session_id": request.session_id,
            "user_message": request.user_message,
            "conversation_history": request.conversation_history,
            "structured_state": request.structured_state,
            "timestamp": request.timestamp or time.time(),
            "simulation_mode": request.simulation_mode,
        }

    def _parse_response(
        self,
        response: httpx.Response,
        session_id: str,
        duration: float,
        attempt: int,
    ) -> ConsultationResult:
        """Parse and validate the n8n webhook response.

        Args:
            response: The HTTP response from n8n.
            session_id: The consultation session ID.
            duration: Request duration in seconds.
            attempt: The attempt number.

        Returns:
            Parsed ConsultationResult.

        Raises:
            GatewayInvalidResponseError: If the response is malformed.
        """
        try:
            data = response.json()
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(
                "N8n invalid JSON response: session=%s status=%d error=%s body=%s",
                session_id,
                response.status_code,
                str(e),
                response.text[:500],
            )
            raise GatewayInvalidResponseError(
                message="n8n webhook returned invalid JSON",
            ) from e

        if not isinstance(data, dict):
            logger.error(
                "N8n non-dict response: session=%s type=%s body=%s",
                session_id,
                type(data).__name__,
                str(data)[:500],
            )
            raise GatewayInvalidResponseError(
                message="n8n webhook returned an unexpected response format",
            )

        logger.info(
            "N8n dispatch success: session=%s status=%d duration=%.2fs attempt=%d/%d",
            session_id,
            response.status_code,
            duration,
            attempt,
            self._max_retries,
        )

        assistant_message = data.get("assistant_message", "")
        conversation_phase = data.get("conversation_phase", "discovery")

        return ConsultationResult(
            assistant_message=assistant_message,
            conversation_phase=conversation_phase,
            business_profile=data.get("business_profile"),
            lead_score=data.get("lead_score"),
            recommendations=data.get("recommendations", []),
            completion_percentage=data.get("completion_percentage", 0),
            next_question=data.get("next_question"),
            is_complete=data.get("conversation_finished", False),
            completion_reason=data.get("completion_reason", ""),
            analysis_snapshot=data.get("analysis_snapshot"),
            errors=data.get("errors", []),
        )

    def _build_idempotency_result(
        self,
        request: ConsultationRequest,
    ) -> ConsultationResult:
        """Build a result for an idempotency match (409 response).

        Args:
            request: The original consultation request.

        Returns:
            A ConsultationResult indicating continuation.
        """
        return ConsultationResult(
            assistant_message="",
            conversation_phase=request.structured_state.get("phase", "discovery"),
            business_profile=request.structured_state.get("business_profile"),
            lead_score=request.structured_state.get("lead_score"),
            recommendations=request.structured_state.get("recommendations", []),
            completion_percentage=request.structured_state.get("completion_percentage", 0),
            is_complete=False,
        )

    async def _async_sleep(self, seconds: float) -> None:
        """Async sleep helper for retry backoff."""
        import asyncio

        await asyncio.sleep(seconds)
