# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Smoke tests for the RelevanceScorer — scoring math, not Claude API calls.

These tests run fully offline (no Anthropic API, no DB, no Redis).
"""

import pytest
from uuid import uuid4

from backend.agents.discovery.schemas import (
    IdentityProfileSchema,
    DiscoveredJobSchema,
    ScoreBreakdown,
)
from backend.agents.discovery.relevance_scorer import RelevanceScorer


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def profile() -> IdentityProfileSchema:
    """A realistic identity profile for Sean Young."""
    return IdentityProfileSchema(
        archetypes=[
            "Head of AI",
            "VP Engineering at music-tech startup",
            "Technical Co-Founder Series A",
            "AI Creative Director",
            "CTO fractional",
        ],
        leadership_level="C-Level",
        technical_skills=[
            "Python",
            "FastAPI",
            "Java",
            "Spring Boot",
            "PostgreSQL",
            "Redis",
            "Docker",
            "Kubernetes",
            "Claude API",
            "Solana",
        ],
        soft_skills=["technical-leadership", "team-building", "product-vision"],
        industry_experience=["fintech", "ai", "web3", "music", "creator-economy"],
        notable_achievements=[
            "Founded VibeSpace",
            "Built AI-powered talent agent system",
        ],
        career_trajectory="From software engineer to founder",
        ideal_role_description="Lead AI engineering at a mission-driven music-tech startup",
        signals={
            "startup_vs_enterprise": "startup",
            "remote_preference": "remote",
            "mission_vs_comp": "mission",
        },
    )


@pytest.fixture
def strong_match_job() -> DiscoveredJobSchema:
    """A job that should score high for this profile."""
    return DiscoveredJobSchema(
        id=uuid4(),
        source="greenhouse",
        source_id="gh-12345",
        title="Head of AI Engineering",
        company="MusicTech Startup",
        location="Remote",
        url="https://example.com/jobs/head-of-ai",
        description="""
        We're a Series B music-tech startup building AI tools for creators.
        Looking for a Head of AI Engineering to define our AI strategy from scratch.

        Required: Python, FastAPI, PostgreSQL, Redis, LLMs, Claude API
        Preferred: Kubernetes, Solana, Web3

        This is a 0-to-1 greenfield role. You'll shape the technical strategy,
        build the team from scratch, and report directly to the CTO.

        Compensation: $250,000-$300,000 + equity

        Remote-first. Mission-driven team.
        Industry: Music, AI, Creator Economy
        """,
    )


@pytest.fixture
def weak_match_job() -> DiscoveredJobSchema:
    """A job that should score low for this profile."""
    return DiscoveredJobSchema(
        id=uuid4(),
        source="indeed",
        source_id="indeed-67890",
        title="Junior Java Developer",
        company="Big Bank Corp",
        location="New York, NY (On-site required)",
        url="https://bigbank.com/jobs/junior-java",
        description="""
        Entry-level Java developer position. 0-2 years experience preferred.
        Required: Java basics, SQL
        On-site 5 days/week in Manhattan.
        Salary: $65,000 - $80,000
        Industry: Traditional Banking
        """,
    )


# ─── ScoreBreakdown unit tests ────────────────────────────────────────────────


class TestScoreBreakdown:
    def test_composite_weights_sum_to_full_score(self):
        """All dimensions at 100 should produce composite of 100."""
        breakdown = ScoreBreakdown(
            technical_match=100,
            level_match=100,
            culture_match=100,
            industry_match=100,
            growth_potential=100,
            compensation_match=100,
        )
        assert breakdown.composite == 100

    def test_composite_is_weighted(self):
        """Technical match at 100 (30% weight) + zeros = 30."""
        breakdown = ScoreBreakdown(
            technical_match=100,
            level_match=0,
            culture_match=0,
            industry_match=0,
            growth_potential=0,
            compensation_match=0,
        )
        assert breakdown.composite == 30

    def test_composite_rounds_down(self):
        """Composite should be an integer."""
        breakdown = ScoreBreakdown(
            technical_match=50,
            level_match=50,
            culture_match=50,
            industry_match=50,
            growth_potential=50,
            compensation_match=50,
        )
        assert breakdown.composite == 50
        assert isinstance(breakdown.composite, int)

    def test_field_bounds(self):
        """Scores outside 0-100 should be rejected by pydantic."""
        import pytest as pt
        from pydantic import ValidationError

        with pt.raises(ValidationError):
            ScoreBreakdown(
                technical_match=101,
                level_match=0,
                culture_match=0,
                industry_match=0,
                growth_potential=0,
                compensation_match=0,
            )


# ─── RelevanceScorer local scoring tests (no Claude) ─────────────────────────


class TestRelevanceScorerLocal:
    """
    Tests for the local scoring methods that don't require Claude API.

    Instantiates RelevanceScorer with a None client — only _score_* methods
    that don't call self._claude are tested here.
    """

    @pytest.fixture
    def scorer(self):
        return RelevanceScorer(anthropic_client=None)  # type: ignore

    def test_technical_match_high_overlap(self, scorer, profile):
        parsed_jd = {
            "required_skills": ["Python", "FastAPI", "PostgreSQL", "Redis"],
            "preferred_skills": ["Kubernetes", "Docker"],
        }
        score = scorer._score_technical(parsed_jd, profile)
        assert score >= 80, f"Expected >= 80, got {score}"

    def test_technical_match_no_overlap(self, scorer, profile):
        parsed_jd = {
            "required_skills": ["COBOL", "Fortran", "RPGLE"],
            "preferred_skills": [],
        }
        score = scorer._score_technical(parsed_jd, profile)
        assert score < 30, f"Expected < 30, got {score}"

    def test_technical_match_no_requirements(self, scorer, profile):
        """Empty requirements = neutral score."""
        score = scorer._score_technical({}, profile)
        assert score == 60

    def test_level_match_exact(self, scorer, profile):
        """C-Level → cto should be 100."""
        parsed_jd = {"seniority_level": "cto"}
        score = scorer._score_level(parsed_jd, profile)
        assert score == 100

    def test_level_match_one_step_off(self, scorer, profile):
        """C-Level → vp (1 step) should be 80."""
        parsed_jd = {"seniority_level": "vp"}
        score = scorer._score_level(parsed_jd, profile)
        assert score == 80

    def test_level_match_junior_job_for_clevel(self, scorer, profile):
        """C-Level vs junior (many steps) should be low."""
        parsed_jd = {"seniority_level": "junior"}
        score = scorer._score_level(parsed_jd, profile)
        assert score <= 30

    def test_culture_match_remote_alignment(self, scorer, profile):
        """Remote candidate + remote job should score well."""
        job = DiscoveredJobSchema(
            source="greenhouse",
            source_id="test-1",
            title="Test",
            company="Test Co",
            url="https://x.com",
        )
        parsed_jd = {
            "remote_type": "remote",
            "culture_signals": {"startup_vs_enterprise": "startup"},
        }
        score = scorer._score_culture(parsed_jd, profile, job)
        assert score >= 80

    def test_culture_match_onsite_penalty(self, scorer, profile):
        """Remote candidate + onsite job should score low."""
        job = DiscoveredJobSchema(
            source="greenhouse",
            source_id="test-2",
            title="Test",
            company="Test Co",
            url="https://x.com",
        )
        parsed_jd = {
            "remote_type": "onsite",
            "culture_signals": {"startup_vs_enterprise": "enterprise"},
        }
        score = scorer._score_culture(parsed_jd, profile, job)
        assert score < 40

    def test_compensation_not_listed(self, scorer, profile):
        """Senior roles often don't list comp — should be generous neutral."""
        score = scorer._score_compensation({}, profile)
        assert score >= 70


