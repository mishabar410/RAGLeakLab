"""Bundle runner for benchmark suites.

Provides loading, execution, and summary generation for benchmark bundles.
"""

from __future__ import annotations

import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

__all__ = [
    "BundleManifest",
    "BundlePackResult",
    "BundleSummary",
    "load_bundle",
    "run_bundle",
]


class PackSpec(BaseModel):
    """Specification for a pack in the bundle."""

    name: str
    corpus: str | None = None
    type: Literal["standard", "poisoning"] = "standard"
    category: str = "default"


class ScoringConfig(BaseModel):
    """Configuration for risk scoring."""

    severity_weights: dict[str, float] = Field(
        default_factory=lambda: {"high": 3.0, "medium": 2.0, "low": 1.0}
    )
    category_weights: dict[str, float] = Field(default_factory=dict)


class BundleManifest(BaseModel):
    """Manifest for a benchmark bundle."""

    name: str
    version: str
    description: str = ""
    packs: list[PackSpec]
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    expected_outputs: list[str] = Field(default_factory=list)


class BundlePackResult(BaseModel):
    """Result of running a single pack."""

    pack_name: str
    category: str
    status: Literal["pass", "fail", "error", "skipped"]
    runtime_sec: float
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    pass_rate: float = 0.0
    fail_rate: float = 0.0
    error_message: str | None = None
    report_path: str | None = None


class BundleSummary(BaseModel):
    """Summary of benchmark bundle execution."""

    bundle_name: str
    bundle_version: str
    generated_at: str
    total_packs: int
    passed_packs: int
    failed_packs: int
    error_packs: int
    skipped_packs: int
    total_runtime_sec: float
    risk_score: float
    pack_results: list[BundlePackResult]


def load_bundle(bundle_path: Path | str) -> BundleManifest:
    """Load bundle manifest from file.

    Args:
        bundle_path: Path to bundle.yaml or bundle.json.

    Returns:
        Parsed BundleManifest.

    Raises:
        FileNotFoundError: If bundle file doesn't exist.
        ValueError: If bundle format is invalid.
    """
    bundle_path = Path(bundle_path)
    if not bundle_path.exists():
        raise FileNotFoundError(f"Bundle not found: {bundle_path}")

    with open(bundle_path) as f:
        if bundle_path.suffix in (".yaml", ".yml"):
            data = yaml.safe_load(f) or {}
        else:
            data = json.load(f)

    return BundleManifest.model_validate(data)


def _run_pack(
    pack: PackSpec,
    out_dir: Path,
    project_root: Path,
) -> BundlePackResult:
    """Run a single pack and return result."""
    pack_out = out_dir / pack.name.replace("-", "_")
    pack_out.mkdir(parents=True, exist_ok=True)

    start_time = time.perf_counter()

    # Build command based on pack type
    if pack.type == "poisoning":
        cmd = [
            "uv",
            "run",
            "ragleaklab",
            "run",
            "--poisoning-pack",
            pack.name,
            "--out",
            str(pack_out),
        ]
    else:
        cmd = [
            "uv",
            "run",
            "ragleaklab",
            "run",
            "--pack",
            pack.name,
            "--out",
            str(pack_out),
        ]
        # Add corpus if specified
        if pack.corpus:
            corpus_path = project_root / pack.corpus
            if corpus_path.exists():
                cmd.extend(["--corpus", str(corpus_path)])

    # Run the pack
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(project_root),
    )

    elapsed = time.perf_counter() - start_time
    report_path = pack_out / "report.json"

    # Parse result
    if result.returncode != 0:
        # Check if report was still generated
        if not report_path.exists():
            return BundlePackResult(
                pack_name=pack.name,
                category=pack.category,
                status="error",
                runtime_sec=elapsed,
                error_message=result.stderr[:500] if result.stderr else "Unknown error",
            )

    # Load report to extract metrics
    if report_path.exists():
        with open(report_path) as f:
            report = json.load(f)

        summary = report.get("summary", {})
        total_cases = summary.get("total_cases", 0)
        passed_cases = summary.get("passed", 0)
        failed_cases = summary.get("failed", 0)
        pass_rate = summary.get("pass_rate", 0.0)
        fail_rate = summary.get("fail_rate", 0.0)

        # Determine status based on failure count
        status = "pass" if failed_cases == 0 else "fail"

        return BundlePackResult(
            pack_name=pack.name,
            category=pack.category,
            status=status,
            runtime_sec=elapsed,
            total_cases=total_cases,
            passed_cases=passed_cases,
            failed_cases=failed_cases,
            pass_rate=pass_rate,
            fail_rate=fail_rate,
            report_path=str(report_path),
        )

    return BundlePackResult(
        pack_name=pack.name,
        category=pack.category,
        status="error",
        runtime_sec=elapsed,
        error_message="Report not generated",
    )


