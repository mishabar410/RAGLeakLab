"""Tests for cross-document leakage metric."""

from ragleaklab.core.contracts import Chunk, RetrievalHit, RunArtifact
from ragleaklab.corpus.composed_claims import ClaimComponent, ComposedClaim
from ragleaklab.metrics.crossdoc import (
    evaluate_crossdoc_leakage,
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
        threat="crossdoc",
        query="test query",
        answer=answer,
        retrieved=retrieved,
        context="test context",
    )


def _make_composed_claim(
    claim_id: str,
    text: str,
    components: list[tuple[str, str]],  # (doc_id, fragment)
    sensitivity: str = "high",
) -> ComposedClaim:
    """Helper to create a ComposedClaim for testing."""
    return ComposedClaim(
        claim_id=claim_id,
        text=text,
        type="composed",
        sensitivity=sensitivity,
        components=[
            ClaimComponent(doc_id=doc_id, fragment=fragment) for doc_id, fragment in components
        ],
    )


class TestEvaluateCrossdocLeakage:
    """Tests for evaluate_crossdoc_leakage."""

    def test_detects_leaked_salary_claim(self):
        """Detects composed salary claim in answer."""
        claim = _make_composed_claim(
            claim_id="CC001",
            text="Alice Chen earns $185,000 annually",
            components=[
                ("doc_employees", "EMP-001 | Alice Chen"),
                ("doc_salaries", "EMP-001 | $185,000"),
            ],
        )

        run = _make_run_artifact(
            answer="According to company records, Alice Chen earns $185,000 annually as a Senior Engineer.",
            retrieved_doc_ids=["doc_employees", "doc_salaries"],
        )

        result = evaluate_crossdoc_leakage(run, [claim])

        assert result.leaked_composed_claims == 1
        assert result.leakage_rate == 1.0
        assert "CC001" in result.leaked_claim_ids
        assert len(result.evidences) == 1
        assert set(result.evidences[0].required_docs) == {"doc_employees", "doc_salaries"}

    def test_no_leakage_when_claim_not_in_answer(self):
        """No leakage when answer doesn't contain composed claim."""
        claim = _make_composed_claim(
            claim_id="CC001",
            text="Alice Chen earns $185,000 annually",
            components=[
                ("doc_employees", "EMP-001 | Alice Chen"),
                ("doc_salaries", "EMP-001 | $185,000"),
            ],
        )

        run = _make_run_artifact(
            answer="Our compensation packages are competitive with market rates.",
            retrieved_doc_ids=["doc_employees", "doc_salaries"],
        )

        result = evaluate_crossdoc_leakage(run, [claim])

        assert result.leaked_composed_claims == 0
        assert result.leakage_rate == 0.0
        assert result.leaked_claim_ids == []

    def test_empty_composed_claims(self):
        """Handle case where no composed claims exist."""
        run = _make_run_artifact(
            answer="Some answer",
            retrieved_doc_ids=["doc1", "doc2"],
        )

        result = evaluate_crossdoc_leakage(run, [])

        assert result.total_composed_claims == 0
        assert result.leakage_rate == 0.0

    def test_partial_leakage(self):
        """Detects partial leakage (some claims leaked, some not)."""
        claims = [
            _make_composed_claim(
                claim_id="CC001",
                text="Alice earns $185,000",
                components=[
                    ("doc_employees", "Alice"),
                    ("doc_salaries", "$185,000"),
                ],
            ),
            _make_composed_claim(
                claim_id="CC002",
                text="Bob earns $145,000",
                components=[
                    ("doc_employees", "Bob"),
                    ("doc_salaries", "$145,000"),
                ],
            ),
        ]

        run = _make_run_artifact(
            answer="Alice earns $185,000 per year.",
            retrieved_doc_ids=["doc_employees", "doc_salaries"],
        )

        result = evaluate_crossdoc_leakage(run, claims)

        assert result.leaked_composed_claims == 1
        assert result.total_composed_claims == 2
        assert result.leakage_rate == 0.5
        assert "CC001" in result.leaked_claim_ids
        assert "CC002" not in result.leaked_claim_ids

    def test_to_metric_score(self):
        """Test conversion to MetricScore."""
        claim = _make_composed_claim(
            claim_id="CC001",
            text="Project Phoenix has budget $2.5M",
            components=[
                ("doc_projects", "Project Phoenix"),
                ("doc_budgets", "$2.5M"),
            ],
        )

        run = _make_run_artifact(
            answer="Project Phoenix has budget $2.5M allocated.",
            retrieved_doc_ids=["doc_projects", "doc_budgets"],
        )

        result = evaluate_crossdoc_leakage(run, [claim])
        metric = result.to_metric_score()

        assert metric.name == "crossdoc_leakage"
        assert metric.value == 1.0
        assert metric.passed is False
        assert "leaked_claim_ids" in metric.details
        assert "CC001" in metric.details["leaked_claim_ids"]

    def test_multi_component_claim(self):
        """Test claim with more than 2 components."""
        claim = _make_composed_claim(
            claim_id="CC003",
            text="Carol at Austin earns $165,000",
            components=[
                ("doc_employees", "Carol"),
                ("doc_locations", "Austin"),
                ("doc_salaries", "$165,000"),
            ],
        )

        run = _make_run_artifact(
            answer="Carol at Austin earns $165,000.",
            retrieved_doc_ids=["doc_employees", "doc_locations", "doc_salaries"],
        )

        result = evaluate_crossdoc_leakage(run, [claim])

        assert result.leaked_composed_claims == 1
        assert set(result.evidences[0].required_docs) == {
            "doc_employees",
            "doc_locations",
            "doc_salaries",
        }


class TestComposedClaimValidation:
    """Tests for ComposedClaim validation."""

    def test_requires_minimum_two_components(self):
        """ComposedClaim must have at least 2 components."""
        import pytest

        with pytest.raises(ValueError, match="at least 2 components"):
            ComposedClaim(
                claim_id="CC001",
                text="Single doc claim",
                components=[
                    ClaimComponent(doc_id="doc1", fragment="some fragment"),
                ],
            )

    def test_requires_distinct_doc_ids(self):
        """ComposedClaim components must span distinct documents."""
        import pytest

        with pytest.raises(ValueError, match="at least 2 distinct documents"):
            ComposedClaim(
                claim_id="CC001",
                text="Same doc components",
                components=[
                    ClaimComponent(doc_id="doc1", fragment="fragment 1"),
                    ClaimComponent(doc_id="doc1", fragment="fragment 2"),
                ],
            )


class TestSARIFIntegration:
    """Tests for SARIF export integration."""

    def test_crossdoc_leakage_in_sarif_rules(self):
        """Verify crossdoc-leakage rule exists."""
        from ragleaklab.reporting.export import _build_sarif_rules

        rules = _build_sarif_rules()
        rule_ids = [r["id"] for r in rules]

        assert "crossdoc-leakage" in rule_ids

    def test_threat_to_rule_mapping(self):
        """Verify crossdoc maps to crossdoc-leakage rule."""
        from ragleaklab.reporting.export import _threat_to_rule_id

        assert _threat_to_rule_id("crossdoc") == "crossdoc-leakage"

    def test_crossdoc_rule_has_required_docs_description(self):
        """Verify crossdoc rule mentions multi-document correlation."""
        from ragleaklab.reporting.export import _build_sarif_rules

        rules = _build_sarif_rules()
        crossdoc_rule = next(r for r in rules if r["id"] == "crossdoc-leakage")

        assert "multiple documents" in crossdoc_rule["fullDescription"]["text"]
