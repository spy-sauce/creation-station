# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""Scheduler module for Celery beat and task definitions."""

from backend.scheduler.celery_app import celery_app
from backend.scheduler.tasks import daily_discovery_task, trigger_daily_discovery

__all__ = ["celery_app", "daily_discovery_task", "trigger_daily_discovery"]
