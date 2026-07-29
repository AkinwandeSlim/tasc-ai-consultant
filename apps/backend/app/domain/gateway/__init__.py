"""Gateway abstractions for external automation integration."""

from app.domain.gateway.automation_gateway import (
    AutomationGateway,
    ConsultationRequest,
    ConsultationResult,
)

__all__ = [
    "AutomationGateway",
    "ConsultationRequest",
    "ConsultationResult",
]
