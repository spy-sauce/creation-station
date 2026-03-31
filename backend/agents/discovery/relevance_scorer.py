# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Relevance Scorer — scores each discovered job against the candidate's identity profile.

Scoring dimensions (each 0–100):
  technical_match   30%  — skills overlap between JD and candidate profile
  level_match       20%  — seniority alignment (penalise over AND under)
  culture_match     15%  — startup/enterprise, remote, mission alignment
  industry_match    15%  — domain expertise alignment
  growth_potential  10%  — does this expand the candidate's trajectory?
  compensation_match 10% — estimated band vs candidate target

Claude parses the JD. Math runs locally. Claude writes 2-sentence reasoning.
"""

import json
import re
from typing import Optional

import structlog
from anthropic import AsyncAnthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.config import settings
from backend.agents.discovery.schemas import (
    IdentityProfile,
    DiscoveredJobSchema,
    ScoredJobSchema,
    ScoreBreakdown,
)

logger = structlog.get_logger(__name__)

# Seniority levels for level_match scoring — lower index = more junior
_SENIORITY_LADDER = [
    "intern", "junior", "associate", "mid", "senior", "staff",
    "principal", "lead", "manager", "director", "vp", "svp",
    "head", "cto", "coo", "ceo", "founder", "exec",
]

_LEADERSHIP_TO_LADDER = {
    "ic": "senior",
    "lead": "lead",
    "staff": "staff",
    "principal": "principal",
    "founder": "founder",
    "exec": "vp",
}

_REMOTE_KEYWORD_MAP = {
    "remote": ["remote", "distributed", "anywhere", "work from home", "wfh"],
    "hybrid": ["hybrid", "flexible"],
    "onsite": ["on-site", "onsite", "in-office", "in office", "office required"],
}


class RelevanceScorer:
    """
    Scores discovered jobs against a candidate's identity profile.

    Uses Claude to parse JD requirements and generate reasoning.
    Scoring math runs locally — no LLM needed for the numbers.
    """

    def __init__(self, anthropic_client: AsyncAnthropic):
        self._claude = anthropic_client

    async def score_batch(
        self,
        jobs: list[DiscoveredJobSchema],
        profile: IdentityProfile,
        min_score: int = 60,
    ) -> list[ScoredJobSchema]:
        """
        Score a batch of discovered jobs, filtering out those below min_score.

        Args:
            jobs: Raw discovered jobs to score
            profile: Candidate identity profile
            min_score: Jobs below this composite score are discarded

        Returns:
            Sorted list of ScoredJobSchema, highest composite first
        """
        logger.info(
            "relevance_scorer.batch_start",
            job_count=len(jobs),
            min_score=min_score,
        )

        scored: list[ScoredJobSchema] = []
        for job in jobs:
            try:
                result = await self.score_job(job, profile)
                if result.composite_score >= min_score:
                    scored.append(result)
            except Exception as e:
                logger.error(
                    "relevance_scorer.job_error",
                    job_url=job.url,
                    error=str(e),
                )

        scored.sort(key=lambda s: s.composite_score, reverse=True)
        logger.info(
            "relevance_scorer.batch_complete",
            scored=len(scored),
            filtered_out=len(jobs) - len(scored),
        )
        return scored

    async def score_job(self, job: DiscoveredJobSchema, profile: IdentityProfile) -> ScoredJobSchema:
        """
        Score a single job against the identity profile.

        Args:
            job: Discovered job
            profile: Candidate identity profile

        Returns:
            ScoredJobSchema with full breakdown and reasoning
        """
        parsed_jd = await self._parse_jd(job)
        scores = self._compute_scores(parsed_jd, profile, job)
        composite = scores.composite
        reasoning = await self._generate_reasoning(job, profile, scores, composite)

        return ScoredJobSchema(
            job=job,
            scores=scores,
            composite_score=composite,
            reasoning=reasoning,
            is_hot=composite >= 80,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _parse_jd(self, job: DiscoveredJobSchema) -> dict:
        """Use Claude to extract structured requirements from a job description."""
        if not job.description:
            return {}

        prompt = f"""Extract structured data from this job description. Return ONLY valid JSON, no markdown:

Job Title: {job.title}
Company: {job.company}
Location: {job.location or "Not specified"}

Description:
{job.description[:3000]}

