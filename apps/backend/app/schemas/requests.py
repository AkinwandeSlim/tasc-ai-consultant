"""Request body schemas for API endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    """POST /api/v1/sessions request body."""

    locale: str | None = Field(default="en-US", max_length=10)
    referrer: str | None = Field(default=None, max_length=2048)
    utm: dict[str, str] | None = Field(default=None, max_length=10)
    client_metadata: dict[str, str] | None = Field(default=None, max_length=10)


class SendMessageRequest(BaseModel):
    """POST /api/v1/sessions/{id}/messages request body."""

    content: str = Field(..., min_length=1, max_length=2000)
    client_turn_id: str | None = Field(default=None, max_length=64)


class ContactInfo(BaseModel):
    """Contact details for consultation completion."""

    name: str | None = Field(default=None, min_length=2, max_length=120)
    email: str | None = Field(default=None, max_length=254)
    company: str | None = Field(default=None, max_length=160)
    phone: str | None = Field(default=None, max_length=30)
    consent: bool = False


class CompleteConsultationRequest(BaseModel):
    """POST /api/v1/sessions/{id}/complete request body."""

    reason: str = "visitor_requested"
    contact: ContactInfo | None = None
