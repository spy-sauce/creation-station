# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Application Orchestrator — coordinates the full application pipeline for an approved job.

Pipeline flow:
  receive_approved_job(job_id)
    → jd_parser.parse(job)
    → resume_tailor.tailor(parsed_jd, candidate)      ← parallel
    → company_intel.research(company)                  ← parallel
    → contact_finder.find(intel, parsed_jd)
    → outreach_composer.compose(all_context)
    → [PAUSE — await Review Dashboard approval]
    → auto_apply.submit(job, resume)                  ← only if APPROVED
    → log CRM events throughout

Status machine:
  QUEUED → PARSING → TAILORING → RESEARCHING → COMPOSING →
  AWAITING_REVIEW → APPROVED/REJECTED → SUBMITTED → SENT → TRACKED
"""

import asyncio
from uuid import UUID

import redis.asyncio as aioredis
import structlog
from anthropic import AsyncAnthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.agents.application.jd_parser import JDParser
from backend.agents.application.resume_tailor import ResumeTailor
from backend.agents.application.company_intel import CompanyIntelAgent
from backend.agents.application.contact_finder import ContactFinder
from backend.agents.application.outreach_composer import OutreachComposer
from backend.agents.application.auto_apply import AutoApplyAgent
from backend.agents.application.crm import CRM
from backend.agents.application.schemas import ApplicationPipelineSchema
from backend.agents.discovery.schemas import CandidateSchema
from backend.agents.discovery.identity_profiler import IdentityProfiler
from backend.models.discovery import Candidate as CandidateORM, DiscoveredJob, ScoredJob
from backend.models.application import ApplicationPipeline as ApplicationPipelineORM

logger = structlog.get_logger(__name__)

_STATUS_CHANNEL = "agent.status.application"


class ApplicationOrchestrator:
    """
    Coordinates the full application pipeline for a single approved job.

    resume_tailor and company_intel run concurrently — both need parsed_jd
    but don't depend on each other. This cuts wall-clock time roughly in half.
    """

    def __init__(
        self,
        db: AsyncSession,
        redis_client: aioredis.Redis,
    ):
        self._db = db
        self._redis = redis_client
        self._claude = AsyncAnthropic(api_key=settings.anthropic_api_key)

        self._jd_parser = JDParser(db, self._claude)
        self._resume_tailor = ResumeTailor(db, self._claude)
        self._company_intel = CompanyIntelAgent(db, redis_client, self._claude)
        self._contact_finder = ContactFinder(db)
        self._composer = OutreachComposer(db, self._claude)
        self._auto_apply = AutoApplyAgent()
        self._crm = CRM(db)
        self._profiler = IdentityProfiler(redis_client, self._claude)

    async def start(self, job_id: UUID, candidate_id: UUID) -> ApplicationPipelineSchema:
        """
        Start the application pipeline for an approved job.

        Runs through JD parsing, resume tailoring, company research,
        and outreach composition. Pauses at AWAITING_REVIEW.

        Args:
            job_id: Approved job to process
            candidate_id: Candidate to build application for

        Returns:
            ApplicationPipelineSchema with all artifacts ready for review
        """
        log = logger.bind(job_id=str(job_id), candidate_id=str(candidate_id))
        log.info("application_orchestrator.starting")

        # Create pipeline record
        pipeline = await self._create_pipeline(job_id, candidate_id)
        pipeline_id = pipeline.id

        try:
            # Load candidate + job
            candidate = await self._load_candidate(candidate_id)
            job = await self._load_scored_job(job_id, candidate_id)
            profile = await self._profiler.build_profile(candidate)

            log.info("application_orchestrator.loaded", candidate=candidate.name)

            # Step 1: Parse JD
            await self._crm.update_pipeline_status(pipeline_id, "PARSING", "jd_parser")
            parsed_jd = await self._jd_parser.parse(job)
            await self._crm.log(pipeline_id, candidate_id, job_id, "JD_PARSED", {
                "required_skills": parsed_jd.required_skills[:5],
                "seniority_level": parsed_jd.seniority_level,
            })
            log.info("application_orchestrator.jd_parsed", skills=len(parsed_jd.required_skills))

            # Steps 2+3: Resume tailoring and company research run in parallel
            await self._crm.update_pipeline_status(pipeline_id, "TAILORING", "resume_tailor+company_intel")

            resume_task = asyncio.create_task(
                self._resume_tailor.tailor(parsed_jd, candidate, profile)
            )
            intel_task = asyncio.create_task(
                self._company_intel.research(
                    job.job.company,
                    company_url=None,  # Could be extracted from job URL
                )
            )

            resume, intel = await asyncio.gather(resume_task, intel_task)

            await self._crm.log(pipeline_id, candidate_id, job_id, "RESUME_TAILORED", {
                "version": resume.version,
            })
            await self._crm.log(pipeline_id, candidate_id, job_id, "COMPANY_RESEARCHED", {
                "company": intel.company_name,
                "growth_stage": intel.growth_stage,
            })
            log.info("application_orchestrator.parallel_complete")

            # Step 4: Find contact
            await self._crm.update_pipeline_status(pipeline_id, "RESEARCHING", "contact_finder")
            contact = await self._contact_finder.find(intel, parsed_jd)
            await self._crm.log(pipeline_id, candidate_id, job_id, "CONTACT_FOUND", {
                "email": contact.email,
                "confidence": contact.confidence,
                "source": contact.source,
            })

            # Step 5: Compose outreach
            await self._crm.update_pipeline_status(pipeline_id, "COMPOSING", "outreach_composer")
            email = await self._composer.compose(
                parsed_jd=parsed_jd,
                intel=intel,
                contact=contact,
                resume=resume,
                profile=profile,
                candidate_name=candidate.name,
                candidate_email=candidate.email,
                candidate_github=candidate.github_url,
                candidate_linkedin=candidate.linkedin_url,
            )
            await self._crm.log(pipeline_id, candidate_id, job_id, "EMAIL_DRAFTED", {
                "subject": email.subject,
                "tone": email.tone_used,
            })

            # Pause — await human review
            await self._crm.update_pipeline_status(pipeline_id, "AWAITING_REVIEW")
            await self._publish_status(pipeline_id, candidate_id, "AWAITING_REVIEW")

            log.info("application_orchestrator.awaiting_review", pipeline_id=str(pipeline_id))

            return ApplicationPipelineSchema(
                id=pipeline_id,
                job_id=job_id,
                candidate_id=candidate_id,
                status="AWAITING_REVIEW",
                parsed_jd=parsed_jd,
                tailored_resume=resume,
                company_intel=intel,
                contact=contact,
                outreach_email=email,
            )

        except Exception as e:
            log.error("application_orchestrator.failed", error=str(e))
            await self._crm.update_pipeline_status(pipeline_id, "FAILED")
            await self._crm.log(pipeline_id, candidate_id, job_id, "PIPELINE_FAILED", {
                "error": str(e)
            })
            raise

    async def submit(self, pipeline_id: UUID) -> None:
        """
        Execute the approved submission — called only after Review Dashboard approval.

        Runs auto_apply for form submission. CRM logs the outcome.

        Args:
            pipeline_id: The pipeline that was approved in the Review Dashboard
        """
        result_orm = await self._db.execute(
            select(ApplicationPipelineORM).where(ApplicationPipelineORM.id == pipeline_id)
        )
        pipeline = result_orm.scalar_one_or_none()
        if not pipeline:
            raise ValueError(f"Pipeline {pipeline_id} not found")
        if pipeline.status != "APPROVED":
            raise ValueError(f"Pipeline {pipeline_id} is not APPROVED (status: {pipeline.status})")

        log = logger.bind(pipeline_id=str(pipeline_id))
        log.info("application_orchestrator.submitting")

        candidate = await self._load_candidate(pipeline.candidate_id)
        job_result = await self._db.execute(
            select(DiscoveredJob).where(DiscoveredJob.id == pipeline.job_id)
        )
        job = job_result.scalar_one_or_none()

        if not job:
            raise ValueError(f"Job {pipeline.job_id} not found")

        # Load tailored resume
        from backend.models.application import TailoredResume as TailoredResumeORM
        from backend.agents.application.schemas import TailoredResumeSchema
        resume_result = await self._db.execute(
            select(TailoredResumeORM).where(TailoredResumeORM.id == pipeline.resume_id)
        )
        resume_orm = resume_result.scalar_one_or_none()
        resume = TailoredResumeSchema(
            job_id=pipeline.job_id,
            candidate_id=pipeline.candidate_id,
            full_text=resume_orm.full_text if resume_orm else "",
            summary=resume_orm.summary if resume_orm else "",
            change_log=resume_orm.change_log if resume_orm else "",
            pdf_path=resume_orm.pdf_path if resume_orm else None,
        )

        result = await self._auto_apply.submit(
            job_url=job.url,
            job_id=pipeline.job_id,
            pipeline_id=pipeline_id,
            candidate=candidate,
            resume=resume,
        )

        await self._crm.update_pipeline_status(pipeline_id, result.status)
        await self._crm.log(
            pipeline_id, pipeline.candidate_id, pipeline.job_id,
            "SUBMITTED",
            {"status": result.status, "confirmation": result.confirmation_number, "fields": result.fields_completed},
        )
        log.info("application_orchestrator.submit_complete", status=result.status)

    async def _create_pipeline(
        self, job_id: UUID, candidate_id: UUID
    ) -> ApplicationPipelineORM:
        """Create a new ApplicationPipeline record and return it."""
        pipeline = ApplicationPipelineORM(
            job_id=job_id,
            candidate_id=candidate_id,
            status="QUEUED",
        )
        self._db.add(pipeline)
        await self._db.commit()
        await self._db.refresh(pipeline)
        return pipeline

    async def _load_candidate(self, candidate_id: UUID) -> CandidateSchema:
        """Load candidate from PostgreSQL."""
        result = await self._db.execute(
            select(CandidateORM).where(CandidateORM.id == candidate_id)
        )
        orm = result.scalar_one_or_none()
        if not orm:
            raise ValueError(f"Candidate {candidate_id} not found")
        return CandidateSchema.model_validate(orm)

    async def _load_scored_job(self, job_id: UUID, candidate_id: UUID):
        """Load the scored job — wraps DiscoveredJob + ScoredJob into ScoredJobSchema."""
        from backend.agents.discovery.schemas import (
            DiscoveredJobSchema, ScoredJobSchema, ScoreBreakdown
        )

        job_result = await self._db.execute(
            select(DiscoveredJob).where(DiscoveredJob.id == job_id)
        )
        job_orm = job_result.scalar_one_or_none()
        if not job_orm:
            raise ValueError(f"Job {job_id} not found")

        score_result = await self._db.execute(
            select(ScoredJob).where(ScoredJob.job_id == job_id)
        )
        score_orm = score_result.scalar_one_or_none()

        job_schema = DiscoveredJobSchema(
            id=job_orm.id,
            candidate_id=job_orm.candidate_id,
            title=job_orm.title,
            company=job_orm.company,
            location=job_orm.location,
            url=job_orm.url,
            url_hash=job_orm.url_hash,
            description=job_orm.description,
            source=job_orm.source,
        )

        scores = ScoreBreakdown(
            technical_match=score_orm.technical_match or 70 if score_orm else 70,
            level_match=score_orm.level_match or 70 if score_orm else 70,
            culture_match=score_orm.culture_match or 70 if score_orm else 70,
            industry_match=score_orm.industry_match or 70 if score_orm else 70,
            growth_potential=score_orm.growth_potential or 70 if score_orm else 70,
            compensation_match=score_orm.compensation_match or 70 if score_orm else 70,
        )

        return ScoredJobSchema(
            job=job_schema,
            scores=scores,
            composite_score=score_orm.composite_score if score_orm else 70,
            reasoning=score_orm.reasoning or "" if score_orm else "",
            is_hot=score_orm.is_hot if score_orm else False,
        )

    async def _publish_status(
        self, pipeline_id: UUID, candidate_id: UUID, status: str
    ) -> None:
        """Publish pipeline status event to Redis pub/sub."""
        import json
        payload = json.dumps({
            "event": "APPLICATION_STATUS",
            "pipeline_id": str(pipeline_id),
            "candidate_id": str(candidate_id),
            "status": status,
        })
        await self._redis.publish(_STATUS_CHANNEL, payload)
