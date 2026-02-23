from __future__ import annotations

from typing import Any, Dict, List, Tuple


def decode_frc_ext_id(arb_id: int) -> Tuple[int, int, int]:
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
    msg_count: Dict[Tuple[int, int, int], int],
    now: float,
    timeout_s: float,
) -> None:
    for spec in devices:
        key = (spec["manufacturer"], spec["device_type"], spec["device_id"])
        ts = last_seen.get(key)

        if ts is None:
            age = -1.0
            status = "MISSING"
        else:
            age = now - ts
            status = "OK" if age < timeout_s else "MISSING"

        base = f"dev/{key[0]}/{key[1]}/{key[2]}"
        table.getEntry(f"{base}/label").setString(str(spec.get("label", "")))
        table.getEntry(f"{base}/status").setString(status)
        table.getEntry(f"{base}/ageSec").setDouble(float(age))
        table.getEntry(f"{base}/msgCount").setDouble(float(msg_count.get(key, 0)))
