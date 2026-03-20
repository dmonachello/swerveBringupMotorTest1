from __future__ import annotations

"""
NAME
    sync_profiles.py - Copy canonical bringup_profiles.json into deploy.

SYNOPSIS
    python tools\\sync_profiles.py [--source PATH] [--dest PATH]

DESCRIPTION
    Copies the canonical bringup profiles JSON (stored under data/) into
    the roboRIO deploy folder so the Java code can load it on the robot.

PARAMETERS
    --source: Path to canonical bringup_profiles.json (default: data/bringup_profiles.json).
    --dest: Path to deploy bringup_profiles.json (default: src/main/deploy/bringup_profiles.json).

SIDE EFFECTS
    Writes the deploy bringup_profiles.json file.

ERRORS
    Exits nonzero on missing source or copy failure.
"""

import argparse
import hashlib
import json
import time
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync bringup_profiles.json into deploy.")
    parser.add_argument(
        "--source",
        default=str(Path("data") / "bringup_profiles.json"),
        help="Canonical bringup_profiles.json path",
    )
    parser.add_argument(
        "--dest",
        default=str(Path("src") / "main" / "deploy" / "bringup_profiles.json"),
        help="Deploy bringup_profiles.json path",
    )
    return parser.parse_args()


def _compute_data_hash(payload: dict) -> str:
    """
    NAME
        _compute_data_hash - Compute a stable hash for profile payloads.
    """
    normalized = dict(payload)
    normalized["data_hash"] = ""
    blob = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def main() -> int:
    args = _parse_args()
    source = Path(args.source)
    dest = Path(args.dest)
    if not source.exists():
        print(f"ERROR: source file not found: {source}")
        return 2
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: failed to read source JSON: {exc}")
        return 2
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        print("ERROR: source schema_version mismatch (expected 1).")
        return 2
    payload["data_version"] = time.strftime("%Y-%m-%d_%H%M%S", time.localtime())
    data_version = payload["data_version"]
    payload["data_hash"] = _compute_data_hash(payload)
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except Exception as exc:
        print(f"ERROR: failed to copy profiles: {exc}")
        return 2
    print(f"Synced profiles to {dest} (data_version={data_version})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
