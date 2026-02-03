"""Framework-grade pydantic contracts for RAGLeakLab.

These models define the canonical data structures used across all modules:
- attacks runner returns RunArtifact
- metrics return MetricScore
- reporting collects CaseResult and produces ReportSummary
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Document(BaseModel):
    """A document in the corpus."""

    doc_id: str = Field(..., description="Unique document identifier")
    text: str = Field(..., description="Document text content")
    metadata: dict[str, Any] | None = Field(default=None, description="Optional metadata")


class Chunk(BaseModel):
    """A chunk of a document."""

    doc_id: str = Field(..., description="Parent document ID")
    chunk_id: str = Field(..., description="Chunk identifier within document")
    text: str = Field(..., description="Chunk text content")
    metadata: dict[str, Any] | None = Field(default=None, description="Optional metadata")

    @property
    def full_id(self) -> str:
        """Return full chunk identifier as doc_id:chunk_id."""
        return f"{self.doc_id}:{self.chunk_id}"


class RetrievalHit(BaseModel):
    """A single retrieval result with chunk and score."""

    chunk: Chunk = Field(..., description="Retrieved chunk")
    score: float | None = Field(default=None, description="Retrieval score (higher is better)")


class RunArtifact(BaseModel):
    """Result artifact from running a test case through RAG pipeline.

    This is the unified result type returned by attacks runner.
    """

    test_id: str = Field(..., description="ID of the test case")
    threat: str = Field(..., description="Threat type tested (canary, verbatim, membership)")
    query: str = Field(..., description="Query that was sent (possibly transformed)")
    answer: str = Field(..., description="Generated answer from RAG")
    retrieved: list[RetrievalHit] = Field(
        default_factory=list, description="Retrieved chunks with scores"
    )
    context: str = Field(..., description="Context passed to generator")
    timings: dict[str, Any] = Field(
        default_factory=dict, description="Timing information (retrieval_ms, generation_ms, etc.)"
    )
    meta: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata (strategy, original_query, etc.)"
    )

    @property
    def retrieved_ids(self) -> list[str]:
        """Return list of retrieved chunk IDs for backward compatibility."""
        return [hit.chunk.full_id for hit in self.retrieved]

    @property
    def scores(self) -> list[float]:
        """Return list of retrieval scores for backward compatibility."""
        return [hit.score if hit.score is not None else 0.0 for hit in self.retrieved]


class MetricScore(BaseModel):
    """Result from a metric evaluation.

    All metrics return this unified type for consistent aggregation.
    """

    name: str = Field(..., description="Metric name (canary, verbatim, membership, etc.)")
    value: float = Field(..., description="Metric value (interpretation varies by metric)")
    details: dict[str, Any] = Field(default_factory=dict, description="Metric-specific details")
    passed: bool | None = Field(
        default=None, description="Whether metric passed threshold (None if no threshold)"
    )


class CaseResult(BaseModel):
    """Complete result for a single test case including run and metrics."""

    run: RunArtifact = Field(..., description="The run artifact")
    scores: list[MetricScore] = Field(default_factory=list, description="Metric scores")
    passed: bool = Field(..., description="Overall pass/fail for this case")
    reasons: list[str] = Field(default_factory=list, description="Failure reasons if any")


class ReportSummary(BaseModel):
    """Summary report for an entire test run.

    This is the top-level output structure written to report.json.
    """

    schema_version: str = Field(default="2.0.0", description="Report schema version")
    tool_version: str = Field(
        default="",
        description="RAGLeakLab package version",
    )
    generated_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="ISO timestamp of report generation",
    )
    overall_pass: bool = Field(..., description="Overall pass/fail status")
    aggregates: dict[str, Any] = Field(
        default_factory=dict,
        description="Aggregate metrics (total_cases, canary_count, verbatim_rate, etc.)",
    )
    failures: list[dict[str, Any]] = Field(
        default_factory=list, description="List of failure details"
    )
    meta: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (corpus_path, attacks_path, config_hash, etc.)",
    )
