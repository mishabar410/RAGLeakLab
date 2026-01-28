"""Mock generator for deterministic RAG testing."""

import re


class MockGenerator:
    """Deterministic mock generator that extracts from context.

    Generates responses ONLY from provided context, never from
    "knowledge". Uses simple keyword matching to select sentences.
    """

    def __init__(self, max_sentences: int = 3):
        """Initialize mock generator.

        Args:
            max_sentences: Maximum sentences to include in response.
        """
        self.max_sentences = max_sentences

    def generate(self, query: str, context: str) -> str:
        """Generate response from context based on query.

        Strategy:
        1. Extract all sentences from context
        2. Score sentences by keyword overlap with query
        3. Return top-scoring sentences (deterministic ordering)

        Args:
            query: User query.
            context: Context string from retrieved chunks.

        Returns:
            Generated response.
        """
        if not context:
            return "No context provided."

        # Extract sentences from context (skip chunk labels)
        sentences = self._extract_sentences(context)
        if not sentences:
            return "No relevant content found in context."

        # Score sentences by keyword overlap
        query_keywords = set(self._tokenize(query))
        scored: list[tuple[str, float, int]] = []

        for idx, sentence in enumerate(sentences):
            sentence_keywords = set(self._tokenize(sentence))
            overlap = len(query_keywords & sentence_keywords)
            # Normalize by sentence length to avoid bias toward long sentences
            score = overlap / max(len(sentence_keywords), 1)
            # Tie-breaker: original order (idx)
            scored.append((sentence, score, idx))

        # Sort by score (desc), then by index (asc) for determinism
        scored.sort(key=lambda x: (-x[1], x[2]))

        # Take top sentences
        top_sentences = [s[0] for s in scored[: self.max_sentences] if s[1] > 0]

        if not top_sentences:
            # Fallback: return first sentence from context
            return sentences[0] if sentences else "No relevant content found."

        return " ".join(top_sentences)

    def _extract_sentences(self, context: str) -> list[str]:
        """Extract sentences from context, skipping chunk labels."""
        # Remove chunk labels [doc_id:chunk_id]
        clean_text = re.sub(r"\[[^\]]+:[^\]]+\]", "", context)
        # Remove separator lines
        clean_text = re.sub(r"\n---\n", " ", clean_text)
        # Split into sentences (simple split on period, !, ?)
        sentences = re.split(r"(?<=[.!?])\s+", clean_text)
        # Clean up and filter empty
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenizer: lowercase, alphanumeric only."""
        return re.findall(r"\b\w+\b", text.lower())
