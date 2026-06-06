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
from dataclasses import dataclass, field
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
    from tools.can_nt.visibility_provider import VisibilityProvider, SourceInfo
    from tools.can_nt.visibility_constants import (
        VIS_KEY_SEPARATOR,
        VIS_MS_PER_SEC,
    )
    from tools.can_nt.source_config import load_sources_config, SourceConfig
    from tools.common.time_utils import timestamp_compact
    from tools.common.runtime_constants import (
        RUNTIME_COMPONENT_CLI,
        RUNTIME_COMPONENT_CONSOLE,
        RUNTIME_COMPONENT_PCAP,
        RUNTIME_COMPONENT_SESSION,
        RUNTIME_COMPONENT_SNIFFER,
        RUNTIME_COMPONENT_SOURCES,
        RUNTIME_COMPONENT_SOURCE_PREFIX,
        RUNTIME_COMPONENT_VISIBILITY,
        RUNTIME_DETAIL_AVAILABLE_PREFIX,
        RUNTIME_DETAIL_COUNT_PREFIX,
        RUNTIME_DETAIL_DISABLED,
        RUNTIME_DETAIL_ENABLED,
        RUNTIME_DETAIL_HANDSHAKE_DONE,
        RUNTIME_DETAIL_HANDSHAKE_PENDING,
        RUNTIME_DETAIL_SEPARATOR,
        RUNTIME_DETAIL_SESSION_PREFIX,
        RUNTIME_KEY_ALIVE,
        RUNTIME_KEY_COMPONENTS,
        RUNTIME_KEY_DAEMON,
        RUNTIME_KEY_DETAIL,
        RUNTIME_KEY_IDENT,
        RUNTIME_KEY_NAME,
        RUNTIME_KEY_STATUS,
        RUNTIME_KEY_THREADS,
        RUNTIME_STATUS_AVAILABLE,
        RUNTIME_STATUS_CONNECTED,
        RUNTIME_STATUS_DISABLED,
        RUNTIME_STATUS_DISCONNECTED,
        RUNTIME_STATUS_ENABLED,
        RUNTIME_STATUS_RUNNING,
        RUNTIME_STATUS_STOPPED,
        RUNTIME_STATUS_UNAVAILABLE,
    )
    from tools.common.app_versions import (
        APP_CAN_BRIDGE_NAME,
        VERSIONS,
        VERSION_HEADER,
        format_version_line,
    )
    from tools.common.build_info import build_lines
    from tools.common.profile_constants import (
        KEY_DEVICE_TYPE,
        KEY_ID,
        KEY_LABEL,
        KEY_MANUFACTURER,
    )
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
    from tools.can_nt.visibility_provider import VisibilityProvider, SourceInfo
    from tools.can_nt.visibility_constants import (
        VIS_KEY_SEPARATOR,
        VIS_MS_PER_SEC,
    )
    from tools.can_nt.source_config import load_sources_config, SourceConfig
    from tools.common.time_utils import timestamp_compact
    from tools.common.runtime_constants import (
        RUNTIME_COMPONENT_CLI,
        RUNTIME_COMPONENT_CONSOLE,
        RUNTIME_COMPONENT_PCAP,
        RUNTIME_COMPONENT_SESSION,
        RUNTIME_COMPONENT_SNIFFER,
        RUNTIME_COMPONENT_SOURCES,
        RUNTIME_COMPONENT_SOURCE_PREFIX,
        RUNTIME_COMPONENT_VISIBILITY,
        RUNTIME_DETAIL_AVAILABLE_PREFIX,
        RUNTIME_DETAIL_COUNT_PREFIX,
        RUNTIME_DETAIL_DISABLED,
        RUNTIME_DETAIL_ENABLED,
        RUNTIME_DETAIL_HANDSHAKE_DONE,
        RUNTIME_DETAIL_HANDSHAKE_PENDING,
        RUNTIME_DETAIL_SEPARATOR,
        RUNTIME_DETAIL_SESSION_PREFIX,
        RUNTIME_KEY_ALIVE,
        RUNTIME_KEY_COMPONENTS,
        RUNTIME_KEY_DAEMON,
        RUNTIME_KEY_DETAIL,
        RUNTIME_KEY_IDENT,
        RUNTIME_KEY_NAME,
        RUNTIME_KEY_STATUS,
        RUNTIME_KEY_THREADS,
        RUNTIME_STATUS_AVAILABLE,
        RUNTIME_STATUS_CONNECTED,
        RUNTIME_STATUS_DISABLED,
        RUNTIME_STATUS_DISCONNECTED,
        RUNTIME_STATUS_ENABLED,
        RUNTIME_STATUS_RUNNING,
        RUNTIME_STATUS_STOPPED,
        RUNTIME_STATUS_UNAVAILABLE,
    )
    from tools.common.app_versions import (
        APP_CAN_BRIDGE_NAME,
        VERSIONS,
        VERSION_HEADER,
        format_version_line,
    )
    from tools.common.build_info import build_lines
    from tools.common.profile_constants import (
        KEY_DEVICE_TYPE,
        KEY_ID,
        KEY_LABEL,
        KEY_MANUFACTURER,
    )
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
DEVICE_KEY_LABEL = KEY_LABEL
DEVICE_KEY_MFG = KEY_MANUFACTURER
DEVICE_KEY_TYPE = KEY_DEVICE_TYPE
DEVICE_KEY_ID = KEY_ID
DEVICE_KEY_PREFER_STATUS = "prefer_status"

