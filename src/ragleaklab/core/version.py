"""Version utilities for RAGLeakLab."""

from __future__ import annotations

import hashlib
from importlib.metadata import PackageNotFoundError, version


def get_tool_version() -> str:
    """Get the installed RAGLeakLab version.

    Returns:
        Version string, or 'dev' if not installed as package.
    """
    try:
        return version("ragleaklab")
    except PackageNotFoundError:
        return "dev"


def compute_config_hash(**settings: object) -> str:
    """Compute a hash of runtime settings for reproducibility.

    Args:
        **settings: Key-value pairs of configuration settings.

    Returns:
        Short hash string (first 12 chars of SHA256).
    """
    # Sort keys for deterministic ordering
    items = sorted((k, str(v)) for k, v in settings.items())
    content = ";".join(f"{k}={v}" for k, v in items)
    return hashlib.sha256(content.encode()).hexdigest()[:12]
