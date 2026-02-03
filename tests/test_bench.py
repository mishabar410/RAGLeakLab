"""Tests for the bench CLI command."""

import json
import subprocess
import sys
from pathlib import Path


class TestBenchCommand:
    """Tests for the bench CLI command."""

    def test_bench_help(self) -> None:
        """Test bench --help works."""
        result = subprocess.run(
            [sys.executable, "-m", "ragleaklab", "bench", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "--pack" in result.stdout
        assert "--runs" in result.stdout
        assert "--out" in result.stdout

    def test_bench_produces_valid_json(self, tmp_path: Path) -> None:
        """Test bench command produces valid JSON output."""
        out_file = tmp_path / "bench.json"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "ragleaklab",
                "bench",
                "--pack",
                "canary-basic",
                "--runs",
                "2",
                "--out",
                str(out_file),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert out_file.exists()

        # Validate JSON structure
        with open(out_file) as f:
            data = json.load(f)

        # Required fields
        assert data["pack"] == "canary-basic"
        assert data["runs"] == 2
        assert "cases_per_run" in data
        assert data["cases_per_run"] > 0
        assert "jobs" in data
        assert "cache_enabled" in data
        assert "total_runtime_sec" in data
        assert "run_times_sec" in data
        assert len(data["run_times_sec"]) == 2
        assert "median_per_case_sec" in data
        assert "median_per_case_ms" in data
        assert "cache_hit_rate" in data
        assert "generated_at" in data

        # Types
        assert isinstance(data["total_runtime_sec"], (int, float))
        assert isinstance(data["median_per_case_sec"], (int, float))
        assert isinstance(data["cache_hit_rate"], (int, float))

    def test_bench_invalid_pack(self, tmp_path: Path) -> None:
        """Test bench with invalid pack name fails gracefully."""
        out_file = tmp_path / "bench.json"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "ragleaklab",
                "bench",
                "--pack",
                "nonexistent-pack",
                "--out",
                str(out_file),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert not out_file.exists()

    def test_bench_with_jobs(self, tmp_path: Path) -> None:
        """Test bench with parallel jobs."""
        out_file = tmp_path / "bench.json"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "ragleaklab",
                "bench",
                "--pack",
                "canary-basic",
                "--runs",
                "1",
                "--jobs",
                "2",
                "--out",
                str(out_file),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"

        with open(out_file) as f:
            data = json.load(f)

        assert data["jobs"] == 2
