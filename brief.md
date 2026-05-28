# Talent Agent — Cultivation Brief (Iteration 4 — End-to-End Loop)

> Input to `mycelium cultivate`. Iter-3.5 shipped real Greenhouse/Lever/Ashby/Workday crawler adapters and `ats_selectors.yaml`. This iteration closes the loop: the orchestrator publishes status, the dashboard reads it, and a single command takes a real candidate through Discovery → Review → Apply.
>
> Read `CLAUDE.md` (project), `NUTRIENTS.md` (frozen contracts), `CELLULAR-MAP.md`, and `hyphae/HYPHA-*.md` before acting. Mycelium framework spec: this organism runs **cellular: true · gating: contract-freeze · max_depth: 3**. Specialists consume frozen HYPHA stubs, not upstream live code. Integration happens at merge time via `merge_order` in `mycelium.yaml`.

---

## What we're building

End-to-end loop validation for a single candidate (Sean Young). Today the pipeline has all 10 biomes shipped and the crawler is real, but five seams are still loose:

1. **Discovery orchestrator** never publishes on `agent.status.discovery` (HYPHA-DISCOVERY-ENGINE §Notes line 76 explicitly flags this gap; the helper `_publish_status` is referenced but unimplemented in `backend/agents/discovery/orchestrator.py`).
2. **Celery beat** is in the stack but never wired (HYPHA-DISCOVERY-ENGINE §Out of Scope flagged it). Daily 7am cron must trigger `DiscoveryOrchestrator.run(candidate_id)` for every active candidate.
3. **Frontend** has primitives + pages but no `apiClient` wired to the FastAPI surface. Pages render mock data.
4. **Review queue** detail panel renders applications but the approve/reject path doesn't call `POST /applications/{id}/approve` end-to-end.
5. **infra-agent** is still flat (CELLULAR-MAP "What's Next" #1 flagged this). Decompose into docker/ecs/pipeline leaves so a future infra change cultivates surgically.

## Core goal

Run `python -m backend.cli loop --candidate sean-young` and watch the system go from a resume PDF on disk to a tailored email draft awaiting human approval in the Review Queue UI — with structured logs and pub/sub events at every stage. **The recursive build worked when audit-run audited the framework itself.** This iteration validates the same loop closure on the real product surface.

## Stack canon

Same as iter-3.5 (canonical override block below). The repo uses `--stack nextjs-fastapi-supabase` as a label only — the real stack is:

- Backend: FastAPI · Python 3.12 · Pydantic v2 · SQLAlchemy 2.0 async · Alembic · httpx · Playwright async · Celery
- DB: raw PostgreSQL 15 (NOT Supabase) · Redis 7 (cache + pub/sub + Celery broker)
- Frontend: React 19 · Vite 8 · Tailwind · react-router-dom · lucide-react
- No Next.js, no Supabase, no httpOnly cookies, no RLS, no NEXT_PUBLIC_ env vars

---

## Organisms (biomes in scope)

Five biomes are in scope. **Do not touch** `data-agent`, `design-agent`, `auth-agent`, `agents-agent` — they are frozen and integration tested. The crawler internals from iter-3.5 are also frozen — only `discover-agent.orchestrator` changes.

### discover-agent — close the pub/sub gap

The orchestrator already calls every sub-agent correctly. What's missing: every `await self._publish_status(...)` call refers to a helper that doesn't exist. The HYPHA explicitly says to follow the pattern from `application/orchestrator.py:325-336`.

**Hard requirements:**

- Implement `DiscoveryOrchestrator._publish_status(candidate_id, event_name)` that publishes to Redis channel `agent.status.discovery` with payload `{candidate_id, event, ts}` (ISO-8601 UTC).
- Delete the stale `# 4. Crawl (currently stubbed — Phase 1B)` comment at `backend/agents/discovery/orchestrator.py:128`. The crawler is real now (iter-3.5 commits `7f4d514`, `b140392`). Replace with `# 4. Crawl across all four sources`.
- The `score_with_semaphore` wrapper at orchestrator.py ~line 122 is defined but unused (HYPHA-DISCOVERY-ENGINE §Notes confirms this was intentional). **Leave it alone.** Do not refactor. Annotate with `# noqa: F841 — reserved for per-job-scoring path` if ruff complains.
- Emit `CRAWL_SOURCE_COMPLETE` events with `{source, jobs_found}` per adapter, not just the rollup `CRAWL_COMPLETE`. This lets the dashboard show per-source progress during a multi-minute run.

**Acceptance:**

- `redis-cli SUBSCRIBE agent.status.discovery` shows ≥ 8 events for a single `run(candidate_id)` invocation: `RUN_STARTED, CANDIDATE_LOADED, PROFILE_BUILT, MANIFEST_BUILT, CRAWL_SOURCE_COMPLETE×4, CRAWL_COMPLETE, SCORING_COMPLETE, RUN_COMPLETE`.
- `pytest tests/discovery/test_orchestrator_pubsub.py -v` passes (new — see Tests biome).

### scheduler-agent (NEW biome) — Celery beat wiring

A new top-level biome. `data-agent`, `obs-agent`, and `discover-agent` must be frozen before it germinates.

**Hard requirements:**

- `backend/scheduler/celery_app.py` — Celery app factory reading broker URL from `settings.redis_url`.
- `backend/scheduler/tasks.py` — `daily_discovery_task(candidate_id)` that constructs a fresh DB session + Redis client and invokes `DiscoveryOrchestrator.run(candidate_id)`. Wrap the async call with `asyncio.run(...)` since Celery workers are sync.
- `backend/scheduler/beat.py` — Beat schedule: 07:00 America/New_York every day, iterates active candidates, enqueues one task per candidate with a per-candidate `task_id` (idempotent if the worker re-fires).
- `docker-compose.yml` gains two services: `celery-worker` and `celery-beat`, both reading the same env as the backend.
- On task failure, exponential backoff: 3 retries at 60s/300s/900s, then dead-letter into the `crawl_runs` row's `error_log` column and publish `agent.status.discovery` event `DAILY_TASK_DEAD`.

**Acceptance:**

- `celery -A backend.scheduler.celery_app beat --loglevel=info` starts without import errors.
- `celery -A backend.scheduler.celery_app inspect scheduled` shows the daily task registered.
- Manual trigger `celery -A backend.scheduler.celery_app call backend.scheduler.tasks.daily_discovery_task --args='["<uuid>"]'` produces a `daily_digests` row.
- A simulated worker crash mid-run leaves the `crawl_runs` row in `FAILED` with the traceback in `error_log`, NOT `RUNNING` (this exercises HYPHA-DISCOVERY-ENGINE acceptance criterion line 56).

### api-client-agent (NEW biome) — frontend API wiring

`api-agent` and `frontend-agent` must be frozen before it germinates.

**Hard requirements:**

- `frontend/src/api/client.ts` — single `apiClient` instance built on `fetch`. Reads base URL from `import.meta.env.VITE_API_BASE_URL` (no `NEXT_PUBLIC_` — this is Vite).
- `frontend/src/api/auth.ts` — `requestMagicLink(email)`, `verifyToken(token)`, `refreshSession()`. Stores JWT in `localStorage` under key `talent-agent-jwt`. Every request injects `Authorization: Bearer ${jwt}`.
- `frontend/src/api/discovery.ts` — `getTodayDigest()`, `triggerDiscoveryRun()`, `getJob(id)`.
- `frontend/src/api/applications.ts` — `listApplications()`, `approveApplication(id)`, `rejectApplication(id, reason)`.
- `frontend/src/api/events.ts` — `subscribeAgentStatus(channel, onMessage)` — opens an EventSource to `GET /events/stream?channel=agent.status.discovery` (new endpoint on api-agent — see api-streaming-agent biome below).
- On 401, the client invalidates the JWT, redirects to `/login`, and surfaces a toast.
- All `fetch` calls catch network errors and surface a `TalentAgentApiError` with `{status, code, message}` so pages can render error states.
- Existing `frontend/src/pages/Overview.tsx`, `Pipeline.tsx`, `Analytics.tsx`, `ReviewQueue.tsx`, `ReviewDetail.tsx` must be re-wired to call the client instead of mock data. **Preserve their existing layout and styling exactly.**

**Acceptance:**

- `npm run typecheck` clean.
- Opening the frontend with the backend running shows real digest data, not mocks.
- Clicking Approve in `ReviewDetail` fires `POST /applications/{id}/approve` and updates the row optimistically.
- Killing the backend mid-session triggers an error toast on the next request and shows a banner; recovery resumes when the backend comes back.

### api-streaming-agent (NEW biome) — SSE event stream

`obs-agent` and `api-agent` must be frozen before it germinates.

**Hard requirements:**

- `backend/api/events.py` — `GET /events/stream?channel=...` endpoint. FastAPI `StreamingResponse` with `media_type="text/event-stream"`. Subscribes to the requested Redis channel and re-emits each message as an SSE `data: {json}\n\n` frame.
- Channel allowlist: `agent.status.discovery`, `agent.status.application`. Reject any other channel with 400.
- Heartbeat: emit `:ping\n\n` every 15s so clients can detect connection loss.
- Auth: same `get_current_user` dependency as the other routers — every connection requires a valid JWT.
- Backpressure: if a client falls > 100 messages behind, drop the slowest end of their queue and emit `event: slow_client\ndata: {dropped: N}\n\n`. Better to skip frames than block the publisher.

**Acceptance:**

- `curl -N -H "Authorization: Bearer ${JWT}" http://localhost:8000/events/stream?channel=agent.status.discovery` streams events as they're published.
- Triggering `DiscoveryOrchestrator.run` from another shell produces visible events on the open curl connection within 100ms of each publish.
- Connection-loss recovery: dropping the network for 5s and reconnecting resumes without duplicate events for already-acked frames (best-effort — full event sourcing is iter-5).

### infra-agent — leaf decomposition + Celery containers

`api-agent` and `frontend-agent` frozen. **Decompose infra-agent into the leaves declared in mycelium.yaml** (`infra-agent.docker.backend`, `infra-agent.docker.frontend`, `infra-agent.docker.compose`, `infra-agent.ecs.task-defs`, `infra-agent.ecs.bootstrap`, `infra-agent.pipeline.digital-dash`). Each leaf owns one file path. No leaf may touch another's artifact.

**Hard requirements:**

- `docker-compose.yml` must gain `celery-worker` and `celery-beat` services as siblings to `backend`. Both consume the same `.env`. `depends_on` Redis + Postgres with health checks.
- `deploy/ecs-task-def-celery-worker.json` and `deploy/ecs-task-def-celery-beat.json` — new Fargate task definitions. The `beat` task must be `desired_count: 1`, the `worker` task `desired_count: 2` with auto-scaling on CPU > 70%.
- `digital-dash-pipeline.yml` gets a new stage `deploy-celery` after `deploy-backend`, gated by a manual approval (do not auto-deploy schedulers on every push).
- `setup-aws.sh` provisions one extra IAM role for the Celery tasks (read SES, read SQS dead-letter, write CloudWatch metrics). Append only — do not modify existing role declarations.

**Acceptance:**

- `docker-compose up` brings all 6 services (postgres, redis, backend, frontend, celery-worker, celery-beat) to healthy state.
- `docker-compose logs celery-beat` shows the daily task scheduled.
- `aws ecs describe-task-definition --task-definition talent-agent-celery-worker` returns a definition matching the JSON file.

---

## Tests biome (NEW — runs in every wave)

`pytest` must be green on every shipped path. One test leaf per impacted biome.

**Hard requirements:**

- `tests/discovery/test_orchestrator_pubsub.py` — fake Redis (`fakeredis.aioredis`), run `DiscoveryOrchestrator.run` against an in-memory SQLite, assert the 8+ event sequence in order, with no duplicates, and `event=RUN_COMPLETE` last.
- `tests/scheduler/test_daily_task.py` — invoke `daily_discovery_task` directly with a mocked orchestrator, assert one `crawl_runs` row created per candidate, assert idempotent re-fire deduplicates by `task_id`.
- `tests/api/test_events_stream.py` — TestClient with streaming response, publish to Redis, assert the SSE frame surfaces with correct JSON. Heartbeat: assert a `:ping` line within 16s.
- `tests/api/test_review_approve.py` — full integration: create an application row, POST approve, assert state transitions to `APPROVED` and an `application_events` row is written.
- `frontend/src/api/__tests__/client.test.ts` — vitest. Mock fetch, assert auth header injection, 401 → logout, network error → typed `TalentAgentApiError`.

**Acceptance:**

- `pytest -q` exit 0.
- `cd frontend && npm test -- --run` exit 0.
- `ruff check backend/` clean.
- Coverage report shows ≥80% on the new files (excluding `__init__.py` and migrations).

---

## Mathematics & concurrency

Per `CELLULAR-MAP.md` Concurrency Math, this organism has **10 biomes → ~50 leaves at depth 3 → peak 4 concurrent sessions** under current rate-limit discipline. Iter-4 adds 4 new biomes (scheduler, api-client, api-streaming, tests) and a leaf-level decomposition of infra. New totals:

| Depth | Count | Description |
|---|---|---|
| Biomes (1) | 14 | 10 existing + 4 new |
| Specialists (2) | ~32 | After this iteration's decomposition |
| Leaf specialists (3) | ~62 | Including infra leaves and tests |
| Peak concurrent sessions | 4 | Held at -c 4 per legendary-funicular's 1055.7s run evidence |

Run with `mycelium cultivate -c 4`. Do NOT raise concurrency until cache hit-rate observability is in place. Legendary-funicular's first `-c 30` attempt rate-limited all 43 leaves and burned ~$17 with zero output.

**Budget:** `organism.budget.maxUsd: 100`. Iter-3.5's two leaves cost ~$1.40 total. Iter-4's ~16 active leaves (5 modified biomes + 1 test biome × ~3 leaves each) should land at ~$10-15 with prompt cache hits. Stop the cultivation if `spend > $50` and reassess.

---

## How to run

```bash
cd /Users/spy/mfautomations/repos/creation-station/reverse-search

# Wave 1 — pub/sub gap close (no new biomes blocked)
mycelium cultivate \
  --only-biome discover-agent \
  --max-concurrency 2

# Wave 2 — new biomes in parallel (independent dep graphs)
mycelium cultivate \
  --only-biome scheduler-agent,api-streaming-agent \
  --max-concurrency 4

# Wave 3 — frontend wiring (depends on api-streaming)
mycelium cultivate \
  --only-biome api-client-agent,infra-agent \
  --max-concurrency 4

# Wave 4 — tests sweep (depends on everything above)
mycelium cultivate \
  --only-biome tests \
  --max-concurrency 4
```

Run waves sequentially. Inside each wave the leaves germinate against frozen HYPHA contracts in parallel. Harvest after each wave with `mycelium harvest -t 0.8` and let the merge_order do its job.

---

## What MUST NOT happen

- **No re-cultivation of frozen biomes.** Do not touch `data-agent`, `design-agent`, `auth-agent`, `agents-agent`, or the iter-3.5 crawler internals. The freeze is real.
- **No new top-level dependencies.** `celery`, `fakeredis`, and `vitest` go in `requirements.txt` / `package.json`. Nothing else.
- **No mocked data in frontend pages.** If a page can't get real data because the backend isn't running, it must show an error state, not silently render placeholders.
- **No `print()` anywhere.** `structlog` only. Frontend uses the existing logging utility, not `console.log`.
- **No comments containing "STUB", "TODO: implement", "Phase 1B", or "placeholder".** Iter-3.5 already cleaned the crawler; do not reintroduce them.
- **No `--no-verify` git commits.** Auto-commit hooks must pass.
- **No raising concurrency above -c 4.** Cache hit-rate observability is iter-5 work. Until then, hold the line.
- **No Bash escape hatches.** Sub-agents write/edit files via Write and Edit only. The `mycelium audit-run` `--autofix` loop relies on declared artifacts being accurate.
- **No skipping the test biome.** Iter-3 shipped 5 stubs because the test sweep was elided. Not again.

---

## Acceptance (organism-level)

The cultivation is considered successful when ALL of the following are true after `mycelium harvest -t 0.8`:

1. `pytest -q` → exit 0, ≥80% coverage on new files.
2. `cd frontend && npm test -- --run` → exit 0, `npm run typecheck` clean.
3. `ruff check backend/` clean.
4. `docker-compose up` brings 6 services healthy within 90s.
5. End-to-end smoke: `python -m backend.cli loop --candidate sean-young --dry-run` produces a `daily_digests` row, a `crawl_runs` row in COMPLETED, ≥8 published events, and no errors in `structlog` JSON output.
6. Frontend visited in a browser with backend running shows real digest data, supports magic-link login, and the Approve button on a Review Queue item produces a state transition in Postgres.
7. The dashboard at `sporenet/dashboard.html` (rendered post-cultivate by `mycelium sporenet render`) shows all 14 biomes at `done` status with commit SHAs.
8. Every published `agent.status.*` event lands in the SSE stream within 100ms.

If 1-3 fail, fix the leaves and re-cultivate. If 4-8 fail, the integration seam was not closed correctly — file a framework bug if a leaf reported FRUIT_READY but its acceptance criterion regresses on the merged main.

---

## Why this iteration matters

This is the first cultivation where the system observes itself end-to-end. Discovery publishes, the API streams, the frontend listens, the operator approves. Until those four seams close, every prior iteration's shipped biome was a leaf without a tree. After this cultivation, the recursive build pattern from legendary-funicular's audit-run applies to talent-agent: the system can run itself, watch itself, and (in iter-5) heal itself.

*The Dot Connects.*
