# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Tests for the daily_discovery_task Celery task.

Scope: tests/scheduler/test_daily_task.py
Contract: HYPHA-TESTS.md

Test requirements:
  - Mock DiscoveryOrchestrator to avoid real Claude API calls
  - Verify crawl_runs row creation per candidate
  - Verify idempotent re-fire deduplication by task_id
  - Verify retry failure writes to crawl_runs.error_log
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import fakeredis.aioredis
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.database import Base
from backend.models.discovery import Candidate, CrawlRun, RemotePreference


# ─── Test Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def candidate_id() -> uuid.UUID:
    """Generate a consistent UUID for the test candidate."""
    return uuid.uuid4()


@pytest.fixture
def expected_task_id(candidate_id: uuid.UUID) -> str:
    """Compute the expected idempotent task ID for today."""
    run_date = date.today().isoformat()
    return f"discovery-{candidate_id}-{run_date}"


@pytest_asyncio.fixture
async def async_engine():
    """Create an in-memory SQLite async engine for testing."""
    # Use aiosqlite for async support
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create an async session for database operations."""
    session_factory = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def fake_redis():
    """Create a fakeredis async client for testing."""
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def test_candidate(
    async_session: AsyncSession, candidate_id: uuid.UUID
) -> Candidate:
    """Create a test candidate in the database."""
    candidate = Candidate(
        id=candidate_id,
        name="Test Candidate",
        email="test@example.com",
        resume_text="Test resume text for unit tests.",
        remote_preference=RemotePreference.FLEXIBLE,
        target_locations=[],
        excluded_companies=[],
        excluded_industries=[],
    )
    async_session.add(candidate)
    await async_session.commit()
    await async_session.refresh(candidate)
    return candidate


# ─── Test: Crawl Run Creation ───────────────────────────────────────────────────


class TestDailyDiscoveryTaskCrawlRunCreation:
    """Tests for crawl_runs row creation during task execution."""

    @pytest.mark.asyncio
    async def test_orchestrator_creates_crawl_run(
        self,
        async_session: AsyncSession,
        test_candidate: Candidate,
        fake_redis,
    ):
        """Verify that DiscoveryOrchestrator.run creates a crawl_runs row."""
        from backend.agents.discovery.orchestrator import DiscoveryOrchestrator

        # Mock the sub-agents to avoid real Claude calls
        with (
            patch.object(
                DiscoveryOrchestrator,
                "_DiscoveryOrchestrator__init__",
                return_value=None,
            ),
        ):
            # Create orchestrator with mocked dependencies
            orchestrator = DiscoveryOrchestrator.__new__(DiscoveryOrchestrator)
            orchestrator._db = async_session
            orchestrator._redis = fake_redis

            # Mock the private methods that would call Claude
            orchestrator._profiler = MagicMock()
            orchestrator._profiler.build_profile = AsyncMock(
                return_value=MagicMock(
                    archetypes=["software-engineer"],
                    leadership_level="IC",
                    technical_skills=["python"],
                    soft_skills=[],
                    industry_experience=[],
                    notable_achievements=[],
                    career_trajectory="",
                    ideal_role_description="",
                    signals={},
                )
            )

            orchestrator._archetype_gen = MagicMock()
            orchestrator._archetype_gen.expand = MagicMock(
                return_value=MagicMock(
                    target_titles=["Software Engineer"],
                    keywords=["python", "fastapi"],
                    excluded_titles=[],
                    excluded_companies=[],
                    excluded_industries=[],
                    location_filters=[],
                    remote_preference="flexible",
                    min_compensation=None,
                )
            )

            orchestrator._scorer = MagicMock()
            orchestrator._scorer.score_batch = AsyncMock(return_value=[])

            orchestrator._digest_builder = MagicMock()
            orchestrator._digest_builder.compile = AsyncMock(
                return_value=MagicMock(
                    candidate_id=test_candidate.id,
                    run_date=date.today().isoformat(),
                    total_jobs_discovered=0,
                    total_jobs_scored=0,
                    top_picks=[],
                    hot_picks=[],
                    new_companies=[],
                )
            )

            # Patch the CrawlerAgent to return empty jobs
            with patch(
                "backend.agents.discovery.orchestrator.CrawlerAgent"
            ) as MockCrawler:
                MockCrawler.return_value.run = AsyncMock(return_value=[])

                # Execute the orchestrator
                await orchestrator.run(test_candidate.id, dry_run=False)

        # Verify crawl_run was created
        result = await async_session.execute(
            select(CrawlRun).where(CrawlRun.candidate_id == test_candidate.id)
        )
        crawl_runs = result.scalars().all()

        assert len(crawl_runs) == 1, "Expected exactly one crawl_run row"
        crawl_run = crawl_runs[0]
        assert crawl_run.candidate_id == test_candidate.id
        assert crawl_run.status.value == "COMPLETED"
        assert crawl_run.error_log is None


# ─── Test: Task ID Idempotency ──────────────────────────────────────────────────


class TestDailyTaskIdempotency:
    """Tests for idempotent task_id generation and deduplication."""

    def test_compute_task_id_format(self, candidate_id: uuid.UUID):
        """Verify task_id follows the discovery-{id}-{YYYY-MM-DD} format."""
        from backend.scheduler.tasks import _compute_task_id

        task_id = _compute_task_id(candidate_id)
        run_date = date.today().isoformat()

        assert task_id == f"discovery-{candidate_id}-{run_date}"

    def test_compute_task_id_consistent(self, candidate_id: uuid.UUID):
        """Verify task_id is consistent across multiple calls on the same day."""
        from backend.scheduler.tasks import _compute_task_id

        task_id_1 = _compute_task_id(candidate_id)
        task_id_2 = _compute_task_id(candidate_id)
        task_id_3 = _compute_task_id(str(candidate_id))

        assert task_id_1 == task_id_2, "Same UUID should produce same task_id"
        assert task_id_1 == task_id_3, "String UUID should produce same task_id"

    def test_compute_task_id_different_candidates(self):
        """Verify different candidates produce different task_ids."""
        from backend.scheduler.tasks import _compute_task_id

        candidate_1 = uuid.uuid4()
        candidate_2 = uuid.uuid4()

        task_id_1 = _compute_task_id(candidate_1)
        task_id_2 = _compute_task_id(candidate_2)

        assert task_id_1 != task_id_2, "Different candidates need different task_ids"


# ─── Test: Celery Task Retry Behavior ───────────────────────────────────────────


class TestDailyTaskRetryBehavior:
    """Tests for the Celery task retry policy and failure handling."""

    def test_retry_countdowns_configured(self):
        """Verify retry countdown values match the spec: 60s, 300s, 900s."""
        from backend.scheduler.tasks import RETRY_COUNTDOWNS

        assert RETRY_COUNTDOWNS == [
            60,
            300,
            900,
        ], "Retry countdowns should be 60s, 300s, 900s"

    @pytest.mark.asyncio
    async def test_mark_crawl_run_failed_writes_error_log(
        self,
        async_session: AsyncSession,
        test_candidate: Candidate,
    ):
        """Verify _mark_crawl_run_failed writes traceback to crawl_runs.error_log."""
        # Create a RUNNING crawl run
        crawl_run = CrawlRun(
            candidate_id=test_candidate.id,
            status="RUNNING",
            started_at=datetime.now(timezone.utc),
        )
        async_session.add(crawl_run)
        await async_session.commit()
        await async_session.refresh(crawl_run)

        # Mock settings to use our in-memory database
        error_message = "Test error: Claude API rate limit exceeded"

        # Patch the task module's database creation to use our test session
        with patch(
            "backend.scheduler.tasks.create_async_engine"
        ) as mock_engine_factory:
            # Create a mock engine that returns our session factory
            mock_engine = MagicMock()
            mock_engine.dispose = AsyncMock()
            mock_engine_factory.return_value = mock_engine

            with patch(
                "backend.scheduler.tasks.async_sessionmaker"
            ) as mock_session_factory:
                # Create a context manager that yields our test session
                mock_factory = MagicMock()

                async def session_context():
                    yield async_session

                mock_factory.return_value.__aenter__ = AsyncMock(
                    return_value=async_session
                )
                mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)
                mock_session_factory.return_value = mock_factory

                from backend.scheduler.tasks import _mark_crawl_run_failed

                await _mark_crawl_run_failed(test_candidate.id, error_message)

        # Verify crawl run was updated
        await async_session.refresh(crawl_run)
        assert crawl_run.status.value == "FAILED"
        assert crawl_run.error_log == error_message
        assert crawl_run.completed_at is not None


# ─── Test: Dead Task Event Publishing ───────────────────────────────────────────


class TestDailyTaskDeadEvent:
    """Tests for DAILY_TASK_DEAD event publishing on terminal failure."""

    @pytest.mark.asyncio
    async def test_publish_dead_event_format(
        self, candidate_id: uuid.UUID, fake_redis
    ):
        """Verify DAILY_TASK_DEAD event payload matches the contract."""
        from backend.scheduler.tasks import DailyTaskDeadEvent

        event = DailyTaskDeadEvent(
            candidate_id=str(candidate_id),
            task_id=f"discovery-{candidate_id}-2026-05-27",
            error="Max retries exceeded",
            retries_exhausted=3,
        )

        assert event.event == "DAILY_TASK_DEAD"
        assert event.candidate_id == str(candidate_id)
        assert event.retries_exhausted == 3

    @pytest.mark.asyncio
    async def test_publish_dead_event_to_redis(
        self, candidate_id: uuid.UUID, fake_redis, expected_task_id: str
    ):
        """Verify DAILY_TASK_DEAD event is published to agent.status.discovery."""
        import json

        from backend.observability.events import PubSubChannel

        # Subscribe to the discovery channel
        pubsub = fake_redis.pubsub()
        await pubsub.subscribe(PubSubChannel.DISCOVERY.value)

        # Patch settings and redis creation
        with (
            patch("backend.scheduler.tasks.settings") as mock_settings,
            patch("backend.scheduler.tasks.aioredis") as mock_aioredis,
        ):
            mock_settings.redis_url = "redis://fake"
            mock_aioredis.from_url = MagicMock(return_value=fake_redis)

            from backend.scheduler.tasks import _publish_dead_event

            await _publish_dead_event(
                candidate_id,
                expected_task_id,
                "Test error message",
                retries=3,
            )

        # Get the published message
        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
        assert message is not None, "Expected a message to be published"

        payload = json.loads(message["data"])
        assert payload["event"] == "DAILY_TASK_DEAD"
        assert payload["candidate_id"] == str(candidate_id)
        assert payload["task_id"] == expected_task_id
        assert payload["error"] == "Test error message"
        assert payload["retries_exhausted"] == 3


# ─── Test: Task Execution Flow ──────────────────────────────────────────────────


class TestDailyTaskExecution:
    """Integration tests for the full task execution flow."""

    def test_task_has_correct_name(self):
        """Verify the Celery task has the expected name."""
        from backend.scheduler.tasks import daily_discovery_task

        assert (
            daily_discovery_task.name == "backend.scheduler.tasks.daily_discovery_task"
        )

    def test_task_has_correct_retry_config(self):
        """Verify the Celery task has correct retry configuration."""
        from backend.scheduler.tasks import daily_discovery_task

        assert daily_discovery_task.max_retries == 3
        assert daily_discovery_task.acks_late is True

    def test_trigger_daily_discovery_returns_task_id(self, candidate_id: uuid.UUID):
        """Verify trigger_daily_discovery returns the idempotent task_id."""
        from backend.scheduler.tasks import _compute_task_id, trigger_daily_discovery

        with patch(
            "backend.scheduler.tasks.daily_discovery_task.apply_async"
        ) as mock_apply:
            mock_apply.return_value = MagicMock()

            result = trigger_daily_discovery(candidate_id)

            expected_task_id = _compute_task_id(candidate_id)
            assert result == expected_task_id

            # Verify apply_async was called with correct task_id
            mock_apply.assert_called_once()
            call_kwargs = mock_apply.call_args.kwargs
            assert call_kwargs["task_id"] == expected_task_id


# ─── Test: Dry Run Mode ─────────────────────────────────────────────────────────


class TestDryRunMode:
    """Tests for dry_run mode behavior."""

    @pytest.mark.asyncio
    async def test_dry_run_does_not_create_crawl_run(
        self,
        async_session: AsyncSession,
        test_candidate: Candidate,
        fake_redis,
    ):
        """Verify dry_run=True does not create a crawl_runs row."""
        from backend.agents.discovery.orchestrator import DiscoveryOrchestrator

        # Create orchestrator with mocked dependencies
        orchestrator = DiscoveryOrchestrator.__new__(DiscoveryOrchestrator)
        orchestrator._db = async_session
        orchestrator._redis = fake_redis

        # Mock all sub-agents
        orchestrator._profiler = MagicMock()
        orchestrator._profiler.build_profile = AsyncMock(
            return_value=MagicMock(
                archetypes=[],
                leadership_level="IC",
                technical_skills=[],
                soft_skills=[],
                industry_experience=[],
                notable_achievements=[],
                career_trajectory="",
                ideal_role_description="",
                signals={},
            )
        )

        orchestrator._archetype_gen = MagicMock()
        orchestrator._archetype_gen.expand = MagicMock(
            return_value=MagicMock(
                target_titles=[],
                keywords=[],
                excluded_titles=[],
                excluded_companies=[],
                excluded_industries=[],
                location_filters=[],
                remote_preference="flexible",
                min_compensation=None,
            )
        )

        orchestrator._scorer = MagicMock()
        orchestrator._scorer.score_batch = AsyncMock(return_value=[])

        orchestrator._digest_builder = MagicMock()

        with patch(
            "backend.agents.discovery.orchestrator.CrawlerAgent"
        ) as MockCrawler:
            MockCrawler.return_value.run = AsyncMock(return_value=[])

            # Execute in dry_run mode
            await orchestrator.run(test_candidate.id, dry_run=True)

        # Verify no crawl_run was created
        result = await async_session.execute(
            select(CrawlRun).where(CrawlRun.candidate_id == test_candidate.id)
        )
        crawl_runs = result.scalars().all()

        assert len(crawl_runs) == 0, "dry_run should not create crawl_runs"
