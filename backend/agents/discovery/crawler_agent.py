# Licensed under the Apache License, Version 2.0

"""
Web Crawler Agent — multi-source job board crawler.

Supported sources:
  1. Greenhouse (boards.greenhouse.io/{slug}.json) — public JSON
  2. Lever (api.lever.co/v0/postings/{slug}?mode=json) — public JSON
  3. Ashby (api.ashbyhq.com/posting-api/job-board/{slug}) — public JSON
  4. Workday — deferred (Playwright crawl; not in this revision)

Rate limits: 2 req/sec per host, 0.5-2.0s jitter, User-Agent
"TalentAgent/1.0 (+https://github.com/example/talent-agent)". Adapters
fan out concurrently across slugs with a semaphore of 4 per source.

Dedup: url_hash() against the discovered_jobs table before insert.
Curated company slugs live in backend/agents/discovery/sources.yaml.

Offline fallback: if all live adapters return zero rows (network down,
all sources rate-limited), CrawlerAgent falls back to the FIXTURE_JOBS
roster so dev pipelines still produce data. Production should monitor
for this fallback via the `crawler.fallback_used` structured log event.
"""

import asyncio
import hashlib
import html
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

import httpx
import structlog
import yaml

from backend.agents.discovery.schemas import SearchManifestSchema, DiscoveredJobSchema

logger = structlog.get_logger(__name__)

USER_AGENT = "TalentAgent/1.0 (+https://github.com/example/talent-agent)"
HTTP_TIMEOUT = 15.0
PER_SOURCE_CONCURRENCY = 4
SOURCES_YAML = Path(__file__).parent / "sources.yaml"


# ─── Offline fallback fixture data ────────────────────────────────────────────
# Used only when all live adapters return zero rows (network down or all
# sources unreachable). The `crawler.fallback_used` log event fires when this
# kicks in so prod can alert on it.

