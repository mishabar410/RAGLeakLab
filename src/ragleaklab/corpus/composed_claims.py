"""Composed claims layer for cross-document leakage detection.

Provides models and utilities for working with composed claims that
represent facts derivable only by combining information from multiple documents.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

__all__ = [
    "ClaimComponent",
    "ComposedClaim",
    "load_composed_claims",
]

logger = logging.getLogger(__name__)


class ClaimComponent(BaseModel):
    """A component of a composed claim from a single document."""

    doc_id: str = Field(..., description="ID of the source document")
    claim_id: str | None = Field(default=None, description="Optional reference to atomic claim")
    fragment: str = Field(..., description="The piece of information from this doc")


class ComposedClaim(BaseModel):
    """A composed claim requiring multiple documents to derive.

    Composed claims represent facts that can only be known by correlating
    information from multiple private documents. They are used to measure
    cross-document leakage in RAG systems.
    """

    claim_id: str = Field(..., description="Unique identifier (CC prefix)")
    text: str = Field(..., description="The final composed claim form")
    type: str = Field(default="composed", description="Claim type")
    sensitivity: Literal["high", "medium", "low"] = Field(
        default="high", description="Sensitivity level"
    )
    components: list[ClaimComponent] = Field(
        ..., description="Component facts from different documents"
    )
    tags: list[str] = Field(default_factory=list, description="Optional tags")

    @field_validator("components")
    @classmethod
    def validate_multiple_docs(cls, v: list[ClaimComponent]) -> list[ClaimComponent]:
        """Ensure components span at least 2 distinct documents."""
        if len(v) < 2:
            raise ValueError("Composed claims must have at least 2 components")
        doc_ids = {c.doc_id for c in v}
        if len(doc_ids) < 2:
            raise ValueError("Composed claims must span at least 2 distinct documents")
        return v

    def get_required_doc_ids(self) -> list[str]:
        """Get unique doc_ids required for this composed claim."""
        return list({c.doc_id for c in self.components})


def load_composed_claims(path: Path | str) -> list[ComposedClaim]:
    """Load composed claims from a JSONL file.

    Args:
        path: Path to composed_claims.jsonl file.

    Returns:
        List of ComposedClaim objects.

    Raises:
        FileNotFoundError: If claims file doesn't exist.
        ValueError: If claims file contains invalid JSON.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Composed claims file not found: {path}")

    claims: list[ComposedClaim] = []
    with open(path) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                claims.append(ComposedClaim.model_validate(data))
            except json.JSONDecodeError as e:
                logger.warning("Invalid JSON on line %d: %s", line_num, e)
            except Exception as e:
                logger.warning("Failed to parse composed claim on line %d: %s", line_num, e)

    logger.info("Loaded %d composed claims from %s", len(claims), path)
    return claims
