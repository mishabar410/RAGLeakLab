"""Corpus module for document loading, chunking, and canary injection."""

from ragleaklab.corpus.canary import find_canaries, generate_canary, inject_canary
from ragleaklab.corpus.chunking import chunk_text
from ragleaklab.corpus.loader import load_corpus

__all__ = [
    "chunk_text",
    "find_canaries",
    "generate_canary",
    "inject_canary",
    "load_corpus",
]
