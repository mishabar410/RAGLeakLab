"""Deterministic attack query minimization using delta debugging.

Minimizes failing queries to produce stable, minimal test cases for regressions.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel, Field


class MinimizationResult(BaseModel):
    """Result of query minimization."""

    original_query: str = Field(..., description="Original query before minimization")
    minimized_query: str = Field(..., description="Minimized query that still fails")
    original_chunks: int = Field(..., description="Number of chunks in original")
    minimized_chunks: int = Field(..., description="Number of chunks after minimization")
    iterations: int = Field(..., description="Number of oracle calls made")
    reduced: bool = Field(..., description="True if query was actually reduced")


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences.

    Uses simple regex to split on sentence-ending punctuation.
    Preserves the punctuation with the sentence.
    """
    # Split on sentence boundaries, keeping delimiters
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _split_lines(text: str) -> list[str]:
    """Split text into lines."""
    return [line.strip() for line in text.split("\n") if line.strip()]


def _join_chunks(chunks: list[str], mode: Literal["sentence", "line"]) -> str:
    """Join chunks back into text."""
    if mode == "line":
        return "\n".join(chunks)
    return " ".join(chunks)


def ddmin(
    chunks: list[str],
    test_fn: Callable[[list[str]], bool],
    n: int = 2,
) -> tuple[list[str], int]:
    """Delta debugging minimization algorithm.

    Finds a minimal subset of chunks that still causes the test to fail.
    Deterministic: same input always produces same output.

    Args:
        chunks: List of chunks (sentences or lines).
        test_fn: Oracle function. Returns True if failure PERSISTS.
        n: Number of subsets to try (starts at 2, doubles on failure).

    Returns:
        Tuple of (minimal_chunks, iteration_count).

    Reference:
        Zeller & Hildebrandt, "Simplifying and Isolating Failure-Inducing Input"
    """
    if len(chunks) <= 1:
        return chunks, 0

    iterations = 0

    while len(chunks) >= 2:
        subset_size = len(chunks) // n
        if subset_size == 0:
            subset_size = 1

        found_reduction = False

        # Try removing each subset
        for i in range(n):
            start = i * subset_size
            end = start + subset_size if i < n - 1 else len(chunks)

            # Create complement (all except this subset)
            complement = chunks[:start] + chunks[end:]

            if not complement:
                continue

            iterations += 1

            if test_fn(complement):
                # Failure still reproduces without this subset
                chunks = complement
                n = max(n - 1, 2)
                found_reduction = True
                break

        if not found_reduction:
            if n >= len(chunks):
                # Can't reduce further
                break
            # Increase granularity
            n = min(n * 2, len(chunks))

    return chunks, iterations


def minimize_query(
    query: str,
    oracle: Callable[[str], bool],
    chunk_mode: Literal["sentence", "line"] = "sentence",
) -> MinimizationResult:
    """Minimize a failing query using delta debugging.

    Args:
        query: Original query that causes a failure (leak detected).
        oracle: Function that returns True if failure PERSISTS with given query.
        chunk_mode: How to split the query ("sentence" or "line").

    Returns:
        MinimizationResult with original and minimized queries.
    """
    # Split into chunks
    if chunk_mode == "line":
        chunks = _split_lines(query)
    else:
        chunks = _split_sentences(query)

    # Handle edge cases
    if len(chunks) <= 1:
        return MinimizationResult(
            original_query=query,
            minimized_query=query,
            original_chunks=len(chunks),
            minimized_chunks=len(chunks),
            iterations=0,
            reduced=False,
        )

    # Wrap oracle to work with chunks
    def chunk_oracle(chunk_list: list[str]) -> bool:
        joined = _join_chunks(chunk_list, chunk_mode)
        return oracle(joined)

    # Run ddmin
    minimized_chunks, iterations = ddmin(chunks, chunk_oracle)

    # Join result
    minimized_query = _join_chunks(minimized_chunks, chunk_mode)

    return MinimizationResult(
        original_query=query,
        minimized_query=minimized_query,
        original_chunks=len(chunks),
        minimized_chunks=len(minimized_chunks),
        iterations=iterations,
        reduced=len(minimized_chunks) < len(chunks),
    )
