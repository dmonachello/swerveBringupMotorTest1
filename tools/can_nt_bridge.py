#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import queue
import threading
import time
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple, List, Any

from can_analyzer import CanLiveAnalyzer
from can_logging import PcapLogger
from can_nt_publish import decode_frc_ext_id, publish_devices
from can_profiles import get_default_profile, get_profile


def _parse_tx_sequence(path: str) -> List[Tuple[float, int, bytes]]:
    entries: List[Tuple[float, int, bytes]] = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
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


def _tx_worker(
    bus,
    can_module,
    sequence: List[Tuple[float, int, bytes]],
    stop_event: threading.Event,
    scale: float,
    loop: bool,
    verbose: bool,
) -> None:
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


def _dump_seen_ids(
    path: str,
    profile: str,
    interface: str,
    channel: str,
    bitrate: int,
    seen_ids: list[int],
) -> None:
    now = time.time()
    payload = {
        "created": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
        "profile": profile,
        "interface": interface,
        "channel": channel,
        "bitrate": bitrate,
        "seen_ids_int": seen_ids,
        "seen_ids_hex": [hex(x) for x in seen_ids],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _build_profile_from_seen(
    seen_keys: Iterable[Tuple[int, int, int]],
    profile_name: str,
    include_unknown: bool,
) -> Dict[str, object]:
    neos: List[Dict[str, int]] = []
    flexes: List[Dict[str, int]] = []
    krakens: List[Dict[str, int]] = []
    falcons: List[Dict[str, int]] = []
    cancoders: List[Dict[str, int]] = []
    unknown: List[Dict[str, int]] = []
    pdh_id: Optional[int] = None
    pdp_id: Optional[int] = None
    pigeon_id: Optional[int] = None
    roborio_id: Optional[int] = None

    for mfg, dtype, did in sorted(seen_keys):
        if mfg == 5 and dtype == 2:
            neos.append({"id": did})
        elif mfg == 4 and dtype == 2:
            krakens.append({"id": did})
        elif mfg == 4 and dtype == 7:
            cancoders.append({"id": did})
        elif mfg == 5 and dtype == 8:
            if pdh_id is None:
                pdh_id = did
            elif include_unknown:
                unknown.append({"manufacturer": mfg, "device_type": dtype, "device_id": did})
        elif mfg == 4 and dtype == 8:
            if pdp_id is None:
                pdp_id = did
            elif include_unknown:
                unknown.append({"manufacturer": mfg, "device_type": dtype, "device_id": did})
        elif mfg == 4 and dtype == 4:
            if pigeon_id is None:
                pigeon_id = did
            elif include_unknown:
                unknown.append({"manufacturer": mfg, "device_type": dtype, "device_id": did})
        elif mfg == 1 and dtype == 1:
            if roborio_id is None:
                roborio_id = did
            elif include_unknown:
                unknown.append({"manufacturer": mfg, "device_type": dtype, "device_id": did})
        elif include_unknown:
            unknown.append({"manufacturer": mfg, "device_type": dtype, "device_id": did})

    profile: Dict[str, object] = {
        "neos": neos,
        "flexes": flexes,
        "krakens": krakens,
        "falcons": falcons,
        "cancoders": cancoders,
        "notes": {
            "generated_by": "can_nt_bridge.py",
            "profile_name": profile_name,
            "assumptions": [
                "REV mfg=5 type=2 mapped to 'neos' (cannot distinguish NEO vs FLEX).",
                "CTRE mfg=4 type=2 mapped to 'krakens' (cannot distinguish Kraken vs Falcon).",
            ],
        },
    }
    if pdh_id is not None:
        profile["pdh"] = {"id": pdh_id}
    if pdp_id is not None:
        profile["pdp"] = {"id": pdp_id}
    if pigeon_id is not None:
        profile["pigeon"] = {"id": pigeon_id}
    if roborio_id is not None:
        profile["roborio"] = {"id": roborio_id}
    if include_unknown and unknown:
        profile["unknown"] = unknown

    return profile


def _dump_profile(
    path: str,
    profile_name: str,
    seen_keys: Iterable[Tuple[int, int, int]],
    include_unknown: bool,
) -> None:
    payload = {
        "default_profile": profile_name,
        "profiles": {
            profile_name: _build_profile_from_seen(seen_keys, profile_name, include_unknown),
        },
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _decode_frc_ext_id_full(arb_id: int) -> Tuple[int, int, int, int, int]:
    # FRC extended CAN layout (common subset):
    # manufacturer: bits 16..23
    # device_type:  bits 24..28
    # api_class:    bits 10..15
    # api_index:    bits 6..9
    # device_id:    bits 0..5
    manufacturer = (arb_id >> 16) & 0xFF
    device_type = (arb_id >> 24) & 0x1F
    api_class = (arb_id >> 10) & 0x3F
    api_index = (arb_id >> 6) & 0x0F
    device_id = arb_id & 0x3F
    return manufacturer, device_type, api_class, api_index, device_id


def _classify_frame(
    arb_id: int,
    manufacturer: int,
    device_type: int,
    api_class: int,
    api_index: int,
) -> Tuple[bool, bool]:
    # Heuristics aligned with the Wireshark dissector (unverified).
    # REV: api_class 6 appears to be periodic status for motor controllers.
    is_status = (manufacturer == 5 and device_type == 2 and api_class == 6)
    # REV: api_class 46 observed as control frames for motor controllers.
    is_control = (manufacturer == 5 and device_type == 2 and api_class == 46)

    # CTRE: Phoenix frames often use J1939-style PF/PS fields.
    pf = (arb_id >> 16) & 0xFF
    ps = (arb_id >> 8) & 0xFF
    is_control = is_control or (manufacturer == 4 and pf == 0xEF)
    if manufacturer == 4 and pf == 0xFF and ps <= 0x07:
        is_status = True

    return is_status, is_control


def _uses_status_presence(manufacturer: int, device_type: int) -> bool:
    if manufacturer == 5 and device_type == 2:
        return True
    if manufacturer == 4:
        return True
    return False


def _dump_api_inventory(
    path: str,
    profile: str,
    interface: str,
    channel: str,
    bitrate: int,
    pairs: Dict[Tuple[int, int, int, int, int], Dict[str, float]],
) -> None:
    devices: Dict[Tuple[int, int, int], List[Dict[str, Any]]] = {}
    for (mfg, dtype, did, api_class, api_index), stats in pairs.items():
        key = (mfg, dtype, did)
        duration = max(0.0, stats["last"] - stats["first"])
        fps = (stats["count"] / duration) if duration > 0 else 0.0
        entry = {
            "apiClass": api_class,
            "apiIndex": api_index,
            "count": int(stats["count"]),
            "firstSeen": stats["first"],
            "lastSeen": stats["last"],
            "fps": fps,
        }
        devices.setdefault(key, []).append(entry)

    payload = {
        "created": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())),
        "profile": profile,
        "interface": interface,
        "channel": channel,
        "bitrate": bitrate,
        "devices": [
            {
                "mfg": mfg,
                "type": dtype,
                "id": did,
                "pairs": sorted(pairs, key=lambda p: (p["apiClass"], p["apiIndex"])),
            }
            for (mfg, dtype, did), pairs in sorted(devices.items())
        ],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _load_inventory(path: str) -> Dict[Tuple[int, int, int, int, int], float]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    result: Dict[Tuple[int, int, int, int, int], float] = {}
    for dev in payload.get("devices", []):
        try:
            mfg = int(dev.get("mfg"))
            dtype = int(dev.get("type"))
            did = int(dev.get("id"))
        except Exception:
            continue
        for pair in dev.get("pairs", []):
            try:
                api_class = int(pair.get("apiClass"))
                api_index = int(pair.get("apiIndex"))
                fps = float(pair.get("fps", 0.0))
            except Exception:
                continue
            result[(mfg, dtype, did, api_class, api_index)] = fps
    return result


def _print_inventory_diff(path_a: str, path_b: str, top_n: int) -> None:
    a = _load_inventory(path_a)
    b = _load_inventory(path_b)
    keys_a = set(a.keys())
    keys_b = set(b.keys())

    new_pairs = sorted(keys_b - keys_a)
    missing_pairs = sorted(keys_a - keys_b)
    deltas = []
    for key in sorted(keys_a & keys_b):
        fps_a = a.get(key, 0.0)
        fps_b = b.get(key, 0.0)
        delta = fps_b - fps_a
        deltas.append((abs(delta), delta, key, fps_a, fps_b))
    deltas.sort(reverse=True)

    print("=== Inventory Diff ===")
    print(f"New pairs: {len(new_pairs)}")
    for key in new_pairs[:top_n]:
        mfg, dtype, did, api_class, api_index = key
        print(f"  + mfg={mfg} type={dtype} id={did} apiClass={api_class} apiIndex={api_index}")
    if len(new_pairs) > top_n:
        print(f"  ... {len(new_pairs) - top_n} more")

    print(f"Missing pairs: {len(missing_pairs)}")
    for key in missing_pairs[:top_n]:
        mfg, dtype, did, api_class, api_index = key
        print(f"  - mfg={mfg} type={dtype} id={did} apiClass={api_class} apiIndex={api_index}")
    if len(missing_pairs) > top_n:
        print(f"  ... {len(missing_pairs) - top_n} more")

    print(f"Biggest rate changes (top {top_n}):")
    for _, delta, key, fps_a, fps_b in deltas[:top_n]:
        mfg, dtype, did, api_class, api_index = key
        print(
            "  "
            f"mfg={mfg} type={dtype} id={did} apiClass={api_class} apiIndex={api_index} "
            f"fps={fps_a:.2f} -> {fps_b:.2f} (delta {delta:+.2f})"
        )


def _list_ports() -> List[Tuple[str, str]]:
    try:
        import serial.tools.list_ports  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "pyserial is required for listing serial ports. "
            "Install it with: py -m pip install pyserial"
        ) from exc
    ports: List[Tuple[str, str]] = []
    for port in serial.tools.list_ports.comports():
        ports.append((port.device, port.description or ""))
    return ports


