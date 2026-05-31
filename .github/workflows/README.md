# CI Workflows — Talent Agent

This directory holds the GitHub Actions pipeline that gates merges and lays
the road toward cloud deployment (Cloudflare / Vultr).

**Status: SKELETON (iter-6).** Some jobs run real checks; one is a documented
placeholder. Read the table below before trusting a green check.

## Triggers

`ci.yml` runs on:

- `pull_request` (any branch)
- `push` to `main`
- `workflow_dispatch` (manual)

Superseded runs on the same ref are auto-cancelled (`concurrency` block).

## Jobs

| Job | Real or Scaffold | What it does |
|---|---|---|
| `backend-lint-type` | **Real** | Python 3.12, installs `requirements.txt`, runs `python -m compileall backend/` as a syntax gate. No ruff/flake8/black is configured in the repo, so no linter is invented — `compileall` is the minimal gate until one is added. |
| `backend-unit` | **Real** | Python 3.12 + requirements, runs the offline-capable `tests/synthetics/` suite (mocked; no live DB/Redis/Claude). See "Notes" for the two CI-specific accommodations. |
| `frontend-build-test` | **Real** | Node 20, `npm ci`, `npm run lint` (eslint flat config), `npm run build` (Vite 8), `npm test -- --run` (vitest). npm cache enabled. |
| `backend-integration` | **SCAFFOLD / PLACEHOLDER** | Boots real `postgres:15-alpine` + `redis:7-alpine` service containers (matching `docker-compose.yml`) to prove the wiring, then prints an explicit "pending backend runtime" message and **exits 0**. It runs **zero real integration tests**. Do not mistake this green check for working integration coverage. |

### Real vs scaffold — the honest summary

- **3 jobs run real checks** on code that is exercisable without a live stack:
  `backend-lint-type`, `backend-unit`, `frontend-build-test`.
- **1 job is a scaffold**: `backend-integration`. The service containers boot
  for real (so the `services:` wiring is validated), but it asserts nothing.
  The "pending" echo makes the gap explicit in the logs — it is **not** a
  silently-passing fake.

## Notes on `backend-unit`

Two CI-specific accommodations, both deliberate:

1. **Env vars for import-time config validation.** `tests/conftest.py` imports
   `backend.main` at collection time, which imports `backend/config.py`.
   `Settings` has **required** fields with no defaults (`database_url`,
   `redis_url`, `anthropic_api_key`) and there is no `.env` in CI, so without
   dummy env vars the suite would die with a pydantic `ValidationError` before
   any test runs. The job sets dummy `DATABASE_URL` / `REDIS_URL` /
   `ANTHROPIC_API_KEY` to satisfy import-time validation only — nothing
   connects to a real service.

2. **One stale test is deselected.**
   `tests/synthetics/test_cli.py::TestMain::test_run_crawler_not_implemented`
   is a stale iter-5 test: it asserts the crawler is "not implemented" and
   makes **live network calls** to greenhouse/lever/ashby. The crawler is now
   implemented, so the test fails and is network-dependent. It is deselected to
   keep CI deterministic and offline — deselected, **not** hidden to fake a
   green run. Repairing it is on the TODO list below (and the `tests/` dir is
   off-limits to the CI agent, so it could not be fixed in this pass).

## TODO — road to full CI

Tracked work to graduate this skeleton into a full pipeline:

1. **Wire real integration tests** into `backend-integration`: run Alembic
   migrations against the postgres service, then the DB/Redis-dependent suites
   (`tests/api/`, `tests/application/`, `tests/discovery/`, `tests/scheduler/`,
   plus `tests/test_health.py`). Do this once the backend runtime decision
   lands.
2. **Add e2e and load jobs** (gates 2–5) against a live stack once the runtime
   is chosen (Cloudflare / Vultr). Currently blocked on the same runtime
   decision.
3. **Repair the stale iter-5 crawler test**
   (`test_run_crawler_not_implemented`) so it no longer makes live network
   calls and no longer asserts a now-false "not implemented" state, then remove
   the `--deselect` from `backend-unit`.
   - **Re-verify `backend-unit`'s offline guarantee when the parallel iter-6
     synthetics work lands.** A parallel agent has uncommitted
     `tests/synthetics/conftest.py` and `tests/synthetics/test_cli_iter6_crawler.py`
     (likely the replacement for the deselected stale test). Once committed,
     `backend-unit` will start collecting them; confirm they are fully mocked
     (no live network). Also note: the `--deselect` hardcodes
     `test_cli.py::TestMain::test_run_crawler_not_implemented`; if that test is
     removed or renamed, the deselect silently matches nothing (pytest does not
     error), so the offline guarantee then rests entirely on the new conftest.
4. **Configure a Python linter** (ruff recommended — fast, single binary) with
   a `pyproject.toml`/`ruff.toml`, then swap the `compileall` step in
   `backend-lint-type` for `ruff check` (+ `ruff format --check`). A
   `.ruff_cache` already exists in the repo but no config is committed.
5. **Add type checking** (mypy or pyright) to `backend-lint-type` once a
   config and the baseline error set are agreed.
6. **Add SAST / secret scanning / coverage jobs** once the QA charter
   `QA-PRINCIPLES.md` is authored. Candidates: CodeQL or Semgrep (SAST),
   gitleaks or trufflehog (secrets), `pytest --cov` + Codecov/coverage gate.
7. **Pin Docker image digests / add a deploy job** when the cloud target
   (Cloudflare / Vultr) is finalized.
