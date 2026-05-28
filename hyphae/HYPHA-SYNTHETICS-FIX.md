# HYPHA-SYNTHETICS-FIX.md — Iter-6 UUID Detection Fix
> Owner: synthetics-fix-agent
> Branch: feat/synthetics-fix-agent
> Status: PENDING

---

## Goal

Surgically fix the broken UUID detection mechanism in the synthetics infrastructure. The iter-5 implementation incorrectly assumed UUIDv5 hashes would start with `00000000-`, but UUIDv5 produces SHA-1 digests where the first 8 hex chars are essentially random.

This biome creates a single source of truth (`backend/synthetics/known_ids.py`) for synthetic candidate UUIDs and updates all consumers to use membership checks instead of prefix matching.

---

## Scope

### In Scope

- Create `backend/synthetics/known_ids.py` — canonical frozen UUID constants
- Update `backend/synthetics/scoring_runner.py` — replace broken SQL LIKE with ANY(:ids)
- Update `synthetics/fixtures/seeder.py` — add self-verify block, import known_ids
- Update `synthetics/fixtures/candidates.yaml` — fix header comment
- Amend `NUTRIENTS.md §I.1` — document the fix and lesson learned
- Add tests for known_ids module and seeder idempotency

### Out of Scope

- Re-cultivation of any frozen biome (17 biomes from iter-1..5 are frozen)
- New tables or columns — UUID namespace isolation stands
- Workday monitoring — accepted coverage gap
- `mycelium synthetics` CLI — deferred to iter-7
- Any `-c` above 3 concurrency

---

## Inputs

- **Contracts:** NUTRIENTS.md §I.1-I.9 (Synthetic Drift Contract)
- **Upstream agents:** None (additive seam pattern — no upstream deps)
- **Fixtures:** synthetics/fixtures/candidates.yaml (read-only except header comment)

---

## Outputs (Deliverables)

| File Path | Description |
|---|---|
| `backend/synthetics/known_ids.py` | Canonical synthetic UUID constants + `is_synthetic()` oracle |
| `backend/synthetics/scoring_runner.py` | Updated SQL query (≤6 changed lines) |
| `synthetics/fixtures/seeder.py` | Import + self-verify block |
| `synthetics/fixtures/candidates.yaml` | Fixed header comment (lines 10-11) |
| `NUTRIENTS.md` | §I.1 amendment + §I.1.b new subsection |
| `tests/synthetics/test_known_ids.py` | Unit tests for known_ids module |
| `tests/synthetics/test_seeder_idempotent.py` | Seeder idempotency + self-verify tests |

---

## Acceptance Criteria

- [ ] `pytest tests/synthetics/test_known_ids.py -v` passes
- [ ] `pytest tests/synthetics/test_seeder_idempotent.py -v` passes
- [ ] `grep -r "LIKE '00000000-%'" backend/ synthetics/ NUTRIENTS.md hyphae/` returns exit 1 (no matches)
- [ ] `python -c "from backend.synthetics.known_ids import is_synthetic, SYNTHETIC_CANDIDATE_IDS; assert len(SYNTHETIC_CANDIDATE_IDS) == 3"` exits 0
- [ ] Each known UUID is a valid UUIDv5 (version field == 5)
- [ ] Recomputing UUIDs from slugs reproduces the constants exactly
- [ ] `NUTRIENTS.md §I.1.b` exists and documents "constants not prefix" lesson
- [ ] Seeder self-verify block raises RuntimeError on UUID mismatch
- [ ] Scoring runner SQL uses `WHERE id = ANY(:synthetic_ids)` not LIKE

---

## Verification Gates (must pass before harvest)

1. **Local DB seed:** `docker-compose up postgres redis backend` → healthy, then run seeder. Assert `SELECT count(*) FROM candidates WHERE id = ANY(...)` returns 3.

2. **First scoring run:** `python -m backend.synthetics run --suite=scoring` produces `synthetics/runs/<ts>/scoring-report.json`. Status = `green`.

3. **Baseline acceptance:** Copy run artifacts to `synthetics/fixtures/baselines/<candidate_id>__<run_id>.json` for each candidate.

4. **Second scoring run:** Re-run within 5 minutes. Assert:
   - Identical fingerprints
   - `cache_read_input_tokens > 0` on every Claude usage block
   - `cache_creation_input_tokens == 0` after first call

5. **Tampering proof:** Mutate one weight in `relevance_scorer.py`, re-run scoring, assert `DriftReport.severity in ("yellow", "red")`, revert.

Capture all 5 verification outputs in `synthetics/runs/iter-6-verification/`.

---

## Notes

### The Bug

UUIDv5 hashes the namespace + name with SHA-1. The first 8 hex chars of the digest are essentially random. The empirical UUIDs:

```
synthetic-jr-engineer  -> 3c7eab85-c380-584b-a128-43bba592f163
synthetic-senior-ml    -> 24fd155e-d431-5dd1-9a59-ee9b70c535a6
synthetic-mid-product  -> fb752ea7-1682-5cb8-84b9-b6402e8675a6
```

None start with `00000000-`. The `LIKE '00000000-%'` query returns **zero rows**.

### The Fix

Detect by membership in a known constant list, not by prefix. The seeder MUST produce these exact UUIDs deterministically; the `known_ids.py` module is the membership oracle for detection.

### Additive Seam Pattern

The frozen files get one-line import edits, not rewrites. The new file `backend/synthetics/known_ids.py` becomes the single source of truth.

### Lesson for NUTRIENTS.md §I.1.b

**Detection mechanism is separate from generation mechanism.** A brief that conflates them propagates the bug everywhere the planner reads it. UUIDv5 SHA-1 distribution fact: first 8 hex chars are not zero.

---

## Sub-agents

| ID | Scope |
|---|---|
| synthetics-fix-agent.known-ids | Create `backend/synthetics/known_ids.py` |
| synthetics-fix-agent.scoring-runner-detection | Fix SQL in `scoring_runner.py` |
| synthetics-fix-agent.seeder-self-verify | Add import + self-verify to seeder |
| synthetics-fix-agent.candidates-yaml-cleanup | Fix header comment |
| synthetics-fix-agent.contract-amendment | Amend NUTRIENTS.md §I.1 + add §I.1.b |
| synthetics-fix-agent.tests | Add test files |

---

## Blocked By

None — this is an additive patch with no upstream dependencies.

## Blocks

- synthetics-scoring-agent (must freeze before re-running)
- synthetics-crawler-agent (indirectly, via shared known_ids)

---

*Contract: NUTRIENTS.md §I.1 (as amended by iter-6)*
