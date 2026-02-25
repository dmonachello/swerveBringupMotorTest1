#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple, List, Any

from can_analyzer import CanLiveAnalyzer
from can_logging import PcapLogger
from can_nt_publish import decode_frc_ext_id, publish_devices
from can_profiles import get_default_profile, get_profile


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
    now: float,
    timeout_s: float,
    last_status: Dict[Tuple[int, int, int], str],
) -> None:
    for spec in devices:
        key = (spec["manufacturer"], spec["device_type"], spec["device_id"])
        ts = last_seen.get(key)
        if ts is None:
            status = "MISSING"
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
                print(f"[missing] {label} mfg={key[0]} type={key[1]} id={key[2]}")
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

    # Delayed imports so --help still works without packages installed
    from ntcore import NetworkTableInstance
    import can  # type: ignore

    bus = can.Bus(interface=args.interface, channel=channel, bitrate=args.bitrate)

    pcap = PcapLogger(args.pcap)
    if args.pcap and pcap.start():
        print(f"PCAP logging enabled: {args.pcap}")

    nt = NetworkTableInstance.getDefault()
    nt.startClient4("can-nt-bridge")
    nt.setServer(args.rio)
    table = nt.getTable("bringup").getSubTable("diag")

    analyzer = CanLiveAnalyzer(expected_ids=expected_ids)
    last_seen: Dict[Tuple[int, int, int], float] = {}
    msg_count: Dict[Tuple[int, int, int], int] = {}
    last_status: Dict[Tuple[int, int, int], str] = {}
    pair_stats: Dict[Tuple[int, int, int, int, int], Dict[str, float]] = {}
    total_frames = 0
    period_frames = 0
    read_errors = 0
    last_frame_time = 0.0
    heartbeat = 0
    open_ok = True

    start = time.time()
    last_publish = 0.0
    last_summary = 0.0

    try:
        while True:
            now = time.time()

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
                pcap.log(msg)

                arb_id = int(msg.arbitration_id)
                data = bytes(getattr(msg, "data", b"") or b"")

                analyzer.ingest(now, arb_id, data)

                mfg, dtype, did = decode_frc_ext_id(arb_id)
                _, _, api_class, api_index, _ = _decode_frc_ext_id_full(arb_id)
                key = (mfg, dtype, did)
                last_seen[key] = now
                msg_count[key] = msg_count.get(key, 0) + 1

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

                publish_devices(
                    table=table,
                    devices=_merge_unknown_devices(devices, last_seen, args.publish_unknown),
                    last_seen=last_seen,
                    msg_count=msg_count,
                    now=now,
                    timeout_s=args.timeout,
                )

                if args.print_publish:
                    _print_status_transitions(
                        devices=devices,
                        last_seen=last_seen,
                        now=now,
                        timeout_s=args.timeout,
                        last_status=last_status,
                    )

                if args.publish_can_summary:
                    summary = analyzer.summary(now, stale_s=args.stale_s, top_n=args.top_n)
                    table.getEntry("can/summary/json").setString(
                        json.dumps(summary, separators=(",", ":"))
                    )

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
        pcap.stop()
        try:
            bus.shutdown()
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
