from __future__ import annotations

"""
NAME
    migrate_profiles.py - Migrate bringup_system.json to schema v3.

SYNOPSIS
    python tools\\migrate_profiles.py --source src\\main\\deploy\\bringup_system.json --dest src\\main\\deploy\\bringup_system.json

DESCRIPTION
    Normalizes bringup_system.json so device labels are unique within each
    profile, updates schema_version to 3, syncs diagram labels, and refreshes
    data_hash. Writes a JSON report with any renames performed.
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from tools.common.json_io import read_json, write_json
from tools.common.profile_io import compute_profiles_hash
from tools.common.time_utils import timestamp_version


BUCKET_CATEGORIES = [
    "neos",
    "neo550s",
    "flexes",
    "krakens",
    "falcons",
    "cancoders",
    "candles",
]
SINGLETON_CATEGORIES = ["pdh", "pdp", "pigeon", "roborio"]
GENERIC_CATEGORY = "devices"


def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    """
    NAME
        parse_args - Parse CLI arguments.
    """
    parser = argparse.ArgumentParser(description="Migrate bringup_system.json to schema v3.")
    parser.add_argument("--source", required=True, help="Source bringup_system.json path")
    parser.add_argument("--dest", required=True, help="Destination path for migrated JSON")
    parser.add_argument("--report", default="", help="Optional path for a JSON rename report")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write output files; only print summary.",
    )
    return parser.parse_args(argv)


def _disambiguate(label: str, entry: Dict[str, Any]) -> str:
    tags = entry.get("tags")
    if isinstance(tags, list):
        for tag in tags:
            if isinstance(tag, str) and tag.startswith("swerve-"):
                return f"{label} ({tag})"
    if "id" in entry:
        return f"{label} (id {entry['id']})"
    return f"{label} (dup)"


def _rewrite_profile(
    profile: Dict[str, Any],
    rename_report: List[Dict[str, str]],
) -> Dict[Tuple[str, int], str]:
    """
    NAME
        _rewrite_profile - Ensure unique labels and return a map for diagram updates.
    """
    label_map: Dict[Tuple[str, int], str] = {}
    seen: Dict[str, int] = {}

    def _set_label(category: str, entry: Dict[str, Any]) -> None:
        if "id" not in entry:
            return
        label = entry.get("label") or f"{category} {entry.get('id')}"
        base = str(label)
        key = base.lower()
        seen[key] = seen.get(key, 0) + 1
        new_label = base
        if seen[key] > 1:
            new_label = _disambiguate(base, entry)
            rename_report.append({"from": base, "to": new_label})
        entry["label"] = new_label
        label_map[(category, int(entry.get("id")))] = new_label

    for category in BUCKET_CATEGORIES:
        for entry in profile.get(category, []) or []:
            if isinstance(entry, dict):
                _set_label(category, entry)

    for category in SINGLETON_CATEGORIES:
        entry = profile.get(category)
        if isinstance(entry, dict):
            _set_label(category, entry)

    for entry in profile.get(GENERIC_CATEGORY, []) or []:
        if isinstance(entry, dict):
            _set_label(GENERIC_CATEGORY, entry)

    return label_map


def _rewrite_diagram(payload: Dict[str, Any], label_maps: Dict[str, Dict[Tuple[str, int], str]]) -> None:
    diagram = payload.get("diagram")
    if not isinstance(diagram, dict):
        return
    profiles = diagram.get("profiles")
    if not isinstance(profiles, dict):
        return
    for profile_name, diag in profiles.items():
        if not isinstance(diag, dict):
            continue
        nodes = diag.get("nodes") or []
        if not isinstance(nodes, list):
            continue
        mapping = label_maps.get(profile_name, {})
        for node in nodes:
            if not isinstance(node, dict):
                continue
            if node.get("nodeType") != "device":
                continue
            category = node.get("category")
            dev_id = node.get("id")
            if category is None or dev_id is None:
                continue
            new_label = mapping.get((str(category), int(dev_id)))
            if new_label:
                node["label"] = new_label


def migrate(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, str]]]:
    """
    NAME
        migrate - Perform schema v3 migration in memory.
    """
    profiles = payload.get("profiles")
    if not isinstance(profiles, dict):
        raise ValueError("payload missing profiles map")
    rename_report: List[Dict[str, str]] = []
    label_maps: Dict[str, Dict[Tuple[str, int], str]] = {}
    for name, profile in profiles.items():
        if not isinstance(profile, dict):
            continue
        label_maps[name] = _rewrite_profile(profile, rename_report)
    _rewrite_diagram(payload, label_maps)
    payload["schema_version"] = 3
    payload["data_version"] = timestamp_version()
    payload["data_hash"] = compute_profiles_hash(payload)
    return payload, rename_report


def main() -> int:
    """
    NAME
        main - CLI entry point.
    """
    args = parse_args()
    source = Path(args.source)
    dest = Path(args.dest)
    payload = read_json(source)
    migrated, report = migrate(payload)
    if args.dry_run:
        print(f"Dry run: {len(report)} labels renamed.")
        return 0
    write_json(dest, migrated, indent=2, trailing_newline=True)
    if args.report:
        report_path = Path(args.report)
        write_json(report_path, {"renames": report}, indent=2, trailing_newline=True)
    print(f"Wrote {dest}")
    if args.report:
        print(f"Wrote {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
