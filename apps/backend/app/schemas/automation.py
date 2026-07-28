"""Automation payload schema — the validated contract sent to n8n."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AutomationContact(BaseModel):
    """Contact details for automation dispatch."""

    name: str | None = None
    email: str | None = None
    company: str | None = None
    phone: str | None = None
    consent: bool = False


class RoutingFlags(BaseModel):
    """Routing flags consumed by n8n."""

    send_sales_email: bool = True
    send_telegram_alert: bool = False
    send_visitor_confirmation: bool = True
    append_to_sheet: bool = True
    priority: str = "follow_up_24h"


class ConversationMeta(BaseModel):
    """Conversation metadata for the payload."""

    turn_count: int = 0
    transcript_ref: str = ""
    deferral_count: int = 0
    grounding_chunk_ids: list[str] = Field(default_factory=list)


class Provenance(BaseModel):
    """Version provenance information."""

    prompt_manifest_version: str = ""
    ruleset_version: str = ""
    index_manifest_version: str = ""


class AutomationPayload(BaseModel):
    """The complete validated payload dispatched to n8n.

    Schema validated before dispatch (FR-45). Contains everything the
    sales team and downstream systems need.
    """

    schema_version: str = "1.0"
    consultation_id: str
    session_id: str
    completion_reason: str = "criteria_met"
    partial: bool = False
    contact: AutomationContact | None = None
    business_profile: dict = Field(default_factory=dict)
    qualification: dict = Field(default_factory=dict)
    recommendations: list[dict] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)
    routing: RoutingFlags = Field(default_factory=RoutingFlags)
    conversation: ConversationMeta = Field(default_factory=ConversationMeta)
    provenance: Provenance = Field(default_factory=Provenance)
