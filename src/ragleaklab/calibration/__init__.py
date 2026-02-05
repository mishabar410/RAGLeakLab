"""Calibration module for pack threshold tuning.

Provides tools for calibrating pass/fail thresholds on labeled test sets
with target FPR (false positive rate) constraints.
"""

from ragleaklab.calibration.fit import CalibrationResult, fit_threshold
from ragleaklab.calibration.loader import load_labels
from ragleaklab.calibration.report import CalibrationReport, generate_report

__all__ = [
    "CalibrationReport",
    "CalibrationResult",
    "fit_threshold",
    "generate_report",
    "load_labels",
]
