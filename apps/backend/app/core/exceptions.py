"""Domain exception hierarchy.

Every exception carries an error code (stable machine-readable identifier)
and a human-readable message suitable for the visitor. Exceptions here are
caught by the API error handler and converted to the standard error envelope.
"""

from __future__ import annotations


class TASCError(Exception):
    """Base exception for all TASC domain errors."""

    code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred."
    retryable: bool = False
    http_status: int = 500

    def __init__(
        self,
        message: str | None = None,
        code: str | None = None,
        retryable: bool | None = None,
        details: dict | None = None,
    ) -> None:
        super().__init__(message or self.message)
        self.code = code or self.code
        self.message = message or self.message
        self.retryable = retryable if retryable is not None else self.retryable
        self.details = details


# --- Validation ---

class ValidationError(TASCError):
    code = "VALIDATION_ERROR"
    message = "The request body was invalid."
    http_status = 422


class EmptyMessageError(TASCError):
    code = "EMPTY_MESSAGE"
    message = "Message content is empty. Please write something."
    http_status = 400


class MessageTooLongError(TASCError):
    code = "MESSAGE_TOO_LONG"
    message = "Message exceeds the maximum allowed length."
    http_status = 413


# --- Session ---

class SessionNotFoundError(TASCError):
    code = "SESSION_NOT_FOUND"
    message = "This consultation session no longer exists."
    http_status = 404


class SessionExpiredError(TASCError):
    code = "SESSION_EXPIRED"
    message = "This consultation session has expired. Start a new one."
    http_status = 410


class TurnInProgressError(TASCError):
    code = "TURN_IN_PROGRESS"
    message = "A response is already being generated for this session."
    retryable = True
    http_status = 409


class AlreadyCompletedError(TASCError):
    code = "ALREADY_COMPLETED"
    message = "This consultation has already been completed."
    http_status = 409


# --- Payment / Automation ---

class AlreadyDispatchedError(TASCError):
    code = "ALREADY_DISPATCHED"
    message = "This consultation has already been dispatched to automation."
    http_status = 409


class ConsultationNotFoundError(TASCError):
    code = "CONSULTATION_NOT_FOUND"
    message = "Consultation record not found."
    http_status = 404


class PayloadInvalidError(TASCError):
    code = "PAYLOAD_INVALID"
    message = "The consultation payload failed validation and could not be dispatched."
    retryable = True
    http_status = 500


# --- Rate limiting ---

class RateLimitedError(TASCError):
    code = "RATE_LIMITED"
    message = "Too many requests. Please wait before sending another message."
    retryable = True
    http_status = 429


# --- Auth ---

class UnauthorizedError(TASCError):
    code = "UNAUTHORIZED"
    message = "Authentication is required to access this resource."
    http_status = 401


# --- Provider / Infrastructure ---

class ProviderUnavailableError(TASCError):
    code = "PROVIDER_UNAVAILABLE"
    message = "Something went wrong on my end. Your message is still here, try again?"
    retryable = True
    http_status = 503


class RetrievalUnavailableError(TASCError):
    code = "RETRIEVAL_UNAVAILABLE"
    message = "I cannot look up that information right now. A consultant can help."
    retryable = True
    http_status = 503


class ContentBlockedError(TASCError):
    code = "CONTENT_BLOCKED"
    message = "I'm here to discuss business challenges. Let me know how I can help."
    http_status = 400
