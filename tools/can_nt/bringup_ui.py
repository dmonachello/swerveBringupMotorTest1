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
import importlib
import time
import tkinter as tk
import uuid
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Callable, Dict, List, Optional, Tuple, Any

from .bridge_cmd_tracker import CommandTracker
from .bridge_ops import (
    connect,
    download_current_config,
    disconnect,
    push_config,
    runtime_activate,
    runtime_deactivate,
    send_command,
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
    HOST_ACTION_RECONNECT_UI_SESSION,
    HOST_UI_ACTIONS,
)
from tools.common.json_io import read_json, write_json
from tools.common.nt_labels import encode_label_for_nt
from tools.common.paths import repo_root, tests_deploy_path
from tools.common.tests_domain import collect_available_tests
from tools.common.config_lifecycle import ConfigLifecycleService
from tools.common.profiles import list_profile_names
from tools.common.profile_constants import KEY_DEVICE_TYPE, KEY_ID, KEY_LABEL as PROFILE_KEY_LABEL, KEY_MANUFACTURER
from tools.common.time_utils import timestamp_hms
from tools.common.app_versions import (
    APP_BRINGUP_UI_NAME,
    VERSIONS,
    VERSION_HEADER,
    format_version_line,
)
from tools.common.build_info import build_lines
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
DEFAULT_RUNTIME_STATE_RATE_TEXT = "2"
BUTTON_RUNTIME_ACTIVATE = "Runtime Activate"
BUTTON_RUNTIME_DEACTIVATE = "Runtime Deactivate"
BUTTON_PUSH_CONFIG = "Push Config"
BUTTON_DOWNLOAD_CONFIG = "Download Current Config"
BUTTON_SHOW_RUNTIME_STATE = "Show Runtime State"
OUTPUT_NOT_CONNECTED = "Not connected: command blocked."
OUTPUT_BUSY = "Busy: wait for current command to finish."
OUTPUT_NO_PROFILE = "No profile selected."
OUTPUT_PUSH_CANCELLED = "Config push cancelled."
OUTPUT_DOWNLOAD_CANCELLED = "Config download cancelled."
OUTPUT_PUSH_START_FMT = "PUSH {path} profile={profile}"
OUTPUT_DOWNLOAD_START_FMT = "DOWNLOAD {path}"
OUTPUT_RUNTIME_ACTIVATE_FMT = "CMD runtimeActivate \"{profile}\""
OUTPUT_RUNTIME_DEACTIVATE = "CMD runtimeDeactivate"
DOWNLOAD_FILENAME = "bringup_system.downloaded.json"
CONFIG_FILE_TYPES = (("JSON files", "*.json"), ("All files", "*.*"))
DEVICE_TYPE_MOTOR = "2"
MANUAL_DUTY_CMD_SET = "manualDeviceDutySet"
MANUAL_DUTY_CMD_CLEAR = "manualDeviceDutyClear"
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
MANUAL_DUTY_BLOCKED_TEXT = "Manual motor control blocked: not connected."
MANUAL_DUTY_BUSY_TEXT = "Manual motor control blocked: command in flight."
MANUAL_DUTY_NO_LABEL = ""
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

