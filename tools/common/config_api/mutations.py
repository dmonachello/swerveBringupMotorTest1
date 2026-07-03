from __future__ import annotations

"""
NAME
    mutations.py - Shared config mutation helpers for bringup_system.json.

DESCRIPTION
    Owns semantic payload updates that should behave the same across host
    surfaces. These helpers preserve non-targeted profile metadata while
    updating canonical fields such as devices.
"""

from typing import Dict, Iterable, List, Optional, Tuple

from tools.common.profile_constants import (
    KEY_DEFAULT_PROFILE,
    KEY_DEVICES,
    KEY_DIAGRAM,
    KEY_PROFILES,
    KEY_TOPOLOGY,
    KEY_TOPOLOGY_EDGES,
    KEY_TOPOLOGY_NODES,
    KEY_TOPOLOGY_PROFILES,
    KEY_TOPOLOGY_SOURCE,
    KEY_TOPOLOGY_VERSION,
)


DEFAULT_TOPOLOGY_SOURCE = "local"
DEFAULT_TOPOLOGY_VERSION = 1


def _ensure_profile_roots(payload: Dict[str, object]) -> Tuple[Dict[str, object], Dict[str, object], Dict[str, object]]:
    """
    NAME
        _ensure_profile_roots - Ensure profiles/topology/diagram profile maps exist.
    """
    profiles = payload.get(KEY_PROFILES)
    if not isinstance(profiles, dict):
        profiles = {}
        payload[KEY_PROFILES] = profiles

    topology = payload.get(KEY_TOPOLOGY)
    if not isinstance(topology, dict):
        topology = {
            KEY_TOPOLOGY_VERSION: DEFAULT_TOPOLOGY_VERSION,
            KEY_TOPOLOGY_SOURCE: DEFAULT_TOPOLOGY_SOURCE,
            KEY_TOPOLOGY_PROFILES: {},
        }
        payload[KEY_TOPOLOGY] = topology
    topology_profiles = topology.get(KEY_TOPOLOGY_PROFILES)
    if not isinstance(topology_profiles, dict):
        topology_profiles = {}
        topology[KEY_TOPOLOGY_PROFILES] = topology_profiles

    diagram = payload.get(KEY_DIAGRAM)
    if not isinstance(diagram, dict):
        diagram = {}
        payload[KEY_DIAGRAM] = diagram
    diagram_profiles = diagram.get(KEY_PROFILES)
    if not isinstance(diagram_profiles, dict):
        diagram_profiles = {}
        diagram[KEY_PROFILES] = diagram_profiles
    return profiles, topology_profiles, diagram_profiles


def _normalize_device_labels(device_labels: Iterable[object]) -> List[str]:
    """
    NAME
        _normalize_device_labels - Normalize profile device labels while preserving order.
    """
    labels: List[str] = []
    seen: set[str] = set()
    for value in device_labels:
        label = str(value or "").strip()
        if not label or label in seen:
            continue
        seen.add(label)
        labels.append(label)
    return labels


def replace_profile_devices(existing_profile: object, device_labels: Iterable[object]) -> Dict[str, object]:
    """
    NAME
        replace_profile_devices - Preserve profile metadata while replacing the devices list.

    PARAMETERS
        existing_profile - Existing profile payload or non-dict placeholder.
        device_labels - New ordered device labels for the profile.

    RETURNS
        Dict profile payload with non-device fields preserved.
    """
    merged = dict(existing_profile) if isinstance(existing_profile, dict) else {}
    merged[KEY_DEVICES] = _normalize_device_labels(device_labels)
    return merged


def blank_profile_payload() -> Dict[str, object]:
    """
    NAME
        blank_profile_payload - Build the canonical empty profile payload.
    """
    return replace_profile_devices({}, [])


def blank_topology_entry() -> Dict[str, object]:
    """
    NAME
        blank_topology_entry - Build the canonical blank topology entry.
    """
    return {
        KEY_TOPOLOGY_VERSION: DEFAULT_TOPOLOGY_VERSION,
        KEY_TOPOLOGY_SOURCE: DEFAULT_TOPOLOGY_SOURCE,
        KEY_TOPOLOGY_NODES: [],
        KEY_TOPOLOGY_EDGES: [],
    }


