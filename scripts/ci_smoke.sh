#!/usr/bin/env bash
# CI Smoke Test - Reproduces GitHub Actions CI locally
#
# Usage: ./scripts/ci_smoke.sh
#
# This script runs the same checks as the CI pipeline to ensure
# local development matches CI behavior exactly.

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

step() {
    echo -e "${YELLOW}==> $1${NC}"
}

success() {
    echo -e "${GREEN}✓ $1${NC}"
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

# Step 1: Sync dependencies
step "Installing dependencies..."
uv sync --all-extras || fail "Dependency sync failed"
success "Dependencies installed"

# Step 2: Lint
step "Running ruff check..."
uv run ruff check . || fail "Linting failed"
success "Linting passed"

# Step 3: Format check
step "Checking formatting..."
uv run ruff format --check . || fail "Format check failed"
success "Formatting OK"

# Step 4: Tests (excluding slow)
step "Running tests (excluding slow)..."
uv run pytest -q -m "not slow" || fail "Tests failed"
success "Tests passed"

# Step 5: Asset validation
step "Validating assets..."
uv run python -m ragleaklab assets validate --path . || fail "Asset validation failed"
success "Assets valid"

# Step 6: Security audit (basic pack)
step "Running security audit (basic pack)..."
rm -rf out/
uv run python -m ragleaklab run \
    --corpus data/corpus_private_canary \
    --attacks data/attacks \
    --out out/ || fail "Security audit failed"
success "Security audit completed"

# Step 7: Regression check
step "Checking regression against baseline..."
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

# Cleanup
rm -rf out/

echo ""
echo "========================================"
echo -e "${GREEN}  All CI checks passed!${NC}"
echo "========================================"
