"""Pydantic schemas for asset manifests."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CorpusManifest(BaseModel):
    """Manifest for a corpus directory.

    Describes the contents and version of a document corpus.
    """

    name: str = Field(..., description="Unique corpus identifier")
    version: str = Field(..., description="Semantic version (e.g., '1.0.0')")
    seed: int | None = Field(None, description="Random seed if synthetically generated")
    doc_count: int = Field(..., ge=0, description="Number of documents in corpus")
    claims_supported: list[str] = Field(
        default_factory=list,
        description="Claim types present (e.g., EMAIL, PHONE, ACCOUNT_ID)",
    )
    hash: str = Field(..., description="SHA-256 hash of corpus file tree")


class AttacksManifest(BaseModel):
    """Manifest for an attacks directory.

    Describes attack test case files and their coverage.
    """

    name: str = Field(..., description="Unique attacks set identifier")
    version: str = Field(..., description="Semantic version")
    threat_coverage: list[str] = Field(
        ..., description="Threat types covered (e.g., canary, verbatim)"
    )
    case_count: int = Field(..., ge=0, description="Total number of test cases")
    hash: str = Field(..., description="SHA-256 hash of attacks file tree")


class PackManifest(BaseModel):
    """Manifest for an attack pack.

    Links corpus, attacks, and configuration for reproducible runs.
    """

    name: str = Field(..., description="Pack name (e.g., canary-basic)")
    version: str = Field(..., description="Semantic version")
    corpus_ref: str | None = Field(
        None, description="Corpus reference (e.g., 'corpus_public@1.0.0')"
    )
    attacks_ref: str = Field(..., description="Attacks reference (e.g., 'canary-basic@1.0.0')")
    thresholds_ref: str | None = Field(None, description="Thresholds config reference")
    expected_report_fields: list[str] = Field(
        default_factory=list, description="Required fields in generated reports"
    )
