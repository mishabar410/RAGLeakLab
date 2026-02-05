"""Fit binary thresholds for metrics with target FPR constraint."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["CalibrationResult", "fit_threshold"]


@dataclass
class CalibrationResult:
    """Result of threshold calibration."""

    threshold: float
    achieved_fpr: float
    achieved_tpr: float
    n_positive: int
    n_negative: int
    decision_rule: str  # e.g., "score >= threshold -> FAIL"


def fit_threshold(
    scores: list[tuple[str, float]],
    labels: dict[str, str],
    target_fpr: float = 0.01,
    higher_is_worse: bool = True,
) -> CalibrationResult:
    """Find threshold achieving target FPR with maximum TPR.

    Args:
        scores: List of (test_id, numeric_score) tuples.
        labels: Mapping test_id -> "positive" (leak expected) or "negative" (no leak).
        target_fpr: Maximum acceptable false positive rate (default 0.01 = 1%).
        higher_is_worse: If True, score >= threshold means FAIL (default).

    Returns:
        CalibrationResult with optimal threshold and achieved rates.

    Algorithm:
        1. Separate scores into positive and negative sets.
        2. Sort all unique thresholds.
        3. For each threshold, compute FPR and TPR.
        4. Select threshold with highest TPR where FPR <= target_fpr.
        5. Deterministic tie-breaking: prefer higher threshold (more conservative).

    Definitions (with higher_is_worse=True):
        - True Positive (TP): positive label, score >= threshold (correctly flagged)
        - False Positive (FP): negative label, score >= threshold (wrongly flagged)
        - True Negative (TN): negative label, score < threshold (correctly passed)
        - False Negative (FN): positive label, score < threshold (missed leak)
        - FPR = FP / (FP + TN) = FP / N_negative
        - TPR = TP / (TP + FN) = TP / N_positive
    """
    # Separate by label
    positive_scores: list[tuple[str, float]] = []
    negative_scores: list[tuple[str, float]] = []

    for test_id, score in scores:
        if test_id not in labels:
            continue  # Skip unlabeled cases
        if labels[test_id] == "positive":
            positive_scores.append((test_id, score))
        else:
            negative_scores.append((test_id, score))

    n_positive = len(positive_scores)
    n_negative = len(negative_scores)

    # Edge case: no positive or no negative samples
    if n_positive == 0 or n_negative == 0:
        # Return a neutral threshold
        all_scores = [s for _, s in scores]
        mid = sum(all_scores) / len(all_scores) if all_scores else 0.0
        decision_rule = (
            "score >= threshold -> FAIL" if higher_is_worse else "score <= threshold -> FAIL"
        )
        return CalibrationResult(
            threshold=mid,
            achieved_fpr=0.0,
            achieved_tpr=0.0 if n_positive == 0 else 1.0,
            n_positive=n_positive,
            n_negative=n_negative,
            decision_rule=decision_rule,
        )

    # Collect all unique score values as candidate thresholds
    # Add epsilon above max to catch "all pass" case
    all_score_values = sorted({s for _, s in positive_scores + negative_scores})

    # We'll try thresholds between consecutive scores and at extremes
    # For each candidate threshold t, we count how many scores >= t (if higher_is_worse)
    candidates: list[tuple[float, float, float]] = []  # (threshold, fpr, tpr)

    # Helper: count scores >= threshold
    def count_above(score_list: list[tuple[str, float]], thresh: float) -> int:
        return sum(1 for _, s in score_list if s >= thresh)

    # Helper: count scores <= threshold
    def count_below_or_eq(score_list: list[tuple[str, float]], thresh: float) -> int:
        return sum(1 for _, s in score_list if s <= thresh)

    # Generate candidate thresholds: unique scores + slightly above max
    max_score = max(all_score_values)
    eps = 1e-9

    # Include threshold above max (everything passes) and at each score value
    thresholds = [max_score + eps, *reversed(all_score_values)]

    for thresh in thresholds:
        if higher_is_worse:
            # score >= threshold -> flagged as leak
            tp = count_above(positive_scores, thresh)
            fp = count_above(negative_scores, thresh)
        else:
            # score <= threshold -> flagged as leak
            tp = count_below_or_eq(positive_scores, thresh)
            fp = count_below_or_eq(negative_scores, thresh)

        fpr = fp / n_negative
        tpr = tp / n_positive
        candidates.append((thresh, fpr, tpr))

    # Find best threshold: max TPR where FPR <= target_fpr
    # Deterministic tie-breaking: higher threshold wins (more conservative)
    valid_candidates = [(t, fpr, tpr) for t, fpr, tpr in candidates if fpr <= target_fpr]

    if valid_candidates:
        # Sort by TPR descending, then threshold descending for ties
        valid_candidates.sort(key=lambda x: (-x[2], -x[0]))
        best_thresh, best_fpr, best_tpr = valid_candidates[0]
    else:
        # Can't achieve target FPR - use most conservative threshold (highest)
        best_thresh = max_score + eps
        if higher_is_worse:
            best_fpr = count_above(negative_scores, best_thresh) / n_negative
            best_tpr = count_above(positive_scores, best_thresh) / n_positive
        else:
            best_fpr = 0.0
            best_tpr = 0.0

    decision_rule = (
        "score >= threshold -> FAIL" if higher_is_worse else "score <= threshold -> FAIL"
    )

    return CalibrationResult(
        threshold=best_thresh,
        achieved_fpr=best_fpr,
        achieved_tpr=best_tpr,
        n_positive=n_positive,
        n_negative=n_negative,
        decision_rule=decision_rule,
    )
