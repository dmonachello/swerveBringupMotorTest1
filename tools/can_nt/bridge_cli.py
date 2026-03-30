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
import sys
import re
from copy import deepcopy
from pathlib import Path
import copy
from dataclasses import dataclass
from typing import Dict, List, Optional

from tools.can_nt.bridge_cmd_tracker import CommandTracker
from tools.can_nt.bridge_cli_parser import BridgeCliParser, CliParseError
from tools.can_nt.bridge_cli_ast import BridgeCliAstExecutor, AST_EXEC_SPEC
from tools.can_nt.bridge_cli_constants import CLI_PARSER_CONST
from tools.can_nt.bridge_cli_constants_gen import SPEC as PARSER_SPEC
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
from tools.config.schema_store import ConfigSchemaStore, LOCATION_BINDINGS, LOCATION_MAPPINGS
from tools.common.json_io import read_json, write_json
from tools.common.profile_io import compute_profiles_hash
from tools.common.paths import (
    repo_root,
    logs_dir,
    tests_deploy_path,
    profiles_canonical_path,
    can_mappings_path,
    bindings_deploy_path,
    test_templates_dir,
)
from tools.common.profile_constants import (
    BRIDGE_CONFIG_SCHEMA_VERSION,
    KEY_BRIDGE_BY_PROFILE,
    KEY_BRIDGE_CONFIG,
    KEY_BRIDGE_GENERATED_AT,
    KEY_BRIDGE_GROUPS,
    KEY_BRIDGE_SCHEMA_VERSION,
    KEY_BRIDGE_SELECTED_DEVICE,
    KEY_DATA_HASH,
    KEY_DATA_VERSION,
    KEY_DIO,
    KEY_DEFAULT_PROFILE,
    KEY_DEVICE_TYPE,
    KEY_DEVICES,
    KEY_ID,
    KEY_INTERFACE,
    KEY_INVERT,
    KEY_LABEL,
    KEY_LIMITS,
    KEY_MANUFACTURER,
    KEY_MODEL,
    KEY_NOTES,
    KEY_PWM,
    KEY_ANALOG,
    KEY_PROFILE,
    KEY_PROFILES,
    KEY_PROFILE_DEVICES,
    KEY_SCHEMA_VERSION,
    PROFILE_SCHEMA_VERSION,
    INTERFACE_ANALOG,
    INTERFACE_CAN,
    INTERFACE_DIO,
    INTERFACE_INTERNAL,
    INTERFACE_PWM,
    KEY_ATTACHMENTS,
    KEY_TERMINATOR,
    KEY_TYPE,
    KEY_VENDOR,
    KEY_ROLE,
    KEY_TAGS,
)
from tools.common.tests_io import load_tests_payload, write_tests_payload
from tools.common.test_authoring import (
    TestAuthoringModel,
    TestBindingButton,
    TestBindingJoystick,
    DeviceActionModel,
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

# Optional line editing for Cisco-style '?' prefill.
MESSAGE_WARN_PROMPT_TOOLKIT = (
    "WARNING: prompt_toolkit not installed; '?' help cannot prefill the line buffer."
)
MESSAGE_WARN_HISTORY_DISABLED = (
    "WARNING: command history disabled (prompt_toolkit not available)."
)
PROMPT_TOOLKIT_AVAILABLE = False

try:
    from prompt_toolkit import prompt as prompt_toolkit_prompt
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory
    PROMPT_TOOLKIT_AVAILABLE = True
except Exception:
    prompt_toolkit_prompt = None
    PromptSession = None
    FileHistory = None

# Parser selection (comment out one of the two lines below).
CLI_PARSER_KIND = CLI_PARSER_CONST["ebnf"]

MODE_CONFIG = "config"
MODE_TEST = "test"

TESTS_FILENAME = "bringup_tests.json"
DEFAULT_TEST_SET = "default"
EMPTY_STRING = ""
TEST_LABEL_UNKNOWN = "unknown"
COUNT_ZERO = 0
COUNT_ONE = 1
COUNT_TWO = 2
COUNT_THREE = 3
COUNT_FOUR = 4
COUNT_FIVE = 5
COUNT_SIX = 6
COUNT_SEVEN = 7
COUNT_EIGHT = 8
COUNT_NINE = 9
EXIT_CODE_ERROR = 2

CMD_SHOW = "show"
CMD_WRITE = "write"
CMD_TEST = "test"
CMD_TESTS = "tests"
CMD_CREATE = "create"
CMD_DELETE = "delete"
CMD_SET = "set"
CMD_CLEAR = "clear"
CMD_MESSAGES = "messages"
CMD_MESSAGE_LEVEL = "message-level"
CMD_TYPE = "type"
CMD_DEVICE = "device"
CMD_REGISTRY = "registry"
CMD_GROUP = "group"
CMD_CONFIG = "config"
CMD_LOCAL_RAW = "local-raw"
CMD_DIRTY = "dirty"
CMD_PROFILES = "profiles"
CMD_PROFILE = "profile"
CMD_CONFIGURE = "configure"
CMD_TERMINAL = "terminal"
CMD_ACTION = "action"
CMD_COLOR = "color"
CMD_PATTERN = "pattern"
CMD_BRIGHTNESS = "brightness"
CMD_DURATION = "duration"
CMD_ADD = "add"
CMD_NO = "no"
CMD_RENAME = "rename"
CMD_VALIDATE = "validate"
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
CMD_BINDINGS = "bindings"
CMD_CONTROLLER = "controller"
CMD_BINDING = "binding"
CMD_BIND = PARSER_SPEC.cmd_bind
CMD_AXIS = "axis"
CMD_CAN_MAPPINGS = "can-mappings"
CMD_MANUFACTURER = "manufacturer"
CMD_DEVICE_TYPE_NAME = "device-type"
CMD_LOAD = "load"
CMD_SAVE = "save"
CMD_MERGE = "merge"
CMD_TEMPLATES = "templates"
CMD_TEMPLATE = "template"
CMD_INFO = "info"
QUESTION_MARK = "?"
SUGGESTION_SEPARATOR = " | "
MESSAGE_NEXT_ARGS_PREFIX = "Next args: "
MESSAGE_NEXT_ARGS_NONE = "Next args: (none)"
PLACEHOLDER_NAME = "<name>"
PLACEHOLDER_PATH = "<path>"
FLAG_JSON = "--json"
FLAG_PRETTY = "--pretty"
JSON_PRETTY_INDENT = 2
MESSAGE_EMPTY_PROMPT = ""
HISTORY_FILENAME = "bridge_cli_history.txt"

KEY_DEVICE = "device"
KEY_NAME = "name"
KEY_GROUPS = "groups"
KEY_BY_PROFILE = "byProfile"
KEY_SELECTED_DEVICE = "selectedDevice"
KEY_MANUFACTURERS = "manufacturers"
KEY_DEVICE_TYPES = "device_types"
KEY_TEST_SETS = "test_sets"
KEY_TESTS = "tests"
KEY_TEST_SET = "test_set"
KEY_TEST = "test"
KEY_DIRTY = "dirty"
DIRTY_BINDINGS = "bindings"
DIRTY_CAN_MAPPINGS = "can-mappings"
KEY_CONTROLLERS = "controllers"
KEY_BINDINGS = "bindings"
KEY_AXES = "axes"
KEY_COMMAND = "command"
KEY_CONTROLLER = "controller"
KEY_INPUT = "input"
KEY_MODE = "mode"
KEY_PORT = "port"
KEY_DEADBAND = "deadband"

SHOW_TARGET_CONFIG = "config"
SHOW_TARGET_RUNTIME = "runtime-state"
SHOW_TARGET_CONFIG_RAW = "config-raw"
SHOW_CONFIG_LOCAL_RAW = "local-raw"
SHOW_TARGET_PROFILES = "profiles"
SHOW_TARGET_PROFILE = "profile"
SHOW_TARGET_CONFIG_DIRTY = "config-dirty"
SHOW_CONFIG_DIRTY = "dirty"

KEY_PROFILE_INFO = "profile"
KEY_DIAGRAM = "diagram"
KEY_DIAGRAM_PROFILES = "profiles"
KEY_ACTIVE = "active"
KEY_DEFAULT = "default"
KEY_AVAILABLE = "available"
STRING_NONE = "(none)"
SEP_NEWLINE = "\n"

PROMPT_EXEC = "bridge> "
PROMPT_EXEC_WITH_PROFILE_FMT = "bridge{suffix}> "
PROMPT_CONFIG_PREFIX = "bridge(config"
PROMPT_GROUP_SEGMENT = "-group-"
PROMPT_DEVICE_PREFIX = "bridge(config-device-"
PROMPT_TEST_PREFIX = "bridge(config-test-"
PROMPT_SUFFIX = ")# "
PROMPT_PROFILE_PREFIX = "-profile-"
SHOW_TARGET_STATUS = "status"
SHOW_TARGET_GROUPS = "groups"
SHOW_TARGET_GROUP = "group"
SHOW_TARGET_DEVICES = "devices"
SHOW_TARGET_DEVICE = "device"
SHOW_TARGET_DEVICE_REGISTRY = "device-registry"
SHOW_TARGET_BINDINGS = "bindings"
SHOW_TARGET_SELECTED_DEVICE = "selected-device"
SHOW_TARGET_MESSAGE_LEVEL = "message-level"

MESSAGE_ERR_UNKNOWN_SHOW = "ERROR: Unknown show command."
MESSAGE_ERR_UNKNOWN_SHOW_SOURCE = "ERROR: Unknown show source."
MESSAGE_ERR_SHOW_REQUIRES_TARGET = "ERROR: show requires a target."
MESSAGE_ERR_PRETTY_REQUIRES_JSON = "ERROR: --pretty requires --json."
MESSAGE_ERR_LOCAL_CONFIG_MISSING = "ERROR: Local config not loaded. Use merge/import config <bringup_system.json>."
MESSAGE_ERR_LOCAL_DEVICE_NOT_FOUND = "ERROR: Local device not found."
MESSAGE_OK_CONFIG_VALID = "OK: Config is valid."
MESSAGE_ERR_CONFIG_VALIDATE = "ERROR: {message}"
MESSAGE_STORE_ISSUE = "{location}: {message}"
MESSAGE_ERR_REGISTRY_NOT_LOADED = "ERROR: Profiles not loaded. Use merge/import config <bringup_system.json>."
MESSAGE_LOCAL_PROFILES_EMPTY = "Local profiles: (none)"
MESSAGE_LOCAL_PROFILES_HEADER = "Local profiles:"
MESSAGE_LOCAL_PROFILE_HEADER = "Local profile:"
MESSAGE_LOCAL_PROFILE_NAME = "  name={name}"
MESSAGE_LOCAL_PROFILE_ACTIVE = "  active={name}"
MESSAGE_LOCAL_PROFILE_DEFAULT = "  default={name}"
MESSAGE_LOCAL_PROFILE_AVAILABLE = "  available={count}"
MESSAGE_LOCAL_PROFILE_DEVICES_HEADER = "  devices={count}"
MESSAGE_LOCAL_PROFILE_DEVICE_FMT = "    {label}"
MESSAGE_ERR_PROFILE_NOT_FOUND = "ERROR: Profile not found."
MESSAGE_DIRTY_HEADER = "Local dirty state:"
MESSAGE_DIRTY_ENTRY = "  {name}={value}"
MESSAGE_DIRTY_NONE = "  (clean)"
MESSAGE_DIRTY_PROMPT = "Unsaved changes in: {items}. Exit anyway?"
MESSAGE_ERR_DEVICE_LABEL_REQUIRED = "ERROR: device name required."
MESSAGE_ERR_DEVICE_PROFILE_REQUIRED = "ERROR: Profile not selected. Use 'profile <name>'."
MESSAGE_ERR_DEVICE_INTERFACE_INVALID = "ERROR: interface must be CAN, DIO, PWM, ANALOG, or INTERNAL."
MESSAGE_ERR_DEVICE_FIELD_UNKNOWN = "ERROR: device set field not supported."
MESSAGE_ERR_DEVICE_FIELD_INT = "ERROR: device set value must be an integer."
MESSAGE_ERR_DEVICE_FIELD_BOOL = "ERROR: device set value must be true/false."
MESSAGE_ERR_DEVICE_FIELD_LIST = "ERROR: device set value must be a JSON list."
MESSAGE_ERR_DEVICE_FIELD_DICT = "ERROR: device set value must be a JSON object."
MESSAGE_WARN_DEVICE_INCOMPLETE = "WARNING: Device {label} missing required fields: {fields}"
MESSAGE_ERR_REGISTRY_DEVICE_NOT_FOUND = "ERROR: Device not found in registry."
MESSAGE_SOURCE_LOCAL = "SOURCE: local"
MESSAGE_LOCAL_CONFIG_RAW = "Local bridgeConfig (raw):"
MESSAGE_LOCAL_REGISTRY_DEVICE = "Local registry device {label}:"
MESSAGE_LOCAL_REGISTRY_EMPTY = "  (no fields)"
MESSAGE_REGISTRY_FIELD_FMT = "  {key}={value}"
MESSAGE_REGISTRY_FIELD_FMT_NAMED = "  {key}={value} ({name})"
MESSAGE_MAPPINGS_READ_FAIL = "WARNING: Failed to read CAN mappings: {path}"
MESSAGE_ERR_BINDINGS_SUBCOMMAND = (
    "ERROR: bindings <show|controller|binding|axis|load|save|validate>"
)
MESSAGE_ERR_BINDINGS_SHOW = "ERROR: bindings show [controllers|bindings|axes] [--json] [--pretty]"
MESSAGE_ERR_BINDINGS_CONTROLLER_ADD = "ERROR: bindings controller add <name> <type> <port>"
MESSAGE_ERR_BINDINGS_CONTROLLER_SET = "ERROR: bindings controller set <name> <field> <value>"
MESSAGE_ERR_BINDINGS_CONTROLLER_RENAME = "ERROR: bindings controller rename <old> <new>"
MESSAGE_ERR_BINDINGS_CONTROLLER_DELETE = "ERROR: bindings no controller <name>"
MESSAGE_ERR_BINDINGS_CONTROLLER_PORT = "ERROR: controller port must be an integer."
MESSAGE_ERR_BINDINGS_CONTROLLER_EXISTS = "ERROR: controller already exists."
MESSAGE_ERR_BINDINGS_CONTROLLER_NOT_FOUND = "ERROR: controller not found."
MESSAGE_ERR_BINDINGS_CONTROLLER_IN_USE = "ERROR: controller is referenced by bindings or axes."
MESSAGE_ERR_BINDINGS_BINDING_ADD = (
    "ERROR: bindings binding add <command> <controller> <input> <id> <mode>"
)
MESSAGE_ERR_BINDINGS_BINDING_SET = "ERROR: bindings binding set <index> <field> <value>"
MESSAGE_ERR_BINDINGS_BINDING_DELETE = "ERROR: bindings binding delete <index>"
MESSAGE_ERR_BINDINGS_BINDING_INDEX = "ERROR: binding index out of range."
MESSAGE_ERR_BINDINGS_AXIS_ADD = (
    "ERROR: bindings axis add <command> <controller> <id> invert <on|off> deadband <value>"
)
MESSAGE_ERR_BINDINGS_AXIS_SET = "ERROR: bindings axis set <index> <field> <value>"
MESSAGE_ERR_BINDINGS_AXIS_DELETE = "ERROR: bindings axis delete <index>"
MESSAGE_ERR_BINDINGS_AXIS_INDEX = "ERROR: axis index out of range."
MESSAGE_ERR_BINDINGS_FIELD_UNKNOWN = "ERROR: bindings field not supported."
MESSAGE_ERR_BINDINGS_CONTROLLER_REQUIRED = "ERROR: controller not found: {name}"
MESSAGE_ERR_BINDINGS_INVERT = "ERROR: invert must be on/off."
MESSAGE_ERR_BINDINGS_DEADBAND = "ERROR: deadband must be 0.0 to 1.0."
MESSAGE_ERR_BINDINGS_LOAD = "ERROR: Failed to read bindings: {path}"
MESSAGE_ERR_BINDINGS_WRITE = "ERROR: Failed to write bindings: {path}: {error}"
MESSAGE_ERR_BINDINGS_VALIDATE = "ERROR: bindings validation failed: {message}"
MESSAGE_INFO_BINDINGS_LOADED = "Loaded bindings: {path}"
MESSAGE_INFO_BINDINGS_SAVED = "Wrote bindings to {path}."
MESSAGE_BINDINGS_HEADER = "Local bindings config:"
MESSAGE_BINDINGS_CONTROLLERS_HEADER = "  controllers:"
MESSAGE_BINDINGS_BINDINGS_HEADER = "  bindings:"
MESSAGE_BINDINGS_AXES_HEADER = "  axes:"
MESSAGE_BINDINGS_NONE = "  (none)"
MESSAGE_BINDINGS_CONTROLLER_FMT = "    {name} type={type} port={port}"
MESSAGE_BINDINGS_BINDING_FMT = (
    "    [{index}] command={command} controller={controller} input={input} id={id} mode={mode}"
)
MESSAGE_BINDINGS_AXIS_FMT = (
    "    [{index}] command={command} controller={controller} id={id} invert={invert} deadband={deadband}"
)
MESSAGE_ERR_MAPPINGS_SUBCOMMAND = (
    "ERROR: can-mappings <show|manufacturer|device-type|load|save|validate>"
)
MESSAGE_ERR_MAPPINGS_SHOW = "ERROR: can-mappings show [manufacturers|device-types] [--json] [--pretty]"
MESSAGE_ERR_MAPPINGS_SET = "ERROR: {target} set <id> <name>"
MESSAGE_ERR_MAPPINGS_DELETE = "ERROR: {target} delete <id>"
MESSAGE_ERR_MAPPINGS_ID = "ERROR: id must be an integer."
MESSAGE_ERR_MAPPINGS_LOAD = "ERROR: Failed to read CAN mappings: {path}"
MESSAGE_ERR_MAPPINGS_WRITE = "ERROR: Failed to write CAN mappings: {path}: {error}"
MESSAGE_ERR_MAPPINGS_VALIDATE = "ERROR: can-mappings validation failed: {message}"
MESSAGE_INFO_MAPPINGS_LOADED = "Loaded CAN mappings: {path}"
MESSAGE_INFO_MAPPINGS_SAVED = "Wrote CAN mappings to {path}."
MESSAGE_MAPPINGS_HEADER = "Local CAN mappings:"
MESSAGE_MAPPINGS_MANUFACTURERS_HEADER = "  manufacturers:"
MESSAGE_MAPPINGS_DEVICE_TYPES_HEADER = "  device-types:"
MESSAGE_MAPPINGS_ENTRY_FMT = "    {id}={name}"
MESSAGE_MAPPINGS_NONE = "  (none)"
MESSAGE_ERR_TESTS_SUBCOMMAND = "ERROR: tests <templates|load|merge|save|clear>"
MESSAGE_ERR_TESTS_LOAD = "ERROR: tests load <path> | tests load template <name>"
MESSAGE_ERR_TESTS_SAVE = "ERROR: tests save requires a loaded tests file."
MESSAGE_ERR_TESTS_TEMPLATE_NOT_FOUND = "ERROR: test template not found: {name}"
MESSAGE_TESTS_TEMPLATES_HEADER = "Test templates:"
MESSAGE_TESTS_TEMPLATES_NONE = "  (none)"
MESSAGE_TESTS_TEMPLATE_ENTRY = "  {name}"
MESSAGE_TESTS_LOADED = "Loaded tests: {path}"
MESSAGE_TESTS_CLEARED = "Tests cleared."
MESSAGE_MESSAGE_LEVEL = "Message level: {level}"
MESSAGE_MESSAGE_LEVEL_UPDATED = "Message level set to {level}."
MESSAGE_MESSAGE_LEVEL_ERROR = "ERROR: messages <beginner|medium|expert>"
HELP_SHOW_TEXT = (
    "show <status|groups|group <name>|devices|device <name>|device registry <name>|bindings|"
    "selected-device|runtime-state|config|config local-raw|config dirty|profiles|profile|tests|test <name>|message-level> "
    "[--json] [--pretty] [robot|local|both]\n"
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
FIELD_MODEL = "model"
FIELD_DIO = "dio"
FIELD_INVERT = "invert"
FIELD_PWM = "pwm"
FIELD_ANALOG = "analog"
FIELD_ATTACHMENTS = "attachments"
FIELD_TERMINATOR = "terminator"
FIELD_VENDOR = "vendor"
FIELD_ROLE = "role"
FIELD_NOTES = "notes"
FIELD_TAGS = "tags"
FIELD_LIMITS = "limits"

DEVICE_FIELD_INT = "int"
DEVICE_FIELD_BOOL = "bool"
DEVICE_FIELD_LIST = "list"
DEVICE_FIELD_STR = "str"
DEVICE_FIELD_DICT = "dict"

DEVICE_INTERFACE_ALLOWED = {
    INTERFACE_CAN,
    INTERFACE_DIO,
    INTERFACE_PWM,
    INTERFACE_ANALOG,
    INTERFACE_INTERNAL,
}

DEVICE_FIELDS_PROFILE = {
    FIELD_INTERFACE,
    FIELD_MANUFACTURER,
    FIELD_DEVICE_TYPE,
    FIELD_ID,
    FIELD_MODEL,
    FIELD_TYPE,
    FIELD_DIO,
    FIELD_INVERT,
    FIELD_PWM,
    FIELD_ANALOG,
    FIELD_ATTACHMENTS,
    FIELD_TERMINATOR,
    FIELD_VENDOR,
    FIELD_ROLE,
    FIELD_NOTES,
    FIELD_TAGS,
    FIELD_LIMITS,
}

DEVICE_FIELD_TYPES = {
    FIELD_INTERFACE: DEVICE_FIELD_STR,
    FIELD_MANUFACTURER: DEVICE_FIELD_INT,
    FIELD_DEVICE_TYPE: DEVICE_FIELD_INT,
    FIELD_ID: DEVICE_FIELD_INT,
    FIELD_MODEL: DEVICE_FIELD_STR,
    FIELD_TYPE: DEVICE_FIELD_STR,
    FIELD_DIO: DEVICE_FIELD_INT,
    FIELD_INVERT: DEVICE_FIELD_BOOL,
    FIELD_PWM: DEVICE_FIELD_INT,
    FIELD_ANALOG: DEVICE_FIELD_INT,
    FIELD_ATTACHMENTS: DEVICE_FIELD_LIST,
    FIELD_TERMINATOR: DEVICE_FIELD_BOOL,
    FIELD_VENDOR: DEVICE_FIELD_STR,
    FIELD_ROLE: DEVICE_FIELD_STR,
    FIELD_NOTES: DEVICE_FIELD_STR,
    FIELD_TAGS: DEVICE_FIELD_LIST,
    FIELD_LIMITS: DEVICE_FIELD_DICT,
}

BOOL_TRUE_VALUES = {"true", "on", "1", "yes"}
BOOL_FALSE_VALUES = {"false", "off", "0", "no"}

DEVICE_REQUIRED_CAN = (FIELD_INTERFACE, FIELD_MANUFACTURER, FIELD_DEVICE_TYPE, FIELD_ID)
DEVICE_REQUIRED_DIO = (FIELD_INTERFACE, FIELD_DIO, FIELD_INVERT)
DEVICE_REQUIRED_PWM = (FIELD_INTERFACE, FIELD_PWM)
DEVICE_REQUIRED_ANALOG = (FIELD_INTERFACE, FIELD_ANALOG)
DEVICE_REQUIRED_INTERNAL = (FIELD_INTERFACE,)

TEST_TYPE_JOYSTICK = "joystick"
TEST_TYPE_BUTTON = "button"
TEST_TYPE_COMPOSITE = "composite"
TEST_TYPE_DEADBAND_SWEEP = "deadbandSweep"
TEST_TYPE_DEVICE_ACTION = "deviceAction"
ACTION_TOGGLE_LED = "toggle_led"
ACTION_SET_COLOR = "set_color"
ACTION_ALLOWED = {ACTION_TOGGLE_LED, ACTION_SET_COLOR}
PATTERN_SOLID = "solid"
PATTERN_ALLOWED = {PATTERN_SOLID}
COLOR_PREFIX = "#"
COLOR_HEX_LEN = 7
COLOR_HEX_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")

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
BRIGHTNESS_MIN = 0.0
BRIGHTNESS_MAX = 1.0
DURATION_MIN_SEC = 0.0
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

BINDINGS_EMPTY_PAYLOAD = {
    KEY_CONTROLLERS: [],
    KEY_BINDINGS: [],
    KEY_AXES: [],
}
BINDINGS_SHOW_CONTROLLERS = "controllers"
BINDINGS_SHOW_BINDINGS = "bindings"
BINDINGS_SHOW_AXES = "axes"
BINDINGS_SHOW_TARGETS = {BINDINGS_SHOW_CONTROLLERS, BINDINGS_SHOW_BINDINGS, BINDINGS_SHOW_AXES}
BINDINGS_CONTROLLER_FIELDS = {FIELD_TYPE, KEY_PORT, KEY_NAME}
BINDINGS_BINDING_FIELDS = {KEY_COMMAND, KEY_CONTROLLER, KEY_INPUT, KEY_ID, KEY_MODE}
BINDINGS_AXIS_FIELDS = {KEY_COMMAND, KEY_CONTROLLER, KEY_ID, KEY_INVERT, KEY_DEADBAND}

MAPPINGS_SHOW_MANUFACTURERS = "manufacturers"
MAPPINGS_SHOW_DEVICE_TYPES = "device-types"
MAPPINGS_SHOW_TARGETS = {MAPPINGS_SHOW_MANUFACTURERS, MAPPINGS_SHOW_DEVICE_TYPES}

TESTS_TEMPLATES_SUFFIX = ".json"

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
MESSAGE_ERROR_TYPE = (
    "ERROR: type must be joystick, button, composite, deadbandSweep, or deviceAction."
)
MESSAGE_ERROR_DEVICE_DUP = "WARNING: Device already present."
MESSAGE_ERROR_INPUT_SOURCE_TYPE = "ERROR: inputSource only valid for joystick/button/composite tests."
MESSAGE_ERROR_INPUT_SOURCE_VALUE = "ERROR: inputSource requires <controller>.<inputId>."
MESSAGE_ERROR_DEADBAND_TYPE = "ERROR: deadband only valid for joystick tests."
MESSAGE_ERROR_DEADBAND_NUMBER = "ERROR: deadband requires a number."
MESSAGE_ERROR_DEADBAND_RANGE = "ERROR: deadband must be 0.0 to 1.0."
MESSAGE_ERROR_DUTY_TYPE = "ERROR: duty only valid for button/composite tests."
MESSAGE_ERROR_DUTY_NUMBER = "ERROR: duty requires a number."
MESSAGE_ERROR_DUTY_RANGE = "ERROR: duty must be -1.0 to 1.0."
MESSAGE_ERROR_ACTION_TYPE = "ERROR: action only valid for deviceAction tests."
MESSAGE_ERROR_ACTION_REQUIRED = "ERROR: action requires toggle_led or set_color."
MESSAGE_ERROR_COLOR_TYPE = "ERROR: color only valid for deviceAction tests."
MESSAGE_ERROR_COLOR_REQUIRED = "ERROR: color requires #RRGGBB."
MESSAGE_ERROR_PATTERN_TYPE = "ERROR: pattern only valid for deviceAction tests."
MESSAGE_ERROR_PATTERN_VALUE = "ERROR: pattern must be solid."
MESSAGE_ERROR_BRIGHTNESS_TYPE = "ERROR: brightness only valid for deviceAction tests."
MESSAGE_ERROR_BRIGHTNESS_NUMBER = "ERROR: brightness requires a number."
MESSAGE_ERROR_BRIGHTNESS_RANGE = "ERROR: brightness must be 0.0 to 1.0."
MESSAGE_ERROR_DURATION_TYPE = "ERROR: duration only valid for deviceAction tests."
MESSAGE_ERROR_DURATION_NUMBER = "ERROR: duration requires a number."
MESSAGE_ERROR_DURATION_RANGE = "ERROR: duration must be >= 0."
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
MESSAGE_ERR_PROFILE_CREATE_NAME = "ERROR: Profile name is required."
MESSAGE_ERR_PROFILE_EXISTS = "ERROR: Profile already exists: {name}."
MESSAGE_PROFILE_CREATED = "Created profile: {name}."
MESSAGE_ERROR_SHOW_TESTS = "ERROR: show tests | show test <name>"
MESSAGE_ERROR_WRITE_TESTS = "ERROR: write tests <path>"
MESSAGE_SELECTED_TEST_SET = "Selected test set: {name}"
MESSAGE_CANCELLED = "Cancelled."
MESSAGE_DELETED_TEST = "Deleted test: {name}"
MESSAGE_WROTE_TESTS = "Wrote tests to {path}."
MESSAGE_TEST_SETS_HEADER = "Test sets:"
MESSAGE_TEST_SETS_ENTRY = "  {name} ({count} tests)"
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
MESSAGE_TEST_ACTION = "  action: {action}"
MESSAGE_TEST_COLOR = "  color: {color}"
MESSAGE_TEST_PATTERN = "  pattern: {pattern}"
MESSAGE_TEST_BRIGHTNESS = "  brightness: {brightness}"
MESSAGE_TEST_DURATION = "  durationSec: {duration}"

MESSAGE_LEVEL_BEGINNER = "beginner"
MESSAGE_LEVEL_MEDIUM = "medium"
MESSAGE_LEVEL_EXPERT = "expert"
MESSAGE_LEVELS = {MESSAGE_LEVEL_BEGINNER, MESSAGE_LEVEL_MEDIUM, MESSAGE_LEVEL_EXPERT}

CLI_SETTINGS_FILENAME = ".bridge_cli_settings.json"


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
        echo_enabled: bool = False,
        message_level: Optional[str] = None,
    ) -> None:
        self._session = session
        self._batch = batch
        self._conflict_policy = conflict_policy
        self._echo_enabled = echo_enabled
        self._message_level = MESSAGE_LEVEL_BEGINNER
        self._message_level_from_flag = False
        self._tips_suppressed: set[str] = set()
        self._tests_device_catalog: Dict[str, object] = {}
        self._tests_duplicate_labels: set[str] = set()
        self._parser_kind = CLI_PARSER_KIND
        self._parser = BridgeCliParser(strict=bool(CLI_PARSER_CONST["strict_default"]))
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
        self._groups_dirty: bool = False
        self._tracker = CommandTracker(timeout_sec=2.0, max_retries=0)
        self._store = ConfigSchemaStore()
        self._tests_model: Optional[TestAuthoringModel] = None
        self._tests_path: Optional[Path] = None
        self._tests_dirty: bool = False
        self._tests_active_set: str = ""
        self._tests_profile: Optional[str] = None
        self._load_message_level(message_level)
        self._groups_profile: Optional[str] = None
        self._pending_prompt_text: Optional[str] = None
        self._use_prompt_toolkit: bool = PROMPT_TOOLKIT_AVAILABLE
        self._warned_prompt_toolkit: bool = False
        self._warned_history: bool = False
        self._prompt_session = self._build_prompt_session()
        self._can_mappings: Optional[Dict[str, Dict[str, str]]] = None
        self._can_mappings_path: Optional[Path] = None
        self._can_mappings_dirty: bool = False
        self._bindings_payload: Optional[Dict[str, object]] = None
        self._bindings_path: Optional[Path] = None
        self._bindings_dirty: bool = False

    def run_interactive(self) -> int:
        """
        NAME
            run_interactive - Enter the interactive prompt loop.
        """
        self._auto_merge_default_profiles()
        while True:
            try:
                prompt = self._prompt()
                if self._use_prompt_toolkit and self._prompt_session is not None:
                    if self._pending_prompt_text is not None:
                        line = self._prompt_session.prompt(prompt, default=self._pending_prompt_text)
                        self._pending_prompt_text = None
                    else:
                        line = self._prompt_session.prompt(prompt)
                else:
                    if self._pending_prompt_text is not None:
                        if not self._warned_prompt_toolkit:
                            print(MESSAGE_WARN_PROMPT_TOOLKIT)
                            self._warned_prompt_toolkit = True
                        sys.stdout.write(self._prompt() + self._pending_prompt_text)
                        sys.stdout.flush()
                        self._pending_prompt_text = None
                        line = input(MESSAGE_EMPTY_PROMPT)
                    else:
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
                self._warn("WARNING: Command failed; staying in CLI.")
                continue

    def _build_prompt_session(self) -> Optional[PromptSession]:
        """
        NAME
            _build_prompt_session - Build a prompt_toolkit session with history.
        """
        if not self._use_prompt_toolkit or PromptSession is None or FileHistory is None:
            if not self._warned_history:
                print(MESSAGE_WARN_HISTORY_DISABLED)
                self._warned_history = True
            return None
        history_path = logs_dir() / HISTORY_FILENAME
        history_path.parent.mkdir(parents=True, exist_ok=True)
        return PromptSession(history=FileHistory(str(history_path)))

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
            suffix = self._profile_prompt_suffix(use_active=True)
            if suffix:
                return PROMPT_EXEC_WITH_PROFILE_FMT.format(suffix=suffix)
            return PROMPT_EXEC
        if mode.name == MODE_CONFIG:
            suffix = self._profile_prompt_suffix()
            return f"{PROMPT_CONFIG_PREFIX}{suffix}{PROMPT_SUFFIX}"
        if mode.name == "group":
            suffix = self._profile_prompt_suffix()
            return f"{PROMPT_CONFIG_PREFIX}{suffix}{PROMPT_GROUP_SEGMENT}{mode.group}{PROMPT_SUFFIX}"
        if mode.name == "device":
            return f"{PROMPT_DEVICE_PREFIX}{mode.device}{PROMPT_SUFFIX}"
        if mode.name == MODE_TEST:
            label = mode.test or TEST_LABEL_UNKNOWN
            return f"{PROMPT_TEST_PREFIX}{label}{PROMPT_SUFFIX}"
        return PROMPT_EXEC

    def _profile_prompt_suffix(self, use_active: bool = False) -> str:
        """
        NAME
            _profile_prompt_suffix - Render prompt suffix for active profile.
        """
        profile = self._groups_profile or ""
        if use_active and not profile:
            profile = self._active_profile_name() or ""
        if profile:
            return f"{PROMPT_PROFILE_PREFIX}{profile}"
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
            self._warn(MESSAGE_AUTO_MERGE_FAIL.format(path=path))
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

    def _refresh_tests_profile(self, profile_name: Optional[str]) -> None:
        """
        NAME
            _refresh_tests_profile - Sync test profile and device catalog.

        DESCRIPTION
            Prefer local profiles payload when present so unsaved edits
            are visible to test validation.
        """

        if not profile_name:
            self._tests_profile = None
            self._tests_device_catalog = {}
            self._tests_duplicate_labels = set()
            return
        self._tests_profile = profile_name
        payload = self._local_root_payload if isinstance(self._local_root_payload, dict) else None
        catalog, duplicates = self._catalog_from_payload(payload, profile_name)
        if catalog:
            self._tests_device_catalog = catalog
            self._tests_duplicate_labels = duplicates
            return
        try:
            catalog, duplicates = load_profile_devices(profile_name)
            self._tests_device_catalog = catalog
            self._tests_duplicate_labels = duplicates
        except Exception:
            self._tests_device_catalog = {}
            self._tests_duplicate_labels = set()

    def _catalog_from_payload(
        self, payload: Optional[Dict[str, object]], profile_name: str
    ) -> tuple[Dict[str, Dict[str, object]], set[str]]:
        """
        NAME
            _catalog_from_payload - Build device catalog from profiles payload.

        DESCRIPTION
            Returns catalog + duplicate labels using an in-memory payload.
        """

        catalog: Dict[str, Dict[str, object]] = {}
        duplicates: set[str] = set()
        if not payload or not profile_name:
            return catalog, duplicates
        profiles = payload.get(KEY_PROFILES)
        devices = payload.get(KEY_DEVICES)
        if not isinstance(profiles, dict) or not isinstance(devices, list):
            return catalog, duplicates
        profile = profiles.get(profile_name)
        if not isinstance(profile, dict):
            return catalog, duplicates
        labels = profile.get(KEY_PROFILE_DEVICES)
        if not isinstance(labels, list):
            return catalog, duplicates
        registry: Dict[str, Dict[str, object]] = {}
        for entry in devices:
            if not isinstance(entry, dict):
                continue
            label = str(entry.get(KEY_LABEL, EMPTY_STRING)).strip()
            if not label:
                continue
            registry[label.lower()] = entry
        seen: set[str] = set()
        for label in labels:
            if not isinstance(label, str):
                continue
            clean = label.strip()
            if not clean:
                continue
            key = clean.lower()
            if key in seen:
                duplicates.add(clean)
                continue
            seen.add(key)
            entry = registry.get(key)
            if entry is None:
                continue
            catalog[clean] = dict(entry)
        return catalog, duplicates

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
        self._refresh_tests_profile(key)
        return True

    def _ensure_local_profiles_payload(self) -> bool:
        """
        NAME
            _ensure_local_profiles_payload - Ensure a profiles payload exists.
        """
        if self._local_root_payload is None:
            self._local_root_payload = {
                KEY_SCHEMA_VERSION: PROFILE_SCHEMA_VERSION,
                KEY_DATA_VERSION: timestamp_version(),
                KEY_DATA_HASH: EMPTY_STRING,
                KEY_DEFAULT_PROFILE: EMPTY_STRING,
                KEY_PROFILES: {},
                KEY_DEVICES: [],
                KEY_DIAGRAM: {KEY_DIAGRAM_PROFILES: {}},
            }
            self._local_root_hash = None
            self._local_devices_locked = True
            self._profiles_dirty = True
        payload = self._local_root_payload
        if not isinstance(payload, dict):
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return False
        profiles = payload.get(KEY_PROFILES)
        if profiles is None:
            payload[KEY_PROFILES] = {}
        elif not isinstance(profiles, dict):
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return False
        devices = payload.get(KEY_DEVICES)
        if devices is None:
            payload[KEY_DEVICES] = []
        elif not isinstance(devices, list):
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return False
        diagram = payload.get(KEY_DIAGRAM)
        if diagram is None:
            payload[KEY_DIAGRAM] = {KEY_DIAGRAM_PROFILES: {}}
        elif not isinstance(diagram, dict):
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return False
        return True

    def _create_profile(self, name: str) -> bool:
        """
        NAME
            _create_profile - Create a new empty profile and select it.
        """
        key = name.strip()
        if not key:
            print(MESSAGE_ERR_PROFILE_CREATE_NAME)
            return False
        self._ensure_local_config()
        if not self._ensure_local_profiles_payload():
            return False
        payload = self._local_root_payload
        if not isinstance(payload, dict):
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return False
        profiles = payload.get(KEY_PROFILES)
        if not isinstance(profiles, dict):
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return False
        if key in profiles:
            print(MESSAGE_ERR_PROFILE_EXISTS.format(name=key))
            return False
        profiles[key] = {KEY_PROFILE_DEVICES: []}
        default_profile = payload.get(KEY_DEFAULT_PROFILE)
        if not isinstance(default_profile, str) or not default_profile.strip():
            payload[KEY_DEFAULT_PROFILE] = key
        diagram = payload.get(KEY_DIAGRAM)
        if isinstance(diagram, dict):
            diag_profiles = diagram.get(KEY_DIAGRAM_PROFILES)
            if not isinstance(diag_profiles, dict):
                diag_profiles = {}
                diagram[KEY_DIAGRAM_PROFILES] = diag_profiles
            diag_profiles.setdefault(key, {})
        self._profiles_dirty = True
        self._local_devices_locked = True
        self._groups_profile = key
        self._local_profile_entry(key, create=True)
        self._refresh_tests_profile(key)
        self._sync_store_from_local()
        print(MESSAGE_PROFILE_CREATED.format(name=key))
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
        if self._handle_question(line):
            return None
        try:
            parsed = self._parser.parse(line, mode=self._modes[-1].name)
            tokens = parsed.tokens
            ast = parsed.ast
        except (CliParseError, ValueError) as exc:
            try:
                self._split_command(line)
            except CliParseError as split_exc:
                print(f"ERROR: {split_exc}")
                return None
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
                dirty = {name: flag for name, flag in self._dirty_state().items() if flag}
                if dirty:
                    items = ", ".join(sorted(dirty.keys()))
                    if self._batch:
                        print(MESSAGE_DIRTY_PROMPT.format(items=items))
                        return 0
                    if not self._confirm(MESSAGE_DIRTY_PROMPT.format(items=items)):
                        return None
                return 0
            self._warn_unsaved_if_needed()
            self._pop_mode()
            return None
        if cmd == "end":
            self._warn_unsaved_if_needed()
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
        if cmd == CMD_MESSAGES:
            if len(tokens) < 2:
                print(MESSAGE_MESSAGE_LEVEL_ERROR)
                return 2 if self._batch else None
            if not self._set_message_level(tokens[1], persist=True):
                print(MESSAGE_MESSAGE_LEVEL_ERROR)
                return 2 if self._batch else None
            print(MESSAGE_MESSAGE_LEVEL_UPDATED.format(level=self._message_level))
            return None

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

    def _handle_question(self, line: str) -> bool:
        """
        NAME
            _handle_question - Provide Cisco-style help for trailing '?'.

        DESCRIPTION
            When a command line ends with '?', display possible next arguments
            instead of executing the command. This is handled before parsing
            so the EBNF parser does not see the '?' token.
        """
        if QUESTION_MARK not in line:
            return False
        tokens = self._split_command(line)
        if not tokens:
            return False
        tokens = self._normalize_question_tokens(tokens)
        if not tokens or tokens[-1] != QUESTION_MARK:
            return False
        base_tokens = tokens[:-1]
        suggestions = self._suggest_next_args(base_tokens)
        self._print_next_args(suggestions)
        self._queue_question_line(base_tokens)
        return True

    def _normalize_question_tokens(self, tokens: List[str]) -> List[str]:
        """
        NAME
            _normalize_question_tokens - Split a trailing '?' token when attached.
        """
        last = tokens[-1]
        if not last.endswith(QUESTION_MARK):
            return tokens
        if last == QUESTION_MARK:
            return tokens
        base = last[:-len(QUESTION_MARK)]
        normalized = tokens[:-1]
        if base:
            normalized.append(base)
        normalized.append(QUESTION_MARK)
        return normalized

    def _print_next_args(self, suggestions: List[str]) -> None:
        """
        NAME
            _print_next_args - Print suggestion list for '?' help.
        """
        if not suggestions:
            print(MESSAGE_NEXT_ARGS_NONE)
            return
        joined = SUGGESTION_SEPARATOR.join(suggestions)
        print(MESSAGE_NEXT_ARGS_PREFIX + joined)

    def _queue_question_line(self, tokens: List[str]) -> None:
        """
        NAME
            _queue_question_line - Queue the original command line after '?' help.
        """
        if not tokens:
            return
        line = PARSER_SPEC.space_str.join(tokens) + PARSER_SPEC.space_str
        self._pending_prompt_text = line

    def _suggest_next_args(self, tokens: List[str]) -> List[str]:
        """
        NAME
            _suggest_next_args - Compute next-argument suggestions.
        """
        mode = self._modes[-1].name
        if not tokens:
            return self._mode_root_suggestions(mode)
        cmd = tokens[COUNT_ZERO].lower()
        if cmd == CMD_SHOW:
            return self._suggest_show_args(tokens[COUNT_ONE:])
        if cmd == CMD_CONFIGURE:
            return self._suggest_configure_args(tokens[COUNT_ONE:])
        if mode == MODE_CONFIG and cmd == CMD_BINDINGS:
            return self._suggest_bindings_args(tokens[COUNT_ONE:])
        if mode == MODE_CONFIG and cmd == CMD_CAN_MAPPINGS:
            return self._suggest_mappings_args(tokens[COUNT_ONE:])
        if mode == MODE_CONFIG and cmd == CMD_PROFILE:
            if len(tokens) == COUNT_ONE:
                return [CMD_CREATE, PLACEHOLDER_NAME]
            if len(tokens) == COUNT_TWO and tokens[COUNT_ONE].lower() == CMD_CREATE:
                return [PLACEHOLDER_NAME]
            return []
        if cmd == CMD_TESTS:
            return self._suggest_tests_args(tokens[COUNT_ONE:])
        if mode == MODE_CONFIG and cmd == CMD_TEST:
            return self._suggest_test_config_args(tokens[COUNT_ONE:])
        return []

    def _mode_root_suggestions(self, mode: str) -> List[str]:
        """
        NAME
            _mode_root_suggestions - Suggest top-level commands for a mode.
        """
        if mode == MODE_CONFIG:
            return [
                CMD_SHOW,
                CMD_GROUP,
                CMD_NO,
                CMD_PROFILE,
                PARSER_SPEC.cmd_selected_device,
                PARSER_SPEC.cmd_selected_mode,
                PARSER_SPEC.cmd_merge,
                PARSER_SPEC.cmd_import,
                PARSER_SPEC.cmd_export,
                CMD_SAVE,
                CMD_RENAME,
                CMD_DEVICE,
                CMD_BINDINGS,
                CMD_CAN_MAPPINGS,
                CMD_TESTS,
                CMD_TEST,
                CMD_WRITE,
                CMD_VALIDATE,
            ]
        if mode == MODE_TEST:
            return [
                CMD_SHOW,
                CMD_TYPE,
                CMD_DEVICE,
                CMD_INPUT_SOURCE,
                CMD_DEADBAND,
                CMD_DUTY,
                CMD_TERMINATION,
                CMD_ACTION,
                CMD_COLOR,
                CMD_PATTERN,
                CMD_BRIGHTNESS,
                CMD_DURATION,
            ]
        if mode == PARSER_SPEC.msg_mode_name_group:
            return [CMD_SHOW, CMD_ADD, CMD_NO, CMD_BIND, PARSER_SPEC.cmd_enable, PARSER_SPEC.cmd_disable, PARSER_SPEC.cmd_run]
        if mode == PARSER_SPEC.msg_mode_name_device:
            return [CMD_SHOW, CMD_SET, CMD_NO]
        return [
            CMD_SHOW,
            PARSER_SPEC.cmd_connect,
            PARSER_SPEC.cmd_disconnect,
            PARSER_SPEC.cmd_configure,
        ]

    def _suggest_show_args(self, tokens: List[str]) -> List[str]:
        """
        NAME
            _suggest_show_args - Suggest next args for show commands.
        """
        if not tokens:
            return self._show_target_suggestions()
        target = tokens[COUNT_ZERO].lower()
        if target == CMD_GROUP:
            if len(tokens) == COUNT_ONE:
                return [PLACEHOLDER_NAME]
            if len(tokens) == COUNT_TWO:
                return self._show_flag_suggestions()
            return []
        if target == CMD_DEVICE:
            if len(tokens) == COUNT_ONE:
                return [PLACEHOLDER_NAME, CMD_REGISTRY]
            if len(tokens) == COUNT_TWO and tokens[COUNT_ONE].lower() == CMD_REGISTRY:
                return [PLACEHOLDER_NAME]
            if len(tokens) == COUNT_TWO:
                return self._show_flag_suggestions()
            if len(tokens) == COUNT_THREE:
                return self._show_flag_suggestions()
            return []
        if target == CMD_CONFIG:
            if len(tokens) == COUNT_ONE:
                return [CMD_LOCAL_RAW, CMD_DIRTY] + self._show_flag_suggestions()
            if len(tokens) == COUNT_TWO and tokens[COUNT_ONE].lower() in (CMD_LOCAL_RAW, CMD_DIRTY):
                return self._show_flag_suggestions()
            return self._show_flag_suggestions()
        if target == CMD_PROFILE:
            if len(tokens) == COUNT_ONE:
                return [PLACEHOLDER_NAME] + self._show_flag_suggestions()
            if len(tokens) == COUNT_TWO:
                return self._show_flag_suggestions()
            return []
        if target == PARSER_SPEC.show_target_test:
            if len(tokens) == COUNT_ONE:
                return [PLACEHOLDER_NAME]
            if len(tokens) == COUNT_TWO:
                return self._show_flag_suggestions()
            return []
        if target in PARSER_SPEC.show_targets:
            if len(tokens) == COUNT_ONE:
                return self._show_flag_suggestions()
            return []
        return []

    def _show_target_suggestions(self) -> List[str]:
        """
        NAME
            _show_target_suggestions - Suggest show targets.
        """
        return [
            PARSER_SPEC.show_target_status,
            PARSER_SPEC.show_target_groups,
            CMD_GROUP + PARSER_SPEC.space_str + PLACEHOLDER_NAME,
            PARSER_SPEC.show_target_devices,
            CMD_DEVICE + PARSER_SPEC.space_str + PLACEHOLDER_NAME,
            CMD_DEVICE + PARSER_SPEC.space_str + CMD_REGISTRY + PARSER_SPEC.space_str + PLACEHOLDER_NAME,
            PARSER_SPEC.show_target_bindings,
            PARSER_SPEC.show_target_selected_device,
            PARSER_SPEC.show_target_runtime_state,
            CMD_CONFIG,
            CMD_CONFIG + PARSER_SPEC.space_str + CMD_LOCAL_RAW,
            CMD_CONFIG + PARSER_SPEC.space_str + CMD_DIRTY,
            CMD_PROFILES,
            CMD_PROFILE,
            CMD_PROFILE + PARSER_SPEC.space_str + PLACEHOLDER_NAME,
            PARSER_SPEC.show_target_tests,
            PARSER_SPEC.show_target_test + PARSER_SPEC.space_str + PLACEHOLDER_NAME,
            PARSER_SPEC.show_target_message_level,
        ]

    def _show_flag_suggestions(self) -> List[str]:
        """
        NAME
            _show_flag_suggestions - Suggest show flags.
        """
        return [
            PARSER_SPEC.show_source_robot,
            PARSER_SPEC.show_source_local,
            PARSER_SPEC.show_source_both,
            FLAG_JSON,
            FLAG_PRETTY,
        ]

    def _suggest_bindings_args(self, tokens: List[str]) -> List[str]:
        """
        NAME
            _suggest_bindings_args - Suggest bindings subcommands.
        """
        if not tokens:
            return [CMD_SHOW, CMD_CONTROLLER, CMD_BINDING, CMD_AXIS, CMD_LOAD, CMD_SAVE, CMD_VALIDATE]
        sub = tokens[COUNT_ZERO].lower()
        if sub == CMD_SHOW and len(tokens) == COUNT_ONE:
            return [BINDINGS_SHOW_CONTROLLERS, BINDINGS_SHOW_BINDINGS, BINDINGS_SHOW_AXES, FLAG_JSON]
        if sub == CMD_CONTROLLER and len(tokens) == COUNT_ONE:
            return [CMD_ADD, CMD_SET, CMD_RENAME, CMD_NO]
        if sub == CMD_BINDING and len(tokens) == COUNT_ONE:
            return [CMD_ADD, CMD_SET, CMD_DELETE]
        if sub == CMD_AXIS and len(tokens) == COUNT_ONE:
            return [CMD_ADD, CMD_SET, CMD_DELETE]
        if sub in (CMD_LOAD, CMD_SAVE, CMD_VALIDATE) and len(tokens) == COUNT_ONE:
            return [PLACEHOLDER_PATH]
        return []

    def _suggest_configure_args(self, tokens: List[str]) -> List[str]:
        """
        NAME
            _suggest_configure_args - Suggest configure subcommands.
        """
        if not tokens:
            return [CMD_TERMINAL]
        return []

    def _suggest_mappings_args(self, tokens: List[str]) -> List[str]:
        """
        NAME
            _suggest_mappings_args - Suggest can-mappings subcommands.
        """
        if not tokens:
            return [CMD_SHOW, CMD_MANUFACTURER, CMD_DEVICE_TYPE_NAME, CMD_LOAD, CMD_SAVE, CMD_VALIDATE]
        sub = tokens[COUNT_ZERO].lower()
        if sub == CMD_SHOW and len(tokens) == COUNT_ONE:
            return [CMD_MANUFACTURER, CMD_DEVICE_TYPE_NAME, FLAG_JSON]
        if sub in (CMD_LOAD, CMD_SAVE, CMD_VALIDATE) and len(tokens) == COUNT_ONE:
            return [PLACEHOLDER_PATH]
        return []

    def _suggest_tests_args(self, tokens: List[str]) -> List[str]:
        """
        NAME
            _suggest_tests_args - Suggest tests subcommands.
        """
        if not tokens:
            return [CMD_TEMPLATES, CMD_LOAD, CMD_MERGE, CMD_SAVE, CMD_CLEAR]
        sub = tokens[COUNT_ZERO].lower()
        if sub in (CMD_LOAD, CMD_MERGE) and len(tokens) == COUNT_ONE:
            return [PLACEHOLDER_PATH, CMD_TEMPLATE]
        if sub == CMD_TEMPLATE and len(tokens) == COUNT_ONE:
            return [PLACEHOLDER_NAME]
        return []

    def _suggest_test_config_args(self, tokens: List[str]) -> List[str]:
        """
        NAME
            _suggest_test_config_args - Suggest config-mode test subcommands.
        """
        if not tokens:
            return [CMD_SET, CMD_CREATE, CMD_DELETE, PLACEHOLDER_NAME]
        sub = tokens[COUNT_ZERO].lower()
        if sub in (CMD_SET, CMD_CREATE, CMD_DELETE) and len(tokens) == COUNT_ONE:
            return [PLACEHOLDER_NAME]
        return []

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
        if tokens[0].lower() == CMD_TESTS:
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
        if tokens[0].lower() == CMD_TESTS:
            return self._tests_command(tokens)
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
        self._sync_store_tests()
        if not self._tests_profile:
            self._refresh_tests_profile(self._active_profile_name() or get_default_profile())
        else:
            self._refresh_tests_profile(self._tests_profile)
        default_set = self._tests_model.default_test_set if self._tests_model else EMPTY_STRING
        self._tests_active_set = default_set or DEFAULT_TEST_SET

    def _tests_command(self, tokens: List[str]) -> Optional[int]:
        """
        NAME
            _tests_command - Handle tests subcommands (templates/load/save).
        """

        self._ensure_tests_loaded()
        if len(tokens) < COUNT_TWO:
            print(MESSAGE_ERR_TESTS_SUBCOMMAND)
            return None
        sub = tokens[COUNT_ONE].lower()
        if sub == CMD_TEMPLATES:
            return self._show_test_templates()
        if sub == CMD_LOAD:
            if len(tokens) >= COUNT_FOUR and tokens[COUNT_TWO].lower() == CMD_TEMPLATE:
                name = tokens[COUNT_THREE]
                path = self._resolve_template_path(name)
                if path is None:
                    print(MESSAGE_ERR_TESTS_TEMPLATE_NOT_FOUND.format(name=name))
                    return None
                if not self._load_tests_from_path(path):
                    return None
                print(MESSAGE_TESTS_LOADED.format(path=path))
                return None
            if len(tokens) >= COUNT_THREE:
                path = Path(tokens[COUNT_TWO])
                if not self._load_tests_from_path(path):
                    return None
                print(MESSAGE_TESTS_LOADED.format(path=path))
                return None
            print(MESSAGE_ERR_TESTS_LOAD)
            return None
        if sub == CMD_MERGE:
            if len(tokens) >= COUNT_THREE:
                path = Path(tokens[COUNT_TWO])
                if not self._merge_tests_from_path(path):
                    return None
                print(MESSAGE_TESTS_LOADED.format(path=path))
                return None
            print(MESSAGE_ERR_TESTS_LOAD)
            return None
        if sub == CMD_SAVE:
            if not self._tests_path:
                print(MESSAGE_ERR_TESTS_SAVE)
                return None
            return self._write_tests_command([CMD_WRITE, CMD_TESTS, str(self._tests_path)])
        if sub == CMD_CLEAR:
            model = TestAuthoringModel()
            model.test_sets[DEFAULT_TEST_SET] = TestSetModel(name=DEFAULT_TEST_SET, tests=[])
            self._tests_model = model
            self._tests_active_set = DEFAULT_TEST_SET
            self._tests_dirty = True
            self._sync_store_tests()
            if not self._tests_profile:
                self._refresh_tests_profile(self._active_profile_name() or get_default_profile())
            else:
                self._refresh_tests_profile(self._tests_profile)
            print(MESSAGE_TESTS_CLEARED)
            return None
        print(MESSAGE_ERR_TESTS_SUBCOMMAND)
        return None

    def _show_test_templates(self) -> Optional[int]:
        """
        NAME
            _show_test_templates - List available test templates.
        """

        templates = self._list_test_templates()
        print(MESSAGE_TESTS_TEMPLATES_HEADER)
        if not templates:
            print(MESSAGE_TESTS_TEMPLATES_NONE)
            return None
        for name in templates:
            print(MESSAGE_TESTS_TEMPLATE_ENTRY.format(name=name))
        return None

    def _list_test_templates(self) -> List[str]:
        """
        NAME
            _list_test_templates - Return template filenames.
        """

        template_dir = test_templates_dir()
        if not template_dir.exists():
            return []
        return sorted([path.name for path in template_dir.glob(f"*{TESTS_TEMPLATES_SUFFIX}")])

    def _resolve_template_path(self, name: str) -> Optional[Path]:
        """
        NAME
            _resolve_template_path - Resolve a template name to a path.
        """

        template_dir = test_templates_dir()
        if not template_dir.exists():
            return None
        filename = name
        if not filename.endswith(TESTS_TEMPLATES_SUFFIX):
            filename = f"{filename}{TESTS_TEMPLATES_SUFFIX}"
        path = template_dir / filename
        if not path.exists():
            return None
        return path

    def _load_tests_from_path(self, path: Path) -> bool:
        """
        NAME
            _load_tests_from_path - Load tests JSON from a path.
        """

        try:
            payload = load_tests_payload(path)
        except Exception:
            return False
        model = model_from_payload(payload or {})
        self._tests_model = model
        self._tests_path = path
        self._tests_dirty = False
        if not self._tests_profile:
            self._refresh_tests_profile(self._active_profile_name() or get_default_profile())
        else:
            self._refresh_tests_profile(self._tests_profile)
        default_set = model.default_test_set if model else EMPTY_STRING
        self._tests_active_set = default_set or DEFAULT_TEST_SET
        self._sync_store_tests()
        return True

    def _merge_tests_from_path(self, path: Path) -> bool:
        """
        NAME
            _merge_tests_from_path - Merge tests JSON into current model.
        """
        try:
            payload = load_tests_payload(path)
        except Exception as exc:
            print(f"ERROR: Failed to read tests: {exc}")
            return False
        incoming = model_from_payload(payload or {})
        dest = self._tests_model or TestAuthoringModel()
        if not dest.default_test_set and incoming.default_test_set:
            dest.default_test_set = incoming.default_test_set
        for set_name, src_set in incoming.test_sets.items():
            if set_name not in dest.test_sets:
                dest.test_sets[set_name] = TestSetModel(
                    name=set_name,
                    tests=[copy.deepcopy(t) for t in src_set.tests],
                )
                continue
            dst_set = dest.test_sets[set_name]
            for src_test in src_set.tests:
                existing_idx = None
                for idx, test in enumerate(dst_set.tests):
                    if test.name == src_test.name:
                        existing_idx = idx
                        break
                if existing_idx is not None:
                    dst_set.tests[existing_idx] = copy.deepcopy(src_test)
                    self._warn(
                        f"WARNING: Test '{src_test.name}' overwritten in set '{set_name}'."
                    )
                else:
                    dst_set.tests.append(copy.deepcopy(src_test))
        self._tests_model = dest
        if not self._tests_active_set:
            self._tests_active_set = dest.default_test_set or DEFAULT_TEST_SET
        if self._tests_active_set not in dest.test_sets:
            self._tests_active_set = dest.default_test_set or DEFAULT_TEST_SET
        self._tests_dirty = True
        self._sync_store_tests()
        if not self._tests_profile:
            self._refresh_tests_profile(self._active_profile_name() or get_default_profile())
        else:
            self._refresh_tests_profile(self._tests_profile)
        return True

    def _ensure_bindings_loaded(self) -> bool:
        """
        NAME
            _ensure_bindings_loaded - Load bringup_bindings.json if needed.
        """

        if isinstance(self._bindings_payload, dict):
            return True
        path = bindings_deploy_path()
        return self._load_bindings_from_path(path, announce=False)

    def _load_bindings_from_path(self, path: Path, announce: bool = True) -> bool:
        """
        NAME
            _load_bindings_from_path - Load bindings config from a path.
        """

        payload = deepcopy(BINDINGS_EMPTY_PAYLOAD)
        if path.exists():
            try:
                loaded = read_json(path)
            except Exception:
                print(MESSAGE_ERR_BINDINGS_LOAD.format(path=path))
                return False
            if isinstance(loaded, dict):
                payload.update(loaded)
        payload[KEY_CONTROLLERS] = (
            payload.get(KEY_CONTROLLERS) if isinstance(payload.get(KEY_CONTROLLERS), list) else []
        )
        payload[KEY_BINDINGS] = (
            payload.get(KEY_BINDINGS) if isinstance(payload.get(KEY_BINDINGS), list) else []
        )
        payload[KEY_AXES] = payload.get(KEY_AXES) if isinstance(payload.get(KEY_AXES), list) else []
        self._bindings_payload = payload
        self._bindings_path = path
        self._bindings_dirty = False
        self._sync_store_bindings()
        if announce:
            print(MESSAGE_INFO_BINDINGS_LOADED.format(path=path))
        return True

    def _save_bindings_to_path(self, path: Path) -> Optional[int]:
        """
        NAME
            _save_bindings_to_path - Save bindings config to a path.
        """

        if not isinstance(self._bindings_payload, dict):
            print(MESSAGE_ERR_BINDINGS_LOAD.format(path=path))
            return EXIT_CODE_ERROR if self._batch else None
        payload = {
            KEY_CONTROLLERS: self._bindings_payload.get(KEY_CONTROLLERS, []),
            KEY_BINDINGS: self._bindings_payload.get(KEY_BINDINGS, []),
            KEY_AXES: self._bindings_payload.get(KEY_AXES, []),
        }
        try:
            write_json(path, payload, indent=COUNT_TWO, trailing_newline=True)
        except Exception as exc:
            print(MESSAGE_ERR_BINDINGS_WRITE.format(path=path, error=exc))
            return EXIT_CODE_ERROR if self._batch else None
        self._bindings_dirty = False
        self._bindings_path = path
        self._sync_store_bindings()
        print(MESSAGE_INFO_BINDINGS_SAVED.format(path=path))
        return None

    def _bindings_show(self, tokens: List[str]) -> Optional[int]:
        """
        NAME
            _bindings_show - Show bindings config content.
        """

        if not isinstance(self._bindings_payload, dict):
            print(MESSAGE_ERR_BINDINGS_LOAD.format(path=EMPTY_STRING))
            return None
        _source, cleaned, json_output, pretty, ok = self._parse_show_flags(tokens)
        if not ok:
            return 2 if self._batch else None
        target = cleaned[COUNT_ZERO].lower() if cleaned else EMPTY_STRING
        controllers = self._bindings_payload.get(KEY_CONTROLLERS, [])
        bindings = self._bindings_payload.get(KEY_BINDINGS, [])
        axes = self._bindings_payload.get(KEY_AXES, [])
        print(MESSAGE_SOURCE_LOCAL)
        if json_output:
            if target == BINDINGS_SHOW_CONTROLLERS:
                print(self._dump_json({KEY_CONTROLLERS: controllers}, pretty))
                return None
            if target == BINDINGS_SHOW_BINDINGS:
                print(self._dump_json({KEY_BINDINGS: bindings}, pretty))
                return None
            if target == BINDINGS_SHOW_AXES:
                print(self._dump_json({KEY_AXES: axes}, pretty))
                return None
            print(self._dump_json(self._bindings_payload, pretty))
            return None
        if target and target not in BINDINGS_SHOW_TARGETS:
            print(MESSAGE_ERR_BINDINGS_SHOW)
            return None
        print(MESSAGE_BINDINGS_HEADER)
        if target in (EMPTY_STRING, BINDINGS_SHOW_CONTROLLERS):
            print(MESSAGE_BINDINGS_CONTROLLERS_HEADER)
            self._print_bindings_controllers(controllers)
            if target == BINDINGS_SHOW_CONTROLLERS:
                return None
        if target in (EMPTY_STRING, BINDINGS_SHOW_BINDINGS):
            print(MESSAGE_BINDINGS_BINDINGS_HEADER)
            self._print_bindings_entries(bindings)
            if target == BINDINGS_SHOW_BINDINGS:
                return None
        if target in (EMPTY_STRING, BINDINGS_SHOW_AXES):
            print(MESSAGE_BINDINGS_AXES_HEADER)
            self._print_bindings_axes(axes)
        return None

    def _print_bindings_controllers(self, controllers: object) -> None:
        if not isinstance(controllers, list) or not controllers:
            print(MESSAGE_BINDINGS_NONE)
            return
        for entry in controllers:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get(KEY_NAME, "")).strip()
            ctrl_type = str(entry.get(FIELD_TYPE, "")).strip()
            port = entry.get(KEY_PORT)
            if name:
                print(MESSAGE_BINDINGS_CONTROLLER_FMT.format(name=name, type=ctrl_type, port=port))

    def _print_bindings_entries(self, bindings: object) -> None:
        if not isinstance(bindings, list) or not bindings:
            print(MESSAGE_BINDINGS_NONE)
            return
        for idx, entry in enumerate(bindings, start=COUNT_ONE):
            if not isinstance(entry, dict):
                continue
            print(
                MESSAGE_BINDINGS_BINDING_FMT.format(
                    index=idx,
                    command=entry.get(KEY_COMMAND),
                    controller=entry.get(KEY_CONTROLLER),
                    input=entry.get(KEY_INPUT),
                    id=entry.get(KEY_ID),
                    mode=entry.get(KEY_MODE),
                )
            )

    def _print_bindings_axes(self, axes: object) -> None:
        if not isinstance(axes, list) or not axes:
            print(MESSAGE_BINDINGS_NONE)
            return
        for idx, entry in enumerate(axes, start=COUNT_ONE):
            if not isinstance(entry, dict):
                continue
            print(
                MESSAGE_BINDINGS_AXIS_FMT.format(
                    index=idx,
                    command=entry.get(KEY_COMMAND),
                    controller=entry.get(KEY_CONTROLLER),
                    id=entry.get(KEY_ID),
                    invert=entry.get(KEY_INVERT),
                    deadband=entry.get(KEY_DEADBAND),
                )
            )

    def _bindings_controller_command(self, tokens: List[str]) -> Optional[int]:
        """
        NAME
            _bindings_controller_command - Edit controller entries.
        """

        if not tokens:
            print(MESSAGE_ERR_BINDINGS_CONTROLLER_SET)
            return None
        action = tokens[COUNT_ZERO].lower()
        controllers = self._bindings_payload.get(KEY_CONTROLLERS, []) if self._bindings_payload else []
        if action == CMD_ADD:
            if len(tokens) < COUNT_FOUR:
                print(MESSAGE_ERR_BINDINGS_CONTROLLER_ADD)
                return None
            name = tokens[COUNT_ONE].strip()
            ctrl_type = tokens[COUNT_TWO].strip()
            try:
                port = int(tokens[COUNT_THREE])
            except ValueError:
                print(MESSAGE_ERR_BINDINGS_CONTROLLER_PORT)
                return None
            if self._bindings_find_controller(name, controllers):
                print(MESSAGE_ERR_BINDINGS_CONTROLLER_EXISTS)
                return None
            controllers.append({KEY_NAME: name, FIELD_TYPE: ctrl_type, KEY_PORT: port})
            self._bindings_payload[KEY_CONTROLLERS] = controllers
            self._bindings_dirty = True
            return None
        if action == CMD_SET:
            if len(tokens) < COUNT_FOUR:
                print(MESSAGE_ERR_BINDINGS_CONTROLLER_SET)
                return None
            name = tokens[COUNT_ONE].strip()
            field = tokens[COUNT_TWO].strip()
            value = " ".join(tokens[COUNT_THREE:]).strip()
            entry = self._bindings_find_controller(name, controllers)
            if not entry:
                print(MESSAGE_ERR_BINDINGS_CONTROLLER_NOT_FOUND)
                return None
            if field == KEY_NAME:
                return self._bindings_rename_controller(name, value)
            if field == FIELD_TYPE:
                entry[FIELD_TYPE] = value
            elif field == KEY_PORT:
                try:
                    entry[KEY_PORT] = int(value)
                except ValueError:
                    print(MESSAGE_ERR_BINDINGS_CONTROLLER_PORT)
                    return None
            else:
                print(MESSAGE_ERR_BINDINGS_FIELD_UNKNOWN)
                return None
            self._bindings_dirty = True
            return None
        if action == CMD_RENAME:
            if len(tokens) < COUNT_THREE:
                print(MESSAGE_ERR_BINDINGS_CONTROLLER_RENAME)
                return None
            return self._bindings_rename_controller(tokens[COUNT_ONE], tokens[COUNT_TWO])
        print(MESSAGE_ERR_BINDINGS_SUBCOMMAND)
        return None

    def _bindings_delete_controller(self, name: str) -> Optional[int]:
        """
        NAME
            _bindings_delete_controller - Remove a controller by name.
        """

        controllers = self._bindings_payload.get(KEY_CONTROLLERS, []) if self._bindings_payload else []
        entry = self._bindings_find_controller(name, controllers)
        if not entry:
            print(MESSAGE_ERR_BINDINGS_CONTROLLER_NOT_FOUND)
            return None
        if self._bindings_controller_in_use(name):
            print(MESSAGE_ERR_BINDINGS_CONTROLLER_IN_USE)
            return None
        controllers.remove(entry)
        self._bindings_payload[KEY_CONTROLLERS] = controllers
        self._bindings_dirty = True
        return None

    def _bindings_binding_command(self, tokens: List[str]) -> Optional[int]:
        """
        NAME
            _bindings_binding_command - Edit button binding entries.
        """

        if not tokens:
            print(MESSAGE_ERR_BINDINGS_BINDING_SET)
            return None
        action = tokens[COUNT_ZERO].lower()
        bindings = self._bindings_payload.get(KEY_BINDINGS, []) if self._bindings_payload else []
        if action == CMD_ADD:
            if len(tokens) < COUNT_SIX:
                print(MESSAGE_ERR_BINDINGS_BINDING_ADD)
                return None
            entry = {
                KEY_COMMAND: tokens[COUNT_ONE],
                KEY_CONTROLLER: tokens[COUNT_TWO],
                KEY_INPUT: tokens[COUNT_THREE],
                KEY_ID: tokens[COUNT_FOUR],
                KEY_MODE: tokens[COUNT_FIVE],
            }
            if not self._bindings_controller_exists(entry[KEY_CONTROLLER]):
                print(MESSAGE_ERR_BINDINGS_CONTROLLER_REQUIRED.format(name=entry[KEY_CONTROLLER]))
                return None
            bindings.append(entry)
            self._bindings_payload[KEY_BINDINGS] = bindings
            self._bindings_dirty = True
            return None
        if action == CMD_SET:
            if len(tokens) < COUNT_FOUR:
                print(MESSAGE_ERR_BINDINGS_BINDING_SET)
                return None
            index = self._parse_index(tokens[COUNT_ONE], MESSAGE_ERR_BINDINGS_BINDING_INDEX)
            if index is None:
                return None
            entry = self._bindings_entry_at(bindings, index)
            if entry is None:
                print(MESSAGE_ERR_BINDINGS_BINDING_INDEX)
                return None
            field = tokens[COUNT_TWO]
            value = " ".join(tokens[COUNT_THREE:]).strip()
            if field not in BINDINGS_BINDING_FIELDS:
                print(MESSAGE_ERR_BINDINGS_FIELD_UNKNOWN)
                return None
            if field == KEY_CONTROLLER and not self._bindings_controller_exists(value):
                print(MESSAGE_ERR_BINDINGS_CONTROLLER_REQUIRED.format(name=value))
                return None
            entry[field] = value
            self._bindings_dirty = True
            return None
        if action == CMD_DELETE:
            if len(tokens) < COUNT_TWO:
                print(MESSAGE_ERR_BINDINGS_BINDING_DELETE)
                return None
            index = self._parse_index(tokens[COUNT_ONE], MESSAGE_ERR_BINDINGS_BINDING_INDEX)
            if index is None:
                return None
            entry = self._bindings_entry_at(bindings, index)
            if entry is None:
                print(MESSAGE_ERR_BINDINGS_BINDING_INDEX)
                return None
            bindings.remove(entry)
            self._bindings_dirty = True
            return None
        print(MESSAGE_ERR_BINDINGS_SUBCOMMAND)
        return None

    def _bindings_axis_command(self, tokens: List[str]) -> Optional[int]:
        """
        NAME
            _bindings_axis_command - Edit axis binding entries.
        """

        if not tokens:
            print(MESSAGE_ERR_BINDINGS_AXIS_SET)
            return None
        action = tokens[COUNT_ZERO].lower()
        axes = self._bindings_payload.get(KEY_AXES, []) if self._bindings_payload else []
        if action == CMD_ADD:
            if len(tokens) < COUNT_EIGHT:
                print(MESSAGE_ERR_BINDINGS_AXIS_ADD)
                return None
            if tokens[COUNT_FOUR].lower() != KEY_INVERT:
                print(MESSAGE_ERR_BINDINGS_AXIS_ADD)
                return None
            if tokens[COUNT_SIX].lower() != KEY_DEADBAND:
                print(MESSAGE_ERR_BINDINGS_AXIS_ADD)
                return None
            invert = self._parse_bool(tokens[COUNT_FIVE])
            if invert is None:
                print(MESSAGE_ERR_BINDINGS_INVERT)
                return None
            try:
                deadband = float(tokens[COUNT_SEVEN])
            except ValueError:
                print(MESSAGE_ERR_BINDINGS_DEADBAND)
                return None
            if deadband < DEADBAND_MIN or deadband > DEADBAND_MAX:
                print(MESSAGE_ERR_BINDINGS_DEADBAND)
                return None
            controller = tokens[COUNT_TWO]
            if not self._bindings_controller_exists(controller):
                print(MESSAGE_ERR_BINDINGS_CONTROLLER_REQUIRED.format(name=controller))
                return None
            entry = {
                KEY_COMMAND: tokens[COUNT_ONE],
                KEY_CONTROLLER: controller,
                KEY_ID: tokens[COUNT_THREE],
                KEY_INVERT: invert,
                KEY_DEADBAND: deadband,
            }
            axes.append(entry)
            self._bindings_payload[KEY_AXES] = axes
            self._bindings_dirty = True
            return None
        if action == CMD_SET:
            if len(tokens) < COUNT_FOUR:
                print(MESSAGE_ERR_BINDINGS_AXIS_SET)
                return None
            index = self._parse_index(tokens[COUNT_ONE], MESSAGE_ERR_BINDINGS_AXIS_INDEX)
            if index is None:
                return None
            entry = self._bindings_entry_at(axes, index)
            if entry is None:
                print(MESSAGE_ERR_BINDINGS_AXIS_INDEX)
                return None
            field = tokens[COUNT_TWO]
            value = " ".join(tokens[COUNT_THREE:]).strip()
            if field not in BINDINGS_AXIS_FIELDS:
                print(MESSAGE_ERR_BINDINGS_FIELD_UNKNOWN)
                return None
            if field == KEY_CONTROLLER:
                if not self._bindings_controller_exists(value):
                    print(MESSAGE_ERR_BINDINGS_CONTROLLER_REQUIRED.format(name=value))
                    return None
                entry[field] = value
                self._bindings_dirty = True
                return None
            if field == KEY_INVERT:
                parsed = self._parse_bool(value)
                if parsed is None:
                    print(MESSAGE_ERR_BINDINGS_INVERT)
                    return None
                entry[field] = parsed
                self._bindings_dirty = True
                return None
            if field == KEY_DEADBAND:
                try:
                    deadband = float(value)
                except ValueError:
                    print(MESSAGE_ERR_BINDINGS_DEADBAND)
                    return None
                if deadband < DEADBAND_MIN or deadband > DEADBAND_MAX:
                    print(MESSAGE_ERR_BINDINGS_DEADBAND)
                    return None
                entry[field] = deadband
                self._bindings_dirty = True
                return None
            entry[field] = value
            self._bindings_dirty = True
            return None
        if action == CMD_DELETE:
            if len(tokens) < COUNT_TWO:
                print(MESSAGE_ERR_BINDINGS_AXIS_DELETE)
                return None
            index = self._parse_index(tokens[COUNT_ONE], MESSAGE_ERR_BINDINGS_AXIS_INDEX)
            if index is None:
                return None
            entry = self._bindings_entry_at(axes, index)
            if entry is None:
                print(MESSAGE_ERR_BINDINGS_AXIS_INDEX)
                return None
            axes.remove(entry)
            self._bindings_dirty = True
            return None
        print(MESSAGE_ERR_BINDINGS_SUBCOMMAND)
        return None

    def _bindings_validate(self, path: Optional[Path]) -> Optional[int]:
        """
        NAME
            _bindings_validate - Validate bindings payload or file.
        """

        payload = self._bindings_payload
        if path is not None:
            try:
                loaded = read_json(path)
            except Exception:
                print(MESSAGE_ERR_BINDINGS_LOAD.format(path=path))
                return EXIT_CODE_ERROR if self._batch else None
            if not isinstance(loaded, dict):
                print(MESSAGE_ERR_BINDINGS_VALIDATE.format(message=EMPTY_STRING))
                return EXIT_CODE_ERROR if self._batch else None
            payload = loaded
        self._store.set_bindings_payload(payload or {})
        result = self._store.validate_bindings_only(strict=True)
        errors = [issue for issue in result.errors() if issue.location == LOCATION_BINDINGS]
        if errors:
            message = self._format_store_errors(errors)
            print(MESSAGE_ERR_BINDINGS_VALIDATE.format(message=message))
            return EXIT_CODE_ERROR if self._batch else None
        print(AST_EXEC_SPEC["msg_ok_config"])
        return None

    def _validate_bindings_payload(self, payload: Dict[str, object]) -> List[str]:
        """
        NAME
            _validate_bindings_payload - Return validation errors for bindings.
        """

        errors: List[str] = []
        controllers = payload.get(KEY_CONTROLLERS, [])
        bindings = payload.get(KEY_BINDINGS, [])
        axes = payload.get(KEY_AXES, [])
        controller_names: set[str] = set()
        if isinstance(controllers, list):
            for entry in controllers:
                if not isinstance(entry, dict):
                    errors.append(MESSAGE_ERR_BINDINGS_CONTROLLER_NOT_FOUND)
                    continue
                name = str(entry.get(KEY_NAME, "")).strip()
                ctrl_type = str(entry.get(FIELD_TYPE, "")).strip()
                port = entry.get(KEY_PORT)
                if not name or not ctrl_type:
                    errors.append(MESSAGE_ERR_BINDINGS_CONTROLLER_SET)
                if name in controller_names:
                    errors.append(MESSAGE_ERR_BINDINGS_CONTROLLER_EXISTS)
                controller_names.add(name)
                if not isinstance(port, int):
                    errors.append(MESSAGE_ERR_BINDINGS_CONTROLLER_PORT)
        if isinstance(bindings, list):
            for entry in bindings:
                if not isinstance(entry, dict):
                    errors.append(MESSAGE_ERR_BINDINGS_BINDING_SET)
                    continue
                controller = str(entry.get(KEY_CONTROLLER, "")).strip()
                for field in BINDINGS_BINDING_FIELDS:
                    value = entry.get(field)
                    if value is None or str(value).strip() == EMPTY_STRING:
                        errors.append(MESSAGE_ERR_BINDINGS_BINDING_SET)
                        break
                if controller and controller not in controller_names:
                    errors.append(MESSAGE_ERR_BINDINGS_CONTROLLER_REQUIRED.format(name=controller))
        if isinstance(axes, list):
            for entry in axes:
                if not isinstance(entry, dict):
                    errors.append(MESSAGE_ERR_BINDINGS_AXIS_SET)
                    continue
                controller = str(entry.get(KEY_CONTROLLER, "")).strip()
                for field in BINDINGS_AXIS_FIELDS:
                    if entry.get(field) is None:
                        errors.append(MESSAGE_ERR_BINDINGS_AXIS_SET)
                        break
                invert = entry.get(KEY_INVERT)
                if not isinstance(invert, bool):
                    errors.append(MESSAGE_ERR_BINDINGS_INVERT)
                deadband = entry.get(KEY_DEADBAND)
                if not isinstance(deadband, (int, float)):
                    errors.append(MESSAGE_ERR_BINDINGS_DEADBAND)
                else:
                    if deadband < DEADBAND_MIN or deadband > DEADBAND_MAX:
                        errors.append(MESSAGE_ERR_BINDINGS_DEADBAND)
                if controller and controller not in controller_names:
                    errors.append(MESSAGE_ERR_BINDINGS_CONTROLLER_REQUIRED.format(name=controller))
        return errors

    def _bindings_find_controller(
        self, name: str, controllers: List[Dict[str, object]]
    ) -> Optional[Dict[str, object]]:
        """
        NAME
            _bindings_find_controller - Find a controller entry by name.
        """

        for entry in controllers:
            if not isinstance(entry, dict):
                continue
            if str(entry.get(KEY_NAME, "")).strip() == name:
                return entry
        return None

    def _bindings_controller_exists(self, name: str) -> bool:
        """
        NAME
            _bindings_controller_exists - Check for a controller by name.
        """

        controllers = self._bindings_payload.get(KEY_CONTROLLERS, []) if self._bindings_payload else []
        return self._bindings_find_controller(name, controllers) is not None

    def _bindings_controller_in_use(self, name: str) -> bool:
        """
        NAME
            _bindings_controller_in_use - Check references in bindings/axes.
        """

        if not self._bindings_payload:
            return False
        for entry in self._bindings_payload.get(KEY_BINDINGS, []):
            if isinstance(entry, dict) and str(entry.get(KEY_CONTROLLER, "")).strip() == name:
                return True
        for entry in self._bindings_payload.get(KEY_AXES, []):
            if isinstance(entry, dict) and str(entry.get(KEY_CONTROLLER, "")).strip() == name:
                return True
        return False

    def _bindings_rename_controller(self, old: str, new: str) -> Optional[int]:
        """
        NAME
            _bindings_rename_controller - Rename a controller and update references.
        """

        if old == new:
            return None
        controllers = self._bindings_payload.get(KEY_CONTROLLERS, []) if self._bindings_payload else []
        entry = self._bindings_find_controller(old, controllers)
        if not entry:
            print(MESSAGE_ERR_BINDINGS_CONTROLLER_NOT_FOUND)
            return None
        if self._bindings_find_controller(new, controllers):
            print(MESSAGE_ERR_BINDINGS_CONTROLLER_EXISTS)
            return None
        entry[KEY_NAME] = new
        for binding in self._bindings_payload.get(KEY_BINDINGS, []):
            if isinstance(binding, dict) and binding.get(KEY_CONTROLLER) == old:
                binding[KEY_CONTROLLER] = new
        for axis in self._bindings_payload.get(KEY_AXES, []):
            if isinstance(axis, dict) and axis.get(KEY_CONTROLLER) == old:
                axis[KEY_CONTROLLER] = new
        self._bindings_dirty = True
        return None

    def _bindings_entry_at(
        self, entries: List[Dict[str, object]], index: int
    ) -> Optional[Dict[str, object]]:
        """
        NAME
            _bindings_entry_at - Return 1-based entry by index.
        """

        if index < COUNT_ONE or index > len(entries):
            return None
        return entries[index - COUNT_ONE]

    def _parse_index(self, raw: str, error_message: str) -> Optional[int]:
        """
        NAME
            _parse_index - Parse a 1-based index value.
        """

        try:
            index = int(raw)
        except ValueError:
            print(error_message)
            return None
        if index < COUNT_ONE:
            print(error_message)
            return None
        return index

    def _ensure_can_mappings_loaded(self) -> bool:
        """
        NAME
            _ensure_can_mappings_loaded - Load CAN mappings if needed.
        """

        if isinstance(self._can_mappings, dict):
            return True
        self._load_can_mappings()
        return isinstance(self._can_mappings, dict)

    def _load_can_mappings_from_path(self, path: Path) -> Optional[int]:
        """
        NAME
            _load_can_mappings_from_path - Load CAN mappings from a path.
        """

        payload: Dict[str, object] = {}
        if path.exists():
            try:
                loaded = read_json(path)
            except Exception:
                print(MESSAGE_ERR_MAPPINGS_LOAD.format(path=path))
                return EXIT_CODE_ERROR if self._batch else None
            if isinstance(loaded, dict):
                payload = loaded
        manufacturers = payload.get(KEY_MANUFACTURERS)
        device_types = payload.get(KEY_DEVICE_TYPES)
        self._can_mappings = {
            KEY_MANUFACTURERS: manufacturers if isinstance(manufacturers, dict) else {},
            KEY_DEVICE_TYPES: device_types if isinstance(device_types, dict) else {},
        }
        self._can_mappings_path = path
        self._can_mappings_dirty = False
        self._sync_store_mappings()
        print(MESSAGE_INFO_MAPPINGS_LOADED.format(path=path))
        return None

    def _save_can_mappings_to_path(self, path: Path) -> Optional[int]:
        """
        NAME
            _save_can_mappings_to_path - Save CAN mappings to a path.
        """

        if not isinstance(self._can_mappings, dict):
            print(MESSAGE_ERR_MAPPINGS_LOAD.format(path=path))
            return EXIT_CODE_ERROR if self._batch else None
        payload = {
            KEY_MANUFACTURERS: self._can_mappings.get(KEY_MANUFACTURERS, {}),
            KEY_DEVICE_TYPES: self._can_mappings.get(KEY_DEVICE_TYPES, {}),
        }
        try:
            write_json(path, payload, indent=COUNT_TWO, trailing_newline=True)
        except Exception as exc:
            print(MESSAGE_ERR_MAPPINGS_WRITE.format(path=path, error=exc))
            return EXIT_CODE_ERROR if self._batch else None
        self._can_mappings_dirty = False
        self._can_mappings_path = path
        self._sync_store_mappings()
        print(MESSAGE_INFO_MAPPINGS_SAVED.format(path=path))
        return None

    def _mappings_show(self, tokens: List[str]) -> Optional[int]:
        """
        NAME
            _mappings_show - Show CAN mappings content.
        """

        if not isinstance(self._can_mappings, dict):
            print(MESSAGE_ERR_MAPPINGS_LOAD.format(path=EMPTY_STRING))
            return None
        _source, cleaned, json_output, pretty, ok = self._parse_show_flags(tokens)
        if not ok:
            return 2 if self._batch else None
        target = cleaned[COUNT_ZERO].lower() if cleaned else EMPTY_STRING
        manufacturers = self._can_mappings.get(KEY_MANUFACTURERS, {})
        device_types = self._can_mappings.get(KEY_DEVICE_TYPES, {})
        print(MESSAGE_SOURCE_LOCAL)
        if json_output:
            if target == MAPPINGS_SHOW_MANUFACTURERS:
                print(self._dump_json({KEY_MANUFACTURERS: manufacturers}, pretty))
                return None
            if target == MAPPINGS_SHOW_DEVICE_TYPES:
                print(self._dump_json({KEY_DEVICE_TYPES: device_types}, pretty))
                return None
            print(self._dump_json(self._can_mappings, pretty))
            return None
        if target and target not in MAPPINGS_SHOW_TARGETS:
            print(MESSAGE_ERR_MAPPINGS_SHOW)
            return None
        print(MESSAGE_MAPPINGS_HEADER)
        if target in (EMPTY_STRING, MAPPINGS_SHOW_MANUFACTURERS):
            print(MESSAGE_MAPPINGS_MANUFACTURERS_HEADER)
            self._print_mappings_entries(manufacturers)
            if target == MAPPINGS_SHOW_MANUFACTURERS:
                return None
        if target in (EMPTY_STRING, MAPPINGS_SHOW_DEVICE_TYPES):
            print(MESSAGE_MAPPINGS_DEVICE_TYPES_HEADER)
            self._print_mappings_entries(device_types)
        return None

    def _print_mappings_entries(self, entries: object) -> None:
        """
        NAME
            _print_mappings_entries - Render mapping entries.
        """

        if not isinstance(entries, dict) or not entries:
            print(MESSAGE_MAPPINGS_NONE)
            return
        for key in sorted(entries.keys(), key=lambda value: int(value) if str(value).isdigit() else value):
            name = entries.get(key)
            print(MESSAGE_MAPPINGS_ENTRY_FMT.format(id=key, name=name))

    def _mappings_entry_command(self, target_key: str, tokens: List[str]) -> Optional[int]:
        """
        NAME
            _mappings_entry_command - Edit manufacturer/device-type entries.
        """

        if not tokens:
            print(MESSAGE_ERR_MAPPINGS_SUBCOMMAND)
            return None
        action = tokens[COUNT_ZERO].lower()
        if action == CMD_SET:
            if len(tokens) < COUNT_THREE:
                print(MESSAGE_ERR_MAPPINGS_SET.format(target=target_key))
                return None
            try:
                key = int(tokens[COUNT_ONE])
            except ValueError:
                print(MESSAGE_ERR_MAPPINGS_ID)
                return None
            name = " ".join(tokens[COUNT_TWO:]).strip()
            entries = self._can_mappings.setdefault(target_key, {})
            entries[str(key)] = name
            self._can_mappings_dirty = True
            return None
        if action in (CMD_DELETE, CMD_NO):
            if len(tokens) < COUNT_TWO:
                print(MESSAGE_ERR_MAPPINGS_DELETE.format(target=target_key))
                return None
            try:
                key = int(tokens[COUNT_ONE])
            except ValueError:
                print(MESSAGE_ERR_MAPPINGS_ID)
                return None
            entries = self._can_mappings.setdefault(target_key, {})
            entries.pop(str(key), None)
            self._can_mappings_dirty = True
            return None
        print(MESSAGE_ERR_MAPPINGS_SUBCOMMAND)
        return None

    def _mappings_validate(self, path: Optional[Path]) -> Optional[int]:
        """
        NAME
            _mappings_validate - Validate CAN mappings payload or file.
        """

        payload = self._can_mappings
        if path is not None:
            try:
                loaded = read_json(path)
            except Exception:
                print(MESSAGE_ERR_MAPPINGS_LOAD.format(path=path))
                return EXIT_CODE_ERROR if self._batch else None
            if not isinstance(loaded, dict):
                print(MESSAGE_ERR_MAPPINGS_VALIDATE.format(message=EMPTY_STRING))
                return EXIT_CODE_ERROR if self._batch else None
            payload = loaded
        self._store.set_mappings_payload(payload or {})
        result = self._store.validate_mappings_only(strict=True)
        errors = [issue for issue in result.errors() if issue.location == LOCATION_MAPPINGS]
        if errors:
            message = self._format_store_errors(errors)
            print(MESSAGE_ERR_MAPPINGS_VALIDATE.format(message=message))
            return EXIT_CODE_ERROR if self._batch else None
        print(AST_EXEC_SPEC["msg_ok_config"])
        return None

    def _validate_mappings_payload(self, payload: Dict[str, object]) -> List[str]:
        """
        NAME
            _validate_mappings_payload - Return validation errors for mappings.
        """

        errors: List[str] = []
        for key in (KEY_MANUFACTURERS, KEY_DEVICE_TYPES):
            entries = payload.get(key)
            if not isinstance(entries, dict):
                errors.append(MESSAGE_ERR_MAPPINGS_SUBCOMMAND)
                continue
            for entry_key, entry_value in entries.items():
                if not str(entry_key).isdigit():
                    errors.append(MESSAGE_ERR_MAPPINGS_ID)
                if entry_value is None or str(entry_value).strip() == EMPTY_STRING:
                    errors.append(MESSAGE_ERR_MAPPINGS_SET.format(target=key))
        return errors

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
                TEST_TYPE_DEVICE_ACTION.lower(): TEST_TYPE_DEVICE_ACTION,
            }
            if kind not in kind_map:
                print(MESSAGE_ERROR_TYPE)
                return None
            test.test_type = kind_map[kind]
            if test.test_type == TEST_TYPE_JOYSTICK:
                test.joystick = test.joystick or TestBindingJoystick()
                test.button = None
                test.deadband_sweep = None
                test.device_action = None
            elif test.test_type == TEST_TYPE_DEADBAND_SWEEP:
                from tools.common.test_authoring.model import DeadbandSweepModel
                test.deadband_sweep = test.deadband_sweep or DeadbandSweepModel()
                test.joystick = None
                test.button = None
                test.device_action = None
            elif test.test_type == TEST_TYPE_DEVICE_ACTION:
                test.device_action = test.device_action or DeviceActionModel()
                test.joystick = None
                test.button = None
                test.deadband_sweep = None
            else:
                test.button = test.button or TestBindingButton()
                test.joystick = None
                test.deadband_sweep = None
                test.device_action = None
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
                self._warn(MESSAGE_ERROR_DEVICE_DUP)
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
        if cmd == CMD_ACTION and len(tokens) >= 2:
            if test.test_type != TEST_TYPE_DEVICE_ACTION:
                print(MESSAGE_ERROR_ACTION_TYPE)
                return None
            action = tokens[1].lower()
            if action not in ACTION_ALLOWED:
                print(MESSAGE_ERROR_ACTION_REQUIRED)
                return None
            test.device_action = test.device_action or DeviceActionModel()
            test.device_action.action = action
            self._tests_dirty = True
            return None
        if cmd == CMD_COLOR and len(tokens) >= 2:
            if test.test_type != TEST_TYPE_DEVICE_ACTION:
                print(MESSAGE_ERROR_COLOR_TYPE)
                return None
            value = tokens[1]
            if not COLOR_HEX_PATTERN.match(value):
                print(MESSAGE_ERROR_COLOR_REQUIRED)
                return None
            test.device_action = test.device_action or DeviceActionModel()
            test.device_action.color = value
            self._tests_dirty = True
            return None
        if cmd == CMD_PATTERN and len(tokens) >= 2:
            if test.test_type != TEST_TYPE_DEVICE_ACTION:
                print(MESSAGE_ERROR_PATTERN_TYPE)
                return None
            value = tokens[1].lower()
            if value not in PATTERN_ALLOWED:
                print(MESSAGE_ERROR_PATTERN_VALUE)
                return None
            test.device_action = test.device_action or DeviceActionModel()
            test.device_action.pattern = value
            self._tests_dirty = True
            return None
        if cmd == CMD_BRIGHTNESS and len(tokens) >= 2:
            if test.test_type != TEST_TYPE_DEVICE_ACTION:
                print(MESSAGE_ERROR_BRIGHTNESS_TYPE)
                return None
            try:
                value = float(tokens[1])
            except ValueError:
                print(MESSAGE_ERROR_BRIGHTNESS_NUMBER)
                return None
            if value < BRIGHTNESS_MIN or value > BRIGHTNESS_MAX:
                print(MESSAGE_ERROR_BRIGHTNESS_RANGE)
                return None
            test.device_action = test.device_action or DeviceActionModel()
            test.device_action.brightness = value
            self._tests_dirty = True
            return None
        if cmd == CMD_DURATION and len(tokens) >= 2:
            if test.test_type != TEST_TYPE_DEVICE_ACTION:
                print(MESSAGE_ERROR_DURATION_TYPE)
                return None
            try:
                value = float(tokens[1])
            except ValueError:
                print(MESSAGE_ERROR_DURATION_NUMBER)
                return None
            if value < DURATION_MIN_SEC:
                print(MESSAGE_ERROR_DURATION_RANGE)
                return None
            test.device_action = test.device_action or DeviceActionModel()
            test.device_action.duration_sec = value
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
        source, cleaned, json_output, pretty, ok = self._parse_show_flags(tokens[1:])
        if not ok:
            return 2 if self._batch else None
        if source:
            pass
        if len(cleaned) >= 1 and cleaned[0].lower() == CMD_TESTS:
            if json_output:
                self._print_tests_json(pretty)
                return None
            self._print_tests()
            return None
        if len(cleaned) >= 2 and cleaned[0].lower() == CMD_TEST:
            test_set = self._get_active_test_set()
            test = self._find_test(cleaned[1], test_set)
            if not test:
                print(MESSAGE_ERROR_TEST_NOT_FOUND)
                return None
            if json_output:
                self._print_test_json(test, pretty)
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
        result = validate_model(
            model,
            profile_name=profile,
            controller_names=controller_names,
            device_catalog=self._tests_device_catalog,
            duplicate_labels=self._tests_duplicate_labels,
        )
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
            self._warn(
                MESSAGE_WARNING_WITH_TEST.format(
                    message=issue.message,
                    test=test_name,
                )
            )
        payload = model_to_payload(model)
        write_tests_payload(path, payload)
        self._tests_dirty = False
        self._sync_store_tests()
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
        model = self._tests_model or TestAuthoringModel()
        active_name = self._tests_active_set or model.default_test_set or DEFAULT_TEST_SET
        test_sets = model.test_sets
        if test_sets:
            print(MESSAGE_TEST_SETS_HEADER)
            for name in sorted(test_sets.keys()):
                entry = test_sets.get(name)
                count = len(entry.tests) if entry else 0
                print(MESSAGE_TEST_SETS_ENTRY.format(name=name, count=count))
        else:
            print(MESSAGE_TEST_SETS_HEADER)
            print(MESSAGE_TESTS_TEMPLATES_NONE)

        test_set = test_sets.get(active_name)
        if test_set is None:
            test_set = TestSetModel(name=active_name, tests=[])
            test_sets[active_name] = test_set
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

    def _print_tests_json(self, pretty: bool) -> None:
        """
        NAME
            _print_tests_json - Render tests as JSON payload.
        """

        model = self._tests_model or TestAuthoringModel()
        payload = model_to_payload(model)
        print(self._dump_json(payload, pretty))

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
            print(MESSAGE_TEST_INPUT_SOURCE.format(source=STRING_NONE))
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
        if test.test_type == TEST_TYPE_DEVICE_ACTION:
            device_action = test.device_action or DeviceActionModel()
            action = device_action.action or STRING_NONE
            color = device_action.color or STRING_NONE
            pattern = device_action.pattern or STRING_NONE
            brightness = (
                device_action.brightness if device_action.brightness is not None else STRING_NONE
            )
            duration = (
                device_action.duration_sec if device_action.duration_sec is not None else STRING_NONE
            )
            print(MESSAGE_TEST_ACTION.format(action=action))
            print(MESSAGE_TEST_COLOR.format(color=color))
            print(MESSAGE_TEST_PATTERN.format(pattern=pattern))
            print(MESSAGE_TEST_BRIGHTNESS.format(brightness=brightness))
            print(MESSAGE_TEST_DURATION.format(duration=duration))

    def _print_test_json(self, test: TestModel, pretty: bool) -> None:
        """
        NAME
            _print_test_json - Render a single test as JSON payload.
        """

        test_set = self._get_active_test_set()
        temp_set = TestSetModel(name=test_set.name, tests=[test])
        model = TestAuthoringModel(
            default_test_set=test_set.name,
            test_sets={test_set.name: temp_set},
        )
        payload = model_to_payload(model)
        tests_payload = payload.get(KEY_TEST_SETS)
        entries = []
        if isinstance(tests_payload, dict):
            entries = tests_payload.get(test_set.name, []) or []
        entry = entries[COUNT_ZERO] if isinstance(entries, list) and entries else {}
        print(self._dump_json({KEY_TEST_SET: test_set.name, KEY_TEST: entry}, pretty))

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
        if cmd == CMD_BINDINGS:
            return self._config_bindings_command(tokens)
        if cmd == CMD_CAN_MAPPINGS:
            return self._config_can_mappings_command(tokens)
        if cmd == CMD_PROFILE:
            if len(tokens) < 2:
                print(MESSAGE_ERR_PROFILE_REQUIRED)
                return 2 if self._batch else None
            if len(tokens) >= 3 and tokens[1].lower() == CMD_CREATE:
                if not self._create_profile(tokens[2]):
                    return 2 if self._batch else None
                return None
            if not self._set_active_profile(tokens[1]):
                return 2 if self._batch else None
            print(f"Active profile: {self._groups_profile}")
            return None
        if cmd == "group" and len(tokens) >= 2 and not self._session.is_connected():
            name = tokens[1]
            if not self._select_or_create_local_group(name):
                return EXIT_CODE_ERROR if self._batch else None
            self._modes.append(CliMode("group", name))
            self._warn("WARNING: Robot not connected; local group selected.")
            return None
        if cmd == "rename" and len(tokens) >= 4 and tokens[1].lower() == "device":
            if self._rename_local_device(tokens[2], tokens[3]):
                print(f"Renamed device {tokens[2]} -> {tokens[3]}.")
                return None
            return 2 if self._batch else None
        if cmd == "no" and len(tokens) >= 3 and tokens[1].lower() == "device":
            name = tokens[2]
            if not self._confirm(f"Delete device '{name}'?"):
                return None
            if not self._delete_local_device(name):
                return 2 if self._batch else None
            print(f"Deleted device {name}.")
            return None
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
            self._warn("WARNING: Robot not connected; local group deleted.")
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
            self._warn("WARNING: Robot not connected; local selected-device updated.")
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
            self._warn("WARNING: Robot not connected; local selected-mode updated.")
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
                self._sync_store_from_local()
                result = self._store.validate_profiles_only(strict=True)
                ok = result.ok()
                message = self._format_store_errors(result.errors())
            if ok:
                print(MESSAGE_OK_CONFIG_VALID)
                return None
            print(MESSAGE_ERR_CONFIG_VALIDATE.format(message=message))
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

    def _config_bindings_command(self, tokens: List[str]) -> Optional[int]:
        """
        NAME
            _config_bindings_command - Handle bindings subcommands.
        """

        if not self._ensure_bindings_loaded():
            return EXIT_CODE_ERROR if self._batch else None
        if len(tokens) == COUNT_ONE:
            return self._bindings_show([])
        sub = tokens[COUNT_ONE].lower()
        if sub == CMD_SHOW:
            return self._bindings_show(tokens[COUNT_TWO:])
        if sub == CMD_CONTROLLER:
            return self._bindings_controller_command(tokens[COUNT_TWO:])
        if sub == CMD_BINDING:
            return self._bindings_binding_command(tokens[COUNT_TWO:])
        if sub == CMD_AXIS:
            return self._bindings_axis_command(tokens[COUNT_TWO:])
        if sub == CMD_LOAD:
            if len(tokens) < COUNT_THREE:
                print(MESSAGE_ERR_BINDINGS_LOAD.format(path=EMPTY_STRING))
                return None
            return self._load_bindings_from_path(Path(tokens[COUNT_TWO]))
        if sub == CMD_SAVE:
            if len(tokens) < COUNT_THREE:
                print(MESSAGE_ERR_BINDINGS_WRITE.format(path=EMPTY_STRING, error=EMPTY_STRING))
                return None
            return self._save_bindings_to_path(Path(tokens[COUNT_TWO]))
        if sub == CMD_VALIDATE:
            path = Path(tokens[COUNT_TWO]) if len(tokens) >= COUNT_THREE else None
            return self._bindings_validate(path)
        if sub == CMD_NO and len(tokens) >= COUNT_THREE and tokens[COUNT_TWO].lower() == CMD_CONTROLLER:
            if len(tokens) < COUNT_FOUR:
                print(MESSAGE_ERR_BINDINGS_CONTROLLER_DELETE)
                return None
            return self._bindings_delete_controller(tokens[COUNT_THREE])
        print(MESSAGE_ERR_BINDINGS_SUBCOMMAND)
        return None

    def _config_can_mappings_command(self, tokens: List[str]) -> Optional[int]:
        """
        NAME
            _config_can_mappings_command - Handle CAN mappings subcommands.
        """

        if not self._ensure_can_mappings_loaded():
            return EXIT_CODE_ERROR if self._batch else None
        if len(tokens) == COUNT_ONE:
            return self._mappings_show([])
        sub = tokens[COUNT_ONE].lower()
        if sub == CMD_SHOW:
            return self._mappings_show(tokens[COUNT_TWO:])
        if sub == CMD_MANUFACTURER:
            return self._mappings_entry_command(KEY_MANUFACTURERS, tokens[COUNT_TWO:])
        if sub == CMD_DEVICE_TYPE_NAME:
            return self._mappings_entry_command(KEY_DEVICE_TYPES, tokens[COUNT_TWO:])
        if sub == CMD_LOAD:
            if len(tokens) < COUNT_THREE:
                print(MESSAGE_ERR_MAPPINGS_LOAD.format(path=EMPTY_STRING))
                return None
            return self._load_can_mappings_from_path(Path(tokens[COUNT_TWO]))
        if sub == CMD_SAVE:
            if len(tokens) < COUNT_THREE:
                print(MESSAGE_ERR_MAPPINGS_WRITE.format(path=EMPTY_STRING, error=EMPTY_STRING))
                return None
            return self._save_can_mappings_to_path(Path(tokens[COUNT_TWO]))
        if sub == CMD_VALIDATE:
            path = Path(tokens[COUNT_TWO]) if len(tokens) >= COUNT_THREE else None
            return self._mappings_validate(path)
        print(MESSAGE_ERR_MAPPINGS_SUBCOMMAND)
        return None

    def _group_command(self, tokens: List[str]) -> Optional[int]:
        group = self._modes[-1].group
        cmd = tokens[0].lower()
        if not self._session.is_connected():
            return self._group_command_local(tokens, group)
        if cmd == "show":
            if not self._validate_pretty_flag(tokens):
                return EXIT_CODE_ERROR if self._batch else None
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
        if cmd in ("delete", "remove") or (
            cmd == "no" and len(tokens) >= 2 and tokens[1].lower() == "device"
        ):
            if not self._confirm(f"Delete device '{device}'?"):
                return None
            if not self._delete_local_device(device):
                return 2 if self._batch else None
            print(f"Deleted device {device}.")
            self._pop_mode()
            return None
        print(f"ERROR: Unknown command: {' '.join(tokens)}")
        return None

    def _handle_show(self, tokens: List[str]) -> Optional[int]:
        if not tokens:
            print(MESSAGE_ERR_SHOW_REQUIRES_TARGET)
            return None
        source, tokens, json_output, pretty, ok = self._parse_show_flags(tokens)
        if not ok:
            return 2 if self._batch else None
        if not tokens:
            print(MESSAGE_ERR_SHOW_REQUIRES_TARGET)
            return None
        target = tokens[0].lower()
        if target == SHOW_TARGET_CONFIG and len(tokens) >= 2:
            name = tokens[1].lower()
            if name == SHOW_CONFIG_LOCAL_RAW:
                target = SHOW_TARGET_CONFIG_RAW
            elif name == SHOW_CONFIG_DIRTY:
                target = SHOW_TARGET_CONFIG_DIRTY
        if (
            target == CMD_DEVICE
            and len(tokens) >= 3
            and tokens[1].lower() == CMD_REGISTRY
        ):
            target = SHOW_TARGET_DEVICE_REGISTRY
            tokens = [SHOW_TARGET_DEVICE_REGISTRY, tokens[2]]
        if target == SHOW_TARGET_CONFIG:
            target = SHOW_TARGET_RUNTIME
        if target == SHOW_TARGET_MESSAGE_LEVEL:
            source = "local"
        if target in (SHOW_TARGET_CONFIG_RAW, SHOW_TARGET_CONFIG_DIRTY):
            source = "local"
        if source == "both":
            local_ok = self._show_local(target, tokens, json_output, pretty)
            robot_ok = self._show_robot(target, tokens, json_output)
            if self._batch and (not local_ok or not robot_ok):
                return 2
            return None
        if source == "local":
            if not self._show_local(target, tokens, json_output, pretty):
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
            self._groups_dirty = False
            self._sync_group_profile()
            self._sync_store_from_local()
        if not self._session.is_connected():
            self._warn("WARNING: Robot not connected; local config loaded only.")
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
            self._warn("WARNING: Timeout waiting for OUT.", essential=True)
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

    def _settings_path(self) -> Path:
        return repo_root() / CLI_SETTINGS_FILENAME

    def _load_message_level(self, message_level: Optional[str]) -> None:
        if message_level:
            self._message_level_from_flag = True
            self._set_message_level(message_level, persist=False)
            return
        level = self._read_message_level()
        if level:
            self._set_message_level(level, persist=False)

    def _read_message_level(self) -> Optional[str]:
        path = self._settings_path()
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        level = payload.get("message_level") if isinstance(payload, dict) else None
        if isinstance(level, str) and level in MESSAGE_LEVELS:
            return level
        return None

    def _write_message_level(self) -> None:
        path = self._settings_path()
        payload = {"message_level": self._message_level}
        try:
            path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        except Exception:
            return

    def _set_message_level(self, level: str, persist: bool) -> bool:
        value = level.strip().lower()
        if value not in MESSAGE_LEVELS:
            return False
        self._message_level = value
        if persist:
            self._write_message_level()
        return True

    def _warn(self, message: str, essential: bool = False) -> None:
        if self._message_level == MESSAGE_LEVEL_EXPERT and not essential:
            return
        print(message)

    def _tip(self, key: str, message: str) -> None:
        if self._batch:
            return
        if self._message_level != MESSAGE_LEVEL_BEGINNER:
            return
        if key in self._tips_suppressed:
            return
        self._tips_suppressed.add(key)
        print(message)

    def _clear_tip(self, key: str) -> None:
        self._tips_suppressed.discard(key)

    def _warn_unsaved_if_needed(self) -> None:
        if self._modes[-1].name == "exec":
            return
        dirty = {name: flag for name, flag in self._dirty_state().items() if flag}
        if not dirty:
            self._clear_tip("unsaved")
            return
        items = ", ".join(sorted(dirty.keys()))
        self._warn(f"WARNING: Unsaved changes in: {items}.", essential=True)
        self._tip(
            "unsaved",
            "You have unsaved changes. Use `write tests ...` or `save profiles ...` to save.",
        )

    def _show_message_level(self, json_output: bool, pretty: bool) -> bool:
        if json_output:
            print(self._dump_json({"messageLevel": self._message_level}, pretty))
        else:
            print(MESSAGE_MESSAGE_LEVEL.format(level=self._message_level))
        return True

    @staticmethod
    def _validate_pretty_flag(tokens: List[str]) -> bool:
        if FLAG_PRETTY in tokens and FLAG_JSON not in tokens:
            print(MESSAGE_ERR_PRETTY_REQUIRES_JSON)
            return False
        return True

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
                "messages": "messages <beginner|medium|expert>\n  Set CLI message level.",
                "show message-level": "show message-level\n  Show current CLI message level.",
                "group": "group <name>\n  Create/select a group (config mode).",
                "no group": "no group <name>\n  Delete group (config mode, prompts in interactive).",
                "no device": "no device <name>\n  Delete a device from the active profile.",
                "profile": (
                    "profile <name>\n"
                    "  Select active profile for groups/bindings.\n"
                    "profile create <name>\n"
                    "  Create a new empty profile and select it."
                ),
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
                    "  Save bringup_system.json (profiles + bridgeConfig.byProfile)."
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
                    "device mode: show, set <field> <value>, no <field>, delete\n"
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
                "bindings": (
                    "bindings show [controllers|bindings|axes] [--json] [--pretty]\n"
                    "bindings controller add <name> <type> <port>\n"
                    "bindings controller set <name> <field> <value>\n"
                    "bindings controller rename <old> <new>\n"
                    "bindings no controller <name>\n"
                    "bindings binding add <command> <controller> <input> <id> <mode>\n"
                    "bindings binding set <index> <field> <value>\n"
                    "bindings binding delete <index>\n"
                    "bindings axis add <command> <controller> <id> invert <on|off> deadband <value>\n"
                    "bindings axis set <index> <field> <value>\n"
                    "bindings axis delete <index>\n"
                    "bindings load <path>\n"
                    "bindings save <path>\n"
                    "bindings validate [path]"
                ),
                "can-mappings": (
                    "can-mappings show [manufacturers|device-types] [--json] [--pretty]\n"
                    "can-mappings manufacturer set <id> <name>\n"
                    "can-mappings manufacturer delete <id>\n"
                    "can-mappings device-type set <id> <name>\n"
                    "can-mappings device-type delete <id>\n"
                    "can-mappings load <path>\n"
                    "can-mappings save <path>\n"
                    "can-mappings validate [path]"
                ),
            "tests": (
                "tests templates\n"
                "tests load <path>\n"
                "tests merge <path>\n"
                "tests load template <name>\n"
                "tests save\n"
                "tests clear"
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
                "json": "append --json to show commands for JSON output; add --pretty for pretty JSON",
                "sources": "append robot|local|both to show commands to select source",
                "batch": "use --batch --script <file> (no prompts, conflict policy applies)",
                "conflict-policy": "set with --conflict-policy <error|move>",
                "exec": "exec mode: show, connect, disconnect, configure terminal",
                "config": (
                    "config mode: profile, group, no group, no device, selected-device, selected-mode, "
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
            "Common: help, exit, end, quit, ping, echo, messages\n"
            "Exec: show, connect, disconnect, configure terminal\n"
            "Config: profile, group, device, bindings, can-mappings, tests, no group, selected-device, selected-mode, merge/import/export/save\n"
            "Group: show, add device, no device, member, bind, no bind, enable, disable, run test\n"
            "Device: show, set, no\n"
            "Tips: help show | help sources | help group | help batch | help json"
        )

    def _parse_show_flags(self, tokens: List[str]) -> tuple[str, List[str], bool, bool, bool]:
        source = ""
        cleaned: List[str] = []
        json_output = False
        pretty = False
        for tok in tokens:
            lower = tok.lower()
            if lower in ("--json",):
                json_output = True
                continue
            if lower in ("--pretty",):
                pretty = True
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
        if pretty and not json_output:
            print(MESSAGE_ERR_PRETTY_REQUIRES_JSON)
            return source, cleaned, False, False, False
        return source, cleaned, json_output, pretty, True

    @staticmethod
    def _dump_json(payload: object, pretty: bool) -> str:
        """
        NAME
            _dump_json - Serialize JSON with optional pretty formatting.
        """
        if pretty:
            return json.dumps(payload, indent=JSON_PRETTY_INDENT)
        return json.dumps(payload)

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

    def _show_local(
        self, target: str, tokens: List[str], json_output: bool, pretty: bool
    ) -> bool:
        if target == SHOW_TARGET_MESSAGE_LEVEL:
            return self._show_message_level(json_output, pretty)
        if not self._local_config:
            print(MESSAGE_ERR_LOCAL_CONFIG_MISSING)
            return False
        if target == SHOW_TARGET_CONFIG_RAW:
            return self._show_local_config_raw(json_output, pretty)
        if target == SHOW_TARGET_CONFIG_DIRTY:
            return self._show_local_config_dirty(json_output, pretty)
        if target == SHOW_TARGET_PROFILES:
            return self._show_local_profiles(json_output, pretty)
        if target == SHOW_TARGET_PROFILE:
            name = tokens[1] if len(tokens) >= 2 else ""
            return self._show_local_profile(name, json_output, pretty)
        if target == SHOW_TARGET_DEVICE_REGISTRY:
            name = tokens[1] if len(tokens) >= 2 else ""
            return self._show_local_registry_device(name, json_output, pretty)
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
                print(self._dump_json(payload_json, pretty))
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

    def _show_local_config_dirty(self, json_output: bool, pretty: bool) -> bool:
        """
        NAME
            _show_local_config_dirty - Show local dirty flags.
        """

        dirty = self._dirty_state()
        print(MESSAGE_SOURCE_LOCAL)
        if json_output:
            print(self._dump_json({KEY_DIRTY: dirty}, pretty))
            return True
        print(MESSAGE_DIRTY_HEADER)
        any_dirty = False
        for name in sorted(dirty.keys()):
            value = dirty[name]
            if value:
                any_dirty = True
            print(MESSAGE_DIRTY_ENTRY.format(name=name, value=str(value).lower()))
        if not any_dirty:
            print(MESSAGE_DIRTY_NONE)
        return True

    def _show_local_profiles(self, json_output: bool, pretty: bool) -> bool:
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
            print(self._dump_json({KEY_PROFILES: names}, pretty))
            return True
        if not names:
            print(MESSAGE_LOCAL_PROFILES_EMPTY)
            return True
        print(MESSAGE_LOCAL_PROFILES_HEADER)
        for name in names:
            print(f"  {name}")
        return True

    def _show_local_profile(self, name: str, json_output: bool, pretty: bool) -> bool:
        """
        NAME
            _show_local_profile - Show profile summary info.
        """
        payload = self._local_root_payload
        profiles = payload.get(KEY_PROFILES) if isinstance(payload, dict) else {}
        names = [name for name in profiles.keys() if isinstance(name, str)] if isinstance(profiles, dict) else []
        active = self._active_profile_name() or ""
        default_profile = self._default_profile_name() or ""
        selected = name.strip() if name else ""
        if selected:
            if not isinstance(profiles, dict) or selected not in profiles:
                print(MESSAGE_ERR_PROFILE_NOT_FOUND)
                return False
            profile = profiles.get(selected)
            labels = profile.get(KEY_PROFILE_DEVICES) if isinstance(profile, dict) else []
            device_labels = [label for label in labels if isinstance(label, str)]
            output = {KEY_PROFILE: selected, KEY_PROFILE_DEVICES: sorted(device_labels)}
            print(MESSAGE_SOURCE_LOCAL)
            if json_output:
                print(self._dump_json(output, pretty))
                return True
            print(MESSAGE_LOCAL_PROFILE_HEADER)
            print(MESSAGE_LOCAL_PROFILE_NAME.format(name=selected))
            print(MESSAGE_LOCAL_PROFILE_DEVICES_HEADER.format(count=len(device_labels)))
            for label in device_labels:
                print(MESSAGE_LOCAL_PROFILE_DEVICE_FMT.format(label=label))
            return True
        count = len(names)
        output = {KEY_ACTIVE: active, KEY_DEFAULT: default_profile, KEY_AVAILABLE: sorted(names)}
        print(MESSAGE_SOURCE_LOCAL)
        if json_output:
            print(self._dump_json({KEY_PROFILE_INFO: output}, pretty))
            return True
        print(MESSAGE_LOCAL_PROFILE_HEADER)
        print(MESSAGE_LOCAL_PROFILE_ACTIVE.format(name=active or STRING_NONE))
        print(MESSAGE_LOCAL_PROFILE_DEFAULT.format(name=default_profile or STRING_NONE))
        print(MESSAGE_LOCAL_PROFILE_AVAILABLE.format(count=count))
        return True

    def _show_local_config_raw(self, json_output: bool, pretty: bool) -> bool:
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
            print(self._dump_json(payload, pretty))
            return True
        print(MESSAGE_LOCAL_CONFIG_RAW)
        print(json.dumps(payload, indent=JSON_PRETTY_INDENT))
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
                self._warn("WARNING: Robot not connected; local group member added.")
                return None
            return 2 if self._batch else None
        if cmd == "no" and len(tokens) >= 3 and tokens[1].lower() == "device":
            if self._remove_local_group_member(group, tokens[2]):
                self._warn("WARNING: Robot not connected; local group member removed.")
                return None
            return 2 if self._batch else None
        if cmd == "member" and len(tokens) >= 3:
            action = tokens[2].lower()
            if action in ("enable", "disable", "toggle"):
                if self._set_local_member_enabled(group, tokens[1], action):
                    self._warn("WARNING: Robot not connected; local member updated.")
                    return None
                return EXIT_CODE_ERROR if self._batch else None
        if cmd == "bind" and len(tokens) >= 3:
            if self._add_local_binding(group, tokens[1:]):
                self._warn("WARNING: Robot not connected; local binding updated.")
                return None
            return 2 if self._batch else None
        if cmd == "no" and len(tokens) >= 2 and tokens[1].lower() == "bind":
            if self._clear_local_bindings(group):
                self._warn("WARNING: Robot not connected; local bindings cleared.")
                return None
            return 2 if self._batch else None
        if cmd == "enable":
            if self._set_local_group_enabled(group, True):
                self._warn("WARNING: Robot not connected; local group enabled.")
                return None
            return 2 if self._batch else None
        if cmd == "disable":
            if self._set_local_group_enabled(group, False):
                self._warn("WARNING: Robot not connected; local group disabled.")
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
        self._mark_groups_dirty()
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
        self._mark_groups_dirty()
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
        self._mark_groups_dirty()
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
        self._mark_groups_dirty()
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
        self._mark_groups_dirty()
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
        self._mark_groups_dirty()
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
                    self._mark_groups_dirty()
                    return True
            elif isinstance(member, str):
                if member.strip().lower() == device.lower():
                    members.remove(member)
                    members.append({"device": member, "enabled": action != "disable"})
                    self._mark_groups_dirty()
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
        self._mark_groups_dirty()
        return True

    def _clear_local_bindings(self, group_name: str) -> bool:
        group = self._find_local_group(group_name)
        if group is None:
            print("ERROR: Local group not found.")
            return False
        group["bindings"] = []
        self._mark_groups_dirty()
        return True

    def _set_local_group_enabled(self, group_name: str, enabled: bool) -> bool:
        group = self._find_local_group(group_name)
        if group is None:
            print("ERROR: Local group not found.")
            return False
        group["enabled"] = bool(enabled)
        self._mark_groups_dirty()
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

    def _delete_local_device(self, name: str) -> bool:
        if not self._local_config:
            print("ERROR: Local config not loaded. Use merge/import config <bringup_system.json>.")
            return False
        if self._local_devices_locked:
            return self._delete_profiles_device(name)
        label = name.strip()
        if not label:
            print("ERROR: device name required.")
            return False
        config = self._local_config
        devices = config.get("devices")
        if not isinstance(devices, list):
            print("ERROR: No local devices are defined.")
            return False
        removed = False
        for idx, device in enumerate(list(devices)):
            if not isinstance(device, dict):
                continue
            dev_name = str(device.get("name", "")).strip()
            if dev_name.lower() == label.lower():
                del devices[idx]
                removed = True
                break
        if not removed:
            print(f"ERROR: Device {label} not found in local config.")
            return False
        if self._remove_bridge_groups_device(label):
            self._mark_groups_dirty()
        return True

    def _delete_profiles_device(self, name: str) -> bool:
        entry = self._find_profiles_device_entry(name)
        if entry is None:
            if self._delete_bridge_config_device(name):
                self._warn(
                    f"WARNING: Device {name} not found in profiles; removed from local bridgeConfig devices."
                )
                return True
            print(f"ERROR: Device {name} not found in profiles.")
            return False
        payload = self._local_root_payload
        if not isinstance(payload, dict):
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return False
        profiles, profile_name = self._profiles_root_and_name()
        if profiles is None or profile_name is None:
            print(MESSAGE_ERR_DEVICE_PROFILE_REQUIRED)
            return False
        profile = profiles.get(profile_name)
        if not isinstance(profile, dict):
            print(MESSAGE_ERR_DEVICE_PROFILE_REQUIRED)
            return False
        category = self._find_entry_category(profile, entry)
        removed = False
        if category in (
            "neos",
            "neo550s",
            "flexes",
            "krakens",
            "falcons",
            "cancoders",
            "candles",
            "devices",
        ):
            devices = profile.get(category) or []
            if isinstance(devices, list):
                for idx, item in enumerate(list(devices)):
                    if item is entry:
                        del devices[idx]
                        removed = True
                        break
        elif category in ("pdh", "pdp", "pigeon", "roborio"):
            if profile.get(category) is entry:
                profile.pop(category, None)
                removed = True

        label = str(entry.get(KEY_LABEL, "")).strip()
        if label:
            labels = profile.get(KEY_PROFILE_DEVICES)
            if isinstance(labels, list) and label in labels:
                labels.remove(label)
                removed = True
            devices_registry = payload.get(KEY_DEVICES)
            if isinstance(devices_registry, list):
                for idx, item in enumerate(list(devices_registry)):
                    if not isinstance(item, dict):
                        continue
                    existing = str(item.get(KEY_LABEL, "")).strip()
                    if existing.lower() == label.lower():
                        del devices_registry[idx]
                        removed = True
                        break

        if not removed:
            print(f"ERROR: Device {name} not found in profiles.")
            return False
        self._profiles_dirty = True
        self._remove_diagram_device(entry)
        self._remove_bridge_groups_device(name)
        self._refresh_devices_from_profiles()
        return True

    def _delete_bridge_config_device(self, name: str) -> bool:
        if not self._local_config:
            return False
        devices = self._local_config.get("devices")
        if not isinstance(devices, list):
            return False
        label = name.strip()
        if not label:
            return False
        removed = False
        for idx, device in enumerate(list(devices)):
            if not isinstance(device, dict):
                continue
            dev_name = str(device.get("name", "")).strip()
            if dev_name.lower() == label.lower():
                del devices[idx]
                removed = True
                break
        if removed:
            self._local_config["devices"] = devices
            return True
        return False

    def _remove_bridge_groups_device(self, name: str) -> bool:
        config = self._local_config
        if not isinstance(config, dict):
            return False
        by_profile = config.get(KEY_BRIDGE_BY_PROFILE)
        if not isinstance(by_profile, dict):
            return False
        changed = False
        for entry in by_profile.values():
            if not isinstance(entry, dict):
                continue
            for group in entry.get(KEY_BRIDGE_GROUPS, []) or []:
                if not isinstance(group, dict):
                    continue
                members = group.get("members", []) or []
                if not isinstance(members, list):
                    continue
                to_remove = []
                for member in members:
                    if isinstance(member, dict):
                        dev_name = str(member.get(KEY_DEVICE, "")).strip()
                        if dev_name.lower() == name.strip().lower():
                            to_remove.append(member)
                    else:
                        dev_name = str(member).strip()
                        if dev_name.lower() == name.strip().lower():
                            to_remove.append(member)
                for member in to_remove:
                    members.remove(member)
                    changed = True
                if to_remove:
                    group["members"] = members
            selected = entry.get(KEY_BRIDGE_SELECTED_DEVICE)
            if isinstance(selected, dict):
                sel_name = str(selected.get(KEY_DEVICE, "")).strip()
                if sel_name.lower() == name.strip().lower():
                    entry.pop(KEY_BRIDGE_SELECTED_DEVICE, None)
                    changed = True
        if changed:
            self._local_config = config
        return changed

    def _remove_diagram_device(self, entry: Dict[str, object]) -> None:
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
        removed = False
        for node in list(nodes):
            if not isinstance(node, dict):
                continue
            if node.get("nodeType") != "device":
                continue
            if node.get("category") == category and node.get("id") == device_id:
                nodes.remove(node)
                removed = True
        if removed:
            diag_profile["nodes"] = nodes

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
            self._mark_groups_dirty()

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
        if field_key == FIELD_LABEL:
            print("ERROR: device label is managed by rename device.")
            return False
        if field_key not in DEVICE_FIELDS_PROFILE:
            print(MESSAGE_ERR_DEVICE_FIELD_UNKNOWN)
            return False
        store_key = FIELD_TYPE if field_key == FIELD_ROLE else field_key
        field_type = DEVICE_FIELD_TYPES.get(field_key, DEVICE_FIELD_STR)
        value: object
        if field_type == DEVICE_FIELD_INT:
            try:
                value = int(value_raw, 0)
            except ValueError:
                print(MESSAGE_ERR_DEVICE_FIELD_INT)
                return False
        elif field_type == DEVICE_FIELD_BOOL:
            parsed = self._parse_bool(value_raw)
            if parsed is None:
                print(MESSAGE_ERR_DEVICE_FIELD_BOOL)
                return False
            value = parsed
        elif field_type == DEVICE_FIELD_LIST:
            parsed = parse_json_arg(value_raw)
            if parsed is None or not isinstance(parsed, list):
                print(MESSAGE_ERR_DEVICE_FIELD_LIST)
                return False
            value = parsed
        elif field_type == DEVICE_FIELD_DICT:
            parsed = parse_json_arg(value_raw)
            if parsed is None or not isinstance(parsed, dict):
                print(MESSAGE_ERR_DEVICE_FIELD_DICT)
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
        target[store_key] = value
        if field_key == FIELD_INTERFACE and isinstance(target, dict):
            interface = str(target.get(KEY_INTERFACE, "")).strip()
            if interface and interface not in DEVICE_INTERFACE_ALLOWED:
                print(MESSAGE_ERR_DEVICE_INTERFACE_INVALID)
                return False
        if not self._local_devices_locked:
            self._mark_groups_dirty()
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
        if field_key == FIELD_LABEL:
            print("ERROR: device label is managed by rename device.")
            return False
        if field_key not in DEVICE_FIELDS_PROFILE:
            print(MESSAGE_ERR_DEVICE_FIELD_UNKNOWN)
            return False
        store_key = FIELD_TYPE if field_key == FIELD_ROLE else field_key
        devices = self._local_config.get("devices")
        if not isinstance(devices, list):
            print("ERROR: No local devices are defined.")
            return False
        for device in devices:
            if not isinstance(device, dict):
                continue
            dev_name = str(device.get("name", "")).strip()
            if dev_name.lower() == name.strip().lower():
                if store_key in device:
                    device.pop(store_key, None)
                    self._validate_device_entry(device)
                    if not self._local_devices_locked:
                        self._mark_groups_dirty()
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
        self._validate_device_entry(devices[-1])
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

    def _show_local_registry_device(self, name: str, json_output: bool, pretty: bool) -> bool:
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
            print(self._dump_json(payload, pretty))
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
            self._warn(MESSAGE_MAPPINGS_READ_FAIL.format(path=path))
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
        self._can_mappings_path = path
        self._can_mappings_dirty = False
        self._sync_store_mappings()
        return self._can_mappings

    def _parse_bool(self, value_raw: str) -> Optional[bool]:
        """
        NAME
            _parse_bool - Parse a boolean from CLI input.
        """

        value = value_raw.strip().lower()
        if value in BOOL_TRUE_VALUES:
            return True
        if value in BOOL_FALSE_VALUES:
            return False
        return None

    def _device_missing_fields(self, entry: Dict[str, object]) -> List[str]:
        """
        NAME
            _device_missing_fields - Return missing required fields for a device.
        """

        interface = str(entry.get(KEY_INTERFACE, "")).strip()
        if not interface:
            return [FIELD_INTERFACE]
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
        missing: List[str] = []
        for field in required:
            if field == FIELD_INTERFACE:
                continue
            if entry.get(field) is None:
                missing.append(field)
        return missing

    def _validate_device_entry(self, entry: Dict[str, object]) -> None:
        """
        NAME
            _validate_device_entry - Validate a device definition after edits.
        """

        interface = str(entry.get(KEY_INTERFACE, "")).strip()
        if interface and interface not in DEVICE_INTERFACE_ALLOWED:
            print(MESSAGE_ERR_DEVICE_INTERFACE_INVALID)
            return
        missing = self._device_missing_fields(entry)
        if missing:
            label = str(entry.get(KEY_LABEL, "")).strip() or str(entry.get(KEY_NAME, "")).strip()
            fields = ", ".join(missing)
            self._warn(MESSAGE_WARN_DEVICE_INCOMPLETE.format(label=label, fields=fields))

    def _dirty_state(self) -> Dict[str, bool]:
        """
        NAME
            _dirty_state - Return local dirty flags.
        """

        return self._current_dirty_flags()

    def _current_dirty_flags(self) -> Dict[str, bool]:
        """
        NAME
            _current_dirty_flags - Build current dirty flags map.
        """

        return {
            KEY_GROUPS: bool(self._groups_dirty),
            KEY_PROFILES: bool(self._profiles_dirty),
            KEY_TESTS: bool(self._tests_dirty),
            DIRTY_BINDINGS: bool(self._bindings_dirty),
            DIRTY_CAN_MAPPINGS: bool(self._can_mappings_dirty),
        }

    def _sync_store_from_local(self) -> None:
        """
        NAME
            _sync_store_from_local - Sync CLI state into the config store.
        """

        if self._local_root_payload is not None:
            payload = dict(self._local_root_payload)
            if isinstance(self._local_config, dict):
                payload[KEY_BRIDGE_CONFIG] = self._ordered_bridge_config(
                    self._local_config, include_devices=False
                )
            self._store.set_profiles_payload(payload)
        self._sync_store_tests()
        self._sync_store_bindings()
        self._sync_store_mappings()
        self._store.set_dirty_flags(self._current_dirty_flags())

    def _sync_store_tests(self) -> None:
        """
        NAME
            _sync_store_tests - Sync tests model into the store.
        """

        if self._tests_model is not None:
            self._store.set_tests_model(self._tests_model)

    def _sync_store_bindings(self) -> None:
        """
        NAME
            _sync_store_bindings - Sync bindings payload into the store.
        """

        if isinstance(self._bindings_payload, dict):
            self._store.set_bindings_payload(self._bindings_payload)

    def _sync_store_mappings(self) -> None:
        """
        NAME
            _sync_store_mappings - Sync CAN mappings payload into the store.
        """

        if isinstance(self._can_mappings, dict):
            self._store.set_mappings_payload(self._can_mappings)

    def _format_store_errors(self, issues: List[object]) -> str:
        """
        NAME
            _format_store_errors - Format store validation errors.
        """

        lines: List[str] = []
        for issue in issues:
            location = getattr(issue, "location", EMPTY_STRING)
            message = getattr(issue, "message", EMPTY_STRING)
            lines.append(MESSAGE_STORE_ISSUE.format(location=location, message=message))
        return SEP_NEWLINE.join(lines)

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
        self._groups_dirty = False
        self._sync_store_from_local()
        print(f"Wrote profiles to {path}.")
        return True

    def _ensure_profiles_device_entry(self, name: str) -> bool:
        """
        NAME
            _ensure_profiles_device_entry - Reject implicit registry creation.
        """
        label = name.strip()
        if not label:
            print(MESSAGE_ERR_DEVICE_LABEL_REQUIRED)
            return False
        payload = self._local_root_payload
        if not isinstance(payload, dict):
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return False
        profile_name = self._active_profile_name()
        if not profile_name:
            print(MESSAGE_ERR_DEVICE_PROFILE_REQUIRED)
            return False
        profiles = payload.get(KEY_PROFILES)
        if not isinstance(profiles, dict):
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return False
        profile = profiles.get(profile_name)
        if not isinstance(profile, dict):
            print(MESSAGE_ERR_PROFILE_UNKNOWN.format(name=profile_name))
            return False
        devices = payload.get(KEY_DEVICES)
        if not isinstance(devices, list):
            devices = []
            payload[KEY_DEVICES] = devices
        for entry in devices:
            if not isinstance(entry, dict):
                continue
            existing = str(entry.get(KEY_LABEL, "")).strip()
            if existing.lower() == label.lower():
                labels = profile.get(KEY_PROFILE_DEVICES)
                if not isinstance(labels, list):
                    labels = []
                    profile[KEY_PROFILE_DEVICES] = labels
                if existing and existing not in labels:
                    labels.append(existing)
                    self._profiles_dirty = True
                return True
        entry = {KEY_LABEL: label}
        devices.append(entry)
        labels = profile.get(KEY_PROFILE_DEVICES)
        if not isinstance(labels, list):
            labels = []
            profile[KEY_PROFILE_DEVICES] = labels
        if label not in labels:
            labels.append(label)
        self._profiles_dirty = True
        self._refresh_devices_from_profiles()
        self._validate_device_entry(entry)
        return True

    def _set_profiles_device_meta(self, name: str, field: str, value_raw: str) -> bool:
        """
        NAME
            _set_profiles_device_meta - Update a device entry inside profiles.
        """
        entry = self._find_profiles_device_entry(name)
        if entry is None:
            return self._ensure_profiles_device_entry(name)
        field_key = field.strip()
        if field_key == FIELD_LABEL:
            print("ERROR: device label is managed by rename device.")
            return False
        if field_key not in DEVICE_FIELDS_PROFILE:
            print(MESSAGE_ERR_DEVICE_FIELD_UNKNOWN)
            return False
        store_key = FIELD_TYPE if field_key == FIELD_ROLE else field_key
        field_type = DEVICE_FIELD_TYPES.get(field_key, DEVICE_FIELD_STR)
        if field_type == DEVICE_FIELD_INT:
            try:
                entry[store_key] = int(value_raw, 0)
            except ValueError:
                print(MESSAGE_ERR_DEVICE_FIELD_INT)
                return False
        elif field_type == DEVICE_FIELD_BOOL:
            parsed = self._parse_bool(value_raw)
            if parsed is None:
                print(MESSAGE_ERR_DEVICE_FIELD_BOOL)
                return False
            entry[store_key] = parsed
        elif field_type == DEVICE_FIELD_LIST:
            parsed = parse_json_arg(value_raw)
            if parsed is None or not isinstance(parsed, list):
                print(MESSAGE_ERR_DEVICE_FIELD_LIST)
                return False
            entry[store_key] = parsed
        elif field_type == DEVICE_FIELD_DICT:
            parsed = parse_json_arg(value_raw)
            if parsed is None or not isinstance(parsed, dict):
                print(MESSAGE_ERR_DEVICE_FIELD_DICT)
                return False
            entry[field_key] = parsed
        else:
            entry[store_key] = value_raw
        if field_key == FIELD_INTERFACE:
            interface = str(entry.get(KEY_INTERFACE, "")).strip()
            if interface and interface not in DEVICE_INTERFACE_ALLOWED:
                print(MESSAGE_ERR_DEVICE_INTERFACE_INVALID)
                return False
        self._profiles_dirty = True
        self._refresh_devices_from_profiles()
        self._validate_device_entry(entry)
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
        field_key = field.strip()
        if field_key == FIELD_LABEL:
            print("ERROR: device label is managed by rename device.")
            return False
        if field_key not in DEVICE_FIELDS_PROFILE:
            print(MESSAGE_ERR_DEVICE_FIELD_UNKNOWN)
            return False
        store_key = FIELD_TYPE if field_key == FIELD_ROLE else field_key
        entry.pop(store_key, None)
        self._profiles_dirty = True
        self._refresh_devices_from_profiles()
        self._validate_device_entry(entry)
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
        try:
            return list(lexer)
        except ValueError as exc:
            raise CliParseError(str(exc)) from exc

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
            self._groups_dirty = False
        if self._groups_profile is None and self._local_root_payload is None:
            self._groups_profile = DEFAULT_PROFILE_LOCAL
            self._local_profile_entry(self._groups_profile, create=True)

    def _mark_groups_dirty(self) -> None:
        """
        NAME
            _mark_groups_dirty - Mark local group config as dirty.
        """

        self._groups_dirty = True

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
        self._groups_dirty = False
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
        self._groups_dirty = False
        if self._local_devices_locked:
            print(f"Wrote groups config to {path}.")
        else:
            print(f"Wrote bridgeConfig to {path}.")
        return True
