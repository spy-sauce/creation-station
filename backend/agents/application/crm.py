# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
CRM — tracks every application and its outcome over time.

Simple PostgreSQL-backed event log. No third-party CRM dependency.
Every significant moment in the application journey gets an event.

Event types:
  APPLICATION_STARTED
  RESUME_TAILORED
  COMPANY_RESEARCHED
  CONTACT_FOUND
  EMAIL_DRAFTED
  APPROVED_FOR_SUBMISSION
  SUBMITTED
  EMAIL_SENT
  EMAIL_OPENED
  RESPONDED
  INTERVIEW_SCHEDULED
  OFFER_RECEIVED
  REJECTED
  PLACED
"""

from uuid import UUID
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models.application import CRMEvent as CRMEventORM, ApplicationPipeline

logger = structlog.get_logger(__name__)


class CRM:
    """
    Logs application lifecycle events to PostgreSQL.

    Provides a complete audit trail for every application from start to placement.
    """

    def __init__(self, db: AsyncSession):
        self._db = db

    async def log(
        self,
        pipeline_id: UUID,
        candidate_id: UUID,
        job_id: UUID,
        event_type: str,
        details: Optional[dict] = None,
    ) -> None:
        """
        Record an event in the application timeline.

        Args:
            pipeline_id: The application pipeline this event belongs to
            candidate_id: Candidate FK
            job_id: Job FK
            event_type: One of the defined event type strings
            details: Optional metadata dict (scores, email subjects, confirmation numbers, etc.)
        """
        orm = CRMEventORM(
            pipeline_id=pipeline_id,
            candidate_id=candidate_id,
            job_id=job_id,
            event_type=event_type,
            details=details,
        )
        self._db.add(orm)
        await self._db.commit()

        logger.info(
            "crm.event_logged",
            pipeline_id=str(pipeline_id),
            event_type=event_type,
        )

    async def get_timeline(self, pipeline_id: UUID) -> list[dict]:
        """
        Return the full event timeline for an application pipeline.

        Args:
            pipeline_id: Pipeline to fetch events for

        Returns:
            List of event dicts ordered by created_at ascending
        """
        result = await self._db.execute(
            select(CRMEventORM)
            .where(CRMEventORM.pipeline_id == pipeline_id)
            .order_by(CRMEventORM.created_at.asc())
        )
        events = result.scalars().all()
        return [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "details": e.details,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ]

    async def update_pipeline_status(
        self, pipeline_id: UUID, status: str, current_step: Optional[str] = None
    ) -> None:
        """
        Update the application pipeline's status and log the transition.

        Args:
            pipeline_id: Pipeline to update
            status: New pipeline status
            current_step: Optional current step name
        """
        result = await self._db.execute(
            select(ApplicationPipeline).where(ApplicationPipeline.id == pipeline_id)
        )
        pipeline = result.scalar_one_or_none()
        if not pipeline:
            logger.warning("crm.pipeline_not_found", pipeline_id=str(pipeline_id))
            return

        old_status = pipeline.status
        pipeline.status = status
        if current_step:
            pipeline.current_step = current_step

        await self._db.commit()

        logger.info(
            "crm.status_updated",
            pipeline_id=str(pipeline_id),
            old_status=old_status,
            new_status=status,
        )
