"""Memory management — history windowing, compaction, token budget enforcement.

Three tiers (PRD Section 7.3):
1. Verbatim window — last N turns, unmodified
2. Compacted summary — narrative paragraph of older turns
3. Structured state — slot map, score, recommendations (separate model)

References: PRD FR-04, FR-05, PRD Section 7.3
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MemoryState:
    """Current memory state after applying compaction."""

    verbatim_turns: list[dict] = field(default_factory=list)
    compacted_summary: str | None = None
    compaction_count: int = 0
    estimated_tokens: int = 0
    needs_compaction: bool = False


class ConversationMemory:
    """Manages conversation history with three-tier memory.

    Tracks token usage and triggers compaction when the budget is exceeded.
    Pure function — receives state, returns new state.
    """

    def __init__(
        self,
        verbatim_window_size: int = 8,
        token_budget: int = 3000,
    ) -> None:
        self._window_size = verbatim_window_size
        self._token_budget = token_budget

    def compute_state(
        self,
        messages: list[dict],
        existing_summary: str | None = None,
        compaction_count: int = 0,
    ) -> MemoryState:
        """Compute the current memory state.

        Args:
            messages: Full list of conversation messages.
            existing_summary: Existing compacted summary if any.
            compaction_count: Number of previous compactions.

        Returns:
            MemoryState with verbatim window and compaction status.
        """
        estimated_tokens = self._estimate_tokens(messages)
        needs_compaction = estimated_tokens > self._token_budget and len(messages) > self._window_size * 2

        # Get verbatim window
        verbatim = messages[-self._window_size:] if messages else []

        return MemoryState(
            verbatim_turns=verbatim,
            compacted_summary=existing_summary,
            compaction_count=compaction_count,
            estimated_tokens=estimated_tokens,
            needs_compaction=needs_compaction,
        )

    def get_prompt_messages(
        self,
        messages: list[dict],
        existing_summary: str | None = None,
        compaction_count: int = 0,
    ) -> tuple[list[dict], MemoryState]:
        """Get messages for prompt assembly, applying compaction if needed.

        Args:
            messages: Full message list.
            existing_summary: Existing compacted summary.
            compaction_count: Previous compaction count.

        Returns:
            Tuple of (messages_for_prompt, memory_state).
        """
        state = self.compute_state(messages, existing_summary, compaction_count)

        if state.needs_compaction and existing_summary:
            # Already compacted — use summary + verbatim window
            prompt_messages: list[dict] = []

            if existing_summary:
                prompt_messages.append({
                    "role": "system",
                    "content": f"[Compacted summary of earlier conversation: {existing_summary}]",
                })

            # Compact older turns in the verbatim window into a system message
            older = messages[:-self._window_size] if len(messages) > self._window_size else []
            if older and not existing_summary:
                # Simulate compaction — older turns get reduced to a summary
                compacted = self._summarise_turns(older)
                prompt_messages.append({
                    "role": "system",
                    "content": f"[Earlier conversation: {compacted}]",
                })

            prompt_messages.extend(state.verbatim_turns)
            return prompt_messages, state

        # No compaction needed — use messages as-is
        # But cap at token budget by dropping oldest if needed
        if state.estimated_tokens > self._token_budget and len(messages) > self._window_size:
            # Drop oldest messages gradually
            overflow = state.estimated_tokens - self._token_budget
            drop_count = min(
                len(messages) - self._window_size,
                max(1, overflow // 200),
            )
            trimmed = messages[drop_count:]
            return trimmed, state

        return messages, state

    def estimate_compaction_savings(
        self,
        messages: list[dict],
        existing_summary: str | None = None,
    ) -> int:
        """Estimate how many tokens would be saved by compaction.

        Args:
            messages: Full message list.
            existing_summary: Existing summary if any.

        Returns:
            Estimated token savings.
        """
        self._estimate_tokens(messages)
        older_turns = messages[:-self._window_size] if len(messages) > self._window_size else []
        older_tokens = self._estimate_tokens(older_turns)

        # After compaction, older turns become ~50 tokens
        summary_tokens = 50 if older_turns else 0
        return older_tokens - summary_tokens

    @staticmethod
    def _estimate_tokens(messages: list[dict]) -> int:
        """Estimate token count from messages."""
        chars = sum(len(m.get("content", "")) for m in messages)
        return int(chars / 4)  # rough 4 chars per token

    @staticmethod
    def _summarise_turns(turns: list[dict]) -> str:
        """Create a minimal summary of turns for compaction."""
        # In Sprint 2B+ this would use an LLM call
        # For Sprint 3, extract key content points
        content_parts: list[str] = []
        for turn in turns:
            role = turn.get("role", "unknown")
            content = turn.get("content", "")
            if content:
                truncated = content[:100].strip()
                content_parts.append(f"{role}: {truncated}")

        if not content_parts:
            return ""

        summary = " | ".join(content_parts)
        if len(summary) > 500:
            summary = summary[:500] + "..."

        return summary
