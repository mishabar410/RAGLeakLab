"""V1 contract tests for report.json required fields.

Ensures that report.json always contains the fields documented in
docs/V1_CONTRACTS.md § A (Report JSON).
"""

import json
from pathlib import Path
from typing import ClassVar

from ragleaklab.reporting.schema import Report

GOLDEN_DIR = Path(__file__).parent / "golden"


class TestReportV1Contract:
    """Enforce V1 report.json required field contract."""

    # Fields required by V1_CONTRACTS.md § A
    V1_REQUIRED_FIELDS: ClassVar[set[str]] = {
        "schema_version",
        "tool_version",
        "generated_at",
        "total_cases",
        "canary_extracted",
        "canary_count",
        "verbatim_leakage_rate",
        "membership_confidence",
        "overall_pass",
        "failures",
        "corpus_path",
        "attacks_path",
        "config_hash",
    }

    def test_golden_report_has_v1_required_fields(self):
        """Golden report.json contains all V1 required fields."""
        report_path = GOLDEN_DIR / "report.json"
        with open(report_path) as f:
            report = json.load(f)

        missing = self.V1_REQUIRED_FIELDS - set(report.keys())
        assert not missing, f"Golden report.json missing V1 required fields: {missing}"

    def test_golden_report_has_schema_version(self):
        """report.json has non-empty schema_version."""
        report_path = GOLDEN_DIR / "report.json"
        with open(report_path) as f:
            report = json.load(f)

        assert report.get("schema_version"), "schema_version must be non-empty"

    def test_golden_report_has_tool_version(self):
        """report.json has tool_version field."""
        report_path = GOLDEN_DIR / "report.json"
        with open(report_path) as f:
            report = json.load(f)

        assert "tool_version" in report, "tool_version must be present"

    def test_golden_report_has_config_hash(self):
        """report.json has config_hash field."""
        report_path = GOLDEN_DIR / "report.json"
        with open(report_path) as f:
            report = json.load(f)

        assert "config_hash" in report, "config_hash must be present"

    def test_report_pydantic_model_has_v1_fields(self):
        """Report pydantic model exposes all V1 contracted fields."""
        model_fields = set(Report.model_fields.keys())
        # V1 contract fields minus 'failures' which is always present in Pydantic
        for field in self.V1_REQUIRED_FIELDS:
            assert field in model_fields, f"Report model missing V1 contract field: {field}"
