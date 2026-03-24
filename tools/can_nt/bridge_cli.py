from __future__ import annotations

"""
NAME
    bridge_cli.py - Interactive Cisco-style CLI for the bridge app.

SYNOPSIS
    python tools\\can_nt\\bridge_cli.py --rio 172.22.11.2

DESCRIPTION
    Provides interactive and batch CLI modes over the shared BridgeSession
    and bridge_ops layers. Output streams directly to console.
"""

import json
import shlex
import time
from copy import deepcopy
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional

from tools.can_nt.bridge_ops import (
    connect,
    disconnect,
    export_runtime_groups,
    BridgeCommand,
    ConfigPlan,
    validate_config_file,
    validate_config_data,
    devices_from_profiles_payload,
    group_add_device,
    group_bind,
    group_create,
    group_delete,
    group_disable,
    group_enable,
    group_member_disable,
    group_member_enable,
    group_member_toggle,
    group_remove_device,
    group_run_test,
    group_unbind,
    import_config,
    merge_config,
    save_config,
    selected_device_set,
    selected_mode_set,
    show_bindings,
    show_device,
    show_devices,
    show_group,
    show_groups,
    show_runtime_state,
    show_selected_device,
    show_status,
)
from tools.can_nt.bridge_session import BridgeEvent, BridgeSession
from tools.common.json_io import write_json
from tools.common.profile_io import compute_profiles_hash
from tools.common.time_utils import timestamp_version


@dataclass
class CliMode:
    name: str
    group: str = ""
    device: str = ""


