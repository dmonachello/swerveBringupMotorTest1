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
MAX_UNKNOWN_LABELS = 5
TEXT_NA = "n/a"
TEXT_CAPTURE_INCOMPLETE = "captureIncomplete"
TEXT_UNKNOWN_ACTIVE = "unknownActive"
FLOAT_ZERO = 0.0
INT_ZERO = 0
BITS_PER_BYTE = 8.0
AGE_FORMAT = "{:.2f}s"
KEY_BUS = "bus"
KEY_BYTES_PER_S = "bytes_per_s"
KEY_FPS = "fps"
KEY_HEALTH = "health"
KEY_MISSING = "missing"
KEY_TOP = "top"
KEY_LABEL_FIELD = "label"
KEY_HZ_FIELD = "hz"
KEY_BUS_LOAD_PCT = "bus_load_pct"
KEY_READ_ERRORS = "read_errors"
KEY_PCAP_ERRORS = "pcap_errors"
KEY_DROPPED = "dropped"
KEY_SEEN_DEVICES = "seen_devices"
KEY_UNKNOWN_DEVICES = "unknown_devices"
KEY_UNKNOWN_LABELS = "unknown_labels"
KEY_CAPTURE_OK = "capture_ok"
KEY_LAST_FRAME_AGE_SEC = "last_frame_age_sec"
SUMMARY_PREFIX = "[summary "
SUMMARY_SUFFIX = "]"
SUMMARY_FMT = (
    " fps={fps} missing={missing} top={top} busLoad={bus_load} "
    "readErr={read_err} pcapErr={pcap_err} dropped={dropped} "
    "seen={seen} unknown={unknown}"
)
SUMMARY_TOP_FMT = "  {label} hz={hz}"
SUMMARY_UNKNOWN_ACTIVE_FMT = "  {unknown_key}={labels}"
SUMMARY_CAPTURE_FMT = "  {capture_key} lastFrameAge={age}"
MAX_TOP_LINES = 5


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
    now: float,
    stale_s: float,
) -> Dict[str, Any]:
    """
    NAME
        build_summary_extra - Compute derived summary fields for printing.

    DESCRIPTION
        Adds bus-load percentage, unknown device info, and capture health.

    RETURNS
        Dictionary of extra summary values.
    """
    bytes_per_s = summary.get(KEY_BUS, {}).get(KEY_BYTES_PER_S, FLOAT_ZERO)
    bus_load_pct = None
    if isinstance(bytes_per_s, (int, float)) and bitrate > INT_ZERO:
        bus_load_pct = (bytes_per_s * BITS_PER_BYTE / float(bitrate)) * 100.0
    known_labels = {str(d.get(KEY_LABEL, LABEL_UNKNOWN)) for d in devices}
    seen_labels = set(state.last_seen.keys())
    unknown_labels = sorted(seen_labels - known_labels)
    last_frame_age = None
    if state.last_frame_time > FLOAT_ZERO:
        last_frame_age = now - state.last_frame_time
    capture_ok = bool(state.open_ok)
    if last_frame_age is not None and last_frame_age > stale_s:
        capture_ok = False
    return {
        KEY_BUS_LOAD_PCT: bus_load_pct,
        KEY_READ_ERRORS: state.read_errors,
        KEY_PCAP_ERRORS: state.pcap_errors,
        KEY_DROPPED: get_bus_dropped(bus),
        KEY_SEEN_DEVICES: len(seen_labels),
        KEY_UNKNOWN_DEVICES: len(unknown_labels),
        KEY_UNKNOWN_LABELS: unknown_labels[:MAX_UNKNOWN_LABELS],
        KEY_CAPTURE_OK: capture_ok,
        KEY_LAST_FRAME_AGE_SEC: last_frame_age,
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
    bus = summary.get(KEY_BUS, {})
    health = summary.get(KEY_HEALTH, {})
    top = summary.get(KEY_TOP, [])
    total = bus.get(KEY_FPS)
    missing = health.get(KEY_MISSING, [])
    ts = timestamp_hms(now)
    bus_load = extra.get(KEY_BUS_LOAD_PCT)
    bus_load_text = f"{bus_load:.1f}%" if isinstance(bus_load, (int, float)) else TEXT_NA
    dropped = extra.get(KEY_DROPPED)
    dropped_text = str(dropped) if isinstance(dropped, int) else TEXT_NA
    print(
        SUMMARY_PREFIX
        + ts
        + SUMMARY_SUFFIX
        + SUMMARY_FMT.format(
            fps=total,
            missing=len(missing),
            top=len(top),
            bus_load=bus_load_text,
            read_err=extra.get(KEY_READ_ERRORS, INT_ZERO),
            pcap_err=extra.get(KEY_PCAP_ERRORS, INT_ZERO),
            dropped=dropped_text,
            seen=extra.get(KEY_SEEN_DEVICES, INT_ZERO),
            unknown=extra.get(KEY_UNKNOWN_DEVICES, INT_ZERO),
        )
    )
    unknown_labels = extra.get(KEY_UNKNOWN_LABELS)
    if isinstance(unknown_labels, list) and unknown_labels:
        print(
            SUMMARY_UNKNOWN_ACTIVE_FMT.format(
                unknown_key=TEXT_UNKNOWN_ACTIVE,
                labels=", ".join(str(label) for label in unknown_labels),
            )
        )
    if extra.get(KEY_CAPTURE_OK) is False:
        age = extra.get(KEY_LAST_FRAME_AGE_SEC)
        age_text = AGE_FORMAT.format(age) if isinstance(age, (int, float)) else TEXT_NA
        print(
            SUMMARY_CAPTURE_FMT.format(
                capture_key=TEXT_CAPTURE_INCOMPLETE,
                age=age_text,
            )
        )
    for row in top[:MAX_TOP_LINES]:
        try:
            label = row.get(KEY_LABEL_FIELD, LABEL_UNKNOWN)
            print(
                SUMMARY_TOP_FMT.format(
                    label=label,
                    hz=row.get(KEY_HZ_FIELD),
                )
            )
        except Exception:
            continue
