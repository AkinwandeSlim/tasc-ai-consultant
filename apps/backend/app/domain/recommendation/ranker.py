"""Ranker — scores and ranks candidate services.

candidate_score = base_weight * pain_frequency_factor + evidence_boost
                 + industry_match_boost - constraint_penalty

References: PRD Section 15.3, AI Blueprint Section 6.2
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from app.domain.recommendation.candidate_builder import Candidate


@dataclass
class RankedService:
    """A ranked service with full scoring breakdown."""

    service_code: str
    name: str
    rank: int = 1
    score: float = 0.0
    confidence: float = 0.0
    pain_signals: list[str] = field(default_factory=list)
    is_primary: bool = False


# Maximum normalised score for confidence calculation
_MAX_NORMALISED_SCORE: float = 1.8


class Ranker:
    """Ranks service candidates using the PRD scoring formula.

    Pure function. Deterministic — same inputs always produce same ranking.
    """

    def __init__(
        self,
        confidence_floor: float = 0.6,
        max_recommendations: int = 3,
    ) -> None:
        self._confidence_floor = confidence_floor
        self._max_recommendations = max_recommendations

    def rank(
        self,
        candidates: list[Candidate],
        industry: str | None = None,
        business_size: str | None = None,
        budget_band: str | None = None,
        evidence_boosts: dict[str, float] | None = None,
        industry_boosts: dict[str, float] | None = None,
    ) -> list[RankedService]:
        """Rank candidates and return top N.

        Args:
            candidates: List of candidates to rank.
            industry: Optional industry for matching.
            business_size: Optional business size for constraint checks.
            budget_band: Optional budget for constraint checks.
            evidence_boosts: Per-service-code evidence boost (0-0.3).
            industry_boosts: Per-service-code industry match boost (0-0.2).

        Returns:
            List of RankedService sorted by score descending.
        """
        if not candidates:
            return []

        scored: list[RankedService] = []
        for candidate in candidates:
            # 1. Pain frequency factor: 1.0 base + 0.1 per extra pain signal
            pain_count = len(candidate.pain_signals)
            pain_frequency = 1.0 + (max(0, pain_count - 1) * 0.1)

            # 2. Base score
            score = candidate.base_weight * pain_frequency

            # 3. Evidence boost
            ev_boost = (evidence_boosts or {}).get(candidate.service_code, 0.0)
            score += ev_boost

            # 4. Industry match boost
            ind_boost = (industry_boosts or {}).get(candidate.service_code, 0.0)
            score += ind_boost

            # 5. Constraint penalty
            penalty = self._compute_constraint_penalty(
                candidate.service_code, business_size, budget_band,
            )
            score -= penalty

            # 6. Normalised confidence
            confidence = min(score / _MAX_NORMALISED_SCORE, 0.98)

            scored.append(RankedService(
                service_code=candidate.service_code,
                name=self._service_name(candidate.service_code),
                score=score,
                confidence=confidence,
                pain_signals=candidate.pain_signals,
                is_primary=candidate.is_primary,
            ))

        # Sort by score descending
        scored.sort(key=lambda x: x.score, reverse=True)

        # Assign ranks
        for i, s in enumerate(scored):
            s.rank = i + 1

        return scored

    def should_withhold(
        self,
        ranked: list[RankedService],
        pain_point_count: int,
        current_phase: str,
    ) -> tuple[bool, str | None]:
        """Determine if recommendations should be withheld.

        Withhold when:
        - Fewer than 2 pain points
        - Top confidence below floor
        - Phase is too early (before exploration)

        Returns:
            Tuple of (withhold, reason).
        """
        if pain_point_count < 2:
            return True, "Not enough pain points identified yet"

        if current_phase in ("greeting", "discovery"):
            return True, "Still learning about your business needs"

        if not ranked:
            return True, "No services could be matched to the identified needs"

        if ranked[0].confidence < self._confidence_floor:
            return True, f"Top service confidence ({ranked[0].confidence:.2f}) below threshold ({self._confidence_floor})"

        return False, None

    def truncate(self, ranked: list[RankedService]) -> list[RankedService]:
        """Truncate to max recommendations."""
        return ranked[:self._max_recommendations]

    @staticmethod
    def _compute_constraint_penalty(
        service_code: str,
        business_size: str | None,
        budget_band: str | None,
    ) -> float:
        """Compute constraint penalty (0 to 0.5)."""
        penalty = 0.0

        # Large service + small budget → penalty
        large_services = {"SVC-WEB", "SVC-DAT", "SVC-CLD"}
        if service_code in large_services and budget_band == "under_5k":
            penalty += 0.3

        # Integration + very small budget
        if service_code == "SVC-INT" and budget_band == "under_5k":
            penalty += 0.2

        # AI Automation + very small company + small budget
        if service_code == "SVC-AIA" and business_size == "1-10" and budget_band == "under_5k":
            penalty += 0.1

        return penalty

    @staticmethod
    def _service_name(code: str) -> str:
        """Get a human-readable service name."""
        names = {
            "SVC-AIA": "AI Automation and Agents",
            "SVC-WEB": "Web and Application Development",
            "SVC-DAT": "Data Engineering and Analytics",
            "SVC-INT": "Systems Integration",
            "SVC-CLD": "Cloud and DevOps",
            "SVC-CON": "Technology Strategy Consulting",
        }
        return names.get(code, code)
