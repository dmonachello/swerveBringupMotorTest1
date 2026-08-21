from __future__ import annotations

"""
NAME
    can_bus_report_service.py - Shared host-owned CAN bus diagnostics report builder.

SYNOPSIS
    from tools.can_nt.can_bus_report_service import build_host_can_bus_report

DESCRIPTION
    Builds one authoritative CAN diagnostics text report on the host by
    combining host-side visibility data with robot runtime-state JSON fetched
    over REST.
"""

import time
from typing import Any, Dict, List, Optional

from tools.can_nt.bridge_session import BridgeSession
from tools.can_nt.visibility_constants import (
    VIS_KEY_AVAILABLE,
    VIS_KEY_DEVICES,
    VIS_KEY_DEVICES_SHOWN,
    VIS_KEY_FRAMES_PER_SEC,
    VIS_KEY_ID,
    VIS_KEY_IDENTITY,
    VIS_KEY_LABEL,
    VIS_KEY_LAST_SEEN_MS,
    VIS_KEY_METRICS,
    VIS_KEY_MSG_COUNT,
    VIS_KEY_RAW_IDS,
    VIS_KEY_SOURCES,
    VIS_KEY_VISIBLE_ALL,
    VIS_KEY_VISIBLE_NONE,
    VIS_KEY_VISIBLE_SOME,
)
from tools.common.motor_runtime_verdict import runtime_motor_attachment

SECTION_REPORT = "=== CAN Bus Report (Host Assembled) ==="
SECTION_HOST = "Host Visibility:"
SECTION_DEFINED = "Defined Nodes:"
SECTION_UNRECOGNIZED = "Unrecognized Nodes:"
SECTION_ROBOT_BUS = "Robot CAN Bus Health:"
SECTION_ROBOT_DEVICES = "Robot Runtime Devices:"
SECTION_FOOTER = "===================================="
TEXT_NONE = "(none)"
TEXT_UNAVAILABLE = "unavailable"
TEXT_UNKNOWN = "UNKNOWN"
TEXT_TRUE = "YES"
TEXT_FALSE = "NO"
TEXT_VALID = "valid"
TEXT_INVALID = "invalid"
TEXT_DEFINED = "defined"
TEXT_UNRECOGNIZED = "unrecognized"
KEY_CAN_BUS = "canBus"
KEY_DEVICES = "devices"
KEY_ATTACHMENTS = "attachments"
KEY_TYPE = "type"
KEY_VENDOR = "vendor"
KEY_ID_RUNTIME = "id"
KEY_LABEL_RUNTIME = "label"
KEY_INSTANTIATED = "instantiated"
KEY_LIFECYCLE_STATE = "lifecycleState"
KEY_TESTABLE = "testable"
KEY_PRESENCE_CONFIDENCE = "presenceConfidence"
KEY_UTILIZATION_PCT = "utilizationPct"
KEY_RX_ERRORS = "rxErrors"
KEY_TX_ERRORS = "txErrors"
KEY_RX_DELTA = "rxDelta"
KEY_TX_DELTA = "txDelta"
KEY_TX_FULL = "txFull"
KEY_TX_FULL_DELTA = "txFullDelta"
KEY_BUS_OFF = "busOff"
KEY_BUS_OFF_DELTA = "busOffDelta"
KEY_SAMPLE_AGE_SEC = "sampleAgeSec"
KEY_UNEXPECTED = "unexpected"
KEY_BUS_V = "busV"
KEY_MOTOR_CURRENT_A = "motorCurrentA"
KEY_TEMP_C = "tempC"
KEY_CMD_DUTY = "cmdDuty"
KEY_APPLIED_DUTY = "appliedDuty"
KEY_APPLIED_V = "appliedV"
KEY_VEL_RPM = "velRpm"
KEY_POSITION_ROT = "positionRot"
KEY_WARNING_FLAGS = "warningFlags"
KEY_STICKY_WARNING_FLAGS = "stickyWarningFlags"
KEY_FAULT_FLAGS = "faultFlags"
KEY_STICKY_FAULT_FLAGS = "stickyFaultFlags"
KEY_LAST_ERROR = "lastError"
KEY_RESET = "reset"
KEY_MATCHED = "matched"
KEY_MODEL = "model"
KEY_REQUESTED_MODEL = "requestedModel"
ATTACHMENT_TYPE_PDP_STATUS = "pdpStatus"
ATTACHMENT_TYPE_PDH_STATUS = "pdhStatus"
ATTACHMENT_TYPE_MOTOR_SPEC = "motorSpec"
KEY_SWITCHABLE_ENABLED = "switchableEnabled"
KEY_TOTAL_CURRENT_A = "totalCurrentA"
FLOAT_PACKETS_SCALE = 0
FLOAT_RATE_SCALE = 1
FLOAT_SMALL_SCALE = 2
FLOAT_CURRENT_SCALE = 3
FLOAT_TEMP_SCALE = 1
FLOAT_POS_SCALE = 3
VISIBILITY_SCOPE = "both"
MS_PER_SEC = 1000.0
MAX_RAW_IDS_TO_SHOW = 3
EMPTY_LIST: List[str] = []


