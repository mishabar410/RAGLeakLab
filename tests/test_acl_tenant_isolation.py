"""Tests for ACL tenant isolation pack."""

from __future__ import annotations

import pytest

from ragleaklab.poisoning.evidence import AclIntegrityEvidence, IntegritySection
from ragleaklab.poisoning.packs.acl_tenant_isolation import (
    AclPack,
    AclResult,
    evaluate_acl_isolation,
    get_acl_pack_path,
    load_acl_pack,
    pack_to_test_cases,
)


@pytest.fixture()
def acl_pack() -> AclPack:
    """Load the built-in ACL pack."""
    path = get_acl_pack_path()
    return load_acl_pack(path)


class TestLoadAclPack:
    """Tests for loading ACL pack data."""

    def test_load_manifest(self, acl_pack: AclPack) -> None:
        assert acl_pack.manifest.name == "acl-tenant-isolation"
        assert acl_pack.manifest.pack_type == "acl"
        assert acl_pack.manifest.version == "1.0.0"

    def test_load_queries(self, acl_pack: AclPack) -> None:
        assert len(acl_pack.queries) == 12
        # Deterministic order
        assert acl_pack.queries[0].query_id == "acl_q01"
        assert acl_pack.queries[-1].query_id == "acl_q12"

    def test_load_tenants(self, acl_pack: AclPack) -> None:
        assert "tenant_a" in acl_pack.tenant_docs
        assert "tenant_b" in acl_pack.tenant_docs
        assert "shared" in acl_pack.tenant_docs
        assert len(acl_pack.tenant_docs["tenant_a"]) == 8
        assert len(acl_pack.tenant_docs["tenant_b"]) == 8
        assert len(acl_pack.tenant_docs["shared"]) == 4

    def test_load_canaries(self, acl_pack: AclPack) -> None:
        # 4 canaries per tenant = 8 total
        assert len(acl_pack.doc_canaries) == 8
        assert "CANARY-ALPHA-7829" in acl_pack.doc_canaries.values()
        assert "CANARY-BETA-3456" in acl_pack.doc_canaries.values()

    def test_thresholds(self, acl_pack: AclPack) -> None:
        thresholds = acl_pack.get_thresholds()
        assert thresholds["cross_tenant_leak_rate"]["max_rate"] == 0.0
        assert thresholds["canary_leak_rate"]["max_rate"] == 0.0
        assert thresholds["isolation_score"]["min_score"] == 1.0


class TestEvaluateAclIsolation:
    """Tests for ACL isolation evaluation logic."""

    def test_no_leaks_passes(self, acl_pack: AclPack) -> None:
        """When no cross-tenant docs are retrieved, result should pass."""
        # Simulate retrieval where all docs belong to querying tenant
        results: dict[str, tuple[list[str], str]] = {}
        for q in acl_pack.queries:
            if q.target_tenant == "shared":
                results[q.query_id] = (["shared_001", "shared_002"], "")
            else:
                # Return own docs only
                own_tenant = q.querying_tenant
                own_docs = list(acl_pack.tenant_docs[own_tenant])[:3]
                results[q.query_id] = (own_docs, "")

        result = evaluate_acl_isolation(acl_pack, results)
        assert result.overall_passed is True
        assert result.cross_tenant_leak_rate == 0.0
        assert result.canary_leak_rate == 0.0
        assert result.isolation_score == 1.0
        assert len(result.evidences) == 0

    def test_doc_leak_detected(self, acl_pack: AclPack) -> None:
        """When cross-tenant docs are retrieved, result should fail."""
        results: dict[str, tuple[list[str], str]] = {}
        # First query: tenant_b sees tenant_a's doc (leak!)
        results["acl_q01"] = (["tenant_a_001", "shared_001"], "")
        # Other queries: clean
        for q in acl_pack.queries:
            if q.query_id != "acl_q01" and q.target_tenant != "shared":
                own_docs = list(acl_pack.tenant_docs[q.querying_tenant])[:2]
                results[q.query_id] = (own_docs, "")

        result = evaluate_acl_isolation(acl_pack, results)
        assert result.overall_passed is False
        assert result.leaked_queries >= 1
        assert len(result.evidences) >= 1
        assert result.evidences[0].query_id == "acl_q01"
        assert "tenant_a_001" in result.evidences[0].leaked_doc_ids

    def test_canary_leak_detected(self, acl_pack: AclPack) -> None:
        """When canary token appears in response, it is flagged."""
        results: dict[str, tuple[list[str], str]] = {}
        response_texts: dict[str, str] = {}
        # Simulate canary leak in response text
        results["acl_q01"] = (
            ["tenant_a_001"],
            "",
        )
        response_texts["acl_q01"] = "The budget report shows CANARY-ALPHA-7829 allocated."
        # Others clean
        for q in acl_pack.queries:
            if q.query_id != "acl_q01" and q.target_tenant != "shared":
                own_docs = list(acl_pack.tenant_docs[q.querying_tenant])[:2]
                results[q.query_id] = (own_docs, "")

        result = evaluate_acl_isolation(acl_pack, results, response_texts)
        assert result.canary_leaks >= 1
        assert result.overall_passed is False
        assert any(e.canary_found == "CANARY-ALPHA-7829" for e in result.evidences)

    def test_shared_docs_not_flagged(self, acl_pack: AclPack) -> None:
        """Shared docs in results should not cause failures."""
        results: dict[str, tuple[list[str], str]] = {}
        for q in acl_pack.queries:
            # Give everyone shared docs only
            results[q.query_id] = (["shared_001", "shared_002"], "")

        result = evaluate_acl_isolation(acl_pack, results)
        assert result.overall_passed is True
        assert len(result.evidences) == 0

    def test_empty_results(self, acl_pack: AclPack) -> None:
        """Empty results should pass (nothing leaked)."""
        result = evaluate_acl_isolation(acl_pack, {})
        assert result.overall_passed is True
        assert result.isolation_score == 1.0

    def test_severity_levels(self, acl_pack: AclPack) -> None:
        """High severity for canary, medium for single doc leak."""
        results: dict[str, tuple[list[str], str]] = {}
        response_texts: dict[str, str] = {}
        results["acl_q01"] = (["tenant_a_001"], "")
        response_texts["acl_q01"] = "CANARY-ALPHA-7829"
        results["acl_q05"] = (["tenant_b_001"], "")
        for q in acl_pack.queries:
            if q.query_id not in ("acl_q01", "acl_q05") and q.target_tenant != "shared":
                own_docs = list(acl_pack.tenant_docs[q.querying_tenant])[:2]
                results[q.query_id] = (own_docs, "")

        result = evaluate_acl_isolation(acl_pack, results, response_texts)
        severities = {e.query_id: e.severity for e in result.evidences}
        assert severities["acl_q01"] == "high"  # canary leak
        assert severities["acl_q05"] == "medium"  # single doc leak


