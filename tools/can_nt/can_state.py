from __future__ import annotations

"""
NAME
    can_state.py - Shared runtime state for the CAN sniffer.

SYNOPSIS
    from tools.can_nt.can_state import SnifferState

DESCRIPTION
    Defines the mutable counters and timestamps used across analysis and NT
    publishing.
"""

from dataclasses import dataclass, field
from typing import Dict, Tuple


LABEL_KEY = "label"
GROUP_KEY = "group"
GROUP_UNKNOWN = "unknown"
PREFER_STATUS_KEY = "prefer_status"


@dataclass
class SnifferState:
    """
    NAME
        SnifferState - Aggregated counters and timestamps for a run.

    DESCRIPTION
        Holds per-device timestamps, message counts, and error totals used by
        reporting and publishing.
    """
    last_seen: Dict[str, float] = field(default_factory=dict)
    status_last_seen: Dict[str, float] = field(default_factory=dict)
    control_last_seen: Dict[str, float] = field(default_factory=dict)
    msg_count: Dict[str, int] = field(default_factory=dict)
    pair_stats: Dict[Tuple[str, int, int], Dict[str, float]] = field(default_factory=dict)
    last_status: Dict[str, str] = field(default_factory=dict)
    total_frames: int = 0
    period_frames: int = 0
    read_errors: int = 0
    pcap_errors: int = 0
    last_frame_time: float = 0.0
    heartbeat: int = 0
    open_ok: bool = True
    marker_counter: int = 0
    last_marker_ts: float = 0.0


def merge_unknown_devices(devices, last_seen: Dict[str, float], enabled: bool):
    """
    NAME
        merge_unknown_devices - Optionally include unprofiled devices.

    PARAMETERS
        devices: Profile device list.
        last_seen: Map of observed devices to last-seen timestamps.
        enabled: Whether to add unknown entries.

    RETURNS
        A list including UNKNOWN entries for unprofiled devices when enabled.
    """
    if not enabled:
        return devices
    known_labels = {str(d.get(LABEL_KEY, "")) for d in devices}
    merged = list(devices)
    for label in last_seen.keys():
        if label in known_labels:
            continue
        merged.append(
            {
                LABEL_KEY: label,
                GROUP_KEY: GROUP_UNKNOWN,
                PREFER_STATUS_KEY: False,
            }
        )
    return merged
