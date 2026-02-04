"""Contract tests for runs.jsonl schema.

Validates that runs.jsonl entries adhere to the public contract:
- Each line is valid JSON
- Required fields present in each entry
- Field types are correct
"""

import json
from pathlib import Path
from typing import ClassVar

# Path to golden samples
GOLDEN_DIR = Path(__file__).parent / "golden"


class TestRunsSchema:
    """Contract tests for runs.jsonl structure."""

    # Required fields in each runs.jsonl entry
    REQUIRED_FIELDS: ClassVar[set[str]] = {
        "test_id",
        "threat",
        "query",
        "transformed_query",
        "retrieved_ids",
        "answer",
    }

    # Optional but expected fields
    OPTIONAL_FIELDS: ClassVar[set[str]] = {
        "context",
        "timings",
        "context_stats",
        "hashes",
        "attribution",
        "canary_detected",
        "canary_count",
        "verbatim_score",
        "details",
    }

    def _load_runs(self, path: Path) -> list[dict]:
        """Load runs.jsonl file."""
        entries = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries

    def test_golden_runs_is_valid_jsonl(self):
        """Golden runs.jsonl contains valid JSONL."""
        runs_path = GOLDEN_DIR / "runs.jsonl"
        entries = self._load_runs(runs_path)
        assert len(entries) > 0, "runs.jsonl should have at least one entry"

    def test_golden_runs_has_required_fields(self):
        """Each entry in runs.jsonl has required fields."""
        runs_path = GOLDEN_DIR / "runs.jsonl"
        entries = self._load_runs(runs_path)

        for i, entry in enumerate(entries):
            missing = self.REQUIRED_FIELDS - set(entry.keys())
            assert not missing, f"Entry {i} missing required fields: {missing}"

    def test_golden_runs_field_types(self):
        """Fields in runs.jsonl have correct types."""
        runs_path = GOLDEN_DIR / "runs.jsonl"
        entries = self._load_runs(runs_path)

        for entry in entries:
            assert isinstance(entry["test_id"], str)
            assert isinstance(entry["threat"], str)
            assert isinstance(entry["query"], str)
            assert isinstance(entry["transformed_query"], str)
            assert isinstance(entry["retrieved_ids"], list)
            assert isinstance(entry["answer"], str)

            # Optional field types
            if "context" in entry:
                assert isinstance(entry["context"], str)
            if "timings" in entry:
                assert isinstance(entry["timings"], dict)
            if "context_stats" in entry:
                assert isinstance(entry["context_stats"], dict)
            if "hashes" in entry:
                assert isinstance(entry["hashes"], dict)
            if "attribution" in entry:
                assert isinstance(entry["attribution"], list)
            if "canary_detected" in entry:
                assert isinstance(entry["canary_detected"], bool)
            if "canary_count" in entry:
                assert isinstance(entry["canary_count"], int)
            if "verbatim_score" in entry:
                assert isinstance(entry["verbatim_score"], (int, float))

    def test_test_id_is_non_empty(self):
        """test_id field is non-empty string."""
        runs_path = GOLDEN_DIR / "runs.jsonl"
        entries = self._load_runs(runs_path)

        for entry in entries:
            assert entry["test_id"], "test_id should be non-empty"
            assert len(entry["test_id"]) > 0

    def test_threat_is_valid(self):
        """threat field contains known threat type."""
        runs_path = GOLDEN_DIR / "runs.jsonl"
        entries = self._load_runs(runs_path)

        known_threats = {"canary", "verbatim", "membership", "semantic", "multi-turn"}
        for entry in entries:
            assert entry["threat"] in known_threats, f"Unknown threat: {entry['threat']}"

    def test_retrieved_ids_is_list_of_strings(self):
        """retrieved_ids is a list of strings."""
        runs_path = GOLDEN_DIR / "runs.jsonl"
        entries = self._load_runs(runs_path)

        for entry in entries:
            assert isinstance(entry["retrieved_ids"], list)
            for doc_id in entry["retrieved_ids"]:
                assert isinstance(doc_id, str)

    def test_entries_are_sorted_by_test_id(self):
        """Entries should be sorted by test_id for determinism."""
        runs_path = GOLDEN_DIR / "runs.jsonl"
        entries = self._load_runs(runs_path)

        if len(entries) > 1:
            test_ids = [e["test_id"] for e in entries]
            assert test_ids == sorted(test_ids), "Entries should be sorted by test_id"
