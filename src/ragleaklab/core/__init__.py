"""Core contracts and unified types for RAGLeakLab."""

from ragleaklab.core.contracts import (
    CaseResult,
    Chunk,
    Document,
    MetricScore,
    ReportSummary,
    RetrievalHit,
    RunArtifact,
)
from ragleaklab.core.plugins import (
    PLUGIN_KINDS,
    PluginError,
    clear,
    get,
    list_plugins,
    load_all_entry_points,
    load_entry_points,
    register,
)

__all__ = [
    "PLUGIN_KINDS",
    "CaseResult",
    "Chunk",
    "Document",
    "MetricScore",
    "PluginError",
    "ReportSummary",
    "RetrievalHit",
    "RunArtifact",
    "clear",
    "get",
    "list_plugins",
    "load_all_entry_points",
    "load_entry_points",
    "register",
]
