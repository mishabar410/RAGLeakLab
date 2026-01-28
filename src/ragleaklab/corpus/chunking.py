"""Deterministic text chunking for corpus processing."""

from pydantic import BaseModel


class Chunk(BaseModel):
    """A chunk of text with metadata."""

    doc_id: str
    chunk_index: int
    text: str
    start_char: int
    end_char: int


def chunk_text(
    text: str,
    doc_id: str,
    chunk_size: int = 512,
    overlap: int = 64,
) -> list[Chunk]:
    """Split text into fixed-size chunks with overlap.

    Args:
        text: Text to chunk.
        doc_id: Document ID for metadata.
        chunk_size: Size of each chunk in characters.
        overlap: Overlap between consecutive chunks.

    Returns:
        List of Chunk objects.
    """
    if not text:
        return []

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk_text_content = text[start:end]

        chunks.append(
            Chunk(
                doc_id=doc_id,
                chunk_index=chunk_index,
                text=chunk_text_content,
                start_char=start,
                end_char=end,
            )
        )

        # Move to next chunk position
        start += chunk_size - overlap
        chunk_index += 1

        # Prevent infinite loop on small texts
        if start >= len(text):
            break

    return chunks