# Constants (unknown label handling).
CONSOLE_UNKNOWN_LABEL_PREFIX = "UNPROFILED_CONSOLE_"
EMPTY_STRING = ""
PROFILE_NONE = "(none)"

# Constants (multi-source CAN).
SOURCE_DEFAULT_ID = "default"
SOURCE_DEFAULT_LABEL = "default"
SOURCE_DEFAULT_PORT = ""
SOURCE_PRIMARY_INDEX = 0
SOURCE_READ_TIMEOUT_SEC = 0.05
SOURCE_ERROR_BACKOFF_SEC = 0.25
SOURCE_THREAD_JOIN_SEC = 2.0
SOURCE_AVAILABLE_FALSE = False
SOURCE_AVAILABLE_TRUE = True
SOURCE_ENABLED_TRUE = True
SOURCE_ENABLED_FALSE = False
SOURCE_QUEUE_EMPTY = None
SOURCE_ERR_LOAD = "ERROR: Failed to load sources: {error}"
SOURCE_ERR_DUP = "ERROR: Duplicate source id: {source_id}"
SOURCE_ERR_PORT = "ERROR: Source '{source_id}' missing port."
SOURCE_ERR_OPEN = "ERROR: Failed to open CAN bus for source {source_id}: {error}"
SOURCE_WARN_OPEN = "WARNING: Source {source_id} unavailable ({error})."
SOURCE_INFO_DISABLED = "Source {source_id} disabled; marking unavailable."
SOURCE_INFO_AVAILABLE = "Source {source_id} available."
PCAP_LOGGER_STOPPED = "PCAP logger stopped."
THREAD_NAME_SNIFFER = "sniffer"
THREAD_NAME_KEYBOARD = "keyboard"
THREAD_NAME_SOURCE_PREFIX = "source:"
PAIR_STATS_FIRST = "first"
PAIR_STATS_LAST = "last"
PAIR_STATS_COUNT = "count"
FRAME_KIND_FRAME = "frame"
FRAME_KIND_STATUS = "status"
FRAME_KIND_CONTROL = "control"
EMPTY_BYTES = b""
PAIR_STATS_COUNT_INIT = 0.0
PAIR_STATS_COUNT_INC = 1.0
INT_ONE = 1
INT_ZERO = 0
FLOAT_ZERO = 0.0
NT_UI_STATE_ENABLED = "state/enabled"
NT_UI_STATE_ESTOPPED = "state/estopped"
NT_UI_STATE_MODE = "state/mode"
NT_UI_STATE_LAST_ACK = "state/lastAckMs"
NT_UI_STATE_SESSION = "state/sessionId"
NT_UI_STATE_SELECTED_PROFILE = "state/selectedProfile"
NT_UI_STATE_ACTIVE_RUNTIME_PROFILE = "state/activeRuntimeProfile"
NT_UI_MODE_DISABLED = "disabled"
CAN_MSG_DATA_ATTR = "data"


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
        label = str(spec.get(DEVICE_KEY_LABEL, EMPTY_STRING)).strip()
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


def _normalize_profile_name(value: object) -> str:
    """
    NAME
        _normalize_profile_name - Return a trimmed profile name or empty string.
    """
    if not isinstance(value, str):
        return EMPTY_STRING
    normalized = value.strip()
    if not normalized or normalized == PROFILE_NONE:
        return EMPTY_STRING
    return normalized


