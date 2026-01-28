"""Verbatim overlap metrics."""

import re
from collections.abc import Sequence

from pydantic import BaseModel


class VerbatimResult(BaseModel):
    """Result of verbatim overlap detection."""

    score: float  # 0.0 - 1.0, highest overlap ratio
    max_lcs_length: int  # Longest common substring length
    source_with_max_overlap: str | None  # Source ID with highest overlap
    ngram_matches: int  # Number of matching n-grams


def _tokenize(text: str) -> list[str]:
    """Simple word tokenization."""
    return re.findall(r"\b\w+\b", text.lower())


def _get_ngrams(tokens: list[str], n: int) -> set[tuple[str, ...]]:
    """Generate n-grams from tokens."""
    if len(tokens) < n:
        return set()
    return {tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def _longest_common_substring(s1: str, s2: str) -> str:
    """Find longest common substring between two strings."""
    s1 = s1.lower()
    s2 = s2.lower()

    if not s1 or not s2:
        return ""

    # Dynamic programming approach
    m, n = len(s1), len(s2)
    # Use rolling array to save memory
    prev = [0] * (n + 1)
    curr = [0] * (n + 1)

    max_length = 0
    end_pos = 0

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                curr[j] = prev[j - 1] + 1
                if curr[j] > max_length:
                    max_length = curr[j]
                    end_pos = i
            else:
                curr[j] = 0
        prev, curr = curr, prev

    return s1[end_pos - max_length : end_pos]


def verbatim_overlap(
    answer: str,
    sources: Sequence[tuple[str, str]],  # List of (source_id, source_text)
    min_chars: int = 20,
    min_ngram_len: int = 4,
) -> VerbatimResult:
    """Calculate verbatim overlap between answer and source texts.

    Uses both LCS ratio and n-gram overlap for robustness.

    Args:
        answer: Generated answer text.
        sources: List of (source_id, source_text) tuples.
        min_chars: Minimum LCS length to count (reduces FP on common phrases).
        min_ngram_len: N-gram size for matching.

    Returns:
        VerbatimResult with overlap metrics.
    """
    if not answer or not sources:
        return VerbatimResult(
            score=0.0,
            max_lcs_length=0,
            source_with_max_overlap=None,
            ngram_matches=0,
        )

    answer_tokens = _tokenize(answer)
    answer_ngrams = _get_ngrams(answer_tokens, min_ngram_len)

    max_score = 0.0
    max_lcs_length = 0
    max_source_id: str | None = None
    total_ngram_matches = 0

    for source_id, source_text in sources:
        # LCS-based overlap
        lcs = _longest_common_substring(answer, source_text)
        lcs_length = len(lcs)

        # Only count if above minimum threshold
        if lcs_length >= min_chars:
            # Score as ratio of LCS to source length
            source_len = len(source_text)
            if source_len > 0:
                ratio = lcs_length / source_len
                if ratio > max_score:
                    max_score = ratio
                    max_lcs_length = lcs_length
                    max_source_id = source_id

        # N-gram overlap
        source_tokens = _tokenize(source_text)
        source_ngrams = _get_ngrams(source_tokens, min_ngram_len)
        ngram_overlap = len(answer_ngrams & source_ngrams)
        total_ngram_matches += ngram_overlap

    return VerbatimResult(
        score=min(max_score, 1.0),  # Cap at 1.0
        max_lcs_length=max_lcs_length,
        source_with_max_overlap=max_source_id,
        ngram_matches=total_ngram_matches,
    )
