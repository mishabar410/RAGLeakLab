# Asset Generation

RAGLeakLab includes tools for generating synthetic test data with deterministic, seeded random values.

## Quick Start

```bash
# Generate a synthetic corpus with 50 documents and 3 claims each
uv run python -m ragleaklab assets build \
  --out data/generated/test_v1 \
  --seed 1337 \
  --docs 50 \
  --claims-per-doc 3
```

## Command Options

| Option | Default | Description |
|--------|---------|-------------|
| `--out`, `-o` | (required) | Output directory |
| `--seed`, `-s` | 42 | Random seed for determinism |
| `--docs`, `-d` | 10 | Number of documents |
| `--claims-per-doc`, `-c` | 3 | Claims per document |
| `--no-pii` | false | Exclude PII-type claims (EMAIL, PHONE) |

## Output Files

The generator creates:

```
data/generated/test_v1/
├── doc_0000.txt         # Document with embedded claims
├── doc_0001.txt
├── ...
├── claims.jsonl         # All claims in JSONL format
└── manifest.json        # Generation parameters and hash
```

## Claim Types

| Type | Example |
|------|---------|
| `EMAIL` | "Contact email is john.doe@example.com" |
| `PHONE` | "Phone number is 555-123-4567" |
| `ACCOUNT_ID` | "Account ID is ACC-847291" |
| `SECRET_CODEWORD` | "Secret codeword is ALPHA-BRAVO-CHARLIE" |
| `INTERNAL_PROJECT` | "Project codename is Phoenix-Dragon" |

## Determinism

Same seed always produces identical output:

```bash
# These two runs produce identical claims.jsonl
ragleaklab assets build --out run1 --seed 1337
ragleaklab assets build --out run2 --seed 1337

# Verify
diff run1/claims.jsonl run2/claims.jsonl  # No differences
```

## Manifest

The `manifest.json` records generation parameters:

```json
{
  "generated_at": "2024-01-15T10:30:00",
  "seed": 1337,
  "n_docs": 50,
  "claims_per_doc": 3,
  "include_pii": true,
  "total_claims": 150,
  "corpus_hash": "a1b2c3d4e5f6..."
}
```

Use `corpus_hash` to verify reproducibility across runs.

## Use Cases

1. **CI Testing**: Generate consistent test data for regression checks
2. **Benchmarking**: Compare RAG pipelines with identical inputs
3. **Development**: Quick setup of test corpora without real data
