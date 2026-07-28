"""Analysis snapshot schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SlotValue(BaseModel):
    """A single extracted slot value (industry, business size, etc.)."""

    value: str | None = None
    label: str | None = None
    raw: str | None = None
    confidence: float = 0.0
    turn_index: int = 0


class PainPoint(BaseModel):
    """A captured pain point with metadata."""

    id: str
    label: str
    service_codes: list[str] = Field(default_factory=list)
    quantified: bool = False
    turn_index: int = 0


class RecommendedService(BaseModel):
    """A single recommended service."""

    service_code: str
    name: str
    rank: int
    confidence: float
    rationale: str
    typical_engagement: str = ""
