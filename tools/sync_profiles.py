from __future__ import annotations

"""
NAME
    sync_profiles.py - Copy canonical bringup_system.json into deploy.

SYNOPSIS
    python tools\\sync_profiles.py [--source PATH] [--dest PATH]

DESCRIPTION
    Copies the canonical bringup system JSON (stored under data/) into
    the roboRIO deploy folder so the Java code can load it on the robot.

PARAMETERS
    --source: Path to canonical bringup_system.json (default: data/bringup_system.json).
    --dest: Path to deploy bringup_system.json (default: src/main/deploy/bringup_system.json).

SIDE EFFECTS
    Writes the deploy bringup_system.json file.

ERRORS
    Exits nonzero on missing source or copy failure.
"""

import argparse
from pathlib import Path

from tools.common.json_io import read_json, write_json
from tools.common.profile_io import compute_profiles_hash, validate_profiles_schema
from tools.common.time_utils import timestamp_version

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync bringup_system.json into deploy.")
    parser.add_argument(
        "--source",
        default=str(Path("data") / "bringup_system.json"),
        help="Canonical bringup_system.json path",
    )
    parser.add_argument(
        "--dest",
        default=str(Path("src") / "main" / "deploy" / "bringup_system.json"),
        help="Deploy bringup_system.json path",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    source = Path(args.source)
    dest = Path(args.dest)
    if not source.exists():
        print(f"ERROR: source file not found: {source}")
        return 2
    try:
        payload = read_json(source)
    except Exception as exc:
        print(f"ERROR: failed to read source JSON: {exc}")
        return 2
    if not isinstance(payload, dict):
        print("ERROR: source schema_version mismatch (expected 3).")
        return 2
    ok, _err = validate_profiles_schema(payload, 3)
    if not ok:
        print("ERROR: source schema_version mismatch (expected 3).")
        return 2
    payload["data_version"] = timestamp_version()
    data_version = payload["data_version"]
    payload["data_hash"] = compute_profiles_hash(payload)
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        write_json(source, payload)
        write_json(dest, payload)
    except Exception as exc:
        print(f"ERROR: failed to copy profiles: {exc}")
        return 2
    print(f"Synced profiles to {dest} (data_version={data_version})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
