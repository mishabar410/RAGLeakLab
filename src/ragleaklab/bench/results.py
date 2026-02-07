"""Schema and validation for leaderboard-ready benchmark results.

Defines the normalized results format produced by ``bench publish``
and consumed by ``bench validate-results``.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from ragleaklab import __version__

__all__ = [
    "BenchResultsSchema",
    "PackMetricsSummary",
    "build_results",
    "validate_results_file",
]

# Fixed schema version for the results format itself
RESULTS_SCHEMA_VERSION = "1.0.0"


class EnvironmentInfo(BaseModel):
    """Runtime environment metadata."""

    python_version: str = Field(description="Python version string")
    platform: str = Field(description="OS platform identifier")
    machine: str = Field(description="Machine architecture")


class BundleRef(BaseModel):
    """Reference to the bundle used for the run."""

    name: str
    version: str
    hash: str = Field(description="SHA-256 of bundle.yaml")


class PackMetricsSummary(BaseModel):
    """Per-pack metrics summary."""

    pack_name: str
    category: str
    status: str
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    pass_rate: float = 0.0
    fail_rate: float = 0.0
    runtime_sec: float = 0.0


class BenchResultsSchema(BaseModel):
    """Normalized benchmark results for leaderboard submission."""

    results_schema_version: str = Field(
        default=RESULTS_SCHEMA_VERSION,
        description="Version of this results format",
    )
    tool_version: str = Field(description="RAGLeakLab version used")
    schema_version: str = Field(description="Report schema version")
    generated_at: str = Field(description="ISO timestamp of generation")
    bundle: BundleRef = Field(description="Bundle reference")
    total_packs: int = 0
    passed_packs: int = 0
    failed_packs: int = 0
    error_packs: int = 0
    risk_score: float = 0.0
    total_runtime_sec: float = 0.0
    pack_results: list[PackMetricsSummary] = Field(default_factory=list)
    environment: EnvironmentInfo = Field(description="Runtime environment")


def _hash_file(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _current_environment() -> EnvironmentInfo:
    """Capture current runtime environment."""
    return EnvironmentInfo(
        python_version=sys.version.split()[0],
        platform=platform.system(),
        machine=platform.machine(),
    )


def build_results(
    out_dir: Path,
    bundle_path: Path,
    *,
    schema_version: str = "2.0.0",
) -> BenchResultsSchema:
    """Build normalized results from a bench output directory.

    Args:
        out_dir: Directory containing bench_summary.json from ``bench bundle``.
        bundle_path: Path to the bundle.yaml used for the run.
        schema_version: Report schema version to embed.

    Returns:
        Validated BenchResultsSchema.

    Raises:
        FileNotFoundError: If required files are missing.
        ValueError: If output doesn't match bundle.
    """
    summary_path = out_dir / "bench_summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(
            f"bench_summary.json not found in {out_dir}. Run 'ragleaklab bench bundle' first."
        )
    if not bundle_path.exists():
        raise FileNotFoundError(f"Bundle not found: {bundle_path}")

    # Load summary
    with open(summary_path) as f:
        summary = json.load(f)

    # Load bundle for validation
    with open(bundle_path) as f:
        bundle_data = yaml.safe_load(f)

    # Validate bundle name matches
    if summary.get("bundle_name") != bundle_data.get("name"):
        raise ValueError(
            f"Bundle name mismatch: summary says '{summary.get('bundle_name')}' "
            f"but bundle.yaml says '{bundle_data.get('name')}'"
        )

    # Build pack results
    pack_results = []
    for pr in summary.get("pack_results", []):
        pack_results.append(
            PackMetricsSummary(
                pack_name=pr["pack_name"],
                category=pr.get("category", "default"),
                status=pr.get("status", "error"),
                total_cases=pr.get("total_cases", 0),
                passed_cases=pr.get("passed_cases", 0),
                failed_cases=pr.get("failed_cases", 0),
                pass_rate=pr.get("pass_rate", 0.0),
                fail_rate=pr.get("fail_rate", 0.0),
                runtime_sec=pr.get("runtime_sec", 0.0),
            )
        )

    return BenchResultsSchema(
        tool_version=__version__,
        schema_version=schema_version,
        generated_at=datetime.now(UTC).isoformat(),
        bundle=BundleRef(
            name=bundle_data["name"],
            version=bundle_data.get("version", "0.0.0"),
            hash=_hash_file(bundle_path),
        ),
        total_packs=summary.get("total_packs", 0),
        passed_packs=summary.get("passed_packs", 0),
        failed_packs=summary.get("failed_packs", 0),
        error_packs=summary.get("error_packs", 0),
        risk_score=summary.get("risk_score", 0.0),
        total_runtime_sec=summary.get("total_runtime_sec", 0.0),
        pack_results=pack_results,
        environment=_current_environment(),
    )


def validate_results_file(path: Path) -> BenchResultsSchema:
    """Parse and validate a results JSON file.

    Args:
        path: Path to results.json.

    Returns:
        Validated BenchResultsSchema.

    Raises:
        FileNotFoundError: If file doesn't exist.
        pydantic.ValidationError: If schema is invalid.
    """
    if not path.exists():
        raise FileNotFoundError(f"Results file not found: {path}")

    with open(path) as f:
        data = json.load(f)

    return BenchResultsSchema.model_validate(data)
