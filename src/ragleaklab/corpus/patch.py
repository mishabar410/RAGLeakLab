"""Patch operations for corpus updates.

Provides deterministic application of incremental changes to corpus
directories including document and claim modifications.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

__all__ = [
    "AddDocSpec",
    "PatchSpec",
    "RemoveClaimSpec",
    "apply_patch",
]


class AddDocSpec(BaseModel):
    """Specification for adding a document."""

    doc_id: str
    path: str  # Relative to patch directory
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReplaceDocSpec(BaseModel):
    """Specification for replacing a document."""

    doc_id: str
    path: str  # Relative to patch directory


class AddClaimSpec(BaseModel):
    """Specification for adding a claim."""

    doc_id: str
    claim_id: str
    text: str
    type: str = "general"
    sensitivity: str = "medium"
    tags: list[str] = Field(default_factory=list)


class RemoveClaimSpec(BaseModel):
    """Specification for removing a claim."""

    doc_id: str
    claim_id: str


class PatchSpec(BaseModel):
    """Specification for a corpus patch."""

    add_docs: list[AddDocSpec] = Field(default_factory=list)
    replace_docs: list[ReplaceDocSpec] = Field(default_factory=list)
    remove_docs: list[str] = Field(default_factory=list)
    add_claims: list[AddClaimSpec] = Field(default_factory=list)
    replace_claims_for_doc: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    remove_claims: list[RemoveClaimSpec] = Field(default_factory=list)


def load_patch(patch_dir: Path) -> PatchSpec:
    """Load patch specification from directory.

    Args:
        patch_dir: Path to patch directory containing patch.yaml or patch.json.

    Returns:
        Parsed PatchSpec.

    Raises:
        FileNotFoundError: If no patch file exists.
        ValueError: If patch file is invalid.
    """
    patch_yaml = patch_dir / "patch.yaml"
    patch_json = patch_dir / "patch.json"

    if patch_yaml.exists():
        with open(patch_yaml) as f:
            data = yaml.safe_load(f) or {}
    elif patch_json.exists():
        with open(patch_json) as f:
            data = json.load(f)
    else:
        raise FileNotFoundError(f"No patch.yaml or patch.json found in {patch_dir}")

    return PatchSpec.model_validate(data)


def _compute_corpus_hash(corpus_dir: Path) -> str:
    """Compute deterministic hash of corpus contents."""
    hasher = hashlib.sha256()

    # Hash all document files (sorted for determinism)
    for doc_path in sorted(corpus_dir.glob("*.txt")):
        hasher.update(doc_path.name.encode())
        hasher.update(doc_path.read_bytes())

    # Hash claims if present
    claims_path = corpus_dir / "claims.jsonl"
    if claims_path.exists():
        hasher.update(claims_path.read_bytes())

    # Hash composed claims if present
    composed_claims_path = corpus_dir / "composed_claims.jsonl"
    if composed_claims_path.exists():
        hasher.update(composed_claims_path.read_bytes())

    return hasher.hexdigest()


def apply_patch(
    base_corpus_dir: Path | str,
    patch_dir: Path | str,
    out_corpus_dir: Path | str,
) -> Path:
    """Apply patch to base corpus and write to output directory.

    Args:
        base_corpus_dir: Path to source corpus directory.
        patch_dir: Path to patch directory containing patch.yaml.
        out_corpus_dir: Path to output directory for patched corpus.

    Returns:
        Path to output corpus directory.

    The function is deterministic - same inputs produce identical outputs.
    JSONL files are written with entries sorted by doc_id, then claim_id.
    """
    base_corpus_dir = Path(base_corpus_dir)
    patch_dir = Path(patch_dir)
    out_corpus_dir = Path(out_corpus_dir)

    # Load patch spec
    patch = load_patch(patch_dir)

    # Create output directory
    out_corpus_dir.mkdir(parents=True, exist_ok=True)

    # Copy base corpus to output (excluding claims files which we'll regenerate)
    for item in base_corpus_dir.iterdir():
        if item.is_file():
            if item.name in ("claims.jsonl", "composed_claims.jsonl", "corpus.yaml"):
                continue  # Will regenerate these
            if item.suffix == ".txt":
                # Only copy if not in remove list
                doc_id = item.stem
                if doc_id not in patch.remove_docs:
                    shutil.copy2(item, out_corpus_dir / item.name)
            else:
                shutil.copy2(item, out_corpus_dir / item.name)

    # Apply document additions
    for add_doc in patch.add_docs:
        src_path = patch_dir / add_doc.path
        if not src_path.exists():
            raise FileNotFoundError(f"Document not found: {src_path}")
        dst_path = out_corpus_dir / f"{add_doc.doc_id}.txt"
        shutil.copy2(src_path, dst_path)

    # Apply document replacements
    for replace_doc in patch.replace_docs:
        src_path = patch_dir / replace_doc.path
        if not src_path.exists():
            raise FileNotFoundError(f"Document not found: {src_path}")
        dst_path = out_corpus_dir / f"{replace_doc.doc_id}.txt"
        shutil.copy2(src_path, dst_path)

    # Load existing claims
    claims: list[dict[str, Any]] = []
    base_claims_path = base_corpus_dir / "claims.jsonl"
    if base_claims_path.exists():
        with open(base_claims_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    claims.append(json.loads(line))

    # Process claim removals
    remove_claim_keys = {(rc.doc_id, rc.claim_id) for rc in patch.remove_claims}
    claims = [c for c in claims if (c.get("doc_id"), c.get("claim_id")) not in remove_claim_keys]

    # Process doc-level claim replacements (remove existing claims for doc first)
    for doc_id in patch.replace_claims_for_doc:
        claims = [c for c in claims if c.get("doc_id") != doc_id]

    # Add replacement claims
    for doc_id, new_claims in patch.replace_claims_for_doc.items():
        for claim_data in new_claims:
            claim = {"doc_id": doc_id, **claim_data}
            claims.append(claim)

    # Add new claims
    for add_claim in patch.add_claims:
        claims.append(add_claim.model_dump())

    # Remove claims for removed documents
    claims = [c for c in claims if c.get("doc_id") not in patch.remove_docs]

    # Sort claims deterministically by (doc_id, claim_id)
    claims.sort(key=lambda c: (c.get("doc_id", ""), c.get("claim_id", "")))

    # Write claims.jsonl
    if claims:
        with open(out_corpus_dir / "claims.jsonl", "w") as f:
            for claim in claims:
                f.write(json.dumps(claim, sort_keys=True) + "\n")

    # Copy composed_claims.jsonl if exists (not modified by patches for now)
    composed_claims_src = base_corpus_dir / "composed_claims.jsonl"
    if composed_claims_src.exists():
        shutil.copy2(composed_claims_src, out_corpus_dir / "composed_claims.jsonl")

    # Update corpus.yaml with new hash
    base_corpus_yaml = base_corpus_dir / "corpus.yaml"
    if base_corpus_yaml.exists():
        with open(base_corpus_yaml) as f:
            corpus_meta = yaml.safe_load(f) or {}
    else:
        corpus_meta = {}

    # Update hash
    new_hash = _compute_corpus_hash(out_corpus_dir)
    corpus_meta["hash"] = new_hash
    corpus_meta["patched_from"] = str(base_corpus_dir.name)

    # Update doc count
    doc_count = len(list(out_corpus_dir.glob("*.txt")))
    corpus_meta["doc_count"] = doc_count

    with open(out_corpus_dir / "corpus.yaml", "w") as f:
        yaml.safe_dump(corpus_meta, f, default_flow_style=False)

    return out_corpus_dir
