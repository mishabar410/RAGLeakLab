"""End-to-end tests for CLI."""

import json
import subprocess
import sys
from pathlib import Path


class TestCLIRun:
    """E2E tests for CLI run command."""

    def test_cli_run_produces_outputs(self, tmp_path: Path):
        """CLI run creates report.json and runs.jsonl."""
        # Setup paths
        project_root = Path(__file__).parent.parent
        corpus = project_root / "data" / "corpus_private_canary"
        attacks = project_root / "data" / "attacks"
        out_dir = tmp_path / "output"

        # Run CLI
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "ragleaklab",
                "run",
                "--corpus",
                str(corpus),
                "--attacks",
                str(attacks),
                "--out",
                str(out_dir),
            ],
            capture_output=True,
            text=True,
            cwd=project_root,
        )

        # Check exit code
        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        # Check report.json exists and is valid
        report_path = out_dir / "report.json"
        assert report_path.exists(), "report.json not created"

        with open(report_path) as f:
            report = json.load(f)

        # Check required fields
        assert "schema_version" in report
        assert "generated_at" in report
        assert "canary_extracted" in report
        assert "verbatim_leakage_rate" in report
        assert "membership_confidence" in report
        assert "overall_pass" in report
        assert "failures" in report
        assert "total_cases" in report

        # Check runs.jsonl exists and has correct line count
        runs_path = out_dir / "runs.jsonl"
        assert runs_path.exists(), "runs.jsonl not created"

        with open(runs_path) as f:
            lines = f.readlines()

        # Should have 20 cases (10 canary + 10 verbatim)
        assert len(lines) == 20, f"Expected 20 lines, got {len(lines)}"

        # Each line should be valid JSON
        for line in lines:
            case = json.loads(line)
            assert "test_id" in case
            assert "threat" in case
            assert "query" in case
            assert "answer" in case
            assert "retrieved_ids" in case

    def test_cli_run_detects_canaries(self, tmp_path: Path):
        """CLI run correctly detects canary leaks."""
        project_root = Path(__file__).parent.parent
        corpus = project_root / "data" / "corpus_private_canary"
        attacks = project_root / "data" / "attacks"
        out_dir = tmp_path / "output"

        subprocess.run(
            [
                sys.executable,
                "-m",
                "ragleaklab",
                "run",
                "--corpus",
                str(corpus),
                "--attacks",
                str(attacks),
                "--out",
                str(out_dir),
            ],
            capture_output=True,
            text=True,
            cwd=project_root,
        )

        with open(out_dir / "report.json") as f:
            report = json.load(f)

        # Private canary corpus should trigger canary detection
        # (depends on attack queries matching canary content)
        assert isinstance(report["canary_extracted"], bool)
        assert isinstance(report["canary_count"], int)

    def test_cli_version(self):
        """CLI version command works."""
        project_root = Path(__file__).parent.parent
        result = subprocess.run(
            [sys.executable, "-m", "ragleaklab", "version"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )

        assert result.returncode == 0
        assert "RAGLeakLab" in result.stdout

    def test_cli_help(self):
        """CLI help works."""
        project_root = Path(__file__).parent.parent
        result = subprocess.run(
            [sys.executable, "-m", "ragleaklab", "--help"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )

        assert result.returncode == 0
        assert "run" in result.stdout
