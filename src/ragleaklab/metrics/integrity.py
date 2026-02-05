"""Integrity metrics for corpus poisoning detection.

Provides metrics to detect retrieval manipulation attacks:
- poison_rate_at_k: Fraction of top-k results that are poison
- poison_mrr: Mean Reciprocal Rank of first poison document
- true_doc_recall_at_k: Fraction of expected docs in top-k
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ragleaklab.core.contracts import MetricScore

if TYPE_CHECKING:
    pass

__all__ = [
    "IntegrityMetricsResult",
    "poison_mrr",
    "poison_rate_at_k",
    "true_doc_recall_at_k",
]


def poison_rate_at_k(
    retrieved_ids: list[str],
    poison_ids: set[str],
    k: int = 10,
) -> float:
    """Calculate fraction of top-k results that are poison documents.

    Args:
        retrieved_ids: Ordered list of retrieved document IDs (highest first).
        poison_ids: Set of known poison document IDs.
        k: Number of top results to consider.

    Returns:
        Float in [0, 1] representing poison fraction in top-k.
    """
    if not retrieved_ids or k <= 0:
        return 0.0

    top_k = retrieved_ids[:k]
    poison_count = sum(1 for doc_id in top_k if doc_id in poison_ids)
    return poison_count / len(top_k)


def poison_mrr(
    retrieved_ids: list[str],
    poison_ids: set[str],
) -> float:
    """Calculate Mean Reciprocal Rank of first poison document.

    MRR = 1/rank of first poison doc, or 0 if no poison docs found.
    Higher MRR means poison docs appear earlier (worse for integrity).

    Args:
        retrieved_ids: Ordered list of retrieved document IDs (highest first).
        poison_ids: Set of known poison document IDs.

    Returns:
        Float in [0, 1] representing MRR of first poison doc.
    """
    if not retrieved_ids:
        return 0.0

    for rank, doc_id in enumerate(retrieved_ids, start=1):
        if doc_id in poison_ids:
            return 1.0 / rank

    return 0.0


def true_doc_recall_at_k(
    retrieved_ids: list[str],
    expected_ids: set[str],
    k: int = 10,
) -> float:
    """Calculate fraction of expected documents appearing in top-k.

    Args:
        retrieved_ids: Ordered list of retrieved document IDs (highest first).
        expected_ids: Set of expected legitimate document IDs.
        k: Number of top results to consider.

    Returns:
        Float in [0, 1] representing recall of expected docs in top-k.
    """
    if not expected_ids:
        return 1.0  # No expected docs = vacuously true

    if not retrieved_ids or k <= 0:
        return 0.0

    top_k = set(retrieved_ids[:k])
    found = len(expected_ids & top_k)
    return found / len(expected_ids)


@dataclass
class IntegrityMetricsResult:
    """Result of integrity metrics evaluation for a single query."""

    query_id: str
    poison_rate: float
    poison_mrr_value: float
    true_recall: float
    top_k_doc_ids: list[str] = field(default_factory=list)
    top_k_scores: list[float] = field(default_factory=list)
    poison_in_top_k: list[str] = field(default_factory=list)
    expected_doc_ids: list[str] = field(default_factory=list)

    # Threshold evaluation
    poison_rate_passed: bool | None = None
    poison_mrr_passed: bool | None = None
    true_recall_passed: bool | None = None

    def to_metric_scores(self) -> list[MetricScore]:
        """Convert to list of MetricScore for reporting."""
        return [
            MetricScore(
                name="integrity.retrieval.poison_rate_at_k",
                value=self.poison_rate,
                details={
                    "query_id": self.query_id,
                    "k": len(self.top_k_doc_ids),
                    "poison_in_top_k": self.poison_in_top_k[:5],  # Truncate for summary
                },
                passed=self.poison_rate_passed,
            ),
            MetricScore(
                name="integrity.retrieval.poison_mrr",
                value=self.poison_mrr_value,
                details={
                    "query_id": self.query_id,
                    "first_poison_rank": (
                        int(1.0 / self.poison_mrr_value) if self.poison_mrr_value > 0 else None
                    ),
                },
                passed=self.poison_mrr_passed,
            ),
            MetricScore(
                name="integrity.retrieval.true_doc_recall_at_k",
                value=self.true_recall,
                details={
                    "query_id": self.query_id,
                    "expected_doc_ids": self.expected_doc_ids,
                    "k": len(self.top_k_doc_ids),
                },
                passed=self.true_recall_passed,
            ),
        ]

    def to_evidence_dict(self) -> dict:
        """Convert to full evidence dict for file output."""
        return {
            "query_id": self.query_id,
            "poison_rate_at_k": self.poison_rate,
            "poison_mrr": self.poison_mrr_value,
            "true_doc_recall_at_k": self.true_recall,
            "top_k_doc_ids": self.top_k_doc_ids,
            "top_k_scores": self.top_k_scores,
            "poison_in_top_k": self.poison_in_top_k,
            "expected_doc_ids": self.expected_doc_ids,
            "passed": {
                "poison_rate": self.poison_rate_passed,
                "poison_mrr": self.poison_mrr_passed,
                "true_recall": self.true_recall_passed,
            },
        }

    def to_summary_dict(self) -> dict:
        """Convert to truncated summary dict for report."""
        return {
            "query_id": self.query_id,
            "poison_rate_at_k": self.poison_rate,
            "poison_mrr": self.poison_mrr_value,
            "true_doc_recall_at_k": self.true_recall,
            "top_k_doc_ids": self.top_k_doc_ids[:5],  # Truncate
            "poison_in_top_k": self.poison_in_top_k[:3],  # Truncate
        }


def evaluate_integrity_metrics(
    retrieved_ids: list[str],
    retrieved_scores: list[float],
    poison_ids: set[str],
    expected_ids: set[str],
    query_id: str,
    k: int = 10,
    thresholds: dict | None = None,
) -> IntegrityMetricsResult:
    """Evaluate all integrity metrics for a single query.

    Args:
        retrieved_ids: Ordered list of retrieved document IDs.
        retrieved_scores: Corresponding retrieval scores.
        poison_ids: Set of known poison document IDs.
        expected_ids: Set of expected legitimate document IDs.
        query_id: Identifier for this query.
        k: Number of top results to consider.
        thresholds: Optional dict with pass/fail thresholds.

    Returns:
        IntegrityMetricsResult with all computed metrics.
    """
    top_k_ids = retrieved_ids[:k]
    top_k_scores = retrieved_scores[:k] if retrieved_scores else []

    rate = poison_rate_at_k(retrieved_ids, poison_ids, k)
    mrr = poison_mrr(retrieved_ids, poison_ids)
    recall = true_doc_recall_at_k(retrieved_ids, expected_ids, k)

    # Find poison docs in top-k
    poison_in_top = [doc_id for doc_id in top_k_ids if doc_id in poison_ids]

    result = IntegrityMetricsResult(
        query_id=query_id,
        poison_rate=rate,
        poison_mrr_value=mrr,
        true_recall=recall,
        top_k_doc_ids=top_k_ids,
        top_k_scores=top_k_scores,
        poison_in_top_k=poison_in_top,
        expected_doc_ids=sorted(expected_ids),
    )

    # Apply thresholds if provided
    if thresholds:
        pr_thresh = thresholds.get("poison_rate_at_k", {})
        if "max_rate" in pr_thresh:
            result.poison_rate_passed = rate <= pr_thresh["max_rate"]

        mrr_thresh = thresholds.get("poison_mrr", {})
        if "max_mrr" in mrr_thresh:
            result.poison_mrr_passed = mrr <= mrr_thresh["max_mrr"]

        recall_thresh = thresholds.get("true_doc_recall_at_k", {})
        if "min_recall" in recall_thresh:
            result.true_recall_passed = recall >= recall_thresh["min_recall"]

    return result
