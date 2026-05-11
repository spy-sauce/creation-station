# HYPHA-SCHEMA-CORE

> HYPHA tag: `TA/SCHEMA`

## Goal

Own the single source of truth for all data contracts in Talent Agent: Postgres migrations, SQLAlchemy ORM models, Pydantic v2 schemas, and the shared base/enum types. Every other biome reads from these definitions; only schema-core writes them.

## Scope

### In Scope
- `backend/migrations/000_init.sql` — extensions (uuid-ossp, pg_trgm), enums (`job_status`, `application_status`)
- `backend/migrations/001_discovery.sql` — candidates, discovered_jobs, scored_jobs, daily_digests, crawl_runs
- `backend/migrations/002_application.sql` — parsed_jds, tailored_resumes, company_intel, contacts, application_pipelines, crm_events
- `backend/migrations/003_auth.sql` — users, magic_links, `update_updated_at_column()` trigger
- `backend/models/base.py` — declarative `Base` + id/created_at/updated_at columns
- `backend/models/discovery.py` — Candidate, DiscoveredJob, ScoredJob, DailyDigest, CrawlRun
- `backend/models/application.py` — ParsedJD, TailoredResume, CompanyIntel, Contact, ApplicationPipeline, CRMEvent
- `backend/models/auth.py` — User, MagicLink
- `backend/agents/discovery/schemas.py` — Pydantic v2 schemas (CandidateSchema, DiscoveredJobSchema, ScoredJobSchema, ScoreBreakdown, IdentityProfileSchema, SearchManifestSchema, DailyDigestSchema)
- `backend/agents/application/schemas.py` — Pydantic v2 schemas (ParsedJDSchema, TailoredResumeSchema, CompanyIntelSchema, ContactSchema, OutreachEmailSchema, ApplicationPipelineSchema)

### Out of Scope
- API endpoint definitions (api-surface owns)
- Agent business logic (discovery-engine, application-engine own)
- Database connection management (lives in `backend/database.py`, owned by api-surface)
- New tables for multi-tenant agency features (out of cultivation scope)

## Inputs

- Brief §1 (Database schema) — column lists, FK shapes, enum values
- Brief §11 (Naming conventions)
- Repo CLAUDE.md (UUID PK + created_at + updated_at convention on every table)

## Outputs (Deliverables)

Existing files locked at HEAD `26143cd`:
- `backend/migrations/000_init.sql`
- `backend/migrations/001_discovery.sql`
- `backend/migrations/002_application.sql`
- `backend/migrations/003_auth.sql`
- `backend/models/__init__.py`
- `backend/models/base.py`
- `backend/models/discovery.py`
- `backend/models/application.py`
- `backend/models/auth.py`
- `backend/agents/discovery/schemas.py`
- `backend/agents/application/schemas.py`

## Acceptance Criteria

- [ ] All four migrations apply cleanly on a fresh Postgres 15 instance, in order, with no errors
- [ ] Every table has `id UUID PRIMARY KEY DEFAULT … gen_random_uuid() | uuid_generate_v4()`
- [ ] Every mutable table has `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()` and `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
- [ ] `update_updated_at_column()` trigger exists and fires on `users` (and any other mutable rows where the model declares `onupdate=func.now()`)
- [ ] All FK relationships in 002 reference tables in 001 (or earlier 002), all FKs in 003 reference 001 where required (`candidate_id`)
- [ ] SQLAlchemy ORM column types match migration column types exactly
- [ ] Pydantic v2 schemas use `model_config = ConfigDict(from_attributes=True)` where they wrap ORM models
- [ ] `from backend.models import …` imports all model classes without ImportError
- [ ] No `service_role` or admin bypass references in any model
- [ ] `ruff check backend/models/ backend/agents/*/schemas.py` is clean

## Notes

- Migrations are plain SQL (not Alembic) at this stage — Alembic is in the stack but not yet bootstrapped. Adding Alembic baseline is a follow-up, not part of this freeze.
- `pg_trgm` extension is loaded in `000_init.sql` to support future search; not yet used.
- The `application_pipelines.status` enum mirrors the Application state machine in brief §2 — adding a state requires a brief amendment.
- `users.candidate_id` is `UNIQUE` (1:1 with candidate). On candidate delete it `SET NULL`; the user account survives.
- Do NOT add columns or tables for agency / multi-tenant features — `candidate_id` FK is the only multi-tenancy plumbing in this cultivation.
