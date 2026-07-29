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

import sys
from pathlib import Path
import argparse

KEY_DEVICE_COUNT = "deviceCount"
KEY_PRIMARY_LABEL = "primaryLabel"
KEY_ENABLED_MEMBER_COUNT = "enabledMemberCount"
KEY_HAS_MEMBERS = "hasMembers"
KEY_ALL_ENABLED_MEMBERS_PRESENT = "allEnabledMembersPresent"
KEY_LOCKED = "locked"
KEY_INVALID = "invalid"
KEY_SCOPE_ACTIVE = "scopeActive"
KEY_RUNTIME_PRESENT = "runtimePresent"
KEY_TESTABLE = "testable"

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import json
import hashlib
import shlex
import time
import re
import threading
import io
import contextlib
import shutil
from collections import deque
from copy import deepcopy
import copy
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from tools.can_nt.bridge_cmd_tracker import CommandTracker
from tools.can_nt.command_workflow_service import wait_for_command_event
from tools.can_nt.bridge_cli_parser import BridgeCliParser, CliParseError
from tools.can_nt.bridge_cli_ast import BridgeCliAstExecutor, AST_EXEC_SPEC
from tools.can_nt.bridge_cli_facades import (
    BridgeCliParseContext,
    BridgeCliExecuteFacade,
    BridgeCliOutputFacade,
    BridgeCliParseFacade,
    BridgeCliValidateFacade,
)
from tools.can_nt.bridge_robot_control_facade import BridgeRobotControlTransport
from tools.can_nt.bridge_cli_constants import CLI_PARSER_CONST
from tools.can_nt.bridge_cli_constants_gen import SPEC as PARSER_SPEC
from tools.can_nt.can_profiles import get_default_profile
from tools.common.profile_session import (
    SYNC_ACTION_ADOPT,
    SYNC_ACTION_MISSING_LOCAL,
    SYNC_ACTION_NONE,
    SYNC_ACTION_PROMPT,
    decide_host_profile_sync,
    normalize_profile_name,
)
from tools.can_nt.bridge_ops import (
    add_all_devices,
    add_next_motor,
    connect,
    disconnect,
    local_show_data,
    export_runtime_groups,
    BridgeCommand,
    ConfigPlan,
    validate_config_file,
    validate_config_file_all,
    validate_config_data,
    validate_config_data_all,
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
    show_profile,
    show_profiles,
    show_lifecycle_state,
    show_runtime_state,
    show_selected_device,
    show_status,
    show_sources,
    show_tests,
    show_version,
    active_add,
    active_next,
    active_show,
    ui_ping,
    parse_json_arg,
    profile_activate,
    select_profile,
    lifecycle_activate,
    lifecycle_deactivate,
    lifecycle_deactivate_active,
    runtime_activate,
    runtime_deactivate,
    profiles_reload,
    run_all_tests,
    run_test,
)
from tools.can_nt.bridge_session import BridgeEvent, BridgeSession
from tools.can_nt.motor_diag_constants import (
    CMD_DIAGNOSE,
    CMD_MOTOR,
    CAUSE_EXPLANATIONS,
    FMT_CAUSE_LINE,
    FMT_EVIDENCE_LINE,
    FMT_FINDING_LINE,
    FMT_MISSING_LINE,
    MSG_DEVICE_AMBIGUOUS,
    MSG_DEVICE_CANDIDATES,
    MSG_DEVICE_NOT_FOUND,
    MSG_DIAGNOSE_SYNTAX,
    MSG_DIAGNOSE_TARGET,
    MSG_RUNTIME_MISSING,
    MSG_RUNTIME_REQUIRED,
    OUT_FINDINGS,
    OUT_LIKELY_CAUSES,
    OUT_MISSING_FIELDS,
    SEP_COMMA_SPACE,
)
from tools.can_nt.motor_diag_normalize import collect_profile_labels, normalize_runtime_state
from tools.can_nt.motor_diag_rules import diagnose_motor
from tools.can_nt.host_ui_state_service import (
    RUNNABLE_SCOPE_KIND_MANUAL,
    HostActionAccessState,
    SCOPE_CONTROL_BLOCKED_WAITING_TEXT,
    resolve_active_group_edit_action_state,
    resolve_runnable_scope_state,
    resolve_scope_control_state,
)
from tools.can_nt.status import (
    StatusResult,
    format_status_message,
    SS__CLI_PARSER__UNKNOWN_COMMAND,
    SS__CLI_PARSER__INVALID_SYNTAX,
    SS__CLI_PARSER__MISSING_ARGUMENT,
    SS__CLI_PARSER__INVALID_FLAG,
    SS__CLI_VALIDATOR__INVALID_VALUE,
    SS__CLI_VALIDATOR__OUT_OF_RANGE,
    SS__CLI_VALIDATOR__REQUIRED,
    SS__CONFIG__INVALID,
    SS__CONFIG__NOT_LOADED,
    SS__CONFIG__PROFILE_REQUIRED,
    SS__CONFIG__SAVED,
    SS__CONFIG__VALID,
    SS__CONFIG__MERGED,
    SS__CONFIG__IMPORTED,
    SS__CONFIG__DUPLICATE_LABEL,
    SS__DEVICE__INVALID_FIELD,
    SS__DEVICE__NOT_DEFINED,
    SS__DEVICE__NOT_FOUND,
    SS__EXECUTOR__CANCELLED,
    SS__EXECUTOR__FAILED,
    SS__EXECUTOR__INTERNAL_ERROR,
    SS__EXECUTOR__NOT_SUPPORTED,
    SS__NORMAL,
    SS__GROUP__BINDING_INVALID,
    SS__GROUP__NOT_FOUND,
    SS__GROUP__MEMBER_MISSING,
    SS__INPUT_BINDING__INVALID,
    SS__INPUT_BINDING__NOT_FOUND,
    SS__NETWORK__CONNECT_FAILED,
    SS__NETWORK__COMMAND_SEND_FAILED,
    SS__NETWORK__HANDSHAKE_FAILED,
    SS__NETWORK__NOT_CONNECTED,
    SS__NETWORK__ROBOT_UNAVAILABLE,
)
from tools.config.schema_store import ConfigSchemaStore, LOCATION_BINDINGS, LOCATION_MAPPINGS
from tools.common.json_io import read_json, write_json
from tools.common.profile_io import compute_profiles_hash
from tools.common.paths import (
    repo_root,
    logs_dir,
    profiles_canonical_path,
    profiles_deploy_path,
    can_mappings_path,
    bindings_canonical_path,
    bindings_deploy_path,
    test_templates_dir,
)
from tools.common.config_api import (
    ConfigRepository,
    create_blank_profile,
    delete_profile as delete_profile_payload,
    ensure_profile_topology_entry,
    set_default_profile as set_default_profile_payload,
)
from tools.common.config_lifecycle import ConfigLifecycleService
from tools.common.workflows import Workflow01Service
from tools.common.tests_domain import collect_available_tests
from tools.common.diagnostics import normalize_device_attachments, summarize_attachment_metrics
from tools.common.topology_parse import (
    topology_edges,
    topology_nodes,
    topology_neighbor_links,
    topology_neighbor_ports,
    topology_node_lookup,
    topology_profile_from_payload,
)
from tools.common.group_contract import resolve_group_state_from_member_map
from tools.common.profile_constants import (
    BRIDGE_CONFIG_SCHEMA_VERSION,
    EDGE_TYPE_CAN_DROP,
    EDGE_TYPE_CAN_TAP,
    EDGE_TYPE_CAN_TRUNK,
    KEY_BRIDGE_BY_PROFILE,
    KEY_BRIDGE_CONFIG,
    KEY_BRIDGE_GENERATED_AT,
    KEY_BRIDGE_GROUPS,
    KEY_BRIDGE_SCHEMA_VERSION,
    KEY_BRIDGE_SELECTED_DEVICE,
    KEY_BRIDGE_TESTS,
    KEY_BRIDGE_BINDINGS,
    KEY_DATA_HASH,
    KEY_DATA_VERSION,
    KEY_DSL_DEFAULT_SET,
    KEY_DSL_TEST_SET,
    KEY_DSL_TEST_SETS,
    KEY_DSL_TESTS,
    KEY_DSL_TESTS_BY_NAME,
    KEY_DEFAULT_PROFILE,
    KEY_DEVICE_TYPE,
    KEY_DEVICES,
    KEY_ENABLED,
    KEY_ESTOPPED,
    KEY_MODE,
    KEY_GROUP_COUNT,
    KEY_MEMBER_COUNT,
    KEY_BINDING_COUNT,
    KEY_INPUT,
    KEY_KIND,
    KEY_VALUE,
    KEY_GENERATED_AT_MS,
    KEY_GROUPED,
    KEY_SOURCES,
    KEY_SOURCES_NAME,
    KEY_SOURCES_PATH,
    KEY_SOURCES_EXISTS,
    KEY_TESTS_ACTIVE_SET,
    KEY_TESTS_DEFAULT_SET,
    KEY_TESTS_USING_SETS,
    KEY_TESTS_TOTAL_COUNT,
    KEY_TESTS_ENABLED_COUNT,
    KEY_TESTS_ROWS,
    KEY_TESTS_INDEX,
    KEY_TESTS_NAME,
    KEY_TESTS_ENABLED,
    KEY_TESTS_SELECTED,
    KEY_TESTS_TYPE,
    KEY_TESTS_STATUS,
    KEY_TESTS_REQUIRED_DEVICES,
    KEY_VERSION,
    KEY_ID,
    KEY_INPUT_ALIASES,
    KEY_INTERFACE,
    KEY_INVERT,
    KEY_LABEL,
    KEY_LIMITS,
    KEY_MANUFACTURER,
    KEY_MODEL,
    KEY_NODE_CLASS,
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
    INTERFACE_USB,
    KEY_ATTACHMENTS,
    KEY_BUS,
    KEY_TERMINATOR,
    KEY_TYPE,
    KEY_VENDOR,
    KEY_ROLE,
    KEY_TAGS,
    KEY_DIAGRAM,
    KEY_NEIGHBOR_LINKS,
    KEY_NEIGHBOR_PORTS,
    KEY_LINK_A,
    KEY_LINK_B,
    KEY_LINK_NODE,
    KEY_LINK_PORT,
    KEY_LINK_NEIGHBOR,
    KEY_LINK_NEIGHBOR_PORT,
    KEY_NODE_KEY,
    KEY_NODE_TYPE,
    KEY_OBJECT_TYPE,
    KEY_DEVICE_REF,
    KEY_LAYOUT,
    KEY_EDGE_TYPE,
    KEY_EDGE_ID,
    KEY_TOPOLOGY_VIEW,
    KEY_TOPOLOGY,
    KEY_TOPOLOGY_PROFILES,
    KEY_TOPOLOGY_VERSION,
    KEY_TOPOLOGY_SOURCE,
    KEY_TOPOLOGY_NODES,
    KEY_TOPOLOGY_EDGES,
    KEY_ETHERNET_LINKS,
    KEY_DEVICE_LINKS,
    KEY_FROM_NODE,
    KEY_FROM_PORT,
    KEY_TO_NODE,
    KEY_TO_PORT,
    NEIGHBOR_PORT_LEFT,
    NEIGHBOR_PORT_RIGHT,
    NODE_TYPE_DEVICE,
    NODE_TYPE_JUNCTION,
    KEY_LINK_DEVICE,
    get_device_interface,
    get_group_member_label,
    get_node_class,
    get_object_type,
    make_group_member,
)
from tools.can_topology.validate_profiles import Reporter, validate_profiles
from tools.common.robot_test_dsl import (
    create_blank_test_in_root_payload as robot_test_dsl_create_blank_test_in_root_payload,
    copy_external_library_test_into_root_payload as robot_test_dsl_copy_external_library_test_into_root_payload,
    copy_test_into_root_payload as robot_test_dsl_copy_test_into_root_payload,
    DEFAULT_TEST_SET as DSL_DEFAULT_TEST_SET,
    delete_external_library_test as robot_test_dsl_delete_external_library_test,
    delete_test_from_root_payload as robot_test_dsl_delete_test_from_root_payload,
    RobotTestDslEntry,
    RobotTestDslStore,
    ValidationResult,
    cleanup_stale_tests_in_store as robot_test_dsl_cleanup_stale_tests_in_store,
    device_catalog as robot_test_dsl_device_catalog,
    import_test_into_config_library as robot_test_dsl_import_test_into_config_library,
    import_test_into_external_library as robot_test_dsl_import_test_into_external_library,
    import_test_into_root_payload as robot_test_dsl_import_test_into_root_payload,
    issue_detail as robot_test_dsl_issue_detail,
    list_external_library_test_names as robot_test_dsl_list_external_library_test_names,
    rename_external_library_test as robot_test_dsl_rename_external_library_test,
    rename_test_in_root_payload as robot_test_dsl_rename_test_in_root_payload,
    render_validation_text as robot_test_dsl_render_validation_text,
    resolve_global_library_test_names as robot_test_dsl_resolve_global_library_test_names,
    resolve_profile_test_names as robot_test_dsl_resolve_profile_test_names,
    resolve_profile_test_set_name as robot_test_dsl_resolve_profile_test_set_name,
    signal_catalog as robot_test_dsl_signal_catalog,
    store_from_root_payload as robot_test_dsl_store_from_root_payload,
    store_to_payload as robot_test_dsl_store_to_payload,
    validate_store_for_profile as robot_test_dsl_validate_store_for_profile,
    write_store_to_root_payload as robot_test_dsl_write_store_to_root_payload,
)
from tools.common.test_authoring import (
    BUILTIN_TIMER_NAME,
    CONDITION_OPERATOR_EQ,
    CONDITION_OPERATOR_GT,
    CONDITION_OPERATOR_GTE,
    CONDITION_OPERATOR_LT,
    CONDITION_OPERATOR_LTE,
    CONDITION_OPERATOR_NE,
    DEVICE_ROLE_OBSERVER,
    DEVICE_ROLE_PRIMARY,
    PSEUDO_DEVICE_TYPE_TEST_TIMER,
    TestCommandModel,
    TestConditionModel,
    TestAuthoringModel,
    TestBindingButton,
    TestBindingJoystick,
    DeviceActionModel,
    TestModel,
    TestPseudoDeviceModel,
    TestSetModel,
    TerminationModel,
    model_from_payload,
    model_to_payload,
    validate_model,
    validate_test_name,
)
from tools.common.test_authoring.device_catalog import load_controller_names, load_profile_devices
from tools.common.time_utils import timestamp_version
from tools.common.app_versions import (
    APP_BRIDGE_CLI_NAME,
    APP_VERSION_ORDER,
    VERSIONS,
    VERSION_HEADER,
    format_version_line,
)
from tools.common.build_info import (
    KEY_BUILD,
    build_info_payload,
    build_lines,
)

# Optional line editing for Cisco-style '?' prefill.
MESSAGE_WARN_PROMPT_TOOLKIT = (
    "WARNING: prompt_toolkit not installed; '?' help cannot prefill the line buffer."
)
MESSAGE_WARN_HISTORY_DISABLED = (
    "WARNING: command history disabled (prompt_toolkit not available)."
)
MESSAGE_WARN_PROMPT_TOOLKIT_NO_CONSOLE = (
    "WARNING: prompt_toolkit unavailable (no console); falling back to basic input."
)
MESSAGE_WARN_COMPLETION_DISABLED = (
    "WARNING: prompt_toolkit completion unavailable; continuing without tab completion."
)
PROMPT_TOOLKIT_AVAILABLE = False
COMPLETION_ENABLED = True
COMPLETION_WHILE_TYPING = True
COMPLETION_META_TEXT = ""
COMPLETION_PREFIX_EMPTY = ""
COMPLETION_SPACE = " "
COMPLETION_START_POS_ZERO = 0
KEEPALIVE_INTERVAL_SEC = 1.0
KEEPALIVE_SLEEP_SEC = 0.1
KEEPALIVE_DISCONNECTED_WAIT_SEC = 0.5
KEEPALIVE_JOIN_TIMEOUT_SEC = 1.0
ROBOT_COMMAND_TIMEOUT_SEC = 3.5
ROBOT_LONG_COMMAND_TIMEOUT_SEC = 20.0
CONNECT_PROFILE_SYNC_TIMEOUT_SEC = 1.0
CONNECT_PROFILE_SYNC_SLEEP_SEC = 0.05
PROFILE_EXPORT_TEST_RUN_WAIT_SEC = 2.0
TEST_WAIT_DEFAULT_TIMEOUT_SEC = 10.0
TEST_WAIT_RUN_ALL_DEFAULT_TIMEOUT_SEC = 120.0
TEST_WAIT_POLL_SEC = 0.1
TEST_WAIT_RUN_ALL_SETTLE_POLLS = 3
TEST_WAIT_PROGRESS_PERIOD_SEC = 1.0
SLEEP_MIN_SEC = 0.0
SLEEP_MAX_SEC = 3600.0
SLEEP_ARG_COUNT = 2
KEEPALIVE_LAST_INIT = 0.0
KEEPALIVE_THREAD_NAME = "BridgeCliKeepalive"
CMD_UI_PING = "uiPing"
EVENT_TYPE_ACK = "ack"
EVENT_TYPE_OUT = "out"
MESSAGE_KEEPALIVE_THREAD_START = "KEEPALIVE: thread started."
MESSAGE_KEEPALIVE_THREAD_STOP = "KEEPALIVE: thread stopped."
MESSAGE_KEEPALIVE_STATE_CONNECTED = "KEEPALIVE: session connected."
MESSAGE_KEEPALIVE_STATE_DISCONNECTED = "KEEPALIVE: session disconnected."
MESSAGE_KEEPALIVE_SEND_FAIL = "KEEPALIVE: uiPing send failed."
MESSAGE_WAITING_FOR_OUT = "WARNING: Timeout waiting for OUT."
MESSAGE_DEBUG_REGISTRY_PUSH = (
    "DEBUG: registry push path={path} bytes={bytes} sha256={sha256} data_hash={data_hash}"
)
PROTO_TIME_ZERO = 0.0
PROTO_LAST_SEQ_INIT = 0
PROTO_EMPTY_ID = ""
PROTO_KEY_TCP = "tcp"
PROTO_KEY_NT = "nt"
PROTO_KEY_UI = "ui"
PROTO_KEY_KEEPALIVE = "keepalive"
PROTO_KEY_COMMANDS = "commands"
PROTO_KEY_ACKS = "acks"
PROTO_KEY_OUTS = "outs"
PROTO_KEY_TIMEOUTS = "timeouts"
PROTO_KEY_PROTOCOL = "protocol"
PROTO_KEY_CONNECTED = "connected"
PROTO_KEY_CONNECT_ATTEMPTS = "connectAttempts"
PROTO_KEY_CONNECT_FAILS = "connectFailures"
PROTO_KEY_CONNECT_SUCCESSES = "connectSuccesses"
PROTO_KEY_LAST_CONNECT_AT = "lastConnectAt"
PROTO_KEY_LAST_DISCONNECT_AT = "lastDisconnectAt"
PROTO_KEY_HANDSHAKES = "handshakes"
PROTO_KEY_LAST_HANDSHAKE_AT = "lastHandshakeAt"
PROTO_KEY_SESSION_ID = "sessionId"
PROTO_KEY_COMMANDS_SENT = "sent"
PROTO_KEY_COMMANDS_LAST = "last"
PROTO_KEY_COMMANDS_LAST_AT = "lastAt"
PROTO_KEY_LAST_SEQ = "lastSeq"
PROTO_KEY_ACK_COUNT = "count"
PROTO_KEY_OUT_COUNT = "count"
PROTO_KEY_LAST_ACK_AT = "lastAckAt"
PROTO_KEY_LAST_OUT_AT = "lastOutAt"
PROTO_KEY_KEEPALIVE_SENT = "sent"
PROTO_KEY_KEEPALIVE_FAILED = "failed"
PROTO_KEY_KEEPALIVE_ACKED = "acked"
PROTO_KEY_KEEPALIVE_OUT = "out"
PROTO_KEY_KEEPALIVE_LAST_SENT_AT = "lastSentAt"
PROTO_KEY_KEEPALIVE_LAST_ACK_AT = "lastAckAt"
PROTO_KEY_KEEPALIVE_LAST_OUT_AT = "lastOutAt"
PROTO_KEY_TIMEOUT_COUNT = "count"
PROTO_KEY_LAST_TIMEOUT_AT = "lastTimeoutAt"
NT_STATE_ENABLED = "enabled"
NT_STATE_ESTOPPED = "estopped"
NT_STATE_MODE = "mode"
NT_STATE_LAST_ACK_MS = "lastAckMs"
NT_STATE_SESSION_ID = "sessionId"
CMD_SHOW_STATUS = "showStatus"
CMD_SHOW_GROUPS = "showGroups"
CMD_SHOW_GROUP = "showGroup"
CMD_SHOW_DEVICES = "showDevices"
CMD_SHOW_DEVICE = "showDevice"
CMD_SHOW_BINDINGS = "showBindings"
CMD_SHOW_SELECTED_DEVICE = "showSelectedDevice"
CMD_SHOW_RUNTIME_STATE = "showRuntimeState"
CMD_SHOW_VERSION = "showVersion"
CMD_SHOW_TESTS = "showTests"
CMD_SHOW_SOURCES = "showSources"
CMD_SHOW_PROFILES = "showProfiles"
CMD_SHOW_PROFILE = "showProfile"

try:
    from prompt_toolkit import prompt as prompt_toolkit_prompt
    from prompt_toolkit import PromptSession
    from prompt_toolkit.application import Application
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.layout import HSplit, Layout, VSplit, Window
    from prompt_toolkit.layout.controls import FormattedTextControl
    from prompt_toolkit.layout.dimension import Dimension
    from prompt_toolkit.widgets import Frame, TextArea
    PROMPT_TOOLKIT_AVAILABLE = True
except Exception:
    prompt_toolkit_prompt = None
    PromptSession = None
    Application = None
    Completer = None
    Completion = None
    FileHistory = None
    KeyBindings = None
    HSplit = None
    Layout = None
    VSplit = None
    Window = None
    FormattedTextControl = None
    Dimension = None
    Frame = None
    TextArea = None

# Parser selection (comment out one of the two lines below).
CLI_PARSER_KIND = CLI_PARSER_CONST["ebnf"]

MODE_CONFIG = "config"
MODE_TEST = "test"
MODE_GROUP = "group"
MODE_DEVICE = "device"
MODE_EXEC = "exec"

TESTS_FILENAME = "bringup_tests.json"
TESTS_MULTISET_MIN_COUNT = 1
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
COUNT_THOUSAND = 1000
COUNT_TEN = 10
COUNT_TWELVE = 12
COUNT_FIFTEEN = 15
STATUS_INCLUDE_RAW_DEFAULT = False
STATUS_DETAIL_PREFIX = "DETAIL: "
STATUS_OK_MESSAGE = "OK"
EXIT_CODE_ERROR = 2
VERSION_TITLE = VERSION_HEADER
VERSION_KEY_APPS = "apps"
VERSION_KEY_NAME = "name"
VERSION_KEY_VERSION = "version"
MESSAGE_VERSION_NONE = "  (none)"
VERSION_APP_NAME = APP_BRIDGE_CLI_NAME
BUILD_TITLE = "Build"

CMD_SHOW = "show"
CMD_LS = "ls"
CMD_CONNECT = "connect"
CMD_DISCONNECT = "disconnect"
CMD_WRITE = "write"
CMD_SAVE_TESTS = "save-tests"
CMD_TEST = "test"
CMD_TESTS = "tests"
CMD_CREATE = "create"
CMD_NEW = "new"
CMD_IMPORT = "import"
CMD_LIBRARY = "library"
CMD_CLEANUP = "cleanup"
CMD_STALE = "stale"
CMD_EXPORT = "export"
CMD_DELETE = "delete"
CMD_SET = "set"
CMD_CLEAR = "clear"
CMD_SELECT = "select"
CMD_RUN_ALL = "run-all"
SHOW_TARGET_VERSION = "version"
CMD_DEFAULT = PARSER_SPEC.cmd_default
CMD_ON = PARSER_SPEC.cmd_on
CMD_OFF = PARSER_SPEC.cmd_off
CMD_MESSAGES = "messages"
CMD_SLEEP = "sleep"
CMD_WAIT = "wait"
CMD_MESSAGE_LEVEL = "message-level"
CMD_TYPE = "type"
CMD_DEVICE = "device"
CMD_DEVICES = "devices"
CMD_REGISTRY = "registry"
CMD_GROUP = "group"
CMD_CONFIG = "config"
CMD_LOCAL_RAW = "local-raw"
CMD_DIRTY = "dirty"
CMD_PROFILES = "profiles"
CMD_RUNTIME = "runtime"
CMD_PROFILE = "profile"
CMD_PROF = "prof"
CMD_CONFIGURE = "configure"
CMD_TERMINAL = "terminal"
CMD_CFG = "cfg"
CMD_ACTION = "action"
CMD_COLOR = "color"
CMD_PATTERN = "pattern"
CMD_BRIGHTNESS = "brightness"
CMD_DURATION = "duration"
CMD_ADD = "add"
CMD_ASSIGN = "assign"
CMD_NEXT = "next"
CMD_INSTANTIATE = "instantiate"
CMD_RESET = "reset"
CMD_ZERO_CONFIG = "zero-config"
CMD_ACTIVE_SHORT = "active"
CMD_ACTIVE_SHOW_SHORT = "show"
CMD_ACTIVE_ADD_SHORT = "add"
CMD_ACTIVE_NEXT_SHORT = "next"
GROUP_NAME_ACTIVE = CMD_ACTIVE_SHORT
CMD_TOGGLE = PARSER_SPEC.cmd_toggle
CMD_RUN = PARSER_SPEC.cmd_run
CMD_NO = "no"
CMD_REMOVE = "remove"
CMD_MEMBER = "member"
CMD_RENAME = "rename"
CMD_VALIDATE = "validate"
CMD_VAL = "val"
CMD_INPUT_SOURCE = "inputsource"
CMD_COMMAND = "command"
CMD_DEADBAND = "deadband"
CMD_DUTY = "duty"
CMD_TERMINATION = "termination"
CMD_ROTATION = "rotation"
CMD_TIME = "time"
CMD_HOLD = "hold"
CMD_LIMITSWITCH = "limitswitch"
CMD_UNTIL = "until"
CMD_EXPECT = "expect"
CMD_SUCCESS = "success"
CMD_ABORT = "abort"
CMD_PASSIVE = "passive"
CMD_MANUAL_STOP = "manual_stop"
CMD_ROLE = "role"
CMD_DEADBAND_SWEEP = "deadbandsweep"
CMD_ENABLED = "enabled"
CMD_ENABLE = "enable"
CMD_DISABLE = "disable"
CMD_EXIT = "exit"
CMD_END = "end"
CMD_QUIT = "quit"
CMD_BINDINGS = "bindings"
CMD_CONTROLLER = "controller"
CMD_BINDING = "binding"
CMD_BIND = PARSER_SPEC.cmd_bind
CMD_EXPLAIN = "explain"
CMD_AXIS = "axis"
CMD_CAN_MAPPINGS = "can-mappings"
CMD_MANUFACTURER = "manufacturer"
CMD_DEVICE_TYPE_NAME = "device-type"
CMD_DEVICE_TYPES = "device-types"
TARGET_KIND_GROUP = "group"
TARGET_KIND_DEVICE = "device"
TARGET_KIND_TEST = "test"
CMD_COPY = "copy"
WARN_DUPLICATE_MEMBER = "WARNING: label already in group: {device}"
WARN_MISSING_MEMBER = "WARNING: label not in group: {device}"
WARN_LOCAL_GROUP_CLEARED = "WARNING: Robot not connected; local group cleared."
ERR_RESERVED_ACTIVE_DELETE = "ERROR: group \"active\" cannot be deleted."
ERR_RESERVED_ACTIVE_RENAME = "ERROR: group \"active\" cannot be renamed."
ERR_ACTIVE_GROUP_MEMBERSHIP_ONLY = "ERROR: active group supports membership operations only."
ERR_GROUP_REFERENCED_BY_TEST = "ERROR: group \"{name}\" referenced by test {test}."
ERR_DEVICE_REFERENCED = "ERROR: device \"{name}\" referenced by {kind} {ref}."
ERR_NAME_EXISTS = "ERROR: name \"{name}\" already exists."
ERR_NAME_RESERVED = "ERROR: name \"{name}\" is reserved."
ERR_GROUP_NOT_FOUND_FMT = "ERROR: group \"{name}\" not found."
ERR_DEVICE_NOT_FOUND_FMT = "ERROR: device \"{name}\" not found."
ERR_SOURCE_DEST_SAME = "ERROR: source and destination are the same."
ERR_COPY_NON_INTERACTIVE = "ERROR: non-interactive copy to existing group requires failure by policy."
ERR_NO_DEVICES_AVAILABLE_INSTANTIATE = "ERROR: no device available for instantiate next motor."
ERR_NO_DEVICES_AVAILABLE_MEMBER_ASSIGN = "ERROR: no device available for member assign next."
MESSAGE_ERR_MEMBER_ACTION = "ERROR: member requires assign/remove/enable/disable/toggle."
MESSAGE_ERR_INSTANTIATE_USAGE = (
    "ERROR: instantiate requires `instantiate next motor` or `instantiate all devices`."
)
ERR_GROUP_NAME_REQUIRED = "ERROR: group name required."
CMD_DEVICE_USAGE = "device-usage"
CMD_SHOW_ALL = "show-all"
CMD_WORKSPACE = "workspace"
CMD_SESSION = "session"
CMD_CONTROLLERS = "controllers"
ALIAS_REPLACEMENTS = {
    CMD_LS: CMD_SHOW,
    CMD_CFG: f"{CMD_CONFIGURE} {CMD_TERMINAL}",
    CMD_PROF: CMD_PROFILE,
    CMD_VAL: CMD_VALIDATE,
    f"{CMD_SHOW} {CMD_SESSION}": f"{CMD_SHOW} {CMD_WORKSPACE}",
    f"{CMD_BINDINGS} {CMD_LS}": f"{CMD_BINDINGS} {CMD_SHOW}",
    f"{CMD_CAN_MAPPINGS} {CMD_LS}": f"{CMD_CAN_MAPPINGS} {CMD_SHOW}",
}
MESSAGE_ERR_ALIAS_REMOVED = "ERROR: Command '{alias}' was removed. Use '{canonical}'."
CMD_ROBOT = "robot"
CMD_LOCAL = "local"
CMD_PUSH = "push"
CMD_INIT = PARSER_SPEC.cmd_init
CMD_ACTIVATE = PARSER_SPEC.cmd_activate
CMD_ACTIVATE_PROFILE = PARSER_SPEC.cmd_activate_profile
CMD_PROFILES_RELOAD = "profilesReload"
CMD_RUNTIME_ACTIVATE = "runtimeActivate"
CMD_RUNTIME_DEACTIVATE = "runtimeDeactivate"
CMD_LIFECYCLE_ACTIVATE = "lifecycleActivate"
CMD_LIFECYCLE_DEACTIVATE = "lifecycleDeactivate"
CMD_LIFECYCLE_DEACTIVATE_ACTIVE = "lifecycleDeactivateActive"
CMD_SHOW_LIFECYCLE_STATE = "showLifecycleState"
CMD_SAVE_BRIDGE_CONFIG = "bridge-config"
CMD_SAVE_RUNTIME_GROUPS = "runtime-groups"
CMD_VALIDATE_ALL = PARSER_SPEC.cmd_validate_all
CMD_ACTIVE = "--active"
CMD_ACTIVE_SET = "--active-set"
FLAG_RUN = "--run"
FLAG_TIMEOUT = "--timeout"
FLAG_WAIT = "--wait"
CMD_ALL = "all"
CMD_SCRIPT = "script"
CMD_PROMPT = "--prompt"
CMD_LOAD = "load"
CMD_RELOAD = PARSER_SPEC.cmd_reload
CMD_SAVE = "save"
CMD_SOURCES = "sources"
CMD_MERGE = "merge"
CMD_TEMPLATES = "templates"
CMD_TEMPLATE = "template"
CMD_INFO = "info"
CMD_DEBUG = "debug"
CMD_GRAMMAR = "grammar"
CMD_RECOVER = "recover"
CMD_LAST_GOOD = "last-good"
CMD_FROM = "from"
CMD_LIST = "list"
CMD_FILE = "file"
FLAG_JSON = "--json"
FLAG_DOT = "--dot"
FLAG_FORCE = "--force"
FLAG_INSTALL_ROBOT = "--install-robot"
FLAG_REPAIR = "--repair"
FLAG_VERBOSE = "--verbose"
FLAG_GROUPED = "--grouped"
TOKEN_EQUALS = "="
BOOLEAN_TRUE = "true"
BOOLEAN_FALSE = "false"
DSL_ALLOWED_OPERATORS = {
    CONDITION_OPERATOR_GT,
    CONDITION_OPERATOR_GTE,
    CONDITION_OPERATOR_LT,
    CONDITION_OPERATOR_LTE,
    CONDITION_OPERATOR_EQ,
    CONDITION_OPERATOR_NE,
}
FLAG_YES = "--yes"
FLAG_CLEAR_MEMORY = "--clear-memory"
QUESTION_MARK = "?"
SUGGESTION_SEPARATOR = " | "
TOPOLOGY_LABEL_ROBORIO = "roborio"
TOPOLOGY_LABEL_INJECT = "inject"
MESSAGE_NEXT_ARGS_PREFIX = "Next args: "
MESSAGE_NEXT_ARGS_NONE = "Next args: (none)"
HELP_INDENT = "  "
PLACEHOLDER_NAME = "<name>"
PLACEHOLDER_PROFILE = "<profile>"
PLACEHOLDER_DEVICE = "<device>"
PLACEHOLDER_GROUP = "<group>"
PLACEHOLDER_TEST = "<test>"
PLACEHOLDER_INPUT = "<input>"
PLACEHOLDER_FIELD = "<field>"
PLACEHOLDER_BINDING = "<binding>"
PLACEHOLDER_TEMPLATE = "<template>"
PLACEHOLDER_PATH = "<path>"
PLACEHOLDER_REGISTRY = "<devices-table>"
FLAG_JSON = "--json"
FLAG_PRETTY = "--pretty"
JSON_PRETTY_INDENT = 2
MESSAGE_EMPTY_PROMPT = ""
HISTORY_FILENAME = "bridge_cli_history.txt"
ENCODING_UTF8 = "utf-8"
FILE_MODE_WRITE = "w"
FILE_MODE_READ = "r"
BACKUP_DIR_PARENT = "backup_data"
BACKUP_DIR_NAME = "backups"
BACKUP_INDEX_NAME = "index.json"
BACKUP_SUFFIX_TMP = ".tmp"
BACKUP_SUFFIX_BAK = ".bak"
SNAPSHOT_SEPARATOR = "_"
SNAPSHOT_LAST_GOOD = "last_good"
SNAPSHOT_RETAIN_COUNT = 10
SNAPSHOT_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"
SNAPSHOT_DOT = "."
SNAPSHOT_GLOB_WILDCARD = "*"
HASH_ALGO_SHA256 = "sha256"
PROFILE_EXPORT_JSON_SUFFIX = ".json"
PROFILE_EXPORT_SCRIPT_SUFFIX = ".cli"
PROFILE_EXPORT_JSON_FMT = "{profile}_profile.json"
PROFILE_EXPORT_SCRIPT_FMT = "{profile}_profile.cli"
PROFILE_EXPORT_SCRIPT_HEADER = "# bridge_cli profile export"
PROFILE_EXPORT_SCRIPT_HEADER_ALL = "# bridge_cli profiles export"
PROFILES_EXPORT_JSON_NAME = "profiles_export.json"
PROFILES_EXPORT_SCRIPT_NAME = "profiles_export.cli"
PROFILE_EXPORT_HEADER_PREFIX = "#"
PROFILE_EXPORT_HEADER_ECHO = "echo on"
PROFILE_EXPORT_HEADER_INIT = "# profiles init"
PROFILE_EXPORT_HEADER_SAVE_NEW = "# save config <path>"
PROFILE_EXPORT_HEADER_INSTALL_ROBOT = "# robot install and verification"
PROFILE_EXPORT_CMD_MERGE = "merge"
PROFILE_EXPORT_CMD_CONFIG = "config"
PROFILE_EXPORT_CMD_PROFILE = "profile"
PROFILE_EXPORT_CMD_PROFILES = "profiles"
PROFILE_EXPORT_CMD_CREATE = "create"
PROFILE_EXPORT_CMD_DEFAULT = "default"
PROFILE_EXPORT_CMD_DELETE = "delete"
PROFILE_EXPORT_CMD_EXIT = "exit"
PROFILE_EXPORT_CMD_CONFIGURE = "configure"
PROFILE_EXPORT_CMD_TERMINAL = "terminal"
PROFILE_EXPORT_CMD_DEVICE = "device"
PROFILE_EXPORT_CMD_SET = "set"
PROFILE_EXPORT_CMD_GROUP = "group"
PROFILE_EXPORT_CMD_ADD = "add"
PROFILE_EXPORT_CMD_MEMBER = "member"
PROFILE_EXPORT_CMD_ASSIGN = "assign"
PROFILE_EXPORT_CMD_DISABLE = "disable"
PROFILE_EXPORT_CMD_BIND = "bind"
PROFILE_EXPORT_CMD_SELECTED_DEVICE = "selected-device"
PROFILE_EXPORT_CMD_SELECTED_MODE = "selected-mode"
PROFILE_EXPORT_CMD_TEST = "test"
PROFILE_EXPORT_CMD_TESTS = "tests"
PROFILE_EXPORT_CMD_SHOW = "show"
PROFILE_EXPORT_CMD_TEST_CREATE = "create"
PROFILE_EXPORT_CMD_TEST_SET = "set"
PROFILE_EXPORT_CMD_TYPE = "type"
PROFILE_EXPORT_CMD_INPUTSOURCE = "inputsource"
PROFILE_EXPORT_CMD_DEADBAND = "deadband"
PROFILE_EXPORT_CMD_DUTY = "duty"
PROFILE_EXPORT_CMD_ACTION = "action"
PROFILE_EXPORT_CMD_COLOR = "color"
PROFILE_EXPORT_CMD_PATTERN = "pattern"
PROFILE_EXPORT_CMD_BRIGHTNESS = "brightness"
PROFILE_EXPORT_CMD_DURATION = "duration"
PROFILE_EXPORT_CMD_ROTATION = "rotation"
PROFILE_EXPORT_CMD_TIME = "time"
PROFILE_EXPORT_CMD_HOLD = "hold"
PROFILE_EXPORT_CMD_LIMITSWITCH = "limitswitch"
PROFILE_EXPORT_CMD_DEADBAND_SWEEP = "deadbandsweep"
PROFILE_EXPORT_CMD_ENABLED = "enabled"
PROFILE_EXPORT_CMD_TERMINATION = "termination"
PROFILE_EXPORT_CMD_ON = "on"
PROFILE_EXPORT_CMD_OFF = "off"
PROFILE_EXPORT_CMD_ENABLE = "enable"
PROFILE_EXPORT_CMD_TOGGLE = "toggle"
PROFILE_EXPORT_CMD_NO = "no"
PROFILE_EXPORT_CMD_DEVICE_ADD = "add"
PROFILE_EXPORT_CMD_DEVICE_NO = "no"
PROFILE_EXPORT_CMD_DEVICE_SUB = "device"
PROFILE_EXPORT_CMD_MEMBER_DISABLE = "disable"
PROFILE_EXPORT_CMD_MEMBER_ENABLE = "enable"
PROFILE_EXPORT_CMD_MEMBER_TOGGLE = "toggle"
PROFILE_EXPORT_CMD_BIND_ANALOG = "analog"
PROFILE_EXPORT_CMD_BIND_HOLD = "hold"
PROFILE_EXPORT_CMD_BIND_TOGGLE = "toggle"
PROFILE_EXPORT_CMD_BIND_JOG_FORWARD = "jog-forward"
PROFILE_EXPORT_CMD_BIND_JOG_REVERSE = "jog-reverse"
PROFILE_EXPORT_BOOL_TRUE = "true"
PROFILE_EXPORT_BOOL_FALSE = "false"
PROFILE_EXPORT_ROTATION_LIMIT = "limit"
PROFILE_EXPORT_ROTATION_ENCODER_KEY = "encoderKey"
PROFILE_EXPORT_ROTATION_ENCODER_SOURCE = "encoderSource"
PROFILE_EXPORT_ROTATION_ENCODER_MOTOR_INDEX = "encoderMotorIndex"
PROFILE_EXPORT_ROTATION_ENCODER_COUNTS_PER_REV = "encoderCountsPerRev"
PROFILE_EXPORT_TIME_TIMEOUT = "timeout"
PROFILE_EXPORT_TIME_ON_TIMEOUT = "onTimeout"
PROFILE_EXPORT_HOLD_ON_RELEASE = "onRelease"
PROFILE_EXPORT_LIMITSWITCH_ON_HIT = "onHit"
PROFILE_EXPORT_LIMITSWITCH_ID = "id"
PROFILE_EXPORT_SWEEP_START_DUTY = "startDuty"
PROFILE_EXPORT_SWEEP_MAX_DUTY = "maxDuty"
PROFILE_EXPORT_SWEEP_STEP_DUTY = "stepDuty"
PROFILE_EXPORT_SWEEP_STEP_HOLD_SEC = "stepHoldSec"
PROFILE_EXPORT_SWEEP_MOTION_THRESHOLD_ROT = "motionThresholdRot"
PROFILE_EXPORT_SWEEP_REQUIRED_SAMPLES = "requiredSamples"
PROFILE_EXPORT_SWEEP_ENCODER_KEY = "encoderKey"
PROFILE_EXPORT_SWEEP_ENCODER_SOURCE = "encoderSource"
PROFILE_EXPORT_SWEEP_ENCODER_MOTOR_INDEX = "encoderMotorIndex"
PROFILE_EXPORT_SWEEP_ENCODER_COUNTS_PER_REV = "encoderCountsPerRev"
PROFILE_EXPORT_NEWLINE = "\n"
PROFILE_EXPORT_QUOTE = "\""
PROFILE_EXPORT_INDENT = 2
PROFILE_EXPORT_PATH_SEPARATOR = " "
CONTROL_SIGNAL_SEPARATOR = "."
PROFILE_EXPORT_JSON_SEP_COMMA = ","
PROFILE_EXPORT_JSON_SEP_COLON = ":"
PROFILE_EXPORT_JSON_SEPARATORS = (PROFILE_EXPORT_JSON_SEP_COMMA, PROFILE_EXPORT_JSON_SEP_COLON)
ATTR_SWEEP_START_DUTY = "start_duty"
ATTR_SWEEP_MAX_DUTY = "max_duty"
ATTR_SWEEP_STEP_DUTY = "step_duty"
ATTR_SWEEP_STEP_HOLD_SEC = "step_hold_sec"
ATTR_SWEEP_MOTION_THRESHOLD_ROT = "motion_threshold_rot"
ATTR_SWEEP_REQUIRED_SAMPLES = "required_samples"
ATTR_SWEEP_ENCODER_KEY = "encoder_key"
ATTR_SWEEP_ENCODER_SOURCE = "encoder_source"
ATTR_SWEEP_ENCODER_MOTOR_INDEX = "encoder_motor_index"
ATTR_SWEEP_ENCODER_COUNTS_PER_REV = "encoder_counts_per_rev"
PROFILE_EXPORT_FIELD_ORDER = (
    KEY_INTERFACE,
    KEY_MANUFACTURER,
    KEY_DEVICE_TYPE,
    KEY_ID,
    KEY_MODEL,
    KEY_TYPE,
    KEY_INVERT,
    KEY_PWM,
    KEY_ANALOG,
    KEY_ATTACHMENTS,
    KEY_TERMINATOR,
    KEY_VENDOR,
    KEY_ROLE,
    KEY_NOTES,
    KEY_TAGS,
    KEY_LIMITS,
)

CMD_PROFILES_APPLY = "profilesApply"
CMD_PROFILE_ACTIVATE = "profileActivate"
ARG_REGISTRY_JSON = "registryJson"
ARG_ACTIVATE_PROFILE = "activateProfile"
ARG_REGISTRY_HASH = "registryHash"
ARG_REGISTRY_BYTES = "registryBytes"

KEY_DEVICE = "device"
KEY_NAME = "name"
KEY_GROUPS = "groups"
KEY_MEMBERS = "members"
KEY_TEMP = "temp"
KEY_BY_PROFILE = "byProfile"
KEY_SELECTED_DEVICE = "selectedDevice"
KEY_MANUFACTURERS = "manufacturers"
KEY_DEVICE_TYPES = "device_types"
KEY_TEST_SETS = "test_sets"
KEY_TESTS = "tests"
KEY_TEST_SET = "test_set"
KEY_TEST = "test"
KEY_DIRTY = "dirty"
DIRTY_PROFILES = "profiles"
DIRTY_TESTS = "tests"
DIRTY_BINDINGS = "bindings"
DIRTY_MAPPINGS = "can-mappings"
KEY_COMMANDS = "commands"
KEY_WORKFLOW01 = "workflow01"
KEY_STATE = "state"
KEY_TESTS_RUN = "run"
KEY_RUN_ID = "runId"
KEY_RUN_STATE = "state"
KEY_RUN_TEST = "test"
KEY_RUN_RESULT = "result"
KEY_RUN_STATUS = "status"
KEY_RUN_MESSAGE = "message"
KEY_RUN_STARTED_AT_MS = "startedAtMs"
KEY_RUN_FINISHED_AT_MS = "finishedAtMs"
KEY_RUN_DETAILS = "details"
RUN_STATE_IDLE = "idle"
RUN_STATE_STARTING = "starting"
RUN_STATE_RUNNING = "running"
RUN_STATE_PASSED = "passed"
RUN_STATE_FAILED = "failed"
RUN_STATE_BLOCKED = "blocked"
RUN_STATE_ABORTED = "aborted"
RUN_STATE_TIMEOUT = "timeout"
RUN_TERMINAL_STATES = {
    RUN_STATE_PASSED,
    RUN_STATE_FAILED,
    RUN_STATE_BLOCKED,
    RUN_STATE_ABORTED,
    RUN_STATE_TIMEOUT,
}
RUN_SUCCESS_STATES = {RUN_STATE_PASSED}
KEY_BLOCKING_REASONS = "blockingReasons"
KEY_NEXT_STEPS = "nextSteps"
KEY_TEST_OVERVIEW = "testOverview"
KEY_TEST_SELECTED = "testSelected"
KEY_TOPICS = "topics"
KEY_CONTROLLERS = "controllers"
KEY_BINDINGS = "bindings"
KEY_GLOBAL_BINDINGS = "globalBindings"
KEY_COMMAND = "command"
KEY_CONTROLLER = "controller"
KEY_INPUT = "input"
KEY_KIND = "kind"
KEY_VALUE = "value"
KEY_MODE = "mode"
KEY_PORT = "port"
KEY_DEADBAND = "deadband"
LABEL_INPUT_PREFIX = "label="
LABEL_INPUT_VENDOR_MARK = " vendor="
LABEL_INPUT_TYPE_MARK = " type="
LABEL_INPUT_ID_MARK = " id="
LABEL_INPUT_MARKERS = (
    LABEL_INPUT_VENDOR_MARK,
    LABEL_INPUT_TYPE_MARK,
    LABEL_INPUT_ID_MARK,
)
LABEL_INPUT_PAREN_REGEX = r"^(?P<label>.+?)\s*\([^)]*\bid=\d+\)\s*$"

SHOW_TARGET_CONFIG = "config"
SHOW_TARGET_RUNTIME = "runtime-state"
SHOW_TARGET_LIFECYCLE = "lifecycle-state"
SHOW_TARGET_CONFIG_RAW = "config-raw"
SHOW_CONFIG_LOCAL_RAW = "local-raw"
SHOW_TARGET_PROFILES = "profiles"
SHOW_TARGET_PROFILE = "profile"
SHOW_TARGET_CONFIG_DIRTY = "config-dirty"
SHOW_CONFIG_DIRTY = "dirty"

KEY_PROFILE_INFO = "profile"
KEY_SELECTED = "selected"
KEY_ACTIVE_RUNTIME = "activeRuntime"
KEY_RUNTIME_ACTIVE = "runtimeActive"
KEY_CONTROLLED_LIFECYCLE_ACTIVE = "controlledLifecycleActive"
KEY_ESTOPPED = "estopped"
CLI_ACTIVE_GROUP_EDIT_SCOPE_KIND = RUNNABLE_SCOPE_KIND_MANUAL
KEY_DIAGRAM = "diagram"
KEY_DIAGRAM_PROFILES = "profiles"
KEY_DIAGRAM_NODES = "nodes"


def _group_member_label(member: object) -> str:
    """
    NAME
        _group_member_label - Return canonical group member label text.
    """
    if isinstance(member, dict):
        return get_group_member_label(member)
    if isinstance(member, str):
        return member.strip()
    return EMPTY_STRING


def _group_member_entry(label: str, enabled: bool = True) -> Dict[str, object]:
    """
    NAME
        _group_member_entry - Build canonical group member payload entry.
    """
    return make_group_member(label, enabled)
KEY_ACTIVE = "active"
KEY_DEFAULT = "default"
KEY_AVAILABLE = "available"
KEY_PROVENANCE = "provenance"
KEY_LAST_MODIFIED_AT = "lastModifiedAt"
KEY_LAST_SAVED = "lastSaved"
KEY_LAST_PUSHED = "lastPushed"
KEY_MATCH = "match"
KEY_LOCAL_VS_SAVED = "localVsSaved"
KEY_LOCAL_VS_PUSHED = "localVsPushed"
KEY_ROBOT_VS_PUSHED = "robotVsPushed"
KEY_AT = "at"
KEY_HASH = "hash"
KEY_PROFILE_NAME = "profile"
STRING_NONE = "(none)"
SEP_NEWLINE = "\n"
SEP_DOUBLE_SPACE = "  "
MATCH_STATE_YES = "YES"
MATCH_STATE_NO = "NO"
MATCH_STATE_UNKNOWN = "UNKNOWN"

PROMPT_LABEL_BRIDGE = "bridge"
PROMPT_DIRTY_MARK = "*"
PROMPT_EXEC = "bridge> "
PROMPT_EXEC_DISCONNECTED = "bridge(disconnected)> "
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
SHOW_TARGET_DEVICE_GROUP = "device-group"
SHOW_TARGET_BINDINGS = "bindings"
SHOW_TARGET_CAN_MAPPINGS = "can-mappings"
SHOW_TARGET_SELECTED_DEVICE = "selected-device"
SHOW_TARGET_SAFETY_LATCH = "safety-latch"
SHOW_TARGET_MESSAGE_LEVEL = "message-level"
SHOW_TARGET_DEVICE_USAGE = "device-usage"
SHOW_TARGET_COMMANDS = "commands"
SHOW_TARGET_HELP = "help"
SHOW_TARGET_WORKSPACE = "workspace"
SHOW_TARGET_CONTROLLERS = "controllers"
SHOW_TARGET_SOURCES = "sources"
SHOW_TARGET_TOPOLOGY = "topology"
SHOW_TARGET_NEIGHBORS = "neighbors"
SHOW_TARGET_ACTIVE = "active"
SHOW_TARGET_INSTANTIATED = "instantiated"
SHOW_TARGET_FAULTS = "faults"
SHOW_TARGET_SIGNALS = "signals"
SHOW_TARGET_SIGNAL = "signal"
CMD_TOPOLOGY = "topology"
CMD_NEIGHBORS = "neighbors"
CMD_NEIGHBOR_PORTS = "neighbor-ports"
CMD_NEIGHBOR_AUTO = "neighbor-auto"
CMD_NODES = "nodes"
CMD_EDGES = "edges"
CMD_NODE = "node"

SHOW_SOURCE_ROBOT = "robot"
SHOW_SOURCE_LOCAL = "local"
SHOW_SOURCE_BOTH = "both"
SHOW_FLAG_ALL = "--all"
SHOW_FLAG_GROUPED = FLAG_GROUPED
KEY_SCOPE = "scope"
KEY_IN_PROFILE = "inProfile"
SCOPE_CONFIG = "config"
SHOW_SOURCE_FLAGS = {
    SHOW_SOURCE_ROBOT,
    SHOW_SOURCE_LOCAL,
    SHOW_SOURCE_BOTH,
    "--robot",
    "--local",
    "--both",
}

MESSAGE_ERR_UNKNOWN_SHOW = "ERROR: Unknown show command."
MESSAGE_ERR_UNKNOWN_SHOW_SOURCE = "ERROR: Unknown show source."
MESSAGE_ERR_SHOW_DEVICE_REGISTRY_REMOVED = (
    "ERROR: 'show device registry <name>' was removed. Use 'show device <name>'."
)
MESSAGE_ERR_SHOW_LOCAL_ONLY = "ERROR: show {target} is local-only; remove robot/local/both."
MESSAGE_ERR_BINDINGS_SHOW_LOCAL_ONLY = (
    "ERROR: bindings show is local-only; remove robot/local/both."
)
MESSAGE_ERR_MAPPINGS_SHOW_LOCAL_ONLY = (
    "ERROR: can-mappings show is local-only; remove robot/local/both."
)
MESSAGE_ERR_TEST_SHOW_LOCAL_ONLY = (
    "ERROR: show test <name> is local-only; remove robot/local/both."
)
MESSAGE_ERR_SHOW_TESTS_ROBOT_ONLY = (
    "ERROR: show tests robot requires an active REST session."
)
MESSAGE_ERR_SHOW_LIFECYCLE_ROBOT_ONLY = (
    "ERROR: show lifecycle-state requires an active REST session."
)
LOCAL_ONLY_SHOW_TARGETS = (
    SHOW_TARGET_MESSAGE_LEVEL,
    SHOW_TARGET_DEVICE_USAGE,
    SHOW_TARGET_DEVICE,
    SHOW_TARGET_SIGNALS,
    SHOW_TARGET_SIGNAL,
    SHOW_TARGET_CAN_MAPPINGS,
    SHOW_TARGET_COMMANDS,
    SHOW_TARGET_HELP,
    SHOW_TARGET_WORKSPACE,
    SHOW_TARGET_CONTROLLERS,
    SHOW_TARGET_TOPOLOGY,
    SHOW_TARGET_SOURCES,
    SHOW_TARGET_CONFIG_RAW,
    SHOW_TARGET_CONFIG_DIRTY,
    CMD_TESTS,
    CMD_TEST,
)
KEY_INSTANTIATED = "instantiated"
KEY_OK = "ok"
KEY_MESSAGE = "message"
KEY_REASON = "reason"
KEY_STATUS = "status"
KEY_RUNTIME = "runtime"
KEY_RUNTIME_COMPONENTS = "components"
KEY_RUNTIME_THREADS = "threads"
KEY_VISIBILITY = "visibility"
KEY_SUMMARY = "summary"
KEY_SIGNALS = "signals"
KEY_FAULTS = "faults"
KEY_RECOVERY_MODE = "recoveryMode"
KEY_COMPONENT_COUNT = "componentCount"
KEY_ACTIVE_GROUP = "activeGroup"
KEY_ACTIVE_TEST_SET = "activeTestSet"
KEY_PRESENT = "present"
KEY_VIEW_BUS_OFFSETS = "busOffsets"
KEY_VIEW_BUS_COUNT = "busCount"
KEY_VIEW_BUS_CONNECTORS = "busConnectors"
KEY_VIEW_BUS_CONNECTOR_SIDES = "busConnectorSides"
KEY_LAYOUT_BUS = "bus"
KEY_LAYOUT_X = "x"
KEY_WARNING_COUNT = "warningCount"
KEY_FAULT_COUNT = "faultCount"
KEY_LAST_SEEN_MS = "lastSeenMs"
KEY_PRESENCE_CONF = "presenceConfidence"
KEY_FAULT_FLAGS = "faultFlags"
KEY_STICKY_FAULT_FLAGS = "stickyFaultFlags"
KEY_WARNING_FLAGS = "warningFlags"
KEY_STICKY_WARNING_FLAGS = "stickyWarningFlags"
KEY_FAULTS_RAW = "faultsRaw"
KEY_STICKY_FAULTS_RAW = "stickyFaultsRaw"
KEY_WARNINGS_RAW = "warningsRaw"
KEY_STICKY_WARNINGS_RAW = "stickyWarningsRaw"
KEY_CHANNEL_FAULT = "channelFault"
KEY_CHANNEL_STICKY_FAULT = "channelStickyFault"
KEY_BROWNOUT = "brownout"
KEY_CAN_WARNING = "canWarning"
KEY_HARDWARE_FAULT = "hardwareFault"
KEY_STICKY_BROWNOUT = "stickyBrownout"
KEY_STICKY_CAN_WARNING = "stickyCanWarning"
KEY_STICKY_CAN_BUS_OFF = "stickyCanBusOff"
KEY_STICKY_HAS_RESET = "stickyHasReset"
KEY_DETAILS = "details"
VALUE_UNAVAILABLE = "unavailable"
VALUE_ACTIVE = "ACTIVE"
MESSAGE_ERR_SHOW_REQUIRES_TARGET = "ERROR: show requires a target."
MESSAGE_ERR_TOPOLOGY_PROFILE_REQUIRED = "ERROR: Active profile required for topology commands."
MESSAGE_ERR_TOPOLOGY_NOT_LOADED = "ERROR: Topology not loaded for the active profile."
MESSAGE_ERR_TOPOLOGY_LOCAL_ONLY = "ERROR: topology commands are local-only right now."
MESSAGE_ERR_TOPOLOGY_USAGE = "ERROR: topology neighbor-ports set|delete|clear ... or topology neighbor-auto all|node ..."
MESSAGE_ERR_TOPOLOGY_NODE_REQUIRED = "ERROR: topology node label required."
MESSAGE_ERR_TOPOLOGY_NEIGHBOR_PORTS_SET = "ERROR: topology neighbor-ports set <node> <port> <neighbor> <neighborPort>"
MESSAGE_ERR_TOPOLOGY_NEIGHBOR_PORTS_DELETE = "ERROR: topology neighbor-ports delete <node> <port>"
MESSAGE_ERR_TOPOLOGY_NEIGHBOR_PORTS_CLEAR = "ERROR: topology neighbor-ports clear <node>"
MESSAGE_ERR_TOPOLOGY_NEIGHBOR_AUTO = "ERROR: topology neighbor-auto all [label1,label2] | topology neighbor-auto node <label>"
MESSAGE_ERR_TOPOLOGY_NODE_NOT_FOUND = "ERROR: topology node '{name}' not found in the active profile."
MESSAGE_INFO_TOPOLOGY_NEIGHBOR_PORT_SET = "INFO: topology neighbor port updated."
MESSAGE_INFO_TOPOLOGY_NEIGHBOR_PORT_DELETE = "INFO: topology neighbor port removed."
MESSAGE_INFO_TOPOLOGY_NEIGHBOR_PORT_CLEAR = "INFO: topology node neighbor ports cleared."
MESSAGE_INFO_TOPOLOGY_NEIGHBOR_AUTO = "INFO: topology neighbors rebuilt from layout."
MESSAGE_INFO_TOPOLOGY_VALIDATE_OK = "OK: topology is valid."
MESSAGE_TOPOLOGY_HEADER = "Topology:"
MESSAGE_TOPOLOGY_NODES_HEADER = "Nodes:"
MESSAGE_TOPOLOGY_EDGES_HEADER = "Edges:"
MESSAGE_TOPOLOGY_NEIGHBORS_HEADER = "Neighbors:"
MESSAGE_TOPOLOGY_NONE = "  (none)"
MESSAGE_TOPOLOGY_CAN_BUS_HEADER = "CAN Bus"
MESSAGE_TOPOLOGY_BACKBONE_HEADER = "  SWYFT Backbone:"
MESSAGE_TOPOLOGY_GROUP_HEADER_FMT = "  {name}:"
MESSAGE_TOPOLOGY_CAN_LINE_FMT = "  {from_label} -> {to_label}"
MESSAGE_TOPOLOGY_CAN_GROUP_LINE_FMT = "    {from_label} -> {to_label}{suffix}"
MESSAGE_TOPOLOGY_CAN_DUPLICATE_SUFFIX_FMT = " [listed multiple times: {groups}]"
MESSAGE_TOPOLOGY_FALLBACK_TEXT = "INFO: showing raw topology because a single CAN device path could not be derived."
MESSAGE_ERR_PRETTY_REQUIRES_JSON = "ERROR: --pretty requires --json."
MESSAGE_ERR_LOCAL_CONFIG_MISSING = "ERROR: Local config not loaded. Use merge/import config <bringup_system.json>."
MESSAGE_ERR_LOCAL_DEVICE_NOT_FOUND = "ERROR: Local device not found."
MESSAGE_OK_CONFIG_VALID = "OK: Config is valid."
MESSAGE_ERR_CONFIG_VALIDATE = "ERROR: {message}"
MESSAGE_STORE_ISSUE = "{location}: {message}"
MESSAGE_ERR_REGISTRY_NOT_LOADED = "ERROR: Devices table not loaded. Use merge/import config <bringup_system.json>."
MESSAGE_INFO_RENAME_REFS = "INFO: Updated references for {old} -> {new}: {details}"
MESSAGE_INFO_RENAME_REFS_NONE = "INFO: No references updated for {old} -> {new}."
MESSAGE_INFO_RENAME_REFS_ITEM = "{label}({count})"
MESSAGE_INFO_RENAME_REFS_LABEL_PROFILE_DEVICES = "profiles.devices"
MESSAGE_INFO_RENAME_REFS_LABEL_ATTACHMENTS = "devices.attachments"
MESSAGE_INFO_RENAME_REFS_LABEL_GROUPS = "bridgeConfig.groups"
MESSAGE_INFO_RENAME_REFS_LABEL_SELECTED = "bridgeConfig.selectedDevice"
MESSAGE_INFO_RENAME_REFS_LABEL_DIAGRAM = "diagram.nodes"
MESSAGE_INFO_RENAME_REFS_LABEL_TEST_DEVICES = "tests.devices"
MESSAGE_INFO_RENAME_REFS_LABEL_TEST_LIMIT_SWITCH = "tests.limitSwitch.id"
MESSAGE_INFO_RENAME_REFS_LABEL_TEST_ROTATION_ENCODER = "tests.rotation.encoderKey"
MESSAGE_INFO_RENAME_REFS_LABEL_TEST_DEADBAND_ENCODER = "tests.deadbandSweep.encoderKey"
RENAME_REF_PROFILE_DEVICES = "profile_devices"
RENAME_REF_ATTACHMENTS = "attachments"
RENAME_REF_GROUPS = "groups"
RENAME_REF_SELECTED = "selected"
RENAME_REF_DIAGRAM = "diagram"
RENAME_REF_TEST_DEVICES = "test_devices"
RENAME_REF_TEST_LIMIT_SWITCH = "test_limit_switch"
RENAME_REF_TEST_ROTATION_ENCODER = "test_rotation_encoder"
RENAME_REF_TEST_DEADBAND_ENCODER = "test_deadband_encoder"
RENAME_REF_ORDER = (
    RENAME_REF_PROFILE_DEVICES,
    RENAME_REF_ATTACHMENTS,
    RENAME_REF_GROUPS,
    RENAME_REF_SELECTED,
    RENAME_REF_DIAGRAM,
    RENAME_REF_TEST_DEVICES,
    RENAME_REF_TEST_LIMIT_SWITCH,
    RENAME_REF_TEST_ROTATION_ENCODER,
    RENAME_REF_TEST_DEADBAND_ENCODER,
)
KEY_LIMIT_SWITCH_ID = "id"
MESSAGE_LOCAL_PROFILES_EMPTY = "Local profiles: (none)"
MESSAGE_LOCAL_PROFILES_HEADER = "Local profiles:"
MESSAGE_LOCAL_PROFILE_HEADER = "Local profile:"
MESSAGE_LOCAL_PROFILE_NAME = "  name={name}"
MESSAGE_LOCAL_PROFILE_ACTIVE = "  active={name}"
MESSAGE_LOCAL_PROFILE_SELECTED = "  selected={name}"
MESSAGE_LOCAL_PROFILE_ACTIVE_RUNTIME = "  activeRuntime={name}"
MESSAGE_LOCAL_PROFILE_RUNTIME_ACTIVE = "  runtimeActive={value}"
MESSAGE_LOCAL_PROFILE_DEFAULT = "  default={name}"
MESSAGE_LOCAL_PROFILE_AVAILABLE = "  available={count}"
MESSAGE_LOCAL_PROFILE_DEVICES_HEADER = "  devices={count}"
MESSAGE_LOCAL_PROFILE_DEVICE_FMT = "    {label}"
MESSAGE_ERR_PROFILE_NOT_FOUND = "ERROR: Profile not found."
MESSAGE_DIRTY_HEADER = "Local dirty state:"
MESSAGE_DIRTY_ENTRY = "  {name}={value}"
MESSAGE_DIRTY_NONE = "  (clean)"
MESSAGE_DIRTY_PROMPT = "Unsaved changes in: {items}. Exit anyway?"
MESSAGE_DIRTY_LAST_MODIFIED = "  last-modified={value}"
MESSAGE_DIRTY_LAST_SAVED = "  last-saved={value}"
MESSAGE_DIRTY_LAST_PUSHED = "  last-pushed={value}"
MESSAGE_ERR_DEVICE_LABEL_REQUIRED = "ERROR: device name required."
MESSAGE_ERR_DEVICE_PROFILE_REQUIRED = "ERROR: Profile not selected. Use 'profile <profile>'."
MESSAGE_ERR_DEVICE_INTERFACE_INVALID = (
    "ERROR: deviceInterface must be CAN, DIO, PWM, ANALOG, or INTERNAL."
)
MESSAGE_ERR_DEVICE_FIELD_UNKNOWN = "ERROR: device set field not supported."
MESSAGE_ERR_DEVICE_FIELD_INT = "ERROR: device set value must be an integer."
MESSAGE_ERR_DEVICE_FIELD_BOOL = "ERROR: device set value must be true/false."
MESSAGE_ERR_DEVICE_FIELD_LIST = "ERROR: device set value must be a JSON list."
MESSAGE_ERR_DEVICE_FIELD_DICT = "ERROR: device set value must be a JSON object."
MESSAGE_WARN_DEVICE_INCOMPLETE = "WARNING: Device {label} missing required fields: {fields}"
MESSAGE_ERR_REGISTRY_DEVICE_NOT_FOUND = "ERROR: Device not found in devices table."
MESSAGE_SOURCE_LOCAL = "SOURCE: local"
MESSAGE_SOURCE_ROBOT = "SOURCE: robot"
MESSAGE_LOCAL_CONFIG_RAW = "Local bridgeConfig (raw):"
MESSAGE_LOCAL_REGISTRY_DEVICE = "Local devices-table entry {label}:"
MESSAGE_LOCAL_REGISTRY_EMPTY = "  (no fields)"
MESSAGE_REGISTRY_FIELD_FMT = "  {key}={value}"
MESSAGE_REGISTRY_FIELD_FMT_NAMED = "  {key}={value} ({name})"
MESSAGE_REGISTRY_TOPOLOGY_HEADER = "  topology:"
MESSAGE_REGISTRY_TOPOLOGY_FIELD_FMT = "    {key}={value}"
MESSAGE_REGISTRY_TOPOLOGY_NEIGHBOR_FMT = (
    "    neighbor {port}: {label} (key={key}, port={neighbor_port})"
)
MESSAGE_MAPPINGS_READ_FAIL = "WARNING: Failed to read CAN mappings: {path}"
MESSAGE_ERR_BINDINGS_SUBCOMMAND = (
    "ERROR: bindings <show|controller|binding|load|save|validate>"
)
MESSAGE_ERR_BINDINGS_SHOW = (
    "ERROR: bindings show [controllers|bindings] [--all] [--json] [--pretty]"
)
MESSAGE_ERR_BINDINGS_CONTROLLER_ADD = "ERROR: bindings controller add <controller> <type> <port>"
MESSAGE_ERR_BINDINGS_CONTROLLER_SET = "ERROR: bindings controller set <controller> <field> <value>"
MESSAGE_ERR_BINDINGS_CONTROLLER_RENAME = "ERROR: bindings controller rename <old> <new>"
MESSAGE_ERR_BINDINGS_CONTROLLER_DELETE = "ERROR: bindings no controller <controller>"
MESSAGE_ERR_BINDINGS_CONTROLLER_PORT = "ERROR: controller port must be an integer."
MESSAGE_ERR_BINDINGS_CONTROLLER_EXISTS = "ERROR: controller already exists."
MESSAGE_ERR_BINDINGS_CONTROLLER_NOT_FOUND = "ERROR: controller not found."
MESSAGE_ERR_BINDINGS_CONTROLLER_IN_USE = "ERROR: controller is referenced by bindings."
MESSAGE_ERR_BINDINGS_BINDING_ADD = (
    "ERROR: bindings binding add <command> <controller> <input> <id> <mode> [invert <on|off> deadband <value>]"
)
MESSAGE_ERR_BINDINGS_BINDING_SET = "ERROR: bindings binding set <index> <field> <value>"
MESSAGE_ERR_BINDINGS_BINDING_DELETE = "ERROR: bindings binding delete <index>"
MESSAGE_ERR_BINDINGS_BINDING_INDEX = "ERROR: binding index out of range."
MESSAGE_ERR_BINDINGS_FIELD_UNKNOWN = "ERROR: bindings field not supported."
MESSAGE_ERR_BINDINGS_CONTROLLER_REQUIRED = "ERROR: controller not found: {name}"
MESSAGE_ERR_BINDINGS_INVERT = "ERROR: invert must be on/off."
MESSAGE_ERR_BINDINGS_DEADBAND = "ERROR: deadband must be 0.0 to 1.0."
MESSAGE_ERR_BINDINGS_INPUT_KIND = "ERROR: input must be button, dpad, combo, or axis."
MESSAGE_ERR_BINDINGS_AXIS_MODE = "ERROR: axis bindings must use mode analog."
MESSAGE_ERR_BINDINGS_AXIS_FIELDS = "ERROR: axis bindings require invert <on|off> deadband <value>."
MESSAGE_ERR_BINDINGS_NON_AXIS_EXTRA = "ERROR: only axis bindings may define invert/deadband."
MESSAGE_ERR_BINDINGS_LOAD = "ERROR: Failed to read bindings: {path}"
MESSAGE_ERR_BINDINGS_WRITE = "ERROR: Failed to write bindings: {path}: {error}"
MESSAGE_ERR_BINDINGS_VALIDATE = "ERROR: bindings validation failed: {message}"
MESSAGE_INFO_BINDINGS_LOADED = "Loaded bindings: {path}"
MESSAGE_INFO_BINDINGS_SAVED = "Wrote bindings to {path}."
MESSAGE_INFO_BINDINGS_MIRRORED = "Mirrored bindings to {path}."
MESSAGE_BINDINGS_HEADER = "Local bindings config:"
MESSAGE_BINDINGS_CONTROLLERS_HEADER = "  controllers:"
MESSAGE_BINDINGS_BINDINGS_HEADER = "  bindings:"
MESSAGE_BINDINGS_GLOBAL_HEADER = "Global bindings:"
MESSAGE_BINDINGS_GLOBAL_UNAVAILABLE = "  (global bindings not loaded)"
MESSAGE_BINDINGS_NONE = "  (none)"
MESSAGE_BINDINGS_CONTROLLER_FMT = "    {name} type={type} port={port}"
MESSAGE_BINDINGS_BINDING_FMT = (
    "    [{index}] command={command} controller={controller} input={input} id={id} mode={mode}"
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
MESSAGE_ERR_TESTS_SUBCOMMAND = "ERROR: tests <templates|clear>"
MESSAGE_ERR_TESTS_TEMPLATE_NOT_FOUND = "ERROR: test template not found: {name}"
MESSAGE_TESTS_TEMPLATES_HEADER = "Test templates:"
MESSAGE_TESTS_TEMPLATES_NONE = "  (none)"
MESSAGE_TESTS_TEMPLATE_ENTRY = "  {name}"
MESSAGE_TESTS_CLEARED = "Tests cleared."
MESSAGE_TIP_UNSAVED = "You have unsaved changes. Use `save profiles ...` or `save sources` to save."
MESSAGE_ERR_TESTS_EDIT_MODE = "ERROR: tests templates/clear not allowed in test edit mode. Use `exit` or `end` first."
MESSAGE_SAVE_ALL_PROFILES_MISSING = "ERROR: No profiles destination set. Fix: save profiles src/main/deploy/bringup_system.json"
MESSAGE_SAVE_PROFILES_PATH_REQUIRED = "ERROR: No profiles path set. Fix: save profiles <path>."
MESSAGE_SAVE_PROFILES_CONFIRM = "Save profiles to {path}?"
MESSAGE_INFO_PROFILES_MIRRORED = "Mirrored profiles to {path}."
MESSAGE_PUSH_DIRTY_BLOCKED = "ERROR: push config refused: local config is dirty. Save to disk first."
MESSAGE_REVERT_START = "Reverting local unsaved state from disk sources."
MESSAGE_REVERT_DONE = "Revert complete."
MESSAGE_REVERT_NOTHING = "Nothing to revert."
MESSAGE_PUSH_STAGE = "  {stage}: {status}"
MESSAGE_PUSH_STAGE_DETAIL = "    detail: {detail}"
MESSAGE_PUSH_STAGE_ACTIVE = "  active robot profile: {profile}"
MESSAGE_PUSH_STAGE_DATA_VERSION = "  local config version: {version}"
MESSAGE_TIU_USAGE = "ERROR: tiu on|off"
MESSAGE_TIU_ON = "TIU mode enabled."
MESSAGE_TIU_OFF = "TIU mode disabled."
MESSAGE_TIU_HEADER_FMT = "{prompt} {rule} {clock}"
MESSAGE_TIU_SECTIONS = "[x] Host  [x] Save/Push  [x] Robot  [x] Runtime  [x] Devices  [x] Faults  [x] Events  [x] CLI"
MESSAGE_TIU_HOST = "HOST"
MESSAGE_TIU_SAVE_PUSH = "SAVE / PUSH"
MESSAGE_TIU_ROBOT = "ROBOT"
MESSAGE_TIU_RUNTIME = "RUNTIME"
MESSAGE_TIU_DEVICES = "DEVICES"
MESSAGE_TIU_FAULTS = "DEVICE FAULTS"
MESSAGE_TIU_EVENTS = "RECENT EVENTS"
MESSAGE_TIU_CLI = "CLI OUTPUT"
MESSAGE_TIU_NONE = "  (none)"
MESSAGE_TIU_UNAVAILABLE = "  unavailable"
MESSAGE_TIU_MATCH_FMT = "  Match: local=saved {saved}   local=pushed {pushed}   robot=pushed {robot}"
MESSAGE_TIU_SOURCES_FMT = "  Sources: registry={registry} bindings={bindings} mappings={mappings} tests={tests}"
MESSAGE_TIU_HOST_STATE_FMT = "  Profile: {profile}   Dirty: {dirty}   Recovery: {recovery}"
MESSAGE_TIU_SAVE_MODIFIED_FMT = "  Last modified: {value}"
MESSAGE_TIU_SAVE_SAVED_FMT = "  Last save:     {value}"
MESSAGE_TIU_SAVE_PUSHED_FMT = "  Last push:     {value}"
MESSAGE_TIU_ROBOT_STATE_FMT = "  Connected: {connected}   Enabled: {enabled}   EStopped: {estopped}   Mode: {mode}"
MESSAGE_TIU_ROBOT_PROFILE_FMT = "  Active profile: {profile}"
MESSAGE_TIU_RUNTIME_FMT = "  Active group members: {members}   Active test set: {test_set}   Runtime components: {components}"
MESSAGE_TIU_DEVICES_FMT = "  Configured: {configured}   Instantiated: {instantiated}   Unavailable: {unavailable}   Visible: {visible}"
MESSAGE_TIU_FAULTS_FMT = "  Faulted devices: {faulted}"
MESSAGE_TIU_FAULT_ROW_FMT = "  {label}  faults={faults} warnings={warnings}"
MESSAGE_TIU_EVENT_ROW_FMT = "  {line}"
MESSAGE_TIU_OUTPUT_ROW_FMT = "  {line}"
MESSAGE_TIU_SECTION_RULE = "-"
MESSAGE_TIU_CLEAR_SCREEN = "\x1b[2J\x1b[H"
MESSAGE_TIU_CURSOR_FMT = "\x1b[{row};1H"
MESSAGE_TIU_CLEAR_LINE = "\x1b[2K"
MESSAGE_TIU_CLEAR_TO_END = "\x1b[J"
MESSAGE_TIU_UNSET = "(none)"
MESSAGE_TIU_BOOL_YES = "YES"
MESSAGE_TIU_BOOL_NO = "NO"
MESSAGE_TIU_STATUS_CONNECTED = "YES"
MESSAGE_TIU_STATUS_DISCONNECTED = "NO"
MESSAGE_TIU_STATUS_DIRTY = "YES"
MESSAGE_TIU_STATUS_CLEAN = "NO"
MESSAGE_TIU_EVENT_ENABLED = "INFO: TIU mode enabled."
MESSAGE_TIU_EVENT_DISABLED = "INFO: TIU mode disabled."
TIU_OUTPUT_MAX_LINES = 400
TIU_EVENT_MAX_LINES = 50
TIU_DEVICE_DETAIL_MAX = 6
TIU_FAULT_DETAIL_MAX = 4
TIU_LINE_MAX_FALLBACK = 120
TIU_SECTION_MARGIN = 4
TIU_RUNTIME_CACHE_SEC = 0.75
TIU_RENDER_RESERVED_LINES = 6
TIU_PROMPT_ROW_OFFSET = 2
MESSAGE_SAVE_ALL_BINDINGS_MISSING = (
    "ERROR: No bindings destination set. Fix: bindings save src/main/deploy/bringup_bindings.json"
)
MESSAGE_SAVE_ALL_MAPPINGS_MISSING = (
    "ERROR: No mappings destination set. Fix: can-mappings save src/main/deploy/can_mappings.json"
)
MESSAGE_MESSAGE_LEVEL = "Message level: {level}"
MESSAGE_MESSAGE_LEVEL_UPDATED = "Message level set to {level}."
MESSAGE_MESSAGE_LEVEL_ERROR = "ERROR: messages <beginner|medium|expert>"
MESSAGE_CONFIRM_PROFILE_DEVICE_DELETE = "Delete profile device '{name}'?"
MESSAGE_PROFILE_DEVICE_DELETED = "Deleted profile device {name}."
MESSAGE_PROFILE_EXPORT_NONE = "ERROR: No profiles loaded. Merge a bringup_system.json first."
MESSAGE_PROFILE_EXPORT_UNKNOWN = "ERROR: Profile not found: {name}."
MESSAGE_PROFILE_EXPORT_WRITE_FAIL = "ERROR: Failed to write profile export: {detail}"
MESSAGE_PROFILE_EXPORT_WRITTEN = "Wrote profile export: {json_path} + {script_path}."
MESSAGE_PROFILES_EXPORT_WRITTEN = "Wrote profiles export: {json_path} + {script_path}."
MESSAGE_PROFILE_EXPORT_PATH_INVALID = "Invalid export path (missing directory): {path}"
MESSAGE_PROFILE_DEVICE_SHOW_ALL_HEADER = "Profile device entries:"
MESSAGE_PROFILE_DEVICE_SHOW_ALL_PROFILE_HEADER = "Profile device list:"
MESSAGE_PROFILE_DEVICE_SHOW_ALL_PROFILE_ENTRY = "  {label} x{count}"
MESSAGE_PROFILE_DEVICE_SHOW_ALL_ENTRY = "  [{index}] label={label}"
MESSAGE_PROFILE_DEVICE_SHOW_ALL_COUNT = "  count={count}"
MESSAGE_PROFILE_DEVICE_SHOW_ALL_FIELD_FMT = "    {key}={value}"
MESSAGE_PROFILE_DEVICE_SHOW_ALL_NONE = "  (none)"
MESSAGE_SHOW_COMMANDS_HEADER = "Available commands:"
MESSAGE_SHOW_HELP_HEADER = "Help topics:"
MESSAGE_HELP_QUICK_HEADER = "Quick help:"
MESSAGE_HELP_QUICK_EMPTY = "  (no commands)"
MESSAGE_HELP_QUICK_ALIASES = "Abbrev: use unique prefixes (e.g., 'conf ter', 'pro def', 'sho ver')."
MESSAGE_PROFILES_INIT_OK = "Initialized empty profiles payload."
MESSAGE_HINT_PREFIX = "HINT: "
MESSAGE_HINT_VALIDATE = (
    "validate all | validate config [path] [--all] | validate profiles [robot|local] [--active] | "
    "validate tests [--active-set] | validate bindings [path] | validate can-mappings [path] | "
    "validate script <path> | validate file <path> [--repair]"
)
from tools.common.test_authoring.validator import AXIS_INPUTS, BUTTON_INPUTS, LIMIT_SWITCH_DEVICE_TYPE
MESSAGE_HINT_SAVE = (
    "save all [--prompt] [--force] | save config <path> [--force] | "
    "save bridge-config <path> [--force] | save runtime-groups <path> [--force] | "
    "save profiles <path> [--force] | save sources [--force]"
)
MESSAGE_HINT_SOURCES = "show sources | load sources | save sources"
MESSAGE_HINT_RECOVER = "recover list | recover last-good | recover from <timestamp>"
MESSAGE_HINT_RESET_ZERO_CONFIG = "reset zero-config [--yes] [--clear-memory]"
MESSAGE_HINT_SHOW = "show <target> [--json] [--pretty] [robot|local|both]"
MESSAGE_HINT_PROFILE = (
    "profile <profile> | profile create <profile> | profile delete <profile> | profile device delete <device> "
    "| profile device show-all <device> | profile export <profile> <path> [--install-robot] | "
    "profile default <profile>"
)
MESSAGE_HINT_PROFILES = (
    "profiles init | profiles push <path> [--activate <profile>] | profiles reload | profiles activate <profile>"
)
MESSAGE_HINT_RUNTIME = "runtime activate [<profile>] | runtime deactivate"
MESSAGE_ERR_PROFILES_ACTIVATE = "ERROR: profiles activate requires a profile name."
MESSAGE_ERR_RUNTIME_ACTION = "ERROR: runtime requires activate [<profile>] or deactivate."
MESSAGE_ERR_RUNTIME_ACTIVATE_SEND = "ERROR: Failed to send runtime activate."
MESSAGE_ERR_RUNTIME_DEACTIVATE_SEND = "ERROR: Failed to send runtime deactivate."
MESSAGE_ERR_LIFECYCLE_ACTION = (
    "ERROR: lifecycle requires activate <label> [mode <mode>] | deactivate <label> | deactivate-active."
)
MESSAGE_ERR_LIFECYCLE_LABEL = "ERROR: lifecycle label required."
MESSAGE_ERR_LIFECYCLE_MODE = "ERROR: lifecycle mode requires a value."
MESSAGE_ERR_LIFECYCLE_ACTIVATE_SEND = "ERROR: Failed to send lifecycle activate."
MESSAGE_ERR_LIFECYCLE_DEACTIVATE_SEND = "ERROR: Failed to send lifecycle deactivate."
MESSAGE_ERR_LIFECYCLE_DEACTIVATE_ACTIVE_SEND = "ERROR: Failed to send lifecycle deactivate-active."
MESSAGE_LIFECYCLE_ACTIVATED_PREFIX = "Lifecycle activated: "
MESSAGE_LIFECYCLE_DEACTIVATED_PREFIX = "Lifecycle deactivated: "
MESSAGE_LIFECYCLE_DEACTIVATED_ACTIVE = "Lifecycle deactivated active session."
MESSAGE_ERR_PROFILES_ACTIVATE_SEND = "ERROR: Failed to send profile activate command."
MESSAGE_ERR_PROFILES_RELOAD_SEND = "ERROR: Failed to send profiles reload command."
MESSAGE_INFO_PROFILES_RELOAD = "Profiles reloaded on robot."
MESSAGE_HINT_CAN_MAPPINGS = "can-mappings show [manufacturers|device-types] | can-mappings manufacturer set <id> <name>"
MESSAGE_VALIDATE_ALL_HEADER = "Validate all:"
MESSAGE_VALIDATE_ALL_ITEM_OK = "  {label}: OK"
MESSAGE_VALIDATE_ALL_ITEM_ERR = "  {label}: ERROR: {message}"
MESSAGE_VALIDATE_ALL_SUMMARY_OK = "OK: All validations passed."
MESSAGE_VALIDATE_ALL_SUMMARY_ERR = "ERROR: Validation failures: {count}"
VALIDATE_ALL_CONFIG = "config"
VALIDATE_ALL_PROFILES_LOCAL = "profiles local"
VALIDATE_ALL_PROFILES_ROBOT = "profiles robot"
VALIDATE_ALL_TESTS = "tests"
VALIDATE_ALL_BINDINGS = "bindings"
VALIDATE_ALL_MAPPINGS = "can-mappings"
MESSAGE_VALIDATE_SCRIPT_HEADER = "Script lint:"
MESSAGE_VALIDATE_SCRIPT_OK = "OK: Script lint passed."
MESSAGE_VALIDATE_SCRIPT_ERR = "ERROR: Script lint failures: {count}"
MESSAGE_VALIDATE_SCRIPT_LINE = "  line {line}: {message}"
MESSAGE_VALIDATE_SCRIPT_PATH_REQUIRED = "ERROR: validate script <path>"
SCRIPT_COMMENT_PREFIX = "#"
MESSAGE_DEBUG_GRAMMAR_HEADER = "Grammar model dump:"
MESSAGE_DEBUG_GRAMMAR_USAGE = "ERROR: debug grammar [--json] [--dot <path>]"
MESSAGE_DEBUG_GRAMMAR_DOT_REQUIRED = "ERROR: --dot requires a path."
MESSAGE_DEBUG_GRAMMAR_DOT_SAVED = "Wrote grammar DOT to {path}."
MESSAGE_DEBUG_GRAMMAR_DOT_FAIL = "ERROR: Failed to write grammar DOT: {error}"
MESSAGE_RESET_ZERO_CONFIG_WARNING = (
    "WARNING: This operation deletes bringup_system.json in the active deploy path."
)
MESSAGE_RESET_ZERO_CONFIG_TARGET = "  - {path}"
MESSAGE_RESET_ZERO_CONFIG_CONFIRM = "Proceed with zero-config reset?"
MESSAGE_RESET_ZERO_CONFIG_CANCELLED = "Cancelled."
MESSAGE_RESET_ZERO_CONFIG_DELETED = "Deleted: {path}"
MESSAGE_RESET_ZERO_CONFIG_MISSING = "Already missing: {path}"
MESSAGE_RESET_ZERO_CONFIG_DONE = "Zero-config reset complete. deleted={deleted} missing={missing}."
MESSAGE_RESET_ZERO_CONFIG_MEMORY_CLEARED = "Cleared in-memory local workspace state."
MESSAGE_RESET_ZERO_CONFIG_FAILED = "ERROR: Failed to delete {path}: {error}"
MESSAGE_HINT_VALIDATE_CONFIG_PROFILE = "validate config expects a file path; did you mean `profile <profile>`?"
MESSAGE_VALIDATE_OK = "OK"
MESSAGE_VALIDATE_ROBOT_NOT_CONNECTED = "Robot not connected."
MESSAGE_VALIDATE_ROBOT_DEVICES_FETCH = "ERROR: Failed to fetch robot devices."
MESSAGE_VALIDATE_PROFILES_MISSING = "  missing: {labels}"
MESSAGE_VALIDATE_PROFILES_EXTRA = "  extra: {labels}"
MESSAGE_VALIDATE_PROFILES_HEADER = "Profile devices do not match robot:"
MESSAGE_LABEL_SHOW_DEVICES = "show devices"
MESSAGE_LABEL_SHOW_TESTS = "show tests"
MESSAGE_LABEL_SHOW_SOURCES = "show sources"
MESSAGE_VALIDATE_SCHEMA_VERSION = "schema_version mismatch: expected {expected}, got {found}"
MESSAGE_VALIDATE_DATA_VERSION = "data_version missing or empty"
MESSAGE_VALIDATE_DATA_HASH = "data_hash missing or empty"
MESSAGE_VALIDATE_DATA_HASH_MISMATCH = "data_hash mismatch (run python -m tools.validate_sync)"
MESSAGE_VALIDATE_DEVICES_MISSING = "devices missing or empty"
MESSAGE_VALIDATE_DEVICE_LABEL_MISSING = "device label missing"
MESSAGE_VALIDATE_DEVICE_LABEL_DUP = "duplicate device label: {label}"
MESSAGE_VALIDATE_PROFILES_EMPTY = "profiles missing or empty"
MESSAGE_VALIDATE_PROFILE_DEVICES_MISSING = "profile devices list missing: {profile}"
MESSAGE_VALIDATE_PROFILE_DEVICE_UNKNOWN = "profile {profile} references unknown device {label}"
MESSAGE_VALIDATE_PROFILE_DEVICE_DUP = "profile {profile} duplicate device label {label}"
MESSAGE_VALIDATE_ACTIVATE_PROFILE_UNKNOWN = "activate profile not found: {profile}"
MESSAGE_ERR_PROFILES_PUSH_PARSE_ROOT = "root is not an object"
MESSAGE_VALIDATE_BINDINGS_LOAD = "ERROR: Failed to read bindings: {path}"
MESSAGE_VALIDATE_MAPPINGS_LOAD = "ERROR: Failed to read CAN mappings: {path}"
MESSAGE_VALIDATE_TESTS_HEADER = "Test validation errors:"
MESSAGE_VALIDATE_TESTS_ENTRY = "  {message}"
MESSAGE_VALIDATE_TESTS_ENTRY_WITH_TEST = "  {test}: {message}"
MESSAGE_DEVICE_USAGE_HEADER = "Device usage:"
MESSAGE_DEVICE_USAGE_DEVICE = "  device={name}"
MESSAGE_DEVICE_USAGE_PROFILE = "  profile={name}"
MESSAGE_DEVICE_USAGE_GROUPS_HEADER = "  groups:"
MESSAGE_DEVICE_USAGE_TESTS_HEADER = "  tests:"
MESSAGE_DEVICE_USAGE_NONE = "    (none)"
MESSAGE_DEVICE_USAGE_GROUP_ENTRY = "    {name}"
MESSAGE_DEVICE_USAGE_TEST_ENTRY = "    {test_set}/{name} ({type})"
MESSAGE_DEVICE_USAGE_TEST_ENTRY_SIMPLE = "    {test_set}/{name}"
MESSAGE_NO_KNOWN_VALUES = "No known values; see docs."
MESSAGE_SOURCES_HEADER = "Sources:"
MESSAGE_SOURCES_ENTRY = "  {name}: {value}"
MESSAGE_SOURCES_NOT_LOADED = "(not loaded)"
MESSAGE_SOURCES_UNKNOWN = "(unknown source)"
MESSAGE_SOURCES_LOAD_HEADER = "Loading sources:"
MESSAGE_SOURCES_SAVE_HEADER = "Saving sources:"
MESSAGE_SOURCES_LOAD_OK = "Loaded {name} from {path}."
MESSAGE_SOURCES_SAVE_OK = "Saved {name} to {path}."
MESSAGE_SOURCES_SKIP_UNKNOWN = "ERROR: {name} has unknown source path."
MESSAGE_SOURCES_SKIP_NOT_LOADED = "ERROR: {name} not loaded."
MESSAGE_SOURCES_ROBOT_UNSUPPORTED = "ERROR: Robot sources unavailable."
MESSAGE_SOURCES_DONE = "Done."
MESSAGE_SAVE_BLOCKED = "ERROR: Save blocked; validation failed."
MESSAGE_SAVE_FORCE_HINT = "Hint: Use --force to save anyway."
MESSAGE_SAVE_FORCED = "WARNING: Saving despite validation errors (--force)."
MESSAGE_ERR_SAVE_WRITE = "ERROR: Failed to write {path}: {error}"
MESSAGE_ERR_SAVE_PROMPT = "ERROR: --prompt only valid with save all."
MESSAGE_ERR_SAVE_PATH_REQUIRED = "ERROR: save {target} <path>"
MESSAGE_SAVE_CONFIG_SAVED = "Wrote bridgeConfig to {path}."
MESSAGE_SNAPSHOT_CREATED = "Snapshot created: {path}"
MESSAGE_SNAPSHOT_FAILED = "WARNING: Failed to write snapshot: {path}: {error}"
MESSAGE_SNAPSHOT_LAST_GOOD_FAILED = "WARNING: Failed to write last_good snapshot: {path}: {error}"
MESSAGE_AUDIT_WRITE_FAILED = "WARNING: Failed to write audit log: {path}: {error}"
MESSAGE_RECOVER_HEADER = "Recovery:"
MESSAGE_RECOVER_LIST_HEADER = "Recovery snapshots:"
MESSAGE_RECOVER_LIST_EMPTY = "  (none)"
MESSAGE_RECOVER_LIST_SOURCE = "  {source}: {path}"
MESSAGE_RECOVER_LIST_LAST_GOOD = "    last-good: {name}"
MESSAGE_RECOVER_LIST_ENTRY = "    {name}"
MESSAGE_RECOVER_LIST_SOURCE_EMPTY = "    (none)"
MESSAGE_RECOVER_MISSING = "WARNING: Snapshot not found for {source}: {path}"
MESSAGE_RECOVER_SOURCE_SKIP = "WARNING: Source not loaded; skipping {source}."
MESSAGE_RECOVER_APPLIED = "Recovery applied."
MESSAGE_RECOVER_FAILED = "ERROR: Recovery failed for {source}: {path}"
MESSAGE_REPAIR_APPLIED = "Repair applied to {path}."
MESSAGE_REPAIR_NO_CHANGES = "No repairs needed for {path}."
MESSAGE_REPAIR_FAILED = "ERROR: Repair failed: {message}"
MESSAGE_VALIDATE_FILE_OK = "OK: File validation passed."
MESSAGE_VALIDATE_FILE_ERR = "ERROR: File validation failed: {message}"
MESSAGE_VALIDATE_FILE_LOAD = "ERROR: Failed to read file: {path}"
MESSAGE_VALIDATE_FILE_UNSUPPORTED = "ERROR: Unsupported file for validation: {path}"
MESSAGE_VALIDATE_FILE_PATH_REQUIRED = "ERROR: validate file <path>"
SOURCE_DISPLAY_FMT = "{path} (exists={exists})"
TEXT_STATUS_HEADER = "Bridge status:"
TEXT_STATUS_BUILD = "  build={value}"
TEXT_STATUS_PROFILE = "  profile={value}"
TEXT_STATUS_ENABLED = "  enabled={value}"
TEXT_STATUS_ESTOPPED = "  estopped={value}"
TEXT_STATUS_MODE = "  mode={value}"
TEXT_STATUS_GROUPS = "  groups={value}"
TEXT_STATUS_SELECTED = "  selectedDevice={device} ({state})"
TEXT_GROUPS_NONE = "Groups: (none)"
TEXT_GROUPS_HEADER = "Groups:"
TEXT_GROUPS_ENTRY = "  {name} ({state}) members={members} bindings={bindings}"
TEXT_GROUP_HEADER = "Group {name} ({state})"
TEXT_GROUP_MEMBERS_HEADER = "Members:"
TEXT_GROUP_BINDINGS_HEADER = "Bindings:"
TEXT_GROUP_NONE = "  (none)"
TEXT_BINDINGS_NONE = "Bindings: (no groups)"
TEXT_BINDINGS_HEADER = "Bindings:"
TEXT_BINDINGS_GROUP = "  {name}"
TEXT_BINDING_ENTRY = "    {input} {kind}"
TEXT_BINDING_ENTRY_VALUE = "    {input} {kind} {value}"
TEXT_SELECTED_DEVICE_PREFIX = "Selected device: "
TEXT_DEVICE_NOT_FOUND = "Device: (not found)"
TEXT_DEVICE_PREFIX = "Device "
TEXT_DEVICE_ENTRY = "label={label} vendor={vendor} type={type} id={id}"
TEXT_DEVICES_HEADER = "Devices:"
TEXT_DEVICES_NONE = "Devices: (none)"
TEXT_DEVICES_ALL_HEADER = "Devices (full config inventory):"
TEXT_DEVICES_ALL_NONE = "Devices (full config inventory): (none)"
TEXT_DEVICES_LIST_PREFIX = "  "
TEXT_DEVICE_REGISTRY_ENTRY = (
    "label={label} interface={interface} vendor={vendor} type={type} id={id} "
    "model={model} inProfile={in_profile}"
)
TEXT_TESTS_HEADER = "=== Bringup Tests ==="
TEXT_TESTS_FOOTER = "====================="
TEXT_TESTS_ACTIVE_SET = "Active set: {active} (default: {default})"
TEXT_TESTS_COUNTS = "Total: {total} Enabled: {enabled}"
TEXT_TESTS_TABLE_HEADER = "Idx Sel En Type       Name                         HoldBtn                Devices"
TEXT_TESTS_ROW_FMT = "{index:3d}  {sel}  {en}  {type:<9} {name:<28} {hold:<20} {devices}"
TEXT_TESTS_NO_TESTS = "No tests loaded."
TEXT_SOURCES_HEADER = "=== Sources ==="
TEXT_SOURCES_FOOTER = "==============="
TEXT_SOURCES_ENTRY = "  {name}: {path} (exists={exists})"
TEXT_PROVENANCE_HEADER = "Provenance:"
TEXT_PROVENANCE_MODIFIED = "  Last modified: {value}"
TEXT_PROVENANCE_SAVED = "  Last save:     {value}"
TEXT_PROVENANCE_PUSHED = "  Last push:     {value}"
TEXT_PROVENANCE_MATCH = "  Match: local=saved {saved}   local=pushed {pushed}   robot=pushed {robot}"
TEXT_STATUS_ON = "on"
TEXT_STATUS_OFF = "off"
TEXT_STATUS_NONE = "(none)"
TEXT_ENABLED = "enabled"
TEXT_DISABLED = "disabled"
TEXT_PAREN_OPEN = " ("
TEXT_PAREN_CLOSE = ")"
TEXT_BINDINGS_GROUP_NONE = "    (none)"
TEXT_BIND_LIST_HEADER = "Binding diagnostics:"
TEXT_BIND_LIST_NONE = "  (no bindings)"
TEXT_BIND_LIST_ENTRY = "  {index}. {input} {kind}{value} status={status} reason={reason}"
TEXT_BIND_EXPLAIN_HEADER = "Binding {index}"
TEXT_BIND_EXPLAIN_GROUP = "  group: {group}"
TEXT_BIND_EXPLAIN_INPUT = "  input: {input}"
TEXT_BIND_EXPLAIN_KIND = "  kind: {kind}"
TEXT_BIND_EXPLAIN_VALUE = "  value: {value}"
TEXT_BIND_EXPLAIN_CONTROLLER = "  controller: {controller} found={found}"
TEXT_BIND_EXPLAIN_SIGNAL = "  signal: {signal} found={found}"
TEXT_BIND_EXPLAIN_GROUP_ENABLED = "  group enabled: {enabled}"
TEXT_BIND_EXPLAIN_MEMBERS = "  enabled members: {enabled}/{total}"
TEXT_BIND_EXPLAIN_STATUS = "  status: {status}"
TEXT_BIND_EXPLAIN_REASON = "  reason: {reason}"
TEXT_BIND_EXPLAIN_LAST_INPUT = "  last input value: unavailable"
TEXT_BIND_EXPLAIN_LAST_OUTPUT = "  last output value: unavailable"
TEXT_BIND_TEST_PASS = "Binding test result: PASS"
TEXT_BIND_TEST_FAIL = "Binding test result: FAIL"
TEXT_BIND_VALUE_PREFIX = " "
TEXT_BIND_VALUE_NONE = "(none)"
BIND_DIAG_STATUS_ACTIVE = "ACTIVE"
BIND_DIAG_STATUS_BLOCKED = "BLOCKED"
BIND_DIAG_STATUS_UNRESOLVED = "UNRESOLVED"
BIND_DIAG_STATUS_DISABLED = "DISABLED"
BIND_BOOL_YES = "yes"
BIND_BOOL_NO = "no"
ERR_BIND_EXPLAIN_USAGE = "ERROR: bind explain <binding>"
ERR_BIND_TEST_USAGE = "ERROR: bind test <binding>"
ERR_BIND_NOT_FOUND = "ERROR: binding not found."
ERR_BIND_CONTROLLER_PREFIX = "binding input must include controller.signal"
ERR_BIND_CONTROLLER_MISSING = "controller not found"
ERR_BIND_SIGNAL_MISSING = "signal not found"
ERR_BIND_GROUP_DISABLED = "group disabled"
ERR_BIND_NO_ENABLED_MEMBERS = "group has no enabled members"
ERR_BIND_READY_LOCAL_ONLY = "binding resolves in local config; runtime values unavailable"
TEXT_VERSION_PREFIX = "Robot version: "
TEXT_BUILD_HEADER = "Build:"
TEXT_TESTS_HOLD_DEFAULT = "-"
TEXT_TESTS_DEVICES_EMPTY = "-"
TEXT_TESTS_TYPE_UNKNOWN = "?"
TEXT_TESTS_NAME_UNNAMED = "(unnamed)"
TEXT_TESTS_SELECTED_MARK = "*"
TEXT_TESTS_SELECTED_EMPTY = " "
TEXT_TESTS_ENABLED_MARK = "Y"
TEXT_TESTS_DISABLED_MARK = "N"

KEY_SOURCES = "sources"
KEY_SOURCE_NAME = "name"
KEY_SOURCE_PATH = "path"
KEY_SOURCE_STATUS = "status"
KEY_SOURCE_NOTE = "note"
KEY_AUDIT_ENTRIES = "entries"
KEY_AUDIT_TIMESTAMP = "timestamp"
KEY_AUDIT_ACTION = "action"
KEY_AUDIT_SOURCE = "source"
KEY_AUDIT_PATH = "path"
KEY_AUDIT_HASH = "hash"
KEY_AUDIT_VALID = "valid"
KEY_DATA_VERSION_CAMEL = "dataVersion"
KEY_DATA_HASH_CAMEL = "dataHash"
SOURCE_STATUS_LOADED = "loaded"
SOURCE_STATUS_NOT_LOADED = "not-loaded"
SOURCE_STATUS_UNKNOWN = "unknown"
SOURCE_NAME_PROFILES = "profiles"
SOURCE_NAME_REGISTRY = "devices"
SOURCE_NAME_CONFIG = "config"
SOURCE_NAME_TESTS = "tests"
SOURCE_NAME_BINDINGS = "bindings"
SOURCE_NAME_CAN_MAPPINGS = "canMappings"
TOPOLOGY_SOURCE_LOCAL = "local"
AUDIT_ACTION_SAVE = "save"
AUDIT_ACTION_RECOVER = "recover"
AUDIT_ACTION_REPAIR = "repair"
HELP_TOPIC_DEVICE_USAGE = "device-usage"
HELP_DEVICE_USAGE_TEXT = "show device-usage <device>\n  Show local group/test references for a device."
HELP_TOPIC_SOURCES = "sources"
HELP_SOURCES_TEXT = (
    "show sources\n"
    "load sources\n"
    "save sources\n"
    "  Show and reload/save CLI data sources (show supports robot/local/both)."
)
HELP_TOPIC_PROFILE_DEVICE_DELETE = "profile device delete"
HELP_PROFILE_DEVICE_DELETE_TEXT = (
    "profile device delete <device>\n  Remove a device label from the active profile."
)
HELP_TOPIC_PROFILE_DEVICE_SHOW_ALL = "profile device show-all"
HELP_PROFILE_DEVICE_SHOW_ALL_TEXT = (
    "profile device show-all <device>\n  Show all profile device entries matching a label."
)
HELP_TOPIC_PROFILE_DELETE = "profile delete"
HELP_PROFILE_DELETE_TEXT = (
    "profile delete <profile>\n  Delete a profile from the registry and local config."
)
HELP_TOPIC_PROFILE_EXPORT = "profile export"
HELP_PROFILE_EXPORT_TEXT = (
    "profile export <profile> <path> [--install-robot]\n"
    "  Write a JSON snapshot plus CLI script for the profile.\n"
    "  --install-robot appends robot push, verify, and test-run commands.\n"
    "  Includes global bindings and CAN mappings.\n"
    "  If <path> is a directory, files are created under it."
)
HELP_TOPIC_PROFILE_DEFAULT = "profile default"
HELP_PROFILE_DEFAULT_TEXT = (
    "profile default <profile>\n  Set the default profile name in bringup_system.json."
)
HELP_TOPIC_PROFILES_PUSH = "profiles push"
HELP_PROFILES_PUSH_TEXT = (
    "profiles push <path> [--activate <profile>]\n  Push profiles/devices registry to the robot REST server.\n"
    "profiles reload\n  Reload bringup_system.json on the robot (drops in-memory profiles).\n"
    "profiles activate <profile>\n  Compatibility alias for runtime activate <profile>."
)
HELP_TOPIC_PROFILES_RELOAD = "profiles reload"
HELP_PROFILES_RELOAD_TEXT = (
    "profiles reload\n"
    "  Reload bringup_system.json on the robot (drops in-memory profiles).\n"
    "  Use runtime activate to apply the selected profile after reload."
)
HELP_TOPIC_RUNTIME = "runtime"
HELP_RUNTIME_TEXT = (
    "runtime activate [<profile>]\n"
    "  Activate the selected profile runtime, or select and activate <profile>.\n"
    "runtime deactivate\n"
    "  Deactivate the active runtime without changing the selected profile."
)
HELP_TOPIC_LIFECYCLE = "lifecycle"
HELP_LIFECYCLE_TEXT = (
    "lifecycle activate <label> [mode <mode>]\n"
    "  Activate the current scope membership for one device or group label.\n"
    "lifecycle deactivate <label>\n"
    "  Deactivate the active scope session when it matches <label>.\n"
    "lifecycle deactivate-active\n"
    "  Deactivate whichever scope session is active now.\n"
    "show lifecycle-state [--json] [--pretty]\n"
    "  Show the robot scope-state snapshot."
)
HELP_TOPIC_PROFILES_INIT = "profiles init"
HELP_PROFILES_INIT_TEXT = (
    "profiles init\n  Initialize an empty profiles payload in memory."
)
HELP_TOPIC_PROFILES_EXPORT = "profiles export"
HELP_PROFILES_EXPORT_TEXT = (
    "profiles export <path>\n  Write a JSON snapshot plus CLI script for all profiles.\n"
    "  Includes global bindings and CAN mappings."
)
HELP_TOPIC_CONFIG_PUSH = "config push"
HELP_CONFIG_PUSH_TEXT = (
    "config push <path> [--activate <profile>]\n"
    "  Push registry then import groups/bindings.\n"
    "  By default this updates selection/config only; use --activate for explicit runtime activation."
)
HELP_TOPIC_RESET_ZERO_CONFIG = "reset zero-config"
HELP_RESET_ZERO_CONFIG_TEXT = (
    "reset zero-config [--yes] [--clear-memory]\n"
    "  Delete src/main/deploy/bringup_system.json.\n"
    "  Prompts for y/N unless --yes is provided.\n"
    "  Use --clear-memory to also clear in-memory local config/tests/groups."
)
HELP_TOPIC_RECOVER = "recover"
HELP_RECOVER_TEXT = (
    "recover list\n"
    "recover last-good\n"
    "recover from <timestamp>\n"
    "  Load a snapshot into memory; use `save sources` to persist."
)
HELP_TOPIC_VALIDATE_FILE = "validate file"
HELP_VALIDATE_FILE_TEXT = (
    "validate file <path> [--repair]\n"
    "  Validate a profiles payload file; use --repair to fix missing keys."
)
HELP_TOPIC_QUICK = "quick"
HELP_SHOW_TEXT = (
    "show <status|groups|group <group>|devices|device <device>|device-group <device>|"
    "device-usage <device>|signals|signal <device>|commands|help|bindings|active|instantiated|faults|selected-device|safety-latch|runtime-state|config|config local-raw|config dirty|"
    "sources|profiles|profile|tests|test <test>|message-level|workspace|controllers> "
    "[--json] [--pretty] [robot|local|both]\n"
    "  Defaults: robot if connected, otherwise local.\n"
    "  Note: some targets are local-only (e.g., workspace)."
)
HELP_TIU_TEXT = (
    "tiu on\n"
    "  Enable the terminal information utility dashboard while preserving normal CLI commands.\n"
    "tiu off\n"
    "  Return to the normal CLI presentation."
)
HELP_DIAGNOSE_TEXT = (
    "diagnose motor <label>\n"
    "diagnose device <label>\n"
    "  Analyze runtime telemetry to explain why a motor is not running."
)
MESSAGE_AUTO_MERGE_FAIL = "WARNING: Failed to auto-load default profiles: {path}"
MESSAGE_AUTO_MERGE_OK = "Loaded default profiles: {path}"
MESSAGE_PROFILE_CONTEXT_SYNC_FMT = "Profile context -> {profile}"
MESSAGE_PROFILE_CONTEXT_MISMATCH_FMT = (
    "Robot selected profile is '{robot}', but host context is '{host}'. "
    "Switch host context to the robot profile?"
)
MESSAGE_PROFILE_CONTEXT_BATCH_SYNC_FMT = (
    "WARNING: Robot selected profile is '{robot}', but host context is '{host}'. "
    "Using robot profile for this session."
)
MESSAGE_PROFILE_CONTEXT_MISSING_LOCAL_FMT = (
    "WARNING: Robot selected profile '{robot}' is not available in local profiles; "
    "keeping host context '{host}'."
)
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
MESSAGE_ERR_PROFILE_REQUIRED = "ERROR: Profile not selected. Use 'profile <profile>'."
MESSAGE_PROFILE_DELETE_OK = "Deleted profile: {name}."
MESSAGE_PROFILE_DELETE_MISSING = "WARNING: Profile not found: {name}."
MESSAGE_PROFILE_DELETE_CONFIRM = "Delete profile '{name}'?"
MESSAGE_ERR_PLAN = "ERROR: {message}"
MESSAGE_ERR_PROFILE_UNKNOWN = "ERROR: Profile not found: {name}."
MESSAGE_PROFILE_DEFAULT_SET = "Default profile: {name}."
MESSAGE_ERR_PROFILES_PUSH_PATH = "ERROR: profiles push requires a path."
MESSAGE_ERR_PROFILES_EXPORT_PATH = "ERROR: profiles export <path>"
MESSAGE_ERR_PROFILES_PUSH_READ = "ERROR: Failed to read profiles JSON: {path}."
MESSAGE_ERR_PROFILES_PUSH_PARSE = "ERROR: Invalid profiles JSON: {detail}."
MESSAGE_ERR_PROFILES_PUSH_VALIDATE = "ERROR: Profiles validation failed: {detail}."
MESSAGE_ERR_PROFILES_PUSH_SEND = "ERROR: Failed to send profiles apply command."
MESSAGE_ERR_PROFILES_PUSH_ACTIVATE = "ERROR: Invalid activate profile: {profile}."
MESSAGE_INFO_PROFILES_PUSH_LOCAL = "Loaded profiles from {path}."
MESSAGE_INFO_CONFIG_PUSH_START = "Pushing registry then groups from {path}."

FIELD_MANUFACTURER = "manufacturer"
FIELD_DEVICE_TYPE = "deviceType"
FIELD_DEVICE_ID = "deviceId"
FIELD_ID = "id"
FIELD_DEVICE_INTERFACE = KEY_INTERFACE
FIELD_LABEL = "label"
FIELD_TYPE = "type"
FIELD_MODEL = "model"
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
    INTERFACE_USB,
}

DEVICE_FIELDS_PROFILE = {
    FIELD_DEVICE_INTERFACE,
    FIELD_MANUFACTURER,
    FIELD_DEVICE_TYPE,
    FIELD_ID,
    FIELD_MODEL,
    FIELD_TYPE,
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
    FIELD_DEVICE_INTERFACE: DEVICE_FIELD_STR,
    FIELD_MANUFACTURER: DEVICE_FIELD_INT,
    FIELD_DEVICE_TYPE: DEVICE_FIELD_INT,
    FIELD_ID: DEVICE_FIELD_INT,
    FIELD_MODEL: DEVICE_FIELD_STR,
    FIELD_TYPE: DEVICE_FIELD_STR,
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

DEVICE_REQUIRED_CAN = (FIELD_DEVICE_INTERFACE, FIELD_MANUFACTURER, FIELD_DEVICE_TYPE, FIELD_ID)
DEVICE_REQUIRED_DIO = (FIELD_DEVICE_INTERFACE, FIELD_ID, FIELD_INVERT)
DEVICE_REQUIRED_PWM = (FIELD_DEVICE_INTERFACE, FIELD_PWM)
DEVICE_REQUIRED_ANALOG = (FIELD_DEVICE_INTERFACE, FIELD_ANALOG)
DEVICE_REQUIRED_INTERNAL = (FIELD_DEVICE_INTERFACE,)
DEVICE_REQUIRED_USB = (FIELD_DEVICE_INTERFACE, FIELD_ID)

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
    KEY_SCHEMA_VERSION: PROFILE_SCHEMA_VERSION,
    KEY_CONTROLLERS: [],
    KEY_BINDINGS: [],
    KEY_INPUT_ALIASES: {},
}
BINDINGS_SHOW_CONTROLLERS = "controllers"
BINDINGS_SHOW_BINDINGS = "bindings"
BINDINGS_SHOW_TARGETS = {BINDINGS_SHOW_CONTROLLERS, BINDINGS_SHOW_BINDINGS}
BINDINGS_CONTROLLER_FIELDS = {FIELD_TYPE, KEY_PORT, KEY_NAME}
BINDINGS_BINDING_FIELDS = {KEY_COMMAND, KEY_CONTROLLER, KEY_INPUT, KEY_ID, KEY_MODE, KEY_INVERT, KEY_DEADBAND}
BINDINGS_INPUT_KINDS = {"button", "dpad", "combo", "axis"}
BINDINGS_AXIS_MODE = "analog"

MAPPINGS_SHOW_MANUFACTURERS = "manufacturers"
MAPPINGS_SHOW_DEVICE_TYPES = "device-types"
MAPPINGS_SHOW_DEVICE_TYPE = "device-type"
MAPPINGS_SHOW_TARGETS = {MAPPINGS_SHOW_MANUFACTURERS, MAPPINGS_SHOW_DEVICE_TYPES, MAPPINGS_SHOW_DEVICE_TYPE}

TESTS_TEMPLATES_SUFFIX = ".json"

MESSAGE_ERROR_TEST_SUBCOMMAND = "ERROR: test requires a subcommand."
MESSAGE_ERROR_TEST_SET_NAME = "ERROR: test set requires a name."
MESSAGE_ERROR_TEST_EXISTS = "ERROR: Test already exists."
MESSAGE_ERROR_TEST_NOT_FOUND = "ERROR: Test not found."
MESSAGE_ERROR_UNKNOWN_TEST = "ERROR: Unknown test command."
MESSAGE_ERROR_INVALID_TEST_COMMAND = "ERROR: Invalid test authoring command."
MESSAGE_ERROR_LEGACY_TEST_AUTHORING_REMOVED = (
    "ERROR: legacy local test authoring was removed. "
    "Use tools/can_nt/scripts/dsl_tests_config_tool.py for DSL import/export/validate."
)
MESSAGE_ERROR_DSL_CLI_USAGE = "ERROR: test new|import|copy|export|validate|delete|cleanup|set ..."
MESSAGE_ERROR_DSL_SHOW_USAGE = "ERROR: show tests | show test <name> [normalized] | show test sets | show test library"
MESSAGE_ERROR_DSL_PROFILE_REQUIRED = "ERROR: active profile required."
MESSAGE_ERROR_DSL_CONFIG_REQUIRED = "ERROR: local bringup_system.json must be loaded first (merge/import config)."
MESSAGE_ERROR_DSL_TEST_NOT_FOUND = "ERROR: test not found: {name}"
MESSAGE_ERROR_DSL_SET_NOT_FOUND = "ERROR: test set not found: {name}"
MESSAGE_ERROR_DSL_PROFILE_UNKNOWN = "ERROR: unknown profile: {name}"
MESSAGE_ERROR_DSL_LOCAL_ONLY = "ERROR: DSL show commands are local-only."
MESSAGE_DSL_TEST_CREATED = "Created DSL test: {name}"
MESSAGE_DSL_TEST_IMPORTED = "Imported DSL test: {name}"
MESSAGE_DSL_TEST_COPIED = "Copied DSL test {source} -> {target}"
MESSAGE_DSL_TEST_IMPORTED_GLOBAL = "Imported external global DSL test: {name}"
MESSAGE_DSL_TEST_IMPORTED_CONFIG = "Imported config library DSL test: {name}"
MESSAGE_DSL_TEST_COPIED_GLOBAL = "Copied external global DSL test {source} -> {target} ({destination})"
MESSAGE_DSL_TEST_RENAMED = "Renamed DSL test {source} -> {target}"
MESSAGE_DSL_TEST_RENAMED_GLOBAL = "Renamed external global DSL test {source} -> {target}"
MESSAGE_DSL_TEST_DELETED_ARCHIVED = "Deleted DSL test {name} (archived to {path})"
MESSAGE_DSL_TEST_DELETED_GLOBAL_ARCHIVED = "Deleted external global DSL test {name} (archived to {path})"
MESSAGE_DSL_TEST_DELETED = "Deleted DSL test: {name}"
MESSAGE_DSL_SET_CREATED = "Created test set: {name}"
MESSAGE_DSL_SET_DELETED = "Deleted test set: {name}"
MESSAGE_DSL_SET_DEFAULT = "Default test set: {name}"
MESSAGE_DSL_SET_MEMBER_ADDED = "Added test {test} to set {name}"
MESSAGE_DSL_SET_MEMBER_REMOVED = "Removed test {test} from set {name}"
MESSAGE_DSL_TEST_EXPORTED = "Exported DSL test: {name}"
MESSAGE_DSL_TESTS_CLEANED = "Removed stale DSL tests: {names}"
MESSAGE_DSL_TESTS_CLEAN_NONE = "No stale DSL tests found."
MESSAGE_DSL_LIBRARY_GLOBAL_HEADER = "external global library:"
MESSAGE_DSL_LIBRARY_CONFIG_HEADER = "config library set: {name}"
MESSAGE_DSL_PROFILE_SET_HEADER = "profile test set: {name}"
MESSAGE_DSL_NONE = "(none)"
MESSAGE_DSL_VALIDATION_LINE_FMT = "line {line}: {text}"
MESSAGE_DSL_VALIDATION_FIELD_FMT = "field {field}"
DSL_VALIDATION_META_FIELDS = {"source", "normalized", "sourceHash", "devices", "testSets"}
ROBOT_TEST_DSL_SIGNALS_PATH = repo_root() / "tools" / "common" / "generated" / "robot_test_dsl_signals.json"
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
MESSAGE_ERROR_SHOW_TESTS = "ERROR: show tests | show test <test>"
MESSAGE_SELECTED_TEST_SET = "Selected test set: {name}"
MESSAGE_CANCELLED = "Cancelled."
MESSAGE_DELETED_TEST = "Deleted test: {name}"
MESSAGE_WROTE_TESTS = "Wrote tests to {path}."
MESSAGE_ERR_TESTS_STANDALONE = (
    "ERROR: Standalone tests files are not supported. "
    "Use bringup_system.json and `save config <path>`."
)
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
MESSAGE_TEST_OBSERVERS = "  observers: {devices}"
MESSAGE_TEST_CREATED_DEVICES = "  createdDevices: {devices}"
MESSAGE_TEST_COMMANDS = "  commands: {items}"
MESSAGE_TEST_UNTIL = "  until: {items}"
MESSAGE_TEST_EXPECT = "  expect: {items}"
MESSAGE_TEST_SUCCESS = "  success: {items}"
MESSAGE_TEST_ABORT = "  abort: {items}"
MESSAGE_TEST_PASSIVE = "  passive: {value}"
MESSAGE_TEST_MANUAL_STOP = "  manualStop: {value}"
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
MESSAGE_ERROR_DSL_DEVICE_ROLE = "ERROR: device add role must be primary or observer."
MESSAGE_ERROR_DSL_DEVICE_CREATE = "ERROR: device create <name> type TestTimer"
MESSAGE_ERROR_DSL_COMMAND = "ERROR: command <signal> = <value>"
MESSAGE_ERROR_DSL_CONDITION = "ERROR: {kind} <signal> <operator> <value>"
MESSAGE_ERROR_DSL_OPERATOR = "ERROR: invalid operator."
MESSAGE_ERROR_DSL_BOOLEAN = "ERROR: boolean value must be true or false."
MESSAGE_ERROR_DSL_PASSIVE = "ERROR: passive requires true/false."
MESSAGE_ERROR_DSL_MANUAL_STOP = "ERROR: manual_stop requires true/false."
MESSAGE_ERROR_DSL_CREATED_DEVICE_EXISTS = "ERROR: created device already exists."
MESSAGE_ERROR_DSL_CREATED_DEVICE_RESERVED = "ERROR: created device name is reserved."
MESSAGE_ERROR_DSL_CREATED_DEVICE_COLLISION = "ERROR: created device collides with bound device."

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
        recovery_mode: bool = False,
        visibility_provider: Optional[object] = None,
        runtime_details_provider: Optional[Callable[[], Dict[str, Any]]] = None,
    ) -> None:
        self._session = session
        self._batch = batch
        self._conflict_policy = conflict_policy
        self._echo_enabled = echo_enabled
        self._message_level = MESSAGE_LEVEL_BEGINNER
        self._message_level_from_flag = False
        self._tips_suppressed: set[str] = set()
        self._warnings: List[str] = []
        self._recovery_mode = recovery_mode
        # Optional helpers injected by can_nt_bridge (safe to be None).
        self._visibility_provider = visibility_provider
        self._runtime_details_provider = runtime_details_provider
        self._tests_device_catalog: Dict[str, object] = {}
        self._tests_duplicate_labels: set[str] = set()
        self._parser_kind = CLI_PARSER_KIND
        self._parser = BridgeCliParser(strict=bool(CLI_PARSER_CONST["strict_default"]))
        self._ast_executor = BridgeCliAstExecutor(self)
        self._modes: List[CliMode] = [CliMode("exec")]
        self._parse_facade = BridgeCliParseFacade()
        self._validate_facade = BridgeCliValidateFacade()
        self._execute_facade = BridgeCliExecuteFacade()
        self._output_facade = BridgeCliOutputFacade()
        self._config_lifecycle = ConfigLifecycleService()
        self._config_repository = ConfigRepository(self._config_lifecycle)
        self._workflow01 = Workflow01Service()
        self._parse_context = BridgeCliParseContext(
            parse_line=lambda line, mode: self._parser.parse(line, mode=mode),
            split_command=self._split_command,
            maybe_print_failure_hint=self._maybe_print_failure_hint,
            alias_replacement=self._alias_replacement,
            print_alias_removed=self._print_alias_removed,
            normalize_tokens=lambda tokens, mode: self._parser.normalize_tokens(tokens, mode),
            fallback_device_set=self._fallback_device_set,
            config_command=self._config_command,
            coerce_status=self._coerce_status,
            mode_name=self._modes[-1].name,
        )
        self._robot_control_transport = BridgeRobotControlTransport(
            send_command=lambda command_name, command_args: self._session.send_command(command_name, command_args),
            mark_command_sent=lambda command_name, now: self._proto_mark_cmd_sent(command_name, now=now),
            wait_for_seq=self._wait_for_seq,
            event_failed=self._event_failed,
            handle_add_device_conflict=self._handle_add_device_conflict,
        )
        self._last_seq: Optional[int] = None
        self._local_config: Optional[Dict[str, object]] = None
        self._local_config_path: Optional[str] = None
        self._local_loaded_at: Optional[float] = None
        self._local_root_payload: Optional[Dict[str, object]] = None
        self._local_root_path: Optional[str] = None
        self._local_root_hash: Optional[str] = None
        self._last_modified_at: Optional[float] = None
        self._last_saved_at: Optional[float] = None
        self._last_saved_path: Optional[str] = None
        self._last_saved_hash: Optional[str] = None
        self._last_pushed_at: Optional[float] = None
        self._last_pushed_path: Optional[str] = None
        self._last_pushed_hash: Optional[str] = None
        self._last_pushed_profile: Optional[str] = None
        self._show_label_seq: Dict[int, str] = {}
        self._show_pretty_json_seq: Dict[int, bool] = {}
        self._last_show_pretty: bool = False
        self._last_line_pretty: bool = False
        self._local_devices_locked: bool = False
        self._profiles_dirty: bool = False
        self._groups_dirty: bool = False
        self._active_group_members: List[str] = []
        self._active_add_cursor: int = COUNT_ZERO
        self._tracker = CommandTracker(timeout_sec=2.0, max_retries=0)
        self._store = ConfigSchemaStore()
        self._tests_model: Optional[TestAuthoringModel] = None
        self._tests_dirty: bool = False
        self._tests_active_set: str = ""
        self._tests_profile: Optional[str] = None
        self._last_test_run_id: Optional[int] = None
        self._load_message_level(message_level)
        self._groups_profile: Optional[str] = None
        self._robot_selected_profile: Optional[str] = None
        self._profile_context_mismatch_seen: Optional[Tuple[str, str]] = None
        self._pending_prompt_text: Optional[str] = None
        self._use_prompt_toolkit: bool = PROMPT_TOOLKIT_AVAILABLE
        self._warned_prompt_toolkit: bool = False
        self._warned_history: bool = False
        self._prompt_session = self._build_prompt_session()
        self._tiu_enabled: bool = False
        self._tiu_recent_events: List[str] = []
        self._tiu_cli_output: List[str] = []
        self._tiu_runtime_cache: Optional[Dict[str, object]] = None
        self._tiu_runtime_cache_at: float = 0.0
        self._tiu_app: Optional[object] = None
        self._tiu_dashboard_view: Optional[object] = None
        self._tiu_output_view: Optional[object] = None
        self._tiu_input_view: Optional[object] = None
        self._tiu_exit_code: Optional[int] = None
        self._tiu_output_follow_tail: bool = True
        self._can_mappings: Optional[Dict[str, Dict[str, str]]] = None
        self._can_mappings_path: Optional[Path] = None
        self._can_mappings_dirty: bool = False
        self._bindings_payload: Optional[Dict[str, object]] = deepcopy(BINDINGS_EMPTY_PAYLOAD)
        self._bindings_path: Optional[Path] = None
        self._bindings_dirty: bool = False
        self._store.set_bindings_payload(self._bindings_payload)
        self._version_printed = False
        self._keepalive_stop = threading.Event()
        self._keepalive_thread: Optional[threading.Thread] = None
        self._proto_connect_attempts = COUNT_ZERO
        self._proto_connect_failures = COUNT_ZERO
        self._proto_connect_successes = COUNT_ZERO
        self._proto_last_connect_at = PROTO_TIME_ZERO
        self._proto_last_disconnect_at = PROTO_TIME_ZERO
        self._proto_handshake_count = COUNT_ZERO
        self._proto_last_handshake_at = PROTO_TIME_ZERO
        self._proto_cmd_sent = COUNT_ZERO
        self._proto_cmd_last = EMPTY_STRING
        self._proto_cmd_last_at = PROTO_TIME_ZERO
        self._proto_ack_count = COUNT_ZERO
        self._proto_last_ack_at = PROTO_TIME_ZERO
        self._proto_last_ack_seq = PROTO_LAST_SEQ_INIT
        self._proto_out_count = COUNT_ZERO
        self._proto_last_out_at = PROTO_TIME_ZERO
        self._proto_last_out_seq = PROTO_LAST_SEQ_INIT
        self._proto_timeout_count = COUNT_ZERO
        self._proto_last_timeout_at = PROTO_TIME_ZERO
        self._proto_keepalive_sent = COUNT_ZERO
        self._proto_keepalive_fail = COUNT_ZERO
        self._proto_keepalive_ack = COUNT_ZERO
        self._proto_keepalive_out = COUNT_ZERO
        self._proto_keepalive_last_sent_at = PROTO_TIME_ZERO
        self._proto_keepalive_last_ack_at = PROTO_TIME_ZERO
        self._proto_keepalive_last_out_at = PROTO_TIME_ZERO
        trace_setter = getattr(self._session, "set_trace_logger", None)
        if callable(trace_setter):
            trace_setter(self._debug_log)

    def run_interactive(self) -> int:
        """
        NAME
            run_interactive - Enter the interactive prompt loop.
        """
        self._print_version_banner()
        self._auto_merge_default_profiles()
        self._auto_load_default_sources()
        try:
            while True:
                try:
                    if self._tiu_enabled:
                        tiu_exit_code = self._run_tiu_application()
                        if tiu_exit_code is not None:
                            return tiu_exit_code
                        continue
                    else:
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
                    result = self._execute_line("exit")
                    self._emit_status(result)
                    if result.exit_requested:
                        return result.exit_code()
                    continue
                except KeyboardInterrupt:
                    print()
                    continue
                line = line.strip()
                if not line:
                    continue
                result = self._execute_line_with_tiu_capture(line)
                if result.exit_requested:
                    return result.exit_code()
                if not result.ok():
                    self._warn("WARNING: Command failed; staying in CLI.")
                    continue
        finally:
            self._shutdown_session()

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
        try:
            completer = self._build_completer()
            return PromptSession(
                history=FileHistory(str(history_path)),
                completer=completer,
                complete_while_typing=COMPLETION_WHILE_TYPING,
            )
        except Exception:
            if not self._warned_prompt_toolkit:
                print(MESSAGE_WARN_PROMPT_TOOLKIT_NO_CONSOLE)
                self._warned_prompt_toolkit = True
            return None

    def _start_keepalive(self) -> None:
        """
        NAME
            _start_keepalive - Start the background UI keepalive loop.

        DESCRIPTION
            Sends periodic uiPing messages to prevent REST session timeout.
        """
        if self._keepalive_thread is not None and self._keepalive_thread.is_alive():
            return
        self._keepalive_stop.clear()
        thread = threading.Thread(
            target=self._keepalive_loop,
            name=KEEPALIVE_THREAD_NAME,
            daemon=True,
        )
        self._keepalive_thread = thread
        thread.start()
        self._keepalive_log(MESSAGE_KEEPALIVE_THREAD_START)

    def _stop_keepalive(self) -> None:
        """
        NAME
            _stop_keepalive - Stop the background UI keepalive loop.
        """
        if self._keepalive_thread is None:
            return
        self._keepalive_stop.set()
        self._keepalive_thread.join(timeout=KEEPALIVE_JOIN_TIMEOUT_SEC)
        if not self._keepalive_thread.is_alive():
            self._keepalive_thread = None
            self._keepalive_log(MESSAGE_KEEPALIVE_THREAD_STOP)

    def _keepalive_loop(self) -> None:
        """
        NAME
            _keepalive_loop - Background uiPing loop for CLI sessions.

        DESCRIPTION
            Periodically sends uiPing while the REST session is connected.
        """
        last_ping = KEEPALIVE_LAST_INIT
        was_connected: Optional[bool] = None
        while not self._keepalive_stop.is_set():
            is_connected = self._session.is_connected()
            if was_connected is None or was_connected != is_connected:
                if is_connected:
                    self._keepalive_log(MESSAGE_KEEPALIVE_STATE_CONNECTED)
                    self._proto_mark_tcp_state(now=time.time(), connected=True)
                else:
                    self._keepalive_log(MESSAGE_KEEPALIVE_STATE_DISCONNECTED)
                    self._proto_mark_tcp_state(now=time.time(), connected=False)
                was_connected = is_connected
            if not is_connected:
                self._keepalive_stop.wait(KEEPALIVE_DISCONNECTED_WAIT_SEC)
                continue
            now = time.time()
            if (now - last_ping) >= KEEPALIVE_INTERVAL_SEC:
                seq = ui_ping(self._session)
                if seq is not None:
                    last_ping = now
                    self._proto_mark_keepalive_sent(seq=seq, now=now, ok=True)
                else:
                    self._keepalive_log(MESSAGE_KEEPALIVE_SEND_FAIL)
                    self._proto_mark_keepalive_sent(seq=PROTO_LAST_SEQ_INIT, now=now, ok=False)
            self._keepalive_stop.wait(KEEPALIVE_SLEEP_SEC)

    def _build_completer(self) -> Optional[object]:
        """
        NAME
            _build_completer - Build a prompt_toolkit completer if available.
        """
        if not COMPLETION_ENABLED:
            return None
        if Completer is None or Completion is None:
            if not self._warned_prompt_toolkit:
                print(MESSAGE_WARN_COMPLETION_DISABLED)
                self._warned_prompt_toolkit = True
            return None
        return BridgeCliCompleter(self)

    def run_batch(self, lines: List[str]) -> int:
        """
        NAME
            run_batch - Execute a batch script.
        """
        self._print_version_banner()
        self._auto_merge_default_profiles()
        self._auto_load_default_sources()
        try:
            lint_error = self._lint_script(lines)
            if lint_error:
                print(f"ERROR: {lint_error}")
                result = StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX, message=str(lint_error))
                self._emit_status(result)
                return result.exit_code()
            for raw in lines:
                line = raw.strip()
                if line.startswith("\ufeff"):
                    line = line.lstrip("\ufeff").lstrip()
                if not line or line.startswith("#"):
                    continue
                if self._echo_enabled:
                    print(f">> {line}")
                result = self._execute_line(line)
                self._emit_status(result)
                if result.exit_requested:
                    return result.exit_code()
                if not result.ok():
                    return result.exit_code()
            return StatusResult(code=SS__NORMAL).exit_code()
        finally:
            self._shutdown_session()

    def _shutdown_session(self) -> None:
        """
        NAME
            _shutdown_session - Stop keepalive and release the owned REST session.

        DESCRIPTION
            Mirrors the explicit `disconnect` command during CLI process exit so
            a terminated CLI does not leave the robot-side control session owned
            until timeout or manual reset.
        """
        self._stop_keepalive()
        disconnect(self._session)

    def _print_version_banner(self) -> None:
        """
        NAME
            _print_version_banner - Print bridge CLI version once.
        """
        if self._version_printed:
            return
        self._version_printed = True
        version = VERSIONS.get(VERSION_APP_NAME, EMPTY_STRING)
        if not version:
            return
        print(VERSION_TITLE)
        print(format_version_line(VERSION_APP_NAME, version))
        for line in build_lines():
            print(line)

    def _prompt(self) -> str:
        mode = self._modes[-1]
        if mode.name == "exec":
            if not self._session.is_connected():
                return self._decorate_prompt_dirty(
                    self._decorate_prompt_tiu(PROMPT_EXEC_DISCONNECTED)
                )
            suffix = self._profile_prompt_suffix(use_active=True)
            if suffix:
                prompt = PROMPT_EXEC_WITH_PROFILE_FMT.format(suffix=suffix)
            else:
                prompt = PROMPT_EXEC
            return self._decorate_prompt_dirty(self._decorate_prompt_tiu(prompt))
        if mode.name == MODE_CONFIG:
            suffix = self._profile_prompt_suffix()
            return self._decorate_prompt_dirty(self._decorate_prompt_tiu(f"{PROMPT_CONFIG_PREFIX}{suffix}{PROMPT_SUFFIX}"))
        if mode.name == "group":
            suffix = self._profile_prompt_suffix()
            return self._decorate_prompt_dirty(self._decorate_prompt_tiu(f"{PROMPT_CONFIG_PREFIX}{suffix}{PROMPT_GROUP_SEGMENT}{mode.group}{PROMPT_SUFFIX}"))
        if mode.name == "device":
            return self._decorate_prompt_dirty(self._decorate_prompt_tiu(f"{PROMPT_DEVICE_PREFIX}{mode.device}{PROMPT_SUFFIX}"))
        if mode.name == MODE_TEST:
            label = mode.test or TEST_LABEL_UNKNOWN
            return self._decorate_prompt_dirty(self._decorate_prompt_tiu(f"{PROMPT_TEST_PREFIX}{label}{PROMPT_SUFFIX}"))
        return self._decorate_prompt_dirty(self._decorate_prompt_tiu(PROMPT_EXEC))

    def _profile_prompt_suffix(self, use_active: bool = False) -> str:
        """
        NAME
            _profile_prompt_suffix - Render prompt suffix for active profile.
        """
        profile = EMPTY_STRING
        if use_active and self._session.is_connected():
            profile = self._robot_selected_profile or EMPTY_STRING
        else:
            profile = self._groups_profile or EMPTY_STRING
            if use_active and not profile:
                profile = self._active_profile_name() or EMPTY_STRING
        if profile:
            return f"{PROMPT_PROFILE_PREFIX}{profile}"
        return ""

    def _host_profile_context_name(self) -> str:
        """
        NAME
            _host_profile_context_name - Return the current host-side profile context.
        """
        return str(self._groups_profile or EMPTY_STRING).strip()

    @staticmethod
    def _normalize_profile_context_name(value: object) -> str:
        """
        NAME
            _normalize_profile_context_name - Normalize one profile name for host/robot comparison.
        """
        return normalize_profile_name(value)

    @staticmethod
    def _selected_profile_from_show_profiles_payload(payload: object) -> str:
        """
        NAME
            _selected_profile_from_show_profiles_payload - Parse selected profile from showProfiles JSON.
        """
        if not isinstance(payload, dict):
            return EMPTY_STRING
        profile = payload.get(KEY_PROFILE)
        if not isinstance(profile, dict):
            return EMPTY_STRING
        return BridgeCli._normalize_profile_context_name(profile.get("selected"))

    @staticmethod
    def _selected_profile_from_show_profiles_text(text: object) -> str:
        """
        NAME
            _selected_profile_from_show_profiles_text - Parse selected profile from text showProfiles output.
        """
        if not isinstance(text, str):
            return EMPTY_STRING
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line.startswith("selected="):
                continue
            return BridgeCli._normalize_profile_context_name(line.split("=", 1)[1])
        return EMPTY_STRING

    def _apply_host_profile_context(self, name: str, announce: bool) -> None:
        """
        NAME
            _apply_host_profile_context - Switch the host profile context without mutating the robot.
        """
        key = normalize_profile_name(name)
        profiles = self._local_root_payload.get(KEY_PROFILES) if isinstance(self._local_root_payload, dict) else None
        if not key or not isinstance(profiles, dict) or key not in profiles:
            return
        self._groups_profile = key
        self._local_profile_entry(key, create=True)
        self._refresh_tests_profile(key)
        if announce:
            print(MESSAGE_PROFILE_CONTEXT_SYNC_FMT.format(profile=key))

    def _has_dirty_state(self) -> bool:
        """
        NAME
            _has_dirty_state - Return whether any local section is dirty.
        """
        return any(bool(flag) for flag in self._current_dirty_flags().values())

    def _decorate_prompt_dirty(self, prompt: str) -> str:
        """
        NAME
            _decorate_prompt_dirty - Add a dirty marker to the prompt label.
        """
        if not self._has_dirty_state():
            return prompt
        return prompt.replace(PROMPT_LABEL_BRIDGE, PROMPT_LABEL_BRIDGE + PROMPT_DIRTY_MARK, COUNT_ONE)

    def _decorate_prompt_tiu(self, prompt: str) -> str:
        """
        NAME
            _decorate_prompt_tiu - Add TIU mode marker to the prompt label.
        """
        if not self._tiu_enabled:
            return prompt
        return prompt.replace(PROMPT_LABEL_BRIDGE, PROMPT_LABEL_BRIDGE + "(tiu)", COUNT_ONE)

    def _record_last_modified(self) -> None:
        """
        NAME
            _record_last_modified - Update in-memory modification timestamp.
        """
        self._last_modified_at = time.time()

    def _mark_profiles_dirty(self) -> None:
        """
        NAME
            _mark_profiles_dirty - Mark local profiles state dirty.
        """
        self._profiles_dirty = True
        self._record_last_modified()

    def _mark_bindings_dirty(self) -> None:
        """
        NAME
            _mark_bindings_dirty - Mark local bindings state dirty.
        """
        self._bindings_dirty = True
        self._record_last_modified()

    def _mark_mappings_dirty(self) -> None:
        """
        NAME
            _mark_mappings_dirty - Mark local mappings state dirty.
        """
        self._can_mappings_dirty = True
        self._record_last_modified()

    def _current_workspace_hash(self) -> str:
        """
        NAME
            _current_workspace_hash - Compute the current local workspace hash when available.
        """
        if not isinstance(self._local_root_payload, dict) or not isinstance(self._local_config, dict):
            return EMPTY_STRING
        payload = dict(self._local_root_payload)
        payload[KEY_BRIDGE_CONFIG] = self._ordered_bridge_config(self._local_config)
        payload[KEY_SCHEMA_VERSION] = PROFILE_SCHEMA_VERSION
        if KEY_DATA_VERSION not in payload:
            payload[KEY_DATA_VERSION] = timestamp_version()
        try:
            return compute_profiles_hash(payload)
        except Exception:
            return EMPTY_STRING

    def _match_label(self, current_hash: str, reference_hash: Optional[str]) -> str:
        """
        NAME
            _match_label - Format a YES/NO/UNKNOWN comparison label for hashes.
        """
        if not current_hash or not reference_hash:
            return MATCH_STATE_UNKNOWN
        return MATCH_STATE_YES if current_hash == reference_hash else MATCH_STATE_NO

    def _format_provenance_value(
        self,
        timestamp: Optional[float],
        path: Optional[str] = None,
        hash_value: Optional[str] = None,
        profile_name: Optional[str] = None,
    ) -> str:
        """
        NAME
            _format_provenance_value - Format one provenance line for text output.
        """
        if timestamp is None:
            return STRING_NONE
        parts = [time.strftime("%H:%M:%S", time.localtime(timestamp))]
        if path:
            parts.append(path)
        if profile_name:
            parts.append(f"profile={profile_name}")
        if hash_value:
            parts.append(f"hash={hash_value[:8]}")
        return SEP_DOUBLE_SPACE.join(parts)

    def _record_last_save(self, path: Path) -> None:
        """
        NAME
            _record_last_save - Record successful local save provenance.
        """
        self._last_saved_at = time.time()
        self._last_saved_path = str(path)
        self._last_saved_hash = self._hash_file(path)

    def _record_last_push(self, path: str, hash_value: str, profile_name: str) -> None:
        """
        NAME
            _record_last_push - Record successful push provenance.
        """
        self._last_pushed_at = time.time()
        self._last_pushed_path = path
        self._last_pushed_hash = hash_value
        self._last_pushed_profile = profile_name

    def _build_provenance_payload(self) -> Dict[str, object]:
        """
        NAME
            _build_provenance_payload - Build provenance summary for workspace/status surfaces.
        """
        current_hash = self._current_workspace_hash()
        return {
            KEY_LAST_MODIFIED_AT: self._last_modified_at,
            KEY_LAST_SAVED: {
                KEY_AT: self._last_saved_at,
                KEY_SOURCE_PATH: self._last_saved_path or EMPTY_STRING,
                KEY_HASH: self._last_saved_hash or EMPTY_STRING,
            },
            KEY_LAST_PUSHED: {
                KEY_AT: self._last_pushed_at,
                KEY_SOURCE_PATH: self._last_pushed_path or EMPTY_STRING,
                KEY_HASH: self._last_pushed_hash or EMPTY_STRING,
                KEY_PROFILE_NAME: self._last_pushed_profile or EMPTY_STRING,
            },
            KEY_MATCH: {
                KEY_LOCAL_VS_SAVED: self._match_label(current_hash, self._last_saved_hash),
                KEY_LOCAL_VS_PUSHED: self._match_label(current_hash, self._last_pushed_hash),
                KEY_ROBOT_VS_PUSHED: MATCH_STATE_YES if self._last_pushed_hash else MATCH_STATE_UNKNOWN,
            },
        }

    def _auto_merge_default_profiles(self) -> None:
        """
        NAME
            _auto_merge_default_profiles - Load the default bringup_system.json if present.
        """
        if self._local_config is not None:
            return
        path = self._config_repository.canonical_path()
        if not path.exists():
            return
        self._load_profiles_from_path(path, announce=True)

    def _auto_merge_default_profiles_for_connect(self) -> None:
        """
        NAME
            _auto_merge_default_profiles_for_connect - Silently load canonical profiles before connect-time sync.
        """
        if self._local_config is not None:
            return
        path = self._config_repository.canonical_path()
        if not path.exists():
            return
        self._load_profiles_from_path(path, announce=False)


    def _auto_load_default_sources(self) -> None:
        """
        NAME
            _auto_load_default_sources - Auto-load default bindings/mappings if present.
        """
        bindings_path = bindings_deploy_path()
        if bindings_path.exists():
            self._load_bindings_from_path(bindings_path, announce=True)
        mappings_path = can_mappings_path()
        if mappings_path.exists():
            self._load_can_mappings_from_path(mappings_path)

    def _load_profiles_from_path(self, path: Path, announce: bool = True) -> StatusResult:
        """
        NAME
            _load_profiles_from_path - Load profiles JSON with salvage-first recovery.
        """

        payload: object = None
        read_failed = False
        if path.exists():
            try:
                payload = self._config_repository.load_path(path).to_payload()
            except Exception:
                read_failed = True
                self._warn(MESSAGE_ERR_PROFILES_PUSH_READ.format(path=path), essential=True)
        sanitized, warnings, changed = self._store.sanitize_profiles_payload(payload)
        self._install_loaded_profiles_payload(path, sanitized)
        self._recovery_mode = bool(read_failed or changed)
        self._profiles_dirty = bool(changed)
        self._groups_dirty = False
        if changed:
            self._local_root_hash = None
        for warning in warnings:
            self._warnings.append(warning)
            self._warn(f"WARNING: {warning}", essential=True)
        if announce:
            print(MESSAGE_AUTO_MERGE_OK.format(path=path))
        return StatusResult(
            code=SS__CONFIG__IMPORTED if not changed and not read_failed else SS__CONFIG__INVALID
        )

    def _install_loaded_profiles_payload(
        self, path: Path, payload: Dict[str, object]
    ) -> None:
        """
        NAME
            _install_loaded_profiles_payload - Install sanitized profiles payload into local CLI state.
        """

        self._local_root_payload = payload
        self._local_root_path = path
        self._local_root_hash = self._profiles_hash(payload)
        self._local_loaded_at = time.time()
        self._local_devices_locked = True
        bridge = payload.get(KEY_BRIDGE_CONFIG)
        self._local_config = dict(bridge) if isinstance(bridge, dict) else None
        self._local_config_path = path
        self._tests_profile = None
        self._tests_model = None
        self._tests_active_set = DEFAULT_TEST_SET
        self._tests_device_catalog = {}
        self._tests_duplicate_labels = set()
        self._sync_group_profile()
        if self._groups_profile:
            self._refresh_tests_profile(self._groups_profile)
        self._sync_store_from_local()

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

    def _connect_target_profile_name(self) -> str:
        """
        NAME
            _connect_target_profile_name - Return the host profile that should be pushed to the robot on connect.

        DESCRIPTION
            Prefers the current host profile context when that profile exists in
            local config. Falls back to empty string when the host has no valid
            local profile context, allowing connect-time robot->host adoption.
        """
        payload = self._local_root_payload
        profiles = payload.get(KEY_PROFILES) if isinstance(payload, dict) else None
        candidate = self._active_profile_name()
        if not isinstance(profiles, dict) or not candidate or candidate not in profiles:
            return EMPTY_STRING
        return candidate

    def _fallback_profile_name(self) -> Optional[str]:
        """
        NAME
            _fallback_profile_name - Legacy profile fallback (disabled).
        """
        return None

    def _ensure_default_profile_context(self) -> None:
        """
        NAME
            _ensure_default_profile_context - Ensure a real profiles default exists.

        DESCRIPTION
            Creates a default profile in the local profiles payload when none is
            present so local editing never falls back to a synthetic legacy profile.
        """
        result = self._ensure_local_profiles_payload()
        if not result.ok():
            return
        payload = self._local_root_payload
        if not isinstance(payload, dict):
            return
        profiles = payload.get(KEY_PROFILES)
        if not isinstance(profiles, dict):
            return
        if not profiles:
            default_name = get_default_profile().strip() or CMD_PROFILE
            create_blank_profile(payload, default_name, set_default_if_missing=True)
            self._mark_profiles_dirty()
        default_profile = payload.get(KEY_DEFAULT_PROFILE)
        if not isinstance(default_profile, str) or default_profile not in profiles:
            set_default_profile_payload(payload, next(iter(profiles.keys())))
        if self._groups_profile:
            if isinstance(self._local_config, dict):
                by_profile = self._local_config.get(KEY_BRIDGE_BY_PROFILE)
                if not isinstance(by_profile, dict):
                    by_profile = {}
                    self._local_config[KEY_BRIDGE_BY_PROFILE] = by_profile
                if self._groups_profile not in by_profile:
                    by_profile[self._groups_profile] = {
                        KEY_BRIDGE_GROUPS: [],
                        KEY_BRIDGE_SELECTED_DEVICE: {KEY_DEVICE: EMPTY_STRING, CMD_ENABLED: False},
                    }

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
            self._tests_model = None
            self._tests_device_catalog = {}
            self._tests_duplicate_labels = set()
            return
        if self._tests_profile and self._tests_profile != profile_name and self._tests_model is not None:
            self._sync_store_tests()
        self._tests_profile = profile_name
        entry = self._local_profile_entry(profile_name, create=True)
        payload = entry.get(KEY_BRIDGE_TESTS)
        if not isinstance(payload, dict):
            payload = {}
        self._tests_model = model_from_payload(payload or {})
        default_set = self._tests_model.default_test_set if self._tests_model else EMPTY_STRING
        self._tests_active_set = default_set or DEFAULT_TEST_SET
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
            name = str(device.get(KEY_LABEL, "")).strip() or str(device.get("name", "")).strip()
            if name:
                labels.add(name.lower())
        return labels

    def _profile_object_labels(self, profile_name: str) -> set[str]:
        """
        NAME
            _profile_object_labels - Return all known object labels for a profile.
        """
        labels = set(self._profile_device_labels(profile_name))
        topology_profile = topology_profile_from_payload(self._local_root_payload, profile_name)
        if isinstance(topology_profile, dict):
            for node in topology_nodes(topology_profile):
                if not isinstance(node, dict):
                    continue
                if get_object_type(node) == NODE_TYPE_DEVICE:
                    value = str(node.get(KEY_DEVICE_REF, EMPTY_STRING)).strip()
                else:
                    value = str(node.get(KEY_LABEL, EMPTY_STRING)).strip()
                if value:
                    labels.add(value.lower())
        diagram_root = self._local_root_payload.get(KEY_DIAGRAM) if isinstance(self._local_root_payload, dict) else None
        diagram_profiles = diagram_root.get(KEY_DIAGRAM_PROFILES) if isinstance(diagram_root, dict) else None
        diagram_profile = diagram_profiles.get(profile_name) if isinstance(diagram_profiles, dict) else None
        nodes = diagram_profile.get(KEY_DIAGRAM_NODES) if isinstance(diagram_profile, dict) else None
        if isinstance(nodes, list):
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                value = str(node.get(KEY_LABEL, EMPTY_STRING)).strip()
                if value:
                    labels.add(value.lower())
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
        self._groups_profile = None

    def _set_active_profile(self, name: str) -> StatusResult:
        """
        NAME
            _set_active_profile - Set active profile for local group operations.
        """
        profiles = self._local_root_payload.get(KEY_PROFILES) if isinstance(self._local_root_payload, dict) else None
        key = name.strip()
        if not key:
            print(MESSAGE_ERR_PROFILE_REQUIRED)
            return StatusResult(code=SS__CONFIG__PROFILE_REQUIRED)
        if not isinstance(profiles, dict) or not profiles:
            print(MESSAGE_ERR_PROFILE_UNKNOWN.format(name=name))
            return StatusResult(code=SS__CONFIG__INVALID)
        if key not in profiles:
            print(MESSAGE_ERR_PROFILE_UNKNOWN.format(name=name))
            return StatusResult(code=SS__CONFIG__INVALID)
        if self._session.is_connected():
            seq = select_profile(self._session, key)
            if seq is None:
                print(MESSAGE_ERR_PROFILES_ACTIVATE_SEND)
                return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
            self._proto_mark_cmd_sent("selectProfile", now=time.time())
            event = self._wait_for_seq(seq, timeout_sec=ROBOT_LONG_COMMAND_TIMEOUT_SEC)
            if self._event_failed(event, "selectProfile"):
                return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
            semantic_error = self._profile_select_event_error(event)
            if semantic_error:
                print(semantic_error)
                return StatusResult(code=SS__EXECUTOR__FAILED, message=semantic_error)
            self._robot_selected_profile = key
        self._groups_profile = key
        self._local_profile_entry(key, create=True)
        self._refresh_tests_profile(key)
        return StatusResult(code=SS__NORMAL)

    def _ensure_local_profiles_payload(self) -> StatusResult:
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
                KEY_TOPOLOGY: {
                    KEY_TOPOLOGY_VERSION: COUNT_ONE,
                    KEY_TOPOLOGY_SOURCE: TOPOLOGY_SOURCE_LOCAL,
                    KEY_TOPOLOGY_PROFILES: {},
                },
            }
            self._local_root_hash = None
            self._local_devices_locked = True
            self._mark_profiles_dirty()
        payload = self._local_root_payload
        if not isinstance(payload, dict):
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        profiles = payload.get(KEY_PROFILES)
        if profiles is None:
            payload[KEY_PROFILES] = {}
        elif not isinstance(profiles, dict):
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        devices = payload.get(KEY_DEVICES)
        if devices is None:
            payload[KEY_DEVICES] = []
        elif not isinstance(devices, list):
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        topology_root = payload.get(KEY_TOPOLOGY)
        if topology_root is None:
            payload[KEY_TOPOLOGY] = {
                KEY_TOPOLOGY_VERSION: COUNT_ONE,
                KEY_TOPOLOGY_SOURCE: TOPOLOGY_SOURCE_LOCAL,
                KEY_TOPOLOGY_PROFILES: {},
            }
        elif not isinstance(topology_root, dict):
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        return StatusResult(code=SS__NORMAL)

    def _create_profile(self, name: str) -> StatusResult:
        """
        NAME
            _create_profile - Create a new empty profile and select it.
        """
        key = name.strip()
        if not key:
            print(MESSAGE_ERR_PROFILE_CREATE_NAME)
            return StatusResult(code=SS__CONFIG__INVALID)
        if self._local_config is None:
            self._local_config = {
                KEY_BRIDGE_SCHEMA_VERSION: BRIDGE_CONFIG_SCHEMA_VERSION,
                KEY_BRIDGE_GENERATED_AT: None,
                KEY_BRIDGE_BY_PROFILE: {},
            }
            self._local_devices_locked = True
            self._groups_dirty = False
        payload_result = self._ensure_local_profiles_payload()
        if not payload_result.ok():
            return payload_result
        payload = self._local_root_payload
        if not isinstance(payload, dict):
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        profiles = payload.get(KEY_PROFILES)
        if not isinstance(profiles, dict):
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        if key in profiles:
            print(MESSAGE_ERR_PROFILE_EXISTS.format(name=key))
            return StatusResult(code=SS__CONFIG__INVALID)
        create_blank_profile(payload, key, set_default_if_missing=True)
        self._mark_profiles_dirty()
        self._local_devices_locked = True
        self._groups_profile = key
        self._local_profile_entry(key, create=True)
        self._refresh_tests_profile(key)
        self._sync_store_from_local()
        print(MESSAGE_PROFILE_CREATED.format(name=key))
        return StatusResult(code=SS__NORMAL)

    def _delete_profile(self, name: str) -> StatusResult:
        """
        NAME
            _delete_profile - Delete a profile from local profiles/config.
        """
        payload = self._local_root_payload
        if not isinstance(payload, dict):
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        profiles = payload.get(KEY_PROFILES)
        if not isinstance(profiles, dict):
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        key = name.strip()
        if not key:
            print(MESSAGE_ERR_PROFILE_REQUIRED)
            return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
        if key not in profiles:
            print(MESSAGE_PROFILE_DELETE_MISSING.format(name=key))
            return StatusResult(code=SS__NORMAL)
        delete_profile_payload(payload, key)
        config = payload.get(KEY_BRIDGE_CONFIG)
        if isinstance(config, dict):
            by_profile = config.get(KEY_BRIDGE_BY_PROFILE)
            if isinstance(by_profile, dict):
                by_profile.pop(key, None)
        if KEY_DEFAULT_PROFILE not in payload and profiles:
            set_default_profile_payload(payload, next(iter(profiles.keys())))
        if self._groups_profile == key:
            self._groups_profile = self._default_profile_name()
        self._mark_profiles_dirty()
        self._local_devices_locked = True
        self._refresh_devices_from_profiles()
        self._sync_store_from_local()
        print(MESSAGE_PROFILE_DELETE_OK.format(name=key))
        return StatusResult(code=SS__NORMAL)

    def _init_profiles_payload(self) -> StatusResult:
        """
        NAME
            _init_profiles_payload - Initialize an empty profiles payload.
        """
        root_path = self._config_repository.canonical_path()
        self._local_root_path = root_path
        self._local_config_path = root_path
        payload: Dict[str, object] = {
            KEY_SCHEMA_VERSION: PROFILE_SCHEMA_VERSION,
            KEY_PROFILES: {},
            KEY_DEVICES: [],
            KEY_TOPOLOGY: {
                KEY_TOPOLOGY_VERSION: COUNT_ONE,
                KEY_TOPOLOGY_SOURCE: TOPOLOGY_SOURCE_LOCAL,
                KEY_TOPOLOGY_PROFILES: {},
            },
            KEY_DATA_VERSION: timestamp_version(),
        }
        try:
            payload[KEY_DATA_HASH] = compute_profiles_hash(payload)
        except Exception:
            payload[KEY_DATA_HASH] = EMPTY_STRING
        self._local_root_payload = payload
        self._local_root_hash = self._profiles_hash(payload)
        self._local_loaded_at = time.time()
        self._local_devices_locked = True
        self._mark_profiles_dirty()
        self._groups_dirty = False
        self._tests_dirty = False
        self._local_config = {
            KEY_BRIDGE_SCHEMA_VERSION: BRIDGE_CONFIG_SCHEMA_VERSION,
            KEY_BRIDGE_GENERATED_AT: None,
            KEY_BRIDGE_BY_PROFILE: {},
        }
        self._groups_profile = None
        self._tests_profile = None
        self._tests_model = None
        self._tests_active_set = EMPTY_STRING
        self._tests_device_catalog = {}
        self._tests_duplicate_labels = set()
        self._sync_store_from_local()
        print(MESSAGE_PROFILES_INIT_OK)
        return StatusResult(code=SS__NORMAL)

    def _set_default_profile(self, name: str) -> StatusResult:
        """
        NAME
            _set_default_profile - Set the default profile in the local payload.
        """
        key = name.strip()
        if not key:
            print(MESSAGE_ERR_PROFILE_REQUIRED)
            return StatusResult(code=SS__CONFIG__INVALID)
        payload_result = self._ensure_local_profiles_payload()
        if not payload_result.ok():
            return payload_result
        payload = self._local_root_payload
        if not isinstance(payload, dict):
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        profiles = payload.get(KEY_PROFILES)
        if not isinstance(profiles, dict) or key not in profiles:
            print(MESSAGE_ERR_PROFILE_UNKNOWN.format(name=key))
            return StatusResult(code=SS__CONFIG__INVALID)
        set_default_profile_payload(payload, key)
        self._mark_profiles_dirty()
        self._local_devices_locked = True
        self._sync_store_from_local()
        print(MESSAGE_PROFILE_DEFAULT_SET.format(name=key))
        return StatusResult(code=SS__NORMAL)

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

    def _is_active_group(self, name: str) -> bool:
        """
        NAME
            _is_active_group - Check if a group name targets the reserved active group.
        """
        return name.strip().lower() == GROUP_NAME_ACTIVE

    def _reset_transient_active_group(self) -> None:
        """
        NAME
            _reset_transient_active_group - Reset non-persistent active group membership.
        """
        self._active_group_members = []
        self._active_add_cursor = COUNT_ZERO

    def _clear_in_memory_workspace_state(self) -> None:
        """
        NAME
            _clear_in_memory_workspace_state - Clear local in-memory config and tests state.

        DESCRIPTION
            Leaves CLI process/session running while removing loaded local config,
            profile/group/test state, and transient active-group membership.
        """
        self._local_config = None
        self._local_config_path = None
        self._local_root_payload = None
        self._local_root_hash = None
        self._local_root_path = None
        self._local_loaded_at = None
        self._local_devices_locked = True
        self._profiles_dirty = False
        self._groups_dirty = False
        self._tests_dirty = False
        self._groups_profile = None
        self._tests_profile = None
        self._tests_model = None
        self._tests_active_set = EMPTY_STRING
        self._tests_device_catalog = {}
        self._tests_duplicate_labels = set()
        self._reset_transient_active_group()
        self._store = ConfigSchemaStore()

    def _active_group_payload(self) -> Dict[str, object]:
        """
        NAME
            _active_group_payload - Build a local payload for the reserved active group.
        """
        members_payload = []
        for device in self._active_group_members:
            members_payload.append(_group_member_entry(device, True))
        return {
            KEY_NAME: GROUP_NAME_ACTIVE,
            KEY_ENABLED: True,
            KEY_MEMBERS: members_payload,
            KEY_BRIDGE_BINDINGS: [],
            KEY_TEMP: True,
        }

    def _resolved_local_group_state(
        self,
        group: Dict[str, object],
        *,
        scope_active: bool,
    ):
        """
        NAME
            _resolved_local_group_state - Return shared resolved state for one local group payload.
        """
        member_map: Dict[str, Dict[str, object]] = {}
        members = group.get(KEY_MEMBERS, []) or []
        primary_label = EMPTY_STRING
        if isinstance(members, list):
            for member in members:
                label = _group_member_label(member)
                if not label:
                    continue
                if not primary_label and (
                    not isinstance(member, dict) or bool(member.get(KEY_ENABLED, True))
                ):
                    primary_label = label
                member_map[label.strip().lower()] = (
                    dict(member)
                    if isinstance(member, dict)
                    else _group_member_entry(label, True)
                )
        return resolve_group_state_from_member_map(
            name=group.get(KEY_NAME, EMPTY_STRING),
            member_map=member_map,
            runtime_state_by_label={},
            primary_label=primary_label,
            scope_active=scope_active,
        )

    def _resolved_local_group_payload(
        self,
        group: Dict[str, object],
        *,
        scope_active: bool,
        binding_count: int,
    ) -> Dict[str, object]:
        """
        NAME
            _resolved_local_group_payload - Build one local group payload from the shared group contract.
        """
        resolved = self._resolved_local_group_state(group, scope_active=scope_active)
        payload: Dict[str, object] = {
            KEY_NAME: str(group.get(KEY_NAME, EMPTY_STRING)).strip(),
            KEY_ENABLED: bool(group.get(KEY_ENABLED, True)),
            KEY_PRIMARY_LABEL: resolved.primary_label,
            KEY_MEMBER_COUNT: resolved.member_count,
            KEY_ENABLED_MEMBER_COUNT: resolved.enabled_member_count,
            KEY_HAS_MEMBERS: resolved.has_members,
            KEY_ALL_ENABLED_MEMBERS_PRESENT: resolved.all_enabled_members_present,
            KEY_BINDING_COUNT: binding_count,
            KEY_MEMBERS: [],
            KEY_BRIDGE_BINDINGS: list(group.get(KEY_BRIDGE_BINDINGS, []) or []),
        }
        payload_members = payload[KEY_MEMBERS]
        if isinstance(payload_members, list):
            for member in resolved.members:
                payload_members.append(
                    {
                        KEY_LABEL: member.label,
                        KEY_ENABLED: member.enabled,
                        KEY_LOCKED: member.locked,
                        KEY_INVALID: member.invalid,
                        KEY_SCOPE_ACTIVE: member.scope_active,
                        KEY_RUNTIME_PRESENT: member.runtime_present,
                        KEY_INSTANTIATED: member.instantiated,
                        KEY_TESTABLE: member.testable,
                    }
                )
        if KEY_TEMP in group:
            payload[KEY_TEMP] = bool(group.get(KEY_TEMP, False))
        return payload

    def _global_name_conflict(self, name: str, skip_group: Optional[str] = None) -> Optional[str]:
        """
        NAME
            _global_name_conflict - Return first conflicting global namespace owner.
        """
        key = name.strip().lower()
        if not key:
            return None
        if key == GROUP_NAME_ACTIVE:
            return GROUP_NAME_ACTIVE
        config = self._local_config or {}
        if isinstance(config, dict):
            devices = config.get(KEY_DEVICES)
            if isinstance(devices, list):
                for device in devices:
                    if not isinstance(device, dict):
                        continue
                    device_name = str(device.get(KEY_NAME, EMPTY_STRING)).strip()
                    if not device_name:
                        device_name = str(device.get(KEY_LABEL, EMPTY_STRING)).strip()
                    if device_name.lower() == key:
                        return device_name
        profile_name = self._active_profile_name()
        if profile_name:
            groups = self._local_groups(profile_name, create=True)
            for group in groups:
                if not isinstance(group, dict):
                    continue
                group_name = str(group.get(KEY_NAME, EMPTY_STRING)).strip()
                if not group_name:
                    continue
                if skip_group and group_name.lower() == skip_group.strip().lower():
                    continue
                if group_name.lower() == key:
                    return group_name
        return None

    def _find_named_local_group(self, name: str) -> Optional[Dict[str, object]]:
        """
        NAME
            _find_named_local_group - Find a non-active local group by case-insensitive name.
        """
        if self._is_active_group(name):
            return None
        profile = self._active_profile_name()
        if not profile or not self._local_config:
            return None
        groups = self._local_groups(profile, create=True)
        for group in groups:
            if not isinstance(group, dict):
                continue
            group_name = str(group.get(KEY_NAME, EMPTY_STRING)).strip()
            if group_name.lower() == name.strip().lower():
                return group
        return None

    def _target_group_name(self, explicit_name: Optional[str] = None) -> str:
        """
        NAME
            _target_group_name - Resolve target group using explicit arg, context, or active.
        """
        if explicit_name and explicit_name.strip():
            return explicit_name.strip()
        mode = self._modes[-1]
        if mode.name == CMD_GROUP and mode.group:
            return mode.group
        return GROUP_NAME_ACTIVE

    def _group_exists_for_context(self, name: str) -> bool:
        """
        NAME
            _group_exists_for_context - Check whether a group can be entered as CLI context.
        """
        clean = name.strip()
        if not clean:
            return False
        if self._is_active_group(clean):
            return True
        return self._find_named_local_group(clean) is not None

    def _list_target_group_members(self, group_name: str) -> Optional[List[str]]:
        """
        NAME
            _list_target_group_members - Return normalized member names for target group.
        """
        if self._is_active_group(group_name):
            return list(self._active_group_members)
        group = self._find_named_local_group(group_name)
        if group is None:
            return None
        resolved = self._resolved_local_group_state(group, scope_active=False)
        return [member.label for member in resolved.members if member.label]

    def _write_target_group_members(self, group_name: str, members: List[str]) -> StatusResult:
        """
        NAME
            _write_target_group_members - Replace target group membership from a label list.
        """
        normalized: List[str] = []
        seen: set[str] = set()
        for label in members:
            value = str(label).strip()
            if not value:
                continue
            key = value.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(value)
        if self._is_active_group(group_name):
            self._active_group_members = normalized
            return StatusResult(code=SS__NORMAL)
        group = self._find_named_local_group(group_name)
        if group is None:
            print(ERR_GROUP_NOT_FOUND_FMT.format(name=group_name))
            return StatusResult(code=SS__GROUP__NOT_FOUND)
        group[KEY_MEMBERS] = [_group_member_entry(label, True) for label in normalized]
        self._mark_groups_dirty()
        return StatusResult(code=SS__NORMAL)

    def _device_sequence_labels(self) -> List[str]:
        """
        NAME
            _device_sequence_labels - Return deterministic cyclic source list for add-next/add-all.
        """
        profile_name = self._active_profile_name()
        labels: List[str] = []
        if profile_name:
            for entry in self._profile_device_entries(profile_name):
                if not isinstance(entry, dict):
                    continue
                name = str(entry.get(KEY_NAME, EMPTY_STRING)).strip()
                if not name:
                    name = str(entry.get(KEY_LABEL, EMPTY_STRING)).strip()
                if name:
                    labels.append(name)
        if not labels:
            config = self._local_config or {}
            devices = config.get(KEY_DEVICES) if isinstance(config, dict) else None
            if isinstance(devices, list):
                for entry in devices:
                    if not isinstance(entry, dict):
                        continue
                    name = str(entry.get(KEY_NAME, EMPTY_STRING)).strip()
                    if not name:
                        name = str(entry.get(KEY_LABEL, EMPTY_STRING)).strip()
                    if name:
                        labels.append(name)
        deduped: List[str] = []
        seen: set[str] = set()
        for label in labels:
            key = label.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(label)
        return deduped

    def _next_device_label(self) -> Optional[str]:
        """
        NAME
            _next_device_label - Select next device from deterministic cyclic list.
        """
        labels = self._device_sequence_labels()
        if not labels:
            return None
        index = self._active_add_cursor % len(labels)
        self._active_add_cursor = (index + COUNT_ONE) % len(labels)
        return labels[index]

    def _replace_tests_group_refs(self, old_name: str, new_name: str) -> int:
        """
        NAME
            _replace_tests_group_refs - Update test target references for group rename.
        """
        self._ensure_tests_loaded()
        model = self._tests_model
        if model is None:
            return COUNT_ZERO
        old_key = old_name.strip().lower()
        updates = COUNT_ZERO
        for test_set in model.test_sets.values():
            if not isinstance(test_set, TestSetModel):
                continue
            for test in test_set.tests:
                if not isinstance(test, TestModel):
                    continue
                for idx, label in enumerate(list(test.devices)):
                    if isinstance(label, str) and label.strip().lower() == old_key:
                        test.devices[idx] = new_name
                        updates += COUNT_ONE
        if updates > COUNT_ZERO:
            self._mark_tests_dirty()
        return updates

    def _rename_local_group(self, old_name: str, new_name: str) -> StatusResult:
        """
        NAME
            _rename_local_group - Rename a local named group with atomic validation.
        """
        old_clean = old_name.strip()
        new_clean = new_name.strip()
        if not old_clean or not new_clean:
            print(ERR_GROUP_NAME_REQUIRED)
            return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
        if self._is_active_group(old_clean):
            print(ERR_RESERVED_ACTIVE_RENAME)
            return StatusResult(code=SS__CONFIG__INVALID)
        if self._is_active_group(new_clean):
            print(ERR_NAME_RESERVED.format(name=new_clean))
            return StatusResult(code=SS__CONFIG__INVALID)
        group = self._find_named_local_group(old_clean)
        if group is None:
            print(ERR_GROUP_NOT_FOUND_FMT.format(name=old_clean))
            return StatusResult(code=SS__GROUP__NOT_FOUND)
        conflict = self._global_name_conflict(new_clean, skip_group=old_clean)
        if conflict is not None:
            print(ERR_NAME_EXISTS.format(name=new_clean))
            return StatusResult(code=SS__CONFIG__DUPLICATE_LABEL)
        snapshot_config = deepcopy(self._local_config)
        snapshot_tests = deepcopy(self._tests_model)
        group[KEY_NAME] = new_clean
        self._replace_tests_group_refs(old_clean, new_clean)
        if self._modes[-1].name == CMD_GROUP and self._modes[-1].group:
            if self._modes[-1].group.strip().lower() == old_clean.lower():
                self._modes[-1].group = new_clean
        if isinstance(self._local_config, dict) and isinstance(self._local_root_payload, dict):
            ok, message = validate_config_data_all(self._local_config, self._local_root_payload)
            if not ok:
                self._local_config = snapshot_config
                self._tests_model = snapshot_tests
                print(MESSAGE_ERR_CONFIG_VALIDATE.format(message=message))
                return StatusResult(code=SS__CONFIG__INVALID)
        self._mark_groups_dirty()
        return StatusResult(code=SS__NORMAL)

    def _create_local_group(self, name: str) -> StatusResult:
        """
        NAME
            _create_local_group - Create a named group and fail when it already exists.
        """
        clean = name.strip()
        if not clean:
            print(ERR_GROUP_NAME_REQUIRED)
            return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
        if self._is_active_group(clean):
            print(ERR_NAME_RESERVED.format(name=clean))
            return StatusResult(code=SS__CONFIG__INVALID)
        if self._find_named_local_group(clean) is not None:
            print(ERR_NAME_EXISTS.format(name=clean))
            return StatusResult(code=SS__CONFIG__DUPLICATE_LABEL)
        conflict = self._global_name_conflict(clean)
        if conflict is not None:
            print(ERR_NAME_EXISTS.format(name=clean))
            return StatusResult(code=SS__CONFIG__DUPLICATE_LABEL)
        return self._select_or_create_local_group(clean)

    def _copy_local_group(self, source: str, dest: str) -> StatusResult:
        """
        NAME
            _copy_local_group - Copy group membership from source into destination.
        """
        source_clean = source.strip()
        dest_clean = dest.strip()
        if not source_clean or not dest_clean:
            print(ERR_GROUP_NAME_REQUIRED)
            return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
        if source_clean.lower() == dest_clean.lower():
            print(ERR_SOURCE_DEST_SAME)
            return StatusResult(code=SS__CONFIG__INVALID)
        source_members = self._list_target_group_members(source_clean)
        if source_members is None:
            print(ERR_GROUP_NOT_FOUND_FMT.format(name=source_clean))
            return StatusResult(code=SS__GROUP__NOT_FOUND)
        if self._is_active_group(dest_clean):
            return self._write_target_group_members(dest_clean, source_members)
        existing_dest = self._find_named_local_group(dest_clean)
        if existing_dest is not None:
            if self._batch:
                print(ERR_COPY_NON_INTERACTIVE)
                return StatusResult(code=SS__CONFIG__INVALID)
            if not self._confirm(f"Overwrite group '{dest_clean}'?"):
                return StatusResult(code=SS__EXECUTOR__CANCELLED)
            return self._write_target_group_members(dest_clean, source_members)
        conflict = self._global_name_conflict(dest_clean)
        if conflict is not None:
            print(ERR_NAME_EXISTS.format(name=dest_clean))
            return StatusResult(code=SS__CONFIG__DUPLICATE_LABEL)
        create_result = self._select_or_create_local_group(dest_clean)
        if not create_result.ok():
            return create_result
        return self._write_target_group_members(dest_clean, source_members)

    def validate_config_file(self, path: str) -> tuple[bool, str, Optional[Dict[str, object]]]:
        """
        NAME
            validate_config_file - Wrapper to validate a config file path.
        """
        return validate_config_file(path)

    def validate_config_file_all(self, path: str) -> tuple[bool, str, Optional[Dict[str, object]]]:
        """
        NAME
            validate_config_file_all - Validate config and report all issues.
        """
        return validate_config_file_all(path)

    def validate_config_data(self, config: Dict[str, object]) -> tuple[bool, str]:
        """
        NAME
            validate_config_data - Wrapper to validate an in-memory config.
        """
        return validate_config_data(config, self._local_root_payload)

    def validate_config_data_all(self, config: Dict[str, object]) -> tuple[bool, str]:
        """
        NAME
            validate_config_data_all - Validate config and report all issues.
        """
        return validate_config_data_all(config, self._local_root_payload)

    def validate_profiles_only(self, profile_name: Optional[str] = None) -> tuple[bool, str]:
        """
        NAME
            validate_profiles_only - Validate profiles payload only.
        """
        self._sync_store_from_local()
        result = self._store.validate_profiles_only(strict=True, profile_name=profile_name)
        if result.ok():
            return (True, MESSAGE_VALIDATE_OK)
        message = self._format_store_errors(result.errors())
        if profile_name:
            message = f"profile {profile_name}:\n{message}"
        return (False, message)

    def validate_profiles_only_verbose(self, profile_name: Optional[str] = None) -> tuple[bool, str]:
        """
        NAME
            validate_profiles_only_verbose - Validate profiles payload and emit detailed issues.
        """
        self._sync_store_from_local()
        result = self._store.validate_profiles_only(strict=True, profile_name=profile_name)
        errors = result.errors()
        warnings = result.warnings()
        if not errors and not warnings:
            print("PASS: profiles payload is valid.")
            if profile_name:
                print(f"INFO: active profile scope = {profile_name}")
            return (True, MESSAGE_VALIDATE_OK)
        for issue in errors:
            print(f"FAIL: {issue.message}")
        for issue in warnings:
            print(f"WARN: {issue.message}")
        message = self._format_store_errors(errors)
        if profile_name:
            message = f"profile {profile_name}:\n{message}"
        return (not errors, message if errors else MESSAGE_VALIDATE_OK)

    def validate_profiles_robot(self) -> tuple[bool, str]:
        """
        NAME
            validate_profiles_robot - Compare local profile devices to robot devices.
        """
        if not self._session.is_connected():
            return (False, MESSAGE_VALIDATE_ROBOT_NOT_CONNECTED)
        profile_name = self._active_profile_name()
        if not profile_name:
            return (False, MESSAGE_ERR_PROFILE_REQUIRED)
        local_labels = self._profile_device_labels(profile_name)
        seq = show_devices(self._session, json_output=True)
        if seq is None:
            return (False, MESSAGE_VALIDATE_ROBOT_DEVICES_FETCH)
        event = self._wait_for_seq(seq, print_events=False)
        if self._event_failed(event, MESSAGE_LABEL_SHOW_DEVICES):
            return (False, MESSAGE_VALIDATE_ROBOT_DEVICES_FETCH)
        payload = parse_json_arg(event.json_text) if event else None
        devices = payload.get(KEY_DEVICES) if isinstance(payload, dict) else None
        robot_labels: set[str] = set()
        if isinstance(devices, list):
            for entry in devices:
                if isinstance(entry, dict):
                    label = str(entry.get(KEY_LABEL, "")).strip()
                else:
                    label = str(entry).strip()
                if label:
                    robot_labels.add(label.lower())
        missing = sorted(local_labels - robot_labels)
        extra = sorted(robot_labels - local_labels)
        if missing or extra:
            lines = [MESSAGE_VALIDATE_PROFILES_HEADER]
            if missing:
                lines.append(MESSAGE_VALIDATE_PROFILES_MISSING.format(labels=SEP_COMMA_SPACE.join(missing)))
            if extra:
                lines.append(MESSAGE_VALIDATE_PROFILES_EXTRA.format(labels=SEP_COMMA_SPACE.join(extra)))
            return (False, SEP_NEWLINE.join(lines))
        return (True, MESSAGE_VALIDATE_OK)

    def validate_tests_only(self, active_set: Optional[str] = None) -> tuple[bool, str]:
        """
        NAME
            validate_tests_only - Validate tests against profile devices.
        """
        self._ensure_tests_loaded()
        model = self._tests_model or TestAuthoringModel()
        if active_set:
            test_set = model.test_sets.get(active_set)
            if test_set is None:
                return (False, f"Test set not found: {active_set}")
            model = TestAuthoringModel(default_test_set=active_set, test_sets={active_set: test_set})
        profile_name = self._tests_profile or self._active_profile_name()
        controller_names = load_controller_names()
        result = validate_model(
            model,
            profile_name=profile_name,
            controller_names=controller_names,
            device_catalog=self._tests_device_catalog,
        )
        if result.ok():
            return (True, MESSAGE_VALIDATE_OK)
        issues = [
            (issue.test_name or GLOBAL_LABEL, issue.message)
            for issue in result.errors
            if issue.message
        ]
        if not issues:
            return (False, MESSAGE_VALIDATE_OK)
        header = MESSAGE_VALIDATE_TESTS_HEADER
        if active_set:
            header = f"{MESSAGE_VALIDATE_TESTS_HEADER} (test set: {active_set})"
        message = SEP_NEWLINE.join(
            [header]
            + [
                MESSAGE_VALIDATE_TESTS_ENTRY_WITH_TEST.format(test=test, message=msg)
                for test, msg in issues
            ]
        )
        return (False, message)

    def validate_tests_only_verbose(self, active_set: Optional[str] = None) -> tuple[bool, str]:
        """
        NAME
            validate_tests_only_verbose - Validate tests and emit detailed issues and warnings.
        """
        self._ensure_tests_loaded()
        model = self._tests_model or TestAuthoringModel()
        if active_set:
            test_set = model.test_sets.get(active_set)
            if test_set is None:
                return (False, f"Test set not found: {active_set}")
            model = TestAuthoringModel(default_test_set=active_set, test_sets={active_set: test_set})
        profile_name = self._tests_profile or self._active_profile_name()
        controller_names = load_controller_names()
        result = validate_model(
            model,
            profile_name=profile_name,
            controller_names=controller_names,
            device_catalog=self._tests_device_catalog,
        )
        if result.ok():
            print("PASS: tests are valid.")
            for issue in result.warnings:
                print(f"WARN: {issue.message}")
            return (True, MESSAGE_VALIDATE_OK)
        for issue in result.errors:
            label = issue.test_name or GLOBAL_LABEL
            print(f"FAIL: {label}: {issue.message}")
        for issue in result.warnings:
            label = issue.test_name or GLOBAL_LABEL
            print(f"WARN: {label}: {issue.message}")
        return self.validate_tests_only(active_set=active_set)

    def validate_bindings_only(self, path: Optional[str]) -> tuple[bool, str]:
        """
        NAME
            validate_bindings_only - Validate bindings payload or file.
        """
        payload = self._bindings_payload
        if path:
            try:
                payload = read_json(Path(path))
            except Exception:
                return (False, MESSAGE_VALIDATE_BINDINGS_LOAD.format(path=path))
        self._store.set_bindings_payload(payload or {})
        result = self._store.validate_bindings_only(strict=True)
        errors = [issue for issue in result.errors() if issue.location == LOCATION_BINDINGS]
        if errors:
            message = self._format_store_errors(errors)
            return (False, message)
        return (True, MESSAGE_VALIDATE_OK)

    def validate_bindings_only_verbose(self, path: Optional[str]) -> tuple[bool, str]:
        """
        NAME
            validate_bindings_only_verbose - Validate bindings and emit detailed issues.
        """
        payload = self._bindings_payload
        if path:
            try:
                payload = read_json(Path(path))
            except Exception:
                return (False, MESSAGE_VALIDATE_BINDINGS_LOAD.format(path=path))
        self._store.set_bindings_payload(payload or {})
        result = self._store.validate_bindings_only(strict=True)
        errors = [issue for issue in result.errors() if issue.location == LOCATION_BINDINGS]
        warnings = [issue for issue in result.warnings() if issue.location == LOCATION_BINDINGS]
        if not errors and not warnings:
            print("PASS: bindings payload is valid.")
            return (True, MESSAGE_VALIDATE_OK)
        for issue in errors:
            print(f"FAIL: {issue.message}")
        for issue in warnings:
            print(f"WARN: {issue.message}")
        if errors:
            return (False, self._format_store_errors(errors))
        return (True, MESSAGE_VALIDATE_OK)

    def validate_mappings_only(self, path: Optional[str]) -> tuple[bool, str]:
        """
        NAME
            validate_mappings_only - Validate CAN mappings payload or file.
        """
        payload = self._can_mappings
        if path:
            try:
                payload = read_json(Path(path))
            except Exception:
                return (False, MESSAGE_VALIDATE_MAPPINGS_LOAD.format(path=path))
        self._store.set_mappings_payload(payload or {})
        result = self._store.validate_mappings_only(strict=True)
        errors = [issue for issue in result.errors() if issue.location == LOCATION_MAPPINGS]
        if errors:
            message = self._format_store_errors(errors)
            return (False, message)
        return (True, MESSAGE_VALIDATE_OK)

    def validate_mappings_only_verbose(self, path: Optional[str]) -> tuple[bool, str]:
        """
        NAME
            validate_mappings_only_verbose - Validate mappings and emit detailed issues.
        """
        payload = self._can_mappings
        if path:
            try:
                payload = read_json(Path(path))
            except Exception:
                return (False, MESSAGE_VALIDATE_MAPPINGS_LOAD.format(path=path))
        self._store.set_mappings_payload(payload or {})
        result = self._store.validate_mappings_only(strict=True)
        errors = [issue for issue in result.errors() if issue.location == LOCATION_MAPPINGS]
        warnings = [issue for issue in result.warnings() if issue.location == LOCATION_MAPPINGS]
        if not errors and not warnings:
            print("PASS: can-mappings payload is valid.")
            return (True, MESSAGE_VALIDATE_OK)
        for issue in errors:
            print(f"FAIL: {issue.message}")
        for issue in warnings:
            print(f"WARN: {issue.message}")
        if errors:
            return (False, self._format_store_errors(errors))
        return (True, MESSAGE_VALIDATE_OK)

    def lint_script(self, path: str) -> tuple[bool, List[str]]:
        """
        NAME
            lint_script - Validate a CLI script without executing it.
        """
        errors: List[str] = []
        try:
            lines = Path(path).read_text(encoding=ENCODING_UTF8).splitlines()
        except Exception as exc:
            errors.append(str(exc))
            return (False, errors)
        mode_stack = [MODE_EXEC]
        for index, raw in enumerate(lines, start=COUNT_ONE):
            line = raw.strip()
            if not line:
                continue
            if line.startswith(SCRIPT_COMMENT_PREFIX):
                continue
            try:
                parsed = self._parser.parse(line, mode_stack[-1])
            except Exception as exc:
                errors.append(MESSAGE_VALIDATE_SCRIPT_LINE.format(line=index, message=str(exc)))
                continue
            tokens = parsed.tokens
            if not tokens:
                continue
            verb = tokens[COUNT_ZERO].lower()
            if verb in (CMD_EXIT, CMD_END, CMD_QUIT):
                if len(mode_stack) > COUNT_ONE:
                    mode_stack.pop()
                continue
            if verb == CMD_CONFIGURE and len(tokens) > COUNT_ONE and tokens[COUNT_ONE].lower() == CMD_TERMINAL:
                if mode_stack[-1] != MODE_CONFIG:
                    mode_stack.append(MODE_CONFIG)
                continue
            if mode_stack[-1] == MODE_CONFIG:
                if verb == CMD_GROUP and len(tokens) > COUNT_ONE:
                    mode_stack.append(MODE_GROUP)
                    continue
                if verb == CMD_DEVICE and len(tokens) == COUNT_TWO:
                    mode_stack.append(MODE_DEVICE)
                    continue
                if (
                    verb == CMD_TEST
                    and len(tokens) > COUNT_ONE
                    and tokens[COUNT_ONE].lower() not in (CMD_SET, CMD_DELETE)
                ):
                    mode_stack.append(MODE_TEST)
                    continue
        return (not errors, errors)

    def validate_all(self, verbose: bool = False) -> tuple[bool, List[tuple[str, bool, str]]]:
        """
        NAME
            validate_all - Run all local validations and return per-step results.

        RETURNS
            ok - True if all validations pass.
            results - List of (label, ok, message) tuples.
        """
        results: List[tuple[str, bool, str]] = []
        if self._local_config:
            ok, message = self.validate_config_data_all(self._local_config)
        else:
            ok = False
            message = MESSAGE_ERR_LOCAL_CONFIG_MISSING
        results.append((VALIDATE_ALL_CONFIG, ok, message))

        ok, message = (
            self.validate_profiles_only_verbose() if verbose else self.validate_profiles_only()
        )
        results.append((VALIDATE_ALL_PROFILES_LOCAL, ok, message))

        if self._session.is_connected():
            ok, message = self.validate_profiles_robot()
            results.append((VALIDATE_ALL_PROFILES_ROBOT, ok, message))

        ok, message = (
            self.validate_tests_only_verbose(active_set=None)
            if verbose
            else self.validate_tests_only(active_set=None)
        )
        results.append((VALIDATE_ALL_TESTS, ok, message))

        ok, message = (
            self.validate_bindings_only_verbose(None) if verbose else self.validate_bindings_only(None)
        )
        results.append((VALIDATE_ALL_BINDINGS, ok, message))

        ok, message = (
            self.validate_mappings_only_verbose(None) if verbose else self.validate_mappings_only(None)
        )
        results.append((VALIDATE_ALL_MAPPINGS, ok, message))

        all_ok = all(item[1] for item in results)
        return all_ok, results

    def _emit_status(self, result: StatusResult) -> None:
        """
        NAME
            _emit_status - Print a structured status code line.
        """
        self._output_facade.emit_status(result, STATUS_INCLUDE_RAW_DEFAULT)

    def _execute_line_with_tiu_capture(self, line: str) -> StatusResult:
        """
        NAME
            _execute_line_with_tiu_capture - Execute one line and capture output into TIU buffers.
        """
        if not self._tiu_enabled:
            result = self._execute_line(line)
            self._emit_status(result)
            return result
        result, output_text = self._execute_line_captured(line)
        self._tiu_store_output(output_text)
        if result.ok():
            self._tiu_add_event(f"OK: {line}")
        else:
            self._tiu_add_event(f"FAIL {result.code}: {line}")
        self._render_tiu_if_needed()
        return result

    def _execute_line_captured(self, line: str) -> Tuple[StatusResult, str]:
        """
        NAME
            _execute_line_captured - Execute one line and return captured stdout text.
        """
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            result = self._execute_line(line)
            self._emit_status(result)
        return result, buffer.getvalue()

    def _run_tiu_application(self) -> Optional[int]:
        """
        NAME
            _run_tiu_application - Run TIU as a full-screen prompt_toolkit application when available.
        """
        if not self._tiu_enabled:
            return None
        if (
            not self._use_prompt_toolkit
            or Application is None
            or TextArea is None
            or Frame is None
            or Layout is None
            or HSplit is None
            or VSplit is None
            or Window is None
            or FormattedTextControl is None
            or KeyBindings is None
            or Dimension is None
        ):
            line = self._tiu_input_line()
            line = line.strip()
            if not line:
                return None
            result = self._execute_line_with_tiu_capture(line)
            if result.exit_requested:
                return result.exit_code()
            return None
        self._tiu_exit_code = None
        app = self._build_tiu_application()
        self._tiu_app = app
        try:
            app.run()
        finally:
            self._tiu_app = None
            self._tiu_dashboard_view = None
            self._tiu_output_view = None
            self._tiu_input_view = None
        return self._tiu_exit_code

    def _build_tiu_application(self) -> object:
        """
        NAME
            _build_tiu_application - Build the prompt_toolkit TIU full-screen application.
        """
        output_view = TextArea(
            text=self._tiu_output_text(),
            read_only=True,
            focusable=False,
            scrollbar=True,
            wrap_lines=False,
        )
        dashboard_view = TextArea(
            text=self._tiu_status_text(),
            read_only=True,
            focusable=False,
            scrollbar=False,
            wrap_lines=False,
        )
        input_view = TextArea(
            text=self._pending_prompt_text or EMPTY_STRING,
            multiline=False,
            wrap_lines=False,
            completer=self._build_completer(),
            complete_while_typing=COMPLETION_WHILE_TYPING,
            history=self._build_prompt_history(),
        )
        self._pending_prompt_text = None
        self._tiu_dashboard_view = dashboard_view
        self._tiu_output_view = output_view
        self._tiu_input_view = input_view
        input_focus_target = input_view.control

        prompt_control = FormattedTextControl(text=lambda: self._prompt())
        prompt_window = Window(content=prompt_control, width=Dimension(min=1, preferred=24))

        bindings = KeyBindings()

        @bindings.add("enter")
        def _tiu_accept(event) -> None:
            if not event.app.layout.has_focus(input_focus_target):
                return
            line = self._tiu_commit_input_line(input_view)
            if not line:
                return
            self._tiu_store_output(f"{self._prompt()}{line}")
            result, output_text = self._execute_line_captured(line)
            self._tiu_store_output(output_text)
            if result.ok():
                self._tiu_add_event(f"OK: {line}")
            else:
                self._tiu_add_event(f"FAIL {result.code}: {line}")
            self._refresh_tiu_views()
            if result.exit_requested:
                self._tiu_exit_code = result.exit_code()
                event.app.exit()
                return
            if not self._tiu_enabled:
                event.app.exit()
                return

        @bindings.add("escape")
        def _tiu_focus_input(event) -> None:
            self._tiu_output_follow_tail = True
            event.app.layout.focus(input_focus_target)
            self._tiu_move_output_to_end()

        @bindings.add("pageup")
        def _tiu_output_page_up(event) -> None:
            self._tiu_output_follow_tail = False
            self._tiu_move_output_cursor(lines=-10)

        @bindings.add("pagedown")
        def _tiu_output_page_down(event) -> None:
            self._tiu_move_output_cursor(lines=10)

        @bindings.add("home")
        def _tiu_output_home(event) -> None:
            self._tiu_output_follow_tail = False
            self._tiu_output_set_scroll_line(COUNT_ZERO)
            self._refresh_tiu_views()

        @bindings.add("end")
        def _tiu_output_end(event) -> None:
            self._tiu_output_follow_tail = True
            self._tiu_move_output_to_end()

        @bindings.add("<scroll-up>")
        def _tiu_mouse_scroll_up(event) -> None:
            self._tiu_output_follow_tail = False
            self._tiu_move_output_cursor(lines=-3)

        @bindings.add("<scroll-down>")
        def _tiu_mouse_scroll_down(event) -> None:
            self._tiu_move_output_cursor(lines=3)

        body = HSplit(
            [
                Frame(dashboard_view, title="TIU Status", height=Dimension(preferred=12, max=14)),
                Frame(output_view, title="TIU Output / Scrollback"),
                VSplit(
                    [
                        prompt_window,
                        input_view,
                    ],
                    height=Dimension.exact(COUNT_ONE),
                ),
            ]
        )
        app = Application(
            layout=Layout(body, focused_element=input_focus_target),
            key_bindings=bindings,
            full_screen=True,
            mouse_support=True,
        )
        self._refresh_tiu_views()
        return app

    @staticmethod
    def _tiu_commit_input_line(input_view: object) -> str:
        """
        NAME
            _tiu_commit_input_line - Normalize, persist, and reset one TIU input line.
        """
        buffer = getattr(input_view, "buffer", None)
        if buffer is None:
            return EMPTY_STRING
        raw_text = str(getattr(input_view, "text", EMPTY_STRING) or EMPTY_STRING)
        line = raw_text.strip()
        if line and hasattr(input_view, "text"):
            input_view.text = line
        reset_method = getattr(buffer, "reset", None)
        if callable(reset_method):
            reset_method(append_to_history=True)
            BridgeCli._tiu_rebuild_buffer_history(buffer)
        elif hasattr(input_view, "text"):
            input_view.text = EMPTY_STRING
        return line

    @staticmethod
    def _tiu_rebuild_buffer_history(buffer: object) -> None:
        """
        NAME
            _tiu_rebuild_buffer_history - Rebuild prompt_toolkit working history after TIU commits.
        """
        history = getattr(buffer, "history", None)
        if history is None or not hasattr(history, "load_history_strings"):
            return
        try:
            loaded = list(history.load_history_strings())
        except Exception:
            return
        working_lines = deque([EMPTY_STRING])
        for item in loaded:
            if isinstance(item, str):
                working_lines.appendleft(item)
        if not hasattr(buffer, "_working_lines"):
            return
        setattr(buffer, "_working_lines", working_lines)
        if hasattr(buffer, "_Buffer__working_index"):
            setattr(buffer, "_Buffer__working_index", len(working_lines) - COUNT_ONE)

    def _build_prompt_history(self) -> Optional[object]:
        """
        NAME
            _build_prompt_history - Build a prompt_toolkit file history object when available.
        """
        if FileHistory is None:
            return None
        history_path = logs_dir() / HISTORY_FILENAME
        history_path.parent.mkdir(parents=True, exist_ok=True)
        return FileHistory(str(history_path))

    def _tiu_move_output_to_end(self) -> None:
        """
        NAME
            _tiu_move_output_to_end - Move the TIU output cursor to the end of scrollback.
        """
        if self._tiu_output_view is None:
            return
        self._tiu_output_view.buffer.cursor_position = len(self._tiu_output_view.text)
        self._tiu_output_set_scroll_line(max(self._tiu_output_line_count() - COUNT_ONE, COUNT_ZERO))
        self._refresh_tiu_views()

    def _tiu_move_output_cursor(self, lines: int) -> None:
        """
        NAME
            _tiu_move_output_cursor - Move the TIU output window scroll by a line count.
        """
        if self._tiu_output_view is None:
            return
        window = getattr(self._tiu_output_view, "window", None)
        if window is None:
            return
        if lines < COUNT_ZERO:
            scroll_up = getattr(window, "_scroll_up", None)
            if callable(scroll_up):
                for _ in range(abs(lines)):
                    scroll_up()
            else:
                line_count = self._tiu_output_line_count()
                next_scroll = max(COUNT_ZERO, int(getattr(window, "vertical_scroll", COUNT_ZERO)) + lines)
                resolved_scroll = min(next_scroll, max(line_count - COUNT_ONE, COUNT_ZERO))
                self._tiu_output_set_scroll_line(resolved_scroll)
            self._tiu_output_follow_tail = False
            self._refresh_tiu_views()
            return
        scroll_down = getattr(window, "_scroll_down", None)
        if callable(scroll_down):
            for _ in range(lines):
                scroll_down()
        else:
            line_count = self._tiu_output_line_count()
            next_scroll = max(COUNT_ZERO, int(getattr(window, "vertical_scroll", COUNT_ZERO)) + lines)
            resolved_scroll = min(next_scroll, max(line_count - COUNT_ONE, COUNT_ZERO))
            self._tiu_output_set_scroll_line(resolved_scroll)
        current_scroll = int(getattr(window, "vertical_scroll", COUNT_ZERO))
        if current_scroll >= max(self._tiu_output_line_count() - COUNT_ONE, COUNT_ZERO):
            self._tiu_output_follow_tail = True
        self._refresh_tiu_views()

    def _tiu_output_line_count(self) -> int:
        """
        NAME
            _tiu_output_line_count - Return the current output pane logical line count.
        """
        text = self._tiu_output_text()
        if not text:
            return COUNT_ONE
        return max(len(text.splitlines()), COUNT_ONE)

    def _tiu_output_set_scroll_line(self, line_index: int, *, sync_cursor: bool = True) -> None:
        """
        NAME
            _tiu_output_set_scroll_line - Sync TIU output cursor and window scroll to a logical line.
        """
        if self._tiu_output_view is None:
            return
        window = getattr(self._tiu_output_view, "window", None)
        buffer = getattr(self._tiu_output_view, "buffer", None)
        if window is None or buffer is None:
            return
        clamped_line = max(COUNT_ZERO, min(line_index, max(self._tiu_output_line_count() - COUNT_ONE, COUNT_ZERO)))
        if sync_cursor:
            document = getattr(buffer, "document", None)
            if document is not None and hasattr(document, "translate_row_col_to_index"):
                try:
                    buffer.cursor_position = document.translate_row_col_to_index(clamped_line, COUNT_ZERO)
                except Exception:
                    pass
        window.vertical_scroll = clamped_line

    def _refresh_tiu_views(self) -> None:
        """
        NAME
            _refresh_tiu_views - Refresh TIU prompt_toolkit widgets from current state.
        """
        if self._tiu_dashboard_view is not None:
            self._tiu_dashboard_view.text = self._tiu_status_text()
        if self._tiu_output_view is not None:
            previous_cursor = self._tiu_output_view.buffer.cursor_position
            previous_scroll = COUNT_ZERO
            if hasattr(self._tiu_output_view, "window") and self._tiu_output_view.window is not None:
                previous_scroll = int(getattr(self._tiu_output_view.window, "vertical_scroll", COUNT_ZERO))
            self._tiu_output_view.text = self._tiu_output_text()
            text_length = len(self._tiu_output_view.text)
            if self._tiu_output_follow_tail:
                self._tiu_output_view.buffer.cursor_position = text_length
                self._tiu_output_set_scroll_line(
                    max(self._tiu_output_line_count() - COUNT_ONE, COUNT_ZERO),
                    sync_cursor=False,
                )
            else:
                self._tiu_output_view.buffer.cursor_position = min(previous_cursor, text_length)
                self._tiu_output_set_scroll_line(
                    min(
                        previous_scroll,
                        max(self._tiu_output_line_count() - COUNT_ONE, COUNT_ZERO),
                    )
                )
        if self._tiu_app is not None:
            invalidate = getattr(self._tiu_app, "invalidate", None)
            if callable(invalidate):
                invalidate()

    def _render_tiu_if_needed(self) -> None:
        """
        NAME
            _render_tiu_if_needed - Redraw the TIU dashboard when the mode is active.
        """
        if not self._tiu_enabled:
            return
        if hasattr(sys.stdout, "isatty") and not sys.stdout.isatty():
            return
        sys.stdout.write(MESSAGE_TIU_CLEAR_SCREEN)
        for line in self._tiu_dashboard_lines():
            sys.stdout.write(line + "\n")
        sys.stdout.flush()

    def _tiu_input_line(self) -> str:
        """
        NAME
            _tiu_input_line - Render TIU and read one command line at a fixed screen row.
        """
        self._render_tiu_if_needed()
        prompt_row = self._tiu_prompt_row()
        prompt = self._prompt()
        sys.stdout.write(MESSAGE_TIU_CURSOR_FMT.format(row=prompt_row))
        sys.stdout.write(MESSAGE_TIU_CLEAR_LINE)
        sys.stdout.write(prompt)
        if self._pending_prompt_text is not None:
            sys.stdout.write(self._pending_prompt_text)
            sys.stdout.flush()
            self._pending_prompt_text = None
            line = input(MESSAGE_EMPTY_PROMPT)
        else:
            sys.stdout.write(MESSAGE_TIU_CLEAR_TO_END)
            sys.stdout.flush()
            line = input(MESSAGE_EMPTY_PROMPT)
        return line

    def _tiu_prompt_row(self) -> int:
        """
        NAME
            _tiu_prompt_row - Return the fixed prompt row used while TIU mode is active.
        """
        terminal_height = max(shutil.get_terminal_size((TIU_LINE_MAX_FALLBACK, 30)).lines or 30, 12)
        return max(terminal_height - TIU_PROMPT_ROW_OFFSET, COUNT_ONE)

    def _tiu_store_output(self, text: str) -> None:
        """
        NAME
            _tiu_store_output - Append command output lines to the bounded TIU output pane.
        """
        if not text:
            return
        lines = [line.rstrip() for line in text.splitlines() if line.strip()]
        if not lines:
            return
        self._tiu_cli_output.extend(lines)
        if len(self._tiu_cli_output) > TIU_OUTPUT_MAX_LINES:
            self._tiu_cli_output = self._tiu_cli_output[-TIU_OUTPUT_MAX_LINES:]

    def _tiu_output_text(self) -> str:
        """
        NAME
            _tiu_output_text - Build the TIU scrollback pane text.
        """
        return "\n".join(self._tiu_cli_output[-TIU_OUTPUT_MAX_LINES:])

    def _tiu_status_text(self) -> str:
        """
        NAME
            _tiu_status_text - Build the compact fixed TIU status pane text.
        """
        provenance = self._build_provenance_payload()
        match = provenance.get(KEY_MATCH, {}) if isinstance(provenance, dict) else {}
        last_saved = provenance.get(KEY_LAST_SAVED, {}) if isinstance(provenance, dict) else {}
        last_pushed = provenance.get(KEY_LAST_PUSHED, {}) if isinstance(provenance, dict) else {}
        state = self._session.get_state_snapshot()
        runtime_payload = self._tiu_runtime_payload()
        runtime_details = self._runtime_details_snapshot_local()
        visibility = self._visibility_snapshot_local()
        visible_devices = visibility.get(KEY_DEVICES, []) if isinstance(visibility, dict) else []
        visible_count = len(visible_devices) if isinstance(visible_devices, list) else COUNT_ZERO
        configured_labels = self._active_profile_labels()
        indexed_runtime = self._device_runtime_index(runtime_payload) if isinstance(runtime_payload, dict) else {}
        instantiated_count = len(
            [
                label
                for label in configured_labels
                if bool(indexed_runtime.get(label.lower(), {}).get(KEY_INSTANTIATED, False))
            ]
        )
        fault_rows = self._collect_runtime_fault_rows(runtime_payload) if isinstance(runtime_payload, dict) else []
        active_group = self._active_group_payload()
        active_group_resolved = self._resolved_local_group_payload(
            active_group,
            scope_active=False,
            binding_count=COUNT_ZERO,
        )
        components = runtime_details.get(KEY_RUNTIME_COMPONENTS, []) if isinstance(runtime_details, dict) else []
        recent_event = self._tiu_recent_events[-1] if self._tiu_recent_events else MESSAGE_TIU_UNSET
        output_count = len(self._tiu_cli_output)
        lines = [
            f"{self._prompt()}  {time.strftime('%H:%M:%S', time.localtime(time.time()))}",
            MESSAGE_TIU_SECTIONS,
            (
                f"host: profile={self._active_profile_name() or MESSAGE_TIU_UNSET} "
                f"dirty={MESSAGE_TIU_STATUS_DIRTY if self._has_dirty_state() else MESSAGE_TIU_STATUS_CLEAN} "
                f"recovery={self._tiu_bool_text(bool(self._recovery_mode))} "
                f"sources=r:{self._tiu_source_status(SOURCE_NAME_REGISTRY)} "
                f"b:{self._tiu_source_status(SOURCE_NAME_BINDINGS)} "
                f"m:{self._tiu_source_status(SOURCE_NAME_CAN_MAPPINGS)} "
                f"t:{self._tiu_source_status(SOURCE_NAME_TESTS)}"
            ),
            (
                f"save/push: modified={self._format_provenance_value(self._last_modified_at)} "
                f"saved={self._format_provenance_value(last_saved.get(KEY_AT) if isinstance(last_saved, dict) else None)} "
                f"pushed={self._format_provenance_value(last_pushed.get(KEY_AT) if isinstance(last_pushed, dict) else None)}"
            ),
            (
                f"match: local-saved={str(match.get(KEY_LOCAL_VS_SAVED, MATCH_STATE_UNKNOWN)).upper()} "
                f"local-pushed={str(match.get(KEY_LOCAL_VS_PUSHED, MATCH_STATE_UNKNOWN)).upper()} "
                f"robot-pushed={str(match.get(KEY_ROBOT_VS_PUSHED, MATCH_STATE_UNKNOWN)).upper()}"
            ),
            (
                f"robot: connected={MESSAGE_TIU_STATUS_CONNECTED if self._session.is_connected() else MESSAGE_TIU_STATUS_DISCONNECTED} "
                f"enabled={self._tiu_bool_text(bool(state.get(NT_STATE_ENABLED, False))) if isinstance(state, dict) else VALUE_UNAVAILABLE} "
                f"estopped={self._tiu_bool_text(bool(state.get(NT_STATE_ESTOPPED, False))) if isinstance(state, dict) else VALUE_UNAVAILABLE} "
                f"mode={str(state.get(NT_STATE_MODE, EMPTY_STRING)).strip() if isinstance(state, dict) else VALUE_UNAVAILABLE} "
                f"profile={str(runtime_payload.get(KEY_PROFILE, EMPTY_STRING)).strip() if isinstance(runtime_payload, dict) else MESSAGE_TIU_UNSET}"
            ),
            (
                f"runtime: group-members={active_group_resolved.get(KEY_MEMBER_COUNT, COUNT_ZERO)} "
                f"active-test-set={self._tests_active_set or MESSAGE_TIU_UNSET} "
                f"components={len(components) if isinstance(components, list) else COUNT_ZERO}"
            ),
            (
                f"devices: configured={len(configured_labels)} "
                f"instantiated={instantiated_count if isinstance(runtime_payload, dict) else VALUE_UNAVAILABLE} "
                f"visible={visible_count} faults={len(fault_rows) if isinstance(runtime_payload, dict) else VALUE_UNAVAILABLE}"
            ),
            f"events: latest={recent_event}",
            f"scrollback: lines={output_count} PageUp/PageDown/Home/End or mouse wheel scroll output",
        ]
        return "\n".join(lines)

    def _tiu_source_status(self, name: str) -> str:
        """
        NAME
            _tiu_source_status - Return a compact one-word source status for TIU summaries.
        """
        for entry in self._collect_sources():
            if str(entry.get(KEY_SOURCE_NAME, EMPTY_STRING)) != name:
                continue
            value = str(entry.get(KEY_SOURCE_STATUS, EMPTY_STRING)).strip()
            return value or VALUE_UNAVAILABLE
        return VALUE_UNAVAILABLE

    def _tiu_add_event(self, message: str) -> None:
        """
        NAME
            _tiu_add_event - Append one recent-event entry to the bounded TIU event pane.
        """
        line = str(message or EMPTY_STRING).strip()
        if not line:
            return
        timestamp = time.strftime("%H:%M:%S", time.localtime(time.time()))
        self._tiu_recent_events.append(f"{timestamp} {line}")
        if len(self._tiu_recent_events) > TIU_EVENT_MAX_LINES:
            self._tiu_recent_events = self._tiu_recent_events[-TIU_EVENT_MAX_LINES:]

    def _tiu_runtime_payload(self) -> Optional[Dict[str, object]]:
        """
        NAME
            _tiu_runtime_payload - Return a lightly cached robot runtime-state payload for TIU.
        """
        now = time.time()
        if self._tiu_runtime_cache is not None and (now - self._tiu_runtime_cache_at) < TIU_RUNTIME_CACHE_SEC:
            return self._tiu_runtime_cache
        payload = self._fetch_robot_runtime_payload()
        if isinstance(payload, dict):
            self._tiu_runtime_cache = payload
            self._tiu_runtime_cache_at = now
            return payload
        self._tiu_runtime_cache = None
        self._tiu_runtime_cache_at = now
        return None

    def _tiu_bool_text(self, value: bool) -> str:
        """
        NAME
            _tiu_bool_text - Render a compact TIU YES/NO value.
        """
        return MESSAGE_TIU_BOOL_YES if value else MESSAGE_TIU_BOOL_NO

    @staticmethod
    def _tiu_clip(text: str, width: int) -> str:
        """
        NAME
            _tiu_clip - Clip one TIU line to the available terminal width.
        """
        if width <= COUNT_ZERO:
            return EMPTY_STRING
        if len(text) <= width:
            return text
        if width <= COUNT_THREE:
            return text[:width]
        return text[: width - COUNT_THREE] + "..."

    def _tiu_section_block(
        self,
        title: str,
        body: List[str],
        width: int,
        max_body_lines: Optional[int] = None,
    ) -> List[str]:
        """
        NAME
            _tiu_section_block - Build a titled TIU section with clipped lines.
        """
        clipped_width = max(width - TIU_SECTION_MARGIN, COUNT_ONE)
        if max_body_lines is not None:
            if max_body_lines <= COUNT_ZERO:
                body = []
            else:
                body = body[:max_body_lines]
        lines = [title]
        if body:
            lines.extend(self._tiu_clip(line, clipped_width) for line in body)
        else:
            lines.append(self._tiu_clip(MESSAGE_TIU_NONE, clipped_width))
        return lines

    def _tiu_dashboard_lines(self) -> List[str]:
        """
        NAME
            _tiu_dashboard_lines - Build the current TIU dashboard text lines.
        """
        terminal_size = shutil.get_terminal_size((TIU_LINE_MAX_FALLBACK, 30))
        terminal_width = terminal_size.columns or TIU_LINE_MAX_FALLBACK
        terminal_height = max(terminal_size.lines or 30, 12)
        rule = MESSAGE_TIU_SECTION_RULE * max(
            terminal_width - len(self._prompt()) - len(time.strftime("%H:%M:%S")) - COUNT_TWO,
            COUNT_TEN,
        )
        lines: List[str] = [
            self._tiu_clip(
                MESSAGE_TIU_HEADER_FMT.format(
                    prompt=self._prompt(),
                    rule=rule,
                    clock=time.strftime("%H:%M:%S", time.localtime(time.time())),
                ),
                terminal_width,
            ),
            self._tiu_clip(MESSAGE_TIU_SECTIONS, terminal_width),
        ]
        fixed_sections = [
            self._tiu_section_block(MESSAGE_TIU_HOST, self._tiu_host_lines(), terminal_width, max_body_lines=2),
            self._tiu_section_block(MESSAGE_TIU_SAVE_PUSH, self._tiu_save_push_lines(), terminal_width, max_body_lines=4),
            self._tiu_section_block(MESSAGE_TIU_ROBOT, self._tiu_robot_lines(), terminal_width, max_body_lines=2),
            self._tiu_section_block(MESSAGE_TIU_RUNTIME, self._tiu_runtime_lines(), terminal_width, max_body_lines=1),
            self._tiu_section_block(MESSAGE_TIU_DEVICES, self._tiu_device_lines(), terminal_width, max_body_lines=2),
            self._tiu_section_block(MESSAGE_TIU_FAULTS, self._tiu_fault_lines(), terminal_width, max_body_lines=2),
        ]
        for section in fixed_sections:
            lines.extend(section)
        reserved_footer_lines = TIU_RENDER_RESERVED_LINES
        remaining_lines = max(terminal_height - len(lines) - reserved_footer_lines, 2)
        event_budget = max(1, remaining_lines // 3)
        cli_budget = max(1, remaining_lines - event_budget)
        lines.extend(
            self._tiu_section_block(
                MESSAGE_TIU_EVENTS,
                self._tiu_recent_event_lines(),
                terminal_width,
                max_body_lines=event_budget,
            )
        )
        lines.extend(
            self._tiu_section_block(
                MESSAGE_TIU_CLI,
                self._tiu_cli_output_lines(),
                terminal_width,
                max_body_lines=cli_budget,
            )
        )
        max_dashboard_lines = max(terminal_height - TIU_RENDER_RESERVED_LINES, COUNT_ONE)
        return lines[:max_dashboard_lines]

    def _tiu_host_lines(self) -> List[str]:
        provenance = self._build_provenance_payload()
        sources = self._collect_sources()
        sources_by_name = {
            str(entry.get(KEY_SOURCE_NAME, EMPTY_STRING)): str(entry.get(KEY_SOURCE_STATUS, EMPTY_STRING))
            for entry in sources
            if isinstance(entry, dict)
        }
        return [
            MESSAGE_TIU_HOST_STATE_FMT.format(
                profile=self._active_profile_name() or MESSAGE_TIU_UNSET,
                dirty=MESSAGE_TIU_STATUS_DIRTY if self._has_dirty_state() else MESSAGE_TIU_STATUS_CLEAN,
                recovery=self._tiu_bool_text(bool(self._recovery_mode)),
            ),
            MESSAGE_TIU_SOURCES_FMT.format(
                registry=sources_by_name.get(SOURCE_NAME_REGISTRY, VALUE_UNAVAILABLE),
                bindings=sources_by_name.get(SOURCE_NAME_BINDINGS, VALUE_UNAVAILABLE),
                mappings=sources_by_name.get(SOURCE_NAME_CAN_MAPPINGS, VALUE_UNAVAILABLE),
                tests=sources_by_name.get(SOURCE_NAME_TESTS, VALUE_UNAVAILABLE),
            ),
        ]

    def _tiu_save_push_lines(self) -> List[str]:
        provenance = self._build_provenance_payload()
        last_saved = provenance.get(KEY_LAST_SAVED, {}) if isinstance(provenance, dict) else {}
        last_pushed = provenance.get(KEY_LAST_PUSHED, {}) if isinstance(provenance, dict) else {}
        match = provenance.get(KEY_MATCH, {}) if isinstance(provenance, dict) else {}
        return [
            MESSAGE_TIU_SAVE_MODIFIED_FMT.format(value=self._format_provenance_value(self._last_modified_at)),
            MESSAGE_TIU_SAVE_SAVED_FMT.format(
                value=self._format_provenance_value(
                    last_saved.get(KEY_AT) if isinstance(last_saved, dict) else None,
                    str(last_saved.get(KEY_SOURCE_PATH, EMPTY_STRING)) if isinstance(last_saved, dict) else EMPTY_STRING,
                    str(last_saved.get(KEY_HASH, EMPTY_STRING)) if isinstance(last_saved, dict) else EMPTY_STRING,
                )
            ),
            MESSAGE_TIU_SAVE_PUSHED_FMT.format(
                value=self._format_provenance_value(
                    last_pushed.get(KEY_AT) if isinstance(last_pushed, dict) else None,
                    str(last_pushed.get(KEY_SOURCE_PATH, EMPTY_STRING)) if isinstance(last_pushed, dict) else EMPTY_STRING,
                    str(last_pushed.get(KEY_HASH, EMPTY_STRING)) if isinstance(last_pushed, dict) else EMPTY_STRING,
                    str(last_pushed.get(KEY_PROFILE_NAME, EMPTY_STRING)) if isinstance(last_pushed, dict) else EMPTY_STRING,
                )
            ),
            MESSAGE_TIU_MATCH_FMT.format(
                saved=str(match.get(KEY_LOCAL_VS_SAVED, MATCH_STATE_UNKNOWN)).upper(),
                pushed=str(match.get(KEY_LOCAL_VS_PUSHED, MATCH_STATE_UNKNOWN)).upper(),
                robot=str(match.get(KEY_ROBOT_VS_PUSHED, MATCH_STATE_UNKNOWN)).upper(),
            ),
        ]

    def _tiu_robot_lines(self) -> List[str]:
        state = self._session.get_state_snapshot()
        runtime_payload = self._tiu_runtime_payload()
        mode_value = str(state.get(NT_STATE_MODE, EMPTY_STRING)).strip() if isinstance(state, dict) else EMPTY_STRING
        profile_value = EMPTY_STRING
        if isinstance(runtime_payload, dict):
            profile_value = str(runtime_payload.get(KEY_PROFILE, EMPTY_STRING)).strip()
        return [
            MESSAGE_TIU_ROBOT_STATE_FMT.format(
                connected=MESSAGE_TIU_STATUS_CONNECTED if self._session.is_connected() else MESSAGE_TIU_STATUS_DISCONNECTED,
                enabled=self._tiu_bool_text(bool(state.get(NT_STATE_ENABLED, False))) if isinstance(state, dict) else VALUE_UNAVAILABLE,
                estopped=self._tiu_bool_text(bool(state.get(NT_STATE_ESTOPPED, False))) if isinstance(state, dict) else VALUE_UNAVAILABLE,
                mode=mode_value or VALUE_UNAVAILABLE,
            ),
            MESSAGE_TIU_ROBOT_PROFILE_FMT.format(profile=profile_value or MESSAGE_TIU_UNSET),
        ]

    def _tiu_runtime_lines(self) -> List[str]:
        runtime_details = self._runtime_details_snapshot_local()
        active_group = self._active_group_payload()
        active_group_resolved = self._resolved_local_group_payload(
            active_group,
            scope_active=False,
            binding_count=COUNT_ZERO,
        )
        components = runtime_details.get(KEY_RUNTIME_COMPONENTS, []) if isinstance(runtime_details, dict) else []
        return [
            MESSAGE_TIU_RUNTIME_FMT.format(
                members=active_group_resolved.get(KEY_MEMBER_COUNT, COUNT_ZERO),
                test_set=self._tests_active_set or MESSAGE_TIU_UNSET,
                components=len(components) if isinstance(components, list) else COUNT_ZERO,
            )
        ]

    def _tiu_device_lines(self) -> List[str]:
        configured_labels = self._active_profile_labels()
        visibility = self._visibility_snapshot_local()
        visible_devices = visibility.get(KEY_DEVICES, []) if isinstance(visibility, dict) else []
        visible_count = len(visible_devices) if isinstance(visible_devices, list) else COUNT_ZERO
        runtime_payload = self._tiu_runtime_payload()
        rows: List[str] = []
        instantiated_count = COUNT_ZERO
        unavailable_count = COUNT_ZERO
        if isinstance(runtime_payload, dict):
            indexed = self._device_runtime_index(runtime_payload)
            for label in configured_labels[:TIU_DEVICE_DETAIL_MAX]:
                runtime_entry = indexed.get(label.lower(), {})
                instantiated = runtime_entry.get(KEY_INSTANTIATED) if isinstance(runtime_entry, dict) else None
                if instantiated is True:
                    instantiated_count += COUNT_ONE
                elif instantiated is not False:
                    unavailable_count += COUNT_ONE
                rows.append(
                    MESSAGE_TIU_EVENT_ROW_FMT.format(
                        line=f"{label} instantiated={VALUE_UNAVAILABLE if instantiated is None else self._bool_text(bool(instantiated)).lower()}"
                    )
                )
            if len(configured_labels) > TIU_DEVICE_DETAIL_MAX:
                rows.append(MESSAGE_TIU_EVENT_ROW_FMT.format(line=f"... {len(configured_labels) - TIU_DEVICE_DETAIL_MAX} more"))
            return [
                MESSAGE_TIU_DEVICES_FMT.format(
                    configured=len(configured_labels),
                    instantiated=instantiated_count,
                    unavailable=unavailable_count,
                    visible=visible_count,
                )
            ] + rows
        return [
            MESSAGE_TIU_DEVICES_FMT.format(
                configured=len(configured_labels),
                instantiated=VALUE_UNAVAILABLE,
                unavailable=len(configured_labels),
                visible=visible_count,
            ),
            MESSAGE_TIU_UNAVAILABLE,
        ]

    def _tiu_fault_lines(self) -> List[str]:
        runtime_payload = self._tiu_runtime_payload()
        if not isinstance(runtime_payload, dict):
            return [MESSAGE_TIU_UNAVAILABLE]
        rows = self._collect_runtime_fault_rows(runtime_payload)
        output = [MESSAGE_TIU_FAULTS_FMT.format(faulted=len(rows))]
        if not rows:
            output.append(MESSAGE_TIU_NONE)
            return output
        for row in rows[:TIU_FAULT_DETAIL_MAX]:
            output.append(
                MESSAGE_TIU_FAULT_ROW_FMT.format(
                    label=str(row.get(KEY_LABEL, EMPTY_STRING)).strip() or MESSAGE_TIU_UNSET,
                    faults=row.get(KEY_FAULT_COUNT, COUNT_ZERO),
                    warnings=row.get(KEY_WARNING_COUNT, COUNT_ZERO),
                )
            )
        if len(rows) > TIU_FAULT_DETAIL_MAX:
            output.append(MESSAGE_TIU_EVENT_ROW_FMT.format(line=f"... {len(rows) - TIU_FAULT_DETAIL_MAX} more"))
        return output

    def _tiu_recent_event_lines(self) -> List[str]:
        if not self._tiu_recent_events:
            return [MESSAGE_TIU_NONE]
        return [MESSAGE_TIU_EVENT_ROW_FMT.format(line=line) for line in self._tiu_recent_events[-TIU_EVENT_MAX_LINES:]]

    def _tiu_cli_output_lines(self) -> List[str]:
        if not self._tiu_cli_output:
            return [MESSAGE_TIU_NONE]
        return [MESSAGE_TIU_OUTPUT_ROW_FMT.format(line=line) for line in self._tiu_cli_output[-TIU_OUTPUT_MAX_LINES:]]

    def _print_alias_removed(self, alias_name: str, canonical: str) -> None:
        """
        NAME
            _print_alias_removed - Print removed alias replacement guidance.
        """
        print(MESSAGE_ERR_ALIAS_REMOVED.format(alias=alias_name, canonical=canonical))

    def _handshake_error_text(self) -> str:
        """
        NAME
            _handshake_error_text - Return a specific handshake failure detail when available.
        """
        getter = getattr(self._session, "last_handshake_error", None)
        if not callable(getter):
            return "Handshake failed."
        detail = str(getter() or "").strip()
        if not detail:
            return "Handshake failed."
        return f"Handshake failed: {detail}"

    def _coerce_status(self, outcome: Optional[object]) -> StatusResult:
        """
        NAME
            _coerce_status - Normalize handler output into a StatusResult.
        """
        if isinstance(outcome, StatusResult):
            return outcome
        if outcome is None:
            return StatusResult(code=SS__NORMAL, message=STATUS_OK_MESSAGE)
        if isinstance(outcome, int):
            if outcome == COUNT_ZERO:
                return StatusResult(code=SS__NORMAL, exit_requested=True)
            return StatusResult(code=outcome)
        return StatusResult(code=SS__EXECUTOR__INTERNAL_ERROR)

    def _execute_line(self, line: str) -> StatusResult:
        if self._handle_question(line):
            return StatusResult(code=SS__NORMAL)
        active_result = self._handle_active_command(line)
        if active_result is not None:
            return active_result
        tests_run_result = self._handle_tests_run_command(line)
        if tests_run_result is not None:
            return tests_run_result
        targeting_result = self._handle_group_targeting_command(line)
        if targeting_result is not None:
            return targeting_result
        reset_result = self._handle_reset_zero_config_command(line)
        if reset_result is not None:
            return reset_result
        self._parse_context = BridgeCliParseContext(
            parse_line=self._parse_context.parse_line,
            split_command=self._parse_context.split_command,
            maybe_print_failure_hint=self._parse_context.maybe_print_failure_hint,
            alias_replacement=self._parse_context.alias_replacement,
            print_alias_removed=self._parse_context.print_alias_removed,
            normalize_tokens=self._parse_context.normalize_tokens,
            fallback_device_set=self._parse_context.fallback_device_set,
            config_command=self._parse_context.config_command,
            coerce_status=self._parse_context.coerce_status,
            mode_name=self._modes[-1].name,
        )
        parsed_line = self._parse_facade.parse_line(self._parse_context, line)
        self._last_line_pretty = parsed_line.line_pretty
        parsed_validation = self._validate_facade.validate_parsed_line(parsed_line)
        if parsed_validation is not None:
            return parsed_validation
        tokens = parsed_line.tokens
        ast = parsed_line.ast
        cmd = tokens[0].lower()
        if cmd == "revert":
            return self._revert_all()
        if cmd == "tiu":
            return self._handle_tiu_command(tokens)
        if cmd in ("quit", "exit"):
            if self._modes[-1].name == "exec":
                dirty = {name: flag for name, flag in self._dirty_state().items() if flag}
                if dirty:
                    items = ", ".join(sorted(dirty.keys()))
                    if self._batch:
                        print(MESSAGE_DIRTY_PROMPT.format(items=items))
                        return StatusResult(code=SS__NORMAL, exit_requested=True)
                    if not self._confirm(MESSAGE_DIRTY_PROMPT.format(items=items)):
                        return StatusResult(code=SS__EXECUTOR__CANCELLED)
                return StatusResult(code=SS__NORMAL, exit_requested=True)
            self._warn_unsaved_if_needed()
            self._pop_mode()
            return StatusResult(code=SS__NORMAL)
        if cmd == "end":
            self._warn_unsaved_if_needed()
            self._modes = [CliMode("exec")]
            return StatusResult(code=SS__NORMAL)
        if cmd == "help":
            self._print_help(tokens[1:] if len(tokens) > 1 else [])
            return StatusResult(code=SS__NORMAL)
        if cmd == "ping":
            seq = show_status(self._session, json_output=False)
            self._wait_for_seq(seq)
            return StatusResult(code=SS__NORMAL)
        if cmd == "echo":
            if len(tokens) < 2:
                state = "on" if self._echo_enabled else "off"
                print(f"echo {state}")
                return StatusResult(code=SS__NORMAL)
            value = tokens[1].lower()
            if value in ("on", "true", "1", "yes"):
                self._echo_enabled = True
                return StatusResult(code=SS__NORMAL)
            if value in ("off", "false", "0", "no"):
                self._echo_enabled = False
                return StatusResult(code=SS__NORMAL)
            print("ERROR: echo requires on/off.")
            return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
        if cmd == CMD_SLEEP:
            return self._handle_sleep_command(tokens)
        if cmd == CMD_MESSAGES:
            if len(tokens) < 2:
                print(MESSAGE_MESSAGE_LEVEL_ERROR)
                return StatusResult(code=SS__CLI_VALIDATOR__REQUIRED)
            if not self._set_message_level(tokens[1], persist=True):
                print(MESSAGE_MESSAGE_LEVEL_ERROR)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            print(MESSAGE_MESSAGE_LEVEL_UPDATED.format(level=self._message_level))
            return StatusResult(code=SS__NORMAL)

        if cmd == CMD_DIAGNOSE:
            return self._coerce_status(self._diagnose_command(tokens))
        if (
            cmd == CMD_TESTS
            and len(tokens) >= COUNT_TWO
            and tokens[COUNT_ONE].lower() == CMD_WAIT
        ):
            return self._handle_tests_wait_command(tokens)
        if self._is_test_authoring_command(tokens):
            return self._coerce_status(self._execute_test_authoring(tokens))
        if ast is not None:
            return self._coerce_status(self._ast_executor.execute(ast))

        mode = self._modes[-1].name
        if mode == "exec":
            return self._coerce_status(self._exec_command(tokens))
        if mode == MODE_CONFIG:
            return self._coerce_status(self._config_command(tokens))
        if mode == "group":
            return self._coerce_status(self._group_command(tokens))
        if mode == "device":
            return self._coerce_status(self._device_command(tokens))
        if mode == MODE_TEST:
            return self._coerce_status(self._test_mode_command(tokens))
        return StatusResult(code=SS__EXECUTOR__NOT_SUPPORTED)

    def _handle_sleep_command(self, tokens: List[str]) -> StatusResult:
        """
        NAME
            _handle_sleep_command - Pause local CLI execution.

        DESCRIPTION
            Lets batch scripts wait for robot-side asynchronous work to finish
            before sending the next command.
        """
        if len(tokens) != SLEEP_ARG_COUNT:
            print("ERROR: sleep <seconds>")
            return StatusResult(code=SS__CLI_VALIDATOR__REQUIRED)
        try:
            seconds = float(tokens[COUNT_ONE])
        except ValueError:
            print("ERROR: sleep seconds must be numeric.")
            return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
        if seconds < SLEEP_MIN_SEC or seconds > SLEEP_MAX_SEC:
            print(f"ERROR: sleep seconds must be between {SLEEP_MIN_SEC} and {SLEEP_MAX_SEC}.")
            return StatusResult(code=SS__CLI_VALIDATOR__OUT_OF_RANGE)
        time.sleep(seconds)
        return StatusResult(code=SS__NORMAL)

    def _record_test_run_event(self, event: Optional[BridgeEvent]) -> None:
        """
        NAME
            _record_test_run_event - Remember the latest robot test run id.
        """
        payload = self._event_json_payload(event)
        if not isinstance(payload, dict):
            return
        run_id = self._safe_int(payload.get(KEY_RUN_ID), None)
        if run_id and run_id > COUNT_ZERO:
            self._last_test_run_id = run_id

    def _handle_tests_wait_command(self, tokens: List[str]) -> StatusResult:
        """
        NAME
            _handle_tests_wait_command - Wait for a robot-side test run to finish.

        DESCRIPTION
            Polls showTests JSON and watches the shared robot run lifecycle
            instead of relying on a fixed sleep.
        """
        if not self._session.is_connected():
            print(MESSAGE_ERR_SHOW_TESTS_ROBOT_NOT_CONNECTED)
            return StatusResult(code=SS__NETWORK__NOT_CONNECTED)
        run_id, timeout_sec, error = self._parse_tests_wait_args(tokens)
        if error:
            print(error)
            return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
        if run_id is None:
            run_id = self._last_test_run_id
        deadline = time.time() + timeout_sec
        last_run: Dict[str, object] = {}
        self._tests_wait_progress_next_sec = 0.0
        while time.time() <= deadline:
            seq = show_tests(self._session, json_output=True)
            event = self._wait_for_seq(seq, print_events=False, suppress_timeout_warning=True)
            payload = self._event_json_payload(event)
            run = payload.get(KEY_TESTS_RUN) if isinstance(payload, dict) else None
            if isinstance(run, dict):
                last_run = run
                observed_run_id = self._safe_int(run.get(KEY_RUN_ID), COUNT_ZERO)
                state = str(run.get(KEY_RUN_STATE, EMPTY_STRING)).strip().lower()
                if observed_run_id and observed_run_id > COUNT_ZERO:
                    self._last_test_run_id = observed_run_id
                if run_id is not None and observed_run_id != run_id:
                    time.sleep(TEST_WAIT_POLL_SEC)
                    continue
                if state in RUN_TERMINAL_STATES:
                    return self._finish_tests_wait(run, payload=payload)
            self._print_tests_wait_progress(last_run, run_id, deadline)
            time.sleep(TEST_WAIT_POLL_SEC)
        return self._tests_wait_timeout(run_id, last_run)

    def _handle_tests_run_command(self, line: str) -> Optional[StatusResult]:
        """
        NAME
            _handle_tests_run_command - Handle tests run/run-all with optional wait flags.

        DESCRIPTION
            Keeps the default asynchronous robot command behavior, but adds an
            opt-in wait path so operators can see the finished run summary
            without issuing a separate command.
        """
        mode = self._modes[-1].name
        if mode not in ("exec", MODE_CONFIG):
            return None
        try:
            tokens = self._split_command(line)
        except Exception:
            return None
        if len(tokens) < COUNT_TWO or tokens[COUNT_ZERO].lower() != CMD_TESTS:
            return None
        action = tokens[COUNT_ONE].lower()
        if action not in (CMD_RUN, CMD_RUN_ALL):
            return None
        wait_flag, timeout_sec, timeout_explicit, error = self._parse_tests_run_args(tokens)
        if error:
            print(error)
            return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
        if not self._session.is_connected():
            print(MESSAGE_ERR_SHOW_TESTS_ROBOT_NOT_CONNECTED)
            return StatusResult(code=SS__NETWORK__NOT_CONNECTED)
        if action == CMD_RUN:
            seq = run_test(self._session)
        else:
            seq = run_all_tests(self._session)
        event = self._wait_for_seq(seq)
        self._record_test_run_event(event)
        label = "tests run" if action == CMD_RUN else "tests run-all"
        if self._event_failed(event, label):
            return StatusResult(code=SS__EXECUTOR__FAILED)
        run_payload = self._event_json_payload(event)
        run_id = self._safe_int(run_payload.get(KEY_RUN_ID), None)
        if run_id and run_id > COUNT_ZERO:
            self._last_test_run_id = run_id
        if wait_flag:
            effective_timeout_sec = timeout_sec
            if effective_timeout_sec is None:
                effective_timeout_sec = (
                    TEST_WAIT_RUN_ALL_DEFAULT_TIMEOUT_SEC
                    if action == CMD_RUN_ALL
                    else TEST_WAIT_DEFAULT_TIMEOUT_SEC
                )
            return self._wait_for_test_run_completion(
                run_id,
                effective_timeout_sec,
                run_all=(action == CMD_RUN_ALL),
            )
        self._print_tests_run_started(action, run_id)
        return StatusResult(code=SS__NORMAL)

    def _parse_tests_wait_args(
        self,
        tokens: List[str],
    ) -> tuple[Optional[int], float, Optional[str]]:
        run_id: Optional[int] = None
        timeout_sec = TEST_WAIT_DEFAULT_TIMEOUT_SEC
        index = COUNT_TWO
        while index < len(tokens):
            flag = tokens[index].lower()
            if flag not in (FLAG_RUN, FLAG_TIMEOUT):
                return (None, timeout_sec, "ERROR: tests wait [--run <id>] [--timeout <seconds>]")
            if index + COUNT_ONE >= len(tokens):
                return (None, timeout_sec, "ERROR: tests wait flag requires a value.")
            value = tokens[index + COUNT_ONE]
            try:
                if flag == FLAG_RUN:
                    run_id = int(float(value))
                else:
                    timeout_sec = float(value)
            except ValueError:
                return (None, timeout_sec, "ERROR: tests wait values must be numeric.")
            index += COUNT_TWO
        if timeout_sec <= SLEEP_MIN_SEC or timeout_sec > SLEEP_MAX_SEC:
            return (None, timeout_sec, f"ERROR: timeout must be between {SLEEP_MIN_SEC} and {SLEEP_MAX_SEC}.")
        return (run_id, timeout_sec, None)

    def _parse_tests_run_args(
        self,
        tokens: List[str],
    ) -> tuple[bool, Optional[float], bool, Optional[str]]:
        wait_flag = False
        timeout_sec: Optional[float] = None
        timeout_explicit = False
        index = COUNT_TWO
        while index < len(tokens):
            flag = tokens[index].lower()
            if flag == FLAG_WAIT:
                wait_flag = True
                index += COUNT_ONE
                continue
            if flag == FLAG_TIMEOUT:
                if index + COUNT_ONE >= len(tokens):
                    return (False, timeout_sec, timeout_explicit, "ERROR: tests run --timeout requires a value.")
                try:
                    timeout_sec = float(tokens[index + COUNT_ONE])
                    timeout_explicit = True
                except ValueError:
                    return (False, timeout_sec, timeout_explicit, "ERROR: tests run timeout must be numeric.")
                index += COUNT_TWO
                continue
            return (False, timeout_sec, timeout_explicit, "ERROR: tests run [--wait] [--timeout <seconds>]")
        if timeout_sec is not None and (timeout_sec <= SLEEP_MIN_SEC or timeout_sec > SLEEP_MAX_SEC):
            return (
                False,
                timeout_sec,
                timeout_explicit,
                f"ERROR: timeout must be between {SLEEP_MIN_SEC} and {SLEEP_MAX_SEC}.",
            )
        return (wait_flag, timeout_sec, timeout_explicit, None)

    def _wait_for_test_run_completion(
        self,
        run_id: Optional[int],
        timeout_sec: float,
        run_all: bool,
    ) -> StatusResult:
        deadline = time.time() + timeout_sec
        last_run: Dict[str, object] = {}
        last_payload: Dict[str, object] = {}
        last_terminal_key: tuple[int, str] | None = None
        terminal_polls = COUNT_ZERO
        self._tests_wait_progress_next_sec = 0.0
        while time.time() <= deadline:
            seq = show_tests(self._session, json_output=True)
            event = self._wait_for_seq(seq, print_events=False, suppress_timeout_warning=True)
            payload = self._event_json_payload(event)
            run = payload.get(KEY_TESTS_RUN) if isinstance(payload, dict) else None
            if isinstance(run, dict):
                last_run = run
                last_payload = payload if isinstance(payload, dict) else {}
                observed_run_id = self._safe_int(run.get(KEY_RUN_ID), COUNT_ZERO)
                state = str(run.get(KEY_RUN_STATE, EMPTY_STRING)).strip().lower()
                if observed_run_id and observed_run_id > COUNT_ZERO:
                    self._last_test_run_id = observed_run_id
                if run_all:
                    if run_id is not None and observed_run_id < run_id:
                        time.sleep(TEST_WAIT_POLL_SEC)
                        continue
                    if state in RUN_TERMINAL_STATES:
                        current_key = (observed_run_id, state)
                        if current_key == last_terminal_key:
                            terminal_polls += COUNT_ONE
                        else:
                            last_terminal_key = current_key
                            terminal_polls = COUNT_ONE
                        if terminal_polls >= TEST_WAIT_RUN_ALL_SETTLE_POLLS:
                            return self._finish_tests_wait(run, payload=last_payload, run_all=True)
                    else:
                        last_terminal_key = None
                        terminal_polls = COUNT_ZERO
                else:
                    if run_id is not None and observed_run_id != run_id:
                        time.sleep(TEST_WAIT_POLL_SEC)
                        continue
                    if state in RUN_TERMINAL_STATES:
                        return self._finish_tests_wait(run, payload=last_payload)
            self._print_tests_wait_progress(last_run, run_id, deadline, run_all=run_all)
            time.sleep(TEST_WAIT_POLL_SEC)
        return self._tests_wait_timeout(run_id, last_run)

    def _print_tests_run_started(self, action: str, run_id: Optional[int]) -> None:
        if action == CMD_RUN_ALL:
            if run_id and run_id > COUNT_ZERO:
                print(f"Run-all started: first runId={run_id}. Use `tests wait --run {run_id}` for completion summary.")
                return
            print("Run-all started. Use `tests wait` for completion summary.")
            return
        if run_id and run_id > COUNT_ZERO:
            print(f"Test run started: runId={run_id}. Use `tests wait --run {run_id}` for completion summary.")
            return
        print("Test run started. Use `tests wait` for completion summary.")

    def _print_tests_wait_progress(
        self,
        run: Dict[str, object],
        run_id: Optional[int],
        deadline: float,
        run_all: bool = False,
    ) -> None:
        now = time.time()
        next_due = getattr(self, "_tests_wait_progress_next_sec", 0.0)
        if now < next_due:
            return
        self._tests_wait_progress_next_sec = now + TEST_WAIT_PROGRESS_PERIOD_SEC
        observed_run_id = self._safe_int(run.get(KEY_RUN_ID), COUNT_ZERO) if run else COUNT_ZERO
        state = str(run.get(KEY_RUN_STATE, EMPTY_STRING)).strip().lower() if run else ""
        test_name = str(run.get(KEY_RUN_TEST, EMPTY_STRING)).strip() if run else ""
        remaining = max(0.0, deadline - now)
        label = "run-all" if run_all else "test"
        effective_run_id = run_id or observed_run_id or 0
        state_text = state or RUN_STATE_STARTING
        if test_name:
            print(
                f"Waiting for {label} completion: runId={effective_run_id} "
                f"state={state_text} test={test_name} remaining={remaining:.1f}s"
            )
            return
        print(
            f"Waiting for {label} completion: runId={effective_run_id} "
            f"state={state_text} remaining={remaining:.1f}s"
        )

    def _finish_tests_wait(
        self,
        run: Dict[str, object],
        payload: Optional[Dict[str, object]] = None,
        run_all: bool = False,
    ) -> StatusResult:
        state = str(run.get(KEY_RUN_STATE, EMPTY_STRING)).strip().lower()
        run_id = self._safe_int(run.get(KEY_RUN_ID), COUNT_ZERO)
        test_name = str(run.get(KEY_RUN_TEST, EMPTY_STRING)).strip()
        result = str(run.get(KEY_RUN_RESULT, EMPTY_STRING)).strip()
        message = str(run.get(KEY_RUN_MESSAGE, EMPTY_STRING)).strip()
        status = str(run.get(KEY_RUN_STATUS, EMPTY_STRING)).strip()
        started_ms = self._safe_int(run.get(KEY_RUN_STARTED_AT_MS), COUNT_ZERO) or COUNT_ZERO
        finished_ms = self._safe_int(run.get(KEY_RUN_FINISHED_AT_MS), COUNT_ZERO) or COUNT_ZERO
        elapsed_sec: Optional[float] = None
        if started_ms > 0 and finished_ms >= started_ms:
            elapsed_sec = (finished_ms - started_ms) / 1000.0
        header = "Run-all complete:" if run_all else "Test run complete:"
        print(header)
        print(f"  runId: {run_id}")
        if test_name:
            print(f"  test: {test_name}")
        print(f"  state: {state}")
        if result:
            print(f"  result: {result}")
        if elapsed_sec is not None:
            print(f"  elapsed: {elapsed_sec:.2f}s")
        if status:
            print(f"  status: {status}")
        if message:
            print(f"  message: {message}")
        details = run.get(KEY_RUN_DETAILS)
        self._print_test_run_details(details)
        if run_all:
            self._print_run_all_rows_summary(payload)
        if state in RUN_SUCCESS_STATES:
            return StatusResult(code=SS__NORMAL)
        return StatusResult(code=SS__EXECUTOR__FAILED)

    def _print_test_run_details(self, details: object) -> None:
        if not isinstance(details, dict):
            return
        requires = details.get("requires")
        if isinstance(requires, list) and requires:
            print("  require:")
            for entry in requires:
                if not isinstance(entry, dict):
                    continue
                ident = str(entry.get("id", EMPTY_STRING)).strip()
                text = str(entry.get("text", EMPTY_STRING)).strip()
                satisfied = bool(entry.get("satisfied", False))
                sample = entry.get("sampleValue")
                when_sec = entry.get("satisfiedAtSec")
                label = "PASS" if satisfied else "FAIL"
                line = f"    {ident or '(unnamed)'} {label}"
                if text:
                    line = f"{line}  {text}"
                if satisfied and when_sec is not None:
                    line = f"{line}  at={when_sec}"
                if sample is not None:
                    line = f"{line}  sample={sample}"
                print(line)
        last_samples = details.get("lastSamples")
        if isinstance(last_samples, dict) and last_samples:
            print("  lastSamples:")
            for key in sorted(last_samples.keys()):
                print(f"    {key}: {last_samples[key]}")
        unsafe_exit = details.get("unsafeExit")
        if isinstance(unsafe_exit, list) and unsafe_exit:
            print("  unsafeExit:")
            for entry in unsafe_exit:
                if not isinstance(entry, dict):
                    continue
                text = str(entry.get("text", EMPTY_STRING)).strip()
                if text:
                    print(f"    {text}")

    def _print_run_all_rows_summary(self, payload: Optional[Dict[str, object]]) -> None:
        if not isinstance(payload, dict):
            return
        rows = payload.get("rows")
        if not isinstance(rows, list) or not rows:
            return
        print("  tests:")
        for entry in rows:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get(KEY_TESTS_NAME, EMPTY_STRING)).strip()
            status = str(entry.get(KEY_TESTS_STATUS, EMPTY_STRING)).strip()
            enabled = bool(entry.get(KEY_TESTS_ENABLED, False))
            if not enabled:
                continue
            print(f"    {name}: {status}")

    def _tests_wait_timeout(
        self,
        run_id: Optional[int],
        last_run: Dict[str, object],
    ) -> StatusResult:
        state = str(last_run.get(KEY_RUN_STATE, EMPTY_STRING)).strip().lower() if last_run else ""
        observed = self._safe_int(last_run.get(KEY_RUN_ID), COUNT_ZERO) if last_run else COUNT_ZERO
        print(f"ERROR: Timeout waiting for test run runId={run_id or observed} state={state or RUN_STATE_TIMEOUT}.")
        return StatusResult(code=SS__EXECUTOR__FAILED)

    def _event_json_payload(self, event: Optional[BridgeEvent]) -> Dict[str, object]:
        if event is None or not event.json_text:
            return {}
        try:
            payload = json.loads(event.json_text)
        except Exception:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _safe_int(self, value: object, default: Optional[int]) -> Optional[int]:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default

    def _handle_active_command(self, line: str) -> Optional[StatusResult]:
        """
        NAME
            _handle_active_command - Execute active-group shorthand commands.
        """
        if self._modes[-1].name != "exec":
            return None
        try:
            tokens = self._split_command(line)
        except Exception:
            return None
        if not tokens:
            return None
        if tokens[COUNT_ZERO].lower() != CMD_ACTIVE_SHORT:
            return None
        if len(tokens) < COUNT_TWO:
            print("ERROR: active requires add/next/show.")
            return StatusResult(code=SS__CLI_VALIDATOR__REQUIRED)
        action = tokens[COUNT_ONE].lower()
        if action == CMD_ACTIVE_SHOW_SHORT:
            wants_json = FLAG_JSON in [token.lower() for token in tokens[COUNT_TWO:]]
            seq = active_show(self._session, json_output=wants_json)
            self._wait_for_seq(seq)
            return StatusResult(code=SS__NORMAL)
        if action == CMD_ACTIVE_ADD_SHORT:
            seq = active_add(self._session)
            self._wait_for_seq(seq)
            return StatusResult(code=SS__NORMAL)
        if action == CMD_ACTIVE_NEXT_SHORT:
            seq = active_next(self._session)
            self._wait_for_seq(seq)
            return StatusResult(code=SS__NORMAL)
        print("ERROR: active requires add/next/show.")
        return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)

    def _dispatch_instantiate_command(
        self,
        action: str,
    ) -> StatusResult:
        """
        NAME
            _dispatch_instantiate_command - Execute runtime instantiation commands.
        """
        if not self._session.is_connected():
            print("ERROR: Robot source unavailable (not connected).")
            return StatusResult(code=SS__NETWORK__ROBOT_UNAVAILABLE)
        if action == CMD_NEXT:
            seq = add_next_motor(self._session)
            label = f"{CMD_INSTANTIATE} {CMD_NEXT} {CMD_MOTOR}"
        else:
            seq = add_all_devices(self._session)
            label = f"{CMD_INSTANTIATE} {CMD_ALL} {CMD_DEVICES}"
        event = self._wait_for_seq(seq)
        if self._event_failed(event, label):
            return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
        return StatusResult(code=SS__NORMAL)

    def _handle_member_membership_action(
        self,
        target_name: str,
        action: str,
        subject: str,
    ) -> StatusResult:
        """
        NAME
            _handle_member_membership_action - Apply one local group membership edit.
        """
        if action == CMD_ASSIGN:
            return self._add_local_group_member(target_name, subject)
        if action == CMD_REMOVE:
            return self._remove_local_group_member(target_name, subject)
        return self._set_local_member_enabled(target_name, subject, action)

    def _runtime_active_group_edit_action_state(self) -> HostActionAccessState:
        """
        NAME
            _runtime_active_group_edit_action_state - Return the shared active-group edit gate for connected robot edits.
        """
        payload = self._fetch_robot_runtime_payload(print_events=False)
        session_state = self._session.get_state_snapshot()
        runtime_state_seen = isinstance(payload, dict)
        controlled_lifecycle_active = (
            bool(payload.get(KEY_CONTROLLED_LIFECYCLE_ACTIVE, False))
            if isinstance(payload, dict)
            else False
        )
        robot_enabled = (
            bool(payload.get(KEY_ENABLED, False))
            if isinstance(payload, dict)
            else bool(session_state.get(NT_STATE_ENABLED, False))
            if isinstance(session_state, dict)
            else False
        )
        robot_estopped = (
            bool(payload.get(KEY_ESTOPPED, False))
            if isinstance(payload, dict)
            else bool(session_state.get(NT_STATE_ESTOPPED, False))
            if isinstance(session_state, dict)
            else False
        )
        robot_mode = (
            str(payload.get(KEY_MODE, EMPTY_STRING)).strip().lower()
            if isinstance(payload, dict)
            else EMPTY_STRING
        )
        runnable_scope_state = resolve_runnable_scope_state(
            scope_kind=CLI_ACTIVE_GROUP_EDIT_SCOPE_KIND,
            local_selected_profile=self._active_profile_name(),
            local_profile_required=not bool(self._active_profile_name()),
            tcp_connected=True,
            runtime_state_seen=runtime_state_seen,
            stale_state=False,
            robot_enabled=robot_enabled,
            robot_estopped=robot_estopped,
            robot_mode=robot_mode,
            manual_group_empty=False,
            scope_active=controlled_lifecycle_active,
        )
        scope_control_state = resolve_scope_control_state(
            scope_kind=CLI_ACTIVE_GROUP_EDIT_SCOPE_KIND,
            runtime_ui_ready=True,
            tracker_pending=self._tracker.is_pending(),
            stale_state=False,
            runtime_state_seen=runtime_state_seen,
            controlled_lifecycle_active=controlled_lifecycle_active,
            transition_pending=False,
            runnable_scope_state=runnable_scope_state,
            selected_test_name=EMPTY_STRING,
            selected_test_ready=False,
            selected_test_invalid=False,
            selected_test_running=False,
            selected_test_runtime_block_reason=EMPTY_STRING,
        )
        return resolve_active_group_edit_action_state(
            tcp_connected=True,
            tracker_pending=self._tracker.is_pending(),
            controlled_lifecycle_active=controlled_lifecycle_active,
            scope_control_state=scope_control_state,
        )

    def _guard_runtime_active_group_edit(self, group_name: str) -> Optional[StatusResult]:
        """
        NAME
            _guard_runtime_active_group_edit - Block connected active-group edits when the shared ownership gate is closed.
        """
        if not self._session.is_connected() or not self._is_active_group(group_name):
            return None
        action_state = self._runtime_active_group_edit_action_state()
        if action_state.allowed:
            return None
        print(str(action_state.blocked_reason or SCOPE_CONTROL_BLOCKED_WAITING_TEXT))
        return StatusResult(code=SS__EXECUTOR__FAILED, message=action_state.blocked_reason)

    def _handle_member_assign_selector(
        self,
        target_name: str,
        selector: str,
    ) -> StatusResult:
        """
        NAME
            _handle_member_assign_selector - Apply member assign all/next.
        """
        if selector == CMD_ALL:
            labels = self._device_sequence_labels()
            members = self._list_target_group_members(target_name)
            if members is None:
                print(ERR_GROUP_NOT_FOUND_FMT.format(name=target_name))
                return StatusResult(code=SS__GROUP__NOT_FOUND)
            seen = {label.lower() for label in members}
            for label in labels:
                key = label.lower()
                if key in seen:
                    print(WARN_DUPLICATE_MEMBER.format(device=label))
                    continue
                members.append(label)
                seen.add(key)
            return self._write_target_group_members(target_name, members)
        next_label = self._next_device_label()
        if not next_label:
            print(ERR_NO_DEVICES_AVAILABLE_MEMBER_ASSIGN)
            return StatusResult(code=SS__CONFIG__INVALID)
        return self._add_local_group_member(target_name, next_label)

    def _handle_group_targeting_command(self, line: str) -> Optional[StatusResult]:
        """
        NAME
            _handle_group_targeting_command - Handle V1 group/targeting commands before parser.
        """
        try:
            tokens = self._split_command(line)
        except Exception:
            return None
        if not tokens:
            return None
        mode = self._modes[-1].name
        normalized = [token.lower() for token in tokens]
        cmd = normalized[COUNT_ZERO]

        if cmd == CMD_INSTANTIATE:
            if mode not in (MODE_EXEC, MODE_CONFIG):
                return None
            if len(tokens) == COUNT_THREE and normalized[COUNT_ONE] == CMD_NEXT and normalized[COUNT_TWO] == CMD_MOTOR:
                return self._dispatch_instantiate_command(CMD_NEXT)
            if len(tokens) == COUNT_THREE and normalized[COUNT_ONE] == CMD_ALL and normalized[COUNT_TWO] == CMD_DEVICES:
                return self._dispatch_instantiate_command(CMD_ALL)
            print(MESSAGE_ERR_INSTANTIATE_USAGE)
            return StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX)

        if (
            cmd == CMD_ADD
            and mode in (MODE_EXEC, MODE_CONFIG)
            and len(tokens) == COUNT_TWO
            and normalized[COUNT_ONE] in (CMD_NEXT, CMD_ALL)
            and mode != MODE_GROUP
        ):
            canonical = (
                f"{CMD_INSTANTIATE} {CMD_NEXT} {CMD_MOTOR}"
                if normalized[COUNT_ONE] == CMD_NEXT
                else f"{CMD_INSTANTIATE} {CMD_ALL} {CMD_DEVICES}"
            )
            print(MESSAGE_ERR_ALIAS_REMOVED.format(alias=" ".join(tokens), canonical=canonical))
            return StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX)

        if mode not in (MODE_CONFIG, CMD_GROUP):
            return None
        if cmd not in (CMD_GROUP, CMD_NO, CMD_COPY, CMD_ADD, CMD_REMOVE, CMD_MEMBER):
            return None
        if cmd == CMD_ADD and normalized[COUNT_ONE:COUNT_TWO] not in ([CMD_DEVICE], [CMD_ALL], [CMD_NEXT]):
            return None
        if cmd == CMD_REMOVE and normalized[COUNT_ONE:COUNT_TWO] != [CMD_DEVICE]:
            return None
        if cmd == CMD_COPY and normalized[COUNT_ONE:COUNT_TWO] != [CMD_GROUP]:
            return None
        if cmd == CMD_NO and normalized[COUNT_ONE:COUNT_TWO] not in ([CMD_GROUP], [CMD_DEVICE]):
            return None
        self._ensure_local_config()
        if not self._local_config:
            print(MESSAGE_ERR_LOCAL_CONFIG_MISSING)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        profile = self._require_active_profile()
        if not profile:
            return StatusResult(code=SS__CONFIG__PROFILE_REQUIRED)

        explicit_group: Optional[str] = None
        if len(tokens) >= COUNT_FOUR and normalized[-2] == CMD_GROUP:
            explicit_group = tokens[-1]

        if cmd == CMD_GROUP and len(tokens) >= COUNT_FIVE and normalized[COUNT_ONE] == CMD_MEMBER:
            action = normalized[COUNT_TWO]
            if action not in (CMD_ASSIGN, CMD_REMOVE, CMD_ENABLE, CMD_DISABLE, CMD_TOGGLE):
                print(MESSAGE_ERR_MEMBER_ACTION)
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            if action == CMD_ASSIGN and normalized[COUNT_THREE] in (CMD_ALL, CMD_NEXT):
                return self._handle_member_assign_selector(tokens[4], normalized[COUNT_THREE])
            return self._handle_member_membership_action(tokens[3], action, tokens[4])

        if cmd == CMD_MEMBER and len(tokens) >= COUNT_THREE:
            if normalized[COUNT_ONE] in (CMD_ASSIGN, CMD_REMOVE, CMD_ENABLE, CMD_DISABLE, CMD_TOGGLE):
                action = normalized[COUNT_ONE]
                target_name = self._target_group_name(None)
                if action == CMD_ASSIGN and normalized[COUNT_TWO] in (CMD_ALL, CMD_NEXT):
                    return self._handle_member_assign_selector(target_name, normalized[COUNT_TWO])
                return self._handle_member_membership_action(target_name, action, tokens[2])
            if normalized[COUNT_TWO] in (CMD_ENABLE, CMD_DISABLE, CMD_TOGGLE):
                canonical = f"{CMD_MEMBER} {normalized[COUNT_TWO]} {tokens[1]}"
                print(MESSAGE_ERR_ALIAS_REMOVED.format(alias=" ".join(tokens), canonical=canonical))
                return StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX)
            print(MESSAGE_ERR_MEMBER_ACTION)
            return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)

        if cmd == CMD_GROUP and len(tokens) == COUNT_THREE and normalized[1] == CMD_CREATE:
            result = self._create_local_group(tokens[2])
            if not result.ok():
                return result
            self._modes.append(CliMode(CMD_GROUP, tokens[2]))
            return StatusResult(code=SS__NORMAL)

        if cmd == CMD_GROUP and len(tokens) == COUNT_THREE and normalized[1] == CMD_DELETE:
            if not self._batch and not self._confirm(f"Delete group '{tokens[2]}'?"):
                return StatusResult(code=SS__EXECUTOR__CANCELLED)
            return self._delete_local_group(tokens[2])

        if cmd == CMD_NO and len(tokens) == COUNT_THREE and normalized[1] == CMD_GROUP:
            if not self._batch and not self._confirm(f"Delete group '{tokens[2]}'?"):
                return StatusResult(code=SS__EXECUTOR__CANCELLED)
            return self._delete_local_group(tokens[2])

        if cmd == CMD_GROUP and len(tokens) == COUNT_FOUR and normalized[1] == CMD_RENAME:
            return self._rename_local_group(tokens[2], tokens[3])

        if cmd == CMD_GROUP and normalized[1:2] == [CMD_CLEAR]:
            target_name = tokens[2] if len(tokens) >= COUNT_THREE else self._target_group_name(None)
            return self._clear_local_group_members(target_name)

        if cmd == CMD_COPY and len(tokens) == COUNT_FOUR and normalized[1] == CMD_GROUP:
            return self._copy_local_group(tokens[2], tokens[3])

        if cmd == CMD_ADD and len(tokens) >= COUNT_THREE and normalized[1] == CMD_DEVICE:
            if explicit_group is not None:
                target_name = explicit_group
            else:
                target_name = self._target_group_name(None)
            canonical = (
                f"{CMD_GROUP} {CMD_MEMBER} {CMD_ASSIGN} {target_name} {tokens[2]}"
                if explicit_group is not None
                else f"{CMD_MEMBER} {CMD_ASSIGN} {tokens[2]}"
            )
            print(MESSAGE_ERR_ALIAS_REMOVED.format(alias=" ".join(tokens), canonical=canonical))
            return StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX)

        if cmd == CMD_REMOVE and len(tokens) >= COUNT_THREE and normalized[1] == CMD_DEVICE:
            if explicit_group is not None:
                target_name = explicit_group
            else:
                target_name = self._target_group_name(None)
            canonical = (
                f"{CMD_GROUP} {CMD_MEMBER} {CMD_REMOVE} {target_name} {tokens[2]}"
                if explicit_group is not None
                else f"{CMD_MEMBER} {CMD_REMOVE} {tokens[2]}"
            )
            print(MESSAGE_ERR_ALIAS_REMOVED.format(alias=" ".join(tokens), canonical=canonical))
            return StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX)

        if (
            cmd == CMD_NO
            and len(tokens) >= COUNT_THREE
            and normalized[1] == CMD_DEVICE
            and (mode == CMD_GROUP or explicit_group is not None)
        ):
            if explicit_group is not None:
                target_name = explicit_group
            else:
                target_name = self._target_group_name(None)
            canonical = (
                f"{CMD_GROUP} {CMD_MEMBER} {CMD_REMOVE} {target_name} {tokens[2]}"
                if explicit_group is not None
                else f"{CMD_MEMBER} {CMD_REMOVE} {tokens[2]}"
            )
            print(MESSAGE_ERR_ALIAS_REMOVED.format(alias=" ".join(tokens), canonical=canonical))
            return StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX)

        if (
            cmd == CMD_ADD
            and len(tokens) >= COUNT_TWO
            and normalized[1] == CMD_ALL
            and (mode == CMD_GROUP or explicit_group is not None)
        ):
            target_name = self._target_group_name(explicit_group)
            canonical = (
                f"{CMD_GROUP} {CMD_MEMBER} {CMD_ASSIGN} {CMD_ALL} {target_name}"
                if explicit_group is not None
                else f"{CMD_MEMBER} {CMD_ASSIGN} {CMD_ALL}"
            )
            print(MESSAGE_ERR_ALIAS_REMOVED.format(alias=" ".join(tokens), canonical=canonical))
            return StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX)

        if cmd == CMD_ADD and len(tokens) >= COUNT_TWO and normalized[1] == CMD_NEXT:
            target_name = self._target_group_name(explicit_group)
            canonical = (
                f"{CMD_GROUP} {CMD_MEMBER} {CMD_ASSIGN} {CMD_NEXT} {target_name}"
                if explicit_group is not None
                else f"{CMD_MEMBER} {CMD_ASSIGN} {CMD_NEXT}"
            )
            print(MESSAGE_ERR_ALIAS_REMOVED.format(alias=" ".join(tokens), canonical=canonical))
            return StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX)

        return None

    def _handle_reset_zero_config_command(self, line: str) -> Optional[StatusResult]:
        """
        NAME
            _handle_reset_zero_config_command - Delete the deploy-owned unified config file.

        DESCRIPTION
            Handles exec-mode shorthand `reset zero-config [--yes]` before parser
            execution so operators can perform a guarded zero-config reset from the
            same CLI session used for bringup work.
        """
        if self._modes[-1].name != "exec":
            return None
        try:
            tokens = self._split_command(line)
        except Exception:
            return None
        if not tokens:
            return None
        if tokens[COUNT_ZERO].lower() != CMD_RESET:
            return None
        if len(tokens) < COUNT_TWO or tokens[COUNT_ONE].lower() != CMD_ZERO_CONFIG:
            print(MESSAGE_HINT_RESET_ZERO_CONFIG)
            return StatusResult(code=SS__CLI_VALIDATOR__REQUIRED)

        force_yes = False
        clear_memory = False
        for token in tokens[COUNT_TWO:]:
            token_lower = token.lower()
            if token_lower == FLAG_YES:
                force_yes = True
                continue
            if token_lower == FLAG_CLEAR_MEMORY:
                clear_memory = True
                continue
            print(MESSAGE_HINT_RESET_ZERO_CONFIG)
            return StatusResult(code=SS__CLI_PARSER__INVALID_FLAG)

        canonical_path = self._config_repository.canonical_path()
        deploy_path = self._config_repository.deploy_path()
        print(MESSAGE_RESET_ZERO_CONFIG_WARNING)
        print(MESSAGE_RESET_ZERO_CONFIG_TARGET.format(path=canonical_path))
        print(MESSAGE_RESET_ZERO_CONFIG_TARGET.format(path=deploy_path))

        if not force_yes and not self._confirm(MESSAGE_RESET_ZERO_CONFIG_CONFIRM):
            print(MESSAGE_RESET_ZERO_CONFIG_CANCELLED)
            return StatusResult(code=SS__EXECUTOR__CANCELLED)

        deleted_count = COUNT_ZERO
        missing_count = COUNT_ZERO
        for target_path in (canonical_path, deploy_path):
            if not target_path.exists():
                print(MESSAGE_RESET_ZERO_CONFIG_MISSING.format(path=target_path))
                missing_count += COUNT_ONE
                continue
            try:
                target_path.unlink()
            except OSError as error:
                print(MESSAGE_RESET_ZERO_CONFIG_FAILED.format(path=target_path, error=error))
                return StatusResult(code=SS__EXECUTOR__FAILED)
            print(MESSAGE_RESET_ZERO_CONFIG_DELETED.format(path=target_path))
            deleted_count += COUNT_ONE

        print(
            MESSAGE_RESET_ZERO_CONFIG_DONE.format(
                deleted=deleted_count,
                missing=missing_count,
            )
        )
        if clear_memory:
            self._clear_in_memory_workspace_state()
            print(MESSAGE_RESET_ZERO_CONFIG_MEMORY_CLEARED)
        return StatusResult(code=SS__NORMAL)

    def _fallback_device_set(self, tokens: List[str]) -> bool:
        """
        NAME
            _fallback_device_set - Allow device set values that collide with keywords.
        """
        if self._modes[-1].name != MODE_CONFIG:
            return False
        if len(tokens) < COUNT_FIVE:
            return False
        if tokens[COUNT_ZERO].lower() != CMD_DEVICE:
            return False
        if tokens[COUNT_TWO].lower() != CMD_SET:
            return False
        field = tokens[COUNT_THREE]
        if field not in DEVICE_FIELDS_PROFILE:
            return False
        return True


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
        try:
            tokens = self._split_command(line)
        except Exception as exc:
            print(f"ERROR: {exc}")
            return True
        if not tokens:
            return False
        tokens = self._normalize_question_tokens(tokens)
        if not tokens or tokens[-1] != QUESTION_MARK:
            return False
        base_tokens = self._parser.normalize_tokens(tokens[:-1], self._modes[-1].name)
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
        if suggestions == [MESSAGE_NO_KNOWN_VALUES]:
            print(MESSAGE_NO_KNOWN_VALUES)
            return
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

    def _contextual_value_suggestions(self, tokens: List[str]) -> Optional[List[str]]:
        """
        NAME
            _contextual_value_suggestions - Provide inline value lists for '?' help.
        """

        if not tokens:
            return None
        mode = self._modes[-1].name
        lowered = [token.lower() for token in tokens]
        cmd = lowered[COUNT_ZERO]
        if mode == MODE_CONFIG:
            if len(lowered) >= 4 and cmd == CMD_DEVICE and lowered[COUNT_TWO] == CMD_SET:
                return self._device_field_values(lowered[COUNT_THREE])
            if cmd == CMD_BINDINGS:
                return self._bindings_value_help(lowered)
            if cmd == CMD_CAN_MAPPINGS:
                return self._mappings_value_help(lowered)
        if mode == PARSER_SPEC.msg_mode_name_device and cmd == CMD_SET and len(lowered) >= 2:
            return self._device_field_values(lowered[COUNT_ONE])
        if mode == MODE_TEST:
            if cmd == CMD_INPUT_SOURCE and len(lowered) == COUNT_ONE:
                return self._input_source_values()
            if cmd == CMD_DEADBAND and len(lowered) == COUNT_ONE:
                return [self._format_range("deadband", DEADBAND_MIN, DEADBAND_MAX)]
            if cmd == CMD_DUTY and len(lowered) == COUNT_ONE:
                return [self._format_range("duty", DUTY_MIN, DUTY_MAX)]
            if cmd == CMD_BRIGHTNESS and len(lowered) == COUNT_ONE:
                return [self._format_range("brightness", BRIGHTNESS_MIN, BRIGHTNESS_MAX)]
            if cmd == CMD_DURATION and len(lowered) == COUNT_ONE:
                return [self._format_minimum("durationSec", DURATION_MIN_SEC)]
            if cmd == CMD_TERMINATION:
                if len(lowered) == COUNT_ONE:
                    return [TERMINATION_HOLD, TERMINATION_TIME, TERMINATION_ROTATION, TERMINATION_LIMITSWITCH]
                if len(lowered) == COUNT_TWO and lowered[COUNT_ONE] == TERMINATION_TIME:
                    return [self._format_minimum("timeSec", TIME_MIN_SEC)]
                if len(lowered) == COUNT_TWO and lowered[COUNT_ONE] == TERMINATION_ROTATION:
                    return [self._format_minimum("rotation", ROTATION_MIN)]
                if len(lowered) == COUNT_TWO and lowered[COUNT_ONE] == TERMINATION_LIMITSWITCH:
                    return self._limit_switch_labels()
            if cmd == CMD_TIME:
                if len(lowered) == COUNT_ONE:
                    return ["timeout", "onTimeout"]
                if len(lowered) == COUNT_TWO and lowered[COUNT_ONE] == "timeout":
                    return [self._format_minimum("timeoutSec", TIME_MIN_SEC)]
                if len(lowered) == COUNT_TWO and lowered[COUNT_ONE] == "ontimeout":
                    return ["pass", "fail"]
            if cmd == CMD_ROTATION:
                if len(lowered) == COUNT_ONE:
                    return [
                        "limit",
                        "encoderKey",
                        "encoderSource",
                        "encoderMotorIndex",
                        "encoderCountsPerRev",
                    ]
                if len(lowered) == COUNT_TWO and lowered[COUNT_ONE] == "limit":
                    return [self._format_minimum("limitRot", ROTATION_MIN)]
                if len(lowered) == COUNT_TWO and lowered[COUNT_ONE] == "encodermotorindex":
                    return ["integer >= 0"]
                if len(lowered) == COUNT_TWO and lowered[COUNT_ONE] == "encodercountsperrev":
                    return ["number > 0"]
            if cmd == CMD_HOLD:
                if len(lowered) == COUNT_ONE:
                    return ["onRelease"]
                if len(lowered) == COUNT_TWO and lowered[COUNT_ONE] == "onrelease":
                    return ["pass", "fail"]
            if cmd == CMD_LIMITSWITCH:
                if len(lowered) == COUNT_ONE:
                    return ["onHit", "id"]
                if len(lowered) == COUNT_TWO and lowered[COUNT_ONE] == "onhit":
                    return ["pass", "fail"]
                if len(lowered) == COUNT_TWO and lowered[COUNT_ONE] == "id":
                    return self._limit_switch_labels()
        return None

    def _device_field_values(self, field: str) -> Optional[List[str]]:
        """
        NAME
            _device_field_values - Provide value lists for device fields.
        """

        if field == FIELD_DEVICE_INTERFACE:
            return sorted(DEVICE_INTERFACE_ALLOWED)
        if field == FIELD_MANUFACTURER:
            return self._mappings_values(KEY_MANUFACTURERS)
        if field == FIELD_DEVICE_TYPE:
            return self._mappings_values(KEY_DEVICE_TYPES)
        if field == FIELD_TYPE:
            return ["motor", "sensor", "limitSwitch"]
        if field == FIELD_TERMINATOR:
            return ["true", "false"]
        return None

    def _bindings_value_help(self, tokens: List[str]) -> Optional[List[str]]:
        """
        NAME
            _bindings_value_help - Contextual '?' for bindings commands.
        """

        if len(tokens) < COUNT_TWO:
            return None
        sub = tokens[COUNT_ONE]
        if sub == CMD_BINDING and len(tokens) >= 5 and tokens[COUNT_TWO] == CMD_SET:
            field = tokens[COUNT_FOUR]
            if field == KEY_INPUT:
                return sorted(BINDINGS_INPUT_KINDS)
            if field == KEY_ID:
                return sorted(AXIS_INPUTS | BUTTON_INPUTS)
            if field == KEY_MODE:
                return ["analog", "edge", "hold", "toggle"]
            if field == KEY_DEADBAND:
                return [self._format_range("deadband", DEADBAND_MIN, DEADBAND_MAX)]
            if field == KEY_INVERT:
                return ["true", "false"]
        if sub == CMD_BINDING and len(tokens) >= 6 and tokens[COUNT_TWO] == CMD_ADD:
            input_kind = tokens[COUNT_FOUR]
            if input_kind == "axis":
                return ["analog", KEY_INVERT, KEY_DEADBAND]
            if tokens[-1] == KEY_MODE:
                return ["analog", "edge", "hold", "toggle"]
            if tokens[-1] == KEY_INVERT:
                return ["true", "false"]
            if tokens[-1] == KEY_DEADBAND:
                return [self._format_range("deadband", DEADBAND_MIN, DEADBAND_MAX)]
        return None

    def _mappings_value_help(self, tokens: List[str]) -> Optional[List[str]]:
        """
        NAME
            _mappings_value_help - Contextual '?' for can-mappings commands.
        """

        if len(tokens) < COUNT_TWO:
            return None
        sub = tokens[COUNT_ONE]
        if sub == CMD_MANUFACTURER:
            return self._mappings_values(KEY_MANUFACTURERS)
        if sub == CMD_DEVICE_TYPE_NAME:
            return self._mappings_values(KEY_DEVICE_TYPES)
        return None

    def _mappings_values(self, key: str) -> List[str]:
        """
        NAME
            _mappings_values - Format mappings entries as inline id=name values.
        """

        if not self._ensure_can_mappings_loaded() or not isinstance(self._can_mappings, dict):
            return [MESSAGE_NO_KNOWN_VALUES]
        mapping = self._can_mappings.get(key)
        if not isinstance(mapping, dict) or not mapping:
            return [MESSAGE_NO_KNOWN_VALUES]
        entries = []
        for raw_id, name in mapping.items():
            entries.append(f"{raw_id}={name}")
        return sorted(entries, key=lambda item: int(item.split("=", 1)[0]) if item.split("=", 1)[0].isdigit() else item)

    def _input_source_values(self) -> List[str]:
        """
        NAME
            _input_source_values - Enumerate controller.inputSource values.
        """

        controllers = sorted(load_controller_names(self._bindings_path))
        inputs = sorted(AXIS_INPUTS | BUTTON_INPUTS)
        if not controllers or not inputs:
            return [MESSAGE_NO_KNOWN_VALUES]
        values: List[str] = []
        for controller in controllers:
            for input_id in inputs:
                values.append(f"{controller}.{input_id}")
        return values

    def _limit_switch_labels(self) -> List[str]:
        """
        NAME
            _limit_switch_labels - Provide limit switch labels for '?' help.
        """

        labels: List[str] = []
        catalog = self._tests_device_catalog or {}
        for name, entry in catalog.items():
            if not isinstance(entry, dict):
                continue
            device_type = str(entry.get(KEY_TYPE, "")).strip()
            if device_type == LIMIT_SWITCH_DEVICE_TYPE:
                labels.append(name)
        if not labels:
            return [MESSAGE_NO_KNOWN_VALUES]
        return sorted(labels)

    @staticmethod
    def _format_range(label: str, minimum: float, maximum: float) -> str:
        return f"{label}: {minimum}..{maximum}"

    @staticmethod
    def _format_minimum(label: str, minimum: float) -> str:
        return f"{label}: >= {minimum}"

    def _suggest_next_args(self, tokens: List[str]) -> List[str]:
        """
        NAME
            _suggest_next_args - Compute next-argument suggestions.
        """
        contextual = self._contextual_value_suggestions(tokens)
        if contextual is not None:
            return contextual
        mode = self._modes[-1].name
        lowered = [token.lower() for token in tokens]
        if lowered:
            cmd = lowered[COUNT_ZERO]
            if cmd == CMD_BINDINGS:
                return self._suggest_bindings_args(lowered[COUNT_ONE:])
            if mode == MODE_GROUP and cmd == CMD_BIND:
                return self._suggest_group_bind_args(tokens[COUNT_ONE:])
        return self._parser.expected_suggestions(tokens, mode)

    def _suggest_diagnose_args(self, tokens: List[str]) -> List[str]:
        """
        NAME
            _suggest_diagnose_args - Suggest diagnose command arguments.
        """
        if not tokens:
            return [CMD_MOTOR, CMD_DEVICE]
        if len(tokens) == COUNT_ONE and tokens[COUNT_ZERO].lower() in (CMD_MOTOR, CMD_DEVICE):
            return [PLACEHOLDER_DEVICE]
        return []

    def _mode_root_suggestions(self, mode: str) -> List[str]:
        """
        NAME
            _mode_root_suggestions - Suggest top-level commands for a mode.
        """
        if mode == MODE_CONFIG:
            return [
                CMD_SHOW,
                "lifecycle",
                CMD_GROUP,
                CMD_NO,
                CMD_PROFILE,
                CMD_PROFILES,
                CMD_CONFIG,
                CMD_DIAGNOSE,
                PARSER_SPEC.cmd_selected_device,
                PARSER_SPEC.cmd_selected_mode,
                PARSER_SPEC.cmd_merge,
                PARSER_SPEC.cmd_import,
                PARSER_SPEC.cmd_export,
                CMD_SAVE,
                CMD_LOAD,
                CMD_RENAME,
                CMD_DEVICE,
                CMD_BINDINGS,
                CMD_CAN_MAPPINGS,
                CMD_TESTS,
                CMD_TEST,
                CMD_TOPOLOGY,
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
            "lifecycle",
            CMD_DIAGNOSE,
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
                return [PLACEHOLDER_GROUP]
            if len(tokens) == COUNT_TWO:
                return self._show_flag_suggestions(target)
            return []
        if target == CMD_DEVICE:
            if len(tokens) == COUNT_ONE:
                return [PLACEHOLDER_DEVICE]
            if len(tokens) == COUNT_TWO:
                return self._show_flag_suggestions(target)
            return []
        if target == SHOW_TARGET_DEVICE_GROUP:
            if len(tokens) == COUNT_ONE:
                return [PLACEHOLDER_DEVICE]
            if len(tokens) == COUNT_TWO:
                return self._show_flag_suggestions(target)
            return []
        if target == CMD_DEVICE_USAGE:
            if len(tokens) == COUNT_ONE:
                return [PLACEHOLDER_DEVICE]
            if len(tokens) == COUNT_TWO:
                return self._show_flag_suggestions(target)
            return []
        if target in (SHOW_TARGET_COMMANDS, SHOW_TARGET_HELP):
            if len(tokens) == COUNT_ONE:
                return self._show_flag_suggestions(target)
            return []
        if target == CMD_CONFIG:
            if len(tokens) == COUNT_ONE:
                return [CMD_LOCAL_RAW, CMD_DIRTY] + self._show_flag_suggestions(target)
            if len(tokens) == COUNT_TWO and tokens[COUNT_ONE].lower() in (CMD_LOCAL_RAW, CMD_DIRTY):
                return self._show_flag_suggestions(target)
            return self._show_flag_suggestions(target)
        if target == CMD_PROFILE:
            if len(tokens) == COUNT_ONE:
                return [PLACEHOLDER_PROFILE] + self._show_flag_suggestions(target)
            if len(tokens) == COUNT_TWO:
                return self._show_flag_suggestions(target)
            return []
        if target == PARSER_SPEC.show_target_test:
            if len(tokens) == COUNT_ONE:
                return [PLACEHOLDER_TEST]
            if len(tokens) == COUNT_TWO:
                return self._show_flag_suggestions(target)
            return []
        if target == SHOW_TARGET_TOPOLOGY:
            if len(tokens) == COUNT_ONE:
                return [CMD_NEIGHBORS, CMD_NODES, CMD_EDGES, CMD_NODE + PARSER_SPEC.space_str + PLACEHOLDER_DEVICE] + self._show_flag_suggestions(target)
            if len(tokens) == COUNT_TWO and tokens[COUNT_ONE].lower() in (CMD_NEIGHBORS, CMD_NODES, CMD_EDGES):
                return self._show_flag_suggestions(target)
            if len(tokens) == COUNT_TWO and tokens[COUNT_ONE].lower() == CMD_NODE:
                return [PLACEHOLDER_DEVICE]
            if len(tokens) == COUNT_THREE and tokens[COUNT_ONE].lower() == CMD_NODE:
                return self._show_flag_suggestions(target)
            return []
        if target == SHOW_TARGET_NEIGHBORS:
            if len(tokens) == COUNT_ONE:
                return [PLACEHOLDER_DEVICE]
            if len(tokens) == COUNT_TWO:
                return self._show_flag_suggestions(target)
            return []
        if target in PARSER_SPEC.show_targets:
            if len(tokens) == COUNT_ONE:
                return self._show_flag_suggestions(target)
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
            CMD_GROUP + PARSER_SPEC.space_str + PLACEHOLDER_GROUP,
            PARSER_SPEC.show_target_devices,
            CMD_DEVICE + PARSER_SPEC.space_str + PLACEHOLDER_DEVICE,
            PARSER_SPEC.show_target_commands,
            PARSER_SPEC.show_target_help,
            SHOW_TARGET_VERSION,
            SHOW_TARGET_SOURCES,
            CMD_DEVICE_USAGE + PARSER_SPEC.space_str + PLACEHOLDER_DEVICE,
            SHOW_TARGET_DEVICE_GROUP + PARSER_SPEC.space_str + PLACEHOLDER_DEVICE,
            PARSER_SPEC.show_target_bindings,
            SHOW_TARGET_CAN_MAPPINGS,
            PARSER_SPEC.show_target_selected_device,
            PARSER_SPEC.show_target_runtime_state,
            SHOW_TARGET_LIFECYCLE,
            CMD_CONFIG,
            CMD_CONFIG + PARSER_SPEC.space_str + CMD_LOCAL_RAW,
            CMD_CONFIG + PARSER_SPEC.space_str + CMD_DIRTY,
            CMD_PROFILES,
            CMD_PROFILE,
            CMD_PROFILE + PARSER_SPEC.space_str + PLACEHOLDER_PROFILE,
            PARSER_SPEC.show_target_tests,
            PARSER_SPEC.show_target_test + PARSER_SPEC.space_str + PLACEHOLDER_TEST,
            PARSER_SPEC.show_target_message_level,
            SHOW_TARGET_ACTIVE,
            SHOW_TARGET_INSTANTIATED,
            SHOW_TARGET_FAULTS,
            SHOW_TARGET_SIGNALS,
            SHOW_TARGET_SIGNAL + PARSER_SPEC.space_str + PLACEHOLDER_DEVICE,
            SHOW_TARGET_WORKSPACE,
            SHOW_TARGET_CONTROLLERS,
            SHOW_TARGET_TOPOLOGY,
            SHOW_TARGET_TOPOLOGY + PARSER_SPEC.space_str + CMD_NEIGHBORS,
            SHOW_TARGET_NEIGHBORS + PARSER_SPEC.space_str + PLACEHOLDER_DEVICE,
        ]

    def _show_flag_suggestions(self, target: Optional[str] = None) -> List[str]:
        """
        NAME
            _show_flag_suggestions - Suggest show flags.
        """
        flags = [FLAG_JSON, FLAG_PRETTY, SHOW_FLAG_ALL]
        if target in LOCAL_ONLY_SHOW_TARGETS:
            return flags
        return [
            PARSER_SPEC.show_source_robot,
            PARSER_SPEC.show_source_local,
            PARSER_SPEC.show_source_both,
            *flags,
        ]

    def _suggest_bindings_args(self, tokens: List[str]) -> List[str]:
        """
        NAME
            _suggest_bindings_args - Suggest bindings subcommands.
        """
        if not tokens:
            return [CMD_SHOW, CMD_CONTROLLER, CMD_BINDING, CMD_LOAD, CMD_SAVE, CMD_VALIDATE]
        sub = tokens[COUNT_ZERO].lower()
        if sub == CMD_SHOW and len(tokens) == COUNT_ONE:
            return [SHOW_FLAG_ALL, FLAG_JSON, FLAG_PRETTY, BINDINGS_SHOW_CONTROLLERS, BINDINGS_SHOW_BINDINGS]
        if sub == CMD_SHOW and len(tokens) == COUNT_TWO:
            target = tokens[COUNT_ONE].lower()
            if target in BINDINGS_SHOW_TARGETS:
                return [SHOW_FLAG_ALL, FLAG_JSON, FLAG_PRETTY]
            return [SHOW_FLAG_ALL, FLAG_JSON, FLAG_PRETTY, BINDINGS_SHOW_CONTROLLERS, BINDINGS_SHOW_BINDINGS]
        if sub == CMD_CONTROLLER and len(tokens) == COUNT_ONE:
            return [CMD_ADD, CMD_SET, CMD_RENAME, CMD_NO]
        if sub == CMD_BINDING and len(tokens) == COUNT_ONE:
            return [CMD_ADD, CMD_SET, CMD_DELETE]
        if sub in (CMD_LOAD, CMD_SAVE, CMD_VALIDATE) and len(tokens) == COUNT_ONE:
            return [PLACEHOLDER_PATH]
        return []

    def _suggest_group_bind_args(self, tokens: List[str]) -> List[str]:
        """
        NAME
            _suggest_group_bind_args - Suggest bind subcommands in group mode.
        """
        if not tokens:
            return [CMD_LIST, CMD_EXPLAIN, CMD_TEST, PLACEHOLDER_INPUT]
        action = tokens[COUNT_ZERO].lower()
        if action == CMD_LIST:
            return []
        if action in (CMD_EXPLAIN, CMD_TEST):
            if len(tokens) == COUNT_ONE:
                return self._group_binding_selector_suggestions()
            return []
        if len(tokens) == COUNT_ONE:
            return [PROFILE_EXPORT_CMD_BIND_ANALOG, PROFILE_EXPORT_CMD_BIND_HOLD, PROFILE_EXPORT_CMD_BIND_TOGGLE, PROFILE_EXPORT_CMD_BIND_JOG_FORWARD, PROFILE_EXPORT_CMD_BIND_JOG_REVERSE]
        return []

    def _group_binding_selector_suggestions(self) -> List[str]:
        """
        NAME
            _group_binding_selector_suggestions - Suggest current-group binding selectors.
        """
        if not self._modes or self._modes[-1].name != MODE_GROUP or not self._modes[-1].group:
            return [PLACEHOLDER_BINDING]
        diagnostics = self._evaluate_group_bindings(self._modes[-1].group)
        if not diagnostics:
            return [PLACEHOLDER_BINDING]
        suggestions: List[str] = []
        for diag in diagnostics:
            index = str(diag.get("index", EMPTY_STRING)).strip()
            input_name = str(diag.get(KEY_INPUT, EMPTY_STRING)).strip()
            if index:
                suggestions.append(index)
            if input_name:
                suggestions.append(input_name)
        seen: set[str] = set()
        unique: List[str] = []
        for suggestion in suggestions:
            lowered = suggestion.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            unique.append(suggestion)
        return unique or [PLACEHOLDER_BINDING]

    def _suggest_configure_args(self, tokens: List[str]) -> List[str]:
        """
        NAME
            _suggest_configure_args - Suggest configure subcommands.
        """
        if not tokens:
            return [CMD_TERMINAL]
        return []

    def _suggest_validate_args(self, tokens: List[str]) -> List[str]:
        """
        NAME
            _suggest_validate_args - Suggest validate subcommands.
        """
        if not tokens:
            return [
                CMD_ALL,
                CMD_CONFIG,
                CMD_PROFILES,
                CMD_TESTS,
                CMD_BINDINGS,
                CMD_CAN_MAPPINGS,
                CMD_TOPOLOGY,
            ]
        if len(tokens) == COUNT_ONE and tokens[COUNT_ZERO].lower() == CMD_CONFIG:
            return [PLACEHOLDER_PATH, CMD_VALIDATE_ALL, FLAG_VERBOSE]
        if len(tokens) == COUNT_TWO and tokens[COUNT_ZERO].lower() == CMD_CONFIG:
            return [CMD_VALIDATE_ALL, FLAG_VERBOSE]
        if len(tokens) == COUNT_ONE and tokens[COUNT_ZERO].lower() == CMD_PROFILES:
            return [CMD_ROBOT, CMD_LOCAL, CMD_ACTIVE, FLAG_VERBOSE]
        if len(tokens) == COUNT_ONE and tokens[COUNT_ZERO].lower() == CMD_TESTS:
            return [CMD_ACTIVE_SET, FLAG_VERBOSE]
        if len(tokens) == COUNT_ONE and tokens[COUNT_ZERO].lower() in (CMD_BINDINGS, CMD_CAN_MAPPINGS):
            return [PLACEHOLDER_PATH, FLAG_VERBOSE]
        if len(tokens) == COUNT_ONE and tokens[COUNT_ZERO].lower() in (CMD_ALL, CMD_FILE, CMD_TOPOLOGY, CMD_SCRIPT):
            return [FLAG_VERBOSE]
        return []

    def _suggest_save_args(self, tokens: List[str]) -> List[str]:
        """
        NAME
            _suggest_save_args - Suggest save targets.
        """
        if not tokens:
            return [
                CMD_ALL,
                CMD_CONFIG,
                CMD_SAVE_BRIDGE_CONFIG,
                CMD_SAVE_RUNTIME_GROUPS,
                CMD_PROFILES,
                CMD_SOURCES,
            ]
        if len(tokens) == COUNT_ONE and tokens[COUNT_ZERO].lower() == CMD_ALL:
            return [CMD_PROMPT]
        if len(tokens) == COUNT_ONE:
            if tokens[COUNT_ZERO].lower() == CMD_SOURCES:
                return []
            return [PLACEHOLDER_PATH]
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
            return [CMD_MANUFACTURER, CMD_DEVICE_TYPE_NAME, CMD_DEVICE_TYPES, FLAG_JSON]
        if sub in (CMD_LOAD, CMD_SAVE, CMD_VALIDATE) and len(tokens) == COUNT_ONE:
            return [PLACEHOLDER_PATH]
        return []

    def _suggest_tests_args(self, tokens: List[str]) -> List[str]:
        """
        NAME
            _suggest_tests_args - Suggest tests subcommands.
        """
        if not tokens:
            return [CMD_TEMPLATES, CMD_CLEAR]
        return []

    def _suggest_test_config_args(self, tokens: List[str]) -> List[str]:
        """
        NAME
            _suggest_test_config_args - Suggest config-mode test subcommands.
        """
        if not tokens:
            return [CMD_NEW, CMD_IMPORT, CMD_COPY, CMD_SET, CMD_CREATE, CMD_DELETE, CMD_CLEANUP, PLACEHOLDER_TEST]
        sub = tokens[COUNT_ZERO].lower()
        if sub in (CMD_SET, CMD_CREATE, CMD_DELETE, CMD_COPY) and len(tokens) == COUNT_ONE:
            return [PLACEHOLDER_TEST]
        if sub == CMD_CLEANUP and len(tokens) == COUNT_ONE:
            return [CMD_STALE]
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
            # Allow runtime test runner commands to flow through the AST executor.
            if len(tokens) >= COUNT_TWO:
                sub = tokens[COUNT_ONE].lower()
                if sub in (CMD_SELECT, CMD_TOGGLE, CMD_RUN, CMD_RUN_ALL, "activate", "deactivate"):
                    return False
            return True
        if tokens[0].lower() == CMD_SHOW and len(tokens) > 1:
            target = tokens[1].lower()
            if target not in (CMD_TEST, CMD_TESTS):
                return False
            explicit_robot_source = any(
                token.lower() in (SHOW_SOURCE_ROBOT, SHOW_SOURCE_BOTH, "--robot", "--both")
                for token in tokens[2:]
            )
            if explicit_robot_source:
                return False
            return True
        return False

    def _execute_test_authoring(self, tokens: List[str]) -> StatusResult:
        """
        NAME
            _execute_test_authoring - Dispatch test authoring commands.

        PARAMETERS
            tokens - Tokenized command input.

        RETURNS
            None on success, or a CLI exit code.
        """

        mode = self._modes[-1].name
        cmd = tokens[COUNT_ZERO].lower()
        if cmd == CMD_SHOW:
            return self._dsl_show_command(tokens)
        if cmd == CMD_TESTS:
            print(MESSAGE_ERROR_LEGACY_TEST_AUTHORING_REMOVED)
            return StatusResult(code=SS__CLI_PARSER__UNKNOWN_COMMAND)
        if cmd == CMD_TEST and mode == MODE_CONFIG:
            return self._dsl_test_command(tokens)
        print(MESSAGE_ERROR_DSL_CLI_USAGE)
        return StatusResult(code=SS__CLI_PARSER__UNKNOWN_COMMAND)

    def _dsl_require_local_root(self) -> Optional[Dict[str, object]]:
        self._ensure_local_config()
        if self._local_root_payload is None:
            print(MESSAGE_ERROR_DSL_CONFIG_REQUIRED)
            return None
        return self._local_root_payload

    def _dsl_active_profile(self) -> Optional[str]:
        profile_name = self._active_profile_name()
        if not profile_name:
            print(MESSAGE_ERROR_DSL_PROFILE_REQUIRED)
            return None
        return profile_name

    def _dsl_store(self) -> RobotTestDslStore:
        payload = self._local_root_payload if isinstance(self._local_root_payload, dict) else {}
        return robot_test_dsl_store_from_root_payload(payload)

    def _dsl_write_store(self, store: RobotTestDslStore) -> None:
        if self._local_root_payload is None:
            return
        robot_test_dsl_write_store_to_root_payload(self._local_root_payload, store)
        self._mark_tests_dirty()
        self._mark_profiles_dirty()

    def _dsl_signal_catalog(self) -> Dict[str, Dict[str, object]]:
        return robot_test_dsl_signal_catalog(ROBOT_TEST_DSL_SIGNALS_PATH)

    def _dsl_device_catalog(self, profile_name: str) -> Dict[str, Dict[str, object]]:
        payload = self._local_root_payload if isinstance(self._local_root_payload, dict) else {}
        return robot_test_dsl_device_catalog(payload, profile_name)

    def _dsl_validate_store(self, store: RobotTestDslStore, profile_name: str):
        payload = self._local_root_payload if isinstance(self._local_root_payload, dict) else {}
        return robot_test_dsl_validate_store_for_profile(payload, store, profile_name, ROBOT_TEST_DSL_SIGNALS_PATH)

    def _dsl_cleanup_stale_tests(self, store: RobotTestDslStore, profile_name: str) -> List[str]:
        """
        NAME
            _dsl_cleanup_stale_tests - Remove DSL tests that do not validate for the active profile.
        """
        payload = self._local_root_payload if isinstance(self._local_root_payload, dict) else {}
        return robot_test_dsl_cleanup_stale_tests_in_store(payload, store, profile_name, ROBOT_TEST_DSL_SIGNALS_PATH)

    @staticmethod
    def _dsl_issue_line_excerpt(entry: RobotTestDslEntry, field: str) -> Optional[str]:
        """
        NAME
            _dsl_issue_line_excerpt - Resolve a field or statement to a source line excerpt.
        """
        if not isinstance(field, str):
            return None
        field_text = field.strip()
        if not field_text or field_text in DSL_VALIDATION_META_FIELDS:
            return None
        for line_number, source_line in enumerate(entry.source.splitlines(), start=1):
            line_text = source_line.strip()
            if not line_text:
                continue
            if line_text == field_text or field_text in line_text:
                return MESSAGE_DSL_VALIDATION_LINE_FMT.format(line=line_number, text=line_text)
        return MESSAGE_DSL_VALIDATION_FIELD_FMT.format(field=field_text)

    def _dsl_issue_detail(
        self,
        issue,
        entries_override: Optional[Dict[str, RobotTestDslEntry]] = None,
    ) -> str:
        """
        NAME
            _dsl_issue_detail - Render a location detail suffix for one DSL validation issue.
        """
        store = self._dsl_store()
        return robot_test_dsl_issue_detail(issue, store, entries_override)

    def _dsl_print_validation(
        self,
        result,
        json_output: bool,
        pretty: bool,
        entries_override: Optional[Dict[str, RobotTestDslEntry]] = None,
    ) -> None:
        text = robot_test_dsl_render_validation_text(
            result,
            self._dsl_store(),
            json_output=json_output,
            pretty=pretty,
            entries_override=entries_override,
        )
        print(text)

    def _dsl_show_command(self, tokens: List[str]) -> StatusResult:
        root = self._dsl_require_local_root()
        if root is None:
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        source, cleaned, json_output, pretty, _grouped, ok = self._parse_show_flags(tokens[COUNT_ONE:])
        if not ok:
            return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
        explicit_source = any(
            tok.lower() in (SHOW_SOURCE_ROBOT, SHOW_SOURCE_LOCAL, SHOW_SOURCE_BOTH, "--robot", "--local", "--both")
            for tok in tokens[COUNT_ONE:]
        )
        if not explicit_source:
            source = SHOW_SOURCE_LOCAL
        if source in (SHOW_SOURCE_ROBOT, SHOW_SOURCE_BOTH):
            print(MESSAGE_ERROR_DSL_LOCAL_ONLY)
            return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
        if not cleaned:
            print(MESSAGE_ERROR_DSL_SHOW_USAGE)
            return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
        store = self._dsl_store()
        target = cleaned[COUNT_ZERO].lower()
        if target == CMD_TESTS:
            payload = {
                "defaultSet": store.default_set,
                "testSets": store.test_sets,
                "tests": sorted(store.tests_by_name.keys()),
            }
            if json_output:
                print(self._dump_json(payload, pretty))
            else:
                print("DSL tests:")
                for name in sorted(store.tests_by_name.keys()):
                    print(f"  {name}")
            return StatusResult(code=SS__NORMAL)
        if target != CMD_TEST:
            print(MESSAGE_ERROR_DSL_SHOW_USAGE)
            return StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX)
        if len(cleaned) >= COUNT_TWO and cleaned[COUNT_ONE].lower() == CMD_LIBRARY:
            external_global_names = robot_test_dsl_list_external_library_test_names()
            config_library_names = robot_test_dsl_resolve_global_library_test_names(root)
            profile_set_name = robot_test_dsl_resolve_profile_test_set_name(
                root,
                self._active_profile_name() or EMPTY_STRING,
            )
            payload = {
                "externalGlobalTests": external_global_names,
                "configLibrarySet": store.default_set,
                "configLibraryTests": config_library_names,
                "activeProfile": self._active_profile_name() or EMPTY_STRING,
                "profileSet": profile_set_name,
                "profileTests": robot_test_dsl_resolve_profile_test_names(
                    root,
                    self._active_profile_name() or EMPTY_STRING,
                ),
            }
            if json_output:
                print(self._dump_json(payload, pretty))
            else:
                print(MESSAGE_DSL_LIBRARY_GLOBAL_HEADER)
                if external_global_names:
                    for name in external_global_names:
                        print(f"  {name}")
                else:
                    print(f"  {MESSAGE_DSL_NONE}")
                print(
                    MESSAGE_DSL_LIBRARY_CONFIG_HEADER.format(
                        name=store.default_set or MESSAGE_DSL_NONE
                    )
                )
                if config_library_names:
                    for name in config_library_names:
                        print(f"  {name}")
                else:
                    print(f"  {MESSAGE_DSL_NONE}")
                print(
                    MESSAGE_DSL_PROFILE_SET_HEADER.format(
                        name=profile_set_name or MESSAGE_DSL_NONE
                    )
                )
                profile_names = robot_test_dsl_resolve_profile_test_names(
                    root,
                    self._active_profile_name() or EMPTY_STRING,
                )
                if profile_names:
                    for name in profile_names:
                        print(f"  {name}")
                else:
                    print(f"  {MESSAGE_DSL_NONE}")
            return StatusResult(code=SS__NORMAL)
        if len(cleaned) >= COUNT_TWO and cleaned[COUNT_ONE].lower() == "sets":
            payload = {
                "defaultSet": store.default_set,
                "testSets": store.test_sets,
                "activeProfile": self._active_profile_name() or EMPTY_STRING,
            }
            if json_output:
                print(self._dump_json(payload, pretty))
            else:
                print(f"default set: {store.default_set}")
                for set_name, names in store.test_sets.items():
                    print(f"  {set_name}: {', '.join(names) if names else '-'}")
            return StatusResult(code=SS__NORMAL)
        if len(cleaned) < COUNT_TWO:
            print(MESSAGE_ERROR_DSL_SHOW_USAGE)
            return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
        test_name = cleaned[COUNT_ONE]
        entry = store.tests_by_name.get(test_name)
        if entry is None:
            print(MESSAGE_ERROR_DSL_TEST_NOT_FOUND.format(name=test_name))
            return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
        wants_normalized = len(cleaned) >= 3 and cleaned[2].lower() == "normalized"
        if wants_normalized:
            payload = robot_test_dsl_store_to_payload(
                RobotTestDslStore(
                    tests_by_name={test_name: entry},
                    test_sets={},
                    default_set=store.default_set,
                )
            )[KEY_DSL_TESTS_BY_NAME][test_name]["normalized"]
            print(self._dump_json(payload, pretty if json_output else True))
            return StatusResult(code=SS__NORMAL)
        if json_output:
            print(self._dump_json({"name": test_name, "source": entry.source}, pretty))
        else:
            print(entry.source)
        return StatusResult(code=SS__NORMAL)

    def _dsl_test_command(self, tokens: List[str]) -> StatusResult:
        root = self._dsl_require_local_root()
        if root is None:
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        profile_name = self._dsl_active_profile()
        if profile_name is None:
            return StatusResult(code=SS__CONFIG__PROFILE_REQUIRED)
        if len(tokens) < COUNT_TWO:
            print(MESSAGE_ERROR_DSL_CLI_USAGE)
            return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
        store = self._dsl_store()
        sub = tokens[COUNT_ONE].lower()
        if sub == CMD_NEW:
            if len(tokens) < 3:
                print("ERROR: test new <name> [set <set_name>]")
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            test_name = tokens[2]
            set_name = None
            if len(tokens) >= 5:
                if tokens[3].lower() != CMD_SET:
                    print("ERROR: test new <name> [set <set_name>]")
                    return StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX)
                set_name = tokens[4]
            try:
                create_result = robot_test_dsl_create_blank_test_in_root_payload(
                    root,
                    profile_name,
                    test_name,
                    set_name=set_name,
                    signal_catalog_path=ROBOT_TEST_DSL_SIGNALS_PATH,
                )
            except Exception as exc:
                print(str(exc))
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            result = create_result.validation
            if not result.ok():
                self._dsl_print_validation(
                    result,
                    False,
                    False,
                    entries_override={test_name: create_result.entry},
                )
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            self._mark_tests_dirty()
            self._mark_profiles_dirty()
            print(MESSAGE_DSL_TEST_CREATED.format(name=test_name))
            return StatusResult(code=SS__NORMAL)
        if sub == CMD_IMPORT:
            if len(tokens) < 4:
                print("ERROR: test import <name> <path> [set <set_name>]")
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            test_name = tokens[2]
            source_path = Path(tokens[3])
            set_name = None
            if len(tokens) >= 6:
                if tokens[4].lower() != CMD_SET:
                    print("ERROR: test import <name> <path> [set <set_name>]")
                    return StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX)
                set_name = tokens[5]
            try:
                import_result = robot_test_dsl_import_test_into_root_payload(
                    root,
                    profile_name,
                    test_name,
                    source_path,
                    set_name=set_name,
                    signal_catalog_path=ROBOT_TEST_DSL_SIGNALS_PATH,
                )
            except Exception as exc:
                print(str(exc))
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            result = import_result.validation
            if not result.ok():
                self._dsl_print_validation(
                    result,
                    False,
                    False,
                    entries_override={test_name: import_result.entry},
                )
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            self._mark_tests_dirty()
            self._mark_profiles_dirty()
            print(MESSAGE_DSL_TEST_IMPORTED.format(name=test_name))
            return StatusResult(code=SS__NORMAL)
        if sub == "import-global":
            if len(tokens) < 4:
                print("ERROR: test import-global <name> <path>")
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            test_name = tokens[2]
            source_path = Path(tokens[3])
            try:
                robot_test_dsl_import_test_into_external_library(test_name, source_path)
            except Exception as exc:
                print(str(exc))
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            print(MESSAGE_DSL_TEST_IMPORTED_GLOBAL.format(name=test_name))
            return StatusResult(code=SS__NORMAL)
        if sub == "import-config":
            if len(tokens) < 4:
                print("ERROR: test import-config <name> <path>")
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            test_name = tokens[2]
            source_path = Path(tokens[3])
            try:
                import_result = robot_test_dsl_import_test_into_config_library(
                    root,
                    profile_name,
                    test_name,
                    source_path,
                    signal_catalog_path=ROBOT_TEST_DSL_SIGNALS_PATH,
                )
            except Exception as exc:
                print(str(exc))
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            self._mark_tests_dirty()
            self._mark_profiles_dirty()
            result = import_result.validation
            if not result.ok():
                self._dsl_print_validation(
                    result,
                    False,
                    False,
                    entries_override={test_name: import_result.entry},
                )
            print(MESSAGE_DSL_TEST_IMPORTED_CONFIG.format(name=test_name))
            return StatusResult(code=SS__NORMAL)
        if sub == CMD_COPY:
            if len(tokens) < 4:
                print("ERROR: test copy <source_test> <target_test> [set <set_name>]")
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            source_name = tokens[2]
            target_name = tokens[3]
            set_name = None
            if len(tokens) >= 6:
                if tokens[4].lower() != CMD_SET:
                    print("ERROR: test copy <source_test> <target_test> [set <set_name>]")
                    return StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX)
                set_name = tokens[5]
            try:
                copy_result = robot_test_dsl_copy_test_into_root_payload(
                    root,
                    profile_name,
                    source_name,
                    target_name,
                    set_name=set_name,
                    signal_catalog_path=ROBOT_TEST_DSL_SIGNALS_PATH,
                )
            except Exception as exc:
                print(str(exc))
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            result = copy_result.validation
            if not result.ok():
                self._dsl_print_validation(
                    result,
                    False,
                    False,
                    entries_override={target_name: copy_result.entry},
                )
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            self._mark_tests_dirty()
            self._mark_profiles_dirty()
            print(MESSAGE_DSL_TEST_COPIED.format(source=source_name, target=target_name))
            return StatusResult(code=SS__NORMAL)
        if sub == "copy-global":
            if len(tokens) < 5:
                print("ERROR: test copy-global <source_test> <target_test> <config|profile>")
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            source_name = tokens[2]
            target_name = tokens[3]
            destination = tokens[4].strip().lower()
            if destination not in ("config", "profile"):
                print("ERROR: test copy-global <source_test> <target_test> <config|profile>")
                return StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX)
            try:
                copy_result = robot_test_dsl_copy_external_library_test_into_root_payload(
                    root,
                    profile_name,
                    source_name,
                    target_name,
                    destination=destination,
                    signal_catalog_path=ROBOT_TEST_DSL_SIGNALS_PATH,
                )
            except Exception as exc:
                print(str(exc))
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            self._mark_tests_dirty()
            self._mark_profiles_dirty()
            result = copy_result.validation
            if not result.ok():
                self._dsl_print_validation(
                    result,
                    False,
                    False,
                    entries_override={target_name: copy_result.entry},
                )
            print(
                MESSAGE_DSL_TEST_COPIED_GLOBAL.format(
                    source=source_name,
                    target=target_name,
                    destination=destination,
                )
            )
            return StatusResult(code=SS__NORMAL)
        if sub == "rename-global":
            if len(tokens) < 4:
                print("ERROR: test rename-global <old_name> <new_name>")
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            old_name = tokens[2]
            new_name = tokens[3]
            try:
                robot_test_dsl_rename_external_library_test(old_name, new_name)
            except Exception as exc:
                print(str(exc))
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            print(MESSAGE_DSL_TEST_RENAMED_GLOBAL.format(source=old_name, target=new_name))
            return StatusResult(code=SS__NORMAL)
        if sub == "delete-global":
            if len(tokens) < 3:
                print("ERROR: test delete-global <name>")
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            test_name = tokens[2]
            try:
                archive_path = robot_test_dsl_delete_external_library_test(test_name)
            except Exception as exc:
                print(str(exc))
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            print(MESSAGE_DSL_TEST_DELETED_GLOBAL_ARCHIVED.format(name=test_name, path=archive_path))
            return StatusResult(code=SS__NORMAL)
        if sub == CMD_EXPORT:
            if len(tokens) < 4:
                print("ERROR: test export <name> <path>")
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            test_name = tokens[2]
            entry = store.tests_by_name.get(test_name)
            if entry is None:
                print(MESSAGE_ERROR_DSL_TEST_NOT_FOUND.format(name=test_name))
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            Path(tokens[3]).write_text(entry.source, encoding=ENCODING_UTF8)
            print(MESSAGE_DSL_TEST_EXPORTED.format(name=test_name))
            return StatusResult(code=SS__NORMAL)
        if sub == CMD_VALIDATE:
            source, cleaned, json_output, pretty, _grouped, ok = self._parse_show_flags(tokens[COUNT_TWO:])
            _ = source
            if not ok:
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            result = self._dsl_validate_store(store, profile_name)
            if cleaned:
                test_name = cleaned[COUNT_ZERO]
                from tools.common.robot_test_dsl import ValidationResult

                filtered = ValidationResult(
                    errors=[item for item in result.errors if item.test_name in (None, test_name)],
                    warnings=[item for item in result.warnings if item.test_name in (None, test_name)],
                )
                result = filtered
            self._dsl_print_validation(result, json_output, pretty)
            return StatusResult(code=SS__NORMAL if result.ok() else SS__CLI_VALIDATOR__INVALID_VALUE)
        if sub == CMD_DELETE:
            if len(tokens) < 3:
                print("ERROR: test delete <name>")
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            test_name = tokens[2]
            if test_name not in store.tests_by_name:
                print(MESSAGE_ERROR_DSL_TEST_NOT_FOUND.format(name=test_name))
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            archive_path = robot_test_dsl_delete_test_from_root_payload(root, test_name)
            self._mark_tests_dirty()
            self._mark_profiles_dirty()
            print(MESSAGE_DSL_TEST_DELETED_ARCHIVED.format(name=test_name, path=archive_path))
            return StatusResult(code=SS__NORMAL)
        if sub == "rename":
            if len(tokens) < 4:
                print("ERROR: test rename <old_name> <new_name>")
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            old_name = tokens[2]
            new_name = tokens[3]
            if old_name not in store.tests_by_name:
                print(MESSAGE_ERROR_DSL_TEST_NOT_FOUND.format(name=old_name))
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            robot_test_dsl_rename_test_in_root_payload(root, old_name, new_name)
            self._mark_tests_dirty()
            self._mark_profiles_dirty()
            print(MESSAGE_DSL_TEST_RENAMED.format(source=old_name, target=new_name))
            return StatusResult(code=SS__NORMAL)
        if sub == CMD_SET:
            if len(tokens) < 4:
                print("ERROR: test set create|delete|add|remove|default ...")
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            action = tokens[2].lower()
            set_name = tokens[3]
            if action == CMD_CREATE:
                store.test_sets.setdefault(set_name, [])
                if not store.default_set:
                    store.default_set = set_name
                self._dsl_write_store(store)
                print(MESSAGE_DSL_SET_CREATED.format(name=set_name))
                return StatusResult(code=SS__NORMAL)
            if action == CMD_DELETE:
                if set_name not in store.test_sets:
                    print(MESSAGE_ERROR_DSL_SET_NOT_FOUND.format(name=set_name))
                    return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
                del store.test_sets[set_name]
                if store.default_set == set_name:
                    store.default_set = next(iter(store.test_sets.keys()), EMPTY_STRING)
                self._dsl_write_store(store)
                print(MESSAGE_DSL_SET_DELETED.format(name=set_name))
                return StatusResult(code=SS__NORMAL)
            if action == CMD_DEFAULT:
                if set_name not in store.test_sets:
                    print(MESSAGE_ERROR_DSL_SET_NOT_FOUND.format(name=set_name))
                    return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
                store.default_set = set_name
                self._dsl_write_store(store)
                print(MESSAGE_DSL_SET_DEFAULT.format(name=set_name))
                return StatusResult(code=SS__NORMAL)
            if action in (CMD_ADD, CMD_REMOVE):
                if len(tokens) < 5:
                    print(f"ERROR: test set {action} <set_name> <test_name>")
                    return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
                test_name = tokens[4]
                if set_name not in store.test_sets:
                    print(MESSAGE_ERROR_DSL_SET_NOT_FOUND.format(name=set_name))
                    return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
                if test_name not in store.tests_by_name:
                    print(MESSAGE_ERROR_DSL_TEST_NOT_FOUND.format(name=test_name))
                    return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
                names = list(store.test_sets.get(set_name, []))
                if action == CMD_ADD and test_name not in names:
                    names.append(test_name)
                    print(MESSAGE_DSL_SET_MEMBER_ADDED.format(test=test_name, name=set_name))
                if action == CMD_REMOVE and test_name in names:
                    names.remove(test_name)
                    print(MESSAGE_DSL_SET_MEMBER_REMOVED.format(test=test_name, name=set_name))
                store.test_sets[set_name] = names
                self._dsl_write_store(store)
                return StatusResult(code=SS__NORMAL)
            print("ERROR: test set create|delete|add|remove|default ...")
            return StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX)
        if sub == CMD_CLEANUP:
            if len(tokens) < 3 or tokens[2].lower() != CMD_STALE:
                print(f"ERROR: {CMD_TEST} {CMD_CLEANUP} {CMD_STALE}")
                return StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX)
            removed = self._dsl_cleanup_stale_tests(store, profile_name)
            self._dsl_write_store(store)
            if removed:
                print(MESSAGE_DSL_TESTS_CLEANED.format(names=SEP_COMMA_SPACE.join(removed)))
            else:
                print(MESSAGE_DSL_TESTS_CLEAN_NONE)
            return StatusResult(code=SS__NORMAL)
        print(MESSAGE_ERROR_DSL_CLI_USAGE)
        return StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX)

    def _ensure_tests_loaded(self) -> None:
        """
        NAME
            _ensure_tests_loaded - Load tests JSON into the authoring model.

        DESCRIPTION
            Loads tests from bridgeConfig.byProfile for the active profile.
        """

        profile_name = self._tests_profile or self._active_profile_name() or get_default_profile()
        if self._tests_model is not None and profile_name == self._tests_profile:
            return
        self._ensure_local_config()
        self._tests_profile = profile_name
        entry = self._local_profile_entry(profile_name, create=True)
        payload = entry.get(KEY_BRIDGE_TESTS)
        if not isinstance(payload, dict):
            payload = {}
        self._tests_model = model_from_payload(payload or {})
        self._sync_store_tests()
        self._refresh_tests_profile(profile_name)
        default_set = self._tests_model.default_test_set if self._tests_model else EMPTY_STRING
        self._tests_active_set = default_set or DEFAULT_TEST_SET

    def _tests_command(self, tokens: List[str]) -> StatusResult:
        """
        NAME
            _tests_command - Handle tests subcommands (templates/clear).
        """

        self._ensure_tests_loaded()
        if len(tokens) < COUNT_TWO:
            print(MESSAGE_ERR_TESTS_SUBCOMMAND)
            return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
        sub = tokens[COUNT_ONE].lower()
        if sub == CMD_TEMPLATES:
            return self._show_test_templates()
        if sub == CMD_CLEAR:
            model = TestAuthoringModel()
            model.test_sets[DEFAULT_TEST_SET] = TestSetModel(name=DEFAULT_TEST_SET, tests=[])
            self._tests_model = model
            self._tests_active_set = DEFAULT_TEST_SET
            self._mark_tests_dirty()
            self._sync_store_tests()
            if not self._tests_profile:
                self._refresh_tests_profile(self._active_profile_name() or get_default_profile())
            else:
                self._refresh_tests_profile(self._tests_profile)
            print(MESSAGE_TESTS_CLEARED)
            return StatusResult(code=SS__NORMAL)
        print(MESSAGE_ERR_TESTS_SUBCOMMAND)
        return StatusResult(code=SS__CLI_PARSER__UNKNOWN_COMMAND)

    def _show_test_templates(self) -> StatusResult:
        """
        NAME
            _show_test_templates - List available test templates.
        """

        templates = self._list_test_templates()
        print(MESSAGE_TESTS_TEMPLATES_HEADER)
        if not templates:
            print(MESSAGE_TESTS_TEMPLATES_NONE)
            return StatusResult(code=SS__NORMAL)
        for name in templates:
            print(MESSAGE_TESTS_TEMPLATE_ENTRY.format(name=name))
        return StatusResult(code=SS__NORMAL)

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

    def _load_tests_from_path(self, path: Path) -> StatusResult:
        """
        NAME
            _load_tests_from_path - Load tests JSON from a path.
        """
        print(MESSAGE_ERR_TESTS_STANDALONE)
        return StatusResult(code=SS__CONFIG__INVALID)

    def _merge_tests_from_path(self, path: Path) -> StatusResult:
        """
        NAME
            _merge_tests_from_path - Merge tests JSON into current model.
        """
        print(MESSAGE_ERR_TESTS_STANDALONE)
        return StatusResult(code=SS__CONFIG__INVALID)

    def _ensure_bindings_loaded(self) -> bool:
        """
        NAME
            _ensure_bindings_loaded - Load bringup_bindings.json if needed.
        """

        if isinstance(self._bindings_payload, dict):
            return True
        path = bindings_deploy_path()
        return self._load_bindings_from_path(path, announce=False).ok()

    def _load_bindings_from_path(self, path: Path, announce: bool = True) -> StatusResult:
        """
        NAME
            _load_bindings_from_path - Load bindings config from a path.
        """

        payload: object = BINDINGS_EMPTY_PAYLOAD
        read_failed = False
        if path.exists():
            try:
                payload = read_json(path)
            except Exception:
                read_failed = True
                self._warn(MESSAGE_ERR_BINDINGS_LOAD.format(path=path), essential=True)
        sanitized, warnings, changed = self._store.sanitize_bindings_payload(payload)
        self._bindings_payload = sanitized
        self._bindings_path = path
        self._bindings_dirty = bool(changed)
        self._recovery_mode = bool(self._recovery_mode or read_failed or changed)
        for warning in warnings:
            self._warnings.append(warning)
            self._warn(f"WARNING: {warning}", essential=True)
        self._sync_store_bindings()
        if announce:
            print(MESSAGE_INFO_BINDINGS_LOADED.format(path=path))
        return StatusResult(
            code=SS__CONFIG__IMPORTED if not changed and not read_failed else SS__CONFIG__INVALID
        )

    def _save_bindings_to_path(self, path: Path, *, validation_ok: bool = True) -> StatusResult:
        """
        NAME
            _save_bindings_to_path - Save bindings config to a path.
        """

        if not isinstance(self._bindings_payload, dict):
            print(MESSAGE_ERR_BINDINGS_LOAD.format(path=path))
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        payload = {
            KEY_SCHEMA_VERSION: PROFILE_SCHEMA_VERSION,
            KEY_CONTROLLERS: self._bindings_payload.get(KEY_CONTROLLERS, []),
            KEY_BINDINGS: self._bindings_payload.get(KEY_BINDINGS, []),
            KEY_INPUT_ALIASES: self._bindings_payload.get(KEY_INPUT_ALIASES, {}),
        }
        ok, error = self._atomic_write_json(
            path,
            payload,
            JSON_PRETTY_INDENT,
            True,
        )
        if not ok:
            print(MESSAGE_ERR_BINDINGS_WRITE.format(path=path, error=error))
            return StatusResult(code=SS__CONFIG__INVALID)
        mirror_path = self._mirror_repo_save_target(
            path,
            bindings_canonical_path(),
            bindings_deploy_path(),
        )
        if mirror_path is not None:
            ok, error = self._atomic_write_json(
                mirror_path,
                payload,
                JSON_PRETTY_INDENT,
                True,
            )
            if not ok:
                print(MESSAGE_ERR_BINDINGS_WRITE.format(path=mirror_path, error=error))
                return StatusResult(code=SS__CONFIG__INVALID)
        self._bindings_dirty = False
        self._bindings_path = path
        self._sync_store_bindings()
        self._post_save(
            AUDIT_ACTION_SAVE,
            [SOURCE_NAME_BINDINGS],
            path,
            payload,
            validation_ok,
            JSON_PRETTY_INDENT,
            True,
        )
        self._record_last_save(path)
        print(MESSAGE_INFO_BINDINGS_SAVED.format(path=path))
        if mirror_path is not None:
            print(MESSAGE_INFO_BINDINGS_MIRRORED.format(path=mirror_path))
        return StatusResult(code=SS__CONFIG__SAVED)

    def _bindings_show(self, tokens: List[str]) -> StatusResult:
        """
        NAME
            _bindings_show - Show bindings config content.
        """

        if not isinstance(self._bindings_payload, dict):
            print(MESSAGE_ERR_BINDINGS_LOAD.format(path=EMPTY_STRING))
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        if any(token.lower() in SHOW_SOURCE_FLAGS for token in tokens):
            print(MESSAGE_ERR_BINDINGS_SHOW_LOCAL_ONLY)
            return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
        tokens = [token for token in tokens if token.lower() != SHOW_FLAG_ALL]
        _source, cleaned, json_output, pretty, _grouped, ok = self._parse_show_flags(tokens)
        if not ok:
            return StatusResult(code=SS__CLI_PARSER__INVALID_FLAG)
        target = cleaned[COUNT_ZERO].lower() if cleaned else EMPTY_STRING
        controllers = self._bindings_payload.get(KEY_CONTROLLERS, [])
        bindings = self._bindings_payload.get(KEY_BINDINGS, [])
        print(MESSAGE_SOURCE_LOCAL)
        if json_output:
            if target == BINDINGS_SHOW_CONTROLLERS:
                print(self._dump_json({KEY_CONTROLLERS: controllers}, pretty))
                return StatusResult(code=SS__NORMAL)
            if target == BINDINGS_SHOW_BINDINGS:
                print(self._dump_json({KEY_BINDINGS: bindings}, pretty))
                return StatusResult(code=SS__NORMAL)
            print(self._dump_json(self._bindings_payload, pretty))
            return StatusResult(code=SS__NORMAL)
        if target and target not in BINDINGS_SHOW_TARGETS:
            print(MESSAGE_ERR_BINDINGS_SHOW)
            return StatusResult(code=SS__CLI_PARSER__UNKNOWN_COMMAND)
        print(MESSAGE_BINDINGS_HEADER)
        if target in (EMPTY_STRING, BINDINGS_SHOW_CONTROLLERS):
            print(MESSAGE_BINDINGS_CONTROLLERS_HEADER)
            self._print_bindings_controllers(controllers)
            if target == BINDINGS_SHOW_CONTROLLERS:
                return StatusResult(code=SS__NORMAL)
        if target in (EMPTY_STRING, BINDINGS_SHOW_BINDINGS):
            print(MESSAGE_BINDINGS_BINDINGS_HEADER)
            self._print_bindings_entries(bindings)
        if target == BINDINGS_SHOW_BINDINGS:
            return StatusResult(code=SS__NORMAL)
        return StatusResult(code=SS__NORMAL)

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
            line = MESSAGE_BINDINGS_BINDING_FMT.format(
                index=idx,
                command=entry.get(KEY_COMMAND),
                controller=entry.get(KEY_CONTROLLER),
                input=entry.get(KEY_INPUT),
                id=entry.get(KEY_ID),
                mode=entry.get(KEY_MODE),
            )
            if self._binding_entry_is_axis(entry):
                line += f" invert={entry.get(KEY_INVERT)} deadband={entry.get(KEY_DEADBAND)}"
            print(line)

    def _bindings_controller_command(self, tokens: List[str]) -> StatusResult:
        """
        NAME
            _bindings_controller_command - Edit controller entries.
        """

        if not tokens:
            print(MESSAGE_ERR_BINDINGS_CONTROLLER_SET)
            return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
        action = tokens[COUNT_ZERO].lower()
        controllers = self._bindings_payload.get(KEY_CONTROLLERS, []) if self._bindings_payload else []
        if action == CMD_ADD:
            if len(tokens) < COUNT_FOUR:
                print(MESSAGE_ERR_BINDINGS_CONTROLLER_ADD)
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            name = tokens[COUNT_ONE].strip()
            ctrl_type = tokens[COUNT_TWO].strip()
            try:
                port = int(tokens[COUNT_THREE])
            except ValueError:
                print(MESSAGE_ERR_BINDINGS_CONTROLLER_PORT)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            if self._bindings_find_controller(name, controllers):
                print(MESSAGE_ERR_BINDINGS_CONTROLLER_EXISTS)
                return StatusResult(code=SS__INPUT_BINDING__INVALID)
            controllers.append({KEY_NAME: name, FIELD_TYPE: ctrl_type, KEY_PORT: port})
            self._bindings_payload[KEY_CONTROLLERS] = controllers
            self._mark_bindings_dirty()
            return StatusResult(code=SS__NORMAL)
        if action == CMD_SET:
            if len(tokens) < COUNT_FOUR:
                print(MESSAGE_ERR_BINDINGS_CONTROLLER_SET)
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            name = tokens[COUNT_ONE].strip()
            field = tokens[COUNT_TWO].strip()
            value = " ".join(tokens[COUNT_THREE:]).strip()
            entry = self._bindings_find_controller(name, controllers)
            if not entry:
                print(MESSAGE_ERR_BINDINGS_CONTROLLER_NOT_FOUND)
                return StatusResult(code=SS__INPUT_BINDING__NOT_FOUND)
            if field == KEY_NAME:
                return self._bindings_rename_controller(name, value)
            if field == FIELD_TYPE:
                entry[FIELD_TYPE] = value
            elif field == KEY_PORT:
                try:
                    entry[KEY_PORT] = int(value)
                except ValueError:
                    print(MESSAGE_ERR_BINDINGS_CONTROLLER_PORT)
                    return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            else:
                print(MESSAGE_ERR_BINDINGS_FIELD_UNKNOWN)
                return StatusResult(code=SS__INPUT_BINDING__INVALID)
            self._mark_bindings_dirty()
            return StatusResult(code=SS__NORMAL)
        if action == CMD_RENAME:
            if len(tokens) < COUNT_THREE:
                print(MESSAGE_ERR_BINDINGS_CONTROLLER_RENAME)
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            return self._bindings_rename_controller(tokens[COUNT_ONE], tokens[COUNT_TWO])
        if action == CMD_NO:
            if len(tokens) < COUNT_TWO:
                print(MESSAGE_ERR_BINDINGS_CONTROLLER_DELETE)
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            return self._bindings_delete_controller(tokens[COUNT_ONE])
        print(MESSAGE_ERR_BINDINGS_SUBCOMMAND)
        return StatusResult(code=SS__CLI_PARSER__UNKNOWN_COMMAND)

    def _bindings_delete_controller(self, name: str) -> StatusResult:
        """
        NAME
            _bindings_delete_controller - Remove a controller by name.
        """

        controllers = self._bindings_payload.get(KEY_CONTROLLERS, []) if self._bindings_payload else []
        entry = self._bindings_find_controller(name, controllers)
        if not entry:
            print(MESSAGE_ERR_BINDINGS_CONTROLLER_NOT_FOUND)
            return StatusResult(code=SS__INPUT_BINDING__NOT_FOUND)
        if self._bindings_controller_in_use(name):
            print(MESSAGE_ERR_BINDINGS_CONTROLLER_IN_USE)
            return StatusResult(code=SS__INPUT_BINDING__INVALID)
        controllers.remove(entry)
        self._bindings_payload[KEY_CONTROLLERS] = controllers
        self._mark_bindings_dirty()
        return StatusResult(code=SS__NORMAL)

    def _bindings_binding_command(self, tokens: List[str]) -> StatusResult:
        """
        NAME
            _bindings_binding_command - Edit unified binding entries.
        """

        if not tokens:
            print(MESSAGE_ERR_BINDINGS_BINDING_SET)
            return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
        action = tokens[COUNT_ZERO].lower()
        bindings = self._bindings_payload.get(KEY_BINDINGS, []) if self._bindings_payload else []
        if action == CMD_ADD:
            if len(tokens) < COUNT_SIX:
                print(MESSAGE_ERR_BINDINGS_BINDING_ADD)
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            input_kind = tokens[COUNT_THREE]
            if input_kind not in BINDINGS_INPUT_KINDS:
                print(MESSAGE_ERR_BINDINGS_INPUT_KIND)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            entry = {
                KEY_COMMAND: tokens[COUNT_ONE],
                KEY_CONTROLLER: tokens[COUNT_TWO],
                KEY_INPUT: input_kind,
                KEY_ID: tokens[COUNT_FOUR],
                KEY_MODE: tokens[COUNT_FIVE],
            }
            if not self._bindings_controller_exists(entry[KEY_CONTROLLER]):
                print(MESSAGE_ERR_BINDINGS_CONTROLLER_REQUIRED.format(name=entry[KEY_CONTROLLER]))
                return StatusResult(code=SS__INPUT_BINDING__NOT_FOUND)
            if self._binding_entry_is_axis(entry):
                if len(tokens) != COUNT_TEN:
                    print(MESSAGE_ERR_BINDINGS_AXIS_FIELDS)
                    return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
                if str(entry[KEY_MODE]).strip() != BINDINGS_AXIS_MODE:
                    print(MESSAGE_ERR_BINDINGS_AXIS_MODE)
                    return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
                if tokens[COUNT_SIX].lower() != KEY_INVERT or tokens[COUNT_EIGHT].lower() != KEY_DEADBAND:
                    print(MESSAGE_ERR_BINDINGS_AXIS_FIELDS)
                    return StatusResult(code=SS__CLI_PARSER__INVALID_FLAG)
                invert = self._parse_bool(tokens[COUNT_SEVEN])
                if invert is None:
                    print(MESSAGE_ERR_BINDINGS_INVERT)
                    return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
                try:
                    deadband = float(tokens[COUNT_NINE])
                except ValueError:
                    print(MESSAGE_ERR_BINDINGS_DEADBAND)
                    return StatusResult(code=SS__CLI_VALIDATOR__OUT_OF_RANGE)
                if deadband < DEADBAND_MIN or deadband > DEADBAND_MAX:
                    print(MESSAGE_ERR_BINDINGS_DEADBAND)
                    return StatusResult(code=SS__CLI_VALIDATOR__OUT_OF_RANGE)
                entry[KEY_INVERT] = invert
                entry[KEY_DEADBAND] = deadband
            elif len(tokens) != COUNT_SIX:
                print(MESSAGE_ERR_BINDINGS_NON_AXIS_EXTRA)
                return StatusResult(code=SS__CLI_PARSER__INVALID_FLAG)
            bindings.append(entry)
            self._bindings_payload[KEY_BINDINGS] = bindings
            self._mark_bindings_dirty()
            return StatusResult(code=SS__NORMAL)
        if action == CMD_SET:
            if len(tokens) < COUNT_FOUR:
                print(MESSAGE_ERR_BINDINGS_BINDING_SET)
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            index = self._parse_index(tokens[COUNT_ONE], MESSAGE_ERR_BINDINGS_BINDING_INDEX)
            if index is None:
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            entry = self._bindings_entry_at(bindings, index)
            if entry is None:
                print(MESSAGE_ERR_BINDINGS_BINDING_INDEX)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            field = tokens[COUNT_TWO]
            value = " ".join(tokens[COUNT_THREE:]).strip()
            if field not in BINDINGS_BINDING_FIELDS:
                print(MESSAGE_ERR_BINDINGS_FIELD_UNKNOWN)
                return StatusResult(code=SS__INPUT_BINDING__INVALID)
            if field == KEY_CONTROLLER and not self._bindings_controller_exists(value):
                print(MESSAGE_ERR_BINDINGS_CONTROLLER_REQUIRED.format(name=value))
                return StatusResult(code=SS__INPUT_BINDING__NOT_FOUND)
            if field == KEY_INPUT:
                if value not in BINDINGS_INPUT_KINDS:
                    print(MESSAGE_ERR_BINDINGS_INPUT_KIND)
                    return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
                entry[field] = value
            elif field == KEY_MODE:
                if self._binding_entry_is_axis(entry) and value != BINDINGS_AXIS_MODE:
                    print(MESSAGE_ERR_BINDINGS_AXIS_MODE)
                    return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
                entry[field] = value
            elif field == KEY_INVERT:
                if not self._binding_entry_is_axis(entry):
                    print(MESSAGE_ERR_BINDINGS_NON_AXIS_EXTRA)
                    return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
                parsed = self._parse_bool(value)
                if parsed is None:
                    print(MESSAGE_ERR_BINDINGS_INVERT)
                    return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
                entry[field] = parsed
            elif field == KEY_DEADBAND:
                if not self._binding_entry_is_axis(entry):
                    print(MESSAGE_ERR_BINDINGS_NON_AXIS_EXTRA)
                    return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
                try:
                    deadband = float(value)
                except ValueError:
                    print(MESSAGE_ERR_BINDINGS_DEADBAND)
                    return StatusResult(code=SS__CLI_VALIDATOR__OUT_OF_RANGE)
                if deadband < DEADBAND_MIN or deadband > DEADBAND_MAX:
                    print(MESSAGE_ERR_BINDINGS_DEADBAND)
                    return StatusResult(code=SS__CLI_VALIDATOR__OUT_OF_RANGE)
                entry[field] = deadband
            else:
                entry[field] = value
            self._mark_bindings_dirty()
            return StatusResult(code=SS__NORMAL)
        if action == CMD_DELETE:
            if len(tokens) < COUNT_TWO:
                print(MESSAGE_ERR_BINDINGS_BINDING_DELETE)
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            index = self._parse_index(tokens[COUNT_ONE], MESSAGE_ERR_BINDINGS_BINDING_INDEX)
            if index is None:
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            entry = self._bindings_entry_at(bindings, index)
            if entry is None:
                print(MESSAGE_ERR_BINDINGS_BINDING_INDEX)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            bindings.remove(entry)
            self._mark_bindings_dirty()
            return StatusResult(code=SS__NORMAL)
        print(MESSAGE_ERR_BINDINGS_SUBCOMMAND)
        return StatusResult(code=SS__CLI_PARSER__UNKNOWN_COMMAND)

    def _bindings_validate(self, path: Optional[Path]) -> StatusResult:
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
                return StatusResult(code=SS__CONFIG__INVALID)
            if not isinstance(loaded, dict):
                print(MESSAGE_ERR_BINDINGS_VALIDATE.format(message=EMPTY_STRING))
                return StatusResult(code=SS__CONFIG__INVALID)
            payload = loaded
        self._store.set_bindings_payload(payload or {})
        result = self._store.validate_bindings_only(strict=True)
        errors = [issue for issue in result.errors() if issue.location == LOCATION_BINDINGS]
        if errors:
            message = self._format_store_errors(errors)
            print(MESSAGE_ERR_BINDINGS_VALIDATE.format(message=message))
            return StatusResult(code=SS__CONFIG__INVALID)
        print(AST_EXEC_SPEC["msg_ok_config"])
        return StatusResult(code=SS__CONFIG__VALID)

    def _validate_bindings_payload(self, payload: Dict[str, object]) -> List[str]:
        """
        NAME
            _validate_bindings_payload - Return validation errors for bindings.
        """

        errors: List[str] = []
        controllers = payload.get(KEY_CONTROLLERS, [])
        bindings = payload.get(KEY_BINDINGS, [])
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
                entry_errors = self._validate_binding_entry(entry, controller_names)
                errors.extend(entry_errors)
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
        return False

    def _bindings_rename_controller(self, old: str, new: str) -> StatusResult:
        """
        NAME
            _bindings_rename_controller - Rename a controller and update references.
        """

        if old == new:
            return StatusResult(code=SS__INPUT_BINDING__INVALID)
        controllers = self._bindings_payload.get(KEY_CONTROLLERS, []) if self._bindings_payload else []
        entry = self._bindings_find_controller(old, controllers)
        if not entry:
            print(MESSAGE_ERR_BINDINGS_CONTROLLER_NOT_FOUND)
            return StatusResult(code=SS__INPUT_BINDING__NOT_FOUND)
        if self._bindings_find_controller(new, controllers):
            print(MESSAGE_ERR_BINDINGS_CONTROLLER_EXISTS)
            return StatusResult(code=SS__INPUT_BINDING__INVALID)
        entry[KEY_NAME] = new
        for binding in self._bindings_payload.get(KEY_BINDINGS, []):
            if isinstance(binding, dict) and binding.get(KEY_CONTROLLER) == old:
                binding[KEY_CONTROLLER] = new
        self._mark_bindings_dirty()
        return StatusResult(code=SS__NORMAL)

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

    def _binding_entry_is_axis(self, entry: Dict[str, object]) -> bool:
        """
        NAME
            _binding_entry_is_axis - Return True when a binding entry is an axis row.
        """

        return str(entry.get(KEY_INPUT, EMPTY_STRING)).strip() == "axis"

    def _validate_binding_entry(
        self,
        entry: Dict[str, object],
        controller_names: set[str],
    ) -> List[str]:
        """
        NAME
            _validate_binding_entry - Validate one unified binding entry.
        """

        errors: List[str] = []
        command = str(entry.get(KEY_COMMAND, EMPTY_STRING)).strip()
        controller = str(entry.get(KEY_CONTROLLER, EMPTY_STRING)).strip()
        input_kind = str(entry.get(KEY_INPUT, EMPTY_STRING)).strip()
        input_id = str(entry.get(KEY_ID, EMPTY_STRING)).strip()
        mode = str(entry.get(KEY_MODE, EMPTY_STRING)).strip()
        if not command or not controller or not input_kind or not input_id or not mode:
            return [MESSAGE_ERR_BINDINGS_BINDING_SET]
        if controller not in controller_names:
            errors.append(MESSAGE_ERR_BINDINGS_CONTROLLER_REQUIRED.format(name=controller))
        if input_kind not in BINDINGS_INPUT_KINDS:
            errors.append(MESSAGE_ERR_BINDINGS_INPUT_KIND)
            return errors
        if self._binding_entry_is_axis(entry):
            if mode != BINDINGS_AXIS_MODE:
                errors.append(MESSAGE_ERR_BINDINGS_AXIS_MODE)
            invert = entry.get(KEY_INVERT)
            if not isinstance(invert, bool):
                errors.append(MESSAGE_ERR_BINDINGS_INVERT)
            deadband = entry.get(KEY_DEADBAND)
            if not isinstance(deadband, (int, float)) or deadband < DEADBAND_MIN or deadband > DEADBAND_MAX:
                errors.append(MESSAGE_ERR_BINDINGS_DEADBAND)
        else:
            if KEY_INVERT in entry or KEY_DEADBAND in entry:
                errors.append(MESSAGE_ERR_BINDINGS_NON_AXIS_EXTRA)
        return errors

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

    def _load_can_mappings_from_path(self, path: Path) -> StatusResult:
        """
        NAME
            _load_can_mappings_from_path - Load CAN mappings from a path.
        """

        payload: object = dict()
        read_failed = False
        if path.exists():
            try:
                payload = read_json(path)
            except Exception:
                read_failed = True
                self._warn(MESSAGE_ERR_MAPPINGS_LOAD.format(path=path), essential=True)
        sanitized, warnings, changed = self._store.sanitize_mappings_payload(payload)
        self._can_mappings = sanitized
        self._can_mappings_path = path
        self._can_mappings_dirty = bool(changed)
        self._recovery_mode = bool(self._recovery_mode or read_failed or changed)
        for warning in warnings:
            self._warnings.append(warning)
            self._warn(f"WARNING: {warning}", essential=True)
        self._sync_store_mappings()
        print(MESSAGE_INFO_MAPPINGS_LOADED.format(path=path))
        return StatusResult(
            code=SS__CONFIG__IMPORTED if not changed and not read_failed else SS__CONFIG__INVALID
        )

    def _save_can_mappings_to_path(self, path: Path, *, validation_ok: bool = True) -> StatusResult:
        """
        NAME
            _save_can_mappings_to_path - Save CAN mappings to a path.
        """

        if not isinstance(self._can_mappings, dict):
            print(MESSAGE_ERR_MAPPINGS_LOAD.format(path=path))
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        payload = {
            KEY_MANUFACTURERS: self._can_mappings.get(KEY_MANUFACTURERS, {}),
            KEY_DEVICE_TYPES: self._can_mappings.get(KEY_DEVICE_TYPES, {}),
        }
        ok, error = self._atomic_write_json(
            path,
            payload,
            JSON_PRETTY_INDENT,
            True,
        )
        if not ok:
            print(MESSAGE_ERR_MAPPINGS_WRITE.format(path=path, error=error))
            return StatusResult(code=SS__CONFIG__INVALID)
        self._can_mappings_dirty = False
        self._can_mappings_path = path
        self._sync_store_mappings()
        self._post_save(
            AUDIT_ACTION_SAVE,
            [SOURCE_NAME_CAN_MAPPINGS],
            path,
            payload,
            validation_ok,
            JSON_PRETTY_INDENT,
            True,
        )
        self._record_last_save(path)
        print(MESSAGE_INFO_MAPPINGS_SAVED.format(path=path))
        return StatusResult(code=SS__CONFIG__SAVED)

    def _mappings_show(self, tokens: List[str]) -> StatusResult:
        """
        NAME
            _mappings_show - Show CAN mappings content.
        """

        if not isinstance(self._can_mappings, dict):
            print(MESSAGE_ERR_MAPPINGS_LOAD.format(path=EMPTY_STRING))
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        if any(token.lower() in SHOW_SOURCE_FLAGS for token in tokens):
            print(MESSAGE_ERR_MAPPINGS_SHOW_LOCAL_ONLY)
            return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
        _source, cleaned, json_output, pretty, _grouped, ok = self._parse_show_flags(tokens)
        if not ok:
            return StatusResult(code=SS__CLI_PARSER__INVALID_FLAG)
        target = cleaned[COUNT_ZERO].lower() if cleaned else EMPTY_STRING
        if target == MAPPINGS_SHOW_DEVICE_TYPE:
            target = MAPPINGS_SHOW_DEVICE_TYPES
        manufacturers = self._can_mappings.get(KEY_MANUFACTURERS, {})
        device_types = self._can_mappings.get(KEY_DEVICE_TYPES, {})
        print(MESSAGE_SOURCE_LOCAL)
        if json_output:
            if target == MAPPINGS_SHOW_MANUFACTURERS:
                print(self._dump_json({KEY_MANUFACTURERS: manufacturers}, pretty))
                return StatusResult(code=SS__NORMAL)
            if target == MAPPINGS_SHOW_DEVICE_TYPES:
                print(self._dump_json({KEY_DEVICE_TYPES: device_types}, pretty))
                return StatusResult(code=SS__NORMAL)
            print(self._dump_json(self._can_mappings, pretty))
            return StatusResult(code=SS__NORMAL)
        if target and target not in MAPPINGS_SHOW_TARGETS:
            print(MESSAGE_ERR_MAPPINGS_SHOW)
            return StatusResult(code=SS__CLI_PARSER__UNKNOWN_COMMAND)
        print(MESSAGE_MAPPINGS_HEADER)
        if target in (EMPTY_STRING, MAPPINGS_SHOW_MANUFACTURERS):
            print(MESSAGE_MAPPINGS_MANUFACTURERS_HEADER)
            self._print_mappings_entries(manufacturers)
            if target == MAPPINGS_SHOW_MANUFACTURERS:
                return StatusResult(code=SS__NORMAL)
        if target in (EMPTY_STRING, MAPPINGS_SHOW_DEVICE_TYPES):
            print(MESSAGE_MAPPINGS_DEVICE_TYPES_HEADER)
            self._print_mappings_entries(device_types)
        return StatusResult(code=SS__NORMAL)

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

    def _mappings_entry_command(self, target_key: str, tokens: List[str]) -> StatusResult:
        """
        NAME
            _mappings_entry_command - Edit manufacturer/device-type entries.
        """

        if not tokens:
            print(MESSAGE_ERR_MAPPINGS_SUBCOMMAND)
            return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
        action = tokens[COUNT_ZERO].lower()
        if action == CMD_SET:
            if len(tokens) < COUNT_THREE:
                print(MESSAGE_ERR_MAPPINGS_SET.format(target=target_key))
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            try:
                key = int(tokens[COUNT_ONE])
            except ValueError:
                print(MESSAGE_ERR_MAPPINGS_ID)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            name = " ".join(tokens[COUNT_TWO:]).strip()
            entries = self._can_mappings.setdefault(target_key, {})
            entries[str(key)] = name
            self._mark_mappings_dirty()
            return StatusResult(code=SS__NORMAL)
        if action in (CMD_DELETE, CMD_NO):
            if len(tokens) < COUNT_TWO:
                print(MESSAGE_ERR_MAPPINGS_DELETE.format(target=target_key))
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            try:
                key = int(tokens[COUNT_ONE])
            except ValueError:
                print(MESSAGE_ERR_MAPPINGS_ID)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            entries = self._can_mappings.setdefault(target_key, {})
            entries.pop(str(key), None)
            self._mark_mappings_dirty()
            return StatusResult(code=SS__NORMAL)
        print(MESSAGE_ERR_MAPPINGS_SUBCOMMAND)
        return StatusResult(code=SS__CLI_PARSER__UNKNOWN_COMMAND)

    def _mappings_validate(self, path: Optional[Path]) -> StatusResult:
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
                return StatusResult(code=SS__CONFIG__INVALID)
            if not isinstance(loaded, dict):
                print(MESSAGE_ERR_MAPPINGS_VALIDATE.format(message=EMPTY_STRING))
                return StatusResult(code=SS__CONFIG__INVALID)
            payload = loaded
        self._store.set_mappings_payload(payload or {})
        result = self._store.validate_mappings_only(strict=True)
        errors = [issue for issue in result.errors() if issue.location == LOCATION_MAPPINGS]
        if errors:
            message = self._format_store_errors(errors)
            print(MESSAGE_ERR_MAPPINGS_VALIDATE.format(message=message))
            return StatusResult(code=SS__CONFIG__INVALID)
        print(AST_EXEC_SPEC["msg_ok_config"])
        return StatusResult(code=SS__CONFIG__VALID)

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

    def _config_test_command(self, tokens: List[str]) -> StatusResult:
        """
        NAME
            _config_test_command - Handle config-mode test authoring commands.
        """

        self._ensure_tests_loaded()
        if len(tokens) < 2:
            print(MESSAGE_ERROR_TEST_SUBCOMMAND)
            return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
        sub = tokens[1].lower()
        if sub == CMD_SET and len(tokens) >= 3:
            name = tokens[2]
            if not name:
                print(MESSAGE_ERROR_TEST_SET_NAME)
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            self._tests_active_set = name
            if self._tests_model and name not in self._tests_model.test_sets:
                self._tests_model.test_sets[name] = TestSetModel(name=name, tests=[])
                self._mark_tests_dirty()
            print(MESSAGE_SELECTED_TEST_SET.format(name=name))
            return StatusResult(code=SS__NORMAL)
        if sub == CMD_CREATE and len(tokens) >= 3:
            name = tokens[2]
            err = validate_test_name(name)
            if err:
                print(MESSAGE_ERROR_WITH_TEXT.format(message=err))
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            test_set = self._get_active_test_set()
            if self._find_test(name, test_set):
                if self._batch:
                    print(MESSAGE_ERROR_TEST_EXISTS)
                    return StatusResult(code=SS__CONFIG__INVALID)
                prompt = PROMPT_OVERWRITE.format(name=name)
                confirm = input(prompt).strip().lower()
                if confirm != CONFIRM_YES:
                    print(MESSAGE_CANCELLED)
                    return StatusResult(code=SS__EXECUTOR__CANCELLED)
                self._delete_test(name, test_set)
            test_set.tests.append(
                TestModel(
                    name=name,
                    test_type=TEST_TYPE_COMPOSITE,
                    devices=[],
                    enabled=False,
                )
            )
            self._mark_tests_dirty()
            self._modes.append(CliMode(MODE_TEST, test=name))
            return StatusResult(code=SS__NORMAL)
        if sub == CMD_DELETE and len(tokens) >= 3:
            name = tokens[2]
            test_set = self._get_active_test_set()
            if not self._delete_test(name, test_set):
                print(MESSAGE_ERROR_TEST_NOT_FOUND)
                return StatusResult(code=SS__CONFIG__INVALID)
            self._mark_tests_dirty()
            print(MESSAGE_DELETED_TEST.format(name=name))
            return StatusResult(code=SS__NORMAL)
        if len(tokens) >= 2 and sub not in (CMD_CREATE, CMD_DELETE, CMD_SET):
            name = tokens[1]
            test_set = self._get_active_test_set()
            if not self._find_test(name, test_set):
                print(MESSAGE_ERROR_TEST_NOT_FOUND)
                return StatusResult(code=SS__CONFIG__INVALID)
            self._modes.append(CliMode(MODE_TEST, test=name))
            return StatusResult(code=SS__NORMAL)
        print(MESSAGE_ERROR_UNKNOWN_TEST)
        return StatusResult(code=SS__CLI_PARSER__UNKNOWN_COMMAND)

    def _test_mode_command(self, tokens: List[str]) -> Optional[int]:
        """
        NAME
            _test_mode_command - Handle test-mode configuration commands.
        """

        self._ensure_tests_loaded()
        if not tokens:
            return StatusResult(code=SS__NORMAL)
        cmd = tokens[0].lower()
        if cmd == CMD_WRITE and len(tokens) >= COUNT_TWO and tokens[COUNT_ONE].lower() == CMD_TESTS:
            print("ERROR: You are in test edit mode. Use `exit` or `end` first.")
            return StatusResult(code=SS__CLI_PARSER__INVALID_COMMAND)
        if cmd == CMD_TESTS:
            print(MESSAGE_ERR_TESTS_EDIT_MODE)
            return StatusResult(code=SS__CLI_PARSER__INVALID_COMMAND)
        if cmd in (CMD_EXIT, CMD_END):
            self._pop_mode()
            return StatusResult(code=SS__NORMAL)
        test = self._get_active_test()
        if test is None:
            print(MESSAGE_ERROR_TEST_MODE)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
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
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
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
                test.joystick = None
                test.deadband_sweep = None
                test.device_action = None
            self._mark_tests_dirty()
            return StatusResult(code=SS__NORMAL)
        if cmd == CMD_DEVICE and len(tokens) >= 3 and tokens[1].lower() == CMD_ADD:
            label = tokens[2]
            role = DEVICE_ROLE_PRIMARY
            if len(tokens) >= 5:
                if tokens[3].lower() != CMD_ROLE or tokens[4].lower() not in (
                    DEVICE_ROLE_PRIMARY,
                    DEVICE_ROLE_OBSERVER,
                ):
                    print(MESSAGE_ERROR_DSL_DEVICE_ROLE)
                    return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
                role = tokens[4].lower()
            elif len(tokens) == 4:
                print(MESSAGE_ERROR_DSL_DEVICE_ROLE)
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            if not self._is_device_label_valid(label):
                if self._tests_duplicate_labels:
                    print(MESSAGE_ERROR_DEVICE_LABEL_DUPLICATE)
                else:
                    print(MESSAGE_ERROR_DEVICE_LABEL)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            if label in test.devices or label in test.observers:
                self._warn(MESSAGE_ERROR_DEVICE_DUP)
                return StatusResult(code=SS__NORMAL)
            if role == DEVICE_ROLE_OBSERVER:
                test.observers.append(label)
            else:
                test.devices.append(label)
            self._mark_tests_dirty()
            return StatusResult(code=SS__NORMAL)
        if cmd == CMD_DEVICE and len(tokens) >= 5 and tokens[1].lower() == CMD_CREATE:
            name = tokens[2]
            if tokens[3].lower() != CMD_TYPE or tokens[4] != PSEUDO_DEVICE_TYPE_TEST_TIMER:
                print(MESSAGE_ERROR_DSL_DEVICE_CREATE)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            if name.strip().lower() == BUILTIN_TIMER_NAME:
                print(MESSAGE_ERROR_DSL_CREATED_DEVICE_RESERVED)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            if name in test.devices or name in test.observers:
                print(MESSAGE_ERROR_DSL_CREATED_DEVICE_COLLISION)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            if any(device.name == name for device in test.pseudo_devices):
                print(MESSAGE_ERROR_DSL_CREATED_DEVICE_EXISTS)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            test.pseudo_devices.append(
                TestPseudoDeviceModel(name=name, device_type=PSEUDO_DEVICE_TYPE_TEST_TIMER)
            )
            self._mark_tests_dirty()
            return StatusResult(code=SS__NORMAL)
        if cmd == CMD_NO and len(tokens) >= 3 and tokens[1].lower() == CMD_DEVICE:
            label = tokens[2]
            if label in test.devices:
                test.devices.remove(label)
                self._mark_tests_dirty()
            if label in test.observers:
                test.observers.remove(label)
                self._mark_tests_dirty()
            removed_pseudo = [device for device in test.pseudo_devices if device.name == label]
            if removed_pseudo:
                test.pseudo_devices = [device for device in test.pseudo_devices if device.name != label]
                self._mark_tests_dirty()
            return StatusResult(code=SS__NORMAL)
        if cmd == CMD_COMMAND:
            command_model = self._parse_test_command(tokens)
            if command_model is None:
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            test.commands.append(command_model)
            self._mark_tests_dirty()
            return StatusResult(code=SS__NORMAL)
        if cmd in (CMD_UNTIL, CMD_EXPECT, CMD_SUCCESS, CMD_ABORT):
            condition_model = self._parse_test_condition(cmd, tokens)
            if condition_model is None:
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            if cmd == CMD_UNTIL:
                test.until_conditions.append(condition_model)
            elif cmd == CMD_EXPECT:
                test.expect_conditions.append(condition_model)
            elif cmd == CMD_SUCCESS:
                test.success_conditions.append(condition_model)
            else:
                test.abort_conditions.append(condition_model)
            self._mark_tests_dirty()
            return StatusResult(code=SS__NORMAL)
        if cmd == CMD_PASSIVE and len(tokens) >= 2:
            value = self._parse_bool_token(tokens[1])
            if value is None:
                print(MESSAGE_ERROR_DSL_PASSIVE)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            test.passive = value
            self._mark_tests_dirty()
            return StatusResult(code=SS__NORMAL)
        if cmd == CMD_MANUAL_STOP and len(tokens) >= 2:
            value = self._parse_bool_token(tokens[1])
            if value is None:
                print(MESSAGE_ERROR_DSL_MANUAL_STOP)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            test.manual_stop = value
            self._mark_tests_dirty()
            return StatusResult(code=SS__NORMAL)
        if cmd == CMD_INPUT_SOURCE:
            if test.test_type not in (TEST_TYPE_JOYSTICK, TEST_TYPE_BUTTON, TEST_TYPE_COMPOSITE):
                print(MESSAGE_ERROR_INPUT_SOURCE_TYPE)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            if len(tokens) != 2:
                print(MESSAGE_ERROR_INPUT_SOURCE_VALUE)
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            value = tokens[1].strip()
            if "." not in value:
                print(MESSAGE_ERROR_INPUT_SOURCE_VALUE)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            test.input_source = value
            self._mark_tests_dirty()
            return StatusResult(code=SS__NORMAL)
        if cmd == CMD_DEADBAND and len(tokens) >= 2:
            if test.test_type != TEST_TYPE_JOYSTICK:
                print(MESSAGE_ERROR_DEADBAND_TYPE)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            try:
                value = float(tokens[1])
            except ValueError:
                print(MESSAGE_ERROR_DEADBAND_NUMBER)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            if value < DEADBAND_MIN or value > DEADBAND_MAX:
                print(MESSAGE_ERROR_DEADBAND_RANGE)
                return StatusResult(code=SS__CLI_VALIDATOR__OUT_OF_RANGE)
            test.joystick = test.joystick or TestBindingJoystick()
            test.joystick.deadband = value
            self._mark_tests_dirty()
            return StatusResult(code=SS__NORMAL)
        if cmd == CMD_DUTY and len(tokens) >= 2:
            if test.test_type not in (TEST_TYPE_BUTTON, TEST_TYPE_COMPOSITE):
                print(MESSAGE_ERROR_DUTY_TYPE)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            try:
                value = float(tokens[1])
            except ValueError:
                print(MESSAGE_ERROR_DUTY_NUMBER)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            if value < DUTY_MIN or value > DUTY_MAX:
                print(MESSAGE_ERROR_DUTY_RANGE)
                return StatusResult(code=SS__CLI_VALIDATOR__OUT_OF_RANGE)
            test.button = test.button or TestBindingButton()
            test.button.duty = value
            self._mark_tests_dirty()
            return StatusResult(code=SS__NORMAL)
        if cmd == CMD_ACTION and len(tokens) >= 2:
            if test.test_type != TEST_TYPE_DEVICE_ACTION:
                print(MESSAGE_ERROR_ACTION_TYPE)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            action = tokens[1].lower()
            if action not in ACTION_ALLOWED:
                print(MESSAGE_ERROR_ACTION_REQUIRED)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            test.device_action = test.device_action or DeviceActionModel()
            test.device_action.action = action
            self._mark_tests_dirty()
            return StatusResult(code=SS__NORMAL)
        if cmd == CMD_COLOR and len(tokens) >= 2:
            if test.test_type != TEST_TYPE_DEVICE_ACTION:
                print(MESSAGE_ERROR_COLOR_TYPE)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            value = tokens[1]
            if not COLOR_HEX_PATTERN.match(value):
                print(MESSAGE_ERROR_COLOR_REQUIRED)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            test.device_action = test.device_action or DeviceActionModel()
            test.device_action.color = value
            self._mark_tests_dirty()
            return StatusResult(code=SS__NORMAL)
        if cmd == CMD_PATTERN and len(tokens) >= 2:
            if test.test_type != TEST_TYPE_DEVICE_ACTION:
                print(MESSAGE_ERROR_PATTERN_TYPE)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            value = tokens[1].lower()
            if value not in PATTERN_ALLOWED:
                print(MESSAGE_ERROR_PATTERN_VALUE)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            test.device_action = test.device_action or DeviceActionModel()
            test.device_action.pattern = value
            self._mark_tests_dirty()
            return StatusResult(code=SS__NORMAL)
        if cmd == CMD_BRIGHTNESS and len(tokens) >= 2:
            if test.test_type != TEST_TYPE_DEVICE_ACTION:
                print(MESSAGE_ERROR_BRIGHTNESS_TYPE)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            try:
                value = float(tokens[1])
            except ValueError:
                print(MESSAGE_ERROR_BRIGHTNESS_NUMBER)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            if value < BRIGHTNESS_MIN or value > BRIGHTNESS_MAX:
                print(MESSAGE_ERROR_BRIGHTNESS_RANGE)
                return StatusResult(code=SS__CLI_VALIDATOR__OUT_OF_RANGE)
            test.device_action = test.device_action or DeviceActionModel()
            test.device_action.brightness = value
            self._mark_tests_dirty()
            return StatusResult(code=SS__NORMAL)
        if cmd == CMD_DURATION and len(tokens) >= 2:
            if test.test_type != TEST_TYPE_DEVICE_ACTION:
                print(MESSAGE_ERROR_DURATION_TYPE)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            try:
                value = float(tokens[1])
            except ValueError:
                print(MESSAGE_ERROR_DURATION_NUMBER)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            if value < DURATION_MIN_SEC:
                print(MESSAGE_ERROR_DURATION_RANGE)
                return StatusResult(code=SS__CLI_VALIDATOR__OUT_OF_RANGE)
            test.device_action = test.device_action or DeviceActionModel()
            test.device_action.duration_sec = value
            self._mark_tests_dirty()
            return StatusResult(code=SS__NORMAL)
        if cmd == CMD_TERMINATION and len(tokens) >= 2:
            if test.test_type not in (TEST_TYPE_BUTTON, TEST_TYPE_COMPOSITE):
                print(MESSAGE_ERROR_TERMINATION)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            term = test.termination
            kind = tokens[1].lower()
            if kind == TERMINATION_HOLD:
                term.hold_enabled = True
                self._mark_tests_dirty()
                return StatusResult(code=SS__NORMAL)
            if kind == TERMINATION_TIME and len(tokens) >= 3:
                try:
                    value = float(tokens[2])
                except ValueError:
                    print(MESSAGE_ERROR_TERMINATION_TIME)
                    return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
                if value < TIME_MIN_SEC:
                    print(MESSAGE_ERROR_TERMINATION_TIME_RANGE)
                    return StatusResult(code=SS__CLI_VALIDATOR__OUT_OF_RANGE)
                term.time_sec = value
                term.time_on_timeout = term.time_on_timeout or TIME_ON_TIMEOUT_DEFAULT
                self._mark_tests_dirty()
                return StatusResult(code=SS__NORMAL)
            if kind == TERMINATION_ROTATION and len(tokens) >= 3:
                try:
                    value = float(tokens[2])
                except ValueError:
                    print(MESSAGE_ERROR_TERMINATION_ROTATION)
                    return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
                if value < ROTATION_MIN:
                    print(MESSAGE_ERROR_TERMINATION_ROTATION_RANGE)
                    return StatusResult(code=SS__CLI_VALIDATOR__OUT_OF_RANGE)
                term.rotation_limit = value
                self._mark_tests_dirty()
                return StatusResult(code=SS__NORMAL)
            if kind == TERMINATION_LIMITSWITCH:
                limit = term.limit_switch or deepcopy(LIMIT_SWITCH_DEFAULT)
                if len(tokens) >= 3:
                    limit[LIMIT_SWITCH_KEY_ID] = tokens[2]
                term.limit_switch = limit
                self._mark_tests_dirty()
                return StatusResult(code=SS__NORMAL)
            print(MESSAGE_ERROR_TERMINATION)
            return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
        if cmd == CMD_ROTATION and len(tokens) >= 2:
            if test.test_type not in (TEST_TYPE_BUTTON, TEST_TYPE_COMPOSITE):
                print(MESSAGE_ERROR_ROTATION_TYPE)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            term = test.termination
            field = tokens[1].lower()
            if field == "limit" and len(tokens) >= 3:
                try:
                    value = float(tokens[2])
                except ValueError:
                    print(MESSAGE_ERROR_TERMINATION_ROTATION)
                    return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
                if value < ROTATION_MIN:
                    print(MESSAGE_ERROR_TERMINATION_ROTATION_RANGE)
                    return StatusResult(code=SS__CLI_VALIDATOR__OUT_OF_RANGE)
                term.rotation_limit = value
                self._mark_tests_dirty()
                return StatusResult(code=SS__NORMAL)
            if field == "encoderkey" and len(tokens) >= 3:
                term.rotation_encoder_key = tokens[2]
                self._mark_tests_dirty()
                return StatusResult(code=SS__NORMAL)
            if field == "encodersource" and len(tokens) >= 3:
                term.rotation_encoder_source = tokens[2]
                self._mark_tests_dirty()
                return StatusResult(code=SS__NORMAL)
            if field == "encodermotorindex" and len(tokens) >= 3:
                try:
                    term.rotation_encoder_motor_index = int(tokens[2])
                except ValueError:
                    print(MESSAGE_ERROR_TERMINATION_ROTATION)
                    return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
                self._mark_tests_dirty()
                return StatusResult(code=SS__NORMAL)
            if field == "encodercountsperrev" and len(tokens) >= 3:
                try:
                    term.rotation_encoder_counts_per_rev = float(tokens[2])
                except ValueError:
                    print(MESSAGE_ERROR_TERMINATION_ROTATION)
                    return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
                self._mark_tests_dirty()
                return StatusResult(code=SS__NORMAL)
            print(MESSAGE_ERROR_TERMINATION)
            return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
        if cmd == CMD_TIME and len(tokens) >= 2:
            if test.test_type not in (TEST_TYPE_BUTTON, TEST_TYPE_COMPOSITE):
                print(MESSAGE_ERROR_TIME_TYPE)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            term = test.termination
            field = tokens[1].lower()
            if field == "timeout" and len(tokens) >= 3:
                try:
                    value = float(tokens[2])
                except ValueError:
                    print(MESSAGE_ERROR_TERMINATION_TIME)
                    return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
                if value < TIME_MIN_SEC:
                    print(MESSAGE_ERROR_TERMINATION_TIME_RANGE)
                    return StatusResult(code=SS__CLI_VALIDATOR__OUT_OF_RANGE)
                term.time_sec = value
                self._mark_tests_dirty()
                return StatusResult(code=SS__NORMAL)
            if field == "ontimeout" and len(tokens) >= 3:
                term.time_on_timeout = tokens[2]
                self._mark_tests_dirty()
                return StatusResult(code=SS__NORMAL)
            print(MESSAGE_ERROR_TERMINATION)
            return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
        if cmd == CMD_HOLD and len(tokens) >= 2:
            if test.test_type not in (TEST_TYPE_BUTTON, TEST_TYPE_COMPOSITE):
                print(MESSAGE_ERROR_HOLD_TYPE)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            term = test.termination
            field = tokens[1].lower()
            if field == "onrelease" and len(tokens) >= 3:
                term.hold_enabled = True
                term.hold_on_release = tokens[2]
                self._mark_tests_dirty()
                return StatusResult(code=SS__NORMAL)
            print(MESSAGE_ERROR_TERMINATION)
            return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
        if cmd == CMD_LIMITSWITCH and len(tokens) >= 2:
            if test.test_type not in (TEST_TYPE_BUTTON, TEST_TYPE_COMPOSITE):
                print(MESSAGE_ERROR_LIMITSWITCH_TYPE)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            term = test.termination
            limit = term.limit_switch or deepcopy(LIMIT_SWITCH_DEFAULT)
            field = tokens[1].lower()
            if field == "onhit" and len(tokens) >= 3:
                limit[LIMIT_SWITCH_KEY_ON_HIT] = tokens[2]
                term.limit_switch = limit
                self._mark_tests_dirty()
                return StatusResult(code=SS__NORMAL)
            if field == "id" and len(tokens) >= 3:
                limit[LIMIT_SWITCH_KEY_ID] = tokens[2]
                term.limit_switch = limit
                self._mark_tests_dirty()
                return StatusResult(code=SS__NORMAL)
            print(MESSAGE_ERROR_TERMINATION)
            return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
        if cmd == CMD_DEADBAND_SWEEP:
            if test.test_type != TEST_TYPE_DEADBAND_SWEEP:
                print(MESSAGE_ERROR_DEADBAND_SWEEP_TYPE)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            if len(tokens) < 3:
                print(MESSAGE_ERROR_DEADBAND_SWEEP_FIELD)
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
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
                    return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            except ValueError:
                print(MESSAGE_ERROR_DEADBAND_SWEEP_FIELD)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            self._mark_tests_dirty()
            return StatusResult(code=SS__NORMAL)
        if cmd == CMD_ENABLED and len(tokens) >= 2:
            value = tokens[1].lower()
            if value in ("true", "on", "1", "yes"):
                test.enabled = True
            elif value in ("false", "off", "0", "no"):
                test.enabled = False
            else:
                print("ERROR: enabled requires true/false.")
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            self._mark_tests_dirty()
            return StatusResult(code=SS__NORMAL)
        if cmd == CMD_SHOW:
            self._print_test(test)
            return StatusResult(code=SS__NORMAL)
        print(MESSAGE_ERROR_UNKNOWN_TEST)
        return StatusResult(code=SS__CLI_PARSER__UNKNOWN_COMMAND)

    def _parse_test_command(self, tokens: List[str]) -> Optional[TestCommandModel]:
        """
        NAME
            _parse_test_command - Parse a DSL command assignment line.
        """

        if len(tokens) < COUNT_FOUR or tokens[COUNT_TWO] != TOKEN_EQUALS:
            print(MESSAGE_ERROR_DSL_COMMAND)
            return None
        signal = tokens[COUNT_ONE].strip()
        if not signal:
            print(MESSAGE_ERROR_DSL_COMMAND)
            return None
        value = self._parse_scalar_token(tokens[COUNT_THREE])
        if value is None:
            print(MESSAGE_ERROR_DSL_COMMAND)
            return None
        return TestCommandModel(signal=signal, value=value)

    def _parse_test_condition(
        self,
        kind: str,
        tokens: List[str],
    ) -> Optional[TestConditionModel]:
        """
        NAME
            _parse_test_condition - Parse a DSL condition expression.
        """

        if len(tokens) < COUNT_FOUR:
            print(MESSAGE_ERROR_DSL_CONDITION.format(kind=kind))
            return None
        signal = tokens[COUNT_ONE].strip()
        operator = tokens[COUNT_TWO].strip()
        if operator not in DSL_ALLOWED_OPERATORS:
            print(MESSAGE_ERROR_DSL_OPERATOR)
            return None
        value = self._parse_scalar_token(tokens[COUNT_THREE])
        if value is None:
            print(MESSAGE_ERROR_DSL_CONDITION.format(kind=kind))
            return None
        return TestConditionModel(signal=signal, operator=operator, value=value)

    def _parse_bool_token(self, token: str) -> Optional[bool]:
        """
        NAME
            _parse_bool_token - Parse a CLI true/false token.
        """

        value = token.strip().lower()
        if value in (BOOLEAN_TRUE, CMD_ON, "1", "yes"):
            return True
        if value in (BOOLEAN_FALSE, CMD_OFF, "0", "no"):
            return False
        return None

    def _parse_scalar_token(self, token: str) -> Optional[object]:
        """
        NAME
            _parse_scalar_token - Parse a DSL scalar token.
        """

        bool_value = self._parse_bool_token(token)
        if bool_value is not None:
            return bool_value
        raw = token.strip()
        if not raw:
            return None
        try:
            if raw.isdigit() or (raw.startswith("-") and raw[1:].isdigit()):
                return int(raw)
            return float(raw)
        except ValueError:
            return raw

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
        label = self._normalize_device_label_input(label)
        if self._tests_duplicate_labels:
            return False
        if not self._tests_device_catalog:
            return False
        return label in self._tests_device_catalog

    def _normalize_device_label_input(self, label: str) -> str:
        """
        NAME
            _normalize_device_label_input - Strip CLI-rendered metadata from a device label.

        DESCRIPTION
            Accepts labels formatted like:
              - "LABEL (VENDOR TYPE id=25)"
              - "label=LABEL vendor=VENDOR type=TYPE id=25"
            Returns the raw LABEL for local lookups.
        """
        if not isinstance(label, str):
            return label
        raw = label.strip()
        if raw.startswith(LABEL_INPUT_PREFIX):
            trimmed = raw[len(LABEL_INPUT_PREFIX) :]
            for marker in LABEL_INPUT_MARKERS:
                idx = trimmed.find(marker)
                if idx != -1:
                    return trimmed[:idx].strip()
            return trimmed.strip()
        match = re.match(LABEL_INPUT_PAREN_REGEX, raw)
        if match:
            return match.group("label").strip()
        return raw

    def _print_tests_local(self, json_output: bool, pretty: bool, show_source: bool) -> StatusResult:
        """
        NAME
            _print_tests_local - Print local tests output.
        """
        if show_source:
            print(MESSAGE_SOURCE_LOCAL)
        if json_output:
            payload = self._build_tests_overview_payload()
            print(self._dump_json(payload, pretty))
            return StatusResult(code=SS__NORMAL)
        payload = self._build_tests_overview_payload()
        print(self._format_tests_overview_text(payload))
        return StatusResult(code=SS__NORMAL)

    def _build_tests_overview_payload(self) -> Dict[str, object]:
        """
        NAME
            _build_tests_overview_payload - Build tests overview matching robot schema.
        """
        self._ensure_tests_loaded()
        model = self._tests_model or TestAuthoringModel()
        active_set = self._tests_active_set or model.default_test_set or EMPTY_STRING
        default_set = model.default_test_set or EMPTY_STRING
        test_set = model.test_sets.get(active_set)
        if not isinstance(test_set, TestSetModel):
            test_set = TestSetModel(name=active_set, tests=[])
        total_count = len(test_set.tests)
        enabled_count = 0
        rows = []
        for index, test in enumerate(test_set.tests):
            if not isinstance(test, TestModel):
                continue
            if test.enabled:
                enabled_count += 1
            rows.append(
                {
                    KEY_TESTS_INDEX: index,
                    KEY_TESTS_NAME: test.name,
                    KEY_TESTS_ENABLED: bool(test.enabled),
                    KEY_TESTS_SELECTED: False,
                    KEY_TESTS_TYPE: test.test_type,
                    KEY_TESTS_STATUS: EMPTY_STRING,
                    KEY_TESTS_REQUIRED_DEVICES: list(test.devices) if isinstance(test.devices, list) else [],
                }
            )
        return {
            KEY_TESTS_ACTIVE_SET: active_set,
            KEY_TESTS_DEFAULT_SET: default_set,
            KEY_TESTS_USING_SETS: len(model.test_sets) > TESTS_MULTISET_MIN_COUNT,
            KEY_TESTS_TOTAL_COUNT: total_count,
            KEY_TESTS_ENABLED_COUNT: enabled_count,
            KEY_TESTS_ROWS: rows,
        }

    def _format_tests_overview_text(self, payload: Dict[str, object]) -> str:
        """
        NAME
            _format_tests_overview_text - Render tests overview text matching robot output.
        """
        if not isinstance(payload, dict):
            return SEP_NEWLINE.join([TEXT_TESTS_HEADER, TEXT_TESTS_NO_TESTS, TEXT_TESTS_FOOTER])
        rows = payload.get(KEY_TESTS_ROWS, [])
        total_count = payload.get(KEY_TESTS_TOTAL_COUNT, 0)
        enabled_count = payload.get(KEY_TESTS_ENABLED_COUNT, 0)
        using_sets = bool(payload.get(KEY_TESTS_USING_SETS, False))
        active_set = str(payload.get(KEY_TESTS_ACTIVE_SET, TEXT_STATUS_NONE)).strip()
        default_set = str(payload.get(KEY_TESTS_DEFAULT_SET, TEXT_STATUS_NONE)).strip()
        lines = [TEXT_TESTS_HEADER]
        if using_sets:
            lines.append(
                TEXT_TESTS_ACTIVE_SET.format(
                    active=active_set or TEXT_STATUS_NONE,
                    default=default_set or TEXT_STATUS_NONE,
                )
            )
        lines.append(
            TEXT_TESTS_COUNTS.format(
                total=total_count,
                enabled=enabled_count,
            )
        )
        lines.append(TEXT_TESTS_TABLE_HEADER)
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict):
                    continue
                index = int(row.get(KEY_TESTS_INDEX, 0))
                selected = bool(row.get(KEY_TESTS_SELECTED, False))
                enabled = bool(row.get(KEY_TESTS_ENABLED, False))
                test_type = str(row.get(KEY_TESTS_TYPE, EMPTY_STRING)).strip() or TEXT_TESTS_TYPE_UNKNOWN
                name = str(row.get(KEY_TESTS_NAME, EMPTY_STRING)).strip() or TEXT_TESTS_NAME_UNNAMED
                required_devices = row.get(KEY_TESTS_REQUIRED_DEVICES, [])
                required_devices_text = (
                    SEP_COMMA_SPACE.join([str(d) for d in required_devices if str(d).strip()])
                    if isinstance(required_devices, list) and required_devices
                    else TEXT_TESTS_DEVICES_EMPTY
                )
                sel_char = TEXT_TESTS_SELECTED_MARK if selected else TEXT_TESTS_SELECTED_EMPTY
                en_char = TEXT_TESTS_ENABLED_MARK if enabled else TEXT_TESTS_DISABLED_MARK
                lines.append(
                    TEXT_TESTS_ROW_FMT.format(
                        index=index,
                        sel=sel_char,
                        en=en_char,
                        type=test_type,
                        name=name,
                        hold=TEXT_TESTS_HOLD_DEFAULT,
                        devices=required_devices_text,
                    )
                )
        lines.append(TEXT_TESTS_FOOTER)
        return SEP_NEWLINE.join(lines)

    def _show_tests_robot(self, json_output: bool, pretty: bool) -> StatusResult:
        """
        NAME
            _show_tests_robot - Request tests overview from the robot.
        """
        seq = show_tests(self._session, json_output=json_output)
        if seq is None:
            print(MESSAGE_ERR_COMMAND_SEND_FAILED)
            return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
        self._proto_mark_cmd_sent(CMD_SHOW_TESTS, now=time.time())
        self._show_label_seq[int(seq)] = SHOW_SOURCE_ROBOT
        self._show_pretty_json_seq[int(seq)] = bool(pretty)
        event = self._wait_for_seq(seq, timeout_sec=ROBOT_LONG_COMMAND_TIMEOUT_SEC)
        if self._event_failed(event, MESSAGE_LABEL_SHOW_TESTS):
            return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
        return StatusResult(code=SS__NORMAL)

    def _show_tests_command(self, tokens: List[str]) -> StatusResult:
        """
        NAME
            _show_tests_command - Render test authoring state.
        """

        self._ensure_tests_loaded()
        source, cleaned, json_output, pretty, _grouped, ok = self._parse_show_flags(tokens[1:])
        if not ok:
            return StatusResult(code=SS__CLI_PARSER__INVALID_FLAG)
        target = cleaned[0].lower() if cleaned else EMPTY_STRING
        is_list = target == CMD_TESTS
        is_single = target == CMD_TEST and len(cleaned) >= COUNT_TWO

        if source in (SHOW_SOURCE_ROBOT, SHOW_SOURCE_BOTH):
            if not self._session.is_connected():
                print(MESSAGE_ERR_SHOW_TESTS_ROBOT_ONLY)
                return StatusResult(code=SS__NETWORK__NOT_CONNECTED)
            if is_single:
                print(MESSAGE_ERR_TEST_SHOW_LOCAL_ONLY)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            if not is_list:
                print(MESSAGE_ERROR_SHOW_TESTS)
                return StatusResult(code=SS__CLI_PARSER__UNKNOWN_COMMAND)
            if source == SHOW_SOURCE_BOTH:
                self._print_tests_local(json_output, pretty, show_source=True)
            return self._show_tests_robot(json_output, pretty)

        if is_list:
            return self._print_tests_local(json_output, pretty, show_source=False)
        if is_single:
            test_set = self._get_active_test_set()
            test = self._find_test(cleaned[1], test_set)
            if not test:
                print(MESSAGE_ERROR_TEST_NOT_FOUND)
                return StatusResult(code=SS__CONFIG__INVALID)
            if json_output:
                self._print_test_json(test, pretty)
                return StatusResult(code=SS__NORMAL)
            self._print_test(test)
            return StatusResult(code=SS__NORMAL)
        print(MESSAGE_ERROR_SHOW_TESTS)
        return StatusResult(code=SS__CLI_PARSER__UNKNOWN_COMMAND)

    def _save_tests_command(self, tokens: List[str]) -> StatusResult:
        """
        NAME
            _save_tests_command - Validate and persist tests JSON.
        """
        print(MESSAGE_ERR_TESTS_STANDALONE)
        return StatusResult(code=SS__CONFIG__INVALID)

    def _save_tests_to_path(
        self,
        path: Path,
        *,
        skip_validation: bool = False,
        force: bool = False,
        validation_ok: Optional[bool] = None,
    ) -> StatusResult:
        """
        NAME
            _save_tests_to_path - Save tests payload to disk.
        """
        if not skip_validation:
            allowed, validation_ok = self._guard_save(force)
            if not allowed:
                return StatusResult(code=SS__CONFIG__INVALID)
        if validation_ok is None:
            validation_ok = True
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
            return StatusResult(code=SS__CONFIG__INVALID)
        for issue in result.warnings:
            test_name = issue.test_name or GLOBAL_LABEL
            self._warn(
                MESSAGE_WARNING_WITH_TEST.format(
                    message=issue.message,
                    test=test_name,
                )
            )
        payload = model_to_payload(model)
        ok, error = self._atomic_write_json(
            path,
            payload,
            JSON_PRETTY_INDENT,
            False,
        )
        if not ok:
            print(MESSAGE_ERR_SAVE_WRITE.format(path=path, error=error))
            return StatusResult(code=SS__CONFIG__INVALID)
        self._tests_dirty = False
        self._sync_store_tests()
        self._post_save(
            AUDIT_ACTION_SAVE,
            [SOURCE_NAME_TESTS],
            path,
            payload,
            validation_ok,
            JSON_PRETTY_INDENT,
            False,
        )
        print(MESSAGE_WROTE_TESTS.format(path=path))
        return StatusResult(code=SS__CONFIG__SAVED)

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
        if test.observers:
            observers = DEVICE_JOIN_SEPARATOR.join(test.observers)
            print(MESSAGE_TEST_OBSERVERS.format(devices=observers))
        if test.pseudo_devices:
            created = DEVICE_JOIN_SEPARATOR.join(
                [f"{device.name}:{device.device_type}" for device in test.pseudo_devices]
            )
            print(MESSAGE_TEST_CREATED_DEVICES.format(devices=created))
        if test.input_source:
            print(MESSAGE_TEST_INPUT_SOURCE.format(source=test.input_source))
        if test.commands:
            print(
                MESSAGE_TEST_COMMANDS.format(
                    items=DEVICE_JOIN_SEPARATOR.join(
                        [self._format_test_command(command) for command in test.commands]
                    )
                )
            )
        if test.until_conditions:
            print(
                MESSAGE_TEST_UNTIL.format(
                    items=DEVICE_JOIN_SEPARATOR.join(
                        [self._format_test_condition(condition) for condition in test.until_conditions]
                    )
                )
            )
        if test.expect_conditions:
            print(
                MESSAGE_TEST_EXPECT.format(
                    items=DEVICE_JOIN_SEPARATOR.join(
                        [self._format_test_condition(condition) for condition in test.expect_conditions]
                    )
                )
            )
        if test.success_conditions:
            print(
                MESSAGE_TEST_SUCCESS.format(
                    items=DEVICE_JOIN_SEPARATOR.join(
                        [self._format_test_condition(condition) for condition in test.success_conditions]
                    )
                )
            )
        if test.abort_conditions:
            print(
                MESSAGE_TEST_ABORT.format(
                    items=DEVICE_JOIN_SEPARATOR.join(
                        [self._format_test_condition(condition) for condition in test.abort_conditions]
                    )
                )
            )
        if test.passive:
            print(MESSAGE_TEST_PASSIVE.format(value=test.passive))
        if test.manual_stop:
            print(MESSAGE_TEST_MANUAL_STOP.format(value=test.manual_stop))
        if test.test_type == TEST_TYPE_JOYSTICK and test.joystick:
            print(MESSAGE_TEST_DEADBAND.format(deadband=test.joystick.deadband))
        if test.test_type == TEST_TYPE_BUTTON and test.button:
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

    def _format_test_command(self, command: TestCommandModel) -> str:
        """
        NAME
            _format_test_command - Render one DSL command.
        """

        return f"{command.signal} {TOKEN_EQUALS} {command.value}"

    def _format_test_condition(self, condition: TestConditionModel) -> str:
        """
        NAME
            _format_test_condition - Render one DSL condition.
        """

        return f"{condition.signal} {condition.operator} {condition.value}"

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

    def _exec_command(self, tokens: List[str]) -> StatusResult:
        cmd = tokens[0].lower()
        if cmd == "connect":
            self._proto_mark_connect_attempt()
            if not connect(self._session):
                self._proto_mark_connect_failure()
                print("ERROR: Failed to connect.")
                return StatusResult(code=SS__NETWORK__CONNECT_FAILED)
            ok = self._session.ensure_handshake(reset=True)
            if not ok:
                self._proto_mark_connect_failure()
                message = self._handshake_error_text()
                print(f"ERROR: {message}")
                return StatusResult(code=SS__NETWORK__HANDSHAKE_FAILED, message=message)
            self._proto_mark_connected(now=time.time())
            self._proto_mark_handshake(now=time.time())
            result = self._apply_profile_sync_after_connect(prompt_user=not self._batch)
            if result is not None:
                return result
            self._start_keepalive()
            print("Connected.")
            return StatusResult(code=SS__NORMAL)
        if cmd == "disconnect":
            self._stop_keepalive()
            disconnect(self._session)
            self._proto_mark_disconnected(now=time.time())
            self._robot_selected_profile = None
            self._profile_context_mismatch_seen = None
            print("Disconnected.")
            return StatusResult(code=SS__NORMAL)
        if cmd == "configure" and len(tokens) > 1 and tokens[1].lower() == "terminal":
            self._ensure_local_config()
            self._modes.append(CliMode("config"))
            return StatusResult(code=SS__NORMAL)
        if cmd == CMD_PROFILE:
            if len(tokens) < COUNT_TWO:
                print(MESSAGE_ERR_PROFILE_REQUIRED)
                return StatusResult(code=SS__CONFIG__PROFILE_REQUIRED)
            result = self._set_active_profile(tokens[COUNT_ONE])
            if not result.ok():
                return result
            print(f"Active profile: {self._groups_profile}")
            return StatusResult(code=SS__NORMAL)
        if cmd == CMD_BINDINGS:
            return self._config_bindings_command(tokens)
        if cmd == "lifecycle":
            return self._lifecycle_command(tokens)
        if cmd == CMD_RUNTIME:
            return self._runtime_command(tokens)
        if cmd == "show":
            return self._coerce_status(self._handle_show(tokens[1:]))
        print(f"ERROR: Unknown command: {' '.join(tokens)}")
        return StatusResult(code=SS__CLI_PARSER__UNKNOWN_COMMAND)

    def _handle_save_command(self, tokens: List[str]) -> StatusResult:
        """
        NAME
            _handle_save_command - Dispatch save commands with flags.
        """
        cleaned, flags = self._strip_flags(tokens, [FLAG_FORCE, CMD_PROMPT])
        force = FLAG_FORCE in flags
        prompt = CMD_PROMPT in flags
        if len(cleaned) < COUNT_TWO:
            return self._save_all(prompt, force=force)
        target = cleaned[COUNT_ONE].lower()
        if prompt and target != CMD_ALL:
            print(MESSAGE_ERR_SAVE_PROMPT)
            return StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX)
        if target == CMD_ALL:
            return self._save_all(prompt, force=force)
        if target == CMD_SOURCES:
            return self._save_sources(force=force)
        if target == CMD_TESTS:
            return self._coerce_status(self._save_tests_command(tokens))
        if target == CMD_PROFILES:
            path = cleaned[COUNT_TWO] if len(cleaned) >= COUNT_THREE else EMPTY_STRING
            if not path:
                if not self._local_root_path:
                    print(MESSAGE_SAVE_PROFILES_PATH_REQUIRED)
                    return StatusResult(code=SS__CONFIG__NOT_LOADED)
                if self._batch:
                    print(MESSAGE_SAVE_PROFILES_PATH_REQUIRED)
                    return StatusResult(code=SS__CONFIG__NOT_LOADED)
                if not self._confirm(
                    MESSAGE_SAVE_PROFILES_CONFIRM.format(path=self._local_root_path)
                ):
                    return StatusResult(code=SS__EXECUTOR__CANCELLED)
                path = str(self._local_root_path)
            return self._save_profiles(path, force=force)
        if target == CMD_CONFIG:
            if len(cleaned) < COUNT_THREE:
                print(MESSAGE_ERR_SAVE_PATH_REQUIRED.format(target=CMD_CONFIG))
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            return self._save_unified_config(cleaned[COUNT_TWO], force=force)
        if target == CMD_SAVE_RUNTIME_GROUPS:
            if len(cleaned) < COUNT_THREE:
                print(MESSAGE_ERR_SAVE_PATH_REQUIRED.format(target=CMD_SAVE_RUNTIME_GROUPS))
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            return self._save_runtime_config(cleaned[COUNT_TWO], force=force)
        if target == CMD_SAVE_BRIDGE_CONFIG:
            if len(cleaned) < COUNT_THREE:
                print(MESSAGE_ERR_SAVE_PATH_REQUIRED.format(target=CMD_SAVE_BRIDGE_CONFIG))
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            return self._save_local_config(cleaned[COUNT_TWO], force=force)
        print(MESSAGE_HINT_SAVE)
        return StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX)

    def _config_command(self, tokens: List[str]) -> StatusResult:
        cmd = tokens[0].lower()
        if cmd == "lifecycle":
            return self._lifecycle_command(tokens)
        if cmd == CMD_RUNTIME:
            return self._runtime_command(tokens)
        if cmd == CMD_BINDINGS:
            return self._config_bindings_command(tokens)
        if cmd == CMD_CAN_MAPPINGS:
            return self._config_can_mappings_command(tokens)
        if cmd == CMD_SAVE:
            return self._handle_save_command(tokens)
        if cmd == CMD_RECOVER:
            return self._handle_recover_command(tokens)
        if cmd == CMD_LOAD and len(tokens) >= COUNT_TWO and tokens[COUNT_ONE].lower() == CMD_SOURCES:
            return self._load_sources()
        if cmd == CMD_PROFILES and len(tokens) >= COUNT_TWO and tokens[COUNT_ONE].lower() == CMD_INIT:
            return self._init_profiles_payload()
        if cmd == CMD_PROFILES and len(tokens) >= COUNT_TWO and tokens[COUNT_ONE].lower() == CMD_RELOAD:
            return self._profiles_reload()
        if cmd == CMD_PROFILES and len(tokens) >= COUNT_TWO and tokens[COUNT_ONE].lower() == CMD_ACTIVATE_PROFILE:
            if len(tokens) < COUNT_THREE:
                print(MESSAGE_ERR_PROFILES_ACTIVATE)
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            return self._profiles_activate(tokens[COUNT_TWO])
        if cmd == CMD_PROFILES and len(tokens) >= COUNT_TWO and tokens[COUNT_ONE].lower() == CMD_EXPORT:
            if len(tokens) < COUNT_THREE:
                print(MESSAGE_ERR_PROFILES_EXPORT_PATH)
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            return self._export_profiles_bundle(tokens[COUNT_TWO])
        if cmd == CMD_PROFILE:
            if len(tokens) < 2:
                print(MESSAGE_ERR_PROFILE_REQUIRED)
                return StatusResult(code=SS__CONFIG__PROFILE_REQUIRED)
            if tokens[COUNT_ONE].lower() == CMD_EXPORT:
                cleaned, flags = self._strip_flags(tokens, [FLAG_INSTALL_ROBOT])
                if len(cleaned) < COUNT_FOUR:
                    print(MESSAGE_ERR_PROFILE_REQUIRED)
                    return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
                profile_name = cleaned[COUNT_TWO]
                path = cleaned[COUNT_THREE]
                return self._export_profile_bundle(
                    profile_name,
                    path,
                    install_robot=FLAG_INSTALL_ROBOT in flags,
                )
            if (
                len(tokens) >= COUNT_FOUR
                and tokens[COUNT_ONE].lower() == CMD_DEVICE
                and tokens[COUNT_TWO].lower() == CMD_DELETE
            ):
                name = tokens[COUNT_THREE]
                if not self._confirm(
                    MESSAGE_CONFIRM_PROFILE_DEVICE_DELETE.format(name=name)
                ):
                    return StatusResult(code=SS__EXECUTOR__CANCELLED)
                result = self._delete_profiles_device(name)
                if not result.ok():
                    return result
                print(MESSAGE_PROFILE_DEVICE_DELETED.format(name=name))
                return StatusResult(code=SS__NORMAL)
            if (
                len(tokens) >= COUNT_FOUR
                and tokens[COUNT_ONE].lower() == CMD_DEVICE
                and tokens[COUNT_TWO].lower() == CMD_SHOW_ALL
            ):
                name = tokens[COUNT_THREE]
                return self._show_profiles_device_all(name)
            if len(tokens) >= 3 and tokens[1].lower() == CMD_CREATE:
                result = self._create_profile(tokens[2])
                if not result.ok():
                    return result
                return StatusResult(code=SS__NORMAL)
            if len(tokens) >= 3 and tokens[1].lower() == CMD_DELETE:
                name = tokens[2]
                if not self._batch and not self._confirm(
                    MESSAGE_PROFILE_DELETE_CONFIRM.format(name=name)
                ):
                    return StatusResult(code=SS__EXECUTOR__CANCELLED)
                return self._delete_profile(name)
            result = self._set_active_profile(tokens[1])
            if not result.ok():
                return result
            print(f"Active profile: {self._groups_profile}")
            return StatusResult(code=SS__NORMAL)
        if cmd == "group" and len(tokens) >= 2:
            name = tokens[1]
            if not self._group_exists_for_context(name):
                print(ERR_GROUP_NOT_FOUND_FMT.format(name=name))
                return StatusResult(code=SS__GROUP__NOT_FOUND)
            self._modes.append(CliMode("group", name))
            if not self._session.is_connected():
                self._warn("WARNING: Robot not connected; local group selected.")
                return StatusResult(code=SS__NETWORK__NOT_CONNECTED)
            return StatusResult(code=SS__NORMAL)
        if cmd == "rename" and len(tokens) >= 4 and tokens[1].lower() == "device":
            result = self._rename_local_device(tokens[2], tokens[3])
            if result.ok():
                print(f"Renamed device {tokens[2]} -> {tokens[3]}.")
                return StatusResult(code=SS__NORMAL)
            return result
        if cmd == "no" and len(tokens) >= 3 and tokens[1].lower() == "device":
            name = tokens[2]
            if not self._confirm(f"Delete device '{name}'?"):
                return StatusResult(code=SS__EXECUTOR__CANCELLED)
            result = self._delete_local_device(name)
            if not result.ok():
                return result
            print(f"Deleted device {name}.")
            return StatusResult(code=SS__NORMAL)
        if cmd == "device" and len(tokens) >= 5 and tokens[2].lower() == "set":
            field = tokens[3]
            value_raw = " ".join(tokens[4:])
            result = self._set_local_device_meta(tokens[1], field, value_raw)
            if not result.ok():
                return result
            print(f"Updated device {tokens[1]} {field}={value_raw}.")
            return StatusResult(code=SS__NORMAL)
        if cmd == "group" and len(tokens) >= 2:
            name = tokens[1]
            if not self._group_exists_for_context(name):
                print(ERR_GROUP_NOT_FOUND_FMT.format(name=name))
                return StatusResult(code=SS__GROUP__NOT_FOUND)
            self._modes.append(CliMode("group", name))
            return StatusResult(code=SS__NORMAL)
        if cmd == "device" and len(tokens) >= 2:
            name = tokens[1]
            result = self._ensure_local_device_entry(name)
            if not result.ok():
                return result
            self._modes.append(CliMode("device", device=name))
            return StatusResult(code=SS__NORMAL)
        if cmd == "no" and len(tokens) >= 3 and tokens[1].lower() == "group" and not self._session.is_connected():
            name = tokens[2]
            if not self._confirm(f"Delete group '{name}'?"):
                return StatusResult(code=SS__EXECUTOR__CANCELLED)
            result = self._delete_local_group(name)
            if not result.ok():
                return result
            self._warn("WARNING: Robot not connected; local group deleted.")
            return StatusResult(code=SS__NETWORK__NOT_CONNECTED)
        if cmd == "no" and len(tokens) >= 3 and tokens[1].lower() == "group":
            name = tokens[2]
            if not self._confirm(f"Delete group '{name}'?"):
                return StatusResult(code=SS__EXECUTOR__CANCELLED)
            seq = group_delete(self._session, name, confirm=True)
            event = self._wait_for_seq(seq)
            if self._event_failed(event, "group delete"):
                return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
            return StatusResult(code=SS__NORMAL)
        if cmd == "selected-device" and len(tokens) >= 2 and not self._session.is_connected():
            result = self._set_local_selected_device(tokens[1])
            if not result.ok():
                return result
            self._warn("WARNING: Robot not connected; local selected-device updated.")
            return StatusResult(code=SS__NETWORK__NOT_CONNECTED)
        if cmd == "selected-device" and len(tokens) >= 2:
            seq = selected_device_set(self._session, tokens[1])
            event = self._wait_for_seq(seq)
            if self._event_failed(event, "selected-device"):
                return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
            return StatusResult(code=SS__NORMAL)
        if cmd == "selected-mode" and len(tokens) >= 2 and not self._session.is_connected():
            mode_value = tokens[1].lower()
            if mode_value not in ("on", "off"):
                print("ERROR: selected-mode requires on/off.")
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            enabled = mode_value == "on"
            result = self._set_local_selected_mode(enabled)
            if not result.ok():
                return result
            self._warn("WARNING: Robot not connected; local selected-mode updated.")
            return StatusResult(code=SS__NETWORK__NOT_CONNECTED)
        if cmd == "selected-mode" and len(tokens) >= 2:
            mode_value = tokens[1].lower()
            if mode_value not in ("on", "off"):
                print("ERROR: selected-mode requires on/off.")
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            enabled = mode_value == "on"
            seq = selected_mode_set(self._session, enabled)
            event = self._wait_for_seq(seq)
            if self._event_failed(event, "selected-mode"):
                return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
            return StatusResult(code=SS__NORMAL)
        if cmd == "merge" and len(tokens) >= 3 and tokens[1].lower() == "config":
            plan = merge_config(tokens[2], self._conflict_policy, self._active_profile_name())
            return self._coerce_status(self._apply_config_plan(plan, prompt_on_replace=True))
        if cmd == "import" and len(tokens) >= 3 and tokens[1].lower() == "config":
            plan = import_config(tokens[2], self._conflict_policy, self._active_profile_name())
            return self._coerce_status(self._apply_config_plan(plan, prompt_on_replace=True))
        if cmd == "export" and len(tokens) >= 3 and tokens[1].lower() == "runtime-groups":
            result = export_runtime_groups(self._session, tokens[2], self._active_profile_name())
            message = format_status_message(result.code, **result.message_args) or result.message
            if message:
                print(message)
            return StatusResult(code=SS__NORMAL if result.ok() else SS__NETWORK__COMMAND_SEND_FAILED)
        if cmd == "export" and len(tokens) >= 3 and tokens[1].lower() == "cli-script":
            result = self._export_cli_script(tokens[2])
            if not result.ok():
                return result
            return StatusResult(code=SS__NORMAL)
        if cmd == "save" and len(tokens) >= 2 and tokens[1].lower() == "profiles":
            path = tokens[2] if len(tokens) >= 3 else ""
            if not path:
                if not self._local_root_path:
                    print(MESSAGE_SAVE_PROFILES_PATH_REQUIRED)
                    return StatusResult(code=SS__CONFIG__NOT_LOADED)
                if self._batch:
                    print(MESSAGE_SAVE_PROFILES_PATH_REQUIRED)
                    return StatusResult(code=SS__CONFIG__NOT_LOADED)
                if not self._confirm(MESSAGE_SAVE_PROFILES_CONFIRM.format(path=self._local_root_path)):
                    return StatusResult(code=SS__EXECUTOR__CANCELLED)
                path = str(self._local_root_path)
            result = self._save_profiles(path)
            if not result.ok():
                return result
            return StatusResult(code=SS__NORMAL)
        if cmd == "save" and len(tokens) >= 3 and tokens[1].lower() == CMD_CONFIG:
            result = self._save_unified_config(tokens[2])
            if not result.ok():
                return result
            return StatusResult(code=SS__NORMAL)
        if cmd == "save" and len(tokens) >= 3 and tokens[1].lower() == CMD_SAVE_RUNTIME_GROUPS:
            result = save_config(self._session, tokens[2], self._active_profile_name())
            message = format_status_message(result.code, **result.message_args) or result.message
            if message:
                print(message)
            return StatusResult(code=SS__CONFIG__SAVED if result.ok() else SS__CONFIG__INVALID)
        if cmd == "save" and len(tokens) >= 3 and tokens[1].lower() == CMD_SAVE_BRIDGE_CONFIG:
            result = self._save_local_config(tokens[2])
            if not result.ok():
                return result
            return StatusResult(code=SS__NORMAL)
        if cmd == CMD_SAVE and len(tokens) >= COUNT_TWO and tokens[COUNT_ONE].lower() == CMD_SOURCES:
            result = self._save_sources()
            if not result.ok():
                return result
            return StatusResult(code=SS__NORMAL)
        if cmd == CMD_VALIDATE and len(tokens) >= 2:
            target = tokens[1].lower()
            use_all = tokens[-1].lower() == CMD_VALIDATE_ALL if tokens else False
            verbose = self._flag_present(tokens, FLAG_VERBOSE)
            path = ""
            if len(tokens) >= 3:
                candidate = tokens[2]
                if candidate.lower() not in (CMD_VALIDATE_ALL, FLAG_VERBOSE):
                    path = candidate
            if target == CMD_FILE:
                if not path or path.lower() == FLAG_REPAIR:
                    print(MESSAGE_VALIDATE_FILE_PATH_REQUIRED)
                    return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
                repair = self._flag_present(tokens, FLAG_REPAIR)
                return self._validate_file(path, repair, verbose=verbose)
            if target == CMD_CONFIG:
                if path:
                    if use_all or verbose:
                        ok, message, _config = validate_config_file_all(path)
                    else:
                        ok, message, _config = validate_config_file(path)
                else:
                    if not self._local_config:
                        print("ERROR: Local config not loaded. Use merge/import config <path> first.")
                        return StatusResult(code=SS__CONFIG__NOT_LOADED)
                    if use_all or verbose:
                        ok, message = validate_config_data_all(self._local_config, self._local_root_payload)
                    else:
                        self._sync_store_from_local()
                        result = self._store.validate_profiles_only(strict=True)
                        ok = result.ok()
                        message = self._format_store_errors(result.errors())
                if verbose and message:
                    print(message)
                if ok:
                    print(MESSAGE_OK_CONFIG_VALID)
                    return StatusResult(code=SS__CONFIG__VALID)
                print(MESSAGE_ERR_CONFIG_VALIDATE.format(message=message))
                if path:
                    self._maybe_hint_validate_profile(path)
                return StatusResult(code=SS__CONFIG__INVALID)
            if target == CMD_PROFILES:
                use_robot = any(token.lower() == CMD_ROBOT for token in tokens[COUNT_TWO:])
                active_only = any(token.lower() == CMD_ACTIVE for token in tokens[COUNT_TWO:])
                if use_robot:
                    ok, message = self.validate_profiles_robot()
                elif active_only:
                    profile_name = self._active_profile_name()
                    if not profile_name:
                        print(MESSAGE_ERR_PROFILE_REQUIRED)
                        return StatusResult(code=SS__CONFIG__PROFILE_REQUIRED)
                    ok, message = (
                        self.validate_profiles_only_verbose(profile_name=profile_name)
                        if verbose
                        else self.validate_profiles_only(profile_name=profile_name)
                    )
                else:
                    ok, message = (
                        self.validate_profiles_only_verbose() if verbose else self.validate_profiles_only()
                    )
                if verbose and use_robot and message:
                    print(message)
                if ok:
                    print(MESSAGE_OK_CONFIG_VALID)
                    return StatusResult(code=SS__CONFIG__VALID)
                print(MESSAGE_ERR_CONFIG_VALIDATE.format(message=message))
                return StatusResult(code=SS__CONFIG__INVALID)
            if target == CMD_TESTS:
                active_only = any(token.lower() == CMD_ACTIVE_SET for token in tokens[COUNT_TWO:])
                active_set = None
                if active_only:
                    if self._tests_model is None:
                        self._ensure_tests_loaded()
                    model = self._tests_model or TestAuthoringModel()
                    active_set = self._tests_active_set or model.default_test_set
                ok, message = (
                    self.validate_tests_only_verbose(active_set=active_set)
                    if verbose
                    else self.validate_tests_only(active_set=active_set)
                )
                if ok:
                    print(MESSAGE_OK_CONFIG_VALID)
                    return StatusResult(code=SS__CONFIG__VALID)
                print(MESSAGE_ERR_CONFIG_VALIDATE.format(message=message))
                return StatusResult(code=SS__CONFIG__INVALID)
            if target == CMD_TOPOLOGY:
                return self._validate_topology(verbose=verbose)
            if target == CMD_BINDINGS:
                ok, message = (
                    self.validate_bindings_only_verbose(path or None)
                    if verbose
                    else self.validate_bindings_only(path or None)
                )
                if ok:
                    print(MESSAGE_OK_CONFIG_VALID)
                    return StatusResult(code=SS__CONFIG__VALID)
                print(MESSAGE_ERR_CONFIG_VALIDATE.format(message=message))
                return StatusResult(code=SS__CONFIG__INVALID)
            if target == CMD_CAN_MAPPINGS:
                ok, message = (
                    self.validate_mappings_only_verbose(path or None)
                    if verbose
                    else self.validate_mappings_only(path or None)
                )
                if ok:
                    print(MESSAGE_OK_CONFIG_VALID)
                    return StatusResult(code=SS__CONFIG__VALID)
                print(MESSAGE_ERR_CONFIG_VALIDATE.format(message=message))
                return StatusResult(code=SS__CONFIG__INVALID)
            if target == CMD_SCRIPT:
                if not path:
                    print(MESSAGE_VALIDATE_SCRIPT_PATH_REQUIRED)
                    return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
                if verbose:
                    print(f"INFO: validating script {path}")
                ok, issues = self.lint_script(path)
                if ok:
                    print(MESSAGE_VALIDATE_SCRIPT_OK)
                    return StatusResult(code=SS__CONFIG__VALID)
                print(MESSAGE_VALIDATE_SCRIPT_HEADER)
                for issue in issues:
                    print(issue)
                print(MESSAGE_VALIDATE_SCRIPT_ERR.format(count=len(issues)))
                return StatusResult(code=SS__CONFIG__INVALID)
        if cmd == CMD_SAVE and len(tokens) >= COUNT_TWO and tokens[COUNT_ONE].lower() == CMD_ALL:
            prompt = any(token.lower() == CMD_PROMPT for token in tokens[COUNT_TWO:])
            return self._save_all(prompt)
        if cmd == CMD_SAVE and len(tokens) >= COUNT_TWO and tokens[COUNT_ONE].lower() == CMD_TESTS:
            return self._coerce_status(self._save_tests_command(tokens))
        if cmd == CMD_TOPOLOGY:
            return self._topology_command(tokens)
        if cmd == CMD_DEBUG:
            if len(tokens) < COUNT_TWO or tokens[COUNT_ONE].lower() != CMD_GRAMMAR:
                print(MESSAGE_DEBUG_GRAMMAR_USAGE)
                return StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX)
            json_output = False
            dot_path = None
            idx = COUNT_TWO
            while idx < len(tokens):
                token = tokens[idx].lower()
                if token == FLAG_JSON:
                    json_output = True
                    idx += COUNT_ONE
                    continue
                if token == FLAG_DOT:
                    if idx + COUNT_ONE >= len(tokens):
                        print(MESSAGE_DEBUG_GRAMMAR_DOT_REQUIRED)
                        return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
                    dot_path = tokens[idx + COUNT_ONE]
                    idx += COUNT_TWO
                    continue
                print(MESSAGE_DEBUG_GRAMMAR_USAGE)
                return StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX)
            payload = self._parser.dump_grammar(self._modes[-1].name)
            if json_output:
                print(self._dump_json(payload, pretty=True))
            else:
                print(MESSAGE_DEBUG_GRAMMAR_HEADER)
                print(self._dump_json(payload, pretty=True))
            if dot_path:
                try:
                    dot_text = self._parser.dump_grammar_dot(self._modes[-1].name)
                    with open(dot_path, FILE_MODE_WRITE, encoding=ENCODING_UTF8) as handle:
                        handle.write(dot_text)
                    print(MESSAGE_DEBUG_GRAMMAR_DOT_SAVED.format(path=dot_path))
                except OSError as exc:
                    print(MESSAGE_DEBUG_GRAMMAR_DOT_FAIL.format(error=exc))
                    return StatusResult(code=SS__EXECUTOR__INTERNAL_ERROR)
            return StatusResult(code=SS__NORMAL)
        if cmd == "show":
            return self._coerce_status(self._handle_show(tokens[1:]))
        print(f"ERROR: Unknown command: {' '.join(tokens)}")
        return StatusResult(code=SS__CLI_PARSER__UNKNOWN_COMMAND)

    def _config_bindings_command(self, tokens: List[str]) -> StatusResult:
        """
        NAME
            _config_bindings_command - Handle bindings subcommands.
        """

        if not self._ensure_bindings_loaded():
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        if len(tokens) == COUNT_ONE:
            return self._coerce_status(self._bindings_show([]))
        sub = tokens[COUNT_ONE].lower()
        if sub == CMD_CLEAR:
            self._bindings_payload = deepcopy(BINDINGS_EMPTY_PAYLOAD)
            self._mark_bindings_dirty()
            self._sync_store_bindings()
            return StatusResult(code=SS__NORMAL)
        if sub == CMD_SHOW:
            return self._coerce_status(self._bindings_show(tokens[COUNT_TWO:]))
        if sub == CMD_CONTROLLER:
            return self._coerce_status(self._bindings_controller_command(tokens[COUNT_TWO:]))
        if sub == CMD_BINDING:
            return self._coerce_status(self._bindings_binding_command(tokens[COUNT_TWO:]))
        if sub == CMD_LOAD:
            if len(tokens) < COUNT_THREE:
                print(MESSAGE_ERR_BINDINGS_LOAD.format(path=EMPTY_STRING))
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            return self._coerce_status(self._load_bindings_from_path(Path(tokens[COUNT_TWO])))
        if sub == CMD_SAVE:
            if len(tokens) < COUNT_THREE:
                print(MESSAGE_ERR_BINDINGS_WRITE.format(path=EMPTY_STRING, error=EMPTY_STRING))
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            return self._coerce_status(self._save_bindings_to_path(Path(tokens[COUNT_TWO])))
        if sub == CMD_VALIDATE:
            path = Path(tokens[COUNT_TWO]) if len(tokens) >= COUNT_THREE else None
            return self._coerce_status(self._bindings_validate(path))
        if sub == CMD_NO and len(tokens) >= COUNT_THREE and tokens[COUNT_TWO].lower() == CMD_CONTROLLER:
            if len(tokens) < COUNT_FOUR:
                print(MESSAGE_ERR_BINDINGS_CONTROLLER_DELETE)
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            return self._coerce_status(self._bindings_delete_controller(tokens[COUNT_THREE]))
        print(MESSAGE_ERR_BINDINGS_SUBCOMMAND)
        return StatusResult(code=SS__CLI_PARSER__UNKNOWN_COMMAND)

    def _config_can_mappings_command(self, tokens: List[str]) -> StatusResult:
        """
        NAME
            _config_can_mappings_command - Handle CAN mappings subcommands.
        """

        if not self._ensure_can_mappings_loaded():
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        if len(tokens) == COUNT_ONE:
            return self._coerce_status(self._mappings_show([]))
        sub = tokens[COUNT_ONE].lower()
        if sub == CMD_CLEAR:
            self._can_mappings = {
                KEY_MANUFACTURERS: {},
                KEY_DEVICE_TYPES: {},
            }
            self._mark_mappings_dirty()
            self._sync_store_mappings()
            return StatusResult(code=SS__NORMAL)
        if sub == CMD_SHOW:
            return self._coerce_status(self._mappings_show(tokens[COUNT_TWO:]))
        if sub == CMD_MANUFACTURER:
            return self._coerce_status(self._mappings_entry_command(KEY_MANUFACTURERS, tokens[COUNT_TWO:]))
        if sub == CMD_DEVICE_TYPE_NAME:
            return self._coerce_status(self._mappings_entry_command(KEY_DEVICE_TYPES, tokens[COUNT_TWO:]))
        if sub == CMD_LOAD:
            if len(tokens) < COUNT_THREE:
                print(MESSAGE_ERR_MAPPINGS_LOAD.format(path=EMPTY_STRING))
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            return self._coerce_status(self._load_can_mappings_from_path(Path(tokens[COUNT_TWO])))
        if sub == CMD_SAVE:
            if len(tokens) < COUNT_THREE:
                print(MESSAGE_ERR_MAPPINGS_WRITE.format(path=EMPTY_STRING, error=EMPTY_STRING))
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            return self._coerce_status(self._save_can_mappings_to_path(Path(tokens[COUNT_TWO])))
        if sub == CMD_VALIDATE:
            path = Path(tokens[COUNT_TWO]) if len(tokens) >= COUNT_THREE else None
            return self._coerce_status(self._mappings_validate(path))
        print(MESSAGE_ERR_MAPPINGS_SUBCOMMAND)
        return StatusResult(code=SS__CLI_PARSER__UNKNOWN_COMMAND)

    def _group_command(self, tokens: List[str]) -> StatusResult:
        group = self._modes[-1].group
        cmd = tokens[0].lower()
        if cmd == CMD_BIND and len(tokens) >= COUNT_TWO:
            action = tokens[COUNT_ONE].lower()
            if action in (CMD_LIST, CMD_EXPLAIN, CMD_TEST):
                return self._coerce_status(self._handle_group_bind_diagnostics(group, tokens))
        if not self._session.is_connected():
            return self._coerce_status(self._group_command_local(tokens, group))
        if cmd == "show":
            if not self._validate_pretty_flag(tokens):
                return StatusResult(code=SS__CLI_PARSER__INVALID_FLAG)
            if len(tokens) == 1:
                seq = show_group(self._session, group, json_output=self._has_json(tokens))
                event = self._wait_for_seq(seq)
                if self._event_failed(event, "show group"):
                    return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
                return StatusResult(code=SS__NORMAL)
            if tokens[1].lower() == "members":
                seq = show_group(self._session, group, json_output=self._has_json(tokens))
                event = self._wait_for_seq(seq)
                if self._event_failed(event, "show group"):
                    return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
                return StatusResult(code=SS__NORMAL)
            if tokens[1].lower() == "binding":
                seq = show_group(self._session, group, json_output=self._has_json(tokens))
                event = self._wait_for_seq(seq)
                if self._event_failed(event, "show group"):
                    return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
                return StatusResult(code=SS__NORMAL)
            return self._coerce_status(self._handle_show(tokens[1:]))
        if cmd == "add" and len(tokens) >= 3 and tokens[1].lower() == "device":
            blocked = self._guard_runtime_active_group_edit(group)
            if blocked is not None:
                return blocked
            device_label = self._normalize_device_label_input(tokens[2])
            if not self._local_device_exists(device_label):
                print("ERROR: Device not defined in local config. Use device <device> to create it.")
                return StatusResult(code=SS__DEVICE__NOT_DEFINED)
            seq = group_add_device(
                self._session, group, device_label, self._conflict_policy, force_move=False
            )
            event = self._wait_for_seq(seq)
            if self._handle_add_device_conflict(event, group, device_label):
                return StatusResult(code=SS__GROUP__BINDING_INVALID)
            if self._event_failed(event, "member assign"):
                return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
            return StatusResult(code=SS__NORMAL)
        if cmd == "no" and len(tokens) >= 3 and tokens[1].lower() == "device":
            blocked = self._guard_runtime_active_group_edit(group)
            if blocked is not None:
                return blocked
            seq = group_remove_device(self._session, group, tokens[2])
            event = self._wait_for_seq(seq)
            if self._event_failed(event, "member remove"):
                return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
            return StatusResult(code=SS__NORMAL)
        if cmd == "member" and len(tokens) >= 3:
            blocked = self._guard_runtime_active_group_edit(group)
            if blocked is not None:
                return blocked
            action = tokens[2].lower()
            if action == "enable":
                seq = group_member_enable(self._session, group, tokens[1])
            elif action == "disable":
                seq = group_member_disable(self._session, group, tokens[1])
            elif action == "toggle":
                seq = group_member_toggle(self._session, group, tokens[1])
            else:
                print("ERROR: member requires enable/disable/toggle.")
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            event = self._wait_for_seq(seq)
            if self._event_failed(event, "member"):
                return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
            return StatusResult(code=SS__NORMAL)
        if cmd == "bind" and len(tokens) >= 3:
            input_name = tokens[1]
            kind = tokens[2].lower()
            value = None
            if kind != "analog":
                if len(tokens) < 4:
                    print("ERROR: binding requires value.")
                    return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
                try:
                    value = float(tokens[3])
                except ValueError:
                    print("ERROR: binding value must be numeric.")
                    return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            seq = group_bind(self._session, group, input_name, kind, value=value)
            event = self._wait_for_seq(seq)
            if self._event_failed(event, "bind"):
                return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
            return StatusResult(code=SS__NORMAL)
        if cmd == "no" and len(tokens) >= 2 and tokens[1].lower() == "bind":
            seq = group_unbind(self._session, group)
            event = self._wait_for_seq(seq)
            if self._event_failed(event, "no bind"):
                return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
            return StatusResult(code=SS__NORMAL)
        if cmd == "enable":
            seq = group_enable(self._session, group)
            event = self._wait_for_seq(seq)
            if self._event_failed(event, "enable"):
                return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
            return StatusResult(code=SS__NORMAL)
        if cmd == "disable":
            seq = group_disable(self._session, group)
            event = self._wait_for_seq(seq)
            if self._event_failed(event, "disable"):
                return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
            return StatusResult(code=SS__NORMAL)
        if cmd == "run" and len(tokens) >= 2 and tokens[1].lower() == "test":
            name = tokens[2] if len(tokens) >= 3 else None
            seq = group_run_test(self._session, group, name)
            event = self._wait_for_seq(seq)
            if self._event_failed(event, "run test"):
                return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
            return StatusResult(code=SS__NORMAL)
        print(f"ERROR: Unknown command: {' '.join(tokens)}")
        return StatusResult(code=SS__CLI_PARSER__UNKNOWN_COMMAND)

    def _device_command(self, tokens: List[str]) -> StatusResult:
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
                return self._coerce_status(self._show_local_device_entry(device))
            return self._coerce_status(self._handle_show(tokens[1:]))
        if cmd == "set" and len(tokens) >= 3:
            field = tokens[1]
            value_raw = " ".join(tokens[2:])
            result = self._set_local_device_meta(device, field, value_raw)
            if not result.ok():
                return result
            print(f"Updated device {device} {field}={value_raw}.")
            return StatusResult(code=SS__NORMAL)
        if cmd == "no" and len(tokens) >= 2:
            field = tokens[1]
            result = self._clear_local_device_meta(device, field)
            if not result.ok():
                return result
            print(f"Cleared device {device} {field}.")
            return StatusResult(code=SS__NORMAL)
        if cmd in ("delete", "remove") or (
            cmd == "no" and len(tokens) >= 2 and tokens[1].lower() == "device"
        ):
            if not self._confirm(f"Delete device '{device}'?"):
                return StatusResult(code=SS__EXECUTOR__CANCELLED)
            result = self._delete_local_device(device)
            if not result.ok():
                return result
            print(f"Deleted device {device}.")
            self._pop_mode()
            return StatusResult(code=SS__NORMAL)
        print(f"ERROR: Unknown command: {' '.join(tokens)}")
        return StatusResult(code=SS__CLI_PARSER__UNKNOWN_COMMAND)

    def _handle_show(self, tokens: List[str]) -> StatusResult:
        if not tokens:
            print(MESSAGE_ERR_SHOW_REQUIRES_TARGET)
            return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
        has_source_flag = any(token.lower() in SHOW_SOURCE_FLAGS for token in tokens)
        source, tokens, json_output, pretty, grouped, ok = self._parse_show_flags(tokens)
        if not ok:
            return StatusResult(code=SS__CLI_PARSER__INVALID_FLAG)
        if not tokens:
            print(MESSAGE_ERR_SHOW_REQUIRES_TARGET)
            return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
        target = tokens[0].lower()
        if target == SHOW_TARGET_CONFIG and len(tokens) >= 2:
            name = tokens[1].lower()
            if name == SHOW_CONFIG_LOCAL_RAW:
                target = SHOW_TARGET_CONFIG_RAW
            elif name == SHOW_CONFIG_DIRTY:
                target = SHOW_TARGET_CONFIG_DIRTY
        if target == CMD_DEVICE and len(tokens) >= 3 and tokens[1].lower() == CMD_REGISTRY:
            print(MESSAGE_ERR_SHOW_DEVICE_REGISTRY_REMOVED)
            return StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX)
        if target == SHOW_TARGET_CONFIG:
            target = SHOW_TARGET_RUNTIME
        if target == SHOW_TARGET_LIFECYCLE:
            if has_source_flag and source != SHOW_SOURCE_ROBOT:
                print(MESSAGE_ERR_SHOW_LIFECYCLE_ROBOT_ONLY)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            source = SHOW_SOURCE_ROBOT
        if target == SHOW_TARGET_SAFETY_LATCH:
            source = SHOW_SOURCE_ROBOT
        if target == SHOW_TARGET_MESSAGE_LEVEL:
            source = SHOW_SOURCE_LOCAL
        if target == SHOW_TARGET_DEVICE_USAGE:
            source = SHOW_SOURCE_LOCAL
        if target == SHOW_TARGET_DEVICE:
            source = SHOW_SOURCE_LOCAL
        if target in (SHOW_TARGET_SIGNALS, SHOW_TARGET_SIGNAL):
            source = SHOW_SOURCE_LOCAL
        if target == SHOW_TARGET_BINDINGS and len(tokens) >= COUNT_TWO:
            sub_target = tokens[COUNT_ONE].lower()
            if sub_target in BINDINGS_SHOW_TARGETS:
                source = SHOW_SOURCE_LOCAL
        if target == SHOW_TARGET_CAN_MAPPINGS:
            source = SHOW_SOURCE_LOCAL
        if target in (SHOW_TARGET_COMMANDS, SHOW_TARGET_HELP):
            source = SHOW_SOURCE_LOCAL
        if target in (SHOW_TARGET_WORKSPACE, SHOW_TARGET_CONTROLLERS):
            source = SHOW_SOURCE_LOCAL
        if (
            has_source_flag
            and target in LOCAL_ONLY_SHOW_TARGETS
            and source != SHOW_SOURCE_LOCAL
        ):
            print(MESSAGE_ERR_SHOW_LOCAL_ONLY.format(target=target))
            return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
        if target == SHOW_TARGET_SOURCES and not has_source_flag:
            source = SHOW_SOURCE_LOCAL
        if target in (SHOW_TARGET_CONFIG_RAW, SHOW_TARGET_CONFIG_DIRTY):
            source = SHOW_SOURCE_LOCAL
        if target == SHOW_TARGET_BINDINGS and len(tokens) >= COUNT_TWO:
            sub_target = tokens[COUNT_ONE].lower()
            if sub_target in BINDINGS_SHOW_TARGETS:
                result = self._bindings_show(tokens[COUNT_ONE:])
                if not result.ok():
                    return result
                return StatusResult(code=SS__NORMAL)
        if source == SHOW_SOURCE_BOTH:
            local_result = self._show_local(target, tokens, json_output, pretty, grouped)
            robot_result = self._show_robot(target, tokens, json_output, pretty)
            if self._batch and (not local_result.ok() or not robot_result.ok()):
                return StatusResult(code=SS__EXECUTOR__FAILED)
            if not local_result.ok():
                return local_result
            if not robot_result.ok():
                return robot_result
            return StatusResult(code=SS__NORMAL)
        if source == SHOW_SOURCE_LOCAL:
            result = self._show_local(target, tokens, json_output, pretty, grouped)
            if not result.ok():
                return result
            return StatusResult(code=SS__NORMAL)
        if source == SHOW_SOURCE_ROBOT:
            result = self._show_robot(target, tokens, json_output, pretty)
            if not result.ok():
                return result
            return StatusResult(code=SS__NORMAL)
        print(MESSAGE_ERR_UNKNOWN_SHOW_SOURCE)
        print(MESSAGE_HINT_PREFIX + MESSAGE_HINT_SHOW)
        return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)

    def _apply_config_plan(self, plan: ConfigPlan, prompt_on_replace: bool = True) -> StatusResult:
        """
        NAME
            _apply_config_plan - Execute commands from a merge/import plan.
        """
        if not plan.ok:
            print(MESSAGE_ERR_PLAN.format(message=plan.message))
            return StatusResult(code=SS__CONFIG__INVALID)
        if plan.root_payload is None and self._local_root_payload is None:
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        incoming_hash = self._profiles_hash(plan.root_payload)
        if not plan.replace and incoming_hash:
            if self._local_root_hash is None and self._local_group_count() > COUNT_ZERO:
                print(MESSAGE_ERR_PROFILE_MISSING_HASH)
                return StatusResult(code=SS__CONFIG__INVALID)
            if self._local_root_hash and incoming_hash != self._local_root_hash:
                print(
                    MESSAGE_ERR_PROFILE_HASH.format(
                        local=self._local_root_hash,
                        incoming=incoming_hash,
                    )
                )
                return StatusResult(code=SS__CONFIG__INVALID)
        if plan.replace:
            if prompt_on_replace and not self._batch and self._session.is_connected():
                if not self._confirm("Replace existing groups?"):
                    print("Import cancelled.")
                    return StatusResult(code=SS__EXECUTOR__CANCELLED)
            if self._session.is_connected():
                result = self._clear_existing_groups()
                if not result.ok():
                    return result
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
            if plan.replace:
                return StatusResult(code=SS__CONFIG__MERGED)
            return StatusResult(code=SS__CONFIG__IMPORTED)
        for command in plan.commands:
            result = self._execute_command(command)
            if not result.ok():
                return result
        if plan.replace:
            return StatusResult(code=SS__CONFIG__MERGED)
        return StatusResult(code=SS__CONFIG__IMPORTED)

    def _read_registry_raw(self, path: str) -> tuple[bool, str, str, Optional[Dict[str, object]]]:
        """
        NAME
            _read_registry_raw - Load raw registry JSON and parse payload.
        """
        if not path:
            return (False, MESSAGE_ERR_PROFILES_PUSH_PATH, EMPTY_STRING, None)
        source_path = Path(path)
        try:
            raw = source_path.read_text(encoding=ENCODING_UTF8)
        except Exception:
            return (False, MESSAGE_ERR_PROFILES_PUSH_READ.format(path=path), EMPTY_STRING, None)
        try:
            payload = json.loads(raw)
        except Exception as exc:
            return (False, MESSAGE_ERR_PROFILES_PUSH_PARSE.format(detail=exc), raw, None)
        if not isinstance(payload, dict):
            return (False, MESSAGE_ERR_PROFILES_PUSH_PARSE.format(detail=MESSAGE_ERR_PROFILES_PUSH_PARSE_ROOT), raw, None)
        return (True, EMPTY_STRING, raw, payload)

    def _hash_raw_registry(self, raw: str) -> str:
        """
        NAME
            _hash_raw_registry - Compute SHA-256 for raw registry JSON.
        """
        digest = hashlib.sha256(raw.encode(ENCODING_UTF8))
        return digest.hexdigest()

    def _validate_registry_payload(
        self,
        payload: Dict[str, object],
        activate_profile: str,
    ) -> tuple[bool, str]:
        """
        NAME
            _validate_registry_payload - Validate bringup_system.json payload.
        """
        schema_version = payload.get(KEY_SCHEMA_VERSION)
        if schema_version != PROFILE_SCHEMA_VERSION:
            return (
                False,
                MESSAGE_VALIDATE_SCHEMA_VERSION.format(expected=PROFILE_SCHEMA_VERSION, found=schema_version),
            )
        data_version = payload.get(KEY_DATA_VERSION)
        if not isinstance(data_version, str) or not data_version.strip():
            return (False, MESSAGE_VALIDATE_DATA_VERSION)
        data_hash = payload.get(KEY_DATA_HASH)
        if not isinstance(data_hash, str) or not data_hash.strip():
            return (False, MESSAGE_VALIDATE_DATA_HASH)
        computed_hash = compute_profiles_hash(payload)
        if data_hash != computed_hash:
            return (False, MESSAGE_VALIDATE_DATA_HASH_MISMATCH)
        devices_raw = payload.get(KEY_DEVICES)
        if not isinstance(devices_raw, list) or not devices_raw:
            return (False, MESSAGE_VALIDATE_DEVICES_MISSING)
        registry: Dict[str, Dict[str, object]] = {}
        for entry in devices_raw:
            if not isinstance(entry, dict):
                continue
            label = str(entry.get(KEY_LABEL, EMPTY_STRING)).strip()
            if not label:
                return (False, MESSAGE_VALIDATE_DEVICE_LABEL_MISSING)
            key = label.lower()
            if key in registry:
                return (False, MESSAGE_VALIDATE_DEVICE_LABEL_DUP.format(label=label))
            registry[key] = entry
        profiles = payload.get(KEY_PROFILES)
        if not isinstance(profiles, dict) or not profiles:
            return (False, MESSAGE_VALIDATE_PROFILES_EMPTY)
        for profile_name, entry in profiles.items():
            if not isinstance(entry, dict):
                continue
            labels = entry.get(KEY_PROFILE_DEVICES)
            if labels is None:
                return (
                    False,
                    MESSAGE_VALIDATE_PROFILE_DEVICES_MISSING.format(profile=profile_name),
                )
            if not isinstance(labels, list):
                return (
                    False,
                    MESSAGE_VALIDATE_PROFILE_DEVICES_MISSING.format(profile=profile_name),
                )
            seen: set[str] = set()
            for label in labels:
                name = str(label).strip()
                if not name:
                    continue
                key = name.lower()
                if key in seen:
                    return (
                        False,
                        MESSAGE_VALIDATE_PROFILE_DEVICE_DUP.format(
                            profile=profile_name, label=name
                        ),
                    )
                seen.add(key)
                if key not in registry:
                    return (
                        False,
                        MESSAGE_VALIDATE_PROFILE_DEVICE_UNKNOWN.format(
                            profile=profile_name, label=name
                        ),
                    )
        if activate_profile:
            if activate_profile not in profiles:
                return (
                    False,
                    MESSAGE_VALIDATE_ACTIVATE_PROFILE_UNKNOWN.format(profile=activate_profile),
                )
        return (True, EMPTY_STRING)

    def _backup_root(self) -> Path:
        """
        NAME
            _backup_root - Return the base directory for snapshots/audit logs.
        """
        return Path(repo_root()) / BACKUP_DIR_PARENT / BACKUP_DIR_NAME

    def _ensure_backup_root(self) -> Path:
        """
        NAME
            _ensure_backup_root - Ensure the backup root directory exists.
        """
        root = self._backup_root()
        try:
            root.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            self._warn(MESSAGE_SNAPSHOT_FAILED.format(path=root, error=exc))
        return root

    def _snapshot_timestamp(self) -> str:
        """
        NAME
            _snapshot_timestamp - Format timestamps for snapshot/audit entries.
        """
        return time.strftime(SNAPSHOT_TIMESTAMP_FORMAT, time.localtime(time.time()))

    def _snapshot_paths(self, path: Path, stamp: str) -> tuple[Path, Path]:
        """
        NAME
            _snapshot_paths - Build snapshot and last_good paths for a file.
        """
        root = self._ensure_backup_root()
        stem = path.stem
        suffix = path.suffix
        snapshot_name = f"{stem}{SNAPSHOT_DOT}{stamp}{suffix}"
        last_good_name = f"{stem}{SNAPSHOT_DOT}{SNAPSHOT_LAST_GOOD}{suffix}"
        return (root / snapshot_name, root / last_good_name)

    def _snapshot_tag_from_name(self, name: str, stem: str, suffix: str) -> str:
        """
        NAME
            _snapshot_tag_from_name - Extract snapshot tag from a filename.
        """
        prefix = f"{stem}{SNAPSHOT_DOT}"
        if not name.startswith(prefix) or not name.endswith(suffix):
            return EMPTY_STRING
        return name[len(prefix) : len(name) - len(suffix)]

    def _list_snapshots_for_path(self, path: Path) -> tuple[Optional[Path], List[str]]:
        """
        NAME
            _list_snapshots_for_path - List snapshot tags for a source path.
        """
        root = self._backup_root()
        if not root.exists():
            return (None, [])
        stem = path.stem
        suffix = path.suffix
        pattern = f"{stem}{SNAPSHOT_DOT}{SNAPSHOT_GLOB_WILDCARD}{suffix}"
        last_good = root / f"{stem}{SNAPSHOT_DOT}{SNAPSHOT_LAST_GOOD}{suffix}"
        tags: List[str] = []
        for entry in sorted(root.glob(pattern)):
            tag = self._snapshot_tag_from_name(entry.name, stem, suffix)
            if not tag or tag == SNAPSHOT_LAST_GOOD:
                continue
            tags.append(tag)
        return (last_good if last_good.exists() else None, tags)

    def _prune_snapshots(self, path: Path) -> None:
        """
        NAME
            _prune_snapshots - Enforce snapshot retention for a source path.
        """
        root = self._backup_root()
        if not root.exists():
            return
        stem = path.stem
        suffix = path.suffix
        pattern = f"{stem}{SNAPSHOT_DOT}{SNAPSHOT_GLOB_WILDCARD}{suffix}"
        snapshots = [
            entry
            for entry in sorted(root.glob(pattern))
            if SNAPSHOT_LAST_GOOD not in entry.name
        ]
        if len(snapshots) <= SNAPSHOT_RETAIN_COUNT:
            return
        to_remove = snapshots[: len(snapshots) - SNAPSHOT_RETAIN_COUNT]
        for entry in to_remove:
            try:
                entry.unlink()
            except Exception as exc:
                self._warn(MESSAGE_SNAPSHOT_FAILED.format(path=entry, error=exc))

    def _atomic_write_json(
        self,
        path: Path,
        payload: object,
        indent: int,
        trailing_newline: bool,
    ) -> tuple[bool, str]:
        """
        NAME
            _atomic_write_json - Write JSON using a temp file and backup swap.
        """
        temp_path = path.with_name(path.name + BACKUP_SUFFIX_TMP)
        backup_path = path.with_name(path.name + BACKUP_SUFFIX_BAK)
        try:
            write_json(temp_path, payload, indent=indent, trailing_newline=trailing_newline)
        except Exception as exc:
            return (False, str(exc))
        try:
            read_json(temp_path)
        except Exception as exc:
            try:
                temp_path.unlink()
            except Exception:
                pass
            return (False, str(exc))
        try:
            if backup_path.exists():
                backup_path.unlink()
            if path.exists():
                path.replace(backup_path)
            temp_path.replace(path)
        except Exception as exc:
            try:
                if backup_path.exists() and not path.exists():
                    backup_path.replace(path)
            except Exception:
                pass
            return (False, str(exc))
        return (True, EMPTY_STRING)

    def _hash_file(self, path: Path) -> str:
        """
        NAME
            _hash_file - Compute SHA-256 for a file.
        """
        try:
            digest = hashlib.new(HASH_ALGO_SHA256)
            digest.update(path.read_bytes())
            return digest.hexdigest()
        except Exception:
            return EMPTY_STRING

    def _append_audit_log(
        self,
        action: str,
        source: str,
        path: Path,
        validation_ok: bool,
    ) -> None:
        """
        NAME
            _append_audit_log - Append an audit entry to the backup index.
        """
        root = self._ensure_backup_root()
        index_path = root / BACKUP_INDEX_NAME
        entries: List[Dict[str, object]] = []
        if index_path.exists():
            try:
                payload = read_json(index_path)
                if isinstance(payload, dict):
                    loaded = payload.get(KEY_AUDIT_ENTRIES, [])
                    if isinstance(loaded, list):
                        entries = list(loaded)
                elif isinstance(payload, list):
                    entries = list(payload)
            except Exception:
                entries = []
        entry = {
            KEY_AUDIT_TIMESTAMP: self._snapshot_timestamp(),
            KEY_AUDIT_ACTION: action,
            KEY_AUDIT_SOURCE: source,
            KEY_AUDIT_PATH: str(path),
            KEY_AUDIT_HASH: self._hash_file(path),
            KEY_AUDIT_VALID: bool(validation_ok),
        }
        entries.append(entry)
        try:
            write_json(index_path, {KEY_AUDIT_ENTRIES: entries}, indent=JSON_PRETTY_INDENT, trailing_newline=True)
        except Exception as exc:
            self._warn(MESSAGE_AUDIT_WRITE_FAILED.format(path=index_path, error=exc))

    def _write_snapshot(
        self,
        path: Path,
        payload: object,
        validation_ok: bool,
        indent: int,
        trailing_newline: bool,
    ) -> None:
        """
        NAME
            _write_snapshot - Write snapshot and last_good files for a payload.
        """
        stamp = self._snapshot_timestamp()
        snapshot_path, last_good_path = self._snapshot_paths(path, stamp)
        ok, error = self._atomic_write_json(snapshot_path, payload, indent, trailing_newline)
        if ok:
            print(MESSAGE_SNAPSHOT_CREATED.format(path=snapshot_path))
        else:
            self._warn(MESSAGE_SNAPSHOT_FAILED.format(path=snapshot_path, error=error))
        if validation_ok:
            ok, error = self._atomic_write_json(last_good_path, payload, indent, trailing_newline)
            if not ok:
                self._warn(MESSAGE_SNAPSHOT_LAST_GOOD_FAILED.format(path=last_good_path, error=error))
        self._prune_snapshots(path)

    def _post_save(
        self,
        action: str,
        sources: List[str],
        path: Path,
        payload: object,
        validation_ok: bool,
        indent: int,
        trailing_newline: bool,
    ) -> None:
        """
        NAME
            _post_save - Record snapshots and audit entries after saving.
        """
        self._write_snapshot(path, payload, validation_ok, indent, trailing_newline)
        for source in sources:
            self._append_audit_log(action, source, path, validation_ok)

    def _print_validation_results(self, results: List[tuple[str, bool, str]]) -> int:
        """
        NAME
            _print_validation_results - Emit validate-all style output.
        """
        print(MESSAGE_VALIDATE_ALL_HEADER)
        for label, item_ok, message in results:
            if item_ok:
                print(MESSAGE_VALIDATE_ALL_ITEM_OK.format(label=label))
            else:
                print(MESSAGE_VALIDATE_ALL_ITEM_ERR.format(label=label, message=message))
        failures = [item for item in results if not item[COUNT_ONE]]
        if failures:
            print(MESSAGE_VALIDATE_ALL_SUMMARY_ERR.format(count=len(failures)))
        else:
            print(MESSAGE_VALIDATE_ALL_SUMMARY_OK)
        return len(failures)

    def _guard_save(self, force: bool) -> tuple[bool, bool]:
        """
        NAME
            _guard_save - Validate before save with optional force override.
        """
        ok, results = self.validate_all()
        if ok:
            return (True, True)
        self._print_validation_results(results)
        if not force:
            print(MESSAGE_SAVE_BLOCKED)
            print(MESSAGE_SAVE_FORCE_HINT)
            return (False, False)
        print(MESSAGE_SAVE_FORCED)
        return (True, False)

    def _strip_flags(self, tokens: List[str], flags: List[str]) -> tuple[List[str], List[str]]:
        """
        NAME
            _strip_flags - Remove recognized flags from tokens.
        """
        cleaned: List[str] = []
        seen: List[str] = []
        for token in tokens:
            lowered = token.lower()
            if lowered in flags:
                seen.append(lowered)
                continue
            cleaned.append(token)
        return (cleaned, seen)

    def _flag_present(self, tokens: List[str], flag: str) -> bool:
        """
        NAME
            _flag_present - Check if a flag appears in tokens.
        """
        return any(token.lower() == flag for token in tokens)

    def _profiles_push(self, path: str, activate_profile: str) -> StatusResult:
        """
        NAME
            _profiles_push - Push registry payload to the robot.
        """
        if not self._session.is_connected():
            return StatusResult(code=SS__NETWORK__NOT_CONNECTED)
        print(MESSAGE_PUSH_STAGE.format(stage="local config loaded", status=MATCH_STATE_YES))
        ok, error, raw, payload = self._read_registry_raw(path)
        if not ok:
            print(MESSAGE_PUSH_STAGE.format(stage="local config loaded", status=MATCH_STATE_NO))
            print(MESSAGE_PUSH_STAGE_DETAIL.format(detail=error))
            print(error)
            return StatusResult(code=SS__CONFIG__INVALID)
        assert payload is not None
        valid, message = self._validate_registry_payload(payload, activate_profile)
        if not valid:
            print(MESSAGE_PUSH_STAGE.format(stage="schema validation", status=MATCH_STATE_NO))
            print(MESSAGE_PUSH_STAGE_DETAIL.format(detail=message))
            print(MESSAGE_ERR_PROFILES_PUSH_VALIDATE.format(detail=message))
            return StatusResult(code=SS__CONFIG__INVALID)
        print(MESSAGE_PUSH_STAGE.format(stage="schema validation", status=MATCH_STATE_YES))
        print(MESSAGE_PUSH_STAGE.format(stage="semantic validation", status=MATCH_STATE_YES))
        registry_hash = self._hash_raw_registry(raw)
        registry_bytes = len(raw.encode(ENCODING_UTF8))
        data_hash = payload.get(KEY_DATA_HASH)
        if not isinstance(data_hash, str):
            data_hash = EMPTY_STRING
        data_version = payload.get(KEY_DATA_VERSION)
        if isinstance(data_version, str) and data_version.strip():
            print(MESSAGE_PUSH_STAGE_DATA_VERSION.format(version=data_version))
        resolved_path = str(Path(path).resolve())
        self._debug_log(
            MESSAGE_DEBUG_REGISTRY_PUSH.format(
                path=resolved_path,
                bytes=registry_bytes,
                sha256=registry_hash,
                data_hash=data_hash,
            )
        )
        args = {
            ARG_REGISTRY_JSON: raw,
            ARG_REGISTRY_HASH: registry_hash,
            ARG_REGISTRY_BYTES: registry_bytes,
        }
        print(MESSAGE_PUSH_STAGE.format(stage="config sent to robot", status=MATCH_STATE_YES))
        seq = self._session.send_command(CMD_PROFILES_APPLY, args)
        if seq is None:
            print(MESSAGE_PUSH_STAGE.format(stage="config sent to robot", status=MATCH_STATE_NO))
            print(MESSAGE_ERR_PROFILES_PUSH_SEND)
            return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
        self._proto_mark_cmd_sent(CMD_PROFILES_APPLY, now=time.time())
        event = self._wait_for_seq(seq, timeout_sec=ROBOT_LONG_COMMAND_TIMEOUT_SEC)
        event_payload = self._parse_event_json_payload(event)
        if event_payload:
            self._print_profiles_apply_stages(event_payload)
        if self._event_failed(event, CMD_PROFILES_APPLY):
            return StatusResult(code=SS__CONFIG__INVALID)
        self._local_root_payload = payload
        self._local_root_path = path
        self._local_root_hash = self._profiles_hash(payload)
        self._local_devices_locked = True
        self._record_last_push(path, registry_hash, activate_profile or self._active_profile_name() or EMPTY_STRING)
        self._sync_store_from_local()
        print(MESSAGE_INFO_PROFILES_PUSH_LOCAL.format(path=path))
        if activate_profile:
            activation_result = self._runtime_activate(activate_profile)
            if not activation_result.ok():
                return activation_result
        return StatusResult(code=SS__NORMAL)

    def _profiles_reload(self) -> StatusResult:
        """
        NAME
            _profiles_reload - Reload profiles on the robot from deploy.
        """
        if not self._session.is_connected():
            return StatusResult(code=SS__NETWORK__NOT_CONNECTED)
        seq = profiles_reload(self._session)
        if seq is None:
            print(MESSAGE_ERR_PROFILES_RELOAD_SEND)
            return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
        self._proto_mark_cmd_sent(CMD_PROFILES_RELOAD, now=time.time())
        event = self._wait_for_seq(seq, timeout_sec=ROBOT_LONG_COMMAND_TIMEOUT_SEC)
        if self._event_failed(event, CMD_PROFILES_RELOAD):
            return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
        print(MESSAGE_INFO_PROFILES_RELOAD)
        return StatusResult(code=SS__NORMAL)

    def _profiles_activate(self, profile_name: str) -> StatusResult:
        """
        NAME
            _profiles_activate - Activate an already-loaded profile on the robot.
        """
        return self._runtime_activate(profile_name)

    def _runtime_command(self, tokens: List[str]) -> StatusResult:
        """
        NAME
            _runtime_command - Dispatch explicit runtime activate/deactivate commands.
        """
        if len(tokens) < COUNT_TWO:
            print(MESSAGE_ERR_RUNTIME_ACTION)
            return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
        action = tokens[COUNT_ONE].lower()
        if action == CMD_ACTIVATE_PROFILE:
            profile_name = tokens[COUNT_TWO] if len(tokens) >= COUNT_THREE else EMPTY_STRING
            return self._runtime_activate(profile_name)
        if action == CMD_DISABLE:
            return self._runtime_deactivate()
        if action == "deactivate":
            return self._runtime_deactivate()
        print(MESSAGE_ERR_RUNTIME_ACTION)
        return StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX)

    def _lifecycle_command(self, tokens: List[str]) -> StatusResult:
        """
        NAME
            _lifecycle_command - Dispatch controlled lifecycle activate/deactivate commands.
        """
        if len(tokens) < COUNT_TWO:
            print(MESSAGE_ERR_LIFECYCLE_ACTION)
            return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
        action = tokens[COUNT_ONE].lower()
        if action == CMD_ACTIVATE_PROFILE:
            if len(tokens) < COUNT_THREE:
                print(MESSAGE_ERR_LIFECYCLE_LABEL)
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            label = tokens[COUNT_TWO]
            mode = "READ_ONLY"
            if len(tokens) > COUNT_THREE:
                if len(tokens) != COUNT_FIVE or tokens[COUNT_THREE].lower() != "mode":
                    print(MESSAGE_ERR_LIFECYCLE_ACTION)
                    return StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX)
                mode = tokens[COUNT_FOUR].strip()
                if not mode:
                    print(MESSAGE_ERR_LIFECYCLE_MODE)
                    return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            return self._lifecycle_activate(label, mode)
        if action == "deactivate":
            if len(tokens) < COUNT_THREE:
                print(MESSAGE_ERR_LIFECYCLE_LABEL)
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            if len(tokens) != COUNT_THREE:
                print(MESSAGE_ERR_LIFECYCLE_ACTION)
                return StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX)
            return self._lifecycle_deactivate(tokens[COUNT_TWO])
        if action == "deactivate-active":
            if len(tokens) != COUNT_TWO:
                print(MESSAGE_ERR_LIFECYCLE_ACTION)
                return StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX)
            return self._lifecycle_deactivate_active()
        print(MESSAGE_ERR_LIFECYCLE_ACTION)
        return StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX)

    def _runtime_activate(self, profile_name: str = EMPTY_STRING) -> StatusResult:
        """
        NAME
            _runtime_activate - Activate the selected or named runtime profile on the robot.
        """
        if not profile_name:
            profile_name = EMPTY_STRING
        if not self._session.is_connected():
            return StatusResult(code=SS__NETWORK__NOT_CONNECTED)
        seq = runtime_activate(self._session, profile_name)
        if seq is None:
            print(MESSAGE_ERR_RUNTIME_ACTIVATE_SEND)
            return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
        self._proto_mark_cmd_sent(CMD_RUNTIME_ACTIVATE, now=time.time())
        event = self._wait_for_seq(seq, timeout_sec=ROBOT_LONG_COMMAND_TIMEOUT_SEC)
        if self._event_failed(event, CMD_RUNTIME_ACTIVATE):
            return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
        return StatusResult(code=SS__NORMAL)

    def _runtime_deactivate(self) -> StatusResult:
        """
        NAME
            _runtime_deactivate - Deactivate the active runtime profile on the robot.
        """
        if not self._session.is_connected():
            return StatusResult(code=SS__NETWORK__NOT_CONNECTED)
        seq = runtime_deactivate(self._session)
        if seq is None:
            print(MESSAGE_ERR_RUNTIME_DEACTIVATE_SEND)
            return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
        self._proto_mark_cmd_sent(CMD_RUNTIME_DEACTIVATE, now=time.time())
        event = self._wait_for_seq(seq, timeout_sec=ROBOT_LONG_COMMAND_TIMEOUT_SEC)
        if self._event_failed(event, CMD_RUNTIME_DEACTIVATE):
            return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
        return StatusResult(code=SS__NORMAL)

    def _lifecycle_activate(self, label: str, mode: str = "READ_ONLY") -> StatusResult:
        """
        NAME
            _lifecycle_activate - Activate the robot controlled lifecycle session for a label.
        """
        if not self._session.is_connected():
            return StatusResult(code=SS__NETWORK__NOT_CONNECTED)
        seq = lifecycle_activate(self._session, label, mode)
        if seq is None:
            print(MESSAGE_ERR_LIFECYCLE_ACTIVATE_SEND)
            return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
        self._proto_mark_cmd_sent(CMD_LIFECYCLE_ACTIVATE, now=time.time())
        event = self._wait_for_seq(seq, timeout_sec=ROBOT_LONG_COMMAND_TIMEOUT_SEC)
        if self._event_failed(event, CMD_LIFECYCLE_ACTIVATE):
            return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
        semantic_error = self._lifecycle_event_error(event)
        if semantic_error:
            return StatusResult(code=SS__EXECUTOR__FAILED, message=semantic_error)
        return StatusResult(code=SS__NORMAL)

    def _lifecycle_deactivate(self, label: str) -> StatusResult:
        """
        NAME
            _lifecycle_deactivate - Deactivate the robot controlled lifecycle session for a label.
        """
        if not self._session.is_connected():
            return StatusResult(code=SS__NETWORK__NOT_CONNECTED)
        seq = lifecycle_deactivate(self._session, label)
        if seq is None:
            print(MESSAGE_ERR_LIFECYCLE_DEACTIVATE_SEND)
            return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
        self._proto_mark_cmd_sent(CMD_LIFECYCLE_DEACTIVATE, now=time.time())
        event = self._wait_for_seq(seq, timeout_sec=ROBOT_LONG_COMMAND_TIMEOUT_SEC)
        if self._event_failed(event, CMD_LIFECYCLE_DEACTIVATE):
            return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
        semantic_error = self._lifecycle_event_error(event)
        if semantic_error:
            return StatusResult(code=SS__EXECUTOR__FAILED, message=semantic_error)
        return StatusResult(code=SS__NORMAL)

    def _lifecycle_deactivate_active(self) -> StatusResult:
        """
        NAME
            _lifecycle_deactivate_active - Deactivate the current robot controlled lifecycle session.
        """
        if not self._session.is_connected():
            return StatusResult(code=SS__NETWORK__NOT_CONNECTED)
        seq = lifecycle_deactivate_active(self._session)
        if seq is None:
            print(MESSAGE_ERR_LIFECYCLE_DEACTIVATE_ACTIVE_SEND)
            return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
        self._proto_mark_cmd_sent(CMD_LIFECYCLE_DEACTIVATE_ACTIVE, now=time.time())
        event = self._wait_for_seq(seq, timeout_sec=ROBOT_LONG_COMMAND_TIMEOUT_SEC)
        if self._event_failed(event, CMD_LIFECYCLE_DEACTIVATE_ACTIVE):
            return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
        semantic_error = self._lifecycle_event_error(event)
        if semantic_error:
            return StatusResult(code=SS__EXECUTOR__FAILED, message=semantic_error)
        return StatusResult(code=SS__NORMAL)

    def _lifecycle_event_error(self, event: Optional[BridgeEvent]) -> str:
        """
        NAME
            _lifecycle_event_error - Extract one semantic lifecycle failure message from a successful transport event.
        """
        if event is None:
            return EMPTY_STRING
        payload = parse_json_arg(getattr(event, "json_text", EMPTY_STRING))
        if isinstance(payload, dict) and payload.get("success") is True:
            return EMPTY_STRING
        if isinstance(payload, dict) and payload.get("success") is False:
            for key in ("errorMessage", "message", "errorCode"):
                value = str(payload.get(key, EMPTY_STRING)).strip()
                if value:
                    return value
        text_value = str(getattr(event, "text", EMPTY_STRING) or EMPTY_STRING).strip()
        if self._is_lifecycle_success_text(text_value):
            return EMPTY_STRING
        if text_value:
            return text_value
        message_value = str(getattr(event, "message", EMPTY_STRING) or EMPTY_STRING).strip()
        if message_value:
            return message_value
        return "Lifecycle command failed."

    def _is_lifecycle_success_text(self, value: str) -> bool:
        """
        NAME
            _is_lifecycle_success_text - Recognize successful lifecycle text payloads for backward-compatible fallback handling.
        """
        if not value:
            return False
        if value.startswith(MESSAGE_LIFECYCLE_ACTIVATED_PREFIX):
            return True
        if value.startswith(MESSAGE_LIFECYCLE_DEACTIVATED_PREFIX):
            return True
        return value == MESSAGE_LIFECYCLE_DEACTIVATED_ACTIVE

    def _config_push(self, path: str, activate_profile: str) -> StatusResult:
        """
        NAME
            _config_push - Push registry then bridgeConfig groups to robot.
        """
        if self._has_dirty_state():
            print(MESSAGE_PUSH_DIRTY_BLOCKED)
            return StatusResult(code=SS__CONFIG__INVALID)
        resolved_profile = activate_profile or self._active_profile_name()
        print(MESSAGE_INFO_CONFIG_PUSH_START.format(path=path))
        plan = import_config(path, self._conflict_policy, resolved_profile)
        if not plan.ok:
            print(MESSAGE_PUSH_STAGE.format(stage="config semantic validation", status=MATCH_STATE_NO))
            print(MESSAGE_PUSH_STAGE_DETAIL.format(detail=plan.message))
            print(plan.message)
            return StatusResult(code=SS__CONFIG__INVALID)
        print(MESSAGE_PUSH_STAGE.format(stage="config semantic validation", status=MATCH_STATE_YES))
        result = self._profiles_push(path, resolved_profile)
        if not result.ok():
            return result
        print(MESSAGE_PUSH_STAGE.format(stage="bridge config applied locally", status=MATCH_STATE_YES))
        return self._apply_config_plan(plan)

    def _clear_existing_groups(self) -> StatusResult:
        """
        NAME
            _clear_existing_groups - Delete all current groups.
        """
        if not self._session.is_connected():
            return self._clear_local_groups()
        groups = self._fetch_group_names()
        if groups is None:
            print("ERROR: Failed to query groups.")
            return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
        if not groups:
            return StatusResult(code=SS__NORMAL)
        for name in groups:
            seq = group_delete(self._session, name, confirm=True)
            self._wait_for_seq(seq)
        return StatusResult(code=SS__NORMAL)

    def _clear_local_groups(self) -> StatusResult:
        """
        NAME
            _clear_local_groups - Clear local groups without touching the robot.
        """
        if not isinstance(self._local_config, dict):
            return StatusResult(code=SS__NORMAL)
        by_profile = self._local_config.get(KEY_BRIDGE_BY_PROFILE)
        if not isinstance(by_profile, dict):
            return StatusResult(code=SS__NORMAL)
        for entry in by_profile.values():
            if isinstance(entry, dict):
                entry[KEY_BRIDGE_GROUPS] = []
        return StatusResult(code=SS__NORMAL)

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

    def _execute_command(self, command: BridgeCommand) -> StatusResult:
        """
        NAME
            _execute_command - Send a BridgeCommand and wait for output.
        """
        return self._execute_facade.execute_command(self._robot_control_transport, command)

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
        timeout_sec: float = ROBOT_COMMAND_TIMEOUT_SEC,
        print_events: bool = True,
        suppress_timeout_warning: bool = False,
    ) -> Optional[BridgeEvent]:
        if seq is None:
            print("ERROR: Command failed to send.")
            return None
        self._tracker.start("cli", None, seq, now=time.time(), retryable=False)
        self._last_seq = seq
        def _on_event(event: BridgeEvent) -> None:
            if print_events:
                self._print_event(event)
            if event.type == EVENT_TYPE_ACK:
                self._proto_mark_ack(event.seq, now=time.time())
            if event.type == EVENT_TYPE_OUT:
                self._proto_mark_out(event.seq, now=time.time())

        result = wait_for_command_event(
            self._session,
            self._tracker,
            seq,
            timeout_sec=timeout_sec,
            on_event=_on_event,
        )
        if result.event is None:
            self._proto_mark_timeout(now=time.time())
            if not suppress_timeout_warning:
                self._debug_log(MESSAGE_WAITING_FOR_OUT)
        return result.event

    def _event_failed(self, event: Optional[BridgeEvent], context: str) -> bool:
        if event is None:
            if self._batch:
                print(f"ERROR: Timeout waiting for {context} output.")
                return True
            return False
        return event.status == "error"

    def _print_event(self, event: BridgeEvent) -> None:
        if event.type == EVENT_TYPE_ACK:
            if event.name == CMD_UI_PING:
                self._proto_mark_keepalive_ack(event.seq, now=time.time())
                return
            if self._last_seq and event.seq != self._last_seq:
                return
            msg = event.message or event.status
            print(f"ACK {event.seq} {event.name} {event.status} {msg}".rstrip())
            return
        if event.type == EVENT_TYPE_OUT:
            if event.name == CMD_UI_PING:
                self._proto_mark_keepalive_out(event.seq, now=time.time())
                return
            source = self._show_label_seq.pop(event.seq, "")
            if source:
                print(f"SOURCE: {source}")
            pretty = self._show_pretty_json_seq.pop(event.seq, False)
            if not pretty and event.seq == self._last_seq and self._last_show_pretty:
                pretty = True
            if not pretty and self._last_line_pretty:
                pretty = True
            if event.text:
                if pretty:
                    try:
                        payload = json.loads(event.text)
                        print(self._dump_json(payload, pretty=True))
                    except json.JSONDecodeError:
                        print(event.text.rstrip())
                else:
                    print(event.text.rstrip())
            elif event.json_text:
                if pretty:
                    try:
                        payload = json.loads(event.json_text)
                        print(self._dump_json(payload, pretty=True))
                    except json.JSONDecodeError:
                        print(event.json_text.rstrip())
                else:
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

    def _confirm_yes_default(self, prompt: str) -> bool:
        """
        NAME
            _confirm_yes_default - Prompt for confirmation with Yes as the default.
        """
        if self._batch:
            return False
        while True:
            resp = input(f"{prompt} [Y/n] ").strip().lower()
            if not resp or resp in ("y", "yes"):
                return True
            if resp in ("n", "no"):
                return False

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

    def _keepalive_log(self, message: str) -> None:
        """
        NAME
            _keepalive_log - Emit keepalive debug logging when enabled.
        """
        if self._message_level == MESSAGE_LEVEL_EXPERT:
            return
        print(message)

    def _debug_log(self, message: str) -> None:
        """
        NAME
            _debug_log - Emit debug logging at expert message level.
        """
        if self._message_level != MESSAGE_LEVEL_EXPERT:
            return
        print(message)

    def _proto_mark_connect_attempt(self) -> None:
        self._proto_connect_attempts += COUNT_ONE

    def _proto_mark_connect_failure(self) -> None:
        self._proto_connect_failures += COUNT_ONE

    def _proto_mark_connected(self, now: float) -> None:
        self._proto_connect_successes += COUNT_ONE
        self._proto_last_connect_at = now

    def _proto_mark_disconnected(self, now: float) -> None:
        self._proto_last_disconnect_at = now

    def _proto_mark_tcp_state(self, now: float, connected: bool) -> None:
        if connected:
            self._proto_last_connect_at = now
        else:
            self._proto_last_disconnect_at = now

    def _proto_mark_handshake(self, now: float) -> None:
        self._proto_handshake_count += COUNT_ONE
        self._proto_last_handshake_at = now

    def _proto_mark_cmd_sent(self, name: str, now: float) -> None:
        self._proto_cmd_sent += COUNT_ONE
        self._proto_cmd_last = name
        self._proto_cmd_last_at = now

    def _proto_mark_ack(self, seq: int, now: float) -> None:
        self._proto_ack_count += COUNT_ONE
        self._proto_last_ack_seq = seq
        self._proto_last_ack_at = now

    def _proto_mark_out(self, seq: int, now: float) -> None:
        self._proto_out_count += COUNT_ONE
        self._proto_last_out_seq = seq
        self._proto_last_out_at = now

    def _proto_mark_timeout(self, now: float) -> None:
        self._proto_timeout_count += COUNT_ONE
        self._proto_last_timeout_at = now

    def _proto_mark_keepalive_sent(self, seq: int, now: float, ok: bool) -> None:
        if ok:
            self._proto_keepalive_sent += COUNT_ONE
            self._proto_keepalive_last_sent_at = now
        else:
            self._proto_keepalive_fail += COUNT_ONE

    def _proto_mark_keepalive_ack(self, seq: int, now: float) -> None:
        self._proto_keepalive_ack += COUNT_ONE
        self._proto_keepalive_last_ack_at = now

    def _proto_mark_keepalive_out(self, seq: int, now: float) -> None:
        self._proto_keepalive_out += COUNT_ONE
        self._proto_keepalive_last_out_at = now

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
        if self._batch:
            return
        if self._modes[-1].name == "exec":
            return
        dirty = {name: flag for name, flag in self._dirty_state().items() if flag}
        if not dirty:
            self._clear_tip("unsaved")
            return
        items = ", ".join(sorted(dirty.keys()))
        self._warn(f"WARNING: Unsaved changes in: {items}.", essential=True)
        self._tip("unsaved", MESSAGE_TIP_UNSAVED)

    def _show_message_level(self, json_output: bool, pretty: bool) -> bool:
        if json_output:
            print(self._dump_json({"messageLevel": self._message_level}, pretty))
        else:
            print(MESSAGE_MESSAGE_LEVEL.format(level=self._message_level))
        return True

    def _show_workspace(self, json_output: bool, pretty: bool) -> StatusResult:
        profiles_path = str(self._local_root_path) if self._local_root_path else EMPTY_STRING
        tests_path = profiles_path
        bindings_path = str(self._bindings_path) if self._bindings_path else EMPTY_STRING
        mappings_path = str(self._can_mappings_path) if self._can_mappings_path else EMPTY_STRING
        dirty = self._current_dirty_flags()
        model = self._tests_model
        default_set = model.default_test_set if model else EMPTY_STRING
        test_count = 0
        if model:
            for test_set in model.test_sets.values():
                test_count += len(test_set.tests)
        tests_empty = bool(model is not None and test_count == 0)
        tests_payload = model_to_payload(model) if model is not None else {}
        available_tests = collect_available_tests(tests_payload if isinstance(tests_payload, dict) else {})
        test_selected = bool(self._tests_active_set and available_tests)
        has_unsaved = any(bool(flag) for flag in dirty.values())
        state = self._session.get_state_snapshot()
        session_id = self._session.session_id() or EMPTY_STRING
        nt_session_id = EMPTY_STRING
        robot_enabled = False
        robot_estopped = False
        if isinstance(state, dict):
            nt_session_id = str(state.get(NT_STATE_SESSION_ID, EMPTY_STRING))
            robot_enabled = bool(state.get(NT_STATE_ENABLED, False))
            robot_estopped = bool(state.get(NT_STATE_ESTOPPED, False))
        session_mismatch = bool(session_id) and bool(nt_session_id) and session_id != nt_session_id
        workflow = self._workflow01.assess(
            config_loaded=bool(self._local_root_payload),
            profile_selected=bool(self._active_profile_name()),
            robot_connected=bool(self._session.is_connected()),
            test_selected=test_selected,
            handshake_done=bool(self._session.handshake_done()),
            session_mismatch=session_mismatch,
            robot_enabled=robot_enabled,
            robot_estopped=robot_estopped,
            has_unsaved_changes=has_unsaved,
        )
        diagnostics_rows = normalize_device_attachments(
            self._local_root_payload if isinstance(self._local_root_payload, dict) else {}
        )
        diagnostics_summary = summarize_attachment_metrics(diagnostics_rows)
        payload = {
            "profiles": {
                "path": profiles_path,
                "loaded": bool(self._local_root_payload),
                "activeProfile": self._active_profile_name() or EMPTY_STRING,
                "dirty": bool(dirty.get(DIRTY_PROFILES, False)),
                "recoveryMode": bool(self._recovery_mode),
                "loadWarnings": list(self._warnings),
            },
            "tests": {
                "path": tests_path,
                "loaded": bool(model is not None),
                "activeSet": self._tests_active_set or EMPTY_STRING,
                "defaultSet": default_set,
                "dirty": bool(dirty.get(DIRTY_TESTS, False)),
                "testCount": test_count,
                "empty": tests_empty,
                KEY_TEST_SELECTED: test_selected,
                KEY_TEST_OVERVIEW: {
                    "available": len(available_tests),
                },
            },
            "bindings": {
                "path": bindings_path,
                "loaded": bool(self._bindings_payload),
                "dirty": bool(dirty.get(DIRTY_BINDINGS, False)),
            },
            "mappings": {
                "path": mappings_path,
                "loaded": bool(self._can_mappings),
                "dirty": bool(dirty.get(DIRTY_MAPPINGS, False)),
            },
            "cli": {
                "messageLevel": self._message_level,
                "echo": bool(self._echo_enabled),
            },
            KEY_PROVENANCE: self._build_provenance_payload(),
            KEY_WORKFLOW01: {
                KEY_STATE: workflow.state,
                KEY_BLOCKING_REASONS: list(workflow.blocking_reasons),
                KEY_NEXT_STEPS: list(workflow.next_steps),
            },
            "diagnostics": diagnostics_summary,
        }
        payload[PROTO_KEY_PROTOCOL] = {
            PROTO_KEY_TCP: {
                PROTO_KEY_CONNECTED: bool(self._session.is_connected()),
                PROTO_KEY_CONNECT_ATTEMPTS: self._proto_connect_attempts,
                PROTO_KEY_CONNECT_FAILS: self._proto_connect_failures,
                PROTO_KEY_CONNECT_SUCCESSES: self._proto_connect_successes,
                PROTO_KEY_LAST_CONNECT_AT: self._proto_last_connect_at,
                PROTO_KEY_LAST_DISCONNECT_AT: self._proto_last_disconnect_at,
            },
            PROTO_KEY_UI: {
                PROTO_KEY_SESSION_ID: session_id,
                PROTO_KEY_HANDSHAKES: self._proto_handshake_count,
                PROTO_KEY_LAST_HANDSHAKE_AT: self._proto_last_handshake_at,
            },
            PROTO_KEY_NT: {
                PROTO_KEY_SESSION_ID: nt_session_id,
                NT_STATE_ENABLED: bool(state.get(NT_STATE_ENABLED, False)) if isinstance(state, dict) else False,
                NT_STATE_ESTOPPED: bool(state.get(NT_STATE_ESTOPPED, False)) if isinstance(state, dict) else False,
                NT_STATE_MODE: str(state.get(NT_STATE_MODE, EMPTY_STRING)) if isinstance(state, dict) else EMPTY_STRING,
                NT_STATE_LAST_ACK_MS: float(state.get(NT_STATE_LAST_ACK_MS, PROTO_TIME_ZERO)) if isinstance(state, dict) else PROTO_TIME_ZERO,
            },
            PROTO_KEY_COMMANDS: {
                PROTO_KEY_COMMANDS_SENT: self._proto_cmd_sent,
                PROTO_KEY_COMMANDS_LAST: self._proto_cmd_last,
                PROTO_KEY_COMMANDS_LAST_AT: self._proto_cmd_last_at,
            },
            PROTO_KEY_ACKS: {
                PROTO_KEY_ACK_COUNT: self._proto_ack_count,
                PROTO_KEY_LAST_ACK_AT: self._proto_last_ack_at,
                PROTO_KEY_LAST_SEQ: self._proto_last_ack_seq,
            },
            PROTO_KEY_OUTS: {
                PROTO_KEY_OUT_COUNT: self._proto_out_count,
                PROTO_KEY_LAST_OUT_AT: self._proto_last_out_at,
                PROTO_KEY_LAST_SEQ: self._proto_last_out_seq,
            },
            PROTO_KEY_TIMEOUTS: {
                PROTO_KEY_TIMEOUT_COUNT: self._proto_timeout_count,
                PROTO_KEY_LAST_TIMEOUT_AT: self._proto_last_timeout_at,
            },
            PROTO_KEY_KEEPALIVE: {
                PROTO_KEY_KEEPALIVE_SENT: self._proto_keepalive_sent,
                PROTO_KEY_KEEPALIVE_FAILED: self._proto_keepalive_fail,
                PROTO_KEY_KEEPALIVE_ACKED: self._proto_keepalive_ack,
                PROTO_KEY_KEEPALIVE_OUT: self._proto_keepalive_out,
                PROTO_KEY_KEEPALIVE_LAST_SENT_AT: self._proto_keepalive_last_sent_at,
                PROTO_KEY_KEEPALIVE_LAST_ACK_AT: self._proto_keepalive_last_ack_at,
                PROTO_KEY_KEEPALIVE_LAST_OUT_AT: self._proto_keepalive_last_out_at,
            },
        }
        if json_output:
            print(self._dump_json(payload, pretty))
            return StatusResult(code=SS__NORMAL)
        print(
            f"Profiles: {profiles_path or '(none)'} "
            f"({'loaded' if payload['profiles']['loaded'] else 'not loaded'})"
        )
        print(f"Active profile: {payload['profiles']['activeProfile'] or '(none)'}")
        tests_loaded = payload["tests"]["loaded"]
        tests_state = "loaded" if tests_loaded else "not loaded"
        if tests_loaded and payload["tests"]["empty"]:
            tests_state += ", empty"
        elif tests_loaded:
            tests_state += f", {payload['tests']['testCount']} tests"
        print(f"Tests: {tests_path or '(none)'} ({tests_state})")
        print(
            f"Active set: {payload['tests']['activeSet'] or '(none)'} "
            f"(default={payload['tests']['defaultSet'] or '(none)'})"
        )
        print(
            f"Bindings: {bindings_path or '(none)'} "
            f"({'loaded' if payload['bindings']['loaded'] else 'not loaded'})"
        )
        print(
            f"Mappings: {mappings_path or '(none)'} "
            f"({'loaded' if payload['mappings']['loaded'] else 'not loaded'})"
        )
        print(
            "Dirty: profiles={profiles} tests={tests} bindings={bindings} mappings={mappings}".format(
                profiles=payload["profiles"]["dirty"],
                tests=payload["tests"]["dirty"],
                bindings=payload["bindings"]["dirty"],
                mappings=payload["mappings"]["dirty"],
            )
        )
        provenance = payload.get(KEY_PROVENANCE, {})
        matches = provenance.get(KEY_MATCH, {}) if isinstance(provenance, dict) else {}
        last_saved = provenance.get(KEY_LAST_SAVED, {}) if isinstance(provenance, dict) else {}
        last_pushed = provenance.get(KEY_LAST_PUSHED, {}) if isinstance(provenance, dict) else {}
        print(TEXT_PROVENANCE_HEADER)
        print(
            TEXT_PROVENANCE_MODIFIED.format(
                value=self._format_provenance_value(provenance.get(KEY_LAST_MODIFIED_AT) if isinstance(provenance, dict) else None)
            )
        )
        print(
            TEXT_PROVENANCE_SAVED.format(
                value=self._format_provenance_value(
                    last_saved.get(KEY_AT) if isinstance(last_saved, dict) else None,
                    path=last_saved.get(KEY_SOURCE_PATH) if isinstance(last_saved, dict) else None,
                    hash_value=last_saved.get(KEY_HASH) if isinstance(last_saved, dict) else None,
                )
            )
        )
        print(
            TEXT_PROVENANCE_PUSHED.format(
                value=self._format_provenance_value(
                    last_pushed.get(KEY_AT) if isinstance(last_pushed, dict) else None,
                    path=last_pushed.get(KEY_SOURCE_PATH) if isinstance(last_pushed, dict) else None,
                    hash_value=last_pushed.get(KEY_HASH) if isinstance(last_pushed, dict) else None,
                    profile_name=last_pushed.get(KEY_PROFILE_NAME) if isinstance(last_pushed, dict) else None,
                )
            )
        )
        print(
            TEXT_PROVENANCE_MATCH.format(
                saved=matches.get(KEY_LOCAL_VS_SAVED, MATCH_STATE_UNKNOWN) if isinstance(matches, dict) else MATCH_STATE_UNKNOWN,
                pushed=matches.get(KEY_LOCAL_VS_PUSHED, MATCH_STATE_UNKNOWN) if isinstance(matches, dict) else MATCH_STATE_UNKNOWN,
                robot=matches.get(KEY_ROBOT_VS_PUSHED, MATCH_STATE_UNKNOWN) if isinstance(matches, dict) else MATCH_STATE_UNKNOWN,
            )
        )
        print(f"CLI: messages={self._message_level} echo={'on' if self._echo_enabled else 'off'}")
        print(f"Recovery mode: {'ON' if self._recovery_mode else 'OFF'}")
        workflow_payload = payload.get(KEY_WORKFLOW01, {})
        print(f"Workflow01: state={workflow_payload.get(KEY_STATE, EMPTY_STRING)}")
        for blocking in workflow_payload.get(KEY_BLOCKING_REASONS, []):
            print(f"  BLOCKED: {blocking}")
        next_steps = workflow_payload.get(KEY_NEXT_STEPS, [])
        if next_steps:
            print("  Next steps:")
            for step in next_steps:
                print(f"    - {step}")
        proto = payload.get(PROTO_KEY_PROTOCOL, {})
        tcp = proto.get(PROTO_KEY_TCP, {}) if isinstance(proto, dict) else {}
        ui = proto.get(PROTO_KEY_UI, {}) if isinstance(proto, dict) else {}
        nt = proto.get(PROTO_KEY_NT, {}) if isinstance(proto, dict) else {}
        cmds = proto.get(PROTO_KEY_COMMANDS, {}) if isinstance(proto, dict) else {}
        acks = proto.get(PROTO_KEY_ACKS, {}) if isinstance(proto, dict) else {}
        outs = proto.get(PROTO_KEY_OUTS, {}) if isinstance(proto, dict) else {}
        timeouts = proto.get(PROTO_KEY_TIMEOUTS, {}) if isinstance(proto, dict) else {}
        keepalive = proto.get(PROTO_KEY_KEEPALIVE, {}) if isinstance(proto, dict) else {}
        print("Protocol:")
        print(
            "  REST: connected={connected} attempts={attempts} ok={ok} fail={fail} "
            "lastConnectAt={last_connect} lastDisconnectAt={last_disconnect}".format(
                connected=tcp.get(PROTO_KEY_CONNECTED, False),
                attempts=tcp.get(PROTO_KEY_CONNECT_ATTEMPTS, COUNT_ZERO),
                ok=tcp.get(PROTO_KEY_CONNECT_SUCCESSES, COUNT_ZERO),
                fail=tcp.get(PROTO_KEY_CONNECT_FAILS, COUNT_ZERO),
                last_connect=tcp.get(PROTO_KEY_LAST_CONNECT_AT, PROTO_TIME_ZERO),
                last_disconnect=tcp.get(PROTO_KEY_LAST_DISCONNECT_AT, PROTO_TIME_ZERO),
            )
        )
        print(
            "  UI: sessionId={session} handshakes={count} lastHandshakeAt={last}".format(
                session=ui.get(PROTO_KEY_SESSION_ID, PROTO_EMPTY_ID),
                count=ui.get(PROTO_KEY_HANDSHAKES, COUNT_ZERO),
                last=ui.get(PROTO_KEY_LAST_HANDSHAKE_AT, PROTO_TIME_ZERO),
            )
        )
        print(
            "  NT: sessionId={session} enabled={enabled} estopped={estopped} mode={mode} lastAckMs={last_ack}".format(
                session=nt.get(PROTO_KEY_SESSION_ID, PROTO_EMPTY_ID),
                enabled=nt.get(NT_STATE_ENABLED, False),
                estopped=nt.get(NT_STATE_ESTOPPED, False),
                mode=nt.get(NT_STATE_MODE, EMPTY_STRING),
                last_ack=nt.get(NT_STATE_LAST_ACK_MS, PROTO_TIME_ZERO),
            )
        )
        print(
            "  Commands: sent={sent} last={last} lastAt={last_at}".format(
                sent=cmds.get(PROTO_KEY_COMMANDS_SENT, COUNT_ZERO),
                last=cmds.get(PROTO_KEY_COMMANDS_LAST, EMPTY_STRING),
                last_at=cmds.get(PROTO_KEY_COMMANDS_LAST_AT, PROTO_TIME_ZERO),
            )
        )
        print(
            "  ACKs: count={count} lastSeq={last_seq} lastAt={last_at}".format(
                count=acks.get(PROTO_KEY_ACK_COUNT, COUNT_ZERO),
                last_seq=acks.get(PROTO_KEY_LAST_SEQ, PROTO_LAST_SEQ_INIT),
                last_at=acks.get(PROTO_KEY_LAST_ACK_AT, PROTO_TIME_ZERO),
            )
        )
        print(
            "  OUTs: count={count} lastSeq={last_seq} lastAt={last_at}".format(
                count=outs.get(PROTO_KEY_OUT_COUNT, COUNT_ZERO),
                last_seq=outs.get(PROTO_KEY_LAST_SEQ, PROTO_LAST_SEQ_INIT),
                last_at=outs.get(PROTO_KEY_LAST_OUT_AT, PROTO_TIME_ZERO),
            )
        )
        print(
            "  Timeouts: count={count} lastAt={last_at}".format(
                count=timeouts.get(PROTO_KEY_TIMEOUT_COUNT, COUNT_ZERO),
                last_at=timeouts.get(PROTO_KEY_LAST_TIMEOUT_AT, PROTO_TIME_ZERO),
            )
        )
        print(
            "  Keepalive: sent={sent} acked={acked} out={out} failed={failed} "
            "lastSentAt={last_sent} lastAckAt={last_ack} lastOutAt={last_out}".format(
                sent=keepalive.get(PROTO_KEY_KEEPALIVE_SENT, COUNT_ZERO),
                acked=keepalive.get(PROTO_KEY_KEEPALIVE_ACKED, COUNT_ZERO),
                out=keepalive.get(PROTO_KEY_KEEPALIVE_OUT, COUNT_ZERO),
                failed=keepalive.get(PROTO_KEY_KEEPALIVE_FAILED, COUNT_ZERO),
                last_sent=keepalive.get(PROTO_KEY_KEEPALIVE_LAST_SENT_AT, PROTO_TIME_ZERO),
                last_ack=keepalive.get(PROTO_KEY_KEEPALIVE_LAST_ACK_AT, PROTO_TIME_ZERO),
                last_out=keepalive.get(PROTO_KEY_KEEPALIVE_LAST_OUT_AT, PROTO_TIME_ZERO),
            )
        )
        if payload["profiles"]["loadWarnings"]:
            print("Warnings:")
            for warning in payload["profiles"]["loadWarnings"]:
                print(f"  {warning}")
        return StatusResult(code=SS__NORMAL)

    def _show_controllers(self, json_output: bool, pretty: bool) -> StatusResult:
        controller_names = sorted(load_controller_names(self._bindings_path))
        inputs = sorted(AXIS_INPUTS | BUTTON_INPUTS)
        declared: List[Dict[str, object]] = []
        if isinstance(self._bindings_payload, dict):
            controllers = self._bindings_payload.get(KEY_CONTROLLERS)
            if isinstance(controllers, list):
                for entry in controllers:
                    if isinstance(entry, dict):
                        declared.append(dict(entry))
        payload = {"controllers": controller_names, "declared": declared, "inputs": inputs}
        if json_output:
            print(self._dump_json(payload, pretty))
            return StatusResult(code=SS__NORMAL)
        print("Controllers:")
        for name in controller_names:
            print(f"  {name}")
        if declared:
            print("Declared controllers:")
            for entry in declared:
                name = entry.get(KEY_NAME)
                ctrl_type = entry.get(FIELD_TYPE)
                port = entry.get(KEY_PORT)
                print(f"  {name} type={ctrl_type} port={port}")
        print("Inputs:")
        print("  " + ", ".join(inputs))
        return StatusResult(code=SS__NORMAL)

    def _show_commands(self, json_output: bool, pretty: bool) -> StatusResult:
        """
        NAME
            _show_commands - Show available commands for the current mode.
        """
        mode = self._modes[-1].name
        commands = sorted(self._parser.expected_suggestions([], mode))
        print(MESSAGE_SOURCE_LOCAL)
        if json_output:
            print(self._dump_json({KEY_COMMANDS: commands}, pretty))
            return StatusResult(code=SS__NORMAL)
        print(MESSAGE_SHOW_COMMANDS_HEADER)
        if not commands:
            print(HELP_INDENT + MESSAGE_HELP_QUICK_EMPTY.strip())
            return StatusResult(code=SS__NORMAL)
        for cmd in commands:
            print(HELP_INDENT + cmd)
        return StatusResult(code=SS__NORMAL)

    def _show_help_topics(self, json_output: bool, pretty: bool) -> StatusResult:
        """
        NAME
            _show_help_topics - Show available help topics.
        """
        topics = sorted(self._help_topics())
        print(MESSAGE_SOURCE_LOCAL)
        if json_output:
            print(self._dump_json({KEY_TOPICS: topics}, pretty))
            return StatusResult(code=SS__NORMAL)
        print(MESSAGE_SHOW_HELP_HEADER)
        if not topics:
            print(HELP_INDENT + MESSAGE_HELP_QUICK_EMPTY.strip())
            return StatusResult(code=SS__NORMAL)
        for topic in topics:
            print(HELP_INDENT + topic)
        return StatusResult(code=SS__NORMAL)

    def _show_device_usage(self, name: str, json_output: bool, pretty: bool) -> StatusResult:
        """
        NAME
            _show_device_usage - Show local group/test references for a device.
        """

        device_name = str(name).strip()
        if not device_name:
            print(MESSAGE_ERR_DEVICE_LABEL_REQUIRED)
            return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
        profile = self._active_profile_name()
        if not profile:
            print(MESSAGE_ERR_PROFILE_REQUIRED)
            return StatusResult(code=SS__CONFIG__PROFILE_REQUIRED)
        target = device_name.lower()
        group_hits: List[str] = []
        group_seen: set[str] = set()
        for group in self._local_groups(profile):
            if not isinstance(group, dict):
                continue
            group_name = str(group.get(KEY_NAME, EMPTY_STRING)).strip()
            if not group_name:
                continue
            members = group.get(KEY_MEMBERS, []) or []
            for member in members:
                member_name = _group_member_label(member)
                if not member_name:
                    continue
                if member_name.lower() == target:
                    group_key = group_name.lower()
                    if group_key not in group_seen:
                        group_seen.add(group_key)
                        group_hits.append(group_name)
                    break
        tests_hits: List[Dict[str, str]] = []
        self._ensure_tests_loaded()
        model = self._tests_model
        if model and isinstance(model.test_sets, dict):
            for test_set_name in sorted(model.test_sets.keys()):
                test_set = model.test_sets.get(test_set_name)
                if not isinstance(test_set, TestSetModel):
                    continue
                for test in test_set.tests:
                    if not isinstance(test, TestModel):
                        continue
                    device_refs = list(test.devices) + list(test.observers)
                    if not device_refs:
                        continue
                    for label in device_refs:
                        if str(label).strip().lower() == target:
                            tests_hits.append(
                                {
                                    KEY_TEST_SET: test_set.name,
                                    KEY_NAME: test.name,
                                    KEY_TYPE: test.test_type,
                                }
                            )
                            break
        group_hits_sorted = sorted(group_hits)
        tests_hits_sorted = sorted(
            tests_hits,
            key=lambda entry: (
                str(entry.get(KEY_TEST_SET, EMPTY_STRING)),
                str(entry.get(KEY_NAME, EMPTY_STRING)),
            ),
        )
        print(MESSAGE_SOURCE_LOCAL)
        if json_output:
            payload = {
                KEY_DEVICE: device_name,
                KEY_PROFILE: profile,
                KEY_GROUPS: group_hits_sorted,
                KEY_TESTS: tests_hits_sorted,
            }
            print(self._dump_json(payload, pretty))
            return StatusResult(code=SS__NORMAL)
        print(MESSAGE_DEVICE_USAGE_HEADER)
        print(MESSAGE_DEVICE_USAGE_DEVICE.format(name=device_name))
        print(MESSAGE_DEVICE_USAGE_PROFILE.format(name=profile))
        print(MESSAGE_DEVICE_USAGE_GROUPS_HEADER)
        if group_hits_sorted:
            for group_name in group_hits_sorted:
                print(MESSAGE_DEVICE_USAGE_GROUP_ENTRY.format(name=group_name))
        else:
            print(MESSAGE_DEVICE_USAGE_NONE)
        print(MESSAGE_DEVICE_USAGE_TESTS_HEADER)
        if tests_hits_sorted:
            for entry in tests_hits_sorted:
                test_set = str(entry.get(KEY_TEST_SET, EMPTY_STRING)).strip()
                test_name = str(entry.get(KEY_NAME, EMPTY_STRING)).strip()
                test_type = str(entry.get(KEY_TYPE, EMPTY_STRING)).strip()
                if test_type:
                    print(
                        MESSAGE_DEVICE_USAGE_TEST_ENTRY.format(
                            test_set=test_set, name=test_name, type=test_type
                        )
                    )
                else:
                    print(
                        MESSAGE_DEVICE_USAGE_TEST_ENTRY_SIMPLE.format(
                            test_set=test_set, name=test_name
                        )
                    )
        else:
            print(MESSAGE_DEVICE_USAGE_NONE)
        return StatusResult(code=SS__NORMAL)

    def _show_profiles_device_all(self, name: str) -> StatusResult:
        """
        NAME
            _show_profiles_device_all - Show all profile device entries for a label.
        """

        label = str(name).strip()
        if not label:
            print(MESSAGE_ERR_DEVICE_LABEL_REQUIRED)
            return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
        payload = self._local_root_payload
        if not isinstance(payload, dict):
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        devices = payload.get(KEY_DEVICES)
        if not isinstance(devices, list):
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        profile_name = self._active_profile_name()
        if not profile_name:
            print(MESSAGE_ERR_PROFILE_REQUIRED)
            return StatusResult(code=SS__CONFIG__PROFILE_REQUIRED)
        profiles = payload.get(KEY_PROFILES)
        if not isinstance(profiles, dict):
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        profile = profiles.get(profile_name)
        if not isinstance(profile, dict):
            print(MESSAGE_ERR_PROFILE_REQUIRED)
            return StatusResult(code=SS__CONFIG__PROFILE_REQUIRED)
        labels = profile.get(KEY_PROFILE_DEVICES)
        if not isinstance(labels, list):
            labels = []
        matches: List[Dict[str, object]] = []
        target = label.lower()
        for entry in devices:
            if not isinstance(entry, dict):
                continue
            entry_label = str(entry.get(FIELD_LABEL, "")).strip()
            if entry_label.lower() == target:
                matches.append(entry)
        profile_counts: Dict[str, int] = {}
        for entry in labels:
            if not isinstance(entry, str):
                continue
            key = entry.strip()
            if not key:
                continue
            if key.lower() == target:
                profile_counts[key] = profile_counts.get(key, 0) + 1
        print(MESSAGE_PROFILE_DEVICE_SHOW_ALL_HEADER)
        if not matches:
            print(MESSAGE_PROFILE_DEVICE_SHOW_ALL_NONE)
        else:
            print(MESSAGE_PROFILE_DEVICE_SHOW_ALL_COUNT.format(count=len(matches)))
            for idx, entry in enumerate(matches, start=1):
                entry_label = str(entry.get(FIELD_LABEL, "")).strip()
                print(MESSAGE_PROFILE_DEVICE_SHOW_ALL_ENTRY.format(index=idx, label=entry_label or label))
                for key in sorted(entry.keys()):
                    print(MESSAGE_PROFILE_DEVICE_SHOW_ALL_FIELD_FMT.format(key=key, value=entry.get(key)))
        print(MESSAGE_PROFILE_DEVICE_SHOW_ALL_PROFILE_HEADER)
        if not profile_counts:
            print(MESSAGE_PROFILE_DEVICE_SHOW_ALL_NONE)
            return StatusResult(code=SS__NORMAL)
        for entry_label in sorted(profile_counts.keys(), key=lambda v: v.lower()):
            print(
                MESSAGE_PROFILE_DEVICE_SHOW_ALL_PROFILE_ENTRY.format(
                    label=entry_label, count=profile_counts[entry_label]
                )
            )
        return StatusResult(code=SS__NORMAL)

    def _diagnose_command(self, tokens: List[str]) -> StatusResult:
        """
        NAME
            _diagnose_command - Diagnose a motor using runtime telemetry.
        """
        if len(tokens) < COUNT_THREE:
            print(MSG_DIAGNOSE_SYNTAX)
            return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
        target = tokens[COUNT_ONE].lower()
        if target not in (CMD_MOTOR, CMD_DEVICE):
            print(MSG_DIAGNOSE_TARGET)
            return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
        label = tokens[COUNT_TWO]
        if not self._session.is_connected():
            print(MSG_RUNTIME_REQUIRED)
            return StatusResult(code=SS__NETWORK__ROBOT_UNAVAILABLE)
        seq = show_runtime_state(self._session, json_output=True)
        event = self._wait_for_seq(seq, print_events=False)
        if event is None or not event.json_text:
            print(MSG_RUNTIME_MISSING)
            return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
        payload = parse_json_arg(event.json_text)
        if not isinstance(payload, dict):
            print(MSG_RUNTIME_MISSING)
            return StatusResult(code=SS__CONFIG__INVALID)
        result = normalize_runtime_state(payload, label)
        if result.telemetry is None:
            if result.candidates:
                print(MSG_DEVICE_AMBIGUOUS)
                print(MSG_DEVICE_CANDIDATES.format(candidates=SEP_COMMA_SPACE.join(result.candidates)))
            else:
                print(MSG_DEVICE_NOT_FOUND)
            return StatusResult(code=SS__DEVICE__NOT_FOUND)
        profile_labels = collect_profile_labels(self._local_root_payload, self._active_profile_name())
        report = diagnose_motor(result.telemetry, profile_labels, result.power_devices)
        self._print_diagnosis(report)
        return StatusResult(code=SS__NORMAL)

    @staticmethod
    def _print_diagnosis(report) -> None:
        """
        NAME
            _print_diagnosis - Print a diagnosis report.
        """
        print(OUT_LIKELY_CAUSES)
        for idx, finding in enumerate(report.causes, start=COUNT_ONE):
            print(
                FMT_CAUSE_LINE.format(
                    index=idx, cause=finding.cause, confidence=finding.confidence
                )
            )
            explanation = CAUSE_EXPLANATIONS.get(finding.cause)
            if explanation:
                print(f"  {explanation}")
            if finding.evidence:
                print(FMT_EVIDENCE_LINE.format(evidence=SEP_COMMA_SPACE.join(finding.evidence)))
        if report.findings:
            print(OUT_FINDINGS)
            for finding in report.findings:
                print(
                    FMT_FINDING_LINE.format(
                        cause=finding.cause, confidence=finding.confidence
                    )
                )
                explanation = CAUSE_EXPLANATIONS.get(finding.cause)
                if explanation:
                    print(f"  {explanation}")
                if finding.evidence:
                    print(
                        FMT_EVIDENCE_LINE.format(
                            evidence=SEP_COMMA_SPACE.join(finding.evidence)
                        )
                    )
        if report.missing:
            print(OUT_MISSING_FIELDS)
            print(FMT_MISSING_LINE.format(fields=SEP_COMMA_SPACE.join(report.missing)))

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
            detail = self._help_topic_map().get(topic)
            if detail:
                print(detail)
            else:
                print("Help: command not found.")
            return
        print(
            "Common: help, exit, end, quit, ping, echo, sleep, messages\n"
            "Exec: show, diagnose, connect, disconnect, configure terminal, instantiate all devices, clear stop-latch, tests\n"
            "Config: profile, group, device, instantiate all devices, clear stop-latch, bindings, can-mappings, tests, no group, selected-device, selected-mode, merge/import/export/save/load\n"
            "Group: show, member assign/remove/enable/disable/toggle, bind, no bind, enable, disable, run test\n"
            "Device: show, set, no\n"
            "Tips: help show | help instantiate all devices | help clear stop-latch | help batch | help json"
        )

    def _help_topic_map(self) -> Dict[str, str]:
        """
        NAME
            _help_topic_map - Build help topic map for the CLI.
        """
        return {
            "show": HELP_SHOW_TEXT,
            "configure terminal": "configure terminal\n  Enter config mode.",
            "connect": "connect\n  Open REST session and perform handshake.",
            "disconnect": "disconnect\n  Close REST session.",
            "instantiate all devices": (
                "instantiate all devices\n"
                "  Instantiate all configured robot devices for the active profile."
            ),
            "instantiate next motor": (
                "instantiate next motor\n"
                "  Instantiate the next configured motor for the active profile."
            ),
            "clear stop-latch": (
                "clear stop-latch\n"
                "  Clear the robot safety stop latch through the runtime command path.\n"
                "clear safety-latch\n"
                "  Alias for clear stop-latch."
            ),
            "clear safety-latch": "clear safety-latch\n  Alias for clear stop-latch.",
            "show safety-latch": (
                "show safety-latch [--json] [--pretty]\n"
                "  Show robot safety latch active state and reason."
            ),
            "tests": (
                "tests select <name>\n"
                "  Select a bringup test on the robot by name.\n"
                "tests toggle\n"
                "  Toggle enabled state of the selected test (robot).\n"
                "tests activate\n"
                "  Activate the selected test's required device scope (robot).\n"
                "tests deactivate\n"
                "  Deactivate the selected test's active device scope (robot).\n"
                "tests run [--wait] [--timeout <seconds>]\n"
                "  Run the selected test once (robot).\n"
                "tests wait [--run <id>] [--timeout <seconds>]\n"
                "  Wait until a robot-side test run reaches a terminal state and print a summary.\n"
                "tests run-all [--wait] [--timeout <seconds>]\n"
                "  Run all enabled tests sequentially (robot)."
            ),
            "tests select": "tests select <name>\n  Select a bringup test on the robot by name.",
            "tests toggle": "tests toggle\n  Toggle enabled state of the selected test (robot).",
            "tests activate": (
                "tests activate\n"
                "  Activate the selected test's required device scope (robot)."
            ),
            "tests deactivate": (
                "tests deactivate\n"
                "  Deactivate the selected test's active device scope (robot)."
            ),
            "tests run": (
                "tests run [--wait] [--timeout <seconds>]\n"
                "  Run the selected test once (robot). Use --wait to print the finished run summary."
            ),
            "tests wait": (
                "tests wait [--run <id>] [--timeout <seconds>]\n"
                "  Poll robot test lifecycle until pass/fail/blocked/aborted and print a finished-run summary."
            ),
            "tests run-all": (
                "tests run-all [--wait] [--timeout <seconds>]\n"
                "  Run all enabled tests sequentially (robot). Use --wait to print the finished summary after run-all settles."
            ),
            "echo": "echo on|off\n  Toggle echo for batch scripts (prints each command).",
            "sleep": "sleep <seconds>\n  Pause batch execution without sending a robot command.",
            "messages": "messages <beginner|medium|expert>\n  Set CLI message level.",
            "tiu": HELP_TIU_TEXT,
            "tiu on": "tiu on\n  Enable the TIU dashboard while keeping normal CLI command entry.",
            "tiu off": "tiu off\n  Disable the TIU dashboard and return to the normal CLI presentation.",
            "debug grammar": "debug grammar [--json] [--dot <path>]\n  Dump the grammar model for the current mode.",
            "show message-level": "show message-level\n  Show current CLI message level.",
            "show workspace": "show workspace\n  Show loaded file paths, active profile/set, dirty flags, and recovery mode.",
            "show controllers": "show controllers\n  List controller names and supported input IDs.",
            "show signals": "show signals [--json] [--pretty]\n  List configured devices and their supported DSL signals.",
            "show signal": "show signal <device>\n  Show supported DSL signals for one configured device.",
            "sources": HELP_SOURCES_TEXT,
            "show sources": HELP_SOURCES_TEXT,
            "diagnose": HELP_DIAGNOSE_TEXT,
            "group": "group <group>\n  Create/select a group (config mode).",
            "no group": "no group <group>\n  Delete group (config mode, prompts in interactive).",
            "no device": "no device <device>\n  Delete a device from the active profile.",
            "profile": (
                "profile <profile>\n"
                "  Select active profile for groups/bindings.\n"
                "profile default <profile>\n"
                "  Set the default profile name in bringup_system.json.\n"
                "profile create <profile>\n"
                "  Create a new empty profile and select it.\n"
                "profile export <profile> <path> [--install-robot]\n"
                "  Write a JSON snapshot plus CLI script for the profile."
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
                "save config <bringup_system.json> [--force]\n"
                "  Write full unified config (profiles + bridgeConfig.byProfile)."
            ),
            "save bridge-config": (
                "save bridge-config <bridgeConfig.json> [--force]\n"
                "  Write bridgeConfig.byProfile for the active profile."
            ),
            "save runtime-groups": (
                "save runtime-groups <runtime_groups.json> [--force]\n"
                "  Save runtime groups from the connected robot."
            ),
            "save all": (
                "save all [--prompt] [--force]\n"
                "  Save all dirty sections using current file paths."
            ),
            "save profiles": (
                "save profiles [path] [--force]\n"
                "  Save bringup_system.json (profiles + bridgeConfig.byProfile).\n"
                "  If path is omitted, uses the loaded profiles path (prompts)."
            ),
            "save tests": (
                "save tests <path> [--force]\n"
                "  Legacy bringup_tests.json is not supported; use `save config <path>`."
            ),
            "save sources": "save sources [--force]\n  Save all local sources back to disk.",
            "reset zero-config": HELP_RESET_ZERO_CONFIG_TEXT,
            "recover": HELP_RECOVER_TEXT,
            "validate file": HELP_VALIDATE_FILE_TEXT,
            "rename device": (
                "rename device <old> <new>\n"
                "  Rename a device in local config.\n"
                "  Alias: rename <old> <new>"
            ),
            "device set": (
                "device <device> set <field> <value>\n"
                "  Fields: vendor, role, notes, bus, tags, limits\n"
                "  Use JSON for tags/limits (e.g., tags [\"arm\",\"motor\"])."
            ),
            "device": (
                "device <device>\n"
                "  Enter device mode to edit local device metadata."
            ),
            HELP_TOPIC_DEVICE_USAGE: HELP_DEVICE_USAGE_TEXT,
            HELP_TOPIC_PROFILE_DEVICE_DELETE: HELP_PROFILE_DEVICE_DELETE_TEXT,
            HELP_TOPIC_PROFILE_DEVICE_SHOW_ALL: HELP_PROFILE_DEVICE_SHOW_ALL_TEXT,
            HELP_TOPIC_PROFILE_DELETE: HELP_PROFILE_DELETE_TEXT,
            HELP_TOPIC_PROFILE_EXPORT: HELP_PROFILE_EXPORT_TEXT,
            HELP_TOPIC_PROFILE_DEFAULT: HELP_PROFILE_DEFAULT_TEXT,
            HELP_TOPIC_PROFILES_PUSH: HELP_PROFILES_PUSH_TEXT,
            HELP_TOPIC_PROFILES_INIT: HELP_PROFILES_INIT_TEXT,
            HELP_TOPIC_PROFILES_EXPORT: HELP_PROFILES_EXPORT_TEXT,
            HELP_TOPIC_PROFILES_RELOAD: HELP_PROFILES_RELOAD_TEXT,
            HELP_TOPIC_RUNTIME: HELP_RUNTIME_TEXT,
            HELP_TOPIC_LIFECYCLE: HELP_LIFECYCLE_TEXT,
            HELP_TOPIC_CONFIG_PUSH: HELP_CONFIG_PUSH_TEXT,
            HELP_TOPIC_RESET_ZERO_CONFIG: HELP_RESET_ZERO_CONFIG_TEXT,
            HELP_TOPIC_RECOVER: HELP_RECOVER_TEXT,
            HELP_TOPIC_VALIDATE_FILE: HELP_VALIDATE_FILE_TEXT,
            HELP_TOPIC_QUICK: self._quick_help_text(),
            "device mode": (
                "device mode: show, set <field> <value>, no <field>, delete\n"
                "  Fields: vendor, role, notes, bus, tags, limits"
            ),
            "export cli-script": (
                "export cli-script <path>\n"
                "  Write a batch script that recreates the local config."
            ),
            "validate config": (
                "validate config [path] [--all]\n"
                "  Validate devices vs groups in a config file, or the local config if omitted."
            ),
            "validate all": (
                "validate all\n"
                "  Validate config, profiles, tests, bindings, and CAN mappings."
            ),
            "validate profiles": "validate profiles [robot|local]\n  Compare profile devices to robot or validate locally.",
            "validate tests": "validate tests\n  Validate tests against profile devices.",
            "validate bindings": "validate bindings [path]\n  Validate bindings payload.",
            "validate can-mappings": "validate can-mappings [path]\n  Validate CAN mappings payload.",
            "validate script": "validate script <path>\n  Lint a CLI script without executing it.",
            "bindings": (
                "bindings show [controllers|bindings] [--all] [--json] [--pretty]\n"
                "bindings controller add <controller> <type> <port>\n"
                "bindings controller set <controller> <field> <value>\n"
                "bindings controller rename <old> <new>\n"
                "bindings no controller <controller>\n"
                "bindings binding add <command> <controller> <input> <id> <mode> [invert <on|off> deadband <value>]\n"
                "bindings binding set <index> <field> <value>\n"
                "bindings binding delete <index>\n"
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
                "tests clear"
            ),
            "member assign": (
                "member assign <device>\n"
                "member assign all\n"
                "member assign next\n"
                "  Assign device labels to the current group."
            ),
            "member remove": "member remove <device>\n  Remove a device label from the current group.",
            "member enable": "member enable <label>\n  Enable one current-group member.",
            "member disable": "member disable <label>\n  Disable one current-group member.",
            "member toggle": "member toggle <label>\n  Toggle one current-group member.",
            "group member": (
                "group member assign <group> <label>\n"
                "group member remove <group> <label>\n"
                "group member enable <group> <label>\n"
                "group member disable <group> <label>\n"
                "group member toggle <group> <label>\n"
                "group member assign all <group>\n"
                "group member assign next <group>\n"
                "  Edit group membership from config mode without entering group context."
            ),
            "member": (
                "member assign|remove|enable|disable|toggle <device>\n"
                "  Edit current-group membership or per-member enabled state."
            ),
            "bind": (
                "bind list\n"
                "bind explain <binding>\n"
                "bind test <binding>\n"
                "bind <input> <analog|hold|toggle|jog-forward|jog-reverse> [value]\n"
                "  Create a binding or inspect one current-group binding."
            ),
            "no bind": "no bind\n  Clear all bindings from current group.",
            "enable": "enable\n  Enable current group.",
            "disable": "disable\n  Disable current group.",
            "run test": "run test [name]\n  Run a test in the current group.",
            "json": "append --json to show commands for JSON output; add --pretty for pretty JSON",
            "sources": "append robot|local|both to show commands to select source",
            "batch": "use --batch --script <file> (no prompts, conflict policy applies)",
        }

    def _help_topics(self) -> List[str]:
        return sorted(self._help_topic_map().keys())

    def _quick_help_text(self) -> str:
        """
        NAME
            _quick_help_text - Build a concise, mode-aware help summary.
        """
        mode = self._modes[-1].name
        entries: List[str] = []
        if mode == MODE_CONFIG:
            entries = [
                f"{CMD_PROFILE} {PLACEHOLDER_PROFILE}",
                f"{CMD_SHOW} {CMD_DEVICES}",
                f"{CMD_VALIDATE} {CMD_CONFIG}",
                f"{CMD_SAVE} {CMD_PROFILES} {PLACEHOLDER_PATH}",
                f"{CMD_PROFILE} {CMD_DEVICE} {CMD_DELETE} {PLACEHOLDER_DEVICE}",
            ]
        elif mode == MODE_TEST:
            entries = [
                f"{CMD_SHOW} {CMD_TESTS}",
                f"{CMD_TEST} {CMD_CREATE} {PLACEHOLDER_TEST}",
                f"{CMD_TEST} {CMD_SET} {PLACEHOLDER_TEST}",
                f"{CMD_SAVE} {CMD_TESTS} {PLACEHOLDER_PATH}",
            ]
        elif mode == MODE_GROUP:
            entries = [
                f"{CMD_SHOW}",
                f"{CMD_MEMBER} {CMD_ASSIGN} {PLACEHOLDER_DEVICE}",
                f"{CMD_RUN} {CMD_TEST} {PLACEHOLDER_TEST}",
            ]
        elif mode == MODE_DEVICE:
            entries = [
                f"{CMD_SHOW}",
                f"{CMD_SET} {PLACEHOLDER_FIELD}",
                f"{CMD_NO} {PLACEHOLDER_FIELD}",
            ]
        else:
            entries = [
                CMD_SHOW,
                CMD_CONFIGURE,
                CMD_CONNECT,
                CMD_DISCONNECT,
                f"{CMD_INSTANTIATE} {CMD_NEXT} {CMD_MOTOR}",
                f"{CMD_INSTANTIATE} {CMD_ALL} {CMD_DEVICES}",
                f"{CMD_RUN} {CMD_TEST} {PLACEHOLDER_TEST}",
            ]
        lines = [MESSAGE_HELP_QUICK_HEADER]
        if not entries:
            lines.append(HELP_INDENT + MESSAGE_HELP_QUICK_EMPTY.strip())
            return SEP_NEWLINE.join(lines)
        for entry in entries:
            lines.append(HELP_INDENT + entry)
        lines.append(HELP_INDENT + MESSAGE_HELP_QUICK_ALIASES)
        return SEP_NEWLINE.join(lines)

    def _parse_show_flags(self, tokens: List[str]) -> tuple[str, List[str], bool, bool, bool, bool]:
        source = EMPTY_STRING
        cleaned: List[str] = []
        json_output = False
        pretty = False
        grouped = False
        for tok in tokens:
            lower = tok.lower()
            if lower in ("--json",):
                json_output = True
                continue
            if lower in ("--pretty",):
                pretty = True
                continue
            if lower == SHOW_FLAG_GROUPED:
                grouped = True
                continue
            if lower in (SHOW_SOURCE_ROBOT, "--robot"):
                source = SHOW_SOURCE_ROBOT
                continue
            if lower in (SHOW_SOURCE_LOCAL, "--local"):
                source = SHOW_SOURCE_LOCAL
                continue
            if lower in (SHOW_SOURCE_BOTH, "--both"):
                source = SHOW_SOURCE_BOTH
                continue
            cleaned.append(tok)
        if not source:
            source = SHOW_SOURCE_ROBOT if self._session.is_connected() else SHOW_SOURCE_LOCAL
        if pretty and not json_output:
            print(MESSAGE_ERR_PRETTY_REQUIRES_JSON)
            return source, cleaned, False, False, grouped, False
        return source, cleaned, json_output, pretty, grouped, True

    @staticmethod
    def _dump_json(payload: object, pretty: bool) -> str:
        """
        NAME
            _dump_json - Serialize JSON with optional pretty formatting.
        """
        if pretty:
            return json.dumps(payload, indent=JSON_PRETTY_INDENT)
        return json.dumps(payload)

    def _fetch_robot_runtime_payload(self, print_events: bool = True) -> Optional[Dict[str, object]]:
        """
        NAME
            _fetch_robot_runtime_payload - Fetch runtime-state JSON from the robot.
        """
        if not self._session.is_connected():
            return None
        seq = show_runtime_state(self._session, json_output=True)
        if seq is None:
            return None
        self._proto_mark_cmd_sent(CMD_SHOW_RUNTIME_STATE, now=time.time())
        event = self._wait_for_seq(
            seq,
            timeout_sec=self._robot_show_timeout_sec(CMD_SHOW_RUNTIME_STATE),
            print_events=print_events,
            suppress_timeout_warning=not print_events,
        )
        if self._event_failed(event, "show runtime-state"):
            return None
        payload = parse_json_arg(event.json_text or event.text or EMPTY_STRING)
        if isinstance(payload, dict):
            return payload
        return None

    def _runtime_details_snapshot_local(self) -> Dict[str, object]:
        """
        NAME
            _runtime_details_snapshot_local - Read host runtime component details when available.
        """
        if self._runtime_details_provider is None:
            return {}
        try:
            payload = self._runtime_details_provider()
        except Exception:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _visibility_snapshot_local(self) -> Dict[str, object]:
        """
        NAME
            _visibility_snapshot_local - Read host visibility snapshot + summary when available.
        """
        provider = self._visibility_provider
        if provider is None:
            return {}
        now_ms = int(time.time() * COUNT_THOUSAND)
        snapshot = {}
        summary = {}
        try:
            if hasattr(provider, "snapshot"):
                raw_snapshot = provider.snapshot("expected", now_ms)
                if isinstance(raw_snapshot, dict):
                    snapshot = raw_snapshot
            if hasattr(provider, "summary"):
                raw_summary = provider.summary("expected", now_ms)
                if isinstance(raw_summary, dict):
                    summary = raw_summary
        except Exception:
            return {}
        return {
            KEY_SUMMARY: summary,
            KEY_DEVICES: snapshot.get(KEY_DEVICES, []) if isinstance(snapshot.get(KEY_DEVICES), list) else [],
            KEY_SOURCES: snapshot.get(KEY_SOURCES, []) if isinstance(snapshot.get(KEY_SOURCES), list) else [],
        }

    @staticmethod
    def _device_runtime_index(runtime_payload: Dict[str, object]) -> Dict[str, Dict[str, object]]:
        """
        NAME
            _device_runtime_index - Index runtime-state devices by normalized label.
        """
        devices = runtime_payload.get(KEY_DEVICES)
        if not isinstance(devices, list):
            return {}
        indexed: Dict[str, Dict[str, object]] = {}
        for entry in devices:
            if not isinstance(entry, dict):
                continue
            label = str(entry.get(KEY_LABEL, EMPTY_STRING)).strip().lower()
            if label:
                indexed[label] = entry
        return indexed

    @staticmethod
    def _fault_flag_count(attachment: Dict[str, object], key: str) -> int:
        """
        NAME
            _fault_flag_count - Count list-style fault flag fields.
        """
        values = attachment.get(key)
        if not isinstance(values, list):
            return COUNT_ZERO
        return len([item for item in values if isinstance(item, str) and item.strip()])

    def _collect_runtime_fault_rows(self, runtime_payload: Dict[str, object]) -> List[Dict[str, object]]:
        """
        NAME
            _collect_runtime_fault_rows - Extract device fault rows from runtime-state JSON.
        """
        devices = runtime_payload.get(KEY_DEVICES)
        if not isinstance(devices, list):
            return []
        rows: List[Dict[str, object]] = []
        for entry in devices:
            if not isinstance(entry, dict):
                continue
            label = str(entry.get(KEY_LABEL, EMPTY_STRING)).strip()
            attachments = entry.get(KEY_ATTACHMENTS)
            found = False
            if isinstance(attachments, list):
                for attachment in attachments:
                    if not isinstance(attachment, dict):
                        continue
                    fault_count = COUNT_ZERO
                    warning_count = COUNT_ZERO
                    raw_faults = attachment.get(KEY_FAULTS_RAW)
                    raw_sticky_faults = attachment.get(KEY_STICKY_FAULTS_RAW)
                    raw_warnings = attachment.get(KEY_WARNINGS_RAW)
                    raw_sticky_warnings = attachment.get(KEY_STICKY_WARNINGS_RAW)
                    if isinstance(raw_faults, int) and raw_faults != COUNT_ZERO:
                        fault_count += COUNT_ONE
                    if isinstance(raw_sticky_faults, int) and raw_sticky_faults != COUNT_ZERO:
                        fault_count += COUNT_ONE
                    if isinstance(raw_warnings, int) and raw_warnings != COUNT_ZERO:
                        warning_count += COUNT_ONE
                    if isinstance(raw_sticky_warnings, int) and raw_sticky_warnings != COUNT_ZERO:
                        warning_count += COUNT_ONE
                    fault_count += self._fault_flag_count(attachment, KEY_FAULT_FLAGS)
                    fault_count += self._fault_flag_count(attachment, KEY_STICKY_FAULT_FLAGS)
                    warning_count += self._fault_flag_count(attachment, KEY_WARNING_FLAGS)
                    warning_count += self._fault_flag_count(attachment, KEY_STICKY_WARNING_FLAGS)
                    if fault_count > COUNT_ZERO or warning_count > COUNT_ZERO:
                        rows.append(
                            {
                                KEY_LABEL: label,
                                KEY_TYPE: str(attachment.get(KEY_TYPE, EMPTY_STRING)).strip(),
                                KEY_FAULT_COUNT: fault_count,
                                KEY_WARNING_COUNT: warning_count,
                                KEY_DETAILS: attachment,
                            }
                        )
                        found = True
            power_fault = any(
                bool(entry.get(key, False))
                for key in (
                    KEY_BROWNOUT,
                    KEY_CAN_WARNING,
                    KEY_HARDWARE_FAULT,
                    KEY_STICKY_BROWNOUT,
                    KEY_STICKY_CAN_WARNING,
                    KEY_STICKY_CAN_BUS_OFF,
                    KEY_STICKY_HAS_RESET,
                )
            )
            channel_fault = any(bool(value) for value in entry.get(KEY_CHANNEL_FAULT, []) or [])
            channel_sticky_fault = any(
                bool(value) for value in entry.get(KEY_CHANNEL_STICKY_FAULT, []) or []
            )
            if not found and (power_fault or channel_fault or channel_sticky_fault):
                rows.append(
                    {
                        KEY_LABEL: label,
                        KEY_TYPE: str(entry.get(KEY_TYPE, EMPTY_STRING)).strip(),
                        KEY_FAULT_COUNT: COUNT_ONE if (power_fault or channel_fault or channel_sticky_fault) else COUNT_ZERO,
                        KEY_WARNING_COUNT: COUNT_ZERO,
                        KEY_DETAILS: entry,
                    }
                )
        return rows

    @staticmethod
    def _parse_event_json_payload(event: Optional[BridgeEvent]) -> Dict[str, object]:
        """
        NAME
            _parse_event_json_payload - Parse event JSON payload when present.
        """
        json_text = getattr(event, "json_text", EMPTY_STRING) if event is not None else EMPTY_STRING
        if not json_text:
            return {}
        payload = parse_json_arg(json_text)
        return payload if isinstance(payload, dict) else {}

    def _sync_host_profile_context_to_robot(self, robot_profile: object, prompt_user: bool) -> None:
        """
        NAME
            _sync_host_profile_context_to_robot - Align host context to robot-selected profile when requested.
        """
        decision = decide_host_profile_sync(
            self._host_profile_context_name(),
            robot_profile,
            (
                self._local_root_payload.get(KEY_PROFILES, {}).keys()
                if isinstance(self._local_root_payload, dict)
                and isinstance(self._local_root_payload.get(KEY_PROFILES), dict)
                else []
            ),
        )
        robot_name = decision.robot_profile
        host_name = decision.host_profile
        if not robot_name:
            return
        self._robot_selected_profile = robot_name
        if decision.action == SYNC_ACTION_NONE:
            self._profile_context_mismatch_seen = None
            return
        mismatch_key = (host_name, robot_name)
        if self._profile_context_mismatch_seen == mismatch_key:
            return
        if decision.action == SYNC_ACTION_MISSING_LOCAL:
            print(MESSAGE_PROFILE_CONTEXT_MISSING_LOCAL_FMT.format(robot=robot_name, host=host_name))
            self._profile_context_mismatch_seen = mismatch_key
            return
        if decision.action == SYNC_ACTION_ADOPT:
            self._apply_host_profile_context(robot_name, announce=True)
            self._profile_context_mismatch_seen = None
            return
        if self._batch or not prompt_user:
            print(MESSAGE_PROFILE_CONTEXT_BATCH_SYNC_FMT.format(robot=robot_name, host=host_name))
            self._apply_host_profile_context(robot_name, announce=True)
            self._profile_context_mismatch_seen = mismatch_key
            return
        if decision.action == SYNC_ACTION_PROMPT and self._confirm_yes_default(
            MESSAGE_PROFILE_CONTEXT_MISMATCH_FMT.format(robot=robot_name, host=host_name)
        ):
            self._apply_host_profile_context(robot_name, announce=True)
        self._profile_context_mismatch_seen = mismatch_key

    def _query_robot_selected_profile(self) -> str:
        """
        NAME
            _query_robot_selected_profile - Read the robot-selected profile using showProfiles JSON.
        """
        if not self._session.is_connected():
            return EMPTY_STRING
        runtime_payload = self._fetch_robot_runtime_payload(print_events=False)
        if isinstance(runtime_payload, dict):
            selected = self._normalize_profile_context_name(runtime_payload.get("selectedProfile"))
            if selected:
                return selected
        seq = show_profiles(self._session, json_output=True)
        event = self._wait_for_seq(
            seq,
            timeout_sec=ROBOT_COMMAND_TIMEOUT_SEC,
            print_events=False,
            suppress_timeout_warning=True,
        )
        if not self._event_failed(event, "show profiles"):
            selected = self._selected_profile_from_show_profiles_payload(self._parse_event_json_payload(event))
            if selected:
                return selected
            selected = self._selected_profile_from_show_profiles_text(
                event.text if event is not None else EMPTY_STRING
            )
            if selected:
                return selected
            if event is not None and isinstance(event.state, dict):
                selected = self._normalize_profile_context_name(event.state.get("selectedProfile"))
                if selected:
                    return selected
        snapshot = self._session.get_state_snapshot()
        if isinstance(snapshot, dict):
            selected = self._normalize_profile_context_name(snapshot.get("selectedProfile"))
            if selected:
                return selected
        return EMPTY_STRING

    def _query_robot_selected_profile_after_connect(self) -> str:
        """
        NAME
            _query_robot_selected_profile_after_connect - Retry selected-profile discovery during explicit connect.

        DESCRIPTION
            After a successful REST handshake, robot-selected profile state can
            lag briefly behind the first host query. This bounded retry is only
            used during explicit `connect`, not during disconnected startup.
        """
        deadline = time.time() + CONNECT_PROFILE_SYNC_TIMEOUT_SEC
        while time.time() < deadline:
            selected = self._query_robot_selected_profile()
            if selected:
                return selected
            time.sleep(CONNECT_PROFILE_SYNC_SLEEP_SEC)
        return self._query_robot_selected_profile()

    def _apply_profile_sync_after_connect(self, prompt_user: bool) -> Optional[StatusResult]:
        """
        NAME
            _apply_profile_sync_after_connect - Align robot and host profile context after a successful connect.
        """
        self._auto_merge_default_profiles_for_connect()
        connect_profile = self._connect_target_profile_name()
        if connect_profile:
            result = self._set_active_profile(connect_profile)
            if not result.ok():
                return result
            return None
        self._sync_host_profile_context_to_robot(
            self._query_robot_selected_profile_after_connect(),
            prompt_user=prompt_user,
        )
        return None

    def _profile_select_event_error(self, event: Optional[BridgeEvent]) -> str:
        """
        NAME
            _profile_select_event_error - Return semantic profile-selection failure text when present.
        """
        payload = self._parse_event_json_payload(event)
        if isinstance(payload, dict):
            success_value = payload.get("success")
            error_message = str(payload.get("errorMessage", EMPTY_STRING)).strip()
            if success_value is False and error_message:
                return error_message
        if event is None:
            return EMPTY_STRING
        message_text = str(
            getattr(event, "message", EMPTY_STRING) or getattr(event, "text", EMPTY_STRING) or EMPTY_STRING
        ).strip()
        if message_text.startswith("Profile change blocked:"):
            return message_text
        return EMPTY_STRING

    def _print_profiles_apply_stages(self, payload: Dict[str, object]) -> None:
        """
        NAME
            _print_profiles_apply_stages - Print staged profilesApply results from robot JSON.
        """
        stages = [
            ("transfer check", "transferCheck"),
            ("content validation", "contentValidation"),
            ("apply", "apply"),
            ("post-apply check", "postApplyCheck"),
        ]
        for label, key in stages:
            stage_payload = payload.get(key)
            if not isinstance(stage_payload, dict):
                print(MESSAGE_PUSH_STAGE.format(stage=label, status=VALUE_UNAVAILABLE))
                continue
            ok = bool(stage_payload.get(KEY_OK, False))
            status = MATCH_STATE_YES if ok else MATCH_STATE_NO
            print(MESSAGE_PUSH_STAGE.format(stage=label, status=status))
            detail = str(stage_payload.get(KEY_MESSAGE, EMPTY_STRING)).strip()
            if detail:
                print(MESSAGE_PUSH_STAGE_DETAIL.format(detail=detail))
        active_profile = str(payload.get("activeProfile", EMPTY_STRING)).strip()
        if active_profile:
            print(MESSAGE_PUSH_STAGE_ACTIVE.format(profile=active_profile))

    @staticmethod
    def _bool_text(value: bool) -> str:
        """
        NAME
            _bool_text - Render YES/NO for human-readable output.
        """
        return MATCH_STATE_YES if value else MATCH_STATE_NO

    def _active_profile_labels(self) -> List[str]:
        """
        NAME
            _active_profile_labels - Return configured device labels for the active profile.
        """
        profile_name = self._active_profile_name()
        if not isinstance(self._local_root_payload, dict) or not profile_name:
            return []
        profiles = self._local_root_payload.get(KEY_PROFILES)
        if not isinstance(profiles, dict):
            return []
        entry = profiles.get(profile_name)
        if not isinstance(entry, dict):
            return []
        labels = entry.get(KEY_PROFILE_DEVICES)
        if not isinstance(labels, list):
            return []
        return [str(label).strip() for label in labels if isinstance(label, str) and str(label).strip()]

    def _registry_manufacturer_display(self, entry: Dict[str, object]) -> str:
        """
        NAME
            _registry_manufacturer_display - Resolve display text for one registry manufacturer.
        """
        value = entry.get(KEY_MANUFACTURER)
        if isinstance(value, int):
            mappings = self._load_can_mappings()
            manufacturers = mappings.get(KEY_MANUFACTURERS, {}) if isinstance(mappings, dict) else {}
            mapped = manufacturers.get(str(value), EMPTY_STRING) if isinstance(manufacturers, dict) else EMPTY_STRING
            if isinstance(mapped, str) and mapped.strip():
                return mapped.strip()
            return str(value)
        text = str(value or EMPTY_STRING).strip()
        return text

    def _registry_device_type_display(self, entry: Dict[str, object]) -> str:
        """
        NAME
            _registry_device_type_display - Resolve display text for one registry device type.
        """
        value = entry.get(KEY_DEVICE_TYPE)
        if isinstance(value, int):
            mappings = self._load_can_mappings()
            device_types = mappings.get(KEY_DEVICE_TYPES, {}) if isinstance(mappings, dict) else {}
            mapped = device_types.get(str(value), EMPTY_STRING) if isinstance(device_types, dict) else EMPTY_STRING
            if isinstance(mapped, str) and mapped.strip():
                return mapped.strip()
            return str(value)
        text = str(entry.get(KEY_TYPE, value or EMPTY_STRING)).strip()
        return text

    def _registry_show_device_entry(
        self,
        entry: Dict[str, object],
        active_labels: set[str],
    ) -> Dict[str, object]:
        """
        NAME
            _registry_show_device_entry - Build one config-wide show devices row from the shared registry.
        """
        label = str(entry.get(KEY_LABEL, EMPTY_STRING)).strip()
        interface_value = str(entry.get(KEY_INTERFACE, EMPTY_STRING)).strip()
        row: Dict[str, object] = {
            KEY_LABEL: label,
            KEY_INTERFACE: interface_value,
            KEY_VENDOR: self._registry_manufacturer_display(entry),
            KEY_TYPE: self._registry_device_type_display(entry),
            KEY_ID: entry.get(KEY_ID, COUNT_ZERO),
            KEY_MODEL: str(entry.get(KEY_MODEL, EMPTY_STRING)).strip(),
            KEY_IN_PROFILE: label.lower() in active_labels,
        }
        return row

    def _show_local_registry_devices(self, json_output: bool, pretty: bool) -> StatusResult:
        """
        NAME
            _show_local_registry_devices - Show the full shared device inventory from the loaded config.
        """
        if not isinstance(self._local_root_payload, dict):
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        devices = self._local_root_payload.get(KEY_DEVICES)
        rows: List[Dict[str, object]] = []
        active_labels = {label.lower() for label in self._active_profile_labels()}
        active_order = {label.lower(): index for index, label in enumerate(self._active_profile_labels())}
        if isinstance(devices, list):
            for entry in devices:
                if not isinstance(entry, dict):
                    continue
                label = str(entry.get(KEY_LABEL, EMPTY_STRING)).strip()
                if not label:
                    continue
                rows.append(self._registry_show_device_entry(entry, active_labels))
        rows.sort(
            key=lambda item: (
                not bool(item.get(KEY_IN_PROFILE, False)),
                active_order.get(str(item.get(KEY_LABEL, EMPTY_STRING)).strip().lower(), COUNT_ZERO),
                str(item.get(KEY_LABEL, EMPTY_STRING)).strip().lower(),
            )
        )
        payload = {
            KEY_PROFILE: self._active_profile_name() or EMPTY_STRING,
            KEY_SCOPE: SCOPE_CONFIG,
            KEY_DEVICES: rows,
        }
        print(MESSAGE_SOURCE_LOCAL)
        if json_output:
            print(self._dump_json(payload, pretty))
            return StatusResult(code=SS__NORMAL)
        if not rows:
            print(TEXT_DEVICES_ALL_NONE)
            return StatusResult(code=SS__NORMAL)
        print(TEXT_DEVICES_ALL_HEADER)
        for row in rows:
            print(
                TEXT_DEVICES_LIST_PREFIX
                + TEXT_DEVICE_REGISTRY_ENTRY.format(
                    label=row.get(KEY_LABEL, EMPTY_STRING),
                    interface=row.get(KEY_INTERFACE, EMPTY_STRING),
                    vendor=row.get(KEY_VENDOR, EMPTY_STRING),
                    type=row.get(KEY_TYPE, EMPTY_STRING),
                    id=row.get(KEY_ID, COUNT_ZERO),
                    model=row.get(KEY_MODEL, EMPTY_STRING) or STRING_NONE,
                    in_profile=MATCH_STATE_YES if bool(row.get(KEY_IN_PROFILE, False)) else MATCH_STATE_NO,
                )
            )
        return StatusResult(code=SS__NORMAL)

    def _show_active_local(self, json_output: bool, pretty: bool) -> StatusResult:
        """
        NAME
            _show_active_local - Show effective local active state summary.
        """
        runtime_details = self._runtime_details_snapshot_local()
        visibility = self._visibility_snapshot_local()
        active_group = self._active_group_payload()
        members = active_group.get(KEY_MEMBERS, []) if isinstance(active_group, dict) else []
        payload = {
            KEY_PROFILE: self._active_profile_name() or EMPTY_STRING,
            KEY_RECOVERY_MODE: bool(self._recovery_mode),
            KEY_DIRTY: self._current_dirty_flags(),
            KEY_ACTIVE_GROUP: {
                KEY_NAME: GROUP_NAME_ACTIVE,
                KEY_MEMBER_COUNT: len(members) if isinstance(members, list) else COUNT_ZERO,
            },
            KEY_ACTIVE_TEST_SET: self._tests_active_set or EMPTY_STRING,
            KEY_RUNTIME: runtime_details,
            KEY_VISIBILITY: visibility,
        }
        print(MESSAGE_SOURCE_LOCAL)
        if json_output:
            print(self._dump_json(payload, pretty))
            return StatusResult(code=SS__NORMAL)
        component_count = len(runtime_details.get(KEY_RUNTIME_COMPONENTS, [])) if isinstance(runtime_details.get(KEY_RUNTIME_COMPONENTS), list) else COUNT_ZERO
        visible_summary = visibility.get(KEY_SUMMARY, {}) if isinstance(visibility, dict) else {}
        print("Active state:")
        print(f"  profile: {payload[KEY_PROFILE] or STRING_NONE}")
        print(f"  recovery mode: {self._bool_text(bool(payload[KEY_RECOVERY_MODE]))}")
        print(f"  dirty: {self._bool_text(self._has_dirty_state())}")
        print(f"  active group members: {payload[KEY_ACTIVE_GROUP][KEY_MEMBER_COUNT]}")
        print(f"  active test set: {payload[KEY_ACTIVE_TEST_SET] or STRING_NONE}")
        print(f"  runtime components: {component_count}")
        if isinstance(visible_summary, dict) and visible_summary:
            print(
                "  visibility: devices={devices} all={all_seen} some={some_seen} none={none_seen}".format(
                    devices=visible_summary.get("devicesShown", COUNT_ZERO),
                    all_seen=visible_summary.get("visibleAll", COUNT_ZERO),
                    some_seen=visible_summary.get("visibleSome", COUNT_ZERO),
                    none_seen=visible_summary.get("visibleNone", COUNT_ZERO),
                )
            )
        else:
            print(f"  visibility: {VALUE_UNAVAILABLE}")
        return StatusResult(code=SS__NORMAL)

    def _show_active_robot(self, json_output: bool, pretty: bool) -> StatusResult:
        """
        NAME
            _show_active_robot - Show robot runtime active state summary.
        """
        payload = self._fetch_robot_runtime_payload()
        if not isinstance(payload, dict):
            print("ERROR: Robot runtime-state unavailable.")
            return StatusResult(code=SS__NETWORK__ROBOT_UNAVAILABLE)
        devices = payload.get(KEY_DEVICES, []) if isinstance(payload.get(KEY_DEVICES), list) else []
        groups = payload.get(KEY_BRIDGE_GROUPS, []) if isinstance(payload.get(KEY_BRIDGE_GROUPS), list) else []
        selected = payload.get(KEY_BRIDGE_SELECTED_DEVICE, {}) if isinstance(payload.get(KEY_BRIDGE_SELECTED_DEVICE), dict) else {}
        summary = {
            KEY_PROFILE: str(payload.get(KEY_PROFILE, EMPTY_STRING)).strip(),
            KEY_ENABLED: bool(payload.get(KEY_ENABLED, False)),
            KEY_ESTOPPED: bool(payload.get(KEY_ESTOPPED, False)),
            KEY_MODE: str(payload.get(KEY_MODE, EMPTY_STRING)).strip(),
            KEY_DEVICE_COUNT: len(devices),
            KEY_GROUP_COUNT: len(groups),
            KEY_BRIDGE_SELECTED_DEVICE: selected,
            KEY_DEVICES: devices,
            KEY_BRIDGE_GROUPS: groups,
        }
        print(MESSAGE_SOURCE_ROBOT)
        if json_output:
            print(self._dump_json(summary, pretty))
            return StatusResult(code=SS__NORMAL)
        print("Active state:")
        print(f"  profile: {summary[KEY_PROFILE] or STRING_NONE}")
        print(f"  enabled: {self._bool_text(bool(summary[KEY_ENABLED]))}")
        print(f"  estopped: {self._bool_text(bool(summary[KEY_ESTOPPED]))}")
        print(f"  mode: {summary[KEY_MODE] or STRING_NONE}")
        print(f"  runtime devices: {summary[KEY_DEVICE_COUNT]}")
        print(f"  groups: {summary[KEY_GROUP_COUNT]}")
        print(
            "  selected device: {device} ({state})".format(
                device=str(selected.get(KEY_DEVICE, EMPTY_STRING)).strip() or STRING_NONE,
                state=TEXT_STATUS_ON if bool(selected.get(KEY_ENABLED, False)) else TEXT_STATUS_OFF,
            )
        )
        return StatusResult(code=SS__NORMAL)

    def _show_instantiated_local(self, json_output: bool, pretty: bool) -> StatusResult:
        """
        NAME
            _show_instantiated_local - Show configured devices with local visibility state.
        """
        labels = self._active_profile_labels()
        visibility = self._visibility_snapshot_local()
        visible_devices = visibility.get(KEY_DEVICES, []) if isinstance(visibility.get(KEY_DEVICES), list) else []
        visible_by_label = {
            str(entry.get(KEY_LABEL, EMPTY_STRING)).strip().lower(): entry
            for entry in visible_devices
            if isinstance(entry, dict)
        }
        rows: List[Dict[str, object]] = []
        for label in labels:
            vis_entry = visible_by_label.get(label.lower(), {})
            visibility_map = vis_entry.get(KEY_VISIBILITY, {}) if isinstance(vis_entry, dict) else {}
            present = any(value is True for value in visibility_map.values()) if isinstance(visibility_map, dict) else False
            rows.append(
                {
                    KEY_LABEL: label,
                    KEY_INSTANTIATED: None,
                    KEY_PRESENT: present,
                    KEY_REASON: "robot runtime instantiation unavailable from local source",
                    KEY_VISIBILITY: visibility_map if isinstance(visibility_map, dict) else {},
                }
            )
        payload = {KEY_PROFILE: self._active_profile_name() or EMPTY_STRING, KEY_DEVICES: rows}
        print(MESSAGE_SOURCE_LOCAL)
        if json_output:
            print(self._dump_json(payload, pretty))
            return StatusResult(code=SS__NORMAL)
        print("Instantiated devices:")
        if not rows:
            print(f"  {STRING_NONE}")
            return StatusResult(code=SS__NORMAL)
        for row in rows:
            print(
                "  {label}: instantiated={instantiated} present={present} reason={reason}".format(
                    label=row[KEY_LABEL],
                    instantiated=VALUE_UNAVAILABLE,
                    present=self._bool_text(bool(row[KEY_PRESENT])),
                    reason=row[KEY_REASON],
                )
            )
        return StatusResult(code=SS__NORMAL)

    def _show_instantiated_robot(self, json_output: bool, pretty: bool) -> StatusResult:
        """
        NAME
            _show_instantiated_robot - Show robot runtime instantiated device state.
        """
        payload = self._fetch_robot_runtime_payload()
        if not isinstance(payload, dict):
            print("ERROR: Robot runtime-state unavailable.")
            return StatusResult(code=SS__NETWORK__ROBOT_UNAVAILABLE)
        devices = payload.get(KEY_DEVICES, []) if isinstance(payload.get(KEY_DEVICES), list) else []
        rows: List[Dict[str, object]] = []
        for entry in devices:
            if not isinstance(entry, dict):
                continue
            rows.append(
                {
                    KEY_LABEL: str(entry.get(KEY_LABEL, EMPTY_STRING)).strip(),
                    KEY_TYPE: str(entry.get(KEY_TYPE, EMPTY_STRING)).strip(),
                    KEY_ID: entry.get(KEY_ID),
                    KEY_INSTANTIATED: bool(entry.get(KEY_INSTANTIATED, False)),
                    KEY_PRESENT: float(entry.get(KEY_PRESENCE_CONF, 0.0)) > 0.0,
                    KEY_LAST_SEEN_MS: entry.get(KEY_LAST_SEEN_MS),
                }
            )
        result_payload = {KEY_PROFILE: str(payload.get(KEY_PROFILE, EMPTY_STRING)).strip(), KEY_DEVICES: rows}
        print(MESSAGE_SOURCE_ROBOT)
        if json_output:
            print(self._dump_json(result_payload, pretty))
            return StatusResult(code=SS__NORMAL)
        print("Instantiated devices:")
        if not rows:
            print(f"  {STRING_NONE}")
            return StatusResult(code=SS__NORMAL)
        for row in rows:
            print(
                "  {label}: instantiated={instantiated} present={present} id={id}".format(
                    label=row[KEY_LABEL] or STRING_NONE,
                    instantiated=self._bool_text(bool(row[KEY_INSTANTIATED])),
                    present=self._bool_text(bool(row[KEY_PRESENT])),
                    id=row[KEY_ID],
                )
            )
        return StatusResult(code=SS__NORMAL)

    def _show_faults_local(self, json_output: bool, pretty: bool) -> StatusResult:
        """
        NAME
            _show_faults_local - Show local fault visibility availability.
        """
        payload = {
            KEY_FAULTS: [],
            KEY_REASON: "local source does not have robot fault attachments; use show faults robot",
        }
        print(MESSAGE_SOURCE_LOCAL)
        if json_output:
            print(self._dump_json(payload, pretty))
            return StatusResult(code=SS__NORMAL)
        print("Faults:")
        print(f"  {VALUE_UNAVAILABLE}: {payload[KEY_REASON]}")
        return StatusResult(code=SS__NORMAL)

    def _show_faults_robot(self, json_output: bool, pretty: bool) -> StatusResult:
        """
        NAME
            _show_faults_robot - Show robot runtime fault summary.
        """
        payload = self._fetch_robot_runtime_payload()
        if not isinstance(payload, dict):
            print("ERROR: Robot runtime-state unavailable.")
            return StatusResult(code=SS__NETWORK__ROBOT_UNAVAILABLE)
        rows = self._collect_runtime_fault_rows(payload)
        result_payload = {KEY_PROFILE: str(payload.get(KEY_PROFILE, EMPTY_STRING)).strip(), KEY_FAULTS: rows}
        print(MESSAGE_SOURCE_ROBOT)
        if json_output:
            print(self._dump_json(result_payload, pretty))
            return StatusResult(code=SS__NORMAL)
        print("Faults:")
        if not rows:
            print("  none")
            return StatusResult(code=SS__NORMAL)
        for row in rows:
            print(
                "  {label}: faults={faults} warnings={warnings} type={type}".format(
                    label=row.get(KEY_LABEL, STRING_NONE),
                    faults=row.get(KEY_FAULT_COUNT, COUNT_ZERO),
                    warnings=row.get(KEY_WARNING_COUNT, COUNT_ZERO),
                    type=row.get(KEY_TYPE, EMPTY_STRING) or STRING_NONE,
                )
            )
        return StatusResult(code=SS__NORMAL)

    def _show_robot(self, target: str, tokens: List[str], json_output: bool, pretty: bool) -> StatusResult:
        if not self._session.is_connected():
            print("ERROR: Robot source unavailable (not connected).")
            return StatusResult(code=SS__NETWORK__NOT_CONNECTED)
        if target == SHOW_TARGET_ACTIVE:
            return self._show_active_robot(json_output, pretty)
        if target == SHOW_TARGET_INSTANTIATED:
            return self._show_instantiated_robot(json_output, pretty)
        if target == SHOW_TARGET_FAULTS:
            return self._show_faults_robot(json_output, pretty)
        if target == SHOW_TARGET_SOURCES:
            seq = show_sources(self._session, json_output=json_output)
            cmd_name = CMD_SHOW_SOURCES
        elif target == SHOW_TARGET_STATUS:
            seq = show_status(self._session, json_output=json_output)
            cmd_name = CMD_SHOW_STATUS
        elif target == SHOW_TARGET_GROUPS:
            seq = show_groups(self._session, json_output=json_output)
            cmd_name = CMD_SHOW_GROUPS
        elif target == SHOW_TARGET_GROUP and len(tokens) >= 2:
            seq = show_group(self._session, tokens[1], json_output=json_output)
            cmd_name = CMD_SHOW_GROUP
        elif target == SHOW_TARGET_DEVICES:
            seq = show_devices(self._session, json_output=json_output)
            cmd_name = CMD_SHOW_DEVICES
        elif target == SHOW_TARGET_DEVICE_GROUP and len(tokens) >= 2:
            seq = show_device(self._session, tokens[1], json_output=json_output)
            cmd_name = CMD_SHOW_DEVICE
        elif target == SHOW_TARGET_BINDINGS:
            seq = show_bindings(self._session, json_output=json_output)
            cmd_name = CMD_SHOW_BINDINGS
        elif target == SHOW_TARGET_SELECTED_DEVICE:
            seq = show_selected_device(self._session, json_output=json_output)
            cmd_name = CMD_SHOW_SELECTED_DEVICE
        elif target == SHOW_TARGET_SAFETY_LATCH:
            seq = show_status(self._session, json_output=json_output)
            cmd_name = CMD_SHOW_STATUS
        elif target == SHOW_TARGET_RUNTIME:
            seq = show_runtime_state(self._session, json_output=json_output)
            cmd_name = CMD_SHOW_RUNTIME_STATE
        elif target == SHOW_TARGET_LIFECYCLE:
            seq = show_lifecycle_state(self._session, json_output=json_output)
            cmd_name = CMD_SHOW_LIFECYCLE_STATE
        elif target == SHOW_TARGET_VERSION:
            seq = show_version(self._session, json_output=json_output)
            cmd_name = CMD_SHOW_VERSION
        elif target == SHOW_TARGET_PROFILES:
            seq = show_profiles(self._session, json_output=json_output)
            cmd_name = CMD_SHOW_PROFILES
        elif target == SHOW_TARGET_PROFILE:
            name = tokens[1] if len(tokens) >= 2 else EMPTY_STRING
            if name:
                seq = show_profile(self._session, name, json_output=json_output)
                cmd_name = CMD_SHOW_PROFILE
            else:
                seq = show_profiles(self._session, json_output=json_output)
                cmd_name = CMD_SHOW_PROFILES
        else:
            print(MESSAGE_ERR_UNKNOWN_SHOW)
            print(MESSAGE_HINT_PREFIX + MESSAGE_HINT_SHOW)
            return StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX)
        if seq is None:
            print("ERROR: Command failed to send.")
            return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
        self._proto_mark_cmd_sent(cmd_name, now=time.time())
        self._show_label_seq[int(seq)] = "robot"
        self._show_pretty_json_seq[int(seq)] = bool(pretty)
        self._last_show_pretty = bool(pretty)
        event = self._wait_for_seq(seq, timeout_sec=self._robot_show_timeout_sec(cmd_name))
        if self._event_failed(event, "show"):
            return StatusResult(code=SS__NETWORK__COMMAND_SEND_FAILED)
        return StatusResult(code=SS__NORMAL)

    def _robot_show_timeout_sec(self, cmd_name: str) -> float:
        """
        NAME
            _robot_show_timeout_sec - Select CLI wait timeout for robot show commands.

        DESCRIPTION
            Runtime-state JSON can be expensive immediately after profile apply
            because the robot has just rebuilt devices, tests, and telemetry
            state. Keep ordinary show commands on the short default timeout.
        """
        if cmd_name in (CMD_SHOW_RUNTIME_STATE, CMD_SHOW_LIFECYCLE_STATE):
            return ROBOT_LONG_COMMAND_TIMEOUT_SEC
        return ROBOT_COMMAND_TIMEOUT_SEC

    def _show_local(
        self,
        target: str,
        tokens: List[str],
        json_output: bool,
        pretty: bool,
        grouped: bool,
    ) -> StatusResult:
        if target == SHOW_TARGET_VERSION:
            return self._show_local_version(json_output, pretty)
        if target == SHOW_TARGET_SOURCES:
            return self._show_local_sources(json_output, pretty)
        if target == SHOW_TARGET_CAN_MAPPINGS:
            if not self._ensure_can_mappings_loaded():
                return StatusResult(code=SS__CONFIG__NOT_LOADED)
            return self._show_local_mappings(tokens, json_output, pretty)
        if target == SHOW_TARGET_WORKSPACE:
            return self._show_workspace(json_output, pretty)
        if target == SHOW_TARGET_CONTROLLERS:
            return self._show_controllers(json_output, pretty)
        if target == SHOW_TARGET_ACTIVE:
            return self._show_active_local(json_output, pretty)
        if target == SHOW_TARGET_INSTANTIATED:
            return self._show_instantiated_local(json_output, pretty)
        if target == SHOW_TARGET_FAULTS:
            return self._show_faults_local(json_output, pretty)
        if target == SHOW_TARGET_MESSAGE_LEVEL:
            if self._show_message_level(json_output, pretty):
                return StatusResult(code=SS__NORMAL)
            return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
        if not self._local_config:
            print(MESSAGE_ERR_LOCAL_CONFIG_MISSING)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        if target == SHOW_TARGET_COMMANDS:
            return self._show_commands(json_output, pretty)
        if target == SHOW_TARGET_HELP:
            return self._show_help_topics(json_output, pretty)
        if target == SHOW_TARGET_DEVICE_USAGE:
            name = tokens[COUNT_ONE] if len(tokens) >= COUNT_TWO else EMPTY_STRING
            return self._show_device_usage(name, json_output, pretty)
        if target == SHOW_TARGET_SIGNALS:
            return self._show_local_signals(json_output, pretty)
        if target == SHOW_TARGET_SIGNAL:
            name = tokens[COUNT_ONE] if len(tokens) >= COUNT_TWO else EMPTY_STRING
            return self._show_local_signal_device(name, json_output, pretty)
        if target == SHOW_TARGET_CONFIG_RAW:
            return self._show_local_config_raw(json_output, pretty)
        if target == SHOW_TARGET_CONFIG_DIRTY:
            return self._show_local_config_dirty(json_output, pretty)
        if target == SHOW_TARGET_PROFILES:
            return self._show_local_profiles(json_output, pretty)
        if target == SHOW_TARGET_PROFILE:
            name = tokens[1] if len(tokens) >= 2 else ""
            return self._show_local_profile(name, json_output, pretty)
        if target == SHOW_TARGET_DEVICE:
            name = tokens[1] if len(tokens) >= 2 else ""
            return self._show_local_registry_device(name, json_output, pretty)
        if target == SHOW_TARGET_DEVICES:
            show_all = any(tok.lower() == SHOW_FLAG_ALL for tok in tokens[1:])
            if show_all:
                return self._show_local_registry_devices(json_output, pretty)
        if target == SHOW_TARGET_TOPOLOGY:
            return self._show_local_topology(tokens, json_output, pretty, grouped)
        if target == SHOW_TARGET_NEIGHBORS:
            return self._show_local_neighbors(tokens, json_output, pretty)
        profile = self._active_profile_name()
        if not profile:
            print(MESSAGE_ERR_PROFILE_REQUIRED)
            return StatusResult(code=SS__CONFIG__PROFILE_REQUIRED)
        if target == SHOW_TARGET_GROUP and len(tokens) >= COUNT_TWO and self._is_active_group(tokens[1]):
            ok = True
            error = None
            payload = self._active_group_payload()
        else:
            ok, error, payload = local_show_data(
                target, tokens, self._local_config, profile, self._local_root_payload, self._can_mappings
            )
        if not ok:
            print(f"ERROR: {error}")
            print(MESSAGE_HINT_PREFIX + MESSAGE_HINT_SHOW)
            return StatusResult(code=SS__CONFIG__INVALID)
        groups = (
            payload.get(KEY_BRIDGE_GROUPS, [])
            if isinstance(payload.get(KEY_BRIDGE_GROUPS), list)
            else []
        )
        active_group_payload = self._active_group_payload()
        selected = (
            payload.get(KEY_BRIDGE_SELECTED_DEVICE)
            if isinstance(payload.get(KEY_BRIDGE_SELECTED_DEVICE), dict)
            else {}
        )
        selected_device = str(selected.get(KEY_DEVICE, EMPTY_STRING)).strip()
        selected_enabled = bool(selected.get(KEY_ENABLED, False))
        profile_name = str(payload.get(KEY_PROFILE, profile)).strip()

        def _print_local(payload_text: str, payload_json: Optional[Dict[str, object]]) -> None:
            print(MESSAGE_SOURCE_LOCAL)
            if json_output and payload_json is not None:
                print(self._dump_json(payload_json, pretty))
            else:
                print(payload_text.rstrip())

        if target == SHOW_TARGET_STATUS:
            build_value = str(payload.get(KEY_BUILD, EMPTY_STRING))
            enabled_value = str(bool(payload.get(KEY_ENABLED, False))).lower()
            estopped_value = str(bool(payload.get(KEY_ESTOPPED, False))).lower()
            mode_value = str(payload.get(KEY_MODE, EMPTY_STRING))
            group_count = len(groups) + COUNT_ONE
            selected_label = selected_device or TEXT_STATUS_NONE
            selected_state = TEXT_STATUS_ON if selected_enabled else TEXT_STATUS_OFF
            payload_status = dict(payload)
            payload_status[KEY_GROUP_COUNT] = group_count
            text = SEP_NEWLINE.join(
                [
                    TEXT_STATUS_HEADER,
                    TEXT_STATUS_BUILD.format(value=build_value),
                    TEXT_STATUS_PROFILE.format(value=profile_name or TEXT_STATUS_NONE),
                    TEXT_STATUS_ENABLED.format(value=enabled_value),
                    TEXT_STATUS_ESTOPPED.format(value=estopped_value),
                    TEXT_STATUS_MODE.format(value=mode_value),
                    TEXT_STATUS_GROUPS.format(value=group_count),
                    TEXT_STATUS_SELECTED.format(device=selected_label, state=selected_state),
                ]
            )
            _print_local(text, payload_status)
            return StatusResult(code=SS__NORMAL)

        if target == SHOW_TARGET_GROUPS:
            lines = []
            active_group_resolved = self._resolved_local_group_payload(
                active_group_payload,
                scope_active=False,
                binding_count=COUNT_ZERO,
            )
            groups_payload = [active_group_resolved]
            lines.append(
                TEXT_GROUPS_ENTRY.format(
                    name=GROUP_NAME_ACTIVE,
                    state=TEXT_ENABLED,
                    members=active_group_resolved.get(KEY_MEMBER_COUNT, COUNT_ZERO),
                    bindings=COUNT_ZERO,
                )
            )
            for group in groups:
                if not isinstance(group, dict):
                    continue
                group_name = str(group.get(KEY_NAME, EMPTY_STRING)).strip()
                source_group = self._find_named_local_group(group_name) or group
                bindings = len(source_group.get(KEY_BRIDGE_BINDINGS, []) or [])
                resolved_payload = self._resolved_local_group_payload(
                    source_group,
                    scope_active=False,
                    binding_count=bindings,
                )
                name = str(resolved_payload.get(KEY_NAME, EMPTY_STRING)).strip()
                enabled = bool(resolved_payload.get(KEY_ENABLED, True))
                members = resolved_payload.get(KEY_MEMBER_COUNT, COUNT_ZERO)
                state = TEXT_ENABLED if enabled else TEXT_DISABLED
                lines.append(
                    TEXT_GROUPS_ENTRY.format(
                        name=name,
                        state=state,
                        members=members,
                        bindings=bindings,
                    )
                )
                groups_payload.append(resolved_payload)
            if not lines:
                _print_local(TEXT_GROUPS_NONE, {KEY_BRIDGE_GROUPS: groups_payload})
                return StatusResult(code=SS__NORMAL)
            lines.insert(0, TEXT_GROUPS_HEADER)
            _print_local("\n".join(lines), {KEY_BRIDGE_GROUPS: groups_payload})
            return StatusResult(code=SS__NORMAL)

        if target == SHOW_TARGET_GROUP and len(tokens) >= 2:
            name = tokens[1]
            if self._is_active_group(name):
                match = active_group_payload
            else:
                match = payload if isinstance(payload, dict) else {}
            bindings = match.get(KEY_BRIDGE_BINDINGS, []) or []
            resolved_payload = self._resolved_local_group_payload(
                match,
                scope_active=False,
                binding_count=len(bindings),
            )
            members = resolved_payload.get(KEY_MEMBERS, []) or []
            lines = [
                TEXT_GROUP_HEADER.format(
                    name=name,
                    state=TEXT_ENABLED if resolved_payload.get(KEY_ENABLED, True) else TEXT_DISABLED,
                ),
            ]
            lines.append(TEXT_GROUP_MEMBERS_HEADER)
            if members:
                for member in members:
                    device = (
                        str(member.get(KEY_LABEL, EMPTY_STRING)).strip()
                        if isinstance(member, dict)
                        else EMPTY_STRING
                    )
                    enabled = bool(member.get(KEY_ENABLED, True)) if isinstance(member, dict) else True
                    if device:
                        state = TEXT_ENABLED if enabled else TEXT_DISABLED
                        lines.append(f"  {device} [{state}]")
            else:
                lines.append(TEXT_GROUP_NONE)
            lines.append(TEXT_GROUP_BINDINGS_HEADER)
            if bindings:
                for binding in bindings:
                    if not isinstance(binding, dict):
                        continue
                    if KEY_VALUE in binding:
                        lines.append(
                            TEXT_BINDING_ENTRY_VALUE.format(
                                input=binding.get(KEY_INPUT),
                                kind=binding.get(KEY_KIND),
                                value=binding.get(KEY_VALUE),
                            )
                        )
                    else:
                        lines.append(
                            TEXT_BINDING_ENTRY.format(
                                input=binding.get(KEY_INPUT),
                                kind=binding.get(KEY_KIND),
                            )
                        )
            else:
                lines.append(TEXT_GROUP_NONE)
            _print_local(SEP_NEWLINE.join(lines), resolved_payload)
            return StatusResult(code=SS__NORMAL)

        if target == SHOW_TARGET_DEVICES:
            devices_raw = payload.get(KEY_DEVICES)
            lines = [TEXT_DEVICES_HEADER]
            if isinstance(devices_raw, list) and devices_raw:
                for device in devices_raw:
                    if not isinstance(device, dict):
                        continue
                    label = str(device.get(KEY_LABEL, EMPTY_STRING)).strip()
                    if not label:
                        continue
                    vendor = str(device.get(KEY_VENDOR, EMPTY_STRING)).strip()
                    dev_type = str(device.get(KEY_TYPE, EMPTY_STRING)).strip()
                    dev_id = device.get(KEY_ID, EMPTY_STRING)
                    lines.append(
                        TEXT_DEVICES_LIST_PREFIX
                        + TEXT_DEVICE_ENTRY.format(
                            label=label,
                            vendor=vendor,
                            type=dev_type,
                            id=dev_id,
                        )
                    )
            else:
                lines = [TEXT_DEVICES_NONE]
            _print_local("\n".join(lines), payload)
            return StatusResult(code=SS__NORMAL)

        if target == SHOW_TARGET_DEVICE_GROUP and len(tokens) >= 2:
            name = tokens[1]
            device_payload = payload if isinstance(payload, dict) else {}
            label = str(device_payload.get(KEY_LABEL, EMPTY_STRING)).strip()
            if label:
                vendor = str(device_payload.get(KEY_VENDOR, EMPTY_STRING)).strip()
                dev_type = str(device_payload.get(KEY_TYPE, EMPTY_STRING)).strip()
                dev_id = device_payload.get(KEY_ID, EMPTY_STRING)
                text = (
                    TEXT_DEVICE_PREFIX
                    + TEXT_DEVICE_ENTRY.format(
                        label=label,
                        vendor=vendor,
                        type=dev_type,
                        id=dev_id,
                    )
                )
                _print_local(text, payload)
                return StatusResult(code=SS__NORMAL)
            print(MESSAGE_ERR_LOCAL_DEVICE_NOT_FOUND)
            return StatusResult(code=SS__DEVICE__NOT_FOUND)

        if target == SHOW_TARGET_BINDINGS:
            show_all = any(tok.lower() == SHOW_FLAG_ALL for tok in tokens[1:])
            if show_all:
                tokens = [tok for tok in tokens if tok.lower() != SHOW_FLAG_ALL]
            global_payload = None
            if show_all:
                if self._ensure_bindings_loaded() and isinstance(self._bindings_payload, dict):
                    global_payload = self._bindings_payload
            if not groups:
                _print_local(TEXT_BINDINGS_NONE, payload)
                return StatusResult(code=SS__NORMAL)
            lines = [TEXT_BINDINGS_HEADER]
            for group in groups:
                if not isinstance(group, dict):
                    continue
                name = str(group.get(KEY_NAME, EMPTY_STRING)).strip()
                lines.append(TEXT_BINDINGS_GROUP.format(name=name))
                bindings = group.get(KEY_BRIDGE_BINDINGS, []) or []
                if not bindings:
                    lines.append(TEXT_BINDINGS_GROUP_NONE)
                    continue
                for binding in bindings:
                    if not isinstance(binding, dict):
                        continue
                    if KEY_VALUE in binding:
                        lines.append(
                            TEXT_BINDING_ENTRY_VALUE.format(
                                input=binding.get(KEY_INPUT),
                                kind=binding.get(KEY_KIND),
                                value=binding.get(KEY_VALUE),
                            )
                        )
                    else:
                        lines.append(
                            TEXT_BINDING_ENTRY.format(
                                input=binding.get(KEY_INPUT),
                                kind=binding.get(KEY_KIND),
                            )
                        )
            payload_json = payload
            if show_all:
                lines.append(MESSAGE_BINDINGS_GLOBAL_HEADER)
                if not isinstance(global_payload, dict):
                    lines.append(MESSAGE_BINDINGS_GLOBAL_UNAVAILABLE)
                else:
                    controllers = global_payload.get(KEY_CONTROLLERS, [])
                    bindings = global_payload.get(KEY_BINDINGS, [])
                    lines.append(MESSAGE_BINDINGS_CONTROLLERS_HEADER)
                    if not isinstance(controllers, list) or not controllers:
                        lines.append(MESSAGE_BINDINGS_NONE)
                    else:
                        for entry in controllers:
                            if not isinstance(entry, dict):
                                continue
                            name = str(entry.get(KEY_NAME, "")).strip()
                            ctrl_type = str(entry.get(FIELD_TYPE, "")).strip()
                            port = entry.get(KEY_PORT)
                            if name:
                                lines.append(
                                    MESSAGE_BINDINGS_CONTROLLER_FMT.format(
                                        name=name, type=ctrl_type, port=port
                                    )
                                )
                    lines.append(MESSAGE_BINDINGS_BINDINGS_HEADER)
                    if not isinstance(bindings, list) or not bindings:
                        lines.append(MESSAGE_BINDINGS_NONE)
                    else:
                        for idx, entry in enumerate(bindings, start=COUNT_ONE):
                            if not isinstance(entry, dict):
                                continue
                            line = MESSAGE_BINDINGS_BINDING_FMT.format(
                                index=idx,
                                command=entry.get(KEY_COMMAND),
                                controller=entry.get(KEY_CONTROLLER),
                                input=entry.get(KEY_INPUT),
                                id=entry.get(KEY_ID),
                                mode=entry.get(KEY_MODE),
                            )
                            if self._binding_entry_is_axis(entry):
                                line += f" invert={entry.get(KEY_INVERT)} deadband={entry.get(KEY_DEADBAND)}"
                            lines.append(line)
                payload_json = dict(payload)
                payload_json[KEY_GLOBAL_BINDINGS] = (
                    {
                        KEY_CONTROLLERS: global_payload.get(KEY_CONTROLLERS, [])
                        if isinstance(global_payload, dict)
                        else [],
                        KEY_BINDINGS: global_payload.get(KEY_BINDINGS, [])
                        if isinstance(global_payload, dict)
                        else [],
                    }
                    if isinstance(global_payload, dict)
                    else None
                )
            _print_local("\n".join(lines), payload_json)
            return StatusResult(code=SS__NORMAL)

        if target == SHOW_TARGET_SELECTED_DEVICE:
            selected_device = str(payload.get(KEY_DEVICE, EMPTY_STRING)).strip()
            selected_enabled = bool(payload.get(KEY_ENABLED, False))
            device_text = selected_device or TEXT_STATUS_NONE
            state = TEXT_STATUS_ON if selected_enabled else TEXT_STATUS_OFF
            text = (
                TEXT_SELECTED_DEVICE_PREFIX
                + device_text
                + TEXT_PAREN_OPEN
                + state
                + TEXT_PAREN_CLOSE
            )
            _print_local(text, payload)
            return StatusResult(code=SS__NORMAL)

        if target == SHOW_TARGET_RUNTIME:
            selected = (
                payload.get(KEY_BRIDGE_SELECTED_DEVICE)
                if isinstance(payload.get(KEY_BRIDGE_SELECTED_DEVICE), dict)
                else {}
            )
            selected_device = str(selected.get(KEY_DEVICE, EMPTY_STRING)).strip()
            selected_enabled = bool(selected.get(KEY_ENABLED, False))
            build_value = str(payload.get(KEY_BUILD, EMPTY_STRING))
            enabled_value = str(bool(payload.get(KEY_ENABLED, False))).lower()
            estopped_value = str(bool(payload.get(KEY_ESTOPPED, False))).lower()
            mode_value = str(payload.get(KEY_MODE, EMPTY_STRING))
            group_count = len(groups) + COUNT_ONE
            selected_label = selected_device or TEXT_STATUS_NONE
            selected_state = TEXT_STATUS_ON if selected_enabled else TEXT_STATUS_OFF
            payload_runtime = dict(payload)
            payload_runtime[KEY_GROUP_COUNT] = group_count
            resolved_runtime_groups = [
                self._resolved_local_group_payload(
                    active_group_payload,
                    scope_active=False,
                    binding_count=COUNT_ZERO,
                )
            ]
            for group in groups:
                if not isinstance(group, dict):
                    continue
                resolved_runtime_groups.append(
                    self._resolved_local_group_payload(
                        group,
                        scope_active=False,
                        binding_count=len(group.get(KEY_BRIDGE_BINDINGS, []) or []),
                    )
                )
            payload_runtime[KEY_BRIDGE_GROUPS] = resolved_runtime_groups
            status_lines = [
                TEXT_STATUS_HEADER,
                TEXT_STATUS_BUILD.format(value=build_value),
                TEXT_STATUS_PROFILE.format(value=profile_name or TEXT_STATUS_NONE),
                TEXT_STATUS_ENABLED.format(value=enabled_value),
                TEXT_STATUS_ESTOPPED.format(value=estopped_value),
                TEXT_STATUS_MODE.format(value=mode_value),
                TEXT_STATUS_GROUPS.format(value=group_count),
                TEXT_STATUS_SELECTED.format(device=selected_label, state=selected_state),
            ]
            group_lines = []
            if not groups:
                group_lines.append(TEXT_GROUPS_NONE)
            else:
                group_lines.append(TEXT_GROUPS_HEADER)
                active_group_resolved = resolved_runtime_groups[COUNT_ZERO]
                group_lines.append(
                    TEXT_GROUPS_ENTRY.format(
                        name=GROUP_NAME_ACTIVE,
                        state=TEXT_ENABLED,
                        members=active_group_resolved.get(KEY_MEMBER_COUNT, COUNT_ZERO),
                        bindings=COUNT_ZERO,
                    )
                )
                for group in resolved_runtime_groups[COUNT_ONE:]:
                    name = str(group.get(KEY_NAME, EMPTY_STRING)).strip()
                    enabled = bool(group.get(KEY_ENABLED, True))
                    members = int(group.get(KEY_MEMBER_COUNT, COUNT_ZERO))
                    bindings = int(group.get(KEY_BINDING_COUNT, COUNT_ZERO))
                    group_lines.append(
                        TEXT_GROUPS_ENTRY.format(
                            name=name,
                            state=TEXT_ENABLED if enabled else TEXT_DISABLED,
                            members=members,
                            bindings=bindings,
                        )
                    )
            _print_local(SEP_NEWLINE.join(status_lines + [""] + group_lines), payload_runtime)
            return StatusResult(code=SS__NORMAL)

        print("ERROR: Unknown show command.")
        return StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX)

    def _show_local_config_dirty(self, json_output: bool, pretty: bool) -> StatusResult:
        """
        NAME
            _show_local_config_dirty - Show local dirty flags.
        """

        dirty = self._dirty_state()
        print(MESSAGE_SOURCE_LOCAL)
        if json_output:
            print(self._dump_json({KEY_DIRTY: dirty}, pretty))
            return StatusResult(code=SS__NORMAL)
        print(MESSAGE_DIRTY_HEADER)
        any_dirty = False
        for name in sorted(dirty.keys()):
            value = dirty[name]
            if value:
                any_dirty = True
            print(MESSAGE_DIRTY_ENTRY.format(name=name, value=str(value).lower()))
        print(
            MESSAGE_DIRTY_LAST_MODIFIED.format(
                value=self._format_provenance_value(self._last_modified_at)
            )
        )
        print(
            MESSAGE_DIRTY_LAST_SAVED.format(
                value=self._format_provenance_value(
                    self._last_saved_at,
                    path=self._last_saved_path,
                    hash_value=self._last_saved_hash,
                )
            )
        )
        print(
            MESSAGE_DIRTY_LAST_PUSHED.format(
                value=self._format_provenance_value(
                    self._last_pushed_at,
                    path=self._last_pushed_path,
                    hash_value=self._last_pushed_hash,
                    profile_name=self._last_pushed_profile,
                )
            )
        )
        if not any_dirty:
            print(MESSAGE_DIRTY_NONE)
        return StatusResult(code=SS__NORMAL)

    def _show_local_version(self, json_output: bool, pretty: bool) -> StatusResult:
        """
        NAME
            _show_local_version - Show local app version information.
        """
        version = VERSIONS.get(VERSION_APP_NAME, EMPTY_STRING)
        payload = {KEY_VERSION: version, KEY_BUILD: build_info_payload()}
        print(MESSAGE_SOURCE_LOCAL)
        if json_output:
            print(self._dump_json(payload, pretty))
            return StatusResult(code=SS__NORMAL)
        if not version:
            print(MESSAGE_VERSION_NONE)
            return StatusResult(code=SS__NORMAL)
        print(TEXT_VERSION_PREFIX + version)
        print(TEXT_BUILD_HEADER)
        for line in build_lines():
            print(line)
        return StatusResult(code=SS__NORMAL)

    def _show_local_sources(self, json_output: bool, pretty: bool) -> StatusResult:
        """
        NAME
            _show_local_sources - Show local file sources for loaded data.
        """

        entries = self._collect_sources()
        print(MESSAGE_SOURCE_LOCAL)
        if json_output:
            print(self._dump_json({KEY_SOURCES: entries}, pretty))
            return StatusResult(code=SS__NORMAL)
        print(TEXT_SOURCES_HEADER)
        for entry in entries:
            name = str(entry.get(KEY_SOURCES_NAME, EMPTY_STRING))
            path = str(entry.get(KEY_SOURCES_PATH, EMPTY_STRING))
            exists = str(bool(entry.get(KEY_SOURCES_EXISTS, False))).lower()
            print(TEXT_SOURCES_ENTRY.format(name=name, path=path, exists=exists))
        print(TEXT_SOURCES_FOOTER)
        return StatusResult(code=SS__NORMAL)

    def _collect_sources(self) -> List[Dict[str, object]]:
        """
        NAME
            _collect_sources - Collect local source info for CLI data.
        """
        def source_entry(name: str, path: object, loaded: bool) -> Dict[str, object]:
            source_path = Path(path) if path else None
            exists = bool(source_path is not None and source_path.exists())
            if loaded and source_path is not None:
                status = SOURCE_STATUS_LOADED
            elif source_path is None:
                status = SOURCE_STATUS_UNKNOWN
            else:
                status = SOURCE_STATUS_NOT_LOADED
            return {
                KEY_SOURCE_NAME: name,
                KEY_SOURCE_PATH: str(source_path) if source_path is not None else EMPTY_STRING,
                KEY_SOURCES_EXISTS: exists,
                KEY_SOURCE_STATUS: status,
            }

        root_loaded = bool(self._local_root_payload)
        return [
            source_entry(SOURCE_NAME_REGISTRY, self._local_root_path, root_loaded),
            source_entry(SOURCE_NAME_CONFIG, self._local_root_path, bool(self._local_config)),
            source_entry(SOURCE_NAME_BINDINGS, self._bindings_path, bool(self._bindings_payload)),
            source_entry(SOURCE_NAME_CAN_MAPPINGS, self._can_mappings_path, bool(self._can_mappings)),
            source_entry(SOURCE_NAME_TESTS, self._local_root_path, self._tests_model is not None),
        ]

    @staticmethod
    def _source_display_value(entry: Dict[str, object]) -> str:
        """
        NAME
            _source_display_value - Build display text for a source entry.
        """

        path = str(entry.get(KEY_SOURCES_PATH, EMPTY_STRING))
        exists = bool(entry.get(KEY_SOURCES_EXISTS, False))
        return SOURCE_DISPLAY_FMT.format(path=path, exists=str(exists).lower())

    def _show_local_profiles(self, json_output: bool, pretty: bool) -> StatusResult:
        """
        NAME
            _show_local_profiles - Show local profile summary.
        """
        return self._show_local_profile(EMPTY_STRING, json_output, pretty)

    def _show_local_profile(self, name: str, json_output: bool, pretty: bool) -> StatusResult:
        """
        NAME
            _show_local_profile - Show profile summary info.
        """
        payload = self._local_root_payload
        profiles = payload.get(KEY_PROFILES) if isinstance(payload, dict) else {}
        names = [name for name in profiles.keys() if isinstance(name, str)] if isinstance(profiles, dict) else []
        active = self._host_profile_context_name() or ""
        selected_context = self._host_profile_context_name() or ""
        default_profile = self._default_profile_name() or ""
        selected = name.strip() if name else ""
        if selected:
            if not isinstance(profiles, dict) or selected not in profiles:
                print(MESSAGE_ERR_PROFILE_NOT_FOUND)
                return StatusResult(code=SS__CONFIG__PROFILE_REQUIRED)
            profile = profiles.get(selected)
            labels = profile.get(KEY_PROFILE_DEVICES) if isinstance(profile, dict) else []
            device_labels = [label for label in labels if isinstance(label, str)]
            output = {KEY_PROFILE: selected, KEY_PROFILE_DEVICES: sorted(device_labels)}
            print(MESSAGE_SOURCE_LOCAL)
            if json_output:
                print(self._dump_json(output, pretty))
                return StatusResult(code=SS__NORMAL)
            print(MESSAGE_LOCAL_PROFILE_HEADER)
            print(MESSAGE_LOCAL_PROFILE_NAME.format(name=selected))
            print(MESSAGE_LOCAL_PROFILE_DEVICES_HEADER.format(count=len(device_labels)))
            for label in device_labels:
                print(MESSAGE_LOCAL_PROFILE_DEVICE_FMT.format(label=label))
            return StatusResult(code=SS__NORMAL)
        count = len(names)
        output = {
            KEY_ACTIVE: active,
            KEY_SELECTED: selected_context,
            KEY_ACTIVE_RUNTIME: EMPTY_STRING,
            KEY_RUNTIME_ACTIVE: False,
            KEY_DEFAULT: default_profile,
            KEY_AVAILABLE: sorted(names),
        }
        print(MESSAGE_SOURCE_LOCAL)
        if json_output:
            print(self._dump_json({KEY_PROFILE_INFO: output}, pretty))
            return StatusResult(code=SS__NORMAL)
        print(MESSAGE_LOCAL_PROFILE_HEADER)
        print(MESSAGE_LOCAL_PROFILE_ACTIVE.format(name=active or STRING_NONE))
        print(MESSAGE_LOCAL_PROFILE_SELECTED.format(name=selected_context or STRING_NONE))
        print(MESSAGE_LOCAL_PROFILE_ACTIVE_RUNTIME.format(name=STRING_NONE))
        print(MESSAGE_LOCAL_PROFILE_RUNTIME_ACTIVE.format(value="false"))
        print(MESSAGE_LOCAL_PROFILE_DEFAULT.format(name=default_profile or STRING_NONE))
        print(MESSAGE_LOCAL_PROFILE_AVAILABLE.format(count=count))
        for profile_name in sorted(names):
            print(MESSAGE_LOCAL_PROFILE_DEVICE_FMT.format(label=profile_name))
        return StatusResult(code=SS__NORMAL)

    def _show_local_config_raw(self, json_output: bool, pretty: bool) -> StatusResult:
        """
        NAME
            _show_local_config_raw - Show raw local bridgeConfig content.
        """
        if not self._local_config:
            print(MESSAGE_ERR_LOCAL_CONFIG_MISSING)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        payload = self._ordered_bridge_config(self._local_config)
        print(MESSAGE_SOURCE_LOCAL)
        if json_output:
            print(self._dump_json(payload, pretty))
            return StatusResult(code=SS__NORMAL)
        print(MESSAGE_LOCAL_CONFIG_RAW)
        print(json.dumps(payload, indent=JSON_PRETTY_INDENT))
        return StatusResult(code=SS__NORMAL)

    def _show_local_mappings(
        self, tokens: List[str], json_output: bool, pretty: bool
    ) -> StatusResult:
        """
        NAME
            _show_local_mappings - Show CAN mappings via show can-mappings.
        """

        if not isinstance(self._can_mappings, dict):
            print(MESSAGE_ERR_MAPPINGS_LOAD.format(path=EMPTY_STRING))
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        target = tokens[COUNT_ONE].lower() if len(tokens) >= COUNT_TWO else EMPTY_STRING
        if target == MAPPINGS_SHOW_DEVICE_TYPE:
            target = MAPPINGS_SHOW_DEVICE_TYPES
        manufacturers = self._can_mappings.get(KEY_MANUFACTURERS, {})
        device_types = self._can_mappings.get(KEY_DEVICE_TYPES, {})
        print(MESSAGE_SOURCE_LOCAL)
        if json_output:
            if target == MAPPINGS_SHOW_MANUFACTURERS:
                print(self._dump_json({KEY_MANUFACTURERS: manufacturers}, pretty))
                return StatusResult(code=SS__NORMAL)
            if target == MAPPINGS_SHOW_DEVICE_TYPES:
                print(self._dump_json({KEY_DEVICE_TYPES: device_types}, pretty))
                return StatusResult(code=SS__NORMAL)
            print(self._dump_json(self._can_mappings, pretty))
            return StatusResult(code=SS__NORMAL)
        if target and target not in MAPPINGS_SHOW_TARGETS:
            print(MESSAGE_ERR_MAPPINGS_SHOW)
            return StatusResult(code=SS__CLI_PARSER__UNKNOWN_COMMAND)
        print(MESSAGE_MAPPINGS_HEADER)
        if target in (EMPTY_STRING, MAPPINGS_SHOW_MANUFACTURERS):
            print(MESSAGE_MAPPINGS_MANUFACTURERS_HEADER)
            self._print_mappings_entries(manufacturers)
            if target == MAPPINGS_SHOW_MANUFACTURERS:
                return StatusResult(code=SS__NORMAL)
        if target in (EMPTY_STRING, MAPPINGS_SHOW_DEVICE_TYPES):
            print(MESSAGE_MAPPINGS_DEVICE_TYPES_HEADER)
            self._print_mappings_entries(device_types)
        return StatusResult(code=SS__NORMAL)

    def _group_command_local(self, tokens: List[str], group: str) -> StatusResult:
        if not self._local_config:
            print("ERROR: Local config not loaded. Use merge/import config <bringup_system.json>.")
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        cmd = tokens[0].lower()
        if cmd == CMD_BIND and len(tokens) >= COUNT_TWO:
            action = tokens[COUNT_ONE].lower()
            if action in (CMD_LIST, CMD_EXPLAIN, CMD_TEST):
                return self._coerce_status(self._handle_group_bind_diagnostics(group, tokens))
        if cmd == "show":
            return self._coerce_status(self._handle_show(["group", group] + tokens[1:]))
        if cmd == "add" and len(tokens) >= 3 and tokens[1].lower() == "device":
            result = self._add_local_group_member(group, tokens[2])
            if result.ok():
                self._warn("WARNING: Robot not connected; local group member added.")
                return StatusResult(code=SS__NETWORK__NOT_CONNECTED)
            return result
        if cmd == "no" and len(tokens) >= 3 and tokens[1].lower() == "device":
            result = self._remove_local_group_member(group, tokens[2])
            if result.ok():
                self._warn("WARNING: Robot not connected; local group member removed.")
                return StatusResult(code=SS__NETWORK__NOT_CONNECTED)
            return result
        if cmd == "member" and len(tokens) >= 3:
            action = tokens[2].lower()
            if action in ("enable", "disable", "toggle"):
                result = self._set_local_member_enabled(group, tokens[1], action)
                if result.ok():
                    self._warn("WARNING: Robot not connected; local member updated.")
                    return StatusResult(code=SS__NETWORK__NOT_CONNECTED)
                return result
        if cmd == "bind" and len(tokens) >= 3:
            result = self._add_local_binding(group, tokens[1:])
            if result.ok():
                self._warn("WARNING: Robot not connected; local binding updated.")
                return StatusResult(code=SS__NETWORK__NOT_CONNECTED)
            return result
        if cmd == "no" and len(tokens) >= 2 and tokens[1].lower() == "bind":
            result = self._clear_local_bindings(group)
            if result.ok():
                self._warn("WARNING: Robot not connected; local bindings cleared.")
                return StatusResult(code=SS__NETWORK__NOT_CONNECTED)
            return result
        if cmd == "enable":
            result = self._set_local_group_enabled(group, True)
            if result.ok():
                self._warn("WARNING: Robot not connected; local group enabled.")
                return StatusResult(code=SS__NETWORK__NOT_CONNECTED)
            return result
        if cmd == "disable":
            result = self._set_local_group_enabled(group, False)
            if result.ok():
                self._warn("WARNING: Robot not connected; local group disabled.")
                return StatusResult(code=SS__NETWORK__NOT_CONNECTED)
            return result
        if cmd == CMD_CLEAR:
            result = self._clear_local_group_members(group)
            if result.ok():
                self._warn(WARN_LOCAL_GROUP_CLEARED)
                return StatusResult(code=SS__NETWORK__NOT_CONNECTED)
            return result
        if cmd == "run" and len(tokens) >= 2 and tokens[1].lower() == "test":
            print("ERROR: Cannot run tests without robot connection.")
            return StatusResult(code=SS__NETWORK__ROBOT_UNAVAILABLE)
        print(f"ERROR: Unknown command: {' '.join(tokens)}")
        return StatusResult(code=SS__CLI_PARSER__UNKNOWN_COMMAND)

    def _handle_group_bind_diagnostics(self, group_name: str, tokens: List[str]) -> StatusResult:
        """
        NAME
            _handle_group_bind_diagnostics - Inspect current-group bindings.
        """
        if len(tokens) < COUNT_TWO:
            print(ERR_BIND_EXPLAIN_USAGE)
            return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
        action = tokens[COUNT_ONE].lower()
        diagnostics = self._evaluate_group_bindings(group_name)
        if action == CMD_LIST:
            print(TEXT_BIND_LIST_HEADER)
            if not diagnostics:
                print(TEXT_BIND_LIST_NONE)
                return StatusResult(code=SS__NORMAL)
            for diag in diagnostics:
                value = diag[KEY_VALUE]
                value_text = (
                    TEXT_BIND_VALUE_PREFIX + str(value)
                    if value is not None
                    else EMPTY_STRING
                )
                print(
                    TEXT_BIND_LIST_ENTRY.format(
                        index=diag["index"],
                        input=diag[KEY_INPUT],
                        kind=diag[KEY_KIND],
                        value=value_text,
                        status=diag[KEY_STATUS],
                        reason=diag[KEY_REASON],
                    )
                )
            return StatusResult(code=SS__NORMAL)
        if action == CMD_EXPLAIN:
            if len(tokens) < COUNT_THREE:
                print(ERR_BIND_EXPLAIN_USAGE)
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            diag = self._select_group_binding_diagnostic(diagnostics, tokens[COUNT_TWO])
            if diag is None:
                print(ERR_BIND_NOT_FOUND)
                return StatusResult(code=SS__GROUP__BINDING_INVALID)
            self._print_group_binding_diagnostic(diag)
            return StatusResult(code=SS__NORMAL)
        if action == CMD_TEST:
            if len(tokens) < COUNT_THREE:
                print(ERR_BIND_TEST_USAGE)
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            diag = self._select_group_binding_diagnostic(diagnostics, tokens[COUNT_TWO])
            if diag is None:
                print(ERR_BIND_NOT_FOUND)
                return StatusResult(code=SS__GROUP__BINDING_INVALID)
            self._print_group_binding_diagnostic(diag)
            if diag[KEY_STATUS] == BIND_DIAG_STATUS_ACTIVE:
                print(TEXT_BIND_TEST_PASS)
                return StatusResult(code=SS__NORMAL)
            print(TEXT_BIND_TEST_FAIL)
            return StatusResult(code=SS__CONFIG__INVALID)
        print(f"ERROR: Unknown command: {' '.join(tokens)}")
        return StatusResult(code=SS__CLI_PARSER__UNKNOWN_COMMAND)

    def _known_controller_names(self) -> set[str]:
        names: set[str] = set()
        if self._ensure_bindings_loaded() and isinstance(self._bindings_payload, dict):
            controllers = self._bindings_payload.get(KEY_CONTROLLERS, [])
            if isinstance(controllers, list):
                for entry in controllers:
                    if not isinstance(entry, dict):
                        continue
                    name = str(entry.get(KEY_NAME, EMPTY_STRING)).strip()
                    if name:
                        names.add(name)
        for name in load_controller_names(self._bindings_path):
            clean = str(name).strip()
            if clean:
                names.add(clean)
        return names

    def _evaluate_group_bindings(self, group_name: str) -> List[Dict[str, object]]:
        group = self._find_local_group(group_name)
        if group is None:
            return []
        bindings = group.get(KEY_BRIDGE_BINDINGS, []) or []
        resolved_payload = self._resolved_local_group_payload(
            group,
            scope_active=self._is_active_group(group_name),
            binding_count=len(bindings) if isinstance(bindings, list) else COUNT_ZERO,
        )
        total_members = int(resolved_payload.get(KEY_MEMBER_COUNT, COUNT_ZERO))
        enabled_members = int(
            resolved_payload.get(KEY_ENABLED_MEMBER_COUNT, COUNT_ZERO)
        )
        group_enabled = bool(resolved_payload.get(KEY_ENABLED, True))
        controller_names = self._known_controller_names()
        diagnostics: List[Dict[str, object]] = []
        for index, binding in enumerate(bindings, start=COUNT_ONE):
            if not isinstance(binding, dict):
                continue
            input_name = str(binding.get(KEY_INPUT, EMPTY_STRING)).strip()
            kind = str(binding.get(KEY_KIND, EMPTY_STRING)).strip()
            value = binding.get(KEY_VALUE)
            controller_name = EMPTY_STRING
            signal_name = EMPTY_STRING
            if CONTROL_SIGNAL_SEPARATOR in input_name:
                controller_name, signal_name = input_name.split(CONTROL_SIGNAL_SEPARATOR, maxsplit=1)
            controller_found = bool(controller_name) and controller_name in controller_names
            signal_found = bool(signal_name) and signal_name in (AXIS_INPUTS | BUTTON_INPUTS)
            status = BIND_DIAG_STATUS_ACTIVE
            reason = ERR_BIND_READY_LOCAL_ONLY
            if CONTROL_SIGNAL_SEPARATOR not in input_name:
                status = BIND_DIAG_STATUS_UNRESOLVED
                reason = ERR_BIND_CONTROLLER_PREFIX
            elif not controller_found:
                status = BIND_DIAG_STATUS_UNRESOLVED
                reason = ERR_BIND_CONTROLLER_MISSING
            elif not signal_found:
                status = BIND_DIAG_STATUS_UNRESOLVED
                reason = ERR_BIND_SIGNAL_MISSING
            elif not group_enabled:
                status = BIND_DIAG_STATUS_DISABLED
                reason = ERR_BIND_GROUP_DISABLED
            elif enabled_members <= COUNT_ZERO:
                status = BIND_DIAG_STATUS_BLOCKED
                reason = ERR_BIND_NO_ENABLED_MEMBERS
            diagnostics.append(
                {
                    "index": index,
                    "group": group_name,
                    KEY_INPUT: input_name,
                    KEY_KIND: kind,
                    KEY_VALUE: value,
                    KEY_STATUS: status,
                    KEY_REASON: reason,
                    "controller": controller_name,
                    "controllerFound": controller_found,
                    "signal": signal_name,
                    "signalFound": signal_found,
                    "groupEnabled": group_enabled,
                    "enabledMembers": enabled_members,
                    "totalMembers": total_members,
                }
            )
        return diagnostics

    def _select_group_binding_diagnostic(
        self, diagnostics: List[Dict[str, object]], selector: str
    ) -> Optional[Dict[str, object]]:
        try:
            index = int(selector)
        except ValueError:
            index = COUNT_ZERO
        if index > COUNT_ZERO:
            for diag in diagnostics:
                if int(diag.get("index", COUNT_ZERO)) == index:
                    return diag
        lowered = selector.strip().lower()
        for diag in diagnostics:
            input_name = str(diag.get(KEY_INPUT, EMPTY_STRING)).strip().lower()
            if input_name == lowered:
                return diag
        return None

    def _print_group_binding_diagnostic(self, diag: Dict[str, object]) -> None:
        print(TEXT_BIND_EXPLAIN_HEADER.format(index=diag["index"]))
        print(TEXT_BIND_EXPLAIN_GROUP.format(group=diag["group"]))
        print(TEXT_BIND_EXPLAIN_INPUT.format(input=diag[KEY_INPUT]))
        print(TEXT_BIND_EXPLAIN_KIND.format(kind=diag[KEY_KIND]))
        value = diag.get(KEY_VALUE)
        print(TEXT_BIND_EXPLAIN_VALUE.format(value=value if value is not None else TEXT_BIND_VALUE_NONE))
        print(
            TEXT_BIND_EXPLAIN_CONTROLLER.format(
                controller=diag["controller"] or TEXT_BIND_VALUE_NONE,
                found=BIND_BOOL_YES if diag["controllerFound"] else BIND_BOOL_NO,
            )
        )
        print(
            TEXT_BIND_EXPLAIN_SIGNAL.format(
                signal=diag["signal"] or TEXT_BIND_VALUE_NONE,
                found=BIND_BOOL_YES if diag["signalFound"] else BIND_BOOL_NO,
            )
        )
        print(
            TEXT_BIND_EXPLAIN_GROUP_ENABLED.format(
                enabled=BIND_BOOL_YES if diag["groupEnabled"] else BIND_BOOL_NO
            )
        )
        print(
            TEXT_BIND_EXPLAIN_MEMBERS.format(
                enabled=diag["enabledMembers"],
                total=diag["totalMembers"],
            )
        )
        print(TEXT_BIND_EXPLAIN_STATUS.format(status=diag[KEY_STATUS]))
        print(TEXT_BIND_EXPLAIN_REASON.format(reason=diag[KEY_REASON]))
        print(TEXT_BIND_EXPLAIN_LAST_INPUT)
        print(TEXT_BIND_EXPLAIN_LAST_OUTPUT)

    def _select_or_create_local_group(self, name: str) -> StatusResult:
        if not self._local_config:
            print("ERROR: Local config not loaded. Use merge/import config <bringup_system.json>.")
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        profile = self._require_active_profile()
        if not profile:
            return StatusResult(code=SS__CONFIG__PROFILE_REQUIRED)
        key = name.strip()
        if not key:
            print("ERROR: group name required.")
            return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
        if self._is_active_group(key):
            return StatusResult(code=SS__NORMAL)
        groups = self._local_groups(profile, create=True)
        for group in groups:
            if isinstance(group, dict) and str(group.get("name", "")).strip().lower() == key.lower():
                return StatusResult(code=SS__NORMAL)
        conflict = self._global_name_conflict(key)
        if conflict is not None:
            print(ERR_NAME_EXISTS.format(name=key))
            return StatusResult(code=SS__CONFIG__INVALID)
        groups.append({"name": key, "enabled": True, "members": [], "bindings": []})
        self._mark_groups_dirty()
        return StatusResult(code=SS__NORMAL)

    def _delete_local_group(self, name: str) -> StatusResult:
        if not self._local_config:
            print("ERROR: Local config not loaded. Use merge/import config <bringup_system.json>.")
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        profile = self._require_active_profile()
        if not profile:
            return StatusResult(code=SS__CONFIG__PROFILE_REQUIRED)
        key = name.strip().lower()
        if self._is_active_group(key):
            print(ERR_RESERVED_ACTIVE_DELETE)
            return StatusResult(code=SS__CONFIG__INVALID)
        test_name = self._group_ref_test_name(name)
        if test_name:
            print(ERR_GROUP_REFERENCED_BY_TEST.format(name=name.strip(), test=test_name))
            return StatusResult(code=SS__CONFIG__INVALID)
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
            return StatusResult(code=SS__GROUP__NOT_FOUND)
        entry = self._local_profile_entry(profile, create=True)
        entry[KEY_BRIDGE_GROUPS] = kept
        self._mark_groups_dirty()
        return StatusResult(code=SS__NORMAL)

    def _set_local_selected_device(self, device: str) -> StatusResult:
        if not self._local_config:
            print("ERROR: Local config not loaded. Use merge/import config <bringup_system.json>.")
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        profile = self._require_active_profile()
        if not profile:
            return StatusResult(code=SS__CONFIG__PROFILE_REQUIRED)
        entry = self._local_profile_entry(profile, create=True)
        selected = entry.get(KEY_BRIDGE_SELECTED_DEVICE, {}) or {}
        enabled = bool(selected.get("enabled", False)) if isinstance(selected, dict) else False
        entry[KEY_BRIDGE_SELECTED_DEVICE] = {KEY_DEVICE: device.strip(), CMD_ENABLED: enabled}
        self._mark_groups_dirty()
        return StatusResult(code=SS__NORMAL)

    def _set_local_selected_mode(self, enabled: bool) -> StatusResult:
        if not self._local_config:
            print("ERROR: Local config not loaded. Use merge/import config <bringup_system.json>.")
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        profile = self._require_active_profile()
        if not profile:
            return StatusResult(code=SS__CONFIG__PROFILE_REQUIRED)
        entry = self._local_profile_entry(profile, create=True)
        selected = entry.get(KEY_BRIDGE_SELECTED_DEVICE, {}) or {}
        device = str(selected.get(KEY_DEVICE, "")).strip() if isinstance(selected, dict) else ""
        entry[KEY_BRIDGE_SELECTED_DEVICE] = {KEY_DEVICE: device, CMD_ENABLED: bool(enabled)}
        self._mark_groups_dirty()
        return StatusResult(code=SS__NORMAL)

    def _find_local_group(self, name: str) -> Optional[Dict[str, object]]:
        if self._is_active_group(name):
            return self._active_group_payload()
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

    def _add_local_group_member(self, group_name: str, device: str) -> StatusResult:
        if self._is_active_group(group_name):
            device_name = self._normalize_device_label_input(device)
            if not self._local_device_exists(device_name):
                print("ERROR: Device not defined in local config. Use device <device> to create it.")
                return StatusResult(code=SS__DEVICE__NOT_DEFINED)
            for existing in self._active_group_members:
                if existing.lower() == device_name.lower():
                    print(WARN_DUPLICATE_MEMBER.format(device=device_name))
                    return StatusResult(code=SS__NORMAL)
            self._active_group_members.append(device_name)
            return StatusResult(code=SS__NORMAL)
        group = self._find_local_group(group_name)
        if group is None:
            print("ERROR: Local group not found.")
            return StatusResult(code=SS__GROUP__NOT_FOUND)
        if not self._local_device_exists(device):
            print("ERROR: Device not defined in local config. Use device <device> to create it.")
            return StatusResult(code=SS__DEVICE__NOT_DEFINED)
        members = group.get("members", [])
        for member in members:
            name = _group_member_label(member)
            if name.lower() == device.lower():
                print(WARN_DUPLICATE_MEMBER.format(device=device))
                return StatusResult(code=SS__NORMAL)
        members.append(_group_member_entry(device, True))
        group["members"] = members
        self._mark_groups_dirty()
        return StatusResult(code=SS__NORMAL)

    def _remove_local_group_member(self, group_name: str, device: str) -> StatusResult:
        if self._is_active_group(group_name):
            kept = []
            removed = False
            for existing in self._active_group_members:
                if existing.lower() == device.lower():
                    removed = True
                    continue
                kept.append(existing)
            self._active_group_members = kept
            if not removed:
                print(WARN_MISSING_MEMBER.format(device=device))
            return StatusResult(code=SS__NORMAL)
        group = self._find_local_group(group_name)
        if group is None:
            print("ERROR: Local group not found.")
            return StatusResult(code=SS__GROUP__NOT_FOUND)
        members = group.get("members", [])
        kept = []
        removed = False
        for member in members:
            name = _group_member_label(member)
            if name.lower() == device.lower():
                removed = True
                continue
            kept.append(member)
        if not removed:
            print(WARN_MISSING_MEMBER.format(device=device))
            return StatusResult(code=SS__NORMAL)
        group["members"] = kept
        self._mark_groups_dirty()
        return StatusResult(code=SS__NORMAL)

    def _set_local_member_enabled(self, group_name: str, device: str, action: str) -> StatusResult:
        if self._is_active_group(group_name):
            print(ERR_ACTIVE_GROUP_MEMBERSHIP_ONLY)
            return StatusResult(code=SS__CONFIG__INVALID)
        group = self._find_local_group(group_name)
        if group is None:
            print("ERROR: Local group not found.")
            return StatusResult(code=SS__GROUP__NOT_FOUND)
        members = group.get("members", [])
        for member in members:
            if isinstance(member, dict):
                name = _group_member_label(member)
                if name.lower() == device.lower():
                    enabled = bool(member.get("enabled", True))
                    if action == "enable":
                        member["enabled"] = True
                    elif action == "disable":
                        member["enabled"] = False
                    elif action == "toggle":
                        member["enabled"] = not enabled
                    self._mark_groups_dirty()
                    return StatusResult(code=SS__NORMAL)
            elif isinstance(member, str):
                if member.strip().lower() == device.lower():
                    members.remove(member)
                    members.append(_group_member_entry(member, action != "disable"))
                    self._mark_groups_dirty()
                    return StatusResult(code=SS__NORMAL)
        print("ERROR: Label not in local group.")
        return StatusResult(code=SS__GROUP__MEMBER_MISSING)

    def _add_local_binding(self, group_name: str, tokens: List[str]) -> StatusResult:
        if self._is_active_group(group_name):
            print(ERR_ACTIVE_GROUP_MEMBERSHIP_ONLY)
            return StatusResult(code=SS__CONFIG__INVALID)
        if len(tokens) < 2:
            print("ERROR: bind requires input and kind.")
            return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
        group = self._find_local_group(group_name)
        if group is None:
            print("ERROR: Local group not found.")
            return StatusResult(code=SS__GROUP__NOT_FOUND)
        input_name = tokens[0]
        kind = tokens[1]
        entry = {"input": input_name, "kind": kind}
        if kind != "analog":
            if len(tokens) < 3:
                print("ERROR: Button bindings require a value.")
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            entry["value"] = tokens[2]
        bindings = group.get("bindings", [])
        bindings.append(entry)
        group["bindings"] = bindings
        self._mark_groups_dirty()
        return StatusResult(code=SS__NORMAL)

    def _clear_local_bindings(self, group_name: str) -> StatusResult:
        if self._is_active_group(group_name):
            print(ERR_ACTIVE_GROUP_MEMBERSHIP_ONLY)
            return StatusResult(code=SS__CONFIG__INVALID)
        group = self._find_local_group(group_name)
        if group is None:
            print("ERROR: Local group not found.")
            return StatusResult(code=SS__GROUP__NOT_FOUND)
        group["bindings"] = []
        self._mark_groups_dirty()
        return StatusResult(code=SS__NORMAL)

    def _set_local_group_enabled(self, group_name: str, enabled: bool) -> StatusResult:
        if self._is_active_group(group_name):
            print(ERR_ACTIVE_GROUP_MEMBERSHIP_ONLY)
            return StatusResult(code=SS__CONFIG__INVALID)
        group = self._find_local_group(group_name)
        if group is None:
            print("ERROR: Local group not found.")
            return StatusResult(code=SS__GROUP__NOT_FOUND)
        group["enabled"] = bool(enabled)
        self._mark_groups_dirty()
        return StatusResult(code=SS__NORMAL)

    def _clear_local_group_members(self, group_name: str) -> StatusResult:
        """
        NAME
            _clear_local_group_members - Remove all members from a local group target.
        """
        if self._is_active_group(group_name):
            self._active_group_members = []
            self._active_add_cursor = COUNT_ZERO
            return StatusResult(code=SS__NORMAL)
        group = self._find_local_group(group_name)
        if group is None:
            print("ERROR: Local group not found.")
            return StatusResult(code=SS__GROUP__NOT_FOUND)
        group[KEY_MEMBERS] = []
        self._mark_groups_dirty()
        return StatusResult(code=SS__NORMAL)

    def _rename_local_device(self, old: str, new: str) -> StatusResult:
        return self._rename_profiles_device(old, new)

    def _delete_local_device(self, name: str) -> StatusResult:
        return self._delete_profiles_device(name)

    def _delete_profiles_device(self, name: str) -> StatusResult:
        group_name = self._device_ref_group_name(name)
        if group_name:
            print(
                ERR_DEVICE_REFERENCED.format(
                    name=name.strip(),
                    kind=TARGET_KIND_GROUP,
                    ref=group_name,
                )
            )
            return StatusResult(code=SS__CONFIG__INVALID)
        test_name = self._device_ref_test_name(name)
        if test_name:
            print(ERR_DEVICE_REFERENCED.format(name=name.strip(), kind=TARGET_KIND_TEST, ref=test_name))
            return StatusResult(code=SS__CONFIG__INVALID)
        entry = self._find_profiles_device_entry(name)
        if entry is None:
            print(f"ERROR: Device {name} not found in profiles.")
            return StatusResult(code=SS__DEVICE__NOT_FOUND)
        payload = self._local_root_payload
        if not isinstance(payload, dict):
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        profiles, profile_name = self._profiles_root_and_name()
        if profiles is None or profile_name is None:
            print(MESSAGE_ERR_DEVICE_PROFILE_REQUIRED)
            return StatusResult(code=SS__CONFIG__PROFILE_REQUIRED)
        profile = profiles.get(profile_name)
        if not isinstance(profile, dict):
            print(MESSAGE_ERR_DEVICE_PROFILE_REQUIRED)
            return StatusResult(code=SS__CONFIG__PROFILE_REQUIRED)
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
            return StatusResult(code=SS__DEVICE__NOT_FOUND)
        self._mark_profiles_dirty()
        self._remove_diagram_device(entry)
        self._remove_bridge_groups_device(name)
        self._refresh_devices_from_profiles()
        return StatusResult(code=SS__NORMAL)

    def _remove_bridge_groups_device(self, name: str) -> StatusResult:
        config = self._local_config
        if not isinstance(config, dict):
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        by_profile = config.get(KEY_BRIDGE_BY_PROFILE)
        if not isinstance(by_profile, dict):
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
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
                    dev_name = _group_member_label(member)
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
        return StatusResult(code=SS__NORMAL)

    def _remove_diagram_device(self, entry: Dict[str, object]) -> None:
        payload = self._local_root_payload
        if not isinstance(payload, dict):
            return
        label = str(entry.get(KEY_LABEL, EMPTY_STRING)).strip()
        if not label:
            return
        topology_root = payload.get(KEY_TOPOLOGY)
        if not isinstance(topology_root, dict):
            return
        topology_profiles = topology_root.get(KEY_TOPOLOGY_PROFILES)
        if not isinstance(topology_profiles, dict):
            return
        for topology_profile in topology_profiles.values():
            if not isinstance(topology_profile, dict):
                continue
            nodes = topology_profile.get(KEY_TOPOLOGY_NODES)
            if not isinstance(nodes, list):
                continue
            filtered: List[Dict[str, object]] = []
            removed_keys: set[int] = set()
            for node in nodes:
                if not isinstance(node, dict):
                    filtered.append(node)
                    continue
                if node.get(KEY_NODE_TYPE) != NODE_TYPE_DEVICE:
                    filtered.append(node)
                    continue
                device_ref = str(node.get(KEY_DEVICE_REF, EMPTY_STRING)).strip()
                if device_ref.lower() == label.lower():
                    key_value = node.get(KEY_NODE_KEY)
                    if isinstance(key_value, int):
                        removed_keys.add(key_value)
                    continue
                filtered.append(node)
            if len(filtered) == len(nodes):
                continue
            topology_profile[KEY_TOPOLOGY_NODES] = filtered
            edges = topology_profile.get(KEY_TOPOLOGY_EDGES)
            if isinstance(edges, list) and removed_keys:
                topology_profile[KEY_TOPOLOGY_EDGES] = [
                    edge
                    for edge in edges
                    if not (
                        isinstance(edge, dict)
                        and (
                            edge.get(KEY_FROM_NODE) in removed_keys
                            or edge.get(KEY_TO_NODE) in removed_keys
                        )
                    )
                ]

    def _rename_profiles_device(self, old: str, new: str) -> StatusResult:
        """
        NAME
            _rename_profiles_device - Rename a device label inside profiles.
        """
        entry = self._find_profiles_device_entry(old)
        if entry is None:
            print(f"ERROR: Device {old} not found in profiles.")
            return StatusResult(code=SS__DEVICE__NOT_FOUND)
        new_label = new.strip()
        if not new_label:
            print("ERROR: new device name required.")
            return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
        if old.strip().lower() == new_label.lower():
            print("ERROR: New name matches existing name.")
            return StatusResult(code=SS__CONFIG__DUPLICATE_LABEL)
        if self._is_active_group(new_label):
            print(ERR_NAME_RESERVED.format(name=new_label))
            return StatusResult(code=SS__CONFIG__INVALID)
        conflict = self._global_name_conflict(new_label)
        if conflict is not None and conflict.lower() != old.strip().lower():
            print(ERR_NAME_EXISTS.format(name=new_label))
            return StatusResult(code=SS__CONFIG__DUPLICATE_LABEL)
        entry["label"] = new_label
        self._mark_profiles_dirty()
        rename_counts: Dict[str, int] = {
            RENAME_REF_PROFILE_DEVICES: COUNT_ZERO,
            RENAME_REF_ATTACHMENTS: COUNT_ZERO,
            RENAME_REF_GROUPS: COUNT_ZERO,
            RENAME_REF_SELECTED: COUNT_ZERO,
            RENAME_REF_DIAGRAM: COUNT_ZERO,
            RENAME_REF_TEST_DEVICES: COUNT_ZERO,
            RENAME_REF_TEST_LIMIT_SWITCH: COUNT_ZERO,
            RENAME_REF_TEST_ROTATION_ENCODER: COUNT_ZERO,
            RENAME_REF_TEST_DEADBAND_ENCODER: COUNT_ZERO,
        }
        rename_counts[RENAME_REF_PROFILE_DEVICES] = self._update_profile_device_label(old, new_label)
        rename_counts[RENAME_REF_ATTACHMENTS] = self._update_attachment_labels(old, new_label)
        groups_count, selected_count = self._update_bridge_groups_label(old, new_label)
        rename_counts[RENAME_REF_GROUPS] = groups_count
        rename_counts[RENAME_REF_SELECTED] = selected_count
        if self._update_diagram_label(old, new_label):
            rename_counts[RENAME_REF_DIAGRAM] = COUNT_ONE
        test_counts = self._update_tests_label_refs(old, new_label)
        if test_counts:
            rename_counts.update(test_counts)
        self._refresh_devices_from_profiles()
        profile_name = self._tests_profile or self._active_profile_name()
        if profile_name:
            self._refresh_tests_profile(profile_name)
        self._print_rename_summary(old, new_label, rename_counts)
        return StatusResult(code=SS__NORMAL)

    def _update_bridge_groups_label(self, old: str, new: str) -> tuple[int, int]:
        """
        NAME
            _update_bridge_groups_label - Update bridgeConfig group members after rename.
        """
        config = self._local_config
        if not isinstance(config, dict):
            return COUNT_ZERO, COUNT_ZERO
        by_profile = config.get(KEY_BRIDGE_BY_PROFILE)
        if not isinstance(by_profile, dict):
            return COUNT_ZERO, COUNT_ZERO
        changed = False
        groups_changed = COUNT_ZERO
        selected_changed = COUNT_ZERO
        for entry in by_profile.values():
            if not isinstance(entry, dict):
                continue
            for group in entry.get(KEY_BRIDGE_GROUPS, []) or []:
                if not isinstance(group, dict):
                    continue
                for member in group.get("members", []) or []:
                    if isinstance(member, dict):
                        name = _group_member_label(member)
                        if name.lower() == old.lower():
                            member[KEY_LABEL] = new
                            member.pop(KEY_DEVICE, None)
                            changed = True
                            groups_changed += COUNT_ONE
                    elif isinstance(member, str):
                        if member.strip().lower() == old.lower():
                            index = group["members"].index(member)
                            group["members"][index] = new
                            changed = True
                            groups_changed += COUNT_ONE
            selected = entry.get(KEY_BRIDGE_SELECTED_DEVICE)
            if isinstance(selected, dict):
                sel_name = str(selected.get(KEY_DEVICE, "")).strip()
                if sel_name.lower() == old.lower():
                    selected[KEY_DEVICE] = new
                    changed = True
                    selected_changed += COUNT_ONE
        if changed:
            self._local_config = config
            self._mark_groups_dirty()
        return groups_changed, selected_changed

    def _update_diagram_label(self, old_label: str, new_label: str) -> bool:
        payload = self._local_root_payload
        if not isinstance(payload, dict):
            return False
        if not old_label.strip():
            return False
        topology_root = payload.get(KEY_TOPOLOGY)
        if not isinstance(topology_root, dict):
            return False
        topology_profiles = topology_root.get(KEY_TOPOLOGY_PROFILES)
        if not isinstance(topology_profiles, dict):
            return False
        updated = False
        for topology_profile in topology_profiles.values():
            if not isinstance(topology_profile, dict):
                continue
            nodes = topology_profile.get(KEY_TOPOLOGY_NODES)
            if not isinstance(nodes, list):
                continue
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                if node.get(KEY_NODE_TYPE) != NODE_TYPE_DEVICE:
                    continue
                device_ref = str(node.get(KEY_DEVICE_REF, EMPTY_STRING)).strip()
                if device_ref.lower() == old_label.strip().lower():
                    node[KEY_DEVICE_REF] = new_label
                    updated = True
        return updated

    def _update_profile_device_label(self, old: str, new: str) -> int:
        """
        NAME
            _update_profile_device_label - Replace label in active profile devices list.
        """
        payload = self._local_root_payload
        if not isinstance(payload, dict):
            return COUNT_ZERO
        profiles, profile_name = self._profiles_root_and_name()
        if profiles is None or profile_name is None:
            return COUNT_ZERO
        profile = profiles.get(profile_name)
        if not isinstance(profile, dict):
            return COUNT_ZERO
        labels = profile.get(KEY_PROFILE_DEVICES)
        if not isinstance(labels, list):
            return COUNT_ZERO
        replaced = COUNT_ZERO
        for idx, label in enumerate(list(labels)):
            if not isinstance(label, str):
                continue
            if label.strip().lower() == old.strip().lower():
                labels[idx] = new
                replaced += COUNT_ONE
        profile[KEY_PROFILE_DEVICES] = labels
        return replaced

    def _update_attachment_labels(self, old: str, new: str) -> int:
        """
        NAME
            _update_attachment_labels - Replace label in device attachments lists.
        """
        payload = self._local_root_payload
        if not isinstance(payload, dict):
            return COUNT_ZERO
        devices = payload.get(KEY_DEVICES)
        if not isinstance(devices, list):
            return COUNT_ZERO
        replaced = COUNT_ZERO
        for entry in devices:
            if not isinstance(entry, dict):
                continue
            attachments = entry.get(KEY_ATTACHMENTS)
            if not isinstance(attachments, list):
                continue
            for idx, label in enumerate(list(attachments)):
                if not isinstance(label, str):
                    continue
                if label.strip().lower() == old.strip().lower():
                    attachments[idx] = new
                    replaced += COUNT_ONE
            entry[KEY_ATTACHMENTS] = attachments
        return replaced

    def _update_tests_label_refs(self, old: str, new: str) -> Dict[str, int]:
        """
        NAME
            _update_tests_label_refs - Update test references for renamed devices.
        """
        self._ensure_tests_loaded()
        model = self._tests_model
        if model is None:
            return {}
        old_key = old.strip().lower()
        counts = {
            RENAME_REF_TEST_DEVICES: COUNT_ZERO,
            RENAME_REF_TEST_LIMIT_SWITCH: COUNT_ZERO,
            RENAME_REF_TEST_ROTATION_ENCODER: COUNT_ZERO,
            RENAME_REF_TEST_DEADBAND_ENCODER: COUNT_ZERO,
        }
        for test_set in model.test_sets.values():
            if not isinstance(test_set, TestSetModel):
                continue
            for test in test_set.tests:
                if not isinstance(test, TestModel):
                    continue
                for idx, label in enumerate(list(test.devices)):
                    if not isinstance(label, str):
                        continue
                    if label.strip().lower() == old_key:
                        test.devices[idx] = new
                        counts[RENAME_REF_TEST_DEVICES] += COUNT_ONE
                term = test.termination
                if term and isinstance(term.limit_switch, dict):
                    limit_id = term.limit_switch.get(KEY_LIMIT_SWITCH_ID)
                    if isinstance(limit_id, str) and limit_id.strip().lower() == old_key:
                        term.limit_switch[KEY_LIMIT_SWITCH_ID] = new
                        counts[RENAME_REF_TEST_LIMIT_SWITCH] += COUNT_ONE
                if term and term.rotation_encoder_key:
                    if str(term.rotation_encoder_key).strip().lower() == old_key:
                        term.rotation_encoder_key = new
                        counts[RENAME_REF_TEST_ROTATION_ENCODER] += COUNT_ONE
                deadband = test.deadband_sweep
                if deadband and deadband.encoder_key:
                    if str(deadband.encoder_key).strip().lower() == old_key:
                        deadband.encoder_key = new
                        counts[RENAME_REF_TEST_DEADBAND_ENCODER] += COUNT_ONE
        if any(count > COUNT_ZERO for count in counts.values()):
            self._mark_tests_dirty()
        return counts

    def _print_rename_summary(self, old: str, new: str, counts: Dict[str, int]) -> None:
        """
        NAME
            _print_rename_summary - Print rename reference updates.
        """
        label_map = {
            RENAME_REF_PROFILE_DEVICES: MESSAGE_INFO_RENAME_REFS_LABEL_PROFILE_DEVICES,
            RENAME_REF_ATTACHMENTS: MESSAGE_INFO_RENAME_REFS_LABEL_ATTACHMENTS,
            RENAME_REF_GROUPS: MESSAGE_INFO_RENAME_REFS_LABEL_GROUPS,
            RENAME_REF_SELECTED: MESSAGE_INFO_RENAME_REFS_LABEL_SELECTED,
            RENAME_REF_DIAGRAM: MESSAGE_INFO_RENAME_REFS_LABEL_DIAGRAM,
            RENAME_REF_TEST_DEVICES: MESSAGE_INFO_RENAME_REFS_LABEL_TEST_DEVICES,
            RENAME_REF_TEST_LIMIT_SWITCH: MESSAGE_INFO_RENAME_REFS_LABEL_TEST_LIMIT_SWITCH,
            RENAME_REF_TEST_ROTATION_ENCODER: MESSAGE_INFO_RENAME_REFS_LABEL_TEST_ROTATION_ENCODER,
            RENAME_REF_TEST_DEADBAND_ENCODER: MESSAGE_INFO_RENAME_REFS_LABEL_TEST_DEADBAND_ENCODER,
        }
        parts: List[str] = []
        for key in RENAME_REF_ORDER:
            count = counts.get(key, COUNT_ZERO)
            if count > COUNT_ZERO:
                parts.append(
                    MESSAGE_INFO_RENAME_REFS_ITEM.format(
                        label=label_map.get(key, key),
                        count=count,
                    )
                )
        if not parts:
            print(MESSAGE_INFO_RENAME_REFS_NONE.format(old=old, new=new))
            return
        details = SEP_COMMA_SPACE.join(parts)
        print(MESSAGE_INFO_RENAME_REFS.format(old=old, new=new, details=details))

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

    def _normalize_device_field(self, field: str) -> str:
        """
        NAME
            _normalize_device_field - Validate canonical device field names.
        """
        return field

    def _set_local_device_meta(self, name: str, field: str, value_raw: str) -> StatusResult:
        """
        NAME
            _set_local_device_meta - Update metadata for a local device.
        """
        field_key = self._normalize_device_field(field.strip())
        return self._set_profiles_device_meta(name, field_key, value_raw)

    def _clear_local_device_meta(self, name: str, field: str) -> StatusResult:
        """
        NAME
            _clear_local_device_meta - Clear metadata for a local device.
        """
        field_key = self._normalize_device_field(field.strip())
        return self._clear_profiles_device_meta(name, field_key)

    def _ensure_local_device_entry(self, name: str) -> StatusResult:
        """
        NAME
            _ensure_local_device_entry - Ensure a local device entry exists.
        """
        return self._ensure_profiles_device_entry(name)

    def _show_local_device_entry(self, name: str) -> StatusResult:
        """
        NAME
            _show_local_device_entry - Print the local device metadata.
        """
        return self._show_local_registry_device(name, json_output=False, pretty=False)

    def _show_local_registry_device(self, name: str, json_output: bool, pretty: bool) -> StatusResult:
        """
        NAME
            _show_local_registry_device - Print device registry entry details.
        """
        if not isinstance(self._local_root_payload, dict):
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        entry = self._find_profiles_device_entry(name)
        if entry is None:
            print(MESSAGE_ERR_REGISTRY_DEVICE_NOT_FOUND)
            return StatusResult(code=SS__DEVICE__NOT_FOUND)
        label = str(entry.get(FIELD_LABEL, name)).strip() or name
        topology = self._local_device_topology(label)
        payload = {KEY_DEVICE: entry}
        if topology:
            payload["topology"] = topology
        print(MESSAGE_SOURCE_LOCAL)
        if json_output:
            print(self._dump_json(payload, pretty))
            return StatusResult(code=SS__NORMAL)
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
        if topology:
            lines.extend(self._format_device_topology_lines(topology))
        if len(lines) == 1:
            lines.append(MESSAGE_LOCAL_REGISTRY_EMPTY)
        print("\n".join(lines))
        return StatusResult(code=SS__NORMAL)

    def _signal_catalog_entry(self, device_entry: Dict[str, object]) -> Tuple[str, Dict[str, object]]:
        """
        NAME
            _signal_catalog_entry - Resolve DSL signal metadata for one configured device entry.
        """
        device_type = str(device_entry.get(KEY_TYPE, EMPTY_STRING)).strip()
        catalog = self._dsl_signal_catalog()
        entry = catalog.get(device_type, {}) if device_type else {}
        return device_type, entry if isinstance(entry, dict) else {}

    def _iter_signal_device_entries(self) -> List[Dict[str, object]]:
        """
        NAME
            _iter_signal_device_entries - Return configured device registry entries for signal inspection.
        """
        if not isinstance(self._local_root_payload, dict):
            return []
        devices = self._local_root_payload.get(KEY_DEVICES)
        if not isinstance(devices, list):
            return []
        active_labels = {label.lower(): index for index, label in enumerate(self._active_profile_labels())}
        result: List[Tuple[int, Dict[str, object]]] = []
        fallback_index = len(active_labels)
        for entry in devices:
            if not isinstance(entry, dict):
                continue
            label = str(entry.get(KEY_LABEL, EMPTY_STRING)).strip()
            if not label:
                continue
            order = active_labels.get(label.lower(), fallback_index)
            if label.lower() not in active_labels:
                fallback_index += COUNT_ONE
            result.append((order, entry))
        result.sort(key=lambda item: (item[0], str(item[1].get(KEY_LABEL, EMPTY_STRING)).lower()))
        return [entry for _, entry in result]

    @staticmethod
    def _signal_meta_summary(signal_name: str, meta: Dict[str, object]) -> str:
        """
        NAME
            _signal_meta_summary - Build a compact summary for one supported signal.
        """
        flags: List[str] = []
        if bool(meta.get("readable", False)):
            flags.append("read")
        if bool(meta.get("writable", False)):
            flags.append("write")
        if bool(meta.get("clearable", False)):
            flags.append("clear")
        value_type = str(meta.get("valueType", EMPTY_STRING)).strip() or VALUE_UNAVAILABLE
        flags_text = SEP_COMMA_SPACE.join(flags) if flags else VALUE_UNAVAILABLE
        return f"{signal_name} ({value_type}; {flags_text})"

    def _show_local_signals(self, json_output: bool, pretty: bool) -> StatusResult:
        """
        NAME
            _show_local_signals - Show supported DSL signals for configured devices.
        """
        if not isinstance(self._local_root_payload, dict):
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        rows: List[Dict[str, object]] = []
        for entry in self._iter_signal_device_entries():
            label = str(entry.get(KEY_LABEL, EMPTY_STRING)).strip()
            device_type, signal_meta = self._signal_catalog_entry(entry)
            signals = []
            for signal_name in sorted(signal_meta.keys(), key=lambda value: value.lower()):
                meta = signal_meta.get(signal_name)
                if isinstance(meta, dict):
                    signals.append({KEY_NAME: signal_name, KEY_DETAILS: meta})
            rows.append(
                {
                    KEY_LABEL: label,
                    KEY_TYPE: device_type,
                    KEY_SIGNALS: signals,
                }
            )
        payload = {KEY_DEVICES: rows}
        print(MESSAGE_SOURCE_LOCAL)
        if json_output:
            print(self._dump_json(payload, pretty))
            return StatusResult(code=SS__NORMAL)
        print("Supported signals:")
        if not rows:
            print(f"  {STRING_NONE}")
            return StatusResult(code=SS__NORMAL)
        for row in rows:
            label = str(row.get(KEY_LABEL, EMPTY_STRING)).strip() or STRING_NONE
            device_type = str(row.get(KEY_TYPE, EMPTY_STRING)).strip() or VALUE_UNAVAILABLE
            signals = row.get(KEY_SIGNALS, [])
            print(f"  {label} ({device_type})")
            if not isinstance(signals, list) or not signals:
                print(f"    {VALUE_UNAVAILABLE}")
                continue
            for signal in signals:
                if not isinstance(signal, dict):
                    continue
                signal_name = str(signal.get(KEY_NAME, EMPTY_STRING)).strip()
                meta = signal.get(KEY_DETAILS, {})
                if signal_name and isinstance(meta, dict):
                    print(f"    {self._signal_meta_summary(signal_name, meta)}")
        return StatusResult(code=SS__NORMAL)

    def _show_local_signal_device(self, name: str, json_output: bool, pretty: bool) -> StatusResult:
        """
        NAME
            _show_local_signal_device - Show supported DSL signals for one configured device.
        """
        if not isinstance(self._local_root_payload, dict):
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        clean_name = str(name or EMPTY_STRING).strip()
        if not clean_name:
            print(MESSAGE_ERR_LOCAL_DEVICE_NOT_FOUND)
            return StatusResult(code=SS__DEVICE__NOT_FOUND)
        entry = self._find_profiles_device_entry(clean_name)
        if entry is None:
            print(MESSAGE_ERR_LOCAL_DEVICE_NOT_FOUND)
            return StatusResult(code=SS__DEVICE__NOT_FOUND)
        device_type, signal_meta = self._signal_catalog_entry(entry)
        signals = []
        for signal_name in sorted(signal_meta.keys(), key=lambda value: value.lower()):
            meta = signal_meta.get(signal_name)
            if isinstance(meta, dict):
                signals.append({KEY_NAME: signal_name, KEY_DETAILS: meta})
        payload = {
            KEY_LABEL: str(entry.get(KEY_LABEL, clean_name)).strip() or clean_name,
            KEY_TYPE: device_type,
            KEY_SIGNALS: signals,
        }
        print(MESSAGE_SOURCE_LOCAL)
        if json_output:
            print(self._dump_json(payload, pretty))
            return StatusResult(code=SS__NORMAL)
        print(f"Supported signals: {payload[KEY_LABEL]} ({device_type or VALUE_UNAVAILABLE})")
        if not signals:
            print(f"  {VALUE_UNAVAILABLE}")
            return StatusResult(code=SS__NORMAL)
        for signal in signals:
            signal_name = str(signal.get(KEY_NAME, EMPTY_STRING)).strip()
            meta = signal.get(KEY_DETAILS, {})
            if signal_name and isinstance(meta, dict):
                print(f"  {self._signal_meta_summary(signal_name, meta)}")
        return StatusResult(code=SS__NORMAL)

    def _active_topology_profile(self, create: bool = False) -> Dict[str, object]:
        """
        NAME
            _active_topology_profile - Return the active profile topology object.
        """
        if not isinstance(self._local_root_payload, dict):
            return {}
        profile_name = self._active_profile_name()
        if not profile_name:
            return {}
        topology_root = self._local_root_payload.get(KEY_TOPOLOGY)
        if not isinstance(topology_root, dict):
            if not create:
                return {}
            topology_root = {
                KEY_TOPOLOGY_VERSION: 1,
                KEY_TOPOLOGY_SOURCE: SHOW_SOURCE_LOCAL,
                KEY_TOPOLOGY_PROFILES: {},
            }
            self._local_root_payload[KEY_TOPOLOGY] = topology_root
        profiles = topology_root.get(KEY_TOPOLOGY_PROFILES)
        if not isinstance(profiles, dict):
            if not create:
                return {}
            profiles = {}
            topology_root[KEY_TOPOLOGY_PROFILES] = profiles
        profile = profiles.get(profile_name)
        if not isinstance(profile, dict):
            if not create:
                return {}
            return ensure_profile_topology_entry(self._local_root_payload, profile_name)
        if not isinstance(profile.get(KEY_TOPOLOGY_NODES), list):
            profile[KEY_TOPOLOGY_NODES] = []
        if not isinstance(profile.get(KEY_TOPOLOGY_EDGES), list):
            profile[KEY_TOPOLOGY_EDGES] = []
        return profile

    def _active_topology_registry(self) -> Dict[str, Dict[str, object]]:
        """
        NAME
            _active_topology_registry - Build the active device registry map.
        """
        return self._local_registry_by_label()

    def _topology_raw_text_lines(
        self,
        payload: Dict[str, object],
        node_map: Dict[int, Dict[str, object]],
        profile_name: str,
        subtarget: str,
    ) -> List[str]:
        """
        NAME
            _topology_raw_text_lines - Format the raw node/edge topology text view.
        """
        lines = [MESSAGE_SOURCE_LOCAL, MESSAGE_TOPOLOGY_HEADER, f"  profile: {profile_name}"]
        lines.append(MESSAGE_TOPOLOGY_NODES_HEADER)
        nodes_list = payload.get(KEY_TOPOLOGY_NODES, [])
        if isinstance(nodes_list, list) and nodes_list:
            for raw in nodes_list:
                if not isinstance(raw, dict):
                    continue
                key = raw.get(KEY_NODE_KEY, EMPTY_STRING)
                label = self._topology_node_label(node_map.get(key, raw) if isinstance(key, int) else raw)
                node_type = raw.get(KEY_NODE_TYPE, EMPTY_STRING)
                lines.append(f"  {key}: {label} [{node_type}]")
        else:
            lines.append(MESSAGE_TOPOLOGY_NONE)
        if subtarget in (EMPTY_STRING, CMD_EDGES):
            lines.append(MESSAGE_TOPOLOGY_EDGES_HEADER)
            edges_list = payload.get(KEY_TOPOLOGY_EDGES, [])
            if isinstance(edges_list, list) and edges_list:
                for edge in edges_list:
                    if not isinstance(edge, dict):
                        continue
                    from_key = edge.get(KEY_FROM_NODE, EMPTY_STRING)
                    to_key = edge.get(KEY_TO_NODE, EMPTY_STRING)
                    from_label = self._topology_node_label(node_map.get(from_key, {})) if isinstance(from_key, int) else EMPTY_STRING
                    to_label = self._topology_node_label(node_map.get(to_key, {})) if isinstance(to_key, int) else EMPTY_STRING
                    lines.append(
                        f"  {edge.get(KEY_EDGE_ID, EMPTY_STRING)}: "
                        f"{from_label}.{edge.get(KEY_FROM_PORT, EMPTY_STRING)} -> "
                        f"{to_label}.{edge.get(KEY_TO_PORT, EMPTY_STRING)} "
                        f"[{edge.get(KEY_EDGE_TYPE, EMPTY_STRING)}]"
                    )
            else:
                lines.append(MESSAGE_TOPOLOGY_NONE)
        return lines

    def _topology_can_device_edges(
        self,
        topology_profile: Dict[str, object],
        node_map: Dict[int, Dict[str, object]],
    ) -> List[Tuple[str, str]]:
        """
        NAME
            _topology_can_device_edges - Collapse CAN trunk edges into device-to-device hops.
        """
        full_adj: Dict[int, set[int]] = {}
        for edge in topology_edges(topology_profile):
            if not isinstance(edge, dict):
                continue
            if edge.get(KEY_EDGE_TYPE) != EDGE_TYPE_CAN_TRUNK:
                continue
            from_node = edge.get(KEY_FROM_NODE)
            to_node = edge.get(KEY_TO_NODE)
            if not isinstance(from_node, int) or not isinstance(to_node, int):
                continue
            full_adj.setdefault(from_node, set()).add(to_node)
            full_adj.setdefault(to_node, set()).add(from_node)
        if not full_adj:
            return []

        device_keys = []
        for key, node in node_map.items():
            if key not in full_adj:
                continue
            if not isinstance(node, dict) or node.get(KEY_NODE_TYPE) != NODE_TYPE_DEVICE:
                continue
            label = self._topology_node_label(node).strip()
            if label:
                device_keys.append(key)
        if len(device_keys) < COUNT_TWO:
            return []

        reduced: Dict[int, set[int]] = {key: set() for key in device_keys}
        for origin in device_keys:
            queue: deque[Tuple[int, int]] = deque()
            seen = {origin}
            for neighbor in sorted(full_adj.get(origin, set())):
                queue.append((neighbor, origin))
                seen.add(neighbor)
            while queue:
                current, parent = queue.popleft()
                node = node_map.get(current, {})
                if current != origin and isinstance(node, dict) and node.get(KEY_NODE_TYPE) == NODE_TYPE_DEVICE:
                    reduced.setdefault(origin, set()).add(current)
                    reduced.setdefault(current, set()).add(origin)
                    continue
                for neighbor in sorted(full_adj.get(current, set())):
                    if neighbor == parent or neighbor in seen:
                        continue
                    seen.add(neighbor)
                    queue.append((neighbor, current))

        if any(len(neighbors) > COUNT_TWO for neighbors in reduced.values()):
            return []

        edge_total = sum(len(neighbors) for neighbors in reduced.values()) // COUNT_TWO
        if edge_total <= 0:
            return []

        def _label(key: int) -> str:
            return self._topology_node_label(node_map.get(key, {})).strip()

        endpoints = [key for key, neighbors in reduced.items() if len(neighbors) <= COUNT_ONE]
        start = None
        for key in endpoints:
            if _label(key).strip().lower() == TOPOLOGY_LABEL_ROBORIO:
                start = key
                break
        if start is None and endpoints:
            start = sorted(endpoints, key=lambda value: _label(value).lower())[COUNT_ZERO]
        if start is None:
            start = sorted(device_keys, key=lambda value: _label(value).lower())[COUNT_ZERO]

        walked: List[Tuple[str, str]] = []
        visited_edges: set[Tuple[int, int]] = set()
        current = start
        previous = None
        while True:
            next_key = None
            for neighbor in sorted(reduced.get(current, set()), key=lambda value: _label(value).lower()):
                edge_key = (min(current, neighbor), max(current, neighbor))
                if edge_key in visited_edges:
                    continue
                if previous is not None and neighbor == previous:
                    next_key = neighbor
                    continue
                next_key = neighbor
                break
            if next_key is None:
                break
            edge_key = (min(current, next_key), max(current, next_key))
            visited_edges.add(edge_key)
            walked.append((_label(current), _label(next_key)))
            previous, current = current, next_key

        if len(visited_edges) != edge_total:
            return []
        return [(from_label, to_label) for from_label, to_label in walked if from_label and to_label]

    def _topology_group_memberships(self, profile_name: str) -> Dict[str, List[str]]:
        """
        NAME
            _topology_group_memberships - Map device labels to display group names.
        """
        memberships: Dict[str, List[str]] = {}
        for group in self._local_groups(profile_name, create=False):
            if not isinstance(group, dict):
                continue
            name = str(group.get(KEY_NAME, EMPTY_STRING)).strip()
            if not name or self._is_active_group(name):
                continue
            members = group.get(KEY_MEMBERS, []) or []
            for member in members:
                label = _group_member_label(member)
                if not label:
                    continue
                key = label.lower()
                names = memberships.setdefault(key, [])
                if name not in names:
                    names.append(name)
        return memberships

    @staticmethod
    def _topology_view_dict(topology_profile: Dict[str, object]) -> Dict[str, object]:
        """
        NAME
            _topology_view_dict - Return the optional topology view metadata block.
        """
        view = topology_profile.get(KEY_TOPOLOGY_VIEW)
        return view if isinstance(view, dict) else {}

    def _topology_can_view_path_edges(
        self,
        topology_profile: Dict[str, object],
        node_map: Dict[int, Dict[str, object]],
        profile_name: str,
    ) -> List[Tuple[str, str]]:
        """
        NAME
            _topology_can_view_path_edges - Derive one logical CAN path from wrapped bus-segment layout.
        """
        view = self._topology_view_dict(topology_profile)
        bus_offsets = view.get(KEY_VIEW_BUS_OFFSETS)
        bus_count = view.get(KEY_VIEW_BUS_COUNT)
        if isinstance(bus_offsets, list):
            logical_bus_count = len([item for item in bus_offsets if isinstance(item, (int, float))])
        elif isinstance(bus_count, int):
            logical_bus_count = bus_count
        else:
            logical_bus_count = COUNT_ZERO
        if logical_bus_count <= COUNT_ONE:
            return []
        connectors = view.get(KEY_VIEW_BUS_CONNECTORS)
        if isinstance(connectors, list) and connectors:
            normalized = [bool(item) for item in connectors]
            if not all(normalized[: max(logical_bus_count - COUNT_ONE, COUNT_ZERO)]):
                return []
        connector_sides_raw = view.get(KEY_VIEW_BUS_CONNECTOR_SIDES)
        connector_sides = (
            [
                str(item).strip().lower()
                for item in connector_sides_raw
                if isinstance(item, str)
            ]
            if isinstance(connector_sides_raw, list)
            else []
        )

        can_device_labels: set[str] = set()
        if isinstance(self._local_root_payload, dict):
            for entry in self._local_root_payload.get(KEY_DEVICES, []) or []:
                if not isinstance(entry, dict):
                    continue
                if str(entry.get(KEY_INTERFACE, EMPTY_STRING)).strip().upper() != INTERFACE_CAN:
                    continue
                label = str(entry.get(KEY_LABEL, EMPTY_STRING)).strip()
                if label:
                    can_device_labels.add(label.lower())
        if not can_device_labels:
            return []

        region_memberships = self._topology_group_memberships(profile_name)
        region_names = {
            "frontleft",
            "frontright",
            "backleft",
            "backright",
        }

        by_bus: Dict[int, List[Tuple[float, str]]] = {}
        for key, node in node_map.items():
            if not isinstance(node, dict) or node.get(KEY_NODE_TYPE) != NODE_TYPE_DEVICE:
                continue
            label = self._topology_node_label(node).strip()
            if label.lower() not in can_device_labels:
                continue
            layout = node.get(KEY_LAYOUT)
            if not label or not isinstance(layout, dict):
                continue
            bus_index = layout.get(KEY_LAYOUT_BUS)
            x_value = layout.get(KEY_LAYOUT_X)
            if not isinstance(bus_index, int) or not isinstance(x_value, (int, float)):
                continue
            by_bus.setdefault(bus_index, []).append((float(x_value), label))
        if not by_bus:
            return []

        ordered_labels: List[str] = []
        for bus_index in range(logical_bus_count):
            entries = by_bus.get(bus_index, [])
            if not entries:
                continue
            if bus_index == COUNT_ZERO:
                first_side = (
                    connector_sides[COUNT_ZERO]
                    if connector_sides
                    else (NEIGHBOR_PORT_RIGHT if logical_bus_count > COUNT_ONE else NEIGHBOR_PORT_LEFT)
                )
                reverse = first_side == NEIGHBOR_PORT_LEFT
            else:
                prev_side = (
                    connector_sides[bus_index - COUNT_ONE]
                    if bus_index - COUNT_ONE < len(connector_sides)
                    else (NEIGHBOR_PORT_RIGHT if (bus_index - COUNT_ONE) % COUNT_TWO == COUNT_ZERO else NEIGHBOR_PORT_LEFT)
                )
                reverse = prev_side == NEIGHBOR_PORT_RIGHT
            if bus_index + COUNT_ONE < logical_bus_count:
                next_side = (
                    connector_sides[bus_index]
                    if bus_index < len(connector_sides)
                    else (NEIGHBOR_PORT_RIGHT if bus_index % COUNT_TWO == COUNT_ZERO else NEIGHBOR_PORT_LEFT)
                )
                current_end_side = NEIGHBOR_PORT_LEFT if reverse else NEIGHBOR_PORT_RIGHT
                if current_end_side != next_side:
                    return []
            buckets: Dict[str, List[Tuple[float, str]]] = {}
            bucket_order: List[str] = []
            for x_value, label in entries:
                names = region_memberships.get(label.lower(), [])
                region_key = EMPTY_STRING
                for name in names:
                    if name.strip().lower() in region_names:
                        region_key = name.strip()
                        break
                bucket_key = region_key or label
                if bucket_key not in buckets:
                    bucket_order.append(bucket_key)
                buckets.setdefault(bucket_key, []).append((x_value, label))
            ordered_bucket_keys = sorted(
                bucket_order,
                key=lambda bucket: sum(item[0] for item in buckets[bucket]) / max(len(buckets[bucket]), COUNT_ONE),
                reverse=reverse,
            )
            for bucket_key in ordered_bucket_keys:
                for _x_value, label in sorted(buckets[bucket_key], key=lambda item: item[0]):
                    if not ordered_labels or ordered_labels[-1] != label:
                        ordered_labels.append(label)
        if len(ordered_labels) < COUNT_TWO:
            return []
        return [
            (ordered_labels[idx], ordered_labels[idx + COUNT_ONE])
            for idx in range(len(ordered_labels) - COUNT_ONE)
        ]

    def _topology_swyft_device_links(
        self,
        topology_profile: Dict[str, object],
        node_map: Dict[int, Dict[str, object]],
    ) -> List[Tuple[str, str, int]]:
        """
        NAME
            _topology_swyft_device_links - Return SWYFT junction-to-device attachments.
        """
        view = self._topology_view_dict(topology_profile)
        raw_links = view.get(KEY_DEVICE_LINKS)
        if not isinstance(raw_links, list):
            return []
        rows: List[Tuple[str, str, int]] = []
        for entry in raw_links:
            if not isinstance(entry, dict):
                continue
            node_key = entry.get(KEY_LINK_NODE)
            device_key = entry.get(KEY_LINK_DEVICE)
            port = entry.get(KEY_LINK_PORT, COUNT_ONE)
            if not isinstance(node_key, int) or not isinstance(device_key, int):
                continue
            if not isinstance(port, int):
                port = COUNT_ONE
            node = node_map.get(node_key, {})
            device = node_map.get(device_key, {})
            if not isinstance(node, dict) or not isinstance(device, dict):
                continue
            if node.get(KEY_NODE_TYPE) != NODE_TYPE_JUNCTION or device.get(KEY_NODE_TYPE) != NODE_TYPE_DEVICE:
                continue
            node_label = self._topology_node_label(node).strip()
            device_label = self._topology_node_label(device).strip()
            if node_label and device_label:
                rows.append((node_label, device_label, port))
        rows.sort(key=lambda item: (item[COUNT_ZERO].lower(), item[2], item[COUNT_ONE].lower()))
        return rows

    def _topology_swyft_backbone_links(
        self,
        topology_profile: Dict[str, object],
        node_map: Dict[int, Dict[str, object]],
    ) -> List[Tuple[str, str]]:
        """
        NAME
            _topology_swyft_backbone_links - Return ordered SWYFT backbone links.
        """
        view = self._topology_view_dict(topology_profile)
        raw_links = view.get(KEY_ETHERNET_LINKS)
        if not isinstance(raw_links, list):
            return []
        adjacency: Dict[int, set[int]] = {}
        for entry in raw_links:
            if not isinstance(entry, dict):
                continue
            a = entry.get(KEY_LINK_A)
            b = entry.get(KEY_LINK_B)
            if not isinstance(a, int) or not isinstance(b, int):
                continue
            adjacency.setdefault(a, set()).add(b)
            adjacency.setdefault(b, set()).add(a)
        if not adjacency:
            return []

        def _label(key: int) -> str:
            return self._topology_node_label(node_map.get(key, {})).strip()

        start = None
        for key in adjacency.keys():
            if _label(key).lower() == TOPOLOGY_LABEL_INJECT:
                start = key
                break
        if start is None:
            start = sorted(adjacency.keys(), key=lambda value: _label(value).lower())[COUNT_ZERO]

        seen = {start}
        queue: deque[int] = deque([start])
        ordered: List[Tuple[str, str]] = []
        while queue:
            current = queue.popleft()
            for neighbor in sorted(adjacency.get(current, set()), key=lambda value: _label(value).lower()):
                if neighbor in seen:
                    continue
                seen.add(neighbor)
                queue.append(neighbor)
                from_label = _label(current)
                to_label = _label(neighbor)
                if from_label and to_label:
                    ordered.append((from_label, to_label))
        return ordered

    def _topology_grouped_swyft_lines(
        self,
        backbone_links: List[Tuple[str, str]],
        device_links: List[Tuple[str, str, int]],
        profile_name: str,
    ) -> List[str]:
        """
        NAME
            _topology_grouped_swyft_lines - Format SWYFT topology using group headers.
        """
        memberships = self._topology_group_memberships(profile_name)
        group_order = [
            str(group.get(KEY_NAME, EMPTY_STRING)).strip()
            for group in self._local_groups(profile_name, create=False)
            if isinstance(group, dict) and str(group.get(KEY_NAME, EMPTY_STRING)).strip() and not self._is_active_group(str(group.get(KEY_NAME, EMPTY_STRING)).strip())
        ]
        lines = [MESSAGE_SOURCE_LOCAL, MESSAGE_TOPOLOGY_CAN_BUS_HEADER]
        if backbone_links:
            lines.append(MESSAGE_TOPOLOGY_BACKBONE_HEADER)
            for from_label, to_label in backbone_links:
                lines.append(
                    MESSAGE_TOPOLOGY_CAN_GROUP_LINE_FMT.format(
                        from_label=from_label,
                        to_label=to_label,
                        suffix=EMPTY_STRING,
                    )
                )
        grouped_lines: Dict[str, List[str]] = {}
        for swyft_label, device_label, _port in device_links:
            names = memberships.get(device_label.lower(), [])
            if not names:
                continue
            suffix = EMPTY_STRING
            if len(names) > COUNT_ONE:
                suffix = MESSAGE_TOPOLOGY_CAN_DUPLICATE_SUFFIX_FMT.format(
                    groups=SEP_COMMA_SPACE.join(name for name in names)
                )
            for name in names:
                grouped_lines.setdefault(name, []).append(
                    MESSAGE_TOPOLOGY_CAN_GROUP_LINE_FMT.format(
                        from_label=swyft_label,
                        to_label=device_label,
                        suffix=suffix,
                    )
                )
        wrote_any = bool(backbone_links)
        for name in group_order:
            entries = grouped_lines.get(name, [])
            if not entries:
                continue
            if wrote_any:
                lines.append(EMPTY_STRING)
            lines.append(MESSAGE_TOPOLOGY_GROUP_HEADER_FMT.format(name=name))
            lines.extend(entries)
            wrote_any = True
        return lines

    def _topology_swyft_can_bus_lines(
        self,
        topology_profile: Dict[str, object],
        node_map: Dict[int, Dict[str, object]],
        profile_name: str,
        grouped: bool,
    ) -> List[str]:
        """
        NAME
            _topology_swyft_can_bus_lines - Format topology text from SWYFT view metadata.
        """
        device_links = self._topology_swyft_device_links(topology_profile, node_map)
        if not device_links:
            return []
        backbone_links = self._topology_swyft_backbone_links(topology_profile, node_map)
        if grouped:
            return self._topology_grouped_swyft_lines(backbone_links, device_links, profile_name)
        lines = [MESSAGE_SOURCE_LOCAL, MESSAGE_TOPOLOGY_CAN_BUS_HEADER]
        if backbone_links:
            lines.append(MESSAGE_TOPOLOGY_BACKBONE_HEADER)
            for from_label, to_label in backbone_links:
                lines.append(
                    MESSAGE_TOPOLOGY_CAN_GROUP_LINE_FMT.format(
                        from_label=from_label,
                        to_label=to_label,
                        suffix=EMPTY_STRING,
                    )
                )
            lines.append(EMPTY_STRING)
        current_source = EMPTY_STRING
        for swyft_label, device_label, _port in device_links:
            if swyft_label != current_source:
                if current_source:
                    lines.append(EMPTY_STRING)
                lines.append(MESSAGE_TOPOLOGY_GROUP_HEADER_FMT.format(name=swyft_label))
                current_source = swyft_label
            lines.append(
                MESSAGE_TOPOLOGY_CAN_GROUP_LINE_FMT.format(
                    from_label=swyft_label,
                    to_label=device_label,
                    suffix=EMPTY_STRING,
                )
            )
        return lines

    def _topology_grouped_can_bus_lines(
        self,
        can_edges: List[Tuple[str, str]],
        profile_name: str,
    ) -> List[str]:
        """
        NAME
            _topology_grouped_can_bus_lines - Format CAN path lines with optional group duplication.
        """
        memberships = self._topology_group_memberships(profile_name)
        group_order = [
            str(group.get(KEY_NAME, EMPTY_STRING)).strip()
            for group in self._local_groups(profile_name, create=False)
            if isinstance(group, dict) and str(group.get(KEY_NAME, EMPTY_STRING)).strip() and not self._is_active_group(str(group.get(KEY_NAME, EMPTY_STRING)).strip())
        ]
        standalone: List[str] = []
        grouped_lines: Dict[str, List[str]] = {}
        for from_label, to_label in can_edges:
            names = memberships.get(from_label.lower(), [])
            if not names:
                standalone.append(
                    MESSAGE_TOPOLOGY_CAN_LINE_FMT.format(from_label=from_label, to_label=to_label)
                )
                continue
            suffix = EMPTY_STRING
            if len(names) > COUNT_ONE:
                suffix = MESSAGE_TOPOLOGY_CAN_DUPLICATE_SUFFIX_FMT.format(
                    groups=SEP_COMMA_SPACE.join(name for name in names)
                )
            for name in names:
                grouped_lines.setdefault(name, []).append(
                    MESSAGE_TOPOLOGY_CAN_GROUP_LINE_FMT.format(
                        from_label=from_label,
                        to_label=to_label,
                        suffix=suffix,
                    )
                )
        lines = [MESSAGE_SOURCE_LOCAL, MESSAGE_TOPOLOGY_CAN_BUS_HEADER]
        lines.extend(standalone if standalone else [])
        wrote_any = bool(standalone)
        for name in group_order:
            entries = grouped_lines.get(name, [])
            if not entries:
                continue
            if wrote_any:
                lines.append(EMPTY_STRING)
            lines.append(MESSAGE_TOPOLOGY_GROUP_HEADER_FMT.format(name=name))
            lines.extend(entries)
            wrote_any = True
        return lines

    def _topology_can_bus_lines(
        self,
        topology_profile: Dict[str, object],
        node_map: Dict[int, Dict[str, object]],
        profile_name: str,
        grouped: bool,
    ) -> List[str]:
        """
        NAME
            _topology_can_bus_lines - Format the operator-facing CAN bus path view.
        """
        swyft_lines = self._topology_swyft_can_bus_lines(topology_profile, node_map, profile_name, grouped)
        if swyft_lines:
            return swyft_lines
        can_edges = self._topology_can_view_path_edges(topology_profile, node_map, profile_name)
        if not can_edges:
            can_edges = self._topology_can_device_edges(topology_profile, node_map)
        if not can_edges:
            return []
        if grouped:
            return self._topology_grouped_can_bus_lines(can_edges, profile_name)
        lines = [MESSAGE_SOURCE_LOCAL, MESSAGE_TOPOLOGY_CAN_BUS_HEADER]
        for from_label, to_label in can_edges:
            lines.append(
                MESSAGE_TOPOLOGY_CAN_LINE_FMT.format(from_label=from_label, to_label=to_label)
            )
        return lines

    def _show_local_topology(
        self,
        tokens: List[str],
        json_output: bool,
        pretty: bool,
        grouped: bool,
    ) -> StatusResult:
        """
        NAME
            _show_local_topology - Show topology nodes/edges for the active profile.
        """
        if not isinstance(self._local_root_payload, dict):
            print(MESSAGE_ERR_LOCAL_CONFIG_MISSING)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        profile_name = self._active_profile_name()
        if not profile_name:
            print(MESSAGE_ERR_TOPOLOGY_PROFILE_REQUIRED)
            return StatusResult(code=SS__CONFIG__PROFILE_REQUIRED)
        topology_profile = self._active_topology_profile(create=False)
        if not topology_profile:
            print(MESSAGE_ERR_TOPOLOGY_NOT_LOADED)
            return StatusResult(code=SS__CONFIG__INVALID)
        subtarget = tokens[1].lower() if len(tokens) >= COUNT_TWO else EMPTY_STRING
        registry = self._active_topology_registry()
        node_map = topology_node_lookup(topology_profile, registry)
        payload: Dict[str, object] = {
            KEY_PROFILE: profile_name,
            KEY_TOPOLOGY_NODES: [node_map[key] for key in sorted(node_map.keys())],
            KEY_TOPOLOGY_EDGES: topology_edges(topology_profile),
        }
        if subtarget == CMD_NEIGHBORS:
            neighbor_payload: List[Dict[str, object]] = []
            for node_key, node in sorted(node_map.items()):
                entry = self._topology_neighbor_entry(node_key, node_map)
                entry[KEY_NEIGHBOR_PORTS] = self._device_neighbor_ports(topology_profile, node_key, node_map)
                neighbor_payload.append(entry)
            payload = {KEY_PROFILE: profile_name, KEY_NEIGHBOR_PORTS: neighbor_payload}
            if json_output:
                print(MESSAGE_SOURCE_LOCAL)
                print(self._dump_json(payload, pretty))
                return StatusResult(code=SS__NORMAL)
            lines = [MESSAGE_SOURCE_LOCAL, MESSAGE_TOPOLOGY_NEIGHBORS_HEADER]
            if not neighbor_payload:
                lines.append(MESSAGE_TOPOLOGY_NONE)
            for entry in neighbor_payload:
                lines.append(f"  {entry.get(KEY_LABEL, EMPTY_STRING)}:")
                ports = entry.get(KEY_NEIGHBOR_PORTS, [])
                if not isinstance(ports, list) or not ports:
                    lines.append(MESSAGE_TOPOLOGY_NONE)
                    continue
                for port in ports:
                    lines.append(
                        f"    {port.get(KEY_LINK_PORT, EMPTY_STRING)} -> "
                        f"{port.get(KEY_LABEL, EMPTY_STRING)}.{port.get(KEY_LINK_NEIGHBOR_PORT, EMPTY_STRING)} "
                        f"[{port.get(KEY_EDGE_TYPE, EMPTY_STRING)}]"
                    )
            print("\n".join(lines))
            return StatusResult(code=SS__NORMAL)
        if subtarget == CMD_NODE:
            if len(tokens) < COUNT_THREE:
                print(MESSAGE_ERR_TOPOLOGY_NODE_REQUIRED)
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            return self._show_local_neighbors([SHOW_TARGET_NEIGHBORS, tokens[2]], json_output, pretty)
        if subtarget == CMD_EDGES:
            payload = {KEY_PROFILE: profile_name, KEY_TOPOLOGY_EDGES: topology_edges(topology_profile)}
        elif subtarget == CMD_NODES:
            payload = {KEY_PROFILE: profile_name, KEY_TOPOLOGY_NODES: topology_nodes(topology_profile)}
        if grouped:
            payload[KEY_GROUPED] = True
        if json_output:
            print(MESSAGE_SOURCE_LOCAL)
            print(self._dump_json(payload, pretty))
            return StatusResult(code=SS__NORMAL)
        lines: List[str]
        if subtarget == EMPTY_STRING:
            lines = self._topology_can_bus_lines(topology_profile, node_map, profile_name, grouped)
            if not lines:
                lines = self._topology_raw_text_lines(payload, node_map, profile_name, subtarget)
                lines.insert(COUNT_ONE, MESSAGE_TOPOLOGY_FALLBACK_TEXT)
        else:
            lines = self._topology_raw_text_lines(payload, node_map, profile_name, subtarget)
        print("\n".join(lines))
        return StatusResult(code=SS__NORMAL)

    def _show_local_neighbors(self, tokens: List[str], json_output: bool, pretty: bool) -> StatusResult:
        """
        NAME
            _show_local_neighbors - Show neighbor data for one topology node.
        """
        if not isinstance(self._local_root_payload, dict):
            print(MESSAGE_ERR_LOCAL_CONFIG_MISSING)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        if len(tokens) < COUNT_TWO:
            print(MESSAGE_ERR_TOPOLOGY_NODE_REQUIRED)
            return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
        label = tokens[1]
        topology = self._local_device_topology(label)
        if not topology:
            print(MESSAGE_ERR_TOPOLOGY_NODE_NOT_FOUND.format(name=label))
            return StatusResult(code=SS__DEVICE__NOT_FOUND)
        payload = {
            KEY_LABEL: label,
            KEY_NODE_KEY: topology.get(KEY_NODE_KEY),
            KEY_NEIGHBOR_LINKS: topology.get(KEY_NEIGHBOR_LINKS, []),
            KEY_NEIGHBOR_PORTS: topology.get(KEY_NEIGHBOR_PORTS, []),
        }
        print(MESSAGE_SOURCE_LOCAL)
        if json_output:
            print(self._dump_json(payload, pretty))
            return StatusResult(code=SS__NORMAL)
        lines = [f"{MESSAGE_TOPOLOGY_NEIGHBORS_HEADER} {label}"]
        ports = payload.get(KEY_NEIGHBOR_PORTS, [])
        if isinstance(ports, list) and ports:
            for entry in ports:
                if not isinstance(entry, dict):
                    continue
                lines.append(
                    f"  {entry.get(KEY_LINK_PORT, EMPTY_STRING)} -> "
                    f"{entry.get(KEY_LABEL, EMPTY_STRING)}.{entry.get(KEY_LINK_NEIGHBOR_PORT, EMPTY_STRING)} "
                    f"[{entry.get(KEY_EDGE_TYPE, EMPTY_STRING)}]"
                )
        else:
            lines.append(MESSAGE_TOPOLOGY_NONE)
        print("\n".join(lines))
        return StatusResult(code=SS__NORMAL)

    def _validate_topology(self, verbose: bool = False) -> StatusResult:
        """
        NAME
            _validate_topology - Validate the current local topology payload.
        """
        if not isinstance(self._local_root_payload, dict):
            print(MESSAGE_ERR_LOCAL_CONFIG_MISSING)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        reporter = Reporter(bool(verbose))
        errors, warnings = validate_profiles(self._local_root_payload, reporter)
        if errors:
            for message in errors:
                print(MESSAGE_ERR_CONFIG_VALIDATE.format(message=message))
            for message in warnings:
                print(MESSAGE_WARNING_PREFIX + message)
            return StatusResult(code=SS__CONFIG__INVALID)
        for message in warnings:
            print(MESSAGE_WARNING_PREFIX + message)
        print(MESSAGE_INFO_TOPOLOGY_VALIDATE_OK)
        return StatusResult(code=SS__CONFIG__VALID)

    def _topology_command(self, tokens: List[str]) -> StatusResult:
        """
        NAME
            _topology_command - Handle topology editing commands in config mode.
        """
        if not isinstance(self._local_root_payload, dict):
            print(MESSAGE_ERR_LOCAL_CONFIG_MISSING)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        profile_name = self._active_profile_name()
        if not profile_name:
            print(MESSAGE_ERR_TOPOLOGY_PROFILE_REQUIRED)
            return StatusResult(code=SS__CONFIG__PROFILE_REQUIRED)
        if len(tokens) < COUNT_TWO:
            print(MESSAGE_ERR_TOPOLOGY_USAGE)
            return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
        sub = tokens[COUNT_ONE].lower()
        if sub == CMD_NEIGHBOR_PORTS:
            return self._topology_neighbor_ports_command(tokens[COUNT_TWO:])
        if sub == CMD_NEIGHBOR_AUTO:
            return self._topology_neighbor_auto_command(tokens[COUNT_TWO:])
        print(MESSAGE_ERR_TOPOLOGY_USAGE)
        return StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX)

    def _topology_neighbor_ports_command(self, tokens: List[str]) -> StatusResult:
        """
        NAME
            _topology_neighbor_ports_command - Edit one explicit neighbor port edge.
        """
        if not tokens:
            print(MESSAGE_ERR_TOPOLOGY_USAGE)
            return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
        action = tokens[COUNT_ZERO].lower()
        topology_profile = self._active_topology_profile(create=True)
        edges = topology_profile.get(KEY_TOPOLOGY_EDGES, [])
        if not isinstance(edges, list):
            edges = []
            topology_profile[KEY_TOPOLOGY_EDGES] = edges
        registry = self._active_topology_registry()
        node_map = topology_node_lookup(topology_profile, registry)
        if action == CMD_SET:
            if len(tokens) < 5:
                print(MESSAGE_ERR_TOPOLOGY_NEIGHBOR_PORTS_SET)
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            node = self._resolve_topology_node_key(tokens[1], node_map)
            neighbor = self._resolve_topology_node_key(tokens[3], node_map)
            if node is None:
                print(MESSAGE_ERR_TOPOLOGY_NODE_NOT_FOUND.format(name=tokens[1]))
                return StatusResult(code=SS__DEVICE__NOT_FOUND)
            if neighbor is None:
                print(MESSAGE_ERR_TOPOLOGY_NODE_NOT_FOUND.format(name=tokens[3]))
                return StatusResult(code=SS__DEVICE__NOT_FOUND)
            port = tokens[2]
            neighbor_port = tokens[4]
            self._remove_neighbor_edge(edges, node, port)
            self._remove_neighbor_edge(edges, neighbor, neighbor_port)
            edges.append(
                {
                    KEY_EDGE_ID: self._next_topology_edge_id(edges),
                    KEY_FROM_NODE: node,
                    KEY_FROM_PORT: port,
                    KEY_TO_NODE: neighbor,
                    KEY_TO_PORT: neighbor_port,
                    KEY_EDGE_TYPE: self._infer_topology_edge_type(port, neighbor_port),
                }
            )
            self._mark_profiles_dirty()
            print(MESSAGE_INFO_TOPOLOGY_NEIGHBOR_PORT_SET)
            return StatusResult(code=SS__NORMAL)
        if action == CMD_DELETE:
            if len(tokens) < 3:
                print(MESSAGE_ERR_TOPOLOGY_NEIGHBOR_PORTS_DELETE)
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            node = self._resolve_topology_node_key(tokens[1], node_map)
            if node is None:
                print(MESSAGE_ERR_TOPOLOGY_NODE_NOT_FOUND.format(name=tokens[1]))
                return StatusResult(code=SS__DEVICE__NOT_FOUND)
            removed = self._remove_neighbor_edge(edges, node, tokens[2])
            if not removed:
                print(MESSAGE_ERR_TOPOLOGY_NODE_NOT_FOUND.format(name=f"{tokens[1]}:{tokens[2]}"))
                return StatusResult(code=SS__DEVICE__NOT_FOUND)
            self._mark_profiles_dirty()
            print(MESSAGE_INFO_TOPOLOGY_NEIGHBOR_PORT_DELETE)
            return StatusResult(code=SS__NORMAL)
        if action == CMD_CLEAR:
            if len(tokens) < 2:
                print(MESSAGE_ERR_TOPOLOGY_NEIGHBOR_PORTS_CLEAR)
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            node = self._resolve_topology_node_key(tokens[1], node_map)
            if node is None:
                print(MESSAGE_ERR_TOPOLOGY_NODE_NOT_FOUND.format(name=tokens[1]))
                return StatusResult(code=SS__DEVICE__NOT_FOUND)
            topology_profile[KEY_TOPOLOGY_EDGES] = [
                edge
                for edge in edges
                if not (
                    isinstance(edge, dict)
                    and (edge.get(KEY_FROM_NODE) == node or edge.get(KEY_TO_NODE) == node)
                )
            ]
            self._mark_profiles_dirty()
            print(MESSAGE_INFO_TOPOLOGY_NEIGHBOR_PORT_CLEAR)
            return StatusResult(code=SS__NORMAL)
        print(MESSAGE_ERR_TOPOLOGY_USAGE)
        return StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX)

    def _topology_neighbor_auto_command(self, tokens: List[str]) -> StatusResult:
        """
        NAME
            _topology_neighbor_auto_command - Auto-generate CAN neighbor edges from layout.
        """
        if not tokens:
            print(MESSAGE_ERR_TOPOLOGY_NEIGHBOR_AUTO)
            return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
        action = tokens[COUNT_ZERO].lower()
        topology_profile = self._active_topology_profile(create=True)
        registry = self._active_topology_registry()
        node_map = topology_node_lookup(topology_profile, registry)
        selected_labels: Optional[set[str]] = None
        if action == CMD_ALL and len(tokens) >= COUNT_TWO:
            selected_labels = {name.strip().lower() for name in tokens[1].split(",") if name.strip()}
        elif action == CMD_NODE:
            if len(tokens) < COUNT_TWO:
                print(MESSAGE_ERR_TOPOLOGY_NEIGHBOR_AUTO)
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            selected_labels = {tokens[1].strip().lower()}
        elif action != CMD_ALL:
            print(MESSAGE_ERR_TOPOLOGY_NEIGHBOR_AUTO)
            return StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX)
        selected_keys: Optional[set[int]] = None
        if selected_labels is not None:
            selected_keys = set()
            for key, node in node_map.items():
                if self._topology_node_label(node).strip().lower() in selected_labels:
                    selected_keys.add(key)
            if not selected_keys:
                print(MESSAGE_ERR_TOPOLOGY_NODE_NOT_FOUND.format(name=SEP_COMMA_SPACE.join(sorted(selected_labels))))
                return StatusResult(code=SS__DEVICE__NOT_FOUND)
        edges = topology_profile.get(KEY_TOPOLOGY_EDGES, [])
        if not isinstance(edges, list):
            edges = []
        preserved: List[Dict[str, object]] = []
        reusable_ids: List[str] = []
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            edge_type = str(edge.get(KEY_EDGE_TYPE, EMPTY_STRING)).strip()
            if edge_type not in (
                EDGE_TYPE_CAN_TRUNK,
                EDGE_TYPE_CAN_DROP,
                EDGE_TYPE_CAN_TAP,
            ):
                preserved.append(edge)
                continue
            if selected_keys is None:
                continue
            from_node = edge.get(KEY_FROM_NODE)
            to_node = edge.get(KEY_TO_NODE)
            if from_node in selected_keys or to_node in selected_keys:
                edge_id = str(edge.get(KEY_EDGE_ID, EMPTY_STRING)).strip()
                if edge_id:
                    reusable_ids.append(edge_id)
                continue
            preserved.append(edge)
        device_nodes: List[Tuple[int, Dict[str, object]]] = []
        for key, node in node_map.items():
            if str(node.get(KEY_NODE_TYPE, EMPTY_STRING)).strip() != NODE_TYPE_DEVICE:
                continue
            if selected_keys is not None and key not in selected_keys:
                continue
            layout = node.get(KEY_LAYOUT)
            layout_dict = layout if isinstance(layout, dict) else {}
            device_nodes.append((key, layout_dict))
        by_bus: Dict[int, List[Tuple[int, Dict[str, object]]]] = {}
        for key, layout in device_nodes:
            bus = int(layout.get(KEY_BUS, 0))
            by_bus.setdefault(bus, []).append((key, layout))
        for bus_nodes in by_bus.values():
            ordered = sorted(bus_nodes, key=lambda item: (float(item[1].get("x", 0.0)), int(item[0])))
            for idx in range(len(ordered) - 1):
                left_key = ordered[idx][0]
                right_key = ordered[idx + 1][0]
                edge_id = reusable_ids.pop(0) if reusable_ids else self._next_topology_edge_id(preserved)
                preserved.append(
                    {
                        KEY_EDGE_ID: edge_id,
                        KEY_FROM_NODE: left_key,
                        KEY_FROM_PORT: NEIGHBOR_PORT_RIGHT,
                        KEY_TO_NODE: right_key,
                        KEY_TO_PORT: NEIGHBOR_PORT_LEFT,
                        KEY_EDGE_TYPE: EDGE_TYPE_CAN_TRUNK,
                    }
                )
        topology_profile[KEY_TOPOLOGY_EDGES] = preserved
        self._mark_profiles_dirty()
        print(MESSAGE_INFO_TOPOLOGY_NEIGHBOR_AUTO)
        return StatusResult(code=SS__NORMAL)

    def _resolve_topology_node_key(
        self,
        label: str,
        node_map: Dict[int, Dict[str, object]],
    ) -> Optional[int]:
        """
        NAME
            _resolve_topology_node_key - Resolve a node label to topology key.
        """
        label_key = str(label).strip().lower()
        for key, node in node_map.items():
            if self._topology_node_label(node).strip().lower() == label_key:
                return key
        return None

    @staticmethod
    def _next_topology_edge_id(edges: List[Dict[str, object]]) -> str:
        """
        NAME
            _next_topology_edge_id - Allocate the next simple edge id.
        """
        max_value = 0
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            raw = str(edge.get(KEY_EDGE_ID, EMPTY_STRING)).strip()
            if raw.startswith("edge_"):
                tail = raw.split("_", 1)[1]
                if tail.isdigit():
                    max_value = max(max_value, int(tail))
        return f"edge_{max_value + COUNT_ONE}"

    @staticmethod
    def _infer_topology_edge_type(from_port: str, to_port: str) -> str:
        """
        NAME
            _infer_topology_edge_type - Infer edge type from port names.
        """
        ports = {str(from_port).strip().lower(), str(to_port).strip().lower()}
        if "tap" in ports:
            return EDGE_TYPE_CAN_TAP
        if any(name.startswith("drop") or name.startswith("branch") for name in ports):
            return EDGE_TYPE_CAN_DROP
        return EDGE_TYPE_CAN_TRUNK

    @staticmethod
    def _remove_neighbor_edge(edges: List[Dict[str, object]], node_key: int, port: str) -> bool:
        """
        NAME
            _remove_neighbor_edge - Remove one edge matching a node/port endpoint.
        """
        removed = False
        kept: List[Dict[str, object]] = []
        port_key = str(port).strip().lower()
        for edge in edges:
            if not isinstance(edge, dict):
                kept.append(edge)
                continue
            from_node = edge.get(KEY_FROM_NODE)
            to_node = edge.get(KEY_TO_NODE)
            from_port = str(edge.get(KEY_FROM_PORT, EMPTY_STRING)).strip().lower()
            to_port = str(edge.get(KEY_TO_PORT, EMPTY_STRING)).strip().lower()
            if (from_node == node_key and from_port == port_key) or (to_node == node_key and to_port == port_key):
                removed = True
                continue
            kept.append(edge)
        if removed:
            edges[:] = kept
        return removed

    def _local_device_topology(self, label: str) -> Dict[str, object]:
        """
        NAME
            _local_device_topology - Return topology graph details for a topology node label.
        """
        if not isinstance(self._local_root_payload, dict):
            return {}
        profile = self._active_profile_name()
        if not profile:
            return {}
        topology_profile = topology_profile_from_payload(self._local_root_payload, profile)
        if not topology_profile:
            return {}
        registry = self._local_registry_by_label()
        node_by_key = topology_node_lookup(topology_profile, registry)
        target_node: Optional[Dict[str, object]] = None
        label_key = label.strip().lower()
        for raw in node_by_key.values():
            node_label = self._topology_node_label(raw)
            if node_label.lower() == label_key:
                target_node = raw
                break
        if target_node is None:
            return {}
        node_key = target_node.get(KEY_NODE_KEY)
        if not isinstance(node_key, int):
            return {}
        layout = target_node.get(KEY_LAYOUT)
        layout_dict = layout if isinstance(layout, dict) else {}
        topology: Dict[str, object] = {
            KEY_NODE_KEY: node_key,
            KEY_LABEL: self._topology_node_label(target_node),
            KEY_BUS: layout_dict.get(KEY_BUS),
            "row": layout_dict.get("row"),
            "x": layout_dict.get("x"),
            KEY_OBJECT_TYPE: target_node.get(KEY_OBJECT_TYPE, get_object_type(target_node)),
            KEY_NODE_TYPE: target_node.get(KEY_NODE_TYPE),
            KEY_NODE_CLASS: target_node.get(KEY_NODE_CLASS, get_node_class(target_node)),
        }
        neighbor_links = self._device_neighbor_links(topology_profile, node_key, node_by_key)
        neighbor_ports = self._device_neighbor_ports(topology_profile, node_key, node_by_key)
        if neighbor_links:
            topology[KEY_NEIGHBOR_LINKS] = neighbor_links
        if neighbor_ports:
            topology[KEY_NEIGHBOR_PORTS] = neighbor_ports
        return topology

    def _local_registry_by_label(self) -> Dict[str, Dict[str, object]]:
        """
        NAME
            _local_registry_by_label - Build a label-keyed device registry map.
        """
        registry: Dict[str, Dict[str, object]] = {}
        devices = self._local_root_payload.get(KEY_DEVICES)
        if not isinstance(devices, list):
            return registry
        for entry in devices:
            if not isinstance(entry, dict):
                continue
            label = str(entry.get(KEY_LABEL, EMPTY_STRING)).strip()
            if not label:
                continue
            registry[label.lower()] = entry
        return registry

    def _device_neighbor_links(
        self,
        topology_profile: Dict[str, object],
        node_key: int,
        node_by_key: Dict[int, Dict[str, object]],
    ) -> List[Dict[str, object]]:
        """
        NAME
            _device_neighbor_links - Return undirected neighbors for one node.
        """
        neighbors: List[Dict[str, object]] = []
        for a, b in topology_neighbor_links(topology_profile, node_key):
            other = b if a == node_key else a
            neighbors.append(self._topology_neighbor_entry(other, node_by_key))
        return neighbors

    def _device_neighbor_ports(
        self,
        topology_profile: Dict[str, object],
        node_key: int,
        node_by_key: Dict[int, Dict[str, object]],
    ) -> List[Dict[str, object]]:
        """
        NAME
            _device_neighbor_ports - Return port-aware neighbors for one node.
        """
        neighbors: List[Dict[str, object]] = []
        for entry in topology_neighbor_ports(topology_profile, node_key):
            neighbor = entry.get(KEY_LINK_NEIGHBOR)
            if not isinstance(neighbor, int):
                continue
            neighbor_entry = self._topology_neighbor_entry(neighbor, node_by_key)
            neighbor_entry[KEY_LINK_PORT] = entry.get(KEY_LINK_PORT)
            neighbor_entry[KEY_LINK_NEIGHBOR_PORT] = entry.get(KEY_LINK_NEIGHBOR_PORT)
            if KEY_EDGE_TYPE in entry:
                neighbor_entry[KEY_EDGE_TYPE] = entry.get(KEY_EDGE_TYPE)
            if KEY_EDGE_ID in entry:
                neighbor_entry[KEY_EDGE_ID] = entry.get(KEY_EDGE_ID)
            neighbors.append(neighbor_entry)
        return neighbors

    def _topology_neighbor_entry(
        self,
        key: int,
        node_by_key: Dict[int, Dict[str, object]],
    ) -> Dict[str, object]:
        """
        NAME
            _topology_neighbor_entry - Build one neighbor summary.
        """
        node = node_by_key.get(key, {})
        layout = node.get(KEY_LAYOUT)
        layout_dict = layout if isinstance(layout, dict) else node
        return {
            KEY_NODE_KEY: key,
            KEY_LABEL: self._topology_node_label(node),
            KEY_BUS: layout_dict.get(KEY_BUS),
            "row": layout_dict.get("row"),
            "x": layout_dict.get("x"),
            KEY_OBJECT_TYPE: node.get(KEY_OBJECT_TYPE, get_object_type(node)),
            KEY_NODE_TYPE: node.get(KEY_NODE_TYPE, get_object_type(node)),
            KEY_NODE_CLASS: node.get(KEY_NODE_CLASS, get_node_class(node)),
        }

    def _topology_node_label(self, node: Dict[str, object]) -> str:
        """
        NAME
            _topology_node_label - Resolve the display label for one topology node.
        """
        if str(node.get(KEY_NODE_TYPE, EMPTY_STRING)).strip() == NODE_TYPE_DEVICE:
            return str(node.get(KEY_DEVICE_REF, EMPTY_STRING)).strip()
        return str(node.get(KEY_LABEL, EMPTY_STRING)).strip()

    def _format_device_topology_lines(self, topology: Dict[str, object]) -> List[str]:
        """
        NAME
            _format_device_topology_lines - Format topology metadata for text show.
        """
        lines = [MESSAGE_REGISTRY_TOPOLOGY_HEADER]
        for key in (KEY_LABEL, KEY_NODE_KEY, KEY_OBJECT_TYPE, KEY_NODE_CLASS, KEY_BUS, "row", "x"):
            if key in topology:
                lines.append(
                    MESSAGE_REGISTRY_TOPOLOGY_FIELD_FMT.format(
                        key=key,
                        value=topology.get(key),
                    )
                )
        neighbor_ports = topology.get(KEY_NEIGHBOR_PORTS)
        if isinstance(neighbor_ports, list) and neighbor_ports:
            for entry in neighbor_ports:
                if not isinstance(entry, dict):
                    continue
                lines.append(
                    MESSAGE_REGISTRY_TOPOLOGY_NEIGHBOR_FMT.format(
                        port=entry.get(KEY_LINK_PORT, EMPTY_STRING),
                        label=entry.get(KEY_LABEL, EMPTY_STRING),
                        key=entry.get(KEY_NODE_KEY, EMPTY_STRING),
                        neighbor_port=entry.get(KEY_LINK_NEIGHBOR_PORT, EMPTY_STRING),
                    )
                )
        return lines

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

        interface = str(get_device_interface(entry) or "").strip()
        if not interface:
            return [FIELD_DEVICE_INTERFACE]
        required: tuple[str, ...]
        if interface == INTERFACE_CAN:
            required = DEVICE_REQUIRED_CAN
        elif interface == INTERFACE_DIO:
            required = DEVICE_REQUIRED_DIO
        elif interface == INTERFACE_PWM:
            required = DEVICE_REQUIRED_PWM
        elif interface == INTERFACE_ANALOG:
            required = DEVICE_REQUIRED_ANALOG
        elif interface == INTERFACE_USB:
            required = DEVICE_REQUIRED_USB
        else:
            required = DEVICE_REQUIRED_INTERNAL
        missing: List[str] = []
        for field in required:
            if field == FIELD_DEVICE_INTERFACE:
                continue
            if entry.get(field) is None:
                missing.append(field)
        return missing

    def _validate_device_entry(self, entry: Dict[str, object]) -> None:
        """
        NAME
            _validate_device_entry - Validate a device definition after edits.
        """

        interface = str(get_device_interface(entry) or "").strip()
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
            DIRTY_MAPPINGS: bool(self._can_mappings_dirty),
        }

    def _sync_store_from_local(self) -> None:
        """
        NAME
            _sync_store_from_local - Sync CLI state into the config store.
        """

        if self._local_root_payload is not None:
            payload = dict(self._local_root_payload)
            if isinstance(self._local_config, dict):
                payload[KEY_BRIDGE_CONFIG] = self._ordered_bridge_config(self._local_config)
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

        if self._tests_model is None:
            return
        profile = self._tests_profile or self._active_profile_name() or get_default_profile()
        if not profile:
            return
        entry = self._local_profile_entry(profile, create=True)
        entry[KEY_BRIDGE_TESTS] = model_to_payload(self._tests_model)
        self._store.set_tests_model(profile, self._tests_model)

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

    def _save_profiles(
        self,
        path: str,
        *,
        skip_validation: bool = False,
        force: bool = False,
        validation_ok: Optional[bool] = None,
    ) -> StatusResult:
        """
        NAME
            _save_profiles - Save updated bringup_system.json.
        """
        if not skip_validation:
            allowed, validation_ok = self._guard_save(force)
            if not allowed:
                return StatusResult(code=SS__CONFIG__INVALID)
        if validation_ok is None:
            validation_ok = True
        if not self._local_devices_locked or self._local_root_payload is None:
            print("ERROR: No profiles are loaded.")
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        if not self._local_config:
            print(MESSAGE_ERR_LOCAL_CONFIG_MISSING)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        self._sync_store_tests()
        payload = dict(self._local_root_payload)
        payload["bridgeConfig"] = self._ordered_bridge_config(self._local_config)
        target_path = Path(path)
        payload["schema_version"] = PROFILE_SCHEMA_VERSION
        payload["data_version"] = timestamp_version()
        payload["data_hash"] = compute_profiles_hash(payload)
        try:
            target = target_path.resolve()
            canonical = self._config_repository.canonical_path().resolve()
            deploy = self._config_repository.deploy_path().resolve()
            session = self._config_repository.session_for_payload(target_path, payload)
            if target == canonical or target == deploy:
                self._config_repository.sync(session, stamp=False)
            else:
                self._config_repository.save(session, path=target_path, stamp=False)
        except Exception as exc:
            print(MESSAGE_ERR_SAVE_WRITE.format(path=path, error=exc))
            return StatusResult(code=SS__CONFIG__INVALID)
        self._profiles_dirty = False
        self._groups_dirty = False
        self._tests_dirty = False
        self._sync_store_from_local()
        self._post_save(
            AUDIT_ACTION_SAVE,
            [SOURCE_NAME_REGISTRY],
            Path(path),
            payload,
            validation_ok,
            JSON_PRETTY_INDENT,
            True,
        )
        self._record_last_save(Path(path))
        print(f"Wrote profiles to {path}.")
        if target_path.resolve() in (
            self._config_repository.canonical_path().resolve(),
            self._config_repository.deploy_path().resolve(),
        ):
            canonical = self._config_repository.canonical_path().resolve()
            deploy = self._config_repository.deploy_path().resolve()
            if canonical != deploy:
                other = deploy if target_path.resolve() == canonical else canonical
                print(MESSAGE_INFO_PROFILES_MIRRORED.format(path=other))
        return StatusResult(code=SS__CONFIG__SAVED)

    def _save_all(self, prompt: bool, force: bool = False) -> StatusResult:
        """
        NAME
            _save_all - Save all dirty sections using current paths.
        """

        if self._batch:
            prompt = False
        failures = False
        saved_any = False
        save_candidates = False
        dirty_profiles = self._profiles_dirty or self._groups_dirty or self._tests_dirty
        if dirty_profiles:
            if not self._local_root_path:
                print(MESSAGE_SAVE_ALL_PROFILES_MISSING)
                failures = True
            else:
                save_candidates = True
        if self._bindings_dirty:
            if not self._bindings_path:
                print(MESSAGE_SAVE_ALL_BINDINGS_MISSING)
                failures = True
            else:
                save_candidates = True
        if self._can_mappings_dirty:
            if not self._can_mappings_path:
                print(MESSAGE_SAVE_ALL_MAPPINGS_MISSING)
                failures = True
            else:
                save_candidates = True
        if not save_candidates and not failures:
            print("Nothing to save.")
            return StatusResult(code=SS__CONFIG__SAVED)
        if failures and not save_candidates:
            return StatusResult(code=SS__CONFIG__INVALID)
        allowed, validation_ok = self._guard_save(force)
        if not allowed:
            return StatusResult(code=SS__CONFIG__INVALID)
        if dirty_profiles and self._local_root_path:
            if prompt and not self._confirm(f"Save profiles to {self._local_root_path}?"):
                pass
            else:
                result = self._save_profiles(
                    str(self._local_root_path),
                    skip_validation=True,
                    validation_ok=validation_ok,
                )
                saved_any = True
                if not result.ok():
                    failures = True
        if self._bindings_dirty and self._bindings_path:
            if prompt and not self._confirm(f"Save bindings to {self._bindings_path}?"):
                pass
            else:
                result = self._save_bindings_to_path(
                    Path(self._bindings_path),
                    validation_ok=validation_ok,
                )
                saved_any = True
                if not result.ok():
                    failures = True
        if self._can_mappings_dirty and self._can_mappings_path:
            if prompt and not self._confirm(f"Save mappings to {self._can_mappings_path}?"):
                pass
            else:
                result = self._save_can_mappings_to_path(
                    Path(self._can_mappings_path),
                    validation_ok=validation_ok,
                )
                saved_any = True
                if not result.ok():
                    failures = True
        if failures:
            return StatusResult(code=SS__CONFIG__INVALID)
        return StatusResult(code=SS__CONFIG__SAVED)

    def _ensure_profiles_device_entry(self, name: str) -> StatusResult:
        """
        NAME
            _ensure_profiles_device_entry - Reject implicit registry creation.
        """
        label = name.strip()
        if not label:
            print(MESSAGE_ERR_DEVICE_LABEL_REQUIRED)
            return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
        payload = self._local_root_payload
        if not isinstance(payload, dict):
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        profile_name = self._active_profile_name()
        if not profile_name:
            print(MESSAGE_ERR_DEVICE_PROFILE_REQUIRED)
            return StatusResult(code=SS__CONFIG__PROFILE_REQUIRED)
        profiles = payload.get(KEY_PROFILES)
        if not isinstance(profiles, dict):
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        profile = profiles.get(profile_name)
        if not isinstance(profile, dict):
            print(MESSAGE_ERR_PROFILE_UNKNOWN.format(name=profile_name))
            return StatusResult(code=SS__CONFIG__PROFILE_REQUIRED)
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
                    self._mark_profiles_dirty()
                return StatusResult(code=SS__NORMAL)
        entry = {KEY_LABEL: label}
        devices.append(entry)
        labels = profile.get(KEY_PROFILE_DEVICES)
        if not isinstance(labels, list):
            labels = []
            profile[KEY_PROFILE_DEVICES] = labels
        if label not in labels:
            labels.append(label)
        self._mark_profiles_dirty()
        self._refresh_devices_from_profiles()
        self._validate_device_entry(entry)
        return StatusResult(code=SS__NORMAL)

    def _maybe_hint_validate_profile(self, path: str) -> None:
        """
        NAME
            _maybe_hint_validate_profile - Suggest profile usage when a path is missing.
        """
        if not path:
            return
        try:
            if Path(path).exists():
                return
        except Exception:
            return
        payload = self._local_root_payload
        profiles = payload.get(KEY_PROFILES) if isinstance(payload, dict) else None
        if not isinstance(profiles, dict):
            return
        if path in profiles:
            print(MESSAGE_HINT_PREFIX + MESSAGE_HINT_VALIDATE_CONFIG_PROFILE)

    def _maybe_print_failure_hint(self, line: str) -> None:
        """
        NAME
            _maybe_print_failure_hint - Print a targeted hint for common commands.
        """
        try:
            tokens = self._split_command(line)
        except CliParseError:
            return
        if not tokens:
            return
        tokens = self._parser.normalize_tokens(tokens, self._modes[-1].name)
        cmd = tokens[COUNT_ZERO].lower()
        if cmd == CMD_VALIDATE:
            print(MESSAGE_HINT_PREFIX + MESSAGE_HINT_VALIDATE)
            return
        if cmd == CMD_SAVE:
            print(MESSAGE_HINT_PREFIX + MESSAGE_HINT_SAVE)
            return
        if cmd == CMD_SHOW:
            print(MESSAGE_HINT_PREFIX + MESSAGE_HINT_SHOW)
            return
        if cmd == CMD_SOURCES:
            print(MESSAGE_HINT_PREFIX + MESSAGE_HINT_SOURCES)
            return
        if cmd == CMD_LOAD:
            print(MESSAGE_HINT_PREFIX + MESSAGE_HINT_SOURCES)
            return
        if cmd == CMD_PROFILE:
            print(MESSAGE_HINT_PREFIX + MESSAGE_HINT_PROFILE)
            return
        if cmd == CMD_PROFILES:
            print(MESSAGE_HINT_PREFIX + MESSAGE_HINT_PROFILES)
            return
        if cmd == CMD_CAN_MAPPINGS:
            print(MESSAGE_HINT_PREFIX + MESSAGE_HINT_CAN_MAPPINGS)

    def _alias_replacement(self, tokens: List[str]) -> Optional[Tuple[str, str]]:
        """
        NAME
            _alias_replacement - Resolve removed alias commands to canonical replacements.
        """
        if not tokens:
            return None
        first = tokens[COUNT_ZERO].lower()
        if first in ALIAS_REPLACEMENTS:
            return first, ALIAS_REPLACEMENTS[first]
        if len(tokens) >= COUNT_TWO:
            alias_key = f"{first} {tokens[COUNT_ONE].lower()}"
            if alias_key in ALIAS_REPLACEMENTS:
                return alias_key, ALIAS_REPLACEMENTS[alias_key]
        return None

    def _set_profiles_device_meta(self, name: str, field: str, value_raw: str) -> StatusResult:
        """
        NAME
            _set_profiles_device_meta - Update a device entry inside profiles.
        """
        entry = self._find_profiles_device_entry(name)
        if entry is None:
            create_result = self._ensure_profiles_device_entry(name)
            if not create_result.ok():
                return create_result
            entry = self._find_profiles_device_entry(name)
            if entry is None:
                print(MESSAGE_ERR_REGISTRY_DEVICE_NOT_FOUND)
                return StatusResult(code=SS__DEVICE__NOT_FOUND)
        self._ensure_profile_device_label(name)
        field_key = self._normalize_device_field(field.strip())
        if field_key == FIELD_LABEL:
            print("ERROR: device label is managed by rename device.")
            return StatusResult(code=SS__DEVICE__INVALID_FIELD)
        if field_key not in DEVICE_FIELDS_PROFILE:
            print(MESSAGE_ERR_DEVICE_FIELD_UNKNOWN)
            return StatusResult(code=SS__DEVICE__INVALID_FIELD)
        store_key = FIELD_TYPE if field_key == FIELD_ROLE else field_key
        field_type = DEVICE_FIELD_TYPES.get(field_key, DEVICE_FIELD_STR)
        if field_type == DEVICE_FIELD_INT:
            try:
                entry[store_key] = int(value_raw, 0)
            except ValueError:
                print(MESSAGE_ERR_DEVICE_FIELD_INT)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
        elif field_type == DEVICE_FIELD_BOOL:
            parsed = self._parse_bool(value_raw)
            if parsed is None:
                print(MESSAGE_ERR_DEVICE_FIELD_BOOL)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            entry[store_key] = parsed
        elif field_type == DEVICE_FIELD_LIST:
            parsed = parse_json_arg(value_raw)
            if parsed is None or not isinstance(parsed, list):
                print(MESSAGE_ERR_DEVICE_FIELD_LIST)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            entry[store_key] = parsed
        elif field_type == DEVICE_FIELD_DICT:
            parsed = parse_json_arg(value_raw)
            if parsed is None or not isinstance(parsed, dict):
                print(MESSAGE_ERR_DEVICE_FIELD_DICT)
                return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
            entry[field_key] = parsed
        else:
            entry[store_key] = value_raw
        if field_key == FIELD_DEVICE_INTERFACE:
            interface = str(get_device_interface(entry) or "").strip()
            if interface and interface not in DEVICE_INTERFACE_ALLOWED:
                print(MESSAGE_ERR_DEVICE_INTERFACE_INVALID)
                return StatusResult(code=SS__DEVICE__INVALID_FIELD)
        self._mark_profiles_dirty()
        self._refresh_devices_from_profiles()
        self._validate_device_entry(entry)
        return StatusResult(code=SS__NORMAL)

    def _ensure_profile_device_label(self, name: str) -> None:
        """
        NAME
            _ensure_profile_device_label - Ensure a device label is in the active profile.
        """
        profile_name = self._active_profile_name()
        if not profile_name:
            return
        payload = self._local_root_payload
        if not isinstance(payload, dict):
            return
        profiles = payload.get(KEY_PROFILES)
        if not isinstance(profiles, dict):
            return
        profile = profiles.get(profile_name)
        if not isinstance(profile, dict):
            return
        labels = profile.get(KEY_PROFILE_DEVICES)
        if not isinstance(labels, list):
            labels = []
            profile[KEY_PROFILE_DEVICES] = labels
        if name not in labels:
            labels.append(name)
            self._mark_profiles_dirty()
            self._refresh_devices_from_profiles()

    def _clear_profiles_device_meta(self, name: str, field: str) -> StatusResult:
        """
        NAME
            _clear_profiles_device_meta - Clear a device field in profiles.
        """
        entry = self._find_profiles_device_entry(name)
        if entry is None:
            print("ERROR: Device not found in profiles.")
            return StatusResult(code=SS__DEVICE__NOT_FOUND)
        field_key = self._normalize_device_field(field.strip())
        if field_key == FIELD_LABEL:
            print("ERROR: device label is managed by rename device.")
            return StatusResult(code=SS__DEVICE__INVALID_FIELD)
        if field_key not in DEVICE_FIELDS_PROFILE:
            print(MESSAGE_ERR_DEVICE_FIELD_UNKNOWN)
            return StatusResult(code=SS__DEVICE__INVALID_FIELD)
        store_key = FIELD_TYPE if field_key == FIELD_ROLE else field_key
        entry.pop(store_key, None)
        self._mark_profiles_dirty()
        self._refresh_devices_from_profiles()
        self._validate_device_entry(entry)
        return StatusResult(code=SS__NORMAL)

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
            self._refresh_tests_profile(profile)
    def _export_cli_script(self, path: str) -> StatusResult:
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
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        config = self._local_config
        lines: List[str] = []
        if self._local_devices_locked:
            if self._local_root_path:
                lines.append(f'merge config "{self._local_root_path}"')
            else:
                lines.append("# NOTE: devices are derived from profiles; merge a profiles file first.")
        lines.append("configure terminal")
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
                        device = _group_member_label(member)
                        enabled = bool(member.get("enabled", True)) if isinstance(member, dict) else True
                        if not device:
                            continue
                        lines.append(f'member assign "{device}"')
                        if not enabled:
                            lines.append(f'member disable "{device}"')
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
            return StatusResult(code=SS__CONFIG__INVALID)
        print(f"Wrote CLI script to {path}.")
        return StatusResult(code=SS__NORMAL)

    def _export_profile_bundle(
        self,
        profile_name: str,
        path: str,
        *,
        install_robot: bool = False,
    ) -> StatusResult:
        """
        NAME
            _export_profile_bundle - Export a profile JSON snapshot and CLI script.
        """
        payload = self._local_root_payload
        if not isinstance(payload, dict):
            print(MESSAGE_PROFILE_EXPORT_NONE)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        profiles = payload.get(KEY_PROFILES)
        if not isinstance(profiles, dict):
            print(MESSAGE_PROFILE_EXPORT_NONE)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        profile_entry = profiles.get(profile_name)
        if not isinstance(profile_entry, dict):
            print(MESSAGE_PROFILE_EXPORT_UNKNOWN.format(name=profile_name))
            return StatusResult(code=SS__CONFIG__INVALID)
        device_entries = self._profile_export_registry_entries(profile_name)
        self._ensure_local_config()
        bridge_entry = self._local_profile_entry(profile_name, create=True)
        bridge_config = {
            KEY_BRIDGE_SCHEMA_VERSION: BRIDGE_CONFIG_SCHEMA_VERSION,
            KEY_BRIDGE_GENERATED_AT: None,
            KEY_BRIDGE_BY_PROFILE: {profile_name: deepcopy(bridge_entry)},
        }
        export_payload: Dict[str, object] = {
            KEY_SCHEMA_VERSION: PROFILE_SCHEMA_VERSION,
            KEY_DATA_VERSION: timestamp_version(),
            KEY_DEFAULT_PROFILE: profile_name,
            KEY_PROFILES: {profile_name: deepcopy(profile_entry)},
            KEY_DEVICES: deepcopy(device_entries),
            KEY_BRIDGE_CONFIG: bridge_config,
        }
        topology_root = payload.get(KEY_TOPOLOGY)
        if isinstance(topology_root, dict):
            topology_profiles = topology_root.get(KEY_TOPOLOGY_PROFILES)
            if isinstance(topology_profiles, dict):
                topology_entry = topology_profiles.get(profile_name)
                if isinstance(topology_entry, dict):
                    export_payload[KEY_TOPOLOGY] = {
                        KEY_TOPOLOGY_VERSION: topology_root.get(KEY_TOPOLOGY_VERSION, COUNT_ONE),
                        KEY_TOPOLOGY_SOURCE: topology_root.get(
                            KEY_TOPOLOGY_SOURCE, TOPOLOGY_SOURCE_LOCAL
                        ),
                        KEY_TOPOLOGY_PROFILES: {profile_name: deepcopy(topology_entry)},
                    }
        export_payload[KEY_DATA_HASH] = compute_profiles_hash(export_payload)
        json_path, script_path, error = self._resolve_profile_export_paths(profile_name, path)
        if error:
            print(MESSAGE_PROFILE_EXPORT_WRITE_FAIL.format(detail=error))
            return StatusResult(code=SS__CONFIG__INVALID)
        try:
            write_json(Path(json_path), export_payload, indent=PROFILE_EXPORT_INDENT)
            script_lines = self._profile_export_script_lines(
                profile_name,
                json_path,
                install_robot=install_robot,
            )
            Path(script_path).write_text(
                PROFILE_EXPORT_NEWLINE.join(script_lines) + PROFILE_EXPORT_NEWLINE,
                encoding=ENCODING_UTF8,
            )
        except Exception as exc:
            print(MESSAGE_PROFILE_EXPORT_WRITE_FAIL.format(detail=str(exc)))
            return StatusResult(code=SS__CONFIG__INVALID)
        print(
            MESSAGE_PROFILE_EXPORT_WRITTEN.format(
                json_path=json_path,
                script_path=script_path,
            )
        )
        return StatusResult(code=SS__NORMAL)

    def _export_profiles_bundle(self, path: str) -> StatusResult:
        """
        NAME
            _export_profiles_bundle - Export all profiles JSON snapshot and CLI script.
        """
        payload = self._local_root_payload
        if not isinstance(payload, dict):
            print(MESSAGE_PROFILE_EXPORT_NONE)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        profiles = payload.get(KEY_PROFILES)
        if not isinstance(profiles, dict) or not profiles:
            print(MESSAGE_PROFILE_EXPORT_NONE)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        export_payload: Dict[str, object] = {
            KEY_SCHEMA_VERSION: PROFILE_SCHEMA_VERSION,
            KEY_DATA_VERSION: timestamp_version(),
            KEY_DEFAULT_PROFILE: self._default_profile_name(),
            KEY_PROFILES: deepcopy(profiles),
            KEY_DEVICES: deepcopy(payload.get(KEY_DEVICES, [])),
        }
        bridge_config = payload.get(KEY_BRIDGE_CONFIG)
        if isinstance(bridge_config, dict):
            export_payload[KEY_BRIDGE_CONFIG] = deepcopy(bridge_config)
        topology_root = payload.get(KEY_TOPOLOGY)
        if isinstance(topology_root, dict):
            export_payload[KEY_TOPOLOGY] = deepcopy(topology_root)
        export_payload[KEY_DATA_HASH] = compute_profiles_hash(export_payload)
        json_path, script_path, error = self._resolve_profiles_export_paths(path)
        if error:
            print(MESSAGE_PROFILE_EXPORT_WRITE_FAIL.format(detail=error))
            return StatusResult(code=SS__CONFIG__INVALID)
        try:
            write_json(Path(json_path), export_payload, indent=PROFILE_EXPORT_INDENT)
            script_lines = self._profiles_export_script_lines(json_path)
            Path(script_path).write_text(
                PROFILE_EXPORT_NEWLINE.join(script_lines) + PROFILE_EXPORT_NEWLINE,
                encoding=ENCODING_UTF8,
            )
        except Exception as exc:
            print(MESSAGE_PROFILE_EXPORT_WRITE_FAIL.format(detail=str(exc)))
            return StatusResult(code=SS__CONFIG__INVALID)
        print(
            MESSAGE_PROFILES_EXPORT_WRITTEN.format(
                json_path=json_path,
                script_path=script_path,
            )
        )
        return StatusResult(code=SS__NORMAL)

    def _resolve_profile_export_paths(
        self, profile_name: str, path: str
    ) -> tuple[str, str, str]:
        """
        NAME
            _resolve_profile_export_paths - Resolve JSON/script output paths.
        """
        target = Path(path)
        json_path = EMPTY_STRING
        script_path = EMPTY_STRING
        error = EMPTY_STRING
        if target.exists() and target.is_dir():
            json_name = PROFILE_EXPORT_JSON_FMT.format(profile=profile_name)
            script_name = PROFILE_EXPORT_SCRIPT_FMT.format(profile=profile_name)
            json_path = str(target / json_name)
            script_path = str(target / script_name)
            return (json_path, script_path, error)
        suffix = target.suffix.lower()
        if suffix == PROFILE_EXPORT_JSON_SUFFIX:
            json_path = str(target)
            script_path = str(target.with_suffix(PROFILE_EXPORT_SCRIPT_SUFFIX))
        elif suffix == PROFILE_EXPORT_SCRIPT_SUFFIX:
            script_path = str(target)
            json_path = str(target.with_suffix(PROFILE_EXPORT_JSON_SUFFIX))
        else:
            json_path = str(target.with_suffix(PROFILE_EXPORT_JSON_SUFFIX))
            script_path = str(target.with_suffix(PROFILE_EXPORT_SCRIPT_SUFFIX))
        parent = Path(json_path).parent
        if not parent.exists():
            error = MESSAGE_PROFILE_EXPORT_PATH_INVALID.format(path=str(parent))
            return (EMPTY_STRING, EMPTY_STRING, error)
        return (json_path, script_path, error)

    def _resolve_profiles_export_paths(self, path: str) -> tuple[str, str, str]:
        """
        NAME
            _resolve_profiles_export_paths - Resolve JSON/script output paths for all profiles.
        """
        target = Path(path)
        json_path = EMPTY_STRING
        script_path = EMPTY_STRING
        error = EMPTY_STRING
        if target.exists() and target.is_dir():
            json_path = str(target / PROFILES_EXPORT_JSON_NAME)
            script_path = str(target / PROFILES_EXPORT_SCRIPT_NAME)
            return (json_path, script_path, error)
        suffix = target.suffix.lower()
        if suffix == PROFILE_EXPORT_JSON_SUFFIX:
            json_path = str(target)
            script_path = str(target.with_suffix(PROFILE_EXPORT_SCRIPT_SUFFIX))
        elif suffix == PROFILE_EXPORT_SCRIPT_SUFFIX:
            script_path = str(target)
            json_path = str(target.with_suffix(PROFILE_EXPORT_JSON_SUFFIX))
        else:
            json_path = str(target.with_suffix(PROFILE_EXPORT_JSON_SUFFIX))
            script_path = str(target.with_suffix(PROFILE_EXPORT_SCRIPT_SUFFIX))
        parent = Path(json_path).parent
        if not parent.exists():
            error = MESSAGE_PROFILE_EXPORT_PATH_INVALID.format(path=str(parent))
            return (EMPTY_STRING, EMPTY_STRING, error)
        return (json_path, script_path, error)

    def _profile_export_script_lines(
        self,
        profile_name: str,
        json_path: str,
        *,
        install_robot: bool = False,
    ) -> List[str]:
        """
        NAME
            _profile_export_script_lines - Build a CLI batch script for profile import.
        """
        profile_token = self._quote_if_needed(profile_name)
        lines = [
            PROFILE_EXPORT_SCRIPT_HEADER,
            PROFILE_EXPORT_HEADER_ECHO,
            PROFILE_EXPORT_HEADER_SAVE_NEW,
        ]
        lines.append(
            PROFILE_EXPORT_CMD_CONFIGURE
            + PROFILE_EXPORT_PATH_SEPARATOR
            + PROFILE_EXPORT_CMD_TERMINAL
        )
        lines.append(
            PROFILE_EXPORT_CMD_PROFILES
            + PROFILE_EXPORT_PATH_SEPARATOR
            + CMD_INIT
        )
        lines.append(CMD_BINDINGS + PROFILE_EXPORT_PATH_SEPARATOR + CMD_CLEAR)
        lines.append(CMD_CAN_MAPPINGS + PROFILE_EXPORT_PATH_SEPARATOR + CMD_CLEAR)
        lines.extend(self._profile_export_global_lines())
        lines.append(
            PROFILE_EXPORT_CMD_PROFILE
            + PROFILE_EXPORT_PATH_SEPARATOR
            + PROFILE_EXPORT_CMD_CREATE
            + PROFILE_EXPORT_PATH_SEPARATOR
            + profile_token
        )
        lines.append(PROFILE_EXPORT_CMD_PROFILE + PROFILE_EXPORT_PATH_SEPARATOR + profile_token)
        lines.extend(self._profile_export_device_lines(profile_name))
        lines.extend(self._profile_export_group_lines(profile_name))
        lines.extend(self._profile_export_tests_lines(profile_name))
        lines.extend(self._profile_export_selected_lines(profile_name))
        lines.append(
            PROFILE_EXPORT_CMD_PROFILE
            + PROFILE_EXPORT_PATH_SEPARATOR
            + PROFILE_EXPORT_CMD_DEFAULT
            + PROFILE_EXPORT_PATH_SEPARATOR
            + profile_token
        )
        lines.append(CMD_VALIDATE + PROFILE_EXPORT_PATH_SEPARATOR + CMD_ALL)
        lines.extend(self._profile_export_save_source_lines())
        if install_robot:
            lines.extend(self._profile_export_robot_install_lines(profile_name, json_path))
        lines.append(PROFILE_EXPORT_CMD_EXIT)
        return lines

    def _profile_export_robot_install_lines(self, profile_name: str, json_path: str) -> List[str]:
        """
        NAME
            _profile_export_robot_install_lines - Build robot install/test commands.
        """
        profile_token = self._quote_if_needed(profile_name)
        json_token = self._quote_if_needed(json_path)
        lines = [
            PROFILE_EXPORT_HEADER_INSTALL_ROBOT,
            CMD_END,
            CMD_CONNECT,
            (
                PROFILE_EXPORT_CMD_CONFIGURE
                + PROFILE_EXPORT_PATH_SEPARATOR
                + PROFILE_EXPORT_CMD_TERMINAL
            ),
            (
                PROFILE_EXPORT_CMD_CONFIG
                + PROFILE_EXPORT_PATH_SEPARATOR
                + CMD_PUSH
                + PROFILE_EXPORT_PATH_SEPARATOR
                + json_token
                + PROFILE_EXPORT_PATH_SEPARATOR
                + CMD_ACTIVATE
                + PROFILE_EXPORT_PATH_SEPARATOR
                + profile_token
            ),
            (
                PROFILE_EXPORT_CMD_SHOW
                + PROFILE_EXPORT_PATH_SEPARATOR
                + SHOW_TARGET_PROFILE
                + PROFILE_EXPORT_PATH_SEPARATOR
                + profile_token
                + PROFILE_EXPORT_PATH_SEPARATOR
                + CMD_ROBOT
                + PROFILE_EXPORT_PATH_SEPARATOR
                + FLAG_JSON
                + PROFILE_EXPORT_PATH_SEPARATOR
                + FLAG_PRETTY
            ),
            (
                PROFILE_EXPORT_CMD_SHOW
                + PROFILE_EXPORT_PATH_SEPARATOR
                + SHOW_TARGET_DEVICES
                + PROFILE_EXPORT_PATH_SEPARATOR
                + CMD_ROBOT
                + PROFILE_EXPORT_PATH_SEPARATOR
                + FLAG_JSON
                + PROFILE_EXPORT_PATH_SEPARATOR
                + FLAG_PRETTY
            ),
            (
                PROFILE_EXPORT_CMD_SHOW
                + PROFILE_EXPORT_PATH_SEPARATOR
                + CMD_TESTS
                + PROFILE_EXPORT_PATH_SEPARATOR
                + CMD_ROBOT
                + PROFILE_EXPORT_PATH_SEPARATOR
                + FLAG_JSON
                + PROFILE_EXPORT_PATH_SEPARATOR
                + FLAG_PRETTY
            ),
            (
                PROFILE_EXPORT_CMD_SHOW
                + PROFILE_EXPORT_PATH_SEPARATOR
                + SHOW_TARGET_RUNTIME
                + PROFILE_EXPORT_PATH_SEPARATOR
                + CMD_ROBOT
                + PROFILE_EXPORT_PATH_SEPARATOR
                + FLAG_JSON
                + PROFILE_EXPORT_PATH_SEPARATOR
                + FLAG_PRETTY
            ),
        ]
        for test_name in self._profile_export_test_names(profile_name):
            test_token = self._quote_if_needed(test_name)
            lines.append(
                CMD_TESTS
                + PROFILE_EXPORT_PATH_SEPARATOR
                + CMD_SELECT
                + PROFILE_EXPORT_PATH_SEPARATOR
                + test_token
            )
            lines.append(CMD_TESTS + PROFILE_EXPORT_PATH_SEPARATOR + CMD_RUN)
            lines.append(
                CMD_TESTS
                + PROFILE_EXPORT_PATH_SEPARATOR
                + CMD_WAIT
                + PROFILE_EXPORT_PATH_SEPARATOR
                + FLAG_TIMEOUT
                + PROFILE_EXPORT_PATH_SEPARATOR
                + str(TEST_WAIT_DEFAULT_TIMEOUT_SEC)
            )
            lines.append(
                PROFILE_EXPORT_CMD_SHOW
                + PROFILE_EXPORT_PATH_SEPARATOR
                + CMD_TESTS
                + PROFILE_EXPORT_PATH_SEPARATOR
                + CMD_ROBOT
                + PROFILE_EXPORT_PATH_SEPARATOR
                + FLAG_JSON
                + PROFILE_EXPORT_PATH_SEPARATOR
                + FLAG_PRETTY
            )
        return lines

    def _profile_export_test_names(self, profile_name: str) -> List[str]:
        """
        NAME
            _profile_export_test_names - Return exported test names for a profile.
        """
        self._ensure_local_config()
        entry = self._local_profile_entry(profile_name, create=True)
        tests_payload = entry.get(KEY_BRIDGE_TESTS) if isinstance(entry, dict) else None
        model = model_from_payload(tests_payload or {})
        names: List[str] = []
        if not model or not model.test_sets:
            return names
        for set_name in sorted(model.test_sets.keys()):
            test_set = model.test_sets.get(set_name)
            if not test_set:
                continue
            for test in test_set.tests:
                if test and test.name:
                    names.append(test.name)
        return names

    def _profiles_export_script_lines(self, json_path: str) -> List[str]:
        """
        NAME
            _profiles_export_script_lines - Build a CLI batch script for all profiles.
        """
        payload = self._local_root_payload
        profiles = payload.get(KEY_PROFILES) if isinstance(payload, dict) else None
        if not isinstance(profiles, dict):
            return []
        default_profile = self._default_profile_name()
        lines = [
            PROFILE_EXPORT_SCRIPT_HEADER_ALL,
            PROFILE_EXPORT_HEADER_ECHO,
            PROFILE_EXPORT_HEADER_SAVE_NEW,
        ]
        lines.append(
            PROFILE_EXPORT_CMD_CONFIGURE
            + PROFILE_EXPORT_PATH_SEPARATOR
            + PROFILE_EXPORT_CMD_TERMINAL
        )
        lines.append(
            PROFILE_EXPORT_CMD_PROFILES
            + PROFILE_EXPORT_PATH_SEPARATOR
            + CMD_INIT
        )
        lines.append(CMD_BINDINGS + PROFILE_EXPORT_PATH_SEPARATOR + CMD_CLEAR)
        lines.append(CMD_CAN_MAPPINGS + PROFILE_EXPORT_PATH_SEPARATOR + CMD_CLEAR)
        lines.extend(self._profile_export_global_lines())
        for profile_name in sorted(profiles.keys()):
            profile_token = self._quote_if_needed(profile_name)
            lines.append(
                PROFILE_EXPORT_CMD_PROFILE
                + PROFILE_EXPORT_PATH_SEPARATOR
                + PROFILE_EXPORT_CMD_CREATE
                + PROFILE_EXPORT_PATH_SEPARATOR
                + profile_token
            )
            lines.append(PROFILE_EXPORT_CMD_PROFILE + PROFILE_EXPORT_PATH_SEPARATOR + profile_token)
            lines.extend(self._profile_export_device_lines(profile_name))
            lines.extend(self._profile_export_group_lines(profile_name))
            lines.extend(self._profile_export_tests_lines(profile_name))
            lines.extend(self._profile_export_selected_lines(profile_name))
        if default_profile:
            lines.append(
                PROFILE_EXPORT_CMD_PROFILE
                + PROFILE_EXPORT_PATH_SEPARATOR
                + PROFILE_EXPORT_CMD_DEFAULT
                + PROFILE_EXPORT_PATH_SEPARATOR
                + self._quote_if_needed(default_profile)
            )
        lines.append(CMD_VALIDATE + PROFILE_EXPORT_PATH_SEPARATOR + CMD_ALL)
        lines.extend(self._profile_export_save_source_lines())
        lines.append(PROFILE_EXPORT_CMD_EXIT)
        return lines

    def _profile_export_save_source_lines(self) -> List[str]:
        """
        NAME
            _profile_export_save_source_lines - Build explicit save commands.
        """
        profiles_path = self._local_root_path or self._config_repository.canonical_path()
        bindings_path = self._bindings_path or bindings_deploy_path()
        mappings_path = self._can_mappings_path or can_mappings_path()
        return [
            (
                CMD_SAVE
                + PROFILE_EXPORT_PATH_SEPARATOR
                + CMD_CONFIG
                + PROFILE_EXPORT_PATH_SEPARATOR
                + self._quote_if_needed(str(profiles_path))
            ),
            (
                CMD_BINDINGS
                + PROFILE_EXPORT_PATH_SEPARATOR
                + CMD_SAVE
                + PROFILE_EXPORT_PATH_SEPARATOR
                + self._quote_if_needed(str(bindings_path))
            ),
            (
                CMD_CAN_MAPPINGS
                + PROFILE_EXPORT_PATH_SEPARATOR
                + CMD_SAVE
                + PROFILE_EXPORT_PATH_SEPARATOR
                + self._quote_if_needed(str(mappings_path))
            ),
        ]

    def _profile_export_device_lines(self, profile_name: str) -> List[str]:
        """
        NAME
            _profile_export_device_lines - Build CLI lines for profile devices.
        """
        devices = self._profile_export_registry_entries(profile_name)
        lines: List[str] = []
        for entry in devices:
            if not isinstance(entry, dict):
                continue
            label = str(entry.get(KEY_LABEL, EMPTY_STRING)).strip()
            if not label:
                continue
            label_token = self._quote_if_needed(label)
            for field in PROFILE_EXPORT_FIELD_ORDER:
                if field not in entry:
                    continue
                value = entry.get(field)
                if value is None:
                    continue
                value_token = self._format_cli_value(value)
                if value_token == EMPTY_STRING:
                    continue
                lines.append(
                    PROFILE_EXPORT_CMD_DEVICE
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + label_token
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + PROFILE_EXPORT_CMD_SET
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + field
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + value_token
                )
        return lines

    def _profile_export_global_lines(self) -> List[str]:
        """
        NAME
            _profile_export_global_lines - Build CLI lines for global bindings and CAN mappings.
        """
        lines: List[str] = []
        lines.extend(self._profile_export_bindings_lines())
        lines.extend(self._profile_export_can_mappings_lines())
        return lines

    def _profile_export_bindings_lines(self) -> List[str]:
        """
        NAME
            _profile_export_bindings_lines - Build CLI lines for global bindings.
        """
        if not self._ensure_bindings_loaded():
            return []
        payload = self._bindings_payload
        if not isinstance(payload, dict):
            return []
        lines: List[str] = []
        controllers = payload.get(KEY_CONTROLLERS, [])
        if isinstance(controllers, list):
            for entry in controllers:
                if not isinstance(entry, dict):
                    continue
                name = str(entry.get(KEY_NAME, EMPTY_STRING)).strip()
                ctrl_type = str(entry.get(FIELD_TYPE, EMPTY_STRING)).strip()
                port = entry.get(KEY_PORT)
                if not name or not ctrl_type or port is None:
                    continue
                lines.append(
                    CMD_BINDINGS
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + CMD_CONTROLLER
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + CMD_ADD
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + self._quote_if_needed(name)
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + self._quote_if_needed(ctrl_type)
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + self._format_cli_value(port)
                )
        bindings = payload.get(KEY_BINDINGS, [])
        if isinstance(bindings, list):
            for entry in bindings:
                if not isinstance(entry, dict):
                    continue
                command = str(entry.get(KEY_COMMAND, EMPTY_STRING)).strip()
                controller = str(entry.get(KEY_CONTROLLER, EMPTY_STRING)).strip()
                input_name = str(entry.get(KEY_INPUT, EMPTY_STRING)).strip()
                input_id = str(entry.get(KEY_ID, EMPTY_STRING)).strip()
                mode = str(entry.get(KEY_MODE, EMPTY_STRING)).strip()
                if not command or not controller or not input_name or not input_id or not mode:
                    continue
                line = (
                    CMD_BINDINGS
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + CMD_BINDING
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + CMD_ADD
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + self._quote_if_needed(command)
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + self._quote_if_needed(controller)
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + self._quote_if_needed(input_name)
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + self._quote_if_needed(input_id)
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + self._quote_if_needed(mode)
                )
                if input_name == "axis":
                    invert_token = PROFILE_EXPORT_CMD_ON if bool(entry.get(KEY_INVERT)) else PROFILE_EXPORT_CMD_OFF
                    deadband = entry.get(KEY_DEADBAND)
                    if deadband is None:
                        continue
                    line += (
                        PROFILE_EXPORT_PATH_SEPARATOR
                        + KEY_INVERT
                        + PROFILE_EXPORT_PATH_SEPARATOR
                        + invert_token
                        + PROFILE_EXPORT_PATH_SEPARATOR
                        + KEY_DEADBAND
                        + PROFILE_EXPORT_PATH_SEPARATOR
                        + self._format_cli_value(deadband)
                    )
                lines.append(line)
        return lines

    def _profile_export_can_mappings_lines(self) -> List[str]:
        """
        NAME
            _profile_export_can_mappings_lines - Build CLI lines for CAN mappings.
        """
        if not self._ensure_can_mappings_loaded():
            return []
        payload = self._can_mappings
        if not isinstance(payload, dict):
            return []
        lines: List[str] = []
        manufacturers = payload.get(KEY_MANUFACTURERS, {})
        if isinstance(manufacturers, dict):
            for key in sorted(manufacturers.keys(), key=lambda value: int(value) if str(value).isdigit() else value):
                name = manufacturers.get(key)
                if name is None:
                    continue
                lines.append(
                    CMD_CAN_MAPPINGS
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + CMD_MANUFACTURER
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + CMD_SET
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + self._format_cli_value(key)
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + self._quote_if_needed(str(name))
                )
        device_types = payload.get(KEY_DEVICE_TYPES, {})
        if isinstance(device_types, dict):
            for key in sorted(device_types.keys(), key=lambda value: int(value) if str(value).isdigit() else value):
                name = device_types.get(key)
                if name is None:
                    continue
                lines.append(
                    CMD_CAN_MAPPINGS
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + CMD_DEVICE_TYPE_NAME
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + CMD_SET
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + self._format_cli_value(key)
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + self._quote_if_needed(str(name))
                )
        return lines

    def _profile_export_registry_entries(self, profile_name: str) -> List[Dict[str, object]]:
        """
        NAME
            _profile_export_registry_entries - Gather raw registry device entries for a profile.
        """
        payload = self._local_root_payload
        if not isinstance(payload, dict):
            return []
        profiles = payload.get(KEY_PROFILES)
        if not isinstance(profiles, dict):
            return []
        profile = profiles.get(profile_name)
        if not isinstance(profile, dict):
            return []
        labels = profile.get(KEY_PROFILE_DEVICES)
        if not isinstance(labels, list):
            return []
        registry_entries = payload.get(KEY_DEVICES)
        if not isinstance(registry_entries, list):
            return []
        registry: Dict[str, Dict[str, object]] = {}
        for entry in registry_entries:
            if not isinstance(entry, dict):
                continue
            label = str(entry.get(KEY_LABEL, EMPTY_STRING)).strip()
            if not label:
                continue
            registry[label.lower()] = entry
        ordered: List[Dict[str, object]] = []
        for label in labels:
            if not isinstance(label, str):
                continue
            entry = registry.get(label.lower())
            if entry is not None:
                ordered.append(entry)
        return ordered

    def _profile_export_group_lines(self, profile_name: str) -> List[str]:
        """
        NAME
            _profile_export_group_lines - Build CLI lines for profile groups/bindings.
        """
        self._ensure_local_config()
        entry = self._local_profile_entry(profile_name, create=True)
        groups = entry.get(KEY_BRIDGE_GROUPS, []) if isinstance(entry, dict) else []
        lines: List[str] = []
        for group in groups:
            if not isinstance(group, dict):
                continue
            name = str(group.get(KEY_NAME, EMPTY_STRING)).strip()
            if not name:
                continue
            name_token = self._quote_if_needed(name)
            lines.append(PROFILE_EXPORT_CMD_GROUP + PROFILE_EXPORT_PATH_SEPARATOR + name_token)
            members = group.get(KEY_MEMBERS, []) or []
            for member in members:
                device_name = EMPTY_STRING
                enabled = True
                if isinstance(member, dict):
                    device_name = _group_member_label(member)
                    enabled = bool(member.get(CMD_ENABLED, True))
                else:
                    device_name = str(member).strip()
                if not device_name:
                    continue
                device_token = self._quote_if_needed(device_name)
                lines.append(
                    PROFILE_EXPORT_CMD_MEMBER
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + PROFILE_EXPORT_CMD_ASSIGN
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + device_token
                )
                if not enabled:
                    lines.append(
                        PROFILE_EXPORT_CMD_MEMBER
                        + PROFILE_EXPORT_PATH_SEPARATOR
                        + PROFILE_EXPORT_CMD_MEMBER_DISABLE
                        + PROFILE_EXPORT_PATH_SEPARATOR
                        + device_token
                    )
            bindings = group.get(KEY_BRIDGE_BINDINGS, []) or []
            for binding in bindings:
                if not isinstance(binding, dict):
                    continue
                input_name = str(binding.get(KEY_INPUT, EMPTY_STRING)).strip()
                kind = str(binding.get(KEY_KIND, EMPTY_STRING)).strip()
                if not input_name or not kind:
                    continue
                bind_line = (
                    PROFILE_EXPORT_CMD_BIND
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + input_name
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + kind
                )
                if KEY_VALUE in binding:
                    value_token = self._format_cli_value(binding.get(KEY_VALUE))
                    if value_token:
                        bind_line += PROFILE_EXPORT_PATH_SEPARATOR + value_token
                lines.append(bind_line)
            if group.get(CMD_ENABLED) is False:
                lines.append(PROFILE_EXPORT_CMD_DISABLE)
            lines.append(PROFILE_EXPORT_CMD_EXIT)
        return lines

    def _profile_export_tests_lines(self, profile_name: str) -> List[str]:
        """
        NAME
            _profile_export_tests_lines - Build CLI lines for profile tests.
        """
        self._ensure_local_config()
        entry = self._local_profile_entry(profile_name, create=True)
        tests_payload = entry.get(KEY_BRIDGE_TESTS) if isinstance(entry, dict) else None
        model = model_from_payload(tests_payload or {})
        lines: List[str] = []
        if not model or not model.test_sets:
            return lines
        lines.append(PROFILE_EXPORT_CMD_TESTS + PROFILE_EXPORT_PATH_SEPARATOR + CMD_CLEAR)
        default_set = model.default_test_set or DEFAULT_TEST_SET
        if default_set:
            lines.append(
                PROFILE_EXPORT_CMD_TEST
                + PROFILE_EXPORT_PATH_SEPARATOR
                + PROFILE_EXPORT_CMD_TEST_SET
                + PROFILE_EXPORT_PATH_SEPARATOR
                + self._quote_if_needed(default_set)
            )
        for set_name in sorted(model.test_sets.keys()):
            test_set = model.test_sets.get(set_name)
            if not test_set:
                continue
            lines.append(
                PROFILE_EXPORT_CMD_TEST
                + PROFILE_EXPORT_PATH_SEPARATOR
                + PROFILE_EXPORT_CMD_TEST_SET
                + PROFILE_EXPORT_PATH_SEPARATOR
                + self._quote_if_needed(set_name)
            )
            for test in test_set.tests:
                if not test:
                    continue
                test_name = self._quote_if_needed(test.name)
                lines.append(
                    PROFILE_EXPORT_CMD_TEST
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + PROFILE_EXPORT_CMD_TEST_CREATE
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + test_name
                )
                lines.extend(self._profile_export_test_body_lines(test))
                lines.append(PROFILE_EXPORT_CMD_EXIT)
        return lines

    def _profile_export_test_body_lines(self, test: TestModel) -> List[str]:
        """
        NAME
            _profile_export_test_body_lines - Build test-mode commands for one test.
        """
        lines: List[str] = []
        if test.test_type:
            lines.append(
                PROFILE_EXPORT_CMD_TYPE
                + PROFILE_EXPORT_PATH_SEPARATOR
                + test.test_type
            )
        for device in test.devices or []:
            device_token = self._quote_if_needed(str(device))
            lines.append(
                PROFILE_EXPORT_CMD_DEVICE_SUB
                + PROFILE_EXPORT_PATH_SEPARATOR
                + PROFILE_EXPORT_CMD_DEVICE_ADD
                + PROFILE_EXPORT_PATH_SEPARATOR
                + device_token
            )
        if test.input_source:
            lines.append(
                PROFILE_EXPORT_CMD_INPUTSOURCE
                + PROFILE_EXPORT_PATH_SEPARATOR
                + self._quote_if_needed(test.input_source)
            )
        if test.test_type == TEST_TYPE_JOYSTICK and test.joystick:
            lines.append(
                PROFILE_EXPORT_CMD_DEADBAND
                + PROFILE_EXPORT_PATH_SEPARATOR
                + self._format_cli_value(test.joystick.deadband)
            )
        if test.test_type in (TEST_TYPE_BUTTON, TEST_TYPE_COMPOSITE) and test.button:
            lines.append(
                PROFILE_EXPORT_CMD_DUTY
                + PROFILE_EXPORT_PATH_SEPARATOR
                + self._format_cli_value(test.button.duty)
            )
        if test.test_type == TEST_TYPE_DEVICE_ACTION and test.device_action:
            if test.device_action.action:
                lines.append(
                    PROFILE_EXPORT_CMD_ACTION
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + self._quote_if_needed(test.device_action.action)
                )
            if test.device_action.color:
                lines.append(
                    PROFILE_EXPORT_CMD_COLOR
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + self._quote_if_needed(test.device_action.color)
                )
            if test.device_action.pattern:
                lines.append(
                    PROFILE_EXPORT_CMD_PATTERN
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + self._quote_if_needed(test.device_action.pattern)
                )
            if test.device_action.brightness is not None:
                lines.append(
                    PROFILE_EXPORT_CMD_BRIGHTNESS
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + self._format_cli_value(test.device_action.brightness)
                )
            if test.device_action.duration_sec is not None:
                lines.append(
                    PROFILE_EXPORT_CMD_DURATION
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + self._format_cli_value(test.device_action.duration_sec)
                )
        if test.test_type == TEST_TYPE_DEADBAND_SWEEP and test.deadband_sweep:
            sweep = test.deadband_sweep
            lines.extend(self._profile_export_deadband_sweep_lines(sweep))
        lines.extend(self._profile_export_termination_lines(test.termination))
        lines.extend(self._profile_export_enabled_line(test.enabled))
        return lines

    def _profile_export_deadband_sweep_lines(self, sweep: object) -> List[str]:
        """
        NAME
            _profile_export_deadband_sweep_lines - Build commands for deadband sweep tests.
        """
        if not isinstance(sweep, object):
            return []
        lines: List[str] = []
        if getattr(sweep, ATTR_SWEEP_START_DUTY, None) is not None:
            lines.append(
                PROFILE_EXPORT_CMD_DEADBAND_SWEEP
                + PROFILE_EXPORT_PATH_SEPARATOR
                + PROFILE_EXPORT_SWEEP_START_DUTY
                + PROFILE_EXPORT_PATH_SEPARATOR
                + self._format_cli_value(getattr(sweep, ATTR_SWEEP_START_DUTY))
            )
        if getattr(sweep, ATTR_SWEEP_MAX_DUTY, None) is not None:
            lines.append(
                PROFILE_EXPORT_CMD_DEADBAND_SWEEP
                + PROFILE_EXPORT_PATH_SEPARATOR
                + PROFILE_EXPORT_SWEEP_MAX_DUTY
                + PROFILE_EXPORT_PATH_SEPARATOR
                + self._format_cli_value(getattr(sweep, ATTR_SWEEP_MAX_DUTY))
            )
        if getattr(sweep, ATTR_SWEEP_STEP_DUTY, None) is not None:
            lines.append(
                PROFILE_EXPORT_CMD_DEADBAND_SWEEP
                + PROFILE_EXPORT_PATH_SEPARATOR
                + PROFILE_EXPORT_SWEEP_STEP_DUTY
                + PROFILE_EXPORT_PATH_SEPARATOR
                + self._format_cli_value(getattr(sweep, ATTR_SWEEP_STEP_DUTY))
            )
        if getattr(sweep, ATTR_SWEEP_STEP_HOLD_SEC, None) is not None:
            lines.append(
                PROFILE_EXPORT_CMD_DEADBAND_SWEEP
                + PROFILE_EXPORT_PATH_SEPARATOR
                + PROFILE_EXPORT_SWEEP_STEP_HOLD_SEC
                + PROFILE_EXPORT_PATH_SEPARATOR
                + self._format_cli_value(getattr(sweep, ATTR_SWEEP_STEP_HOLD_SEC))
            )
        if getattr(sweep, ATTR_SWEEP_MOTION_THRESHOLD_ROT, None) is not None:
            lines.append(
                PROFILE_EXPORT_CMD_DEADBAND_SWEEP
                + PROFILE_EXPORT_PATH_SEPARATOR
                + PROFILE_EXPORT_SWEEP_MOTION_THRESHOLD_ROT
                + PROFILE_EXPORT_PATH_SEPARATOR
                + self._format_cli_value(getattr(sweep, ATTR_SWEEP_MOTION_THRESHOLD_ROT))
            )
        if getattr(sweep, ATTR_SWEEP_REQUIRED_SAMPLES, None) is not None:
            lines.append(
                PROFILE_EXPORT_CMD_DEADBAND_SWEEP
                + PROFILE_EXPORT_PATH_SEPARATOR
                + PROFILE_EXPORT_SWEEP_REQUIRED_SAMPLES
                + PROFILE_EXPORT_PATH_SEPARATOR
                + self._format_cli_value(getattr(sweep, ATTR_SWEEP_REQUIRED_SAMPLES))
            )
        if getattr(sweep, ATTR_SWEEP_ENCODER_KEY, None):
            lines.append(
                PROFILE_EXPORT_CMD_DEADBAND_SWEEP
                + PROFILE_EXPORT_PATH_SEPARATOR
                + PROFILE_EXPORT_SWEEP_ENCODER_KEY
                + PROFILE_EXPORT_PATH_SEPARATOR
                + self._quote_if_needed(str(getattr(sweep, ATTR_SWEEP_ENCODER_KEY)))
            )
        if getattr(sweep, ATTR_SWEEP_ENCODER_SOURCE, None):
            lines.append(
                PROFILE_EXPORT_CMD_DEADBAND_SWEEP
                + PROFILE_EXPORT_PATH_SEPARATOR
                + PROFILE_EXPORT_SWEEP_ENCODER_SOURCE
                + PROFILE_EXPORT_PATH_SEPARATOR
                + self._quote_if_needed(str(getattr(sweep, ATTR_SWEEP_ENCODER_SOURCE)))
            )
        if getattr(sweep, ATTR_SWEEP_ENCODER_MOTOR_INDEX, None) is not None:
            lines.append(
                PROFILE_EXPORT_CMD_DEADBAND_SWEEP
                + PROFILE_EXPORT_PATH_SEPARATOR
                + PROFILE_EXPORT_SWEEP_ENCODER_MOTOR_INDEX
                + PROFILE_EXPORT_PATH_SEPARATOR
                + self._format_cli_value(getattr(sweep, ATTR_SWEEP_ENCODER_MOTOR_INDEX))
            )
        if getattr(sweep, ATTR_SWEEP_ENCODER_COUNTS_PER_REV, None) is not None:
            lines.append(
                PROFILE_EXPORT_CMD_DEADBAND_SWEEP
                + PROFILE_EXPORT_PATH_SEPARATOR
                + PROFILE_EXPORT_SWEEP_ENCODER_COUNTS_PER_REV
                + PROFILE_EXPORT_PATH_SEPARATOR
                + self._format_cli_value(getattr(sweep, ATTR_SWEEP_ENCODER_COUNTS_PER_REV))
            )
        return lines

    def _profile_export_termination_lines(self, term: TerminationModel) -> List[str]:
        """
        NAME
            _profile_export_termination_lines - Build termination command lines.
        """
        lines: List[str] = []
        if term.hold_enabled:
            lines.append(PROFILE_EXPORT_CMD_TERMINATION + PROFILE_EXPORT_PATH_SEPARATOR + PROFILE_EXPORT_CMD_HOLD)
        if term.time_sec is not None:
            lines.append(
                PROFILE_EXPORT_CMD_TERMINATION
                + PROFILE_EXPORT_PATH_SEPARATOR
                + PROFILE_EXPORT_CMD_TIME
                + PROFILE_EXPORT_PATH_SEPARATOR
                + self._format_cli_value(term.time_sec)
            )
        if term.rotation_limit is not None:
            lines.append(
                PROFILE_EXPORT_CMD_TERMINATION
                + PROFILE_EXPORT_PATH_SEPARATOR
                + PROFILE_EXPORT_CMD_ROTATION
                + PROFILE_EXPORT_PATH_SEPARATOR
                + self._format_cli_value(term.rotation_limit)
            )
        if term.rotation_encoder_key:
            lines.append(
                PROFILE_EXPORT_CMD_ROTATION
                + PROFILE_EXPORT_PATH_SEPARATOR
                + PROFILE_EXPORT_ROTATION_ENCODER_KEY
                + PROFILE_EXPORT_PATH_SEPARATOR
                + self._quote_if_needed(term.rotation_encoder_key)
            )
        if term.rotation_encoder_source:
            lines.append(
                PROFILE_EXPORT_CMD_ROTATION
                + PROFILE_EXPORT_PATH_SEPARATOR
                + PROFILE_EXPORT_ROTATION_ENCODER_SOURCE
                + PROFILE_EXPORT_PATH_SEPARATOR
                + self._quote_if_needed(term.rotation_encoder_source)
            )
        if term.rotation_encoder_motor_index is not None:
            lines.append(
                PROFILE_EXPORT_CMD_ROTATION
                + PROFILE_EXPORT_PATH_SEPARATOR
                + PROFILE_EXPORT_ROTATION_ENCODER_MOTOR_INDEX
                + PROFILE_EXPORT_PATH_SEPARATOR
                + self._format_cli_value(term.rotation_encoder_motor_index)
            )
        if term.rotation_encoder_counts_per_rev is not None:
            lines.append(
                PROFILE_EXPORT_CMD_ROTATION
                + PROFILE_EXPORT_PATH_SEPARATOR
                + PROFILE_EXPORT_ROTATION_ENCODER_COUNTS_PER_REV
                + PROFILE_EXPORT_PATH_SEPARATOR
                + self._format_cli_value(term.rotation_encoder_counts_per_rev)
            )
        if term.time_on_timeout:
            lines.append(
                PROFILE_EXPORT_CMD_TIME
                + PROFILE_EXPORT_PATH_SEPARATOR
                + PROFILE_EXPORT_TIME_ON_TIMEOUT
                + PROFILE_EXPORT_PATH_SEPARATOR
                + self._quote_if_needed(term.time_on_timeout)
            )
        if term.hold_on_release:
            lines.append(
                PROFILE_EXPORT_CMD_HOLD
                + PROFILE_EXPORT_PATH_SEPARATOR
                + PROFILE_EXPORT_HOLD_ON_RELEASE
                + PROFILE_EXPORT_PATH_SEPARATOR
                + self._quote_if_needed(term.hold_on_release)
            )
        if isinstance(term.limit_switch, dict):
            limit_id = term.limit_switch.get(PROFILE_EXPORT_LIMITSWITCH_ID)
            on_hit = term.limit_switch.get(PROFILE_EXPORT_LIMITSWITCH_ON_HIT)
            if limit_id is not None:
                lines.append(
                    PROFILE_EXPORT_CMD_LIMITSWITCH
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + PROFILE_EXPORT_LIMITSWITCH_ID
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + self._format_cli_value(limit_id)
                )
            if on_hit:
                lines.append(
                    PROFILE_EXPORT_CMD_LIMITSWITCH
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + PROFILE_EXPORT_LIMITSWITCH_ON_HIT
                    + PROFILE_EXPORT_PATH_SEPARATOR
                    + self._quote_if_needed(str(on_hit))
                )
        if term.limit_switch:
            limit_id = term.limit_switch.get(PROFILE_EXPORT_LIMITSWITCH_ID) if isinstance(term.limit_switch, dict) else None
            lines.append(
                PROFILE_EXPORT_CMD_TERMINATION
                + PROFILE_EXPORT_PATH_SEPARATOR
                + PROFILE_EXPORT_CMD_LIMITSWITCH
                + (
                    PROFILE_EXPORT_PATH_SEPARATOR + self._format_cli_value(limit_id)
                    if limit_id is not None
                    else EMPTY_STRING
                )
            )
        return lines

    def _profile_export_enabled_line(self, enabled: bool) -> List[str]:
        """
        NAME
            _profile_export_enabled_line - Build the enabled command line.
        """
        value = PROFILE_EXPORT_BOOL_TRUE if enabled else PROFILE_EXPORT_BOOL_FALSE
        return [PROFILE_EXPORT_CMD_ENABLED + PROFILE_EXPORT_PATH_SEPARATOR + value]

    def _profile_export_selected_lines(self, profile_name: str) -> List[str]:
        """
        NAME
            _profile_export_selected_lines - Build selected-device commands.
        """
        entry = self._local_profile_entry(profile_name, create=True)
        selected = entry.get(KEY_BRIDGE_SELECTED_DEVICE, {}) if isinstance(entry, dict) else {}
        if not isinstance(selected, dict):
            return []
        device_name = str(selected.get(KEY_DEVICE, EMPTY_STRING)).strip()
        enabled = selected.get(CMD_ENABLED)
        lines: List[str] = []
        if device_name:
            lines.append(
                PROFILE_EXPORT_CMD_SELECTED_DEVICE
                + PROFILE_EXPORT_PATH_SEPARATOR
                + self._quote_if_needed(device_name)
            )
        if enabled is True:
            lines.append(
                PROFILE_EXPORT_CMD_SELECTED_MODE
                + PROFILE_EXPORT_PATH_SEPARATOR
                + PROFILE_EXPORT_CMD_ON
            )
        elif enabled is False:
            lines.append(
                PROFILE_EXPORT_CMD_SELECTED_MODE
                + PROFILE_EXPORT_PATH_SEPARATOR
                + PROFILE_EXPORT_CMD_OFF
            )
        return lines

    def _format_cli_value(self, value: object) -> str:
        """
        NAME
            _format_cli_value - Format a CLI value token.
        """
        if isinstance(value, bool):
            return PROFILE_EXPORT_BOOL_TRUE if value else PROFILE_EXPORT_BOOL_FALSE
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, (list, dict)):
            return json.dumps(value, separators=PROFILE_EXPORT_JSON_SEPARATORS)
        if value is None:
            return EMPTY_STRING
        return self._quote_if_needed(str(value))

    def _quote_if_needed(self, value: str) -> str:
        """
        NAME
            _quote_if_needed - Quote a value when it contains spaces.
        """
        if not value:
            return EMPTY_STRING
        if PROFILE_EXPORT_PATH_SEPARATOR in value and PROFILE_EXPORT_QUOTE not in value:
            return PROFILE_EXPORT_QUOTE + value + PROFILE_EXPORT_QUOTE
        return value

    def _lint_script(self, lines: List[str]) -> Optional[str]:
        """
        NAME
            _lint_script - Validate script ordering and device references.
        """
        known_devices = set()
        mode_stack: List[str] = ["exec"]
        for raw in lines:
            line = raw.strip()
            if line.startswith("\ufeff"):
                line = line.lstrip("\ufeff").lstrip()
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
                    return f"Device '{tokens[2]}' not defined before member assign."
            if cmd == CMD_MEMBER and len(tokens) >= COUNT_THREE:
                if tokens[1].lower() == CMD_ASSIGN and tokens[2].lower() not in (CMD_ALL, CMD_NEXT):
                    device = tokens[2].strip().lower()
                    if known_devices and device not in known_devices:
                        return f"Device '{tokens[2]}' not defined before member assign."
                if (
                    len(tokens) >= COUNT_THREE
                    and tokens[COUNT_TWO].lower() in (CMD_ENABLE, CMD_DISABLE, CMD_TOGGLE)
                ):
                    device = tokens[1].strip().lower()
                    if known_devices and device not in known_devices:
                        return f"Device '{tokens[1]}' not defined before member update."
            if cmd == CMD_GROUP and len(tokens) >= COUNT_FIVE and tokens[1].lower() == CMD_MEMBER:
                action = tokens[2].lower()
                if action == CMD_ASSIGN and tokens[3].lower() in (CMD_ALL, CMD_NEXT):
                    continue
                device = tokens[4].strip().lower()
                if known_devices and device not in known_devices:
                    return f"Label '{tokens[4]}' not defined before group member command."
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

    def _device_ref_group_name(self, name: str) -> Optional[str]:
        """
        NAME
            _device_ref_group_name - Return first group name that references a device.
        """
        config = self._local_config or {}
        by_profile = config.get(KEY_BRIDGE_BY_PROFILE) if isinstance(config, dict) else None
        if not isinstance(by_profile, dict):
            return None
        for entry in by_profile.values():
            if not isinstance(entry, dict):
                continue
            for group in entry.get(KEY_BRIDGE_GROUPS, []) or []:
                if not isinstance(group, dict):
                    continue
                group_name = str(group.get(KEY_NAME, EMPTY_STRING)).strip()
                for member in group.get("members", []) or []:
                    dev_name = _group_member_label(member)
                    if dev_name.lower() == name.strip().lower():
                        return group_name
        return None

    def _device_ref_test_name(self, name: str) -> Optional[str]:
        """
        NAME
            _device_ref_test_name - Return first test that references a device label.
        """
        self._ensure_tests_loaded()
        model = self._tests_model
        if model is None:
            return None
        key = name.strip().lower()
        for test_set in model.test_sets.values():
            if not isinstance(test_set, TestSetModel):
                continue
            for test in test_set.tests:
                if not isinstance(test, TestModel):
                    continue
                for label in test.devices:
                    if isinstance(label, str) and label.strip().lower() == key:
                        return test.name
                term = test.termination
                if term and isinstance(term.limit_switch, dict):
                    limit_id = term.limit_switch.get(KEY_LIMIT_SWITCH_ID)
                    if isinstance(limit_id, str) and limit_id.strip().lower() == key:
                        return test.name
                if term and isinstance(term.rotation_encoder_key, str):
                    if term.rotation_encoder_key.strip().lower() == key:
                        return test.name
                deadband = test.deadband_sweep
                if deadband and isinstance(deadband.encoder_key, str):
                    if deadband.encoder_key.strip().lower() == key:
                        return test.name
        return None

    def _group_ref_test_name(self, name: str) -> Optional[str]:
        """
        NAME
            _group_ref_test_name - Return first test that references a group name.

        NOTES
            V1 compatibility scans test device targets for an exact (case-insensitive)
            group-name match.
        """
        self._ensure_tests_loaded()
        model = self._tests_model
        if model is None:
            return None
        key = name.strip().lower()
        for test_set in model.test_sets.values():
            if not isinstance(test_set, TestSetModel):
                continue
            for test in test_set.tests:
                if not isinstance(test, TestModel):
                    continue
                for label in test.devices:
                    if isinstance(label, str) and label.strip().lower() == key:
                        return test.name
        return None

    @staticmethod
    def _ordered_bridge_config(config: Dict[str, object]) -> Dict[str, object]:
        """
        NAME
            _ordered_bridge_config - Normalize bridgeConfig key order for output.
        """
        ordered: Dict[str, object] = {
            KEY_BRIDGE_SCHEMA_VERSION: config.get(KEY_BRIDGE_SCHEMA_VERSION, BRIDGE_CONFIG_SCHEMA_VERSION),
            KEY_BRIDGE_GENERATED_AT: config.get(KEY_BRIDGE_GENERATED_AT),
        }
        by_profile = config.get(KEY_BRIDGE_BY_PROFILE)
        ordered_by_profile = dict(by_profile) if isinstance(by_profile, dict) else {}
        ordered[KEY_BRIDGE_BY_PROFILE] = ordered_by_profile
        return ordered

    def _local_device_exists(self, name: str) -> bool:
        """
        NAME
            _local_device_exists - Check if a device entry exists in local config.
        """
        name = self._normalize_device_label_input(name)
        if self._local_root_payload is not None:
            profile = self._active_profile_name()
            if profile:
                return name.strip().lower() in self._profile_object_labels(profile)
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
            self._local_devices_locked = True
            self._profiles_dirty = False
            self._groups_dirty = False
        self._ensure_default_profile_context()

    def _mark_groups_dirty(self) -> None:
        """
        NAME
            _mark_groups_dirty - Mark local group config as dirty.
        """

        self._groups_dirty = True
        self._record_last_modified()

    def _mark_tests_dirty(self) -> None:
        """
        NAME
            _mark_tests_dirty - Mark tests state as dirty and sync payload.
        """

        self._tests_dirty = True
        self._record_last_modified()
        self._sync_store_tests()

    def _mirror_repo_save_target(
        self,
        primary_path: Path,
        canonical_path: Path,
        deploy_path: Path,
    ) -> Optional[Path]:
        """
        NAME
            _mirror_repo_save_target - Return repo sibling path for mirrored saves.
        """

        primary = primary_path.resolve()
        canonical = canonical_path.resolve()
        deploy = deploy_path.resolve()
        if canonical == deploy:
            return None
        if primary == canonical:
            return deploy
        if primary == deploy:
            return canonical
        return None

    def _build_unified_payload(self) -> Optional[Dict[str, object]]:
        """
        NAME
            _build_unified_payload - Build a bringup_system.json payload from local state.
        """
        if not self._local_config:
            print("ERROR: Local config not loaded. Use merge/import config <bringup_system.json>.")
            return None
        self._sync_store_tests()
        payload: Dict[str, object] = deepcopy(self._local_root_payload) if self._local_root_payload else {}
        if "profiles" not in payload or not self._local_root_payload:
            print("ERROR: No profiles loaded. Merge a bringup_system.json before saving unified config.")
            return None
        if KEY_TOPOLOGY not in payload:
            payload[KEY_TOPOLOGY] = {
                KEY_TOPOLOGY_VERSION: COUNT_ONE,
                KEY_TOPOLOGY_SOURCE: TOPOLOGY_SOURCE_LOCAL,
                KEY_TOPOLOGY_PROFILES: {},
            }
        payload.setdefault("default_profile", "robot")
        payload["schema_version"] = PROFILE_SCHEMA_VERSION
        payload["bridgeConfig"] = self._ordered_bridge_config(self._local_config)
        if self._profiles_dirty or "data_version" not in payload:
            payload["data_version"] = timestamp_version()
        payload["data_hash"] = compute_profiles_hash(payload)
        return payload

    def _save_unified_config(
        self,
        path: str,
        *,
        skip_validation: bool = False,
        force: bool = False,
        validation_ok: Optional[bool] = None,
    ) -> StatusResult:
        """
        NAME
            _save_unified_config - Save a unified bringup_system.json payload.
        """
        if not skip_validation:
            allowed, validation_ok = self._guard_save(force)
            if not allowed:
                return StatusResult(code=SS__CONFIG__INVALID)
        if validation_ok is None:
            validation_ok = True
        payload = self._build_unified_payload()
        if payload is None:
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        target_path = Path(path)
        try:
            target = target_path.resolve()
            canonical = self._config_repository.canonical_path().resolve()
            deploy = self._config_repository.deploy_path().resolve()
            session = self._config_repository.session_for_payload(target_path, payload)
            if target == canonical or target == deploy:
                self._config_repository.sync(session, stamp=False)
            else:
                self._config_repository.save(session, path=target_path, stamp=False)
        except Exception as exc:
            print(MESSAGE_ERR_SAVE_WRITE.format(path=path, error=exc))
            return StatusResult(code=SS__CONFIG__INVALID)
        self._profiles_dirty = False
        self._groups_dirty = False
        self._tests_dirty = False
        self._post_save(
            AUDIT_ACTION_SAVE,
            [SOURCE_NAME_REGISTRY, SOURCE_NAME_CONFIG],
            Path(path),
            payload,
            validation_ok,
            JSON_PRETTY_INDENT,
            True,
        )
        self._record_last_save(Path(path))
        print(f"Wrote unified config to {path}.")
        return StatusResult(code=SS__CONFIG__SAVED)

    def _save_local_config(
        self,
        path: str,
        *,
        skip_validation: bool = False,
        force: bool = False,
        validation_ok: Optional[bool] = None,
    ) -> StatusResult:
        if not skip_validation:
            allowed, validation_ok = self._guard_save(force)
            if not allowed:
                return StatusResult(code=SS__CONFIG__INVALID)
        if validation_ok is None:
            validation_ok = True
        if not self._local_config:
            print("ERROR: Local config not loaded. Use merge/import config <bringup_system.json>.")
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        self._sync_store_tests()
        try:
            config_out = self._ordered_bridge_config(self._local_config)
        except Exception as exc:
            print(MESSAGE_ERR_SAVE_WRITE.format(path=path, error=exc))
            return StatusResult(code=SS__CONFIG__INVALID)
        ok, error = self._atomic_write_json(
            Path(path),
            config_out,
            JSON_PRETTY_INDENT,
            True,
        )
        if not ok:
            print(MESSAGE_ERR_SAVE_WRITE.format(path=path, error=error))
            return StatusResult(code=SS__CONFIG__INVALID)
        self._groups_dirty = False
        self._post_save(
            AUDIT_ACTION_SAVE,
            [SOURCE_NAME_CONFIG],
            Path(path),
            config_out,
            validation_ok,
            JSON_PRETTY_INDENT,
            True,
        )
        self._record_last_save(Path(path))
        if self._local_devices_locked:
            print(f"Wrote groups config to {path}.")
        else:
            print(f"Wrote bridgeConfig to {path}.")
        return StatusResult(code=SS__CONFIG__SAVED)

    def _save_runtime_config(self, path: str, *, force: bool = False) -> StatusResult:
        """
        NAME
            _save_runtime_config - Save runtime bridgeConfig with atomic swap.
        """
        allowed, validation_ok = self._guard_save(force)
        if not allowed:
            return StatusResult(code=SS__CONFIG__INVALID)
        target_path = Path(path)
        temp_path = target_path.with_name(target_path.name + BACKUP_SUFFIX_TMP)
        result = save_config(self._session, str(temp_path), self._active_profile_name())
        if not result.ok():
            message = format_status_message(result.code, **result.message_args) or result.message
            if message:
                print(message)
            return StatusResult(code=SS__CONFIG__INVALID)
        try:
            payload = self._config_repository.load_path(temp_path).to_payload()
        except Exception as exc:
            print(MESSAGE_ERR_SAVE_WRITE.format(path=path, error=exc))
            return StatusResult(code=SS__CONFIG__INVALID)
        try:
            if temp_path.exists():
                temp_path.unlink()
        except Exception:
            pass
        try:
            session = self._config_repository.session_for_payload(target_path, payload)
            self._config_repository.save(session, path=target_path)
            payload = session.to_payload()
        except Exception as exc:
            print(MESSAGE_ERR_SAVE_WRITE.format(path=path, error=exc))
            return StatusResult(code=SS__CONFIG__INVALID)
        self._post_save(
            AUDIT_ACTION_SAVE,
            [SOURCE_NAME_CONFIG],
            target_path,
            payload,
            validation_ok,
            JSON_PRETTY_INDENT,
            True,
        )
        self._record_last_save(target_path)
        print(MESSAGE_SAVE_CONFIG_SAVED.format(path=path))
        return StatusResult(code=SS__CONFIG__SAVED)

    def _load_sources(self) -> StatusResult:
        """
        NAME
            _load_sources - Reload all known local sources from disk.
        """

        print(MESSAGE_SOURCES_LOAD_HEADER)
        entries = self._collect_sources()
        ok = True
        for entry in entries:
            name = str(entry.get(KEY_SOURCE_NAME, EMPTY_STRING))
            status = str(entry.get(KEY_SOURCE_STATUS, EMPTY_STRING))
            path = str(entry.get(KEY_SOURCE_PATH, EMPTY_STRING))
            if status == SOURCE_STATUS_UNKNOWN or not path:
                print(MESSAGE_SOURCES_SKIP_UNKNOWN.format(name=name))
                ok = False
                continue
            if status == SOURCE_STATUS_NOT_LOADED and not path:
                print(MESSAGE_SOURCES_SKIP_NOT_LOADED.format(name=name))
                ok = False
                continue
            result = self._reload_source(name, path)
            if not result.ok():
                ok = False
                continue
            print(MESSAGE_SOURCES_LOAD_OK.format(name=name, path=path))
        if ok:
            print(MESSAGE_SOURCES_DONE)
            return StatusResult(code=SS__NORMAL)
        return StatusResult(code=SS__EXECUTOR__FAILED)

    def _revert_all(self) -> StatusResult:
        """
        NAME
            _revert_all - Discard unsaved local state by reloading known disk sources.
        """
        if not self._has_dirty_state():
            print(MESSAGE_REVERT_NOTHING)
            return StatusResult(code=SS__NORMAL)
        print(MESSAGE_REVERT_START)
        result = self._load_sources()
        if result.ok():
            self._last_modified_at = None
            print(MESSAGE_REVERT_DONE)
        return result

    def _handle_tiu_command(self, tokens: List[str]) -> StatusResult:
        """
        NAME
            _handle_tiu_command - Toggle TIU presentation mode on or off.
        """
        if len(tokens) != COUNT_TWO:
            print(MESSAGE_TIU_USAGE)
            return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)
        value = tokens[COUNT_ONE].strip().lower()
        if value == TEXT_STATUS_ON:
            self._tiu_enabled = True
            self._tiu_add_event(MESSAGE_TIU_EVENT_ENABLED)
            print(MESSAGE_TIU_ON)
            return StatusResult(code=SS__NORMAL)
        if value == TEXT_STATUS_OFF:
            self._tiu_enabled = False
            self._tiu_add_event(MESSAGE_TIU_EVENT_DISABLED)
            print(MESSAGE_TIU_OFF)
            return StatusResult(code=SS__NORMAL)
        print(MESSAGE_TIU_USAGE)
        return StatusResult(code=SS__CLI_VALIDATOR__INVALID_VALUE)

    def _reload_source(self, name: str, path: str) -> StatusResult:
        """
        NAME
            _reload_source - Reload a single source entry from disk.
        """

        if name == SOURCE_NAME_REGISTRY:
            plan = import_config(path, self._conflict_policy, self._active_profile_name())
            return self._apply_config_plan_local(plan)
        if name == SOURCE_NAME_CONFIG:
            ok, message, config = validate_config_file(path)
            if not ok or config is None:
                print(MESSAGE_ERR_CONFIG_VALIDATE.format(message=message))
                return StatusResult(code=SS__CONFIG__INVALID)
            self._local_config = config
            self._local_config_path = path
            self._local_loaded_at = time.time()
            self._groups_dirty = False
            self._sync_store_from_local()
            return StatusResult(code=SS__NORMAL)
        if name == SOURCE_NAME_BINDINGS:
            return self._load_bindings_from_path(Path(path))
        if name == SOURCE_NAME_CAN_MAPPINGS:
            return self._load_can_mappings_from_path(Path(path))
        if name == SOURCE_NAME_TESTS:
            self._tests_model = None
            self._tests_profile = None
            self._ensure_tests_loaded()
            self._tests_dirty = False
            return StatusResult(code=SS__NORMAL)
        return StatusResult(code=SS__EXECUTOR__FAILED)

    def _save_sources(self, force: bool = False) -> StatusResult:
        """
        NAME
            _save_sources - Save all known local sources back to disk.
        """

        allowed, validation_ok = self._guard_save(force)
        if not allowed:
            return StatusResult(code=SS__CONFIG__INVALID)
        print(MESSAGE_SOURCES_SAVE_HEADER)
        entries = self._collect_sources()
        registry_path = EMPTY_STRING
        config_path = EMPTY_STRING
        registry_loaded = False
        config_loaded = False
        for entry in entries:
            name = str(entry.get(KEY_SOURCE_NAME, EMPTY_STRING))
            status = str(entry.get(KEY_SOURCE_STATUS, EMPTY_STRING))
            path = str(entry.get(KEY_SOURCE_PATH, EMPTY_STRING))
            if name == SOURCE_NAME_REGISTRY:
                registry_path = path
                registry_loaded = status != SOURCE_STATUS_NOT_LOADED and bool(path)
            if name == SOURCE_NAME_CONFIG:
                config_path = path
                config_loaded = status != SOURCE_STATUS_NOT_LOADED and bool(path)
        skip_names: set[str] = set()
        ok = True
        if (
            registry_loaded
            and config_loaded
            and registry_path
            and registry_path == config_path
        ):
            result = self._save_unified_config(
                registry_path,
                skip_validation=True,
                validation_ok=validation_ok,
            )
            if not result.ok():
                ok = False
            else:
                skip_names.update({SOURCE_NAME_REGISTRY, SOURCE_NAME_CONFIG, SOURCE_NAME_TESTS})
                for name in (SOURCE_NAME_REGISTRY, SOURCE_NAME_CONFIG):
                    print(MESSAGE_SOURCES_SAVE_OK.format(name=name, path=registry_path))
        for entry in entries:
            name = str(entry.get(KEY_SOURCE_NAME, EMPTY_STRING))
            status = str(entry.get(KEY_SOURCE_STATUS, EMPTY_STRING))
            path = str(entry.get(KEY_SOURCE_PATH, EMPTY_STRING))
            if name in skip_names:
                continue
            if status == SOURCE_STATUS_UNKNOWN or not path:
                print(MESSAGE_SOURCES_SKIP_UNKNOWN.format(name=name))
                ok = False
                continue
            if status == SOURCE_STATUS_NOT_LOADED:
                print(MESSAGE_SOURCES_SKIP_NOT_LOADED.format(name=name))
                ok = False
                continue
            result = self._save_source(name, path, validation_ok=validation_ok)
            if not result.ok():
                ok = False
                continue
            print(MESSAGE_SOURCES_SAVE_OK.format(name=name, path=path))
        if ok:
            print(MESSAGE_SOURCES_DONE)
            return StatusResult(code=SS__NORMAL)
        return StatusResult(code=SS__EXECUTOR__FAILED)

    def _save_source(self, name: str, path: str, *, validation_ok: bool = True) -> StatusResult:
        """
        NAME
            _save_source - Save a single source entry to disk.
        """

        if name == SOURCE_NAME_REGISTRY:
            return self._save_profiles(path, skip_validation=True, validation_ok=validation_ok)
        if name == SOURCE_NAME_CONFIG:
            return self._save_local_config(path, skip_validation=True, validation_ok=validation_ok)
        if name == SOURCE_NAME_BINDINGS:
            return self._save_bindings_to_path(Path(path), validation_ok=validation_ok)
        if name == SOURCE_NAME_CAN_MAPPINGS:
            return self._save_can_mappings_to_path(Path(path), validation_ok=validation_ok)
        return StatusResult(code=SS__EXECUTOR__FAILED)

    def _handle_recover_command(self, tokens: List[str]) -> StatusResult:
        """
        NAME
            _handle_recover_command - Dispatch recovery commands.
        """
        if len(tokens) < COUNT_TWO:
            print(MESSAGE_HINT_RECOVER)
            return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
        action = tokens[COUNT_ONE].lower()
        if action == CMD_LIST:
            return self._recover_list()
        if action == CMD_LAST_GOOD:
            return self._recover_apply(SNAPSHOT_LAST_GOOD)
        if action == CMD_FROM:
            if len(tokens) < COUNT_THREE:
                print(MESSAGE_HINT_RECOVER)
                return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
            return self._recover_apply(tokens[COUNT_TWO])
        print(MESSAGE_HINT_RECOVER)
        return StatusResult(code=SS__CLI_PARSER__INVALID_SYNTAX)

    def _recover_list(self) -> StatusResult:
        """
        NAME
            _recover_list - List available recovery snapshots.
        """
        entries = self._collect_sources()
        grouped: Dict[str, List[str]] = {}
        for entry in entries:
            name = str(entry.get(KEY_SOURCE_NAME, EMPTY_STRING))
            status = str(entry.get(KEY_SOURCE_STATUS, EMPTY_STRING))
            path = str(entry.get(KEY_SOURCE_PATH, EMPTY_STRING))
            if not path or status == SOURCE_STATUS_NOT_LOADED:
                continue
            grouped.setdefault(path, []).append(name)
        print(MESSAGE_RECOVER_LIST_HEADER)
        if not grouped:
            print(MESSAGE_RECOVER_LIST_EMPTY)
            return StatusResult(code=SS__NORMAL)
        for path_text, names in grouped.items():
            source_label = SEP_COMMA_SPACE.join(sorted(names))
            print(MESSAGE_RECOVER_LIST_SOURCE.format(source=source_label, path=path_text))
            last_good, tags = self._list_snapshots_for_path(Path(path_text))
            if last_good is not None:
                print(MESSAGE_RECOVER_LIST_LAST_GOOD.format(name=last_good.name))
            if tags:
                for tag in tags:
                    print(MESSAGE_RECOVER_LIST_ENTRY.format(name=tag))
            if last_good is None and not tags:
                print(MESSAGE_RECOVER_LIST_SOURCE_EMPTY)
        return StatusResult(code=SS__NORMAL)

    def _recover_apply(self, tag: str) -> StatusResult:
        """
        NAME
            _recover_apply - Apply a snapshot to local state.
        """
        entries = self._collect_sources()
        grouped: Dict[str, List[str]] = {}
        for entry in entries:
            name = str(entry.get(KEY_SOURCE_NAME, EMPTY_STRING))
            status = str(entry.get(KEY_SOURCE_STATUS, EMPTY_STRING))
            path = str(entry.get(KEY_SOURCE_PATH, EMPTY_STRING))
            if not path:
                continue
            if status == SOURCE_STATUS_NOT_LOADED:
                self._warn(MESSAGE_RECOVER_SOURCE_SKIP.format(source=name))
                continue
            grouped.setdefault(path, []).append(name)
        if not grouped:
            print(MESSAGE_RECOVER_LIST_EMPTY)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        ok = True
        for path_text, names in grouped.items():
            source_path = Path(path_text)
            stamp = tag
            snapshot_path, last_good_path = self._snapshot_paths(source_path, stamp)
            selected_path = last_good_path if tag == SNAPSHOT_LAST_GOOD else snapshot_path
            if not selected_path.exists():
                for name in names:
                    self._warn(MESSAGE_RECOVER_MISSING.format(source=name, path=selected_path))
                ok = False
                continue
            if SOURCE_NAME_REGISTRY in names or SOURCE_NAME_CONFIG in names:
                if not self._recover_profiles_snapshot(selected_path, source_path):
                    ok = False
                    continue
            if SOURCE_NAME_BINDINGS in names:
                if not self._recover_bindings_snapshot(selected_path, source_path):
                    ok = False
                    continue
            if SOURCE_NAME_CAN_MAPPINGS in names:
                if not self._recover_mappings_snapshot(selected_path, source_path):
                    ok = False
                    continue
        if ok:
            print(MESSAGE_RECOVER_APPLIED)
            return StatusResult(code=SS__NORMAL)
        return StatusResult(code=SS__CONFIG__INVALID)

    def _recover_profiles_snapshot(self, snapshot_path: Path, source_path: Path) -> bool:
        """
        NAME
            _recover_profiles_snapshot - Load a profiles snapshot into memory.
        """
        plan = import_config(str(snapshot_path), self._conflict_policy, self._active_profile_name())
        result = self._apply_config_plan_local(plan)
        if not result.ok():
            self._warn(MESSAGE_RECOVER_FAILED.format(source=SOURCE_NAME_REGISTRY, path=snapshot_path))
            return False
        self._local_root_path = source_path
        self._local_config_path = source_path
        self._mark_profiles_dirty()
        self._groups_dirty = True
        self._tests_dirty = True
        self._record_last_modified()
        self._sync_store_from_local()
        valid, _message = self._validate_registry_payload(
            self._local_root_payload or {},
            EMPTY_STRING,
        )
        for name in (SOURCE_NAME_REGISTRY, SOURCE_NAME_CONFIG):
            self._append_audit_log(AUDIT_ACTION_RECOVER, name, snapshot_path, valid)
        return True

    def _recover_bindings_snapshot(self, snapshot_path: Path, source_path: Path) -> bool:
        """
        NAME
            _recover_bindings_snapshot - Load a bindings snapshot into memory.
        """
        result = self._load_bindings_from_path(snapshot_path, announce=False)
        if not result.ok():
            self._warn(MESSAGE_RECOVER_FAILED.format(source=SOURCE_NAME_BINDINGS, path=snapshot_path))
            return False
        self._bindings_path = source_path
        self._mark_bindings_dirty()
        self._sync_store_bindings()
        valid, _message = self.validate_bindings_only(None)
        self._append_audit_log(AUDIT_ACTION_RECOVER, SOURCE_NAME_BINDINGS, snapshot_path, valid)
        return True

    def _recover_mappings_snapshot(self, snapshot_path: Path, source_path: Path) -> bool:
        """
        NAME
            _recover_mappings_snapshot - Load a mappings snapshot into memory.
        """
        result = self._load_can_mappings_from_path(snapshot_path)
        if not result.ok():
            self._warn(MESSAGE_RECOVER_FAILED.format(source=SOURCE_NAME_CAN_MAPPINGS, path=snapshot_path))
            return False
        self._can_mappings_path = source_path
        self._mark_mappings_dirty()
        self._sync_store_mappings()
        valid, _message = self.validate_mappings_only(None)
        self._append_audit_log(AUDIT_ACTION_RECOVER, SOURCE_NAME_CAN_MAPPINGS, snapshot_path, valid)
        return True

    def _validate_file(self, path: str, repair: bool, verbose: bool = False) -> StatusResult:
        """
        NAME
            _validate_file - Validate or repair a profiles file on disk.
        """
        if not path:
            print(MESSAGE_VALIDATE_FILE_PATH_REQUIRED)
            return StatusResult(code=SS__CLI_PARSER__MISSING_ARGUMENT)
        if verbose:
            print(f"INFO: validating file {path}")
            if repair:
                print("INFO: repair mode enabled")
        source_path = Path(path)
        config_repository = getattr(self, "_config_repository", None)
        if config_repository is None:
            config_lifecycle = getattr(self, "_config_lifecycle", None)
            config_repository = ConfigRepository(config_lifecycle)
            self._config_repository = config_repository
        try:
            payload = config_repository.load_path(source_path).to_payload()
        except Exception:
            print(MESSAGE_VALIDATE_FILE_LOAD.format(path=path))
            return StatusResult(code=SS__CONFIG__INVALID)
        if not isinstance(payload, dict):
                print(MESSAGE_VALIDATE_FILE_UNSUPPORTED.format(path=path))
                return StatusResult(code=SS__CONFIG__INVALID)
        if repair:
            repaired, changed = self._repair_profiles_payload(payload)
            if changed:
                try:
                    session = config_repository.session_for_payload(source_path, repaired)
                    config_repository.save(session, path=source_path)
                except Exception as exc:
                    print(MESSAGE_ERR_SAVE_WRITE.format(path=path, error=exc))
                    return StatusResult(code=SS__CONFIG__INVALID)
                self._post_save(
                    AUDIT_ACTION_REPAIR,
                    [SOURCE_NAME_REGISTRY],
                    source_path,
                    repaired,
                    True,
                    JSON_PRETTY_INDENT,
                    True,
                )
                print(MESSAGE_REPAIR_APPLIED.format(path=path))
            else:
                print(MESSAGE_REPAIR_NO_CHANGES.format(path=path))
            valid, message = self._validate_registry_payload(repaired, EMPTY_STRING)
            if valid:
                print(MESSAGE_VALIDATE_FILE_OK)
                return StatusResult(code=SS__CONFIG__VALID)
            print(MESSAGE_VALIDATE_FILE_ERR.format(message=message))
            return StatusResult(code=SS__CONFIG__INVALID)
        valid, message = self._validate_registry_payload(payload, EMPTY_STRING)
        if valid:
            print(MESSAGE_VALIDATE_FILE_OK)
            return StatusResult(code=SS__CONFIG__VALID)
        print(MESSAGE_VALIDATE_FILE_ERR.format(message=message))
        return StatusResult(code=SS__CONFIG__INVALID)

    def _repair_profiles_payload(
        self, payload: Dict[str, object]
    ) -> tuple[Dict[str, object], bool]:
        """
        NAME
            _repair_profiles_payload - Repair missing required profile fields.
        """
        repaired = deepcopy(payload)
        changed = BOOL_FALSE
        if KEY_DATA_VERSION_CAMEL in repaired and KEY_DATA_VERSION not in repaired:
            repaired[KEY_DATA_VERSION] = repaired.get(KEY_DATA_VERSION_CAMEL)
            changed = BOOL_TRUE
        if KEY_DATA_HASH_CAMEL in repaired and KEY_DATA_HASH not in repaired:
            repaired[KEY_DATA_HASH] = repaired.get(KEY_DATA_HASH_CAMEL)
            changed = BOOL_TRUE
        repaired, salvage_warnings, salvage_changed = self._store.sanitize_profiles_payload(repaired)
        for warning in salvage_warnings:
            self._warnings.append(warning)
        return repaired, bool(changed or salvage_changed)

    def _apply_config_plan_local(self, plan: ConfigPlan) -> StatusResult:
        """
        NAME
            _apply_config_plan_local - Apply a config plan without robot IO.
        """

        if not plan.ok:
            print(MESSAGE_ERR_PLAN.format(message=plan.message))
            return StatusResult(code=SS__CONFIG__INVALID)
        if plan.root_payload is None and self._local_root_payload is None:
            print(MESSAGE_ERR_REGISTRY_NOT_LOADED)
            return StatusResult(code=SS__CONFIG__NOT_LOADED)
        incoming_hash = self._profiles_hash(plan.root_payload)
        if not plan.replace and incoming_hash:
            if self._local_root_hash is None and self._local_group_count() > COUNT_ZERO:
                print(MESSAGE_ERR_PROFILE_MISSING_HASH)
                return StatusResult(code=SS__CONFIG__INVALID)
            if self._local_root_hash and incoming_hash != self._local_root_hash:
                print(
                    MESSAGE_ERR_PROFILE_HASH.format(
                        local=self._local_root_hash,
                        incoming=incoming_hash,
                    )
                )
                return StatusResult(code=SS__CONFIG__INVALID)
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
        return StatusResult(code=SS__NORMAL)


if Completer is None:
    class BridgeCliCompleter:
        """
        NAME
            BridgeCliCompleter - Placeholder when prompt_toolkit is unavailable.
        """

        def __init__(self, cli: "BridgeCli") -> None:
            self._cli = cli
else:
    class BridgeCliCompleter(Completer):
        """
        NAME
            BridgeCliCompleter - Keyword completer for the Bridge CLI.
        """

        def __init__(self, cli: "BridgeCli") -> None:
            self._cli = cli

        def get_completions(self, document, complete_event):
            text = document.text_before_cursor
            try:
                tokens = self._cli._parser.tokenize(text) if text else []
            except Exception:
                return
            if tokens and text.endswith(COMPLETION_SPACE):
                base_tokens = tokens
                prefix = COMPLETION_PREFIX_EMPTY
            elif tokens:
                base_tokens = tokens[:-1]
                prefix = tokens[-1]
            else:
                base_tokens = []
                prefix = COMPLETION_PREFIX_EMPTY
            suggestions = self._cli._suggest_next_args(base_tokens)
            if prefix:
                pref = prefix.lower()
                suggestions = [
                    item for item in suggestions if item and item.lower().startswith(pref)
                ]
            for item in suggestions:
                if not item:
                    continue
                start_pos = -len(prefix) if prefix else COMPLETION_START_POS_ZERO
                yield Completion(item, start_position=start_pos, display_meta=COMPLETION_META_TEXT)


DEFAULT_DIRECT_RIO_HOST = "172.22.11.2"
DEFAULT_DIRECT_UI_REST_PORT = 5805


def _build_direct_parser() -> argparse.ArgumentParser:
    """
    NAME
        _build_direct_parser - Build argparse parser for direct bridge_cli.py execution.
    """
    parser = argparse.ArgumentParser(description="Bridge CLI (direct mode).")
    parser.add_argument("--rio", default=DEFAULT_DIRECT_RIO_HOST, help="Robot host/IP for REST command session.")
    parser.add_argument(
        "--ui-rest-port",
        type=int,
        default=DEFAULT_DIRECT_UI_REST_PORT,
        help="REST port for robot command server.",
    )
    parser.add_argument("--batch", action="store_true", help="Run non-interactive batch script mode.")
    parser.add_argument("--script", default="", help="Path to batch script when --batch is set.")
    parser.add_argument("--conflict-policy", default="error", help="Conflict policy for config merges.")
    parser.add_argument("--cli-echo", action="store_true", help="Enable CLI echo mode.")
    parser.add_argument("--cli-messages", default="", help="CLI message level override.")
    parser.add_argument("--no-can", action="store_true", help="Accepted for compatibility; ignored here.")
    parser.add_argument("--no-nt", action="store_true", help="Accepted for compatibility; ignored here.")
    parser.add_argument("--cli", action="store_true", help="Accepted for compatibility; ignored here.")
    return parser


def _run_direct_cli(argv: List[str]) -> int:
    """
    NAME
        _run_direct_cli - Entrypoint for direct execution of bridge_cli.py.
    """
    parser = _build_direct_parser()
    args = parser.parse_args(argv)
    if args.batch and not args.script:
        print("ERROR: --batch requires --script <file>.")
        return EXIT_CODE_ERROR
    session = BridgeSession(args.rio, int(args.ui_rest_port))
    cli = BridgeCli(
        session,
        batch=bool(args.batch),
        conflict_policy=str(args.conflict_policy),
        echo_enabled=bool(args.cli_echo),
        message_level=(args.cli_messages or None),
    )
    if args.batch:
        try:
            with open(args.script, "r", encoding="utf-8") as handle:
                lines = handle.readlines()
        except Exception as exc:
            print(f"ERROR: Failed to read script: {exc}")
            return EXIT_CODE_ERROR
        return int(cli.run_batch(lines))
    return int(cli.run_interactive())


if __name__ == "__main__":
    raise SystemExit(_run_direct_cli(sys.argv[1:]))
