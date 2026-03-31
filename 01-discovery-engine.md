# TALENT AGENT — DISCOVERY ENGINE
## Claude Code Prompt · Phase 1

---

## CONTEXT

You are building the **Discovery Engine** for **VibeSpace Talent Agent** — an autonomous AI talent system built by **Sean Young (Space Cowboy #9)** at **VibeSpace LLC ("The Dot Connector")**, Miami, FL.

The operator is a Principal AI Engineer, Founder, and multi-hyphenate creative. His full identity stack: enterprise Java/Python engineer (7+ years JPMorgan Chase + BofA), AI systems architect, VibeSpace LLC founder, DJ/music producer, Solana developer, and visionary builder. The system must understand that candidates are **whole people** — not job titles.

The Discovery Engine is the first of two core agents in the Talent Agent system. It runs on a **daily cron schedule**, reverse-engineers the web to find roles that match a candidate's full identity — not just their resume — and delivers a ranked digest of opportunities.

This is **not a job board scraper.** It is a reverse-engineering engine that asks: *"Given everything this person is, what roles exist in the world that they should know about?"*

---

## PHILOSOPHY

Most job search tools pattern-match a resume against job titles. This engine does the opposite:

1. Build a rich multi-dimensional identity model of the candidate
2. Generate a wide net of role archetypes they *could* be a fit for — including roles they'd never think to search for
3. Crawl the web and find real open positions that match those archetypes
4. Score each opportunity across multiple dimensions
5. Return a ranked, contextualised daily digest

A candidate who is "Senior Java Engineer + AI Founder + DJ/Producer" should surface:
- Head of AI Products
- Technical Co-Founder (Series A startups)
- VP Engineering at music-tech or creator economy companies
- AI Creative Director
- Developer Advocate at AI infrastructure companies
- CTO / fractional CTO roles
- ...not just "Senior Software Engineer L5"

---

## WHAT YOU ARE BUILDING

### Directory: `backend/agents/discovery/`

Build the full Discovery Engine as a FastAPI-compatible Python module with the following components:

---

### 1. Identity Profiler · `identity_profiler.py`

**Purpose:** Transforms raw candidate input into a structured multi-dimensional identity model.

**Input:** Candidate object (see models below)

**Output:** `IdentityProfile` — a rich model with dimensions:
- `technical_skills`: Languages, frameworks, infrastructure (weighted by years + recency)
- `domain_expertise`: Industries, problem spaces (fintech, web3, AI, music, creator economy)
- `leadership_level`: IC, lead, staff, principal, founder, exec
- `archetype_tags`: Human-readable identity descriptors (e.g. `"technical-founder"`, `"ai-builder"`, `"creative-technologist"`, `"multi-hyphenate"`)
- `role_expansion`: Generated list of role archetypes this person could target beyond their obvious title
- `culture_signals`: Startup vs enterprise, remote vs in-person, mission-driven vs comp-driven
- `compensation_band`: Estimated target range based on level + location
- `creative_layer`: Non-technical identity (music, art, entrepreneurship) — used to match culture

**Implementation notes:**
- Use Claude API to generate `role_expansion` — prompt it with the full identity profile and ask it to generate 15–20 non-obvious role archetypes
- Cache the identity profile in Redis (TTL: 24h) — only regenerate if candidate data changes
- Log identity profile generation to PostgreSQL for audit trail

---

### 2. Role Archetype Generator · `archetype_generator.py`

**Purpose:** Expands the identity profile into a broad set of search targets — job titles, company types, and industries to crawl.

**Input:** `IdentityProfile`

**Output:** `ArchetypeManifest`
- `target_titles`: List of specific job titles to search (e.g. `["Head of AI", "Principal AI Engineer", "VP Engineering", "Technical Co-Founder"]`)
- `target_companies`: Company profiles to watch (by industry, stage, size, tech stack)
- `target_industries`: Industries ranked by fit score
- `keywords`: Search keyword combinations for each archetype
- `exclusions`: Titles/companies to explicitly skip (e.g. roles clearly below level, industries candidate opted out of)

**Implementation notes:**
- Build title expansion logic that converts archetypes to search variants (e.g. "Head of AI" → ["Head of AI", "Director of AI", "VP AI", "AI Lead"])
- Company targeting should factor in: tech stack match, funding stage, size, culture signals
- Persist manifest to PostgreSQL — used by the crawler as its search instructions

---

### 3. Web Crawler Agent · `crawler_agent.py`

**Purpose:** Crawls job boards and company career pages to find open positions matching the archetype manifest.

**Sources to crawl (in priority order):**
1. Company career pages (direct) — highest signal, no middleman
2. Greenhouse API (`boards.greenhouse.io`) — used by most tech startups
3. Lever API (`api.lever.co`) — widely adopted
4. Workday career portals — enterprise companies
5. Ashby (`jobs.ashby.io`) — growing in tech
6. LinkedIn Jobs (scrape, not API — handle rate limits carefully)
7. Indeed / Glassdoor (fallback only)

**Implementation:**
- Use `Playwright` for JavaScript-heavy career pages
- Use `httpx` + `BeautifulSoup` for static pages
- Implement respectful rate limiting: 1–2 req/sec per domain, randomised delay 0.5–2.0s
- Deduplicate against `seen_jobs` table in PostgreSQL (by URL hash)
- Store raw job data: title, company, location, URL, posted date, job description text, source
- Mark jobs as `DISCOVERED` status in the pipeline

**Error handling:**
- Log failed crawls with reason — never crash the full run
- Retry failed sources up to 3x with exponential backoff
- Alert via Redis pub/sub if >20% of sources fail in a single run

---

### 4. Relevance Scorer · `relevance_scorer.py`

**Purpose:** Scores each discovered job against the candidate's identity profile across multiple dimensions.

**Scoring dimensions (each 0–100, weighted):**

| Dimension | Weight | What it measures |
|---|---|---|
| `technical_match` | 30% | Skills overlap between JD requirements and candidate profile |
| `level_match` | 20% | Seniority alignment — penalise both under and over |
| `culture_match` | 15% | Startup/enterprise, remote/hybrid, mission alignment |
| `industry_match` | 15% | Domain expertise alignment |
| `growth_potential` | 10% | Does this role expand the candidate's trajectory? |
| `compensation_match` | 10% | Estimated band vs candidate target |

**Output:** `ScoredJob` — job + score breakdown + reasoning string

**Implementation notes:**
- Use Claude API to parse JD text and extract structured requirements (skills, level, culture signals, comp if mentioned)
- Run scoring logic locally (no LLM needed for math)
- Use Claude API to generate a 2-sentence human-readable reasoning for each score — shown in the digest
- Filter out jobs scoring below `MIN_SCORE` threshold (configurable, default: 60)
- Jobs scoring 80+ are flagged as `HOT`

---

### 5. Daily Digest Builder · `digest_builder.py`

**Purpose:** Assembles the daily ranked digest from scored jobs and prepares it for the Review Dashboard.

**Output:** `DailyDigest`
- `date`: Run date
- `candidate_id`: FK to candidate
- `total_discovered`: Raw jobs found
- `total_scored`: Jobs that passed MIN_SCORE filter
- `top_picks`: Top 10 jobs, ranked by composite score
- `hot_picks`: Jobs flagged 80+ (surfaced separately)
- `new_companies`: Companies not seen in previous digests (novelty signal)
- `digest_summary`: Claude-generated 3-sentence narrative about today's landscape

**Delivery:**
- Persist full digest to PostgreSQL
- Publish `DIGEST_READY` event on Redis pub/sub → triggers Review Dashboard notification
- Optional: send summary email to candidate (configurable)

---

### 6. Discovery Orchestrator · `orchestrator.py`

**Purpose:** Coordinates the full daily discovery run. Acts as the entry point for the cron job.

**Flow:**
```
load_candidate(candidate_id)
  → identity_profiler.build_profile()
  → archetype_generator.expand()
  → crawler_agent.run(manifest)
  → relevance_scorer.score_batch(jobs)
  → digest_builder.compile(scored_jobs)
  → emit DIGEST_READY
```

**Implementation:**
- Run crawler and scorer concurrently using `asyncio.gather` where possible
- Full run should complete in under 10 minutes for a single candidate
- Log run metadata: start time, end time, jobs discovered, jobs scored, errors
- Support `dry_run=True` mode for testing without writing to DB

---

## MODELS · `models/discovery.py`

Define all Pydantic models:

```python
class Candidate(BaseModel):
    id: UUID
    name: str
    email: str
    resume_text: str
    linkedin_url: Optional[str]
    github_url: Optional[str]
    personal_context: str        # free-form: "I'm also a DJ, founder of VibeSpace..."
    target_locations: List[str]
    remote_preference: str       # "remote", "hybrid", "onsite", "flexible"
    min_compensation: Optional[int]
    excluded_companies: List[str]
    excluded_industries: List[str]

class IdentityProfile(BaseModel): ...
class ArchetypeManifest(BaseModel): ...
class DiscoveredJob(BaseModel): ...
class ScoredJob(BaseModel): ...
class DailyDigest(BaseModel): ...
```

---

## DATABASE SCHEMA · `migrations/001_discovery.sql`

Create tables:
- `candidates` — candidate profiles
- `identity_profiles` — versioned identity models (one per candidate per day)
- `archetype_manifests` — search instructions derived from identity
- `discovered_jobs` — raw crawled jobs (deduplicated by url_hash)
- `scored_jobs` — jobs with scoring breakdown
- `daily_digests` — digest metadata
- `digest_jobs` — junction: digest ↔ scored_jobs (top picks)
- `crawl_runs` — audit log of every discovery run

---

## API ENDPOINTS · `api/discovery.py`

```
POST   /discovery/run/{candidate_id}       → trigger manual run
GET    /discovery/digest/{candidate_id}    → get latest digest
GET    /discovery/digests/{candidate_id}   → list all digests
GET    /discovery/job/{job_id}             → get job detail
PATCH  /discovery/job/{job_id}/status      → update status (APPROVED, SKIPPED, APPLIED)
GET    /discovery/stats/{candidate_id}     → run history + metrics
```

---

## ENVIRONMENT VARIABLES

```env
ANTHROPIC_API_KEY=
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
MIN_SCORE=60
MAX_JOBS_PER_RUN=500
CRAWL_CONCURRENCY=5
DISCOVERY_CRON="0 7 * * *"   # 7am daily
```

---

## TECH STACK

- Python 3.12
- FastAPI
- Pydantic v2
- SQLAlchemy 2.0 (async)
- Alembic (migrations)
- Playwright (async) + BeautifulSoup
- httpx (async HTTP)
- Celery + Redis (task queue for cron)
- Claude API (claude-sonnet-4-20250514)
- PostgreSQL 15
- Redis 7

---

## CONSTRAINTS & STANDARDS

- All agents extend `BaseAgent` from the Mycelium Agent Network if available, otherwise implement standalone with identical interface
- Every external call (Claude API, scraper, DB) wrapped in try/except with structured logging
- No synchronous blocking calls in async context
- All secrets via environment variables — never hardcoded
- Type hints on every function
- Docstrings on every class and public method
- Tests in `tests/discovery/` — use pytest + pytest-asyncio
- Follow Apache 2.0 license headers

---

## OUTPUT

When complete, confirm:
- [ ] All 6 agent modules created and wired
- [ ] Pydantic models defined
- [ ] Database migration written
- [ ] API endpoints registered on the FastAPI app
- [ ] `.env.example` updated
- [ ] `tests/discovery/` with at least smoke tests for orchestrator and scorer
- [ ] `README` section for Discovery Engine updated

Start with `models/discovery.py`, then `identity_profiler.py`, then `orchestrator.py`. Build top-down.
