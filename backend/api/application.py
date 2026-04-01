# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Application Engine API — triggers and monitors the application pipeline.

POST   /application/start/{job_id}          → start pipeline for approved job
POST   /application/cloud/{job_id}          → start pipeline via cloud agent manager
GET    /application/pipeline/{pipeline_id}  → get pipeline status + artifacts
GET    /application/pipelines/{candidate_id} → list all pipelines for candidate
GET    /application/crm/{candidate_id}      → CRM event log for all applications
POST   /application/submit/{pipeline_id}    → trigger auto-submit (post-approval)
GET    /application/agents                  → list registered cloud sub-agents
GET    /application/agents/plan             → preview execution plan (dependency tiers)
POST   /application/agents/{agent_name}     → run a single sub-agent in isolation
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
from backend.api.discovery import get_redis
from backend.agents.application.orchestrator import ApplicationOrchestrator
from backend.agents.application.agent_manager import AgentManager
from backend.agents.application.crm import CRM
from backend.models.application import ApplicationPipeline, CRMEvent

logger = structlog.get_logger(__name__)
router = APIRouter()


# ─── Request/response schemas ─────────────────────────────────────────────────

class StartPipelineRequest(BaseModel):
    """Start an application pipeline for an approved job."""
    candidate_id: UUID


class CloudPipelineRequest(BaseModel):
    """Start a cloud-dispatched pipeline via the Agent Manager."""
    candidate_id: UUID
    agents: Optional[list[str]] = None


class SingleAgentRequest(BaseModel):
    """Run a single sub-agent in isolation."""
    pipeline_id: UUID
    input_payload: dict


