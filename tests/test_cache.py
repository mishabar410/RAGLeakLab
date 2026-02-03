"""Tests for disk cache layer."""

from pathlib import Path

from ragleaklab.attacks.schema import TestCase
from ragleaklab.core.cache import (
    CachedResult,
    CacheKey,
    DiskCache,
    build_cache_key,
    hits_to_cached_result,
)
from ragleaklab.core.contracts import Chunk, Hashes, RetrievalHit


class TestCacheKey:
    """Tests for CacheKey computation."""

    def test_cache_key_deterministic(self):
        """Same inputs produce same cache key."""
        key1 = CacheKey(
            corpus_hash="abc123",
            target_hash="in-process",
            query="test query",
            retrieval_params={"top_k": 3, "strategy": "direct_ask"},
        )
        key2 = CacheKey(
            corpus_hash="abc123",
            target_hash="in-process",
            query="test query",
            retrieval_params={"top_k": 3, "strategy": "direct_ask"},
        )
        assert key1.compute() == key2.compute()

    def test_cache_key_different_query(self):
        """Different queries produce different keys."""
        key1 = CacheKey(
            corpus_hash="abc",
            target_hash="target",
            query="query one",
            retrieval_params={"top_k": 3},
        )
        key2 = CacheKey(
            corpus_hash="abc",
            target_hash="target",
            query="query two",
            retrieval_params={"top_k": 3},
        )
        assert key1.compute() != key2.compute()

    def test_cache_key_different_corpus_hash(self):
        """Different corpus hashes produce different keys."""
        key1 = CacheKey(
            corpus_hash="hash_v1",
            target_hash="target",
            query="query",
            retrieval_params={},
        )
        key2 = CacheKey(
            corpus_hash="hash_v2",
            target_hash="target",
            query="query",
            retrieval_params={},
        )
        assert key1.compute() != key2.compute()

    def test_build_cache_key_helper(self):
        """build_cache_key creates valid CacheKey."""
        key = build_cache_key(
            corpus_hash="corp123",
            target_hash="in-process",
            query="what is secret",
            top_k=5,
            strategy="roleplay",
        )
        assert isinstance(key, CacheKey)
        assert key.corpus_hash == "corp123"
        assert len(key.compute()) == 64  # SHA-256 hex


class TestDiskCache:
    """Tests for DiskCache operations."""

    def test_cache_put_get(self, tmp_path: Path):
        """Cache stores and retrieves results."""
        cache = DiskCache(tmp_path / "cache")

        key = CacheKey(
            corpus_hash="abc",
            target_hash="target",
            query="test",
            retrieval_params={"top_k": 3},
        )
        result = CachedResult(
            retrieved=[],
            context="test context",
            answer="test answer",
            scores=[],
        )

        cache.put(key, result)
        retrieved = cache.get(key)

        assert retrieved is not None
        assert retrieved.answer == "test answer"
        assert retrieved.context == "test context"

    def test_cache_exists(self, tmp_path: Path):
        """exists() returns correct status."""
        cache = DiskCache(tmp_path / "cache")
        key = CacheKey(
            corpus_hash="abc",
            target_hash="target",
            query="test",
            retrieval_params={},
        )

        assert not cache.exists(key)

        cache.put(key, CachedResult(retrieved=[], context="", answer="", scores=[]))

        assert cache.exists(key)

    def test_cache_miss_returns_none(self, tmp_path: Path):
        """Non-existent key returns None."""
        cache = DiskCache(tmp_path / "cache")
        key = CacheKey(
            corpus_hash="nonexistent",
            target_hash="target",
            query="missing",
            retrieval_params={},
        )

        assert cache.get(key) is None

    def test_cache_clear(self, tmp_path: Path):
        """clear() removes all entries."""
        cache = DiskCache(tmp_path / "cache")

        for i in range(3):
            key = CacheKey(
                corpus_hash=f"hash{i}",
                target_hash="target",
                query=f"query{i}",
                retrieval_params={},
            )
            cache.put(key, CachedResult(retrieved=[], context="", answer="", scores=[]))

        removed = cache.clear()
        assert removed == 3

        # All entries should be gone
        for i in range(3):
            key = CacheKey(
                corpus_hash=f"hash{i}",
                target_hash="target",
                query=f"query{i}",
                retrieval_params={},
            )
            assert cache.get(key) is None

    def test_cache_with_retrieval_hits(self, tmp_path: Path):
        """Cache correctly serializes RetrievalHit objects."""
        cache = DiskCache(tmp_path / "cache")

        chunk = Chunk(doc_id="doc1", chunk_id="c0", text="sample text")
        hit = RetrievalHit(chunk=chunk, score=0.95)

        key = CacheKey(
            corpus_hash="abc",
            target_hash="target",
            query="test",
            retrieval_params={},
        )
        result = CachedResult(
            retrieved=[hit],
            context="context with sample text",
            answer="answer",
            scores=[0.95],
        )

        cache.put(key, result)
        retrieved = cache.get(key)

        assert retrieved is not None
        assert len(retrieved.retrieved) == 1
        assert retrieved.retrieved[0].chunk.doc_id == "doc1"
        assert retrieved.retrieved[0].score == 0.95


