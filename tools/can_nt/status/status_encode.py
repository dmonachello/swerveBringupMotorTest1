"""
NAME
    status_encode.py - Encode/decode helpers for status codes.

SYNOPSIS
    from tools.can_nt.status.status_encode import code, decode, format_status

DESCRIPTION
    Provides shared encode/decode helpers for the 32-bit status code format.
"""

from __future__ import annotations

import re
from typing import Dict

from tools.can_nt.status.status_catalog import FAC, SEV, MSG

SHIFT_SEVERITY = 0
SHIFT_MESSAGE = 3
SHIFT_FACILITY = 16
SHIFT_FLAGS = 28

MASK_SEVERITY = 0b111
MASK_MESSAGE = 0x1FFF
MASK_FACILITY = 0x0FFF
MASK_FLAGS = 0xF

KEY_SEVERITY = "severity"
KEY_MESSAGE = "message"
KEY_FACILITY = "facility"
KEY_FLAGS = "flags"

UNKNOWN_FACILITY = "UNKNOWN_FACILITY"
UNKNOWN_MESSAGE = "UNKNOWN_MESSAGE"
UNKNOWN_SEVERITY = "UNKNOWN_SEVERITY"
UNKNOWN_TEMPLATE = ""
EMPTY_MAPPING: Dict[str, int] = {}
REGEX_PLACEHOLDER = re.compile(r"\{([A-Za-z0-9_]+)\}")

FLAG_PRINT_MESSAGE = 1 << 28
FLAG_LOG_ONLY = 1 << 29
FLAG_USER_DEFINED = 1 << 30
FLAG_RESERVED = 1 << 31


def code(severity: int, facility: int, message: int, flags: int = 0) -> int:
    return (flags << SHIFT_FLAGS) | (facility << SHIFT_FACILITY) | (message << SHIFT_MESSAGE) | severity


def decode(value: int) -> Dict[str, int]:
    return {
        KEY_SEVERITY: (value >> SHIFT_SEVERITY) & MASK_SEVERITY,
        KEY_MESSAGE: (value >> SHIFT_MESSAGE) & MASK_MESSAGE,
        KEY_FACILITY: (value >> SHIFT_FACILITY) & MASK_FACILITY,
        KEY_FLAGS: (value >> SHIFT_FLAGS) & MASK_FLAGS,
    }


def format_status(value: int, include_raw: bool = False) -> str:
    parts = decode(value)
    sev_name = _reverse_lookup(SEV.__dict__, parts[KEY_SEVERITY], UNKNOWN_SEVERITY)
    fac_name = _reverse_lookup(FAC.__dict__, parts[KEY_FACILITY], UNKNOWN_FACILITY)
    msg_container = MSG.__dict__.get(fac_name, EMPTY_MAPPING)
    msg_map = _coerce_mapping(msg_container)
    msg_name = _reverse_lookup(msg_map, parts[KEY_MESSAGE], UNKNOWN_MESSAGE)
    label = f"{sev_name} [{fac_name}.{msg_name}]"
    if include_raw:
        return f"{label} (0x{value:08X})"
    return label


def format_status_message(value: int, *args: object, **kwargs: object) -> str | None:
    """
    NAME
        format_status_message - Return formatted message text for a status code.
    """

    from tools.can_nt.status.status_messages import get_message_template

    template = get_message_template(value) or UNKNOWN_TEMPLATE
    if not template:
        return None
    if kwargs:
        safe_kwargs = dict(kwargs)
    else:
        safe_kwargs = {}
    for key in REGEX_PLACEHOLDER.findall(template):
        if key not in safe_kwargs:
            safe_kwargs[key] = key
    try:
        return template.format(*args, **safe_kwargs)
    except (KeyError, IndexError, ValueError):
        return template


def _reverse_lookup(mapping: Dict[str, int], value: int, fallback: str) -> str:
    for name, code_value in mapping.items():
        if name.startswith("_"):
            continue
        if code_value == value:
            return name
    return fallback


def _coerce_mapping(mapping_like: object) -> Dict[str, int]:
    """
    NAME
        _coerce_mapping - Normalize mapping-like objects to dicts for lookups.
    """

    if isinstance(mapping_like, dict):
        return mapping_like
    return getattr(mapping_like, "__dict__", EMPTY_MAPPING)
