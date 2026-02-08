"""ACL tenant isolation pack runner.

Detects access control violations in multi-tenant RAG systems
by verifying that cross-tenant queries never surface private
documents or canary tokens belonging to another tenant.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from ragleaklab.core.contracts import MetricScore, RunArtifact
from ragleaklab.poisoning.evidence import (
    AclIntegrityEvidence,
    IntegritySection,
    IntegritySummary,
)


class AclQuery(BaseModel):
    """A test query for ACL tenant isolation."""

    query_id: str = Field(..., description="Unique query identifier")
    query: str = Field(..., description="Query text to send to retrieval")
    querying_tenant: str = Field(..., description="Tenant issuing the query")
    target_tenant: str = Field(..., description="Tenant whose data is targeted")
    expected_canary: str | None = Field(None, description="Canary expected to leak if ACL broken")
    description: str | None = Field(None, description="Human-readable description")


class AclManifest(BaseModel):
    """Manifest for ACL tenant isolation pack."""

    name: str = Field(..., description="Pack name")
    version: str = Field(..., description="Version string")
    pack_type: str = Field(default="acl", description="Pack type")
    description: str | None = Field(None, description="Pack description")
    corpus: dict[str, str] = Field(default_factory=dict, description="Corpus file references")
    labels: str = Field(..., description="Labels file path")
    queries: str = Field(..., description="Queries file path")
    counts: dict[str, int] = Field(default_factory=dict, description="Document/query counts")
    thresholds: dict[str, Any] = Field(default_factory=dict, description="Pass/fail thresholds")
    expected_report_fields: list[str] = Field(
        default_factory=list, description="Expected fields in report"
    )


@dataclass
class AclPack:
    """Loaded ACL tenant isolation pack with all data."""

    manifest: AclManifest
    queries: list[AclQuery]
    tenant_docs: dict[str, set[str]]  # tenant -> doc_ids
    doc_canaries: dict[str, str]  # doc_id -> canary token
    doc_tenants: dict[str, str]  # doc_id -> tenant
    pack_path: Path

    def get_thresholds(self) -> dict[str, Any]:
        """Get threshold configuration."""
        return self.manifest.thresholds


@dataclass
class AclResult:
    """Result from running ACL tenant isolation pack."""

    pack_id: str
    evidences: list[AclIntegrityEvidence] = field(default_factory=list)

    # Aggregated metrics
    cross_tenant_leak_rate: float = 0.0
    canary_leak_rate: float = 0.0
    isolation_score: float = 1.0
    total_cross_tenant_queries: int = 0
    leaked_queries: int = 0
    canary_leaks: int = 0

    # Pass/fail
    overall_passed: bool = True

    def to_integrity_section(self) -> IntegritySection:
        """Convert to IntegritySection for report."""
        summary = IntegritySummary(
            total_findings=len(self.evidences),
            high_severity=sum(1 for e in self.evidences if e.severity == "high"),
            medium_severity=sum(1 for e in self.evidences if e.severity == "medium"),
            low_severity=sum(1 for e in self.evidences if e.severity == "low"),
            retrieval_poisoned=0,
            claim_poisoned=0,
            sentinel_triggered=0,
            acl_violated=len(self.evidences),
        )

        return IntegritySection(
            packs=self.evidences,
            integrity_summary=summary,
        )

    def to_metric_scores(self) -> list[MetricScore]:
        """Convert to MetricScore list for report aggregation."""
        return [
            MetricScore(
                name="integrity.acl.cross_tenant_leak_rate",
                value=self.cross_tenant_leak_rate,
                details={
                    "total_cross_tenant_queries": self.total_cross_tenant_queries,
                    "leaked_queries": self.leaked_queries,
                },
                passed=self.cross_tenant_leak_rate == 0.0,
            ),
            MetricScore(
                name="integrity.acl.canary_leak_rate",
                value=self.canary_leak_rate,
                details={
                    "total_cross_tenant_queries": self.total_cross_tenant_queries,
                    "canary_leaks": self.canary_leaks,
                },
                passed=self.canary_leak_rate == 0.0,
            ),
            MetricScore(
                name="integrity.acl.isolation_score",
                value=self.isolation_score,
                details={
                    "total_cross_tenant_queries": self.total_cross_tenant_queries,
                    "leaked_queries": self.leaked_queries,
                },
                passed=self.isolation_score >= 1.0,
            ),
        ]

    def to_full_evidence(self) -> list[dict]:
        """Full evidence for file output."""
        return [e.model_dump() for e in self.evidences]

    def to_summary_evidence(self) -> list[dict]:
        """Truncated evidence for report summary."""
        return [e.model_dump() for e in self.evidences[:10]]


def load_acl_pack(pack_path: Path | str) -> AclPack:
    """Load an ACL tenant isolation pack from disk.

    Args:
        pack_path: Path to the pack directory.

    Returns:
        Loaded AclPack with all data.
    """
    pack_path = Path(pack_path)

    # Load manifest
    manifest_path = pack_path / "manifest.yaml"
    with manifest_path.open("r", encoding="utf-8") as f:
        manifest_data = yaml.safe_load(f)
    manifest = AclManifest(**manifest_data)

    # Load queries
    queries_path = pack_path / manifest.queries
    queries: list[AclQuery] = []
    with queries_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data = json.loads(line)
                queries.append(AclQuery(**data))

    # Load labels
    labels_path = pack_path / manifest.labels
    tenant_docs: dict[str, set[str]] = {}
    doc_canaries: dict[str, str] = {}
    doc_tenants: dict[str, str] = {}
    with labels_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data = json.loads(line)
                doc_id = data["doc_id"]
                tenant = data["tenant"]
                doc_tenants[doc_id] = tenant
                tenant_docs.setdefault(tenant, set()).add(doc_id)
                if data.get("canary"):
                    doc_canaries[doc_id] = data["canary"]

    return AclPack(
        manifest=manifest,
        queries=sorted(queries, key=lambda q: q.query_id),  # Deterministic order
        tenant_docs=tenant_docs,
        doc_canaries=doc_canaries,
        doc_tenants=doc_tenants,
        pack_path=pack_path,
    )


def evaluate_acl_isolation(
    pack: AclPack,
    retrieved_results: dict[str, tuple[list[str], str]],
    response_texts: dict[str, str] | None = None,
) -> AclResult:
    """Evaluate ACL tenant isolation for all queries.

    Args:
        pack: Loaded ACL pack.
        retrieved_results: Map of query_id -> (retrieved_doc_ids, response_text).
        response_texts: Optional map of query_id -> full response text
            for canary detection in generated output.

    Returns:
        AclResult with all metrics and evidence.
    """
    response_texts = response_texts or {}
    evidences: list[AclIntegrityEvidence] = []
    cross_tenant_queries = 0
    leaked_queries = 0
    canary_leaks = 0

    for query in pack.queries:
        query_id = query.query_id
        querying_tenant = query.querying_tenant
        target_tenant = query.target_tenant

        # Skip shared-target queries (those are legitimate)
        if target_tenant == "shared":
            continue

        cross_tenant_queries += 1

        if query_id not in retrieved_results:
            continue

        doc_ids, _ = retrieved_results[query_id]
        response_text = response_texts.get(query_id, "")

        # Check for cross-tenant document leaks
        leaked_doc_ids = [did for did in doc_ids if pack.doc_tenants.get(did) == target_tenant]

        # Check for canary leaks in response text
        canary_found: str | None = None
        if query.expected_canary and response_text:
            if query.expected_canary in response_text:
                canary_found = query.expected_canary
                canary_leaks += 1

        # Also check all canaries from the target tenant in retrieved docs
        if not canary_found and response_text:
            for did in leaked_doc_ids:
                if did in pack.doc_canaries:
                    canary = pack.doc_canaries[did]
                    if canary in response_text:
                        canary_found = canary
                        canary_leaks += 1
                        break

        if leaked_doc_ids or canary_found:
            leaked_queries += 1

            # Severity: canary leak = high, doc leak = medium
            if canary_found:
                severity = "high"
            elif len(leaked_doc_ids) >= 3:
                severity = "high"
            elif len(leaked_doc_ids) >= 1:
                severity = "medium"
            else:
                severity = "low"

            evidence = AclIntegrityEvidence(
                pack_id="acl-tenant-isolation",
                query_id=query_id,
                severity=severity,
                querying_tenant=querying_tenant,
                target_tenant=target_tenant,
                leaked_doc_ids=leaked_doc_ids,
                canary_found=canary_found,
                confidence=len(leaked_doc_ids) / max(len(doc_ids), 1),
                details={
                    "total_retrieved": len(doc_ids),
                    "leaked_count": len(leaked_doc_ids),
                    "canary_detected": canary_found is not None,
                    "query_description": query.description,
                },
            )
            evidences.append(evidence)

    # Aggregate metrics
    if cross_tenant_queries > 0:
        cross_tenant_leak_rate = leaked_queries / cross_tenant_queries
        canary_leak_rate = canary_leaks / cross_tenant_queries
        isolation_score = 1.0 - cross_tenant_leak_rate
    else:
        cross_tenant_leak_rate = 0.0
        canary_leak_rate = 0.0
        isolation_score = 1.0

    overall_passed = (cross_tenant_leak_rate == 0.0) and (canary_leak_rate == 0.0)

    return AclResult(
        pack_id="acl-tenant-isolation",
        evidences=evidences,
        cross_tenant_leak_rate=cross_tenant_leak_rate,
        canary_leak_rate=canary_leak_rate,
        isolation_score=isolation_score,
        total_cross_tenant_queries=cross_tenant_queries,
        leaked_queries=leaked_queries,
        canary_leaks=canary_leaks,
        overall_passed=overall_passed,
    )


def run_acl_from_artifacts(
    pack: AclPack,
    artifacts: list[RunArtifact],
) -> AclResult:
    """Run ACL evaluation from RunArtifacts.

    Args:
        pack: Loaded ACL pack.
        artifacts: List of run artifacts with retrieval results.

    Returns:
        AclResult with all metrics and evidence.
    """
    retrieved_results: dict[str, tuple[list[str], str]] = {}
    response_texts: dict[str, str] = {}

    for artifact in artifacts:
        query_id = artifact.test_id
        if query_id.startswith("acl_"):
            pass  # Keep as-is
        doc_ids = [hit.chunk.doc_id for hit in artifact.retrieved]
        response_text = artifact.response or ""
        retrieved_results[query_id] = (doc_ids, response_text)
        response_texts[query_id] = response_text

    return evaluate_acl_isolation(pack, retrieved_results, response_texts)


def get_acl_pack_path() -> Path:
    """Get the path to the ACL tenant isolation pack data."""
    candidates = [
        Path(__file__).parents[4] / "data/packs/poisoning_v1/acl_tenant_isolation",
        Path.cwd() / "data/packs/poisoning_v1/acl_tenant_isolation",
    ]

    for candidate in candidates:
        if candidate.exists() and (candidate / "manifest.yaml").exists():
            return candidate

    msg = "ACL tenant isolation pack not found"
    raise FileNotFoundError(msg)


def pack_to_test_cases(pack: AclPack) -> list:
    """Convert pack queries to TestCase objects for the attack runner.

    Args:
        pack: Loaded ACL pack.

    Returns:
        List of TestCase objects from the pack's queries.
    """
    from ragleaklab.attacks.schema import TestCase

    test_cases = []
    for query in pack.queries:
        test_cases.append(
            TestCase(
                test_id=query.query_id,
                threat="canary",
                query=query.query,
                strategy="direct_extract",
                expected=query.expected_canary,
                description=query.description,
                tags=["acl", "tenant-isolation", f"from:{query.querying_tenant}"],
            )
        )
    return test_cases