class TestCacheIntegration:
    """Integration tests for cache with runner."""

    def test_cache_hit_skips_pipeline(self, tmp_path: Path):
        """Second run with cache uses cached result and skips pipeline."""
        from ragleaklab.attacks.runner import run_case
        from ragleaklab.rag import Document, RAGPipeline

        # Setup
        cache_dir = tmp_path / "cache"
        cache = DiskCache(cache_dir)

        docs = [Document(doc_id="doc1", text="Secret API key: ABC123")]
        pipeline = RAGPipeline(top_k=2)
        pipeline.add_documents(docs)

        case = TestCase(
            test_id="cache_test",
            threat="canary",
            query="what is the API key",
            strategy="direct_ask",
        )

        hashes = Hashes(
            corpus_hash="fixed_hash",
            target_hash="in-process",
        )

        # First run: cache miss
        result1 = run_case(pipeline, case, hashes=hashes, cache=cache)
        assert result1.meta.get("cache_hit") is False

        # Second run: cache hit
        result2 = run_case(pipeline, case, hashes=hashes, cache=cache)
        assert result2.meta.get("cache_hit") is True

        # Results should match
        assert result1.answer == result2.answer
        assert result1.context == result2.context

    def test_cache_hit_verified_by_monkeypatch(self, tmp_path: Path, monkeypatch):
        """Verify retriever/generator not called on cache hit via monkeypatch."""
        from ragleaklab.attacks.runner import run_case
        from ragleaklab.rag import Document, RAGPipeline

        cache = DiskCache(tmp_path / "cache")

        docs = [Document(doc_id="doc1", text="Test document content")]
        pipeline = RAGPipeline(top_k=2)
        pipeline.add_documents(docs)

        case = TestCase(
            test_id="monkeypatch_test",
            threat="canary",
            query="test query",
            strategy="direct_ask",
        )

        hashes = Hashes(corpus_hash="test_hash", target_hash="in-process")

        # First run populates cache
        result1 = run_case(pipeline, case, hashes=hashes, cache=cache)
        assert result1.meta.get("cache_hit") is False

        # Monkeypatch pipeline.run to track if called
        call_count = {"count": 0}
        original_run = pipeline.run

        def tracked_run(query):
            call_count["count"] += 1
            return original_run(query)

        monkeypatch.setattr(pipeline, "run", tracked_run)

        # Second run should use cache, not call pipeline.run
        result2 = run_case(pipeline, case, hashes=hashes, cache=cache)

        assert result2.meta.get("cache_hit") is True
        assert call_count["count"] == 0, "pipeline.run should NOT be called on cache hit"

    def test_cache_invalidation_on_corpus_change(self, tmp_path: Path):
        """Different corpus hash causes cache miss."""
        from ragleaklab.attacks.runner import run_case
        from ragleaklab.rag import Document, RAGPipeline

        cache = DiskCache(tmp_path / "cache")

        docs = [Document(doc_id="doc1", text="Content")]
        pipeline = RAGPipeline(top_k=2)
        pipeline.add_documents(docs)

        case = TestCase(
            test_id="invalidation_test",
            threat="canary",
            query="query",
            strategy="direct_ask",
        )

        # First run with hash v1
        hashes_v1 = Hashes(corpus_hash="hash_v1", target_hash="in-process")
        result1 = run_case(pipeline, case, hashes=hashes_v1, cache=cache)
        assert result1.meta.get("cache_hit") is False

        # Second run with hash v2 (simulating corpus change)
        hashes_v2 = Hashes(corpus_hash="hash_v2", target_hash="in-process")
        result2 = run_case(pipeline, case, hashes=hashes_v2, cache=cache)

        # Should be cache miss because corpus hash changed
        assert result2.meta.get("cache_hit") is False


class TestCacheHelpers:
    """Tests for cache helper functions."""

    def test_hits_to_cached_result(self):
        """hits_to_cached_result creates valid CachedResult."""
        chunk = Chunk(doc_id="doc1", chunk_id="c0", text="text")
        hits = [RetrievalHit(chunk=chunk, score=0.8)]

        result = hits_to_cached_result(hits, "context", "answer")

        assert isinstance(result, CachedResult)
        assert result.answer == "answer"
        assert result.context == "context"
        assert len(result.retrieved) == 1
        assert result.scores == [0.8]
