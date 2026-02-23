#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from typing import Dict, Iterable, Optional, Tuple, List

from can_analyzer import CanLiveAnalyzer
from can_logging import PcapLogger
from can_nt_publish import decode_frc_ext_id, publish_devices
from can_profiles import get_profile


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


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="FRC CAN bringup diagnostics")

    parser.add_argument("--profile", choices=["demo", "robot"], default="robot")

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
    parser.add_argument("--stale-s", type=float, default=0.75)
    parser.add_argument("--top-n", type=int, default=15)

    parser.add_argument("--dump-can-expected-ids", default="")
    parser.add_argument("--dump-after", type=float, default=3.0)

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

    # Delayed imports so --help still works without packages installed
    from ntcore import NetworkTableInstance
    import can  # type: ignore

    channel = args.channel
    if not channel:
        channel, channel_desc = _auto_channel(args.auto_match, not args.no_prompt)
        print(f"Auto-detected CAN channel: {channel} ({channel_desc})")

    bus = can.Bus(interface=args.interface, channel=channel, bitrate=args.bitrate)

    pcap = PcapLogger(args.pcap)
    if args.pcap:
        pcap.start()
        print(f"PCAP logging enabled: {args.pcap}")

    nt = NetworkTableInstance.getDefault()
    nt.startClient4("can-nt-bridge")
    nt.setServer(args.rio)
    table = nt.getTable("bringup").getSubTable("diag")

    analyzer = CanLiveAnalyzer(expected_ids=expected_ids)
    last_seen: Dict[Tuple[int, int, int], float] = {}
    msg_count: Dict[Tuple[int, int, int], int] = {}

    start = time.time()
    last_publish = 0.0

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

            msg = bus.recv(timeout=0.05)
            if msg is not None:
                pcap.log(msg)

                arb_id = int(msg.arbitration_id)
                data = bytes(getattr(msg, "data", b"") or b"")

                analyzer.ingest(now, arb_id, data)

                mfg, dtype, did = decode_frc_ext_id(arb_id)
                key = (mfg, dtype, did)
                last_seen[key] = now
                msg_count[key] = msg_count.get(key, 0) + 1

            if (now - last_publish) >= args.publish_period:
                publish_devices(
                    table=table,
                    devices=devices,
                    last_seen=last_seen,
                    msg_count=msg_count,
                    now=now,
                    timeout_s=args.timeout,
                )

                if args.publish_can_summary:
                    summary = analyzer.summary(now, stale_s=args.stale_s, top_n=args.top_n)
                    table.getEntry("can/summary/json").setString(
                        json.dumps(summary, separators=(",", ":"))
                    )

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
