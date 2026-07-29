"""Conversation-related schemas."""

from __future__ import annotations

from pydantic import BaseModel


class MessageSchema(BaseModel):
    """A single message in the conversation history."""

    message_id: str
    role: str  # "assistant" | "visitor"
    content: str
    created_at: str
