"""
Integration tests for the FastAPI HTTP layer.

Exercises the full API stack through httpx AsyncClient / ASGITransport.
Tests are imported from the existing API test suite to prevent duplication
while making both `pytest tests/unit/` and `pytest tests/integration/` work.

References: PRD Section 6 (API contracts), Backend Blueprint Section 6
"""

# Re-export all tests from the existing API test suite so that
# `pytest tests/integration/` discovers and runs them alongside `pytest tests/unit/`.
from tests.unit.test_api import *  # noqa: F401, F403
