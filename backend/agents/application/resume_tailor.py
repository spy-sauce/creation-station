# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Resume Tailor — rewrites a candidate's resume to align with a specific role.

Rules:
  - Never fabricate experience, titles, dates, or metrics
  - Mirror JD language naturally — not robotically
  - Prioritise relevance over comprehensiveness
  - Flag skill gaps in change_log, never invent them
  - Sound like a human wrote it, not an AI keyword-stuffer
"""

import json
import os
import re
from pathlib import Path
from uuid import UUID

import structlog
from anthropic import AsyncAnthropic
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.agents.application.schemas import ParsedJDSchema, TailoredResumeSchema
from backend.agents.discovery.schemas import CandidateSchema, IdentityProfile
from backend.models.application import TailoredResume as TailoredResumeORM

logger = structlog.get_logger(__name__)


class ResumeTailor:
    """
    Rewrites a candidate's resume to position them for a specific role.

    Uses Claude with the full identity profile and parsed JD as context.
    Stores versioned tailored resumes in PostgreSQL.
    """

    def __init__(
        self,
        db: AsyncSession,
        anthropic_client: AsyncAnthropic,
        screenshot_dir: str = "./screenshots",
    ):
        self._db = db
        self._claude = anthropic_client
        self._screenshot_dir = screenshot_dir

    async def tailor(
        self,
        parsed_jd: ParsedJDSchema,
        candidate: CandidateSchema,
        profile: IdentityProfile,
    ) -> TailoredResumeSchema:
        """
        Generate a tailored resume for this specific role.

        Args:
            parsed_jd: Structured signals from the job description
            candidate: Full candidate profile including base resume
            profile: Multi-dimensional identity model

        Returns:
            TailoredResumeSchema with full_text, change_log, and PDF path
        """
        log = logger.bind(job_id=str(parsed_jd.job_id), candidate=candidate.name)
        log.info("resume_tailor.starting")

        result = await self._call_claude(parsed_jd, candidate, profile)
        await self._persist(result)

        log.info("resume_tailor.complete", version=result.version)
        return result

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _call_claude(
        self,
        parsed_jd: ParsedJDSchema,
        candidate: CandidateSchema,
        profile: IdentityProfile,
    ) -> TailoredResumeSchema:
        """Ask Claude to rewrite the resume for this role."""
        prompt = self._build_prompt(parsed_jd, candidate, profile)

        response = await self._claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text.strip()
        logger.info(
            "resume_tailor.claude_response",
            job_id=str(parsed_jd.job_id),
            tokens=response.usage.output_tokens,
        )

        return self._parse_response(parsed_jd.job_id, candidate.id, raw)

    def _build_prompt(
        self,
        parsed_jd: ParsedJDSchema,
        candidate: CandidateSchema,
        profile: IdentityProfile,
    ) -> str:
        """Construct the tailoring prompt with full context."""
        skills_gap = [
            s for s in parsed_jd.required_skills
            if s.lower() not in {k.lower() for k in profile.technical_skills}
        ]

        return f"""You are rewriting a resume to position a candidate for a specific role.

# CANDIDATE
Name: {candidate.name}
Identity: {", ".join(profile.archetype_tags)}
Leadership level: {profile.leadership_level}
Domain expertise: {", ".join(profile.domain_expertise)}

# BASE RESUME
{candidate.resume_text}

# TARGET ROLE
Required skills: {", ".join(parsed_jd.required_skills)}
Preferred skills: {", ".join(parsed_jd.preferred_skills)}
Seniority: {parsed_jd.seniority_level}
Key responsibilities: {chr(10).join(f"- {r}" for r in parsed_jd.key_responsibilities)}
Pain point this hire solves: {parsed_jd.pain_points or "not specified"}
JD tone: {parsed_jd.tone}
Team context: {parsed_jd.team_context or "not specified"}

# SKILL GAPS (do NOT invent these — flag them in change_log)
{", ".join(skills_gap) if skills_gap else "None — strong overlap"}

# RULES
1. Rewrite the summary/profile section to directly address this role's pain point
2. Reorder and rewrite bullets to mirror JD language — naturally, not robotically
3. Surface the most relevant projects first
4. Cut bullets that don't serve this application
5. NEVER fabricate experience, dates, titles, or metrics
6. If a required skill is missing, do NOT invent it — note it in change_log
7. Preserve the candidate's authentic voice — sound like a human wrote this at 9pm
8. Keep it tight — every word earns its place

Return ONLY valid JSON:
{{
  "summary": "<rewritten profile/summary section>",
  "full_text": "<complete tailored resume as plain text, ready for PDF generation>",
  "change_log": "<bullet list: what changed from base resume and why, including any skill gaps>"
}}"""

    def _parse_response(
        self, job_id: UUID, candidate_id: UUID, raw: str
    ) -> TailoredResumeSchema:
        """Parse Claude's JSON response into a TailoredResumeSchema."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                raise ValueError(f"Claude returned non-JSON: {raw[:200]}")
            data = json.loads(match.group())

        return TailoredResumeSchema(
            job_id=job_id,
            candidate_id=candidate_id,
            summary=data.get("summary", ""),
            full_text=data.get("full_text", ""),
            change_log=data.get("change_log", ""),
        )

    async def _persist(self, resume: TailoredResumeSchema) -> None:
        """Store the tailored resume in PostgreSQL."""
        orm = TailoredResumeORM(
            job_id=resume.job_id,
            candidate_id=resume.candidate_id,
            summary=resume.summary,
            full_text=resume.full_text,
            change_log=resume.change_log,
            version=resume.version,
        )
        self._db.add(orm)
        await self._db.commit()
        await self._db.refresh(orm)
        logger.info(
            "resume_tailor.persisted",
            resume_id=str(orm.id),
            job_id=str(resume.job_id),
        )
