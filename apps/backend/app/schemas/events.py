"""SSE event schemas — the streaming transport contract.

Each event type maps to a Pydantic model. Events are serialised as
``event: <type>\\ndata: <json>`` lines in the SSE stream.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PhaseEvent(BaseModel):
    """Emitted when a pipeline phase starts."""

    v: int = 1
    phase: str
    turn_index: int
    at: str


class TokenEvent(BaseModel):
    """Emitted for each chunk of response text."""

    v: int = 1
    delta: str
    turn_index: int


class ErrorEvent(BaseModel):
    """Emitted on a recoverable turn failure."""

    v: int = 1
    code: str
    message: str
    retryable: bool = True
    turn_index: int


class DoneEvent(BaseModel):
    """Always the final event in a stream."""

    v: int = 1
    turn_index: int
    client_turn_id: str | None = None
    message_id: str | None = None
    finish_reason: str = "complete"
    consultation_complete: bool = False
    consultation_id: str | None = None
