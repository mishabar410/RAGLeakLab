"""Context builder for RAG pipeline."""

from ragleaklab.rag.types import Chunk


class ContextBuilder:
    """Builds formatted context from retrieved chunks."""

    def __init__(self, separator: str = "\n---\n"):
        """Initialize context builder.

        Args:
            separator: String to separate chunks in context.
        """
        self.separator = separator

    def build(self, chunks: list[Chunk]) -> str:
        """Build context string from chunks with explicit labels.

        Args:
            chunks: List of chunks to include in context.

        Returns:
            Formatted context string with [doc_id:chunk_id] labels.
        """
        if not chunks:
            return ""

        parts = []
        for chunk in chunks:
            label = f"[{chunk.full_id}]"
            parts.append(f"{label}\n{chunk.text}")

        return self.separator.join(parts)

    def extract_chunk_ids(self, context: str) -> list[str]:
        """Extract chunk IDs from context string.

        Args:
            context: Context string with [doc_id:chunk_id] labels.

        Returns:
            List of chunk IDs in order of appearance.
        """
        import re

        pattern = r"\[([^\]]+:[^\]]+)\]"
        return re.findall(pattern, context)
