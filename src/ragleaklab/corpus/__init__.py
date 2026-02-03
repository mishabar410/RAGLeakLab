"""Corpus module for document loading, chunking, and canary injection."""

from ragleaklab.corpus.canary import find_canaries, generate_canary, inject_canary
from ragleaklab.corpus.chunking import chunk_text
from ragleaklab.corpus.claims import Claim, index_claims_by_doc, load_claims
from ragleaklab.corpus.loader import (
    CorpusWithClaims,
    load_corpus,
    load_corpus_with_claims,
)

__all__ = [
    "Claim",
    "CorpusWithClaims",
    "chunk_text",
    "find_canaries",
    "generate_canary",
    "index_claims_by_doc",
    "inject_canary",
    "load_claims",
    "load_corpus",
    "load_corpus_with_claims",
]
