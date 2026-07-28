"""Session domain model — the canonical session state.

Represents the full server-side session state as defined in PRD Section 21.4.
All state mutation flows through this model.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Session:
    """Canonical server-side session state."""

    # Identity
    session_id: str
    created_at: datetime.datetime
    last_active_at: datetime.datetime
    expires_at: datetime.datetime
    status: str = "active"

    # Attribution
    locale: str = "en-US"
    referrer: str | None = None
    utm: dict[str, str] | None = None
    client_metadata: dict[str, str] | None = None

    # Conversation
    phase: str = "greeting"
    turn_index: int = 0
    messages: list[dict] = field(default_factory=list)
    compacted_summary: str | None = None
    questions_asked: list[str] = field(default_factory=list)

    # Understanding
    slots: dict[str, Any] = field(default_factory=dict)
    conflicts: list[dict] = field(default_factory=list)

    # Engagement
    visitor_turn_count: int = 0
    asked_company_question: bool = False
    responded_to_recommendation: bool = False
    volunteered_contact: bool = False

    # Assessment
    score: int = 0
    score_components: list[dict] = field(default_factory=list)
    band: str = "exploring"
    applied_overrides: list[str] = field(default_factory=list)

    # Recommendation
    recommendations: list[dict] = field(default_factory=list)
    recommendations_presented_at_turn: int | None = None

    # Grounding
    retrieval_log: list[dict] = field(default_factory=list)
    deferral_count: int = 0

    # Consent
    consent_granted: bool = False
    consent_granted_at: datetime.datetime | None = None

    # Completion
    consultation_id: str | None = None
    completion_reason: str | None = None
    completed_at: datetime.datetime | None = None

    # Accounting
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    estimated_cost_usd: float = 0.0

    # Provenance
    prompt_manifest_version: str = ""
    ruleset_version: str = ""
    index_manifest_version: str = ""
