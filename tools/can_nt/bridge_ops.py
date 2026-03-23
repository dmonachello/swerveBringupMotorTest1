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
from typing import Any, Dict, List, Optional

from tools.can_nt.bridge_session import BridgeSession
from tools.common.json_io import read_json, write_json

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


def merge_config(path: str, conflict_policy: str = "error") -> ConfigPlan:
    """
    NAME
        merge_config - Load a config file and build merge commands.
    """
    config = _read_bridge_config(path)
    if config is None:
        return ConfigPlan(False, f"Invalid config: {path}", [], False, None)
    commands = _build_commands_from_config(config, conflict_policy)
    return ConfigPlan(
        True,
        f"Loaded {len(config.get('groups', []))} group(s) from {path}.",
        commands,
        False,
        config,
    )


def import_config(path: str, conflict_policy: str = "error") -> ConfigPlan:
    """
    NAME
        import_config - Load a config file and build replace commands.
    """
    config = _read_bridge_config(path)
    if config is None:
        return ConfigPlan(False, f"Invalid config: {path}", [], True, None)
    commands = _build_commands_from_config(config, conflict_policy)
    return ConfigPlan(
        True,
        f"Loaded {len(config.get('groups', []))} group(s) from {path}.",
        commands,
        True,
        config,
    )


def export_runtime_groups(session: BridgeSession, path: str) -> LocalOpResult:
    """
    NAME
        export_runtime_groups - Export runtime groups to a config file.
    """
    state = _fetch_runtime_state_json(session)
    if state is None:
        return LocalOpResult(False, "Failed to fetch runtime state.")
    config = _config_from_runtime_state(state)
    try:
        write_json(Path(path), config, indent=2, trailing_newline=True)
    except Exception as exc:
        return LocalOpResult(False, f"Failed to write {path}: {exc}")
    return LocalOpResult(True, f"Wrote runtime groups to {path}.")


def save_config(session: BridgeSession, path: str) -> LocalOpResult:
    """
    NAME
        save_config - Save current runtime config to a file.
    """
    state = _fetch_runtime_state_json(session)
    if state is None:
        return LocalOpResult(False, "Failed to fetch runtime state.")
    config = _config_from_runtime_state(state)
    try:
        write_json(Path(path), config, indent=2, trailing_newline=True)
    except Exception as exc:
        return LocalOpResult(False, f"Failed to write {path}: {exc}")
    return LocalOpResult(True, f"Wrote config to {path}.")


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


def _read_bridge_config(path: str) -> Optional[Dict[str, Any]]:
    """
    NAME
        _read_bridge_config - Load and normalize a bridge config file.
    """
    if not path:
        return None
    try:
        payload = read_json(Path(path))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    return _normalize_config(payload)


def _normalize_config(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    NAME
        _normalize_config - Normalize config fields to a stable schema.
    """
    version = int(payload.get("schemaVersion", CONFIG_SCHEMA_VERSION))
    if version != CONFIG_SCHEMA_VERSION:
        return None
    groups_raw = payload.get("groups")
    if not isinstance(groups_raw, list):
        return None
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
    selected = payload.get("selectedDevice", {}) or {}
    selected_device = ""
    selected_enabled = False
    if isinstance(selected, dict):
        selected_device = str(selected.get("device", "")).strip()
        selected_enabled = bool(selected.get("enabled", False))
    return {
        "schemaVersion": version,
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
        "groups": groups,
        "selectedDevice": {
            "device": str(selected.get("device", "")).strip(),
            "enabled": bool(selected.get("enabled", False)),
        },
    }
