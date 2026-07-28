"""Question selector — picks the next discovery question deterministically.

Implements PRD Section 12.6 scoring formula:
    score = scoring_weight * phase_multiplier * recency_penalty

Selects among unfilled, non-declined slots valid for the current phase.
Ties broken by slot order in vocabulary definition.

References: PRD 12.6, PRD FR-26, FR-27
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# Slot-specific question templates
QUESTION_TEMPLATES: dict[str, str] = {
    "industry": "What sector does your business operate in?",
    "business_size": "Roughly how many people are in your team?",
    "pain_points": "Can you tell me more about where that process breaks down?",
    "current_tools": "What are you currently using to manage that?",
    "goals": "What would success look like in six months?",
    "timeline": "When are you hoping to have something running?",
    "budget": "Do you have a budget range in mind for this?",
    "decision_role": "Will you be leading this decision internally?",
    "contact": "If you'd like, I can pass this to a consultant. That needs your name and email.",
}


@dataclass
class SelectedQuestion:
    """The selected next question."""

    slot: str
    template_id: str
    question_text: str
    reason: str = "highest_information_gain"


# Scoring weights for each slot (PRD 12.5)
SLOT_SCORING_WEIGHTS: dict[str, float] = {
    "industry": 10.0,
    "business_size": 10.0,
    "pain_points": 25.0,
    "current_tools": 5.0,
    "goals": 10.0,
    "timeline": 15.0,
    "budget": 15.0,
    "decision_role": 10.0,
    "contact": 0.0,  # gate, not weighted
}

# Phase multipliers (PRD 12.6)
PHASE_MULTIPLIERS: dict[str, float] = {
    "greeting": 0.0,
    "discovery": 1.0,
    "exploration": 0.8,
    "recommendation": 0.0,
    "qualification": 1.0,
    "capture_and_close": 0.0,
}

# Eligible slots per phase (PRD 12.6)
PHASE_ELIGIBLE_SLOTS: dict[str, list[str]] = {
    "greeting": [],
    "discovery": ["industry", "business_size", "pain_points", "current_tools"],
    "exploration": ["pain_points", "goals", "current_tools"],
    "recommendation": ["goals"],
    "qualification": ["timeline", "budget", "decision_role"],
    "capture_and_close": ["contact"],
}

# Slot order for deterministic tie-breaking
_SLOT_ORDER: list[str] = [
    "industry", "business_size", "pain_points", "current_tools",
    "goals", "timeline", "budget", "decision_role", "contact",
]


class QuestionSelector:
    """Deterministic next-question selector.

    Pure function. Given current slot state and phase, returns the
    single next discovery question to ask.
    """

    def __init__(
        self,
        slot_weights: dict[str, float] | None = None,
        phase_multipliers: dict[str, float] | None = None,
        phase_eligible_slots: dict[str, list[str]] | None = None,
    ) -> None:
        self._slot_weights = slot_weights or SLOT_SCORING_WEIGHTS
        self._phase_multipliers = phase_multipliers or PHASE_MULTIPLIERS
        self._phase_eligible_slots = phase_eligible_slots or PHASE_ELIGIBLE_SLOTS

    def select_question(
        self,
        current_phase: str,
        slot_map: Any,
        questions_asked: list[str],
        previous_turn_slot: str | None = None,
    ) -> SelectedQuestion | None:
        """Select the next discovery question.

        Args:
            current_phase: The current conversation phase.
            slot_map: The current slot map with values.
            questions_asked: List of slots already asked.
            previous_turn_slot: Slot asked in the previous turn.

        Returns:
            SelectedQuestion or None if no question needed.
        """
        # Determine eligible slots for this phase
        eligible = self._phase_eligible_slots.get(current_phase, [])

        if not eligible:
            return None

        # Score each eligible slot
        scored_slots: list[tuple[str, float]] = []
        for slot in eligible:
            # Skip if already asked and answered
            if self._is_slot_filled(slot, slot_map):
                continue

            # Skip if declined
            if self._is_slot_declined(slot, slot_map):
                continue

            # Skip if already asked recently (don't repeat)
            if slot in questions_asked:
                continue

            # Compute score
            weight = self._slot_weights.get(slot, 0.0)
            multiplier = self._phase_multipliers.get(current_phase, 0.0)
            recency_penalty = 0.5 if slot == previous_turn_slot else 1.0

            score = weight * multiplier * recency_penalty
            scored_slots.append((slot, score))

        if not scored_slots:
            # Fallback: ask a deepening question about highest-confidence pain
            if hasattr(slot_map, "pain_points") and slot_map.pain_points:
                return SelectedQuestion(
                    slot="pain_points",
                    template_id="pain_points.deepen",
                    question_text="Can you help me understand the impact of that challenge in more detail?",
                    reason="deepening_question",
                )
            return None

        # Sort by score descending, tie-break by slot order
        scored_slots.sort(key=lambda x: (-x[1], _SLOT_ORDER.index(x[0]) if x[0] in _SLOT_ORDER else 999))

        best_slot = scored_slots[0][0]
        question_text = QUESTION_TEMPLATES.get(
            best_slot, "Could you tell me more about that?"
        )

        return SelectedQuestion(
            slot=best_slot,
            template_id=f"{best_slot}.discovery",
            question_text=question_text,
            reason="highest_information_gain",
        )

    @staticmethod
    def _is_slot_filled(slot: str, slot_map: Any) -> bool:
        """Check if a slot has a filled value."""
        if hasattr(slot_map, slot):
            value = getattr(slot_map, slot)
            if value is None:
                return False
            if hasattr(value, "value") and value.value:
                return True
            if isinstance(value, list) and value:
                return True
        return False

    @staticmethod
    def _is_slot_declined(slot: str, slot_map: Any) -> bool:
        """Check if a slot has been declined."""
        if hasattr(slot_map, slot):
            value = getattr(slot_map, slot)
            if hasattr(value, "declined") and value.declined:
                return True
        return False
