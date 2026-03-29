"""
NAME
    can_table_import.py - Convert a CAN ID table into a bringup profile.

SYNOPSIS
    python tools\\can_topology\\can_table_import.py --profile NAME --input table.txt --output profile.json

DESCRIPTION
    Parses a simple text table (tab or multi-space columns) describing
    subsystem, device name, and CAN ID. Produces a label-only
    bringup_system.json payload with placeholder CAN identity fields
    suitable for loading into the topology editor.
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from tools.common.cli_helpers import add_input_arg, add_output_arg
from tools.common.profile_constants import (
    INTERFACE_CAN,
    KEY_DATA_HASH,
    KEY_DATA_VERSION,
    KEY_DEFAULT_PROFILE,
    KEY_DEVICE_TYPE,
    KEY_DEVICES,
    KEY_ID,
    KEY_INTERFACE,
    KEY_LABEL,
    KEY_MANUFACTURER,
    KEY_PROFILE_DEVICES,
    KEY_PROFILES,
    KEY_SCHEMA_VERSION,
    KEY_TAGS,
    PROFILE_SCHEMA_VERSION,
)
from tools.common.profile_io import compute_profiles_hash
from tools.common.text_io import read_lines
from tools.common.time_utils import timestamp_version

UNKNOWN_CAN_FIELD = -1
MSG_DUP_LABEL = "Duplicate device label: {label}"

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


def build_payload(rows: List[TableRow], profile_name: str) -> Dict[str, object]:
    """
    NAME
        build_payload - Convert rows into a label-only profiles payload.
    """
    devices: List[Dict[str, object]] = []
    labels: List[str] = []
    seen: Dict[str, str] = {}
    for row in rows:
        label = _normalize_text(row.device)
        if not label:
            continue
        label_key = label.lower()
        if label_key in seen:
            raise ValueError(MSG_DUP_LABEL.format(label=label))
        seen[label_key] = label
        labels.append(label)
        entry: Dict[str, object] = {
            KEY_LABEL: label,
            KEY_INTERFACE: INTERFACE_CAN,
            KEY_ID: row.can_id,
            KEY_MANUFACTURER: UNKNOWN_CAN_FIELD,
            KEY_DEVICE_TYPE: UNKNOWN_CAN_FIELD,
        }
        tags = _device_tags(row.subsystem, row.device)
        if tags:
            entry[KEY_TAGS] = tags
        devices.append(entry)
    payload: Dict[str, object] = {
        KEY_SCHEMA_VERSION: PROFILE_SCHEMA_VERSION,
        KEY_DATA_VERSION: timestamp_version(),
        KEY_DEFAULT_PROFILE: profile_name,
        KEY_DEVICES: devices,
        KEY_PROFILES: {
            profile_name: {
                KEY_PROFILE_DEVICES: labels,
            },
        },
    }
    payload[KEY_DATA_HASH] = _compute_data_hash(payload)
    return payload


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
        return read_lines(Path(path))
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


def _compute_data_hash(payload: Dict[str, object]) -> str:
    """
    NAME
        _compute_data_hash - Compute a stable hash for profile payloads.
    """
    return compute_profiles_hash(payload)


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
    add_input_arg(
        parser,
        default=None,
        help_text="Path to table text (defaults to stdin).",
    )
    add_output_arg(
        parser,
        default=None,
        help_text="Write JSON to this path (defaults to stdout).",
    )
    parser.add_argument(
        "--warn-duplicates",
        action="store_true",
        help="Print duplicate CAN ID warnings to stderr.",
    )
    args = parser.parse_args(argv)

    rows = parse_table(_load_text(args.input))
    try:
        payload = build_payload(rows, args.profile)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    _write_json(args.output, payload)

    if args.warn_duplicates:
        dups = _detect_duplicates(rows)
        for can_id, items in sorted(dups.items()):
            names = ", ".join(f"{r.subsystem}:{r.device}" for r in items)
            print(f"Duplicate CAN ID {can_id}: {names}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
