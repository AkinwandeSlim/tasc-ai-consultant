"""Completion detection — evaluates whether consultation should end.

Three triggers (FR-47):
1. Explicit: visitor intent end_conversation or API call
2. Criteria: phase is capture_and_close with all commercial slots filled
3. Abandonment: idle past threshold with 3+ turns and contact present
"""

# TODO: Implement completion detection
