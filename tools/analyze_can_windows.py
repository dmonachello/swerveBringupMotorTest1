#!/usr/bin/env python3
"""
NAME
    analyze_can_windows.py - Windowed CAN log summary helper.

SYNOPSIS
    python analyze_can_windows.py <log> --window start,duration,label [--window ...]

DESCRIPTION
    Parses python-can text logs or BLF files and summarizes API class/index
    counts within specified time windows.

SIDE EFFECTS
    Reads log files and prints window summaries to stdout.
"""
from __future__ import annotations

import argparse
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple


LINE_RX = re.compile(
    r"^\((?P<ts>[0-9]+\.[0-9]+)\)\s+(?P<chan>\S+)\s+(?P<id>[0-9A-Fa-f]{1,8})#(?P<data>[0-9A-Fa-f]*)\s*(?P<dir>[RT])\s*$"
)


@dataclass(frozen=True)
class DecodedId:
    """
    NAME
        DecodedId - Parsed fields from an FRC extended arbitration ID.
    """
    manufacturer: int
    device_type: int
    api_class: int
    api_index: int
    device_id: int


def decode_ext_id(arb: int) -> DecodedId:
    """
    NAME
        decode_ext_id - Decode a 29-bit FRC arbitration ID.

    PARAMETERS
        arb: Arbitration ID as integer.

    RETURNS
        DecodedId with manufacturer, device type, API class/index, and device ID.
    """
    device_type = (arb >> 24) & 0x1F
    manufacturer = (arb >> 16) & 0xFF
    api_class = (arb >> 10) & 0x3F
    api_index = (arb >> 6) & 0x0F
    device_id = arb & 0x3F
    return DecodedId(
        manufacturer=manufacturer,
        device_type=device_type,
        api_class=api_class,
        api_index=api_index,
        device_id=device_id,
    )


def iter_frames_from_log(path: Path) -> Iterable[Tuple[float, int]]:
    """
    NAME
        iter_frames_from_log - Yield (timestamp, arb_id) from text logs.
    """
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            m = LINE_RX.match(line)
            if not m:
                continue
            ts = float(m.group("ts"))
            arb = int(m.group("id"), 16)
            yield (ts, arb)


def iter_frames_from_blf(path: Path) -> Iterable[Tuple[float, int]]:
    """
    NAME
        iter_frames_from_blf - Yield (timestamp, arb_id) from BLF logs.
    """
    import can  # type: ignore

    with can.io.BLFReader(str(path)) as reader:
        for msg in reader:
            if msg is None:
                continue
            yield (float(msg.timestamp), int(msg.arbitration_id))


def iter_frames(path: Path) -> Iterable[Tuple[float, int]]:
    """
    NAME
        iter_frames - Select log reader based on file suffix.
    """
    if path.suffix.lower() == ".blf":
        return iter_frames_from_blf(path)
    return iter_frames_from_log(path)


def within_window(ts: float, start: float, duration: float) -> bool:
    """
    NAME
        within_window - Test if a timestamp falls inside a window.
    """
    return ts >= start and ts < (start + duration)


def parse_windows(raw: List[str]) -> List[Tuple[float, float, str]]:
    """
    NAME
        parse_windows - Parse window strings into tuples.

    ERRORS
        Raises ValueError on invalid window syntax.
    """
    windows: List[Tuple[float, float, str]] = []
    for entry in raw:
        parts = entry.split(",", 2)
        if len(parts) != 3:
            raise ValueError("window must be start,duration,label")
        start = float(parts[0].strip())
        duration = float(parts[1].strip())
        label = parts[2].strip() or f"{start}+{duration}"
        windows.append((start, duration, label))
    return windows


def main() -> int:
    """
    NAME
        main - CLI entry point for windowed log analysis.

    RETURNS
        Process exit code (0 on success).

    SIDE EFFECTS
        Reads logs and prints summaries to stdout.
    """
    parser = argparse.ArgumentParser(
        description="Summarize API class/index counts per time window from python-can text logs."
    )
    parser.add_argument("log", help="Path to .log or .blf file")
    parser.add_argument(
        "--window",
        action="append",
        default=[],
        help="Window as start_seconds,duration_seconds,label (repeatable)",
    )
    parser.add_argument(
        "--relative",
        action="store_true",
        help="Use timestamps relative to the first frame (recommended for .blf)",
    )
    parser.add_argument("--mfg", type=int, default=5, help="Manufacturer filter (default: 5 REV)")
    parser.add_argument("--dtype", type=int, default=2, help="Device type filter (default: 2 MotorController)")
    parser.add_argument("--device-id", type=int, default=None, help="Device ID filter")
    parser.add_argument("--top", type=int, default=10, help="Top N API class/index per window")
    args = parser.parse_args()

    windows = parse_windows(args.window)
    if not windows:
        raise SystemExit("At least one --window is required.")

    frames = list(iter_frames(Path(args.log)))
    if not frames:
        raise SystemExit("No frames parsed from log.")

    if args.relative:
        first_ts = min(ts for ts, _ in frames)
        frames = [(ts - first_ts, arb) for ts, arb in frames]

    for start, duration, label in windows:
        counts: Counter[Tuple[int, int]] = Counter()
        for ts, arb in frames:
            if not within_window(ts, start, duration):
                continue
            if arb <= 0x7FF:
                continue
            decoded = decode_ext_id(arb)
            if decoded.manufacturer != args.mfg:
                continue
            if decoded.device_type != args.dtype:
                continue
            if args.device_id is not None and decoded.device_id != args.device_id:
                continue
            counts[(decoded.api_class, decoded.api_index)] += 1

        print(f"Window '{label}' start={start:.3f}s duration={duration:.3f}s")
        if not counts:
            print("  No matching frames.")
            print()
            continue
        for (api_class, api_index), count in counts.most_common(args.top):
            print(f"  api_class={api_class:>2} api_index={api_index:>2} count={count}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
