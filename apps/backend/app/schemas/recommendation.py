"""Recommendation-related schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RecommendationItem(BaseModel):
    """A single recommended service with rationale."""

    service_code: str
    name: str
    rank: int
    confidence: float = 0.0
    matched_pain_point_ids: list[str] = Field(default_factory=list)
    evidence_chunk_ids: list[str] = Field(default_factory=list)
    rationale: str = ""
    rationale_source: str = "model"
    typical_engagement: str = ""


class RecommendationResult(BaseModel):
    """Output of the recommendation engine."""

    withheld: bool = False
    withheld_reason: str | None = None
    changed_since_presented: bool = False
    items: list[RecommendationItem] = Field(default_factory=list)
