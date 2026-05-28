# HYPHA-TESTS

> HYPHA tag: `TA/TESTS`
> Maps to Mycelium agent: `tests-agent`

## Goal

Own the test suites for all iter-4 biomes. Every new path must have coverage. The test biome runs last in the cultivation wave, validating that all seams are properly closed.

## Scope

### In Scope

- `tests/discovery/test_orchestrator_pubsub.py` — verify 8+ event sequence from `DiscoveryOrchestrator.run`
- `tests/scheduler/test_daily_task.py` — verify Celery task creates `crawl_runs` row, handles retries
- `tests/api/test_events_stream.py` — verify SSE endpoint streams events, sends heartbeats
- `tests/api/test_review_approve.py` — full integration: create application → approve → verify state transition
- `frontend/src/api/__tests__/client.test.ts` — vitest tests for auth header injection, 401 handling, error normalization

### Out of Scope

- E2E tests with Playwright (follow-up iteration)
- Load testing / performance benchmarks
- Coverage for frozen biomes (already tested)
- Frontend component tests (unit tests only for API client)
- Contract testing between frontend and backend

## Inputs

- `discover-agent`: `DiscoveryOrchestrator` class
- `scheduler-agent`: `daily_discovery_task` Celery task
- `api-streaming-agent`: `GET /events/stream` endpoint
- `api-agent`: `POST /applications/{id}/approve`, `POST /applications/{id}/reject` endpoints
- `api-client-agent`: `apiClient` and API wrapper functions

## Outputs (Deliverables)

- `tests/discovery/test_orchestrator_pubsub.py`
- `tests/scheduler/__init__.py`
- `tests/scheduler/test_daily_task.py`
- `tests/api/test_events_stream.py`
- `tests/api/test_review_approve.py`
- `frontend/src/api/__tests__/client.test.ts`

## Acceptance Criteria

### Backend (pytest)

- [ ] `pytest tests/discovery/test_orchestrator_pubsub.py -v` passes
- [ ] Test uses `fakeredis.aioredis` for Redis — no real Redis required
- [ ] Test uses in-memory SQLite for database
- [ ] Asserts 8+ events in sequence: `RUN_STARTED, CANDIDATE_LOADED, PROFILE_BUILT, MANIFEST_BUILT, CRAWL_SOURCE_COMPLETE×4, CRAWL_COMPLETE, SCORING_COMPLETE, RUN_COMPLETE`
- [ ] Asserts no duplicate events
- [ ] Asserts `event=RUN_COMPLETE` is last

- [ ] `pytest tests/scheduler/test_daily_task.py -v` passes
- [ ] Test mocks `DiscoveryOrchestrator` to avoid real Claude calls
- [ ] Asserts one `crawl_runs` row created per candidate
- [ ] Asserts idempotent re-fire deduplicates by `task_id`
- [ ] Asserts retry failure writes to `crawl_runs.error_log`

- [ ] `pytest tests/api/test_events_stream.py -v` passes
- [ ] Test uses FastAPI `TestClient` with streaming response
- [ ] Publishes to Redis from test, asserts SSE frame surfaces
- [ ] Asserts `:ping` heartbeat within 16s
- [ ] Asserts 401 on missing auth

- [ ] `pytest tests/api/test_review_approve.py -v` passes
- [ ] Creates application row in test database
- [ ] POSTs approve, asserts state transition to `APPROVED`
- [ ] Asserts `application_events` row written
- [ ] Asserts 404 on non-existent pipeline
- [ ] Asserts 400 on approving non-AWAITING_REVIEW pipeline

### Frontend (vitest)

- [ ] `cd frontend && npm test -- --run` passes
- [ ] `client.test.ts` mocks `fetch` via `vi.mock` or `msw`
- [ ] Asserts `Authorization: Bearer` header injected on requests
- [ ] Asserts 401 response triggers logout callback
- [ ] Asserts network error surfaces `TalentAgentApiError` with correct shape

### Coverage

- [ ] `pytest --cov=backend --cov-report=term-missing` shows ≥80% on new files
- [ ] Excludes `__init__.py` and migrations from coverage calculation

### Linting

- [ ] `ruff check backend/` clean
- [ ] `ruff check tests/` clean

## Notes

- Use `fakeredis.aioredis` for async Redis mocking. It supports pub/sub operations.
- Use `pytest-asyncio` for async test functions. Mark all async tests with `@pytest.mark.asyncio`.
- The in-memory SQLite setup is in `tests/conftest.py`. Reuse the existing fixtures.
- For SSE testing, `TestClient` with `stream=True` allows reading the response incrementally. Set a timeout to avoid hanging on heartbeat tests.
- The scheduler tests should mock `DiscoveryOrchestrator` at the import level to prevent real Claude API calls.
- Frontend tests use `vitest`. The `vi.mock` API is similar to Jest's `jest.mock`.
- Coverage threshold of 80% applies to new files only. Do not regress coverage on existing code.
- All test files must pass `ruff check` — no linting exceptions for test code.
