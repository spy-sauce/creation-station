# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Backend synthetics package for Talent Agent.

Provides deterministic scoring drift detection via:
    - ScoringSyntheticRunner: Iterates synthetic candidates × JDs
    - compute_fingerprint: Produces stable JSON fingerprints
    - diff_against_baseline: Compares fingerprints for drift
    - DriftReport: Drift comparison result with severity

Contract: NUTRIENTS.md §I.2-I.5, HYPHA-SYNTHETICS-SCORING.md
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

__all__ = [
    # Runner
    "ScoringSyntheticRunner",
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
]
