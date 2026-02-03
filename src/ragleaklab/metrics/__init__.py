"""Metrics module for leakage detection."""

from ragleaklab.metrics.canary import CanaryResult, detect_canary
from ragleaklab.metrics.consistency import ConsistencyResult, membership_consistency
from ragleaklab.metrics.membership import MembershipResult, membership_confidence
from ragleaklab.metrics.paraphrase import generate_paraphrases
from ragleaklab.metrics.verbatim import VerbatimResult, verbatim_overlap
from ragleaklab.metrics.verdict import Verdict, apply_thresholds

__all__ = [
    "CanaryResult",
    "ConsistencyResult",
    "MembershipResult",
    "VerbatimResult",
    "Verdict",
    "apply_thresholds",
    "detect_canary",
    "generate_paraphrases",
    "membership_confidence",
    "membership_consistency",
    "verbatim_overlap",
]

# Register built-in metrics as plugins
from ragleaklab.core.plugins import register as _register

_register("metrics", "canary", detect_canary)
_register("metrics", "verbatim", verbatim_overlap)
_register("metrics", "membership", membership_confidence)
_register("metrics", "consistency", membership_consistency)
_register("metrics", "paraphrase", generate_paraphrases)
