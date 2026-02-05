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
    "relevance-hijack",
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
        Path to the pack directory or YAML file.

    Raises:
        ValueError: If pack doesn't exist.
    """
    version = version or PACK_VERSION

    if pack_name not in AVAILABLE_POISONING_PACKS:
        available = ", ".join(AVAILABLE_POISONING_PACKS)
        msg = f"Unknown poisoning pack '{pack_name}'. Available: {available}"
        raise ValueError(msg)

    # Special handling for relevance-hijack (uses data/packs structure)
    if pack_name == "relevance-hijack":
        # Find project root (go up from src/ragleaklab/poisoning/packs/)
        project_root = _get_packs_dir().parent.parent.parent.parent
        path = project_root / "data" / "packs" / "poisoning_v1" / "relevance_hijack"
        if not path.exists():
            msg = f"Relevance hijack pack not found: {path}"
            raise ValueError(msg)
        return path

    # Get path from package directory for v1 YAML packs
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
