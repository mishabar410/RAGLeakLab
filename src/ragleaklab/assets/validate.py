"""Asset manifest validation utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ragleaklab.assets.hash import compute_tree_hash
from ragleaklab.assets.validator import (
    load_attacks_manifest,
    load_corpus_manifest,
    load_pack_manifest,
)


@dataclass
class ValidationError:
    """A single validation error."""

    path: Path
    message: str
    severity: str = "error"  # error, warning


@dataclass
class ValidationResult:
    """Result of validating assets."""

    passed: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)
    manifests_found: int = 0
    manifests_valid: int = 0


def validate_corpus_manifest(manifest_path: Path) -> list[ValidationError]:
    """Validate a corpus manifest file."""
    errors: list[ValidationError] = []

    try:
        manifest = load_corpus_manifest(manifest_path)
    except FileNotFoundError:
        errors.append(ValidationError(manifest_path, "Manifest file not found"))
        return errors
    except (ValueError, TypeError, KeyError) as e:
        errors.append(ValidationError(manifest_path, f"Invalid manifest: {e}"))
        return errors

    # Validate hash matches
    base_dir = manifest_path.parent
    try:
        actual_hash = compute_tree_hash(base_dir, exclude_manifest=True)
        if manifest.hash != actual_hash:
            errors.append(
                ValidationError(
                    manifest_path,
                    f"Hash mismatch: manifest={manifest.hash[:16]}... actual={actual_hash[:16]}...",
                )
            )
    except OSError as e:
        errors.append(ValidationError(manifest_path, f"Cannot compute hash: {e}"))

    return errors


def validate_attacks_manifest(manifest_path: Path) -> list[ValidationError]:
    """Validate an attacks manifest file."""
    errors: list[ValidationError] = []

    try:
        manifest = load_attacks_manifest(manifest_path)
    except FileNotFoundError:
        errors.append(ValidationError(manifest_path, "Manifest file not found"))
        return errors
    except (ValueError, TypeError, KeyError) as e:
        errors.append(ValidationError(manifest_path, f"Invalid manifest: {e}"))
        return errors

    # Validate hash matches
    base_dir = manifest_path.parent
    try:
        actual_hash = compute_tree_hash(base_dir, exclude_manifest=True)
        if manifest.hash != actual_hash:
            errors.append(
                ValidationError(
                    manifest_path,
                    f"Hash mismatch: manifest={manifest.hash[:16]}... actual={actual_hash[:16]}...",
                )
            )
    except OSError as e:
        errors.append(ValidationError(manifest_path, f"Cannot compute hash: {e}"))

    return errors


def validate_pack_manifest(
    manifest_path: Path, all_manifests: dict[str, Path]
) -> list[ValidationError]:
    """Validate a pack manifest file.

    Supports both regular attack pack manifests and poisoning pack manifests.

    Args:
        manifest_path: Path to pack manifest.
        all_manifests: Dict mapping ref names to their manifest paths for reference resolution.
    """
    errors: list[ValidationError] = []

    # Determine if this is a poisoning pack manifest
    is_poisoning = "poisoning" in str(manifest_path)

    try:
        if is_poisoning:
            # Load as poisoning pack manifest
            from ragleaklab.poisoning.packs.schema import PoisoningPackManifest

            with manifest_path.open() as f:
                import yaml

                data = yaml.safe_load(f)
            manifest = PoisoningPackManifest.model_validate(data)
        else:
            manifest = load_pack_manifest(manifest_path)
    except FileNotFoundError:
        errors.append(ValidationError(manifest_path, "Manifest file not found"))
        return errors
    except (ValueError, TypeError, KeyError) as e:
        errors.append(ValidationError(manifest_path, f"Invalid manifest: {e}"))
        return errors

    # Note: Reference validation is currently schema-only.
    # Future versions may validate that referenced assets exist.

    # Validate expected_report_fields reference valid schema fields
    if manifest.expected_report_fields:
        valid_fields = {
            "aggregates.canary",
            "aggregates.verbatim",
            "aggregates.membership",
            "aggregates.semantic",
            "aggregates.crossdoc",
            "aggregates.crossdoc_leakage_rate",
            "aggregates.total_cases",
            "aggregates.canary_extracted",
            "aggregates.canary_count",
            "aggregates.verbatim_leakage_rate",
            "aggregates.membership_confidence",
            "overall_pass",
            # Integrity fields from poisoning packs
            "integrity.integrity_summary.total_findings",
            "integrity.integrity_summary.high_severity",
            "integrity.integrity_summary.medium_severity",
            "integrity.integrity_summary.low_severity",
            "integrity.integrity_summary.retrieval_poisoned",
            "integrity.integrity_summary.claim_poisoned",
            "integrity.integrity_summary.sentinel_triggered",
            "integrity.integrity_summary.acl_violated",
        }
        for field_ref in manifest.expected_report_fields:
            if field_ref not in valid_fields:
                errors.append(
                    ValidationError(
                        manifest_path,
                        f"Unknown report field: {field_ref}",
                        severity="warning",
                    )
                )

    return errors


def validate_assets(base_path: Path) -> ValidationResult:
    """Validate all manifests under a directory.

    Args:
        base_path: Root directory to scan for manifests.

    Returns:
        ValidationResult with all errors and warnings.
    """
    errors: list[ValidationError] = []
    warnings: list[ValidationError] = []
    manifests_found = 0
    manifests_valid = 0
    all_manifests: dict[str, Path] = {}

    # Find all manifests
    corpus_manifests = list(base_path.rglob("corpus.yaml"))
    attacks_manifests = list(base_path.rglob("attacks.yaml"))
    pack_manifests = list(base_path.rglob("*.pack.yaml"))

    manifests_found = len(corpus_manifests) + len(attacks_manifests) + len(pack_manifests)

    # Validate corpus manifests
    for path in corpus_manifests:
        errs = validate_corpus_manifest(path)
        for e in errs:
            if e.severity == "warning":
                warnings.append(e)
            else:
                errors.append(e)
        if not any(e.severity == "error" for e in errs):
            manifests_valid += 1

    # Validate attacks manifests
    for path in attacks_manifests:
        errs = validate_attacks_manifest(path)
        for e in errs:
            if e.severity == "warning":
                warnings.append(e)
            else:
                errors.append(e)
        if not any(e.severity == "error" for e in errs):
            manifests_valid += 1

    # Validate pack manifests
    for path in pack_manifests:
        errs = validate_pack_manifest(path, all_manifests)
        for e in errs:
            if e.severity == "warning":
                warnings.append(e)
            else:
                errors.append(e)
        if not any(e.severity == "error" for e in errs):
            manifests_valid += 1

    return ValidationResult(
        passed=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        manifests_found=manifests_found,
        manifests_valid=manifests_valid,
    )
