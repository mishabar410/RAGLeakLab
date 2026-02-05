"""Tests for poisoning pack infrastructure."""

import json
from pathlib import Path

from ragleaklab.core.contracts import (
    Chunk,
    ContextStats,
    Hashes,
    RetrievalHit,
    RunArtifact,
    Timings,
)
from ragleaklab.poisoning.packs import (
    AVAILABLE_POISONING_PACKS,
    get_poisoning_pack_path,
    get_poisoning_pack_version,
    list_poisoning_packs,
)
from ragleaklab.poisoning.packs.runner import (
    evaluate_claim_integrity,
    evaluate_retrieval_integrity,
    evaluate_sentinel_integrity,
    load_poisoning_cases,
    run_poisoning_case,
    run_poisoning_pack,
)
from ragleaklab.poisoning.packs.schema import PoisoningPackManifest, PoisoningTestCase


class TestPoisoningPackRegistry:
    """Tests for poisoning pack registry functions."""

    def test_list_poisoning_packs_returns_all(self):
        """list_poisoning_packs returns all available packs."""
        packs = list_poisoning_packs()
        assert "integrity-dummy" in packs

    def test_get_poisoning_pack_version(self):
        """get_poisoning_pack_version returns current version."""
        version = get_poisoning_pack_version()
        assert version == "v1"

    def test_get_poisoning_pack_path_valid(self):
        """get_poisoning_pack_path returns valid path for known pack."""
        for pack_name in AVAILABLE_POISONING_PACKS:
            path = get_poisoning_pack_path(pack_name)
            assert path.exists()
            # Packs can be either YAML files or directories (like relevance-hijack)
            assert path.suffix == ".yaml" or path.is_dir()

    def test_get_poisoning_pack_path_unknown_raises(self):
        """get_poisoning_pack_path raises for unknown pack."""
        import pytest

        with pytest.raises(ValueError, match="Unknown poisoning pack"):
            get_poisoning_pack_path("nonexistent-pack")


class TestPoisoningPackLoading:
    """Tests for loading poisoning pack cases."""

    def test_load_poisoning_cases_from_file(self):
        """Can load poisoning cases from pack YAML."""
        path = get_poisoning_pack_path("integrity-dummy")
        cases = load_poisoning_cases(path)

        assert len(cases) == 3
        # Verify sorted by test_id
        assert cases[0].test_id < cases[1].test_id < cases[2].test_id

    def test_load_poisoning_cases_have_required_fields(self):
        """All loaded cases have required fields."""
        path = get_poisoning_pack_path("integrity-dummy")
        cases = load_poisoning_cases(path)

        for case in cases:
            assert case.test_id
            assert case.pack_type in ("retrieval", "claim", "sentinel")
            assert case.query
            assert case.severity in ("high", "medium", "low")

    def test_poisoning_test_case_schema_validation(self):
        """PoisoningTestCase validates correctly."""
        case = PoisoningTestCase(
            test_id="test1",
            pack_type="retrieval",
            query="test query",
            expected_doc_ids=["doc1"],
        )
        assert case.test_id == "test1"
        assert case.pack_type == "retrieval"
        assert case.severity == "medium"  # default

    def test_poisoning_pack_manifest_schema(self):
        """PoisoningPackManifest validates correctly."""
        manifest = PoisoningPackManifest(
            name="test-pack",
            version="1.0.0",
            pack_type="mixed",
            test_count=5,
        )
        assert manifest.name == "test-pack"
        assert manifest.pack_type == "mixed"


