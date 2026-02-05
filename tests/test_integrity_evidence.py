"""Unit tests for integrity evidence types."""

import json

from ragleaklab.poisoning import (
    ClaimIntegrityEvidence,
    IntegritySection,
    IntegritySummary,
    RetrievalIntegrityEvidence,
    SentinelIntegrityEvidence,
)


class TestRetrievalIntegrityEvidence:
    """Tests for RetrievalIntegrityEvidence model."""

    def test_minimal_creation(self):
        """Create evidence with minimal required fields."""
        evidence = RetrievalIntegrityEvidence(
            pack_id="test-pack",
            query_id="q001",
            severity="high",
        )
        assert evidence.pack_id == "test-pack"
        assert evidence.query_id == "q001"
        assert evidence.severity == "high"
        assert evidence.expected_doc_ids == []
        assert evidence.actual_doc_ids == []
        assert evidence.confidence == 0.0

    def test_full_creation(self):
        """Create evidence with all fields."""
        evidence = RetrievalIntegrityEvidence(
            pack_id="integrity-basic",
            query_id="q001",
            severity="high",
            expected_doc_ids=["doc1", "doc2"],
            actual_doc_ids=["doc_poison", "doc1"],
            confidence=0.95,
            details={"method": "ranking_anomaly"},
        )
        assert evidence.expected_doc_ids == ["doc1", "doc2"]
        assert evidence.confidence == 0.95
        assert evidence.details["method"] == "ranking_anomaly"

    def test_serialization_roundtrip(self):
        """Evidence can be serialized and deserialized."""
        evidence = RetrievalIntegrityEvidence(
            pack_id="test-pack",
            query_id="q001",
            severity="high",
            expected_doc_ids=["doc1"],
            actual_doc_ids=["doc2", "doc1"],
            confidence=0.85,
        )
        json_str = evidence.model_dump_json()
        parsed = json.loads(json_str)
        restored = RetrievalIntegrityEvidence.model_validate(parsed)
        assert restored == evidence

    def test_severity_validation(self):
        """Severity must be one of high, medium, low."""
        # Valid severities should work
        for severity in ["high", "medium", "low"]:
            evidence = RetrievalIntegrityEvidence(
                pack_id="test", query_id="q001", severity=severity
            )
            assert evidence.severity == severity


class TestClaimIntegrityEvidence:
    """Tests for ClaimIntegrityEvidence model."""

    def test_creation(self):
        """Create claim evidence."""
        evidence = ClaimIntegrityEvidence(
            pack_id="claim-pack",
            query_id="q002",
            severity="medium",
            expected_claim="The system is secure",
            actual_claim="The system has vulnerabilities",
            semantic_distance=0.78,
        )
        assert evidence.expected_claim == "The system is secure"
        assert evidence.semantic_distance == 0.78

    def test_serialization_roundtrip(self):
        """Claim evidence can be serialized and deserialized."""
        evidence = ClaimIntegrityEvidence(
            pack_id="claim-pack",
            query_id="q002",
            severity="medium",
            expected_claim="Expected text",
            actual_claim="Actual text",
        )
        json_str = evidence.model_dump_json()
        parsed = json.loads(json_str)
        restored = ClaimIntegrityEvidence.model_validate(parsed)
        assert restored == evidence


class TestSentinelIntegrityEvidence:
    """Tests for SentinelIntegrityEvidence model."""

    def test_creation(self):
        """Create sentinel evidence."""
        evidence = SentinelIntegrityEvidence(
            pack_id="sentinel-pack",
            query_id="q003",
            severity="high",
            sentinel_type="backdoor",
            triggered=True,
            expected_behavior="Normal response",
            actual_behavior="Backdoor activated",
        )
        assert evidence.sentinel_type == "backdoor"
        assert evidence.triggered is True

    def test_serialization_roundtrip(self):
        """Sentinel evidence can be serialized and deserialized."""
        evidence = SentinelIntegrityEvidence(
            pack_id="sentinel-pack",
            query_id="q003",
            severity="high",
            sentinel_type="trigger",
            triggered=False,
            expected_behavior="Normal",
            actual_behavior="Normal",
        )
        json_str = evidence.model_dump_json()
        parsed = json.loads(json_str)
        restored = SentinelIntegrityEvidence.model_validate(parsed)
        assert restored == evidence

    def test_sentinel_types(self):
        """All sentinel types are valid."""
        for stype in ["suffix", "trigger", "backdoor"]:
            evidence = SentinelIntegrityEvidence(
                pack_id="test",
                query_id="q001",
                severity="high",
                sentinel_type=stype,
                triggered=False,
                expected_behavior="Normal",
                actual_behavior="Normal",
            )
            assert evidence.sentinel_type == stype


