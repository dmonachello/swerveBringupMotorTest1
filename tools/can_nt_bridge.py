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
from typing import Dict, Iterable, Optional, Tuple, Any, List


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


def _default_device_ids() -> Tuple[int, ...]:
    return _parse_ids("10,1,7,4,2,5,8,11,12,3,9,6")


def _device_type_labels(device_ids: Iterable[int]) -> Dict[int, str]:
    labels: Dict[int, str] = {}
    neo_ids = {10, 1, 7, 4}
    kraken_ids = {11, 2, 8, 5}
    cancoder_ids = {12, 3, 9, 6}
    for device_id in device_ids:
        if device_id in cancoder_ids:
            labels[device_id] = "CANCoder"
        elif device_id in kraken_ids:
            labels[device_id] = "KRAKEN"
        elif device_id in neo_ids:
            labels[device_id] = "NEO"
        else:
            labels[device_id] = "Unknown"
    return labels


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


def _nt_is_connected(kind: str, inst) -> Optional[bool]:
    try:
        if kind == "ntcore":
            return bool(inst.isConnected())
        if kind == "pynetworktables":
            return bool(inst.isConnected())
    except Exception:
        return None
    return None


def _auto_channel(match_text: str, prompt: bool) -> Tuple[str, str]:
    try:
        import serial.tools.list_ports  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "pyserial is required for auto-detecting the CANable port. "
            "Install it with: py -m pip install pyserial"
        ) from exc

    matches = []
    for port in serial.tools.list_ports.comports():
        desc = port.description or ""
        if match_text.lower() in desc.lower():
            matches.append((port.device, desc))

    if not matches:
        raise RuntimeError(
            f"No serial ports matched '{match_text}'. "
            "Specify --channel explicitly (e.g., COM3)."
        )

    if len(matches) > 1:
        if not prompt:
            raise RuntimeError(
                "Multiple serial ports matched "
                f"'{match_text}': {', '.join(dev for dev, _ in matches)}. "
                "Specify --channel explicitly."
            )
        print("Multiple matching serial ports found:")
        for idx, (dev, desc) in enumerate(matches, start=1):
            print(f"  {idx}. {dev} ({desc})")
        choice = input("Select port by number: ").strip()
        if not choice.isdigit():
            raise RuntimeError("Invalid selection. Specify --channel explicitly.")
        index = int(choice) - 1
        if index < 0 or index >= len(matches):
            raise RuntimeError("Selection out of range. Specify --channel explicitly.")
        return matches[index]

    return matches[0]


def _device_id_from_arb_id(arb_id: int) -> int:
    # FRC CAN device ID is carried in the lowest 6 bits of the extended ID.
    return arb_id & 0x3F


def _load_config(path: str) -> Dict[str, Any]:
    if not path:
        return {}
    try:
        import json
        import os

        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception as exc:
        raise RuntimeError(f"Failed to read config file: {path}") from exc


def _get_config_path(argv: Optional[Iterable[str]]) -> str:
    args = list(argv) if argv is not None else sys.argv[1:]
    if "--config" in args:
        idx = args.index("--config")
        if idx + 1 < len(args):
            return args[idx + 1]
    return "tools/can_nt_config.json"


def _coerce_labels(raw: Any) -> Dict[int, str]:
    if not isinstance(raw, dict):
        return {}
    labels: Dict[int, str] = {}
    for key, value in raw.items():
        try:
            device_id = int(key)
        except Exception:
            continue
        if isinstance(value, str):
            labels[device_id] = value
    return labels


def _list_ports() -> List[Tuple[str, str]]:
    try:
        import serial.tools.list_ports  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "pyserial is required for listing serial ports. "
            "Install it with: py -m pip install pyserial"
        ) from exc
    ports = []
    for port in serial.tools.list_ports.comports():
        ports.append((port.device, port.description or ""))
    return ports


