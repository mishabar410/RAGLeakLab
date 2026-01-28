"""Schema for report output."""

from datetime import datetime

from pydantic import BaseModel, Field

SCHEMA_VERSION = "1.0.0"


class FailureReason(BaseModel):
    """A single failure reason."""

    threat: str
    reason: str
    value: float | int | bool
    threshold: float | int | bool


class CaseResult(BaseModel):
    """Result for a single test case."""

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
    """Main report schema."""

    schema_version: str = Field(default=SCHEMA_VERSION)
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
