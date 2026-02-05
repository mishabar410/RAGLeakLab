"""Poisoning module for integrity threat detection.

This module provides types and utilities for detecting corpus/dataset
poisoning attacks against RAG systems. These are integrity threats where
an attacker manipulates the corpus to influence retrieval or generation.

Key concepts:
- RetrievalIntegrityEvidence: Detects poisoned retrieval rankings
- ClaimIntegrityEvidence: Detects manipulated claim generation
- SentinelIntegrityEvidence: Detects backdoor trigger activation
"""

from ragleaklab.poisoning.evidence import (
    ClaimIntegrityEvidence,
    IntegrityEvidence,
    IntegritySection,
    IntegritySummary,
    RetrievalIntegrityEvidence,
    SentinelIntegrityEvidence,
    SentinelType,
    SeverityLevel,
)

__all__ = [
    "ClaimIntegrityEvidence",
    "IntegrityEvidence",
    "IntegritySection",
    "IntegritySummary",
    "RetrievalIntegrityEvidence",
    "SentinelIntegrityEvidence",
    "SentinelType",
    "SeverityLevel",
]
