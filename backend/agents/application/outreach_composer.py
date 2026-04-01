# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Outreach Composer — writes a cold email that doesn't read like a cold email.

Email structure:
  1. Hook (1 sentence) — specific and real: funding, launch, blog post, shared signal
  2. Bridge (1-2 sentences) — connect hook to why the candidate is reaching out
  3. Value (2-3 sentences) — most relevant proof of impact for THIS role
  4. Ask (1 sentence) — specific low-friction CTA
  5. Signature — name, title, links

Rules:
  - 150–200 words max
  - Never start with "I hope this email finds you well"
  - Never use "I'm reaching out because..."
  - 3 subject line variants shown in Review Dashboard
  - Draft stays DRAFT until approved
"""

import json
import re
from uuid import UUID

import structlog
from anthropic import AsyncAnthropic
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.agents.application.schemas import (
    CompanyIntelSchema,
    ContactSchema,
    OutreachEmailSchema,
    ParsedJDSchema,
    TailoredResumeSchema,
)
from backend.agents.discovery.schemas import IdentityProfile
from backend.models.application import OutreachEmail as OutreachEmailORM

logger = structlog.get_logger(__name__)


class OutreachComposer:
    """
    Writes a personalised cold email grounded in real company context.

    Uses all available context: parsed JD, company intel, contact, tailored resume, identity profile.
    Generates 3 subject variants. Stays in DRAFT until the Review Dashboard approves it.
    """

    def __init__(self, db: AsyncSession, anthropic_client: AsyncAnthropic):
        self._db = db
        self._claude = anthropic_client

    async def compose(
        self,
        parsed_jd: ParsedJDSchema,
        intel: CompanyIntelSchema,
        contact: ContactSchema,
        resume: TailoredResumeSchema,
        profile: IdentityProfile,
        candidate_name: str,
        candidate_email: str,
        candidate_github: str | None = None,
        candidate_linkedin: str | None = None,
    ) -> OutreachEmailSchema:
        """
        Compose a cold outreach email for a specific job application.

        Args:
            parsed_jd: Structured job description signals
            intel: Company research with recent news and notable facts
            contact: Target recipient
            resume: Tailored resume (for selecting the right proof points)
            profile: Candidate identity profile
            candidate_name: Candidate's full name
            candidate_email: Candidate's email for signature
            candidate_github: Optional GitHub URL
            candidate_linkedin: Optional LinkedIn URL

        Returns:
            OutreachEmailSchema in DRAFT status
        """
        log = logger.bind(
            job_id=str(parsed_jd.job_id),
            company=intel.company_name,
            contact=contact.email,
        )
        log.info("outreach_composer.composing")

        result = await self._call_claude(
            parsed_jd, intel, contact, resume, profile,
            candidate_name, candidate_email, candidate_github, candidate_linkedin,
        )

        await self._persist(result)
        log.info("outreach_composer.complete", subject=result.subject)
        return result

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _call_claude(
        self,
        parsed_jd: ParsedJDSchema,
        intel: CompanyIntelSchema,
        contact: ContactSchema,
        resume: TailoredResumeSchema,
        profile: IdentityProfile,
        candidate_name: str,
        candidate_email: str,
        candidate_github: str | None,
        candidate_linkedin: str | None,
    ) -> OutreachEmailSchema:
        """Generate the outreach email via Claude."""
        prompt = self._build_prompt(
            parsed_jd, intel, contact, resume, profile,
            candidate_name, candidate_email, candidate_github, candidate_linkedin,
        )

        response = await self._claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text.strip()
        logger.info(
            "outreach_composer.claude_response",
            job_id=str(parsed_jd.job_id),
            tokens=response.usage.output_tokens,
        )

        data = self._extract_json(raw)

        subjects = data.get("subject_variants", [])
        primary_subject = subjects[0] if subjects else data.get("subject", "")

        return OutreachEmailSchema(
            job_id=parsed_jd.job_id,
            candidate_id=resume.candidate_id,
            to=contact.email or contact.fallback_email,
            subject=primary_subject,
            subject_variants=subjects,
            body=data.get("body", ""),
            tone_used=data.get("tone_used", intel.growth_stage or "professional"),
            hook_used=data.get("hook_used"),
            status="DRAFT",
        )

    def _build_prompt(
        self,
        parsed_jd: ParsedJDSchema,
        intel: CompanyIntelSchema,
        contact: ContactSchema,
        resume: TailoredResumeSchema,
        profile: IdentityProfile,
        candidate_name: str,
        candidate_email: str,
        candidate_github: str | None,
        candidate_linkedin: str | None,
    ) -> str:
        sig_links = []
        if candidate_github:
            sig_links.append(candidate_github)
        if candidate_linkedin:
            sig_links.append(candidate_linkedin)

        signature = f"{candidate_name}\n{candidate_email}"
        if sig_links:
            signature += "\n" + " | ".join(sig_links)

        return f"""You are writing a cold outreach email for a job application. It must feel human — specific, direct, not AI-generated.

