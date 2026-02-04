"""Tests for determinism verification."""

import json
from pathlib import Path

import pytest

from ragleaklab.core.determinism import (
    compare_normalized,
    compare_reports,
    compare_runs,
    normalize_report,
    normalize_run_entry,
    normalize_runs,
)


class TestNormalizeReport:
    """Tests for report normalization."""

    def test_strips_generated_at(self):
        """Removes generated_at field."""
        data = {
            "tool_version": "0.1.0",
            "generated_at": "2024-01-15T10:00:00",
            "total_cases": 10,
        }
        result = normalize_report(data)
        assert "generated_at" not in result
        assert result["tool_version"] == "0.1.0"
        assert result["total_cases"] == 10

    def test_preserves_other_fields(self):
        """Preserves non-volatile fields."""
        data = {
            "tool_version": "0.1.0",
            "config_hash": "abc123",
            "overall_pass": True,
        }
        result = normalize_report(data)
        assert result == data


class TestNormalizeRuns:
    """Tests for runs.jsonl normalization."""

    def test_strips_timings(self):
        """Removes timings field from entries."""
        entry = {
            "test_id": "test_001",
            "threat": "canary",
            "timings": {"retrieval_ms": 50, "generation_ms": 100},
        }
        result = normalize_run_entry(entry)
        assert "timings" not in result
        assert result["test_id"] == "test_001"

    def test_sorts_by_test_id(self):
        """Sorts entries by test_id."""
        entries = [
            {"test_id": "z_test"},
            {"test_id": "a_test"},
            {"test_id": "m_test"},
        ]
        result = normalize_runs(entries)
        assert [e["test_id"] for e in result] == ["a_test", "m_test", "z_test"]


class TestCompareNormalized:
    """Tests for deep comparison."""

    def test_equal_dicts(self):
        """Equal dicts return no diffs."""
        data = {"a": 1, "b": {"c": 2}}
        diffs = compare_normalized(data, data)
        assert diffs == []

    def test_different_values(self):
        """Different values produce diffs."""
        data1 = {"a": 1}
        data2 = {"a": 2}
        diffs = compare_normalized(data1, data2)
        assert len(diffs) == 1
        assert "a:" in diffs[0]

    def test_missing_keys(self):
        """Missing keys produce diffs."""
        data1 = {"a": 1, "b": 2}
        data2 = {"a": 1}
        diffs = compare_normalized(data1, data2)
        assert len(diffs) == 1
        assert "b:" in diffs[0]

    def test_list_comparison(self):
        """Lists are compared element-wise."""
        data1 = {"items": [1, 2, 3]}
        data2 = {"items": [1, 2, 4]}
        diffs = compare_normalized(data1, data2)
        assert len(diffs) == 1


class TestCompareReports:
    """Tests for report file comparison."""

    def test_identical_reports_match(self, tmp_path: Path):
        """Identical reports (after normalization) match."""
        report = {
            "tool_version": "0.1.0",
            "total_cases": 5,
            "overall_pass": True,
        }

        path1 = tmp_path / "report1.json"
        path2 = tmp_path / "report2.json"

        # Add different generated_at (should be stripped)
        report1 = {**report, "generated_at": "2024-01-01T00:00:00"}
        report2 = {**report, "generated_at": "2024-01-02T00:00:00"}

        path1.write_text(json.dumps(report1))
        path2.write_text(json.dumps(report2))

        equal, diffs = compare_reports(path1, path2)
        assert equal
        assert diffs == []

    def test_different_reports_fail(self, tmp_path: Path):
        """Different reports produce diffs."""
        path1 = tmp_path / "report1.json"
        path2 = tmp_path / "report2.json"

        path1.write_text(json.dumps({"total_cases": 5}))
        path2.write_text(json.dumps({"total_cases": 10}))

        equal, diffs = compare_reports(path1, path2)
        assert not equal
        assert len(diffs) > 0


class TestCompareRuns:
    """Tests for runs.jsonl file comparison."""

    def test_identical_runs_match(self, tmp_path: Path):
        """Identical runs (after normalization) match."""
        runs = [
            {"test_id": "test_002", "threat": "canary"},
            {"test_id": "test_001", "threat": "verbatim"},
        ]

        path1 = tmp_path / "runs1.jsonl"
        path2 = tmp_path / "runs2.jsonl"

        # Add timings (should be stripped) and different order (should be sorted)
        runs1 = [
            {**runs[0], "timings": {"ms": 100}},
            {**runs[1], "timings": {"ms": 50}},
        ]
        runs2 = [
            {**runs[1], "timings": {"ms": 75}},  # Different order
            {**runs[0], "timings": {"ms": 200}},
        ]

        path1.write_text("\n".join(json.dumps(r) for r in runs1))
        path2.write_text("\n".join(json.dumps(r) for r in runs2))

        equal, diffs = compare_runs(path1, path2)
        assert equal
        assert diffs == []


@pytest.mark.slow
class TestVerifyDeterminismIntegration:
    """Integration tests for full determinism verification."""

    def test_basic_pack_is_deterministic(self, tmp_path: Path):
        """Basic pack produces identical output across runs."""
        from ragleaklab.core.determinism import verify_determinism

        passed, diffs = verify_determinism(
            pack="canary-basic",
            runs=2,
            out_dir=tmp_path / "determinism_test",
        )

        # Basic pack should be deterministic
        assert passed, f"Pack not deterministic: {diffs}"
