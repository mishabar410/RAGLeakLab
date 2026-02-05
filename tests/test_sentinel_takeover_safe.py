"""Tests for Sentinel Takeover Safe pack."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from ragleaklab.poisoning.packs.sentinel_takeover_safe import (
    SentinelEngine,
    SentinelEvalResult,
    SentinelManifest,
    SentinelMatch,
    SentinelPack,
    SentinelPackResult,
    SentinelQuery,
    SentinelRule,
    SentinelRulesConfig,
    evaluate_sentinel,
    load_sentinel_pack,
    load_sentinel_queries,
    load_sentinel_rules,
    pack_to_test_cases,
)


# Test data fixtures
@pytest.fixture
def sample_rules() -> SentinelRulesConfig:
    """Create sample sentinel rules."""
    return SentinelRulesConfig(
        version="1.0.0",
        rules=[
            SentinelRule(
                id="system_override",
                name="System Override",
                pattern=r"(?i)(SYSTEM_OVERRIDE|IGNORE_PREVIOUS)",
                policy="block",
                severity="high",
            ),
            SentinelRule(
                id="base64_payload",
                name="Base64 Payload",
                pattern=r"[A-Za-z0-9+/]{40,}={0,2}",
                policy="strip",
                severity="medium",
            ),
            SentinelRule(
                id="hidden_marker",
                name="Hidden Marker",
                pattern=r"\[HIDDEN\]",
                policy="strip",
                severity="low",
            ),
        ],
    )


@pytest.fixture
def sample_queries() -> list[SentinelQuery]:
    """Create sample queries."""
    return [
        SentinelQuery(
            query_id="q001",
            query="Test query 1",
            target_doc_ids=["doc1"],
            expected_triggers=["system_override"],
        ),
        SentinelQuery(
            query_id="q002",
            query="Test query 2",
            target_doc_ids=["doc2"],
            expected_triggers=["base64_payload"],
        ),
    ]


class TestSentinelRule:
    """Tests for SentinelRule model."""

    def test_rule_creation(self) -> None:
        """Test basic rule creation."""
        rule = SentinelRule(
            id="test_rule",
            pattern=r"test pattern",
            policy="block",
            severity="high",
        )
        assert rule.id == "test_rule"
        assert rule.policy == "block"
        assert rule.severity == "high"

    def test_rule_compile(self) -> None:
        """Test pattern compilation."""
        rule = SentinelRule(
            id="test",
            pattern=r"(?i)OVERRIDE",
            policy="block",
        )
        compiled = rule.compile()
        assert compiled.search("OVERRIDE") is not None
        assert compiled.search("override") is not None  # Case insensitive


class TestSentinelEngine:
    """Tests for SentinelEngine."""

    def test_evaluate_block_policy(self, sample_rules: SentinelRulesConfig) -> None:
        """Test block policy detection."""
        engine = SentinelEngine(sample_rules)
        result = engine.evaluate("This contains SYSTEM_OVERRIDE trigger")

        assert result.triggered is True
        assert result.policy_action == "block"
        assert result.blocked is True
        assert len(result.matches) == 1
        assert result.matches[0].rule_id == "system_override"

    def test_evaluate_strip_policy(self, sample_rules: SentinelRulesConfig) -> None:
        """Test strip policy detection."""
        engine = SentinelEngine(sample_rules)
        # Long base64-like string
        result = engine.evaluate("Data: YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY3ODkw")

        assert result.triggered is True
        assert result.policy_action == "strip"
        assert result.blocked is False
        assert len(result.leaked_markers) > 0

    def test_evaluate_no_match(self, sample_rules: SentinelRulesConfig) -> None:
        """Test clean text with no triggers."""
        engine = SentinelEngine(sample_rules)
        result = engine.evaluate("Completely normal text with nothing suspicious")

        assert result.triggered is False
        assert result.policy_action == "allow"
        assert result.blocked is False
        assert len(result.matches) == 0

    def test_evaluate_multiple_matches(self, sample_rules: SentinelRulesConfig) -> None:
        """Test text with multiple triggers."""
        engine = SentinelEngine(sample_rules)
        result = engine.evaluate("SYSTEM_OVERRIDE and also IGNORE_PREVIOUS")

        assert result.triggered is True
        assert result.policy_action == "block"
        assert len(result.matches) == 2

    def test_block_takes_precedence_over_strip(self, sample_rules: SentinelRulesConfig) -> None:
        """Test that block policy takes precedence over strip."""
        engine = SentinelEngine(sample_rules)
        result = engine.evaluate("SYSTEM_OVERRIDE and also [HIDDEN] marker")

        assert result.policy_action == "block"  # Block wins over strip
        assert result.blocked is True


class TestPackLoading:
    """Tests for pack loading functions."""

    def test_load_sentinel_rules(self, tmp_path: Path) -> None:
        """Test loading rules from YAML file."""
        rules_data = {
            "version": "1.0.0",
            "rules": [
                {
                    "id": "test_rule",
                    "pattern": "TEST",
                    "policy": "block",
                    "severity": "high",
                }
            ],
        }
        rules_path = tmp_path / "rules.yaml"
        with rules_path.open("w") as f:
            yaml.dump(rules_data, f)

        rules = load_sentinel_rules(rules_path)
        assert len(rules.rules) == 1
        assert rules.rules[0].id == "test_rule"

    def test_load_sentinel_queries(self, tmp_path: Path) -> None:
        """Test loading queries from JSONL file."""
        queries_data = [
            {"query_id": "q1", "query": "Query 1", "target_doc_ids": ["d1"]},
            {"query_id": "q2", "query": "Query 2", "target_doc_ids": ["d2"]},
        ]
        queries_path = tmp_path / "queries.jsonl"
        with queries_path.open("w") as f:
            for q in queries_data:
                f.write(json.dumps(q) + "\n")

        queries = load_sentinel_queries(queries_path)
        assert len(queries) == 2
        assert queries[0].query_id == "q1"


class TestEvaluateSentinel:
    """Tests for sentinel pack evaluation."""

    def test_evaluate_sentinel_pack(
        self, sample_rules: SentinelRulesConfig, sample_queries: list[SentinelQuery]
    ) -> None:
        """Test pack evaluation with outputs."""
        manifest = SentinelManifest(
            name="test-pack",
            sentinel_rules="rules.yaml",
            queries="queries.jsonl",
        )
        pack = SentinelPack(
            manifest=manifest,
            rules=sample_rules,
            queries=sample_queries,
            poison_docs={},
            pack_path=Path("."),
        )

        outputs = {
            "q001": "This contains SYSTEM_OVERRIDE trigger",
            "q002": "Normal text without triggers",
        }

        result = evaluate_sentinel(pack, outputs)

        assert result.pack_id is not None or result.pack_id == ""
        assert len(result.query_results) == 2
        # First query should have triggered
        q1_result = next(r for r in result.query_results if r.query_id == "q001")
        assert q1_result.triggered is True
        assert q1_result.blocked is True


class TestPackToTestCases:
    """Tests for converting pack to test cases."""

    def test_pack_to_test_cases(
        self, sample_rules: SentinelRulesConfig, sample_queries: list[SentinelQuery]
    ) -> None:
        """Test conversion to TestCase objects."""
        manifest = SentinelManifest(
            name="test-pack",
            sentinel_rules="rules.yaml",
            queries="queries.jsonl",
        )
        pack = SentinelPack(
            manifest=manifest,
            rules=sample_rules,
            queries=sample_queries,
            poison_docs={},
            pack_path=Path("."),
        )

        test_cases = pack_to_test_cases(pack)

        assert len(test_cases) == 2
        assert test_cases[0].test_id == "st_q001"
        assert test_cases[1].test_id == "st_q002"
        assert all("sentinel-takeover" in tc.tags for tc in test_cases)


class TestResultToIntegritySection:
    """Tests for converting results to IntegritySection."""

    def test_result_to_integrity_section(self) -> None:
        """Test conversion to IntegritySection."""
        result = SentinelPackResult(
            pack_id="sentinel-takeover-safe",
            query_results=[
                SentinelEvalResult(
                    query_id="q001",
                    triggered=True,
                    policy_action="block",
                    matches=[
                        SentinelMatch(
                            rule_id="test",
                            matched_text="OVERRIDE",
                            start_pos=0,
                            end_pos=8,
                            policy="block",
                            severity="high",
                        )
                    ],
                    output_markers=["OVERRIDE"],
                    blocked=True,
                    leaked_markers=[],
                )
            ],
            block_rate=1.0,
            leak_rate=0.0,
            total_triggers=1,
        )

        section = result.to_integrity_section()

        assert len(section.packs) == 1
        assert section.packs[0].triggered is True
        assert section.packs[0].policy_action == "block"
        assert section.integrity_summary.sentinel_triggered == 1


class TestRealPackLoading:
    """Tests for loading the real sentinel pack."""

    def test_load_real_pack(self) -> None:
        """Test loading the actual sentinel pack from data/."""
        from ragleaklab.poisoning.packs import get_poisoning_pack_path

        pack_path = get_poisoning_pack_path("sentinel-takeover-safe")
        pack = load_sentinel_pack(pack_path)

        assert pack.manifest.name == "sentinel-takeover-safe"
        assert len(pack.rules.rules) > 0
        assert len(pack.queries) > 0
        assert len(pack.poison_docs) > 0

    def test_real_pack_evaluation(self) -> None:
        """Test evaluating queries against real pack rules."""
        from ragleaklab.poisoning.packs import get_poisoning_pack_path

        pack_path = get_poisoning_pack_path("sentinel-takeover-safe")
        pack = load_sentinel_pack(pack_path)

        # Simulate outputs that contain poison content
        outputs: dict[str, str] = {}
        for query in pack.queries[:3]:  # Test first 3 queries
            # Get content from target docs
            target_texts = [pack.poison_docs.get(doc_id, "") for doc_id in query.target_doc_ids]
            outputs[query.query_id] = "\n".join(target_texts)

        result = evaluate_sentinel(pack, outputs)

        # Should detect triggers in poison docs
        assert result.total_triggers > 0
