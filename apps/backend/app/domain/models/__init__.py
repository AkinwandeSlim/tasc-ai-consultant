"""Domain models — the canonical state representation.

These models are richer than DTOs and never serialised directly to API
responses. They carry the internal state shape defined in PRD Section 21.4.
"""

from app.domain.models.consultation_response import ConsultationResponse
from app.domain.models.conversation import (
    ConversationContext,
    ConversationEvent,
    ConversationHistory,
    ConversationMetadata,
    ConversationProgress,
    ConversationStage,
    ConversationState,
    SessionStatus,
)
from app.domain.models.recommendation import (
    Confidence,
    Priority,
    Recommendation,
    RecommendationCategory,
    RecommendationReason,
    RecommendationSummary,
    RecommendedService,
)
from app.domain.models.score import (
    LeadQualification,
    LeadScore,
    QualificationConfidence,
    QualificationDimension,
    QualificationReason,
    ScoreComponent,
    ScoringBreakdown,
)

__all__ = [
    "Confidence",
    "ConsultationResponse",
    "ConversationContext",
    "ConversationEvent",
    "ConversationHistory",
    "ConversationMetadata",
    "ConversationProgress",
    "ConversationStage",
    "ConversationState",
    "LeadQualification",
    "LeadScore",
    "Priority",
    "QualificationConfidence",
    "QualificationDimension",
    "QualificationReason",
    "Recommendation",
    "RecommendationCategory",
    "RecommendationReason",
    "RecommendationSummary",
    "RecommendedService",
    "ScoreComponent",
    "ScoringBreakdown",
    "SessionStatus",
]
