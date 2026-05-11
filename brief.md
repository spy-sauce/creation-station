# Talent Agent — Cultivation Brief

> Input to `mycelium plant`. Canonical spec the cultivation seeds from. This brief **locks the current state of the project** for HYPHA contract-freeze. It does not redesign the existing agent architecture — it captures it.
>
> Read `CLAUDE.md` (project) and `/Users/spy/.claude/CLAUDE.md` (global VibeSpace context) before acting on anything below.

---

## What we're building

**Talent Agent** — a 24/7 autonomous AI talent system with two engines:

1. **Discovery Engine** — reverse-engineers the web daily to find roles matching a candidate's full identity (not just resume title). Produces a ranked daily digest.
2. **Application Engine** — for each approved job, autonomously runs: parse JD → tailor resume → research company → find contact → compose outreach → fill form → submit. Pauses for human approval before anything sends.

Initial use case: single candidate (Sean Young) running on his own resume. Target market: recruiting agencies managing 50–500 candidates simultaneously.

The repo at HEAD (commit `26143cd`) already has both engines wired through their orchestrators, the FastAPI surface live, passwordless auth + onboarding scaffolded, the Review Dashboard frontend scaffolded, and the Digital Dash CI/CD pipeline configured. **This cultivation contract-freezes what's there.** No agent rewrites.

---

## Why

This is **Phase 1 — single-candidate MVP.** "Done" = the loop finds a real job, tailors a real resume, composes a real email, fills a real form, all reviewed and approved by the operator.

The MVP is personal. The vision is a B2B SaaS platform for recruiting agencies. Build the MVP right and the platform follows naturally.

The cultivation itself is also a **dogfood pass for `legendary-funicular` on a Python/FastAPI/Postgres workload** — prior `mycelium ddp` runs (live-grid run7/run8) targeted Expo/Supabase. Surfacing framework gaps on a Python stack is useful for the framework.

---

## Team + governance

