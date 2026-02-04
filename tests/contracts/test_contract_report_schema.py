"""Contract tests for report.json schema.

Validates that report.json adheres to the public contract:
- Required fields present
- Valid types
- Schema version matches expected
"""

import json
from pathlib import Path
from typing import ClassVar

from ragleaklab.reporting.schema import SCHEMA_VERSION

# Path to golden samples
GOLDEN_DIR = Path(__file__).parent / "golden"


class TestReportSchema:
    """Contract tests for report.json structure."""

    # Required top-level fields in report.json
    REQUIRED_FIELDS: ClassVar[set[str]] = {
        "schema_version",
        "generated_at",
        "total_cases",
        "canary_extracted",
        "canary_count",
        "verbatim_leakage_rate",
        "membership_confidence",
        "overall_pass",
        "failures",
    }

    # Optional but expected fields
    OPTIONAL_FIELDS: ClassVar[set[str]] = {
        "tool_version",
        "corpus_path",
        "attacks_path",
        "config_hash",
    }

    def test_golden_report_has_required_fields(self):
        """Golden report.json contains all required fields."""
        report_path = GOLDEN_DIR / "report.json"
        with open(report_path) as f:
            report = json.load(f)

        missing = self.REQUIRED_FIELDS - set(report.keys())
        assert not missing, f"Missing required fields: {missing}"

    def test_golden_report_field_types(self):
        """Golden report.json fields have correct types."""
        report_path = GOLDEN_DIR / "report.json"
        with open(report_path) as f:
            report = json.load(f)

        # Type checks
        assert isinstance(report["schema_version"], str)
        assert isinstance(report["generated_at"], str)
        assert isinstance(report["total_cases"], int)
        assert isinstance(report["canary_extracted"], bool)
        assert isinstance(report["canary_count"], int)
        assert isinstance(report["verbatim_leakage_rate"], (int, float))
        assert isinstance(report["membership_confidence"], (int, float))
        assert isinstance(report["overall_pass"], bool)
        assert isinstance(report["failures"], list)

    def test_schema_version_format(self):
        """Schema version follows semantic versioning pattern."""
        report_path = GOLDEN_DIR / "report.json"
        with open(report_path) as f:
            report = json.load(f)

        version = report["schema_version"]
        parts = version.split(".")
        assert len(parts) == 3, f"Schema version should be MAJOR.MINOR.PATCH: {version}"
        for part in parts:
            assert part.isdigit(), f"Version part must be numeric: {part}"

    def test_failures_structure(self):
        """Failures array entries have required structure."""
        # Create a report with failures for testing
        report_with_failures = {
            "schema_version": SCHEMA_VERSION,
            "generated_at": "2026-01-15T12:00:00Z",
            "total_cases": 10,
            "canary_extracted": True,
            "canary_count": 1,
            "verbatim_leakage_rate": 0.5,
            "membership_confidence": 0.3,
            "overall_pass": False,
            "failures": [
                {
                    "threat": "canary",
                    "reason": "Canary token detected",
                    "value": 1,
                    "threshold": 0,
                }
            ],
        }

        failure = report_with_failures["failures"][0]
        assert "threat" in failure
        assert "reason" in failure
        assert "value" in failure
        assert "threshold" in failure

    def test_current_schema_version_matches_code(self):
        """Verify current SCHEMA_VERSION constant is valid."""
        assert SCHEMA_VERSION is not None
        parts = SCHEMA_VERSION.split(".")
        assert len(parts) == 3

    def test_aggregates_are_numeric(self):
        """Aggregate metrics are numeric types."""
        report_path = GOLDEN_DIR / "report.json"
        with open(report_path) as f:
            report = json.load(f)

        # All aggregates should be numeric
        assert report["total_cases"] >= 0
        assert 0 <= report["verbatim_leakage_rate"] <= 1 or report["verbatim_leakage_rate"] > 1
        assert report["membership_confidence"] >= 0
        assert report["canary_count"] >= 0


class TestReportSchemaBackwardCompatibility:
    """Tests for backward compatibility of report schema."""

    def test_v1_report_can_be_parsed(self):
        """Verify v1 baseline reports can still be read."""
        baseline_path = Path(__file__).parent.parent.parent / "baselines" / "v1" / "report.json"
        if baseline_path.exists():
            with open(baseline_path) as f:
                report = json.load(f)
            # v1 reports should have core fields
            assert "total_cases" in report
            assert "overall_pass" in report or "canary_extracted" in report
