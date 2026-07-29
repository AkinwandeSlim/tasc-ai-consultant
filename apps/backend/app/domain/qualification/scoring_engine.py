"""Scoring engine — deterministic lead score computation (FR-30 to FR-36).

Pure function: given slots and engagement signals, returns a LeadScore
with component breakdown. No model calls, no I/O.

References: PRD FR-30 to FR-36, PRD Section 14, AI Blueprint Section 5
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.domain.models.score import (
    LeadScore,
    QualificationConfidence,
    ScoreComponent,
    ScoringBreakdown,
)
from app.domain.qualification.banding import score_to_band
from app.domain.qualification.components import (
    compute_authority,
    compute_budget,
    compute_engagement,
    compute_fit,
    compute_need_clarity,
    compute_urgency,
)
from app.domain.qualification.overrides import apply_overrides

# Default scoring weights matching PRD Section 14.2
DEFAULT_COMPONENT_WEIGHTS: dict[str, int] = {
    "need_clarity": 25,
    "fit": 20,
    "urgency": 15,
    "budget": 15,
    "authority": 10,
    "engagement": 15,
}


@dataclass
class ScoringInput:
    """Input data for the scoring engine."""

    pain_points: list[Any] = field(default_factory=list)
    service_mappings: list[str] = field(default_factory=list)
    has_case_study_coverage: bool = False
    timeline_value: str | None = None
    budget_value: str | None = None
    authority_value: str | None = None
    visitor_turn_count: int = 0
    asked_company_question: bool = False
    responded_to_recommendation: bool = False
    volunteered_contact: bool = False
    anti_persona: bool = False
    human_requested: bool = False
    has_contact: bool = False
    is_abandoned: bool = False
    is_terminated: bool = False
    business_size_value: str | None = None
    slot_confidences: dict[str, float] = field(default_factory=dict)
    filled_slot_count: int = 0


class ScoringEngine:
    """Deterministic lead scoring engine.

    Pure function — given slot data and engagement signals, returns
    a fully computed LeadScore with component breakdown, overrides,
    band, confidence, and next-contributor analysis.
    """

    def __init__(
        self,
        threshold_warm: int = 35,
        threshold_qualified: int = 60,
        threshold_hot: int = 80,
        component_weights: dict[str, int] | None = None,
    ) -> None:
        self._threshold_warm = threshold_warm
        self._threshold_qualified = threshold_qualified
        self._threshold_hot = threshold_hot
        self._weights = component_weights or DEFAULT_COMPONENT_WEIGHTS

    def compute(self, input_data: ScoringInput) -> tuple[LeadScore, ScoringBreakdown]:
        """Compute a deterministic lead score.

        Args:
            input_data: All signals and slot data for scoring.

        Returns:
            Tuple of (LeadScore, ScoringBreakdown) with full breakdown.
        """
        # 1. Compute each component
        need_clarity = compute_need_clarity(input_data.pain_points)
        fit = compute_fit(
            has_service_mapping=len(input_data.service_mappings) > 0,
            has_case_study_coverage=input_data.has_case_study_coverage,
            weak_mapping=len(input_data.service_mappings) == 1,
        )
        urgency = compute_urgency(input_data.timeline_value)
        budget = compute_budget(input_data.budget_value)
        authority = compute_authority(input_data.authority_value)
        engagement = compute_engagement(
            visitor_turn_count=input_data.visitor_turn_count,
            asked_company_question=input_data.asked_company_question,
            responded_to_recommendation=input_data.responded_to_recommendation,
            volunteered_contact=input_data.volunteered_contact,
        )

        components = [
            ScoreComponent(
                name="need_clarity", awarded=need_clarity.awarded,
                max=need_clarity.max_points, basis=need_clarity.basis,
                weight=1.0,
            ),
            ScoreComponent(
                name="fit", awarded=fit.awarded,
                max=fit.max_points, basis=fit.basis,
                weight=1.0,
            ),
            ScoreComponent(
                name="urgency", awarded=urgency.awarded,
                max=urgency.max_points, basis=urgency.basis,
                weight=1.0,
            ),
            ScoreComponent(
                name="budget", awarded=budget.awarded,
                max=budget.max_points, basis=budget.basis,
                weight=1.0,
            ),
            ScoreComponent(
                name="authority", awarded=authority.awarded,
                max=authority.max_points, basis=authority.basis,
                weight=1.0,
            ),
            ScoreComponent(
                name="engagement", awarded=engagement.awarded,
                max=engagement.max_points, basis=engagement.basis,
                weight=1.0,
            ),
        ]

        # 2. Compute raw score
        raw_score = sum(c.awarded for c in components)
        raw_score = min(max(raw_score, 0), 100)

        # 3. Compute band
        band = score_to_band(
            raw_score,
            threshold_warm=self._threshold_warm,
            threshold_qualified=self._threshold_qualified,
            threshold_hot=self._threshold_hot,
        )

        # 4. Apply overrides
        override_result = apply_overrides(
            raw_score=raw_score,
            band=band,
            visitor_turn_count=input_data.visitor_turn_count,
            anti_persona=input_data.anti_persona,
            human_requested=input_data.human_requested,
            has_contact=input_data.has_contact,
            budget_band=input_data.budget_value,
            timeline=input_data.timeline_value,
            business_size_value=input_data.business_size_value,
            decision_role_value=input_data.authority_value,
            is_abandoned=input_data.is_abandoned,
            is_terminated=input_data.is_terminated,
        )

        final_band = override_result.force_band or band

        # 5. Compute qualification confidence
        confidence = self._compute_confidence(
            components, input_data.slot_confidences,
        )

        # 6. Find next contributor
        next_contributor, next_headroom = self._find_next_contributor(components, band)

        # 7. Build justification
        justification = self._build_justification(components, raw_score, final_band, override_result)

        score = LeadScore(
            score=raw_score if final_band != "not_a_lead" else 0,
            raw_score=raw_score,
            band=final_band,
            confidence=confidence.overall,
            components=components,
            applied_overrides=override_result.applied_overrides,
            next_contributor=next_contributor,
            justification=justification,
            disqualified=override_result.disqualified,
            partial=override_result.flag_partial,
        )

        breakdown = ScoringBreakdown(
            total=score.score,
            components=components,
            applied_overrides=override_result.applied_overrides,
            next_contributor=next_contributor,
            next_contributor_headroom=next_headroom,
            band=final_band,
            justification=justification,
        )

        return score, breakdown

    def _compute_confidence(
        self,
        components: list[ScoreComponent],
        slot_confidences: dict[str, float],
    ) -> QualificationConfidence:
        """Compute qualification confidence from evidence quality."""
        # Based on slot confidences and component fill
        filled_components = [c for c in components if c.awarded > 0]
        filled_slots = {k: v for k, v in slot_confidences.items() if v > 0}

        if not filled_components:
            return QualificationConfidence(
                overall=0.0,
                field_confidences=slot_confidences,
                coverage=0.0,
                effect="briefing_flag_only",
            )

        # Average confidence from filled slots
        mean_slot_conf = (
            sum(filled_slots.values()) / len(filled_slots)
            if filled_slots else 0.0
        )

        # Coverage factor: proportion of max possible score achieved
        max_possible = sum(c.max for c in components)
        total_awarded = sum(c.awarded for c in components)
        coverage = total_awarded / max_possible if max_possible > 0 else 0.0

        # Overall confidence = mean slot confidence * coverage factor
        overall = mean_slot_conf * (0.5 + 0.5 * coverage)

        # Find uncertainties
        uncertainties: list[str] = []
        for c in components:
            if c.awarded == 0 and c.max > 0:
                uncertainties.append(f"{c.name} not established")

        return QualificationConfidence(
            overall=min(overall, 1.0),
            field_confidences=slot_confidences,
            coverage=min(coverage, 1.0),
            uncertainties=uncertainties,
            effect="briefing_flag_only",
        )

    def _find_next_contributor(
        self,
        components: list[ScoreComponent],
        current_band: str,
    ) -> tuple[str | None, int]:
        """Find the component with the most headroom to increase the score.

        Returns:
            Tuple of (next_contributor_name, headroom_points).
        """
        # Skip engagement for next contributor (it's retrospective)
        best_component: ScoreComponent | None = None
        most_headroom = 0

        for c in components:
            if c.name == "engagement":
                continue
            headroom = c.remaining
            if headroom > most_headroom:
                most_headroom = headroom
                best_component = c

        if best_component:
            display_name = best_component.name.replace("_", " ").title()
            return f"{display_name} not yet discussed", most_headroom

        return None, 0

    @staticmethod
    def _build_justification(
        components: list[ScoreComponent],
        score: int,
        band: str,
        override_result: Any,
    ) -> str:
        """Build a human-readable justification string."""
        parts: list[str] = []
        for c in components:
            if c.awarded > 0:
                parts.append(f"{c.name.replace('_', ' ')} {c.awarded}/{c.max}")

        if not parts:
            return "Gathering context — no score computed yet."

        justification = f"{band.title()} at {score}. " + ", ".join(parts) + "."

        if override_result.applied_overrides:
            justification += f" Overrides applied: {', '.join(override_result.applied_overrides)}."

        return justification