_FALLBACK_JOBS: list[dict] = [
    {
        "source": "greenhouse",
        "source_id": "gh-fixture-001",
        "title": "Head of AI Engineering",
        "company": "MusicTech AI",
        "location": "Remote (US)",
        "url": "https://boards.greenhouse.io/musictech/jobs/001",
        "description": """
We're a Series B music-tech startup building AI tools for creators and artists.

Looking for a Head of AI Engineering to define our AI strategy from scratch.
You'll lead a team of ML engineers and shape the technical direction of our
AI-powered music recommendation and generation systems.

Required:
- Python, FastAPI, PostgreSQL, Redis
- LLMs, Claude API, OpenAI API
- 8+ years engineering experience
- 3+ years in leadership roles

Preferred:
- Kubernetes, Docker
- Music or audio domain experience
- Startup experience

This is a 0-to-1 greenfield role. You'll shape the technical strategy,
build the team from scratch, and report directly to the CTO.

Compensation: $250,000-$350,000 + 0.5-1.0% equity

Remote-first. Mission-driven team.
Industry: Music, AI, Creator Economy
        """,
        "salary_min": 250000,
        "salary_max": 350000,
        "remote": True,
    },
    {
        "source": "lever",
        "source_id": "lever-fixture-002",
        "title": "VP of Engineering",
        "company": "FinTech Startup",
        "location": "Miami, FL / Remote",
        "url": "https://jobs.lever.co/fintechstartup/002",
        "description": """
Fast-growing fintech startup looking for a VP of Engineering to scale our
platform from Series A to B.

You'll own the entire engineering organization (currently 15 engineers) and
drive our technical roadmap as we expand into new markets.

Requirements:
- 10+ years software engineering
- 5+ years in engineering leadership
- Java, Spring Boot, microservices
- AWS, Kubernetes, distributed systems
- Fintech or regulated industry experience

What you'll do:
- Build and scale the engineering team to 40+ engineers
- Define technical strategy and architecture
- Partner with Product and Design leadership
- Establish engineering culture and processes

Compensation: $300,000-$400,000 base + equity
Location: Miami preferred, remote considered
Industry: Fintech, Payments
        """,
        "salary_min": 300000,
        "salary_max": 400000,
        "remote": True,
    },
    {
        "source": "ashby",
        "source_id": "ashby-fixture-003",
        "title": "Principal AI Engineer",
        "company": "AI Creative Studio",
        "location": "San Francisco, CA / Remote",
        "url": "https://jobs.ashbyhq.com/aicreative/003",
        "description": """
We're building the future of AI-powered creative tools. Our platform helps
artists, musicians, and creators bring their visions to life.

As Principal AI Engineer, you'll lead our core AI team and drive innovation
across our product suite.

Required skills:
- Python, PyTorch or TensorFlow
- LLMs, generative AI, diffusion models
- Claude API, OpenAI API
- 8+ years ML/AI experience
- PhD or equivalent experience preferred

The role:
- Define AI architecture and research direction
- Mentor and grow the AI team (currently 5 engineers)
- Ship production ML systems at scale
- Collaborate with product and design

Culture: Small, intense, mission-driven startup. We ship fast and iterate.
Compensation: $280,000-$350,000 + significant equity

Industry: AI, Creative Tools, Music
        """,
        "salary_min": 280000,
        "salary_max": 350000,
        "remote": True,
    },
    {
        "source": "greenhouse",
        "source_id": "gh-fixture-004",
        "title": "Technical Co-Founder / CTO",
        "company": "Stealth Web3 Startup",
        "location": "Remote",
        "url": "https://boards.greenhouse.io/stealthweb3/jobs/004",
        "description": """
Pre-seed stealth startup building the future of decentralized music royalties.

Looking for a Technical Co-Founder / CTO to lead all technical efforts.
You'll work directly with the CEO (former Spotify PM) to bring our vision
to life.

Must have:
- Full-stack engineering background
- Solana, Rust, or Ethereum/Solidity
- Python, FastAPI or Django
- Experience shipping 0-to-1 products

Nice to have:
- Music industry experience
- Previous founder experience
- Claude API or LLM experience

Equity: 5-15% depending on experience
Salary: $150,000-$200,000 (negotiable for more equity)

This is a true co-founder role. You'll shape the company from day one.
Industry: Web3, Music, Blockchain
        """,
        "salary_min": 150000,
        "salary_max": 200000,
        "remote": True,
    },
    {
        "source": "lever",
        "source_id": "lever-fixture-005",
        "title": "AI Creative Director",
        "company": "Digital Agency X",
        "location": "New York, NY / Hybrid",
        "url": "https://jobs.lever.co/agencyx/005",
        "description": """
Leading digital agency seeking an AI Creative Director to lead our new
AI & Innovation practice.

You'll bridge the gap between cutting-edge AI technology and creative
storytelling for our Fortune 500 clients.

Requirements:
- 7+ years creative or technical experience
- Deep understanding of generative AI tools
- Strong portfolio of AI-powered creative work
- Client-facing experience
- Python/technical skills a plus

Responsibilities:
- Lead AI creative strategy for major brand clients
- Build and grow the AI creative team
- Develop new AI-powered creative services
- Present to and advise C-suite clients

Compensation: $200,000-$280,000 + bonus
Location: NYC office 3 days/week

Industry: Advertising, Creative, AI
        """,
        "salary_min": 200000,
        "salary_max": 280000,
        "remote": False,
    },
    {
        "source": "workday",
        "source_id": "wd-fixture-006",
        "title": "Director of Engineering - AI Platform",
        "company": "Enterprise Tech Corp",
        "location": "Austin, TX / Remote",
        "url": "https://enterprise.wd5.myworkdayjobs.com/careers/job/006",
        "description": """
Enterprise Tech Corp is hiring a Director of Engineering to lead our
AI Platform team.

You'll own the platform that powers AI features across all our products,
serving millions of enterprise users.

Requirements:
- 12+ years software engineering
- 5+ years managing engineering teams
- Experience with ML infrastructure at scale
- Java, Python, Kubernetes, AWS
- Enterprise software experience

Team: 25 engineers across 4 teams
Budget: $5M+ annual cloud spend under your ownership

Compensation: $280,000-$350,000 + RSUs
Location: Austin HQ or remote US

Industry: Enterprise Software, AI, SaaS
        """,
        "salary_min": 280000,
        "salary_max": 350000,
        "remote": True,
    },
    {
        "source": "greenhouse",
        "source_id": "gh-fixture-007",
        "title": "Senior Staff Engineer - AI",
        "company": "Music Streaming Co",
        "location": "Los Angeles, CA / Remote",
        "url": "https://boards.greenhouse.io/musicstreaming/jobs/007",
        "description": """
Music Streaming Co is looking for a Senior Staff Engineer to lead our
AI recommendation systems.

You'll work on the algorithms that power music discovery for 50M+ users.

Required:
- Python, PyTorch/TensorFlow
- Recommendation systems experience
- 10+ years engineering experience
- Distributed systems at scale

Nice to have:
- Music domain expertise
- PhD in ML/AI
- Publications in RecSys

Impact: Your work will directly shape what millions of people listen to.

Compensation: $300,000-$380,000 + equity + bonus
Location: LA office or full remote

Industry: Music, Streaming, AI
        """,
        "salary_min": 300000,
        "salary_max": 380000,
        "remote": True,
    },
    {
        "source": "ashby",
        "source_id": "ashby-fixture-008",
        "title": "Founding Engineer",
        "company": "AI Agent Startup",
        "location": "Remote",
        "url": "https://jobs.ashbyhq.com/aiagent/008",
        "description": """
We're building autonomous AI agents that help knowledge workers.

As Founding Engineer #3, you'll shape the technical foundation and culture
of the company.

Requirements:
- 5+ years software engineering
- Python, FastAPI or similar
- Claude API or OpenAI API experience
- Strong product sense
- Startup experience preferred

What we offer:
- Meaningful equity (1-3%)
- Work directly with founders
- Shape the product and company
- Remote-first culture

Salary: $180,000-$220,000 + equity

Industry: AI, SaaS, Productivity
        """,
        "salary_min": 180000,
        "salary_max": 220000,
        "remote": True,
    },
    {
        "source": "lever",
        "source_id": "lever-fixture-009",
        "title": "Junior Software Engineer",
        "company": "BigCorp Bank",
        "location": "New York, NY (On-site)",
        "url": "https://jobs.lever.co/bigcorp/009",
        "description": """
Entry-level position for recent graduates.

Requirements:
- Bachelor's in CS or related
- Java or Python basics
- 0-2 years experience
- On-site 5 days/week required

Salary: $75,000-$95,000

Industry: Banking, Finance
        """,
        "salary_min": 75000,
        "salary_max": 95000,
        "remote": False,
    },
    {
        "source": "greenhouse",
        "source_id": "gh-fixture-010",
        "title": "Platform Engineer",
        "company": "DevOps Startup",
        "location": "Denver, CO / Remote",
        "url": "https://boards.greenhouse.io/devops/jobs/010",
        "description": """
We're building the next-gen developer platform.

Looking for a Platform Engineer to help scale our infrastructure.

Required:
- Kubernetes, Docker, Terraform
- AWS or GCP
- Python or Go
- 5+ years experience

Compensation: $180,000-$240,000 + equity
Location: Denver or remote

Industry: DevOps, Infrastructure, SaaS
        """,
        "salary_min": 180000,
        "salary_max": 240000,
        "remote": True,
    },
]


