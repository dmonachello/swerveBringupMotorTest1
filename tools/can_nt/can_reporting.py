from __future__ import annotations

"""
NAME
    can_reporting.py - Console/summary reporting helpers.

SYNOPSIS
    from tools.can_nt.can_reporting import print_summary, format_frame_line

DESCRIPTION
    Formats NetworkTables key inventories, status transitions, and summary
    lines for human-readable diagnostics.
"""

import json
from typing import Any, Dict, List, Optional

from tools.common.time_utils import timestamp_hms
from tools.common.nt_labels import encode_label_for_nt
from .can_analyzer import CanLiveAnalyzer
from .can_state import SnifferState


KEY_DEV_BASE = "bringup/diag/dev"
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

KEY_CAN_SUMMARY = "bringup/diag/can/summary/json"
KEY_PC_HEARTBEAT = "bringup/diag/can/pc/heartbeat"
KEY_PC_OPEN_OK = "bringup/diag/can/pc/openOk"
KEY_PC_FRAMES_PER_SEC = "bringup/diag/can/pc/framesPerSec"
KEY_PC_FRAMES_TOTAL = "bringup/diag/can/pc/framesTotal"
KEY_PC_READ_ERRORS = "bringup/diag/can/pc/readErrors"
KEY_PC_LAST_FRAME_AGE = "bringup/diag/can/pc/lastFrameAgeSec"
KEY_CONSOLE_DYNAMIC = "bringup/diag/console/(dynamic keys per rule/device)"
KEY_CONSOLE_RESET = "bringup/diag/console/reset"

STATUS_OK = "OK"
STATUS_MISSING = "MISSING"
STATUS_CONTROL_ONLY = "CONTROL_ONLY"
STATUS_UNKNOWN = "UNKNOWN"

LABEL_UNKNOWN = "UNKNOWN"


