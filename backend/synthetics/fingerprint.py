# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Fingerprint module — produces stable JSON fingerprints for drift detection.

Computes deterministic fingerprints from scoring results that can be compared
across runs. The fingerprint captures both exact-match fields (ordering, IDs)
and tolerance-match fields (scores with bounded variance).

Stability guarantees:
    1. Arrays sorted by deterministic keys (job_id for top_picks)
    2. Floats rounded to 4 decimal places to avoid IEEE precision drift
    3. Timestamps and run_ids excluded from comparison
    4. First 5 top_picks ordering captured as exact-match field

Contract: NUTRIENTS.md §I.2-I.5, HYPHA-SYNTHETICS-SCORING.md
Owner: synthetics-scoring-agent.fingerprint
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# ─── Contract Fields (from NUTRIENTS.md §I.2) ─────────────────────────────────


class ToleranceSpec(BaseModel):
    """Tolerance specification for a numeric field."""

    tolerance: float = Field(description="Allowed variance as ratio (0.05 = ±5%)")


# Default tolerance thresholds from NUTRIENTS.md §I.2
TOLERANCE_THRESHOLDS = {
    "technical_match": ToleranceSpec(tolerance=0.05),
    "level_match": ToleranceSpec(tolerance=0.05),
    "culture_match": ToleranceSpec(tolerance=0.05),
    "industry_match": ToleranceSpec(tolerance=0.05),
    "growth_potential": ToleranceSpec(tolerance=0.05),
    "compensation_match": ToleranceSpec(tolerance=0.05),
    "composite_score": ToleranceSpec(tolerance=0.03),
    "total_jobs_discovered": ToleranceSpec(tolerance=0.10),
}


# ─── Top Pick Fingerprint ─────────────────────────────────────────────────────


class TopPickFingerprint(BaseModel):
    """
    Fingerprint for a single top pick in the digest.

    Captures the exact-match fields: job_id, source, url, position.
    """

    job_id: str = Field(description="Deterministic job ID (synthetic JD UUID)")
    source: str = Field(description="Job source (greenhouse, lever, etc.)")
    url: str = Field(description="Job URL")
    position: int = Field(description="Position in top_picks (0-indexed)")


# ─── Tolerance Field Value ────────────────────────────────────────────────────


class ToleranceFieldValue(BaseModel):
    """
    Value for a tolerance-match field with drift tracking.

    Stores current value, baseline value (if exists), and computed drift %.
    """

    value: float = Field(description="Current value (rounded to 4 decimals)")
    baseline: Optional[float] = Field(
        default=None,
        description="Baseline value for comparison (null if no baseline)",
    )
    drift_pct: Optional[float] = Field(
        default=None,
        description="Drift percentage from baseline (null if no baseline)",
    )


# ─── Exact Fields Container ───────────────────────────────────────────────────


class ExactFields(BaseModel):
    """
    Container for exact-match fields in the fingerprint.

    Per NUTRIENTS.md §I.2, these fields MUST be byte-identical between runs.
    Any difference is a drift violation.
    """

    top_picks: list[TopPickFingerprint] = Field(
        default_factory=list,
        description="First 5 top picks with position (exact-match)",
    )


# ─── Tolerance Fields Container ───────────────────────────────────────────────


class ToleranceFields(BaseModel):
    """
    Container for tolerance-match fields in the fingerprint.

    Per NUTRIENTS.md §I.2, these fields allow bounded variance (±N%).
    Exceeding the tolerance is a drift violation.
    """

    technical_match: ToleranceFieldValue
    level_match: ToleranceFieldValue
    culture_match: ToleranceFieldValue
    industry_match: ToleranceFieldValue
    growth_potential: ToleranceFieldValue
    compensation_match: ToleranceFieldValue
    composite_score: ToleranceFieldValue
    total_jobs_discovered: ToleranceFieldValue


# ─── Scoring Fingerprint ──────────────────────────────────────────────────────


