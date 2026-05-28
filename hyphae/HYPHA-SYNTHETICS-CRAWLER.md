# HYPHA-SYNTHETICS-CRAWLER

> HYPHA tag: `TA/SYNTH-CRAWL`
> Maps to Mycelium agent: `synthetics-crawler-agent`

## Goal

Own the upstream health monitoring harness. Exercise the live crawler endpoints (Greenhouse, Lever, Ashby) hourly with lightweight HEAD-equivalent requests, track consecutive failures via a state machine, and alert on 3-strike threshold. This biome is the sentinel: if an upstream API changes, rate-limits, or breaks — the crawler harness detects it within 3 hours.

## Scope

### In Scope

- `backend/synthetics/crawler_health.py` — `CrawlerHealthRunner.run_suite()` health check orchestration
- `backend/synthetics/expected_schema_v1.json` — expected response shapes for Greenhouse/Lever/Ashby
- `synthetics/state.json` — persistent state file tracking consecutive failures per source
- `backend/synthetics/beat_schedule.py` — Celery beat extension for hourly crawler health + daily scoring
- `backend/synthetics/cli.py` extension — `python -m backend.synthetics run --suite=crawler`

### Out of Scope

- Synthetic candidate fixtures (owned by `synthetics-fixtures-agent`)
- Scoring drift detection (owned by `synthetics-scoring-agent`)
- Workday health checks — Playwright is too expensive for hourly. Workday exercises daily via scoring suite.
- Modifying the frozen `scheduler-agent` beat schedule — use additive registration only
- Schema changes — no new tables, no new columns

## Inputs

- `discover-agent` (FROZEN): Crawler adapter implementations for API endpoint patterns
- `obs-agent` (FROZEN): `publish_event(channel, payload)` for health alerts
- `NUTRIENTS.md §I.6`: Crawler health contract, state machine rules

## Outputs (Deliverables)

- `backend/synthetics/crawler_health.py`
- `backend/synthetics/expected_schema_v1.json`
- `backend/synthetics/beat_schedule.py`
- `synthetics/state.json`
- `synthetics/runs/<ts>/crawler-report.json` — per-run health reports

## Acceptance Criteria

- [ ] `python -m backend.synthetics run --suite=crawler` produces `synthetics/runs/<ts>/crawler-report.json`
- [ ] Report contains per-source `{status, latency_ms, schema_match, sample_jobs, error}`
- [ ] `curl http://localhost:8000/events/stream?channel=agent.status.synthetics.crawler` shows health pings during manual run
- [ ] Pointing the suite at a deliberately-wrong slug produces `status: failed, consecutive_failures: 1` — no alert
- [ ] Three consecutive failures for the same source produces `status: red, consecutive_failures: 3` — publishes alert
- [ ] A success after 3 failures resets to `status: green, consecutive_failures: 0` — publishes recovery event
- [ ] `cat synthetics/state.json` shows `consecutive_failures: 0` for all sources after successful run
- [ ] Hourly Celery beat entry is registered additively (does not modify frozen `daily_discovery_task`)
- [ ] No `print()` anywhere — `structlog` only
- [ ] `ruff check backend/synthetics/` clean
- [ ] `pytest tests/synthetics/ -v` → exit 0

## Notes

### Health Check Targets

| Source | Slug | Endpoint | Method | Expected shape |
|---|---|---|---|---|
| Greenhouse | `anthropic` | `https://boards.greenhouse.io/anthropic.json` | GET | `{jobs: [...]}` |
| Lever | `netflix` | `https://api.lever.co/v0/postings/netflix?limit=1` | GET | `[{id, text, ...}]` |
| Ashby | `posthog` | `https://api.ashbyhq.com/posting-api/job-board/posthog` | GET | `{jobs: [...]}` |

Note: Lever uses `?limit=1` to minimize data transfer while validating schema.

### State Machine

