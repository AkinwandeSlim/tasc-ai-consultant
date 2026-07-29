"""Automation — n8n dispatcher with retry, idempotency, and signing.

Components:
  n8n_dispatcher:   Base n8n dispatch stub (to be replaced).
  signing:          HMAC-SHA256 payload signing and verification.
  mock_gateway:     MockAutomationGateway — local deterministic engine.
  n8n_gateway:      N8nAutomationGateway — production n8n webhook adapter.
"""

from app.infrastructure.automation.mock_gateway import MockAutomationGateway
from app.infrastructure.automation.n8n_gateway import N8nAutomationGateway
from app.infrastructure.automation.signing import (
    build_signature_headers,
    sign_payload,
    verify_signature,
)

__all__ = [
    "MockAutomationGateway",
    "N8nAutomationGateway",
    "build_signature_headers",
    "sign_payload",
    "verify_signature",
]
