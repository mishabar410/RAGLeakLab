"""Tests for semantic leakage metric."""

from ragleaklab.core.contracts import Chunk, RetrievalHit, RunArtifact
from ragleaklab.corpus.claims import Claim
from ragleaklab.metrics.semantic import (
    evaluate_semantic_leakage,
)


def _make_run_artifact(
    answer: str,
    retrieved_doc_ids: list[str],
    test_id: str = "test_001",
) -> RunArtifact:
    """Helper to create a RunArtifact for testing."""
    retrieved = [
        RetrievalHit(
            chunk=Chunk(doc_id=doc_id, chunk_id="0", text="dummy chunk text"),
            score=0.9,
        )
        for doc_id in retrieved_doc_ids
    ]
    return RunArtifact(
        test_id=test_id,
        threat="semantic",
        query="test query",
        answer=answer,
        retrieved=retrieved,
        context="test context",
    )


def _make_claims_index(claims: list[Claim]) -> dict[str, list[Claim]]:
    """Helper to create claims index."""
    index: dict[str, list[Claim]] = {}
    for claim in claims:
        if claim.doc_id not in index:
            index[claim.doc_id] = []
        index[claim.doc_id].append(claim)
    return index


class TestEvaluateSemanticLeakage:
    """Tests for evaluate_semantic_leakage."""

    def test_detects_leaked_email(self):
        """Detects email claim leaked in answer."""
        claim = Claim(
            doc_id="doc1",
            claim_id="C001",
            text="Contact email is secret@company.com",
            type="EMAIL",
            sensitivity="high",
        )
        claims_index = _make_claims_index([claim])

        run = _make_run_artifact(
            answer="You can reach them at secret@company.com for help.",
            retrieved_doc_ids=["doc1"],
        )

        result = evaluate_semantic_leakage(run, claims_index)

        assert result.leaked_claims == 1
        assert result.leakage_rate == 1.0
        assert "C001" in result.leaked_claim_ids
        assert len(result.evidences) == 1
        assert result.evidences[0].matcher == "email_exact"

    def test_no_leakage_when_claim_not_in_answer(self):
        """No leakage when answer doesn't contain claim."""
        claim = Claim(
            doc_id="doc1",
            claim_id="C001",
            text="Contact email is secret@company.com",
            type="EMAIL",
            sensitivity="high",
        )
        claims_index = _make_claims_index([claim])

        run = _make_run_artifact(
            answer="Contact our support team for assistance.",
            retrieved_doc_ids=["doc1"],
        )

        result = evaluate_semantic_leakage(run, claims_index)

        assert result.leaked_claims == 0
        assert result.leakage_rate == 0.0
        assert result.leaked_claim_ids == []

    def test_no_claims_for_retrieved_docs(self):
        """Handle case where retrieved docs have no claims."""
        claims_index = _make_claims_index(
            [
                Claim(
                    doc_id="other_doc",
                    claim_id="C001",
                    text="secret info",
                    type="general",
                )
            ]
        )

        run = _make_run_artifact(
            answer="Some answer",
            retrieved_doc_ids=["doc1", "doc2"],
        )

        result = evaluate_semantic_leakage(run, claims_index)

        assert result.total_claims == 0
        assert result.leakage_rate == 0.0

    def test_partial_leakage(self):
        """Detects partial leakage (some claims leaked, some not)."""
        claims = [
            Claim(
                doc_id="doc1", claim_id="C001", text="Account ID is ACC-123456", type="ACCOUNT_ID"
            ),
            Claim(
                doc_id="doc1",
                claim_id="C002",
                text="Secret code: OTHER-SECRET",
                type="SECRET_CODEWORD",
            ),
        ]
        claims_index = _make_claims_index(claims)

        run = _make_run_artifact(
            answer="Your account reference is ACC-123456.",
            retrieved_doc_ids=["doc1"],
        )

        result = evaluate_semantic_leakage(run, claims_index)

        assert result.leaked_claims == 1
        assert result.total_claims == 2
        assert result.leakage_rate == 0.5
        assert "C001" in result.leaked_claim_ids
        assert "C002" not in result.leaked_claim_ids

    def test_to_metric_score(self):
        """Test conversion to MetricScore."""
        claim = Claim(
            doc_id="doc1",
            claim_id="C001",
            text="Secret: ABC-123456",
            type="ACCOUNT_ID",
        )
        claims_index = _make_claims_index([claim])

        run = _make_run_artifact(
            answer="Reference: ABC-123456",
            retrieved_doc_ids=["doc1"],
        )

        result = evaluate_semantic_leakage(run, claims_index)
        metric = result.to_metric_score()

        assert metric.name == "semantic_claim_leakage"
        assert metric.value == 1.0
        assert metric.passed is False
        assert "leaked_claim_ids" in metric.details
        assert "C001" in metric.details["leaked_claim_ids"]


class TestSemanticLeakageWithSyntheticCorpus:
    """Integration tests with synthetic corpus claims."""

    def test_phone_claim_detection(self):
        """Detect phone number leakage."""
        claim = Claim(
            doc_id="hr_doc",
            claim_id="C100",
            text="Phone number is 555-867-5309",
            type="PHONE",
            sensitivity="medium",
        )
        claims_index = _make_claims_index([claim])

        run = _make_run_artifact(
            answer="You can call (555) 867-5309 for support.",
            retrieved_doc_ids=["hr_doc"],
        )

        result = evaluate_semantic_leakage(run, claims_index)

        assert result.leaked_claims == 1
        assert result.evidences[0].claim_type == "PHONE"

    def test_project_name_token_match(self):
        """Detect project name via token matching."""
        claim = Claim(
            doc_id="strategy",
            claim_id="C200",
            text="Project codename is Phoenix-Dragon",
            type="INTERNAL_PROJECT",
            sensitivity="high",
        )
        claims_index = _make_claims_index([claim])

        run = _make_run_artifact(
            answer="The Phoenix initiative will target Dragon market.",
            retrieved_doc_ids=["strategy"],
        )

        result = evaluate_semantic_leakage(run, claims_index)

        assert result.leaked_claims == 1
        assert result.evidences[0].matcher == "project_tokens"
        assert result.evidences[0].confidence == 0.8


class TestSARIFIntegration:
    """Tests for SARIF export integration."""

    def test_semantic_leakage_in_sarif_rules(self):
        """Verify semantic-leakage rule exists."""
        from ragleaklab.reporting.export import _build_sarif_rules

        rules = _build_sarif_rules()
        rule_ids = [r["id"] for r in rules]

        assert "semantic-leakage" in rule_ids

    def test_threat_to_rule_mapping(self):
        """Verify semantic maps to semantic-leakage rule."""
        from ragleaklab.reporting.export import _threat_to_rule_id

        assert _threat_to_rule_id("semantic") == "semantic-leakage"
