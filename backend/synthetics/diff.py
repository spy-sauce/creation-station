# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Diff module — compares fingerprints against baselines to detect drift.

Implements the drift detection logic per NUTRIENTS.md §I.2-I.4:
    - Exact-match violations: any difference in top_picks ordering/IDs
    - Tolerance violations: score dimensions exceeding ±N% threshold
    - Severity rules: green (clean), yellow (tolerance only), red (exact or 2× tolerance)

Contract: NUTRIENTS.md §I.2-I.4, HYPHA-SYNTHETICS-SCORING.md
Owner: synthetics-scoring-agent.diff
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional, Literal

import structlog
from pydantic import BaseModel, Field

from backend.synthetics.fingerprint import (
    FingerprintContract,
    ScoringFingerprint,
    TopPickFingerprint,
    TOLERANCE_THRESHOLDS,
)

logger = structlog.get_logger(__name__)


# ─── Drift Severity (from NUTRIENTS.md §I.4) ─────────────────────────────────


DriftSeverity = Literal["green", "yellow", "red"]


# ─── Drift Violation ─────────────────────────────────────────────────────────


class DriftViolation(BaseModel):
    """
    A single drift violation detected during comparison.

    Captures the field that drifted, baseline and current values,
    and delta percentage for tolerance fields.

    Contract: NUTRIENTS.md §I.4 (DriftViolation)
    """

    field: str = Field(description="Path to the drifted field")
    baseline_value: Any = Field(description="Value in the baseline fingerprint")
    current_value: Any = Field(description="Value in the current fingerprint")
    delta_pct: Optional[float] = Field(
        default=None,
        description="Drift percentage for tolerance fields (null for exact fields)",
    )


# ─── Drift Report ────────────────────────────────────────────────────────────


class DriftReport(BaseModel):
    """
    Complete drift report comparing a fingerprint against baseline.

    Contains all exact-match and tolerance violations, plus computed
    severity level.

    Severity rules (NUTRIENTS.md §I.4):
        - green: zero violations
        - yellow: tolerance violations only, no exact-match violations
        - red: any exact-match violation OR tolerance violation > 2× threshold

    Contract: NUTRIENTS.md §I.4 (DriftReport)
    """

    candidate_id: str = Field(description="Synthetic candidate UUID")
    run_id: str = Field(description="UUID of the current run")
    baseline_run_id: str = Field(description="UUID of the baseline run")
    exact_violations: list[DriftViolation] = Field(
        default_factory=list,
        description="Exact-match field violations (any difference = violation)",
    )
    tolerance_violations: list[DriftViolation] = Field(
        default_factory=list,
        description="Tolerance-match field violations (exceeded threshold)",
    )
    severity: DriftSeverity = Field(description="Overall severity level")
    computed_at: str = Field(description="ISO-8601 timestamp of comparison")


# ─── Diff Functions ──────────────────────────────────────────────────────────


