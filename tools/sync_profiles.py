from __future__ import annotations

"""
NAME
    sync_profiles.py - Validate and rewrite the deploy-owned bringup_system.json.

SYNOPSIS
    python tools\\sync_profiles.py [--source PATH] [--dest PATH]

DESCRIPTION
    Validates the deploy-owned bringup system JSON, refreshes the version/hash
    fields, and rewrites the file in place.

PARAMETERS
    --source: Path to bringup_system.json (default: src/main/deploy/bringup_system.json).
    --dest: Path to deploy bringup_system.json (default: src/main/deploy/bringup_system.json).

SIDE EFFECTS
    Writes the deploy bringup_system.json file.

ERRORS
    Exits nonzero on missing source or copy failure.
"""

import argparse
from pathlib import Path

from tools.common.json_io import read_json, write_json
from tools.common.profile_constants import (
    KEY_DATA_HASH,
    KEY_DATA_VERSION,
    KEY_SCHEMA_VERSION,
    PROFILE_SCHEMA_VERSION,
)
from tools.common.profile_io import compute_profiles_hash, validate_profiles_schema
from tools.common.time_utils import timestamp_version

DEFAULT_SOURCE = str(Path("src") / "main" / "deploy" / "bringup_system.json")
DEFAULT_DEST = str(Path("src") / "main" / "deploy" / "bringup_system.json")

MSG_ERR_SOURCE_MISSING = "ERROR: source file not found: {path}"
MSG_ERR_READ = "ERROR: failed to read source JSON: {error}"
MSG_ERR_SCHEMA = "ERROR: source schema_version mismatch (expected {version})."
MSG_ERR_COPY = "ERROR: failed to copy profiles: {error}"
MSG_SYNCED = "Synced profiles to {path} (data_version={version})"

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync bringup_system.json into deploy.")
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE,
        help="Source bringup_system.json path",
    )
    parser.add_argument(
        "--dest",
        default=DEFAULT_DEST,
        help="Deploy bringup_system.json path",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    source = Path(args.source)
    dest = Path(args.dest)
    if not source.exists():
        print(MSG_ERR_SOURCE_MISSING.format(path=source))
        return 2
    try:
        payload = read_json(source)
    except Exception as exc:
        print(MSG_ERR_READ.format(error=exc))
        return 2
    if not isinstance(payload, dict):
        print(MSG_ERR_SCHEMA.format(version=PROFILE_SCHEMA_VERSION))
        return 2
    ok, _err = validate_profiles_schema(payload, PROFILE_SCHEMA_VERSION)
    if not ok:
        print(MSG_ERR_SCHEMA.format(version=PROFILE_SCHEMA_VERSION))
        return 2
    payload[KEY_DATA_VERSION] = timestamp_version()
    data_version = payload[KEY_DATA_VERSION]
    payload[KEY_DATA_HASH] = compute_profiles_hash(payload)
    payload[KEY_SCHEMA_VERSION] = PROFILE_SCHEMA_VERSION
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        write_json(source, payload)
        write_json(dest, payload)
    except Exception as exc:
        print(MSG_ERR_COPY.format(error=exc))
        return 2
    print(MSG_SYNCED.format(path=dest, version=data_version))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
