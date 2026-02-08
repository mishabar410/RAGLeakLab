"""External results publishing and validation.

Provides a safe, redacted format for publishing benchmark results
from runs against third-party RAG systems.  The schema strips all
secrets, raw claims, and environment details that could leak
private information.

Key safety guarantees:
- All string fields are run through ``core.redact``
- A dedicated ``scan_secrets`` pass rejects any file that still
  contains patterns matching emails, canary tokens, API keys, etc.
- Bundle hash is verified against the canonical bundle.yaml
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

from ragleaklab import __version__
from ragleaklab.core.redact import redact

__all__ = [
    "ExternalPackMetrics",
    "ExternalResult",
    "ExternalResultsSummary",
    "SecretLeakError",
    "build_external_result",
    "validate_external_result",
]

# ── Schema version ──────────────────────────────────────────────────
EXTERNAL_SCHEMA_VERSION = "1.0.0"

# ── Secret-scanning patterns (stricter than redaction) ──────────────
_SECRET_PATTERNS: list[re.Pattern[str]] = [
    # Emails
    re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    # Canary tokens
    re.compile(r"CANARY_[a-fA-F0-9]{16,}"),
    # SECRET_xxx
    re.compile(r"SECRET_\w+"),
    # Bearer / Basic auth
    re.compile(r"Bearer\s+[A-Za-z0-9\-_.~+/]+=*", re.IGNORECASE),
    re.compile(r"Basic\s+[A-Za-z0-9+/]+=*", re.IGNORECASE),
    # API keys (stripe-style)
    re.compile(r"(?:sk|pk)_(?:live|test)_[a-zA-Z0-9]+"),
    # AWS keys
    re.compile(r"AKIA[0-9A-Z]{16}"),
    # Generic token/password assignments
    re.compile(
        r"(?:token|password|secret|credential|auth)[=:]\s*['\"]?[^\s'\"]{8,}['\"]?",
        re.IGNORECASE,
    ),
]


class SecretLeakError(Exception):
    """Raised when secrets are detected in data intended for publication."""

    def __init__(self, findings: list[str]) -> None:
        self.findings = findings
        msg = "Secrets detected in external result — refusing to write.\n" + "\n".join(
            f"  • {f}" for f in findings
        )
        super().__init__(msg)


# ── Pydantic models ─────────────────────────────────────────────────


class ExternalPackMetrics(BaseModel):
    """Per-pack aggregate metrics (rates + counts only)."""

    pack_name: str
    category: str
    status: str
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    pass_rate: float = 0.0
    fail_rate: float = 0.0


class ExternalResultsSummary(BaseModel):
    """Aggregate metrics across all packs."""

    total_packs: int = 0
    passed_packs: int = 0
    failed_packs: int = 0
    risk_score: float = 0.0
    pack_results: list[ExternalPackMetrics] = Field(default_factory=list)


class ExternalReproduction(BaseModel):
    """Reproduction hints (redacted, no secrets)."""

    config_snippet: str = ""
    command: str = ""


class BundleReference(BaseModel):
    """Identifies the benchmark bundle used."""

    name: str
    version: str
    hash: str = Field(description="SHA-256 of bundle.yaml")


class ExternalResult(BaseModel):
    """Top-level schema for a published external result."""

    external_schema_version: str = Field(
        default=EXTERNAL_SCHEMA_VERSION,
        description="Version of the external results format",
    )
    system_name: str = Field(description="Human-readable name of the tested system")
    system_type: Literal["oss", "commercial", "internal"] = Field(
        description="Category of the system"
    )
    integration_type: Literal["inprocess", "http", "other"] = Field(
        description="How RAGLeakLab connected to the system"
    )
    ragleaklab_version: str = Field(description="RAGLeakLab version used")
    bundle: BundleReference = Field(description="Bundle reference")
    results_summary: ExternalResultsSummary = Field(description="Aggregate benchmark metrics")
    notes: str = Field(default="", description="Optional markdown notes")
    redaction_applied: bool = Field(
        default=True,
        description="Must be true — confirms secrets were scrubbed",
    )
    reproduction: ExternalReproduction = Field(
        default_factory=ExternalReproduction,
        description="Safe reproduction instructions",
    )
    generated_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="ISO timestamp of generation",
    )


# ── Secret scanning ─────────────────────────────────────────────────


def scan_secrets(data: Any) -> list[str]:
    """Walk a JSON-serialisable structure and return secret findings.

    Returns a list of human-readable descriptions of secrets found.
    An empty list means the data is clean.
    """
    findings: list[str] = []
    _scan_recursive(data, "$", findings)
    return findings


def _scan_recursive(obj: Any, path: str, findings: list[str]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            _scan_recursive(value, f"{path}.{key}", findings)
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            _scan_recursive(item, f"{path}[{idx}]", findings)
    elif isinstance(obj, str):
        for pattern in _SECRET_PATTERNS:
            match = pattern.search(obj)
            if match:
                # Don't include the actual secret in the finding!
                findings.append(
                    f"Secret pattern matched at {path}: /{pattern.pattern}/ (value hidden)"
                )
                break  # one finding per field is enough


# ── Hash helper ──────────────────────────────────────────────────────


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


# ── Builder ──────────────────────────────────────────────────────────


def build_external_result(
    bench_dir: Path,
    *,
    system_name: str,
    system_type: Literal["oss", "commercial", "internal"] = "oss",
    integration_type: Literal["inprocess", "http", "other"] = "inprocess",
    notes: str = "",
    config_snippet: str = "",
    command: str = "",
    bundle_path: Path | None = None,
) -> ExternalResult:
    """Build an external result from a bench output directory.

    Args:
        bench_dir: Directory containing ``bench_summary.json``.
        system_name: Name of the tested system.
        system_type: Type of the system.
        integration_type: How RAGLeakLab was integrated.
        notes: Optional markdown notes.
        config_snippet: Redacted config snippet.
        command: Safe reproduction command.
        bundle_path: Path to the bundle.yaml used.

    Returns:
        Validated ExternalResult ready for serialisation.

    Raises:
        FileNotFoundError: If required files are missing.
        ValueError: If bundle hash doesn't match.
        SecretLeakError: If secrets remain after redaction.
    """
    summary_path = bench_dir / "bench_summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(
            f"bench_summary.json not found in {bench_dir}. Run 'ragleaklab bench bundle' first."
        )

    with open(summary_path) as f:
        summary = json.load(f)

    # Resolve bundle path
    if bundle_path is None:
        # Default location
        project_root = Path(__file__).parent.parent.parent.parent
        bundle_path = project_root / "benchmarks" / "ragleakbench_v1" / "bundle.yaml"
    if not bundle_path.exists():
        raise FileNotFoundError(f"Bundle not found: {bundle_path}")

    with open(bundle_path) as f:
        bundle_data = yaml.safe_load(f) or {}

    # Validate bundle name matches
    if summary.get("bundle_name") != bundle_data.get("name"):
        raise ValueError(
            f"Bundle name mismatch: summary says '{summary.get('bundle_name')}' "
            f"but bundle.yaml says '{bundle_data.get('name')}'"
        )

    bundle_hash = _hash_file(bundle_path)

    # Build pack results (redacted — only rates and counts)
    pack_results = []
    for pr in summary.get("pack_results", []):
        pack_results.append(
            ExternalPackMetrics(
                pack_name=redact(pr.get("pack_name", "")),
                category=redact(pr.get("category", "default")),
                status=pr.get("status", "error"),
                total_cases=pr.get("total_cases", 0),
                passed_cases=pr.get("passed_cases", 0),
                failed_cases=pr.get("failed_cases", 0),
                pass_rate=pr.get("pass_rate", 0.0),
                fail_rate=pr.get("fail_rate", 0.0),
            )
        )

    results_summary = ExternalResultsSummary(
        total_packs=summary.get("total_packs", 0),
        passed_packs=summary.get("passed_packs", 0),
        failed_packs=summary.get("failed_packs", 0),
        risk_score=summary.get("risk_score", 0.0),
        pack_results=pack_results,
    )

    # Redact user-supplied text
    result = ExternalResult(
        system_name=redact(system_name),
        system_type=system_type,
        integration_type=integration_type,
        ragleaklab_version=__version__,
        bundle=BundleReference(
            name=bundle_data["name"],
            version=bundle_data.get("version", "0.0.0"),
            hash=bundle_hash,
        ),
        results_summary=results_summary,
        notes=redact(notes),
        redaction_applied=True,
        reproduction=ExternalReproduction(
            config_snippet=redact(config_snippet),
            command=redact(command),
        ),
    )

    # Final safety gate: scan serialised data for remaining secrets
    data = json.loads(result.model_dump_json())
    secrets = scan_secrets(data)
    if secrets:
        raise SecretLeakError(secrets)

    return result


# ── Validator ────────────────────────────────────────────────────────


def validate_external_result(
    path: Path,
    *,
    bundle_path: Path | None = None,
) -> ExternalResult:
    """Parse and validate an external result JSON file.

    Checks:
    1. File parses as valid JSON
    2. Conforms to ExternalResult schema
    3. ``redaction_applied`` is True
    4. No secrets remain in any string field
    5. Bundle hash matches (if bundle_path given)

    Args:
        path: Path to external result JSON.
        bundle_path: Optional bundle.yaml for hash verification.

    Returns:
        Validated ExternalResult.

    Raises:
        FileNotFoundError: If file doesn't exist.
        pydantic.ValidationError: If schema is invalid.
        ValueError: If redaction flag is False or hash mismatch.
        SecretLeakError: If secrets are detected.
    """
    if not path.exists():
        raise FileNotFoundError(f"External result not found: {path}")

    with open(path) as f:
        data = json.load(f)

    result = ExternalResult.model_validate(data)

    # Enforce redaction flag
    if not result.redaction_applied:
        raise ValueError(
            "External result has redaction_applied=false — all published results must be redacted."
        )

    # Scan for residual secrets
    secrets = scan_secrets(data)
    if secrets:
        raise SecretLeakError(secrets)

    # Optional bundle hash check
    if bundle_path is not None:
        if not bundle_path.exists():
            raise FileNotFoundError(f"Bundle not found: {bundle_path}")
        expected_hash = _hash_file(bundle_path)
        if result.bundle.hash != expected_hash:
            raise ValueError(
                f"Bundle hash mismatch: result says '{result.bundle.hash}' "
                f"but bundle.yaml hashes to '{expected_hash}'"
            )

    return result
