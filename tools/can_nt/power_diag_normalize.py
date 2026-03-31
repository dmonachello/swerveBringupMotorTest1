from __future__ import annotations

"""
NAME
    power_diag_normalize.py - Normalize PDH/PDP runtime-state payloads.

SYNOPSIS
    from tools.can_nt.power_diag_normalize import normalize_power_distribution

DESCRIPTION
    Extracts PDH/PDP telemetry from runtime-state JSON payloads and produces
    vendor-agnostic power distribution records.
"""

from typing import Any, Dict, List, Optional

from tools.can_nt.power_diag_constants import (
    FIELD_BROWNOUT,
    FIELD_BUS_V,
    FIELD_CAN_WARNING,
    FIELD_CHANNEL_CURRENT_A,
    FIELD_CHANNEL_FAULT,
    FIELD_CHANNEL_STICKY_FAULT,
    FIELD_HARDWARE_FAULT,
    FIELD_STICKY_BROWNOUT,
    FIELD_STICKY_CAN_BUS_OFF,
    FIELD_STICKY_CAN_WARNING,
    FIELD_STICKY_HAS_RESET,
    FIELD_SWITCHABLE_ENABLED,
    FIELD_TEMP_C,
    FIELD_TOTAL_CURRENT_A,
    FLAG_BROWNOUT,
    FLAG_CAN_BUS_OFF,
    FLAG_CAN_WARNING,
    FLAG_HAS_RESET,
    FLAG_HARDWARE_FAULT,
    FLOAT_ZERO,
    KEY_DEVICES,
    KEY_LABEL,
    KEY_PRESENT,
    KEY_PRESENCE_CONF,
    KEY_TYPE,
    KEY_VENDOR,
    STR_EMPTY,
    TYPE_PDH,
    TYPE_PDP,
)
from tools.can_nt.power_diag_model import PowerDistributionTelemetry


def normalize_power_distribution(state: Dict[str, Any]) -> List[PowerDistributionTelemetry]:
    """
    NAME
        normalize_power_distribution - Extract PDH/PDP telemetry entries.

    PARAMETERS
        state - Runtime-state JSON payload.

    RETURNS
        List of PowerDistributionTelemetry entries.
    """
    devices = state.get(KEY_DEVICES)
    if not isinstance(devices, list):
        return []
    telemetry: List[PowerDistributionTelemetry] = []
    for entry in devices:
        if not isinstance(entry, dict):
            continue
        device_type = str(entry.get(KEY_TYPE, STR_EMPTY)).strip()
        if device_type not in (TYPE_PDH, TYPE_PDP):
            continue
        record = _normalize_entry(entry)
        if record is not None:
            telemetry.append(record)
    return telemetry


def _normalize_entry(entry: Dict[str, Any]) -> Optional[PowerDistributionTelemetry]:
    record = PowerDistributionTelemetry()
    record.label = str(entry.get(KEY_LABEL, STR_EMPTY)).strip() or None
    record.device_type = str(entry.get(KEY_TYPE, STR_EMPTY)).strip() or None
    record.vendor = str(entry.get(KEY_VENDOR, STR_EMPTY)).strip() or None
    record.present = _present_from_entry(entry)
    record.bus_v = _as_float(entry.get(FIELD_BUS_V))
    record.total_current_a = _as_float(entry.get(FIELD_TOTAL_CURRENT_A))
    record.temperature_c = _as_float(entry.get(FIELD_TEMP_C))
    record.switchable_enabled = _as_bool(entry.get(FIELD_SWITCHABLE_ENABLED))
    record.fault_flags = _collect_fault_flags(entry, sticky=False)
    record.sticky_fault_flags = _collect_fault_flags(entry, sticky=True)
    record.channel_current_a = _as_float_list(entry.get(FIELD_CHANNEL_CURRENT_A))
    record.channel_fault = _as_bool_list(entry.get(FIELD_CHANNEL_FAULT))
    record.channel_sticky_fault = _as_bool_list(entry.get(FIELD_CHANNEL_STICKY_FAULT))
    return record


def _present_from_entry(entry: Dict[str, Any]) -> Optional[bool]:
    if KEY_PRESENT in entry:
        return bool(entry.get(KEY_PRESENT))
    conf = entry.get(KEY_PRESENCE_CONF)
    if isinstance(conf, (int, float)):
        return conf > FLOAT_ZERO
    return None


def _collect_fault_flags(entry: Dict[str, Any], *, sticky: bool) -> List[str]:
    flags: List[str] = []
    if sticky:
        mapping = (
            (FIELD_STICKY_BROWNOUT, FLAG_BROWNOUT),
            (FIELD_STICKY_CAN_WARNING, FLAG_CAN_WARNING),
            (FIELD_STICKY_CAN_BUS_OFF, FLAG_CAN_BUS_OFF),
            (FIELD_STICKY_HAS_RESET, FLAG_HAS_RESET),
        )
    else:
        mapping = (
            (FIELD_BROWNOUT, FLAG_BROWNOUT),
            (FIELD_CAN_WARNING, FLAG_CAN_WARNING),
            (FIELD_HARDWARE_FAULT, FLAG_HARDWARE_FAULT),
        )
    for key, label in mapping:
        if _as_bool(entry.get(key)):
            flags.append(label)
    return flags


def _as_float(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _as_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    return None


def _as_float_list(value: Any) -> List[float]:
    if not isinstance(value, list):
        return []
    out: List[float] = []
    for item in value:
        if isinstance(item, (int, float)):
            out.append(float(item))
    return out


def _as_bool_list(value: Any) -> List[bool]:
    if not isinstance(value, list):
        return []
    out: List[bool] = []
    for item in value:
        if isinstance(item, bool):
            out.append(item)
    return out