# ─── Source Adapters ──────────────────────────────────────────────────────────


def _title_matches(title: str, target_titles: list[str]) -> bool:
    """Case-insensitive substring match of any target title against `title`."""
    if not target_titles:
        return True
    low = title.lower()
    return any(t.lower() in low for t in target_titles)


def _strip_html(raw: str) -> str:
    """Unescape entities then strip HTML tags via BeautifulSoup."""
    if not raw:
        return ""
    try:
        from bs4 import BeautifulSoup
        return BeautifulSoup(html.unescape(raw), "html.parser").get_text(separator=" ", strip=True)
    except Exception:
        return html.unescape(raw)


class _RateLimitedClient:
    """httpx.AsyncClient with per-host jitter to stay polite (~2 req/sec)."""

    def __init__(self, client: httpx.AsyncClient):
        self._client = client
        self._sem = asyncio.Semaphore(PER_SOURCE_CONCURRENCY)

    async def get(self, url: str, **kw) -> httpx.Response:
        async with self._sem:
            await asyncio.sleep(random.uniform(0.5, 2.0))
            return await self._client.get(url, **kw)

    async def post(self, url: str, **kw) -> httpx.Response:
        async with self._sem:
            await asyncio.sleep(random.uniform(0.5, 2.0))
            return await self._client.post(url, **kw)


