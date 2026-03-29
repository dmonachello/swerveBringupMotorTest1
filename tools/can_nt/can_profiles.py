from __future__ import annotations

"""
NAME
    can_profiles.py - Load and expose CAN device profiles.

SYNOPSIS
    from tools.can_nt.can_profiles import get_profile, list_profiles

DESCRIPTION
    Reads bringup_system.json from the central data repository (deploy fallback)
    and provides CAN device entries for the diagnostics tool.
"""

from typing import Any, Dict, List, Set, Tuple

from tools.common.json_io import read_json
from tools.common.paths import (
    profiles_canonical_path,
    profiles_deploy_path,
)
from tools.common.profile_constants import (
    INTERFACE_CAN,
    KEY_ATTACHMENTS,
    KEY_DATA_HASH,
    KEY_DATA_VERSION,
    KEY_DEFAULT_PROFILE,
    KEY_DEVICE_TYPE,
    KEY_DEVICES,
    KEY_ID,
    KEY_INTERFACE,
    KEY_LABEL,
    KEY_MANUFACTURER,
    KEY_MODEL,
    KEY_PROFILES,
    KEY_PROFILE_DEVICES,
    KEY_SCHEMA_VERSION,
    KEY_TAGS,
    KEY_TERMINATOR,
    KEY_TYPE,
    PROFILE_SCHEMA_VERSION,
)
from tools.common.profile_io import compute_profiles_hash
from .can_frc_defs import uses_status_presence

DEFAULT_PROFILE_NAME = "robot"
CANONICAL_PROFILE_FILE = profiles_canonical_path()
DEPLOY_PROFILE_FILE = profiles_deploy_path()
_LOAD_ERROR: str = ""
_DATA_VERSION: str = ""
_DATA_HASH: str = ""

KEY_PREFER_STATUS = "prefer_status"
EMPTY_STRING = ""

MSG_LOAD_MISSING = "Profiles file not found at {path}"
MSG_LOAD_PARSE = "Failed to parse profiles JSON at {path}"
MSG_SCHEMA_MISMATCH = "Profile schema_version mismatch: expected {version}, got {found}"
MSG_DATA_VERSION_MISSING = "Profile data_version missing or empty"
MSG_DATA_HASH_MISSING = "Profile data_hash missing or empty"
MSG_DATA_HASH_MISMATCH = "Profile data_hash mismatch (run tools/sync_profiles.py)"
MSG_PROFILES_MISSING = "Profiles payload missing 'profiles' map"
MSG_DEVICES_MISSING = "Profiles payload missing 'devices' list"
MSG_DEVICE_LABEL_MISSING = "Device entry missing label"
MSG_DEVICE_LABEL_DUP = "Duplicate device label in registry: {label}"
MSG_PROFILE_DEVICES_MISSING = "Profile '{profile}' missing devices list"
MSG_PROFILE_DEVICE_UNKNOWN = "Profile '{profile}' references unknown device label: {label}"
MSG_PROFILES_EMPTY = "Profiles map is empty"
MSG_DEVICE_LIST_EMPTY = "Devices registry is empty"
MSG_UNKNOWN_PROFILE = "Unknown profile: {profile}. Available: {profiles}"


