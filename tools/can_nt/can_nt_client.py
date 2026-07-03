from __future__ import annotations

"""
NAME
    can_nt_client.py - Periodic host-side diagnostics update wrapper.

SYNOPSIS
    from tools.can_nt.can_nt_client import publish_updates

DESCRIPTION
    Owns summary/status cadence for the host bridge without publishing
    any external diagnostics transport state.
"""

from typing import Dict, List, Tuple

from .can_analyzer import CanLiveAnalyzer
from .can_reporting import print_status_transitions, build_summary_extra, print_summary
from .can_state import SnifferState, merge_unknown_devices


def publish_updates(
    args,
    now: float,
    last_publish: float,
    last_summary: float,
    analyzer: CanLiveAnalyzer,
    state: SnifferState,
    devices: List[Dict[str, object]],
    label_lookup: Dict[Tuple[int, int, int], str],
    decode_device_key,
    bus,
) -> Tuple[float, float]:
    """
    NAME
        publish_updates - Emit periodic host-side summaries and transitions.

    PARAMETERS
        args: Parsed CLI args controlling publish cadence and features.
        now: Current wall-clock time (seconds).
        last_publish: Last publish timestamp (seconds).
        last_summary: Last summary print timestamp (seconds).
        analyzer: Live analyzer for summary data.
        state: SnifferState with counters and timestamps.
        devices: Profile device list.
        label_lookup: Map of (mfg,type,id) to device label.
        decode_device_key: Function that decodes a CAN ID into (mfg,type,id).
        bus: CAN bus instance for extra summary context.

    RETURNS
        Updated (last_publish, last_summary) timestamps.

    SIDE EFFECTS
        Prints status transitions and summaries.
    """
    if (now - last_publish) < args.publish_period:
        return last_publish, last_summary

    merged_devices = merge_unknown_devices(devices, state.last_seen, args.publish_unknown)

    if args.print_publish:
        print_status_transitions(
            devices=merged_devices,
            last_seen=state.last_seen,
            status_last_seen=state.status_last_seen,
            control_last_seen=state.control_last_seen,
            now=now,
            timeout_s=args.timeout,
            last_status=state.last_status,
        )

    state.period_frames = 0
    state.heartbeat += 1
    if args.print_summary_period and (now - last_summary) >= args.print_summary_period:
        summary = analyzer.summary(
            now,
            stale_s=args.stale_s,
            top_n=args.top_n,
            label_lookup=label_lookup,
            decode_device_key=decode_device_key,
        )
        extra = build_summary_extra(summary, devices, analyzer, state, bus, args.bitrate)
        print_summary(summary, now, extra)
        last_summary = now

    last_publish = now
    return last_publish, last_summary
