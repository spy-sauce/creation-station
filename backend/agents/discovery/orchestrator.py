# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Discovery Orchestrator — coordinates the full daily discovery run.

This is the entry point for both the Celery cron job and the manual API trigger.

Flow:
  load_candidate(candidate_id)
    → identity_profiler.build_profile()
    → archetype_generator.expand()
    → crawler_agent.run(manifest)           ← currently stubbed
    → relevance_scorer.score_batch(jobs)
    → digest_builder.compile(scored_jobs)
    → emit DIGEST_READY

Concurrency:
  - Scoring runs with bounded concurrency (CRAWL_CONCURRENCY semaphore)
  - Digest build follows after all scoring is complete

Status machine:
  QUEUED → RUNNING → COMPLETED
                   → FAILED
"""

import asyncio
import json
from datetime import date, datetime, timezone
from uuid import UUID

import redis.asyncio as aioredis
import structlog
from anthropic import AsyncAnthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.agents.discovery.schemas import (
    CandidateSchema,
    DailyDigestSchema,
    ScoredJobSchema,
)
from backend.agents.discovery.identity_profiler import IdentityProfiler
from backend.agents.discovery.archetype_generator import ArchetypeGenerator
from backend.agents.discovery.crawler_agent import CrawlerAgent
from backend.agents.discovery.relevance_scorer import RelevanceScorer
from backend.agents.discovery.digest_builder import DigestBuilder
from backend.models.discovery import Candidate as CandidateORM, CrawlRun

logger = structlog.get_logger(__name__)

_STATUS_CHANNEL = "agent.status.discovery"


class DiscoveryOrchestrator:
    """
    Coordinates the full Discovery Engine pipeline for a single candidate.

    Designed to run once per candidate per day via Celery cron,
    or on-demand via the API trigger endpoint.
    """

    def __init__(self, db: AsyncSession, redis_client: aioredis.Redis):
        """
        Initialize the DiscoveryOrchestrator.

        Args:
            db: Async SQLAlchemy session
            redis_client: Async Redis client for caching and pub/sub
        """
        self._db = db
        self._redis = redis_client
        self._claude = AsyncAnthropic(api_key=settings.anthropic_api_key)

        self._profiler = IdentityProfiler(redis_client, self._claude)
        self._archetype_gen = ArchetypeGenerator()
        self._scorer = RelevanceScorer(self._claude)
        self._digest_builder = DigestBuilder(redis_client, db)

    async def run(
        self,
        candidate_id: UUID,
        dry_run: bool = False,
    ) -> DailyDigestSchema:
        """
        Execute a full daily discovery run for a candidate.

        Args:
            candidate_id: UUID of the candidate to run for
            dry_run: If True, don't write to DB or publish events

        Returns:
            DailyDigestSchema with the full ranked digest
        """
        crawl_run = await self._start_run(candidate_id, dry_run)
        log = logger.bind(candidate_id=str(candidate_id), dry_run=dry_run)

        try:
            # 1. Load candidate
            candidate = await self._load_candidate(candidate_id)
            log.info("orchestrator.candidate_loaded", name=candidate.name)
            await self._publish_status(candidate_id, "CANDIDATE_LOADED")

            # 2. Build identity profile (cached 24h)
            profile = await self._profiler.build_profile(candidate)
            log.info(
                "orchestrator.profile_built",
                archetypes=len(profile.archetypes),
                level=profile.leadership_level,
            )
            await self._publish_status(candidate_id, "PROFILE_BUILT")

            # 3. Expand archetypes into search manifest
            excluded = {
                "titles": [],
                "companies": candidate.excluded_companies or [],
                "industries": candidate.excluded_industries or [],
            }
            manifest = self._archetype_gen.expand(profile, excluded)
            log.info(
                "orchestrator.manifest_built",
                target_titles=len(manifest.target_titles),
                keywords=len(manifest.keywords),
            )
            await self._publish_status(candidate_id, "MANIFEST_BUILT")

            # 4. Crawl (currently stubbed — Phase 1B)
            crawler = CrawlerAgent(candidate_id)
            raw_jobs = await crawler.run(manifest)
            log.info("orchestrator.crawl_complete", jobs_found=len(raw_jobs))
            await self._publish_status(candidate_id, "CRAWL_COMPLETE")

            # 5. Score with bounded concurrency
            semaphore = asyncio.Semaphore(settings.crawl_concurrency)

            async def score_with_semaphore(job):
                async with semaphore:
                    return job

            # Fan out scoring — respect the semaphore so we don't hammer Claude
            scored_jobs = await self._scorer.score_batch(
                raw_jobs,
                profile,
                candidate_id,
                min_score=settings.min_score,
            )
            log.info(
                "orchestrator.scoring_complete",
                passed=len(scored_jobs),
                filtered=len(raw_jobs) - len(scored_jobs),
            )
            await self._publish_status(candidate_id, "SCORING_COMPLETE")

            # 6. Build and publish digest
            if not dry_run:
                digest = await self._digest_builder.compile(
                    candidate_id=candidate_id,
                    scored_jobs=scored_jobs,
                    total_discovered=len(raw_jobs),
                )
            else:
                digest = self._build_dry_run_digest(
                    candidate_id, scored_jobs, len(raw_jobs)
                )

            await self._complete_run(
                crawl_run, len(raw_jobs), len(scored_jobs), dry_run
            )
            log.info(
                "orchestrator.run_complete",
                top_picks=len(digest.top_picks),
                hot_picks=len(digest.hot_picks),
            )
            await self._publish_status(candidate_id, "RUN_COMPLETE")
            return digest

        except Exception as e:
            log.error("orchestrator.run_failed", error=str(e))
            await self._publish_status(candidate_id, "RUN_FAILED")
            await self._fail_run(crawl_run, str(e), dry_run)
            raise

    async def _load_candidate(self, candidate_id: UUID) -> CandidateSchema:
        """Load candidate from PostgreSQL and convert to schema."""
        result = await self._db.execute(
            select(CandidateORM).where(CandidateORM.id == candidate_id)
        )
        orm = result.scalar_one_or_none()
        if not orm:
            raise ValueError(f"Candidate {candidate_id} not found")
        return CandidateSchema.model_validate(orm)

    async def _start_run(self, candidate_id: UUID, dry_run: bool) -> CrawlRun | None:
        """Create a CrawlRun record and return it (None in dry_run mode)."""
        if dry_run:
            return None
        run = CrawlRun(candidate_id=candidate_id, status="RUNNING")
        self._db.add(run)
        await self._db.commit()
        await self._db.refresh(run)
        return run

    async def _complete_run(
        self, run: CrawlRun | None, discovered: int, scored: int, dry_run: bool
    ) -> None:
        """Mark the CrawlRun as COMPLETED."""
        if dry_run or run is None:
            return
        run.status = "COMPLETED"
        run.completed_at = datetime.now(timezone.utc)
        run.jobs_discovered = discovered
        run.jobs_scored = scored
        await self._db.commit()

    async def _fail_run(
        self, run: CrawlRun | None, error: str, dry_run: bool
    ) -> None:
        """Mark the CrawlRun as FAILED with error log."""
        if dry_run or run is None:
            return
        run.status = "FAILED"
        run.completed_at = datetime.now(timezone.utc)
        run.error_log = error
        await self._db.commit()

    def _build_dry_run_digest(
        self,
        candidate_id: UUID,
        scored_jobs: list[ScoredJobSchema],
        total_discovered: int,
    ) -> DailyDigestSchema:
        """Build an in-memory digest without DB writes — for dry_run mode."""
        return DailyDigestSchema(
            candidate_id=candidate_id,
            run_date=date.today().isoformat(),
            total_jobs_discovered=total_discovered,
            total_jobs_scored=len(scored_jobs),
            top_picks=[],
            hot_picks=[],
            new_companies=[],
        )

    async def _publish_status(self, candidate_id: UUID, status: str) -> None:
        """Publish discovery pipeline status event to Redis pub/sub."""
        payload = json.dumps(
            {
                "event": "DISCOVERY_STATUS",
                "candidate_id": str(candidate_id),
                "status": status,
            }
        )
        await self._redis.publish(_STATUS_CHANNEL, payload)
        logger.info(
            "orchestrator.status_published",
            channel=_STATUS_CHANNEL,
            status=status,
        )
