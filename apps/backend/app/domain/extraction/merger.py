"""Slot merger — merges new extraction results into existing slot state.

Rules (PRD 13.4):
1. Never overwrite a confident value with a lower-confidence one
2. Append to list slots with deduplication
3. Mark declined slots permanently
4. Record conflicts

References: PRD FR-23 to FR-29, PRD 13.4
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from app.domain.extraction.slot_extractor import ExtractionResult
from app.domain.models.slots import PainPoint, SlotMap, SlotValue


@dataclass
class MergeResult:
    """Result of merging extraction into existing slot state."""

    slot_map: SlotMap = field(default_factory=SlotMap)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    new_pain_points: list[PainPoint] = field(default_factory=list)
    declined_slots: list[str] = field(default_factory=list)


_CONFIDENCE_OVERWRITE_THRESHOLD: float = 0.15


def _normalise_slot_value(value: Any) -> str | None:
    """Extract a string value from various slot value representations."""
    if isinstance(value, dict):
        return value.get("value") or value.get("normalised") or value.get("raw")
    if isinstance(value, str):
        return value
    return None


def _get_confidence(value: Any) -> float:
    """Extract confidence from a slot value."""
    if isinstance(value, dict):
        return float(value.get("confidence", 0.0))
    return 0.0


class SlotMerger:
    """Merges new extraction results into existing slot state.

    Implements the merge rules from PRD Section 13.4.
    Pure function — no I/O, no side effects.
    """

    def merge(
        self,
        current: SlotMap,
        extraction: ExtractionResult,
        turn_index: int,
    ) -> MergeResult:
        """Merge extraction results into current slot map.

        Args:
            current: The current slot state.
            extraction: New extraction results.
            turn_index: The current turn index.

        Returns:
            MergeResult with updated slot map and metadata.
        """
        result = MergeResult(slot_map=deepcopy(current))

        # Process each extracted slot
        for slot_name, new_value in extraction.slots.items():
            if new_value is None:
                continue

            current_val = getattr(result.slot_map, slot_name, None)

            if isinstance(current_val, SlotValue):
                self._merge_scalar_slot(
                    result, slot_name, current_val, new_value, turn_index
                )

        # Process pain points
        for pp_data in extraction.pain_points:
            self._merge_pain_point(result, pp_data, turn_index)

        # Process current_tools
        for tool in extraction.current_tools:
            if tool not in result.slot_map.current_tools:
                result.slot_map.current_tools.append(tool)
                if "current_tools" not in result.changed:
                    result.changed.append("current_tools")

        # Process goals
        for goal in extraction.goals:
            if goal not in result.slot_map.goals:
                result.slot_map.goals.append(goal)
                if "goals" not in result.changed:
                    result.changed.append("goals")

        return result

    def _merge_scalar_slot(
        self,
        result: MergeResult,
        slot_name: str,
        current_val: SlotValue,
        new_value: dict[str, Any],
        turn_index: int,
    ) -> None:
        """Merge a scalar slot value with confidence rules."""
        new_raw = new_value.get("raw", "")
        new_val = new_value.get("value")
        new_confidence = float(new_value.get("confidence", 0.0))
        source_turn = int(new_value.get("source_turn", turn_index))

        # If slot is already declined, never overwrite
        if current_val.declined:
            result.declined_slots.append(slot_name)
            return

        # If current has no value, accept new
        if not current_val.value:
            current_val.value = new_val
            current_val.raw = new_raw
            current_val.confidence = new_confidence
            current_val.source_turn = source_turn
            current_val.normalised = new_value.get("normalised")
            result.changed.append(slot_name)
            return

        # Check overwrite rule: never overwrite if existing confidence
        # exceeds new confidence by more than the threshold
        if current_val.confidence > 0 and current_val.confidence - new_confidence > _CONFIDENCE_OVERWRITE_THRESHOLD:
            # Record conflict
            result.conflicts.append({
                "slot": slot_name,
                "existing_value": current_val.value,
                "existing_confidence": current_val.confidence,
                "new_value": new_val,
                "new_confidence": new_confidence,
                "turn_index": turn_index,
                "resolution": "kept_existing",
            })
            return

        # Accept new value
        old_value = current_val.value
        old_confidence = current_val.confidence
        current_val.value = new_val
        current_val.raw = new_raw
        current_val.confidence = new_confidence
        current_val.source_turn = source_turn
        current_val.normalised = new_value.get("normalised")
        result.changed.append(slot_name)

        # Record conflict if value changed
        if old_value and old_value != new_val:
            result.conflicts.append({
                "slot": slot_name,
                "existing_value": old_value,
                "existing_confidence": old_confidence,
                "new_value": new_val,
                "new_confidence": new_confidence,
                "turn_index": turn_index,
                "resolution": "overwritten_by_newer",
            })

    def _merge_pain_point(
        self,
        result: MergeResult,
        pp_data: dict[str, Any],
        turn_index: int,
    ) -> None:
        """Merge a pain point into the existing list with deduplication."""
        pp_label = pp_data.get("label", "")
        pp_raw = pp_data.get("raw_text", "")

        # Check for similar existing pain point
        for existing in result.slot_map.pain_points:
            if self._pain_points_equivalent(existing.label, pp_label):
                # Update confidence if new is higher
                new_conf = float(pp_data.get("confidence", 0.0))
                if new_conf > existing.confidence:
                    existing.confidence = new_conf
                return

        # Add new pain point
        new_pp = PainPoint(
            id=pp_data.get("id", f"pp_{len(result.slot_map.pain_points) + 1:02d}"),
            label=pp_label,
            raw_text=pp_raw,
            specificity=pp_data.get("specificity", "vague"),
            service_codes=pp_data.get("service_codes", []),
            confidence=float(pp_data.get("confidence", 0.0)),
            source_turn=turn_index,
        )
        result.slot_map.pain_points.append(new_pp)
        result.new_pain_points.append(new_pp)
        if "pain_points" not in result.changed:
            result.changed.append("pain_points")

    def mark_declined(self, slot_map: SlotMap, slot_name: str) -> SlotMap:
        """Mark a slot as permanently declined.

        Args:
            slot_map: The current slot map.
            slot_name: The slot to mark declined.

        Returns:
            Updated SlotMap with the slot marked declined.
        """
        updated = deepcopy(slot_map)
        slot = getattr(updated, slot_name, None)
        if isinstance(slot, SlotValue):
            slot.declined = True
        return updated

    @staticmethod
    def _pain_points_equivalent(a: str, b: str) -> bool:
        """Check if two pain point labels refer to the same issue."""
        a_lower = a.lower().strip()
        b_lower = b.lower().strip()

        if a_lower == b_lower:
            return True

        # Check significant word overlap
        a_words = set(a_lower.split())
        b_words = set(b_lower.split())
        common = a_words & b_words

        if len(common) >= min(len(a_words), len(b_words)) * 0.5:
            return True

        return False