class ScoringFingerprint(BaseModel):
    """
    Stable fingerprint for a candidate's scoring results.

    This is the unit of comparison for drift detection. Contains both
    exact-match fields (must be byte-identical) and tolerance-match
    fields (allow bounded variance).

    Per HYPHA-SYNTHETICS-SCORING.md, fingerprints must be byte-stable
    across runs given the same inputs.

    Contract: NUTRIENTS.md §I.9 (ScoringFingerprint)
    """

    candidate_id: str = Field(description="Synthetic candidate UUID")
    run_id: str = Field(description="UUID of the run that produced this fingerprint")
    computed_at: str = Field(description="ISO-8601 timestamp of computation")
    exact_fields: ExactFields = Field(
        default_factory=ExactFields,
        description="Fields that must be byte-identical",
    )
    tolerance_fields: ToleranceFields = Field(
        description="Fields that allow bounded variance",
    )


# ─── Fingerprint Contract ─────────────────────────────────────────────────────


class FingerprintContract(BaseModel):
    """
    Contract defining which fields are exact-match vs tolerance-match.

    Used by compute_fingerprint to determine how to extract and normalize
    values from scoring results.
    """

    exact_fields: list[str] = Field(
        default_factory=lambda: [
            "digest.top_picks[0..4].job.id",
            "digest.top_picks[0..4].job.source",
            "digest.top_picks[0..4].job.url",
            "digest.top_picks[0..4].ordering",
        ],
        description="Fields requiring byte-identical match",
    )

    tolerance_fields: dict[str, float] = Field(
        default_factory=lambda: {
            "score.technical_match": 0.05,
            "score.level_match": 0.05,
            "score.culture_match": 0.05,
            "score.industry_match": 0.05,
            "score.growth_potential": 0.05,
            "score.compensation_match": 0.05,
            "composite_score": 0.03,
            "total_jobs_discovered": 0.10,
        },
        description="Field -> tolerance (as ratio)",
    )

    excluded_fields: list[str] = Field(
        default_factory=lambda: [
            "created_at",
            "updated_at",
            "run_id",
            "crawl_run.duration_seconds",
            "crawl_run.started_at",
            "crawl_run.completed_at",
            "non_synthetic_uuids",
        ],
        description="Fields excluded from all comparisons",
    )


# ─── Fingerprint Computation ──────────────────────────────────────────────────


def compute_fingerprint(
    candidate_scoring_result: dict,
    contract: Optional[FingerprintContract] = None,
    baseline: Optional[ScoringFingerprint] = None,
) -> ScoringFingerprint:
    """
    Compute a stable fingerprint from scoring results.

    Takes the raw scoring output from ScoringSyntheticRunner and produces
    a deterministic fingerprint suitable for drift comparison.

    Stability guarantees:
        1. Top picks sorted by job_id before position assignment
        2. All floats rounded to 4 decimal places
        3. Timestamps excluded (only computed_at for reference)
        4. Only first 5 top picks captured

    Args:
        candidate_scoring_result: Dict from CandidateScoringResult.model_dump()
            Expected keys: candidate_id, scored_results, cache_stats
        contract: Optional FingerprintContract defining comparison rules
            Defaults to standard contract from NUTRIENTS.md §I.2
        baseline: Optional baseline fingerprint for drift calculation

    Returns:
        ScoringFingerprint with exact and tolerance fields populated

    Example:
        >>> result = await runner.run_suite()
        >>> for candidate in result["candidates"]:
        ...     fp = compute_fingerprint(candidate)
        ...     print(fp.candidate_id, fp.tolerance_fields.composite_score.value)
    """
    if contract is None:
        contract = FingerprintContract()

    candidate_id = candidate_scoring_result.get("candidate_id", "unknown")
    scored_results = candidate_scoring_result.get("scored_results", [])

    logger.debug(
        "fingerprint.computing",
        candidate_id=candidate_id,
        scored_results_count=len(scored_results),
    )

    # Extract and sort scored results for deterministic ordering
    # Sort by jd_filename for reproducibility
    sorted_results = sorted(
        [r for r in scored_results if r.get("scored_job") is not None],
        key=lambda r: r.get("jd_filename", ""),
    )

    # Compute exact fields: first 5 top picks by composite score
    top_results = sorted(
        sorted_results,
        key=lambda r: r.get("scored_job", {}).get("composite_score", 0),
        reverse=True,
    )[:5]

    top_picks: list[TopPickFingerprint] = []
    for position, result in enumerate(top_results):
        scored_job = result.get("scored_job", {})
        top_picks.append(
            TopPickFingerprint(
                job_id=str(scored_job.get("discovered_job_id", "")),
                source=str(result.get("jd_filename", "").split("-")[0]),  # Extract source prefix
                url=str(scored_job.get("url", "")),
                position=position,
            )
        )

    exact_fields = ExactFields(top_picks=top_picks)

    # Compute tolerance fields: aggregate score dimensions
    tolerance_fields = _compute_tolerance_fields(
        scored_results,
        baseline,
    )

    # Generate deterministic run_id from candidate_id + computed_at
    computed_at = datetime.now(timezone.utc).isoformat()

    fingerprint = ScoringFingerprint(
        candidate_id=candidate_id,
        run_id=candidate_scoring_result.get("run_id", "unknown"),
        computed_at=computed_at,
        exact_fields=exact_fields,
        tolerance_fields=tolerance_fields,
    )

    logger.info(
        "fingerprint.computed",
        candidate_id=candidate_id,
        top_picks_count=len(top_picks),
        composite_score=tolerance_fields.composite_score.value,
    )

    return fingerprint


