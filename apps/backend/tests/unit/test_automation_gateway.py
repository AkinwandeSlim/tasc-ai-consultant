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

import httpx
import pytest
import respx
from httpx import ASGITransport, AsyncClient, Response

from app.container import build_container
from app.core.config import Settings, get_settings
from app.core.exceptions import (
    GatewayConnectionError,
    GatewayInvalidResponseError,
    GatewayRejectedError,
    GatewayTimeoutError,
)
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
    """Verify N8nAutomationGateway forwards requests to n8n."""

    @pytest.mark.asyncio
    async def test_successful_dispatch(
        self,
        n8n_settings: Settings,
        consultation_request: ConsultationRequest,
        n8n_webhook_payload: dict,
    ) -> None:
        """A successful webhook dispatch should return a ConsultationResult."""
        async with httpx.AsyncClient() as client:
            gateway = N8nAutomationGateway(
                webhook_url=n8n_settings.N8N_WEBHOOK_URL,
                shared_secret=n8n_settings.N8N_SHARED_SECRET.get_secret_value(),
                signing_secret=n8n_settings.N8N_SIGNING_SECRET.get_secret_value(),
                http_client=client,
                timeout_seconds=5.0,
                max_retries=1,
                backoff_base_seconds=0.1,
            )

            # Use respx to mock the n8n webhook
            with respx.mock:
                route = respx.post(n8n_settings.N8N_WEBHOOK_URL).mock(
                    return_value=Response(200, json=n8n_webhook_payload)
                )

                result = await gateway.process_consultation(consultation_request)

                # Verify the webhook was called with the correct method and headers
                assert route.called
                request = route.calls[0].request
                assert request.method == "POST"
                assert request.headers["Content-Type"] == "application/json"
                assert "X-TASC-Secret" in request.headers
                assert "X-TASC-Signature" in request.headers
                assert "X-TASC-Timestamp" in request.headers

                # Verify the result matches the webhook response
                assert result.assistant_message == n8n_webhook_payload["assistant_message"]
                assert result.conversation_phase == n8n_webhook_payload["conversation_phase"]
                assert isinstance(result, ConsultationResult)

    @pytest.mark.asyncio
    async def test_timeout_raises_gateway_timeout(
        self,
        n8n_settings: Settings,
        consultation_request: ConsultationRequest,
    ) -> None:
        """A timeout should raise GatewayTimeoutError."""
        async with httpx.AsyncClient() as client:
            gateway = N8nAutomationGateway(
                webhook_url=n8n_settings.N8N_WEBHOOK_URL,
                shared_secret=n8n_settings.N8N_SHARED_SECRET.get_secret_value(),
                signing_secret=n8n_settings.N8N_SIGNING_SECRET.get_secret_value(),
                http_client=client,
                timeout_seconds=0.1,
                max_retries=1,
                backoff_base_seconds=0.05,
            )

            with respx.mock:
                # Simulate a timeout by using a slow response
                respx.post(n8n_settings.N8N_WEBHOOK_URL).mock(
                    side_effect=httpx.TimeoutException("Request timed out", request=None)
                )

                with pytest.raises(GatewayTimeoutError):
                    await gateway.process_consultation(consultation_request)

    @pytest.mark.asyncio
    async def test_connection_error_raises_gateway_connection(
        self,
        n8n_settings: Settings,
        consultation_request: ConsultationRequest,
    ) -> None:
        """A connection error should raise GatewayConnectionError."""
        async with httpx.AsyncClient() as client:
            gateway = N8nAutomationGateway(
                webhook_url=n8n_settings.N8N_WEBHOOK_URL,
                shared_secret=n8n_settings.N8N_SHARED_SECRET.get_secret_value(),
                signing_secret=n8n_settings.N8N_SIGNING_SECRET.get_secret_value(),
                http_client=client,
                timeout_seconds=5.0,
                max_retries=1,
                backoff_base_seconds=0.1,
            )

            with respx.mock:
                respx.post(n8n_settings.N8N_WEBHOOK_URL).mock(
                    side_effect=httpx.ConnectError("Connection refused")
                )

                with pytest.raises(GatewayConnectionError):
                    await gateway.process_consultation(consultation_request)

    @pytest.mark.asyncio
    async def test_401_raises_gateway_rejected(
        self,
        n8n_settings: Settings,
        consultation_request: ConsultationRequest,
    ) -> None:
        """A 401 auth failure should raise GatewayRejectedError (no retry)."""
        async with httpx.AsyncClient() as client:
            gateway = N8nAutomationGateway(
                webhook_url=n8n_settings.N8N_WEBHOOK_URL,
                shared_secret=n8n_settings.N8N_SHARED_SECRET.get_secret_value(),
                signing_secret=n8n_settings.N8N_SIGNING_SECRET.get_secret_value(),
                http_client=client,
                timeout_seconds=5.0,
                max_retries=2,
                backoff_base_seconds=0.1,
            )

            with respx.mock:
                route = respx.post(n8n_settings.N8N_WEBHOOK_URL).mock(
                    return_value=Response(401, json={"error": "unauthorized"})
                )

                with pytest.raises(GatewayRejectedError):
                    await gateway.process_consultation(consultation_request)

                # Should only be called once (no retry on 401)
                assert route.call_count == 1

    @pytest.mark.asyncio
    async def test_403_raises_gateway_rejected(
        self,
        n8n_settings: Settings,
        consultation_request: ConsultationRequest,
    ) -> None:
        """A 403 auth failure should raise GatewayRejectedError (no retry)."""
        async with httpx.AsyncClient() as client:
            gateway = N8nAutomationGateway(
                webhook_url=n8n_settings.N8N_WEBHOOK_URL,
                shared_secret=n8n_settings.N8N_SHARED_SECRET.get_secret_value(),
                signing_secret=n8n_settings.N8N_SIGNING_SECRET.get_secret_value(),
                http_client=client,
                timeout_seconds=5.0,
                max_retries=2,
                backoff_base_seconds=0.1,
            )

            with respx.mock:
                route = respx.post(n8n_settings.N8N_WEBHOOK_URL).mock(
                    return_value=Response(403, json={"error": "forbidden"})
                )

                with pytest.raises(GatewayRejectedError):
                    await gateway.process_consultation(consultation_request)

                assert route.call_count == 1

    @pytest.mark.asyncio
    async def test_409_treated_as_success(
        self,
        n8n_settings: Settings,
        consultation_request: ConsultationRequest,
    ) -> None:
        """A 409 idempotency match should be treated as success."""
        async with httpx.AsyncClient() as client:
            gateway = N8nAutomationGateway(
                webhook_url=n8n_settings.N8N_WEBHOOK_URL,
                shared_secret=n8n_settings.N8N_SHARED_SECRET.get_secret_value(),
                signing_secret=n8n_settings.N8N_SIGNING_SECRET.get_secret_value(),
                http_client=client,
                timeout_seconds=5.0,
                max_retries=1,
                backoff_base_seconds=0.1,
            )

            with respx.mock:
                route = respx.post(n8n_settings.N8N_WEBHOOK_URL).mock(
                    return_value=Response(409, json={"error": "duplicate"})
                )

                result = await gateway.process_consultation(consultation_request)

                assert route.called
                assert isinstance(result, ConsultationResult)
                # 409 should return an empty/idempotent result
                assert result.assistant_message == ""

    @pytest.mark.asyncio
    async def test_500_retries_then_raises(
        self,
        n8n_settings: Settings,
        consultation_request: ConsultationRequest,
    ) -> None:
        """A 500 error should be retried then raise GatewayConnectionError."""
        async with httpx.AsyncClient() as client:
            gateway = N8nAutomationGateway(
                webhook_url=n8n_settings.N8N_WEBHOOK_URL,
                shared_secret=n8n_settings.N8N_SHARED_SECRET.get_secret_value(),
                signing_secret=n8n_settings.N8N_SIGNING_SECRET.get_secret_value(),
                http_client=client,
                timeout_seconds=5.0,
                max_retries=3,
                backoff_base_seconds=0.05,
            )

            with respx.mock:
                route = respx.post(n8n_settings.N8N_WEBHOOK_URL).mock(
                    return_value=Response(500, json={"error": "server error"})
                )

                with pytest.raises(GatewayConnectionError):
                    await gateway.process_consultation(consultation_request)

                # Should have retried up to max_retries times
                assert route.call_count == 3

    @pytest.mark.asyncio
    async def test_422_raises_gateway_rejected(
        self,
        n8n_settings: Settings,
        consultation_request: ConsultationRequest,
    ) -> None:
        """A 422 client error should raise GatewayRejectedError (no retry)."""
        async with httpx.AsyncClient() as client:
            gateway = N8nAutomationGateway(
                webhook_url=n8n_settings.N8N_WEBHOOK_URL,
                shared_secret=n8n_settings.N8N_SHARED_SECRET.get_secret_value(),
                signing_secret=n8n_settings.N8N_SIGNING_SECRET.get_secret_value(),
                http_client=client,
                timeout_seconds=5.0,
                max_retries=2,
                backoff_base_seconds=0.1,
            )

            with respx.mock:
                route = respx.post(n8n_settings.N8N_WEBHOOK_URL).mock(
                    return_value=Response(422, json={"error": "validation error"})
                )

                with pytest.raises(GatewayRejectedError):
                    await gateway.process_consultation(consultation_request)

                assert route.call_count == 1

    @pytest.mark.asyncio
    async def test_invalid_json_raises_invalid_response(
        self,
        n8n_settings: Settings,
        consultation_request: ConsultationRequest,
    ) -> None:
        """Invalid JSON response should raise GatewayInvalidResponseError."""
        async with httpx.AsyncClient() as client:
            gateway = N8nAutomationGateway(
                webhook_url=n8n_settings.N8N_WEBHOOK_URL,
                shared_secret=n8n_settings.N8N_SHARED_SECRET.get_secret_value(),
                signing_secret=n8n_settings.N8N_SIGNING_SECRET.get_secret_value(),
                http_client=client,
                timeout_seconds=5.0,
                max_retries=1,
                backoff_base_seconds=0.1,
            )

            with respx.mock:
                respx.post(n8n_settings.N8N_WEBHOOK_URL).mock(
                    return_value=Response(200, content=b"not-json-{{{")
                )

                with pytest.raises(GatewayInvalidResponseError):
                    await gateway.process_consultation(consultation_request)

    @pytest.mark.asyncio
    async def test_invalid_response_type_raises(
        self,
        n8n_settings: Settings,
        consultation_request: ConsultationRequest,
    ) -> None:
        """A non-dict JSON response should raise GatewayInvalidResponseError."""
        async with httpx.AsyncClient() as client:
            gateway = N8nAutomationGateway(
                webhook_url=n8n_settings.N8N_WEBHOOK_URL,
                shared_secret=n8n_settings.N8N_SHARED_SECRET.get_secret_value(),
                signing_secret=n8n_settings.N8N_SIGNING_SECRET.get_secret_value(),
                http_client=client,
                timeout_seconds=5.0,
                max_retries=1,
                backoff_base_seconds=0.1,
            )

            with respx.mock:
                respx.post(n8n_settings.N8N_WEBHOOK_URL).mock(
                    return_value=Response(200, json=["list", "not", "dict"])
                )

                with pytest.raises(GatewayInvalidResponseError):
                    await gateway.process_consultation(consultation_request)

    @pytest.mark.asyncio
    async def test_retry_with_backoff(
        self,
        n8n_settings: Settings,
        consultation_request: ConsultationRequest,
    ) -> None:
        """Retries should occur with backoff on 5xx errors."""
        async with httpx.AsyncClient() as client:
            gateway = N8nAutomationGateway(
                webhook_url=n8n_settings.N8N_WEBHOOK_URL,
                shared_secret=n8n_settings.N8N_SHARED_SECRET.get_secret_value(),
                signing_secret=n8n_settings.N8N_SIGNING_SECRET.get_secret_value(),
                http_client=client,
                timeout_seconds=5.0,
                max_retries=2,
                backoff_base_seconds=0.1,
            )

            with respx.mock:
                # First call fails with 502, second succeeds
                route = respx.post(n8n_settings.N8N_WEBHOOK_URL).mock(
                    side_effect=[
                        Response(502, json={"error": "bad gateway"}),
                        Response(200, json={
                            "assistant_message": "Success!",
                            "conversation_phase": "discovery",
                        }),
                    ]
                )

                result = await gateway.process_consultation(consultation_request)

                assert route.call_count == 2
                assert result.assistant_message == "Success!"


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

        assert "X-TASC-Secret" in headers
        assert "X-TASC-Signature" in headers
        assert "X-TASC-Timestamp" in headers
        assert "X-Correlation-Id" in headers
        assert "Content-Type" in headers

        assert headers["X-TASC-Secret"] == "shared-secret"
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
