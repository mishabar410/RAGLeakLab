#!/usr/bin/env bash
# CI Smoke Test - Reproduces GitHub Actions CI locally
#
# Usage: ./scripts/ci_smoke.sh
#
# This script runs the same checks as the CI pipeline to ensure
# local development matches CI behavior exactly.
# See docs/CI_PARITY.md for details.

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

step() {
    echo -e "${YELLOW}==> $1${NC}"
}

success() {
    echo -e "${GREEN}✓ $1${NC}"
}

skip() {
    echo -e "${BLUE}SKIP $1${NC}"
}

fail() {
    echo -e "${RED}✗ $1${NC}"
    exit 1
}

# Ensure we're in the project root
cd "$(dirname "$0")/.."

echo "========================================"
echo "  RAGLeakLab CI Smoke Test"
echo "========================================"
echo ""

# Step 1: Sync dependencies (frozen = use lockfile exactly, all-extras for dev tools)
step "Installing dependencies (frozen)..."
uv sync --frozen --all-extras || fail "Dependency sync failed"
success "Dependencies installed"

# Step 2: Format check
step "Checking formatting..."
uv run ruff format --check . || fail "Format check failed"
success "Formatting OK"

# Step 3: Lint
step "Running ruff check..."
uv run ruff check . || fail "Linting failed"
success "Linting passed"

# Step 4: Tests (excluding slow)
step "Running tests (excluding slow)..."
uv run pytest -q -m "not slow" || fail "Tests failed"
success "Tests passed"

# Step 5: Asset validation
step "Validating assets..."
if uv run python -m ragleaklab assets validate --path . 2>/dev/null; then
    success "Assets valid"
else
    # Check if command exists
    if uv run python -m ragleaklab assets validate --help >/dev/null 2>&1; then
        fail "Asset validation failed"
    else
        skip "assets validate (command not available)"
    fi
fi

# Step 6: Security audit (basic pack using --attacks)
step "Running security audit (basic pack)..."
rm -rf out/
uv run python -m ragleaklab run \
    --corpus data/corpus_private_canary \
    --attacks data/attacks \
    --out out/ || fail "Security audit failed"
success "Security audit completed"

# Step 7: Regression check against v1 baseline
step "Checking regression against v1 baseline..."
uv run python -m ragleaklab diff \
    --baseline baselines/v1/report.json \
    --current out/report.json || fail "Regression check failed"
success "Baseline regression passed"

# Step 8: Semantic pack
step "Running semantic pack..."
uv run python -m ragleaklab run \
    --corpus data/corpus_private_canary \
    --pack semantic-basic \
    --out out/semantic/ || fail "Semantic pack failed"
success "Semantic pack completed"

# Step 9: Semantic regression check
step "Checking semantic regression..."
uv run python -m ragleaklab diff \
    --baseline baselines/semantic_v1/report.json \
    --current out/semantic/report.json || fail "Semantic regression failed"
success "Semantic baseline passed"

# Step 10: Crossdoc pack (if pack and baseline exist)
if [ -d "data/packs/crossdoc_v0" ] && [ -f "baselines/crossdoc_v0/report.json" ]; then
    step "Running crossdoc pack..."
    uv run python -m ragleaklab run \
        --corpus data/corpus_crossdoc_v0 \
        --pack crossdoc-basic \
        --out out/crossdoc/ || fail "Crossdoc pack failed"
    success "Crossdoc pack completed"

    step "Checking crossdoc regression..."
    uv run python -m ragleaklab diff \
        --baseline baselines/crossdoc_v0/report.json \
        --current out/crossdoc/report.json || fail "Crossdoc regression failed"
    success "Crossdoc baseline passed"
else
    skip "crossdoc pack (pack or baseline not found)"
fi

# Step 11: Relevance hijack poisoning pack (if pack and baseline exist)
if [ -d "data/packs/poisoning_v1/relevance_hijack" ] && [ -f "baselines/poisoning_v1/report.json" ]; then
    step "Running relevance hijack poisoning pack..."
    uv run python -m ragleaklab run \
        --corpus data/packs/poisoning_v1/relevance_hijack/corpus \
        --poisoning-pack relevance-hijack \
        --out out/relevance_hijack/ || fail "Relevance hijack pack failed"
    success "Relevance hijack pack completed"

    step "Checking relevance hijack regression..."
    uv run python -m ragleaklab diff \
        --baseline baselines/poisoning_v1/report.json \
        --current out/relevance_hijack/report.json || fail "Relevance hijack regression failed"
    success "Relevance hijack baseline passed"
else
    skip "relevance hijack pack (pack or baseline not found)"
fi

# Step 12: Claim corruption poisoning pack (if pack and baseline exist)
if [ -d "data/packs/poisoning_v1/claim_corruption" ] && [ -f "baselines/poisoning_v1/claim_corruption_report.json" ]; then
    step "Running claim corruption poisoning pack..."
    uv run python -m ragleaklab run \
        --corpus data/packs/poisoning_v1/claim_corruption/corpus \
        --poisoning-pack claim-corruption \
        --out out/claim_corruption/ || fail "Claim corruption pack failed"
    success "Claim corruption pack completed"

    step "Checking claim corruption regression..."
    uv run python -m ragleaklab diff \
        --baseline baselines/poisoning_v1/claim_corruption_report.json \
        --current out/claim_corruption/report.json || fail "Claim corruption regression failed"
    success "Claim corruption baseline passed"
else
    skip "claim corruption pack (pack or baseline not found)"
fi

# Step 14: Delta ingestion gate smoke test (if patch fixture exists)
if [ -d "data/patches/example_poison_doc" ]; then
    step "Running delta gate smoke test..."
    uv run python -m ragleaklab delta run \
        --pack canary-basic \
        --base-corpus data/corpus_private_canary \
        --patch data/patches/example_poison_doc \
        --out out/delta_smoke/ 2>/dev/null && {
        success "Delta gate smoke passed"
    } || {
        # Delta gate may fail (by design) if new findings detected
        if [ -f "out/delta_smoke/delta_report.json" ]; then
            success "Delta gate smoke completed (with findings)"
        else
            fail "Delta gate smoke failed to run"
        fi
    }
else
    skip "delta gate smoke (patch fixture not found)"
fi

# Note: sentinel-takeover-safe pack runs in nightly CI only (slower rule-based checks)

# Step 13: Determinism verification
step "Running determinism check..."
if uv run python -m ragleaklab verify determinism --help >/dev/null 2>&1; then
    # Use canary-basic pack for determinism check
    uv run python -m ragleaklab verify determinism \
        --pack canary-basic \
        --runs 2 \
        --out out/determinism/ || fail "Determinism check failed"
    success "Determinism verified"
else
    skip "determinism check (command not available)"
fi

# Cleanup
rm -rf out/

echo ""
echo "========================================"
echo -e "${GREEN}  CI smoke OK${NC}"
echo "========================================"
