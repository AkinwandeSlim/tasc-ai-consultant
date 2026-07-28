"""Shared enum definitions for API contracts.

All enums use lowercase snake_case strings.
Clients MUST tolerate unknown values.
"""

from enum import Enum


class SessionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETING = "completing"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    EXPIRED = "expired"
    TERMINATED = "terminated"


class ConversationPhase(str, Enum):
    GREETING = "greeting"
    DISCOVERY = "discovery"
    EXPLORATION = "exploration"
    RECOMMENDATION = "recommendation"
    QUALIFICATION = "qualification"
    CAPTURE_AND_CLOSE = "capture_and_close"


class LeadBand(str, Enum):
    EXPLORING = "exploring"
    COLD = "cold"
    WARM = "warm"
    QUALIFIED = "qualified"
    HOT = "hot"
    NOT_A_LEAD = "not_a_lead"


class FinishReason(str, Enum):
    COMPLETE = "complete"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class CompletionReason(str, Enum):
    VISITOR_REQUESTED = "visitor_requested"
    CRITERIA_MET = "criteria_met"
    ABANDONED = "abandoned"
    OPERATOR = "operator"


class IntentType(str, Enum):
    DESCRIBE_PROBLEM = "describe_problem"
    ANSWER_QUESTION = "answer_question"
    COMPANY_QUESTION = "company_question"
    CAPABILITY_QUESTION = "capability_question"
    PRICING_QUESTION = "pricing_question"
    TIMELINE_QUESTION = "timeline_question"
    OBJECTION = "objection"
    REQUEST_HUMAN = "request_human"
    SMALLTALK = "smalltalk"
    OFF_TOPIC = "off_topic"
    ANTI_PERSONA = "anti_persona"
    END_CONVERSATION = "end_conversation"


class DispatchStatus(str, Enum):
    QUEUED = "queued"
    SENDING = "sending"
    ACKNOWLEDGED = "acknowledged"
    RETRYING = "retrying"
    DEAD_LETTERED = "dead_lettered"
    SUPPRESSED = "suppressed"
