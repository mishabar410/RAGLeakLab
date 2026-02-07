"""Tests for attacks/coverage.py."""

from ragleaklab.attacks.coverage import (
    CoverageReport,
    compute_coverage,
    load_expectations_from_manifest,
)


class TestComputeCoverage:
    """Tests for compute_coverage."""

    def _write_cases(self, tmp_path, cases: list[dict]):
        import yaml

        cases_file = tmp_path / "cases.yaml"
        cases_file.write_text(yaml.dump(cases))

    def test_basic_coverage(self, tmp_path):
        import yaml

        cases_file = tmp_path / "cases.yaml"
        cases_file.write_text(
            yaml.dump(
                [
                    {
                        "test_id": "t1",
                        "threat": "canary",
                        "query": "q1",
                        "strategy": "direct_ask",
                    },
                    {
                        "test_id": "t2",
                        "threat": "verbatim",
                        "query": "q2",
                        "strategy": "indirect_ask",
                    },
                ]
            )
        )

        report = compute_coverage(tmp_path)
        assert isinstance(report, CoverageReport)
        assert report.total_cases == 2
        assert report.threats["canary"] == 1
        assert report.strategies["direct_ask"] == 1
        assert report.matrix["canary"]["direct_ask"] == 1

    def test_missing_combos(self, tmp_path):
        import yaml

        cases_file = tmp_path / "cases.yaml"
        cases_file.write_text(
            yaml.dump(
                [
                    {
                        "test_id": "t1",
                        "threat": "canary",
                        "query": "q1",
                        "strategy": "direct_ask",
                    },
                ]
            )
        )

        report = compute_coverage(
            tmp_path,
            expected_threats=["canary", "verbatim"],
            expected_strategies=["direct_ask", "indirect_ask"],
        )
        # Missing: canary+indirect_ask, verbatim+direct_ask, verbatim+indirect_ask
        assert len(report.missing_combos) == 3

    def test_empty_dir(self, tmp_path):
        report = compute_coverage(tmp_path)
        assert report.total_cases == 0

    def test_tags_counted(self, tmp_path):
        import yaml

        cases_file = tmp_path / "cases.yaml"
        cases_file.write_text(
            yaml.dump(
                [
                    {
                        "test_id": "t1",
                        "threat": "canary",
                        "query": "q",
                        "strategy": "direct_ask",
                        "tags": ["fast", "core"],
                    },
                ]
            )
        )
        report = compute_coverage(tmp_path)
        assert report.tags["fast"] == 1
        assert report.tags["core"] == 1


class TestLoadExpectationsFromManifest:
    """Tests for load_expectations_from_manifest."""

    def test_with_manifest(self, tmp_path):
        import yaml

        manifest = tmp_path / "attacks.yaml"
        manifest.write_text(
            yaml.dump(
                {
                    "threat_coverage": ["canary", "verbatim"],
                    "strategy_coverage": ["direct_ask"],
                }
            )
        )
        threats, strategies = load_expectations_from_manifest(tmp_path)
        assert threats == ["canary", "verbatim"]
        assert strategies == ["direct_ask"]

    def test_no_manifest(self, tmp_path):
        threats, strategies = load_expectations_from_manifest(tmp_path)
        assert threats == []
        assert strategies == []

    def test_file_path_returns_empty(self, tmp_path):
        # When attacks_path is a file, not a dir → no manifest
        f = tmp_path / "cases.yaml"
        f.write_text("[]")
        threats, strategies = load_expectations_from_manifest(f)
        assert threats == []
        assert strategies == []
