"""Consultation chat endpoints.

POST   /api/v1/chat/start        — start a new consultation
POST   /api/v1/chat/message      — send a message in an active session
GET    /api/v1/chat/{session_id} — current consultation snapshot

Every endpoint is a thin passthrough to the domain orchestrator
(or automation gateway when n8n is enabled). No business logic lives here.

References: PRD Section 6, Backend Blueprint Section 6
"""

from __future__ import annotations

import datetime
import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import get_automation_gateway
from app.core.exceptions import (
    AlreadyCompletedError,
    EmptyMessageError,
    SessionNotFoundError,
)
from app.domain.gateway.automation_gateway import ConsultationRequest
from app.infrastructure.session_store import SessionRepository
from app.orchestration.orchestrator import ConsultationOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


# ── Request DTOs ────────────────────────────────────────────────────


class StartConsultationRequest(BaseModel):
    """POST /api/v1/chat/start request body."""

    locale: str | None = Field(default="en-US", max_length=10)
    referrer: str | None = Field(default=None, max_length=2048)
    utm: dict[str, str] | None = None
    client_metadata: dict[str, str] | None = None


class SendMessageRequest(BaseModel):
    """POST /api/v1/chat/message request body."""

    session_id: str = Field(..., min_length=1, max_length=128)
    message: str = Field(..., min_length=1, max_length=2000)
    client_turn_id: str | None = Field(default=None, max_length=64)


# ── Response DTOs ────────────────────────────────────────────────────


class _SlotValueModel(BaseModel):
    """Serialised slot value from the business profile."""
    value: str | None = None
    raw: str | None = None
    confidence: float = 0.0
    declined: bool = False


class _PainPointModel(BaseModel):
    """Serialised pain point."""
    label: str = ""
    source_turn: int = 0


class _BusinessProfileModel(BaseModel):
    """Serialised subset of the business profile for API responses."""
    industry: str | None = None
    company_size: str | None = None
    pain_points: list[_PainPointModel] = Field(default_factory=list)
    current_tools: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    timeline: str | None = None
    budget_band: str | None = None
    decision_authority: str | None = None
    has_contact: bool = False
    core_slots_filled: int = 0
    commercial_slots_filled: int = 0
    total_slots_filled: int = 0


class _LeadScoreModel(BaseModel):
    """Serialised lead score card."""
    score: int = 0
    band: str = "exploring"
    confidence: float = 0.0
    next_contributor: str | None = None
    disqualified: bool = False
    partial: bool = False
    justification: str = ""


class _RecommendationItemModel(BaseModel):
    """A single recommended service."""
    service_code: str = ""
    name: str = ""
    rank: int = 0
    confidence: float = 0.0
    confidence_label: str = ""
    category: str = ""
    priority: str = ""
    rationale: str = ""
    typical_engagement: str = ""


class _ScenarioModel(BaseModel):
    """A simulation scenario exposed in the API."""
    scenario_id: str
    name: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    turn_count: int = 0
    expected_band: str = ""
    expected_score: int = 0


class StartConsultationResponse(BaseModel):
    """Response from POST /api/v1/chat/start."""
    session_id: str
    greeting: str
    conversation_phase: str = "greeting"
    business_profile: _BusinessProfileModel = Field(default_factory=_BusinessProfileModel)
    lead_score: _LeadScoreModel = Field(default_factory=_LeadScoreModel)
    recommendations: list[_RecommendationItemModel] = Field(default_factory=list)
    completion_percentage: int = 0
    next_question: str | None = None
    conversation_finished: bool = False


class MessageResponse(BaseModel):
    """Response from POST /api/v1/chat/message."""
    assistant_message: str
    conversation_phase: str
    business_profile: _BusinessProfileModel = Field(default_factory=_BusinessProfileModel)
    lead_score: _LeadScoreModel = Field(default_factory=_LeadScoreModel)
    recommendations: list[_RecommendationItemModel] = Field(default_factory=list)
    completion_percentage: int = 0
    next_question: str | None = None
    conversation_finished: bool = False


