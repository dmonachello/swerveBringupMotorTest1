#!/usr/bin/env python3
"""
NAME
    can_nt_bridge.py - FRC CAN bringup diagnostics runner.

SYNOPSIS
    python -m tools.can_nt.can_nt_bridge [options]

DESCRIPTION
    Runs the PC-side CAN sniffer, optional NetworkTables publishing, optional
    PCAP logging, and console monitoring. Designed for Windows + CANable slcan.

SIDE EFFECTS
    Opens the CAN interface, optional NetworkTables client, optional PCAP file
    or pipe, optional NetConsole sockets, and emits console output.

ERRORS
    Exits nonzero when CAN bus open or incompatible options fail.
"""
from __future__ import annotations

import queue
import threading
import time
from typing import Iterable, Optional, Tuple, List, Dict, Any

from .can_analyzer import CanLiveAnalyzer
from .can_cli import build_parser
from .can_console_monitor import ConsoleMonitor
from .can_frc_defs import decode_frc_ext_id_full, classify_frame, uses_status_presence
from ..can_inventory.can_inventory import dump_api_inventory, print_inventory_diff
from .can_nt_client import publish_updates, setup_nt
from .can_nt_publish import decode_frc_ext_id
from .can_pcap import build_pcap_comment, setup_pcap, handle_marker_keys
from .can_ports import list_ports, maybe_auto_channel
from .can_profiles import get_profile
from .can_profiles_dump import dump_seen_ids, dump_profile, dump_can_config
from .can_reporting import (
    build_device_label_map,
    build_summary_extra,
    format_frame_line,
    print_or_dump_nt_keys,
    print_summary,
)
from .can_state import SnifferState
from .can_tx import start_tx_if_requested


def _maybe_handle_dumps(
    args,
    now: float,
    start: float,
    analyzer: CanLiveAnalyzer,
    state: SnifferState,
    devices: List[Dict[str, Any]],
) -> bool:
    """
    NAME
        _maybe_handle_dumps - Emit one-shot dump outputs when timers elapse.

    SYNOPSIS
        handled = _maybe_handle_dumps(args, now, start, analyzer, state, devices)

    DESCRIPTION
        Checks configured dump flags and their delays, writes outputs once, and
        signals the caller to exit when a dump completes.

    PARAMETERS
        args: Parsed CLI arguments with dump settings.
        now: Current wall-clock time (seconds).
        start: Process start time (seconds).
        analyzer: Live analyzer for seen IDs.
        state: SnifferState carrying observed pairs and timestamps.
        devices: Profile device list for context.

    RETURNS
        True when a dump was produced and the caller should exit.

    SIDE EFFECTS
        Writes JSON or profile outputs to disk and prints status lines.
    """
    if args.dump_can_expected_ids and (now - start) >= args.dump_after:
        seen_sorted = sorted(analyzer.seen_ids())
        dump_seen_ids(
            args.dump_can_expected_ids,
            args.profile,
            args.interface,
            args.channel,
            args.bitrate,
            seen_sorted,
        )
        print(f"Dumped observed arbitration IDs to {args.dump_can_expected_ids}")
        return True
    if args.dump_profile and (now - start) >= args.dump_profile_after:
        seen_keys = sorted(state.last_seen.keys())
        profile_name = args.dump_profile_name
        if not profile_name:
            profile_name = time.strftime("sniffer_%Y%m%d_%H%M%S", time.localtime(now))
        dump_profile(
            args.dump_profile,
            profile_name,
            seen_keys,
            args.dump_profile_include_unknown,
        )
        print(f"Dumped profile to {args.dump_profile}")
        return True
    if args.dump_api_inventory and (now - start) >= args.dump_api_inventory_after:
        dump_api_inventory(
            args.dump_api_inventory,
            args.profile,
            args.interface,
            args.channel,
            args.bitrate,
            state.pair_stats,
            source="can_nt_bridge",
            robot_ip=args.rio,
        )
        print(f"Dumped API inventory to {args.dump_api_inventory}")
        return True
    return False


