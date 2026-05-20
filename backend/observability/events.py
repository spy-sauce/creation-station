# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Redis pub/sub event taxonomy and CRM event types.

Channel taxonomy from HYPHA-OBSERVABILITY.md:
  - agent.status.discovery    — Discovery Engine events (crawl, scoring, digest)
  - agent.status.application  — Application Engine events (pipeline status)
  - agent.status.subagent     — Sub-agent execution events (tool_use loop)

Event payload rules:
  - Every payload is JSON with an `event` field (SCREAMING_SNAKE_CASE)
  - Payloads include pipeline_id, candidate_id, timestamps
  - No PII in event payloads — use IDs for reference

CRM event types from crm.py docstring + HYPHA-OBSERVABILITY.md:
  - APPLICATION_STARTED
  - JD_PARSED
  - RESUME_TAILORED
  - COMPANY_RESEARCHED
  - CONTACT_FOUND
  - EMAIL_DRAFTED
  - APPROVED_FOR_SUBMISSION
  - SUBMITTED
  - EMAIL_SENT
  - EMAIL_OPENED
  - RESPONDED
  - INTERVIEW_SCHEDULED
  - OFFER_RECEIVED
  - REJECTED
  - PLACED
  - PIPELINE_FAILED
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID

import redis.asyncio as aioredis
from pydantic import BaseModel, Field

import structlog

logger = structlog.get_logger(__name__)


# ─── Pub/Sub Channels ────────────────────────────────────────────────────────


class PubSubChannel(str, Enum):
    """
    Canonical Redis pub/sub channels.

    These are the ONLY allowed channels for agent status events.
    Any new channel must be added here and documented in HYPHA-OBSERVABILITY.md.
    """

    # Discovery Engine events
    DISCOVERY = "agent.status.discovery"

    # Application Engine events (pipeline level)
    APPLICATION = "agent.status.application"

    # Sub-agent execution events (Claude tool_use loop)
    SUBAGENT = "agent.status.subagent"


# ─── CRM Event Types ─────────────────────────────────────────────────────────


class CRMEventType(str, Enum):
    """
    Canonical CRM event types for the application pipeline.

    These events form the auditable timeline for each application.
    New event types must be added here — no ad-hoc strings in code.
    """

    # Pipeline lifecycle
    APPLICATION_STARTED = "APPLICATION_STARTED"
    PIPELINE_FAILED = "PIPELINE_FAILED"

    # Processing stages
    JD_PARSED = "JD_PARSED"
    RESUME_TAILORED = "RESUME_TAILORED"
    COMPANY_RESEARCHED = "COMPANY_RESEARCHED"
    CONTACT_FOUND = "CONTACT_FOUND"
    EMAIL_DRAFTED = "EMAIL_DRAFTED"

    # Review + submission
    APPROVED_FOR_SUBMISSION = "APPROVED_FOR_SUBMISSION"
    REJECTED = "REJECTED"
    SUBMITTED = "SUBMITTED"
    EMAIL_SENT = "EMAIL_SENT"

    # Tracking (post-submission)
    EMAIL_OPENED = "EMAIL_OPENED"
    RESPONDED = "RESPONDED"
    INTERVIEW_SCHEDULED = "INTERVIEW_SCHEDULED"
    OFFER_RECEIVED = "OFFER_RECEIVED"
    PLACED = "PLACED"


# ─── Event Payload Schemas ───────────────────────────────────────────────────


class BaseEvent(BaseModel):
    """Base schema for all pub/sub events."""

    event: str = Field(..., description="Event type in SCREAMING_SNAKE_CASE")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp",
    )

    class Config:
        extra = "allow"


class AgentStatusEvent(BaseEvent):
    """
    Application pipeline status event.

    Published to: agent.status.application
    """

    event: str = "APPLICATION_STATUS"
    pipeline_id: str
    candidate_id: str
    status: str


class PipelineStatusEvent(BaseEvent):
    """
    Pipeline-level status event (used by PipelineDispatcher).

    Published to: agent.status.application
    """

    event: str = "PIPELINE_STATUS"
    pipeline_id: str
    status: str
    details: dict[str, Any] = Field(default_factory=dict)


class SubAgentStatusEvent(BaseEvent):
    """
    Sub-agent execution status event.

    Published to: agent.status.subagent
    """

    event: str = "SUBAGENT_STATUS"
    execution_id: str
    agent_name: str
    pipeline_id: str
    status: str
    attempt: int = 1
    duration_ms: Optional[int] = None


