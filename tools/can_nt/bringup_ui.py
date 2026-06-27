from __future__ import annotations

"""
NAME
    bringup_ui.py - Bringup control UI for PC-side command dispatch.

SYNOPSIS
    from tools.can_nt.bringup_ui import BringupControlUI

DESCRIPTION
    Provides a Windows-friendly Tk UI that mirrors bringup commands with
    labeled on-screen buttons. Commands are sent through the shared REST-backed
    BridgeSession layer, and output is displayed in a single scrolling panel.

NOTES
    All UI command sends must go through tools.can_nt.bridge_ops wrappers.
"""

import json
import time
import tkinter as tk
import uuid
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Callable, Dict, List, Optional, Tuple, Any

from .bridge_cmd_tracker import CommandTracker
from .command_catalog_service import (
    load_host_ui_command_metadata,
    merge_host_ui_actions as merge_host_ui_actions_shared,
)
from .command_workflow_service import send_tracked_command
from .bridge_ops import (
    _resolve_device_type_label,
    connect,
    download_current_config,
    disconnect,
    lifecycle_activate,
    lifecycle_deactivate_active,
    push_config,
    send_command,
    show_lifecycle_state,
    show_runtime_state,
    select_test_by_name,
    ui_disconnect,
    ui_handshake,
    ui_monitor,
    ui_poll_log,
    ui_ping,
)
from .bridge_session import BridgeEvent, BridgeSession
from .host_ui_actions import (
    ACTION_KIND_HOST_LOCAL,
    ACTION_SOURCE_HOST,
    HOST_ACTION_DSL_TEST_IMPORT,
    HOST_ACTION_DSL_TEST_VALIDATE,
    HOST_ACTION_RECONNECT_UI_SESSION,
    HOST_UI_ACTIONS,
)
from .status import SS__NORMAL
from tools.common.json_io import read_json, write_json
from tools.common.config_api import ConfigEditSession, ConfigRepository
from tools.common.nt_labels import decode_label_from_nt, encode_label_for_nt
from tools.common.paths import repo_root, tests_deploy_path
from tools.common.profile_constants import KEY_DEFAULT_PROFILE, KEY_DSL_TESTS
from tools.common.tests_domain import collect_available_tests
from tools.common.config_lifecycle import LocalConfigQueryService
from tools.common.profiles import list_profile_names
from tools.common.profile_constants import (
    KEY_DEVICE_TYPE,
    KEY_ID,
    KEY_LABEL as PROFILE_KEY_LABEL,
    KEY_MANUFACTURER,
)
from tools.common.profile_constants import KEY_ENABLED
from tools.common.profile_constants import KEY_TYPE
from tools.common.group_contract import (
    group_member_map,
    resolve_group_motor_targets,
)
from tools.common.robot_test_dsl import (
    compile_source,
    copy_external_library_test_into_root_payload,
    create_blank_test_in_root_payload,
    copy_test_into_root_payload,
    delete_external_library_test,
    delete_test_from_root_payload,
    DslServiceError,
    import_test_into_config_library,
    import_test_into_external_library,
    import_test_into_root_payload,
    list_external_library_test_names,
    read_external_library_test_source,
    rename_external_library_test,
    rename_test_in_root_payload,
    render_validation_text,
    resolve_profile_test_names,
    resolve_profile_device_dsl_type,
    resolve_runnable_profile_test_names,
    signal_catalog as robot_test_dsl_signal_catalog,
    store_from_root_payload as robot_test_dsl_store_from_root_payload,
    update_test_source_in_root_payload,
    validate_store_for_profile,
    write_test_source_into_config_library,
)
from tools.common.time_utils import timestamp_hms
from tools.common.motor_runtime_verdict import (
    infer_motor_runtime_verdict,
    runtime_motor_attachment,
    RESULT_ELECTRICAL,
    RESULT_STALLED,
)
from tools.common.app_versions import (
    APP_BRINGUP_UI_NAME,
    VERSIONS,
    VERSION_HEADER,
    format_version_line,
)
from tools.common.build_info import build_lines
from tools.common.profile_session import (
    SYNC_ACTION_ADOPT,
    SYNC_ACTION_MISSING_LOCAL,
    SYNC_ACTION_PROMPT,
    decide_host_profile_sync,
    normalize_profile_name as normalize_profile_name_shared,
)
from .can_profiles import get_profile, get_profiles_load_error, list_profiles, reload_profiles
from .can_profiles import get_default_profile
from tools.config.schema_store import ConfigSchemaStore
from tools.can_topology.live_topology_view import LiveTopologyView
from tools.can_nt.visibility_constants import (
    VIS_KEY_DEVICES,
    VIS_KEY_DEVICES_SHOWN,
    VIS_KEY_API_CLASS,
    VIS_KEY_API_INDEX,
    VIS_KEY_ARB_HEX,
    VIS_KEY_DATA_PAGE,
    VIS_KEY_FRAMES_PER_SEC,
    VIS_KEY_ID,
    VIS_KEY_IDENTITY,
    VIS_KEY_LABEL,
    VIS_KEY_LAST_SEEN_MS,
    VIS_KEY_METRICS,
    VIS_KEY_MSG_COUNT,
    VIS_KEY_PF,
    VIS_KEY_PGN,
    VIS_KEY_PRIORITY,
    VIS_KEY_PS,
    VIS_KEY_RAW_IDS,
    VIS_KEY_RESERVED,
    VIS_KEY_SA,
    VIS_KEY_SEPARATOR,
    VIS_KEY_SOURCES,
    VIS_KEY_SOURCES_COUNT,
    VIS_KEY_VISIBLE_ALL,
    VIS_KEY_VISIBLE_NONE,
    VIS_KEY_VISIBLE_SOME,
    VIS_KEY_VISIBILITY,
    VIS_MS_PER_SEC,
    VIS_SCOPE_BOTH,
    VIS_SCOPE_EXPECTED,
)

# Constants (NetworkTables paths and presence values).
NT_PATH_PRESENCE_FMT = "dev/{}/presenceConfidence"
NT_VALUE_EMPTY = ""
PRESENCE_VALUE_HIGH = "HIGH"
PRESENCE_VALUE_LOW = "LOW"
PRESENCE_VALUE_NONE = "NONE"
PRESENCE_VALUES = {
    PRESENCE_VALUE_HIGH,
    PRESENCE_VALUE_LOW,
    PRESENCE_VALUE_NONE,
}

# Constants (device dict keys).
DEVICE_KEY_LABEL = "label"
DEVICE_KEY_MFG = KEY_MANUFACTURER
DEVICE_KEY_TYPE = KEY_DEVICE_TYPE
DEVICE_KEY_ID = KEY_ID

# Constants (file-based presence overrides).
PRESENCE_FILE_KEY_OVERRIDES = "presenceOverrides"
PRESENCE_FILE_KEY_TIMELINE = "presenceTimeline"
PRESENCE_FILE_KEY_AT_SEC = "atSec"
PRESENCE_FILE_KEY_OVERRIDES_BLOCK = "overrides"
PRESENCE_TIME_NONE = 0.0
PRESENCE_TIMELINE_MIN_STEP = 1.0
PRESENCE_TIMELINE_DEFAULT_STEP = 2.0
LIVE_SOURCE_REST = "rest"
LIVE_SOURCE_FILE = "file"
LIVE_CLOCK_FORMAT = "%H:%M:%S"
LIVE_CLOCK_LABEL = "Clock:"
PROFILE_NONE = "(none)"
NT_UI_STATE_SELECTED_PROFILE = "state/selectedProfile"
NT_UI_STATE_ACTIVE_RUNTIME_PROFILE = "state/activeRuntimeProfile"
DEFAULT_RUNTIME_STATE_RATE_HZ = 2.0
ACTIVE_MANUAL_RUNTIME_STATE_RATE_HZ = 10.0
DEFAULT_RUNTIME_STATE_RATE_TEXT = "2"
BUTTON_LIFECYCLE_ACTIVATE = "Lifecycle Activate"
BUTTON_LIFECYCLE_DEACTIVATE = "Lifecycle Deactivate"
BUTTON_ACTIVATE_GROUP = "Activate Group"
BUTTON_DEACTIVATE_GROUP = "Deactivate Group"
BUTTON_PUSH_CONFIG = "Push Config"
BUTTON_DOWNLOAD_CONFIG = "Download Current Config"
BUTTON_SHOW_RUNTIME_STATE = "Show Runtime State"
BUTTON_SHOW_LIFECYCLE_STATE = "Show Lifecycle State"
GROUP_SOURCE_MANUAL = "manual"
GROUP_SOURCE_SELECTED_TEST = "selected test"
GROUP_SOURCE_LABEL_PREFIX = "Active Group Source: "
GROUP_SOURCE_LABEL_MANUAL = GROUP_SOURCE_LABEL_PREFIX + GROUP_SOURCE_MANUAL
GROUP_SOURCE_LABEL_SELECTED_TEST = GROUP_SOURCE_LABEL_PREFIX + GROUP_SOURCE_SELECTED_TEST
OUTPUT_NOT_CONNECTED = "Not connected: command blocked."
OUTPUT_BUSY = "Busy: wait for current command to finish."
OUTPUT_NO_PROFILE = "No profile selected."
OUTPUT_NO_SELECTED_TEST = "no selected test"
OUTPUT_PUSH_CANCELLED = "Config push cancelled."
OUTPUT_DOWNLOAD_CANCELLED = "Config download cancelled."
OUTPUT_PUSH_START_FMT = "PUSH {path} profile={profile}"
OUTPUT_DOWNLOAD_START_FMT = "DOWNLOAD {path}"
OUTPUT_RUNTIME_ACTIVATE_FMT = "CMD runtimeActivate \"{profile}\""
OUTPUT_RUNTIME_DEACTIVATE = "CMD runtimeDeactivate"
OUTPUT_LIFECYCLE_ACTIVATE_FMT = "CMD lifecycleActivate \"{label}\" mode={mode}"
OUTPUT_LIFECYCLE_DEACTIVATE_FMT = "CMD lifecycleDeactivate \"{label}\""
OUTPUT_LIFECYCLE_DEACTIVATE_ACTIVE = "CMD lifecycleDeactivateActive"
OUTPUT_NO_ACTIVE_CONTROLLED_SESSION = "No active controlled session to deactivate."
OUTPUT_GROUP_REPLACE_FMT = "CMD groupReplaceMembers \"{group}\" members={count}"
OUTPUT_SELECTED_PROFILE_PREFIX = "Selected profile: "
OUTPUT_GROUP_RUN_FMT = "CMD groupRunTest \"{group}\""
OUTPUT_OWNER_REQUIRED = "Owning control client required. Use Reconnect UI Session to reclaim control."
DOWNLOAD_FILENAME = "bringup_system.downloaded.json"
CONFIG_FILE_TYPES = (("JSON files", "*.json"), ("All files", "*.*"))
DEVICE_TYPE_MOTOR = "2"
CMD_GROUP_RUN_TEST = "groupRunTest"
CMD_GROUP_ADD_DEVICE = "groupAddDevice"
CMD_GROUP_REMOVE_DEVICE = "groupRemoveDevice"
GROUP_RUN_ARG_GROUP = "group"
GROUP_ACTIVE_NAME = "active-group"
GROUP_RUN_ARG_DEVICE = "device"
GROUP_KEY_GROUP = "group"
GROUP_KEY_MEMBERS = "members"
GROUP_MEMBER_KEY_LABEL = "label"
ACTIVE_GROUP_RESULT_COMMANDS = {"activeadd", "activenext"}
MANUAL_DUTY_CMD_SET = "manualDeviceDutySet"
MANUAL_DUTY_CMD_CLEAR = "manualDeviceDutyClear"
MANUAL_GROUP_DUTY_CMD_SET = "manualGroupDutySet"
MANUAL_GROUP_DUTY_CMD_CLEAR = "manualGroupDutyClear"
DEVICE_OVERRIDE_CMD_INSTANTIATE = "deviceOverrideInstantiate"
DEVICE_OVERRIDE_CMD_CLEAR = "deviceOverrideClear"
MANUAL_DUTY_ARG_NAME = "name"
MANUAL_DUTY_ARG_DUTY = "duty"
MANUAL_DUTY_MIN = -1.0
MANUAL_DUTY_MAX = 1.0
MANUAL_DUTY_DEFAULT = 0.0
MANUAL_DUTY_POPUP_TITLE = "Manual Motor Speed"
MANUAL_DUTY_POPUP_OFFSET_X = 12
MANUAL_DUTY_POPUP_OFFSET_Y = 12
MANUAL_DUTY_POPUP_SIZE = "280x120"
MANUAL_DUTY_SCALE_LENGTH = 220
MANUAL_DUTY_SEND_MIN_INTERVAL_SEC = 0.05
MANUAL_DUTY_SEND_MIN_INTERVAL_LIVE_SEC = 0.20
MANUAL_DUTY_STATUS_FMT = "Manual motor duty active: {label} = {duty:.2f}"
MANUAL_DUTY_STOPPED_FMT = "Manual motor duty cleared: {label}"
MANUAL_DUTY_GROUP_STATUS_FMT = "Manual group duty active: {label} = {duty:.2f}"
MANUAL_DUTY_GROUP_STOPPED_FMT = "Manual group duty cleared: {label}"
MANUAL_DUTY_BLOCKED_TEXT = "Manual motor control blocked: not connected."
MANUAL_DUTY_BLOCKED_STALE_TEXT = "Manual motor control blocked: robot state stale."
MANUAL_DUTY_BLOCKED_ESTOP_TEXT = "Manual motor control blocked: robot estopped."
MANUAL_DUTY_BLOCKED_DISABLED_TEXT = "Manual motor control blocked: robot disabled."
MANUAL_DUTY_BLOCKED_RUNTIME_TEXT = "Manual motor control blocked: runtime inactive."
MANUAL_DUTY_BLOCKED_CONTROLLED_SCOPE_TEXT = (
    "Manual motor control blocked: device is outside the active controlled lifecycle scope."
)
ACTIVE_GROUP_LOCKED_TEXT = (
    "Active group membership is locked while controlled lifecycle session is ACTIVE. Deactivate lifecycle first."
)
MANUAL_DUTY_BUSY_TEXT = "Manual motor control blocked: command in flight."
MANUAL_DUTY_SCALE_ELEMENT_SLIDER = "slider"
MANUAL_DUTY_NO_LABEL = ""
MANUAL_DUTY_NO_TARGETS: List[str] = []
MANUAL_DUTY_VALUE_FMT = "{value:.2f}"
TEST_NAME_EMPTY = ""
VERSION_APP_NAME = APP_BRINGUP_UI_NAME
VERSION_TITLE = VERSION_HEADER
ABOUT_TITLE = "About Bringup Control"
ABOUT_NAME = "Bringup Control UI"
ABOUT_DESCRIPTION = "PC-side NetworkTables command panel for RobotV2 bringup."
ABOUT_LAUNCH = "Launch via tools/can_nt/run_can_nt.cmd --ui"
ABOUT_SEPARATOR = "\n"
BUILD_TITLE = "Build"
UI_PREFS_DIR = "backup_data"
UI_PREFS_SUBDIR = "ui"
UI_PREFS_FILE = "bringup_ui_command_prefs.json"
UI_PREFS_KEY_COMMANDS = "commands"
UI_PREFS_KEY_VISIBLE = "visible"
UI_PREFS_KEY_AUTO_SELECT_DEFAULT_PROFILE = "autoSelectDefaultProfileOnStartup"
UI_PREFS_KEY_SHOW_VISIBILITY_TAB = "showVisibilityTab"
UI_PREFS_KEY_SHOW_WALL_CLOCK = "showWallClock"

# Constants (visibility UI).
VIS_TAB_LABEL = "Visibility"
VIS_COL_DEVICE = "Device"
VIS_COL_IDENTITY = "Identity"
VIS_COL_LAST_SEEN = "Last Seen"
VIS_COL_PACKETS = "Packets"
VIS_COL_RATE = "Rate"
VIS_COL_PROBE_BUCKET = "Full Probe"
VIS_COL_PROBE_SCORE = "Full Probe Score"
VIS_COL_VISIBLE = "Visible"
VIS_VALUE_YES = "Y"
VIS_VALUE_NO = "N"
VIS_VALUE_UNKNOWN = "?"
VIS_MODE_LABEL = "Visibility Mode"
VIS_SUMMARY_FMT = "Sources: {sources} | Devices: {devices} | All: {all} | Some: {some} | None: {none}"
VIS_PANEL_SCOPE = VIS_SCOPE_BOTH
VIS_EMPTY_MESSAGE = "Visibility provider not available."
VIS_LAST_SEEN_UNKNOWN = "--"
VIS_REFRESH_SEC = 0.5
VIS_SOURCE_COUNT_UNKNOWN = "--"
VIS_UNEXPECTED_KEY = "unexpected"
VIS_ROW_META_LABEL = "label"
VIS_ROW_META_UNEXPECTED = "unexpected"
VIS_ROW_META_RAW_IDS = "rawIds"
VIS_RENAME_DIALOG_TITLE = "Rename Discovered Device"
VIS_RENAME_EMPTY_TEXT = "Device label cannot be empty."
VIS_RENAME_DUPLICATE_TEXT = "Device label already exists."
VIS_RENAME_FAILED_TEXT = "Rename failed."
VIS_RENAME_PROMPT_FMT = "Rename discovered device {label}:"
VIS_RENAME_SUCCESS_FMT = "Renamed discovered device: {old_label} -> {new_label}"
VIS_DEFINED_SECTION_LABEL = "Defined Nodes"
VIS_UNRECOGNIZED_SECTION_LABEL = "Unrecognized Nodes"
VIS_CTRE_RAW_SECTION_LABEL = "CTRE Raw Decode"
VIS_CLEAR_PANELS_BUTTON = "Clear Panels"
VIS_PACKETS_UNKNOWN = "--"
VIS_RATE_UNKNOWN = "--"
VIS_RATE_FMT = "{value:.1f}/s"
VIS_TABLE_SPLIT_ORIENT = "vertical"
VIS_RAW_EMPTY_MESSAGE = "Select a CTRE row to inspect contributing raw IDs."
LIVE_TOPOLOGY_TAB_LABEL = "Live Topology"
VIS_RAW_COL_ARB = "Arb ID"
VIS_RAW_COL_PACKETS = "Packets"
VIS_RAW_COL_RATE = "Rate"
VIS_RAW_COL_PRIORITY = "Pri"
VIS_RAW_COL_RESERVED = "R"
VIS_RAW_COL_DATA_PAGE = "DP"
VIS_RAW_COL_API_CLASS = "ApiC"
VIS_RAW_COL_API_INDEX = "ApiI"
VIS_RAW_COL_PF = "PF"
VIS_RAW_COL_PS = "PS"
VIS_RAW_COL_SA = "SA"
VIS_RAW_COL_PGN = "PGN"
NOTICE_COLOR_INFO_BG = "#eff6ff"
NOTICE_COLOR_INFO_FG = "#1d4ed8"
NOTICE_COLOR_WARN_BG = "#fff7ed"
NOTICE_COLOR_WARN_FG = "#c2410c"
NOTICE_COLOR_ERROR_BG = "#fef2f2"
NOTICE_COLOR_ERROR_FG = "#b91c1c"
COLOR_KEY_TITLE = "Live Topology Color Key"
COLOR_KEY_GEOMETRY = "420x360"
COLOR_KEY_MIN_WIDTH = 360
COLOR_KEY_MIN_HEIGHT = 300
COLOR_SWATCH_WIDTH = 3
COLOR_SWATCH_RELIEF = "solid"
COLOR_SWATCH_BORDER = 1
COLOR_KEY_SECTION_PRESENCE = "Presence Mode"
COLOR_KEY_SECTION_VISIBILITY = "Visibility Mode"
COLOR_KEY_SECTION_ANALYZER = "Analyzer Node"
COLOR_KEY_PRESENCE_HIGH = "#2f7a2f"
COLOR_KEY_PRESENCE_LOW = "#f59e0b"
COLOR_KEY_PRESENCE_NONE = "#dc2626"
COLOR_KEY_VIS_ALL = "#16a34a"
COLOR_KEY_VIS_SOME = "#f59e0b"
COLOR_KEY_VIS_NONE = "#dc2626"
COLOR_KEY_VIS_UNKNOWN = "#9ca3af"
COLOR_KEY_ANALYZER_OK = "#16a34a"
COLOR_KEY_ANALYZER_UNKNOWN = "#9ca3af"
COLOR_KEY_TEXT_PRESENCE_HIGH = "Green: high confidence or recently seen."
COLOR_KEY_TEXT_PRESENCE_LOW = "Amber: low confidence or stale (> 2s since last seen / last update)."
COLOR_KEY_TEXT_PRESENCE_NONE = "Red: explicit missing / none."
COLOR_KEY_TEXT_VIS_ALL = "Green: visible on all available sources."
COLOR_KEY_TEXT_VIS_SOME = "Amber: visible on some but not all sources."
COLOR_KEY_TEXT_VIS_NONE = "Red: visible on no available sources."
COLOR_KEY_TEXT_VIS_UNKNOWN = "Gray: unknown or source unavailable."
COLOR_KEY_TEXT_ANALYZER_OK = "Green: analyzer source is available."
COLOR_KEY_TEXT_ANALYZER_UNKNOWN = "Gray: analyzer source unavailable."
COLOR_KEY_TEXT_TIME_NOTE = (
    "Time factor: Presence mode turns stale at about 2.0 s without a fresh last-seen update. "
    "The Visibility table Last Seen column shows the same recency in age form."
)
COLOR_KEY_SECTION_PAD = (10, 8)
COLOR_KEY_ROW_PADY = 2
COLOR_KEY_ROW_PADX = 8
VIS_TREE_SHOW = "headings"
VIS_TREE_END = "end"
VIS_TREE_ROOT = ""
VIS_TREE_COLUMNS = "columns"
VIS_TREE_ANCHOR_W = "w"
VIS_TREE_ANCHOR_CENTER = "center"
VIS_PACK_SIDE_RIGHT = "right"
VIS_PACK_SIDE_LEFT = "left"
VIS_FILL_BOTH = "both"
VIS_FILL_Y = "y"
VIS_FILL_X = "x"
VIS_SCROLLBAR_ORIENT = "vertical"
VIS_PAD_HEADER = (8, 8, 8, 4)
VIS_PAD_TABLE = (8, 0, 8, 8)
VIS_PAD_LEFT = (8, 0)
VIS_COL_DEVICE_WIDTH = 240
VIS_COL_IDENTITY_WIDTH = 110
VIS_COL_LAST_SEEN_WIDTH = 90
VIS_COL_PACKETS_WIDTH = 80
VIS_COL_RATE_WIDTH = 80
VIS_COL_PROBE_BUCKET_WIDTH = 90
VIS_COL_PROBE_SCORE_WIDTH = 92
VIS_COL_SOURCE_WIDTH = 72
EVIDENCE_TAB_LABEL = "Evidence"
EVIDENCE_SUMMARY_DEFAULT = "Select a device to inspect interpreted evidence."
EVIDENCE_TITLE_TEXT = "Device Evidence"
EVIDENCE_BUS_HEALTH_TEXT = "CAN Bus Health (System Console)"
EVIDENCE_FILTER_ALL = "all"
EVIDENCE_FILTER_CONFLICTED = "conflicted"
EVIDENCE_FILTER_MISSING = "missing"
EVIDENCE_FILTER_DEGRADED = "degraded"
EVIDENCE_FILTER_OPTIONS = (
    EVIDENCE_FILTER_ALL,
    EVIDENCE_FILTER_CONFLICTED,
    EVIDENCE_FILTER_MISSING,
    EVIDENCE_FILTER_DEGRADED,
)
EVIDENCE_FILTER_LABELS = {
    EVIDENCE_FILTER_ALL: "All",
    EVIDENCE_FILTER_CONFLICTED: "Conflicted",
    EVIDENCE_FILTER_MISSING: "Missing",
    EVIDENCE_FILTER_DEGRADED: "Degraded",
}
EVIDENCE_COL_DEVICE = "Device"
EVIDENCE_COL_PASSIVE = "Passive CAN"
EVIDENCE_COL_CONSOLE = "Console"
EVIDENCE_COL_PROBE = "Full Probe"
EVIDENCE_COL_PROBE_SCORE = "Full Probe Score"
EVIDENCE_COL_MANUAL = "Manual"
EVIDENCE_COL_EXISTENCE = "Existence"
EVIDENCE_COL_OPERABILITY = "Operability"
EVIDENCE_COL_IDENTITY = "Identity"
EVIDENCE_COL_CONFIDENCE = "Confidence"
EVIDENCE_COL_DEVICE_WIDTH = 180
EVIDENCE_COL_SOURCE_WIDTH = 96
EVIDENCE_COL_PROBE_SCORE_WIDTH = 92
EVIDENCE_COL_RESULT_WIDTH = 94
EVIDENCE_STATUS_OK = "OK"
EVIDENCE_STATUS_PRESENT = "PRESENT"
EVIDENCE_STATUS_ABSENT = "ABSENT"
EVIDENCE_STATUS_DEGRADED = "DEGRADED"
EVIDENCE_STATUS_FAILED = "FAILED"
EVIDENCE_STATUS_UNKNOWN = "UNKNOWN"
EVIDENCE_STATUS_MATCHING = "MATCHING"
EVIDENCE_STATUS_WRONG = "WRONG"
EVIDENCE_STATUS_NOT_RUN = "NOT RUN"
EVIDENCE_STATUS_CONFLICT = "CONFLICT"
EVIDENCE_CONFIDENCE_HIGH = "HIGH"
EVIDENCE_CONFIDENCE_MEDIUM = "MEDIUM"
EVIDENCE_CONFIDENCE_LOW = "LOW"
EVIDENCE_SOURCE_NONE = "--"
EVIDENCE_NOTE_SEPARATOR = " | "
EVIDENCE_MANUAL_PLACEHOLDER = "Not run"
EVIDENCE_MANUAL_OUTCOME_CORRECT = "correct_response"
EVIDENCE_MANUAL_OUTCOME_NO_RESPONSE = "no_response"
EVIDENCE_MANUAL_OUTCOME_WRONG_DEVICE = "wrong_device_response"
EVIDENCE_MANUAL_OUTCOME_WRONG_BRANCH = "wrong_branch_response"
EVIDENCE_MANUAL_OUTCOME_INTERMITTENT = "intermittent_response"
EVIDENCE_MANUAL_OUTCOME_DEGRADED = "degraded_response"
EVIDENCE_MANUAL_OUTCOME_UNCERTAIN = "operator_uncertain"
EVIDENCE_MANUAL_OUTCOME_LABELS = {
    EVIDENCE_MANUAL_OUTCOME_CORRECT: "Correct response",
    EVIDENCE_MANUAL_OUTCOME_NO_RESPONSE: "No response",
    EVIDENCE_MANUAL_OUTCOME_WRONG_DEVICE: "Wrong device",
    EVIDENCE_MANUAL_OUTCOME_WRONG_BRANCH: "Wrong branch",
    EVIDENCE_MANUAL_OUTCOME_INTERMITTENT: "Intermittent",
    EVIDENCE_MANUAL_OUTCOME_DEGRADED: "Degraded",
    EVIDENCE_MANUAL_OUTCOME_UNCERTAIN: "Uncertain",
}
EVIDENCE_MANUAL_DIALOG_TITLE = "Manual Test Result"
EVIDENCE_MANUAL_DIALOG_PROMPT = "Select observed device/branch:"
EVIDENCE_MANUAL_DIALOG_OK = "Record"
EVIDENCE_MANUAL_DIALOG_CANCEL = "Cancel"
EVIDENCE_MANUAL_DIALOG_WIDTH = 320
EVIDENCE_MANUAL_DIALOG_HEIGHT = 140
EVIDENCE_PROBE_STATS_WAITING = "Updates only when Full Probe is run."
EVIDENCE_PROBE_STATS_RUNNING = "Full Probe is running now."
EVIDENCE_PROBE_STATS_LAST_COMPLETE_FMT = "Last Full Probe completed {age} ago."
EVIDENCE_PROBE_STATS_RUN_COUNT_FMT = "Full Probe runs requested: {count}"
EVIDENCE_MANUAL_OPERABILITY_WINDOW_SEC = 120.0
EVIDENCE_MANUAL_IDENTITY_WINDOW_SEC = 900.0
EVIDENCE_MOTION_CMD_THRESHOLD_DUTY = 0.15
EVIDENCE_MOTION_MIN_RPM = 5.0
EVIDENCE_MOTION_MIN_POSITION_DELTA_ROT = 0.05
EVIDENCE_MANUAL_MOTION_WINDOW_SEC = 3.0
EVIDENCE_MANUAL_MOTION_SETTLE_SEC = 0.4
EVIDENCE_MANUAL_NOTE_AGE_IDENTITY_ONLY = "Manual result is older than the operability window; using it only as identity evidence."
EVIDENCE_MANUAL_NOTE_STALE = "Manual result is stale and not being used for automatic conclusions."
EVIDENCE_MANUAL_NOTE_CONFLICT = "Manual evidence conflicts with stronger automatic evidence."
EVIDENCE_MOTION_NOTE_NO_ROTATION = "Motor commanded but no rotation detected."
EVIDENCE_MOTION_NOTE_ROTATING = "Motor rotation detected."
EVIDENCE_LAYOUT_TOP_WEIGHT = 5
EVIDENCE_LAYOUT_BOTTOM_WEIGHT = 1
EVIDENCE_SUMMARY_TABLE_HEIGHT = 5
EVIDENCE_TEXT_HEIGHT_DEFAULT = 3
EVIDENCE_TEXT_HEIGHT_PROBE = 6
EVIDENCE_TEXT_HEIGHT_MANUAL = 6
EVIDENCE_TEXT_HEIGHT_NOTES = 4
EVIDENCE_PROBE_DETAIL_LIMIT = 4
EVIDENCE_INSPECTOR_PANED_WEIGHT_DEFAULT = 1
EVIDENCE_INSPECTOR_PANED_WEIGHT_PROBE = 2
EVIDENCE_INSPECTOR_PANED_WEIGHT_MANUAL = 2
EVIDENCE_INSPECTOR_PANED_WEIGHT_NOTES = 1
EVIDENCE_FIELD_CMD_DUTY = "cmdDuty"
EVIDENCE_FIELD_APPLIED_DUTY = "appliedDuty"
EVIDENCE_FIELD_VEL_RPM = "velRpm"
EVIDENCE_FIELD_MOTOR_CURRENT_A = "motorCurrentA"
EVIDENCE_FIELD_POSITION_ROT = "positionRot"
EVIDENCE_MANUAL_LINE_RESULT = "result={value}"
EVIDENCE_MANUAL_LINE_AGE = "age={value}"
EVIDENCE_MANUAL_LINE_OBSERVED = "observed={value}"
EVIDENCE_MANUAL_LINE_NOTES = "note={value}"
EVIDENCE_MANUAL_LINE_RECORDED = "at={value}"
EVIDENCE_MANUAL_LINE_AUTO_RESULT = "autoResult={value}"
EVIDENCE_MANUAL_LINE_MOTION = "motionCheck={value}"
EVIDENCE_MANUAL_LINE_MOTION_VALUES = "cmdDuty={cmd} | appliedDuty={applied} | velRpm={vel} | positionRot={position} | positionDeltaRot={delta} | motorCurrentA={current}"
EVIDENCE_MANUAL_MOTION_ACTIVE = "active"
EVIDENCE_MANUAL_MOTION_PASS = "rotation_detected"
EVIDENCE_MANUAL_MOTION_FAIL = "no_rotation_detected"
EVIDENCE_MANUAL_MOTION_IDLE = "idle"
EVIDENCE_MANUAL_AUTO_RESULT_RUNNING = "test_running"
EVIDENCE_MANUAL_AUTO_RESULT_ROTATION = "rotation_detected"
EVIDENCE_MANUAL_AUTO_RESULT_NO_ROTATION = "no_rotation_detected"
EVIDENCE_MANUAL_AUTO_RESULT_LABELS = {
    EVIDENCE_MANUAL_AUTO_RESULT_RUNNING: "Test running",
    EVIDENCE_MANUAL_AUTO_RESULT_ROTATION: "Rotation detected",
    EVIDENCE_MANUAL_AUTO_RESULT_NO_ROTATION: "No rotation detected",
}
EVIDENCE_VALUE_NOT_APPLICABLE = "n/a"
EVIDENCE_INTERPRETATION_TEXT = "Final Interpretation"
EVIDENCE_PRESENCE_TEXT = "Presence Check (Robot Local Snapshot)"
EVIDENCE_PASSIVE_TEXT = "Passive CAN Evidence (CANable Observer)"
EVIDENCE_CONSOLE_TEXT = "Console Evidence (Robot/NT)"
EVIDENCE_PROBE_TEXT = "Full Probe (Manual One-Shot)"
EVIDENCE_MANUAL_TEXT = "Manual Test (Operator / Motion)"
EVIDENCE_NOTES_TEXT = "Conflicts / Notes"
EVIDENCE_LABEL_EXISTENCE = "Existence"
EVIDENCE_LABEL_OPERABILITY = "Operability"
EVIDENCE_LABEL_IDENTITY = "Identity"
EVIDENCE_LABEL_CONFIDENCE = "Confidence"
EVIDENCE_LABEL_PASSIVE = "Passive"
EVIDENCE_LABEL_CONSOLE = "Console"
EVIDENCE_LABEL_PROBE = "Probe"
EVIDENCE_LABEL_MANUAL = "Manual"
EVIDENCE_NOTE_NONE = "No major source conflict."
EVIDENCE_BUS_HEALTH_OK = "OK"
EVIDENCE_BUS_HEALTH_ELEVATED = "ELEVATED LOAD"
EVIDENCE_BUS_HEALTH_DEGRADED = "DEGRADED"
EVIDENCE_BUS_HEALTH_CRITICAL = "CRITICAL"
EVIDENCE_CAN_TEXT_HIGH_UTIL = "high utilization"
EVIDENCE_CAN_TEXT_RECOVERED = "utilization recovered"
EVIDENCE_CAN_TEXT_BUS_OFF = "bus off"
EVIDENCE_CAN_TEXT_ERROR_SPIKE = "error spike"
EVIDENCE_CAN_TEXT_TX_FULL = "tx full"
EVIDENCE_CONSOLE_SCOPE_DEVICES = "devices"
EVIDENCE_CONSOLE_SCOPE_SYSTEM = "system"
EVIDENCE_CONSOLE_KEY_ACTIVE = "Active"
EVIDENCE_CONSOLE_KEY_COUNT = "Count"
EVIDENCE_CONSOLE_KEY_LAST_SEEN = "LastSeen"
EVIDENCE_CONSOLE_KEY_MESSAGE = "Message"
EVIDENCE_CONSOLE_KEY_SEVERITY = "Severity"
EVIDENCE_CONSOLE_KEY_WARN = "warnCount"
EVIDENCE_CONSOLE_KEY_ERROR = "errorCount"
EVIDENCE_CONSOLE_KEY_FATAL = "fatalCount"
EVIDENCE_EVENT_TYPE_BUS_FAULT = "BUS_FAULT_SUSPECTED"
EVIDENCE_TEXT_DEVICE_TIMEOUT = "timeout"
EVIDENCE_TEXT_STALE = "stale"
EVIDENCE_STATE_OK = "ok"
EVIDENCE_STATE_DEGRADED = "degraded"
EVIDENCE_STATE_MISSING = "missing"
EVIDENCE_STATE_UNKNOWN = "unknown"
EVIDENCE_STATE_IDENTITY = "identity"
EVIDENCE_ACTIVE_PROBE_FRESH_SEC = 15.0
EVIDENCE_ACTIVE_PROBE_AGING_SEC = 60.0
EVIDENCE_ACTIVE_PROBE_STALE_SEC = 180.0
EVIDENCE_PROBE_AGE_FRESH = "fresh"
EVIDENCE_PROBE_AGE_AGING = "aging"
EVIDENCE_PROBE_AGE_STALE = "stale"
EVIDENCE_PROBE_NOTE_AGING = "Full-probe result is aging; lowering its weight."
EVIDENCE_PROBE_NOTE_STALE = "Full-probe result is stale; using it only as historical evidence."
EVIDENCE_PROBE_NOTE_ONE_SHOT = "Full Probe is a cached manual one-shot diagnostic result."
EVIDENCE_PROBE_NO_DEVICE_RESULT = "No device-specific full-probe result for this device."
EVIDENCE_PROBE_NOT_IN_RUNTIME_SET = (
    "This device was not part of the active runtime probe set when Full Probe ran."
)
EVIDENCE_NOTE_PASSIVE_WITHOUT_PROBE_RESULT = (
    "Passive CAN traffic is present, but Full Probe did not produce a device-specific result here."
)
ATTACHMENT_KEY_TYPE = "type"
ATTACHMENT_TYPE_PRESENCE_CHECK = "presenceCheck"
ATTACHMENT_TYPE_ACTIVE_PRESENCE_PROBE = "activePresenceProbe"
ATTACHMENT_TYPE_REV_MOTOR = "revMotor"
ATTACHMENT_TYPE_CTRE_MOTOR = "ctreMotor"
RUNTIME_PRESENCE_KEY_BUCKET = "bucket"
RUNTIME_PRESENCE_KEY_STATUS = "status"
RUNTIME_PRESENCE_KEY_SOURCE = "source"
RUNTIME_PRESENCE_KEY_UPDATED_AT_MS = "updatedAtMs"
RUNTIME_PRESENCE_KEY_MESSAGE = "message"
RUNTIME_PROBE_KEY_BUCKET = "bucket"
RUNTIME_PROBE_KEY_SCORE = "score"
RUNTIME_PROBE_KEY_MAX_SCORE = "maxScore"
RUNTIME_PROBE_KEY_UPDATED_AT_MS = "updatedAtMs"
RUNTIME_PROBE_KEY_FAILED_CHECKS = "failedChecks"
RUNTIME_PROBE_KEY_WARNINGS = "warnings"
RUNTIME_PROBE_KEY_ERRORS = "errors"
VIS_RAW_COL_ARB_WIDTH = 96
VIS_RAW_COL_PACKETS_WIDTH = 72
VIS_RAW_COL_RATE_WIDTH = 72
VIS_RAW_COL_SMALL_WIDTH = 42
VIS_RAW_COL_API_WIDTH = 46
VIS_RAW_COL_PGN_WIDTH = 84
INVENTORY_KEY_COMMANDS = "commands"
INVENTORY_KEY_SHOW_IN_HOST_UI = "showInHostUi"
INVENTORY_KEY_UI_SECTION = "uiSection"
INVENTORY_KEY_NAME = "name"
INVENTORY_KEY_UI_LABEL = "uiLabel"
INVENTORY_KEY_UI_DESCRIPTION = "uiDescription"
INVENTORY_KEY_UI_ARGS_JSON = "uiArgsJson"
INVENTORY_KEY_ACTION_KIND = "actionKind"
INVENTORY_KEY_SOURCE = "source"
KEY_NAME = "name"
CMD_SHOW_RUNTIME_STATE = "showRuntimeState"
CMD_SHOW_LIFECYCLE_STATE = "showLifecycleState"
LIFECYCLE_DEFAULT_MODE = "READ_ONLY"
ACTION_KIND_REMOTE_COMMAND = "remoteCommand"
ACTION_SOURCE_ROBOT = "robot"
DSL_FILE_TYPES = (("DSL files", "*.dsl"), ("Text files", "*.txt"), ("All files", "*.*"))
DSL_IMPORT_CANCELLED = "DSL import cancelled."
DSL_VALIDATE_CANCELLED = "DSL validation cancelled."
DSL_IMPORT_PATH_FMT = "IMPORT DSL {path}"
DSL_CREATE_START_FMT = "CREATE DSL profile={profile} target={target}"
DSL_COPY_START_FMT = "COPY DSL test={source} profile={profile} target={target}"
DSL_VALIDATE_START_FMT = "VALIDATE DSL profile={profile}"
DSL_IMPORT_GLOBAL_PATH_FMT = "IMPORT GLOBAL DSL {path}"
DSL_IMPORT_CONFIG_PATH_FMT = "IMPORT CONFIG DSL {path} profile={profile}"
DSL_COPY_GLOBAL_CONFIG_FMT = "COPY GLOBAL DSL test={source} profile={profile} target={target}"
DSL_COPY_TO_PROFILE_FMT = "COPY DSL TO PROFILE test={source} profile={profile} target={target}"
DSL_CREATE_SAVED_FMT = "Local DSL test created. Push config to the robot to use the updated test."
DSL_IMPORT_SAVED_FMT = "Local DSL import saved. Push config to the robot to use the updated test."
DSL_COPY_SAVED_FMT = "Local DSL copy saved. Push config to the robot to use the updated test."
DSL_IMPORT_GLOBAL_SAVED_FMT = "External global DSL library updated."
DSL_IMPORT_CONFIG_SAVED_FMT = "Config library DSL import saved. Push config to the robot to use the updated test."
DSL_COPY_CONFIG_SAVED_FMT = "Config library DSL copy saved. Push config to the robot to use the updated test."
DSL_COPY_DUPLICATE_PREFIX = "ERROR: target DSL test already exists:"
DSL_COPY_DUPLICATE_REVEAL_FMT = "Profile test already exists and was selected: {name}"
DSL_VALIDATE_OK_FMT = "DSL validation OK for profile {profile}."
DSL_VALIDATE_FAIL_FMT = "DSL validation failed for profile {profile}."
DSL_DIALOG_CREATE_NAME_TITLE = "Create New DSL Test"
DSL_DIALOG_CREATE_NAME_PROMPT = "Profile test name:"
DSL_DIALOG_IMPORT_NAME_TITLE = "Import DSL Test"
DSL_DIALOG_IMPORT_NAME_PROMPT = "Test name:"
DSL_DIALOG_COPY_NAME_TITLE = "Copy Global Test To Profile"
DSL_DIALOG_COPY_NAME_PROMPT = "Profile test name:"
DSL_OUTPUT_NO_PROFILE = "No profile selected for DSL action."
DSL_OUTPUT_NO_GLOBAL_TEST = "No global library test selected for DSL copy."
DSL_OUTPUT_NO_CONFIG_TEST = "No config library test selected for DSL copy."
DSL_CREATE_CANCELLED = "DSL test creation cancelled."
DSL_COPY_CANCELLED = "DSL copy cancelled."
DSL_RENAME_CANCELLED = "DSL rename cancelled."
DSL_CREATE_NAME_REQUIRED = "DSL test creation blocked: test name is required."
DSL_COPY_NAME_REQUIRED = "DSL copy blocked: test name is required."
DSL_RENAME_NAME_REQUIRED = "DSL rename blocked: test name is required."
DSL_OUTPUT_NO_TEST = "No test selected for DSL action."
DSL_RENAME_START_FMT = "RENAME DSL test={source} target={target}"
DSL_DELETE_START_FMT = "DELETE DSL test={name}"
DSL_RENAME_SAVED_FMT = "DSL test renamed."
DSL_DELETE_SAVED_FMT = "DSL test deleted and archived: {path}"
DSL_DIALOG_RENAME_NAME_TITLE = "Rename DSL Test"
DSL_DIALOG_RENAME_NAME_PROMPT = "New test name:"
TEST_LIBRARY_TAB_LABEL = "Tests"
TEST_LIBRARY_TITLE = "Test Library"
TEST_LIBRARY_GLOBAL_TITLE = "Global Library"
TEST_LIBRARY_CONFIG_TITLE = "Config Library"
TEST_LIBRARY_PROFILE_TITLE = "Profile Tests"
TEST_LIBRARY_DEVICES_TITLE = "Available Devices"
TEST_LIBRARY_DEVICES_COL_LABEL = "Label"
TEST_LIBRARY_DEVICES_COL_TYPE = "Type"
TEST_LIBRARY_DEVICES_COL_ID = "ID"
TEST_LIBRARY_BUTTON_REFRESH = "Refresh Lists"
TEST_LIBRARY_BUTTON_NEW = "New Test..."
TEST_LIBRARY_BUTTON_RENAME = "Rename Test..."
TEST_LIBRARY_BUTTON_DELETE = "Delete Test"
TEST_LIBRARY_BUTTON_IMPORT_GLOBAL = "Import To Global..."
TEST_LIBRARY_BUTTON_IMPORT_CONFIG = "Import To Config..."
TEST_LIBRARY_BUTTON_IMPORT_PROFILE = "Import To Profile..."
TEST_LIBRARY_BUTTON_COPY_CONFIG = "Copy To Config"
TEST_LIBRARY_BUTTON_COPY_PROFILE = "Copy To Profile"
TEST_LIBRARY_BUTTON_VALIDATE = "Validate Profile Tests"
TEST_LIBRARY_BUTTON_INFO = "Tests Info"
TEST_LIBRARY_BUTTON_OVERVIEW = "Tests Overview"
TEST_LIBRARY_BUTTON_STATE = "State"
TEST_LIBRARY_BUTTON_SOURCE = "Test Source"
TEST_LIBRARY_BUTTON_PRINT_NEXT = "Print Next"
TEST_LIBRARY_BUTTON_RUN_SELECTED = "Run Selected"
TEST_LIBRARY_BUTTON_RUN_ALL = "Run All"
TEST_LIBRARY_BUTTON_NEXT = "Test Next"
TEST_LIBRARY_BUTTON_PREV = "Test Prev"
TEST_LIBRARY_BUTTON_TOGGLE = "Toggle Enabled"
TEST_LIBRARY_STATUS_EMPTY = "Profile: (none) | Select a profile to manage runnable tests."
TEST_LIBRARY_STATUS_FMT = (
    "Profile: {profile} | Runnable set: {set_name} | "
    "Profile tests: {profile_count} | Runnable: {runnable_count} | "
    "Config library: {config_count} | Global library: {global_count}"
)
TEST_LIBRARY_SELECTION_LABEL = "Current Test"
TEST_LIBRARY_RUNNING_DEFAULT = "Running: (none)"
TEST_LIBRARY_LAST_RESULT_DEFAULT = "Last Result: (none)"
TEST_LIBRARY_STATUS_INACTIVE_PREFIX = "selected test inactive - "
TEST_LIBRARY_STATUS_READY = "active-group active - ready to run"
TEST_LIBRARY_STATUS_NO_SELECTED_TEST = TEST_LIBRARY_STATUS_INACTIVE_PREFIX + OUTPUT_NO_SELECTED_TEST
TEST_LIBRARY_STATUS_LOADED_NOT_ACTIVATED = "active-group loaded from selected test - not activated"
TEST_LIBRARY_STATUS_MANUAL_RESTORED = "manual active-group restored - not activated"
TEST_LIBRARY_STATUS_BLOCKED_ESTOP = "robot disabled (E-Stop)"
TEST_LIBRARY_STATUS_BLOCKED_DISABLED = "robot disabled"
TEST_LIBRARY_STATUS_BLOCKED_NOT_TELEOP = "robot not in teleop"
TEST_SCOPE_DETAIL_NO_SELECTION = "Select a test from one of the library lists to load its devices into active-group."
TEST_SCOPE_DETAIL_LOADED_NOT_ACTIVATED = (
    "This test has loaded its required devices into active-group. "
    "Press Activate Group, then run the test."
)
TEST_SCOPE_DETAIL_MANUAL_RESTORED = (
    "The remembered manual active-group was restored after leaving Tests. "
    "Press Activate Group before running manual actions."
)
RUNNABLE_SCOPE_DETAIL_MANUAL_NOT_ACTIVATED = (
    "Activate Group first."
)
RUNNABLE_SCOPE_DETAIL_SELECTED_TEST_NOT_ACTIVATED = (
    "Activate lifecycle first."
)
RUNNABLE_SCOPE_DETAIL_MANUAL_NOT_TELEOP = (
    "Switch to teleop, then Activate Group."
)
RUNNABLE_SCOPE_DETAIL_SELECTED_TEST_NOT_TELEOP = (
    "Switch to teleop, then Activate lifecycle."
)
RUNNABLE_SCOPE_DETAIL_MANUAL_EMPTY = (
    "Active group is empty. Add devices before Activate Group."
)
TEST_SCOPE_DETAIL_MISSING_DEVICE_PREFIX = (
    "This test cannot run because a required profile device is missing: "
)
TEST_SCOPE_DETAIL_REQUIRED_UNAVAILABLE = (
    "This test cannot run because one or more required devices are not available."
)
TEST_SCOPE_DETAIL_BLOCKED_ESTOP = (
    "This test cannot run because the robot is E-stopped. Clear the E-stop before activating the group or running the test."
)
TEST_SCOPE_DETAIL_BLOCKED_DISABLED = (
    "This test cannot run because the robot is disabled. Enable teleop before activating the group or running the test."
)
TEST_SCOPE_DETAIL_BLOCKED_NOT_TELEOP = (
    "This test cannot run because the robot is not in teleop. Switch to teleop before activating the group or running the test."
)
TEST_LIBRARY_LOCAL_SCOPE_PROFILE = "profile"
TEST_LIBRARY_LOCAL_SCOPE_CONFIG = "config"
TEST_LIBRARY_LOCAL_SCOPE_GLOBAL = "global"
TEST_SCOPE_PANEL_TITLE = "Test State"
TEST_SCOPE_PANEL_READY_HEADLINE = "READY TO RUN"
TEST_SCOPE_PANEL_INACTIVE_HEADLINE = "NOT RUNNABLE"
TEST_SCOPE_PANEL_NO_SELECTION_HEADLINE = "NO TEST SELECTED"
TEST_SCOPE_PANEL_WAITING_HEADLINE = "WAITING FOR STATE"
RUNNABLE_SCOPE_PANEL_TITLE = "Runnable State"
RUNNABLE_SCOPE_PANEL_READY_DETAIL = "manual/group controls available - ready to run"
RUNNABLE_SCOPE_PANEL_WAITING_DETAIL = "waiting for robot runtime state"
TEST_SCOPE_PANEL_READY_BG = "#dcfce7"
TEST_SCOPE_PANEL_READY_FG = "#166534"
TEST_SCOPE_PANEL_INACTIVE_BG = "#fee2e2"
TEST_SCOPE_PANEL_INACTIVE_FG = "#991b1b"
TEST_SCOPE_PANEL_NEUTRAL_BG = "#e5e7eb"
TEST_SCOPE_PANEL_NEUTRAL_FG = "#374151"
TEST_SCOPE_PANEL_BORDER = "#cbd5e1"
TEST_SCOPE_PANEL_WRAP = 320
TEST_SCOPE_PANEL_PAD_X = 12
TEST_SCOPE_PANEL_PAD_Y = 8
TEST_SCOPE_PANEL_HEADLINE_FONT = ("Segoe UI", 11, "bold")
TEST_SCOPE_PANEL_DETAIL_FONT = ("Segoe UI", 10, "normal")
TEST_RESULT_PASS_FG = "#166534"
TEST_RESULT_FAIL_FG = "#991b1b"
TEST_RESULT_RUNNING_FG = "#1d4ed8"
TEST_RESULT_NEUTRAL_FG = "#374151"
TEST_ACTIVE_GROUP_TITLE = "Active Group"
TEST_ACTIVE_GROUP_STATUS_LOCKED = "locked"
TEST_ACTIVE_GROUP_STATUS_INVALID = "invalid"
TEST_ACTIVE_GROUP_STATUS_NOT_ACTIVATED = "not instantiated"
TEST_ACTIVE_GROUP_STATUS_ENABLED = "enabled"
TEST_ACTIVE_GROUP_PANEL_EMPTY = "No test-owned active-group members."
TEST_ACTIVE_GROUP_SINGLETON_LABELS = {"controller0", "roborio", "pdp"}
TEST_LIBRARY_NOTE_TEXT = (
    "The Tests tab has three sources: external Global Library, config-shared Config Library, "
    "and selected-profile Profile Tests. Selecting a test loads active-group from that DSL test. "
    "Use Push Config to make config/profile changes available on the robot."
)
TEST_LIBRARY_SET_NONE = "(none)"
TEST_LIBRARY_NAME_NEW_FMT = "{profile}_new_test"
TEST_LIBRARY_NAME_COPY_FMT = "{profile}_{name}"
TEST_LIBRARY_INVALID_SUFFIX = " [not runnable]"
TEST_LIBRARY_LISTBOX_HEIGHT = 18
TEST_LIBRARY_STATUS_COLOR = "#374151"
TEST_LIBRARY_RESULTS_TITLE = "Test Activity"
TEST_LIBRARY_DEVICES_EMPTY = "(none)"
TEST_LIBRARY_RESULTS_HEIGHT = 8
TEST_SOURCE_TAB_LABEL = "Source Editor"
TEST_SOURCE_REFERENCE_TITLE = "DSL Reference"
TEST_SOURCE_REFERENCE_GEOMETRY = "420x180"
TEST_SOURCE_REFERENCE_TEXT = (
    'Top level: test "name", device "label"\n'
    "Phases: init:, main:, close:\n"
    "Statements: set, clear, until, abort, success, require, unsafe-exit"
)
TEST_SOURCE_COMPLETION_POPUP_TITLE = "Signal Completion"
TEST_SOURCE_COMPLETION_DEVICE_PATTERN = r'(?:\"([^\"]+)\"|([A-Za-z_][A-Za-z0-9_]*))\.$'
TEST_SOURCE_COMPLETION_EMPTY = "(no signals)"
TEST_SOURCE_COMPLETION_MODE_NONE = ""
TEST_SOURCE_COMPLETION_MODE_READ = "read"
TEST_SOURCE_COMPLETION_MODE_WRITE = "write"
TEST_SOURCE_COMPLETION_MODE_CLEAR = "clear"
TEST_SOURCE_COMPLETION_READ_PREFIXES = ("require ", "until ", "abort ", "success ")
TEST_SOURCE_COMPLETION_WRITE_PREFIXES = ("set ", "unsafe-exit ")
TEST_SOURCE_COMPLETION_CLEAR_PREFIXES = ("clear ",)
TEST_SOURCE_SWITCH_TITLE = "Unsaved Test Source"
TEST_SOURCE_SWITCH_PROMPT_FMT = "Save changes to {name} before switching tests?"
TEST_ACTIVITY_TAB_LABEL = "Test Activity"
TEST_SOURCE_BUTTON_SAVE = "Save Source"
TEST_SOURCE_BUTTON_REVERT = "Revert Source"
TEST_SOURCE_BUTTON_VALIDATE = "Validate Source"
TEST_SOURCE_STATUS_NONE = "Select a test to view source."
TEST_SOURCE_STATUS_GLOBAL_FMT = "Global library test: {name} (read-only)"
TEST_SOURCE_STATUS_CONFIG_FMT = "Config library test: {name} (editable)"
TEST_SOURCE_STATUS_PROFILE_FMT = "Profile test: {name} (editable)"
TEST_SOURCE_STATUS_CONFIG_SAVED_FMT = "Saved source for config library test {name}. Push Config to update the robot."
TEST_SOURCE_STATUS_CONFIG_SAVED_INVALID_FMT = (
    "Saved source for config library test {name}. The current profile cannot run it until validation errors are fixed."
)
TEST_SOURCE_STATUS_SAVED_FMT = "Saved source for profile test {name}. Push Config to update the robot."
TEST_SOURCE_STATUS_VALID_FMT = "Source validation OK for profile test {name}."
TEST_SOURCE_STATUS_INVALID_FMT = "Source validation failed for profile test {name}."
TEST_SOURCE_STATUS_SAVED_INVALID_FMT = (
    "Saved source for profile test {name}. Test is not runnable until validation errors are fixed."
)
TEST_SOURCE_STATUS_DIRTY_SUFFIX = " [modified]"
TEST_SOURCE_EDIT_BLOCKED = "Source editing is only available for profile-owned tests."
TEST_SOURCE_EMPTY = ""
TEST_SOURCE_START_VALIDATE_FMT = "VALIDATE SOURCE test={name} profile={profile}"
TEST_SOURCE_START_SAVE_FMT = "SAVE SOURCE test={name} profile={profile}"
TEST_SOURCE_RESULTS_TITLE = "Source Validation Results"
TEST_SOURCE_RESULTS_HEIGHT = 12
TEST_SOURCE_RESULTS_GEOMETRY = "720x280"
TEST_SOURCE_RESULTS_CLOSE = "Close"
TEST_SOURCE_LINE_NUMBER_WIDTH = 5
HIDDEN_LEFT_RAIL_COMMANDS = {
    "printState",
    "printTestsInfo",
    "printTestsOverview",
    "printSelectedTestSource",
    "printNextTest",
    "runAll",
    "runTest",
    "testNext",
    "testPrev",
    "toggleEnabled",
}
TEST_ACTIVITY_COMMANDS = {
    "printstate",
    "printtestsinfo",
    "printtestsoverview",
    "printselectedtestsource",
    "printnexttest",
    "selecttestbyname",
    "runall",
    "runalltests",
    "runtest",
    "testnext",
    "testprev",
    "selecttestnext",
    "selecttestprev",
    "toggleenabled",
    "groupreplacemembers",
    "lifecycleactivate",
    "lifecycledeactivateactive",
    "showlifecyclestate",
}
TEST_OUTPUT_PREFIX_STARTED = "Test started #"
TEST_OUTPUT_PREFIX_STARTED_LEGACY = "Test started: "
TEST_OUTPUT_PREFIX_NAME = "Test #"
TEST_OUTPUT_PREFIX_RESULT = "Test result #"
TEST_OUTPUT_PREFIX_RESULT_LEGACY = "Test result: "
TEST_OUTPUT_PREFIX_RUN_ALL_COMPLETE = "Run-all complete."
UNICODE_CATEGORY_CONTROL = "Cc"
UNICODE_CATEGORY_FORMAT = "Cf"
OUTPUT_SANITIZE_DROP_CATEGORIES = {
    UNICODE_CATEGORY_CONTROL,
    UNICODE_CATEGORY_FORMAT,
}


def _normalize_host_action_row(row: Dict[str, Any], default_source: str, default_kind: str) -> Dict[str, Any]:
    """
    NAME
        _normalize_host_action_row - Normalize a host UI action row to the merged action schema.
    """
    from .command_catalog_service import normalize_action_row

    return normalize_action_row(row, default_source, default_kind)


def _build_host_ui_sections_from_inventory(commands: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    NAME
        _build_host_ui_sections_from_inventory - Build host UI sections from command inventory rows.
    """
    from .command_catalog_service import build_host_ui_sections_from_inventory

    return build_host_ui_sections_from_inventory(commands)


def _merge_host_ui_actions(
    robot_actions: List[Dict[str, Any]], host_actions: List[Dict[str, Any]]
) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    """
    NAME
        _merge_host_ui_actions - Merge robot and host action metadata into one UI action model.
    """
    return merge_host_ui_actions_shared(
        robot_actions,
        host_actions,
        ACTION_SOURCE_ROBOT,
        ACTION_SOURCE_HOST,
        ACTION_KIND_HOST_LOCAL,
    )


def _load_generated_command_metadata() -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    """
    NAME
        _load_generated_command_metadata - Load merged robot and host UI action metadata.
    """
    return load_host_ui_command_metadata(
        HOST_UI_ACTIONS,
        ACTION_SOURCE_ROBOT,
        ACTION_SOURCE_HOST,
        ACTION_KIND_HOST_LOCAL,
    )


def _sanitize_stream_output_line(line: object) -> str:
    """
    NAME
        _sanitize_stream_output_line - Remove hidden control/format characters from streamed output.
    """
    text = str(line or "")
    if not text:
        return ""
    cleaned_chars: List[str] = []
    for char in text:
        if unicodedata.category(char) in OUTPUT_SANITIZE_DROP_CATEGORIES:
            continue
        cleaned_chars.append(char)
    return "".join(cleaned_chars)


ACTIONS_BY_NAME, HOST_UI_SECTIONS = _load_generated_command_metadata()


def _load_profiles() -> List[str]:
    """
    NAME
        _load_profiles - Load profile names from bringup_system.json.
    """
    ok, _err = reload_profiles()
    if not ok:
        err = get_profiles_load_error()
        if err:
            print(f"ERROR: bringup_system.json load failed: {err}")
        return []
    try:
        names = LocalConfigQueryService().list_profiles()
        if names:
            return names
    except Exception:
        pass
    return sorted(name for name in list_profiles() if name)


def _load_tests(profile_name: str) -> List[str]:
    """
    NAME
        _load_tests - Load test names for a profile.
    """
    if not profile_name or profile_name == PROFILE_NONE:
        return []
    try:
        return LocalConfigQueryService().test_names_for_profile(profile_name)
    except Exception:
        pass
    return []


def _normalize_profile_name(profile_name: object) -> str:
    """
    NAME
        _normalize_profile_name - Return a trimmed profile name or PROFILE_NONE.
    """
    name = normalize_profile_name_shared(profile_name)
    if not name:
        return PROFILE_NONE
    return name


def _selectable_profiles() -> List[str]:
    """
    NAME
        _selectable_profiles - Return the UI profile list including the empty selection.
    """
    try:
        return LocalConfigQueryService().selectable_profiles(PROFILE_NONE)
    except Exception:
        return [PROFILE_NONE] + (_load_profiles() or [])


def _startup_selected_profile(profile_names: List[str], auto_select_default: bool) -> str:
    """
    NAME
        _startup_selected_profile - Resolve the startup-selected profile for the UI.
    """
    default_profile = get_default_profile()
    if (
        auto_select_default
        and isinstance(default_profile, str)
        and default_profile in profile_names
    ):
        return default_profile
    return PROFILE_NONE


def _load_tests_from_store(profile_name: str) -> Optional[List[str]]:
    """
    NAME
        _load_tests_from_store - Load test names for a profile from the config store.
    """
    store = ConfigSchemaStore()
    try:
        store.load(repo_root())
    except Exception:
        return None
    model = store.tests_model(profile_name)
    if model is None:
        return None
    names: List[str] = []
    for test_set in model.test_sets.values():
        for test in test_set.tests:
            name = test.name
            if isinstance(name, str) and name and name != TEST_NAME_EMPTY:
                names.append(name)
    return sorted(set(names))


def _load_tests_from_dsl_store(profile_name: str) -> Optional[List[str]]:
    """
    NAME
        _load_tests_from_dsl_store - Load test names for a profile from top-level dslTests.
    """
    try:
        payload = ConfigRepository().load_canonical().to_payload()
    except Exception:
        return None
    if not isinstance(payload.get(KEY_DSL_TESTS), dict):
        return None
    return resolve_runnable_profile_test_names(payload, profile_name)


def _ui_prefs_path() -> Path:
    """
    NAME
        _ui_prefs_path - Return the repo-local UI command preferences path.
    """
    return repo_root() / UI_PREFS_DIR / UI_PREFS_SUBDIR / UI_PREFS_FILE


def _load_ui_prefs_payload() -> Dict[str, Any]:
    """
    NAME
        _load_ui_prefs_payload - Load raw UI preferences payload.
    """
    path = _ui_prefs_path()
    if not path.exists():
        return {}
    try:
        payload = read_json(path)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_ui_command_prefs() -> Dict[str, bool]:
    """
    NAME
        _load_ui_command_prefs - Load per-command visibility preferences.
    """
    payload = _load_ui_prefs_payload()
    commands = payload.get(UI_PREFS_KEY_COMMANDS, {})
    if not isinstance(commands, dict):
        return {}
    result: Dict[str, bool] = {}
    for name, value in commands.items():
        if isinstance(name, str):
            result[name] = bool(value)
    return result


def _load_ui_auto_select_default_pref() -> bool:
    """
    NAME
        _load_ui_auto_select_default_pref - Return whether startup should auto-select the default profile.
    """
    payload = _load_ui_prefs_payload()
    return bool(payload.get(UI_PREFS_KEY_AUTO_SELECT_DEFAULT_PROFILE, False))


def _load_ui_show_visibility_tab_pref() -> bool:
    """
    NAME
        _load_ui_show_visibility_tab_pref - Return whether the Visibility tab should be shown.
    """
    payload = _load_ui_prefs_payload()
    return bool(payload.get(UI_PREFS_KEY_SHOW_VISIBILITY_TAB, True))


def _load_ui_show_wall_clock_pref() -> bool:
    """
    NAME
        _load_ui_show_wall_clock_pref - Return whether the header wall clock should be shown.
    """
    payload = _load_ui_prefs_payload()
    return bool(payload.get(UI_PREFS_KEY_SHOW_WALL_CLOCK, True))


def _action_sections() -> List[Tuple[str, List[Tuple[str, Optional[str]]]]]:
    """
    NAME
        _action_sections - Build action sections with labels and commands.
    """
    sections: List[Tuple[str, List[Tuple[str, Optional[str]]]]] = []
    for section in HOST_UI_SECTIONS:
        title = str(section.get("section", "")).strip()
        commands = section.get("commands", [])
        if not title or not isinstance(commands, list):
            continue
        items: List[Tuple[str, Optional[str]]] = []
        for row in commands:
            if not isinstance(row, dict):
                continue
            action_kind = str(
                row.get(INVENTORY_KEY_ACTION_KIND, ACTION_KIND_REMOTE_COMMAND)
            ).strip()
            host_ui_allowed = bool(row.get("hostUiAllowed", True))
            if action_kind == ACTION_KIND_REMOTE_COMMAND and not host_ui_allowed:
                continue
            label = str(row.get("uiLabel", row.get("name", ""))).strip()
            command = str(row.get("name", "")).strip()
            if not label or not command:
                continue
            if command in HIDDEN_LEFT_RAIL_COMMANDS:
                continue
            items.append((label, command))
        if items:
            sections.append((title, items))
    return sections


def _build_visibility_expected_devices(devices: List[Dict[str, Any]]) -> List[Tuple[str, str]]:
    """
    NAME
        _build_visibility_expected_devices - Build label-first visibility expectations for one profile.
    """
    expected: List[Tuple[str, str]] = []
    for device in devices:
        if not isinstance(device, dict):
            continue
        label = str(device.get(PROFILE_KEY_LABEL, NT_VALUE_EMPTY)).strip()
        if not label:
            continue
        try:
            manufacturer = int(device.get(DEVICE_KEY_MFG))
            device_type = int(device.get(DEVICE_KEY_TYPE))
            device_id = int(device.get(DEVICE_KEY_ID))
        except Exception:
            continue
        identity_key = (
            str(manufacturer)
            + VIS_KEY_SEPARATOR
            + str(device_type)
            + VIS_KEY_SEPARATOR
            + str(device_id)
        )
        expected.append((label, identity_key))
    return expected


def _runtime_active_probe_attachment(device: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    NAME
        _runtime_active_probe_attachment - Return the active probe attachment from one runtime-state device.
    """
    if not isinstance(device, dict):
        return None
    attachments = device.get("attachments")
    if not isinstance(attachments, list):
        return None
    for attachment in attachments:
        if not isinstance(attachment, dict):
            continue
        attachment_type = str(attachment.get(ATTACHMENT_KEY_TYPE, "")).strip()
        if attachment_type == ATTACHMENT_TYPE_ACTIVE_PRESENCE_PROBE:
            return attachment
    return None


def _runtime_presence_check_attachment(device: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    NAME
        _runtime_presence_check_attachment - Return the live presence-check attachment from one runtime-state device.
    """
    if not isinstance(device, dict):
        return None
    attachments = device.get("attachments")
    if not isinstance(attachments, list):
        return None
    for attachment in attachments:
        if not isinstance(attachment, dict):
            continue
        attachment_type = str(attachment.get(ATTACHMENT_KEY_TYPE, "")).strip()
        if attachment_type == ATTACHMENT_TYPE_PRESENCE_CHECK:
            return attachment
    return None


def _runtime_device_field(device: Dict[str, Any], key: str) -> object:
    """
    NAME
        _runtime_device_field - Read one runtime-state field from top-level or motor attachments.
    """
    if not isinstance(device, dict) or not key:
        return None
    value = device.get(key)
    if value is not None:
        return value
    attachments = device.get("attachments")
    if not isinstance(attachments, list):
        return None
    for attachment in attachments:
        if not isinstance(attachment, dict):
            continue
        attachment_type = str(attachment.get(ATTACHMENT_KEY_TYPE, "")).strip()
        if attachment_type not in (ATTACHMENT_TYPE_REV_MOTOR, ATTACHMENT_TYPE_CTRE_MOTOR):
            continue
        value = attachment.get(key)
        if value is not None:
            return value
    return None


def _format_runtime_probe_bucket(device: Optional[Dict[str, Any]]) -> str:
    """
    NAME
        _format_runtime_probe_bucket - Format the active probe bucket for table display.
    """
    attachment = _runtime_active_probe_attachment(device or {})
    if not isinstance(attachment, dict):
        return VIS_VALUE_UNKNOWN
    bucket = str(attachment.get(RUNTIME_PROBE_KEY_BUCKET, NT_VALUE_EMPTY)).strip()
    return bucket if bucket else VIS_VALUE_UNKNOWN


def _format_runtime_probe_score(device: Optional[Dict[str, Any]]) -> str:
    """
    NAME
        _format_runtime_probe_score - Format the active probe score for table display.
    """
    attachment = _runtime_active_probe_attachment(device or {})
    if not isinstance(attachment, dict):
        return VIS_LAST_SEEN_UNKNOWN
    bucket = str(attachment.get(RUNTIME_PROBE_KEY_BUCKET, NT_VALUE_EMPTY)).strip().lower()
    if bucket in (VIS_VALUE_UNKNOWN, "unknown", NT_VALUE_EMPTY):
        return VIS_LAST_SEEN_UNKNOWN
    score = attachment.get(RUNTIME_PROBE_KEY_SCORE)
    max_score = attachment.get(RUNTIME_PROBE_KEY_MAX_SCORE)
    if isinstance(score, (int, float)) and isinstance(max_score, (int, float)):
        return f"{int(score)}/{int(max_score)}"
    if isinstance(score, (int, float)):
        return str(int(score))
    return VIS_LAST_SEEN_UNKNOWN


def _runtime_probe_age_seconds(device: Optional[Dict[str, Any]]) -> Optional[float]:
    """
    NAME
        _runtime_probe_age_seconds - Return the age in seconds of one cached active probe result.
    """
    attachment = _runtime_active_probe_attachment(device or {})
    if not isinstance(attachment, dict):
        return None
    updated_at_ms = attachment.get(RUNTIME_PROBE_KEY_UPDATED_AT_MS)
    if not isinstance(updated_at_ms, (int, float)) or float(updated_at_ms) <= 0.0:
        return None
    return max(0.0, time.time() - (float(updated_at_ms) / 1000.0))


def _runtime_probe_age_bucket(device: Optional[Dict[str, Any]]) -> str:
    """
    NAME
        _runtime_probe_age_bucket - Classify one cached active probe result by age.
    """
    age_sec = _runtime_probe_age_seconds(device)
    if not isinstance(age_sec, (int, float)):
        return VIS_VALUE_UNKNOWN
    if age_sec <= EVIDENCE_ACTIVE_PROBE_FRESH_SEC:
        return EVIDENCE_PROBE_AGE_FRESH
    if age_sec <= EVIDENCE_ACTIVE_PROBE_AGING_SEC:
        return EVIDENCE_PROBE_AGE_AGING
    return EVIDENCE_PROBE_AGE_STALE


def _runtime_probe_age_text(device: Optional[Dict[str, Any]]) -> str:
    """
    NAME
        _runtime_probe_age_text - Format one cached active probe age for UI display.
    """
    age_sec = _runtime_probe_age_seconds(device)
    if not isinstance(age_sec, (int, float)):
        return EVIDENCE_STATUS_NOT_RUN
    return _format_age_seconds(float(age_sec))


def _runtime_presence_age_seconds(device: Optional[Dict[str, Any]]) -> Optional[float]:
    """
    NAME
        _runtime_presence_age_seconds - Return the age in seconds of one live presence-check result.
    """
    attachment = _runtime_presence_check_attachment(device or {})
    if not isinstance(attachment, dict):
        return None
    updated_at_ms = attachment.get(RUNTIME_PRESENCE_KEY_UPDATED_AT_MS)
    if not isinstance(updated_at_ms, (int, float)) or float(updated_at_ms) <= 0.0:
        return None
    return max(0.0, time.time() - (float(updated_at_ms) / 1000.0))


def _runtime_presence_age_text(device: Optional[Dict[str, Any]]) -> str:
    """
    NAME
        _runtime_presence_age_text - Format one live presence-check age for UI display.
    """
    age_sec = _runtime_presence_age_seconds(device)
    if not isinstance(age_sec, (int, float)):
        return VIS_LAST_SEEN_UNKNOWN
    return _format_age_seconds(float(age_sec))


def _format_age_seconds(elapsed_sec: float) -> str:
    """
    NAME
        _format_age_seconds - Format one elapsed duration in seconds for UI display.
    """
    if elapsed_sec < 0.0:
        elapsed_sec = 0.0
    return f"{elapsed_sec:.1f}s ago"


def _manual_age_seconds(entry: Optional[Dict[str, Any]]) -> Optional[float]:
    """
    NAME
        _manual_age_seconds - Return elapsed age in seconds for one recorded manual-test entry.
    """
    if not isinstance(entry, dict):
        return None
    recorded_epoch = entry.get("recordedAtEpochSec")
    if not isinstance(recorded_epoch, (int, float)):
        return None
    return max(0.0, time.time() - float(recorded_epoch))


def _attachment_string_list(attachment: Optional[Dict[str, Any]], key: str) -> List[str]:
    """
    NAME
        _attachment_string_list - Return one attachment string-array field as a cleaned list.
    """
    if not isinstance(attachment, dict):
        return []
    values = attachment.get(key)
    if not isinstance(values, list):
        return []
    out: List[str] = []
    for value in values:
        text = str(value or "").strip()
        if text:
            out.append(text)
    return out


class BringupControlUI(tk.Tk):
    """
    NAME
        BringupControlUI - Bringup command UI with a fixed action panel.

    DESCRIPTION
        Builds a fixed action list and a scrolling output panel. Commands are
        sent over NetworkTables via a command sender callback.
    """

    def __init__(
        self,
        ui_table,
        tests_table,
        diag_table,
        rio_host: str,
        tcp_port: int,
        is_connected: Optional[Callable[[], bool]] = None,
        on_close: Optional[Callable[[], None]] = None,
        visibility_provider: Optional[object] = None,
    ) -> None:
        super().__init__()
        self._print_version_banner()
        self.title("Bringup Control")
        self.geometry("1100x720")
        self.minsize(900, 600)
        self._ui_table = ui_table
        self._tests_table = tests_table
        self._diag_table = diag_table
        self._on_close = on_close
        self._rio_host = rio_host
        self._is_connected = is_connected
        self._session = BridgeSession(rio_host, tcp_port, auto_handshake=False)
        self._tcp_connected = False
        self._last_connect_attempt = 0.0
        self._seq = 0
        self._max_lines = 500
        self._lines: List[str] = []
        self._last_ack_seq = None
        self._last_out_seq = None
        self._visibility_provider = visibility_provider
        self._visibility_last_update = 0.0
        self._visibility_sources: List[Dict[str, object]] = []
        self._visibility_columns: List[str] = []
        self._visibility_table: Optional[ttk.Treeview] = None
        self._visibility_unrecognized_table: Optional[ttk.Treeview] = None
        self._visibility_ctre_raw_table: Optional[ttk.Treeview] = None
        self._visibility_row_meta: Dict[str, Dict[str, object]] = {}
        self._visibility_selected_label = NT_VALUE_EMPTY
        self._visibility_selected_unexpected = False
        self._visibility_summary_var = tk.StringVar(value=VIS_SOURCE_COUNT_UNKNOWN)
        self._visibility_enabled_var = tk.BooleanVar(value=False)
        self._latest_visibility_snapshot: Dict[str, Any] = {}
        self._latest_visibility_summary: Dict[str, Any] = {}
        self._evidence_panel: Optional[ttk.Frame] = None
        self._evidence_live_view: Optional[LiveTopologyView] = None
        self._evidence_table: Optional[ttk.Treeview] = None
        self._evidence_summary_var = tk.StringVar(value=EVIDENCE_SUMMARY_DEFAULT)
        self._evidence_filter_var = tk.StringVar(value=EVIDENCE_FILTER_ALL)
        self._evidence_selected_label = NT_VALUE_EMPTY
        self._evidence_rows_by_label: Dict[str, Dict[str, Any]] = {}
        self._evidence_detail_vars: Dict[str, tk.StringVar] = {}
        self._evidence_text_widgets: Dict[str, tk.Text] = {}
        self._evidence_selected_title_var = tk.StringVar(value=NT_VALUE_EMPTY)
        self._evidence_syncing_selection = False
        self._evidence_pending_row_label = NT_VALUE_EMPTY
        self._evidence_pending_node_label = NT_VALUE_EMPTY
        self._evidence_manual_results: Dict[str, Dict[str, Any]] = {}
        self._evidence_last_probe_at = 0.0
        self._evidence_probe_pending = False
        self._evidence_probe_run_count = 0
        self._evidence_probe_complete_count = 0
        self._evidence_last_probe_completed_at = 0.0
        self._evidence_last_probe_complete_seq: Optional[int] = None
        self._evidence_probe_results_by_label: Dict[str, Dict[str, Any]] = {}
        self._last_selected_test = None
        self._last_sent_seq: Optional[int] = None
        self._nt_connected = False
        self._timeout_sec = 1.5
        self._client_id = str(uuid.uuid4())
        self._robot_ui_session_id: Optional[str] = None
        self._handshake_done = False
        self._handshake_inflight = False
        self._last_handshake_attempt = 0.0
        self._handshake_min_interval = 2.0
        self._handshake_warn_last = 0.0
        self._owner_required = False
        self._keepalive_interval = 1.0
        self._last_keepalive = 0.0
        self._last_selected_profile = ""
        self._ui_fail_interval = 5.0
        self._ui_failures: Dict[str, Dict[str, Any]] = {}
        self._prev_tcp_connected = False
        self._log_poll_interval = 2.0
        self._last_log_poll = 0.0
        self._log_poll_inflight = False
        self._log_poll_seq: Optional[int] = None
        self._out_dedupe_window = 2.0
        self._recent_out_lines: Dict[str, float] = {}
        self._seq_seeded = False
        self._last_cmd: Optional[Tuple[str, Optional[Dict[str, Any]]]] = None
        self._max_retries = 1
        self._state_stale_sec = 2.0
        self._state_stale = False
        self._auto_connect_enabled = True
        self._tracker = CommandTracker(timeout_sec=self._timeout_sec, max_retries=self._max_retries)
        self._live_enabled_var = tk.BooleanVar(value=False)
        self._live_source_var = tk.StringVar(value=LIVE_SOURCE_REST)
        self._live_rate_var = tk.StringVar(value=DEFAULT_RUNTIME_STATE_RATE_TEXT)
        self._live_groups_var = tk.BooleanVar(value=True)
        self._live_clock_var = tk.StringVar(value=NT_VALUE_EMPTY)
        self._live_rate_min = 0.2
        self._live_rate_max = 20.0
        self._runtime_state_hz = DEFAULT_RUNTIME_STATE_RATE_HZ
        self._runtime_state_interval = 1.0 / self._runtime_state_hz
        self._runtime_state_last_poll = 0.0
        self._runtime_state_pending_seq: Optional[int] = None
        self._runtime_state_pending_at = 0.0
        self._runtime_state_timeout_sec = 0.6
        self._runtime_state_seen = False
        self._runtime_active_known: Optional[bool] = None
        self._controlled_lifecycle_active_known: Optional[bool] = None
        self._robot_enabled_known = True
        self._robot_estopped_known = False
        self._robot_mode_known = "disabled"
        self._runtime_state_notice_text = NT_VALUE_EMPTY
        self._runtime_state_notice_level = "warn"
        self._runtime_event_notice_text = NT_VALUE_EMPTY
        self._runtime_event_notice_level = "warn"
        self._runtime_state_path: Optional[str] = None
        self._runtime_state_path_mtime: Optional[float] = None
        self._latest_runtime_state_payload: Dict[str, Any] = {}
        self._latest_runtime_devices: Dict[str, Dict[str, Any]] = {}
        self._presence_overrides_file: Dict[str, str] = {}
        self._presence_timeline: List[Dict[str, Any]] = []
        self._presence_timeline_start = PRESENCE_TIME_NONE
        self._presence_timeline_period = PRESENCE_TIME_NONE
        self._runtime_state_backoff = 1.0
        self._runtime_state_idle_count = 0
        self._runtime_state_idle_pause_sec = 5.0
        self._runtime_state_pause_until: Optional[float] = None
        self._poll_interval_active = 0.25
        self._poll_interval_idle = 1.0
        self._live_view: Optional[LiveTopologyView] = None
        self._visibility_live_view: Optional[LiveTopologyView] = None
        self._evidence_live_view = None
        self._manual_duty_popup: Optional[tk.Toplevel] = None
        self._manual_duty_var = tk.DoubleVar(value=MANUAL_DUTY_DEFAULT)
        self._manual_duty_value_var = tk.StringVar(
            value=MANUAL_DUTY_VALUE_FMT.format(value=MANUAL_DUTY_DEFAULT)
        )
        self._manual_duty_label = MANUAL_DUTY_NO_LABEL
        self._manual_duty_targets: List[str] = []
        self._manual_duty_group_name = MANUAL_DUTY_NO_LABEL
        self._manual_duty_last_sent_value: Optional[float] = None
        self._manual_duty_last_sent_at = 0.0
        self._manual_duty_pending_after: Optional[str] = None
        self._manual_motion_checks: Dict[str, Dict[str, Any]] = {}
        self._manual_test_observations: Dict[str, Dict[str, Any]] = {}
        self._profile_devices: Dict[str, Dict[str, Any]] = {}
        self._test_profile_devices: Dict[str, Dict[str, Any]] = {}
        self._remembered_manual_active_group_members: List[Dict[str, Any]] = []
        self._tests_active_group_rows: List[Dict[str, Any]] = []
        self._tests_active_group_membership_key: Tuple[str, ...] = tuple()
        self._group_owner_mode = GROUP_SOURCE_MANUAL
        self._last_right_tab_text = NT_VALUE_EMPTY
        self._pending_tests_boundary_transition: Optional[Tuple[str, str]] = None
        self._robot_selected_profile = PROFILE_NONE
        self._robot_active_runtime_profile = PROFILE_NONE
        self._last_profile_context = PROFILE_NONE
        self._last_profile_mismatch_prompt: Optional[Tuple[str, str]] = None
        self._ui_command_prefs = _load_ui_command_prefs()
        self._ui_auto_select_default_profile = _load_ui_auto_select_default_pref()
        self._ui_show_visibility_tab = _load_ui_show_visibility_tab_pref()
        self._ui_show_wall_clock = _load_ui_show_wall_clock_pref()
        self._ui_pref_vars: Dict[str, tk.BooleanVar] = {}
        self._build_menu()
        self._build_ui()
        self._apply_profile_selection(self._profile_box.get(), reload_views=True)
        self.after_idle(self._poll_nt)
        self.protocol("WM_DELETE_WINDOW", self._handle_close)

    def _print_version_banner(self) -> None:
        """
        NAME
            _print_version_banner - Print the bringup UI version on startup.
        """
        version = VERSIONS.get(VERSION_APP_NAME, "")
        if not version:
            return
        print(VERSION_TITLE)
        print(format_version_line(VERSION_APP_NAME, version))
        for line in build_lines():
            print(line)

    def _build_menu(self) -> None:
        """
        NAME
            _build_menu - Create the main menubar with a Help menu.
        """
        menubar = tk.Menu(self)
        prefs_menu = tk.Menu(menubar, tearoff=False)
        self._auto_select_default_profile_var = tk.BooleanVar(
            value=self._ui_auto_select_default_profile
        )
        prefs_menu.add_checkbutton(
            label="Auto-select default profile on startup",
            variable=self._auto_select_default_profile_var,
            command=self._set_auto_select_default_profile_pref,
        )
        self._show_visibility_tab_var = tk.BooleanVar(value=self._ui_show_visibility_tab)
        prefs_menu.add_checkbutton(
            label="Show Visibility Tab",
            variable=self._show_visibility_tab_var,
            command=self._set_show_visibility_tab_pref,
        )
        self._show_wall_clock_var = tk.BooleanVar(value=self._ui_show_wall_clock)
        prefs_menu.add_checkbutton(
            label="Show Wall Clock",
            variable=self._show_wall_clock_var,
            command=self._set_show_wall_clock_pref,
        )
        prefs_menu.add_separator()
        for _section, items in _action_sections():
            for _label, command in items:
                if not command:
                    continue
                metadata = ACTIONS_BY_NAME.get(command, {})
                label = str(metadata.get("uiLabel", command))
                default_visible = bool(metadata.get("showInHostUi", True))
                visible = self._ui_command_prefs.get(command, default_visible)
                var = tk.BooleanVar(value=visible)
                self._ui_pref_vars[command] = var
                prefs_menu.add_checkbutton(
                    label=label,
                    variable=var,
                    command=lambda c=command, v=var: self._set_command_visibility(c, bool(v.get())),
                )
        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="Help", command=self._show_help)
        help_menu.add_command(label="Color Key", command=self._toggle_color_key_window)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Preferences", menu=prefs_menu)
        menubar.add_cascade(label="Help", menu=help_menu)
        self.config(menu=menubar)

    def _build_ui(self) -> None:
        """
        NAME
            _build_ui - Construct the fixed action layout and output panel.
        """
        header = ttk.Frame(self, padding=10)
        header.pack(fill="x")
        ttk.Label(header, text="Bringup Control", font=("Trebuchet MS", 16)).pack(
            side="left"
        )

        profile_names = _load_profiles() or []
        profiles = _selectable_profiles()
        active_profile = _startup_selected_profile(
            profile_names, self._ui_auto_select_default_profile
        )
        tests = _load_tests(active_profile) or [PROFILE_NONE]

        profile_box = ttk.Combobox(header, values=profiles, state="readonly", width=18)
        profile_box.set(active_profile)
        self._profile_box = profile_box
        profile_box.bind("<<ComboboxSelected>>", self._on_profile_selected)
        ttk.Label(header, text="Profile").pack(side="left", padx=(16, 4))
        profile_box.pack(side="left")
        ttk.Button(header, text="Refresh", command=self._refresh_profiles).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(
            header, text=BUTTON_PUSH_CONFIG, command=self._push_config_from_ui
        ).pack(side="left", padx=(10, 0))
        ttk.Button(
            header, text=BUTTON_DOWNLOAD_CONFIG, command=self._download_current_config_from_ui
        ).pack(side="left", padx=(6, 0))
        ttk.Button(
            header, text=BUTTON_SHOW_RUNTIME_STATE, command=self._show_runtime_state_from_ui
        ).pack(side="left", padx=(6, 0))
        activate_scope_button = ttk.Button(
            header, text=BUTTON_ACTIVATE_GROUP, command=self._activate_scope_from_ui
        )
        activate_scope_button.pack(side="left", padx=(10, 0))
        self._activate_scope_button = activate_scope_button
        deactivate_scope_button = ttk.Button(
            header, text=BUTTON_DEACTIVATE_GROUP, command=self._deactivate_scope_from_ui
        )
        deactivate_scope_button.pack(side="left", padx=(6, 0))
        self._deactivate_scope_button = deactivate_scope_button
        ttk.Button(
            header, text=BUTTON_SHOW_LIFECYCLE_STATE, command=self._show_lifecycle_state_from_ui
        ).pack(side="left", padx=(6, 0))
        self._scope_context_var = tk.StringVar(value=GROUP_SOURCE_LABEL_MANUAL)
        ttk.Label(
            header,
            textvariable=self._scope_context_var,
            foreground="#374151",
        ).pack(side="left", padx=(12, 0))

        self._selected_test_var = tk.StringVar(value=tests[0])
        self._running_text_var = tk.StringVar(value=TEST_LIBRARY_RUNNING_DEFAULT)
        self._last_result_text_var = tk.StringVar(value=TEST_LIBRARY_LAST_RESULT_DEFAULT)
        self._last_selected_test = str(self._selected_test_var.get() or "").strip()
        wall_clock_frame = ttk.Frame(header)
        wall_clock_frame.pack(side="left", padx=(12, 0))
        ttk.Label(wall_clock_frame, text=LIVE_CLOCK_LABEL).pack(side="left", padx=(0, 4))
        ttk.Label(
            wall_clock_frame,
            textvariable=self._live_clock_var,
            foreground="#374151",
        ).pack(side="left")
        self._wall_clock_frame = wall_clock_frame
        self._pending_label = ttk.Label(header, text="", foreground="#b45309")
        self._pending_label.pack(side="left", padx=(16, 4))

        status = ttk.Label(header, text="NT Disconnected", foreground="#b32323")
        status.pack(side="right", padx=6)
        self._status_label = status
        self._apply_wall_clock_visibility()

        body = ttk.Frame(self, padding=10)
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body)
        left.pack(side="left", fill="y")
        right = ttk.Frame(body)
        right.pack(side="right", fill="both", expand=True)

        actions_container = ttk.LabelFrame(left, text="Actions", padding=0)
        actions_container.pack(fill="y", expand=True)
        actions_canvas = tk.Canvas(actions_container, highlightthickness=0)
        actions_scroll = ttk.Scrollbar(
            actions_container, orient="vertical", command=actions_canvas.yview
        )
        actions_canvas.configure(yscrollcommand=actions_scroll.set)
        actions_canvas.pack(side="left", fill="y", expand=True)
        actions_scroll.pack(side="right", fill="y")

        action_panel = ttk.Frame(actions_canvas, padding=10)
        actions_canvas.create_window((0, 0), window=action_panel, anchor="nw")

        self._action_buttons: List[ttk.Button] = []
        self._action_buttons_by_command: Dict[str, ttk.Button] = {}
        self._reset_button: Optional[ttk.Button] = None
        self._actions_canvas = actions_canvas
        self._action_panel = action_panel
        self._render_action_buttons()

        def _on_actions_configure(_event=None) -> None:
            actions_canvas.configure(scrollregion=actions_canvas.bbox("all"))
            actions_canvas.configure(width=action_panel.winfo_reqwidth())

        action_panel.bind("<Configure>", _on_actions_configure)

        notebook = ttk.Notebook(right)
        notebook.pack(fill="both", expand=True)
        self._right_notebook = notebook
        output_panel = ttk.Frame(notebook)
        notebook.add(output_panel, text="Output")
        output_header = ttk.Frame(output_panel)
        output_header.pack(fill="x")
        ttk.Button(output_header, text="Clear Output", command=self._clear_output).pack(
            side="right"
        )
        self._output_scope_headline_var = tk.StringVar(value=TEST_SCOPE_PANEL_WAITING_HEADLINE)
        self._output_scope_detail_var = tk.StringVar(value=RUNNABLE_SCOPE_PANEL_WAITING_DETAIL)
        output_status_row = ttk.Frame(output_panel)
        output_status_row.pack(fill="x", pady=(0, 8))
        output_status_panel = tk.Frame(
            output_status_row,
            bg=TEST_SCOPE_PANEL_NEUTRAL_BG,
            highlightbackground=TEST_SCOPE_PANEL_BORDER,
            highlightthickness=1,
            bd=0,
            padx=TEST_SCOPE_PANEL_PAD_X,
            pady=TEST_SCOPE_PANEL_PAD_Y,
        )
        output_status_panel.pack(side="right", anchor="e", padx=8)
        self._output_scope_panel = output_status_panel
        self._output_scope_title_label = tk.Label(
            output_status_panel,
            text=RUNNABLE_SCOPE_PANEL_TITLE,
            bg=TEST_SCOPE_PANEL_NEUTRAL_BG,
            fg=TEST_SCOPE_PANEL_NEUTRAL_FG,
            anchor="w",
            font=TEST_SCOPE_PANEL_DETAIL_FONT,
        )
        self._output_scope_title_label.pack(anchor="w")
        self._output_scope_headline_label = tk.Label(
            output_status_panel,
            textvariable=self._output_scope_headline_var,
            bg=TEST_SCOPE_PANEL_NEUTRAL_BG,
            fg=TEST_SCOPE_PANEL_NEUTRAL_FG,
            anchor="w",
            justify="left",
            font=TEST_SCOPE_PANEL_HEADLINE_FONT,
        )
        self._output_scope_headline_label.pack(anchor="w", pady=(2, 0))
        self._output_scope_detail_label = tk.Label(
            output_status_panel,
            textvariable=self._output_scope_detail_var,
            bg=TEST_SCOPE_PANEL_NEUTRAL_BG,
            fg=TEST_SCOPE_PANEL_NEUTRAL_FG,
            anchor="w",
            justify="left",
            wraplength=TEST_SCOPE_PANEL_WRAP,
            font=TEST_SCOPE_PANEL_DETAIL_FONT,
        )
        self._output_scope_detail_label.pack(anchor="w", pady=(2, 0))
        output_body = ttk.Frame(output_panel)
        output_body.pack(fill="both", expand=True)
        self._output = tk.Text(output_body, height=10, wrap="word", state="disabled")
        self._output.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(output_body, command=self._output.yview)
        scroll.pack(side="right", fill="y")
        self._output.configure(yscrollcommand=scroll.set)

        live_panel = ttk.Frame(notebook)
        notebook.add(live_panel, text="Live Topology")
        self._build_live_panel(live_panel)

        visibility_panel = ttk.Frame(notebook)
        self._visibility_panel = visibility_panel
        self._build_visibility_panel(visibility_panel)
        evidence_panel = ttk.Frame(notebook)
        self._evidence_panel = evidence_panel
        notebook.add(evidence_panel, text=EVIDENCE_TAB_LABEL)
        self._build_evidence_panel(evidence_panel)
        tests_panel = ttk.Frame(notebook)
        self._tests_panel = tests_panel
        notebook.add(tests_panel, text=TEST_LIBRARY_TAB_LABEL)
        self._build_test_library_panel(tests_panel)
        notebook.bind("<<NotebookTabChanged>>", self._on_right_notebook_changed)
        self._apply_visibility_tab_pref()
        self._sync_test_selection_visibility()
        self._last_right_tab_text = self._current_right_tab_text()

    def _build_live_panel(self, parent: tk.Widget) -> None:
        """
        NAME
            _build_live_panel - Build the live topology overlay tab.
        """
        controls = ttk.Frame(parent, padding=(8, 8, 8, 4))
        controls.pack(fill="x")
        ttk.Checkbutton(
            controls,
            text="Enable Live Overlay",
            variable=self._live_enabled_var,
        ).pack(side="left")
        ttk.Checkbutton(
            controls,
            text="Show Groups",
            variable=self._live_groups_var,
            command=self._apply_live_group_toggle,
        ).pack(side="left", padx=(8, 0))
        ttk.Checkbutton(
            controls,
            text=VIS_MODE_LABEL,
            variable=self._visibility_enabled_var,
            command=self._apply_visibility_mode_toggle,
        ).pack(side=VIS_PACK_SIDE_LEFT, padx=VIS_PAD_LEFT)
        ttk.Label(controls, text="Source:").pack(side="left", padx=(12, 4))
        source_menu = ttk.OptionMenu(
            controls,
            self._live_source_var,
            LIVE_SOURCE_REST,
            LIVE_SOURCE_REST,
            LIVE_SOURCE_FILE,
        )
        source_menu.pack(side="left")
        ttk.Button(controls, text="Load File...", command=self._load_runtime_state_file).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(controls, text="Reload File", command=self._reload_runtime_state_file).pack(
            side="left", padx=(6, 0)
        )
        ttk.Label(controls, text="Rate (Hz):").pack(side="left", padx=(12, 4))
        rate_entry = ttk.Entry(controls, textvariable=self._live_rate_var, width=6)
        rate_entry.pack(side="left")
        ttk.Button(controls, text="Apply", command=self._apply_runtime_state_rate).pack(
            side="left", padx=(6, 0)
        )
        ttk.Label(controls, text=LIVE_CLOCK_LABEL).pack(side="left", padx=(12, 4))
        ttk.Label(controls, textvariable=self._live_clock_var).pack(side="left")
        ttk.Button(controls, text="Zoom -", command=self._zoom_out).pack(
            side="left", padx=(12, 0)
        )
        ttk.Button(controls, text="Zoom +", command=self._zoom_in).pack(
            side="left", padx=(4, 0)
        )
        ttk.Button(controls, text="Reset Zoom", command=self._zoom_reset).pack(
            side="left", padx=(4, 0)
        )
        ttk.Button(controls, text="Fit to Window", command=self._fit_live_view).pack(
            side="left", padx=(4, 0)
        )

        profile_name = self._profile_box.get() if hasattr(self, "_profile_box") else ""
        self._live_view = LiveTopologyView(
            parent,
            profile_name,
            on_node_right_click=self._on_live_node_right_click,
            on_group_right_click=self._on_live_group_right_click,
            on_active_group_member_toggled=self._on_active_group_member_toggled,
            on_override_action=self._on_live_override_action,
            on_left_click=self._on_live_view_left_click,
        )
        self._live_view.set_show_groups(self._live_groups_var.get())
        self._live_view.set_visibility_enabled(self._visibility_enabled_var.get())
        self._live_view.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _build_test_library_panel(self, parent: tk.Widget) -> None:
        """
        NAME
            _build_test_library_panel - Build the dedicated test-library authoring tab.
        """
        container = ttk.Frame(parent, padding=10)
        container.pack(fill="both", expand=True)
        ttk.Label(container, text=TEST_LIBRARY_TITLE).pack(anchor="w")
        toolbar = ttk.Frame(container)
        toolbar.pack(fill="x", pady=(8, 8))
        ttk.Button(
            toolbar,
            text=TEST_LIBRARY_BUTTON_REFRESH,
            command=self._refresh_test_library_view,
        ).pack(side="left")
        ttk.Button(
            toolbar,
            text=TEST_LIBRARY_BUTTON_NEW,
            command=self._create_new_test_from_ui,
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            toolbar,
            text=TEST_LIBRARY_BUTTON_RENAME,
            command=self._rename_selected_test_from_ui,
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            toolbar,
            text=TEST_LIBRARY_BUTTON_DELETE,
            command=self._delete_selected_test_from_ui,
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            toolbar,
            text=TEST_LIBRARY_BUTTON_IMPORT_GLOBAL,
            command=self._dsl_import_global_from_ui,
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            toolbar,
            text=TEST_LIBRARY_BUTTON_IMPORT_CONFIG,
            command=self._dsl_import_to_config_from_ui,
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            toolbar,
            text=TEST_LIBRARY_BUTTON_IMPORT_PROFILE,
            command=self._dsl_import_from_ui,
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            toolbar,
            text=TEST_LIBRARY_BUTTON_COPY_CONFIG,
            command=self._copy_selected_test_to_config_from_ui,
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            toolbar,
            text=TEST_LIBRARY_BUTTON_COPY_PROFILE,
            command=self._copy_selected_test_to_profile_from_ui,
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            toolbar,
            text=TEST_LIBRARY_BUTTON_VALIDATE,
            command=self._dsl_validate_from_ui,
        ).pack(side="left", padx=(8, 0))
        execution_toolbar = ttk.Frame(container)
        execution_toolbar.pack(fill="x", pady=(0, 8))
        for label, command in [
            (TEST_LIBRARY_BUTTON_STATE, "printState"),
            (TEST_LIBRARY_BUTTON_INFO, "printTestsInfo"),
            (TEST_LIBRARY_BUTTON_OVERVIEW, "printTestsOverview"),
            (TEST_LIBRARY_BUTTON_SOURCE, "printSelectedTestSource"),
            (TEST_LIBRARY_BUTTON_PRINT_NEXT, "printNextTest"),
            (TEST_LIBRARY_BUTTON_RUN_SELECTED, "runTest"),
            (TEST_LIBRARY_BUTTON_RUN_ALL, "runAllTests"),
            (TEST_LIBRARY_BUTTON_NEXT, "selectTestNext"),
            (TEST_LIBRARY_BUTTON_PREV, "selectTestPrev"),
            (TEST_LIBRARY_BUTTON_TOGGLE, "toggleEnabled"),
        ]:
            button = ttk.Button(
                execution_toolbar,
                text=label,
                command=(lambda c=command: self._on_action(c)),
            )
            button.pack(side="left", padx=(0, 8))
            if command == "runTest":
                self._tests_run_selected_button = button
        selection_toolbar = ttk.Frame(container)
        selection_toolbar.pack(fill="x", pady=(0, 8))
        selection_left = ttk.Frame(selection_toolbar)
        selection_left.pack(side="left", fill="x", expand=True)
        ttk.Label(selection_left, text=TEST_LIBRARY_SELECTION_LABEL).pack(
            side="left", padx=(0, 4)
        )
        current_test_label = ttk.Label(
            selection_left,
            textvariable=self._selected_test_var,
            foreground=TEST_LIBRARY_STATUS_COLOR,
            width=28,
            anchor="w",
        )
        current_test_label.pack(side="left")
        self._tests_tab_current_test_label = current_test_label
        ttk.Label(
            selection_left,
            textvariable=self._running_text_var,
            foreground=TEST_LIBRARY_STATUS_COLOR,
        ).pack(side="left", padx=(16, 4))
        self._last_result_label = ttk.Label(
            selection_left,
            textvariable=self._last_result_text_var,
            foreground=TEST_RESULT_NEUTRAL_FG,
        )
        self._last_result_label.pack(side="left", padx=(16, 4))
        self._selected_test_scope_headline_var = tk.StringVar(
            value=TEST_SCOPE_PANEL_NO_SELECTION_HEADLINE
        )
        self._selected_test_scope_status_var = tk.StringVar(
            value=TEST_LIBRARY_STATUS_NO_SELECTED_TEST
        )
        status_panel = tk.Frame(
            selection_toolbar,
            bg=TEST_SCOPE_PANEL_NEUTRAL_BG,
            highlightbackground=TEST_SCOPE_PANEL_BORDER,
            highlightthickness=1,
            bd=0,
            padx=TEST_SCOPE_PANEL_PAD_X,
            pady=TEST_SCOPE_PANEL_PAD_Y,
        )
        status_panel.pack(side="right", anchor="e")
        self._selected_test_scope_panel = status_panel
        self._selected_test_scope_title_label = tk.Label(
            status_panel,
            text=TEST_SCOPE_PANEL_TITLE,
            bg=TEST_SCOPE_PANEL_NEUTRAL_BG,
            fg=TEST_SCOPE_PANEL_NEUTRAL_FG,
            anchor="w",
            font=TEST_SCOPE_PANEL_DETAIL_FONT,
        )
        self._selected_test_scope_title_label.pack(anchor="w")
        self._selected_test_scope_headline_label = tk.Label(
            status_panel,
            textvariable=self._selected_test_scope_headline_var,
            bg=TEST_SCOPE_PANEL_NEUTRAL_BG,
            fg=TEST_SCOPE_PANEL_NEUTRAL_FG,
            anchor="w",
            justify="left",
            font=TEST_SCOPE_PANEL_HEADLINE_FONT,
        )
        self._selected_test_scope_headline_label.pack(anchor="w", pady=(2, 0))
        self._selected_test_scope_detail_label = tk.Label(
            status_panel,
            textvariable=self._selected_test_scope_status_var,
            bg=TEST_SCOPE_PANEL_NEUTRAL_BG,
            fg=TEST_SCOPE_PANEL_NEUTRAL_FG,
            anchor="w",
            justify="left",
            wraplength=TEST_SCOPE_PANEL_WRAP,
            font=TEST_SCOPE_PANEL_DETAIL_FONT,
        )
        self._selected_test_scope_detail_label.pack(anchor="w", pady=(2, 0))
        self._test_library_status_var = tk.StringVar(value=TEST_LIBRARY_STATUS_EMPTY)
        ttk.Label(
            container,
            textvariable=self._test_library_status_var,
            foreground=TEST_LIBRARY_STATUS_COLOR,
        ).pack(anchor="w", pady=(0, 8))
        ttk.Label(
            container,
            text=TEST_LIBRARY_NOTE_TEXT,
            foreground=TEST_LIBRARY_STATUS_COLOR,
            wraplength=900,
            justify="left",
        ).pack(anchor="w", pady=(0, 8))
        layout = ttk.Panedwindow(container, orient="vertical")
        layout.pack(fill="both", expand=True)
        library_area = ttk.Frame(layout)
        activity_area = ttk.Frame(layout)
        layout.add(library_area, weight=3)
        layout.add(activity_area, weight=1)
        self._tests_layout_pane = layout
        columns = ttk.Panedwindow(library_area, orient="horizontal")
        columns.pack(fill="both", expand=True)
        global_frame = ttk.LabelFrame(columns, text=TEST_LIBRARY_GLOBAL_TITLE, padding=8)
        config_frame = ttk.LabelFrame(columns, text=TEST_LIBRARY_CONFIG_TITLE, padding=8)
        profile_frame = ttk.LabelFrame(columns, text=TEST_LIBRARY_PROFILE_TITLE, padding=8)
        devices_frame = ttk.LabelFrame(columns, text=TEST_LIBRARY_DEVICES_TITLE, padding=8)
        active_group_frame = ttk.LabelFrame(columns, text=TEST_ACTIVE_GROUP_TITLE, padding=8)
        columns.add(global_frame, weight=1)
        columns.add(config_frame, weight=1)
        columns.add(profile_frame, weight=1)
        columns.add(devices_frame, weight=1)
        columns.add(active_group_frame, weight=1)

        global_body = ttk.Frame(global_frame)
        global_body.pack(fill="both", expand=True)
        global_list = tk.Listbox(
            global_body,
            exportselection=False,
            height=TEST_LIBRARY_LISTBOX_HEIGHT,
        )
        global_list.pack(side="left", fill="both", expand=True)
        global_scroll = ttk.Scrollbar(global_body, command=global_list.yview)
        global_scroll.pack(side="right", fill="y")
        global_list.configure(yscrollcommand=global_scroll.set)
        self._test_library_global_list = global_list
        global_list.bind("<<ListboxSelect>>", self._on_test_library_global_selected)

        config_body = ttk.Frame(config_frame)
        config_body.pack(fill="both", expand=True)
        config_list = tk.Listbox(
            config_body,
            exportselection=False,
            height=TEST_LIBRARY_LISTBOX_HEIGHT,
        )
        config_list.pack(side="left", fill="both", expand=True)
        config_scroll = ttk.Scrollbar(config_body, command=config_list.yview)
        config_scroll.pack(side="right", fill="y")
        config_list.configure(yscrollcommand=config_scroll.set)
        self._test_library_config_list = config_list
        config_list.bind("<<ListboxSelect>>", self._on_test_library_config_selected)

        profile_body = ttk.Frame(profile_frame)
        profile_body.pack(fill="both", expand=True)
        profile_list = tk.Listbox(
            profile_body,
            exportselection=False,
            height=TEST_LIBRARY_LISTBOX_HEIGHT,
        )
        profile_list.pack(side="left", fill="both", expand=True)
        profile_scroll = ttk.Scrollbar(profile_body, command=profile_list.yview)
        profile_scroll.pack(side="right", fill="y")
        profile_list.configure(yscrollcommand=profile_scroll.set)
        self._test_library_profile_list = profile_list
        profile_list.bind("<<ListboxSelect>>", self._on_test_library_profile_selected)

        devices_body = ttk.Frame(devices_frame)
        devices_body.pack(fill="both", expand=True)
        devices_table = ttk.Treeview(
            devices_body,
            columns=(
                TEST_LIBRARY_DEVICES_COL_LABEL,
                TEST_LIBRARY_DEVICES_COL_TYPE,
                TEST_LIBRARY_DEVICES_COL_ID,
            ),
            show="headings",
        )
        devices_table.heading(TEST_LIBRARY_DEVICES_COL_LABEL, text=TEST_LIBRARY_DEVICES_COL_LABEL)
        devices_table.heading(TEST_LIBRARY_DEVICES_COL_TYPE, text=TEST_LIBRARY_DEVICES_COL_TYPE)
        devices_table.heading(TEST_LIBRARY_DEVICES_COL_ID, text=TEST_LIBRARY_DEVICES_COL_ID)
        devices_table.column(TEST_LIBRARY_DEVICES_COL_LABEL, width=180, anchor="w")
        devices_table.column(TEST_LIBRARY_DEVICES_COL_TYPE, width=90, anchor="w")
        devices_table.column(TEST_LIBRARY_DEVICES_COL_ID, width=60, anchor="center")
        devices_table.pack(side="left", fill="both", expand=True)
        devices_scroll = ttk.Scrollbar(devices_body, command=devices_table.yview)
        devices_scroll.pack(side="right", fill="y")
        devices_table.configure(yscrollcommand=devices_scroll.set)
        self._test_library_devices_table = devices_table
        devices_table.bind("<Double-1>", self._on_test_library_device_double_click)
        active_group_body = ttk.Frame(active_group_frame)
        active_group_body.pack(fill="both", expand=True)
        active_group_list = tk.Listbox(
            active_group_body,
            exportselection=False,
            height=TEST_LIBRARY_LISTBOX_HEIGHT,
        )
        active_group_list.pack(side="left", fill="both", expand=True)
        active_group_scroll = ttk.Scrollbar(active_group_body, command=active_group_list.yview)
        active_group_scroll.pack(side="right", fill="y")
        active_group_list.configure(yscrollcommand=active_group_scroll.set)
        self._tests_active_group_list = active_group_list
        lower_notebook = ttk.Notebook(activity_area)
        lower_notebook.pack(fill="both", expand=True, pady=(8, 0))
        results_frame = ttk.Frame(lower_notebook, padding=8)
        lower_notebook.add(results_frame, text=TEST_ACTIVITY_TAB_LABEL)
        results_header = ttk.Frame(results_frame)
        results_header.pack(fill="x", pady=(0, 8))
        ttk.Button(
            results_header,
            text="Clear Output",
            command=self._clear_test_output,
        ).pack(side="right")
        results_body = ttk.Frame(results_frame)
        results_body.pack(fill="both", expand=True)
        self._test_output = tk.Text(
            results_body,
            height=TEST_LIBRARY_RESULTS_HEIGHT,
            wrap="word",
            state="disabled",
        )
        self._test_output.pack(side="left", fill="both", expand=True)
        results_scroll = ttk.Scrollbar(results_body, command=self._test_output.yview)
        results_scroll.pack(side="right", fill="y")
        self._test_output.configure(yscrollcommand=results_scroll.set)
        source_frame = ttk.Frame(lower_notebook, padding=8)
        lower_notebook.add(source_frame, text=TEST_SOURCE_TAB_LABEL)
        source_toolbar = ttk.Frame(source_frame)
        source_toolbar.pack(fill="x", pady=(0, 8))
        save_button = ttk.Button(
            source_toolbar,
            text=TEST_SOURCE_BUTTON_SAVE,
            command=self._save_selected_test_source,
        )
        save_button.pack(side="left")
        self._test_source_save_button = save_button
        revert_button = ttk.Button(
            source_toolbar,
            text=TEST_SOURCE_BUTTON_REVERT,
            command=self._reload_selected_test_source,
        )
        revert_button.pack(side="left", padx=(8, 0))
        self._test_source_revert_button = revert_button
        validate_button = ttk.Button(
            source_toolbar,
            text=TEST_SOURCE_BUTTON_VALIDATE,
            command=self._validate_selected_test_source,
        )
        validate_button.pack(side="left", padx=(8, 0))
        self._test_source_validate_button = validate_button
        reference_button = ttk.Button(
            source_toolbar,
            text=TEST_SOURCE_REFERENCE_TITLE,
            command=self._toggle_test_source_reference_window,
        )
        reference_button.pack(side="left", padx=(8, 0))
        self._test_source_status_var = tk.StringVar(value=TEST_SOURCE_STATUS_NONE)
        ttk.Label(
            source_frame,
            textvariable=self._test_source_status_var,
            foreground=TEST_LIBRARY_STATUS_COLOR,
        ).pack(anchor="w", pady=(0, 8))
        source_body = ttk.Frame(source_frame)
        source_body.pack(fill="both", expand=True)
        self._test_source_line_numbers = tk.Text(
            source_body,
            width=TEST_SOURCE_LINE_NUMBER_WIDTH,
            wrap="none",
            state="disabled",
            takefocus=0,
            background="#f3f4f6",
            foreground="#6b7280",
        )
        self._test_source_line_numbers.pack(side="left", fill="y")
        self._test_source_text = tk.Text(
            source_body,
            wrap="word",
            state="disabled",
            undo=True,
            maxundo=-1,
            autoseparators=True,
        )
        self._test_source_text.pack(side="left", fill="both", expand=True)
        source_scroll = ttk.Scrollbar(source_body, command=self._on_test_source_scrollbar)
        source_scroll.pack(side="right", fill="y")
        self._test_source_scrollbar = source_scroll
        self._test_source_text.configure(yscrollcommand=self._on_test_source_yscroll)
        self._test_source_text.bind("<<Modified>>", self._on_test_source_modified)
        self._test_source_text.bind("<KeyRelease>", self._on_test_source_key_release)
        self._test_source_text.bind("<MouseWheel>", self._on_test_source_mousewheel)
        self._test_source_text.bind("<ButtonRelease-1>", self._on_test_source_click_release)
        self._test_source_text.bind("<Configure>", self._on_test_source_configure)
        self._test_source_text.bind("<Control-z>", self._on_test_source_undo)
        self._test_source_text.bind("<Control-y>", self._on_test_source_redo)
        self._refresh_test_library_view()

    def _build_visibility_panel(self, parent: tk.Widget) -> None:
        """
        NAME
            _build_visibility_panel - Build the visibility matrix tab.
        """
        header = ttk.Frame(parent, padding=VIS_PAD_HEADER)
        header.pack(fill=VIS_FILL_X)
        ttk.Label(header, textvariable=self._visibility_summary_var).pack(
            side=VIS_PACK_SIDE_LEFT,
            anchor=VIS_TREE_ANCHOR_W,
        )
        ttk.Button(
            header,
            text=VIS_CLEAR_PANELS_BUTTON,
            command=self._clear_visibility_panels,
        ).pack(side=VIS_PACK_SIDE_RIGHT)

        body = ttk.Panedwindow(parent, orient="horizontal")
        body.pack(fill=VIS_FILL_BOTH, expand=True, padx=8, pady=8)

        topology_frame = ttk.Frame(body)
        body.add(topology_frame, weight=3)

        profile_name = self._profile_box.get() if hasattr(self, "_profile_box") else ""
        self._visibility_live_view = LiveTopologyView(
            topology_frame,
            profile_name,
            on_node_right_click=self._on_live_node_right_click,
            on_group_right_click=self._on_live_group_right_click,
            on_active_group_member_toggled=self._on_active_group_member_toggled,
            on_override_action=self._on_live_override_action,
            on_left_click=self._on_live_view_left_click,
        )
        self._visibility_live_view.set_show_groups(self._live_groups_var.get())
        self._visibility_live_view.set_visibility_enabled(True)
        self._visibility_live_view.pack(fill="both", expand=True)

        table_panel = ttk.Panedwindow(body, orient=VIS_TABLE_SPLIT_ORIENT)
        body.add(table_panel, weight=2)

        defined_frame = ttk.LabelFrame(table_panel, text=VIS_DEFINED_SECTION_LABEL, padding=VIS_PAD_TABLE)
        table_panel.add(defined_frame, weight=3)
        self._visibility_table = self._build_visibility_table_widget(defined_frame)
        self._visibility_table.bind("<<TreeviewSelect>>", self._on_visibility_row_selected)

        unrecognized_frame = ttk.LabelFrame(
            table_panel,
            text=VIS_UNRECOGNIZED_SECTION_LABEL,
            padding=VIS_PAD_TABLE,
        )
        table_panel.add(unrecognized_frame, weight=2)
        self._visibility_unrecognized_table = self._build_visibility_table_widget(unrecognized_frame)
        self._visibility_unrecognized_table.bind("<Double-1>", self._on_visibility_row_double_click)
        self._visibility_unrecognized_table.bind("<<TreeviewSelect>>", self._on_visibility_row_selected)

        ctre_raw_frame = ttk.LabelFrame(
            table_panel,
            text=VIS_CTRE_RAW_SECTION_LABEL,
            padding=VIS_PAD_TABLE,
        )
        table_panel.add(ctre_raw_frame, weight=2)
        self._visibility_ctre_raw_table = self._build_visibility_ctre_raw_table_widget(ctre_raw_frame)

        if self._visibility_provider is None:
            self._visibility_table.insert(VIS_TREE_ROOT, VIS_TREE_END, values=[VIS_EMPTY_MESSAGE])
        elif self._visibility_ctre_raw_table is not None:
            self._visibility_ctre_raw_table.insert(VIS_TREE_ROOT, VIS_TREE_END, values=[VIS_RAW_EMPTY_MESSAGE])

    def _build_visibility_table_widget(self, parent: tk.Widget) -> ttk.Treeview:
        """
        NAME
            _build_visibility_table_widget - Build one visibility table with shared columns and scrolling.
        """
        table = ttk.Treeview(
            parent,
            columns=(),
            show=VIS_TREE_SHOW,
        )
        table.pack(side=VIS_PACK_SIDE_LEFT, fill=VIS_FILL_BOTH, expand=True)
        scrollbar = ttk.Scrollbar(
            parent,
            orient=VIS_SCROLLBAR_ORIENT,
            command=table.yview,
        )
        scrollbar.pack(side=VIS_PACK_SIDE_RIGHT, fill=VIS_FILL_Y)
        table.configure(yscrollcommand=scrollbar.set)
        return table

    def _clear_visibility_panels(self) -> None:
        """
        NAME
            _clear_visibility_panels - Clear the three Visibility right-hand subpanels.
        """
        self._visibility_selected_label = NT_VALUE_EMPTY
        self._visibility_selected_unexpected = False
        self._visibility_row_meta = {}
        if self._visibility_table is not None:
            for row in self._visibility_table.get_children():
                self._visibility_table.delete(row)
            self._visibility_table.insert(VIS_TREE_ROOT, VIS_TREE_END, values=[VIS_EMPTY_MESSAGE])
        if self._visibility_unrecognized_table is not None:
            for row in self._visibility_unrecognized_table.get_children():
                self._visibility_unrecognized_table.delete(row)
            self._visibility_unrecognized_table.insert(
                VIS_TREE_ROOT,
                VIS_TREE_END,
                values=[VIS_EMPTY_MESSAGE],
            )
        self._populate_ctre_raw_table([])

    def _build_evidence_panel(self, parent: tk.Widget) -> None:
        """
        NAME
            _build_evidence_panel - Build the topology-first device evidence tab.
        """
        body = ttk.Panedwindow(parent, orient="vertical")
        body.pack(fill=VIS_FILL_BOTH, expand=True, padx=8, pady=8)

        top = ttk.Panedwindow(body, orient="horizontal")
        body.add(top, weight=EVIDENCE_LAYOUT_TOP_WEIGHT)

        topology_frame = ttk.Frame(top)
        top.add(topology_frame, weight=3)
        profile_name = self._profile_box.get() if hasattr(self, "_profile_box") else ""
        self._evidence_live_view = LiveTopologyView(
            topology_frame,
            profile_name,
            on_node_right_click=self._on_live_node_right_click,
            on_group_right_click=self._on_live_group_right_click,
            on_active_group_member_toggled=self._on_active_group_member_toggled,
            on_left_click=self._on_live_view_left_click,
            on_selection_changed=self._on_evidence_topology_selected,
            show_selection_panel=False,
            title_text=EVIDENCE_TITLE_TEXT,
        )
        self._evidence_live_view.set_show_groups(self._live_groups_var.get())
        self._evidence_live_view.set_visibility_enabled(False)
        self._evidence_live_view.pack(fill=VIS_FILL_BOTH, expand=True)

        inspector = ttk.Frame(top, padding=(8, 0, 0, 0))
        top.add(inspector, weight=2)
        self._build_evidence_inspector(inspector)

        table_frame = ttk.LabelFrame(body, text="Device Summary", padding=VIS_PAD_TABLE)
        body.add(table_frame, weight=EVIDENCE_LAYOUT_BOTTOM_WEIGHT)
        table_header = ttk.Frame(table_frame)
        table_header.pack(fill=VIS_FILL_X, pady=(0, 6))
        ttk.Label(table_header, textvariable=self._evidence_summary_var).pack(side=VIS_PACK_SIDE_LEFT)
        ttk.Label(table_header, text="Filter:").pack(side=VIS_PACK_SIDE_RIGHT, padx=(8, 4))
        filter_menu = ttk.OptionMenu(
            table_header,
            self._evidence_filter_var,
            EVIDENCE_FILTER_LABELS[EVIDENCE_FILTER_ALL],
            *[EVIDENCE_FILTER_LABELS[key] for key in EVIDENCE_FILTER_OPTIONS],
            command=lambda _value: self._refresh_evidence_view(),
        )
        filter_menu.pack(side=VIS_PACK_SIDE_RIGHT)
        self._evidence_table = ttk.Treeview(
            table_frame,
            columns=(
                EVIDENCE_COL_DEVICE,
                EVIDENCE_COL_PASSIVE,
                EVIDENCE_COL_CONSOLE,
                EVIDENCE_COL_PROBE,
                EVIDENCE_COL_PROBE_SCORE,
                EVIDENCE_COL_MANUAL,
                EVIDENCE_COL_EXISTENCE,
                EVIDENCE_COL_OPERABILITY,
                EVIDENCE_COL_IDENTITY,
                EVIDENCE_COL_CONFIDENCE,
            ),
            show=VIS_TREE_SHOW,
            height=EVIDENCE_SUMMARY_TABLE_HEIGHT,
        )
        self._evidence_table.pack(side=VIS_PACK_SIDE_LEFT, fill=VIS_FILL_BOTH, expand=True)
        evidence_scroll = ttk.Scrollbar(
            table_frame,
            orient=VIS_SCROLLBAR_ORIENT,
            command=self._evidence_table.yview,
        )
        evidence_scroll.pack(side=VIS_PACK_SIDE_RIGHT, fill=VIS_FILL_Y)
        self._evidence_table.configure(yscrollcommand=evidence_scroll.set)
        self._configure_evidence_table_columns(self._evidence_table)
        self._evidence_table.bind("<<TreeviewSelect>>", self._on_evidence_row_selected)

    def _build_evidence_inspector(self, parent: tk.Widget) -> None:
        """
        NAME
            _build_evidence_inspector - Build the selected-device evidence inspector.
        """
        ttk.Label(parent, text="Selected Device", font=("Trebuchet MS", 12)).pack(anchor=VIS_TREE_ANCHOR_W)
        ttk.Label(parent, textvariable=self._evidence_selected_title_var, font=("Segoe UI", 10, "bold")).pack(
            anchor=VIS_TREE_ANCHOR_W,
            pady=(2, 0),
        )
        self._evidence_detail_vars = {
            EVIDENCE_LABEL_EXISTENCE: tk.StringVar(value=EVIDENCE_STATUS_UNKNOWN),
            EVIDENCE_LABEL_OPERABILITY: tk.StringVar(value=EVIDENCE_STATUS_UNKNOWN),
            EVIDENCE_LABEL_IDENTITY: tk.StringVar(value=EVIDENCE_STATUS_UNKNOWN),
            EVIDENCE_LABEL_CONFIDENCE: tk.StringVar(value=EVIDENCE_CONFIDENCE_LOW),
        }
        interpretation = ttk.LabelFrame(parent, text=EVIDENCE_INTERPRETATION_TEXT, padding=8)
        interpretation.pack(fill=VIS_FILL_X, pady=(8, 8))
        for row_index, key in enumerate(
            (
                EVIDENCE_LABEL_EXISTENCE,
                EVIDENCE_LABEL_OPERABILITY,
                EVIDENCE_LABEL_IDENTITY,
                EVIDENCE_LABEL_CONFIDENCE,
            )
        ):
            ttk.Label(interpretation, text=f"{key}:").grid(row=row_index, column=0, sticky=VIS_TREE_ANCHOR_W, padx=(0, 6))
            ttk.Label(interpretation, textvariable=self._evidence_detail_vars[key]).grid(
                row=row_index,
                column=1,
                sticky=VIS_TREE_ANCHOR_W,
            )
        self._evidence_text_widgets = {}
        bus_health = ttk.LabelFrame(parent, text=EVIDENCE_BUS_HEALTH_TEXT, padding=6)
        bus_health.pack(fill=VIS_FILL_X, pady=(0, 8))
        self._evidence_text_widgets[EVIDENCE_BUS_HEALTH_TEXT] = tk.Text(
            bus_health,
            height=EVIDENCE_TEXT_HEIGHT_DEFAULT,
            wrap="word",
        )
        self._evidence_text_widgets[EVIDENCE_BUS_HEALTH_TEXT].pack(fill=VIS_FILL_BOTH, expand=True)
        self._evidence_text_widgets[EVIDENCE_BUS_HEALTH_TEXT].configure(state="disabled")
        sections = ttk.Panedwindow(parent, orient="vertical")
        sections.pack(fill=VIS_FILL_BOTH, expand=True)
        for title in (
            EVIDENCE_PRESENCE_TEXT,
            EVIDENCE_PASSIVE_TEXT,
            EVIDENCE_CONSOLE_TEXT,
            EVIDENCE_PROBE_TEXT,
            EVIDENCE_MANUAL_TEXT,
            EVIDENCE_NOTES_TEXT,
        ):
            frame = ttk.LabelFrame(sections, text=title, padding=6)
            section_weight = EVIDENCE_INSPECTOR_PANED_WEIGHT_DEFAULT
            if title == EVIDENCE_PROBE_TEXT:
                section_weight = EVIDENCE_INSPECTOR_PANED_WEIGHT_PROBE
            elif title == EVIDENCE_MANUAL_TEXT:
                section_weight = EVIDENCE_INSPECTOR_PANED_WEIGHT_MANUAL
            elif title == EVIDENCE_NOTES_TEXT:
                section_weight = EVIDENCE_INSPECTOR_PANED_WEIGHT_NOTES
            sections.add(frame, weight=section_weight)
            if title == EVIDENCE_MANUAL_TEXT:
                buttons = ttk.Frame(frame)
                buttons.pack(fill=VIS_FILL_X, pady=(0, 6))
                for outcome in (
                    EVIDENCE_MANUAL_OUTCOME_CORRECT,
                    EVIDENCE_MANUAL_OUTCOME_NO_RESPONSE,
                    EVIDENCE_MANUAL_OUTCOME_WRONG_DEVICE,
                    EVIDENCE_MANUAL_OUTCOME_WRONG_BRANCH,
                    EVIDENCE_MANUAL_OUTCOME_INTERMITTENT,
                    EVIDENCE_MANUAL_OUTCOME_DEGRADED,
                    EVIDENCE_MANUAL_OUTCOME_UNCERTAIN,
                ):
                    ttk.Button(
                        buttons,
                        text=EVIDENCE_MANUAL_OUTCOME_LABELS[outcome],
                        command=lambda selected=outcome: self._record_manual_evidence(selected),
                    ).pack(side=VIS_PACK_SIDE_LEFT, padx=(0, 4))
                ttk.Button(
                    buttons,
                    text="Clear",
                    command=self._clear_manual_evidence_for_selected,
                ).pack(side=VIS_PACK_SIDE_LEFT, padx=(8, 0))
            text_height = EVIDENCE_TEXT_HEIGHT_DEFAULT
            if title == EVIDENCE_PROBE_TEXT:
                text_height = EVIDENCE_TEXT_HEIGHT_PROBE
            elif title == EVIDENCE_MANUAL_TEXT:
                text_height = EVIDENCE_TEXT_HEIGHT_MANUAL
            elif title == EVIDENCE_NOTES_TEXT:
                text_height = EVIDENCE_TEXT_HEIGHT_NOTES
            text = tk.Text(frame, height=text_height, wrap="word")
            text.pack(fill=VIS_FILL_BOTH, expand=True)
            text.configure(state="disabled")
            self._evidence_text_widgets[title] = text

    def _configure_evidence_table_columns(self, table: ttk.Treeview) -> None:
        """
        NAME
            _configure_evidence_table_columns - Apply the Evidence summary table layout.
        """
        columns = [
            EVIDENCE_COL_DEVICE,
            EVIDENCE_COL_PASSIVE,
            EVIDENCE_COL_CONSOLE,
            EVIDENCE_COL_PROBE,
            EVIDENCE_COL_PROBE_SCORE,
            EVIDENCE_COL_MANUAL,
            EVIDENCE_COL_EXISTENCE,
            EVIDENCE_COL_OPERABILITY,
            EVIDENCE_COL_IDENTITY,
            EVIDENCE_COL_CONFIDENCE,
        ]
        table[VIS_TREE_COLUMNS] = columns
        for column in columns:
            anchor = VIS_TREE_ANCHOR_W if column == EVIDENCE_COL_DEVICE else VIS_TREE_ANCHOR_CENTER
            width = EVIDENCE_COL_DEVICE_WIDTH if column == EVIDENCE_COL_DEVICE else EVIDENCE_COL_SOURCE_WIDTH
            if column == EVIDENCE_COL_PROBE_SCORE:
                width = EVIDENCE_COL_PROBE_SCORE_WIDTH
            if column in (EVIDENCE_COL_EXISTENCE, EVIDENCE_COL_OPERABILITY, EVIDENCE_COL_IDENTITY, EVIDENCE_COL_CONFIDENCE):
                width = EVIDENCE_COL_RESULT_WIDTH
            table.heading(column, text=column, anchor=anchor)
            table.column(column, width=width, anchor=anchor, stretch=(column == EVIDENCE_COL_DEVICE))

    def _current_right_tab_text(self) -> str:
        """
        NAME
            _current_right_tab_text - Return the visible label of the active right-side notebook tab.
        """
        notebook = self.__dict__.get("_right_notebook")
        if notebook is None:
            return NT_VALUE_EMPTY
        try:
            current = notebook.select()
            if not current:
                return NT_VALUE_EMPTY
            return str(notebook.tab(current, "text")).strip()
        except Exception:
            return NT_VALUE_EMPTY

    def _evidence_tab_active(self) -> bool:
        """
        NAME
            _evidence_tab_active - Return whether the Evidence tab is currently selected.
        """
        return self._current_right_tab_text() == EVIDENCE_TAB_LABEL

    def _scope_context_kind(self) -> str:
        """
        NAME
            _scope_context_kind - Return the shared top-bar scope context for the active tab.
        """
        if self._current_right_tab_text() == TEST_LIBRARY_TAB_LABEL:
            return GROUP_SOURCE_SELECTED_TEST
        return GROUP_SOURCE_MANUAL

    def _refresh_scope_context_label(self) -> None:
        """
        NAME
            _refresh_scope_context_label - Refresh the top-bar scope context label.
        """
        label_var = self.__dict__.get("_scope_context_var")
        if label_var is None:
            return
        if self._scope_context_kind() == GROUP_SOURCE_SELECTED_TEST:
            label_var.set(GROUP_SOURCE_LABEL_SELECTED_TEST)
            return
        label_var.set(GROUP_SOURCE_LABEL_MANUAL)

    def _on_right_notebook_changed(self, _event: tk.Event) -> None:
        """
        NAME
            _on_right_notebook_changed - React to right-side tab changes.
        """
        previous_tab = self._last_right_tab_text
        current_tab = self._current_right_tab_text()
        if {previous_tab, current_tab} == {TEST_LIBRARY_TAB_LABEL, "Live Topology"} or (
            previous_tab == TEST_LIBRARY_TAB_LABEL and current_tab != TEST_LIBRARY_TAB_LABEL
        ) or (
            previous_tab != TEST_LIBRARY_TAB_LABEL and current_tab == TEST_LIBRARY_TAB_LABEL
        ):
            self._handle_tests_boundary_transition(previous_tab, current_tab)
        self._last_right_tab_text = current_tab
        self._sync_test_selection_visibility()
        self._refresh_scope_context_label()
        self._refresh_selected_test_scope_status()
        if self._evidence_tab_active():
            self._refresh_evidence_view()

    def _sync_test_selection_visibility(self) -> None:
        """
        NAME
            _sync_test_selection_visibility - Show selected-test controls in the active context only.
        """
        frame = getattr(self, "_test_header_frame", None)
        if frame is None:
            return
        if frame.winfo_manager():
            frame.pack_forget()

    def _apply_selected_test_name_from_ui(self, name: str) -> None:
        """
        NAME
            _apply_selected_test_name_from_ui - Make one UI-selected test authoritative for editor, activation, and run actions.
        """
        selected_name = str(name or "").strip()
        if not selected_name or selected_name == PROFILE_NONE:
            return
        self._selected_test_var.set(selected_name)
        tests_tab_active = self._current_right_tab_text() == TEST_LIBRARY_TAB_LABEL
        if not tests_tab_active:
            self._refresh_selected_test_scope_status()
            return
        if not self._tcp_connected:
            self._refresh_selected_test_scope_status()
            return
        if self._tracker.is_pending():
            self._refresh_selected_test_scope_status()
            return
        if selected_name == self._last_selected_test:
            self._refresh_selected_test_scope_status()
            return
        self._last_selected_test = selected_name
        ts = timestamp_hms()
        self._append_output(f'{ts} CMD selectTestByName "{selected_name}"')
        self._append_test_output(f'{ts} CMD selectTestByName "{selected_name}"')
        self._last_cmd = ("selectTestByName", {"name": selected_name})
        if not self._send_and_wait("selectTestByName", {"name": selected_name}):
            return
        previous_key = self._tests_active_group_membership_key
        self._load_selected_test_into_active_group(force_replace=False)
        if self._tests_active_group_membership_key == previous_key:
            self._refresh_selected_test_scope_status()

    def _handle_tests_boundary_transition(self, previous_tab: str, current_tab: str) -> None:
        """
        NAME
            _handle_tests_boundary_transition - Apply V2 deactivate/clear/restore behavior when crossing Tests and non-Tests.
        """
        previous_is_tests = previous_tab == TEST_LIBRARY_TAB_LABEL
        current_is_tests = current_tab == TEST_LIBRARY_TAB_LABEL
        if previous_is_tests == current_is_tests:
            return
        if not self._tcp_connected:
            return
        if self._tracker.is_pending():
            self._pending_tests_boundary_transition = (previous_tab, current_tab)
            return
        self._pending_tests_boundary_transition = None
        if previous_is_tests:
            self._deactivate_group_blocking()
            self._restore_manual_active_group_members()
            self._group_owner_mode = GROUP_SOURCE_MANUAL
            return
        self._remembered_manual_active_group_members = self._runtime_active_group_members()
        self._deactivate_group_blocking()
        self._load_selected_test_into_active_group(force_replace=True)
        self._group_owner_mode = GROUP_SOURCE_SELECTED_TEST

    def _runtime_active_group_payload(self) -> Dict[str, Any]:
        """
        NAME
            _runtime_active_group_payload - Return the latest runtime active-group payload when present.
        """
        groups = self._latest_runtime_state_payload_groups()
        for group in groups:
            if str(group.get("name", "")).strip().lower() == GROUP_ACTIVE_NAME:
                return dict(group)
        return {}

    def _latest_runtime_state_payload_groups(self) -> List[Dict[str, Any]]:
        """
        NAME
            _latest_runtime_state_payload_groups - Return the latest runtime-state groups list.
        """
        payload = self.__dict__.get("_latest_runtime_state_payload", {})
        groups = payload.get("groups") if isinstance(payload, dict) else None
        return list(groups) if isinstance(groups, list) else []

    def _runtime_active_group_members(self) -> List[Dict[str, Any]]:
        """
        NAME
            _runtime_active_group_members - Return ordered active-group member rows from runtime state.
        """
        member_map = group_member_map(self._runtime_active_group_payload(), enabled_only=False)
        rows: List[Dict[str, Any]] = []
        for key, member in member_map.items():
            label = str(member.get(GROUP_MEMBER_KEY_LABEL, "")).strip()
            if not label:
                label = key
            rows.append({"label": label, "enabled": bool(member.get(KEY_ENABLED, True))})
        return rows

    def _manual_active_group_is_empty(self) -> bool:
        """
        NAME
            _manual_active_group_is_empty - Return whether runtime currently shows no active-group members in manual mode.
        """
        if self.__dict__.get("_group_owner_mode", GROUP_SOURCE_MANUAL) != GROUP_SOURCE_MANUAL:
            return False
        if self.__dict__.get("_controlled_lifecycle_active_known") is True:
            return False
        return not bool(self._runtime_active_group_members())

    def _send_and_wait(self, command: str, args: Dict[str, Any]) -> bool:
        """
        NAME
            _send_and_wait - Send one tracked command and block briefly until its OUT event arrives.
        """
        seq = send_tracked_command(
            self._session,
            self._tracker,
            command,
            args,
            sender=lambda session, command_name, command_args: send_command(session, command_name, command_args),
            now=time.time(),
        )
        if seq is None:
            return False
        self._last_sent_seq = seq
        deadline = time.time() + 2.0
        while time.time() < deadline:
            events = self._session.poll_events()
            if not events:
                self.update_idletasks()
                time.sleep(0.02)
                continue
            for event in events:
                self._handle_tcp_response(event)
                if int(event.seq) == int(seq) and event.type == "out":
                    return True
        self._tracker.clear_pending()
        self._append_output("TIMEOUT waiting for ACK/OUT.")
        return False

    def _deactivate_group_blocking(self) -> bool:
        """
        NAME
            _deactivate_group_blocking - Deactivate the currently active group and treat inactive as a harmless no-op.
        """
        ts = timestamp_hms()
        self._append_output(f"{ts} {OUTPUT_LIFECYCLE_DEACTIVATE_ACTIVE}")
        self._last_cmd = ("lifecycleDeactivateActive", {})
        ok = self._send_and_wait("lifecycleDeactivateActive", {})
        if not ok:
            return False
        return True

    def _replace_active_group_members(self, members: List[Dict[str, Any]]) -> bool:
        """
        NAME
            _replace_active_group_members - Replace robot active-group membership with one ordered row list.
        """
        payload = [{"label": str(member.get("label", "")).strip(), "enabled": bool(member.get("enabled", True))}
                   for member in members if str(member.get("label", "")).strip()]
        ts = timestamp_hms()
        self._append_output(
            f"{ts} {OUTPUT_GROUP_REPLACE_FMT.format(group=GROUP_ACTIVE_NAME, count=len(payload))}"
        )
        self._last_cmd = ("groupReplaceMembers", {"group": GROUP_ACTIVE_NAME, "members": payload})
        return self._send_and_wait(
            "groupReplaceMembers",
            {"group": GROUP_ACTIVE_NAME, "members": payload},
        )

    def _selected_test_required_rows(self) -> List[Dict[str, Any]]:
        """
        NAME
            _selected_test_required_rows - Build ordered Tests-tab active-group rows from the selected local DSL declaration.
        """
        selected_name = str(self._selected_test_var.get() or "").strip()
        required_devices = self._selected_test_declared_required_devices(selected_name)
        test_profile_devices = self.__dict__.get("_test_profile_devices", {})
        profile_devices = self.__dict__.get("_profile_devices", {})
        rows: List[Dict[str, Any]] = []
        for label in required_devices:
            clean_label = str(label).strip()
            if not clean_label:
                continue
            key = clean_label.lower()
            known_to_tests = isinstance(test_profile_devices, dict) and key in test_profile_devices
            known_to_profile = isinstance(profile_devices, dict) and key in profile_devices
            invalid = not (known_to_tests or known_to_profile)
            rows.append(
                {
                    "label": clean_label,
                    "enabled": True,
                    "locked": key in TEST_ACTIVE_GROUP_SINGLETON_LABELS or clean_label in ("lmtSw0",),
                    "invalid": invalid,
                    "reason": "missing resource/device - " + clean_label if invalid else "",
                }
            )
        return rows

    def _selected_test_declared_required_devices(self, selected_name: str) -> List[str]:
        """
        NAME
            _selected_test_declared_required_devices - Return declared device labels for the selected local DSL test.
        """
        clean_name = str(selected_name or "").strip()
        if not clean_name or clean_name == PROFILE_NONE:
            return []
        try:
            payload = LocalConfigQueryService().load_canonical_payload()
            store = robot_test_dsl_store_from_root_payload(payload)
        except Exception:
            return []
        tests_by_name = getattr(store, "tests_by_name", {})
        entry = tests_by_name.get(clean_name) if isinstance(tests_by_name, dict) else None
        normalized = getattr(entry, "normalized", None)
        if normalized is None and clean_name in list_external_library_test_names():
            try:
                normalized = compile_source(clean_name, read_external_library_test_source(clean_name))
            except Exception:
                normalized = None
        devices = getattr(normalized, "devices", None)
        required_devices: List[str] = []
        if isinstance(devices, list):
            for device_ref in devices:
                label = str(getattr(device_ref, "name", "") or "").strip()
                if label:
                    required_devices.append(label)
        return required_devices

    def _runtime_device_for_label(self, label: object) -> Dict[str, Any]:
        """
        NAME
            _runtime_device_for_label - Return the latest runtime device payload for one label.
        """
        clean_label = str(label or NT_VALUE_EMPTY).strip().lower()
        latest_runtime_devices = self.__dict__.get("_latest_runtime_devices", {})
        if not clean_label or not isinstance(latest_runtime_devices, dict):
            return {}
        device = latest_runtime_devices.get(clean_label, {})
        return dict(device) if isinstance(device, dict) else {}

    def _tests_active_group_membership_key_for_rows(
        self,
        rows: List[Dict[str, Any]],
    ) -> Tuple[str, ...]:
        """
        NAME
            _tests_active_group_membership_key_for_rows - Normalize one Tests-tab group row list for change detection.
        """
        return tuple(str(row.get("label", "")).strip().lower() for row in rows if str(row.get("label", "")).strip())

    def _load_selected_test_into_active_group(self, force_replace: bool = False) -> None:
        """
        NAME
            _load_selected_test_into_active_group - Rebuild active-group from the selected DSL test while in Tests.
        """
        rows = self._selected_test_required_rows()
        membership_key = self._tests_active_group_membership_key_for_rows(rows)
        changed = membership_key != self._tests_active_group_membership_key
        if not force_replace and not changed:
            self._tests_active_group_rows = rows
            self._refresh_tests_active_group_panel()
            return
        self._tests_active_group_rows = rows
        self._tests_active_group_membership_key = membership_key
        if changed and self._active_group_is_currently_active():
            self._deactivate_group_blocking()
        valid_members = [
            {"label": row["label"], "enabled": True}
            for row in rows
            if not bool(row.get("invalid"))
        ]
        if self._tcp_connected and not self._tracker.is_pending():
            self._replace_active_group_members(valid_members)
            self.after_idle(self._request_runtime_state_refresh)
        self._set_runtime_event_notice(TEST_LIBRARY_STATUS_LOADED_NOT_ACTIVATED, "info")
        self._refresh_tests_active_group_panel()

    def _restore_manual_active_group_members(self) -> None:
        """
        NAME
            _restore_manual_active_group_members - Restore the remembered manual active-group membership after leaving Tests.
        """
        members = list(self.__dict__.get("_remembered_manual_active_group_members", []))
        if self._tcp_connected and not self._tracker.is_pending():
            self._replace_active_group_members(members)
            self.after_idle(self._request_runtime_state_refresh)
        self._set_runtime_event_notice(TEST_LIBRARY_STATUS_MANUAL_RESTORED, "info")
        self._refresh_selected_test_scope_status()

    def _active_group_is_currently_active(self) -> bool:
        """
        NAME
            _active_group_is_currently_active - Return whether runtime currently shows an active controlled session for active-group.
        """
        if self.__dict__.get("_controlled_lifecycle_active_known") is not True:
            return False
        latest_runtime_devices = self.__dict__.get("_latest_runtime_devices", {})
        if not isinstance(latest_runtime_devices, dict):
            return False
        for device in latest_runtime_devices.values():
            if not isinstance(device, dict):
                continue
            if str(device.get("activeGroupLabel", "")).strip().lower() == GROUP_ACTIVE_NAME:
                return True
        return False

    def _scope_is_currently_active(self) -> bool:
        """
        NAME
            _scope_is_currently_active - Return whether the current top-bar owner scope is active.

        DESCRIPTION
            Manual mode is active only when runtime shows an active-group-owned
            controlled session. Selected-test mode is active when the robot
            reports any controlled lifecycle session active for the selected-test
            owner flow.
        """
        if self._scope_context_kind() == GROUP_SOURCE_SELECTED_TEST:
            return self.__dict__.get("_controlled_lifecycle_active_known") is True
        return self._active_group_is_currently_active()

    def _scope_activation_notice_text(self) -> str:
        """
        NAME
            _scope_activation_notice_text - Return the next-step activation message for the current scope.

        DESCRIPTION
            The UI already knows whether the robot is disabled or not in teleop.
            When those blockers are not present, the message should only talk
            about the missing activation step instead of redundantly mentioning
            teleop again.
        """
        owner_mode = self.__dict__.get("_group_owner_mode", GROUP_SOURCE_MANUAL)
        mode = str(self.__dict__.get("_robot_mode_known", "") or "").strip().lower()
        if mode and mode != "teleop":
            if owner_mode == GROUP_SOURCE_SELECTED_TEST:
                return RUNNABLE_SCOPE_DETAIL_SELECTED_TEST_NOT_TELEOP
            return RUNNABLE_SCOPE_DETAIL_MANUAL_NOT_TELEOP
        if owner_mode == GROUP_SOURCE_SELECTED_TEST:
            return RUNNABLE_SCOPE_DETAIL_SELECTED_TEST_NOT_ACTIVATED
        return RUNNABLE_SCOPE_DETAIL_MANUAL_NOT_ACTIVATED

    def _build_visibility_ctre_raw_table_widget(self, parent: tk.Widget) -> ttk.Treeview:
        """
        NAME
            _build_visibility_ctre_raw_table_widget - Build the CTRE raw decode table and scrollbar.
        """
        table = ttk.Treeview(
            parent,
            columns=(
                VIS_RAW_COL_ARB,
                VIS_RAW_COL_PACKETS,
                VIS_RAW_COL_RATE,
                VIS_RAW_COL_API_CLASS,
                VIS_RAW_COL_API_INDEX,
                VIS_RAW_COL_PRIORITY,
                VIS_RAW_COL_RESERVED,
                VIS_RAW_COL_DATA_PAGE,
                VIS_RAW_COL_PF,
                VIS_RAW_COL_PS,
                VIS_RAW_COL_SA,
                VIS_RAW_COL_PGN,
            ),
            show=VIS_TREE_SHOW,
        )
        table.pack(side=VIS_PACK_SIDE_LEFT, fill=VIS_FILL_BOTH, expand=True)
        scrollbar = ttk.Scrollbar(
            parent,
            orient=VIS_SCROLLBAR_ORIENT,
            command=table.yview,
        )
        scrollbar.pack(side=VIS_PACK_SIDE_RIGHT, fill=VIS_FILL_Y)
        table.configure(yscrollcommand=scrollbar.set)
        table.heading(VIS_RAW_COL_ARB, text=VIS_RAW_COL_ARB, anchor=VIS_TREE_ANCHOR_CENTER)
        table.column(VIS_RAW_COL_ARB, width=VIS_RAW_COL_ARB_WIDTH, anchor=VIS_TREE_ANCHOR_CENTER, stretch=False)
        table.heading(VIS_RAW_COL_PACKETS, text=VIS_RAW_COL_PACKETS, anchor=VIS_TREE_ANCHOR_CENTER)
        table.column(VIS_RAW_COL_PACKETS, width=VIS_RAW_COL_PACKETS_WIDTH, anchor=VIS_TREE_ANCHOR_CENTER, stretch=False)
        table.heading(VIS_RAW_COL_RATE, text=VIS_RAW_COL_RATE, anchor=VIS_TREE_ANCHOR_CENTER)
        table.column(VIS_RAW_COL_RATE, width=VIS_RAW_COL_RATE_WIDTH, anchor=VIS_TREE_ANCHOR_CENTER, stretch=False)
        for col in (VIS_RAW_COL_API_CLASS, VIS_RAW_COL_API_INDEX):
            table.heading(col, text=col, anchor=VIS_TREE_ANCHOR_CENTER)
            table.column(col, width=VIS_RAW_COL_API_WIDTH, anchor=VIS_TREE_ANCHOR_CENTER, stretch=False)
        for col in (VIS_RAW_COL_PRIORITY, VIS_RAW_COL_RESERVED, VIS_RAW_COL_DATA_PAGE, VIS_RAW_COL_PF, VIS_RAW_COL_PS, VIS_RAW_COL_SA):
            table.heading(col, text=col, anchor=VIS_TREE_ANCHOR_CENTER)
            table.column(col, width=VIS_RAW_COL_SMALL_WIDTH, anchor=VIS_TREE_ANCHOR_CENTER, stretch=False)
        table.heading(VIS_RAW_COL_PGN, text=VIS_RAW_COL_PGN, anchor=VIS_TREE_ANCHOR_CENTER)
        table.column(VIS_RAW_COL_PGN, width=VIS_RAW_COL_PGN_WIDTH, anchor=VIS_TREE_ANCHOR_CENTER, stretch=False)
        return table

    def _on_profile_selected(self, _event=None) -> None:
        """
        NAME
            _on_profile_selected - Update live topology view when profile changes.
        """
        name = self._selected_profile_name()
        self._apply_profile_selection(name, reload_views=True)
        if name == self._last_selected_profile:
            return
        self._last_selected_profile = name
        if name == PROFILE_NONE:
            return
        if not self._tcp_connected or not self._handshake_done:
            return
        if self._tracker.is_pending():
            return
        seq = send_command(self._session, "selectProfile", {"name": name})
        if seq is not None:
            self._last_sent_seq = seq
            self._tracker.start("selectProfile", {"name": name}, seq, now=time.time())

    def _selected_profile_name(self) -> str:
        """
        NAME
            _selected_profile_name - Return the current UI-selected profile or PROFILE_NONE.
        """
        if not hasattr(self, "_profile_box"):
            return PROFILE_NONE
        return _normalize_profile_name(self._profile_box.get())

    def _diagnostic_profile_context_name(self) -> str:
        """
        NAME
            _diagnostic_profile_context_name - Return the profile context used by diagnostics views.

        DESCRIPTION
            Prefers the robot's active runtime profile, then the robot's selected
            profile, then the local UI selection.
        """
        active_name = _normalize_profile_name(self._robot_active_runtime_profile)
        if active_name != PROFILE_NONE:
            return active_name
        robot_selected = _normalize_profile_name(self._robot_selected_profile)
        if robot_selected != PROFILE_NONE:
            return robot_selected
        return self._selected_profile_name()

    def _sync_diagnostic_profile_context(self, reload_views: bool) -> None:
        """
        NAME
            _sync_diagnostic_profile_context - Re-anchor diagnostics surfaces to one profile context.
        """
        name = self._diagnostic_profile_context_name()
        self._refresh_profile_devices(name)
        if reload_views and name != self._last_profile_context:
            for live_view in self._iter_live_views():
                live_view.reload_profile(name)
        self._last_profile_context = name
        self.after_idle(self._refresh_evidence_view)

    def _apply_host_profile_context_only(self, profile_name: object, reload_views: bool) -> None:
        """
        NAME
            _apply_host_profile_context_only - Switch local UI profile context without sending robot commands.
        """
        name = _normalize_profile_name(profile_name)
        if name == PROFILE_NONE or not hasattr(self, "_profile_box"):
            return
        self._profile_box.set(name)
        self._last_selected_profile = name
        self._apply_profile_selection(name, reload_views=reload_views)

    def _maybe_prompt_host_profile_context_sync(self) -> None:
        """
        NAME
            _maybe_prompt_host_profile_context_sync - Offer to align local UI context to the robot-selected profile.
        """
        if not hasattr(self, "_profile_box"):
            return
        available_profiles = tuple(str(value) for value in self._profile_box.cget("values"))
        decision = decide_host_profile_sync(
            self._selected_profile_name(),
            self._robot_selected_profile,
            available_profiles,
        )
        robot_selected = decision.robot_profile or PROFILE_NONE
        local_selected = decision.host_profile or PROFILE_NONE
        if decision.action not in (SYNC_ACTION_ADOPT, SYNC_ACTION_MISSING_LOCAL, SYNC_ACTION_PROMPT):
            self._last_profile_mismatch_prompt = None
            return
        mismatch_key = (local_selected, robot_selected)
        if self._last_profile_mismatch_prompt == mismatch_key:
            return
        if decision.action == SYNC_ACTION_MISSING_LOCAL:
            self._last_profile_mismatch_prompt = mismatch_key
            return
        if decision.action == SYNC_ACTION_ADOPT:
            self._last_profile_mismatch_prompt = mismatch_key
            self._apply_host_profile_context_only(robot_selected, reload_views=True)
            return
        self._last_profile_mismatch_prompt = mismatch_key
        if messagebox.askyesno(
            "Profile Context Mismatch",
            (
                f"Robot selected profile is '{robot_selected}', but the UI is using "
                f"'{local_selected}'.\n\nSwitch the UI to the robot profile?"
            ),
            parent=self,
            default=messagebox.YES,
        ):
            self._apply_host_profile_context_only(robot_selected, reload_views=True)

    def _apply_profile_selection(self, profile_name: object, reload_views: bool) -> None:
        """
        NAME
            _apply_profile_selection - Apply profile-selection side effects inside the UI.

        DESCRIPTION
            Centralizes all local UI updates that depend on the selected profile:
            profile-device mapping, tests dropdown contents, and live-topology reloads.
            This keeps PROFILE_NONE handling in one place instead of repeating it
            across startup, refresh, and selection callbacks.
        """
        name = _normalize_profile_name(profile_name)
        self._refresh_tests_for_profile(name)
        self._refresh_test_library_view(name)
        self._sync_diagnostic_profile_context(reload_views=reload_views)

    def _refresh_profile_devices(self, profile_name: object) -> None:
        """
        NAME
            _refresh_profile_devices - Refresh label->device mapping for the profile.
        """
        name = _normalize_profile_name(profile_name)
        if name == PROFILE_NONE:
            self._profile_devices = {}
            if self._visibility_provider is not None:
                self._visibility_provider.set_expected_devices([])
            return
        try:
            devices, _expected = get_profile(name)
        except Exception:
            self._profile_devices = {}
            if self._visibility_provider is not None:
                self._visibility_provider.set_expected_devices([])
            return
        mapping: Dict[str, Dict[str, Any]] = {}
        for device in devices:
            if not isinstance(device, dict):
                continue
            label = str(device.get(DEVICE_KEY_LABEL, NT_VALUE_EMPTY)).strip()
            if not label:
                continue
            mapping[label.lower()] = device
        self._profile_devices = mapping
        if self._visibility_provider is not None:
            self._visibility_provider.set_expected_devices(
                _build_visibility_expected_devices(devices)
            )
            self._visibility_last_update = 0.0

    def _refresh_test_library_available_devices(self) -> None:
        """
        NAME
            _refresh_test_library_available_devices - Refresh the Tests-tab available-device list from the selected profile.
        """
        table = getattr(self, "_test_library_devices_table", None)
        if table is None:
            return
        for item in table.get_children():
            table.delete(item)
        rows: List[Tuple[str, str, str]] = []
        for device in sorted(
            self._test_profile_devices.values(),
            key=lambda entry: str(entry.get(PROFILE_KEY_LABEL, "") or "").lower(),
        ):
            label = str(device.get(PROFILE_KEY_LABEL, NT_VALUE_EMPTY)).strip()
            if not label:
                continue
            device_type = self._profile_device_type_display(device)
            device_id = str(device.get(KEY_ID, NT_VALUE_EMPTY)).strip()
            rows.append((label, device_type, device_id))
        if not rows:
            rows.append((TEST_LIBRARY_DEVICES_EMPTY, "", ""))
        for row in rows:
            table.insert("", "end", values=row)

    def _profile_device_type_display(self, device: Dict[str, Any]) -> str:
        """
        NAME
            _profile_device_type_display - Resolve one Available Devices type label with both readable and numeric forms when useful.
        """
        if not isinstance(device, dict):
            return NT_VALUE_EMPTY
        raw_value = str(device.get(KEY_DEVICE_TYPE, NT_VALUE_EMPTY) or "").strip()
        type_name = str(device.get(KEY_TYPE, NT_VALUE_EMPTY) or "").strip()
        if not type_name:
            try:
                type_name = str(_resolve_device_type_label(device, None) or "").strip()
            except Exception:
                type_name = NT_VALUE_EMPTY
        if type_name and raw_value and type_name != raw_value and type_name.lower() != "unknown":
            return f"{type_name} ({raw_value})"
        if type_name and type_name.lower() != "unknown":
            return type_name
        return raw_value

    def _selected_test_library_available_device_label(self) -> str:
        """
        NAME
            _selected_test_library_available_device_label - Return the selected available-device label from the Tests tab.
        """
        table = getattr(self, "_test_library_devices_table", None)
        if table is None:
            return ""
        selection = table.selection()
        if not selection:
            return ""
        values = table.item(selection[0], "values")
        if not values:
            return ""
        label = str(values[0] or "").strip()
        if not label or label == TEST_LIBRARY_DEVICES_EMPTY:
            return ""
        return label

    def _on_test_library_device_double_click(self, _event=None) -> None:
        """
        NAME
            _on_test_library_device_double_click - Insert the selected available-device label at the source-editor cursor.
        """
        label = self._selected_test_library_available_device_label()
        if not label:
            return
        widget = getattr(self, "_test_source_text", None)
        if widget is None or str(widget.cget("state")) == "disabled":
            return
        insert_text = label
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", label):
            insert_text = f'"{label}"'
        widget.insert("insert", insert_text)
        widget.focus_set()
        self._refresh_test_source_line_numbers()

    def _iter_live_views(self) -> List[LiveTopologyView]:
        """
            NAME
            _iter_live_views - Return all instantiated topology views.
        """
        views: List[LiveTopologyView] = []
        if self._live_view is not None:
            views.append(self._live_view)
        if self._visibility_live_view is not None:
            views.append(self._visibility_live_view)
        if self._evidence_live_view is not None:
            views.append(self._evidence_live_view)
        return views

    def _reset_ui_session_runtime_context(self) -> None:
        """
        NAME
            _reset_ui_session_runtime_context - Drop session-scoped runtime/UI caches after session generation changes.
        """
        self._runtime_state_seen = False
        self._runtime_state_pending_seq = None
        self._runtime_state_pending_at = 0.0
        self._runtime_active_known = None
        self._controlled_lifecycle_active_known = None
        self._robot_enabled_known = False
        self._robot_estopped_known = False
        self._robot_mode_known = "disabled"
        self._state_stale = False
        self._runtime_state_backoff = 1.0
        self._runtime_state_idle_count = 0
        self._runtime_state_pause_until = None
        self._log_poll_inflight = False
        self._log_poll_seq = None
        self._last_cmd = None
        self._last_sent_seq = None
        self._runtime_state_notice_text = NT_VALUE_EMPTY
        self._runtime_event_notice_text = NT_VALUE_EMPTY
        self._latest_runtime_state_payload = {}
        self._latest_runtime_devices = {}
        self._evidence_probe_results_by_label = {}
        self._manual_motion_checks = {}
        self._manual_test_observations = {}
        self._remembered_manual_active_group_members = []
        self._tests_active_group_rows = []
        self._tests_active_group_membership_key = tuple()
        self._group_owner_mode = GROUP_SOURCE_MANUAL
        self._manual_duty_last_sent_value = None
        self._manual_duty_last_sent_at = 0.0
        self._manual_duty_pending_after = None
        self._manual_duty_targets = []
        self._manual_duty_group_name = MANUAL_DUTY_NO_LABEL
        self._tracker.clear()
        if self._manual_duty_popup is not None:
            self._close_manual_duty_popup(stop_motor=False)
        self._refresh_tests_active_group_panel()
        self._refresh_output_runtime_notice()
        self._refresh_selected_test_scope_status()
        self._refresh_evidence_view()
        self._update_action_enabled()
        for live_view in self._iter_live_views():
            live_view.update_runtime_state(None)
            live_view.set_manual_test_observations({})
            live_view.clear_runtime_state_notice()
            live_view.clear_runtime_notice()

    def _apply_robot_ui_session_id(self, session_id: str) -> None:
        """
        NAME
            _apply_robot_ui_session_id - Track robot UI session generation and invalidate stale host runtime context.
        """
        clean_session_id = str(session_id or "").strip()
        previous_session_id = str(self.__dict__.get("_robot_ui_session_id") or "").strip()
        if clean_session_id and previous_session_id and clean_session_id != previous_session_id:
            self._reset_ui_session_runtime_context()
        self._robot_ui_session_id = clean_session_id or None

    def _manual_duty_block_message(self) -> str:
        """
        NAME
            _manual_duty_block_message - Return the current operator-facing reason manual duty is blocked.
        """
        if not self._tcp_connected:
            return MANUAL_DUTY_BLOCKED_TEXT
        if self._state_stale:
            return MANUAL_DUTY_BLOCKED_STALE_TEXT
        if self._robot_estopped_known:
            return MANUAL_DUTY_BLOCKED_ESTOP_TEXT
        if not self._robot_enabled_known:
            return MANUAL_DUTY_BLOCKED_DISABLED_TEXT
        return NT_VALUE_EMPTY

    def _is_manual_duty_target_allowed(self, label: object) -> bool:
        """
        NAME
            _is_manual_duty_target_allowed - Return whether one target label is eligible for manual duty.
        """
        clean_label = str(label or NT_VALUE_EMPTY).strip().lower()
        if not clean_label:
            return False
        runtime_device = self._latest_runtime_devices.get(clean_label, {})
        if not isinstance(runtime_device, dict):
            return False
        if self._controlled_lifecycle_active_known is True:
            lifecycle_state = str(
                runtime_device.get("lifecycleState", NT_VALUE_EMPTY)
            ).strip()
            return lifecycle_state == "controlled-active"
        return bool(runtime_device.get("testable", False))

    def _manual_duty_scope_block_message_for_targets(self, targets: List[str]) -> str:
        """
        NAME
            _manual_duty_scope_block_message_for_targets - Return a lifecycle-scope block reason for manual duty targets.
        """
        if self._controlled_lifecycle_active_known is not True:
            return NT_VALUE_EMPTY
        for label in targets:
            if not self._is_manual_duty_target_allowed(label):
                return MANUAL_DUTY_BLOCKED_CONTROLLED_SCOPE_TEXT
        return NT_VALUE_EMPTY

    def _is_manual_motor_node(self, node: object) -> bool:
        """
        NAME
            _is_manual_motor_node - Return whether the live node is a motor-like device.
        """
        if node is None:
            return False
        device_type = str(getattr(node, "device_type", NT_VALUE_EMPTY)).strip()
        return device_type == DEVICE_TYPE_MOTOR

    def _on_live_node_right_click(self, node: object, event: tk.Event) -> None:
        """
        NAME
            _on_live_node_right_click - Open the manual motor popup for a motor node.
        """
        if not self._is_manual_motor_node(node):
            return
        blocked = self._manual_duty_block_message()
        if blocked:
            self._append_output(blocked)
            return
        if self._tracker.is_pending():
            self._append_output(MANUAL_DUTY_BUSY_TEXT)
            return
        label = str(getattr(node, DEVICE_KEY_LABEL, NT_VALUE_EMPTY)).strip()
        if not label:
            label = str(getattr(node, "label", NT_VALUE_EMPTY)).strip()
        if not label:
            return
        scope_blocked = self._manual_duty_scope_block_message_for_targets([label])
        if scope_blocked:
            self._append_output(scope_blocked)
            return
        self._open_manual_duty_targets(label, [label], int(event.x_root), int(event.y_root))

    def _on_live_group_right_click(self, group: Dict[str, Any], _event: tk.Event) -> None:
        """
        NAME
            _on_live_group_right_click - Open one manual-duty popup targeting the clicked group's motor members.
        """
        group_name = str(group.get("name", NT_VALUE_EMPTY)).strip()
        if not group_name:
            return
        group_payload = group.get(GROUP_KEY_GROUP)
        if not isinstance(group_payload, dict):
            self._append_output(f"Group payload not available for {group_name}.")
            return
        targets = self._resolved_group_motor_targets(group_payload)
        if not targets:
            self._append_output(f"Group has no motor targets: {group_name}")
            return
        scope_blocked = self._manual_duty_scope_block_message_for_targets(targets)
        if scope_blocked:
            self._append_output(scope_blocked)
            return
        self._open_manual_group_duty_targets(group_name, targets, int(_event.x_root), int(_event.y_root))

    def _on_active_group_member_toggled(self, label: str, enabled: bool) -> None:
        """
        NAME
            _on_active_group_member_toggled - Add or remove one device from active-group from the Live Topology side panel.
        """
        clean_label = str(label or NT_VALUE_EMPTY).strip()
        if not clean_label:
            return
        if self._controlled_lifecycle_active_known is True:
            self._append_output(ACTIVE_GROUP_LOCKED_TEXT)
            self.after_idle(self._request_runtime_state_refresh)
            return
        if not self._tcp_connected:
            self._append_output(OUTPUT_NOT_CONNECTED)
            return
        if self._tracker.is_pending():
            self._append_output(OUTPUT_BUSY)
            return
        if not self.__dict__.get("_runtime_state_seen", False):
            self._append_output("Runtime state not loaded yet. Wait for refresh before editing active-group.")
            self.after_idle(self._request_runtime_state_refresh)
            return
        command = CMD_GROUP_ADD_DEVICE if enabled else CMD_GROUP_REMOVE_DEVICE
        args = {
            GROUP_RUN_ARG_GROUP: GROUP_ACTIVE_NAME,
            GROUP_RUN_ARG_DEVICE: clean_label,
        }
        self._append_output(
            f"{timestamp_hms()} CMD {command} \"{GROUP_ACTIVE_NAME}\" \"{clean_label}\""
        )
        self._last_cmd = (command, args)
        if self._send_and_wait(command, args):
            self.after_idle(self._request_runtime_state_refresh)

    def _on_live_override_action(self, label: str, action: str) -> None:
        """
        NAME
            _on_live_override_action - Send one explicit lifecycle override action for the selected device.
        """
        clean_label = str(label or NT_VALUE_EMPTY).strip()
        clean_action = str(action or NT_VALUE_EMPTY).strip().lower()
        if not clean_label or clean_action not in ("instantiate", "clear"):
            return
        if not self._tcp_connected:
            self._append_output(OUTPUT_NOT_CONNECTED)
            return
        if self._tracker.is_pending():
            self._append_output(OUTPUT_BUSY)
            return
        command = (
            DEVICE_OVERRIDE_CMD_INSTANTIATE
            if clean_action == "instantiate"
            else DEVICE_OVERRIDE_CMD_CLEAR
        )
        args = {MANUAL_DUTY_ARG_NAME: clean_label}
        self._append_output(f'{timestamp_hms()} CMD {command} "{clean_label}"')
        self._last_cmd = (command, args)
        seq = self._send_tcp_command(command, args)
        if seq is not None:
            self.after_idle(self._request_runtime_state_refresh)

    def _open_manual_duty_targets(self, label: str, targets: List[str], x_root: int, y_root: int) -> None:
        """
        NAME
            _open_manual_duty_targets - Validate manual-duty preconditions then open the shared popup for one or more targets.
        """
        blocked = self._manual_duty_block_message()
        if blocked:
            self._append_output(blocked)
            return
        if self._tracker.is_pending():
            self._append_output(MANUAL_DUTY_BUSY_TEXT)
            return
        self._request_runtime_state_refresh()
        self._open_manual_duty_popup(label, targets, MANUAL_DUTY_NO_LABEL, x_root, y_root)

    def _open_manual_group_duty_targets(
        self,
        group_name: str,
        targets: List[str],
        x_root: int,
        y_root: int,
    ) -> None:
        """
        NAME
            _open_manual_group_duty_targets - Validate group manual-duty preconditions then open the shared popup.
        """
        blocked = self._manual_duty_block_message()
        if blocked:
            self._append_output(blocked)
            return
        if self._tracker.is_pending():
            self._append_output(MANUAL_DUTY_BUSY_TEXT)
            return
        self._request_runtime_state_refresh()
        self._open_manual_duty_popup(
            group_name,
            targets,
            group_name,
            x_root,
            y_root,
        )
        for live_view in self._iter_live_views():
            live_view.set_group_run_inspector(group_name, targets)

    def _resolved_group_motor_targets(self, group_payload: Dict[str, Any]) -> List[str]:
        """
        NAME
            _resolved_group_motor_targets - Return enabled motor member labels for one clicked group payload.
        """
        return resolve_group_motor_targets(
            group_payload,
            [
                self.__dict__.get("_profile_devices", {}),
                self.__dict__.get("_test_profile_devices", {}),
                self.__dict__.get("_latest_runtime_devices", {}),
            ],
            fallback_device_lists=self._fallback_profile_device_lists(),
        )

    def _fallback_profile_device_lists(self) -> List[List[Dict[str, Any]]]:
        """
        NAME
            _fallback_profile_device_lists - Return profile device lists used as a readable last-resort label resolver.
        """
        fallback_lists: List[List[Dict[str, Any]]] = []
        for profile_name in list_profiles():
            try:
                profile_devices, _expected = get_profile(profile_name)
            except Exception:
                continue
            fallback_lists.append(
                [entry for entry in profile_devices if isinstance(entry, dict)]
            )
        return fallback_lists

    def _on_live_view_left_click(self, _node: object, _event: tk.Event) -> None:
        """
        NAME
            _on_live_view_left_click - Stop manual motor duty on the next live-view left click.
        """
        self._request_runtime_state_refresh()
        if self._manual_duty_popup is not None:
            self._close_manual_duty_popup(stop_motor=True)

    def _open_manual_duty_popup(
        self,
        label: str,
        targets: List[str],
        group_name: str,
        x_root: int,
        y_root: int,
    ) -> None:
        """
        NAME
            _open_manual_duty_popup - Show a popup slider for manual motor duty.
        """
        self._close_manual_duty_popup(stop_motor=True)
        popup = tk.Toplevel(self)
        popup.title(MANUAL_DUTY_POPUP_TITLE)
        popup.transient(self)
        popup.resizable(False, False)
        popup.geometry(
            f"{MANUAL_DUTY_POPUP_SIZE}+{x_root + MANUAL_DUTY_POPUP_OFFSET_X}+{y_root + MANUAL_DUTY_POPUP_OFFSET_Y}"
        )
        popup.protocol("WM_DELETE_WINDOW", lambda: self._close_manual_duty_popup(stop_motor=True))
        body = ttk.Frame(popup, padding=8)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=label).pack(anchor="w")
        scale = ttk.Scale(
            body,
            from_=MANUAL_DUTY_MIN,
            to=MANUAL_DUTY_MAX,
            variable=self._manual_duty_var,
            orient="horizontal",
            length=MANUAL_DUTY_SCALE_LENGTH,
            command=self._on_manual_duty_slider_changed,
        )
        scale.bind("<Button-1>", self._on_manual_duty_scale_button_down, add="+")
        scale.pack(fill="x", pady=(8, 4))
        ttk.Label(body, textvariable=self._manual_duty_value_var).pack(anchor="center")
        self._manual_duty_popup = popup
        self._manual_duty_label = label
        self._manual_duty_targets = [str(target).strip() for target in targets if str(target).strip()]
        self._manual_duty_group_name = str(group_name or MANUAL_DUTY_NO_LABEL).strip()
        self._manual_duty_var.set(MANUAL_DUTY_DEFAULT)
        self._manual_duty_value_var.set(
            MANUAL_DUTY_VALUE_FMT.format(value=MANUAL_DUTY_DEFAULT)
        )
        self._manual_duty_last_sent_value = None
        self._manual_duty_last_sent_at = 0.0
        self._manual_duty_pending_after = None
        scale.focus_set()

    def _on_manual_duty_scale_button_down(self, event: tk.Event) -> Optional[str]:
        """
        NAME
            _on_manual_duty_scale_button_down - Ignore trough clicks so manual duty changes only start from the slider thumb.
        """
        widget = event.widget
        identify = getattr(widget, "identify", None)
        if not callable(identify):
            return None
        try:
            element = str(identify(int(event.x), int(event.y)) or "").strip().lower()
        except Exception:
            return None
        if MANUAL_DUTY_SCALE_ELEMENT_SLIDER in element:
            return None
        return "break"

    def _close_manual_duty_popup(self, stop_motor: bool) -> None:
        """
        NAME
            _close_manual_duty_popup - Destroy the manual-duty popup and optionally stop the motor.
        """
        if self._manual_duty_pending_after is not None:
            try:
                self.after_cancel(self._manual_duty_pending_after)
            except Exception:
                pass
            self._manual_duty_pending_after = None
        label = self._manual_duty_label
        targets = list(self._manual_duty_targets)
        group_name = self._manual_duty_group_name
        popup = self._manual_duty_popup
        self._manual_duty_popup = None
        self._manual_duty_label = MANUAL_DUTY_NO_LABEL
        self._manual_duty_targets = MANUAL_DUTY_NO_TARGETS.copy()
        self._manual_duty_group_name = MANUAL_DUTY_NO_LABEL
        self._manual_duty_last_sent_value = None
        self._manual_duty_last_sent_at = 0.0
        self._manual_duty_var.set(MANUAL_DUTY_DEFAULT)
        self._manual_duty_value_var.set(
            MANUAL_DUTY_VALUE_FMT.format(value=MANUAL_DUTY_DEFAULT)
        )
        for live_view in self._iter_live_views():
            live_view.clear_group_run_inspector()
        if popup is not None:
            try:
                popup.destroy()
            except Exception:
                pass
        if stop_motor and targets:
            self._send_manual_duty_clear(label, targets, group_name)

    def _schedule_manual_duty_send(self) -> None:
        """
        NAME
            _schedule_manual_duty_send - Schedule a throttled manual-duty send.
        """
        if self._manual_duty_pending_after is not None:
            return
        delay_ms = int(self._manual_duty_send_interval_sec() * 1000.0)
        self._manual_duty_pending_after = self.after(
            delay_ms,
            self._flush_manual_duty_send,
        )

    def _on_manual_duty_slider_changed(self, value: str) -> None:
        """
        NAME
            _on_manual_duty_slider_changed - Track popup slider changes and send throttled motor commands.
        """
        try:
            duty = float(value)
        except Exception:
            duty = MANUAL_DUTY_DEFAULT
        duty = max(MANUAL_DUTY_MIN, min(MANUAL_DUTY_MAX, duty))
        self._manual_duty_value_var.set(MANUAL_DUTY_VALUE_FMT.format(value=duty))
        now = time.time()
        if (now - self._manual_duty_last_sent_at) >= self._manual_duty_send_interval_sec():
            self._flush_manual_duty_send()
            return
        self._schedule_manual_duty_send()

    def _manual_duty_send_interval_sec(self) -> float:
        """
        NAME
            _manual_duty_send_interval_sec - Return the current throttle interval for manual duty sends.
        """
        if self._live_enabled_var.get() and self._live_source_var.get() == LIVE_SOURCE_REST:
            return MANUAL_DUTY_SEND_MIN_INTERVAL_LIVE_SEC
        return MANUAL_DUTY_SEND_MIN_INTERVAL_SEC

    def _record_manual_motion_command(self, label: str, duty: float) -> None:
        """
        NAME
            _record_manual_motion_command - Start or refresh a short motion-verification window for one motor.
        """
        clean_label = str(label or NT_VALUE_EMPTY).strip().lower()
        if not clean_label:
            return
        now_sec = time.time()
        runtime_device = self._latest_runtime_devices.get(clean_label, {})
        start_position_rot = _runtime_device_field(runtime_device, EVIDENCE_FIELD_POSITION_ROT)
        existing_entry = self._manual_motion_checks.get(clean_label)
        if isinstance(existing_entry, dict):
            existing_entry["label"] = str(label).strip()
            existing_entry["duty"] = float(duty)
            existing_entry["startedAt"] = now_sec
            existing_entry["clearedAt"] = None
            existing_entry["sawMotion"] = bool(existing_entry.get("sawMotion"))
            existing_entry["maxAbsVelRpm"] = float(existing_entry.get("maxAbsVelRpm", 0.0))
            existing_entry["startPositionRot"] = (
                existing_entry.get("startPositionRot")
                if isinstance(existing_entry.get("startPositionRot"), (int, float))
                else (float(start_position_rot) if isinstance(start_position_rot, (int, float)) else None)
            )
            existing_entry["maxAbsPositionDeltaRot"] = float(existing_entry.get("maxAbsPositionDeltaRot", 0.0))
        else:
            self._manual_motion_checks[clean_label] = {
                "label": str(label).strip(),
                "duty": float(duty),
                "startedAt": now_sec,
                "clearedAt": None,
                "sawMotion": False,
                "maxAbsVelRpm": 0.0,
                "startPositionRot": float(start_position_rot) if isinstance(start_position_rot, (int, float)) else None,
                "maxAbsPositionDeltaRot": 0.0,
            }
        current_observation = self._manual_test_observations.get(clean_label)
        current_auto_result = (
            str(current_observation.get("autoResult", NT_VALUE_EMPTY)).strip()
            if isinstance(current_observation, dict)
            else NT_VALUE_EMPTY
        )
        next_auto_result = (
            current_auto_result
            if current_auto_result == EVIDENCE_MANUAL_AUTO_RESULT_ROTATION
            else EVIDENCE_MANUAL_AUTO_RESULT_RUNNING
        )
        self._update_manual_test_observation(
            clean_label,
            {
                "label": str(label).strip(),
                "autoResult": next_auto_result,
                "recordedAtEpochSec": now_sec,
                "recordedAt": timestamp_hms(),
                "cmdDuty": float(duty),
                "maxAbsVelRpm": float(self._manual_motion_checks.get(clean_label, {}).get("maxAbsVelRpm", 0.0)),
                "positionRot": start_position_rot if isinstance(start_position_rot, (int, float)) else None,
                "maxAbsPositionDeltaRot": float(self._manual_motion_checks.get(clean_label, {}).get("maxAbsPositionDeltaRot", 0.0)),
            },
        )
        self._refresh_evidence_view()
        self._apply_evidence_selection(label)

    def _mark_manual_motion_clear(self, label: str) -> None:
        """
        NAME
            _mark_manual_motion_clear - Mark the manual-duty command cleared while preserving the verification window.
        """
        clean_label = str(label or NT_VALUE_EMPTY).strip().lower()
        if not clean_label:
            return
        entry = self._manual_motion_checks.get(clean_label)
        if not isinstance(entry, dict):
            return
        entry["clearedAt"] = time.time()
        observation = self._manual_test_observations.get(clean_label)
        if isinstance(observation, dict):
            observation["recordedAtEpochSec"] = time.time()
            observation["recordedAt"] = timestamp_hms()
        self._refresh_evidence_view()
        self._apply_evidence_selection(label)

    def _update_manual_test_observation(self, clean_label: str, fields: Dict[str, Any]) -> None:
        """
        NAME
            _update_manual_test_observation - Persist the latest automatic manual-test observation for one device.
        """
        if not clean_label:
            return
        current = self._manual_test_observations.get(clean_label)
        if not isinstance(current, dict):
            current = {}
            self._manual_test_observations[clean_label] = current
        current.update(fields)
        self._push_manual_test_observations_to_live_views()

    def _push_manual_test_observations_to_live_views(self) -> None:
        """
        NAME
            _push_manual_test_observations_to_live_views - Publish cached manual-test observations to live topology surfaces.
        """
        for live_view in self._iter_live_views():
            live_view.set_manual_test_observations(self._manual_test_observations)

    def _flush_manual_duty_send(self) -> None:
        """
        NAME
            _flush_manual_duty_send - Send the current popup duty to the robot.
        """
        self._manual_duty_pending_after = None
        if not self._manual_duty_label or not self._manual_duty_targets:
            return
        blocked = self._manual_duty_block_message()
        if blocked:
            self._append_output(blocked)
            return
        duty = max(
            MANUAL_DUTY_MIN,
            min(MANUAL_DUTY_MAX, float(self._manual_duty_var.get())),
        )
        if self._manual_duty_last_sent_value is not None:
            if abs(duty - self._manual_duty_last_sent_value) < 1e-6:
                return
        sent_any = False
        if self._manual_duty_group_name:
            seq = self._send_tcp_command(
                MANUAL_GROUP_DUTY_CMD_SET,
                {
                    GROUP_RUN_ARG_GROUP: self._manual_duty_group_name,
                    MANUAL_DUTY_ARG_DUTY: duty,
                },
            )
            sent_any = seq is not None
        else:
            for target in self._manual_duty_targets:
                seq = self._send_tcp_command(
                    MANUAL_DUTY_CMD_SET,
                    {
                        MANUAL_DUTY_ARG_NAME: target,
                        MANUAL_DUTY_ARG_DUTY: duty,
                    },
                )
                if seq is not None:
                    sent_any = True
        if not sent_any:
            return
        self._manual_duty_last_sent_value = duty
        self._manual_duty_last_sent_at = time.time()
        if abs(duty) >= EVIDENCE_MOTION_CMD_THRESHOLD_DUTY:
            for target in self._manual_duty_targets:
                self._record_manual_motion_command(target, duty)
        self.after_idle(self._request_runtime_state_refresh)
        self._append_output(
            (
                MANUAL_DUTY_STATUS_FMT
                if len(self._manual_duty_targets) == 1
                else MANUAL_DUTY_GROUP_STATUS_FMT
            ).format(
                label=self._manual_duty_label,
                duty=duty,
            )
        )

    def _send_manual_duty_clear(self, label: str, targets: List[str], group_name: str) -> None:
        """
        NAME
            _send_manual_duty_clear - Stop the active manual-duty target set.
        """
        if not label or not self._tcp_connected or not targets:
            return
        sent_any = False
        if group_name:
            seq = self._send_tcp_command(
                MANUAL_GROUP_DUTY_CMD_CLEAR,
                {GROUP_RUN_ARG_GROUP: group_name},
            )
            sent_any = seq is not None
        else:
            for target in targets:
                seq = self._send_tcp_command(
                    MANUAL_DUTY_CMD_CLEAR,
                    {MANUAL_DUTY_ARG_NAME: target},
                )
                if seq is not None:
                    sent_any = True
        if not sent_any:
            return
        for target in targets:
            self._mark_manual_motion_clear(target)
        self.after_idle(self._request_runtime_state_refresh)
        self._append_output(
            (
                MANUAL_DUTY_STOPPED_FMT
                if len(targets) == 1
                else MANUAL_DUTY_GROUP_STOPPED_FMT
            ).format(label=label)
        )

    def _poll_presence_overrides(self) -> None:
        """
        NAME
            _poll_presence_overrides - Read presence confidence from NT diagnostics.
        """
        live_views = self._iter_live_views()
        if not live_views:
            return
        if not self._live_enabled_var.get():
            for live_view in live_views:
                live_view.set_presence_overrides({})
            return
        source = self._live_source_var.get()
        if source == LIVE_SOURCE_FILE:
            overrides = self._presence_overrides_file
            if self._presence_timeline:
                elapsed = max(PRESENCE_TIME_NONE, time.time() - self._presence_timeline_start)
                if self._presence_timeline_period > PRESENCE_TIME_NONE:
                    elapsed = elapsed % self._presence_timeline_period
                active = None
                for entry in self._presence_timeline:
                    at_sec = float(entry.get(PRESENCE_FILE_KEY_AT_SEC, PRESENCE_TIME_NONE))
                    if elapsed >= at_sec:
                        active = entry
                    else:
                        break
                if isinstance(active, dict):
                    overrides = dict(active.get(PRESENCE_FILE_KEY_OVERRIDES_BLOCK, {}))
            for live_view in live_views:
                live_view.set_presence_overrides(overrides or {})
            return
        if self._diag_table is None:
            for live_view in live_views:
                live_view.set_presence_overrides({})
            return
        overrides: Dict[str, str] = {}
        for label, device in self._profile_devices.items():
            label = str(device.get(DEVICE_KEY_LABEL, "")).strip()
            if not label:
                continue
            label_key = encode_label_for_nt(label)
            path = NT_PATH_PRESENCE_FMT.format(label_key)
            value = self._diag_table.getEntry(path).getString(NT_VALUE_EMPTY)
            if value in PRESENCE_VALUES:
                overrides[label] = value
        for live_view in live_views:
            live_view.set_presence_overrides(overrides)

    def _poll_visibility_snapshot(self, now: float) -> None:
        """
        NAME
            _poll_visibility_snapshot - Refresh visibility snapshot data.
        """
        if self._visibility_provider is None:
            return
        if (now - self._visibility_last_update) < VIS_REFRESH_SEC:
            return
        self._visibility_last_update = now
        now_ms = int(now * VIS_MS_PER_SEC)
        try:
            snapshot = self._visibility_provider.snapshot(VIS_PANEL_SCOPE, now_ms)
            summary = self._visibility_provider.summary(VIS_PANEL_SCOPE, now_ms)
        except Exception:
            return
        self._apply_visibility_snapshot(snapshot, summary)

    def _apply_visibility_snapshot(self, snapshot: Dict[str, object], summary: Dict[str, object]) -> None:
        """
        NAME
            _apply_visibility_snapshot - Apply visibility snapshot to UI.
        """
        self._latest_visibility_snapshot = dict(snapshot) if isinstance(snapshot, dict) else {}
        self._latest_visibility_summary = dict(summary) if isinstance(summary, dict) else {}
        if (
            self._visibility_table is None
            or self._visibility_unrecognized_table is None
            or self._visibility_ctre_raw_table is None
        ):
            return
        sources = snapshot.get(VIS_KEY_SOURCES)
        devices = snapshot.get(VIS_KEY_DEVICES)
        if not isinstance(sources, list) or not isinstance(devices, list):
            return
        source_ids: List[str] = []
        source_labels: Dict[str, str] = {}
        for entry in sources:
            if not isinstance(entry, dict):
                continue
            src_id = str(entry.get(VIS_KEY_ID, NT_VALUE_EMPTY)).strip()
            if not src_id:
                continue
            source_ids.append(src_id)
            label = str(entry.get(VIS_KEY_LABEL, src_id)).strip() or src_id
            source_labels[src_id] = label
        if source_ids != self._visibility_columns:
            self._visibility_columns = list(source_ids)
            self._configure_visibility_table_columns(self._visibility_table, source_ids, source_labels)
            self._configure_visibility_table_columns(
                self._visibility_unrecognized_table,
                source_ids,
                source_labels,
            )
        for row in self._visibility_table.get_children():
            self._visibility_table.delete(row)
        for row in self._visibility_unrecognized_table.get_children():
            self._visibility_unrecognized_table.delete(row)
        for row in self._visibility_ctre_raw_table.get_children():
            self._visibility_ctre_raw_table.delete(row)
        self._visibility_ctre_raw_table.insert(VIS_TREE_ROOT, VIS_TREE_END, values=[VIS_RAW_EMPTY_MESSAGE])
        self._visibility_row_meta = {}
        selected_defined_item = NT_VALUE_EMPTY
        selected_unrecognized_item = NT_VALUE_EMPTY
        profile_labels = set(self._profile_devices.keys())
        shown_devices = 0
        shown_all = 0
        shown_some = 0
        shown_none = 0
        for device in devices:
            if not isinstance(device, dict):
                continue
            label = str(device.get(VIS_KEY_LABEL, NT_VALUE_EMPTY)).strip()
            device_name = label
            unexpected = bool(device.get(VIS_UNEXPECTED_KEY, False))
            if profile_labels and label.strip().lower() not in profile_labels:
                if not unexpected:
                    continue
            visibility = device.get(VIS_KEY_VISIBILITY) if isinstance(device.get(VIS_KEY_VISIBILITY), dict) else {}
            metrics = device.get(VIS_KEY_METRICS) if isinstance(device.get(VIS_KEY_METRICS), dict) else {}
            raw_ids = device.get(VIS_KEY_RAW_IDS) if isinstance(device.get(VIS_KEY_RAW_IDS), list) else []
            runtime_device = self._latest_runtime_devices.get(label.strip().lower(), {})
            values: List[str] = [
                device_name,
                self._format_visibility_identity(device),
                self._format_visibility_last_seen(metrics),
                self._format_visibility_packet_count(metrics),
                self._format_visibility_packet_rate(metrics),
                _format_runtime_probe_bucket(runtime_device),
                _format_runtime_probe_score(runtime_device),
            ]
            visible_true_count = 0
            visible_false_count = 0
            for src_id in source_ids:
                value = visibility.get(src_id)
                if value is True:
                    values.append(VIS_VALUE_YES)
                    visible_true_count += 1
                elif value is False:
                    values.append(VIS_VALUE_NO)
                    visible_false_count += 1
                else:
                    values.append(VIS_VALUE_UNKNOWN)
            target_table = (
                self._visibility_unrecognized_table
                if unexpected and label.strip().lower() not in profile_labels
                else self._visibility_table
            )
            item_id = target_table.insert(VIS_TREE_ROOT, VIS_TREE_END, values=values)
            self._visibility_row_meta[item_id] = {
                VIS_ROW_META_LABEL: label,
                VIS_ROW_META_UNEXPECTED: unexpected,
                VIS_ROW_META_RAW_IDS: raw_ids,
            }
            if label == self._visibility_selected_label:
                if unexpected == self._visibility_selected_unexpected:
                    if target_table is self._visibility_unrecognized_table:
                        selected_unrecognized_item = item_id
                    else:
                        selected_defined_item = item_id
            shown_devices += 1
            if source_ids and visible_true_count == len(source_ids):
                shown_all += 1
            elif visible_true_count > 0:
                shown_some += 1
            else:
                shown_none += 1
        scoped_summary = {
            VIS_KEY_SOURCES_COUNT: len(source_ids),
            VIS_KEY_DEVICES_SHOWN: shown_devices,
            VIS_KEY_VISIBLE_ALL: shown_all,
            VIS_KEY_VISIBLE_SOME: shown_some,
            VIS_KEY_VISIBLE_NONE: shown_none,
        }
        if selected_defined_item:
            self._visibility_table.selection_set(selected_defined_item)
            self._visibility_table.focus(selected_defined_item)
            self._visibility_table.see(selected_defined_item)
            meta = self._visibility_row_meta.get(selected_defined_item, {})
            raw_ids = meta.get(VIS_ROW_META_RAW_IDS, [])
            self._populate_ctre_raw_table(raw_ids if isinstance(raw_ids, list) else [])
        elif selected_unrecognized_item:
            self._visibility_unrecognized_table.selection_set(selected_unrecognized_item)
            self._visibility_unrecognized_table.focus(selected_unrecognized_item)
            self._visibility_unrecognized_table.see(selected_unrecognized_item)
            meta = self._visibility_row_meta.get(selected_unrecognized_item, {})
            raw_ids = meta.get(VIS_ROW_META_RAW_IDS, [])
            self._populate_ctre_raw_table(raw_ids if isinstance(raw_ids, list) else [])
        else:
            self._populate_ctre_raw_table([])
        self._update_visibility_summary(scoped_summary)
        for live_view in self._iter_live_views():
            live_view.set_visibility_snapshot(snapshot)
        self._refresh_evidence_view()

    def _configure_visibility_table_columns(
        self,
        table: ttk.Treeview,
        source_ids: List[str],
        source_labels: Dict[str, str],
    ) -> None:
        """
        NAME
            _configure_visibility_table_columns - Apply the shared visibility table column layout.
        """
        columns = [
            VIS_COL_DEVICE,
            VIS_COL_IDENTITY,
            VIS_COL_LAST_SEEN,
            VIS_COL_PACKETS,
            VIS_COL_RATE,
            VIS_COL_PROBE_BUCKET,
            VIS_COL_PROBE_SCORE,
        ] + source_ids
        table[VIS_TREE_COLUMNS] = columns
        table.heading(VIS_COL_DEVICE, text=VIS_COL_DEVICE, anchor=VIS_TREE_ANCHOR_W)
        table.column(
            VIS_COL_DEVICE,
            width=VIS_COL_DEVICE_WIDTH,
            anchor=VIS_TREE_ANCHOR_W,
        )
        table.heading(VIS_COL_IDENTITY, text=VIS_COL_IDENTITY, anchor=VIS_TREE_ANCHOR_CENTER)
        table.column(
            VIS_COL_IDENTITY,
            width=VIS_COL_IDENTITY_WIDTH,
            anchor=VIS_TREE_ANCHOR_CENTER,
            stretch=False,
        )
        table.heading(VIS_COL_LAST_SEEN, text=VIS_COL_LAST_SEEN, anchor=VIS_TREE_ANCHOR_CENTER)
        table.column(
            VIS_COL_LAST_SEEN,
            width=VIS_COL_LAST_SEEN_WIDTH,
            anchor=VIS_TREE_ANCHOR_CENTER,
            stretch=False,
        )
        table.heading(VIS_COL_PACKETS, text=VIS_COL_PACKETS, anchor=VIS_TREE_ANCHOR_CENTER)
        table.column(
            VIS_COL_PACKETS,
            width=VIS_COL_PACKETS_WIDTH,
            anchor=VIS_TREE_ANCHOR_CENTER,
            stretch=False,
        )
        table.heading(VIS_COL_RATE, text=VIS_COL_RATE, anchor=VIS_TREE_ANCHOR_CENTER)
        table.column(
            VIS_COL_RATE,
            width=VIS_COL_RATE_WIDTH,
            anchor=VIS_TREE_ANCHOR_CENTER,
            stretch=False,
        )
        table.heading(VIS_COL_PROBE_BUCKET, text=VIS_COL_PROBE_BUCKET, anchor=VIS_TREE_ANCHOR_CENTER)
        table.column(
            VIS_COL_PROBE_BUCKET,
            width=VIS_COL_PROBE_BUCKET_WIDTH,
            anchor=VIS_TREE_ANCHOR_CENTER,
            stretch=False,
        )
        table.heading(VIS_COL_PROBE_SCORE, text=VIS_COL_PROBE_SCORE, anchor=VIS_TREE_ANCHOR_CENTER)
        table.column(
            VIS_COL_PROBE_SCORE,
            width=VIS_COL_PROBE_SCORE_WIDTH,
            anchor=VIS_TREE_ANCHOR_CENTER,
            stretch=False,
        )
        for src_id in source_ids:
            label = source_labels.get(src_id, src_id)
            table.heading(src_id, text=label, anchor=VIS_TREE_ANCHOR_CENTER)
            table.column(
                src_id,
                width=VIS_COL_SOURCE_WIDTH,
                anchor=VIS_TREE_ANCHOR_CENTER,
                stretch=True,
            )

    def _format_visibility_last_seen(self, metrics: Dict[str, object]) -> str:
        """
        NAME
            _format_visibility_last_seen - Format the most recent per-device visibility timestamp.
        """
        latest_ms: Optional[int] = None
        for entry in metrics.values():
            if not isinstance(entry, dict):
                continue
            last_seen = entry.get(VIS_KEY_LAST_SEEN_MS)
            if isinstance(last_seen, (int, float)):
                value = int(last_seen)
                latest_ms = value if latest_ms is None else max(latest_ms, value)
        if latest_ms is None or latest_ms <= 0:
            return VIS_LAST_SEEN_UNKNOWN
        age_sec = max(0.0, (time.time() * VIS_MS_PER_SEC - latest_ms) / VIS_MS_PER_SEC)
        if age_sec < 1.0:
            return f"{age_sec:.1f}s"
        if age_sec < 60.0:
            return f"{age_sec:.0f}s"
        if age_sec < 3600.0:
            return f"{age_sec / 60.0:.1f}m"
        return f"{age_sec / 3600.0:.1f}h"

    def _selected_evidence_filter_key(self) -> str:
        """
        NAME
            _selected_evidence_filter_key - Return the normalized Evidence filter key.
        """
        current = str(self._evidence_filter_var.get()).strip().lower()
        for key, label in EVIDENCE_FILTER_LABELS.items():
            if current == key or current == label.lower():
                return key
        return EVIDENCE_FILTER_ALL

    def _collect_console_snapshot(self) -> Dict[str, Any]:
        """
        NAME
            _collect_console_snapshot - Read the current console-diagnostics summary from NT.
        """
        result: Dict[str, Any] = {
            EVIDENCE_CONSOLE_SCOPE_DEVICES: {},
            EVIDENCE_CONSOLE_SCOPE_SYSTEM: [],
            "systemText": EVIDENCE_SOURCE_NONE,
            "systemConflict": False,
        }
        if self._diag_table is None or not self._nt_connected:
            return result
        console_table = self._diag_table.getSubTable("console")
        devices_table = console_table.getSubTable(EVIDENCE_CONSOLE_SCOPE_DEVICES)
        for label_key in devices_table.getSubTables():
            label = decode_label_from_nt(label_key).strip()
            if not label:
                continue
            device_table = devices_table.getSubTable(label_key)
            events: List[str] = []
            has_error = False
            has_warn = False
            for event_type in device_table.getSubTables():
                event_table = device_table.getSubTable(event_type)
                if not event_table.getEntry(EVIDENCE_CONSOLE_KEY_ACTIVE).getBoolean(False):
                    continue
                severity = str(
                    event_table.getEntry(EVIDENCE_CONSOLE_KEY_SEVERITY).getString(NT_VALUE_EMPTY)
                ).strip().upper()
                message = str(
                    event_table.getEntry(EVIDENCE_CONSOLE_KEY_MESSAGE).getString(NT_VALUE_EMPTY)
                ).strip()
                event_summary = f"[{severity or 'INFO'}] {event_type}"
                if message:
                    event_summary = f"{event_summary}: {message}"
                events.append(event_summary)
                if severity in ("ERROR", "FATAL"):
                    has_error = True
                elif severity == "WARN":
                    has_warn = True
            warn_count = int(device_table.getEntry(EVIDENCE_CONSOLE_KEY_WARN).getDouble(0.0))
            error_count = int(device_table.getEntry(EVIDENCE_CONSOLE_KEY_ERROR).getDouble(0.0))
            fatal_count = int(device_table.getEntry(EVIDENCE_CONSOLE_KEY_FATAL).getDouble(0.0))
            summary = EVIDENCE_SOURCE_NONE
            if events:
                summary = events[0]
            elif fatal_count > 0 or error_count > 0:
                summary = f"errors={error_count} fatal={fatal_count}"
            elif warn_count > 0:
                summary = f"warn={warn_count}"
            result[EVIDENCE_CONSOLE_SCOPE_DEVICES][label.lower()] = {
                "events": events,
                "summary": summary,
                "hasError": has_error or error_count > 0 or fatal_count > 0,
                "hasWarn": has_warn or warn_count > 0,
            }
        system_events: List[str] = []
        system_table = console_table.getSubTable(EVIDENCE_CONSOLE_SCOPE_SYSTEM)
        for event_type in system_table.getSubTables():
            event_table = system_table.getSubTable(event_type)
            if not event_table.getEntry(EVIDENCE_CONSOLE_KEY_ACTIVE).getBoolean(False):
                continue
            severity = str(
                event_table.getEntry(EVIDENCE_CONSOLE_KEY_SEVERITY).getString(NT_VALUE_EMPTY)
            ).strip().upper()
            message = str(
                event_table.getEntry(EVIDENCE_CONSOLE_KEY_MESSAGE).getString(NT_VALUE_EMPTY)
            ).strip()
            event_summary = f"[{severity or 'INFO'}] {event_type}"
            if message:
                event_summary = f"{event_summary}: {message}"
            system_events.append(event_summary)
        result[EVIDENCE_CONSOLE_SCOPE_SYSTEM] = system_events
        result["systemText"] = system_events[0] if system_events else EVIDENCE_SOURCE_NONE
        result["systemConflict"] = any(
            EVIDENCE_EVENT_TYPE_BUS_FAULT in entry or EVIDENCE_TEXT_STALE in entry.lower()
            for entry in system_events
        )
        return result

    def _build_evidence_can_bus_health_text(self, system_console: Dict[str, Any]) -> str:
        """
        NAME
            _build_evidence_can_bus_health_text - Build one operator-facing CAN-bus health summary from system console evidence.
        """
        system_events = (
            system_console.get(EVIDENCE_CONSOLE_SCOPE_SYSTEM, [])
            if isinstance(system_console, dict)
            else []
        )
        if not isinstance(system_events, list) or not system_events:
            return "Overall Health=OK | Active Events=0\nNo active CAN-bus warning events in system console."
        normalized = [str(entry or "").strip() for entry in system_events if str(entry or "").strip()]
        lower_events = [entry.lower() for entry in normalized]
        high_util_count = sum(EVIDENCE_CAN_TEXT_HIGH_UTIL in entry for entry in lower_events)
        recovered_count = sum(EVIDENCE_CAN_TEXT_RECOVERED in entry for entry in lower_events)
        bus_off_count = sum(EVIDENCE_CAN_TEXT_BUS_OFF in entry for entry in lower_events)
        error_spike_count = sum(EVIDENCE_CAN_TEXT_ERROR_SPIKE in entry for entry in lower_events)
        tx_full_count = sum(EVIDENCE_CAN_TEXT_TX_FULL in entry for entry in lower_events)
        if bus_off_count > 0:
            overall = EVIDENCE_BUS_HEALTH_CRITICAL
            impact = "Bus-off evidence can invalidate device freshness and per-device confidence."
        elif error_spike_count > 0 or tx_full_count > 0 or bool(system_console.get("systemConflict")):
            overall = EVIDENCE_BUS_HEALTH_DEGRADED
            impact = "CAN errors/contention may reduce confidence in timing and device-level conclusions."
        elif high_util_count > 0:
            overall = EVIDENCE_BUS_HEALTH_ELEVATED
            impact = "High bus load may reduce freshness and increase latency, but not all devices are necessarily unhealthy."
        else:
            overall = EVIDENCE_BUS_HEALTH_OK
            impact = "No active CAN-bus warning conditions are currently surfaced."
        summary = (
            f"Overall Health={overall}"
            f"{EVIDENCE_NOTE_SEPARATOR}Active Events={len(normalized)}"
            f"{EVIDENCE_NOTE_SEPARATOR}HighUtil={high_util_count}"
            f"{EVIDENCE_NOTE_SEPARATOR}Recovered={recovered_count}"
            f"{EVIDENCE_NOTE_SEPARATOR}ErrorSpike={error_spike_count}"
            f"{EVIDENCE_NOTE_SEPARATOR}TxFull={tx_full_count}"
            f"{EVIDENCE_NOTE_SEPARATOR}BusOff={bus_off_count}"
        )
        lines = [summary, impact]
        lines.extend(normalized[:4])
        return "\n".join(lines)

    def _manual_evidence_for_label(self, label: str) -> Optional[Dict[str, Any]]:
        """
        NAME
            _manual_evidence_for_label - Return the recorded manual-test evidence for one device label.
        """
        clean_label = str(label or NT_VALUE_EMPTY).strip().lower()
        if not clean_label:
            return None
        entry = self._evidence_manual_results.get(clean_label)
        return entry if isinstance(entry, dict) else None

    def _choose_manual_observed_label(self, selected_label: str) -> str:
        """
        NAME
            _choose_manual_observed_label - Show a mouse-first chooser for wrong-device manual-test outcomes.
        """
        choices = []
        for row in self._build_evidence_rows():
            label = str(row.get("label", NT_VALUE_EMPTY)).strip()
            if label:
                choices.append(label)
        if selected_label and selected_label not in choices:
            choices.insert(0, selected_label)
        if not choices:
            return NT_VALUE_EMPTY
        chosen = tk.StringVar(value=choices[0])
        dialog = tk.Toplevel(self)
        dialog.title(EVIDENCE_MANUAL_DIALOG_TITLE)
        dialog.transient(self)
        dialog.resizable(False, False)
        dialog.geometry(f"{EVIDENCE_MANUAL_DIALOG_WIDTH}x{EVIDENCE_MANUAL_DIALOG_HEIGHT}")
        result: Dict[str, str] = {"value": NT_VALUE_EMPTY}
        body = ttk.Frame(dialog, padding=8)
        body.pack(fill=tk.BOTH, expand=True)
        ttk.Label(body, text=EVIDENCE_MANUAL_DIALOG_PROMPT).pack(anchor=tk.W)
        combo = ttk.Combobox(body, state="readonly", values=choices, textvariable=chosen)
        combo.pack(fill=tk.X, pady=(8, 8))
        combo.focus_set()
        if selected_label:
            combo.set(selected_label)

        def _record_choice() -> None:
            result["value"] = str(chosen.get()).strip()
            dialog.destroy()

        def _cancel_choice() -> None:
            dialog.destroy()

        button_row = ttk.Frame(body)
        button_row.pack(fill=tk.X)
        ttk.Button(button_row, text=EVIDENCE_MANUAL_DIALOG_OK, command=_record_choice).pack(side=tk.LEFT)
        ttk.Button(button_row, text=EVIDENCE_MANUAL_DIALOG_CANCEL, command=_cancel_choice).pack(side=tk.LEFT, padx=(8, 0))
        dialog.protocol("WM_DELETE_WINDOW", _cancel_choice)
        dialog.grab_set()
        self.wait_window(dialog)
        return str(result.get("value", NT_VALUE_EMPTY)).strip()

    def _record_manual_evidence(self, outcome: str) -> None:
        """
        NAME
            _record_manual_evidence - Record one manual-test outcome for the selected Evidence device.
        """
        label = str(self._evidence_selected_title_var.get()).strip()
        if not label:
            return
        observed = NT_VALUE_EMPTY
        notes = NT_VALUE_EMPTY
        if outcome in (EVIDENCE_MANUAL_OUTCOME_WRONG_DEVICE, EVIDENCE_MANUAL_OUTCOME_WRONG_BRANCH):
            observed = self._choose_manual_observed_label(label) or NT_VALUE_EMPTY
            if not observed:
                return
        self._evidence_manual_results[label.lower()] = {
            "outcome": outcome,
            "observed": observed.strip(),
            "notes": notes.strip(),
            "recordedAt": timestamp_hms(),
            "recordedAtEpochSec": time.time(),
        }
        self._refresh_evidence_view()
        self._apply_evidence_selection(label)

    def _clear_manual_evidence_for_selected(self) -> None:
        """
        NAME
            _clear_manual_evidence_for_selected - Remove manual-test evidence for the selected device.
        """
        label = str(self._evidence_selected_title_var.get()).strip().lower()
        if not label:
            return
        self._evidence_manual_results.pop(label, None)
        self._manual_test_observations.pop(label, None)
        self._refresh_evidence_view()
        self._apply_evidence_selection(label)

    def _build_evidence_probe_stats_text(self) -> str:
        """
        NAME
            _build_evidence_probe_stats_text - Summarize active-probe session cadence for the Evidence inspector.
        """
        if self._evidence_probe_pending:
            return EVIDENCE_PROBE_STATS_RUNNING
        completed_at = float(self.__dict__.get("_evidence_last_probe_completed_at", 0.0) or 0.0)
        if completed_at > 0.0:
            age_sec = max(0.0, time.time() - completed_at)
            return EVIDENCE_PROBE_STATS_LAST_COMPLETE_FMT.format(
                age=_format_age_seconds(age_sec)
            )
        run_count = int(self.__dict__.get("_evidence_probe_run_count", 0) or 0)
        if run_count > 0:
            return EVIDENCE_PROBE_STATS_RUN_COUNT_FMT.format(count=run_count)
        return EVIDENCE_PROBE_STATS_WAITING

    def _build_evidence_probe_missing_text(self, runtime_device: Optional[Dict[str, Any]]) -> str:
        """
        NAME
            _build_evidence_probe_missing_text - Explain why the selected device has no device-specific Full Probe result.
        """
        completed_at = float(self.__dict__.get("_evidence_last_probe_completed_at", 0.0) or 0.0)
        if completed_at <= 0.0:
            return "Not run yet"
        if not isinstance(runtime_device, dict):
            return EVIDENCE_PROBE_NOT_IN_RUNTIME_SET
        if not bool(runtime_device.get("instantiated", False)):
            return EVIDENCE_PROBE_NOT_IN_RUNTIME_SET
        return EVIDENCE_PROBE_NO_DEVICE_RESULT

    def _cache_active_probe_results_from_command(self, payload: Optional[Dict[str, Any]]) -> None:
        """
        NAME
            _cache_active_probe_results_from_command - Cache per-device active probe results from one command JSON payload.
        """
        if not isinstance(payload, dict):
            return
        devices = payload.get("devices")
        if not isinstance(devices, list):
            return
        updated_at_ms = int(time.time() * 1000.0)
        cached: Dict[str, Dict[str, Any]] = {}
        for device in devices:
            if not isinstance(device, dict):
                continue
            label = str(device.get("label", "")).strip()
            if not label:
                continue
            failed_checks: List[str] = []
            evidence_rows = device.get("evidence")
            if isinstance(evidence_rows, list):
                for row in evidence_rows:
                    if not isinstance(row, dict):
                        continue
                    if bool(row.get("passed")):
                        continue
                    code = str(row.get("code", "")).strip()
                    observed = str(row.get("observedValue", "")).strip()
                    if not code:
                        continue
                    failed_checks.append(f"{code}={observed}" if observed else code)
            cached[label.lower()] = {
                ATTACHMENT_KEY_TYPE: ATTACHMENT_TYPE_ACTIVE_PRESENCE_PROBE,
                RUNTIME_PROBE_KEY_BUCKET: str(device.get("bucket", VIS_VALUE_UNKNOWN) or VIS_VALUE_UNKNOWN).strip(),
                RUNTIME_PROBE_KEY_SCORE: device.get("score"),
                RUNTIME_PROBE_KEY_MAX_SCORE: device.get("maxScore"),
                RUNTIME_PROBE_KEY_UPDATED_AT_MS: updated_at_ms,
                RUNTIME_PROBE_KEY_FAILED_CHECKS: failed_checks,
                RUNTIME_PROBE_KEY_WARNINGS: list(device.get("warnings", []) or []),
                RUNTIME_PROBE_KEY_ERRORS: list(device.get("errors", []) or []),
                "message": str(device.get("message", "") or "").strip(),
                "status": str(device.get("status", "") or "").strip(),
                "code": device.get("code"),
            }
        if cached:
            self._evidence_probe_results_by_label = cached

    def _merge_cached_active_probe_results_into_runtime_devices(self) -> None:
        """
        NAME
            _merge_cached_active_probe_results_into_runtime_devices - Fill missing runtime probe attachments from the last probe command result.
        """
        cached = self.__dict__.get("_evidence_probe_results_by_label")
        runtime_devices = self.__dict__.get("_latest_runtime_devices")
        if not isinstance(cached, dict) or not cached:
            return
        if not isinstance(runtime_devices, dict) or not runtime_devices:
            return
        for label_key, runtime_device in runtime_devices.items():
            if not isinstance(runtime_device, dict):
                continue
            if _runtime_active_probe_attachment(runtime_device) is not None:
                continue
            cached_attachment = cached.get(str(label_key).strip().lower())
            if not isinstance(cached_attachment, dict):
                continue
            attachments = runtime_device.get("attachments")
            if not isinstance(attachments, list):
                attachments = []
                runtime_device["attachments"] = attachments
            attachments.append(dict(cached_attachment))

    def _infer_device_evidence(
        self,
        label: str,
        visibility_device: Optional[Dict[str, Any]],
        runtime_device: Optional[Dict[str, Any]],
        console_entry: Optional[Dict[str, Any]],
        system_console: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        NAME
            _infer_device_evidence - Build one first-pass interpreted evidence row.
        """
        presence_attachment = _runtime_presence_check_attachment(runtime_device or {})
        probe_attachment = _runtime_active_probe_attachment(runtime_device or {})
        presence_value = (
            runtime_device.get("presenceConfidence")
            if isinstance(runtime_device, dict)
            else None
        )
        presence_bucket = VIS_VALUE_UNKNOWN
        if isinstance(presence_attachment, dict):
            presence_bucket = str(
                presence_attachment.get(RUNTIME_PRESENCE_KEY_BUCKET, VIS_VALUE_UNKNOWN)
            ).strip() or VIS_VALUE_UNKNOWN
        elif isinstance(presence_value, (int, float)):
            presence_bucket = (
                EVIDENCE_STATUS_PRESENT.lower()
                if float(presence_value) > 0.05
                else EVIDENCE_STATUS_ABSENT.lower()
            )
        presence_age_text = _runtime_presence_age_text(runtime_device)
        raw_probe_bucket = _format_runtime_probe_bucket(runtime_device)
        probe_bucket = raw_probe_bucket
        probe_age_bucket = _runtime_probe_age_bucket(runtime_device)
        probe_age_text = _runtime_probe_age_text(runtime_device)
        passive_summary = EVIDENCE_SOURCE_NONE
        passive_visible = False
        passive_identity = EVIDENCE_STATUS_UNKNOWN
        if isinstance(visibility_device, dict):
            metrics = visibility_device.get(VIS_KEY_METRICS) if isinstance(visibility_device.get(VIS_KEY_METRICS), dict) else {}
            passive_summary = " / ".join(
                (
                    self._format_visibility_last_seen(metrics),
                    self._format_visibility_packet_rate(metrics),
                )
            )
            visibility = visibility_device.get(VIS_KEY_VISIBILITY) if isinstance(visibility_device.get(VIS_KEY_VISIBILITY), dict) else {}
            passive_visible = any(value is True for value in visibility.values())
            identity_text = self._format_visibility_identity(visibility_device)
            if identity_text != VIS_LAST_SEEN_UNKNOWN:
                passive_identity = EVIDENCE_STATUS_MATCHING
        elif runtime_device:
            last_seen = runtime_device.get("lastSeenMs")
            passive_summary = _format_visibility_last_seen({VIS_KEY_SOURCES: {}, "runtime": {VIS_KEY_LAST_SEEN_MS: last_seen}}) if isinstance(last_seen, (int, float)) else EVIDENCE_SOURCE_NONE
        console_summary = console_entry.get("summary") if isinstance(console_entry, dict) else EVIDENCE_SOURCE_NONE
        console_events = console_entry.get("events", []) if isinstance(console_entry, dict) else []
        console_has_error = bool(console_entry.get("hasError")) if isinstance(console_entry, dict) else False
        console_has_warn = bool(console_entry.get("hasWarn")) if isinstance(console_entry, dict) else False
        manual_entry = self._manual_evidence_for_label(label)
        manual_observation = self._manual_test_observations.get(str(label or NT_VALUE_EMPTY).strip().lower())
        manual_auto_result = (
            str(manual_observation.get("autoResult", NT_VALUE_EMPTY)).strip()
            if isinstance(manual_observation, dict)
            else NT_VALUE_EMPTY
        )
        manual_age_sec = _manual_age_seconds(manual_entry)
        manual_recent_operability = isinstance(manual_age_sec, float) and manual_age_sec <= EVIDENCE_MANUAL_OPERABILITY_WINDOW_SEC
        manual_recent_identity = isinstance(manual_age_sec, float) and manual_age_sec <= EVIDENCE_MANUAL_IDENTITY_WINDOW_SEC
        manual_summary = EVIDENCE_MANUAL_PLACEHOLDER
        existence = EVIDENCE_STATUS_UNKNOWN
        operability = EVIDENCE_STATUS_UNKNOWN
        identity = passive_identity
        confidence = EVIDENCE_CONFIDENCE_LOW
        notes: List[str] = []
        evidence_state = EVIDENCE_STATE_UNKNOWN
        evidence_conflicted = False
        cmd_duty = _runtime_device_field(runtime_device or {}, EVIDENCE_FIELD_CMD_DUTY)
        applied_duty = _runtime_device_field(runtime_device or {}, EVIDENCE_FIELD_APPLIED_DUTY)
        velocity_rpm = _runtime_device_field(runtime_device or {}, EVIDENCE_FIELD_VEL_RPM)
        motor_current = _runtime_device_field(runtime_device or {}, EVIDENCE_FIELD_MOTOR_CURRENT_A)
        applied_v = _runtime_device_field(runtime_device or {}, "appliedV")
        bus_v = _runtime_device_field(runtime_device or {}, "busV")
        position_rot = _runtime_device_field(runtime_device or {}, EVIDENCE_FIELD_POSITION_ROT)
        motor_attachment = runtime_motor_attachment(runtime_device or {})
        manual_motion = self._manual_motion_checks.get(str(label or NT_VALUE_EMPTY).strip().lower())
        motion_commanded = (
            isinstance(cmd_duty, (int, float)) and abs(float(cmd_duty)) >= EVIDENCE_MOTION_CMD_THRESHOLD_DUTY
        ) or (
            isinstance(applied_duty, (int, float)) and abs(float(applied_duty)) >= EVIDENCE_MOTION_CMD_THRESHOLD_DUTY
        )
        motion_detected = isinstance(velocity_rpm, (int, float)) and abs(float(velocity_rpm)) >= EVIDENCE_MOTION_MIN_RPM
        position_delta_rot = None
        manual_motion_window_active = False
        manual_motion_failed = False
        if isinstance(manual_motion, dict):
            started_at = manual_motion.get("startedAt")
            duty_value = manual_motion.get("duty")
            start_position_rot = manual_motion.get("startPositionRot")
            if isinstance(position_rot, (int, float)) and isinstance(start_position_rot, (int, float)):
                position_delta_rot = float(position_rot) - float(start_position_rot)
            if isinstance(started_at, (int, float)) and isinstance(duty_value, (int, float)):
                age_sec = max(0.0, time.time() - float(started_at))
                if age_sec <= EVIDENCE_MANUAL_MOTION_WINDOW_SEC and abs(float(duty_value)) >= EVIDENCE_MOTION_CMD_THRESHOLD_DUTY:
                    manual_motion_window_active = True
                    motion_commanded = True
                    motion_detected = motion_detected or bool(manual_motion.get("sawMotion"))
                    if not motion_detected and isinstance(position_delta_rot, (int, float)):
                        motion_detected = abs(float(position_delta_rot)) >= EVIDENCE_MOTION_MIN_POSITION_DELTA_ROT
                    if age_sec >= EVIDENCE_MANUAL_MOTION_SETTLE_SEC and not motion_detected:
                        manual_motion_failed = True
        if manual_auto_result == EVIDENCE_MANUAL_AUTO_RESULT_ROTATION:
            motion_detected = True
            manual_motion_failed = False

        if presence_bucket == EVIDENCE_STATUS_PRESENT.lower():
            existence = EVIDENCE_STATUS_PRESENT
            confidence = EVIDENCE_CONFIDENCE_HIGH
            evidence_state = EVIDENCE_STATE_OK
        elif presence_bucket == EVIDENCE_STATUS_ABSENT.lower():
            existence = EVIDENCE_STATUS_ABSENT
            confidence = EVIDENCE_CONFIDENCE_MEDIUM
            evidence_state = EVIDENCE_STATE_MISSING

        if probe_attachment is None:
            probe_bucket = "not_run"
        elif probe_age_bucket == EVIDENCE_PROBE_AGE_STALE:
            notes.append(EVIDENCE_PROBE_NOTE_STALE)
        elif probe_age_bucket == EVIDENCE_PROBE_AGE_AGING:
            notes.append(EVIDENCE_PROBE_NOTE_AGING)
        if probe_bucket == "present" and probe_age_bucket != EVIDENCE_PROBE_AGE_STALE:
            if existence == EVIDENCE_STATUS_UNKNOWN:
                existence = EVIDENCE_STATUS_PRESENT
            if operability == EVIDENCE_STATUS_UNKNOWN:
                operability = EVIDENCE_STATUS_OK
            if confidence == EVIDENCE_CONFIDENCE_LOW:
                confidence = EVIDENCE_CONFIDENCE_MEDIUM
            if evidence_state == EVIDENCE_STATE_UNKNOWN:
                evidence_state = EVIDENCE_STATE_OK
        elif probe_bucket == "degraded" and probe_age_bucket != EVIDENCE_PROBE_AGE_STALE:
            if existence == EVIDENCE_STATUS_UNKNOWN:
                existence = EVIDENCE_STATUS_PRESENT
            operability = EVIDENCE_STATUS_DEGRADED
            confidence = EVIDENCE_CONFIDENCE_MEDIUM
            evidence_state = EVIDENCE_STATE_DEGRADED
        elif probe_bucket == "absent" and probe_age_bucket != EVIDENCE_PROBE_AGE_STALE:
            if existence == EVIDENCE_STATUS_PRESENT:
                existence = EVIDENCE_STATUS_CONFLICT
                evidence_conflicted = True
                notes.append("Full probe says absent but live presence check says present.")
                if confidence == EVIDENCE_CONFIDENCE_HIGH:
                    confidence = EVIDENCE_CONFIDENCE_MEDIUM
            elif existence == EVIDENCE_STATUS_UNKNOWN:
                existence = EVIDENCE_STATUS_ABSENT
                confidence = EVIDENCE_CONFIDENCE_HIGH
                evidence_state = EVIDENCE_STATE_MISSING
            if operability == EVIDENCE_STATUS_UNKNOWN:
                operability = EVIDENCE_STATUS_FAILED
        if probe_age_bucket == EVIDENCE_PROBE_AGE_AGING:
            if confidence == EVIDENCE_CONFIDENCE_HIGH:
                confidence = EVIDENCE_CONFIDENCE_MEDIUM
            elif confidence == EVIDENCE_CONFIDENCE_MEDIUM:
                confidence = EVIDENCE_CONFIDENCE_LOW

        if existence == EVIDENCE_STATUS_UNKNOWN and passive_visible:
            existence = EVIDENCE_STATUS_PRESENT
            confidence = EVIDENCE_CONFIDENCE_MEDIUM
            evidence_state = EVIDENCE_STATE_OK

        if console_has_error:
            if existence == EVIDENCE_STATUS_PRESENT:
                operability = EVIDENCE_STATUS_DEGRADED
                confidence = EVIDENCE_CONFIDENCE_MEDIUM
                evidence_state = EVIDENCE_STATE_DEGRADED
            elif existence == EVIDENCE_STATUS_UNKNOWN:
                operability = EVIDENCE_STATUS_FAILED
                evidence_state = EVIDENCE_STATE_DEGRADED
            if any(EVIDENCE_TEXT_DEVICE_TIMEOUT in entry.lower() for entry in console_events):
                notes.append("Device-specific timeout evidence present.")
        elif console_has_warn and operability == EVIDENCE_STATUS_UNKNOWN:
            operability = EVIDENCE_STATUS_DEGRADED
            confidence = EVIDENCE_CONFIDENCE_LOW
            evidence_state = EVIDENCE_STATE_DEGRADED

        if system_console.get("systemConflict"):
            notes.append("System-level console fault may reflect broader CAN isolation.")
            evidence_conflicted = True
            if confidence == EVIDENCE_CONFIDENCE_HIGH and probe_bucket != "absent":
                confidence = EVIDENCE_CONFIDENCE_MEDIUM
            elif confidence == EVIDENCE_CONFIDENCE_MEDIUM:
                confidence = EVIDENCE_CONFIDENCE_LOW

        if isinstance(manual_entry, dict):
            outcome = str(manual_entry.get("outcome", NT_VALUE_EMPTY)).strip().lower()
            manual_summary = EVIDENCE_MANUAL_OUTCOME_LABELS.get(outcome, outcome or EVIDENCE_MANUAL_PLACEHOLDER)
            if outcome == EVIDENCE_MANUAL_OUTCOME_CORRECT:
                if not manual_recent_identity:
                    notes.append(EVIDENCE_MANUAL_NOTE_STALE)
                elif probe_bucket == "absent" or console_has_error:
                    existence = EVIDENCE_STATUS_CONFLICT if probe_bucket == "absent" else existence
                    operability = EVIDENCE_STATUS_CONFLICT
                    identity = EVIDENCE_STATUS_MATCHING
                    confidence = EVIDENCE_CONFIDENCE_LOW
                    evidence_state = EVIDENCE_STATE_DEGRADED
                    evidence_conflicted = True
                    notes.append(EVIDENCE_MANUAL_NOTE_CONFLICT)
                elif manual_recent_operability:
                    existence = EVIDENCE_STATUS_PRESENT
                    operability = EVIDENCE_STATUS_OK
                    identity = EVIDENCE_STATUS_MATCHING
                    confidence = EVIDENCE_CONFIDENCE_HIGH
                    evidence_state = EVIDENCE_STATE_OK
                else:
                    existence = EVIDENCE_STATUS_PRESENT
                    identity = EVIDENCE_STATUS_MATCHING
                    confidence = EVIDENCE_CONFIDENCE_MEDIUM
                    notes.append(EVIDENCE_MANUAL_NOTE_AGE_IDENTITY_ONLY)
            elif outcome == EVIDENCE_MANUAL_OUTCOME_NO_RESPONSE:
                if manual_recent_operability:
                    operability = EVIDENCE_STATUS_FAILED
                    confidence = EVIDENCE_CONFIDENCE_HIGH
                    evidence_state = EVIDENCE_STATE_DEGRADED
                else:
                    notes.append(EVIDENCE_MANUAL_NOTE_STALE)
            elif outcome in (EVIDENCE_MANUAL_OUTCOME_INTERMITTENT, EVIDENCE_MANUAL_OUTCOME_DEGRADED):
                if manual_recent_operability:
                    existence = EVIDENCE_STATUS_PRESENT
                    operability = EVIDENCE_STATUS_DEGRADED
                    confidence = EVIDENCE_CONFIDENCE_HIGH
                    evidence_state = EVIDENCE_STATE_DEGRADED
                else:
                    notes.append(EVIDENCE_MANUAL_NOTE_STALE)
            elif outcome in (EVIDENCE_MANUAL_OUTCOME_WRONG_DEVICE, EVIDENCE_MANUAL_OUTCOME_WRONG_BRANCH):
                if manual_recent_identity:
                    existence = EVIDENCE_STATUS_PRESENT
                    identity = EVIDENCE_STATUS_WRONG
                    confidence = EVIDENCE_CONFIDENCE_HIGH if manual_recent_operability else EVIDENCE_CONFIDENCE_MEDIUM
                    if manual_recent_operability:
                        operability = EVIDENCE_STATUS_FAILED
                    evidence_state = EVIDENCE_STATE_IDENTITY
                    if not manual_recent_operability:
                        notes.append(EVIDENCE_MANUAL_NOTE_AGE_IDENTITY_ONLY)
                else:
                    notes.append(EVIDENCE_MANUAL_NOTE_STALE)
            elif outcome == EVIDENCE_MANUAL_OUTCOME_UNCERTAIN:
                confidence = EVIDENCE_CONFIDENCE_LOW
                notes.append("Operator marked manual result uncertain.")

        motion_verdict_position_delta = position_delta_rot
        if not isinstance(motion_verdict_position_delta, (int, float)) and isinstance(manual_observation, dict):
            motion_verdict_position_delta = manual_observation.get("maxAbsPositionDeltaRot")
        motion_verdict = infer_motor_runtime_verdict(
            present=existence != EVIDENCE_STATUS_ABSENT and existence != EVIDENCE_STATUS_UNKNOWN,
            cmd_duty=cmd_duty,
            applied_duty=applied_duty,
            applied_v=applied_v,
            bus_v=bus_v,
            vel_rpm=velocity_rpm,
            position_delta_rot=motion_verdict_position_delta,
            motor_current_a=motor_current,
            attachment=motor_attachment,
            duty_threshold=EVIDENCE_MOTION_CMD_THRESHOLD_DUTY,
            rpm_threshold=EVIDENCE_MOTION_MIN_RPM,
            position_delta_threshold=EVIDENCE_MOTION_MIN_POSITION_DELTA_ROT,
            current_active_threshold=0.2,
            low_bus_v_threshold=7.0,
            applied_v_active_threshold=1.0,
        )
        if manual_auto_result == EVIDENCE_MANUAL_AUTO_RESULT_ROTATION:
            motion_detected = True
        elif manual_auto_result == EVIDENCE_MANUAL_AUTO_RESULT_NO_ROTATION and motion_commanded:
            motion_detected = False
        if motion_commanded:
            if motion_detected or str(motion_verdict.get("result", "")).strip() == "rotating":
                if existence == EVIDENCE_STATUS_UNKNOWN:
                    existence = EVIDENCE_STATUS_PRESENT
                if operability == EVIDENCE_STATUS_UNKNOWN:
                    operability = EVIDENCE_STATUS_OK
                confidence = EVIDENCE_CONFIDENCE_HIGH if confidence == EVIDENCE_CONFIDENCE_LOW else confidence
                if evidence_state == EVIDENCE_STATE_UNKNOWN:
                    evidence_state = EVIDENCE_STATE_OK
                notes.append(EVIDENCE_MOTION_NOTE_ROTATING)
            elif manual_motion_failed or (not manual_motion_window_active):
                operability = EVIDENCE_STATUS_FAILED
                confidence = EVIDENCE_CONFIDENCE_HIGH if probe_bucket == "present" else EVIDENCE_CONFIDENCE_MEDIUM
                evidence_state = EVIDENCE_STATE_DEGRADED
                verdict_result = str(motion_verdict.get("result", "")).strip()
                if verdict_result == RESULT_STALLED:
                    notes.append("Motor commanded with current draw but no motion; possible stall/bind.")
                elif verdict_result == RESULT_ELECTRICAL:
                    notes.append("Motor commanded with little current and no motion; possible electrical/output-path issue.")
                else:
                    notes.append(EVIDENCE_MOTION_NOTE_NO_ROTATION)

        if identity == EVIDENCE_STATUS_MATCHING and existence == EVIDENCE_STATUS_PRESENT:
            if evidence_state == EVIDENCE_STATE_UNKNOWN:
                evidence_state = EVIDENCE_STATE_IDENTITY
        elif identity != EVIDENCE_STATUS_WRONG:
            identity = EVIDENCE_STATUS_UNKNOWN

        if probe_bucket in (VIS_VALUE_UNKNOWN, "not_run") and passive_visible and not console_has_error:
            notes.append(EVIDENCE_NOTE_PASSIVE_WITHOUT_PROBE_RESULT)
        if not notes:
            notes.append(EVIDENCE_NOTE_NONE)

        presence_lines = [EVIDENCE_SOURCE_NONE]
        if isinstance(presence_attachment, dict):
            presence_lines = [
                EVIDENCE_NOTE_SEPARATOR.join(
                    (
                        f"bucket={presence_bucket}",
                        f"score={float(presence_value):.2f}" if isinstance(presence_value, (int, float)) else "score=--",
                        f"updated={presence_age_text}",
                        f"source={str(presence_attachment.get(RUNTIME_PRESENCE_KEY_SOURCE, EVIDENCE_SOURCE_NONE)).strip() or EVIDENCE_SOURCE_NONE}",
                    )
                )
            ]
            message_text = str(
                presence_attachment.get(RUNTIME_PRESENCE_KEY_MESSAGE, EVIDENCE_SOURCE_NONE)
            ).strip() or EVIDENCE_SOURCE_NONE
            if message_text:
                presence_lines.append(message_text)
        elif isinstance(presence_value, (int, float)):
            presence_lines = [
                EVIDENCE_NOTE_SEPARATOR.join(
                    (
                        f"bucket={presence_bucket}",
                        f"score={float(presence_value):.2f}",
                        f"updated={presence_age_text}",
                        "source=runtimeState",
                    )
                )
            ]
        presence_text = "\n".join(presence_lines)

        passive_text = passive_summary
        if isinstance(visibility_device, dict):
            passive_text = EVIDENCE_NOTE_SEPARATOR.join(
                (
                    "source=CANable observer",
                    f"identity={self._format_visibility_identity(visibility_device)}",
                    f"lastSeen={self._format_visibility_last_seen(visibility_device.get(VIS_KEY_METRICS, {})) if isinstance(visibility_device.get(VIS_KEY_METRICS), dict) else VIS_LAST_SEEN_UNKNOWN}",
                    f"packets={self._format_visibility_packet_count(visibility_device.get(VIS_KEY_METRICS, {})) if isinstance(visibility_device.get(VIS_KEY_METRICS), dict) else VIS_PACKETS_UNKNOWN}",
                    f"rate={self._format_visibility_packet_rate(visibility_device.get(VIS_KEY_METRICS, {})) if isinstance(visibility_device.get(VIS_KEY_METRICS), dict) else VIS_RATE_UNKNOWN}",
                )
            )
        console_text = EVIDENCE_NOTE_SEPARATOR.join(console_events) if console_events else system_console.get("systemText", EVIDENCE_SOURCE_NONE)
        probe_stats_text = self._build_evidence_probe_stats_text()
        probe_lines = [self._build_evidence_probe_missing_text(runtime_device), probe_stats_text]
        if isinstance(probe_attachment, dict):
            failed_checks = _attachment_string_list(probe_attachment, RUNTIME_PROBE_KEY_FAILED_CHECKS)
            warnings = _attachment_string_list(probe_attachment, RUNTIME_PROBE_KEY_WARNINGS)
            errors = _attachment_string_list(probe_attachment, RUNTIME_PROBE_KEY_ERRORS)
            probe_lines = [
                EVIDENCE_NOTE_SEPARATOR.join(
                    (
                        f"bucket={raw_probe_bucket}",
                        f"score={_format_runtime_probe_score(runtime_device)}",
                        f"updated={probe_age_text}",
                        f"ageClass={probe_age_bucket if probe_age_bucket != VIS_VALUE_UNKNOWN else EVIDENCE_STATUS_NOT_RUN}",
                    )
                )
            ]
            if failed_checks:
                probe_lines.append("failed: " + ", ".join(failed_checks))
            if warnings:
                probe_lines.append("warnings: " + ", ".join(warnings[:EVIDENCE_PROBE_DETAIL_LIMIT]))
            if errors:
                probe_lines.append("errors: " + ", ".join(errors[:EVIDENCE_PROBE_DETAIL_LIMIT]))
            probe_lines.append(probe_stats_text)
            message_text = str(probe_attachment.get("message", EVIDENCE_SOURCE_NONE)).strip() or EVIDENCE_SOURCE_NONE
            if message_text:
                probe_lines.append(message_text)
            probe_lines.append(EVIDENCE_PROBE_NOTE_ONE_SHOT)
        probe_text = "\n".join(probe_lines)
        if isinstance(manual_observation, dict):
            auto_result = str(manual_observation.get("autoResult", NT_VALUE_EMPTY)).strip()
            if auto_result:
                manual_summary = EVIDENCE_MANUAL_AUTO_RESULT_LABELS.get(auto_result, auto_result)
        manual_lines = [EVIDENCE_MANUAL_PLACEHOLDER]
        if isinstance(manual_entry, dict):
            manual_lines = [EVIDENCE_MANUAL_LINE_RESULT.format(value=manual_summary)]
            observed = str(manual_entry.get("observed", NT_VALUE_EMPTY)).strip()
            notes_value = str(manual_entry.get("notes", NT_VALUE_EMPTY)).strip()
            recorded = str(manual_entry.get("recordedAt", NT_VALUE_EMPTY)).strip()
            if isinstance(manual_age_sec, float):
                manual_lines.append(EVIDENCE_MANUAL_LINE_AGE.format(value=_format_age_seconds(manual_age_sec)))
            if observed:
                manual_lines.append(EVIDENCE_MANUAL_LINE_OBSERVED.format(value=observed))
            if notes_value:
                manual_lines.append(EVIDENCE_MANUAL_LINE_NOTES.format(value=notes_value))
            if recorded:
                manual_lines.append(EVIDENCE_MANUAL_LINE_RECORDED.format(value=recorded))
        elif isinstance(manual_observation, dict):
            auto_result = str(manual_observation.get("autoResult", NT_VALUE_EMPTY)).strip() or EVIDENCE_MANUAL_PLACEHOLDER
            auto_result_label = EVIDENCE_MANUAL_AUTO_RESULT_LABELS.get(auto_result, auto_result)
            manual_lines = [EVIDENCE_MANUAL_LINE_AUTO_RESULT.format(value=auto_result_label)]
            observation_age_sec = _manual_age_seconds(manual_observation)
            observation_recorded = str(manual_observation.get("recordedAt", NT_VALUE_EMPTY)).strip()
            if isinstance(observation_age_sec, float):
                manual_lines.append(EVIDENCE_MANUAL_LINE_AGE.format(value=_format_age_seconds(observation_age_sec)))
            if observation_recorded:
                manual_lines.append(EVIDENCE_MANUAL_LINE_RECORDED.format(value=observation_recorded))

        def _format_motion_value(value: Any) -> str:
            if isinstance(value, (int, float)):
                return f"{float(value):.2f}"
            return EVIDENCE_VALUE_NOT_APPLICABLE

        motion_detail_source = manual_observation if isinstance(manual_observation, dict) else None
        motion_cmd_value = cmd_duty
        motion_applied_value = applied_duty
        motion_vel_value = velocity_rpm
        motion_current_value = motor_current
        motion_position_value = position_rot
        motion_position_delta_value = position_delta_rot
        if isinstance(motion_detail_source, dict):
            motion_cmd_value = motion_detail_source.get("cmdDuty", motion_cmd_value)
            motion_applied_value = motion_detail_source.get("appliedDuty", motion_applied_value)
            motion_vel_value = motion_detail_source.get("velRpm", motion_vel_value)
            motion_current_value = motion_detail_source.get("motorCurrentA", motion_current_value)
            motion_position_value = motion_detail_source.get("positionRot", motion_position_value)
            motion_position_delta_value = motion_detail_source.get("positionDeltaRot", motion_position_delta_value)
            max_position_delta_value = motion_detail_source.get("maxAbsPositionDeltaRot")
            if (
                not isinstance(motion_position_delta_value, (int, float))
                and isinstance(max_position_delta_value, (int, float))
            ):
                motion_position_delta_value = max_position_delta_value

        if (
            motion_commanded
            or manual_motion_window_active
            or isinstance(manual_motion, dict)
            or isinstance(manual_observation, dict)
        ):
            motion_state = EVIDENCE_MANUAL_MOTION_IDLE
            if motion_detected:
                motion_state = EVIDENCE_MANUAL_MOTION_PASS
            elif motion_commanded and (manual_motion_failed or not manual_motion_window_active):
                motion_state = EVIDENCE_MANUAL_MOTION_FAIL
            elif motion_commanded or manual_motion_window_active:
                motion_state = EVIDENCE_MANUAL_MOTION_ACTIVE
            elif isinstance(manual_observation, dict):
                auto_result = str(manual_observation.get("autoResult", NT_VALUE_EMPTY)).strip()
                if auto_result == EVIDENCE_MANUAL_AUTO_RESULT_ROTATION:
                    motion_state = EVIDENCE_MANUAL_MOTION_PASS
                elif auto_result == EVIDENCE_MANUAL_AUTO_RESULT_NO_ROTATION:
                    motion_state = EVIDENCE_MANUAL_MOTION_FAIL
                elif auto_result == EVIDENCE_MANUAL_AUTO_RESULT_RUNNING:
                    motion_state = EVIDENCE_MANUAL_MOTION_ACTIVE
            manual_lines.append(EVIDENCE_MANUAL_LINE_MOTION.format(value=motion_state))
            manual_lines.append(
                EVIDENCE_MANUAL_LINE_MOTION_VALUES.format(
                    cmd=_format_motion_value(motion_cmd_value),
                    applied=_format_motion_value(motion_applied_value),
                    vel=_format_motion_value(motion_vel_value),
                    position=_format_motion_value(motion_position_value),
                    delta=_format_motion_value(motion_position_delta_value),
                    current=_format_motion_value(motion_current_value),
                )
            )
        manual_text = "\n".join(manual_lines)
        return {
            "label": label,
            "passive": passive_summary,
            "console": console_summary or EVIDENCE_SOURCE_NONE,
            "probe": (
                "Waiting"
                if probe_bucket in (VIS_VALUE_UNKNOWN, "not_run")
                else (
                    f"{probe_bucket}*"
                    if probe_age_bucket in (EVIDENCE_PROBE_AGE_AGING, EVIDENCE_PROBE_AGE_STALE)
                    else probe_bucket
                )
            ),
            "probeScore": _format_runtime_probe_score(runtime_device),
            "manual": manual_summary,
            "existence": existence,
            "operability": operability,
            "identity": identity,
            "confidence": confidence,
            "presenceText": presence_text,
            "passiveText": passive_text,
            "consoleText": console_text,
            "probeText": probe_text,
            "manualText": manual_text,
            "notesText": EVIDENCE_NOTE_SEPARATOR.join(notes),
            "state": evidence_state,
            "conflicted": evidence_conflicted,
        }

    def _build_evidence_rows(self) -> List[Dict[str, Any]]:
        """
        NAME
            _build_evidence_rows - Build interpreted evidence rows for the current profile.
        """
        visibility_devices = {}
        devices = self._latest_visibility_snapshot.get(VIS_KEY_DEVICES)
        if isinstance(devices, list):
            for device in devices:
                if not isinstance(device, dict):
                    continue
                label = str(device.get(VIS_KEY_LABEL, NT_VALUE_EMPTY)).strip()
                if label:
                    visibility_devices[label.lower()] = device
        console_snapshot = self._collect_console_snapshot()
        rows: List[Dict[str, Any]] = []
        for label, profile_device in self._profile_devices.items():
            display_label = str(profile_device.get(DEVICE_KEY_LABEL, label)).strip() or label
            rows.append(
                self._infer_device_evidence(
                    display_label,
                    visibility_devices.get(label),
                    self._latest_runtime_devices.get(label),
                    console_snapshot[EVIDENCE_CONSOLE_SCOPE_DEVICES].get(label),
                    console_snapshot,
                )
            )
        rows.sort(key=lambda row: str(row.get("label", NT_VALUE_EMPTY)).lower())
        return rows

    def _evidence_matches_filter(self, row: Dict[str, Any], filter_key: str) -> bool:
        """
        NAME
            _evidence_matches_filter - Return whether one row should be shown for the selected filter.
        """
        if filter_key == EVIDENCE_FILTER_ALL:
            return True
        if filter_key == EVIDENCE_FILTER_CONFLICTED:
            return bool(row.get("conflicted"))
        if filter_key == EVIDENCE_FILTER_MISSING:
            return str(row.get("existence", NT_VALUE_EMPTY)).upper() == EVIDENCE_STATUS_ABSENT
        if filter_key == EVIDENCE_FILTER_DEGRADED:
            return str(row.get("operability", NT_VALUE_EMPTY)).upper() in (
                EVIDENCE_STATUS_DEGRADED,
                EVIDENCE_STATUS_FAILED,
            )
        return True

    def _set_evidence_text(self, section: str, text_value: str) -> None:
        """
        NAME
            _set_evidence_text - Replace one read-only Evidence inspector text block.
        """
        widget = self._evidence_text_widgets.get(section)
        if widget is None:
            return
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text_value or EVIDENCE_SOURCE_NONE)
        widget.configure(state="disabled")

    def _apply_evidence_selection(self, label: str) -> None:
        """
        NAME
            _apply_evidence_selection - Update the Evidence inspector for one device label.
        """
        clean_label = str(label or NT_VALUE_EMPTY).strip().lower()
        row = self._evidence_rows_by_label.get(clean_label)
        self._evidence_selected_label = clean_label
        if row is None:
            self._evidence_selected_title_var.set(NT_VALUE_EMPTY)
            for key, var in self._evidence_detail_vars.items():
                if key == EVIDENCE_LABEL_CONFIDENCE:
                    var.set(EVIDENCE_CONFIDENCE_LOW)
                else:
                    var.set(EVIDENCE_STATUS_UNKNOWN)
            console_snapshot = self._collect_console_snapshot()
            self._set_evidence_text(
                EVIDENCE_BUS_HEALTH_TEXT,
                self._build_evidence_can_bus_health_text(console_snapshot),
            )
            for section in self._evidence_text_widgets:
                if section == EVIDENCE_BUS_HEALTH_TEXT:
                    continue
                self._set_evidence_text(section, EVIDENCE_SOURCE_NONE)
            return
        self._evidence_selected_title_var.set(str(row.get("label", NT_VALUE_EMPTY)))
        self._evidence_detail_vars[EVIDENCE_LABEL_EXISTENCE].set(str(row.get("existence", EVIDENCE_STATUS_UNKNOWN)))
        self._evidence_detail_vars[EVIDENCE_LABEL_OPERABILITY].set(str(row.get("operability", EVIDENCE_STATUS_UNKNOWN)))
        self._evidence_detail_vars[EVIDENCE_LABEL_IDENTITY].set(str(row.get("identity", EVIDENCE_STATUS_UNKNOWN)))
        self._evidence_detail_vars[EVIDENCE_LABEL_CONFIDENCE].set(str(row.get("confidence", EVIDENCE_CONFIDENCE_LOW)))
        console_snapshot = self._collect_console_snapshot()
        self._set_evidence_text(
            EVIDENCE_BUS_HEALTH_TEXT,
            self._build_evidence_can_bus_health_text(console_snapshot),
        )
        self._set_evidence_text(EVIDENCE_PRESENCE_TEXT, str(row.get("presenceText", EVIDENCE_SOURCE_NONE)))
        self._set_evidence_text(EVIDENCE_PASSIVE_TEXT, str(row.get("passiveText", EVIDENCE_SOURCE_NONE)))
        self._set_evidence_text(EVIDENCE_CONSOLE_TEXT, str(row.get("consoleText", EVIDENCE_SOURCE_NONE)))
        self._set_evidence_text(EVIDENCE_PROBE_TEXT, str(row.get("probeText", EVIDENCE_SOURCE_NONE)))
        self._set_evidence_text(EVIDENCE_MANUAL_TEXT, str(row.get("manualText", EVIDENCE_MANUAL_PLACEHOLDER)))
        self._set_evidence_text(EVIDENCE_NOTES_TEXT, str(row.get("notesText", EVIDENCE_NOTE_NONE)))

    def _refresh_evidence_view(self) -> None:
        """
        NAME
            _refresh_evidence_view - Rebuild the Evidence table, topology overlay, and inspector.
        """
        table = self._evidence_table
        live_view = self._evidence_live_view
        if table is None or live_view is None:
            return
        yview_state = table.yview()
        if not isinstance(yview_state, tuple) or len(yview_state) != 2:
            yview_state = (0.0, 1.0)
        existing_selection = tuple(table.selection())
        for row_id in table.get_children():
            table.delete(row_id)
        rows = self._build_evidence_rows()
        self._evidence_rows_by_label = {
            str(row.get("label", NT_VALUE_EMPTY)).strip().lower(): row for row in rows
        }
        filter_key = self._selected_evidence_filter_key()
        shown_rows = [row for row in rows if self._evidence_matches_filter(row, filter_key)]
        evidence_snapshot = {
            str(row.get("label", NT_VALUE_EMPTY)).strip().lower(): str(row.get("state", EVIDENCE_STATE_UNKNOWN)).strip().lower()
            for row in rows
        }
        live_view.set_evidence_snapshot(evidence_snapshot)
        for row in shown_rows:
            table.insert(
                VIS_TREE_ROOT,
                VIS_TREE_END,
                values=(
                    row.get("label", NT_VALUE_EMPTY),
                    row.get("passive", EVIDENCE_SOURCE_NONE),
                    row.get("console", EVIDENCE_SOURCE_NONE),
                    row.get("probe", EVIDENCE_SOURCE_NONE),
                    row.get("probeScore", EVIDENCE_SOURCE_NONE),
                    row.get("manual", EVIDENCE_MANUAL_PLACEHOLDER),
                    row.get("existence", EVIDENCE_STATUS_UNKNOWN),
                    row.get("operability", EVIDENCE_STATUS_UNKNOWN),
                    row.get("identity", EVIDENCE_STATUS_UNKNOWN),
                    row.get("confidence", EVIDENCE_CONFIDENCE_LOW),
                ),
            )
        self._evidence_summary_var.set(
            f"Devices: {len(rows)} | Showing: {len(shown_rows)} | Filter: {EVIDENCE_FILTER_LABELS.get(filter_key, EVIDENCE_FILTER_LABELS[EVIDENCE_FILTER_ALL])}"
        )
        selected_label = self._evidence_selected_label
        auto_selected_label = False
        if not selected_label and shown_rows:
            selected_label = str(shown_rows[0].get("label", NT_VALUE_EMPTY)).strip().lower()
            self._evidence_selected_label = selected_label
            auto_selected_label = True
        if selected_label:
            self._evidence_syncing_selection = True
            try:
                selected_item = NT_VALUE_EMPTY
                for item_id in table.get_children():
                    values = table.item(item_id, "values")
                    if values and str(values[0]).strip().lower() == selected_label:
                        selected_item = item_id
                        break
                if selected_item:
                    table.selection_set(selected_item)
                    table.focus(selected_item)
                self._apply_evidence_selection(selected_label)
            finally:
                self._evidence_syncing_selection = False
        else:
            self._apply_evidence_selection(NT_VALUE_EMPTY)
        if auto_selected_label and selected_label:
            selected_items = table.selection()
            if selected_items:
                table.see(selected_items[0])
            return
        if existing_selection:
            try:
                table.yview_moveto(float(yview_state[0]))
            except Exception:
                pass

    def _apply_evidence_table_selection_by_label(self, label: str) -> None:
        """
        NAME
            _apply_evidence_table_selection_by_label - Select one Evidence table row outside the canvas click stack.
        """
        self._evidence_pending_row_label = NT_VALUE_EMPTY
        table = self._evidence_table
        if table is None:
            return
        clean_label = str(label or NT_VALUE_EMPTY).strip().lower()
        if not clean_label:
            return
        self._evidence_syncing_selection = True
        try:
            for item_id in table.get_children():
                values = table.item(item_id, "values")
                if values and str(values[0]).strip().lower() == clean_label:
                    table.selection_set(item_id)
                    table.focus(item_id)
                    table.see(item_id)
                    break
        finally:
            self._evidence_syncing_selection = False

    def _apply_evidence_topology_selection_by_label(self, label: str) -> None:
        """
        NAME
            _apply_evidence_topology_selection_by_label - Select one Evidence topology node outside the row-selection stack.
        """
        self._evidence_pending_node_label = NT_VALUE_EMPTY
        live_view = self._evidence_live_view
        if live_view is None:
            return
        clean_label = str(label or NT_VALUE_EMPTY).strip()
        if not clean_label:
            return
        self._evidence_syncing_selection = True
        try:
            live_view.select_node_by_label(clean_label)
        finally:
            self._evidence_syncing_selection = False

    def _on_evidence_row_selected(self, event: tk.Event) -> None:
        """
        NAME
            _on_evidence_row_selected - Sync table selection into topology and inspector.
        """
        if self._evidence_syncing_selection:
            return
        widget = event.widget
        if not isinstance(widget, ttk.Treeview):
            return
        selection = widget.selection()
        if not selection:
            return
        values = widget.item(selection[0], "values")
        if not values:
            return
        label = str(values[0]).strip()
        self._apply_evidence_selection(label)
        if self._evidence_pending_node_label != label:
            self._evidence_pending_node_label = label
            self.after_idle(lambda target=label: self._apply_evidence_topology_selection_by_label(target))

    def _on_evidence_topology_selected(self, node: Optional[object]) -> None:
        """
        NAME
            _on_evidence_topology_selected - Sync topology selection into the Evidence table and inspector.
        """
        if self._evidence_syncing_selection:
            return
        label = str(getattr(node, "label", NT_VALUE_EMPTY)).strip() if node is not None else NT_VALUE_EMPTY
        if not label:
            return
        self._apply_evidence_selection(label)
        if self._evidence_pending_row_label != label:
            self._evidence_pending_row_label = label
            self.after_idle(lambda target=label: self._apply_evidence_table_selection_by_label(target))

    def _format_visibility_identity(self, device: Dict[str, object]) -> str:
        """
        NAME
            _format_visibility_identity - Format the passive identity key for one visibility row.
        """
        identity = device.get(VIS_KEY_IDENTITY)
        if isinstance(identity, str) and identity.strip():
            return identity.strip()
        return VIS_LAST_SEEN_UNKNOWN

    def _format_visibility_packet_count(self, metrics: Dict[str, object]) -> str:
        """
        NAME
            _format_visibility_packet_count - Format the aggregate packet count across sources.
        """
        total = 0
        seen_any = False
        for entry in metrics.values():
            if not isinstance(entry, dict):
                continue
            msg_count = entry.get(VIS_KEY_MSG_COUNT)
            if isinstance(msg_count, (int, float)):
                total += int(msg_count)
                seen_any = True
        if not seen_any:
            return VIS_PACKETS_UNKNOWN
        return str(total)

    def _format_visibility_packet_rate(self, metrics: Dict[str, object]) -> str:
        """
        NAME
            _format_visibility_packet_rate - Format the aggregate frames-per-second rate across sources.
        """
        total = 0.0
        seen_any = False
        for entry in metrics.values():
            if not isinstance(entry, dict):
                continue
            rate = entry.get(VIS_KEY_FRAMES_PER_SEC)
            if isinstance(rate, (int, float)):
                total += float(rate)
                seen_any = True
        if not seen_any:
            return VIS_RATE_UNKNOWN
        return VIS_RATE_FMT.format(value=total)

    def _format_visibility_rate_value(self, value: object) -> str:
        """
        NAME
            _format_visibility_rate_value - Format one scalar frames-per-second value.
        """
        if not isinstance(value, (int, float)):
            return VIS_RATE_UNKNOWN
        return VIS_RATE_FMT.format(value=float(value))

    def _format_visibility_small_int(self, value: object) -> str:
        """
        NAME
            _format_visibility_small_int - Format one compact integer field for the raw decode table.
        """
        if not isinstance(value, (int, float)):
            return VIS_LAST_SEEN_UNKNOWN
        return str(int(value))

    def _format_visibility_hex_byte(self, value: object) -> str:
        """
        NAME
            _format_visibility_hex_byte - Format one 8-bit field as hex.
        """
        if not isinstance(value, (int, float)):
            return VIS_LAST_SEEN_UNKNOWN
        return f"0x{int(value) & 0xFF:02X}"

    def _format_visibility_hex_pgn(self, value: object) -> str:
        """
        NAME
            _format_visibility_hex_pgn - Format one candidate PGN value as hex.
        """
        if not isinstance(value, (int, float)):
            return VIS_LAST_SEEN_UNKNOWN
        return f"0x{int(value) & 0x3FFFF:05X}"

    def _on_visibility_row_double_click(self, _event: tk.Event) -> None:
        """
        NAME
            _on_visibility_row_double_click - Prompt to rename a discovered unexpected visibility row.
        """
        widget = _event.widget
        if not isinstance(widget, ttk.Treeview) or self._visibility_provider is None:
            return
        selection = widget.selection()
        if not selection:
            return
        meta = self._visibility_row_meta.get(selection[0], {})
        if not bool(meta.get(VIS_ROW_META_UNEXPECTED, False)):
            return
        old_label = str(meta.get(VIS_ROW_META_LABEL, NT_VALUE_EMPTY)).strip()
        if not old_label:
            return
        new_label = simpledialog.askstring(
            VIS_RENAME_DIALOG_TITLE,
            VIS_RENAME_PROMPT_FMT.format(label=old_label),
            parent=self,
            initialvalue=old_label,
        )
        if new_label is None:
            return
        clean_label = new_label.strip()
        if not clean_label:
            messagebox.showerror(VIS_RENAME_DIALOG_TITLE, VIS_RENAME_EMPTY_TEXT, parent=self)
            return
        if clean_label.lower() in self._profile_devices:
            messagebox.showerror(VIS_RENAME_DIALOG_TITLE, VIS_RENAME_DUPLICATE_TEXT, parent=self)
            return
        if not self._visibility_provider.rename_discovered_label(old_label, clean_label):
            messagebox.showerror(VIS_RENAME_DIALOG_TITLE, VIS_RENAME_FAILED_TEXT, parent=self)
            return
        self._append_output(
            VIS_RENAME_SUCCESS_FMT.format(old_label=old_label, new_label=clean_label)
        )
        self._visibility_last_update = 0.0
        self._poll_visibility_snapshot(time.time())

    def _on_visibility_row_selected(self, event: tk.Event) -> None:
        """
        NAME
            _on_visibility_row_selected - Update the CTRE raw decode panel from the selected visibility row.
        """
        widget = event.widget
        if not isinstance(widget, ttk.Treeview):
            return
        selection = widget.selection()
        if not selection:
            return
        meta = self._visibility_row_meta.get(selection[0], {})
        self._visibility_selected_label = str(
            meta.get(VIS_ROW_META_LABEL, NT_VALUE_EMPTY)
        ).strip()
        self._visibility_selected_unexpected = bool(
            meta.get(VIS_ROW_META_UNEXPECTED, False)
        )
        raw_ids = meta.get(VIS_ROW_META_RAW_IDS, [])
        self._populate_ctre_raw_table(raw_ids if isinstance(raw_ids, list) else [])

    def _populate_ctre_raw_table(self, raw_ids: List[Dict[str, object]]) -> None:
        """
        NAME
            _populate_ctre_raw_table - Render candidate J1939-style CTRE raw-ID rows for the selected visibility item.
        """
        if self._visibility_ctre_raw_table is None:
            return
        for row in self._visibility_ctre_raw_table.get_children():
            self._visibility_ctre_raw_table.delete(row)
        rows_written = 0
        for raw in raw_ids:
            if not isinstance(raw, dict):
                continue
            arb_hex = str(raw.get(VIS_KEY_ARB_HEX, NT_VALUE_EMPTY)).strip()
            if not arb_hex:
                continue
            values = [
                arb_hex,
                str(int(raw.get(VIS_KEY_MSG_COUNT, 0))) if isinstance(raw.get(VIS_KEY_MSG_COUNT), (int, float)) else VIS_PACKETS_UNKNOWN,
                self._format_visibility_rate_value(raw.get(VIS_KEY_FRAMES_PER_SEC)),
                self._format_visibility_small_int(raw.get(VIS_KEY_API_CLASS)),
                self._format_visibility_small_int(raw.get(VIS_KEY_API_INDEX)),
                self._format_visibility_small_int(raw.get(VIS_KEY_PRIORITY)),
                self._format_visibility_small_int(raw.get(VIS_KEY_RESERVED)),
                self._format_visibility_small_int(raw.get(VIS_KEY_DATA_PAGE)),
                self._format_visibility_hex_byte(raw.get(VIS_KEY_PF)),
                self._format_visibility_hex_byte(raw.get(VIS_KEY_PS)),
                self._format_visibility_hex_byte(raw.get(VIS_KEY_SA)),
                self._format_visibility_hex_pgn(raw.get(VIS_KEY_PGN)),
            ]
            self._visibility_ctre_raw_table.insert(VIS_TREE_ROOT, VIS_TREE_END, values=values)
            rows_written += 1
        if rows_written == 0:
            self._visibility_ctre_raw_table.insert(VIS_TREE_ROOT, VIS_TREE_END, values=[VIS_RAW_EMPTY_MESSAGE])

    def _update_visibility_summary(self, summary: Dict[str, object]) -> None:
        """
        NAME
            _update_visibility_summary - Update summary text for visibility.
        """
        if not isinstance(summary, dict):
            return
        sources = summary.get(VIS_KEY_SOURCES_COUNT)
        devices = summary.get(VIS_KEY_DEVICES_SHOWN)
        visible_all = summary.get(VIS_KEY_VISIBLE_ALL)
        visible_some = summary.get(VIS_KEY_VISIBLE_SOME)
        visible_none = summary.get(VIS_KEY_VISIBLE_NONE)
        if not all(isinstance(v, int) for v in [sources, devices, visible_all, visible_some, visible_none]):
            return
        self._visibility_summary_var.set(
            VIS_SUMMARY_FMT.format(
                sources=sources,
                devices=devices,
                all=visible_all,
                some=visible_some,
                none=visible_none,
            )
        )

    def _load_runtime_state_file(self) -> None:
        """
        NAME
            _load_runtime_state_file - Select a runtime-state JSON file.
        """
        path = filedialog.askopenfilename(
            title="Load Runtime State JSON",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        self._runtime_state_path = path
        self._runtime_state_path_mtime = None
        self._live_source_var.set(LIVE_SOURCE_FILE)
        self._reload_runtime_state_file()

    def _reload_runtime_state_file(self) -> None:
        """
        NAME
            _reload_runtime_state_file - Manually reload the runtime-state JSON file.
        """
        if not self._runtime_state_path:
            return
        try:
            payload = read_json(Path(self._runtime_state_path))
        except Exception:
            return
        if isinstance(payload, dict):
            self._apply_runtime_state_payload(payload)
            self._apply_presence_overrides_file(payload)

    def _apply_presence_overrides_file(self, payload: Dict[str, Any]) -> None:
        """
        NAME
            _apply_presence_overrides_file - Load presence overrides/timeline from file.
        """
        overrides: Dict[str, str] = {}
        raw_overrides = payload.get(PRESENCE_FILE_KEY_OVERRIDES)
        if isinstance(raw_overrides, dict):
            for label, value in raw_overrides.items():
                label_text = str(label).strip()
                value_text = str(value).strip()
                if label_text and value_text in PRESENCE_VALUES:
                    overrides[label_text.lower()] = value_text
        self._presence_overrides_file = overrides
        timeline: List[Dict[str, Any]] = []
        raw_timeline = payload.get(PRESENCE_FILE_KEY_TIMELINE)
        if isinstance(raw_timeline, list):
            for entry in raw_timeline:
                if not isinstance(entry, dict):
                    continue
                at_sec = entry.get(PRESENCE_FILE_KEY_AT_SEC)
                block = entry.get(PRESENCE_FILE_KEY_OVERRIDES_BLOCK)
                if not isinstance(at_sec, (int, float)) or not isinstance(block, dict):
                    continue
                mapped: Dict[str, str] = {}
                for label, value in block.items():
                    label_text = str(label).strip()
                    value_text = str(value).strip()
                    if label_text and value_text in PRESENCE_VALUES:
                        mapped[label_text.lower()] = value_text
                timeline.append({PRESENCE_FILE_KEY_AT_SEC: float(at_sec), PRESENCE_FILE_KEY_OVERRIDES_BLOCK: mapped})
        timeline.sort(
            key=lambda item: float(item.get(PRESENCE_FILE_KEY_AT_SEC, PRESENCE_TIME_NONE))
        )
        self._presence_timeline = timeline
        if timeline:
            max_at = max(
                float(item.get(PRESENCE_FILE_KEY_AT_SEC, PRESENCE_TIME_NONE))
                for item in timeline
            )
            prev_at = PRESENCE_TIME_NONE
            if len(timeline) > 1:
                prev_at = float(
                    timeline[-2].get(PRESENCE_FILE_KEY_AT_SEC, PRESENCE_TIME_NONE)
                )
            step = max(PRESENCE_TIMELINE_MIN_STEP, max_at - prev_at)
            if max_at <= PRESENCE_TIME_NONE:
                step = PRESENCE_TIMELINE_DEFAULT_STEP
            self._presence_timeline_period = max_at + step
            if self._presence_timeline_period <= PRESENCE_TIME_NONE:
                self._presence_timeline_period = PRESENCE_TIMELINE_DEFAULT_STEP
            self._presence_timeline_start = time.time()
        else:
            self._presence_timeline_start = PRESENCE_TIME_NONE
            self._presence_timeline_period = PRESENCE_TIME_NONE

    def _apply_runtime_state_rate(self) -> None:
        """
        NAME
            _apply_runtime_state_rate - Update the runtime-state polling rate.
        """
        try:
            rate = float(self._live_rate_var.get())
        except (TypeError, ValueError):
            rate = self._runtime_state_hz
        rate = max(self._live_rate_min, min(self._live_rate_max, rate))
        self._runtime_state_hz = rate
        self._runtime_state_interval = 1.0 / self._runtime_state_hz
        self._live_rate_var.set(f"{rate:g}")
        self._runtime_state_backoff = 1.0
        self._runtime_state_idle_count = 0
        self._runtime_state_pause_until = None

    def _apply_live_group_toggle(self) -> None:
        """
        NAME
            _apply_live_group_toggle - Toggle group overlays in the live view.
        """
        for live_view in self._iter_live_views():
            live_view.set_show_groups(self._live_groups_var.get())

    def _apply_visibility_mode_toggle(self) -> None:
        """
        NAME
            _apply_visibility_mode_toggle - Toggle visibility mode in the live view.
        """
        if self._live_view is not None:
            self._live_view.set_visibility_enabled(self._visibility_enabled_var.get())
        if self._visibility_live_view is not None:
            self._visibility_live_view.set_visibility_enabled(True)

    def _zoom_in(self) -> None:
        """
        NAME
            _zoom_in - Zoom in the live topology view.
        """
        for live_view in self._iter_live_views():
            live_view._nudge_zoom(0.1)

    def _zoom_out(self) -> None:
        """
        NAME
            _zoom_out - Zoom out the live topology view.
        """
        for live_view in self._iter_live_views():
            live_view._nudge_zoom(-0.1)

    def _zoom_reset(self) -> None:
        """
        NAME
            _zoom_reset - Reset zoom in the live topology view.
        """
        for live_view in self._iter_live_views():
            live_view._reset_zoom()

    def _fit_live_view(self) -> None:
        """
        NAME
            _fit_live_view - Fit live topology views to their current viewport.
        """
        for live_view in self._iter_live_views():
            live_view._fit_to_window()

    def _attach_tooltip(self, widget: tk.Widget, text: str) -> None:
        """
        NAME
            _attach_tooltip - Attach a hover tooltip to a widget.
        """
        if not text:
            return
        tip = tk.Toplevel(self)
        tip.withdraw()
        tip.overrideredirect(True)
        tip.attributes("-topmost", True)
        label = ttk.Label(
            tip,
            text=text,
            justify="left",
            padding=6,
            background="#f9fafb",
            foreground="#111827",
            relief="solid",
            borderwidth=1,
        )
        label.pack()

        def _show(_event=None) -> None:
            x = widget.winfo_rootx() + 18
            y = widget.winfo_rooty() + widget.winfo_height() + 6
            tip.geometry(f"+{x}+{y}")
            tip.deiconify()

        def _hide(_event=None) -> None:
            tip.withdraw()

        widget.bind("<Enter>", _show)
        widget.bind("<Leave>", _hide)

    def _command_visible(self, command: str) -> bool:
        """
        NAME
            _command_visible - Return whether a generated UI command should be shown.
        """
        if command == CMD_SHOW_RUNTIME_STATE:
            return True
        metadata = ACTIONS_BY_NAME.get(command, {})
        action_kind = str(
            metadata.get(INVENTORY_KEY_ACTION_KIND, ACTION_KIND_REMOTE_COMMAND)
        ).strip()
        if action_kind == ACTION_KIND_REMOTE_COMMAND and not bool(
            metadata.get("hostUiAllowed", True)
        ):
            return False
        return self._ui_command_prefs.get(command, bool(metadata.get("showInHostUi", True)))

    def _set_command_visibility(self, command: str, visible: bool) -> None:
        """
        NAME
            _set_command_visibility - Update and persist command visibility preference.
        """
        self._ui_command_prefs[command] = bool(visible)
        self._save_ui_command_prefs()
        self._render_action_buttons()

    def _set_show_visibility_tab_pref(self) -> None:
        """
        NAME
            _set_show_visibility_tab_pref - Persist the Visibility-tab preference and apply it.
        """
        self._ui_show_visibility_tab = bool(self._show_visibility_tab_var.get())
        self._save_ui_command_prefs()
        self._apply_visibility_tab_pref()

    def _set_show_wall_clock_pref(self) -> None:
        """
        NAME
            _set_show_wall_clock_pref - Persist the wall-clock preference and apply it.
        """
        self._ui_show_wall_clock = bool(self._show_wall_clock_var.get())
        self._save_ui_command_prefs()
        self._apply_wall_clock_visibility()

    def _apply_visibility_tab_pref(self) -> None:
        """
        NAME
            _apply_visibility_tab_pref - Show or hide the Visibility tab from the right notebook.
        """
        notebook = getattr(self, "_right_notebook", None)
        panel = getattr(self, "_visibility_panel", None)
        if notebook is None or panel is None:
            return
        tab_visible = bool(self._ui_show_visibility_tab)
        current_tabs = notebook.tabs()
        panel_id = str(panel)
        is_present = panel_id in current_tabs
        if tab_visible and not is_present:
            notebook.add(panel, text=VIS_TAB_LABEL)
        elif not tab_visible and is_present:
            notebook.forget(panel)

    def _apply_wall_clock_visibility(self) -> None:
        """
        NAME
            _apply_wall_clock_visibility - Show or hide the header wall clock.
        """
        frame = getattr(self, "_wall_clock_frame", None)
        if frame is None:
            return
        if self._ui_show_wall_clock:
            if not frame.winfo_manager():
                frame.pack(side="left", padx=(12, 0), before=self._pending_label)
        elif frame.winfo_manager():
            frame.pack_forget()

    def _save_ui_command_prefs(self) -> None:
        """
        NAME
            _save_ui_command_prefs - Persist command visibility preferences to disk.
        """
        path = _ui_prefs_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(
            path,
            {
                UI_PREFS_KEY_COMMANDS: self._ui_command_prefs,
                UI_PREFS_KEY_AUTO_SELECT_DEFAULT_PROFILE: self._ui_auto_select_default_profile,
                UI_PREFS_KEY_SHOW_VISIBILITY_TAB: self._ui_show_visibility_tab,
                UI_PREFS_KEY_SHOW_WALL_CLOCK: self._ui_show_wall_clock,
            },
        )

    def _render_action_buttons(self) -> None:
        """
        NAME
            _render_action_buttons - Rebuild action buttons from generated metadata and preferences.
        """
        panel = getattr(self, "_action_panel", None)
        if panel is None:
            return
        for child in panel.winfo_children():
            child.destroy()
        self._action_buttons = []
        self._action_buttons_by_command = {}
        self._reset_button = None
        for section, items in _action_sections():
            visible_items = [
                (label, command)
                for label, command in items
                if command and self._command_visible(command)
            ]
            if not visible_items:
                continue
            ttk.Label(panel, text=section, foreground="#5b6672").pack(
                anchor="w", pady=(8, 2)
            )
            for label, command in visible_items:
                btn = ttk.Button(
                    panel,
                    text=label,
                    command=(lambda c=command: self._on_action(c)),
                )
                self._action_buttons.append(btn)
                self._action_buttons_by_command[command] = btn
                self._attach_tooltip(btn, self._tooltip_text(command))
                btn.pack(fill="x", pady=2)
        canvas = getattr(self, "_actions_canvas", None)
        if canvas is not None:
            self.update_idletasks()
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.configure(width=panel.winfo_reqwidth())

    def _tooltip_text(self, command: str) -> str:
        """
        NAME
            _tooltip_text - Return a short tooltip for a command.
        """
        metadata = ACTIONS_BY_NAME.get(command, {})
        return str(metadata.get("uiDescription", "")).strip()

    def _show_help(self) -> None:
        """
        NAME
            _show_help - Display the bringup UI help window.
        """
        if hasattr(self, "_help_window") and self._help_window.winfo_exists():
            self._help_window.deiconify()
            self._help_window.lift()
            self._help_window.focus_set()
            return
        self._help_window = self._build_help_window()
        self._help_window.lift()
        self._help_window.focus_set()

    def _show_about(self) -> None:
        """
        NAME
            _show_about - Display the about dialog.
        """
        version = VERSIONS.get(VERSION_APP_NAME, "")
        version_line = format_version_line(VERSION_APP_NAME, version) if version else ""
        lines = [ABOUT_NAME, version_line, BUILD_TITLE, *build_lines(), ABOUT_DESCRIPTION, ABOUT_LAUNCH]
        body = ABOUT_SEPARATOR.join([line for line in lines if line])
        messagebox.showinfo(ABOUT_TITLE, body)

    def _toggle_color_key_window(self) -> None:
        """
        NAME
            _toggle_color_key_window - Open or close the live-topology color legend.
        """
        if hasattr(self, "_color_key_window") and self._color_key_window.winfo_exists():
            self._color_key_window.destroy()
            return
        self._color_key_window = self._build_color_key_window()
        self._color_key_window.lift()
        self._color_key_window.focus_set()

    def _build_color_key_window(self) -> tk.Toplevel:
        """
        NAME
            _build_color_key_window - Build the live-topology color legend window.
        """
        window = tk.Toplevel(self)
        window.title(COLOR_KEY_TITLE)
        window.geometry(COLOR_KEY_GEOMETRY)
        window.minsize(COLOR_KEY_MIN_WIDTH, COLOR_KEY_MIN_HEIGHT)
        window.protocol("WM_DELETE_WINDOW", window.destroy)

        body = ttk.Frame(window, padding=10)
        body.pack(fill="both", expand=True)

        self._add_color_key_section(
            body,
            COLOR_KEY_SECTION_PRESENCE,
            [
                (COLOR_KEY_PRESENCE_HIGH, COLOR_KEY_TEXT_PRESENCE_HIGH),
                (COLOR_KEY_PRESENCE_LOW, COLOR_KEY_TEXT_PRESENCE_LOW),
                (COLOR_KEY_PRESENCE_NONE, COLOR_KEY_TEXT_PRESENCE_NONE),
            ],
        )
        self._add_color_key_section(
            body,
            COLOR_KEY_SECTION_VISIBILITY,
            [
                (COLOR_KEY_VIS_ALL, COLOR_KEY_TEXT_VIS_ALL),
                (COLOR_KEY_VIS_SOME, COLOR_KEY_TEXT_VIS_SOME),
                (COLOR_KEY_VIS_NONE, COLOR_KEY_TEXT_VIS_NONE),
                (COLOR_KEY_VIS_UNKNOWN, COLOR_KEY_TEXT_VIS_UNKNOWN),
            ],
        )
        self._add_color_key_section(
            body,
            COLOR_KEY_SECTION_ANALYZER,
            [
                (COLOR_KEY_ANALYZER_OK, COLOR_KEY_TEXT_ANALYZER_OK),
                (COLOR_KEY_ANALYZER_UNKNOWN, COLOR_KEY_TEXT_ANALYZER_UNKNOWN),
            ],
        )
        ttk.Label(body, text=COLOR_KEY_TEXT_TIME_NOTE, wraplength=360, justify="left").pack(
            anchor="w", pady=(4, 0)
        )
        return window

    def _add_color_key_section(
        self,
        parent: tk.Widget,
        title: str,
        rows: List[Tuple[str, str]],
    ) -> None:
        """
        NAME
            _add_color_key_section - Add one titled section to the color legend window.
        """
        frame = ttk.LabelFrame(parent, text=title, padding=COLOR_KEY_SECTION_PAD)
        frame.pack(fill="x", pady=(0, 8))
        for color, text in rows:
            row = ttk.Frame(frame)
            row.pack(fill="x", pady=COLOR_KEY_ROW_PADY)
            tk.Label(
                row,
                text="   ",
                bg=color,
                width=COLOR_SWATCH_WIDTH,
                relief=COLOR_SWATCH_RELIEF,
                bd=COLOR_SWATCH_BORDER,
            ).pack(side="left", padx=(0, COLOR_KEY_ROW_PADX))
            ttk.Label(row, text=text, wraplength=300, justify="left").pack(side="left", fill="x", expand=True)

    def _build_help_window(self) -> tk.Toplevel:
        """
        NAME
            _build_help_window - Build the tabbed help window.
        """
        window = tk.Toplevel(self)
        window.title("Bringup Control Help")
        window.geometry("860x620")
        window.minsize(720, 520)

        notebook = ttk.Notebook(window)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        tabs = [
            ("Overview", self._build_help_text()),
            ("Profiles", self._build_profiles_help()),
            ("Reports", self._build_reports_help()),
            ("Tests", self._build_tests_help()),
            ("System", self._build_system_help()),
            ("Live Topology", self._build_live_help()),
            ("Troubleshooting", self._build_troubleshooting_help()),
        ]
        for title, text in tabs:
            frame = ttk.Frame(notebook)
            notebook.add(frame, text=title)
            text_widget = tk.Text(frame, wrap="word", state="normal")
            text_widget.insert("end", text)
            text_widget.configure(state="disabled")
            text_widget.pack(side="left", fill="both", expand=True, padx=6, pady=6)
            scroll = ttk.Scrollbar(frame, command=text_widget.yview)
            scroll.pack(side="right", fill="y")
            text_widget.configure(yscrollcommand=scroll.set)
        return window

    def _toggle_test_source_reference_window(self) -> None:
        """
        NAME
            _toggle_test_source_reference_window - Open or close the DSL reference popup.
        """
        if hasattr(self, "_test_source_reference_window") and self._test_source_reference_window.winfo_exists():
            self._test_source_reference_window.destroy()
            return
        self._test_source_reference_window = self._build_test_source_reference_window()
        self._test_source_reference_window.lift()
        self._test_source_reference_window.focus_set()

    def _build_test_source_reference_window(self) -> tk.Toplevel:
        """
        NAME
            _build_test_source_reference_window - Build the DSL reference popup.
        """
        window = tk.Toplevel(self)
        window.title(TEST_SOURCE_REFERENCE_TITLE)
        window.geometry(TEST_SOURCE_REFERENCE_GEOMETRY)
        window.resizable(False, False)
        window.protocol("WM_DELETE_WINDOW", window.destroy)

        body = ttk.Frame(window, padding=10)
        body.pack(fill="both", expand=True)
        text_widget = tk.Text(body, wrap="word", height=6, state="normal")
        text_widget.insert("end", TEST_SOURCE_REFERENCE_TEXT)
        text_widget.configure(state="disabled")
        text_widget.pack(fill="both", expand=True)
        return window

    def _build_help_text(self) -> str:
        """
        NAME
            _build_help_text - Build the Overview tab text.
        """
        lines = [
            "Purpose:",
            "  Send bringup commands to the roboRIO via NetworkTables (bringup/ui).",
            "",
            "Basics:",
            "  - Select a test from the dropdown to send selectTestByName.",
            "  - Use Actions to print reports or run tests.",
            "  - Output shows ACK/OUT messages from the robot.",
            "  - Live Topology tab shows read-only runtime overlays.",
            "",
            "Connection:",
            "  - Status shows NetworkTables link to the RIO.",
            "  - If disconnected, commands are blocked.",
            "",
            "Launch examples:",
            "  tools\\can_nt\\run_can_nt.cmd --ui",
            "  python tools\\can_nt\\can_nt_bridge.py --ui --rio 172.22.11.2",
        ]
        return "\n".join(lines)

    def _build_profiles_help(self) -> str:
        """
        NAME
            _build_profiles_help - Build the Profiles tab text.
        """
        lines = [
            "Purpose:",
            "  Manage selected profile, config sync, controlled activation, and incremental bringup.",
            "",
            "Toggle Profile:",
            "  Switches to the next profile defined in bringup_system.json.",
            "  The active profile controls which CAN IDs and labels the robot expects.",
            "  Use this before adding motors so commands target the correct devices.",
            "  If a profile has no devices, Add Motor/Add All will do nothing.",
            "  Output: ACK + OUT with the new profile name and device count.",
            "",
            "Profile Dropdown:",
            "  Selecting a profile updates the live topology view.",
            "  If the REST session is connected, it also selects that profile on the robot",
            "  (selection only; never activates runtime by itself).",
            "",
            "Push Config:",
            "  Sends the selected bringup_system.json file to the robot over REST.",
            "  This updates robot config and selects the currently chosen profile.",
            "  It does not activate runtime by default.",
            "",
            "Download Current Config:",
            "  Fetches the robot's current bringup_system.json over REST and saves it locally.",
            "  Use this to re-anchor the host UI to the robot's current config.",
            "",
            "Lifecycle Activate:",
            "  Activates the active-group controlled session on the robot.",
            "  Use this in enabled teleop before running motors.",
            "",
            "Lifecycle Deactivate:",
            "  Deactivates the current controlled session on the robot.",
            "",
            "Add Motor:",
            "  Adds the next motor from the selected profile to the incremental bringup list.",
            "  The bringup list is the set of devices that tests and reports use.",
            "  Use this to step through devices one at a time and confirm behavior.",
            "  If the same motor is already added, it will be skipped.",
            "  Output: ACK + OUT showing the device label and ID that was added.",
            "",
            "Add All Motors:",
            "  Adds every motor from the selected profile to the bringup list.",
            "  This is convenient but can start many devices at once during tests.",
            "  Prefer Add Motor for first bringup or when hardware is unverified.",
            "  Output: ACK + OUT listing all added devices (may stream in batches).",
            "",
            "Refresh:",
            "  Reloads bringup_system.json and updates the dropdown list.",
        ]
        return "\n".join(lines)

    def _refresh_profiles(self) -> None:
        """
        NAME
            _refresh_profiles - Reload profile names from bringup_system.json.
        """
        profile_names = _load_profiles() or []
        profiles = _selectable_profiles()
        current = self._selected_profile_name()
        self._profile_box["values"] = profiles
        if current in profiles:
            self._profile_box.set(current)
        else:
            self._profile_box.set(
                _startup_selected_profile(profile_names, self._ui_auto_select_default_profile)
            )
        self._last_selected_profile = self._selected_profile_name()
        self._apply_profile_selection(self._selected_profile_name(), reload_views=True)

    def _set_auto_select_default_profile_pref(self) -> None:
        """
        NAME
            _set_auto_select_default_profile_pref - Persist startup auto-select preference.
        """
        self._ui_auto_select_default_profile = bool(self._auto_select_default_profile_var.get())
        self._save_ui_command_prefs()

    def _refresh_tests_for_profile(self, profile_name: str) -> None:
        """
        NAME
            _refresh_tests_for_profile - Refresh tests dropdown for a profile.
        """
        name = _normalize_profile_name(profile_name)
        tests = _load_tests(name) or [PROFILE_NONE]
        self._sync_test_dropdown_values(tests)

    def _test_selection_boxes(self) -> List[ttk.Combobox]:
        """
        NAME
            _test_selection_boxes - Return all visible/invisible test-selection combobox widgets.
        """
        boxes: List[ttk.Combobox] = []
        for attr_name in ("_test_box", "_tests_tab_test_box"):
            box = getattr(self, attr_name, None)
            if box is not None:
                boxes.append(box)
        return boxes

    def _refresh_test_library_view(self, profile_name: object = None) -> None:
        """
        NAME
            _refresh_test_library_view - Refresh the dedicated Tests tab from local config.
        """
        if not hasattr(self, "_test_library_status_var"):
            return
        selected_profile = (
            self._selected_profile_name() if profile_name is None else _normalize_profile_name(profile_name)
        )
        try:
            query = LocalConfigQueryService()
            global_names = list_external_library_test_names()
            global_runnable_map = (
                query.external_library_test_runnable_map(selected_profile)
                if selected_profile != PROFILE_NONE
                else {}
            )
            config_names = query.global_test_names()
            profile_names = (
                query.profile_test_names(selected_profile)
                if selected_profile != PROFILE_NONE
                else []
            )
            config_runnable_map = (
                query.config_library_test_runnable_map(selected_profile)
                if selected_profile != PROFILE_NONE
                else {}
            )
            runnable_map = (
                query.profile_test_runnable_map(selected_profile)
                if selected_profile != PROFILE_NONE
                else {}
            )
            test_profile_devices = (
                query.profile_device_catalog(selected_profile)
                if selected_profile != PROFILE_NONE
                else {}
            )
            profile_set_name = (
                query.profile_test_set_name(selected_profile)
                if selected_profile != PROFILE_NONE
                else ""
            )
        except Exception as exc:
            self._test_profile_devices = {}
            self._replace_test_library_list(self._test_library_global_list, [], "")
            self._replace_test_library_list(self._test_library_config_list, [], "")
            self._replace_test_library_list(self._test_library_profile_list, [], "")
            self._refresh_test_library_available_devices()
            self._test_library_status_var.set(str(exc))
            return
        self._test_profile_devices = {
            str(label).strip().lower(): entry
            for label, entry in test_profile_devices.items()
            if isinstance(label, str) and label.strip() and isinstance(entry, dict)
        }
        current_global = self._selected_test_library_global_name()
        current_config = self._selected_test_library_config_name()
        current_profile = self._selected_test_library_profile_name()
        self._replace_test_library_list(
            self._test_library_global_list,
            [
                name if global_runnable_map.get(name, False) else name + TEST_LIBRARY_INVALID_SUFFIX
                for name in global_names
            ],
            current_global,
        )
        self._replace_test_library_list(
            self._test_library_config_list,
            [
                name if config_runnable_map.get(name, False) else name + TEST_LIBRARY_INVALID_SUFFIX
                for name in config_names
            ],
            current_config,
        )
        self._replace_test_library_list(
            self._test_library_profile_list,
            [
                name if runnable_map.get(name, False) else name + TEST_LIBRARY_INVALID_SUFFIX
                for name in profile_names
            ],
            current_profile,
        )
        self._refresh_test_library_available_devices()
        if selected_profile == PROFILE_NONE:
            self._test_library_status_var.set(TEST_LIBRARY_STATUS_EMPTY)
            self._load_selected_test_source()
            return
        self._test_library_status_var.set(
            TEST_LIBRARY_STATUS_FMT.format(
                profile=selected_profile,
                set_name=profile_set_name or TEST_LIBRARY_SET_NONE,
                profile_count=len(profile_names),
                runnable_count=sum(1 for value in runnable_map.values() if value),
                config_count=len(config_names),
                global_count=len(global_names),
            )
        )
        self._load_selected_test_source()

    def _replace_test_library_list(
        self,
        listbox: tk.Listbox,
        names: List[str],
        preferred_name: str,
    ) -> None:
        """
        NAME
            _replace_test_library_list - Replace one Tests-tab listbox while preserving selection when possible.
        """
        listbox.delete(0, tk.END)
        for entry in names:
            listbox.insert(tk.END, entry)
        selected_name = str(preferred_name or "").strip()
        if not selected_name:
            return
        for index, entry in enumerate(names):
            entry_name = str(entry or "").strip()
            if entry_name.endswith(TEST_LIBRARY_INVALID_SUFFIX):
                entry_name = entry_name[: -len(TEST_LIBRARY_INVALID_SUFFIX)].rstrip()
            if entry_name != selected_name:
                continue
            listbox.selection_clear(0, tk.END)
            listbox.selection_set(index)
            listbox.see(index)
            return

    def _select_test_library_profile_name(self, test_name: str) -> bool:
        """
        NAME
            _select_test_library_profile_name - Select one saved profile test by name in the Tests tab.
        """
        listbox = getattr(self, "_test_library_profile_list", None)
        if listbox is None:
            return False
        target = str(test_name or "").strip()
        if not target:
            return False
        count = int(listbox.size())
        for index in range(count):
            entry = str(listbox.get(index) or "").strip()
            if entry.endswith(TEST_LIBRARY_INVALID_SUFFIX):
                entry = entry[: -len(TEST_LIBRARY_INVALID_SUFFIX)].rstrip()
            if entry != target:
                continue
            listbox.selection_clear(0, tk.END)
            if hasattr(self, "_test_library_global_list"):
                self._test_library_global_list.selection_clear(0, tk.END)
            listbox.selection_set(index)
            listbox.see(index)
            self._load_selected_test_source()
            return True
        return False

    def _select_test_library_config_name(self, test_name: str) -> bool:
        """
        NAME
            _select_test_library_config_name - Select one config-library test by name in the Tests tab.
        """
        listbox = getattr(self, "_test_library_config_list", None)
        if listbox is None:
            return False
        target = str(test_name or "").strip()
        if not target:
            return False
        count = int(listbox.size())
        for index in range(count):
            entry = str(listbox.get(index) or "").strip()
            if entry.endswith(TEST_LIBRARY_INVALID_SUFFIX):
                entry = entry[: -len(TEST_LIBRARY_INVALID_SUFFIX)].rstrip()
            if entry != target:
                continue
            listbox.selection_clear(0, tk.END)
            if hasattr(self, "_test_library_global_list"):
                self._test_library_global_list.selection_clear(0, tk.END)
            if hasattr(self, "_test_library_profile_list"):
                self._test_library_profile_list.selection_clear(0, tk.END)
            listbox.selection_set(index)
            listbox.see(index)
            self._load_selected_test_source()
            return True
        return False

    def _selected_test_library_global_name(self) -> str:
        """
        NAME
            _selected_test_library_global_name - Return the selected global-library DSL test name.
        """
        listbox = self.__dict__.get("_test_library_global_list")
        if listbox is None:
            return ""
        selection = listbox.curselection()
        if not selection:
            return ""
        value = str(listbox.get(selection[0]) or "").strip()
        if value.endswith(TEST_LIBRARY_INVALID_SUFFIX):
            return value[: -len(TEST_LIBRARY_INVALID_SUFFIX)].rstrip()
        return value

    def _selected_test_library_config_name(self) -> str:
        """
        NAME
            _selected_test_library_config_name - Return the selected config-library DSL test name.
        """
        listbox = self.__dict__.get("_test_library_config_list")
        if listbox is None:
            return ""
        selection = listbox.curselection()
        if not selection:
            return ""
        value = str(listbox.get(selection[0]) or "").strip()
        if value.endswith(TEST_LIBRARY_INVALID_SUFFIX):
            return value[: -len(TEST_LIBRARY_INVALID_SUFFIX)].rstrip()
        return value

    def _selected_test_library_profile_name(self) -> str:
        """
        NAME
            _selected_test_library_profile_name - Return the selected profile-runnable DSL test name.
        """
        listbox = self.__dict__.get("_test_library_profile_list")
        if listbox is None:
            return ""
        selection = listbox.curselection()
        if not selection:
            return ""
        value = str(listbox.get(selection[0]) or "").strip()
        if value.endswith(TEST_LIBRARY_INVALID_SUFFIX):
            return value[: -len(TEST_LIBRARY_INVALID_SUFFIX)].rstrip()
        return value

    def _selected_test_library_entry(self) -> Tuple[str, str]:
        """
        NAME
            _selected_test_library_entry - Return the selected test name plus source scope.
        """
        profile_name = self._selected_test_library_profile_name()
        if profile_name:
            return (profile_name, "profile")
        config_name = self._selected_test_library_config_name()
        if config_name:
            return (config_name, "config")
        global_name = self._selected_test_library_global_name()
        if global_name:
            return (global_name, "global")
        return ("", "")

    def _sync_test_library_entry_to_selected_test(self, test_name: str) -> None:
        """
        NAME
            _sync_test_library_entry_to_selected_test - Align list selections and source editor to one authoritative selected test.
        """
        target = str(test_name or "").strip()
        if not target:
            return
        current_entry_name, _current_entry_scope = self._selected_test_library_entry()
        current_source_name = str(self.__dict__.get("_selected_test_source_name", "") or "").strip()
        if current_entry_name == target and current_source_name == target:
            return
        global_list = self.__dict__.get("_test_library_global_list")
        config_list = self.__dict__.get("_test_library_config_list")
        profile_list = self.__dict__.get("_test_library_profile_list")
        self._suppress_test_library_selection_change = True
        try:
            if global_list is not None:
                global_list.selection_clear(0, tk.END)
            if config_list is not None:
                config_list.selection_clear(0, tk.END)
            if profile_list is not None:
                profile_list.selection_clear(0, tk.END)
            selected = (
                self._restore_test_library_listbox_selection(profile_list, target)
                or self._restore_test_library_listbox_selection(config_list, target)
                or self._restore_test_library_listbox_selection(global_list, target)
            )
        finally:
            self._suppress_test_library_selection_change = False
        if selected:
            self._load_selected_test_source()

    def _test_source_has_unsaved_changes(self) -> bool:
        """
        NAME
            _test_source_has_unsaved_changes - Return whether the current editable source buffer differs from the saved source.
        """
        scope = str(getattr(self, "_selected_test_source_scope", "") or "").strip()
        if scope not in ("config", "profile"):
            return False
        original = str(getattr(self, "_selected_test_source_original", "") or "")
        return self._current_test_source_text() != original

    def _restore_selected_test_library_entry(self) -> None:
        """
        NAME
            _restore_selected_test_library_entry - Restore the prior test selection after a canceled switch.
        """
        name = str(getattr(self, "_selected_test_source_name", "") or "").strip()
        scope = str(getattr(self, "_selected_test_source_scope", "") or "").strip()
        if not name or not scope:
            return
        self._suppress_test_library_selection_change = True
        try:
            if hasattr(self, "_test_library_global_list"):
                self._test_library_global_list.selection_clear(0, tk.END)
            if hasattr(self, "_test_library_config_list"):
                self._test_library_config_list.selection_clear(0, tk.END)
            if hasattr(self, "_test_library_profile_list"):
                self._test_library_profile_list.selection_clear(0, tk.END)
            if scope == "profile":
                self._restore_test_library_listbox_selection(
                    getattr(self, "_test_library_profile_list", None),
                    name,
                )
            elif scope == "config":
                self._restore_test_library_listbox_selection(
                    getattr(self, "_test_library_config_list", None),
                    name,
                )
            elif scope == "global":
                self._restore_test_library_listbox_selection(
                    getattr(self, "_test_library_global_list", None),
                    name,
                )
        finally:
            self._suppress_test_library_selection_change = False

    def _restore_test_library_listbox_selection(self, listbox: object, target_name: str) -> bool:
        """
        NAME
            _restore_test_library_listbox_selection - Restore a listbox selection by test name without reloading the editor.
        """
        if listbox is None:
            return False
        target = str(target_name or "").strip()
        if not target:
            return False
        count = int(listbox.size())
        for index in range(count):
            entry = str(listbox.get(index) or "").strip()
            if entry.endswith(TEST_LIBRARY_INVALID_SUFFIX):
                entry = entry[: -len(TEST_LIBRARY_INVALID_SUFFIX)].rstrip()
            if entry != target:
                continue
            listbox.selection_set(index)
            listbox.see(index)
            return True
        return False

    def _confirm_test_source_switch(self) -> bool:
        """
        NAME
            _confirm_test_source_switch - Prompt to save, discard, or cancel when leaving a dirty test source buffer.
        """
        if not self._test_source_has_unsaved_changes():
            return True
        current_name = str(getattr(self, "_selected_test_source_name", "") or "").strip() or "test"
        answer = messagebox.askyesnocancel(
            TEST_SOURCE_SWITCH_TITLE,
            TEST_SOURCE_SWITCH_PROMPT_FMT.format(name=current_name),
            parent=self,
        )
        if answer is None:
            return False
        if answer:
            self._save_selected_test_source()
            return not self._test_source_has_unsaved_changes()
        return True

    def _on_test_library_global_selected(self, _event=None) -> None:
        """
        NAME
            _on_test_library_global_selected - Load selected global-library test source into the editor.
        """
        if getattr(self, "_suppress_test_library_selection_change", False):
            return
        if not self._confirm_test_source_switch():
            self._restore_selected_test_library_entry()
            return
        if hasattr(self, "_test_library_profile_list"):
            self._test_library_profile_list.selection_clear(0, tk.END)
        if hasattr(self, "_test_library_config_list"):
            self._test_library_config_list.selection_clear(0, tk.END)
        self._load_selected_test_source()
        self._apply_selected_test_name_from_ui(self._selected_test_library_global_name())

    def _on_test_library_config_selected(self, _event=None) -> None:
        """
        NAME
            _on_test_library_config_selected - Load selected config-library test source into the editor.
        """
        if getattr(self, "_suppress_test_library_selection_change", False):
            return
        if not self._confirm_test_source_switch():
            self._restore_selected_test_library_entry()
            return
        if hasattr(self, "_test_library_global_list"):
            self._test_library_global_list.selection_clear(0, tk.END)
        if hasattr(self, "_test_library_profile_list"):
            self._test_library_profile_list.selection_clear(0, tk.END)
        self._load_selected_test_source()
        test_name, _scope = self._selected_test_library_entry()
        self._apply_selected_test_name_from_ui(test_name)

    def _on_test_library_profile_selected(self, _event=None) -> None:
        """
        NAME
            _on_test_library_profile_selected - Load selected profile test source into the editor.
        """
        if getattr(self, "_suppress_test_library_selection_change", False):
            return
        if not self._confirm_test_source_switch():
            self._restore_selected_test_library_entry()
            return
        if hasattr(self, "_test_library_global_list"):
            self._test_library_global_list.selection_clear(0, tk.END)
        if hasattr(self, "_test_library_config_list"):
            self._test_library_config_list.selection_clear(0, tk.END)
        self._load_selected_test_source()
        test_name, _scope = self._selected_test_library_entry()
        self._apply_selected_test_name_from_ui(test_name)

    def _load_selected_test_source(self) -> None:
        """
        NAME
            _load_selected_test_source - Refresh the Tests-tab source editor from the current list selection.
        """
        if not hasattr(self, "_test_source_text"):
            return
        test_name, scope = self._selected_test_library_entry()
        if not test_name:
            self._set_test_source_editor(TEST_SOURCE_EMPTY, editable=False)
            self._selected_test_source_name = ""
            self._selected_test_source_scope = ""
            self._selected_test_source_original = TEST_SOURCE_EMPTY
            self._set_test_source_status(TEST_SOURCE_STATUS_NONE)
            self._set_test_source_buttons_enabled(False)
            self._clear_test_source_results()
            return
        try:
            payload = self._load_local_profiles_payload()
            store = robot_test_dsl_store_from_root_payload(payload)
        except Exception as exc:
            self._set_test_source_editor(TEST_SOURCE_EMPTY, editable=False)
            self._set_test_source_status(str(exc))
            self._set_test_source_buttons_enabled(False)
            self._set_test_source_results([str(exc)])
            return
        source_text = TEST_SOURCE_EMPTY
        editable = scope in ("config", "profile")
        if scope == "global":
            try:
                source_text = read_external_library_test_source(test_name)
            except Exception as exc:
                self._set_test_source_editor(TEST_SOURCE_EMPTY, editable=False)
                self._set_test_source_status(str(exc))
                self._set_test_source_buttons_enabled(False)
                self._set_test_source_results([str(exc)])
                return
        else:
            entry = store.tests_by_name.get(test_name)
            source_text = entry.source if isinstance(entry, object) and hasattr(entry, "source") else TEST_SOURCE_EMPTY
        self._set_test_source_editor(str(source_text or ""), editable=editable)
        self._selected_test_source_name = test_name
        self._selected_test_source_scope = scope
        self._selected_test_source_original = str(source_text or "")
        self._set_test_source_buttons_enabled(editable)
        self._clear_test_source_results()
        if editable:
            if scope == "config":
                self._set_test_source_status(TEST_SOURCE_STATUS_CONFIG_FMT.format(name=test_name))
            else:
                self._set_test_source_status(TEST_SOURCE_STATUS_PROFILE_FMT.format(name=test_name))
            return
        self._set_test_source_status(TEST_SOURCE_STATUS_GLOBAL_FMT.format(name=test_name))

    def _set_test_source_editor(self, text: str, *, editable: bool) -> None:
        """
        NAME
            _set_test_source_editor - Replace the DSL source editor contents and editability state.
        """
        widget = getattr(self, "_test_source_text", None)
        if widget is None:
            return
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", str(text or ""))
        widget.edit_modified(False)
        widget.configure(state="normal" if editable else "disabled")
        self._refresh_test_source_line_numbers()

    def _refresh_test_source_line_numbers(self, _event=None) -> None:
        """
        NAME
            _refresh_test_source_line_numbers - Redraw the source-editor line-number gutter.
        """
        text_widget = getattr(self, "_test_source_text", None)
        gutter = getattr(self, "_test_source_line_numbers", None)
        if text_widget is None or gutter is None:
            return
        try:
            line_count = int(text_widget.index("end-1c").split(".")[0])
        except Exception:
            line_count = 1
        gutter.configure(state="normal")
        gutter.delete("1.0", "end")
        gutter.insert("1.0", "\n".join(str(index) for index in range(1, line_count + 1)))
        gutter.configure(state="disabled")
        gutter.yview_moveto(text_widget.yview()[0])

    def _on_test_source_yscroll(self, first: str, last: str) -> None:
        """
        NAME
            _on_test_source_yscroll - Keep the source-editor scrollbar and line-number gutter in sync.
        """
        scrollbar = getattr(self, "_test_source_scrollbar", None)
        if scrollbar is not None:
            scrollbar.set(first, last)
        gutter = getattr(self, "_test_source_line_numbers", None)
        if gutter is not None:
            gutter.yview_moveto(float(first))

    def _on_test_source_scrollbar(self, *args) -> None:
        """
        NAME
            _on_test_source_scrollbar - Scroll the source editor and line-number gutter together.
        """
        text_widget = getattr(self, "_test_source_text", None)
        gutter = getattr(self, "_test_source_line_numbers", None)
        if text_widget is not None:
            text_widget.yview(*args)
        if gutter is not None:
            gutter.yview(*args)

    def _on_test_source_key_release(self, event=None) -> None:
        """
        NAME
            _on_test_source_key_release - Refresh source-editor line numbers and show/hide signal completion.
        """
        self._refresh_test_source_line_numbers()
        self._show_test_source_completion_popup()

    def _on_test_source_click_release(self, _event=None) -> None:
        """
        NAME
            _on_test_source_click_release - Refresh source-editor state and dismiss signal completion on cursor clicks.
        """
        self._refresh_test_source_line_numbers()
        self._hide_test_source_completion_popup()

    def _on_test_source_mousewheel(self, _event=None) -> None:
        """
        NAME
            _on_test_source_mousewheel - Dismiss completion during wheel scroll without rewriting editor state.
        """
        self._hide_test_source_completion_popup()

    def _on_test_source_configure(self, _event=None) -> None:
        """
        NAME
            _on_test_source_configure - Refresh line numbers and dismiss signal completion when the editor is reflowed.
        """
        self._refresh_test_source_line_numbers()
        self._hide_test_source_completion_popup()

    def _current_test_source_line_before_cursor(self) -> str:
        """
        NAME
            _current_test_source_line_before_cursor - Return the current source-editor line content up to the cursor.
        """
        widget = getattr(self, "_test_source_text", None)
        if widget is None:
            return ""
        try:
            return widget.get("insert linestart", "insert")
        except Exception:
            return ""

    def _test_source_completion_mode_for_line(self, line_text: str) -> str:
        """
        NAME
            _test_source_completion_mode_for_line - Classify the current DSL statement so completion only offers compatible signals.
        """
        normalized = str(line_text or "").lstrip().lower()
        if not normalized:
            return TEST_SOURCE_COMPLETION_MODE_NONE
        for prefix in TEST_SOURCE_COMPLETION_WRITE_PREFIXES:
            if normalized.startswith(prefix):
                return TEST_SOURCE_COMPLETION_MODE_WRITE
        for prefix in TEST_SOURCE_COMPLETION_READ_PREFIXES:
            if normalized.startswith(prefix):
                return TEST_SOURCE_COMPLETION_MODE_READ
        for prefix in TEST_SOURCE_COMPLETION_CLEAR_PREFIXES:
            if normalized.startswith(prefix):
                return TEST_SOURCE_COMPLETION_MODE_CLEAR
        return TEST_SOURCE_COMPLETION_MODE_NONE

    def _selected_profile_signal_names_for_device_label(self, label: str, mode: str) -> List[str]:
        """
        NAME
            _selected_profile_signal_names_for_device_label - Resolve DSL signal names for one selected-profile device label and statement mode.
        """
        clean_label = str(label or "").strip()
        if not clean_label:
            return []
        if mode not in (
            TEST_SOURCE_COMPLETION_MODE_READ,
            TEST_SOURCE_COMPLETION_MODE_WRITE,
            TEST_SOURCE_COMPLETION_MODE_CLEAR,
        ):
            return []
        device = self._test_profile_devices.get(clean_label.lower(), {})
        if not isinstance(device, dict):
            return []
        device_type = resolve_profile_device_dsl_type(device)
        if not device_type:
            return []
        catalog = robot_test_dsl_signal_catalog()
        signals = catalog.get(device_type)
        if not isinstance(signals, dict):
            return []
        capability_key = {
            TEST_SOURCE_COMPLETION_MODE_READ: "readable",
            TEST_SOURCE_COMPLETION_MODE_WRITE: "writable",
            TEST_SOURCE_COMPLETION_MODE_CLEAR: "clearable",
        }.get(mode, "")
        if not capability_key:
            return []
        resolved_names: List[str] = []
        for name, metadata in signals.items():
            signal_name = str(name or "").strip()
            if not signal_name or not isinstance(metadata, dict):
                continue
            if bool(metadata.get(capability_key, False)):
                resolved_names.append(signal_name)
        return sorted(resolved_names)

    def _source_completion_device_label_before_cursor(self) -> str:
        """
        NAME
            _source_completion_device_label_before_cursor - Extract the device label from a trailing device-reference prefix.
        """
        line_text = self._current_test_source_line_before_cursor()
        if not line_text:
            return ""
        match = re.search(TEST_SOURCE_COMPLETION_DEVICE_PATTERN, line_text)
        if match is None:
            return ""
        return str(match.group(1) or match.group(2) or "").strip()

    def _show_test_source_completion_popup(self) -> None:
        """
        NAME
            _show_test_source_completion_popup - Show a signal-completion popup for the device reference before the cursor.
        """
        mode = self._test_source_completion_mode_for_line(self._current_test_source_line_before_cursor())
        if not mode:
            self._hide_test_source_completion_popup()
            return
        label = self._source_completion_device_label_before_cursor()
        if not label:
            self._hide_test_source_completion_popup()
            return
        signals = self._selected_profile_signal_names_for_device_label(label, mode)
        display_signals = list(signals) if signals else [TEST_SOURCE_COMPLETION_EMPTY]
        widget = getattr(self, "_test_source_text", None)
        if widget is None or str(widget.cget("state")) == "disabled":
            self._hide_test_source_completion_popup()
            return
        bbox = widget.bbox("insert")
        if bbox is None:
            self._hide_test_source_completion_popup()
            return
        popup = getattr(self, "_test_source_completion_popup", None)
        if popup is not None and not popup.winfo_exists():
            popup = None
            self._test_source_completion_popup = None
            self._test_source_completion_list = None
        if popup is None:
            popup = tk.Toplevel(self)
            popup.title(TEST_SOURCE_COMPLETION_POPUP_TITLE)
            popup.transient(self)
            popup.resizable(False, False)
            listbox = tk.Listbox(popup, exportselection=False, height=min(8, len(display_signals)))
            listbox.pack(fill="both", expand=True)
            listbox.bind("<Double-1>", self._insert_selected_test_source_completion)
            self._test_source_completion_popup = popup
            self._test_source_completion_list = listbox
        listbox = getattr(self, "_test_source_completion_list", None)
        if listbox is None:
            return
        listbox.delete(0, tk.END)
        for signal_name in display_signals:
            listbox.insert(tk.END, signal_name)
        if display_signals:
            listbox.selection_clear(0, tk.END)
            listbox.selection_set(0)
        x, y, _width, height = bbox
        popup.geometry(f"+{widget.winfo_rootx() + x}+{widget.winfo_rooty() + y + height}")
        popup.deiconify()
        popup.lift()

    def _insert_selected_test_source_completion(self, _event=None) -> None:
        """
        NAME
            _insert_selected_test_source_completion - Insert the selected signal-completion token into the source editor.
        """
        listbox = getattr(self, "_test_source_completion_list", None)
        widget = getattr(self, "_test_source_text", None)
        if listbox is None or widget is None or str(widget.cget("state")) == "disabled":
            self._hide_test_source_completion_popup()
            return
        selection = listbox.curselection()
        if not selection:
            self._hide_test_source_completion_popup()
            return
        signal_name = str(listbox.get(selection[0]) or "").strip()
        if not signal_name or signal_name == TEST_SOURCE_COMPLETION_EMPTY:
            self._hide_test_source_completion_popup()
            return
        widget.insert("insert", signal_name)
        widget.focus_set()
        self._hide_test_source_completion_popup()
        self._refresh_test_source_line_numbers()

    def _hide_test_source_completion_popup(self) -> None:
        """
        NAME
            _hide_test_source_completion_popup - Hide the signal-completion popup when it is visible.
        """
        popup = getattr(self, "_test_source_completion_popup", None)
        if popup is None:
            return
        try:
            popup.withdraw()
        except tk.TclError:
            self._test_source_completion_popup = None
            self._test_source_completion_list = None

    def _set_test_source_status(self, text: str) -> None:
        """
        NAME
            _set_test_source_status - Update the source-editor status line.
        """
        if hasattr(self, "_test_source_status_var"):
            self._test_source_status_var.set(str(text or "").strip())

    def _set_test_source_buttons_enabled(self, enabled: bool) -> None:
        """
        NAME
            _set_test_source_buttons_enabled - Enable or disable source-editor mutation controls.
        """
        state = ["!disabled"] if enabled else ["disabled"]
        for attr_name in (
            "_test_source_save_button",
            "_test_source_revert_button",
            "_test_source_validate_button",
        ):
            button = getattr(self, attr_name, None)
            if button is not None:
                button.state(state)

    def _on_test_source_modified(self, _event=None) -> None:
        """
        NAME
            _on_test_source_modified - Mark the source-editor status when the current profile test has unsaved edits.
        """
        widget = getattr(self, "_test_source_text", None)
        if widget is None:
            return
        if not widget.edit_modified():
            return
        scope = getattr(self, "_selected_test_source_scope", "")
        if scope in ("config", "profile"):
            if scope == "config":
                base = TEST_SOURCE_STATUS_CONFIG_FMT.format(
                    name=getattr(self, "_selected_test_source_name", "")
                )
            else:
                base = TEST_SOURCE_STATUS_PROFILE_FMT.format(
                    name=getattr(self, "_selected_test_source_name", "")
                )
            self._set_test_source_status(base + TEST_SOURCE_STATUS_DIRTY_SUFFIX)
        widget.edit_modified(False)

    def _on_test_source_undo(self, _event=None) -> str | None:
        """
        NAME
            _on_test_source_undo - Undo one source-editor change when the editor is editable.
        """
        widget = getattr(self, "_test_source_text", None)
        if widget is None or str(widget.cget("state")) == "disabled":
            return None
        try:
            widget.edit_undo()
        except tk.TclError:
            return "break"
        self._refresh_test_source_line_numbers()
        return "break"

    def _on_test_source_redo(self, _event=None) -> str | None:
        """
        NAME
            _on_test_source_redo - Redo one source-editor change when the editor is editable.
        """
        widget = getattr(self, "_test_source_text", None)
        if widget is None or str(widget.cget("state")) == "disabled":
            return None
        try:
            widget.edit_redo()
        except tk.TclError:
            return "break"
        self._refresh_test_source_line_numbers()
        return "break"

    def _reload_selected_test_source(self) -> None:
        """
        NAME
            _reload_selected_test_source - Revert the source editor to the last saved DSL source.
        """
        self._load_selected_test_source()

    def _current_test_source_text(self) -> str:
        """
        NAME
            _current_test_source_text - Return the DSL source text currently shown in the editor.
        """
        widget = getattr(self, "_test_source_text", None)
        if widget is None:
            return ""
        return widget.get("1.0", "end-1c")

    def _validate_selected_test_source(self) -> None:
        """
        NAME
            _validate_selected_test_source - Validate the current editor contents for the selected editable test.
        """
        profile_name = self._selected_real_profile()
        test_name = str(getattr(self, "_selected_test_source_name", "") or "").strip()
        scope = str(getattr(self, "_selected_test_source_scope", "") or "").strip()
        self._clear_test_source_results()
        if scope not in ("config", "profile") or not test_name:
            self._append_output(TEST_SOURCE_EDIT_BLOCKED)
            self._append_test_output(TEST_SOURCE_EDIT_BLOCKED)
            self._append_test_source_result(TEST_SOURCE_EDIT_BLOCKED)
            return
        try:
            payload = self._load_local_profiles_payload()
        except Exception as exc:
            self._append_output(str(exc))
            self._append_test_output(str(exc))
            self._append_test_source_result(str(exc))
            return
        source_text = self._current_test_source_text()

        def _operation() -> object:
            try:
                if scope == "config":
                    return write_test_source_into_config_library(
                        payload,
                        profile_name,
                        test_name,
                        source_text,
                    )
                return update_test_source_in_root_payload(
                    payload,
                    profile_name,
                    test_name,
                    source_text,
                )
            except DslServiceError as exc:
                return exc

        outcome = self._run_blocking_status_operation(
            TEST_SOURCE_START_VALIDATE_FMT.format(name=test_name, profile=profile_name),
            _operation,
            include_test_output=True,
        )
        if isinstance(outcome, DslServiceError):
            self._append_output(str(outcome))
            self._append_test_output(str(outcome))
            self._append_test_source_result(str(outcome))
            return
        validation_text = render_validation_text(
            outcome.validation,
            robot_test_dsl_store_from_root_payload(payload),
            entries_override={test_name: outcome.entry},
        )
        for line in validation_text.splitlines():
            if line == "OK":
                continue
            self._append_output(line)
            self._append_test_output(line)
            self._append_test_source_result(line)
        if outcome.ok():
            status_text = TEST_SOURCE_STATUS_VALID_FMT.format(name=test_name)
            self._set_test_source_status(status_text)
            self._append_test_output(status_text)
            self._append_test_source_result(status_text)
            return
        self._set_test_source_status(TEST_SOURCE_STATUS_INVALID_FMT.format(name=test_name))
        self._append_test_output(TEST_SOURCE_STATUS_INVALID_FMT.format(name=test_name))
        self._append_test_source_result(TEST_SOURCE_STATUS_INVALID_FMT.format(name=test_name))

    def _save_selected_test_source(self) -> None:
        """
        NAME
            _save_selected_test_source - Save the current editor contents back into the selected editable test.
        """
        profile_name = self._selected_real_profile()
        test_name = str(getattr(self, "_selected_test_source_name", "") or "").strip()
        scope = str(getattr(self, "_selected_test_source_scope", "") or "").strip()
        self._clear_test_source_results()
        if scope not in ("config", "profile") or not test_name:
            self._append_output(TEST_SOURCE_EDIT_BLOCKED)
            self._append_test_output(TEST_SOURCE_EDIT_BLOCKED)
            self._append_test_source_result(TEST_SOURCE_EDIT_BLOCKED)
            return
        try:
            session = self._begin_local_profiles_edit()
        except Exception as exc:
            self._append_output(str(exc))
            self._append_test_output(str(exc))
            self._append_test_source_result(str(exc))
            return
        payload = session.to_payload()
        source_text = self._current_test_source_text()

        def _operation() -> object:
            try:
                if scope == "config":
                    result = write_test_source_into_config_library(
                        payload,
                        profile_name,
                        test_name,
                        source_text,
                    )
                else:
                    result = update_test_source_in_root_payload(
                        payload,
                        profile_name,
                        test_name,
                        source_text,
                    )
            except DslServiceError as exc:
                return exc
            session.mark_dirty()
            self._persist_local_profiles_edit(session)
            return result

        outcome = self._run_blocking_status_operation(
            TEST_SOURCE_START_SAVE_FMT.format(name=test_name, profile=profile_name),
            _operation,
            include_test_output=True,
        )
        if isinstance(outcome, DslServiceError):
            self._append_output(str(outcome))
            self._append_test_output(str(outcome))
            self._append_test_source_result(str(outcome))
            return
        validation_text = render_validation_text(
            outcome.validation,
            robot_test_dsl_store_from_root_payload(payload),
            entries_override={test_name: outcome.entry},
        )
        for line in validation_text.splitlines():
            if line == "OK":
                continue
            self._append_output(line)
            self._append_test_output(line)
            self._append_test_source_result(line)
        self._selected_test_source_original = outcome.entry.source
        self._set_test_source_editor(outcome.entry.source, editable=True)
        self._refresh_test_library_view(profile_name)
        self._refresh_tests_for_profile(profile_name)
        if scope == "config":
            self._select_test_library_config_name(test_name)
        else:
            self._select_test_library_profile_name(test_name)
        if outcome.ok():
            if scope == "config":
                saved_text = TEST_SOURCE_STATUS_CONFIG_SAVED_FMT.format(name=test_name)
            else:
                saved_text = TEST_SOURCE_STATUS_SAVED_FMT.format(name=test_name)
            self._set_test_source_status(saved_text)
            self._append_test_output(saved_text)
            self._append_test_source_result(saved_text)
            return
        if scope == "config":
            invalid_text = TEST_SOURCE_STATUS_CONFIG_SAVED_INVALID_FMT.format(name=test_name)
        else:
            invalid_text = TEST_SOURCE_STATUS_SAVED_INVALID_FMT.format(name=test_name)
        self._set_test_source_status(invalid_text)
        self._append_test_output(invalid_text)
        self._append_test_source_result(invalid_text)

    def _build_reports_help(self) -> str:
        """
        NAME
            _build_reports_help - Build the Reports tab text.
        """
        lines = [
            "Purpose:",
            "  Print robot-side summaries to the console output panel.",
            "  Reports are queued and streamed to avoid slowing the 20ms loop.",
            "",
            "State:",
            "  Prints current bringup state, active profile, selected test,",
            "  enabled/disabled status, and the current device list.",
            "  Use this as a quick sanity check before running tests.",
            "  Output: local robot data only.",
            "",
            "CAN Bus:",
            "  Prints local vendor API CAN status and recent frame activity.",
            "  This is robot-side vendor API data (not the PC sniffer).",
            "  Output: vendor API status, seen/missing device notes.",
            "",
            "NT Diagnostics:",
            "  Prints diagnostics from the PC CAN tool via bringup/diag.",
            "  Requires the PC sniffer to be running and connected.",
            "  Use this to verify CAN traffic when the robot can’t see it.",
            "  Output: PC sniffer status + per-device presence/age/count.",
            "",
            "Inputs:",
            "  Prints controller status and input bindings state.",
            "  Helpful to confirm button mappings and axis directions.",
            "  Output: detected controllers, raw axes/buttons, bind summary.",
            "",
            "Health:",
            "  Prints local device health summary (faults, temps, currents).",
            "  Uses vendor APIs for on-robot readings.",
            "  If a device is missing, it will be called out explicitly.",
            "  Output: per-device health rows and fault summaries.",
            "",
            "Dump:",
            "  Prints a full bringup report with device and test details.",
            "  This is the most verbose report and will stream in batches.",
            "  Output: full device list, test config, and status sections.",
            "",
            "Bindings:",
            "  Prints controller bindings and UI command mappings.",
            "  Use when you need to verify what each button triggers.",
            "  Output: button/axis mapping with command names.",
            "",
            "CANcoder:",
            "  Prints encoder details and health for configured encoders.",
            "  Includes device IDs, presence status, and recent readings.",
            "  Output: encoder IDs, absolute position, and health notes.",
            "",
            "Tests Info:",
            "  Prints details for the currently selected test.",
            "  Includes parameters like duty, time, and encoder settings.",
            "  Output: test parameters and resolved encoder/motor labels.",
            "",
            "Tests Overview:",
            "  Prints the test list with enabled/disabled status.",
            "  Also shows which test is selected and which is active.",
            "  Output: test index, name, enabled flag, status.",
        ]
        return "\n".join(lines)

    def _build_tests_help(self) -> str:
        """
        NAME
            _build_tests_help - Build the Tests tab text.
        """
        lines = [
            "Purpose:",
            "  Run scripted or fixed-output tests against added motors.",
            "  Tests act only on devices in the bringup list.",
            "",
            "Select Test Dropdown:",
            "  Sends selectTestByName when the selection changes.",
            "  The selected test is the one affected by Toggle Enabled and Run Selected.",
            "  Output: ACK + OUT confirming selected test.",
            "",
            "Toggle Enabled:",
            "  Enable or disable the selected scripted test.",
            "  Enabled tests are included when you run all tests.",
            "  Output: ACK + OUT indicating new enabled state.",
            "",
            "Run Selected:",
            "  Run the selected scripted test once.",
            "  Output will show ACK/OUT when the robot accepts and completes it.",
            "  Notes: test may take time; UI shows pending until OUT is received.",
            "",
            "Run All:",
            "  Run all enabled scripted tests in order.",
            "  Use this after verifying individual devices with Add Motor.",
            "  Output: streaming results per test; use Print Next to preview order.",
            "",
            "Print Next:",
            "  Prints the next test that would run in sequence.",
            "  Useful for confirming ordering and enabled/disabled state.",
            "  Output: next test name and index.",
            "",
            "CAN Sweep:",
            "  Uses vendor APIs to probe devices and report visibility.",
            "  This does not use the PC sniffer; it is robot-side polling.",
            "  Output: per-device seen/missing results.",
            "",
            "Manual Motor Control:",
            "  Use group bindings or explicit joystick/manual tests instead",
            "  of vendor-wide fixed-speed commands.",
            "  Group bindings keep the target motors explicit in config.",
        ]
        return "\n".join(lines)

    def _build_system_help(self) -> str:
        """
        NAME
            _build_system_help - Build the System tab text.
        """
        lines = [
            "Purpose:",
            "  System-wide controls not tied to a specific test.",
            "",
            "Toggle Dashboard:",
            "  Enables or disables dashboard reporting output.",
            "  Use to reduce console noise during focused testing.",
            "  Output: ACK + OUT confirming new dashboard mode.",
            "",
            "Clear Faults:",
            "  Clears latched motor faults using vendor APIs.",
            "  If faults reappear immediately, inspect wiring and power.",
            "  Output: ACK + OUT listing devices cleared or failures.",
            "",
            "Drive Axes Labels:",
            "  Left Drive (LY Axis) and Right Drive (RY Axis) are labels only.",
            "  They indicate which joystick axes are bound; no command is sent.",
        ]
        return "\n".join(lines)

    def _build_live_help(self) -> str:
        """
        NAME
            _build_live_help - Build the Live Topology tab text.
        """
        lines = [
            "Purpose:",
            "  Show live device presence and telemetry on the topology diagram.",
            "",
            "Enable Live Overlay:",
            "  Starts polling runtime state from the roboRIO REST command server.",
            "  Live overlay is read-only and does not send commands.",
            "",
            "Show Groups:",
            "  Toggles group boxes/labels from bridgeConfig by-profile groups.",
            "  Useful for visualizing CLI groups in the live view.",
            "",
            "Source:",
            "  - tcp: Fetch runtime state from the roboRIO REST server (default).",
            "  - file: Replay a saved JSON snapshot for offline testing.",
            "",
            "Rate:",
            "  Updates per second (default 5 Hz).",
            "  Higher rates add more REST traffic; keep it modest.",
        ]
        return "\n".join(lines)

    def _build_troubleshooting_help(self) -> str:
        """
        NAME
            _build_troubleshooting_help - Build the Troubleshooting tab text.
        """
        lines = [
            "Purpose:",
            "  Common issues and quick checks.",
            "",
            "No connection:",
            "  Verify --rio matches the roboRIO IP and the robot is powered.",
            "  Check that the driver station can see the robot on the network.",
            "",
            "Commands blocked:",
            "  The UI blocks commands when disconnected or waiting on ACK/OUT.",
            "  Wait for pending output or clear the robot state.",
            "  If the robot is disabled, enable to allow commands to run.",
            "",
            "NT Diagnostics empty:",
            "  Start the PC tool: tools\\can_nt\\run_can_nt.cmd --profile <profile>",
            "  Use --channel COMx if auto-detect fails.",
        ]
        return "\n".join(lines)

    def _append_output(self, line: str) -> None:
        """
        NAME
            _append_output - Append a line to the output log.
        """
        lines = self.__dict__.get("_lines")
        if lines is None:
            lines = []
            self._lines = lines
        lines.append(line)
        max_lines = int(self.__dict__.get("_max_lines", 200))
        if len(lines) > max_lines:
            self._lines = lines[-max_lines:]
        self._render_log_lines(self.__dict__.get("_output"), self._lines)

    def _append_test_output(self, line: str) -> None:
        """
        NAME
            _append_test_output - Append a line to the Tests-tab activity log.
        """
        line = _sanitize_stream_output_line(line)
        if not line.strip():
            return
        lines = self.__dict__.get("_test_lines")
        if lines is None:
            lines = []
            self._test_lines = lines
        lines.append(line)
        max_lines = int(self.__dict__.get("_max_lines", 200))
        if len(lines) > max_lines:
            self._test_lines = lines[-max_lines:]
        self._render_log_lines(self.__dict__.get("_test_output"), self._test_lines)

    def _render_log_lines(self, widget: Optional[tk.Text], lines: List[str]) -> None:
        """
        NAME
            _render_log_lines - Replace a text widget body with the provided log lines.
        """
        if widget is None:
            return
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("end", "\n".join(lines) + "\n")
        widget.see("end")
        widget.configure(state="disabled")

    def _set_test_source_results(self, lines: List[str]) -> None:
        """
        NAME
            _set_test_source_results - Replace the non-modal source validation popup contents.
        """
        clean_lines = [str(line) for line in lines if str(line).strip()]
        if not clean_lines:
            text_widget = getattr(self, "_test_source_results_popup_text", None)
            self._render_log_lines(text_widget, clean_lines)
            return
        popup = self._ensure_test_source_results_popup(show=True)
        if popup is None:
            return
        text_widget = getattr(self, "_test_source_results_popup_text", None)
        self._render_log_lines(text_widget, clean_lines)

    def _append_test_source_result(self, line: str) -> None:
        """
        NAME
            _append_test_source_result - Append one line to the non-modal source validation popup.
        """
        lines = getattr(self, "_test_source_result_lines", None)
        if lines is None:
            lines = []
            self._test_source_result_lines = lines
        if str(line or "").strip():
            lines.append(str(line))
        self._set_test_source_results(self._test_source_result_lines)

    def _clear_test_source_results(self) -> None:
        """
        NAME
            _clear_test_source_results - Clear the source validation popup contents without closing it.
        """
        self._test_source_result_lines = []
        self._set_test_source_results([])

    def _ensure_test_source_results_popup(self, *, show: bool) -> Optional[tk.Toplevel]:
        """
        NAME
            _ensure_test_source_results_popup - Create or refresh the non-modal source validation popup.
        """
        popup = getattr(self, "_test_source_results_popup", None)
        if popup is not None and not popup.winfo_exists():
            popup = None
            self._test_source_results_popup = None
            self._test_source_results_popup_text = None
        if popup is None:
            popup = tk.Toplevel(self)
            popup.title(TEST_SOURCE_RESULTS_TITLE)
            popup.geometry(TEST_SOURCE_RESULTS_GEOMETRY)
            popup.protocol("WM_DELETE_WINDOW", self._close_test_source_results_popup)
            popup.transient(self)
            body = ttk.Frame(popup, padding=8)
            body.pack(fill="both", expand=True)
            text_widget = tk.Text(
                body,
                height=TEST_SOURCE_RESULTS_HEIGHT,
                wrap="word",
                state="disabled",
            )
            text_widget.pack(side="left", fill="both", expand=True)
            scroll = ttk.Scrollbar(body, command=text_widget.yview)
            scroll.pack(side="right", fill="y")
            text_widget.configure(yscrollcommand=scroll.set)
            footer = ttk.Frame(popup, padding=(8, 0, 8, 8))
            footer.pack(fill="x")
            ttk.Button(
                footer,
                text=TEST_SOURCE_RESULTS_CLOSE,
                command=self._close_test_source_results_popup,
            ).pack(side="right")
            self._test_source_results_popup = popup
            self._test_source_results_popup_text = text_widget
        if show:
            popup.deiconify()
            popup.lift()
        return popup

    def _close_test_source_results_popup(self) -> None:
        """
        NAME
            _close_test_source_results_popup - Close the non-modal source validation popup.
        """
        popup = getattr(self, "_test_source_results_popup", None)
        if popup is None:
            return
        try:
            popup.destroy()
        finally:
            self._test_source_results_popup = None
            self._test_source_results_popup_text = None

    def _is_test_activity_command(self, name: object) -> bool:
        """
        NAME
            _is_test_activity_command - Return true when a command belongs in the Tests-tab activity log.
        """
        command = str(name or "").strip().lower()
        return command in TEST_ACTIVITY_COMMANDS

    def _is_test_activity_output_line(self, line: object) -> bool:
        """
        NAME
            _is_test_activity_output_line - Return true when one streamed output line belongs in the Tests-tab activity log.
        """
        text = _sanitize_stream_output_line(line).strip()
        if not text:
            return False
        return text.startswith(
            (
                TEST_OUTPUT_PREFIX_STARTED,
                TEST_OUTPUT_PREFIX_STARTED_LEGACY,
                TEST_OUTPUT_PREFIX_NAME,
                TEST_OUTPUT_PREFIX_RESULT,
                TEST_OUTPUT_PREFIX_RESULT_LEGACY,
                TEST_OUTPUT_PREFIX_RUN_ALL_COMPLETE,
            )
        )

    def _remember_out_line(self, line: str) -> None:
        """
        NAME
            _remember_out_line - Record an OUT line for deduplication.
        """
        if not line:
            return
        now = time.time()
        self._recent_out_lines[line] = now
        self._purge_out_lines(now)

    def _should_skip_out_line(self, line: str) -> bool:
        """
        NAME
            _should_skip_out_line - Return true if line should be deduped.
        """
        if not line:
            return True
        now = time.time()
        self._purge_out_lines(now)
        seen = self._recent_out_lines.get(line)
        if seen is None:
            return False
        return (now - seen) <= self._out_dedupe_window

    def _purge_out_lines(self, now: float) -> None:
        """
        NAME
            _purge_out_lines - Drop expired OUT lines from dedupe cache.
        """
        if not self._recent_out_lines:
            return
        cutoff = now - self._out_dedupe_window
        stale = [line for line, ts in self._recent_out_lines.items() if ts < cutoff]
        for line in stale:
            self._recent_out_lines.pop(line, None)

    def _notify_ui_failure(
        self,
        key: str,
        is_failing: bool,
        fail_message: str,
        recovery_message: str,
    ) -> None:
        """
        NAME
            _notify_ui_failure - Log throttled failure/recovery messages.
        """
        now = time.time()
        state = self._ui_failures.get(key)
        if state is None:
            state = {"active": False, "last_log": 0.0}
            self._ui_failures[key] = state
        if is_failing:
            if not state["active"] or (now - state["last_log"]) >= self._ui_fail_interval:
                self._append_output(f"{timestamp_hms()} {fail_message}")
                state["last_log"] = now
            state["active"] = True
        else:
            if state["active"]:
                self._append_output(f"{timestamp_hms()} {recovery_message}")
                state["active"] = False
                state["last_log"] = now
    
    def _clear_output(self) -> None:
        """
        NAME
            _clear_output - Clear the output log.
        """
        self._lines = []
        self._output.configure(state="normal")
        self._output.delete("1.0", "end")
        self._output.configure(state="disabled")

    def _clear_test_output(self) -> None:
        """
        NAME
            _clear_test_output - Clear the Tests-tab activity log.
        """
        self._test_lines = []
        test_output = getattr(self, "_test_output", None)
        if test_output is None:
            return
        test_output.configure(state="normal")
        test_output.delete("1.0", "end")
        test_output.configure(state="disabled")

    def _next_seq(self) -> int:
        """
        NAME
            _next_seq - Increment and return the command sequence.
        """
        self._seq += 1
        return self._seq

    def _send_tcp_command(self, name: str, args: Optional[Dict[str, Any]]) -> Optional[int]:
        """
        NAME
            _send_tcp_command - Send a command over the REST-backed session.
        """
        if not self._tcp_connected:
            return None
        self._session.set_client_id(self._client_id)
        seq = send_command(self._session, name, args or {})
        if seq is None:
            self._tcp_connected = False
        return seq

    def _request_runtime_state_refresh(self) -> None:
        """
        NAME
            _request_runtime_state_refresh - Force the next runtime-state poll and issue it immediately when possible.
        """
        self._runtime_state_backoff = 1.0
        self._runtime_state_idle_count = 0
        self._runtime_state_pause_until = None
        self._runtime_state_last_poll = 0.0
        self._runtime_state_pending_seq = None
        if not self._tcp_connected or not self._handshake_done:
            return
        if self._tracker.is_pending() or self._log_poll_inflight:
            return
        seq = show_runtime_state(self._session, json_output=True)
        if seq is not None:
            self._runtime_state_pending_seq = int(seq)
            self._runtime_state_pending_at = time.time()

    def _send_handshake(self, reset: bool, force: bool = False, log: bool = True) -> None:
        """
        NAME
            _send_handshake - Send a UI handshake command.
        """
        self._auto_connect_enabled = True
        if not self._tcp_connected:
            self._tcp_connected = connect(self._session)
        if not self._tcp_connected:
            return
        if self._tracker.is_pending() and not force:
            self._append_output("Busy: wait for current command to finish.")
            return
        if force and self._tracker.is_pending():
            self._append_output("Forcing UI session reset (clearing pending state).")
            self._tracker.clear_pending()
        payload = {"clientId": self._client_id, "reset": reset}
        if log:
            ts = timestamp_hms()
            label = "uiHandshake (reset)" if reset else "uiHandshake"
            self._append_output(f"{ts} CMD {label}")
        self._session.set_client_id(self._client_id)
        seq = send_tracked_command(
            self._session,
            self._tracker,
            "uiHandshake",
            payload,
            sender=lambda session, _name, _args: ui_handshake(session, self._client_id, reset),
            now=time.time(),
            retryable=False,
        )
        if seq is not None:
            self._last_sent_seq = seq
            self._handshake_inflight = True
            self._last_handshake_attempt = time.time()
            self._last_cmd = ("uiHandshake", payload)

    def _send_disconnect(self, force: bool = False) -> None:
        """
        NAME
            _send_disconnect - Release the UI lock on the robot.
        """
        self._auto_connect_enabled = False
        if not self._tcp_connected:
            return
        if self._tracker.is_pending() and not force:
            self._append_output("Busy: wait for current command to finish.")
            return
        if force and self._tracker.is_pending():
            self._append_output("Forcing UI disconnect (clearing pending state).")
            self._tracker.clear_pending()
        ts = timestamp_hms()
        self._append_output(f"{ts} CMD uiDisconnect")
        self._last_cmd = ("uiDisconnect", None)
        seq = send_tracked_command(
            self._session,
            self._tracker,
            "uiDisconnect",
            None,
            sender=lambda session, _name, _args: ui_disconnect(session),
            now=time.time(),
            retryable=False,
        )
        if seq is not None:
            self._last_sent_seq = seq

    def _send_monitor(self, enabled: bool) -> None:
        """
        NAME
            _send_monitor - Toggle protocol monitor publishing on the robot.
        """
        if not self._tcp_connected:
            return
        if self._tracker.is_pending():
            self._append_output("Busy: wait for current command to finish.")
            return
        label = "uiMonitorEnable" if enabled else "uiMonitorDisable"
        ts = timestamp_hms()
        self._append_output(f"{ts} CMD {label}")
        args = {"enabled": enabled}
        self._last_cmd = (label, args)
        seq = send_tracked_command(
            self._session,
            self._tracker,
            label,
            args,
            sender=lambda session, _name, _args: ui_monitor(session, enabled),
            now=time.time(),
        )
        if seq is not None:
            self._last_sent_seq = seq

    def _reconnect_ui_session(self) -> None:
        """
        NAME
            _reconnect_ui_session - Reconnect the REST session and issue a normal UI handshake.
        """
        self._owner_required = False
        self._handshake_done = False
        self._runtime_state_seen = False
        self._handshake_inflight = False
        self._last_handshake_attempt = 0.0
        self._session.reset_handshake()
        self._send_handshake(reset=True, force=True, log=True)

    def _dispatch_host_local_action(self, command: str) -> bool:
        """
        NAME
            _dispatch_host_local_action - Execute a host-local UI action.
        """
        if command == HOST_ACTION_RECONNECT_UI_SESSION:
            self._reconnect_ui_session()
            return True
        if command == HOST_ACTION_DSL_TEST_IMPORT:
            self._dsl_import_from_ui()
            return True
        if command == HOST_ACTION_DSL_TEST_VALIDATE:
            self._dsl_validate_from_ui()
            return True
        return False

    def _host_local_action_enabled(self, command: str) -> bool:
        """
        NAME
            _host_local_action_enabled - Return whether a host-local UI action should be enabled.
        """
        if command == HOST_ACTION_RECONNECT_UI_SESSION:
            return not self._tracker.is_pending()
        if command in (HOST_ACTION_DSL_TEST_IMPORT, HOST_ACTION_DSL_TEST_VALIDATE):
            return not self._tracker.is_pending()
        return not self._tracker.is_pending()

    def _retry_last_command(self) -> None:
        """
        NAME
            _retry_last_command - Retry the last command after recovery.
        """
        cmd = self._tracker.take_retry()
        if cmd is None:
            return
        name, args = cmd
        if not name or name in ("uiHandshake", "uiDisconnect"):
            return
        ts = timestamp_hms()
        self._append_output(f"{ts} RETRY {name}")
        if self._is_test_activity_command(name):
            self._append_test_output(f"{ts} RETRY {name}")
        seq = send_tracked_command(
            self._session,
            self._tracker,
            name,
            args,
            sender=lambda session, command_name, command_args: self._send_tcp_command(command_name, command_args),
            now=time.time(),
        )
        if seq is not None:
            self._last_sent_seq = seq

    def _on_action(self, command: Optional[str]) -> None:
        """
        NAME
            _on_action - Send a command when a button is pressed.
        """
        if not command:
            return
        metadata = ACTIONS_BY_NAME.get(command, {})
        action_kind = str(metadata.get(INVENTORY_KEY_ACTION_KIND, ACTION_KIND_REMOTE_COMMAND))
        if action_kind == ACTION_KIND_HOST_LOCAL:
            self._dispatch_host_local_action(command)
            return
        args_json = str(metadata.get(INVENTORY_KEY_UI_ARGS_JSON, "")).strip()
        args = json.loads(args_json) if args_json else None
        if command == "uiHandshake":
            reset = bool(args.get("reset")) if isinstance(args, dict) else False
            self._send_handshake(reset=reset, force=reset, log=True)
            return
        if command == "uiDisconnect":
            self._send_disconnect()
            return
        if command == "uiMonitorEnable":
            self._send_monitor(True)
            return
        if command == "uiMonitorDisable":
            self._send_monitor(False)
            return
        if not self._tcp_connected:
            self._append_output("Not connected: command blocked.")
            if self._is_test_activity_command(command):
                self._append_test_output("Not connected: command blocked.")
            return
        if self._tracker.is_pending():
            self._append_output("Busy: wait for current command to finish.")
            if self._is_test_activity_command(command):
                self._append_test_output("Busy: wait for current command to finish.")
            return
        ts = timestamp_hms()
        self._append_output(f"{ts} CMD {command}")
        if self._is_test_activity_command(command):
            self._append_test_output(f"{ts} CMD {command}")
        if str(command or "").strip().lower() == "activepresenceprobe":
            self._evidence_probe_pending = True
            self._evidence_probe_run_count += 1
            self.after_idle(self._refresh_evidence_view)
        self._last_cmd = (command, args)
        seq = send_tracked_command(
            self._session,
            self._tracker,
            command,
            args,
            sender=lambda session, command_name, command_args: send_command(session, command_name, command_args),
            now=time.time(),
        )
        if seq is not None:
            self._last_sent_seq = seq

    def _on_test_selected(self, _event=None) -> None:
        """
        NAME
            _on_test_selected - Send selectTestByName when dropdown changes.
        """
        name = str(self._selected_test_var.get() or "").strip()
        self._apply_selected_test_name_from_ui(name)

    def _clear_test_selection_ui(self) -> None:
        """
        NAME
            _clear_test_selection_ui - Clear selected-test UI state without mutating library contents.
        """
        self._selected_test_var.set(PROFILE_NONE)
        self._last_selected_test = PROFILE_NONE
        for attr_name in (
            "_test_library_global_list",
            "_test_library_config_list",
            "_test_library_profile_list",
        ):
            listbox = getattr(self, attr_name, None)
            if listbox is not None:
                listbox.selection_clear(0, tk.END)
        self._refresh_selected_test_scope_status()

    def _selected_test_inactive_reason(self) -> str:
        """
        NAME
            _selected_test_inactive_reason - Return the current selected-test readiness blocker.
        """
        selected_name = str(self._selected_test_var.get() or "").strip()
        if not selected_name or selected_name == PROFILE_NONE:
            return OUTPUT_NO_SELECTED_TEST
        rows = list(self.__dict__.get("_tests_active_group_rows", []))
        invalid_labels = [str(row.get("label", "")).strip() for row in rows if bool(row.get("invalid"))]
        if invalid_labels:
            return "missing resource/device - " + invalid_labels[0]
        runtime_block_reason = self._test_runtime_block_reason()
        if runtime_block_reason:
            return runtime_block_reason
        if not self._active_group_is_currently_active():
            return TEST_LIBRARY_STATUS_LOADED_NOT_ACTIVATED
        row = self._selected_test_row(selected_name)
        if not isinstance(row, dict):
            return "required devices unavailable"
        blocked_reason = str(row.get("blockedReason", "") or "").strip()
        if blocked_reason:
            return blocked_reason
        runnable_now = row.get("runnableNow")
        if isinstance(runnable_now, bool):
            return "" if runnable_now else "required devices unavailable"
        return ""

    def _test_runtime_block_reason(self) -> str:
        """
        NAME
            _test_runtime_block_reason - Return robot-state blocker text for activation/test execution.
        """
        if bool(self.__dict__.get("_robot_estopped_known", False)):
            return TEST_LIBRARY_STATUS_BLOCKED_ESTOP
        if not bool(self.__dict__.get("_robot_enabled_known", True)):
            return TEST_LIBRARY_STATUS_BLOCKED_DISABLED
        mode = str(self.__dict__.get("_robot_mode_known", "") or "").strip().lower()
        if mode and mode != "teleop":
            return TEST_LIBRARY_STATUS_BLOCKED_NOT_TELEOP
        return ""

    def _selected_test_row(self, selected_name: str) -> Optional[Dict[str, Any]]:
        """
        NAME
            _selected_test_row - Return the robot-published metadata row for one selected test.
        """
        if self._tests_table is None or not selected_name:
            return None
        total = int(self._tests_table.getEntry("totalCount").getDouble(0.0))
        rows = self._tests_table.getSubTable("rows")
        for i in range(total):
            row = rows.getSubTable(str(i))
            row_name = str(row.getEntry("name").getString("") or "").strip()
            if row_name != selected_name:
                continue
            raw_required = str(row.getEntry("requiredDevices").getString("") or "").strip()
            required_devices = (
                [part.strip() for part in raw_required.split(",") if part.strip()]
                if raw_required
                else []
            )
            return {
                "requiredDevices": required_devices,
                "runnableNow": row.getEntry("runnableNow").getBoolean(False),
                "blockedReason": str(row.getEntry("blockedReason").getString("") or "").strip(),
            }
        return None

    def _selected_test_ready(self) -> bool:
        """
        NAME
            _selected_test_ready - Return whether the current selected test is ready to run.
        """
        return self._selected_test_inactive_reason() == ""

    def _refresh_test_result_status(self) -> None:
        """
        NAME
            _refresh_test_result_status - Refresh the visible last-result summary in the Tests header.
        """
        result_var = self.__dict__.get("_last_result_text_var")
        result_label = self.__dict__.get("_last_result_label")
        if result_var is None:
            return
        result_text = TEST_LIBRARY_LAST_RESULT_DEFAULT
        result_color = TEST_RESULT_NEUTRAL_FG
        if self._tests_table is not None:
            run_state = str(self._tests_table.getEntry("runState").getString("") or "").strip()
            run_test = str(self._tests_table.getEntry("runTest").getString("") or "").strip()
            run_result = str(self._tests_table.getEntry("runResult").getString("") or "").strip()
            run_message = str(self._tests_table.getEntry("runMessage").getString("") or "").strip()
            if run_state == "running" and run_test:
                result_text = f"Last Result: RUNNING - {run_test}"
                result_color = TEST_RESULT_RUNNING_FG
            elif run_state == "passed" and run_test:
                detail = run_message or run_test
                result_text = f"Last Result: PASS - {detail}"
                result_color = TEST_RESULT_PASS_FG
            elif run_state == "failed" and run_test:
                detail = run_message or run_test
                result_text = f"Last Result: FAIL - {detail}"
                result_color = TEST_RESULT_FAIL_FG
            elif run_state in ("blocked", "aborted", "interrupted"):
                detail = run_message or run_test or run_state.upper()
                result_text = f"Last Result: {run_state.upper()} - {detail}"
                result_color = TEST_RESULT_FAIL_FG
            elif run_result and run_test:
                result_text = f"Last Result: {run_result} - {run_test}"
                result_color = (
                    TEST_RESULT_PASS_FG
                    if run_result.upper() == "PASS"
                    else TEST_RESULT_FAIL_FG
                )
        result_var.set(result_text)
        if result_label is not None:
            result_label.configure(foreground=result_color)

    def _refresh_tests_active_group_panel(self) -> None:
        """
        NAME
            _refresh_tests_active_group_panel - Render the Tests-tab read-only active-group rows.
        """
        listbox = getattr(self, "_tests_active_group_list", None)
        if listbox is None:
            return
        listbox.delete(0, tk.END)
        rows = list(self.__dict__.get("_tests_active_group_rows", []))
        if not rows:
            listbox.insert(tk.END, TEST_ACTIVE_GROUP_PANEL_EMPTY)
            return
        group_active = self._active_group_is_currently_active()
        for row in rows:
            label = str(row.get("label", "")).strip()
            if not label:
                continue
            statuses = [TEST_ACTIVE_GROUP_STATUS_ENABLED]
            if bool(row.get("locked")):
                statuses.append(TEST_ACTIVE_GROUP_STATUS_LOCKED)
            if bool(row.get("invalid")):
                statuses.append(TEST_ACTIVE_GROUP_STATUS_INVALID)
            runtime_device = self._runtime_device_for_label(label)
            instantiated = False
            if runtime_device:
                if bool(runtime_device.get("instantiated", False)):
                    instantiated = True
                elif str(label).strip().lower() in TEST_ACTIVE_GROUP_SINGLETON_LABELS:
                    instantiated = bool(runtime_device.get("testable", False))
            statuses.append(
                "instantiated" if group_active and instantiated else TEST_ACTIVE_GROUP_STATUS_NOT_ACTIVATED
            )
            reason = str(row.get("reason", "")).strip()
            line = f"{label} | " + " | ".join(statuses)
            if reason:
                line += f" | {reason}"
            listbox.insert(tk.END, line)

    def _refresh_selected_test_scope_status(self) -> None:
        """
        NAME
            _refresh_selected_test_scope_status - Refresh the Tests-tab selected-test readiness label.
        """
        status_var = self.__dict__.get("_selected_test_scope_status_var")
        headline_var = self.__dict__.get("_selected_test_scope_headline_var")
        if status_var is None:
            return
        panel_bg = TEST_SCOPE_PANEL_NEUTRAL_BG
        panel_fg = TEST_SCOPE_PANEL_NEUTRAL_FG
        inactive_reason = self._selected_test_inactive_reason()
        if inactive_reason:
            status_var.set(self._format_selected_test_scope_status_detail(inactive_reason))
            if headline_var is not None:
                if inactive_reason == OUTPUT_NO_SELECTED_TEST:
                    headline_var.set(TEST_SCOPE_PANEL_NO_SELECTION_HEADLINE)
                else:
                    headline_var.set(TEST_SCOPE_PANEL_INACTIVE_HEADLINE)
            if inactive_reason == OUTPUT_NO_SELECTED_TEST:
                panel_bg = TEST_SCOPE_PANEL_NEUTRAL_BG
                panel_fg = TEST_SCOPE_PANEL_NEUTRAL_FG
            else:
                panel_bg = TEST_SCOPE_PANEL_INACTIVE_BG
                panel_fg = TEST_SCOPE_PANEL_INACTIVE_FG
        else:
            status_var.set(TEST_LIBRARY_STATUS_READY)
            if headline_var is not None:
                headline_var.set(TEST_SCOPE_PANEL_READY_HEADLINE)
            panel_bg = TEST_SCOPE_PANEL_READY_BG
            panel_fg = TEST_SCOPE_PANEL_READY_FG
        self._apply_selected_test_scope_panel_colors(panel_bg, panel_fg)

    def _format_selected_test_scope_status_detail(self, inactive_reason: str) -> str:
        """
        NAME
            _format_selected_test_scope_status_detail - Convert one internal blocked reason into clearer operator guidance.
        """
        reason = str(inactive_reason or "").strip()
        if not reason:
            return TEST_LIBRARY_STATUS_READY
        if reason == OUTPUT_NO_SELECTED_TEST:
            return TEST_SCOPE_DETAIL_NO_SELECTION
        if reason == TEST_LIBRARY_STATUS_LOADED_NOT_ACTIVATED:
            return TEST_SCOPE_DETAIL_LOADED_NOT_ACTIVATED
        if reason == TEST_LIBRARY_STATUS_MANUAL_RESTORED:
            return TEST_SCOPE_DETAIL_MANUAL_RESTORED
        if reason == TEST_LIBRARY_STATUS_BLOCKED_ESTOP:
            return TEST_SCOPE_DETAIL_BLOCKED_ESTOP
        if reason == TEST_LIBRARY_STATUS_BLOCKED_DISABLED:
            return TEST_SCOPE_DETAIL_BLOCKED_DISABLED
        if reason == TEST_LIBRARY_STATUS_BLOCKED_NOT_TELEOP:
            return TEST_SCOPE_DETAIL_BLOCKED_NOT_TELEOP
        if reason.startswith("missing resource/device - "):
            missing = reason.split(" - ", 1)[1].strip()
            return TEST_SCOPE_DETAIL_MISSING_DEVICE_PREFIX + missing
        if reason == "required devices unavailable":
            return TEST_SCOPE_DETAIL_REQUIRED_UNAVAILABLE
        return TEST_LIBRARY_STATUS_INACTIVE_PREFIX + reason

    def _apply_selected_test_scope_panel_colors(self, background: str, foreground: str) -> None:
        """
        NAME
            _apply_selected_test_scope_panel_colors - Apply the current Tests-tab scope status panel colors.
        """
        panel = self.__dict__.get("_selected_test_scope_panel")
        if panel is not None:
            panel.configure(bg=background, highlightbackground=TEST_SCOPE_PANEL_BORDER)
        for attr_name in (
            "_selected_test_scope_title_label",
            "_selected_test_scope_headline_label",
            "_selected_test_scope_detail_label",
        ):
            label = self.__dict__.get(attr_name)
            if label is not None:
                label.configure(bg=background, fg=foreground)

    def _selected_real_profile(self) -> str:
        """
        NAME
            _selected_real_profile - Return the selected profile or empty string when none is selected.
        """
        name = self._selected_profile_name()
        return "" if name == PROFILE_NONE else name

    def _default_profiles_path(self) -> Path:
        """
        NAME
            _default_profiles_path - Return the canonical bringup_system.json path.
        """
        return ConfigRepository().canonical_path()

    def _load_local_profiles_payload(self) -> Dict[str, object]:
        """
        NAME
            _load_local_profiles_payload - Load the canonical local bringup_system.json payload.
        """
        return ConfigRepository().load_canonical().to_payload()

    def _begin_local_profiles_edit(self) -> ConfigEditSession:
        """
        NAME
            _begin_local_profiles_edit - Open a mutable edit session for canonical local bringup config.
        """
        return ConfigRepository().begin_canonical_edit()

    def _persist_local_profiles_payload(self, payload: Dict[str, object]) -> None:
        """
        NAME
            _persist_local_profiles_payload - Persist a local bringup_system.json payload with shared sync semantics.
        """
        session = ConfigRepository().begin_canonical_edit()
        session.to_payload().clear()
        session.to_payload().update(payload)
        session.mark_dirty()
        ConfigRepository().sync(session)

    def _persist_local_profiles_edit(self, session: ConfigEditSession) -> None:
        """
        NAME
            _persist_local_profiles_edit - Persist a mutable local config edit session through the shared repository.
        """
        ConfigRepository().sync(session)

    def _dsl_import_from_ui(self) -> None:
        """
        NAME
            _dsl_import_from_ui - Import a DSL source file into the selected profile test set from the UI.
        """
        profile_name = self._selected_real_profile()
        if not profile_name:
            self._append_output(DSL_OUTPUT_NO_PROFILE)
            self._append_test_output(DSL_OUTPUT_NO_PROFILE)
            return
        selected = filedialog.askopenfilename(
            title=DSL_DIALOG_IMPORT_NAME_TITLE,
            initialdir=str(self._default_profiles_path().parent),
            filetypes=DSL_FILE_TYPES,
        )
        if not selected:
            self._append_output(DSL_IMPORT_CANCELLED)
            self._append_test_output(DSL_IMPORT_CANCELLED)
            return
        selected_path = Path(selected)
        default_name = selected_path.stem.strip() or TEST_NAME_EMPTY
        test_name = simpledialog.askstring(
            DSL_DIALOG_IMPORT_NAME_TITLE,
            DSL_DIALOG_IMPORT_NAME_PROMPT,
            parent=self,
            initialvalue=default_name,
        )
        if test_name is None:
            self._append_output(DSL_IMPORT_CANCELLED)
            self._append_test_output(DSL_IMPORT_CANCELLED)
            return
        test_name = test_name.strip()
        if not test_name:
            self._append_output("DSL import blocked: test name is required.")
            self._append_test_output("DSL import blocked: test name is required.")
            return
        try:
            session = self._begin_local_profiles_edit()
        except Exception as exc:
            self._append_output(str(exc))
            self._append_test_output(str(exc))
            return
        payload = session.to_payload()
        def _operation() -> object:
            try:
                result = import_test_into_root_payload(
                    payload,
                    profile_name,
                    test_name,
                    selected_path,
                )
            except DslServiceError as exc:
                return exc
            session.mark_dirty()
            self._persist_local_profiles_edit(session)
            return result

        outcome = self._run_blocking_status_operation(
            DSL_IMPORT_PATH_FMT.format(path=str(selected_path)),
            _operation,
            include_test_output=True,
        )
        if isinstance(outcome, DslServiceError):
            self._append_output(str(outcome))
            self._append_test_output(str(outcome))
            return
        validation_text = render_validation_text(
            outcome.validation,
            robot_test_dsl_store_from_root_payload(payload),
            entries_override={test_name: outcome.entry},
        )
        if validation_text != "OK":
            for line in validation_text.splitlines():
                self._append_output(line)
                self._append_test_output(line)
        self._refresh_tests_for_profile(profile_name)
        self._refresh_test_library_view(profile_name)
        self._select_test_library_profile_name(test_name)
        if outcome.ok():
            self._append_output(DSL_IMPORT_SAVED_FMT)
            self._append_test_output(DSL_IMPORT_SAVED_FMT)
            return
        invalid_text = TEST_SOURCE_STATUS_SAVED_INVALID_FMT.format(name=test_name)
        self._append_output(invalid_text)
        self._append_test_output(invalid_text)

    def _create_new_test_from_ui(self) -> None:
        """
        NAME
            _create_new_test_from_ui - Create a new minimal profile-owned DSL test from the UI.
        """
        profile_name = self._selected_real_profile()
        if not profile_name:
            self._append_output(DSL_OUTPUT_NO_PROFILE)
            self._append_test_output(DSL_OUTPUT_NO_PROFILE)
            return
        test_name = simpledialog.askstring(
            DSL_DIALOG_CREATE_NAME_TITLE,
            DSL_DIALOG_CREATE_NAME_PROMPT,
            parent=self,
            initialvalue=TEST_LIBRARY_NAME_NEW_FMT.format(profile=profile_name),
        )
        if test_name is None:
            self._append_output(DSL_CREATE_CANCELLED)
            self._append_test_output(DSL_CREATE_CANCELLED)
            return
        test_name = test_name.strip()
        if not test_name:
            self._append_output(DSL_CREATE_NAME_REQUIRED)
            self._append_test_output(DSL_CREATE_NAME_REQUIRED)
            return
        try:
            session = self._begin_local_profiles_edit()
        except Exception as exc:
            self._append_output(str(exc))
            self._append_test_output(str(exc))
            return
        payload = session.to_payload()

        def _operation() -> object:
            try:
                result = create_blank_test_in_root_payload(
                    payload,
                    profile_name,
                    test_name,
                )
            except DslServiceError as exc:
                return exc
            session.mark_dirty()
            self._persist_local_profiles_edit(session)
            return result

        outcome = self._run_blocking_status_operation(
            DSL_CREATE_START_FMT.format(profile=profile_name, target=test_name),
            _operation,
            include_test_output=True,
        )
        if isinstance(outcome, DslServiceError):
            self._append_output(str(outcome))
            self._append_test_output(str(outcome))
            return
        validation_text = render_validation_text(
            outcome.validation,
            robot_test_dsl_store_from_root_payload(payload),
            entries_override={test_name: outcome.entry},
        )
        if validation_text != "OK":
            for line in validation_text.splitlines():
                self._append_output(line)
                self._append_test_output(line)
        self._refresh_tests_for_profile(profile_name)
        self._refresh_test_library_view(profile_name)
        self._select_test_library_profile_name(test_name)
        if outcome.ok():
            self._append_output(DSL_CREATE_SAVED_FMT)
            self._append_test_output(DSL_CREATE_SAVED_FMT)
            return
        invalid_text = TEST_SOURCE_STATUS_SAVED_INVALID_FMT.format(name=test_name)
        self._append_output(invalid_text)
        self._append_test_output(invalid_text)

    def _rename_selected_test_from_ui(self) -> None:
        """
        NAME
            _rename_selected_test_from_ui - Rename the selected DSL test in external-global or config-backed scope.
        """
        profile_name = self._selected_real_profile()
        source_name, scope = self._selected_test_library_entry()
        if not source_name:
            self._append_output(DSL_OUTPUT_NO_TEST)
            self._append_test_output(DSL_OUTPUT_NO_TEST)
            return
        target_name = simpledialog.askstring(
            DSL_DIALOG_RENAME_NAME_TITLE,
            DSL_DIALOG_RENAME_NAME_PROMPT,
            parent=self,
            initialvalue=source_name,
        )
        if target_name is None:
            self._append_output(DSL_RENAME_CANCELLED)
            self._append_test_output(DSL_RENAME_CANCELLED)
            return
        target_name = target_name.strip()
        if not target_name:
            self._append_output(DSL_RENAME_NAME_REQUIRED)
            self._append_test_output(DSL_RENAME_NAME_REQUIRED)
            return
        if scope == "global":
            def _operation() -> object:
                try:
                    return rename_external_library_test(source_name, target_name)
                except DslServiceError as exc:
                    return exc

            outcome = self._run_blocking_status_operation(
                DSL_RENAME_START_FMT.format(source=source_name, target=target_name),
                _operation,
                include_test_output=True,
            )
            if isinstance(outcome, DslServiceError):
                self._append_output(str(outcome))
                self._append_test_output(str(outcome))
                return
            self._refresh_test_library_view(profile_name)
            self._select_test_library_global_name(target_name)
            self._append_output(DSL_RENAME_SAVED_FMT)
            self._append_test_output(DSL_RENAME_SAVED_FMT)
            return
        try:
            session = self._begin_local_profiles_edit()
        except Exception as exc:
            self._append_output(str(exc))
            self._append_test_output(str(exc))
            return
        payload = session.to_payload()

        def _operation() -> object:
            try:
                entry = rename_test_in_root_payload(payload, source_name, target_name)
            except DslServiceError as exc:
                return exc
            session.mark_dirty()
            self._persist_local_profiles_edit(session)
            return entry

        outcome = self._run_blocking_status_operation(
            DSL_RENAME_START_FMT.format(source=source_name, target=target_name),
            _operation,
            include_test_output=True,
        )
        if isinstance(outcome, DslServiceError):
            self._append_output(str(outcome))
            self._append_test_output(str(outcome))
            return
        self._refresh_tests_for_profile(profile_name)
        self._refresh_test_library_view(profile_name)
        if scope == "config":
            self._select_test_library_config_name(target_name)
        else:
            self._select_test_library_profile_name(target_name)
        self._append_output(DSL_RENAME_SAVED_FMT)
        self._append_test_output(DSL_RENAME_SAVED_FMT)

    def _delete_selected_test_from_ui(self) -> None:
        """
        NAME
            _delete_selected_test_from_ui - Archive and delete the selected DSL test from the selected scope.
        """
        profile_name = self._selected_real_profile()
        test_name, scope = self._selected_test_library_entry()
        if not test_name:
            self._append_output(DSL_OUTPUT_NO_TEST)
            self._append_test_output(DSL_OUTPUT_NO_TEST)
            return
        if not messagebox.askyesno(
            TEST_SOURCE_SWITCH_TITLE,
            f"Delete and archive test {test_name}?",
            parent=self,
        ):
            return
        if scope == "global":
            def _operation() -> object:
                try:
                    return delete_external_library_test(test_name)
                except DslServiceError as exc:
                    return exc

            outcome = self._run_blocking_status_operation(
                DSL_DELETE_START_FMT.format(name=test_name),
                _operation,
                include_test_output=True,
            )
            if isinstance(outcome, DslServiceError):
                self._append_output(str(outcome))
                self._append_test_output(str(outcome))
                return
            self._refresh_test_library_view(profile_name)
            self._append_output(DSL_DELETE_SAVED_FMT.format(path=str(outcome)))
            self._append_test_output(DSL_DELETE_SAVED_FMT.format(path=str(outcome)))
            return
        try:
            session = self._begin_local_profiles_edit()
        except Exception as exc:
            self._append_output(str(exc))
            self._append_test_output(str(exc))
            return
        payload = session.to_payload()

        def _operation() -> object:
            try:
                archive_path = delete_test_from_root_payload(payload, test_name)
            except DslServiceError as exc:
                return exc
            session.mark_dirty()
            self._persist_local_profiles_edit(session)
            return archive_path

        outcome = self._run_blocking_status_operation(
            DSL_DELETE_START_FMT.format(name=test_name),
            _operation,
            include_test_output=True,
        )
        if isinstance(outcome, DslServiceError):
            self._append_output(str(outcome))
            self._append_test_output(str(outcome))
            return
        self._refresh_tests_for_profile(profile_name)
        self._refresh_test_library_view(profile_name)
        self._append_output(DSL_DELETE_SAVED_FMT.format(path=str(outcome)))
        self._append_test_output(DSL_DELETE_SAVED_FMT.format(path=str(outcome)))

    def _dsl_import_global_from_ui(self) -> None:
        """
        NAME
            _dsl_import_global_from_ui - Import a DSL source file into the external shared global library.
        """
        selected = filedialog.askopenfilename(
            title=DSL_DIALOG_IMPORT_NAME_TITLE,
            initialdir=str(self._default_profiles_path().parent),
            filetypes=DSL_FILE_TYPES,
        )
        if not selected:
            self._append_output(DSL_IMPORT_CANCELLED)
            self._append_test_output(DSL_IMPORT_CANCELLED)
            return
        selected_path = Path(selected)
        default_name = selected_path.stem.strip() or TEST_NAME_EMPTY
        test_name = simpledialog.askstring(
            DSL_DIALOG_IMPORT_NAME_TITLE,
            DSL_DIALOG_IMPORT_NAME_PROMPT,
            parent=self,
            initialvalue=default_name,
        )
        if test_name is None:
            self._append_output(DSL_IMPORT_CANCELLED)
            self._append_test_output(DSL_IMPORT_CANCELLED)
            return
        test_name = test_name.strip()
        if not test_name:
            self._append_output("DSL import blocked: test name is required.")
            self._append_test_output("DSL import blocked: test name is required.")
            return

        def _operation() -> object:
            try:
                return import_test_into_external_library(test_name, selected_path)
            except DslServiceError as exc:
                return exc

        outcome = self._run_blocking_status_operation(
            DSL_IMPORT_GLOBAL_PATH_FMT.format(path=str(selected_path)),
            _operation,
            include_test_output=True,
        )
        if isinstance(outcome, DslServiceError):
            self._append_output(str(outcome))
            self._append_test_output(str(outcome))
            return
        self._refresh_test_library_view(self._selected_real_profile())
        self._select_test_library_global_name(test_name)
        self._append_output(DSL_IMPORT_GLOBAL_SAVED_FMT)
        self._append_test_output(DSL_IMPORT_GLOBAL_SAVED_FMT)

    def _dsl_import_to_config_from_ui(self) -> None:
        """
        NAME
            _dsl_import_to_config_from_ui - Import a DSL source file into the config-scoped shared library.
        """
        profile_name = self._selected_real_profile()
        if not profile_name:
            self._append_output(DSL_OUTPUT_NO_PROFILE)
            self._append_test_output(DSL_OUTPUT_NO_PROFILE)
            return
        selected = filedialog.askopenfilename(
            title=DSL_DIALOG_IMPORT_NAME_TITLE,
            initialdir=str(self._default_profiles_path().parent),
            filetypes=DSL_FILE_TYPES,
        )
        if not selected:
            self._append_output(DSL_IMPORT_CANCELLED)
            self._append_test_output(DSL_IMPORT_CANCELLED)
            return
        selected_path = Path(selected)
        default_name = selected_path.stem.strip() or TEST_NAME_EMPTY
        test_name = simpledialog.askstring(
            DSL_DIALOG_IMPORT_NAME_TITLE,
            DSL_DIALOG_IMPORT_NAME_PROMPT,
            parent=self,
            initialvalue=default_name,
        )
        if test_name is None:
            self._append_output(DSL_IMPORT_CANCELLED)
            self._append_test_output(DSL_IMPORT_CANCELLED)
            return
        test_name = test_name.strip()
        if not test_name:
            self._append_output("DSL import blocked: test name is required.")
            self._append_test_output("DSL import blocked: test name is required.")
            return
        try:
            session = self._begin_local_profiles_edit()
        except Exception as exc:
            self._append_output(str(exc))
            self._append_test_output(str(exc))
            return
        payload = session.to_payload()

        def _operation() -> object:
            try:
                result = import_test_into_config_library(
                    payload,
                    profile_name,
                    test_name,
                    selected_path,
                )
            except DslServiceError as exc:
                return exc
            session.mark_dirty()
            self._persist_local_profiles_edit(session)
            return result

        outcome = self._run_blocking_status_operation(
            DSL_IMPORT_CONFIG_PATH_FMT.format(path=str(selected_path), profile=profile_name),
            _operation,
            include_test_output=True,
        )
        if isinstance(outcome, DslServiceError):
            self._append_output(str(outcome))
            self._append_test_output(str(outcome))
            if str(outcome).startswith(DSL_COPY_DUPLICATE_PREFIX):
                self._refresh_test_library_view(profile_name)
                if self._select_test_library_profile_name(target_name):
                    message = DSL_COPY_DUPLICATE_REVEAL_FMT.format(name=target_name)
                    self._append_output(message)
                    self._append_test_output(message)
            return
        validation_text = render_validation_text(
            outcome.validation,
            robot_test_dsl_store_from_root_payload(payload),
            entries_override={test_name: outcome.entry},
        )
        if validation_text != "OK":
            for line in validation_text.splitlines():
                self._append_output(line)
                self._append_test_output(line)
        self._refresh_tests_for_profile(profile_name)
        self._refresh_test_library_view(profile_name)
        self._select_test_library_config_name(test_name)
        if outcome.ok():
            self._append_output(DSL_IMPORT_CONFIG_SAVED_FMT)
            self._append_test_output(DSL_IMPORT_CONFIG_SAVED_FMT)
            return
        invalid_text = TEST_SOURCE_STATUS_CONFIG_SAVED_INVALID_FMT.format(name=test_name)
        self._append_output(invalid_text)
        self._append_test_output(invalid_text)

    def _copy_selected_test_to_config_from_ui(self) -> None:
        """
        NAME
            _copy_selected_test_to_config_from_ui - Copy the selected external global-library DSL test into config scope.
        """
        profile_name = self._selected_real_profile()
        if not profile_name:
            self._append_output(DSL_OUTPUT_NO_PROFILE)
            self._append_test_output(DSL_OUTPUT_NO_PROFILE)
            return
        source_name = self._selected_test_library_global_name()
        if not source_name:
            self._append_output(DSL_OUTPUT_NO_GLOBAL_TEST)
            self._append_test_output(DSL_OUTPUT_NO_GLOBAL_TEST)
            return
        default_name = TEST_LIBRARY_NAME_COPY_FMT.format(profile=profile_name, name=source_name)
        target_name = simpledialog.askstring(
            DSL_DIALOG_COPY_NAME_TITLE,
            DSL_DIALOG_COPY_NAME_PROMPT,
            parent=self,
            initialvalue=default_name,
        )
        if target_name is None:
            self._append_output(DSL_COPY_CANCELLED)
            self._append_test_output(DSL_COPY_CANCELLED)
            return
        target_name = target_name.strip()
        if not target_name:
            self._append_output(DSL_COPY_NAME_REQUIRED)
            self._append_test_output(DSL_COPY_NAME_REQUIRED)
            return
        try:
            session = self._begin_local_profiles_edit()
        except Exception as exc:
            self._append_output(str(exc))
            self._append_test_output(str(exc))
            return
        payload = session.to_payload()

        def _operation() -> object:
            try:
                result = copy_external_library_test_into_root_payload(
                    payload,
                    profile_name,
                    source_name,
                    target_name,
                    destination="config",
                )
            except DslServiceError as exc:
                return exc
            session.mark_dirty()
            self._persist_local_profiles_edit(session)
            return result

        outcome = self._run_blocking_status_operation(
            DSL_COPY_GLOBAL_CONFIG_FMT.format(
                source=source_name,
                profile=profile_name,
                target=target_name,
            ),
            _operation,
            include_test_output=True,
        )
        if isinstance(outcome, DslServiceError):
            self._append_output(str(outcome))
            self._append_test_output(str(outcome))
            return
        validation_text = render_validation_text(
            outcome.validation,
            robot_test_dsl_store_from_root_payload(payload),
            entries_override={target_name: outcome.entry},
        )
        if validation_text != "OK":
            for line in validation_text.splitlines():
                self._append_output(line)
                self._append_test_output(line)
        self._refresh_tests_for_profile(profile_name)
        self._refresh_test_library_view(profile_name)
        self._select_test_library_config_name(target_name)
        if outcome.ok():
            self._append_output(DSL_COPY_CONFIG_SAVED_FMT)
            self._append_test_output(DSL_COPY_CONFIG_SAVED_FMT)
            return
        invalid_text = TEST_SOURCE_STATUS_CONFIG_SAVED_INVALID_FMT.format(name=target_name)
        self._append_output(invalid_text)
        self._append_test_output(invalid_text)

    def _copy_selected_test_to_profile_from_ui(self) -> None:
        """
        NAME
            _copy_selected_test_to_profile_from_ui - Copy the selected global/config DSL test into the selected profile.
        """
        profile_name = self._selected_real_profile()
        if not profile_name:
            self._append_output(DSL_OUTPUT_NO_PROFILE)
            self._append_test_output(DSL_OUTPUT_NO_PROFILE)
            return
        source_name, scope = self._selected_test_library_entry()
        if scope == "profile":
            self._append_output(DSL_OUTPUT_NO_CONFIG_TEST)
            self._append_test_output(DSL_OUTPUT_NO_CONFIG_TEST)
            return
        if scope == "global":
            no_selection_text = DSL_OUTPUT_NO_GLOBAL_TEST
        elif scope == "config":
            no_selection_text = DSL_OUTPUT_NO_CONFIG_TEST
        else:
            no_selection_text = DSL_OUTPUT_NO_GLOBAL_TEST
        if not source_name or scope not in ("global", "config"):
            self._append_output(no_selection_text)
            self._append_test_output(no_selection_text)
            return
        default_name = TEST_LIBRARY_NAME_COPY_FMT.format(profile=profile_name, name=source_name)
        target_name = simpledialog.askstring(
            DSL_DIALOG_COPY_NAME_TITLE,
            DSL_DIALOG_COPY_NAME_PROMPT,
            parent=self,
            initialvalue=default_name,
        )
        if target_name is None:
            self._append_output(DSL_COPY_CANCELLED)
            self._append_test_output(DSL_COPY_CANCELLED)
            return
        target_name = target_name.strip()
        if not target_name:
            self._append_output(DSL_COPY_NAME_REQUIRED)
            self._append_test_output(DSL_COPY_NAME_REQUIRED)
            return
        try:
            session = self._begin_local_profiles_edit()
        except Exception as exc:
            self._append_output(str(exc))
            self._append_test_output(str(exc))
            return
        payload = session.to_payload()

        def _operation() -> object:
            try:
                if scope == "global":
                    result = copy_external_library_test_into_root_payload(
                        payload,
                        profile_name,
                        source_name,
                        target_name,
                        destination="profile",
                    )
                else:
                    result = copy_test_into_root_payload(
                        payload,
                        profile_name,
                        source_name,
                        target_name,
                    )
            except DslServiceError as exc:
                return exc
            session.mark_dirty()
            self._persist_local_profiles_edit(session)
            return result

        outcome = self._run_blocking_status_operation(
            DSL_COPY_TO_PROFILE_FMT.format(
                source=source_name,
                profile=profile_name,
                target=target_name,
            ),
            _operation,
            include_test_output=True,
        )
        if isinstance(outcome, DslServiceError):
            self._append_output(str(outcome))
            self._append_test_output(str(outcome))
            if str(outcome).startswith(DSL_COPY_DUPLICATE_PREFIX):
                self._refresh_test_library_view(profile_name)
                if self._select_test_library_profile_name(target_name):
                    message = DSL_COPY_DUPLICATE_REVEAL_FMT.format(name=target_name)
                    self._append_output(message)
                    self._append_test_output(message)
            return
        validation_text = render_validation_text(
            outcome.validation,
            robot_test_dsl_store_from_root_payload(payload),
            entries_override={target_name: outcome.entry},
        )
        if validation_text != "OK":
            for line in validation_text.splitlines():
                self._append_output(line)
                self._append_test_output(line)
        self._refresh_tests_for_profile(profile_name)
        self._refresh_test_library_view(profile_name)
        self._select_test_library_profile_name(target_name)
        if outcome.ok():
            self._append_output(DSL_COPY_SAVED_FMT)
            self._append_test_output(DSL_COPY_SAVED_FMT)
            return
        invalid_text = TEST_SOURCE_STATUS_SAVED_INVALID_FMT.format(name=target_name)
        self._append_output(invalid_text)
        self._append_test_output(invalid_text)

    def _dsl_validate_from_ui(self) -> None:
        """
        NAME
            _dsl_validate_from_ui - Validate local DSL tests for the selected profile from the UI.
        """
        profile_name = self._selected_real_profile()
        if not profile_name:
            self._append_output(DSL_OUTPUT_NO_PROFILE)
            self._append_test_output(DSL_OUTPUT_NO_PROFILE)
            return
        try:
            payload = self._load_local_profiles_payload()
        except Exception as exc:
            self._append_output(str(exc))
            self._append_test_output(str(exc))
            return

        def _operation() -> object:
            store = robot_test_dsl_store_from_root_payload(payload)
            return validate_store_for_profile(payload, store, profile_name)

        result = self._run_blocking_status_operation(
            DSL_VALIDATE_START_FMT.format(profile=profile_name),
            _operation,
            include_test_output=True,
        )
        store = robot_test_dsl_store_from_root_payload(payload)
        for line in render_validation_text(result, store).splitlines():
            self._append_output(line)
            self._append_test_output(line)
        if result.ok():
            self._append_output(DSL_VALIDATE_OK_FMT.format(profile=profile_name))
            self._append_test_output(DSL_VALIDATE_OK_FMT.format(profile=profile_name))
            return
        self._append_output(DSL_VALIDATE_FAIL_FMT.format(profile=profile_name))
        self._append_test_output(DSL_VALIDATE_FAIL_FMT.format(profile=profile_name))

    def _config_dialog_start(self) -> Tuple[Path, str]:
        """
        NAME
            _config_dialog_start - Return initial directory and filename for config dialogs.
        """
        path = self._default_profiles_path()
        return (path.parent, path.name)

    def _run_blocking_status_operation(
        self,
        start_line: str,
        operation: Callable[[], object],
        include_test_output: bool = False,
    ) -> object:
        """
        NAME
            _run_blocking_status_operation - Run a blocking host-side operation with simple UI status output.
        """
        self._append_output(f"{timestamp_hms()} {start_line}")
        if include_test_output:
            self._append_test_output(f"{timestamp_hms()} {start_line}")
        self.update_idletasks()
        return operation()

    def _runtime_activate_from_ui(self) -> None:
        """
        NAME
            _runtime_activate_from_ui - Explicitly activate the selected runtime profile.
        """
        if not self._tcp_connected:
            self._append_output(OUTPUT_NOT_CONNECTED)
            return
        if self._tracker.is_pending():
            self._append_output(OUTPUT_BUSY)
            return
        profile_name = self._selected_real_profile()
        if not profile_name:
            self._append_output(OUTPUT_NO_PROFILE)
            return
        args = {KEY_NAME: profile_name}
        self._append_output(
            f"{timestamp_hms()} {OUTPUT_RUNTIME_ACTIVATE_FMT.format(profile=profile_name)}"
        )
        self._last_cmd = ("runtimeActivate", args)
        seq = send_tracked_command(
            self._session,
            self._tracker,
            "runtimeActivate",
            args,
            sender=lambda session, _command_name, _command_args: runtime_activate(session, profile_name),
            now=time.time(),
        )
        if seq is not None:
            self._last_sent_seq = seq

    def _runtime_deactivate_from_ui(self) -> None:
        """
        NAME
            _runtime_deactivate_from_ui - Explicitly deactivate the active runtime profile.
        """
        if not self._tcp_connected:
            self._append_output(OUTPUT_NOT_CONNECTED)
            return
        if self._tracker.is_pending():
            self._append_output(OUTPUT_BUSY)
            return
        self._append_output(f"{timestamp_hms()} {OUTPUT_RUNTIME_DEACTIVATE}")
        self._last_cmd = ("runtimeDeactivate", {})
        seq = send_tracked_command(
            self._session,
            self._tracker,
            "runtimeDeactivate",
            {},
            sender=lambda session, _command_name, _command_args: runtime_deactivate(session),
            now=time.time(),
        )
        if seq is not None:
            self._last_sent_seq = seq

    def _show_runtime_state_from_ui(self) -> None:
        """
        NAME
            _show_runtime_state_from_ui - Request the runtime-state payload through the top-bar control.
        """
        self._on_action(CMD_SHOW_RUNTIME_STATE)

    def _activate_scope_from_ui(self) -> None:
        """
        NAME
            _activate_scope_from_ui - Activate active-group from the current context.
        """
        if not self._tcp_connected:
            self._append_output(OUTPUT_NOT_CONNECTED)
            return
        if self._tracker.is_pending():
            self._append_output(OUTPUT_BUSY)
            return
        mode = LIFECYCLE_DEFAULT_MODE
        label = GROUP_ACTIVE_NAME
        args = {PROFILE_KEY_LABEL: label, "mode": mode}
        self._append_output(
            f"{timestamp_hms()} {OUTPUT_LIFECYCLE_ACTIVATE_FMT.format(label=label, mode=mode)}"
        )
        self._last_cmd = ("lifecycleActivate", args)
        seq = send_tracked_command(
            self._session,
            self._tracker,
            "lifecycleActivate",
            args,
            sender=lambda session, _command_name, _command_args: lifecycle_activate(session, label, mode),
            now=time.time(),
        )
        if seq is not None:
            self._last_sent_seq = seq

    def _lifecycle_activate_from_ui(self) -> None:
        """
        NAME
            _lifecycle_activate_from_ui - Compatibility wrapper for shared top-bar scope activation.
        """
        self._activate_scope_from_ui()

    def _deactivate_scope_from_ui(self) -> None:
        """
        NAME
            _deactivate_scope_from_ui - Deactivate the current active-group session from the top bar.
        """
        if not self._tcp_connected:
            self._append_output(OUTPUT_NOT_CONNECTED)
            return
        if self._tracker.is_pending():
            self._append_output(OUTPUT_BUSY)
            return
        if self.__dict__.get("_controlled_lifecycle_active_known") is not True:
            self._append_output(OUTPUT_NO_ACTIVE_CONTROLLED_SESSION)
            return
        self._append_output(f"{timestamp_hms()} {OUTPUT_LIFECYCLE_DEACTIVATE_ACTIVE}")
        self._last_cmd = ("lifecycleDeactivateActive", {})
        seq = send_tracked_command(
            self._session,
            self._tracker,
            "lifecycleDeactivateActive",
            {},
            sender=lambda session, _command_name, _command_args: lifecycle_deactivate_active(
                session
            ),
            now=time.time(),
        )
        if seq is not None:
            self._last_sent_seq = seq

    def _lifecycle_deactivate_from_ui(self) -> None:
        """
        NAME
            _lifecycle_deactivate_from_ui - Compatibility wrapper for shared top-bar scope deactivation.
        """
        self._deactivate_scope_from_ui()

    def _lifecycle_deactivate_active_from_ui(self) -> None:
        """
        NAME
            _lifecycle_deactivate_active_from_ui - Deactivate whichever controlled lifecycle session is active.
        """
        if not self._tcp_connected:
            self._append_output(OUTPUT_NOT_CONNECTED)
            return
        if self._tracker.is_pending():
            self._append_output(OUTPUT_BUSY)
            return
        self._append_output(f"{timestamp_hms()} {OUTPUT_LIFECYCLE_DEACTIVATE_ACTIVE}")
        self._last_cmd = ("lifecycleDeactivateActive", {})
        seq = send_tracked_command(
            self._session,
            self._tracker,
            "lifecycleDeactivateActive",
            {},
            sender=lambda session, _command_name, _command_args: lifecycle_deactivate_active(session),
            now=time.time(),
        )
        if seq is not None:
            self._last_sent_seq = seq

    def _show_lifecycle_state_from_ui(self) -> None:
        """
        NAME
            _show_lifecycle_state_from_ui - Request the lifecycle-state payload through the top-bar control.
        """
        if not self._tcp_connected:
            self._append_output(OUTPUT_NOT_CONNECTED)
            self._append_test_output(OUTPUT_NOT_CONNECTED)
            return
        if self._tracker.is_pending():
            self._append_output(OUTPUT_BUSY)
            self._append_test_output(OUTPUT_BUSY)
            return
        command_line = f"{timestamp_hms()} CMD {CMD_SHOW_LIFECYCLE_STATE}"
        self._append_output(command_line)
        self._append_test_output(command_line)
        self._last_cmd = (CMD_SHOW_LIFECYCLE_STATE, {})
        seq = send_tracked_command(
            self._session,
            self._tracker,
            CMD_SHOW_LIFECYCLE_STATE,
            {},
            sender=lambda session, _command_name, _command_args: show_lifecycle_state(session, json_output=False),
            now=time.time(),
        )
        if seq is not None:
            self._last_sent_seq = seq

    def _push_config_from_ui(self) -> None:
        """
        NAME
            _push_config_from_ui - Push a full bringup_system.json payload from the UI.
        """
        if not self._tcp_connected:
            self._append_output(OUTPUT_NOT_CONNECTED)
            return
        if self._tracker.is_pending():
            self._append_output(OUTPUT_BUSY)
            return
        profile_name = self._selected_real_profile()
        if not profile_name:
            self._append_output(OUTPUT_NO_PROFILE)
            return
        initial_dir, initial_file = self._config_dialog_start()
        selected = filedialog.askopenfilename(
            title=BUTTON_PUSH_CONFIG,
            initialdir=str(initial_dir),
            initialfile=initial_file,
            filetypes=CONFIG_FILE_TYPES,
        )
        if not selected:
            self._append_output(OUTPUT_PUSH_CANCELLED)
            return

        def _operation() -> object:
            return push_config(self._session, selected, profile_name)

        result = self._run_blocking_status_operation(
            OUTPUT_PUSH_START_FMT.format(path=selected, profile=profile_name),
            _operation,
        )
        message = getattr(result, "message", "") if result is not None else ""
        self._append_output(message or "Config push finished.")
        self._refresh_profiles()

    def _download_current_config_from_ui(self) -> None:
        """
        NAME
            _download_current_config_from_ui - Download the robot's current config to disk.
        """
        if not self._tcp_connected:
            self._append_output(OUTPUT_NOT_CONNECTED)
            return
        if self._tracker.is_pending():
            self._append_output(OUTPUT_BUSY)
            return
        initial_dir, _initial_file = self._config_dialog_start()
        selected = filedialog.asksaveasfilename(
            title=BUTTON_DOWNLOAD_CONFIG,
            initialdir=str(initial_dir),
            initialfile=DOWNLOAD_FILENAME,
            filetypes=CONFIG_FILE_TYPES,
            defaultextension=".json",
        )
        if not selected:
            self._append_output(OUTPUT_DOWNLOAD_CANCELLED)
            return

        def _operation() -> object:
            return download_current_config(self._session, selected)

        result = self._run_blocking_status_operation(
            OUTPUT_DOWNLOAD_START_FMT.format(path=selected),
            _operation,
        )
        message = getattr(result, "message", "") if result is not None else ""
        self._append_output(message or "Config download finished.")

    def _poll_nt(self) -> None:
        """
        NAME
            _poll_nt - Poll REST/NT inputs and update output log.
        """
        self._live_clock_var.set(time.strftime(LIVE_CLOCK_FORMAT))
        now = time.time()
        if not self._tcp_connected and self._auto_connect_enabled:
            if (now - self._last_connect_attempt) > 1.0:
                self._last_connect_attempt = now
                self._tcp_connected = connect(self._session)
        elif self._tcp_connected and self._auto_connect_enabled:
            self._tcp_connected = connect(self._session)
        if self._tcp_connected:
            self._handshake_done = self._session.handshake_done()
        if self._tcp_connected != self._prev_tcp_connected:
            if self._tcp_connected:
                self._notify_ui_failure(
                    "tcp",
                    False,
                    "REST session disconnected.",
                    "REST session reconnected.",
                )
            else:
                self._notify_ui_failure(
                    "tcp",
                    True,
                    "REST session disconnected.",
                    "REST session reconnected.",
                )
            self._prev_tcp_connected = self._tcp_connected
        if not self._tcp_connected:
            self._handshake_done = False
            self._runtime_state_seen = False
            self._handshake_inflight = False
            self._session.reset_handshake()
            self._last_keepalive = 0.0
        for event in self._session.poll_events():
            self._handle_tcp_response(event)

        if self._ui_table is not None:
            session_id = self._ui_table.getEntry("state/sessionId").getString("")
            if session_id:
                self._apply_robot_ui_session_id(session_id)
            enabled = self._ui_table.getEntry("state/enabled").getBoolean(True)
            estopped = self._ui_table.getEntry("state/estopped").getBoolean(False)
            mode = self._ui_table.getEntry("state/mode").getString("disabled")
            last_ack_ms = self._ui_table.getEntry("state/lastAckMs").getDouble(0.0)
            self._robot_selected_profile = _normalize_profile_name(
                self._ui_table.getEntry(NT_UI_STATE_SELECTED_PROFILE).getString(PROFILE_NONE)
            )
            self._robot_active_runtime_profile = _normalize_profile_name(
                self._ui_table.getEntry(NT_UI_STATE_ACTIVE_RUNTIME_PROFILE).getString(PROFILE_NONE)
            )
            self._sync_diagnostic_profile_context(reload_views=True)
            self._maybe_prompt_host_profile_context_sync()
            nt_connected = True
        else:
            enabled = True
            estopped = False
            mode = "disabled"
            last_ack_ms = 0.0
            nt_connected = False
        if self._robot_enabled_known and not enabled:
            self._runtime_active_known = False
            self._controlled_lifecycle_active_known = False
        self._robot_enabled_known = enabled
        self._robot_estopped_known = estopped
        self._robot_mode_known = str(mode or "disabled").strip().lower()
        if self._tests_table is not None:
            selected_name = str(
                self._tests_table.getEntry("selectedName").getString("") or ""
            ).strip()
            test_names = self._resolve_test_names_from_rows()
            if (
                selected_name
                and selected_name != PROFILE_NONE
                and selected_name not in test_names
            ):
                test_names = test_names + [selected_name]
            self._sync_test_dropdown_values(test_names)
            if not selected_name:
                selected_name = self._resolve_selected_from_rows()
            if selected_name:
                self._sync_test_selection(selected_name)
            active_name = self._tests_table.getEntry("activeName").getString("")
            active_status = self._tests_table.getEntry("activeStatus").getString("")
            run_all = self._tests_table.getEntry("runAllActive").getBoolean(False)
            running = "(none)"
            if active_name:
                running = active_name
                if active_status:
                    running += f" ({active_status})"
                if run_all:
                    running += " [run all]"
            self._running_text_var.set(f"Running: {running}")
            self._refresh_test_result_status()
        if self._is_connected is not None:
            try:
                nt_connected = bool(self._is_connected())
            except Exception:
                nt_connected = False
        self._nt_connected = nt_connected
        if self._tracker.check_timeout(time.time()):
            self._notify_ui_failure(
                "cmd_timeout",
                True,
                "TIMEOUT waiting for ACK/OUT.",
                "Recovered: command responses received.",
            )
            self._handshake_inflight = False
        self._pending_label.configure(text=self._tracker.pending_text())
        stale_state = False
        if nt_connected:
            now_ms = time.time() * 1000.0
            if last_ack_ms > 0.0 and (now_ms - last_ack_ms) > (self._state_stale_sec * 1000.0):
                stale_state = True
        self._state_stale = stale_state
        nt_label = "NT OK" if nt_connected else "NT Disconnected"
        label = (
            f"REST Connected ({nt_label}, rio={self._rio_host})"
            if self._tcp_connected
            else f"REST Disconnected ({nt_label}, rio={self._rio_host})"
        )
        self._status_label.configure(
            text=label,
            foreground="#2f7a2f" if self._tcp_connected else "#b32323",
        )
        if nt_connected and not self._tracker.is_pending():
            if stale_state:
                self._pending_label.configure(text="Robot state stale (code not running?)")
            elif estopped:
                self._pending_label.configure(text="Robot E-Stop (disabled)")
            elif not enabled:
                self._pending_label.configure(text="Robot Disabled")
            elif mode:
                self._pending_label.configure(text=f"Robot: {mode}")
        self._apply_live_runtime_notice_from_nt_state(enabled, estopped, stale_state)
        blocked = self._manual_duty_block_message()
        if blocked and self._manual_duty_popup is not None:
            self._append_output(blocked)
            self._close_manual_duty_popup(stop_motor=False)
        if (
            self._tcp_connected
            and not stale_state
            and not self._handshake_done
            and not self._handshake_inflight
            and not self._tracker.is_pending()
            and (time.time() - self._last_handshake_attempt) >= self._handshake_min_interval
        ):
            self._send_handshake(reset=False, log=False)
        if self._tcp_connected and not self._tracker.is_pending():
            if (now - self._last_keepalive) >= self._keepalive_interval:
                seq = ui_ping(self._session)
                if seq is not None:
                    self._last_keepalive = now
        if (
            self._tcp_connected
            and self._handshake_done
            and not self._log_poll_inflight
            and (now - self._last_log_poll) >= self._log_poll_interval
        ):
            seq = ui_poll_log(self._session)
            if seq is not None:
                self._log_poll_inflight = True
                self._log_poll_seq = seq
                self._last_log_poll = now
        self._poll_live_overlay(now)
        self._poll_presence_overrides()
        self._poll_visibility_snapshot(now)
        self._update_action_enabled()
        idle = (
            not self._tcp_connected
            and not self._nt_connected
            and not self._live_enabled_var.get()
            and not self._tracker.is_pending()
            and not self._log_poll_inflight
        )
        interval = self._poll_interval_idle if idle else self._poll_interval_active
        self.after(int(interval * 1000), self._poll_nt)

    def _poll_live_overlay(self, now: float) -> None:
        """
        NAME
            _poll_live_overlay - Poll runtime state for runtime-backed topology/evidence panels.
        """
        fast_manual_refresh = self._manual_runtime_refresh_active()
        if (
            not fast_manual_refresh
            and self._runtime_state_pause_until is not None
            and now < self._runtime_state_pause_until
        ):
            return
        effective_interval = (
            1.0 / ACTIVE_MANUAL_RUNTIME_STATE_RATE_HZ
            if fast_manual_refresh
            else (self._runtime_state_interval * self._runtime_state_backoff)
        )
        if (now - self._runtime_state_last_poll) < effective_interval:
            return
        self._runtime_state_last_poll = now
        source = self._live_source_var.get()
        if source == LIVE_SOURCE_FILE:
            return
        if not self._tcp_connected or not self._handshake_done:
            return
        if self._tracker.is_pending() or self._log_poll_inflight:
            return
        if self._runtime_state_pending_seq is None:
            seq = show_runtime_state(self._session, json_output=True)
            if seq is not None:
                self._runtime_state_pending_seq = int(seq)
                self._runtime_state_pending_at = now
        else:
            if (now - self._runtime_state_pending_at) > self._runtime_state_timeout_sec:
                self._runtime_state_pending_seq = None

    def _manual_runtime_refresh_active(self) -> bool:
        """
        NAME
            _manual_runtime_refresh_active - Return whether runtime-state polling should run at fast manual-test cadence.
        """
        if self._manual_duty_popup is not None:
            return True
        return bool(self._manual_motion_checks)

    def _set_runtime_state_notice(self, text: str, level: str = "warn") -> None:
        """
        NAME
            _set_runtime_state_notice - Store persistent next-step guidance from runtime state.
        """
        message = str(text).strip()
        self._runtime_state_notice_text = message
        self._runtime_state_notice_level = (
            level if level in {"info", "warn", "error"} else "warn"
        )
        self._refresh_output_runtime_notice()

    def _clear_runtime_state_notice(self) -> None:
        """
        NAME
            _clear_runtime_state_notice - Clear persistent runtime-state guidance.
        """
        self._runtime_state_notice_text = NT_VALUE_EMPTY
        self._refresh_output_runtime_notice()

    def _set_runtime_event_notice(self, text: str, level: str = "warn") -> None:
        """
        NAME
            _set_runtime_event_notice - Store transient operator guidance from command results.
        """
        message = str(text).strip()
        self._runtime_event_notice_text = message
        self._runtime_event_notice_level = (
            level if level in {"info", "warn", "error"} else "warn"
        )
        self._refresh_output_runtime_notice()

    def _clear_runtime_event_notice(self) -> None:
        """
        NAME
            _clear_runtime_event_notice - Clear transient operator guidance.
        """
        self._runtime_event_notice_text = NT_VALUE_EMPTY
        self._refresh_output_runtime_notice()

    def _refresh_output_runtime_notice(self) -> None:
        """
        NAME
            _refresh_output_runtime_notice - Render the highest-priority next-step notice under Output.
        """
        panel = getattr(self, "_output_scope_panel", None)
        if panel is None:
            return
        runtime_state_seen = bool(self.__dict__.get("_runtime_state_seen", False))
        if not self._tcp_connected or not self._handshake_done or not runtime_state_seen:
            headline = TEST_SCOPE_PANEL_WAITING_HEADLINE
            bg = TEST_SCOPE_PANEL_NEUTRAL_BG
            fg = TEST_SCOPE_PANEL_NEUTRAL_FG
            detail = RUNNABLE_SCOPE_PANEL_WAITING_DETAIL
        elif self._runtime_state_notice_text:
            headline = TEST_SCOPE_PANEL_INACTIVE_HEADLINE
            bg = TEST_SCOPE_PANEL_INACTIVE_BG
            fg = TEST_SCOPE_PANEL_INACTIVE_FG
            detail = self._runtime_state_notice_text
        elif self._runtime_event_notice_text:
            headline = TEST_SCOPE_PANEL_INACTIVE_HEADLINE
            bg = TEST_SCOPE_PANEL_INACTIVE_BG
            fg = TEST_SCOPE_PANEL_INACTIVE_FG
            detail = self._runtime_event_notice_text
        else:
            headline = TEST_SCOPE_PANEL_READY_HEADLINE
            bg = TEST_SCOPE_PANEL_READY_BG
            fg = TEST_SCOPE_PANEL_READY_FG
            detail = RUNNABLE_SCOPE_PANEL_READY_DETAIL
        self._output_scope_headline_var.set(headline)
        self._output_scope_detail_var.set(detail)
        panel.configure(bg=bg, highlightbackground=TEST_SCOPE_PANEL_BORDER)
        for attr_name in (
            "_output_scope_title_label",
            "_output_scope_headline_label",
            "_output_scope_detail_label",
        ):
            label = self.__dict__.get(attr_name)
            if label is not None:
                label.configure(bg=bg, fg=fg)

    def _apply_runtime_state_payload(self, payload: Dict[str, Any]) -> None:
        """
        NAME
            _apply_runtime_state_payload - Apply live runtime-state JSON.
        """
        self._latest_runtime_state_payload = dict(payload or {})
        self._runtime_state_seen = True
        latest_runtime_devices: Dict[str, Dict[str, Any]] = {}
        runtime_active = payload.get("runtimeActive")
        if isinstance(runtime_active, bool):
            self._runtime_active_known = runtime_active
        controlled_lifecycle_active = payload.get("controlledLifecycleActive")
        if isinstance(controlled_lifecycle_active, bool):
            self._controlled_lifecycle_active_known = controlled_lifecycle_active
        selected_profile = _normalize_profile_name(payload.get("selectedProfile"))
        active_runtime_profile = _normalize_profile_name(
            payload.get("activeRuntimeProfile")
        )
        self._robot_selected_profile = selected_profile
        self._robot_active_runtime_profile = active_runtime_profile
        self._sync_diagnostic_profile_context(reload_views=True)
        devices = payload.get("devices")
        if isinstance(devices, list):
            for device in devices:
                if not isinstance(device, dict):
                    continue
                label = str(device.get("label", "")).strip()
                if label:
                    latest_runtime_devices[label.lower()] = device
        self._latest_runtime_devices = latest_runtime_devices
        self._merge_cached_active_probe_results_into_runtime_devices()
        now_sec = time.time()
        for label_key, device in latest_runtime_devices.items():
            motion_entry = self._manual_motion_checks.get(label_key)
            if not isinstance(motion_entry, dict):
                continue
            velocity_rpm = _runtime_device_field(device, "velRpm")
            applied_duty = _runtime_device_field(device, EVIDENCE_FIELD_APPLIED_DUTY)
            motor_current = _runtime_device_field(device, EVIDENCE_FIELD_MOTOR_CURRENT_A)
            position_rot = _runtime_device_field(device, EVIDENCE_FIELD_POSITION_ROT)
            position_delta_rot = None
            start_position_rot = motion_entry.get("startPositionRot")
            if (
                not isinstance(start_position_rot, (int, float))
                and isinstance(position_rot, (int, float))
            ):
                motion_entry["startPositionRot"] = float(position_rot)
                start_position_rot = motion_entry.get("startPositionRot")
            if isinstance(position_rot, (int, float)) and isinstance(start_position_rot, (int, float)):
                position_delta_rot = float(position_rot) - float(start_position_rot)
            observation_update: Dict[str, Any] = {
                "recordedAtEpochSec": now_sec,
                "recordedAt": timestamp_hms(),
                "appliedDuty": applied_duty if isinstance(applied_duty, (int, float)) else None,
                "velRpm": velocity_rpm if isinstance(velocity_rpm, (int, float)) else None,
                "motorCurrentA": motor_current if isinstance(motor_current, (int, float)) else None,
                "positionRot": position_rot if isinstance(position_rot, (int, float)) else None,
                "positionDeltaRot": position_delta_rot if isinstance(position_delta_rot, (int, float)) else None,
                "maxAbsVelRpm": float(motion_entry.get("maxAbsVelRpm", 0.0)),
                "maxAbsPositionDeltaRot": float(motion_entry.get("maxAbsPositionDeltaRot", 0.0)),
            }
            if isinstance(velocity_rpm, (int, float)):
                abs_vel = abs(float(velocity_rpm))
                motion_entry["maxAbsVelRpm"] = max(abs_vel, float(motion_entry.get("maxAbsVelRpm", 0.0)))
                if abs_vel >= EVIDENCE_MOTION_MIN_RPM:
                    motion_entry["sawMotion"] = True
                    observation_update["autoResult"] = EVIDENCE_MANUAL_AUTO_RESULT_ROTATION
            if isinstance(position_delta_rot, (int, float)):
                abs_position_delta_rot = abs(float(position_delta_rot))
                motion_entry["maxAbsPositionDeltaRot"] = max(
                    abs_position_delta_rot,
                    float(motion_entry.get("maxAbsPositionDeltaRot", 0.0)),
                )
                observation_update["maxAbsPositionDeltaRot"] = float(motion_entry.get("maxAbsPositionDeltaRot", 0.0))
                if abs_position_delta_rot >= EVIDENCE_MOTION_MIN_POSITION_DELTA_ROT:
                    motion_entry["sawMotion"] = True
                    observation_update["autoResult"] = EVIDENCE_MANUAL_AUTO_RESULT_ROTATION
            elif motion_entry.get("sawMotion"):
                observation_update["autoResult"] = EVIDENCE_MANUAL_AUTO_RESULT_ROTATION
            self._update_manual_test_observation(label_key, observation_update)
        stale_motion_labels = []
        for label_key, motion_entry in self._manual_motion_checks.items():
            started_at = motion_entry.get("startedAt")
            if not isinstance(started_at, (int, float)):
                stale_motion_labels.append(label_key)
                continue
            age_sec = now_sec - float(started_at)
            if age_sec >= EVIDENCE_MANUAL_MOTION_SETTLE_SEC:
                observation = self._manual_test_observations.get(label_key)
                if isinstance(observation, dict) and observation.get("autoResult") == EVIDENCE_MANUAL_AUTO_RESULT_RUNNING:
                    if motion_entry.get("sawMotion"):
                        observation["autoResult"] = EVIDENCE_MANUAL_AUTO_RESULT_ROTATION
                    else:
                        observation["autoResult"] = EVIDENCE_MANUAL_AUTO_RESULT_NO_ROTATION
                        observation["recordedAtEpochSec"] = now_sec
                        observation["recordedAt"] = timestamp_hms()
            if (now_sec - float(started_at)) > EVIDENCE_MANUAL_MOTION_WINDOW_SEC:
                stale_motion_labels.append(label_key)
        for label_key in stale_motion_labels:
            self._manual_motion_checks.pop(label_key, None)
        live_views = self._iter_live_views()
        if not live_views:
            return
        changed = False
        for live_view in live_views:
            changed = live_view.update_runtime_state(payload) or changed
        self._refresh_tests_active_group_panel()
        self._refresh_selected_test_scope_status()
        self._refresh_evidence_view()
        if changed:
            self._runtime_state_backoff = 1.0
            self._runtime_state_idle_count = 0
            self._runtime_state_pause_until = None
            return
        self._runtime_state_idle_count += 1
        if self._runtime_state_idle_count >= 3:
            self._runtime_state_backoff = min(8.0, self._runtime_state_backoff * 2.0)
            self._runtime_state_idle_count = 0
            self._runtime_state_pause_until = time.time() + self._runtime_state_idle_pause_sec

    def _apply_runtime_group_command_payload(self, payload: Optional[Dict[str, Any]]) -> None:
        """
        NAME
            _apply_runtime_group_command_payload - Apply one command-returned runtime group update to all live views.
        """
        if not isinstance(payload, dict):
            return
        group_payload = payload.get(GROUP_KEY_GROUP)
        if not isinstance(group_payload, dict):
            return
        for live_view in self._iter_live_views():
            live_view.apply_runtime_group(group_payload)

    def _apply_live_runtime_notice_from_nt_state(
        self,
        enabled: bool,
        estopped: bool,
        stale_state: bool,
    ) -> None:
        """
        NAME
            _apply_live_runtime_notice_from_nt_state - Surface DS/NT state directly in Live Topology.
        """
        activation_notice = self._scope_activation_notice_text()
        scope_active = self._scope_is_currently_active()
        if stale_state:
            self._set_runtime_state_notice(
                "Robot state stale (code not running?)", "warn"
            )
        elif self._manual_active_group_is_empty():
            self._set_runtime_state_notice(
                RUNNABLE_SCOPE_DETAIL_MANUAL_EMPTY, "warn"
            )
        elif estopped:
            self._set_runtime_state_notice("Robot E-Stop. Manual run blocked.", "error")
        elif not enabled:
            self._set_runtime_state_notice(
                "Robot disabled. Enable teleop to run motors.", "info"
            )
        elif not scope_active:
            self._set_runtime_state_notice(activation_notice, "warn")
        else:
            self._clear_runtime_state_notice()
        for live_view in self._iter_live_views():
            if stale_state:
                live_view.set_runtime_state_notice("Robot state stale (code not running?)", "warn")
            elif self._manual_active_group_is_empty():
                live_view.set_runtime_state_notice(RUNNABLE_SCOPE_DETAIL_MANUAL_EMPTY, "warn")
            elif estopped:
                live_view.set_runtime_state_notice("Robot E-Stop. Manual run blocked.", "error")
            elif not enabled:
                live_view.set_runtime_state_notice("Robot disabled. Enable teleop to run motors.", "info")
            elif not scope_active:
                live_view.set_runtime_state_notice(activation_notice, "warn")
            else:
                live_view.clear_runtime_state_notice()

    def _selected_profile_from_command_event(
        self,
        name: str,
        status: str,
        message: str,
        text: str,
    ) -> str:
        """
        NAME
            _selected_profile_from_command_event - Parse one successful selectProfile result.
        """
        command_name = str(name or NT_VALUE_EMPTY).strip().lower()
        if command_name != "selectprofile":
            return PROFILE_NONE
        if str(status or NT_VALUE_EMPTY).strip().lower() != "ok":
            return PROFILE_NONE
        for candidate in (message, text):
            for line in str(candidate or NT_VALUE_EMPTY).splitlines():
                clean_line = str(line or NT_VALUE_EMPTY).strip()
                if not clean_line.startswith(OUTPUT_SELECTED_PROFILE_PREFIX):
                    continue
                return _normalize_profile_name(
                    clean_line[len(OUTPUT_SELECTED_PROFILE_PREFIX):]
                )
        return PROFILE_NONE

    def _apply_robot_profile_context_from_command_event(
        self,
        name: str,
        status: str,
        message: str,
        text: str,
    ) -> None:
        """
        NAME
            _apply_robot_profile_context_from_command_event - Update robot profile context from command ACK/OUT.
        """
        selected_profile = self._selected_profile_from_command_event(
            name,
            status,
            message,
            text,
        )
        if selected_profile == PROFILE_NONE:
            return
        self._robot_selected_profile = selected_profile
        self._sync_diagnostic_profile_context(reload_views=True)

    def _handle_tcp_response(self, event: BridgeEvent) -> None:
        """
        NAME
            _handle_tcp_response - Handle an inbound REST-session response payload.
        """
        data = None
        msg_type = event.type
        name = event.name.strip()
        seq = event.seq
        if name.lower() == "uiping":
            return
        if msg_type in ("ack", "out") and self._is_handshake_required(event):
            self._handle_handshake_required()
            return
        if msg_type in ("ack", "out") and self._is_owner_required(event):
            self._handle_owner_required()
            return
        if (
            self._runtime_state_pending_seq is not None
            and name.lower() == "showruntimestate"
            and int(seq) == int(self._runtime_state_pending_seq)
        ):
            if msg_type == "out":
                try:
                    payload = json.loads(event.json_text) if event.json_text else None
                except Exception:
                    payload = None
                if isinstance(payload, dict):
                    self._apply_runtime_state_payload(payload)
                self._runtime_state_pending_seq = None
                return
            if msg_type == "ack":
                return
        seq_match = self._log_poll_seq is not None and int(seq) == int(self._log_poll_seq)
        if msg_type in ("ack", "out") and (name.lower() == "uipolllog" or seq_match):
            if msg_type == "out":
                text = event.text
                mirror_to_test = False
                last_cmd = self.__dict__.get("_last_cmd")
                if isinstance(last_cmd, tuple) and last_cmd:
                    mirror_to_test = self._is_test_activity_command(str(last_cmd[0]))
                if text:
                    for line in text.splitlines():
                        line = _sanitize_stream_output_line(line)
                        if self._should_skip_out_line(line):
                            continue
                        self._append_output(line)
                        if mirror_to_test or self._is_test_activity_output_line(line):
                            self._append_test_output(line)
                self._log_poll_inflight = False
                self._log_poll_seq = None
            elif msg_type == "ack":
                self._log_poll_inflight = False
                self._log_poll_seq = None
            return
        if msg_type in ("ack", "out"):
            self._notify_ui_failure(
                "cmd_timeout",
                False,
                "TIMEOUT waiting for ACK/OUT.",
                "Recovered: command responses received.",
            )
        if msg_type == "ack":
            seq = int(event.seq)
            name = event.name
            status = event.status
            message = event.message
            ts = timestamp_hms()
            header = f"{ts} ACK {seq} {name} {status} {message}".rstrip()
            self._append_output(header)
            if self._is_test_activity_command(name):
                self._append_test_output(header)
            self._apply_live_runtime_notice_from_ack(name, status, message)
            self._apply_robot_profile_context_from_command_event(
                name,
                status,
                message,
                NT_VALUE_EMPTY,
            )
            self._last_ack_seq = seq
        elif msg_type == "out":
            seq = int(event.seq)
            name = event.name
            text = event.text
            json_payload = event.json_text
            data = None
            ts = timestamp_hms()
            header = f"{ts} OUT {seq} {name}".rstrip()
            self._append_output(header)
            if self._is_test_activity_command(name):
                self._append_test_output(header)
            if text:
                for line in text.splitlines():
                    line = _sanitize_stream_output_line(line)
                    self._remember_out_line(line)
                    self._append_output(f"  {line}")
                    if self._is_test_activity_command(name):
                        self._append_test_output(f"  {line}")
            if json_payload:
                self._append_output("  json: " + str(json_payload))
                if self._is_test_activity_command(name):
                    self._append_test_output("  json: " + str(json_payload))
                try:
                    data = json.loads(json_payload)
                except Exception:
                    data = None
            self._apply_robot_profile_context_from_command_event(
                name,
                event.status,
                event.message,
                text,
            )
            command_lower = str(name or NT_VALUE_EMPTY).strip().lower()
            if command_lower in ACTIVE_GROUP_RESULT_COMMANDS or command_lower == "groupreplacemembers":
                self._apply_runtime_group_command_payload(data)
            if name == "uiHandshake" and isinstance(data, dict):
                min_next = data.get("minNextSeq")
                if isinstance(min_next, (int, float)):
                    self._seq = int(min_next) - 1
                    self._seq_seeded = True
                session_id = data.get("sessionId")
                session_id_value = session_id if isinstance(session_id, str) else ""
                if session_id_value:
                    self._apply_robot_ui_session_id(session_id_value)
                min_seq = int(min_next) if isinstance(min_next, (int, float)) else None
                self._session.mark_handshake_done(session_id_value, min_seq)
            self._last_out_seq = seq
            if name == "uiHandshake":
                self._handshake_done = True
                self._handshake_inflight = False
                self._retry_last_command()
            elif name == "uiDisconnect":
                self._tcp_connected = False
                self._handshake_done = False
                self._runtime_state_seen = False
                self._handshake_inflight = False
                self._session.reset_handshake()
                self._last_profile_mismatch_prompt = None
        if msg_type in ("ack", "out"):
            self._tracker.handle_event(event)
            command_lower = str(event.name or "").strip().lower()
            if command_lower == "deactivateselectedtestdevices" and msg_type == "ack":
                if str(event.status or "").strip().lower() == "ok":
                    self._clear_test_selection_ui()
            if command_lower == "activepresenceprobe":
                self._evidence_probe_pending = False
                if isinstance(data, dict):
                    self._cache_active_probe_results_from_command(data)
                seq_value = int(event.seq)
                if self._evidence_last_probe_complete_seq != seq_value:
                    self._evidence_last_probe_complete_seq = seq_value
                    self._evidence_probe_complete_count += 1
                    self._evidence_last_probe_completed_at = time.time()
                    self.after_idle(self._refresh_evidence_view)
            if command_lower in {
                "runtimeactivate",
                "runtimedeactivate",
                "activeadd",
                "activenext",
                "lifecycleactivate",
                "lifecycledeactivateactive",
                "groupadddevice",
                "groupremovedevice",
                "groupreplacemembers",
                "activateselectedtestdevices",
                "deactivateselectedtestdevices",
                "manualdevicedutyset",
                "manualdevicedutyclear",
                "manualgroupdutyset",
                "manualgroupdutyclear",
                "activepresenceprobe",
            }:
                self.after_idle(self._request_runtime_state_refresh)
            if not self._tracker.is_pending():
                pending_transition = self.__dict__.get("_pending_tests_boundary_transition")
                if pending_transition:
                    self._pending_tests_boundary_transition = None
                    previous_tab, current_tab = pending_transition
                    self.after_idle(
                        lambda prev=previous_tab, curr=current_tab: self._handle_tests_boundary_transition(
                            prev, curr
                        )
                    )

    def _apply_live_runtime_notice_from_ack(
        self,
        name: str,
        status: str,
        message: str,
    ) -> None:
        """
        NAME
            _apply_live_runtime_notice_from_ack - Surface critical runtime/manual-run failures in Live Topology.
        """
        command = str(name or "").strip().lower()
        state = str(status or "").strip().lower()
        detail = str(message or "").strip()
        if state == "error":
            if "runtime inactive" in detail.lower():
                self._runtime_active_known = False
                self._set_runtime_event_notice(detail, "warn")
                for live_view in self._iter_live_views():
                    live_view.set_runtime_notice(detail, "warn")
                return
            if "robot disabled" in detail.lower() or "e-stop" in detail.lower():
                self._set_runtime_event_notice(detail, "error")
                for live_view in self._iter_live_views():
                    live_view.set_runtime_notice(detail, "error")
                return
        if command == MANUAL_DUTY_CMD_SET.lower() and state == "ok":
            self._clear_runtime_event_notice()
            for live_view in self._iter_live_views():
                live_view.clear_runtime_notice()
        if command == "runtimeactivate" and state == "ok":
            self._runtime_active_known = True
            self._clear_runtime_event_notice()
        elif command == "runtimedeactivate" and state == "ok":
            self._runtime_active_known = False
            self._clear_runtime_event_notice()
        elif command == "lifecycleactivate" and state == "ok":
            self._controlled_lifecycle_active_known = True
            self._clear_runtime_event_notice()
        elif command == "activateselectedtestdevices" and state == "ok":
            self._controlled_lifecycle_active_known = True
            self._clear_runtime_event_notice()
        elif command in {
            "lifecycledeactivate",
            "lifecycledeactivateactive",
            "deactivateselectedtestdevices",
        } and state == "ok":
            self._controlled_lifecycle_active_known = False
            self._clear_runtime_event_notice()

    def _update_action_enabled(self) -> None:
        """
        NAME
            _update_action_enabled - Enable/disable UI actions based on state.
        """
        self._refresh_scope_context_label()
        self._refresh_selected_test_scope_status()
        allow = (
            self._tcp_connected
            and self._handshake_done
            and not self._tracker.is_pending()
            and not self._state_stale
        )
        state = "normal" if allow else "disabled"
        for btn in getattr(self, "_action_buttons", []):
            btn.state(["!disabled"] if allow else ["disabled"])
        for command, btn in getattr(self, "_action_buttons_by_command", {}).items():
            metadata = ACTIONS_BY_NAME.get(command, {})
            action_kind = str(metadata.get(INVENTORY_KEY_ACTION_KIND, ACTION_KIND_REMOTE_COMMAND))
            if action_kind != ACTION_KIND_HOST_LOCAL:
                command_key = str(command or "").strip().lower()
                if command_key in ACTIVE_GROUP_RESULT_COMMANDS and self._active_group_is_currently_active():
                    btn.state(["disabled"])
                continue
            btn.state(
                ["!disabled"] if self._host_local_action_enabled(command) else ["disabled"]
            )
        for box in self._test_selection_boxes():
            box.configure(state=state)
        activate_scope_button = getattr(self, "_activate_scope_button", None)
        if activate_scope_button is not None:
            activate_allowed = allow
            if activate_allowed and self._test_runtime_block_reason():
                activate_allowed = False
            if activate_allowed and self._scope_context_kind() != GROUP_SOURCE_SELECTED_TEST:
                activate_allowed = not self._manual_active_group_is_empty()
            if (
                activate_allowed
                and self._scope_context_kind() == GROUP_SOURCE_SELECTED_TEST
                and str(self._selected_test_var.get() or "").strip() in ("", PROFILE_NONE)
            ):
                activate_allowed = False
            if activate_allowed and self._scope_context_kind() == GROUP_SOURCE_SELECTED_TEST:
                tests_active_group_rows = self.__dict__.get("_tests_active_group_rows", [])
                activate_allowed = not any(
                    bool(row.get("invalid")) for row in tests_active_group_rows
                )
            activate_scope_button.state(
                ["!disabled"] if activate_allowed else ["disabled"]
            )
        deactivate_scope_button = getattr(self, "_deactivate_scope_button", None)
        if deactivate_scope_button is not None:
            deactivate_allowed = (
                allow and self.__dict__.get("_controlled_lifecycle_active_known") is True
            )
            deactivate_scope_button.state(
                ["!disabled"] if deactivate_allowed else ["disabled"]
            )
        run_selected_button = getattr(self, "_tests_run_selected_button", None)
        if run_selected_button is not None:
            run_selected_allowed = (
                allow and not self._test_runtime_block_reason() and self._selected_test_ready()
            )
            run_selected_button.state(
                ["!disabled"] if run_selected_allowed else ["disabled"]
            )
        if self._reset_button is not None:
            self._reset_button.state(["!disabled"] if self._tcp_connected else ["disabled"])

    def _is_handshake_required(self, event: BridgeEvent) -> bool:
        """
        NAME
            _is_handshake_required - Check if a response indicates missing handshake.
        """
        if event is None:
            return False
        message = (event.message or "").strip()
        if message:
            return "UI handshake required before commands." in message
        text = (event.text or "").strip()
        if text:
            return "UI handshake required before commands." in text
        return False

    def _is_owner_required(self, event: BridgeEvent) -> bool:
        """
        NAME
            _is_owner_required - Check if a response indicates lost session ownership.
        """
        if event is None:
            return False
        message = (event.message or "").strip()
        if message:
            return "Owning control client required." in message
        text = (event.text or "").strip()
        if text:
            return "Owning control client required." in text
        return False

    def _handle_handshake_required(self) -> None:
        """
        NAME
            _handle_handshake_required - Reset handshake state on server warning.
        """
        self._handshake_done = False
        self._runtime_state_seen = False
        self._handshake_inflight = False
        self._last_handshake_attempt = 0.0
        self._session.reset_handshake()
        self._log_poll_inflight = False
        self._log_poll_seq = None
        self._tracker.clear()
        now = time.time()
        if (now - self._handshake_warn_last) >= 2.0:
            self._handshake_warn_last = now
            self._notify_ui_failure(
                "handshake",
                True,
                "UI handshake required, resyncing.",
                "UI handshake OK.",
            )

    def _handle_owner_required(self) -> None:
        """
        NAME
            _handle_owner_required - Enter owner-recovery state after losing REST control ownership.
        """
        self._owner_required = True
        self._handshake_done = False
        self._runtime_state_seen = False
        self._handshake_inflight = False
        self._last_handshake_attempt = 0.0
        self._session.reset_handshake()
        self._log_poll_inflight = False
        self._log_poll_seq = None
        self._tracker.clear()
        self._append_output(OUTPUT_OWNER_REQUIRED)
        self._notify_ui_failure(
            "owner_required",
            True,
            OUTPUT_OWNER_REQUIRED,
            "UI control ownership restored.",
        )

    def _resolve_selected_from_rows(self) -> str:
        """
        NAME
            _resolve_selected_from_rows - Find selected test name from rows.
        """
        if self._tests_table is None:
            return ""
        total = int(self._tests_table.getEntry("totalCount").getDouble(0.0))
        rows = self._tests_table.getSubTable("rows")
        if total <= 0:
            return ""
        for i in range(total):
            row = rows.getSubTable(str(i))
            if row.getEntry("selected").getBoolean(False):
                return row.getEntry("name").getString("")
        return ""

    def _resolve_test_names_from_rows(self) -> List[str]:
        """
        NAME
            _resolve_test_names_from_rows - Return robot-known test names from the live tests table.
        """
        if self._tests_table is None:
            return []
        total = int(self._tests_table.getEntry("totalCount").getDouble(0.0))
        rows = self._tests_table.getSubTable("rows")
        if total <= 0:
            return []
        names: List[str] = []
        for i in range(total):
            row = rows.getSubTable(str(i))
            name = str(row.getEntry("name").getString("") or "").strip()
            if name and name not in names:
                names.append(name)
        return names

    def _sync_test_dropdown_values(self, names: List[str]) -> None:
        """
        NAME
            _sync_test_dropdown_values - Track the authoritative set of robot-known test names.
        """
        values = [str(name).strip() for name in names if str(name).strip()]
        current_selection = str(self._selected_test_var.get() or "").strip()
        if not values:
            values = [PROFILE_NONE]
        self._known_test_names = values
        if not current_selection:
            self._selected_test_var.set(values[0])
            self._last_selected_test = values[0]

    def _sync_test_selection(self, name: str) -> None:
        """
        NAME
            _sync_test_selection - Update the authoritative current-test selection from robot state.
        """
        if not name or name == "(none)":
            return
        current_name = str(self._selected_test_var.get() or "").strip()
        if name == current_name:
            self._sync_test_library_entry_to_selected_test(name)
            return
        self._last_selected_test = name
        self._selected_test_var.set(name)
        self._sync_test_library_entry_to_selected_test(name)
        if self._current_right_tab_text() == TEST_LIBRARY_TAB_LABEL:
            self._load_selected_test_into_active_group(force_replace=False)
        self._refresh_selected_test_scope_status()

    def _handle_close(self) -> None:
        """
        NAME
            _handle_close - Handle UI close and notify caller.
        """
        self._close_manual_duty_popup(stop_motor=True)
        self.release_lock()
        if self._on_close:
            self._on_close()
        self.destroy()

    def release_lock(self) -> None:
        """
        NAME
            release_lock - Release the UI lock if connected.
        """
        if self._tcp_connected:
            self._send_disconnect(force=True)
            disconnect(self._session)