def _compute_risk_score(
    results: list[BundlePackResult],
    scoring: ScoringConfig,
) -> float:
    """Compute aggregate risk score from results.

    Risk score = sum of (fail_rate * category_weight) for each pack.
    Higher scores indicate more security risk.
    """
    total_score = 0.0

    for result in results:
        if result.status in ("error", "skipped"):
            continue

        # Get category weight (default 1.0)
        cat_weight = scoring.category_weights.get(result.category, 1.0)

        # Add weighted fail rate
        total_score += result.fail_rate * cat_weight

    return round(total_score, 4)


def run_bundle(
    manifest: BundleManifest,
    out_dir: Path | str,
    limit_packs: int | None = None,
    dry_run: bool = False,
) -> BundleSummary:
    """Run all packs in a bundle and generate summary.

    Args:
        manifest: Bundle manifest.
        out_dir: Output directory for results.
        limit_packs: Optional limit on number of packs to run.
        dry_run: If True, don't actually run packs.

    Returns:
        BundleSummary with aggregate results.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Determine project root
    project_root = Path(__file__).parent.parent.parent.parent

    # Select packs to run
    packs_to_run = manifest.packs[:limit_packs] if limit_packs else manifest.packs

    results: list[BundlePackResult] = []
    total_runtime = 0.0

    for pack in packs_to_run:
        if dry_run:
            results.append(
                BundlePackResult(
                    pack_name=pack.name,
                    category=pack.category,
                    status="skipped",
                    runtime_sec=0.0,
                )
            )
        else:
            result = _run_pack(pack, out_dir, project_root)
            results.append(result)
            total_runtime += result.runtime_sec

    # Count statuses
    passed = sum(1 for r in results if r.status == "pass")
    failed = sum(1 for r in results if r.status == "fail")
    errors = sum(1 for r in results if r.status == "error")
    skipped = sum(1 for r in results if r.status == "skipped")

    # Compute risk score
    risk_score = _compute_risk_score(results, manifest.scoring)

    return BundleSummary(
        bundle_name=manifest.name,
        bundle_version=manifest.version,
        generated_at=datetime.now(UTC).isoformat(),
        total_packs=len(results),
        passed_packs=passed,
        failed_packs=failed,
        error_packs=errors,
        skipped_packs=skipped,
        total_runtime_sec=round(total_runtime, 3),
        risk_score=risk_score,
        pack_results=results,
    )


def generate_summary_markdown(summary: BundleSummary) -> str:
    """Generate human-readable markdown summary."""
    lines = [
        f"# {summary.bundle_name} Benchmark Results",
        "",
        f"**Version**: {summary.bundle_version}",
        f"**Generated**: {summary.generated_at}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total Packs | {summary.total_packs} |",
        f"| Passed | {summary.passed_packs} |",
        f"| Failed | {summary.failed_packs} |",
        f"| Errors | {summary.error_packs} |",
        f"| Risk Score | {summary.risk_score:.4f} |",
        f"| Total Runtime | {summary.total_runtime_sec:.2f}s |",
        "",
        "## Pack Results",
        "",
        "| Pack | Category | Status | Cases | Pass Rate | Runtime |",
        "|------|----------|--------|-------|-----------|---------|",
    ]

    for r in summary.pack_results:
        status_icon = {
            "pass": "✅",
            "fail": "❌",
            "error": "⚠️",
            "skipped": "⏭️",
        }.get(r.status, "❓")

        lines.append(
            f"| {r.pack_name} | {r.category} | {status_icon} {r.status} | "
            f"{r.total_cases} | {r.pass_rate:.1%} | {r.runtime_sec:.2f}s |"
        )

    # Overall status
    lines.extend(
        [
            "",
            "---",
            "",
        ]
    )

    if summary.failed_packs == 0 and summary.error_packs == 0:
        lines.append("✅ **All packs passed**")
    else:
        lines.append(f"❌ **{summary.failed_packs} failed, {summary.error_packs} errors**")

    return "\n".join(lines)
