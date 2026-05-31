# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Iter-6 tests for the crawler suite CLI wiring.

Supersedes the stale assertion in
``tests/synthetics/test_cli.py::TestMain::test_run_crawler_not_implemented``,
which guarded a feature that no longer exists: iter-5 shipped a working
``CrawlerHealthRunner`` (``backend/synthetics/crawler_health.py``) and the CLI
now dispatches ``--suite=crawler`` to ``run_crawler_suite`` rather than
returning 1.

These tests verify the CORRECT current behavior — that the CLI actually
executes the crawler suite — while remaining deterministic and offline. The
real ``CrawlerHealthRunner.run_suite`` hits live upstreams (Greenhouse, Lever,
Ashby) and writes report/state files; we patch it so no network or filesystem
side effects occur.

Patch target rationale:
    ``run_crawler_suite`` imports ``CrawlerHealthRunner`` lazily from
    ``backend.synthetics.crawler_health`` at call time, so the runner must be
    patched at its definition site
    (``backend.synthetics.crawler_health.CrawlerHealthRunner``), not on the
    ``cli`` module.

We always pass ``--no-publish`` so ``run_crawler_suite`` sets
``publish_events=False`` and never constructs a Redis client — keeping the test
fully offline.

Contract: NUTRIENTS.md §I.6, HYPHA-SYNTHETICS-CRAWLER.md
Owner: synthetics-fix-agent.tests (iter-6)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import structlog

from backend.synthetics.cli import main, run_crawler_suite

logger = structlog.get_logger(__name__)


def _fake_suite_result() -> dict[str, Any]:
    """
    Build a realistic ``run_suite`` return payload.

    Mirrors the shape ``run_crawler_suite`` reads: ``sources``,
    ``state_transitions``, ``run_id``, and ``report_path``.

    Returns:
        A dict matching the contract of ``CrawlerHealthRunner.run_suite``.
    """
    return {
        "run_id": "00000000-0000-4000-8000-000000000abc",
        "started_at": "2026-05-31T00:00:00+00:00",
        "completed_at": "2026-05-31T00:00:01+00:00",
        "sources": [
            {
                "source": "greenhouse",
                "status": "success",
                "latency_ms": 120,
                "schema_match": True,
                "sample_jobs": 7,
                "error": None,
            },
            {
                "source": "lever",
                "status": "failed",
                "latency_ms": 90,
                "schema_match": False,
                "sample_jobs": 0,
                "error": "Schema validation failed",
            },
            {
                "source": "ashby",
                "status": "success",
                "latency_ms": 210,
                "schema_match": True,
                "sample_jobs": 3,
                "error": None,
            },
        ],
        "state_transitions": [
            {
                "source": "greenhouse",
                "previous_status": "green",
                "previous_failures": 0,
                "new_status": "green",
                "new_failures": 0,
                "alert_fired": False,
            },
            {
                "source": "lever",
                "previous_status": "green",
                "previous_failures": 0,
                "new_status": "green",
                "new_failures": 1,
                "alert_fired": False,
            },
            {
                "source": "ashby",
                "previous_status": "green",
                "previous_failures": 0,
                "new_status": "green",
                "new_failures": 0,
                "alert_fired": False,
            },
        ],
        "report_path": "/tmp/synthetics/runs/20260531_000001/crawler-report.json",
    }


class TestCrawlerSuiteCli:
    """
    Tests for ``--suite=crawler`` CLI dispatch (iter-6 corrected behavior).

    These supersede ``test_run_crawler_not_implemented``: the crawler suite is
    implemented, so the CLI runs it and returns the runner's exit code.
    """

    def test_main_dispatches_crawler_to_runner(self) -> None:
        """
        ``main`` with ``--suite=crawler`` should execute the crawler runner.

        Patches ``CrawlerHealthRunner.run_suite`` so no network/filesystem side
        effects occur, then asserts the runner was awaited exactly once and the
        CLI returned 0 (success) for a healthy run.
        """
        mock_run_suite = AsyncMock(return_value=_fake_suite_result())

        with patch(
            "backend.synthetics.crawler_health.CrawlerHealthRunner.run_suite",
            mock_run_suite,
        ):
            with patch(
                "sys.argv",
                ["backend.synthetics", "run", "--suite=crawler", "--no-publish"],
            ):
                result = main()

        mock_run_suite.assert_awaited_once()
        assert result == 0, "crawler suite should return 0 on a successful run"

    def test_main_crawler_does_not_return_not_implemented(self) -> None:
        """
        ``main`` must NOT treat ``--suite=crawler`` as unimplemented.

        The stale test asserted ``main()`` returns 1 (not implemented). This
        asserts the opposite: with the runner mocked, the CLI runs it and
        returns the runner's success code, never the legacy 1.
        """
        mock_run_suite = AsyncMock(return_value=_fake_suite_result())

        with patch(
            "backend.synthetics.crawler_health.CrawlerHealthRunner.run_suite",
            mock_run_suite,
        ):
            with patch(
                "sys.argv",
                ["backend.synthetics", "run", "--suite=crawler", "--no-publish"],
            ):
                result = main()

        assert result != 1, "crawler suite is implemented and must not return the legacy not-implemented code"
        mock_run_suite.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_run_crawler_suite_returns_zero_on_success(self) -> None:
        """
        ``run_crawler_suite`` should return 0 when the runner completes.

        Exercises the coroutine directly (offline, no-publish) and asserts it
        consumes the runner result and reports success.
        """
        mock_run_suite = AsyncMock(return_value=_fake_suite_result())

        with patch(
            "backend.synthetics.crawler_health.CrawlerHealthRunner.run_suite",
            mock_run_suite,
        ):
            exit_code = await run_crawler_suite(publish_events=False, verbose=False)

        assert exit_code == 0
        mock_run_suite.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_run_crawler_suite_returns_one_on_runner_failure(self) -> None:
        """
        ``run_crawler_suite`` should return 1 if the runner raises.

        Confirms the CLI handles a runner failure as a hard error rather than
        propagating the exception.
        """
        mock_run_suite = AsyncMock(side_effect=RuntimeError("upstream exploded"))

        with patch(
            "backend.synthetics.crawler_health.CrawlerHealthRunner.run_suite",
            mock_run_suite,
        ):
            exit_code = await run_crawler_suite(publish_events=False, verbose=False)

        assert exit_code == 1
        mock_run_suite.assert_awaited_once()
