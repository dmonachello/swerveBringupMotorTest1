from __future__ import annotations

"""
NAME
    migrate_device_interface_key.py - Migrate bringup_system.json device key interface -> deviceInterface.

SYNOPSIS
    python -m tools.migrate_device_interface_key --path src/main/deploy/bringup_system.json

DESCRIPTION
    Updates device registry entries in bringup_system.json to use the canonical
    key deviceInterface instead of the legacy key interface.

    This is a file rewrite tool intended to clean up existing configs after the
    codebase begins reading deviceInterface with legacy fallback.

SIDE EFFECTS
    Writes the given JSON file in-place unless --no-write is provided.

ERRORS
    Exits nonzero on read/parse errors or invalid JSON structure.
"""

import argparse
from pathlib import Path
from typing import Any, Dict, List

from tools.common.json_io import read_json, write_json
from tools.common.profile_constants import (
    KEY_DEVICES,
    KEY_INTERFACE,
    KEY_INTERFACE_LEGACY,
)


ARG_PATH = "--path"
ARG_NO_WRITE = "--no-write"
ARG_KEEP_LEGACY = "--keep-legacy"

MSG_DESC = "Migrate bringup_system.json device key interface -> deviceInterface."
MSG_ERR_ROOT = "ERROR: root must be a JSON object."
MSG_ERR_DEVICES = "ERROR: root.devices must be a JSON list."
MSG_OK = "OK: migrated {migrated} device(s) in {path}"

EXIT_OK = 0
EXIT_ERROR = 2


def _build_parser() -> argparse.ArgumentParser:
    """
    NAME
        _build_parser - Build CLI argument parser.
    """

    parser = argparse.ArgumentParser(description=MSG_DESC)
    parser.add_argument(
        ARG_PATH,
        required=True,
        help="Path to bringup_system.json (canonical).",
    )
    parser.add_argument(
        ARG_NO_WRITE,
        action="store_true",
        help="Do not write; validate and report only.",
    )
    parser.add_argument(
        ARG_KEEP_LEGACY,
        action="store_true",
        help="Keep legacy 'interface' key alongside deviceInterface.",
    )
    return parser


def _migrate_devices(devices: List[object], keep_legacy: bool) -> int:
    """
    NAME
        _migrate_devices - Apply key migration to device registry entries.

    RETURNS
        Count of entries that were changed.
    """

    migrated = 0
    for entry in devices:
        if not isinstance(entry, dict):
            continue
        interface_legacy = entry.get(KEY_INTERFACE_LEGACY)
        interface_new = entry.get(KEY_INTERFACE)
        if interface_new is None and interface_legacy is not None:
            entry[KEY_INTERFACE] = interface_legacy
            migrated += 1
        if not keep_legacy and KEY_INTERFACE_LEGACY in entry:
            if entry.get(KEY_INTERFACE) is not None:
                entry.pop(KEY_INTERFACE_LEGACY, None)
    return migrated


def main(argv: List[str] | None = None) -> int:
    """
    NAME
        main - CLI entry point.
    """

    args = _build_parser().parse_args(argv)
    path = Path(getattr(args, "path"))
    try:
        root = read_json(path)
    except Exception as exc:
        print(f"ERROR: failed to read {path}: {exc}")
        return EXIT_ERROR
    if not isinstance(root, dict):
        print(MSG_ERR_ROOT)
        return EXIT_ERROR
    devices = root.get(KEY_DEVICES)
    if not isinstance(devices, list):
        print(MSG_ERR_DEVICES)
        return EXIT_ERROR
    migrated = _migrate_devices(devices, bool(getattr(args, "keep_legacy", False)))
    if not bool(getattr(args, "no_write", False)):
        try:
            write_json(path, root)
        except Exception as exc:
            print(f"ERROR: failed to write {path}: {exc}")
            return EXIT_ERROR
    print(MSG_OK.format(migrated=migrated, path=path))
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
