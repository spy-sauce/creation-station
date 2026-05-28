# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Crawler Health Runner — upstream health monitoring for job board sources.

Exercises live crawler endpoints (Greenhouse, Lever, Ashby) with lightweight
requests, tracks consecutive failures via a state machine, and alerts on
3-strike threshold.

The runner hits known-good slugs per source to verify:
  1. HTTP connectivity
  2. Response schema matches expected shape
  3. At least 1 job returned (source is active)

Workday is NOT checked hourly — Playwright is too expensive. Workday exercises
daily via the scoring suite.

Contract: NUTRIENTS.md §I.6, HYPHA-SYNTHETICS-CRAWLER.md
Owner: synthetics-crawler-agent.runner
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Literal

import httpx
import structlog
import redis.asyncio as aioredis

logger = structlog.get_logger(__name__)

# ─── Health Check Targets ─────────────────────────────────────────────────────
# Contract: HYPHA-SYNTHETICS-CRAWLER.md "Health Check Targets"

HEALTH_TARGETS: dict[str, dict] = {
    "greenhouse": {
        "slug": "anthropic",
        "url": "https://boards.greenhouse.io/anthropic.json",
        "method": "GET",
    },
    "lever": {
        "slug": "netflix",
        "url": "https://api.lever.co/v0/postings/netflix?limit=1",
        "method": "GET",
    },
    "ashby": {
        "slug": "posthog",
        "url": "https://api.ashbyhq.com/posting-api/job-board/posthog",
        "method": "GET",
    },
}

USER_AGENT = "TalentAgent/1.0 (+https://github.com/example/talent-agent)"
HTTP_TIMEOUT = 15.0

# Paths
STATE_FILE_PATH = Path(__file__).parent.parent.parent / "synthetics" / "state.json"
RUNS_DIR = Path(__file__).parent.parent.parent / "synthetics" / "runs"


# ─── State Machine ────────────────────────────────────────────────────────────
# Contract: NUTRIENTS.md §I.6

SourceName = Literal["greenhouse", "lever", "ashby"]
StatusColor = Literal["green", "red"]


@dataclass
class CrawlerHealthState:
    """
    State for a single crawler source.

    Tracks consecutive failures and status color per NUTRIENTS.md §I.6.
    """

    source: SourceName
    status: StatusColor = "green"
    consecutive_failures: int = 0
    last_success: Optional[str] = None  # ISO-8601
    last_failure: Optional[str] = None  # ISO-8601
    last_error: Optional[str] = None


@dataclass
class SourceCheckResult:
    """Result of checking a single source."""

    source: SourceName
    status: Literal["success", "failed"]
    latency_ms: int
    schema_match: bool
    sample_jobs: int
    error: Optional[str] = None


@dataclass
class StateTransition:
    """Records a state transition for a source."""

    source: SourceName
    previous_status: StatusColor
    previous_failures: int
    new_status: StatusColor
    new_failures: int
    alert_fired: bool


# ─── State Persistence ────────────────────────────────────────────────────────


def _load_state() -> dict[str, CrawlerHealthState]:
    """
    Load state from synthetics/state.json.

    If the file doesn't exist, initialize with all sources green + zero failures.
    """
    if not STATE_FILE_PATH.exists():
        logger.info("crawler_health.state_init", path=str(STATE_FILE_PATH))
        return _default_state()

    try:
        with open(STATE_FILE_PATH, "r") as f:
            data = json.load(f)

        states: dict[str, CrawlerHealthState] = {}
        for source in HEALTH_TARGETS:
            source_data = data.get(source, {})
            states[source] = CrawlerHealthState(
                source=source,  # type: ignore
                status=source_data.get("status", "green"),
                consecutive_failures=source_data.get("consecutive_failures", 0),
                last_success=source_data.get("last_success"),
                last_failure=source_data.get("last_failure"),
                last_error=source_data.get("last_error"),
            )

        logger.debug("crawler_health.state_loaded", sources=list(states.keys()))
        return states

    except Exception as e:
        logger.error("crawler_health.state_load_error", error=str(e))
        return _default_state()


def _default_state() -> dict[str, CrawlerHealthState]:
    """Return default state with all sources green."""
    return {
        source: CrawlerHealthState(source=source)  # type: ignore
        for source in HEALTH_TARGETS
    }


