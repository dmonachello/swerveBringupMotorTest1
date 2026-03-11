from __future__ import annotations

"""
NAME
    can_profiles_dump.py - Helpers to emit profiles and config snapshots.

SYNOPSIS
    from can_profiles_dump import dump_seen_ids, dump_profile, dump_can_config

DESCRIPTION
    Serializes observed IDs into JSON artifacts for profile generation and
    reproducible configuration files.
"""

import json
import time
from typing import Dict, Iterable, List, Optional, Tuple

from can_frc_defs import PROFILE_MAP_RULES


def dump_seen_ids(
    path: str,
    profile: str,
    interface: str,
    channel: str,
    bitrate: int,
    seen_ids: list[int],
) -> None:
    """
    NAME
        dump_seen_ids - Write a snapshot of observed arbitration IDs.

    PARAMETERS
        path: Output JSON file path.
        profile: Active profile name.
        interface: CAN interface type.
        channel: CAN channel identifier.
        bitrate: CAN bitrate in bps.
        seen_ids: Sorted list of observed arbitration IDs.

    SIDE EFFECTS
        Writes JSON to disk.
    """
    now = time.time()
    payload = {
        "created": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
        "profile": profile,
        "interface": interface,
        "channel": channel,
        "bitrate": bitrate,
        "seen_ids_int": seen_ids,
        "seen_ids_hex": [hex(x) for x in seen_ids],
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception as exc:
        print(f"ERROR: Failed to write seen-IDs dump '{path}': {exc}")


def _build_profile_from_seen(
    seen_keys: Iterable[Tuple[int, int, int]],
    profile_name: str,
    include_unknown: bool,
) -> Dict[str, object]:
    """
    NAME
        _build_profile_from_seen - Generate a profile mapping from observed IDs.

    PARAMETERS
        seen_keys: Iterable of (mfg, type, id) tuples.
        profile_name: Name to embed in metadata.
        include_unknown: Whether to include unknown devices.

    RETURNS
        Profile dictionary compatible with bringup_profiles.json.
    """
    buckets: Dict[str, List[Dict[str, int]]] = {
        "neos": [],
        "flexes": [],
        "krakens": [],
        "falcons": [],
        "cancoders": [],
    }
    singletons: Dict[str, Optional[int]] = {
        "pdh": None,
        "pdp": None,
        "pigeon": None,
        "roborio": None,
    }
    unknown: List[Dict[str, int]] = []
    assumptions: List[str] = []

    for mfg, dtype, did in sorted(seen_keys):
        matched = False
        for rule in PROFILE_MAP_RULES:
            if "mfg" in rule and mfg != rule["mfg"]:
                continue
            if "type" in rule and dtype != rule["type"]:
                continue
            bucket = rule.get("bucket")
            singleton = rule.get("singleton")
            note = rule.get("note")
            if bucket:
                buckets.setdefault(bucket, []).append({"id": did})
                matched = True
            elif singleton:
                if singletons.get(singleton) is None:
                    singletons[singleton] = did
                    matched = True
                elif include_unknown:
                    unknown.append({"manufacturer": mfg, "device_type": dtype, "device_id": did})
                    matched = True
            if note and note not in assumptions:
                assumptions.append(note)
            if matched:
                break
        if not matched and include_unknown:
            unknown.append({"manufacturer": mfg, "device_type": dtype, "device_id": did})

    profile: Dict[str, object] = {
        "neos": buckets["neos"],
        "flexes": buckets["flexes"],
        "krakens": buckets["krakens"],
        "falcons": buckets["falcons"],
        "cancoders": buckets["cancoders"],
        "notes": {
            "generated_by": "can_nt_bridge.py",
            "profile_name": profile_name,
            "assumptions": assumptions,
        },
    }
    for key, value in singletons.items():
        if value is not None:
            profile[key] = {"id": value}
    if include_unknown and unknown:
        profile["unknown"] = unknown

    return profile


def dump_profile(
    path: str,
    profile_name: str,
    seen_keys: Iterable[Tuple[int, int, int]],
    include_unknown: bool,
) -> None:
    """
    NAME
        dump_profile - Write a bringup_profiles.json file from observations.

    PARAMETERS
        path: Output JSON file path.
        profile_name: Profile key to create in output.
        seen_keys: Observed (mfg, type, id) tuples.
        include_unknown: Whether to include unknown devices.

    SIDE EFFECTS
        Writes JSON to disk.
    """
    payload = {
        "default_profile": profile_name,
        "profiles": {
            profile_name: _build_profile_from_seen(seen_keys, profile_name, include_unknown),
        },
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception as exc:
        print(f"ERROR: Failed to write profile dump '{path}': {exc}")


def dump_can_config(path: str, args, devices: List[Dict[str, object]]) -> None:
    """
    NAME
        dump_can_config - Emit a can_nt_config.json-style snapshot.

    PARAMETERS
        path: Output JSON file path.
        args: Parsed CLI args for metadata.
        devices: Device list from the active profile.

    SIDE EFFECTS
        Writes JSON to disk.
    """
    payload = {
        "created": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())),
        "generated_from_profile": args.profile,
        "rio": args.rio,
        "interface": args.interface,
        "channel": args.channel,
        "bitrate": args.bitrate,
        "timeout": args.timeout,
        "publish_period": args.publish_period,
        "print_summary_period": args.print_summary_period,
        "auto_match": args.auto_match,
        "devices": devices,
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception as exc:
        print(f"ERROR: Failed to write CAN config '{path}': {exc}")
