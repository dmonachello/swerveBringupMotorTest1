from __future__ import annotations

"""
NAME
    can_profiles_dump.py - Helpers to emit profiles and config snapshots.

SYNOPSIS
    from tools.can_nt.can_profiles_dump import dump_seen_ids, dump_profile, dump_can_config

DESCRIPTION
    Serializes observed IDs into JSON artifacts for profile generation and
    reproducible configuration files.
"""

import json
import time
from typing import Dict, Iterable, List, Optional, Tuple

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
    PROFILE_SCHEMA_VERSION,
)
from tools.common.profile_io import compute_profiles_hash
from tools.common.time_utils import timestamp_human, timestamp_version
from .can_frc_defs import PROFILE_MAP_RULES

KEY_GROUP = "group"
KEY_PREFER_STATUS = "prefer_status"
KEY_CREATED = "created"
KEY_PROFILE = "profile"
KEY_CHANNEL = "channel"
KEY_BITRATE = "bitrate"
KEY_GENERATED = "generated"
KEY_SCHEMA_VERSION_CAN_CONFIG = "schema_version"
KEY_DEVICES_CAN_CONFIG = "devices"
KEY_SEEN_LABELS = "seen_labels"

UNKNOWN_PREFIX = "Device"
UNKNOWN_LABEL_TEMPLATE = "Unknown {mfg}-{dtype}-{did}"

BUCKET_NEOS = "neos"
BUCKET_NEO550S = "neo550s"
BUCKET_FLEXES = "flexes"
BUCKET_KRAKENS = "krakens"
BUCKET_FALCONS = "falcons"
BUCKET_CANCODERS = "cancoders"
BUCKET_CANDLES = "candles"

SINGLETON_PDH = "pdh"
SINGLETON_PDP = "pdp"
SINGLETON_PIGEON = "pigeon"
SINGLETON_ROBORIO = "roborio"

PREFIX_NEOS = "NEO"
PREFIX_NEO550S = "NEO 550"
PREFIX_FLEXES = "FLEX"
PREFIX_KRAKENS = "KRAKEN"
PREFIX_FALCONS = "FALCON"
PREFIX_CANCODERS = "CANCoder"
PREFIX_CANDLES = "CANdle"
PREFIX_PDH = "PDH"
PREFIX_PDP = "PDP"
PREFIX_PIGEON = "Pigeon"
PREFIX_ROBORIO = "roboRIO"

LABEL_PREFIX_BY_BUCKET = {
    BUCKET_NEOS: PREFIX_NEOS,
    BUCKET_NEO550S: PREFIX_NEO550S,
    BUCKET_FLEXES: PREFIX_FLEXES,
    BUCKET_KRAKENS: PREFIX_KRAKENS,
    BUCKET_FALCONS: PREFIX_FALCONS,
    BUCKET_CANCODERS: PREFIX_CANCODERS,
    BUCKET_CANDLES: PREFIX_CANDLES,
}

LABEL_PREFIX_BY_SINGLETON = {
    SINGLETON_PDH: PREFIX_PDH,
    SINGLETON_PDP: PREFIX_PDP,
    SINGLETON_PIGEON: PREFIX_PIGEON,
    SINGLETON_ROBORIO: PREFIX_ROBORIO,
}



def _compute_data_hash(payload: Dict[str, object]) -> str:
    """
    NAME
        _compute_data_hash - Compute a stable hash for profile payloads.
    """
    return compute_profiles_hash(payload)



