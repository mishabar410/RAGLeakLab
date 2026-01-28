"""Tests for regression diff."""

from ragleaklab.regression.diff import compare_reports
from ragleaklab.reporting.schema import Report


def _make_report(
    canary_extracted: bool = False,
    verbatim_rate: float = 0.05,
    membership_conf: float = 0.4,
) -> Report:
    """Create a test report with specified values."""
    return Report(
        total_cases=10,
        canary_extracted=canary_extracted,
        canary_count=1 if canary_extracted else 0,
        verbatim_leakage_rate=verbatim_rate,
        membership_confidence=membership_conf,
        overall_pass=not canary_extracted,
        failures=[],
        corpus_path="/test/corpus",
        attacks_path="/test/attacks",
    )


class TestRegressionDiff:
    """Tests for compare_reports function."""

    def test_no_regression_pass(self):
        """No regression when metrics are same or better."""
        baseline = _make_report(canary_extracted=False, verbatim_rate=0.05)
        current = _make_report(canary_extracted=False, verbatim_rate=0.05)

        result = compare_reports(baseline, current)

        assert result.status == "pass"
        assert len(result.reasons) == 0

    def test_canary_regression_fail(self):
        """Fail when canary goes from false to true."""
        baseline = _make_report(canary_extracted=False)
        current = _make_report(canary_extracted=True)

        result = compare_reports(baseline, current)

        assert result.status == "fail"
        assert any("canary" in r.lower() for r in result.reasons)

    def test_canary_both_true_no_regression(self):
        """No canary regression when both baseline and current have canaries."""
        baseline = _make_report(canary_extracted=True)
        current = _make_report(canary_extracted=True)

        result = compare_reports(baseline, current)

        # Canary is not a regression if it was already present
        assert not any("canary" in r.lower() for r in result.reasons)

    def test_verbatim_regression_above_threshold(self):
        """Fail when verbatim rate increases above threshold."""
        baseline = _make_report(verbatim_rate=0.05)
        current = _make_report(verbatim_rate=0.10)  # +0.05 > default 0.01 threshold

        result = compare_reports(baseline, current, verbatim_delta_threshold=0.01)

        assert result.status == "fail"
        assert any("verbatim" in r.lower() for r in result.reasons)

    def test_verbatim_within_threshold_pass(self):
        """Pass when verbatim rate increase is within threshold."""
        baseline = _make_report(verbatim_rate=0.05)
        current = _make_report(verbatim_rate=0.055)  # +0.005 < 0.01 threshold

        result = compare_reports(baseline, current, verbatim_delta_threshold=0.01)

        assert result.status == "pass"

    def test_membership_regression_above_threshold(self):
        """Fail when membership confidence increases above threshold."""
        baseline = _make_report(membership_conf=0.4)
        current = _make_report(membership_conf=0.5)  # +0.1 > default 0.05 threshold

        result = compare_reports(baseline, current, membership_delta_threshold=0.05)

        assert result.status == "fail"
        assert any("membership" in r.lower() for r in result.reasons)

    def test_membership_within_threshold_pass(self):
        """Pass when membership increase is within threshold."""
        baseline = _make_report(membership_conf=0.4)
        current = _make_report(membership_conf=0.42)  # +0.02 < 0.05 threshold

        result = compare_reports(baseline, current, membership_delta_threshold=0.05)

        assert result.status == "pass"

    def test_multiple_regressions(self):
        """Report all regressions when multiple occur."""
        baseline = _make_report(canary_extracted=False, verbatim_rate=0.05)
        current = _make_report(canary_extracted=True, verbatim_rate=0.20)

        result = compare_reports(baseline, current)

        assert result.status == "fail"
        assert len(result.reasons) >= 2

    def test_improvement_not_failure(self):
        """Improvement (lower scores) is not a regression."""
        baseline = _make_report(verbatim_rate=0.10)
        current = _make_report(verbatim_rate=0.05)  # Improved

        result = compare_reports(baseline, current)

        assert result.status == "pass"

    def test_deltas_populated(self):
        """Deltas contain metric information."""
        baseline = _make_report()
        current = _make_report()

        result = compare_reports(baseline, current)

        assert len(result.deltas) == 3  # canary, verbatim, membership
        metric_names = {d.metric for d in result.deltas}
        assert "canary_extracted" in metric_names
        assert "verbatim_leakage_rate" in metric_names
        assert "membership_confidence" in metric_names
