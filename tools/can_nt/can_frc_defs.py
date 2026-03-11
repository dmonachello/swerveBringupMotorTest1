from __future__ import annotations

"""
NAME
    can_frc_defs.py - FRC CAN ID helpers and classification rules.

SYNOPSIS
    from tools.can_nt.can_frc_defs import decode_frc_ext_id_full, classify_frame

DESCRIPTION
    Defines common FRC CAN ID constants and rule tables to classify frames as
    status or control for bringup diagnostics.
"""

from typing import Any, Dict, Tuple

NI_MANUFACTURER = 1
CTRE_MANUFACTURER = 4
REV_MANUFACTURER = 5

DEVICE_TYPE_MOTOR_CONTROLLER = 2
DEVICE_TYPE_PNEUMATICS = 8
DEVICE_TYPE_ROBORIO = 1

NI_ROBORIO_STATUS_API_CLASS = 6
REV_MC_STATUS_API_CLASS = 6
REV_MC_STATUS_API_CLASS_EXT = 46
CTRE_MC_STATUS_API_CLASS = 11
CTRE_PNEU_STATUS_API_CLASS = 5

CTRE_J1939_CONTROL_PF = 0xEF
CTRE_J1939_STATUS_PF = 0xFF
CTRE_J1939_STATUS_PS_MAX = 0x07

STATUS_RULES = [
    {
        "name": "NI_ROBORIO_STATUS",
        "mfg": NI_MANUFACTURER,
        "type": DEVICE_TYPE_ROBORIO,
        "api_class": NI_ROBORIO_STATUS_API_CLASS,
    },
    {
        "name": "REV_MC_STATUS",
        "mfg": REV_MANUFACTURER,
        "type": DEVICE_TYPE_MOTOR_CONTROLLER,
        "api_class": REV_MC_STATUS_API_CLASS,
    },
    {
        "name": "REV_MC_STATUS_EXT",
        "mfg": REV_MANUFACTURER,
        "type": DEVICE_TYPE_MOTOR_CONTROLLER,
        "api_class": REV_MC_STATUS_API_CLASS_EXT,
        "api_index_min": 0,
        "api_index_max": 6,
    },
    {
        "name": "CTRE_J1939_STATUS",
        "mfg": CTRE_MANUFACTURER,
        "pf": CTRE_J1939_STATUS_PF,
        "ps_max": CTRE_J1939_STATUS_PS_MAX,
    },
    {
        "name": "CTRE_FRC_STATUS_MC",
        "mfg": CTRE_MANUFACTURER,
        "type": DEVICE_TYPE_MOTOR_CONTROLLER,
        "api_class": CTRE_MC_STATUS_API_CLASS,
    },
    {
        "name": "CTRE_FRC_STATUS_PNEU",
        "mfg": CTRE_MANUFACTURER,
        "type": DEVICE_TYPE_PNEUMATICS,
        "api_class": CTRE_PNEU_STATUS_API_CLASS,
    },
]

CONTROL_RULES = [
    {
        "name": "CTRE_J1939_CONTROL",
        "mfg": CTRE_MANUFACTURER,
        "pf": CTRE_J1939_CONTROL_PF,
    },
    {
        "name": "REV_MC_CONTROL_EXT",
        "mfg": REV_MANUFACTURER,
        "type": DEVICE_TYPE_MOTOR_CONTROLLER,
        "api_class": REV_MC_STATUS_API_CLASS_EXT,
        "api_index_min": 7,
    },
]

