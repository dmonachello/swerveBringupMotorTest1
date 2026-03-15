"""
NAME
    can_table_import.py - Convert a CAN ID table into a bringup profile.

SYNOPSIS
    python tools\\can_topology\\can_table_import.py --profile NAME --input table.txt --output profile.json

DESCRIPTION
    Parses a simple text table (tab or multi-space columns) describing
    subsystem, device name, and CAN ID. Produces a first-pass
    bringup_profiles.json payload suitable for loading into the topology editor.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass
class TableRow:
    """
    NAME
        TableRow - Parsed row from a CAN ID table.

    DESCRIPTION
        Holds normalized subsystem, device, CAN ID, and optional source text.
    """

    subsystem: str
    device: str
    can_id: int
    source: str = ""


def _normalize_text(value: str) -> str:
    """
    NAME
        _normalize_text - Normalize freeform text for comparison.
    """
    return " ".join(value.strip().split())


def _slug_tag(value: str) -> str:
    """
    NAME
        _slug_tag - Convert text to a lowercase tag.
    """
    return _normalize_text(value).lower().replace(" ", "-")


def _split_columns(line: str) -> Optional[List[str]]:
    """
    NAME
        _split_columns - Split a table row into columns.

    DESCRIPTION
        Accepts tab-separated or two-or-more space-separated tables.
    """
    if "\t" in line:
        parts = [p.strip() for p in line.split("\t") if p.strip()]
    else:
        parts = [p.strip() for p in line.split("  ") if p.strip()]
    if len(parts) < 3:
        return None
    return parts


def parse_table(lines: Iterable[str]) -> List[TableRow]:
    """
    NAME
        parse_table - Parse a CAN ID table into structured rows.

    PARAMETERS
        lines - Iterable of input lines (text table).

    RETURNS
        List of TableRow entries.
    """
    rows: List[TableRow] = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        cols = _split_columns(line)
        if not cols:
            continue
        if cols[0].lower().startswith("subsystem") and any("can" in c.lower() for c in cols):
            continue
        subsystem = _normalize_text(cols[0])
        device = _normalize_text(cols[1])
        can_id_text = cols[2]
        try:
            can_id = int(can_id_text)
        except ValueError:
            continue
        source = _normalize_text(cols[3]) if len(cols) > 3 else ""
        rows.append(TableRow(subsystem=subsystem, device=device, can_id=can_id, source=source))
    return rows


def _device_tags(subsystem: str, device: str) -> List[str]:
    """
    NAME
        _device_tags - Build a default tag list for a device.
    """
    tags = {_slug_tag(subsystem)}
    lowered = device.lower()
    if "drive" in lowered:
        tags.add("drive")
    if "angle" in lowered or "azimuth" in lowered:
        tags.add("angle")
    if "encoder" in lowered or "cancoder" in lowered:
        tags.add("encoder")
    if "flywheel" in lowered:
        tags.add("flywheel")
    if "feeder" in lowered:
        tags.add("feeder")
    if "intake" in lowered:
        tags.add("intake")
    if "pivot" in lowered:
        tags.add("pivot")
    if "climb" in lowered:
        tags.add("climb")
    if "imu" in lowered or "gyro" in lowered:
        tags.add("imu")
    return sorted(tags)


def _classify_device(device: str) -> Tuple[str, Dict[str, str]]:
    """
    NAME
        _classify_device - Map a device name to a profile category.

    RETURNS
        Tuple of (category, extra_fields). The extra_fields contain
        vendor/type/motor when using the generic devices category.
    """
    lowered = device.lower()
    if "cancoder" in lowered:
        return "cancoders", {}
    if "candle" in lowered:
        return "candles", {}
    if "pigeon" in lowered or "imu" in lowered:
        return "pigeon", {}
    if "pdh" in lowered:
        return "pdh", {}
    if "pdp" in lowered:
        return "pdp", {}
    if "roborio" in lowered:
        return "roborio", {}
    if "kraken" in lowered:
        return "krakens", {"motor": "CTRE Kraken X60"}
    if "falcon" in lowered:
        return "falcons", {"motor": "CTRE Falcon 500"}
    if "neo 550" in lowered or "neo550" in lowered:
        return "neo550s", {"motor": "REV NEO 550"}
    if "vortex" in lowered or "sparkflex" in lowered or "spark flex" in lowered:
        return "flexes", {"motor": "REV NEO Vortex"}
    if "neo" in lowered or "sparkmax" in lowered or "spark max" in lowered:
        return "neos", {"motor": "REV NEO"}

    extra: Dict[str, str] = {"vendor": "Unknown", "type": "Miscellaneous"}
    if "motor" in lowered:
        extra["type"] = "MotorController"
    if "encoder" in lowered:
        extra["type"] = "Encoder"
    return "devices", extra


def build_profile(rows: List[TableRow]) -> Dict[str, List[Dict[str, object]]]:
    """
    NAME
        build_profile - Convert rows into a bringup profile structure.
    """
    profile: Dict[str, List[Dict[str, object]]] = {}
    singletons: Dict[str, Dict[str, object]] = {}
    for row in rows:
        category, extra = _classify_device(row.device)
        entry: Dict[str, object] = {
            "label": row.device,
            "id": row.can_id,
        }
        tags = _device_tags(row.subsystem, row.device)
        if tags:
            entry["tags"] = tags
        entry.update(extra)
        if category in {"pdh", "pdp", "pigeon", "roborio"}:
            singletons[category] = entry
            continue
        profile.setdefault(category, []).append(entry)
    profile.update(singletons)
    return profile


def _detect_duplicates(rows: List[TableRow]) -> Dict[int, List[TableRow]]:
    """
    NAME
        _detect_duplicates - Identify duplicate CAN IDs.
    """
    seen: Dict[int, List[TableRow]] = {}
    for row in rows:
        seen.setdefault(row.can_id, []).append(row)
    return {can_id: items for can_id, items in seen.items() if len(items) > 1}


def _load_text(path: Optional[str]) -> List[str]:
    """
    NAME
        _load_text - Load input lines from a path or stdin.
    """
    if path:
        return Path(path).read_text(encoding="utf-8").splitlines()
    return sys.stdin.read().splitlines()


def _write_json(path: Optional[str], payload: Dict[str, object]) -> None:
    """
    NAME
        _write_json - Write JSON to a file or stdout.
    """
    data = json.dumps(payload, indent=2, sort_keys=False)
    if path:
        Path(path).write_text(data + "\n", encoding="utf-8")
    else:
        print(data)


def main(argv: Optional[List[str]] = None) -> int:
    """
    NAME
        main - CLI entrypoint for converting tables to profiles.

    PARAMETERS
        argv - Optional argument list (defaults to sys.argv).

    RETURNS
        Process exit code.
    """
    parser = argparse.ArgumentParser(
        description="Convert a CAN ID table into a bringup profile JSON payload."
    )
    parser.add_argument(
        "--profile",
        required=True,
        help="Profile name to emit under 'profiles'.",
    )
    parser.add_argument(
        "--input",
        help="Path to table text (defaults to stdin).",
    )
    parser.add_argument(
        "--output",
        help="Write JSON to this path (defaults to stdout).",
    )
    parser.add_argument(
        "--warn-duplicates",
        action="store_true",
        help="Print duplicate CAN ID warnings to stderr.",
    )
    args = parser.parse_args(argv)

    rows = parse_table(_load_text(args.input))
    profile = build_profile(rows)
    payload = {
        "default_profile": args.profile,
        "profiles": {args.profile: profile},
    }
    _write_json(args.output, payload)

    if args.warn_duplicates:
        dups = _detect_duplicates(rows)
        for can_id, items in sorted(dups.items()):
            names = ", ".join(f"{r.subsystem}:{r.device}" for r in items)
            print(f"Duplicate CAN ID {can_id}: {names}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
