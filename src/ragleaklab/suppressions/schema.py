"""Suppression data schema.

Each suppression entry marks a specific finding as *known risk*.
It does NOT hide the finding — it changes the verdict from FAIL
to KNOWN_RISK while keeping the finding visible in all outputs.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class SuppressionType(str, Enum):
    """What kind of identifier is being suppressed."""

    test_id = "test_id"
    claim_id = "claim_id"
    doc_id = "doc_id"
    metric = "metric"


class Suppression(BaseModel):
    """A single suppression entry.

    Attributes:
        id: Unique identifier (UUID string).
        type: What kind of finding is targeted.
        value: The identifier to match (e.g. test ID, metric name).
        reason: Why this finding is being suppressed — required.
        expires_at: Mandatory expiry timestamp (ISO-8601).
        owner: Optional person or team responsible.
    """

    id: str = Field(description="UUID identifying this suppression")
    type: SuppressionType = Field(description="Kind of identifier being suppressed")
    value: str = Field(description="Identifier to match against findings")
    reason: str = Field(min_length=1, description="Why this suppression exists")
    expires_at: datetime = Field(description="When this suppression expires (ISO-8601)")
    owner: str | None = Field(default=None, description="Team or person responsible")

    @field_validator("reason")
    @classmethod
    def reason_not_blank(cls, v: str) -> str:
        if not v.strip():
            msg = "Suppression reason must not be blank"
            raise ValueError(msg)
        return v.strip()


class SuppressionFile(BaseModel):
    """Top-level schema for ``suppressions.yaml``."""

    version: str = Field(default="1.0.0", description="Schema version")
    suppressions: list[Suppression] = Field(
        default_factory=list,
        description="List of active suppressions",
    )
