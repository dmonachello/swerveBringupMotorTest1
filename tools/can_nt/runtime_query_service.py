from __future__ import annotations

"""
NAME
    runtime_query_service.py - Shared JSON query helpers for robot runtime commands.

SYNOPSIS
    from tools.can_nt.runtime_query_service import fetch_runtime_state_payload

DESCRIPTION
    Centralizes the fetch/send/wait/parse flow for robot JSON show commands so
    CLI/UI/config workflows do not each invent their own polling path.
"""

from typing import Any, Dict, Optional

from tools.can_nt.bridge_cmd_tracker import CommandTracker
from tools.can_nt.bridge_session import BridgeEvent, BridgeSession
from tools.can_nt.command_workflow_service import wait_for_command_event
from tools.can_nt.status import SS__NETWORK__ROBOT_UNAVAILABLE, StatusResult

JSON_ARG = "json"
CMD_SHOW_GROUPS = "showGroups"
CMD_SHOW_RUNTIME_STATE = "showRuntimeState"
EVENT_STATUS_OK = "ok"
DEFAULT_TIMEOUT_SEC = 10.0
MSG_FETCH_FAILED = "Failed to fetch robot JSON payload."


def parse_json_arg(raw: str) -> Optional[Any]:
    """
    NAME
        parse_json_arg - Parse a JSON string into Python objects.
    """
    if not raw:
        return None
    import json

    try:
        return json.loads(raw)
    except Exception:
        return None


def fetch_json_command(
    session: BridgeSession,
    command_name: str,
    *,
    args: Optional[Dict[str, Any]] = None,
    timeout_sec: float = DEFAULT_TIMEOUT_SEC,
) -> Optional[Dict[str, Any]]:
    """
    NAME
        fetch_json_command - Send one JSON robot command and return its parsed payload.
    """
    command_args = dict(args or {})
    command_args[JSON_ARG] = True
    seq = session.send_command(command_name, command_args)
    tracker = CommandTracker(timeout_sec=timeout_sec, max_retries=0)
    if seq is None:
        return None
    tracker.start(command_name, command_args, seq)
    result = wait_for_command_event(
        session,
        tracker,
        seq,
        timeout_sec=timeout_sec,
    )
    event = result.event
    if event is None or str(event.status).strip().lower() != EVENT_STATUS_OK:
        return None
    payload = parse_json_arg(event.json_text)
    return payload if isinstance(payload, dict) else None


def fetch_runtime_state_payload(
    session: BridgeSession,
    *,
    timeout_sec: float = DEFAULT_TIMEOUT_SEC,
) -> Optional[Dict[str, Any]]:
    """
    NAME
        fetch_runtime_state_payload - Fetch the runtime-state JSON payload.
    """
    return fetch_json_command(
        session,
        CMD_SHOW_RUNTIME_STATE,
        timeout_sec=timeout_sec,
    )


def fetch_groups_payload(
    session: BridgeSession,
    *,
    timeout_sec: float = DEFAULT_TIMEOUT_SEC,
) -> Optional[Dict[str, Any]]:
    """
    NAME
        fetch_groups_payload - Fetch the runtime groups JSON payload.
    """
    return fetch_json_command(
        session,
        CMD_SHOW_GROUPS,
        timeout_sec=timeout_sec,
    )


def fetch_json_command_result(
    session: BridgeSession,
    command_name: str,
    *,
    args: Optional[Dict[str, Any]] = None,
    timeout_sec: float = DEFAULT_TIMEOUT_SEC,
) -> tuple[StatusResult, Optional[Dict[str, Any]]]:
    """
    NAME
        fetch_json_command_result - Return a StatusResult plus parsed payload.
    """
    payload = fetch_json_command(
        session,
        command_name,
        args=args,
        timeout_sec=timeout_sec,
    )
    if payload is None:
        return (
            StatusResult(code=SS__NETWORK__ROBOT_UNAVAILABLE, message=MSG_FETCH_FAILED),
            None,
        )
    return (StatusResult(code=0, message="OK"), payload)
