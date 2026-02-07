"""Tests for bench publish command and results generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from ragleaklab.bench.results import (
    build_results,
    validate_results_file,
)

PROJECT_ROOT = Path(__file__).parent.parent


@pytest.fixture()
def bundle_path(tmp_path: Path) -> Path:
    """Create a minimal bundle.yaml for testing."""
    bundle = {
        "name": "test_bundle",
        "version": "1.0.0",
        "description": "Test bundle",
        "packs": [
            {"name": "pack-a", "category": "canary"},
            {"name": "pack-b", "category": "semantic"},
        ],
    }
    path = tmp_path / "bundle.yaml"
    with open(path, "w") as f:
        yaml.dump(bundle, f)
    return path


@pytest.fixture()
def bench_output_dir(tmp_path: Path) -> Path:
    """Create a minimal bench output directory with bench_summary.json."""
    out = tmp_path / "bench_out"
    out.mkdir()
    summary = {
        "bundle_name": "test_bundle",
        "bundle_version": "1.0.0",
        "generated_at": "2026-01-01T00:00:00Z",
        "total_packs": 2,
        "passed_packs": 1,
        "failed_packs": 1,
        "error_packs": 0,
        "skipped_packs": 0,
        "total_runtime_sec": 5.0,
        "risk_score": 0.15,
        "pack_results": [
            {
                "pack_name": "pack-a",
                "category": "canary",
                "status": "pass",
                "total_cases": 10,
                "passed_cases": 10,
                "failed_cases": 0,
                "pass_rate": 1.0,
                "fail_rate": 0.0,
                "runtime_sec": 2.0,
            },
            {
                "pack_name": "pack-b",
                "category": "semantic",
                "status": "fail",
                "total_cases": 8,
                "passed_cases": 6,
                "failed_cases": 2,
                "pass_rate": 0.75,
                "fail_rate": 0.25,
                "runtime_sec": 3.0,
            },
        ],
    }
    with open(out / "bench_summary.json", "w") as f:
        json.dump(summary, f)
    return out


class TestBuildResults:
    """Test build_results() function."""

    def test_builds_valid_results(self, bench_output_dir: Path, bundle_path: Path, tmp_path: Path):
        """build_results produces valid BenchResultsSchema."""
        results = build_results(bench_output_dir, bundle_path)

        assert results.results_schema_version == "1.0.0"
        assert results.bundle.name == "test_bundle"
        assert results.bundle.version == "1.0.0"
        assert results.total_packs == 2
        assert results.passed_packs == 1
        assert results.failed_packs == 1
        assert results.risk_score == 0.15
        assert len(results.pack_results) == 2
        assert results.environment.python_version

    def test_writes_valid_json(self, bench_output_dir: Path, bundle_path: Path, tmp_path: Path):
        """Results can be serialized and deserialized."""
        results = build_results(bench_output_dir, bundle_path)
        out_path = tmp_path / "results.json"
        with open(out_path, "w") as f:
            json.dump(results.model_dump(), f)

        # Validate the written file
        validated = validate_results_file(out_path)
        assert validated.bundle.name == results.bundle.name

    def test_missing_summary_raises(self, tmp_path: Path, bundle_path: Path):
        """Missing bench_summary.json raises FileNotFoundError."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        with pytest.raises(FileNotFoundError, match=r"bench_summary\.json"):
            build_results(empty_dir, bundle_path)

    def test_bundle_mismatch_raises(self, bench_output_dir: Path, tmp_path: Path):
        """Mismatched bundle name raises ValueError."""
        wrong_bundle = {
            "name": "wrong_bundle",
            "version": "1.0.0",
            "packs": [],
        }
        path = tmp_path / "wrong.yaml"
        with open(path, "w") as f:
            yaml.dump(wrong_bundle, f)

        with pytest.raises(ValueError, match="mismatch"):
            build_results(bench_output_dir, path)


class TestValidateResultsFile:
    """Test validate_results_file() function."""

    def test_validates_sample_results(self):
        """Sample results file validates successfully."""
        sample = PROJECT_ROOT / "results" / "sample_results.json"
        if not sample.exists():
            pytest.skip("sample_results.json not found")

        results = validate_results_file(sample)
        assert results.results_schema_version == "1.0.0"
        assert results.bundle.name == "ragleakbench_v1"

    def test_missing_file_raises(self, tmp_path: Path):
        """Missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            validate_results_file(tmp_path / "nope.json")

    def test_invalid_schema_raises(self, tmp_path: Path):
        """Invalid schema raises ValidationError."""
        from pydantic import ValidationError

        bad = tmp_path / "bad.json"
        bad.write_text('{"bad": true}')
        with pytest.raises(ValidationError):
            validate_results_file(bad)


class TestBenchPublishCLI:
    """Test bench publish CLI integration."""

    def test_publish_creates_results_json(
        self, bench_output_dir: Path, bundle_path: Path, tmp_path: Path
    ):
        """CLI publish command creates valid results.json."""
        from typer.testing import CliRunner

        from ragleaklab.cli.bench import bench_app

        runner = CliRunner()
        out_path = tmp_path / "results.json"

        result = runner.invoke(
            bench_app,
            [
                "publish",
                "--in",
                str(bench_output_dir),
                "--bundle",
                str(bundle_path),
                "--out",
                str(out_path),
            ],
        )

        assert result.exit_code == 0, result.output
        assert out_path.exists()

        # Validate output
        validated = validate_results_file(out_path)
        assert validated.bundle.name == "test_bundle"

    def test_validate_results_cli(self, bench_output_dir: Path, bundle_path: Path, tmp_path: Path):
        """CLI validate-results command works on published results."""
        from typer.testing import CliRunner

        from ragleaklab.cli.bench import bench_app

        runner = CliRunner()
        out_path = tmp_path / "results.json"

        # First publish
        runner.invoke(
            bench_app,
            [
                "publish",
                "--in",
                str(bench_output_dir),
                "--bundle",
                str(bundle_path),
                "--out",
                str(out_path),
            ],
        )

        # Then validate
        result = runner.invoke(
            bench_app,
            ["validate-results", "--file", str(out_path)],
        )

        assert result.exit_code == 0, result.output
        assert "Valid" in result.output
