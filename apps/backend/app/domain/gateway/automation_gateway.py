"""Automation gateway protocol and data models.

Defines the interface that all automation gateways must implement.
The gateway abstracts where consultation processing happens:
local deterministic engine (mock) or external n8n workflow.

This protocol lives in the domain layer so that higher layers
(orchestration, API) depend on an abstraction, not a concrete adapter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ConsultationRequest:
    """Request to process a consultation turn through the automation gateway.

    Contains all the context needed for an external system (or mock)
    to produce a consultation response.

    Fields:
        session_id: Unique session identifier.
        user_message: The visitor's current message.
        conversation_history: List of prior message dicts with role/content.
        structured_state: Current session/business state from the store.
        timestamp: ISO 8601 timestamp of the request.
        simulation_mode: Whether the session is running in simulation mode.
    """

    session_id: str
    user_message: str
    conversation_history: list[dict[str, Any]] = field(default_factory=list)
    structured_state: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    simulation_mode: bool = False


@dataclass
class ConsultationResult:
    """Result from processing a consultation turn.

    This dataclass mirrors the existing frontend response contract
    exactly — no frontend changes are required when switching between
    mock and n8n mode.

    Fields match the MessageResponse / OrchestrationResult contract.
    """

    assistant_message: str = ""
    conversation_phase: str = "greeting"
    business_profile: dict[str, Any] | None = None
    lead_score: dict[str, Any] | None = None
    recommendations: list[dict[str, Any]] = field(default_factory=list)
    completion_percentage: int = 0
    next_question: str | None = None
    is_complete: bool = False
    completion_reason: str = ""
    analysis_snapshot: dict[str, Any] | None = None
    errors: list[dict[str, Any]] = field(default_factory=list)


class AutomationGateway(Protocol):
    """Protocol for consultation automation gateways.

    Implementations decide how consultation turns are processed:
    - MockAutomationGateway: local deterministic engine (N8N_ENABLED=false)
    - N8nAutomationGateway:  forwards to external n8n webhook (N8N_ENABLED=true)

    The FastAPI application never knows implementation details about n8n.
    Switching implementations requires only a configuration change.
    """

    async def process_consultation(
        self,
        request: ConsultationRequest,
    ) -> ConsultationResult:
        """Process a consultation turn and return the result.

        Args:
            request: The consultation request with session context.

        Returns:
            ConsultationResult matching the frontend contract.

        Raises:
            GatewayConnectionError: If the gateway is unreachable.
            GatewayTimeoutError: If the gateway times out.
            GatewayInvalidResponseError: If the response is malformed.
        """
        ...
