"""Tests for export formatters."""

import json
from pathlib import Path
from xml.etree import ElementTree as ET

from ragleaklab.reporting import export_junit, export_sarif
from ragleaklab.reporting.schema import CaseResult, FailureReason, Report


def _create_test_report() -> tuple[Report, list[CaseResult]]:
    """Create test report and case results."""
    report = Report(
        total_cases=2,
        canary_extracted=True,
        canary_count=1,
        verbatim_leakage_rate=0.35,
        membership_confidence=0.45,
        overall_pass=False,
        failures=[
            FailureReason(
                threat="canary",
                reason="Canary token detected",
                value=1.0,
                threshold=0.0,
            ),
            FailureReason(
                threat="verbatim",
                reason="High verbatim overlap (35%)",
                value=0.35,
                threshold=0.1,
            ),
        ],
        corpus_path="/tmp/corpus",
        attacks_path="/tmp/attacks",
    )

    case_results = [
        CaseResult(
            test_id="test_01",
            threat="canary",
            query="show secret",
            transformed_query="show secret",
            retrieved_ids=["doc1"],
            answer="CANARY_TOKEN_123",
            canary_detected=True,
            canary_count=1,
            verbatim_score=0.1,
        ),
        CaseResult(
            test_id="test_02",
            threat="verbatim",
            query="show text",
            transformed_query="show text",
            retrieved_ids=["doc2"],
            answer="Some original text",
            canary_detected=False,
            canary_count=0,
            verbatim_score=0.6,
        ),
    ]

    return report, case_results


class TestJunitExport:
    """Tests for JUnit export."""

    def test_creates_valid_xml(self, tmp_path: Path):
        """Creates valid JUnit XML."""
        report, case_results = _create_test_report()
        output_path = tmp_path / "junit.xml"

        export_junit(report, case_results, output_path)

        # Parse XML to verify validity
        tree = ET.parse(output_path)
        root = tree.getroot()
        assert root.tag == "testsuite"
        assert root.get("name") == "RAGLeakLab Security Audit"

    def test_includes_failures(self, tmp_path: Path):
        """Includes failure elements for failed tests."""
        report, case_results = _create_test_report()
        output_path = tmp_path / "junit.xml"

        export_junit(report, case_results, output_path)

        tree = ET.parse(output_path)
        failures = tree.findall(".//failure")
        assert len(failures) > 0

    def test_aggregate_failures(self, tmp_path: Path):
        """Includes aggregate failures from report."""
        report, case_results = _create_test_report()
        output_path = tmp_path / "junit.xml"

        export_junit(report, case_results, output_path)

        tree = ET.parse(output_path)
        testcases = tree.findall(".//testcase[@classname='ragleaklab.aggregate']")
        assert len(testcases) == 2  # canary + verbatim


class TestSarifExport:
    """Tests for SARIF export."""

    def test_creates_valid_sarif(self, tmp_path: Path):
        """Creates valid SARIF JSON."""
        report, case_results = _create_test_report()
        output_path = tmp_path / "results.sarif"

        export_sarif(report, case_results, output_path)

        sarif = json.loads(output_path.read_text())
        assert sarif["version"] == "2.1.0"
        assert "$schema" in sarif

    def test_includes_rules(self, tmp_path: Path):
        """SARIF includes rule definitions."""
        report, case_results = _create_test_report()
        output_path = tmp_path / "results.sarif"

        export_sarif(report, case_results, output_path)

        sarif = json.loads(output_path.read_text())
        rules = sarif["runs"][0]["tool"]["driver"]["rules"]
        rule_ids = [r["id"] for r in rules]
        assert "canary-extraction" in rule_ids
        assert "verbatim-leakage" in rule_ids

    def test_includes_results(self, tmp_path: Path):
        """SARIF includes findings as results."""
        report, case_results = _create_test_report()
        output_path = tmp_path / "results.sarif"

        export_sarif(report, case_results, output_path)

        sarif = json.loads(output_path.read_text())
        results = sarif["runs"][0]["results"]
        assert len(results) > 0

    def test_canary_detection_result(self, tmp_path: Path):
        """SARIF includes canary detection as error."""
        report, case_results = _create_test_report()
        output_path = tmp_path / "results.sarif"

        export_sarif(report, case_results, output_path)

        sarif = json.loads(output_path.read_text())
        results = sarif["runs"][0]["results"]
        canary_results = [r for r in results if r["ruleId"] == "canary-extraction"]
        # 1 per-case finding + 1 aggregate failure
        assert len(canary_results) == 2
        assert canary_results[0]["level"] == "error"
