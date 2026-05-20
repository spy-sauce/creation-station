# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Archetype Generator — expands an IdentityProfileSchema into a SearchManifestSchema.

Takes the abstract role archetypes and converts them into:
  - Specific job title search strings
  - Title variants (Head of AI → [VP AI, Director of AI, AI Lead, ...])
  - Search keyword combinations
  - Explicit exclusions

The SearchManifestSchema is the crawler's search instructions.
"""

import structlog

from backend.agents.discovery.schemas import IdentityProfileSchema, SearchManifestSchema

logger = structlog.get_logger(__name__)

# Title variant expansion rules — maps archetype patterns to search variants
_TITLE_VARIANTS: dict[str, list[str]] = {
    "head of ai": ["Head of AI", "Director of AI", "VP of AI", "AI Lead", "AI Director"],
    "principal engineer": [
        "Principal Engineer",
        "Staff Engineer",
        "Principal Software Engineer",
        "Distinguished Engineer",
    ],
    "vp engineering": [
        "VP Engineering",
        "VP of Engineering",
        "Head of Engineering",
        "Director of Engineering",
    ],
    "technical co-founder": [
        "Technical Co-Founder",
        "CTO",
        "Founding Engineer",
        "Head of Technology",
    ],
    "developer advocate": [
        "Developer Advocate",
        "Developer Relations",
        "DevRel Engineer",
        "Developer Experience",
    ],
    "ai architect": ["AI Architect", "ML Architect", "AI/ML Architect", "Principal AI Engineer"],
    "engineering manager": [
        "Engineering Manager",
        "Director of Engineering",
        "Head of Engineering",
    ],
    "cto": ["CTO", "Chief Technology Officer", "VP Engineering", "Head of Technology"],
    "product engineer": [
        "Product Engineer",
        "Full Stack Engineer",
        "Software Engineer - Product",
    ],
    "ai creative director": [
        "AI Creative Director",
        "Creative Technologist",
        "Director of Creative Technology",
    ],
    "technical pm": [
        "Technical Product Manager",
        "Senior PM - Platform",
        "Group Product Manager - AI",
    ],
    "fractional cto": ["Fractional CTO", "CTO Advisor", "Technology Advisor", "Interim CTO"],
    "solutions architect": [
        "Solutions Architect",
        "Principal Solutions Architect",
        "Enterprise Architect",
    ],
    "platform engineer": [
        "Platform Engineer",
        "Infrastructure Engineer",
        "Staff Platform Engineer",
    ],
}


class ArchetypeGenerator:
    """
    Converts an IdentityProfileSchema into a SearchManifestSchema for the crawler.

    No external API calls — all logic is local expansion rules + profile data.
    """

    def expand(
        self,
        profile: IdentityProfileSchema,
        candidate_excluded: dict[str, list[str]],
    ) -> SearchManifestSchema:
        """
        Build a SearchManifestSchema from an IdentityProfileSchema.

        Args:
            profile: Candidate's identity profile
            candidate_excluded: {titles: [...], companies: [...], industries: [...]}

        Returns:
            SearchManifestSchema with search targets and exclusions
        """
        logger.info("archetype_generator.expanding")

        target_titles = self._extract_target_titles(profile.archetypes)
        keywords = self._build_keywords(profile, target_titles)

        manifest = SearchManifestSchema(
            target_titles=target_titles,
            keywords=keywords,
            excluded_titles=candidate_excluded.get("titles", []),
            excluded_companies=candidate_excluded.get("companies", []),
            excluded_industries=candidate_excluded.get("industries", []),
            location_filters=[],  # TODO: derive from profile if needed
            remote_preference=profile.signals.get("remote_preference", "flexible"),
            min_compensation=None,  # Passed separately from candidate
        )

        logger.info(
            "archetype_generator.manifest_built",
            title_count=len(target_titles),
            keyword_count=len(keywords),
        )
        return manifest

    def _extract_target_titles(self, archetypes: list[str]) -> list[str]:
        """
        Convert role archetype strings into specific job title search targets.

        For each archetype, emit the archetype itself plus any known variants.
        Deduplicate while preserving order.
        """
        seen: set[str] = set()
        titles: list[str] = []

        for archetype in archetypes:
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

    def _build_keywords(
        self, profile: IdentityProfileSchema, target_titles: list[str]
    ) -> list[str]:
        """
        Build a flat keyword list for job board search queries.

        Combines title variants with skill signals.
        """
        keywords: set[str] = set()

        # Add top 15 titles
        for title in target_titles[:15]:
            keywords.add(title)

        # Add technical skills as qualifier terms (top 10)
        for skill in profile.technical_skills[:10]:
            keywords.add(skill)

        # Add industry experience
        for industry in profile.industry_experience[:5]:
            keywords.add(industry)

        return list(keywords)