def _compute_tolerance_fields(
    scored_results: list[dict],
    baseline: Optional[ScoringFingerprint],
) -> ToleranceFields:
    """
    Compute tolerance field values from scored results.

    Aggregates score dimensions across all scored jobs and computes
    drift percentage if a baseline is provided.

    Args:
        scored_results: List of scoring result dicts
        baseline: Optional baseline fingerprint for drift calculation

    Returns:
        ToleranceFields with aggregated values and drift percentages
    """
    # Collect all score dimensions
    tech_scores: list[int] = []
    level_scores: list[int] = []
    culture_scores: list[int] = []
    industry_scores: list[int] = []
    growth_scores: list[int] = []
    comp_scores: list[int] = []
    composite_scores: list[int] = []

    for result in scored_results:
        scored_job = result.get("scored_job")
        if scored_job is None:
            continue

        breakdown = scored_job.get("score_breakdown", {})
        tech_scores.append(breakdown.get("technical_match", 0))
        level_scores.append(breakdown.get("level_match", 0))
        culture_scores.append(breakdown.get("culture_match", 0))
        industry_scores.append(breakdown.get("industry_match", 0))
        growth_scores.append(breakdown.get("growth_potential", 0))
        comp_scores.append(breakdown.get("compensation_match", 0))
        composite_scores.append(scored_job.get("composite_score", 0))

    # Compute averages (rounded to 4 decimals for stability)
    def avg(scores: list[int]) -> float:
        if not scores:
            return 0.0
        return round(sum(scores) / len(scores), 4)

    tech_avg = avg(tech_scores)
    level_avg = avg(level_scores)
    culture_avg = avg(culture_scores)
    industry_avg = avg(industry_scores)
    growth_avg = avg(growth_scores)
    comp_avg = avg(comp_scores)
    composite_avg = avg(composite_scores)
    total_discovered = float(len(scored_results))

    # Helper to compute drift percentage
    def drift_pct(current: float, baseline_val: Optional[float]) -> Optional[float]:
        if baseline_val is None or baseline_val == 0:
            return None
        return round((current - baseline_val) / baseline_val, 4)

    # Extract baseline values if present
    baseline_tech = None
    baseline_level = None
    baseline_culture = None
    baseline_industry = None
    baseline_growth = None
    baseline_comp = None
    baseline_composite = None
    baseline_discovered = None

    if baseline is not None:
        baseline_tech = baseline.tolerance_fields.technical_match.value
        baseline_level = baseline.tolerance_fields.level_match.value
        baseline_culture = baseline.tolerance_fields.culture_match.value
        baseline_industry = baseline.tolerance_fields.industry_match.value
        baseline_growth = baseline.tolerance_fields.growth_potential.value
        baseline_comp = baseline.tolerance_fields.compensation_match.value
        baseline_composite = baseline.tolerance_fields.composite_score.value
        baseline_discovered = baseline.tolerance_fields.total_jobs_discovered.value

    return ToleranceFields(
        technical_match=ToleranceFieldValue(
            value=tech_avg,
            baseline=baseline_tech,
            drift_pct=drift_pct(tech_avg, baseline_tech),
        ),
        level_match=ToleranceFieldValue(
            value=level_avg,
            baseline=baseline_level,
            drift_pct=drift_pct(level_avg, baseline_level),
        ),
        culture_match=ToleranceFieldValue(
            value=culture_avg,
            baseline=baseline_culture,
            drift_pct=drift_pct(culture_avg, baseline_culture),
        ),
        industry_match=ToleranceFieldValue(
            value=industry_avg,
            baseline=baseline_industry,
            drift_pct=drift_pct(industry_avg, baseline_industry),
        ),
        growth_potential=ToleranceFieldValue(
            value=growth_avg,
            baseline=baseline_growth,
            drift_pct=drift_pct(growth_avg, baseline_growth),
        ),
        compensation_match=ToleranceFieldValue(
            value=comp_avg,
            baseline=baseline_comp,
            drift_pct=drift_pct(comp_avg, baseline_comp),
        ),
        composite_score=ToleranceFieldValue(
            value=composite_avg,
            baseline=baseline_composite,
            drift_pct=drift_pct(composite_avg, baseline_composite),
        ),
        total_jobs_discovered=ToleranceFieldValue(
            value=total_discovered,
            baseline=baseline_discovered,
            drift_pct=drift_pct(total_discovered, baseline_discovered),
        ),
    )


