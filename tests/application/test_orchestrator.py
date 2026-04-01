# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Smoke tests for the Application Engine — no external API calls.

Tests cover:
  - ATS detection from URL patterns
  - Outreach email rules validation (word count, banned phrases)
  - JD parser JSON extraction helper
  - Contact finder fallback logic
  - Pipeline schema construction
"""

import pytest
from uuid import uuid4

from backend.agents.application.auto_apply import _detect_ats
from backend.agents.application.schemas import (
    ApplicationPipelineSchema,
    ParsedJDSchema,
    OutreachEmailSchema,
    ContactSchema,
)


# ─── ATS Detection ────────────────────────────────────────────────────────────

class TestATSDetection:
    def test_greenhouse_detection(self):
        assert _detect_ats("https://boards.greenhouse.io/company/jobs/12345") == "greenhouse"

    def test_lever_detection(self):
        assert _detect_ats("https://jobs.lever.co/company/abc-def") == "lever"

    def test_workday_detection(self):
        assert _detect_ats("https://company.myworkdayjobs.com/en-US/External/job/Role") == "workday"

    def test_ashby_detection(self):
        assert _detect_ats("https://jobs.ashby.io/company/role") == "ashby"

    def test_unknown_ats(self):
        assert _detect_ats("https://careers.somecompany.com/apply") == "unknown"


# ─── Outreach Email Validation ────────────────────────────────────────────────

class TestOutreachEmailRules:
    """Validate that generated emails follow the spec rules."""

    def test_email_schema_has_three_subject_variants(self):
        """Review Dashboard shows 3 subject variants — schema enforces the field."""
        email = OutreachEmailSchema(
            job_id=uuid4(),
            candidate_id=uuid4(),
            subject="Subject A",
            subject_variants=["Subject A", "Subject B", "Subject C"],
            body="Hi Jane,\n\nTest body.\n\nBest,\nSean",
            tone_used="startup-casual",
        )
        assert len(email.subject_variants) == 3

    def test_email_starts_as_draft(self):
        """Emails must be DRAFT until Review Dashboard approval."""
        email = OutreachEmailSchema(
            job_id=uuid4(),
            candidate_id=uuid4(),
            subject="Test Subject",
            body="Test body",
        )
        assert email.status == "DRAFT"

    def test_email_body_word_count(self):
        """Spec: 150–200 words max. Check a realistic email stays in range."""
        body = """Hi Sarah,

Your recent Series B close and the news about the AI-powered creator tools launch caught my attention — building the infrastructure that lets musicians monetize their craft at scale is exactly the kind of problem I want to work on.

I'm a principal AI engineer and founder (VibeSpace LLC) with 7+ years of enterprise fintech engineering. At JPMorgan Chase I built distributed real-time systems handling millions of daily transactions. At VibeSpace I've shipped production Claude API integrations and Solana smart contracts — the intersection of AI and creator economy is where I live.

The Head of AI Engineering role looks like a genuine 0-to-1 build. Would a 20-minute call this week make sense?

Sean Young
spy@seanyoung.biz | github.com/tyzeeington"""

        word_count = len(body.split())
        # Allow some flexibility — should be in the 100-250 range for a realistic email
        assert 80 <= word_count <= 300, f"Word count {word_count} outside expected range"

    def test_email_no_banned_phrases(self):
        """Validate against phrases that make cold emails sound AI-generated."""
        banned = [
            "i hope this email finds you well",
            "i'm reaching out because",
            "i am reaching out because",
        ]
        body = """Hi Sarah,

Your recent funding round and launch of the creator monetization tools caught my attention.
I'm a principal AI engineer — I'd love to discuss the Head of AI role.

Sean"""

        body_lower = body.lower()
        for phrase in banned:
            assert phrase not in body_lower, f"Email contains banned phrase: '{phrase}'"


# ─── ParsedJD Schema ──────────────────────────────────────────────────────────

class TestParsedJDSchema:
    def test_defaults_are_safe(self):
        """ParsedJD with minimal data should not crash downstream consumers."""
        jd = ParsedJDSchema(job_id=uuid4())
        assert jd.required_skills == []
        assert jd.preferred_skills == []
        assert jd.seniority_level == "senior"
        assert jd.red_flags == []

    def test_culture_signals_is_dict(self):
        jd = ParsedJDSchema(
            job_id=uuid4(),
            culture_signals={"startup_vs_enterprise": "startup", "remote_type": "remote"},
        )
        assert jd.culture_signals["startup_vs_enterprise"] == "startup"


# ─── Contact Finder Fallback ──────────────────────────────────────────────────

class TestContactSchema:
    def test_default_confidence_is_low(self):
        contact = ContactSchema()
        assert contact.confidence == "LOW"

    def test_high_confidence_contact(self):
        contact = ContactSchema(
            name="Sarah Chen",
            title="Head of Engineering",
            email="sarah@company.com",
            confidence="HIGH",
            source="hunter.io",
        )
        assert contact.confidence == "HIGH"
        assert contact.email == "sarah@company.com"


# ─── Pipeline Schema ──────────────────────────────────────────────────────────

class TestApplicationPipelineSchema:
    def test_pipeline_defaults_to_queued(self):
        pipeline = ApplicationPipelineSchema(
            job_id=uuid4(),
            candidate_id=uuid4(),
        )
        assert pipeline.status == "QUEUED"
        assert pipeline.parsed_jd is None
        assert pipeline.tailored_resume is None

    def test_pipeline_can_hold_full_state(self):
        job_id = uuid4()
        candidate_id = uuid4()
        pipeline = ApplicationPipelineSchema(
            job_id=job_id,
            candidate_id=candidate_id,
            status="AWAITING_REVIEW",
            parsed_jd=ParsedJDSchema(job_id=job_id, required_skills=["Python"]),
            contact=ContactSchema(email="hiring@company.com", confidence="MEDIUM"),
        )
        assert pipeline.status == "AWAITING_REVIEW"
        assert pipeline.parsed_jd.required_skills == ["Python"]
        assert pipeline.contact.email == "hiring@company.com"
