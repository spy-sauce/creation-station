# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Scoring Synthetic Runner — iterates synthetic candidates × JD fixtures.

Executes the RelevanceScorer against synthetic candidates with cache-aware
instrumentation. Tracks cache hit/miss rates from Claude API responses.

The scorer module (RelevanceScorer) is FROZEN. To enforce the cache contract
(NUTRIENTS.md §I.5), this runner wraps Claude API calls with cache_control
headers by providing a wrapper client that intercepts and augments requests.

Contract: NUTRIENTS.md §I.2-I.5, HYPHA-SYNTHETICS-SCORING.md
Owner: synthetics-scoring-agent.runner
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import redis.asyncio as aioredis
import structlog
import yaml
from anthropic import AsyncAnthropic
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.discovery.identity_profiler import IdentityProfiler
from backend.agents.discovery.relevance_scorer import RelevanceScorer
from backend.agents.discovery.schemas import (
    CandidateSchema,
    DiscoveredJobSchema,
    IdentityProfileSchema,
    ScoredJobSchema,
)

logger = structlog.get_logger(__name__)


# ─── Cache Statistics ────────────────────────────────────────────────────────


@dataclass
class CacheMissEvent:
    """
    Records a cache miss event for the run report.

    Per NUTRIENTS.md §I.5, if cache_creation_input_tokens > 0 on subsequent
    runs, a cache_miss event is written to the report.
    """

    call_index: int
    cache_creation_tokens: int
    cache_read_tokens: int
    timestamp: str


@dataclass
class CacheStats:
    """Tracks cache hit/miss statistics for Claude API calls."""

    total_calls: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0

    # For cache contract verification (NUTRIENTS.md §I.5)
    is_subsequent_run: bool = False
    cache_miss_events: list[CacheMissEvent] = field(default_factory=list)

    @property
    def cache_hits(self) -> int:
        """Number of calls that hit the cache."""
        # A cache hit is when cache_read_input_tokens > 0
        return self._hit_count

    @property
    def cache_misses(self) -> int:
        """Number of calls that missed the cache."""
        return self.total_calls - self._hit_count

    @property
    def cache_hit_rate(self) -> float:
        """Cache hit rate as a ratio 0.0-1.0."""
        if self.total_calls == 0:
            return 0.0
        return self._hit_count / self.total_calls

    @property
    def cache_contract_violated(self) -> bool:
        """
        Check if cache contract was violated.

        Per NUTRIENTS.md §I.5, on subsequent runs:
            - cache_creation_input_tokens == 0 (MUST hit cache)
            - cache_read_input_tokens > 0

        Returns True if subsequent run had cache misses (creation tokens > 0).
        """
        return self.is_subsequent_run and len(self.cache_miss_events) > 0

    _hit_count: int = field(default=0, init=False)

    def record_call(
        self,
        cache_creation_input_tokens: int,
        cache_read_input_tokens: int,
    ) -> None:
        """
        Record a Claude API call's cache statistics.

        Per NUTRIENTS.md §I.5, on subsequent runs if cache_creation_input_tokens > 0,
        this constitutes a cache contract violation. We record it as a cache_miss event.
        """
        self.total_calls += 1
        self.cache_creation_tokens += cache_creation_input_tokens
        self.cache_read_tokens += cache_read_input_tokens
        if cache_read_input_tokens > 0:
            self._hit_count += 1

        # Cache contract verification for subsequent runs (NUTRIENTS.md §I.5)
        # On subsequent runs, cache_creation_input_tokens MUST be 0
        if self.is_subsequent_run and cache_creation_input_tokens > 0:
            cache_miss = CacheMissEvent(
                call_index=self.total_calls,
                cache_creation_tokens=cache_creation_input_tokens,
                cache_read_tokens=cache_read_input_tokens,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            self.cache_miss_events.append(cache_miss)
            logger.warning(
                "cache_contract.violation",
                call_index=self.total_calls,
                cache_creation_tokens=cache_creation_input_tokens,
                cache_read_tokens=cache_read_input_tokens,
                message="Subsequent run should have cache_creation_input_tokens == 0",
            )


# ─── JD Fixture Loading ──────────────────────────────────────────────────────


class JDFixture(BaseModel):
    """A JD fixture loaded from synthetics/fixtures/jobs/."""

    filename: str
    target_candidate: str
    expected_hot: bool
    expected_score_band: str  # low | mid | high
    source: str
    title: str
    company: str
    location: Optional[str] = None
    description: str
    url: str = ""


def load_jd_fixtures(fixtures_dir: Path) -> list[JDFixture]:
    """
    Load all JD fixtures from the jobs directory.

    Each fixture is a markdown file with YAML frontmatter.

    Args:
        fixtures_dir: Path to synthetics/fixtures/jobs/

    Returns:
        List of JDFixture objects
    """
    fixtures: list[JDFixture] = []
    jobs_dir = fixtures_dir / "jobs"

    if not jobs_dir.exists():
        logger.warning("jd_fixtures.dir_not_found", path=str(jobs_dir))
        return fixtures

    for md_file in jobs_dir.glob("*.md"):
        try:
            fixture = _parse_jd_fixture(md_file)
            fixtures.append(fixture)
            logger.debug(
                "jd_fixtures.loaded",
                filename=md_file.name,
                target=fixture.target_candidate,
            )
        except Exception as e:
            logger.error(
                "jd_fixtures.parse_error",
                filename=md_file.name,
                error=str(e),
            )

    logger.info("jd_fixtures.loaded_all", count=len(fixtures))
    return fixtures


def _parse_jd_fixture(path: Path) -> JDFixture:
    """Parse a single JD fixture markdown file with YAML frontmatter."""
    content = path.read_text()

    # Split frontmatter from body
    if not content.startswith("---"):
        raise ValueError(f"No YAML frontmatter in {path.name}")

    parts = content.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"Invalid frontmatter format in {path.name}")

    frontmatter = yaml.safe_load(parts[1])
    body = parts[2].strip()

    return JDFixture(
        filename=path.name,
        target_candidate=frontmatter["target_candidate"],
        expected_hot=frontmatter["expected_hot"],
        expected_score_band=frontmatter["expected_score_band"],
        source=frontmatter.get("source", "greenhouse"),
        title=frontmatter.get("title", "Unknown Title"),
        company=frontmatter.get("company", "Unknown Company"),
        location=frontmatter.get("location"),
        description=body,
        url=frontmatter.get("url", f"https://example.com/jobs/{path.stem}"),
    )


