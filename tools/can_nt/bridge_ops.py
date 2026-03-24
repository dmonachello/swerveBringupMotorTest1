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
from tools.common.json_io import read_json, write_json
from tools.common.profile_io import validate_profiles_schema
from tools.common.paths import profiles_deploy_path

CONFIG_SCHEMA_VERSION = 1


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


@dataclass(frozen=True)
class LocalOpResult:
    """
    NAME
        LocalOpResult - Result of a local config operation.
    """

    ok: bool
    message: str


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


def local_show_data(
    target: str, tokens: List[str], config: Dict[str, Any]
) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    NAME
        local_show_data - Build local show payloads from bridgeConfig.
    """
    if not isinstance(config, dict):
        return (False, "Local config missing or invalid.", {})
    groups = list(config.get("groups", [])) if isinstance(config.get("groups"), list) else []
    selected = config.get("selectedDevice") if isinstance(config.get("selectedDevice"), dict) else {}
    selected_device = str(selected.get("device", "")).strip()
    selected_enabled = bool(selected.get("enabled", False))

    if target == "status":
        payload = {
            "source": "local",
            "groupCount": len(groups),
            "selectedDevice": {"device": selected_device, "enabled": selected_enabled},
        }
        return (True, None, payload)

    if target == "groups":
        return (True, None, {"source": "local", "groups": groups})

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
        devices_raw = config.get("devices") if isinstance(config.get("devices"), list) else None
        if isinstance(devices_raw, list) and devices_raw:
            return (True, None, {"source": "local", "devices": devices_raw})
        devices: List[str] = []
        for group in groups:
            if not isinstance(group, dict):
                continue
            for member in group.get("members", []) or []:
                if isinstance(member, dict):
                    name = str(member.get("device", "")).strip()
                else:
                    name = str(member).strip()
                if name and name not in devices:
                    devices.append(name)
        if selected_device and selected_device not in devices:
            devices.append(selected_device)
        return (True, None, {"source": "local", "devices": devices})

    if target == "device":
        name = tokens[1] if len(tokens) >= 2 else ""
        devices_raw = config.get("devices") if isinstance(config.get("devices"), list) else None
        if isinstance(devices_raw, list):
            for device in devices_raw:
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
        devices = config.get("devices") if isinstance(config.get("devices"), list) else None
        payload = {
            "source": "local",
            "schemaVersion": config.get("schemaVersion", CONFIG_SCHEMA_VERSION),
            "generatedAt": config.get("generatedAt"),
            "groups": groups,
            "selectedDevice": {"device": selected_device, "enabled": selected_enabled},
            "devices": devices if isinstance(devices, list) else None,
        }
        return (True, None, payload)

    return (False, "Unknown show command.", {})

def merge_config(path: str, conflict_policy: str = "error") -> ConfigPlan:
    """
    NAME
        merge_config - Load a config file and build merge commands.
    """
    config, root_payload = _read_bridge_config(path)
    if config is None:
        return ConfigPlan(False, f"Invalid config: {path}", [], False, None)
    commands = _build_commands_from_config(config, conflict_policy)
    return ConfigPlan(
        True,
        f"Loaded {len(config.get('groups', []))} group(s) from {path}.",
        commands,
        False,
        config,
        root_payload,
        path if root_payload is not None else None,
    )


def import_config(path: str, conflict_policy: str = "error") -> ConfigPlan:
    """
    NAME
        import_config - Load a config file and build replace commands.
    """
    config, root_payload = _read_bridge_config(path)
    if config is None:
        return ConfigPlan(False, f"Invalid config: {path}", [], True, None)
    commands = _build_commands_from_config(config, conflict_policy)
    return ConfigPlan(
        True,
        f"Loaded {len(config.get('groups', []))} group(s) from {path}.",
        commands,
        True,
        config,
        root_payload,
        path if root_payload is not None else None,
    )


def export_runtime_groups(session: BridgeSession, path: str) -> LocalOpResult:
    """
    NAME
        export_runtime_groups - Export runtime groups to a bridgeConfig file.
    """
    state = _fetch_runtime_state_json(session)
    if state is None:
        return LocalOpResult(False, "Failed to fetch runtime state.")
    config = _config_from_runtime_state(state)
    try:
        write_json(Path(path), config, indent=2, trailing_newline=True)
    except Exception as exc:
        return LocalOpResult(False, f"Failed to write {path}: {exc}")
    return LocalOpResult(True, f"Wrote bridgeConfig to {path}.")


def save_config(session: BridgeSession, path: str) -> LocalOpResult:
    """
    NAME
        save_config - Save current runtime config to a bridgeConfig file.
    """
    state = _fetch_runtime_state_json(session)
    if state is None:
        return LocalOpResult(False, "Failed to fetch runtime state.")
    config = _config_from_runtime_state(state)
    try:
        write_json(Path(path), config, indent=2, trailing_newline=True)
    except Exception as exc:
        return LocalOpResult(False, f"Failed to write {path}: {exc}")
    return LocalOpResult(True, f"Wrote bridgeConfig to {path}.")


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
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    NAME
        _read_bridge_config - Load and normalize bridge config from a profiles file.
    """
    if not path:
        return (None, None)
    try:
        payload = read_json(Path(path))
    except Exception:
        return (None, None)
    if not isinstance(payload, dict):
        return (None, None)
    if "schema_version" in payload and "profiles" in payload:
        bridge = payload.get("bridgeConfig") or {}
        if not isinstance(bridge, dict):
            return (None, None)
        config = _normalize_bridge_config(bridge, allow_empty=True)
        if config is None:
            return (None, None)
        generated_devices = devices_from_profiles_payload(payload)
        if generated_devices is None:
            return (None, None)
        config["devices"] = generated_devices
        return (config, payload)
    config = _normalize_bridge_config(payload, allow_empty=False)
    return (config, None)


