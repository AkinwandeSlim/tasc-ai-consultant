"""Completion detection — evaluates whether consultation should end.

Three triggers (FR-47):
1. Explicit: visitor intent end_conversation or API call
2. Criteria: phase is capture_and_close with all commercial slots filled
3. Abandonment: idle past threshold with 3+ turns and contact present

References: PRD FR-47, PRD Section 7.6
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CompletionResult:
    """Result of completion evaluation."""

    should_complete: bool = False
    reason: str = ""
    reason_code: str = ""  # visitor_requested | criteria_met | abandoned


class CompletionDetector:
    """Evaluates whether a consultation should be completed.

    Pure function — given state signals, returns a completion decision.
    """

    def __init__(
        self,
        abandon_threshold_turns: int = 3,
    ) -> None:
        self._abandon_threshold = abandon_threshold_turns

    def evaluate(
        self,
        phase: str,
        intent: str | None = None,
        commercial_slots_resolved: bool = False,
        contact_captured: bool = False,
        contact_declined: bool = False,
        is_idle: bool = False,
        visitor_turn_count: int = 0,
    ) -> CompletionResult:
        """Evaluate whether the consultation should complete.

        Args:
            phase: The current conversation phase.
            intent: The visitor's current intent.
            commercial_slots_resolved: Whether commercial slots are done.
            contact_captured: Whether contact has been captured with consent.
            is_idle: Whether the session is idle (abandonment check).
            visitor_turn_count: Number of visitor turns.

        Returns:
            CompletionResult with decision.
        """
        # 1. Explicit end_conversation intent
        if intent == "end_conversation":
            return CompletionResult(
                should_complete=True,
                reason="Visitor ended the conversation",
                reason_code="visitor_requested",
            )

        # Resolve contact status: captured or declined are both terminal
        contact_resolved = contact_captured or contact_declined

        # 2. Criteria met: capture_and_close phase + contact resolved + commercial resolved
        if phase in ("capture_and_close",) and contact_resolved and commercial_slots_resolved:
            return CompletionResult(
                should_complete=True,
                reason="All completion criteria satisfied",
                reason_code="criteria_met",
            )

        # 3. Visitor explicitly from qualification with all needed data
        if phase == "qualification" and commercial_slots_resolved and contact_resolved:
            return CompletionResult(
                should_complete=True,
                reason="Qualification complete with contact",
                reason_code="criteria_met",
            )

        # 4. Abandonment check
        if is_idle and visitor_turn_count >= self._abandon_threshold:
            return CompletionResult(
                should_complete=True,
                reason="Session idle past abandonment threshold",
                reason_code="abandoned",
            )

        return CompletionResult(should_complete=False, reason="", reason_code="")

    def check_explicit_completion(
        self,
        reason: str = "visitor_requested",
        has_contact: bool = False,
    ) -> CompletionResult:
        """Handle explicit completion request.

        Args:
            reason: The completion reason.
            has_contact: Whether contact is captured.

        Returns:
            CompletionResult for the explicit request.
        """
        return CompletionResult(
            should_complete=True,
            reason="Consultation completed by request",
            reason_code=reason,
        )
