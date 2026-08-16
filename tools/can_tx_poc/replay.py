from __future__ import annotations

"""
NAME
    replay.py - Explicitly authorized experimental live CAN replay.

SYNOPSIS
    python -m tools.can_tx_poc.replay --channel COM3 --sequence frames.txt
        --tx-allow

DESCRIPTION
    Replays timestamped CAN frames on a live bus for isolated lab experiments.
    This module is not part of the supported passive diagnostics runtime.

SIDE EFFECTS
    Transmits CAN frames only when --tx-allow is present.
"""

import argparse
import time
from pathlib import Path
from typing import Any, List, Optional, Sequence, Tuple

from tools.common.text_io import read_lines


ARG_BITRATE = "--bitrate"
ARG_CHANNEL = "--channel"
ARG_INTERFACE = "--interface"
ARG_LOOP = "--loop"
ARG_SCALE = "--scale"
ARG_SEQUENCE = "--sequence"
ARG_TX_ALLOW = "--tx-allow"
ARG_VERBOSE = "--verbose"
DEFAULT_BITRATE = 1_000_000
DEFAULT_INTERFACE = "slcan"
DEFAULT_SCALE = 1.0
EMPTY_STRING = ""
ERROR_AUTHORIZATION_REQUIRED = (
    "ERROR: live CAN replay is disabled. Pass --tx-allow only in an isolated lab."
)
ERROR_BUS_OPEN = "ERROR: failed to open CAN bus: {error}"
ERROR_EMPTY_SEQUENCE = "ERROR: sequence contains no valid CAN frames."
ERROR_READ_SEQUENCE = "ERROR: failed to read sequence file '{path}': {error}"
ERROR_SEND = "ERROR: failed to send id=0x{can_id:X}: {error}"
EXIT_ERROR = 2
EXIT_SUCCESS = 0
HELP_BITRATE = "CAN bitrate."
HELP_CHANNEL = "CAN channel, such as COM3 for slcan."
HELP_INTERFACE = "python-can interface."
HELP_LOOP = "Loop the sequence until interrupted."
HELP_SCALE = "Timing scale where 1.0 is realtime."
HELP_SEQUENCE = "Timestamped CAN sequence file."
HELP_TX_ALLOW = "Authorize live CAN transmission for this invocation."
HELP_VERBOSE = "Print transmitted frame details."
MAX_STANDARD_CAN_ID = 0x7FF
MIN_SLEEP_SEC = 0.01
PARSER_DESCRIPTION = "EXPERIMENTAL: replay CAN frames on a live lab bus"
PRINT_FINISHED = "TX sequence finished. Sent {count} frames in {elapsed:.2f}s."
PRINT_SENT = "TX sent #{count} id=0x{can_id:X} len={length} data={data}"
VERBOSE_INITIAL_COUNT = 5
VERBOSE_PERIOD = 100

Frame = Tuple[float, int, bytes]


def build_parser() -> argparse.ArgumentParser:
    """
    NAME
        build_parser - Build the isolated PoC command parser.

    RETURNS
        Parser requiring an explicit channel and sequence path.
    """
    parser = argparse.ArgumentParser(description=PARSER_DESCRIPTION)
    parser.add_argument(ARG_CHANNEL, required=True, help=HELP_CHANNEL)
    parser.add_argument(ARG_SEQUENCE, required=True, help=HELP_SEQUENCE)
    parser.add_argument(ARG_INTERFACE, default=DEFAULT_INTERFACE, help=HELP_INTERFACE)
    parser.add_argument(ARG_BITRATE, type=int, default=DEFAULT_BITRATE, help=HELP_BITRATE)
    parser.add_argument(ARG_TX_ALLOW, action="store_true", help=HELP_TX_ALLOW)
    parser.add_argument(ARG_SCALE, type=float, default=DEFAULT_SCALE, help=HELP_SCALE)
    parser.add_argument(ARG_LOOP, action="store_true", help=HELP_LOOP)
    parser.add_argument(ARG_VERBOSE, action="store_true", help=HELP_VERBOSE)
    return parser