def _auto_channel(match_text: str, prompt: bool) -> Tuple[str, str]:
    try:
        import serial.tools.list_ports  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "pyserial is required for auto-detecting the CANable port. "
            "Install it with: py -m pip install pyserial"
        ) from exc

    matches: List[Tuple[str, str]] = []
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


def _print_or_dump_nt_keys(devices, print_keys: bool, dump_path: str) -> None:
    keys = []
    for spec in devices:
        base = f"bringup/diag/dev/{spec['manufacturer']}/{spec['device_type']}/{spec['device_id']}"
        keys.extend([
            f"{base}/label",
            f"{base}/status",
            f"{base}/ageSec",
            f"{base}/msgCount",
            f"{base}/lastSeen",
            f"{base}/presenceSource",
            f"{base}/presenceConfidence",
            f"{base}/trafficAgeSec",
            f"{base}/statusAgeSec",
            f"{base}/manufacturer",
            f"{base}/deviceType",
            f"{base}/deviceId",
        ])
    keys.append("bringup/diag/can/summary/json")
    keys.extend([
        "bringup/diag/can/pc/heartbeat",
        "bringup/diag/can/pc/openOk",
        "bringup/diag/can/pc/framesPerSec",
        "bringup/diag/can/pc/framesTotal",
        "bringup/diag/can/pc/readErrors",
        "bringup/diag/can/pc/lastFrameAgeSec",
    ])
    payload = {
        "keys": keys,
        "count": len(keys),
    }
    if print_keys:
        print("NetworkTables keys published by can_nt_bridge.py:")
        for key in keys:
            print(f"  {key}")
    if dump_path:
        with open(dump_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"Wrote NT key inventory to {dump_path}")


