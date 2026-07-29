"""Application configuration via pydantic-settings.

Single source of truth for all environment variables. Loaded once at import,
validated eagerly so a missing required variable kills the process before
the ASGI app starts (BP-06).
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(str, Enum):
    LOCAL = "local"
    PREVIEW = "preview"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class LLMProvider(str, Enum):
    OPENAI = "openai"


class StructuredMode(str, Enum):
    SCHEMA = "schema"
    JSON_OBJECT = "json_object"


class ChromaMode(str, Enum):
    EMBEDDED = "embedded"
    HTTP = "http"


class SessionStore(str, Enum):
    MEMORY = "memory"
    FILE = "file"
    REDIS = "redis"


class SimulationMode(str, Enum):
    ENABLED = "true"
    DISABLED = "false"


class Settings(BaseSettings):
    """Root settings model composed of nested groups.

    Validated at construction — a missing required field fails fast.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        frozen=True,
    )

    # --- Application ---
    APP_ENV: AppEnv = AppEnv.LOCAL
    APP_NAME: str = "tasc-backend"
    APP_VERSION: str = "1.0.0"
    LOG_LEVEL: LogLevel = LogLevel.INFO
    LOG_FORMAT: str = "console"
    API_PREFIX: str = "/api"
    DOCS_ENABLED: bool = True
    SHUTDOWN_GRACE_SECONDS: int = 20

    # --- Model Provider ---
    LLM_PROVIDER: LLMProvider = LLMProvider.OPENAI
    OPENAI_API_KEY: SecretStr = Field(default="", validate_default=False)
    OPENAI_BASE_URL: str | None = None
    LLM_CHAT_MODEL: str = "gpt-4.1-mini"
    LLM_EMBEDDING_MODEL: str = "text-embedding-3-small"
    LLM_TEMPERATURE_CONVERSATION: float = 0.3
    LLM_TEMPERATURE_STRUCTURED: float = 0.0
    LLM_MAX_OUTPUT_TOKENS: int = 700
    LLM_TIMEOUT_SECONDS: float = 30.0
    LLM_CONNECT_TIMEOUT_SECONDS: float = 5.0
    LLM_MAX_RETRIES: int = 1
    LLM_STRUCTURED_MODE: StructuredMode = StructuredMode.SCHEMA

    # --- AI Settings ---
    AI_PROMPT_MANIFEST_PATH: str = "app/resources/prompts/manifest.yaml"
    AI_PROMPT_BASE_PATH: str = "app/resources/prompts"
    AI_KNOWLEDGE_MANIFEST_PATH: str = "knowledge/manifest.yaml"
    AI_RULESET_VERSION: str = ""
    AI_DEFAULT_TEMPERATURE: float = 0.3

    # --- Retrieval ---
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    CHROMA_COLLECTION: str = "trizen_knowledge"
    CHROMA_MODE: ChromaMode = ChromaMode.EMBEDDED
    CHROMA_HTTP_URL: str | None = None
    RAG_TOP_K: int = 5
    RAG_SIMILARITY_FLOOR: float = 0.35
    RAG_CHUNK_TARGET_TOKENS: int = 650
    RAG_CHUNK_OVERLAP_RATIO: float = 0.15
    RAG_MAX_CONTEXT_CHUNKS: int = 5
    RAG_ENABLE_METADATA_FILTER: bool = True

    # --- Conversation & Session ---
    SESSION_TTL_MINUTES: int = 60
    SESSION_ABANDON_MINUTES: int = 20
    SESSION_STORE: SessionStore = SessionStore.FILE
    SESSION_STORE_PATH: str = "./data/sessions"
    REDIS_URL: str | None = None
    MESSAGE_MAX_CHARS: int = 2000
    HISTORY_FULL_TURNS: int = 8
    HISTORY_TOKEN_BUDGET: int = 3000
    SESSION_TOKEN_CEILING: int = 60000

    # --- Scoring ---
    SCORING_WEIGHTS_PATH: str = "app/resources/scoring/weights.yaml"
    SCORING_OVERRIDES_PATH: str = "app/resources/scoring/overrides.yaml"
    BAND_THRESHOLD_WARM: int = 35
    BAND_THRESHOLD_QUALIFIED: int = 60
    BAND_THRESHOLD_HOT: int = 80
    CATALOGUE_PATH: str = "app/resources/catalogue/services.yaml"
    PAIN_MAPPING_PATH: str = "app/resources/catalogue/pain_mapping.yaml"
    RECOMMENDATION_CONFIDENCE_FLOOR: float = 0.6
    RECOMMENDATION_MAX: int = 3

    # --- Automation ---
    N8N_WEBHOOK_URL: str = ""
    N8N_SHARED_SECRET: SecretStr = Field(default="", validate_default=False)
    N8N_SIGNING_SECRET: SecretStr = Field(default="", validate_default=False)
    N8N_TIMEOUT_SECONDS: float = 15.0
    N8N_MAX_ATTEMPTS: int = 3
    N8N_BACKOFF_BASE_SECONDS: float = 2.0
    N8N_ENABLED: bool = True
    DEADLETTER_PATH: str = "./data/payloads/deadletter"

    # --- Security ---
    CORS_ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]
    RATE_LIMIT_SESSION_PER_MINUTE: int = 20
    RATE_LIMIT_IP_PER_MINUTE: int = 60
    RATE_LIMIT_SESSION_CREATE_PER_HOUR: int = 10
    ADMIN_API_KEY: SecretStr = Field(default="", validate_default=False)
    ADMIN_ROUTES_ENABLED: bool = False
    TRUSTED_HOSTS: list[str] = ["*"]

    # --- Simulation ---
    SIMULATION_MODE: bool = False
    SIMULATION_SCENARIO_ID: str = ""
    SIMULATION_DETERMINISTIC: bool = True
    SIMULATION_LATENCY: bool = False
    SIMULATION_LATENCY_MIN_MS: int = 200
    SIMULATION_LATENCY_MAX_MS: int = 1500
    SIMULATION_ERRORS: bool = False
    SIMULATION_ERROR_RATE: float = 0.0

    # --- Observability ---
    SENTRY_DSN: str | None = None
    TELEMETRY_ENABLED: bool = True
    COST_PER_1K_INPUT_TOKENS: float = 0.00015
    COST_PER_1K_OUTPUT_TOKENS: float = 0.00060
    LOG_SAMPLE_RATE: float = 1.0

    # --- Validation ---

    @field_validator("CORS_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("TRUSTED_HOSTS", mode="before")
    @classmethod
    def parse_trusted_hosts(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [host.strip() for host in v.split(",") if host.strip()]
        return v

    @model_validator(mode="after")
    def validate_dependencies(self) -> Settings:
        if self.CHROMA_MODE == ChromaMode.HTTP and not self.CHROMA_HTTP_URL:
            raise ValueError("CHROMA_HTTP_URL is required when CHROMA_MODE is http")
        if self.SESSION_STORE == SessionStore.REDIS and not self.REDIS_URL:
            raise ValueError("REDIS_URL is required when SESSION_STORE is redis")
        if self.ADMIN_ROUTES_ENABLED and not self.ADMIN_API_KEY.get_secret_value():
            raise ValueError("ADMIN_API_KEY is required when ADMIN_ROUTES_ENABLED is true")
        return self


# Module-level singleton — import this to get validated settings
_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the validated settings singleton.

    Initialised on first call. FastAPI dependency callers use Depends(get_settings)
    but importing the function directly is also safe.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
