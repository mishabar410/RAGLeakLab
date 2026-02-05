"""Sentinel Takeover Safe Pack - Rule-based sentinel bypass detection.

This pack evaluates RAG output against configurable sentinel rules using
pure regex pattern matching. Operates entirely offline without LLM or network.

Key features:
- Pattern-based trigger detection
- Deterministic policy enforcement (block/strip)
- Metrics: block_rate, leak_rate
- Evidence with policy_action and output_markers
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

from ragleaklab.core.contracts import RunArtifact
from ragleaklab.poisoning.evidence import (
    IntegritySection,
    IntegritySummary,
    SentinelIntegrityEvidence,
)

PolicyAction = Literal["block", "strip", "allow"]
SeverityLevel = Literal["high", "medium", "low"]


class SentinelRule(BaseModel):
    """A single sentinel detection rule."""

    id: str = Field(..., description="Unique rule identifier")
    name: str = Field(default="", description="Human-readable rule name")
    description: str = Field(default="", description="Rule description")
    pattern: str = Field(..., description="Regex pattern to match")
    policy: PolicyAction = Field(..., description="Policy action: block, strip, allow")
    severity: SeverityLevel = Field(default="medium", description="Severity level")

    def compile(self) -> re.Pattern[str]:
        """Compile the regex pattern."""
        return re.compile(self.pattern, re.IGNORECASE | re.MULTILINE)


class SentinelRulesConfig(BaseModel):
    """Configuration for sentinel rules."""

    version: str = Field(default="1.0.0", description="Rules version")
    rules: list[SentinelRule] = Field(default_factory=list, description="List of rules")


class SentinelQuery(BaseModel):
    """A test query for sentinel evaluation."""

    query_id: str = Field(..., description="Unique query identifier")
    query: str = Field(..., description="Query text")
    target_doc_ids: list[str] = Field(default_factory=list, description="Target document IDs")
    expected_triggers: list[str] = Field(
        default_factory=list, description="Expected rule IDs to trigger"
    )
    description: str = Field(default="", description="Query description")


class SentinelManifest(BaseModel):
    """Sentinel pack manifest."""

    name: str = Field(..., description="Pack name")
    version: str = Field(default="1.0.0", description="Pack version")
    pack_type: str = Field(default="sentinel", description="Pack type")
    description: str = Field(default="", description="Pack description")
    corpus: dict[str, str] = Field(default_factory=dict, description="Corpus paths")
    sentinel_rules: str = Field(..., description="Path to sentinel rules file")
    queries: str = Field(..., description="Path to queries file")
    counts: dict[str, int] = Field(default_factory=dict, description="Item counts")
    thresholds: dict[str, dict[str, float]] = Field(
        default_factory=dict, description="Pass/fail thresholds"
    )


class SentinelMatch(BaseModel):
    """A single pattern match result."""

    rule_id: str = Field(..., description="Rule ID that matched")
    rule_name: str = Field(default="", description="Rule name")
    matched_text: str = Field(..., description="Text that matched the pattern")
    start_pos: int = Field(..., description="Start position in text")
    end_pos: int = Field(..., description="End position in text")
    policy: PolicyAction = Field(..., description="Policy action")
    severity: SeverityLevel = Field(default="medium", description="Severity")


class SentinelEvalResult(BaseModel):
    """Result of sentinel evaluation for a single query/output."""

    query_id: str = Field(..., description="Query ID")
    triggered: bool = Field(default=False, description="Whether any rule triggered")
    policy_action: PolicyAction = Field(default="allow", description="Final policy action taken")
    matches: list[SentinelMatch] = Field(default_factory=list, description="All pattern matches")
    output_markers: list[str] = Field(default_factory=list, description="Markers found in output")
    blocked: bool = Field(default=False, description="Whether output was blocked")
    leaked_markers: list[str] = Field(
        default_factory=list, description="Markers that leaked through"
    )


class SentinelPack(BaseModel):
    """Loaded sentinel pack with all data."""

    manifest: SentinelManifest = Field(..., description="Pack manifest")
    rules: SentinelRulesConfig = Field(..., description="Sentinel rules")
    queries: list[SentinelQuery] = Field(default_factory=list, description="Test queries")
    poison_docs: dict[str, str] = Field(
        default_factory=dict, description="Poison documents (doc_id -> text)"
    )
    pack_path: Path = Field(..., description="Path to pack directory")


class SentinelPackResult(BaseModel):
    """Complete result from sentinel pack evaluation."""

    pack_id: str = Field(..., description="Pack identifier")
    query_results: list[SentinelEvalResult] = Field(
        default_factory=list, description="Per-query results"
    )
    block_rate: float = Field(default=0.0, description="Rate of blocked outputs")
    leak_rate: float = Field(default=0.0, description="Rate of leaked markers")
    total_triggers: int = Field(default=0, description="Total rule triggers")

    def to_integrity_section(self) -> IntegritySection:
        """Convert to IntegritySection for report."""
        packs: list[SentinelIntegrityEvidence] = []

        for result in self.query_results:
            if result.triggered:
                # Determine severity from highest severity match
                severity: SeverityLevel = "low"
                if any(m.severity == "high" for m in result.matches):
                    severity = "high"
                elif any(m.severity == "medium" for m in result.matches):
                    severity = "medium"

                packs.append(
                    SentinelIntegrityEvidence(
                        pack_id=self.pack_id,
                        query_id=result.query_id,
                        severity=severity,
                        sentinel_type="trigger",
                        triggered=result.triggered,
                        policy_action=result.policy_action,
                        output_markers=result.output_markers,
                        expected_behavior="blocked" if result.blocked else "stripped",
                        actual_behavior="blocked"
                        if result.blocked
                        else "leaked"
                        if result.leaked_markers
                        else "clean",
                        details={
                            "matches": [m.model_dump() for m in result.matches],
                            "leaked_markers": result.leaked_markers,
                        },
                    )
                )

        summary = IntegritySummary(
            total_findings=len(packs),
            sentinel_triggered=len(packs),
        )

        return IntegritySection(packs=packs, integrity_summary=summary)


class SentinelEngine:
    """Rule-based sentinel engine for pattern matching and policy enforcement."""

    def __init__(self, rules: SentinelRulesConfig) -> None:
        self.rules = rules
        self._compiled: dict[str, re.Pattern[str]] = {}
        for rule in rules.rules:
            self._compiled[rule.id] = rule.compile()

    def evaluate(self, text: str) -> SentinelEvalResult:
        """Evaluate text against all sentinel rules.

        Args:
            text: Text to evaluate (e.g., RAG output).

        Returns:
            SentinelEvalResult with matches and policy action.
        """
        matches: list[SentinelMatch] = []
        output_markers: list[str] = []
        highest_policy: PolicyAction = "allow"

        for rule in self.rules.rules:
            pattern = self._compiled[rule.id]
            for match in pattern.finditer(text):
                matched_text = match.group()
                matches.append(
                    SentinelMatch(
                        rule_id=rule.id,
                        rule_name=rule.name,
                        matched_text=matched_text,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        policy=rule.policy,
                        severity=rule.severity,
                    )
                )
                output_markers.append(matched_text)

                # Escalate policy (block > strip > allow)
                if rule.policy == "block":
                    highest_policy = "block"
                elif rule.policy == "strip" and highest_policy != "block":
                    highest_policy = "strip"

        triggered = len(matches) > 0
        blocked = highest_policy == "block"

        # For strip policy, check if markers would leak
        leaked_markers: list[str] = []
        if highest_policy == "strip" and not blocked:
            # Simulate stripping - markers that survive
            leaked_markers = output_markers  # All matched markers are detected

        return SentinelEvalResult(
            query_id="",  # Set by caller
            triggered=triggered,
            policy_action=highest_policy,
            matches=sorted(matches, key=lambda m: (m.start_pos, m.rule_id)),
            output_markers=sorted(set(output_markers)),
            blocked=blocked,
            leaked_markers=sorted(set(leaked_markers)),
        )


def load_sentinel_rules(rules_path: Path) -> SentinelRulesConfig:
    """Load sentinel rules from YAML file."""
    with rules_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return SentinelRulesConfig.model_validate(data)


def load_sentinel_queries(queries_path: Path) -> list[SentinelQuery]:
    """Load queries from JSONL file."""
    queries: list[SentinelQuery] = []
    with queries_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            queries.append(SentinelQuery.model_validate(data))
    return queries


def load_poison_corpus(corpus_path: Path) -> dict[str, str]:
    """Load poison documents from JSONL file."""
    docs: dict[str, str] = {}
    if not corpus_path.exists():
        return docs
    with corpus_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            doc_id = data.get("doc_id", data.get("id", ""))
            text = data.get("text", data.get("content", ""))
            if doc_id:
                docs[doc_id] = text
    return docs


def load_sentinel_pack(pack_path: Path | str) -> SentinelPack:
    """Load a complete sentinel pack from directory.

    Args:
        pack_path: Path to pack directory containing manifest.yaml.

    Returns:
        Loaded SentinelPack with all data.
    """
    pack_path = Path(pack_path)
    manifest_path = pack_path / "manifest.yaml"

    with manifest_path.open(encoding="utf-8") as f:
        manifest_data = yaml.safe_load(f)
    manifest = SentinelManifest.model_validate(manifest_data)

    # Load rules
    rules_path = pack_path / manifest.sentinel_rules
    rules = load_sentinel_rules(rules_path)

    # Load queries
    queries_path = pack_path / manifest.queries
    queries = load_sentinel_queries(queries_path)

    # Load poison corpus
    poison_docs: dict[str, str] = {}
    if "poison" in manifest.corpus:
        poison_path = pack_path / manifest.corpus["poison"]
        poison_docs = load_poison_corpus(poison_path)

    return SentinelPack(
        manifest=manifest,
        rules=rules,
        queries=queries,
        poison_docs=poison_docs,
        pack_path=pack_path,
    )


def evaluate_sentinel(
    pack: SentinelPack,
    outputs: dict[str, str],
) -> SentinelPackResult:
    """Evaluate sentinel pack against provided outputs.

    Args:
        pack: Loaded sentinel pack.
        outputs: Dict mapping query_id to output text.

    Returns:
        SentinelPackResult with all metrics.
    """
    engine = SentinelEngine(pack.rules)
    results: list[SentinelEvalResult] = []

    total_blocked = 0
    total_leaked = 0
    total_queries = 0

    for query in pack.queries:
        output_text = outputs.get(query.query_id, "")
        if not output_text:
            continue

        total_queries += 1
        eval_result = engine.evaluate(output_text)
        eval_result.query_id = query.query_id
        results.append(eval_result)

        if eval_result.blocked:
            total_blocked += 1
        elif eval_result.leaked_markers:
            total_leaked += 1

    # Compute metrics
    block_rate = total_blocked / total_queries if total_queries > 0 else 0.0
    leak_rate = total_leaked / total_queries if total_queries > 0 else 0.0
    total_triggers = sum(1 for r in results if r.triggered)

    return SentinelPackResult(
        pack_id=pack.manifest.name,
        query_results=results,
        block_rate=block_rate,
        leak_rate=leak_rate,
        total_triggers=total_triggers,
    )


def run_sentinel_from_artifacts(
    pack: SentinelPack,
    artifacts: list[RunArtifact],
) -> SentinelPackResult:
    """Run sentinel evaluation from RunArtifacts.

    This function extracts output text from artifacts and evaluates
    against sentinel rules.

    Args:
        pack: Loaded sentinel pack.
        artifacts: List of run artifacts with output text.

    Returns:
        SentinelPackResult with all metrics.
    """
    # Build outputs dict from artifacts
    outputs: dict[str, str] = {}

    for artifact in artifacts:
        # Map test_id to query_id (strip prefix if present)
        query_id = artifact.test_id
        if query_id.startswith("st_"):
            query_id = query_id[3:]  # Remove "st_" prefix

        # Use retrieved chunks as output to evaluate
        # (simulates RAG output containing retrieved content)
        output_parts: list[str] = []
        for hit in artifact.retrieved:
            if hit.chunk and hit.chunk.text:
                output_parts.append(hit.chunk.text)

        if output_parts:
            outputs[query_id] = "\n".join(output_parts)

    return evaluate_sentinel(pack, outputs)


def pack_to_test_cases(pack: SentinelPack) -> list[Any]:
    """Convert pack queries to TestCase objects for attack runner.

    Args:
        pack: Loaded sentinel pack.

    Returns:
        List of TestCase objects.
    """
    from ragleaklab.attacks.schema import TestCase

    test_cases: list[TestCase] = []
    for query in pack.queries:
        test_cases.append(
            TestCase(
                test_id=f"st_{query.query_id}",  # Prefix to identify pack queries
                threat="semantic",
                query=query.query,
                strategy="direct_extract",
                expected=None,
                description=query.description,
                tags=["sentinel-takeover", "poisoning"],
            )
        )
    return test_cases


def get_sentinel_pack_path() -> Path:
    """Get path to sentinel takeover safe pack."""
    # Check relative to project root
    candidates = [
        Path("data/packs/poisoning_v1/sentinel_takeover_safe"),
        Path(__file__).parent.parent.parent.parent
        / "data"
        / "packs"
        / "poisoning_v1"
        / "sentinel_takeover_safe",
    ]
    for path in candidates:
        if path.exists():
            return path.resolve()
    raise FileNotFoundError("Sentinel takeover safe pack not found")
