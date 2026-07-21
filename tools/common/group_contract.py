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

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

from tools.common.profile_constants import KEY_DEVICE_TYPE, KEY_ENABLED, KEY_TYPE, TYPE_MOTOR, get_group_member_label

EMPTY_STRING = ""
DEVICE_TYPE_MOTOR = "2"
GROUP_KEY_NAME = "name"
GROUP_KEY_MEMBERS = "members"
GROUP_KEY_BINDINGS = "bindings"
GROUP_RUNTIME_PRESENT_THRESHOLD = 0.5


@dataclass(frozen=True)
class GroupMemberState:
    """
    NAME
        GroupMemberState - Shared resolved state for one group member.
    """

    label: str
    enabled: bool
    locked: bool
    invalid: bool
    scope_active: bool
    runtime_present: bool
    instantiated: bool
    testable: bool


@dataclass(frozen=True)
class GroupState:
    """
    NAME
        GroupState - Shared resolved state for one group and its member facts.
    """

    name: str
    primary_label: str
    members: List[GroupMemberState]
    member_count: int
    enabled_member_count: int
    has_members: bool
    all_enabled_members_present: bool


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


def resolve_group_member_state(
    *,
    label: object,
    enabled: bool,
    locked: bool,
    invalid: bool,
    runtime_state_by_label: Dict[str, Dict[str, Any]],
    scope_active: bool,
    singleton_labels: Sequence[str] = (),
) -> GroupMemberState:
    """
    NAME
        resolve_group_member_state - Return shared resolved facts for one group member label.
    """
    clean_label = str(label or EMPTY_STRING).strip()
    label_key = clean_label.lower()
    runtime_device = runtime_state_by_label.get(label_key, {})
    runtime_present = False
    instantiated = False
    testable = False
    if isinstance(runtime_device, dict):
        presence = runtime_device.get("presenceConfidence")
        runtime_present = isinstance(presence, (int, float)) and float(presence) >= GROUP_RUNTIME_PRESENT_THRESHOLD
        instantiated = bool(runtime_device.get("instantiated", False))
        testable = bool(runtime_device.get("testable", False))
        if not instantiated and label_key in {str(value).strip().lower() for value in singleton_labels}:
            instantiated = testable
    return GroupMemberState(
        label=clean_label,
        enabled=bool(enabled),
        locked=bool(locked),
        invalid=bool(invalid),
        scope_active=bool(scope_active),
        runtime_present=runtime_present,
        instantiated=instantiated,
        testable=testable,
    )


def resolve_group_state_from_member_map(
    *,
    name: object,
    member_map: Dict[str, Dict[str, Any]],
    runtime_state_by_label: Dict[str, Dict[str, Any]],
    primary_label: object,
    scope_active: bool,
    singleton_labels: Sequence[str] = (),
) -> GroupState:
    """
    NAME
        resolve_group_state_from_member_map - Build shared resolved state from one normalized member map.
    """
    members: List[GroupMemberState] = []
    for member_key, member in member_map.items():
        if not isinstance(member, dict):
            continue
        member_label = group_member_label(member) or str(member_key or EMPTY_STRING).strip()
        if not member_label:
            continue
        members.append(
            resolve_group_member_state(
                label=member_label,
                enabled=group_member_enabled(member),
                locked=False,
                invalid=False,
                runtime_state_by_label=runtime_state_by_label,
                scope_active=scope_active,
                singleton_labels=singleton_labels,
            )
        )
    enabled_members = [member for member in members if member.enabled]
    return GroupState(
        name=str(name or EMPTY_STRING).strip(),
        primary_label=str(primary_label or EMPTY_STRING).strip(),
        members=members,
        member_count=len(members),
        enabled_member_count=len(enabled_members),
        has_members=bool(members),
        all_enabled_members_present=bool(enabled_members) and all(member.runtime_present for member in enabled_members),
    )


def resolve_group_state_from_rows(
    *,
    name: object,
    rows: Sequence[object],
    runtime_state_by_label: Dict[str, Dict[str, Any]],
    primary_label: object,
    scope_active: bool,
    singleton_labels: Sequence[str] = (),
) -> GroupState:
    """
    NAME
        resolve_group_state_from_rows - Build shared resolved state from row-style member payloads.
    """
    members: List[GroupMemberState] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        member_label = str(row.get("label", EMPTY_STRING)).strip()
        if not member_label:
            continue
        members.append(
            resolve_group_member_state(
                label=member_label,
                enabled=bool(row.get(KEY_ENABLED, True)),
                locked=bool(row.get("locked")) or bool(scope_active),
                invalid=bool(row.get("invalid")),
                runtime_state_by_label=runtime_state_by_label,
                scope_active=scope_active,
                singleton_labels=singleton_labels,
            )
        )
    enabled_members = [member for member in members if member.enabled]
    return GroupState(
        name=str(name or EMPTY_STRING).strip(),
        primary_label=str(primary_label or EMPTY_STRING).strip(),
        members=members,
        member_count=len(members),
        enabled_member_count=len(enabled_members),
        has_members=bool(members),
        all_enabled_members_present=bool(enabled_members) and all(member.runtime_present for member in enabled_members),
    )


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