# ─── Archetype generator tests ────────────────────────────────────────────────


class TestArchetypeGenerator:
    def test_title_expansion_known_archetype(self, profile):
        from backend.agents.discovery.archetype_generator import ArchetypeGenerator

        gen = ArchetypeGenerator()
        manifest = gen.expand(
            profile,
            {"titles": [], "companies": [], "industries": []},
        )
        assert len(manifest.target_titles) > 0
        assert len(manifest.keywords) > 0

    def test_exclusions_passed_through(self, profile):
        """Excluded companies and industries should be in the manifest."""
        from backend.agents.discovery.archetype_generator import ArchetypeGenerator

        gen = ArchetypeGenerator()
        manifest = gen.expand(
            profile,
            {
                "titles": [],
                "companies": ["BadCo"],
                "industries": ["oil-and-gas"],
            },
        )
        assert "BadCo" in manifest.excluded_companies
        assert "oil-and-gas" in manifest.excluded_industries

    def test_keywords_include_skills(self, profile):
        """Keywords should include technical skills from the profile."""
        from backend.agents.discovery.archetype_generator import ArchetypeGenerator

        gen = ArchetypeGenerator()
        manifest = gen.expand(
            profile,
            {"titles": [], "companies": [], "industries": []},
        )
        # At least some skills should be in keywords
        skill_overlap = set(profile.technical_skills[:10]) & set(manifest.keywords)
        assert len(skill_overlap) > 0


