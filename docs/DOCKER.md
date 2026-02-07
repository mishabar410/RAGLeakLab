# Docker

Run RAGLeakLab scans in a reproducible Docker container.

## Build

```bash
docker build -t ragleaklab:local .
```

## Run

Mount your `data/` and `out/` directories:

```bash
# Run a pack
docker run --rm \
  -v "$PWD/data:/work/data:ro" \
  -v "$PWD/out:/work/out" \
  ragleaklab:local run --pack basic --out out/basic

# Validate a config
docker run --rm \
  -v "$PWD:/work:ro" \
  ragleaklab:local config validate --path ragleaklab.yaml

# Show help
docker run --rm ragleaklab:local --help
```

## Docker Compose

A minimal `docker-compose.yml` is included for local development:

```bash
# Run with default (--help)
docker compose run --rm ragleaklab

# Run a scan
docker compose run --rm ragleaklab run --pack basic --out out/basic

# Start the mock leaky target
docker compose up mock-target -d

# Run against the mock target (from host)
docker run --rm --network host \
  -v "$PWD:/work" \
  ragleaklab:local run --config examples/fastapi_target/ragleaklab.yaml --out out/http
```

> [!NOTE]
> Docker Compose is **not** required for CI. Use the `Dockerfile` directly.

## Environment Variables

Pass secrets via `-e`:

```bash
docker run --rm \
  -e API_TOKEN=secret123 \
  -v "$PWD:/work" \
  ragleaklab:local run --config ragleaklab.yaml --out out/
```

## Smoke Test

```bash
bash scripts/docker_smoke.sh
```

This builds the image and verifies `ragleaklab --help` runs successfully.
