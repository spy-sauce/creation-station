# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Company Intel Agent — researches a company to give the outreach composer real context.

Sources (in priority order):
  1. Company website (/about, /team, /engineering, /blog)
  2. GitHub org (public repos, activity)
  3. Crunchbase (funding stage — public pages only)
  4. Google News (last 30 days)
  5. Engineering blog

Cache: Redis TTL 7 days + PostgreSQL for persistence.
Never re-scrapes the same company within a week.
"""

import asyncio
import json
import re
from datetime import datetime, timezone, timedelta
from uuid import UUID

import httpx
import redis.asyncio as aioredis
import structlog
from anthropic import AsyncAnthropic
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.agents.application.schemas import CompanyIntelSchema
from backend.models.application import CompanyIntel as CompanyIntelORM

logger = structlog.get_logger(__name__)

_CACHE_TTL_SECONDS = 86_400 * 7  # 7 days
_REQUEST_HEADERS = {
    "User-Agent": "VibeSpaceTalentAgent/1.0 (talent research bot; contact spy@seanyoung.biz)"
}


def _cache_key(company_name: str) -> str:
    return f"company_intel:{company_name.lower().replace(' ', '_')}"


class CompanyIntelAgent:
    """
    Researches a company and synthesises findings into a CompanyIntelSchema.

    Checks Redis + PostgreSQL cache before scraping. Synthesises via Claude.
    """

    def __init__(
        self,
        db: AsyncSession,
        redis_client: aioredis.Redis,
        anthropic_client: AsyncAnthropic,
    ):
        self._db = db
        self._redis = redis_client
        self._claude = anthropic_client

    async def research(self, company_name: str, company_url: str | None = None) -> CompanyIntelSchema:
        """
        Research a company — from cache or by scraping.

        Args:
            company_name: The company name to research
            company_url: Optional direct URL to the company website

        Returns:
            CompanyIntelSchema with synthesised intelligence
        """
        log = logger.bind(company=company_name)

        # Check Redis cache first
        cached_raw = await self._redis.get(_cache_key(company_name))
        if cached_raw:
            log.info("company_intel.cache_hit", source="redis")
            return CompanyIntelSchema.model_validate_json(cached_raw)

        # Check PostgreSQL cache
        db_cached = await self._get_from_db(company_name)
        if db_cached:
            log.info("company_intel.cache_hit", source="postgres")
            await self._redis.setex(_cache_key(company_name), _CACHE_TTL_SECONDS, db_cached.model_dump_json())
            return db_cached

        # Scrape and synthesise
        log.info("company_intel.researching")
        intel = await self._scrape_and_synthesise(company_name, company_url)

        await self._persist(intel)
        await self._redis.setex(_cache_key(company_name), _CACHE_TTL_SECONDS, intel.model_dump_json())

        log.info("company_intel.complete", has_news=bool(intel.recent_news))
        return intel

    async def _get_from_db(self, company_name: str) -> CompanyIntelSchema | None:
        """Return cached intel from PostgreSQL if not expired."""
        result = await self._db.execute(
            select(CompanyIntelORM)
            .where(CompanyIntelORM.company_name == company_name)
            .order_by(CompanyIntelORM.created_at.desc())
            .limit(1)
        )
        orm = result.scalar_one_or_none()
        if not orm:
            return None
        if orm.cache_expires_at and orm.cache_expires_at < datetime.now(timezone.utc):
            return None
        return CompanyIntelSchema(
            company_name=orm.company_name,
            domain=orm.domain,
            about=orm.about,
            recent_news=orm.recent_news,
            tech_stack=orm.tech_stack or [],
            engineering_culture=orm.engineering_culture,
            glassdoor_signals=orm.glassdoor_signals,
            growth_stage=orm.growth_stage,
            team_size=orm.team_size,
            notable_facts=orm.notable_facts,
            cache_age=orm.created_at,
        )

    async def _scrape_and_synthesise(
        self, company_name: str, company_url: str | None
    ) -> CompanyIntelSchema:
        """Scrape available sources and synthesise with Claude."""
        raw_data: dict[str, str] = {}

        async with httpx.AsyncClient(
            headers=_REQUEST_HEADERS,
            follow_redirects=True,
            timeout=10.0,
        ) as client:
            # Scrape company website if URL available
            if company_url:
                raw_data["website"] = await self._scrape_url(client, company_url)
                about_url = company_url.rstrip("/") + "/about"
                raw_data["about_page"] = await self._scrape_url(client, about_url)

            # Search Google News for recent articles
            raw_data["news"] = await self._search_news(client, company_name)

        return await self._synthesise(company_name, company_url, raw_data)

    async def _scrape_url(self, client: httpx.AsyncClient, url: str) -> str:
        """Fetch and extract text content from a URL."""
        try:
            await asyncio.sleep(0.5 + 0.5)  # Respectful delay
            response = await client.get(url)
            if response.status_code != 200:
                return ""
            soup = BeautifulSoup(response.text, "html.parser")
            # Remove nav, footer, scripts
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            return soup.get_text(separator=" ", strip=True)[:3000]
        except Exception as e:
            logger.warning("company_intel.scrape_failed", url=url, error=str(e))
            return ""

    async def _search_news(self, client: httpx.AsyncClient, company_name: str) -> str:
        """Search for recent news about the company via Google News RSS."""
        try:
            encoded = company_name.replace(" ", "+")
            url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
            await asyncio.sleep(1.0)
            response = await client.get(url)
            if response.status_code != 200:
                return ""
            # Extract headlines from RSS
            soup = BeautifulSoup(response.text, "xml")
            items = soup.find_all("item")[:10]
            headlines = []
            for item in items:
                title = item.find("title")
                pub_date = item.find("pubDate")
                if title:
                    headlines.append(f"{title.text} ({pub_date.text if pub_date else 'recent'})")
            return "\n".join(headlines)
        except Exception as e:
            logger.warning("company_intel.news_failed", company=company_name, error=str(e))
            return ""

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _synthesise(
        self, company_name: str, company_url: str | None, raw_data: dict[str, str]
    ) -> CompanyIntelSchema:
        """Use Claude to synthesise raw scraped data into structured intel."""
        context_parts = []
        if raw_data.get("website"):
            context_parts.append(f"WEBSITE:\n{raw_data['website'][:1500]}")
        if raw_data.get("about_page"):
            context_parts.append(f"ABOUT PAGE:\n{raw_data['about_page'][:1000]}")
        if raw_data.get("news"):
            context_parts.append(f"RECENT NEWS:\n{raw_data['news']}")

        context = "\n\n".join(context_parts) if context_parts else "No data available — limited public footprint."

        prompt = f"""You are researching a company for a job application. Synthesise the available data.