def _save_state(states: dict[str, CrawlerHealthState]) -> None:
    """Persist state to synthetics/state.json."""
    # Ensure directory exists
    STATE_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

    data = {}
    for source, state in states.items():
        data[source] = {
            "status": state.status,
            "consecutive_failures": state.consecutive_failures,
            "last_success": state.last_success,
            "last_failure": state.last_failure,
            "last_error": state.last_error,
        }

    with open(STATE_FILE_PATH, "w") as f:
        json.dump(data, f, indent=2)

    logger.debug("crawler_health.state_saved", path=str(STATE_FILE_PATH))


# ─── Schema Validation ────────────────────────────────────────────────────────
# Using simple checks instead of jsonschema to avoid new dependency


def _validate_greenhouse_schema(data: dict) -> tuple[bool, int]:
    """
    Validate Greenhouse response schema.

    Expected: {"jobs": [...]} with at least 1 job.

    Returns:
        (schema_match, sample_jobs)
    """
    if not isinstance(data, dict):
        return False, 0
    if "jobs" not in data:
        return False, 0
    jobs = data.get("jobs")
    if not isinstance(jobs, list):
        return False, 0
    if len(jobs) < 1:
        return False, 0
    return True, len(jobs)


def _validate_lever_schema(data: list) -> tuple[bool, int]:
    """
    Validate Lever response schema.

    Expected: [{id, ...}, ...] array with at least 1 posting.

    Returns:
        (schema_match, sample_jobs)
    """
    if not isinstance(data, list):
        return False, 0
    if len(data) < 1:
        return False, 0
    # Check first item has 'id'
    if not isinstance(data[0], dict) or "id" not in data[0]:
        return False, 0
    return True, len(data)


def _validate_ashby_schema(data: dict) -> tuple[bool, int]:
    """
    Validate Ashby response schema.

    Expected: {"jobs": [...]} with at least 1 job.

    Returns:
        (schema_match, sample_jobs)
    """
    if not isinstance(data, dict):
        return False, 0
    if "jobs" not in data:
        return False, 0
    jobs = data.get("jobs")
    if not isinstance(jobs, list):
        return False, 0
    if len(jobs) < 1:
        return False, 0
    return True, len(jobs)


def _validate_schema(source: SourceName, data) -> tuple[bool, int]:
    """Route to the appropriate schema validator."""
    if source == "greenhouse":
        return _validate_greenhouse_schema(data)
    elif source == "lever":
        return _validate_lever_schema(data)
    elif source == "ashby":
        return _validate_ashby_schema(data)
    else:
        return False, 0


# ─── Health Check Execution ───────────────────────────────────────────────────


async def _check_source(
    client: httpx.AsyncClient,
    source: SourceName,
) -> SourceCheckResult:
    """
    Execute health check for a single source.

    Args:
        client: httpx async client
        source: Source name (greenhouse, lever, ashby)

    Returns:
        SourceCheckResult with status, latency, schema validation, etc.
    """
    target = HEALTH_TARGETS[source]
    url = target["url"]
    method = target["method"]

    start_time = datetime.now(timezone.utc)

    try:
        if method == "GET":
            response = await client.get(url)
        else:
            response = await client.post(url)

        latency_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

        response.raise_for_status()
        data = response.json()

        schema_match, sample_jobs = _validate_schema(source, data)

        if not schema_match:
            logger.warning(
                "crawler_health.schema_mismatch",
                source=source,
                url=url,
            )
            return SourceCheckResult(
                source=source,
                status="failed",
                latency_ms=latency_ms,
                schema_match=False,
                sample_jobs=sample_jobs,
                error="Schema validation failed",
            )

        logger.info(
            "crawler_health.source_success",
            source=source,
            latency_ms=latency_ms,
            sample_jobs=sample_jobs,
        )

        return SourceCheckResult(
            source=source,
            status="success",
            latency_ms=latency_ms,
            schema_match=True,
            sample_jobs=sample_jobs,
        )

    except httpx.HTTPStatusError as e:
        latency_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        error_msg = f"HTTP {e.response.status_code}"

        logger.warning(
            "crawler_health.http_error",
            source=source,
            status_code=e.response.status_code,
            url=url,
        )

        return SourceCheckResult(
            source=source,
            status="failed",
            latency_ms=latency_ms,
            schema_match=False,
            sample_jobs=0,
            error=error_msg,
        )

    except httpx.TimeoutException:
        latency_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

        logger.warning(
            "crawler_health.timeout",
            source=source,
            url=url,
            timeout_seconds=HTTP_TIMEOUT,
        )

        return SourceCheckResult(
            source=source,
            status="failed",
            latency_ms=latency_ms,
            schema_match=False,
            sample_jobs=0,
            error=f"Timeout after {HTTP_TIMEOUT}s",
        )

    except Exception as e:
        latency_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        error_msg = str(e)

        logger.error(
            "crawler_health.unexpected_error",
            source=source,
            url=url,
            error=error_msg,
        )

        return SourceCheckResult(
            source=source,
            status="failed",
            latency_ms=latency_ms,
            schema_match=False,
            sample_jobs=0,
            error=error_msg,
        )


