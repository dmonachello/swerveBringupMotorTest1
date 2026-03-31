from __future__ import annotations

"""
NAME
    motor_diag_rules.py - Diagnosis rules for normalized motor telemetry.

SYNOPSIS
    from tools.can_nt.motor_diag_rules import diagnose_motor

DESCRIPTION
    Applies deterministic rules to normalized motor telemetry and produces
    ranked causes with evidence.
"""

from typing import List, Optional

from tools.can_nt.motor_diag_constants import (
    APPLIED_V_MIN,
    BRACKET_CLOSE,
    BRACKET_OPEN,
    BUS_V_LOW,
    CAUSE_CAN_BUS_ISSUE,
    CAUSE_CONFIG_MISMATCH,
    CAUSE_CONTROLLER_FAULT,
    CAUSE_LIMIT_ACTIVE,
    CAUSE_LOW_CURRENT,
    CAUSE_POWER_DISTRIBUTION_FAULT,
    CAUSE_NO_MOTION,
    CAUSE_NO_POWER,
    CAUSE_NOT_COMMANDED,
    CAUSE_ORDER,
    CAUSE_STALL,
    CAUSE_UNKNOWN,
    CONF_HIGH,
    CONF_LOW,
    CONF_MED,
    FIELD_FAULT_FLAGS,
    FIELD_FAULT_STATUS,
    FIELD_LAST_ERROR,
    FIELD_APPLIED_DUTY,
    FIELD_APPLIED_V,
    FIELD_BUS_V,
    FIELD_CMD_DUTY,
    FIELD_LIMIT,
    FIELD_MOTOR_CURRENT_A,
    FIELD_PROFILE_MISSING,
    FIELD_STICKY_FAULT_FLAGS,
    FIELD_STICKY_STATUS,
    FIELD_STICKY_WARNING_FLAGS,
    FIELD_THRESHOLD,
    FIELD_WARNING_FLAGS,
    FIELD_VEL_RPM,
    FLOAT_ZERO,
    LOW_CURRENT_FACTOR,
    LOW_CURRENT_FALLBACK,
    MAX_CAUSES,
    MOTION_EPS_RPM,
    SEP_COMMA_SPACE,
    SEP_EQ,
    STALL_FACTOR,
    STR_EMPTY,
    STR_KOK,
    KEY_PRESENT,
    TEXT_FALSE,
    TEXT_TRUE,
)
from tools.can_nt.motor_diag_model import DiagnosisFinding, DiagnosisReport, NormalizedMotorTelemetry
from tools.can_nt.power_diag_model import PowerDistributionTelemetry
from tools.can_nt.power_diag_constants import FIELD_BROWNOUT, FLAG_BROWNOUT


def diagnose_motor(
    telemetry: NormalizedMotorTelemetry,
    profile_labels: List[str],
    power_devices: List[PowerDistributionTelemetry],
) -> DiagnosisReport:
    """
    NAME
        diagnose_motor - Evaluate diagnosis rules for a motor telemetry record.

    PARAMETERS
        telemetry - Normalized motor telemetry.
        profile_labels - Active profile labels (lower-cased).
        power_devices - Normalized PDH/PDP telemetry list.

    RETURNS
        DiagnosisReport containing ranked causes and findings.
    """
    report = DiagnosisReport()
    if telemetry.present is False:
        report.causes.append(_cause(CAUSE_CAN_BUS_ISSUE, CONF_HIGH, [_ev_present(False)]))
        return _rank_report(report)

    _append_controller_faults(report, telemetry)
    _append_power_distribution_faults(report, power_devices)
    _append_no_power(report, telemetry, power_devices)
    _append_not_commanded(report, telemetry)
    _append_limit_active(report, telemetry)
    _append_no_motion(report, telemetry)
    _append_low_current(report, telemetry)
    _append_stall(report, telemetry)
    _append_config_mismatch(report, telemetry, profile_labels)

    if not report.causes:
        report.causes.append(_cause(CAUSE_UNKNOWN, CONF_LOW, []))
        report.missing = _missing_fields(telemetry)
    return _rank_report(report)


