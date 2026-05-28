# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Backend synthetics package for Talent Agent.

Provides deterministic scoring drift detection via:
    - ScoringSyntheticRunner: Iterates synthetic candidates × JDs
    - compute_fingerprint: Produces stable JSON fingerprints
    - diff_against_baseline: Compares fingerprints for drift

Contract: NUTRIENTS.md §I.2-I.5, HYPHA-SYNTHETICS-SCORING.md
"""

from backend.synthetics.scoring_runner import ScoringSyntheticRunner

__all__ = ["ScoringSyntheticRunner"]