# ─── State Machine Transitions ────────────────────────────────────────────────


def _apply_result_to_state(
    result: SourceCheckResult,
    state: CrawlerHealthState,
) -> tuple[CrawlerHealthState, StateTransition]:
    """
    Apply a check result to the current state, returning new state + transition.

    Transition rules from NUTRIENTS.md §I.6:
    - on_success: consecutive_failures = 0, status = 'green'
    - on_failure: consecutive_failures += 1, if >= 3 then status = 'red'

    Args:
        result: SourceCheckResult from the health check
        state: Current CrawlerHealthState

    Returns:
        (new_state, transition) tuple
    """
    now = datetime.now(timezone.utc).isoformat()

    previous_status = state.status
    previous_failures = state.consecutive_failures
    alert_fired = False

    if result.status == "success":
        # Success case
        new_state = CrawlerHealthState(
            source=state.source,
            status="green",
            consecutive_failures=0,
            last_success=now,
            last_failure=state.last_failure,
            last_error=None,
        )

        # Recovery: was red, now green
        if previous_status == "red":
            alert_fired = True
            logger.info(
                "crawler_health.recovery",
                source=state.source,
                previous_failures=previous_failures,
            )
    else:
        # Failure case
        new_failures = state.consecutive_failures + 1
        new_status: StatusColor = state.status

        # Transition to red at 3+ failures
        if new_failures >= 3 and previous_status != "red":
            new_status = "red"
            alert_fired = True
            logger.warning(
                "crawler_health.alert_threshold",
                source=state.source,
                consecutive_failures=new_failures,
                error=result.error,
            )

        new_state = CrawlerHealthState(
            source=state.source,
            status=new_status,
            consecutive_failures=new_failures,
            last_success=state.last_success,
            last_failure=now,
            last_error=result.error,
        )

    transition = StateTransition(
        source=state.source,
        previous_status=previous_status,
        previous_failures=previous_failures,
        new_status=new_state.status,
        new_failures=new_state.consecutive_failures,
        alert_fired=alert_fired,
    )

    return new_state, transition


# ─── Event Publishing ─────────────────────────────────────────────────────────


async def _publish_event(
    redis_client: Optional[aioredis.Redis],
    source: SourceName,
    status: StatusColor,
    consecutive_failures: int,
    error: Optional[str] = None,
) -> None:
    """
    Publish alert/recovery event to Redis pub/sub.

    Channel: agent.status.synthetics.crawler

    Args:
        redis_client: Async Redis client (may be None in tests)
        source: Source name
        status: 'red' (alert) or 'green' (recovery)
        consecutive_failures: Current failure count
        error: Error message (for alerts)
    """
    if redis_client is None:
        logger.debug(
            "crawler_health.pubsub_skip",
            reason="no_redis_client",
        )
        return

    event = {
        "source": source,
        "status": status,
        "consecutive_failures": consecutive_failures,
        "ts": datetime.now(timezone.utc).isoformat(),
    }

    if error and status == "red":
        event["error"] = error

    channel = "agent.status.synthetics.crawler"

    try:
        await redis_client.publish(channel, json.dumps(event))
        logger.info(
            "crawler_health.event_published",
            channel=channel,
            source=source,
            status=status,
        )
    except Exception as e:
        logger.error(
            "crawler_health.publish_failed",
            channel=channel,
            error=str(e),
        )


# ─── Report Generation ────────────────────────────────────────────────────────


