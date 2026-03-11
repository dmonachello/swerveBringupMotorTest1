from __future__ import annotations

"""
NAME
    can_profiles.py - Load and expose CAN device profiles.

SYNOPSIS
    from can_profiles import get_profile, list_profiles

DESCRIPTION
    Reads bringup_profiles.json from deploy resources and provides default
    device lists for the CAN diagnostics tool.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


DEFAULT_PROFILE_NAME = "robot"
PROFILE_FILE = Path(__file__).resolve().parents[1] / "src" / "main" / "deploy" / "bringup_profiles.json"


def _device(label: str, manufacturer: int, device_type: int, device_id: int, group: str) -> Dict[str, Any]:
    """
    NAME
        _device - Build a normalized device dictionary.
    """
    return {
        "label": label,
        "manufacturer": manufacturer,
        "device_type": device_type,
        "device_id": device_id,
        "group": group,
    }


def _load_profiles() -> Tuple[str, Dict[str, List[Dict[str, Any]]]]:
    """
    NAME
        _load_profiles - Load profiles from JSON with fallbacks.

    RETURNS
        (default_profile_name, profiles_map).
    """
    if not PROFILE_FILE.exists():
        return (_fallback_default(), _fallback_profiles())

    try:
        payload = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return (_fallback_default(), _fallback_profiles())

    default_profile = payload.get("default_profile") or DEFAULT_PROFILE_NAME
    raw_profiles = payload.get("profiles")
    if not isinstance(raw_profiles, dict) or not raw_profiles:
        return (_fallback_default(), _fallback_profiles())

    profiles: Dict[str, List[Dict[str, Any]]] = {}
    for name, raw in raw_profiles.items():
        if not isinstance(raw, dict):
            continue
        profiles[name] = _profile_devices(raw)

    if default_profile not in profiles:
        default_profile = DEFAULT_PROFILE_NAME

    if not profiles:
        return (_fallback_default(), _fallback_profiles())

    return (default_profile, profiles)


def _profile_devices(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    NAME
        _profile_devices - Convert a profile JSON section into device entries.
    """
    devices: List[Dict[str, Any]] = []

    for entry in raw.get("neos", []) or []:
        if not isinstance(entry, dict) or "id" not in entry:
            continue
        label = entry.get("label") or f"NEO {entry.get('id')}"
        device_id = int(entry.get("id"))
        devices.append(_device(label, 5, 2, device_id, "neos"))

    for entry in raw.get("neo550s", []) or []:
        if not isinstance(entry, dict) or "id" not in entry:
            continue
        label = entry.get("label") or f"NEO 550 {entry.get('id')}"
        device_id = int(entry.get("id"))
        devices.append(_device(label, 5, 2, device_id, "neo550s"))

    for entry in raw.get("flexes", []) or []:
        if not isinstance(entry, dict) or "id" not in entry:
            continue
        label = entry.get("label") or f"FLEX {entry.get('id')}"
        device_id = int(entry.get("id"))
        devices.append(_device(label, 5, 2, device_id, "flexes"))

    for entry in raw.get("krakens", []) or []:
        if not isinstance(entry, dict) or "id" not in entry:
            continue
        label = entry.get("label") or f"KRAKEN {entry.get('id')}"
        device_id = int(entry.get("id"))
        devices.append(_device(label, 4, 2, device_id, "krakens"))

    for entry in raw.get("falcons", []) or []:
        if not isinstance(entry, dict) or "id" not in entry:
            continue
        label = entry.get("label") or f"FALCON {entry.get('id')}"
        device_id = int(entry.get("id"))
        devices.append(_device(label, 4, 2, device_id, "falcons"))

    for entry in raw.get("cancoders", []) or []:
        if not isinstance(entry, dict) or "id" not in entry:
            continue
        label = entry.get("label") or f"CANCoder {entry.get('id')}"
        device_id = int(entry.get("id"))
        devices.append(_device(label, 4, 7, device_id, "cancoders"))

    for entry in raw.get("candles", []) or []:
        if not isinstance(entry, dict) or "id" not in entry:
            continue
        label = entry.get("label") or f"CANdle {entry.get('id')}"
        device_id = int(entry.get("id"))
        devices.append(_device(label, 4, 10, device_id, "candles"))

    pdh = raw.get("pdh")
    if isinstance(pdh, dict) and "id" in pdh:
        label = pdh.get("label") or "PDH"
        devices.append(_device(label, 5, 8, int(pdh.get("id")), "power"))

    pdp = raw.get("pdp")
    if isinstance(pdp, dict) and "id" in pdp:
        label = pdp.get("label") or "PDP"
        devices.append(_device(label, 4, 8, int(pdp.get("id")), "power"))

    pigeon = raw.get("pigeon")
    if isinstance(pigeon, dict) and "id" in pigeon:
        label = pigeon.get("label") or "Pigeon"
        devices.append(_device(label, 4, 4, int(pigeon.get("id")), "sensors"))

    roborio = raw.get("roborio")
    if isinstance(roborio, dict) and "id" in roborio:
        label = roborio.get("label") or "roboRIO"
        devices.append(_device(label, 1, 1, int(roborio.get("id")), "controller"))

    return devices