def diff_against_baseline(
    fingerprint: ScoringFingerprint,
    baseline: ScoringFingerprint,
    contract: Optional[FingerprintContract] = None,
) -> DriftReport:
    """
    Compare a fingerprint against baseline and produce a DriftReport.

    Checks both exact-match fields (top_picks ordering) and tolerance-match
    fields (score dimensions) for drift violations.

    Severity calculation (NUTRIENTS.md §I.4):
        - green: zero violations
        - yellow: tolerance violations only, no exact-match violations
        - red: any exact-match violation OR tolerance violation > 2× threshold

    Args:
        fingerprint: Current scoring fingerprint to compare
        baseline: Accepted baseline fingerprint to compare against
        contract: Optional FingerprintContract with tolerance thresholds
            Defaults to standard contract from NUTRIENTS.md §I.2

    Returns:
        DriftReport with violations and severity

    Example:
        >>> fp = compute_fingerprint(result)
        >>> baseline = load_baseline(baselines_dir, candidate_id)
        >>> if baseline:
        ...     report = diff_against_baseline(fp, baseline)
        ...     if report.severity != "green":
        ...         publish_drift_alert(report)
    """
    if contract is None:
        contract = FingerprintContract()

    logger.debug(
        "diff.comparing",
        candidate_id=fingerprint.candidate_id,
        run_id=fingerprint.run_id,
        baseline_run_id=baseline.run_id,
    )

    # Check exact-match violations
    exact_violations = _check_exact_violations(fingerprint, baseline)

    # Check tolerance violations
    tolerance_violations = _check_tolerance_violations(
        fingerprint,
        baseline,
        contract,
    )

    # Compute severity
    severity = _compute_severity(exact_violations, tolerance_violations, contract)

    computed_at = datetime.now(timezone.utc).isoformat()

    report = DriftReport(
        candidate_id=fingerprint.candidate_id,
        run_id=fingerprint.run_id,
        baseline_run_id=baseline.run_id,
        exact_violations=exact_violations,
        tolerance_violations=tolerance_violations,
        severity=severity,
        computed_at=computed_at,
    )

    logger.info(
        "diff.complete",
        candidate_id=fingerprint.candidate_id,
        severity=severity,
        exact_violations=len(exact_violations),
        tolerance_violations=len(tolerance_violations),
    )

    return report


def _check_exact_violations(
    fingerprint: ScoringFingerprint,
    baseline: ScoringFingerprint,
) -> list[DriftViolation]:
    """
    Check exact-match fields for violations.

    Compares top_picks ordering and IDs. Any difference is a violation.

    Contract: NUTRIENTS.md §I.2 (Exact-Match Fields)
    """
    violations: list[DriftViolation] = []

    current_picks = fingerprint.exact_fields.top_picks
    baseline_picks = baseline.exact_fields.top_picks

    # Check count mismatch
    if len(current_picks) != len(baseline_picks):
        violations.append(
            DriftViolation(
                field="exact_fields.top_picks.count",
                baseline_value=len(baseline_picks),
                current_value=len(current_picks),
                delta_pct=None,
            )
        )

    # Check each position for match
    min_len = min(len(current_picks), len(baseline_picks))
    for i in range(min_len):
        current = current_picks[i]
        baseline_pick = baseline_picks[i]

        # Check job_id match
        if current.job_id != baseline_pick.job_id:
            violations.append(
                DriftViolation(
                    field=f"exact_fields.top_picks[{i}].job_id",
                    baseline_value=baseline_pick.job_id,
                    current_value=current.job_id,
                    delta_pct=None,
                )
            )

        # Check source match
        if current.source != baseline_pick.source:
            violations.append(
                DriftViolation(
                    field=f"exact_fields.top_picks[{i}].source",
                    baseline_value=baseline_pick.source,
                    current_value=current.source,
                    delta_pct=None,
                )
            )

        # Check url match
        if current.url != baseline_pick.url:
            violations.append(
                DriftViolation(
                    field=f"exact_fields.top_picks[{i}].url",
                    baseline_value=baseline_pick.url,
                    current_value=current.url,
                    delta_pct=None,
                )
            )

        # Check position match (should always match by index, but verify)
        if current.position != baseline_pick.position:
            violations.append(
                DriftViolation(
                    field=f"exact_fields.top_picks[{i}].position",
                    baseline_value=baseline_pick.position,
                    current_value=current.position,
                    delta_pct=None,
                )
            )

    # Report any extra picks beyond baseline
    for i in range(min_len, len(current_picks)):
        violations.append(
            DriftViolation(
                field=f"exact_fields.top_picks[{i}]",
                baseline_value=None,
                current_value=_pick_to_dict(current_picks[i]),
                delta_pct=None,
            )
        )

    # Report any missing picks from baseline
    for i in range(min_len, len(baseline_picks)):
        violations.append(
            DriftViolation(
                field=f"exact_fields.top_picks[{i}]",
                baseline_value=_pick_to_dict(baseline_picks[i]),
                current_value=None,
                delta_pct=None,
            )
        )

    return violations


