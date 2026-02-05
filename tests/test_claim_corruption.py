"""Tests for claim corruption pack and claim matching."""

from ragleaklab.poisoning.packs import (
    AVAILABLE_POISONING_PACKS,
    get_poisoning_pack_path,
)
from ragleaklab.poisoning.packs.claim_corruption import (
    ClaimCorruptionManifest,
    ClaimCorruptionQuery,
    PoisonClaim,
    TrueClaim,
    evaluate_claim_corruption,
    evaluate_query_claims,
    fingerprint_claim,
    get_claim_corruption_pack_path,
    load_claim_corruption_pack,
    match_claims_in_text,
    normalize_text,
)


class TestNormalizeText:
    """Tests for text normalization."""

    def test_lowercase(self):
        """normalize_text converts to lowercase."""
        assert normalize_text("HELLO World") == "hello world"

    def test_removes_punctuation(self):
        """normalize_text removes punctuation."""
        assert normalize_text("Hello, World!") == "hello world"

    def test_collapses_whitespace(self):
        """normalize_text collapses multiple spaces."""
        assert normalize_text("hello    world") == "hello world"

    def test_strips_whitespace(self):
        """normalize_text strips leading/trailing whitespace."""
        assert normalize_text("  hello world  ") == "hello world"

    def test_unicode_normalization(self):
        """normalize_text handles unicode characters."""
        # NFKC normalization
        assert normalize_text("ﬁle") == "file"  # fi ligature

    def test_empty_string(self):
        """normalize_text handles empty string."""
        assert normalize_text("") == ""


class TestFingerprintClaim:
    """Tests for claim fingerprinting."""

    def test_deterministic(self):
        """fingerprint_claim returns same hash for same input."""
        claim = "Python 3.12 was released in October 2023"
        fp1 = fingerprint_claim(claim)
        fp2 = fingerprint_claim(claim)
        assert fp1 == fp2

    def test_case_insensitive(self):
        """fingerprint_claim is case insensitive."""
        fp1 = fingerprint_claim("Hello World")
        fp2 = fingerprint_claim("hello world")
        assert fp1 == fp2

    def test_punctuation_invariant(self):
        """fingerprint_claim ignores punctuation."""
        fp1 = fingerprint_claim("Hello, World!")
        fp2 = fingerprint_claim("Hello World")
        assert fp1 == fp2

    def test_different_claims_different_fingerprints(self):
        """fingerprint_claim returns different hashes for different claims."""
        fp1 = fingerprint_claim("Python 3.12 was released in October 2023")
        fp2 = fingerprint_claim("Python 3.12 was released in March 2024")
        assert fp1 != fp2


class TestMatchClaimsInText:
    """Tests for claim matching in text."""

    def test_matches_true_claim(self):
        """match_claims_in_text finds true claims."""
        true_claims = [TrueClaim(claim_id="tc_001", claim="Python is a programming language")]
        poison_claims: list[PoisonClaim] = []

        text = "Python is a programming language used for web development."
        matched_true, matched_poison = match_claims_in_text(
            text, {}, {}, true_claims, poison_claims
        )

        assert "tc_001" in matched_true
        assert len(matched_poison) == 0

    def test_matches_poison_claim(self):
        """match_claims_in_text finds poison claims."""
        true_claims: list[TrueClaim] = []
        poison_claims = [PoisonClaim(claim_id="pc_001", claim="Python is deprecated")]

        text = "Python is deprecated and should not be used."
        matched_true, matched_poison = match_claims_in_text(
            text, {}, {}, true_claims, poison_claims
        )

        assert len(matched_true) == 0
        assert "pc_001" in matched_poison

    def test_case_insensitive_matching(self):
        """match_claims_in_text matches regardless of case."""
        true_claims = [TrueClaim(claim_id="tc_001", claim="HTTP 404 means not found")]
        poison_claims: list[PoisonClaim] = []

        text = "http 404 means not found when the resource is missing"
        matched_true, _matched_poison = match_claims_in_text(
            text, {}, {}, true_claims, poison_claims
        )

        assert "tc_001" in matched_true

    def test_no_match(self):
        """match_claims_in_text returns empty when no match."""
        true_claims = [TrueClaim(claim_id="tc_001", claim="Python is great")]
        poison_claims: list[PoisonClaim] = []

        text = "JavaScript is a scripting language."
        matched_true, matched_poison = match_claims_in_text(
            text, {}, {}, true_claims, poison_claims
        )

        assert len(matched_true) == 0
        assert len(matched_poison) == 0


