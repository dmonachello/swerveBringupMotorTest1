from __future__ import annotations

"""
NAME
    group_contract.py - Shared host-side group normalization and resolution helpers.

SYNOPSIS
    from tools.common.group_contract import merge_effective_groups

DESCRIPTION
    Centralizes the readable host-side rules for:
    - interpreting group member entries
    - merging static and runtime groups by name
    - resolving member labels back to device entries
    - selecting enabled motor targets for UI interactions

NOTES
    These helpers intentionally favor explicit, easy-to-follow control flow
    over micro-optimizations. The goal is one shared contract that renderers
    and UI interactions can both consume.
"""

from typing import Any, Dict, List, Optional, Sequence

from tools.common.profile_constants import KEY_DEVICE_TYPE, KEY_ENABLED, KEY_TYPE, TYPE_MOTOR, get_group_member_label

EMPTY_STRING = ""
DEVICE_TYPE_MOTOR = "2"
GROUP_KEY_NAME = "name"
GROUP_KEY_MEMBERS = "members"
GROUP_KEY_BINDINGS = "bindings"


def normalize_group_name(value: object) -> str:
    """
    NAME
        normalize_group_name - Return one group name normalized for lookups.
    """
    return str(value or EMPTY_STRING).strip().lower()


def group_member_label(member: object) -> str:
    """
    NAME
        group_member_label - Return one member label from either canonical or compatibility shapes.
    """
    if isinstance(member, dict):
        return get_group_member_label(member)
    return str(member or EMPTY_STRING).strip()


def group_member_enabled(member: object) -> bool:
    """
    NAME
        group_member_enabled - Return whether one group member is enabled.
    """
    if not isinstance(member, dict):
        return True
    enabled = member.get(KEY_ENABLED)
    if isinstance(enabled, bool):
        return enabled
    return True


def group_member_labels(group: object, *, enabled_only: bool) -> List[str]:
    """
    NAME
        group_member_labels - Return ordered member labels from one group payload.
    """
    if not isinstance(group, dict):
        return []
    members = group.get(GROUP_KEY_MEMBERS)
    if not isinstance(members, list):
        return []
    labels: List[str] = []
    for member in members:
        label = group_member_label(member)
        if not label:
            continue
        if enabled_only and not group_member_enabled(member):
            continue
        labels.append(label)
    return labels


def group_member_map(group: object, *, enabled_only: bool) -> Dict[str, Dict[str, object]]:
    """
    NAME
        group_member_map - Return one lowercase-label member map from a group payload.
    """
    if not isinstance(group, dict):
        return {}
    members = group.get(GROUP_KEY_MEMBERS)
    if not isinstance(members, list):
        return {}
    mapped: Dict[str, Dict[str, object]] = {}
    for member in members:
        label = group_member_label(member)
        if not label:
            continue
        if enabled_only and not group_member_enabled(member):
            continue
        key = label.strip().lower()
        if not key:
            continue
        if isinstance(member, dict):
            mapped[key] = dict(member)
        else:
            mapped[key] = {"label": label, KEY_ENABLED: True}
    return mapped


def group_primary_label(group: object, *, enabled_only: bool) -> str:
    """
    NAME
        group_primary_label - Return the first ordered group member label, optionally filtered by enabled state.
    """
    labels = group_member_labels(group, enabled_only=enabled_only)
    if not labels:
        return EMPTY_STRING
    return labels[0]


def merge_effective_groups(
    static_groups: Sequence[object],
    runtime_groups: Sequence[object],
) -> List[Dict[str, object]]:
    """
    NAME
        merge_effective_groups - Merge static profile groups with runtime groups by normalized name.

    DESCRIPTION
        Runtime groups override static groups by name, but when the runtime
        payload only carries summary fields the static members/bindings remain
        authoritative so draw and interaction paths stay consistent.
    """
    merged: Dict[str, Dict[str, object]] = {}
    order: List[str] = []
    for source_groups in (static_groups, runtime_groups):
        for raw_group in source_groups:
            if not isinstance(raw_group, dict):
                continue
            name = str(raw_group.get(GROUP_KEY_NAME, EMPTY_STRING)).strip()
            if not name:
                continue
            key = normalize_group_name(name)
            if key not in merged:
                merged[key] = dict(raw_group)
                order.append(key)
                continue
            merged[key] = _merge_group_pair(merged[key], raw_group)
    return [merged[key] for key in order]


