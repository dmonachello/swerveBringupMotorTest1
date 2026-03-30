from __future__ import annotations

"""
NAME
    bridge_cli_ast.py - AST-native executor for the Bridge CLI.

SYNOPSIS
    executor = BridgeCliAstExecutor(cli)
    return executor.execute(ast)

DESCRIPTION
    Executes Bridge CLI commands from the AST without re-parsing tokens.
    This module is isolated to keep bridge_cli.py merge diffs minimal.
"""

from typing import Dict, Optional

from tools.can_nt.bridge_cli_parser import CommandAst, SPEC
from tools.can_nt.bridge_ops import (
    connect,
    disconnect,
    export_runtime_groups,
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


AST_EXEC_SPEC = {
    "ret_ok": 0,
    "ret_err": 2,
    "msg_err_unknown_cmd": "ERROR: Unknown command.",
    "msg_err_show_requires": "ERROR: show requires a target.",
    "msg_err_unknown_show": "ERROR: Unknown show command.",
    "msg_err_unknown_show_source": "ERROR: Unknown show source.",
    "msg_err_pretty_requires_json": "ERROR: --pretty requires --json.",
    "msg_err_robot_unavailable": "ERROR: Robot source unavailable (not connected).",
    "msg_err_cmd_send": "ERROR: Command failed to send.",
    "msg_err_connect": "ERROR: Failed to connect.",
    "msg_err_handshake": "ERROR: Handshake failed.",
    "msg_err_selected_mode": "ERROR: selected-mode requires on/off.",
    "msg_err_run_no_robot": "ERROR: Cannot run tests without robot connection.",
    "msg_err_bind_value": "ERROR: binding requires value.",
    "msg_err_bind_numeric": "ERROR: binding value must be numeric.",
    "msg_err_device_missing": "ERROR: Device not defined in local config. Use device <name> to create it.",
    "msg_err_local_missing": "ERROR: Local config not loaded. Use merge/import config <bringup_system.json> first.",
    "msg_err_member_action": "ERROR: member requires enable/disable/toggle.",
    "msg_err_fmt": "ERROR: %s",
    "msg_ok_config": "OK: Config is valid.",
    "msg_connected": "Connected.",
    "msg_disconnected": "Disconnected.",
    "msg_warn_local_group": "WARNING: Robot not connected; local group selected.",
    "msg_warn_local_group_deleted": "WARNING: Robot not connected; local group deleted.",
    "msg_warn_local_selected": "WARNING: Robot not connected; local selected-device updated.",
    "msg_warn_local_selected_mode": "WARNING: Robot not connected; local selected-mode updated.",
    "msg_warn_local_member_add": "WARNING: Robot not connected; local group member added.",
    "msg_warn_local_member_remove": "WARNING: Robot not connected; local group member removed.",
    "msg_warn_local_member_update": "WARNING: Robot not connected; local member updated.",
    "msg_warn_local_binding": "WARNING: Robot not connected; local binding updated.",
    "msg_warn_local_bind_clear": "WARNING: Robot not connected; local bindings cleared.",
    "msg_warn_local_group_enable": "WARNING: Robot not connected; local group enabled.",
    "msg_warn_local_group_disable": "WARNING: Robot not connected; local group disabled.",
    "fmt_delete_group": "Delete group '%s'?",
    "fmt_rename_device": "Renamed device %s -> %s.",
    "fmt_update_device": "Updated device %s %s=%s.",
    "fmt_clear_device": "Cleared device %s %s.",
    "label_group_create": "group create",
    "label_group_delete": "group delete",
    "label_selected_device": "selected-device",
    "label_selected_mode": "selected-mode",
    "label_add_device": "add device",
    "label_remove_device": "remove device",
    "label_member": "member",
    "label_bind": "bind",
    "label_no_bind": "no bind",
    "label_enable": "enable",
    "label_disable": "disable",
    "label_run_test": "run test",
    "label_show": "show",
    "label_show_group": "show group",
}

SHOW_TARGET_CONFIG_RAW = "config-raw"
SHOW_NAME_LOCAL_RAW = "local-raw"
SHOW_TARGET_CONFIG_DIRTY = "config-dirty"
SHOW_NAME_DIRTY = "dirty"
SHOW_TARGET_PROFILE = "profile"
SHOW_TARGET_PROFILES = "profiles"


class BridgeCliAstExecutor:
    """
    NAME
        BridgeCliAstExecutor - AST-native command executor.
    """

    def __init__(self, cli: object) -> None:
        """
        NAME
            __init__ - Bind an executor to a BridgeCli instance.
        """
        self._cli = cli
        self._dispatch = self._build_dispatch()

    def execute(self, ast: CommandAst) -> Optional[int]:
        """
        NAME
            execute - Execute a parsed AST command.
        """
        if not ast.verb or not ast.kind:
            return None
        handler = self._dispatch.get(ast.kind)
        if not handler:
            print(AST_EXEC_SPEC["msg_err_unknown_cmd"])
            return None
        return handler(ast)

    def _build_dispatch(self) -> Dict[str, callable]:
        """
        NAME
            _build_dispatch - Build the AST execution dispatch table.
        """
        return {
            SPEC.kind_common_exit: self._ast_common_exit,
            SPEC.kind_common_end: self._ast_common_end,
            SPEC.kind_common_help: self._ast_common_help,
            SPEC.kind_common_ping: self._ast_common_ping,
            SPEC.kind_exec_connect: self._ast_exec_connect,
            SPEC.kind_exec_disconnect: self._ast_exec_disconnect,
            SPEC.kind_exec_configure_terminal: self._ast_exec_configure_terminal,
            SPEC.kind_show: self._ast_show,
            SPEC.kind_config_group: self._ast_config_group,
            SPEC.kind_config_no_group: self._ast_config_no_group,
            SPEC.kind_config_profile: self._ast_config_profile,
            SPEC.kind_config_selected_device: self._ast_config_selected_device,
            SPEC.kind_config_selected_mode: self._ast_config_selected_mode,
            SPEC.kind_config_merge: self._ast_config_merge,
            SPEC.kind_config_import: self._ast_config_import,
            SPEC.kind_config_export: self._ast_config_export,
            SPEC.kind_config_save: self._ast_config_save,
            SPEC.kind_config_rename_device: self._ast_config_rename_device,
            SPEC.kind_config_device: self._ast_config_device,
            SPEC.kind_config_device_set: self._ast_config_device_set,
            SPEC.kind_config_validate: self._ast_config_validate,
            SPEC.kind_config_bindings: self._ast_config_bindings,
            SPEC.kind_config_can_mappings: self._ast_config_can_mappings,
            SPEC.kind_group_show: self._ast_group_show,
            SPEC.kind_group_show_members: self._ast_group_show,
            SPEC.kind_group_show_binding: self._ast_group_show,
            SPEC.kind_group_add_device: self._ast_group_add_device,
            SPEC.kind_group_no_device: self._ast_group_no_device,
            SPEC.kind_group_member: self._ast_group_member,
            SPEC.kind_group_bind: self._ast_group_bind,
            SPEC.kind_group_no_bind: self._ast_group_no_bind,
            SPEC.kind_group_enable: self._ast_group_enable,
            SPEC.kind_group_disable: self._ast_group_disable,
            SPEC.kind_group_run_test: self._ast_group_run_test,
            SPEC.kind_device_show: self._ast_device_show,
            SPEC.kind_device_set: self._ast_device_set,
            SPEC.kind_device_no: self._ast_device_no,
        }

    def _ast_common_exit(self, _ast: CommandAst) -> Optional[int]:
        if self._cli._modes[-1].name == SPEC.modes[SPEC.idx_exec]:
            return AST_EXEC_SPEC["ret_ok"]
        self._cli._pop_mode()
        return None

    def _ast_common_end(self, _ast: CommandAst) -> Optional[int]:
        mode_cls = type(self._cli._modes[SPEC.count_zero])
        self._cli._modes = [mode_cls(SPEC.modes[SPEC.idx_exec])]
        return None

    def _ast_common_help(self, ast: CommandAst) -> Optional[int]:
        self._cli._print_help(ast.args if ast.args else [])
        return None

    def _ast_common_ping(self, _ast: CommandAst) -> Optional[int]:
        seq = show_status(self._cli._session, json_output=bool(SPEC.bool_false))
        self._cli._wait_for_seq(seq)
        return None

    def _ast_exec_connect(self, _ast: CommandAst) -> Optional[int]:
        if not connect(self._cli._session):
            print(AST_EXEC_SPEC["msg_err_connect"])
            return AST_EXEC_SPEC["ret_err"]
        ok = self._cli._session.ensure_handshake()
        if not ok:
            print(AST_EXEC_SPEC["msg_err_handshake"])
            return AST_EXEC_SPEC["ret_err"]
        print(AST_EXEC_SPEC["msg_connected"])
        return None

    def _ast_exec_disconnect(self, _ast: CommandAst) -> Optional[int]:
        disconnect(self._cli._session)
        print(AST_EXEC_SPEC["msg_disconnected"])
        return None

    def _ast_exec_configure_terminal(self, _ast: CommandAst) -> Optional[int]:
        self._cli._ensure_local_config()
        mode_cls = type(self._cli._modes[SPEC.count_zero])
        self._cli._modes.append(mode_cls(SPEC.modes[SPEC.idx_config]))
        return None

    def _ast_show(self, ast: CommandAst) -> Optional[int]:
        return self._handle_show_ast(ast)

    def _ast_config_group(self, ast: CommandAst) -> Optional[int]:
        name = ast.group_name
        if not self._cli._session.is_connected():
            if not self._cli._select_or_create_local_group(name):
                return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
            mode_cls = type(self._cli._modes[SPEC.count_zero])
            self._cli._modes.append(mode_cls(SPEC.modes[SPEC.idx_group], name))
            print(AST_EXEC_SPEC["msg_warn_local_group"])
            return None
        seq = group_create(self._cli._session, name)
        event = self._cli._wait_for_seq(seq)
        if self._cli._event_failed(event, AST_EXEC_SPEC["label_group_create"]):
            return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
        mode_cls = type(self._cli._modes[SPEC.count_zero])
        self._cli._modes.append(mode_cls(SPEC.modes[SPEC.idx_group], name))
        return None

    def _ast_config_no_group(self, ast: CommandAst) -> Optional[int]:
        name = ast.group_name
        if not self._cli._session.is_connected():
            if not self._cli._confirm(AST_EXEC_SPEC["fmt_delete_group"] % name):
                return None
            if not self._cli._delete_local_group(name):
                return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
            print(AST_EXEC_SPEC["msg_warn_local_group_deleted"])
            return None
        if not self._cli._confirm(AST_EXEC_SPEC["fmt_delete_group"] % name):
            return None
        seq = group_delete(self._cli._session, name, confirm=bool(SPEC.bool_true))
        event = self._cli._wait_for_seq(seq)
        if self._cli._event_failed(event, AST_EXEC_SPEC["label_group_delete"]):
            return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
        return None

    def _ast_config_profile(self, ast: CommandAst) -> Optional[int]:
        if ast.field == SPEC.cmd_create:
            if not self._cli._create_profile(ast.profile_name):
                return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
            return None
        if not self._cli._set_active_profile(ast.profile_name):
            return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
        print(f"Active profile: {self._cli._groups_profile}")
        return None

    def _ast_config_selected_device(self, ast: CommandAst) -> Optional[int]:
        if not self._cli._session.is_connected():
            if not self._cli._set_local_selected_device(ast.device_name):
                return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
            print(AST_EXEC_SPEC["msg_warn_local_selected"])
            return None
        seq = selected_device_set(self._cli._session, ast.device_name)
        event = self._cli._wait_for_seq(seq)
        if self._cli._event_failed(event, AST_EXEC_SPEC["label_selected_device"]):
            return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
        return None

    def _ast_config_selected_mode(self, ast: CommandAst) -> Optional[int]:
        mode_value = ast.field.lower()
        if mode_value not in (SPEC.cmd_on, SPEC.cmd_off):
            print(AST_EXEC_SPEC["msg_err_selected_mode"])
            return None
        enabled = mode_value == SPEC.cmd_on
        if not self._cli._session.is_connected():
            if not self._cli._set_local_selected_mode(enabled):
                return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
            print(AST_EXEC_SPEC["msg_warn_local_selected_mode"])
            return None
        seq = selected_mode_set(self._cli._session, enabled)
        event = self._cli._wait_for_seq(seq)
        if self._cli._event_failed(event, AST_EXEC_SPEC["label_selected_mode"]):
            return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
        return None

    def _ast_config_merge(self, ast: CommandAst) -> Optional[int]:
        plan = merge_config(ast.path, self._cli._conflict_policy, self._cli._active_profile_name())
        return self._cli._apply_config_plan(plan)

    def _ast_config_import(self, ast: CommandAst) -> Optional[int]:
        plan = import_config(ast.path, self._cli._conflict_policy, self._cli._active_profile_name())
        return self._cli._apply_config_plan(plan)

    def _ast_config_export(self, ast: CommandAst) -> Optional[int]:
        if ast.export_target == SPEC.cmd_export_runtime_groups:
            result = export_runtime_groups(
                self._cli._session, ast.path, self._cli._active_profile_name()
            )
            print(result.message)
            return AST_EXEC_SPEC["ret_err"] if not result.ok else None
        if ast.export_target == SPEC.cmd_export_cli_script:
            if not self._cli._export_cli_script(ast.path):
                return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
            return None
        print(AST_EXEC_SPEC["msg_err_unknown_cmd"])
        return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None

    def _ast_config_save(self, ast: CommandAst) -> Optional[int]:
        if ast.save_target == SPEC.cmd_save_profiles:
            if not self._cli._save_profiles(ast.path):
                return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
            return None
        if ast.save_target == SPEC.cmd_save_unified:
            if not self._cli._save_unified_config(ast.path):
                return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
            return None
        if ast.save_target == SPEC.cmd_save_config:
            result = save_config(self._cli._session, ast.path, self._cli._active_profile_name())
            print(result.message)
            return AST_EXEC_SPEC["ret_err"] if not result.ok else None
        if ast.save_target == SPEC.cmd_save_local_config:
            if not self._cli._save_local_config(ast.path):
                return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
            return None
        print(AST_EXEC_SPEC["msg_err_unknown_cmd"])
        return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None

    def _ast_config_rename_device(self, ast: CommandAst) -> Optional[int]:
        if self._cli._rename_local_device(ast.device_name, ast.field):
            print(AST_EXEC_SPEC["fmt_rename_device"] % (ast.device_name, ast.field))
            return None
        return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None

    def _ast_config_device(self, ast: CommandAst) -> Optional[int]:
        name = ast.device_name
        if not self._cli._ensure_local_device_entry(name):
            return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
        mode_cls = type(self._cli._modes[SPEC.count_zero])
        self._cli._modes.append(mode_cls(SPEC.modes[SPEC.idx_device], device=name))
        return None

    def _ast_config_device_set(self, ast: CommandAst) -> Optional[int]:
        if not self._cli._set_local_device_meta(ast.device_name, ast.field, ast.value):
            return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
        print(AST_EXEC_SPEC["fmt_update_device"] % (ast.device_name, ast.field, ast.value))
        return None

    def _ast_config_validate(self, ast: CommandAst) -> Optional[int]:
        if ast.path:
            ok, message, _config = self._cli.validate_config_file(ast.path)
        else:
            if not self._cli._local_config:
                print(AST_EXEC_SPEC["msg_err_local_missing"])
                return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
            ok, message = self._cli.validate_config_data(self._cli._local_config)
        if ok:
            print(AST_EXEC_SPEC["msg_ok_config"])
            return None
        print(AST_EXEC_SPEC["msg_err_fmt"] % message)
        return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None

    def _ast_config_bindings(self, ast: CommandAst) -> Optional[int]:
        return self._cli._config_bindings_command(ast.tokens)

    def _ast_config_can_mappings(self, ast: CommandAst) -> Optional[int]:
        return self._cli._config_can_mappings_command(ast.tokens)

    def _ast_group_show(self, ast: CommandAst) -> Optional[int]:
        group = self._cli._modes[-1].group
        if not self._cli._session.is_connected():
            return self._show_local_ast(
                SPEC.show_target_group, group, ast.show_json, ast.show_pretty
            )
        seq = show_group(self._cli._session, group, json_output=ast.show_json)
        event = self._cli._wait_for_seq(seq)
        if self._cli._event_failed(event, AST_EXEC_SPEC["label_show_group"]):
            return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
        return None

    def _ast_group_add_device(self, ast: CommandAst) -> Optional[int]:
        group = self._cli._modes[-1].group
        if not self._cli._session.is_connected():
            if self._cli._add_local_group_member(group, ast.input_name):
                print(AST_EXEC_SPEC["msg_warn_local_member_add"])
                return None
            return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
        if not self._cli._local_device_exists(ast.input_name):
            print(AST_EXEC_SPEC["msg_err_device_missing"])
            return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
        seq = group_add_device(
            self._cli._session,
            group,
            ast.input_name,
            self._cli._conflict_policy,
            force_move=bool(SPEC.bool_false),
        )
        event = self._cli._wait_for_seq(seq)
        if self._cli._handle_add_device_conflict(event, group, ast.input_name):
            return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
        if self._cli._event_failed(event, AST_EXEC_SPEC["label_add_device"]):
            return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
        return None

    def _ast_group_no_device(self, ast: CommandAst) -> Optional[int]:
        group = self._cli._modes[-1].group
        if not self._cli._session.is_connected():
            if self._cli._remove_local_group_member(group, ast.input_name):
                print(AST_EXEC_SPEC["msg_warn_local_member_remove"])
                return None
            return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
        seq = group_remove_device(self._cli._session, group, ast.input_name)
        event = self._cli._wait_for_seq(seq)
        if self._cli._event_failed(event, AST_EXEC_SPEC["label_remove_device"]):
            return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
        return None

    def _ast_group_member(self, ast: CommandAst) -> Optional[int]:
        group = self._cli._modes[-1].group
        action = ast.member_action
        if not self._cli._session.is_connected():
            if action in (SPEC.cmd_enable, SPEC.cmd_disable, SPEC.cmd_toggle):
                if self._cli._set_local_member_enabled(group, ast.input_name, action):
                    print(AST_EXEC_SPEC["msg_warn_local_member_update"])
                    return None
                return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
        if action == SPEC.cmd_enable:
            seq = group_member_enable(self._cli._session, group, ast.input_name)
        elif action == SPEC.cmd_disable:
            seq = group_member_disable(self._cli._session, group, ast.input_name)
        elif action == SPEC.cmd_toggle:
            seq = group_member_toggle(self._cli._session, group, ast.input_name)
        else:
            print(AST_EXEC_SPEC["msg_err_member_action"])
            return None
        event = self._cli._wait_for_seq(seq)
        if self._cli._event_failed(event, AST_EXEC_SPEC["label_member"]):
            return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
        return None

    def _ast_group_bind(self, ast: CommandAst) -> Optional[int]:
        group = self._cli._modes[-1].group
        if not self._cli._session.is_connected():
            tokens = [ast.input_name, ast.bind_kind]
            if ast.bind_kind != SPEC.bind_kinds[SPEC.count_zero] and ast.bind_value:
                tokens.append(ast.bind_value)
            if self._cli._add_local_binding(group, tokens):
                print(AST_EXEC_SPEC["msg_warn_local_binding"])
                return None
            return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
        value = None
        if ast.bind_kind != SPEC.bind_kinds[SPEC.count_zero]:
            if not ast.bind_value:
                print(AST_EXEC_SPEC["msg_err_bind_value"])
                return None
            try:
                value = float(ast.bind_value)
            except ValueError:
                print(AST_EXEC_SPEC["msg_err_bind_numeric"])
                return None
        seq = group_bind(self._cli._session, group, ast.input_name, ast.bind_kind, value=value)
        event = self._cli._wait_for_seq(seq)
        if self._cli._event_failed(event, AST_EXEC_SPEC["label_bind"]):
            return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
        return None

    def _ast_group_no_bind(self, _ast: CommandAst) -> Optional[int]:
        group = self._cli._modes[-1].group
        if not self._cli._session.is_connected():
            if self._cli._clear_local_bindings(group):
                print(AST_EXEC_SPEC["msg_warn_local_bind_clear"])
                return None
            return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
        seq = group_unbind(self._cli._session, group)
        event = self._cli._wait_for_seq(seq)
        if self._cli._event_failed(event, AST_EXEC_SPEC["label_no_bind"]):
            return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
        return None

    def _ast_group_enable(self, _ast: CommandAst) -> Optional[int]:
        group = self._cli._modes[-1].group
        if not self._cli._session.is_connected():
            if self._cli._set_local_group_enabled(group, bool(SPEC.bool_true)):
                print(AST_EXEC_SPEC["msg_warn_local_group_enable"])
                return None
            return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
        seq = group_enable(self._cli._session, group)
        event = self._cli._wait_for_seq(seq)
        if self._cli._event_failed(event, AST_EXEC_SPEC["label_enable"]):
            return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
        return None

    def _ast_group_disable(self, _ast: CommandAst) -> Optional[int]:
        group = self._cli._modes[-1].group
        if not self._cli._session.is_connected():
            if self._cli._set_local_group_enabled(group, bool(SPEC.bool_false)):
                print(AST_EXEC_SPEC["msg_warn_local_group_disable"])
                return None
            return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
        seq = group_disable(self._cli._session, group)
        event = self._cli._wait_for_seq(seq)
        if self._cli._event_failed(event, AST_EXEC_SPEC["label_disable"]):
            return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
        return None

    def _ast_group_run_test(self, ast: CommandAst) -> Optional[int]:
        group = self._cli._modes[-1].group
        if not self._cli._session.is_connected():
            print(AST_EXEC_SPEC["msg_err_run_no_robot"])
            return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
        name = ast.test_name if ast.test_name else None
        seq = group_run_test(self._cli._session, group, name)
        event = self._cli._wait_for_seq(seq)
        if self._cli._event_failed(event, AST_EXEC_SPEC["label_run_test"]):
            return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
        return None

    def _ast_device_show(self, ast: CommandAst) -> Optional[int]:
        device = self._cli._modes[-1].device
        if not ast.show_target:
            return self._cli._show_local_device_entry(device)
        return self._handle_show_ast(ast)

    def _ast_device_set(self, ast: CommandAst) -> Optional[int]:
        device = self._cli._modes[-1].device
        if not self._cli._set_local_device_meta(device, ast.field, ast.value):
            return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
        print(AST_EXEC_SPEC["fmt_update_device"] % (device, ast.field, ast.value))
        return None

    def _ast_device_no(self, ast: CommandAst) -> Optional[int]:
        device = self._cli._modes[-1].device
        if not self._cli._clear_local_device_meta(device, ast.field):
            return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
        print(AST_EXEC_SPEC["fmt_clear_device"] % (device, ast.field))
        return None

    def _handle_show_ast(self, ast: CommandAst) -> Optional[int]:
        target = ast.show_target.lower() if ast.show_target else SPEC.empty_str
        if not target:
            print(AST_EXEC_SPEC["msg_err_show_requires"])
            return None
        if ast.show_pretty and not ast.show_json:
            print(AST_EXEC_SPEC["msg_err_pretty_requires_json"])
            return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
        if target == SPEC.show_target_config:
            if ast.show_name:
                name = ast.show_name.lower()
                if name == SHOW_NAME_LOCAL_RAW:
                    target = SHOW_TARGET_CONFIG_RAW
                elif name == SHOW_NAME_DIRTY:
                    target = SHOW_TARGET_CONFIG_DIRTY
                else:
                    target = SPEC.show_target_runtime_state
            else:
                target = SPEC.show_target_runtime_state
        source = ast.show_source
        if target in (
            SHOW_TARGET_CONFIG_RAW,
            SHOW_TARGET_CONFIG_DIRTY,
            SHOW_TARGET_PROFILE,
            SHOW_TARGET_PROFILES,
            SPEC.show_target_device_registry,
        ):
            source = SPEC.show_source_local
        if not source:
            source = SPEC.show_source_robot if self._cli._session.is_connected() else SPEC.show_source_local
        if source == SPEC.show_source_both:
            local_ok = self._show_local_ast(
                target, ast.show_name, ast.show_json, ast.show_pretty
            )
            robot_ok = self._show_robot_ast(target, ast.show_name, ast.show_json)
            if self._cli._batch and (not local_ok or not robot_ok):
                return AST_EXEC_SPEC["ret_err"]
            return None
        if source == SPEC.show_source_local:
            if not self._show_local_ast(
                target, ast.show_name, ast.show_json, ast.show_pretty
            ):
                return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
            return None
        if source == SPEC.show_source_robot:
            if not self._show_robot_ast(target, ast.show_name, ast.show_json):
                return AST_EXEC_SPEC["ret_err"] if self._cli._batch else None
            return None
        print(AST_EXEC_SPEC["msg_err_unknown_show_source"])
        return None

    def _show_robot_ast(self, target: str, name: str, json_output: bool) -> bool:
        if not self._cli._session.is_connected():
            print(AST_EXEC_SPEC["msg_err_robot_unavailable"])
            return bool(SPEC.bool_false)
        if target == SPEC.show_target_status:
            seq = show_status(self._cli._session, json_output=json_output)
        elif target == SPEC.show_target_groups:
            seq = show_groups(self._cli._session, json_output=json_output)
        elif target == SPEC.show_target_group and name:
            seq = show_group(self._cli._session, name, json_output=json_output)
        elif target == SPEC.show_target_devices:
            seq = show_devices(self._cli._session, json_output=json_output)
        elif target == SPEC.show_target_device and name:
            seq = show_device(self._cli._session, name, json_output=json_output)
        elif target == SPEC.show_target_bindings:
            seq = show_bindings(self._cli._session, json_output=json_output)
        elif target == SPEC.show_target_selected_device:
            seq = show_selected_device(self._cli._session, json_output=json_output)
        elif target == SPEC.show_target_runtime_state:
            seq = show_runtime_state(self._cli._session, json_output=json_output)
        elif target == SPEC.show_target_device_registry:
            print(AST_EXEC_SPEC["msg_err_unknown_show"])
            return bool(SPEC.bool_false)
        else:
            print(AST_EXEC_SPEC["msg_err_unknown_show"])
            return bool(SPEC.bool_false)
        if seq is None:
            print(AST_EXEC_SPEC["msg_err_cmd_send"])
            return bool(SPEC.bool_false)
        self._cli._show_label_seq[int(seq)] = SPEC.show_source_robot
        event = self._cli._wait_for_seq(seq)
        if self._cli._event_failed(event, AST_EXEC_SPEC["label_show"]):
            return bool(SPEC.bool_false)
        return bool(SPEC.bool_true)

    def _show_local_ast(
        self, target: str, name: str, json_output: bool, pretty: bool
    ) -> bool:
        return self._cli._show_local(
            target, [target, name] if name else [target], json_output, pretty
        )
