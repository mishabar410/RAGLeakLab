"""Tests for canary generation and detection."""

from pathlib import Path

from ragleaklab.corpus.canary import (
    find_canaries,
    generate_canary,
    has_canary,
    inject_canary,
)
from ragleaklab.corpus.loader import load_corpus


class TestGenerateCanary:
    """Tests for canary generation."""

    def test_deterministic_with_same_seed(self):
        """Canary is deterministic with fixed seed."""
        canary1 = generate_canary(42)
        canary2 = generate_canary(42)
        assert canary1 == canary2

    def test_different_seeds_different_canaries(self):
        """Different seeds produce different canaries."""
        canary1 = generate_canary(1)
        canary2 = generate_canary(2)
        assert canary1 != canary2

    def test_canary_format(self):
        """Canary follows expected format."""
        canary = generate_canary(1)
        assert canary.startswith("CANARY_")
        assert len(canary) == 23  # CANARY_ (7) + 16 hex chars

    def test_known_canary_values(self):
        """Test known canary values used in fixtures."""
        assert generate_canary(1) == "CANARY_e635ed32eb120f88"
        assert generate_canary(2) == "CANARY_986743ac15a7be7e"


class TestInjectCanary:
    """Tests for canary injection."""

    def test_inject_at_end(self):
        """Canary injected at end of text."""
        text = "Some document text."
        canary = generate_canary(1)
        result = inject_canary(text, canary, strategy="end")

        assert text in result
        assert canary in result
        assert result.index(canary) > result.index(text)

    def test_inject_at_middle(self):
        """Canary injected in middle of text."""
        text = "First paragraph.\n\nSecond paragraph."
        canary = generate_canary(1)
        result = inject_canary(text, canary, strategy="middle")

        assert canary in result


class TestFindCanaries:
    """Tests for canary detection."""

    def test_find_canary_in_text(self):
        """Find canary in text with canary."""
        canary = generate_canary(1)
        text = f"Some text with {canary} embedded."
        found = find_canaries(text)

        assert len(found) == 1
        assert found[0] == canary

    def test_no_canary_in_clean_text(self):
        """No canary found in clean text."""
        text = "Just regular text without any secrets."
        found = find_canaries(text)

        assert len(found) == 0

    def test_has_canary_true(self):
        """has_canary returns True when canary present."""
        canary = generate_canary(1)
        text = f"Text with {canary}"
        assert has_canary(text) is True

    def test_has_canary_false(self):
        """has_canary returns False when no canary."""
        text = "Clean text"
        assert has_canary(text) is False


class TestCorpusCanaryIntegration:
    """Integration tests with actual corpus fixtures."""

    def test_public_corpus_no_canaries(self):
        """Public corpus contains no canaries."""
        corpus_path = Path(__file__).parent.parent / "data" / "corpus_public"
        docs = load_corpus(corpus_path)

        for doc in docs:
            assert not has_canary(doc.text), f"Canary found in public doc: {doc.doc_id}"

    def test_private_corpus_has_canaries(self):
        """Private corpus contains canaries."""
        corpus_path = Path(__file__).parent.parent / "data" / "corpus_private_canary"
        docs = load_corpus(corpus_path)

        canary_count = 0
        for doc in docs:
            if has_canary(doc.text):
                canary_count += 1

        assert canary_count == 2, f"Expected 2 docs with canaries, found {canary_count}"

    def test_private_corpus_correct_canaries(self):
        """Private corpus contains expected canary values."""
        corpus_path = Path(__file__).parent.parent / "data" / "corpus_private_canary"
        docs = load_corpus(corpus_path)

        all_canaries = []
        for doc in docs:
            all_canaries.extend(find_canaries(doc.text))

        expected = {generate_canary(1), generate_canary(2)}
        assert set(all_canaries) == expected
