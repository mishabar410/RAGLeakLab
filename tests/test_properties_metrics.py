"""Property-based tests for metrics using hypothesis.

Tests invariants:
- verbatim_overlap score invariant to source permutation
- claim matching invariant to case/punctuation for EMAIL/ACCOUNT_ID types
- canary detection: no false positives on random strings without CANARY_ prefix
"""

import random

from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from ragleaklab.metrics import detect_canary, verbatim_overlap
from ragleaklab.metrics.claim_match import match_claim

# Fixed settings for fast, deterministic tests
PROP_SETTINGS = settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
    derandomize=True,  # Use deterministic seed
)


# --- Strategies ---

# Text without CANARY_ prefix - alphanumeric chars, spaces, punctuation
safe_chars = st.text(
    alphabet=st.sampled_from(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,;:!?()-"
    ),
    min_size=0,
    max_size=200,
)

# Source tuples: (source_id, source_text)
source_strategy = st.tuples(
    st.text(min_size=1, max_size=10, alphabet="abcdefghij0123456789"),
    st.text(min_size=10, max_size=100),
)

# Lists of sources
sources_strategy = st.lists(source_strategy, min_size=1, max_size=5)


class TestVerbatimPermutationInvariant:
    """Verbatim score should be invariant to source order."""

    @PROP_SETTINGS
    @given(
        answer=st.text(min_size=10, max_size=100),
        sources=sources_strategy,
    )
    def test_verbatim_score_invariant_to_source_permutation(self, answer, sources):
        """Permuting sources does not change the score."""
        assume(len(sources) >= 2)  # Need at least 2 sources to permute

        # Original order
        result1 = verbatim_overlap(answer, sources)

        # Permuted order (reversed)
        permuted_sources = list(reversed(sources))
        result2 = verbatim_overlap(answer, permuted_sources)

        assert result1.score == result2.score, (
            f"Score changed with permutation: {result1.score} != {result2.score}"
        )
        assert result1.max_lcs_length == result2.max_lcs_length, (
            f"max_lcs_length changed: {result1.max_lcs_length} != {result2.max_lcs_length}"
        )

    @PROP_SETTINGS
    @given(
        answer=st.text(min_size=10, max_size=100),
        sources=sources_strategy,
        seed=st.integers(min_value=0, max_value=1000),
    )
    def test_verbatim_score_invariant_to_random_permutation(self, answer, sources, seed):
        """Random permutation also preserves score."""
        assume(len(sources) >= 2)

        result1 = verbatim_overlap(answer, sources)

        # Random shuffle
        rng = random.Random(seed)
        shuffled = list(sources)
        rng.shuffle(shuffled)
        result2 = verbatim_overlap(answer, shuffled)

        assert result1.score == result2.score