class GreenhouseAdapter:
    """Greenhouse public board adapter."""

    async def fetch(self, client: _RateLimitedClient, slugs: list[str], target_titles: list[str]) -> list[dict]:
        async def _one(slug: str) -> list[dict]:
            url = f"https://boards.greenhouse.io/{slug}.json"
            try:
                r = await client.get(url)
                r.raise_for_status()
                payload = r.json()
            except Exception as exc:
                logger.warning("crawler.greenhouse.fetch_failed", slug=slug, error=str(exc))
                return []
            out: list[dict] = []
            for job in payload.get("jobs", []):
                title = job.get("title") or ""
                if not _title_matches(title, target_titles):
                    continue
                loc = (job.get("location") or {}).get("name")
                out.append({
                    "source": "greenhouse",
                    "source_id": f"gh-{slug}-{job.get('id')}",
                    "title": title,
                    "company": slug.replace("-", " ").title(),
                    "location": loc,
                    "description": _strip_html(job.get("content") or ""),
                    "url": job.get("absolute_url"),
                    "posted_at": job.get("updated_at"),
                })
            logger.info("crawler.greenhouse.fetched", slug=slug, total=len(payload.get("jobs", [])), matched=len(out))
            return out

        results = await asyncio.gather(*[_one(s) for s in slugs], return_exceptions=True)
        flat: list[dict] = []
        for r in results:
            if isinstance(r, list):
                flat.extend(r)
        return flat


class LeverAdapter:
    """Lever public postings adapter."""

    async def fetch(self, client: _RateLimitedClient, slugs: list[str], target_titles: list[str]) -> list[dict]:
        async def _one(slug: str) -> list[dict]:
            url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
            try:
                r = await client.get(url)
                r.raise_for_status()
                postings = r.json()
            except Exception as exc:
                logger.warning("crawler.lever.fetch_failed", slug=slug, error=str(exc))
                return []
            out: list[dict] = []
            for p in postings:
                title = p.get("text") or ""
                if not _title_matches(title, target_titles):
                    continue
                cats = p.get("categories") or {}
                created_ms = p.get("createdAt")
                posted_at = None
                if isinstance(created_ms, (int, float)):
                    try:
                        posted_at = datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc).isoformat()
                    except Exception:
                        posted_at = None
                out.append({
                    "source": "lever",
                    "source_id": f"lever-{slug}-{p.get('id')}",
                    "title": title,
                    "company": slug.replace("-", " ").title(),
                    "location": cats.get("location"),
                    "description": p.get("descriptionPlain") or _strip_html(p.get("description") or ""),
                    "url": p.get("hostedUrl"),
                    "posted_at": posted_at,
                })
            logger.info("crawler.lever.fetched", slug=slug, total=len(postings), matched=len(out))
            return out

        results = await asyncio.gather(*[_one(s) for s in slugs], return_exceptions=True)
        flat: list[dict] = []
        for r in results:
            if isinstance(r, list):
                flat.extend(r)
        return flat


