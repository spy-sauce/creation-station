# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
JD Parser — deep-parses a job description into structured signals for application tailoring.

Uses Claude to extract: required skills, seniority, team context, culture signals,
pain points the hire is solving, tone, and application instructions.

Caches parsed JDs in PostgreSQL — if the same job is re-processed, we skip Claude.
"""

import json
import re
from uuid import UUID

import structlog
from anthropic import AsyncAnthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.agents.application.schemas import ParsedJDSchema
from backend.agents.discovery.schemas import ScoredJobSchema
from backend.models.application import ParsedJD as ParsedJDORM

logger = structlog.get_logger(__name__)


class JDParser:
    """
    Parses a job description into structured signals using Claude.

    Results are cached in PostgreSQL — call parse() and it handles cache lookup automatically.
    """

    def __init__(self, db: AsyncSession, anthropic_client: AsyncAnthropic):
        self._db = db
        self._claude = anthropic_client

    async def parse(self, job: ScoredJobSchema) -> ParsedJDSchema:
        """
        Parse a job description into structured signals.

        Checks PostgreSQL cache first — reuses if already parsed.

        Args:
            job: ScoredJob from the Discovery Engine

        Returns:
            ParsedJDSchema with all signals extracted
        """
        job_id = job.job.id
        log = logger.bind(job_id=str(job_id), title=job.job.title, company=job.job.company)

        # Check cache
        cached = await self._get_cached(job_id)
        if cached:
            log.info("jd_parser.cache_hit")
            return cached

        log.info("jd_parser.parsing")
        parsed = await self._call_claude(job)
        await self._persist(parsed)
        log.info("jd_parser.complete", skills=len(parsed.required_skills))
        return parsed

    async def _get_cached(self, job_id: UUID) -> ParsedJDSchema | None:
        """Return cached ParsedJD if one exists for this job."""
        result = await self._db.execute(
            select(ParsedJDORM).where(ParsedJDORM.job_id == job_id)
        )
        orm = result.scalar_one_or_none()
        if not orm:
            return None
        return ParsedJDSchema(
            job_id=orm.job_id,
            required_skills=orm.required_skills or [],
            preferred_skills=orm.preferred_skills or [],
            seniority_level=orm.seniority_level or "senior",
            team_context=orm.team_context,
            key_responsibilities=orm.key_responsibilities or [],
            culture_signals=orm.culture_signals or {},
            tech_stack=orm.tech_stack or [],
            pain_points=orm.pain_points,
            tone=orm.tone or "professional",
            comp_mentioned=orm.comp_mentioned,
            red_flags=orm.red_flags or [],
            application_instructions=orm.application_instructions,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _call_claude(self, job: ScoredJobSchema) -> ParsedJDSchema:
        """Extract structured data from the JD via Claude."""
        description = job.job.description or ""
        prompt = f"""Parse this job description into structured signals. Return ONLY valid JSON, no markdown.

Job Title: {job.job.title}
Company: {job.job.company}
Location: {job.job.location or "Not specified"}

Description:
{description[:4000]}

Return this exact JSON:
{{
  "required_skills": ["<skill>"],
  "preferred_skills": ["<skill>"],
  "seniority_level": "<intern|junior|mid|senior|staff|principal|lead|manager|director|vp|head|exec>",
  "team_context": "<who they join, who they report to>",
  "key_responsibilities": ["<top 5 responsibilities by emphasis>"],
  "culture_signals": {{
    "startup_vs_enterprise": "<startup|enterprise|both>",
    "remote_type": "<remote|hybrid|onsite|flexible>",
    "mission_driven": "<true|false>"
  }},
  "tech_stack": ["<technology>"],
  "pain_points": "<what problem is this hire solving>",
  "tone": "<formal|startup-casual|technical|mission-driven>",
  "comp_mentioned": "<salary string or null>",
  "red_flags": ["<red flag if any>"],
  "application_instructions": "<any specific apply instructions or null>"
}}"""

        response = await self._claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text.strip()
        logger.info(
            "jd_parser.claude_response",
            job_id=str(job.job.id),
            tokens=response.usage.output_tokens,
        )

        data = self._extract_json(raw)
        return ParsedJDSchema(
            job_id=job.job.id,
            required_skills=data.get("required_skills", []),
            preferred_skills=data.get("preferred_skills", []),
            seniority_level=data.get("seniority_level", "senior"),
            team_context=data.get("team_context"),
            key_responsibilities=data.get("key_responsibilities", []),
            culture_signals=data.get("culture_signals", {}),
            tech_stack=data.get("tech_stack", []),
            pain_points=data.get("pain_points"),
            tone=data.get("tone", "professional"),
            comp_mentioned=data.get("comp_mentioned"),
            red_flags=data.get("red_flags", []),
            application_instructions=data.get("application_instructions"),
        )

    def _extract_json(self, raw: str) -> dict:
        """Parse JSON from Claude's response, handling any surrounding text."""
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                raise ValueError(f"Claude returned non-JSON: {raw[:200]}")
            return json.loads(match.group())

    async def _persist(self, parsed: ParsedJDSchema) -> None:
        """Cache the parsed JD in PostgreSQL."""
        orm = ParsedJDORM(
            job_id=parsed.job_id,
            required_skills=parsed.required_skills,
            preferred_skills=parsed.preferred_skills,
            seniority_level=parsed.seniority_level,
            team_context=parsed.team_context,
            key_responsibilities=parsed.key_responsibilities,
            culture_signals=parsed.culture_signals,
            tech_stack=parsed.tech_stack,
            pain_points=parsed.pain_points,
            tone=parsed.tone,
            comp_mentioned=parsed.comp_mentioned,
            red_flags=parsed.red_flags,
            application_instructions=parsed.application_instructions,
        )
        self._db.add(orm)
        await self._db.commit()