def _pick_to_dict(pick: TopPickFingerprint) -> dict:
    """Convert a TopPickFingerprint to a dict for violation reporting."""
    return {
        "job_id": pick.job_id,
        "source": pick.source,
        "url": pick.url,
        "position": pick.position,
    }


def _check_tolerance_violations(
    fingerprint: ScoringFingerprint,
    baseline: ScoringFingerprint,
    contract: FingerprintContract,
) -> list[DriftViolation]:
    """
    Check tolerance-match fields for violations.

    Compares score dimensions against tolerance thresholds.
    Only drift exceeding the tolerance ratio is a violation.

    Contract: NUTRIENTS.md §I.2 (Tolerance-Match Fields)
    """
    violations: list[DriftViolation] = []

    # Map of field names to (current_value, baseline_value, tolerance)
    fields_to_check = [
        (
            "tolerance_fields.technical_match",
            fingerprint.tolerance_fields.technical_match.value,
            baseline.tolerance_fields.technical_match.value,
            TOLERANCE_THRESHOLDS["technical_match"].tolerance,
        ),
        (
            "tolerance_fields.level_match",
            fingerprint.tolerance_fields.level_match.value,
            baseline.tolerance_fields.level_match.value,
            TOLERANCE_THRESHOLDS["level_match"].tolerance,
        ),
        (
            "tolerance_fields.culture_match",
            fingerprint.tolerance_fields.culture_match.value,
            baseline.tolerance_fields.culture_match.value,
            TOLERANCE_THRESHOLDS["culture_match"].tolerance,
        ),
        (
            "tolerance_fields.industry_match",
            fingerprint.tolerance_fields.industry_match.value,
            baseline.tolerance_fields.industry_match.value,
            TOLERANCE_THRESHOLDS["industry_match"].tolerance,
        ),
        (
            "tolerance_fields.growth_potential",
            fingerprint.tolerance_fields.growth_potential.value,
            baseline.tolerance_fields.growth_potential.value,
            TOLERANCE_THRESHOLDS["growth_potential"].tolerance,
        ),
        (
            "tolerance_fields.compensation_match",
            fingerprint.tolerance_fields.compensation_match.value,
            baseline.tolerance_fields.compensation_match.value,
            TOLERANCE_THRESHOLDS["compensation_match"].tolerance,
        ),
        (
            "tolerance_fields.composite_score",
            fingerprint.tolerance_fields.composite_score.value,
            baseline.tolerance_fields.composite_score.value,
            TOLERANCE_THRESHOLDS["composite_score"].tolerance,
        ),
        (
            "tolerance_fields.total_jobs_discovered",
            fingerprint.tolerance_fields.total_jobs_discovered.value,
            baseline.tolerance_fields.total_jobs_discovered.value,
            TOLERANCE_THRESHOLDS["total_jobs_discovered"].tolerance,
        ),
    ]

    for field_name, current_val, baseline_val, tolerance in fields_to_check:
        violation = _check_single_tolerance(
            field_name,
            current_val,
            baseline_val,
            tolerance,
        )
        if violation is not None:
            violations.append(violation)

    return violations


def _check_single_tolerance(
    field: str,
    current_value: float,
    baseline_value: float,
    tolerance: float,
) -> Optional[DriftViolation]:
    """
    Check a single tolerance field for drift violation.

    Args:
        field: Field path for violation reporting
        current_value: Current fingerprint value
        baseline_value: Baseline fingerprint value
        tolerance: Allowed tolerance as ratio (0.05 = ±5%)

    Returns:
        DriftViolation if exceeded, None otherwise
    """
    # Handle edge case of zero baseline
    if baseline_value == 0:
        # If baseline is 0 and current is not, that's significant drift
        if current_value != 0:
            return DriftViolation(
                field=field,
                baseline_value=baseline_value,
                current_value=current_value,
                delta_pct=None,  # Can't compute % from zero
            )
        return None

    # Compute drift percentage
    delta_pct = abs((current_value - baseline_value) / baseline_value)
    delta_pct_rounded = round(delta_pct, 4)

    # Check if drift exceeds tolerance
    if delta_pct > tolerance:
        return DriftViolation(
            field=field,
            baseline_value=baseline_value,
            current_value=current_value,
            delta_pct=delta_pct_rounded,
        )

    return None


