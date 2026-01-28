"""Consistency-based membership inference.

Uses paraphrases to measure retrieval stability and answer consistency.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from pydantic import BaseModel

from ragleaklab.metrics.paraphrase import generate_paraphrases

if TYPE_CHECKING:
    from ragleaklab.targets.base import BaseTarget


class ConsistencyResult(BaseModel):
    """Result of consistency-based membership analysis."""

    score: float  # 0.0 - 1.0, confidence of membership
    retrieval_consistency: float  # How stable are retrieved doc_ids
    answer_similarity: float  # How similar are answers across paraphrases
    dominant_doc_id: str | None  # Most frequently retrieved doc_id
    paraphrases_tested: int


def membership_consistency(
    target: BaseTarget,
    probe_query: str,
    paraphrase_count: int = 5,
) -> ConsistencyResult:
    """Calculate membership confidence using paraphrase consistency.

    High confidence if:
    - Same documents consistently retrieved across paraphrases
    - Answers are similar/stable across paraphrases

    Low confidence if:
    - Retrieved documents vary significantly
    - Answers are inconsistent

    Args:
        target: RAG target to probe.
        probe_query: Query to test for membership.
        paraphrase_count: Number of paraphrases to test.

    Returns:
        ConsistencyResult with confidence score.
    """
    paraphrases = generate_paraphrases(probe_query, count=paraphrase_count)

    # Collect responses
    all_doc_ids: list[list[str]] = []
    all_answers: list[str] = []

    for query in paraphrases:
        result = target.ask(query)
        all_doc_ids.append(result.retrieved_ids)
        all_answers.append(result.answer)

    # Calculate retrieval consistency
    retrieval_consistency = _calculate_retrieval_consistency(all_doc_ids)

    # Calculate answer similarity (simple token overlap)
    answer_similarity = _calculate_answer_similarity(all_answers)

    # Find dominant doc_id
    dominant_doc_id = _find_dominant_doc_id(all_doc_ids)

    # Combined score: weighted average
    # High retrieval consistency + high answer similarity = likely member
    score = retrieval_consistency * 0.6 + answer_similarity * 0.4

    return ConsistencyResult(
        score=score,
        retrieval_consistency=retrieval_consistency,
        answer_similarity=answer_similarity,
        dominant_doc_id=dominant_doc_id,
        paraphrases_tested=len(paraphrases),
    )


def _calculate_retrieval_consistency(doc_id_lists: list[list[str]]) -> float:
    """Calculate how consistent retrieval is across paraphrases.

    Returns 1.0 if same doc_id is always top-1.
    Returns 0.0 if completely random.
    """
    if not doc_id_lists:
        return 0.0

    # Get top-1 doc_id from each response
    top_doc_ids = [docs[0] if docs else "" for docs in doc_id_lists]

    if not any(top_doc_ids):
        return 0.0

    # Count occurrences
    counter = Counter(top_doc_ids)
    most_common_count = counter.most_common(1)[0][1]

    # Consistency = fraction of times most common appears
    return most_common_count / len(top_doc_ids)


def _calculate_answer_similarity(answers: list[str]) -> float:
    """Calculate token overlap similarity across answers.

    Simple approach: average pairwise Jaccard similarity.
    """
    if len(answers) < 2:
        return 1.0

    similarities = []
    for i, a1 in enumerate(answers):
        for a2 in answers[i + 1 :]:
            sim = _jaccard_similarity(a1, a2)
            similarities.append(sim)

    return sum(similarities) / len(similarities) if similarities else 0.0


def _jaccard_similarity(text1: str, text2: str) -> float:
    """Calculate Jaccard similarity between two texts."""
    tokens1 = set(text1.lower().split())
    tokens2 = set(text2.lower().split())

    if not tokens1 and not tokens2:
        return 1.0
    if not tokens1 or not tokens2:
        return 0.0

    intersection = tokens1 & tokens2
    union = tokens1 | tokens2

    return len(intersection) / len(union)


def _find_dominant_doc_id(doc_id_lists: list[list[str]]) -> str | None:
    """Find the most frequently retrieved doc_id."""
    all_ids = [doc_id for docs in doc_id_lists for doc_id in docs]

    if not all_ids:
        return None

    counter = Counter(all_ids)
    return counter.most_common(1)[0][0]
