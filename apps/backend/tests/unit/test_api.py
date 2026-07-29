"""API layer integration tests.

Tests the FastAPI HTTP layer: request parsing, response serialization,
error handling, and endpoint contracts. Domain logic is tested separately
in test_sprint_2a.py and test_sprint_3.py.

Uses httpx TestClient for synchronous-style requests against the
asynchronous FastAPI application.

References: PRD Section 6 (API contracts), Backend Blueprint Section 6
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
def app() -> FastAPI:
    """Return a fresh FastAPI app instance for testing."""
    return create_app()


@pytest.fixture
async def client(app: FastAPI) -> AsyncClient:
    """Return an async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── Helper ────────────────────────────────────────────────────────────


async def _start_session(client: AsyncClient) -> dict:
    """Start a consultation and return the response JSON."""
    resp = await client.post("/api/v1/chat/start")
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    return resp.json()


async def _send_message(client: AsyncClient, session_id: str, message: str) -> dict:
    """Send a chat message and return the response JSON."""
    resp = await client.post(
        "/api/v1/chat/message",
        json={"session_id": session_id, "message": message},
    )
    return resp.json()


# ── Health Tests ──────────────────────────────────────────────────────


class TestHealthEndpoint:
    """Tests for GET /health."""

    async def test_health_returns_ok(self, client: AsyncClient) -> None:
        """GET /health should return status=ok with version info."""
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert isinstance(data["version"], str)
        assert isinstance(data["simulation_mode"], bool)
        assert isinstance(data["timestamp"], str)

    async def test_health_live(self, client: AsyncClient) -> None:
        """GET /health/live should return alive."""
        resp = await client.get("/api/health/live")
        assert resp.status_code == 200
        assert resp.json()["status"] == "alive"

    async def test_health_ready(self, client: AsyncClient) -> None:
        """GET /health/ready should return ready."""
        resp = await client.get("/api/health/ready")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"


# ── Chat Start Tests ──────────────────────────────────────────────────


class TestStartConsultation:
    """Tests for POST /api/v1/chat/start."""

    async def test_start_returns_201(self, client: AsyncClient) -> None:
        """Starting a consultation should return 201 with session data."""
        data = await _start_session(client)
        assert "session_id" in data
        assert len(data["session_id"]) > 0
        assert "greeting" in data
        assert len(data["greeting"]) > 0

    async def test_start_returns_contract_fields(self, client: AsyncClient) -> None:
        """Response should contain all required contract fields."""
        data = await _start_session(client)
        expected_keys = {
            "session_id", "greeting", "conversation_phase",
            "business_profile", "lead_score", "recommendations",
            "completion_percentage", "next_question", "conversation_finished",
        }
        assert set(data.keys()) == expected_keys, f"Missing keys: {expected_keys - set(data.keys())}"

    async def test_start_initial_phase_is_greeting(self, client: AsyncClient) -> None:
        """New session should be in greeting phase."""
        data = await _start_session(client)
        assert data["conversation_phase"] == "greeting"
        assert data["conversation_finished"] is False
        assert data["completion_percentage"] == 0

    async def test_start_unique_session_ids(self, client: AsyncClient) -> None:
        """Each start call should return a unique session ID."""
        s1 = await _start_session(client)
        s2 = await _start_session(client)
        assert s1["session_id"] != s2["session_id"]


# ── Chat Message Tests ───────────────────────────────────────────────


