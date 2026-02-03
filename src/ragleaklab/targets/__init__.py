"""Target adapters for testing different RAG backends."""

from ragleaklab.targets.base import Target, TargetResponse
from ragleaklab.targets.http import HttpTarget
from ragleaklab.targets.inprocess import InProcessTarget

__all__ = [
    "HttpTarget",
    "InProcessTarget",
    "Target",
    "TargetResponse",
]

# Register built-in targets as plugins
from ragleaklab.core.plugins import register as _register

_register("targets", "http", HttpTarget)
_register("targets", "inprocess", InProcessTarget)
