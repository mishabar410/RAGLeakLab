"""Tests for relevance hijack pack and integrity metrics."""

import pytest

from ragleaklab.metrics.integrity import (
    IntegrityMetricsResult,
    evaluate_integrity_metrics,
    poison_mrr,
    poison_rate_at_k,
    true_doc_recall_at_k,
)
from ragleaklab.poisoning.packs.relevance_hijack import (
    RelevanceHijackManifest,
    RelevanceHijackQuery,
    RelevanceHijackResult,
    evaluate_relevance_hijack,
    get_relevance_hijack_pack_path,
    load_relevance_hijack_pack,
)


class TestIntegrityMetricFunctions:
    """Tests for individual integrity metric functions."""

    def test_poison_rate_at_k_no_poison(self):
        """poison_rate_at_k returns 0 when no poison in top-k."""
        retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        poison_ids = {"poison1", "poison2"}
        rate = poison_rate_at_k(retrieved, poison_ids, k=5)
        assert rate == 0.0

    def test_poison_rate_at_k_some_poison(self):
        """poison_rate_at_k correctly calculates rate."""
        retrieved = ["doc1", "poison1", "doc2", "poison2", "doc3"]
        poison_ids = {"poison1", "poison2"}
        rate = poison_rate_at_k(retrieved, poison_ids, k=5)
        assert rate == 0.4  # 2 out of 5

    def test_poison_rate_at_k_all_poison(self):
        """poison_rate_at_k returns 1.0 when all are poison."""
        retrieved = ["poison1", "poison2", "poison3"]
        poison_ids = {"poison1", "poison2", "poison3"}
        rate = poison_rate_at_k(retrieved, poison_ids, k=3)
        assert rate == 1.0

    def test_poison_rate_at_k_respects_limit(self):
        """poison_rate_at_k only considers top-k."""
        retrieved = ["doc1", "doc2", "poison1", "poison2", "poison3"]
        poison_ids = {"poison1", "poison2", "poison3"}
        rate = poison_rate_at_k(retrieved, poison_ids, k=2)
        assert rate == 0.0  # Only looks at first 2

    def test_poison_rate_at_k_empty_results(self):
        """poison_rate_at_k handles empty results."""
        rate = poison_rate_at_k([], {"poison1"}, k=10)
        assert rate == 0.0

    def test_poison_mrr_no_poison(self):
        """poison_mrr returns 0 when no poison."""
        retrieved = ["doc1", "doc2", "doc3"]
        poison_ids = {"poison1", "poison2"}
        mrr = poison_mrr(retrieved, poison_ids)
        assert mrr == 0.0

    def test_poison_mrr_first_position(self):
        """poison_mrr returns 1.0 when poison is first."""
        retrieved = ["poison1", "doc1", "doc2"]
        poison_ids = {"poison1"}
        mrr = poison_mrr(retrieved, poison_ids)
        assert mrr == 1.0

    def test_poison_mrr_later_position(self):
        """poison_mrr correctly calculates for later positions."""
        retrieved = ["doc1", "doc2", "poison1", "doc3"]
        poison_ids = {"poison1"}
        mrr = poison_mrr(retrieved, poison_ids)
        assert mrr == 1 / 3  # Position 3 (1-indexed)

    def test_true_doc_recall_at_k_all_found(self):
        """true_doc_recall_at_k returns 1.0 when all expected found."""
        retrieved = ["doc1", "doc2", "doc3", "other"]
        expected_ids = {"doc1", "doc2", "doc3"}
        recall = true_doc_recall_at_k(retrieved, expected_ids, k=10)
        assert recall == 1.0

    def test_true_doc_recall_at_k_none_found(self):
        """true_doc_recall_at_k returns 0 when none found."""
        retrieved = ["other1", "other2"]
        expected_ids = {"doc1", "doc2"}
        recall = true_doc_recall_at_k(retrieved, expected_ids, k=10)
        assert recall == 0.0

    def test_true_doc_recall_at_k_partial(self):
        """true_doc_recall_at_k correctly calculates partial recall."""
        retrieved = ["doc1", "other", "doc3"]
        expected_ids = {"doc1", "doc2", "doc3"}
        recall = true_doc_recall_at_k(retrieved, expected_ids, k=10)
        assert recall == 2 / 3

    def test_true_doc_recall_at_k_respects_limit(self):
        """true_doc_recall_at_k only considers top-k."""
        retrieved = ["other1", "other2", "doc1", "doc2"]
        expected_ids = {"doc1", "doc2"}
        recall = true_doc_recall_at_k(retrieved, expected_ids, k=2)
        assert recall == 0.0  # Only looks at first 2

    def test_true_doc_recall_at_k_empty_expected(self):
        """true_doc_recall_at_k returns 1.0 when no expected docs."""
        retrieved = ["doc1", "doc2"]
        expected_ids = set()
        recall = true_doc_recall_at_k(retrieved, expected_ids, k=10)
        assert recall == 1.0


