"""Claim corruption poisoning pack runner.

Detects corpus poisoning attacks that inject false or contradictory claims,
causing RAG systems to generate incorrect answers.

Two-phase evaluation:
1. Clean corpus: Measure true claim recall
2. Poisoned corpus: Measure recall drop from poison interference
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from ragleaklab.core.contracts import MetricScore
from ragleaklab.poisoning.evidence import (
    ClaimIntegrityEvidence,
    IntegritySection,
    IntegritySummary,
)

# =============================================================================
# Claim Fingerprinting (Deterministic Matching)
# =============================================================================


def normalize_text(text: str) -> str:
    """Normalize text for fingerprinting.

    Steps:
    1. Unicode NFKC normalization
    2. Lowercase
    3. Remove punctuation
    4. Collapse whitespace
    5. Strip

    Args:
        text: Raw text to normalize.

    Returns:
        Normalized text string.
    """
    # Unicode normalization
    text = unicodedata.normalize("NFKC", text)

    # Lowercase
    text = text.lower()

    # Remove punctuation (keep alphanumeric and spaces)
    text = re.sub(r"[^\w\s]", "", text)

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)

    # Strip
    return text.strip()


def fingerprint_claim(claim: str) -> str:
    """Generate fingerprint hash for a claim.

    Args:
        claim: Claim text.

    Returns:
        SHA-256 hex digest of normalized claim.
    """
    normalized = normalize_text(claim)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def match_claim_exact(claim: str, known_claims: dict[str, str]) -> str | None:
    """Match a claim against known claims by fingerprint.

    Args:
        claim: Claim text to match.
        known_claims: Map of fingerprint -> claim_id.

    Returns:
        claim_id if matched, None otherwise.
    """
    fp = fingerprint_claim(claim)
    return known_claims.get(fp)


# =============================================================================
# Pydantic Models
# =============================================================================


class ClaimCorruptionQuery(BaseModel):
    """A test query for claim corruption detection."""

    query_id: str = Field(..., description="Unique query identifier")
    query: str = Field(..., description="Query text")
    expected_claim_ids: list[str] = Field(
        default_factory=list, description="Expected true claim IDs"
    )
    topic: str | None = Field(None, description="Topic category")


class TrueClaim(BaseModel):
    """A ground truth claim."""

    claim_id: str = Field(..., description="Unique claim identifier")
    claim: str = Field(..., description="Claim text")
    topic: str | None = Field(None, description="Topic category")
    source_doc_id: str | None = Field(None, description="Source document ID")


class PoisonClaim(BaseModel):
    """A poisoned false claim."""

    claim_id: str = Field(..., description="Unique claim identifier")
    claim: str = Field(..., description="Claim text")
    topic: str | None = Field(None, description="Topic category")
    source_doc_id: str | None = Field(None, description="Source document ID")
    contradicts: str | None = Field(None, description="True claim ID this contradicts")


class ClaimCorruptionManifest(BaseModel):
    """Manifest for claim corruption pack."""

    name: str = Field(..., description="Pack name")
    version: str = Field(..., description="Version string")
    pack_type: str = Field(default="claim", description="Pack type")
    description: str | None = Field(None, description="Pack description")
    corpus: dict[str, str] = Field(default_factory=dict, description="Corpus files")
    claims: dict[str, str] = Field(default_factory=dict, description="Claim files")
    queries: str = Field(..., description="Queries file path")
    counts: dict[str, int] = Field(default_factory=dict, description="Counts")
    thresholds: dict[str, Any] = Field(default_factory=dict, description="Thresholds")
    expected_report_fields: list[str] = Field(
        default_factory=list, description="Expected report fields"
    )


# =============================================================================
# Pack Data Structures
# =============================================================================


@dataclass
class ClaimCorruptionPack:
    """Loaded claim corruption pack with all data."""

    manifest: ClaimCorruptionManifest
    queries: list[ClaimCorruptionQuery]
    true_claims: list[TrueClaim]
    poison_claims: list[PoisonClaim]
    claim_map: dict[str, list[str]]  # claim_id -> doc_ids
    pack_path: Path

    # Pre-computed fingerprint indices
    true_claim_fingerprints: dict[str, str] = field(default_factory=dict)
    poison_claim_fingerprints: dict[str, str] = field(default_factory=dict)
    contradiction_map: dict[str, str] = field(default_factory=dict)

    def get_thresholds(self) -> dict[str, Any]:
        """Get threshold configuration."""
        return self.manifest.thresholds


@dataclass
class ClaimMetricsResult:
    """Result of claim metrics evaluation for a single query."""

    query_id: str
    poison_claim_rate: float
    true_claim_recall: float
    matched_true_claims: list[str] = field(default_factory=list)
    matched_poison_claims: list[str] = field(default_factory=list)
    expected_claim_ids: list[str] = field(default_factory=list)
    supporting_doc_ids: list[str] = field(default_factory=list)
    contradiction_hits: int = 0

    # Threshold evaluation
    poison_rate_passed: bool | None = None
    true_recall_passed: bool | None = None

    def to_metric_scores(self) -> list[MetricScore]:
        """Convert to list of MetricScore for reporting."""
        return [
            MetricScore(
                name="integrity.claim.poison_claim_rate",
                value=self.poison_claim_rate,
                details={
                    "query_id": self.query_id,
                    "matched_poison_claims": self.matched_poison_claims[:5],
                },
                passed=self.poison_rate_passed,
            ),
            MetricScore(
                name="integrity.claim.true_claim_recall",
                value=self.true_claim_recall,
                details={
                    "query_id": self.query_id,
                    "matched_true_claims": self.matched_true_claims[:5],
                    "expected_claims": self.expected_claim_ids,
                },
                passed=self.true_recall_passed,
            ),
        ]

    def to_evidence_dict(self) -> dict:
        """Convert to full evidence dict for file output."""
        return {
            "query_id": self.query_id,
            "poison_claim_rate": self.poison_claim_rate,
            "true_claim_recall": self.true_claim_recall,
            "matched_true_claims": self.matched_true_claims,
            "matched_poison_claims": self.matched_poison_claims,
            "expected_claim_ids": self.expected_claim_ids,
            "supporting_doc_ids": self.supporting_doc_ids,
            "contradiction_hits": self.contradiction_hits,
            "passed": {
                "poison_rate": self.poison_rate_passed,
                "true_recall": self.true_recall_passed,
            },
        }


@dataclass
class ClaimCorruptionResult:
    """Result from running claim corruption pack."""

    pack_id: str
    query_results_clean: list[ClaimMetricsResult] = field(default_factory=list)
    query_results_poisoned: list[ClaimMetricsResult] = field(default_factory=list)
    evidences: list[ClaimIntegrityEvidence] = field(default_factory=list)

    # Phase metrics
    avg_true_recall_clean: float = 0.0
    avg_true_recall_poisoned: float = 0.0
    avg_poison_claim_rate: float = 0.0
    total_contradiction_hits: int = 0

    # Derived metrics
    true_claim_recall_drop: float = 0.0

    # Totals
    total_queries: int = 0
    queries_with_poison: int = 0

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
            claim_poisoned=len(self.evidences),
            sentinel_triggered=0,
        )

        return IntegritySection(
            packs=self.evidences,
            integrity_summary=summary,
        )

    def to_metric_scores(self) -> list[MetricScore]:
        """Convert to MetricScore list for report aggregation."""
        return [
            MetricScore(
                name="integrity.claim.poison_claim_rate",
                value=self.avg_poison_claim_rate,
                details={
                    "total_queries": self.total_queries,
                    "queries_with_poison": self.queries_with_poison,
                },
                passed=self.overall_passed,
            ),
            MetricScore(
                name="integrity.claim.true_claim_recall",
                value=self.avg_true_recall_poisoned,
                details={
                    "clean_recall": self.avg_true_recall_clean,
                    "poisoned_recall": self.avg_true_recall_poisoned,
                },
                passed=self.overall_passed,
            ),
            MetricScore(
                name="integrity.claim.true_claim_recall_drop",
                value=self.true_claim_recall_drop,
                details={
                    "clean_recall": self.avg_true_recall_clean,
                    "poisoned_recall": self.avg_true_recall_poisoned,
                },
                passed=self.overall_passed,
            ),
            MetricScore(
                name="integrity.claim.contradiction_hits",
                value=float(self.total_contradiction_hits),
                details={"total_hits": self.total_contradiction_hits},
                passed=self.total_contradiction_hits == 0,
            ),
        ]

    def to_full_evidence(self) -> list[dict]:
        """Full evidence for file output."""
        return [r.to_evidence_dict() for r in self.query_results_poisoned]

    def to_summary_evidence(self) -> list[dict]:
        """Truncated evidence for report summary."""
        results = [r.to_evidence_dict() for r in self.query_results_poisoned[:10]]
        for r in results:
            r["matched_true_claims"] = r["matched_true_claims"][:3]
            r["matched_poison_claims"] = r["matched_poison_claims"][:3]
        return results


# =============================================================================
# Pack Loading
# =============================================================================


def load_claim_corruption_pack(pack_path: Path | str) -> ClaimCorruptionPack:
    """Load a claim corruption pack from disk.

    Args:
        pack_path: Path to the pack directory.

    Returns:
        Loaded ClaimCorruptionPack with all data.
    """
    pack_path = Path(pack_path)

    # Load manifest
    manifest_path = pack_path / "manifest.yaml"
    with manifest_path.open("r", encoding="utf-8") as f:
        manifest_data = yaml.safe_load(f)
    manifest = ClaimCorruptionManifest(**manifest_data)

    # Load queries
    queries_path = pack_path / manifest.queries
    queries: list[ClaimCorruptionQuery] = []
    with queries_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data = json.loads(line)
                queries.append(ClaimCorruptionQuery(**data))

    # Load true claims
    true_claims_path = pack_path / manifest.claims["true_claims"]
    true_claims: list[TrueClaim] = []
    with true_claims_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data = json.loads(line)
                true_claims.append(TrueClaim(**data))

    # Load poison claims
    poison_claims_path = pack_path / manifest.claims["poison_claims"]
    poison_claims: list[PoisonClaim] = []
    with poison_claims_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data = json.loads(line)
                poison_claims.append(PoisonClaim(**data))

    # Load claim map
    claim_map_path = pack_path / manifest.claims["claim_map"]
    claim_map: dict[str, list[str]] = {}
    with claim_map_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data = json.loads(line)
                claim_map[data["claim_id"]] = data["doc_ids"]

    # Build fingerprint indices
    true_claim_fingerprints: dict[str, str] = {}
    for tc in true_claims:
        fp = fingerprint_claim(tc.claim)
        true_claim_fingerprints[fp] = tc.claim_id

    poison_claim_fingerprints: dict[str, str] = {}
    for pc in poison_claims:
        fp = fingerprint_claim(pc.claim)
        poison_claim_fingerprints[fp] = pc.claim_id

    # Build contradiction map
    contradiction_map: dict[str, str] = {}
    for pc in poison_claims:
        if pc.contradicts:
            contradiction_map[pc.claim_id] = pc.contradicts

    return ClaimCorruptionPack(
        manifest=manifest,
        queries=sorted(queries, key=lambda q: q.query_id),
        true_claims=true_claims,
        poison_claims=poison_claims,
        claim_map=claim_map,
        pack_path=pack_path,
        true_claim_fingerprints=true_claim_fingerprints,
        poison_claim_fingerprints=poison_claim_fingerprints,
        contradiction_map=contradiction_map,
    )


# =============================================================================
# Claim Matching
# =============================================================================


def match_claims_in_text(
    text: str,
    true_claim_fingerprints: dict[str, str],
    poison_claim_fingerprints: dict[str, str],
    true_claims: list[TrueClaim],
    poison_claims: list[PoisonClaim],
) -> tuple[list[str], list[str]]:
    """Match claims in generated text against known claims.

    Uses fingerprint-based exact matching after normalization.

    Args:
        text: Generated/retrieved text to analyze.
        true_claim_fingerprints: Map of fingerprint -> true claim_id.
        poison_claim_fingerprints: Map of fingerprint -> poison claim_id.
        true_claims: List of true claims to match.
        poison_claims: List of poison claims to match.

    Returns:
        Tuple of (matched_true_claim_ids, matched_poison_claim_ids).
    """
    matched_true: list[str] = []
    matched_poison: list[str] = []

    normalized_text = normalize_text(text)

    # Check each true claim
    for tc in true_claims:
        normalized_claim = normalize_text(tc.claim)
        if normalized_claim in normalized_text:
            matched_true.append(tc.claim_id)

    # Check each poison claim
    for pc in poison_claims:
        normalized_claim = normalize_text(pc.claim)
        if normalized_claim in normalized_text:
            matched_poison.append(pc.claim_id)

    return matched_true, matched_poison


def evaluate_query_claims(
    query: ClaimCorruptionQuery,
    retrieved_text: str,
    pack: ClaimCorruptionPack,
    thresholds: dict[str, Any] | None = None,
) -> ClaimMetricsResult:
    """Evaluate claim metrics for a single query.

    Args:
        query: Query with expected claims.
        retrieved_text: Combined text from retrieval/generation.
        pack: Loaded claim corruption pack.
        thresholds: Optional threshold configuration.

    Returns:
        ClaimMetricsResult with all metrics.
    """
    # Match claims in retrieved text
    matched_true, matched_poison = match_claims_in_text(
        text=retrieved_text,
        true_claim_fingerprints=pack.true_claim_fingerprints,
        poison_claim_fingerprints=pack.poison_claim_fingerprints,
        true_claims=pack.true_claims,
        poison_claims=pack.poison_claims,
    )

    # Calculate true claim recall
    expected_ids = set(query.expected_claim_ids)
    found_expected = set(matched_true) & expected_ids
    true_recall = len(found_expected) / len(expected_ids) if expected_ids else 1.0

    # Calculate poison claim rate
    total_matched = len(matched_true) + len(matched_poison)
    poison_rate = len(matched_poison) / total_matched if total_matched > 0 else 0.0

    # Count contradiction hits
    contradiction_hits = 0
    for pc_id in matched_poison:
        if pc_id in pack.contradiction_map:
            contradicted_tc = pack.contradiction_map[pc_id]
            if contradicted_tc in query.expected_claim_ids:
                contradiction_hits += 1

    # Get supporting doc ids
    supporting_docs: set[str] = set()
    for claim_id in matched_true + matched_poison:
        if claim_id in pack.claim_map:
            supporting_docs.update(pack.claim_map[claim_id])

    result = ClaimMetricsResult(
        query_id=query.query_id,
        poison_claim_rate=poison_rate,
        true_claim_recall=true_recall,
        matched_true_claims=matched_true,
        matched_poison_claims=matched_poison,
        expected_claim_ids=list(expected_ids),
        supporting_doc_ids=sorted(supporting_docs),
        contradiction_hits=contradiction_hits,
    )

    # Apply thresholds
    if thresholds:
        pr_thresh = thresholds.get("poison_claim_rate", {})
        if "max_rate" in pr_thresh:
            result.poison_rate_passed = poison_rate <= pr_thresh["max_rate"]

        tr_thresh = thresholds.get("true_claim_recall", {})
        if "min_recall" in tr_thresh:
            result.true_recall_passed = true_recall >= tr_thresh["min_recall"]

    return result


# =============================================================================
# Two-Phase Evaluation
# =============================================================================


def evaluate_claim_corruption(
    pack: ClaimCorruptionPack,
    clean_results: dict[str, str],
    poisoned_results: dict[str, str],
) -> ClaimCorruptionResult:
    """Evaluate claim corruption with two-phase comparison.

    Args:
        pack: Loaded claim corruption pack.
        clean_results: Map of query_id -> text from clean corpus.
        poisoned_results: Map of query_id -> text from poisoned corpus.

    Returns:
        ClaimCorruptionResult with all metrics and evidence.
    """
    thresholds = pack.get_thresholds()
    results_clean: list[ClaimMetricsResult] = []
    results_poisoned: list[ClaimMetricsResult] = []
    evidences: list[ClaimIntegrityEvidence] = []

    for query in pack.queries:
        query_id = query.query_id

        # Phase 1: Clean corpus evaluation
        if query_id in clean_results:
            clean_text = clean_results[query_id]
            clean_metrics = evaluate_query_claims(query, clean_text, pack, thresholds)
            results_clean.append(clean_metrics)

        # Phase 2: Poisoned corpus evaluation
        if query_id in poisoned_results:
            poisoned_text = poisoned_results[query_id]
            poisoned_metrics = evaluate_query_claims(query, poisoned_text, pack, thresholds)
            results_poisoned.append(poisoned_metrics)

            # Create evidence if poison detected
            if poisoned_metrics.matched_poison_claims:
                # Determine severity
                if poisoned_metrics.contradiction_hits > 0:
                    severity = "high"
                elif poisoned_metrics.poison_claim_rate >= 0.3:
                    severity = "high"
                elif poisoned_metrics.poison_claim_rate >= 0.1:
                    severity = "medium"
                else:
                    severity = "low"

                evidence = ClaimIntegrityEvidence(
                    pack_id="claim-corruption",
                    query_id=query_id,
                    severity=severity,
                    expected_claim_ids=query.expected_claim_ids,
                    matched_true_claims=poisoned_metrics.matched_true_claims,
                    matched_poison_claims=poisoned_metrics.matched_poison_claims,
                    contradiction_hits=poisoned_metrics.contradiction_hits,
                    confidence=poisoned_metrics.poison_claim_rate,
                    details={
                        "poison_claim_rate": poisoned_metrics.poison_claim_rate,
                        "true_claim_recall": poisoned_metrics.true_claim_recall,
                        "supporting_doc_ids": poisoned_metrics.supporting_doc_ids[:5],
                    },
                )
                evidences.append(evidence)

    # Calculate aggregate metrics
    total_clean = len(results_clean)
    total_poisoned = len(results_poisoned)

    if total_clean > 0:
        avg_true_recall_clean = sum(r.true_claim_recall for r in results_clean) / total_clean
    else:
        avg_true_recall_clean = 1.0

    if total_poisoned > 0:
        avg_true_recall_poisoned = (
            sum(r.true_claim_recall for r in results_poisoned) / total_poisoned
        )
        avg_poison_rate = sum(r.poison_claim_rate for r in results_poisoned) / total_poisoned
        total_contradiction_hits = sum(r.contradiction_hits for r in results_poisoned)
        queries_with_poison = sum(1 for r in results_poisoned if r.matched_poison_claims)
    else:
        avg_true_recall_poisoned = 1.0
        avg_poison_rate = 0.0
        total_contradiction_hits = 0
        queries_with_poison = 0

    # Calculate recall drop
    recall_drop = avg_true_recall_clean - avg_true_recall_poisoned

    # Determine overall pass/fail
    overall_passed = True

    # Check thresholds
    drop_thresh = thresholds.get("true_claim_recall_drop", {})
    if "max_drop" in drop_thresh and recall_drop > drop_thresh["max_drop"]:
        overall_passed = False

    contra_thresh = thresholds.get("contradiction_hits", {})
    if "max_hits" in contra_thresh and total_contradiction_hits > contra_thresh["max_hits"]:
        overall_passed = False

    for r in results_poisoned:
        if r.poison_rate_passed is False:
            overall_passed = False
        if r.true_recall_passed is False:
            overall_passed = False

    return ClaimCorruptionResult(
        pack_id="claim-corruption",
        query_results_clean=results_clean,
        query_results_poisoned=results_poisoned,
        evidences=evidences,
        avg_true_recall_clean=avg_true_recall_clean,
        avg_true_recall_poisoned=avg_true_recall_poisoned,
        avg_poison_claim_rate=avg_poison_rate,
        total_contradiction_hits=total_contradiction_hits,
        true_claim_recall_drop=recall_drop,
        total_queries=total_poisoned,
        queries_with_poison=queries_with_poison,
        overall_passed=overall_passed,
    )


# =============================================================================
# Pack Path Resolution
# =============================================================================


def get_claim_corruption_pack_path() -> Path:
    """Get the path to the claim corruption pack data."""
    candidates = [
        Path(__file__).parents[4] / "data/packs/poisoning_v1/claim_corruption",
        Path.cwd() / "data/packs/poisoning_v1/claim_corruption",
    ]

    for candidate in candidates:
        if candidate.exists() and (candidate / "manifest.yaml").exists():
            return candidate

    msg = "Claim corruption pack not found"
    raise FileNotFoundError(msg)