# Constants (visibility UI).
VIS_TAB_LABEL = "Visibility"
VIS_COL_DEVICE = "Device"
VIS_COL_IDENTITY = "Identity"
VIS_COL_LAST_SEEN = "Last Seen"
VIS_COL_PACKETS = "Packets"
VIS_COL_RATE = "Rate"
VIS_COL_PROBE_BUCKET = "Probe"
VIS_COL_PROBE_SCORE = "Probe Score"
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
VIS_PACKETS_UNKNOWN = "--"
VIS_RATE_UNKNOWN = "--"
VIS_RATE_FMT = "{value:.1f}/s"
VIS_TABLE_SPLIT_ORIENT = "vertical"
VIS_RAW_EMPTY_MESSAGE = "Select a CTRE row to inspect contributing raw IDs."
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
ATTACHMENT_KEY_TYPE = "type"
ATTACHMENT_TYPE_ACTIVE_PRESENCE_PROBE = "activePresenceProbe"
RUNTIME_PROBE_KEY_BUCKET = "bucket"
RUNTIME_PROBE_KEY_SCORE = "score"
RUNTIME_PROBE_KEY_MAX_SCORE = "maxScore"
VIS_RAW_COL_ARB_WIDTH = 96
VIS_RAW_COL_PACKETS_WIDTH = 72
VIS_RAW_COL_RATE_WIDTH = 72
VIS_RAW_COL_SMALL_WIDTH = 42
VIS_RAW_COL_API_WIDTH = 46
VIS_RAW_COL_PGN_WIDTH = 84
GENERATED_MODULE_NAME = "tools.can_nt.generated.robot_local_commands_generated"
GENERATED_INVENTORY_PATH = repo_root() / "tools" / "can_nt" / "generated" / "robot_local_command_inventory.json"
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
ACTION_KIND_REMOTE_COMMAND = "remoteCommand"
ACTION_SOURCE_ROBOT = "robot"


def _normalize_host_action_row(row: Dict[str, Any], default_source: str, default_kind: str) -> Dict[str, Any]:
    """
    NAME
        _normalize_host_action_row - Normalize a host UI action row to the merged action schema.
    """
    normalized = dict(row)
    normalized[INVENTORY_KEY_NAME] = str(row.get(INVENTORY_KEY_NAME, NT_VALUE_EMPTY)).strip()
    normalized[INVENTORY_KEY_UI_SECTION] = str(
        row.get(INVENTORY_KEY_UI_SECTION, NT_VALUE_EMPTY)
    ).strip()
    normalized[INVENTORY_KEY_UI_LABEL] = str(
        row.get(INVENTORY_KEY_UI_LABEL, normalized[INVENTORY_KEY_NAME])
    ).strip()
    normalized[INVENTORY_KEY_UI_DESCRIPTION] = str(
        row.get(INVENTORY_KEY_UI_DESCRIPTION, NT_VALUE_EMPTY)
    ).strip()
    normalized[INVENTORY_KEY_UI_ARGS_JSON] = str(
        row.get(INVENTORY_KEY_UI_ARGS_JSON, NT_VALUE_EMPTY)
    ).strip()
    normalized[INVENTORY_KEY_SHOW_IN_HOST_UI] = bool(
        row.get(INVENTORY_KEY_SHOW_IN_HOST_UI, True)
    )
    normalized[INVENTORY_KEY_ACTION_KIND] = str(
        row.get(INVENTORY_KEY_ACTION_KIND, default_kind)
    ).strip() or default_kind
    normalized[INVENTORY_KEY_SOURCE] = str(
        row.get(INVENTORY_KEY_SOURCE, default_source)
    ).strip() or default_source
    return normalized


