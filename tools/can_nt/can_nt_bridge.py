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

import json
import signal
import queue
import threading
import time
from typing import Iterable, Optional, Tuple, List, Dict, Any
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))

try:
    from tools.can_nt.can_analyzer import CanLiveAnalyzer
    from tools.can_nt.can_cli import build_parser
    from tools.can_nt.can_console_monitor import ConsoleMonitor
    from tools.can_nt.can_frc_defs import decode_frc_ext_id_full, classify_frame
    from tools.can_inventory.can_inventory import dump_api_inventory, print_inventory_diff
    from tools.can_nt.can_nt_client import publish_updates, setup_nt
    from tools.can_nt.can_nt_publish import decode_frc_ext_id
    from tools.can_nt.can_pcap import build_pcap_comment, setup_pcap, handle_marker_keys
    from tools.can_nt.can_ports import list_ports, maybe_auto_channel
    from tools.can_nt.can_profiles import (
        get_profile,
        get_profiles_load_error,
        get_profiles_data_version,
        get_profiles_data_hash,
        reload_profiles,
    )
    from tools.can_nt.can_profiles_dump import dump_seen_ids, dump_profile, dump_can_config
    from tools.can_nt.can_reporting import (
        build_summary_extra,
        format_frame_line,
        print_or_dump_nt_keys,
        print_summary,
    )
    from tools.can_nt.can_state import SnifferState
    from tools.can_nt.can_tx import start_tx_if_requested
    from tools.common.time_utils import timestamp_compact
    from tools.common.app_versions import (
        APP_CAN_BRIDGE_NAME,
        VERSIONS,
        VERSION_HEADER,
        format_version_line,
    )
    from tools.common.build_info import build_lines
    from tools.can_nt.bridge_cli import BridgeCli
    from tools.can_nt.bridge_session import BridgeSession
except ModuleNotFoundError:
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)
    from tools.can_nt.can_analyzer import CanLiveAnalyzer
    from tools.can_nt.can_cli import build_parser
    from tools.can_nt.can_console_monitor import ConsoleMonitor
    from tools.can_nt.can_frc_defs import decode_frc_ext_id_full, classify_frame
    from tools.can_inventory.can_inventory import dump_api_inventory, print_inventory_diff
    from tools.can_nt.can_nt_client import publish_updates, setup_nt
    from tools.can_nt.can_nt_publish import decode_frc_ext_id
    from tools.can_nt.can_pcap import build_pcap_comment, setup_pcap, handle_marker_keys
    from tools.can_nt.can_ports import list_ports, maybe_auto_channel
    from tools.can_nt.can_profiles import (
        get_profile,
        get_profiles_load_error,
        get_profiles_data_version,
        get_profiles_data_hash,
        reload_profiles,
    )
    from tools.can_nt.can_profiles_dump import dump_seen_ids, dump_profile, dump_can_config
    from tools.can_nt.can_reporting import (
        build_summary_extra,
        format_frame_line,
        print_or_dump_nt_keys,
        print_summary,
    )
    from tools.can_nt.can_state import SnifferState
    from tools.can_nt.can_tx import start_tx_if_requested
    from tools.common.time_utils import timestamp_compact
    from tools.common.app_versions import (
        APP_CAN_BRIDGE_NAME,
        VERSIONS,
        VERSION_HEADER,
        format_version_line,
    )
    from tools.common.build_info import build_lines
    from tools.can_nt.bridge_cli import BridgeCli
    from tools.can_nt.bridge_session import BridgeSession

# Constants (NetworkTables table names).
NT_TABLE_ROOT = "bringup"
NT_TABLE_UI = "ui"
NT_TABLE_TESTS = "tests"
NT_TABLE_DIAG = "diag"

# Constants (version output).
VERSION_APP_NAME = APP_CAN_BRIDGE_NAME
VERSION_TITLE = VERSION_HEADER
VERSION_ARG_ATTR = "version"

# Constants (device keys).
DEVICE_KEY_LABEL = "label"
DEVICE_KEY_MFG = "manufacturer"
DEVICE_KEY_TYPE = "device_type"
DEVICE_KEY_ID = "device_id"
DEVICE_KEY_PREFER_STATUS = "prefer_status"

