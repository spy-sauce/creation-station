# Talent Agent — Cultivation Brief (Iteration 5 — Synthetic Monitoring)

> Input to `mycelium cultivate`. Iter-4 shipped the end-to-end loop (Celery beat, SSE stream, frontend apiClient, full test sweep — 20/20 FRUIT_READY · 100% organism health · pushed to origin/main). Now we make the system observe itself in production via a synthetic monitoring harness.
>
> Read `CLAUDE.md`, `NUTRIENTS.md`, `CELLULAR-MAP.md`, and `hyphae/HYPHA-*.md` before acting. This organism runs **cellular: true · gating: contract-freeze · max_depth: 3**. Specialists consume frozen HYPHA stubs, not upstream live code. Iter-4's 14 biomes are frozen.

---

## What we're building

A **synthetic monitoring biome** that exercises the live Discovery → Score → Apply pipeline daily with known-input synthetic candidates, fingerprints the output, and alerts on drift. Synthetics are the analyzation tool: the only honest way to detect crawler regression, scoring drift, or prompt drift in a system whose real candidates are personal and non-reproducible.

The brief from legendary-funicular's MYC 2026-05-10 entry called this out as iter-4-or-later work: *"Mycelium has zero formal reliability data today."* This is that.

## Core goal

Run `mycelium synthetics run --suite=daily` and produce a `synthetics/runs/<ts>/report.json` containing: (a) per-candidate digest fingerprint diff vs the last green baseline, (b) per-source crawler health (HTTP, schema-shape, sample-job-count), (c) per-scorer-dimension score-distribution percentiles vs baseline. If any drift exceeds the contract thresholds, fire `agent.status.synthetics.drift` on Redis pub/sub and write a markdown report.

**Two failure modes the synthetic harness must surface that iter-4 cannot:**
1. **Scoring drift** — same input, different score. Catches Claude version bumps, prompt edits, archetype-generator regressions.
2. **Crawler regression** — upstream API schema change, rate-limit policy shift, or selector breakage in Workday/Playwright path.

## Six design calls (locked — do not delegate)

These are decided up front so the planner cannot pick wrong:

### 1. Synthetic isolation via UUID namespace — no schema changes

Synthetic candidates use `candidate_id` UUIDs deterministically derived from a known seed string under namespace `urn:talent-agent:synthetic:`. Concretely: `uuid5(NAMESPACE_DNS, "synthetic-" + slug)`. Every synthetic `candidate_id` has high-bit pattern `00000000-0000-5xxx-...` (UUIDv5 marker) AND falls under the seed namespace, making them detectable without a schema column. **No new migration. No `candidates.synthetic` boolean. data-agent stays frozen.** Existing queries `WHERE id = ?` still work; analysis queries can `WHERE id::text LIKE '00000000-%'`.

### 2. Drift contract lives in NUTRIENTS — frozen before any leaf builds

A new section `§I — Synthetic Drift Contract` defines:
- **Exact-match fields** (any difference = drift): `digest.top_picks[].job.id`, `digest.top_picks[].job.source`, `digest.top_picks[].job.url`, ordering of `top_picks` first 5
- **Tolerance-match fields** (±N% allowed): each of 6 score dimensions ±5%, composite_score ±3%, `total_jobs_discovered` ±10%
- **Excluded fields** (never compared): `created_at`, `updated_at`, `run_id`, `crawl_run.duration_seconds`, all UUIDs that aren't synthetic-namespace
- **Baseline reset rules**: explicit `mycelium synthetics baseline accept <run_id>` writes a new fingerprint; drift compares against latest accepted baseline only

Without this in a frozen contract, the fingerprint leaf produces vague output and the alert leaf fires on noise.

### 3. Split scoring-drift from crawler-health — different biomes, different cadence

These look adjacent but have orthogonal failure modes:

| Biome | Inputs | Cadence | Alert threshold |
|---|---|---|---|
| `synthetics-scoring` | 12 local JD fixtures, 3 synthetic candidates | Daily 03:00 ET | Any exact-match drift OR tolerance breach |
| `synthetics-crawler` | Real upstream APIs (Greenhouse/Lever/Ashby head only, no Workday) | Hourly | 3 consecutive failures OR schema shape change |

Scoring is deterministic given fixed JDs + fixed prompt + fixed candidate → fingerprints are reproducible. Crawler health is inherently flaky (rate limits, transient 5xx) → different threshold logic. **Bundling them = the alert dashboard becomes noise within a week.**

