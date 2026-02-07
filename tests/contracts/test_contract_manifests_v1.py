"""V1 contract tests for asset manifests validation.

Ensures that all YAML manifests in data/ and benchmarks/ parse correctly
against their respective pydantic schemas, as documented in
docs/V1_CONTRACTS.md § E (Asset Manifests).
"""

from pathlib import Path

import pytest
import yaml

from ragleaklab.assets.schema import AttacksManifest, CorpusManifest, PackManifest

PROJECT_ROOT = Path(__file__).parent.parent.parent


def _collect_manifests(base_dir: Path) -> list[tuple[Path, str]]:
    """Collect manifest files with their detected type.

    Returns list of (path, type) where type is one of:
    corpus, attacks, pack, bundle, other.
    """
    results = []
    for yaml_path in sorted(base_dir.rglob("*.yaml")):
        # Skip non-manifest YAML files (rules, patches, individual attack files, etc.)
        name = yaml_path.name
        if name == "corpus.yaml":
            results.append((yaml_path, "corpus"))
        elif name == "attacks.yaml":
            results.append((yaml_path, "attacks"))
        elif name.endswith(".pack.yaml") or name == "pack.yaml":
            results.append((yaml_path, "pack"))
        elif name == "bundle.yaml":
            results.append((yaml_path, "bundle"))
        elif name == "manifest.yaml":
            # Poisoning pack manifests — treat as pack-like
            results.append((yaml_path, "pack_like"))
    return results


class TestDataManifestsValidate:
    """Validate all manifests in data/ against pydantic schemas."""

    DATA_DIR = PROJECT_ROOT / "data"

    def test_data_dir_has_manifests(self):
        """data/ directory contains at least one manifest."""
        manifests = _collect_manifests(self.DATA_DIR)
        assert len(manifests) > 0, "data/ should contain at least one manifest YAML"

    @pytest.fixture()
    def data_manifests(self) -> list[tuple[Path, str]]:
        return _collect_manifests(self.DATA_DIR)

    def test_corpus_manifests_validate(self, data_manifests: list[tuple[Path, str]]):
        """All corpus.yaml files validate against CorpusManifest."""
        corpus_files = [(p, t) for p, t in data_manifests if t == "corpus"]
        assert len(corpus_files) > 0, "Should have at least one corpus.yaml"

        for path, _ in corpus_files:
            with open(path) as f:
                raw = yaml.safe_load(f)
            manifest = CorpusManifest(**raw)
            assert manifest.name, f"{path}: name must be non-empty"
            assert manifest.version, f"{path}: version must be non-empty"

    def test_attacks_manifests_validate(self, data_manifests: list[tuple[Path, str]]):
        """All attacks.yaml files validate against AttacksManifest."""
        attacks_files = [(p, t) for p, t in data_manifests if t == "attacks"]
        if not attacks_files:
            pytest.skip("No attacks.yaml found in data/")

        for path, _ in attacks_files:
            with open(path) as f:
                raw = yaml.safe_load(f)
            manifest = AttacksManifest(**raw)
            assert manifest.name, f"{path}: name must be non-empty"
            assert manifest.version, f"{path}: version must be non-empty"

    def test_pack_manifests_validate(self, data_manifests: list[tuple[Path, str]]):
        """All pack.yaml files validate against PackManifest."""
        pack_files = [(p, t) for p, t in data_manifests if t == "pack"]
        if not pack_files:
            pytest.skip("No pack.yaml found in data/")

        for path, _ in pack_files:
            with open(path) as f:
                raw = yaml.safe_load(f)
            manifest = PackManifest(**raw)
            assert manifest.name, f"{path}: name must be non-empty"
            assert manifest.version, f"{path}: version must be non-empty"

    def test_pack_like_manifests_have_name_and_version(
        self, data_manifests: list[tuple[Path, str]]
    ):
        """Poisoning pack manifest.yaml files have name and version."""
        pack_like = [(p, t) for p, t in data_manifests if t == "pack_like"]
        if not pack_like:
            pytest.skip("No poisoning manifest.yaml found")

        for path, _ in pack_like:
            with open(path) as f:
                raw = yaml.safe_load(f)
            assert "name" in raw, f"{path}: missing 'name'"
            assert "version" in raw, f"{path}: missing 'version'"


class TestBenchmarkManifestsValidate:
    """Validate all manifests in benchmarks/ directory."""

    BENCH_DIR = PROJECT_ROOT / "benchmarks"

    def test_benchmark_bundle_has_required_fields(self):
        """bundle.yaml has name, version, and packs list."""
        if not self.BENCH_DIR.exists():
            pytest.skip("benchmarks/ directory not found")

        bundles = list(self.BENCH_DIR.rglob("bundle.yaml"))
        assert len(bundles) > 0, "benchmarks/ should have at least one bundle.yaml"

        for path in bundles:
            with open(path) as f:
                raw = yaml.safe_load(f)
            assert "name" in raw, f"{path}: missing 'name'"
            assert "version" in raw, f"{path}: missing 'version'"
            assert "packs" in raw, f"{path}: missing 'packs'"
            assert isinstance(raw["packs"], list), f"{path}: 'packs' must be a list"
            assert len(raw["packs"]) > 0, f"{path}: 'packs' must be non-empty"
