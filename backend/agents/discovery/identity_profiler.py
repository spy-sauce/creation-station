# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Identity Profiler — transforms a raw candidate profile into a rich,
multi-dimensional identity model used by the rest of the Discovery Engine.

Flow:
  1. Check Redis cache (TTL 24h) — return cached profile if fresh
  2. Parse resume + personal context with Claude
  3. Generate role_expansion (15–20 non-obvious archetypes) via Claude
  4. Cache result in Redis
  5. Return IdentityProfile
"""

import json
import hashlib
from datetime import datetime
from uuid import UUID

import redis.asyncio as aioredis
import structlog
from anthropic import AsyncAnthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.config import settings
from backend.agents.discovery.schemas import CandidateSchema, IdentityProfile

logger = structlog.get_logger(__name__)

_CACHE_TTL = 86_400  # 24 hours


class IdentityProfiler:
    """
    Builds a rich multi-dimensional identity model from a candidate profile.

    Uses Claude to extract technical skills, leadership level, domain expertise,
    and generate non-obvious role expansion archetypes.
    """

    def __init__(self, redis_client: aioredis.Redis, anthropic_client: AsyncAnthropic):
        self._redis = redis_client
        self._claude = anthropic_client

    def _cache_key(self, candidate: CandidateSchema) -> str:
        """Derive a cache key from the candidate's data hash so stale profiles auto-invalidate."""
        content = f"{candidate.resume_text}{candidate.personal_context}"
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"identity_profile:{candidate.id}:{content_hash}"

    async def build_profile(self, candidate: CandidateSchema) -> IdentityProfile:
        """
        Build or retrieve cached identity profile for a candidate.

        Args:
            candidate: Full candidate schema

        Returns:
            IdentityProfile with all dimensions populated
        """
        cache_key = self._cache_key(candidate)

        # Check cache first
        cached = await self._redis.get(cache_key)
        if cached:
            logger.info("identity_profile.cache_hit", candidate_id=str(candidate.id))
            return IdentityProfile.model_validate_json(cached)

        logger.info("identity_profile.generating", candidate_id=str(candidate.id))
        profile = await self._generate_profile(candidate)

        # Cache the result
        await self._redis.setex(cache_key, _CACHE_TTL, profile.model_dump_json())
        logger.info(
            "identity_profile.cached",
            candidate_id=str(candidate.id),
            archetypes=len(profile.role_expansion),
        )
        return profile

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _generate_profile(self, candidate: CandidateSchema) -> IdentityProfile:
        """Call Claude to extract identity dimensions and generate role expansion."""
        prompt = self._build_prompt(candidate)

        response = await self._claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text
        logger.info(
            "identity_profile.claude_response",
            candidate_id=str(candidate.id),
            tokens_used=response.usage.output_tokens,
        )

        return self._parse_response(candidate.id, raw)

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
Email: {candidate.email}
Remote Preference: {candidate.remote_preference}
Min Compensation: {candidate.min_compensation or "Not specified"}
Target Locations: {", ".join(candidate.target_locations) or "Flexible"}
Excluded: {json.dumps(excluded)}

## Resume
{candidate.resume_text}

## Personal Context
{candidate.personal_context}

# INSTRUCTIONS

Return ONLY valid JSON matching this exact schema. No markdown, no explanation:

{{
  "technical_skills": {{
    "<skill_name>": <score_0_to_100>
  }},
  "domain_expertise": ["<domain1>", "<domain2>"],
  "leadership_level": "<ic|lead|staff|principal|founder|exec>",
  "archetype_tags": ["<tag1>", "<tag2>"],
  "role_expansion": [
    "<role_archetype_1>",
    "<role_archetype_2>"
  ],
  "culture_signals": {{
    "startup_vs_enterprise": "<startup|enterprise|both>",
    "remote_preference": "<remote|hybrid|onsite|flexible>",
    "mission_vs_comp": "<mission|comp|balanced>"
  }},
  "compensation_band": {{
    "min": <integer_usd>,
    "max": <integer_usd>
  }},
  "creative_layer": ["<creative_identity_1>"]
}}

# RULES FOR role_expansion
- Generate 15–20 non-obvious role archetypes beyond the candidate's current title
- Think: what roles would a headhunter NOT suggest but should?
- Include VP/director-level if seniority warrants
- Include cross-functional roles (e.g., DevRel, Technical PM, CTO, AI Creative Director)
- Include roles at the intersection of their technical + creative identity
- Do NOT include roles clearly below their level
- Do NOT include roles in their excluded_industries
"""

    def _parse_response(self, candidate_id: UUID, raw: str) -> IdentityProfile:
        """Parse Claude's JSON response into an IdentityProfile."""
        try:
            data = json.loads(raw.strip())
        except json.JSONDecodeError:
            # Attempt to extract JSON block if Claude included surrounding text
            import re
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                raise ValueError(f"Claude returned non-JSON response: {raw[:200]}")
            data = json.loads(match.group())

        return IdentityProfile(
            candidate_id=candidate_id,
            technical_skills=data.get("technical_skills", {}),
            domain_expertise=data.get("domain_expertise", []),
            leadership_level=data.get("leadership_level", "ic"),
            archetype_tags=data.get("archetype_tags", []),
            role_expansion=data.get("role_expansion", []),
            culture_signals=data.get("culture_signals", {}),
            compensation_band=data.get("compensation_band", {"min": 0, "max": 0}),
            creative_layer=data.get("creative_layer", []),
            generated_at=datetime.utcnow(),
        )
