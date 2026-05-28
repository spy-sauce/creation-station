# HYPHA-SCHEDULER

> HYPHA tag: `TA/SCHEDULER`
> Maps to Mycelium agent: `scheduler-agent`

## Goal

Own the Celery beat wiring that triggers daily discovery runs at 7am America/New_York for every active candidate. The scheduler is the cron backbone of the autonomous talent system — ensuring continuous job discovery without operator intervention.

## Scope

### In Scope

- `backend/scheduler/celery_app.py` — Celery app factory reading broker URL from `settings.redis_url`
- `backend/scheduler/tasks.py` — `daily_discovery_task(candidate_id)` that wraps async `DiscoveryOrchestrator.run()` with `asyncio.run()`
- `backend/scheduler/beat.py` — Beat schedule configuration: 07:00 America/New_York daily
- Exponential backoff retry policy: 3 retries at 60s/300s/900s intervals
- Dead-letter handling: on terminal failure, write traceback to `crawl_runs.error_log` and publish `DAILY_TASK_DEAD` event
- Idempotent task firing: per-candidate `task_id` prevents duplicate runs if the worker re-fires

### Out of Scope

- Real-time task monitoring dashboard (use `celery -A ... inspect`)
- Task result storage in database (Celery results backend is Redis, not Postgres)
- Multi-tenant isolation (single-tenant MVP; candidate iteration is simple query)
- Custom task routing (all tasks go to default queue)
- Flower or other Celery monitoring tools

## Inputs

- `data-agent`: `Candidate` ORM model (query active candidates)
- `data-agent`: `CrawlRun` ORM model (write error_log on failure)
- `discover-agent`: `DiscoveryOrchestrator` class with `run(candidate_id)` async method
- `obs-agent`: `publish_event(channel, payload)` for `DAILY_TASK_DEAD` events
- `api-agent`: `settings.redis_url` from Pydantic Settings

## Outputs (Deliverables)

- `backend/scheduler/__init__.py`
- `backend/scheduler/celery_app.py`
- `backend/scheduler/tasks.py`
- `backend/scheduler/beat.py`

## Acceptance Criteria

- [ ] `celery -A backend.scheduler.celery_app beat --loglevel=info` starts without import errors
- [ ] `celery -A backend.scheduler.celery_app inspect scheduled` shows the daily task registered
- [ ] Manual trigger `celery -A backend.scheduler.celery_app call backend.scheduler.tasks.daily_discovery_task --args='["<uuid>"]'` produces a `crawl_runs` row
- [ ] The task constructs a fresh DB session + Redis client for each invocation (no connection pooling across tasks)
- [ ] The async `DiscoveryOrchestrator.run()` call is wrapped with `asyncio.run()` since Celery workers are sync
- [ ] On task failure after 3 retries, the `crawl_runs` row transitions to `FAILED` with the traceback in `error_log`
- [ ] On terminal failure, `agent.status.discovery` channel receives `DAILY_TASK_DEAD` event
- [ ] A simulated worker crash mid-run leaves the `crawl_runs` row in `FAILED`, NOT `RUNNING` (exercises HYPHA-DISCOVERY-ENGINE acceptance criterion line 56)
- [ ] Idempotent re-fire: calling the same task with the same `task_id` deduplicates and does not create a second `crawl_runs` row
- [ ] No `print()` anywhere — `structlog` only
- [ ] `ruff check backend/scheduler/` clean

## Notes

- Celery workers are sync by design. The `daily_discovery_task` wraps the async orchestrator with `asyncio.run()`. This creates a fresh event loop per task, which is intentional — no shared async state across Celery tasks.
- The 07:00 schedule uses `America/New_York` timezone. The beat scheduler must be timezone-aware via `celery.schedules.crontab` with `timezone` kwarg.
- Task retry uses Celery's built-in `self.retry()` with `countdown` for exponential backoff. Do not implement custom retry logic.
- The `task_id` for idempotency is computed as `f"discovery-{candidate_id}-{run_date}"` where `run_date` is `YYYY-MM-DD` UTC. This ensures one task per candidate per day.
- On `MaxRetriesExceededError`, the task should catch, write to `crawl_runs.error_log`, and publish the `DAILY_TASK_DEAD` event before re-raising.
- The scheduler does NOT trigger `ApplicationOrchestrator` — that requires human approval via the Review Queue.
