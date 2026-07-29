"""Mock automation gateway — deterministic local consultation processing.

Used when N8N_ENABLED=false. Wraps the local consultation engine
(ConsultationOrchestrator or LlmConsultationEngine) so all current
frontend functionality continues working without n8n.

Returns consultation responses that match the existing frontend
API contract exactly.
"""

from __future__ import annotations

import logging
from typing import Any

from app.domain.gateway.automation_gateway import (
    ConsultationRequest,
    ConsultationResult,
)

logger = logging.getLogger(__name__)


class MockAutomationGateway:
    """Gateway that processes consultations using a local engine.

    Used for development and testing when N8N_ENABLED=false.
    The engine can be the deterministic ConsultationOrchestrator
    (default) or the LlmConsultationEngine (when LLM_ENABLED=true).
    No external calls are made — all processing stays local.
    """

    def __init__(
        self,
        orchestrator: Any = None,
    ) -> None:
        if orchestrator is None:
            from app.orchestration.orchestrator import ConsultationOrchestrator
            self._orchestrator = ConsultationOrchestrator()
        else:
            self._orchestrator = orchestrator

    async def process_consultation(
        self,
        request: ConsultationRequest,
    ) -> ConsultationResult:
        """Process a consultation turn using the local deterministic engine.

        Delegates to the ConsultationOrchestrator and maps the result
        to the ConsultationResult contract.

        Args:
            request: The consultation request with session context.

        Returns:
            ConsultationResult matching the frontend contract.
        """
        session_state = request.structured_state

        # Preserve session context from the request
        if "session_id" not in session_state:
            session_state["session_id"] = request.session_id

        logger.debug(
            "Mock gateway processing turn: session=%s msg_len=%d",
            request.session_id,
            len(request.user_message),
        )

        # Use the existing deterministic consultation engine
        result = await self._orchestrator.process_turn(
            session_state=session_state,
            visitor_message=request.user_message,
        )

        logger.info(
            "Mock gateway completed: session=%s phase=%s score=%d",
            request.session_id,
            result.conversation_phase,
            result.lead_score.get("score", 0) if result.lead_score else 0,
        )

        return ConsultationResult(
            assistant_message=result.assistant_message,
            conversation_phase=result.conversation_phase,
            business_profile=result.business_profile,
            lead_score=result.lead_score,
            recommendations=result.recommendations,
            completion_percentage=result.completion_percentage,
            next_question=result.next_question,
            is_complete=result.is_complete,
            completion_reason=result.completion_reason,
            analysis_snapshot=result.analysis_snapshot,
            errors=result.errors,
        )

    async def start_consultation(self) -> dict[str, Any]:
        """Start a new consultation using the local engine.

        Returns:
            Dict with session state including greeting message.
        """
        return await self._orchestrator.start_consultation()