class PipelineStatusResponse(BaseModel):
    """Current status of an application pipeline."""
    pipeline_id: UUID
    job_id: UUID
    candidate_id: UUID
    status: str
    current_step: Optional[str]
    created_at: str
    updated_at: str


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/start/{job_id}", response_model=PipelineStatusResponse)
async def start_pipeline(
    job_id: UUID,
    payload: StartPipelineRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """
    Start the application pipeline for an approved job.

    Runs asynchronously — returns immediately with the pipeline ID.
    Monitor progress via GET /application/pipeline/{pipeline_id}.
    """
    orchestrator = ApplicationOrchestrator(db=db, redis_client=redis)

    async def _run():
        try:
            await orchestrator.start(job_id=job_id, candidate_id=payload.candidate_id)
        except Exception as e:
            logger.error(
                "api.application.pipeline_failed",
                job_id=str(job_id),
                error=str(e),
            )

    background_tasks.add_task(_run)

    # Create pipeline record immediately so we can return its ID
    from backend.models.application import ApplicationPipeline as APipeline
    from datetime import datetime, timezone
    pipeline = APipeline(
        job_id=job_id,
        candidate_id=payload.candidate_id,
        status="QUEUED",
    )
    db.add(pipeline)
    await db.commit()
    await db.refresh(pipeline)

    logger.info(
        "api.application.pipeline_started",
        pipeline_id=str(pipeline.id),
        job_id=str(job_id),
    )

    return PipelineStatusResponse(
        pipeline_id=pipeline.id,
        job_id=pipeline.job_id,
        candidate_id=pipeline.candidate_id,
        status=pipeline.status,
        current_step=pipeline.current_step,
        created_at=pipeline.created_at.isoformat(),
        updated_at=pipeline.updated_at.isoformat(),
    )


@router.get("/pipeline/{pipeline_id}", response_model=PipelineStatusResponse)
async def get_pipeline(
    pipeline_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get the current status and step of an application pipeline."""
    result = await db.execute(
        select(ApplicationPipeline).where(ApplicationPipeline.id == pipeline_id)
    )
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    return PipelineStatusResponse(
        pipeline_id=pipeline.id,
        job_id=pipeline.job_id,
        candidate_id=pipeline.candidate_id,
        status=pipeline.status,
        current_step=pipeline.current_step,
        created_at=pipeline.created_at.isoformat(),
        updated_at=pipeline.updated_at.isoformat(),
    )


@router.get("/pipelines/{candidate_id}")
async def list_pipelines(
    candidate_id: UUID,
    status: Optional[str] = Query(default=None, description="Filter by status"),
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all application pipelines for a candidate, newest first."""
    query = (
        select(ApplicationPipeline)
        .where(ApplicationPipeline.candidate_id == candidate_id)
        .order_by(desc(ApplicationPipeline.updated_at))
        .limit(limit)
    )
    if status:
        query = query.where(ApplicationPipeline.status == status)

    result = await db.execute(query)
    pipelines = result.scalars().all()

    return [
        {
            "pipeline_id": str(p.id),
            "job_id": str(p.job_id),
            "status": p.status,
            "current_step": p.current_step,
            "created_at": p.created_at.isoformat(),
            "updated_at": p.updated_at.isoformat(),
        }
        for p in pipelines
    ]


@router.get("/crm/{candidate_id}")
async def get_crm_log(
    candidate_id: UUID,
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Return CRM event log for all applications by this candidate."""
    result = await db.execute(
        select(CRMEvent)
        .where(CRMEvent.candidate_id == candidate_id)
        .order_by(desc(CRMEvent.created_at))
        .limit(limit)
    )
    events = result.scalars().all()

    return [
        {
            "id": str(e.id),
            "pipeline_id": str(e.pipeline_id),
            "job_id": str(e.job_id),
            "event_type": e.event_type,
            "details": e.details,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]


@router.post("/submit/{pipeline_id}")
async def submit_application(
    pipeline_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """
    Trigger auto-submit for an APPROVED pipeline.

    This is the second human confirmation — pipeline must be in APPROVED status.
    """
    result = await db.execute(
        select(ApplicationPipeline).where(ApplicationPipeline.id == pipeline_id)
    )
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    if pipeline.status != "APPROVED":
        raise HTTPException(
            status_code=422,
            detail=f"Pipeline must be in APPROVED status to submit (current: {pipeline.status})",
        )

    orchestrator = ApplicationOrchestrator(db=db, redis_client=redis)

    async def _submit():
        try:
            await orchestrator.submit(pipeline_id=pipeline_id)
        except Exception as e:
            logger.error("api.application.submit_failed", pipeline_id=str(pipeline_id), error=str(e))

    background_tasks.add_task(_submit)

    logger.info("api.application.submit_triggered", pipeline_id=str(pipeline_id))
    return {"pipeline_id": str(pipeline_id), "message": "Submission started"}


# ─── Cloud Agent Manager Endpoints ──────────────────────────────────────────


@router.post("/cloud/{job_id}")
async def start_cloud_pipeline(
    job_id: UUID,
    payload: CloudPipelineRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """
    Start the application pipeline via cloud-dispatched sub-agents.

    Each sub-agent runs as an independent Claude API call with its own
    system prompt and tool definitions. Agents within the same dependency
    tier execute concurrently.

    Returns immediately with pipeline ID. Monitor via GET /application/pipeline/{id}.
    """
    from backend.models.application import ApplicationPipeline as APipeline

    # Create pipeline record
    pipeline = APipeline(
        job_id=job_id,
        candidate_id=payload.candidate_id,
        status="QUEUED",
    )
    db.add(pipeline)
    await db.commit()
    await db.refresh(pipeline)
    pipeline_id = pipeline.id

    # Load job data for the agent context
    from backend.models.discovery import DiscoveredJob, Candidate as CandidateORM
    job_result = await db.execute(
        select(DiscoveredJob).where(DiscoveredJob.id == job_id)
    )
    job_orm = job_result.scalar_one_or_none()
    if not job_orm:
        raise HTTPException(status_code=404, detail="Job not found")

    candidate_result = await db.execute(
        select(CandidateORM).where(CandidateORM.id == payload.candidate_id)
    )
    candidate_orm = candidate_result.scalar_one_or_none()
    if not candidate_orm:
        raise HTTPException(status_code=404, detail="Candidate not found")

    job_data = {
        "job_id": str(job_orm.id),
        "title": job_orm.title,
        "company": job_orm.company,
        "description": job_orm.description or "",
        "url": job_orm.url,
        "location": job_orm.location or "",
        "source": job_orm.source or "",
    }
    candidate_data = {
        "id": str(candidate_orm.id),
        "name": candidate_orm.name,
        "email": candidate_orm.email,
        "resume_text": candidate_orm.resume_text or "",
        "linkedin_url": candidate_orm.linkedin_url,
        "github_url": candidate_orm.github_url,
    }

    async def _run_cloud():
        try:
            manager = AgentManager(db=db, redis_client=redis)
            results = await manager.run_application_pipeline(
                pipeline_id=pipeline_id,
                job_data=job_data,
                candidate_data=candidate_data,
                agents=payload.agents,
            )
            # Update pipeline status based on results
            all_completed = all(
                r.status == "COMPLETED" for r in results.values()
            )
            final_status = "AWAITING_REVIEW" if all_completed else "FAILED"
            pipeline.status = final_status
            await db.commit()

            logger.info(
                "api.application.cloud_pipeline_complete",
                pipeline_id=str(pipeline_id),
                status=final_status,
                agents_run=list(results.keys()),
            )
        except Exception as e:
            logger.error(
                "api.application.cloud_pipeline_failed",
                pipeline_id=str(pipeline_id),
                error=str(e),
            )
            pipeline.status = "FAILED"
            await db.commit()

    background_tasks.add_task(_run_cloud)

    logger.info(
        "api.application.cloud_pipeline_started",
        pipeline_id=str(pipeline_id),
        job_id=str(job_id),
        agents=payload.agents,
    )

    return {
        "pipeline_id": str(pipeline_id),
        "mode": "cloud",
        "message": "Cloud agent pipeline dispatched",
        "agents": payload.agents or [
            "jd_parser", "resume_tailor", "company_intel",
            "contact_finder", "outreach_composer",
        ],
    }


@router.get("/agents")
async def list_agents(
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """List all registered cloud sub-agents with their metadata."""
    manager = AgentManager(db=db, redis_client=redis)
    return {"agents": manager.list_agents()}


@router.get("/agents/plan")
async def get_execution_plan(
    agents: Optional[str] = Query(
        default=None,
        description="Comma-separated agent names (defaults to full pipeline)",
    ),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """
    Preview the execution plan without running anything.

    Returns tiers of agents — agents within a tier run concurrently.
    """
    manager = AgentManager(db=db, redis_client=redis)
    agent_list = agents.split(",") if agents else None
    tiers = manager.get_execution_plan(agent_list)
    return {
        "tiers": [
            {"tier": i, "agents": tier, "concurrent": len(tier) > 1}
            for i, tier in enumerate(tiers)
        ],
    }


@router.post("/agents/{agent_name}")
async def run_single_agent(
    agent_name: str,
    payload: SingleAgentRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """
    Run a single sub-agent in isolation.

    Useful for re-running a failed agent, testing individual agents,
    or ad-hoc execution outside the full pipeline.
    """
    manager = AgentManager(db=db, redis_client=redis)

    # Validate agent exists
    try:
        manager._registry.get(agent_name)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    async def _run():
        try:
            record = await manager.run_single_agent(
                agent_name=agent_name,
                input_payload=payload.input_payload,
                pipeline_id=payload.pipeline_id,
            )
            logger.info(
                "api.application.single_agent_complete",
                agent=agent_name,
                status=record.status,
                duration_ms=record.duration_ms,
            )
        except Exception as e:
            logger.error(
                "api.application.single_agent_failed",
                agent=agent_name,
                error=str(e),
            )

    background_tasks.add_task(_run)

    return {
        "agent": agent_name,
        "pipeline_id": str(payload.pipeline_id),
        "message": f"Agent '{agent_name}' dispatched",
    }
