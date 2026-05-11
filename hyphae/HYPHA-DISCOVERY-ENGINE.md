# HYPHA-DISCOVERY-ENGINE

> HYPHA tag: `TA/DISCOVER`

## Goal

Own the daily reverse-engineered discovery pipeline that turns a candidate's full identity into a ranked digest of relevant roles. Six sub-agents coordinated by `DiscoveryOrchestrator`; persisted to Postgres, published to Redis pub/sub.

## Scope

### In Scope
- `IdentityProfiler` — Claude-driven identity extraction from resume + context; 24h Redis cache keyed by candidate
- `ArchetypeGenerator` — expands identity into a search manifest (target_titles, keywords, exclusions)
- `CrawlerAgent` — manifest → raw job list (stubbed in Phase 1A; pluggable for real sources)
- `RelevanceScorer` — 6-dimension weighted scoring: technical_match, level_match, culture_match, industry_match, growth_potential, compensation_match → composite + `is_hot`
- `DigestBuilder` — compose `daily_digests` row from scored jobs (top_picks, hot_picks, new_companies)
- `DiscoveryOrchestrator` — pipeline coordinator with `CrawlRun` state tracking + structured logging + `dry_run` mode
- Concurrency: bounded scoring via `asyncio.Semaphore(settings.crawl_concurrency)`
- Events on `agent.status.discovery`

### Out of Scope
- Real crawler integrations (stub stays; real sources are Phase 1B)
- Application pipeline (application-engine owns)
- Frontend rendering of the digest (review-dashboard owns)
- Cron scheduling (Celery beat is in the stack but not yet wired — TODO outside this freeze)

## Inputs

- schema-core: `Candidate`, `DiscoveredJob`, `ScoredJob`, `DailyDigest`, `CrawlRun` ORM models; matching Pydantic schemas (`CandidateSchema`, `DiscoveredJobSchema`, `ScoredJobSchema`, `ScoreBreakdown`, `IdentityProfileSchema`, `SearchManifestSchema`, `DailyDigestSchema`)
- `backend/database.py`: `get_db` (async session) and Redis client factory
- `backend/config.py`: `anthropic_api_key`, `crawl_concurrency`, `min_score`
- Anthropic SDK: `AsyncAnthropic`, model `claude-sonnet-4-20250514`

## Outputs (Deliverables)

Existing files locked at HEAD:
- `backend/agents/discovery/__init__.py`
- `backend/agents/discovery/schemas.py`
- `backend/agents/discovery/identity_profiler.py`
- `backend/agents/discovery/archetype_generator.py`
- `backend/agents/discovery/crawler_agent.py`
- `backend/agents/discovery/relevance_scorer.py`
- `backend/agents/discovery/digest_builder.py`
- `backend/agents/discovery/orchestrator.py`
- `tests/discovery/` — smoke tests (existing)

Internal contracts:
- `DiscoveryOrchestrator.run(candidate_id, dry_run=False) -> DailyDigestSchema`
- 24h identity profile cache key: `profile:candidate:{candidate_id}` in Redis
- `crawl_runs` lifecycle: `QUEUED → RUNNING → COMPLETED | FAILED`

## Acceptance Criteria

- [ ] `DiscoveryOrchestrator.run(candidate_id)` on a seeded candidate completes without exceptions
- [ ] A `crawl_runs` row is created on start with `status="RUNNING"`, transitions to `COMPLETED` with `jobs_discovered` and `jobs_scored` populated
- [ ] On exception, the `crawl_runs` row transitions to `FAILED` with `error_log` set, then the exception re-raises
- [ ] `dry_run=True` skips all DB writes and returns an in-memory digest with empty picks lists
- [ ] `IdentityProfiler.build_profile()` returns a populated `IdentityProfileSchema` (archetypes, leadership_level, signals)
- [ ] Second call within 24h hits the Redis cache (no Claude call)
- [ ] `ArchetypeGenerator.expand(profile, excluded)` returns a `SearchManifestSchema` honoring excluded titles/companies/industries
- [ ] `CrawlerAgent.run(manifest)` returns a list of `DiscoveredJobSchema` (stub returns deterministic fixtures in Phase 1A)
- [ ] `RelevanceScorer.score_batch(raw_jobs, profile, min_score)` filters out jobs below `min_score` and assigns 6 component scores + composite + reasoning
- [ ] `DigestBuilder.compile(...)` writes a `daily_digests` row keyed by `(candidate_id, run_date)`
- [ ] Structured logs emitted at every stage (`orchestrator.candidate_loaded`, `orchestrator.profile_built`, `orchestrator.manifest_built`, `orchestrator.crawl_complete`, `orchestrator.scoring_complete`, `orchestrator.run_complete`, `orchestrator.run_failed`)
- [ ] No `print()` anywhere in the biome
- [ ] All Claude calls use `claude-sonnet-4-20250514`
- [ ] `pytest tests/discovery/ -v` passes
- [ ] `ruff check backend/agents/discovery/` clean

## Notes

- The 24h profile cache is intentional — identity drift on the same resume between runs is noise. Force-refresh requires a cache delete (no API for it yet; manual `DEL profile:candidate:*` is fine).
- `RelevanceScorer.score_batch` does not currently use the `score_with_semaphore` wrapper in `orchestrator.py` (line ~122) — the wrapper is defined but the scorer self-bounds. Leave as-is for the freeze; don't refactor.
- `CrawlerAgent` is deliberately stubbed in Phase 1A. Replacing the stub with real sources (Greenhouse API, Lever API, aggregators) is Phase 1B — a separate leaf, not part of this cultivation.
- `is_hot` is a 6-dim threshold flag set by the scorer; not a separate Claude call.
- Pub/sub channel `agent.status.discovery` is reserved here but not yet published from this biome's code (the application orchestrator does publish its own channel). Wiring discovery's pub/sub publishes is a deliverable inside this HYPHA — `_publish_status` helper to add, following the pattern from `application/orchestrator.py:325-336`.
- Identity profiles must NEVER fabricate skills. The system prompt enforces this; resume_tailor consumes the profile and inherits the constraint.
