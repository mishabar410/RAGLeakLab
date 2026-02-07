"""Tests for reporting/export.py (JUnit and SARIF export)."""

import json
from xml.etree import ElementTree as ET

from ragleaklab.reporting.export import (
    _build_integrity_message,
    _get_evidence_type,
    _get_junit_evidence_type,
    _integrity_evidence_to_rule_id,
    _threat_to_rule_id,
    export_junit,
    export_sarif,
)
from ragleaklab.reporting.schema import CaseResult, FailureReason, Report


def _make_report(**overrides) -> Report:
    defaults = {
        "total_cases": 2,
        "canary_extracted": False,
        "canary_count": 0,
        "verbatim_leakage_rate": 0.0,
        "membership_confidence": 0.0,
        "overall_pass": True,
        "failures": [],
        "corpus_path": "data/corpus",
        "attacks_path": "data/attacks",
    }
    defaults.update(overrides)
    return Report(**defaults)


def _make_case(**overrides) -> CaseResult:
    defaults = {
        "test_id": "t1",
        "threat": "canary",
        "query": "test query",
        "transformed_query": "test query",
        "retrieved_ids": ["doc1:0"],
        "answer": "test answer",
    }
    defaults.update(overrides)
    return CaseResult(**defaults)


# ── JUnit tests ──────────────────────────────────────────────────────


class TestExportJunit:
    """Tests for JUnit XML export."""

    def test_basic_export(self, tmp_path):
        report = _make_report()
        cases = [_make_case()]
        out = tmp_path / "junit.xml"
        export_junit(report, cases, out)
        assert out.exists()
        tree = ET.parse(out)
        root = tree.getroot()
        assert root.tag == "testsuite"
        assert root.get("name") == "RAGLeakLab Security Audit"

    def test_canary_detection_failure(self, tmp_path):
        report = _make_report()
        cases = [_make_case(canary_detected=True, canary_count=3)]
        out = tmp_path / "junit.xml"
        export_junit(report, cases, out)
        tree = ET.parse(out)
        failures = tree.findall(".//failure")
        assert len(failures) >= 1
        assert "Canary extracted" in failures[0].get("message")

    def test_verbatim_failure(self, tmp_path):
        report = _make_report()
        cases = [_make_case(verbatim_score=0.5)]
        out = tmp_path / "junit.xml"
        export_junit(report, cases, out)
        tree = ET.parse(out)
        failures = tree.findall(".//failure")
        assert any("verbatim" in f.get("message", "").lower() for f in failures)

    def test_aggregate_failures(self, tmp_path):
        report = _make_report(
            failures=[
                FailureReason(
                    threat="canary", reason="Canary leaked", value=True, threshold=False
                )
            ]
        )
        out = tmp_path / "junit.xml"
        export_junit(report, [], out)
        tree = ET.parse(out)
        root = tree.getroot()
        assert int(root.get("failures")) >= 1

    def test_integrity_findings_high(self, tmp_path):
        report = _make_report(
            integrity={
                "packs": [
                    {
                        "pack_id": "hijack-pack",
                        "query_id": "q1",
                        "severity": "high",
                        "expected_doc_ids": ["d1"],
                        "actual_doc_ids": ["d2"],
                    }
                ]
            }
        )
        out = tmp_path / "junit.xml"
        export_junit(report, [], out)
        tree = ET.parse(out)
        failures = tree.findall(".//failure")
        assert len(failures) >= 1

    def test_integrity_findings_medium(self, tmp_path):
        """Medium severity should not be a failure."""
        report = _make_report(
            integrity={
                "packs": [
                    {
                        "pack_id": "pack",
                        "query_id": "q1",
                        "severity": "medium",
                        "triggered": False,
                    }
                ]
            }
        )
        out = tmp_path / "junit.xml"
        export_junit(report, [], out)
        tree = ET.parse(out)
        # test_count includes the integrity finding
        root = tree.getroot()
        assert int(root.get("tests")) >= 1
        assert int(root.get("failures")) == 0


# ── SARIF tests ──────────────────────────────────────────────────────


