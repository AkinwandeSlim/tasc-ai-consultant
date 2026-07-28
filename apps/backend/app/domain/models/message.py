"""Message domain model."""

from __future__ import annotations

import datetime
from dataclasses import dataclass


@dataclass
class Message:
    """A single message in the conversation."""

    message_id: str
    role: str  # "assistant" | "visitor"
    content: str
    created_at: datetime.datetime
    turn_index: int = 0