def _compute_severity(
    exact_violations: list[DriftViolation],
    tolerance_violations: list[DriftViolation],
    contract: FingerprintContract,
) -> DriftSeverity:
    """
    Compute overall severity from violations.

    Severity rules (NUTRIENTS.md §I.4):
        - green: zero violations
        - yellow: tolerance violations only, no exact-match violations
        - red: any exact-match violation OR tolerance violation > 2× threshold

    Args:
        exact_violations: List of exact-match violations
        tolerance_violations: List of tolerance violations
        contract: FingerprintContract with tolerance thresholds

    Returns:
        DriftSeverity level
    """
    # Green: no violations at all
    if not exact_violations and not tolerance_violations:
        return "green"

    # Red: any exact-match violation
    if exact_violations:
        logger.warning(
            "diff.severity_red_exact",
            exact_count=len(exact_violations),
            fields=[v.field for v in exact_violations[:3]],  # Log first 3
        )
        return "red"

    # Check if any tolerance violation exceeds 2× threshold
    for violation in tolerance_violations:
        field_name = violation.field.replace("tolerance_fields.", "")
        tolerance = TOLERANCE_THRESHOLDS.get(field_name)

        if tolerance is not None and violation.delta_pct is not None:
            # Red if drift > 2× tolerance
            if violation.delta_pct > (tolerance.tolerance * 2):
                logger.warning(
                    "diff.severity_red_tolerance",
                    field=violation.field,
                    delta_pct=violation.delta_pct,
                    threshold=tolerance.tolerance,
                    exceeded_2x=True,
                )
                return "red"

    # Yellow: tolerance violations only, none exceeding 2× threshold
    logger.info(
        "diff.severity_yellow",
        tolerance_count=len(tolerance_violations),
    )
    return "yellow"


# ─── Convenience Functions ───────────────────────────────────────────────────


def has_drift(report: DriftReport) -> bool:
    """
    Check if a drift report contains any violations.

    Args:
        report: DriftReport to check

    Returns:
        True if any violations present (severity != green)
    """
    return report.severity != "green"


def is_critical(report: DriftReport) -> bool:
    """
    Check if a drift report has critical (red) severity.

    Args:
        report: DriftReport to check

    Returns:
        True if severity is red
    """
    return report.severity == "red"


def format_summary(report: DriftReport) -> str:
    """
    Format a human-readable summary of the drift report.

    Args:
        report: DriftReport to summarize

    Returns:
        Multi-line string summary
    """
    lines = [
        f"Drift Report for {report.candidate_id}",
        f"  Run: {report.run_id}",
        f"  Baseline: {report.baseline_run_id}",
        f"  Severity: {report.severity.upper()}",
        f"  Computed: {report.computed_at}",
        "",
    ]

    if report.exact_violations:
        lines.append(f"Exact-Match Violations ({len(report.exact_violations)}):")
        for v in report.exact_violations:
            lines.append(f"  - {v.field}: {v.baseline_value} -> {v.current_value}")
        lines.append("")

    if report.tolerance_violations:
        lines.append(f"Tolerance Violations ({len(report.tolerance_violations)}):")
        for v in report.tolerance_violations:
            pct = f" ({v.delta_pct*100:.1f}%)" if v.delta_pct else ""
            lines.append(
                f"  - {v.field}: {v.baseline_value} -> {v.current_value}{pct}"
            )
        lines.append("")

    if not report.exact_violations and not report.tolerance_violations:
        lines.append("No violations detected.")

    return "\n".join(lines)
