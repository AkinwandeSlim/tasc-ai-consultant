"""Recommendation engine — hybrid rule + evidence service ranking.

Deterministic candidate generation from pain-to-service mapping,
evidence-based scoring and ranking, then template rationale writing.

References: PRD FR-37 to FR-43, PRD Section 15, AI Blueprint Section 6
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.models.recommendation import (
    Recommendation,
    RecommendationSummary,
)
from app.domain.recommendation.candidate_builder import CandidateBuilder
from app.domain.recommendation.ranker import Ranker
from app.domain.recommendation.rationale import RationaleWriter


@dataclass
class RecommendationInput:
    """Input data for the recommendation engine."""

    pain_point_labels: list[str] = field(default_factory=list)
    pain_signal_ids: list[str] = field(default_factory=list)
    industry: str | None = None
    business_size: str | None = None
    budget_band: str | None = None
    current_phase: str = "greeting"
    evidence_boosts: dict[str, float] | None = None
    industry_boosts: dict[str, float] | None = None

    @property
    def pain_point_count(self) -> int:
        return len(self.pain_point_labels)


class RecommendationEngine:
    """Rule-based recommendation engine.

    Three-stage process:
    1. Candidate generation from pain-to-service mapping
    2. Score and rank candidates using formula
    3. Generate template rationales

    The model never selects services — only writes rationales (Sprint 2B+).
    """

    def __init__(
        self,
        candidate_builder: CandidateBuilder | None = None,
        ranker: Ranker | None = None,
        rationale_writer: RationaleWriter | None = None,
        confidence_floor: float = 0.6,
        max_recommendations: int = 3,
    ) -> None:
        self._candidate_builder = candidate_builder or CandidateBuilder()
        self._ranker = ranker or Ranker(
            confidence_floor=confidence_floor,
            max_recommendations=max_recommendations,
        )
        self._rationale_writer = rationale_writer or RationaleWriter()
        self._confidence_floor = confidence_floor
        self._max_recommendations = max_recommendations

    def evaluate(
        self,
        input_data: RecommendationInput,
    ) -> RecommendationSummary:
        """Evaluate and produce recommendations.

        Args:
            input_data: All inputs needed for recommendation.

        Returns:
            RecommendationSummary with ranked recommendations or withheld.
        """
        # Step 1: Build candidates from pain signals
        candidates = self._candidate_builder.build_candidates(
            pain_signal_ids=input_data.pain_signal_ids,
            industry=input_data.industry,
        )

        # Step 2: Rank candidates
        ranked = self._ranker.rank(
            candidates=candidates,
            industry=input_data.industry,
            business_size=input_data.business_size,
            budget_band=input_data.budget_band,
            evidence_boosts=input_data.evidence_boosts,
            industry_boosts=input_data.industry_boosts,
        )

        # Step 3: Check if should withhold
        withhold, reason = self._ranker.should_withhold(
            ranked=ranked,
            pain_point_count=input_data.pain_point_count,
            current_phase=input_data.current_phase,
        )

        if withhold:
            return RecommendationSummary(
                withheld=True,
                withheld_reason=reason,
                items=[],
                max_items=self._max_recommendations,
            )

        # Step 4: Truncate to max recommendations
        ranked = self._ranker.truncate(ranked)

        # Step 5: Generate rationales
        service_codes = [r.service_code for r in ranked]
        rationales = self._rationale_writer.write_all_rationales(
            service_codes=service_codes,
            pain_point_labels=input_data.pain_point_labels,
        )
        rationale_map = {r.service_code: r.rationale for r in rationales}

        # Step 6: Build Recommendation objects
        items: list[Recommendation] = []
        for ranked_svc in ranked:
            rationale = rationale_map.get(
                ranked_svc.service_code,
                "This service aligns with your business needs.",
            )
            items.append(Recommendation(
                service_code=ranked_svc.service_code,
                name=ranked_svc.name,
                rank=ranked_svc.rank,
                confidence=ranked_svc.confidence,
                confidence_label=self._confidence_label(ranked_svc.confidence),
                category=self._get_category(ranked_svc.service_code),
                priority="primary" if ranked_svc.rank == 1 else "secondary",
                matched_pain_point_ids=ranked_svc.pain_signals,
                rationale=rationale,
                rationale_source="template",
                typical_engagement=self._get_engagement(ranked_svc.service_code),
            ))

        return RecommendationSummary(
            withheld=False,
            withheld_reason=None,
            changed_since_presented=False,
            items=items,
            max_items=self._max_recommendations,
        )

    @staticmethod
    def _confidence_label(confidence: float) -> str:
        """Get confidence label."""
        if confidence >= 0.8:
            return "high"
        if confidence >= 0.6:
            return "medium"
        return "low"

    @staticmethod
    def _get_category(code: str) -> str:
        """Get service category."""
        categories = {
            "SVC-AIA": "automation",
            "SVC-WEB": "development",
            "SVC-DAT": "data",
            "SVC-INT": "integration",
            "SVC-CLD": "infrastructure",
            "SVC-CON": "strategy",
        }
        return categories.get(code, "")

    @staticmethod
    def _get_engagement(code: str) -> str:
        """Get typical engagement description."""
        engagements = {
            "SVC-AIA": "4 to 10 weeks, discovery plus build",
            "SVC-WEB": "6 to 16 weeks",
            "SVC-DAT": "6 to 12 weeks",
            "SVC-INT": "3 to 8 weeks",
            "SVC-CLD": "4 to 10 weeks",
            "SVC-CON": "2 to 6 weeks",
        }
        return engagements.get(code, "")
