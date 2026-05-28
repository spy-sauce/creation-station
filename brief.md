# Talent Agent — Cultivation Brief (Iteration 6 — Fix UUID Detection + Verify Iter-5)

> Input to `mycelium cultivate`. Iter-5 shipped synthetic monitoring (13/13 FRUIT_READY, 100% harvest, pushed). But the brief contained a factual error that the planner faithfully replicated everywhere: synthetic-candidate detection via SQL prefix-LIKE doesn't work. Iter-6 fixes the contract, verifies iter-5 actually runs, and captures the first baseline.
>
> Read `CLAUDE.md`, `NUTRIENTS.md` (§I.1 is the contract being amended), `hyphae/HYPHA-SYNTHETICS-*.md`. The 17 prior biomes from iter-1..5 are frozen; this iteration touches only `synthetics-fixtures-agent`, `synthetics-scoring-agent`, and the contract.

---

## The bug

Iter-5's brief said synthetic candidate UUIDs would be detectable via `WHERE id::text LIKE '00000000-%'`. That's factually wrong. **UUIDv5 hashes the namespace + name with SHA-1; the first 8 hex chars of the digest are essentially random.** Empirical verification:

```
synthetic-jr-engineer  -> 3c7eab85-c380-584b-a128-43bba592f163
synthetic-senior-ml    -> 24fd155e-d431-5dd1-9a59-ee9b70c535a6
synthetic-mid-product  -> fb752ea7-1682-5cb8-84b9-b6402e8675a6
```

None start with `00000000-`. The `LIKE '00000000-%'` query returns **zero rows**. Every code path, contract, and HYPHA that depends on this filter is silently broken — including the scoring suite's loader, the WHERE clause in `synthetics/cli.py`, and `NUTRIENTS.md §I.1`'s detection claim.

The UUIDs themselves are fine — deterministic, namespace-isolated, idempotent. **Only the detection mechanism is wrong.** The fix is to detect by membership in a known constant list, not by prefix.

## Core goal

After cultivation: `python -m backend.synthetics run --suite=scoring` against a freshly-seeded docker-compose backend produces a scoring report on the FIRST run, and `mycelium synthetics baseline accept <run_id>` (or a manual filesystem copy until the CLI lands in iter-7) freezes that run as baseline. The SECOND run produces an identical fingerprint with `cache_read_input_tokens > 0` on every Claude call. iter-5's acceptance criteria #3 and #7 actually pass.

## Scope (single biome)

### synthetics-fix-agent — surgical correction across 3 files + 1 contract amendment