class SessionSnapshotResponse(BaseModel):
    """Full consultation snapshot for GET /api/v1/chat/{session_id}."""
    session_id: str
    phase: str
    status: str
    turn_index: int = 0
    visitor_turn_count: int = 0
    business_profile: _BusinessProfileModel = Field(default_factory=_BusinessProfileModel)
    lead_score: _LeadScoreModel = Field(default_factory=_LeadScoreModel)
    recommendations: list[_RecommendationItemModel] = Field(default_factory=list)
    completion_percentage: int = 0
    last_question: str | None = None
    conversation_finished: bool = False
    messages: list[dict[str, Any]] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Standard error envelope."""
    error: _ErrorDetail


class _ErrorDetail(BaseModel):
    code: str
    message: str
    correlation_id: str = ""
    retryable: bool = False
    details: dict[str, Any] | None = None


# ── Helpers ──────────────────────────────────────────────────────────

_EMPTY_BP = _BusinessProfileModel()
_EMPTY_LS = _LeadScoreModel()


def _build_business_profile_model(bp: dict[str, Any] | None) -> _BusinessProfileModel:
    """Map a business profile dict (from the orchestrator) to the response model."""
    if not bp:
        return _EMPTY_BP
    return _BusinessProfileModel(
        industry=bp.get("industry"),
        company_size=bp.get("company_size"),
        pain_points=[
            _PainPointModel(label=p.get("label", ""), source_turn=p.get("source_turn", 0))
            for p in bp.get("pain_points", [])
        ],
        current_tools=list(bp.get("current_tools", [])),
        goals=list(bp.get("goals", [])),
        timeline=bp.get("timeline"),
        budget_band=bp.get("budget_band"),
        decision_authority=bp.get("decision_authority"),
        has_contact=bp.get("has_contact", False),
        core_slots_filled=bp.get("core_slots_filled", 0),
        commercial_slots_filled=bp.get("commercial_slots_filled", 0),
        total_slots_filled=bp.get("total_slots_filled", 0),
    )


def _build_lead_score_model(ls: dict[str, Any] | None) -> _LeadScoreModel:
    """Map a lead score dict (from the orchestrator) to the response model."""
    if not ls:
        return _EMPTY_LS
    return _LeadScoreModel(
        score=ls.get("score", 0),
        band=ls.get("band", "exploring"),
        confidence=ls.get("confidence", 0.0),
        next_contributor=ls.get("next_contributor"),
        disqualified=ls.get("disqualified", False),
        partial=ls.get("partial", False),
        justification=ls.get("justification", ""),
    )


def _build_recommendation_models(
    recs: list[dict[str, Any]],
) -> list[_RecommendationItemModel]:
    """Map recommendation dicts to response models."""
    return [
        _RecommendationItemModel(
            service_code=r.get("service_code", ""),
            name=r.get("name", ""),
            rank=r.get("rank", 0),
            confidence=r.get("confidence", 0.0),
            confidence_label=r.get("confidence_label", ""),
            category=r.get("category", ""),
            priority=r.get("priority", ""),
            rationale=r.get("rationale", ""),
            typical_engagement=r.get("typical_engagement", ""),
        )
        for r in recs
    ]


# ── Dependencies ─────────────────────────────────────────────────────


def _get_orchestrator() -> ConsultationOrchestrator:
    """Return the singleton orchestrator instance.

    For Sprint 4 the orchestrator is stateless and can be a singleton.
    A future version may resolve this from the DI container.
    """
    return ConsultationOrchestrator()


def _get_session_store() -> SessionRepository:
    """Resolve the session store dependency.

    Uses a module-level singleton for Sprint 4. Will be replaced
    with proper DI container resolution.
    """
    from app.infrastructure.session_store import InMemorySessionStore

    if not hasattr(_get_session_store, "_store"):
        _get_session_store._store = InMemorySessionStore()  # type: ignore[attr-defined]
    return _get_session_store._store  # type: ignore[attr-defined]


# ── Routes ───────────────────────────────────────────────────────────


@router.post("/start", response_model=StartConsultationResponse, status_code=201)
async def start_consultation(
    body: StartConsultationRequest | None = None,
    orchestrator: ConsultationOrchestrator = Depends(_get_orchestrator),
    session_store: SessionRepository = Depends(_get_session_store),
) -> StartConsultationResponse:
    """Start a new consultation session.

    Creates a session with a greeting message and returns the initial
    consultation state. No message payload is required — just call this
    endpoint to begin.
    """
    # Start the consultation via the orchestrator
    session = await orchestrator.start_consultation()

    session_id = session.get("session_id", "")
    greeting = _extract_greeting(session)

    # Persist initial session state
    await session_store.save(session_id, session)

    logger.info("Consultation started: session_id=%s", session_id)

    return StartConsultationResponse(
        session_id=session_id,
        greeting=greeting,
        conversation_phase="greeting",
        completion_percentage=0,
        next_question=greeting,
        conversation_finished=False,
    )


@router.post("/message", response_model=MessageResponse)
async def send_message(
    body: SendMessageRequest,
    orchestrator: ConsultationOrchestrator = Depends(_get_orchestrator),
    session_store: SessionRepository = Depends(_get_session_store),
    automation_gateway: object | None = Depends(get_automation_gateway),
) -> MessageResponse:
    """Send a message in an active consultation session.

    Processes the visitor message through the consultation engine or
    automation gateway and returns the assistant reply along with updated
    state, lead score, recommendations, and progress.

    The automation gateway is selected based on N8N_ENABLED:
      - MockAutomationGateway: uses local deterministic engine (default)
      - N8nAutomationGateway: forwards request to n8n webhook
    """
    if not body.message.strip():
        raise EmptyMessageError()

    # Resolve session
    session_state = await session_store.get(body.session_id)
    if session_state is None:
        raise SessionNotFoundError(
            f"Session '{body.session_id}' not found or has expired."
        )

    # Check if already completed
    if session_state.get("status") in ("completed", "terminated"):
        raise AlreadyCompletedError()

    # Construct a timestamp
    now = datetime.datetime.now(datetime.UTC).isoformat()

    # Gather conversation history from session state
    conversation_history = session_state.get("messages", [])

    # Process through the automation gateway
    # The gateway abstracts whether processing happens locally (mock)
    # or externally (n8n) — the route handler never knows which.
    gateway_request = ConsultationRequest(
        session_id=body.session_id,
        user_message=body.message,
        conversation_history=conversation_history,
        structured_state=session_state,
        timestamp=now,
        simulation_mode=session_state.get("simulation_mode", False),
    )

    # If the gateway has a process_consultation method, use it;
    # otherwise fall back to the orchestrator directly.
    if hasattr(automation_gateway, "process_consultation"):
        result = await automation_gateway.process_consultation(gateway_request)
    else:
        # Fallback: use orchestrator directly
        fallback_result = await orchestrator.process_turn(
            session_state=session_state,
            visitor_message=body.message,
            client_turn_id=body.client_turn_id,
        )
        # Wrap in ConsultationResult-like interface
        from dataclasses import dataclass

        @dataclass
        class _FallbackResult:
            assistant_message: str = ""
            conversation_phase: str = "greeting"
            business_profile: Any = None
            lead_score: Any = None
            recommendations: list = None
            completion_percentage: int = 0
            next_question: str | None = None
            is_complete: bool = False
            completion_reason: str = ""

            def __post_init__(self):
                if self.recommendations is None:
                    self.recommendations = []

        result = _FallbackResult(
            assistant_message=fallback_result.assistant_message,
            conversation_phase=fallback_result.conversation_phase,
            business_profile=fallback_result.business_profile,
            lead_score=fallback_result.lead_score,
            recommendations=fallback_result.recommendations or [],
            completion_percentage=fallback_result.completion_percentage,
            next_question=fallback_result.next_question,
            is_complete=fallback_result.is_complete,
            completion_reason=fallback_result.completion_reason,
        )

    # Update session state in store
    session_state["turn_index"] = session_state.get("turn_index", 0) + 1
    session_state["visitor_turn_count"] = (
        session_state.get("visitor_turn_count", 0) + 1
    )
    session_state["phase"] = result.conversation_phase

    # Append messages to history
    now_str = now
    messages = session_state.setdefault("messages", [])
    messages.append({
        "message_id": f"usr_{body.session_id[:8]}_{session_state['turn_index']:03d}",
        "role": "user",
        "content": body.message,
        "created_at": now_str,
    })
    messages.append({
        "message_id": f"ast_{body.session_id[:8]}_{session_state['turn_index']:03d}",
        "role": "assistant",
        "content": result.assistant_message,
        "created_at": now_str,
    })

    if result.is_complete:
        session_state["status"] = "completed" if result.completion_reason != "terminated" else "terminated"

    await session_store.save(body.session_id, session_state)

    return MessageResponse(
        assistant_message=result.assistant_message,
        conversation_phase=result.conversation_phase,
        business_profile=_build_business_profile_model(
            result.business_profile if isinstance(result.business_profile, dict)
            else _profile_to_dict(result.business_profile)
        ),
        lead_score=_build_lead_score_model(result.lead_score),
        recommendations=_build_recommendation_models(result.recommendations or []),
        completion_percentage=result.completion_percentage,
        next_question=result.next_question,
        conversation_finished=result.is_complete,
    )


@router.get("/{session_id}", response_model=SessionSnapshotResponse)
async def get_session_snapshot(
    session_id: str,
    session_store: SessionRepository = Depends(_get_session_store),
) -> SessionSnapshotResponse:
    """Get the current snapshot of an active or completed consultation.

    Returns the full consultation state including profile data,
    lead score, recommendations, and message history.
    """
    session_state = await session_store.get(session_id)
    if session_state is None:
        raise SessionNotFoundError(
            f"Session '{session_id}' not found or has expired."
        )

    business_profile = session_state.get("business_profile", {})
    phase = session_state.get("phase", "greeting")
    status = session_state.get("status", "active")
    is_finished = status in ("completed", "terminated")

    # Build a lead score from stored state (simplified — domain re-computes on each turn)
    lead_score_data = {}
    if hasattr(business_profile, "lead_score"):
        lead_score_data = getattr(business_profile, "lead_score", {})

    messages = session_state.get("messages", [])
    last_question = None
    if messages:
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                last_question = msg.get("content")
                break

    return SessionSnapshotResponse(
        session_id=session_id,
        phase=phase,
        status=status,
        turn_index=session_state.get("turn_index", 0),
        visitor_turn_count=session_state.get("visitor_turn_count", 0),
        business_profile=_build_business_profile_model(
            _profile_to_dict(business_profile)
        ),
        lead_score=_build_lead_score_model(lead_score_data),
        completion_percentage=_estimate_completion(business_profile, phase),
        last_question=last_question,
        conversation_finished=is_finished,
        messages=messages,
    )


# ── Internal helpers ─────────────────────────────────────────────────


def _extract_greeting(session: dict[str, Any]) -> str:
    """Extract the greeting message from a session dict."""
    messages = session.get("messages", [])
    for m in messages:
        if m.get("role") == "assistant":
            return m.get("content", "")
    return ""


def _profile_to_dict(bp: Any) -> dict[str, Any]:
    """Convert a BusinessProfile object to a plain dict for the model builder."""

    def _convert_pain_points(pp_list: Any) -> list[dict[str, Any]]:
        """Convert pain points to a list of dicts with label and source_turn."""
        result = []
        for pp in (pp_list or []):
            if isinstance(pp, dict):
                result.append(pp)
            elif hasattr(pp, "label"):
                result.append({
                    "label": getattr(pp, "label", ""),
                    "source_turn": getattr(pp, "source_turn", 0),
                })
        return result

    if bp is None:
        return {}
    if isinstance(bp, dict):
        return bp
    try:
        def _val(v: Any) -> str | None:
            """Extract value from a SlotValue-like object or return as-is."""
            if hasattr(v, "value"):
                return v.value if v.value else None
            if isinstance(v, str):
                return v
            return None

        def _bool_val(v: Any) -> bool:
            """Extract boolean from a SlotValue-like object or return as-is."""
            if hasattr(v, "value"):
                return bool(v.value)
            if isinstance(v, bool):
                return v
            return False

        def _list_val(v: Any) -> list:
            """Return a list value, handling callable properties."""
            if callable(v):
                return v()
            return list(v) if v else []

        bp_industry = getattr(bp, "industry", None)
        bp_company_size = getattr(bp, "company_size", None)
        bp_timeline = getattr(bp, "timeline", None)
        bp_budget = getattr(bp, "budget_band", None)
        bp_authority = getattr(bp, "decision_authority", None)

        return {
            "industry": _val(bp_industry),
            "company_size": _val(bp_company_size),
            "pain_points": _convert_pain_points(getattr(bp, "pain_points", [])),
            "current_tools": _list_val(getattr(bp, "current_tools", [])),
            "goals": _list_val(getattr(bp, "goals", [])),
            "timeline": _val(bp_timeline),
            "budget_band": _val(bp_budget),
            "decision_authority": _val(bp_authority),
            "has_contact": _bool_val(getattr(bp, "has_contact", False)) or _bool_val(getattr(bp, "contact_email", False)),
            "core_slots_filled": getattr(bp, "core_slots_filled", 0),
            "commercial_slots_filled": getattr(bp, "commercial_slots_filled", 0),
            "total_slots_filled": getattr(bp, "total_slots_filled", 0),
        }
    except Exception:
        return {}


def _estimate_completion(bp: Any, phase: str) -> int:
    """Estimate completion percentage from profile and phase."""
    if phase in ("completed", "terminated"):
        return 100
    mapped_phase = {"greeting": 0, "discovery": 20, "exploration": 35,
                    "recommendation": 50, "qualification": 65, "capture_and_close": 80}
    base = mapped_phase.get(phase, 0)
    return base