class TestExportSarif:
    """Tests for SARIF JSON export."""

    def test_basic_structure(self, tmp_path):
        report = _make_report()
        out = tmp_path / "sarif.json"
        export_sarif(report, [], out)
        data = json.loads(out.read_text())
        assert data["version"] == "2.1.0"
        assert len(data["runs"]) == 1
        assert data["runs"][0]["tool"]["driver"]["name"] == "RAGLeakLab"

    def test_sarif_rules_present(self, tmp_path):
        report = _make_report()
        out = tmp_path / "sarif.json"
        export_sarif(report, [], out)
        data = json.loads(out.read_text())
        rules = data["runs"][0]["tool"]["driver"]["rules"]
        rule_ids = {r["id"] for r in rules}
        assert "canary-extraction" in rule_ids
        assert "verbatim-leakage" in rule_ids
        assert "RAGLEAKLAB-INTEGRITY-RETRIEVAL-HIJACK" in rule_ids

    def test_sarif_with_canary(self, tmp_path):
        report = _make_report()
        cases = [_make_case(canary_detected=True, canary_count=2)]
        out = tmp_path / "sarif.json"
        export_sarif(report, cases, out)
        data = json.loads(out.read_text())
        results = data["runs"][0]["results"]
        assert any(r["ruleId"] == "canary-extraction" for r in results)

    def test_sarif_with_integrity(self, tmp_path):
        report = _make_report(
            integrity={
                "packs": [
                    {
                        "pack_id": "hijack",
                        "query_id": "q1",
                        "severity": "high",
                        "expected_doc_ids": ["d1"],
                    }
                ]
            }
        )
        out = tmp_path / "sarif.json"
        export_sarif(report, [], out)
        data = json.loads(out.read_text())
        results = data["runs"][0]["results"]
        assert any("INTEGRITY" in r["ruleId"] for r in results)


# ── Helper function tests ────────────────────────────────────────────


class TestHelperFunctions:
    """Tests for export helper functions."""

    def test_threat_to_rule_id(self):
        assert _threat_to_rule_id("canary") == "canary-extraction"
        assert _threat_to_rule_id("verbatim") == "verbatim-leakage"
        assert _threat_to_rule_id("unknown_threat") == "unknown"

    def test_get_evidence_type_retrieval(self):
        assert _get_evidence_type({"expected_doc_ids": []}) == "RetrievalIntegrityEvidence"

    def test_get_evidence_type_sentinel(self):
        assert _get_evidence_type({"triggered": True}) == "SentinelIntegrityEvidence"

    def test_get_evidence_type_claim(self):
        assert (
            _get_evidence_type({"matched_poison_claims": []}) == "ClaimIntegrityEvidence"
        )

    def test_get_evidence_type_unknown(self):
        assert _get_evidence_type({}) == "unknown"

    def test_get_junit_evidence_type(self):
        assert _get_junit_evidence_type({"expected_doc_ids": []}) == "retrieval-hijack"
        assert _get_junit_evidence_type({"triggered": True}) == "sentinel-takeover"
        assert _get_junit_evidence_type({}) == "unknown"

    def test_integrity_evidence_to_rule_id(self):
        assert (
            _integrity_evidence_to_rule_id("RetrievalIntegrityEvidence")
            == "RAGLEAKLAB-INTEGRITY-RETRIEVAL-HIJACK"
        )
        assert _integrity_evidence_to_rule_id("unknown") == "unknown"

    def test_build_integrity_message_retrieval(self):
        msg = _build_integrity_message(
            "RetrievalIntegrityEvidence",
            {"pack_id": "p", "query_id": "q", "severity": "high"},
        )
        assert "Retrieval hijack" in msg

    def test_build_integrity_message_sentinel_triggered(self):
        msg = _build_integrity_message(
            "SentinelIntegrityEvidence",
            {"pack_id": "p", "query_id": "q", "severity": "high", "triggered": True},
        )
        assert "Sentinel takeover" in msg

    def test_build_integrity_message_sentinel_not_triggered(self):
        msg = _build_integrity_message(
            "SentinelIntegrityEvidence",
            {"pack_id": "p", "query_id": "q", "severity": "low", "triggered": False},
        )
        assert "Sentinel check" in msg

    def test_build_integrity_message_unknown(self):
        msg = _build_integrity_message(
            "unknown",
            {"pack_id": "p", "query_id": "q", "severity": "medium"},
        )
        assert "Integrity finding" in msg