def _append_controller_faults(
    report: DiagnosisReport, telemetry: NormalizedMotorTelemetry
) -> None:
    controller = telemetry.controller
    if _has_controller_fault(controller):
        evidence: List[str] = []
        if controller.last_error:
            evidence.append(_ev_pair(FIELD_LAST_ERROR, controller.last_error))
        if controller.fault_flags:
            evidence.append(_ev_list(FIELD_FAULT_FLAGS, controller.fault_flags))
        if controller.sticky_fault_flags:
            evidence.append(_ev_list(FIELD_STICKY_FAULT_FLAGS, controller.sticky_fault_flags))
        if controller.warning_flags:
            evidence.append(_ev_list(FIELD_WARNING_FLAGS, controller.warning_flags))
        if controller.sticky_warning_flags:
            evidence.append(_ev_list(FIELD_STICKY_WARNING_FLAGS, controller.sticky_warning_flags))
        if controller.fault_status:
            evidence.append(_ev_pair(FIELD_FAULT_STATUS, controller.fault_status))
        if controller.sticky_status:
            evidence.append(_ev_pair(FIELD_STICKY_STATUS, controller.sticky_status))
        report.causes.append(_cause(CAUSE_CONTROLLER_FAULT, CONF_HIGH, evidence))


def _append_no_power(
    report: DiagnosisReport,
    telemetry: NormalizedMotorTelemetry,
    power_devices: List[PowerDistributionTelemetry],
) -> None:
    bus_v = telemetry.power.bus_v
    if bus_v is not None and bus_v < BUS_V_LOW:
        report.causes.append(_cause(CAUSE_NO_POWER, CONF_HIGH, [_ev_pair(FIELD_BUS_V, bus_v)]))
        return
    power_bus_v, power_label = _min_power_bus_v(power_devices)
    if power_bus_v is not None and power_bus_v < BUS_V_LOW:
        label_field = _power_field_label(FIELD_BUS_V, power_label or STR_EMPTY)
        report.causes.append(
            _cause(CAUSE_NO_POWER, CONF_HIGH, [_ev_pair(label_field, power_bus_v)])
        )
        return
    if _power_brownout(power_devices):
        report.causes.append(
            _cause(CAUSE_NO_POWER, CONF_HIGH, [_ev_pair(FIELD_BROWNOUT, TEXT_TRUE)])
        )


def _append_not_commanded(report: DiagnosisReport, telemetry: NormalizedMotorTelemetry) -> None:
    cmd = telemetry.power.cmd_duty
    applied = telemetry.power.applied_duty
    applied_v = telemetry.power.applied_v
    if _is_zero(cmd) and _is_zero(applied) and _is_zero(applied_v):
        report.causes.append(
            _cause(
                CAUSE_NOT_COMMANDED,
                CONF_HIGH,
                [
                    _ev_pair(FIELD_CMD_DUTY, cmd),
                    _ev_pair(FIELD_APPLIED_DUTY, applied),
                    _ev_pair(FIELD_APPLIED_V, applied_v),
                ],
            )
        )


def _append_limit_active(report: DiagnosisReport, telemetry: NormalizedMotorTelemetry) -> None:
    if not _motor_not_running(telemetry):
        return
    for limit in telemetry.limits:
        if limit.closed is True:
            label = limit.label or ""
            report.causes.append(
            _cause(CAUSE_LIMIT_ACTIVE, CONF_MED, [_ev_pair(FIELD_LIMIT, label)])
            )
            return


def _append_no_motion(report: DiagnosisReport, telemetry: NormalizedMotorTelemetry) -> None:
    if not _has_drive_evidence(telemetry):
        return
    applied_v = _effective_applied_v(telemetry)
    vel = telemetry.encoder.vel_rpm
    if vel is None:
        return
    if abs(vel) <= MOTION_EPS_RPM:
        evidence = []
        if applied_v is not None:
            evidence.append(_ev_pair(FIELD_APPLIED_V, applied_v))
        elif telemetry.power.applied_duty is not None:
            evidence.append(_ev_pair(FIELD_APPLIED_DUTY, telemetry.power.applied_duty))
        elif telemetry.power.cmd_duty is not None:
            evidence.append(_ev_pair(FIELD_CMD_DUTY, telemetry.power.cmd_duty))
        evidence.append(_ev_pair(FIELD_VEL_RPM, vel))
        report.causes.append(_cause(CAUSE_NO_MOTION, CONF_MED, evidence))


