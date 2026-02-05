"""Relevance hijack poisoning pack runner.

Detects corpus poisoning attacks that manipulate retrieval rankings
through keyword stuffing, bait injection, or near-duplicate patterns.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from ragleaklab.core.contracts import MetricScore, RunArtifact
from ragleaklab.metrics.integrity import (
    IntegrityMetricsResult,
    evaluate_integrity_metrics,
)
from ragleaklab.poisoning.evidence import (
    IntegritySection,
    IntegritySummary,
    RetrievalIntegrityEvidence,
)


class RelevanceHijackQuery(BaseModel):
    """A test query for relevance hijack detection."""

    query_id: str = Field(..., description="Unique query identifier")
    query: str = Field(..., description="Query text to send to retrieval")
    expected_doc_ids: list[str] = Field(
        default_factory=list, description="Expected legitimate document IDs"
    )
    description: str | None = Field(None, description="Human-readable description")


class RelevanceHijackManifest(BaseModel):
    """Manifest for relevance hijack pack."""

    name: str = Field(..., description="Pack name")
    version: str = Field(..., description="Version string")
    pack_type: str = Field(default="retrieval", description="Pack type")
    description: str | None = Field(None, description="Pack description")
    corpus: dict[str, str] = Field(default_factory=dict, description="Corpus file references")
    labels: str = Field(..., description="Labels file path")
    queries: str = Field(..., description="Queries file path")
    counts: dict[str, int] = Field(default_factory=dict, description="Document/query counts")
    thresholds: dict[str, Any] = Field(default_factory=dict, description="Pass/fail thresholds")
    expected_report_fields: list[str] = Field(
        default_factory=list, description="Expected fields in report"
    )


@dataclass
class RelevanceHijackPack:
    """Loaded relevance hijack pack with all data."""

    manifest: RelevanceHijackManifest
    queries: list[RelevanceHijackQuery]
    poison_ids: set[str]
    legit_ids: set[str]
    pack_path: Path

    def get_thresholds(self) -> dict[str, Any]:
        """Get threshold configuration."""
        return self.manifest.thresholds


@dataclass
class RelevanceHijackResult:
    """Result from running relevance hijack pack."""

    pack_id: str
    query_results: list[IntegrityMetricsResult] = field(default_factory=list)
    evidences: list[RetrievalIntegrityEvidence] = field(default_factory=list)

    # Aggregated metrics
    avg_poison_rate: float = 0.0
    avg_poison_mrr: float = 0.0
    avg_true_recall: float = 0.0
    total_queries: int = 0
    queries_with_poison: int = 0

    # Pass/fail
    overall_passed: bool = True

    def to_integrity_section(self) -> IntegritySection:
        """Convert to IntegritySection for report."""
        summary = IntegritySummary(
            total_findings=len(self.evidences),
            high_severity=sum(1 for e in self.evidences if e.severity == "high"),
            medium_severity=sum(1 for e in self.evidences if e.severity == "medium"),
            low_severity=sum(1 for e in self.evidences if e.severity == "low"),
            retrieval_poisoned=len(self.evidences),
            claim_poisoned=0,
            sentinel_triggered=0,
        )

        return IntegritySection(
            packs=self.evidences,
            integrity_summary=summary,
        )

    def to_metric_scores(self) -> list[MetricScore]:
        """Convert to MetricScore list for report aggregation."""
        scores = [
            MetricScore(
                name="integrity.retrieval.avg_poison_rate_at_k",
                value=self.avg_poison_rate,
                details={
                    "total_queries": self.total_queries,
                    "queries_with_poison": self.queries_with_poison,
                },
                passed=self.overall_passed,
            ),
            MetricScore(
                name="integrity.retrieval.avg_poison_mrr",
                value=self.avg_poison_mrr,
                details={"total_queries": self.total_queries},
                passed=self.overall_passed,
            ),
            MetricScore(
                name="integrity.retrieval.avg_true_doc_recall_at_k",
                value=self.avg_true_recall,
                details={"total_queries": self.total_queries},
                passed=self.overall_passed,
            ),
        ]
        return scores

    def to_full_evidence(self) -> list[dict]:
        """Full evidence for file output."""
        return [r.to_evidence_dict() for r in self.query_results]

    def to_summary_evidence(self) -> list[dict]:
        """Truncated evidence for report summary."""
        return [r.to_summary_dict() for r in self.query_results[:10]]


def load_relevance_hijack_pack(pack_path: Path | str) -> RelevanceHijackPack:
    """Load a relevance hijack pack from disk.

    Args:
        pack_path: Path to the pack directory.

    Returns:
        Loaded RelevanceHijackPack with all data.
    """
    pack_path = Path(pack_path)

    # Load manifest
    manifest_path = pack_path / "manifest.yaml"
    with manifest_path.open("r", encoding="utf-8") as f:
        manifest_data = yaml.safe_load(f)
    manifest = RelevanceHijackManifest(**manifest_data)

    # Load queries
    queries_path = pack_path / manifest.queries
    queries: list[RelevanceHijackQuery] = []
    with queries_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data = json.loads(line)
                queries.append(RelevanceHijackQuery(**data))

    # Load labels
    labels_path = pack_path / manifest.labels
    poison_ids: set[str] = set()
    legit_ids: set[str] = set()
    with labels_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data = json.loads(line)
                doc_id = data["doc_id"]
                if data.get("is_poison", False):
                    poison_ids.add(doc_id)
                else:
                    legit_ids.add(doc_id)

    return RelevanceHijackPack(
        manifest=manifest,
        queries=sorted(queries, key=lambda q: q.query_id),  # Deterministic order
        poison_ids=poison_ids,
        legit_ids=legit_ids,
        pack_path=pack_path,
    )


def evaluate_relevance_hijack(
    pack: RelevanceHijackPack,
    retrieved_results: dict[str, tuple[list[str], list[float]]],
    k: int = 10,
) -> RelevanceHijackResult:
    """Evaluate relevance hijack detection for all queries.

    Args:
        pack: Loaded relevance hijack pack.
        retrieved_results: Map of query_id -> (doc_ids, scores).
        k: Number of top results to consider.

    Returns:
        RelevanceHijackResult with all metrics and evidence.
    """
    thresholds = pack.get_thresholds()
    results: list[IntegrityMetricsResult] = []
    evidences: list[RetrievalIntegrityEvidence] = []

    for query in pack.queries:
        query_id = query.query_id
        expected_ids = set(query.expected_doc_ids)

        # Get retrieval results for this query
        if query_id not in retrieved_results:
            continue

        doc_ids, scores = retrieved_results[query_id]

        # Evaluate metrics
        metrics = evaluate_integrity_metrics(
            retrieved_ids=doc_ids,
            retrieved_scores=scores,
            poison_ids=pack.poison_ids,
            expected_ids=expected_ids,
            query_id=query_id,
            k=k,
            thresholds=thresholds,
        )
        results.append(metrics)

        # Create evidence if poison detected
        if metrics.poison_in_top_k:
            # Determine severity based on poison rate
            if metrics.poison_rate >= 0.3:
                severity = "high"
            elif metrics.poison_rate >= 0.1:
                severity = "medium"
            else:
                severity = "low"

            evidence = RetrievalIntegrityEvidence(
                pack_id="relevance-hijack",
                query_id=query_id,
                severity=severity,
                expected_doc_ids=list(expected_ids),
                actual_doc_ids=metrics.top_k_doc_ids,
                confidence=metrics.poison_rate,
                details={
                    "poison_rate_at_k": metrics.poison_rate,
                    "poison_mrr": metrics.poison_mrr_value,
                    "true_doc_recall_at_k": metrics.true_recall,
                    "poison_in_top_k": metrics.poison_in_top_k,
                    "top_k_scores": metrics.top_k_scores[:5],  # Truncate
                },
            )
            evidences.append(evidence)

    # Aggregate metrics
    total = len(results)
    if total > 0:
        avg_poison_rate = sum(r.poison_rate for r in results) / total
        avg_poison_mrr = sum(r.poison_mrr_value for r in results) / total
        avg_true_recall = sum(r.true_recall for r in results) / total
        queries_with_poison = sum(1 for r in results if r.poison_in_top_k)
    else:
        avg_poison_rate = 0.0
        avg_poison_mrr = 0.0
        avg_true_recall = 1.0
        queries_with_poison = 0

    # Determine overall pass/fail
    overall_passed = True
    for r in results:
        if r.poison_rate_passed is False:
            overall_passed = False
        if r.poison_mrr_passed is False:
            overall_passed = False
        if r.true_recall_passed is False:
            overall_passed = False

    return RelevanceHijackResult(
        pack_id="relevance-hijack",
        query_results=results,
        evidences=evidences,
        avg_poison_rate=avg_poison_rate,
        avg_poison_mrr=avg_poison_mrr,
        avg_true_recall=avg_true_recall,
        total_queries=total,
        queries_with_poison=queries_with_poison,
        overall_passed=overall_passed,
    )


def run_relevance_hijack_from_artifacts(
    pack: RelevanceHijackPack,
    artifacts: list[RunArtifact],
    k: int = 10,
) -> RelevanceHijackResult:
    """Run relevance hijack evaluation from RunArtifacts.

    Args:
        pack: Loaded relevance hijack pack.
        artifacts: List of run artifacts with retrieval results.
        k: Number of top results to consider.

    Returns:
        RelevanceHijackResult with all metrics and evidence.
    """
    # Build retrieved results from artifacts
    retrieved_results: dict[str, tuple[list[str], list[float]]] = {}

    for artifact in artifacts:
        # Match artifact to query by test_id
        # Strip the "rh_" prefix if present (added by pack_to_test_cases)
        query_id = artifact.test_id
        if query_id.startswith("rh_"):
            query_id = query_id[3:]  # Remove "rh_" prefix
        doc_ids = [hit.chunk.doc_id for hit in artifact.retrieved]
        scores = [hit.score or 0.0 for hit in artifact.retrieved]
        retrieved_results[query_id] = (doc_ids, scores)

    return evaluate_relevance_hijack(pack, retrieved_results, k)


def get_relevance_hijack_pack_path() -> Path:
    """Get the path to the relevance hijack pack data."""
    # First check in data/packs directory relative to project root
    # We'll use a relative import path approach
    from pathlib import Path

    # Try to find the pack in the expected location
    candidates = [
        Path(__file__).parents[4] / "data/packs/poisoning_v1/relevance_hijack",
        Path.cwd() / "data/packs/poisoning_v1/relevance_hijack",
    ]

    for candidate in candidates:
        if candidate.exists() and (candidate / "manifest.yaml").exists():
            return candidate

    msg = "Relevance hijack pack not found"
    raise FileNotFoundError(msg)


def pack_to_test_cases(pack: RelevanceHijackPack) -> list:
    """Convert pack queries to TestCase objects for the attack runner.

    This allows the pack's queries to be executed by the regular attack
    pipeline, generating retrieval results that can then be evaluated
    for relevance hijacking.

    Args:
        pack: Loaded relevance hijack pack.

    Returns:
        List of TestCase objects from the pack's queries.
    """
    from ragleaklab.attacks.schema import TestCase

    test_cases = []
    for query in pack.queries:
        test_cases.append(
            TestCase(
                test_id=f"rh_{query.query_id}",  # Prefix to identify pack queries
                threat="semantic",  # Use semantic as it's closest to retrieval evaluation
                query=query.query,
                strategy="direct_extract",
                expected=None,
                description=query.description,
                tags=["relevance-hijack", "poisoning"],
            )
        )
    return test_cases