class TestEvaluateIntegrityMetrics:
    """Tests for the evaluate_integrity_metrics function."""

    def test_basic_evaluation(self):
        """evaluate_integrity_metrics returns correct result."""
        result = evaluate_integrity_metrics(
            retrieved_ids=["doc1", "poison1", "doc2"],
            retrieved_scores=[0.9, 0.8, 0.7],
            poison_ids={"poison1"},
            expected_ids={"doc1", "doc2"},
            query_id="q1",
            k=10,
        )

        assert isinstance(result, IntegrityMetricsResult)
        assert result.query_id == "q1"
        assert result.poison_rate == pytest.approx(1 / 3)
        assert result.poison_mrr_value == pytest.approx(0.5)  # Position 2
        assert result.true_recall == pytest.approx(2 / 2)

    def test_evaluation_with_thresholds_pass(self):
        """evaluate_integrity_metrics applies thresholds correctly for pass."""
        thresholds = {
            "poison_rate_at_k": {"max_rate": 0.5},
            "poison_mrr": {"max_mrr": 0.5},
            "true_doc_recall_at_k": {"min_recall": 0.5},
        }
        result = evaluate_integrity_metrics(
            retrieved_ids=["doc1", "doc2", "doc3"],
            retrieved_scores=[0.9, 0.8, 0.7],
            poison_ids={"poison1"},
            expected_ids={"doc1"},
            query_id="q1",
            k=10,
            thresholds=thresholds,
        )

        assert result.poison_rate_passed is True
        assert result.poison_mrr_passed is True
        assert result.true_recall_passed is True

    def test_evaluation_with_thresholds_fail(self):
        """evaluate_integrity_metrics applies thresholds correctly for fail."""
        thresholds = {
            "poison_rate_at_k": {"max_rate": 0.1},
            "poison_mrr": {"max_mrr": 0.1},
            "true_doc_recall_at_k": {"min_recall": 1.0},
        }
        result = evaluate_integrity_metrics(
            retrieved_ids=["poison1", "doc1", "doc2"],
            retrieved_scores=[0.9, 0.8, 0.7],
            poison_ids={"poison1"},
            expected_ids={"doc1", "doc3"},  # doc3 not found
            query_id="q1",
            k=10,
            thresholds=thresholds,
        )

        # At least one threshold should fail
        assert (
            result.poison_rate_passed is False
            or result.poison_mrr_passed is False
            or result.true_recall_passed is False
        )


class TestRelevanceHijackPackLoading:
    """Tests for loading the relevance hijack pack."""

    def test_get_pack_path(self):
        """get_relevance_hijack_pack_path returns valid path."""
        path = get_relevance_hijack_pack_path()
        assert path.exists()
        assert path.is_dir()
        assert (path / "manifest.yaml").exists()

    def test_load_pack_manifest(self):
        """load_relevance_hijack_pack loads manifest correctly."""
        path = get_relevance_hijack_pack_path()
        pack = load_relevance_hijack_pack(path)

        assert isinstance(pack.manifest, RelevanceHijackManifest)
        assert pack.manifest.name == "relevance-hijack"
        assert pack.manifest.version == "1.0.0"

    def test_load_pack_queries(self):
        """load_relevance_hijack_pack loads queries."""
        path = get_relevance_hijack_pack_path()
        pack = load_relevance_hijack_pack(path)

        assert len(pack.queries) == 15
        for query in pack.queries:
            assert isinstance(query, RelevanceHijackQuery)
            assert query.query_id
            assert query.query  # The text field is 'query', not 'query_text'
            assert len(query.expected_doc_ids) > 0

    def test_load_pack_labels(self):
        """load_relevance_hijack_pack loads poison/legit labels."""
        path = get_relevance_hijack_pack_path()
        pack = load_relevance_hijack_pack(path)

        assert len(pack.poison_ids) == 10
        assert len(pack.legit_ids) == 15
        assert pack.poison_ids.isdisjoint(pack.legit_ids)

    def test_pack_thresholds(self):
        """Pack has correct thresholds."""
        path = get_relevance_hijack_pack_path()
        pack = load_relevance_hijack_pack(path)

        thresholds = pack.get_thresholds()
        assert "poison_rate_at_k" in thresholds
        assert "poison_mrr" in thresholds
        assert "true_doc_recall_at_k" in thresholds


