"""Lead score domain model."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ScoreComponent:
    """A single score component with award and basis."""

    name: str
    awarded: int = 0
    max: int = 0
    basis: str = ""


@dataclass
class LeadScore:
    """Deterministic lead score with breakdown."""

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
