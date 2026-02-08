"""Tests for the results table builder.

Covers:
- build_table_rows: parsing, sorting, category mapping, invalid file skipping
- render_table_md: header structure, column format, empty table, auto-generation notice
- Stable sorting: deterministic output across runs
- CLI smoke: --help works
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ragleaklab.bench.table import TableRow, build_table_rows, render_table_md

# ── Helpers ──────────────────────────────────────────────────────────


def _make_result(
    system_name: str = "Test System",
    system_type: str = "oss",
    bundle_version: str = "1.0.0",
    risk_score: float = 0.15,
    pack_results: list[dict] | None = None,
    notes: str = "",
) -> dict:
    """Build a minimal valid external result dict."""
    if pack_results is None:
        pack_results = [
            {
                "pack_name": "canary-basic",
                "category": "canary",
                "status": "pass",
                "total_cases": 10,
                "passed_cases": 10,
                "failed_cases": 0,
                "pass_rate": 1.0,
                "fail_rate": 0.0,
            },
            {
                "pack_name": "semantic-basic",
                "category": "semantic",
                "status": "fail",
                "total_cases": 10,
                "passed_cases": 7,
                "failed_cases": 3,
                "pass_rate": 0.7,
                "fail_rate": 0.3,
            },
            {
                "pack_name": "crossdoc-basic",
                "category": "crossdoc",
                "status": "pass",
                "total_cases": 5,
                "passed_cases": 5,
                "failed_cases": 0,
                "pass_rate": 1.0,
                "fail_rate": 0.0,
            },
            {
                "pack_name": "relevance-hijack",
                "category": "poisoning",
                "status": "pass",
                "total_cases": 8,
                "passed_cases": 6,
                "failed_cases": 2,
                "pass_rate": 0.75,
                "fail_rate": 0.25,
            },
        ]

    return {
        "external_schema_version": "1.0.0",
        "system_name": system_name,
        "system_type": system_type,
        "integration_type": "inprocess",
        "ragleaklab_version": "1.0.0",
        "bundle": {
            "name": "ragleakbench_v1",
            "version": bundle_version,
            "hash": "a" * 64,
        },
        "results_summary": {
            "total_packs": len(pack_results),
            "passed_packs": sum(1 for p in pack_results if p["status"] == "pass"),
            "failed_packs": sum(1 for p in pack_results if p["status"] == "fail"),
            "risk_score": risk_score,
            "pack_results": pack_results,
        },
        "notes": notes,
        "redaction_applied": True,
        "reproduction": {"config_snippet": "", "command": ""},
        "generated_at": "2026-02-08T00:00:00+00:00",
    }


def _write_result(dir_path: Path, name: str, data: dict) -> Path:
    """Write a result dict as JSON and return the path."""
    path = dir_path / name
    path.write_text(json.dumps(data))
    return path


# ── build_table_rows tests ───────────────────────────────────────────


class TestBuildTableRows:
    """Test row building from JSON files."""

    def test_empty_directory(self, tmp_path: Path):
        rows = build_table_rows(tmp_path, quiet=True)
        assert rows == []

    def test_single_result(self, tmp_path: Path):
        _write_result(tmp_path, "system_a.json", _make_result("System A"))
        rows = build_table_rows(tmp_path, quiet=True)
        assert len(rows) == 1
        assert rows[0].system_name == "System A"
        assert rows[0].risk_score == 0.15

    def test_category_rates_extracted(self, tmp_path: Path):
        _write_result(tmp_path, "system.json", _make_result())
        rows = build_table_rows(tmp_path, quiet=True)
        row = rows[0]
        assert row.canary_leak_rate == 0.0  # canary pass_rate=1.0, fail_rate=0.0
        assert row.semantic_leak_rate == pytest.approx(0.3)  # fail_rate=0.3
        assert row.acl_breach_rate == 0.0  # crossdoc pass_rate=1.0
        assert row.poisoning_indicator_rate == pytest.approx(0.25)  # fail_rate=0.25

    def test_missing_category_returns_none(self, tmp_path: Path):
        """When a category has no packs, the rate should be None."""
        data = _make_result(
            pack_results=[
                {
                    "pack_name": "canary-basic",
                    "category": "canary",
                    "status": "pass",
                    "total_cases": 5,
                    "passed_cases": 5,
                    "failed_cases": 0,
                    "pass_rate": 1.0,
                    "fail_rate": 0.0,
                },
            ],
        )
        _write_result(tmp_path, "system.json", data)
        rows = build_table_rows(tmp_path, quiet=True)
        row = rows[0]
        assert row.canary_leak_rate == 0.0
        assert row.semantic_leak_rate is None
        assert row.acl_breach_rate is None
        assert row.poisoning_indicator_rate is None

    def test_invalid_files_skipped(self, tmp_path: Path):
        """Non-conforming JSON files should be silently skipped."""
        _write_result(tmp_path, "valid.json", _make_result("Valid"))
        _write_result(tmp_path, "invalid.json", {"not": "a result"})
        _write_result(tmp_path, "corrupt.json", _make_result("Also Valid"))
        # Overwrite corrupt with actually valid data
        (tmp_path / "corrupt.json").write_text("NOT JSON {{{")
        rows = build_table_rows(tmp_path, quiet=True)
        assert len(rows) == 1  # Only "valid.json" parsed
        assert rows[0].system_name == "Valid"

    def test_notes_truncated(self, tmp_path: Path):
        long_notes = "A" * 200
        _write_result(tmp_path, "s.json", _make_result(notes=long_notes))
        rows = build_table_rows(tmp_path, quiet=True)
        assert len(rows[0].notes) <= 120


# ── Sorting tests ────────────────────────────────────────────────────


class TestSorting:
    """Test that sorting is correct and deterministic."""

    def test_sorted_by_risk_descending(self, tmp_path: Path):
        _write_result(tmp_path, "low.json", _make_result("Low Risk", risk_score=0.05))
        _write_result(tmp_path, "high.json", _make_result("High Risk", risk_score=0.90))
        _write_result(tmp_path, "mid.json", _make_result("Mid Risk", risk_score=0.40))
        rows = build_table_rows(tmp_path, quiet=True)
        scores = [r.risk_score for r in rows]
        assert scores == [0.90, 0.40, 0.05]
        assert rows[0].system_name == "High Risk"
        assert rows[2].system_name == "Low Risk"

    def test_stable_sort_same_score(self, tmp_path: Path):
        """Systems with equal risk scores sort alphabetically by name."""
        _write_result(tmp_path, "b.json", _make_result("Bravo", risk_score=0.50))
        _write_result(tmp_path, "a.json", _make_result("Alpha", risk_score=0.50))
        _write_result(tmp_path, "c.json", _make_result("Charlie", risk_score=0.50))
        rows = build_table_rows(tmp_path, quiet=True)
        names = [r.system_name for r in rows]
        assert names == ["Alpha", "Bravo", "Charlie"]

    def test_deterministic_across_runs(self, tmp_path: Path):
        """Multiple invocations produce identical output."""
        _write_result(tmp_path, "x.json", _make_result("X", risk_score=0.30))
        _write_result(tmp_path, "y.json", _make_result("Y", risk_score=0.70))
        _write_result(tmp_path, "z.json", _make_result("Z", risk_score=0.30))

        results = []
        for _ in range(5):
            rows = build_table_rows(tmp_path, quiet=True)
            results.append([(r.system_name, r.risk_score) for r in rows])

        # All 5 runs should produce the same order
        for r in results[1:]:
            assert r == results[0]


# ── Render tests ─────────────────────────────────────────────────────


class TestRenderTableMd:
    """Test Markdown table rendering."""

    def test_empty_table(self):
        md = render_table_md([])
        assert "no results yet" in md
        assert "*0 system(s) tested.*" in md

    def test_auto_generated_notice(self):
        md = render_table_md([])
        assert "AUTO-GENERATED" in md
        assert "do not edit" in md

    def test_header_columns(self):
        md = render_table_md([])
        assert "System" in md
        assert "Type" in md
        assert "Bundle" in md
        assert "Risk Score" in md
        assert "Canary Leaks" in md
        assert "Semantic Leakage" in md
        assert "Poisoning Indicators" in md
        assert "ACL Breaches" in md
        assert "Notes" in md

    def test_row_rendered(self):
        row = TableRow(
            system_name="TestSys",
            system_type="oss",
            bundle_version="1.0.0",
            risk_score=0.42,
            canary_leak_rate=0.1,
            semantic_leak_rate=0.2,
            poisoning_indicator_rate=None,
            acl_breach_rate=0.0,
            notes="some notes",
        )
        md = render_table_md([row])
        assert "**TestSys**" in md
        assert "`1.0.0`" in md
        assert "0.4200" in md
        assert "10.0%" in md  # canary
        assert "20.0%" in md  # semantic
        assert "—" in md  # poisoning (None)
        assert "0.0%" in md  # acl
        assert "some notes" in md
        assert "*1 system(s) tested.*" in md

    def test_none_rates_render_as_dash(self):
        row = TableRow(
            system_name="X",
            system_type="oss",
            bundle_version="1.0.0",
            risk_score=0.0,
        )
        md = render_table_md([row])
        # Find the data row (starts with "| **X**")
        data_line = next(line for line in md.splitlines() if "**X**" in line)
        # All 4 rate columns should show "—"
        assert data_line.count("—") == 4

    def test_bundle_version_in_code_block(self):
        row = TableRow(
            system_name="X",
            system_type="oss",
            bundle_version="2.0.0",
            risk_score=0.0,
        )
        md = render_table_md([row])
        assert "`2.0.0`" in md


# ── Sample file test ─────────────────────────────────────────────────


class TestSampleFile:
    """Verify the shipped sample produces a valid table."""

    def test_sample_builds_table(self):
        sample_dir = Path(__file__).parent.parent / "external_results" / "examples"
        if not sample_dir.is_dir():
            pytest.skip("Sample directory not found")
        rows = build_table_rows(sample_dir, quiet=True)
        assert len(rows) == 1
        md = render_table_md(rows)
        assert "Example RAG System" in md
        assert "*1 system(s) tested.*" in md