def main(argv: Optional[Iterable[str]] = None) -> int:
    config_path = _get_config_path(argv)
    config = _load_config(config_path)

    default_ids = _default_device_ids()
    if isinstance(config.get("device_ids"), list) and config["device_ids"]:
        default_ids = tuple(int(x) for x in config["device_ids"])

    default_labels = _device_type_labels(default_ids)
    default_labels.update(_coerce_labels(config.get("labels")))

    parser = argparse.ArgumentParser(description="CAN -> NetworkTables bridge")
    parser.add_argument("--config", default=config_path, help="Path to JSON config")
    parser.add_argument("--rio", default=config.get("rio", "172.22.11.2"), help="RoboRIO IP/host")
    parser.add_argument(
        "--device-ids",
        type=_parse_ids,
        default=default_ids,
        help="Comma-separated CAN IDs to report",
    )
    parser.add_argument(
        "--interface",
        default=config.get("interface", "slcan"),
        help="python-can interface (default: slcan)",
    )
    parser.add_argument(
        "--channel",
        default=config.get("channel", ""),
        help="CAN channel (for slcan, the COM port like COM3). "
        "If omitted, attempts auto-detect by description.",
    )
    parser.add_argument(
        "--bitrate",
        type=int,
        default=int(config.get("bitrate", 1_000_000)),
        help="CAN bitrate (default: 1000000 for FRC)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(config.get("timeout", 1.0)),
        help="Seconds without frames before marking missing",
    )
    parser.add_argument(
        "--publish-period",
        type=float,
        default=float(config.get("publish_period", 0.2)),
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
        default=float(config.get("print_summary_period", 2.0)),
        help="Seconds between summary prints (0 to disable)",
    )
    parser.add_argument(
        "--no-traffic-secs",
        type=float,
        default=float(config.get("no_traffic_secs", 5.0)),
        help="Seconds with zero CAN frames before printing a warning (0 to disable)",
    )
    parser.add_argument(
        "--no-rio-secs",
        type=float,
        default=float(config.get("no_rio_secs", 5.0)),
        help="Seconds between warnings if not connected to the RIO (0 to disable)",
    )
    parser.add_argument(
        "--auto-match",
        default=config.get("auto_match", "USB Serial Device"),
        help="Substring to match when auto-detecting serial ports",
    )
    parser.add_argument(
        "--no-prompt",
        action="store_true",
        help="Disable port selection prompt when multiple matches are found",
    )
    parser.add_argument(
        "--list-ports",
        action="store_true",
        help="List available serial ports and exit",
    )
    parser.add_argument(
        "--debug-imports",
        action="store_true",
        help="Print sys.path and site-package locations when imports fail",
    )
    args = parser.parse_args(argv)

    if args.list_ports:
        ports = _list_ports()
        if not ports:
            print("No serial ports found.")
        else:
            print("Available serial ports:")
            for dev, desc in ports:
                print(f"  {dev} ({desc})")
        return 0

    nt_kind, nt_inst, diag_table = _init_nt(args.rio, args.debug_imports)
    channel = args.channel
    if not channel:
        channel, channel_desc = _auto_channel(args.auto_match, not args.no_prompt)
        print(f"Auto-detected CAN channel: {channel} ({channel_desc})")
    bus = _init_can(args.interface, channel, args.bitrate)

    device_ids = list(args.device_ids)
    device_labels = _device_type_labels(device_ids)
    device_labels.update(default_labels)
    last_seen: Dict[int, float] = {}
    msg_count: Dict[int, int] = {}
    bus_error_count = 0
    last_publish = 0.0
    last_summary = 0.0
    last_traffic_warn = 0.0
    last_rio_warn = 0.0
    total_frames = 0
    summary_frames = 0
    summary_errors = 0

    default_rio = config.get("rio", "172.22.11.2")
    if args.rio != default_rio:
        print(f"RIO IP: {args.rio} (default {default_rio})")
    else:
        print(f"RIO IP: {args.rio}")
    print(f"NetworkTables client: {nt_kind}")
    print(f"CAN: interface={args.interface} channel={channel} bitrate={args.bitrate}")
    print(f"Tracking device IDs: {', '.join(str(i) for i in device_ids)}")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            now = time.time()
            msg = bus.recv(timeout=0.05)

            if msg is not None:
                if getattr(msg, "is_error_frame", False):
                    bus_error_count += 1
                    summary_errors += 1
                else:
                    device_id = _device_id_from_arb_id(msg.arbitration_id)
                    prev_seen = last_seen.get(device_id)
                    prev_missing = prev_seen is None or (now - prev_seen) > args.timeout
                    last_seen[device_id] = now
                    msg_count[device_id] = msg_count.get(device_id, 0) + 1
                    total_frames += 1
                    summary_frames += 1
                    if args.print_publish and prev_missing:
                        print(f"Device seen: id={device_id} count={msg_count[device_id]}")
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
                        diag_table.getEntry(f"type/{device_id}").setString(
                            device_labels.get(device_id, "Unknown")
                        )
                    else:
                        diag_table.getEntry(f"missing/{device_id}").setBoolean(True)
                        diag_table.getEntry(f"msgCount/{device_id}").setDouble(0.0)
                        diag_table.getEntry(f"type/{device_id}").setString(
                            device_labels.get(device_id, "Unknown")
                        )

                last_publish = now

            if args.print_summary_period > 0 and (now - last_summary) >= args.print_summary_period:
                timestamp = time.strftime("%H:%M:%S", time.localtime(now))
                period = now - last_summary if last_summary > 0 else args.print_summary_period
                fps = (summary_frames / period) if period > 0 else 0.0
                err_rate = (summary_errors / period) if period > 0 else 0.0
                missing_count = 0
                lines = [f"Summary @ {timestamp}"]
                for device_id in device_ids:
                    count = msg_count.get(device_id, 0)
                    ts = last_seen.get(device_id)
                    missing = ts is None or (now - ts) > args.timeout
                    if missing:
                        missing_count += 1
                    age = None if ts is None else (now - ts)
                    age_text = "n/a" if age is None else f"{age:.2f}s"
                    missing_text = "YES" if missing else "NO"
                    label = device_labels.get(device_id, "Unknown")
                    lines.append(
                        f"  id {device_id:>2}  label={label:<8}  count={count:<6}  missing={missing_text:<3}  age={age_text}"
                    )
                lines.insert(
                    1,
                    f"  Pit check: seen={len(device_ids) - missing_count}/{len(device_ids)} "
                    f"missing={missing_count} frames/s={fps:.1f} errors/s={err_rate:.2f}",
                )
                print("\n".join(lines))
                last_summary = now
                summary_frames = 0
                summary_errors = 0

            if args.no_traffic_secs > 0 and (now - last_traffic_warn) >= args.no_traffic_secs:
                if total_frames == 0:
                    timestamp = time.strftime("%H:%M:%S", time.localtime(now))
                    print(f"No CAN traffic detected as of {timestamp}.")
                last_traffic_warn = now

            if args.no_rio_secs > 0 and (now - last_rio_warn) >= args.no_rio_secs:
                connected = _nt_is_connected(nt_kind, nt_inst)
                if connected is False:
                    timestamp = time.strftime("%H:%M:%S", time.localtime(now))
                    print(f"Not connected to RIO NetworkTables as of {timestamp}.")
                last_rio_warn = now
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
