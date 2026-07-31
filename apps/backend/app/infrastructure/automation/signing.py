"""Payload signing for n8n webhook authentication.

Implements HMAC-SHA256 signing of request bodies for the n8n webhook.
The signature header is verified by the n8n workflow to ensure the
request originated from this backend (FR-52).
"""

from __future__ import annotations

import hashlib
import hmac
import time


def sign_payload(
    payload: bytes,
    signing_secret: str,
) -> str:
    """Compute HMAC-SHA256 signature of a raw payload body.

    Args:
        payload: The raw UTF-8 encoded JSON body.
        signing_secret: The HMAC signing secret.

    Returns:
        Hex-encoded HMAC-SHA256 digest.
    """
    if not signing_secret:
        return ""

    h = hmac.new(
        signing_secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    )
    return h.hexdigest()


def verify_signature(
    payload: bytes,
    signature: str,
    signing_secret: str,
) -> bool:
    """Verify an HMAC-SHA256 signature against a payload.

    Uses constant-time comparison to prevent timing attacks.

    Args:
        payload: The raw UTF-8 encoded JSON body.
        signature: The hex-encoded signature to verify.
        signing_secret: The HMAC signing secret.

    Returns:
        True if the signature is valid, False otherwise.
    """
    if not signing_secret or not signature:
        return False

    expected = sign_payload(payload, signing_secret)
    return hmac.compare_digest(expected, signature)


def build_signature_headers(
    payload: bytes,
    shared_secret: str,
    signing_secret: str,
    correlation_id: str,
) -> dict[str, str]:
    """Build the full set of authentication headers for an n8n webhook request.

    Args:
        payload: The raw UTF-8 encoded JSON body.
        shared_secret: The shared secret for X-TASC-Secret header.
        signing_secret: The HMAC signing secret.
        correlation_id: Correlation ID propagated from the originating turn.

    Returns:
        Dict of header name to value.
    """
    timestamp = int(time.time())
    signature = sign_payload(payload, signing_secret)

    return {
        "X-TASC-Shared-Secret": shared_secret,
        "X-TASC-Signature": f"sha256={signature}",
        "X-TASC-Timestamp": str(timestamp),
        "X-Correlation-Id": correlation_id,
        "Content-Type": "application/json",
    }
