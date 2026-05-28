# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Backend synthetics package for Talent Agent.

Provides two monitoring capabilities:

1. Scoring Drift Detection (synthetics-scoring-agent):
    - ScoringSyntheticRunner: Iterates synthetic candidates × JDs
    - compute_fingerprint: Produces stable JSON fingerprints
    - diff_against_baseline: Compares fingerprints for drift
    - DriftReport: Drift comparison result with severity

2. Crawler Health Monitoring (synthetics-crawler-agent):
    - CrawlerHealthRunner: Hits known-good slugs per source
    - CrawlerHealthState: Tracks consecutive failures + alerts
    - State machine: 3-strike threshold for alerts

Contract: NUTRIENTS.md §I.2-I.6, HYPHA-SYNTHETICS-SCORING.md, HYPHA-SYNTHETICS-CRAWLER.md
"""

from backend.synthetics.diff import (
    DriftReport,
    DriftViolation,
    diff_against_baseline,
    has_drift,
    is_critical,
    format_summary,
)
from backend.synthetics.fingerprint import (
    FingerprintContract,
    ScoringFingerprint,
    compute_fingerprint,
    load_baseline,
    save_baseline,
)
from backend.synthetics.scoring_runner import ScoringSyntheticRunner
from backend.synthetics.crawler_health import (
    CrawlerHealthRunner,
    CrawlerHealthState,
    SourceCheckResult,
    StateTransition,
)
from backend.synthetics.beat_schedule import (
    register_synthetics_beat,
    crawler_health_task,
    scoring_suite_task,
)

__all__ = [
    # Scoring Runner
    "ScoringSyntheticRunner",
    # Crawler Health Runner
    "CrawlerHealthRunner",
    "CrawlerHealthState",
    "SourceCheckResult",
    "StateTransition",
    # Fingerprint
    "FingerprintContract",
    "ScoringFingerprint",
    "compute_fingerprint",
    "load_baseline",
    "save_baseline",
    # Diff
    "DriftReport",
    "DriftViolation",
    "diff_against_baseline",
    "has_drift",
    "is_critical",
    "format_summary",
    # Beat Schedule
    "register_synthetics_beat",
    "crawler_health_task",
    "scoring_suite_task",
]
