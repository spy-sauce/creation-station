# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Daily Digest Builder — assembles the ranked digest from scored jobs.

Flow:
  1. Receive scored jobs from RelevanceScorer
  2. Separate HOT picks (80+) from top picks
  3. Identify new companies not seen in previous digests
  4. Generate Claude narrative summary of today's landscape
  5. Persist digest to PostgreSQL
  6. Publish DIGEST_READY event to Redis pub/sub
"""

import json
from datetime import date, datetime
from uuid import UUID

import redis.asyncio as aioredis
import structlog
from anthropic import AsyncAnthropic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.agents.discovery.schemas import (
    ScoredJobSchema,
    DailyDigestSchema,
    DigestJobPreview,
)
from backend.models.discovery import DailyDigest as DailyDigestORM

logger = structlog.get_logger(__name__)

_DIGEST_READY_CHANNEL = "agent.status.digest"
_SEEN_COMPANIES_KEY = "seen_companies:{candidate_id}"
_SEEN_COMPANIES_TTL = 86_400 * 30  # 30 days


class DigestBuilder:
    """
    Compiles scored jobs into a daily digest, persists it, and fires the DIGEST_READY event.
    """

    def __init__(
        self,
        redis_client: aioredis.Redis,
        anthropic_client: AsyncAnthropic,
        db: AsyncSession,
    ):
        self._redis = redis_client
        self._claude = anthropic_client
        self._db = db

    async def compile(
        self,
        candidate_id: UUID,
        scored_jobs: list[ScoredJobSchema],
        total_discovered: int,
    ) -> DailyDigestSchema:
        """
        Build the full daily digest from scored jobs.

        Args:
            candidate_id: Candidate this digest belongs to
            scored_jobs: All jobs that passed MIN_SCORE, sorted descending by composite
            total_discovered: Raw count before scoring/filtering

        Returns:
            DailyDigestSchema ready for the Review Dashboard
        """
        today = date.today().isoformat()
        logger.info(
            "digest_builder.compiling",
            candidate_id=str(candidate_id),
            scored_jobs=len(scored_jobs),
            run_date=today,
        )

        hot_picks = [self._to_preview(s) for s in scored_jobs if s.is_hot]
        top_picks = [self._to_preview(s) for s in scored_jobs[:10]]
        new_companies = await self._find_new_companies(candidate_id, scored_jobs)
        summary = await self._generate_summary(scored_jobs, new_companies, today)

        digest = DailyDigestSchema(
            candidate_id=candidate_id,
            run_date=today,
            total_discovered=total_discovered,
            total_scored=len(scored_jobs),
            top_picks=top_picks,
            hot_picks=hot_picks,
            new_companies=new_companies,
            digest_summary=summary,
        )

        await self._persist(digest)
        await self._publish_ready_event(candidate_id, digest)

        logger.info(
            "digest_builder.complete",
            candidate_id=str(candidate_id),
            top_picks=len(top_picks),
            hot_picks=len(hot_picks),
            new_companies=len(new_companies),
        )
        return digest

    def _to_preview(self, scored: ScoredJobSchema) -> DigestJobPreview:
        """Convert a ScoredJobSchema to a lightweight DigestJobPreview."""
        return DigestJobPreview(
            job_id=scored.job.id or UUID(int=0),
            title=scored.job.title,
            company=scored.job.company,
            location=scored.job.location,
            url=scored.job.url,
            composite_score=scored.composite_score,
            is_hot=scored.is_hot,
            reasoning=scored.reasoning,
        )

    async def _find_new_companies(
        self, candidate_id: UUID, scored_jobs: list[ScoredJobSchema]
    ) -> list[str]:
        """
        Return companies appearing in today's digest that weren't in recent digests.

        Uses a Redis set as a rolling 30-day seen-companies tracker.
        """
        key = _SEEN_COMPANIES_KEY.format(candidate_id=str(candidate_id))
        today_companies = list({s.job.company for s in scored_jobs})

        # Identify new ones
        seen_raw = await self._redis.smembers(key)
        seen = {c.decode() if isinstance(c, bytes) else c for c in seen_raw}
        new_companies = [c for c in today_companies if c not in seen]

        # Update the seen set
        if today_companies:
            await self._redis.sadd(key, *today_companies)
            await self._redis.expire(key, _SEEN_COMPANIES_TTL)

        return new_companies

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _generate_summary(
        self,
        scored_jobs: list[ScoredJobSchema],
        new_companies: list[str],
        run_date: str,
    ) -> str:
        """Generate a 3-sentence narrative summary of today's digest via Claude."""
        if not scored_jobs:
            return "No jobs met the scoring threshold today. The engine ran successfully — consider lowering MIN_SCORE or expanding the archetype manifest. Check back tomorrow."

        top_companies = [s.job.company for s in scored_jobs[:5]]
        hot_count = sum(1 for s in scored_jobs if s.is_hot)
        avg_score = int(sum(s.composite_score for s in scored_jobs) / len(scored_jobs))

        prompt = f"""Write a 3-sentence digest summary for a daily job discovery report. Be specific, direct, and useful. No filler.

Date: {run_date}
Total jobs passing threshold: {len(scored_jobs)}
HOT picks (80+): {hot_count}
Average composite score: {avg_score}/100
Top companies appearing: {", ".join(top_companies)}
New companies not seen before: {", ".join(new_companies[:5]) if new_companies else "none"}
Top role: {scored_jobs[0].job.title} at {scored_jobs[0].job.company} (score: {scored_jobs[0].composite_score})

Write exactly 3 sentences. Focus on: (1) what the landscape looks like today, (2) the standout opportunity, (3) one specific action to take. Return only the 3 sentences."""

        response = await self._claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()

    async def _persist(self, digest: DailyDigestSchema) -> None:
        """Persist the digest to PostgreSQL."""
        orm = DailyDigestORM(
            candidate_id=digest.candidate_id,
            run_date=date.fromisoformat(digest.run_date),
            total_discovered=digest.total_discovered,
            total_scored=digest.total_scored,
            top_picks=[p.model_dump(mode="json") for p in digest.top_picks],
            hot_picks=[p.model_dump(mode="json") for p in digest.hot_picks],
            new_companies=digest.new_companies,
            digest_summary=digest.digest_summary,
        )
        self._db.add(orm)
        await self._db.commit()
        logger.info("digest_builder.persisted", candidate_id=str(digest.candidate_id))

    async def _publish_ready_event(self, candidate_id: UUID, digest: DailyDigestSchema) -> None:
        """Publish DIGEST_READY event to Redis pub/sub for dashboard notification."""
        payload = json.dumps({
            "event": "DIGEST_READY",
            "candidate_id": str(candidate_id),
            "run_date": digest.run_date,
            "total_scored": digest.total_scored,
            "hot_count": len(digest.hot_picks),
            "top_score": digest.top_picks[0].composite_score if digest.top_picks else 0,
        })
        await self._redis.publish(_DIGEST_READY_CHANNEL, payload)
        logger.info(
            "digest_builder.event_published",
            channel=_DIGEST_READY_CHANNEL,
            candidate_id=str(candidate_id),
        )
