"""Tests for the LLM consultation engine (Sprint 6.3).

Verifies the deterministic-source-of-truth contract:
  ✓ Deterministic ConsultationOrchestrator is always called first.
  ✓ LLM output replaces ONLY assistant_message and next_question.
  ✓ On any failure (timeout, rate limit, invalid JSON, schema
    mismatch, exception), deterministic result is returned unchanged.
  ✓ start_consultation always uses the deterministic engine.
  ✓ Without a provider, all calls go through deterministic only.
  ✓ DI container wiring is correct.
  ✓ Simplified LlmConsultationOutput has only NL fields.

References: Sprint 6.3 requirement
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import ProviderUnavailableError

# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def deterministic_result():
    """Return a realistic OrchestrationResult-like object."""
    return MagicMock(
        assistant_message="Based on what you've shared, I'd recommend exploring automation for your inventory management.",
        conversation_phase="exploration",
        business_profile={
            "industry": "logistics",
            "company_size": "sme",
            "pain_points": [{"label": "Manual inventory management", "source_turn": 2}],
            "current_tools": ["Excel"],
            "goals": ["Reduce costs"],
        },
        lead_score={"score": 45, "band": "warm", "confidence": 0.72},
        recommendations=[
            {
                "service_code": "INV-001",
                "name": "Inventory Automation",
                "rank": 1,
                "priority": "high",
                "rationale": "Manual inventory is a clear automation target.",
            },
        ],
        completion_percentage=35,
        next_question="What is your monthly order volume?",
        is_complete=False,
        completion_reason="",
        errors=[],
    )


@pytest.fixture
def mock_deterministic(deterministic_result):
    """Return a mock deterministic ConsultationOrchestrator."""
    engine = AsyncMock()
    engine.process_turn = AsyncMock(return_value=deterministic_result)
    engine.start_consultation = AsyncMock(
        return_value={
            "session_id": "det-session-001",
            "phase": "greeting",
            "status": "active",
            "turn_index": 0,
            "messages": [{"role": "assistant", "content": "Hello! I'm Nova."}],
        },
    )
    return engine


@pytest.fixture
def mock_chat_provider():
    """Return a mock ChatProvider that returns valid structured output.

    The output contains ONLY assistant_message and next_question.
    """
    provider = AsyncMock()
    provider.complete_structured = AsyncMock(
        return_value=MagicMock(
            content={
                "assistant_message": "Thanks for sharing that. Could you tell me more about your current inventory volumes?",
                "next_question": "How many units do you move per month?",
            },
        ),
    )
    return provider


@pytest.fixture
def failing_provider():
    """Return a mock ChatProvider that fails on structured calls."""
    provider = AsyncMock()
    provider.complete_structured = AsyncMock(
        side_effect=ProviderUnavailableError("Simulated failure"),
    )
    return provider


@pytest.fixture
def session_state():
    """Return a basic session state dict."""
    return {
        "session_id": "test-session-001",
        "phase": "discovery",
        "status": "active",
        "turn_index": 1,
        "visitor_turn_count": 1,
        "messages": [
            {"role": "assistant", "content": "Hello! I'm Nova."},
            {"role": "user", "content": "We run a logistics company."},
        ],
        "business_profile": {"industry": "logistics"},
    }


# ── Construction Tests ────────────────────────────────────────────────


class TestLlmConsultationEngineConstruction:
    """Verify LlmConsultationEngine constructs correctly."""

    def test_constructs_with_provider(self, mock_chat_provider, mock_deterministic):
        """Engine should construct with a ChatProvider."""
        from app.orchestration.llm.engine import LlmConsultationEngine

        engine = LlmConsultationEngine(
            chat_provider=mock_chat_provider,
            deterministic_engine=mock_deterministic,
        )
        assert engine.is_llm_available is True

    def test_constructs_without_provider(self, mock_deterministic):
        """Engine should construct without a ChatProvider."""
        from app.orchestration.llm.engine import LlmConsultationEngine

        engine = LlmConsultationEngine(
            chat_provider=None,
            deterministic_engine=mock_deterministic,
        )
        assert engine.is_llm_available is False


# ── Process Turn Tests ────────────────────────────────────────────────


class TestProcessTurn:
    """Verify process_turn calls deterministic first, then optionally enhances."""

    @pytest.mark.asyncio
    async def test_deterministic_always_called(
        self,
        mock_chat_provider,
        mock_deterministic,
        session_state,
    ):
        """Deterministic engine should always be called first."""
        from app.orchestration.llm.engine import LlmConsultationEngine

        engine = LlmConsultationEngine(
            chat_provider=mock_chat_provider,
            deterministic_engine=mock_deterministic,
        )
        await engine.process_turn(
            session_state=session_state,
            visitor_message="We need help with inventory.",
        )
        mock_deterministic.process_turn.assert_called_once()

    @pytest.mark.asyncio
    async def test_replaces_assistant_message(
        self,
        mock_chat_provider,
        mock_deterministic,
        deterministic_result,
        session_state,
    ):
        """LLM output should replace assistant_message."""
        from app.orchestration.llm.engine import LlmConsultationEngine

        engine = LlmConsultationEngine(
            chat_provider=mock_chat_provider,
            deterministic_engine=mock_deterministic,
        )
        result = await engine.process_turn(
            session_state=session_state,
            visitor_message="We need help with inventory.",
        )
        assert result.assistant_message == mock_chat_provider.complete_structured.return_value.content["assistant_message"]

    @pytest.mark.asyncio
    async def test_replaces_next_question(
        self,
        mock_chat_provider,
        mock_deterministic,
        deterministic_result,
        session_state,
    ):
        """LLM output should replace next_question."""
        from app.orchestration.llm.engine import LlmConsultationEngine

        engine = LlmConsultationEngine(
            chat_provider=mock_chat_provider,
            deterministic_engine=mock_deterministic,
        )
        result = await engine.process_turn(
            session_state=session_state,
            visitor_message="We need help with inventory.",
        )
        assert result.next_question == mock_chat_provider.complete_structured.return_value.content["next_question"]

    @pytest.mark.asyncio
    async def test_preserves_structured_fields(
        self,
        mock_chat_provider,
        mock_deterministic,
        deterministic_result,
        session_state,
    ):
        """Structured fields from deterministic should be preserved."""
        from app.orchestration.llm.engine import LlmConsultationEngine

        engine = LlmConsultationEngine(
            chat_provider=mock_chat_provider,
            deterministic_engine=mock_deterministic,
        )
        result = await engine.process_turn(
            session_state=session_state,
            visitor_message="We need help with inventory.",
        )

        # Business profile unchanged
        assert result.business_profile["industry"] == "logistics"
        assert result.business_profile["company_size"] == "sme"

        # Lead score unchanged
        assert result.lead_score["score"] == 45
        assert result.lead_score["band"] == "warm"

        # Recommendations unchanged
        assert len(result.recommendations) == 1
        assert result.recommendations[0]["service_code"] == "INV-001"

        # Phase unchanged
        assert result.conversation_phase == "exploration"

        # Completion unchanged
        assert result.completion_percentage == 35
        assert result.is_complete is False

    @pytest.mark.asyncio
    async def test_returns_deterministic_on_provider_failure(
        self,
        failing_provider,
        mock_deterministic,
        deterministic_result,
        session_state,
    ):
        """On provider failure, deterministic result should be returned unchanged."""
        from app.orchestration.llm.engine import LlmConsultationEngine

        engine = LlmConsultationEngine(
            chat_provider=failing_provider,
            deterministic_engine=mock_deterministic,
        )
        result = await engine.process_turn(
            session_state=session_state,
            visitor_message="We need help.",
        )

        assert result.assistant_message == deterministic_result.assistant_message
        assert result.conversation_phase == "exploration"
        assert result.lead_score["score"] == 45

    @pytest.mark.asyncio
    async def test_returns_deterministic_on_timeout(
        self,
        mock_deterministic,
        deterministic_result,
        session_state,
    ):
        """On timeout, deterministic result should be returned unchanged."""
        from app.orchestration.llm.engine import LlmConsultationEngine

        timeout_provider = AsyncMock()
        timeout_provider.complete_structured = AsyncMock(
            side_effect=ProviderUnavailableError("Timeout", code="PROVIDER_TIMEOUT"),
        )

        engine = LlmConsultationEngine(
            chat_provider=timeout_provider,
            deterministic_engine=mock_deterministic,
        )
        result = await engine.process_turn(
            session_state=session_state,
            visitor_message="We need help.",
        )

        assert result.assistant_message == deterministic_result.assistant_message
        assert result.conversation_phase == "exploration"

    @pytest.mark.asyncio
    async def test_returns_deterministic_on_rate_limit(
        self,
        mock_deterministic,
        deterministic_result,
        session_state,
    ):
        """On rate limit, deterministic result should be returned unchanged."""
        from app.orchestration.llm.engine import LlmConsultationEngine

        rate_limited_provider = AsyncMock()
        rate_limited_provider.complete_structured = AsyncMock(
            side_effect=ProviderUnavailableError("Rate limited", code="PROVIDER_RATE_LIMITED"),
        )

        engine = LlmConsultationEngine(
            chat_provider=rate_limited_provider,
            deterministic_engine=mock_deterministic,
        )
        result = await engine.process_turn(
            session_state=session_state,
            visitor_message="We need help.",
        )

        assert result.assistant_message == deterministic_result.assistant_message

    @pytest.mark.asyncio
    async def test_returns_deterministic_on_invalid_json(
        self,
        mock_deterministic,
        deterministic_result,
        session_state,
    ):
        """On invalid JSON, deterministic result should be returned unchanged."""
        from app.orchestration.llm.engine import LlmConsultationEngine

        invalid_provider = AsyncMock()
        invalid_provider.complete_structured = AsyncMock(
            side_effect=ProviderUnavailableError("Invalid JSON", code="PROVIDER_INVALID_JSON"),
        )

        engine = LlmConsultationEngine(
            chat_provider=invalid_provider,
            deterministic_engine=mock_deterministic,
        )
        result = await engine.process_turn(
            session_state=session_state,
            visitor_message="We need help.",
        )

        assert result.assistant_message == deterministic_result.assistant_message

    @pytest.mark.asyncio
    async def test_returns_deterministic_on_schema_mismatch(
        self,
        mock_deterministic,
        deterministic_result,
        session_state,
    ):
        """On schema mismatch, deterministic result should be returned unchanged."""
        from app.orchestration.llm.engine import LlmConsultationEngine

        schema_fail_provider = AsyncMock()
        schema_fail_provider.complete_structured = AsyncMock(
            side_effect=ProviderUnavailableError("Schema mismatch", code="PROVIDER_SCHEMA_MISMATCH"),
        )

        engine = LlmConsultationEngine(
            chat_provider=schema_fail_provider,
            deterministic_engine=mock_deterministic,
        )
        result = await engine.process_turn(
            session_state=session_state,
            visitor_message="We need help.",
        )

        assert result.assistant_message == deterministic_result.assistant_message

    @pytest.mark.asyncio
    async def test_returns_deterministic_on_unexpected_exception(
        self,
        mock_deterministic,
        deterministic_result,
        session_state,
    ):
        """On unexpected exception, deterministic result should be returned unchanged."""
        from app.orchestration.llm.engine import LlmConsultationEngine

        broken_provider = AsyncMock()
        broken_provider.complete_structured = AsyncMock(
            side_effect=RuntimeError("Unexpected crash"),
        )

        engine = LlmConsultationEngine(
            chat_provider=broken_provider,
            deterministic_engine=mock_deterministic,
        )
        result = await engine.process_turn(
            session_state=session_state,
            visitor_message="We need help.",
        )

        assert result.assistant_message == deterministic_result.assistant_message

    @pytest.mark.asyncio
    async def test_without_provider_returns_deterministic(
        self,
        mock_deterministic,
        deterministic_result,
        session_state,
    ):
        """Without a provider, deterministic result should be returned."""
        from app.orchestration.llm.engine import LlmConsultationEngine

        engine = LlmConsultationEngine(
            chat_provider=None,
            deterministic_engine=mock_deterministic,
        )
        result = await engine.process_turn(
            session_state=session_state,
            visitor_message="We need help.",
        )

        assert result.assistant_message == deterministic_result.assistant_message
        mock_deterministic.process_turn.assert_called_once()


# ── Start Consultation Tests ──────────────────────────────────────────


class TestStartConsultation:
    """Verify start_consultation always uses deterministic engine."""

    @pytest.mark.asyncio
    async def test_start_with_provider_uses_deterministic(
        self,
        mock_chat_provider,
        mock_deterministic,
    ):
        """Even with a provider, start should go through deterministic."""
        from app.orchestration.llm.engine import LlmConsultationEngine

        engine = LlmConsultationEngine(
            chat_provider=mock_chat_provider,
            deterministic_engine=mock_deterministic,
        )
        session = await engine.start_consultation()

        assert session["session_id"] == "det-session-001"
        assert session["phase"] == "greeting"
        mock_deterministic.start_consultation.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_without_provider_uses_deterministic(
        self,
        mock_deterministic,
    ):
        """Without a provider, start should go through deterministic."""
        from app.orchestration.llm.engine import LlmConsultationEngine

        engine = LlmConsultationEngine(
            chat_provider=None,
            deterministic_engine=mock_deterministic,
        )
        session = await engine.start_consultation()

        assert session["session_id"] == "det-session-001"
        mock_deterministic.start_consultation.assert_called_once()


# ── Routing / DI Tests ────────────────────────────────────────────────


class TestDependencyInjection:
    """Verify the LLM engine integrates with the DI container."""

    def test_llm_engine_none_when_disabled(self):
        """When LLM_ENABLED=false, container should not create an LLM engine."""
        from app.container import build_container
        from app.core.config import Settings

        settings = Settings(
            APP_ENV="local",
            OPENAI_API_KEY="test-key",
            LLM_ENABLED=False,
        )
        container = build_container(settings)
        assert container.llm_engine is None

    def test_llm_engine_created_when_enabled_and_key_present(self):
        """When LLM_ENABLED=true and API key set, container should create engine."""
        from app.container import build_container
        from app.core.config import Settings

        settings = Settings(
            APP_ENV="local",
            OPENAI_API_KEY="sk-test-key",
            LLM_ENABLED=True,
        )
        container = build_container(settings)
        assert container.llm_engine is not None
        assert container.chat_provider is not None

    def test_llm_engine_none_when_enabled_but_no_key(self):
        """When LLM_ENABLED=true but no API key, engine should be None."""
        from app.container import build_container
        from app.core.config import Settings

        settings = Settings(
            APP_ENV="local",
            OPENAI_API_KEY="",
            LLM_ENABLED=True,
        )
        container = build_container(settings)
        assert container.llm_engine is None
        assert container.chat_provider is None

    def test_mock_gateway_uses_deterministic_by_default(self):
        """With LLM_ENABLED=false, MockAutomationGateway uses deterministic engine."""
        from app.container import build_container
        from app.core.config import Settings
        from app.orchestration.orchestrator import ConsultationOrchestrator

        settings = Settings(
            APP_ENV="local",
            OPENAI_API_KEY="test-key",
            LLM_ENABLED=False,
        )
        container = build_container(settings)
        gateway = container.automation_gateway
        assert gateway is not None
        assert isinstance(gateway._orchestrator, ConsultationOrchestrator)

    def test_mock_gateway_uses_llm_engine_when_enabled(self):
        """With LLM_ENABLED=true, MockAutomationGateway uses LlmConsultationEngine."""
        from app.container import build_container
        from app.core.config import Settings
        from app.orchestration.llm.engine import LlmConsultationEngine

        settings = Settings(
            APP_ENV="local",
            OPENAI_API_KEY="sk-test-key",
            LLM_ENABLED=True,
        )
        container = build_container(settings)
        gateway = container.automation_gateway
        assert gateway is not None
        assert isinstance(gateway._orchestrator, LlmConsultationEngine)


# ── Output Model Tests ────────────────────────────────────────────────


class TestLlmConsultationOutputModel:
    """Verify the simplified output model has only NL fields."""

    def test_has_only_nl_fields(self):
        """LlmConsultationOutput should only contain assistant_message and next_question."""
        from app.orchestration.llm.models import LlmConsultationOutput

        fields = set(LlmConsultationOutput.model_fields.keys())
        assert fields == {"assistant_message", "next_question"}

    def test_assistant_message_required(self):
        """assistant_message should be required."""
        # Empty should fail
        import pytest
        from pydantic import ValidationError

        from app.orchestration.llm.models import LlmConsultationOutput
        with pytest.raises(ValidationError):
            LlmConsultationOutput(assistant_message="")

    def test_next_question_optional(self):
        """next_question should be optional."""
        from app.orchestration.llm.models import LlmConsultationOutput

        model = LlmConsultationOutput(assistant_message="Hello!")
        assert model.next_question is None
        assert model.assistant_message == "Hello!"