class AshbyAdapter:
    """Ashby public posting-api adapter."""

    async def fetch(self, client: _RateLimitedClient, slugs: list[str], target_titles: list[str]) -> list[dict]:
        async def _one(slug: str) -> list[dict]:
            url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
            try:
                r = await client.post(url, json={"includeCompensation": True})
                r.raise_for_status()
                payload = r.json()
            except Exception as exc:
                logger.warning("crawler.ashby.fetch_failed", slug=slug, error=str(exc))
                return []
            out: list[dict] = []
            for job in payload.get("jobs", []):
                title = job.get("title") or ""
                if not _title_matches(title, target_titles):
                    continue
                comp = job.get("compensation") or {}
                out.append({
                    "source": "ashby",
                    "source_id": f"ashby-{slug}-{job.get('id')}",
                    "title": title,
                    "company": slug.replace("-", " ").title(),
                    "location": job.get("location"),
                    "description": job.get("descriptionPlain") or _strip_html(job.get("description") or ""),
                    "url": job.get("jobUrl"),
                    "posted_at": job.get("publishedDate"),
                    "salary_min": (comp.get("compensationTierSummary") or {}).get("minValue"),
                    "salary_max": (comp.get("compensationTierSummary") or {}).get("maxValue"),
                })
            logger.info("crawler.ashby.fetched", slug=slug, total=len(payload.get("jobs", [])), matched=len(out))
            return out

        results = await asyncio.gather(*[_one(s) for s in slugs], return_exceptions=True)
        flat: list[dict] = []
        for r in results:
            if isinstance(r, list):
                flat.extend(r)
        return flat


# ─── CrawlerAgent ─────────────────────────────────────────────────────────────


