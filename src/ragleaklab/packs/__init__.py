"""Built-in attack packs for quick security audits."""

from __future__ import annotations

from pathlib import Path

# Current pack version
PACK_VERSION = "v1"

# Available packs
AVAILABLE_PACKS = [
    "canary-basic",
    "verbatim-basic",
    "membership-basic",
]


def _get_packs_dir() -> Path:
    """Get the directory containing pack files."""
    return Path(__file__).parent


def get_pack_path(pack_name: str, version: str | None = None) -> Path:
    """Get the path to a built-in pack.

    Args:
        pack_name: Name of the pack (e.g., 'canary-basic').
        version: Pack version (default: current version).

    Returns:
        Path to the pack YAML file.

    Raises:
        ValueError: If pack doesn't exist.
    """
    version = version or PACK_VERSION

    if pack_name not in AVAILABLE_PACKS:
        available = ", ".join(AVAILABLE_PACKS)
        msg = f"Unknown pack '{pack_name}'. Available: {available}"
        raise ValueError(msg)

    # Get path from package directory
    pack_file = f"{pack_name}.yaml"
    path = _get_packs_dir() / version / pack_file

    if not path.exists():
        msg = f"Pack file not found: {path}"
        raise ValueError(msg)

    return path


def list_packs(version: str | None = None) -> list[str]:
    """List available packs.

    Args:
        version: Pack version (default: current version).

    Returns:
        List of pack names.
    """
    return AVAILABLE_PACKS.copy()


def get_pack_version() -> str:
    """Get current pack version."""
    return PACK_VERSION