def _float_or_none(value: object) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _bool_text(value: object) -> str:
    return TEXT_TRUE if bool(value) else TEXT_FALSE


def _format_float(value: object, scale: int, suffix: str = "") -> str:
    number = _float_or_none(value)
    if number is None:
        return TEXT_UNAVAILABLE
    return f"{number:.{scale}f}{suffix}"


def _format_packet_count(value: object) -> str:
    number = _float_or_none(value)
    if number is None:
        return TEXT_UNAVAILABLE
    return f"{number:.{FLOAT_PACKETS_SCALE}f}"


def _format_age_ms(last_seen_ms: object, now_ms: int) -> str:
    number = _float_or_none(last_seen_ms)
    if number is None or number <= 0.0:
        return TEXT_UNAVAILABLE
    age_sec = max(0.0, (float(now_ms) - number) / MS_PER_SEC)
    return f"{age_sec:.{FLOAT_SMALL_SCALE}f}s"


def _string_list(value: object) -> List[str]:
    if not isinstance(value, list):
        return EMPTY_LIST
    return [str(item).strip() for item in value if str(item).strip()]


def _attachment_flags(attachment: Dict[str, object]) -> List[str]:
    parts: List[str] = []
    for key in (
        KEY_WARNING_FLAGS,
        KEY_STICKY_WARNING_FLAGS,
        KEY_FAULT_FLAGS,
        KEY_STICKY_FAULT_FLAGS,
    ):
        values = _string_list(attachment.get(key))
        if values:
            parts.append(f"{key}=" + ",".join(values))
    last_error = str(attachment.get(KEY_LAST_ERROR, "")).strip()
    if last_error and last_error != "kOk":
        parts.append(f"{KEY_LAST_ERROR}={last_error}")
    if bool(attachment.get(KEY_RESET, False)):
        parts.append("reset=YES")
    return parts


def _device_runtime_line(device: Dict[str, object]) -> str:
    label = str(device.get(KEY_LABEL_RUNTIME, TEXT_UNKNOWN)).strip() or TEXT_UNKNOWN
    vendor = str(device.get(KEY_VENDOR, TEXT_UNKNOWN)).strip() or TEXT_UNKNOWN
    device_type = str(device.get(KEY_TYPE, TEXT_UNKNOWN)).strip() or TEXT_UNKNOWN
    device_id = str(device.get(KEY_ID_RUNTIME, TEXT_UNKNOWN)).strip() or TEXT_UNKNOWN
    instantiated = _bool_text(device.get(KEY_INSTANTIATED, False))
    lifecycle_state = str(device.get(KEY_LIFECYCLE_STATE, TEXT_UNKNOWN)).strip() or TEXT_UNKNOWN
    testable = _bool_text(device.get(KEY_TESTABLE, False))
    presence = _format_float(device.get(KEY_PRESENCE_CONFIDENCE), FLOAT_SMALL_SCALE)
    return (
        f"  {label} vendor={vendor} type={device_type} id={device_id}"
        f" instantiated={instantiated} lifecycleState={lifecycle_state}"
        f" testable={testable} presence={presence}"
    )


