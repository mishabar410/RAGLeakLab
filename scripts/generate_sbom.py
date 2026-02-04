#!/usr/bin/env python3
"""Generate SBOM (Software Bill of Materials) in CycloneDX format.

Reads dependencies from uv.lock and pyproject.toml to produce a CycloneDX JSON SBOM.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def generate_sbom(output_path: Path | None = None) -> dict:
    """Generate SBOM using cyclonedx-py.

    Args:
        output_path: Optional path to write SBOM JSON. If None, returns dict only.

    Returns:
        SBOM as dictionary
    """
    # Use cyclonedx-py to generate SBOM from pyproject.toml
    # This reads the project metadata and dependencies
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyclonedx_py",
            "environment",
            "--format",
            "json",
            "--output-format",
            "json",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        # Try alternative: generate from requirements
        print(f"Warning: cyclonedx environment failed: {result.stderr}", file=sys.stderr)
        # Generate minimal SBOM manually
        sbom = _generate_minimal_sbom()
    else:
        sbom = json.loads(result.stdout)

    # Add metadata
    sbom.setdefault("metadata", {})
    sbom["metadata"]["timestamp"] = datetime.now(UTC).isoformat()
    sbom["metadata"]["tools"] = sbom["metadata"].get("tools", [])
    if not any(t.get("name") == "ragleaklab-sbom" for t in sbom["metadata"]["tools"]):
        sbom["metadata"]["tools"].append(
            {"name": "ragleaklab-sbom", "version": "1.0.0"}
        )

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(sbom, f, indent=2)
        print(f"✅ SBOM written to: {output_path}")

    return sbom


def _generate_minimal_sbom() -> dict:
    """Generate minimal SBOM from pyproject.toml."""
    from importlib.metadata import distributions

    components = []
    for dist in distributions():
        meta = dist.metadata
        components.append(
            {
                "type": "library",
                "name": meta.get("Name", "unknown"),
                "version": meta.get("Version", "0.0.0"),
                "purl": f"pkg:pypi/{meta.get('Name', 'unknown')}@{meta.get('Version', '0.0.0')}",
            }
        )

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.4",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(UTC).isoformat(),
            "component": {
                "type": "application",
                "name": "ragleaklab",
                "version": _get_project_version(),
            },
        },
        "components": components,
    }


def _get_project_version() -> str:
    """Get version from pyproject.toml."""
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
    if pyproject_path.exists():
        import tomllib

        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
            return data.get("project", {}).get("version", "0.0.0")
    return "0.0.0"


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate SBOM for RAGLeakLab")
    parser.add_argument(
        "--out",
        "-o",
        type=Path,
        default=Path("dist/sbom.json"),
        help="Output path for SBOM JSON (default: dist/sbom.json)",
    )
    args = parser.parse_args()

    generate_sbom(args.out)


if __name__ == "__main__":
    main()
