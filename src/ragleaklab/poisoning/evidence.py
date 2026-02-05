"""Integrity evidence types for corpus poisoning detection.

These models define the canonical data structures for integrity threats:
- RetrievalIntegrityEvidence: poisoned retrieval behavior
- ClaimIntegrityEvidence: manipulated claim generation
- SentinelIntegrityEvidence: sentinel trigger detection
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

SeverityLevel = Literal["high", "medium", "low"]
SentinelType = Literal["suffix", "trigger", "backdoor"]


class RetrievalIntegrityEvidence(BaseModel):
    """Evidence of poisoned retrieval behavior.

    Detects when retrieval results are manipulated through corpus poisoning,
    such as injecting documents that rank higher than expected for certain queries.
    """

    pack_id: str = Field(..., description="Pack that generated this evidence")
    query_id: str = Field(..., description="Query ID within the pack")
    severity: SeverityLevel = Field(..., description="Severity level")
    expected_doc_ids: list[str] = Field(
        default_factory=list, description="Expected document IDs in retrieval"
    )
    actual_doc_ids: list[str] = Field(
        default_factory=list, description="Actual document IDs retrieved"
    )
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence score (0-1)")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional evidence details")


class ClaimIntegrityEvidence(BaseModel):
    """Evidence of poisoned claim generation.

    Detects when generated claims are manipulated through corpus poisoning,
    such as injecting false information that appears in the output.
    """

    pack_id: str = Field(..., description="Pack that generated this evidence")
    query_id: str = Field(..., description="Query ID within the pack")
    severity: SeverityLevel = Field(..., description="Severity level")
    expected_claim_ids: list[str] = Field(
        default_factory=list, description="Expected true claim IDs"
    )
    matched_true_claims: list[str] = Field(
        default_factory=list, description="True claim IDs found in output"
    )
    matched_poison_claims: list[str] = Field(
        default_factory=list, description="Poison claim IDs found in output"
    )
    contradiction_hits: int = Field(
        default=0, ge=0, description="Number of contradictions detected"
    )
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence score")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional details")


class SentinelIntegrityEvidence(BaseModel):
    """Evidence of sentinel trigger detection.

    Detects backdoor triggers planted in the corpus that activate specific
    behaviors when certain patterns are present in queries.
    """

    pack_id: str = Field(..., description="Pack that generated this evidence")
    query_id: str = Field(..., description="Query ID within the pack")
    severity: SeverityLevel = Field(..., description="Severity level")
    sentinel_type: SentinelType = Field(..., description="Type of sentinel trigger")
    triggered: bool = Field(default=False, description="Whether the trigger activated")
    expected_behavior: str = Field(..., description="Expected system behavior")
    actual_behavior: str = Field(..., description="Actual observed behavior")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional evidence details")


# Union type for any integrity evidence
IntegrityEvidence = RetrievalIntegrityEvidence | ClaimIntegrityEvidence | SentinelIntegrityEvidence


class IntegritySummary(BaseModel):
    """Summary statistics for integrity assessment."""

    total_findings: int = Field(default=0, ge=0, description="Total number of findings")
    high_severity: int = Field(default=0, ge=0, description="High severity findings count")
    medium_severity: int = Field(default=0, ge=0, description="Medium severity findings count")
    low_severity: int = Field(default=0, ge=0, description="Low severity findings count")
    retrieval_poisoned: int = Field(
        default=0, ge=0, description="Retrieval poisoning findings count"
    )
    claim_poisoned: int = Field(default=0, ge=0, description="Claim poisoning findings count")
    sentinel_triggered: int = Field(default=0, ge=0, description="Sentinel trigger findings count")


class IntegritySection(BaseModel):
    """Integrity section for reports.

    Contains all integrity evidence and summary statistics.
    When present in a report, indicates that integrity testing was performed.
    """

    packs: list[RetrievalIntegrityEvidence | ClaimIntegrityEvidence | SentinelIntegrityEvidence] = (
        Field(default_factory=list, description="List of integrity evidence items")
    )
    integrity_summary: IntegritySummary = Field(
        default_factory=IntegritySummary, description="Summary of integrity findings"
    )

    def compute_summary(self) -> IntegritySummary:
        """Compute summary statistics from packs."""
        summary = IntegritySummary(total_findings=len(self.packs))

        for evidence in self.packs:
            # Count by severity
            if evidence.severity == "high":
                summary.high_severity += 1
            elif evidence.severity == "medium":
                summary.medium_severity += 1
            elif evidence.severity == "low":
                summary.low_severity += 1

            # Count by type
            if isinstance(evidence, RetrievalIntegrityEvidence):
                summary.retrieval_poisoned += 1
            elif isinstance(evidence, ClaimIntegrityEvidence):
                summary.claim_poisoned += 1
            elif isinstance(evidence, SentinelIntegrityEvidence):
                summary.sentinel_triggered += 1

        return summary

    def sorted_packs(
        self,
    ) -> list[RetrievalIntegrityEvidence | ClaimIntegrityEvidence | SentinelIntegrityEvidence]:
        """Return packs sorted deterministically: severity → pack_id → query_id."""
        severity_order = {"high": 0, "medium": 1, "low": 2}
        return sorted(
            self.packs,
            key=lambda e: (severity_order.get(e.severity, 99), e.pack_id, e.query_id),
        )
