#!/usr/bin/env python3
"""Example: Run attack test cases against private corpus."""

from pathlib import Path

from ragleaklab.attacks import load_cases, run_all
from ragleaklab.corpus import find_canaries, load_corpus
from ragleaklab.rag import Document, RAGPipeline


def main():
    """Run attack cases example."""
    # Load corpus
    corpus_path = Path(__file__).parent.parent / "data" / "corpus_private_canary"
    docs = load_corpus(corpus_path)
    rag_docs = [Document(doc_id=d.doc_id, text=d.text) for d in docs]

    print(f"📁 Loaded {len(docs)} documents from corpus")

    # Create pipeline
    pipeline = RAGPipeline(top_k=3)
    pipeline.add_documents(rag_docs)

    # Load attack cases
    attacks_dir = Path(__file__).parent.parent / "data" / "attacks"
    cases = load_cases(attacks_dir)
    print(f"🎯 Loaded {len(cases)} attack test cases")
    print("-" * 60)

    # Run all attacks
    artifacts = run_all(pipeline, cases)

    # Analyze results
    canary_leaks = 0
    for artifact in artifacts:
        canaries = find_canaries(artifact.answer)
        status = "❌ LEAK" if canaries else "✅ SAFE"

        if canaries:
            canary_leaks += 1
            print(f"{status} | {artifact.test_id} | {artifact.threat}")
            print(f"       Query: {artifact.metadata.get('original_query', '')}")
            print(f"       Canaries: {canaries}")
            print()

    # Summary
    print("=" * 60)
    print("📊 Summary:")
    print(f"   Total cases: {len(artifacts)}")
    print(f"   Canary leaks: {canary_leaks}")
    print(f"   Leak rate: {canary_leaks / len(artifacts) * 100:.1f}%")


if __name__ == "__main__":
    main()
