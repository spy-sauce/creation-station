# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
CLI entry point for the synthetics scoring suite.

Provides the command-line interface for running synthetic drift detection:

    python -m backend.synthetics run --suite=scoring

The CLI:
    1. Loads synthetic candidates from the database
    2. Loads JD fixtures from synthetics/fixtures/jobs/
    3. Runs the scoring suite against each candidate × JD pair
    4. Computes fingerprints and compares against baselines
    5. Writes a report to synthetics/runs/<ts>/scoring-report.json
    6. Publishes drift events if severity != green

Contract: NUTRIENTS.md §I.2-I.7, HYPHA-SYNTHETICS-SCORING.md
Owner: synthetics-scoring-agent.cli
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import structlog

# Configure structlog before any logging happens
from backend.observability.logging import configure_logging

configure_logging()

logger = structlog.get_logger(__name__)


# ─── CLI Argument Parser ──────────────────────────────────────────────────────


def create_parser() -> argparse.ArgumentParser:
    """
    Create the argument parser for the synthetics CLI.

    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog="python -m backend.synthetics",
        description="Synthetics monitoring suite for Talent Agent",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Run command
    run_parser = subparsers.add_parser(
        "run",
        help="Execute a synthetics test suite",
    )
    run_parser.add_argument(
        "--suite",
        type=str,
        required=True,
        choices=["scoring", "crawler"],
        help="Suite to run: 'scoring' for drift detection, 'crawler' for health checks",
    )
    run_parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for reports (default: synthetics/runs/<ts>/)",
    )
    run_parser.add_argument(
        "--no-publish",
        action="store_true",
        help="Skip publishing drift events to Redis",
    )
    run_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )
    run_parser.add_argument(
        "--subsequent-run",
        action="store_true",
        help=(
            "Mark this as a subsequent run for cache verification. "
            "Per NUTRIENTS.md §I.5, subsequent runs MUST have "
            "cache_creation_input_tokens == 0. If cache misses are detected, "
            "a cache_miss event is written to the report and logged at WARN level."
        ),
    )

    return parser


# ─── Scoring Suite Runner ─────────────────────────────────────────────────────


async def run_scoring_suite(
    output_dir: Optional[str] = None,
    publish_events: bool = True,
    verbose: bool = False,
    is_subsequent_run: bool = False,
) -> int:
    """
    Execute the scoring drift detection suite.

    Flow:
        1. Initialize database and Redis connections
        2. Load synthetic candidates from database
        3. Load JD fixtures from synthetics/fixtures/jobs/
        4. For each candidate × JD pair, score via RelevanceScorer
        5. Compute fingerprints per candidate
        6. Load baselines and diff against them
        7. Write scoring-report.json to output directory
        8. Publish drift events if severity != green

    Args:
        output_dir: Custom output directory (default: synthetics/runs/<ts>/)
        publish_events: Whether to publish drift events to Redis
        verbose: Enable verbose logging
        is_subsequent_run: Whether this is a subsequent run for cache verification
            Per NUTRIENTS.md §I.5, subsequent runs MUST have
            cache_creation_input_tokens == 0 (hit cache)

    Returns:
        Exit code: 0 for success, 1 for hard failure
    """
    from anthropic import AsyncAnthropic
    import redis.asyncio as aioredis
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

    from backend.config import settings
    from backend.synthetics.scoring_runner import ScoringSyntheticRunner
    from backend.synthetics.fingerprint import (
        compute_fingerprint,
        load_baseline,
        FingerprintContract,
    )
    from backend.synthetics.diff import diff_against_baseline, has_drift

    # Determine output directory
    if output_dir is None:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
        output_path = Path(__file__).parent.parent.parent / "synthetics" / "runs" / ts
    else:
        output_path = Path(output_dir)

    output_path.mkdir(parents=True, exist_ok=True)

    logger.info(
        "scoring_suite.starting",
        output_dir=str(output_path),
        publish_events=publish_events,
        is_subsequent_run=is_subsequent_run,
    )

    # Initialize connections
    engine = create_async_engine(
        settings.database_url,
        echo=verbose,
        pool_pre_ping=True,
    )
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    redis_client = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )

    anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    # Determine fixtures and baselines directories
    synthetics_dir = Path(__file__).parent.parent.parent / "synthetics"
    fixtures_dir = synthetics_dir / "fixtures"
    baselines_dir = fixtures_dir / "baselines"

    try:
        async with async_session() as session:
            # Create runner and execute suite
            # Pass is_subsequent_run for cache contract verification (NUTRIENTS.md §I.5)
            runner = ScoringSyntheticRunner(
                session=session,
                redis_client=redis_client,
                anthropic_client=anthropic_client,
                fixtures_dir=fixtures_dir,
                is_subsequent_run=is_subsequent_run,
            )

            suite_result = await runner.run_suite()

        # Process results and compute fingerprints
        candidates_results = []
        overall_severity = "green"
        contract = FingerprintContract()

        for candidate_result in suite_result.get("candidates", []):
            candidate_id = candidate_result.get("candidate_id")

            # Compute fingerprint
            fingerprint = compute_fingerprint(
                candidate_result,
                contract=contract,
                baseline=None,  # We'll load baseline separately
            )

            # Load baseline if exists
            baseline = load_baseline(str(baselines_dir), candidate_id)

            # Diff against baseline
            drift_report = None
            if baseline is not None:
                drift_report = diff_against_baseline(fingerprint, baseline, contract)

                # Update overall severity
                if drift_report.severity == "red":
                    overall_severity = "red"
                elif drift_report.severity == "yellow" and overall_severity == "green":
                    overall_severity = "yellow"

                # Publish drift event if needed
                if publish_events and has_drift(drift_report):
                    await _publish_drift_event(redis_client, drift_report)

            candidates_results.append({
                "candidate_id": candidate_id,
                "fingerprint": fingerprint.model_dump(),
                "drift_report": drift_report.model_dump() if drift_report else None,
                "cache_stats": candidate_result.get("cache_stats", {}),
            })

        # Build final report (includes cache_verification per NUTRIENTS.md §I.5)
        cache_verification = suite_result.get("cache_verification", {})
        report = {
            "run_id": suite_result.get("run_id"),
            "suite": "scoring",
            "started_at": suite_result.get("started_at"),
            "completed_at": suite_result.get("completed_at"),
            "candidates": candidates_results,
            "overall_status": overall_severity,
            "overall_cache_stats": suite_result.get("overall_cache_stats", {}),
            # Cache verification section (NUTRIENTS.md §I.5)
            "cache_verification": cache_verification,
        }

        # Write report to file
        report_path = output_path / "scoring-report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        # Log cache contract verification result (NUTRIENTS.md §I.5)
        if cache_verification.get("cache_contract_violated", False):
            logger.warning(
                "scoring_suite.cache_contract_violated",
                is_subsequent_run=cache_verification.get("is_subsequent_run"),
                cache_miss_event_count=len(cache_verification.get("cache_miss_events", [])),
                message="Subsequent run had cache misses (cache_creation_input_tokens > 0)",
            )

        logger.info(
            "scoring_suite.complete",
            report_path=str(report_path),
            overall_severity=overall_severity,
            candidates_processed=len(candidates_results),
            cache_hit_rate=suite_result.get("overall_cache_stats", {}).get("cache_hit_rate", 0),
            cache_contract_violated=cache_verification.get("cache_contract_violated", False),
        )

        # Log cache stats
        cache_stats = suite_result.get("overall_cache_stats", {})
        if cache_stats.get("cache_hit_rate", 0) < 0.9:
            logger.warning(
                "scoring_suite.low_cache_hit_rate",
                cache_hit_rate=cache_stats.get("cache_hit_rate"),
                target_rate=0.9,
                cache_misses=cache_stats.get("cache_misses"),
            )

        return 0

    except Exception as e:
        logger.error(
            "scoring_suite.failed",
            error=str(e),
            exc_info=True,
        )
        return 1

    finally:
        # Cleanup connections
        await redis_client.aclose()
        await engine.dispose()


async def _publish_drift_event(
    redis_client,
    drift_report,
) -> None:
    """
    Publish a drift event to Redis pub/sub.

    Channel: agent.status.synthetics.drift
    Contract: NUTRIENTS.md §I.7
    """
    from backend.observability.events import publish_event

    event = {
        "event": "SYNTHETICS_DRIFT",
        "candidate_id": drift_report.candidate_id,
        "run_id": drift_report.run_id,
        "severity": drift_report.severity,
        "violation_count": len(drift_report.exact_violations) + len(drift_report.tolerance_violations),
        "ts": datetime.now(timezone.utc).isoformat(),
    }

    try:
        await publish_event(
            redis_client,
            "agent.status.synthetics.drift",
            event,
        )
        logger.info(
            "drift_event.published",
            candidate_id=drift_report.candidate_id,
            severity=drift_report.severity,
        )
    except Exception as e:
        logger.error(
            "drift_event.publish_failed",
            error=str(e),
            candidate_id=drift_report.candidate_id,
        )


# ─── Main Entry Point ─────────────────────────────────────────────────────────


def main() -> int:
    """
    Main entry point for the synthetics CLI.

    Parses arguments and dispatches to the appropriate suite runner.

    Returns:
        Exit code: 0 for success, 1 for failure
    """
    parser = create_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    if args.command == "run":
        if args.suite == "scoring":
            return asyncio.run(
                run_scoring_suite(
                    output_dir=args.output_dir,
                    publish_events=not args.no_publish,
                    verbose=args.verbose,
                    is_subsequent_run=getattr(args, "subsequent_run", False),
                )
            )
        elif args.suite == "crawler":
            # Crawler suite is owned by synthetics-crawler-agent
            logger.error(
                "cli.suite_not_implemented",
                suite=args.suite,
                message="Crawler suite is owned by synthetics-crawler-agent",
            )
            return 1
        else:
            logger.error("cli.unknown_suite", suite=args.suite)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