Return this exact JSON structure:
{{
  "required_skills": ["<skill1>", "<skill2>"],
  "preferred_skills": ["<skill1>"],
  "seniority_level": "<intern|junior|mid|senior|staff|principal|lead|manager|director|vp|head|exec>",
  "remote_type": "<remote|hybrid|onsite|flexible>",
  "industries": ["<industry1>"],
  "comp_mentioned": "<salary string or null>",
  "culture_signals": {{
    "startup_vs_enterprise": "<startup|enterprise|both>",
    "mission_driven": <true|false>
  }},
  "growth_indicators": ["<indicator1>"]
}}"""

        response = await self._claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text.strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            return json.loads(match.group()) if match else {}

    def _compute_scores(
        self, parsed_jd: dict, profile: IdentityProfile, job: DiscoveredJobSchema
    ) -> ScoreBreakdown:
        """Compute all six scoring dimensions locally."""
        return ScoreBreakdown(
            technical_match=self._score_technical(parsed_jd, profile),
            level_match=self._score_level(parsed_jd, profile),
            culture_match=self._score_culture(parsed_jd, profile, job),
            industry_match=self._score_industry(parsed_jd, profile),
            growth_potential=self._score_growth(parsed_jd, profile),
            compensation_match=self._score_compensation(parsed_jd, profile),
        )

    def _score_technical(self, parsed_jd: dict, profile: IdentityProfile) -> int:
        """Score based on skills overlap between JD requirements and candidate skills."""
        required = {s.lower() for s in parsed_jd.get("required_skills", [])}
        preferred = {s.lower() for s in parsed_jd.get("preferred_skills", [])}
        candidate_skills = {s.lower() for s in profile.technical_skills.keys()}

        if not required:
            return 60  # No requirements listed — neutral score

        required_hits = len(required & candidate_skills)
        preferred_hits = len(preferred & candidate_skills)

        required_ratio = required_hits / len(required) if required else 0
        preferred_bonus = min(20, preferred_hits * 4) if preferred else 0

        base = int(required_ratio * 80)
        return min(100, base + preferred_bonus)

    def _score_level(self, parsed_jd: dict, profile: IdentityProfile) -> int:
        """Score seniority alignment — penalise both under and over."""
        jd_level = parsed_jd.get("seniority_level", "").lower()
        candidate_level = _LEADERSHIP_TO_LADDER.get(profile.leadership_level, "senior")

        try:
            jd_idx = _SENIORITY_LADDER.index(jd_level)
        except ValueError:
            return 70  # Unknown level — generous neutral

        try:
            candidate_idx = _SENIORITY_LADDER.index(candidate_level)
        except ValueError:
            return 70

        diff = abs(jd_idx - candidate_idx)
        if diff == 0:
            return 100
        elif diff == 1:
            return 80
        elif diff == 2:
            return 55
        elif diff == 3:
            return 30
        else:
            return 10

    def _score_culture(
        self, parsed_jd: dict, profile: IdentityProfile, job: DiscoveredJobSchema
    ) -> int:
        """Score culture alignment: startup/enterprise + remote preference."""
        score = 60  # default neutral

        # Startup vs enterprise alignment
        jd_type = parsed_jd.get("culture_signals", {}).get("startup_vs_enterprise", "")
        candidate_pref = profile.culture_signals.get("startup_vs_enterprise", "both")
        if jd_type and candidate_pref != "both":
            if jd_type == candidate_pref:
                score += 20
            else:
                score -= 20

        # Remote alignment
        jd_remote = parsed_jd.get("remote_type", "")
        candidate_remote = profile.culture_signals.get("remote_preference", "flexible")
        if jd_remote and candidate_remote != "flexible":
            if jd_remote == candidate_remote:
                score += 20
            elif jd_remote == "onsite" and candidate_remote == "remote":
                score -= 30
            else:
                score -= 10

        return max(0, min(100, score))

    def _score_industry(self, parsed_jd: dict, profile: IdentityProfile) -> int:
        """Score how well the job's industries align with the candidate's domain expertise."""
        jd_industries = {i.lower() for i in parsed_jd.get("industries", [])}
        candidate_domains = {d.lower() for d in profile.domain_expertise}

        if not jd_industries:
            return 60

        overlap = len(jd_industries & candidate_domains)
        if overlap >= 2:
            return 100
        elif overlap == 1:
            return 75
        else:
            return 35

    def _score_growth(self, parsed_jd: dict, profile: IdentityProfile) -> int:
        """Score whether this role expands the candidate's trajectory."""
        indicators = parsed_jd.get("growth_indicators", [])
        growth_keywords = {
            "build from scratch", "greenfield", "founding", "new team",
            "technical strategy", "shape the", "lead the", "define the",
            "architect", "platform", "0 to 1",
        }

        indicator_text = " ".join(indicators).lower()
        matches = sum(1 for kw in growth_keywords if kw in indicator_text)

        if matches >= 3:
            return 90
        elif matches >= 1:
            return 70
        else:
            return 50

    def _score_compensation(self, parsed_jd: dict, profile: IdentityProfile) -> int:
        """Score comp alignment — generous when comp isn't mentioned (common for senior roles)."""
        comp_str = parsed_jd.get("comp_mentioned")
        if not comp_str:
            return 75  # No comp listed is common for senior/exec roles — assume competitive

        # Extract numbers from comp string
        numbers = re.findall(r"\d[\d,]*", comp_str.replace(",", ""))
        if not numbers:
            return 70

        amounts = [int(n) for n in numbers if len(n) <= 7]  # filter out noise
        if not amounts:
            return 70

        jd_max = max(amounts)
        # Normalize to annual if looks like monthly (< 20000)
        if jd_max < 20_000:
            jd_max *= 12

        candidate_min = profile.compensation_band.get("min", 0)
        if candidate_min == 0:
            return 70

        if jd_max >= candidate_min:
            return 100
        elif jd_max >= candidate_min * 0.85:
            return 70
        elif jd_max >= candidate_min * 0.70:
            return 40
        else:
            return 15

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _generate_reasoning(
        self,
        job: DiscoveredJobSchema,
        profile: IdentityProfile,
        scores: ScoreBreakdown,
        composite: int,
    ) -> str:
        """Generate a 2-sentence human-readable reasoning string via Claude."""
        prompt = f"""You are writing a brief explanation for why a job matches a candidate in a talent agent digest.

Candidate archetype tags: {", ".join(profile.archetype_tags)}
Job: {job.title} at {job.company} ({job.location or "location TBD"})
Composite score: {composite}/100

Score breakdown:
- Technical match: {scores.technical_match}/100
- Level match: {scores.level_match}/100
- Culture match: {scores.culture_match}/100
- Industry match: {scores.industry_match}/100
- Growth potential: {scores.growth_potential}/100
- Compensation match: {scores.compensation_match}/100

Write exactly 2 sentences: one sentence on why this is a strong match, one on the key consideration or risk.
Be specific. Do not use filler phrases like "This role offers" or "This position presents". Start with the substance.
Return only the 2 sentences, no other text."""

        response = await self._claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
