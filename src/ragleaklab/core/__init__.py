"""Core contracts and unified types for RAGLeakLab."""

from ragleaklab.core.contracts import (
    CaseResult,
    Chunk,
    ContextStats,
    Document,
    Hashes,
    MetricScore,
    ReportSummary,
    RetrievalHit,
    RunArtifact,
    Timings,
)
from ragleaklab.core.fs import (
    PathTraversalError,
    atomic_write,
    atomic_write_json,
    safe_join,
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
from ragleaklab.core.redact import redact, redact_dict

__all__ = [
    "PLUGIN_KINDS",
    "CaseResult",
    "Chunk",
    "ContextStats",
    "Document",
    "Hashes",
    "MetricScore",
    "PathTraversalError",
    "PluginError",
    "ReportSummary",
    "RetrievalHit",
    "RunArtifact",
    "Timings",
    "atomic_write",
    "atomic_write_json",
    "clear",
    "get",
    "list_plugins",
    "load_all_entry_points",
    "load_entry_points",
    "redact",
    "redact_dict",
    "register",
    "safe_join",
]
