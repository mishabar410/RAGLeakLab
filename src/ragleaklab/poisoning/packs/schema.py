"""Poisoning pack schema definitions.

These models define the structure for poisoning test packs,
analogous to attack packs but focused on integrity threats.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from ragleaklab.poisoning.evidence import SentinelType, SeverityLevel


class PoisoningTestCase(BaseModel):
    """A test case for poisoning/integrity detection.

    Each case defines expectations that can be verified against
    RAG system responses to detect corpus manipulation.
    """

    test_id: str = Field(..., description="Unique test case identifier")
    pack_type: Literal["retrieval", "claim", "sentinel"] = Field(
        ..., description="Type of integrity check"
    )
    query: str = Field(..., description="Query to send to RAG system")
    description: str | None = Field(None, description="Human-readable description")

    # Retrieval integrity fields
    expected_doc_ids: list[str] = Field(
        default_factory=list,
        description="Expected document IDs in retrieval (for retrieval type)",
    )
    disallowed_doc_ids: list[str] = Field(
        default_factory=list,
        description="Document IDs that should NOT appear in retrieval",
    )

    # Claim integrity fields
    expected_claim: str | None = Field(
        None, description="Expected claim/answer content (for claim type)"
    )
    forbidden_claim: str | None = Field(None, description="Claim content that indicates poisoning")

    # Sentinel integrity fields
    sentinel_type: SentinelType | None = Field(
        None, description="Type of sentinel/backdoor (for sentinel type)"
    )
    trigger_phrase: str | None = Field(None, description="Phrase that triggers backdoor behavior")

    # Common fields
    severity: SeverityLevel = Field("medium", description="Severity if violation found")
    tags: list[str] = Field(default_factory=list, description="Categorization tags")
    meta: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class PoisoningPackManifest(BaseModel):
    """Manifest for a poisoning detection pack.

    Links test cases with metadata for reproducible integrity testing.
    """

    name: str = Field(..., description="Pack name (e.g., 'integrity-basic')")
    version: str = Field(..., description="Semantic version")
    pack_type: Literal["retrieval", "claim", "sentinel", "mixed"] = Field(
        ..., description="Primary type of integrity checks"
    )
    description: str | None = Field(None, description="Pack description")
    test_count: int = Field(..., ge=0, description="Number of test cases")
    expected_report_fields: list[str] = Field(
        default_factory=list, description="Required fields in generated reports"
    )