class TestEvaluateQueryClaims:
    """Tests for single query claim evaluation."""

    def test_full_recall(self):
        """evaluate_query_claims calculates recall correctly."""
        path = get_claim_corruption_pack_path()
        pack = load_claim_corruption_pack(path)

        # Create a query with expected claims
        query = ClaimCorruptionQuery(
            query_id="test_q",
            query="test",
            expected_claim_ids=["tc_001"],
        )

        # Text contains the expected claim
        text = "Python 3.12 was released in October 2023 with many improvements."
        result = evaluate_query_claims(query, text, pack)

        assert result.true_claim_recall == 1.0
        assert "tc_001" in result.matched_true_claims

    def test_zero_recall(self):
        """evaluate_query_claims handles zero recall."""
        path = get_claim_corruption_pack_path()
        pack = load_claim_corruption_pack(path)

        query = ClaimCorruptionQuery(
            query_id="test_q",
            query="test",
            expected_claim_ids=["tc_001"],
        )

        # Text doesn't contain the expected claim
        text = "JavaScript is a popular language."
        result = evaluate_query_claims(query, text, pack)

        assert result.true_claim_recall == 0.0

    def test_poison_detection(self):
        """evaluate_query_claims detects poison claims."""
        path = get_claim_corruption_pack_path()
        pack = load_claim_corruption_pack(path)

        query = ClaimCorruptionQuery(
            query_id="test_q",
            query="test",
            expected_claim_ids=["tc_001"],
        )

        # Text contains poison claim
        text = "Python 3.12 was released in March 2024 with breaking changes."
        result = evaluate_query_claims(query, text, pack)

        assert len(result.matched_poison_claims) > 0
        assert result.poison_claim_rate > 0


class TestClaimCorruptionPackLoading:
    """Tests for pack loading."""

    def test_get_pack_path(self):
        """get_claim_corruption_pack_path returns valid path."""
        path = get_claim_corruption_pack_path()
        assert path.exists()
        assert (path / "manifest.yaml").exists()

    def test_load_pack_manifest(self):
        """load_claim_corruption_pack loads manifest."""
        path = get_claim_corruption_pack_path()
        pack = load_claim_corruption_pack(path)

        assert isinstance(pack.manifest, ClaimCorruptionManifest)
        assert pack.manifest.name == "claim-corruption"
        assert pack.manifest.version == "1.0.0"

    def test_load_pack_queries(self):
        """load_claim_corruption_pack loads queries."""
        path = get_claim_corruption_pack_path()
        pack = load_claim_corruption_pack(path)

        assert len(pack.queries) == 12
        for query in pack.queries:
            assert isinstance(query, ClaimCorruptionQuery)
            assert query.query_id
            assert query.query
            assert len(query.expected_claim_ids) > 0

    def test_load_pack_claims(self):
        """load_claim_corruption_pack loads true and poison claims."""
        path = get_claim_corruption_pack_path()
        pack = load_claim_corruption_pack(path)

        assert len(pack.true_claims) == 20
        assert len(pack.poison_claims) == 15

    def test_fingerprint_indices_built(self):
        """load_claim_corruption_pack builds fingerprint indices."""
        path = get_claim_corruption_pack_path()
        pack = load_claim_corruption_pack(path)

        assert len(pack.true_claim_fingerprints) == 20
        assert len(pack.poison_claim_fingerprints) == 15

    def test_contradiction_map_built(self):
        """load_claim_corruption_pack builds contradiction map."""
        path = get_claim_corruption_pack_path()
        pack = load_claim_corruption_pack(path)

        # Most poison claims have contradictions
        assert len(pack.contradiction_map) > 0


