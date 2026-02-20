#!/usr/bin/env python3
"""
CAN -> NetworkTables bridge for RobotV2 bringup diagnostics.

Publishes:
  bringup/diag/busErrorCount
  bringup/diag/lastSeen/<deviceId>
  bringup/diag/missing/<deviceId>
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Dict, Iterable, Optional, Tuple


def _parse_ids(value: str) -> Tuple[int, ...]:
    items = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        items.append(int(part))
    if not items:
        raise argparse.ArgumentTypeError("Expected at least one CAN ID")
    return tuple(items)


def _init_nt(rio: str, debug: bool):
    try:
        from ntcore import NetworkTableInstance  # type: ignore

        inst = NetworkTableInstance.getDefault()
        inst.startClient4("can-nt-bridge")
        inst.setServer(rio)
        table = inst.getTable("bringup").getSubTable("diag")
        return ("ntcore", inst, table)
    except Exception:
        # Ensure site-packages are on sys.path even if Python was started with -S
        # or user site-packages are disabled.
        try:
            import site as _site  # type: ignore
            import sysconfig as _sysconfig
            import sys as _sys

            _site.main()
            paths = []
            try:
                paths.append(_site.getusersitepackages())
            except Exception:
                pass
            try:
                paths.extend(_site.getsitepackages())
            except Exception:
                pass
            try:
                paths.append(_sysconfig.get_paths().get("purelib"))
            except Exception:
                pass
            for path in paths:
                if path:
                    _site.addsitedir(path)
            if debug:
                print("DEBUG: sys.executable =", _sys.executable)
                print("DEBUG: sys.path:")
                for entry in _sys.path:
                    print("  ", entry)
                print("DEBUG: candidate site-packages:")
                for entry in paths:
                    if entry:
                        print("  ", entry)
        except Exception:
            pass
        try:
            from networktables import NetworkTables  # type: ignore

            NetworkTables.initialize(server=rio)
            table = NetworkTables.getTable("bringup").getSubTable("diag")
            return ("pynetworktables", NetworkTables, table)
        except Exception as exc:
            raise RuntimeError(
                "Failed to import ntcore or pynetworktables. "
                "Install one of them to use NetworkTables."
            ) from exc


def _init_can(interface: str, channel: str, bitrate: int):
    try:
        import can  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "python-can is not installed. Install it with: py -m pip install python-can"
        ) from exc

    try:
        return can.Bus(interface=interface, channel=channel, bitrate=bitrate)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to open CAN bus (interface={interface}, channel={channel}, bitrate={bitrate})."
        ) from exc


def _device_id_from_arb_id(arb_id: int) -> int:
    # FRC CAN device ID is carried in the lowest 6 bits of the extended ID.
    return arb_id & 0x3F


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="CAN -> NetworkTables bridge")
    parser.add_argument("--rio", default="172.22.11.2", help="RoboRIO IP/host")
    parser.add_argument(
        "--device-ids",
        type=_parse_ids,
        default=_parse_ids("2,5,8,11,12,3,9,6"),
        help="Comma-separated CAN IDs to report",
    )
    parser.add_argument(
        "--interface",
        default="slcan",
        help="python-can interface (default: slcan)",
    )
    parser.add_argument(
        "--channel",
        default="COM3",
        help="CAN channel (for slcan, the COM port like COM3)",
    )
    parser.add_argument(
        "--bitrate",
        type=int,
        default=1_000_000,
        help="CAN bitrate (default: 1000000 for FRC)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=1.0,
        help="Seconds without frames before marking missing",
    )
    parser.add_argument(
        "--publish-period",
        type=float,
        default=0.2,
        help="Seconds between NetworkTables updates",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print received device IDs",
    )
    parser.add_argument(
        "--print-publish",
        action="store_true",
        help="Print a line each time NetworkTables is updated",
    )
    parser.add_argument(
        "--print-summary-period",
        type=float,
        default=2.0,
        help="Seconds between summary prints (0 to disable)",
    )
    parser.add_argument(
        "--debug-imports",
        action="store_true",
        help="Print sys.path and site-package locations when imports fail",
    )
    args = parser.parse_args(argv)

    nt_kind, nt_inst, diag_table = _init_nt(args.rio, args.debug_imports)
    bus = _init_can(args.interface, args.channel, args.bitrate)

    device_ids = list(args.device_ids)
    last_seen: Dict[int, float] = {}
    msg_count: Dict[int, int] = {}
    bus_error_count = 0
    last_publish = 0.0
    last_summary = 0.0

    print(f"NetworkTables: {nt_kind} -> {args.rio}")
    print(f"CAN: interface={args.interface} channel={args.channel} bitrate={args.bitrate}")
    print(f"Tracking device IDs: {', '.join(str(i) for i in device_ids)}")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            now = time.time()
            msg = bus.recv(timeout=0.05)

            if msg is not None:
                if getattr(msg, "is_error_frame", False):
                    bus_error_count += 1
                else:
                    device_id = _device_id_from_arb_id(msg.arbitration_id)
                    last_seen[device_id] = now
                    msg_count[device_id] = msg_count.get(device_id, 0) + 1
                    if args.verbose:
                        print(f"RX id={device_id} arb=0x{msg.arbitration_id:X}")

            if now - last_publish >= args.publish_period:
                diag_table.getEntry("busErrorCount").setDouble(bus_error_count)

                for device_id in device_ids:
                    ts = last_seen.get(device_id)
                    if ts is not None:
                        diag_table.getEntry(f"lastSeen/{device_id}").setDouble(ts)
                        missing = (now - ts) > args.timeout
                        diag_table.getEntry(f"missing/{device_id}").setBoolean(missing)
                        diag_table.getEntry(f"msgCount/{device_id}").setDouble(
                            float(msg_count.get(device_id, 0))
                        )
                    else:
                        diag_table.getEntry(f"missing/{device_id}").setBoolean(True)
                        diag_table.getEntry(f"msgCount/{device_id}").setDouble(0.0)

                if args.print_publish:
                    print(
                        f"NT publish: busErrorCount={bus_error_count} "
                        f"tracked={len(device_ids)}"
                    )
                last_publish = now

            if args.print_summary_period > 0 and (now - last_summary) >= args.print_summary_period:
                lines = []
                for device_id in device_ids:
                    count = msg_count.get(device_id, 0)
                    ts = last_seen.get(device_id)
                    missing = ts is None or (now - ts) > args.timeout
                    lines.append(
                        f"{device_id}: count={count} missing={missing}"
                    )
                print("Summary: " + " | ".join(lines))
                last_summary = now
    except KeyboardInterrupt:
        print("Stopping.")
    finally:
        try:
            bus.shutdown()
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