# ─── Synthetic Candidate Loading ─────────────────────────────────────────────


async def load_synthetic_candidates(
    session: AsyncSession,
) -> list[CandidateSchema]:
    """
    Load synthetic candidates from the database.

    Synthetic candidates are identified by UUIDv5 markers matching
    the pattern: id::text LIKE '00000000-%'

    Contract: NUTRIENTS.md §I.1

    Args:
        session: Async SQLAlchemy session

    Returns:
        List of CandidateSchema for synthetic candidates
    """
    # Query candidates with synthetic UUID pattern
    result = await session.execute(
        text("""
            SELECT
                id, name, email, resume_text, linkedin_url, github_url,
                personal_context, target_locations, remote_preference,
                min_compensation, excluded_companies, excluded_industries,
                created_at, updated_at
            FROM candidates
            WHERE id::text LIKE '00000000-%'
            ORDER BY name
        """)
    )

    candidates: list[CandidateSchema] = []
    for row in result.fetchall():
        candidates.append(
            CandidateSchema(
                id=row.id,
                name=row.name,
                email=row.email,
                resume_text=row.resume_text or "",
                linkedin_url=row.linkedin_url,
                github_url=row.github_url,
                personal_context=row.personal_context,
                target_locations=list(row.target_locations or []),
                remote_preference=row.remote_preference or "flexible",
                min_compensation=row.min_compensation,
                excluded_companies=list(row.excluded_companies or []),
                excluded_industries=list(row.excluded_industries or []),
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
        )

    logger.info(
        "synthetic_candidates.loaded",
        count=len(candidates),
        ids=[str(c.id) for c in candidates],
    )
    return candidates


# ─── Cache-Aware Claude Wrapper ──────────────────────────────────────────────


class CacheAwareAnthropic:
    """
    Wrapper around AsyncAnthropic that enforces cache_control headers.

    The RelevanceScorer is FROZEN and doesn't set cache_control.
    This wrapper intercepts message creation and adds the required
    cache_control headers per NUTRIENTS.md §I.5.
    """

    def __init__(
        self,
        client: AsyncAnthropic,
        cache_stats: CacheStats,
        candidate_identity: str,
    ):
        """
        Initialize the cache-aware wrapper.

        Args:
            client: The underlying AsyncAnthropic client
            cache_stats: CacheStats object to record metrics
            candidate_identity: Candidate identity text to cache
        """
        self._client = client
        self._cache_stats = cache_stats
        self._candidate_identity = candidate_identity
        self.messages = _CacheAwareMessages(self)


class _CacheAwareMessages:
    """Wraps the messages API to add cache_control."""

    def __init__(self, wrapper: CacheAwareAnthropic):
        self._wrapper = wrapper

    async def create(self, **kwargs) -> object:
        """
        Create a message with cache_control headers.

        Transforms the messages to include cache_control on system prompt
        and candidate identity per NUTRIENTS.md §I.5.
        """
        # Extract original messages
        messages = kwargs.get("messages", [])

        # Transform to use cache_control
        transformed_messages = []
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    # Split into cacheable parts
                    transformed_messages.append(
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": self._wrapper._candidate_identity,
                                    "cache_control": {"type": "ephemeral"},
                                },
                                {
                                    "type": "text",
                                    "text": content,
                                },
                            ],
                        }
                    )
                else:
                    # Already structured, just pass through
                    transformed_messages.append(msg)
            else:
                transformed_messages.append(msg)

        # Add system prompt with cache_control
        system_content = [
            {
                "type": "text",
                "text": (
                    "You are a talent agent scoring jobs against candidate profiles. "
                    "Return structured JSON responses."
                ),
                "cache_control": {"type": "ephemeral"},
            }
        ]

        # Make the request
        kwargs["messages"] = transformed_messages
        kwargs["system"] = system_content

        response = await self._wrapper._client.messages.create(**kwargs)

        # Record cache statistics
        usage = response.usage
        cache_creation = getattr(usage, "cache_creation_input_tokens", 0) or 0
        cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0

        self._wrapper._cache_stats.record_call(cache_creation, cache_read)

        logger.debug(
            "cache_aware.request_complete",
            cache_creation_tokens=cache_creation,
            cache_read_tokens=cache_read,
            total_calls=self._wrapper._cache_stats.total_calls,
        )

        return response


