"""Structured output model for LLM consultation responses.

This is the schema passed to OpenAI response_format.

The LLM generates ONLY natural-language fields:
  - assistant_message: Nova's conversational response
  - next_question:    The next question Nova will ask (if any)

All structured business fields (scores, recommendations, phase,
business profile, completion status) come exclusively from the
deterministic ConsultationOrchestrator.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class LlmConsultationOutput(BaseModel):
    """Structured output from an LLM consultation turn.

    Only natural-language fields. Everything else is the
    deterministic engine's responsibility.
    """

    assistant_message: str = Field(..., min_length=1)
    next_question: str | None = None