# Constants (unknown label handling).
UNKNOWN_LABEL_PREFIX = "UNPROFILED_DEVICE_"
CONSOLE_UNKNOWN_LABEL_PREFIX = "UNPROFILED_CONSOLE_"


def _print_version_banner() -> None:
    """
    NAME
        _print_version_banner - Print the can_nt_bridge version banner.
    """
    version = VERSIONS.get(VERSION_APP_NAME, "")
    if not version:
        return
    print(VERSION_TITLE)
    print(format_version_line(VERSION_APP_NAME, version))
    for line in build_lines():
        print(line)


def _build_device_maps(
    devices: List[Dict[str, Any]],
) -> Tuple[Dict[Tuple[int, int, int], str], Dict[int, List[str]]]:
    """
    NAME
        _build_device_maps - Build CAN-key and device-id label maps.

    RETURNS
        (can_to_label, id_to_labels).
    """
    can_to_label: Dict[Tuple[int, int, int], str] = {}
    id_to_labels: Dict[int, List[str]] = {}
    for spec in devices:
        label = str(spec.get(DEVICE_KEY_LABEL, "")).strip()
        if not label:
            continue
        try:
            mfg = int(spec.get(DEVICE_KEY_MFG))
            dtype = int(spec.get(DEVICE_KEY_TYPE))
            did = int(spec.get(DEVICE_KEY_ID))
        except Exception:
            continue
        key = (mfg, dtype, did)
        can_to_label[key] = label
        id_to_labels.setdefault(did, []).append(label)
    return can_to_label, id_to_labels


