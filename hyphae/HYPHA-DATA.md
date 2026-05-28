# HYPHA-DATA

> HYPHA tag: `TA/DATA`
> Maps to Mycelium agent: `data-agent`

## Goal

Own the single source of truth for all data contracts in Talent Agent: PostgreSQL migrations, SQLAlchemy ORM models, Pydantic v2 schemas, and the shared base/enum types. Every other biome reads from these definitions; only data-agent writes them.

## Scope

### In Scope

**Migrations (SQL):**
- `backend/migrations/000_init.sql` — extensions (uuid-ossp, pg_trgm), enums
- `backend/migrations/001_discovery.sql` — candidates, discovered_jobs, scored_jobs, daily_digests, crawl_runs
- `backend/migrations/002_application.sql` — parsed_jds, tailored_resumes, company_intel, contacts, application_pipelines, crm_events
- `backend/migrations/003_auth.sql` — users, magic_links, update_updated_at_column() trigger

**ORM Models:**
- `backend/models/__init__.py`
- `backend/models/base.py` — declarative `Base` + id/created_at/updated_at columns
- `backend/models/discovery.py` — Candidate, DiscoveredJob, ScoredJob, DailyDigest, CrawlRun
- `backend/models/application.py` — ParsedJD, TailoredResume, CompanyIntel, Contact, ApplicationPipeline, CRMEvent
- `backend/models/auth.py` — User, MagicLink

**Pydantic Schemas:**
- `backend/agents/discovery/schemas.py` — CandidateSchema, DiscoveredJobSchema, ScoredJobSchema, ScoreBreakdown, IdentityProfileSchema, SearchManifestSchema, DailyDigestSchema
- `backend/agents/application/schemas.py` — ParsedJDSchema, TailoredResumeSchema, CompanyIntelSchema, ContactSchema, OutreachEmailSchema, ApplicationPipelineSchema

### Out of Scope

- API endpoint definitions (api-agent owns)
- Agent business logic (discover-agent, apply-agent own)
- Database connection management (`backend/database.py` owned by api-agent)
- New tables for multi-tenant agency features (out of cultivation scope)

## Inputs

- Brief §1 (Database schema) — column lists, FK shapes, enum values
- Brief §11 (Naming conventions)
- CLAUDE.md (UUID PK + created_at + updated_at convention)
- `NUTRIENTS.md` §DATA_CONTRACTS — TypeScript interface mirrors

## Outputs (Deliverables)

### Migrations

- `backend/migrations/000_init.sql`
- `backend/migrations/001_discovery.sql`
- `backend/migrations/002_application.sql`
- `backend/migrations/003_auth.sql`

### ORM Models

- `backend/models/__init__.py`
- `backend/models/base.py`
- `backend/models/discovery.py`
- `backend/models/application.py`
- `backend/models/auth.py`

### Pydantic Schemas

- `backend/agents/discovery/schemas.py`
- `backend/agents/application/schemas.py`

## Acceptance Criteria

- [ ] All four migrations apply cleanly on fresh Postgres 15, in order, with no errors
- [ ] Every table has `id UUID PRIMARY KEY DEFAULT gen_random_uuid()` or `uuid_generate_v4()`
- [ ] Every mutable table has `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()` and `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
- [ ] `update_updated_at_column()` trigger exists and fires on `users`
- [ ] All FK relationships in 002 reference tables in 001 (or earlier 002)
- [ ] All FKs in 003 reference 001 where required (`candidate_id`)
- [ ] SQLAlchemy ORM column types match migration column types exactly
- [ ] Pydantic v2 schemas use `model_config = ConfigDict(from_attributes=True)` where they wrap ORM models
- [ ] `from backend.models import …` imports all model classes without ImportError
- [ ] No `service_role` or admin bypass references in any model
- [ ] `ruff check backend/models/ backend/agents/*/schemas.py` is clean

## Domain Entity Summary

### Discovery Domain

| Table | Description |
|---|---|
| `candidates` | Job seeker profiles with resume, preferences, exclusions |
| `discovered_jobs` | Raw jobs from crawler sources |
| `scored_jobs` | Jobs scored against candidate profile (6-dim) |
| `daily_digests` | Compiled digest per candidate per day |
| `crawl_runs` | Crawler execution tracking |

### Application Domain

| Table | Description |
|---|---|
| `parsed_jds` | Structured JD parsing output |
| `tailored_resumes` | Resume rewrites for specific jobs |
| `company_intel` | Company research artifacts |
| `contacts` | Discovered recipient contacts |
| `application_pipelines` | Pipeline state machine (QUEUED → SENT) |
| `crm_events` | Append-only event log per pipeline |

### Auth Domain

| Table | Description |
|---|---|
| `users` | Authenticated users with candidate link |
| `magic_links` | One-time magic link tokens |

## Notes

- Migrations are plain SQL (not Alembic auto-generated) at this stage. Alembic baseline is a follow-up.
- `pg_trgm` extension loaded in `000_init.sql` for future search; not yet used.
- `application_pipelines.status` enum mirrors the Application state machine in brief §2.
- `users.candidate_id` is `UNIQUE` (1:1 with candidate). On candidate delete it `SET NULL`; user survives.
- Do NOT add columns/tables for agency/multi-tenant features — `candidate_id` FK is the only multi-tenancy plumbing.
- Identity profiles must NEVER fabricate skills — constraint enforced in system prompts, inherited by resume_tailor.
