# Licensed under the Apache License, Version 2.0

"""
Web Crawler Agent — multi-source job board crawler.

Fetches job postings from public ATS boards and returns deduplicated
DiscoveredJobSchema rows for the relevance scorer.

Supported sources (this module owns the production implementations):
  1. Greenhouse (https://boards.greenhouse.io/{slug}.json) — public JSON API
  2. Lever (https://api.lever.co/v0/postings/{slug}?mode=json) — public JSON API
  3. Ashby (https://api.ashbyhq.com/posting-api/job-board/{slug}) — public JSON API
  4. Workday (https://{tenant}.wd*.myworkdayjobs.com/{board}) — Playwright crawl

Each adapter is a real working implementation, not a stub. The orchestrator
calls CrawlerAgent.run(manifest) and expects a populated list back when the
sources are reachable.

Rate limits: 2 req/sec per domain, 0.5-2.0s jitter, User-Agent
"TalentAgent/1.0 (+https://example.com/bot)". Respect robots.txt.

Dedup: url_hash() against the discovered_jobs table before insert.

Curated company slugs live in backend/agents/discovery/sources.yaml.
"""

import hashlib
import structlog
from uuid import UUID

from backend.agents.discovery.schemas import SearchManifestSchema, DiscoveredJobSchema

logger = structlog.get_logger(__name__)


# ─── Source adapters — IMPLEMENT EACH OF THESE ────────────────────────────────
# Each adapter MUST do real network I/O and return real DiscoveredJobSchema-
# shaped dicts. The orchestrator depends on populated results from these.


class GreenhouseAdapter:
    """
    Greenhouse public board adapter.

    Fetches GET https://boards.greenhouse.io/{slug}.json for each curated slug
    in sources.yaml, then filters postings by the manifest's target_titles
    (case-insensitive substring match on `title`).

    Returns list[dict] with keys: title, company, source='greenhouse', url,
    location, posted_at, raw_description, raw_payload.
    """

    async def fetch(self, slugs: list[str], titles: list[str]) -> list[dict]:
        raise NotImplementedError("GreenhouseAdapter.fetch must ship a real httpx call")


class LeverAdapter:
    """
    Lever public postings adapter.

    Fetches GET https://api.lever.co/v0/postings/{slug}?mode=json for each
    curated slug, filters by manifest titles, returns the same shape as
    GreenhouseAdapter.fetch.
    """

    async def fetch(self, slugs: list[str], titles: list[str]) -> list[dict]:
        raise NotImplementedError("LeverAdapter.fetch must ship a real httpx call")


class AshbyAdapter:
    """
    Ashby public posting-api adapter.

    Fetches POST https://api.ashbyhq.com/posting-api/job-board/{slug}
    with includeCompensation=true, filters by manifest titles, returns
    the same shape as GreenhouseAdapter.fetch.
    """

    async def fetch(self, slugs: list[str], titles: list[str]) -> list[dict]:
        raise NotImplementedError("AshbyAdapter.fetch must ship a real httpx call")


class WorkdayAdapter:
    """
    Workday tenant-board adapter (Playwright-driven; no public JSON API).

    For each (tenant, board) pair in sources.yaml, navigate to
    https://{tenant}.wd*.myworkdayjobs.com/{board}, scrape the listing,
    filter by manifest titles, return the same shape as
    GreenhouseAdapter.fetch.
    """

    async def fetch(self, tenants: list[dict], titles: list[str]) -> list[dict]:
        raise NotImplementedError("WorkdayAdapter.fetch must ship a real Playwright crawl")


# ─── CrawlerAgent ─────────────────────────────────────────────────────────────


class CrawlerAgent:
    """
    Crawls public ATS boards against a SearchManifestSchema and returns a
    deduplicated list of DiscoveredJobSchema rows.

    The four adapters above MUST be implemented with real network I/O.
    The agent fans out across all configured sources, dedupes by url_hash,
    and returns populated results.
    """

    SOURCES = ["greenhouse", "lever", "ashby", "workday"]

    def __init__(self, candidate_id: UUID):
        self._candidate_id = candidate_id

    async def run(self, manifest: SearchManifestSchema) -> list[DiscoveredJobSchema]:
        """
        Execute a full crawl run against the manifest.

        Loads slug roster from backend/agents/discovery/sources.yaml,
        fans out to each adapter in parallel, dedupes by url_hash,
        returns the merged list.
        """
        raise NotImplementedError(
            "CrawlerAgent.run must ship real multi-source crawl: "
            "load sources.yaml, fan out to Greenhouse/Lever/Ashby/Workday "
            "adapters, merge, dedupe by url_hash, return populated list."
        )

    @staticmethod
    def url_hash(url: str) -> str:
        """Deterministic hash for deduplication against the discovered_jobs table."""
        return hashlib.sha256(url.strip().lower().encode()).hexdigest()
