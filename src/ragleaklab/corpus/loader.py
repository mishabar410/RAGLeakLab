"""Document loader for corpus files."""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

from pydantic import BaseModel

from ragleaklab.corpus.claims import Claim, index_claims_by_doc, load_claims


class Document(BaseModel):
    """A document with ID and text content."""

    doc_id: str
    text: str
    source_path: str


class CorpusWithClaims(NamedTuple):
    """Result of loading corpus with claims."""

    documents: list[Document]
    claims_index: dict[str, list[Claim]]


def load_corpus(directory: Path | str, extensions: tuple[str, ...] = (".txt",)) -> list[Document]:
    """Load documents from a directory.

    Args:
        directory: Path to directory containing documents.
        extensions: File extensions to include (default: .txt only).

    Returns:
        List of Document objects with doc_id derived from filename.
    """
    directory = Path(directory)
    if not directory.exists():
        return []

    documents = []
    for path in sorted(directory.iterdir()):
        if path.is_file() and path.suffix in extensions:
            doc_id = path.stem  # filename without extension
            text = path.read_text(encoding="utf-8")
            documents.append(
                Document(
                    doc_id=doc_id,
                    text=text,
                    source_path=str(path),
                )
            )
    return documents


def load_corpus_with_claims(
    directory: Path | str,
    claims_path: Path | str | None = None,
    extensions: tuple[str, ...] = (".txt",),
) -> CorpusWithClaims:
    """Load documents and optionally claims from a directory.

    If claims_path is not provided, looks for claims.jsonl in the directory.
    If no claims file exists, returns empty claims index.

    Args:
        directory: Path to directory containing documents.
        claims_path: Optional path to claims.jsonl file.
        extensions: File extensions to include (default: .txt only).

    Returns:
        CorpusWithClaims containing documents and claims index.
    """
    directory = Path(directory)
    documents = load_corpus(directory, extensions)

    # Determine claims path
    if claims_path is not None:
        claims_file = Path(claims_path)
    else:
        claims_file = directory / "claims.jsonl"

    # Load claims if file exists
    claims_index: dict[str, list[Claim]] = {}
    if claims_file.exists():
        claims = load_claims(claims_file)
        claims_index = index_claims_by_doc(claims)

    return CorpusWithClaims(documents=documents, claims_index=claims_index)