# ─── CrawlerAgent tests ───────────────────────────────────────────────────────


class TestCrawlerAgent:
    """Tests for the CrawlerAgent Phase 1A stub implementation."""

    @pytest.fixture
    def manifest(self):
        from backend.agents.discovery.schemas import SearchManifestSchema

        return SearchManifestSchema(
            target_titles=["Head of AI", "VP Engineering", "CTO"],
            keywords=["Python", "FastAPI", "AI", "music"],
            excluded_companies=[],
            excluded_industries=[],
            location_filters=[],
            remote_preference="remote",
        )

    @pytest.mark.asyncio
    async def test_crawler_returns_jobs(self, manifest):
        """CrawlerAgent.run() should return a non-empty list of jobs."""
        from backend.agents.discovery.crawler_agent import CrawlerAgent

        crawler = CrawlerAgent(candidate_id=uuid4())
        jobs = await crawler.run(manifest)

        assert len(jobs) > 0
        assert all(j.title for j in jobs)
        assert all(j.company for j in jobs)
        assert all(j.url for j in jobs)

    @pytest.mark.asyncio
    async def test_crawler_respects_exclusions(self):
        """CrawlerAgent should exclude companies on the exclusion list."""
        from backend.agents.discovery.crawler_agent import CrawlerAgent
        from backend.agents.discovery.schemas import SearchManifestSchema

        manifest = SearchManifestSchema(
            target_titles=["Head of AI", "VP Engineering"],
            keywords=["Python", "AI"],
            excluded_companies=["MusicTech AI"],  # Exclude a fixture company
            excluded_industries=[],
            location_filters=[],
            remote_preference="flexible",
        )

        crawler = CrawlerAgent(candidate_id=uuid4())
        jobs = await crawler.run(manifest)

        # None of the returned jobs should be from MusicTech AI
        for job in jobs:
            assert "musictech ai" not in job.company.lower()

    @pytest.mark.asyncio
    async def test_crawler_filters_by_keywords(self):
        """CrawlerAgent should only return jobs matching keywords or titles."""
        from backend.agents.discovery.crawler_agent import CrawlerAgent
        from backend.agents.discovery.schemas import SearchManifestSchema

        # Use keywords that won't match any fixture jobs
        manifest = SearchManifestSchema(
            target_titles=["Underwater Basket Weaver"],
            keywords=["ancient-greek", "basket-weaving"],
            excluded_companies=[],
            excluded_industries=[],
            location_filters=[],
            remote_preference="flexible",
        )

        crawler = CrawlerAgent(candidate_id=uuid4())
        jobs = await crawler.run(manifest)

        # Should return empty list when nothing matches
        assert len(jobs) == 0

    def test_url_hash_deterministic(self):
        """url_hash should return the same hash for the same URL."""
        from backend.agents.discovery.crawler_agent import CrawlerAgent

        url = "https://example.com/jobs/123"
        hash1 = CrawlerAgent.url_hash(url)
        hash2 = CrawlerAgent.url_hash(url)
        assert hash1 == hash2

    def test_url_hash_case_insensitive(self):
        """url_hash should be case-insensitive."""
        from backend.agents.discovery.crawler_agent import CrawlerAgent

        hash1 = CrawlerAgent.url_hash("https://Example.COM/Jobs/123")
        hash2 = CrawlerAgent.url_hash("https://example.com/jobs/123")
        assert hash1 == hash2


