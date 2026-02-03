"""Tests for built-in attack packs."""

import pytest

from ragleaklab.packs import (
    AVAILABLE_PACKS,
    get_pack_path,
    get_pack_version,
    list_packs,
)


class TestPackLoader:
    """Tests for pack loading functions."""

    def test_list_packs_returns_all(self):
        """list_packs returns all available packs."""
        packs = list_packs()
        assert "canary-basic" in packs
        assert "verbatim-basic" in packs
        assert "membership-basic" in packs

    def test_get_pack_version(self):
        """get_pack_version returns current version."""
        version = get_pack_version()
        assert version == "v1"

    def test_get_pack_path_valid(self):
        """get_pack_path returns valid path for known pack."""
        for pack_name in AVAILABLE_PACKS:
            path = get_pack_path(pack_name)
            assert path.exists()
            assert path.suffix == ".yaml"

    def test_get_pack_path_unknown(self):
        """get_pack_path raises for unknown pack."""
        with pytest.raises(ValueError, match="Unknown pack"):
            get_pack_path("nonexistent-pack")

    def test_packs_are_loadable(self):
        """All packs can be loaded as valid test cases."""
        from ragleaklab.attacks import load_cases

        for pack_name in AVAILABLE_PACKS:
            path = get_pack_path(pack_name)
            cases = load_cases(path)
            assert len(cases) > 0, f"{pack_name} should have cases"
            for case in cases:
                assert case.test_id, f"Case in {pack_name} missing test_id"
                assert case.threat, f"Case in {pack_name} missing threat"
                assert case.strategy, f"Case in {pack_name} missing strategy"


class TestSemanticPack:
    """Tests specific to semantic-basic pack."""

    def test_semantic_pack_exists(self):
        """semantic-basic pack is registered."""
        assert "semantic-basic" in AVAILABLE_PACKS

    def test_semantic_pack_has_sufficient_cases(self):
        """semantic-basic pack has at least 30 cases."""
        from ragleaklab.attacks import load_cases

        path = get_pack_path("semantic-basic")
        cases = load_cases(path)
        assert len(cases) >= 30, "semantic pack needs at least 30 cases"

    def test_semantic_cases_have_correct_threat(self):
        """All semantic pack cases have threat='semantic'."""
        from ragleaklab.attacks import load_cases

        path = get_pack_path("semantic-basic")
        cases = load_cases(path)
        for case in cases:
            assert case.threat == "semantic", f"{case.test_id} should be semantic threat"

    def test_semantic_baseline_exists(self):
        """Baseline report for semantic_v1 exists."""
        from pathlib import Path

        baseline = Path(__file__).parent.parent / "baselines" / "semantic_v1" / "report.json"
        assert baseline.exists(), "semantic_v1 baseline must exist"

    def test_semantic_baseline_is_valid_json(self):
        """Baseline is valid JSON with required fields."""
        import json
        from pathlib import Path

        baseline = Path(__file__).parent.parent / "baselines" / "semantic_v1" / "report.json"
        data = json.loads(baseline.read_text())

        assert "schema_version" in data
        assert "overall_pass" in data
        assert "aggregates" in data
