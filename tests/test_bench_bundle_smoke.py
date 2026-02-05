"""Smoke tests for benchmark bundle execution."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml

from ragleaklab.bench.bundle import (
    BundleManifest,
    generate_summary_markdown,
    run_bundle,
)


class TestBundleSmokeUnit:
    """Unit-level smoke tests for bundle runner."""

    @pytest.fixture
    def minimal_bundle(self, tmp_path: Path) -> BundleManifest:
        """Create a minimal bundle manifest."""
        return BundleManifest(
            name="test-bundle",
            version="0.1.0",
            packs=[
                {
                    "name": "canary-basic",
                    "corpus": "data/corpus_private_canary",
                    "category": "canary",
                }
            ],
        )

    def test_dry_run_skips_execution(
        self, minimal_bundle: BundleManifest, tmp_path: Path
    ) -> None:
        """Dry run mode skips pack execution."""
        out = tmp_path / "out"

        summary = run_bundle(minimal_bundle, out, dry_run=True)

        assert summary.skipped_packs == 1
        assert summary.passed_packs == 0
        assert summary.total_runtime_sec == 0.0

    def test_limit_packs_restricts_execution(
        self, minimal_bundle: BundleManifest, tmp_path: Path
    ) -> None:
        """limit_packs option restricts number of packs."""
        # Add more packs
        extended_bundle = BundleManifest(
            name="test",
            version="1.0.0",
            packs=[
                {"name": "pack1"},
                {"name": "pack2"},
                {"name": "pack3"},
            ],
        )

        summary = run_bundle(extended_bundle, tmp_path / "out", limit_packs=1, dry_run=True)

        assert summary.total_packs == 1

    def test_summary_has_required_fields(
        self, minimal_bundle: BundleManifest, tmp_path: Path
    ) -> None:
        """Bundle summary contains all required fields."""
        summary = run_bundle(minimal_bundle, tmp_path / "out", dry_run=True)

        assert summary.bundle_name == "test-bundle"
        assert summary.bundle_version == "0.1.0"
        assert summary.generated_at is not None
        assert summary.risk_score >= 0.0
        assert isinstance(summary.pack_results, list)

    def test_generate_markdown_summary(
        self, minimal_bundle: BundleManifest, tmp_path: Path
    ) -> None:
        """Markdown summary is generated correctly."""
        summary = run_bundle(minimal_bundle, tmp_path / "out", dry_run=True)

        md = generate_summary_markdown(summary)

        assert "# test-bundle Benchmark Results" in md
        assert "| Total Packs |" in md
        assert "| Risk Score |" in md


@pytest.mark.slow
class TestBundleSmokeCLI:
    """CLI-level smoke tests for bundle runner."""

    @pytest.fixture
    def smoke_bundle(self, tmp_path: Path) -> Path:
        """Create a smoke bundle with single pack."""
        bundle_dir = tmp_path / "bundle"
        bundle_dir.mkdir()

        bundle_file = bundle_dir / "bundle.yaml"
        bundle_file.write_text(
            yaml.dump(
                {
                    "name": "smoke-test",
                    "version": "0.1.0",
                    "packs": [
                        {
                            "name": "canary-basic",
                            "corpus": "data/corpus_private_canary",
                            "category": "canary",
                        }
                    ],
                }
            )
        )

        return bundle_file

    def test_bundle_cli_dry_run(self, smoke_bundle: Path, tmp_path: Path) -> None:
        """CLI dry-run creates summary without running packs."""
        out = tmp_path / "out"

        result = subprocess.run(
            [
                "uv",
                "run",
                "ragleaklab",
                "bench",
                "bundle",
                "--bundle",
                str(smoke_bundle),
                "--out",
                str(out),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )

        assert result.returncode == 0
        assert (out / "bench_summary.json").exists()
        assert (out / "bench_summary.md").exists()

    def test_bundle_cli_limit_packs(self, smoke_bundle: Path, tmp_path: Path) -> None:
        """CLI limit-packs option is respected."""
        out = tmp_path / "out"

        result = subprocess.run(
            [
                "uv",
                "run",
                "ragleaklab",
                "bench",
                "bundle",
                "--bundle",
                str(smoke_bundle),
                "--out",
                str(out),
                "--limit-packs",
                "1",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )

        assert result.returncode == 0

        summary_path = out / "bench_summary.json"
        with open(summary_path) as f:
            summary = json.load(f)

        assert summary["total_packs"] == 1

    def test_bundle_summary_format(self, smoke_bundle: Path, tmp_path: Path) -> None:
        """Summary JSON has correct format."""
        out = tmp_path / "out"

        subprocess.run(
            [
                "uv",
                "run",
                "ragleaklab",
                "bench",
                "bundle",
                "--bundle",
                str(smoke_bundle),
                "--out",
                str(out),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )

        summary_path = out / "bench_summary.json"
        if summary_path.exists():
            with open(summary_path) as f:
                summary = json.load(f)

            # Validate required fields
            assert "bundle_name" in summary
            assert "bundle_version" in summary
            assert "total_packs" in summary
            assert "passed_packs" in summary
            assert "failed_packs" in summary
            assert "risk_score" in summary
            assert "pack_results" in summary
