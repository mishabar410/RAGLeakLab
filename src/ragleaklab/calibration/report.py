"""Generate calibration reports."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ragleaklab.calibration.fit import CalibrationResult

__all__ = ["CalibrationReport", "generate_report", "write_report"]


@dataclass
class CalibrationReport:
    """Full calibration report for a pack metric."""

    pack_name: str
    metric_name: str
    target_fpr: float
    result: CalibrationResult
    roc_table: list[dict[str, float]] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "pack_name": self.pack_name,
            "metric_name": self.metric_name,
            "target_fpr": self.target_fpr,
            "result": asdict(self.result),
            "roc_table": self.roc_table,
            "generated_at": self.generated_at,
        }


def _compute_roc_table(
    positive_scores: list[float],
    negative_scores: list[float],
    higher_is_worse: bool = True,
) -> list[dict[str, float]]:
    """Compute ROC-like table of (threshold, fpr, tpr) points."""
    if not positive_scores or not negative_scores:
        return []

    n_pos = len(positive_scores)
    n_neg = len(negative_scores)

    all_scores = sorted(set(positive_scores + negative_scores), reverse=True)
    eps = 1e-9
    thresholds = [all_scores[0] + eps, *all_scores]

    table: list[dict[str, float]] = []
    for thresh in thresholds:
        if higher_is_worse:
            tp = sum(1 for s in positive_scores if s >= thresh)
            fp = sum(1 for s in negative_scores if s >= thresh)
        else:
            tp = sum(1 for s in positive_scores if s <= thresh)
            fp = sum(1 for s in negative_scores if s <= thresh)

        fpr = fp / n_neg
        tpr = tp / n_pos

        table.append(
            {
                "threshold": round(thresh, 6),
                "fpr": round(fpr, 4),
                "tpr": round(tpr, 4),
            }
        )

    return table


def generate_report(
    pack_name: str,
    metric_name: str,
    result: CalibrationResult,
    scores: list[tuple[str, float]],
    labels: dict[str, str],
    target_fpr: float,
    higher_is_worse: bool = True,
) -> CalibrationReport:
    """Generate calibration report with ROC-like table.

    Args:
        pack_name: Name of the pack being calibrated.
        metric_name: Name of the metric being calibrated.
        result: CalibrationResult from fit_threshold().
        scores: List of (test_id, score) tuples.
        labels: Mapping test_id -> label.
        target_fpr: Target FPR used for calibration.
        higher_is_worse: Whether higher scores indicate worse outcome.

    Returns:
        CalibrationReport with full details.
    """
    # Separate scores by label
    positive_scores = [s for tid, s in scores if labels.get(tid) == "positive"]
    negative_scores = [s for tid, s in scores if labels.get(tid) == "negative"]

    roc_table = _compute_roc_table(positive_scores, negative_scores, higher_is_worse)

    return CalibrationReport(
        pack_name=pack_name,
        metric_name=metric_name,
        target_fpr=target_fpr,
        result=result,
        roc_table=roc_table,
    )


def write_report(report: CalibrationReport, out_dir: Path) -> Path:
    """Write calibration report to JSON file.

    Args:
        report: CalibrationReport to write.
        out_dir: Output directory.

    Returns:
        Path to written report file.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "calibration_report.json"

    with open(report_path, "w") as f:
        json.dump(report.to_dict(), f, indent=2)

    return report_path