### 4. Recurring monthly budget — aggressive cache, deterministic inputs

Iter-4 was $7-10 once. Synthetics is `3 candidates × 12 JDs × scorer Claude calls × daily = ~108 Claude calls/day`. At ~$0.04/call that's $4.32/day = **~$130/month uncached**. With cache: synthetic inputs are byte-identical day over day, so every call after run 1 should be a prompt-cache hit (~90% discount) → target $13/month.

The mycelium.yaml gains:
```yaml
synthetics:
  budget:
    monthlyUsd: 20
    abort_threshold_pct: 150   # halt suite if monthly burn projects > $30
  cache:
    aggressive: true
    prompt_cache_required: true  # first run warms cache, subsequent runs MUST hit it
```

If a leaf cannot use the prompt cache (Claude API direct calls, no cache_control), it's a contract violation, not an optimization opportunity.

### 5. Local-first — synthetics monitor docker-compose, not "prod"

iter-4 shipped ECS task defs but `deploy/setup-aws.sh` never ran. There is no production deployment. The brief is honest: synthetic monitoring runs against `docker-compose up`'d backend on localhost first.

A `synthetics.target` field in mycelium.yaml selects: `local` (default, against http://localhost:8000) or `remote` (against `SYNTHETICS_TARGET_URL` env var). The remote path is built but not exercised this iteration. When `setup-aws.sh` runs in a later iteration, synthetics flips its target with one env var. **Zero code changes between local and remote.**

### 6. audit-run does NOT host this

`mycelium audit-run` is for biome-level tester HYPHAs that QA a *cultivation*. Synthetics is **runtime monitoring of a deployed system**, not framework QA. Different lifecycle, different state, different alerts. Adjacent but orthogonal. iter-5 builds new infrastructure; audit-run integration is out of scope.

---

## Organisms (new biomes — 3 total)

### synthetics-fixtures — the synthetic inputs themselves

`data-agent`, `auth-agent` must be frozen (they are). No new schema.

**Hard requirements:**

- `synthetics/fixtures/candidates.yaml` — 3 synthetic candidates with full resume text + identity context. Each maps to a deterministic UUIDv5 in the synthetic namespace.
  - `synthetic-jr-engineer` — entry-level full-stack, NYC, $80-110k target
  - `synthetic-senior-ml` — staff-level ML engineer, Bay Area, $250-350k target
  - `synthetic-mid-product` — senior product manager, remote, $150-200k target
- `synthetics/fixtures/jobs/` — 12 JD markdown files. 4 strong matches, 4 weak matches, 4 mismatches per candidate (overlapping where appropriate). Filenames embed expected `is_hot` flag and expected composite score band.
- `synthetics/fixtures/baselines/` — gitignored at first; written by `mycelium synthetics baseline accept`. Each baseline is `<candidate_id>__<run_id>.json` containing a frozen digest snapshot.
- `synthetics/fixtures/seeder.py` — idempotent loader that upserts the 3 synthetic candidates into Postgres on backend boot (called from `lifespan`). Detects existing rows by UUID and no-ops.

**Acceptance:**

- `python -c "from synthetics.fixtures.seeder import seed; import asyncio; asyncio.run(seed())"` is idempotent.
- `SELECT * FROM candidates WHERE id::text LIKE '00000000-%'` returns exactly 3 rows after seeding.
- All 12 JDs have valid front-matter declaring `expected_hot` (bool) and `expected_score_band` (one of `low`, `mid`, `high`).

### synthetics-scoring — deterministic scoring drift detection

`discover-agent`, `apply-agent`, `obs-agent` frozen. Consumes `synthetics-fixtures`.

**Hard requirements:**

- `backend/synthetics/scoring_runner.py` — `ScoringSyntheticRunner.run_suite()` iterates the 3 synthetic candidates × 12 JDs, calls the real `RelevanceScorer.score_batch` directly (no crawler), produces a `ScoringFingerprint` per candidate.
- `backend/synthetics/fingerprint.py` — `compute_fingerprint(digest, contract)` reads NUTRIENTS §I and produces a stable JSON object with the exact-match fields verbatim and the tolerance-match fields as `{value, baseline, drift_pct}`.
- `backend/synthetics/diff.py` — `diff_against_baseline(fingerprint, baseline, contract) -> DriftReport`. Returns `{exact_violations: [...], tolerance_violations: [...], severity: 'green'|'yellow'|'red'}`.
- `backend/synthetics/cli.py` — `python -m backend.synthetics run --suite=scoring` reads candidates+JDs, runs scoring, writes `synthetics/runs/<ts>/scoring-report.json`, publishes `agent.status.synthetics.drift` if non-green.
- **Cache contract**: every Claude call must set `cache_control={"type": "ephemeral"}` on the system prompt + candidate identity. First run primes; subsequent runs verify `cache_creation_input_tokens == 0` and `cache_read_input_tokens > 0`. If verification fails, write a `cache_miss` event and continue (don't abort — log loudly).

**Acceptance:**

- Running the suite twice within 5 min produces identical fingerprints AND >90% cache hit rate (verified from response usage block).
- Mutating one JD's text and re-running produces a non-empty `DriftReport` localized to that JD.
- Mutating one score weight in `relevance_scorer.py` and re-running surfaces the drift across all 12 JDs.

### synthetics-crawler — upstream health monitoring

`discover-agent`, `obs-agent` frozen. Independent of `synthetics-fixtures` (real upstreams, no synthetic data).

**Hard requirements:**

- `backend/synthetics/crawler_health.py` — `CrawlerHealthRunner.run_suite()` hits one known-good slug per source (Greenhouse `anthropic`, Lever `netflix`, Ashby `posthog`) with HEAD-equivalent (small `?limit=1` if supported, full GET otherwise) and asserts: HTTP 200, response is JSON, top-level shape matches `expected_schema_v1.json`, `jobs` array has ≥1 entry.
- Workday is **not** in scope for hourly health checks — Playwright is too expensive per hour. Workday gets a separate daily check via the scoring suite (it's exercised when synthetic candidates pull from it).
- `backend/synthetics/crawler_health.py` writes `synthetics/runs/<ts>/crawler-report.json` with per-source `{status, latency_ms, schema_match, sample_jobs}`.
- **Alert state machine**: track per-source `consecutive_failures` in `synthetics/state.json`. Publish `agent.status.synthetics.crawler` red only after **3 consecutive failures** for the same source. Resets on first success. This prevents flapping on transient 5xx.
- Hourly invocation via Celery beat (new entry in `backend/scheduler/beat.py` — extends frozen biome via the *additive* path: only NEW schedule entries, no changes to `daily_discovery_task`).

**Acceptance:**

- `curl http://localhost:8000/events/stream?channel=agent.status.synthetics.crawler` shows health pings live during a manual `python -m backend.synthetics run --suite=crawler` invocation.
- Pointing the suite at a deliberately-wrong slug for one source produces `status: failed, consecutive_failures: 1` and does NOT alert.
- Three consecutive failures produces `status: red, consecutive_failures: 3` and publishes a drift event.
- A success after 3 failures resets to `status: green, consecutive_failures: 0` and publishes recovery.

---

## Mycelium framework additions

These land at the framework level (legendary-funicular CLI), not in this repo. **Do not write them as leaves of this cultivation.** Track as follow-ups for legendary-funicular PR #4:

- `mycelium synthetics run --suite=<name>` — invokes `python -m backend.synthetics run`, captures stdout, parses the report, surfaces in `sporenet/state.json` as a non-leaf event.
- `mycelium synthetics baseline accept <run_id>` — copies the run's fingerprint files into `synthetics/fixtures/baselines/`.
- `mycelium synthetics drift` — pretty-print the latest `DriftReport` from any in-progress or completed run.

These are NOT required for iter-5 cultivation to ship. The Python CLI (`python -m backend.synthetics run`) is the cultivation deliverable. The mycelium wrapper is a quality-of-life sugar layer added later.

---

## Mathematics & concurrency

Per CELLULAR-MAP, the organism now has **14 biomes / ~100 leaves at depth-3**. Iter-5 adds 3 biomes with conservative leaf counts:

| Biome | Sub-agents |
|---|---|
| synthetics-fixtures | 4 (candidates yaml, jobs dir, baselines scaffold, seeder) |
| synthetics-scoring | 5 (runner, fingerprint, diff, cli, cache verification) |
| synthetics-crawler | 4 (runner, schemas, state machine, beat schedule extension) |

Total iter-5 leaves: **13**. Run at `-c 4` per legendary-funicular's rate-limit discipline. Wall-clock estimate ~12 min based on iter-4's 20-leaf / 9.8min baseline.

**Budget for cultivation itself:** ~$6-9 (smaller than iter-4 since the 4 new biomes are tighter scope). **Budget for ongoing synthetic operation:** $13/month target, $20/month hard ceiling.

---

## How to run

```bash
cd /Users/spy/mfautomations/repos/creation-station/reverse-search

# Wave 1 — fixtures land first (independent)
mycelium cultivate --only-biome synthetics-fixtures -c 2

# Wave 2 — scoring + crawler in parallel (independent, both consume fixtures)
mycelium cultivate --only-biome synthetics-scoring -c 4
mycelium cultivate --only-biome synthetics-crawler -c 4

# (Or one shot, excluding the 14 frozen biomes)
mycelium cultivate --exclude-biome data-agent design-agent auth-agent obs-agent \
  discover-agent apply-agent agents-agent api-agent frontend-agent infra-agent \
  scheduler-agent api-streaming-agent api-client-agent tests-agent -c 4
```

Then harvest:
```bash
mycelium harvest -t 0.8   # framework rollup fix landed in PR #3
```

---

## What MUST NOT happen

- **No schema changes.** Synthetics use UUID namespace, not a new column or table. data-agent stays frozen.
- **No `Candidate.synthetic = True` boolean anywhere.** The UUID prefix IS the marker.
- **No new top-level dependencies.** `httpx`, `pydantic`, `pyyaml`, `redis` already in `requirements.txt`. Anything else is a contract amendment, not a leaf decision.
- **No Workday hourly health checks.** Playwright is too expensive per hour. Daily only, via the scoring suite path.
- **No bypassing the cache.** Every Claude call in synthetics has `cache_control={"type": "ephemeral"}`. A leaf that omits it ships a cache-miss event AND fails its own acceptance criterion.
- **No prod-only paths.** The remote target is configured but exercised only in iter-6+. Local docker-compose is the iter-5 surface.
- **No re-cultivation of frozen biomes.** Iter-4's 14 biomes are sealed. The crawler-health beat schedule extension lives in `backend/synthetics/`, not `backend/scheduler/`, and is registered from there via the existing Celery app import (additive only).
- **No `--no-verify`.** Auto-commit hooks pass.
- **No `print()`.** `structlog` only. Frontend uses logging utility.
- **No concurrency above `-c 4`.** Cache observability lands later.
- **No mocking the Claude API in scoring runs.** Synthetic INPUTS are mock; the scorer is real. That's the entire point.

---

## Acceptance (organism-level)

The cultivation is successful when ALL of the following are true:

1. `pytest tests/synthetics/ -v` → exit 0.
2. `npx tsc --noEmit` and `npm test -- --run` in frontend → still clean (no regressions to iter-4).
3. `python -m backend.synthetics run --suite=scoring` against a freshly-seeded docker-compose backend produces `synthetics/runs/<ts>/scoring-report.json` with green status on first run AND second run (baseline written between).
4. `python -m backend.synthetics run --suite=crawler` produces `synthetics/runs/<ts>/crawler-report.json` with three sources reporting status `green`.
5. Mutating one score weight in the scorer and re-running scoring suite produces a non-empty `DriftReport` with severity `yellow` or `red`.
6. Three sequential simulated upstream failures produces a single `agent.status.synthetics.crawler` red event — not three separate events.
7. Two sequential clean runs of the scoring suite (within 5 min) show `cache_read_input_tokens > 0` on the second run for every Claude call.
8. `cat synthetics/state.json` shows `consecutive_failures: 0` for every source after a successful crawler run.

If 1-2 fail, fix the leaves and re-cultivate. If 3-8 fail, the synthetic harness can't see itself — that's a deeper design problem, file an issue, do not paper over with `--skip` flags.

---

## Why this iteration matters

Without synthetics, the loop iter-4 closed is invisible after it ships. The frontend renders mock data when the backend is down; the orchestrator runs once a day and nobody knows if it produced the right output until a human checks. Iter-5 makes the system observable to itself: the synthetics ARE the witness. If the discovery pipeline drifts — Claude version bump, crawler API change, scorer regression — the synthetic harness sees it within 24 hours, fingerprints exactly what changed, and screams. That's the foundation every later iteration depends on. iter-6 can finally deploy to prod without flying blind.

*The Dot Connects.*
