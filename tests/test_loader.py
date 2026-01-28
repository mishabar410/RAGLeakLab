"""Tests for corpus loader."""

from pathlib import Path

from ragleaklab.corpus.loader import load_corpus


def test_load_corpus_public():
    """Test loading public corpus documents."""
    corpus_path = Path(__file__).parent.parent / "data" / "corpus_public"
    docs = load_corpus(corpus_path)

    assert len(docs) == 2
    doc_ids = {doc.doc_id for doc in docs}
    assert "doc_data_processing" in doc_ids
    assert "doc_ml_overview" in doc_ids


def test_load_corpus_private():
    """Test loading private corpus with canaries."""
    corpus_path = Path(__file__).parent.parent / "data" / "corpus_private_canary"
    docs = load_corpus(corpus_path)

    assert len(docs) == 2
    doc_ids = {doc.doc_id for doc in docs}
    assert "doc_api_security" in doc_ids
    assert "doc_database_config" in doc_ids


def test_load_corpus_nonexistent():
    """Test loading from nonexistent directory returns empty list."""
    docs = load_corpus("/nonexistent/path")
    assert docs == []


def test_document_has_text():
    """Test that loaded documents have non-empty text."""
    corpus_path = Path(__file__).parent.parent / "data" / "corpus_public"
    docs = load_corpus(corpus_path)

    for doc in docs:
        assert doc.text
        assert len(doc.text) > 0
