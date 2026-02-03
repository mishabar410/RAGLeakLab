"""Manifest loading and validation utilities."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel

from ragleaklab.assets.hash import compute_tree_hash
from ragleaklab.assets.schema import AttacksManifest, CorpusManifest, PackManifest


def _load_manifest[T: BaseModel](path: Path, model: type[T]) -> T:
    """Load and validate a YAML manifest file.

    Args:
        path: Path to manifest YAML file.
        model: Pydantic model class for validation.

    Returns:
        Validated manifest instance.

    Raises:
        FileNotFoundError: If manifest file doesn't exist.
        pydantic.ValidationError: If manifest is invalid.
    """
    if not path.exists():
        msg = f"Manifest not found: {path}"
        raise FileNotFoundError(msg)

    with path.open() as f:
        data = yaml.safe_load(f)

    return model.model_validate(data)


def load_corpus_manifest(path: Path) -> CorpusManifest:
    """Load a corpus manifest from YAML file.

    Args:
        path: Path to corpus.yaml file.

    Returns:
        Validated CorpusManifest.
    """
    return _load_manifest(path, CorpusManifest)


def load_attacks_manifest(path: Path) -> AttacksManifest:
    """Load an attacks manifest from YAML file.

    Args:
        path: Path to attacks.yaml file.

    Returns:
        Validated AttacksManifest.
    """
    return _load_manifest(path, AttacksManifest)


def load_pack_manifest(path: Path) -> PackManifest:
    """Load a pack manifest from YAML file.

    Args:
        path: Path to pack.yaml file.

    Returns:
        Validated PackManifest.
    """
    return _load_manifest(path, PackManifest)


def validate_hash(manifest: CorpusManifest | AttacksManifest, base_path: Path) -> bool:
    """Validate that manifest hash matches actual file tree.

    Args:
        manifest: Manifest with hash field.
        base_path: Directory containing the assets.

    Returns:
        True if hash matches, False otherwise.
    """
    actual_hash = compute_tree_hash(base_path)
    return manifest.hash == actual_hash
