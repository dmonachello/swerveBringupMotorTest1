from __future__ import annotations

"""
NAME
    main.py - CLI entry point for the documentation maintenance pipeline.
"""

import argparse
import json
from pathlib import Path

from .artifacts import write_docs_maintenance_artifacts
from .pipeline import run_docs_inventory_pipeline


ARG_REPO_ROOT = "--repo-root"
ARG_PRETTY = "--pretty"
ARG_OUTPUT = "--output"
ARG_WRITE_ARTIFACTS = "--write-artifacts"
DEFAULT_JSON_INDENT = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inventory and classify Markdown documentation in the repo tree."
    )
    parser.add_argument(
        ARG_REPO_ROOT,
        default=".",
        help="Repository root to scan.",
    )
    parser.add_argument(
        ARG_PRETTY,
        action="store_true",
        help="Pretty-print JSON output.",
    )
    parser.add_argument(
        ARG_OUTPUT,
        default="",
        help="Optional file path to write the JSON report.",
    )
    parser.add_argument(
        ARG_WRITE_ARTIFACTS,
        action="store_true",
        help="Write generated index, glossary, hub, and health-report artifacts into docs/.",
    )
    return parser


def main() -> int:
    """
    NAME
        main - Run the initial docs-maintenance pipeline and print one JSON report.
    """
    parser = build_parser()
    args = parser.parse_args()
    root = Path(getattr(args, ARG_REPO_ROOT.lstrip("-").replace("-", "_"))).resolve()
    report = run_docs_inventory_pipeline(root)
    write_artifacts = bool(getattr(args, ARG_WRITE_ARTIFACTS.lstrip("-").replace("-", "_")))
    if write_artifacts:
        report["writtenArtifacts"] = write_docs_maintenance_artifacts(root, report)
    indent = DEFAULT_JSON_INDENT if bool(getattr(args, ARG_PRETTY.lstrip("-").replace("-", "_"))) else None
    rendered = json.dumps(report, indent=indent, sort_keys=True)
    output_path = str(getattr(args, ARG_OUTPUT.lstrip("-").replace("-", "_")) or "").strip()
    if output_path:
        target = Path(output_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
