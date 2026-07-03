from __future__ import annotations

"""
NAME
    can_reporting.py - Console/summary reporting helpers.

SYNOPSIS
    from tools.can_nt.can_reporting import print_summary, format_frame_line

DESCRIPTION
    Formats status transitions and summary lines for human-readable diagnostics.
"""

from typing import Any, Dict, List, Optional

from tools.common.time_utils import timestamp_hms
from .can_analyzer import CanLiveAnalyzer
from .can_state import SnifferState

STATUS_OK = "OK"
STATUS_MISSING = "MISSING"
STATUS_CONTROL_ONLY = "CONTROL_ONLY"
STATUS_UNKNOWN = "UNKNOWN"
KEY_LABEL = "label"
KEY_PREFER_STATUS = "prefer_status"

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
