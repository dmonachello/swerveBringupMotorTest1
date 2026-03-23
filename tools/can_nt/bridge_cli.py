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
from dataclasses import dataclass
from typing import List, Optional

from tools.can_nt.bridge_ops import (
    connect,
    disconnect,
    export_runtime_groups,
    BridgeCommand,
    ConfigPlan,
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


@dataclass
class CliMode:
    name: str
    group: str = ""


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
                return 0
            except KeyboardInterrupt:
                print()
                continue
            line = line.strip()
            if not line:
                continue
            code = self._execute_line(line)
            if code is not None:
                return code

    def run_batch(self, lines: List[str]) -> int:
        """
        NAME
            run_batch - Execute a batch script.
        """
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
        return "bridge> "

    def _execute_line(self, line: str) -> Optional[int]:
        tokens = shlex.split(line)
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
            self._modes.append(CliMode("config"))
            return None
        if cmd == "show":
            return self._handle_show(tokens[1:])
        print(f"ERROR: Unknown command: {' '.join(tokens)}")
        return None

    def _config_command(self, tokens: List[str]) -> Optional[int]:
        cmd = tokens[0].lower()
        if cmd == "group" and len(tokens) >= 2:
            name = tokens[1]
            seq = group_create(self._session, name)
            event = self._wait_for_seq(seq)
            if self._event_failed(event, "group create"):
                return 2 if self._batch else None
            self._modes.append(CliMode("group", name))
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
        if cmd == "selected-device" and len(tokens) >= 2:
            seq = selected_device_set(self._session, tokens[1])
            event = self._wait_for_seq(seq)
            if self._event_failed(event, "selected-device"):
                return 2 if self._batch else None
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
        if cmd == "save" and len(tokens) >= 3 and tokens[1].lower() == "config":
            result = save_config(self._session, tokens[2])
            print(result.message)
            return 2 if not result.ok else None
        if cmd == "show":
            return self._handle_show(tokens[1:])
        print(f"ERROR: Unknown command: {' '.join(tokens)}")
        return None

    def _group_command(self, tokens: List[str]) -> Optional[int]:
        group = self._modes[-1].group
        cmd = tokens[0].lower()
        if cmd == "show":
            if len(tokens) == 1:
                seq = show_group(self._session, group, json_output=self._has_json(tokens))
            elif tokens[1].lower() == "members":
                seq = show_group(self._session, group, json_output=self._has_json(tokens))
            elif tokens[1].lower() == "binding":
                seq = show_group(self._session, group, json_output=self._has_json(tokens))
            else:
                print("ERROR: Unknown show target.")
                return None
            event = self._wait_for_seq(seq)
            if self._event_failed(event, "show group"):
                return 2 if self._batch else None
            return None
        if cmd == "add" and len(tokens) >= 3 and tokens[1].lower() == "device":
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

    def _handle_show(self, tokens: List[str]) -> Optional[int]:
        if not tokens:
            print("ERROR: show requires a target.")
            return None
        target = tokens[0].lower()
        json_output = self._has_json(tokens)
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
            return None
        event = self._wait_for_seq(seq)
        if self._event_failed(event, "show"):
            return 2 if self._batch else None
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
            if event.text:
                print(event.text.rstrip())
            elif event.json_text:
                print(event.json_text.rstrip())
            return

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
                    "show <status|groups|group <name>|devices|device <name>|bindings|selected-device|runtime-state> [--json]\n"
                    "  Prints state from the robot. Use --json for structured output."
                ),
                "configure terminal": "configure terminal\n  Enter config mode.",
                "connect": "connect\n  Open TCP connection and perform handshake.",
                "disconnect": "disconnect\n  Close TCP connection.",
                "group": "group <name>\n  Create/select a group (config mode).",
                "no group": "no group <name>\n  Delete group (config mode, prompts in interactive).",
                "selected-device": "selected-device <device>\n  Set selected-device override.",
                "selected-mode": "selected-mode <on|off>\n  Enable/disable selected-device mode.",
                "merge config": "merge config <file>\n  Add groups from file without clearing existing.",
                "import config": "import config <file>\n  Replace groups from file (prompts in interactive).",
                "export runtime-groups": "export runtime-groups <file>\n  Export current runtime groups to file.",
                "save config": "save config <file>\n  Save runtime state to config file.",
                "add device": "add device <device>\n  Add device to current group.",
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
                "batch": "use --batch --script <file> (no prompts, conflict policy applies)",
                "conflict-policy": "set with --conflict-policy <error|move>",
                "exec": "exec mode: show, connect, disconnect, configure terminal",
                "config": "config mode: group, no group, selected-device, selected-mode, merge/import/export/save",
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
            "Config: group, no group, selected-device, selected-mode, merge/import/export/save\n"
            "Group: show, add device, no device, member, bind, no bind, enable, disable, run test\n"
            "Tips: help show | help group | help batch | help json"
        )
