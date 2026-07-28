"""Summary-related schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SummaryStructure(BaseModel):
    """Structured breakdown of the executive summary."""

    situation: str = ""
    needs: list[str] = Field(default_factory=list)
    recommended_services: list[str] = Field(default_factory=list)
    qualification: str = ""
    next_step: str = ""


class ExecutiveSummary(BaseModel):
    """Executive summary output."""

    executive_summary: str
    word_count: int = 0
    structure: SummaryStructure = Field(default_factory=SummaryStructure)
    source: str = "model"