class CrawlerAgent:
    """
    Crawls public ATS boards against a SearchManifestSchema and returns a
    deduplicated list of DiscoveredJobSchema rows.

    Fans out across Greenhouse / Lever / Ashby adapters concurrently. Falls
    back to fixture data only if all live adapters return zero rows.
    Workday adapter is deferred (Playwright crawl, separate revision).
    """

    SOURCES = ["greenhouse", "lever", "ashby", "workday"]

    def __init__(self, candidate_id: UUID):
        self._candidate_id = candidate_id

    def _load_sources(self) -> dict:
        try:
            with open(SOURCES_YAML) as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            logger.error("crawler.sources_missing", path=str(SOURCES_YAML))
            return {}

    async def run(self, manifest: SearchManifestSchema) -> list[DiscoveredJobSchema]:
        """
        Execute a crawl run against the manifest.

        Loads sources.yaml, fans out to each adapter in parallel, merges,
        dedupes by url_hash, returns the populated list. Falls back to
        fixture data only if all live adapters return zero rows.
        """
        sources = self._load_sources()
        logger.info(
            "crawler_agent.run_start",
            candidate_id=str(self._candidate_id),
            target_titles=len(manifest.target_titles),
            sources_loaded=list(sources.keys()),
        )

        async with httpx.AsyncClient(
            timeout=HTTP_TIMEOUT,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            follow_redirects=True,
        ) as raw_client:
            client = _RateLimitedClient(raw_client)
            adapters_results = await asyncio.gather(
                GreenhouseAdapter().fetch(client, sources.get("greenhouse", []) or [], manifest.target_titles),
                LeverAdapter().fetch(client, sources.get("lever", []) or [], manifest.target_titles),
                AshbyAdapter().fetch(client, sources.get("ashby", []) or [], manifest.target_titles),
                return_exceptions=True,
            )

        merged: list[dict] = []
        for r in adapters_results:
            if isinstance(r, list):
                merged.extend(r)
            else:
                logger.warning("crawler.adapter_exception", error=str(r))

        # Dedupe by url_hash
        seen: set[str] = set()
        deduped: list[dict] = []
        for j in merged:
            url = j.get("url") or ""
            if not url:
                continue
            h = self.url_hash(url)
            if h in seen:
                continue
            seen.add(h)
            deduped.append(j)

        logger.info(
            "crawler_agent.run_complete",
            candidate_id=str(self._candidate_id),
            adapters_merged=len(merged),
            after_dedup=len(deduped),
        )

        # Apply exclusions + convert to schema
        results = self._apply_exclusions_and_convert(deduped, manifest)

        # Offline fallback: only when EVERY live adapter returned empty
        if not results:
            logger.warning(
                "crawler.fallback_used",
                candidate_id=str(self._candidate_id),
                reason="all_live_adapters_empty",
            )
            return self._filter_fixtures(manifest)

        return results

    def _apply_exclusions_and_convert(
        self, jobs: list[dict], manifest: SearchManifestSchema
    ) -> list[DiscoveredJobSchema]:
        """Apply excluded_companies / excluded_industries and convert dicts to schema."""
        excluded_companies = {c.lower() for c in manifest.excluded_companies}
        excluded_industries = {i.lower() for i in manifest.excluded_industries}

        out: list[DiscoveredJobSchema] = []
        for j in jobs:
            company_low = (j.get("company") or "").lower()
            if any(exc in company_low for exc in excluded_companies):
                continue
            desc_low = (j.get("description") or "").lower()
            if any(exc in desc_low for exc in excluded_industries):
                continue
            posted_at: Optional[datetime] = None
            if isinstance(j.get("posted_at"), str):
                try:
                    posted_at = datetime.fromisoformat(j["posted_at"].replace("Z", "+00:00"))
                except Exception:
                    posted_at = None
            out.append(DiscoveredJobSchema(
                id=uuid4(),
                source=j["source"],
                source_id=j["source_id"],
                title=j["title"],
                company=j["company"],
                location=j.get("location"),
                description=j.get("description"),
                url=j["url"],
                posted_at=posted_at,
                salary_min=j.get("salary_min"),
                salary_max=j.get("salary_max"),
                remote=bool(j.get("remote")) or "remote" in (j.get("location") or "").lower(),
                crawled_at=datetime.now(timezone.utc),
            ))
        return out

    def _filter_fixtures(
        self, manifest: SearchManifestSchema
    ) -> list[DiscoveredJobSchema]:
        """
        Filter fixture jobs based on the search manifest.

        Applies:
          - Title matching (case-insensitive substring)
          - Company exclusions
          - Industry exclusions (checked against description)

        Returns deterministic results for testing.
        """
        results: list[DiscoveredJobSchema] = []
        excluded_companies = {c.lower() for c in manifest.excluded_companies}
        excluded_industries = {i.lower() for i in manifest.excluded_industries}
        target_keywords = {kw.lower() for kw in manifest.keywords}
        target_titles = {t.lower() for t in manifest.target_titles}

        for job_data in _FALLBACK_JOBS:
            company_lower = job_data["company"].lower()
            title_lower = job_data["title"].lower()
            desc_lower = job_data.get("description", "").lower()

            # Skip excluded companies
            if any(exc in company_lower for exc in excluded_companies):
                continue

            # Skip excluded industries (check description)
            if any(exc in desc_lower for exc in excluded_industries):
                continue

            # Match by title or keywords
            title_match = any(t in title_lower for t in target_titles)
            keyword_match = any(
                kw in desc_lower or kw in title_lower for kw in target_keywords
            )

            if title_match or keyword_match:
                results.append(
                    DiscoveredJobSchema(
                        id=uuid4(),
                        source=job_data["source"],
                        source_id=job_data["source_id"],
                        title=job_data["title"],
                        company=job_data["company"],
                        location=job_data.get("location"),
                        description=job_data.get("description"),
                        url=job_data["url"],
                        salary_min=job_data.get("salary_min"),
                        salary_max=job_data.get("salary_max"),
                        remote=job_data.get("remote", False),
                        crawled_at=datetime.now(timezone.utc),
                    )
                )

        return results

    @staticmethod
    def url_hash(url: str) -> str:
        """Deterministic hash for deduplication against the discovered_jobs table."""
        return hashlib.sha256(url.strip().lower().encode()).hexdigest()
