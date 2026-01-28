"""Deterministic TF-IDF based retriever."""

import math
import re
from collections import Counter

from ragleaklab.rag.types import Chunk, Document, RetrievalResult


def tokenize(text: str) -> list[str]:
    """Simple tokenizer: lowercase, split on non-alphanumeric."""
    return re.findall(r"\b\w+\b", text.lower())


class TFIDFRetriever:
    """Deterministic TF-IDF retriever with stable ordering."""

    def __init__(self, chunk_size: int = 256, chunk_overlap: int = 32):
        """Initialize retriever with chunking parameters."""
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunks: list[Chunk] = []
        self.doc_freqs: Counter[str] = Counter()
        self.chunk_vectors: list[dict[str, float]] = []
        self._indexed = False

    def add_documents(self, documents: list[Document]) -> None:
        """Add documents to the index, chunking them first."""
        for doc in documents:
            doc_chunks = self._chunk_document(doc)
            self.chunks.extend(doc_chunks)
        self._build_index()

    def _chunk_document(self, doc: Document) -> list[Chunk]:
        """Split document into chunks."""
        text = doc.text
        chunks = []
        start = 0
        chunk_idx = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk_text = text[start:end]

            chunks.append(
                Chunk(
                    doc_id=doc.doc_id,
                    chunk_id=f"c{chunk_idx}",
                    text=chunk_text,
                )
            )

            start += self.chunk_size - self.chunk_overlap
            chunk_idx += 1

            if start >= len(text):
                break

        return chunks

    def _build_index(self) -> None:
        """Build TF-IDF index from chunks."""
        # Count document frequencies
        self.doc_freqs = Counter()
        for chunk in self.chunks:
            tokens = set(tokenize(chunk.text))
            for token in tokens:
                self.doc_freqs[token] += 1

        # Build TF-IDF vectors for each chunk
        n_docs = len(self.chunks)
        self.chunk_vectors = []

        for chunk in self.chunks:
            tokens = tokenize(chunk.text)
            tf = Counter(tokens)
            vector: dict[str, float] = {}

            for token, count in tf.items():
                # TF: log(1 + count)
                tf_score = math.log1p(count)
                # IDF: log(N / df)
                df = self.doc_freqs.get(token, 1)
                idf = math.log(n_docs / df) if df > 0 else 0
                vector[token] = tf_score * idf

            self.chunk_vectors.append(vector)

        self._indexed = True

    def retrieve(self, query: str, top_k: int = 5) -> RetrievalResult:
        """Retrieve top-k chunks for query.

        Uses TF-IDF cosine similarity with deterministic tie-breaking.
        """
        if not self._indexed:
            return RetrievalResult(chunks=[], scores=[], query=query)

        # Build query vector
        query_tokens = tokenize(query)
        query_tf = Counter(query_tokens)
        n_docs = len(self.chunks)

        query_vector: dict[str, float] = {}
        for token, count in query_tf.items():
            tf_score = math.log1p(count)
            df = self.doc_freqs.get(token, 1)
            idf = math.log(n_docs / df) if df > 0 else 0
            query_vector[token] = tf_score * idf

        # Calculate similarities
        scores: list[tuple[int, float, str]] = []
        for idx, chunk_vector in enumerate(self.chunk_vectors):
            sim = self._cosine_similarity(query_vector, chunk_vector)
            # Tie-breaker: chunk full_id for deterministic ordering
            scores.append((idx, sim, self.chunks[idx].full_id))

        # Sort by score (descending), then by chunk_id (ascending) for ties
        scores.sort(key=lambda x: (-x[1], x[2]))

        # Take top-k
        top_indices = [s[0] for s in scores[:top_k]]
        top_scores = [s[1] for s in scores[:top_k]]

        return RetrievalResult(
            chunks=[self.chunks[i] for i in top_indices],
            scores=top_scores,
            query=query,
        )

    def _cosine_similarity(self, vec1: dict[str, float], vec2: dict[str, float]) -> float:
        """Calculate cosine similarity between two sparse vectors."""
        if not vec1 or not vec2:
            return 0.0

        # Dot product
        common_keys = set(vec1.keys()) & set(vec2.keys())
        dot = sum(vec1[k] * vec2[k] for k in common_keys)

        # Magnitudes
        mag1 = math.sqrt(sum(v * v for v in vec1.values()))
        mag2 = math.sqrt(sum(v * v for v in vec2.values()))

        if mag1 == 0 or mag2 == 0:
            return 0.0

        return dot / (mag1 * mag2)