Company: {company_name}
Website: {company_url or "unknown"}

RAW DATA:
{context}

Return ONLY valid JSON:
{{
  "about": "<2-3 sentence summary of what this company does>",
  "recent_news": "<significant news from last 30 days, or null>",
  "tech_stack": ["<technology>"],
  "engineering_culture": "<signals from public content about eng culture>",
  "growth_stage": "<seed|series-a|series-b|series-c|growth|public|unknown>",
  "team_size": "<estimate like '50-200' or 'unknown'>",
  "notable_facts": "<the single most specific and interesting hook about this company — something a human would reference in an email opening>"
}}"""

        response = await self._claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text.strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            data = json.loads(match.group()) if match else {}

        domain = None
        if company_url:
            match = re.search(r"https?://(?:www\.)?([^/]+)", company_url)
            domain = match.group(1) if match else None

        return CompanyIntelSchema(
            company_name=company_name,
            domain=domain,
            about=data.get("about"),
            recent_news=data.get("recent_news"),
            tech_stack=data.get("tech_stack", []),
            engineering_culture=data.get("engineering_culture"),
            growth_stage=data.get("growth_stage"),
            team_size=data.get("team_size"),
            notable_facts=data.get("notable_facts"),
            cache_age=datetime.now(timezone.utc),
        )

    async def _persist(self, intel: CompanyIntelSchema) -> None:
        """Store company intel in PostgreSQL."""
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        orm = CompanyIntelORM(
            company_name=intel.company_name,
            domain=intel.domain,
            about=intel.about,
            recent_news=intel.recent_news,
            tech_stack=intel.tech_stack,
            engineering_culture=intel.engineering_culture,
            growth_stage=intel.growth_stage,
            team_size=intel.team_size,
            notable_facts=intel.notable_facts,
            cache_expires_at=expires_at,
        )
        self._db.add(orm)
        await self._db.commit()