def _append_low_current(report: DiagnosisReport, telemetry: NormalizedMotorTelemetry) -> None:
    if not _has_drive_evidence(telemetry):
        return
    applied_v = _effective_applied_v(telemetry)
    current = telemetry.load.motor_current_a
    if applied_v is None or current is None:
        return
    if applied_v < APPLIED_V_MIN:
        return
    threshold = _low_current_threshold(telemetry)
    if current <= threshold:
        report.causes.append(
            _cause(
                CAUSE_LOW_CURRENT,
                CONF_MED,
                [
                    _ev_pair(FIELD_APPLIED_V, applied_v),
                    _ev_pair(FIELD_MOTOR_CURRENT_A, current),
                    _ev_pair(FIELD_THRESHOLD, threshold),
                ],
            )
        )


def _append_stall(report: DiagnosisReport, telemetry: NormalizedMotorTelemetry) -> None:
    if not _has_drive_evidence(telemetry):
        return
    applied_v = _effective_applied_v(telemetry)
    current = telemetry.load.motor_current_a
    if applied_v is None or current is None:
        return
    if applied_v < APPLIED_V_MIN:
        return
    threshold = _stall_threshold(telemetry)
    if threshold is None:
        return
    if current >= threshold:
        report.causes.append(
            _cause(
                CAUSE_STALL,
                CONF_MED,
                [
                    _ev_pair(FIELD_APPLIED_V, applied_v),
                    _ev_pair(FIELD_MOTOR_CURRENT_A, current),
                    _ev_pair(FIELD_THRESHOLD, threshold),
                ],
            )
        )


def _append_config_mismatch(
    report: DiagnosisReport, telemetry: NormalizedMotorTelemetry, profile_labels: List[str]
) -> None:
    label = telemetry.label or ""
    if not label:
        return
    if not profile_labels:
        return
    if label.lower() not in profile_labels:
        report.findings.append(
            _cause(
                CAUSE_CONFIG_MISMATCH,
                CONF_MED,
                [_ev_pair(FIELD_PROFILE_MISSING, TEXT_TRUE)],
            )
        )


def _rank_report(report: DiagnosisReport) -> DiagnosisReport:
    report.causes.sort(key=lambda item: _cause_rank(item.cause))
    if len(report.causes) > MAX_CAUSES:
        report.causes = report.causes[:MAX_CAUSES]
    return report


def _append_power_distribution_faults(
    report: DiagnosisReport, power_devices: List[PowerDistributionTelemetry]
) -> None:
    evidence: List[str] = []
    for device in power_devices:
        if not device.fault_flags and not device.sticky_fault_flags:
            continue
        label = device.label or STR_EMPTY
        if device.fault_flags:
            evidence.append(_ev_list(_power_field_label(FIELD_FAULT_FLAGS, label), device.fault_flags))
        if device.sticky_fault_flags:
            evidence.append(
                _ev_list(_power_field_label(FIELD_STICKY_FAULT_FLAGS, label), device.sticky_fault_flags)
            )
    if evidence:
        report.findings.append(_cause(CAUSE_POWER_DISTRIBUTION_FAULT, CONF_MED, evidence))


def _cause_rank(cause: str) -> int:
    if cause in CAUSE_ORDER:
        return CAUSE_ORDER.index(cause)
    return len(CAUSE_ORDER)


def _cause(cause: str, confidence: str, evidence: List[str]) -> DiagnosisFinding:
    return DiagnosisFinding(cause=cause, confidence=confidence, evidence=evidence)


