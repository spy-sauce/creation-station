# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Smoke tests for the RelevanceScorer — scoring math, not Claude API calls.

These tests run fully offline (no Anthropic API, no DB, no Redis).
"""

import pytest
from uuid import uuid4

from backend.agents.discovery.schemas import (
    IdentityProfile,
    DiscoveredJobSchema,
    ScoreBreakdown,
)
from backend.agents.discovery.relevance_scorer import RelevanceScorer


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def profile() -> IdentityProfile:
    """A realistic identity profile for Sean Young."""
    return IdentityProfile(
        candidate_id=uuid4(),
        technical_skills={
            "Python": 95,
            "FastAPI": 90,
            "Java": 85,
            "Spring Boot": 80,
            "PostgreSQL": 80,
            "Redis": 75,
            "Docker": 75,
            "Kubernetes": 70,
            "Claude API": 85,
            "Solana": 65,
        },
        domain_expertise=["fintech", "ai", "web3", "music", "creator-economy"],
        leadership_level="founder",
        archetype_tags=["technical-founder", "ai-builder", "creative-technologist"],
        role_expansion=[
            "Head of AI",
            "VP Engineering at music-tech startup",
            "Technical Co-Founder Series A",
            "AI Creative Director",
            "CTO fractional",
        ],
        culture_signals={
            "startup_vs_enterprise": "startup",
            "remote_preference": "remote",
            "mission_vs_comp": "mission",
        },
        compensation_band={"min": 200_000, "max": 350_000},
        creative_layer=["DJ", "music producer", "Solana developer"],
    )


@pytest.fixture
def strong_match_job() -> DiscoveredJobSchema:
    """A job that should score high for this profile."""
    return DiscoveredJobSchema(
        id=uuid4(),
        candidate_id=uuid4(),
        title="Head of AI Engineering",
        company="MusicTech Startup",
        location="Remote",
        url="https://example.com/jobs/head-of-ai",
        url_hash="abc123",
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
        source="greenhouse",
    )


@pytest.fixture
def weak_match_job() -> DiscoveredJobSchema:
    """A job that should score low for this profile."""
    return DiscoveredJobSchema(
        id=uuid4(),
        candidate_id=uuid4(),
        title="Junior Java Developer",
        company="Big Bank Corp",
        location="New York, NY (On-site required)",
        url="https://bigbank.com/jobs/junior-java",
        url_hash="def456",
        description="""
        Entry-level Java developer position. 0-2 years experience preferred.
        Required: Java basics, SQL
        On-site 5 days/week in Manhattan.
        Salary: $65,000 - $80,000
        Industry: Traditional Banking
        """,
        source="indeed",
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
        """founder → founder should be 100."""
        parsed_jd = {"seniority_level": "founder"}
        score = scorer._score_level(parsed_jd, profile)
        assert score == 100

    def test_level_match_one_step_off(self, scorer, profile):
        """founder → exec (1 step) should be 80."""
        parsed_jd = {"seniority_level": "exec"}
        score = scorer._score_level(parsed_jd, profile)
        assert score == 80

    def test_level_match_junior_job_for_founder(self, scorer, profile):
        """founder vs junior (many steps) should be low."""
        parsed_jd = {"seniority_level": "junior"}
        score = scorer._score_level(parsed_jd, profile)
        assert score <= 30

    def test_culture_match_remote_alignment(self, scorer, profile):
        """Remote candidate + remote job should score well."""
        from backend.agents.discovery.schemas import DiscoveredJobSchema
        job = DiscoveredJobSchema(
            candidate_id=uuid4(),
            title="Test",
            company="Test Co",
            url="https://x.com",
            url_hash="xyz",
        )
        parsed_jd = {
            "remote_type": "remote",
            "culture_signals": {"startup_vs_enterprise": "startup"},
        }
        score = scorer._score_culture(parsed_jd, profile, job)
        assert score >= 80

    def test_culture_match_onsite_penalty(self, scorer, profile):
        """Remote candidate + onsite job should score low."""
        from backend.agents.discovery.schemas import DiscoveredJobSchema
        job = DiscoveredJobSchema(
            candidate_id=uuid4(),
            title="Test",
            company="Test Co",
            url="https://x.com",
            url_hash="xyz",
        )
        parsed_jd = {
            "remote_type": "onsite",
            "culture_signals": {"startup_vs_enterprise": "enterprise"},
        }
        score = scorer._score_culture(parsed_jd, profile, job)
        assert score < 40

    def test_compensation_above_minimum(self, scorer, profile):
        parsed_jd = {"comp_mentioned": "$250,000 - $300,000"}
        score = scorer._score_compensation(parsed_jd, profile)
        assert score == 100

    def test_compensation_below_minimum(self, scorer, profile):
        parsed_jd = {"comp_mentioned": "$65,000 - $80,000"}
        score = scorer._score_compensation(parsed_jd, profile)
        assert score <= 15

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

    def test_company_profile_uses_culture_signals(self, profile):
        from backend.agents.discovery.archetype_generator import ArchetypeGenerator
        gen = ArchetypeGenerator()
        manifest = gen.expand(
            profile,
            {"titles": [], "companies": [], "industries": []},
        )
        # Startup profile should target early stages
        assert any(
            s in manifest.target_company_profile.stages
            for s in ["seed", "series-a", "series-b"]
        )