def dump_seen_ids(
    path: str,
    profile: str,
    interface: str,
    channel: str,
    bitrate: int,
    seen_labels: list[str],
) -> None:
    """
    NAME
        dump_seen_ids - Write a snapshot of observed device labels.

    PARAMETERS
        path: Output JSON file path.
        profile: Active profile name.
        interface: CAN interface type.
        channel: CAN channel identifier.
        bitrate: CAN bitrate in bps.
        seen_labels: Sorted list of observed device labels.

    SIDE EFFECTS
        Writes JSON to disk.
    """
    now = time.time()
    payload = {
        KEY_CREATED: timestamp_human(now),
        KEY_PROFILE: profile,
        KEY_INTERFACE: interface,
        KEY_CHANNEL: channel,
        KEY_BITRATE: bitrate,
        KEY_SEEN_LABELS: seen_labels,
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception as exc:
        print(f"ERROR: Failed to write seen-IDs dump '{path}': {exc}")



def _label_from_bucket(bucket: str, device_id: int) -> str:
    prefix = LABEL_PREFIX_BY_BUCKET.get(bucket, UNKNOWN_PREFIX)
    return f"{prefix} {device_id}"



def _label_from_singleton(singleton: str) -> str:
    return LABEL_PREFIX_BY_SINGLETON.get(singleton, UNKNOWN_PREFIX)



def _build_profile_from_seen(
    seen_keys: Iterable[Tuple[int, int, int]],
    profile_name: str,
    include_unknown: bool,
) -> Tuple[List[Dict[str, object]], List[str]]:
    """
    NAME
        _build_profile_from_seen - Generate devices and labels from observed IDs.

    PARAMETERS
        seen_keys: Iterable of (mfg, type, id) tuples.
        profile_name: Name to embed in metadata.
        include_unknown: Whether to include unknown devices.

    RETURNS
        Tuple of (devices_registry, profile_labels).
    """
    devices: List[Dict[str, object]] = []
    labels: List[str] = []
    seen_labels: set[str] = set()
    assumptions: List[str] = []

    def _add_device(label: str, mfg: int, dtype: int, did: int) -> None:
        if label in seen_labels:
            return
        seen_labels.add(label)
        devices.append(
            {
                KEY_LABEL: label,
                KEY_INTERFACE: INTERFACE_CAN,
                KEY_MANUFACTURER: int(mfg),
                KEY_DEVICE_TYPE: int(dtype),
                KEY_ID: int(did),
            }
        )
        labels.append(label)

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
                label = _label_from_bucket(bucket, did)
                _add_device(label, mfg, dtype, did)
                matched = True
            elif singleton:
                label = _label_from_singleton(singleton)
                _add_device(label, mfg, dtype, did)
                matched = True
            if note and note not in assumptions:
                assumptions.append(note)
            if matched:
                break
        if not matched and include_unknown:
            label = UNKNOWN_LABEL_TEMPLATE.format(mfg=mfg, dtype=dtype, did=did)
            _add_device(label, mfg, dtype, did)

    return devices, labels



def dump_profile(
    path: str,
    profile_name: str,
    seen_keys: Iterable[Tuple[int, int, int]],
    include_unknown: bool,
) -> None:
    """
    NAME
        dump_profile - Write a bringup_system.json file from observations.

    PARAMETERS
        path: Output JSON file path.
        profile_name: Profile key to create in output.
        seen_keys: Observed (mfg, type, id) tuples.
        include_unknown: Whether to include unknown devices.

    SIDE EFFECTS
        Writes JSON to disk.
    """
    devices, labels = _build_profile_from_seen(seen_keys, profile_name, include_unknown)
    payload = {
        KEY_SCHEMA_VERSION: PROFILE_SCHEMA_VERSION,
        KEY_DATA_VERSION: timestamp_version(),
        KEY_DEFAULT_PROFILE: profile_name,
        KEY_DEVICES: devices,
        KEY_PROFILES: {
            profile_name: {
                KEY_PROFILE_DEVICES: labels,
            }
        },
    }
    payload[KEY_DATA_HASH] = _compute_data_hash(payload)
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
    sanitized_devices: List[Dict[str, object]] = []
    for spec in devices:
        label = str(spec.get(KEY_LABEL, "")).strip()
        if not label:
            continue
        entry: Dict[str, object] = {
            KEY_LABEL: label,
        }
        group = spec.get(KEY_GROUP)
        if isinstance(group, str) and group:
            entry[KEY_GROUP] = group
        prefer_status = spec.get(KEY_PREFER_STATUS)
        if isinstance(prefer_status, bool):
            entry[KEY_PREFER_STATUS] = prefer_status
        sanitized_devices.append(entry)

    payload = {
        KEY_SCHEMA_VERSION_CAN_CONFIG: 1,
        KEY_GENERATED: timestamp_human(time.time()),
        KEY_INTERFACE: args.interface,
        KEY_CHANNEL: args.channel,
        KEY_BITRATE: args.bitrate,
        KEY_DEVICES_CAN_CONFIG: sanitized_devices,
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception as exc:
        print(f"ERROR: Failed to write config dump '{path}': {exc}")
