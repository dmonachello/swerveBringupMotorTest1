from __future__ import annotations

import json
from typing import Dict, List, Tuple

from can_analyzer import CanLiveAnalyzer
from can_console_monitor import ConsoleMonitor
from can_nt_publish import publish_devices
from can_reporting import print_status_transitions, build_summary_extra, print_summary
from can_state import SnifferState, merge_unknown_devices


def setup_nt(args):
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