PROFILE_MAP_RULES = [
    {
        "name": "REV_MC_TO_NEOS",
        "mfg": REV_MANUFACTURER,
        "type": DEVICE_TYPE_MOTOR_CONTROLLER,
        "bucket": "neos",
        "note": "REV mfg=5 type=2 mapped to 'neos' (cannot distinguish NEO vs FLEX).",
    },
    {
        "name": "CTRE_MC_TO_KRAKENS",
        "mfg": CTRE_MANUFACTURER,
        "type": DEVICE_TYPE_MOTOR_CONTROLLER,
        "bucket": "krakens",
        "note": "CTRE mfg=4 type=2 mapped to 'krakens' (cannot distinguish Kraken vs Falcon).",
    },
    {
        "name": "CTRE_CANCODER",
        "mfg": CTRE_MANUFACTURER,
        "type": 7,
        "bucket": "cancoders",
    },
    {
        "name": "REV_PDH",
        "mfg": REV_MANUFACTURER,
        "type": DEVICE_TYPE_PNEUMATICS,
        "singleton": "pdh",
    },
    {
        "name": "CTRE_PDP",
        "mfg": CTRE_MANUFACTURER,
        "type": DEVICE_TYPE_PNEUMATICS,
        "singleton": "pdp",
    },
    {
        "name": "CTRE_PIGEON",
        "mfg": CTRE_MANUFACTURER,
        "type": 4,
        "singleton": "pigeon",
    },
    {
        "name": "NI_ROBORIO",
        "mfg": NI_MANUFACTURER,
        "type": DEVICE_TYPE_ROBORIO,
        "singleton": "roborio",
    },
]


def decode_frc_ext_id_full(arb_id: int) -> Tuple[int, int, int, int, int]:
    """
    NAME
        decode_frc_ext_id_full - Decode an FRC extended CAN arbitration ID.

    PARAMETERS
        arb_id: 29-bit arbitration ID (extended frame).

    RETURNS
        Tuple of (manufacturer, device_type, api_class, api_index, device_id).
    """
    # FRC extended CAN layout (common subset):
    # manufacturer: bits 16..23
    # device_type:  bits 24..28
    # api_class:    bits 10..15
    # api_index:    bits 6..9
    # device_id:    bits 0..5
    manufacturer = (arb_id >> 16) & 0xFF
    device_type = (arb_id >> 24) & 0x1F
    api_class = (arb_id >> 10) & 0x3F
    api_index = (arb_id >> 6) & 0x0F
    device_id = arb_id & 0x3F
    return manufacturer, device_type, api_class, api_index, device_id


def _rule_matches(
    rule: Dict[str, Any],
    manufacturer: int,
    device_type: int,
    api_class: int,
    api_index: int,
    pf: int,
    ps: int,
) -> bool:
    """
    NAME
        _rule_matches - Check rule table entry against a decoded frame.

    RETURNS
        True when all specified fields match the given identifiers.
    """
    if "mfg" in rule and manufacturer != rule["mfg"]:
        return False
    if "type" in rule and device_type != rule["type"]:
        return False
    if "api_class" in rule and api_class != rule["api_class"]:
        return False
    if "api_index_min" in rule and api_index < rule["api_index_min"]:
        return False
    if "api_index_max" in rule and api_index > rule["api_index_max"]:
        return False
    if "pf" in rule and pf != rule["pf"]:
        return False
    if "ps_max" in rule and ps > rule["ps_max"]:
        return False
    if "ps_min" in rule and ps < rule["ps_min"]:
        return False
    return True


def classify_frame(
    arb_id: int,
    manufacturer: int,
    device_type: int,
    api_class: int,
    api_index: int,
) -> Tuple[bool, bool]:
    """
    NAME
        classify_frame - Heuristically label a frame as status/control.

    PARAMETERS
        arb_id: Arbitration ID for PF/PS decoding.
        manufacturer, device_type, api_class, api_index: Decoded identifiers.

    RETURNS
        (is_status, is_control) booleans based on rule tables.

    NOTES
        Classification is heuristic and aligned with the dissector rules.
    """
    # Heuristics aligned with the Wireshark dissector (unverified).
    pf = (arb_id >> 16) & 0xFF
    ps = (arb_id >> 8) & 0xFF
    is_status = any(
        _rule_matches(rule, manufacturer, device_type, api_class, api_index, pf, ps)
        for rule in STATUS_RULES
    )
    is_control = any(
        _rule_matches(rule, manufacturer, device_type, api_class, api_index, pf, ps)
        for rule in CONTROL_RULES
    )
    return is_status, is_control


def uses_status_presence(manufacturer: int, device_type: int) -> bool:
    """
    NAME
        uses_status_presence - Indicate if status frames drive presence.

    DESCRIPTION
        Allows vendors/device types to prefer status frames for presence
        confidence.
    """
    return True