`synthetics-fixtures-agent` and `synthetics-scoring-agent` are frozen at the *biome* level. This iteration uses the **additive seam pattern** (proven on iter-5's beat-extension): a NEW file `backend/synthetics/known_ids.py` becomes the single source of truth, and all consumers import from it. The frozen files get one-line import edits, not rewrites.

**Hard requirements:**

#### Leaf 1 — synthetics-fix-agent.known-ids

Create `backend/synthetics/known_ids.py`:

```python
# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Canonical synthetic candidate UUIDs.

Computed once via uuid.uuid5(uuid.NAMESPACE_DNS, "synthetic-<slug>") and
frozen as constants. The seeder produces these exact values deterministically;
this module is the membership oracle for detection.

Contract: NUTRIENTS.md § I.1 (as amended by iter-6).

Why constants instead of computing at import: the seeder MUST produce these
exact UUIDs, and analysis code MUST detect exactly this set. Drift between
compute paths would silently break detection. Constants close the gap.
"""

from uuid import UUID

SYNTHETIC_CANDIDATE_IDS: dict[str, UUID] = {
    "synthetic-jr-engineer": UUID("3c7eab85-c380-584b-a128-43bba592f163"),
    "synthetic-senior-ml":   UUID("24fd155e-d431-5dd1-9a59-ee9b70c535a6"),
    "synthetic-mid-product": UUID("fb752ea7-1682-5cb8-84b9-b6402e8675a6"),
}

SYNTHETIC_CANDIDATE_ID_SET: frozenset[UUID] = frozenset(SYNTHETIC_CANDIDATE_IDS.values())


def is_synthetic(candidate_id: UUID | str) -> bool:
    """Return True iff candidate_id is one of the 3 known synthetic UUIDs."""
    if isinstance(candidate_id, str):
        candidate_id = UUID(candidate_id)
    return candidate_id in SYNTHETIC_CANDIDATE_ID_SET
```

#### Leaf 2 — synthetics-fix-agent.scoring-runner-detection

In `backend/synthetics/scoring_runner.py`, replace the broken SQL filter:

**Before** (line ~260):
```python
WHERE id::text LIKE '00000000-%'
```

**After:**
```python
from backend.synthetics.known_ids import SYNTHETIC_CANDIDATE_IDS
# ... in the query:
WHERE id = ANY(:synthetic_ids)
# bind {"synthetic_ids": list(SYNTHETIC_CANDIDATE_IDS.values())}
```

Also delete the stale comment at line ~241 ("the pattern: id::text LIKE '00000000-%'").

Touch ONLY these two locations. Leave every other line in `scoring_runner.py` byte-identical. The biome's auto-commit must show ≤ 6 changed lines.

#### Leaf 3 — synthetics-fix-agent.seeder-self-verify

In `backend/synthetics/fixtures/seeder.py` (note: actual location is `synthetics/fixtures/seeder.py` per iter-5 layout — confirm via `ls` before editing):

1. Import `SYNTHETIC_CANDIDATE_IDS` from `backend.synthetics.known_ids`.
2. After the upsert loop, add a self-verify block: query `SELECT id FROM candidates WHERE id = ANY(...)` with the 3 known UUIDs; assert the returned set equals `SYNTHETIC_CANDIDATE_ID_SET`. If not, log `seeder.verify_failed` with the diff and raise `RuntimeError("synthetic seeding produced unexpected UUIDs")`.
3. Delete the false docstring claim at lines 11 ("Detection: WHERE id::text LIKE '00000000-%' returns exactly 3 rows.") — replace with: "Detection: backend.synthetics.known_ids.is_synthetic(candidate_id)."

#### Leaf 4 — synthetics-fix-agent.candidates-yaml-cleanup

In `synthetics/fixtures/candidates.yaml` header comment (lines 10-11):

**Before:**
```yaml
# The UUID marker pattern 00000000-0000-5xxx- allows detection via SQL:
#   SELECT * FROM candidates WHERE id::text LIKE '00000000-%'
```

**After:**
```yaml
# These slugs map to deterministic UUIDv5 IDs computed by the seeder via
# uuid5(NAMESPACE_DNS, "synthetic-" + slug). The canonical 3 IDs are frozen
# in backend/synthetics/known_ids.py and used as the detection oracle.
```

#### Leaf 5 — synthetics-fix-agent.contract-amendment

In `NUTRIENTS.md` §I.1 (the Synthetic Candidate Isolation contract):

1. Replace the false UUID marker examples (lines 1403-1407):
   - Remove the three `00000000-0000-5xxx-...` placeholder examples
   - Replace with the actual 3 frozen UUIDs (those listed at the top of this brief)
   - Remove the "Detection: WHERE id::text LIKE '00000000-%' returns exactly 3 rows" sentence
   - Replace with: "Detection: `backend.synthetics.known_ids.is_synthetic(id)` or SQL `WHERE id = ANY(:synthetic_ids)` bound from `SYNTHETIC_CANDIDATE_IDS`."
2. Add a new sub-section §I.1.b "Why constants, not prefix":
   - Document the UUIDv5 SHA-1 distribution fact (first 8 hex chars are not zero)
   - Document the iter-5 lesson: detection mechanism is separate from generation
   - This is mandatory — the lesson must outlive the bug

The contract amendment is a `FRUIT_READY` line in the cultivation report. Mycelium contract freeze rules require this — silent edits to frozen NUTRIENTS sections are forbidden.

#### Leaf 6 — synthetics-fix-agent.tests

Add `tests/synthetics/test_known_ids.py`:

- Assert `len(SYNTHETIC_CANDIDATE_IDS) == 3`
- Assert each value is a valid UUIDv5 (version field == 5)
- Assert `is_synthetic(known_id)` is True for each known UUID
- Assert `is_synthetic(uuid4())` is False
- Assert recomputing from the canonical slugs reproduces the constants exactly: `for slug, expected in SYNTHETIC_CANDIDATE_IDS.items(): assert uuid5(NAMESPACE_DNS, slug) == expected` — this is the crucial invariant; if any future seeder change breaks it, the test fails before the bad code ships.

Add `tests/synthetics/test_seeder_idempotent.py`:

- Mock the DB session.
- Call `seed()` once, capture rows.
- Call `seed()` again, assert no duplicate INSERT, exactly the same row set.
- Inject a corrupted UUID via patched `get_synthetic_id` and assert the self-verify block raises.

---

## Verification gates (must pass before harvest)

These were skipped at the end of iter-5. They are not skippable now.

1. **Local DB seed**: bring `docker-compose up postgres redis backend` to healthy, then run `python -c "from synthetics.fixtures.seeder import seed; import asyncio; asyncio.run(seed())"`. Assert `SELECT count(*) FROM candidates WHERE id = ANY(...)` returns 3.
2. **First scoring run**: `python -m backend.synthetics run --suite=scoring` produces `synthetics/runs/<ts>/scoring-report.json`. Status must be `green` (no baseline yet → drift detector treats first run as the baseline candidate).
3. **Baseline acceptance** (manual until `mycelium synthetics baseline accept` lands in iter-7): copy `synthetics/runs/<ts>/scoring-report.json` to `synthetics/fixtures/baselines/<candidate_id>__<run_id>.json` for each of the 3 candidates.
4. **Second scoring run**: re-run within 5 minutes. Assert (a) identical fingerprints, (b) `cache_read_input_tokens > 0` on every Claude usage block, (c) `cache_creation_input_tokens == 0` on every Claude usage block after the first.
5. **Tampering proof**: temporarily mutate one weight in `relevance_scorer.py` (e.g. multiply `culture_match` weight by 1.5), re-run scoring, assert `DriftReport.severity in ("yellow", "red")`, revert the mutation.

Capture all 5 verification outputs in `synthetics/runs/iter-6-verification/` and reference them in the cultivation's `FRUIT_READY` line.

---

## Workday coverage — accept the gap, document it

iter-5's brief said Workday would be exercised via the scoring suite. That's not true: the scoring suite uses local JD fixtures, never crawls Workday. Workday's Playwright path is unmonitored.

This iteration **accepts the gap explicitly** rather than building Workday monitoring. The reason: an hourly Playwright invocation is too expensive for the synthetics budget (~$0.50/run × 24/day × 30 = $360/month would blow the $20/month cap by 18×). A different architecture — webhook-driven, sampled, or replay-based — is needed and that's iter-8+ scope.

**Deliverable** (no leaf, just a single doc line in the cultivation): append to `NUTRIENTS.md §I.2` a sub-bullet "Known coverage gap: Workday Playwright path is not monitored by iter-6. Tracked for iter-8+ via different architecture."

---

## Mathematics & concurrency

| Biome | Sub-agents |
|---|---|
| synthetics-fix-agent | 6 (known-ids, scoring-runner-detection, seeder-self-verify, candidates-yaml-cleanup, contract-amendment, tests) |

Total iter-6 leaves: **6**. Run at `-c 3` — concurrency tuned down because (a) the contract-amendment leaf cannot run concurrently with the others (it's the only writer of NUTRIENTS §I.1), and (b) the test leaf depends on known-ids landing first. The framework's `blocked_by` will sequence this correctly.

**Budget for cultivation:** ~$3-5 (small leaves, mostly mechanical edits). **Budget for the synthetics runtime AFTER this iteration:** unchanged from iter-5 ($20/month cap, prompt cache required).

Wall-clock estimate: ~6 minutes based on iter-5's 27.7min/13leaves ratio scaled to 6 leaves.

---

## How to run

```bash
cd /Users/spy/mfautomations/repos/creation-station/reverse-search

# Single wave — all 6 leaves can germinate against frozen contracts
mycelium cultivate --only-biome synthetics-fix-agent -c 3
```

After cultivation, **run the 5 verification gates above** and append the results to the cultivation's HANDOFF entry. Then harvest:

```bash
mycelium harvest -t 0.8
```

---

## What MUST NOT happen

- **No re-cultivation of the 17 frozen biomes.** This is a surgical patch. Touching any frozen file outside the explicit scope = the leaf rejects its own work.
- **No new tables or columns.** UUID-namespace isolation stands; only the detection query changes.
- **No "let's also fix X while we're here" creep.** Workday monitoring is out of scope (accepted gap). The `mycelium synthetics` CLI is out of scope (iter-7). The setup-aws.sh execution is out of scope (iter-8+).
- **No `--skip-audit` on freeze unless it's the iter-5 grandfathering pattern from legendary-funicular HANDOFF.** This iteration's freeze should be clean.
- **No mocking the Claude API in verification.** The whole point of synthetics is REAL scorer + DETERMINISTIC inputs.
- **No `--no-verify` commits.**
- **No raising concurrency above `-c 3`.**
- **No silent edits to NUTRIENTS §I.1.** The contract amendment is its own leaf with its own FRUIT_READY line.
- **No claiming verification passed if any of the 5 gates failed.** If gate 4 (cache contract) fails, the cultivation is NOT green — the cache contract was the entire point of the iter-5 budget math.

---

## Acceptance (organism-level)

The cultivation is successful when ALL of the following are true:

1. `pytest tests/synthetics/ -v` → exit 0.
2. `npx tsc --noEmit` and `npm test -- --run` in frontend → still clean (no regression).
3. `grep -r "LIKE '00000000-%'" backend/ synthetics/ NUTRIENTS.md hyphae/ brief.md CLAUDE.md` → exit 1 (no matches).
4. `python -c "from backend.synthetics.known_ids import is_synthetic, SYNTHETIC_CANDIDATE_IDS; assert len(SYNTHETIC_CANDIDATE_IDS) == 3; assert all(is_synthetic(u) for u in SYNTHETIC_CANDIDATE_IDS.values())"` → exit 0.
5. All 5 verification gates above produce their artifacts in `synthetics/runs/iter-6-verification/`.
6. `mycelium harvest -t 0.8` → 100% with the new synthetics-fix-agent biome in FRUIT_READY.
7. `NUTRIENTS.md §I.1.b` exists and documents the "constants not prefix" lesson.

If 1-4 fail: real code bug, fix the leaf and re-cultivate.
If 5 fails: iter-5 isn't actually verified; iter-6 is incomplete. Do not declare done.
If 6 fails: framework rollup bug (already fixed in legendary-funicular PR #3) — pull the latest CLI.
If 7 fails: the lesson didn't outlive the bug. Re-do the contract amendment.

---

## Why this iteration matters

iter-5 shipped infrastructure that doesn't detect what it claims to detect. The harvest said 100% and harvest was right about the *files* — but the files are wired to a query that returns empty. That's the worst class of bug: present, untested, silently wrong. iter-6 closes the loop by fixing the contract, running the verification iter-5 should have run, and capturing the first real baseline. After this, drift detection is actually armed.

The lesson also belongs in NUTRIENTS, not in a HANDOFF entry that gets forgotten: **detection mechanism is separate from generation mechanism, and a brief that conflates them propagates the bug everywhere the planner reads it.**

iter-7 promotes the verified patterns (mycelium synthetics CLI, alert state machine, additive-seam pattern, drift contract template) to legendary-funicular framework.

*The Dot Connects.*
