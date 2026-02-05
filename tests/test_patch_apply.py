"""Tests for patch application."""

from __future__ import annotations

import json

import pytest
import yaml

from ragleaklab.corpus.patch import apply_patch, load_patch


class TestLoadPatch:
    """Tests for loading patch specifications."""

    def test_load_yaml_patch(self, tmp_path):
        """Load patch from YAML file."""
        patch_dir = tmp_path / "patch"
        patch_dir.mkdir()

        patch_yaml = patch_dir / "patch.yaml"
        patch_yaml.write_text(
            """
add_docs:
  - doc_id: new_doc
    path: docs/new.txt
remove_docs:
  - old_doc
"""
        )

        spec = load_patch(patch_dir)
        assert len(spec.add_docs) == 1
        assert spec.add_docs[0].doc_id == "new_doc"
        assert len(spec.remove_docs) == 1
        assert spec.remove_docs[0] == "old_doc"

    def test_load_json_patch(self, tmp_path):
        """Load patch from JSON file."""
        patch_dir = tmp_path / "patch"
        patch_dir.mkdir()

        patch_json = patch_dir / "patch.json"
        patch_json.write_text(
            json.dumps(
                {
                    "add_docs": [{"doc_id": "doc1", "path": "docs/doc1.txt"}],
                    "add_claims": [{"doc_id": "doc1", "claim_id": "C1", "text": "claim text"}],
                }
            )
        )

        spec = load_patch(patch_dir)
        assert len(spec.add_docs) == 1
        assert len(spec.add_claims) == 1

    def test_load_missing_patch_raises(self, tmp_path):
        """Raise error if no patch file exists."""
        with pytest.raises(FileNotFoundError):
            load_patch(tmp_path)


class TestApplyPatch:
    """Tests for applying patches to corpus."""

    def test_add_document(self, tmp_path):
        """Adding a document creates it in output."""
        # Create base corpus
        base = tmp_path / "base"
        base.mkdir()
        (base / "existing.txt").write_text("existing content")

        # Create patch
        patch = tmp_path / "patch"
        patch.mkdir()
        patch_docs = patch / "docs"
        patch_docs.mkdir()
        (patch_docs / "new.txt").write_text("new content")
        (patch / "patch.yaml").write_text(
            """
add_docs:
  - doc_id: new_doc
    path: docs/new.txt
"""
        )

        # Apply
        out = tmp_path / "out"
        apply_patch(base, patch, out)

        assert (out / "existing.txt").exists()
        assert (out / "new_doc.txt").exists()
        assert (out / "new_doc.txt").read_text() == "new content"

    def test_remove_document(self, tmp_path):
        """Removing a document excludes it from output."""
        # Create base corpus
        base = tmp_path / "base"
        base.mkdir()
        (base / "keep.txt").write_text("keep this")
        (base / "remove.txt").write_text("remove this")

        # Create patch
        patch = tmp_path / "patch"
        patch.mkdir()
        (patch / "patch.yaml").write_text(
            """
remove_docs:
  - remove
"""
        )

        # Apply
        out = tmp_path / "out"
        apply_patch(base, patch, out)

        assert (out / "keep.txt").exists()
        assert not (out / "remove.txt").exists()

    def test_add_claims(self, tmp_path):
        """Adding claims updates claims.jsonl."""
        # Create base corpus
        base = tmp_path / "base"
        base.mkdir()
        (base / "doc1.txt").write_text("doc 1")

        # Create patch with claims
        patch = tmp_path / "patch"
        patch.mkdir()
        (patch / "patch.yaml").write_text(
            """
add_claims:
  - doc_id: doc1
    claim_id: C001
    text: "sensitive claim"
    type: security
    sensitivity: high
"""
        )

        # Apply
        out = tmp_path / "out"
        apply_patch(base, patch, out)

        assert (out / "claims.jsonl").exists()
        claims = [json.loads(line) for line in (out / "claims.jsonl").read_text().splitlines()]
        assert len(claims) == 1
        assert claims[0]["claim_id"] == "C001"

    def test_remove_claims(self, tmp_path):
        """Removing claims filters them from output."""
        # Create base corpus with claims
        base = tmp_path / "base"
        base.mkdir()
        (base / "doc1.txt").write_text("doc 1")
        (base / "claims.jsonl").write_text(
            json.dumps({"doc_id": "doc1", "claim_id": "C001", "text": "claim 1"})
            + "\n"
            + json.dumps({"doc_id": "doc1", "claim_id": "C002", "text": "claim 2"})
            + "\n"
        )

        # Create patch
        patch = tmp_path / "patch"
        patch.mkdir()
        (patch / "patch.yaml").write_text(
            """
remove_claims:
  - doc_id: doc1
    claim_id: C001
"""
        )

        # Apply
        out = tmp_path / "out"
        apply_patch(base, patch, out)

        claims = [json.loads(line) for line in (out / "claims.jsonl").read_text().splitlines()]
        assert len(claims) == 1
        assert claims[0]["claim_id"] == "C002"

    def test_deterministic_ordering(self, tmp_path):
        """Claims are sorted deterministically."""
        # Create base corpus
        base = tmp_path / "base"
        base.mkdir()
        (base / "doc_z.txt").write_text("doc z")
        (base / "doc_a.txt").write_text("doc a")

        # Create patch with mixed order claims
        patch = tmp_path / "patch"
        patch.mkdir()
        (patch / "patch.yaml").write_text(
            """
add_claims:
  - doc_id: doc_z
    claim_id: C002
    text: "claim z2"
  - doc_id: doc_a
    claim_id: C001
    text: "claim a1"
  - doc_id: doc_z
    claim_id: C001
    text: "claim z1"
"""
        )

        # Apply
        out = tmp_path / "out"
        apply_patch(base, patch, out)

        claims = [json.loads(line) for line in (out / "claims.jsonl").read_text().splitlines()]
        # Should be sorted by (doc_id, claim_id)
        assert claims[0]["doc_id"] == "doc_a"
        assert claims[1]["doc_id"] == "doc_z"
        assert claims[1]["claim_id"] == "C001"
        assert claims[2]["doc_id"] == "doc_z"
        assert claims[2]["claim_id"] == "C002"

    def test_corpus_yaml_updated(self, tmp_path):
        """Corpus.yaml is updated with new hash."""
        # Create base corpus with corpus.yaml
        base = tmp_path / "base"
        base.mkdir()
        (base / "doc1.txt").write_text("content")
        (base / "corpus.yaml").write_text(
            """
name: test_corpus
version: "1.0.0"
hash: "original_hash"
"""
        )

        # Create patch
        patch = tmp_path / "patch"
        patch.mkdir()
        patch_docs = patch / "docs"
        patch_docs.mkdir()
        (patch_docs / "new.txt").write_text("new")
        (patch / "patch.yaml").write_text(
            """
add_docs:
  - doc_id: new
    path: docs/new.txt
"""
        )

        # Apply
        out = tmp_path / "out"
        apply_patch(base, patch, out)

        corpus_meta = yaml.safe_load((out / "corpus.yaml").read_text())
        assert corpus_meta["hash"] != "original_hash"
        assert corpus_meta["patched_from"] == "base"
        assert corpus_meta["doc_count"] == 2