class TestEvaluateClaimCorruption:
    """Tests for two-phase evaluation."""

    def test_clean_evaluation(self):
        """evaluate_claim_corruption handles clean-only results."""
        path = get_claim_corruption_pack_path()
        pack = load_claim_corruption_pack(path)

        # Simulate clean results with true claims
        clean_results = {}
        for query in pack.queries:
            # Build text containing expected true claims
            texts = []
            for tc in pack.true_claims:
                if tc.claim_id in query.expected_claim_ids:
                    texts.append(tc.claim)
            clean_results[query.query_id] = " ".join(texts)

        result = evaluate_claim_corruption(pack, clean_results, clean_results)

        assert result.avg_true_recall_clean > 0
        assert result.true_claim_recall_drop == 0.0

    def test_poisoned_evaluation(self):
        """evaluate_claim_corruption detects recall drop."""
        path = get_claim_corruption_pack_path()
        pack = load_claim_corruption_pack(path)

        # Clean results with true claims
        clean_results = {}
        for query in pack.queries:
            texts = []
            for tc in pack.true_claims:
                if tc.claim_id in query.expected_claim_ids:
                    texts.append(tc.claim)
            clean_results[query.query_id] = " ".join(texts)

        # Poisoned results replace true claims with poison claims
        poisoned_results = {}
        for query in pack.queries:
            # Use poison claims instead of true claims
            texts = []
            for pc in pack.poison_claims[:3]:
                texts.append(pc.claim)
            poisoned_results[query.query_id] = " ".join(texts)

        result = evaluate_claim_corruption(pack, clean_results, poisoned_results)

        assert result.avg_true_recall_clean > result.avg_true_recall_poisoned
        assert result.true_claim_recall_drop > 0

    def test_generates_evidence(self):
        """evaluate_claim_corruption generates evidence for violations."""
        path = get_claim_corruption_pack_path()
        pack = load_claim_corruption_pack(path)

        # Create results with poison
        clean_results = {pack.queries[0].query_id: ""}
        poisoned_results = {
            pack.queries[0].query_id: pack.poison_claims[0].claim,
        }

        result = evaluate_claim_corruption(pack, clean_results, poisoned_results)

        assert len(result.evidences) > 0
        evidence = result.evidences[0]
        assert evidence.query_id == pack.queries[0].query_id
        assert len(evidence.matched_poison_claims) > 0


class TestClaimCorruptionPackIntegration:
    """Integration tests for pack registration."""

    def test_pack_exists_in_registry(self):
        """claim-corruption is in AVAILABLE_POISONING_PACKS."""
        assert "claim-corruption" in AVAILABLE_POISONING_PACKS

    def test_pack_path_from_registry(self):
        """get_poisoning_pack_path returns valid path for claim-corruption."""
        path = get_poisoning_pack_path("claim-corruption")
        assert path.exists()
        assert path.is_dir()

    def test_manifest_has_expected_structure(self):
        """Pack manifest has expected fields."""
        path = get_claim_corruption_pack_path()
        pack = load_claim_corruption_pack(path)

        assert "integrity.claim.poison_claim_rate" in pack.manifest.expected_report_fields
        assert "integrity.claim.true_claim_recall" in pack.manifest.expected_report_fields

    def test_claims_files_exist(self):
        """Claims files exist and are valid JSONL."""
        import json

        path = get_claim_corruption_pack_path()

        true_claims_path = path / "claims" / "true_claims.jsonl"
        poison_claims_path = path / "claims" / "poison_claims.jsonl"

        assert true_claims_path.exists()
        assert poison_claims_path.exists()

        # Verify JSONL format
        with true_claims_path.open() as f:
            for line in f:
                claim = json.loads(line)
                assert "claim_id" in claim
                assert "claim" in claim

        with poison_claims_path.open() as f:
            for line in f:
                claim = json.loads(line)
                assert "claim_id" in claim
                assert "claim" in claim