def print_or_dump_nt_keys(devices, print_keys: bool, dump_path: str) -> None:
    """
    NAME
        print_or_dump_nt_keys - Emit or persist the published NT key list.

    PARAMETERS
        devices: Profile device list used to expand per-device keys.
        print_keys: Whether to print to stdout.
        dump_path: Optional JSON output path.

    SIDE EFFECTS
        Prints to stdout and/or writes a JSON file.
    """
    keys = []
    for spec in devices:
        label = str(spec.get(KEY_LABEL, LABEL_UNKNOWN))
        label_key = encode_label_for_nt(label)
        base = f"{KEY_DEV_BASE}/{label_key}"
        keys.extend(
            [
                f"{base}/{KEY_LABEL}",
                f"{base}/{KEY_STATUS}",
                f"{base}/{KEY_AGE_SEC}",
                f"{base}/{KEY_MSG_COUNT}",
                f"{base}/{KEY_LAST_SEEN}",
                f"{base}/{KEY_PRESENCE_SOURCE}",
                f"{base}/{KEY_PRESENCE_CONFIDENCE}",
                f"{base}/{KEY_TRAFFIC_AGE_SEC}",
                f"{base}/{KEY_STATUS_AGE_SEC}",
            ]
        )
    keys.append(KEY_CAN_SUMMARY)
    keys.extend(
        [
            KEY_PC_HEARTBEAT,
            KEY_PC_OPEN_OK,
            KEY_PC_FRAMES_PER_SEC,
            KEY_PC_FRAMES_TOTAL,
            KEY_PC_READ_ERRORS,
            KEY_PC_LAST_FRAME_AGE,
            KEY_CONSOLE_DYNAMIC,
            KEY_CONSOLE_RESET,
        ]
    )
    payload = {
        "keys": keys,
        "count": len(keys),
    }
    if print_keys:
        print("NetworkTables keys published by tools/can_nt/can_nt_bridge.py:")
        for key in keys:
            print(f"  {key}")
    if dump_path:
        try:
            with open(dump_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as exc:
            print(f"ERROR: Failed to write NT keys dump '{dump_path}': {exc}")
        print(f"Wrote NT key inventory to {dump_path}")


def print_status_transitions(
    devices,
    last_seen: Dict[str, float],
    status_last_seen: Dict[str, float],
    control_last_seen: Dict[str, float],
    now: float,
    timeout_s: float,
    last_status: Dict[str, str],
) -> None:
    """
    NAME
        print_status_transitions - Print device seen/missing transitions.

    DESCRIPTION
        Compares current presence against cached status and prints transitions
        when a device crosses the timeout threshold.

    SIDE EFFECTS
        Writes to stdout.
    """
    for spec in devices:
        label = str(spec.get(KEY_LABEL, LABEL_UNKNOWN))
        traffic_ts = last_seen.get(label)
        status_ts = status_last_seen.get(label)
        control_ts = control_last_seen.get(label)
        prefer_status = bool(spec.get(KEY_PREFER_STATUS, False))
        ts = status_ts if prefer_status else traffic_ts
        if ts is None:
            status = STATUS_CONTROL_ONLY if control_ts is not None else STATUS_MISSING
        else:
            status = STATUS_OK if (now - ts) < timeout_s else STATUS_MISSING
        prev = last_status.get(label)
        if prev is None:
            last_status[label] = status
            continue
        if prev != status:
            if status == STATUS_OK:
                print(f"[seen] {label}")
            else:
                print(f"[missing] {label} ({status})")
        last_status[label] = status


def format_frame_line(
    kind: str,
    arb_id: int,
    mfg: int,
    dtype: int,
    device_id: int,
    api_class: int,
    api_index: int,
    data: bytes,
    label: str,
) -> str:
    """
    NAME
        format_frame_line - Format a single CAN frame for console output.

    RETURNS
        A one-line string with identifiers, label, and data bytes.
    """
    label_text = f" {label}" if label else ""
    return (
        f"[{kind}]"
        f"{label_text} apiClass={api_class} apiIndex={api_index} "
        f"len={len(data)} data={data.hex()}"
    )


def get_bus_dropped(bus) -> Optional[int]:
    """
    NAME
        get_bus_dropped - Extract dropped-frame counters from a bus object.

    RETURNS
        Integer drop count when available, otherwise None.
    """
    for attr in ("dropped_frames", "drop_count", "rx_overflow", "rx_dropped"):
        value = getattr(bus, attr, None)
        if isinstance(value, int):
            return value
    return None


def build_summary_extra(
    summary: Dict[str, Any],
    devices: List[Dict[str, Any]],
    analyzer: CanLiveAnalyzer,
    state: SnifferState,
    bus,
    bitrate: int,
) -> Dict[str, Any]:
    """
    NAME
        build_summary_extra - Compute derived summary fields for printing.

    DESCRIPTION
        Adds bus-load percentage and counts of seen/unknown devices.

    RETURNS
        Dictionary of extra summary values.
    """
    bytes_per_s = summary.get("bus", {}).get("bytes_per_s", 0.0)
    bus_load_pct = None
    if isinstance(bytes_per_s, (int, float)) and bitrate > 0:
        bus_load_pct = (bytes_per_s * 8.0 / float(bitrate)) * 100.0
    known_labels = {str(d.get(KEY_LABEL, LABEL_UNKNOWN)) for d in devices}
    seen_labels = set(state.last_seen.keys())
    unknown_labels = seen_labels - known_labels
    return {
        "bus_load_pct": bus_load_pct,
        "read_errors": state.read_errors,
        "pcap_errors": state.pcap_errors,
        "dropped": get_bus_dropped(bus),
        "seen_devices": len(seen_labels),
        "unknown_devices": len(unknown_labels),
    }


def print_summary(
    summary,
    now: float,
    extra: Dict[str, Any],
) -> None:
    """
    NAME
        print_summary - Print a compact periodic summary line.

    PARAMETERS
        summary: Analyzer summary payload.
        now: Current wall-clock time (seconds).
        extra: Derived summary fields.

    SIDE EFFECTS
        Writes to stdout.
    """
    bus = summary.get("bus", {})
    health = summary.get("health", {})
    top = summary.get("top", [])
    total = bus.get("fps")
    missing = health.get("missing", [])
    ts = timestamp_hms(now)
    bus_load = extra.get("bus_load_pct")
    bus_load_text = f"{bus_load:.1f}%" if isinstance(bus_load, (int, float)) else "n/a"
    dropped = extra.get("dropped")
    dropped_text = str(dropped) if isinstance(dropped, int) else "n/a"
    print(
        f"[summary {ts}] fps={total} missing={len(missing)} top={len(top)} "
        f"busLoad={bus_load_text} readErr={extra.get('read_errors', 0)} "
        f"pcapErr={extra.get('pcap_errors', 0)} dropped={dropped_text} "
        f"seen={extra.get('seen_devices', 0)} unknown={extra.get('unknown_devices', 0)}"
    )
    for row in top[:5]:
        try:
            label = row.get("label", LABEL_UNKNOWN)
            print(
                "  "
                f"{label} hz={row.get('hz')}"
            )
        except Exception:
            continue