```python
@dataclass
class CrawlerHealthState:
    source: str  # 'greenhouse' | 'lever' | 'ashby'
    status: str  # 'green' | 'red'
    consecutive_failures: int
    last_success: str | None  # ISO-8601
    last_failure: str | None  # ISO-8601
    last_error: str | None
```

**Transition rules:**
```
on_success:
    consecutive_failures = 0
    status = 'green'
    last_success = now()
    if previous.status == 'red':
        publish_recovery_event()

on_failure:
    consecutive_failures += 1
    last_failure = now()
    last_error = error_message
    if consecutive_failures >= 3 and previous.status != 'red':
        status = 'red'
        publish_alert_event()
```

### State Persistence

`synthetics/state.json` is persistent across runs:

```json
{
  "greenhouse": {
    "status": "green",
    "consecutive_failures": 0,
    "last_success": "2026-05-28T03:00:00Z",
    "last_failure": null,
    "last_error": null
  },
  "lever": {
    "status": "green",
    "consecutive_failures": 0,
    "last_success": "2026-05-28T03:00:00Z",
    "last_failure": null,
    "last_error": null
  },
  "ashby": {
    "status": "green",
    "consecutive_failures": 0,
    "last_success": "2026-05-28T03:00:00Z",
    "last_failure": null,
    "last_error": null
  }
}
```

If the file doesn't exist, initialize with all sources green + zero failures.

### Schema Validation

`expected_schema_v1.json`:

```json
{
  "greenhouse": {
    "type": "object",
    "required": ["jobs"],
    "properties": {
      "jobs": {"type": "array", "minItems": 1}
    }
  },
  "lever": {
    "type": "array",
    "minItems": 1,
    "items": {
      "type": "object",
      "required": ["id"]
    }
  },
  "ashby": {
    "type": "object",
    "required": ["jobs"],
    "properties": {
      "jobs": {"type": "array", "minItems": 1}
    }
  }
}
```

Use `jsonschema` for validation. Schema match = True only if response validates against expected shape AND `jobs` array (or root array for Lever) has ≥1 entry.

### Beat Schedule Extension

`backend/synthetics/beat_schedule.py`:

```python
from celery import Celery
from celery.schedules import crontab

def register_synthetics_beat(app: Celery) -> None:
    """Additively register synthetics tasks on the Celery beat schedule.

    Does NOT modify frozen scheduler-agent entries.
    """
    app.conf.beat_schedule.update({
        'synthetics-crawler-hourly': {
            'task': 'backend.synthetics.tasks.crawler_health_task',
            'schedule': crontab(minute=0),  # Every hour on the hour
            'options': {'queue': 'default'}
        },
        'synthetics-scoring-daily': {
            'task': 'backend.synthetics.tasks.scoring_suite_task',
            'schedule': crontab(hour=3, minute=0),  # 03:00 UTC
            'options': {'queue': 'default'}
        }
    })
```

This function is called from `backend/main.py` lifespan after the Celery app is imported:

```python
from backend.synthetics.beat_schedule import register_synthetics_beat
from backend.scheduler.celery_app import celery_app

register_synthetics_beat(celery_app)
```

### Alert Events

Published to Redis pub/sub channel `agent.status.synthetics.crawler`:

```python
# Alert (red)
{
    "source": "greenhouse",
    "status": "red",
    "consecutive_failures": 3,
    "error": "HTTP 429 Too Many Requests",
    "ts": "2026-05-28T04:00:00Z"
}

# Recovery (green)
{
    "source": "greenhouse",
    "status": "green",
    "consecutive_failures": 0,
    "ts": "2026-05-28T05:00:00Z"
}
```

### Why Not Workday?

Workday requires Playwright for browser automation. Running Playwright hourly is:
1. Expensive (compute cost)
2. Slow (~30s per check vs ~200ms for API endpoints)
3. Flaky (browser automation is inherently less stable)

Workday is exercised daily via the scoring suite. If Workday breaks, the scoring fingerprint will drift on the Workday-sourced JDs.
