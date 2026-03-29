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

from tools.can_nt.bridge_cmd_tracker import CommandTracker
from tools.can_nt.bridge_cli_parser import BridgeCliParser, CliParseError
from tools.can_nt.bridge_cli_ast import BridgeCliAstExecutor
from tools.can_nt.bridge_cli_constants import CLI_PARSER_CONST
from tools.can_nt.can_profiles import get_default_profile
from tools.can_nt.bridge_ops import (
    connect,
    disconnect,
    local_show_data,
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
from tools.common.json_io import read_json, write_json
from tools.common.profile_io import compute_profiles_hash
from tools.common.paths import repo_root, tests_deploy_path, profiles_canonical_path, can_mappings_path
from tools.common.profile_constants import (
    BRIDGE_CONFIG_SCHEMA_VERSION,
    KEY_BRIDGE_BY_PROFILE,
    KEY_BRIDGE_GENERATED_AT,
    KEY_BRIDGE_GROUPS,
    KEY_BRIDGE_SCHEMA_VERSION,
    KEY_BRIDGE_SELECTED_DEVICE,
    KEY_DEFAULT_PROFILE,
    KEY_PROFILE,
    KEY_PROFILES,
    PROFILE_SCHEMA_VERSION,
)
from tools.common.tests_io import load_tests_payload, write_tests_payload
from tools.common.test_authoring import (
    TestAuthoringModel,
    TestBindingButton,
    TestBindingJoystick,
    TestModel,
    TestSetModel,
    TerminationModel,
    model_from_payload,
    model_to_payload,
    validate_model,
    validate_test_name,
)
from tools.common.test_authoring.device_catalog import load_controller_names, load_profile_devices
from tools.common.time_utils import timestamp_version

# Parser selection (comment out one of the two lines below).
# CLI_PARSER_KIND = CLI_PARSER_CONST["legacy"]
CLI_PARSER_KIND = CLI_PARSER_CONST["ebnf"]

MODE_CONFIG = "config"
MODE_TEST = "test"

TESTS_FILENAME = "bringup_tests.json"
DEFAULT_TEST_SET = "default"
EMPTY_STRING = ""
TEST_LABEL_UNKNOWN = "unknown"
COUNT_ZERO = 0
EXIT_CODE_ERROR = 2

CMD_SHOW = "show"
CMD_WRITE = "write"
CMD_TEST = "test"
CMD_TESTS = "tests"
CMD_CREATE = "create"
CMD_DELETE = "delete"
CMD_SET = "set"
CMD_TYPE = "type"
CMD_DEVICE = "device"
CMD_REGISTRY = "registry"
CMD_PROFILE = "profile"
CMD_ADD = "add"
CMD_NO = "no"
CMD_INPUT_SOURCE = "inputsource"
CMD_DEADBAND = "deadband"
CMD_DUTY = "duty"
CMD_TERMINATION = "termination"
CMD_ROTATION = "rotation"
CMD_TIME = "time"
CMD_HOLD = "hold"
CMD_LIMITSWITCH = "limitswitch"
CMD_DEADBAND_SWEEP = "deadbandsweep"
CMD_ENABLED = "enabled"
CMD_EXIT = "exit"
CMD_END = "end"

KEY_DEVICE = "device"
KEY_GROUPS = "groups"
KEY_BY_PROFILE = "byProfile"
KEY_SELECTED_DEVICE = "selectedDevice"
KEY_MANUFACTURERS = "manufacturers"
KEY_DEVICE_TYPES = "device_types"

SHOW_TARGET_CONFIG = "config"
SHOW_TARGET_RUNTIME = "runtime-state"
SHOW_TARGET_CONFIG_RAW = "config-raw"
SHOW_CONFIG_LOCAL_RAW = "local-raw"
SHOW_TARGET_PROFILES = "profiles"
SHOW_TARGET_PROFILE = "profile"

COUNT_ZERO = 0
COUNT_ONE = 1
COUNT_TWO = 2

KEY_PROFILE_INFO = "profile"
KEY_ACTIVE = "active"
KEY_DEFAULT = "default"
KEY_AVAILABLE = "available"
STRING_NONE = "(none)"
SHOW_TARGET_STATUS = "status"
SHOW_TARGET_GROUPS = "groups"
SHOW_TARGET_GROUP = "group"
SHOW_TARGET_DEVICES = "devices"
SHOW_TARGET_DEVICE = "device"
SHOW_TARGET_DEVICE_REGISTRY = "device-registry"
SHOW_TARGET_BINDINGS = "bindings"
SHOW_TARGET_SELECTED_DEVICE = "selected-device"

MESSAGE_ERR_UNKNOWN_SHOW = "ERROR: Unknown show command."
MESSAGE_ERR_UNKNOWN_SHOW_SOURCE = "ERROR: Unknown show source."
MESSAGE_ERR_SHOW_REQUIRES_TARGET = "ERROR: show requires a target."
MESSAGE_ERR_LOCAL_CONFIG_MISSING = "ERROR: Local config not loaded. Use merge/import config <bringup_system.json>."
MESSAGE_ERR_LOCAL_DEVICE_NOT_FOUND = "ERROR: Local device not found."
MESSAGE_ERR_REGISTRY_NOT_LOADED = "ERROR: Profiles not loaded. Use merge/import config <bringup_system.json>."
MESSAGE_LOCAL_PROFILES_EMPTY = "Local profiles: (none)"
MESSAGE_LOCAL_PROFILE_HEADER = "Local profile:"
MESSAGE_LOCAL_PROFILE_ACTIVE = "  active={name}"
MESSAGE_LOCAL_PROFILE_DEFAULT = "  default={name}"
MESSAGE_LOCAL_PROFILE_AVAILABLE = "  available={count}"
MESSAGE_ERR_REGISTRY_DEVICE_NOT_FOUND = "ERROR: Device not found in registry."
MESSAGE_SOURCE_LOCAL = "SOURCE: local"
MESSAGE_LOCAL_CONFIG_RAW = "Local bridgeConfig (raw):"
MESSAGE_LOCAL_REGISTRY_DEVICE = "Local registry device {label}:"
MESSAGE_LOCAL_REGISTRY_EMPTY = "  (no fields)"
MESSAGE_REGISTRY_FIELD_FMT = "  {key}={value}"
MESSAGE_REGISTRY_FIELD_FMT_NAMED = "  {key}={value} ({name})"
MESSAGE_MAPPINGS_READ_FAIL = "WARNING: Failed to read CAN mappings: {path}"
HELP_SHOW_TEXT = (
    "show <status|groups|group <name>|devices|device <name>|device registry <name>|bindings|"
    "selected-device|runtime-state|config|config local-raw|profiles|profile> [--json] [robot|local|both]\n"
    "  Defaults: robot if connected, otherwise local."
)
MESSAGE_AUTO_MERGE_FAIL = "WARNING: Failed to auto-load default profiles: {path}"
MESSAGE_AUTO_MERGE_OK = "Loaded default profiles: {path}"
MESSAGE_ERR_PROFILE_MIX = (
    "ERROR: Profiles mismatch. Use 'import config <path>' to replace groups."
)
MESSAGE_ERR_PROFILE_HASH = (
    "ERROR: Profiles hash mismatch (local={local}, incoming={incoming}). "
    "Use 'import config <path>' to replace groups."
)
MESSAGE_ERR_PROFILE_MISSING_HASH = (
    "ERROR: Local groups loaded without profiles; use 'import config <path>' to replace groups."
)
MESSAGE_ERR_PROFILE_REQUIRED = "ERROR: Profile not selected. Use 'profile <name>'."
MESSAGE_ERR_PROFILE_UNKNOWN = "ERROR: Profile not found: {name}."

FIELD_MANUFACTURER = "manufacturer"
FIELD_DEVICE_TYPE = "deviceType"
FIELD_DEVICE_ID = "deviceId"
FIELD_ID = "id"
FIELD_INTERFACE = "interface"
FIELD_LABEL = "label"
FIELD_TYPE = "type"

TEST_TYPE_JOYSTICK = "joystick"
TEST_TYPE_BUTTON = "button"
TEST_TYPE_COMPOSITE = "composite"
TEST_TYPE_DEADBAND_SWEEP = "deadbandSweep"

TERMINATION_HOLD = "hold"
TERMINATION_TIME = "time"
TERMINATION_ROTATION = "rotation"
TERMINATION_LIMITSWITCH = "limitswitch"

DEADBAND_MIN = 0.0
DEADBAND_MAX = 1.0
DUTY_MIN = -1.0
DUTY_MAX = 1.0
TIME_MIN_SEC = 0.0
ROTATION_MIN = 0.0
PROMPT_OVERWRITE = "Test '{name}' exists. Overwrite? (y/N): "
CONFIRM_YES = "y"
TIME_ON_TIMEOUT_DEFAULT = "fail"
GLOBAL_LABEL = "global"
DEFAULT_PROFILE_LOCAL = "local"
LIMIT_SWITCH_KEY_ENABLED = "enabled"
LIMIT_SWITCH_KEY_ON_HIT = "onHit"
LIMIT_SWITCH_KEY_ID = "id"
LIMIT_SWITCH_ON_HIT_DEFAULT = "pass"
LIMIT_SWITCH_DEFAULT = {
    LIMIT_SWITCH_KEY_ENABLED: True,
    LIMIT_SWITCH_KEY_ON_HIT: LIMIT_SWITCH_ON_HIT_DEFAULT,
}
DEVICE_JOIN_SEPARATOR = ", "

MESSAGE_ERROR_TEST_SUBCOMMAND = "ERROR: test requires a subcommand."
MESSAGE_ERROR_TEST_SET_NAME = "ERROR: test set requires a name."
MESSAGE_ERROR_TEST_EXISTS = "ERROR: Test already exists."
MESSAGE_ERROR_TEST_NOT_FOUND = "ERROR: Test not found."
MESSAGE_ERROR_UNKNOWN_TEST = "ERROR: Unknown test command."
MESSAGE_ERROR_INVALID_TEST_COMMAND = "ERROR: Invalid test authoring command."
MESSAGE_ERROR_WITH_TEXT = "ERROR: {message}"
MESSAGE_ERROR_WITH_TEST = "ERROR: {message} ({test})"
MESSAGE_WARNING_WITH_TEST = "WARNING: {message} ({test})"
MESSAGE_ERROR_TEST_MODE = "ERROR: No active test."
MESSAGE_ERROR_TYPE = "ERROR: type must be joystick, button, composite, or deadbandSweep."
MESSAGE_ERROR_DEVICE_DUP = "WARNING: Device already present."
MESSAGE_ERROR_INPUT_SOURCE_TYPE = "ERROR: inputSource only valid for joystick/button/composite tests."
MESSAGE_ERROR_INPUT_SOURCE_VALUE = "ERROR: inputSource requires <controller>.<inputId>."
MESSAGE_ERROR_DEADBAND_TYPE = "ERROR: deadband only valid for joystick tests."
MESSAGE_ERROR_DEADBAND_NUMBER = "ERROR: deadband requires a number."
MESSAGE_ERROR_DEADBAND_RANGE = "ERROR: deadband must be 0.0 to 1.0."
MESSAGE_ERROR_DUTY_TYPE = "ERROR: duty only valid for button/composite tests."
MESSAGE_ERROR_DUTY_NUMBER = "ERROR: duty requires a number."
MESSAGE_ERROR_DUTY_RANGE = "ERROR: duty must be -1.0 to 1.0."
MESSAGE_ERROR_TERMINATION = "ERROR: unknown termination type."
MESSAGE_ERROR_TERMINATION_TIME = "ERROR: termination time requires a number."
MESSAGE_ERROR_TERMINATION_TIME_RANGE = "ERROR: termination time must be >= 0."
MESSAGE_ERROR_TERMINATION_ROTATION = "ERROR: termination rotation requires a number."
MESSAGE_ERROR_TERMINATION_ROTATION_RANGE = "ERROR: termination rotation must be >= 0."
MESSAGE_ERROR_ROTATION_TYPE = "ERROR: rotation only valid for button/composite tests."
MESSAGE_ERROR_TIME_TYPE = "ERROR: time only valid for button/composite tests."
MESSAGE_ERROR_HOLD_TYPE = "ERROR: hold only valid for button/composite tests."
MESSAGE_ERROR_LIMITSWITCH_TYPE = "ERROR: limitswitch only valid for button/composite tests."
MESSAGE_ERROR_DEADBAND_SWEEP_TYPE = "ERROR: deadbandSweep only valid for deadbandSweep tests."
MESSAGE_ERROR_DEADBAND_SWEEP_FIELD = "ERROR: deadbandSweep requires a field name and value."
MESSAGE_ERROR_DEVICE_LABEL = "ERROR: device label not found in active profile."
MESSAGE_ERROR_DEVICE_LABEL_DUPLICATE = "ERROR: duplicate device labels in profile."
MESSAGE_ERROR_SHOW_TESTS = "ERROR: show tests | show test <name>"
MESSAGE_ERROR_WRITE_TESTS = "ERROR: write tests <path>"
MESSAGE_SELECTED_TEST_SET = "Selected test set: {name}"
MESSAGE_CANCELLED = "Cancelled."
MESSAGE_DELETED_TEST = "Deleted test: {name}"
MESSAGE_WROTE_TESTS = "Wrote tests to {path}."
MESSAGE_ACTIVE_TEST_SET = "Active test set: {name}"
MESSAGE_TEST_LIST_ENTRY = "- {name} ({type}) devices={count} enabled={enabled}"
MESSAGE_TEST_HEADER = "Test: {name}"
MESSAGE_TEST_TYPE = "  type: {type}"
MESSAGE_TEST_ENABLED = "  enabled: {enabled}"
MESSAGE_TEST_DEVICES = "  devices: {devices}"
MESSAGE_TEST_INPUT_SOURCE = "  inputSource: {source}"
MESSAGE_TEST_DEADBAND = "  deadband: {deadband}"
MESSAGE_TEST_DUTY = "  duty: {duty}"
MESSAGE_TEST_TERMINATION = "  termination: hold={hold} time={time} rotation={rotation}"
MESSAGE_TEST_LIMIT_SWITCH = "  limitSwitch: {limit}"
MESSAGE_TEST_ROTATION = "  rotation: {rotation}"
MESSAGE_TEST_TIME = "  time: {time}"
MESSAGE_TEST_HOLD = "  hold: {hold}"
MESSAGE_TEST_DEADBAND_SWEEP = "  deadbandSweep: {sweep}"


@dataclass
class CliMode:
    name: str
    group: str = ""
    device: str = ""
    test: str = ""


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
        parser_kind: Optional[str] = None,
        echo_enabled: bool = False,
    ) -> None:
        self._session = session
        self._batch = batch
        self._conflict_policy = conflict_policy
        self._echo_enabled = echo_enabled
        self._tests_device_catalog: Dict[str, object] = {}
        self._tests_duplicate_labels: set[str] = set()
        parser_choice = (parser_kind or CLI_PARSER_KIND).strip().lower()
        if parser_choice not in (CLI_PARSER_CONST["legacy"], CLI_PARSER_CONST["ebnf"]):
            parser_choice = CLI_PARSER_CONST["legacy"]
        self._parser_kind = parser_choice
        self._parser = (
            BridgeCliParser(strict=bool(CLI_PARSER_CONST["strict_default"]))
            if parser_choice == CLI_PARSER_CONST["ebnf"]
            else None
        )
        self._ast_executor = BridgeCliAstExecutor(self)
        self._modes: List[CliMode] = [CliMode("exec")]
        self._last_seq: Optional[int] = None
        self._local_config: Optional[Dict[str, object]] = None
        self._local_config_path: Optional[str] = None
        self._local_loaded_at: Optional[float] = None
        self._local_root_payload: Optional[Dict[str, object]] = None
        self._local_root_path: Optional[str] = None
        self._local_root_hash: Optional[str] = None
        self._show_label_seq: Dict[int, str] = {}
        self._local_devices_locked: bool = False
        self._profiles_dirty: bool = False
        self._tracker = CommandTracker(timeout_sec=2.0, max_retries=0)
        self._tests_model: Optional[TestAuthoringModel] = None
        self._tests_path: Optional[Path] = None
        self._tests_dirty: bool = False
        self._tests_active_set: str = ""
        self._tests_profile: Optional[str] = None
        self._groups_profile: Optional[str] = None
        self._can_mappings: Optional[Dict[str, Dict[str, str]]] = None

    def run_interactive(self) -> int:
        """
        NAME
            run_interactive - Enter the interactive prompt loop.
        """
        self._auto_merge_default_profiles()
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
        self._auto_merge_default_profiles()
        lint_error = self._lint_script(lines)
        if lint_error:
            print(f"ERROR: {lint_error}")
            return 2
        for raw in lines:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if self._echo_enabled:
                print(f">> {line}")
            code = self._execute_line(line)
            if code is not None:
                return code
        return 0

    def _prompt(self) -> str:
        mode = self._modes[-1]
        if mode.name == "exec":
            return "bridge> "
        if mode.name == MODE_CONFIG:
            suffix = self._profile_prompt_suffix()
            return f"bridge(config{suffix})# "
        if mode.name == "group":
            suffix = self._profile_prompt_suffix()
            return f"bridge(config{suffix}-group-{mode.group})# "
        if mode.name == "device":
            return f"bridge(config-device-{mode.device})# "
        if mode.name == MODE_TEST:
            label = mode.test or TEST_LABEL_UNKNOWN
            return f"bridge(config-test-{label})# "
        return "bridge> "

    def _profile_prompt_suffix(self) -> str:
        """
        NAME
            _profile_prompt_suffix - Render prompt suffix for active profile.
        """
        profile = self._groups_profile or ""
        if profile:
            return f"-profile-{profile}"
        return ""

    def _auto_merge_default_profiles(self) -> None:
        """
        NAME
            _auto_merge_default_profiles - Load the default bringup_system.json if present.
        """
        if self._local_config is not None:
            return
        path = profiles_canonical_path()
        if not path.exists():
            return
        plan = import_config(str(path), self._conflict_policy, self._active_profile_name())
        if not plan.ok:
            print(MESSAGE_AUTO_MERGE_FAIL.format(path=path))
            return
        code = self._apply_config_plan(plan, prompt_on_replace=False)
        if code is None or code == 0:
            print(MESSAGE_AUTO_MERGE_OK.format(path=path))

    def _profiles_hash(self, payload: Optional[Dict[str, object]]) -> Optional[str]:
        """
        NAME
            _profiles_hash - Compute the profiles hash for a payload.
        """
        if not isinstance(payload, dict):
            return None
        try:
            return compute_profiles_hash(payload)
        except Exception:
            return None

    def _default_profile_name(self) -> Optional[str]:
        """
        NAME
            _default_profile_name - Return the default profile name from local payload.
        """
        payload = self._local_root_payload
        if not isinstance(payload, dict):
            return None
        profiles = payload.get(KEY_PROFILES)
        if not isinstance(profiles, dict) or not profiles:
            return None
        default_profile = payload.get(KEY_DEFAULT_PROFILE)
        if isinstance(default_profile, str) and default_profile in profiles:
            return default_profile
        return next(iter(profiles.keys()))

    def _active_profile_name(self) -> Optional[str]:
        """
        NAME
            _active_profile_name - Return the active profile name for group editing.
        """
        if self._groups_profile:
            return self._groups_profile
        default_profile = self._default_profile_name()
        if default_profile:
            return default_profile
        return self._fallback_profile_name()

    def _fallback_profile_name(self) -> Optional[str]:
        """
        NAME
            _fallback_profile_name - Return a single local profile if present.
        """
        if not self._local_config:
            return None
        by_profile = self._local_config.get(KEY_BRIDGE_BY_PROFILE)
        if not isinstance(by_profile, dict):
            return None
        names = [name for name in by_profile.keys() if isinstance(name, str)]
        if len(names) == COUNT_ONE:
            return names[COUNT_ZERO]
        return None

    def _local_profile_entry(self, profile_name: str, create: bool = False) -> Dict[str, object]:
        """
        NAME
            _local_profile_entry - Return or create a per-profile bridgeConfig entry.
        """
        self._ensure_local_config()
        if not isinstance(self._local_config, dict):
            return {}
        by_profile = self._local_config.get(KEY_BRIDGE_BY_PROFILE)
        if not isinstance(by_profile, dict):
            by_profile = {}
            self._local_config[KEY_BRIDGE_BY_PROFILE] = by_profile
        entry = by_profile.get(profile_name)
        if isinstance(entry, dict):
            return entry
        if not create:
            return {}
        entry = {
            KEY_BRIDGE_GROUPS: [],
            KEY_BRIDGE_SELECTED_DEVICE: {KEY_DEVICE: EMPTY_STRING, CMD_ENABLED: False},
        }
        by_profile[profile_name] = entry
        return entry

    def _profile_device_entries(self, profile_name: str) -> List[Dict[str, object]]:
        """
        NAME
            _profile_device_entries - Return device entries for a profile.
        """
        if not self._local_root_payload:
            return []
        devices = devices_from_profiles_payload(self._local_root_payload, profile_name)
        if devices is None:
            return []
        return devices

    def _profile_device_labels(self, profile_name: str) -> set[str]:
        """
        NAME
            _profile_device_labels - Return device label set for a profile.
        """
        labels = set()
        for device in self._profile_device_entries(profile_name):
            name = str(device.get("name", "")).strip()
            if name:
                labels.add(name.lower())
        return labels

    def _local_groups(self, profile_name: str, create: bool = False) -> List[Dict[str, object]]:
        """
        NAME
            _local_groups - Return group list for a profile.
        """
        entry = self._local_profile_entry(profile_name, create=create)
        groups = entry.get(KEY_BRIDGE_GROUPS)
        if isinstance(groups, list):
            return groups
        groups = []
        entry[KEY_BRIDGE_GROUPS] = groups
        return groups

    def _sync_group_profile(self) -> None:
        """
        NAME
            _sync_group_profile - Ensure group profile exists in loaded profiles.
        """
        profiles = self._local_root_payload.get(KEY_PROFILES) if isinstance(self._local_root_payload, dict) else None
        if not isinstance(profiles, dict) or not profiles:
            self._groups_profile = None
            return
        if self._groups_profile and self._groups_profile in profiles:
            return
        self._groups_profile = self._default_profile_name()

    def _set_active_profile(self, name: str) -> bool:
        """
        NAME
            _set_active_profile - Set active profile for local group operations.
        """
        profiles = self._local_root_payload.get(KEY_PROFILES) if isinstance(self._local_root_payload, dict) else None
        key = name.strip()
        if not key:
            print(MESSAGE_ERR_PROFILE_REQUIRED)
            return False
        if not isinstance(profiles, dict) or not profiles:
            self._groups_profile = key
            self._local_profile_entry(key, create=True)
            return True
        if key not in profiles:
            print(MESSAGE_ERR_PROFILE_UNKNOWN.format(name=name))
            return False
        self._groups_profile = key
        self._local_profile_entry(key, create=True)
        return True

    def _require_active_profile(self) -> Optional[str]:
        """
        NAME
            _require_active_profile - Return active profile or report error.
        """
        profile = self._active_profile_name()
        if not profile:
            print(MESSAGE_ERR_PROFILE_REQUIRED)
            return None
        return profile

    def _local_group_count(self) -> int:
        """
        NAME
            _local_group_count - Return number of local groups.
        """
        if not isinstance(self._local_config, dict):
            return COUNT_ZERO
        profile_name = self._active_profile_name()
        if not profile_name:
            return COUNT_ZERO
        entry = self._local_profile_entry(profile_name)
        groups = entry.get(KEY_BRIDGE_GROUPS)
        if not isinstance(groups, list):
            return COUNT_ZERO
        return len(groups)

    def validate_config_file(self, path: str) -> tuple[bool, str, Optional[Dict[str, object]]]:
        """
        NAME
            validate_config_file - Wrapper to validate a config file path.
        """
        return validate_config_file(path)

    def validate_config_data(self, config: Dict[str, object]) -> tuple[bool, str]:
        """
        NAME
            validate_config_data - Wrapper to validate an in-memory config.
        """
        return validate_config_data(config, self._local_root_payload)

    def _execute_line(self, line: str) -> Optional[int]:
        try:
            if self._parser_kind == CLI_PARSER_CONST["ebnf"] and self._parser is not None:
                parsed = self._parser.parse(line, mode=self._modes[-1].name)
                tokens = parsed.tokens
                ast = parsed.ast
            else:
                tokens = self._split_command(line)
                ast = None
        except (CliParseError, ValueError) as exc:
            if self._parser_kind == CLI_PARSER_CONST["ebnf"]:
                tokens = self._split_command(line)
                if self._is_test_authoring_command(tokens):
                    return self._execute_test_authoring(tokens)
            print(f"ERROR: {exc}")
            return None
        if self._is_test_authoring_command(tokens):
            return self._execute_test_authoring(tokens)
        if ast is not None:
            return self._ast_executor.execute(ast)
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
        if cmd == "echo":
            if len(tokens) < 2:
                state = "on" if self._echo_enabled else "off"
                print(f"echo {state}")
                return None
            value = tokens[1].lower()
            if value in ("on", "true", "1", "yes"):
                self._echo_enabled = True
                return None
            if value in ("off", "false", "0", "no"):
                self._echo_enabled = False
                return None
            print("ERROR: echo requires on/off.")
            return 2 if self._batch else None

        mode = self._modes[-1].name
        if mode == "exec":
            return self._exec_command(tokens)
        if mode == MODE_CONFIG:
            return self._config_command(tokens)
        if mode == "group":
            return self._group_command(tokens)
        if mode == "device":
            return self._device_command(tokens)
        if mode == MODE_TEST:
            return self._test_mode_command(tokens)
        print("ERROR: unknown mode.")
        return None

    def _is_test_authoring_command(self, tokens: List[str]) -> bool:
        """
        NAME
            _is_test_authoring_command - Identify test authoring commands.

        PARAMETERS
            tokens - Tokenized command input.

        RETURNS
            True when the command targets test authoring workflows.
        """

        if not tokens:
            return False
        mode = self._modes[-1].name
        if mode == MODE_TEST:
            return True
        if mode == MODE_CONFIG and tokens[0].lower() == CMD_TEST:
            return True
        if tokens[0].lower() == CMD_SHOW and len(tokens) > 1:
            return tokens[1].lower().startswith(CMD_TEST)
        if tokens[0].lower() == CMD_WRITE and len(tokens) > 1:
            return tokens[1].lower() == CMD_TESTS
        return False

    def _execute_test_authoring(self, tokens: List[str]) -> Optional[int]:
        """
        NAME
            _execute_test_authoring - Dispatch test authoring commands.

        PARAMETERS
            tokens - Tokenized command input.

        RETURNS
            None on success, or a CLI exit code.
        """

        mode = self._modes[-1].name
        if mode == MODE_TEST:
            return self._test_mode_command(tokens)
        if mode == MODE_CONFIG and tokens[0].lower() == CMD_TEST:
            return self._config_test_command(tokens)
        if tokens[0].lower() == CMD_SHOW:
            return self._show_tests_command(tokens)
        if tokens[0].lower() == CMD_WRITE:
            return self._write_tests_command(tokens)
        print(MESSAGE_ERROR_INVALID_TEST_COMMAND)
        return None

    def _ensure_tests_loaded(self) -> None:
        """
        NAME
            _ensure_tests_loaded - Load tests JSON into the authoring model.

        DESCRIPTION
            Loads the default tests file from the repo root when present,
            otherwise falls back to the deploy copy.
        """

        if self._tests_model is not None:
            return
        root_path = repo_root() / TESTS_FILENAME
        deploy_path = tests_deploy_path()
        path = root_path if root_path.exists() else deploy_path
        payload: Dict[str, object] = {}
        if path.exists():
            try:
                payload = load_tests_payload(path)
            except Exception:
                payload = {}
        self._tests_model = model_from_payload(payload or {})
        self._tests_path = path
        if not self._tests_profile:
            self._tests_profile = get_default_profile()
        try:
            catalog, duplicates = load_profile_devices(self._tests_profile)
            self._tests_device_catalog = catalog
            self._tests_duplicate_labels = duplicates
        except Exception:
            self._tests_device_catalog = {}
            self._tests_duplicate_labels = set()
        default_set = self._tests_model.default_test_set if self._tests_model else EMPTY_STRING
        self._tests_active_set = default_set or DEFAULT_TEST_SET

    def _config_test_command(self, tokens: List[str]) -> Optional[int]:
        """
        NAME
            _config_test_command - Handle config-mode test authoring commands.
        """

        self._ensure_tests_loaded()
        if len(tokens) < 2:
            print(MESSAGE_ERROR_TEST_SUBCOMMAND)
            return None
        sub = tokens[1].lower()
        if sub == CMD_SET and len(tokens) >= 3:
            name = tokens[2]
            if not name:
                print(MESSAGE_ERROR_TEST_SET_NAME)
                return None
            self._tests_active_set = name
            if self._tests_model and name not in self._tests_model.test_sets:
                self._tests_model.test_sets[name] = TestSetModel(name=name, tests=[])
                self._tests_dirty = True
            print(MESSAGE_SELECTED_TEST_SET.format(name=name))
            return None
        if sub == CMD_CREATE and len(tokens) >= 3:
            name = tokens[2]
            err = validate_test_name(name)
            if err:
                print(MESSAGE_ERROR_WITH_TEXT.format(message=err))
                return None
            test_set = self._get_active_test_set()
            if self._find_test(name, test_set):
                if self._batch:
                    print(MESSAGE_ERROR_TEST_EXISTS)
                    return None
                prompt = PROMPT_OVERWRITE.format(name=name)
                confirm = input(prompt).strip().lower()
                if confirm != CONFIRM_YES:
                    print(MESSAGE_CANCELLED)
                    return None
                self._delete_test(name, test_set)
            test_set.tests.append(
                TestModel(
                    name=name,
                    test_type=TEST_TYPE_COMPOSITE,
                    devices=[],
                    button=TestBindingButton(),
                    termination=TerminationModel(),
                    enabled=False,
                )
            )
            self._tests_dirty = True
            self._modes.append(CliMode(MODE_TEST, test=name))
            return None
        if sub == CMD_DELETE and len(tokens) >= 3:
            name = tokens[2]
            test_set = self._get_active_test_set()
            if not self._delete_test(name, test_set):
                print(MESSAGE_ERROR_TEST_NOT_FOUND)
                return None
            self._tests_dirty = True
            print(MESSAGE_DELETED_TEST.format(name=name))
            return None
        if len(tokens) >= 2 and sub not in (CMD_CREATE, CMD_DELETE, CMD_SET):
            name = tokens[1]
            test_set = self._get_active_test_set()
            if not self._find_test(name, test_set):
                print(MESSAGE_ERROR_TEST_NOT_FOUND)
                return None
            self._modes.append(CliMode(MODE_TEST, test=name))
            return None
        print(MESSAGE_ERROR_UNKNOWN_TEST)
        return None

    def _test_mode_command(self, tokens: List[str]) -> Optional[int]:
        """
        NAME
            _test_mode_command - Handle test-mode configuration commands.
        """

        self._ensure_tests_loaded()
        if not tokens:
            return None
        cmd = tokens[0].lower()
        if cmd in (CMD_EXIT, CMD_END):
            self._pop_mode()
            return None
        test = self._get_active_test()
        if test is None:
            print(MESSAGE_ERROR_TEST_MODE)
            return None
        if cmd == CMD_TYPE and len(tokens) >= 2:
            kind_raw = tokens[1]
            kind = kind_raw.lower()
            kind_map = {
                TEST_TYPE_JOYSTICK: TEST_TYPE_JOYSTICK,
                TEST_TYPE_BUTTON: TEST_TYPE_BUTTON,
                TEST_TYPE_COMPOSITE: TEST_TYPE_COMPOSITE,
                TEST_TYPE_DEADBAND_SWEEP.lower(): TEST_TYPE_DEADBAND_SWEEP,
            }
            if kind not in kind_map:
                print(MESSAGE_ERROR_TYPE)
                return None
            test.test_type = kind_map[kind]
            if test.test_type == TEST_TYPE_JOYSTICK:
                test.joystick = test.joystick or TestBindingJoystick()
                test.button = None
                test.deadband_sweep = None
            elif test.test_type == TEST_TYPE_DEADBAND_SWEEP:
                from tools.common.test_authoring.model import DeadbandSweepModel
                test.deadband_sweep = test.deadband_sweep or DeadbandSweepModel()
                test.joystick = None
                test.button = None
            else:
                test.button = test.button or TestBindingButton()
                test.joystick = None
                test.deadband_sweep = None
            self._tests_dirty = True
            return None
        if cmd == CMD_DEVICE and len(tokens) >= 3 and tokens[1].lower() == CMD_ADD:
            label = tokens[2]
            if not self._is_device_label_valid(label):
                if self._tests_duplicate_labels:
                    print(MESSAGE_ERROR_DEVICE_LABEL_DUPLICATE)
                else:
                    print(MESSAGE_ERROR_DEVICE_LABEL)
                return None
            if label in test.devices:
                print(MESSAGE_ERROR_DEVICE_DUP)
                return None
            test.devices.append(label)
            self._tests_dirty = True
            return None
        if cmd == CMD_NO and len(tokens) >= 3 and tokens[1].lower() == CMD_DEVICE:
            label = tokens[2]
            if label in test.devices:
                test.devices.remove(label)
                self._tests_dirty = True
            return None
        if cmd == CMD_INPUT_SOURCE:
            if test.test_type not in (TEST_TYPE_JOYSTICK, TEST_TYPE_BUTTON, TEST_TYPE_COMPOSITE):
                print(MESSAGE_ERROR_INPUT_SOURCE_TYPE)
                return None
            if len(tokens) != 2:
                print(MESSAGE_ERROR_INPUT_SOURCE_VALUE)
                return None
            value = tokens[1].strip()
            if "." not in value:
                print(MESSAGE_ERROR_INPUT_SOURCE_VALUE)
                return None
            test.input_source = value
            self._tests_dirty = True
            return None
        if cmd == CMD_DEADBAND and len(tokens) >= 2:
            if test.test_type != TEST_TYPE_JOYSTICK:
                print(MESSAGE_ERROR_DEADBAND_TYPE)
                return None
            try:
                value = float(tokens[1])
            except ValueError:
                print(MESSAGE_ERROR_DEADBAND_NUMBER)
                return None
            if value < DEADBAND_MIN or value > DEADBAND_MAX:
                print(MESSAGE_ERROR_DEADBAND_RANGE)
                return None
            test.joystick = test.joystick or TestBindingJoystick()
            test.joystick.deadband = value
            self._tests_dirty = True
            return None
        if cmd == CMD_DUTY and len(tokens) >= 2:
            if test.test_type not in (TEST_TYPE_BUTTON, TEST_TYPE_COMPOSITE):
                print(MESSAGE_ERROR_DUTY_TYPE)
                return None
            try:
                value = float(tokens[1])
            except ValueError:
                print(MESSAGE_ERROR_DUTY_NUMBER)
                return None
            if value < DUTY_MIN or value > DUTY_MAX:
                print(MESSAGE_ERROR_DUTY_RANGE)
                return None
            test.button = test.button or TestBindingButton()
            test.button.duty = value
            self._tests_dirty = True
            return None
        if cmd == CMD_TERMINATION and len(tokens) >= 2:
            if test.test_type not in (TEST_TYPE_BUTTON, TEST_TYPE_COMPOSITE):
                print(MESSAGE_ERROR_TERMINATION)
                return None
            term = test.termination
            kind = tokens[1].lower()
            if kind == TERMINATION_HOLD:
                term.hold_enabled = True
                self._tests_dirty = True
                return None
            if kind == TERMINATION_TIME and len(tokens) >= 3:
                try:
                    value = float(tokens[2])
                except ValueError:
                    print(MESSAGE_ERROR_TERMINATION_TIME)
                    return None
                if value < TIME_MIN_SEC:
                    print(MESSAGE_ERROR_TERMINATION_TIME_RANGE)
                    return None
                term.time_sec = value
                term.time_on_timeout = term.time_on_timeout or TIME_ON_TIMEOUT_DEFAULT
                self._tests_dirty = True
                return None
            if kind == TERMINATION_ROTATION and len(tokens) >= 3:
                try:
                    value = float(tokens[2])
                except ValueError:
                    print(MESSAGE_ERROR_TERMINATION_ROTATION)
                    return None
                if value < ROTATION_MIN:
                    print(MESSAGE_ERROR_TERMINATION_ROTATION_RANGE)
                    return None
                term.rotation_limit = value
                self._tests_dirty = True
                return None
            if kind == TERMINATION_LIMITSWITCH:
                limit = term.limit_switch or deepcopy(LIMIT_SWITCH_DEFAULT)
                if len(tokens) >= 3:
                    limit[LIMIT_SWITCH_KEY_ID] = tokens[2]
                term.limit_switch = limit
                self._tests_dirty = True
                return None
            print(MESSAGE_ERROR_TERMINATION)
            return None
        if cmd == CMD_ROTATION and len(tokens) >= 2:
            if test.test_type not in (TEST_TYPE_BUTTON, TEST_TYPE_COMPOSITE):
                print(MESSAGE_ERROR_ROTATION_TYPE)
                return None
            term = test.termination
            field = tokens[1].lower()
            if field == "limit" and len(tokens) >= 3:
                try:
                    value = float(tokens[2])
                except ValueError:
                    print(MESSAGE_ERROR_TERMINATION_ROTATION)
                    return None
                if value < ROTATION_MIN:
                    print(MESSAGE_ERROR_TERMINATION_ROTATION_RANGE)
                    return None
                term.rotation_limit = value
                self._tests_dirty = True
                return None
            if field == "encoderkey" and len(tokens) >= 3:
                term.rotation_encoder_key = tokens[2]
                self._tests_dirty = True
                return None
            if field == "encodersource" and len(tokens) >= 3:
                term.rotation_encoder_source = tokens[2]
                self._tests_dirty = True
                return None
            if field == "encodermotorindex" and len(tokens) >= 3:
                try:
                    term.rotation_encoder_motor_index = int(tokens[2])
                except ValueError:
                    print(MESSAGE_ERROR_TERMINATION_ROTATION)
                    return None
                self._tests_dirty = True
                return None
            if field == "encodercountsperrev" and len(tokens) >= 3:
                try:
                    term.rotation_encoder_counts_per_rev = float(tokens[2])
                except ValueError:
                    print(MESSAGE_ERROR_TERMINATION_ROTATION)
                    return None
                self._tests_dirty = True
                return None
            print(MESSAGE_ERROR_TERMINATION)
            return None
        if cmd == CMD_TIME and len(tokens) >= 2:
            if test.test_type not in (TEST_TYPE_BUTTON, TEST_TYPE_COMPOSITE):
                print(MESSAGE_ERROR_TIME_TYPE)
                return None
            term = test.termination
            field = tokens[1].lower()
            if field == "timeout" and len(tokens) >= 3:
                try:
                    value = float(tokens[2])
                except ValueError:
                    print(MESSAGE_ERROR_TERMINATION_TIME)
                    return None
                if value < TIME_MIN_SEC:
                    print(MESSAGE_ERROR_TERMINATION_TIME_RANGE)
                    return None
                term.time_sec = value
                self._tests_dirty = True
                return None
            if field == "ontimeout" and len(tokens) >= 3:
                term.time_on_timeout = tokens[2]
                self._tests_dirty = True
                return None
            print(MESSAGE_ERROR_TERMINATION)
            return None
        if cmd == CMD_HOLD and len(tokens) >= 2:
            if test.test_type not in (TEST_TYPE_BUTTON, TEST_TYPE_COMPOSITE):
                print(MESSAGE_ERROR_HOLD_TYPE)
                return None
            term = test.termination
            field = tokens[1].lower()
            if field == "onrelease" and len(tokens) >= 3:
                term.hold_enabled = True
                term.hold_on_release = tokens[2]
                self._tests_dirty = True
                return None
            print(MESSAGE_ERROR_TERMINATION)
            return None
        if cmd == CMD_LIMITSWITCH and len(tokens) >= 2:
            if test.test_type not in (TEST_TYPE_BUTTON, TEST_TYPE_COMPOSITE):
                print(MESSAGE_ERROR_LIMITSWITCH_TYPE)
                return None
            term = test.termination
            limit = term.limit_switch or deepcopy(LIMIT_SWITCH_DEFAULT)
            field = tokens[1].lower()
            if field == "onhit" and len(tokens) >= 3:
                limit[LIMIT_SWITCH_KEY_ON_HIT] = tokens[2]
                term.limit_switch = limit
                self._tests_dirty = True
                return None
            if field == "id" and len(tokens) >= 3:
                limit[LIMIT_SWITCH_KEY_ID] = tokens[2]
                term.limit_switch = limit
                self._tests_dirty = True
                return None
            print(MESSAGE_ERROR_TERMINATION)
            return None
        if cmd == CMD_DEADBAND_SWEEP:
            if test.test_type != TEST_TYPE_DEADBAND_SWEEP:
                print(MESSAGE_ERROR_DEADBAND_SWEEP_TYPE)
                return None
            if len(tokens) < 3:
                print(MESSAGE_ERROR_DEADBAND_SWEEP_FIELD)
                return None
            if test.deadband_sweep is None:
                from tools.common.test_authoring.model import DeadbandSweepModel
                test.deadband_sweep = DeadbandSweepModel()
            sweep = test.deadband_sweep
            field = tokens[1]
            value = tokens[2]
            try:
                if field == "startDuty":
                    sweep.start_duty = float(value)
                elif field == "maxDuty":
                    sweep.max_duty = float(value)
                elif field == "stepDuty":
                    sweep.step_duty = float(value)
                elif field == "stepHoldSec":
                    sweep.step_hold_sec = float(value)
                elif field == "motionThresholdRot":
                    sweep.motion_threshold_rot = float(value)
                elif field == "encoderCountsPerRev":
                    sweep.encoder_counts_per_rev = float(value)
                elif field == "requiredSamples":
                    sweep.required_samples = int(value)
                elif field == "encoderMotorIndex":
                    sweep.encoder_motor_index = int(value)
                elif field == "encoderKey":
                    sweep.encoder_key = value
                elif field == "encoderSource":
                    sweep.encoder_source = value
                else:
                    print(MESSAGE_ERROR_DEADBAND_SWEEP_FIELD)
                    return None
            except ValueError:
                print(MESSAGE_ERROR_DEADBAND_SWEEP_FIELD)
                return None
            self._tests_dirty = True
            return None
        if cmd == CMD_ENABLED and len(tokens) >= 2:
            value = tokens[1].lower()
            if value in ("true", "on", "1", "yes"):
                test.enabled = True
            elif value in ("false", "off", "0", "no"):
                test.enabled = False
            else:
                print("ERROR: enabled requires true/false.")
                return None
            self._tests_dirty = True
            return None
        if cmd == CMD_SHOW:
            self._print_test(test)
            return None
        print(MESSAGE_ERROR_UNKNOWN_TEST)
        return None

    def _is_device_label_valid(self, label: str) -> bool:
        """
        NAME
            _is_device_label_valid - Validate device label in active profile.

        PARAMETERS
            label - Proposed device label string.

        RETURNS
            True when the label is known in the active profile.
        """

        if not label or not isinstance(label, str):
            return False
        if self._tests_duplicate_labels:
            return False
        if not self._tests_device_catalog:
            return False
        return label in self._tests_device_catalog

    def _show_tests_command(self, tokens: List[str]) -> Optional[int]:
        """
        NAME
            _show_tests_command - Render test authoring state.
        """

        self._ensure_tests_loaded()
        if len(tokens) >= 2 and tokens[1].lower() == CMD_TESTS:
            self._print_tests()
            return None
        if len(tokens) >= 3 and tokens[1].lower() == CMD_TEST:
            test_set = self._get_active_test_set()
            test = self._find_test(tokens[2], test_set)
            if not test:
                print(MESSAGE_ERROR_TEST_NOT_FOUND)
                return None
            self._print_test(test)
            return None
        print(MESSAGE_ERROR_SHOW_TESTS)
        return None

    def _write_tests_command(self, tokens: List[str]) -> Optional[int]:
        """
        NAME
            _write_tests_command - Validate and persist tests JSON.
        """

        self._ensure_tests_loaded()
        if len(tokens) < 3 or tokens[1].lower() != CMD_TESTS:
            print(MESSAGE_ERROR_WRITE_TESTS)
            return None
        path = Path(tokens[2])
        model = self._tests_model or TestAuthoringModel()
        profile = self._tests_profile
        controller_names = load_controller_names()
        result = validate_model(model, profile_name=profile, controller_names=controller_names)
        if not result.ok():
            for issue in result.errors:
                test_name = issue.test_name or GLOBAL_LABEL
                print(
                    MESSAGE_ERROR_WITH_TEST.format(
                        message=issue.message,
                        test=test_name,
                    )
                )
            return None
        for issue in result.warnings:
            test_name = issue.test_name or GLOBAL_LABEL
            print(
                MESSAGE_WARNING_WITH_TEST.format(
                    message=issue.message,
                    test=test_name,
                )
            )
        payload = model_to_payload(model)
        write_tests_payload(path, payload)
        self._tests_dirty = False
        print(MESSAGE_WROTE_TESTS.format(path=path))
        return None

    def _get_active_test_set(self) -> TestSetModel:
        """
        NAME
            _get_active_test_set - Resolve the active test set.
        """

        self._ensure_tests_loaded()
        model = self._tests_model or TestAuthoringModel()
        name = self._tests_active_set or model.default_test_set
        if name not in model.test_sets:
            model.test_sets[name] = TestSetModel(name=name, tests=[])
        self._tests_model = model
        return model.test_sets[name]

    def _find_test(self, name: str, test_set: TestSetModel) -> Optional[TestModel]:
        """
        NAME
            _find_test - Locate a test by name.
        """

        for test in test_set.tests:
            if test.name == name:
                return test
        return None

    def _delete_test(self, name: str, test_set: TestSetModel) -> bool:
        """
        NAME
            _delete_test - Remove a test from a set.
        """

        for idx, test in enumerate(test_set.tests):
            if test.name == name:
                del test_set.tests[idx]
                return True
        return False

    def _get_active_test(self) -> Optional[TestModel]:
        """
        NAME
            _get_active_test - Resolve the currently edited test.
        """

        mode = self._modes[-1]
        if mode.name != MODE_TEST:
            return None
        test_set = self._get_active_test_set()
        return self._find_test(mode.test, test_set)

    def _print_tests(self) -> None:
        """
        NAME
            _print_tests - Render a summary list of tests.
        """

        test_set = self._get_active_test_set()
        print(MESSAGE_ACTIVE_TEST_SET.format(name=test_set.name))
        for test in test_set.tests:
            print(
                MESSAGE_TEST_LIST_ENTRY.format(
                    name=test.name,
                    type=test.test_type,
                    count=len(test.devices),
                    enabled=test.enabled,
                )
            )

    def _print_test(self, test: TestModel) -> None:
        """
        NAME
            _print_test - Render details for a single test.
        """

        print(MESSAGE_TEST_HEADER.format(name=test.name))
        print(MESSAGE_TEST_TYPE.format(type=test.test_type))
        print(MESSAGE_TEST_ENABLED.format(enabled=test.enabled))
        if test.devices:
            devices = DEVICE_JOIN_SEPARATOR.join(test.devices)
            print(MESSAGE_TEST_DEVICES.format(devices=devices))
        if test.input_source:
            print(MESSAGE_TEST_INPUT_SOURCE.format(source=test.input_source))
        else:
            print(MESSAGE_TEST_INPUT_SOURCE.format(source="(none)"))
        if test.test_type == TEST_TYPE_JOYSTICK and test.joystick:
            print(MESSAGE_TEST_DEADBAND.format(deadband=test.joystick.deadband))
        if test.test_type in (TEST_TYPE_BUTTON, TEST_TYPE_COMPOSITE) and test.button:
            print(MESSAGE_TEST_DUTY.format(duty=test.button.duty))
            term = test.termination
            print(
                MESSAGE_TEST_TERMINATION.format(
                    hold=term.hold_enabled,
                    time=term.time_sec,
                    rotation=term.rotation_limit,
                )
            )
            if term.rotation_limit is not None or term.rotation_encoder_key:
                rotation = {
                    "limitRot": term.rotation_limit,
                    "encoderKey": term.rotation_encoder_key,
                    "encoderSource": term.rotation_encoder_source,
                    "encoderMotorIndex": term.rotation_encoder_motor_index,
                    "encoderCountsPerRev": term.rotation_encoder_counts_per_rev,
                }
                print(MESSAGE_TEST_ROTATION.format(rotation=rotation))
            if term.time_sec is not None or term.time_on_timeout:
                time = {"timeoutSec": term.time_sec, "onTimeout": term.time_on_timeout}
                print(MESSAGE_TEST_TIME.format(time=time))
            if term.hold_enabled or term.hold_on_release:
                hold = {"enabled": term.hold_enabled, "onRelease": term.hold_on_release}
                print(MESSAGE_TEST_HOLD.format(hold=hold))
            if term.limit_switch:
                print(MESSAGE_TEST_LIMIT_SWITCH.format(limit=term.limit_switch))
        if test.test_type == TEST_TYPE_DEADBAND_SWEEP and test.deadband_sweep:
            print(MESSAGE_TEST_DEADBAND_SWEEP.format(sweep=test.deadband_sweep))

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
        if cmd == CMD_PROFILE:
            if len(tokens) < 2:
                print(MESSAGE_ERR_PROFILE_REQUIRED)
                return 2 if self._batch else None
            if not self._set_active_profile(tokens[1]):
                return 2 if self._batch else None
            print(f"Active profile: {self._groups_profile}")
            return None
        if cmd == "group" and len(tokens) >= 2 and not self._session.is_connected():
            name = tokens[1]
            if not self._select_or_create_local_group(name):
                return EXIT_CODE_ERROR if self._batch else None
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
                return EXIT_CODE_ERROR if self._batch else None
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
            plan = merge_config(tokens[2], self._conflict_policy, self._active_profile_name())
            return self._apply_config_plan(plan, prompt_on_replace=True)
        if cmd == "import" and len(tokens) >= 3 and tokens[1].lower() == "config":
            plan = import_config(tokens[2], self._conflict_policy, self._active_profile_name())
            return self._apply_config_plan(plan, prompt_on_replace=True)
        if cmd == "export" and len(tokens) >= 3 and tokens[1].lower() == "runtime-groups":
            result = export_runtime_groups(self._session, tokens[2], self._active_profile_name())
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
                ok, message = validate_config_data(self._local_config, self._local_root_payload)
            if ok:
                print("OK: Config is valid.")
                return None
            print(f"ERROR: {message}")
            return 2 if self._batch else None
        if cmd == "save" and len(tokens) >= 3 and tokens[1].lower() == "config":
            result = save_config(self._session, tokens[2], self._active_profile_name())
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
            print(MESSAGE_ERR_SHOW_REQUIRES_TARGET)
            return None
        source, tokens, json_output = self._parse_show_flags(tokens)
        if not tokens:
            print(MESSAGE_ERR_SHOW_REQUIRES_TARGET)
            return None
        target = tokens[0].lower()
        if target == SHOW_TARGET_CONFIG and len(tokens) >= 2:
            name = tokens[1].lower()
            if name == SHOW_CONFIG_LOCAL_RAW:
                target = SHOW_TARGET_CONFIG_RAW
        if (
            target == CMD_DEVICE
            and len(tokens) >= 3
            and tokens[1].lower() == CMD_REGISTRY
        ):
            target = SHOW_TARGET_DEVICE_REGISTRY
            tokens = [SHOW_TARGET_DEVICE_REGISTRY, tokens[2]]
        if target == SHOW_TARGET_CONFIG:
            target = SHOW_TARGET_RUNTIME
        if source == "both":
            local_ok = self._show_local(target, tokens, json_output)
            robot_ok = self._show_robot(target, tokens, json_output)
            if self._batch and (not local_ok or not robot_ok):
                return 2
            return None
        if source == "local":
            if not self._show_local(target, tokens, json_output):
                return EXIT_CODE_ERROR if self._batch else None
            return None
        if source == "robot":
            if not self._show_robot(target, tokens, json_output):
                return EXIT_CODE_ERROR if self._batch else None
            return None
        print(MESSAGE_ERR_UNKNOWN_SHOW_SOURCE)
        return None

    def _apply_config_plan(self, plan: ConfigPlan, prompt_on_replace: bool = True) -> Optional[int]:
        """
        NAME
            _apply_config_plan - Execute commands from a merge/import plan.
        """
        if not plan.ok:
            print(f"ERROR: {plan.message}")
            return 2
        if plan.root_payload is None and self._local_root_payload is None:
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return EXIT_CODE_ERROR if self._batch else None
        incoming_hash = self._profiles_hash(plan.root_payload)
        if not plan.replace and incoming_hash:
            if self._local_root_hash is None and self._local_group_count() > COUNT_ZERO:
                print(MESSAGE_ERR_PROFILE_MISSING_HASH)
                return EXIT_CODE_ERROR if self._batch else None
            if self._local_root_hash and incoming_hash != self._local_root_hash:
                print(
                    MESSAGE_ERR_PROFILE_HASH.format(
                        local=self._local_root_hash,
                        incoming=incoming_hash,
                    )
                )
                return EXIT_CODE_ERROR if self._batch else None
        if plan.replace:
            if prompt_on_replace and not self._batch and self._session.is_connected():
                if not self._confirm("Replace existing groups?"):
                    print("Import cancelled.")
                    return None
            if self._session.is_connected():
                if not self._clear_existing_groups():
                    return 2
        print(plan.message)
        if plan.config:
            self._local_config = plan.config
            self._local_config_path = plan.root_path
            self._local_loaded_at = time.time()
            if plan.root_payload is not None:
                self._local_root_payload = plan.root_payload
                self._local_root_path = plan.root_path
                self._local_root_hash = incoming_hash
                self._local_devices_locked = True
            self._profiles_dirty = False
            self._sync_group_profile()
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
        if not self._session.is_connected():
            return self._clear_local_groups()
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

    def _clear_local_groups(self) -> bool:
        """
        NAME
            _clear_local_groups - Clear local groups without touching the robot.
        """
        if not isinstance(self._local_config, dict):
            return True
        by_profile = self._local_config.get(KEY_BRIDGE_BY_PROFILE)
        if not isinstance(by_profile, dict):
            return True
        for entry in by_profile.values():
            if isinstance(entry, dict):
                entry[KEY_BRIDGE_GROUPS] = []
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
                return EXIT_CODE_ERROR if self._batch else None
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
        self._tracker.start("cli", None, seq, now=time.time(), retryable=False)
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
                if event.type in ("ack", "out"):
                    self._tracker.handle_event(event)
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
                "show": HELP_SHOW_TEXT,
                "configure terminal": "configure terminal\n  Enter config mode.",
                "connect": "connect\n  Open TCP connection and perform handshake.",
                "disconnect": "disconnect\n  Close TCP connection.",
                "echo": "echo on|off\n  Toggle echo for batch scripts (prints each command).",
                "group": "group <name>\n  Create/select a group (config mode).",
                "no group": "no group <name>\n  Delete group (config mode, prompts in interactive).",
                "profile": "profile <name>\n  Select active profile for groups/bindings.",
                "selected-device": "selected-device <device>\n  Set selected-device override.",
                "selected-mode": "selected-mode <on|off>\n  Enable/disable selected-device mode.",
                "merge config": (
                    "merge config <bringup_system.json>\n"
                    "  Load bridgeConfig.byProfile for the active profile without clearing existing."
                ),
                "import config": (
                    "import config <bringup_system.json>\n"
                    "  Replace bridgeConfig.byProfile for the active profile (prompts in interactive)."
                ),
                "export runtime-groups": (
                    "export runtime-groups <bridgeConfig.json>\n"
                    "  Write bridgeConfig.byProfile for the active profile."
                ),
                "save config": (
                    "save config <bridgeConfig.json>\n"
                    "  Write bridgeConfig.byProfile for the active profile."
                ),
                "save local-config": "save local-config <path>\n  Save local per-profile groups config.",
                "save profiles": (
                    "save profiles <path>\n"
                    "  Save profiles/diagram to bringup_system.json (bridgeConfig.byProfile unchanged)."
                ),
                "save unified-config": (
                    "save unified-config <path>\n"
                    "  Write a unified bringup_system.json with profiles + bridgeConfig.byProfile."
                ),
                "rename device": "rename device <old> <new>\n  Rename a device in local config.",
                "device set": (
                    "device <name> set <field> <value>\n"
                    "  Fields: vendor, role, notes, bus, tags, limits\n"
                    "  Use JSON for tags/limits (e.g., tags [\"arm\",\"motor\"])."
                ),
                "device": (
                    "device <name>\n"
                    "  Enter device mode to edit local device metadata."
                ),
                "device mode": (
                    "device mode: show, set <field> <value>, no <field>\n"
                    "  Fields: vendor, role, notes, bus, tags, limits"
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
                    "config mode: profile, group, no group, selected-device, selected-mode, "
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
            "Common: help, exit, end, quit, ping, echo\n"
            "Exec: show, connect, disconnect, configure terminal\n"
            "Config: profile, group, device, no group, selected-device, selected-mode, merge/import/export/save\n"
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
        if target == SHOW_TARGET_STATUS:
            seq = show_status(self._session, json_output=json_output)
        elif target == SHOW_TARGET_GROUPS:
            seq = show_groups(self._session, json_output=json_output)
        elif target == SHOW_TARGET_GROUP and len(tokens) >= 2:
            seq = show_group(self._session, tokens[1], json_output=json_output)
        elif target == SHOW_TARGET_DEVICES:
            seq = show_devices(self._session, json_output=json_output)
        elif target == SHOW_TARGET_DEVICE and len(tokens) >= 2:
            seq = show_device(self._session, tokens[1], json_output=json_output)
        elif target == SHOW_TARGET_BINDINGS:
            seq = show_bindings(self._session, json_output=json_output)
        elif target == SHOW_TARGET_SELECTED_DEVICE:
            seq = show_selected_device(self._session, json_output=json_output)
        elif target == SHOW_TARGET_RUNTIME:
            seq = show_runtime_state(self._session, json_output=json_output)
        else:
            print(MESSAGE_ERR_UNKNOWN_SHOW)
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
            print(MESSAGE_ERR_LOCAL_CONFIG_MISSING)
            return False
        if target == SHOW_TARGET_CONFIG_RAW:
            return self._show_local_config_raw(json_output)
        if target == SHOW_TARGET_PROFILES:
            return self._show_local_profiles(json_output)
        if target == SHOW_TARGET_PROFILE:
            return self._show_local_profile(json_output)
        if target == SHOW_TARGET_DEVICE_REGISTRY:
            name = tokens[1] if len(tokens) >= 2 else ""
            return self._show_local_registry_device(name, json_output)
        profile = self._active_profile_name()
        if not profile:
            print(MESSAGE_ERR_PROFILE_REQUIRED)
            return False
        devices = self._profile_device_entries(profile)
        ok, error, payload = local_show_data(
            target, tokens, self._local_config, profile, devices
        )
        if not ok:
            print(f"ERROR: {error}")
            return False
        groups = payload.get("groups", []) if isinstance(payload.get("groups"), list) else []
        selected = payload.get("selectedDevice") if isinstance(payload.get("selectedDevice"), dict) else {}
        selected_device = str(selected.get("device", "")).strip()
        selected_enabled = bool(selected.get("enabled", False))
        profile_name = str(payload.get(KEY_PROFILE, "")).strip()

        def _print_local(payload_text: str, payload_json: Optional[Dict[str, object]]) -> None:
            print(MESSAGE_SOURCE_LOCAL)
            if json_output and payload_json is not None:
                print(json.dumps(payload_json))
            else:
                print(payload_text.rstrip())

        if target == SHOW_TARGET_STATUS:
            text = (
                "Local status:\n"
                f"  profile={profile_name or '(none)'}\n"
                f"  groups={payload.get('groupCount', len(groups))}\n"
                f"  selectedDevice={selected_device or '(none)'} ({'on' if selected_enabled else 'off'})"
            )
            _print_local(text, payload)
            return True

        if target == SHOW_TARGET_GROUPS:
            lines = [f"Local groups (profile {profile_name or '(none)'}):"]
            for group in groups:
                if not isinstance(group, dict):
                    continue
                name = str(group.get("name", "")).strip()
                enabled = bool(group.get("enabled", True))
                lines.append(f"  {name} ({'enabled' if enabled else 'disabled'})")
            if len(lines) == 1:
                lines.append("  (none)")
            _print_local("\n".join(lines), payload)
            return True

        if target == SHOW_TARGET_GROUP and len(tokens) >= 2:
            name = tokens[1]
            match = payload.get("group") if isinstance(payload.get("group"), dict) else {}
            members = match.get("members", []) or []
            bindings = match.get("bindings", []) or []
            lines = [
                f"Local group {name} (profile {profile_name or '(none)'}):",
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
            _print_local("\n".join(lines), payload)
            return True

        if target == SHOW_TARGET_DEVICES:
            devices_raw = payload.get("devices")
            lines = ["Local devices:"]
            if isinstance(devices_raw, list) and devices_raw:
                for device in devices_raw:
                    if not isinstance(device, dict):
                        continue
                    name = str(device.get("name", "")).strip()
                    if not name:
                        continue
                    lines.append(f"  {name}")
            else:
                if isinstance(devices_raw, list) and devices_raw:
                    lines.extend(f"  {name}" for name in devices_raw if isinstance(name, str))
                else:
                    lines.append("  (none)")
            _print_local("\n".join(lines), payload)
            return True

        if target == SHOW_TARGET_DEVICE and len(tokens) >= 2:
            name = tokens[1]
            device_payload = payload.get("device")
            group_name = payload.get("group", "")
            enabled = payload.get("enabled", None)
            if isinstance(device_payload, dict):
                if group_name:
                    text = f"Local device {name}: group={group_name} enabled={enabled}".rstrip()
                else:
                    text = f"Local device {name}".rstrip()
                _print_local(text, payload)
                return True
            if isinstance(device_payload, str):
                text = f"Local device {name}: group={group_name} enabled={enabled}"
                _print_local(text, payload)
                return True
            print(MESSAGE_ERR_LOCAL_DEVICE_NOT_FOUND)
            return False

        if target == SHOW_TARGET_BINDINGS:
            lines = [f"Local bindings (profile {profile_name or '(none)'}):"]
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
            _print_local("\n".join(lines), payload)
            return True

        if target == SHOW_TARGET_SELECTED_DEVICE:
            text = (
                f"Local selected device (profile {profile_name or '(none)'}): "
                f"{selected_device or '(none)'} ({'on' if selected_enabled else 'off'})"
            )
            _print_local(text, payload)
            return True

        if target == SHOW_TARGET_RUNTIME:
            lines = [
                "Local runtime-state:",
                f"  profile={profile_name or '(none)'}",
                f"  selectedDevice={selected_device or '(none)'} ({'on' if selected_enabled else 'off'})",
                f"  groups={len(groups)}",
            ]
            devices = payload.get("devices") if isinstance(payload, dict) else None
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

    def _show_local_profiles(self, json_output: bool) -> bool:
        """
        NAME
            _show_local_profiles - Show available profile names.
        """
        payload = self._local_root_payload
        if not isinstance(payload, dict):
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return False
        profiles = payload.get(KEY_PROFILES)
        if not isinstance(profiles, dict):
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return False
        names = sorted([name for name in profiles.keys() if isinstance(name, str)])
        print(MESSAGE_SOURCE_LOCAL)
        if json_output:
            print(json.dumps({"profiles": names}))
            return True
        if not names:
            print(MESSAGE_LOCAL_PROFILES_EMPTY)
            return True
        print("Local profiles:")
        for name in names:
            print(f"  {name}")
        return True

    def _show_local_profile(self, json_output: bool) -> bool:
        """
        NAME
            _show_local_profile - Show the active/default profile names.
        """
        active = self._active_profile_name() or ""
        default_profile = self._default_profile_name() or ""
        payload = self._local_root_payload
        profiles = payload.get(KEY_PROFILES) if isinstance(payload, dict) else {}
        names = [name for name in profiles.keys() if isinstance(name, str)] if isinstance(profiles, dict) else []
        count = len(names)
        output = {
            KEY_ACTIVE: active,
            KEY_DEFAULT: default_profile,
            KEY_AVAILABLE: sorted(names),
        }
        print(MESSAGE_SOURCE_LOCAL)
        if json_output:
            print(json.dumps({KEY_PROFILE_INFO: output}))
            return True
        print(MESSAGE_LOCAL_PROFILE_HEADER)
        print(MESSAGE_LOCAL_PROFILE_ACTIVE.format(name=active or STRING_NONE))
        print(MESSAGE_LOCAL_PROFILE_DEFAULT.format(name=default_profile or STRING_NONE))
        print(MESSAGE_LOCAL_PROFILE_AVAILABLE.format(count=count))
        return True

    def _show_local_config_raw(self, json_output: bool) -> bool:
        """
        NAME
            _show_local_config_raw - Show raw local bridgeConfig content.
        """
        if not self._local_config:
            print(MESSAGE_ERR_LOCAL_CONFIG_MISSING)
            return False
        payload = self._ordered_bridge_config(self._local_config, include_devices=True)
        print(MESSAGE_SOURCE_LOCAL)
        if json_output:
            print(json.dumps(payload))
            return True
        print(MESSAGE_LOCAL_CONFIG_RAW)
        print(json.dumps(payload, indent=2))
        return True

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
                return EXIT_CODE_ERROR if self._batch else None
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
        profile = self._require_active_profile()
        if not profile:
            return False
        key = name.strip()
        if not key:
            print("ERROR: group name required.")
            return False
        groups = self._local_groups(profile, create=True)
        for group in groups:
            if isinstance(group, dict) and str(group.get("name", "")).strip().lower() == key.lower():
                return True
        groups.append({"name": key, "enabled": True, "members": [], "bindings": []})
        return True

    def _delete_local_group(self, name: str) -> bool:
        if not self._local_config:
            print("ERROR: Local config not loaded. Use merge/import config <bringup_system.json>.")
            return False
        profile = self._require_active_profile()
        if not profile:
            return False
        key = name.strip().lower()
        groups = self._local_groups(profile, create=True)
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
        entry = self._local_profile_entry(profile, create=True)
        entry[KEY_BRIDGE_GROUPS] = kept
        return True

    def _set_local_selected_device(self, device: str) -> bool:
        if not self._local_config:
            print("ERROR: Local config not loaded. Use merge/import config <bringup_system.json>.")
            return False
        profile = self._require_active_profile()
        if not profile:
            return False
        entry = self._local_profile_entry(profile, create=True)
        selected = entry.get(KEY_BRIDGE_SELECTED_DEVICE, {}) or {}
        enabled = bool(selected.get("enabled", False)) if isinstance(selected, dict) else False
        entry[KEY_BRIDGE_SELECTED_DEVICE] = {KEY_DEVICE: device.strip(), CMD_ENABLED: enabled}
        return True

    def _set_local_selected_mode(self, enabled: bool) -> bool:
        if not self._local_config:
            print("ERROR: Local config not loaded. Use merge/import config <bringup_system.json>.")
            return False
        profile = self._require_active_profile()
        if not profile:
            return False
        entry = self._local_profile_entry(profile, create=True)
        selected = entry.get(KEY_BRIDGE_SELECTED_DEVICE, {}) or {}
        device = str(selected.get(KEY_DEVICE, "")).strip() if isinstance(selected, dict) else ""
        entry[KEY_BRIDGE_SELECTED_DEVICE] = {KEY_DEVICE: device, CMD_ENABLED: bool(enabled)}
        return True

    def _find_local_group(self, name: str) -> Optional[Dict[str, object]]:
        profile = self._active_profile_name()
        if not profile or not self._local_config:
            return None
        groups = self._local_groups(profile, create=True)
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
        existing_names = set()
        by_profile = config.get(KEY_BRIDGE_BY_PROFILE) if isinstance(config, dict) else None
        if isinstance(by_profile, dict):
            for entry in by_profile.values():
                if not isinstance(entry, dict):
                    continue
                for group in entry.get(KEY_BRIDGE_GROUPS, []) or []:
                    if not isinstance(group, dict):
                        continue
                    for member in group.get("members", []) or []:
                        if isinstance(member, dict):
                            name = str(member.get(KEY_DEVICE, "")).strip()
                        else:
                            name = str(member).strip()
                        if name:
                            existing_names.add(name.lower())
                selected = entry.get(KEY_BRIDGE_SELECTED_DEVICE) if isinstance(entry, dict) else {}
                if isinstance(selected, dict):
                    sel_name = str(selected.get(KEY_DEVICE, "")).strip()
                    if sel_name:
                        existing_names.add(sel_name.lower())
        if new_name.lower() in existing_names:
            print(f"ERROR: Device name {new_name} already exists.")
            return False

        changed = False
        if isinstance(by_profile, dict):
            for entry in by_profile.values():
                if not isinstance(entry, dict):
                    continue
                for group in entry.get(KEY_BRIDGE_GROUPS, []) or []:
                    if not isinstance(group, dict):
                        continue
                    for member in group.get("members", []) or []:
                        if isinstance(member, dict):
                            name = str(member.get(KEY_DEVICE, "")).strip()
                            if name.lower() == old_name.lower():
                                member[KEY_DEVICE] = new_name
                                changed = True
                        elif isinstance(member, str):
                            if member.strip().lower() == old_name.lower():
                                index = group["members"].index(member)
                                group["members"][index] = new_name
                                changed = True
                selected = entry.get(KEY_BRIDGE_SELECTED_DEVICE)
                if isinstance(selected, dict):
                    sel_name = str(selected.get(KEY_DEVICE, "")).strip()
                    if sel_name.lower() == old_name.lower():
                        selected[KEY_DEVICE] = new_name
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
        by_profile = config.get(KEY_BRIDGE_BY_PROFILE)
        if not isinstance(by_profile, dict):
            return
        changed = False
        for entry in by_profile.values():
            if not isinstance(entry, dict):
                continue
            for group in entry.get(KEY_BRIDGE_GROUPS, []) or []:
                if not isinstance(group, dict):
                    continue
                for member in group.get("members", []) or []:
                    if isinstance(member, dict):
                        name = str(member.get(KEY_DEVICE, "")).strip()
                        if name.lower() == old.lower():
                            member[KEY_DEVICE] = new
                            changed = True
                    elif isinstance(member, str):
                        if member.strip().lower() == old.lower():
                            index = group["members"].index(member)
                            group["members"][index] = new
                            changed = True
            selected = entry.get(KEY_BRIDGE_SELECTED_DEVICE)
            if isinstance(selected, dict):
                sel_name = str(selected.get(KEY_DEVICE, "")).strip()
                if sel_name.lower() == old.lower():
                    selected[KEY_DEVICE] = new
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
            _set_local_device_meta - Update metadata for a local device.
        """
        if not self._local_config:
            print("ERROR: Local config not loaded. Use merge/import config <bringup_system.json>.")
            return False
        field_key = field.strip()
        if self._local_devices_locked:
            return self._set_profiles_device_meta(name, field_key, value_raw)
        if field_key not in (
            "vendor",
            "role",
            "notes",
            "bus",
            "tags",
            "limits",
        ):
            print(
                "ERROR: device set field must be vendor, role, notes, bus, tags, or limits."
            )
            return False
        value: object
        if field_key == "bus":
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
            _clear_local_device_meta - Clear metadata for a local device.
        """
        if not self._local_config:
            print("ERROR: Local config not loaded. Use merge/import config <bringup_system.json>.")
            return False
        field_key = field.strip()
        if self._local_devices_locked:
            return self._clear_profiles_device_meta(name, field_key)
        if field_key not in (
            "vendor",
            "role",
            "notes",
            "bus",
            "tags",
            "limits",
        ):
            print(
                "ERROR: device clear field must be vendor, role, notes, bus, tags, or limits."
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
            print(MESSAGE_ERR_LOCAL_CONFIG_MISSING)
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
                vendor = device.get("vendor")
                role = device.get("role")
                notes = device.get("notes")
                bus = device.get("bus")
                tags = device.get("tags")
                limits = device.get("limits")
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
        print(MESSAGE_ERR_LOCAL_DEVICE_NOT_FOUND)
        return None

    def _show_local_registry_device(self, name: str, json_output: bool) -> bool:
        """
        NAME
            _show_local_registry_device - Print device registry entry details.
        """
        if not isinstance(self._local_root_payload, dict):
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return False
        entry = self._find_profiles_device_entry(name)
        if entry is None:
            print(MESSAGE_ERR_REGISTRY_DEVICE_NOT_FOUND)
            return False
        label = str(entry.get(FIELD_LABEL, name)).strip() or name
        payload = {KEY_DEVICE: entry}
        print(MESSAGE_SOURCE_LOCAL)
        if json_output:
            print(json.dumps(payload))
            return True
        lines = [MESSAGE_LOCAL_REGISTRY_DEVICE.format(label=label)]
        mappings = self._load_can_mappings()
        manufacturers = mappings.get(KEY_MANUFACTURERS, {}) if mappings else {}
        device_types = mappings.get(KEY_DEVICE_TYPES, {}) if mappings else {}
        for key in sorted(entry.keys()):
            value = entry.get(key)
            if key == FIELD_MANUFACTURER and isinstance(value, int):
                name_value = manufacturers.get(str(value), "")
                if name_value:
                    lines.append(
                        MESSAGE_REGISTRY_FIELD_FMT_NAMED.format(
                            key=key, value=value, name=name_value
                        )
                    )
                    continue
            if key == FIELD_DEVICE_TYPE and isinstance(value, int):
                name_value = device_types.get(str(value), "")
                if name_value:
                    lines.append(
                        MESSAGE_REGISTRY_FIELD_FMT_NAMED.format(
                            key=key, value=value, name=name_value
                        )
                    )
                    continue
            lines.append(MESSAGE_REGISTRY_FIELD_FMT.format(key=key, value=value))
        if len(lines) == 1:
            lines.append(MESSAGE_LOCAL_REGISTRY_EMPTY)
        print("\n".join(lines))
        return True

    def _load_can_mappings(self) -> Dict[str, Dict[str, str]]:
        """
        NAME
            _load_can_mappings - Load CAN manufacturer/device type mappings.
        """
        if isinstance(self._can_mappings, dict):
            return self._can_mappings
        path = can_mappings_path()
        if not path.exists():
            self._can_mappings = {}
            return self._can_mappings
        try:
            payload = read_json(path)
        except Exception:
            print(MESSAGE_MAPPINGS_READ_FAIL.format(path=path))
            self._can_mappings = {}
            return self._can_mappings
        if not isinstance(payload, dict):
            self._can_mappings = {}
            return self._can_mappings
        manufacturers = payload.get(KEY_MANUFACTURERS)
        device_types = payload.get(KEY_DEVICE_TYPES)
        self._can_mappings = {
            KEY_MANUFACTURERS: manufacturers if isinstance(manufacturers, dict) else {},
            KEY_DEVICE_TYPES: device_types if isinstance(device_types, dict) else {},
        }
        return self._can_mappings

    def _save_profiles(self, path: str) -> bool:
        """
        NAME
            _save_profiles - Save updated bringup_system.json.
        """
        if not self._local_devices_locked or self._local_root_payload is None:
            print("ERROR: No profiles are loaded.")
            return False
        if not self._local_config:
            print(MESSAGE_ERR_LOCAL_CONFIG_MISSING)
            return False
        payload = dict(self._local_root_payload)
        payload["bridgeConfig"] = self._ordered_bridge_config(
            self._local_config, include_devices=False
        )
        payload["schema_version"] = PROFILE_SCHEMA_VERSION
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
            _ensure_profiles_device_entry - Reject implicit registry creation.
        """
        print("ERROR: Device not found in registry. Edit bringup_system.json in the topology tool.")
        return False

    def _set_profiles_device_meta(self, name: str, field: str, value_raw: str) -> bool:
        """
        NAME
            _set_profiles_device_meta - Update a device entry inside profiles.
        """
        entry = self._find_profiles_device_entry(name)
        if entry is None:
            return self._ensure_profiles_device_entry(name)
        if field in (
            FIELD_MANUFACTURER,
            FIELD_DEVICE_TYPE,
            FIELD_DEVICE_ID,
            FIELD_ID,
            FIELD_INTERFACE,
            FIELD_LABEL,
        ):
            print("ERROR: device identity fields are managed in bringup_system.json.")
            return False
        elif field == "vendor":
            entry["vendor"] = value_raw
        elif field == "role":
            entry[FIELD_TYPE] = value_raw
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
        if field in (
            FIELD_MANUFACTURER,
            FIELD_DEVICE_TYPE,
            FIELD_DEVICE_ID,
            FIELD_ID,
            FIELD_INTERFACE,
            FIELD_LABEL,
        ):
            print("ERROR: device identity fields are managed in bringup_system.json.")
            return False
        else:
            entry.pop(field, None)
        self._profiles_dirty = True
        self._refresh_devices_from_profiles()
        return True

    def _find_profiles_device_entry(self, name: str) -> Optional[Dict[str, object]]:
        payload = self._local_root_payload
        if not isinstance(payload, dict):
            return None
        devices = payload.get("devices")
        if not isinstance(devices, list):
            return None
        label = name.strip().lower()
        for entry in devices:
            if isinstance(entry, dict) and str(entry.get(FIELD_LABEL, "")).strip().lower() == label:
                return entry
        return None

    def _profiles_root_and_name(self) -> tuple[Optional[Dict[str, object]], Optional[str]]:
        payload = self._local_root_payload
        if not isinstance(payload, dict):
            return (None, None)
        profiles = payload.get(KEY_PROFILES)
        if not isinstance(profiles, dict) or not profiles:
            return (None, None)
        default_profile = payload.get(KEY_DEFAULT_PROFILE)
        if not isinstance(default_profile, str) or default_profile not in profiles:
            default_profile = next(iter(profiles.keys()))
        return (profiles, default_profile)

    def _refresh_devices_from_profiles(self) -> None:
        if not self._local_root_payload or not self._local_config:
            return
        self._sync_group_profile()
        profile = self._active_profile_name()
        if profile:
            self._local_profile_entry(profile, create=True)
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
        by_profile = config.get(KEY_BRIDGE_BY_PROFILE) if isinstance(config, dict) else None
        if isinstance(by_profile, dict):
            for profile_name in sorted(by_profile.keys()):
                entry = by_profile.get(profile_name)
                if not isinstance(entry, dict):
                    continue
                lines.append(f"profile {profile_name}")
                groups = entry.get(KEY_BRIDGE_GROUPS, []) or []
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
                            device = str(member.get(KEY_DEVICE, "")).strip()
                            enabled = bool(member.get("enabled", True))
                        else:
                            device = str(member).strip()
                            enabled = True
                        if not device:
                            continue
                        lines.append(f'add device "{device}"')
                        if not enabled:
                            lines.append(f'member "{device}" disable')
                    bindings = group.get(KEY_BRIDGE_BINDINGS, []) or []
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
                selected = entry.get(KEY_BRIDGE_SELECTED_DEVICE, {}) if isinstance(entry, dict) else {}
                if isinstance(selected, dict):
                    sel_name = str(selected.get(KEY_DEVICE, "")).strip()
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
                continue
            if cmd == "import" and len(tokens) >= 3 and tokens[1].lower() == "config":
                ok, message, config = validate_config_file(tokens[2])
                if not ok:
                    return message
                continue
            if cmd == "add" and len(tokens) >= 3 and tokens[1].lower() == "device":
                device = tokens[2].strip().lower()
                if known_devices and device not in known_devices:
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
        by_profile = config.get(KEY_BRIDGE_BY_PROFILE) if isinstance(config, dict) else None
        if not isinstance(by_profile, dict):
            return False
        for entry in by_profile.values():
            if not isinstance(entry, dict):
                continue
            for group in entry.get(KEY_BRIDGE_GROUPS, []) or []:
                if not isinstance(group, dict):
                    continue
                for member in group.get("members", []) or []:
                    if isinstance(member, dict):
                        dev_name = str(member.get(KEY_DEVICE, "")).strip()
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
            KEY_BRIDGE_SCHEMA_VERSION: config.get(KEY_BRIDGE_SCHEMA_VERSION, BRIDGE_CONFIG_SCHEMA_VERSION),
            KEY_BRIDGE_GENERATED_AT: config.get(KEY_BRIDGE_GENERATED_AT),
        }
        by_profile = config.get(KEY_BRIDGE_BY_PROFILE)
        ordered[KEY_BRIDGE_BY_PROFILE] = (
            dict(by_profile) if isinstance(by_profile, dict) else {}
        )
        return ordered

    def _local_device_exists(self, name: str) -> bool:
        """
        NAME
            _local_device_exists - Check if a device entry exists in local config.
        """
        if self._local_root_payload is not None:
            profile = self._active_profile_name()
            if profile:
                return name.strip().lower() in self._profile_device_labels(profile)
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

    def _ensure_local_config(self) -> None:
        """
        NAME
            _ensure_local_config - Initialize an empty local bridgeConfig if missing.
        """
        if self._local_config is None:
            self._local_config = {
                KEY_BRIDGE_SCHEMA_VERSION: BRIDGE_CONFIG_SCHEMA_VERSION,
                KEY_BRIDGE_GENERATED_AT: None,
                KEY_BRIDGE_BY_PROFILE: {},
            }
            self._local_devices_locked = False
            self._profiles_dirty = False
        if self._groups_profile is None and self._local_root_payload is None:
            self._groups_profile = DEFAULT_PROFILE_LOCAL
            self._local_profile_entry(self._groups_profile, create=True)

    def _build_unified_payload(self) -> Optional[Dict[str, object]]:
        """
        NAME
            _build_unified_payload - Build a bringup_system.json payload from local state.
        """
        if not self._local_config:
            print("ERROR: Local config not loaded. Use merge/import config <bringup_system.json>.")
            return None
        payload: Dict[str, object] = deepcopy(self._local_root_payload) if self._local_root_payload else {}
        if "profiles" not in payload or not self._local_root_payload:
            print("ERROR: No profiles loaded. Merge a bringup_system.json before saving unified config.")
            return None
        if "diagram" not in payload:
            payload["diagram"] = {"profiles": {}}
        payload.setdefault("default_profile", "robot")
        payload["schema_version"] = PROFILE_SCHEMA_VERSION
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