def parse_sequence(path: str) -> List[Frame]:
    """
    NAME
        parse_sequence - Load timestamped CAN frames from a sequence file.

    PARAMETERS
        path: File containing tab- or comma-delimited frame rows.

    RETURNS
        Valid frames sorted by timestamp. Invalid rows are skipped.
    """
    entries: List[Frame] = []
    try:
        raw_lines = read_lines(Path(path))
    except Exception as exc:
        print(ERROR_READ_SEQUENCE.format(path=path, error=exc))
        return entries
    for raw in raw_lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        entry = _parse_tab_row(line) if "\t" in line else _parse_csv_row(line)
        if entry is not None:
            entries.append(entry)
    entries.sort(key=lambda row: row[0])
    return entries


def _parse_tab_row(line: str) -> Optional[Frame]:
    """Parse one timestamp, CAN ID, length, and data row."""
    parts = [part.strip() for part in line.split("\t")]
    if len(parts) < 4:
        return None
    try:
        timestamp = float(parts[0])
        can_id = int(parts[1], 0)
        length = int(parts[2])
        data = bytes.fromhex(parts[3].replace(" ", EMPTY_STRING))
    except (TypeError, ValueError):
        return None
    if length >= 0:
        data = data[:length] if len(data) > length else data + bytes(length - len(data))
    return timestamp, can_id, data


def _parse_csv_row(line: str) -> Optional[Frame]:
    """Parse one timestamp, CAN ID, and data row."""
    parts = [part.strip() for part in line.split(",")]
    if len(parts) < 3:
        return None
    try:
        return (
            float(parts[0]),
            int(parts[1], 0),
            bytes.fromhex(parts[2].replace(" ", EMPTY_STRING)),
        )
    except (TypeError, ValueError):
        return None


def replay_sequence(
    bus: Any,
    can_module: Any,
    sequence: Sequence[Frame],
    *,
    scale: float,
    loop: bool,
    verbose: bool,
) -> int:
    """
    NAME
        replay_sequence - Replay frames synchronously with captured timing.

    SIDE EFFECTS
        Sends each frame through the provided live CAN bus.

    RETURNS
        Number of successfully transmitted frames.
    """
    sent = 0
    sequence_start = sequence[0][0]
    replay_start = time.monotonic()
    while True:
        iteration_start = time.monotonic()
        for timestamp, can_id, data in sequence:
            delay = max(0.0, (timestamp - sequence_start) * scale)
            remaining = (iteration_start + delay) - time.monotonic()
            while remaining > 0:
                time.sleep(min(MIN_SLEEP_SEC, remaining))
                remaining = (iteration_start + delay) - time.monotonic()
            try:
                message = can_module.Message(
                    arbitration_id=can_id,
                    data=data,
                    is_extended_id=can_id > MAX_STANDARD_CAN_ID,
                )
                bus.send(message)
            except Exception as exc:
                print(ERROR_SEND.format(can_id=can_id, error=exc))
                return sent
            sent += 1
            if verbose and (sent <= VERBOSE_INITIAL_COUNT or sent % VERBOSE_PERIOD == 0):
                print(
                    PRINT_SENT.format(
                        count=sent,
                        can_id=can_id,
                        length=len(data),
                        data=data.hex(),
                    )
                )
        if not loop:
            break
    print(PRINT_FINISHED.format(count=sent, elapsed=time.monotonic() - replay_start))
    return sent


def run(args: argparse.Namespace, can_module: Any = None) -> int:
    """
    NAME
        run - Validate authorization, open the bus, and execute replay.

    ERRORS
        Returns nonzero before opening the bus when authorization is absent.
    """
    if not args.tx_allow:
        print(ERROR_AUTHORIZATION_REQUIRED)
        return EXIT_ERROR
    sequence = parse_sequence(args.sequence)
    if not sequence:
        print(ERROR_EMPTY_SEQUENCE)
        return EXIT_ERROR
    if can_module is None:
        import can as can_module  # type: ignore
    try:
        bus = can_module.Bus(
            interface=args.interface,
            channel=args.channel,
            bitrate=args.bitrate,
        )
    except Exception as exc:
        print(ERROR_BUS_OPEN.format(error=exc))
        return EXIT_ERROR
    try:
        replay_sequence(
            bus,
            can_module,
            sequence,
            scale=args.scale,
            loop=args.loop,
            verbose=args.verbose,
        )
    except KeyboardInterrupt:
        pass
    finally:
        bus.shutdown()
    return EXIT_SUCCESS


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Parse command arguments and run the experimental replay."""
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
