from __future__ import annotations

"""
NAME
    can_nt_publish.py - NetworkTables publishing helpers for CAN devices.

SYNOPSIS
    from tools.can_nt.can_nt_publish import publish_devices

DESCRIPTION
    Encodes per-device presence/age metrics into NetworkTables keys under
    bringup/diag/dev using label-only identifiers.
"""

from typing import Any, Dict, List

from tools.common.nt_labels import encode_label_for_nt


def decode_frc_ext_id(arb_id: int) -> tuple[int, int, int]:
    """
    NAME
        decode_frc_ext_id - Decode manufacturer/type/device ID from arb ID.

    PARAMETERS
        arb_id: 29-bit arbitration ID (extended frame).

    RETURNS
        (manufacturer, device_type, device_id).
    """
    # FRC extended CAN layout (common subset):
    # manufacturer: bits 16..23
    # device_type:  bits 24..28
    # device_id:    bits 0..5
    manufacturer = (arb_id >> 16) & 0xFF
    device_type = (arb_id >> 24) & 0x1F
    device_id = arb_id & 0x3F
    return manufacturer, device_type, device_id


KEY_DEV_BASE = "dev"
KEY_LABEL = "label"
KEY_STATUS = "status"
KEY_AGE_SEC = "ageSec"
KEY_MSG_COUNT = "msgCount"
KEY_LAST_SEEN = "lastSeen"
KEY_PRESENCE_SOURCE = "presenceSource"
KEY_PRESENCE_CONFIDENCE = "presenceConfidence"
KEY_TRAFFIC_AGE_SEC = "trafficAgeSec"
KEY_STATUS_AGE_SEC = "statusAgeSec"
KEY_PREFER_STATUS = "prefer_status"

PRESENCE_STATUS = "STATUS"
PRESENCE_CONTROL_ONLY = "CONTROL_ONLY"
PRESENCE_TRAFFIC = "TRAFFIC"
PRESENCE_NONE = "NONE"

CONFIDENCE_HIGH = "HIGH"
CONFIDENCE_LOW = "LOW"
CONFIDENCE_NONE = "NONE"

STATUS_OK = "OK"
STATUS_CONTROL_ONLY = "CONTROL_ONLY"
STATUS_MISSING = "MISSING"


def publish_devices(
    table,
    devices: List[Dict[str, Any]],
    last_seen: Dict[str, float],
    status_last_seen: Dict[str, float],
    control_last_seen: Dict[str, float],
    msg_count: Dict[str, int],
    now: float,
    timeout_s: float,
) -> None:
    """
    NAME
        publish_devices - Write per-device presence metrics to NetworkTables.

    PARAMETERS
        table: NetworkTables base table (bringup/diag).
        devices: Profile device list with metadata.
        last_seen: Last traffic timestamp per device.
        status_last_seen: Last status-frame timestamp per device.
        control_last_seen: Last control-frame timestamp per device.
        uses_status_presence: Predicate for status-based presence confidence.
        msg_count: Total message counts per device.
        now: Current wall-clock time (seconds).
        timeout_s: Presence timeout threshold in seconds.

    SIDE EFFECTS
        Writes multiple NetworkTables entries under dev/<labelKey>.
    """
    for spec in devices:
        label = str(spec.get(KEY_LABEL, ""))
        label_key = encode_label_for_nt(label)
        traffic_ts = last_seen.get(label)
        status_ts = status_last_seen.get(label)
        control_ts = control_last_seen.get(label)
        prefer_status = bool(spec.get(KEY_PREFER_STATUS, False))

        traffic_age = -1.0 if traffic_ts is None else (now - traffic_ts)
        status_age = -1.0 if status_ts is None else (now - status_ts)

        if prefer_status:
            if status_ts is not None and status_age < timeout_s:
                presence_source = PRESENCE_STATUS
                confidence = CONFIDENCE_HIGH
                status = STATUS_OK
                age = status_age
            elif control_ts is not None and traffic_ts is not None:
                presence_source = PRESENCE_CONTROL_ONLY
                confidence = CONFIDENCE_LOW
                status = STATUS_CONTROL_ONLY
                age = traffic_age
            elif traffic_ts is not None:
                presence_source = PRESENCE_TRAFFIC
                confidence = CONFIDENCE_LOW
                status = STATUS_MISSING
                age = traffic_age
            else:
                presence_source = PRESENCE_NONE
                confidence = CONFIDENCE_NONE
                status = STATUS_MISSING
                age = -1.0
        else:
            if traffic_ts is not None and traffic_age < timeout_s:
                presence_source = PRESENCE_TRAFFIC
                confidence = CONFIDENCE_LOW
                status = STATUS_OK
                age = traffic_age
            else:
                presence_source = PRESENCE_NONE
                confidence = CONFIDENCE_NONE
                status = STATUS_MISSING
                age = -1.0

        last_seen_value = traffic_ts if traffic_ts is not None else -1.0

        base = f"{KEY_DEV_BASE}/{label_key}"
        table.getEntry(f"{base}/{KEY_LABEL}").setString(label)
        table.getEntry(f"{base}/{KEY_STATUS}").setString(status)
        table.getEntry(f"{base}/{KEY_AGE_SEC}").setDouble(float(age))
        table.getEntry(f"{base}/{KEY_MSG_COUNT}").setDouble(float(msg_count.get(label, 0)))
        table.getEntry(f"{base}/{KEY_LAST_SEEN}").setDouble(float(last_seen_value))
        table.getEntry(f"{base}/{KEY_PRESENCE_SOURCE}").setString(presence_source)
        table.getEntry(f"{base}/{KEY_PRESENCE_CONFIDENCE}").setString(confidence)
        table.getEntry(f"{base}/{KEY_TRAFFIC_AGE_SEC}").setDouble(float(traffic_age))
        table.getEntry(f"{base}/{KEY_STATUS_AGE_SEC}").setDouble(float(status_age))
