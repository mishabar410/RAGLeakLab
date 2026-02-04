# Release Process

This document describes how to prepare and publish a RAGLeakLab release.

## Pre-Release Checklist

Before starting a release, verify:

- [ ] All CI checks pass on `main`
- [ ] No open security issues
- [ ] CHANGELOG updated with all changes

## Release Steps

### 1. Validate Assets

```bash
uv run python -m ragleaklab assets validate --path . --strict
```

All asset manifests must be valid with no warnings.

### 2. Run All Packs

```bash
# Run each pack and verify against baselines
uv run python -m ragleaklab run \
  --corpus data/corpus_private_canary \
  --pack canary-basic \
  --out out/canary/

uv run python -m ragleaklab run \
  --corpus data/corpus_private_canary \
  --pack verbatim-basic \
  --out out/verbatim/

uv run python -m ragleaklab run \
  --corpus data/corpus_private_canary \
  --pack semantic-basic \
  --out out/semantic/
```

### 3. Verify Regression Gates

```bash
uv run python -m ragleaklab diff \
  --baseline baselines/v1/report.json \
  --current out/canary/report.json

uv run python -m ragleaklab diff \
  --baseline baselines/semantic_v1/report.json \
  --current out/semantic/report.json
```

All gates must pass.

### 4. Bump Version

Update version in `pyproject.toml`:

```toml
[project]
version = "X.Y.Z"
```

### 5. Update CHANGELOG

Add release entry to `CHANGELOG.md`:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- New features...

### Changed
- Changes...

### Fixed
- Bug fixes...
```

### 6. Commit and Tag

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "release: v0.X.Y"
git tag v0.X.Y
git push origin main --tags
```

### 7. Build Package

```bash
uv build
```

Verify the built package:

```bash
ls dist/
# ragleaklab-X.Y.Z.tar.gz
# ragleaklab-X.Y.Z-py3-none-any.whl
```

### 8. Generate SBOM

Generate a CycloneDX Software Bill of Materials:

```bash
uv run python scripts/generate_sbom.py --out dist/sbom.json
```

The SBOM includes all runtime and dev dependencies from the environment.

### 9. Publish (Optional)

```bash
# Test PyPI
uv publish --repository testpypi

# Production PyPI
uv publish
```

### 10. Create GitHub Release

**Option A: Manual release**

1. Go to Releases → Draft new release
2. Choose tag `vX.Y.Z`
3. Copy CHANGELOG entry as description
4. Attach wheel/sdist/sbom from `dist/`
5. Publish

**Option B: Use release workflow**

1. Go to Actions → Release → Run workflow
2. Enter version (e.g., `0.2.0`)
3. Workflow validates, builds, generates SBOM, and creates draft release
4. Review and publish the draft release

## SBOM (Software Bill of Materials)

After building, the SBOM is located at `dist/sbom.json`. It contains:
- All runtime dependencies
- All dev dependencies  
- Package URLs (purls) for vulnerability scanning
- CycloneDX 1.4 format compatible with most security tools

To regenerate SBOM manually:

```bash
uv run python scripts/generate_sbom.py --out dist/sbom.json
```

## Local Build Reproduction

To reproduce a release build locally:

```bash
# 1. Clone at specific tag
git clone --depth 1 --branch vX.Y.Z https://github.com/mishabar410/RAGLeakLab.git
cd RAGLeakLab

# 2. Install dependencies (exact versions from uv.lock)
uv sync --all-extras

# 3. Run validation
uv run pytest -q
uv run python -m ragleaklab assets validate --path .

# 4. Build
uv build

# 5. Generate SBOM
uv run python scripts/generate_sbom.py --out dist/sbom.json

# 6. Verify
ls -la dist/
```

## Version Numbering

We follow [Semantic Versioning](https://semver.org/):

| Version | When to bump |
|---------|--------------|
| MAJOR (1.0.0) | Breaking changes to CLI or report schema |
| MINOR (0.2.0) | New features, new attack types |
| PATCH (0.1.1) | Bug fixes, documentation |

## Hotfix Process

For critical fixes:

1. Create branch from tag: `git checkout -b hotfix/v0.1.1 v0.1.0`
2. Apply minimal fix
3. Run validation steps
4. Tag and release
5. Cherry-pick to `main` if applicable
