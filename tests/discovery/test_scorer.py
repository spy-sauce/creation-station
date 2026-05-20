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
