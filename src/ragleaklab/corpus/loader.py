"""Document loader for corpus files."""

from pathlib import Path

from pydantic import BaseModel


class Document(BaseModel):
    """A document with ID and text content."""

    doc_id: str
    text: str
    source_path: str


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
