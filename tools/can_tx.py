from __future__ import annotations

"""
NAME
    can_tx.py - CAN transmit replay helper (offline analysis aid).

SYNOPSIS
    from can_tx import start_tx_if_requested

DESCRIPTION
    Parses a timestamped CAN sequence file and replays frames on a live bus.
    Intended for controlled lab use only.

SIDE EFFECTS
    Transmits CAN frames when enabled.
"""

import threading
import time
from pathlib import Path
from typing import List, Tuple


def parse_tx_sequence(path: str) -> List[Tuple[float, int, bytes]]:
    """
    NAME
        parse_tx_sequence - Load timestamped CAN frames from a file.

    PARAMETERS
        path: Sequence file path.

    RETURNS
        List of (timestamp, arbitration_id, data) tuples sorted by time.

    ERRORS
        Prints warnings and returns partial data on parse failures.
    """
    entries: List[Tuple[float, int, bytes]] = []
    try:
        raw_lines = Path(path).read_text(encoding="utf-8").splitlines()
    except Exception as exc:
        print(f"ERROR: Failed to read TX sequence file '{path}': {exc}")
        return entries
    for raw in raw_lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "\t" in line:
            parts = [p.strip() for p in line.split("\t")]
            if len(parts) < 4:
                continue
            try:
                t = float(parts[0])
                can_id = int(parts[1], 0)
                length = int(parts[2])
                data_hex = parts[3].replace(" ", "")
                data = bytes.fromhex(data_hex)
            except Exception:
                continue
            if length >= 0:
                if len(data) < length:
                    data = data + bytes(length - len(data))
                elif len(data) > length:
                    data = data[:length]
            entries.append((t, can_id, data))
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3:
            continue
        try:
            t = float(parts[0])
            can_id = int(parts[1], 0)
            data_hex = parts[2].replace(" ", "")
            data = bytes.fromhex(data_hex)
        except Exception:
            continue
        entries.append((t, can_id, data))
    entries.sort(key=lambda r: r[0])
    return entries


def tx_worker(
    bus,
    can_module,
    sequence: List[Tuple[float, int, bytes]],
    stop_event: threading.Event,
    scale: float,
    loop: bool,
    verbose: bool,
) -> None:
    """
    NAME
        tx_worker - Replay a sequence of CAN frames with timing control.

    PARAMETERS
        bus: CAN bus object with send() support.
        can_module: python-can module for Message construction.
        sequence: Ordered frame list from parse_tx_sequence.
        stop_event: Event to terminate replay.
        scale: Timing scale factor (1.0 = realtime).
        loop: Whether to loop until stopped.
        verbose: Whether to print periodic send status.

    SIDE EFFECTS
        Sends CAN frames on the bus.
    """
    if not sequence:
        print("TX sequence is empty. Nothing to send.")
        return
    sent = 0
    start_time = sequence[0][0]
    start_wall = time.monotonic()
    while True:
        t0 = time.monotonic()
        for ts, can_id, data in sequence:
            if stop_event.is_set():
                break
            delay = max(0.0, (ts - start_time) * scale)
            while not stop_event.is_set():
                now = time.monotonic()
                remaining = (t0 + delay) - now
                if remaining <= 0:
                    break
                time.sleep(min(0.01, remaining))
            if stop_event.is_set():
                break
            try:
                msg = can_module.Message(
                    arbitration_id=can_id,
                    data=data,
                    is_extended_id=(can_id > 0x7FF),
                )
                bus.send(msg)
                sent += 1
                if verbose and (sent <= 5 or sent % 100 == 0):
                    print(f"TX sent #{sent} id=0x{can_id:X} len={len(data)} data={data.hex()}")
            except Exception as exc:
                print(f"TX error sending id=0x{can_id:X}: {exc}")
                stop_event.set()
                break
        if stop_event.is_set() or not loop:
            break
    elapsed = time.monotonic() - start_wall
    print(f"TX sequence finished. Sent {sent} frames in {elapsed:.2f}s.")


def start_tx_if_requested(
    args,
    bus,
    can_module,
    tx_stop: threading.Event,
):
    """
    NAME
        start_tx_if_requested - Launch the TX replay thread when configured.

    PARAMETERS
        args: Parsed CLI args with tx settings.
        bus: CAN bus object.
        can_module: python-can module.
        tx_stop: Stop event shared with the main loop.

    RETURNS
        Thread object when started, otherwise None.
    """
    if not args.tx_seq:
        return None
    sequence = parse_tx_sequence(args.tx_seq)
    tx_thread = threading.Thread(
        target=tx_worker,
        args=(bus, can_module, sequence, tx_stop, args.tx_scale, args.tx_loop, args.tx_verbose),
        daemon=True,
    )
    tx_thread.start()
    return tx_thread