def main(argv: Optional[Iterable[str]] = None) -> int:
    """
    NAME
        main - Entry point for the CAN bringup diagnostics tool.

    SYNOPSIS
        exit_code = main(argv=None)

    DESCRIPTION
        Parses CLI arguments, opens the CAN bus, configures optional outputs,
        and runs the sniffer loop with NT publishing and summary printing.

    PARAMETERS
        argv: Optional argument list; defaults to sys.argv when None.

    RETURNS
        Process exit code (0 on success, nonzero on error).

    SIDE EFFECTS
        Opens hardware interfaces, sockets, files, and writes NT/PCAP outputs.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_ports:
        ports = list_ports()
        if not ports:
            print("No serial ports found.")
        else:
            print("Available serial ports:")
            for dev, desc in ports:
                print(f"  {dev} ({desc})")
        return 0

    devices, expected_ids = get_profile(args.profile)
    device_labels = build_device_label_map(devices)

    channel, _, channel_status = maybe_auto_channel(args)
    if channel_status != 0 or not channel:
        return channel_status

    if args.list_keys or args.dump_nt:
        print_or_dump_nt_keys(devices, args.list_keys, args.dump_nt)
        return 0
    if args.dump_can_config:
        dump_can_config(args.dump_can_config, args, devices)
        print(f"Wrote config to {args.dump_can_config}")
        return 0
    if args.diff_inventory:
        print_inventory_diff(args.diff_inventory[0], args.diff_inventory[1], args.diff_top)
        return 0
    if args.tx_seq and not args.tx_allow:
        print("ERROR: --tx-seq requires --tx-allow for safety.")
        return 2

    # Delayed imports so --help still works without packages installed
    import can  # type: ignore

    try:
        bus = can.Bus(interface=args.interface, channel=channel, bitrate=args.bitrate)
    except Exception as exc:
        print(
            "ERROR: Failed to open CAN bus "
            f"(interface={args.interface}, channel={channel}, bitrate={args.bitrate}): {exc}"
        )
        return 2

    if args.pcap and args.pcap_pipe:
        print("ERROR: Use --pcap or --pcap-pipe, not both.")
        return 2

    pcap_comment = build_pcap_comment(args, channel)
    pcap = setup_pcap(args, pcap_comment)
    if args.enable_markers:
        if args.pcap and not args.pcap.lower().endswith(".pcapng"):
            print("ERROR: Marker injection requires a .pcapng output file.")
            return 2

    nt, table = setup_nt(args)

    console_monitor = None
    if args.console_monitor:
        transport = args.console_transport.lower()
        host = args.console_host or args.rio
        port = args.console_port
        if transport == "udp" and port == 1740:
            port = 6666
        console_monitor = ConsoleMonitor(
            rules_path=args.console_rules,
            inactivity_timeout=args.console_timeout,
            publish_rate_hz=args.console_rate,
            debug_log_path=args.console_debug_log,
            debug_log_max_mb=args.console_log_max_mb,
            debug_log_max_files=args.console_log_max_files,
            transport=transport,
            host=host,
            port=port,
        )
        if args.console_reset_on_start:
            console_monitor.request_reset()
        if transport == "udp":
            print(f"ConsoleMonitor: listening on UDP {port} for NetConsole.")
        else:
            print(f"ConsoleMonitor: connecting to TCP {host}:{port} for NetConsole.")
        if args.console_reset_on_start and table is not None:
            console_monitor.publish(table, time.time())

    analyzer = CanLiveAnalyzer(expected_ids=expected_ids)
    state = SnifferState()
    stop_requested = False
    state.last_marker_ts = 0.0
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
    startup_summary_done = False
    tx_thread = start_tx_if_requested(args, bus, can, tx_stop)

    try:
        while True:
            now = time.time()

            stop_requested = handle_marker_keys(
                args=args,
                key_queue=key_queue,
                marker_keys=marker_keys,
                pcap=pcap,
                tx_stop=tx_stop,
                state=state,
                print_banner=_print_marker_banner,
            ) or stop_requested
            if stop_requested:
                break

            if _maybe_handle_dumps(args, now, start, analyzer, state, devices):
                return 0

            if (
                not startup_summary_done
                and args.startup_summary_after > 0.0
                and (now - start) >= args.startup_summary_after
            ):
                startup_summary_done = True
                print("Startup OK.")
                summary = analyzer.summary(now, args.stale_s, top_n=args.top_n)
                extra = build_summary_extra(summary, devices, analyzer, state, bus, args.bitrate)
                print_summary(summary, now, device_labels, extra)

            try:
                msg = bus.recv(timeout=0.05)
                state.open_ok = True
            except Exception:
                state.read_errors += 1
                state.open_ok = False
                msg = None

            if msg is not None:
                if args.pcap or args.pcap_pipe:
                    if not pcap.log(msg, timestamp_s=now):
                        state.pcap_errors += 1

                arb_id = int(msg.arbitration_id)
                data = bytes(getattr(msg, "data", b"") or b"")

                analyzer.ingest(now, arb_id, data)

                mfg, dtype, did = decode_frc_ext_id(arb_id)
                _, _, api_class, api_index, _ = decode_frc_ext_id_full(arb_id)
                key = (mfg, dtype, did)
                state.last_seen[key] = now
                state.msg_count[key] = state.msg_count.get(key, 0) + 1

                is_status, is_control = classify_frame(
                    arb_id=arb_id,
                    manufacturer=mfg,
                    device_type=dtype,
                    api_class=api_class,
                    api_index=api_index,
                )
                if is_status:
                    state.status_last_seen[key] = now
                if is_control:
                    state.control_last_seen[key] = now

                print_id_match = (args.print_can_id == -1 or arb_id == args.print_can_id)
                print_dev_match = (args.print_device_id == -1 or did == args.print_device_id)
                print_mfg_match = (args.print_mfg == -1 or mfg == args.print_mfg)
                print_type_match = (args.print_type == -1 or dtype == args.print_type)

                label = device_labels.get((mfg, dtype, did), "")
                if (
                    args.print_any
                    and print_id_match
                    and print_dev_match
                    and print_mfg_match
                    and print_type_match
                ):
                    print(
                        format_frame_line(
                            "frame",
                            arb_id,
                            mfg,
                            dtype,
                            did,
                            api_class,
                            api_index,
                            data,
                            label,
                        )
                    )
                if (
                    args.print_status
                    and is_status
                    and print_id_match
                    and print_dev_match
                    and print_mfg_match
                    and print_type_match
                ):
                    print(
                        format_frame_line(
                            "status",
                            arb_id,
                            mfg,
                            dtype,
                            did,
                            api_class,
                            api_index,
                            data,
                            label,
                        )
                    )
                if (
                    args.print_control
                    and is_control
                    and print_id_match
                    and print_dev_match
                    and print_mfg_match
                    and print_type_match
                ):
                    print(
                        format_frame_line(
                            "control",
                            arb_id,
                            mfg,
                            dtype,
                            did,
                            api_class,
                            api_index,
                            data,
                            label,
                        )
                    )

                pair_key = (mfg, dtype, did, api_class, api_index)
                stats = state.pair_stats.get(pair_key)
                if stats is None:
                    stats = {"first": now, "last": now, "count": 0.0, "arb_id": arb_id}
                    state.pair_stats[pair_key] = stats
                stats["last"] = now
                stats["count"] += 1.0

                state.total_frames += 1
                state.period_frames += 1
                state.last_frame_time = now

            if console_monitor is not None:
                console_monitor.poll(now)

            last_publish, last_summary = publish_updates(
                args=args,
                now=now,
                last_publish=last_publish,
                last_summary=last_summary,
                analyzer=analyzer,
                state=state,
                devices=devices,
                labels=device_labels,
                table=table,
                bus=bus,
                console_monitor=console_monitor,
                uses_status_presence=uses_status_presence,
            )

    except KeyboardInterrupt:
        print("Stopping (Ctrl+C)...")
    finally:
        now = time.time()
        if console_monitor is not None:
            console_monitor.stop()
        try:
            summary = analyzer.summary(now, stale_s=args.stale_s, top_n=args.top_n)
            print("=== Final Summary ===")
            extra = build_summary_extra(summary, devices, analyzer, state, bus, args.bitrate)
            print_summary(summary, now, device_labels, extra)
        except Exception as exc:
            print(f"WARNING: Failed to print summary on exit: {exc}")

        key_stop.set()
        tx_stop.set()
        try:
            pcap.stop()
            print("PCAP logger stopped.")
        except Exception as exc:
            print(f"WARNING: Failed to stop PCAP logger: {exc}")
        try:
            bus.shutdown()
            print("CAN bus closed.")
        except Exception as exc:
            print(f"WARNING: Failed to close CAN bus: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