class TestRetrievalIntegrityEvaluation:
    """Tests for retrieval integrity evaluation."""

    def test_no_violation_when_expected_docs_present(self):
        """No evidence when expected documents are retrieved."""
        case = PoisoningTestCase(
            test_id="test1",
            pack_type="retrieval",
            query="test",
            expected_doc_ids=["doc1", "doc2"],
        )
        actual_ids = ["doc1", "doc2", "doc3"]
        evidence = evaluate_retrieval_integrity(case, actual_ids)
        assert evidence is None

    def test_violation_when_expected_docs_missing(self):
        """Evidence generated when expected docs are missing."""
        case = PoisoningTestCase(
            test_id="test1",
            pack_type="retrieval",
            query="test",
            expected_doc_ids=["doc1", "doc2"],
            severity="high",
        )
        actual_ids = ["doc3", "doc4"]
        evidence = evaluate_retrieval_integrity(case, actual_ids)

        assert evidence is not None
        assert evidence.pack_id == "test1"
        assert evidence.severity == "high"
        assert "missing_expected" in evidence.details
        assert set(evidence.details["missing_expected"]) == {"doc1", "doc2"}

    def test_violation_when_disallowed_docs_present(self):
        """Evidence generated when disallowed docs appear."""
        case = PoisoningTestCase(
            test_id="test1",
            pack_type="retrieval",
            query="test",
            disallowed_doc_ids=["poisoned_doc"],
        )
        actual_ids = ["doc1", "poisoned_doc"]
        evidence = evaluate_retrieval_integrity(case, actual_ids)

        assert evidence is not None
        assert "disallowed_present" in evidence.details
        assert "poisoned_doc" in evidence.details["disallowed_present"]


class TestClaimIntegrityEvaluation:
    """Tests for claim integrity evaluation."""

    def test_no_violation_when_expected_claim_present(self):
        """No evidence when expected claim is in answer."""
        case = PoisoningTestCase(
            test_id="test1",
            pack_type="claim",
            query="test",
            expected_claim="correct answer",
        )
        actual_answer = "The correct answer is here."
        evidence = evaluate_claim_integrity(case, actual_answer)
        assert evidence is None

    def test_violation_when_expected_claim_missing(self):
        """Evidence generated when expected claim is missing."""
        case = PoisoningTestCase(
            test_id="test1",
            pack_type="claim",
            query="test",
            expected_claim="correct answer",
            severity="medium",
        )
        actual_answer = "Some other unrelated text."
        evidence = evaluate_claim_integrity(case, actual_answer)

        assert evidence is not None
        assert evidence.pack_id == "test1"
        assert evidence.details["expected_claim"] == "correct answer"
        assert evidence.details["actual_claim"] == actual_answer
        assert evidence.details["violation_type"] == "expected_claim_missing"

    def test_violation_when_forbidden_claim_present(self):
        """Evidence generated when forbidden claim appears."""
        case = PoisoningTestCase(
            test_id="test1",
            pack_type="claim",
            query="test",
            forbidden_claim="poisoned content",
        )
        actual_answer = "The answer contains poisoned content here."
        evidence = evaluate_claim_integrity(case, actual_answer)

        assert evidence is not None
        assert evidence.details["violation_type"] == "forbidden_claim_present"


class TestSentinelIntegrityEvaluation:
    """Tests for sentinel/backdoor integrity evaluation."""

    def test_no_violation_when_trigger_not_present(self):
        """No evidence when trigger phrase not in answer."""
        case = PoisoningTestCase(
            test_id="test1",
            pack_type="sentinel",
            query="test",
            sentinel_type="trigger",
            trigger_phrase="backdoor activated",
        )
        actual_answer = "Normal response without trigger."
        evidence = evaluate_sentinel_integrity(case, actual_answer)
        assert evidence is None

    def test_violation_when_trigger_detected(self):
        """Evidence generated when trigger phrase detected."""
        case = PoisoningTestCase(
            test_id="test1",
            pack_type="sentinel",
            query="test",
            sentinel_type="trigger",
            trigger_phrase="backdoor activated",
            severity="high",
        )
        actual_answer = "Response with backdoor activated in it."
        evidence = evaluate_sentinel_integrity(case, actual_answer)

        assert evidence is not None
        assert evidence.pack_id == "test1"
        assert evidence.severity == "high"
        assert evidence.triggered is True
        assert evidence.sentinel_type == "trigger"


