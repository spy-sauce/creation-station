# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Structured logging configuration with PII redaction.

Rules from HYPHA-OBSERVABILITY.md:
  - JSON renderer in prod, ConsoleRenderer in dev
  - PII (email, phone, resume_text, personal_context, linkedin_url, github_url)
    redacted from INFO logs
  - Full prompt/response only at DEBUG level
  - Every agent module uses structlog.get_logger(__name__)
  - No print() statements anywhere in backend/

PII categories from NUTRIENTS.md §H.4:
  - email — candidate email, contact email, user email
  - phone — any phone numbers
  - legal_name — full legal name if distinct from display name
  - resume_text — full resume content
  - personal_context — candidate personal context field
  - linkedin_url — LinkedIn profile URL
  - github_url — GitHub profile URL
  - address — physical addresses
  - compensation — salary/compensation details
"""

import logging
import re
from typing import Any

import structlog
from structlog.processors import CallsiteParameter

from backend.config import settings


# ─── PII Field Names ─────────────────────────────────────────────────────────

PII_FIELDS = frozenset({
    # From NUTRIENTS.md §H.4
    "email",
    "phone",
    "legal_name",
    "resume_text",
    "personal_context",
    "linkedin_url",
    "github_url",
    "address",
    "compensation",
    # Additional sensitive fields
    "candidate_email",
    "contact_email",
    "user_email",
    "resume",
    "resume_content",
    "full_text",
    "tailored_text",
    "original_text",
    "password",
    "token",
    "secret",
    "api_key",
    "anthropic_api_key",
    "jwt_secret",
    "hunter_api_key",
})

# Regex patterns for detecting PII in unstructured text
PII_PATTERNS = {
    "email": re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
    "phone": re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
}

REDACTED = "[REDACTED]"


# ─── PII Redactor ────────────────────────────────────────────────────────────


class PIIRedactor:
    """
    Redacts PII from log event dictionaries.

    Used as a structlog processor to ensure PII never reaches INFO logs.
    At DEBUG level, PII is still redacted unless explicitly disabled.
    """

    def __init__(self, redact_at_debug: bool = True):
        """
        Initialize the PII redactor.

        Args:
            redact_at_debug: If True, redact PII even at DEBUG level.
                            Set to False only for local development.
        """
        self._redact_at_debug = redact_at_debug

    def __call__(
        self,
        logger: logging.Logger,
        method_name: str,
        event_dict: dict[str, Any],
    ) -> dict[str, Any]:
        """Process a log event, redacting PII fields."""
        # Get the log level
        level = event_dict.get("level", "info").lower()

        # Skip redaction at DEBUG level if configured
        if level == "debug" and not self._redact_at_debug:
            return event_dict

        # Redact known PII fields
        for key in list(event_dict.keys()):
            if key.lower() in PII_FIELDS:
                event_dict[key] = REDACTED
            elif isinstance(event_dict[key], str):
                # Check for PII patterns in string values
                event_dict[key] = self._redact_patterns(event_dict[key])
            elif isinstance(event_dict[key], dict):
                # Recursively redact nested dicts
                event_dict[key] = self._redact_dict(event_dict[key])

        return event_dict

    def _redact_patterns(self, text: str) -> str:
        """Redact PII patterns from a string, preserving structure."""
        # Only redact if the text is suspiciously long (could be a resume)
        # or explicitly contains PII patterns
        result = text
        for pattern_name, pattern in PII_PATTERNS.items():
            if pattern.search(result):
                result = pattern.sub(f"[{pattern_name.upper()}_REDACTED]", result)
        return result

    def _redact_dict(self, d: dict[str, Any]) -> dict[str, Any]:
        """Recursively redact PII from a dictionary."""
        result = {}
        for key, value in d.items():
            if key.lower() in PII_FIELDS:
                result[key] = REDACTED
            elif isinstance(value, str):
                result[key] = self._redact_patterns(value)
            elif isinstance(value, dict):
                result[key] = self._redact_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    self._redact_dict(item) if isinstance(item, dict)
                    else self._redact_patterns(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                result[key] = value
        return result


def redact_pii(data: dict[str, Any]) -> dict[str, Any]:
    """
    Standalone function to redact PII from a dictionary.

    Useful for manually redacting data before logging at non-standard levels.

    Args:
        data: Dictionary potentially containing PII

    Returns:
        Dictionary with PII fields redacted
    """
    redactor = PIIRedactor()
    return redactor._redact_dict(data)


# ─── Logging Configuration ───────────────────────────────────────────────────


def configure_logging() -> None:
    """
    Configure structlog for the application.

    In production (debug=False):
      - JSON renderer for structured log aggregation
      - INFO level minimum
      - PII always redacted

    In development (debug=True):
      - Pretty console renderer with colors
      - DEBUG level minimum
      - PII redacted at INFO+ only (DEBUG can see full data for troubleshooting)
    """
    log_level = logging.DEBUG if settings.debug else logging.INFO

    # Build processor chain
    processors: list[Any] = [
        # Add contextvars (bound context from logger.bind())
        structlog.contextvars.merge_contextvars,
        # Add log level
        structlog.processors.add_log_level,
        # Add timestamp
        structlog.processors.TimeStamper(fmt="iso"),
        # Add callsite info (module, function, line) — useful for debugging
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                CallsiteParameter.MODULE,
                CallsiteParameter.FUNC_NAME,
                CallsiteParameter.LINENO,
            ]
        ),
        # PII redaction — MUST come before rendering
        PIIRedactor(redact_at_debug=not settings.debug),
    ]

    # Add renderer based on environment
    if settings.debug:
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """
    Get a structlog logger instance.

    Usage:
        logger = get_logger(__name__)
        logger.info("event.name", key="value")

    Args:
        name: Logger name, typically __name__

    Returns:
        Bound structlog logger
    """
    return structlog.get_logger(name)
