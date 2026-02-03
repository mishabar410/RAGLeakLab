"""Attack coverage analysis and reporting.

Generates coverage reports showing threat x strategy matrix and missing combinations.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from pydantic import BaseModel, Field

from ragleaklab.attacks.runner import load_cases


class CoverageReport(BaseModel):
    """Coverage report for attack test cases."""

    total_cases: int = Field(..., description="Total number of test cases")
    threats: dict[str, int] = Field(..., description="Case counts per threat type")
    strategies: dict[str, int] = Field(..., description="Case counts per strategy")
    matrix: dict[str, dict[str, int]] = Field(..., description="threat x strategy matrix counts")
    tags: dict[str, int] = Field(..., description="Case counts per tag")
    missing_combos: list[dict[str, str]] = Field(
        default_factory=list, description="Expected but missing threat x strategy combos"
    )


def compute_coverage(
    attacks_path: Path,
    expected_threats: list[str] | None = None,
    expected_strategies: list[str] | None = None,
) -> CoverageReport:
    """Compute coverage report for attack cases.

    Args:
        attacks_path: Path to attacks YAML file or directory.
        expected_threats: Expected threat types (for missing combo detection).
        expected_strategies: Expected strategies (for missing combo detection).

    Returns:
        CoverageReport with counts and matrix.
    """
    cases = load_cases(attacks_path)

    # Count per threat
    threat_counts: dict[str, int] = defaultdict(int)
    # Count per strategy
    strategy_counts: dict[str, int] = defaultdict(int)
    # Count per tag
    tag_counts: dict[str, int] = defaultdict(int)
    # Matrix: threat -> strategy -> count
    matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for case in cases:
        threat_counts[case.threat] += 1
        strategy_counts[case.strategy] += 1
        matrix[case.threat][case.strategy] += 1
        for tag in case.tags:
            tag_counts[tag] += 1

    # Convert defaultdicts to regular dicts for pydantic
    threats_dict = dict(sorted(threat_counts.items()))
    strategies_dict = dict(sorted(strategy_counts.items()))
    tags_dict = dict(sorted(tag_counts.items()))
    matrix_dict: dict[str, dict[str, int]] = {
        threat: dict(sorted(strats.items())) for threat, strats in sorted(matrix.items())
    }

    # Find missing combinations
    missing: list[dict[str, str]] = []
    if expected_threats and expected_strategies:
        for threat in expected_threats:
            for strategy in expected_strategies:
                if matrix.get(threat, {}).get(strategy, 0) == 0:
                    missing.append({"threat": threat, "strategy": strategy})

    return CoverageReport(
        total_cases=len(cases),
        threats=threats_dict,
        strategies=strategies_dict,
        matrix=matrix_dict,
        tags=tags_dict,
        missing_combos=missing,
    )


def load_expectations_from_manifest(attacks_path: Path) -> tuple[list[str], list[str]]:
    """Load expected threats from attacks manifest if present.

    Returns:
        Tuple of (expected_threats, expected_strategies).
    """
    manifest_path = attacks_path / "attacks.yaml" if attacks_path.is_dir() else None

    if manifest_path and manifest_path.exists():
        import yaml

        with open(manifest_path) as f:
            data = yaml.safe_load(f)

        threats = data.get("threat_coverage", [])
        strategies = data.get("strategy_coverage", [])
        return threats, strategies

    return [], []