def _fallback_default() -> str:
    """
    NAME
        _fallback_default - Provide a default profile name.
    """
    return DEFAULT_PROFILE_NAME


def _fallback_profiles() -> Dict[str, List[Dict[str, Any]]]:
    """
    NAME
        _fallback_profiles - Provide fallback profiles when JSON is missing.
    """
    robot_devices: List[Dict[str, Any]] = [
        _device("FR NEO", 5, 2, 10, "neos"),
        _device("FL NEO", 5, 2, 1, "neos"),
        _device("BR NEO", 5, 2, 7, "neos"),
        _device("BL NEO", 5, 2, 4, "neos"),
        _device("FR KRAK", 4, 2, 11, "krakens"),
        _device("FL KRAK", 4, 2, 2, "krakens"),
        _device("BR KRAK", 4, 2, 8, "krakens"),
        _device("BL KRAK", 4, 2, 5, "krakens"),
        _device("FR CANC", 4, 7, 12, "cancoders"),
        _device("FL CANC", 4, 7, 3, "cancoders"),
        _device("BR CANC", 4, 7, 9, "cancoders"),
        _device("BL CANC", 4, 7, 6, "cancoders"),
        _device("PDH", 5, 8, 1, "power"),
        _device("Pigeon", 4, 4, 1, "sensors"),
    ]
    demo_devices: List[Dict[str, Any]] = [
        _device("NEO 22", 5, 2, 22, "neos"),
        _device("NEO 25", 5, 2, 25, "neos"),
        _device("NEO 10", 5, 2, 10, "neos"),
    ]
    return {
        "robot": robot_devices,
        "demo_club": demo_devices,
        "demo_home": [],
    }


DEFAULT_PROFILE, PROFILE_DEVICES = _load_profiles()


def get_default_profile() -> str:
    """
    NAME
        get_default_profile - Return the default profile name.
    """
    return DEFAULT_PROFILE


def list_profiles() -> List[str]:
    """
    NAME
        list_profiles - Return available profile names.
    """
    return list(PROFILE_DEVICES.keys())


def get_profile(profile: str) -> Tuple[List[Dict[str, Any]], Set[int]]:
    """
    NAME
        get_profile - Retrieve devices for a named profile.

    PARAMETERS
        profile: Profile name.

    RETURNS
        (device_list, expected_ids_set).

    ERRORS
        Raises ValueError when the profile is unknown.
    """
    if profile in PROFILE_DEVICES:
        return (list(PROFILE_DEVICES[profile]), set())
    raise ValueError(f"Unknown profile: {profile}. Available: {', '.join(PROFILE_DEVICES.keys())}")
