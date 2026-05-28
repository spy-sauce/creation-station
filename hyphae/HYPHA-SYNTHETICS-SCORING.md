# HYPHA-SYNTHETICS-SCORING

> HYPHA tag: `TA/SYNTH-SCORE`
> Maps to Mycelium agent: `synthetics-scoring-agent`

## Goal

Own the deterministic scoring drift detection harness. Exercise the real `RelevanceScorer` against synthetic candidates and JD fixtures, compute stable fingerprints, compare against accepted baselines, and surface drift reports. This biome is the witness: if Claude changes, if prompts drift, if the archetype generator regresses — the scoring harness sees it within 24 hours.

## Scope

### In Scope

- `backend/synthetics/__init__.py` — module init
- `backend/synthetics/scoring_runner.py` — `ScoringSyntheticRunner.run_suite()` orchestration
- `backend/synthetics/fingerprint.py` — `compute_fingerprint(digest, contract)` stable JSON generation
- `backend/synthetics/diff.py` — `diff_against_baseline(fingerprint, baseline, contract)` → `DriftReport`
- `backend/synthetics/cli.py` — `python -m backend.synthetics run --suite=scoring` CLI entry
- Cache contract enforcement — verify `cache_control={"type": "ephemeral"}` on every Claude call
- Cache verification — check `cache_creation_input_tokens == 0` on subsequent runs

### Out of Scope

- Synthetic candidate fixtures (owned by `synthetics-fixtures-agent`)
- Crawler health monitoring (owned by `synthetics-crawler-agent`)
- Schema changes — no new tables, no new columns
- Mocking the Claude API — synthetic INPUTS are mock, the scorer is real
- Baseline acceptance workflow — that's a future CLI command (`mycelium synthetics baseline accept`)

## Inputs

- `synthetics-fixtures-agent`: Synthetic candidates + JD fixtures
- `discover-agent` (FROZEN): `RelevanceScorer` class with `score_batch()` method
- `obs-agent` (FROZEN): `publish_event(channel, payload)` for drift alerts
- `NUTRIENTS.md §I.2-I.5`: Drift contract fields, baseline management, cache contract

## Outputs (Deliverables)

- `backend/synthetics/__init__.py`
- `backend/synthetics/scoring_runner.py`
- `backend/synthetics/fingerprint.py`
- `backend/synthetics/diff.py`
- `backend/synthetics/cli.py`
- `synthetics/runs/` — directory for run output (gitignored)
- `synthetics/runs/.gitkeep`

## Acceptance Criteria

- [ ] `python -m backend.synthetics run --suite=scoring` produces `synthetics/runs/<ts>/scoring-report.json`
- [ ] Running the suite twice within 5 minutes produces **identical fingerprints**
- [ ] Second run shows **>90% cache hit rate** verified from Claude API response usage block
- [ ] Mutating one JD's text and re-running produces a non-empty `DriftReport` localized to that JD
- [ ] Mutating one score weight in `relevance_scorer.py` and re-running surfaces drift across all 12 JDs
- [ ] Every Claude call sets `cache_control={"type": "ephemeral"}` on system prompt + candidate identity
- [ ] If `cache_creation_input_tokens > 0` on subsequent runs, a `cache_miss` event is written to the report
- [ ] `agent.status.synthetics.drift` event is published if `DriftReport.severity != 'green'`
- [ ] No `print()` anywhere — `structlog` only
- [ ] `ruff check backend/synthetics/` clean
- [ ] `pytest tests/synthetics/ -v` → exit 0

## Notes

### Run Flow

```
python -m backend.synthetics run --suite=scoring

1. Load synthetic candidates from database (WHERE id::text LIKE '00000000-%')
2. Load JD fixtures from synthetics/fixtures/jobs/
3. For each candidate × JD pair:
   a. Call RelevanceScorer.score_batch() with cache_control
   b. Collect score dimensions and composite score
   c. Track cache hit/miss from response usage
4. Compute fingerprint per candidate
5. Load baseline (if exists) from synthetics/fixtures/baselines/
6. Diff fingerprint against baseline
7. Write synthetics/runs/<ts>/scoring-report.json
8. If drift detected, publish agent.status.synthetics.drift event
9. Exit 0 (success) or 1 (hard failure only — drift is reported, not failed)
```

### Fingerprint Stability

The fingerprint MUST be byte-stable across runs. Key decisions:

1. **Sort all arrays by a deterministic key** (job_id for top_picks)
2. **Round floating-point scores to 4 decimal places** to avoid IEEE precision drift
3. **Exclude timestamps and run_ids** from fingerprint comparison
4. **Include ordering of first 5 top_picks** as an exact-match field

### Cache Contract Enforcement

Every Claude API call MUST include:

```python
messages=[
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"}
            },
            {
                "type": "text",
                "text": candidate_identity,
                "cache_control": {"type": "ephemeral"}
            },
            {
                "type": "text",
                "text": jd_text
            }
        ]
    }
]
```

The scorer module is FROZEN. If it doesn't support `cache_control`, the synthetics-scoring-agent must call the Claude API directly (bypassing the scorer's internal call) or wrap the scorer with cache-aware instrumentation. Do NOT modify the frozen `relevance_scorer.py`.

### Drift Severity Rules

From NUTRIENTS.md §I.4:

```
green: zero violations
yellow: tolerance violations only, no exact-match violations
red: any exact-match violation OR tolerance violation > 2× threshold
```

### Report File Path

`synthetics/runs/<ts>/scoring-report.json`

Where `<ts>` is ISO-8601 UTC timestamp: `2026-05-28T03-00-00Z`

The `synthetics/runs/` directory is gitignored. Reports are ephemeral. Baselines are the permanent record.

### Integration with Celery Beat

The scoring suite runs daily at 03:00 ET. This is NOT wired via scheduler-agent (which is frozen). Instead, synthetics-crawler-agent owns a separate beat schedule extension that additively registers the synthetics tasks.

For this biome (synthetics-scoring-agent), the CLI is the primary interface. Celery scheduling is owned by synthetics-crawler-agent via the additive beat extension.
