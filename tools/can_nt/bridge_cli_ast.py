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
CMD_ALL = "all"
CMD_FILE = "file"
FLAG_FORCE = "--force"
FLAG_REPAIR = "--repair"
MESSAGE_VALIDATE_ALL_HEADER = "Validate all:"
MESSAGE_VALIDATE_ALL_ITEM_OK = "  {label}: OK"
MESSAGE_VALIDATE_ALL_ITEM_ERR = "  {label}: ERROR: {message}"
MESSAGE_VALIDATE_ALL_SUMMARY_OK = "OK: All validations passed."
MESSAGE_VALIDATE_ALL_SUMMARY_ERR = "ERROR: Validation failures: {count}"
from tools.can_nt.status import (
    StatusResult,
    SS__CLI_PARSER__UNKNOWN_COMMAND,
    SS__CLI_VALIDATOR__INVALID_VALUE,
    SS__CONFIG__NOT_LOADED,
    SS__CONFIG__INVALID,
    SS__CONFIG__VALID,
    SS__DEVICE__NOT_DEFINED,
    SS__EXECUTOR__FAILED,
    SS__NORMAL,
    SS__NETWORK__COMMAND_SEND_FAILED,
    SS__NETWORK__CONNECT_FAILED,
    SS__NETWORK__HANDSHAKE_FAILED,
    SS__NETWORK__NOT_CONNECTED,
    SS__NETWORK__ROBOT_UNAVAILABLE,
    format_status_message,
)
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
    show_version,
)

SHOW_TARGET_VERSION = "version"