def _device_detail_lines(device: Dict[str, object]) -> List[str]:
    details: List[str] = []
    attachment = runtime_motor_attachment(device)
    spec_line = _motor_spec_detail_line(device)
    if isinstance(attachment, dict):
        motor_bits = [
            f"{KEY_CMD_DUTY}={_format_float(attachment.get(KEY_CMD_DUTY), FLOAT_SMALL_SCALE)}",
            f"{KEY_APPLIED_DUTY}={_format_float(attachment.get(KEY_APPLIED_DUTY), FLOAT_SMALL_SCALE)}",
            f"{KEY_APPLIED_V}={_format_float(attachment.get(KEY_APPLIED_V), FLOAT_SMALL_SCALE, 'V')}",
            f"{KEY_BUS_V}={_format_float(attachment.get(KEY_BUS_V), FLOAT_SMALL_SCALE, 'V')}",
            f"{KEY_MOTOR_CURRENT_A}={_format_float(attachment.get(KEY_MOTOR_CURRENT_A), FLOAT_CURRENT_SCALE, 'A')}",
            f"{KEY_TEMP_C}={_format_float(attachment.get(KEY_TEMP_C), FLOAT_TEMP_SCALE, 'C')}",
            f"{KEY_VEL_RPM}={_format_float(device.get(KEY_VEL_RPM), FLOAT_SMALL_SCALE, 'rpm')}",
            f"{KEY_POSITION_ROT}={_format_float(device.get(KEY_POSITION_ROT), FLOAT_POS_SCALE, 'rot')}",
        ]
        details.append("    motor: " + " ".join(motor_bits))
        flag_bits = _attachment_flags(attachment)
        if flag_bits:
            details.append("    flags: " + " ".join(flag_bits))
        if spec_line:
            details.append(spec_line)
        return details
    attachments = device.get(KEY_ATTACHMENTS)
    if isinstance(attachments, list):
        for attachment_entry in attachments:
            if not isinstance(attachment_entry, dict):
                continue
            attachment_type = str(attachment_entry.get(KEY_TYPE, "")).strip()
            if attachment_type == ATTACHMENT_TYPE_PDP_STATUS:
                details.append(
                    "    pdp: totalCurrentA="
                    + _format_float(attachment_entry.get(KEY_TOTAL_CURRENT_A), FLOAT_CURRENT_SCALE, "A")
                )
            elif attachment_type == ATTACHMENT_TYPE_PDH_STATUS:
                details.append(
                    "    pdh: totalCurrentA="
                    + _format_float(attachment_entry.get(KEY_TOTAL_CURRENT_A), FLOAT_CURRENT_SCALE, "A")
                    + " switchableEnabled="
                    + _bool_text(attachment_entry.get(KEY_SWITCHABLE_ENABLED, False))
                )
    if spec_line:
        details.append(spec_line)
    return details


def _motor_spec_detail_line(device: Dict[str, object]) -> str:
    attachment = _motor_spec_attachment(device)
    if not isinstance(attachment, dict):
        return ""
    if not bool(attachment.get(KEY_MATCHED, False)):
        requested_model = str(attachment.get(KEY_REQUESTED_MODEL, "")).strip()
        if requested_model:
            return f"    motorSpec: matched=NO requestedModel={requested_model}"
        return "    motorSpec: matched=NO"
    model = str(attachment.get(KEY_MODEL, "")).strip()
    if not model:
        return ""
    return f"    motorSpec: matched=YES model={model}"


def _motor_spec_attachment(device: Dict[str, object]) -> Optional[Dict[str, object]]:
    attachments = device.get(KEY_ATTACHMENTS)
    if not isinstance(attachments, list):
        return None
    for attachment in attachments:
        if not isinstance(attachment, dict):
            continue
        if str(attachment.get(KEY_TYPE, "")).strip() == ATTACHMENT_TYPE_MOTOR_SPEC:
            return attachment
    return None


def _visibility_row_line(device: Dict[str, object], now_ms: int) -> str:
    label = str(device.get(VIS_KEY_LABEL, TEXT_UNKNOWN)).strip() or TEXT_UNKNOWN
    identity = str(device.get(VIS_KEY_IDENTITY, TEXT_UNKNOWN)).strip() or TEXT_UNKNOWN
    metrics = device.get(VIS_KEY_METRICS) if isinstance(device.get(VIS_KEY_METRICS), dict) else {}
    last_seen = _format_age_ms(metrics.get(VIS_KEY_LAST_SEEN_MS), now_ms)
    packets = _format_packet_count(metrics.get(VIS_KEY_MSG_COUNT))
    rate = _format_float(metrics.get(VIS_KEY_FRAMES_PER_SEC), FLOAT_RATE_SCALE, "/s")
    raw_ids = device.get(VIS_KEY_RAW_IDS)
    raw_count = len(raw_ids) if isinstance(raw_ids, list) else 0
    return (
        f"  {label} identity={identity} lastSeen={last_seen}"
        f" packets={packets} rate={rate} rawIds={raw_count}"
    )


def build_host_can_bus_report(
    session: BridgeSession,
    visibility_provider: Optional[object],
    *,
    now: Optional[float] = None,
) -> str:
    """
    NAME
        build_host_can_bus_report - Build one host-owned combined CAN diagnostics report.
    """
    report_lines: List[str] = [SECTION_REPORT]
    now_value = time.time() if now is None else float(now)
    now_ms = int(now_value * MS_PER_SEC)
    runtime_state = session.fetch_runtime_state() if session is not None else {}
    report_lines.extend(_build_host_visibility_lines(visibility_provider, now_ms))
    report_lines.extend(_build_robot_bus_lines(runtime_state))
    report_lines.extend(_build_robot_device_lines(runtime_state))
    report_lines.append(SECTION_FOOTER)
    return "\n".join(report_lines)


