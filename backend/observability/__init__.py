# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Observability module — cross-cutting logging, PII redaction, and pub/sub taxonomy.

This module owns:
  - structlog configuration (JSON prod, pretty dev)
  - PII redaction policy (email, phone, resume_text, personal_context, etc.)
  - Redis pub/sub channel taxonomy
  - CRM event type constants
  - Health endpoint contract types

See HYPHA-OBSERVABILITY.md for the frozen contract.
"""

from backend.observability.logging import (
    configure_logging,
    get_logger,
    redact_pii,
    PIIRedactor,
)
from backend.observability.events import (
    CRMEventType,
    PubSubChannel,
    AgentStatusEvent,
    PipelineStatusEvent,
    DigestReadyEvent,
    SubAgentStatusEvent,
    publish_event,
)
from backend.observability.health import HealthResponse

__all__ = [
    # Logging
    "configure_logging",
    "get_logger",
    "redact_pii",
    "PIIRedactor",
    # Events
    "CRMEventType",
    "PubSubChannel",
    "AgentStatusEvent",
    "PipelineStatusEvent",
    "DigestReadyEvent",
    "SubAgentStatusEvent",
    "publish_event",
    # Health
    "HealthResponse",
]
