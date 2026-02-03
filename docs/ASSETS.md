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

---

## Asset Manifests

RAGLeakLab uses YAML manifests to version and validate assets. Each asset type has a corresponding manifest format.

### Corpus Manifest (`corpus.yaml`)

Located in each corpus directory (e.g., `data/corpus_public/corpus.yaml`):

```yaml
name: corpus_public           # Unique identifier
version: "1.0.0"              # Semantic version
seed: 1337                    # Optional: random seed if generated
doc_count: 50                 # Number of documents
claims_supported:             # Claim types present (empty if none)
  - EMAIL
  - PHONE
  - ACCOUNT_ID
hash: "a1b2c3d4..."           # SHA-256 of file tree
```

### Attacks Manifest (`attacks.yaml`)

Located in attack directories (e.g., `data/attacks/attacks.yaml`):

```yaml
name: attacks_default         # Unique identifier
version: "1.0.0"              # Semantic version
threat_coverage:              # Threat types covered
  - canary
  - verbatim
case_count: 20                # Total test cases
hash: "e5f6g7h8..."           # SHA-256 of file tree
```

### Pack Manifest (`pack.yaml`)

Located alongside pack files (e.g., `src/ragleaklab/packs/v1/canary-basic.pack.yaml`):

```yaml
name: canary-basic            # Pack name
version: "1.0.0"              # Semantic version
corpus_ref: null              # Optional corpus reference (name@version)
attacks_ref: "canary-basic@1.0.0"  # Required attacks reference
thresholds_ref: null          # Optional thresholds config
expected_report_fields:       # Required fields in report
  - aggregates.canary
```

## Versioning Rules

1. **Semantic Versioning**: All assets use `MAJOR.MINOR.PATCH` format
2. **Hash Integrity**: SHA-256 hash computed over file tree (excluding manifests, `out/`, `__pycache__/`)
3. **Immutability**: Once published, a version's hash must not change
4. **Backward Compatibility**: MINOR/PATCH updates must not break existing tests

## Validation

Use the assets module to validate manifests:

```python
from ragleaklab.assets import load_corpus_manifest, validate_hash
from pathlib import Path

manifest = load_corpus_manifest(Path("data/corpus_public/corpus.yaml"))
assert validate_hash(manifest, Path("data/corpus_public"))
```

## Hash Computation

Hashes are computed deterministically:

1. Walk directory recursively
2. Exclude: `__pycache__/`, `*.pyc`, `.git/`, `out/`, manifest files
3. Sort files by relative path
4. For each file: hash(relative_path + contents)
5. Combine into final SHA-256

```python
from ragleaklab.assets.hash import compute_tree_hash
from pathlib import Path

h = compute_tree_hash(Path("data/corpus_public"))
print(h)  # 64-character hex string
```

## Validation

Validate all manifests in a directory:

```bash
# Validate all assets from project root
ragleaklab assets validate --path .

# Validate specific directory
ragleaklab assets validate --path data/

# Strict mode (treat warnings as errors)
ragleaklab assets validate --path . --strict
```

This checks:
- Schema validity against Pydantic models
- Hash integrity (computed vs. stored)
- Reference resolution in pack manifests
- Report field validity