def _maybe_handle_dumps(
    args,
    now: float,
    start: float,
    state: SnifferState,
    devices: List[Dict[str, Any]],
    seen_labels: set[str],
    seen_can_keys: set[Tuple[int, int, int]],
) -> bool:
    """
    NAME
        _maybe_handle_dumps - Emit one-shot dump outputs when timers elapse.

    SYNOPSIS
        handled = _maybe_handle_dumps(args, now, start, analyzer, state, devices, seen_can_keys)

    DESCRIPTION
        Checks configured dump flags and their delays, writes outputs once, and
        signals the caller to exit when a dump completes.

    PARAMETERS
        args: Parsed CLI arguments with dump settings.
        now: Current wall-clock time (seconds).
        start: Process start time (seconds).
        state: SnifferState carrying observed pairs and timestamps.
        devices: Profile device list for context.
        seen_labels: Observed device labels for reporting.
        seen_can_keys: Observed (mfg,type,id) tuples for profile generation.

    RETURNS
        True when a dump was produced and the caller should exit.

    SIDE EFFECTS
        Writes JSON or profile outputs to disk and prints status lines.
    """
    if args.dump_can_expected_ids and (now - start) >= args.dump_after:
        seen_sorted = sorted(seen_labels)
        dump_seen_ids(
            args.dump_can_expected_ids,
            args.profile,
            args.interface,
            args.channel,
            args.bitrate,
            seen_sorted,
        )
        print(f"Dumped observed labels to {args.dump_can_expected_ids}")
        return True
    if args.dump_profile and (now - start) >= args.dump_profile_after:
        seen_keys = sorted(seen_can_keys)
        profile_name = args.dump_profile_name
        if not profile_name:
            profile_name = timestamp_compact("sniffer", now)
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
    if getattr(args, VERSION_ARG_ATTR, False):
        _print_version_banner()
        return 0
    _print_version_banner()
    if args.ui_only:
        args.ui = True
        args.no_can = True
    if args.batch and not args.script:
        print("ERROR: --batch requires --script <file>.")
        return 2

    if args.list_ports:
        ports = list_ports()
        if not ports:
            print("No serial ports found.")
        else:
            print("Available serial ports:")
            for dev, desc in ports:
                print(f"  {dev} ({desc})")
        return 0

    load_error = get_profiles_load_error()
    if args.cli or args.batch:
        if load_error:
            print(f"WARNING: bringup_system.json load failed: {load_error}")
            print("WARNING: Starting CLI in recovery mode (profiles must be repaired before robot tools).")
            from tools.common.paths import profiles_canonical_path, profiles_deploy_path

            profiles_path = profiles_canonical_path()
            if not profiles_path.exists():
                profiles_path = profiles_deploy_path()
            print(f"Recovery profiles source: {profiles_path}")
            print("Next: show workspace")
            print("Next: validate profiles --active")
            print("Next: show devices")
        else:
            data_version = get_profiles_data_version()
            if data_version:
                print(f"Profiles data_version: {data_version}")
            data_hash = get_profiles_data_hash()
            if data_hash:
                print(f"Profiles data_hash: {data_hash}")
        nt, _ = setup_nt(args)
        ui_table = None
        if nt is not None:
            ui_table = nt.getTable("bringup").getSubTable("ui")

        def _read_nt_state() -> Dict[str, Any]:
            if ui_table is None:
                return {}
            return {
                "enabled": ui_table.getEntry("state/enabled").getBoolean(False),
                "estopped": ui_table.getEntry("state/estopped").getBoolean(False),
                "mode": ui_table.getEntry("state/mode").getString("disabled"),
                "lastAckMs": ui_table.getEntry("state/lastAckMs").getDouble(0.0),
                "sessionId": ui_table.getEntry("state/sessionId").getString(""),
            }

        session = BridgeSession(args.rio, args.ui_tcp_port, nt_state_reader=_read_nt_state)
        cli = BridgeCli(
            session,
            batch=bool(args.batch),
            conflict_policy=args.conflict_policy,
            echo_enabled=bool(getattr(args, "cli_echo", False)),
            message_level=(args.cli_messages or None),
            recovery_mode=bool(load_error),
        )
        if args.batch:
            try:
                with open(args.script, "r", encoding="utf-8") as handle:
                    lines = handle.readlines()
            except Exception as exc:
                print(f"ERROR: Failed to read script: {exc}")
                return 2
            return cli.run_batch(lines)
        return cli.run_interactive()

    if load_error:
        print(f"ERROR: bringup_system.json load failed: {load_error}")
        return 2
    data_version = get_profiles_data_version()
    if data_version:
        print(f"Profiles data_version: {data_version}")
    data_hash = get_profiles_data_hash()
    if data_hash:
        print(f"Profiles data_hash: {data_hash}")

    devices, expected_ids = get_profile(args.profile)
    can_to_label, id_to_labels = _build_device_maps(devices)
    unknown_labels: Dict[Tuple[int, int, int], str] = {}
    unknown_label_counter = 0
    seen_can_keys: set[Tuple[int, int, int]] = set()
    seen_labels: set[str] = set()
    console_unknown_labels: Dict[int, str] = {}
    console_unknown_counter = 0

    channel = ""
    if not args.no_can:
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

    bus = None
    can = None
    if not args.no_can:
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
    ui_table = None
    tests_table = None
    diag_table = None
    if nt is not None:
        root_table = nt.getTable(NT_TABLE_ROOT)
        ui_table = root_table.getSubTable(NT_TABLE_UI)
        tests_table = root_table.getSubTable(NT_TABLE_TESTS)
        diag_table = root_table.getSubTable(NT_TABLE_DIAG)

    console_monitor = None
    def _resolve_console_label(device_id: int) -> str:
        nonlocal console_unknown_counter
        labels = id_to_labels.get(device_id, [])
        if len(labels) == 1:
            return labels[0]
        label = console_unknown_labels.get(device_id)
        if not label:
            console_unknown_counter += 1
            label = f"{CONSOLE_UNKNOWN_LABEL_PREFIX}{console_unknown_counter}"
            console_unknown_labels[device_id] = label
        return label

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
            device_label_resolver=_resolve_console_label,
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
    reload_queue: queue.Queue[Tuple[str, float]] = queue.Queue()
    key_thread = None
    key_stop = threading.Event()
    tx_stop = threading.Event()
    tx_thread = None

    def _print_marker_banner() -> None:
        print("Marker keys: [1]=0.25 [2]=0.50 [3]=0.75 [4]=1.00 [0]=stop [m]=mark [q]=quit [h]=help")
        print("Other keys: [r]=reload profiles")
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
                    if key.lower() == "r":
                        reload_queue.put((key, time.time()))
                    else:
                        key_queue.put((key, time.time()))
            else:
                time.sleep(0.01)

    if True:
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
    tx_thread = None
    if bus is not None and can is not None:
        tx_thread = start_tx_if_requested(args, bus, can, tx_stop)

    def _send_ui_command(
        name: str, args_payload: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """
        NAME
            _send_ui_command - Emit a bringup UI command over NetworkTables.
        """
        if ui_table is None:
            return None
        if not hasattr(_send_ui_command, "_seq"):
            _send_ui_command._seq = 0  # type: ignore[attr-defined]
        _send_ui_command._seq += 1  # type: ignore[attr-defined]
        seq = int(_send_ui_command._seq)  # type: ignore[attr-defined]
        ui_table.getEntry("cmd/name").setString(str(name))
        ui_table.getEntry("cmd/args/json").setString(
            json.dumps(args_payload) if args_payload else ""
        )
        ui_table.getEntry("cmd/ts").setDouble(float(time.time()))
        ui_table.getEntry("cmd/seq").setInteger(seq)
        return seq

    def _set_ui_command_seq(value: int) -> None:
        """
        NAME
            _set_ui_command_seq - Seed the UI command sequence counter.
        """
        if value < 0:
            value = 0
        _send_ui_command._seq = int(value)  # type: ignore[attr-defined]

    _send_ui_command.set_seq = _set_ui_command_seq  # type: ignore[attr-defined]

    def _run_sniffer(stop_event: Optional[threading.Event]) -> int:
        """
        NAME
            _run_sniffer - Run the CAN sniffer loop until stopped.
        """
        nonlocal stop_requested, last_publish, last_summary, startup_summary_done
        nonlocal unknown_label_counter, console_unknown_counter
        try:
            while True:
                if stop_event is not None and stop_event.is_set():
                    break
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

                while True:
                    try:
                        _key, _ts = reload_queue.get_nowait()
                    except queue.Empty:
                        break
                    print("Reloading profiles...")
                    ok, err = reload_profiles()
                    if not ok:
                        print(f"ERROR: reload failed: {err}")
                        continue
                    try:
                        new_devices, new_expected = get_profile(args.profile)
                    except Exception as exc:
                        print(f"ERROR: reload failed: {exc}")
                        continue
                    devices.clear()
                    devices.extend(new_devices)
                    can_to_label.clear()
                    id_to_labels.clear()
                    new_can_to_label, new_id_to_labels = _build_device_maps(devices)
                    can_to_label.update(new_can_to_label)
                    id_to_labels.update(new_id_to_labels)
                    unknown_labels.clear()
                    unknown_label_counter = 0
                    seen_can_keys.clear()
                    seen_labels.clear()
                    console_unknown_labels.clear()
                    console_unknown_counter = 0
                    analyzer.expected_ids = set(new_expected or [])
                    dv = get_profiles_data_version()
                    dh = get_profiles_data_hash()
                    if dv:
                        print(f"Profiles data_version: {dv}")
                    if dh:
                        print(f"Profiles data_hash: {dh}")

                if _maybe_handle_dumps(args, now, start, state, devices, seen_labels, seen_can_keys):
                    return 0

                if (
                    not startup_summary_done
                    and args.startup_summary_after > 0.0
                    and (now - start) >= args.startup_summary_after
                ):
                    startup_summary_done = True
                    print("Startup OK.")
                    summary = analyzer.summary(
                        now,
                        args.stale_s,
                        top_n=args.top_n,
                        label_lookup=can_to_label,
                        decode_device_key=decode_frc_ext_id,
                    )
                    extra = build_summary_extra(
                        summary,
                        devices,
                        analyzer,
                        state,
                        bus,
                        args.bitrate,
                        now,
                        args.stale_s,
                    )
                    print_summary(summary, now, extra)

                msg = None
                if bus is not None:
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
                    seen_can_keys.add(key)
                    label = can_to_label.get(key)
                    if not label:
                        label = unknown_labels.get(key)
                        if not label:
                            unknown_label_counter += 1
                            label = f"{UNKNOWN_LABEL_PREFIX}{unknown_label_counter}"
                            unknown_labels[key] = label
                    seen_labels.add(label)
                    state.last_seen[label] = now
                    state.msg_count[label] = state.msg_count.get(label, 0) + 1

                    is_status, is_control = classify_frame(
                        arb_id=arb_id,
                        manufacturer=mfg,
                        device_type=dtype,
                        api_class=api_class,
                        api_index=api_index,
                    )
                    if is_status:
                        state.status_last_seen[label] = now
                    if is_control:
                        state.control_last_seen[label] = now

                    print_label_match = (
                        not args.print_label
                        or label.lower() == args.print_label.lower()
                    )

                    if args.print_any and print_label_match:
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
                    if args.print_status and is_status and print_label_match:
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
                    if args.print_control and is_control and print_label_match:
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

                    pair_key = (label, api_class, api_index)
                    stats = state.pair_stats.get(pair_key)
                    if stats is None:
                        stats = {"first": now, "last": now, "count": 0.0}
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
                    label_lookup=can_to_label,
                    decode_device_key=decode_frc_ext_id,
                    table=table,
                    bus=bus,
                    console_monitor=console_monitor,
                )

        except KeyboardInterrupt:
            print("Stopping (Ctrl+C)...")
        finally:
            now = time.time()
            if console_monitor is not None:
                console_monitor.stop()
            try:
                summary = analyzer.summary(
                    now,
                    stale_s=args.stale_s,
                    top_n=args.top_n,
                    label_lookup=can_to_label,
                    decode_device_key=decode_frc_ext_id,
                )
                print("=== Final Summary ===")
                extra = build_summary_extra(
                    summary,
                    devices,
                    analyzer,
                    state,
                    bus,
                    args.bitrate,
                    now,
                    args.stale_s,
                )
                print_summary(summary, now, extra)
            except Exception as exc:
                print(f"WARNING: Failed to print summary on exit: {exc}")

            key_stop.set()
            tx_stop.set()
            try:
                pcap.stop()
                print("PCAP logger stopped.")
            except Exception as exc:
                print(f"WARNING: Failed to stop PCAP logger: {exc}")
            if bus is not None:
                try:
                    bus.shutdown()
                    print("CAN bus closed.")
                except Exception as exc:
                    print(f"WARNING: Failed to close CAN bus: {exc}")

        return 0

    if args.ui:
        if nt is None or ui_table is None:
            print("ERROR: --ui requires NetworkTables (remove --no-nt).")
            return 2
        try:
            from .bringup_ui import BringupControlUI
        except ImportError:
            from tools.can_nt.bringup_ui import BringupControlUI

        def _nt_is_connected() -> bool:
            """
            NAME
                _nt_is_connected - Return current NT connection state.
            """
            try:
                return bool(nt.isConnected())
            except Exception:
                return False

        stop_event = threading.Event()
        thread = threading.Thread(target=_run_sniffer, args=(stop_event,), daemon=True)
        thread.start()
        ui = BringupControlUI(
            ui_table=ui_table,
            tests_table=tests_table,
            diag_table=diag_table,
            rio_host=args.rio,
            tcp_port=args.ui_tcp_port,
            is_connected=_nt_is_connected,
            on_close=stop_event.set,
        )
        def _release_ui_lock() -> None:
            try:
                ui.release_lock()
            except Exception:
                pass

        def _handle_signal(_signum, _frame) -> None:
            _release_ui_lock()
            stop_event.set()
            raise SystemExit(0)

        original_sigint = signal.getsignal(signal.SIGINT)
        original_sigterm = signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)
        try:
            ui.mainloop()
        finally:
            _release_ui_lock()
            stop_event.set()
            thread.join(timeout=2.0)
            signal.signal(signal.SIGINT, original_sigint)
            signal.signal(signal.SIGTERM, original_sigterm)
        return 0

    return _run_sniffer(None)


if __name__ == "__main__":
    raise SystemExit(main())
