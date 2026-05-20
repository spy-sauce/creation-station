# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Web Crawler Agent — multi-source job board crawler.

Phase 1A: Stubbed implementation returning deterministic fixture data.
Phase 1B: Real adapters (Greenhouse, Lever, Ashby, Workday) to be implemented.

The stub returns realistic fixture jobs to allow end-to-end testing of the
full Discovery Engine pipeline without external dependencies.

Supported sources (Phase 1B implementations):
  1. Greenhouse (https://boards.greenhouse.io/{slug}.json) — public JSON API
  2. Lever (https://api.lever.co/v0/postings/{slug}?mode=json) — public JSON API
  3. Ashby (https://api.ashbyhq.com/posting-api/job-board/{slug}) — public JSON API
  4. Workday (https://{tenant}.wd*.myworkdayjobs.com/{board}) — Playwright crawl

Rate limits: 2 req/sec per domain, 0.5-2.0s jitter, User-Agent
"TalentAgent/1.0 (+https://example.com/bot)". Respect robots.txt.

Dedup: url_hash() against the discovered_jobs table before insert.

Curated company slugs live in backend/agents/discovery/sources.yaml.
"""

import hashlib
from datetime import datetime, timezone
from uuid import UUID, uuid4

import structlog

from backend.agents.discovery.schemas import SearchManifestSchema, DiscoveredJobSchema

logger = structlog.get_logger(__name__)


# ─── Phase 1A Fixture Data ─────────────────────────────────────────────────────
# Deterministic fixture jobs for end-to-end testing before real crawlers ship.

_FIXTURE_JOBS: list[dict] = [
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


class CrawlerAgent:
    """
    Crawls public ATS boards against a SearchManifestSchema and returns a
    deduplicated list of DiscoveredJobSchema rows.

    Phase 1A: Returns deterministic fixture data for end-to-end pipeline testing.
    Phase 1B: Real multi-source crawl implementation.
    """

    SOURCES = ["greenhouse", "lever", "ashby", "workday"]

    def __init__(self, candidate_id: UUID):
        """
        Initialize the CrawlerAgent.

        Args:
            candidate_id: UUID of the candidate this crawl is for
        """
        self._candidate_id = candidate_id

    async def run(self, manifest: SearchManifestSchema) -> list[DiscoveredJobSchema]:
        """
        Execute a crawl run against the manifest.

        Phase 1A: Returns filtered fixture data based on manifest keywords.
        Phase 1B: Will load sources.yaml, fan out to adapters, merge, dedupe.

        Args:
            manifest: Search manifest with target titles, keywords, exclusions

        Returns:
            List of discovered jobs matching the manifest
        """
        logger.info(
            "crawler_agent.run_start",
            candidate_id=str(self._candidate_id),
            target_titles=len(manifest.target_titles),
            keywords=len(manifest.keywords),
        )

        # Phase 1A: Filter fixture data based on manifest
        jobs = self._filter_fixtures(manifest)

        logger.info(
            "crawler_agent.run_complete",
            candidate_id=str(self._candidate_id),
            jobs_found=len(jobs),
            note="Phase 1A stub - returning filtered fixtures",
        )
        return jobs

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

        for job_data in _FIXTURE_JOBS:
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
