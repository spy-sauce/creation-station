# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Celery Beat schedule configuration for daily discovery runs.

Runs at 07:00 America/New_York daily, iterating over all active candidates
and dispatching individual discovery tasks with idempotent task IDs.

Schedule:
    07:00 America/New_York → dispatch_daily_discovery_runs
    → For each active candidate: daily_discovery_task(candidate_id)

Idempotency:
    Task ID format: discovery-{candidate_id}-{YYYY-MM-DD}
    Prevents duplicate runs if the beat scheduler or worker re-fires.

Contract: HYPHA-SCHEDULER.md
Symbol: beat_schedule (owner: scheduler-agent)
"""

from __future__ import annotations

import asyncio
from datetime import date
from typing import TYPE_CHECKING

import structlog
from celery import Task
from celery.schedules import crontab
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from backend.config import settings
from backend.scheduler.celery_app import celery_app

if TYPE_CHECKING:
    from backend.models.discovery import Candidate

logger = structlog.get_logger(__name__)


def _compute_task_id(candidate_id: str) -> str:
    """Compute idempotent task ID for a candidate on today's date (UTC).

    Format: discovery-{candidate_id}-{YYYY-MM-DD}

    Args:
        candidate_id: The candidate's UUID as string

    Returns:
        Idempotent task ID string
    """
    run_date = date.today().isoformat()
    return f"discovery-{candidate_id}-{run_date}"


async def _get_active_candidates() -> list[str]:
    """Query all active candidate IDs from the database.

    Creates a fresh DB session for this query, ensuring no connection
    pooling issues across Celery tasks.

    Returns:
        List of candidate UUID strings
    """
    from backend.models.discovery import Candidate

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
            # Query all candidates (single-tenant MVP — all candidates are active)
            # Future: add is_active column filter when multi-tenant
            result = await db.execute(select(Candidate.id))
            candidate_ids = [str(row[0]) for row in result.fetchall()]

            logger.info(
                "beat.candidates_queried",
                count=len(candidate_ids),
            )

            return candidate_ids
    finally:
        await engine.dispose()


@celery_app.task(
    bind=True,
    name="backend.scheduler.tasks.dispatch_daily_discovery_runs",
    acks_late=True,
    track_started=True,
)
def dispatch_daily_discovery_runs(self: Task) -> dict:
    """Dispatch daily discovery tasks for all active candidates.

    This task is triggered by the Celery beat scheduler at 07:00 America/New_York.
    It queries all active candidates and dispatches individual discovery tasks
    with idempotent task IDs to prevent duplicate runs.

    Returns:
        dict with dispatched count and task IDs
    """
    log = logger.bind(task="dispatch_daily_discovery_runs")
    log.info("beat.dispatch_started")

    # Query active candidates
    candidate_ids = asyncio.run(_get_active_candidates())

    if not candidate_ids:
        log.info("beat.no_candidates")
        return {
            "status": "completed",
            "dispatched": 0,
            "message": "No active candidates found",
        }

    # Dispatch individual tasks with idempotent task IDs
    dispatched_tasks = []

    for candidate_id in candidate_ids:
        task_id = _compute_task_id(candidate_id)

        # Import here to avoid circular import at module load
        from backend.scheduler.tasks import daily_discovery_task

        daily_discovery_task.apply_async(
            args=[candidate_id],
            task_id=task_id,
        )

        dispatched_tasks.append({
            "candidate_id": candidate_id,
            "task_id": task_id,
        })

        log.info(
            "beat.task_dispatched",
            candidate_id=candidate_id,
            task_id=task_id,
        )

    log.info(
        "beat.dispatch_completed",
        dispatched=len(dispatched_tasks),
    )

    return {
        "status": "completed",
        "dispatched": len(dispatched_tasks),
        "tasks": dispatched_tasks,
    }


# Beat schedule configuration
# Maps task name → schedule + options
beat_schedule = {
    "dispatch-daily-discovery": {
        "task": "backend.scheduler.tasks.dispatch_daily_discovery_runs",
        "schedule": crontab(hour=7, minute=0),  # 07:00 in timezone configured on celery_app
        "options": {
            "queue": "default",
        },
    },
}

# Apply beat schedule to the Celery app
celery_app.conf.beat_schedule = beat_schedule