def _build_host_ui_sections_from_inventory(commands: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    NAME
        _build_host_ui_sections_from_inventory - Build host UI sections from command inventory rows.
    """
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in commands:
        if not isinstance(row, dict):
            continue
        if not bool(row.get(INVENTORY_KEY_SHOW_IN_HOST_UI)):
            continue
        section = str(row.get(INVENTORY_KEY_UI_SECTION, NT_VALUE_EMPTY)).strip()
        if not section:
            continue
        grouped.setdefault(section, []).append(dict(row))
    sections: List[Dict[str, Any]] = []
    for section, items in grouped.items():
        items.sort(key=lambda row: str(row.get(INVENTORY_KEY_NAME, NT_VALUE_EMPTY)))
        sections.append({"section": section, "commands": items})
    return sections


def _merge_host_ui_actions(
    robot_actions: List[Dict[str, Any]], host_actions: List[Dict[str, Any]]
) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    """
    NAME
        _merge_host_ui_actions - Merge robot and host action metadata into one UI action model.
    """
    merged_actions = [
        _normalize_host_action_row(row, ACTION_SOURCE_ROBOT, ACTION_KIND_REMOTE_COMMAND)
        for row in robot_actions
        if isinstance(row, dict)
    ]
    merged_actions.extend(
        _normalize_host_action_row(row, ACTION_SOURCE_HOST, ACTION_KIND_HOST_LOCAL)
        for row in host_actions
        if isinstance(row, dict)
    )
    actions_by_name: Dict[str, Dict[str, Any]] = {}
    for row in merged_actions:
        name = str(row.get(INVENTORY_KEY_NAME, NT_VALUE_EMPTY)).strip()
        if not name:
            continue
        actions_by_name[name] = row
    return actions_by_name, _build_host_ui_sections_from_inventory(merged_actions)


def _load_generated_command_metadata() -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    """
    NAME
        _load_generated_command_metadata - Load merged robot and host UI action metadata.
    """
    robot_actions: List[Dict[str, Any]] = []
    try:
        generated = importlib.import_module(GENERATED_MODULE_NAME)
        commands_by_name = getattr(generated, "COMMANDS_BY_NAME", {})
        if isinstance(commands_by_name, dict):
            robot_actions = [
                dict(row) for row in commands_by_name.values() if isinstance(row, dict)
            ]
            return _merge_host_ui_actions(robot_actions, HOST_UI_ACTIONS)
    except Exception:
        pass
    try:
        payload = read_json(GENERATED_INVENTORY_PATH)
    except Exception:
        return _merge_host_ui_actions([], HOST_UI_ACTIONS)
    commands = payload.get(INVENTORY_KEY_COMMANDS)
    if not isinstance(commands, list):
        return _merge_host_ui_actions([], HOST_UI_ACTIONS)
    robot_actions = [dict(row) for row in commands if isinstance(row, dict)]
    return _merge_host_ui_actions(robot_actions, HOST_UI_ACTIONS)


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
    service = ConfigLifecycleService()
    try:
        payload = service.load_profiles_payload(service.default_paths().canonical_profiles_path)
        names = list_profile_names(payload)
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
    store_names = _load_tests_from_store(profile_name)
    if store_names is not None:
        return store_names
    try:
        path = tests_deploy_path()
        data = read_json(path)
        return collect_available_tests(data)
    except Exception:
        pass
    return []


def _normalize_profile_name(profile_name: object) -> str:
    """
    NAME
        _normalize_profile_name - Return a trimmed profile name or PROFILE_NONE.
    """
    if not isinstance(profile_name, str):
        return PROFILE_NONE
    name = profile_name.strip()
    if not name or name == PROFILE_NONE:
        return PROFILE_NONE
    return name


def _selectable_profiles() -> List[str]:
    """
    NAME
        _selectable_profiles - Return the UI profile list including the empty selection.
    """
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
    score = attachment.get(RUNTIME_PROBE_KEY_SCORE)
    max_score = attachment.get(RUNTIME_PROBE_KEY_MAX_SCORE)
    if isinstance(score, (int, float)) and isinstance(max_score, (int, float)):
        return f"{int(score)}/{int(max_score)}"
    if isinstance(score, (int, float)):
        return str(int(score))
    return VIS_LAST_SEEN_UNKNOWN


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
        self._last_selected_test = None
        self._last_sent_seq: Optional[int] = None
        self._nt_connected = False
        self._timeout_sec = 1.5
        self._client_id = str(uuid.uuid4())
        self._session_id: Optional[str] = None
        self._handshake_done = False
        self._handshake_inflight = False
        self._last_handshake_attempt = 0.0
        self._handshake_min_interval = 2.0
        self._handshake_warn_last = 0.0
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
        self._runtime_active_known: Optional[bool] = None
        self._robot_enabled_known = True
        self._runtime_state_notice_text = NT_VALUE_EMPTY
        self._runtime_state_notice_level = "warn"
        self._runtime_event_notice_text = NT_VALUE_EMPTY
        self._runtime_event_notice_level = "warn"
        self._runtime_state_path: Optional[str] = None
        self._runtime_state_path_mtime: Optional[float] = None
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
        self._manual_duty_popup: Optional[tk.Toplevel] = None
        self._manual_duty_var = tk.DoubleVar(value=MANUAL_DUTY_DEFAULT)
        self._manual_duty_value_var = tk.StringVar(
            value=MANUAL_DUTY_VALUE_FMT.format(value=MANUAL_DUTY_DEFAULT)
        )
        self._manual_duty_label = MANUAL_DUTY_NO_LABEL
        self._manual_duty_last_sent_value: Optional[float] = None
        self._manual_duty_last_sent_at = 0.0
        self._manual_duty_pending_after: Optional[str] = None
        self._profile_devices: Dict[str, Dict[str, Any]] = {}
        self._robot_selected_profile = PROFILE_NONE
        self._robot_active_runtime_profile = PROFILE_NONE
        self._last_profile_context = PROFILE_NONE
        self._ui_command_prefs = _load_ui_command_prefs()
        self._ui_auto_select_default_profile = _load_ui_auto_select_default_pref()
        self._ui_show_visibility_tab = _load_ui_show_visibility_tab_pref()
        self._ui_pref_vars: Dict[str, tk.BooleanVar] = {}
        self._build_menu()
        self._build_ui()
        self._apply_profile_selection(self._profile_box.get(), reload_views=True)
        self._poll_nt()
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
            header, text=BUTTON_RUNTIME_ACTIVATE, command=self._runtime_activate_from_ui
        ).pack(side="left", padx=(10, 0))
        ttk.Button(
            header, text=BUTTON_RUNTIME_DEACTIVATE, command=self._runtime_deactivate_from_ui
        ).pack(side="left", padx=(6, 0))
        ttk.Button(
            header, text=BUTTON_SHOW_RUNTIME_STATE, command=self._show_runtime_state_from_ui
        ).pack(side="left", padx=(6, 0))

        test_box = ttk.Combobox(header, values=tests, state="readonly", width=26)
        test_box.set(tests[0])
        test_box.bind("<<ComboboxSelected>>", self._on_test_selected)
        self._test_box = test_box
        self._last_selected_test = test_box.get()
        ttk.Label(header, text="Selected Test").pack(side="left", padx=(16, 4))
        test_box.pack(side="left")

        running = ttk.Label(header, text="Running: (none)", foreground="#374151")
        running.pack(side="left", padx=(16, 4))
        self._running_label = running
        self._pending_label = ttk.Label(header, text="", foreground="#b45309")
        self._pending_label.pack(side="left", padx=(16, 4))

        status = ttk.Label(header, text="NT Disconnected", foreground="#b32323")
        status.pack(side="right", padx=6)
        self._status_label = status

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
        output_body = ttk.Frame(output_panel)
        output_body.pack(fill="both", expand=True)
        self._output = tk.Text(output_body, height=10, wrap="word", state="disabled")
        self._output.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(output_body, command=self._output.yview)
        scroll.pack(side="right", fill="y")
        self._output.configure(yscrollcommand=scroll.set)
        self._output_notice_label = tk.Label(
            output_panel,
            text=NT_VALUE_EMPTY,
            anchor="w",
            padx=8,
            pady=4,
        )
        self._output_notice_label.pack_forget()

        live_panel = ttk.Frame(notebook)
        notebook.add(live_panel, text="Live Topology")
        self._build_live_panel(live_panel)

        visibility_panel = ttk.Frame(notebook)
        self._visibility_panel = visibility_panel
        self._build_visibility_panel(visibility_panel)
        self._apply_visibility_tab_pref()

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
            on_left_click=self._on_live_view_left_click,
        )
        self._live_view.set_show_groups(self._live_groups_var.get())
        self._live_view.set_visibility_enabled(self._visibility_enabled_var.get())
        self._live_view.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _build_visibility_panel(self, parent: tk.Widget) -> None:
        """
        NAME
            _build_visibility_panel - Build the visibility matrix tab.
        """
        header = ttk.Frame(parent, padding=VIS_PAD_HEADER)
        header.pack(fill=VIS_FILL_X)
        ttk.Label(header, textvariable=self._visibility_summary_var).pack(anchor=VIS_TREE_ANCHOR_W)

        body = ttk.Panedwindow(parent, orient="horizontal")
        body.pack(fill=VIS_FILL_BOTH, expand=True, padx=8, pady=8)

        topology_frame = ttk.Frame(body)
        body.add(topology_frame, weight=3)

        profile_name = self._profile_box.get() if hasattr(self, "_profile_box") else ""
        self._visibility_live_view = LiveTopologyView(
            topology_frame,
            profile_name,
            on_node_right_click=self._on_live_node_right_click,
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
        return views

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
        if not self._tcp_connected:
            self._append_output(MANUAL_DUTY_BLOCKED_TEXT)
            return
        if self._tracker.is_pending():
            self._append_output(MANUAL_DUTY_BUSY_TEXT)
            return
        label = str(getattr(node, DEVICE_KEY_LABEL, NT_VALUE_EMPTY)).strip()
        if not label:
            label = str(getattr(node, "label", NT_VALUE_EMPTY)).strip()
        if not label:
            return
        self._request_runtime_state_refresh()
        self._open_manual_duty_popup(label, int(event.x_root), int(event.y_root))

    def _on_live_view_left_click(self, _node: object, _event: tk.Event) -> None:
        """
        NAME
            _on_live_view_left_click - Stop manual motor duty on the next live-view left click.
        """
        self._request_runtime_state_refresh()
        if self._manual_duty_popup is not None:
            self._close_manual_duty_popup(stop_motor=True)

    def _open_manual_duty_popup(self, label: str, x_root: int, y_root: int) -> None:
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
        scale.pack(fill="x", pady=(8, 4))
        ttk.Label(body, textvariable=self._manual_duty_value_var).pack(anchor="center")
        self._manual_duty_popup = popup
        self._manual_duty_label = label
        self._manual_duty_var.set(MANUAL_DUTY_DEFAULT)
        self._manual_duty_value_var.set(
            MANUAL_DUTY_VALUE_FMT.format(value=MANUAL_DUTY_DEFAULT)
        )
        self._manual_duty_last_sent_value = None
        self._manual_duty_last_sent_at = 0.0
        self._manual_duty_pending_after = None
        scale.focus_set()

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
        popup = self._manual_duty_popup
        self._manual_duty_popup = None
        self._manual_duty_label = MANUAL_DUTY_NO_LABEL
        self._manual_duty_last_sent_value = None
        self._manual_duty_last_sent_at = 0.0
        self._manual_duty_var.set(MANUAL_DUTY_DEFAULT)
        self._manual_duty_value_var.set(
            MANUAL_DUTY_VALUE_FMT.format(value=MANUAL_DUTY_DEFAULT)
        )
        if popup is not None:
            try:
                popup.destroy()
            except Exception:
                pass
        if stop_motor and label:
            self._send_manual_duty_clear(label)

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

    def _flush_manual_duty_send(self) -> None:
        """
        NAME
            _flush_manual_duty_send - Send the current popup duty to the robot.
        """
        self._manual_duty_pending_after = None
        if not self._manual_duty_label:
            return
        if not self._tcp_connected:
            self._append_output(MANUAL_DUTY_BLOCKED_TEXT)
            return
        duty = max(
            MANUAL_DUTY_MIN,
            min(MANUAL_DUTY_MAX, float(self._manual_duty_var.get())),
        )
        if self._manual_duty_last_sent_value is not None:
            if abs(duty - self._manual_duty_last_sent_value) < 1e-6:
                return
        seq = self._send_tcp_command(
            MANUAL_DUTY_CMD_SET,
            {
                MANUAL_DUTY_ARG_NAME: self._manual_duty_label,
                MANUAL_DUTY_ARG_DUTY: duty,
            },
        )
        if seq is None:
            return
        self._manual_duty_last_sent_value = duty
        self._manual_duty_last_sent_at = time.time()
        self._append_output(
            MANUAL_DUTY_STATUS_FMT.format(
                label=self._manual_duty_label,
                duty=duty,
            )
        )

    def _send_manual_duty_clear(self, label: str) -> None:
        """
        NAME
            _send_manual_duty_clear - Stop the active manual-duty motor.
        """
        if not label or not self._tcp_connected:
            return
        seq = self._send_tcp_command(
            MANUAL_DUTY_CMD_CLEAR,
            {MANUAL_DUTY_ARG_NAME: label},
        )
        if seq is None:
            return
        self._append_output(MANUAL_DUTY_STOPPED_FMT.format(label=label))

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
            "  Manage selected profile, config sync, runtime activation, and incremental bringup.",
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
            "Runtime Activate:",
            "  Explicitly activates the selected profile runtime on the robot.",
            "  This is the only UI action that should activate runtime.",
            "",
            "Runtime Deactivate:",
            "  Explicitly deactivates the active runtime on the robot.",
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
        if not hasattr(self, "_test_box"):
            return
        name = _normalize_profile_name(profile_name)
        tests = _load_tests(name) or [PROFILE_NONE]
        self._test_box["values"] = tests
        if tests:
            self._test_box.set(tests[0])
            self._last_selected_test = tests[0]

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
        self._lines.append(line)
        if len(self._lines) > self._max_lines:
            self._lines = self._lines[-self._max_lines :]
        self._output.configure(state="normal")
        self._output.delete("1.0", "end")
        self._output.insert("end", "\n".join(self._lines) + "\n")
        self._output.see("end")
        self._output.configure(state="disabled")

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
        seq = ui_handshake(self._session, self._client_id, reset)
        if seq is not None:
            self._last_sent_seq = seq
            self._tracker.start("uiHandshake", payload, seq, now=time.time(), retryable=False)
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
        seq = ui_disconnect(self._session)
        if seq is not None:
            self._last_sent_seq = seq
            self._tracker.start("uiDisconnect", None, seq, now=time.time(), retryable=False)

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
        seq = ui_monitor(self._session, enabled)
        if seq is not None:
            self._last_sent_seq = seq
            self._tracker.start(label, args, seq, now=time.time())

    def _reconnect_ui_session(self) -> None:
        """
        NAME
            _reconnect_ui_session - Reconnect the REST session and issue a normal UI handshake.
        """
        self._handshake_done = False
        self._handshake_inflight = False
        self._last_handshake_attempt = 0.0
        self._session.reset_handshake()
        self._send_handshake(reset=False, force=True, log=True)

    def _dispatch_host_local_action(self, command: str) -> bool:
        """
        NAME
            _dispatch_host_local_action - Execute a host-local UI action.
        """
        if command == HOST_ACTION_RECONNECT_UI_SESSION:
            self._reconnect_ui_session()
            return True
        return False

    def _host_local_action_enabled(self, command: str) -> bool:
        """
        NAME
            _host_local_action_enabled - Return whether a host-local UI action should be enabled.
        """
        if command == HOST_ACTION_RECONNECT_UI_SESSION:
            return not self._tracker.is_pending() and not self._tcp_connected
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
        seq = self._send_tcp_command(name, args)
        if seq is not None:
            self._last_sent_seq = seq
            self._tracker.start(name, args, seq, now=time.time())

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
            return
        if self._tracker.is_pending():
            self._append_output("Busy: wait for current command to finish.")
            return
        ts = timestamp_hms()
        self._append_output(f"{ts} CMD {command}")
        self._last_cmd = (command, args)
        seq = send_command(self._session, command, args)
        if seq is not None:
            self._last_sent_seq = seq
            self._tracker.start(command, args, seq, now=time.time())

    def _on_test_selected(self, _event=None) -> None:
        """
        NAME
            _on_test_selected - Send selectTestByName when dropdown changes.
        """
        if not hasattr(self, "_test_box"):
            return
        if not self._tcp_connected:
            self._append_output("Not connected: selection blocked.")
            return
        if self._tracker.is_pending():
            self._append_output("Busy: wait for current command to finish.")
            return
        name = self._test_box.get().strip()
        if not name or name == "(none)":
            return
        if name == self._last_selected_test:
            return
        self._last_selected_test = name
        ts = timestamp_hms()
        self._append_output(f"{ts} CMD selectTestByName \"{name}\"")
        self._last_cmd = ("selectTestByName", {"name": name})
        seq = select_test_by_name(self._session, name)
        if seq is not None:
            self._last_sent_seq = seq
            self._tracker.start("selectTestByName", {"name": name}, seq, now=time.time())

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
        service = ConfigLifecycleService()
        return service.default_paths().canonical_profiles_path

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
    ) -> object:
        """
        NAME
            _run_blocking_status_operation - Run a blocking host-side operation with simple UI status output.
        """
        self._append_output(f"{timestamp_hms()} {start_line}")
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
        seq = runtime_activate(self._session, profile_name)
        if seq is not None:
            self._last_sent_seq = seq
            self._tracker.start("runtimeActivate", args, seq, now=time.time())

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
        seq = runtime_deactivate(self._session)
        if seq is not None:
            self._last_sent_seq = seq
            self._tracker.start("runtimeDeactivate", {}, seq, now=time.time())

    def _show_runtime_state_from_ui(self) -> None:
        """
        NAME
            _show_runtime_state_from_ui - Request the runtime-state payload through the top-bar control.
        """
        self._on_action(CMD_SHOW_RUNTIME_STATE)

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
            self._handshake_inflight = False
            self._session.reset_handshake()
            self._last_keepalive = 0.0
        for event in self._session.poll_events():
            self._handle_tcp_response(event)

        if self._ui_table is not None:
            session_id = self._ui_table.getEntry("state/sessionId").getString("")
            if session_id and session_id != self._session_id:
                self._session_id = session_id
                self._handshake_done = False
                self._handshake_inflight = False
                self._last_handshake_attempt = 0.0
                self._session.reset_handshake()
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
            nt_connected = True
        else:
            enabled = True
            estopped = False
            mode = "disabled"
            last_ack_ms = 0.0
            nt_connected = False
        if self._robot_enabled_known and not enabled:
            self._runtime_active_known = False
        self._robot_enabled_known = enabled
        if self._tests_table is not None:
            selected_name = self._tests_table.getEntry("selectedName").getString("")
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
            self._running_label.configure(text=f"Running: {running}")
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
            _poll_live_overlay - Poll runtime state for the live topology view.
        """
        if not self._live_enabled_var.get():
            return
        if self._runtime_state_pause_until is not None and now < self._runtime_state_pause_until:
            return
        if (now - self._runtime_state_last_poll) < (
            self._runtime_state_interval * self._runtime_state_backoff
        ):
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
        label = getattr(self, "_output_notice_label", None)
        if label is None:
            return
        if self._runtime_state_notice_text:
            message = self._runtime_state_notice_text
            level = self._runtime_state_notice_level
        elif self._runtime_event_notice_text:
            message = self._runtime_event_notice_text
            level = self._runtime_event_notice_level
        else:
            label.configure(text=NT_VALUE_EMPTY)
            label.pack_forget()
            return
        if level == "error":
            bg = NOTICE_COLOR_ERROR_BG
            fg = NOTICE_COLOR_ERROR_FG
        elif level == "warn":
            bg = NOTICE_COLOR_WARN_BG
            fg = NOTICE_COLOR_WARN_FG
        else:
            bg = NOTICE_COLOR_INFO_BG
            fg = NOTICE_COLOR_INFO_FG
        label.configure(text=message, bg=bg, fg=fg)
        label.pack(fill="x", padx=8, pady=(6, 8))

    def _apply_runtime_state_payload(self, payload: Dict[str, Any]) -> None:
        """
        NAME
            _apply_runtime_state_payload - Apply live runtime-state JSON.
        """
        latest_runtime_devices: Dict[str, Dict[str, Any]] = {}
        runtime_active = payload.get("runtimeActive")
        if isinstance(runtime_active, bool):
            self._runtime_active_known = runtime_active
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
        live_views = self._iter_live_views()
        if not live_views:
            return
        changed = False
        for live_view in live_views:
            changed = live_view.update_runtime_state(payload) or changed
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
        if stale_state:
            self._set_runtime_state_notice(
                "Robot state stale (code not running?)", "warn"
            )
        elif estopped:
            self._set_runtime_state_notice("Robot E-Stop. Manual run blocked.", "error")
        elif self._runtime_active_known is False:
            self._set_runtime_state_notice(
                "Runtime inactive. Click Runtime Activate.", "warn"
            )
        elif not enabled:
            self._set_runtime_state_notice(
                "Robot disabled. Enable teleop to run motors.", "info"
            )
        else:
            self._clear_runtime_state_notice()
        for live_view in self._iter_live_views():
            if stale_state:
                live_view.set_runtime_state_notice("Robot state stale (code not running?)", "warn")
            elif estopped:
                live_view.set_runtime_state_notice("Robot E-Stop. Manual run blocked.", "error")
            elif self._runtime_active_known is False:
                live_view.set_runtime_state_notice("Runtime inactive. Click Runtime Activate.", "warn")
            elif not enabled:
                live_view.set_runtime_state_notice("Robot disabled. Enable teleop to run motors.", "info")
            else:
                live_view.clear_runtime_state_notice()

    def _handle_tcp_response(self, event: BridgeEvent) -> None:
        """
        NAME
            _handle_tcp_response - Handle an inbound REST-session response payload.
        """
        msg_type = event.type
        name = event.name.strip()
        seq = event.seq
        if name.lower() == "uiping":
            return
        if msg_type in ("ack", "out") and self._is_handshake_required(event):
            self._handle_handshake_required()
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
                if text:
                    for line in text.splitlines():
                        if self._should_skip_out_line(line):
                            continue
                        self._append_output(line)
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
            self._apply_live_runtime_notice_from_ack(name, status, message)
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
            if text:
                for line in text.splitlines():
                    self._remember_out_line(line)
                    self._append_output(f"  {line}")
            if json_payload:
                self._append_output("  json: " + str(json_payload))
                try:
                    data = json.loads(json_payload)
                except Exception:
                    data = None
            if name == "uiHandshake" and isinstance(data, dict):
                min_next = data.get("minNextSeq")
                if isinstance(min_next, (int, float)):
                    self._seq = int(min_next) - 1
                    self._seq_seeded = True
                session_id = data.get("sessionId")
                session_id_value = session_id if isinstance(session_id, str) else ""
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
                self._handshake_inflight = False
                self._session.reset_handshake()
        if msg_type in ("ack", "out"):
            self._tracker.handle_event(event)
            command_lower = str(event.name or "").strip().lower()
            if command_lower in {
                "runtimeactivate",
                "runtimedeactivate",
                "manualdevicedutyset",
                "manualdevicedutyclear",
                "activepresenceprobe",
            }:
                self.after_idle(self._request_runtime_state_refresh)

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

    def _update_action_enabled(self) -> None:
        """
        NAME
            _update_action_enabled - Enable/disable UI actions based on state.
        """
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
                continue
            btn.state(
                ["!disabled"] if self._host_local_action_enabled(command) else ["disabled"]
            )
        if hasattr(self, "_test_box"):
            self._test_box.configure(state=state)
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

    def _handle_handshake_required(self) -> None:
        """
        NAME
            _handle_handshake_required - Reset handshake state on server warning.
        """
        self._handshake_done = False
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

    def _sync_test_selection(self, name: str) -> None:
        """
        NAME
            _sync_test_selection - Update dropdown to match robot selection.
        """
        if not hasattr(self, "_test_box"):
            return
        if not name or name == "(none)":
            return
        if name == self._test_box.get():
            return
        self._last_selected_test = name
        self._test_box.set(name)

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
