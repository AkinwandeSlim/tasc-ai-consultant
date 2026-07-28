"""Slot merger — merges new extraction results into existing slot state.

Rules (PRD 13.4):
1. Never overwrite a confident value with a lower-confidence one
2. Append to list slots with deduplication
3. Mark declined slots permanently
4. Record conflicts
"""

# TODO: Implement merge rules
