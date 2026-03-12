from __future__ import annotations

"""
NAME
    can_nt_client.py - NetworkTables client setup and publish loop helpers.

SYNOPSIS
    from tools.can_nt.can_nt_client import setup_nt, publish_updates

DESCRIPTION
    Encapsulates NT client creation and periodic publishing of device/summary
    data for the CAN diagnostics tool.
"""

import json
from typing import Dict, List, Tuple

from .can_analyzer import CanLiveAnalyzer
from .can_console_monitor import ConsoleMonitor
from .can_nt_publish import publish_devices
from .can_reporting import print_status_transitions, build_summary_extra, print_summary
from .can_state import SnifferState, merge_unknown_devices


def setup_nt(args):
    """
    NAME
        setup_nt - Initialize the NetworkTables client.

    PARAMETERS
        args: Parsed CLI args with NT configuration.

    RETURNS
        (nt_instance, diag_table) or (None, None) when NT is disabled.

    SIDE EFFECTS
        Starts an NT client and attempts to connect to the roboRIO server.
    """
    if args.no_nt:
        return None, None
    # Local import so --help works without NT dependencies.
    from ntcore import NetworkTableInstance
    nt = NetworkTableInstance.getDefault()
    nt.startClient4("can-nt-bridge")
    nt.setServer(args.rio)
    table = nt.getTable("bringup").getSubTable("diag")
    return nt, table


def publish_updates(
    args,
    now: float,
    last_publish: float,
    last_summary: float,
    analyzer: CanLiveAnalyzer,
    state: SnifferState,
    devices: List[Dict[str, object]],
    labels: Dict[Tuple[int, int, int], str],
    table,
    bus,
    console_monitor: ConsoleMonitor | None,
    uses_status_presence,
) -> Tuple[float, float]:
    """
    NAME
        publish_updates - Emit periodic NT updates and optional summaries.

    PARAMETERS
        args: Parsed CLI args controlling publish cadence and features.
        now: Current wall-clock time (seconds).
        last_publish: Last publish timestamp (seconds).
        last_summary: Last summary print timestamp (seconds).
        analyzer: Live analyzer for summary data.
        state: SnifferState with counters and timestamps.
        devices: Profile device list.
        labels: Device label map.
        table: NetworkTables base table (bringup/diag) or None.
        bus: CAN bus instance for extra summary context.
        console_monitor: Optional NetConsole monitor.
        uses_status_presence: Predicate for presence source selection.

    RETURNS
        Updated (last_publish, last_summary) timestamps.

    SIDE EFFECTS
        Writes NetworkTables keys and optionally prints summaries.
    """
    if (now - last_publish) < args.publish_period:
        return last_publish, last_summary

    publish_dt = now - last_publish if last_publish > 0 else args.publish_period
    frames_per_sec = (state.period_frames / publish_dt) if publish_dt > 0 else 0.0
    last_frame_age = (now - state.last_frame_time) if state.last_frame_time > 0 else -1.0

    if table is not None:
        publish_devices(
            table=table,
            devices=merge_unknown_devices(devices, state.last_seen, args.publish_unknown),
            last_seen=state.last_seen,
            status_last_seen=state.status_last_seen,
            control_last_seen=state.control_last_seen,
            uses_status_presence=uses_status_presence,
            msg_count=state.msg_count,
            now=now,
            timeout_s=args.timeout,
        )

    if args.print_publish:
        print_status_transitions(
            devices=devices,
            last_seen=state.last_seen,
            status_last_seen=state.status_last_seen,
            control_last_seen=state.control_last_seen,
            now=now,
            timeout_s=args.timeout,
            last_status=state.last_status,
            uses_status_presence=uses_status_presence,
        )

    if args.publish_can_summary and table is not None:
        summary = analyzer.summary(now, stale_s=args.stale_s, top_n=args.top_n)
        table.getEntry("can/summary/json").setString(
            json.dumps(summary, separators=(",", ":"))
        )

    if table is not None:
        table.getEntry("can/pc/heartbeat").setDouble(float(state.heartbeat))
        table.getEntry("can/pc/openOk").setBoolean(state.open_ok)
        table.getEntry("can/pc/framesPerSec").setDouble(float(frames_per_sec))
        table.getEntry("can/pc/framesTotal").setDouble(float(state.total_frames))
        table.getEntry("can/pc/readErrors").setDouble(float(state.read_errors))
        table.getEntry("can/pc/lastFrameAgeSec").setDouble(float(last_frame_age))
    if console_monitor is not None:
        console_monitor.publish(table, now)

    state.period_frames = 0
    state.heartbeat += 1
    if args.print_summary_period and (now - last_summary) >= args.print_summary_period:
        summary = analyzer.summary(now, stale_s=args.stale_s, top_n=args.top_n)
        extra = build_summary_extra(summary, devices, analyzer, state, bus, args.bitrate)
        print_summary(summary, now, labels, extra)
        last_summary = now

    last_publish = now
    return last_publish, last_summary