class TestPoisoningPackRunner:
    """Tests for the complete pack runner."""

    def _make_artifact(
        self, test_id: str, answer: str, doc_ids: list[str] | None = None
    ) -> RunArtifact:
        """Create a test RunArtifact."""
        doc_ids = doc_ids or []
        retrieved = [
            RetrievalHit(
                chunk=Chunk(doc_id=doc_id, chunk_id="0", text=""),
                score=1.0,
            )
            for doc_id in doc_ids
        ]
        return RunArtifact(
            test_id=test_id,
            threat="poisoning",
            query="test query",
            answer=answer,
            context="test context",
            retrieved=retrieved,
            timings=Timings(),
            context_stats=ContextStats(context_chars=100, n_chunks=len(doc_ids)),
            hashes=Hashes(),
            meta={},
        )

    def test_run_poisoning_case_retrieval(self):
        """run_poisoning_case handles retrieval type."""
        case = PoisoningTestCase(
            test_id="test1",
            pack_type="retrieval",
            query="test",
            expected_doc_ids=["doc1"],
        )
        artifact = self._make_artifact("test1", "answer", ["doc2"])
        evidence = run_poisoning_case(case, artifact)

        assert evidence is not None
        assert evidence.pack_id == "test1"

    def test_run_poisoning_case_claim(self):
        """run_poisoning_case handles claim type."""
        case = PoisoningTestCase(
            test_id="test1",
            pack_type="claim",
            query="test",
            forbidden_claim="poisoned",
        )
        artifact = self._make_artifact("test1", "the poisoned answer")
        evidence = run_poisoning_case(case, artifact)

        assert evidence is not None

    def test_run_poisoning_case_sentinel(self):
        """run_poisoning_case handles sentinel type."""
        case = PoisoningTestCase(
            test_id="test1",
            pack_type="sentinel",
            query="test",
            sentinel_type="trigger",
            trigger_phrase="activated",
        )
        artifact = self._make_artifact("test1", "backdoor activated here")
        evidence = run_poisoning_case(case, artifact)

        assert evidence is not None
        assert evidence.triggered is True

    def test_run_poisoning_pack_collects_evidence(self):
        """run_poisoning_pack collects all evidence."""
        cases = [
            PoisoningTestCase(
                test_id="test1",
                pack_type="retrieval",
                query="q1",
                expected_doc_ids=["doc1"],
            ),
            PoisoningTestCase(
                test_id="test2",
                pack_type="claim",
                query="q2",
                forbidden_claim="bad",
            ),
        ]
        artifacts = [
            self._make_artifact("test1", "answer1", ["doc2"]),  # Missing doc1
            self._make_artifact("test2", "contains bad content"),  # Has forbidden
        ]

        section = run_poisoning_pack(cases, artifacts)

        assert len(section.packs) == 2
        assert section.integrity_summary.total_findings == 2
        assert section.integrity_summary.retrieval_poisoned == 1
        assert section.integrity_summary.claim_poisoned == 1

    def test_run_poisoning_pack_deterministic(self):
        """run_poisoning_pack produces deterministic output."""
        cases = load_poisoning_cases(get_poisoning_pack_path("integrity-dummy"))

        # Create matching artifacts with violations
        artifacts = [
            self._make_artifact("integrity_dummy_claim", "something else", ["doc1"]),
            self._make_artifact(
                "integrity_dummy_retrieval", "answer", ["doc3"]
            ),  # Missing expected
            self._make_artifact("integrity_dummy_sentinel", "normal response", []),
        ]

        # Run twice
        section1 = run_poisoning_pack(cases, artifacts)
        section2 = run_poisoning_pack(cases, artifacts)

        # Serialize and compare
        json1 = json.dumps(section1.model_dump(), sort_keys=True)
        json2 = json.dumps(section2.model_dump(), sort_keys=True)
        assert json1 == json2


class TestDummyPackIntegration:
    """Integration tests for the dummy integrity pack."""

    def test_dummy_pack_exists(self):
        """integrity-dummy pack is registered."""
        assert "integrity-dummy" in AVAILABLE_POISONING_PACKS

    def test_dummy_pack_has_cases(self):
        """integrity-dummy pack has expected case count."""
        path = get_poisoning_pack_path("integrity-dummy")
        cases = load_poisoning_cases(path)
        assert len(cases) == 3

    def test_dummy_pack_manifest_loadable(self):
        """Dummy pack manifest can be loaded and parsed."""
        import yaml

        manifest_path = (
            Path(__file__).parent.parent
            / "src"
            / "ragleaklab"
            / "poisoning"
            / "packs"
            / "v1"
            / "integrity-dummy.pack.yaml"
        )
        with manifest_path.open() as f:
            data = yaml.safe_load(f)

        manifest = PoisoningPackManifest(**data)
        assert manifest.name == "integrity-dummy"
        assert manifest.version == "1.0.0"
        assert manifest.pack_type == "mixed"
        assert manifest.test_count == 3
