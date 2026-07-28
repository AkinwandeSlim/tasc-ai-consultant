"""Response body schemas for API endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class GreetingMessage(BaseModel):
    """The pre-authored greeting returned on session creation."""

    message_id: str
    role: str = "assistant"
    content: str
    created_at: str


class ConversationProgress(BaseModel):
    """Progress bar data in the analysis snapshot."""

    phase: str
    stage_index: int
    stage_total: int = 5
    slots_filled: int = 0
    slots_total: int = 9
    percent: int = 0


class QualificationStatus(BaseModel):
    """Checklist of qualification criteria."""

    business_context_understood: str = "unmet"
    challenges_identified: str = "unmet"
    solution_matched: str = "unmet"
    timeline_established: str = "unmet"
    budget_discussed: str = "unmet"
    contact_captured: str = "unmet"


class AnalysisSnapshot(BaseModel):
    """Full state replacement for the Live Analysis Panel (PRD Section 16)."""

    turn_index: int = 0
    lead_status: str = "exploring"
    lead_score: int | None = None
    lead_score_delta: int | None = None
    next_score_contributor: str | None = None
    industry: dict | None = None
    business_size: dict | None = None
    pain_points: list[dict] = Field(default_factory=list)
    recommended_services: list[dict] = Field(default_factory=list)
    conversation_progress: ConversationProgress = Field(default_factory=ConversationProgress)
    qualification_status: QualificationStatus = Field(default_factory=QualificationStatus)


class SessionLimit(BaseModel):
    """Session constraint information."""

    message_max_chars: int = 2000
    session_ttl_minutes: int = 60


class CreateSessionResponse(BaseModel):
    """201 response for POST /api/v1/sessions."""

    session_id: str
    created_at: str
    expires_at: str
    phase: str = "greeting"
    greeting: GreetingMessage
    analysis: AnalysisSnapshot = Field(default_factory=AnalysisSnapshot)
    limits: SessionLimit = Field(default_factory=SessionLimit)


class ErrorEnvelope(BaseModel):
    """Standard error envelope for all non-2xx responses."""

    code: str
    message: str
    correlation_id: str
    retryable: bool = False
    details: dict | None = None
