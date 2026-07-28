"""Conversation domain models.

Defines the core conversation lifecycle objects: stages, state, context,
history, metadata, progress tracking, and events. These models represent
the conversation at rest and in motion throughout the domain layer.

References: PRD Sections 12-13, AI Blueprint Sections 2-3
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ConversationStage(str, Enum):
    """Consultation stages matching the PRD runtime phases.

    These are the six runtime phases. The AI Blueprint's ten-stage framework
    is a conceptual decomposition mapped onto these stages.
    """

    GREETING = "greeting"
    DISCOVERY = "discovery"
    EXPLORATION = "exploration"
    RECOMMENDATION = "recommendation"
    QUALIFICATION = "qualification"
    CAPTURE_AND_CLOSE = "capture_and_close"


class SessionStatus(str, Enum):
    """Server-side session lifecycle status."""

    ACTIVE = "active"
    COMPLETING = "completing"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    DEGRADED = "degraded"


class ConversationIntent(str, Enum):
    """Visitor intent taxonomy from PRD Section 12.4."""

    DESCRIBE_PROBLEM = "describe_problem"
    ANSWER_QUESTION = "answer_question"
    COMPANY_QUESTION = "company_question"
    CAPABILITY_QUESTION = "capability_question"
    PRICING_QUESTION = "pricing_question"
    TIMELINE_QUESTION = "timeline_question"
    OBJECTION = "objection"
    REQUEST_HUMAN = "request_human"
    SMALLTALK = "smalltalk"
    OFF_TOPIC = "off_topic"
    ANTI_PERSONA = "anti_persona"
    END_CONVERSATION = "end_conversation"


@dataclass
class ConversationState:
    """The current state of a conversation.

    Captures phase, turn index, slot fill status, and active intent
    for the orchestrator to make decisions.
    """

    phase: str = ConversationStage.GREETING.value
    turn_index: int = 0
    visitor_turn_count: int = 0
    current_intent: str | None = None
    intent_confidence: float = 0.0
    slots_filled: int = 0
    slots_total: int = 9
    completion_criteria_met: bool = False
    wrap_up_flag: bool = False

    @property
    def slots_percent(self) -> float:
        """Proportion of discovery slots filled."""
        if self.slots_total == 0:
            return 0.0
        return (self.slots_filled / self.slots_total) * 100.0


@dataclass
class ConversationContext:
    """Context bundle passed through a single turn.

    Carries the data needed by the orchestrator and domain services
    to process one visitor message turn.
    """

    session_id: str
    turn_index: int
    visitor_message: str
    client_turn_id: str | None = None
    locale: str = "en-US"
    previous_phase: str | None = None
    current_phase: str = ConversationStage.GREETING.value
    is_retry: bool = False
    correlation_id: str = ""


@dataclass
class ConversationHistory:
    """Ordered conversation history with compaction support.

    Three-tier memory per PRD Section 7.3:
    1. Verbatim window — last N turns, unmodified
    2. Compacted summary — narrative paragraph of older turns
    3. Structured state — slot map, score, recommendations (separate model)
    """

    messages: list[dict] = field(default_factory=list)
    compacted_summary: str | None = None
    verbatim_window_size: int = 8
    token_budget: int = 3000
    estimated_tokens: int = 0
    compaction_count: int = 0

    def add_message(self, message: dict) -> None:
        """Append a message and update token estimate."""
        self.messages.append(message)
        char_count = sum(len(m.get("content", "")) for m in self.messages)
        self.estimated_tokens = int(char_count / 4)

    @property
    def needs_compaction(self) -> bool:
        """Whether history exceeds the token budget."""
        return self.estimated_tokens > self.token_budget

    @property
    def recent_turns(self) -> list[dict]:
        """Last N verbatim messages."""
        return self.messages[-self.verbatim_window_size:] if self.messages else []

    @property
    def older_turns(self) -> list[dict]:
        """Messages outside the verbatim window."""
        if len(self.messages) <= self.verbatim_window_size:
            return []
        return self.messages[:-self.verbatim_window_size]


@dataclass
class ConversationMetadata:
    """Metadata and provenance for a conversation."""

    session_id: str
    created_at: datetime.datetime
    last_active_at: datetime.datetime
    locale: str = "en-US"
    referrer: str | None = None
    utm: dict[str, str] | None = None
    prompt_manifest_version: str = ""
    ruleset_version: str = ""
    index_manifest_version: str = ""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    deferral_count: int = 0
    retrieval_count: int = 0
    degradation_count: int = 0


@dataclass
class ConversationProgress:
    """Progress of the conversation toward completion.

    Computed from phase and slot fill (never turn count alone)
    so a fast-track visitor sees genuine progress.
    """

    phase: str = ConversationStage.GREETING.value
    stage_index: int = 0
    stage_total: int = 5
    slots_filled: int = 0
    slots_total: int = 9

    @property
    def percent(self) -> int:
        """Overall progress percentage."""
        if self.slots_total == 0:
            return 0
        phase_progress = (self.stage_index / max(self.stage_total, 1)) * 50
        slot_progress = (self.slots_filled / self.slots_total) * 50
        return min(int(phase_progress + slot_progress), 100)

    @property
    def display_stage(self) -> str:
        """Visitor-safe stage label."""
        labels = {
            "greeting": "Understanding",
            "discovery": "Understanding",
            "exploration": "Exploring",
            "recommendation": "Recommending",
            "qualification": "Qualifying",
            "capture_and_close": "Wrapping up",
        }
        return labels.get(self.phase, "Understanding")


@dataclass
class ConversationEvent:
    """An event emitted during conversation processing.

    Maps to SSE events but is domain-owned — the infrastructure
    layer serialises these to the wire format.
    """

    event_type: str  # phase | token | analysis_snapshot | error | done
    turn_index: int
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    schema_version: int = 1
