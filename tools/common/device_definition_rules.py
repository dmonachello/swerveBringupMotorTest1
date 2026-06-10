from __future__ import annotations

"""
NAME
    device_definition_rules.py - Shared device-definition contract helpers.

SYNOPSIS
    from tools.common.device_definition_rules import (
        format_device_required_field_issue,
        missing_required_fields_for_interface,
    )

DESCRIPTION
    Centralizes interface-specific required fields and basic type checks for
    device definitions that move across topology, CLI, UI, and config flows.
"""

from typing import Dict, List, Mapping, Optional, Tuple, Type

from tools.common.profile_constants import (
    INTERFACE_ANALOG,
    INTERFACE_CAN,
    INTERFACE_DIO,
    INTERFACE_INTERNAL,
    INTERFACE_PWM,
    INTERFACE_USB,
    KEY_ANALOG,
    KEY_DEVICE_TYPE,
    KEY_ID,
    KEY_INTERFACE,
    KEY_INVERT,
    KEY_MANUFACTURER,
    KEY_PWM,
    get_device_interface,
)

FIELD_JOINER = "/"
ISSUE_JOINER = "; "
MESSAGE_DEVICE_FMT = "Device '{label}' {details}."
MESSAGE_DEVICE_MISSING_FMT = "missing {interface} fields: {fields}"
MESSAGE_DEVICE_INVALID_FMT = "invalid {interface} fields: {fields}"

DEVICE_REQUIRED_FIELDS_BY_INTERFACE: Dict[str, Tuple[str, ...]] = {
    INTERFACE_CAN: (KEY_MANUFACTURER, KEY_DEVICE_TYPE, KEY_ID),
    INTERFACE_DIO: (KEY_ID, KEY_INVERT),
    INTERFACE_PWM: (KEY_PWM,),
    INTERFACE_ANALOG: (KEY_ANALOG,),
    INTERFACE_USB: (KEY_ID,),
    INTERFACE_INTERNAL: tuple(),
}

DEVICE_REQUIRED_TYPES_BY_INTERFACE: Dict[str, Dict[str, Type[object]]] = {
    INTERFACE_CAN: {
        KEY_MANUFACTURER: int,
        KEY_DEVICE_TYPE: int,
        KEY_ID: int,
    },
    INTERFACE_DIO: {
        KEY_ID: int,
        KEY_INVERT: bool,
    },
    INTERFACE_PWM: {
        KEY_PWM: int,
    },
    INTERFACE_ANALOG: {
        KEY_ANALOG: int,
    },
    INTERFACE_USB: {
        KEY_ID: int,
    },
    INTERFACE_INTERNAL: {},
}


def required_fields_for_interface(interface: object, include_interface: bool = False) -> Tuple[str, ...]:
    """
    NAME
        required_fields_for_interface - Return required fields for a device interface.

    PARAMETERS
        interface - Interface string such as CAN, DIO, or USB.
        include_interface - Include deviceInterface in the returned tuple.
    """

    normalized = _normalize_interface(interface)
    fields = DEVICE_REQUIRED_FIELDS_BY_INTERFACE.get(normalized)
    if fields is None:
        return (KEY_INTERFACE,) if include_interface else tuple()
    if include_interface:
        return (KEY_INTERFACE,) + fields
    return fields


def missing_required_fields_for_interface(entry: Mapping[str, object]) -> List[str]:
    """
    NAME
        missing_required_fields_for_interface - Return missing required fields.
    """

    interface = _normalize_interface(get_device_interface(entry))
    required = required_fields_for_interface(interface)
    return [field for field in required if entry.get(field) is None]


def invalid_required_fields_for_interface(entry: Mapping[str, object]) -> List[str]:
    """
    NAME
        invalid_required_fields_for_interface - Return required fields with wrong types.
    """

    interface = _normalize_interface(get_device_interface(entry))
    expected_types = DEVICE_REQUIRED_TYPES_BY_INTERFACE.get(interface, {})
    invalid: List[str] = []
    for field, expected_type in expected_types.items():
        value = entry.get(field)
        if value is None:
            continue
        if not isinstance(value, expected_type):
            invalid.append(field)
    return invalid


def format_device_required_field_issue(label: str, entry: Mapping[str, object]) -> Optional[str]:
    """
    NAME
        format_device_required_field_issue - Return a user-facing missing/invalid field message.
    """

    interface = _normalize_interface(get_device_interface(entry))
    if not interface:
        return None
    missing = missing_required_fields_for_interface(entry)
    invalid = invalid_required_fields_for_interface(entry)
    if not missing and not invalid:
        return None
    parts: List[str] = []
    if missing:
        parts.append(
            MESSAGE_DEVICE_MISSING_FMT.format(
                interface=interface,
                fields=FIELD_JOINER.join(missing),
            )
        )
    if invalid:
        parts.append(
            MESSAGE_DEVICE_INVALID_FMT.format(
                interface=interface,
                fields=FIELD_JOINER.join(invalid),
            )
        )
    return MESSAGE_DEVICE_FMT.format(label=label, details=ISSUE_JOINER.join(parts))


def _normalize_interface(interface: object) -> str:
    """
    NAME
        _normalize_interface - Normalize device interface text.
    """

    if not isinstance(interface, str):
        return ""
    return interface.strip().upper()
