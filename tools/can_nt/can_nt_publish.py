from __future__ import annotations

"""
NAME
    can_nt_publish.py - NetworkTables publishing helpers for CAN devices.

SYNOPSIS
    from tools.can_nt.can_nt_publish import publish_devices

DESCRIPTION
    Encodes per-device presence/age metrics into NetworkTables keys under
    bringup/diag/dev.
"""

from typing import Any, Dict, List, Tuple


def decode_frc_ext_id(arb_id: int) -> Tuple[int, int, int]:
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


def publish_devices(
    table,
    devices: List[Dict[str, Any]],
    last_seen: Dict[Tuple[int, int, int], float],
    status_last_seen: Dict[Tuple[int, int, int], float],
    control_last_seen: Dict[Tuple[int, int, int], float],
    uses_status_presence,
    msg_count: Dict[Tuple[int, int, int], int],
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
        Writes multiple NetworkTables entries under dev/<mfg>/<type>/<id>.
    """
    for spec in devices:
        key = (spec["manufacturer"], spec["device_type"], spec["device_id"])
        traffic_ts = last_seen.get(key)
        status_ts = status_last_seen.get(key)
        control_ts = control_last_seen.get(key)
        prefer_status = uses_status_presence(key[0], key[1])

        traffic_age = -1.0 if traffic_ts is None else (now - traffic_ts)
        status_age = -1.0 if status_ts is None else (now - status_ts)

        if prefer_status:
            if status_ts is not None and status_age < timeout_s:
                presence_source = "STATUS"
                confidence = "HIGH"
                status = "OK"
                age = status_age
            elif control_ts is not None and traffic_ts is not None:
                presence_source = "CONTROL_ONLY"
                confidence = "LOW"
                status = "CONTROL_ONLY"
                age = traffic_age
            elif traffic_ts is not None:
                presence_source = "TRAFFIC"
                confidence = "LOW"
                status = "MISSING"
                age = traffic_age
            else:
                presence_source = "NONE"
                confidence = "NONE"
                status = "MISSING"
                age = -1.0
        else:
            if traffic_ts is not None and traffic_age < timeout_s:
                presence_source = "TRAFFIC"
                confidence = "LOW"
                status = "OK"
                age = traffic_age
            else:
                presence_source = "NONE"
                confidence = "NONE"
                status = "MISSING"
                age = -1.0

        last_seen_value = traffic_ts if traffic_ts is not None else -1.0

        base = f"dev/{key[0]}/{key[1]}/{key[2]}"
        table.getEntry(f"{base}/label").setString(str(spec.get("label", "")))
        table.getEntry(f"{base}/status").setString(status)
        table.getEntry(f"{base}/ageSec").setDouble(float(age))
        table.getEntry(f"{base}/msgCount").setDouble(float(msg_count.get(key, 0)))
        table.getEntry(f"{base}/lastSeen").setDouble(float(last_seen_value))
        table.getEntry(f"{base}/manufacturer").setDouble(float(key[0]))
        table.getEntry(f"{base}/deviceType").setDouble(float(key[1]))
        table.getEntry(f"{base}/deviceId").setDouble(float(key[2]))
        table.getEntry(f"{base}/presenceSource").setString(presence_source)
        table.getEntry(f"{base}/presenceConfidence").setString(confidence)
        table.getEntry(f"{base}/trafficAgeSec").setDouble(float(traffic_age))
        table.getEntry(f"{base}/statusAgeSec").setDouble(float(status_age))