# ─── Scored Result ───────────────────────────────────────────────────────────


class ScoredResult(BaseModel):
    """Result of scoring a single candidate × JD pair."""

    candidate_id: str
    candidate_name: str
    jd_filename: str
    scored_job: Optional[ScoredJobSchema] = None
    expected_hot: bool
    expected_score_band: str
    actual_hot: bool = False
    actual_score: int = 0
    error: Optional[str] = None


class CandidateScoringResult(BaseModel):
    """All scoring results for a single candidate."""

    candidate_id: str
    candidate_name: str
    profile: Optional[IdentityProfileSchema] = None
    scored_results: list[ScoredResult] = Field(default_factory=list)
    cache_stats: dict = Field(default_factory=dict)
    error: Optional[str] = None


# ─── Scoring Runner ──────────────────────────────────────────────────────────


class ScoringSyntheticRunner:
    """
    Iterates synthetic candidates × JD fixtures for drift detection.

    This runner:
    1. Loads synthetic candidates from the database
    2. Loads JD fixtures from synthetics/fixtures/jobs/
    3. For each candidate × JD pair, scores via RelevanceScorer
    4. Tracks cache hit/miss from Claude API responses
    5. Verifies cache contract on subsequent runs (NUTRIENTS.md §I.5)
    6. Returns structured results for fingerprinting

    Contract: NUTRIENTS.md §I.2-I.5, HYPHA-SYNTHETICS-SCORING.md
    """

    def __init__(
        self,
        session: AsyncSession,
        redis_client: aioredis.Redis,
        anthropic_client: AsyncAnthropic,
        fixtures_dir: Optional[Path] = None,
        is_subsequent_run: bool = False,
    ):
        """
        Initialize the ScoringSyntheticRunner.

        Args:
            session: Async SQLAlchemy session for database access
            redis_client: Async Redis client for caching
            anthropic_client: Async Anthropic client for Claude API
            fixtures_dir: Path to synthetics/fixtures/ (default: auto-detect)
            is_subsequent_run: Whether this is a subsequent run (for cache verification)
                Per NUTRIENTS.md §I.5, subsequent runs MUST have
                cache_creation_input_tokens == 0 (hit cache)
        """
        self._session = session
        self._redis = redis_client
        self._anthropic = anthropic_client
        self._is_subsequent_run = is_subsequent_run

        # Auto-detect fixtures directory if not provided
        if fixtures_dir is None:
            self._fixtures_dir = Path(__file__).parent.parent.parent / "synthetics" / "fixtures"
        else:
            self._fixtures_dir = fixtures_dir

        self._run_id = str(uuid.uuid4())

    async def run_suite(self) -> dict:
        """
        Execute the full scoring suite.

        Iterates all synthetic candidates × applicable JD fixtures,
        scoring each pair and collecting results.

        Returns:
            dict with:
                - run_id: UUID of this run
                - started_at: ISO timestamp
                - completed_at: ISO timestamp
                - candidates: list of CandidateScoringResult
                - overall_cache_stats: aggregated cache statistics
        """
        started_at = datetime.now(timezone.utc)

        logger.info(
            "scoring_runner.suite_start",
            run_id=self._run_id,
            fixtures_dir=str(self._fixtures_dir),
        )

        # Load synthetic candidates
        candidates = await load_synthetic_candidates(self._session)
        if not candidates:
            logger.warning("scoring_runner.no_candidates")
            return {
                "run_id": self._run_id,
                "started_at": started_at.isoformat(),
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "candidates": [],
                "overall_cache_stats": {"total_calls": 0, "cache_hit_rate": 0.0},
            }

        # Load JD fixtures
        jd_fixtures = load_jd_fixtures(self._fixtures_dir)
        if not jd_fixtures:
            logger.warning("scoring_runner.no_fixtures")
            return {
                "run_id": self._run_id,
                "started_at": started_at.isoformat(),
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "candidates": [],
                "overall_cache_stats": {"total_calls": 0, "cache_hit_rate": 0.0},
            }

        # Build mapping of candidate slug to JD fixtures
        candidate_slug_map = self._build_candidate_slug_map(candidates)

        # Process each candidate
        all_results: list[CandidateScoringResult] = []
        overall_cache_stats = CacheStats(is_subsequent_run=self._is_subsequent_run)

        for candidate in candidates:
            result = await self._score_candidate(
                candidate,
                jd_fixtures,
                candidate_slug_map,
                overall_cache_stats,
            )
            all_results.append(result)

        completed_at = datetime.now(timezone.utc)

        # Log cache contract verification result (NUTRIENTS.md §I.5)
        if overall_cache_stats.cache_contract_violated:
            logger.warning(
                "scoring_runner.cache_contract_violated",
                run_id=self._run_id,
                is_subsequent_run=self._is_subsequent_run,
                cache_miss_count=len(overall_cache_stats.cache_miss_events),
                message="Cache contract violation: cache_creation_input_tokens > 0 on subsequent run",
            )

        logger.info(
            "scoring_runner.suite_complete",
            run_id=self._run_id,
            candidates_processed=len(all_results),
            total_claude_calls=overall_cache_stats.total_calls,
            cache_hit_rate=round(overall_cache_stats.cache_hit_rate, 4),
            duration_seconds=(completed_at - started_at).total_seconds(),
            is_subsequent_run=self._is_subsequent_run,
            cache_contract_violated=overall_cache_stats.cache_contract_violated,
        )

        # Build cache miss events for report (NUTRIENTS.md §I.5)
        cache_miss_events_serialized = [
            {
                "call_index": event.call_index,
                "cache_creation_tokens": event.cache_creation_tokens,
                "cache_read_tokens": event.cache_read_tokens,
                "timestamp": event.timestamp,
            }
            for event in overall_cache_stats.cache_miss_events
        ]

        return {
            "run_id": self._run_id,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "candidates": [r.model_dump() for r in all_results],
            "overall_cache_stats": {
                "total_calls": overall_cache_stats.total_calls,
                "cache_hits": overall_cache_stats.cache_hits,
                "cache_misses": overall_cache_stats.cache_misses,
                "cache_hit_rate": round(overall_cache_stats.cache_hit_rate, 4),
                "cache_creation_tokens": overall_cache_stats.cache_creation_tokens,
                "cache_read_tokens": overall_cache_stats.cache_read_tokens,
            },
            # Cache contract verification (NUTRIENTS.md §I.5)
            "cache_verification": {
                "is_subsequent_run": self._is_subsequent_run,
                "cache_contract_violated": overall_cache_stats.cache_contract_violated,
                "cache_miss_events": cache_miss_events_serialized,
            },
        }

    def _build_candidate_slug_map(
        self,
        candidates: list[CandidateSchema],
    ) -> dict[str, CandidateSchema]:
        """
        Build a mapping of synthetic slugs to candidates.

        Derives the slug from the candidate's email prefix:
            jordan.chen.synthetic@... → synthetic-jr-engineer (from name pattern)
        """
        slug_map: dict[str, CandidateSchema] = {}

        for candidate in candidates:
            # Extract slug from email pattern or name
            email = candidate.email.lower()

            if "jordan" in email or "chen" in email:
                slug_map["synthetic-jr-engineer"] = candidate
            elif "priya" in email or "ramanathan" in email:
                slug_map["synthetic-senior-ml"] = candidate
            elif "marcus" in email or "thompson" in email:
                slug_map["synthetic-mid-product"] = candidate
            else:
                # Fallback: use email prefix
                prefix = email.split("@")[0].replace(".", "-")
                slug_map[prefix] = candidate

        logger.debug(
            "candidate_slug_map.built",
            slugs=list(slug_map.keys()),
        )
        return slug_map

    async def _score_candidate(
        self,
        candidate: CandidateSchema,
        jd_fixtures: list[JDFixture],
        slug_map: dict[str, CandidateSchema],
        overall_cache_stats: CacheStats,
    ) -> CandidateScoringResult:
        """
        Score all applicable JD fixtures for a single candidate.

        Args:
            candidate: The synthetic candidate
            jd_fixtures: All JD fixtures
            slug_map: Mapping of slugs to candidates
            overall_cache_stats: Aggregated cache stats

        Returns:
            CandidateScoringResult with all scoring results
        """
        # Determine which slug this candidate maps to
        candidate_slug = None
        for slug, cand in slug_map.items():
            if cand.id == candidate.id:
                candidate_slug = slug
                break

        if not candidate_slug:
            logger.warning(
                "scoring_runner.unknown_slug",
                candidate_id=str(candidate.id),
                candidate_name=candidate.name,
            )
            return CandidateScoringResult(
                candidate_id=str(candidate.id),
                candidate_name=candidate.name,
                error="Could not determine candidate slug",
            )

        # Filter JD fixtures for this candidate
        applicable_jds = [
            jd for jd in jd_fixtures if jd.target_candidate == candidate_slug
        ]

        logger.info(
            "scoring_runner.candidate_start",
            candidate_id=str(candidate.id),
            candidate_name=candidate.name,
            slug=candidate_slug,
            applicable_jds=len(applicable_jds),
        )

        # Build identity profile first
        candidate_identity = self._build_candidate_identity_text(candidate)
        cache_stats = CacheStats(is_subsequent_run=self._is_subsequent_run)

        # Create cache-aware wrapper for this candidate
        cache_client = CacheAwareAnthropic(
            self._anthropic,
            cache_stats,
            candidate_identity,
        )

        # Build profile via IdentityProfiler
        profiler = IdentityProfiler(self._redis, cache_client)
        try:
            profile = await profiler.build_profile(candidate)
        except Exception as e:
            logger.error(
                "scoring_runner.profile_error",
                candidate_id=str(candidate.id),
                error=str(e),
            )
            return CandidateScoringResult(
                candidate_id=str(candidate.id),
                candidate_name=candidate.name,
                error=f"Failed to build profile: {e}",
            )

        # Create scorer with cache-aware client
        scorer = RelevanceScorer(cache_client)

        # Score each applicable JD
        scored_results: list[ScoredResult] = []

        for jd in applicable_jds:
            result = await self._score_single_jd(
                candidate,
                profile,
                jd,
                scorer,
            )
            scored_results.append(result)

        # Aggregate cache stats into overall
        overall_cache_stats.total_calls += cache_stats.total_calls
        overall_cache_stats.cache_creation_tokens += cache_stats.cache_creation_tokens
        overall_cache_stats.cache_read_tokens += cache_stats.cache_read_tokens
        overall_cache_stats._hit_count += cache_stats._hit_count
        # Aggregate cache miss events for contract verification (NUTRIENTS.md §I.5)
        overall_cache_stats.cache_miss_events.extend(cache_stats.cache_miss_events)

        # Log cache contract violation at candidate level if detected
        if cache_stats.cache_contract_violated:
            logger.warning(
                "scoring_runner.candidate_cache_violation",
                candidate_id=str(candidate.id),
                cache_miss_count=len(cache_stats.cache_miss_events),
                is_subsequent_run=self._is_subsequent_run,
            )

        logger.info(
            "scoring_runner.candidate_complete",
            candidate_id=str(candidate.id),
            scored_count=len(scored_results),
            cache_calls=cache_stats.total_calls,
            cache_hit_rate=round(cache_stats.cache_hit_rate, 4),
            cache_contract_violated=cache_stats.cache_contract_violated,
        )

        return CandidateScoringResult(
            candidate_id=str(candidate.id),
            candidate_name=candidate.name,
            profile=profile,
            scored_results=scored_results,
            cache_stats={
                "total_calls": cache_stats.total_calls,
                "cache_hits": cache_stats.cache_hits,
                "cache_misses": cache_stats.cache_misses,
                "cache_hit_rate": round(cache_stats.cache_hit_rate, 4),
                # Cache verification stats (NUTRIENTS.md §I.5)
                "cache_contract_violated": cache_stats.cache_contract_violated,
                "cache_miss_event_count": len(cache_stats.cache_miss_events),
            },
        )

    def _build_candidate_identity_text(self, candidate: CandidateSchema) -> str:
        """
        Build the candidate identity text for caching.

        This text is prepended to all Claude calls for this candidate
        and marked with cache_control.
        """
        return f"""# CANDIDATE IDENTITY

Name: {candidate.name}
Location: {", ".join(candidate.target_locations) if candidate.target_locations else "Flexible"}
Remote Preference: {candidate.remote_preference}
Min Compensation: {candidate.min_compensation or "Not specified"}
Excluded Companies: {", ".join(candidate.excluded_companies) if candidate.excluded_companies else "None"}
Excluded Industries: {", ".join(candidate.excluded_industries) if candidate.excluded_industries else "None"}

## Resume
{candidate.resume_text}

## Personal Context
{candidate.personal_context or "Not provided"}
"""

    async def _score_single_jd(
        self,
        candidate: CandidateSchema,
        profile: IdentityProfileSchema,
        jd: JDFixture,
        scorer: RelevanceScorer,
    ) -> ScoredResult:
        """
        Score a single candidate × JD pair.

        Args:
            candidate: The synthetic candidate
            profile: The candidate's identity profile
            jd: The JD fixture
            scorer: RelevanceScorer instance

        Returns:
            ScoredResult with scoring details
        """
        logger.debug(
            "scoring_runner.scoring_jd",
            candidate_id=str(candidate.id),
            jd_filename=jd.filename,
        )

        # Convert JD fixture to DiscoveredJobSchema
        discovered_job = DiscoveredJobSchema(
            id=uuid.uuid5(uuid.NAMESPACE_DNS, f"synthetic-jd-{jd.filename}"),
            source=jd.source,
            source_id=f"synthetic-{jd.filename}",
            title=jd.title,
            company=jd.company,
            location=jd.location,
            description=jd.description,
            url=jd.url,
            posted_at=None,
            salary_min=None,
            salary_max=None,
            remote=False,
            crawled_at=datetime.now(timezone.utc),
        )

        try:
            scored_job = await scorer.score_job(
                discovered_job,
                profile,
                candidate.id,
            )

            return ScoredResult(
                candidate_id=str(candidate.id),
                candidate_name=candidate.name,
                jd_filename=jd.filename,
                scored_job=scored_job,
                expected_hot=jd.expected_hot,
                expected_score_band=jd.expected_score_band,
                actual_hot=scored_job.is_hot,
                actual_score=scored_job.composite_score,
            )

        except Exception as e:
            logger.error(
                "scoring_runner.score_error",
                candidate_id=str(candidate.id),
                jd_filename=jd.filename,
                error=str(e),
            )
            return ScoredResult(
                candidate_id=str(candidate.id),
                candidate_name=candidate.name,
                jd_filename=jd.filename,
                expected_hot=jd.expected_hot,
                expected_score_band=jd.expected_score_band,
                error=str(e),
            )
