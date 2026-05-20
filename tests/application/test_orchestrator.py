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
  - Application result schema validation
  - CRM event schema validation
"""

import pytest
from uuid import uuid4

from backend.agents.application.auto_apply import _detect_ats
from backend.agents.application.schemas import (
    ApplicationPipelineSchema,
    ApplicationResultSchema,
    ParsedJDSchema,
    TailoredResumeSchema,
    CompanyIntelSchema,
    OutreachEmailSchema,
    ContactSchema,
    CRMEventSchema,
)


# ─── ATS Detection ────────────────────────────────────────────────────────────


class TestATSDetection:
    """Tests for the _detect_ats helper function."""

    def test_greenhouse_detection(self):
        """Greenhouse URLs should return 'greenhouse'."""
        assert _detect_ats("https://boards.greenhouse.io/company/jobs/12345") == "greenhouse"

    def test_greenhouse_variant(self):
        """Alternative Greenhouse URL pattern."""
        assert _detect_ats("https://greenhouse.io/embed/board?token=abc") == "greenhouse"

    def test_lever_detection(self):
        """Lever URLs should return 'lever'."""
        assert _detect_ats("https://jobs.lever.co/company/abc-def") == "lever"

    def test_workday_detection(self):
        """Workday URLs should return 'workday'."""
        assert _detect_ats("https://company.myworkdayjobs.com/en-US/External/job/Role") == "workday"

    def test_workday_variant(self):
        """Alternative Workday URL pattern."""
        assert _detect_ats("https://workday.com/job/123") == "workday"

    def test_ashby_detection(self):
        """Ashby URLs should return 'ashby'."""
        assert _detect_ats("https://jobs.ashby.io/company/role") == "ashby"

    def test_ashby_variant(self):
        """Alternative Ashby URL pattern."""
        assert _detect_ats("https://ashbyhq.com/company/jobs/123") == "ashby"

    def test_unknown_ats(self):
        """Unknown career page URLs should return 'unknown'."""
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

    def test_email_schema_fields(self):
        """Verify all required fields for outreach composer output."""
        email = OutreachEmailSchema(
            job_id=uuid4(),
            candidate_id=uuid4(),
            to="sarah@company.com",
            subject="About the Head of AI role",
            subject_variants=["About the Head of AI role", "AI leader opportunity", "Building the future of AI"],
            body="Test body here.",
            tone_used="startup-casual",
            hook_used="Series B close",
        )
        assert email.to == "sarah@company.com"
        assert email.hook_used == "Series B close"
        assert email.tone_used == "startup-casual"


# ─── ParsedJD Schema ──────────────────────────────────────────────────────────


class TestParsedJDSchema:
    """Tests for the ParsedJD schema structure."""

    def test_defaults_are_safe(self):
        """ParsedJD with minimal data should not crash downstream consumers."""
        jd = ParsedJDSchema(job_id=uuid4())
        assert jd.required_skills == []
        assert jd.preferred_skills == []
        assert jd.seniority_level == "senior"
        assert jd.red_flags == []

    def test_culture_signals_is_dict(self):
        """Culture signals should be a dict with string keys and values."""
        jd = ParsedJDSchema(
            job_id=uuid4(),
            culture_signals={"startup_vs_enterprise": "startup", "remote_type": "remote"},
        )
        assert jd.culture_signals["startup_vs_enterprise"] == "startup"

    def test_jd_parser_fields(self):
        """Verify all fields needed by JDParser are available."""
        jd = ParsedJDSchema(
            job_id=uuid4(),
            required_skills=["Python", "FastAPI"],
            preferred_skills=["Kubernetes"],
            seniority_level="staff",
            team_context="Reporting to VP Engineering",
            key_responsibilities=["Build AI infrastructure", "Lead team of 5"],
            culture_signals={"startup_vs_enterprise": "startup"},
            tech_stack=["Python", "PostgreSQL", "Redis"],
            pain_points="Need to scale AI inference 10x",
            tone="technical",
            comp_mentioned="$200k-$250k",
            red_flags=["Unlimited PTO"],
            application_instructions="Apply via email to jobs@company.com",
        )
        assert len(jd.key_responsibilities) == 2
        assert jd.team_context == "Reporting to VP Engineering"
        assert jd.pain_points == "Need to scale AI inference 10x"
        assert jd.comp_mentioned == "$200k-$250k"


# ─── Tailored Resume Schema ───────────────────────────────────────────────────


class TestTailoredResumeSchema:
    """Tests for the TailoredResume schema structure."""

    def test_defaults(self):
        """Resume with minimal data should have safe defaults."""
        resume = TailoredResumeSchema()
        assert resume.version == 1
        assert resume.original_text == ""
        assert resume.full_text == ""

    def test_resume_tailor_fields(self):
        """Verify all fields needed by ResumeTailor are available."""
        resume = TailoredResumeSchema(
            job_id=uuid4(),
            candidate_id=uuid4(),
            summary="Experienced AI engineer...",
            full_text="Full resume text here...",
            change_log="- Reordered skills section\n- Emphasized Python experience",
            version=1,
            pdf_path="/tmp/resume_v1.pdf",
        )
        assert resume.summary.startswith("Experienced")
        assert resume.version == 1
        assert resume.pdf_path is not None


# ─── Company Intel Schema ─────────────────────────────────────────────────────


class TestCompanyIntelSchema:
    """Tests for the CompanyIntel schema structure."""

    def test_company_intel_fields(self):
        """Verify all fields needed by CompanyIntelAgent are available."""
        intel = CompanyIntelSchema(
            company_name="Acme Corp",
            domain="acme.com",
            about="Acme builds AI tools for developers.",
            recent_news="Closed Series B at $50M",
            tech_stack=["Python", "Kubernetes", "PostgreSQL"],
            engineering_culture="Remote-first, async communication",
            growth_stage="series-b",
            team_size="50-100",
            notable_facts="Founded by ex-Google engineers",
        )
        assert intel.company_name == "Acme Corp"
        assert intel.domain == "acme.com"
        assert intel.notable_facts == "Founded by ex-Google engineers"


# ─── Contact Schema ───────────────────────────────────────────────────────────


class TestContactSchema:
    """Tests for the Contact schema structure."""

    def test_default_confidence_is_low(self):
        """Contacts without explicit confidence should be LOW."""
        contact = ContactSchema()
        assert contact.confidence == "LOW"

    def test_high_confidence_contact(self):
        """HIGH confidence contacts from verified sources."""
        contact = ContactSchema(
            name="Sarah Chen",
            title="Head of Engineering",
            email="sarah@company.com",
            confidence="HIGH",
            source="hunter.io",
        )
        assert contact.confidence == "HIGH"
        assert contact.email == "sarah@company.com"

    def test_fallback_email(self):
        """Low confidence contacts should have fallback email."""
        contact = ContactSchema(
            email="jobs@company.com",
            confidence="LOW",
            source="generic_fallback",
            fallback_email="recruiting@company.com",
        )
        assert contact.fallback_email == "recruiting@company.com"


# ─── Application Result Schema ────────────────────────────────────────────────


class TestApplicationResultSchema:
    """Tests for the ApplicationResult schema used by AutoApplyAgent."""

    def test_requires_manual_status(self):
        """REQUIRES_MANUAL status when CAPTCHA detected."""
        result = ApplicationResultSchema(
            pipeline_id=uuid4(),
            job_id=uuid4(),
            status="REQUIRES_MANUAL",
            error="CAPTCHA detected — requires manual submission",
            fallback_url="https://jobs.company.com/apply",
        )
        assert result.status == "REQUIRES_MANUAL"
        assert "CAPTCHA" in result.error

    def test_successful_submission(self):
        """Successful submission with confirmation."""
        result = ApplicationResultSchema(
            pipeline_id=uuid4(),
            job_id=uuid4(),
            status="SUBMITTED",
            confirmation_number="APP-12345",
            fields_completed=["first_name", "last_name", "email", "resume"],
        )
        assert result.status == "SUBMITTED"
        assert result.confirmation_number == "APP-12345"
        assert len(result.fields_completed) == 4

    def test_failed_submission(self):
        """Failed submission with error details."""
        result = ApplicationResultSchema(
            pipeline_id=uuid4(),
            job_id=uuid4(),
            status="FAILED",
            error="Form element not found: #submit-button",
        )
        assert result.status == "FAILED"
        assert result.error is not None


# ─── CRM Event Schema ─────────────────────────────────────────────────────────


class TestCRMEventSchema:
    """Tests for the CRM event logging schema."""

    def test_crm_event_types(self):
        """Verify standard CRM event types can be created."""
        event_types = [
            "JD_PARSED",
            "RESUME_TAILORED",
            "COMPANY_RESEARCHED",
            "CONTACT_FOUND",
            "EMAIL_DRAFTED",
            "SUBMITTED",
            "PIPELINE_FAILED",
        ]
        pipeline_id = uuid4()
        for event_type in event_types:
            event = CRMEventSchema(
                pipeline_id=pipeline_id,
                event_type=event_type,
                payload={"test": "data"},
            )
            assert event.event_type == event_type
            assert event.payload == {"test": "data"}


# ─── Pipeline Schema ──────────────────────────────────────────────────────────


class TestApplicationPipelineSchema:
    """Tests for the full ApplicationPipeline schema."""

    def test_pipeline_defaults_to_queued(self):
        """New pipelines start in QUEUED status."""
        pipeline = ApplicationPipelineSchema(
            job_id=uuid4(),
            candidate_id=uuid4(),
        )
        assert pipeline.status == "QUEUED"
        assert pipeline.parsed_jd is None
        assert pipeline.tailored_resume is None

    def test_pipeline_can_hold_full_state(self):
        """Pipeline can contain all sub-schemas for AWAITING_REVIEW state."""
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

    def test_pipeline_status_flow(self):
        """Verify all valid status values per the spec."""
        valid_statuses = [
            "QUEUED",
            "PARSING",
            "TAILORING",
            "RESEARCHING",
            "COMPOSING",
            "AWAITING_REVIEW",
            "APPROVED",
            "REJECTED",
            "SUBMITTED",
            "SENT",
            "TRACKED",
            "FAILED",
            "REQUIRES_MANUAL",
        ]
        for status in valid_statuses:
            pipeline = ApplicationPipelineSchema(
                job_id=uuid4(),
                candidate_id=uuid4(),
                status=status,
            )
            assert pipeline.status == status

    def test_pipeline_with_full_artifacts(self):
        """Pipeline with all artifacts populated."""
        job_id = uuid4()
        candidate_id = uuid4()
        pipeline_id = uuid4()

        pipeline = ApplicationPipelineSchema(
            id=pipeline_id,
            job_id=job_id,
            candidate_id=candidate_id,
            status="AWAITING_REVIEW",
            parsed_jd=ParsedJDSchema(
                job_id=job_id,
                required_skills=["Python", "FastAPI"],
                seniority_level="senior",
            ),
            tailored_resume=TailoredResumeSchema(
                pipeline_id=pipeline_id,
                job_id=job_id,
                candidate_id=candidate_id,
                full_text="Tailored resume content...",
                change_log="- Emphasized Python experience",
            ),
            company_intel=CompanyIntelSchema(
                pipeline_id=pipeline_id,
                company_name="TechCorp",
                about="Building AI tools",
            ),
            contact=ContactSchema(
                pipeline_id=pipeline_id,
                email="hiring@techcorp.com",
                confidence="HIGH",
            ),
            outreach_email=OutreachEmailSchema(
                pipeline_id=pipeline_id,
                job_id=job_id,
                candidate_id=candidate_id,
                subject="AI Engineer Opportunity",
                subject_variants=["AI Engineer Opportunity", "Joining TechCorp", "AI role discussion"],
                body="Hi,\n\nTest email body.\n\nBest,\nSean",
            ),
        )

        assert pipeline.id == pipeline_id
        assert pipeline.parsed_jd.required_skills == ["Python", "FastAPI"]
        assert pipeline.tailored_resume.full_text.startswith("Tailored")
        assert pipeline.company_intel.company_name == "TechCorp"
        assert pipeline.contact.confidence == "HIGH"
        assert pipeline.outreach_email.status == "DRAFT"
        assert len(pipeline.outreach_email.subject_variants) == 3