def upsert_profile(
    payload: Dict[str, object],
    profile_name: str,
    profile_payload: Dict[str, object],
    *,
    topology_entry: Optional[Dict[str, object]] = None,
    diagram_entry: Optional[Dict[str, object]] = None,
    set_default_if_missing: bool = False,
) -> Dict[str, object]:
    """
    NAME
        upsert_profile - Insert or replace one profile while preserving other root data.
    """
    profiles, topology_profiles, diagram_profiles = _ensure_profile_roots(payload)
    profiles[profile_name] = dict(profile_payload)
    if topology_entry is not None:
        topology_profiles[profile_name] = dict(topology_entry)
    if diagram_entry is not None:
        diagram_profiles[profile_name] = dict(diagram_entry)
    if set_default_if_missing and not isinstance(payload.get(KEY_DEFAULT_PROFILE), str):
        payload[KEY_DEFAULT_PROFILE] = profile_name
    return payload


def create_blank_profile(
    payload: Dict[str, object],
    profile_name: str,
    *,
    set_default_if_missing: bool = False,
) -> Dict[str, object]:
    """
    NAME
        create_blank_profile - Insert a canonical empty profile and topology entry.
    """
    return upsert_profile(
        payload,
        profile_name,
        blank_profile_payload(),
        topology_entry=blank_topology_entry(),
        set_default_if_missing=set_default_if_missing,
    )


def replace_profile_topology_entry(
    payload: Dict[str, object],
    profile_name: str,
    topology_entry: Dict[str, object],
) -> Dict[str, object]:
    """
    NAME
        replace_profile_topology_entry - Replace one profile topology entry.

    DESCRIPTION
        Preserves profile payloads, diagram entries, and unrelated topology
        entries while updating the canonical topology snapshot for one profile.
    """
    _, topology_profiles, _ = _ensure_profile_roots(payload)
    topology_profiles[profile_name] = dict(topology_entry)
    return payload


def ensure_profile_topology_entry(
    payload: Dict[str, object],
    profile_name: str,
) -> Dict[str, object]:
    """
    NAME
        ensure_profile_topology_entry - Ensure one profile has a topology entry.
    """
    _, topology_profiles, _ = _ensure_profile_roots(payload)
    profile = topology_profiles.get(profile_name)
    if not isinstance(profile, dict):
        profile = blank_topology_entry()
        topology_profiles[profile_name] = profile
    if not isinstance(profile.get(KEY_TOPOLOGY_NODES), list):
        profile[KEY_TOPOLOGY_NODES] = []
    if not isinstance(profile.get(KEY_TOPOLOGY_EDGES), list):
        profile[KEY_TOPOLOGY_EDGES] = []
    return profile


def set_default_profile(
    payload: Dict[str, object],
    profile_name: str,
) -> Dict[str, object]:
    """
    NAME
        set_default_profile - Set the canonical default profile name.
    """
    payload[KEY_DEFAULT_PROFILE] = profile_name
    return payload


def rename_profile(
    payload: Dict[str, object],
    old_name: str,
    new_name: str,
) -> Dict[str, object]:
    """
    NAME
        rename_profile - Rename one profile and matching topology/diagram entries.
    """
    profiles, topology_profiles, diagram_profiles = _ensure_profile_roots(payload)
    profile_entry = profiles.pop(old_name)
    profiles[new_name] = profile_entry
    if old_name in topology_profiles:
        topology_profiles[new_name] = topology_profiles.pop(old_name)
    if old_name in diagram_profiles:
        diagram_profiles[new_name] = diagram_profiles.pop(old_name)
    if payload.get(KEY_DEFAULT_PROFILE) == old_name:
        payload[KEY_DEFAULT_PROFILE] = new_name
    return payload


def delete_profile(
    payload: Dict[str, object],
    profile_name: str,
) -> Dict[str, object]:
    """
    NAME
        delete_profile - Remove one profile and matching topology/diagram entries.
    """
    profiles, topology_profiles, diagram_profiles = _ensure_profile_roots(payload)
    profiles.pop(profile_name, None)
    topology_profiles.pop(profile_name, None)
    diagram_profiles.pop(profile_name, None)
    if payload.get(KEY_DEFAULT_PROFILE) == profile_name:
        payload.pop(KEY_DEFAULT_PROFILE, None)
    return payload
