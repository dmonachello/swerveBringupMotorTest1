from __future__ import annotations

"""
NAME
    bridge_ops.py - Shared operations for bridge GUI/CLI.

SYNOPSIS
    from tools.can_nt.bridge_ops import show_groups

DESCRIPTION
    Provides shared bridge operations for CLI/GUI, including command wrappers
    and local config import/export planning. GUI and CLI should call these
    operations instead of constructing commands directly.
"""

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tools.can_nt.bridge_session import BridgeSession
from tools.can_nt.status import (
    StatusResult,
    SS__CONFIG__INVALID,
    SS__CONFIG__PROFILE_REQUIRED,
    SS__CONFIG__SAVED,
    SS__NETWORK__ROBOT_UNAVAILABLE,
)
from tools.common.json_io import read_json, write_json
from tools.common.profile_constants import (
    BRIDGE_CONFIG_SCHEMA_VERSION,
    KEY_ATTACHMENTS,
    KEY_BRIDGE_CONFIG,
    KEY_BRIDGE_BY_PROFILE,
    KEY_BRIDGE_BINDINGS,
    KEY_BRIDGE_GENERATED_AT,
    KEY_BRIDGE_GROUPS,
    KEY_BRIDGE_SCHEMA_VERSION,
    KEY_BRIDGE_SELECTED_DEVICE,
    KEY_BRIDGE_TESTS,
    KEY_BUS,
    KEY_DEFAULT_PROFILE,
    KEY_DEVICES,
    KEY_DEVICE,
    KEY_LABEL,
    KEY_INTERFACE,
    KEY_MANUFACTURER,
    KEY_DEVICE_TYPE,
    KEY_ID,
    KEY_DIO,
    KEY_INVERT,
    KEY_PWM,
    KEY_ANALOG,
    KEY_LIMITS,
    KEY_NOTES,
    KEY_PROFILES,
    KEY_PROFILE_DEVICES,
    KEY_PROFILE,
    KEY_ROLE,
    KEY_TAGS,
    KEY_TYPE,
    KEY_VENDOR,
    INTERFACE_ANALOG,
    INTERFACE_CAN,
    INTERFACE_DIO,
    INTERFACE_INTERNAL,
    INTERFACE_PWM,
)
from tools.common.profile_io import validate_profiles_schema

CONFIG_SCHEMA_VERSION = BRIDGE_CONFIG_SCHEMA_VERSION
SEP_COMMA_SPACE = ", "
SEP_NEWLINE = "\n"
MSG_OK = "OK"
CMD_SHOW_VERSION = "showVersion"
MSG_DUPLICATE_DEVICE_NAMES = "Duplicate device names: {names}"
MSG_MISSING_DEVICE_ENTRIES = "Missing device entries: {names}"
MSG_MISSING_DEVICE_GROUP_HEADER = "Missing device references by group:"
MSG_MISSING_DEVICE_GROUP_LINE = "  profile={profile} group={group}: {devices}"
MSG_LEGACY_GROUPS = "Legacy bridgeConfig.groups is not supported. Use per-profile bridgeConfig.byProfile."
MSG_LEGACY_SELECTED_DEVICE = (
    "Legacy bridgeConfig.selectedDevice is not supported. Use per-profile bridgeConfig.byProfile."
)
MSG_MISSING_BY_PROFILE = "bridgeConfig.byProfile is required for schemaVersion 2."
MSG_MISSING_PROFILES = "Profiles payload is required for per-profile bridgeConfig."
MSG_UNKNOWN_PROFILE = "bridgeConfig.byProfile references unknown profile: {name}"
MSG_DUPLICATE_PROFILE_LABEL_HEADER = "Duplicate device labels by profile:"
MSG_DUPLICATE_PROFILE_LABEL_LINE = "  {profile}: {labels}"
MSG_PROFILE_REQUIRED = "Profile not selected."
MSG_DEVICE_DEF_HEADER = "Invalid device definitions:"
MSG_DEVICE_DEF_LINE = "  {label}: {issues}"
MSG_DEVICE_DEF_LABEL_REQUIRED = "label required"
MSG_DEVICE_DEF_LABEL_DUPLICATE = "duplicate label"
MSG_DEVICE_DEF_INTERFACE_REQUIRED = "interface required"
MSG_DEVICE_DEF_INTERFACE_INVALID = "interface invalid"
MSG_DEVICE_DEF_MANUFACTURER_REQUIRED = "manufacturer required"
MSG_DEVICE_DEF_DEVICE_TYPE_REQUIRED = "deviceType required"
MSG_DEVICE_DEF_ID_REQUIRED = "id required"
MSG_DEVICE_DEF_DIO_REQUIRED = "dio required"
MSG_DEVICE_DEF_INVERT_REQUIRED = "invert required"
MSG_DEVICE_DEF_PWM_REQUIRED = "pwm required"
MSG_DEVICE_DEF_ANALOG_REQUIRED = "analog required"
MSG_DEVICE_DEF_MANUFACTURER_TYPE = "manufacturer must be int"
MSG_DEVICE_DEF_DEVICE_TYPE_TYPE = "deviceType must be int"
MSG_DEVICE_DEF_ID_TYPE = "id must be int"
MSG_DEVICE_DEF_DIO_TYPE = "dio must be int"
MSG_DEVICE_DEF_INVERT_TYPE = "invert must be bool"
MSG_DEVICE_DEF_PWM_TYPE = "pwm must be int"
MSG_DEVICE_DEF_ANALOG_TYPE = "analog must be int"
MSG_DEVICE_DEF_UNNAMED = "(unnamed)"

DEVICE_REQUIRED_CAN = (KEY_MANUFACTURER, KEY_DEVICE_TYPE, KEY_ID)
DEVICE_REQUIRED_DIO = (KEY_DIO, KEY_INVERT)
DEVICE_REQUIRED_PWM = (KEY_PWM,)
DEVICE_REQUIRED_ANALOG = (KEY_ANALOG,)
DEVICE_REQUIRED_INTERNAL = tuple()


@dataclass(frozen=True)
class BridgeCommand:
    """
    NAME
        BridgeCommand - Command name + args for bridge operations.
    """

    name: str
    args: Dict[str, Any]