AST_EXEC_SPEC = {
    "ret_ok": 0,
    "ret_err": SS__EXECUTOR__FAILED,
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
    "msg_err_local_missing": "ERROR: Local config not loaded. Use load config <path> --merge|--replace first.",
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
    "fmt_delete_profile_device": "Delete profile device '%s'?",
    "fmt_profile_device_deleted": "Deleted profile device %s.",
    "fmt_delete_profile": "Delete profile '%s'?",
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
SHOW_TARGET_RUNTIME_COMPONENTS = "runtime-components"


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

    def execute(self, ast: CommandAst) -> Optional[StatusResult]:
        """
        NAME
            execute - Execute a parsed AST command.
        """
        if not ast.verb or not ast.kind:
            return None
        handler = self._dispatch.get(ast.kind)
        if not handler:
            print(AST_EXEC_SPEC["msg_err_unknown_cmd"])
            return StatusResult(code=SS__CLI_PARSER__UNKNOWN_COMMAND, message=AST_EXEC_SPEC["msg_err_unknown_cmd"])
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
            SPEC.kind_config_load: self._ast_config_load,
            SPEC.kind_config_push: self._ast_config_push,
            SPEC.kind_config_profiles_init: self._ast_config_profiles_init,
            SPEC.kind_config_rename_device: self._ast_config_rename_device,
            SPEC.kind_config_no_device: self._ast_config_no_device,
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
            SPEC.kind_device_delete: self._ast_device_delete,
        }

    def _ast_common_exit(self, _ast: CommandAst) -> Optional[StatusResult]:
        if self._cli._modes[-1].name == SPEC.modes[SPEC.idx_exec]:
            return StatusResult(code=SS__NORMAL, exit_requested=True)
        self._cli._pop_mode()
        return None

    def _ast_common_end(self, _ast: CommandAst) -> Optional[StatusResult]:
        mode_cls = type(self._cli._modes[SPEC.count_zero])
        self._cli._modes = [mode_cls(SPEC.modes[SPEC.idx_exec])]
        return None

    def _ast_common_help(self, ast: CommandAst) -> Optional[StatusResult]:
        self._cli._print_help(ast.args if ast.args else [])
        return StatusResult(code=SS__NORMAL)

    def _ast_common_ping(self, _ast: CommandAst) -> Optional[StatusResult]:
        seq = show_status(self._cli._session, json_output=bool(SPEC.bool_false))
        self._cli._wait_for_seq(seq)
        return StatusResult(code=SS__NORMAL)

    def _ast_exec_connect(self, _ast: CommandAst) -> Optional[StatusResult]:
        if not connect(self._cli._session):
            print(AST_EXEC_SPEC["msg_err_connect"])
            return StatusResult(code=SS__NETWORK__CONNECT_FAILED, message=AST_EXEC_SPEC["msg_err_connect"])
        ok = self._cli._session.ensure_handshake()
        if not ok:
            print(AST_EXEC_SPEC["msg_err_handshake"])
            return StatusResult(code=SS__NETWORK__HANDSHAKE_FAILED, message=AST_EXEC_SPEC["msg_err_handshake"])
        print(AST_EXEC_SPEC["msg_connected"])
        return StatusResult(code=SS__NORMAL)

    def _ast_exec_disconnect(self, _ast: CommandAst) -> Optional[StatusResult]:
        disconnect(self._cli._session)
        print(AST_EXEC_SPEC["msg_disconnected"])
        return StatusResult(code=SS__NORMAL)

    def _ast_exec_configure_terminal(self, _ast: CommandAst) -> Optional[StatusResult]:
        self._cli._ensure_local_config()
        mode_cls = type(self._cli._modes[SPEC.count_zero])
        self._cli._modes.append(mode_cls(SPEC.modes[SPEC.idx_config]))
        return StatusResult(code=SS__NORMAL)

    def _ast_show(self, ast: CommandAst) -> Optional[int]:
        return self._handle_show_ast(ast)

    def _ast_config_group(self, ast: CommandAst) -> Optional[int]:
        name = ast.group_name
        if not self._cli._session.is_connected():
            if not self._cli._select_or_create_local_group(name):
                return AST_EXEC_SPEC["ret_err"]
            mode_cls = type(self._cli._modes[SPEC.count_zero])
            self._cli._modes.append(mode_cls(SPEC.modes[SPEC.idx_group], name))
            print(AST_EXEC_SPEC["msg_warn_local_group"])
            return None
        seq = group_create(self._cli._session, name)
        event = self._cli._wait_for_seq(seq)
        if self._cli._event_failed(event, AST_EXEC_SPEC["label_group_create"]):
            return AST_EXEC_SPEC["ret_err"]
        mode_cls = type(self._cli._modes[SPEC.count_zero])
        self._cli._modes.append(mode_cls(SPEC.modes[SPEC.idx_group], name))
        return None

    def _ast_config_no_group(self, ast: CommandAst) -> Optional[int]:
        name = ast.group_name
        if not self._cli._session.is_connected():
            if not self._cli._confirm(AST_EXEC_SPEC["fmt_delete_group"] % name):
                return None
            if not self._cli._delete_local_group(name):
                return AST_EXEC_SPEC["ret_err"]
            print(AST_EXEC_SPEC["msg_warn_local_group_deleted"])
            return None
        if not self._cli._confirm(AST_EXEC_SPEC["fmt_delete_group"] % name):
            return None
        seq = group_delete(self._cli._session, name, confirm=bool(SPEC.bool_true))
        event = self._cli._wait_for_seq(seq)
        if self._cli._event_failed(event, AST_EXEC_SPEC["label_group_delete"]):
            return AST_EXEC_SPEC["ret_err"]
        return None

    def _ast_config_profile(self, ast: CommandAst) -> Optional[StatusResult]:
        if ast.field == SPEC.cmd_create:
            if not self._cli._create_profile(ast.profile_name):
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            return StatusResult(code=SS__NORMAL)
        if ast.field == SPEC.cmd_default:
            return self._cli._set_default_profile(ast.profile_name)
        if ast.field == SPEC.cmd_export:
            return self._cli._export_profile_bundle(ast.profile_name, ast.path)
        if ast.field == SPEC.cmd_delete:
            if ast.profile_name and not ast.device_name:
                name = ast.profile_name
                if not self._cli._batch and not self._cli._confirm(
                    AST_EXEC_SPEC["fmt_delete_profile"] % name
                ):
                    return None
                return self._cli._delete_profile(name)
            name = ast.device_name
            if not name:
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            if not self._cli._batch and not self._cli._confirm(
                AST_EXEC_SPEC["fmt_delete_profile_device"] % name
            ):
                return None
            result = self._cli._delete_profiles_device(name)
            if not result.ok():
                return result
            print(AST_EXEC_SPEC["fmt_profile_device_deleted"] % name)
            return StatusResult(code=SS__NORMAL)
        if ast.field == SPEC.cmd_show_all:
            name = ast.device_name
            if not name:
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            return self._cli._show_profiles_device_all(name)
        if not self._cli._set_active_profile(ast.profile_name):
            return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
        print(f"Active profile: {self._cli._groups_profile}")
        return StatusResult(code=SS__NORMAL)

    def _ast_config_selected_device(self, ast: CommandAst) -> Optional[StatusResult]:
        if not self._cli._session.is_connected():
            if not self._cli._set_local_selected_device(ast.device_name):
                return StatusResult(code=SS__DEVICE__NOT_DEFINED, message=AST_EXEC_SPEC["msg_err_device_missing"])
            print(AST_EXEC_SPEC["msg_warn_local_selected"])
            return StatusResult(code=SS__NETWORK__NOT_CONNECTED, message=AST_EXEC_SPEC["msg_warn_local_selected"])
        seq = selected_device_set(self._cli._session, ast.device_name)
        event = self._cli._wait_for_seq(seq)
        if self._cli._event_failed(event, AST_EXEC_SPEC["label_selected_device"]):
            return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED, message=AST_EXEC_SPEC["msg_err_cmd_send"])
        return StatusResult(code=SS__NORMAL)

    def _ast_config_selected_mode(self, ast: CommandAst) -> Optional[StatusResult]:
        mode_value = ast.field.lower()
        if mode_value not in (SPEC.cmd_on, SPEC.cmd_off):
            print(AST_EXEC_SPEC["msg_err_selected_mode"])
            return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE, message=AST_EXEC_SPEC["msg_err_selected_mode"])
        enabled = mode_value == SPEC.cmd_on
        if not self._cli._session.is_connected():
            if not self._cli._set_local_selected_mode(enabled):
                return StatusResult(code=SS__CONFIG__NOT_LOADED, message=AST_EXEC_SPEC["msg_err_local_missing"])
            print(AST_EXEC_SPEC["msg_warn_local_selected_mode"])
            return StatusResult(code=SS__NETWORK__NOT_CONNECTED, message=AST_EXEC_SPEC["msg_warn_local_selected_mode"])
        seq = selected_mode_set(self._cli._session, enabled)
        event = self._cli._wait_for_seq(seq)
        if self._cli._event_failed(event, AST_EXEC_SPEC["label_selected_mode"]):
            return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED, message=AST_EXEC_SPEC["msg_err_cmd_send"])
        return StatusResult(code=SS__NORMAL)

    def _ast_config_merge(self, ast: CommandAst) -> Optional[int]:
        result = self._cli._load_config_merge_deprecated(ast.path)
        return AST_EXEC_SPEC["ret_err"] if not result.ok() else None

    def _ast_config_import(self, ast: CommandAst) -> Optional[int]:
        result = self._cli._load_config_replace_deprecated(ast.path)
        return AST_EXEC_SPEC["ret_err"] if not result.ok() else None

    def _ast_config_export(self, ast: CommandAst) -> Optional[int]:
        if ast.export_target == SPEC.cmd_export_runtime_groups:
            result = export_runtime_groups(
                self._cli._session, ast.path, self._cli._active_profile_name()
            )
            message = format_status_message(result.code) or result.message
            if message:
                print(message)
            return AST_EXEC_SPEC["ret_err"] if not result.ok() else None
        if ast.export_target == SPEC.cmd_export_cli_script:
            if not self._cli._export_cli_script(ast.path):
                return AST_EXEC_SPEC["ret_err"]
            return None
        print(AST_EXEC_SPEC["msg_err_unknown_cmd"])
        return AST_EXEC_SPEC["ret_err"]

    def _ast_config_save(self, ast: CommandAst) -> Optional[int]:
        result = self._cli._handle_save_command(ast.tokens)
        return AST_EXEC_SPEC["ret_err"] if not result.ok() else None

    def _ast_config_load(self, ast: CommandAst) -> Optional[int]:
        result = self._cli._handle_load_command(ast.tokens)
        return AST_EXEC_SPEC["ret_err"] if not result.ok() else None

    def _ast_config_push(self, ast: CommandAst) -> Optional[StatusResult]:
        target = ast.field or SPEC.empty_str
        if target == SPEC.cmd_profiles:
            return self._cli._profiles_push(ast.path, ast.value)
        if target == SPEC.cmd_config:
            return self._cli._config_push(ast.path, ast.value)
        print(AST_EXEC_SPEC["msg_err_unknown_cmd"])
        return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)

    def _ast_config_profiles_init(self, ast: CommandAst) -> Optional[StatusResult]:
        return self._cli._init_profiles_payload()

    def _ast_config_rename_device(self, ast: CommandAst) -> Optional[int]:
        if self._cli._rename_local_device(ast.device_name, ast.field):
            print(AST_EXEC_SPEC["fmt_rename_device"] % (ast.device_name, ast.field))
            return None
        return AST_EXEC_SPEC["ret_err"]

    def _ast_config_no_device(self, ast: CommandAst) -> Optional[int]:
        name = ast.device_name
        if not self._cli._confirm(f"Delete device '{name}'?"):
            return None
        if not self._cli._delete_local_device(name):
            return AST_EXEC_SPEC["ret_err"]
        print(f"Deleted device {name}.")
        return None

    def _ast_config_device(self, ast: CommandAst) -> Optional[int]:
        name = ast.device_name
        if not self._cli._ensure_local_device_entry(name):
            return AST_EXEC_SPEC["ret_err"]
        mode_cls = type(self._cli._modes[SPEC.count_zero])
        self._cli._modes.append(mode_cls(SPEC.modes[SPEC.idx_device], device=name))
        return None

    def _ast_config_device_set(self, ast: CommandAst) -> Optional[int]:
        result = self._cli._set_local_device_meta(ast.device_name, ast.field, ast.value)
        if not result.ok():
            return AST_EXEC_SPEC["ret_err"]
        print(AST_EXEC_SPEC["fmt_update_device"] % (ast.device_name, ast.field, ast.value))
        return None

    def _ast_config_validate(self, ast: CommandAst) -> Optional[StatusResult]:
        target = ast.field or SPEC.empty_str
        if target == CMD_FILE:
            repair = any(token.lower() == FLAG_REPAIR for token in ast.tokens)
            return self._cli._validate_file(ast.path, repair)
        if target == CMD_ALL:
            ok, results = self._cli.validate_all()
            print(MESSAGE_VALIDATE_ALL_HEADER)
            for label, item_ok, message in results:
                if item_ok:
                    print(MESSAGE_VALIDATE_ALL_ITEM_OK.format(label=label))
                else:
                    print(MESSAGE_VALIDATE_ALL_ITEM_ERR.format(label=label, message=message))
            if ok:
                print(MESSAGE_VALIDATE_ALL_SUMMARY_OK)
                return StatusResult(code=SS__CONFIG__VALID)
            failures = [item for item in results if not item[1]]
            print(MESSAGE_VALIDATE_ALL_SUMMARY_ERR.format(count=len(failures)))
            return StatusResult(code=SS__CONFIG__INVALID)
        all_issues = ast.value == SPEC.cmd_validate_all
        if target == SPEC.cmd_config:
            if ast.path:
                if all_issues:
                    ok, message, _config = self._cli.validate_config_file_all(ast.path)
                else:
                    ok, message, _config = self._cli.validate_config_file(ast.path)
            else:
                if not self._cli._local_config:
                    print(AST_EXEC_SPEC["msg_err_local_missing"])
                    return StatusResult(code=SS__CONFIG__NOT_LOADED)
                if all_issues:
                    ok, message = self._cli.validate_config_data_all(self._cli._local_config)
                else:
                    ok, message = self._cli.validate_config_data(self._cli._local_config)
        elif target == "profiles":
            if ast.value == SPEC.show_source_robot:
                ok, message = self._cli.validate_profiles_robot()
            else:
                ok, message = self._cli.validate_profiles_only()
        elif target == SPEC.cmd_tests:
            ok, message = self._cli.validate_tests_only()
        elif target == SPEC.cmd_bindings:
            ok, message = self._cli.validate_bindings_only(ast.path)
        elif target == SPEC.cmd_can_mappings:
            ok, message = self._cli.validate_mappings_only(ast.path)
        else:
            print(AST_EXEC_SPEC["msg_err_unknown_cmd"])
            return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
        if ok:
            print(AST_EXEC_SPEC["msg_ok_config"])
            return StatusResult(code=SS__CONFIG__VALID)
        print(AST_EXEC_SPEC["msg_err_fmt"] % message)
        if target == SPEC.cmd_config and ast.path:
            self._cli._maybe_hint_validate_profile(ast.path)
        return StatusResult(code=SS__CONFIG__INVALID)

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
            return AST_EXEC_SPEC["ret_err"]
        return None

    def _ast_group_add_device(self, ast: CommandAst) -> Optional[int]:
        group = self._cli._modes[-1].group
        if not self._cli._session.is_connected():
            if self._cli._add_local_group_member(group, ast.input_name):
                print(AST_EXEC_SPEC["msg_warn_local_member_add"])
                return None
            return AST_EXEC_SPEC["ret_err"]
        if not self._cli._local_device_exists(ast.input_name):
            print(AST_EXEC_SPEC["msg_err_device_missing"])
            return AST_EXEC_SPEC["ret_err"]
        seq = group_add_device(
            self._cli._session,
            group,
            ast.input_name,
            self._cli._conflict_policy,
            force_move=bool(SPEC.bool_false),
        )
        event = self._cli._wait_for_seq(seq)
        if self._cli._handle_add_device_conflict(event, group, ast.input_name):
            return AST_EXEC_SPEC["ret_err"]
        if self._cli._event_failed(event, AST_EXEC_SPEC["label_add_device"]):
            return AST_EXEC_SPEC["ret_err"]
        return None

    def _ast_group_no_device(self, ast: CommandAst) -> Optional[int]:
        group = self._cli._modes[-1].group
        if not self._cli._session.is_connected():
            if self._cli._remove_local_group_member(group, ast.input_name):
                print(AST_EXEC_SPEC["msg_warn_local_member_remove"])
                return None
            return AST_EXEC_SPEC["ret_err"]
        seq = group_remove_device(self._cli._session, group, ast.input_name)
        event = self._cli._wait_for_seq(seq)
        if self._cli._event_failed(event, AST_EXEC_SPEC["label_remove_device"]):
            return AST_EXEC_SPEC["ret_err"]
        return None

    def _ast_group_member(self, ast: CommandAst) -> Optional[int]:
        group = self._cli._modes[-1].group
        action = ast.member_action
        if not self._cli._session.is_connected():
            if action in (SPEC.cmd_enable, SPEC.cmd_disable, SPEC.cmd_toggle):
                if self._cli._set_local_member_enabled(group, ast.input_name, action):
                    print(AST_EXEC_SPEC["msg_warn_local_member_update"])
                    return None
                return AST_EXEC_SPEC["ret_err"]
        if action == SPEC.cmd_enable:
            seq = group_member_enable(self._cli._session, group, ast.input_name)
        elif action == SPEC.cmd_disable:
            seq = group_member_disable(self._cli._session, group, ast.input_name)
        elif action == SPEC.cmd_toggle:
            seq = group_member_toggle(self._cli._session, group, ast.input_name)
        else:
            print(AST_EXEC_SPEC["msg_err_member_action"])
            return AST_EXEC_SPEC["ret_err"]
        event = self._cli._wait_for_seq(seq)
        if self._cli._event_failed(event, AST_EXEC_SPEC["label_member"]):
            return AST_EXEC_SPEC["ret_err"]
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
            return AST_EXEC_SPEC["ret_err"]
        value = None
        if ast.bind_kind != SPEC.bind_kinds[SPEC.count_zero]:
            if not ast.bind_value:
                print(AST_EXEC_SPEC["msg_err_bind_value"])
                return AST_EXEC_SPEC["ret_err"]
            try:
                value = float(ast.bind_value)
            except ValueError:
                print(AST_EXEC_SPEC["msg_err_bind_numeric"])
                return AST_EXEC_SPEC["ret_err"]
        seq = group_bind(self._cli._session, group, ast.input_name, ast.bind_kind, value=value)
        event = self._cli._wait_for_seq(seq)
        if self._cli._event_failed(event, AST_EXEC_SPEC["label_bind"]):
            return AST_EXEC_SPEC["ret_err"]
        return None

    def _ast_group_no_bind(self, _ast: CommandAst) -> Optional[int]:
        group = self._cli._modes[-1].group
        if not self._cli._session.is_connected():
            if self._cli._clear_local_bindings(group):
                print(AST_EXEC_SPEC["msg_warn_local_bind_clear"])
                return None
            return AST_EXEC_SPEC["ret_err"]
        seq = group_unbind(self._cli._session, group)
        event = self._cli._wait_for_seq(seq)
        if self._cli._event_failed(event, AST_EXEC_SPEC["label_no_bind"]):
            return AST_EXEC_SPEC["ret_err"]
        return None

    def _ast_group_enable(self, _ast: CommandAst) -> Optional[int]:
        group = self._cli._modes[-1].group
        if not self._cli._session.is_connected():
            if self._cli._set_local_group_enabled(group, bool(SPEC.bool_true)):
                print(AST_EXEC_SPEC["msg_warn_local_group_enable"])
                return None
            return AST_EXEC_SPEC["ret_err"]
        seq = group_enable(self._cli._session, group)
        event = self._cli._wait_for_seq(seq)
        if self._cli._event_failed(event, AST_EXEC_SPEC["label_enable"]):
            return AST_EXEC_SPEC["ret_err"]
        return None

    def _ast_group_disable(self, _ast: CommandAst) -> Optional[int]:
        group = self._cli._modes[-1].group
        if not self._cli._session.is_connected():
            if self._cli._set_local_group_enabled(group, bool(SPEC.bool_false)):
                print(AST_EXEC_SPEC["msg_warn_local_group_disable"])
                return None
            return AST_EXEC_SPEC["ret_err"]
        seq = group_disable(self._cli._session, group)
        event = self._cli._wait_for_seq(seq)
        if self._cli._event_failed(event, AST_EXEC_SPEC["label_disable"]):
            return AST_EXEC_SPEC["ret_err"]
        return None

    def _ast_group_run_test(self, ast: CommandAst) -> Optional[int]:
        group = self._cli._modes[-1].group
        if not self._cli._session.is_connected():
            print(AST_EXEC_SPEC["msg_err_run_no_robot"])
            return AST_EXEC_SPEC["ret_err"]
        name = ast.test_name if ast.test_name else None
        seq = group_run_test(self._cli._session, group, name)
        event = self._cli._wait_for_seq(seq)
        if self._cli._event_failed(event, AST_EXEC_SPEC["label_run_test"]):
            return AST_EXEC_SPEC["ret_err"]
        return None

    def _ast_device_show(self, ast: CommandAst) -> Optional[int]:
        device = self._cli._modes[-1].device
        if not ast.show_target:
            return self._cli._show_local_device_entry(device)
        return self._handle_show_ast(ast)

    def _ast_device_set(self, ast: CommandAst) -> Optional[int]:
        device = self._cli._modes[-1].device
        result = self._cli._set_local_device_meta(device, ast.field, ast.value)
        if not result.ok():
            return AST_EXEC_SPEC["ret_err"]
        print(AST_EXEC_SPEC["fmt_update_device"] % (device, ast.field, ast.value))
        return None

    def _ast_device_no(self, ast: CommandAst) -> Optional[int]:
        device = self._cli._modes[-1].device
        result = self._cli._clear_local_device_meta(device, ast.field)
        if not result.ok():
            return AST_EXEC_SPEC["ret_err"]
        print(AST_EXEC_SPEC["fmt_clear_device"] % (device, ast.field))
        return None

    def _ast_device_delete(self, _ast: CommandAst) -> Optional[int]:
        device = self._cli._modes[-1].device
        if not self._cli._confirm(f"Delete device '{device}'?"):
            return None
        if not self._cli._delete_local_device(device):
            return AST_EXEC_SPEC["ret_err"]
        print(f"Deleted device {device}.")
        self._cli._pop_mode()
        return None

    def _handle_show_ast(self, ast: CommandAst) -> Optional[int]:
        target = ast.show_target.lower() if ast.show_target else SPEC.empty_str
        if not target:
            print(AST_EXEC_SPEC["msg_err_show_requires"])
            return AST_EXEC_SPEC["ret_err"]
        if ast.show_pretty and not ast.show_json:
            print(AST_EXEC_SPEC["msg_err_pretty_requires_json"])
            return AST_EXEC_SPEC["ret_err"]
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
            SPEC.show_target_device,
                SPEC.show_target_device_group,
        ):
            source = SPEC.show_source_local
        if target == SHOW_TARGET_RUNTIME_COMPONENTS:
            source = SPEC.show_source_local
        if target == SHOW_TARGET_VERSION and not source:
            source = SPEC.show_source_local
        if not source:
            source = SPEC.show_source_robot if self._cli._session.is_connected() else SPEC.show_source_local
        if source == SPEC.show_source_both:
            local_ok = self._show_local_ast(
                target, ast.show_name, ast.show_json, ast.show_pretty
            )
            robot_result = self._show_robot_ast(target, ast.show_name, ast.show_json)
            if isinstance(robot_result, StatusResult):
                if self._cli._batch and not robot_result.ok():
                    return robot_result
                return robot_result
            robot_ok = bool(robot_result)
            if self._cli._batch and (not local_ok or not robot_ok):
                return AST_EXEC_SPEC["ret_err"]
            return None
        if source == SPEC.show_source_local:
            if not self._show_local_ast(
                target, ast.show_name, ast.show_json, ast.show_pretty
            ):
                return AST_EXEC_SPEC["ret_err"]
            return None
        if source == SPEC.show_source_robot:
            robot_result = self._show_robot_ast(target, ast.show_name, ast.show_json)
            if isinstance(robot_result, StatusResult):
                return robot_result
            if not robot_result:
                return AST_EXEC_SPEC["ret_err"]
            return None
        print(AST_EXEC_SPEC["msg_err_unknown_show_source"])
        return AST_EXEC_SPEC["ret_err"]

    def _show_robot_ast(self, target: str, name: str, json_output: bool) -> object:
        if not self._cli._session.is_connected():
            print(AST_EXEC_SPEC["msg_err_robot_unavailable"])
            return StatusResult(code=SS__NETWORK__NOT_CONNECTED)
        if target == SPEC.show_target_status:
            seq = show_status(self._cli._session, json_output=json_output)
        elif target == SPEC.show_target_groups:
            seq = show_groups(self._cli._session, json_output=json_output)
        elif target == SPEC.show_target_group and name:
            seq = show_group(self._cli._session, name, json_output=json_output)
        elif target == SPEC.show_target_devices:
            seq = show_devices(self._cli._session, json_output=json_output)
        elif target == SPEC.show_target_device_group and name:
            seq = show_device(self._cli._session, name, json_output=json_output)
        elif target == SPEC.show_target_bindings:
            seq = show_bindings(self._cli._session, json_output=json_output)
        elif target == SPEC.show_target_selected_device:
            seq = show_selected_device(self._cli._session, json_output=json_output)
        elif target == SPEC.show_target_runtime_state:
            seq = show_runtime_state(self._cli._session, json_output=json_output)
        elif target == SHOW_TARGET_VERSION:
            seq = show_version(self._cli._session, json_output=json_output)
        else:
            print(AST_EXEC_SPEC["msg_err_unknown_show"])
            return StatusResult(code=SS__CLI_PARSER__UNKNOWN_COMMAND)
        if seq is None:
            print(AST_EXEC_SPEC["msg_err_cmd_send"])
            return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
        self._cli._show_label_seq[int(seq)] = SPEC.show_source_robot
        event = self._cli._wait_for_seq(seq)
        if self._cli._event_failed(event, AST_EXEC_SPEC["label_show"]):
            return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
        return bool(SPEC.bool_true)

    def _show_local_ast(
        self, target: str, name: str, json_output: bool, pretty: bool
    ) -> bool:
        return self._cli._show_local(
            target, [target, name] if name else [target], json_output, pretty
        )
