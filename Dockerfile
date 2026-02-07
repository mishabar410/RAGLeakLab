# ── build stage ──────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Install uv (same method as CI)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install production deps only (no dev deps, no editable install yet)
RUN uv sync --frozen --no-dev --no-install-project

# Copy project source
COPY . .

# Install the project itself
RUN uv sync --frozen --no-dev


# ── runtime stage ────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /work

# Copy the virtualenv and project from builder
COPY --from=builder /app /app

# Put the venv on PATH
ENV PATH="/app/.venv/bin:$PATH"

# Default entrypoint is the CLI
ENTRYPOINT ["ragleaklab"]
CMD ["--help"]
