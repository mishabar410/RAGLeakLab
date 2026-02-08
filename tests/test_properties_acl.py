"""Property-based tests for ACL evidence roundtrip and invariants."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from ragleaklab.poisoning.evidence import (
    AclIntegrityEvidence,
    IntegritySection,
)

# ── Strategies ───────────────────────────────────────────────────────

severity_st = st.sampled_from(["high", "medium", "low"])
tenant_st = st.sampled_from(["tenant_a", "tenant_b", "tenant_c", "shared"])
doc_id_st = st.from_regex(r"[a-z]{3,8}_\d{3}", fullmatch=True)


@st.composite
def acl_evidence_st(draw: st.DrawFn) -> AclIntegrityEvidence:
    return AclIntegrityEvidence(
        pack_id=draw(st.sampled_from(["acl-tenant-isolation", "acl-custom"])),
        query_id=draw(st.from_regex(r"acl_q\d{2}", fullmatch=True)),
        severity=draw(severity_st),
        querying_tenant=draw(tenant_st),
        target_tenant=draw(tenant_st),
        leaked_doc_ids=draw(st.lists(doc_id_st, max_size=5)),
        canary_found=draw(
            st.one_of(st.none(), st.from_regex(r"CANARY-[A-Z]+-\d{4}", fullmatch=True))
        ),
        confidence=draw(st.floats(min_value=0.0, max_value=1.0)),
        details=draw(st.fixed_dictionaries({})),
    )


# ── Roundtrip ────────────────────────────────────────────────────────


@given(evidence=acl_evidence_st())
@settings(max_examples=50)
def test_acl_evidence_roundtrip(evidence: AclIntegrityEvidence) -> None:
    """AclIntegrityEvidence serializes and deserializes idempotently."""
    data = evidence.model_dump()
    restored = AclIntegrityEvidence.model_validate(data)
    assert restored == evidence


@given(evidence=acl_evidence_st())
@settings(max_examples=50)
def test_acl_evidence_json_roundtrip(evidence: AclIntegrityEvidence) -> None:
    """AclIntegrityEvidence JSON roundtrip preserves all fields."""
    json_str = evidence.model_dump_json()
    restored = AclIntegrityEvidence.model_validate_json(json_str)
    assert restored == evidence


# ── Invariants ───────────────────────────────────────────────────────


@given(evidences=st.lists(acl_evidence_st(), min_size=0, max_size=10))
@settings(max_examples=30)
def test_integrity_section_acl_count_matches(evidences: list[AclIntegrityEvidence]) -> None:
    """IntegritySection.compute_summary correctly counts ACL violations."""
    section = IntegritySection(packs=evidences)
    summary = section.compute_summary()
    assert summary.acl_violated == len(evidences)
    assert summary.total_findings == len(evidences)


@given(evidences=st.lists(acl_evidence_st(), min_size=1, max_size=10))
@settings(max_examples=30)
def test_severity_counts_sum_to_total(evidences: list[AclIntegrityEvidence]) -> None:
    """Severity sub-counts always sum to total_findings."""
    section = IntegritySection(packs=evidences)
    summary = section.compute_summary()
    assert (
        summary.high_severity + summary.medium_severity + summary.low_severity
        == summary.total_findings
    )


@given(evidence=acl_evidence_st())
@settings(max_examples=20)
def test_confidence_bounded(evidence: AclIntegrityEvidence) -> None:
    """Confidence is always between 0 and 1."""
    assert 0.0 <= evidence.confidence <= 1.0
