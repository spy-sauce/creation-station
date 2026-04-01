# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Contact Finder — finds the right person to send the cold outreach to.

Strategy (in priority order):
  1. Check if JD explicitly names a hiring manager
  2. Hunter.io email pattern discovery for the domain
  3. Construct likely email from name + domain pattern
  4. Fall back to generic addresses (jobs@, recruiting@, engineering@)

Never sources emails from data brokers. Marks contacts as UNVERIFIED by default.
"""

import re
from typing import Optional

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.application.schemas import (
    CompanyIntelSchema,
    ContactSchema,
    ParsedJDSchema,
)
from backend.config import settings
from backend.models.application import Contact as ContactORM

logger = structlog.get_logger(__name__)

# Common generic fallback patterns
_GENERIC_EMAILS = ["jobs", "recruiting", "careers", "engineering", "talent", "hr"]

# Common email format patterns to try
_EMAIL_PATTERNS = [
    "{first}.{last}@{domain}",
    "{first}{last}@{domain}",
    "{first}@{domain}",
    "{f}{last}@{domain}",
]

_REQUEST_HEADERS = {
    "User-Agent": "VibeSpaceTalentAgent/1.0 (contact research; contact spy@seanyoung.biz)"
}


class ContactFinder:
    """
    Finds the right person to receive a cold outreach email.

    Tries specific contacts first, falls back to generic company addresses.
    All contacts start as UNVERIFIED — confidence is derived from source quality.
    """

    def __init__(self, db: AsyncSession):
        self._db = db

    async def find(
        self,
        intel: CompanyIntelSchema,
        parsed_jd: ParsedJDSchema,
    ) -> ContactSchema:
        """
        Find the best available contact for this role.

        Args:
            intel: Company research from CompanyIntelAgent
            parsed_jd: Parsed job description (may name hiring manager)

        Returns:
            ContactSchema with best available email and confidence level
        """
        log = logger.bind(company=intel.company_name)
        domain = intel.domain

        # 1. Check JD for explicitly named contact
        jd_contact = self._extract_jd_contact(parsed_jd, domain)
        if jd_contact:
            log.info("contact_finder.found", source="jd_explicit", confidence=jd_contact.confidence)
            await self._persist(jd_contact, intel)
            return jd_contact

        # 2. Try Hunter.io if API key is configured
        if settings.hunter_api_key and domain:
            hunter_contact = await self._try_hunter(domain, intel.company_name)
            if hunter_contact:
                log.info("contact_finder.found", source="hunter", confidence=hunter_contact.confidence)
                await self._persist(hunter_contact, intel)
                return hunter_contact

        # 3. Construct generic fallback
        fallback = self._build_fallback(domain, intel.company_name)
        log.info("contact_finder.fallback", domain=domain)
        await self._persist(fallback, intel)
        return fallback

    def _extract_jd_contact(
        self, parsed_jd: ParsedJDSchema, domain: Optional[str]
    ) -> Optional[ContactSchema]:
        """
        Look for explicit contact information in JD application instructions.

        Some JDs say "apply to john.smith@company.com" or "ask for Jane in Engineering."
        """
        if not parsed_jd.application_instructions:
            return None

        text = parsed_jd.application_instructions
        # Look for email addresses in instructions
        email_match = re.search(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", text)
        if email_match:
            email = email_match.group(0)
            return ContactSchema(
                email=email,
                source="jd_instructions",
                confidence="HIGH",
                fallback_email=f"recruiting@{domain}" if domain else None,
            )
        return None

    async def _try_hunter(self, domain: str, company_name: str) -> Optional[ContactSchema]:
        """
        Use Hunter.io domain search to find engineering contacts.

        Hunter.io returns verified email patterns and known contacts for a domain.
        """
        try:
            async with httpx.AsyncClient(headers=_REQUEST_HEADERS, timeout=10.0) as client:
                response = await client.get(
                    "https://api.hunter.io/v2/domain-search",
                    params={
                        "domain": domain,
                        "api_key": settings.hunter_api_key,
                        "type": "personal",
                        "limit": 10,
                    },
                )
                if response.status_code != 200:
                    return None

                data = response.json().get("data", {})
                emails = data.get("emails", [])

                # Find engineering-relevant contacts
                priority_titles = [
                    "engineering manager", "head of engineering", "vp engineering",
                    "cto", "director of engineering", "tech lead", "engineering lead",
                ]
                for contact in emails:
                    title = (contact.get("position") or "").lower()
                    if any(pt in title for pt in priority_titles):
                        return ContactSchema(
                            name=f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip(),
                            title=contact.get("position"),
                            email=contact.get("value"),
                            linkedin_url=contact.get("linkedin"),
                            confidence="HIGH" if contact.get("confidence", 0) > 80 else "MEDIUM",
                            source="hunter.io",
                            fallback_email=f"recruiting@{domain}",
                        )

                # No eng manager found — return pattern info for manual construction
                pattern = data.get("pattern")
                if pattern and emails:
                    first_contact = emails[0]
                    return ContactSchema(
                        name=f"{first_contact.get('first_name', '')} {first_contact.get('last_name', '')}".strip(),
                        title=first_contact.get("position"),
                        email=first_contact.get("value"),
                        confidence="MEDIUM",
                        source="hunter.io",
                        fallback_email=f"recruiting@{domain}",
                    )

        except Exception as e:
            logger.warning("contact_finder.hunter_failed", domain=domain, error=str(e))

        return None

    def _build_fallback(self, domain: Optional[str], company_name: str) -> ContactSchema:
        """Build a generic fallback contact when no specific person can be found."""
        if not domain:
            return ContactSchema(
                confidence="LOW",
                source="fallback",
            )

        # Try common generic addresses in priority order
        primary = f"jobs@{domain}"
        fallback = f"recruiting@{domain}"

        return ContactSchema(
            email=primary,
            confidence="LOW",
            source="generic_fallback",
            fallback_email=fallback,
        )

    async def _persist(self, contact: ContactSchema, intel: CompanyIntelSchema) -> None:
        """Store the contact in PostgreSQL for reuse if same company is targeted again."""
        from sqlalchemy import select
        from backend.models.application import CompanyIntel as CompanyIntelORM

        # Look up company_intel_id
        result = await self._db.execute(
            select(CompanyIntelORM)
            .where(CompanyIntelORM.company_name == intel.company_name)
            .order_by(CompanyIntelORM.created_at.desc())
            .limit(1)
        )
        company_orm = result.scalar_one_or_none()

        orm = ContactORM(
            company_intel_id=company_orm.id if company_orm else None,
            name=contact.name,
            title=contact.title,
            email=contact.email,
            linkedin_url=contact.linkedin_url,
            confidence=contact.confidence,
            source=contact.source,
            fallback_email=contact.fallback_email,
        )
        self._db.add(orm)
        await self._db.commit()