@dataclass(frozen=True)
class ConfigPlan:
    """
    NAME
        ConfigPlan - Parsed config plan for import/merge.
    """

    ok: bool
    message: str
    commands: List[BridgeCommand]
    replace: bool
    config: Optional[Dict[str, Any]] = None
    root_payload: Optional[Dict[str, Any]] = None
    root_path: Optional[str] = None


# LocalOpResult replaced by StatusResult.


def _send(session: BridgeSession, name: str, args: Optional[Dict[str, Any]] = None) -> Optional[int]:
    """
    NAME
        _send - Send a command through the shared BridgeSession.
    """
    return session.send_command(name, args or {})


def connect(session: BridgeSession) -> bool:
    """
    NAME
        connect - Ensure the TCP session is connected.
    """
    return session.connect()


def disconnect(session: BridgeSession) -> None:
    """
    NAME
        disconnect - Close the TCP session.
    """
    session.disconnect()


def send_command(session: BridgeSession, name: str, args: Optional[Dict[str, Any]] = None) -> Optional[int]:
    """
    NAME
        send_command - Send an arbitrary UI command through BridgeSession.
    """
    return _send(session, name, args)


def ui_handshake(session: BridgeSession, client_id: str, reset: bool) -> Optional[int]:
    """
    NAME
        ui_handshake - Send the UI handshake command.
    """
    return _send(session, "uiHandshake", {"clientId": client_id, "reset": bool(reset)})


def ui_disconnect(session: BridgeSession) -> Optional[int]:
    """
    NAME
        ui_disconnect - Release the UI lock on the robot.
    """
    return _send(session, "uiDisconnect", {})


def ui_monitor(session: BridgeSession, enabled: bool) -> Optional[int]:
    """
    NAME
        ui_monitor - Toggle UI protocol monitor publishing.
    """
    name = "uiMonitorEnable" if enabled else "uiMonitorDisable"
    return _send(session, name, {"enabled": bool(enabled)})


def ui_poll_log(session: BridgeSession) -> Optional[int]:
    """
    NAME
        ui_poll_log - Request UI log polling output.
    """
    return _send(session, "uiPollLog", {})


def ui_ping(session: BridgeSession) -> Optional[int]:
    """
    NAME
        ui_ping - Send a UI keepalive ping.
    """
    return _send(session, "uiPing", {})


def select_test_by_name(session: BridgeSession, name: str) -> Optional[int]:
    """
    NAME
        select_test_by_name - Select a scripted test by name.
    """
    return _send(session, "selectTestByName", {"name": name})

def show_status(session: BridgeSession, json_output: bool = False) -> Optional[int]:
    """
    NAME
        show_status - Request bridge status output.
    """
    return _send(session, "showStatus", _json_arg(json_output))


def show_version(session: BridgeSession, json_output: bool = False) -> Optional[int]:
    """
    NAME
        show_version - Request robot version output.
    """
    return _send(session, CMD_SHOW_VERSION, _json_arg(json_output))


def show_groups(session: BridgeSession, json_output: bool = False) -> Optional[int]:
    """
    NAME
        show_groups - Request group list output.
    """
    return _send(session, "showGroups", _json_arg(json_output))


def show_group(session: BridgeSession, name: str, json_output: bool = False) -> Optional[int]:
    """
    NAME
        show_group - Request details for a single group.
    """
    return _send(session, "showGroup", _json_arg(json_output, name=name))


def show_devices(session: BridgeSession, json_output: bool = False) -> Optional[int]:
    """
    NAME
        show_devices - Request active device list output.
    """
    return _send(session, "showDevices", _json_arg(json_output))


def show_device(session: BridgeSession, name: str, json_output: bool = False) -> Optional[int]:
    """
    NAME
        show_device - Request details for one device by label.
    """
    return _send(session, "showDevice", _json_arg(json_output, name=name))


def show_bindings(session: BridgeSession, json_output: bool = False) -> Optional[int]:
    """
    NAME
        show_bindings - Request binding list output.
    """
    return _send(session, "showBindings", _json_arg(json_output))


def show_selected_device(session: BridgeSession, json_output: bool = False) -> Optional[int]:
    """
    NAME
        show_selected_device - Request selected-device state output.
    """
    return _send(session, "showSelectedDevice", _json_arg(json_output))


def show_runtime_state(session: BridgeSession, json_output: bool = False) -> Optional[int]:
    """
    NAME
        show_runtime_state - Request runtime-state output.
    """
    return _send(session, "showRuntimeState", _json_arg(json_output))


def group_create(session: BridgeSession, name: str) -> Optional[int]:
    """
    NAME
        group_create - Create a new group by name.
    """
    return _send(session, "groupCreate", {"name": name})


def group_delete(session: BridgeSession, name: str, confirm: bool) -> Optional[int]:
    """
    NAME
        group_delete - Delete a group (requires confirm flag).
    """
    return _send(session, "groupDelete", {"name": name, "confirm": bool(confirm)})


def selected_device_set(session: BridgeSession, name: str) -> Optional[int]:
    """
    NAME
        selected_device_set - Set the selected device override target.
    """
    return _send(session, "selectedDeviceSet", {"name": name})


def selected_mode_set(session: BridgeSession, enabled: bool) -> Optional[int]:
    """
    NAME
        selected_mode_set - Enable/disable selected-device mode.
    """
    return _send(session, "selectedModeSet", {"enabled": bool(enabled)})


def _bridge_profile_entry(config: Dict[str, Any], profile_name: str) -> Dict[str, Any]:
    """
    NAME
        _bridge_profile_entry - Return per-profile bridgeConfig entry.
    """
    by_profile = config.get(KEY_BRIDGE_BY_PROFILE)
    if not isinstance(by_profile, dict):
        return {}
    entry = by_profile.get(profile_name)
    if isinstance(entry, dict):
        return entry
    return {}


