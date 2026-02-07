"""Tests for the suppression mechanism.

Covers:
- Schema validation (required fields, blank reason, types)
- Loader (YAML parsing, error handling)
- Validator (expired suppressions, blank reasons)
- Applier (case matching, failure matching, verdict changes)
- Export annotations (JUnit skipped, SARIF suppressions)
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
import yaml

from ragleaklab.suppressions.applier import (
    apply_suppressions_to_case,
    apply_suppressions_to_failures,
    build_suppression_summary,
)
from ragleaklab.suppressions.loader import (
    SuppressionError,
    load_suppressions,
    matches_suppression,
    validate_suppressions,
)
from ragleaklab.suppressions.schema import (
    Suppression,
    SuppressionFile,
    SuppressionType,
)

# ── Helpers ──────────────────────────────────────────────────────────

NOW = datetime(2026, 2, 8, 0, 0, 0, tzinfo=UTC)
FUTURE = NOW + timedelta(days=30)
PAST = NOW - timedelta(days=1)


def _make_suppression(
    *,
    sup_id: str = "550e8400-e29b-41d4-a716-446655440000",
    sup_type: str = "test_id",
    value: str = "canary-basic-001",
    reason: str = "Known false positive in test fixtures",
    expires_at: datetime = FUTURE,
    owner: str | None = "security-team",
) -> dict:
    """Build a suppression dict for YAML."""
    return {
        "id": sup_id,
        "type": sup_type,
        "value": value,
        "reason": reason,
        "expires_at": expires_at.isoformat(),
        "owner": owner,
    }


def _write_yaml(path: Path, data: dict) -> Path:
    path.write_text(yaml.dump(data, default_flow_style=False))
    return path


# ── Schema Tests ─────────────────────────────────────────────────────


class TestSuppressionSchema:
    """Test Pydantic schema validation."""

    def test_valid_suppression(self):
        s = Suppression(
            id="abc",
            type=SuppressionType.test_id,
            value="canary-001",
            reason="Known issue",
            expires_at=FUTURE,
        )
        assert s.reason == "Known issue"
        assert s.type == SuppressionType.test_id

    def test_blank_reason_rejected(self):
        with pytest.raises(ValueError, match="blank"):
            Suppression(
                id="abc",
                type=SuppressionType.test_id,
                value="canary-001",
                reason="   ",
                expires_at=FUTURE,
            )

    def test_all_types(self):
        for t in SuppressionType:
            s = Suppression(id="x", type=t, value="v", reason="r", expires_at=FUTURE)
            assert s.type == t

    def test_optional_owner(self):
        s = Suppression(
            id="x",
            type=SuppressionType.metric,
            value="canary",
            reason="test",
            expires_at=FUTURE,
        )
        assert s.owner is None

    def test_suppression_file_version(self):
        sf = SuppressionFile(suppressions=[])
        assert sf.version == "1.0.0"


# ── Loader Tests ─────────────────────────────────────────────────────


class TestLoader:
    """Test YAML loading and parsing."""

    def test_load_valid_file(self, tmp_path: Path):
        data = {
            "version": "1.0.0",
            "suppressions": [_make_suppression()],
        }
        path = _write_yaml(tmp_path / "suppressions.yaml", data)
        result = load_suppressions(path)
        assert len(result.suppressions) == 1
        assert result.suppressions[0].value == "canary-basic-001"

    def test_load_empty_file(self, tmp_path: Path):
        path = _write_yaml(tmp_path / "suppressions.yaml", {})
        result = load_suppressions(path)
        assert len(result.suppressions) == 0

    def test_file_not_found(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_suppressions(tmp_path / "does-not-exist.yaml")

    def test_invalid_yaml(self, tmp_path: Path):
        path = tmp_path / "bad.yaml"
        path.write_text("{{{{ invalid yaml ::::")
        # yaml.safe_load might parse oddly but Pydantic should reject
        # Alternatively the YAML might error
        with pytest.raises((SuppressionError, Exception)):
            load_suppressions(path)

    def test_invalid_schema(self, tmp_path: Path):
        data = {"version": "1.0.0", "suppressions": [{"id": "x"}]}
        path = _write_yaml(tmp_path / "bad.yaml", data)
        with pytest.raises(SuppressionError):
            load_suppressions(path)


# ── Validator Tests ──────────────────────────────────────────────────


class TestValidator:
    """Test CI gating validation."""

    def test_valid_suppression_no_errors(self):
        sf = SuppressionFile(
            suppressions=[
                Suppression(
                    id="x",
                    type=SuppressionType.test_id,
                    value="t-1",
                    reason="ok",
                    expires_at=FUTURE,
                )
            ]
        )
        errors = validate_suppressions(sf, now=NOW)
        assert errors == []

    def test_expired_suppression_fails(self):
        sf = SuppressionFile(
            suppressions=[
                Suppression(
                    id="expired-1",
                    type=SuppressionType.test_id,
                    value="t-1",
                    reason="was valid",
                    expires_at=PAST,
                )
            ]
        )
        errors = validate_suppressions(sf, now=NOW)
        assert len(errors) == 1
        assert "expired" in errors[0].lower()
        assert "expired-1" in errors[0]

    def test_multiple_errors(self):
        sf = SuppressionFile(
            suppressions=[
                Suppression(
                    id="e1",
                    type=SuppressionType.test_id,
                    value="t-1",
                    reason="ok",
                    expires_at=PAST,
                ),
                Suppression(
                    id="e2",
                    type=SuppressionType.metric,
                    value="canary",
                    reason="ok",
                    expires_at=PAST,
                ),
            ]
        )
        errors = validate_suppressions(sf, now=NOW)
        assert len(errors) == 2


# ── Matcher Tests ────────────────────────────────────────────────────


class TestMatcher:
    """Test suppression matching logic."""

    def test_match_test_id(self):
        s = Suppression(
            id="x",
            type=SuppressionType.test_id,
            value="t-1",
            reason="r",
            expires_at=FUTURE,
        )
        assert matches_suppression(s, test_id="t-1")
        assert not matches_suppression(s, test_id="t-2")

    def test_match_metric(self):
        s = Suppression(
            id="x",
            type=SuppressionType.metric,
            value="canary",
            reason="r",
            expires_at=FUTURE,
        )
        assert matches_suppression(s, metric="canary")
        assert not matches_suppression(s, metric="verbatim")

    def test_match_doc_id(self):
        s = Suppression(
            id="x",
            type=SuppressionType.doc_id,
            value="doc-42",
            reason="r",
            expires_at=FUTURE,
        )
        assert matches_suppression(s, doc_id="doc-42")
        assert not matches_suppression(s, doc_id="doc-99")

    def test_match_claim_id(self):
        s = Suppression(
            id="x",
            type=SuppressionType.claim_id,
            value="claim-1",
            reason="r",
            expires_at=FUTURE,
        )
        assert matches_suppression(s, claim_id="claim-1")

    def test_no_match_wrong_type(self):
        s = Suppression(
            id="x",
            type=SuppressionType.test_id,
            value="t-1",
            reason="r",
            expires_at=FUTURE,
        )
        # test_id suppression doesn't match metric
        assert not matches_suppression(s, metric="t-1")


# ── Applier Tests ────────────────────────────────────────────────────


class TestApplier:
    """Test suppression application to findings."""

    def test_suppress_case_by_test_id(self):
        sup = Suppression(
            id="s1",
            type=SuppressionType.test_id,
            value="canary-001",
            reason="False positive",
            expires_at=FUTURE,
        )
        case = {"test_id": "canary-001", "canary_detected": True}
        is_suppressed, record = apply_suppressions_to_case(case, [sup], now=NOW)
        assert is_suppressed
        assert record is not None
        assert record.suppression_id == "s1"

    def test_no_match_case(self):
        sup = Suppression(
            id="s1",
            type=SuppressionType.test_id,
            value="canary-999",
            reason="Something",
            expires_at=FUTURE,
        )
        case = {"test_id": "canary-001"}
        is_suppressed, record = apply_suppressions_to_case(case, [sup], now=NOW)
        assert not is_suppressed
        assert record is None

    def test_expired_suppression_not_applied(self):
        sup = Suppression(
            id="s1",
            type=SuppressionType.test_id,
            value="canary-001",
            reason="Was valid",
            expires_at=PAST,
        )
        case = {"test_id": "canary-001"}
        is_suppressed, _record = apply_suppressions_to_case(case, [sup], now=NOW)
        assert not is_suppressed

    def test_suppress_metric_failure(self):
        sup = Suppression(
            id="s1",
            type=SuppressionType.metric,
            value="canary",
            reason="Fix in progress",
            expires_at=FUTURE,
        )
        failures = [
            {"threat": "canary", "reason": "Canary detected", "value": 1, "threshold": 0},
            {"threat": "verbatim", "reason": "High overlap", "value": 0.5, "threshold": 0.1},
        ]
        remaining, applied = apply_suppressions_to_failures(failures, [sup], now=NOW)
        assert len(remaining) == 1
        assert remaining[0]["threat"] == "verbatim"
        assert len(applied) == 1
        assert applied[0].value == "canary"

    def test_suppress_all_failures_changes_verdict(self):
        """If all failures are suppressed, effective verdict becomes pass."""
        sup = Suppression(
            id="s1",
            type=SuppressionType.metric,
            value="canary",
            reason="Fix coming",
            expires_at=FUTURE,
        )
        failures = [
            {"threat": "canary", "reason": "Canary", "value": 1, "threshold": 0},
        ]
        remaining, applied = apply_suppressions_to_failures(failures, [sup], now=NOW)
        assert len(remaining) == 0
        assert len(applied) == 1

        # Build summary
        sf = SuppressionFile(suppressions=[sup])
        summary = build_suppression_summary(sf, applied, "fail", "pass", now=NOW)
        assert summary.verdict_changed
        assert summary.original_verdict == "fail"
        assert summary.effective_verdict == "pass"
        assert summary.applied_suppressions == 1


class TestSuppressionSummary:
    """Test summary building."""

    def test_summary_counts(self):
        sf = SuppressionFile(
            suppressions=[
                Suppression(
                    id="active",
                    type=SuppressionType.test_id,
                    value="t-1",
                    reason="ok",
                    expires_at=FUTURE,
                ),
            ]
        )
        summary = build_suppression_summary(sf, [], "pass", "pass", now=NOW)
        assert summary.total_suppressions_loaded == 1
        assert summary.active_suppressions == 1
        assert summary.applied_suppressions == 0
        assert not summary.verdict_changed


# ── JUnit Export Suppression Tests ───────────────────────────────────


class TestJUnitSuppression:
    """Test that JUnit export annotates suppressed findings."""

    def test_suppressed_case_has_skipped_element(self, tmp_path: Path):
        from ragleaklab.reporting.export import export_junit
        from ragleaklab.reporting.schema import CaseResult, Report
        from ragleaklab.suppressions.applier import (
            AppliedSuppression,
            SuppressionSummary,
        )

        report = Report(
            total_cases=1,
            canary_extracted=True,
            canary_count=1,
            verbatim_leakage_rate=0.0,
            membership_confidence=0.0,
            overall_pass=True,  # suppressed verdict
            failures=[],
            corpus_path="/tmp/corpus",
            attacks_path="/tmp/attacks",
        )
        cases = [
            CaseResult(
                test_id="canary-001",
                threat="canary",
                query="test",
                transformed_query="test",
                retrieved_ids=[],
                answer="leaked",
                canary_detected=True,
                canary_count=1,
            )
        ]
        summary = SuppressionSummary(
            total_suppressions_loaded=1,
            active_suppressions=1,
            applied_suppressions=1,
            suppressed_findings=[
                AppliedSuppression(
                    suppression_id="s1",
                    type="test_id",
                    value="canary-001",
                    reason="False positive",
                    expires_at="2026-04-01T00:00:00+00:00",
                )
            ],
            verdict_changed=True,
            original_verdict="fail",
            effective_verdict="pass",
        )

        out_path = tmp_path / "junit.xml"
        export_junit(report, cases, out_path, suppression_summary=summary)

        tree = ET.parse(out_path)
        root = tree.getroot()

        # Find the testcase for canary-001
        testcases = root.findall(".//testcase")
        canary_case = None
        for tc in testcases:
            if "canary-001" in tc.get("name", ""):
                canary_case = tc
                break

        assert canary_case is not None
        # Should have <skipped> not <failure>
        skipped = canary_case.find("skipped")
        assert skipped is not None
        assert "SUPPRESSED" in skipped.get("message", "")
        # Should not have <failure>
        failure = canary_case.find("failure")
        assert failure is None


# ── SARIF Export Suppression Tests ───────────────────────────────────


class TestSARIFSuppression:
    """Test that SARIF export annotates suppressed findings."""

    def test_suppressed_finding_has_suppressions_array(self, tmp_path: Path):
        from ragleaklab.reporting.export import export_sarif
        from ragleaklab.reporting.schema import CaseResult, Report
        from ragleaklab.suppressions.applier import (
            AppliedSuppression,
            SuppressionSummary,
        )

        report = Report(
            total_cases=1,
            canary_extracted=True,
            canary_count=1,
            verbatim_leakage_rate=0.0,
            membership_confidence=0.0,
            overall_pass=True,
            failures=[],
            corpus_path="/tmp/corpus",
            attacks_path="/tmp/attacks",
        )
        cases = [
            CaseResult(
                test_id="canary-001",
                threat="canary",
                query="test",
                transformed_query="test",
                retrieved_ids=[],
                answer="leaked",
                canary_detected=True,
                canary_count=1,
            )
        ]
        summary = SuppressionSummary(
            total_suppressions_loaded=1,
            active_suppressions=1,
            applied_suppressions=1,
            suppressed_findings=[
                AppliedSuppression(
                    suppression_id="s1",
                    type="test_id",
                    value="canary-001",
                    reason="Known issue",
                    expires_at="2026-04-01T00:00:00+00:00",
                )
            ],
        )

        out_path = tmp_path / "results.sarif"
        export_sarif(report, cases, out_path, suppression_summary=summary)

        sarif = json.loads(out_path.read_text())
        results = sarif["runs"][0]["results"]

        # Find the canary result
        canary_results = [r for r in results if r["ruleId"] == "canary-extraction"]
        assert len(canary_results) == 1
        result = canary_results[0]

        # Should have suppressions array
        assert "suppressions" in result
        assert len(result["suppressions"]) == 1
        assert result["suppressions"][0]["kind"] == "inSource"
        assert result["suppressions"][0]["status"] == "accepted"
        assert "Known issue" in result["suppressions"][0]["justification"]

    def test_non_suppressed_finding_no_suppressions(self, tmp_path: Path):
        from ragleaklab.reporting.export import export_sarif
        from ragleaklab.reporting.schema import CaseResult, Report

        report = Report(
            total_cases=1,
            canary_extracted=True,
            canary_count=1,
            verbatim_leakage_rate=0.0,
            membership_confidence=0.0,
            overall_pass=False,
            failures=[],
            corpus_path="/tmp/corpus",
            attacks_path="/tmp/attacks",
        )
        cases = [
            CaseResult(
                test_id="canary-001",
                threat="canary",
                query="test",
                transformed_query="test",
                retrieved_ids=[],
                answer="leaked",
                canary_detected=True,
                canary_count=1,
            )
        ]

        out_path = tmp_path / "results.sarif"
        export_sarif(report, cases, out_path)  # No suppression_summary

        sarif = json.loads(out_path.read_text())
        results = sarif["runs"][0]["results"]
        canary_results = [r for r in results if r["ruleId"] == "canary-extraction"]
        assert len(canary_results) == 1
        # Should NOT have suppressions
        assert "suppressions" not in canary_results[0]
