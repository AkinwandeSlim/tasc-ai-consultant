"""Domain exception hierarchy.

Every exception carries an error code (stable machine-readable identifier)
and a human-readable message suitable for the visitor. Exceptions here are
caught by the API error handler and converted to the standard error envelope.

References: PRD Section 6.9 (Error envelope), Implementation Constitution Section 4
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


# --- Conversation Domain ---

class ConversationError(TASCError):
    """Base error for conversation domain failures."""
    code = "CONVERSATION_ERROR"
    message = "An error occurred while processing the conversation."
    http_status = 500


class PhaseTransitionError(ConversationError):
    """Raised when an invalid phase transition is attempted."""
    code = "INVALID_PHASE_TRANSITION"
    message = "The requested phase transition is not allowed."
    http_status = 409


class HistoryCompactionError(ConversationError):
    """Raised when history compaction fails."""
    code = "HISTORY_COMPACTION_ERROR"
    message = "An error occurred while compacting conversation history."
    http_status = 500


# --- Qualification Domain ---

class QualificationError(TASCError):
    """Base error for qualification domain failures."""
    code = "QUALIFICATION_ERROR"
    message = "An error occurred during lead qualification."
    http_status = 500


class ScoringError(QualificationError):
    """Raised when score computation encounters an error."""
    code = "SCORING_ERROR"
    message = "An error occurred while computing the lead score."
    http_status = 500


class OverrideEvaluationError(QualificationError):
    """Raised when override rules cannot be evaluated."""
    code = "OVERRIDE_ERROR"
    message = "An error occurred while applying scoring overrides."
    http_status = 500


# --- Recommendation Domain ---

class RecommendationError(TASCError):
    """Base error for recommendation domain failures."""
    code = "RECOMMENDATION_ERROR"
    message = "An error occurred while generating recommendations."
    http_status = 500


class CandidateGenerationError(RecommendationError):
    """Raised when recommendation candidates cannot be built."""
    code = "CANDIDATE_ERROR"
    message = "An error occurred while building service candidates."
    http_status = 500


class RationaleGenerationError(RecommendationError):
    """Raised when rationale writing fails."""
    code = "RATIONALE_ERROR"
    message = "An error occurred while writing the recommendation rationale."
    retryable = True
    http_status = 500


# --- Prompt Domain ---

class PromptError(TASCError):
    """Base error for prompt management failures."""
    code = "PROMPT_ERROR"
    message = "An error occurred while loading or rendering a prompt."
    http_status = 500


class PromptNotFoundError(PromptError):
    """Raised when a prompt template is not found."""
    code = "PROMPT_NOT_FOUND"
    message = "The requested prompt template was not found."
    http_status = 404


class PromptRenderError(PromptError):
    """Raised when a prompt template fails to render."""
    code = "PROMPT_RENDER_ERROR"
    message = "An error occurred while rendering the prompt template."
    http_status = 500


class ManifestError(PromptError):
    """Raised when the prompt manifest is invalid."""
    code = "MANIFEST_ERROR"
    message = "The prompt manifest is invalid or corrupt."
    http_status = 500


# --- Knowledge / RAG Domain ---

class KnowledgeError(TASCError):
    """Base error for knowledge domain failures."""
    code = "KNOWLEDGE_ERROR"
    message = "An error occurred while accessing the knowledge base."
    http_status = 500


class KnowledgeNotFoundError(KnowledgeError):
    """Raised when a knowledge document is not found."""
    code = "KNOWLEDGE_NOT_FOUND"
    message = "The requested knowledge document was not found."
    http_status = 404


class ChunkingError(KnowledgeError):
    """Raised when document chunking fails."""
    code = "CHUNKING_ERROR"
    message = "An error occurred during document chunking."
    http_status = 500


class IndexError(KnowledgeError):
    """Raised when the knowledge index is unavailable."""
    code = "INDEX_ERROR"
    message = "The knowledge index is unavailable or corrupt."
    http_status = 503


# --- Simulation Domain ---

class SimulationError(TASCError):
    """Base error for simulation framework failures."""
    code = "SIMULATION_ERROR"
    message = "An error occurred in the simulation framework."
    http_status = 500


class ScenarioNotFoundError(SimulationError):
    """Raised when a simulation scenario is not found."""
    code = "SCENARIO_NOT_FOUND"
    message = "The requested simulation scenario was not found."
    http_status = 404


class SimulationConfigError(SimulationError):
    """Raised when simulation configuration is invalid."""
    code = "SIMULATION_CONFIG_ERROR"
    message = "The simulation configuration is invalid."
    http_status = 500


# --- Gateway / Automation Domain ---

class GatewayError(TASCError):
    """Base error for automation gateway failures."""
    code = "GATEWAY_ERROR"
    message = "An error occurred while communicating with the automation gateway."
    retryable = True
    http_status = 502


class GatewayConnectionError(GatewayError):
    """Raised when the gateway is unreachable (network error)."""
    code = "GATEWAY_CONNECTION_ERROR"
    message = "Could not reach the automation gateway. Please try again."
    retryable = True
    http_status = 502


class GatewayTimeoutError(GatewayError):
    """Raised when the gateway request times out."""
    code = "GATEWAY_TIMEOUT"
    message = "The automation gateway did not respond in time. Please try again."
    retryable = True
    http_status = 504


class GatewayInvalidResponseError(GatewayError):
    """Raised when the gateway returns an unparseable or unexpected response."""
    code = "GATEWAY_INVALID_RESPONSE"
    message = "Received an invalid response from the automation gateway."
    retryable = False
    http_status = 502


class GatewayRejectedError(GatewayError):
    """Raised when the gateway rejects the request (4xx non-retryable)."""
    code = "GATEWAY_REJECTED"
    message = "The automation gateway rejected the request."
    retryable = False
    http_status = 502
