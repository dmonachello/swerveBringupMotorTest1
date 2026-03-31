from __future__ import annotations

"""
NAME
    motor_diag_normalize.py - Normalize runtime state for motor diagnosis.

SYNOPSIS
    from tools.can_nt.motor_diag_normalize import normalize_runtime_state

DESCRIPTION
    Resolves device labels and maps runtime-state payloads into a
    vendor-agnostic motor telemetry record.
"""

from typing import Any, Dict, Iterable, List, Optional

from tools.can_nt.motor_diag_constants import (
    ATTACHMENT_CTRE_MOTOR,
    ATTACHMENT_ENCODER,
    ATTACHMENT_LIMITS,
    ATTACHMENT_MOTOR_SPEC,
    ATTACHMENT_REV_MOTOR,
    FIELD_ABS_DEG,
    FIELD_APPLIED_DUTY,
    FIELD_APPLIED_V,
    FIELD_BUS_V,
    FIELD_CMD_DUTY,
    FIELD_CLOSED,
    FIELD_DIO,
    FIELD_FAULTS_RAW,
    FIELD_FAULT_FLAGS,
    FIELD_FAULT_STATUS,
    FIELD_FREE_CURRENT_A,
    FIELD_HEALTH_NOTE,
    FIELD_INVERT,
    FIELD_LAST_ERROR,
    FIELD_LOW_CURRENT_NOTE,
    FIELD_MODEL,
    FIELD_MOTOR_CURRENT_A,
    FIELD_MOTOR_V,
    FIELD_NOMINAL_V,
    FIELD_RESET,
    FIELD_STALL_CURRENT_A,
    FIELD_STICKY_FAULTS_RAW,
    FIELD_STICKY_FAULT_FLAGS,
    FIELD_STICKY_STATUS,
    FIELD_STICKY_WARNINGS_RAW,
    FIELD_STICKY_WARNING_FLAGS,
    FIELD_SWITCHES,
    FIELD_TEMP_C,
    FIELD_VEL_RPM,
    FIELD_WARNING_FLAGS,
    FIELD_WARNINGS_RAW,
    FLOAT_ZERO,
    INT_ONE,
    INT_ZERO,
    KEY_ATTACHMENT_TYPE,
    KEY_ATTACHMENTS,
    KEY_DEVICES,
    KEY_LABEL,
    KEY_NOTE,
    KEY_PRESENT,
    KEY_PRESENCE_CONF,
    KEY_VENDOR,
    STR_EMPTY,
    VENDOR_CTRE,
    VENDOR_REV,
    VENDOR_UNKNOWN,
)
from tools.common.profile_constants import KEY_PROFILES, KEY_PROFILE_DEVICES
from tools.can_nt.motor_diag_model import (
    ControllerState,
    EncoderState,
    LimitState,
    LoadState,
    MotorSpec,
    NormalizeResult,
    NormalizedMotorTelemetry,
    NotesState,
    PowerState,
)


def normalize_runtime_state(state: Dict[str, Any], label: str) -> NormalizeResult:
    """
    NAME
        normalize_runtime_state - Resolve a label and normalize a device entry.

    PARAMETERS
        state - Runtime-state JSON payload.
        label - Device label to diagnose.

    RETURNS
        NormalizeResult containing telemetry or errors.
    """
    devices = _device_entries(state)
    labels = _device_labels(devices)
    resolved, candidates = _resolve_label(labels, label)
    result = NormalizeResult()
    result.candidates = candidates
    if resolved is None:
        return result
    entry = _entry_by_label(devices, resolved)
    if entry is None:
        return result
    result.telemetry = _normalize_entry(entry)
    return result


