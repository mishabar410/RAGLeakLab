"""Built-in poisoning packs for integrity audits.

Poisoning packs test for corpus manipulation and backdoor attacks.
"""

from __future__ import annotations

from pathlib import Path

# Current pack version
PACK_VERSION = "v1"

# Available poisoning packs
AVAILABLE_POISONING_PACKS = [
    "integrity-dummy",
]


def _get_packs_dir() -> Path:
    """Get the directory containing poisoning pack files."""
    return Path(__file__).parent


def get_poisoning_pack_path(pack_name: str, version: str | None = None) -> Path:
    """Get the path to a built-in poisoning pack.

    Args:
        pack_name: Name of the pack (e.g., 'integrity-dummy').
        version: Pack version (default: current version).

    Returns:
        Path to the pack YAML file.

    Raises:
        ValueError: If pack doesn't exist.
    """
    version = version or PACK_VERSION

    if pack_name not in AVAILABLE_POISONING_PACKS:
        available = ", ".join(AVAILABLE_POISONING_PACKS)
        msg = f"Unknown poisoning pack '{pack_name}'. Available: {available}"
        raise ValueError(msg)

    # Get path from package directory
    pack_file = f"{pack_name}.yaml"
    path = _get_packs_dir() / version / pack_file

    if not path.exists():
        msg = f"Poisoning pack file not found: {path}"
        raise ValueError(msg)

    return path


def list_poisoning_packs(version: str | None = None) -> list[str]:
    """List available poisoning packs.

    Args:
        version: Pack version (default: current version).

    Returns:
        List of pack names.
    """
    return AVAILABLE_POISONING_PACKS.copy()


def get_poisoning_pack_version() -> str:
    """Get current poisoning pack version."""
    return PACK_VERSION