def find_group_by_name(groups: Sequence[object], name: object) -> Optional[Dict[str, object]]:
    """
    NAME
        find_group_by_name - Return one normalized-name group from an already-shaped group sequence.
    """
    normalized_name = normalize_group_name(name)
    if not normalized_name:
        return None
    for raw_group in groups:
        if not isinstance(raw_group, dict):
            continue
        if normalize_group_name(raw_group.get(GROUP_KEY_NAME)) == normalized_name:
            return raw_group
    return None


def _merge_group_pair(static_group: Dict[str, object], runtime_group: Dict[str, object]) -> Dict[str, object]:
    """
    NAME
        _merge_group_pair - Merge one runtime group over one static group.
    """
    merged = dict(runtime_group)
    static_members = static_group.get(GROUP_KEY_MEMBERS)
    runtime_members = runtime_group.get(GROUP_KEY_MEMBERS)
    if isinstance(static_members, list) and (not isinstance(runtime_members, list) or not runtime_members):
        merged[GROUP_KEY_MEMBERS] = list(static_members)
    static_bindings = static_group.get(GROUP_KEY_BINDINGS)
    runtime_bindings = runtime_group.get(GROUP_KEY_BINDINGS)
    if isinstance(static_bindings, list) and (not isinstance(runtime_bindings, list) or not runtime_bindings):
        merged[GROUP_KEY_BINDINGS] = list(static_bindings)
    return merged


def find_device_entry_by_label(
    label: object,
    catalogs: Sequence[Optional[Dict[str, Dict[str, Any]]]],
    *,
    fallback_device_lists: Sequence[Sequence[object]] = (),
) -> Dict[str, Any]:
    """
    NAME
        find_device_entry_by_label - Resolve one label from primary catalogs then optional fallback device lists.
    """
    clean_label = str(label or EMPTY_STRING).strip().lower()
    if not clean_label:
        return {}
    for catalog in catalogs:
        if not isinstance(catalog, dict):
            continue
        entry = catalog.get(clean_label, {})
        if isinstance(entry, dict) and entry:
            return entry
    for device_list in fallback_device_lists:
        for entry in device_list:
            if not isinstance(entry, dict):
                continue
            entry_label = str(entry.get("label", EMPTY_STRING)).strip().lower()
            if entry_label == clean_label:
                return entry
    return {}


def device_entry_is_motor(device: object) -> bool:
    """
    NAME
        device_entry_is_motor - Return whether one known device entry represents a motor.
    """
    if not isinstance(device, dict):
        return False
    device_type = str(device.get(KEY_DEVICE_TYPE, EMPTY_STRING)).strip()
    if device_type == DEVICE_TYPE_MOTOR:
        return True
    type_name = str(device.get(KEY_TYPE, EMPTY_STRING)).strip().lower()
    return type_name == TYPE_MOTOR.lower()


def resolve_group_motor_targets(
    group: object,
    catalogs: Sequence[Optional[Dict[str, Dict[str, Any]]]],
    *,
    fallback_device_lists: Sequence[Sequence[object]] = (),
) -> List[str]:
    """
    NAME
        resolve_group_motor_targets - Return enabled motor member labels for one group payload.
    """
    targets: List[str] = []
    for label in group_member_labels(group, enabled_only=True):
        device = find_device_entry_by_label(
            label,
            catalogs,
            fallback_device_lists=fallback_device_lists,
        )
        if device_entry_is_motor(device):
            targets.append(label)
    return targets
