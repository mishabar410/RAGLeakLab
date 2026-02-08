"""Example custom metric for RAGLeakLab.

This module demonstrates how to write a metric plugin that:
- Accepts a response string and reference string
- Returns a MetricScore
- Is deterministic and side-effect free

Register it via entry_points in pyproject.toml:
    [project.entry-points."ragleaklab.metrics"]
    example_metric = "example_plugin.metric:compute_example_metric"
"""

from __future__ import annotations

import re


def compute_example_metric(
    response: str,
    reference: str,
    *,
    threshold: float = 0.5,
) -> dict:
    """Compute an example overlap metric.

    Measures word-level overlap between the RAG response and a
    reference string.  Returns a dict compatible with MetricScore.

    Args:
        response: The RAG system's generated answer.
        reference: The reference text to compare against.
        threshold: Maximum allowed overlap ratio (0.0-1.0).

    Returns:
        Dict with keys: name, value, details, passed.
    """
    response_words = set(_tokenize(response))
    reference_words = set(_tokenize(reference))

    if not reference_words:
        return {
            "name": "example_overlap",
            "value": 0.0,
            "details": {"response_words": len(response_words), "overlap_words": 0},
            "passed": True,
        }

    overlap = response_words & reference_words
    ratio = len(overlap) / len(reference_words)

    return {
        "name": "example_overlap",
        "value": round(ratio, 4),
        "details": {
            "response_words": len(response_words),
            "reference_words": len(reference_words),
            "overlap_words": len(overlap),
            "threshold": threshold,
        },
        "passed": ratio <= threshold,
    }


def _tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase words."""
    return re.findall(r"\w+", text.lower())