class TestClaimMatchCaseInvariant:
    """Claim matching for EMAIL/ACCOUNT_ID should be case-insensitive."""

    @PROP_SETTINGS
    @given(
        local_part=st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz0123456789.",
            min_size=1,
            max_size=15,
        ),
        domain=st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz",
            min_size=2,
            max_size=10,
        ),
        tld=st.sampled_from(["com", "org", "net", "io"]),
    )
    def test_email_match_invariant_to_case(self, local_part, domain, tld):
        """EMAIL matching is case-insensitive."""
        assume(len(local_part) >= 1 and len(domain) >= 2)
        assume(not local_part.startswith(".") and not local_part.endswith("."))
        assume(".." not in local_part)

        email = f"{local_part}@{domain}.{tld}"
        answer_lower = f"Contact at {email.lower()} for info."
        answer_upper = f"Contact at {email.upper()} for info."
        answer_mixed = f"Contact at {email.title()} for info."

        result_lower = match_claim(answer_lower, email, claim_type="EMAIL")
        result_upper = match_claim(answer_upper, email, claim_type="EMAIL")
        result_mixed = match_claim(answer_mixed, email, claim_type="EMAIL")

        # All should match (or all should not match if email is malformed)
        if result_lower.matched:
            assert result_upper.matched, "Case sensitivity: upper case failed"
            assert result_mixed.matched, "Case sensitivity: mixed case failed"

    @PROP_SETTINGS
    @given(
        prefix=st.sampled_from(["ACC", "USR", "ORD", "TXN"]),
        digits=st.integers(min_value=10000, max_value=99999999),
    )
    def test_account_id_match_invariant_to_case(self, prefix, digits):
        """ACCOUNT_ID matching is case-insensitive."""
        account_id = f"{prefix}-{digits}"

        answer_lower = f"Your account {account_id.lower()} is active."
        answer_upper = f"Your account {account_id.upper()} is active."

        result_lower = match_claim(answer_lower, account_id, claim_type="ACCOUNT_ID")
        result_upper = match_claim(answer_upper, account_id, claim_type="ACCOUNT_ID")

        # Both should match
        assert result_lower.matched, f"Lower case failed for {account_id}"
        assert result_upper.matched, f"Upper case failed for {account_id}"

    @PROP_SETTINGS
    @given(
        prefix=st.sampled_from(["ACC", "USR", "ORD"]),
        digits=st.integers(min_value=10000, max_value=99999999),
        punctuation=st.sampled_from(["", ".", ",", "!", " "]),
    )
    def test_account_id_match_with_surrounding_punctuation(self, prefix, digits, punctuation):
        """ACCOUNT_ID matching works with surrounding punctuation."""
        account_id = f"{prefix}-{digits}"
        answer = f"Account:{punctuation}{account_id}{punctuation}done"

        result = match_claim(answer, account_id, claim_type="ACCOUNT_ID")
        assert result.matched, f"Punctuation test failed for {answer}"


class TestCanaryNoFalsePositives:
    """Canary detection should not produce false positives on random strings."""

    @PROP_SETTINGS
    @given(text=safe_chars)
    def test_no_false_positive_on_random_text(self, text):
        """Random text without CANARY_ prefix should not be detected."""
        assume("CANARY_" not in text)

        result = detect_canary(text)

        assert not result.present, f"False positive on: {text!r}"
        assert result.count == 0
        assert result.matches == []

    @PROP_SETTINGS
    @given(
        prefix=st.text(min_size=0, max_size=50),
        suffix=st.text(min_size=0, max_size=50),
    )
    def test_no_false_positive_with_partial_canary_prefix(self, prefix, suffix):
        """Partial CANARY prefix (e.g., CANAR) should not match."""
        assume("CANARY_" not in prefix and "CANARY_" not in suffix)

        # Build text with partial prefixes that look like canaries but aren't
        test_texts = [
            f"{prefix}CANAR{suffix}",
            f"{prefix}CANARY{suffix}",  # Missing underscore
            f"{prefix}CANARY_{suffix}",  # Underscore but not 16 hex chars after
            f"{prefix}CANARY_123{suffix}",  # Too few hex chars
            f"{prefix}CANARY_ghij1234567890ab{suffix}",  # Invalid hex (ghij)
        ]

        for text in test_texts:
            result = detect_canary(text)
            assert not result.present, f"False positive on: {text!r}"

    @PROP_SETTINGS
    @given(
        hex_chars=st.text(
            alphabet="0123456789abcdef",
            min_size=16,
            max_size=16,
        ),
        prefix=st.text(min_size=0, max_size=20),
        suffix=st.text(min_size=0, max_size=20),
    )
    def test_true_canary_is_detected(self, hex_chars, prefix, suffix):
        """Valid CANARY_ pattern should be detected."""
        assume("CANARY_" not in prefix and "CANARY_" not in suffix)

        canary = f"CANARY_{hex_chars}"
        text = f"{prefix}{canary}{suffix}"

        result = detect_canary(text)

        assert result.present, f"Missed valid canary in: {text!r}"
        assert result.count >= 1
        assert canary in result.matches
