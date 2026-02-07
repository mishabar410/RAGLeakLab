"""Tests for calibration/report.py."""

import json

from ragleaklab.calibration.fit import CalibrationResult
from ragleaklab.calibration.report import (
    CalibrationReport,
    _compute_roc_table,
    generate_report,
    write_report,
)


class TestComputeRocTable:
    """Tests for _compute_roc_table."""

    def test_basic_roc_table(self):
        positive = [0.9, 0.8, 0.7]
        negative = [0.3, 0.2, 0.1]
        table = _compute_roc_table(positive, negative, higher_is_worse=True)
        assert len(table) > 0
        # All entries should have threshold, fpr, tpr
        for row in table:
            assert "threshold" in row
            assert "fpr" in row
            assert "tpr" in row

    def test_empty_positive_returns_empty(self):
        assert _compute_roc_table([], [0.1, 0.2]) == []

    def test_empty_negative_returns_empty(self):
        assert _compute_roc_table([0.9], []) == []

    def test_both_empty_returns_empty(self):
        assert _compute_roc_table([], []) == []

    def test_higher_is_worse_false(self):
        positive = [0.1, 0.2]
        negative = [0.8, 0.9]
        table = _compute_roc_table(positive, negative, higher_is_worse=False)
        assert len(table) > 0

    def test_fpr_tpr_range(self):
        positive = [0.8, 0.6, 0.9]
        negative = [0.2, 0.4, 0.1]
        table = _compute_roc_table(positive, negative)
        for row in table:
            assert 0.0 <= row["fpr"] <= 1.0
            assert 0.0 <= row["tpr"] <= 1.0


class TestCalibrationReport:
    """Tests for CalibrationReport model."""

    def _make_result(self) -> CalibrationResult:
        return CalibrationResult(
            threshold=0.5,
            achieved_fpr=0.01,
            achieved_tpr=0.95,
            n_positive=10,
            n_negative=90,
            decision_rule="score >= threshold -> FAIL",
        )

    def test_to_dict(self):
        report = CalibrationReport(
            pack_name="test-pack",
            metric_name="verbatim",
            target_fpr=0.01,
            result=self._make_result(),
        )
        d = report.to_dict()
        assert d["pack_name"] == "test-pack"
        assert d["metric_name"] == "verbatim"
        assert d["target_fpr"] == 0.01
        assert d["result"]["threshold"] == 0.5
        assert isinstance(d["generated_at"], str)

    def test_to_dict_roundtrip_json(self):
        report = CalibrationReport(
            pack_name="p",
            metric_name="m",
            target_fpr=0.05,
            result=self._make_result(),
            roc_table=[{"threshold": 0.5, "fpr": 0.01, "tpr": 0.95}],
        )
        serialized = json.dumps(report.to_dict())
        loaded = json.loads(serialized)
        assert loaded["roc_table"][0]["threshold"] == 0.5


class TestGenerateReport:
    """Tests for generate_report."""

    def _make_result(self) -> CalibrationResult:
        return CalibrationResult(
            threshold=0.5,
            achieved_fpr=0.01,
            achieved_tpr=0.9,
            n_positive=5,
            n_negative=5,
            decision_rule="score >= threshold -> FAIL",
        )

    def test_generate_report_basic(self):
        scores = [("t1", 0.9), ("t2", 0.8), ("t3", 0.2), ("t4", 0.1)]
        labels = {"t1": "positive", "t2": "positive", "t3": "negative", "t4": "negative"}
        report = generate_report(
            pack_name="pack1",
            metric_name="metric1",
            result=self._make_result(),
            scores=scores,
            labels=labels,
            target_fpr=0.01,
        )
        assert report.pack_name == "pack1"
        assert report.metric_name == "metric1"
        assert len(report.roc_table) > 0

    def test_generate_report_no_positive(self):
        scores = [("t1", 0.1)]
        labels = {"t1": "negative"}
        report = generate_report(
            pack_name="p",
            metric_name="m",
            result=self._make_result(),
            scores=scores,
            labels=labels,
            target_fpr=0.01,
        )
        assert report.roc_table == []


class TestWriteReport:
    """Tests for write_report."""

    def test_write_creates_file(self, tmp_path):
        result = CalibrationResult(
            threshold=0.5,
            achieved_fpr=0.01,
            achieved_tpr=0.9,
            n_positive=5,
            n_negative=5,
            decision_rule="score >= threshold -> FAIL",
        )
        report = CalibrationReport(
            pack_name="p",
            metric_name="m",
            target_fpr=0.01,
            result=result,
        )
        out = write_report(report, tmp_path / "sub")
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["pack_name"] == "p"

    def test_write_creates_directories(self, tmp_path):
        result = CalibrationResult(
            threshold=0.5,
            achieved_fpr=0.0,
            achieved_tpr=0.0,
            n_positive=0,
            n_negative=0,
            decision_rule="score >= threshold -> FAIL",
        )
        report = CalibrationReport(
            pack_name="x", metric_name="y", target_fpr=0.05, result=result,
        )
        deep_path = tmp_path / "a" / "b" / "c"
        out = write_report(report, deep_path)
        assert out.exists()