class BridgeCli:
    """
    NAME
        BridgeCli - CLI front end for bridge operations.
    """

    def __init__(
        self,
        session: BridgeSession,
        batch: bool = False,
        conflict_policy: str = "error",
    ) -> None:
        self._session = session
        self._batch = batch
        self._conflict_policy = conflict_policy
        self._modes: List[CliMode] = [CliMode("exec")]
        self._last_seq: Optional[int] = None
        self._local_config: Optional[Dict[str, object]] = None
        self._local_config_path: Optional[str] = None
        self._local_loaded_at: Optional[float] = None
        self._local_root_payload: Optional[Dict[str, object]] = None
        self._local_root_path: Optional[str] = None
        self._show_label_seq: Dict[int, str] = {}
        self._local_devices_locked: bool = False
        self._profiles_dirty: bool = False
        self._can_mfg_id_to_name: Dict[int, str] = {}
        self._can_mfg_name_to_id: Dict[str, int] = {}
        self._can_type_id_to_name: Dict[int, str] = {}
        self._can_type_name_to_id: Dict[str, int] = {}
        self._load_can_mappings()

    def run_interactive(self) -> int:
        """
        NAME
            run_interactive - Enter the interactive prompt loop.
        """
        while True:
            try:
                prompt = self._prompt()
                line = input(prompt)
            except EOFError:
                print()
                code = self._execute_line("exit")
                if code is None:
                    continue
                return code
            except KeyboardInterrupt:
                print()
                continue
            line = line.strip()
            if not line:
                continue
            code = self._execute_line(line)
            if code is not None:
                if code == 0:
                    return 0
                print("WARNING: Command failed; staying in CLI.")
                continue

    def run_batch(self, lines: List[str]) -> int:
        """
        NAME
            run_batch - Execute a batch script.
        """
        lint_error = self._lint_script(lines)
        if lint_error:
            print(f"ERROR: {lint_error}")
            return 2
        for raw in lines:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            code = self._execute_line(line)
            if code is not None:
                return code
        return 0

    def _prompt(self) -> str:
        mode = self._modes[-1]
        if mode.name == "exec":
            return "bridge> "
        if mode.name == "config":
            return "bridge(config)# "
        if mode.name == "group":
            return f"bridge(config-group-{mode.group})# "
        if mode.name == "device":
            return f"bridge(config-device-{mode.device})# "
        return "bridge> "

    def _execute_line(self, line: str) -> Optional[int]:
        try:
            tokens = self._split_command(line)
        except ValueError as exc:
            print(f"ERROR: {exc}")
            return None
        if not tokens:
            return None
        cmd = tokens[0].lower()
        if cmd in ("quit", "exit"):
            if self._modes[-1].name == "exec":
                return 0
            self._pop_mode()
            return None
        if cmd == "end":
            self._modes = [CliMode("exec")]
            return None
        if cmd == "help":
            self._print_help(tokens[1:] if len(tokens) > 1 else [])
            return None
        if cmd == "ping":
            seq = show_status(self._session, json_output=False)
            self._wait_for_seq(seq)
            return None

        mode = self._modes[-1].name
        if mode == "exec":
            return self._exec_command(tokens)
        if mode == "config":
            return self._config_command(tokens)
        if mode == "group":
            return self._group_command(tokens)
        if mode == "device":
            return self._device_command(tokens)
        print("ERROR: unknown mode.")
        return None

    def _exec_command(self, tokens: List[str]) -> Optional[int]:
        cmd = tokens[0].lower()
        if cmd == "connect":
            if not connect(self._session):
                print("ERROR: Failed to connect.")
                return 2
            ok = self._session.ensure_handshake()
            if not ok:
                print("ERROR: Handshake failed.")
                return 2
            print("Connected.")
            return None
        if cmd == "disconnect":
            disconnect(self._session)
            print("Disconnected.")
            return None
        if cmd == "configure" and len(tokens) > 1 and tokens[1].lower() == "terminal":
            self._ensure_local_config()
            self._modes.append(CliMode("config"))
            return None
        if cmd == "show":
            return self._handle_show(tokens[1:])
        print(f"ERROR: Unknown command: {' '.join(tokens)}")
        return None

    def _config_command(self, tokens: List[str]) -> Optional[int]:
        cmd = tokens[0].lower()
        if cmd == "group" and len(tokens) >= 2 and not self._session.is_connected():
            name = tokens[1]
            if not self._select_or_create_local_group(name):
                return 2 if self._batch else None
            self._modes.append(CliMode("group", name))
            print("WARNING: Robot not connected; local group selected.")
            return None
        if cmd == "rename" and len(tokens) >= 4 and tokens[1].lower() == "device":
            if self._rename_local_device(tokens[2], tokens[3]):
                print(f"Renamed device {tokens[2]} -> {tokens[3]}.")
                return None
            return 2 if self._batch else None
        if cmd == "device" and len(tokens) >= 5 and tokens[2].lower() == "set":
            field = tokens[3]
            value_raw = " ".join(tokens[4:])
            if not self._set_local_device_meta(tokens[1], field, value_raw):
                return 2 if self._batch else None
            print(f"Updated device {tokens[1]} {field}={value_raw}.")
            return None
        if cmd == "group" and len(tokens) >= 2:
            name = tokens[1]
            seq = group_create(self._session, name)
            event = self._wait_for_seq(seq)
            if self._event_failed(event, "group create"):
                return 2 if self._batch else None
            self._modes.append(CliMode("group", name))
            return None
        if cmd == "device" and len(tokens) >= 2:
            name = tokens[1]
            if not self._ensure_local_device_entry(name):
                return 2 if self._batch else None
            self._modes.append(CliMode("device", device=name))
            return None
        if cmd == "no" and len(tokens) >= 3 and tokens[1].lower() == "group" and not self._session.is_connected():
            name = tokens[2]
            if not self._confirm(f"Delete group '{name}'?"):
                return None
            if not self._delete_local_group(name):
                return 2 if self._batch else None
            print("WARNING: Robot not connected; local group deleted.")
            return None
        if cmd == "no" and len(tokens) >= 3 and tokens[1].lower() == "group":
            name = tokens[2]
            if not self._confirm(f"Delete group '{name}'?"):
                return None
            seq = group_delete(self._session, name, confirm=True)
            event = self._wait_for_seq(seq)
            if self._event_failed(event, "group delete"):
                return 2 if self._batch else None
            return None
        if cmd == "selected-device" and len(tokens) >= 2 and not self._session.is_connected():
            if not self._set_local_selected_device(tokens[1]):
                return 2 if self._batch else None
            print("WARNING: Robot not connected; local selected-device updated.")
            return None
        if cmd == "selected-device" and len(tokens) >= 2:
            seq = selected_device_set(self._session, tokens[1])
            event = self._wait_for_seq(seq)
            if self._event_failed(event, "selected-device"):
                return 2 if self._batch else None
            return None
        if cmd == "selected-mode" and len(tokens) >= 2 and not self._session.is_connected():
            mode_value = tokens[1].lower()
            if mode_value not in ("on", "off"):
                print("ERROR: selected-mode requires on/off.")
                return None
            enabled = mode_value == "on"
            if not self._set_local_selected_mode(enabled):
                return 2 if self._batch else None
            print("WARNING: Robot not connected; local selected-mode updated.")
            return None
        if cmd == "selected-mode" and len(tokens) >= 2:
            mode_value = tokens[1].lower()
            if mode_value not in ("on", "off"):
                print("ERROR: selected-mode requires on/off.")
                return None
            enabled = mode_value == "on"
            seq = selected_mode_set(self._session, enabled)
            event = self._wait_for_seq(seq)
            if self._event_failed(event, "selected-mode"):
                return 2 if self._batch else None
            return None
        if cmd == "merge" and len(tokens) >= 3 and tokens[1].lower() == "config":
            plan = merge_config(tokens[2], self._conflict_policy)
            return self._apply_config_plan(plan)
        if cmd == "import" and len(tokens) >= 3 and tokens[1].lower() == "config":
            plan = import_config(tokens[2], self._conflict_policy)
            return self._apply_config_plan(plan)
        if cmd == "export" and len(tokens) >= 3 and tokens[1].lower() == "runtime-groups":
            result = export_runtime_groups(self._session, tokens[2])
            print(result.message)
            return 2 if not result.ok else None
        if cmd == "export" and len(tokens) >= 3 and tokens[1].lower() == "cli-script":
            if not self._export_cli_script(tokens[2]):
                return 2 if self._batch else None
            return None
        if cmd == "save" and len(tokens) >= 3 and tokens[1].lower() == "profiles":
            if not self._save_profiles(tokens[2]):
                return 2 if self._batch else None
            return None
        if cmd == "save" and len(tokens) >= 3 and tokens[1].lower() == "unified-config":
            if not self._save_unified_config(tokens[2]):
                return 2 if self._batch else None
            return None
        if cmd == "validate" and len(tokens) >= 2 and tokens[1].lower() == "config":
            if len(tokens) >= 3:
                ok, message, _config = validate_config_file(tokens[2])
            else:
                if not self._local_config:
                    print("ERROR: Local config not loaded. Use merge/import config <path> first.")
                    return 2 if self._batch else None
                ok, message = validate_config_data(self._local_config)
            if ok:
                print("OK: Config is valid.")
                return None
            print(f"ERROR: {message}")
            return 2 if self._batch else None
        if cmd == "save" and len(tokens) >= 3 and tokens[1].lower() == "config":
            result = save_config(self._session, tokens[2])
            print(result.message)
            return 2 if not result.ok else None
        if cmd == "save" and len(tokens) >= 3 and tokens[1].lower() == "local-config":
            if not self._save_local_config(tokens[2]):
                return 2 if self._batch else None
            return None
        if cmd == "show":
            return self._handle_show(tokens[1:])
        print(f"ERROR: Unknown command: {' '.join(tokens)}")
        return None

    def _group_command(self, tokens: List[str]) -> Optional[int]:
        group = self._modes[-1].group
        cmd = tokens[0].lower()
        if not self._session.is_connected():
            return self._group_command_local(tokens, group)
        if cmd == "show":
            if len(tokens) == 1:
                seq = show_group(self._session, group, json_output=self._has_json(tokens))
                event = self._wait_for_seq(seq)
                if self._event_failed(event, "show group"):
                    return 2 if self._batch else None
                return None
            if tokens[1].lower() == "members":
                seq = show_group(self._session, group, json_output=self._has_json(tokens))
                event = self._wait_for_seq(seq)
                if self._event_failed(event, "show group"):
                    return 2 if self._batch else None
                return None
            if tokens[1].lower() == "binding":
                seq = show_group(self._session, group, json_output=self._has_json(tokens))
                event = self._wait_for_seq(seq)
                if self._event_failed(event, "show group"):
                    return 2 if self._batch else None
                return None
            return self._handle_show(tokens[1:])
        if cmd == "add" and len(tokens) >= 3 and tokens[1].lower() == "device":
            if not self._local_device_exists(tokens[2]):
                print("ERROR: Device not defined in local config. Use device <name> to create it.")
                return 2 if self._batch else None
            seq = group_add_device(
                self._session, group, tokens[2], self._conflict_policy, force_move=False
            )
            event = self._wait_for_seq(seq)
            if self._handle_add_device_conflict(event, group, tokens[2]):
                return 2 if self._batch else None
            if self._event_failed(event, "add device"):
                return 2 if self._batch else None
            return None
        if cmd == "no" and len(tokens) >= 3 and tokens[1].lower() == "device":
            seq = group_remove_device(self._session, group, tokens[2])
            event = self._wait_for_seq(seq)
            if self._event_failed(event, "remove device"):
                return 2 if self._batch else None
            return None
        if cmd == "member" and len(tokens) >= 3:
            action = tokens[2].lower()
            if action == "enable":
                seq = group_member_enable(self._session, group, tokens[1])
            elif action == "disable":
                seq = group_member_disable(self._session, group, tokens[1])
            elif action == "toggle":
                seq = group_member_toggle(self._session, group, tokens[1])
            else:
                print("ERROR: member requires enable/disable/toggle.")
                return None
            event = self._wait_for_seq(seq)
            if self._event_failed(event, "member"):
                return 2 if self._batch else None
            return None
        if cmd == "bind" and len(tokens) >= 3:
            input_name = tokens[1]
            kind = tokens[2].lower()
            value = None
            if kind != "analog":
                if len(tokens) < 4:
                    print("ERROR: binding requires value.")
                    return None
                try:
                    value = float(tokens[3])
                except ValueError:
                    print("ERROR: binding value must be numeric.")
                    return None
            seq = group_bind(self._session, group, input_name, kind, value=value)
            event = self._wait_for_seq(seq)
            if self._event_failed(event, "bind"):
                return 2 if self._batch else None
            return None
        if cmd == "no" and len(tokens) >= 2 and tokens[1].lower() == "bind":
            seq = group_unbind(self._session, group)
            event = self._wait_for_seq(seq)
            if self._event_failed(event, "no bind"):
                return 2 if self._batch else None
            return None
        if cmd == "enable":
            seq = group_enable(self._session, group)
            event = self._wait_for_seq(seq)
            if self._event_failed(event, "enable"):
                return 2 if self._batch else None
            return None
        if cmd == "disable":
            seq = group_disable(self._session, group)
            event = self._wait_for_seq(seq)
            if self._event_failed(event, "disable"):
                return 2 if self._batch else None
            return None
        if cmd == "run" and len(tokens) >= 2 and tokens[1].lower() == "test":
            name = tokens[2] if len(tokens) >= 3 else None
            seq = group_run_test(self._session, group, name)
            event = self._wait_for_seq(seq)
            if self._event_failed(event, "run test"):
                return 2 if self._batch else None
            return None
        print(f"ERROR: Unknown command: {' '.join(tokens)}")
        return None

    def _device_command(self, tokens: List[str]) -> Optional[int]:
        """
        NAME
            _device_command - Handle device-mode commands.

        DESCRIPTION
            Applies metadata edits to the local bridgeConfig device entry.
        """
        device = self._modes[-1].device
        cmd = tokens[0].lower()
        if cmd == "show":
            if len(tokens) == 1:
                return self._show_local_device_entry(device)
            return self._handle_show(tokens[1:])
        if cmd == "set" and len(tokens) >= 3:
            field = tokens[1]
            value_raw = " ".join(tokens[2:])
            if not self._set_local_device_meta(device, field, value_raw):
                return 2 if self._batch else None
            print(f"Updated device {device} {field}={value_raw}.")
            return None
        if cmd == "no" and len(tokens) >= 2:
            field = tokens[1]
            if not self._clear_local_device_meta(device, field):
                return 2 if self._batch else None
            print(f"Cleared device {device} {field}.")
            return None
        print(f"ERROR: Unknown command: {' '.join(tokens)}")
        return None

    def _handle_show(self, tokens: List[str]) -> Optional[int]:
        if not tokens:
            print("ERROR: show requires a target.")
            return None
        source, tokens, json_output = self._parse_show_flags(tokens)
        if not tokens:
            print("ERROR: show requires a target.")
            return None
        target = tokens[0].lower()
        if target == "config":
            target = "runtime-state"
        if source == "both":
            local_ok = self._show_local(target, tokens, json_output)
            robot_ok = self._show_robot(target, tokens, json_output)
            if self._batch and (not local_ok or not robot_ok):
                return 2
            return None
        if source == "local":
            if not self._show_local(target, tokens, json_output):
                return 2 if self._batch else None
            return None
        if source == "robot":
            if not self._show_robot(target, tokens, json_output):
                return 2 if self._batch else None
            return None
        print("ERROR: Unknown show source.")
        return None

    def _apply_config_plan(self, plan: ConfigPlan) -> Optional[int]:
        """
        NAME
            _apply_config_plan - Execute commands from a merge/import plan.
        """
        if not plan.ok:
            print(f"ERROR: {plan.message}")
            return 2
        if plan.replace:
            if not self._batch:
                if not self._confirm("Replace existing groups?"):
                    print("Import cancelled.")
                    return None
            if not self._clear_existing_groups():
                return 2
        print(plan.message)
        if plan.config:
            self._local_config = plan.config
            self._local_config_path = plan.root_path
            self._local_loaded_at = time.time()
            self._local_root_payload = plan.root_payload
            self._local_root_path = plan.root_path
            self._local_devices_locked = plan.root_payload is not None
            self._profiles_dirty = False
        if not self._session.is_connected():
            print("WARNING: Robot not connected; local config loaded only.")
            return None
        for command in plan.commands:
            code = self._execute_command(command)
            if code is not None and code != 0:
                return code
        return None

    def _clear_existing_groups(self) -> bool:
        """
        NAME
            _clear_existing_groups - Delete all current groups.
        """
        groups = self._fetch_group_names()
        if groups is None:
            print("ERROR: Failed to query groups.")
            return False
        if not groups:
            return True
        for name in groups:
            seq = group_delete(self._session, name, confirm=True)
            self._wait_for_seq(seq)
        return True

    def _fetch_group_names(self) -> Optional[List[str]]:
        """
        NAME
            _fetch_group_names - Query group names via show groups --json.
        """
        seq = show_groups(self._session, json_output=True)
        event = self._wait_for_seq(seq, print_events=False)
        if event is None or not event.json_text:
            return None
        try:
            payload = json.loads(event.json_text)
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        groups = payload.get("groups", [])
        if not isinstance(groups, list):
            return None
        names: List[str] = []
        for group in groups:
            if not isinstance(group, dict):
                continue
            name = str(group.get("name", "")).strip()
            if name:
                names.append(name)
        return names

    def _execute_command(self, command: BridgeCommand) -> Optional[int]:
        """
        NAME
            _execute_command - Send a BridgeCommand and wait for output.
        """
        seq = self._session.send_command(command.name, command.args)
        if seq is None:
            print(f"ERROR: Failed to send {command.name}.")
            return 2
        event = self._wait_for_seq(seq)
        if self._event_failed(event, command.name):
            return 2 if self._batch else None
        if command.name == "groupAddDevice":
            device = str(command.args.get("device", ""))
            group = str(command.args.get("group", ""))
            if self._handle_add_device_conflict(event, group, device):
                return 2 if self._batch else None
        return None

    def _handle_add_device_conflict(
        self,
        event: Optional[BridgeEvent],
        group: str,
        device: str,
    ) -> bool:
        """
        NAME
            _handle_add_device_conflict - Prompt to move a device on conflicts.
        """
        if event is None or not event.json_text:
            return False
        try:
            payload = json.loads(event.json_text)
        except Exception:
            return False
        if not isinstance(payload, dict) or not payload.get("conflict"):
            return False
        current = str(payload.get("currentGroup", "")).strip()
        if self._batch:
            print(
                f"ERROR: Device {device} already in group {current}. "
                "Batch mode cannot prompt."
            )
            return True
        if not self._confirm(f"Move device '{device}' from '{current}' to '{group}'?"):
            print("Move cancelled.")
            return True
        seq = group_add_device(self._session, group, device, self._conflict_policy, force_move=True)
        self._wait_for_seq(seq)
        return True

    def _wait_for_seq(
        self,
        seq: Optional[int],
        timeout_sec: float = 2.0,
        print_events: bool = True,
    ) -> Optional[BridgeEvent]:
        if seq is None:
            print("ERROR: Command failed to send.")
            return None
        self._last_seq = seq
        deadline = time.time() + timeout_sec
        ack_status = ""
        ack_message = ""
        while time.time() < deadline:
            events = self._session.poll_events()
            if not events:
                time.sleep(0.02)
                continue
            for event in events:
                if print_events:
                    self._print_event(event)
                if event.seq == seq and event.type == "ack":
                    ack_status = event.status
                    ack_message = event.message
                if event.seq == seq and event.type == "out":
                    if ack_status:
                        event.status = ack_status
                        event.message = ack_message
                    return event
        print("WARNING: Timeout waiting for OUT.")
        return None

    def _event_failed(self, event: Optional[BridgeEvent], context: str) -> bool:
        if event is None:
            if self._batch:
                print(f"ERROR: Timeout waiting for {context} output.")
                return True
            return False
        return event.status == "error"

    def _print_event(self, event: BridgeEvent) -> None:
        if event.type == "ack":
            msg = event.message or event.status
            print(f"ACK {event.seq} {event.name} {event.status} {msg}".rstrip())
            return
        if event.type == "out":
            source = self._show_label_seq.pop(event.seq, "")
            if source:
                print(f"SOURCE: {source}")
            if event.text:
                print(event.text.rstrip())
            elif event.json_text:
                print(event.json_text.rstrip())
            return

    def _format_can_meta(self, key: str, value: object) -> str:
        """
        NAME
            _format_can_meta - Format manufacturer/deviceType with optional name.
        """
        if value is None:
            return ""
        try:
            numeric = int(value)
        except Exception:
            return f"{key} {value}"
        if key == "mfg":
            name = self._can_mfg_id_to_name.get(numeric)
        elif key == "type":
            name = self._can_type_id_to_name.get(numeric)
        else:
            name = None
        if name:
            return f"{key} {numeric} ({name})"
        return f"{key} {numeric}"

    def _confirm(self, prompt: str) -> bool:
        if self._batch:
            return False
        while True:
            resp = input(f"{prompt} [y/N] ").strip().lower()
            if not resp or resp in ("n", "no"):
                return False
            if resp in ("y", "yes"):
                return True

    @staticmethod
    def _has_json(tokens: List[str]) -> bool:
        return any(tok == "--json" for tok in tokens)

    def _pop_mode(self) -> None:
        if len(self._modes) > 1:
            self._modes.pop()

    def _print_help(self, args: List[str]) -> None:
        if args:
            topic = " ".join(args).strip().lower()
            detail = {
                "show": (
                    "show <status|groups|group <name>|devices|device <name>|bindings|selected-device|runtime-state|config> "
                    "[--json] [robot|local|both]\n"
                    "  Defaults: robot if connected, otherwise local."
                ),
                "configure terminal": "configure terminal\n  Enter config mode.",
                "connect": "connect\n  Open TCP connection and perform handshake.",
                "disconnect": "disconnect\n  Close TCP connection.",
                "group": "group <name>\n  Create/select a group (config mode).",
                "no group": "no group <name>\n  Delete group (config mode, prompts in interactive).",
                "selected-device": "selected-device <device>\n  Set selected-device override.",
                "selected-mode": "selected-mode <on|off>\n  Enable/disable selected-device mode.",
                "merge config": (
                    "merge config <bringup_system.json>\n"
                    "  Load bridgeConfig from profiles without clearing existing."
                ),
                "import config": (
                    "import config <bringup_system.json>\n"
                    "  Replace groups from profiles (prompts in interactive)."
                ),
                "export runtime-groups": (
                    "export runtime-groups <bridgeConfig.json>\n"
                    "  Write bridgeConfig from current runtime groups."
                ),
                "save config": (
                    "save config <bridgeConfig.json>\n"
                    "  Write bridgeConfig from current runtime state."
                ),
                "save local-config": "save local-config <path>\n  Save local groups config.",
                "save profiles": (
                    "save profiles <path>\n"
                    "  Save profiles/diagram to bringup_system.json (bridgeConfig unchanged)."
                ),
                "save unified-config": (
                    "save unified-config <path>\n"
                    "  Write a unified bringup_system.json with profiles + bridgeConfig."
                ),
                "rename device": "rename device <old> <new>\n  Rename a device in local config.",
                "device set": (
                    "device <name> set <field> <value>\n"
                    "  Fields: manufacturer, deviceType, deviceId, vendor, role, notes, bus, tags, limits\n"
                    "  Use JSON for tags/limits (e.g., tags [\"arm\",\"motor\"])."
                ),
                "device": (
                    "device <name>\n"
                    "  Enter device mode to edit local device metadata."
                ),
                "device mode": (
                    "device mode: show, set <field> <value>, no <field>\n"
                    "  Fields: manufacturer, deviceType, deviceId, vendor, role, notes, bus, tags, limits"
                ),
                "export cli-script": (
                    "export cli-script <path>\n"
                    "  Write a batch script that recreates the local config."
                ),
                "validate config": (
                    "validate config [path]\n"
                    "  Validate devices vs groups in a config file, or the local config if omitted."
                ),
                "add device": (
                    "add device <device>\n"
                    "  Add device to current group (device must exist in local config)."
                ),
                "no device": "no device <device>\n  Remove device from current group.",
                "member": "member <device> <enable|disable|toggle>\n  Control per-member enable state.",
                "bind": (
                    "bind <input> <analog|hold|toggle|jog-forward|jog-reverse> [value]\n"
                    "  Create a binding. Button bindings require a value."
                ),
                "no bind": "no bind\n  Clear all bindings from current group.",
                "enable": "enable\n  Enable current group.",
                "disable": "disable\n  Disable current group.",
                "run test": "run test [name]\n  Run a test in the current group.",
                "json": "append --json to show commands for JSON output",
                "sources": "append robot|local|both to show commands to select source",
                "batch": "use --batch --script <file> (no prompts, conflict policy applies)",
                "conflict-policy": "set with --conflict-policy <error|move>",
                "exec": "exec mode: show, connect, disconnect, configure terminal",
                "config": (
                    "config mode: group, no group, selected-device, selected-mode, "
                    "merge/import/export/save, rename device, device set, save local-config, save profiles, save unified-config"
                ),
                "group mode": "group mode: show, add/no device, member, bind/no bind, enable/disable, run test",
            }.get(topic)
            if detail:
                print(detail)
            else:
                print("Help: command not found.")
            return
        print(
            "Common: help, exit, end, quit, ping\n"
            "Exec: show, connect, disconnect, configure terminal\n"
            "Config: group, device, no group, selected-device, selected-mode, merge/import/export/save\n"
            "Group: show, add device, no device, member, bind, no bind, enable, disable, run test\n"
            "Device: show, set, no\n"
            "Tips: help show | help sources | help group | help batch | help json"
        )

    def _parse_show_flags(self, tokens: List[str]) -> tuple[str, List[str], bool]:
        source = ""
        cleaned: List[str] = []
        json_output = False
        for tok in tokens:
            lower = tok.lower()
            if lower in ("--json",):
                json_output = True
                continue
            if lower in ("robot", "--robot"):
                source = "robot"
                continue
            if lower in ("local", "--local"):
                source = "local"
                continue
            if lower in ("both", "--both"):
                source = "both"
                continue
            cleaned.append(tok)
        if not source:
            source = "robot" if self._session.is_connected() else "local"
        return source, cleaned, json_output

    def _show_robot(self, target: str, tokens: List[str], json_output: bool) -> bool:
        if not self._session.is_connected():
            print("ERROR: Robot source unavailable (not connected).")
            return False
        if target == "status":
            seq = show_status(self._session, json_output=json_output)
        elif target == "groups":
            seq = show_groups(self._session, json_output=json_output)
        elif target == "group" and len(tokens) >= 2:
            seq = show_group(self._session, tokens[1], json_output=json_output)
        elif target == "devices":
            seq = show_devices(self._session, json_output=json_output)
        elif target == "device" and len(tokens) >= 2:
            seq = show_device(self._session, tokens[1], json_output=json_output)
        elif target == "bindings":
            seq = show_bindings(self._session, json_output=json_output)
        elif target == "selected-device":
            seq = show_selected_device(self._session, json_output=json_output)
        elif target == "runtime-state":
            seq = show_runtime_state(self._session, json_output=json_output)
        else:
            print("ERROR: Unknown show command.")
            return False
        if seq is None:
            print("ERROR: Command failed to send.")
            return False
        self._show_label_seq[int(seq)] = "robot"
        event = self._wait_for_seq(seq)
        if self._event_failed(event, "show"):
            return False
        return True

    def _show_local(self, target: str, tokens: List[str], json_output: bool) -> bool:
        if not self._local_config:
            print("WARNING: Local config not loaded. Use merge/import config <bringup_system.json>.")
            return False
        config = self._local_config
        groups = list(config.get("groups", [])) if isinstance(config, dict) else []
        selected = config.get("selectedDevice") if isinstance(config, dict) else {}
        selected_device = ""
        selected_enabled = False
        if isinstance(selected, dict):
            selected_device = str(selected.get("device", "")).strip()
            selected_enabled = bool(selected.get("enabled", False))

        def _print_local(payload_text: str, payload_json: Optional[Dict[str, object]]) -> None:
            print("SOURCE: local")
            if json_output and payload_json is not None:
                print(json.dumps(payload_json))
            else:
                print(payload_text.rstrip())

        if target == "status":
            text = (
                "Local status:\n"
                f"  groups={len(groups)}\n"
                f"  selectedDevice={selected_device or '(none)'} ({'on' if selected_enabled else 'off'})"
            )
            payload = {
                "source": "local",
                "groupCount": len(groups),
                "selectedDevice": {"device": selected_device, "enabled": selected_enabled},
            }
            _print_local(text, payload)
            return True

        if target == "groups":
            lines = ["Local groups:"]
            for group in groups:
                if not isinstance(group, dict):
                    continue
                name = str(group.get("name", "")).strip()
                enabled = bool(group.get("enabled", True))
                lines.append(f"  {name} ({'enabled' if enabled else 'disabled'})")
            if len(lines) == 1:
                lines.append("  (none)")
            payload = {"source": "local", "groups": groups}
            _print_local("\n".join(lines), payload)
            return True

        if target == "group" and len(tokens) >= 2:
            name = tokens[1]
            match = None
            for group in groups:
                if not isinstance(group, dict):
                    continue
                if str(group.get("name", "")).strip().lower() == name.lower():
                    match = group
                    break
            if match is None:
                print("ERROR: Local group not found.")
                return False
            members = match.get("members", []) or []
            bindings = match.get("bindings", []) or []
            lines = [
                f"Local group {name}:",
                f"  enabled={'true' if match.get('enabled', True) else 'false'}",
                f"  members={len(members)}",
                f"  bindings={len(bindings)}",
            ]
            if members:
                lines.append("  members:")
                for member in members:
                    if isinstance(member, dict):
                        device = str(member.get("device", "")).strip()
                        enabled = bool(member.get("enabled", True))
                    else:
                        device = str(member).strip()
                        enabled = True
                    if device:
                        lines.append(f"    {device} ({'enabled' if enabled else 'disabled'})")
            else:
                lines.append("  members: (none)")
            payload = {"source": "local", "group": match}
            _print_local("\n".join(lines), payload)
            return True

        if target == "devices":
            devices_raw = config.get("devices") if isinstance(config, dict) else None
            lines = ["Local devices:"]
            if isinstance(devices_raw, list) and devices_raw:
                for device in devices_raw:
                    if not isinstance(device, dict):
                        continue
                    name = str(device.get("name", "")).strip()
                    if not name:
                        continue
                    details: List[str] = []
                    if "manufacturer" in device:
                        details.append(self._format_can_meta("mfg", device.get("manufacturer")))
                    if "deviceType" in device:
                        details.append(self._format_can_meta("type", device.get("deviceType")))
                    if "deviceId" in device:
                        details.append(f"id {device.get('deviceId')}")
                    suffix = f" ({', '.join(details)})" if details else ""
                    lines.append(f"  {name}{suffix}")
                payload = {"source": "local", "devices": devices_raw}
            else:
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
                if devices:
                    lines.extend(f"  {name}" for name in devices)
                else:
                    lines.append("  (none)")
                payload = {"source": "local", "devices": devices}
            _print_local("\n".join(lines), payload)
            return True

        if target == "device" and len(tokens) >= 2:
            name = tokens[1]
            devices_raw = config.get("devices") if isinstance(config, dict) else None
            if isinstance(devices_raw, list):
                for device in devices_raw:
                    if not isinstance(device, dict):
                        continue
                    device_name = str(device.get("name", "")).strip()
                    if not device_name or device_name.lower() != name.lower():
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
                    details: List[str] = []
                    if "manufacturer" in device:
                        details.append(
                            f"manufacturer={self._format_can_meta('mfg', device.get('manufacturer'))}"
                        )
                    if "deviceType" in device:
                        details.append(
                            f"deviceType={self._format_can_meta('type', device.get('deviceType'))}"
                        )
                    if "deviceId" in device:
                        details.append(f"deviceId={device.get('deviceId')}")
                    detail_text = " ".join(details)
                    if group_name:
                        text = f"Local device {name}: group={group_name} enabled={enabled} {detail_text}".rstrip()
                    else:
                        text = f"Local device {name}: {detail_text}".rstrip()
                    payload = {"source": "local", "device": device, "group": group_name, "enabled": enabled}
                    _print_local(text, payload)
                    return True
            found_group = ""
            enabled = None
            for group in groups:
                if not isinstance(group, dict):
                    continue
                for member in group.get("members", []) or []:
                    if isinstance(member, dict):
                        device = str(member.get("device", "")).strip()
                        if device.lower() == name.lower():
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
                print("ERROR: Local device not found.")
                return False
            text = f"Local device {name}: group={found_group} enabled={enabled}"
            payload = {"source": "local", "device": name, "group": found_group, "enabled": enabled}
            _print_local(text, payload)
            return True

        if target == "bindings":
            lines = ["Local bindings:"]
            for group in groups:
                if not isinstance(group, dict):
                    continue
                name = str(group.get("name", "")).strip()
                bindings = group.get("bindings", []) or []
                for binding in bindings:
                    if not isinstance(binding, dict):
                        continue
                    line = f"  {name}: {binding.get('input')} {binding.get('kind')}"
                    if "value" in binding:
                        line += f" {binding.get('value')}"
                    lines.append(line)
            if len(lines) == 1:
                lines.append("  (none)")
            payload = {"source": "local", "groups": groups}
            _print_local("\n".join(lines), payload)
            return True

        if target == "selected-device":
            text = (
                "Local selected device: "
                f"{selected_device or '(none)'} ({'on' if selected_enabled else 'off'})"
            )
            payload = {
                "source": "local",
                "selectedDevice": {"device": selected_device, "enabled": selected_enabled},
            }
            _print_local(text, payload)
            return True

        if target == "runtime-state":
            payload = {
                "source": "local",
                "schemaVersion": config.get("schemaVersion", 1) if isinstance(config, dict) else 1,
                "generatedAt": config.get("generatedAt") if isinstance(config, dict) else None,
                "groups": groups,
                "selectedDevice": {"device": selected_device, "enabled": selected_enabled},
            }
            lines = [
                "Local runtime-state:",
                f"  selectedDevice={selected_device or '(none)'} ({'on' if selected_enabled else 'off'})",
                f"  groups={len(groups)}",
            ]
            devices = config.get("devices") if isinstance(config, dict) else None
            grouped_devices = set()
            for group in groups:
                if not isinstance(group, dict):
                    continue
                for member in group.get("members", []) or []:
                    if isinstance(member, dict):
                        name = str(member.get("device", "")).strip()
                    else:
                        name = str(member).strip()
                    if name:
                        grouped_devices.add(name.lower())
            if isinstance(devices, list) and devices:
                lines.append(f"  devices={len(devices)}")
                lines.append("  devices:")
                for device in devices:
                    if not isinstance(device, dict):
                        continue
                    name = str(device.get("name", "")).strip()
                    if not name:
                        continue
                    parts = [name]
                    meta = []
                    manufacturer = device.get("manufacturer")
                    device_type = device.get("deviceType")
                    device_id = device.get("deviceId")
                    if manufacturer:
                        meta.append(str(manufacturer))
                    if device_type:
                        meta.append(str(device_type))
                    if device_id is not None:
                        meta.append(f"id {device_id}")
                    if meta:
                        parts.append(f"({', '.join(meta)})")
                    if name.lower() not in grouped_devices:
                        parts.append("[ungrouped]")
                    lines.append("    " + " ".join(parts))
            else:
                lines.append("  devices=(none)")
            for group in groups:
                if not isinstance(group, dict):
                    continue
                name = str(group.get("name", "")).strip()
                enabled = bool(group.get("enabled", True))
                lines.append(f"  group {name} ({'enabled' if enabled else 'disabled'})")
                members = group.get("members", []) or []
                if members:
                    lines.append("    members:")
                    for member in members:
                        if isinstance(member, dict):
                            device = str(member.get("device", "")).strip()
                            member_enabled = bool(member.get("enabled", True))
                        else:
                            device = str(member).strip()
                            member_enabled = True
                        if device:
                            lines.append(
                                f"      {device} ({'enabled' if member_enabled else 'disabled'})"
                            )
                else:
                    lines.append("    members: (none)")
                bindings = group.get("bindings", []) or []
                if bindings:
                    lines.append("    bindings:")
                    for binding in bindings:
                        if not isinstance(binding, dict):
                            continue
                        line = f"      {binding.get('input')} {binding.get('kind')}"
                        if "value" in binding:
                            line += f" {binding.get('value')}"
                        lines.append(line)
                else:
                    lines.append("    bindings: (none)")
            _print_local("\n".join(lines), payload)
            return True

        print("ERROR: Unknown show command.")
        return False

    def _group_command_local(self, tokens: List[str], group: str) -> Optional[int]:
        if not self._local_config:
            print("ERROR: Local config not loaded. Use merge/import config <bringup_system.json>.")
            return 2 if self._batch else None
        cmd = tokens[0].lower()
        if cmd == "show":
            return self._handle_show(["group", group] + tokens[1:])
        if cmd == "add" and len(tokens) >= 3 and tokens[1].lower() == "device":
            if self._add_local_group_member(group, tokens[2]):
                print("WARNING: Robot not connected; local group member added.")
                return None
            return 2 if self._batch else None
        if cmd == "no" and len(tokens) >= 3 and tokens[1].lower() == "device":
            if self._remove_local_group_member(group, tokens[2]):
                print("WARNING: Robot not connected; local group member removed.")
                return None
            return 2 if self._batch else None
        if cmd == "member" and len(tokens) >= 3:
            action = tokens[2].lower()
            if action in ("enable", "disable", "toggle"):
                if self._set_local_member_enabled(group, tokens[1], action):
                    print("WARNING: Robot not connected; local member updated.")
                    return None
                return 2 if self._batch else None
        if cmd == "bind" and len(tokens) >= 3:
            if self._add_local_binding(group, tokens[1:]):
                print("WARNING: Robot not connected; local binding updated.")
                return None
            return 2 if self._batch else None
        if cmd == "no" and len(tokens) >= 2 and tokens[1].lower() == "bind":
            if self._clear_local_bindings(group):
                print("WARNING: Robot not connected; local bindings cleared.")
                return None
            return 2 if self._batch else None
        if cmd == "enable":
            if self._set_local_group_enabled(group, True):
                print("WARNING: Robot not connected; local group enabled.")
                return None
            return 2 if self._batch else None
        if cmd == "disable":
            if self._set_local_group_enabled(group, False):
                print("WARNING: Robot not connected; local group disabled.")
                return None
            return 2 if self._batch else None
        if cmd == "run" and len(tokens) >= 2 and tokens[1].lower() == "test":
            print("ERROR: Cannot run tests without robot connection.")
            return 2 if self._batch else None
        print(f"ERROR: Unknown command: {' '.join(tokens)}")
        return None

    def _select_or_create_local_group(self, name: str) -> bool:
        if not self._local_config:
            print("ERROR: Local config not loaded. Use merge/import config <bringup_system.json>.")
            return False
        key = name.strip()
        if not key:
            print("ERROR: group name required.")
            return False
        groups = self._local_config.get("groups", [])
        for group in groups:
            if isinstance(group, dict) and str(group.get("name", "")).strip().lower() == key.lower():
                return True
        groups.append({"name": key, "enabled": True, "members": [], "bindings": []})
        self._local_config["groups"] = groups
        return True

    def _delete_local_group(self, name: str) -> bool:
        if not self._local_config:
            print("ERROR: Local config not loaded. Use merge/import config <bringup_system.json>.")
            return False
        key = name.strip().lower()
        groups = self._local_config.get("groups", [])
        kept = []
        removed = False
        for group in groups:
            if not isinstance(group, dict):
                continue
            if str(group.get("name", "")).strip().lower() == key:
                removed = True
                continue
            kept.append(group)
        if not removed:
            print("ERROR: Local group not found.")
            return False
        self._local_config["groups"] = kept
        return True

    def _set_local_selected_device(self, device: str) -> bool:
        if not self._local_config:
            print("ERROR: Local config not loaded. Use merge/import config <bringup_system.json>.")
            return False
        selected = self._local_config.get("selectedDevice", {}) or {}
        enabled = bool(selected.get("enabled", False)) if isinstance(selected, dict) else False
        self._local_config["selectedDevice"] = {"device": device.strip(), "enabled": enabled}
        return True

    def _set_local_selected_mode(self, enabled: bool) -> bool:
        if not self._local_config:
            print("ERROR: Local config not loaded. Use merge/import config <bringup_system.json>.")
            return False
        selected = self._local_config.get("selectedDevice", {}) or {}
        device = str(selected.get("device", "")).strip() if isinstance(selected, dict) else ""
        self._local_config["selectedDevice"] = {"device": device, "enabled": bool(enabled)}
        return True

    def _find_local_group(self, name: str) -> Optional[Dict[str, object]]:
        groups = self._local_config.get("groups", []) if self._local_config else []
        for group in groups:
            if not isinstance(group, dict):
                continue
            if str(group.get("name", "")).strip().lower() == name.lower():
                return group
        return None

    def _add_local_group_member(self, group_name: str, device: str) -> bool:
        group = self._find_local_group(group_name)
        if group is None:
            print("ERROR: Local group not found.")
            return False
        if not self._local_device_exists(device):
            print("ERROR: Device not defined in local config. Use device <name> to create it.")
            return False
        members = group.get("members", [])
        for member in members:
            if isinstance(member, dict):
                name = str(member.get("device", "")).strip()
            else:
                name = str(member).strip()
            if name.lower() == device.lower():
                return True
        members.append({"device": device, "enabled": True})
        group["members"] = members
        return True

    def _remove_local_group_member(self, group_name: str, device: str) -> bool:
        group = self._find_local_group(group_name)
        if group is None:
            print("ERROR: Local group not found.")
            return False
        members = group.get("members", [])
        kept = []
        removed = False
        for member in members:
            if isinstance(member, dict):
                name = str(member.get("device", "")).strip()
            else:
                name = str(member).strip()
            if name.lower() == device.lower():
                removed = True
                continue
            kept.append(member)
        if not removed:
            print("ERROR: Device not in local group.")
            return False
        group["members"] = kept
        return True

    def _set_local_member_enabled(self, group_name: str, device: str, action: str) -> bool:
        group = self._find_local_group(group_name)
        if group is None:
            print("ERROR: Local group not found.")
            return False
        members = group.get("members", [])
        for member in members:
            if isinstance(member, dict):
                name = str(member.get("device", "")).strip()
                if name.lower() == device.lower():
                    enabled = bool(member.get("enabled", True))
                    if action == "enable":
                        member["enabled"] = True
                    elif action == "disable":
                        member["enabled"] = False
                    elif action == "toggle":
                        member["enabled"] = not enabled
                    return True
            elif isinstance(member, str):
                if member.strip().lower() == device.lower():
                    members.remove(member)
                    members.append({"device": member, "enabled": action != "disable"})
                    return True
        print("ERROR: Device not in local group.")
        return False

    def _add_local_binding(self, group_name: str, tokens: List[str]) -> bool:
        if len(tokens) < 2:
            print("ERROR: bind requires input and kind.")
            return False
        group = self._find_local_group(group_name)
        if group is None:
            print("ERROR: Local group not found.")
            return False
        input_name = tokens[0]
        kind = tokens[1]
        entry = {"input": input_name, "kind": kind}
        if kind != "analog":
            if len(tokens) < 3:
                print("ERROR: Button bindings require a value.")
                return False
            entry["value"] = tokens[2]
        bindings = group.get("bindings", [])
        bindings.append(entry)
        group["bindings"] = bindings
        return True

    def _clear_local_bindings(self, group_name: str) -> bool:
        group = self._find_local_group(group_name)
        if group is None:
            print("ERROR: Local group not found.")
            return False
        group["bindings"] = []
        return True

    def _set_local_group_enabled(self, group_name: str, enabled: bool) -> bool:
        group = self._find_local_group(group_name)
        if group is None:
            print("ERROR: Local group not found.")
            return False
        group["enabled"] = bool(enabled)
        return True

    def _rename_local_device(self, old: str, new: str) -> bool:
        if not self._local_config:
            print("ERROR: Local config not loaded. Use merge/import config <bringup_system.json>.")
            return False
        if self._local_devices_locked:
            return self._rename_profiles_device(old, new)
        old_name = old.strip()
        new_name = new.strip()
        if not old_name or not new_name:
            print("ERROR: rename device requires old and new names.")
            return False
        if old_name.lower() == new_name.lower():
            print("ERROR: New name matches existing name.")
            return False
        config = self._local_config
        devices = config.get("devices") if isinstance(config, dict) else None
        existing_names = set()
        if isinstance(devices, list):
            for device in devices:
                if isinstance(device, dict):
                    name = str(device.get("name", "")).strip()
                    if name:
                        existing_names.add(name.lower())
        for group in config.get("groups", []) if isinstance(config, dict) else []:
            if not isinstance(group, dict):
                continue
            for member in group.get("members", []) or []:
                if isinstance(member, dict):
                    name = str(member.get("device", "")).strip()
                else:
                    name = str(member).strip()
                if name:
                    existing_names.add(name.lower())
        selected = config.get("selectedDevice") if isinstance(config, dict) else {}
        if isinstance(selected, dict):
            sel_name = str(selected.get("device", "")).strip()
            if sel_name:
                existing_names.add(sel_name.lower())
        if new_name.lower() in existing_names:
            print(f"ERROR: Device name {new_name} already exists.")
            return False

        changed = False
        if isinstance(devices, list):
            for device in devices:
                if not isinstance(device, dict):
                    continue
                name = str(device.get("name", "")).strip()
                if name.lower() == old_name.lower():
                    device["name"] = new_name
                    changed = True
        for group in config.get("groups", []) if isinstance(config, dict) else []:
            if not isinstance(group, dict):
                continue
            for member in group.get("members", []) or []:
                if isinstance(member, dict):
                    name = str(member.get("device", "")).strip()
                    if name.lower() == old_name.lower():
                        member["device"] = new_name
                        changed = True
                elif isinstance(member, str):
                    if member.strip().lower() == old_name.lower():
                        index = group["members"].index(member)
                        group["members"][index] = new_name
                        changed = True
        if isinstance(selected, dict):
            sel_name = str(selected.get("device", "")).strip()
            if sel_name.lower() == old_name.lower():
                selected["device"] = new_name
                changed = True
        if not changed:
            print(f"ERROR: Device {old_name} not found in local config.")
            return False
        return True

    def _rename_profiles_device(self, old: str, new: str) -> bool:
        """
        NAME
            _rename_profiles_device - Rename a device label inside profiles.
        """
        entry = self._find_profiles_device_entry(old)
        if entry is None:
            print(f"ERROR: Device {old} not found in profiles.")
            return False
        new_label = new.strip()
        if not new_label:
            print("ERROR: new device name required.")
            return False
        entry["label"] = new_label
        self._profiles_dirty = True
        self._update_diagram_label(entry, new_label)
        self._update_bridge_groups_label(old, new_label)
        self._refresh_devices_from_profiles()
        return True

    def _update_bridge_groups_label(self, old: str, new: str) -> None:
        """
        NAME
            _update_bridge_groups_label - Update bridgeConfig group members after rename.
        """
        config = self._local_config
        if not isinstance(config, dict):
            return
        changed = False
        for group in config.get("groups", []) if isinstance(config.get("groups"), list) else []:
            if not isinstance(group, dict):
                continue
            for member in group.get("members", []) or []:
                if isinstance(member, dict):
                    name = str(member.get("device", "")).strip()
                    if name.lower() == old.lower():
                        member["device"] = new
                        changed = True
                elif isinstance(member, str):
                    if member.strip().lower() == old.lower():
                        index = group["members"].index(member)
                        group["members"][index] = new
                        changed = True
        selected = config.get("selectedDevice")
        if isinstance(selected, dict):
            sel_name = str(selected.get("device", "")).strip()
            if sel_name.lower() == old.lower():
                selected["device"] = new
                changed = True
        if changed:
            self._local_config = config

    def _update_diagram_label(self, entry: Dict[str, object], new_label: str) -> None:
        payload = self._local_root_payload
        if not isinstance(payload, dict):
            return
        profiles, profile_name = self._profiles_root_and_name()
        if profiles is None or profile_name is None:
            return
        profile = profiles.get(profile_name)
        if not isinstance(profile, dict):
            return
        category = self._find_entry_category(profile, entry)
        if category is None:
            return
        device_id = entry.get("id")
        if device_id is None:
            return
        diagram = payload.get("diagram")
        if not isinstance(diagram, dict):
            return
        diag_profiles = diagram.get("profiles")
        if not isinstance(diag_profiles, dict):
            return
        diag_profile = diag_profiles.get(profile_name)
        if not isinstance(diag_profile, dict):
            return
        nodes = diag_profile.get("nodes")
        if not isinstance(nodes, list):
            return
        for node in nodes:
            if not isinstance(node, dict):
                continue
            if node.get("nodeType") != "device":
                continue
            if node.get("category") == category and node.get("id") == device_id:
                node["label"] = new_label

    def _find_entry_category(self, profile: Dict[str, object], entry: Dict[str, object]) -> Optional[str]:
        for key in (
            "neos",
            "neo550s",
            "flexes",
            "krakens",
            "falcons",
            "cancoders",
            "candles",
        ):
            if entry in (profile.get(key) or []):
                return key
        for key in ("pdh", "pdp", "pigeon", "roborio"):
            if profile.get(key) is entry:
                return key
        if entry in (profile.get("devices") or []):
            return "devices"
        return None

    def _set_local_device_meta(self, name: str, field: str, value_raw: str) -> bool:
        """
        NAME
            _set_local_device_meta - Update manufacturer/deviceType/deviceId for a local device.
        """
        if not self._local_config:
            print("ERROR: Local config not loaded. Use merge/import config <bringup_system.json>.")
            return False
        if self._local_devices_locked:
            return self._set_profiles_device_meta(name, field_key, value_raw)
        field_key = field.strip()
        if field_key not in (
            "manufacturer",
            "deviceType",
            "deviceId",
            "vendor",
            "role",
            "notes",
            "bus",
            "tags",
            "limits",
        ):
            print(
                "ERROR: device set field must be manufacturer, deviceType, deviceId, "
                "vendor, role, notes, bus, tags, or limits."
            )
            return False
        value: object
        if field_key in ("manufacturer", "deviceType"):
            resolved = self._resolve_can_id(field_key, value_raw)
            if resolved is None:
                return False
            value = resolved
        elif field_key in ("deviceId", "bus"):
            try:
                value = int(value_raw, 0)
            except ValueError:
                print("ERROR: device set value must be an integer (decimal or 0x..).")
                return False
        elif field_key in ("tags", "limits"):
            parsed = parse_json_arg(value_raw)
            if parsed is None:
                print("ERROR: device set value must be valid JSON for tags/limits.")
                return False
            if field_key == "tags" and not isinstance(parsed, list):
                print("ERROR: tags must be a JSON list.")
                return False
            if field_key == "limits" and not isinstance(parsed, dict):
                print("ERROR: limits must be a JSON object.")
                return False
            value = parsed
        else:
            value = value_raw
        config = self._local_config
        devices = config.get("devices")
        if not isinstance(devices, list):
            devices = []
            config["devices"] = devices
        target = None
        for device in devices:
            if not isinstance(device, dict):
                continue
            dev_name = str(device.get("name", "")).strip()
            if dev_name.lower() == name.strip().lower():
                target = device
                break
        if target is None:
            # Allow metadata edits for devices already referenced by groups.
            if not self._device_in_groups(name):
                print("ERROR: Device not found in local config or groups.")
                return False
            target = {"name": name.strip()}
            devices.append(target)
        target[field_key] = value
        return True

    def _clear_local_device_meta(self, name: str, field: str) -> bool:
        """
        NAME
            _clear_local_device_meta - Clear manufacturer/deviceType/deviceId for a local device.
        """
        if not self._local_config:
            print("ERROR: Local config not loaded. Use merge/import config <bringup_system.json>.")
            return False
        if self._local_devices_locked:
            return self._clear_profiles_device_meta(name, field_key)
        field_key = field.strip()
        if field_key not in (
            "manufacturer",
            "deviceType",
            "deviceId",
            "vendor",
            "role",
            "notes",
            "bus",
            "tags",
            "limits",
        ):
            print(
                "ERROR: device clear field must be manufacturer, deviceType, deviceId, "
                "vendor, role, notes, bus, tags, or limits."
            )
            return False
        devices = self._local_config.get("devices")
        if not isinstance(devices, list):
            print("ERROR: No local devices are defined.")
            return False
        for device in devices:
            if not isinstance(device, dict):
                continue
            dev_name = str(device.get("name", "")).strip()
            if dev_name.lower() == name.strip().lower():
                if field_key in device:
                    device.pop(field_key, None)
                return True
        print("ERROR: Device not found in local config.")
        return False

    def _ensure_local_device_entry(self, name: str) -> bool:
        """
        NAME
            _ensure_local_device_entry - Ensure a local device entry exists.
        """
        if not self._local_config:
            print("ERROR: Local config not loaded. Use merge/import config <bringup_system.json>.")
            return False
        if self._local_devices_locked:
            return self._ensure_profiles_device_entry(name)
        config = self._local_config
        devices = config.get("devices")
        if not isinstance(devices, list):
            devices = []
            config["devices"] = devices
        for device in devices:
            if not isinstance(device, dict):
                continue
            dev_name = str(device.get("name", "")).strip()
            if dev_name.lower() == name.strip().lower():
                return True
        devices.append({"name": name.strip()})
        return True

    def _show_local_device_entry(self, name: str) -> Optional[int]:
        """
        NAME
            _show_local_device_entry - Print the local device metadata.
        """
        if not self._local_config:
            print("ERROR: Local config not loaded. Use merge/import config <bringup_system.json>.")
            return None
        devices = self._local_config.get("devices")
        if not isinstance(devices, list):
            print("ERROR: No local devices are defined.")
            return None
        for device in devices:
            if not isinstance(device, dict):
                continue
            dev_name = str(device.get("name", "")).strip()
            if dev_name.lower() == name.strip().lower():
                parts = [f"Local device {dev_name}:"]
                manufacturer = device.get("manufacturer")
                device_type = device.get("deviceType")
                device_id = device.get("deviceId")
                vendor = device.get("vendor")
                role = device.get("role")
                notes = device.get("notes")
                bus = device.get("bus")
                tags = device.get("tags")
                limits = device.get("limits")
                if manufacturer is not None:
                    mfg_name = self._can_mfg_id_to_name.get(int(manufacturer))
                    suffix = f" ({mfg_name})" if mfg_name else ""
                    parts.append(f"  manufacturer={manufacturer}{suffix}")
                if device_type is not None:
                    type_name = self._can_type_id_to_name.get(int(device_type))
                    suffix = f" ({type_name})" if type_name else ""
                    parts.append(f"  deviceType={device_type}{suffix}")
                if device_id is not None:
                    parts.append(f"  deviceId={device_id}")
                if vendor is not None:
                    parts.append(f"  vendor={vendor}")
                if role is not None:
                    parts.append(f"  role={role}")
                if notes is not None:
                    parts.append(f"  notes={notes}")
                if bus is not None:
                    parts.append(f"  bus={bus}")
                if tags is not None:
                    parts.append(f"  tags={tags}")
                if limits is not None:
                    parts.append(f"  limits={limits}")
                if len(parts) == 1:
                    parts.append("  (no metadata)")
                print("\n".join(parts))
                return None
        print("ERROR: Device not found in local config.")
        return None

    def _save_profiles(self, path: str) -> bool:
        """
        NAME
            _save_profiles - Save updated bringup_system.json.
        """
        if not self._local_devices_locked or self._local_root_payload is None:
            print("ERROR: No profiles are loaded.")
            return False
        payload = dict(self._local_root_payload)
        payload["schema_version"] = 3
        payload["data_version"] = timestamp_version()
        payload["data_hash"] = compute_profiles_hash(payload)
        try:
            write_json(Path(path), payload, indent=2, trailing_newline=True)
        except Exception as exc:
            print(f"ERROR: Failed to write {path}: {exc}")
            return False
        self._profiles_dirty = False
        print(f"Wrote profiles to {path}.")
        return True

    def _ensure_profiles_device_entry(self, name: str) -> bool:
        """
        NAME
            _ensure_profiles_device_entry - Create a generic device in profiles if missing.
        """
        entry = self._find_profiles_device_entry(name)
        if entry is not None:
            return True
        profiles, profile_name = self._profiles_root_and_name()
        if profiles is None or profile_name is None:
            return False
        profile = profiles.get(profile_name)
        if not isinstance(profile, dict):
            return False
        devices = profile.get("devices")
        if not isinstance(devices, list):
            devices = []
            profile["devices"] = devices
        devices.append({"label": name.strip(), "id": -1})
        self._profiles_dirty = True
        self._refresh_devices_from_profiles()
        return True

    def _set_profiles_device_meta(self, name: str, field: str, value_raw: str) -> bool:
        """
        NAME
            _set_profiles_device_meta - Update a device entry inside profiles.
        """
        entry = self._find_profiles_device_entry(name)
        if entry is None:
            if not self._ensure_profiles_device_entry(name):
                return False
            entry = self._find_profiles_device_entry(name)
            if entry is None:
                return False
        if field in ("manufacturer", "deviceType"):
            # Only generic devices can change vendor/type; bucketed devices are derived.
            if not self._is_generic_profiles_entry(entry):
                print("ERROR: manufacturer/deviceType are derived from profile category.")
                return False
            resolved = self._resolve_can_id(field, value_raw)
            if resolved is None:
                return False
            if field == "manufacturer":
                name_val = self._can_mfg_id_to_name.get(int(resolved))
                if not name_val:
                    print("ERROR: Unknown manufacturer ID.")
                    return False
                entry["vendor"] = name_val
            else:
                name_val = self._can_type_id_to_name.get(int(resolved))
                if not name_val:
                    print("ERROR: Unknown deviceType ID.")
                    return False
                entry["type"] = name_val
        elif field == "deviceId":
            try:
                entry["id"] = int(value_raw, 0)
            except ValueError:
                print("ERROR: deviceId must be an integer (decimal or 0x..).")
                return False
        elif field == "vendor":
            entry["vendor"] = value_raw
        elif field == "role":
            entry["role"] = value_raw
        elif field == "notes":
            entry["notes"] = value_raw
        elif field == "bus":
            try:
                entry["bus"] = int(value_raw, 0)
            except ValueError:
                print("ERROR: bus must be an integer (decimal or 0x..).")
                return False
        elif field == "tags":
            parsed = parse_json_arg(value_raw)
            if parsed is None or not isinstance(parsed, list):
                print("ERROR: tags must be a JSON list.")
                return False
            entry["tags"] = parsed
        elif field == "limits":
            parsed = parse_json_arg(value_raw)
            if parsed is None or not isinstance(parsed, dict):
                print("ERROR: limits must be a JSON object.")
                return False
            entry["limits"] = parsed
        else:
            entry[field] = value_raw
        self._profiles_dirty = True
        self._refresh_devices_from_profiles()
        return True

    def _clear_profiles_device_meta(self, name: str, field: str) -> bool:
        """
        NAME
            _clear_profiles_device_meta - Clear a device field in profiles.
        """
        entry = self._find_profiles_device_entry(name)
        if entry is None:
            print("ERROR: Device not found in profiles.")
            return False
        if field in ("manufacturer", "deviceType"):
            print("ERROR: manufacturer/deviceType are derived from profile category.")
            return False
        if field == "deviceId":
            entry["id"] = -1
        else:
            entry.pop(field, None)
        self._profiles_dirty = True
        self._refresh_devices_from_profiles()
        return True

    def _find_profiles_device_entry(self, name: str) -> Optional[Dict[str, object]]:
        profiles, profile_name = self._profiles_root_and_name()
        if profiles is None or profile_name is None:
            return None
        profile = profiles.get(profile_name)
        if not isinstance(profile, dict):
            return None
        label = name.strip().lower()
        for key in (
            "neos",
            "neo550s",
            "flexes",
            "krakens",
            "falcons",
            "cancoders",
            "candles",
        ):
            for entry in profile.get(key, []) or []:
                if isinstance(entry, dict) and str(entry.get("label", "")).strip().lower() == label:
                    return entry
        for key in ("pdh", "pdp", "pigeon", "roborio"):
            entry = profile.get(key)
            if isinstance(entry, dict) and str(entry.get("label", "")).strip().lower() == label:
                return entry
        for entry in profile.get("devices", []) or []:
            if isinstance(entry, dict) and str(entry.get("label", "")).strip().lower() == label:
                return entry
        return None

    def _is_generic_profiles_entry(self, entry: Dict[str, object]) -> bool:
        profiles, profile_name = self._profiles_root_and_name()
        if profiles is None or profile_name is None:
            return False
        profile = profiles.get(profile_name)
        if not isinstance(profile, dict):
            return False
        devices = profile.get("devices")
        if not isinstance(devices, list):
            return False
        return entry in devices

    def _profiles_root_and_name(self) -> tuple[Optional[Dict[str, object]], Optional[str]]:
        payload = self._local_root_payload
        if not isinstance(payload, dict):
            return (None, None)
        profiles = payload.get("profiles")
        if not isinstance(profiles, dict) or not profiles:
            return (None, None)
        default_profile = payload.get("default_profile")
        if not isinstance(default_profile, str) or default_profile not in profiles:
            default_profile = next(iter(profiles.keys()))
        return (profiles, default_profile)

    def _refresh_devices_from_profiles(self) -> None:
        if not self._local_root_payload or not self._local_config:
            return
        devices = devices_from_profiles_payload(self._local_root_payload)
        if devices is None:
            return
        self._local_config["devices"] = devices
    def _export_cli_script(self, path: str) -> bool:
        """
        NAME
            _export_cli_script - Write a CLI batch script for the local config.

        DESCRIPTION
            Emits a plain-text command script that recreates the local
            bridgeConfig when run in batch mode.

        PARAMETERS
            path: Output file path for the script.
        """
        if not self._local_config:
            print("ERROR: Local config not loaded. Use merge/import config <bringup_system.json>.")
            return False
        config = self._local_config
        lines: List[str] = []
        if self._local_devices_locked:
            if self._local_root_path:
                lines.append(f'merge config "{self._local_root_path}"')
            else:
                lines.append("# NOTE: devices are derived from profiles; merge a profiles file first.")
        lines.append("configure terminal")
        devices = config.get("devices") if isinstance(config, dict) else None
        if isinstance(devices, list) and not self._local_devices_locked:
            for device in devices:
                if not isinstance(device, dict):
                    continue
                name = str(device.get("name", "")).strip()
                if not name:
                    continue
                meta = []
                if "manufacturer" in device:
                    meta.append(("manufacturer", device.get("manufacturer")))
                if "deviceType" in device:
                    meta.append(("deviceType", device.get("deviceType")))
                if "deviceId" in device:
                    meta.append(("deviceId", device.get("deviceId")))
                if "vendor" in device:
                    meta.append(("vendor", device.get("vendor")))
                if "role" in device:
                    meta.append(("role", device.get("role")))
                if "notes" in device:
                    meta.append(("notes", device.get("notes")))
                if "bus" in device:
                    meta.append(("bus", device.get("bus")))
                if "tags" in device:
                    meta.append(("tags", device.get("tags")))
                if "limits" in device:
                    meta.append(("limits", device.get("limits")))
                lines.append(f'device "{name}"')
                for field, value in meta:
                    if field in ("tags", "limits"):
                        encoded = json.dumps(value, separators=(",", ":"))
                        lines.append(f"set {field} {encoded}")
                    else:
                        lines.append(f"set {field} {value}")
                lines.append("exit")
        groups = config.get("groups", []) if isinstance(config, dict) else []
        for group in groups:
            if not isinstance(group, dict):
                continue
            name = str(group.get("name", "")).strip()
            if not name:
                continue
            lines.append(f"group {name}")
            members = group.get("members", []) or []
            for member in members:
                if isinstance(member, dict):
                    device = str(member.get("device", "")).strip()
                    enabled = bool(member.get("enabled", True))
                else:
                    device = str(member).strip()
                    enabled = True
                if not device:
                    continue
                lines.append(f'add device "{device}"')
                if not enabled:
                    lines.append(f'member "{device}" disable')
            bindings = group.get("bindings", []) or []
            for binding in bindings:
                if not isinstance(binding, dict):
                    continue
                input_name = str(binding.get("input", "")).strip()
                kind = str(binding.get("kind", "")).strip()
                if not input_name or not kind:
                    continue
                if "value" in binding:
                    lines.append(f"bind {input_name} {kind} {binding.get('value')}")
                else:
                    lines.append(f"bind {input_name} {kind}")
            if group.get("enabled") is False:
                lines.append("disable")
            lines.append("exit")
        selected = config.get("selectedDevice", {}) if isinstance(config, dict) else {}
        if isinstance(selected, dict):
            sel_name = str(selected.get("device", "")).strip()
            if sel_name:
                lines.append(f'selected-device "{sel_name}"')
            if selected.get("enabled") is True:
                lines.append("selected-mode on")
            elif selected.get("enabled") is False:
                lines.append("selected-mode off")
        try:
            Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
        except Exception as exc:
            print(f"ERROR: Failed to write {path}: {exc}")
            return False
        print(f"Wrote CLI script to {path}.")
        return True

    def _lint_script(self, lines: List[str]) -> Optional[str]:
        """
        NAME
            _lint_script - Validate script ordering and device references.
        """
        known_devices = set()
        mode_stack: List[str] = ["exec"]
        for raw in lines:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            try:
                tokens = self._split_command(line)
            except ValueError as exc:
                return f"Invalid command syntax: {line} ({exc})"
            if not tokens:
                continue
            cmd = tokens[0].lower()
            if cmd == "configure" and len(tokens) > 1 and tokens[1].lower() == "terminal":
                mode_stack.append("config")
                continue
            if cmd == "group" and len(tokens) >= 2 and mode_stack[-1] == "config":
                mode_stack.append("group")
                continue
            if cmd == "device" and len(tokens) >= 2 and mode_stack[-1] == "config":
                known_devices.add(tokens[1].strip().lower())
                mode_stack.append("device")
                continue
            if cmd == "exit":
                if len(mode_stack) > 1:
                    mode_stack.pop()
                continue
            if cmd == "end":
                mode_stack = ["exec"]
                continue
            if cmd == "merge" and len(tokens) >= 3 and tokens[1].lower() == "config":
                ok, message, config = validate_config_file(tokens[2])
                if not ok:
                    return message
                if config:
                    devices = config.get("devices")
                    if isinstance(devices, list):
                        for device in devices:
                            if not isinstance(device, dict):
                                continue
                            name = str(device.get("name", "")).strip()
                            if name:
                                known_devices.add(name.lower())
                continue
            if cmd == "import" and len(tokens) >= 3 and tokens[1].lower() == "config":
                ok, message, config = validate_config_file(tokens[2])
                if not ok:
                    return message
                if config:
                    devices = config.get("devices")
                    if isinstance(devices, list):
                        for device in devices:
                            if not isinstance(device, dict):
                                continue
                            name = str(device.get("name", "")).strip()
                            if name:
                                known_devices.add(name.lower())
                continue
            if cmd == "add" and len(tokens) >= 3 and tokens[1].lower() == "device":
                device = tokens[2].strip().lower()
                if device not in known_devices:
                    return f"Device '{tokens[2]}' not defined before add device."
        return None

    @staticmethod
    def _split_command(line: str) -> List[str]:
        """
        NAME
            _split_command - Split a CLI line without backslash escapes.
        """
        lexer = shlex.shlex(line, posix=True)
        lexer.whitespace_split = True
        lexer.escape = ""
        lexer.escapechar = ""
        return list(lexer)

    def _device_in_groups(self, name: str) -> bool:
        """
        NAME
            _device_in_groups - Check if a device name is referenced in any group.
        """
        config = self._local_config or {}
        for group in config.get("groups", []) if isinstance(config, dict) else []:
            if not isinstance(group, dict):
                continue
            for member in group.get("members", []) or []:
                if isinstance(member, dict):
                    dev_name = str(member.get("device", "")).strip()
                else:
                    dev_name = str(member).strip()
                if dev_name.lower() == name.strip().lower():
                    return True
        return False

    @staticmethod
    def _ordered_bridge_config(config: Dict[str, object], include_devices: bool = True) -> Dict[str, object]:
        """
        NAME
            _ordered_bridge_config - Normalize bridgeConfig key order for output.
        """
        ordered: Dict[str, object] = {
            "schemaVersion": config.get("schemaVersion", 1),
            "generatedAt": config.get("generatedAt"),
        }
        if include_devices:
            ordered["devices"] = (
                list(config.get("devices", [])) if isinstance(config.get("devices"), list) else []
            )
        ordered["groups"] = (
            list(config.get("groups", [])) if isinstance(config.get("groups"), list) else []
        )
        ordered["selectedDevice"] = config.get("selectedDevice", {"device": "", "enabled": False})
        return ordered

    def _local_device_exists(self, name: str) -> bool:
        """
        NAME
            _local_device_exists - Check if a device entry exists in local config.
        """
        config = self._local_config or {}
        devices = config.get("devices") if isinstance(config, dict) else None
        if not isinstance(devices, list):
            return False
        for device in devices:
            if not isinstance(device, dict):
                continue
            dev_name = str(device.get("name", "")).strip()
            if dev_name.lower() == name.strip().lower():
                return True
        return False

    def _resolve_can_id(self, field: str, value_raw: str) -> Optional[int]:
        """
        NAME
            _resolve_can_id - Resolve manufacturer/deviceType from numeric or name.
        """
        raw = value_raw.strip()
        try:
            return int(raw, 0)
        except ValueError:
            pass
        key = raw.lower()
        if field == "manufacturer":
            if key in self._can_mfg_name_to_id:
                return self._can_mfg_name_to_id[key]
            print("ERROR: Unknown manufacturer name.")
            return None
        if field == "deviceType":
            if key in self._can_type_name_to_id:
                return self._can_type_name_to_id[key]
            print("ERROR: Unknown deviceType name.")
            return None
        print("ERROR: Unsupported field for name resolution.")
        return None

    def _load_can_mappings(self) -> None:
        """
        NAME
            _load_can_mappings - Load CAN manufacturer/device type name maps.
        """
        repo_root = Path(__file__).resolve().parents[2]
        mapping_path = repo_root / "src" / "main" / "deploy" / "can_mappings.json"
        try:
            payload = json.loads(mapping_path.read_text(encoding="utf-8"))
        except Exception:
            return
        manufacturers = payload.get("manufacturers", {})
        device_types = payload.get("device_types", {})
        if isinstance(manufacturers, dict):
            for key, value in manufacturers.items():
                try:
                    mid = int(key)
                except Exception:
                    continue
                name = str(value)
                self._can_mfg_id_to_name[mid] = name
                self._can_mfg_name_to_id[name.lower()] = mid
        if isinstance(device_types, dict):
            for key, value in device_types.items():
                try:
                    tid = int(key)
                except Exception:
                    continue
                name = str(value)
                self._can_type_id_to_name[tid] = name
                self._can_type_name_to_id[name.lower()] = tid

    def _ensure_local_config(self) -> None:
        """
        NAME
            _ensure_local_config - Initialize an empty local bridgeConfig if missing.
        """
        if self._local_config is None:
            self._local_config = {
                "schemaVersion": 1,
                "generatedAt": None,
                "devices": [],
                "groups": [],
                "selectedDevice": {"device": "", "enabled": False},
            }
            self._local_devices_locked = False
            self._profiles_dirty = False

    def _profiles_from_local_devices(self) -> Dict[str, object]:
        """
        NAME
            _profiles_from_local_devices - Build a minimal profiles payload from local devices.
        """
        devices_out: List[Dict[str, object]] = []
        config = self._local_config or {}
        for device in config.get("devices", []) if isinstance(config, dict) else []:
            if not isinstance(device, dict):
                continue
            name = str(device.get("name", "")).strip()
            if not name:
                continue
            entry: Dict[str, object] = {"label": name}
            device_id = device.get("deviceId")
            entry["id"] = int(device_id) if device_id is not None else -1
            vendor = device.get("vendor")
            if not vendor:
                manufacturer = device.get("manufacturer")
                if manufacturer is not None:
                    vendor = self._can_mfg_id_to_name.get(int(manufacturer))
            if not vendor:
                vendor = "Unknown"
            entry["vendor"] = vendor
            dtype = device.get("deviceType")
            type_name = None
            if dtype is not None:
                type_name = self._can_type_id_to_name.get(int(dtype))
            if not type_name:
                role = device.get("role")
                if role:
                    type_name = str(role)
            if not type_name:
                type_name = "Unknown"
            entry["type"] = type_name
            for key in ("role", "notes", "bus", "tags", "limits"):
                if key in device:
                    entry[key] = device.get(key)
            devices_out.append(entry)
        profile = {"devices": devices_out}
        return {
            "default_profile": "robot",
            "profiles": {"robot": profile},
            "diagram": {"profiles": {}},
        }

    def _build_unified_payload(self) -> Optional[Dict[str, object]]:
        """
        NAME
            _build_unified_payload - Build a bringup_system.json payload from local state.
        """
        if not self._local_config:
            print("ERROR: Local config not loaded. Use merge/import config <bringup_system.json>.")
            return None
        payload: Dict[str, object] = deepcopy(self._local_root_payload) if self._local_root_payload else {}
        if "profiles" not in payload:
            payload.update(self._profiles_from_local_devices())
        if "diagram" not in payload:
            payload["diagram"] = {"profiles": {}}
        payload.setdefault("default_profile", "robot")
        payload["schema_version"] = 3
        payload["bridgeConfig"] = self._ordered_bridge_config(
            self._local_config, include_devices=False
        )
        if self._profiles_dirty or "data_version" not in payload:
            payload["data_version"] = timestamp_version()
        payload["data_hash"] = compute_profiles_hash(payload)
        return payload

    def _save_unified_config(self, path: str) -> bool:
        """
        NAME
            _save_unified_config - Save a unified bringup_system.json payload.
        """
        payload = self._build_unified_payload()
        if payload is None:
            return False
        try:
            write_json(Path(path), payload, indent=2, trailing_newline=True)
        except Exception as exc:
            print(f"ERROR: Failed to write {path}: {exc}")
            return False
        self._profiles_dirty = False
        print(f"Wrote unified config to {path}.")
        return True

    def _save_local_config(self, path: str) -> bool:
        if not self._local_config:
            print("ERROR: Local config not loaded. Use merge/import config <bringup_system.json>.")
            return False
        try:
            config_out = self._ordered_bridge_config(
                self._local_config, include_devices=not self._local_devices_locked
            )
            write_json(Path(path), config_out, indent=2, trailing_newline=True)
        except Exception as exc:
            print(f"ERROR: Failed to write {path}: {exc}")
            return False
        if self._local_devices_locked:
            print(f"Wrote groups config to {path}.")
        else:
            print(f"Wrote bridgeConfig to {path}.")
        return True
