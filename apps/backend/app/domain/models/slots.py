"""Discovery slot domain models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SlotValue:
    """A single extracted slot value with metadata."""

    value: str | None = None
    normalised: str | None = None
    raw: str | None = None
    confidence: float = 0.0
    source_turn: int = 0
    declined: bool = False


@dataclass
class PainPoint:
    """A captured pain point with specificity and impact."""

    id: str
    label: str
    raw_text: str = ""
    specificity: str = "vague"  # vague | specific | quantified
    severity: str | None = None  # low | medium | high | critical
    frequency: str | None = None
    impact: str | None = None
    service_codes: list[str] = field(default_factory=list)
    confidence: float = 0.0
    source_turn: int = 0


@dataclass
class SlotMap:
    """Container for all extracted discovery slots."""

    industry: SlotValue = field(default_factory=SlotValue)
    business_size: SlotValue = field(default_factory=SlotValue)
    pain_points: list[PainPoint] = field(default_factory=list)
    current_tools: list[str] = field(default_factory=list)
    goals: list[str] = field(default_factory=list)
    timeline: SlotValue = field(default_factory=SlotValue)
    budget_band: SlotValue = field(default_factory=SlotValue)
    decision_role: SlotValue = field(default_factory=SlotValue)
    contact_name: SlotValue = field(default_factory=SlotValue)
    contact_email: SlotValue = field(default_factory=SlotValue)
    contact_company: SlotValue = field(default_factory=SlotValue)
