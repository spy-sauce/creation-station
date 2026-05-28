# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Celery Beat schedule extension for synthetics monitoring.

Additively registers synthetics tasks on the Celery beat schedule without
modifying the frozen scheduler-agent entries (daily_discovery_task).

Schedule:
    - synthetics-crawler-hourly: Every hour on the hour (minute=0)
      → Exercises Greenhouse, Lever, Ashby endpoints for health
    - synthetics-scoring-daily: Daily at 03:00 UTC
      → Runs scoring drift detection against synthetic candidates

Contract: NUTRIENTS.md §I.6, HYPHA-SYNTHETICS-CRAWLER.md
Owner: synthetics-crawler-agent.beat-extension
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import structlog
from celery import Celery, Task
from celery.schedules import crontab

if TYPE_CHECKING:
    import redis.asyncio as aioredis

logger = structlog.get_logger(__name__)


def register_synthetics_beat(app: Celery) -> None:
    """Additively register synthetics tasks on the Celery beat schedule.

    Does NOT modify frozen scheduler-agent entries (dispatch-daily-discovery).

    This function is called from backend/main.py lifespan or from the
    Celery app configuration to extend the beat schedule with synthetics
    monitoring tasks.

    Args:
        app: The Celery application instance

    Note:
        Tasks are registered in the 'backend.synthetics.beat_schedule' module
        to keep synthetics isolated from the core scheduler-agent biome.
    """
    # Ensure beat_schedule exists
    if not hasattr(app.conf, "beat_schedule") or app.conf.beat_schedule is None:
        app.conf.beat_schedule = {}

    app.conf.beat_schedule.update({
        "synthetics-crawler-hourly": {
            "task": "backend.synthetics.beat_schedule.crawler_health_task",
            "schedule": crontab(minute=0),  # Every hour on the hour
            "options": {
                "queue": "default",
            },
        },
        "synthetics-scoring-daily": {
            "task": "backend.synthetics.beat_schedule.scoring_suite_task",
            "schedule": crontab(hour=3, minute=0),  # 03:00 UTC
            "options": {
                "queue": "default",
            },
        },
    })

    logger.info(
        "synthetics.beat_registered",
        tasks=["synthetics-crawler-hourly", "synthetics-scoring-daily"],
    )


# ─── Task Definitions ─────────────────────────────────────────────────────────
# Tasks must be defined in this module to match the task names in beat_schedule


async def _run_crawler_health() -> dict:
    """Run the async CrawlerHealthRunner with fresh Redis connection.

    Creates a fresh Redis client for this invocation to ensure no
    connection pooling issues across Celery tasks.

    Returns:
        dict with run results from CrawlerHealthRunner.run_suite()
    """
    import redis.asyncio as aioredis
    from backend.config import settings
    from backend.synthetics.crawler_health import CrawlerHealthRunner

    # Create fresh Redis client for pub/sub events
    redis_client: aioredis.Redis = aioredis.from_url(
        settings.redis_url,
        decode_responses=True,
    )

    try:
        runner = CrawlerHealthRunner(redis_client=redis_client)
        result = await runner.run_suite()
        return result
    finally:
        await redis_client.aclose()


async def _run_scoring_suite() -> dict:
    """Run the async ScoringSyntheticRunner with fresh connections.

    Creates fresh DB session and Redis client for this invocation.

    Returns:
        dict with run results from ScoringSyntheticRunner.run_suite()
    """
    import redis.asyncio as aioredis
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
    from backend.config import settings
    from backend.synthetics.scoring_runner import ScoringSyntheticRunner

    # Create fresh async engine for this task
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
    redis_client: aioredis.Redis = aioredis.from_url(
        settings.redis_url,
        decode_responses=True,
    )

    try:
        async with session_factory() as db:
            runner = ScoringSyntheticRunner(db=db, redis_client=redis_client)
            result = await runner.run_suite()
            return result
    finally:
        await redis_client.aclose()
        await engine.dispose()


# Import celery_app lazily to avoid circular imports at module load time
def _get_celery_app() -> Celery:
    """Get the Celery app instance lazily."""
    from backend.scheduler.celery_app import celery_app
    return celery_app


# Register tasks with the Celery app
# These are defined at module level so Celery can discover them
_celery_app = _get_celery_app()


@_celery_app.task(
    bind=True,
    name="backend.synthetics.beat_schedule.crawler_health_task",
    acks_late=True,
    track_started=True,
    max_retries=1,
    default_retry_delay=60,
)
def crawler_health_task(self: Task) -> dict:
    """Run hourly crawler health check.

    Exercises Greenhouse, Lever, and Ashby endpoints to verify upstream
    health. Tracks consecutive failures via state machine and alerts on
    3-strike threshold.

    This task wraps the async CrawlerHealthRunner.run_suite() with
    asyncio.run() since Celery workers are synchronous by design.

    Returns:
        dict with:
            - run_id: UUID of this run
            - sources: list of source check results
            - state_transitions: list of state transitions
            - report_path: path to the written report
    """
    log = logger.bind(task="crawler_health_task")
    log.info("synthetics.crawler_health_started")

    try:
        result = asyncio.run(_run_crawler_health())

        # Log summary
        alerts_fired = sum(
            1 for t in result.get("state_transitions", [])
            if t.get("alert_fired", False)
        )

        log.info(
            "synthetics.crawler_health_completed",
            run_id=result.get("run_id"),
            sources_checked=len(result.get("sources", [])),
            alerts_fired=alerts_fired,
            report_path=result.get("report_path"),
        )

        return result

    except Exception as exc:
        log.error(
            "synthetics.crawler_health_failed",
            error=str(exc),
        )
        # Re-raise for Celery retry mechanism
        raise


@_celery_app.task(
    bind=True,
    name="backend.synthetics.beat_schedule.scoring_suite_task",
    acks_late=True,
    track_started=True,
    max_retries=1,
    default_retry_delay=300,  # 5 minutes - scoring is more expensive
)
def scoring_suite_task(self: Task) -> dict:
    """Run daily scoring drift detection.

    Iterates synthetic candidates × JDs, computes fingerprints, and
    compares against accepted baselines to detect scoring drift.

    This task wraps the async ScoringSyntheticRunner.run_suite() with
    asyncio.run() since Celery workers are synchronous by design.

    Returns:
        dict with:
            - run_id: UUID of this run
            - candidates: list of candidate results with fingerprints
            - overall_status: drift severity (green/yellow/red)
            - report_path: path to the written report
    """
    log = logger.bind(task="scoring_suite_task")
    log.info("synthetics.scoring_suite_started")

    try:
        result = asyncio.run(_run_scoring_suite())

        log.info(
            "synthetics.scoring_suite_completed",
            run_id=result.get("run_id"),
            candidates_checked=len(result.get("candidates", [])),
            overall_status=result.get("overall_status"),
            report_path=result.get("report_path"),
        )

        return result

    except Exception as exc:
        log.error(
            "synthetics.scoring_suite_failed",
            error=str(exc),
        )
        # Re-raise for Celery retry mechanism
        raise
