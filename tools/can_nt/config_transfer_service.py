from __future__ import annotations

"""
NAME
    config_transfer_service.py - Shared config push/download workflows.

SYNOPSIS
    from tools.can_nt.config_transfer_service import push_config

DESCRIPTION
    Owns host-side bringup_system.json transfer workflows so bridge_ops can
    stay focused on public command wrappers while transfer semantics live in a
    narrower shared service.
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from tools.can_nt.bridge_session import BridgeEvent, BridgeSession
from tools.can_nt.runtime_query_service import fetch_groups_payload
from tools.can_nt.status import (
    SS__CONFIG__INVALID,
    SS__CONFIG__PROFILE_REQUIRED,
    SS__CONFIG__SAVED,
    SS__NETWORK__ROBOT_UNAVAILABLE,
    StatusResult,
)
from tools.common.json_io import write_json
from tools.common.profile_constants import KEY_DATA_HASH, KEY_DATA_VERSION, KEY_DEVICES, KEY_NAME, KEY_PROFILES
from tools.common.profile_io import compute_profiles_hash, validate_profiles_schema
from tools.common.profile_constants import PROFILE_SCHEMA_VERSION

CMD_GROUP_DELETE = "groupDelete"
CMD_PROFILES_APPLY = "profilesApply"
CMD_SELECT_PROFILE = "selectProfile"
ENCODING_UTF8 = "utf-8"
EVENT_STATUS_OK = "ok"
KEY_GROUPS = "groups"
MSG_DOWNLOAD_FETCH_FAILED = "Failed to fetch current config from robot."
MSG_DOWNLOAD_WRITE_FAILED = "Failed to write config file: {path}"
MSG_OK = "OK"
MSG_PROFILE_REQUIRED = "Profile not selected."
MSG_PUSH_APPLY_FAILED = "Robot rejected config push."
MSG_PUSH_DATA_HASH = "Config data_hash is required."
MSG_PUSH_DATA_HASH_MISMATCH = "Config data_hash does not match computed profiles hash."
MSG_PUSH_DATA_VERSION = "Config data_version is required."
MSG_PUSH_DEVICES_MISSING = "Config devices[] is required."
MSG_PUSH_GROUP_QUERY_FAILED = "Failed to fetch robot groups."
MSG_PUSH_OK = "Config pushed to robot."
MSG_PUSH_PARSE_FAILED = "Failed to parse config file: {detail}"
MSG_PUSH_PARSE_ROOT = "Config root must be a JSON object."
MSG_PUSH_PATH_REQUIRED = "Config path required."
MSG_PUSH_PROFILE_UNKNOWN = "Selected profile not found in config: {profile}"
MSG_PUSH_PROFILES_EMPTY = "Config profiles[] is required."
MSG_PUSH_READ_FAILED = "Failed to read config file: {path}"
MSG_PUSH_TIMEOUT = "Timed out waiting for robot command output."
PUSH_EVENT_SLEEP_SEC = 0.02
PUSH_TIMEOUT_SEC = 10.0
PUSH_STAGE_LOAD = "load local config"
PUSH_STAGE_VALIDATE = "validate local config"
PUSH_STAGE_UPLOAD = "upload registry"
PUSH_STAGE_SELECT_PROFILE = "select profile"
PUSH_STAGE_CLEAR_GROUPS = "clear robot groups"
PUSH_STAGE_IMPORT_GROUPS = "import groups and bindings"
PUSH_STAGE_COMPLETE = "complete"
PAYLOAD_KEY_APPLY = "apply"
PAYLOAD_KEY_ACTIVE_PROFILE = "activeProfile"
PAYLOAD_KEY_PUSH_STAGES = "pushStages"


def _emit_status(status_callback: Optional[Callable[[str], None]], message: str) -> None:
    """
    NAME
        _emit_status - Forward one progress message when a callback is present.
    """
    if status_callback is None:
        return
    status_callback(message)


def wait_for_command_event(
    session: BridgeSession,
    seq: Optional[int],
    timeout_sec: float = PUSH_TIMEOUT_SEC,
) -> Optional[BridgeEvent]:
    """
    NAME
        wait_for_command_event - Wait for the terminal OUT event for one command sequence.
    """
    if seq is None:
        return None
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        events = session.poll_events()
        if not events:
            time.sleep(PUSH_EVENT_SLEEP_SEC)
            continue
        for event in events:
            if event.seq == seq and event.type == "out":
                return event
    return None


def event_succeeded(event: Optional[BridgeEvent]) -> bool:
    """
    NAME
        event_succeeded - Return whether a command OUT event completed successfully.
    """
    return event is not None and str(event.status).strip().lower() == EVENT_STATUS_OK


def read_registry_raw(path: str) -> Tuple[bool, str, str, Optional[Dict[str, Any]]]:
    """
    NAME
        read_registry_raw - Load raw bringup_system.json text and parse it.
    """
    if not path:
        return (False, MSG_PUSH_PATH_REQUIRED, "", None)
    source_path = Path(path)
    try:
        raw = source_path.read_text(encoding=ENCODING_UTF8)
    except Exception:
        return (False, MSG_PUSH_READ_FAILED.format(path=path), "", None)
    try:
        payload = json.loads(raw)
    except Exception as exc:
        return (False, MSG_PUSH_PARSE_FAILED.format(detail=exc), raw, None)
    if not isinstance(payload, dict):
        return (False, MSG_PUSH_PARSE_ROOT, raw, None)
    return (True, "", raw, payload)


def hash_raw_registry(raw: str) -> str:
    """
    NAME
        hash_raw_registry - Compute SHA-256 for raw registry JSON text.
    """
    return hashlib.sha256(raw.encode(ENCODING_UTF8)).hexdigest()


def validate_registry_payload(
    payload: Dict[str, Any],
    profile_name: str,
) -> Tuple[bool, str]:
    """
    NAME
        validate_registry_payload - Validate the bringup_system.json payload for push.
    """
    ok, message = validate_profiles_schema(payload, PROFILE_SCHEMA_VERSION)
    if not ok:
        return (False, message)
    data_version = payload.get(KEY_DATA_VERSION)
    if not isinstance(data_version, str) or not data_version.strip():
        return (False, MSG_PUSH_DATA_VERSION)
    data_hash = payload.get(KEY_DATA_HASH)
    if not isinstance(data_hash, str) or not data_hash.strip():
        return (False, MSG_PUSH_DATA_HASH)
    if data_hash != compute_profiles_hash(payload):
        return (False, MSG_PUSH_DATA_HASH_MISMATCH)
    devices_raw = payload.get(KEY_DEVICES)
    if not isinstance(devices_raw, list) or not devices_raw:
        return (False, MSG_PUSH_DEVICES_MISSING)
    profiles = payload.get(KEY_PROFILES)
    if not isinstance(profiles, dict) or not profiles:
        return (False, MSG_PUSH_PROFILES_EMPTY)
    if profile_name and profile_name not in profiles:
        return (False, MSG_PUSH_PROFILE_UNKNOWN.format(profile=profile_name))
    return (True, MSG_OK)


def clear_existing_groups_remote(session: BridgeSession) -> Tuple[bool, str]:
    """
    NAME
        clear_existing_groups_remote - Delete all current runtime groups on the robot.
    """
    groups_payload = fetch_groups_payload(session, timeout_sec=PUSH_TIMEOUT_SEC)
    groups = groups_payload.get(KEY_GROUPS) if isinstance(groups_payload, dict) else None
    if not isinstance(groups, list):
        return (False, MSG_PUSH_GROUP_QUERY_FAILED)
    for group in groups:
        if not isinstance(group, dict):
            continue
        name = str(group.get(KEY_NAME, "")).strip()
        if not name:
            continue
        seq = session.send_command(CMD_GROUP_DELETE, {KEY_NAME: name, "confirm": True})
        event = wait_for_command_event(session, seq)
        if not event_succeeded(event):
            return (False, event.message if event is not None else MSG_PUSH_TIMEOUT)
    return (True, MSG_OK)


def push_config(
    session: BridgeSession,
    path: str,
    profile_name: str,
    conflict_policy: str,
    *,
    plan_loader: Callable[[str, str, Optional[str]], Any],
    status_callback: Optional[Callable[[str], None]] = None,
) -> StatusResult:
    """
    NAME
        push_config - Push a full bringup_system.json payload plus profile groups to the robot.
    """
    if not profile_name:
        return StatusResult(code=SS__CONFIG__PROFILE_REQUIRED, message=MSG_PROFILE_REQUIRED)
    _emit_status(status_callback, f"Push Config: {PUSH_STAGE_LOAD}")
    ok, error, raw, payload = read_registry_raw(path)
    if not ok or payload is None:
        return StatusResult(code=SS__CONFIG__INVALID, message=error or MSG_PUSH_PARSE_ROOT)
    _emit_status(status_callback, f"Push Config: {PUSH_STAGE_VALIDATE}")
    valid, message = validate_registry_payload(payload, profile_name)
    if not valid:
        return StatusResult(code=SS__CONFIG__INVALID, message=message)
    registry_hash = hash_raw_registry(raw)
    registry_bytes = len(raw.encode(ENCODING_UTF8))
    args = {
        "registryJson": raw,
        "registryHash": registry_hash,
        "registryBytes": registry_bytes,
    }
    _emit_status(status_callback, f"Push Config: {PUSH_STAGE_UPLOAD}")
    event = wait_for_command_event(
        session,
        session.send_command(CMD_PROFILES_APPLY, args),
    )
    if event is None:
        return StatusResult(code=SS__NETWORK__ROBOT_UNAVAILABLE, message=MSG_PUSH_TIMEOUT)
    apply_payload = None
    if event.json_text:
        try:
            apply_payload = json.loads(event.json_text)
        except Exception:
            apply_payload = None
    if not event_succeeded(event):
        return StatusResult(code=SS__CONFIG__INVALID, message=event.message or MSG_PUSH_APPLY_FAILED)
    _emit_status(status_callback, f"Push Config: {PUSH_STAGE_SELECT_PROFILE}")
    select_event = wait_for_command_event(
        session,
        session.send_command(CMD_SELECT_PROFILE, {KEY_NAME: profile_name}),
    )
    if not event_succeeded(select_event):
        return StatusResult(
            code=SS__NETWORK__ROBOT_UNAVAILABLE,
            message=(select_event.message if select_event is not None else MSG_PUSH_TIMEOUT),
        )
    _emit_status(status_callback, f"Push Config: {PUSH_STAGE_CLEAR_GROUPS}")
    cleared, clear_message = clear_existing_groups_remote(session)
    if not cleared:
        return StatusResult(code=SS__NETWORK__ROBOT_UNAVAILABLE, message=clear_message)
    _emit_status(status_callback, f"Push Config: {PUSH_STAGE_IMPORT_GROUPS}")
    plan = plan_loader(path, conflict_policy, profile_name)
    if not getattr(plan, "ok", False):
        return StatusResult(code=SS__CONFIG__INVALID, message=str(getattr(plan, "message", MSG_PUSH_APPLY_FAILED)))
    for command in getattr(plan, "commands", []):
        event = wait_for_command_event(
            session,
            session.send_command(command.name, command.args),
        )
        if not event_succeeded(event):
            return StatusResult(
                code=SS__NETWORK__ROBOT_UNAVAILABLE,
                message=(event.message if event is not None else MSG_PUSH_TIMEOUT),
            )
    result_message = MSG_PUSH_OK
    if isinstance(apply_payload, dict):
        result_message = str(apply_payload.get("message", MSG_PUSH_OK))
    _emit_status(status_callback, f"Push Config: {PUSH_STAGE_COMPLETE}")
    return StatusResult(
        code=SS__CONFIG__SAVED,
        message=result_message,
        payload={
            PAYLOAD_KEY_APPLY: apply_payload if isinstance(apply_payload, dict) else {},
            PAYLOAD_KEY_ACTIVE_PROFILE: profile_name,
            PAYLOAD_KEY_PUSH_STAGES: [
                PUSH_STAGE_LOAD,
                PUSH_STAGE_VALIDATE,
                PUSH_STAGE_UPLOAD,
                PUSH_STAGE_SELECT_PROFILE,
                PUSH_STAGE_CLEAR_GROUPS,
                PUSH_STAGE_IMPORT_GROUPS,
                PUSH_STAGE_COMPLETE,
            ],
        },
    )


def download_current_config(session: BridgeSession, path: str) -> StatusResult:
    """
    NAME
        download_current_config - Download the robot's current bringup_system.json to disk.
    """
    if not path:
        return StatusResult(code=SS__CONFIG__INVALID, message=MSG_PUSH_PATH_REQUIRED)
    payload = session.fetch_current_config()
    if not isinstance(payload, dict):
        return StatusResult(code=SS__NETWORK__ROBOT_UNAVAILABLE, message=MSG_DOWNLOAD_FETCH_FAILED)
    try:
        write_json(Path(path), payload, indent=2, trailing_newline=True)
    except Exception:
        return StatusResult(code=SS__CONFIG__INVALID, message=MSG_DOWNLOAD_WRITE_FAILED.format(path=path))
    return StatusResult(code=SS__CONFIG__SAVED, message=f"Wrote current robot config to {path}.")
