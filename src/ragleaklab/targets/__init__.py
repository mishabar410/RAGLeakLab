"""Target adapters for testing different RAG target adapters."""

from ragleaklab.targets.base import TargetResponse
from ragleaklab.targets.http import AllowlistRequiredError, HttpTarget
from ragleaklab.targets.inprocess import InProcessTarget
from ragleaklab.targets.ssrf import SSRFValidationError

__all__ = [
    "AllowlistRequiredError",
    "HttpTarget",
    "InProcessTarget",
    "SSRFValidationError",
    "TargetResponse",
]

# Register built-in targets as plugins
from ragleaklab.core.plugins import register as _register

_register("targets", "http", HttpTarget)
_register("targets", "inprocess", InProcessTarget)