def _has_controller_fault(controller) -> bool:
    if controller.last_error and controller.last_error.lower() != STR_KOK:
        return True
    if controller.fault_flags:
        return True
    if controller.sticky_fault_flags:
        return True
    if controller.warning_flags:
        return True
    if controller.sticky_warning_flags:
        return True
    if controller.fault_status:
        return True
    if controller.sticky_status:
        return True
    return False


def _has_drive_evidence(telemetry: NormalizedMotorTelemetry) -> bool:
    for value in (
        telemetry.power.applied_v,
        telemetry.power.applied_duty,
        telemetry.power.cmd_duty,
    ):
        if value is None:
            continue
        if abs(value) > FLOAT_ZERO:
            return True
    return False


def _effective_applied_v(telemetry: NormalizedMotorTelemetry) -> Optional[float]:
    if telemetry.power.applied_v is not None:
        return telemetry.power.applied_v
    if telemetry.power.bus_v is None or telemetry.power.applied_duty is None:
        return None
    return telemetry.power.bus_v * telemetry.power.applied_duty


def _motor_not_running(telemetry: NormalizedMotorTelemetry) -> bool:
    vel = telemetry.encoder.vel_rpm
    if vel is not None:
        return abs(vel) <= MOTION_EPS_RPM
    return False


def _low_current_threshold(telemetry: NormalizedMotorTelemetry) -> float:
    free_current = telemetry.spec.free_current_a
    if free_current is not None:
        return free_current * LOW_CURRENT_FACTOR
    return LOW_CURRENT_FALLBACK


def _stall_threshold(telemetry: NormalizedMotorTelemetry) -> Optional[float]:
    stall_current = telemetry.spec.stall_current_a
    if stall_current is None:
        return None
    return stall_current * STALL_FACTOR


def _missing_fields(telemetry: NormalizedMotorTelemetry) -> List[str]:
    fields: List[str] = []
    if telemetry.present is None:
        fields.append(KEY_PRESENT)
    if telemetry.power.applied_v is None:
        fields.append(FIELD_APPLIED_V)
    if telemetry.load.motor_current_a is None:
        fields.append(FIELD_MOTOR_CURRENT_A)
    if telemetry.power.cmd_duty is None:
        fields.append(FIELD_CMD_DUTY)
    if telemetry.power.applied_duty is None:
        fields.append(FIELD_APPLIED_DUTY)
    if telemetry.power.bus_v is None:
        fields.append(FIELD_BUS_V)
    if telemetry.encoder.vel_rpm is None:
        fields.append(FIELD_VEL_RPM)
    return fields


def _min_power_bus_v(
    power_devices: List[PowerDistributionTelemetry],
) -> tuple[Optional[float], Optional[str]]:
    pairs = [(dev.bus_v, dev.label) for dev in power_devices if dev.bus_v is not None]
    if not pairs:
        return (None, None)
    bus_v, label = min(pairs, key=lambda item: item[0])
    return (bus_v, label)


def _power_brownout(power_devices: List[PowerDistributionTelemetry]) -> bool:
    for device in power_devices:
        if FLAG_BROWNOUT in device.fault_flags:
            return True
        if FLAG_BROWNOUT in device.sticky_fault_flags:
            return True
    return False


def _power_field_label(field: str, label: str) -> str:
    if not label:
        return field
    return field + BRACKET_OPEN + label + BRACKET_CLOSE


def _ev_pair(field: str, value: Optional[object]) -> str:
    value_text = STR_EMPTY if value is None else str(value)
    return SEP_EQ.join([field, value_text])


def _ev_list(field: str, values: List[str]) -> str:
    joined = SEP_COMMA_SPACE.join(values)
    return SEP_EQ.join([field, BRACKET_OPEN + joined + BRACKET_CLOSE])


def _ev_present(present: bool) -> str:
    return _ev_pair(KEY_PRESENT, TEXT_TRUE if present else TEXT_FALSE)


def _is_zero(value: Optional[float]) -> bool:
    if value is None:
        return False
    return abs(value) <= FLOAT_ZERO
