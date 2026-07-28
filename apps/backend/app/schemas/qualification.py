"""Qualification-related schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ScoreComponent(BaseModel):
    """A single component of the lead score."""

    name: str
    awarded: int = 0
    max: int
    basis: str = ""


class LeadQualification(BaseModel):
    """Deterministic lead qualification result."""

    score: int = 0
    raw_score: int = 0
    band: str = "exploring"
    confidence: float = 0.0
    components: list[ScoreComponent] = Field(default_factory=list)
    applied_overrides: list[str] = Field(default_factory=list)
    next_contributor: str | None = None
    justification: str = ""
    disqualified: bool = False
    partial: bool = False