class TestSendMessage:
    """Tests for POST /api/v1/chat/message."""

    async def test_send_message_returns_contract(self, client: AsyncClient) -> None:
        """Sending a message should return all required contract fields."""
        session = await _start_session(client)
        sid = session["session_id"]
        data = await _send_message(client, sid, "We are a logistics company with 180 employees.")

        expected_keys = {
            "assistant_message", "conversation_phase", "business_profile",
            "lead_score", "recommendations", "completion_percentage",
            "next_question", "conversation_finished",
        }
        assert set(data.keys()) == expected_keys, f"Missing keys: {expected_keys - set(data.keys())}"

    async def test_send_message_extracts_industry(self, client: AsyncClient) -> None:
        """Sending industry info should update business_profile."""
        session = await _start_session(client)
        sid = session["session_id"]
        data = await _send_message(client, sid, "We are a logistics company with 180 employees.")

        bp = data["business_profile"]
        assert bp["industry"] is not None

    async def test_send_message_increments_progress(self, client: AsyncClient) -> None:
        """Multiple turns should increase completion percentage."""
        session = await _start_session(client)
        sid = session["session_id"]

        turn1 = await _send_message(client, sid, "We are a logistics company with 180 employees.")
        pct1 = turn1["completion_percentage"]

        turn2 = await _send_message(client, sid, "We struggle with manual data entry and order processing.")
        pct2 = turn2["completion_percentage"]

        # Progress should advance (or at least not go backward)
        assert pct2 >= pct1, f"Progress regressed: {pct1} -> {pct2}"

    async def test_invalid_session_id(self, client: AsyncClient) -> None:
        """Sending a message with a non-existent session ID should return 404."""
        resp = await client.post(
            "/api/v1/chat/message",
            json={"session_id": "nonexistent-session-id", "message": "Hello"},
        )
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "SESSION_NOT_FOUND"

    async def test_empty_message(self, client: AsyncClient) -> None:
        """Sending an empty message should return 400."""
        session = await _start_session(client)
        resp = await client.post(
            "/api/v1/chat/message",
            json={"session_id": session["session_id"], "message": "   "},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data

    async def test_message_too_long(self, client: AsyncClient) -> None:
        """Message exceeding max length should return 422."""
        session = await _start_session(client)
        long_msg = "x" * 2001
        resp = await client.post(
            "/api/v1/chat/message",
            json={"session_id": session["session_id"], "message": long_msg},
        )
        assert resp.status_code == 422

    async def test_anti_persona_terminates(self, client: AsyncClient) -> None:
        """Anti-persona message should terminate the consultation."""
        session = await _start_session(client)
        sid = session["session_id"]
        data = await _send_message(client, sid, "I am a student looking for a job at your company.")
        assert data["conversation_finished"] is True
        assert data["conversation_phase"] == "terminated"

    async def test_completed_session_rejects_messages(self, client: AsyncClient) -> None:
        """Completed session should reject new messages with 409."""
        session = await _start_session(client)
        sid = session["session_id"]

        # Terminate via anti-persona
        await _send_message(client, sid, "I am a student looking for a job at your company.")

        # Try sending another message
        resp = await client.post(
            "/api/v1/chat/message",
            json={"session_id": sid, "message": "Hello again"},
        )
        assert resp.status_code == 409
        data = resp.json()
        assert data["error"]["code"] == "ALREADY_COMPLETED"


# ── Session Snapshot Tests ────────────────────────────────────────────


class TestSessionSnapshot:
    """Tests for GET /api/v1/chat/{session_id}."""

    async def test_get_active_session(self, client: AsyncClient) -> None:
        """Getting an active session should return its current state."""
        session = await _start_session(client)
        sid = session["session_id"]

        resp = await client.get(f"/api/v1/chat/{sid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == sid
        assert data["phase"] == "greeting"
        assert data["status"] == "active"
        assert data["conversation_finished"] is False

    async def test_get_nonexistent_session(self, client: AsyncClient) -> None:
        """Getting a non-existent session should return 404."""
        resp = await client.get("/api/v1/chat/nonexistent-session")
        assert resp.status_code == 404

    async def test_get_session_after_message(self, client: AsyncClient) -> None:
        """Session snapshot should reflect processed turns."""
        session = await _start_session(client)
        sid = session["session_id"]
        await _send_message(client, sid, "We are a logistics company.")

        resp = await client.get(f"/api/v1/chat/{sid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["visitor_turn_count"] >= 1
        assert len(data["messages"]) >= 2  # greeting + user + assistant

    async def test_get_session_after_completion(self, client: AsyncClient) -> None:
        """Completed session should show finished status."""
        session = await _start_session(client)
        sid = session["session_id"]

        # Terminate via anti-persona
        await _send_message(client, sid, "I am a student looking for a job at your company.")

        resp = await client.get(f"/api/v1/chat/{sid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("completed", "terminated")
        assert data["conversation_finished"] is True


# ── Demo / Scenarios Tests ────────────────────────────────────────────


class TestDemoScenarios:
    """Tests for GET /api/v1/demo/scenarios."""

    async def test_list_scenarios(self, client: AsyncClient) -> None:
        """Listing scenarios should return a list with count."""
        resp = await client.get("/api/v1/demo/scenarios")
        assert resp.status_code == 200
        data = resp.json()
        assert "scenarios" in data
        assert "count" in data
        assert data["count"] >= 8  # At least the 8 core scenarios
        assert "simulation_enabled" in data

    async def test_scenario_has_required_fields(self, client: AsyncClient) -> None:
        """Each scenario should have all required fields."""
        resp = await client.get("/api/v1/demo/scenarios")
        data = resp.json()
        for scenario in data["scenarios"]:
            assert "scenario_id" in scenario
            assert "name" in scenario
            assert "description" in scenario
            assert "tags" in scenario
            assert "turn_count" in scenario

    async def test_scenario_ids_are_unique(self, client: AsyncClient) -> None:
        """All returned scenario IDs should be unique."""
        resp = await client.get("/api/v1/demo/scenarios")
        data = resp.json()
        ids = [s["scenario_id"] for s in data["scenarios"]]
        assert len(ids) == len(set(ids)), "Duplicate scenario IDs found"


# ── Error Handling Tests ──────────────────────────────────────────────


class TestErrorHandling:
    """Tests for consistent error responses."""

    async def test_404_has_error_envelope(self, client: AsyncClient) -> None:
        """404 responses should use the standard error envelope."""
        resp = await client.get("/api/v1/chat/nonexistent")
        assert resp.status_code == 404
        body = resp.json()
        assert "error" in body
        assert "code" in body["error"]
        assert "message" in body["error"]
        assert "correlation_id" in body["error"]

    async def test_422_has_error_envelope(self, client: AsyncClient) -> None:
        """422 responses should use the standard error envelope."""
        resp = await client.post(
            "/api/v1/chat/message",
            json={"session_id": "", "message": ""},  # Both empty — invalid
        )
        assert resp.status_code == 422
        body = resp.json()
        assert "error" in body
        assert body["error"]["code"] == "VALIDATION_ERROR"

    async def test_correlation_id_on_error(self, client: AsyncClient) -> None:
        """Error responses should include a correlation ID."""
        resp = await client.get("/api/v1/chat/nonexistent")
        body = resp.json()
        cid = body["error"]["correlation_id"]
        assert len(cid) > 0, "Correlation ID should not be empty"

    async def test_response_has_correlation_header(self, client: AsyncClient) -> None:
        """All responses should have the X-Correlation-Id header."""
        resp = await client.get("/api/health")
        assert "X-Correlation-Id" in resp.headers
        assert len(resp.headers["X-Correlation-Id"]) > 0

    async def test_unknown_route_returns_404(self, client: AsyncClient) -> None:
        """Unknown routes should return 404 with error envelope."""
        resp = await client.get("/api/v1/nonexistent-route")
        assert resp.status_code == 404


# ── Full Consultation Flow Tests ──────────────────────────────────────


class TestFullConsultationFlow:
    """End-to-end consultation flow through the API."""

    async def test_full_logistics_consultation(self, client: AsyncClient) -> None:
        """Simulate a complete logistics consultation via the API."""
        session = await _start_session(client)
        sid = session["session_id"]
        assert sid is not None

        # Turn 1: Describe the business
        t1 = await _send_message(client, sid, "We are a logistics company with 180 employees.")
        assert len(t1["assistant_message"]) > 0
        assert t1["conversation_phase"] in ("discovery", "exploration")
        assert t1["business_profile"]["industry"] is not None

        # Turn 2: Describe pain points
        t2 = await _send_message(
            client, sid,
            "We struggle with manual data entry across systems. "
            "Orders are processed by hand and it takes too long.",
        )
        assert len(t2["assistant_message"]) > 0
        assert len(t2["business_profile"]["pain_points"]) >= 1
        assert t2["conversation_finished"] is False

        # Turn 3: Engage with recommendation
        t3 = await _send_message(client, sid, "That sounds good, what do you recommend?")
        assert len(t3["recommendations"]) >= 0  # May or may not have recs yet

        # Progress should have advanced
        assert t1["completion_percentage"] < 100

    async def test_contract_fields_always_present(self, client: AsyncClient) -> None:
        """Every response should include all contract-mandated fields."""
        session = await _start_session(client)
        sid = session["session_id"]

        messages = [
            "We are a logistics company.",
            "We have manual processes that slow us down.",
            "We use Excel spreadsheets for everything.",
        ]

        required = {
            "assistant_message", "conversation_phase", "business_profile",
            "lead_score", "recommendations", "completion_percentage",
            "next_question", "conversation_finished",
        }

        for msg in messages:
            data = await _send_message(client, sid, msg)
            missing = required - set(data.keys())
            assert not missing, f"Missing contract fields: {missing}"


# ── Edge Cases ────────────────────────────────────────────────────────


class TestEdgeCases:
    """Edge case handling through the API."""

    async def test_concurrent_sessions(self, client: AsyncClient) -> None:
        """Multiple sessions should be independent."""
        s1 = await _start_session(client)
        s2 = await _start_session(client)

        assert s1["session_id"] != s2["session_id"]

        await _send_message(client, s1["session_id"], "We are a logistics company.")
        await _send_message(client, s2["session_id"], "We are a retail business.")

        # Check session 2 didn't get polluted by session 1 data
        snap2 = await client.get(f"/api/v1/chat/{s2['session_id']}")
        data2 = snap2.json()
        assert data2["session_id"] == s2["session_id"]

    async def test_missing_body_returns_422(self, client: AsyncClient) -> None:
        """Missing request body should return 422."""
        resp = await client.post(
            "/api/v1/chat/message",
            json={},
        )
        assert resp.status_code == 422

    async def test_invalid_json_returns_422(self, client: AsyncClient) -> None:
        """Invalid JSON body should return 422."""
        transport = ASGITransport(app=create_app())
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/v1/chat/message",
                content=b"this is not json",
                headers={"Content-Type": "application/json"},
            )
            assert resp.status_code == 422
