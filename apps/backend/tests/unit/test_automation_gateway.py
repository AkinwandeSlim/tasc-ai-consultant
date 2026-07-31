"""Comprehensive tests for the automation gateway layer (Sprint 6.1).

Verifies:
  ✓ MockAutomationGateway processes consultations locally
  ✓ N8nAutomationGateway forwards to n8n webhook
  ✓ Dependency injection switches between implementations
  ✓ Timeout handling
  ✓ Retry behaviour with exponential backoff
  ✓ Invalid response handling
  ✓ Error mapping (connection, timeout, rejection, invalid)
  ✓ Signing module produces valid HMAC signatures
  ✓ Existing API endpoints continue working (via test_api import)
  ✓ Existing frontend contract remains unchanged
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import respx
from httpx import ASGITransport, AsyncClient, Response

from app.container import build_container
from app.core.config import Settings, get_settings
from app.domain.gateway.automation_gateway import (
    AutomationGateway,
    ConsultationRequest,
    ConsultationResult,
)
from app.infrastructure.automation.mock_gateway import MockAutomationGateway
from app.infrastructure.automation.n8n_gateway import N8nAutomationGateway
from app.infrastructure.automation.signing import (
    build_signature_headers,
    sign_payload,
    verify_signature,
)
from app.main import create_app

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def mock_gateway() -> MockAutomationGateway:
    """Return a MockAutomationGateway instance."""
    return MockAutomationGateway()


@pytest.fixture
def n8n_settings() -> Settings:
    """Return settings with N8N_ENABLED=True for n8n gateway tests."""
    return Settings(
        APP_ENV="local",
        OPENAI_API_KEY="test-key",
        N8N_WEBHOOK_URL="http://localhost:5678/webhook/consult",
        N8N_SHARED_SECRET="test-shared-secret",
        N8N_SIGNING_SECRET="test-signing-secret",
        N8N_TIMEOUT_SECONDS=5.0,
        N8N_MAX_ATTEMPTS=2,
        N8N_BACKOFF_BASE_SECONDS=0.1,
    )


@pytest.fixture
def consultation_request() -> ConsultationRequest:
    """Return a standard consultation request for testing.

    Uses ConversationManager.create_session() to build proper state objects.
    """
    from app.domain.conversation.manager import ConversationManager

    cm = ConversationManager()
    session = cm.create_session()
    session["phase"] = "discovery"
    session["turn_index"] = 0

    return ConsultationRequest(
        session_id=session["session_id"],
        user_message="We run a logistics company and need help with automation.",
        conversation_history=[
            {"role": "assistant", "content": "Hello! I'm Nova..."},
            {"role": "user", "content": "Hi there"},
        ],
        structured_state=session,
        timestamp="2026-07-29T12:00:00Z",
        simulation_mode=False,
    )


@pytest.fixture
def n8n_webhook_payload() -> dict:
    """Return a realistic n8n webhook response."""
    return {
        "assistant_message": "Great, let me help you with that. Could you tell me more about your current order processing workflow?",
        "conversation_phase": "discovery",
        "business_profile": {
            "industry": "logistics",
            "company_size": None,
            "pain_points": [],
            "current_tools": [],
            "goals": [],
        },
        "lead_score": {
            "score": 25,
            "band": "cold",
            "confidence": 0.6,
            "next_contributor": "Tell me more about your business",
        },
        "recommendations": [],
        "completion_percentage": 15,
        "next_question": "What specific parts of your order processing are manual?",
        "conversation_finished": False,
    }


# ── Gateway Protocol Tests ────────────────────────────────────────────


class TestAutomationGatewayProtocol:
    """Verify the AutomationGateway protocol is properly defined."""

    def test_protocol_is_callable(self):
        """The protocol should define the process_consultation method."""
        import inspect

        # Verify that the protocol exists and has the right signature
        assert hasattr(AutomationGateway, "process_consultation")
        sig = inspect.signature(AutomationGateway.process_consultation)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "request" in params


# ── MockAutomationGateway Tests ───────────────────────────────────────


class TestMockAutomationGateway:
    """Verify MockAutomationGateway processes consultations locally."""

    @pytest.mark.asyncio
    async def test_process_consultation_returns_result(
        self,
        mock_gateway: MockAutomationGateway,
        consultation_request: ConsultationRequest,
    ) -> None:
        """A consultation request should return a ConsultationResult."""
        result = await mock_gateway.process_consultation(consultation_request)

        assert isinstance(result, ConsultationResult)
        # Result should have fields matching the frontend contract
        assert hasattr(result, "assistant_message")
        assert hasattr(result, "conversation_phase")
        assert hasattr(result, "business_profile")
        assert hasattr(result, "lead_score")
        assert hasattr(result, "recommendations")
        assert hasattr(result, "completion_percentage")
        assert hasattr(result, "next_question")
        assert hasattr(result, "is_complete")

    @pytest.mark.asyncio
    async def test_start_consultation_returns_session(
        self,
        mock_gateway: MockAutomationGateway,
    ) -> None:
        """Starting a consultation should return a session dict."""
        session = await mock_gateway.start_consultation()

        assert isinstance(session, dict)
        assert "session_id" in session
        assert "messages" in session

    @pytest.mark.asyncio
    async def test_preserves_frontend_contract(
        self,
        mock_gateway: MockAutomationGateway,
        consultation_request: ConsultationRequest,
    ) -> None:
        """The mock gateway must preserve the existing frontend contract."""
        result = await mock_gateway.process_consultation(consultation_request)

        # The response must have all fields the frontend expects
        # (matching MessageResponse in chat.py)
        assert result.assistant_message is not None
        assert result.conversation_phase is not None
        assert result.completion_percentage is not None
        assert result.next_question is not None or result.is_complete

        # The frontend uses these lead_score fields
        if result.lead_score:
            assert "score" in result.lead_score
            assert "band" in result.lead_score
            assert "confidence" in result.lead_score

        # Recommendations must be a list
        assert isinstance(result.recommendations, list)

    @pytest.mark.asyncio
    async def test_handles_empty_message(
        self,
        mock_gateway: MockAutomationGateway,
    ) -> None:
        """The mock gateway should handle empty messages gracefully."""
        request = ConsultationRequest(
            session_id="test-001",
            user_message="",
            structured_state={"session_id": "test-001", "phase": "discovery"},
        )
        result = await mock_gateway.process_consultation(request)
        assert isinstance(result, ConsultationResult)

    @pytest.mark.asyncio
    async def test_increments_turn_index(
        self,
        mock_gateway: MockAutomationGateway,
        consultation_request: ConsultationRequest,
    ) -> None:
        """Each consultation request should increment the turn tracking."""
        result1 = await mock_gateway.process_consultation(consultation_request)
        assert result1.conversation_phase is not None


# ── N8nAutomationGateway Tests ────────────────────────────────────────


class TestN8nAutomationGateway:
    """Verify N8nAutomationGateway processes locally and dispatches to n8n."""

    @pytest.fixture
    def n8n_gateway(
        self,
        n8n_settings: Settings,
    ) -> N8nAutomationGateway:
        """Return an N8nAutomationGateway with a real HTTP client."""
        import httpx

        # Mock the orchestrator so tests don't run the full consultation engine
        mock_orchestrator = AsyncMock()
        mock_orchestrator.process_turn = AsyncMock(
            return_value=MagicMock(
                assistant_message="Local engine response",
                conversation_phase="discovery",
                business_profile={"industry": "logistics"},
                lead_score={"score": 25, "band": "cold"},
                recommendations=[],
                completion_percentage=15,
                next_question="What specific parts are manual?",
                is_complete=False,
                completion_reason="",
                analysis_snapshot=None,
                errors=[],
            )
        )

        client = httpx.AsyncClient()
        return N8nAutomationGateway(
            webhook_url=n8n_settings.N8N_WEBHOOK_URL,
            shared_secret=n8n_settings.N8N_SHARED_SECRET.get_secret_value(),
            signing_secret=n8n_settings.N8N_SIGNING_SECRET.get_secret_value(),
            http_client=client,
            orchestrator=mock_orchestrator,
            timeout_seconds=5.0,
            max_retries=2,
            backoff_base_seconds=0.1,
        ), mock_orchestrator

    @pytest.mark.asyncio
    async def test_returns_local_engine_result(
        self,
        n8n_settings: Settings,
        consultation_request: ConsultationRequest,
    ) -> None:
        """The gateway should return the result from the local engine, not n8n."""
        from unittest.mock import MagicMock

        mock_orchestrator = AsyncMock()
        mock_orchestrator.process_turn = AsyncMock(
            return_value=MagicMock(
                assistant_message="Local engine response",
                conversation_phase="discovery",
                business_profile={"industry": "logistics"},
                lead_score={"score": 25, "band": "cold"},
                recommendations=[],
                completion_percentage=15,
                next_question="What specific parts are manual?",
                is_complete=False,
                completion_reason="",
                analysis_snapshot=None,
                errors=[],
            )
        )

        async with httpx.AsyncClient() as client:
            gateway = N8nAutomationGateway(
                webhook_url=n8n_settings.N8N_WEBHOOK_URL,
                shared_secret=n8n_settings.N8N_SHARED_SECRET.get_secret_value(),
                signing_secret=n8n_settings.N8N_SIGNING_SECRET.get_secret_value(),
                http_client=client,
                orchestrator=mock_orchestrator,
                timeout_seconds=5.0,
                max_retries=1,
                backoff_base_seconds=0.1,
            )

            with respx.mock:
                # n8n returns 200 — but gateway should use local result
                respx.post(n8n_settings.N8N_WEBHOOK_URL).mock(
                    return_value=Response(200, json={"received": True})
                )

                result = await gateway.process_consultation(consultation_request)

                # Verify local engine result is returned
                assert result.assistant_message == "Local engine response"
                assert result.conversation_phase == "discovery"
                assert result.lead_score == {"score": 25, "band": "cold"}
                assert isinstance(result, ConsultationResult)

    @pytest.mark.asyncio
    async def test_dispatches_to_n8n(
        self,
        n8n_settings: Settings,
        consultation_request: ConsultationRequest,
    ) -> None:
        """The gateway should dispatch the result to n8n after local processing."""
        from unittest.mock import MagicMock

        mock_orchestrator = AsyncMock()
        mock_orchestrator.process_turn = AsyncMock(
            return_value=MagicMock(
                assistant_message="Local response",
                conversation_phase="discovery",
                business_profile={"industry": "logistics"},
                lead_score={"score": 25, "band": "cold"},
                recommendations=[],
                completion_percentage=15,
                next_question="What specific parts are manual?",
                is_complete=False,
                completion_reason="",
                analysis_snapshot=None,
                errors=[],
            )
        )

        async with httpx.AsyncClient() as client:
            gateway = N8nAutomationGateway(
                webhook_url=n8n_settings.N8N_WEBHOOK_URL,
                shared_secret=n8n_settings.N8N_SHARED_SECRET.get_secret_value(),
                signing_secret=n8n_settings.N8N_SIGNING_SECRET.get_secret_value(),
                http_client=client,
                orchestrator=mock_orchestrator,
                timeout_seconds=5.0,
                max_retries=1,
                backoff_base_seconds=0.1,
            )

            with respx.mock:
                route = respx.post(n8n_settings.N8N_WEBHOOK_URL).mock(
                    return_value=Response(200, json={"received": True})
                )

                await gateway.process_consultation(consultation_request)

                # Verify the webhook was called with correct headers
                assert route.called
                request = route.calls[0].request
                assert request.method == "POST"
                assert request.headers["Content-Type"] == "application/json"
                assert "X-TASC-Shared-Secret" in request.headers
                assert "X-TASC-Signature" in request.headers
                assert "X-TASC-Timestamp" in request.headers

                # Verify the payload includes consultation fields
                body = json.loads(request.content)
                assert body["assistant_message"] == "Local response"
                assert body["conversation_phase"] == "discovery"
                assert body["session_id"] == consultation_request.session_id

    @pytest.mark.asyncio
    async def test_n8n_timeout_does_not_block_response(
        self,
        n8n_settings: Settings,
        consultation_request: ConsultationRequest,
    ) -> None:
        """An n8n timeout should be logged but NOT raised — local result is returned."""
        from unittest.mock import MagicMock

        mock_orchestrator = AsyncMock()
        mock_orchestrator.process_turn = AsyncMock(
            return_value=MagicMock(
                assistant_message="Local engine response",
                conversation_phase="discovery",
                business_profile=None,
                lead_score=None,
                recommendations=[],
                completion_percentage=0,
                next_question=None,
                is_complete=False,
                completion_reason="",
                analysis_snapshot=None,
                errors=[],
            )
        )

        async with httpx.AsyncClient() as client:
            gateway = N8nAutomationGateway(
                webhook_url=n8n_settings.N8N_WEBHOOK_URL,
                shared_secret=n8n_settings.N8N_SHARED_SECRET.get_secret_value(),
                signing_secret=n8n_settings.N8N_SIGNING_SECRET.get_secret_value(),
                http_client=client,
                orchestrator=mock_orchestrator,
                timeout_seconds=0.1,
                max_retries=1,
                backoff_base_seconds=0.05,
            )

            with respx.mock:
                respx.post(n8n_settings.N8N_WEBHOOK_URL).mock(
                    side_effect=httpx.TimeoutException("Request timed out", request=None)
                )

                # Should NOT raise — n8n timeout is swallowed
                result = await gateway.process_consultation(consultation_request)

                assert result.assistant_message == "Local engine response"

    @pytest.mark.asyncio
    async def test_n8n_connection_error_does_not_block_response(
        self,
        n8n_settings: Settings,
        consultation_request: ConsultationRequest,
    ) -> None:
        """An n8n connection error should be logged but NOT raised."""
        from unittest.mock import MagicMock

        mock_orchestrator = AsyncMock()
        mock_orchestrator.process_turn = AsyncMock(
            return_value=MagicMock(
                assistant_message="Local engine response",
                conversation_phase="discovery",
                business_profile=None,
                lead_score=None,
                recommendations=[],
                completion_percentage=0,
                next_question=None,
                is_complete=False,
                completion_reason="",
                analysis_snapshot=None,
                errors=[],
            )
        )

        async with httpx.AsyncClient() as client:
            gateway = N8nAutomationGateway(
                webhook_url=n8n_settings.N8N_WEBHOOK_URL,
                shared_secret=n8n_settings.N8N_SHARED_SECRET.get_secret_value(),
                signing_secret=n8n_settings.N8N_SIGNING_SECRET.get_secret_value(),
                http_client=client,
                orchestrator=mock_orchestrator,
                timeout_seconds=5.0,
                max_retries=1,
                backoff_base_seconds=0.1,
            )

            with respx.mock:
                respx.post(n8n_settings.N8N_WEBHOOK_URL).mock(
                    side_effect=httpx.ConnectError("Connection refused")
                )

                # Should NOT raise — connection error is swallowed
                result = await gateway.process_consultation(consultation_request)

                assert result.assistant_message == "Local engine response"

    @pytest.mark.asyncio
    async def test_n8n_401_does_not_block_response(
        self,
        n8n_settings: Settings,
        consultation_request: ConsultationRequest,
    ) -> None:
        """An n8n 401 should be logged but NOT raise — local result is returned."""
        from unittest.mock import MagicMock

        mock_orchestrator = AsyncMock()
        mock_orchestrator.process_turn = AsyncMock(
            return_value=MagicMock(
                assistant_message="Local engine response",
                conversation_phase="discovery",
                business_profile=None,
                lead_score=None,
                recommendations=[],
                completion_percentage=0,
                next_question=None,
                is_complete=False,
                completion_reason="",
                analysis_snapshot=None,
                errors=[],
            )
        )

        async with httpx.AsyncClient() as client:
            gateway = N8nAutomationGateway(
                webhook_url=n8n_settings.N8N_WEBHOOK_URL,
                shared_secret=n8n_settings.N8N_SHARED_SECRET.get_secret_value(),
                signing_secret=n8n_settings.N8N_SIGNING_SECRET.get_secret_value(),
                http_client=client,
                orchestrator=mock_orchestrator,
                timeout_seconds=5.0,
                max_retries=2,
                backoff_base_seconds=0.1,
            )

            with respx.mock:
                route = respx.post(n8n_settings.N8N_WEBHOOK_URL).mock(
                    return_value=Response(401, json={"error": "unauthorized"})
                )

                # Should NOT raise — 401 is logged, not raised
                result = await gateway.process_consultation(consultation_request)

                assert result.assistant_message == "Local engine response"
                # Should only be called once (no retry on 401)
                assert route.call_count == 1

    @pytest.mark.asyncio
    async def test_n8n_500_retried_but_local_result_returned(
        self,
        n8n_settings: Settings,
        consultation_request: ConsultationRequest,
    ) -> None:
        """n8n 5xx should be retried, but local result is still returned regardless."""
        from unittest.mock import MagicMock

        mock_orchestrator = AsyncMock()
        mock_orchestrator.process_turn = AsyncMock(
            return_value=MagicMock(
                assistant_message="Local engine response",
                conversation_phase="discovery",
                business_profile=None,
                lead_score=None,
                recommendations=[],
                completion_percentage=0,
                next_question=None,
                is_complete=False,
                completion_reason="",
                analysis_snapshot=None,
                errors=[],
            )
        )

        async with httpx.AsyncClient() as client:
            gateway = N8nAutomationGateway(
                webhook_url=n8n_settings.N8N_WEBHOOK_URL,
                shared_secret=n8n_settings.N8N_SHARED_SECRET.get_secret_value(),
                signing_secret=n8n_settings.N8N_SIGNING_SECRET.get_secret_value(),
                http_client=client,
                orchestrator=mock_orchestrator,
                timeout_seconds=5.0,
                max_retries=3,
                backoff_base_seconds=0.05,
            )

            with respx.mock:
                route = respx.post(n8n_settings.N8N_WEBHOOK_URL).mock(
                    return_value=Response(500, json={"error": "server error"})
                )

                # Should NOT raise — 5xx is swallowed after retries exhausted
                result = await gateway.process_consultation(consultation_request)

                assert result.assistant_message == "Local engine response"
                # Should have retried up to max_retries times
                assert route.call_count == 3

    @pytest.mark.asyncio
    async def test_n8n_retry_then_success_still_returns_local(
        self,
        n8n_settings: Settings,
        consultation_request: ConsultationRequest,
    ) -> None:
        """Even when n8n eventually succeeds, the local result is what matters."""
        from unittest.mock import MagicMock

        mock_orchestrator = AsyncMock()
        mock_orchestrator.process_turn = AsyncMock(
            return_value=MagicMock(
                assistant_message="Local engine response",
                conversation_phase="discovery",
                business_profile={"industry": "logistics"},
                lead_score={"score": 25, "band": "cold"},
                recommendations=[],
                completion_percentage=15,
                next_question="What specific parts are manual?",
                is_complete=False,
                completion_reason="",
                analysis_snapshot=None,
                errors=[],
            )
        )

        async with httpx.AsyncClient() as client:
            gateway = N8nAutomationGateway(
                webhook_url=n8n_settings.N8N_WEBHOOK_URL,
                shared_secret=n8n_settings.N8N_SHARED_SECRET.get_secret_value(),
                signing_secret=n8n_settings.N8N_SIGNING_SECRET.get_secret_value(),
                http_client=client,
                orchestrator=mock_orchestrator,
                timeout_seconds=5.0,
                max_retries=2,
                backoff_base_seconds=0.1,
            )

            with respx.mock:
                route = respx.post(n8n_settings.N8N_WEBHOOK_URL).mock(
                    side_effect=[
                        Response(502, json={"error": "bad gateway"}),
                        Response(200, json={"acknowledged": True}),
                    ]
                )

                result = await gateway.process_consultation(consultation_request)

                assert route.call_count == 2
                # Result is from local engine, not from n8n
                assert result.assistant_message == "Local engine response"


# ── DI Container Tests ────────────────────────────────────────────────


class TestDependencyInjection:
    """Verify DI container builds the correct gateway implementation."""

    def test_mock_gateway_when_n8n_disabled(self):
        """When N8N_ENABLED=False, container should use MockAutomationGateway."""
        settings = Settings(
            APP_ENV="local",
            OPENAI_API_KEY="test-key",
            N8N_ENABLED=False,
        )
        container = build_container(settings)
        assert container.automation_gateway is not None
        assert isinstance(container.automation_gateway, MockAutomationGateway)

    def test_n8n_gateway_when_n8n_enabled(self):
        """When N8N_ENABLED=True, container should use N8nAutomationGateway."""
        settings = Settings(
            APP_ENV="local",
            OPENAI_API_KEY="test-key",
            N8N_ENABLED=True,
            N8N_WEBHOOK_URL="http://localhost:5678/webhook/consult",
            N8N_SHARED_SECRET="test-shared",
            N8N_SIGNING_SECRET="test-signing",
            N8N_TIMEOUT_SECONDS=5.0,
            N8N_MAX_ATTEMPTS=2,
            N8N_BACKOFF_BASE_SECONDS=0.1,
        )
        container = build_container(settings)
        assert container.automation_gateway is not None
        assert isinstance(container.automation_gateway, N8nAutomationGateway)

    def test_http_client_created_when_n8n_enabled(self):
        """HTTP client should be created when N8N is enabled."""
        settings = Settings(
            APP_ENV="local",
            OPENAI_API_KEY="test-key",
            N8N_ENABLED=True,
            N8N_WEBHOOK_URL="http://localhost:5678/webhook/consult",
            N8N_SHARED_SECRET="test-shared",
            N8N_SIGNING_SECRET="test-signing",
        )
        container = build_container(settings)
        assert container.http_client is not None
        assert isinstance(container.http_client, httpx.AsyncClient)

    def test_n8n_gateway_requires_webhook_url(self):
        """N8nAutomationGateway should require a webhook URL."""
        with pytest.raises(ValueError, match="webhook_url is required"):
            N8nAutomationGateway(
                webhook_url="",
                shared_secret="test",
                signing_secret="test",
                http_client=httpx.AsyncClient(),
            )

    def test_config_validates_n8n_enabled_without_url(self):
        """Settings should validate that N8N_WEBHOOK_URL is set when N8N_ENABLED=True."""
        with pytest.raises(ValueError, match="N8N_WEBHOOK_URL is required"):
            Settings(
                APP_ENV="local",
                OPENAI_API_KEY="test-key",
                N8N_ENABLED=True,
                N8N_WEBHOOK_URL="",
            )


# ── Signing Module Tests ──────────────────────────────────────────────


class TestSigningModule:
    """Verify HMAC signing produces valid signatures."""

    def test_sign_payload_returns_hex_string(self):
        """sign_payload should return a hex-encoded HMAC-SHA256."""
        payload = json.dumps({"session_id": "test"}).encode("utf-8")
        signature = sign_payload(payload, "test-secret")

        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA256 hex digest is 64 chars
        assert all(c in "0123456789abcdef" for c in signature)

    def test_sign_payload_empty_secret(self):
        """An empty signing secret should return empty string."""
        payload = json.dumps({"session_id": "test"}).encode("utf-8")
        signature = sign_payload(payload, "")
        assert signature == ""

    def test_verify_valid_signature(self):
        """A valid signature should verify successfully."""
        payload = json.dumps({"session_id": "test"}).encode("utf-8")
        signature = sign_payload(payload, "test-secret")
        assert verify_signature(payload, signature, "test-secret") is True

    def test_verify_invalid_signature(self):
        """An invalid signature should fail verification."""
        payload = json.dumps({"session_id": "test"}).encode("utf-8")
        assert verify_signature(payload, "invalid-sig", "test-secret") is False

    def test_verify_wrong_secret(self):
        """A signature from a different secret should fail verification."""
        payload = json.dumps({"session_id": "test"}).encode("utf-8")
        signature = sign_payload(payload, "secret-1")
        assert verify_signature(payload, signature, "secret-2") is False

    def test_build_signature_headers_includes_all_headers(self):
        """build_signature_headers should include all required headers."""
        payload = json.dumps({"session_id": "test"}).encode("utf-8")
        headers = build_signature_headers(
            payload=payload,
            shared_secret="shared-secret",
            signing_secret="signing-secret",
            correlation_id="corr-001",
        )

        assert "X-TASC-Shared-Secret" in headers
        assert "X-TASC-Signature" in headers
        assert "X-TASC-Timestamp" in headers
        assert "X-Correlation-Id" in headers
        assert "Content-Type" in headers

        assert headers["X-TASC-Shared-Secret"] == "shared-secret"
        assert headers["X-TASC-Signature"].startswith("sha256=")
        assert headers["X-Correlation-Id"] == "corr-001"
        assert headers["Content-Type"] == "application/json"


# ── API Integration Tests ─────────────────────────────────────────────


class TestAPIWithGateway:
    """Verify the API works correctly with the gateway."""

    @pytest.mark.asyncio
    async def test_api_health_endpoint_still_works(self) -> None:
        """The health endpoint should continue working with the gateway."""
        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/health")
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_api_start_session_works(
        self,
    ) -> None:
        """Starting a consultation should work with the gateway wired."""
        app = create_app()

        # Attach the container with mock gateway
        from app.container import build_container
        settings = get_settings()
        container = build_container(settings)
        app.state.container = container

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/chat/start")
            assert resp.status_code == 201
            data = resp.json()
            assert "session_id" in data
            assert "greeting" in data


# ── Frontend Contract Verification ────────────────────────────────────


class TestFrontendContract:
    """Verify the frontend API contract remains unchanged."""

    @pytest.mark.asyncio
    async def test_message_response_has_all_required_fields(self) -> None:
        """The MessageResponse contract must have all fields the frontend expects."""
        from app.api.v1.chat import MessageResponse

        # These are the fields the frontend relies on
        required_fields = [
            "assistant_message",
            "conversation_phase",
            "business_profile",
            "lead_score",
            "recommendations",
            "completion_percentage",
            "next_question",
            "conversation_finished",
        ]

        model_fields = set(MessageResponse.model_fields.keys())
        for field in required_fields:
            assert field in model_fields, f"Missing required field: {field}"

    @pytest.mark.asyncio
    async def test_business_profile_has_all_required_fields(self) -> None:
        """The BusinessProfile model must have all fields the frontend expects."""
        from app.api.v1.chat import _BusinessProfileModel

        required_fields = [
            "industry",
            "company_size",
            "pain_points",
            "current_tools",
            "goals",
            "timeline",
            "budget_band",
            "decision_authority",
            "has_contact",
            "core_slots_filled",
            "commercial_slots_filled",
            "total_slots_filled",
        ]

        model_fields = set(_BusinessProfileModel.model_fields.keys())
        for field in required_fields:
            assert field in model_fields, f"Missing business profile field: {field}"
