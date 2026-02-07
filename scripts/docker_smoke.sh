#!/usr/bin/env bash
# Docker smoke test — build image and verify CLI starts.
# NOT run in PR CI (no Docker in CI runners by default).
set -euo pipefail

IMAGE="ragleaklab:smoke-$$"

echo "==> Building Docker image: ${IMAGE}"
docker build -t "${IMAGE}" .

echo "==> Running: ragleaklab --help"
docker run --rm "${IMAGE}" --help

echo "==> Running: ragleaklab config validate --help"
docker run --rm "${IMAGE}" config validate --help

echo "==> Cleaning up image"
docker rmi "${IMAGE}" > /dev/null

echo ""
echo "========================================"
echo "  Docker smoke OK"
echo "========================================"