# CANDIDATE CONTEXT
Name: {candidate_name}
Identity: {", ".join(profile.archetype_tags)}
Level: {profile.leadership_level}
Top skills: {", ".join(list(profile.technical_skills.keys())[:8])}
Creative layer: {", ".join(profile.creative_layer)}

# TARGET ROLE
Company: {intel.company_name}
Role: (job_id: {parsed_jd.job_id})
Pain point this hire solves: {parsed_jd.pain_points or "not specified"}
Key responsibilities: {", ".join(parsed_jd.key_responsibilities[:3])}
Culture: {parsed_jd.tone}, {parsed_jd.culture_signals.get("startup_vs_enterprise", "unknown")} company

# COMPANY INTEL
About: {intel.about or "Not available"}
Recent news: {intel.recent_news or "No recent news found"}
Notable hook: {intel.notable_facts or "None identified"}
Growth stage: {intel.growth_stage or "unknown"}
Engineering culture: {intel.engineering_culture or "not available"}

# RECIPIENT
Name: {contact.name or "Hiring Manager"}
Title: {contact.title or "Engineering Lead"}
Email: {contact.email or "unknown"}

# SIGNATURE
{signature}

# EMAIL RULES
1. HOOK (1 sentence): Reference something specific and real about the company — the notable_facts, recent news, a challenge implied by the role, or something in the eng culture. Be specific.
2. BRIDGE (1-2 sentences): Connect that hook to why you're reaching out
3. VALUE (2-3 sentences): The candidate's most relevant proof of impact for THIS role — pick from the tailored resume summary. Be concrete.
4. ASK (1 sentence): Specific low-friction CTA like "Would a 20-minute call this week make sense?"
5. Signature

ABSOLUTE RULES:
- 150–200 words max for the body
- Never start with "I hope this email finds you well"
- Never use "I'm reaching out because..."
- Never list every skill — pick the 1-2 that matter most here
- Address recipient by first name if available, "Hi" + first name
- Sound like a human wrote this at 9pm after doing research, not an AI at 6am

Return ONLY valid JSON:
{{
  "subject_variants": ["<subject 1>", "<subject 2>", "<subject 3>"],
  "body": "<full email body including greeting and signature>",
  "tone_used": "<the tone you chose based on company culture>",
  "hook_used": "<the specific company fact you used as the opening hook>"
}}"""

    def _extract_json(self, raw: str) -> dict:
        """Extract JSON from Claude's response."""
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                raise ValueError(f"Claude returned non-JSON: {raw[:200]}")
            return json.loads(match.group())

    async def _persist(self, email: OutreachEmailSchema) -> None:
        """Store the draft email in PostgreSQL."""
        orm = OutreachEmailORM(
            job_id=email.job_id,
            candidate_id=email.candidate_id,
            subject=email.subject,
            subject_variants=email.subject_variants,
            body=email.body,
            tone_used=email.tone_used,
            hook_used=email.hook_used,
            status=email.status,
        )
        self._db.add(orm)
        await self._db.commit()
        logger.info(
            "outreach_composer.persisted",
            job_id=str(email.job_id),
            subject=email.subject,
        )