def _normalize_bridge_config(
    payload: Dict[str, Any],
    allow_empty: bool,
) -> Optional[Dict[str, Any]]:
    """
    NAME
        _normalize_bridge_config - Normalize bridge config fields to a stable schema.
    """
    version = int(payload.get("schemaVersion", CONFIG_SCHEMA_VERSION))
    if version != CONFIG_SCHEMA_VERSION:
        return None
    groups_raw = payload.get("groups")
    if not isinstance(groups_raw, list):
        if allow_empty:
            groups_raw = []
        else:
            return None
    devices_raw = payload.get("devices")
    generated_at = payload.get("generatedAt")
    groups: List[Dict[str, Any]] = []
    for group in groups_raw:
        if not isinstance(group, dict):
            continue
        name = str(group.get("name", "")).strip()
        if not name:
            continue
        enabled = bool(group.get("enabled", True))
        members: List[Dict[str, Any]] = []
        for member in group.get("members", []) or []:
            if isinstance(member, str):
                members.append({"device": member, "enabled": True})
                continue
            if not isinstance(member, dict):
                continue
            device = str(member.get("device", "")).strip()
            if not device:
                continue
            members.append({"device": device, "enabled": bool(member.get("enabled", True))})
        bindings: List[Dict[str, Any]] = []
        for binding in group.get("bindings", []) or []:
            if not isinstance(binding, dict):
                continue
            input_name = str(binding.get("input", "")).strip()
            kind = str(binding.get("kind", "")).strip()
            if not input_name or not kind:
                continue
            entry: Dict[str, Any] = {"input": input_name, "kind": kind}
            if "value" in binding:
                entry["value"] = binding.get("value")
            bindings.append(entry)
        groups.append(
            {
                "name": name,
                "enabled": enabled,
                "members": members,
                "bindings": bindings,
            }
        )
    devices: List[Dict[str, Any]] = []
    if isinstance(devices_raw, list):
        for device in devices_raw:
            if not isinstance(device, dict):
                continue
            name = str(device.get("name", "")).strip()
            if not name:
                continue
            entry: Dict[str, Any] = {"name": name}
            if "manufacturer" in device:
                entry["manufacturer"] = device.get("manufacturer")
            if "deviceType" in device:
                entry["deviceType"] = device.get("deviceType")
            if "deviceId" in device:
                entry["deviceId"] = device.get("deviceId")
            if "vendor" in device:
                entry["vendor"] = device.get("vendor")
            if "role" in device:
                entry["role"] = device.get("role")
            if "notes" in device:
                entry["notes"] = device.get("notes")
            if "bus" in device:
                entry["bus"] = device.get("bus")
            if "tags" in device:
                entry["tags"] = device.get("tags")
            if "limits" in device:
                entry["limits"] = device.get("limits")
            devices.append(entry)
    selected = payload.get("selectedDevice", {}) or {}
    selected_device = ""
    selected_enabled = False
    if isinstance(selected, dict):
        selected_device = str(selected.get("device", "")).strip()
        selected_enabled = bool(selected.get("enabled", False))
    return {
        "schemaVersion": version,
        "generatedAt": generated_at,
        "devices": devices,
        "groups": groups,
        "selectedDevice": {"device": selected_device, "enabled": selected_enabled},
    }


