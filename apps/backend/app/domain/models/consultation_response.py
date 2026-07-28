"""Consultation response contract — structured output per turn.

Every turn produces a structured response with all fields needed
for the frontend and Live Analysis Panel.

References: PRD Section 6.2, Sprint 3 requirements
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConsultationResponse:
    """Complete consultation turn response.

    Every response includes all fields — null/empty for values
    not yet established. This gives a consistent contract for
    the frontend to consume.

    Fields:
        assistant_message: Nova's response text.
        conversation_phase: Current phase (greeting, discovery, etc.).
        business_profile: Current understanding of the business.
        lead_score: Deterministic score with breakdown.
        recommendations: Ranked service recommendations.
        completion_percentage: 0-100 progress indicator.
        next_question: The next question Nova will ask.
    """

    assistant_message: str = ""
    conversation_phase: str = "greeting"
    business_profile: dict[str, Any] | None = None
    lead_score: dict[str, Any] | None = None
    recommendations: list[dict[str, Any]] = field(default_factory=list)
    completion_percentage: int = 0
    next_question: str | None = None
    is_complete: bool = False
    completion_reason: str = ""
    analysis_snapshot: dict[str, Any] | None = None
    turn_index: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a dict matching the API contract.

        Returns:
            Dict with all response fields.
        """
        return {
            "assistant_message": self.assistant_message,
            "conversation_phase": self.conversation_phase,
            "business_profile": self.business_profile or {},
            "lead_score": self.lead_score or {
                "score": None,
                "band": "exploring",
                "confidence": 0.0,
                "next_contributor": None,
            },
            "recommendations": self.recommendations,
            "completion_percentage": self.completion_percentage,
            "next_question": self.next_question,
            "is_complete": self.is_complete,
            "completion_reason": self.completion_reason,
            "analysis_snapshot": self.analysis_snapshot,
            "turn_index": self.turn_index,
        }
