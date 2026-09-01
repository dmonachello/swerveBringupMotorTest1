from __future__ import annotations

"""
NAME
    command_workflow_service.py - Shared host-side command tracking helpers.

SYNOPSIS
    from tools.can_nt.command_workflow_service import wait_for_command_event

DESCRIPTION
    Provides reusable command lifecycle helpers above BridgeSession so multiple
    host surfaces can share tracker start/wait behavior instead of duplicating
    ACK/OUT orchestration.
"""

import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from tools.can_nt.bridge_cmd_tracker import CommandTracker
from tools.can_nt.bridge_session import BridgeEvent, BridgeSession

WAIT_SLEEP_SEC = 0.02
EVENT_TYPE_ACK = "ack"
EVENT_TYPE_OUT = "out"


@dataclass(frozen=True)
class WaitResult:
    """
    NAME
        WaitResult - Terminal wait result for one tracked command.
    """

    event: Optional[BridgeEvent]
    ack_status: str
    ack_message: str


def start_tracked_command(
    tracker: CommandTracker,
    name: str,
    args: Optional[Dict[str, Any]],
    seq: Optional[int],
    *,
    now: Optional[float] = None,
    retryable: bool = True,
    pending_ack: bool = True,
    pending_out: bool = True,
    timeout_sec: Optional[float] = None,
) -> Optional[int]:
    """
    NAME
        start_tracked_command - Start tracker state for a newly sent command.
    """
    if seq is None:
        return None
    tracker.start(
        name,
        args,
        seq,
        pending_ack=pending_ack,
        pending_out=pending_out,
        retryable=retryable,
        now=now,
        timeout_sec=timeout_sec,
    )
    return seq


def send_tracked_command(
    session: BridgeSession,
    tracker: CommandTracker,
    name: str,
    args: Optional[Dict[str, Any]] = None,
    *,
    sender: Optional[Callable[[BridgeSession, str, Optional[Dict[str, Any]]], Optional[int]]] = None,
    now: Optional[float] = None,
    retryable: bool = True,
    pending_ack: bool = True,
    pending_out: bool = True,
    timeout_sec: Optional[float] = None,
) -> Optional[int]:
    """
    NAME
        send_tracked_command - Send a command and immediately begin shared tracking.
    """
    send_fn = sender or (lambda current_session, command_name, command_args: current_session.send_command(command_name, command_args))
    seq = send_fn(session, name, args)
    return start_tracked_command(
        tracker,
        name,
        args,
        seq,
        now=now,
        retryable=retryable,
        pending_ack=pending_ack,
        pending_out=pending_out,
        timeout_sec=timeout_sec,
    )


def wait_for_command_event(
    session: BridgeSession,
    tracker: CommandTracker,
    seq: Optional[int],
    *,
    timeout_sec: float,
    on_event: Optional[Callable[[BridgeEvent], None]] = None,
    sleep_sec: float = WAIT_SLEEP_SEC,
) -> WaitResult:
    """
    NAME
        wait_for_command_event - Wait for the terminal OUT event for one command sequence.
    """
    if seq is None:
        return WaitResult(None, "", "")
    deadline = time.time() + timeout_sec
    ack_status = ""
    ack_message = ""
    while time.time() < deadline:
        events = session.poll_events()
        if not events:
            time.sleep(sleep_sec)
            continue
        for event in events:
            if callable(on_event):
                on_event(event)
            if event.type in (EVENT_TYPE_ACK, EVENT_TYPE_OUT):
                tracker.handle_event(event)
            if event.seq == seq and event.type == EVENT_TYPE_ACK:
                ack_status = event.status
                ack_message = event.message
            if event.seq == seq and event.type == EVENT_TYPE_OUT:
                if ack_status:
                    event.status = ack_status
                    event.message = ack_message
                return WaitResult(event, ack_status, ack_message)
    return WaitResult(None, ack_status, ack_message)
