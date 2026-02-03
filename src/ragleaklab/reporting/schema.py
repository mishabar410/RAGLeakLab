"""Schema for report output.

Provides both legacy flat-format models for backward compatibility
and re-exports unified contracts from ragleaklab.core.contracts.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from ragleaklab.core.contracts import CaseResult as CoreCaseResult

# Re-export core types for users who want the new format
from ragleaklab.core.contracts import MetricScore, ReportSummary

__all__ = [
    "SCHEMA_VERSION",
    "CaseResult",
    "CoreCaseResult",
    "FailureReason",
    "MetricScore",
    "Report",
    "ReportSummary",
]

SCHEMA_VERSION = "2.0.0"


class FailureReason(BaseModel):
    """A single failure reason."""

    threat: str
    reason: str
    value: float | int | bool
    threshold: float | int | bool


class CaseResult(BaseModel):
    """Result for a single test case (legacy flat format for exports).

    This is the format used by export_junit and export_sarif.
    For the new nested format, use CoreCaseResult.
    """

    test_id: str
    threat: str
    query: str
    transformed_query: str
    retrieved_ids: list[str]
    answer: str
    canary_detected: bool = False
    canary_count: int = 0
    verbatim_score: float = 0.0


class Report(BaseModel):
    """Main report schema.

    For new code, prefer using ReportSummary from ragleaklab.core.contracts.
    """

    schema_version: str = Field(default=SCHEMA_VERSION)
    tool_version: str = Field(default="")
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    # Summary metrics
    total_cases: int
    canary_extracted: bool
    canary_count: int
    verbatim_leakage_rate: float
    membership_confidence: float

    # Verdict
    overall_pass: bool
    failures: list[FailureReason]

    # Metadata
    corpus_path: str
    attacks_path: str
    config_hash: str = Field(default="")

    def to_report_summary(self) -> ReportSummary:
        """Convert to unified ReportSummary."""
        return ReportSummary(
            schema_version=self.schema_version,
            generated_at=self.generated_at,
            overall_pass=self.overall_pass,
            aggregates={
                "total_cases": self.total_cases,
                "canary_extracted": self.canary_extracted,
                "canary_count": self.canary_count,
                "verbatim_leakage_rate": self.verbatim_leakage_rate,
                "membership_confidence": self.membership_confidence,
            },
            failures=[
                {
                    "threat": f.threat,
                    "reason": f.reason,
                    "value": f.value,
                    "threshold": f.threshold,
                }
                for f in self.failures
            ],
            meta={
                "corpus_path": self.corpus_path,
                "attacks_path": self.attacks_path,
            },
        )