def collect_profile_labels(payload: Optional[Dict[str, Any]], profile: Optional[str]) -> List[str]:
    """
    NAME
        collect_profile_labels - Return normalized labels from a profile payload.

    PARAMETERS
        payload - Local profiles payload (bringup_system.json).
        profile - Active profile name.

    RETURNS
        List of lower-cased labels.
    """
    if not isinstance(payload, dict) or not profile:
        return []
    profiles = payload.get(KEY_PROFILES)
    if not isinstance(profiles, dict):
        return []
    entry = profiles.get(profile)
    if not isinstance(entry, dict):
        return []
    labels = entry.get(KEY_PROFILE_DEVICES)
    if not isinstance(labels, list):
        return []
    return [str(item).strip().lower() for item in labels if isinstance(item, str)]


def _device_entries(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    entries = state.get(KEY_DEVICES)
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def _device_labels(entries: Iterable[Dict[str, Any]]) -> List[str]:
    labels: List[str] = []
    for entry in entries:
        label = str(entry.get(KEY_LABEL, STR_EMPTY)).strip()
        if label:
            labels.append(label)
    return labels


def _resolve_label(labels: List[str], target: str) -> tuple[Optional[str], List[str]]:
    if not target:
        return (None, [])
    exact = [label for label in labels if label == target]
    if len(exact) == INT_ONE:
        return (exact[INT_ZERO], [])
    if len(exact) > INT_ONE:
        return (None, sorted(exact))
    lowered = target.lower()
    matches = [label for label in labels if label.lower() == lowered]
    if len(matches) == INT_ONE:
        return (matches[INT_ZERO], [])
    if len(matches) > INT_ONE:
        return (None, sorted(matches))
    return (None, [])


def _entry_by_label(entries: Iterable[Dict[str, Any]], label: str) -> Optional[Dict[str, Any]]:
    if not label:
        return None
    lower = label.lower()
    for entry in entries:
        name = str(entry.get(KEY_LABEL, STR_EMPTY)).strip()
        if name.lower() == lower:
            return entry
    return None


def _normalize_entry(entry: Dict[str, Any]) -> NormalizedMotorTelemetry:
    telemetry = NormalizedMotorTelemetry()
    telemetry.label = str(entry.get(KEY_LABEL, STR_EMPTY)).strip()
    vendor = str(entry.get(KEY_VENDOR, STR_EMPTY)).strip()
    telemetry.vendor = vendor or VENDOR_UNKNOWN
    telemetry.present = _present_from_entry(entry)

    telemetry.power = PowerState()
    telemetry.load = LoadState()
    telemetry.controller = ControllerState()
    telemetry.encoder = EncoderState()
    telemetry.spec = MotorSpec()
    telemetry.notes = NotesState()

    _map_flat_fields(entry, telemetry)
    _map_attachments(entry, telemetry)
    return telemetry


def _present_from_entry(entry: Dict[str, Any]) -> Optional[bool]:
    if KEY_PRESENT in entry:
        return bool(entry.get(KEY_PRESENT))
    conf = entry.get(KEY_PRESENCE_CONF)
    if isinstance(conf, (int, float)):
        return conf > FLOAT_ZERO
    return None


def _map_flat_fields(entry: Dict[str, Any], telemetry: NormalizedMotorTelemetry) -> None:
    if FIELD_BUS_V in entry:
        telemetry.power.bus_v = _as_float(entry.get(FIELD_BUS_V))
    if FIELD_APPLIED_DUTY in entry:
        telemetry.power.applied_duty = _as_float(entry.get(FIELD_APPLIED_DUTY))
    if FIELD_APPLIED_V in entry:
        telemetry.power.applied_v = _as_float(entry.get(FIELD_APPLIED_V))
    if FIELD_CMD_DUTY in entry:
        telemetry.power.cmd_duty = _as_float(entry.get(FIELD_CMD_DUTY))
    if FIELD_MOTOR_CURRENT_A in entry:
        telemetry.load.motor_current_a = _as_float(entry.get(FIELD_MOTOR_CURRENT_A))
    if FIELD_TEMP_C in entry:
        telemetry.load.temp_c = _as_float(entry.get(FIELD_TEMP_C))
    if FIELD_MOTOR_V in entry:
        telemetry.power.motor_v = _as_float(entry.get(FIELD_MOTOR_V))
    if FIELD_VEL_RPM in entry:
        telemetry.encoder.vel_rpm = _as_float(entry.get(FIELD_VEL_RPM))
    if KEY_NOTE in entry:
        telemetry.notes.snapshot_note = str(entry.get(KEY_NOTE, STR_EMPTY)).strip() or None


def _map_attachments(entry: Dict[str, Any], telemetry: NormalizedMotorTelemetry) -> None:
    attachments = entry.get(KEY_ATTACHMENTS)
    if not isinstance(attachments, list):
        return
    for attachment in attachments:
        if not isinstance(attachment, dict):
            continue
        atype = str(attachment.get(KEY_ATTACHMENT_TYPE, STR_EMPTY)).strip()
        if atype == ATTACHMENT_REV_MOTOR:
            _map_rev_attachment(attachment, telemetry)
        elif atype == ATTACHMENT_CTRE_MOTOR:
            _map_ctre_attachment(attachment, telemetry)
        elif atype == ATTACHMENT_LIMITS:
            _map_limits_attachment(attachment, telemetry)
        elif atype == ATTACHMENT_ENCODER:
            _map_encoder_attachment(attachment, telemetry)
        elif atype == ATTACHMENT_MOTOR_SPEC:
            _map_motor_spec_attachment(attachment, telemetry)


def _map_rev_attachment(attachment: Dict[str, Any], telemetry: NormalizedMotorTelemetry) -> None:
    telemetry.vendor = VENDOR_REV
    _map_controller_fields(attachment, telemetry)
    _map_power_fields(attachment, telemetry)
    _map_load_fields(attachment, telemetry)
    if telemetry.encoder.vel_rpm is None and FIELD_VEL_RPM in attachment:
        telemetry.encoder.vel_rpm = _as_float(attachment.get(FIELD_VEL_RPM))
    if FIELD_HEALTH_NOTE in attachment:
        telemetry.notes.health_note = str(attachment.get(FIELD_HEALTH_NOTE, STR_EMPTY)).strip() or None
    if FIELD_LOW_CURRENT_NOTE in attachment:
        telemetry.notes.low_current_note = str(attachment.get(FIELD_LOW_CURRENT_NOTE, STR_EMPTY)).strip() or None


def _map_ctre_attachment(attachment: Dict[str, Any], telemetry: NormalizedMotorTelemetry) -> None:
    telemetry.vendor = VENDOR_CTRE
    _map_controller_fields(attachment, telemetry)
    _map_power_fields(attachment, telemetry)
    _map_load_fields(attachment, telemetry)
    if telemetry.encoder.vel_rpm is None and FIELD_VEL_RPM in attachment:
        telemetry.encoder.vel_rpm = _as_float(attachment.get(FIELD_VEL_RPM))


def _map_limits_attachment(attachment: Dict[str, Any], telemetry: NormalizedMotorTelemetry) -> None:
    switches = attachment.get(FIELD_SWITCHES)
    if not isinstance(switches, list):
        return
    for switch in switches:
        if not isinstance(switch, dict):
            continue
        state = LimitState()
        state.label = str(switch.get(KEY_LABEL, STR_EMPTY)).strip() or None
        state.dio = _as_int(switch.get(FIELD_DIO))
        state.invert = _as_bool(switch.get(FIELD_INVERT))
        state.closed = _as_bool(switch.get(FIELD_CLOSED))
        telemetry.limits.append(state)


def _map_encoder_attachment(attachment: Dict[str, Any], telemetry: NormalizedMotorTelemetry) -> None:
    telemetry.encoder.abs_deg = _as_float(attachment.get(FIELD_ABS_DEG))
    telemetry.encoder.vel_rpm = _as_float(attachment.get(FIELD_VEL_RPM))
    if FIELD_LAST_ERROR in attachment:
        telemetry.encoder.last_error = str(attachment.get(FIELD_LAST_ERROR, STR_EMPTY)).strip() or None


def _map_motor_spec_attachment(attachment: Dict[str, Any], telemetry: NormalizedMotorTelemetry) -> None:
    telemetry.spec.model = str(attachment.get(FIELD_MODEL, STR_EMPTY)).strip() or None
    telemetry.spec.nominal_v = _as_float(attachment.get(FIELD_NOMINAL_V))
    telemetry.spec.free_current_a = _as_float(attachment.get(FIELD_FREE_CURRENT_A))
    telemetry.spec.stall_current_a = _as_float(attachment.get(FIELD_STALL_CURRENT_A))


def _map_controller_fields(attachment: Dict[str, Any], telemetry: NormalizedMotorTelemetry) -> None:
    controller = telemetry.controller
    if FIELD_LAST_ERROR in attachment:
        controller.last_error = str(attachment.get(FIELD_LAST_ERROR, STR_EMPTY)).strip() or None
    controller.faults_raw = _as_int(attachment.get(FIELD_FAULTS_RAW))
    controller.sticky_faults_raw = _as_int(attachment.get(FIELD_STICKY_FAULTS_RAW))
    controller.warnings_raw = _as_int(attachment.get(FIELD_WARNINGS_RAW))
    controller.sticky_warnings_raw = _as_int(attachment.get(FIELD_STICKY_WARNINGS_RAW))
    controller.fault_flags = _as_str_list(attachment.get(FIELD_FAULT_FLAGS))
    controller.sticky_fault_flags = _as_str_list(attachment.get(FIELD_STICKY_FAULT_FLAGS))
    controller.warning_flags = _as_str_list(attachment.get(FIELD_WARNING_FLAGS))
    controller.sticky_warning_flags = _as_str_list(attachment.get(FIELD_STICKY_WARNING_FLAGS))
    if FIELD_FAULT_STATUS in attachment:
        controller.fault_status = str(attachment.get(FIELD_FAULT_STATUS, STR_EMPTY)).strip() or None
    if FIELD_STICKY_STATUS in attachment:
        controller.sticky_status = str(attachment.get(FIELD_STICKY_STATUS, STR_EMPTY)).strip() or None
    controller.reset = _as_bool(attachment.get(FIELD_RESET))


def _map_power_fields(attachment: Dict[str, Any], telemetry: NormalizedMotorTelemetry) -> None:
    power = telemetry.power
    power.bus_v = _first_float(power.bus_v, attachment.get(FIELD_BUS_V))
    power.applied_duty = _first_float(power.applied_duty, attachment.get(FIELD_APPLIED_DUTY))
    power.applied_v = _first_float(power.applied_v, attachment.get(FIELD_APPLIED_V))
    power.cmd_duty = _first_float(power.cmd_duty, attachment.get(FIELD_CMD_DUTY))
    power.motor_v = _first_float(power.motor_v, attachment.get(FIELD_MOTOR_V))


def _map_load_fields(attachment: Dict[str, Any], telemetry: NormalizedMotorTelemetry) -> None:
    load = telemetry.load
    load.motor_current_a = _first_float(load.motor_current_a, attachment.get(FIELD_MOTOR_CURRENT_A))
    load.temp_c = _first_float(load.temp_c, attachment.get(FIELD_TEMP_C))


def _as_float(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _as_int(value: Any) -> Optional[int]:
    if isinstance(value, int):
        return value
    return None


def _as_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    return None


def _as_str_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    items: List[str] = []
    for entry in value:
        if isinstance(entry, str):
            items.append(entry)
    return items


def _first_float(current: Optional[float], candidate: Any) -> Optional[float]:
    if current is not None:
        return current
    return _as_float(candidate)
