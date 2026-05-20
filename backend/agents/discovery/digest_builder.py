# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Daily Digest Builder — assembles the ranked digest from scored jobs.

Flow:
  1. Receive scored jobs from RelevanceScorer
  2. Separate HOT picks (80+) from top picks
  3. Identify new companies not seen in previous digests
  4. Persist digest to PostgreSQL
  5. Publish DIGEST_READY event to Redis pub/sub
"""

import json
from datetime import date
from uuid import UUID

import redis.asyncio as aioredis
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.discovery.schemas import (
    ScoredJobSchema,
    DailyDigestSchema,
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
        db: AsyncSession,
    ):
        """
        Initialize the DigestBuilder.

        Args:
            redis_client: Async Redis client for caching and pub/sub
            db: Async SQLAlchemy session for persistence
        """
        self._redis = redis_client
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

        hot_picks = [s for s in scored_jobs if s.is_hot]
        top_picks = scored_jobs[:10]
        new_companies = await self._find_new_companies(candidate_id, scored_jobs)

        digest = DailyDigestSchema(
            candidate_id=candidate_id,
            run_date=today,
            total_jobs_discovered=total_discovered,
            total_jobs_scored=len(scored_jobs),
            top_picks=top_picks,
            hot_picks=hot_picks,
            new_companies=new_companies,
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

    async def _find_new_companies(
        self, candidate_id: UUID, scored_jobs: list[ScoredJobSchema]
    ) -> list[str]:
        """
        Return companies appearing in today's digest that weren't in recent digests.

        Uses a Redis set as a rolling 30-day seen-companies tracker.
        """
        key = _SEEN_COMPANIES_KEY.format(candidate_id=str(candidate_id))
        today_companies = list({s.company for s in scored_jobs})

        # Identify new ones
        seen_raw = await self._redis.smembers(key)
        seen = {c.decode() if isinstance(c, bytes) else c for c in seen_raw}
        new_companies = [c for c in today_companies if c not in seen]

        # Update the seen set
        if today_companies:
            await self._redis.sadd(key, *today_companies)
            await self._redis.expire(key, _SEEN_COMPANIES_TTL)

        return new_companies

    async def _persist(self, digest: DailyDigestSchema) -> None:
        """Persist the digest to PostgreSQL."""
        orm = DailyDigestORM(
            candidate_id=digest.candidate_id,
            run_date=date.fromisoformat(digest.run_date),
            total_jobs_discovered=digest.total_jobs_discovered,
            total_jobs_scored=digest.total_jobs_scored,
            top_picks=[p.model_dump(mode="json") for p in digest.top_picks],
            hot_picks=[p.model_dump(mode="json") for p in digest.hot_picks],
            new_companies=digest.new_companies,
        )
        self._db.add(orm)
        await self._db.commit()
        logger.info("digest_builder.persisted", candidate_id=str(digest.candidate_id))

    async def _publish_ready_event(
        self, candidate_id: UUID, digest: DailyDigestSchema
    ) -> None:
        """Publish DIGEST_READY event to Redis pub/sub for dashboard notification."""
        payload = json.dumps(
            {
                "event": "DIGEST_READY",
                "candidate_id": str(candidate_id),
                "run_date": digest.run_date,
                "total_scored": digest.total_jobs_scored,
                "hot_count": len(digest.hot_picks),
                "top_score": (
                    digest.top_picks[0].composite_score if digest.top_picks else 0
                ),
            }
        )
        await self._redis.publish(_DIGEST_READY_CHANNEL, payload)
        logger.info(
            "digest_builder.event_published",
            channel=_DIGEST_READY_CHANNEL,
            candidate_id=str(candidate_id),
        )
