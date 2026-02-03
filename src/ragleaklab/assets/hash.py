"""Deterministic file tree hashing for asset integrity."""

from __future__ import annotations

import hashlib
from pathlib import Path

# Patterns to exclude from hash computation
EXCLUDE_PATTERNS = {
    "__pycache__",
    ".pyc",
    ".git",
    ".DS_Store",
    "out",
    ".ruff_cache",
    ".pytest_cache",
}


def _should_exclude(path: Path) -> bool:
    """Check if path should be excluded from hashing."""
    for pattern in EXCLUDE_PATTERNS:
        if pattern in path.parts or path.name.endswith(pattern):
            return True
    return False


def compute_tree_hash(directory: Path, exclude_manifest: bool = True) -> str:
    """Compute deterministic SHA-256 hash of a directory tree.

    Args:
        directory: Root directory to hash.
        exclude_manifest: If True, exclude corpus.yaml/attacks.yaml/pack.yaml from hash.

    Returns:
        Hex-encoded SHA-256 hash string.

    The hash is computed by:
    1. Collecting all files (excluding patterns like __pycache__, .git, out/)
    2. Sorting files by relative path for determinism
    3. For each file: hash(relative_path + file_contents)
    4. Combine all file hashes into final hash
    """
    if not directory.is_dir():
        msg = f"Not a directory: {directory}"
        raise ValueError(msg)

    manifest_names = {"corpus.yaml", "attacks.yaml", "pack.yaml"}
    files: list[tuple[str, Path]] = []

    for path in directory.rglob("*"):
        if not path.is_file():
            continue
        if _should_exclude(path):
            continue
        if exclude_manifest and path.name in manifest_names:
            continue

        rel_path = str(path.relative_to(directory))
        files.append((rel_path, path))

    # Sort by relative path for determinism
    files.sort(key=lambda x: x[0])

    # Compute combined hash
    hasher = hashlib.sha256()
    for rel_path, file_path in files:
        # Include path in hash to detect renames
        hasher.update(rel_path.encode("utf-8"))
        hasher.update(file_path.read_bytes())

    return hasher.hexdigest()