def _resolve_profile_context_name(ui_table, fallback: str) -> str:
    """
    NAME
        _resolve_profile_context_name - Resolve host profile context from robot NT state.

    DESCRIPTION
        Prefers the robot's active runtime profile, then its selected profile,
        then falls back to the local startup/default profile.
    """
    fallback_name = _normalize_profile_name(fallback)
    if ui_table is None:
        return fallback_name
    active_name = _normalize_profile_name(
        ui_table.getEntry(NT_UI_STATE_ACTIVE_RUNTIME_PROFILE).getString(EMPTY_STRING)
    )
    if active_name:
        return active_name
    selected_name = _normalize_profile_name(
        ui_table.getEntry(NT_UI_STATE_SELECTED_PROFILE).getString(EMPTY_STRING)
    )
    if selected_name:
        return selected_name
    return fallback_name


@dataclass
class FrameItem:
    """
    NAME
        FrameItem - Queue item for a received CAN frame.
    """

    source_id: str
    msg: object
    ts_s: float


@dataclass
class SourceRuntime:
    """
    NAME
        SourceRuntime - Runtime state for an analyzer source.
    """

    source_id: str
    label: str
    port: str
    interface: str
    bitrate: int
    enabled: bool
    bus: Optional[object] = None
    available: bool = SOURCE_AVAILABLE_FALSE
    thread: Optional[threading.Thread] = None
    stop_event: threading.Event = field(default_factory=threading.Event)


def _visibility_key_from_ids(mfg: int, dtype: int, device_id: int) -> str:
    """
    NAME
        _visibility_key_from_ids - Build a visibility key from CAN identity.
    """
    return (
        str(mfg)
        + VIS_KEY_SEPARATOR
        + str(dtype)
        + VIS_KEY_SEPARATOR
        + str(device_id)
    )


