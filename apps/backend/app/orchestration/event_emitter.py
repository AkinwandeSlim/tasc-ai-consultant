"""Event emitter — constructs and sends SSE events over the streaming response.

Manages phase events, token deltas, analysis snapshots, and done events.
In Sprint 2B+ this will connect to an actual SSE response stream.
For Sprint 3, it builds event data structures for downstream consumers.

References: PRD Section 6.5, Backend Blueprint Section 5.5
"""

from __future__ import annotations

import datetime
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SSEEvent:
    """A single SSE event to be emitted."""

    event_type: str  # phase | token | analysis_snapshot | error | done
    data: dict[str, Any] = field(default_factory=dict)
    turn_index: int = 0
    schema_version: int = 1


@dataclass
class AnalysisSnapshot:
    """Full analysis snapshot for the Live Analysis Panel.

    Matches the schema from Backend Blueprint Section 6.2.
    """

    turn_index: int = 0
    lead_status: str = "exploring"
    lead_score: int | None = None
    lead_score_delta: int | None = None
    next_score_contributor: str | None = None
    industry: dict | None = None
    business_size: dict | None = None
    pain_points: list[dict] = field(default_factory=list)
    recommended_services: list[dict] = field(default_factory=list)
    conversation_progress: dict | None = None
    qualification_status: dict | None = None


class EventEmitter:
    """Constructs and emits SSE events for a consultation turn.

    Collects events during turn processing and provides serialised
    event data for the streaming response.
    """

    def __init__(self) -> None:
        self._events: list[SSEEvent] = []
        self._turn_index: int = 0
        self._on_event: Callable[[SSEEvent], None] | None = None

    def set_event_callback(self, callback: Callable[[SSEEvent], None]) -> None:
        """Set a callback for each emitted event.

        Args:
            callback: Called for each event as it's emitted.
        """
        self._on_event = callback

    def begin_turn(self, turn_index: int) -> None:
        """Start collecting events for a new turn."""
        self._turn_index = turn_index
        self._events.clear()

    def emit_phase(self, phase: str) -> None:
        """Emit a phase change event.

        Args:
            phase: The phase name (e.g. 'understanding', 'evaluating').
        """
        event = SSEEvent(
            event_type="phase",
            data={
                "v": 1,
                "phase": phase,
                "turn_index": self._turn_index,
                "at": datetime.datetime.now(datetime.UTC).isoformat(),
            },
            turn_index=self._turn_index,
        )
        self._events.append(event)
        if self._on_event:
            self._on_event(event)

    def emit_token(self, delta: str) -> None:
        """Emit a token delta event.

        Args:
            delta: The token text to append.
        """
        event = SSEEvent(
            event_type="token",
            data={
                "v": 1,
                "delta": delta,
                "turn_index": self._turn_index,
            },
            turn_index=self._turn_index,
        )
        self._events.append(event)
        if self._on_event:
            self._on_event(event)

    def emit_analysis_snapshot(self, snapshot: AnalysisSnapshot) -> None:
        """Emit a full analysis snapshot event.

        Args:
            snapshot: The complete analysis snapshot.
        """
        event = SSEEvent(
            event_type="analysis_snapshot",
            data={
                "v": 1,
                "turn_index": snapshot.turn_index,
                "lead_status": snapshot.lead_status,
                "lead_score": snapshot.lead_score,
                "lead_score_delta": snapshot.lead_score_delta,
                "next_score_contributor": snapshot.next_score_contributor,
                "industry": snapshot.industry,
                "business_size": snapshot.business_size,
                "pain_points": snapshot.pain_points,
                "recommended_services": snapshot.recommended_services,
                "conversation_progress": snapshot.conversation_progress,
                "qualification_status": snapshot.qualification_status,
            },
            turn_index=self._turn_index,
        )
        self._events.append(event)
        if self._on_event:
            self._on_event(event)

    def emit_error(
        self,
        code: str,
        message: str,
        retryable: bool = False,
    ) -> None:
        """Emit an error event.

        Args:
            code: Machine-readable error code.
            message: Human-readable error message.
            retryable: Whether the error is retryable.
        """
        event = SSEEvent(
            event_type="error",
            data={
                "v": 1,
                "code": code,
                "message": message,
                "retryable": retryable,
                "turn_index": self._turn_index,
            },
            turn_index=self._turn_index,
        )
        self._events.append(event)
        if self._on_event:
            self._on_event(event)

    def emit_done(
        self,
        finish_reason: str = "complete",
        client_turn_id: str | None = None,
        message_id: str | None = None,
        consultation_complete: bool = False,
        consultation_id: str | None = None,
    ) -> None:
        """Emit the final 'done' event for the turn.

        Args:
            finish_reason: Why the turn finished.
            client_turn_id: Optional client-side turn identifier.
            message_id: The server-assigned message ID.
            consultation_complete: Whether consultation is complete.
            consultation_id: The consultation ID if complete.
        """
        event = SSEEvent(
            event_type="done",
            data={
                "v": 1,
                "turn_index": self._turn_index,
                "client_turn_id": client_turn_id,
                "message_id": message_id,
                "finish_reason": finish_reason,
                "consultation_complete": consultation_complete,
                "consultation_id": consultation_id,
            },
            turn_index=self._turn_index,
        )
        self._events.append(event)
        if self._on_event:
            self._on_event(event)

    def get_events(self) -> list[SSEEvent]:
        """Get all events emitted during this turn.

        Returns:
            List of SSEEvent in emission order.
        """
        return list(self._events)

    def build_analysis_snapshot(
        self,
        turn_index: int,
        lead_status: str = "exploring",
        lead_score: int | None = None,
        lead_score_delta: int | None = None,
        next_score_contributor: str | None = None,
        business_profile_industry: dict | None = None,
        business_profile_size: dict | None = None,
        pain_points: list[dict] | None = None,
        recommended_services: list[dict] | None = None,
        slot_fill_count: int = 0,
        total_slots: int = 9,
        stage_index: int = 0,
        qualification_status: dict | None = None,
    ) -> AnalysisSnapshot:
        """Build a complete analysis snapshot.

        Args:
            See individual fields.

        Returns:
            AnalysisSnapshot ready for emission.
        """
        return AnalysisSnapshot(
            turn_index=turn_index,
            lead_status=lead_status,
            lead_score=lead_score,
            lead_score_delta=lead_score_delta,
            next_score_contributor=next_score_contributor,
            industry=business_profile_industry,
            business_size=business_profile_size,
            pain_points=pain_points or [],
            recommended_services=recommended_services or [],
            conversation_progress={
                "phase": lead_status,
                "stage_index": stage_index,
                "stage_total": 5,
                "slots_filled": slot_fill_count,
                "slots_total": total_slots,
                "percent": int(
                    (stage_index / 5) * 50 + (slot_fill_count / total_slots) * 50
                ) if total_slots > 0 else 0,
            },
            qualification_status=qualification_status or {
                "business_context_understood": "unmet",
                "challenges_identified": "unmet",
                "solution_matched": "unmet",
                "timeline_established": "unmet",
                "budget_discussed": "unmet",
                "contact_captured": "unmet",
            },
        )