class TestIntegritySummary:
    """Tests for IntegritySummary model."""

    def test_default_values(self):
        """Summary has sensible defaults."""
        summary = IntegritySummary()
        assert summary.total_findings == 0
        assert summary.high_severity == 0
        assert summary.medium_severity == 0
        assert summary.low_severity == 0

    def test_custom_values(self):
        """Summary accepts custom values."""
        summary = IntegritySummary(
            total_findings=5,
            high_severity=2,
            medium_severity=2,
            low_severity=1,
            retrieval_poisoned=3,
            claim_poisoned=2,
        )
        assert summary.total_findings == 5
        assert summary.retrieval_poisoned == 3


class TestIntegritySection:
    """Tests for IntegritySection model."""

    def test_empty_section(self):
        """Empty section has sensible defaults."""
        section = IntegritySection()
        assert section.packs == []
        assert section.integrity_summary.total_findings == 0

    def test_compute_summary(self):
        """compute_summary correctly tallies evidence."""
        section = IntegritySection(
            packs=[
                RetrievalIntegrityEvidence(pack_id="p1", query_id="q1", severity="high"),
                ClaimIntegrityEvidence(
                    pack_id="p1",
                    query_id="q2",
                    severity="medium",
                    expected_claim="x",
                    actual_claim="y",
                ),
                SentinelIntegrityEvidence(
                    pack_id="p2",
                    query_id="q3",
                    severity="low",
                    sentinel_type="trigger",
                    triggered=True,
                    expected_behavior="a",
                    actual_behavior="b",
                ),
            ]
        )
        summary = section.compute_summary()
        assert summary.total_findings == 3
        assert summary.high_severity == 1
        assert summary.medium_severity == 1
        assert summary.low_severity == 1
        assert summary.retrieval_poisoned == 1
        assert summary.claim_poisoned == 1
        assert summary.sentinel_triggered == 1

    def test_sorted_packs(self):
        """sorted_packs returns deterministic order."""
        section = IntegritySection(
            packs=[
                RetrievalIntegrityEvidence(pack_id="pack-b", query_id="q2", severity="low"),
                ClaimIntegrityEvidence(
                    pack_id="pack-a",
                    query_id="q1",
                    severity="high",
                    expected_claim="x",
                    actual_claim="y",
                ),
                SentinelIntegrityEvidence(
                    pack_id="pack-a",
                    query_id="q2",
                    severity="high",
                    sentinel_type="trigger",
                    triggered=False,
                    expected_behavior="a",
                    actual_behavior="a",
                ),
            ]
        )
        sorted_packs = section.sorted_packs()

        # High severity first
        assert sorted_packs[0].severity == "high"
        assert sorted_packs[1].severity == "high"
        # Then low severity
        assert sorted_packs[2].severity == "low"

        # Within high severity: pack-a q1 before pack-a q2
        assert sorted_packs[0].pack_id == "pack-a"
        assert sorted_packs[0].query_id == "q1"
        assert sorted_packs[1].pack_id == "pack-a"
        assert sorted_packs[1].query_id == "q2"

    def test_serialization_roundtrip(self):
        """IntegritySection can be serialized and deserialized."""
        section = IntegritySection(
            packs=[
                RetrievalIntegrityEvidence(pack_id="p1", query_id="q1", severity="high"),
            ],
            integrity_summary=IntegritySummary(total_findings=1, high_severity=1),
        )
        json_str = section.model_dump_json()
        parsed = json.loads(json_str)
        restored = IntegritySection.model_validate(parsed)
        assert len(restored.packs) == 1
        assert restored.integrity_summary.total_findings == 1


class TestBackwardCompatibility:
    """Tests for backward compatibility."""

    def test_integrity_field_optional_in_serialization(self):
        """Integrity section serializes to JSON correctly."""
        section = IntegritySection()
        data = section.model_dump()
        assert "packs" in data
        assert "integrity_summary" in data

    def test_json_without_integrity_can_be_parsed(self):
        """JSON without integrity section validates as None."""
        # This tests that RunArtifact with integrity=None serializes correctly
        section = IntegritySection()
        data = section.model_dump()
        # Empty section should work
        assert data["packs"] == []
