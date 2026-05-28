# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""Scheduler module for Celery beat and task definitions."""

from backend.scheduler.celery_app import celery_app

__all__ = ["celery_app"]