# ─── Schema validation tests ─────────────────────────────────────────────────


class TestSchemas:
    def test_identity_profile_defaults(self):
        """IdentityProfileSchema should have sensible defaults."""
        profile = IdentityProfileSchema()
        assert profile.leadership_level == "IC"
        assert profile.archetypes == []
        assert profile.technical_skills == {} or profile.technical_skills == []
        assert profile.signals == {}

    def test_discovered_job_minimal(self):
        """DiscoveredJobSchema should work with minimal required fields."""
        job = DiscoveredJobSchema(
            source="greenhouse",
            source_id="test-123",
            title="Test Job",
            company="Test Co",
            url="https://example.com/job",
        )
        assert job.title == "Test Job"
        assert job.remote is False  # default

    def test_scored_job_schema(self, profile):
        """ScoredJobSchema should validate correctly."""
        from backend.agents.discovery.schemas import ScoredJobSchema

        scored = ScoredJobSchema(
            discovered_job_id=uuid4(),
            candidate_id=uuid4(),
            score_breakdown=ScoreBreakdown(
                technical_match=80,
                level_match=90,
                culture_match=75,
                industry_match=70,
                growth_potential=85,
                compensation_match=80,
            ),
            composite_score=80,
            is_hot=True,
            reasoning="Strong technical match with leadership alignment.",
            title="Head of AI",
            company="Test Co",
            url="https://example.com/job",
        )
        assert scored.is_hot is True
        assert scored.composite_score == 80

    def test_daily_digest_schema(self):
        """DailyDigestSchema should validate correctly."""
        from backend.agents.discovery.schemas import DailyDigestSchema

        digest = DailyDigestSchema(
            candidate_id=uuid4(),
            run_date="2026-05-20",
            total_jobs_discovered=100,
            total_jobs_scored=25,
            top_picks=[],
            hot_picks=[],
            new_companies=["NewCo", "AnotherCo"],
        )
        assert digest.total_jobs_discovered == 100
        assert len(digest.new_companies) == 2


# ─── Search manifest tests ───────────────────────────────────────────────────


class TestSearchManifest:
    def test_manifest_defaults(self):
        """SearchManifestSchema should have sensible defaults."""
        from backend.agents.discovery.schemas import SearchManifestSchema

        manifest = SearchManifestSchema()
        assert manifest.target_titles == []
        assert manifest.keywords == []
        assert manifest.remote_preference == "flexible"
        assert manifest.min_compensation is None

    def test_manifest_with_data(self):
        """SearchManifestSchema should accept all fields."""
        from backend.agents.discovery.schemas import SearchManifestSchema

        manifest = SearchManifestSchema(
            target_titles=["CTO", "VP Engineering"],
            keywords=["Python", "AI"],
            excluded_titles=["Junior"],
            excluded_companies=["BadCo"],
            excluded_industries=["oil"],
            location_filters=["Remote", "Miami"],
            remote_preference="remote_only",
            min_compensation=250000,
        )
        assert len(manifest.target_titles) == 2
        assert manifest.min_compensation == 250000
