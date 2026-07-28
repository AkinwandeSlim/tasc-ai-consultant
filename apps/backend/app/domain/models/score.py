"""Lead score and qualification domain models.

Represents deterministic lead scoring, qualification assessment,
and the component breakdown. Scoring logic lives in the qualification
domain service; these are the data models only.

References: PRD Section 14, AI Blueprint Section 5
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ScoreComponent:
    """A single score component with award and basis."""

    name: str = ""
    awarded: int = 0
    max: int = 0
    basis: str = ""
    weight: float = 1.0

    @property
    def remaining(self) -> int:
        """Points still available for this component."""
        return max(0, self.max - self.awarded)

    @property
    def fraction(self) -> float:
        """Fraction of points awarded (0.0 to 1.0)."""
        if self.max == 0:
            return 0.0
        return self.awarded / self.max


@dataclass
class QualificationDimension:
    """A qualification dimension with evidence and contribution."""

    name: str = ""
    label: str = ""
    awarded: int = 0
    max: int = 0
    evidence: str = ""
    confidence: float = 0.0

    @property
    def contribution(self) -> float:
        """Fractional contribution to this dimension."""
        if self.max == 0:
            return 0.0
        return self.awarded / self.max


@dataclass
class QualificationConfidence:
    """Confidence in the qualification assessment.

    Separate from lead_score — measures evidence quality,
    not lead quality. References: AI Blueprint Section 5.4
    """

    overall: float = 0.0
    field_confidences: dict[str, float] = field(default_factory=dict)
    coverage: float = 0.0  # proportion of scoring dimensions with evidence
    uncertainties: list[str] = field(default_factory=list)
    effect: str = "briefing_flag_only"

    @property
    def evidence_quality(self) -> str:
        """Human-readable evidence quality label."""
        if self.overall >= 0.75:
            return "strong"
        if self.overall >= 0.50:
            return "reasonable"
        return "thin"


@dataclass
class QualificationReason:
    """A single reason contributing to the qualification decision."""

    dimension: str = ""
    reason: str = ""
    positive: bool = True
    weight: float = 1.0


@dataclass
class ScoringBreakdown:
    """Full breakdown of how the lead score was computed.

    Includes components, overrides, and next-contributor analysis
    so the panel can show what would raise the score.
    """

    total: int = 0
    components: list[ScoreComponent] = field(default_factory=list)
    applied_overrides: list[str] = field(default_factory=list)
    next_contributor: str | None = None
    next_contributor_headroom: int = 0
    band: str = "exploring"
    justification: str = ""
    ruleset_version: str = ""

    @property
    def max_possible(self) -> int:
        """Maximum possible score from all components."""
        return sum(c.max for c in self.components) if self.components else 100


@dataclass
class LeadScore:
    """Deterministic lead score with full breakdown.

    Scoring is deterministic code, never model output (FR-30).
    The model contributes extracted facts; code computes the score.
    """

    score: int = 0
    raw_score: int = 0
    band: str = "exploring"
    confidence: float = 0.0
    components: list[ScoreComponent] = field(default_factory=list)
    applied_overrides: list[str] = field(default_factory=list)
    next_contributor: str | None = None
    justification: str = ""
    disqualified: bool = False
    partial: bool = False


@dataclass
class LeadQualification:
    """Complete qualification assessment for a lead.

    Aggregates the score, dimension-level breakdown, confidence,
    reasons, and overrides into a single assessment object.
    """

    score: int = 0
    band: str = "exploring"
    dimensions: list[QualificationDimension] = field(default_factory=list)
    confidence: QualificationConfidence = field(default_factory=QualificationConfidence)
    reasons: list[QualificationReason] = field(default_factory=list)
    applied_overrides: list[str] = field(default_factory=list)
    justification: str = ""
    disqualified: bool = False
    partial: bool = False
