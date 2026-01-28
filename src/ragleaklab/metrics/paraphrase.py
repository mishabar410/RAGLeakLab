"""Deterministic paraphrase generator for membership consistency testing."""

from __future__ import annotations

# Fixed paraphrase templates - deterministic, no ML
PARAPHRASE_TEMPLATES = [
    # Original query
    "{query}",
    # Question form variations
    "What is {query}?",
    "Tell me about {query}",
    "Can you explain {query}?",
    "I need information about {query}",
    # Synonym substitutions
    "Details on {query}",
    "Information regarding {query}",
    # Reordering / emphasis
    "Regarding {query}, what do you know?",
    "{query} - please provide details",
]


def generate_paraphrases(query: str, count: int = 5) -> list[str]:
    """Generate deterministic paraphrases of a query.

    Uses fixed templates to create variations. This is deterministic
    and requires no ML inference.

    Args:
        query: Base query to paraphrase.
        count: Number of paraphrases to generate (max 8).

    Returns:
        List of paraphrased queries including original.
    """
    count = min(count, len(PARAPHRASE_TEMPLATES))

    paraphrases = []
    for template in PARAPHRASE_TEMPLATES[:count]:
        paraphrased = template.format(query=query.strip())
        paraphrases.append(paraphrased)

    return paraphrases


def extract_query_topic(query: str) -> str:
    """Extract the core topic from a query for template filling.

    Strips common question prefixes to get the core topic.

    Args:
        query: Original query.

    Returns:
        Core topic string.
    """
    # Strip common question prefixes
    prefixes = [
        "what is ",
        "what are ",
        "tell me about ",
        "explain ",
        "describe ",
        "how does ",
        "how do ",
        "can you explain ",
        "i need information about ",
        "information about ",
        "details on ",
        "regarding ",
    ]

    query_lower = query.lower().strip()
    for prefix in prefixes:
        if query_lower.startswith(prefix):
            return query[len(prefix) :].strip().rstrip("?").rstrip(".")

    return query.strip().rstrip("?").rstrip(".")
