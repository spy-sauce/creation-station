# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Test suite for DiscoveryOrchestrator pub/sub event emissions.

Validates that the orchestrator publishes the correct sequence of events
to Redis pub/sub during a discovery run.

Uses fakeredis for async Redis mocking and patches Claude API calls.
"""

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import fakeredis.aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.discovery.orchestrator import DiscoveryOrchestrator
from backend.agents.discovery.schemas import (
    CandidateSchema,
    IdentityProfileSchema,
    SearchManifestSchema,
    ScoredJobSchema,
    ScoreBreakdown,
    DailyDigestSchema,
    DiscoveredJobSchema,
)


# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
async def fake_redis():
    """Create a fakeredis async client for testing pub/sub."""
    server = fakeredis.FakeServer()
    client = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
    yield client
    await client.aclose()


@pytest.fixture
async def async_db():
    """
    Create a mock async database session for testing.

    We don't need a real database since we mock all DB interactions.
    """
    # Use a mock session since we patch all DB calls
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    yield session


@pytest.fixture
def mock_candidate_id():
    """Generate a deterministic candidate ID for testing."""
    return uuid4()


@pytest.fixture
def test_candidate(mock_candidate_id):
    """Create a test candidate schema (not ORM model)."""
    return CandidateSchema(
        id=mock_candidate_id,
        name="Test Candidate",
        email="test@example.com",
        resume_text="Senior software engineer with Python, FastAPI, PostgreSQL experience.",
        linkedin_url="https://linkedin.com/in/testcandidate",
        github_url="https://github.com/testcandidate",
        personal_context="Looking for AI/ML leadership roles",
        target_locations=["Remote", "Miami, FL"],
        remote_preference="flexible",
        min_compensation=200000,
        excluded_companies=["BigBank Corp"],
        excluded_industries=["Gambling"],
    )


@pytest.fixture
def mock_identity_profile():
    """Create a mock identity profile returned by IdentityProfiler."""
    return IdentityProfileSchema(
        archetypes=["Head of AI", "Principal Engineer", "VP Engineering"],
        leadership_level="Director",
        technical_skills=["Python", "FastAPI", "PostgreSQL", "Redis", "Claude API"],
        soft_skills=["Leadership", "Communication"],
        industry_experience=["Fintech", "AI/ML", "Music Tech"],
        notable_achievements=["Led team of 15 engineers", "Built AI platform"],
        career_trajectory="IC → Lead → Director, seeking VP/Head of roles",
        ideal_role_description="AI/ML leadership at a growth-stage startup",
        signals={
            "startup_vs_enterprise": "startup",
            "remote_preference": "remote",
            "mission_vs_comp": "balanced",
        },
    )


@pytest.fixture
def mock_search_manifest():
    """Create a mock search manifest returned by ArchetypeGenerator."""
    return SearchManifestSchema(
        target_titles=["Head of AI", "VP Engineering", "Director of AI"],
        keywords=["AI", "ML", "Python", "FastAPI"],
        excluded_titles=[],
        excluded_companies=["BigBank Corp"],
        excluded_industries=["Gambling"],
        location_filters=["Remote", "Miami"],
        remote_preference="remote",
        min_compensation=200000,
    )


@pytest.fixture
def mock_discovered_jobs():
    """Create mock discovered jobs returned by CrawlerAgent."""
    return [
        DiscoveredJobSchema(
            id=uuid4(),
            source="greenhouse",
            source_id="gh-test-001",
            title="Head of AI Engineering",
            company="AI Startup Co",
            location="Remote",
            description="Looking for Head of AI...",
            url="https://example.com/job/001",
            salary_min=250000,
            salary_max=350000,
            remote=True,
            crawled_at=datetime.now(timezone.utc),
        ),
        DiscoveredJobSchema(
            id=uuid4(),
            source="lever",
            source_id="lever-test-002",
            title="VP Engineering",
            company="FinTech Inc",
            location="Miami, FL / Remote",
            description="VP Engineering needed...",
            url="https://example.com/job/002",
            salary_min=300000,
            salary_max=400000,
            remote=True,
            crawled_at=datetime.now(timezone.utc),
        ),
    ]


@pytest.fixture
def mock_scored_jobs(mock_candidate_id, mock_discovered_jobs):
    """Create mock scored jobs returned by RelevanceScorer."""
    return [
        ScoredJobSchema(
            id=uuid4(),
            discovered_job_id=mock_discovered_jobs[0].id,
            candidate_id=mock_candidate_id,
            score_breakdown=ScoreBreakdown(
                technical_match=85,
                level_match=90,
                culture_match=80,
                industry_match=75,
                growth_potential=85,
                compensation_match=80,
            ),
            composite_score=84,
            is_hot=True,
            reasoning="Strong technical match with AI leadership experience.",
            title="Head of AI Engineering",
            company="AI Startup Co",
            location="Remote",
            url="https://example.com/job/001",
            scored_at=datetime.now(timezone.utc),
        ),
        ScoredJobSchema(
            id=uuid4(),
            discovered_job_id=mock_discovered_jobs[1].id,
            candidate_id=mock_candidate_id,
            score_breakdown=ScoreBreakdown(
                technical_match=80,
                level_match=85,
                culture_match=75,
                industry_match=80,
                growth_potential=70,
                compensation_match=85,
            ),
            composite_score=80,
            is_hot=True,
            reasoning="Good fintech leadership opportunity.",
            title="VP Engineering",
            company="FinTech Inc",
            location="Miami, FL / Remote",
            url="https://example.com/job/002",
            scored_at=datetime.now(timezone.utc),
        ),
    ]


# ─── Pub/Sub Collector Helper ────────────────────────────────────────────────


class PubSubCollector:
    """
    Collects published messages from a fakeredis pub/sub channel.

    Used to verify the sequence and content of events published by
    the orchestrator during a discovery run.
    """

    def __init__(self, redis_client, channel: str):
        self.redis_client = redis_client
        self.channel = channel
        self.messages: list[dict] = []
        self._pubsub = None
        self._task = None

    async def start(self):
        """Subscribe to the channel and start collecting messages."""
        self._pubsub = self.redis_client.pubsub()
        await self._pubsub.subscribe(self.channel)
        self._task = asyncio.create_task(self._collect())

    async def _collect(self):
        """Background task to collect published messages."""
        async for message in self._pubsub.listen():
            if message["type"] == "message":
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                try:
                    parsed = json.loads(data)
                    self.messages.append(parsed)
                except json.JSONDecodeError:
                    self.messages.append({"raw": data})

    async def stop(self):
        """Stop collecting and clean up."""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._pubsub:
            await self._pubsub.unsubscribe(self.channel)
            await self._pubsub.aclose()

    def get_event_sequence(self) -> list[str]:
        """Return the sequence of event status values."""
        return [msg.get("status") for msg in self.messages if "status" in msg]


# ─── Tests ───────────────────────────────────────────────────────────────────


class TestOrchestratorPubSub:
    """Test suite for DiscoveryOrchestrator pub/sub event emissions."""

    @pytest.mark.asyncio
    async def test_orchestrator_publishes_event_sequence(
        self,
        fake_redis,
        async_db,
        test_candidate,
        mock_identity_profile,
        mock_search_manifest,
        mock_discovered_jobs,
        mock_scored_jobs,
    ):
        """
        Verify the orchestrator publishes the correct sequence of events.

        Expected sequence (6 events minimum):
          1. CANDIDATE_LOADED
          2. PROFILE_BUILT
          3. MANIFEST_BUILT
          4. CRAWL_COMPLETE
          5. SCORING_COMPLETE
          6. RUN_COMPLETE
        """
        collector = PubSubCollector(fake_redis, "agent.status.discovery")
        await collector.start()

        # Allow subscriber to initialize
        await asyncio.sleep(0.1)

        with (
            patch.object(
                DiscoveryOrchestrator, "_load_candidate"
            ) as mock_load,
            patch(
                "backend.agents.discovery.orchestrator.IdentityProfiler"
            ) as MockProfiler,
            patch(
                "backend.agents.discovery.orchestrator.ArchetypeGenerator"
            ) as MockArchetype,
            patch(
                "backend.agents.discovery.orchestrator.CrawlerAgent"
            ) as MockCrawler,
            patch(
                "backend.agents.discovery.orchestrator.RelevanceScorer"
            ) as MockScorer,
            patch(
                "backend.agents.discovery.orchestrator.DigestBuilder"
            ) as MockDigest,
        ):
            # Set up mocks
            mock_load.return_value = test_candidate

            profiler_instance = AsyncMock()
            profiler_instance.build_profile.return_value = mock_identity_profile
            MockProfiler.return_value = profiler_instance

            archetype_instance = MagicMock()
            archetype_instance.expand.return_value = mock_search_manifest
            MockArchetype.return_value = archetype_instance

            crawler_instance = AsyncMock()
            crawler_instance.run.return_value = mock_discovered_jobs
            MockCrawler.return_value = crawler_instance

            scorer_instance = AsyncMock()
            scorer_instance.score_batch.return_value = mock_scored_jobs
            MockScorer.return_value = scorer_instance

            digest_instance = AsyncMock()
            digest_instance.compile.return_value = DailyDigestSchema(
                candidate_id=test_candidate.id,
                run_date="2026-05-27",
                total_jobs_discovered=2,
                total_jobs_scored=2,
                top_picks=mock_scored_jobs,
                hot_picks=mock_scored_jobs,
                new_companies=["AI Startup Co", "FinTech Inc"],
            )
            MockDigest.return_value = digest_instance

            # Run orchestrator
            with patch("backend.agents.discovery.orchestrator.settings") as mock_settings:
                mock_settings.anthropic_api_key = "test-key"
                mock_settings.crawl_concurrency = 4
                mock_settings.min_score = 60

                orchestrator = DiscoveryOrchestrator(async_db, fake_redis)
                orchestrator._profiler = profiler_instance
                orchestrator._archetype_gen = archetype_instance
                orchestrator._scorer = scorer_instance
                orchestrator._digest_builder = digest_instance

                result = await orchestrator.run(test_candidate.id, dry_run=True)

        # Allow events to propagate
        await asyncio.sleep(0.2)
        await collector.stop()

        # Verify event sequence
        event_sequence = collector.get_event_sequence()

        # Assert minimum 6 events
        assert len(event_sequence) >= 6, (
            f"Expected at least 6 events, got {len(event_sequence)}: {event_sequence}"
        )

        # Verify expected events are present
        expected_events = [
            "CANDIDATE_LOADED",
            "PROFILE_BUILT",
            "MANIFEST_BUILT",
            "CRAWL_COMPLETE",
            "SCORING_COMPLETE",
            "RUN_COMPLETE",
        ]
        for event in expected_events:
            assert event in event_sequence, f"Missing expected event: {event}"

        # Verify RUN_COMPLETE is last
        assert event_sequence[-1] == "RUN_COMPLETE", (
            f"RUN_COMPLETE should be last, but got: {event_sequence[-1]}"
        )

    @pytest.mark.asyncio
    async def test_no_duplicate_events(
        self,
        fake_redis,
        async_db,
        test_candidate,
        mock_identity_profile,
        mock_search_manifest,
        mock_discovered_jobs,
        mock_scored_jobs,
    ):
        """Verify no duplicate events are published during a run."""
        collector = PubSubCollector(fake_redis, "agent.status.discovery")
        await collector.start()
        await asyncio.sleep(0.1)

        with (
            patch.object(
                DiscoveryOrchestrator, "_load_candidate"
            ) as mock_load,
            patch(
                "backend.agents.discovery.orchestrator.IdentityProfiler"
            ) as MockProfiler,
            patch(
                "backend.agents.discovery.orchestrator.ArchetypeGenerator"
            ) as MockArchetype,
            patch(
                "backend.agents.discovery.orchestrator.CrawlerAgent"
            ) as MockCrawler,
            patch(
                "backend.agents.discovery.orchestrator.RelevanceScorer"
            ) as MockScorer,
            patch(
                "backend.agents.discovery.orchestrator.DigestBuilder"
            ) as MockDigest,
        ):
            mock_load.return_value = test_candidate

            profiler_instance = AsyncMock()
            profiler_instance.build_profile.return_value = mock_identity_profile
            MockProfiler.return_value = profiler_instance

            archetype_instance = MagicMock()
            archetype_instance.expand.return_value = mock_search_manifest
            MockArchetype.return_value = archetype_instance

            crawler_instance = AsyncMock()
            crawler_instance.run.return_value = mock_discovered_jobs
            MockCrawler.return_value = crawler_instance

            scorer_instance = AsyncMock()
            scorer_instance.score_batch.return_value = mock_scored_jobs
            MockScorer.return_value = scorer_instance

            digest_instance = AsyncMock()
            digest_instance.compile.return_value = DailyDigestSchema(
                candidate_id=test_candidate.id,
                run_date="2026-05-27",
                total_jobs_discovered=2,
                total_jobs_scored=2,
                top_picks=mock_scored_jobs,
                hot_picks=mock_scored_jobs,
                new_companies=["AI Startup Co", "FinTech Inc"],
            )
            MockDigest.return_value = digest_instance

            with patch("backend.agents.discovery.orchestrator.settings") as mock_settings:
                mock_settings.anthropic_api_key = "test-key"
                mock_settings.crawl_concurrency = 4
                mock_settings.min_score = 60

                orchestrator = DiscoveryOrchestrator(async_db, fake_redis)
                orchestrator._profiler = profiler_instance
                orchestrator._archetype_gen = archetype_instance
                orchestrator._scorer = scorer_instance
                orchestrator._digest_builder = digest_instance

                await orchestrator.run(test_candidate.id, dry_run=True)

        await asyncio.sleep(0.2)
        await collector.stop()

        event_sequence = collector.get_event_sequence()

        # Check for duplicates
        seen = set()
        duplicates = []
        for event in event_sequence:
            if event in seen:
                duplicates.append(event)
            seen.add(event)

        assert not duplicates, f"Found duplicate events: {duplicates}"

    @pytest.mark.asyncio
    async def test_run_complete_is_last_event(
        self,
        fake_redis,
        async_db,
        test_candidate,
        mock_identity_profile,
        mock_search_manifest,
        mock_discovered_jobs,
        mock_scored_jobs,
    ):
        """Explicitly verify RUN_COMPLETE is the final event."""
        collector = PubSubCollector(fake_redis, "agent.status.discovery")
        await collector.start()
        await asyncio.sleep(0.1)

        with (
            patch.object(
                DiscoveryOrchestrator, "_load_candidate"
            ) as mock_load,
            patch(
                "backend.agents.discovery.orchestrator.IdentityProfiler"
            ) as MockProfiler,
            patch(
                "backend.agents.discovery.orchestrator.ArchetypeGenerator"
            ) as MockArchetype,
            patch(
                "backend.agents.discovery.orchestrator.CrawlerAgent"
            ) as MockCrawler,
            patch(
                "backend.agents.discovery.orchestrator.RelevanceScorer"
            ) as MockScorer,
            patch(
                "backend.agents.discovery.orchestrator.DigestBuilder"
            ) as MockDigest,
        ):
            mock_load.return_value = test_candidate

            profiler_instance = AsyncMock()
            profiler_instance.build_profile.return_value = mock_identity_profile
            MockProfiler.return_value = profiler_instance

            archetype_instance = MagicMock()
            archetype_instance.expand.return_value = mock_search_manifest
            MockArchetype.return_value = archetype_instance

            crawler_instance = AsyncMock()
            crawler_instance.run.return_value = mock_discovered_jobs
            MockCrawler.return_value = crawler_instance

            scorer_instance = AsyncMock()
            scorer_instance.score_batch.return_value = mock_scored_jobs
            MockScorer.return_value = scorer_instance

            digest_instance = AsyncMock()
            digest_instance.compile.return_value = DailyDigestSchema(
                candidate_id=test_candidate.id,
                run_date="2026-05-27",
                total_jobs_discovered=2,
                total_jobs_scored=2,
                top_picks=mock_scored_jobs,
                hot_picks=mock_scored_jobs,
                new_companies=["AI Startup Co", "FinTech Inc"],
            )
            MockDigest.return_value = digest_instance

            with patch("backend.agents.discovery.orchestrator.settings") as mock_settings:
                mock_settings.anthropic_api_key = "test-key"
                mock_settings.crawl_concurrency = 4
                mock_settings.min_score = 60

                orchestrator = DiscoveryOrchestrator(async_db, fake_redis)
                orchestrator._profiler = profiler_instance
                orchestrator._archetype_gen = archetype_instance
                orchestrator._scorer = scorer_instance
                orchestrator._digest_builder = digest_instance

                await orchestrator.run(test_candidate.id, dry_run=True)

        await asyncio.sleep(0.2)
        await collector.stop()

        event_sequence = collector.get_event_sequence()
        assert len(event_sequence) > 0, "No events were published"
        assert event_sequence[-1] == "RUN_COMPLETE", (
            f"Expected RUN_COMPLETE as last event, got: {event_sequence[-1]}"
        )

    @pytest.mark.asyncio
    async def test_run_failed_emits_on_error(
        self,
        fake_redis,
        async_db,
        test_candidate,
    ):
        """Verify RUN_FAILED is emitted when orchestrator encounters an error."""
        collector = PubSubCollector(fake_redis, "agent.status.discovery")
        await collector.start()
        await asyncio.sleep(0.1)

        with (
            patch.object(
                DiscoveryOrchestrator, "_load_candidate"
            ) as mock_load,
            patch(
                "backend.agents.discovery.orchestrator.IdentityProfiler"
            ) as MockProfiler,
        ):
            mock_load.return_value = test_candidate

            # Make profiler raise an exception
            profiler_instance = AsyncMock()
            profiler_instance.build_profile.side_effect = Exception("Claude API error")
            MockProfiler.return_value = profiler_instance

            with patch("backend.agents.discovery.orchestrator.settings") as mock_settings:
                mock_settings.anthropic_api_key = "test-key"
                mock_settings.crawl_concurrency = 4
                mock_settings.min_score = 60

                orchestrator = DiscoveryOrchestrator(async_db, fake_redis)
                orchestrator._profiler = profiler_instance

                with pytest.raises(Exception, match="Claude API error"):
                    await orchestrator.run(test_candidate.id, dry_run=True)

        await asyncio.sleep(0.2)
        await collector.stop()

        event_sequence = collector.get_event_sequence()

        # Should have CANDIDATE_LOADED then RUN_FAILED
        assert "CANDIDATE_LOADED" in event_sequence
        assert "RUN_FAILED" in event_sequence
        assert event_sequence[-1] == "RUN_FAILED", (
            f"Expected RUN_FAILED as last event, got: {event_sequence[-1]}"
        )

    @pytest.mark.asyncio
    async def test_event_payload_contains_candidate_id(
        self,
        fake_redis,
        async_db,
        test_candidate,
        mock_identity_profile,
        mock_search_manifest,
        mock_discovered_jobs,
        mock_scored_jobs,
    ):
        """Verify all published events contain the candidate_id."""
        collector = PubSubCollector(fake_redis, "agent.status.discovery")
        await collector.start()
        await asyncio.sleep(0.1)

        with (
            patch.object(
                DiscoveryOrchestrator, "_load_candidate"
            ) as mock_load,
            patch(
                "backend.agents.discovery.orchestrator.IdentityProfiler"
            ) as MockProfiler,
            patch(
                "backend.agents.discovery.orchestrator.ArchetypeGenerator"
            ) as MockArchetype,
            patch(
                "backend.agents.discovery.orchestrator.CrawlerAgent"
            ) as MockCrawler,
            patch(
                "backend.agents.discovery.orchestrator.RelevanceScorer"
            ) as MockScorer,
            patch(
                "backend.agents.discovery.orchestrator.DigestBuilder"
            ) as MockDigest,
        ):
            mock_load.return_value = test_candidate

            profiler_instance = AsyncMock()
            profiler_instance.build_profile.return_value = mock_identity_profile
            MockProfiler.return_value = profiler_instance

            archetype_instance = MagicMock()
            archetype_instance.expand.return_value = mock_search_manifest
            MockArchetype.return_value = archetype_instance

            crawler_instance = AsyncMock()
            crawler_instance.run.return_value = mock_discovered_jobs
            MockCrawler.return_value = crawler_instance

            scorer_instance = AsyncMock()
            scorer_instance.score_batch.return_value = mock_scored_jobs
            MockScorer.return_value = scorer_instance

            digest_instance = AsyncMock()
            digest_instance.compile.return_value = DailyDigestSchema(
                candidate_id=test_candidate.id,
                run_date="2026-05-27",
                total_jobs_discovered=2,
                total_jobs_scored=2,
                top_picks=mock_scored_jobs,
                hot_picks=mock_scored_jobs,
                new_companies=["AI Startup Co", "FinTech Inc"],
            )
            MockDigest.return_value = digest_instance

            with patch("backend.agents.discovery.orchestrator.settings") as mock_settings:
                mock_settings.anthropic_api_key = "test-key"
                mock_settings.crawl_concurrency = 4
                mock_settings.min_score = 60

                orchestrator = DiscoveryOrchestrator(async_db, fake_redis)
                orchestrator._profiler = profiler_instance
                orchestrator._archetype_gen = archetype_instance
                orchestrator._scorer = scorer_instance
                orchestrator._digest_builder = digest_instance

                await orchestrator.run(test_candidate.id, dry_run=True)

        await asyncio.sleep(0.2)
        await collector.stop()

        # Verify all messages have candidate_id
        for msg in collector.messages:
            assert "candidate_id" in msg, f"Message missing candidate_id: {msg}"
            assert msg["candidate_id"] == str(test_candidate.id), (
                f"Wrong candidate_id: {msg['candidate_id']}"
            )

    @pytest.mark.asyncio
    async def test_events_published_to_correct_channel(
        self,
        fake_redis,
        async_db,
        test_candidate,
        mock_identity_profile,
        mock_search_manifest,
        mock_discovered_jobs,
        mock_scored_jobs,
    ):
        """Verify events are published to agent.status.discovery channel."""
        # Subscribe to a different channel — should receive nothing
        wrong_collector = PubSubCollector(fake_redis, "agent.status.application")
        await wrong_collector.start()

        # Subscribe to the correct channel
        correct_collector = PubSubCollector(fake_redis, "agent.status.discovery")
        await correct_collector.start()

        await asyncio.sleep(0.1)

        with (
            patch.object(
                DiscoveryOrchestrator, "_load_candidate"
            ) as mock_load,
            patch(
                "backend.agents.discovery.orchestrator.IdentityProfiler"
            ) as MockProfiler,
            patch(
                "backend.agents.discovery.orchestrator.ArchetypeGenerator"
            ) as MockArchetype,
            patch(
                "backend.agents.discovery.orchestrator.CrawlerAgent"
            ) as MockCrawler,
            patch(
                "backend.agents.discovery.orchestrator.RelevanceScorer"
            ) as MockScorer,
            patch(
                "backend.agents.discovery.orchestrator.DigestBuilder"
            ) as MockDigest,
        ):
            mock_load.return_value = test_candidate

            profiler_instance = AsyncMock()
            profiler_instance.build_profile.return_value = mock_identity_profile
            MockProfiler.return_value = profiler_instance

            archetype_instance = MagicMock()
            archetype_instance.expand.return_value = mock_search_manifest
            MockArchetype.return_value = archetype_instance

            crawler_instance = AsyncMock()
            crawler_instance.run.return_value = mock_discovered_jobs
            MockCrawler.return_value = crawler_instance

            scorer_instance = AsyncMock()
            scorer_instance.score_batch.return_value = mock_scored_jobs
            MockScorer.return_value = scorer_instance

            digest_instance = AsyncMock()
            digest_instance.compile.return_value = DailyDigestSchema(
                candidate_id=test_candidate.id,
                run_date="2026-05-27",
                total_jobs_discovered=2,
                total_jobs_scored=2,
                top_picks=mock_scored_jobs,
                hot_picks=mock_scored_jobs,
                new_companies=["AI Startup Co", "FinTech Inc"],
            )
            MockDigest.return_value = digest_instance

            with patch("backend.agents.discovery.orchestrator.settings") as mock_settings:
                mock_settings.anthropic_api_key = "test-key"
                mock_settings.crawl_concurrency = 4
                mock_settings.min_score = 60

                orchestrator = DiscoveryOrchestrator(async_db, fake_redis)
                orchestrator._profiler = profiler_instance
                orchestrator._archetype_gen = archetype_instance
                orchestrator._scorer = scorer_instance
                orchestrator._digest_builder = digest_instance

                await orchestrator.run(test_candidate.id, dry_run=True)

        await asyncio.sleep(0.2)
        await wrong_collector.stop()
        await correct_collector.stop()

        # Wrong channel should have no messages
        assert len(wrong_collector.messages) == 0, (
            f"Wrong channel received messages: {wrong_collector.messages}"
        )

        # Correct channel should have messages
        assert len(correct_collector.messages) > 0, (
            "Correct channel received no messages"
        )

    @pytest.mark.asyncio
    async def test_event_order_is_deterministic(
        self,
        fake_redis,
        async_db,
        test_candidate,
        mock_identity_profile,
        mock_search_manifest,
        mock_discovered_jobs,
        mock_scored_jobs,
    ):
        """Verify event order follows the pipeline execution order."""
        collector = PubSubCollector(fake_redis, "agent.status.discovery")
        await collector.start()
        await asyncio.sleep(0.1)

        with (
            patch.object(
                DiscoveryOrchestrator, "_load_candidate"
            ) as mock_load,
            patch(
                "backend.agents.discovery.orchestrator.IdentityProfiler"
            ) as MockProfiler,
            patch(
                "backend.agents.discovery.orchestrator.ArchetypeGenerator"
            ) as MockArchetype,
            patch(
                "backend.agents.discovery.orchestrator.CrawlerAgent"
            ) as MockCrawler,
            patch(
                "backend.agents.discovery.orchestrator.RelevanceScorer"
            ) as MockScorer,
            patch(
                "backend.agents.discovery.orchestrator.DigestBuilder"
            ) as MockDigest,
        ):
            mock_load.return_value = test_candidate

            profiler_instance = AsyncMock()
            profiler_instance.build_profile.return_value = mock_identity_profile
            MockProfiler.return_value = profiler_instance

            archetype_instance = MagicMock()
            archetype_instance.expand.return_value = mock_search_manifest
            MockArchetype.return_value = archetype_instance

            crawler_instance = AsyncMock()
            crawler_instance.run.return_value = mock_discovered_jobs
            MockCrawler.return_value = crawler_instance

            scorer_instance = AsyncMock()
            scorer_instance.score_batch.return_value = mock_scored_jobs
            MockScorer.return_value = scorer_instance

            digest_instance = AsyncMock()
            digest_instance.compile.return_value = DailyDigestSchema(
                candidate_id=test_candidate.id,
                run_date="2026-05-27",
                total_jobs_discovered=2,
                total_jobs_scored=2,
                top_picks=mock_scored_jobs,
                hot_picks=mock_scored_jobs,
                new_companies=["AI Startup Co", "FinTech Inc"],
            )
            MockDigest.return_value = digest_instance

            with patch("backend.agents.discovery.orchestrator.settings") as mock_settings:
                mock_settings.anthropic_api_key = "test-key"
                mock_settings.crawl_concurrency = 4
                mock_settings.min_score = 60

                orchestrator = DiscoveryOrchestrator(async_db, fake_redis)
                orchestrator._profiler = profiler_instance
                orchestrator._archetype_gen = archetype_instance
                orchestrator._scorer = scorer_instance
                orchestrator._digest_builder = digest_instance

                await orchestrator.run(test_candidate.id, dry_run=True)

        await asyncio.sleep(0.2)
        await collector.stop()

        event_sequence = collector.get_event_sequence()

        # Define expected order
        expected_order = [
            "CANDIDATE_LOADED",
            "PROFILE_BUILT",
            "MANIFEST_BUILT",
            "CRAWL_COMPLETE",
            "SCORING_COMPLETE",
            "RUN_COMPLETE",
        ]

        # Verify order
        for i, expected in enumerate(expected_order):
            assert event_sequence[i] == expected, (
                f"Event at position {i} should be {expected}, "
                f"got {event_sequence[i]}. Full sequence: {event_sequence}"
            )
