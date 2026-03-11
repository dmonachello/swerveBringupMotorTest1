from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple


@dataclass
class SnifferState:
    last_seen: Dict[Tuple[int, int, int], float] = field(default_factory=dict)
    status_last_seen: Dict[Tuple[int, int, int], float] = field(default_factory=dict)
    control_last_seen: Dict[Tuple[int, int, int], float] = field(default_factory=dict)
    msg_count: Dict[Tuple[int, int, int], int] = field(default_factory=dict)
    pair_stats: Dict[Tuple[int, int, int, int, int], Dict[str, float]] = field(default_factory=dict)
    last_status: Dict[Tuple[int, int, int], str] = field(default_factory=dict)
    total_frames: int = 0
    period_frames: int = 0
    read_errors: int = 0
    pcap_errors: int = 0
    last_frame_time: float = 0.0
    heartbeat: int = 0
    open_ok: bool = True
    marker_counter: int = 0
    last_marker_ts: float = 0.0


def merge_unknown_devices(devices, last_seen: Dict[Tuple[int, int, int], float], enabled: bool):
    if not enabled:
        return devices
    known_keys = {(d["manufacturer"], d["device_type"], d["device_id"]) for d in devices}
    merged = list(devices)
    for key in last_seen.keys():
        if key in known_keys:
            continue
        mfg, dtype, did = key
        merged.append(
            {
                "label": "UNKNOWN",
                "manufacturer": mfg,
                "device_type": dtype,
                "device_id": did,
                "group": "unknown",
            }
        )
    return merged