class TestEvaluateRelevanceHijack:
    """Tests for the evaluate_relevance_hijack function."""

    def test_evaluation_clean_results(self):
        """evaluate_relevance_hijack returns clean result for non-poisoned retrieval."""
        path = get_relevance_hijack_pack_path()
        pack = load_relevance_hijack_pack(path)

        # Create results with no poison docs
        retrieved_results = {
            q.query_id: (
                list(q.expected_doc_ids)[:10],
                [0.9 - i * 0.1 for i in range(len(q.expected_doc_ids[:10]))],
            )
            for q in pack.queries
        }

        result = evaluate_relevance_hijack(pack, retrieved_results, k=10)

        assert isinstance(result, RelevanceHijackResult)
        assert result.pack_id == "relevance-hijack"
        assert result.avg_poison_rate == 0.0
        assert result.avg_poison_mrr == 0.0
        assert result.queries_with_poison == 0
        assert result.overall_passed is True

    def test_evaluation_poisoned_results(self):
        """evaluate_relevance_hijack detects poisoning."""
        path = get_relevance_hijack_pack_path()
        pack = load_relevance_hijack_pack(path)

        # Create results with poison docs at top
        poison_list = list(pack.poison_ids)
        retrieved_results = {
            q.query_id: (poison_list[:5], [0.9 - i * 0.1 for i in range(5)]) for q in pack.queries
        }

        result = evaluate_relevance_hijack(pack, retrieved_results, k=10)

        assert result.avg_poison_rate > 0
        assert result.avg_poison_mrr > 0
        assert result.queries_with_poison > 0
        assert len(result.evidences) > 0
        assert result.overall_passed is False

    def test_evaluation_generates_evidence(self):
        """evaluate_relevance_hijack generates evidence for violations."""
        path = get_relevance_hijack_pack_path()
        pack = load_relevance_hijack_pack(path)

        # Create results with poison in first position
        poison_id = next(iter(pack.poison_ids))
        retrieved_results = {pack.queries[0].query_id: ([poison_id, "legit_doc_001"], [0.95, 0.8])}

        result = evaluate_relevance_hijack(pack, retrieved_results, k=10)

        assert len(result.evidences) == 1
        evidence = result.evidences[0]
        assert evidence.query_id == pack.queries[0].query_id  # query_id, not pack_id
        assert poison_id in evidence.details.get("poison_in_top_k", [])

    def test_to_integrity_section(self):
        """RelevanceHijackResult.to_integrity_section produces valid section."""
        path = get_relevance_hijack_pack_path()
        pack = load_relevance_hijack_pack(path)

        # Run evaluation with some poison
        poison_id = next(iter(pack.poison_ids))
        retrieved_results = {pack.queries[0].query_id: ([poison_id], [0.9])}

        result = evaluate_relevance_hijack(pack, retrieved_results, k=10)
        section = result.to_integrity_section()

        assert section.integrity_summary.total_findings == len(result.evidences)


class TestRelevanceHijackPackIntegration:
    """Integration tests for the full pack."""

    def test_pack_exists_in_registry(self):
        """relevance-hijack pack is registered."""
        from ragleaklab.poisoning.packs import AVAILABLE_POISONING_PACKS

        assert "relevance-hijack" in AVAILABLE_POISONING_PACKS

    def test_pack_path_from_registry(self):
        """get_poisoning_pack_path returns relevance-hijack path."""
        from ragleaklab.poisoning.packs import get_poisoning_pack_path

        path = get_poisoning_pack_path("relevance-hijack")
        assert path.exists()
        assert path.is_dir()
        assert (path / "manifest.yaml").exists()

    def test_manifest_has_expected_structure(self):
        """Pack manifest has expected fields."""
        path = get_relevance_hijack_pack_path()
        pack = load_relevance_hijack_pack(path)

        # Check expected report fields
        assert "integrity.retrieval.poison_rate_at_k" in pack.manifest.expected_report_fields

    def test_corpus_files_exist(self):
        """Corpus files exist and are valid JSONL."""
        import json

        path = get_relevance_hijack_pack_path()

        legit_path = path / "corpus" / "legit.jsonl"
        poison_path = path / "corpus" / "poison.jsonl"

        assert legit_path.exists()
        assert poison_path.exists()

        # Verify JSONL format
        with legit_path.open() as f:
            for line in f:
                doc = json.loads(line)
                assert "doc_id" in doc
                assert "text" in doc  # Corpus uses 'text' field