class TestAclResult:
    """Tests for AclResult methods."""

    def test_to_integrity_section(self) -> None:
        evidence = AclIntegrityEvidence(
            pack_id="acl-tenant-isolation",
            query_id="q1",
            severity="high",
            querying_tenant="tenant_b",
            target_tenant="tenant_a",
            leaked_doc_ids=["tenant_a_001"],
            canary_found="CANARY-ALPHA-7829",
            confidence=0.5,
        )
        result = AclResult(
            pack_id="acl-tenant-isolation",
            evidences=[evidence],
            leaked_queries=1,
            total_cross_tenant_queries=1,
        )
        section = result.to_integrity_section()
        assert isinstance(section, IntegritySection)
        assert section.integrity_summary.acl_violated == 1
        assert section.integrity_summary.total_findings == 1
        assert section.integrity_summary.high_severity == 1

    def test_to_metric_scores(self) -> None:
        result = AclResult(
            pack_id="acl-tenant-isolation",
            cross_tenant_leak_rate=0.25,
            canary_leak_rate=0.125,
            isolation_score=0.75,
            total_cross_tenant_queries=8,
            leaked_queries=2,
            canary_leaks=1,
            overall_passed=False,
        )
        scores = result.to_metric_scores()
        assert len(scores) == 3
        names = {s.name for s in scores}
        assert "integrity.acl.cross_tenant_leak_rate" in names
        assert "integrity.acl.canary_leak_rate" in names
        assert "integrity.acl.isolation_score" in names

    def test_to_full_evidence(self) -> None:
        evidence = AclIntegrityEvidence(
            pack_id="acl-tenant-isolation",
            query_id="q1",
            severity="medium",
            querying_tenant="tenant_a",
            target_tenant="tenant_b",
            leaked_doc_ids=["tenant_b_001"],
        )
        result = AclResult(
            pack_id="acl-tenant-isolation",
            evidences=[evidence],
        )
        full = result.to_full_evidence()
        assert len(full) == 1
        assert full[0]["query_id"] == "q1"


class TestPackToTestCases:
    """Tests for converting ACL pack to test cases."""

    def test_converts_all_queries(self, acl_pack: AclPack) -> None:
        cases = pack_to_test_cases(acl_pack)
        assert len(cases) == 12
        for case in cases:
            assert case.threat == "canary"
            assert "acl" in case.tags

    def test_test_case_ids_match(self, acl_pack: AclPack) -> None:
        cases = pack_to_test_cases(acl_pack)
        ids = {c.test_id for c in cases}
        query_ids = {q.query_id for q in acl_pack.queries}
        assert ids == query_ids
