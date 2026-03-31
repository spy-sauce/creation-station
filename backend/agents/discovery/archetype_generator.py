# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Archetype Generator — expands an IdentityProfile into a concrete search manifest.

Takes the abstract role archetypes and converts them into:
  - Specific job title search strings
  - Title variants (Head of AI → [VP AI, Director of AI, AI Lead, ...])
  - Target company profile (stage, size, tech stack signals)
  - Ranked target industries
  - Search keyword combinations
  - Explicit exclusions

The ArchetypeManifest is the crawler's search instructions.
"""

import structlog
from uuid import UUID
from backend.agents.discovery.schemas import IdentityProfile, ArchetypeManifest, TargetCompanyProfile

logger = structlog.get_logger(__name__)

# Title variant expansion rules — maps archetype patterns to search variants
_TITLE_VARIANTS: dict[str, list[str]] = {
    "head of ai": ["Head of AI", "Director of AI", "VP of AI", "AI Lead", "AI Director"],
    "principal engineer": ["Principal Engineer", "Staff Engineer", "Principal Software Engineer", "Distinguished Engineer"],
    "vp engineering": ["VP Engineering", "VP of Engineering", "Head of Engineering", "Director of Engineering"],
    "technical co-founder": ["Technical Co-Founder", "CTO", "Founding Engineer", "Head of Technology"],
    "developer advocate": ["Developer Advocate", "Developer Relations", "DevRel Engineer", "Developer Experience"],
    "ai architect": ["AI Architect", "ML Architect", "AI/ML Architect", "Principal AI Engineer"],
    "engineering manager": ["Engineering Manager", "Director of Engineering", "Head of Engineering"],
    "cto": ["CTO", "Chief Technology Officer", "VP Engineering", "Head of Technology"],
    "product engineer": ["Product Engineer", "Full Stack Engineer", "Software Engineer - Product"],
    "ai creative director": ["AI Creative Director", "Creative Technologist", "Director of Creative Technology"],
    "technical pm": ["Technical Product Manager", "Senior PM - Platform", "Group Product Manager - AI"],
    "fractional cto": ["Fractional CTO", "CTO Advisor", "Technology Advisor", "Interim CTO"],
    "solutions architect": ["Solutions Architect", "Principal Solutions Architect", "Enterprise Architect"],
    "platform engineer": ["Platform Engineer", "Infrastructure Engineer", "Staff Platform Engineer"],
}

# Company stage → target profile mappings
_STAGE_PROFILES = {
    "startup": ["seed", "series-a", "series-b"],
    "growth": ["series-b", "series-c", "growth"],
    "public": ["public"],
    "enterprise": ["growth", "public"],
    "both": ["series-a", "series-b", "series-c", "growth", "public"],
}

# Culture signal → size range mappings
_SIZE_BY_STAGE = {
    "seed": "1-30",
    "series-a": "10-100",
    "series-b": "50-300",
    "series-c": "100-1000",
    "growth": "200-2000",
    "public": "500+",
}


class ArchetypeGenerator:
    """
    Converts an IdentityProfile into an ArchetypeManifest for the crawler.

    No external API calls — all logic is local expansion rules + profile data.
    """

    def expand(self, profile: IdentityProfile, candidate_excluded: dict[str, list[str]]) -> ArchetypeManifest:
        """
        Build a full ArchetypeManifest from an IdentityProfile.

        Args:
            profile: Candidate's identity profile
            candidate_excluded: {companies: [...], industries: [...]} from candidate settings

        Returns:
            ArchetypeManifest with search targets, title variants, and exclusions
        """
        logger.info("archetype_generator.expanding", candidate_id=str(profile.candidate_id))

        target_titles = self._extract_target_titles(profile.role_expansion)
        title_variants = self._build_title_variants(profile.role_expansion)
        company_profile = self._build_company_profile(profile)
        target_industries = self._rank_industries(profile)
        keywords = self._build_keywords(profile, target_titles)

        manifest = ArchetypeManifest(
            candidate_id=profile.candidate_id,
            target_titles=target_titles,
            title_variants=title_variants,
            target_company_profile=company_profile,
            target_industries=target_industries,
            keywords=keywords,
            exclusions=candidate_excluded,
        )

        logger.info(
            "archetype_generator.manifest_built",
            candidate_id=str(profile.candidate_id),
            title_count=len(target_titles),
            keyword_count=len(keywords),
        )
        return manifest

    def _extract_target_titles(self, role_expansion: list[str]) -> list[str]:
        """
        Convert role archetype strings into specific job title search targets.

        For each archetype, emit the archetype itself plus any known variants.
        Deduplicate while preserving order.
        """
        seen: set[str] = set()
        titles: list[str] = []

        for archetype in role_expansion:
            # Try to find a matching variant group
            matched = False
            for pattern, variants in _TITLE_VARIANTS.items():
                if pattern in archetype.lower():
                    for v in variants:
                        if v not in seen:
                            titles.append(v)
                            seen.add(v)
                    matched = True
                    break

            if not matched and archetype not in seen:
                titles.append(archetype)
                seen.add(archetype)

        return titles

    def _build_title_variants(self, role_expansion: list[str]) -> dict[str, list[str]]:
        """Map each role archetype to its title search variants."""
        variants: dict[str, list[str]] = {}
        for archetype in role_expansion:
            for pattern, title_list in _TITLE_VARIANTS.items():
                if pattern in archetype.lower():
                    variants[archetype] = title_list
                    break
            else:
                variants[archetype] = [archetype]
        return variants

    def _build_company_profile(self, profile: IdentityProfile) -> TargetCompanyProfile:
        """Derive a target company profile from culture signals and identity."""
        startup_vs_enterprise = profile.culture_signals.get("startup_vs_enterprise", "both")
        stages = _STAGE_PROFILES.get(startup_vs_enterprise, _STAGE_PROFILES["both"])

        # Size range: use the widest range across applicable stages
        sizes = [_SIZE_BY_STAGE.get(s, "50-500") for s in stages]
        # Pick first and last to get min–max range
        size_range = f"{sizes[0].split('-')[0]}-{sizes[-1].split('-')[-1]}"

        # Tech signals from top skills
        top_skills = sorted(
            profile.technical_skills.items(), key=lambda x: x[1], reverse=True
        )[:10]
        tech_signals = [skill for skill, _ in top_skills]

        return TargetCompanyProfile(
            industries=profile.domain_expertise[:5],
            stages=stages,
            size_range=size_range,
            tech_signals=tech_signals,
            culture_signals=list(profile.culture_signals.values()),
        )

    def _rank_industries(self, profile: IdentityProfile) -> list[str]:
        """Rank target industries by fit — domain expertise order is already Claude-ranked."""
        return profile.domain_expertise

    def _build_keywords(self, profile: IdentityProfile, target_titles: list[str]) -> list[str]:
        """
        Build a flat keyword list for job board search queries.

        Combines title variants with skill signals and archetype tags.
        """
        keywords: set[str] = set()

        # Add top 15 titles
        for title in target_titles[:15]:
            keywords.add(title)

        # Add archetype tags as search modifiers
        for tag in profile.archetype_tags:
            keywords.add(tag.replace("-", " "))

        # Add top 5 skills as qualifier terms
        top_skills = sorted(
            profile.technical_skills.items(), key=lambda x: x[1], reverse=True
        )[:5]
        for skill, _ in top_skills:
            keywords.add(skill)

        return list(keywords)
