"""Recommendation domain models.

Represents service recommendations produced by the deterministic
recommendation engine. The model selects neither services nor scores;
it writes only the rationale for pre-selected, pre-ranked candidates.

References: PRD Section 15, AI Blueprint Section 6
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Confidence(str, Enum):
    """Confidence label for a recommendation.

    Rendered as High (>=0.8), Medium (0.6-0.79), or withheld (<0.6).
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    WITHHELD = "withheld"


class Priority(str, Enum):
    """Priority level for a recommendation."""

    PRIMARY = "primary"
    SECONDARY = "secondary"
    ALTERNATIVE = "alternative"


class RecommendationCategory(str, Enum):
    """Category of recommendation."""

    AUTOMATION = "automation"
    DEVELOPMENT = "development"
    DATA = "data"
    INTEGRATION = "integration"
    INFRASTRUCTURE = "infrastructure"
    STRATEGY = "strategy"


@dataclass
class RecommendationReason:
    """A single reason supporting a recommendation.

    References at least one stated pain point or goal (PRD FR-39).
    """

    pain_point_id: str = ""
    pain_point_label: str = ""
    relevance: str = ""
    evidence_chunk_id: str | None = None


@dataclass
class RecommendedService:
    """A single recommended service with rationale.

    References: PRD Section 15.4, AI Blueprint Section 6.2
    """

    service_code: str = ""
    name: str = ""
    rank: int = 1
    confidence: float = 0.0
    confidence_label: str = ""
    matched_pain_point_ids: list[str] = field(default_factory=list)
    evidence_chunk_ids: list[str] = field(default_factory=list)
    rationale: str = ""
    rationale_source: str = "model"
    typical_engagement: str = ""
    category: str = ""

    @property
    def display_confidence(self) -> str:
        """Get the display confidence label."""
        if self.confidence >= 0.8:
            return Confidence.HIGH.value
        if self.confidence >= 0.6:
            return Confidence.MEDIUM.value
        return Confidence.LOW.value

    @property
    def is_primary(self) -> bool:
        """Whether this is the top-ranked recommendation."""
        return self.rank == 1


@dataclass
class Recommendation:
    """A complete recommendation output for one turn.

    May be withheld when evidence is insufficient (PRD FR-43).
    """

    service_code: str = ""
    name: str = ""
    rank: int = 1
    confidence: float = 0.0
    confidence_label: str = ""
    category: str = ""
    priority: str = Priority.PRIMARY.value
    matched_pain_point_ids: list[str] = field(default_factory=list)
    evidence_chunk_ids: list[str] = field(default_factory=list)
    rationale: str = ""
    rationale_source: str = "model"
    typical_engagement: str = ""
    reasons: list[RecommendationReason] = field(default_factory=list)

    @property
    def display_confidence(self) -> str:
        """Get the display confidence label."""
        if self.confidence >= 0.8:
            return Confidence.HIGH.value
        if self.confidence >= 0.6:
            return Confidence.MEDIUM.value
        return Confidence.LOW.value


@dataclass
class RecommendationSummary:
    """Summary of recommendations for presentation.

    References: PRD Section 15.4, AI Blueprint Section 6.5
    """

    withheld: bool = False
    withheld_reason: str | None = None
    changed_since_presented: bool = False
    items: list[Recommendation] = field(default_factory=list)
    max_items: int = 3

    @property
    def primary(self) -> Recommendation | None:
        """Get the primary (top-ranked) recommendation."""
        return self.items[0] if self.items else None

    @property
    def has_recommendations(self) -> bool:
        """Whether any recommendations are present."""
        return not self.withheld and len(self.items) > 0
