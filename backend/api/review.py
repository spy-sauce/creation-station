# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Review Dashboard API — exposes all draft application artifacts for human review.

Every deliverable (tailored resume, outreach email, form submission) must be
approved here before anything is sent. Human stays in the loop.

GET    /review/queue                        → list all awaiting review
GET    /review/application/{pipeline_id}    → full application package
PATCH  /review/application/{pipeline_id}/approve → approve + trigger submission
PATCH  /review/application/{pipeline_id}/reject  → skip this application
PATCH  /review/resume/{pipeline_id}         → update tailored resume text
PATCH  /review/email/{pipeline_id}          → update outreach email
GET    /review/preview/{pipeline_id}/resume → render resume as plain text
GET    /review/preview/{pipeline_id}/email  → preview email body
GET    /review/timeline/{pipeline_id}       → CRM event timeline
"""

from uuid import UUID
from typing import Optional

import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.api.discovery import get_redis
from backend.agents.application.crm import CRM
from backend.models.application import (
    ApplicationPipeline,
    TailoredResume,
    OutreachEmail,
    ParsedJD,
    CompanyIntel,
    Contact,
)

logger = structlog.get_logger(__name__)
router = APIRouter()


# ─── Request/response schemas ─────────────────────────────────────────────────

class ResumeUpdate(BaseModel):
    """Updated resume text from the Review Dashboard."""
    full_text: str
    summary: Optional[str] = None


class EmailUpdate(BaseModel):
    """Updated email body or subject from the Review Dashboard."""
    body: Optional[str] = None
    subject: Optional[str] = None


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/queue")
async def get_review_queue(
    db: AsyncSession = Depends(get_db),
):
    """List all application pipelines awaiting human review."""
    result = await db.execute(
        select(ApplicationPipeline)
        .where(ApplicationPipeline.status == "AWAITING_REVIEW")
        .order_by(desc(ApplicationPipeline.updated_at))
    )
    pipelines = result.scalars().all()

    return [
        {
            "pipeline_id": str(p.id),
            "job_id": str(p.job_id),
            "candidate_id": str(p.candidate_id),
            "status": p.status,
            "current_step": p.current_step,
            "created_at": p.created_at.isoformat(),
            "updated_at": p.updated_at.isoformat(),
        }
        for p in pipelines
    ]


@router.get("/application/{pipeline_id}")
async def get_application_package(
    pipeline_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Return the full application package for review.

    Includes: pipeline status, tailored resume, outreach email,
    company intel, contact, and parsed JD signals.
    """
    result = await db.execute(
        select(ApplicationPipeline).where(ApplicationPipeline.id == pipeline_id)
    )
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    # Load related artifacts
    resume = await _get_resume(db, pipeline.resume_id)
    email = await _get_email(db, pipeline.email_id)
    parsed_jd = await _get_parsed_jd(db, pipeline.job_id)

    return {
        "pipeline_id": str(pipeline.id),
        "job_id": str(pipeline.job_id),
        "candidate_id": str(pipeline.candidate_id),
        "status": pipeline.status,
        "current_step": pipeline.current_step,
        "resume": resume,
        "email": email,
        "parsed_jd": parsed_jd,
        "created_at": pipeline.created_at.isoformat(),
    }