def _load_profiles() -> Tuple[str, Dict[str, List[Dict[str, Any]]]]:
    """
    NAME
        _load_profiles - Load profiles from JSON with deploy fallback.

    RETURNS
        (default_profile_name, profiles_map).
    """
    global _LOAD_ERROR
    global _DATA_VERSION
    global _DATA_HASH
    _LOAD_ERROR = EMPTY_STRING
    _DATA_VERSION = EMPTY_STRING
    _DATA_HASH = EMPTY_STRING
    path = CANONICAL_PROFILE_FILE if CANONICAL_PROFILE_FILE.exists() else DEPLOY_PROFILE_FILE
    if not path.exists():
        _LOAD_ERROR = MSG_LOAD_MISSING.format(path=path)
        return (_fallback_default(), _fallback_profiles())

    try:
        payload = read_json(path)
    except Exception:
        _LOAD_ERROR = MSG_LOAD_PARSE.format(path=path)
        return (_fallback_default(), _fallback_profiles())

    schema_version = payload.get(KEY_SCHEMA_VERSION)
    if schema_version != PROFILE_SCHEMA_VERSION:
        _LOAD_ERROR = MSG_SCHEMA_MISMATCH.format(
            version=PROFILE_SCHEMA_VERSION,
            found=schema_version,
        )
        return (_fallback_default(), _fallback_profiles())

    data_version = payload.get(KEY_DATA_VERSION)
    if not isinstance(data_version, str) or not data_version.strip():
        _LOAD_ERROR = MSG_DATA_VERSION_MISSING
        return (_fallback_default(), _fallback_profiles())
    _DATA_VERSION = data_version.strip()

    data_hash = payload.get(KEY_DATA_HASH)
    if not isinstance(data_hash, str) or not data_hash.strip():
        _LOAD_ERROR = MSG_DATA_HASH_MISSING
        return (_fallback_default(), _fallback_profiles())
    computed_hash = compute_profiles_hash(payload)
    if data_hash != computed_hash:
        _LOAD_ERROR = MSG_DATA_HASH_MISMATCH
        return (_fallback_default(), _fallback_profiles())
    _DATA_HASH = data_hash

    devices_raw = payload.get(KEY_DEVICES)
    if not isinstance(devices_raw, list) or not devices_raw:
        _LOAD_ERROR = MSG_DEVICES_MISSING
        return (_fallback_default(), _fallback_profiles())

    device_registry: Dict[str, Dict[str, Any]] = {}
    for entry in devices_raw:
        if not isinstance(entry, dict):
            continue
        label = str(entry.get(KEY_LABEL, EMPTY_STRING)).strip()
        if not label:
            _LOAD_ERROR = MSG_DEVICE_LABEL_MISSING
            return (_fallback_default(), _fallback_profiles())
        key = label.lower()
        if key in device_registry:
            _LOAD_ERROR = MSG_DEVICE_LABEL_DUP.format(label=label)
            return (_fallback_default(), _fallback_profiles())
        device_registry[key] = entry

    if not device_registry:
        _LOAD_ERROR = MSG_DEVICE_LIST_EMPTY
        return (_fallback_default(), _fallback_profiles())

    raw_profiles = payload.get(KEY_PROFILES)
    if not isinstance(raw_profiles, dict) or not raw_profiles:
        _LOAD_ERROR = MSG_PROFILES_MISSING
        return (_fallback_default(), _fallback_profiles())

    profiles: Dict[str, List[Dict[str, Any]]] = {}
    for name, raw in raw_profiles.items():
        if not isinstance(raw, dict):
            continue
        devices = raw.get(KEY_PROFILE_DEVICES)
        if not isinstance(devices, list):
            _LOAD_ERROR = MSG_PROFILE_DEVICES_MISSING.format(profile=name)
            return (_fallback_default(), _fallback_profiles())
        resolved: List[Dict[str, Any]] = []
        for label in devices:
            if not isinstance(label, str):
                continue
            key = label.strip().lower()
            entry = device_registry.get(key)
            if entry is None:
                _LOAD_ERROR = MSG_PROFILE_DEVICE_UNKNOWN.format(profile=name, label=label)
                return (_fallback_default(), _fallback_profiles())
            device_copy = dict(entry)
            if device_copy.get(KEY_INTERFACE) == INTERFACE_CAN:
                manufacturer = device_copy.get(KEY_MANUFACTURER)
                device_type = device_copy.get(KEY_DEVICE_TYPE)
                if isinstance(manufacturer, int) and isinstance(device_type, int):
                    device_copy[KEY_PREFER_STATUS] = uses_status_presence(
                        manufacturer,
                        device_type,
                    )
            resolved.append(device_copy)
        profiles[name] = resolved

    default_profile = payload.get(KEY_DEFAULT_PROFILE) or DEFAULT_PROFILE_NAME
    if default_profile not in profiles:
        default_profile = DEFAULT_PROFILE_NAME

    if not profiles:
        _LOAD_ERROR = MSG_PROFILES_EMPTY
        return (_fallback_default(), _fallback_profiles())

    return (default_profile, profiles)



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
    return {
        DEFAULT_PROFILE_NAME: [],
    }


DEFAULT_PROFILE, PROFILE_DEVICES = _load_profiles()



def get_default_profile() -> str:
    """
    NAME
        get_default_profile - Return the default profile name.
    """
    return DEFAULT_PROFILE



def get_profile_schema_version() -> int:
    """
    NAME
        get_profile_schema_version - Return the expected profiles schema version.
    """
    return PROFILE_SCHEMA_VERSION



def get_profiles_load_error() -> str:
    """
    NAME
        get_profiles_load_error - Return the last profiles load error, if any.
    """
    return _LOAD_ERROR



def get_profiles_data_version() -> str:
    """
    NAME
        get_profiles_data_version - Return the loaded profile data_version.
    """
    return _DATA_VERSION



def get_profiles_data_hash() -> str:
    """
    NAME
        get_profiles_data_hash - Return the loaded profile data_hash.
    """
    return _DATA_HASH



def reload_profiles() -> Tuple[bool, str]:
    """
    NAME
        reload_profiles - Reload profiles from disk and refresh globals.
    """
    global DEFAULT_PROFILE, PROFILE_DEVICES
    default_profile, profiles = _load_profiles()
    if _LOAD_ERROR:
        return False, _LOAD_ERROR
    DEFAULT_PROFILE = default_profile
    PROFILE_DEVICES = profiles
    return True, ""



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
        devices = [
            entry
            for entry in PROFILE_DEVICES[profile]
            if entry.get(KEY_INTERFACE) == INTERFACE_CAN
        ]
        return (devices, set())
    raise ValueError(
        MSG_UNKNOWN_PROFILE.format(
            profile=profile,
            profiles=", ".join(PROFILE_DEVICES.keys()),
        )
    )