# ─── Baseline Loading ─────────────────────────────────────────────────────────


def load_baseline(
    baselines_dir: str,
    candidate_id: str,
) -> Optional[ScoringFingerprint]:
    """
    Load the latest accepted baseline for a candidate.

    Baselines are stored at:
        synthetics/fixtures/baselines/<candidate_id>__<run_id>.json

    Only committed baselines are considered valid. The latest by
    accepted_at timestamp is returned.

    Args:
        baselines_dir: Path to synthetics/fixtures/baselines/
        candidate_id: Synthetic candidate UUID

    Returns:
        ScoringFingerprint from baseline, or None if no baseline exists
    """
    import json
    from pathlib import Path

    baselines_path = Path(baselines_dir)
    if not baselines_path.exists():
        logger.debug("fingerprint.baseline_dir_not_found", path=baselines_dir)
        return None

    # Find all baselines for this candidate
    pattern = f"{candidate_id}__*.json"
    baseline_files = list(baselines_path.glob(pattern))

    if not baseline_files:
        logger.debug(
            "fingerprint.no_baseline",
            candidate_id=candidate_id,
            pattern=pattern,
        )
        return None

    # Sort by file modification time (latest first)
    baseline_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    latest_file = baseline_files[0]

    logger.debug(
        "fingerprint.loading_baseline",
        candidate_id=candidate_id,
        file=str(latest_file),
    )

    try:
        with open(latest_file) as f:
            data = json.load(f)
            # Extract just the fingerprint portion
            fingerprint_data = data.get("fingerprint", data)
            return ScoringFingerprint.model_validate(fingerprint_data)
    except Exception as e:
        logger.error(
            "fingerprint.baseline_load_error",
            file=str(latest_file),
            error=str(e),
        )
        return None


def save_baseline(
    baselines_dir: str,
    fingerprint: ScoringFingerprint,
) -> str:
    """
    Save a fingerprint as a baseline (for baseline acceptance workflow).

    Creates a file at:
        synthetics/fixtures/baselines/<candidate_id>__<run_id>.json

    Note: This function writes the file but does NOT commit it.
    Baseline acceptance requires explicit commit via:
        mycelium synthetics baseline accept <run_id>

    Args:
        baselines_dir: Path to synthetics/fixtures/baselines/
        fingerprint: ScoringFingerprint to save

    Returns:
        Path to the saved baseline file
    """
    import json
    from pathlib import Path

    baselines_path = Path(baselines_dir)
    baselines_path.mkdir(parents=True, exist_ok=True)

    filename = f"{fingerprint.candidate_id}__{fingerprint.run_id}.json"
    filepath = baselines_path / filename

    baseline_record = {
        "candidate_id": fingerprint.candidate_id,
        "run_id": fingerprint.run_id,
        "accepted_at": datetime.now(timezone.utc).isoformat(),
        "fingerprint": fingerprint.model_dump(),
    }

    with open(filepath, "w") as f:
        json.dump(baseline_record, f, indent=2)

    logger.info(
        "fingerprint.baseline_saved",
        candidate_id=fingerprint.candidate_id,
        run_id=fingerprint.run_id,
        file=str(filepath),
    )

    return str(filepath)
