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
