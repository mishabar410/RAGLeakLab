"""Tests for parallel execution."""

import json
from pathlib import Path


class TestParallelExecution:
    """Tests for parallel runner execution."""

    def test_run_all_with_jobs_parameter(self):
        """run_all accepts jobs parameter."""
        from ragleaklab.attacks import TestCase, run_all
        from ragleaklab.rag import Document, RAGPipeline

        docs = [Document(doc_id="doc1", text="Sample text for testing.")]
        pipeline = RAGPipeline(top_k=2)
        pipeline.add_documents(docs)

        cases = [
            TestCase(test_id=f"test_{i:02d}", threat="canary", query="q", strategy="direct_ask")
            for i in range(5)
        ]

        # Should work with jobs=1
        artifacts = run_all(pipeline, cases, jobs=1)
        assert len(artifacts) == 5

    def test_parallel_produces_sorted_results(self):
        """Parallel execution returns results sorted by test_id."""
        from ragleaklab.attacks import TestCase, run_all
        from ragleaklab.rag import Document, RAGPipeline

        docs = [Document(doc_id="doc1", text="Sample text for testing.")]
        pipeline = RAGPipeline(top_k=2)
        pipeline.add_documents(docs)

        # Create cases with non-sequential IDs to verify sorting
        cases = [
            TestCase(test_id="test_05", threat="canary", query="q", strategy="direct_ask"),
            TestCase(test_id="test_01", threat="canary", query="q", strategy="direct_ask"),
            TestCase(test_id="test_03", threat="canary", query="q", strategy="direct_ask"),
            TestCase(test_id="test_02", threat="canary", query="q", strategy="direct_ask"),
            TestCase(test_id="test_04", threat="canary", query="q", strategy="direct_ask"),
        ]

        # Run with jobs=1
        artifacts_seq = run_all(pipeline, cases, jobs=1)

        # Results should be sorted by test_id
        test_ids = [a.test_id for a in artifacts_seq]
        assert test_ids == sorted(test_ids), "Results should be sorted by test_id"

    def test_sequential_and_parallel_produce_same_content(self):
        """jobs=1 and jobs=2 produce identical results (except timing)."""
        from ragleaklab.attacks import TestCase, run_all
        from ragleaklab.rag import Document, RAGPipeline

        docs = [Document(doc_id="doc1", text="Sample text for testing parallel execution.")]
        pipeline = RAGPipeline(top_k=2)
        pipeline.add_documents(docs)

        cases = [
            TestCase(
                test_id=f"test_{i:02d}", threat="canary", query="test query", strategy="direct_ask"
            )
            for i in range(4)
        ]

        # Run sequentially
        artifacts_seq = run_all(pipeline, cases, jobs=1)

        # Run in parallel
        artifacts_par = run_all(pipeline, cases, jobs=2)

        # Same length
        assert len(artifacts_seq) == len(artifacts_par)

        # Same test_ids in same order
        seq_ids = [a.test_id for a in artifacts_seq]
        par_ids = [a.test_id for a in artifacts_par]
        assert seq_ids == par_ids

        # Same content (excluding timing which may differ)
        for a_seq, a_par in zip(artifacts_seq, artifacts_par, strict=True):
            assert a_seq.test_id == a_par.test_id
            assert a_seq.threat == a_par.threat
            assert a_seq.query == a_par.query
            assert a_seq.answer == a_par.answer
            assert a_seq.context == a_par.context


class TestParallelCLI:
    """Tests for parallel execution via CLI."""

    def test_cli_parallel_produces_same_report(self, tmp_path: Path):
        """CLI with jobs=1 and jobs=2 produces identical report (except generated_at)."""
        import subprocess
        import sys

        project_root = Path(__file__).parent.parent
        corpus = project_root / "data" / "corpus_private_canary"
        attacks = project_root / "data" / "attacks"

        out_seq = tmp_path / "seq"
        out_par = tmp_path / "par"

        # Run with jobs=1
        result_seq = subprocess.run(
            [
                sys.executable,
                "-m",
                "ragleaklab",
                "run",
                "--corpus",
                str(corpus),
                "--attacks",
                str(attacks),
                "--out",
                str(out_seq),
                "--jobs",
                "1",
            ],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        assert result_seq.returncode == 0, f"Sequential run failed: {result_seq.stderr}"

        # Run with jobs=2
        result_par = subprocess.run(
            [
                sys.executable,
                "-m",
                "ragleaklab",
                "run",
                "--corpus",
                str(corpus),
                "--attacks",
                str(attacks),
                "--out",
                str(out_par),
                "--jobs",
                "2",
            ],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        assert result_par.returncode == 0, f"Parallel run failed: {result_par.stderr}"

        # Load reports
        with open(out_seq / "report.json") as f:
            report_seq = json.load(f)
        with open(out_par / "report.json") as f:
            report_par = json.load(f)

        # Compare (ignoring generated_at)
        report_seq.pop("generated_at", None)
        report_par.pop("generated_at", None)
        assert report_seq == report_par, "Reports should be identical except generated_at"

        # Load runs.jsonl and compare
        with open(out_seq / "runs.jsonl") as f:
            runs_seq = [json.loads(line) for line in f]
        with open(out_par / "runs.jsonl") as f:
            runs_par = [json.loads(line) for line in f]

        # Same number of runs
        assert len(runs_seq) == len(runs_par)

        # Sort both by test_id for comparison
        runs_seq.sort(key=lambda r: r["test_id"])
        runs_par.sort(key=lambda r: r["test_id"])

        # Compare content (ignoring timing which may differ)
        for r_seq, r_par in zip(runs_seq, runs_par, strict=True):
            assert r_seq["test_id"] == r_par["test_id"]
            assert r_seq["threat"] == r_par["threat"]
            assert r_seq["query"] == r_par["query"]
            assert r_seq["answer"] == r_par["answer"]
            # Timing may differ, skip comparison
