"""Claims layer for semantic leakage detection.

Provides models and utilities for working with claim annotations
that define sensitive facts within private documents.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

__all__ = [
    "Claim",
    "index_claims_by_doc",
    "load_claims",
]

logger = logging.getLogger(__name__)


class Claim(BaseModel):
    """A sensitive fact or claim from a document.

    Claims represent discrete pieces of information that should not
    leak from the RAG system. They are used to measure semantic leakage.
    """

    doc_id: str = Field(..., description="ID of the source document")
    claim_id: str = Field(..., description="Unique identifier for this claim")
    text: str = Field(..., description="The sensitive fact/claim text")
    type: str = Field(default="general", description="Claim category")
    sensitivity: Literal["high", "medium", "low"] = Field(
        default="medium", description="Sensitivity level"
    )
    tags: list[str] = Field(default_factory=list, description="Optional tags")


def load_claims(path: Path | str) -> list[Claim]:
    """Load claims from a JSONL file.

    Args:
        path: Path to claims.jsonl file.

    Returns:
        List of Claim objects.

    Raises:
        FileNotFoundError: If claims file doesn't exist.
        ValueError: If claims file contains invalid JSON.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Claims file not found: {path}")

    claims: list[Claim] = []
    with open(path) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                claims.append(Claim.model_validate(data))
            except json.JSONDecodeError as e:
                logger.warning("Invalid JSON on line %d: %s", line_num, e)
            except (ValueError, TypeError) as e:
                logger.warning("Failed to parse claim on line %d: %s", line_num, e)

    logger.info("Loaded %d claims from %s", len(claims), path)
    return claims


def index_claims_by_doc(claims: list[Claim]) -> dict[str, list[Claim]]:
    """Index claims by document ID.

    Args:
        claims: List of claims to index.

    Returns:
        Dictionary mapping doc_id to list of claims for that document.
    """
    index: dict[str, list[Claim]] = defaultdict(list)
    for claim in claims:
        index[claim.doc_id].append(claim)
    return dict(index)
