"""Disk cache for deterministic runs.

Stores retrieval hits, context, and answers to enable fast repeat runs
when inputs (corpus, target, query, retrieval params) are identical.
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from ragleaklab.core.contracts import RetrievalHit


class CachedResult(BaseModel):
    """Cached result from a pipeline or target run."""

    retrieved: list[RetrievalHit] = Field(default_factory=list, description="Retrieved chunks")
    context: str = Field(..., description="Context passed to generator")
    answer: str = Field(..., description="Generated answer")
    scores: list[float] = Field(default_factory=list, description="Retrieval scores")


@dataclass
class CacheKey:
    """Cache key components for deterministic lookup."""

    corpus_hash: str
    target_hash: str
    query: str
    retrieval_params: dict[str, Any]

    def compute(self) -> str:
        """Compute SHA-256 hash of key components.

        Returns:
            Hexadecimal hash string.
        """
        # Serialize retrieval params deterministically
        params_json = json.dumps(self.retrieval_params, sort_keys=True)

        # Combine all components
        key_string = f"{self.corpus_hash}:{self.target_hash}:{self.query}:{params_json}"

        return hashlib.sha256(key_string.encode("utf-8")).hexdigest()


class DiskCache:
    """Disk-based cache for pipeline results.

    Stores cached results as JSON files in the cache directory.
    """

    def __init__(self, cache_dir: Path):
        """Initialize disk cache.

        Args:
            cache_dir: Directory to store cache files.
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key_path(self, key_hash: str) -> Path:
        """Get file path for a cache key."""
        return self.cache_dir / f"{key_hash}.json"

    def exists(self, key: CacheKey) -> bool:
        """Check if a cache entry exists.

        Args:
            key: Cache key to check.

        Returns:
            True if entry exists, False otherwise.
        """
        return self._key_path(key.compute()).exists()

    def get(self, key: CacheKey) -> CachedResult | None:
        """Get cached result for a key.

        Args:
            key: Cache key to look up.

        Returns:
            CachedResult if found, None otherwise.
        """
        path = self._key_path(key.compute())
        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return CachedResult.model_validate(data)
        except (json.JSONDecodeError, ValueError):
            # Invalid cache entry, remove it
            path.unlink(missing_ok=True)
            return None

    def put(self, key: CacheKey, result: CachedResult) -> None:
        """Store a result in the cache.

        Args:
            key: Cache key.
            result: Result to cache.
        """
        path = self._key_path(key.compute())
        path.write_text(result.model_dump_json(indent=2), encoding="utf-8")

    def clear(self) -> int:
        """Clear all cache entries.

        Returns:
            Number of entries removed.
        """
        count = 0
        for path in self.cache_dir.glob("*.json"):
            path.unlink()
            count += 1
        return count


def build_cache_key(
    corpus_hash: str | None,
    target_hash: str | None,
    query: str,
    top_k: int = 3,
    strategy: str = "direct_ask",
) -> CacheKey:
    """Build a cache key from run parameters.

    Args:
        corpus_hash: Hash of corpus directory.
        target_hash: Identifier for target system.
        query: The query string (transformed).
        top_k: Number of chunks to retrieve.
        strategy: Attack strategy name.

    Returns:
        CacheKey instance.
    """
    return CacheKey(
        corpus_hash=corpus_hash or "",
        target_hash=target_hash or "",
        query=query,
        retrieval_params={"top_k": top_k, "strategy": strategy},
    )


def cached_result_to_hits(result: CachedResult) -> tuple[list[RetrievalHit], list[float]]:
    """Convert cached result to retrieval hits format.

    Args:
        result: Cached result.

    Returns:
        Tuple of (retrieval_hits, scores).
    """
    return result.retrieved, result.scores


def hits_to_cached_result(
    retrieved: list[RetrievalHit],
    context: str,
    answer: str,
) -> CachedResult:
    """Create cached result from run output.

    Args:
        retrieved: List of retrieval hits.
        context: Generated context.
        answer: Generated answer.

    Returns:
        CachedResult ready for caching.
    """
    return CachedResult(
        retrieved=retrieved,
        context=context,
        answer=answer,
        scores=[hit.score if hit.score is not None else 0.0 for hit in retrieved],
    )