- **Operator:** SPY (Sean Young, Space Cowboy #9) — Founder & CEO, VibeSpace LLC. Build authority.
- **Stream tag:** `TA/`
- **Branch:** `TA/<kebab-desc>` · **Commit subject:** `[TA] <imperative>` · **PR title:** `[TA] <what shipped>`
- **HYPHA gate:** non-negotiable per global guardrails. No code written against an unfrozen spec. This brief + the `hyphae/HYPHA-*.md` files freeze together.
- **Polish bar:** Production-grade for the single-candidate loop. Multi-tenant features deliberately deferred — design with multi-tenancy in mind (`candidate_id` FK present everywhere), don't build the agency dashboard yet.

---

## Stack (locked)

| Layer | Choice | Why |
|---|---|---|
| Language | **Python 3.12** | Per repo CLAUDE.md and global stack defaults |
| Backend framework | **FastAPI** + **Pydantic v2** | Async-native, type-safe contracts |
| ORM | **SQLAlchemy 2.0 async** | Async-first, mapped_column style |
| Database | **PostgreSQL 15** | Plain SQL migrations under `backend/migrations/`; SQLAlchemy reads ORM definitions in `backend/models/` |
| Cache + pub/sub | **Redis 7** | Identity profile cache (24h TTL), `agent.status.*` channels |
| AI | **Anthropic SDK** · model `claude-sonnet-4-20250514` · `max_tokens=4096` default | Locked per repo CLAUDE.md |
| Web automation | **Playwright async** + **httpx** + **BeautifulSoup** | Crawler + auto_apply + scraping |
| PDF | **PyMuPDF** (`fitz`) | Resume text extraction in onboarding |
| Auth | **Passwordless magic link** + **JWT** (`HS256`, 7d expiry) | See §7 |
| Frontend | **React 19** · **Vite 8** · **Tailwind 4** · **lucide-react** · **react-router-dom 7** | Per `frontend/package.json` |
| Infrastructure | **Docker** · **AWS ECS Fargate** (us-east-1) · **ECR** · **AWS Secrets Manager** | Per `deploy/` and `digital-dash-pipeline.yml` |
| CI/CD | **Digital Dash** pipeline (`digital-dash-pipeline.yml`) | Stages: lint → test → build → deploy-staging → health-check → deploy-prod (manual gate) |
| Local dev | **docker-compose** (postgres + redis + app) | Plus `start.sh` / `stop.sh` wrappers |
| Logging | **structlog** | No `print()` for logging |
| Testing | **pytest** · **pytest-asyncio** | Smoke tests in `tests/discovery/` |
| License | **Apache 2.0** | Header required on every new file |

**No new dependencies beyond the above.** If a leaf needs one, justify in its `FRUIT_READY` line.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                Review Dashboard (React 19 + Vite 8)                  │
│   Landing · Login · Onboarding · Overview · Candidates · Pipeline    │
│   · ReviewQueue · Analytics · Settings · VerifyAuth                  │
└────────────────────────────┬─────────────────────────────────────────┘
                             │ JWT (Bearer)
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│              FastAPI (backend/main.py · /api/v1)                     │
│   /auth · /onboarding · /discovery · /application · /review          │
└────────┬──────────────┬───────────────┬──────────────────────┬───────┘
         │              │               │                      │
         ▼              ▼               ▼                      ▼
   ┌──────────┐  ┌────────────┐  ┌───────────────────┐  ┌────────────┐
   │ Postgres │  │  Redis     │  │ Discovery Engine  │  │ App Engine │
   │ 15       │  │  7         │  │ (orchestrator)    │  │ (orch +    │
   │          │  │  pub/sub + │  │                   │  │  agent_mgr)│
   │          │  │  cache     │  │                   │  │            │
   └──────────┘  └────────────┘  └────────┬──────────┘  └──────┬─────┘
                                          │                    │
                                          ▼                    ▼
                                  ┌──────────────────────────────┐
                                  │  Anthropic API · Sonnet 4    │
                                  │  Playwright · httpx · bs4    │
                                  └──────────────────────────────┘
```

- **Single FastAPI app** mounting five routers under `/api/v1`.
- **Discovery orchestrator** runs the daily pipeline per candidate: identity profile (cached 24h) → archetype expansion → crawl → score with bounded concurrency → digest. State persisted as `CrawlRun` rows; events on `agent.status.discovery`.
- **Application orchestrator** runs per approved job, with `resume_tailor` + `company_intel` fanned out concurrently via `asyncio.gather`. Pauses at `AWAITING_REVIEW` until the Dashboard posts approval. Events on `agent.status.application`.
- **Agent Manager** (`backend/agents/application/agent_manager.py`) wraps each application sub-agent as an autonomous Claude `tool_use` worker with its own system prompt + tools. Dependency-graph dispatcher runs independent agents concurrently inside a global semaphore. Events on `agent.status.subagent`.
- **Review Dashboard** is the human gate. Inspects every artifact (parsed JD, tailored resume diff, company intel, contact, outreach email) and approves/rejects before submission.

---

## Domain entities

Already defined in `backend/migrations/000–003_*.sql` and `backend/models/`. Locked at freeze.

### Discovery (`001_discovery.sql`)
- `candidates` — identity + preferences (resume_text, linkedin_url, github_url, personal_context, target_locations, remote_preference, min_compensation, excluded_companies, excluded_industries)
- `discovered_jobs` — raw crawl output (title, company, location, url, url_hash, description, source, posted_date, status)
- `scored_jobs` — 6-dimension relevance scoring (technical, level, culture, industry, growth, compensation) + composite + reasoning + `is_hot`
- `daily_digests` — per-candidate per-day digest (top_picks, hot_picks, new_companies)
- `crawl_runs` — run lifecycle records (status, jobs_discovered, jobs_scored, error_log, completed_at)

### Application (`002_application.sql`)
- `parsed_jds` — structured JD signals (required/preferred skills, seniority, tech_stack, culture_signals, tone, responsibilities, pain_points, comp_mentioned, red_flags, application_instructions)
- `tailored_resumes` — tailored output (summary, full_text, change_log, pdf_path, version)
- `company_intel` — research output (about, recent_news, tech_stack, engineering_culture, growth_stage, team_size, notable_facts, cache_expires_at)
- `contacts` — discovered recipient (name, title, email, linkedin_url, confidence: HIGH/MEDIUM/LOW, source, fallback_email)
- `application_pipelines` — full lifecycle row per approved job (status state machine, FK to candidate/job/resume/intel/contact/email)
- CRM event rows (per pipeline event log)

### Auth (`003_auth.sql`)
- `users` — Talent Agent account (email unique, is_active, is_onboarded, candidate_id FK 1:1, last_login_at)
- `magic_links` — single-use, time-limited token (user_id, token unique, is_used, expires_at)

---

## Biome split (DAG-driven)

`mycelium ddp` dispatches all biomes in a single cultivate call; ordering is enforced by each biome's `blocked_by` declarations. Targeting 10 biomes.

| Biome | HYPHA tag | Owns | Blocked by |
|---|---|---|---|
| `schema-core` | `TA/SCHEMA` | Migrations 000–003, SQLAlchemy models, Pydantic schemas, base model (id/created_at/updated_at), enums (job_status, application_status, agent_status) | — |
| `auth` | `TA/AUTH` | Passwordless magic link flow, JWT issuance + validation, `get_current_user` FastAPI dependency. `/auth/request-link`, `/auth/verify`, `/auth/me` | schema-core |
| `onboarding` | `TA/ONBOARD` | Resume PDF upload + text extraction (PyMuPDF), candidate profile save, onboarding status. `/onboarding/resume`, `/onboarding/profile`, `/onboarding/status` | schema-core, auth |
| `discovery-engine` | `TA/DISCOVER` | identity_profiler, archetype_generator, crawler_agent (stubbed in Phase 1A), relevance_scorer (6-dim weighted), digest_builder, orchestrator. Redis cache for profile (24h). | schema-core |
| `application-engine` | `TA/APPLY` | jd_parser, resume_tailor, company_intel, contact_finder, outreach_composer, auto_apply (Playwright), crm (event log), orchestrator. Parallel resume+intel via `asyncio.gather`. Pause state at `AWAITING_REVIEW`. | schema-core, discovery-engine |
| `agent-manager` | `TA/AGENTS` | `SubAgentRegistry`, `SubAgentRunner` (Claude `tool_use` agentic loop, retries with exp backoff), `PipelineDispatcher` (dependency-tier execution), `AgentManager` facade. Wraps application sub-agents as autonomous Claude workers. | application-engine |
| `api-surface` | `TA/API` | `backend/main.py` (lifespan, CORS, health), `backend/api/router.py` (mounts /auth /onboarding /discovery /application /review under `/api/v1`), per-domain router files | auth, onboarding, discovery-engine, application-engine, agent-manager |
| `review-dashboard` | `TA/DASH` | React 19 + Vite 8 + Tailwind 4 frontend. Pages: Landing, Login, VerifyAuth, Onboarding, Overview, Candidates, Pipeline, ReviewQueue, Analytics, Settings. Components: Sidebar, TopBar, StatCard, StatusBadge. AuthContext + DashboardLayout. `lib/api.js` axios-ish client. | api-surface |
| `infra-deploy` | `TA/INFRA` | Backend Dockerfile, frontend Dockerfile + nginx.conf, docker-compose.yml, Makefile, start.sh/stop.sh, `deploy/deploy.sh` (ECS update + rollback), `deploy/setup-aws.sh` (one-time bootstrap), ECS task defs (backend + frontend), `digital-dash-pipeline.yml` (lint/test/build/deploy-staging/health/deploy-prod) | api-surface, review-dashboard |
| `observability` | `TA/OBS` | structlog config, agent lifecycle state machine (per CLAUDE.md), Redis pub/sub channels (`agent.status.discovery`, `agent.status.application`, `agent.status.subagent`), CRM event log, pipeline status codes | discovery-engine, application-engine, agent-manager |

Distribution (ECR push + ECS service update + health check) is a deploy task inside `infra-deploy`, not its own biome.

---

## Frozen contract surfaces (NUTRIENTS.md skeleton)

These contracts, once frozen, every leaf must consume verbatim. SPY signs off as build authority for this run.

### §0 — Stack lock
Per the **Stack (locked)** table above. No version drift without a brief amendment.

### §1 — Database schema
Source of truth: `backend/migrations/000_init.sql` through `003_auth.sql`, plus `backend/models/{base,discovery,application,auth}.py`. Every column, FK, enum, and index in those files is canon. All biomes read this; only `schema-core` writes it. Every table has `id UUID PK`, `created_at TIMESTAMPTZ`, `updated_at TIMESTAMPTZ` (per repo CLAUDE.md).

### §2 — Agent lifecycle state machines

**Generic agent** (per repo CLAUDE.md):
```
QUEUED → RUNNING → COMPLETED
                 → FAILED → RETRYING → COMPLETED
                                     → DEAD
```

**Discovery `crawl_runs`:** `QUEUED → RUNNING → COMPLETED | FAILED`.

**Application `application_pipelines`:**
```
QUEUED → PARSING → TAILORING → RESEARCHING → COMPOSING →
AWAITING_REVIEW → APPROVED | REJECTED →
SUBMITTED → SENT → TRACKED
                 → FAILED
```

**Sub-agent (Claude tool_use):** `QUEUED → DISPATCHED → RUNNING → COMPLETED | FAILED → RETRYING → COMPLETED | DEAD`. Max retries = 3, exponential backoff (`2^attempt` seconds).

Every transition: logged to Postgres, published to Redis pub/sub, surfaced in the Dashboard.

### §3 — Pub/sub event channels
- `agent.status.discovery` — discovery orchestrator status
- `agent.status.application` — application orchestrator + `PIPELINE_STATUS` events
- `agent.status.subagent` — `SUBAGENT_STATUS` per-agent events (execution_id, agent_name, pipeline_id, status, attempt, duration_ms)
- Event payloads are JSON-encoded with an `event` discriminator field.

### §4 — Discovery output shape
`DailyDigestSchema`: `candidate_id`, `run_date` (ISO), `total_discovered`, `total_scored`, `top_picks` (ranked `ScoredJobSchema[]`), `hot_picks` (`is_hot=true` subset), `new_companies` (string[]), `digest_summary`. Locked in `backend/agents/discovery/schemas.py`.

### §5 — Application output shape
`ApplicationPipelineSchema` with embedded `parsed_jd`, `tailored_resume`, `company_intel`, `contact`, `outreach_email`. Schemas in `backend/agents/application/schemas.py`. Resume tailor must never fabricate experience/titles/dates/metrics — gaps flagged in `change_log`. Contact `confidence` is HIGH/MEDIUM/LOW. Outreach email stays `DRAFT` until human approves; 150–200 words, 3 subject variants. AutoApply may NOT submit without explicit human approval — CAPTCHA → `REQUIRES_MANUAL`.

### §6 — Sub-agent registry + tool_use protocol
Registered agents (per `SubAgentRegistry._register_defaults()`): `jd_parser`, `resume_tailor`, `company_intel`, `contact_finder`, `outreach_composer`, `auto_apply`. Dependency graph: `jd_parser → {resume_tailor, company_intel} → contact_finder → outreach_composer → auto_apply`. Each agent has a frozen system prompt, tool schemas, and `max_tokens`. `PipelineDispatcher` resolves tiers; agents within a tier run concurrently bounded by `settings.max_parallel_applications`. Adding a new agent requires a brief amendment.

### §7 — Auth + JWT contract
- **Magic link:** 48-byte URL-safe token, expires per `settings.magic_link_expiry_minutes`, single-use (`is_used` flag). In `DEBUG=true` returned in response body for dev; in prod sent via email (TODO).
- **JWT:** `HS256`, 7-day expiry, claims `{sub: user_id, email, iat, exp}`. Secret from `settings.jwt_secret`.
- **Dependency:** `get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security))` — looks up `User` by `sub`, 401s if missing/inactive.
- **User → Candidate:** 1:1 via `user.candidate_id` FK, created on resume upload.

### §8 — Onboarding payload shape
- `POST /onboarding/resume`: multipart `file` (`application/pdf`, ≤10 MB) → PyMuPDF extract → `Candidate.resume_text`. Response: `candidate_id`, `text_length`, 500-char preview.
- `POST /onboarding/profile`: `{name, linkedin_url?, github_url?, personal_context?, target_locations?, remote_preference="flexible", min_compensation?, excluded_companies?, excluded_industries?}` → persists, sets `user.is_onboarded=true`. Resume must be uploaded first.
- `GET /onboarding/status`: `{is_onboarded, has_resume, has_profile, candidate_id}`.

### §9 — Claude API conventions
- Model: `claude-sonnet-4-20250514` everywhere.
- Default `max_tokens=4096` (override per agent in registry).
- Retry: 3 attempts, exponential backoff. Sub-agent runner implements this in `_agentic_loop`.
- Cache responses keyed by content hash (not timestamp). Identity profile cached 24h in Redis.
- Log prompt + response for every call — redact PII (email, phone, legal_name) before logging.

### §10 — External scraping conventions
- Respect `robots.txt`.
- Rate limit: 1–2 req/sec per domain.
- Random jitter 0.5–2.0s between requests.
- User-Agent: `VibeSpaceTalentAgent/1.0` — identify as a bot.
- On 429/503: exponential backoff, max 3 retries, then log + skip.
- `CRAWL_CONCURRENCY` semaphore bounds Claude scoring fan-out.

### §11 — Naming conventions (per repo CLAUDE.md)
- Files: `snake_case.py` · Classes: `PascalCase` · Functions: `snake_case` · DB tables: `snake_case`
- Redis keys: `{namespace}:{entity}:{id}` (e.g., `digest:candidate:abc123`, `profile:candidate:abc123`)
- Events: `SCREAMING_SNAKE_CASE` (`DIGEST_READY`, `APPLICATION_STATUS`, `SUBAGENT_STATUS`)
- Env vars: `SCREAMING_SNAKE_CASE` (`ANTHROPIC_API_KEY`, `DATABASE_URL`, `REDIS_URL`)

### §12 — Pipeline result codes (Digital Dash)
- Green (all stages PASSED) → auto-merge
- Red (any stage FAILED) → flag for human review
- Yellow (any stage WARNED) → continue, notify

---

## API surface (locked)

All under `/api/v1`. Authentication via `Authorization: Bearer <jwt>` header except `/auth/request-link` and `/auth/verify`.

```
POST   /auth/request-link        → request magic link
POST   /auth/verify              → exchange magic token for JWT
GET    /auth/me                  → current user