def _build_host_visibility_lines(
    visibility_provider: Optional[object],
    now_ms: int,
) -> List[str]:
    lines: List[str] = [SECTION_HOST]
    if visibility_provider is None:
        lines.append(f"  Status: {TEXT_UNAVAILABLE}")
        return lines
    snapshot = visibility_provider.snapshot(VISIBILITY_SCOPE, now_ms)
    summary = visibility_provider.summary(VISIBILITY_SCOPE, now_ms)
    sources = snapshot.get(VIS_KEY_SOURCES) if isinstance(snapshot, dict) else []
    devices = snapshot.get(VIS_KEY_DEVICES) if isinstance(snapshot, dict) else []
    if not isinstance(sources, list):
        sources = []
    if not isinstance(devices, list):
        devices = []
    lines.append(
        "  Summary: sources={sources} devices={devices} all={all_seen} some={some_seen} none={none_seen}".format(
            sources=len(sources),
            devices=int(summary.get(VIS_KEY_DEVICES_SHOWN, len(devices))) if isinstance(summary, dict) else len(devices),
            all_seen=int(summary.get(VIS_KEY_VISIBLE_ALL, 0)) if isinstance(summary, dict) else 0,
            some_seen=int(summary.get(VIS_KEY_VISIBLE_SOME, 0)) if isinstance(summary, dict) else 0,
            none_seen=int(summary.get(VIS_KEY_VISIBLE_NONE, 0)) if isinstance(summary, dict) else 0,
        )
    )
    for source in sources:
        if not isinstance(source, dict):
            continue
        source_label = str(source.get(VIS_KEY_LABEL, source.get(VIS_KEY_ID, TEXT_UNKNOWN))).strip() or TEXT_UNKNOWN
        lines.append(
            f"  Source {source_label}: available={_bool_text(source.get(VIS_KEY_AVAILABLE, False))}"
        )
    defined_rows: List[str] = []
    unexpected_rows: List[str] = []
    for device in devices:
        if not isinstance(device, dict):
            continue
        row_text = _visibility_row_line(device, now_ms)
        if bool(device.get(KEY_UNEXPECTED, False)):
            unexpected_rows.append(row_text)
        else:
            defined_rows.append(row_text)
    lines.append(SECTION_DEFINED)
    lines.extend(defined_rows or [f"  {TEXT_NONE}"])
    lines.append(SECTION_UNRECOGNIZED)
    lines.extend(unexpected_rows or [f"  {TEXT_NONE}"])
    return lines


def _build_robot_bus_lines(runtime_state: Dict[str, object]) -> List[str]:
    lines: List[str] = [SECTION_ROBOT_BUS]
    bus = runtime_state.get(KEY_CAN_BUS) if isinstance(runtime_state.get(KEY_CAN_BUS), dict) else {}
    if not isinstance(bus, dict) or not bool(bus.get(TEXT_VALID, False)):
        lines.append(f"  Status: {TEXT_UNAVAILABLE}")
        return lines
    lines.append(
        "  utilization={util} rxErrors={rx} txErrors={tx} rxDelta={rx_delta} txDelta={tx_delta}".format(
            util=_format_float(bus.get(KEY_UTILIZATION_PCT), FLOAT_RATE_SCALE, "%"),
            rx=_format_packet_count(bus.get(KEY_RX_ERRORS)),
            tx=_format_packet_count(bus.get(KEY_TX_ERRORS)),
            rx_delta=_format_packet_count(bus.get(KEY_RX_DELTA)),
            tx_delta=_format_packet_count(bus.get(KEY_TX_DELTA)),
        )
    )
    lines.append(
        "  txFull={tx_full} txFullDelta={tx_full_delta} busOff={bus_off} busOffDelta={bus_off_delta} sampleAge={age}".format(
            tx_full=_format_packet_count(bus.get(KEY_TX_FULL)),
            tx_full_delta=_format_packet_count(bus.get(KEY_TX_FULL_DELTA)),
            bus_off=_format_packet_count(bus.get(KEY_BUS_OFF)),
            bus_off_delta=_format_packet_count(bus.get(KEY_BUS_OFF_DELTA)),
            age=_format_float(bus.get(KEY_SAMPLE_AGE_SEC), FLOAT_SMALL_SCALE, "s"),
        )
    )
    return lines


def _build_robot_device_lines(runtime_state: Dict[str, object]) -> List[str]:
    lines: List[str] = [SECTION_ROBOT_DEVICES]
    devices = runtime_state.get(KEY_DEVICES)
    if not isinstance(devices, list) or not devices:
        lines.append(f"  {TEXT_NONE}")
        return lines
    for device in devices:
        if not isinstance(device, dict):
            continue
        lines.append(_device_runtime_line(device))
        lines.extend(_device_detail_lines(device))
    return lines
