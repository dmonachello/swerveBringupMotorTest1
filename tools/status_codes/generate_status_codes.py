"""
NAME
    generate_status_codes.py - Validate and emit generated status code catalog.

SYNOPSIS
    python tools/status_codes/generate_status_codes.py

DESCRIPTION
    Validates the status code catalog source and writes a generated JSON file
    used by both Python and Java loaders.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable

KEY_SEVERITIES = "severities"
KEY_FACILITIES = "facilities"
KEY_MESSAGES = "messages"
KEY_VERSION = "version"
KEY_GENERATED_FROM = "generatedFrom"
KEY_GENERATED_NOTICE = "_generatedNotice"
KEY_DATA = "data"

DEFAULT_VERSION = "1"
GENERATED_NOTICE_TEXT = "AUTO-GENERATED FILE. Do not modify; changes will be lost on regeneration."

FILE_SOURCE = "status_codes_source.json"
FILE_GENERATED = "status_codes.generated.json"

ERROR_PREFIX = "ERROR: "


def _ensure_non_empty(mapping: Dict[str, object], label: str) -> None:
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError(f"{label} must be a non-empty object")


def _ensure_unique(values: Iterable[int], label: str) -> None:
    seen = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate value in {label}: {value}")
        seen.add(value)


def _validate_facilities(facilities: Dict[str, int]) -> None:
    _ensure_non_empty(facilities, KEY_FACILITIES)
    for name, value in facilities.items():
        if not isinstance(value, int):
            raise ValueError(f"Facility {name} must be int")
        if value <= 0:
            raise ValueError(f"Facility {name} must be > 0")
    _ensure_unique(facilities.values(), KEY_FACILITIES)


def _validate_messages(messages: Dict[str, Dict[str, int]], facilities: Dict[str, int]) -> None:
    _ensure_non_empty(messages, KEY_MESSAGES)
    for facility, msg_map in messages.items():
        if facility not in facilities:
            raise ValueError(f"Unknown facility in messages: {facility}")
        _ensure_non_empty(msg_map, f"messages.{facility}")
        for name, value in msg_map.items():
            if not isinstance(value, int):
                raise ValueError(f"Message {facility}.{name} must be int")
            if value <= 0:
                raise ValueError(f"Message {facility}.{name} must be > 0")
        _ensure_unique(msg_map.values(), f"messages.{facility}")


def _validate_severities(severities: Dict[str, int]) -> None:
    _ensure_non_empty(severities, KEY_SEVERITIES)
    for name, value in severities.items():
        if not isinstance(value, int):
            raise ValueError(f"Severity {name} must be int")
        if value < 0:
            raise ValueError(f"Severity {name} must be >= 0")
    _ensure_unique(severities.values(), KEY_SEVERITIES)


def generate(catalog: Dict[str, object]) -> Dict[str, object]:
    severities = catalog.get(KEY_SEVERITIES)
    facilities = catalog.get(KEY_FACILITIES)
    messages = catalog.get(KEY_MESSAGES)
    if not isinstance(severities, dict):
        raise ValueError("severities missing or invalid")
    if not isinstance(facilities, dict):
        raise ValueError("facilities missing or invalid")
    if not isinstance(messages, dict):
        raise ValueError("messages missing or invalid")
    _validate_severities(severities)
    _validate_facilities(facilities)
    _validate_messages(messages, facilities)
    return {
        KEY_VERSION: DEFAULT_VERSION,
        KEY_GENERATED_FROM: FILE_SOURCE,
        KEY_GENERATED_NOTICE: GENERATED_NOTICE_TEXT,
        KEY_DATA: catalog,
    }


def main() -> int:
    root = Path(__file__).resolve().parent
    source_path = root / FILE_SOURCE
    generated_path = root / FILE_GENERATED
    catalog = json.loads(source_path.read_text(encoding="utf-8"))
    payload = generate(catalog)
    generated_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover
        print(ERROR_PREFIX + str(exc))
        raise SystemExit(1)