POST   /onboarding/resume        → upload resume PDF (multipart)
POST   /onboarding/profile       → save profile + preferences
GET    /onboarding/status        → onboarding completion

POST   /discovery/run            → trigger discovery for a candidate
GET    /discovery/digest/{id}    → fetch latest digest
…       (see backend/api/discovery.py for full list)

POST   /application/start        → start pipeline for an approved job
POST   /application/submit       → execute submission after approval
GET    /application/pipelines    → list pipelines for a candidate
…       (see backend/api/application.py)

GET    /review/queue             → pipelines awaiting review
POST   /review/{id}/approve      → approve pipeline
POST   /review/{id}/reject       → reject pipeline
```

Exact endpoint lists are in the per-domain router files. Adding endpoints is a leaf-level deliverable, not a brief amendment.

---

## Acceptance criteria (cultivation done)

The cultivation is "ready to harvest" when, on a clean checkout, the operator can:

1. `make up` (docker-compose) → backend healthy at `/health`, Postgres + Redis containers running.
2. Open the dashboard, request a magic link, click through `/auth/verify`, land on Onboarding.
3. Upload a PDF resume → see extracted text preview → fill the profile form → land on Overview.
4. Trigger a Discovery run for the seeded candidate → see the daily digest populate in the Pipeline view.
5. Open ReviewQueue → see a pipeline at `AWAITING_REVIEW` with the four artifact panels (parsed JD / tailored resume diff / company intel / outreach draft) and one contact card.
6. Approve → pipeline transitions to `SUBMITTED` → AutoApply runs against a real job URL on a sandbox/test ATS (Greenhouse demo or equivalent) → status reaches `SENT`.
7. `./deploy/deploy.sh staging backend <git-sha>` succeeds end-to-end with the Digital Dash pipeline passing all stages green.
8. Every agent transition is visible on the Dashboard via the Redis pub/sub channels.

`tsc --noEmit` is not applicable (Python). Equivalent bar: `ruff check backend/` clean, `pytest tests/ -v` green, frontend `npm run build` clean.

---

## Out of scope (this cultivation)

Explicit non-goals. If a leaf wants to build any of these, it's outside the cultivation contract.

- Multi-candidate concurrent processing (single-candidate MVP)
- Agency dashboard / white-label / multi-tenant role model beyond `candidate_id` FK plumbing
- Production email sending in `/auth/request-link` (dev returns link in body; prod email is a TODO)
- Real ATS authentication / login automation in `auto_apply` (assume public application forms or pre-authenticated session)
- CAPTCHA solving
- Stripe / PESO billing
- Mycelium HYPHA NODE wrappers (designed-for, not built — `BaseAgent`-compat interfaces stay aspirational until a future cultivation)
- Bloom identity-card integration (the `personal_context` field is reserved; no Bloom API wiring yet)
- Background `framework_watcher` / `pattern_extractor` agents from `03-vibespace-framework.md` (framework directory remains empty scaffold)
- Push notifications (in-app banners only)
- Mobile app (web dashboard only)
- Detailed analytics dashboards beyond the existing Analytics page shell

---

## Constraints + guardrails

- **No agent architecture changes.** The existing pipeline is locked. Refactors that change call signatures, schemas, or pipeline ordering require a brief amendment.
- **Apache 2.0 license header** on every new file (per repo CLAUDE.md).
- **No `print()`** — `structlog` only. **No `requests`** — `httpx` only. **No bare `except:`.**
- **No hardcoded secrets, URLs, or config values.** Everything goes through `backend/config.py` (Pydantic Settings).
- **No `git` from leaves.** Use `./auto-commit.sh` per repo CLAUDE.md's AUTO-COMMIT RULE — one commit per discrete task.
- **`git push --force` requires explicit confirmation. `rm -rf` outside `/tmp` requires explicit confirmation.** Per global CLAUDE.md.
- **Mycelium vocabulary stays precise** — HYPHA / NUTRIENTS / BIOME BUS / FRUITING BODY etc. Used correctly or ask.
- **Multi-tenancy is design-only.** `candidate_id` FK is everywhere; agency-level features are not in scope.

---

## Open questions (resolve before freeze, or accept defaults)

| Question | Default if unanswered | Sharper with answer |
|---|---|---|
| AWS account ID + ECR push permissions for staging? | Block on first `deploy-staging` run | Pre-bootstrap via `deploy/setup-aws.sh`, prime ECR repos |
| Production magic-link email provider (Postmark? SES? Resend?) | Leave the TODO in `/auth/request-link`; dev-mode link return only | Wire the email send in `auth` biome |
| Real test ATS for `auto_apply` end-to-end (Greenhouse demo? a posted-but-stale internal listing?) | AutoApply stays in dry-run for acceptance criterion #6 | Real form submission in CI |
| Crawler sources for the actual job feeds (Greenhouse public API? LinkedIn? aggregator?) | `crawler_agent` stays stubbed; orchestrator runs end-to-end with seeded jobs | Real crawl integration in Phase 1B |
| Frontend auth context: localStorage vs httpOnly cookie for JWT? | localStorage (matches existing `AuthContext.jsx` skeleton) | Cookie path if security tier escalates |

---

## How to run

Single-call pipeline (preferred for this run):

```bash
cd /Users/spy/mfautomation/repos/creation-station/reverse-search
mycelium ddp \
  --brief ./brief.md \
  --stack fastapi-postgres \
  --security startup \
  --concurrency 10 \
  --threshold 0.8
