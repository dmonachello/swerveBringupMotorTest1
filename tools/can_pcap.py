from __future__ import annotations

import queue
import time
from typing import Iterable

from can_logging import PcapLogger
from can_state import SnifferState


def build_pcap_comment(args, channel: str) -> str:
    if (args.pcap and args.pcap.lower().endswith(".pcapng")) or args.pcap_pipe:
        start_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
        parts = [
            f"start={start_str}",
            f"interface={args.interface}",
            f"channel={channel}",
            f"bitrate={args.bitrate}",
        ]
        if args.capture_note:
            parts.append(f"note={args.capture_note}")
        return " | ".join(parts)
    return ""


def setup_pcap(args, pcap_comment: str) -> PcapLogger:
    if args.pcap_pipe:
        print(f"Waiting for Wireshark to connect to pipe: {args.pcap_pipe}")
    pcap = PcapLogger(args.pcap, pcap_comment, pipe_name=args.pcap_pipe)
    if args.pcap or args.pcap_pipe:
        try:
            if pcap.start():
                if args.pcap:
                    print(f"PCAP logging enabled: {args.pcap}")
                else:
                    print(f"PCAP live pipe enabled: {pcap.pipe_name}")
        except Exception as exc:
            print(f"ERROR: Failed to start PCAP logging: {exc}")
            pcap = PcapLogger(None, "")
    return pcap


def handle_marker_keys(
    args,
    key_queue: "queue.Queue[tuple[str, float]]",
    marker_keys: set[str],
    pcap: PcapLogger,
    tx_stop,
    state: SnifferState,
    print_banner,
) -> bool:
    stop_requested = False
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
            print_banner()
            continue
        if args.enable_markers and args.pcap:
            if key_ts <= state.last_marker_ts:
                key_ts = state.last_marker_ts + 0.000001
            try:
                wrote = pcap.write_marker(
                    timestamp_s=key_ts,
                    marker_id=args.marker_id,
                    key_char=key,
                    counter=state.marker_counter,
                    extra=0,
                )
            except Exception as exc:
                print(f"ERROR: Failed to write PCAP marker: {exc}")
                wrote = False
            if wrote:
                state.marker_counter = (state.marker_counter + 1) & 0xFF
                state.last_marker_ts = key_ts
        if key == "q":
            stop_requested = True
            break
    return stop_requested
