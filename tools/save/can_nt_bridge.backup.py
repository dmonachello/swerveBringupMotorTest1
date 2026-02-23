#!/usr/bin/env python3
"""
CAN -> NetworkTables bridge for RobotV2 bringup diagnostics.

Publishes:
  bringup/diag/busErrorCount
  bringup/diag/dev/<mfg>/<type>/<id>/label
  bringup/diag/dev/<mfg>/<type>/<id>/status
  bringup/diag/dev/<mfg>/<type>/<id>/ageSec
  bringup/diag/dev/<mfg>/<type>/<id>/msgCount
  bringup/diag/dev/<mfg>/<type>/<id>/lastSeen
  bringup/diag/dev/<mfg>/<type>/<id>/manufacturer
  bringup/diag/dev/<mfg>/<type>/<id>/deviceType
  bringup/diag/dev/<mfg>/<type>/<id>/deviceId
  bringup/diag/lastSeen/<deviceId> (legacy aggregate)
  bringup/diag/missing/<deviceId> (legacy aggregate)
  bringup/diag/msgCount/<deviceId> (legacy aggregate)
  bringup/diag/type/<deviceId> (legacy aggregate)
  bringup/diag/status/<deviceId> (legacy aggregate)
  bringup/diag/ageSec/<deviceId> (legacy aggregate)
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


DEFAULT_DEVICES = [
    # {"label": "FR NEO", "manufacturer": 5, "device_type": 2, "device_id": 10, "group": "neos"},
    # {"label": "FL NEO", "manufacturer": 5, "device_type": 2, "device_id": 1, "group": "neos"},
    # {"label": "BR NEO", "manufacturer": 5, "device_type": 2, "device_id": 7, "group": "neos"},
    # {"label": "BL NEO", "manufacturer": 5, "device_type": 2, "device_id": 4, "group": "neos"},
    # {"label": "FR KRAK", "manufacturer": 4, "device_type": 2, "device_id": 11, "group": "krakens"},
    # {"label": "FL KRAK", "manufacturer": 4, "device_type": 2, "device_id": 2, "group": "krakens"},
    # {"label": "BR KRAK", "manufacturer": 4, "device_type": 2, "device_id": 8, "group": "krakens"},
    # {"label": "BL KRAK", "manufacturer": 4, "device_type": 2, "device_id": 5, "group": "krakens"},
    # {"label": "FR CANC", "manufacturer": 4, "device_type": 7, "device_id": 12, "group": "cancoders"},
    # {"label": "FL CANC", "manufacturer": 4, "device_type": 7, "device_id": 3, "group": "cancoders"},
    # {"label": "BR CANC", "manufacturer": 4, "device_type": 7, "device_id": 9, "group": "cancoders"},
    # {"label": "BL CANC", "manufacturer": 4, "device_type": 7, "device_id": 6, "group": "cancoders"},
    # {"label": "PDH", "manufacturer": 5, "device_type": 8, "device_id": 1, "group": "power"},
    # {"label": "Pigeon", "manufacturer": 4, "device_type": 4, "device_id": 1, "group": "sensors"},
    {"label": "NEO 22", "manufacturer": 5, "device_type": 2, "device_id": 22, "group": "neos"},
    {"label": "NEO 25", "manufacturer": 5, "device_type": 2, "device_id": 25, "group": "neos"},
    {"label": "NEO 10", "manufacturer": 5, "device_type": 2, "device_id": 10, "group": "neos"},
]


def _default_device_ids() -> Tuple[int, ...]:
    return _parse_ids("22,25,10")



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


def _nt_connection_info(kind: str, inst) -> str:
    try:
        if kind == "ntcore":
            connections = inst.getConnections()
            if connections:
                addresses = ", ".join(conn.remote_id for conn in connections)
                return f"connections: {addresses}"
            return "connections: none"
        if kind == "pynetworktables":
            addr = inst.getRemoteAddress()
            if addr:
                return f"remote: {addr}"
            return "remote: none"
    except Exception:
        return "connection info: unavailable"
    return "connection info: unavailable"


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


def _decode_ext_id(arb_id: int) -> Tuple[int, int, int, int, int]:
    device_type = (arb_id >> 24) & 0x1F
    manufacturer = (arb_id >> 16) & 0xFF
    api_class = (arb_id >> 10) & 0x3F
    api_index = (arb_id >> 6) & 0x0F
    device_id = arb_id & 0x3F
    return (manufacturer, device_type, api_class, api_index, device_id)


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


def _parse_devices(raw: Any) -> List[Dict[str, Any]]:
    devices: List[Dict[str, Any]] = []
    if not isinstance(raw, list):
        return devices
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        try:
            manufacturer = int(entry.get("manufacturer"))
            device_type = int(entry.get("device_type"))
            device_id = int(entry.get("device_id"))
        except Exception:
            continue
        label = entry.get("label") or f"{manufacturer}:{device_type}:{device_id}"
        group = entry.get("group")
        devices.append(
            {
                "manufacturer": manufacturer,
                "device_type": device_type,
                "device_id": device_id,
                "label": str(label),
                "group": str(group) if group is not None else "",
            }
        )
    return devices


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


def _coerce_groups(raw: Any) -> Dict[str, List[Any]]:
    if not isinstance(raw, dict):
        return {}
    groups: Dict[str, List[Any]] = {}
    for name, value in raw.items():
        if not isinstance(name, str):
            continue
        if isinstance(value, list):
            items: List[Any] = []
            for item in value:
                if isinstance(item, str):
                    items.append(item)
                else:
                    try:
                        items.append(int(item))
                    except Exception:
                        continue
            if items:
                groups[name] = items
    return groups


def _format_status(ts: Optional[float], now: float, timeout: float) -> Tuple[str, Optional[float], bool]:
    if ts is None:
        return ("MISSING", None, True)
    age = now - ts
    if age > timeout:
        return ("STALE", age, True)
    return ("OK", age, False)


def _write_csv_header(handle, specs: List[Dict[str, Any]], groups: Dict[str, List[Tuple[int, int, int]]]) -> None:
    base = ["timestamp", "busErrorCount", "framesPerSec", "errorsPerSec"]
    per_id = []
    for spec in specs:
        device_id = spec["device_id"]
        key = f"m{spec['manufacturer']}_t{spec['device_type']}_id{device_id}"
        per_id.extend(
            [
                f"{key}_count",
                f"{key}_ageSec",
                f"{key}_status",
            ]
        )
    group_cols = []
    for name in groups.keys():
        group_cols.extend([f"group_{name}_seen", f"group_{name}_missing"])
    handle.write(",".join(base + per_id + group_cols) + "\n")


def _write_csv_row(
    handle,
    timestamp: float,
    bus_error_count: int,
    fps: float,
    err_rate: float,
    specs: List[Dict[str, Any]],
    last_seen: Dict[Tuple[int, int, int], float],
    timeout: float,
    groups: Dict[str, List[Tuple[int, int, int]]],
    now: float,
    msg_count: Dict[Tuple[int, int, int], int],
):
    row = [f"{timestamp:.3f}", str(bus_error_count), f"{fps:.2f}", f"{err_rate:.2f}"]
    for spec in specs:
        key = (spec["manufacturer"], spec["device_type"], spec["device_id"])
        ts = last_seen.get(key)
        status, age, _missing = _format_status(ts, now, timeout)
        row.append(str(msg_count.get(key, 0)))
        row.append("" if age is None else f"{age:.3f}")
        row.append(status)
    for name, keys in groups.items():
        seen = 0
        missing = 0
        for key in keys:
            ts = last_seen.get(key)
            _status, _age, is_missing = _format_status(ts, now, timeout)
            if is_missing:
                missing += 1
            else:
                seen += 1
        row.extend([str(seen), str(missing)])
    handle.write(",".join(row) + "\n")


def _build_summary_lines(
    specs: List[Dict[str, Any]],
    last_seen: Dict[Tuple[int, int, int], float],
    msg_count: Dict[Tuple[int, int, int], int],
    timeout: float,
    fps: float,
    err_rate: float,
    groups: Dict[str, List[Tuple[int, int, int]]],
    now: float,
    title: str = "Summary",
) -> List[str]:
    timestamp = time.strftime("%H:%M:%S", time.localtime(now))
    missing_count = 0
    lines = [f"{title} @ {timestamp}"]
    lines.append(
        f"  Pit check: seen={len(specs) - missing_count}/{len(specs)} "
        f"missing={missing_count} frames/s={fps:.1f} errors/s={err_rate:.2f}"
    )
    for spec in specs:
        key = (spec["manufacturer"], spec["device_type"], spec["device_id"])
        count = msg_count.get(key, 0)
        ts = last_seen.get(key)
        status, age, is_missing = _format_status(ts, now, timeout)
        if is_missing:
            missing_count += 1
        age_text = "n/a" if age is None else f"{age:.2f}s"
        label = spec.get("label", "Unknown")
        lines.append(
            f"  id {spec['device_id']:>2}  label={label:<8}  count={count:<6}  status={status:<7}  age={age_text}"
        )
    lines[1] = (
        f"  Pit check: seen={len(specs) - missing_count}/{len(specs)} "
        f"missing={missing_count} frames/s={fps:.1f} errors/s={err_rate:.2f}"
    )
    if groups:
        for name, keys in groups.items():
            seen = 0
            missing = 0
            for key in keys:
                ts = last_seen.get(key)
                _status, _age, is_missing = _format_status(ts, now, timeout)
                if is_missing:
                    missing += 1
                else:
                    seen += 1
            lines.append(f"  Group {name}: seen={seen}/{len(keys)} missing={missing}")
    return lines


def main(argv: Optional[Iterable[str]] = None) -> int:
    config_path = _get_config_path(argv)
    config = _load_config(config_path)

    devices = _parse_devices(config.get("devices")) or list(DEFAULT_DEVICES)
    legacy_ids = tuple(sorted({int(d["device_id"]) for d in devices}))
    if isinstance(config.get("device_ids"), list) and config["device_ids"]:
        legacy_ids = tuple(int(x) for x in config["device_ids"])
    groups_raw = _coerce_groups(config.get("groups"))

    parser = argparse.ArgumentParser(description="CAN -> NetworkTables bridge")
    parser.add_argument("--config", default=config_path, help="Path to JSON config")
    parser.add_argument("--rio", default=config.get("rio", "172.22.11.2"), help="RoboRIO IP/host")
    parser.add_argument(
        "--device-ids",
        type=_parse_ids,
        default=legacy_ids,
        help="Comma-separated CAN IDs to report (legacy deviceId-only mode)",
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
        help="Print when a device is seen after being missing (uses --timeout)",
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
        "--log-csv",
        default=config.get("log_csv", ""),
        help="Path to CSV log file (empty to disable)",
    )
    parser.add_argument(
        "--log-period",
        type=float,
        default=float(config.get("log_period", 1.0)),
        help="Seconds between CSV log rows (0 to disable)",
    )
    parser.add_argument(
        "--quick-check",
        action="store_true",
        help="Print one summary after a short wait and exit",
    )
    parser.add_argument(
        "--quick-wait",
        type=float,
        default=float(config.get("quick_wait", 1.0)),
        help="Seconds to wait before printing a quick check summary",
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
    device_specs: List[Dict[str, Any]] = []
    for entry in devices:
        device_specs.append(entry)
    label_map = {
        spec["label"]: (spec["manufacturer"], spec["device_type"], spec["device_id"])
        for spec in device_specs
    }
    key_by_id: Dict[int, List[Tuple[int, int, int]]] = {}
    for spec in device_specs:
        key = (spec["manufacturer"], spec["device_type"], spec["device_id"])
        key_by_id.setdefault(spec["device_id"], []).append(key)

    groups: Dict[str, List[Tuple[int, int, int]]] = {}
    if groups_raw:
        for name, items in groups_raw.items():
            keys: List[Tuple[int, int, int]] = []
            for item in items:
                if isinstance(item, str) and item in label_map:
                    keys.append(label_map[item])
                elif isinstance(item, int):
                    keys.extend(key_by_id.get(item, []))
            if keys:
                groups[name] = keys
    else:
        for spec in device_specs:
            group = spec.get("group") or ""
            if group:
                key = (spec["manufacturer"], spec["device_type"], spec["device_id"])
                groups.setdefault(group, []).append(key)

    last_seen: Dict[Tuple[int, int, int], float] = {}
    msg_count: Dict[Tuple[int, int, int], int] = {}
    bus_error_count = 0
    last_publish = 0.0
    last_summary = 0.0
    last_traffic_warn = 0.0
    last_rio_warn = 0.0
    total_frames = 0
    summary_frames = 0
    summary_errors = 0
    last_log = 0.0
    log_handle = None
    csv_header_written = False
    start_time = time.time()
    quick_done = False

    default_rio = config.get("rio", "172.22.11.2")
    if args.rio != default_rio:
        print(f"RIO IP: {args.rio} (default {default_rio})")
    else:
        print(f"RIO IP: {args.rio}")
    print(f"NetworkTables client: {nt_kind}")
    print(f"CAN: interface={args.interface} channel={channel} bitrate={args.bitrate}")
    print(f"Tracking devices: {len(device_specs)} entries")
    print("Press Ctrl+C to stop.")
    if groups:
        print("Groups: " + ", ".join(f"{name}({len(ids)})" for name, ids in groups.items()))
    connected = _nt_is_connected(nt_kind, nt_inst)
    if connected is False:
        print("NT status: NOT connected to RIO")
    elif connected is True:
        print("NT status: connected to RIO")
    print("NT details: " + _nt_connection_info(nt_kind, nt_inst))

    try:
        while True:
            now = time.time()
            msg = bus.recv(timeout=0.05)

            if msg is not None:
                if getattr(msg, "is_error_frame", False):
                    bus_error_count += 1
                    summary_errors += 1
                else:
                    manufacturer, device_type, _api_class, _api_index, device_id = _decode_ext_id(
                        msg.arbitration_id
                    )
                    key = (manufacturer, device_type, device_id)
                    prev_seen = last_seen.get(key)
                    prev_missing = prev_seen is None or (now - prev_seen) > args.timeout
                    last_seen[key] = now
                    msg_count[key] = msg_count.get(key, 0) + 1
                    total_frames += 1
                    summary_frames += 1
                    if args.print_publish and prev_missing:
                        print(
                            f"Device seen: mfg={manufacturer} type={device_type} "
                            f"id={device_id} count={msg_count[key]}"
                        )
                    if args.verbose:
                        print(
                            f"RX mfg={manufacturer} type={device_type} id={device_id} "
                            f"arb=0x{msg.arbitration_id:X}"
                        )

            if now - last_publish >= args.publish_period:
                diag_table.getEntry("busErrorCount").setDouble(bus_error_count)

                # Per-device composite keys: dev/<mfg>/<type>/<id>/...
                for spec in device_specs:
                    key = (spec["manufacturer"], spec["device_type"], spec["device_id"])
                    ts = last_seen.get(key)
                    status, age, is_missing = _format_status(ts, now, args.timeout)
                    base = f"dev/{key[0]}/{key[1]}/{key[2]}"
                    diag_table.getEntry(f"{base}/label").setString(spec.get("label", "Unknown"))
                    diag_table.getEntry(f"{base}/status").setString(status)
                    diag_table.getEntry(f"{base}/ageSec").setDouble(
                        -1.0 if age is None else float(age)
                    )
                    diag_table.getEntry(f"{base}/msgCount").setDouble(
                        float(msg_count.get(key, 0))
                    )
                    diag_table.getEntry(f"{base}/lastSeen").setDouble(
                        -1.0 if ts is None else float(ts)
                    )
                    diag_table.getEntry(f"{base}/manufacturer").setDouble(float(key[0]))
                    diag_table.getEntry(f"{base}/deviceType").setDouble(float(key[1]))
                    diag_table.getEntry(f"{base}/deviceId").setDouble(float(key[2]))

                # Legacy deviceId-only aggregation for backward compatibility.
                for device_id in device_ids:
                    keys = key_by_id.get(device_id, [])
                    if not keys:
                        continue
                    total = 0
                    best_ts = None
                    best_age = None
                    status = "MISSING"
                    for key in keys:
                        ts = last_seen.get(key)
                        s, age, _missing = _format_status(ts, now, args.timeout)
                        total += msg_count.get(key, 0)
                        if ts is not None and (best_ts is None or ts > best_ts):
                            best_ts = ts
                            best_age = age
                        if s == "OK":
                            status = "OK"
                        elif s == "STALE" and status != "OK":
                            status = "STALE"
                    diag_table.getEntry(f"lastSeen/{device_id}").setDouble(
                        -1.0 if best_ts is None else float(best_ts)
                    )
                    diag_table.getEntry(f"missing/{device_id}").setBoolean(status != "OK")
                    diag_table.getEntry(f"msgCount/{device_id}").setDouble(float(total))
                    diag_table.getEntry(f"status/{device_id}").setString(status)
                    diag_table.getEntry(f"ageSec/{device_id}").setDouble(
                        -1.0 if best_age is None else float(best_age)
                    )
                    diag_table.getEntry(f"type/{device_id}").setString("Mixed")

                last_publish = now

            if args.print_summary_period > 0 and (now - last_summary) >= args.print_summary_period:
                period = now - last_summary if last_summary > 0 else args.print_summary_period
                fps = (summary_frames / period) if period > 0 else 0.0
                err_rate = (summary_errors / period) if period > 0 else 0.0
                lines = _build_summary_lines(
                    device_specs,
                    last_seen,
                    msg_count,
                    args.timeout,
                    fps,
                    err_rate,
                    groups,
                    now,
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

            if args.log_csv and args.log_period > 0 and (now - last_log) >= args.log_period:
                if log_handle is None:
                    log_handle = open(args.log_csv, "a", encoding="utf-8")
                if not csv_header_written:
                    _write_csv_header(log_handle, device_specs, groups)
                    csv_header_written = True
                period = now - last_log if last_log > 0 else args.log_period
                fps = (summary_frames / period) if period > 0 else 0.0
                err_rate = (summary_errors / period) if period > 0 else 0.0
                _write_csv_row(
                    log_handle,
                    now,
                    bus_error_count,
                    fps,
                    err_rate,
                    device_specs,
                    last_seen,
                    args.timeout,
                    groups,
                    now,
                    msg_count,
                )
                log_handle.flush()
                last_log = now

            if args.quick_check and not quick_done and (now - start_time) >= args.quick_wait:
                period = now - last_summary if last_summary > 0 else args.quick_wait
                fps = (summary_frames / period) if period > 0 else 0.0
                err_rate = (summary_errors / period) if period > 0 else 0.0
                lines = _build_summary_lines(
                    device_specs,
                    last_seen,
                    msg_count,
                    args.timeout,
                    fps,
                    err_rate,
                    groups,
                    now,
                )
                print("\n".join(lines))
                quick_done = True
                break
    except KeyboardInterrupt:
        print("Stopping.")
    finally:
        try:
            now = time.time()
            period = now - last_summary if last_summary > 0 else max(now - start_time, 0.5)
            fps = (summary_frames / period) if period > 0 else 0.0
            err_rate = (summary_errors / period) if period > 0 else 0.0
            lines = _build_summary_lines(
                device_specs,
                last_seen,
                msg_count,
                args.timeout,
                fps,
                err_rate,
                groups,
                now,
                title="Final Summary",
            )
            print("\n".join(lines))
        except Exception:
            pass
        try:
            bus.shutdown()
        except Exception:
            pass
        if log_handle is not None:
            try:
                log_handle.close()
            except Exception:
                pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