def _write_report(
    run_id: str,
    started_at: str,
    completed_at: str,
    results: list[SourceCheckResult],
    transitions: list[StateTransition],
) -> Path:
    """
    Write the crawler health report to synthetics/runs/<ts>/crawler-report.json.

    Returns:
        Path to the written report file.
    """
    # Use timestamp-based directory like scoring runner
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = RUNS_DIR / ts
    run_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "run_id": run_id,
        "suite": "crawler",
        "started_at": started_at,
        "completed_at": completed_at,
        "sources": [
            {
                "source": r.source,
                "status": r.status,
                "latency_ms": r.latency_ms,
                "schema_match": r.schema_match,
                "sample_jobs": r.sample_jobs,
                "error": r.error,
            }
            for r in results
        ],
        "state_transitions": [
            {
                "source": t.source,
                "previous_state": {
                    "status": t.previous_status,
                    "consecutive_failures": t.previous_failures,
                },
                "new_state": {
                    "status": t.new_status,
                    "consecutive_failures": t.new_failures,
                },
                "alert_fired": t.alert_fired,
            }
            for t in transitions
        ],
    }

    report_path = run_dir / "crawler-report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    logger.info(
        "crawler_health.report_written",
        path=str(report_path),
        run_id=run_id,
    )

    return report_path


# ─── CrawlerHealthRunner ──────────────────────────────────────────────────────


class CrawlerHealthRunner:
    """
    Upstream health monitoring runner for job board sources.

    Exercises live crawler endpoints (Greenhouse, Lever, Ashby) with lightweight
    requests, tracks consecutive failures via a state machine, and alerts on
    3-strike threshold.

    Contract: NUTRIENTS.md §I.6, HYPHA-SYNTHETICS-CRAWLER.md
    """

    def __init__(
        self,
        redis_client: Optional[aioredis.Redis] = None,
    ):
        """
        Initialize the CrawlerHealthRunner.

        Args:
            redis_client: Async Redis client for pub/sub events (optional)
        """
        self._redis = redis_client
        self._run_id = str(uuid.uuid4())

    async def run_suite(self) -> dict:
        """
        Execute the full crawler health suite.

        Checks all sources (Greenhouse, Lever, Ashby), updates state,
        publishes alerts/recoveries, and writes a report.

        Returns:
            dict with:
                - run_id: UUID of this run
                - started_at: ISO timestamp
                - completed_at: ISO timestamp
                - sources: list of source check results
                - state_transitions: list of state transitions
                - report_path: path to the written report
        """
        started_at = datetime.now(timezone.utc)

        logger.info(
            "crawler_health.suite_start",
            run_id=self._run_id,
            sources=list(HEALTH_TARGETS.keys()),
        )

        # Load current state
        states = _load_state()

        # Check each source
        results: list[SourceCheckResult] = []
        transitions: list[StateTransition] = []
        new_states: dict[str, CrawlerHealthState] = {}

        async with httpx.AsyncClient(
            timeout=HTTP_TIMEOUT,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            },
            follow_redirects=True,
        ) as client:
            for source in HEALTH_TARGETS:
                source_name: SourceName = source  # type: ignore

                result = await _check_source(client, source_name)
                results.append(result)

                # Apply to state
                current_state = states.get(source, CrawlerHealthState(source=source_name))
                new_state, transition = _apply_result_to_state(result, current_state)
                new_states[source] = new_state
                transitions.append(transition)

                # Publish event if alert fired
                if transition.alert_fired:
                    await _publish_event(
                        self._redis,
                        source_name,
                        new_state.status,
                        new_state.consecutive_failures,
                        new_state.last_error,
                    )

        # Save updated state
        _save_state(new_states)

        completed_at = datetime.now(timezone.utc)

        # Write report
        report_path = _write_report(
            self._run_id,
            started_at.isoformat(),
            completed_at.isoformat(),
            results,
            transitions,
        )

        logger.info(
            "crawler_health.suite_complete",
            run_id=self._run_id,
            duration_seconds=(completed_at - started_at).total_seconds(),
            sources_checked=len(results),
            alerts_fired=sum(1 for t in transitions if t.alert_fired),
        )

        return {
            "run_id": self._run_id,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "sources": [
                {
                    "source": r.source,
                    "status": r.status,
                    "latency_ms": r.latency_ms,
                    "schema_match": r.schema_match,
                    "sample_jobs": r.sample_jobs,
                    "error": r.error,
                }
                for r in results
            ],
            "state_transitions": [
                {
                    "source": t.source,
                    "previous_status": t.previous_status,
                    "previous_failures": t.previous_failures,
                    "new_status": t.new_status,
                    "new_failures": t.new_failures,
                    "alert_fired": t.alert_fired,
                }
                for t in transitions
            ],
            "report_path": str(report_path),
        }
