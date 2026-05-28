# HYPHA-DISCOVERY-ENGINE

> HYPHA tag: `TA/DISCOVER`
> Maps to Mycelium agent: `discover-agent`

## Goal

Own the daily reverse-engineered discovery pipeline that turns a candidate's full identity into a ranked digest of relevant roles. Six sub-agents coordinated by `DiscoveryOrchestrator`; persisted to Postgres, published to Redis pub/sub.

**Iter-4 Focus:** Close the pub/sub gap. The orchestrator must publish status events on `agent.status.discovery` at every stage, enabling real-time dashboard updates via SSE.

## Scope

### In Scope

- `IdentityProfiler` — Claude-driven identity extraction from resume + context; 24h Redis cache keyed by candidate
- `ArchetypeGenerator` — expands identity into a search manifest (target_titles, keywords, exclusions)
- `CrawlerAgent` — manifest → raw job list via real adapters (Greenhouse, Lever, Ashby, Workday)
- `RelevanceScorer` — 6-dimension weighted scoring: technical_match, level_match, culture_match, industry_match, growth_potential, compensation_match → composite + `is_hot`
- `DigestBuilder` — compose `daily_digests` row from scored jobs (top_picks, hot_picks, new_companies)
- `DiscoveryOrchestrator` — pipeline coordinator with `CrawlRun` state tracking + structured logging + `dry_run` mode
- **`_publish_status` helper** — (NEW in iter-4) async helper that publishes to `agent.status.discovery` channel
- **Per-source `CRAWL_SOURCE_COMPLETE` events** — (NEW in iter-4) emit per-adapter progress, not just rollup
- Concurrency: bounded scoring via `asyncio.Semaphore(settings.crawl_concurrency)`
- Events on `agent.status.discovery`

### Out of Scope

- Application pipeline (application-engine owns)
- Frontend rendering of the digest (review-dashboard owns)
- Cron scheduling (scheduler-agent owns — see HYPHA-SCHEDULER)
- SSE streaming endpoint (api-streaming-agent owns — see HYPHA-API-STREAMING)

## Inputs

- schema-core: `Candidate`, `DiscoveredJob`, `ScoredJob`, `DailyDigest`, `CrawlRun` ORM models; matching Pydantic schemas (`CandidateSchema`, `DiscoveredJobSchema`, `ScoredJobSchema`, `ScoreBreakdown`, `IdentityProfileSchema`, `SearchManifestSchema`, `DailyDigestSchema`)
- `backend/database.py`: `get_db` (async session) and Redis client factory
- `backend/config.py`: `anthropic_api_key`, `crawl_concurrency`, `min_score`
- `obs-agent`: `publish_event(channel, payload)` from `backend/obs/publisher.py`
- Anthropic SDK: `AsyncAnthropic`, model `claude-sonnet-4-20250514`

## Outputs (Deliverables)

Existing files (locked at HEAD, minor iter-4 edits only):
- `backend/agents/discovery/__init__.py`
- `backend/agents/discovery/schemas.py`
- `backend/agents/discovery/identity_profiler.py`
- `backend/agents/discovery/archetype_generator.py`
- `backend/agents/discovery/crawler_agent.py`
- `backend/agents/discovery/relevance_scorer.py`
- `backend/agents/discovery/digest_builder.py`
- `backend/agents/discovery/orchestrator.py` — (iter-4 edits: `_publish_status` helper, per-source events, remove stale comments)
- `tests/discovery/` — smoke tests (existing) + `test_orchestrator_pubsub.py` (new)

Internal contracts:
- `DiscoveryOrchestrator.run(candidate_id, dry_run=False) -> DailyDigestSchema`
- 24h identity profile cache key: `profile:candidate:{candidate_id}` in Redis
- `crawl_runs` lifecycle: `QUEUED → RUNNING → COMPLETED | FAILED`

## Acceptance Criteria

### Existing (from frozen contract)

- [ ] `DiscoveryOrchestrator.run(candidate_id)` on a seeded candidate completes without exceptions
- [ ] A `crawl_runs` row is created on start with `status="RUNNING"`, transitions to `COMPLETED` with `jobs_discovered` and `jobs_scored` populated
- [ ] On exception, the `crawl_runs` row transitions to `FAILED` with `error_log` set, then the exception re-raises
- [ ] `dry_run=True` skips all DB writes and returns an in-memory digest with empty picks lists
- [ ] `IdentityProfiler.build_profile()` returns a populated `IdentityProfileSchema` (archetypes, leadership_level, signals)
- [ ] Second call within 24h hits the Redis cache (no Claude call)
- [ ] `ArchetypeGenerator.expand(profile, excluded)` returns a `SearchManifestSchema` honoring excluded titles/companies/industries
- [ ] `CrawlerAgent.run(manifest)` returns a list of `DiscoveredJobSchema` using real adapters
- [ ] `RelevanceScorer.score_batch(raw_jobs, profile, min_score)` filters out jobs below `min_score` and assigns 6 component scores + composite + reasoning
- [ ] `DigestBuilder.compile(...)` writes a `daily_digests` row keyed by `(candidate_id, run_date)`
- [ ] Structured logs emitted at every stage
- [ ] No `print()` anywhere in the biome
- [ ] All Claude calls use `claude-sonnet-4-20250514`

### Iter-4 New (pub/sub gap closure)

- [ ] `_publish_status(candidate_id, event_name, extra=None)` async helper exists in `orchestrator.py`
- [ ] Helper publishes to Redis channel `agent.status.discovery` with payload `{candidate_id, event, ts, **extra}` (ts = ISO-8601 UTC)
- [ ] `redis-cli SUBSCRIBE agent.status.discovery` shows ≥8 events for a single `run(candidate_id)` invocation
- [ ] Events sequence: `RUN_STARTED, CANDIDATE_LOADED, PROFILE_BUILT, MANIFEST_BUILT, CRAWL_SOURCE_COMPLETE×4, CRAWL_COMPLETE, SCORING_COMPLETE, RUN_COMPLETE`
- [ ] `CRAWL_SOURCE_COMPLETE` events include `{source, jobs_found}` per adapter
- [ ] Stale comment `# 4. Crawl (currently stubbed — Phase 1B)` at orchestrator.py ~line 128 is deleted and replaced with `# 4. Crawl across all four sources`
- [ ] The `score_with_semaphore` wrapper (~line 122) is annotated with `# noqa: F841 — reserved for per-job-scoring path` if ruff complains
- [ ] `pytest tests/discovery/test_orchestrator_pubsub.py -v` passes (uses fakeredis, asserts event sequence)
- [ ] `ruff check backend/agents/discovery/` clean

## Notes

- The 24h profile cache is intentional — identity drift on the same resume between runs is noise. Force-refresh requires a cache delete.
- `RelevanceScorer.score_batch` does not currently use the `score_with_semaphore` wrapper in `orchestrator.py`. The wrapper is defined but unused (intentional). **Do not refactor.** Annotate with noqa if linter complains.
- `CrawlerAgent` now has real adapters (iter-3.5 commits `7f4d514`, `b140392`). The stub comments are stale — delete them.
- `is_hot` is a 6-dim threshold flag set by the scorer; not a separate Claude call.
- The `_publish_status` helper follows the pattern from `application/orchestrator.py:325-336`. Copy that structure.
- Identity profiles must NEVER fabricate skills. The system prompt enforces this; resume_tailor consumes the profile and inherits the constraint.
- Events emitted during `dry_run=True` should still publish (useful for testing the pub/sub path without DB writes).