def local_show_data(
    target: str,
    tokens: List[str],
    config: Dict[str, Any],
    profile_name: Optional[str],
    devices: Optional[List[Dict[str, Any]]],
) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    NAME
        local_show_data - Build local show payloads from bridgeConfig.
    """
    if not isinstance(config, dict):
        return (False, "Local config missing or invalid.", {})
    if not profile_name:
        return (False, MSG_PROFILE_REQUIRED, {})
    entry = _bridge_profile_entry(config, profile_name)
    groups = (
        list(entry.get(KEY_BRIDGE_GROUPS, []))
        if isinstance(entry.get(KEY_BRIDGE_GROUPS), list)
        else []
    )
    selected = (
        entry.get(KEY_BRIDGE_SELECTED_DEVICE)
        if isinstance(entry.get(KEY_BRIDGE_SELECTED_DEVICE), dict)
        else {}
    )
    selected_device = str(selected.get(KEY_DEVICE, "")).strip()
    selected_enabled = bool(selected.get("enabled", False))

    if target == "status":
        payload = {
            "source": "local",
            "groupCount": len(groups),
            "selectedDevice": {"device": selected_device, "enabled": selected_enabled},
        }
        return (True, None, payload)

    if target == "groups":
        return (
            True,
            None,
            {"source": "local", "groups": groups, KEY_PROFILE: profile_name},
        )

    if target == "group":
        name = tokens[1] if len(tokens) >= 2 else ""
        match = None
        for group in groups:
            if not isinstance(group, dict):
                continue
            if str(group.get("name", "")).strip().lower() == name.lower():
                match = group
                break
        if match is None:
            return (False, "Local group not found.", {})
        return (True, None, {"source": "local", "group": match})

    if target == "devices":
        if isinstance(devices, list) and devices:
            return (
                True,
                None,
                {"source": "local", "devices": devices, KEY_PROFILE: profile_name},
            )
        devices_list: List[str] = []
        for group in groups:
            if not isinstance(group, dict):
                continue
            for member in group.get("members", []) or []:
                if isinstance(member, dict):
                    name = str(member.get("device", "")).strip()
                else:
                    name = str(member).strip()
                if name and name not in devices_list:
                    devices_list.append(name)
        if selected_device and selected_device not in devices_list:
            devices_list.append(selected_device)
        return (
            True,
            None,
            {"source": "local", "devices": devices_list, KEY_PROFILE: profile_name},
        )

    if target == "device-group":
        name = tokens[1] if len(tokens) >= 2 else ""
        if isinstance(devices, list):
            for device in devices:
                if not isinstance(device, dict):
                    continue
                device_name = str(device.get("name", "")).strip()
                if device_name.lower() != name.lower():
                    continue
                group_name = ""
                enabled = None
                for group in groups:
                    if not isinstance(group, dict):
                        continue
                    for member in group.get("members", []) or []:
                        if isinstance(member, dict):
                            member_name = str(member.get("device", "")).strip()
                            if member_name.lower() == name.lower():
                                group_name = str(group.get("name", ""))
                                enabled = bool(member.get("enabled", True))
                                break
                        else:
                            if str(member).strip().lower() == name.lower():
                                group_name = str(group.get("name", ""))
                                enabled = True
                                break
                    if group_name:
                        break
                return (
                    True,
                    None,
                    {"source": "local", "device": device, "group": group_name, "enabled": enabled},
                )
        found_group = ""
        enabled = None
        for group in groups:
            if not isinstance(group, dict):
                continue
            for member in group.get("members", []) or []:
                if isinstance(member, dict):
                    device_name = str(member.get("device", "")).strip()
                    if device_name.lower() == name.lower():
                        found_group = str(group.get("name", ""))
                        enabled = bool(member.get("enabled", True))
                        break
                else:
                    if str(member).strip().lower() == name.lower():
                        found_group = str(group.get("name", ""))
                        enabled = True
                        break
            if found_group:
                break
        if not found_group:
            return (False, "Local device not found.", {})
        return (True, None, {"source": "local", "device": name, "group": found_group, "enabled": enabled})

    if target == "bindings":
        return (True, None, {"source": "local", "groups": groups})

    if target == "selected-device":
        return (
            True,
            None,
            {"source": "local", "selectedDevice": {"device": selected_device, "enabled": selected_enabled}},
        )

    if target == "runtime-state":
        devices = devices if isinstance(devices, list) else None
        payload = {
            "source": "local",
            "schemaVersion": config.get(KEY_BRIDGE_SCHEMA_VERSION, CONFIG_SCHEMA_VERSION),
            "generatedAt": config.get(KEY_BRIDGE_GENERATED_AT),
            "groups": groups,
            "selectedDevice": {"device": selected_device, "enabled": selected_enabled},
            "devices": devices if isinstance(devices, list) else None,
            KEY_PROFILE: profile_name,
        }
        return (True, None, payload)

    return (False, "Unknown show command.", {})

def merge_config(
    path: str, conflict_policy: str = "error", profile_name: Optional[str] = None
) -> ConfigPlan:
    """
    NAME
        merge_config - Load a config file and build merge commands.
    """
    config, root_payload, error = _read_bridge_config(path)
    if config is None:
        message = error or f"Invalid config: {path}"
        return ConfigPlan(False, message, [], False, None)
    selected_profile = _select_profile_name(profile_name, root_payload, config)
    commands = _build_commands_from_config(config, conflict_policy, selected_profile)
    count = _count_groups_for_profile(config, selected_profile)
    profile_label = selected_profile or "(none)"
    return ConfigPlan(
        True,
        f"Loaded {count} group(s) for profile {profile_label} from {path}.",
        commands,
        False,
        config,
        root_payload,
        path if root_payload is not None else None,
    )


def import_config(
    path: str, conflict_policy: str = "error", profile_name: Optional[str] = None
) -> ConfigPlan:
    """
    NAME
        import_config - Load a config file and build replace commands.
    """
    config, root_payload, error = _read_bridge_config(path)
    if config is None:
        message = error or f"Invalid config: {path}"
        return ConfigPlan(False, message, [], True, None)
    selected_profile = _select_profile_name(profile_name, root_payload, config)
    commands = _build_commands_from_config(config, conflict_policy, selected_profile)
    count = _count_groups_for_profile(config, selected_profile)
    profile_label = selected_profile or "(none)"
    return ConfigPlan(
        True,
        f"Loaded {count} group(s) for profile {profile_label} from {path}.",
        commands,
        True,
        config,
        root_payload,
        path if root_payload is not None else None,
    )


def export_runtime_groups(
    session: BridgeSession, path: str, profile_name: Optional[str]
) -> StatusResult:
    """
    NAME
        export_runtime_groups - Export runtime groups to a bridgeConfig file.
    """
    if not profile_name:
        return StatusResult(code=SS__CONFIG__PROFILE_REQUIRED, message=MSG_PROFILE_REQUIRED)
    state = _fetch_runtime_state_json(session)
    if state is None:
        return StatusResult(code=SS__NETWORK__ROBOT_UNAVAILABLE, message="Failed to fetch runtime state.")
    config = _config_from_runtime_state(state, profile_name)
    try:
        write_json(Path(path), config, indent=2, trailing_newline=True)
    except Exception as exc:
        return StatusResult(code=SS__CONFIG__INVALID, message=f"Failed to write {path}: {exc}")
    return StatusResult(code=SS__CONFIG__SAVED, message=f"Wrote bridgeConfig to {path}.")


def save_config(session: BridgeSession, path: str, profile_name: Optional[str]) -> StatusResult:
    """
    NAME
        save_config - Save current runtime config to a bridgeConfig file.
    """
    if not profile_name:
        return StatusResult(code=SS__CONFIG__PROFILE_REQUIRED, message=MSG_PROFILE_REQUIRED)
    state = _fetch_runtime_state_json(session)
    if state is None:
        return StatusResult(code=SS__NETWORK__ROBOT_UNAVAILABLE, message="Failed to fetch runtime state.")
    config = _config_from_runtime_state(state, profile_name)
    try:
        write_json(Path(path), config, indent=2, trailing_newline=True)
    except Exception as exc:
        return StatusResult(code=SS__CONFIG__INVALID, message=f"Failed to write {path}: {exc}")
    return StatusResult(code=SS__CONFIG__SAVED, message=f"Wrote bridgeConfig to {path}.")


def group_add_device(
    session: BridgeSession,
    group: str,
    device: str,
    conflict_policy: str,
    force_move: bool = False,
) -> Optional[int]:
    """
    NAME
        group_add_device - Add a device to a group with conflict policy.
    """
    return _send(
        session,
        "groupAddDevice",
        {
            "group": group,
            "device": device,
            "conflictPolicy": conflict_policy,
            "forceMove": bool(force_move),
        },
    )


def group_remove_device(session: BridgeSession, group: str, device: str) -> Optional[int]:
    """
    NAME
        group_remove_device - Remove a device from a group.
    """
    return _send(session, "groupRemoveDevice", {"group": group, "device": device})


def group_member_enable(session: BridgeSession, group: str, device: str) -> Optional[int]:
    """
    NAME
        group_member_enable - Enable a device member in a group.
    """
    return _send(session, "groupMemberEnable", {"group": group, "device": device})


def group_member_disable(session: BridgeSession, group: str, device: str) -> Optional[int]:
    """
    NAME
        group_member_disable - Disable a device member in a group.
    """
    return _send(session, "groupMemberDisable", {"group": group, "device": device})


def group_member_toggle(session: BridgeSession, group: str, device: str) -> Optional[int]:
    """
    NAME
        group_member_toggle - Toggle a device member enabled state.
    """
    return _send(session, "groupMemberToggle", {"group": group, "device": device})


def group_bind(
    session: BridgeSession,
    group: str,
    input_name: str,
    kind: str,
    value: Optional[float] = None,
) -> Optional[int]:
    """
    NAME
        group_bind - Add a binding to a group.
    """
    args: Dict[str, Any] = {"group": group, "input": input_name, "kind": kind}
    if value is not None:
        args["value"] = value
    return _send(session, "groupBind", args)


def group_unbind(session: BridgeSession, group: str) -> Optional[int]:
    """
    NAME
        group_unbind - Clear all bindings from a group.
    """
    return _send(session, "groupUnbind", {"group": group})


def group_enable(session: BridgeSession, group: str) -> Optional[int]:
    """
    NAME
        group_enable - Enable a group.
    """
    return _send(session, "groupEnable", {"group": group})


def group_disable(session: BridgeSession, group: str) -> Optional[int]:
    """
    NAME
        group_disable - Disable a group.
    """
    return _send(session, "groupDisable", {"group": group})


def group_run_test(session: BridgeSession, group: str, name: Optional[str] = None) -> Optional[int]:
    """
    NAME
        group_run_test - Run a named test within a group context.
    """
    args: Dict[str, Any] = {"group": group}
    if name:
        args["name"] = name
    return _send(session, "groupRunTest", args)


def _json_arg(json_output: bool, **extra: Any) -> Dict[str, Any]:
    """
    NAME
        _json_arg - Build args payload with optional json flag.
    """
    args = dict(extra)
    if json_output:
        args["json"] = True
    return args


def parse_json_arg(raw: str) -> Optional[Any]:
    """
    NAME
        parse_json_arg - Parse a JSON string into Python objects.
    """
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def _read_bridge_config(
    path: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[str]]:
    """
    NAME
        _read_bridge_config - Load and normalize bridge config from a profiles file.
    """
    if not path:
        return (None, None, None)
    try:
        payload = read_json(Path(path))
    except Exception:
        return (None, None, None)
    if not isinstance(payload, dict):
        return (None, None, None)
    if "schema_version" in payload and "profiles" in payload:
        bridge = payload.get(KEY_BRIDGE_CONFIG) or {}
        if not isinstance(bridge, dict):
            return (None, payload, None)
        config, error = _normalize_bridge_config(bridge, allow_empty=True, profiles_payload=payload)
        if config is None:
            return (None, payload, error)
        return (config, payload, None)
    config, error = _normalize_bridge_config(payload, allow_empty=False, profiles_payload=None)
    if config is None:
        return (None, None, error)
    return (config, None, None)


def _normalize_bridge_config(
    payload: Dict[str, Any],
    allow_empty: bool,
    profiles_payload: Optional[Dict[str, Any]],
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    NAME
        _normalize_bridge_config - Normalize bridge config fields to a stable schema.
    """
    version_raw = payload.get(KEY_BRIDGE_SCHEMA_VERSION, CONFIG_SCHEMA_VERSION)
    try:
        version = int(version_raw)
    except Exception:
        return (None, None)
    if version != CONFIG_SCHEMA_VERSION:
        return (None, None)
    if KEY_BRIDGE_GROUPS in payload:
        return (None, MSG_LEGACY_GROUPS)
    if KEY_BRIDGE_SELECTED_DEVICE in payload:
        return (None, MSG_LEGACY_SELECTED_DEVICE)
    by_profile = payload.get(KEY_BRIDGE_BY_PROFILE)
    if not isinstance(by_profile, dict):
        if allow_empty:
            by_profile = {}
        else:
            return (None, MSG_MISSING_BY_PROFILE)
    profiles = None
    if profiles_payload is not None:
        profiles = profiles_payload.get(KEY_PROFILES)
        if not isinstance(profiles, dict):
            profiles = None
    generated_at = payload.get(KEY_BRIDGE_GENERATED_AT)
    normalized: Dict[str, Dict[str, Any]] = {}
    for name, entry in by_profile.items():
        if not isinstance(name, str) or not name:
            continue
        if profiles is not None and name not in profiles:
            return (None, MSG_UNKNOWN_PROFILE.format(name=name))
        if not isinstance(entry, dict):
            continue
        groups_raw = entry.get(KEY_BRIDGE_GROUPS)
        if not isinstance(groups_raw, list):
            groups_raw = []
        groups: List[Dict[str, Any]] = []
        for group in groups_raw:
            if not isinstance(group, dict):
                continue
            name_field = str(group.get("name", "")).strip()
            if not name_field:
                continue
            enabled = bool(group.get("enabled", True))
            members: List[Dict[str, Any]] = []
            for member in group.get("members", []) or []:
                if isinstance(member, str):
                    members.append({KEY_DEVICE: member, "enabled": True})
                    continue
                if not isinstance(member, dict):
                    continue
                device = str(member.get(KEY_DEVICE, "")).strip()
                if not device:
                    continue
                members.append({KEY_DEVICE: device, "enabled": bool(member.get("enabled", True))})
            bindings: List[Dict[str, Any]] = []
            for binding in group.get(KEY_BRIDGE_BINDINGS, []) or []:
                if not isinstance(binding, dict):
                    continue
                input_name = str(binding.get("input", "")).strip()
                kind = str(binding.get("kind", "")).strip()
                if not input_name or not kind:
                    continue
                entry_out: Dict[str, Any] = {"input": input_name, "kind": kind}
                if "value" in binding:
                    entry_out["value"] = binding.get("value")
                bindings.append(entry_out)
            groups.append(
                {
                    "name": name_field,
                    "enabled": enabled,
                    "members": members,
                    KEY_BRIDGE_BINDINGS: bindings,
                }
            )
        selected = entry.get(KEY_BRIDGE_SELECTED_DEVICE, {}) or {}
        selected_device = ""
        selected_enabled = False
        if isinstance(selected, dict):
            selected_device = str(selected.get(KEY_DEVICE, "")).strip()
            selected_enabled = bool(selected.get("enabled", False))
        tests = entry.get(KEY_BRIDGE_TESTS)
        if not isinstance(tests, dict):
            tests = None
        normalized[name] = {
            KEY_BRIDGE_GROUPS: groups,
            KEY_BRIDGE_SELECTED_DEVICE: {
                KEY_DEVICE: selected_device,
                "enabled": selected_enabled,
            },
        }
        if tests is not None:
            normalized[name][KEY_BRIDGE_TESTS] = tests
    return (
        {
            KEY_BRIDGE_SCHEMA_VERSION: version,
            KEY_BRIDGE_GENERATED_AT: generated_at,
            KEY_BRIDGE_BY_PROFILE: normalized,
        },
        None,
    )


