# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Tests for the synthetics CLI module.

Verifies:
    - CLI argument parsing
    - Help output generation
    - Suite selection logic
    - Exit codes

These tests run without database/Redis connections by testing
the argument parser and entry point logic only.

Contract: HYPHA-SYNTHETICS-SCORING.md Acceptance Criteria
"""

import pytest
from unittest.mock import patch, AsyncMock

from backend.synthetics.cli import create_parser, main


class TestCreateParser:
    """Tests for the CLI argument parser."""

    def test_parser_creation(self):
        """Parser should be created without errors."""
        parser = create_parser()
        assert parser is not None
        assert parser.prog == "python -m backend.synthetics"

    def test_run_command_requires_suite(self):
        """Run command should require --suite argument."""
        parser = create_parser()

        # Should fail without --suite
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["run"])

        # argparse exits with 2 for errors
        assert exc_info.value.code == 2

    def test_run_command_scoring_suite(self):
        """Run command should accept --suite=scoring."""
        parser = create_parser()
        args = parser.parse_args(["run", "--suite=scoring"])

        assert args.command == "run"
        assert args.suite == "scoring"
        assert args.output_dir is None
        assert args.no_publish is False
        assert args.verbose is False

    def test_run_command_crawler_suite(self):
        """Run command should accept --suite=crawler."""
        parser = create_parser()
        args = parser.parse_args(["run", "--suite=crawler"])

        assert args.command == "run"
        assert args.suite == "crawler"

    def test_run_command_invalid_suite(self):
        """Run command should reject invalid suite values."""
        parser = create_parser()

        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["run", "--suite=invalid"])

        assert exc_info.value.code == 2

    def test_run_command_output_dir(self):
        """Run command should accept --output-dir."""
        parser = create_parser()
        args = parser.parse_args(["run", "--suite=scoring", "--output-dir=/tmp/test"])

        assert args.output_dir == "/tmp/test"

    def test_run_command_no_publish(self):
        """Run command should accept --no-publish flag."""
        parser = create_parser()
        args = parser.parse_args(["run", "--suite=scoring", "--no-publish"])

        assert args.no_publish is True

    def test_run_command_verbose(self):
        """Run command should accept --verbose flag."""
        parser = create_parser()
        args = parser.parse_args(["run", "--suite=scoring", "--verbose"])

        assert args.verbose is True

    def test_run_command_verbose_short(self):
        """Run command should accept -v as shorthand for --verbose."""
        parser = create_parser()
        args = parser.parse_args(["run", "--suite=scoring", "-v"])

        assert args.verbose is True

    def test_run_command_subsequent_run(self):
        """Run command should accept --subsequent-run flag for cache verification."""
        parser = create_parser()
        args = parser.parse_args(["run", "--suite=scoring", "--subsequent-run"])

        assert args.subsequent_run is True

    def test_run_command_subsequent_run_default(self):
        """Run command should default subsequent_run to False."""
        parser = create_parser()
        args = parser.parse_args(["run", "--suite=scoring"])

        assert args.subsequent_run is False


class TestMain:
    """Tests for the main entry point."""

    def test_no_command_shows_help(self):
        """Main should show help and exit 1 when no command given."""
        with patch("sys.argv", ["backend.synthetics"]):
            result = main()

        assert result == 1

    @patch("backend.synthetics.cli.asyncio.run")
    @patch("backend.synthetics.cli.run_scoring_suite")
    def test_run_scoring_calls_runner(self, mock_run_suite, mock_asyncio_run):
        """Main should call run_scoring_suite for --suite=scoring."""
        mock_asyncio_run.return_value = 0

        with patch("sys.argv", ["backend.synthetics", "run", "--suite=scoring"]):
            result = main()

        # asyncio.run should be called with the coroutine
        mock_asyncio_run.assert_called_once()
        assert result == 0

    @patch("sys.argv", ["backend.synthetics", "run", "--suite=crawler"])
    def test_run_crawler_not_implemented(self):
        """Main should return 1 for crawler suite (owned by other agent)."""
        result = main()
        assert result == 1


class TestDiffModule:
    """Tests for the diff module functionality."""

    def test_diff_imports(self):
        """Diff module should export required symbols."""
        from backend.synthetics.diff import (
            DriftReport,
            DriftViolation,
            diff_against_baseline,
            has_drift,
            is_critical,
            format_summary,
        )

        # All imports should succeed
        assert DriftReport is not None
        assert DriftViolation is not None
        assert callable(diff_against_baseline)
        assert callable(has_drift)
        assert callable(is_critical)
        assert callable(format_summary)

    def test_drift_severity_green(self):
        """has_drift should return False for green severity."""
        from backend.synthetics.diff import DriftReport, has_drift

        report = DriftReport(
            candidate_id="test-id",
            run_id="run-1",
            baseline_run_id="run-0",
            exact_violations=[],
            tolerance_violations=[],
            severity="green",
            computed_at="2026-05-28T00:00:00Z",
        )

        assert has_drift(report) is False

    def test_drift_severity_yellow(self):
        """has_drift should return True for yellow severity."""
        from backend.synthetics.diff import DriftReport, DriftViolation, has_drift

        report = DriftReport(
            candidate_id="test-id",
            run_id="run-1",
            baseline_run_id="run-0",
            exact_violations=[],
            tolerance_violations=[
                DriftViolation(
                    field="test_field",
                    baseline_value=70.0,
                    current_value=75.0,
                    delta_pct=0.071,
                )
            ],
            severity="yellow",
            computed_at="2026-05-28T00:00:00Z",
        )

        assert has_drift(report) is True

    def test_drift_severity_red(self):
        """is_critical should return True for red severity."""
        from backend.synthetics.diff import DriftReport, DriftViolation, is_critical

        report = DriftReport(
            candidate_id="test-id",
            run_id="run-1",
            baseline_run_id="run-0",
            exact_violations=[
                DriftViolation(
                    field="exact_fields.top_picks[0].job_id",
                    baseline_value="job-1",
                    current_value="job-2",
                    delta_pct=None,
                )
            ],
            tolerance_violations=[],
            severity="red",
            computed_at="2026-05-28T00:00:00Z",
        )

        assert is_critical(report) is True


class TestFingerprintModule:
    """Tests for the fingerprint module functionality."""

    def test_fingerprint_imports(self):
        """Fingerprint module should export required symbols."""
        from backend.synthetics.fingerprint import (
            ScoringFingerprint,
            FingerprintContract,
            compute_fingerprint,
            load_baseline,
            save_baseline,
        )

        # All imports should succeed
        assert ScoringFingerprint is not None
        assert FingerprintContract is not None
        assert callable(compute_fingerprint)
        assert callable(load_baseline)
        assert callable(save_baseline)


class TestPackageExports:
    """Tests for the package-level exports."""

    def test_package_exports(self):
        """Package should export all required symbols."""
        from backend.synthetics import (
            # Runner
            ScoringSyntheticRunner,
            # Fingerprint
            FingerprintContract,
            ScoringFingerprint,
            compute_fingerprint,
            load_baseline,
            save_baseline,
            # Diff
            DriftReport,
            DriftViolation,
            diff_against_baseline,
            has_drift,
            is_critical,
            format_summary,
        )

        # All imports should succeed
        assert ScoringSyntheticRunner is not None
        assert FingerprintContract is not None
        assert ScoringFingerprint is not None
        assert callable(compute_fingerprint)
        assert callable(load_baseline)
        assert callable(save_baseline)
        assert DriftReport is not None
        assert DriftViolation is not None
        assert callable(diff_against_baseline)
        assert callable(has_drift)
        assert callable(is_critical)
        assert callable(format_summary)
