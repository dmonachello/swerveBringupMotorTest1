from __future__ import annotations

"""
NAME
    live_sources.py - Live acquisition adapters for passive discovery.

DESCRIPTION
    Provides reusable live-source capture helpers for CANable/slcan and direct
    REV serial bridge traffic. Both adapters return normalized frames so the
    downstream analysis pipeline stays shared with offline inputs.
"""

import time
from threading import Event
from typing import Iterator, List, Optional, Tuple

from tools.can_nt.can_ports import maybe_auto_channel
from tools.passive_discovery_poc.constants import (
    DIAGNOSTIC_BUS_MESSAGE_COUNT,
    DIAGNOSTIC_NORMALIZED_FRAME_COUNT,
    DIAGNOSTIC_PARSED_RECORD_COUNT,
    DIAGNOSTIC_RAW_BYTES_RECEIVED,
    DIAGNOSTIC_RAW_RECORD_COUNT,
    AUTO_PORT_SENTINEL,
    DEFAULT_AUTO_MATCH,
    DEFAULT_CAN_BITRATE,
    DEFAULT_REV_AUTO_MATCH,
    DEFAULT_SERIAL_TIMEOUT_SEC,
    DEFAULT_SLCAN_INTERFACE,
    DEFAULT_REV_SERIAL_BAUD,
    FLOAT_ZERO,
    INT_ONE,
    INT_ZERO,
    REV_SERIAL_RECORD_SEPARATOR,
    REV_SERIAL_REPLACE_LF,
    REV_SERIAL_AUTO_MATCH_CANDIDATES,
    REV_SERIAL_MATCH_FIELDS,
    SERIAL_MATCH_FIELD_DESCRIPTION,
    SOURCE_KIND_LIVE_REV_SERIAL,
    SOURCE_KIND_LIVE_SLCAN,
)
from tools.passive_discovery_poc.models import NormalizedFrame
from tools.passive_discovery_poc.readers import build_normalized_frame
from tools.vendor_diag.rev_usb_to_candump import parse_ascii_can_record


def capture_live_slcan(
    channel: str,
    bitrate: int,
    duration_sec: float,
    interface: str = DEFAULT_SLCAN_INTERFACE,
) -> List[NormalizedFrame]:
    """
    NAME
        capture_live_slcan - Capture passive CAN traffic from a live slcan source.

    ERRORS
        Raises RuntimeError when python-can is unavailable or the source fails.
    """
    try:
        import can  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "python-can is required for live slcan capture. Install it with: py -m pip install python-can"
        ) from exc
    return list(
        iter_live_slcan_frames(
            channel=channel,
            bitrate=bitrate,
            duration_sec=duration_sec,
            interface=interface,
        )
    )


def capture_live_rev_serial(
    port: str,
    baudrate: int,
    duration_sec: float,
) -> List[NormalizedFrame]:
    """
    NAME
        capture_live_rev_serial - Capture passive CAN frames from a live REV serial bridge.

    DESCRIPTION
        Reads the ASCII CAN record stream directly from the REV bridge serial
        port and normalizes it into frames.
    """
    try:
        import serial  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "pyserial is required for live REV serial capture. Install it with: py -m pip install pyserial"
        ) from exc
    return list(
        iter_live_rev_serial_frames(
            port=port,
            baudrate=baudrate,
            duration_sec=duration_sec,
        )
    )


def iter_live_slcan_frames(
    channel: str,
    bitrate: int,
    duration_sec: Optional[float] = None,
    interface: str = DEFAULT_SLCAN_INTERFACE,
    stop_event: Optional[Event] = None,
    diagnostics: Optional[dict] = None,
) -> Iterator[NormalizedFrame]:
    """
    NAME
        iter_live_slcan_frames - Yield normalized live frames from a slcan source.
    """
    try:
        import can  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "python-can is required for live slcan capture. Install it with: py -m pip install python-can"
        ) from exc
    deadline = None if duration_sec is None else (time.time() + float(duration_sec))
    try:
        bus = can.Bus(interface=interface, channel=channel, bitrate=int(bitrate))
    except Exception as exc:
        raise RuntimeError(f"Failed to open live slcan source {channel}: {exc}") from exc
    try:
        while True:
            if deadline is not None and time.time() >= deadline:
                break
            if stop_event is not None and stop_event.is_set():
                break
            try:
                message = bus.recv(timeout=DEFAULT_SERIAL_TIMEOUT_SEC)
            except Exception as exc:
                raise RuntimeError(f"Live slcan source failed during capture: {exc}") from exc
            if message is None:
                continue
            _increment_diagnostic(diagnostics, DIAGNOSTIC_BUS_MESSAGE_COUNT)
            _increment_diagnostic(diagnostics, DIAGNOSTIC_NORMALIZED_FRAME_COUNT)
            yield build_normalized_frame(
                timestamp_s=float(getattr(message, "timestamp", time.time())),
                can_id=int(getattr(message, "arbitration_id", INT_ZERO)),
                data_bytes=bytes(getattr(message, "data", b"") or b""),
                is_extended=bool(getattr(message, "is_extended_id", False)),
                is_rtr=bool(getattr(message, "is_remote_frame", False)),
                observer_source=SOURCE_KIND_LIVE_SLCAN,
            )
    finally:
        shutdown = getattr(bus, "shutdown", None)
        if callable(shutdown):
            shutdown()