def _build_commands_from_config(
    config: Dict[str, Any],
    conflict_policy: str,
    profile_name: Optional[str],
) -> List[BridgeCommand]:
    """
    NAME
        _build_commands_from_config - Convert config entries into commands.
    """
    commands: List[BridgeCommand] = []
    if not profile_name:
        return commands
    entry = _bridge_profile_entry(config, profile_name)
    groups = entry.get(KEY_BRIDGE_GROUPS) or []
    for group in groups:
        name = str(group.get("name", "")).strip()
        if not name:
            continue
        commands.append(BridgeCommand("groupCreate", {"name": name}))
        for member in group.get("members", []) or []:
            device = str(member.get("device", "")).strip()
            if not device:
                continue
            commands.append(
                BridgeCommand(
                    "groupAddDevice",
                    {
                        "group": name,
                        "device": device,
                        "conflictPolicy": conflict_policy,
                        "forceMove": False,
                    },
                )
            )
            if member.get("enabled") is False:
                commands.append(
                    BridgeCommand(
                        "groupMemberDisable",
                        {"group": name, "device": device},
                    )
                )
        for binding in group.get(KEY_BRIDGE_BINDINGS, []) or []:
            input_name = str(binding.get("input", "")).strip()
            kind = str(binding.get("kind", "")).strip()
            if not input_name or not kind:
                continue
            args: Dict[str, Any] = {"group": name, "input": input_name, "kind": kind}
            if "value" in binding:
                args["value"] = binding.get("value")
            commands.append(BridgeCommand("groupBind", args))
        if group.get("enabled") is False:
            commands.append(BridgeCommand("groupDisable", {"group": name}))
    selected = entry.get(KEY_BRIDGE_SELECTED_DEVICE) or {}
    if isinstance(selected, dict):
        device = str(selected.get(KEY_DEVICE, "")).strip()
        enabled = bool(selected.get("enabled", False))
        if device:
            commands.append(BridgeCommand("selectedDeviceSet", {"name": device}))
            commands.append(BridgeCommand("selectedModeSet", {"enabled": enabled}))
    return commands


