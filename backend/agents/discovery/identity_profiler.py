# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Identity Profiler — transforms a raw candidate profile into a rich,
multi-dimensional identity model used by the rest of the Discovery Engine.

Flow:
  1. Check Redis cache (TTL 24h) — return cached profile if fresh
  2. Parse resume + personal context with Claude
  3. Generate archetypes and identity dimensions via Claude
  4. Cache result in Redis
  5. Return IdentityProfileSchema
"""

import json
import hashlib

import redis.asyncio as aioredis
import structlog
from anthropic import AsyncAnthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.agents.discovery.schemas import CandidateSchema, IdentityProfileSchema

logger = structlog.get_logger(__name__)

_CACHE_TTL = 86_400  # 24 hours


class IdentityProfiler:
    """
    Builds a rich multi-dimensional identity model from a candidate profile.

    Uses Claude to extract technical skills, leadership level, domain expertise,
    and generate archetypes for role matching.
    """

    def __init__(self, redis_client: aioredis.Redis, anthropic_client: AsyncAnthropic):
        """
        Initialize the IdentityProfiler.

        Args:
            redis_client: Async Redis client for caching
            anthropic_client: Async Anthropic client for Claude API
        """
        self._redis = redis_client
        self._claude = anthropic_client

    def _cache_key(self, candidate: CandidateSchema) -> str:
        """
        Derive a cache key from the candidate's data hash.

        Content hash ensures stale profiles auto-invalidate when resume changes.
        """
        content = f"{candidate.resume_text}{candidate.personal_context or ''}"
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"profile:candidate:{candidate.id}:{content_hash}"

    async def build_profile(self, candidate: CandidateSchema) -> IdentityProfileSchema:
        """
        Build or retrieve cached identity profile for a candidate.

        Args:
            candidate: Full candidate schema

        Returns:
            IdentityProfileSchema with all dimensions populated
        """
        cache_key = self._cache_key(candidate)

        # Check cache first
        cached = await self._redis.get(cache_key)
        if cached:
            logger.info("identity_profiler.cache_hit", candidate_id=str(candidate.id))
            return IdentityProfileSchema.model_validate_json(cached)

        logger.info("identity_profiler.generating", candidate_id=str(candidate.id))
        profile = await self._generate_profile(candidate)

        # Cache the result
        await self._redis.setex(cache_key, _CACHE_TTL, profile.model_dump_json())
        logger.info(
            "identity_profiler.cached",
            candidate_id=str(candidate.id),
            archetypes=len(profile.archetypes),
        )
        return profile

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _generate_profile(self, candidate: CandidateSchema) -> IdentityProfileSchema:
        """Call Claude to extract identity dimensions and generate archetypes."""
        prompt = self._build_prompt(candidate)

        response = await self._claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text
        logger.info(
            "identity_profiler.claude_response",
            candidate_id=str(candidate.id),
            tokens_used=response.usage.output_tokens,
        )

        return self._parse_response(raw)

    def _build_prompt(self, candidate: CandidateSchema) -> str:
        """Construct the Claude prompt for identity extraction."""
        excluded = {
            "companies": candidate.excluded_companies,
            "industries": candidate.excluded_industries,
        }
        return f"""You are building a rich identity model for a talent agent system.

Analyze this candidate and return a JSON object with the exact structure specified below.

# CANDIDATE DATA

Name: {candidate.name}
Remote Preference: {candidate.remote_preference}
Min Compensation: {candidate.min_compensation or "Not specified"}
Target Locations: {", ".join(candidate.target_locations) or "Flexible"}
Excluded: {json.dumps(excluded)}

## Resume
{candidate.resume_text}

## Personal Context
{candidate.personal_context or "Not provided"}

# INSTRUCTIONS

Return ONLY valid JSON matching this exact schema. No markdown, no explanation:

{{
  "archetypes": [
    "<archetype_1>",
    "<archetype_2>"
  ],
  "leadership_level": "<IC|Lead|Manager|Director|VP|C-Level>",
  "technical_skills": ["<skill_1>", "<skill_2>"],
  "soft_skills": ["<skill_1>", "<skill_2>"],
  "industry_experience": ["<industry_1>", "<industry_2>"],
  "notable_achievements": ["<achievement_1>", "<achievement_2>"],
  "career_trajectory": "<one sentence describing career arc>",
  "ideal_role_description": "<one sentence describing ideal next role>",
  "signals": {{
    "startup_vs_enterprise": "<startup|enterprise|both>",
    "remote_preference": "<remote|hybrid|onsite|flexible>",
    "mission_vs_comp": "<mission|comp|balanced>"
  }}
}}

# RULES FOR archetypes
- Generate 15–20 non-obvious role archetypes beyond the candidate's current title
- Think: what roles would a headhunter NOT suggest but should?
- Include VP/director-level if seniority warrants
- Include cross-functional roles (e.g., DevRel, Technical PM, CTO, AI Creative Director)
- Include roles at the intersection of their technical + creative identity
- Do NOT include roles clearly below their level
- Do NOT include roles in their excluded_industries

# CRITICAL RULES
- NEVER fabricate skills not evidenced in the resume
- Extract ONLY skills explicitly mentioned or clearly demonstrated
- Be conservative with leadership_level — evidence must be clear
"""

    def _parse_response(self, raw: str) -> IdentityProfileSchema:
        """Parse Claude's JSON response into an IdentityProfileSchema."""
        import re

        try:
            data = json.loads(raw.strip())
        except json.JSONDecodeError:
            # Attempt to extract JSON block if Claude included surrounding text
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                raise ValueError(f"Claude returned non-JSON response: {raw[:200]}")
            data = json.loads(match.group())

        return IdentityProfileSchema(
            archetypes=data.get("archetypes", []),
            leadership_level=data.get("leadership_level", "IC"),
            technical_skills=data.get("technical_skills", []),
            soft_skills=data.get("soft_skills", []),
            industry_experience=data.get("industry_experience", []),
            notable_achievements=data.get("notable_achievements", []),
            career_trajectory=data.get("career_trajectory", ""),
            ideal_role_description=data.get("ideal_role_description", ""),
            signals=data.get("signals", {}),
        )
