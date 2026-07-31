"""N8n automation gateway — processes consultation locally, dispatches to n8n.

The deterministic engine (or LlmConsultationEngine) processes every
consultation turn. The result is then dispatched to the n8n webhook
for business automation (Google Sheets, Gmail, Telegram). The n8n
response is logged but never used to derive consultation fields.

This ensures:
  - The consultation response is always computed by tested Python code.
  - n8n failures never block the frontend from getting a response.
  - n8n owns only business automation, never AI reasoning.

References: Sprint 6.1 architecture, README "Why AI lives in FastAPI"
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from app.domain.gateway.automation_gateway import (
    ConsultationRequest,
    ConsultationResult,
)
from app.infrastructure.automation.signing import build_signature_headers

logger = logging.getLogger(__name__)


class N8nAutomationGateway:
    """Gateway that processes consultation locally and dispatches to n8n.

    The turn is processed by the local consultation engine first.
    The full result is then dispatched to the n8n webhook for business
    automation (sheets, email, notifications). The n8n response is
    acknowledged but NOT used to formulate the consultation result.

    n8n dispatch failures are logged and swallowed — the frontend
    always gets the local consultation result.
    """

    def __init__(
        self,
        webhook_url: str,
        shared_secret: str,
        signing_secret: str,
        http_client: httpx.AsyncClient,
        orchestrator: Any = None,
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
        backoff_base_seconds: float = 2.0,
    ) -> None:
        if not webhook_url:
            raise ValueError("webhook_url is required for N8nAutomationGateway")

        if orchestrator is None:
            from app.orchestration.orchestrator import ConsultationOrchestrator

            self._orchestrator = ConsultationOrchestrator()
        else:
            self._orchestrator = orchestrator

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
        """Process a consultation turn locally and dispatch to n8n.

        Flow:
          1. Process the turn via the local deterministic/LLM engine.
          2. Map the result to a ConsultationResult.
          3. Dispatch the enriched payload to the n8n webhook.
          4. Return the local result — n8n response is advisory only.

        Args:
            request: The consultation request with session context.

        Returns:
            ConsultationResult from the local engine.

        Raises:
            Never raises — n8n dispatch failures are logged and swallowed.
        """
        # 1. Process the turn locally
        session_state = request.structured_state
        if "session_id" not in session_state:
            session_state["session_id"] = request.session_id

        result = await self._orchestrator.process_turn(
            session_state=session_state,
            visitor_message=request.user_message,
        )

        consultation_result = ConsultationResult(
            assistant_message=result.assistant_message,
            conversation_phase=result.conversation_phase,
            business_profile=result.business_profile,
            lead_score=result.lead_score,
            recommendations=result.recommendations or [],
            completion_percentage=result.completion_percentage,
            next_question=result.next_question,
            is_complete=result.is_complete,
            completion_reason=result.completion_reason,
            analysis_snapshot=getattr(result, "analysis_snapshot", None),
            errors=getattr(result, "errors", []),
        )

        # 2. Dispatch the enriched payload to n8n (fire-and-forget)
        await self._dispatch_to_n8n(request, consultation_result)

        return consultation_result

    async def _dispatch_to_n8n(
        self,
        request: ConsultationRequest,
        consultation_result: ConsultationResult,
    ) -> None:
        """Dispatch the consultation result to the n8n webhook.

        Failures are logged and swallowed — they never reach the caller.

        Args:
            request: The original consultation request.
            consultation_result: The locally-computed consultation result.
        """
        payload = self._build_payload(request, consultation_result)
        raw_body = json.dumps(payload, default=str).encode("utf-8")

        correlation_id = request.structured_state.get(
            "correlation_id", request.session_id
        )

        headers = build_signature_headers(
            payload=raw_body,
            shared_secret=self._shared_secret,
            signing_secret=self._signing_secret,
            correlation_id=correlation_id,
        )

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

                if 200 <= status < 300:
                    logger.info(
                        "N8n dispatch success: session=%s status=%d duration=%.2fs attempt=%d/%d",
                        request.session_id,
                        status,
                        duration,
                        attempt,
                        self._max_retries,
                    )
                    return  # Success — done

                if status == 409:
                    logger.info(
                        "N8n idempotency match (409): session=%s duration=%.2fs",
                        request.session_id,
                        duration,
                    )
                    return

                if status in (401, 403):
                    logger.error(
                        "N8n auth rejected (status=%d): session=%s duration=%.2fs",
                        status,
                        request.session_id,
                        duration,
                    )
                    return  # Non-retryable

                if 400 <= status < 500:
                    logger.error(
                        "N8n client error (status=%d): session=%s duration=%.2fs body=%s",
                        status,
                        request.session_id,
                        duration,
                        response.text[:500],
                    )
                    return  # Non-retryable

                logger.warning(
                    "N8n server error (status=%d): session=%s attempt=%d duration=%.2fs",
                    status,
                    request.session_id,
                    attempt,
                    duration,
                )

            except httpx.TimeoutException:
                duration = time.monotonic() - start_time
                logger.warning(
                    "N8n timeout: session=%s attempt=%d duration=%.2fs",
                    request.session_id,
                    attempt,
                    duration,
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

            except Exception:
                duration = time.monotonic() - start_time
                logger.exception(
                    "N8n unexpected error: session=%s attempt=%d duration=%.2fs",
                    request.session_id,
                    attempt,
                    duration,
                )

            # Retry with exponential backoff + jitter
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

        logger.error(
            "N8n dispatch failed after %d attempts: session=%s — result already returned to frontend",
            self._max_retries,
            request.session_id,
        )

    def _build_payload(
        self,
        request: ConsultationRequest,
        consultation_result: ConsultationResult,
    ) -> dict[str, Any]:
        """Build the JSON payload to send to n8n.

        Includes the full consultation result with session context,
        so n8n has everything it needs for business automation.

        The payload shape matches what the n8n Code node
        (Validate & Normalize) expects: lead_qualification, contact,
        conversation, business_profile, etc.

        Args:
            request: The original consultation request.
            consultation_result: The locally-computed consultation result.

        Returns:
            Dict payload for the n8n webhook.
        """
        # Map lead_score → lead_qualification for n8n contract
        lead_score = consultation_result.lead_score or {}
        lead_qualification = {
            "band": lead_score.get("band", "exploring"),
            "level": lead_score.get("band", "exploring"),
            "score": lead_score.get("score", 0),
            "justification": lead_score.get("justification", ""),
        }

        # Extract contact from business_profile (now includes contact_name/email/company)
        bp = consultation_result.business_profile
        if isinstance(bp, dict):
            contact = {
                "name": bp.get("contact_name"),
                "email": bp.get("contact_email") if bp.get("has_contact") else None,
                "company": bp.get("contact_company"),
            }
        elif bp is not None:
            contact = {
                "name": getattr(getattr(bp, "contact_name", None), "value", None),
                "email": getattr(getattr(bp, "contact_email", None), "value", None),
                "company": getattr(getattr(bp, "contact_company", None), "value", None),
            }
        else:
            contact = {}

        return {
            "session_id": request.session_id,
            "consultation_id": request.session_id,
            "user_message": request.user_message,
            "conversation_history": request.conversation_history,
            "assistant_message": consultation_result.assistant_message,
            "conversation_phase": consultation_result.conversation_phase,
            "business_profile": bp,
            "lead_score": lead_score,
            "lead_qualification": lead_qualification,
            "contact": contact,
            "conversation": {
                "message": consultation_result.assistant_message,
                "phase": consultation_result.conversation_phase,
                "turn_count": len(request.conversation_history or []) // 2 + 1,
            },
            "recommendations": consultation_result.recommendations or [],
            "completion_percentage": consultation_result.completion_percentage,
            "next_question": consultation_result.next_question,
            "conversation_finished": consultation_result.is_complete,
            "completion_reason": consultation_result.completion_reason,
            "response_type": "consultation_turn",
            "turn_index": len(request.conversation_history or []) // 2 + 1,
            "structured_state": request.structured_state,
            "timestamp": request.timestamp or time.time(),
            "simulation_mode": request.simulation_mode,
        }

    async def start_consultation(self) -> dict[str, Any]:
        """Start a new consultation using the local engine.

        Returns:
            Dict with session state including greeting message.
        """
        return await self._orchestrator.start_consultation()

    async def _async_sleep(self, seconds: float) -> None:
        """Async sleep helper for retry backoff."""
        import asyncio

        await asyncio.sleep(seconds)
