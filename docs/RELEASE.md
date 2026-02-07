# Release Process

This document describes how to prepare and publish a RAGLeakLab release.

---

## Preflight Checklist

Run **all** checks locally before starting a release.
Every step must pass; do not proceed until green.

```bash
# 1. Full CI smoke (format + lint + test + packs + regression + determinism)
bash scripts/ci_smoke.sh

# 2. Explicit determinism verification (≥ 2 packs, 3 runs each)
uv run python -m ragleaklab verify determinism \
  --pack canary-basic --runs 3
uv run python -m ragleaklab verify determinism \
  --pack verbatim-basic --runs 3

# 3. Asset validation (strict mode)
uv run python -m ragleaklab assets validate --path . --strict

# 4. Contract tests
uv run pytest tests/contracts/ -v
```

> [!IMPORTANT]
> If any step fails, fix it before proceeding. A release with failing
> checks is never acceptable.

---

## Version Bump

Update the version in `pyproject.toml`:

```toml
[project]
version = "1.0.0"
```

Verify the version is picked up:

```bash
uv run python -m ragleaklab version
```

---

## Tagging Rules

| Tag | When |
|-----|------|
| `v1.0.0` | First stable release |
| `v1.1.0` | New features (no breaking changes) |
| `v1.0.1` | Bug fixes only |
| `v2.0.0` | Breaking changes to contracts in `V1_CONTRACTS.md` |

Tags are always prefixed with `v` and follow [Semantic Versioning](https://semver.org/).

```bash
git tag v1.0.0
git push origin main --tags
```

---

## Release Artifacts

Every release produces these artifacts in `dist/`:

| Artifact | Command |
|----------|---------|
| Wheel (`.whl`) | `uv build` |
| Source dist (`.tar.gz`) | `uv build` |
| SBOM (`sbom.json`) | `uv run python scripts/generate_sbom.py --out dist/sbom.json` |
| Sample report | `cp out/report.json dist/sample_report.json` |
| Checksums | `sha256sum dist/* > dist/SHA256SUMS` |

### Build Locally

```bash
# Build wheel + sdist
uv build

# Generate SBOM (CycloneDX JSON)
uv run python scripts/generate_sbom.py --out dist/sbom.json

# Generate sample report
uv run python -m ragleaklab run \
  --corpus data/corpus_private_canary \
  --attacks data/attacks \
  --out out/
cp out/report.json dist/sample_report.json

# Checksums
cd dist && sha256sum * > SHA256SUMS && cd ..
```

### Automated Release

Use the GitHub Actions release workflow:

1. Go to **Actions → Release → Run workflow**
2. Enter the version (e.g., `1.0.0`)
3. The workflow runs preflight, builds, generates SBOM, and creates a draft release
4. Review the draft release, then publish

---

## Commit and Tag

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "release: v1.0.0"
git tag v1.0.0
git push origin main --tags
```

---

## Post-Release

### 1. Update CHANGELOG

Move items from `[Unreleased]` to the new version section:

```markdown
## [1.0.0] - 2026-02-07

### Added
- ...
```

### 2. Bump to Next Dev Version

```toml
[project]
version = "1.1.0-dev"
```

### 3. Announce

- Create GitHub Release from the draft (attach `dist/` artifacts)
- Post to relevant channels

---

## Hotfix Process

For critical fixes after release:

```bash
git checkout -b hotfix/v1.0.1 v1.0.0
# Apply minimal fix
# Run preflight checklist
git tag v1.0.1
git push origin hotfix/v1.0.1 --tags
# Cherry-pick to main
```

---

## Local Build Reproduction

To reproduce a release build from a tag:

```bash
git clone --depth 1 --branch v1.0.0 https://github.com/mishabar410/RAGLeakLab.git
cd RAGLeakLab
uv sync --frozen --all-extras
bash scripts/ci_smoke.sh
uv build
uv run python scripts/generate_sbom.py --out dist/sbom.json
sha256sum dist/* > dist/SHA256SUMS
```
