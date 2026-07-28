"""Security utilities: HMAC signing, constant-time comparison, webhook auth.

Implements webhook authentication between FastAPI and n8n
(FR-52, NFR-16) and provides safe comparison primitives.
"""

from __future__ import annotations

import hashlib
import hmac
import time


def sign_payload(payload: bytes, secret: str) -> str:
    """Create an HMAC-SHA256 signature for the given payload.

    Args:
        payload: Raw request body bytes.
        secret: HMAC signing secret.

    Returns:
        Hex-encoded HMAC-SHA256 signature.
    """
    h = hmac.new(
        key=secret.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256,
    )
    return f"sha256={h.hexdigest()}"


def verify_signature(payload: bytes, secret: str, signature: str) -> bool:
    """Constant-time verification of an HMAC-SHA256 signature.

    Args:
        payload: Raw request body bytes that were signed.
        secret: HMAC signing secret.
        signature: The received signature string (e.g. "sha256=abc123...").

    Returns:
        True if the signature is valid.
    """
    expected = sign_payload(payload, secret)
    return hmac.compare_digest(expected, signature)


def verify_timestamp(timestamp: str, max_skew_seconds: int = 300) -> bool:
    """Check whether a Unix timestamp is within the allowed skew window.

    Args:
        timestamp: Unix seconds as a string.
        max_skew_seconds: Maximum allowed age in seconds.

    Returns:
        True if the timestamp is recent enough.
    """
    try:
        ts = int(timestamp)
    except (ValueError, TypeError):
        return False
    now = time.time()
    return abs(now - ts) <= max_skew_seconds


def constant_time_equal(a: str, b: str) -> bool:
    """Constant-time string comparison to prevent timing attacks.

    Args:
        a: First string.
        b: Second string.

    Returns:
        True if the strings are identical.
    """
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))