def _print_status_transitions(
    devices,
    last_seen: Dict[Tuple[int, int, int], float],
    status_last_seen: Dict[Tuple[int, int, int], float],
    control_last_seen: Dict[Tuple[int, int, int], float],
    now: float,
    timeout_s: float,
    last_status: Dict[Tuple[int, int, int], str],
) -> None:
    for spec in devices:
        key = (spec["manufacturer"], spec["device_type"], spec["device_id"])
        traffic_ts = last_seen.get(key)
        status_ts = status_last_seen.get(key)
        control_ts = control_last_seen.get(key)
        ts = status_ts if _uses_status_presence(key[0], key[1]) else traffic_ts
        if ts is None:
            status = "CONTROL_ONLY" if control_ts is not None else "MISSING"
        else:
            status = "OK" if (now - ts) < timeout_s else "MISSING"
        prev = last_status.get(key)
        if prev is None:
            last_status[key] = status
            continue
        if prev != status:
            label = spec.get("label", "")
            if status == "OK":
                print(f"[seen] {label} mfg={key[0]} type={key[1]} id={key[2]}")
            else:
                print(f"[missing] {label} mfg={key[0]} type={key[1]} id={key[2]} ({status})")
        last_status[key] = status


def _print_summary(summary, now: float) -> None:
    top = summary.get("topTalkers", [])
    total = summary.get("totalFramesPerSec")
    missing = summary.get("missing", [])
    ts = time.strftime("%H:%M:%S", time.localtime(now))
    print(f"[summary {ts}] fps={total} missing={len(missing)} top={len(top)}")
    for row in top[:5]:
        try:
            print(
                "  "
                f"mfg={row.get('mfg')} type={row.get('type')} id={row.get('id')} "
                f"fps={row.get('fps')}"
            )
        except Exception:
            continue