```

Staged invocation (used for first run because the freeze gate needs SPY review before cultivate):

```bash
mycelium plant ./brief.md --stack fastapi-postgres --security startup
mycelium contracts audit
# ── inspection checkpoint (SPY review of NUTRIENTS.md) ──
mycelium contracts freeze
mycelium cultivate -c 10
mycelium harvest -t 0.8
mycelium sporenet serve --port 4173
```

If `mycelium` CLI doesn't yet have a `fastapi-postgres` preset registered, fall back to the closest matching preset and document the substitution in `HANDOFF.md`.

---

## References

- **Repo CLAUDE.md:** `/Users/spy/mfautomation/repos/creation-station/reverse-search/CLAUDE.md`
- **Global CLAUDE.md:** `/Users/spy/.claude/CLAUDE.md`
- **HYPHA exemplars (org pattern):** `/Users/spy/mfautomation/repos/live-grid-run7/hyphae/`
- **Brief exemplar (org pattern):** `/Users/spy/mfautomation/repos/live-grid-run8/brief.md`
- **Mycelium framework:** `/Users/spy/mfautomation/repos/legendary-funicular/`
- **Mycelium orchestrator + 30/60/90:** `/Users/spy/mfautomation/mycelium-orchestrator/`
- **Phase-1 build prompts:** `01-discovery-engine.md`, `02-application-engine.md`
- **Framework spec (deferred):** `03-vibespace-framework.md`
- **Digital Dash pipeline:** `./digital-dash-pipeline.yml`
- **HYPHA contracts:** `./hyphae/HYPHA-*.md` (this cultivation)
