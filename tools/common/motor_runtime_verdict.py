"""
NAME
    motor_runtime_verdict.py - Shared motor runtime motion/health interpretation helpers.

SYNOPSIS
    from tools.common.motor_runtime_verdict import infer_motor_runtime_verdict

DESCRIPTION
    Centralizes the operator-facing interpretation of runtime motor telemetry so
    Evidence and Live Topology group runs do not drift apart.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

ATTACHMENT_KEY_TYPE = "type"
ATTACHMENT_TYPE_REV_MOTOR = "revMotor"
ATTACHMENT_TYPE_CTRE_MOTOR = "ctreMotor"

RESULT_ROTATING = "rotating"
RESULT_NO_MOTION = "commanded no motion"
RESULT_STALLED = "stalled / bind suspect"
RESULT_ELECTRICAL = "electrical / output-path suspect"
RESULT_NOT_COMMANDED = "not commanded"
RESULT_CONFLICT = "conflict"
RESULT_MISSING = "missing"
RESULT_UNKNOWN = "unknown"


def runtime_motor_attachment(device: Dict[str, object]) -> Optional[Dict[str, object]]:
    """
    NAME
        runtime_motor_attachment - Return the first motor attachment from one runtime-state device payload.
    """
    if not isinstance(device, dict):
        return None
    attachments = device.get("attachments")
    if not isinstance(attachments, list):
        return None
    for attachment in attachments:
        if not isinstance(attachment, dict):
            continue
        attachment_type = str(attachment.get(ATTACHMENT_KEY_TYPE, "")).strip()
        if attachment_type in (ATTACHMENT_TYPE_REV_MOTOR, ATTACHMENT_TYPE_CTRE_MOTOR):
            return attachment
    return None


def _float_or_none(value: object) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _string_list(value: object) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(entry).strip() for entry in value if str(entry).strip()]


def infer_motor_runtime_verdict(
    *,
    present: bool,
    cmd_duty: object,
    applied_duty: object,
    applied_v: object,
    bus_v: object,
    vel_rpm: object,
    position_delta_rot: object,
    motor_current_a: object,
    attachment: Optional[Dict[str, object]] = None,
    duty_threshold: float,
    rpm_threshold: float,
    position_delta_threshold: float,
    current_active_threshold: float,
    low_bus_v_threshold: float,
    applied_v_active_threshold: float,
) -> Dict[str, object]:
    """
    NAME
        infer_motor_runtime_verdict - Fuse runtime motor telemetry into one shared operation/health verdict.
    """
    cmd_value = _float_or_none(cmd_duty)
    applied_duty_value = _float_or_none(applied_duty)
    applied_v_value = _float_or_none(applied_v)
    bus_v_value = _float_or_none(bus_v)
    vel_value = _float_or_none(vel_rpm)
    position_delta_value = _float_or_none(position_delta_rot)
    current_value = _float_or_none(motor_current_a)

    commanded = (
        cmd_value is not None and abs(cmd_value) >= duty_threshold
    ) or (
        applied_duty_value is not None and abs(applied_duty_value) >= duty_threshold
    ) or (
        applied_v_value is not None and abs(applied_v_value) >= applied_v_active_threshold
    )
    rotating = (
        vel_value is not None and abs(vel_value) >= rpm_threshold
    ) or (
        position_delta_value is not None and abs(position_delta_value) >= position_delta_threshold
    )
    current_active = current_value is not None and abs(current_value) >= current_active_threshold

    notes: List[str] = []
    warnings: List[str] = []
    faults: List[str] = []
    reset_active = False
    last_error = ""
    if isinstance(attachment, dict):
        warnings.extend(_string_list(attachment.get("warningFlags")))
        warnings.extend(_string_list(attachment.get("stickyWarningFlags")))
        faults.extend(_string_list(attachment.get("faultFlags")))
        faults.extend(_string_list(attachment.get("stickyFaultFlags")))
        reset_active = bool(attachment.get("reset"))
        last_error = str(attachment.get("lastError", "")).strip()
    health_degraded = bool(warnings or faults or reset_active)

    if not present:
        result = RESULT_MISSING
    elif commanded and rotating:
        result = RESULT_ROTATING
    elif commanded and current_active:
        result = RESULT_STALLED
    elif commanded:
        result = RESULT_ELECTRICAL
    elif rotating:
        result = RESULT_CONFLICT
    elif present:
        result = RESULT_NOT_COMMANDED
    else:
        result = RESULT_UNKNOWN

    if result == RESULT_STALLED:
        notes.append("Commanded with current draw but no motion.")
    elif result == RESULT_ELECTRICAL:
        notes.append("Commanded with little current and no motion.")
    elif result == RESULT_ROTATING:
        notes.append("Motion detected from internal sensor telemetry.")
    elif result == RESULT_CONFLICT:
        notes.append("Motion detected without a matching command.")

    if bus_v_value is not None and bus_v_value < low_bus_v_threshold:
        notes.append("Low bus voltage may affect operation.")
        health_degraded = True
    if last_error and last_error != "kOk":
        notes.append(f"Controller error: {last_error}")
        health_degraded = True
    if reset_active:
        notes.append("Controller reported reset.")
    if faults:
        notes.append("Faults: " + ", ".join(faults))
    if warnings:
        notes.append("Warnings: " + ", ".join(warnings))

    return {
        "present": present,
        "commanded": commanded,
        "rotating": rotating,
        "currentActive": current_active,
        "result": result,
        "healthDegraded": health_degraded,
        "notes": notes,
    }
