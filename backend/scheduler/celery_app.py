# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""Celery app factory for the Talent Agent scheduler.

Reads broker URL from settings.redis_url. Configures task serialization,
timezone, and result backend for the autonomous job discovery system.
"""

from celery import Celery
import structlog

from backend.config import settings

logger = structlog.get_logger(__name__)


def create_celery_app() -> Celery:
    """Create and configure the Celery application.

    Returns:
        Celery: Configured Celery application instance.
    """
    app = Celery(
        "talent_agent",
        broker=settings.redis_url,
        backend=settings.redis_url,
        include=["backend.scheduler.tasks"],
    )

    app.conf.update(
        # Timezone for beat scheduler (07:00 America/New_York)
        timezone="America/New_York",
        enable_utc=True,
        # Task serialization
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        # Task execution settings
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        # Result expiration (24 hours)
        result_expires=86400,
        # Worker settings
        worker_prefetch_multiplier=1,
        worker_concurrency=4,
        # Task tracking
        task_track_started=True,
        task_send_sent_event=True,
        # Broker connection retry
        broker_connection_retry_on_startup=True,
    )

    logger.info(
        "celery_app_created",
        broker=settings.redis_url.split("@")[-1] if "@" in settings.redis_url else settings.redis_url,
        timezone="America/New_York",
    )

    return app


# Module-level Celery app instance
celery_app = create_celery_app()
