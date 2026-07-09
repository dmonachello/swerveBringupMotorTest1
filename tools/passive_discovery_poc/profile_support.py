from __future__ import annotations

"""
NAME
    profile_support.py - Bringup profile loading for passive discovery.

DESCRIPTION
    Loads bringup_system.json, resolves the active profile, and extracts expected
    CAN devices for comparison against passive observations.
"""

import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from tools.common.profile_constants import (
    INTERFACE_CAN,
    KEY_DEFAULT_PROFILE,
    KEY_DEVICES,
    KEY_ID,
    KEY_INTERFACE,
    KEY_LABEL,
    KEY_MANUFACTURER,
    KEY_MODEL,
    KEY_PROFILE_DEVICES,
    KEY_PROFILES,
    KEY_DEVICE_TYPE,
)
from tools.common.profile_io import default_profiles_schema_version, validate_profiles_schema
from tools.passive_discovery_poc.constants import BUS_UNKNOWN, ENCODING_UTF8, PROFILE_NODE_UNKNOWN
from tools.passive_discovery_poc.metadata import normalize_device_type
from tools.passive_discovery_poc.models import DeviceIdentity


def load_profile_expectations(profile_path: str, profile_name: str) -> Tuple[str, Dict[Tuple[int, int, int], Dict[str, object]]]:
    """
    NAME
        load_profile_expectations - Load expected CAN devices from bringup profile JSON.

    RETURNS
        Tuple of resolved profile name and mapping keyed by
        (manufacturer, deviceType, deviceId).

    ERRORS
        Raises ValueError when the profile file is invalid or the target profile
        cannot be resolved.
    """
    payload = _load_payload(Path(profile_path))
    ok, err = validate_profiles_schema(payload, default_profiles_schema_version())
    if not ok:
        raise ValueError(err)
    resolved_profile = _resolve_profile_name(payload=payload, explicit_name=profile_name)
    profiles = payload.get(KEY_PROFILES)
    if not isinstance(profiles, dict):
        raise ValueError("profiles mapping missing from bringup profile payload")
    selected = profiles.get(resolved_profile)
    if not isinstance(selected, dict):
        raise ValueError(f"profile not found: {resolved_profile}")
    profile_devices = selected.get(KEY_PROFILE_DEVICES)
    if not isinstance(profile_devices, list):
        raise ValueError(f"profile devices missing for profile: {resolved_profile}")
    device_rows = payload.get(KEY_DEVICES)
    if not isinstance(device_rows, list):
        raise ValueError("root devices list missing from bringup profile payload")
    by_label = _index_devices_by_label(device_rows)
    expected: Dict[Tuple[int, int, int], Dict[str, object]] = {}
    for label in profile_devices:
        if not isinstance(label, str):
            continue
        entry = by_label.get(label)
        if not isinstance(entry, dict):
            continue
        if str(entry.get(KEY_INTERFACE, "")).strip() != INTERFACE_CAN:
            continue
        manufacturer = entry.get(KEY_MANUFACTURER)
        device_type = entry.get(KEY_DEVICE_TYPE)
        device_id = entry.get(KEY_ID)
        if not isinstance(manufacturer, int) or not isinstance(device_type, int) or not isinstance(device_id, int):
            continue
        device_type = normalize_device_type(manufacturer, device_type)
        key = (manufacturer, device_type, device_id)
        expected[key] = {
            KEY_LABEL: str(entry.get(KEY_LABEL, "")).strip(),
            KEY_MODEL: str(entry.get(KEY_MODEL, "")).strip(),
            "profileNode": str(entry.get(KEY_LABEL, PROFILE_NODE_UNKNOWN)).strip(),
            "bus": BUS_UNKNOWN,
            "manufacturer": manufacturer,
            "deviceType": device_type,
            "deviceId": device_id,
        }
    return (resolved_profile, expected)


def expected_identities(expected_rows: Dict[Tuple[int, int, int], Dict[str, object]]) -> Iterable[DeviceIdentity]:
    """
    NAME
        expected_identities - Convert expected-row mapping to canonical identities.
    """
    for manufacturer, device_type, device_id in expected_rows.keys():
        yield DeviceIdentity(
            manufacturer=manufacturer,
            device_type=device_type,
            device_id=device_id,
            bus=BUS_UNKNOWN,
            profile_node=str(expected_rows[(manufacturer, device_type, device_id)].get("profileNode", PROFILE_NODE_UNKNOWN)),
        )


def _load_payload(path: Path) -> Dict[str, object]:
    """
    NAME
        _load_payload - Read and validate a profile root JSON object.
    """
    if not path.exists():
        raise ValueError(f"profile file not found: {path}")
    with path.open("r", encoding=ENCODING_UTF8) as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("bringup profile root must be a JSON object")
    return payload


def _resolve_profile_name(payload: Dict[str, object], explicit_name: str) -> str:
    """
    NAME
        _resolve_profile_name - Choose the active profile name.
    """
    if explicit_name.strip():
        return explicit_name.strip()
    default_profile = payload.get(KEY_DEFAULT_PROFILE)
    if isinstance(default_profile, str) and default_profile.strip():
        return default_profile.strip()
    profiles = payload.get(KEY_PROFILES)
    if isinstance(profiles, dict) and profiles:
        first_key = next(iter(profiles.keys()))
        return str(first_key).strip()
    raise ValueError("unable to resolve active profile")


def _index_devices_by_label(rows: List[object]) -> Dict[str, Dict[str, object]]:
    """
    NAME
        _index_devices_by_label - Build a label-index for device rows.
    """
    result: Dict[str, Dict[str, object]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        label = row.get(KEY_LABEL)
        if isinstance(label, str) and label.strip():
            result[label.strip()] = row
    return result