def _build_commands_from_config(
    config: Dict[str, Any],
    conflict_policy: str,
) -> List[BridgeCommand]:
    """
    NAME
        _build_commands_from_config - Convert config entries into commands.
    """
    commands: List[BridgeCommand] = []
    groups = config.get("groups") or []
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
        for binding in group.get("bindings", []) or []:
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
    selected = config.get("selectedDevice") or {}
    if isinstance(selected, dict):
        device = str(selected.get("device", "")).strip()
        enabled = bool(selected.get("enabled", False))
        if device:
            commands.append(BridgeCommand("selectedDeviceSet", {"name": device}))
            commands.append(BridgeCommand("selectedModeSet", {"enabled": enabled}))
    return commands


def validate_config_file(path: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    NAME
        validate_config_file - Validate a bridgeConfig file and report missing devices.
    """
    config, _root = _read_bridge_config(path)
    if config is None:
        return (False, f"Invalid config: {path}", None)
    duplicates = _find_duplicate_device_names(config)
    if duplicates:
        return (False, f"Duplicate device names: {', '.join(sorted(duplicates))}", config)
    missing = _find_missing_device_refs(config)
    if missing:
        missing_list = ", ".join(sorted(missing))
        return (False, f"Missing device entries: {missing_list}", config)
    return (True, "OK", config)


def _find_missing_device_refs(config: Dict[str, Any]) -> List[str]:
    """
    NAME
        _find_missing_device_refs - Find group members missing from devices list.
    """
    devices = config.get("devices") if isinstance(config, dict) else None
    known = set()
    if isinstance(devices, list):
        for device in devices:
            if not isinstance(device, dict):
                continue
            name = str(device.get("name", "")).strip()
            if name:
                known.add(name.lower())
    missing = []
    groups = config.get("groups") if isinstance(config, dict) else None
    if isinstance(groups, list):
        for group in groups:
            if not isinstance(group, dict):
                continue
            for member in group.get("members", []) or []:
                if isinstance(member, dict):
                    name = str(member.get("device", "")).strip()
                else:
                    name = str(member).strip()
                if name and name.lower() not in known:
                    missing.append(name)
    return missing


def validate_config_data(config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    NAME
        validate_config_data - Validate an in-memory bridgeConfig.
    """
    duplicates = _find_duplicate_device_names(config)
    if duplicates:
        return (False, f"Duplicate device names: {', '.join(sorted(duplicates))}")
    missing = _find_missing_device_refs(config)
    if missing:
        missing_list = ", ".join(sorted(missing))
        return (False, f"Missing device entries: {missing_list}")
    return (True, "OK")


def devices_from_profiles_payload(payload: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """
    NAME
        _devices_from_profiles_payload - Build bridgeConfig devices from profiles.
    """
    profiles = payload.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        return None
    default_profile = payload.get("default_profile")
    if not isinstance(default_profile, str) or default_profile not in profiles:
        default_profile = next(iter(profiles.keys()))
    raw = profiles.get(default_profile)
    if not isinstance(raw, dict):
        return None
    mappings = _load_can_mappings()
    devices = _devices_from_profile(raw, mappings)
    if _find_duplicate_device_names({"devices": devices}):
        return None
    return devices


def _devices_from_profile(
    raw: Dict[str, Any],
    mappings: Tuple[Dict[str, int], Dict[str, int]],
) -> List[Dict[str, Any]]:
    """
    NAME
        _devices_from_profile - Convert a profile section into bridgeConfig devices.
    """
    mfg_map, type_map = mappings
    devices: List[Dict[str, Any]] = []

    def _add_device(entry: Dict[str, Any], label: str, device_id: int, manufacturer: int, device_type: int) -> None:
        dev: Dict[str, Any] = {
            "name": label,
            "manufacturer": manufacturer,
            "deviceType": device_type,
            "deviceId": int(device_id),
        }
        if "vendor" in entry:
            dev["vendor"] = entry.get("vendor")
        if "role" in entry:
            dev["role"] = entry.get("role")
        if "notes" in entry:
            dev["notes"] = entry.get("notes")
        if "bus" in entry:
            dev["bus"] = entry.get("bus")
        if "tags" in entry:
            dev["tags"] = entry.get("tags")
        if "limits" in entry:
            dev["limits"] = entry.get("limits")
        devices.append(dev)

    def _list_devices(key: str, manufacturer: int, device_type: int, default_prefix: str) -> None:
        for entry in raw.get(key, []) or []:
            if not isinstance(entry, dict) or "id" not in entry:
                continue
            label = entry.get("label") or f"{default_prefix} {entry.get('id')}"
            _add_device(entry, str(label), int(entry.get("id")), manufacturer, device_type)

    _list_devices("neos", 5, 2, "NEO")
    _list_devices("neo550s", 5, 2, "NEO 550")
    _list_devices("flexes", 5, 2, "FLEX")
    _list_devices("krakens", 4, 2, "KRAKEN")
    _list_devices("falcons", 4, 2, "FALCON")
    _list_devices("cancoders", 4, 7, "CANCoder")
    _list_devices("candles", 4, 10, "CANdle")

    pdh = raw.get("pdh")
    if isinstance(pdh, dict) and "id" in pdh:
        label = pdh.get("label") or "PDH"
        _add_device(pdh, str(label), int(pdh.get("id")), 5, 8)
    pdp = raw.get("pdp")
    if isinstance(pdp, dict) and "id" in pdp:
        label = pdp.get("label") or "PDP"
        _add_device(pdp, str(label), int(pdp.get("id")), 4, 8)
    pigeon = raw.get("pigeon")
    if isinstance(pigeon, dict) and "id" in pigeon:
        label = pigeon.get("label") or "Pigeon"
        _add_device(pigeon, str(label), int(pigeon.get("id")), 4, 4)
    roborio = raw.get("roborio")
    if isinstance(roborio, dict) and "id" in roborio:
        label = roborio.get("label") or "roboRIO"
        _add_device(roborio, str(label), int(roborio.get("id")), 1, 1)

    for entry in raw.get("devices", []) or []:
        if not isinstance(entry, dict) or "id" not in entry:
            continue
        label = entry.get("label") or f"Device {entry.get('id')}"
        dev: Dict[str, Any] = {"name": str(label), "deviceId": int(entry.get("id"))}
        vendor = entry.get("vendor")
        dtype = entry.get("type")
        if vendor:
            dev["vendor"] = vendor
            mfg_id = mfg_map.get(str(vendor).lower())
            if mfg_id is not None:
                dev["manufacturer"] = mfg_id
        if dtype:
            dev["role"] = dtype
            type_id = type_map.get(str(dtype).lower())
            if type_id is not None:
                dev["deviceType"] = type_id
        if "tags" in entry:
            dev["tags"] = entry.get("tags")
        if "limits" in entry:
            dev["limits"] = entry.get("limits")
        devices.append(dev)

    return devices


def _load_can_mappings() -> Tuple[Dict[str, int], Dict[str, int]]:
    """
    NAME
        _load_can_mappings - Load manufacturer/deviceType name maps.
    """
    mapping_path = profiles_deploy_path().parent / "can_mappings.json"
    try:
        payload = read_json(mapping_path)
    except Exception:
        return ({}, {})
    manufacturers = payload.get("manufacturers", {}) if isinstance(payload, dict) else {}
    device_types = payload.get("device_types", {}) if isinstance(payload, dict) else {}
    mfg_map: Dict[str, int] = {}
    type_map: Dict[str, int] = {}
    if isinstance(manufacturers, dict):
        for key, value in manufacturers.items():
            try:
                mid = int(key)
            except Exception:
                continue
            name = str(value).lower()
            mfg_map[name] = mid
    if isinstance(device_types, dict):
        for key, value in device_types.items():
            try:
                tid = int(key)
            except Exception:
                continue
            name = str(value).lower()
            type_map[name] = tid
    return (mfg_map, type_map)


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


def _config_from_runtime_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    NAME
        _config_from_runtime_state - Build a config file from runtime state.
    """
    groups = state.get("groups") if isinstance(state.get("groups"), list) else []
    selected = state.get("selectedDevice") if isinstance(state.get("selectedDevice"), dict) else {}
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return {
        "schemaVersion": CONFIG_SCHEMA_VERSION,
        "generatedAt": stamp,
        "devices": [],
        "groups": groups,
        "selectedDevice": {
            "device": str(selected.get("device", "")).strip(),
            "enabled": bool(selected.get("enabled", False)),
        },
    }
