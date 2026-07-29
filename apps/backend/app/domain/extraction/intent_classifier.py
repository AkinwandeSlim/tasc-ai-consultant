"""Intent classifier — rule-based visitor message intent classification.

Uses keyword and pattern matching to classify visitor messages into the
PRD Section 12.4 intent taxonomy. No AI calls — purely deterministic.

References: PRD 12.4, AI Blueprint Section 1.4
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class IntentResult:
    """Result of intent classification."""

    intent: str = "describe_problem"
    confidence: float = 0.0
    trigger: str = ""
    sub_intent: str | None = None


# --- Keyword lists grouped by intent ---

_HUMAN_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bspeak\s+to\s+(a\s+)?human\b", re.IGNORECASE),
    re.compile(r"\btalk\s+to\s+(a\s+)?person\b", re.IGNORECASE),
    re.compile(r"\bhuman\s+consultant\b", re.IGNORECASE),
    re.compile(r"\breal\s+person\b", re.IGNORECASE),
    re.compile(r"\bconnect\s+me\b", re.IGNORECASE),
    re.compile(r"\btransfer\s+me\b", re.IGNORECASE),
    re.compile(r"\b(can\s+I|I\s+want\s+to)\s+speak\b", re.IGNORECASE),
    re.compile(r"\bneed\s+to\s+talk\s+to\b", re.IGNORECASE),
    re.compile(r"\bcall\s+me\b", re.IGNORECASE),
]

_ANTI_PERSONA_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(?:I\s+)?(?:am\s+|'m\s+)?(?:a\s+)?(?:job\s+)?seeker\b", re.IGNORECASE),
    re.compile(r"\blooking\s+for\s+(?:a\s+)?job\b", re.IGNORECASE),
    re.compile(r"\bhiring\b", re.IGNORECASE),
    re.compile(r"\bcareer\b", re.IGNORECASE),
    re.compile(r"\bapply\s+for\b", re.IGNORECASE),
    re.compile(r"\bstudent\s+(?:project|research|thesis)\b", re.IGNORECASE),
    re.compile(r"\buniversity\s+project\b", re.IGNORECASE),
    re.compile(r"\bschool\s+project\b", re.IGNORECASE),
    re.compile(r"\bvacancy\b", re.IGNORECASE),
    re.compile(r"\bopen\s+position\b", re.IGNORECASE),
    re.compile(r"\bvendor\s+(?:registration|enquiry)\b", re.IGNORECASE),
    re.compile(r"\bsell\s+(?:you|trizen)\b", re.IGNORECASE),
    re.compile(r"\bpartnership\s+(?:enquiry|opportunity)\b", re.IGNORECASE),
]

_COMPANY_QUESTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(have|has)\s+(trizen|you)\s+(done|worked|built)\b", re.IGNORECASE),
    re.compile(r"\b(experience|expertise)\s+in\b", re.IGNORECASE),
    re.compile(r"\b(case\s+study|client|customer)\s+(example|story|reference)\b", re.IGNORECASE),
    re.compile(r"\bwho\s+(are|is)\s+(trizen|your)\b", re.IGNORECASE),
    re.compile(r"\b(what|which)\s+industr", re.IGNORECASE),
    re.compile(r"\b(how\s+long|when)\s+(have|was)\s+(trizen|you)\s+(been|around|founded)\b", re.IGNORECASE),
    re.compile(r"\btell\s+me\s+about\s+(trizen|yourself|your\s+company)\b", re.IGNORECASE),
    re.compile(r"\b(about|background)\s+(of\s+)?(trizen|the\s+company)\b", re.IGNORECASE),
]

_CAPABILITY_QUESTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(can|do)\s+(you|trizen)\s+(handle|do|build|develop|create|provide)\b", re.IGNORECASE),
    re.compile(r"\b(specialize|specialise)\s+in\b", re.IGNORECASE),
    re.compile(r"\b(offer|provide|have)\s+(.+)\s+service", re.IGNORECASE),
    re.compile(r"\b(technology|tech)\s+stack\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+(tools|technologies|platforms)\b", re.IGNORECASE),
    re.compile(r"\bdo\s+you\s+(use|work\s+with)\b", re.IGNORECASE),
    re.compile(r"\b(integrate|integration)\s+with\b", re.IGNORECASE),
]

_PRICING_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(how\s+much|cost|price|pricing|budget|rate|fee|charge|expensive|afford)\b", re.IGNORECASE),
    re.compile(r"\bwhat.*\bcost\b", re.IGNORECASE),
    re.compile(r"\bhow\s+much\s+(does|would|will)\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+(does|would).*\bcost\b", re.IGNORECASE),
    re.compile(r"\bpricing\s+(model|structure|band|range)\b", re.IGNORECASE),
]

_TIMELINE_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(how\s+long|when)\s+(does|would|will|can)\s+(it|you)\b", re.IGNORECASE),
    re.compile(r"\btimeline\b", re.IGNORECASE),
    re.compile(r"\b(how\s+quickly|how\s+fast)\b", re.IGNORECASE),
    re.compile(r"\b(delivery|deliver|implement)\s+(time|timeline|period|schedule)\b", re.IGNORECASE),
    re.compile(r"\blong\s+does\s+(it\s+)?take\b", re.IGNORECASE),
    re.compile(r"\bduration\b", re.IGNORECASE),
]

_OBJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(too\s+expensive|too\s+much|can'?t\s+afford)\b", re.IGNORECASE),
    re.compile(r"\b(not\s+sure|unsure|hesitant)\b", re.IGNORECASE),
    re.compile(r"\balready\s+(use|have|tried)\b", re.IGNORECASE),
    re.compile(r"\b(didn'?t\s+work|not\s+work|failed)\b", re.IGNORECASE),
    re.compile(r"\bcompare|competitor|alternative|other\s+vendor\b", re.IGNORECASE),
    re.compile(r"\b(previous|past)\s+(experience|vendor|supplier)\b", re.IGNORECASE),
    re.compile(r"\b(concern|worry|risk)\b", re.IGNORECASE),
]

_END_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(?:that'?s\s+)?(?:all|enough|it)\s+(?:for\s+now|thank)\b", re.IGNORECASE),
    re.compile(r"\b(?:i'?m\s+)?done\b", re.IGNORECASE),
    re.compile(r"\bgoodbye|bye|thanks?.+help\b", re.IGNORECASE),
    re.compile(r"\bend\s+(?:the\s+)?conversation\b", re.IGNORECASE),
    re.compile(r"\bthat'?s\s+(?:all|it|everything)\b", re.IGNORECASE),
]

_SMALLTALK_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(hello|hi\s+there|hey|greetings)\b", re.IGNORECASE),
    re.compile(r"\b(good\s+morning|good\s+afternoon|good\s+evening)\b", re.IGNORECASE),
    re.compile(r"\b(thanks?|thank\s+you|appreciate\s+it)\b", re.IGNORECASE),
    re.compile(r"\b(okay|ok|sure|alright|fine)\s*$", re.IGNORECASE),
    re.compile(r"\b(how\s+are\s+you|how'?s\s+it\s+going)\b", re.IGNORECASE),
    re.compile(r"\bnice\s+(to\s+)?meet\s+you\b", re.IGNORECASE),
]

_OFF_TOPIC_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bweather\b", re.IGNORECASE),
    re.compile(r"\bsports?\b", re.IGNORECASE),
    re.compile(r"\bpolitics?\b", re.IGNORECASE),
    re.compile(r"\brecipe\b", re.IGNORECASE),
    re.compile(r"\bmovie\b", re.IGNORECASE),
    re.compile(r"\bmusic\b", re.IGNORECASE),
    re.compile(r"\bgame\s+(?:recommend|suggest|play)\b", re.IGNORECASE),
]

_DISCOVERY_KEYWORDS: list[str] = [
    "we are", "we're", "our company", "my business", "we run",
    "we have", "we need", "we want", "we're looking",
    "problem", "challenge", "issue", "pain", "struggling",
    "manual", "repetitive", "slow", "inefficient", "bottleneck",
    "automate", "improve", "streamline", "optimize", "better way",
]


def _count_matches(text: str, patterns: list[re.Pattern]) -> int:
    """Count how many patterns match the text."""
    return sum(1 for p in patterns if p.search(text))


class IntentClassifier:
    """Rule-based intent classifier.

    Classifies visitor messages using keyword and pattern matching.
    Returns an IntentResult with the predicted intent and confidence.
    """

    def __init__(self, confidence_threshold: float = 0.5) -> None:
        self._threshold = confidence_threshold

    def classify(self, message: str, turn_index: int = 0) -> IntentResult:
        """Classify the intent of a visitor message.

        Args:
            message: The visitor's message text.
            turn_index: The current turn index (used for context).

        Returns:
            IntentResult with predicted intent and confidence.
        """
        text = message.strip()
        if not text:
            return IntentResult(
                intent="describe_problem",
                confidence=0.0,
                trigger="empty_message",
            )

        # Check in priority order
        # 1. Anti-persona (highest priority)
        ap_count = _count_matches(text, _ANTI_PERSONA_PATTERNS)
        if ap_count >= 1 and len(text.split()) >= 4:
            return IntentResult(
                intent="anti_persona",
                confidence=min(0.6 + ap_count * 0.15, 0.95),
                trigger="anti_persona_keywords",
            )

        # 2. End conversation
        end_count = _count_matches(text, _END_PATTERNS)
        if end_count >= 1:
            return IntentResult(
                intent="end_conversation",
                confidence=min(0.6 + end_count * 0.2, 0.95),
                trigger="end_conversation_keywords",
            )

        # 3. Request human
        human_count = _count_matches(text, _HUMAN_PATTERNS)
        if human_count >= 1:
            return IntentResult(
                intent="request_human",
                confidence=min(0.7 + human_count * 0.1, 0.95),
                trigger="human_request_keywords",
            )

        # 4. Pricing question
        price_count = _count_matches(text, _PRICING_PATTERNS)
        if price_count >= 2 or (price_count >= 1 and "?" in text):
            return IntentResult(
                intent="pricing_question",
                confidence=min(0.5 + price_count * 0.15, 0.9),
                trigger="pricing_keywords",
            )

        # 5. Timeline question
        tl_count = _count_matches(text, _TIMELINE_PATTERNS)
        if tl_count >= 1 and "?" in text:
            return IntentResult(
                intent="timeline_question",
                confidence=min(0.5 + tl_count * 0.15, 0.9),
                trigger="timeline_keywords",
            )

        # 6. Company question
        cq_count = _count_matches(text, _COMPANY_QUESTION_PATTERNS)
        if cq_count >= 2 or (cq_count >= 1 and "?" in text):
            return IntentResult(
                intent="company_question",
                confidence=min(0.5 + cq_count * 0.15, 0.9),
                trigger="company_question_keywords",
                sub_intent="company_question",
            )

        # 7. Capability question
        cap_count = _count_matches(text, _CAPABILITY_QUESTION_PATTERNS)
        if cap_count >= 2 or (cap_count >= 1 and "?" in text):
            return IntentResult(
                intent="capability_question",
                confidence=min(0.5 + cap_count * 0.15, 0.9),
                trigger="capability_keywords",
                sub_intent="capability_question",
            )

        # 8. Objection
        obj_count = _count_matches(text, _OBJECTION_PATTERNS)
        if obj_count >= 1:
            return IntentResult(
                intent="objection",
                confidence=min(0.4 + obj_count * 0.15, 0.85),
                trigger="objection_keywords",
            )

        # 9. Off-topic
        off_count = _count_matches(text, _OFF_TOPIC_PATTERNS)
        if off_count >= 2:
            return IntentResult(
                intent="off_topic",
                confidence=min(0.5 + off_count * 0.1, 0.8),
                trigger="off_topic_keywords",
            )

        # 10. Smalltalk
        st_count = _count_matches(text, _SMALLTALK_PATTERNS)
        if st_count >= 2 and len(text.split()) <= 6:
            return IntentResult(
                intent="smalltalk",
                confidence=min(0.5 + st_count * 0.1, 0.8),
                trigger="smalltalk_keywords",
            )

        # 11. Discovery intent detection (describe_problem / answer_question)
        discovery_match_count = sum(
            1 for kw in _DISCOVERY_KEYWORDS if kw in text.lower()
        )
        word_count = len(text.split())

        if discovery_match_count >= 2 or word_count >= 8:
            return IntentResult(
                intent="describe_problem",
                confidence=min(0.5 + discovery_match_count * 0.1, 0.85),
                trigger="discovery_description",
            )

        if discovery_match_count >= 1:
            return IntentResult(
                intent="answer_question",
                confidence=0.5,
                trigger="partial_discovery",
            )

        # 12. Default for short messages
        if word_count <= 3:
            return IntentResult(
                intent="answer_question",
                confidence=0.4,
                trigger="short_message",
            )

        return IntentResult(
            intent="describe_problem",
            confidence=0.4,
            trigger="default",
        )
