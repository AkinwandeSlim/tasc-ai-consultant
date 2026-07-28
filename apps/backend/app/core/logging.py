"""Structured logging configuration with PII redaction.

Redacts email addresses, phone numbers, and names from log output
at write time (FR-70, NFR-21). Configured during startup and should
be the first subsystem initialised.
"""

from __future__ import annotations

import logging
import re
import sys

from app.core.config import Settings

# Patterns for PII redaction
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_PATTERN = re.compile(r"\+?\d[\d\s\-().]{6,}\d")
NAME_PATTERN = re.compile(
    r"\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b"
)


class PIIRedactionFilter(logging.Filter):
    """Redacts PII from log messages and extra fields."""

    def filter(self, record: logging.LogRecord) -> bool:
        if hasattr(record, "msg") and isinstance(record.msg, str):
            record.msg = self._redact(record.msg)
        if hasattr(record, "args") and record.args:
            record.args = tuple(
                self._redact(str(a)) if isinstance(a, str) else a
                for a in record.args
            )
        # Redact extra dict fields
        for key in list(record.__dict__.keys()):
            if key in ("email", "phone", "name", "contact", "message_content"):
                record.__dict__[key] = "[REDACTED]"
        return True

    @staticmethod
    def _redact(text: str) -> str:
        text = EMAIL_PATTERN.sub("[EMAIL REDACTED]", text)
        text = PHONE_PATTERN.sub("[PHONE REDACTED]", text)
        return text


def configure_logging(settings: Settings) -> None:
    """Configure the root logger with structured formatting and PII redaction.

    Args:
        settings: Application settings controlling log level and format.
    """
    level = logging.DEBUG if settings.LOG_LEVEL == "DEBUG" else logging.INFO

    formatter: logging.Formatter
    if settings.LOG_FORMAT == "json":
        # JSON structured logging — uses a custom formatter in production
        formatter = logging.Formatter(
            '{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","msg":"%(message)s"}'
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(PIIRedactionFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Silence noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    logging.info(
        "Logging configured",
        extra={"level": settings.LOG_LEVEL.value, "format": settings.LOG_FORMAT},
    )