def _merge_unknown_devices(devices, last_seen: Dict[Tuple[int, int, int], float], enabled: bool):
    if not enabled:
        return devices
    known_keys = {(d["manufacturer"], d["device_type"], d["device_id"]) for d in devices}
    merged = list(devices)
    for key in last_seen.keys():
        if key in known_keys:
            continue
        mfg, dtype, did = key
        merged.append(
            {
                "label": "UNKNOWN",
                "manufacturer": mfg,
                "device_type": dtype,
                "device_id": did,
                "group": "unknown",
            }
        )
    return merged

def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="FRC CAN bringup diagnostics")

    parser.add_argument("--profile", default=get_default_profile())

    parser.add_argument("--interface", default="slcan")
    parser.add_argument(
        "--channel",
        default="",
        help="CAN channel (for slcan, the COM port like COM3). "
        "If omitted, attempts auto-detect by description.",
    )
    parser.add_argument("--bitrate", type=int, default=1_000_000)
    parser.add_argument(
        "--auto-match",
        default="USB Serial Device",
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

    parser.add_argument("--rio", default="172.22.11.2")
    parser.add_argument(
        "--no-nt",
        action="store_true",
        help="Disable NetworkTables publishing (capture/logging only).",
    )

    parser.add_argument("--timeout", type=float, default=1.0)
    parser.add_argument("--publish-period", type=float, default=0.2)

    parser.add_argument("--publish-can-summary", action="store_true")
    parser.add_argument(
        "--print-summary-period",
        type=float,
        default=0.0,
        help="Print CAN summary to console every N seconds (0 disables).",
    )
    parser.add_argument(
        "--print-publish",
        action="store_true",
        help="Print when a device transitions from missing to seen.",
    )
    parser.add_argument("--stale-s", type=float, default=0.75)
    parser.add_argument("--top-n", type=int, default=15)

    parser.add_argument("--dump-can-expected-ids", default="")
    parser.add_argument("--dump-after", type=float, default=3.0)

    parser.add_argument(
        "--list-keys",
        action="store_true",
        help="Print the NetworkTables keys this tool publishes and exit.",
    )
    parser.add_argument(
        "--dump-nt",
        default="",
        help="Write a JSON description of published NetworkTables keys and exit.",
    )
    parser.add_argument(
        "--publish-unknown",
        action="store_true",
        help="Publish devices seen on the bus that are not in the profile as UNKNOWN.",
    )
    parser.add_argument(
        "--dump-profile",
        default="",
        help=(
            "Write a bringup_profiles.json file generated from observed CAN IDs "
            "and exit."
        ),
    )
    parser.add_argument(
        "--dump-profile-name",
        default="",
        help=(
            "Profile name to use when writing --dump-profile output. "
            "If omitted, a timestamped name is generated."
        ),
    )
    parser.add_argument(
        "--dump-profile-after",
        type=float,
        default=3.0,
        help="Seconds to wait before writing --dump-profile output.",
    )
    parser.add_argument(
        "--dump-profile-include-unknown",
        action="store_true",
        help="Include unknown devices in the generated profile output.",
    )
    parser.add_argument(
        "--dump-api-inventory",
        default="",
        help="Write a JSON inventory of apiClass/apiIndex counts and exit.",
    )
    parser.add_argument(
        "--dump-api-inventory-after",
        type=float,
        default=3.0,
        help="Seconds to wait before writing --dump-api-inventory output.",
    )
    parser.add_argument(
        "--diff-inventory",
        nargs=2,
        metavar=("A.json", "B.json"),
        help="Diff two inventory JSON files and print deltas.",
    )
    parser.add_argument(
        "--diff-top",
        type=int,
        default=10,
        help="Number of rows to show for new/missing/changed pairs.",
    )

    parser.add_argument("--pcap", default="", help="Write all CAN frames to a .pcapng/.pcap file")
    parser.add_argument(
        "--marker-id",
        type=lambda s: int(s, 0),
        default=0x1FFC0D00,
        help="Arbitration ID for synthetic marker frames (29-bit extended).",
    )
    parser.add_argument(
        "--enable-markers",
        dest="enable_markers",
        action="store_true",
        default=True,
        help="Enable keyboard marker injection into pcapng captures.",
    )
    parser.add_argument(
        "--disable-markers",
        dest="enable_markers",
        action="store_false",
        help="Disable keyboard marker injection.",
    )
    parser.add_argument(
        "--capture-note",
        default="",
        help="Optional note to embed in the pcapng section header comment.",
    )
    parser.add_argument(
        "--tx-seq",
        default="",
        help=(
            "Transmit a CAN sequence from a text file. "
            "Supported formats: "
            "TSV (time\\tcan_id\\tlen\\tdata_hex) or "
            "CSV (time,can_id,data_hex)."
        ),
    )
    parser.add_argument(
        "--tx-allow",
        action="store_true",
        help="Allow transmitting CAN frames (required when using --tx-seq).",
    )
    parser.add_argument(
        "--tx-scale",
        type=float,
        default=1.0,
        help="Scale the TX timing (1.0 = realtime).",
    )
    parser.add_argument(
        "--tx-loop",
        action="store_true",
        help="Loop the TX sequence until stopped.",
    )
    parser.add_argument(
        "--tx-verbose",
        action="store_true",
        help="Print TX progress (first few frames and every 100 frames).",
    )
    parser.add_argument(
        "--print-status",
        action="store_true",
        help="Print status frames as they are received.",
    )
    parser.add_argument(
        "--print-control",
        action="store_true",
        help="Print control frames as they are received.",
    )
    parser.add_argument(
        "--print-can-id",
        type=lambda s: int(s, 0),
        default=-1,
        help="Only print frames matching this arbitration ID (hex or dec).",
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

    devices, expected_ids = get_profile(args.profile)

    channel = args.channel
    if not channel:
        channel, channel_desc = _auto_channel(args.auto_match, not args.no_prompt)
        print(f"Auto-detected CAN channel: {channel} ({channel_desc})")

    if args.list_keys or args.dump_nt:
        _print_or_dump_nt_keys(devices, args.list_keys, args.dump_nt)
        return 0
    if args.diff_inventory:
        _print_inventory_diff(args.diff_inventory[0], args.diff_inventory[1], args.diff_top)
        return 0
    if args.tx_seq and not args.tx_allow:
        print("ERROR: --tx-seq requires --tx-allow for safety.")
        return 2

    # Delayed imports so --help still works without packages installed
    from ntcore import NetworkTableInstance
    import can  # type: ignore

    bus = can.Bus(interface=args.interface, channel=channel, bitrate=args.bitrate)

    pcap_comment = ""
    if args.pcap and args.pcap.lower().endswith(".pcapng"):
        start_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
        parts = [
            f"start={start_str}",
            f"interface={args.interface}",
            f"channel={channel}",
            f"bitrate={args.bitrate}",
        ]
        if args.capture_note:
            parts.append(f"note={args.capture_note}")
        pcap_comment = " | ".join(parts)
    pcap = PcapLogger(args.pcap, pcap_comment)
    if args.pcap and pcap.start():
        print(f"PCAP logging enabled: {args.pcap}")
    if args.enable_markers and args.pcap and not args.pcap.lower().endswith(".pcapng"):
        print("ERROR: Marker injection requires a .pcapng output file.")
        return 2

    nt = None
    table = None
    if not args.no_nt:
        nt = NetworkTableInstance.getDefault()
        nt.startClient4("can-nt-bridge")
        nt.setServer(args.rio)
        table = nt.getTable("bringup").getSubTable("diag")

    analyzer = CanLiveAnalyzer(expected_ids=expected_ids)
    last_seen: Dict[Tuple[int, int, int], float] = {}
    status_last_seen: Dict[Tuple[int, int, int], float] = {}
    control_last_seen: Dict[Tuple[int, int, int], float] = {}
    msg_count: Dict[Tuple[int, int, int], int] = {}
    last_status: Dict[Tuple[int, int, int], str] = {}
    pair_stats: Dict[Tuple[int, int, int, int, int], Dict[str, float]] = {}
    total_frames = 0
    period_frames = 0
    read_errors = 0
    last_frame_time = 0.0
    heartbeat = 0
    open_ok = True
    marker_counter = 0
    stop_requested = False
    last_marker_ts = 0.0
    marker_keys = {"0", "1", "2", "3", "4", "m", "q", "h"}
    key_queue: queue.Queue[Tuple[str, float]] = queue.Queue()
    key_thread = None
    key_stop = threading.Event()
    tx_stop = threading.Event()
    tx_thread = None

    def _print_marker_banner() -> None:
        print("Marker keys: [1]=0.25 [2]=0.50 [3]=0.75 [4]=1.00 [0]=stop [m]=mark [q]=quit [h]=help")
        print(f"Marker ID: 0x{args.marker_id:08X} (extended)")

    def _keyboard_worker() -> None:
        try:
            import msvcrt  # type: ignore
        except Exception:
            print("WARNING: marker input requires msvcrt (Windows). Markers disabled.")
            return
        while not key_stop.is_set():
            if msvcrt.kbhit():
                raw = msvcrt.getch()
                if raw in (b"\x00", b"\xe0"):
                    _ = msvcrt.getch()
                    continue
                try:
                    key = raw.decode("utf-8", errors="ignore")
                except Exception:
                    key = ""
                if key:
                    key_queue.put((key, time.time()))
            else:
                time.sleep(0.01)

    if (args.enable_markers and args.pcap) or args.tx_seq:
        key_thread = threading.Thread(target=_keyboard_worker, daemon=True)
        key_thread.start()
        if args.enable_markers and args.pcap:
            _print_marker_banner()
        if args.tx_seq:
            print("TX control: press [space] to stop transmission.")

    start = time.time()
    last_publish = 0.0
    last_summary = 0.0
    if args.tx_seq:
        sequence = _parse_tx_sequence(args.tx_seq)
        tx_thread = threading.Thread(
            target=_tx_worker,
            args=(bus, can, sequence, tx_stop, args.tx_scale, args.tx_loop, args.tx_verbose),
            daemon=True,
        )
        tx_thread.start()

    try:
        while True:
            now = time.time()

            while True:
                try:
                    key, key_ts = key_queue.get_nowait()
                except queue.Empty:
                    break
                if key not in marker_keys:
                    if key == " ":
                        tx_stop.set()
                        print("TX stopped by user.")
                    continue
                if key == "h":
                    _print_marker_banner()
                    continue
                if args.enable_markers and args.pcap:
                    if key_ts <= last_marker_ts:
                        key_ts = last_marker_ts + 0.000001
                    wrote = pcap.write_marker(
                        timestamp_s=key_ts,
                        marker_id=args.marker_id,
                        key_char=key,
                        counter=marker_counter,
                        extra=0,
                    )
                    if wrote:
                        marker_counter = (marker_counter + 1) & 0xFF
                        last_marker_ts = key_ts
                if key == "q":
                    stop_requested = True
                    break
            if stop_requested:
                break

            if args.dump_can_expected_ids and (now - start) >= args.dump_after:
                seen_sorted = sorted(analyzer.seen_ids())
                _dump_seen_ids(
                    args.dump_can_expected_ids,
                    args.profile,
                    args.interface,
                    args.channel,
                    args.bitrate,
                    seen_sorted,
                )
                print(f"Dumped observed arbitration IDs to {args.dump_can_expected_ids}")
                return 0
            if args.dump_profile and (now - start) >= args.dump_profile_after:
                seen_keys = sorted(last_seen.keys())
                profile_name = args.dump_profile_name
                if not profile_name:
                    profile_name = time.strftime("sniffer_%Y%m%d_%H%M%S", time.localtime(now))
                _dump_profile(
                    args.dump_profile,
                    profile_name,
                    seen_keys,
                    args.dump_profile_include_unknown,
                )
                print(f"Dumped profile to {args.dump_profile}")
                return 0
            if args.dump_api_inventory and (now - start) >= args.dump_api_inventory_after:
                _dump_api_inventory(
                    args.dump_api_inventory,
                    args.profile,
                    args.interface,
                    args.channel,
                    args.bitrate,
                    pair_stats,
                )
                print(f"Dumped API inventory to {args.dump_api_inventory}")
                return 0

            try:
                msg = bus.recv(timeout=0.05)
                open_ok = True
            except Exception:
                read_errors += 1
                open_ok = False
                msg = None

            if msg is not None:
                pcap.log(msg, timestamp_s=now)

                arb_id = int(msg.arbitration_id)
                data = bytes(getattr(msg, "data", b"") or b"")

                analyzer.ingest(now, arb_id, data)

                mfg, dtype, did = decode_frc_ext_id(arb_id)
                _, _, api_class, api_index, _ = _decode_frc_ext_id_full(arb_id)
                key = (mfg, dtype, did)
                last_seen[key] = now
                msg_count[key] = msg_count.get(key, 0) + 1

                is_status, is_control = _classify_frame(
                    arb_id=arb_id,
                    manufacturer=mfg,
                    device_type=dtype,
                    api_class=api_class,
                    api_index=api_index,
                )
                if is_status:
                    status_last_seen[key] = now
                if is_control:
                    control_last_seen[key] = now

                if args.print_status and is_status:
                    if args.print_can_id == -1 or arb_id == args.print_can_id:
                        print(f"[status] id=0x{arb_id:X} len={len(data)} data={data.hex()}")
                if args.print_control and is_control:
                    if args.print_can_id == -1 or arb_id == args.print_can_id:
                        print(f"[control] id=0x{arb_id:X} len={len(data)} data={data.hex()}")

                pair_key = (mfg, dtype, did, api_class, api_index)
                stats = pair_stats.get(pair_key)
                if stats is None:
                    stats = {"first": now, "last": now, "count": 0.0}
                    pair_stats[pair_key] = stats
                stats["last"] = now
                stats["count"] += 1.0

                total_frames += 1
                period_frames += 1
                last_frame_time = now

            if (now - last_publish) >= args.publish_period:
                publish_dt = now - last_publish if last_publish > 0 else args.publish_period
                frames_per_sec = (period_frames / publish_dt) if publish_dt > 0 else 0.0
                last_frame_age = (now - last_frame_time) if last_frame_time > 0 else -1.0

                if table is not None:
                    publish_devices(
                        table=table,
                        devices=_merge_unknown_devices(devices, last_seen, args.publish_unknown),
                        last_seen=last_seen,
                        status_last_seen=status_last_seen,
                        control_last_seen=control_last_seen,
                        uses_status_presence=_uses_status_presence,
                        msg_count=msg_count,
                        now=now,
                        timeout_s=args.timeout,
                    )

                if args.print_publish:
                    _print_status_transitions(
                        devices=devices,
                        last_seen=last_seen,
                        status_last_seen=status_last_seen,
                        control_last_seen=control_last_seen,
                        now=now,
                        timeout_s=args.timeout,
                        last_status=last_status,
                    )

                if args.publish_can_summary and table is not None:
                    summary = analyzer.summary(now, stale_s=args.stale_s, top_n=args.top_n)
                    table.getEntry("can/summary/json").setString(
                        json.dumps(summary, separators=(",", ":"))
                    )

                if table is not None:
                    table.getEntry("can/pc/heartbeat").setDouble(float(heartbeat))
                    table.getEntry("can/pc/openOk").setBoolean(open_ok)
                    table.getEntry("can/pc/framesPerSec").setDouble(float(frames_per_sec))
                    table.getEntry("can/pc/framesTotal").setDouble(float(total_frames))
                    table.getEntry("can/pc/readErrors").setDouble(float(read_errors))
                    table.getEntry("can/pc/lastFrameAgeSec").setDouble(float(last_frame_age))

                period_frames = 0
                heartbeat += 1
                if args.print_summary_period and (now - last_summary) >= args.print_summary_period:
                    summary = analyzer.summary(now, stale_s=args.stale_s, top_n=args.top_n)
                    _print_summary(summary, now)
                    last_summary = now

                last_publish = now

    except KeyboardInterrupt:
        pass
    finally:
        key_stop.set()
        tx_stop.set()
        pcap.stop()
        try:
            bus.shutdown()
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
