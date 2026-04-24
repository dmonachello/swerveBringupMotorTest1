from __future__ import annotations

"""
NAME
    lookup.py - Shared profile/device lookup helpers.
"""

from typing import Any, Dict, List, Optional

from tools.common.profile_constants import (
    KEY_BRIDGE_CONFIG,
    KEY_BRIDGE_TESTS,
    KEY_DEFAULT_PROFILE,
    KEY_DEVICES,
    KEY_LABEL,
    KEY_PROFILE,
    KEY_PROFILE_DEVICES,
    KEY_PROFILES,
)


def list_profile_names(root_payload: Dict[str, Any]) -> List[str]:
    """
    NAME
        list_profile_names - Return sorted profile names from payload.
    """
    profiles = root_payload.get(KEY_PROFILES, {})
    if not isinstance(profiles, dict):
        return []
    names = [str(name) for name in profiles.keys() if isinstance(name, str) and name.strip()]
    return sorted(names)


def resolve_active_profile(root_payload: Dict[str, Any], selected_profile: Optional[str]) -> str:
    """
    NAME
        resolve_active_profile - Resolve selected profile with default fallback.
    """
    if isinstance(selected_profile, str) and selected_profile.strip():
        return selected_profile.strip()
    default_profile = root_payload.get(KEY_DEFAULT_PROFILE)
    if isinstance(default_profile, str) and default_profile.strip():
        return default_profile.strip()
    names = list_profile_names(root_payload)
    return names[0] if names else ""


def find_device_by_label(root_payload: Dict[str, Any], label: str) -> Optional[Dict[str, Any]]:
    """
    NAME
        find_device_by_label - Resolve a device entry by label.
    """
    if not isinstance(label, str) or not label.strip():
        return None
    devices = root_payload.get(KEY_DEVICES, [])
    if not isinstance(devices, list):
        return None
    needle = label.strip().lower()
    for entry in devices:
        if isinstance(entry, dict):
            entry_label = entry.get(KEY_LABEL)
            if isinstance(entry_label, str) and entry_label.strip().lower() == needle:
                return entry
    return None


def tests_for_profile(root_payload: Dict[str, Any], profile_name: str) -> List[Dict[str, Any]]:
    """
    NAME
        tests_for_profile - Return bridge tests list for one profile.
    """
    bridge_config = root_payload.get(KEY_BRIDGE_CONFIG, {})
    if not isinstance(bridge_config, dict):
        return []
    by_profile = bridge_config.get(KEY_PROFILE, {})
    if not isinstance(by_profile, dict):
        by_profile = bridge_config.get("byProfile", {})
    if not isinstance(by_profile, dict):
        return []
    profile_entry = by_profile.get(profile_name, {})
    if not isinstance(profile_entry, dict):
        return []
    tests = profile_entry.get(KEY_BRIDGE_TESTS, [])
    if not isinstance(tests, list):
        return []
    return [entry for entry in tests if isinstance(entry, dict)]