class DigestReadyEvent(BaseEvent):
    """
    Discovery digest completion event.

    Published to: agent.status.discovery
    """

    event: str = "DIGEST_READY"
    digest_id: str
    candidate_id: str
    run_date: str
    total_discovered: int
    total_scored: int
    top_picks_count: int
    hot_picks_count: int


class CrawlStatusEvent(BaseEvent):
    """
    Crawl run status event.

    Published to: agent.status.discovery
    """

    event: str = "CRAWL_STATUS"
    crawl_run_id: str
    candidate_id: str
    status: str  # QUEUED, RUNNING, COMPLETED, FAILED
    jobs_discovered: Optional[int] = None
    jobs_scored: Optional[int] = None
    error: Optional[str] = None


# ─── Event Publisher ─────────────────────────────────────────────────────────


async def publish_event(
    redis_client: aioredis.Redis,
    channel: PubSubChannel | str,
    event: BaseEvent | dict[str, Any],
) -> int:
    """
    Publish an event to a Redis pub/sub channel.

    Args:
        redis_client: Async Redis client
        channel: Target pub/sub channel (use PubSubChannel enum)
        event: Event payload (Pydantic model or dict)

    Returns:
        Number of subscribers that received the message
    """
    # Normalize channel to string
    channel_str = channel.value if isinstance(channel, PubSubChannel) else channel

    # Serialize event
    if isinstance(event, BaseModel):
        payload = event.model_dump_json()
    else:
        payload = json.dumps(event, default=str)

    # Publish
    subscriber_count = await redis_client.publish(channel_str, payload)

    logger.debug(
        "pubsub.event_published",
        channel=channel_str,
        event_type=event.event if isinstance(event, BaseEvent) else event.get("event"),
        subscribers=subscriber_count,
    )

    return subscriber_count


# ─── Convenience Publishers ──────────────────────────────────────────────────


async def publish_application_status(
    redis_client: aioredis.Redis,
    pipeline_id: UUID,
    candidate_id: UUID,
    status: str,
) -> int:
    """Publish an application pipeline status update."""
    event = AgentStatusEvent(
        pipeline_id=str(pipeline_id),
        candidate_id=str(candidate_id),
        status=status,
    )
    return await publish_event(redis_client, PubSubChannel.APPLICATION, event)


async def publish_subagent_status(
    redis_client: aioredis.Redis,
    execution_id: UUID,
    agent_name: str,
    pipeline_id: UUID,
    status: str,
    attempt: int = 1,
    duration_ms: Optional[int] = None,
) -> int:
    """Publish a sub-agent execution status update."""
    event = SubAgentStatusEvent(
        execution_id=str(execution_id),
        agent_name=agent_name,
        pipeline_id=str(pipeline_id),
        status=status,
        attempt=attempt,
        duration_ms=duration_ms,
    )
    return await publish_event(redis_client, PubSubChannel.SUBAGENT, event)


async def publish_digest_ready(
    redis_client: aioredis.Redis,
    digest_id: UUID,
    candidate_id: UUID,
    run_date: str,
    total_discovered: int,
    total_scored: int,
    top_picks_count: int,
    hot_picks_count: int,
) -> int:
    """Publish a digest completion event."""
    event = DigestReadyEvent(
        digest_id=str(digest_id),
        candidate_id=str(candidate_id),
        run_date=run_date,
        total_discovered=total_discovered,
        total_scored=total_scored,
        top_picks_count=top_picks_count,
        hot_picks_count=hot_picks_count,
    )
    return await publish_event(redis_client, PubSubChannel.DISCOVERY, event)


async def publish_crawl_status(
    redis_client: aioredis.Redis,
    crawl_run_id: UUID,
    candidate_id: UUID,
    status: str,
    jobs_discovered: Optional[int] = None,
    jobs_scored: Optional[int] = None,
    error: Optional[str] = None,
) -> int:
    """Publish a crawl run status update."""
    event = CrawlStatusEvent(
        crawl_run_id=str(crawl_run_id),
        candidate_id=str(candidate_id),
        status=status,
        jobs_discovered=jobs_discovered,
        jobs_scored=jobs_scored,
        error=error,
    )
    return await publish_event(redis_client, PubSubChannel.DISCOVERY, event)
