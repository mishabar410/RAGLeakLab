"""Tests for corpus/chunking.py."""

import pytest

from ragleaklab.corpus.chunking import Chunk, chunk_text


class TestChunkText:
    """Tests for chunk_text function."""

    def test_basic_chunking(self):
        text = "a" * 100
        chunks = chunk_text(text, "doc1", chunk_size=30, overlap=10)
        assert len(chunks) > 1
        assert all(isinstance(c, Chunk) for c in chunks)
        assert chunks[0].doc_id == "doc1"
        assert chunks[0].chunk_index == 0
        assert chunks[0].start_char == 0

    def test_chunk_content_is_correct(self):
        text = "Hello World! This is a test document for chunking."
        chunks = chunk_text(text, "d1", chunk_size=20, overlap=5)
        # First chunk is text[0:20]
        assert chunks[0].text == text[0:20]
        assert chunks[0].start_char == 0
        assert chunks[0].end_char == 20

    def test_overlap_between_chunks(self):
        text = "a" * 50
        chunks = chunk_text(text, "d1", chunk_size=20, overlap=5)
        # Second chunk starts at 20 - 5 = 15
        assert chunks[1].start_char == 15

    def test_empty_text_returns_empty(self):
        assert chunk_text("", "doc1") == []

    def test_single_char(self):
        chunks = chunk_text("x", "doc1", chunk_size=10, overlap=0)
        assert len(chunks) == 1
        assert chunks[0].text == "x"
        assert chunks[0].start_char == 0
        assert chunks[0].end_char == 1

    def test_text_shorter_than_chunk_size(self):
        text = "short"
        chunks = chunk_text(text, "d1", chunk_size=100, overlap=10)
        assert len(chunks) == 1
        assert chunks[0].text == text

    def test_zero_overlap(self):
        text = "a" * 40
        chunks = chunk_text(text, "d1", chunk_size=20, overlap=0)
        assert len(chunks) == 2
        assert chunks[0].end_char == 20
        assert chunks[1].start_char == 20

    def test_chunk_indices_sequential(self):
        text = "a" * 100
        chunks = chunk_text(text, "d1", chunk_size=20, overlap=5)
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    # Bug fix: validation tests
    def test_overlap_ge_chunk_size_raises(self):
        with pytest.raises(ValueError, match="overlap must be less than chunk_size"):
            chunk_text("hello", "d1", chunk_size=5, overlap=5)

    def test_overlap_gt_chunk_size_raises(self):
        with pytest.raises(ValueError, match="overlap must be less than chunk_size"):
            chunk_text("hello", "d1", chunk_size=5, overlap=10)

    def test_negative_overlap_raises(self):
        with pytest.raises(ValueError, match="overlap must be non-negative"):
            chunk_text("hello", "d1", chunk_size=5, overlap=-1)

    def test_zero_chunk_size_raises(self):
        with pytest.raises(ValueError, match="chunk_size must be positive"):
            chunk_text("hello", "d1", chunk_size=0, overlap=0)

    def test_negative_chunk_size_raises(self):
        with pytest.raises(ValueError, match="chunk_size must be positive"):
            chunk_text("hello", "d1", chunk_size=-1, overlap=0)
