# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Discovery Engine API — 6 endpoints for triggering runs and retrieving results.

POST   /discovery/run/{candidate_id}       → trigger manual run
GET    /discovery/digest/{candidate_id}    → get latest digest
GET    /discovery/digests/{candidate_id}   → list all digests (paginated)
GET    /discovery/job/{job_id}             → get job detail
PATCH  /discovery/job/{job_id}/status      → update job status
GET    /discovery/stats/{candidate_id}     → run history + metrics
"""

from uuid import UUID
from typing import Optional

import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.agents.discovery.orchestrator import DiscoveryOrchestrator
from backend.agents.discovery.schemas import DailyDigestSchema
from backend.models.discovery import DailyDigest, DiscoveredJob, CrawlRun
from backend.config import settings

logger = structlog.get_logger(__name__)
router = APIRouter()


# ─── Shared dependency ────────────────────────────────────────────────────────

async def get_redis() -> aioredis.Redis:
    """FastAPI dependency providing a Redis connection."""
    client = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()


# ─── Request/response schemas ─────────────────────────────────────────────────

class RunResponse(BaseModel):
    """Response from a manual discovery run trigger."""
    message: str
    candidate_id: UUID
    dry_run: bool


class JobStatusUpdate(BaseModel):
    """Payload for updating a job's pipeline status."""
    status: str  # APPROVED | SKIPPED | APPLIED | INTERVIEWING | OFFERED | REJECTED


class DigestSummary(BaseModel):
    """Lightweight digest list entry."""
    id: UUID
    run_date: str
    total_discovered: int
    total_scored: int
    digest_summary: Optional[str]
    created_at: str


class StatsResponse(BaseModel):
    """Run history stats for a candidate."""
    candidate_id: UUID
    total_runs: int
    total_discovered: int
    total_scored: int
    last_run: Optional[str]
    recent_runs: list[dict]


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/run/{candidate_id}", response_model=RunResponse)
async def trigger_run(
    candidate_id: UUID,
    background_tasks: BackgroundTasks,
    dry_run: bool = Query(default=False, description="Run without writing to DB"),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """
    Trigger a manual discovery run for a candidate.

    Runs in the background so the HTTP response returns immediately.
    Monitor progress via the /stats endpoint or Redis pub/sub.
    """
    async def _run():
        orchestrator = DiscoveryOrchestrator(db=db, redis_client=redis)
        try:
            await orchestrator.run(candidate_id=candidate_id, dry_run=dry_run)
        except Exception as e:
            logger.error("api.discovery.run_failed", candidate_id=str(candidate_id), error=str(e))

    background_tasks.add_task(_run)
    logger.info("api.discovery.run_triggered", candidate_id=str(candidate_id), dry_run=dry_run)

    return RunResponse(
        message="Discovery run started",
        candidate_id=candidate_id,
        dry_run=dry_run,
    )


@router.get("/digest/{candidate_id}", response_model=DailyDigestSchema)
async def get_latest_digest(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get the most recent digest for a candidate."""
    result = await db.execute(
        select(DailyDigest)
        .where(DailyDigest.candidate_id == candidate_id)
        .order_by(desc(DailyDigest.created_at))
        .limit(1)
    )
    digest = result.scalar_one_or_none()
    if not digest:
        raise HTTPException(status_code=404, detail="No digest found for this candidate")

    return DailyDigestSchema(
        candidate_id=digest.candidate_id,
        run_date=digest.run_date.isoformat(),
        total_discovered=digest.total_discovered,
        total_scored=digest.total_scored,
        top_picks=digest.top_picks or [],
        hot_picks=digest.hot_picks or [],
        new_companies=digest.new_companies or [],
        digest_summary=digest.digest_summary or "",
    )


@router.get("/digests/{candidate_id}", response_model=list[DigestSummary])
async def list_digests(
    candidate_id: UUID,
    limit: int = Query(default=30, le=100),
    offset: int = Query(default=0),
    db: AsyncSession = Depends(get_db),
):
    """List all digests for a candidate, newest first."""
    result = await db.execute(
        select(DailyDigest)
        .where(DailyDigest.candidate_id == candidate_id)
        .order_by(desc(DailyDigest.created_at))
        .limit(limit)
        .offset(offset)
    )
    digests = result.scalars().all()

    return [
        DigestSummary(
            id=d.id,
            run_date=d.run_date.isoformat(),
            total_discovered=d.total_discovered,
            total_scored=d.total_scored,
            digest_summary=d.digest_summary,
            created_at=d.created_at.isoformat(),
        )
        for d in digests
    ]


@router.get("/job/{job_id}")
async def get_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get full job detail for a specific discovered job."""
    result = await db.execute(
        select(DiscoveredJob).where(DiscoveredJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "url": job.url,
        "description": job.description,
        "source": job.source,
        "posted_date": job.posted_date.isoformat() if job.posted_date else None,
        "status": job.status,
        "created_at": job.created_at.isoformat(),
    }


@router.patch("/job/{job_id}/status")
async def update_job_status(
    job_id: UUID,
    payload: JobStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update the pipeline status of a discovered job (approve, skip, etc.)."""
    valid_statuses = {"APPROVED", "SKIPPED", "APPLIED", "INTERVIEWING", "OFFERED", "REJECTED"}
    if payload.status not in valid_statuses:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status. Must be one of: {', '.join(sorted(valid_statuses))}",
        )

    result = await db.execute(
        select(DiscoveredJob).where(DiscoveredJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    old_status = job.status
    job.status = payload.status
    await db.commit()

    logger.info(
        "api.discovery.job_status_updated",
        job_id=str(job_id),
        old_status=old_status,
        new_status=payload.status,
    )
    return {"job_id": job_id, "status": payload.status}


@router.get("/stats/{candidate_id}", response_model=StatsResponse)
async def get_stats(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return run history and aggregate metrics for a candidate."""
    result = await db.execute(
        select(CrawlRun)
        .where(CrawlRun.candidate_id == candidate_id)
        .order_by(desc(CrawlRun.started_at))
        .limit(10)
    )
    runs = result.scalars().all()

    total_discovered = sum(r.jobs_discovered for r in runs)
    total_scored = sum(r.jobs_scored for r in runs)
    last_run = runs[0].started_at.isoformat() if runs else None

    recent_runs = [
        {
            "id": str(r.id),
            "started_at": r.started_at.isoformat(),
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "status": r.status,
            "jobs_discovered": r.jobs_discovered,
            "jobs_scored": r.jobs_scored,
        }
        for r in runs
    ]

    return StatsResponse(
        candidate_id=candidate_id,
        total_runs=len(runs),
        total_discovered=total_discovered,
        total_scored=total_scored,
        last_run=last_run,
        recent_runs=recent_runs,
    )