def iter_live_rev_serial_frames(
    port: str,
    baudrate: int,
    duration_sec: Optional[float] = None,
    stop_event: Optional[Event] = None,
    diagnostics: Optional[dict] = None,
) -> Iterator[NormalizedFrame]:
    """
    NAME
        iter_live_rev_serial_frames - Yield normalized live frames from a REV serial bridge.
    """
    try:
        import serial  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "pyserial is required for live REV serial capture. Install it with: py -m pip install pyserial"
        ) from exc
    try:
        handle = serial.Serial(port=port, baudrate=int(baudrate), timeout=DEFAULT_SERIAL_TIMEOUT_SEC)
    except Exception as exc:
        raise RuntimeError(f"Failed to open REV serial source {port}: {exc}") from exc
    deadline = None if duration_sec is None else (time.time() + float(duration_sec))
    buffer = ""
    try:
        while True:
            if deadline is not None and time.time() >= deadline:
                break
            if stop_event is not None and stop_event.is_set():
                break
            try:
                chunk = handle.read(4096)
            except Exception as exc:
                raise RuntimeError(f"Live REV serial source failed during capture: {exc}") from exc
            if not chunk:
                continue
            _increment_diagnostic(diagnostics, DIAGNOSTIC_RAW_BYTES_RECEIVED, amount=len(chunk))
            buffer += chunk.decode("ascii", errors="ignore")
            buffer = buffer.replace(REV_SERIAL_REPLACE_LF, REV_SERIAL_RECORD_SEPARATOR)
            parts = buffer.split(REV_SERIAL_RECORD_SEPARATOR)
            buffer = parts[-1]
            for line in parts[:-1]:
                if not line:
                    continue
                _increment_diagnostic(diagnostics, DIAGNOSTIC_RAW_RECORD_COUNT)
                parsed = parse_ascii_can_record(line=line, timestamp_s=time.time())
                if parsed is None:
                    continue
                _increment_diagnostic(diagnostics, DIAGNOSTIC_PARSED_RECORD_COUNT)
                _increment_diagnostic(diagnostics, DIAGNOSTIC_NORMALIZED_FRAME_COUNT)
                yield build_normalized_frame(
                    timestamp_s=parsed.timestamp_s,
                    can_id=parsed.arb_id,
                    data_bytes=parsed.data,
                    is_extended=parsed.is_extended,
                    is_rtr=parsed.is_rtr,
                    observer_source=SOURCE_KIND_LIVE_REV_SERIAL,
                )
    finally:
        handle.close()


def resolve_slcan_channel(explicit_channel: str, auto_match: str) -> str:
    """
    NAME
        resolve_slcan_channel - Resolve a slcan channel from explicit input or auto-detect.
    """
    if explicit_channel.strip():
        return explicit_channel.strip()
    class _Args:
        channel = ""
        no_prompt = True
        auto_match = DEFAULT_AUTO_MATCH

    args = _Args()
    args.auto_match = auto_match.strip() or DEFAULT_AUTO_MATCH
    channel, _desc, status = maybe_auto_channel(args)
    if status != INT_ZERO or not channel:
        raise RuntimeError("Failed to resolve live slcan channel.")
    return channel


def resolve_rev_serial_port(explicit_port: str, auto_match: str = DEFAULT_REV_AUTO_MATCH) -> str:
    """
    NAME
        resolve_rev_serial_port - Resolve a REV serial bridge COM port from explicit input or auto-detect.
    """
    stripped = explicit_port.strip()
    if stripped and stripped.lower() != AUTO_PORT_SENTINEL:
        return stripped
    try:
        import serial.tools.list_ports  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "pyserial is required for auto-detecting the REV serial source. Install it with: py -m pip install pyserial"
        ) from exc
    candidate_terms = [term for term in REV_SERIAL_AUTO_MATCH_CANDIDATES if term]
    preferred_term = auto_match.strip()
    if preferred_term:
        candidate_terms.insert(INT_ZERO, preferred_term)
    matches: List[Tuple[str, str]] = []
    fallback_ports: List[Tuple[str, str]] = []
    try:
        for port in serial.tools.list_ports.comports():
            description = str(getattr(port, SERIAL_MATCH_FIELD_DESCRIPTION, "") or "")
            port_device = str(getattr(port, "device", "") or "").strip()
            if not port_device:
                continue
            fallback_ports.append((port_device, description))
            searchable_values = []
            for field_name in REV_SERIAL_MATCH_FIELDS:
                searchable_values.append(str(getattr(port, field_name, "") or ""))
            combined = " ".join(searchable_values).lower()
            if any(term.lower() in combined for term in candidate_terms if term):
                matches.append((port_device, description))
    except Exception as exc:
        raise RuntimeError(f"Failed to enumerate serial ports: {exc}") from exc
    deduped_matches: List[Tuple[str, str]] = []
    seen_devices = set()
    for device, description in matches:
        if device in seen_devices:
            continue
        seen_devices.add(device)
        deduped_matches.append((device, description))
    if len(deduped_matches) == 1:
        return deduped_matches[0][0]
    if len(deduped_matches) > 1:
        device_list = ", ".join(device for device, _description in deduped_matches)
        raise RuntimeError(
            f"Multiple REV serial candidates matched auto-detect: {device_list}. Specify --live-rev-serial explicitly."
        )
    if not fallback_ports:
        raise RuntimeError("No serial ports were available for REV auto-detect.")
    device_list = ", ".join(device for device, _description in fallback_ports)
    raise RuntimeError(
        f"Could not uniquely auto-detect a REV serial source. Available serial ports: {device_list}. Specify --live-rev-serial explicitly."
    )


def _increment_diagnostic(diagnostics: Optional[dict], key: str, amount: int = INT_ONE) -> None:
    """
    NAME
        _increment_diagnostic - Increment one mutable source-diagnostic counter.
    """
    if diagnostics is None:
        return
    current = diagnostics.get(key, INT_ZERO)
    if not isinstance(current, int):
        current = INT_ZERO
    diagnostics[key] = current + int(amount)
