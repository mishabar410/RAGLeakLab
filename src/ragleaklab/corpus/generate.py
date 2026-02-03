"""Synthetic corpus and claims generator.

Generates deterministic test data for semantic leakage testing.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from faker import Faker

__all__ = [
    "generate_synthetic_corpus",
]


# Claim types and templates for generation
CLAIM_TYPES = [
    ("EMAIL", "Contact email is {email}"),
    ("PHONE", "Phone number is {phone}"),
    ("ACCOUNT_ID", "Account ID is {account_id}"),
    ("SECRET_CODEWORD", "Secret codeword is {codeword}"),
    ("INTERNAL_PROJECT", "Project codename is {project}"),
]

# Project codename components for deterministic generation
PROJECT_ADJECTIVES = [
    "Phoenix",
    "Midnight",
    "Thunder",
    "Crystal",
    "Shadow",
    "Golden",
    "Silver",
    "Iron",
    "Crimson",
    "Azure",
]

PROJECT_NOUNS = [
    "Dragon",
    "Eagle",
    "Tiger",
    "Falcon",
    "Wolf",
    "Lion",
    "Hawk",
    "Bear",
    "Shark",
    "Cobra",
]


def _compute_file_hash(path: Path) -> str:
    """Compute SHA256 hash of file contents."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()[:16]


def _generate_project_name(fake: Faker) -> str:
    """Generate a project codename."""
    adj = fake.random_element(PROJECT_ADJECTIVES)
    noun = fake.random_element(PROJECT_NOUNS)
    return f"{adj}-{noun}"


def _generate_account_id(fake: Faker) -> str:
    """Generate an account ID."""
    prefix = fake.random_element(["ACC", "USR", "ORG", "ENT"])
    number = fake.random_int(min=100000, max=999999)
    return f"{prefix}-{number}"


def _generate_codeword(fake: Faker) -> str:
    """Generate a secret codeword."""
    words = [fake.word().upper() for _ in range(3)]
    return "-".join(words)


def generate_synthetic_corpus(
    out_dir: Path | str,
    seed: int,
    n_docs: int = 10,
    claims_per_doc: int = 3,
    include_pii: bool = True,
) -> dict[str, Any]:
    """Generate a synthetic corpus with claims.

    Args:
        out_dir: Output directory for generated files.
        seed: Random seed for deterministic generation.
        n_docs: Number of documents to generate.
        claims_per_doc: Number of claims per document.
        include_pii: Whether to include PII-type claims (EMAIL, PHONE).

    Returns:
        Manifest dict with generation parameters.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Initialize Faker with seed
    fake = Faker()
    Faker.seed(seed)

    all_claims: list[dict[str, Any]] = []
    claim_counter = 0

    # Filter claim types based on include_pii
    available_types = (
        CLAIM_TYPES
        if include_pii
        else [ct for ct in CLAIM_TYPES if ct[0] not in ("EMAIL", "PHONE")]
    )

    for doc_idx in range(n_docs):
        doc_id = f"doc_{doc_idx:04d}"

        # Generate document content
        paragraphs = [fake.paragraph(nb_sentences=5) for _ in range(3)]

        # Generate claims for this document
        doc_claims: list[dict[str, Any]] = []
        for _ in range(claims_per_doc):
            claim_type, template = fake.random_element(available_types)

            # Generate claim value based on type
            if claim_type == "EMAIL":
                value = fake.email()
                text = template.format(email=value)
            elif claim_type == "PHONE":
                value = fake.phone_number()
                text = template.format(phone=value)
            elif claim_type == "ACCOUNT_ID":
                value = _generate_account_id(fake)
                text = template.format(account_id=value)
            elif claim_type == "SECRET_CODEWORD":
                value = _generate_codeword(fake)
                text = template.format(codeword=value)
            elif claim_type == "INTERNAL_PROJECT":
                value = _generate_project_name(fake)
                text = template.format(project=value)
            else:
                value = fake.word()
                text = f"Secret: {value}"

            claim_counter += 1
            claim = {
                "doc_id": doc_id,
                "claim_id": f"C{claim_counter:04d}",
                "text": text,
                "type": claim_type,
                "sensitivity": fake.random_element(["high", "medium", "low"]),
                "tags": [claim_type.lower(), f"doc{doc_idx}"],
            }
            doc_claims.append(claim)
            all_claims.append(claim)

            # Inject claim into a random paragraph
            inject_idx = fake.random_int(min=0, max=len(paragraphs) - 1)
            paragraphs[inject_idx] += f" {text}."

        # Write document
        doc_path = out_dir / f"{doc_id}.txt"
        doc_path.write_text("\n\n".join(paragraphs), encoding="utf-8")

    # Write claims.jsonl
    claims_path = out_dir / "claims.jsonl"
    with open(claims_path, "w", encoding="utf-8") as f:
        for claim in all_claims:
            f.write(json.dumps(claim) + "\n")

    # Compute corpus hash
    corpus_hash = _compute_file_hash(claims_path)

    # Write manifest
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "seed": seed,
        "n_docs": n_docs,
        "claims_per_doc": claims_per_doc,
        "include_pii": include_pii,
        "total_claims": len(all_claims),
        "corpus_hash": corpus_hash,
    }

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return manifest
