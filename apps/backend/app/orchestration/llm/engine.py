"""LLM Consultation Engine — natural-language enhancement via ChatProvider.

This engine has the same public interface as ConsultationOrchestrator
(process_turn, start_consultation) so it can be swapped in via DI.

Flow:
  1. Always call the deterministic ConsultationOrchestrator for the full turn.
  2. If the LLM is available, call ChatProvider.complete_structured() to
     generate only assistant_message and next_question.
  3. Replace those two fields in the deterministic result.
  4. On any failure (provider, timeout, JSON, schema) return the complete
     deterministic result unchanged.

The deterministic engine is the source of truth for everything except
natural-language wording. The LLM never sets scores, bands,
recommendations, phase, business profile, or completion status.

References: Sprint 6.3 requirement
"""

from __future__ import annotations

import logging
from typing import Any

from app.infrastructure.providers.base import ChatProvider, ChatRequest
from app.orchestration.llm.models import LlmConsultationOutput

logger = logging.getLogger(__name__)

# System prompt — asks only for natural-language fields.
_LLM_SYSTEM_PROMPT = """You are Nova, an expert AI Business Consultant for Trizen Ventures.

Your role is to continue the conversation naturally based on the business
context and conversation history provided below.

Rules:
- Be conversational, professional, and helpful.
- Acknowledge what the user has said before moving the conversation forward.
- Never invent facts about the user's business that aren't in the profile.
- Never output markdown, bullet lists, or formatting — plain text only.
- Do NOT suggest services, scores, phases, or complete the consultation.
  Those are handled by the system automatically.
- If you do not know what to say, ask a relevant follow-up question.
"""


def _build_llm_messages(
    visitor_message: str,
    current_phase: str,
    business_profile: dict[str, Any] | None,
    conversation_history: list[dict[str, Any]] | None,
) -> list[dict[str, str]]:
    """Build the messages list for the LLM chat completion.

    Args:
        visitor_message: The user's current message.
        current_phase: Current consultation phase.
        business_profile: Current business profile dict (may be empty).
        conversation_history: Prior message history (role/content pairs).

    Returns:
        List of message dicts for the ChatRequest.
    """
    messages: list[dict[str, str]] = [{"role": "system", "content": _LLM_SYSTEM_PROMPT}]

    # Add business context
    context_parts = [f"Current consultation phase: {current_phase}"]
    if business_profile:
        context_parts.append("Known business profile:")
        for key in ("industry", "company_size"):
            val = business_profile.get(key)
            if val:
                context_parts.append(f"  {key}: {val}")
        pain_points = business_profile.get("pain_points", [])
        if pain_points:
            labels = ", ".join(p.get("label", "") for p in pain_points if isinstance(p, dict))
            if labels:
                context_parts.append(f"  Pain points: {labels}")

    messages.append({"role": "system", "content": "\n".join(context_parts)})

    # Conversation history (last 8 turns)
    if conversation_history:
        for msg in conversation_history[-8:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant"):
                messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": visitor_message})
    return messages


class LlmConsultationEngine:
    """Consultation engine that enhances deterministic output with LLM wording.

    Implements the same public interface as ConsultationOrchestrator
    so it can be injected into MockAutomationGateway interchangeably.

    The deterministic ConsultationOrchestrator is always called first
    and is the source of truth for all structured fields. The LLM
    only generates assistant_message and next_question.
    """

    def __init__(
        self,
        chat_provider: ChatProvider | None,
        deterministic_engine: Any,
    ) -> None:
        """Initialise the LLM consultation engine.

        Args:
            chat_provider: A ChatProvider instance, or None if not configured.
            deterministic_engine: The ConsultationOrchestrator instance.
        """
        self._chat_provider = chat_provider
        self._deterministic = deterministic_engine

    @property
    def is_llm_available(self) -> bool:
        """Whether the LLM provider is configured and available."""
        return self._chat_provider is not None

    async def start_consultation(self) -> dict[str, Any]:
        """Start a new consultation via the deterministic engine only.

        The LLM does not generate greetings — the deterministic
        engine handles the initial greeting.
        """
        return await self._deterministic.start_consultation()

    async def process_turn(
        self,
        session_state: dict[str, Any],
        visitor_message: str,
        client_turn_id: str | None = None,
    ) -> Any:
        """Process a turn: deterministic engine first, then LLM wording.

        Args:
            session_state: The current session state.
            visitor_message: The visitor's message.
            client_turn_id: Optional client-side turn ID.

        Returns:
            OrchestrationResult from the deterministic engine, with
            assistant_message and next_question optionally replaced
            by LLM output.
        """
        deterministic_result = await self._deterministic.process_turn(
            session_state=session_state,
            visitor_message=visitor_message,
            client_turn_id=client_turn_id,
        )

        if not self._chat_provider:
            return deterministic_result

        return await self._try_llm_enhancement(
            deterministic_result=deterministic_result,
            session_state=session_state,
            visitor_message=visitor_message,
        )

    async def _try_llm_enhancement(
        self,
        deterministic_result: Any,
        session_state: dict[str, Any],
        visitor_message: str,
    ) -> Any:
        """Try to enhance the deterministic result with LLM wording.

        On any failure, returns the deterministic result unchanged.
        """
        assert self._chat_provider is not None

        current_phase = session_state.get("phase", "greeting")
        business_profile = session_state.get("business_profile", {})
        conversation_history = session_state.get("messages", [])

        try:
            messages = _build_llm_messages(
                visitor_message=visitor_message,
                current_phase=current_phase,
                business_profile=business_profile,
                conversation_history=conversation_history,
            )

            request = ChatRequest(
                messages=messages,
                max_tokens=500,
            )

            structured = await self._chat_provider.complete_structured(
                request=request,
                schema=LlmConsultationOutput,
            )

            output = LlmConsultationOutput(**structured.content)

            # Replace only natural-language fields
            deterministic_result.assistant_message = output.assistant_message
            if output.next_question:
                deterministic_result.next_question = output.next_question

        except Exception:
            logger.info(
                "LLM enhancement failed for session=%s — using deterministic result",
                session_state.get("session_id", "unknown"),
            )

        return deterministic_result
