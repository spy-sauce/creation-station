# HYPHA-SYNTHETICS-FIXTURES

> HYPHA tag: `TA/SYNTH-FIX`
> Maps to Mycelium agent: `synthetics-fixtures-agent`

## Goal

Own the synthetic test data that exercises the Discovery → Score pipeline daily. Provide 3 deterministic synthetic candidates with known profiles, 12 JD fixtures with declared expectations, and an idempotent seeder that upserts synthetics into Postgres on backend boot. The fixtures are the inputs to the synthetic monitoring harness — without them, drift detection has no baseline.

## Scope

### In Scope

- `synthetics/fixtures/candidates.yaml` — 3 synthetic candidate definitions with full resume text + identity context
- `synthetics/fixtures/jobs/` — 12 JD markdown files with YAML frontmatter declaring `expected_hot` and `expected_score_band`
- `synthetics/fixtures/baselines/` — gitignored directory scaffold for accepted fingerprint baselines
- `synthetics/fixtures/seeder.py` — idempotent loader that upserts synthetic candidates into Postgres via SQLAlchemy
- `synthetics/fixtures/__init__.py` — module init exposing `seed()` coroutine

### Out of Scope

- Scoring logic (owned by `synthetics-scoring-agent`)
- Crawler health checks (owned by `synthetics-crawler-agent`)
- Baseline comparison (owned by `synthetics-scoring-agent`)
- Schema changes — no new columns, no new tables, no migrations
- Workday JD fixtures — Workday is exercised via scoring suite, not as fixtures

## Inputs

- `data-agent` (FROZEN): `Candidate` ORM model for upserting
- `NUTRIENTS.md §I.1`: Synthetic candidate UUID namespace derivation
- `NUTRIENTS.md §I.9`: `SyntheticCandidateFixture` and `SyntheticJobFixture` contracts

## Outputs (Deliverables)

- `synthetics/__init__.py`
- `synthetics/fixtures/__init__.py`
- `synthetics/fixtures/candidates.yaml`
- `synthetics/fixtures/jobs/jr-01-strong-swe.md`
- `synthetics/fixtures/jobs/jr-02-strong-fullstack.md`
- `synthetics/fixtures/jobs/jr-03-weak-devops.md`
- `synthetics/fixtures/jobs/jr-04-mismatch-sales.md`
- `synthetics/fixtures/jobs/ml-01-strong-staff.md`
- `synthetics/fixtures/jobs/ml-02-strong-research.md`
- `synthetics/fixtures/jobs/ml-03-weak-junior.md`
- `synthetics/fixtures/jobs/ml-04-mismatch-pm.md`
- `synthetics/fixtures/jobs/pm-01-strong-senior.md`
- `synthetics/fixtures/jobs/pm-02-strong-product.md`
- `synthetics/fixtures/jobs/pm-03-weak-junior.md`
- `synthetics/fixtures/jobs/pm-04-mismatch-eng.md`
- `synthetics/fixtures/baselines/.gitkeep`
- `synthetics/fixtures/baselines/.gitignore`
- `synthetics/fixtures/seeder.py`

## Acceptance Criteria

- [ ] `python -c "from synthetics.fixtures.seeder import seed; import asyncio; asyncio.run(seed())"` completes without error
- [ ] Running the seed command twice is idempotent — no duplicate rows, no constraint violations
- [ ] `SELECT count(*) FROM candidates WHERE id = ANY(SYNTHETIC_CANDIDATE_IDS.values())` returns 3 after seeding (see backend/synthetics/known_ids.py — added iter-6 to replace broken LIKE prefix detection)
- [ ] Each synthetic candidate has a unique UUIDv5 derived from `uuid.uuid5(uuid.NAMESPACE_DNS, "synthetic-" + slug)`
- [ ] All 12 JD files have valid YAML frontmatter with `expected_hot` (boolean) and `expected_score_band` (one of `low`, `mid`, `high`)
- [ ] Each JD file declares `target_candidate` matching one of the 3 synthetic slugs
- [ ] JD distribution per candidate: 4 JDs each (1 strong, 1 strong variant, 1 weak, 1 mismatch)
- [ ] `synthetics/fixtures/baselines/.gitignore` contains `*.json` to gitignore baseline files initially
- [ ] No `print()` anywhere — `structlog` only
- [ ] `ruff check synthetics/` clean

## Notes

### Synthetic Candidate Profiles

**synthetic-jr-engineer:**
- Entry-level full-stack developer, 1-2 years experience
- Location: NYC
- Target salary: $80,000-$110,000
- Remote preference: hybrid
- Skills: React, TypeScript, Node.js, PostgreSQL
- Leadership level: IC

**synthetic-senior-ml:**
- Staff-level ML engineer, 8+ years experience
- Location: Bay Area
- Target salary: $250,000-$350,000
- Remote preference: remote_only
- Skills: PyTorch, TensorFlow, distributed systems, MLOps
- Leadership level: Staff

**synthetic-mid-product:**
- Senior product manager, 5 years experience
- Location: Remote
- Target salary: $150,000-$200,000
- Remote preference: remote_only
- Skills: Agile, roadmapping, analytics, stakeholder management
- Leadership level: Manager

### JD Fixture Naming Convention

Format: `{candidate-prefix}-{index}-{match-type}-{role}.md`

Examples:
- `jr-01-strong-swe.md` — Strong match for jr-engineer
- `ml-03-weak-junior.md` — Weak match for senior-ml (junior role)
- `pm-04-mismatch-eng.md` — Mismatch for mid-product (engineering role)

### UUID Namespace

Synthetic candidate IDs are UUIDv5 under the DNS namespace:

```python
import uuid

SYNTHETIC_NAMESPACE = uuid.NAMESPACE_DNS

def get_synthetic_id(slug: str) -> uuid.UUID:
    return uuid.uuid5(SYNTHETIC_NAMESPACE, f"synthetic-{slug}")

# Results:
# synthetic-jr-engineer → deterministic UUIDv5
# synthetic-senior-ml → deterministic UUIDv5
# synthetic-mid-product → deterministic UUIDv5
```

The UUIDv5 marker `00000000-0000-5xxx-...` pattern allows detection via SQL without schema changes.

### Seeder Integration

The seeder is called from `backend/main.py` lifespan context:

```python
from contextlib import asynccontextmanager
from synthetics.fixtures.seeder import seed

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... existing startup code ...
    await seed()  # Idempotent — safe on every boot
    yield
    # ... existing shutdown code ...
```

If synthetic candidates already exist (by UUID), the seeder no-ops. No upsert conflicts. No constraint violations.
