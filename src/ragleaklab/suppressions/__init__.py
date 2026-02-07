"""Suppression mechanism for controlled risk acceptance.

Allows teams to temporarily suppress specific findings without
hiding real risk from reports and CI pipelines.
"""

from ragleaklab.suppressions.loader import load_suppressions, validate_suppressions
from ragleaklab.suppressions.schema import Suppression, SuppressionFile, SuppressionType

__all__ = [
    "Suppression",
    "SuppressionFile",
    "SuppressionType",
    "load_suppressions",
    "validate_suppressions",
]