@router.patch("/application/{pipeline_id}/approve")
async def approve_application(
    pipeline_id: UUID,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """
    Approve this application and trigger auto-submit.

    Status moves from AWAITING_REVIEW → APPROVED → SUBMITTED.
    """
    result = await db.execute(
        select(ApplicationPipeline).where(ApplicationPipeline.id == pipeline_id)
    )
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    if pipeline.status != "AWAITING_REVIEW":
        raise HTTPException(
            status_code=422,
            detail=f"Pipeline is not awaiting review (status: {pipeline.status})",
        )

    pipeline.status = "APPROVED"
    await db.commit()

    crm = CRM(db)
    await crm.log(pipeline_id, pipeline.candidate_id, pipeline.job_id, "APPROVED_FOR_SUBMISSION")

    # Trigger the orchestrator's submit step via the background task
    # (In production, this publishes to Redis and the worker picks it up)
    import json
    await redis.publish(
        "application.approved",
        json.dumps({"pipeline_id": str(pipeline_id), "candidate_id": str(pipeline.candidate_id)}),
    )

    logger.info("review.approved", pipeline_id=str(pipeline_id))
    return {"pipeline_id": str(pipeline_id), "status": "APPROVED"}


@router.patch("/application/{pipeline_id}/reject")
async def reject_application(
    pipeline_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Reject and skip this application."""
    result = await db.execute(
        select(ApplicationPipeline).where(ApplicationPipeline.id == pipeline_id)
    )
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    pipeline.status = "REJECTED"
    await db.commit()

    crm = CRM(db)
    await crm.log(pipeline_id, pipeline.candidate_id, pipeline.job_id, "REJECTED")

    logger.info("review.rejected", pipeline_id=str(pipeline_id))
    return {"pipeline_id": str(pipeline_id), "status": "REJECTED"}


@router.patch("/resume/{pipeline_id}")
async def update_resume(
    pipeline_id: UUID,
    payload: ResumeUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update the tailored resume before approval."""
    result = await db.execute(
        select(ApplicationPipeline).where(ApplicationPipeline.id == pipeline_id)
    )
    pipeline = result.scalar_one_or_none()
    if not pipeline or not pipeline.resume_id:
        raise HTTPException(status_code=404, detail="Resume not found")

    resume_result = await db.execute(
        select(TailoredResume).where(TailoredResume.id == pipeline.resume_id)
    )
    resume = resume_result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume record not found")

    resume.full_text = payload.full_text
    if payload.summary:
        resume.summary = payload.summary
    resume.version += 1
    await db.commit()

    logger.info("review.resume_updated", pipeline_id=str(pipeline_id), version=resume.version)
    return {"pipeline_id": str(pipeline_id), "resume_version": resume.version}


@router.patch("/email/{pipeline_id}")
async def update_email(
    pipeline_id: UUID,
    payload: EmailUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update the outreach email body or subject before approval."""
    result = await db.execute(
        select(ApplicationPipeline).where(ApplicationPipeline.id == pipeline_id)
    )
    pipeline = result.scalar_one_or_none()
    if not pipeline or not pipeline.email_id:
        raise HTTPException(status_code=404, detail="Email not found for this pipeline")

    email_result = await db.execute(
        select(OutreachEmail).where(OutreachEmail.id == pipeline.email_id)
    )
    email = email_result.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="Email record not found")

    if payload.body:
        email.body = payload.body
    if payload.subject:
        email.subject = payload.subject
    await db.commit()

    logger.info("review.email_updated", pipeline_id=str(pipeline_id))
    return {"pipeline_id": str(pipeline_id), "status": "updated"}


@router.get("/preview/{pipeline_id}/resume")
async def preview_resume(
    pipeline_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return tailored resume as plain text for preview."""
    result = await db.execute(
        select(ApplicationPipeline).where(ApplicationPipeline.id == pipeline_id)
    )
    pipeline = result.scalar_one_or_none()
    if not pipeline or not pipeline.resume_id:
        raise HTTPException(status_code=404, detail="Resume not found")

    resume_result = await db.execute(
        select(TailoredResume).where(TailoredResume.id == pipeline.resume_id)
    )
    resume = resume_result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume record not found")

    return {
        "pipeline_id": str(pipeline_id),
        "summary": resume.summary,
        "full_text": resume.full_text,
        "change_log": resume.change_log,
        "version": resume.version,
    }


@router.get("/preview/{pipeline_id}/email")
async def preview_email(
    pipeline_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return outreach email for preview."""
    result = await db.execute(
        select(ApplicationPipeline).where(ApplicationPipeline.id == pipeline_id)
    )
    pipeline = result.scalar_one_or_none()
    if not pipeline or not pipeline.email_id:
        raise HTTPException(status_code=404, detail="Email not found")

    email_result = await db.execute(
        select(OutreachEmail).where(OutreachEmail.id == pipeline.email_id)
    )
    email = email_result.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="Email record not found")

    return {
        "pipeline_id": str(pipeline_id),
        "to": email.contact_id,
        "subject": email.subject,
        "subject_variants": email.subject_variants,
        "body": email.body,
        "tone_used": email.tone_used,
        "hook_used": email.hook_used,
        "status": email.status,
    }


@router.get("/timeline/{pipeline_id}")
async def get_timeline(
    pipeline_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return the full CRM event timeline for a pipeline."""
    crm = CRM(db)
    events = await crm.get_timeline(pipeline_id)
    return {"pipeline_id": str(pipeline_id), "events": events}


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _get_resume(db: AsyncSession, resume_id) -> Optional[dict]:
    if not resume_id:
        return None
    result = await db.execute(select(TailoredResume).where(TailoredResume.id == resume_id))
    r = result.scalar_one_or_none()
    if not r:
        return None
    return {
        "id": str(r.id),
        "summary": r.summary,
        "full_text": r.full_text,
        "change_log": r.change_log,
        "version": r.version,
        "pdf_path": r.pdf_path,
    }


async def _get_email(db: AsyncSession, email_id) -> Optional[dict]:
    if not email_id:
        return None
    result = await db.execute(select(OutreachEmail).where(OutreachEmail.id == email_id))
    e = result.scalar_one_or_none()
    if not e:
        return None
    return {
        "id": str(e.id),
        "subject": e.subject,
        "subject_variants": e.subject_variants,
        "body": e.body,
        "tone_used": e.tone_used,
        "hook_used": e.hook_used,
        "status": e.status,
    }


async def _get_parsed_jd(db: AsyncSession, job_id) -> Optional[dict]:
    if not job_id:
        return None
    result = await db.execute(select(ParsedJD).where(ParsedJD.job_id == job_id))
    p = result.scalar_one_or_none()
    if not p:
        return None
    return {
        "required_skills": p.required_skills,
        "preferred_skills": p.preferred_skills,
        "seniority_level": p.seniority_level,
        "tone": p.tone,
        "team_context": p.team_context,
        "red_flags": p.red_flags,
        "application_instructions": p.application_instructions,
    }