def _build_visibility_expected(devices: List[Dict[str, Any]]) -> List[Tuple[str, str]]:
    """
    NAME
        _build_visibility_expected - Build expected visibility keys for a profile.

    PARAMETERS
        devices: Profile device entries (CAN only).

    RETURNS
        List of (label, identity_key) tuples.
    """
    expected: List[Tuple[str, str]] = []
    for spec in devices:
        label = str(spec.get(DEVICE_KEY_LABEL, EMPTY_STRING)).strip()
        if not label:
            continue
        try:
            mfg = int(spec.get(DEVICE_KEY_MFG))
            dtype = int(spec.get(DEVICE_KEY_TYPE))
            did = int(spec.get(DEVICE_KEY_ID))
        except Exception:
            continue
        key = _visibility_key_from_ids(mfg, dtype, did)
        expected.append((label, key))
    return expected


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
    if (args.cli or args.batch) and load_error:
        print(f"WARNING: bringup_system.json load failed: {load_error}")
        print("WARNING: Starting CLI in recovery mode (profiles must be repaired before robot tools).")
        from tools.common.paths import profiles_canonical_path

        profiles_path = profiles_canonical_path()
        print(f"Recovery profiles source: {profiles_path}")
        print("Next: show workspace")
        print("Next: validate profiles --active")
        print("Next: show devices")
        nt, _ = setup_nt(args)
        ui_table = None
        if nt is not None:
            ui_table = nt.getTable("bringup").getSubTable("ui")

        def _read_nt_state() -> Dict[str, Any]:
            if ui_table is None:
                return {}
            return {
                "enabled": ui_table.getEntry(NT_UI_STATE_ENABLED).getBoolean(False),
                "estopped": ui_table.getEntry(NT_UI_STATE_ESTOPPED).getBoolean(False),
                "mode": ui_table.getEntry(NT_UI_STATE_MODE).getString(NT_UI_MODE_DISABLED),
                "lastAckMs": ui_table.getEntry(NT_UI_STATE_LAST_ACK).getDouble(FLOAT_ZERO),
                "sessionId": ui_table.getEntry(NT_UI_STATE_SESSION).getString(EMPTY_STRING),
                "selectedProfile": ui_table.getEntry(NT_UI_STATE_SELECTED_PROFILE).getString(EMPTY_STRING),
                "activeRuntimeProfile": ui_table.getEntry(NT_UI_STATE_ACTIVE_RUNTIME_PROFILE).getString(EMPTY_STRING),
            }

        session = BridgeSession(args.rio, args.ui_rest_port, nt_state_reader=_read_nt_state)
        cli = BridgeCli(
            session,
            batch=bool(args.batch),
            conflict_policy=args.conflict_policy,
            echo_enabled=bool(getattr(args, "cli_echo", False)),
            message_level=(args.cli_messages or None),
            recovery_mode=bool(load_error),
            visibility_provider=None,
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
    seen_can_keys: set[Tuple[int, int, int]] = set()
    seen_labels: set[str] = set()
    console_unknown_labels: Dict[int, str] = {}
    console_unknown_counter = 0

    visibility_provider = VisibilityProvider(
        timeout_ms=int(args.visibility_timeout_ms),
        observed_retention_ms=int(args.observed_retention_ms),
    )
    visibility_provider.set_expected_devices(_build_visibility_expected(devices))

    sources_config: List[SourceConfig] = []
    sources_error = EMPTY_STRING
    if args.sources:
        sources_config, sources_error = load_sources_config(args.sources)
        if sources_error:
            print(SOURCE_ERR_LOAD.format(error=sources_error))
            return 2

    channel = EMPTY_STRING
    if not args.no_can and not sources_config:
        channel, _, channel_status = maybe_auto_channel(args)
        if channel_status != 0 or not channel:
            return channel_status
    if not sources_config:
        sources_config = [
            SourceConfig(
                source_id=SOURCE_DEFAULT_ID,
                label=SOURCE_DEFAULT_LABEL,
                port=channel or args.channel,
                enabled=SOURCE_ENABLED_TRUE if not args.no_can else SOURCE_ENABLED_FALSE,
            )
        ]
    source_config_map: Dict[str, SourceConfig] = {cfg.source_id: cfg for cfg in sources_config}

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
    source_runtimes: List[SourceRuntime] = []
    primary_source_id = EMPTY_STRING
    primary_bus = None
    primary_channel = EMPTY_STRING
    if not args.no_can:
        # Delayed imports so --help still works without packages installed
        import can  # type: ignore
    source_ids_seen: set[str] = set()
    for cfg in sources_config:
        if cfg.source_id in source_ids_seen:
            print(SOURCE_ERR_DUP.format(source_id=cfg.source_id))
            return 2
        source_ids_seen.add(cfg.source_id)
        interface = cfg.interface or args.interface
        bitrate = int(cfg.bitrate) if cfg.bitrate else int(args.bitrate)
        runtime = SourceRuntime(
            source_id=cfg.source_id,
            label=cfg.label,
            port=cfg.port,
            interface=interface,
            bitrate=bitrate,
            enabled=bool(cfg.enabled) and not args.no_can,
        )
        if not runtime.enabled:
            print(SOURCE_INFO_DISABLED.format(source_id=cfg.source_id))
            source_runtimes.append(runtime)
            continue
        if not cfg.port:
            print(SOURCE_ERR_PORT.format(source_id=cfg.source_id))
            return 2
        try:
            bus = can.Bus(interface=interface, channel=cfg.port, bitrate=bitrate)
            runtime.bus = bus
            runtime.available = SOURCE_AVAILABLE_TRUE
            if primary_bus is None:
                primary_bus = bus
                primary_source_id = cfg.source_id
                primary_channel = cfg.port
            print(SOURCE_INFO_AVAILABLE.format(source_id=cfg.source_id))
        except Exception as exc:
            runtime.available = SOURCE_AVAILABLE_FALSE
            print(SOURCE_WARN_OPEN.format(source_id=cfg.source_id, error=exc))
        source_runtimes.append(runtime)
    if primary_bus is not None:
        bus = primary_bus
    source_runtime_map: Dict[str, SourceRuntime] = {rt.source_id: rt for rt in source_runtimes}

    if args.pcap and args.pcap_pipe:
        print("ERROR: Use --pcap or --pcap-pipe, not both.")
        return 2

    if primary_channel:
        channel = primary_channel
    pcap_comment = build_pcap_comment(args, channel)
    pcap_enabled = bool(args.pcap or args.pcap_pipe)
    pcap = setup_pcap(args, pcap_comment)
    if args.enable_markers:
        if args.pcap and not args.pcap.lower().endswith(".pcapng"):
            print("ERROR: Marker injection requires a .pcapng output file.")
            return 2

    source_infos: List[SourceInfo] = []
    for runtime in source_runtimes:
        cfg = source_config_map.get(runtime.source_id)
        timeout_ms = int(cfg.visibility_timeout_ms) if cfg and cfg.visibility_timeout_ms else int(args.visibility_timeout_ms)
        source_infos.append(
            SourceInfo(
                source_id=runtime.source_id,
                label=runtime.label,
                available=runtime.available,
                timeout_ms=timeout_ms,
            )
        )
    visibility_provider.set_sources(source_infos)

    nt, table = setup_nt(args)
    ui_table = None
    tests_table = None
    diag_table = None
    if nt is not None:
        root_table = nt.getTable(NT_TABLE_ROOT)
        ui_table = root_table.getSubTable(NT_TABLE_UI)
        tests_table = root_table.getSubTable(NT_TABLE_TESTS)
        diag_table = root_table.getSubTable(NT_TABLE_DIAG)

    profile_context_name = _normalize_profile_name(args.profile)

    profile_context_error_name = EMPTY_STRING

    def _apply_profile_context(profile_name: str) -> bool:
        """
        NAME
            _apply_profile_context - Re-anchor host device expectations to one profile.
        """
        nonlocal console_unknown_counter, profile_context_name, profile_context_error_name
        resolved_name = _normalize_profile_name(profile_name)
        if not resolved_name or resolved_name == profile_context_name and devices:
            return False
        try:
            new_devices, new_expected = get_profile(resolved_name)
        except Exception as exc:
            if resolved_name != profile_context_error_name:
                print(f"WARNING: profile context switch failed for '{resolved_name}': {exc}")
                profile_context_error_name = resolved_name
            return False
        profile_context_error_name = EMPTY_STRING
        profile_context_name = resolved_name
        devices.clear()
        devices.extend(new_devices)
        can_to_label.clear()
        id_to_labels.clear()
        new_can_to_label, new_id_to_labels = _build_device_maps(devices)
        can_to_label.update(new_can_to_label)
        id_to_labels.update(new_id_to_labels)
        expected_ids.clear()
        expected_ids.update(new_expected)
        seen_can_keys.clear()
        seen_labels.clear()
        console_unknown_labels.clear()
        console_unknown_counter = 0
        analyzer.expected_ids = set(new_expected or [])
        visibility_provider.set_expected_devices(_build_visibility_expected(devices))
        state.last_seen.clear()
        state.status_last_seen.clear()
        state.control_last_seen.clear()
        state.msg_count.clear()
        state.last_status.clear()
        return True

    initial_context = _resolve_profile_context_name(ui_table, profile_context_name)
    if initial_context and initial_context != profile_context_name:
        _apply_profile_context(initial_context)

    console_monitor = None
    console_monitor_enabled = bool(args.console_monitor or args.ui)
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

    if console_monitor_enabled:
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
    frame_queue: queue.Queue[FrameItem] = queue.Queue()
    source_stop_event = threading.Event()
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

    def _source_reader(runtime: SourceRuntime) -> None:
        """
        NAME
            _source_reader - Background reader for a single CAN source.
        """
        bus = runtime.bus
        if bus is None:
            return
        while not source_stop_event.is_set() and not runtime.stop_event.is_set():
            try:
                msg = bus.recv(timeout=SOURCE_READ_TIMEOUT_SEC)
            except Exception as exc:
                if runtime.available:
                    runtime.available = SOURCE_AVAILABLE_FALSE
                    visibility_provider.set_source_available(
                        runtime.source_id,
                        SOURCE_AVAILABLE_FALSE,
                        int(time.time() * VIS_MS_PER_SEC),
                    )
                    print(SOURCE_WARN_OPEN.format(source_id=runtime.source_id, error=exc))
                time.sleep(SOURCE_ERROR_BACKOFF_SEC)
                continue
            if msg is None:
                continue
            if not runtime.available:
                runtime.available = SOURCE_AVAILABLE_TRUE
                visibility_provider.set_source_available(
                    runtime.source_id,
                    SOURCE_AVAILABLE_TRUE,
                    int(time.time() * VIS_MS_PER_SEC),
                )
            frame_queue.put(FrameItem(runtime.source_id, msg, time.time()))

    def _start_source_threads() -> None:
        """
        NAME
            _start_source_threads - Start reader threads for enabled sources.
        """
        for runtime in source_runtimes:
            if runtime.bus is None:
                continue
            thread = threading.Thread(
                target=_source_reader,
                args=(runtime,),
                name=f"{THREAD_NAME_SOURCE_PREFIX}{runtime.source_id}",
                daemon=True,
            )
            runtime.thread = thread
            thread.start()

    def _stop_source_threads() -> None:
        """
        NAME
            _stop_source_threads - Stop reader threads for all sources.
        """
        source_stop_event.set()
        for runtime in source_runtimes:
            runtime.stop_event.set()
        for runtime in source_runtimes:
            if runtime.thread is None:
                continue
            runtime.thread.join(timeout=SOURCE_THREAD_JOIN_SEC)

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

    sniffer_enabled = any(runtime.enabled for runtime in source_runtimes)
    if console_monitor is not None:
        sniffer_enabled = True

    if sniffer_enabled:
        key_thread = threading.Thread(
            target=_keyboard_worker, name=THREAD_NAME_KEYBOARD, daemon=True
        )
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

    def _resolve_device_label(key: Tuple[int, int, int]) -> str:
        """
        NAME
            _resolve_device_label - Resolve a label for a CAN device key.
        """
        label = can_to_label.get(key)
        identity_key = _visibility_key_from_ids(key[0], key[1], key[2])
        return visibility_provider.resolve_label(identity_key, label)

    def _handle_frame_item(item: FrameItem) -> None:
        """
        NAME
            _handle_frame_item - Process a received CAN frame.
        """
        if item is None:
            return
        msg = item.msg
        arb_id = int(msg.arbitration_id)
        data = bytes(getattr(msg, CAN_MSG_DATA_ATTR, EMPTY_BYTES) or EMPTY_BYTES)
        ts_s = item.ts_s
        ts_ms = int(ts_s * VIS_MS_PER_SEC)

        decoded_key = None
        label = None
        try:
            mfg, dtype, did = decode_frc_ext_id(arb_id)
            decoded_key = _visibility_key_from_ids(mfg, dtype, did)
            label = _resolve_device_label((mfg, dtype, did))
        except Exception:
            decoded_key = None
            label = None

        visibility_provider.ingest_frame(
            item.source_id,
            arb_id,
            ts_ms,
            decoded_key=decoded_key,
            label=label,
        )

        if item.source_id != primary_source_id:
            return

        if args.pcap or args.pcap_pipe:
            if not pcap.log(msg, timestamp_s=ts_s):
                state.pcap_errors += INT_ONE

        analyzer.ingest(ts_s, arb_id, data)

        mfg, dtype, did = decode_frc_ext_id(arb_id)
        _, _, api_class, api_index, _ = decode_frc_ext_id_full(arb_id)
        key = (mfg, dtype, did)
        seen_can_keys.add(key)
        label = _resolve_device_label(key)
        seen_labels.add(label)
        state.last_seen[label] = ts_s
        state.msg_count[label] = state.msg_count.get(label, INT_ZERO) + INT_ONE

        is_status, is_control = classify_frame(
            arb_id=arb_id,
            manufacturer=mfg,
            device_type=dtype,
            api_class=api_class,
            api_index=api_index,
        )
        if is_status:
            state.status_last_seen[label] = ts_s
        if is_control:
            state.control_last_seen[label] = ts_s

        print_label_match = (
            not args.print_label
            or label.lower() == args.print_label.lower()
        )

        if args.print_any and print_label_match:
            print(
                format_frame_line(
                    FRAME_KIND_FRAME,
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
                    FRAME_KIND_STATUS,
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
                    FRAME_KIND_CONTROL,
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
            stats = {
                PAIR_STATS_FIRST: ts_s,
                PAIR_STATS_LAST: ts_s,
                PAIR_STATS_COUNT: PAIR_STATS_COUNT_INIT,
            }
            state.pair_stats[pair_key] = stats
        stats[PAIR_STATS_LAST] = ts_s
        stats[PAIR_STATS_COUNT] += PAIR_STATS_COUNT_INC

        state.total_frames += INT_ONE
        state.period_frames += INT_ONE
        state.last_frame_time = ts_s

    def _run_sniffer(stop_event: Optional[threading.Event]) -> int:
        """
        NAME
            _run_sniffer - Run the CAN sniffer loop until stopped.
        """
        nonlocal stop_requested, last_publish, last_summary, startup_summary_done
        nonlocal console_unknown_counter
        try:
            _start_source_threads()
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
                    resolved_context = _resolve_profile_context_name(ui_table, profile_context_name)
                    if not _apply_profile_context(resolved_context):
                        print(f"Profiles reloaded; context remains {resolved_context or profile_context_name}.")
                    dv = get_profiles_data_version()
                    dh = get_profiles_data_hash()
                    if dv:
                        print(f"Profiles data_version: {dv}")
                    if dh:
                        print(f"Profiles data_hash: {dh}")

                resolved_context = _resolve_profile_context_name(ui_table, profile_context_name)
                if resolved_context and resolved_context != profile_context_name:
                    if _apply_profile_context(resolved_context):
                        print(f"Profile context -> {resolved_context}")

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

                runtime = source_runtime_map.get(primary_source_id)
                state.open_ok = bool(runtime.available) if runtime else False
                frame_item = SOURCE_QUEUE_EMPTY
                try:
                    frame_item = frame_queue.get(timeout=SOURCE_READ_TIMEOUT_SEC)
                except queue.Empty:
                    frame_item = SOURCE_QUEUE_EMPTY
                while frame_item is not SOURCE_QUEUE_EMPTY:
                    _handle_frame_item(frame_item)
                    try:
                        frame_item = frame_queue.get_nowait()
                    except queue.Empty:
                        frame_item = SOURCE_QUEUE_EMPTY

                visibility_provider.tick(int(now * VIS_MS_PER_SEC))

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
            _stop_source_threads()
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
            if pcap_enabled:
                try:
                    pcap.stop()
                    print(PCAP_LOGGER_STOPPED)
                except Exception as exc:
                    print(f"WARNING: Failed to stop PCAP logger: {exc}")
            if bus is not None:
                try:
                    bus.shutdown()
                    print("CAN bus closed.")
                except Exception as exc:
                    print(f"WARNING: Failed to close CAN bus: {exc}")

        return 0

    sniffer_thread: Optional[threading.Thread] = None

    def _runtime_details_snapshot() -> Dict[str, object]:
        """
        NAME
            _runtime_details_snapshot - Capture runtime threads/components state.
        """
        thread_entries: List[Dict[str, object]] = []
        for thread in threading.enumerate():
            thread_entries.append(
                {
                    RUNTIME_KEY_NAME: thread.name,
                    RUNTIME_KEY_IDENT: thread.ident,
                    RUNTIME_KEY_DAEMON: bool(thread.daemon),
                    RUNTIME_KEY_ALIVE: bool(thread.is_alive()),
                }
            )
        component_entries: List[Dict[str, object]] = []
        component_entries.append(
            {
                RUNTIME_KEY_NAME: RUNTIME_COMPONENT_CLI,
                RUNTIME_KEY_STATUS: RUNTIME_STATUS_RUNNING,
            }
        )
        sniffer_status = RUNTIME_STATUS_STOPPED
        if sniffer_thread is not None and sniffer_thread.is_alive():
            sniffer_status = RUNTIME_STATUS_RUNNING
        component_entries.append(
            {
                RUNTIME_KEY_NAME: RUNTIME_COMPONENT_SNIFFER,
                RUNTIME_KEY_STATUS: sniffer_status,
            }
        )
        session_status = RUNTIME_STATUS_CONNECTED if session.is_connected() else RUNTIME_STATUS_DISCONNECTED
        detail_parts: List[str] = []
        detail_parts.append(
            RUNTIME_DETAIL_HANDSHAKE_DONE
            if session.handshake_done()
            else RUNTIME_DETAIL_HANDSHAKE_PENDING
        )
        session_id = session.session_id()
        if session_id:
            detail_parts.append(RUNTIME_DETAIL_SESSION_PREFIX + session_id)
        component_entries.append(
            {
                RUNTIME_KEY_NAME: RUNTIME_COMPONENT_SESSION,
                RUNTIME_KEY_STATUS: session_status,
                RUNTIME_KEY_DETAIL: RUNTIME_DETAIL_SEPARATOR.join(detail_parts)
                if detail_parts
                else EMPTY_STRING,
            }
        )
        component_entries.append(
            {
                RUNTIME_KEY_NAME: RUNTIME_COMPONENT_VISIBILITY,
                RUNTIME_KEY_STATUS: (
                    RUNTIME_STATUS_ENABLED if visibility_provider is not None else RUNTIME_STATUS_DISABLED
                ),
            }
        )
        component_entries.append(
            {
                RUNTIME_KEY_NAME: RUNTIME_COMPONENT_PCAP,
                RUNTIME_KEY_STATUS: RUNTIME_STATUS_ENABLED if pcap_enabled else RUNTIME_STATUS_DISABLED,
                RUNTIME_KEY_DETAIL: pcap.pipe_name or pcap.path or EMPTY_STRING,
            }
        )
        component_entries.append(
            {
                RUNTIME_KEY_NAME: RUNTIME_COMPONENT_CONSOLE,
                RUNTIME_KEY_STATUS: (
                    RUNTIME_STATUS_ENABLED if console_monitor is not None else RUNTIME_STATUS_DISABLED
                ),
            }
        )
        enabled_count = sum(INT_ONE for runtime in source_runtimes if runtime.enabled)
        available_count = sum(INT_ONE for runtime in source_runtimes if runtime.available)
        sources_status = RUNTIME_STATUS_ENABLED if enabled_count > INT_ZERO else RUNTIME_STATUS_DISABLED
        sources_detail = (
            f"{RUNTIME_DETAIL_COUNT_PREFIX}{enabled_count}"
            f"{RUNTIME_DETAIL_SEPARATOR}{RUNTIME_DETAIL_AVAILABLE_PREFIX}{available_count}"
        )
        component_entries.append(
            {
                RUNTIME_KEY_NAME: RUNTIME_COMPONENT_SOURCES,
                RUNTIME_KEY_STATUS: sources_status,
                RUNTIME_KEY_DETAIL: sources_detail,
            }
        )
        for runtime in source_runtimes:
            source_name = f"{RUNTIME_COMPONENT_SOURCE_PREFIX}{runtime.source_id}"
            source_status = (
                RUNTIME_STATUS_AVAILABLE if runtime.available else RUNTIME_STATUS_UNAVAILABLE
            )
            component_entries.append(
                {
                    RUNTIME_KEY_NAME: source_name,
                    RUNTIME_KEY_STATUS: source_status,
                    RUNTIME_KEY_DETAIL: (
                        RUNTIME_DETAIL_ENABLED if runtime.enabled else RUNTIME_DETAIL_DISABLED
                    ),
                }
            )
        return {
            RUNTIME_KEY_THREADS: thread_entries,
            RUNTIME_KEY_COMPONENTS: component_entries,
        }

    if args.cli or args.batch:
        ui_table = None
        if nt is not None:
            ui_table = nt.getTable("bringup").getSubTable("ui")

        def _read_nt_state() -> Dict[str, Any]:
            if ui_table is None:
                return {}
            return {
                "enabled": ui_table.getEntry(NT_UI_STATE_ENABLED).getBoolean(False),
                "estopped": ui_table.getEntry(NT_UI_STATE_ESTOPPED).getBoolean(False),
                "mode": ui_table.getEntry(NT_UI_STATE_MODE).getString(NT_UI_MODE_DISABLED),
                "lastAckMs": ui_table.getEntry(NT_UI_STATE_LAST_ACK).getDouble(FLOAT_ZERO),
                "sessionId": ui_table.getEntry(NT_UI_STATE_SESSION).getString(EMPTY_STRING),
                "selectedProfile": ui_table.getEntry(NT_UI_STATE_SELECTED_PROFILE).getString(EMPTY_STRING),
                "activeRuntimeProfile": ui_table.getEntry(NT_UI_STATE_ACTIVE_RUNTIME_PROFILE).getString(EMPTY_STRING),
            }

        session = BridgeSession(args.rio, args.ui_rest_port, nt_state_reader=_read_nt_state)
        cli = BridgeCli(
            session,
            batch=bool(args.batch),
            conflict_policy=args.conflict_policy,
            echo_enabled=bool(getattr(args, "cli_echo", False)),
            message_level=(args.cli_messages or None),
            recovery_mode=bool(load_error),
            visibility_provider=visibility_provider,
            runtime_details_provider=_runtime_details_snapshot,
        )
        stop_event = None
        if sniffer_enabled:
            stop_event = threading.Event()
            thread = threading.Thread(
                target=_run_sniffer,
                args=(stop_event,),
                name=THREAD_NAME_SNIFFER,
                daemon=True,
            )
            sniffer_thread = thread
            thread.start()
        try:
            if args.batch:
                try:
                    with open(args.script, "r", encoding="utf-8") as handle:
                        lines = handle.readlines()
                except Exception as exc:
                    print(f"ERROR: Failed to read script: {exc}")
                    return 2
                return cli.run_batch(lines)
            return cli.run_interactive()
        finally:
            if stop_event is not None:
                stop_event.set()
            if sniffer_thread is not None:
                sniffer_thread.join(timeout=SOURCE_THREAD_JOIN_SEC)

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

        stop_event = None
        thread = None
        if sniffer_enabled:
            stop_event = threading.Event()
            thread = threading.Thread(
                target=_run_sniffer,
                args=(stop_event,),
                name=THREAD_NAME_SNIFFER,
                daemon=True,
            )
            thread.start()
        on_close = stop_event.set if stop_event is not None else (lambda: None)
        ui = BringupControlUI(
            ui_table=ui_table,
            tests_table=tests_table,
            diag_table=diag_table,
            rio_host=args.rio,
            tcp_port=args.ui_rest_port,
            is_connected=_nt_is_connected,
            on_close=on_close,
            visibility_provider=visibility_provider,
        )
        def _release_ui_lock() -> None:
            try:
                ui.release_lock()
            except Exception:
                pass

        def _handle_signal(_signum, _frame) -> None:
            _release_ui_lock()
            if stop_event is not None:
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
            if stop_event is not None:
                stop_event.set()
            if thread is not None:
                thread.join(timeout=SOURCE_THREAD_JOIN_SEC)
            signal.signal(signal.SIGINT, original_sigint)
            signal.signal(signal.SIGTERM, original_sigterm)
        return 0

    return _run_sniffer(None)


if __name__ == "__main__":
    raise SystemExit(main())