def _select_profile_name(
    profile_name: Optional[str],
    root_payload: Optional[Dict[str, Any]],
    config: Dict[str, Any],
) -> Optional[str]:
    """
    NAME
        _select_profile_name - Choose a profile name for bridgeConfig operations.
    """
    if profile_name:
        return profile_name
    if root_payload is not None:
        profiles = root_payload.get(KEY_PROFILES)
        if isinstance(profiles, dict) and profiles:
            default_profile = root_payload.get(KEY_DEFAULT_PROFILE)
            if isinstance(default_profile, str) and default_profile in profiles:
                return default_profile
            return next(iter(profiles.keys()))
    by_profile = config.get(KEY_BRIDGE_BY_PROFILE)
    if isinstance(by_profile, dict) and by_profile:
        return next(iter(by_profile.keys()))
    return None


def _count_groups_for_profile(config: Dict[str, Any], profile_name: Optional[str]) -> int:
    """
    NAME
        _count_groups_for_profile - Count groups for a selected profile.
    """
    if not profile_name:
        return 0
    entry = _bridge_profile_entry(config, profile_name)
    groups = entry.get(KEY_BRIDGE_GROUPS)
    if isinstance(groups, list):
        return len(groups)
    return 0


def validate_config_file(path: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    NAME
        validate_config_file - Validate a bridgeConfig file and report missing devices.
    """
    config, root_payload, error = _read_bridge_config(path)
    if config is None:
        message = error or f"Invalid config: {path}"
        return (False, message, None)
    if root_payload is None:
        return (False, MSG_MISSING_PROFILES, config)
    duplicates = _find_duplicate_profile_labels(root_payload, config)
    if duplicates:
        return (False, _format_duplicate_profile_labels(duplicates), config)
    missing = _find_missing_device_refs(config, root_payload)
    if missing:
        missing_list = SEP_COMMA_SPACE.join(sorted(missing))
        detail = _describe_missing_device_refs(config, root_payload, missing)
        message = MSG_MISSING_DEVICE_ENTRIES.format(names=missing_list)
        if detail:
            message = SEP_NEWLINE.join([message, detail])
        return (False, message, config)
    return (True, MSG_OK, config)


def validate_config_file_all(path: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    NAME
        validate_config_file_all - Validate config file and report all issues.
    """
    config, root_payload, error = _read_bridge_config(path)
    if config is None:
        message = error or f"Invalid config: {path}"
        return (False, message, None)
    if root_payload is None:
        return (False, MSG_MISSING_PROFILES, config)
    ok, message = validate_config_data_all(config, root_payload)
    return (ok, message, config)


def _find_missing_device_refs(config: Dict[str, Any], root_payload: Dict[str, Any]) -> List[str]:
    """
    NAME
        _find_missing_device_refs - Find group members missing from devices list.
    """
    missing = []
    if not isinstance(config, dict):
        return missing
    by_profile = config.get(KEY_BRIDGE_BY_PROFILE)
    if not isinstance(by_profile, dict):
        return missing
    for profile_name, entry in by_profile.items():
        if not isinstance(entry, dict) or not isinstance(profile_name, str):
            continue
        known = _profile_device_label_set(root_payload, profile_name)
        if known is None:
            continue
        groups = entry.get(KEY_BRIDGE_GROUPS)
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            for member in group.get("members", []) or []:
                if isinstance(member, dict):
                    name = str(member.get(KEY_DEVICE, "")).strip()
                else:
                    name = str(member).strip()
                if name and name.lower() not in known:
                    missing.append(name)
    return missing


def _validate_device_definitions(root_payload: Dict[str, Any]) -> List[str]:
    """
    NAME
        _validate_device_definitions - Validate device registry entries.
    """
    devices = root_payload.get(KEY_DEVICES)
    if not isinstance(devices, list):
        return []
    seen: Dict[str, int] = {}
    errors: List[str] = []
    for entry in devices:
        if not isinstance(entry, dict):
            continue
        label = str(entry.get(KEY_LABEL, "")).strip()
        issues: List[str] = []
        if not label:
            issues.append(MSG_DEVICE_DEF_LABEL_REQUIRED)
        else:
            key = label.lower()
            seen[key] = seen.get(key, 0) + 1
            if seen[key] == 2:
                issues.append(MSG_DEVICE_DEF_LABEL_DUPLICATE)
        interface = str(entry.get(KEY_INTERFACE, "")).strip()
        if not interface:
            issues.append(MSG_DEVICE_DEF_INTERFACE_REQUIRED)
        elif interface not in (
            INTERFACE_CAN,
            INTERFACE_DIO,
            INTERFACE_PWM,
            INTERFACE_ANALOG,
            INTERFACE_INTERNAL,
        ):
            issues.append(MSG_DEVICE_DEF_INTERFACE_INVALID)
        required: tuple[str, ...]
        if interface == INTERFACE_CAN:
            required = DEVICE_REQUIRED_CAN
        elif interface == INTERFACE_DIO:
            required = DEVICE_REQUIRED_DIO
        elif interface == INTERFACE_PWM:
            required = DEVICE_REQUIRED_PWM
        elif interface == INTERFACE_ANALOG:
            required = DEVICE_REQUIRED_ANALOG
        else:
            required = DEVICE_REQUIRED_INTERNAL
        for field in required:
            if entry.get(field) is None:
                if field == KEY_MANUFACTURER:
                    issues.append(MSG_DEVICE_DEF_MANUFACTURER_REQUIRED)
                elif field == KEY_DEVICE_TYPE:
                    issues.append(MSG_DEVICE_DEF_DEVICE_TYPE_REQUIRED)
                elif field == KEY_ID:
                    issues.append(MSG_DEVICE_DEF_ID_REQUIRED)
                elif field == KEY_DIO:
                    issues.append(MSG_DEVICE_DEF_DIO_REQUIRED)
                elif field == KEY_INVERT:
                    issues.append(MSG_DEVICE_DEF_INVERT_REQUIRED)
                elif field == KEY_PWM:
                    issues.append(MSG_DEVICE_DEF_PWM_REQUIRED)
                elif field == KEY_ANALOG:
                    issues.append(MSG_DEVICE_DEF_ANALOG_REQUIRED)
        if interface == INTERFACE_CAN:
            manufacturer = entry.get(KEY_MANUFACTURER)
            device_type = entry.get(KEY_DEVICE_TYPE)
            device_id = entry.get(KEY_ID)
            if manufacturer is not None and not isinstance(manufacturer, int):
                issues.append(MSG_DEVICE_DEF_MANUFACTURER_TYPE)
            if device_type is not None and not isinstance(device_type, int):
                issues.append(MSG_DEVICE_DEF_DEVICE_TYPE_TYPE)
            if device_id is not None and not isinstance(device_id, int):
                issues.append(MSG_DEVICE_DEF_ID_TYPE)
        if interface == INTERFACE_DIO:
            dio = entry.get(KEY_DIO)
            invert = entry.get(KEY_INVERT)
            if dio is not None and not isinstance(dio, int):
                issues.append(MSG_DEVICE_DEF_DIO_TYPE)
            if invert is not None and not isinstance(invert, bool):
                issues.append(MSG_DEVICE_DEF_INVERT_TYPE)
        if interface == INTERFACE_PWM:
            pwm = entry.get(KEY_PWM)
            if pwm is not None and not isinstance(pwm, int):
                issues.append(MSG_DEVICE_DEF_PWM_TYPE)
        if interface == INTERFACE_ANALOG:
            analog = entry.get(KEY_ANALOG)
            if analog is not None and not isinstance(analog, int):
                issues.append(MSG_DEVICE_DEF_ANALOG_TYPE)
        if issues:
            name = label or MSG_DEVICE_DEF_UNNAMED
            errors.append(MSG_DEVICE_DEF_LINE.format(label=name, issues=SEP_COMMA_SPACE.join(issues)))
    if not errors:
        return []
    return [MSG_DEVICE_DEF_HEADER] + errors


def validate_config_data(config: Dict[str, Any], root_payload: Optional[Dict[str, Any]]) -> Tuple[bool, str]:
    """
    NAME
        validate_config_data - Validate an in-memory bridgeConfig.
    """
    if root_payload is None:
        return (False, MSG_MISSING_PROFILES)
    duplicates = _find_duplicate_profile_labels(root_payload, config)
    if duplicates:
        return (False, _format_duplicate_profile_labels(duplicates))
    device_errors = _validate_device_definitions(root_payload)
    if device_errors:
        return (False, SEP_NEWLINE.join(device_errors))
    missing = _find_missing_device_refs(config, root_payload)
    if missing:
        missing_list = SEP_COMMA_SPACE.join(sorted(missing))
        detail = _describe_missing_device_refs(config, root_payload, missing)
        message = MSG_MISSING_DEVICE_ENTRIES.format(names=missing_list)
        if detail:
            message = SEP_NEWLINE.join([message, detail])
        return (False, message)
    return (True, MSG_OK)


def validate_config_data_all(
    config: Dict[str, Any], root_payload: Optional[Dict[str, Any]]
) -> Tuple[bool, str]:
    """
    NAME
        validate_config_data_all - Validate config and report all issues.
    """
    if root_payload is None:
        return (False, MSG_MISSING_PROFILES)
    messages: List[str] = []
    duplicates = _find_duplicate_profile_labels(root_payload, config)
    if duplicates:
        messages.append(_format_duplicate_profile_labels(duplicates))
    device_errors = _validate_device_definitions(root_payload)
    if device_errors:
        messages.append(SEP_NEWLINE.join(device_errors))
    missing = _find_missing_device_refs(config, root_payload)
    if missing:
        missing_list = SEP_COMMA_SPACE.join(sorted(missing))
        detail = _describe_missing_device_refs(config, root_payload, missing)
        message = MSG_MISSING_DEVICE_ENTRIES.format(names=missing_list)
        if detail:
            message = SEP_NEWLINE.join([message, detail])
        messages.append(message)
    if messages:
        return (False, SEP_NEWLINE.join(messages))
    return (True, MSG_OK)


def _describe_missing_device_refs(
    config: Dict[str, Any],
    root_payload: Dict[str, Any],
    missing: List[str],
) -> str:
    """
    NAME
        _describe_missing_device_refs - Map missing device labels to groups.
    """
    if not missing:
        return ""
    missing_set = {name.strip().lower() for name in missing if isinstance(name, str)}
    hits: Dict[tuple[str, str], List[str]] = {}
    by_profile = config.get(KEY_BRIDGE_BY_PROFILE) if isinstance(config, dict) else None
    if not isinstance(by_profile, dict):
        return ""
    for profile_name, entry in by_profile.items():
        if not isinstance(entry, dict) or not isinstance(profile_name, str):
            continue
        groups = entry.get(KEY_BRIDGE_GROUPS)
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            group_name = str(group.get("name", "")).strip()
            if not group_name:
                continue
            for member in group.get("members", []) or []:
                if isinstance(member, dict):
                    name = str(member.get(KEY_DEVICE, "")).strip()
                else:
                    name = str(member).strip()
                if not name:
                    continue
                if name.strip().lower() in missing_set:
                    key = (profile_name, group_name)
                    hits.setdefault(key, []).append(name)
    if not hits:
        return ""
    lines = [MSG_MISSING_DEVICE_GROUP_HEADER]
    for profile_name, group_name in sorted(hits.keys()):
        devices = SEP_COMMA_SPACE.join(sorted(set(hits[(profile_name, group_name)])))
        lines.append(
            MSG_MISSING_DEVICE_GROUP_LINE.format(
                profile=profile_name,
                group=group_name,
                devices=devices,
            )
        )
    return SEP_NEWLINE.join(lines)


def _profile_device_label_set(
    root_payload: Dict[str, Any], profile_name: str
) -> Optional[set[str]]:
    """
    NAME
        _profile_device_label_set - Build a label set for a profile.
    """
    profiles = root_payload.get(KEY_PROFILES)
    if not isinstance(profiles, dict) or not profile_name:
        return None
    profile = profiles.get(profile_name)
    if not isinstance(profile, dict):
        return None
    labels = profile.get(KEY_PROFILE_DEVICES)
    if not isinstance(labels, list):
        return None
    return {str(label).strip().lower() for label in labels if isinstance(label, str) and label}


def _find_duplicate_profile_labels(
    root_payload: Dict[str, Any],
    config: Dict[str, Any],
) -> Dict[str, List[str]]:
    """
    NAME
        _find_duplicate_profile_labels - Find duplicate device labels per profile.
    """
    by_profile = config.get(KEY_BRIDGE_BY_PROFILE) if isinstance(config, dict) else None
    if not isinstance(by_profile, dict):
        return {}
    profiles = root_payload.get(KEY_PROFILES)
    if not isinstance(profiles, dict):
        return {}
    duplicates: Dict[str, List[str]] = {}
    for profile_name in by_profile.keys():
        if not isinstance(profile_name, str):
            continue
        profile = profiles.get(profile_name)
        if not isinstance(profile, dict):
            continue
        labels = profile.get(KEY_PROFILE_DEVICES)
        if not isinstance(labels, list):
            continue
        seen: Dict[str, int] = {}
        dupes: List[str] = []
        for label in labels:
            if not isinstance(label, str):
                continue
            key = label.strip().lower()
            if not key:
                continue
            seen[key] = seen.get(key, 0) + 1
            if seen[key] == 2:
                dupes.append(label.strip())
        if dupes:
            duplicates[profile_name] = sorted(set(dupes))
    return duplicates


def _format_duplicate_profile_labels(duplicates: Dict[str, List[str]]) -> str:
    """
    NAME
        _format_duplicate_profile_labels - Format duplicate label errors.
    """
    if not duplicates:
        return ""
    lines = [MSG_DUPLICATE_PROFILE_LABEL_HEADER]
    for profile_name in sorted(duplicates.keys()):
        labels = SEP_COMMA_SPACE.join(sorted(set(duplicates[profile_name])))
        lines.append(MSG_DUPLICATE_PROFILE_LABEL_LINE.format(profile=profile_name, labels=labels))
    return SEP_NEWLINE.join(lines)


def devices_from_profiles_payload(
    payload: Dict[str, Any],
    profile_name: Optional[str] = None,
) -> Optional[List[Dict[str, Any]]]:
    """
    NAME
        _devices_from_profiles_payload - Build bridgeConfig devices from profiles.
    """
    profiles = payload.get(KEY_PROFILES)
    if not isinstance(profiles, dict) or not profiles:
        return None
    devices_registry = payload.get(KEY_DEVICES)
    if not isinstance(devices_registry, list) or not devices_registry:
        return None
    registry: Dict[str, Dict[str, Any]] = {}
    for entry in devices_registry:
        if not isinstance(entry, dict):
            continue
        label = str(entry.get(KEY_LABEL, "")).strip()
        if not label:
            continue
        registry[label.lower()] = entry
    selected_profile = profile_name
    if not isinstance(selected_profile, str) or selected_profile not in profiles:
        default_profile = payload.get(KEY_DEFAULT_PROFILE)
        if not isinstance(default_profile, str) or default_profile not in profiles:
            default_profile = next(iter(profiles.keys()))
        selected_profile = default_profile
    raw = profiles.get(selected_profile)
    if not isinstance(raw, dict):
        return None
    labels = raw.get(KEY_PROFILE_DEVICES)
    if not isinstance(labels, list):
        return None
    devices: List[Dict[str, Any]] = []
    for label in labels:
        if not isinstance(label, str):
            continue
        entry = registry.get(label.lower())
        if entry is None:
            continue
        device: Dict[str, Any] = {"name": str(label).strip()}
        if KEY_VENDOR in entry:
            device["vendor"] = entry.get(KEY_VENDOR)
        if KEY_TYPE in entry:
            device["role"] = entry.get(KEY_TYPE)
        if KEY_NOTES in entry:
            device["notes"] = entry.get(KEY_NOTES)
        if KEY_BUS in entry:
            device["bus"] = entry.get(KEY_BUS)
        if KEY_TAGS in entry:
            device["tags"] = entry.get(KEY_TAGS)
        if KEY_LIMITS in entry:
            device["limits"] = entry.get(KEY_LIMITS)
        if KEY_ATTACHMENTS in entry:
            device["attachments"] = entry.get(KEY_ATTACHMENTS)
        devices.append(device)
    if _find_duplicate_device_names({"devices": devices}):
        return None
    return devices


def _find_duplicate_device_names(config: Dict[str, Any]) -> List[str]:
    """
    NAME
        _find_duplicate_device_names - Find duplicate device names.
    """
    devices = config.get("devices") if isinstance(config, dict) else None
    if not isinstance(devices, list):
        return []
    seen = {}
    dupes = []
    for device in devices:
        if not isinstance(device, dict):
            continue
        name = str(device.get("name", "")).strip()
        if not name:
            continue
        key = name.lower()
        seen[key] = seen.get(key, 0) + 1
        if seen[key] == 2:
            dupes.append(name)
    return dupes


def _fetch_runtime_state_json(
    session: BridgeSession,
    timeout_sec: float = 2.0,
) -> Optional[Dict[str, Any]]:
    """
    NAME
        _fetch_runtime_state_json - Fetch runtime-state JSON from the robot.
    """
    seq = show_runtime_state(session, json_output=True)
    if seq is None:
        return None
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        events = session.poll_events()
        if not events:
            time.sleep(0.02)
            continue
        for event in events:
            if event.seq != seq or event.type != "out":
                continue
            parsed = parse_json_arg(event.json_text)
            if isinstance(parsed, dict):
                return parsed
            return None
    return None


def _config_from_runtime_state(state: Dict[str, Any], profile_name: str) -> Dict[str, Any]:
    """
    NAME
        _config_from_runtime_state - Build a config file from runtime state.
    """
    groups = state.get("groups") if isinstance(state.get("groups"), list) else []
    selected = state.get("selectedDevice") if isinstance(state.get("selectedDevice"), dict) else {}
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return {
        KEY_BRIDGE_SCHEMA_VERSION: CONFIG_SCHEMA_VERSION,
        KEY_BRIDGE_GENERATED_AT: stamp,
        KEY_BRIDGE_BY_PROFILE: {
            profile_name: {
                KEY_BRIDGE_GROUPS: groups,
                KEY_BRIDGE_SELECTED_DEVICE: {
                    KEY_DEVICE: str(selected.get(KEY_DEVICE, "")).strip(),
                    "enabled": bool(selected.get("enabled", False)),
                },
            }
        },
    }
