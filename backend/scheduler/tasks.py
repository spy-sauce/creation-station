# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""Celery task definitions for daily discovery runs.

This module defines the `daily_discovery_task` that wraps the async
DiscoveryOrchestrator.run() with asyncio.run() for Celery's sync workers.

Retry policy:
    - 3 retries with exponential backoff: 60s, 300s, 900s
    - On terminal failure: write traceback to crawl_runs.error_log
    - Publish DAILY_TASK_DEAD event to agent.status.discovery

Idempotency:
    - Task ID format: discovery-{candidate_id}-{YYYY-MM-DD}
    - Prevents duplicate runs if worker re-fires on the same day

Contract: HYPHA-SCHEDULER.md
"""

from __future__ import annotations

import asyncio
import traceback
from datetime import date, datetime, timezone
from uuid import UUID

import redis.asyncio as aioredis
import structlog
from celery import Task
from celery.exceptions import MaxRetriesExceededError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from backend.config import settings
from backend.scheduler.celery_app import celery_app
from backend.observability.events import PubSubChannel, publish_event, BaseEvent


logger = structlog.get_logger(__name__)

# Retry countdown in seconds: 60s, 300s (5min), 900s (15min)
RETRY_COUNTDOWNS = [60, 300, 900]


class DailyTaskDeadEvent(BaseEvent):
    """Event published when a daily discovery task exhausts all retries.

    Published to: agent.status.discovery
    """

    event: str = "DAILY_TASK_DEAD"
    candidate_id: str
    task_id: str
    error: str
    retries_exhausted: int


def _compute_task_id(candidate_id: str | UUID) -> str:
    """Compute idempotent task ID for a candidate on today's date (UTC).

    Format: discovery-{candidate_id}-{YYYY-MM-DD}

    Args:
        candidate_id: The candidate's UUID

    Returns:
        Idempotent task ID string
    """
    run_date = date.today().isoformat()
    return f"discovery-{candidate_id}-{run_date}"


async def _run_discovery(candidate_id: UUID) -> None:
    """Run the async discovery orchestrator with fresh connections.

    Creates a fresh DB session and Redis client for this invocation,
    ensuring no connection pooling issues across Celery tasks.

    Args:
        candidate_id: UUID of the candidate to run discovery for

    Raises:
        Exception: Any error from the orchestrator is propagated
    """
    # Import here to avoid circular imports at module load time
    from backend.agents.discovery.orchestrator import DiscoveryOrchestrator

    # Create fresh async engine for this task (no shared pool across workers)
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=1,
        max_overflow=0,
    )
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Create fresh Redis client
    redis_client = aioredis.from_url(
        settings.redis_url,
        decode_responses=True,
    )

    try:
        async with session_factory() as db:
            orchestrator = DiscoveryOrchestrator(db, redis_client)
            await orchestrator.run(candidate_id, dry_run=False)
    finally:
        await redis_client.aclose()
        await engine.dispose()


async def _mark_crawl_run_failed(candidate_id: UUID, error_log: str) -> None:
    """Mark the most recent RUNNING crawl run as FAILED with error log.

    Args:
        candidate_id: UUID of the candidate
        error_log: Traceback or error message to record
    """
    from backend.models.discovery import CrawlRun

    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=1,
        max_overflow=0,
    )
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with session_factory() as db:
            # Find the most recent RUNNING crawl run for this candidate
            result = await db.execute(
                select(CrawlRun)
                .where(CrawlRun.candidate_id == candidate_id)
                .where(CrawlRun.status == "RUNNING")
                .order_by(CrawlRun.started_at.desc())
                .limit(1)
            )
            crawl_run = result.scalar_one_or_none()

            if crawl_run:
                crawl_run.status = "FAILED"
                crawl_run.completed_at = datetime.now(timezone.utc)
                crawl_run.error_log = error_log
                await db.commit()
                logger.info(
                    "task.crawl_run_marked_failed",
                    crawl_run_id=str(crawl_run.id),
                    candidate_id=str(candidate_id),
                )
            else:
                logger.warning(
                    "task.no_running_crawl_run",
                    candidate_id=str(candidate_id),
                )
    finally:
        await engine.dispose()


async def _publish_dead_event(
    candidate_id: UUID, task_id: str, error: str, retries: int
) -> None:
    """Publish DAILY_TASK_DEAD event to agent.status.discovery.

    Args:
        candidate_id: UUID of the candidate
        task_id: The Celery task ID
        error: Error message or traceback
        retries: Number of retries exhausted
    """
    redis_client = aioredis.from_url(
        settings.redis_url,
        decode_responses=True,
    )

    try:
        event = DailyTaskDeadEvent(
            candidate_id=str(candidate_id),
            task_id=task_id,
            error=error,
            retries_exhausted=retries,
        )
        await publish_event(redis_client, PubSubChannel.DISCOVERY, event)
        logger.info(
            "task.dead_event_published",
            candidate_id=str(candidate_id),
            task_id=task_id,
        )
    finally:
        await redis_client.aclose()


@celery_app.task(
    bind=True,
    name="backend.scheduler.tasks.daily_discovery_task",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=False,  # We implement custom backoff via countdown
    acks_late=True,
    reject_on_worker_lost=True,
    track_started=True,
)
def daily_discovery_task(self: Task, candidate_id: str) -> dict:
    """Run daily job discovery for a single candidate.

    This task wraps the async DiscoveryOrchestrator.run() with asyncio.run()
    since Celery workers are synchronous by design. Each invocation creates
    a fresh event loop, DB session, and Redis client.

    Retry policy:
        - 3 retries with exponential backoff: 60s, 300s, 900s
        - On MaxRetriesExceededError: write to crawl_runs.error_log,
          publish DAILY_TASK_DEAD, then re-raise

    Args:
        candidate_id: UUID string of the candidate

    Returns:
        dict with status and candidate_id on success

    Raises:
        MaxRetriesExceededError: After 3 failed attempts
    """
    candidate_uuid = UUID(candidate_id)
    task_id = _compute_task_id(candidate_id)
    attempt = self.request.retries + 1

    log = logger.bind(
        candidate_id=candidate_id,
        task_id=task_id,
        attempt=attempt,
        max_retries=self.max_retries,
    )

    log.info("task.started")

    try:
        # Run the async orchestrator in a fresh event loop
        asyncio.run(_run_discovery(candidate_uuid))

        log.info("task.completed")
        return {
            "status": "completed",
            "candidate_id": candidate_id,
            "task_id": task_id,
        }

    except Exception as exc:
        error_msg = str(exc)
        tb = traceback.format_exc()

        log.error(
            "task.failed",
            error=error_msg,
            traceback=tb,
        )

        # Check if we've exhausted retries
        if self.request.retries >= self.max_retries:
            log.error(
                "task.max_retries_exceeded",
                retries_exhausted=self.max_retries,
            )

            # Write to crawl_runs.error_log and publish DAILY_TASK_DEAD
            asyncio.run(_mark_crawl_run_failed(candidate_uuid, tb))
            asyncio.run(
                _publish_dead_event(
                    candidate_uuid,
                    task_id,
                    error_msg,
                    self.max_retries,
                )
            )

            # Re-raise to mark task as failed
            raise MaxRetriesExceededError(
                f"Task {task_id} failed after {self.max_retries} retries: {error_msg}"
            ) from exc

        # Calculate countdown for next retry (exponential backoff)
        retry_index = min(self.request.retries, len(RETRY_COUNTDOWNS) - 1)
        countdown = RETRY_COUNTDOWNS[retry_index]

        log.info(
            "task.retrying",
            countdown=countdown,
            next_attempt=attempt + 1,
        )

        # Schedule retry with backoff
        raise self.retry(exc=exc, countdown=countdown)


def trigger_daily_discovery(candidate_id: str | UUID) -> str:
    """Trigger a daily discovery task for a candidate.

    This is a convenience function for programmatic triggering,
    e.g., from the API endpoint or Celery beat scheduler.

    Args:
        candidate_id: UUID or string UUID of the candidate

    Returns:
        The Celery task ID (idempotent, based on candidate + date)
    """
    candidate_str = str(candidate_id)
    task_id = _compute_task_id(candidate_str)

    daily_discovery_task.apply_async(
        args=[candidate_str],
        task_id=task_id,
    )

    logger.info(
        "task.triggered",
        candidate_id=candidate_str,
        task_id=task_id,
    )

    return task_id
