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
from copy import deepcopy
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
from .can_bus_report_service import build_host_can_bus_report
from .passive_discovery_integration_service import (
    ENGINE_LABEL_LEGACY,
    ENGINE_LABEL_NEW,
    SECTION_CONSOLE,
    SECTION_ENRICHMENT,
    SECTION_INTERPRETATION,
    SECTION_MANUAL,
    SECTION_PASSIVE,
    SECTION_PRESENCE_CHECK,
    SECTION_PROBE,
    SECTION_PROFILE_INVENTORY,
    SECTION_TOPOLOGY_VIEW,
    FAULT_SNAPSHOT_KEY_CANDIDATE_COUNT,
    FAULT_SNAPSHOT_KEY_RAN_AT,
    FAULT_SNAPSHOT_KEY_RENDERED_TEXT,
    FAULT_SNAPSHOT_KEY_RESULT,
    TEXT_EMPTY,
    build_evidence_fault_snapshot,
    build_interpreted_evidence_row,
    classify_device_type,
    build_console_snapshot_from_entries as build_console_snapshot_from_entries_shared,
    build_enrichment_run_snapshot,
    build_live_passive_result,
    build_passive_device_detail_snapshot,
    build_passive_visibility_deep_dive_text,
    build_interpreted_device_detail_snapshot,
    build_manual_snapshot,
    build_runtime_probe_snapshot,
    build_runtime_presence_catalog,
    default_enrichment_run_snapshot,
    default_evidence_engine_status,
    evidence_engine_banner_text,
    evidence_overall_title,
    evidence_section_title,
    enrichment_run_status_text,
    index_run_result_by_identity,
    load_profile_device_catalog,
    normalize_evidence_engine_status,
    resolve_passive_visibility_device_record,
    section_engine_label,
    INTERPRET_KEY_CONFLICTED,
    INTERPRET_KEY_CONSOLE,
    INTERPRET_KEY_CONSOLE_TEXT,
    INTERPRET_KEY_CONFIDENCE,
    INTERPRET_KEY_DEVICE_TYPE,
    INTERPRET_KEY_ENRICHMENT_TEXT,
    INTERPRET_KEY_EXISTENCE,
    INTERPRET_KEY_IDENTITY,
    INTERPRET_KEY_EVENT_LOG,
    INTERPRET_KEY_LABEL,
    INTERPRET_KEY_LAST_EVALUATION_AT,
    INTERPRET_KEY_LAST_KNOWN_GOOD_AT,
    INTERPRET_KEY_LAST_SEEN_MISSING_AT,
    INTERPRET_KEY_LAST_SEEN_PRESENT_AT,
    INTERPRET_KEY_LAST_STATE_CHANGE_AT,
    INTERPRET_KEY_MANUAL,
    INTERPRET_KEY_MANUAL_TEXT,
    INTERPRET_KEY_CHANGE_REASON,
    INTERPRET_KEY_DIRTY,
    INTERPRET_KEY_DIRTY_REASONS,
    INTERPRET_KEY_NOTES_TEXT,
    INTERPRET_KEY_OPERABILITY,
    INTERPRET_KEY_PASSIVE,
    INTERPRET_KEY_PASSIVE_TEXT,
    INTERPRET_KEY_PRESENCE_REASONS,
    INTERPRET_KEY_PRESENCE_SCORE,
    INTERPRET_KEY_PRESENCE_STATE,
    INTERPRET_KEY_PRESENCE_TEXT,
    INTERPRET_KEY_PROBE,
    INTERPRET_KEY_PROBE_SCORE,
    INTERPRET_KEY_PROBE_TEXT,
    INTERPRET_KEY_SOURCE_SCORES,
    INTERPRET_KEY_STATE,
    DEVICE_CLASS_INFRASTRUCTURE,
    DEVICE_CLASS_MOTION,
    DEVICE_CLASS_UNPROFILED,
    PRESENCE_KEY_AGE_TEXT,
    PRESENCE_KEY_BUCKET,
    PRESENCE_KEY_CONFIDENCE,
    PRESENCE_KEY_EXISTENCE,
    PRESENCE_KEY_MESSAGE,
    PRESENCE_KEY_SCORE,
    PRESENCE_KEY_SOURCE,
    CONSOLE_KEY_HAS_ERROR,
    CONSOLE_KEY_HAS_WARN,
    CONSOLE_KEY_SUMMARY,
    CONSOLE_SCOPE_DEVICES,
    CONSOLE_SCOPE_SYSTEM,
    MANUAL_SUMMARY_FIELD,
    PROBE_SUMMARY_FIELD,
    PROBE_TEXT_FIELD,
    ENRICHMENT_RUN_METADATA_KEY,
    ENRICHMENT_RUN_DEVICES_KEY,
    ENRICHMENT_RUN_LABEL,
    ENRICHMENT_RUN_RECORDS_KEY,
    ENRICHMENT_RUN_STATUS_KEY,
    ENRICHMENT_RUN_SUMMARY_KEY,
    ENRICHMENT_RUN_WARNINGS_KEY,
    ENRICHMENT_SOURCE_CONSOLE_LOG,
    ENRICHMENT_SOURCE_CTRE,
    ENRICHMENT_SOURCE_TOPOLOGY,
    ENRICHMENT_DEVICE_KEY_CTRE,
)
from .bridge_ops import (
    _resolve_device_type_label,
    connect,
    download_current_config,
    disconnect,
    lifecycle_activate,
    lifecycle_deactivate_active,
    push_config,
    runtime_activate,
    runtime_deactivate,
    send_command,
    show_lifecycle_state,
    select_test_by_name,
    ui_disconnect,
    ui_handshake,
    ui_monitor,
    ui_poll_log,
    ui_ping,
)
from .bridge_session import BridgeEvent, BridgeSession
from .dsl_reference import (
    TEST_SOURCE_REFERENCE_GEOMETRY,
    TEST_SOURCE_REFERENCE_OVERVIEW,
    TEST_SOURCE_REFERENCE_TITLE,
    TEST_SOURCE_REFERENCE_TREE_WIDTH,
    collect_dsl_reference_topic_map,
    dsl_reference_topics,
    render_dsl_reference_detail,
)
from .host_ui_actions import (
    ACTION_KIND_HOST_LOCAL,
    ACTION_SOURCE_HOST,
    HOST_ACTION_DSL_TEST_IMPORT,
    HOST_ACTION_DSL_TEST_VALIDATE,
    HOST_ACTION_RECONNECT_UI_SESSION,
    HOST_UI_ACTIONS,
)
from .host_ui_state_service import (
    ACTIVE_GROUP_EDIT_BLOCKED_LOCKED_TEXT as SHARED_ACTIVE_GROUP_EDIT_BLOCKED_LOCKED_TEXT,
    HOST_ACTION_BLOCKED_BUSY_TEXT as SHARED_HOST_ACTION_BLOCKED_BUSY_TEXT,
    HOST_ACTION_BLOCKED_NOT_CONNECTED_TEXT as SHARED_HOST_ACTION_BLOCKED_NOT_CONNECTED_TEXT,
    MANUAL_DUTY_BLOCKED_CONTROLLED_SCOPE_TEXT as SHARED_MANUAL_DUTY_BLOCKED_CONTROLLED_SCOPE_TEXT,
    MANUAL_DUTY_BLOCKED_DISABLED_TEXT as SHARED_MANUAL_DUTY_BLOCKED_DISABLED_TEXT,
    MANUAL_DUTY_BLOCKED_ESTOP_TEXT as SHARED_MANUAL_DUTY_BLOCKED_ESTOP_TEXT,
    MANUAL_DUTY_BLOCKED_NOT_CONNECTED_TEXT as SHARED_MANUAL_DUTY_BLOCKED_NOT_CONNECTED_TEXT,
    MANUAL_DUTY_BLOCKED_STALE_TEXT as SHARED_MANUAL_DUTY_BLOCKED_STALE_TEXT,
    MANUAL_DUTY_BLOCKED_TRANSITION_TEXT as SHARED_MANUAL_DUTY_BLOCKED_TRANSITION_TEXT,
    MANUAL_DUTY_BLOCKED_WAITING_TEXT as SHARED_MANUAL_DUTY_BLOCKED_WAITING_TEXT,
    OUTPUT_NO_SELECTED_TEST as SHARED_OUTPUT_NO_SELECTED_TEST,
    PROFILE_NONE as SHARED_PROFILE_NONE,
    RUNTIME_FETCH_BLOCK_BUSY,
    SELECTED_TEST_STATUS_BLOCKED_DISABLED as SHARED_SELECTED_TEST_STATUS_BLOCKED_DISABLED,
    SELECTED_TEST_STATUS_BLOCKED_ESTOP as SHARED_SELECTED_TEST_STATUS_BLOCKED_ESTOP,
    SELECTED_TEST_STATUS_BLOCKED_NOT_TELEOP as SHARED_SELECTED_TEST_STATUS_BLOCKED_NOT_TELEOP,
    SELECTED_TEST_STATUS_LOADED_NOT_ACTIVATED as SHARED_SELECTED_TEST_STATUS_LOADED_NOT_ACTIVATED,
    SELECTED_TEST_STATUS_MANUAL_RESTORED as SHARED_SELECTED_TEST_STATUS_MANUAL_RESTORED,
    SELECTED_TEST_STATUS_SCOPE_SWAP_REQUIRED as SHARED_SELECTED_TEST_STATUS_SCOPE_SWAP_REQUIRED,
    RUNNABLE_SCOPE_DETAIL_MANUAL_EMPTY as SHARED_RUNNABLE_SCOPE_DETAIL_MANUAL_EMPTY,
    RUNNABLE_SCOPE_DETAIL_MANUAL_NOT_ACTIVATED as SHARED_RUNNABLE_SCOPE_DETAIL_MANUAL_NOT_ACTIVATED,
    RUNNABLE_SCOPE_DETAIL_MANUAL_NOT_TELEOP as SHARED_RUNNABLE_SCOPE_DETAIL_MANUAL_NOT_TELEOP,
    RUNNABLE_SCOPE_DETAIL_SELECT_PROFILE as SHARED_RUNNABLE_SCOPE_DETAIL_SELECT_PROFILE,
    RUNNABLE_SCOPE_DETAIL_SELECTED_TEST_NOT_ACTIVATED as SHARED_RUNNABLE_SCOPE_DETAIL_SELECTED_TEST_NOT_ACTIVATED,
    RUNNABLE_SCOPE_DETAIL_SELECTED_TEST_NOT_TELEOP as SHARED_RUNNABLE_SCOPE_DETAIL_SELECTED_TEST_NOT_TELEOP,
    RUNNABLE_SCOPE_KIND_MANUAL,
    RUNNABLE_SCOPE_KIND_SELECTED_TEST,
    RUNNABLE_STATE_LEVEL_ERROR,
    RUNNABLE_STATE_LEVEL_NEUTRAL,
    RUNNABLE_STATE_LEVEL_READY,
    RUNNABLE_STATE_LEVEL_WARN,
    RUNNABLE_SCOPE_PANEL_DISCONNECTED_DETAIL as SHARED_RUNNABLE_SCOPE_PANEL_DISCONNECTED_DETAIL,
    RUNNABLE_SCOPE_PANEL_READY_DETAIL as SHARED_RUNNABLE_SCOPE_PANEL_READY_DETAIL,
    RUNNABLE_SCOPE_PANEL_WAITING_DETAIL as SHARED_RUNNABLE_SCOPE_PANEL_WAITING_DETAIL,
    TEST_ACTIVE_GROUP_STATUS_ENABLED as SHARED_TEST_ACTIVE_GROUP_STATUS_ENABLED,
    TEST_ACTIVE_GROUP_STATUS_INVALID as SHARED_TEST_ACTIVE_GROUP_STATUS_INVALID,
    TEST_ACTIVE_GROUP_STATUS_LOCKED as SHARED_TEST_ACTIVE_GROUP_STATUS_LOCKED,
    TEST_ACTIVE_GROUP_STATUS_NOT_ACTIVATED as SHARED_TEST_ACTIVE_GROUP_STATUS_NOT_ACTIVATED,
    TEST_SCOPE_PANEL_NEUTRAL_LEVEL,
    TEST_SCOPE_STATUS_BLOCKED_DISABLED_DETAIL as SHARED_TEST_SCOPE_STATUS_BLOCKED_DISABLED_DETAIL,
    TEST_SCOPE_STATUS_BLOCKED_ESTOP_DETAIL as SHARED_TEST_SCOPE_STATUS_BLOCKED_ESTOP_DETAIL,
    TEST_SCOPE_STATUS_BLOCKED_NOT_TELEOP_DETAIL as SHARED_TEST_SCOPE_STATUS_BLOCKED_NOT_TELEOP_DETAIL,
    TEST_SCOPE_STATUS_LOADED_NOT_ACTIVATED_DETAIL as SHARED_TEST_SCOPE_STATUS_LOADED_NOT_ACTIVATED_DETAIL,
    TEST_SCOPE_STATUS_MANUAL_RESTORED_DETAIL as SHARED_TEST_SCOPE_STATUS_MANUAL_RESTORED_DETAIL,
    TEST_SCOPE_STATUS_MISSING_DEVICE_PREFIX as SHARED_TEST_SCOPE_STATUS_MISSING_DEVICE_PREFIX,
    TEST_SCOPE_STATUS_NO_SELECTION_DETAIL as SHARED_TEST_SCOPE_STATUS_NO_SELECTION_DETAIL,
    TEST_SCOPE_STATUS_REQUIRED_UNAVAILABLE_DETAIL as SHARED_TEST_SCOPE_STATUS_REQUIRED_UNAVAILABLE_DETAIL,
    TEST_SCOPE_STATUS_READY_DETAIL as SHARED_TEST_SCOPE_STATUS_READY_DETAIL,
    TEST_SCOPE_STATUS_SCOPE_SWAP_REQUIRED_DETAIL as SHARED_TEST_SCOPE_STATUS_SCOPE_SWAP_REQUIRED_DETAIL,
    ActiveGroupMemberRowState,
    SelectedTestScopeState,
    SelectedTestPanelState,
    DiagnosticProfileState,
    HostActionAccessState,
    RunnableScopeState,
    RuntimeStateFetchState,
    TopologySceneState,
    UiContextState,
    resolve_active_group_edit_action_state,
    resolve_manual_duty_access_state,
    resolve_manual_duty_action_state,
    resolve_manual_duty_scope_state,
    resolve_active_group_summary_state,
    resolve_manual_duty_binding_state,
    resolve_diagnostic_profile_state,
    resolve_override_action_state,
    resolve_runtime_state_fetch_state,
    resolve_scope_control_state,
    resolve_scope_activation_notice,
    resolve_selected_test_runtime_block_reason,
    resolve_selected_test_panel_state,
    resolve_selected_test_scope_state,
    resolve_topology_scene_state,
    resolve_tests_active_group_member_rows,
    resolve_runnable_scope_state,
    resolve_ui_context_state,
    should_clear_runtime_event_notice,
)
from .ui_theme import (
    UI_THEME_DEFAULT,
    UiThemePalette,
    apply_ttk_theme,
    get_ui_theme_palette,
    list_ui_theme_names,
)
from .status import SS__NORMAL
from tools.common.json_io import read_json, write_json
from tools.common.config_api import ConfigEditSession, ConfigRepository, rename_profile as rename_profile_payload
from tools.common.paths import repo_root, tests_deploy_path
from tools.common.profile_constants import KEY_DEFAULT_PROFILE, KEY_DSL_TESTS
from tools.common.topology_parse import parse_bridge_groups, topology_profile_from_payload
from tools.common.tests_domain import collect_available_tests
from tools.common.config_lifecycle import LocalConfigQueryService
from tools.common.profiles import list_profile_names
from tools.common.profile_constants import (
    INTERFACE_CAN,
    KEY_DEVICE_REF,
    KEY_DEVICE_TYPE,
    KEY_DEVICES,
    KEY_ID,
    KEY_INTERFACE,
    KEY_LABEL as PROFILE_KEY_LABEL,
    KEY_LAYOUT,
    KEY_MANUFACTURER,
    KEY_MODEL,
    KEY_NODE_CLASS,
    KEY_NODE_KEY,
    KEY_NODE_TYPE,
    KEY_OBJECT_TYPE,
    KEY_PROFILE_DEVICES,
    KEY_PROFILES,
    KEY_TAGS,
    KEY_TOPOLOGY,
    KEY_TOPOLOGY_NODES,
    KEY_TOPOLOGY_PROFILES,
    KEY_TOPOLOGY_SOURCE,
    KEY_TOPOLOGY_VERSION,
    KEY_TOPOLOGY_VIEW,
    TYPE_ENCODER_EXTERNAL,
    TYPE_MOTOR,
    get_device_interface,
    KEY_BUS,
    LAYOUT_KEY_ROW,
    LAYOUT_KEY_X,
)
from tools.common.profile_constants import KEY_ENABLED
from tools.common.profile_constants import KEY_TYPE
from tools.common.group_contract import (
    find_group_by_name,
    group_member_labels,
    group_member_map,
    resolve_group_motor_targets,
)
from tools.common.topology_render import shape_kind_for_category
from tools.common.robot_test_dsl import (
    compile_source,
    config_library_test_runnable_map,
    copy_external_library_test_into_root_payload,
    create_blank_test_in_root_payload,
    copy_test_into_root_payload,
    device_catalog,
    delete_external_library_test,
    delete_test_from_root_payload,
    DslServiceError,
    external_library_test_runnable_map,
    import_test_into_config_library,
    import_test_into_external_library,
    import_test_into_root_payload,
    list_external_library_test_names,
    profile_test_runnable_map,
    read_external_library_test_source,
    rename_external_library_test,
    rename_test_in_root_payload,
    render_validation_text,
    resolve_global_library_test_names,
    resolve_profile_test_names,
    resolve_profile_device_dsl_type,
    resolve_profile_test_set_name,
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
from .can_profiles import (
    get_default_profile,
    get_profile,
    get_profiles_load_error,
    list_profiles,
    reload_profiles,
    set_profiles_path_override,
)
from tools.config.schema_store import ConfigSchemaStore
from tools.can_topology.live_topology_view import (
    LiveTopologyView,
    TOPOLOGY_LENS_EVIDENCE,
    TOPOLOGY_LENS_RUNTIME,
    TOPOLOGY_LENS_VISIBILITY,
)
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

# Constants (presence override buckets and empty values).
NT_VALUE_EMPTY = ""
PRESENCE_VALUE_HIGH = "HIGH"
PRESENCE_VALUE_LOW = "LOW"
PRESENCE_VALUE_NONE = "NONE"
PRESENCE_VALUES = {
    PRESENCE_VALUE_HIGH,
    PRESENCE_VALUE_LOW,
    PRESENCE_VALUE_NONE,
}


class _RestValueAdapter:
    """
    NAME
        _RestValueAdapter - Small value wrapper matching the NT entry getter shape.
    """

    def __init__(self, value: Any) -> None:
        self._value = value

    def getString(self, default: str) -> str:
        value = self._value
        if value is None:
            return default
        if isinstance(value, str):
            return value
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    def getDouble(self, default: float) -> float:
        value = self._value
        try:
            return float(value)
        except Exception:
            return default

    def getBoolean(self, default: bool) -> bool:
        value = self._value
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in ("true", "1", "yes", "on"):
                return True
            if normalized in ("false", "0", "no", "off", ""):
                return False
        return default


class _RestTableAdapter:
    """
    NAME
        _RestTableAdapter - Small nested-table wrapper matching the NT table getter shape.
    """

    def __init__(self, payload: Any) -> None:
        self._payload = payload if isinstance(payload, dict) else {}

    @classmethod
    def from_runtime_state(
        cls,
        session_state: Dict[str, Any],
        runtime_state: Dict[str, Any],
        fetched_at_ms: float = 0.0,
    ) -> "_RestTableAdapter":
        last_ack_ms = float(fetched_at_ms or 0.0)
        state = {
            "sessionId": str(session_state.get("sessionId", "") or ""),
            "enabled": bool(runtime_state.get("enabled", False)),
            "estopped": bool(runtime_state.get("estopped", False)),
            "mode": str(runtime_state.get("mode", "disabled") or "disabled"),
            "lastAckMs": last_ack_ms,
            "selectedProfile": str(runtime_state.get("selectedProfile", PROFILE_NONE) or PROFILE_NONE),
            "activeRuntimeProfile": str(runtime_state.get("activeRuntimeProfile", PROFILE_NONE) or PROFILE_NONE),
        }
        return cls({"state": state})

    @classmethod
    def from_tests_state(cls, tests_state: Dict[str, Any]) -> "_RestTableAdapter":
        rows_payload: Dict[str, Any] = {}
        rows = tests_state.get("rows")
        if isinstance(rows, list):
            for index, row in enumerate(rows):
                if not isinstance(row, dict):
                    continue
                required_devices = row.get("requiredDevices")
                required_text = ""
                if isinstance(required_devices, list):
                    required_text = ",".join(
                        str(part).strip() for part in required_devices if str(part).strip()
                    )
                row_payload = dict(row)
                row_payload["requiredDevices"] = required_text
                rows_payload[str(index)] = row_payload
        run = tests_state.get("run")
        run_payload = run if isinstance(run, dict) else {}
        selected_name = ""
        active_name = ""
        active_status = ""
        run_all_active = False
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict):
                    continue
                if bool(row.get("selected", False)) and not selected_name:
                    selected_name = str(row.get("name", "") or "").strip()
                status = str(row.get("status", "") or "").strip().lower()
                if status == "running" and not active_name:
                    active_name = str(row.get("name", "") or "").strip()
                    active_status = status
        table_payload = {
            "totalCount": len(rows_payload),
            "selectedName": selected_name,
            "activeName": active_name,
            "activeStatus": active_status,
            "runAllActive": run_all_active,
            "runId": run_payload.get("runId", 0),
            "runState": str(run_payload.get("state", "") or ""),
            "runTest": str(run_payload.get("test", "") or ""),
            "runResult": str(run_payload.get("result", "") or ""),
            "runStatus": str(run_payload.get("status", "") or ""),
            "runMessage": str(run_payload.get("message", "") or ""),
            "runStartedAtMs": run_payload.get("startedAtMs", 0),
            "runFinishedAtMs": run_payload.get("finishedAtMs", 0),
            "rows": rows_payload,
        }
        return cls(table_payload)

    def getEntry(self, key: str) -> _RestValueAdapter:
        value: Any = self._payload
        for part in str(key or "").split("/"):
            if not isinstance(value, dict):
                value = None
                break
            value = value.get(part)
        return _RestValueAdapter(value)

    def getSubTable(self, key: str) -> "_RestTableAdapter":
        value: Any = self._payload
        for part in str(key or "").split("/"):
            if not isinstance(value, dict):
                value = {}
                break
            value = value.get(part, {})
        return _RestTableAdapter(value if isinstance(value, dict) else {})

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
PROFILE_NONE = SHARED_PROFILE_NONE
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
BUTTON_SAVE_CONFIG = "Save Config"
BUTTON_NEW_BLANK_CONFIG = "New Blank Config..."
BUTTON_OPEN_CONFIG = "Open Config..."
BUTTON_SAVE_CONFIG_AS = "Save Config As..."
BUTTON_RENAME_PROFILE = "Rename Profile..."
BUTTON_DOWNLOAD_CONFIG = "Download Current Config"
BUTTON_RUNTIME_ACTIVATE = "Runtime Activate"
BUTTON_RUNTIME_DEACTIVATE = "Runtime Deactivate"
BUTTON_SHOW_RUNTIME_STATE = "Show Runtime State"
BUTTON_SHOW_LIFECYCLE_STATE = "Show Scope State"
CMD_PRINT_CAN_DIAG = "printCANdiag"
GROUP_SOURCE_MANUAL = "manual"
GROUP_SOURCE_SELECTED_TEST = "selected test"
GROUP_SOURCE_LABEL_PREFIX = "Active Group Source: "
GROUP_SOURCE_LABEL_MANUAL = GROUP_SOURCE_LABEL_PREFIX + GROUP_SOURCE_MANUAL
GROUP_SOURCE_LABEL_SELECTED_TEST = GROUP_SOURCE_LABEL_PREFIX + GROUP_SOURCE_SELECTED_TEST
OUTPUT_NOT_CONNECTED = SHARED_HOST_ACTION_BLOCKED_NOT_CONNECTED_TEXT
OUTPUT_BUSY = SHARED_HOST_ACTION_BLOCKED_BUSY_TEXT
OUTPUT_NO_PROFILE = "No profile selected."
OUTPUT_NO_SELECTED_TEST = SHARED_OUTPUT_NO_SELECTED_TEST
OUTPUT_PUSH_CANCELLED = "Config push cancelled."
OUTPUT_DOWNLOAD_CANCELLED = "Config download cancelled."
OUTPUT_PUSH_START_FMT = "PUSH {path} profile={profile}"
OUTPUT_PUSH_PROGRESS_FMT = "Push Config: {detail}"
OUTPUT_PUSH_SUCCESS = "Push Config: OK"
OUTPUT_PUSH_FAILURE = "Push Config: FAILED"
OUTPUT_DOWNLOAD_START_FMT = "DOWNLOAD {path}"
OUTPUT_RUNTIME_ACTIVATE_FMT = "CMD runtimeActivate \"{profile}\""
OUTPUT_RUNTIME_DEACTIVATE = "CMD runtimeDeactivate"
OUTPUT_RUNTIME_STATE_FETCH = "CMD showRuntimeState"
OUTPUT_RUNTIME_STATE_FETCH_OUT = "OUT showRuntimeState"
OUTPUT_RUNTIME_STATE_FETCH_EMPTY = "Runtime state fetch returned no data."
OUTPUT_EVIDENCE_ENRICHMENT_RUN_FMT = "RUN enrichment profile={profile} rio={rio} devices={devices}"
OUTPUT_EVIDENCE_ENRICHMENT_RESULT_FMT = "OUT enrichment deviceMatches={devices} warnings={warnings}"
OUTPUT_EVIDENCE_ENRICHMENT_SOURCE_FMT = "  {source}: status={status} summary={summary}"
OUTPUT_EVIDENCE_ENRICHMENT_SOURCE_UNKNOWN = "unknown"
OUTPUT_EVIDENCE_ENRICHMENT_SOURCES = (
    ENRICHMENT_SOURCE_TOPOLOGY,
    ENRICHMENT_SOURCE_CTRE,
    ENRICHMENT_SOURCE_CONSOLE_LOG,
)
OUTPUT_LIFECYCLE_ACTIVATE_FMT = (
    "CMD lifecycleActivate \"{label}\" mode={mode} membershipMode={membership_mode}"
)
OUTPUT_LIFECYCLE_DEACTIVATE_FMT = "CMD lifecycleDeactivate \"{label}\""
OUTPUT_LIFECYCLE_DEACTIVATE_ACTIVE = "CMD lifecycleDeactivateActive"
OUTPUT_NO_ACTIVE_CONTROLLED_SESSION = "No active controlled session to deactivate."
OUTPUT_GROUP_REPLACE_FMT = "CMD groupReplaceMembers \"{group}\" members={count}"
OUTPUT_SELECTED_PROFILE_PREFIX = "Selected profile: "
OUTPUT_GROUP_RUN_FMT = "CMD groupRunTest \"{group}\""
OUTPUT_OWNER_REQUIRED = "Owning control client required. Use Reconnect UI Session to reclaim control."
SCOPE_TRANSITION_WAIT_TIMEOUT_SEC = 3.0
DOWNLOAD_FILENAME = "bringup_system.downloaded.json"
CONFIG_FILE_TYPES = (("JSON files", "*.json"), ("All files", "*.*"))
CONFIG_FILE_DEFAULT_EXTENSION = ".json"
CONFIG_DISCOVERY_DEFAULT_PROFILE = "default"
CONFIG_SESSION_UNSAVED_LABEL = "(unsaved)"
CONFIG_NEW_BLANK_TITLE = "New Blank Config"
CONFIG_NEW_BLANK_PROMPT = (
    "Create a blank config session in memory first?\n\n"
    "Yes: start in memory and save later.\n"
    "No: choose a file path now.\n"
    "Cancel: do nothing."
)
CONFIG_NEW_BLANK_CANCELLED = "New Blank Config cancelled."
CONFIG_NEW_BLANK_CREATED_IN_MEMORY = "Started new blank config in memory."
CONFIG_NEW_BLANK_CREATED_FMT = "Started new blank config: {path}"
HOST_PROFILE_SYNC_NOT_SUPPRESSED = False
HOST_PROFILE_SYNC_SUPPRESSED_FOR_BLANK_SESSION = True
CONFIG_DIRTY_TITLE = "Unsaved Config Changes"
CONFIG_DIRTY_PROMPT = (
    "This config session has unsaved local edits, including discovered-device work.\n\n"
    "Yes: save changes.\n"
    "No: discard changes.\n"
    "Cancel: stay here."
)
CONFIG_DIRTY_SAVE_FAILED = "Config change requires a successful save before continuing."
CONFIG_CREATE_DEFAULT_PROFILE_FMT = "Auto-created default profile '{profile}' for local config authoring."
CONFIG_PUSH_SAVE_FIRST_CANCELLED = "Push Config cancelled: save path selection was cancelled."
CONFIG_PUSH_SAVE_FIRST_FAILED = "Push Config cancelled: local config was not saved."
CONFIG_LABEL_CONFLICT_TITLE = "Discovered Device Label Conflict"
CONFIG_LABEL_CONFLICT_PROMPT_FMT = (
    "A device label conflict was found for '{label}'.\n\n"
    "Yes: use the existing device definition.\n"
    "No: rename the new discovered device.\n"
    "Cancel: stop without creating anything."
)
CONFIG_LABEL_RENAME_TITLE = "Rename Discovered Device"
CONFIG_LABEL_RENAME_PROMPT_FMT = "New device label for discovered device '{label}':"
CONFIG_LABEL_RENAME_CANCELLED = "Create device definition cancelled during rename."
CONFIG_LABEL_RENAME_DUPLICATE = "Create device definition blocked: device label already exists."
CONFIG_LABEL_RENAME_EMPTY = "Create device definition blocked: device label cannot be empty."
PROFILES_APPLY_STAGE_KEYS = (
    ("transfer check", "transferCheck"),
    ("content validation", "contentValidation"),
    ("apply", "apply"),
    ("post-apply check", "postApplyCheck"),
)
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
MANUAL_DUTY_BLOCKED_TEXT = SHARED_MANUAL_DUTY_BLOCKED_NOT_CONNECTED_TEXT
MANUAL_DUTY_BLOCKED_STALE_TEXT = SHARED_MANUAL_DUTY_BLOCKED_STALE_TEXT
MANUAL_DUTY_BLOCKED_ESTOP_TEXT = SHARED_MANUAL_DUTY_BLOCKED_ESTOP_TEXT
MANUAL_DUTY_BLOCKED_DISABLED_TEXT = SHARED_MANUAL_DUTY_BLOCKED_DISABLED_TEXT
MANUAL_DUTY_BLOCKED_WAITING_TEXT = SHARED_MANUAL_DUTY_BLOCKED_WAITING_TEXT
MANUAL_DUTY_BLOCKED_TRANSITION_TEXT = SHARED_MANUAL_DUTY_BLOCKED_TRANSITION_TEXT
MANUAL_DUTY_BLOCKED_RUNTIME_TEXT = "Manual motor control blocked: runtime inactive."
MANUAL_DUTY_BLOCKED_CONTROLLED_SCOPE_TEXT = SHARED_MANUAL_DUTY_BLOCKED_CONTROLLED_SCOPE_TEXT
ACTIVE_GROUP_LOCKED_TEXT = SHARED_ACTIVE_GROUP_EDIT_BLOCKED_LOCKED_TEXT
ACTIVE_GROUP_WAITING_TEXT = (
    "Runtime state not loaded yet. Wait for refresh before editing active-group."
)
MANUAL_DUTY_BUSY_TEXT = "Manual motor control blocked: command in flight."
MANUAL_DUTY_SCALE_ELEMENT_SLIDER = "slider"
MANUAL_DUTY_NO_LABEL = ""
MANUAL_DUTY_NO_TARGETS: List[str] = []
MANUAL_DUTY_VALUE_FMT = "{value:.2f}"
MANUAL_DUTY_BLOCK_REASON_NONE = ""
MANUAL_DUTY_AUTO_CLOSE_CONFIRM_SEC = 0.25
MANUAL_DUTY_DIAG_MISMATCH_THRESHOLD = 0.05
MANUAL_DUTY_DIAG_ACTIVE_REQUEST_THRESHOLD = 0.10
MANUAL_DUTY_DIAG_ZERO_APPLIED_THRESHOLD = 0.02
MANUAL_DUTY_DIAG_FLOAT_PRECISION = 3
MANUAL_DUTY_DIAG_LABEL_NONE = "n/a"
MANUAL_DUTY_DIAG_FMT = (
    "Manual duty diag: {label} requested={requested} cmd={cmd} applied={applied} "
    "vel={vel} current={current} lifecycle={lifecycle}"
)
MANUAL_DUTY_DEBOUNCED_BLOCK_REASONS = {
    MANUAL_DUTY_BLOCKED_STALE_TEXT,
    MANUAL_DUTY_BLOCKED_ESTOP_TEXT,
    MANUAL_DUTY_BLOCKED_DISABLED_TEXT,
}
TEST_NAME_EMPTY = ""
VERSION_APP_NAME = APP_BRINGUP_UI_NAME
VERSION_TITLE = VERSION_HEADER
ABOUT_TITLE = "About Bringup Control"
ABOUT_NAME = "Bringup Control UI"
ABOUT_DESCRIPTION = "PC-side REST bringup control panel for RobotV2."
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
UI_PREFS_KEY_THEME = "theme"

# Constants (visibility UI).
VIS_TAB_LABEL = "CAN Visibility"
VIS_COL_DEVICE = "Device"
VIS_COL_IDENTITY = "Identity"
VIS_COL_LAST_SEEN = "Last Seen"
VIS_COL_PACKETS = "Packets"
VIS_COL_EXISTENCE_PACKETS = "Exist Pkts"
VIS_COL_RATE = "Rate"
VIS_COL_PROBE_BUCKET = "Full Probe"
VIS_COL_PROBE_SCORE = "Full Probe Score"
VIS_COL_VISIBLE = "Visible"
VIS_VALUE_YES = "Y"
VIS_VALUE_NO = "N"
VIS_VALUE_UNKNOWN = "?"
VIS_MODE_LABEL = "CAN Visibility Mode"
VIS_SUMMARY_FMT = "Sources: {sources} | Devices: {devices} | All: {all} | Some: {some} | None: {none}"
VIS_PANEL_SCOPE = VIS_SCOPE_BOTH
VIS_EMPTY_MESSAGE = "CAN visibility provider not available."
VIS_LAST_SEEN_UNKNOWN = "--"
VIS_REFRESH_SEC = 0.5
VIS_SOURCE_COUNT_UNKNOWN = "--"
VIS_UNEXPECTED_KEY = "unexpected"
VIS_ROW_META_LABEL = "label"
VIS_ROW_META_UNEXPECTED = "unexpected"
VIS_ROW_META_RAW_IDS = "rawIds"
VIS_ROW_META_IDENTITY = "identity"
VIS_SELECTION_STATUS_UNRECOGNIZED = "unrecognized-passive"
VIS_SELECTION_REASON_UNRECOGNIZED = (
    "Passive-only unrecognized device; no topology/runtime mapping yet."
)
VIS_SELECTION_SELECTED_PASSIVE_ONLY = "passive-only"
VIS_IDENTITY_SEPARATOR = ":"
VIS_RENAME_DIALOG_TITLE = "Rename Discovered Device"
VIS_RENAME_DEFINED_DIALOG_TITLE = "Rename Defined Device"
VIS_RENAME_EMPTY_TEXT = "Device label cannot be empty."
VIS_RENAME_DUPLICATE_TEXT = "Device label already exists."
VIS_RENAME_FAILED_TEXT = "Rename failed."
VIS_RENAME_PROMPT_FMT = "Rename discovered device {label}:"
VIS_RENAME_SUCCESS_FMT = "Renamed discovered device: {old_label} -> {new_label}"
VIS_RENAME_DEFINED_PROMPT_FMT = "Rename defined device {label}:"
VIS_RENAME_DEFINED_SUCCESS_FMT = (
    "Renamed in-memory defined device: {old_label} -> {new_label}. Use Save Config to persist it."
)
VIS_CREATE_DEVICE_MENU_LABEL = "Create Device Definition..."
VIS_CREATE_DEVICE_DIALOG_TITLE = "Create Device Definition"
VIS_CREATE_DEVICE_NO_PROFILE_TEXT = "Create device definition blocked: select a profile first."
VIS_CREATE_DEVICE_IDENTITY_MISSING_TEXT = (
    "Create device definition blocked: passive identity is unavailable for the selected row."
)
VIS_CREATE_DEVICE_DUPLICATE_TEXT = "Create device definition blocked: device label already exists."
VIS_CREATE_DEVICE_CONFIRM_FMT = (
    "Create one in-memory device definition for profile '{profile}'?\n\n"
    "Nothing will be written to disk until you use Save Config.\n\n"
    "Fields marked with * are guessed.\n\n"
    "label: {label}\n"
    "deviceInterface: {interface}\n"
    "manufacturer: {manufacturer}\n"
    "deviceType: {device_type}\n"
    "id: {device_id}\n"
    "model: {model}\n"
    "type: {logical_type}"
)
VIS_CREATE_DEVICE_OUTPUT_FMT = (
    "Created in-memory device definition for profile '{profile}': {label}. "
    "Use Save Config to persist it."
)
VIS_SAVE_CONFIG_NO_PENDING_TEXT = "Save Config skipped: no pending in-memory profile edits."
VIS_SAVE_CONFIG_SAVED_FMT = "Saved pending profile edits to {path}."
VIS_SAVE_CONFIG_FAILED_FMT = "Save Config failed: {error}"
CONFIG_OPEN_CANCELLED = "Open Config cancelled."
CONFIG_OPEN_FAILED_FMT = "Open Config failed: {error}"
CONFIG_OPENED_FMT = "Opened config: {path}"
CONFIG_SAVE_AS_CANCELLED = "Save Config As cancelled."
CONFIG_SAVE_AS_SAVED_FMT = "Saved current config to {path}."
CONFIG_SAVE_AS_FAILED_FMT = "Save Config As failed: {error}"
CONFIG_RENAME_PROFILE_TITLE = "Rename Profile"
CONFIG_RENAME_PROFILE_PROMPT = "New profile name:"
CONFIG_RENAME_PROFILE_NO_SELECTION = "Rename Profile blocked: no profile selected."
CONFIG_RENAME_PROFILE_NO_PROFILES = "Rename Profile blocked: no profiles are available."
CONFIG_RENAME_PROFILE_EMPTY = "Rename Profile blocked: profile name cannot be empty."
CONFIG_RENAME_PROFILE_DUPLICATE = "Rename Profile blocked: that profile name already exists."
CONFIG_RENAME_PROFILE_SAVED_FMT = "Renamed profile in local config session: {old_name} -> {new_name}. Use Save Config to persist it."
PROFILE_CONTEXT_MISSING_LOCAL_TITLE = "Robot Profile Missing In Local Config"
PROFILE_CONTEXT_MISSING_LOCAL_FMT = (
    "Robot selected profile '{robot}' is not available in the currently open local config session.\n\n"
    "Local UI profile: '{host}'.\n\n"
    "Open the matching config or switch the robot/UI to a shared profile name."
)
VIS_TAG_GUESSED_PREFIX = "guessed:"
VIS_TAG_GUESSED_LABEL = "guessed:label"
VIS_TAG_GUESSED_MODEL = "guessed:model"
VIS_TAG_GUESSED_TYPE = "guessed:type"
VIS_DIALOG_FIELD_GUESS_SUFFIX = "*"
VIS_LABEL_SUFFIX_SEPARATOR = "_"
VIS_LABEL_SUFFIX_START = 2
VIS_DEVICE_TYPE_CAN_MOTOR = 2
VIS_DEVICE_TYPE_CAN_GYRO = 4
VIS_DEVICE_TYPE_CAN_ENCODER = 7
VIS_DEVICE_TYPE_CAN_POWER = 8
VIS_MODEL_EMPTY = ""
VIS_LOGICAL_TYPE_EMPTY = ""
VIS_PASSIVE_TYPE_TOKEN_SPARK = "spark"
VIS_PASSIVE_TYPE_TOKEN_TALON = "talon"
VIS_PASSIVE_TYPE_TOKEN_FALCON = "falcon"
VIS_PASSIVE_TYPE_TOKEN_KRAKEN = "kraken"
VIS_PASSIVE_TYPE_TOKEN_MOTOR = "motor"
VIS_PASSIVE_TYPE_TOKEN_CANCODER = "cancoder"
VIS_PASSIVE_TYPE_TOKEN_ENCODER = "encoder"
VIS_DEFINED_SECTION_LABEL = "Defined Nodes"
VIS_UNRECOGNIZED_SECTION_LABEL = "Unrecognized Nodes"
VIS_CTRE_RAW_SECTION_LABEL = "CTRE Raw Decode"
VIS_PASSIVE_DEEP_DIVE_SECTION_LABEL = "Shared Passive CAN Deep Dive"
VIS_CLEAR_PANELS_BUTTON = "Clear Panels"
VIS_RESTART_SNIFFER_BUTTON = "Restart CAN Sniffer"
VIS_FRAME_FAMILY_HELP_BUTTON = "Frame Family Help"
VIS_RESTART_SNIFFER_REQUESTED = "Restarting passive CAN sniffer..."
VIS_RESTART_SNIFFER_DONE = "Passive CAN sniffer restart requested."
VIS_RESTART_SNIFFER_UNAVAILABLE = "Passive CAN sniffer restart is unavailable."
VIS_RESTART_SNIFFER_FAILED_FMT = "Passive CAN sniffer restart failed: {error}"
VIS_PACKETS_UNKNOWN = "--"
VIS_RATE_UNKNOWN = "--"
VIS_RATE_FMT = "{value:.1f}/s"
TOPOLOGY_REPAIR_VERSION = 1
TOPOLOGY_REPAIR_SOURCE_LOCAL = "local"
TOPOLOGY_REPAIR_NODE_DEVICE = "device"
TOPOLOGY_REPAIR_NODE_CLASS_DEVICE = "device"
TOPOLOGY_REPAIR_BUS_INDEX = 0
TOPOLOGY_REPAIR_ROW_MOD = 2
TOPOLOGY_REPAIR_ROW_EVEN = 0
TOPOLOGY_REPAIR_ROW_ODD = 1
TOPOLOGY_REPAIR_X_START = 120.0
TOPOLOGY_REPAIR_X_STEP = 120.0
TOPOLOGY_KEY_EDGES = "edges"
VIS_DETAIL_TEXT_HEIGHT = 14
VIS_TABLE_SPLIT_ORIENT = "vertical"
VIS_RAW_EMPTY_MESSAGE = "Select a CTRE row to inspect contributing raw IDs."
LIVE_TOPOLOGY_TAB_LABEL = "Live Topology"
LIVE_LENS_LABEL = "Lens:"
LIVE_LENS_OPTION_EVIDENCE = "Evidence"
LIVE_LENS_OPTION_RUNTIME = "Runtime"
LIVE_LENS_OPTION_VISIBILITY = "CAN Visibility"
LIVE_LENS_OPTION_LABELS = (
    LIVE_LENS_OPTION_EVIDENCE,
    LIVE_LENS_OPTION_RUNTIME,
    LIVE_LENS_OPTION_VISIBILITY,
)
LIVE_LENS_TOPOLOGY_KEYS = {
    LIVE_LENS_OPTION_EVIDENCE: TOPOLOGY_LENS_EVIDENCE,
    LIVE_LENS_OPTION_RUNTIME: TOPOLOGY_LENS_RUNTIME,
    LIVE_LENS_OPTION_VISIBILITY: TOPOLOGY_LENS_VISIBILITY,
}
LIVE_LENS_DEFAULT = LIVE_LENS_OPTION_EVIDENCE
CAN_FAULT_FINDER_TAB_LABEL = "CAN Fault Finder"
CAN_FAULT_FINDER_TITLE = "CAN Fault Finder"
CAN_FAULT_FINDER_RUN_BUTTON = "Run CAN Break Check"
CAN_FAULT_FINDER_STATUS_NOT_RUN = "Not run yet."
CAN_FAULT_FINDER_STATUS_RUNNING = "Running CAN Break Check..."
CAN_FAULT_FINDER_STATUS_FMT = "Last run: {age} ago at {clock} | run #{run_count} | candidates={count}"
CAN_FAULT_FINDER_TEXT_RUN_STAMP_FMT = "Diagnosis frozen from run #{run_count} at {clock}\n\n{body}"
CAN_FAULT_FINDER_TEXT_NOT_RUN = (
    "Run CAN Break Check to freeze the current evidence window and rank CAN fault candidates."
)
CAN_FAULT_FINDER_TEXT_ERROR_FMT = "CAN Fault Finder failed: {error}"
EVIDENCE_DIRTY_PRIORITY_CONSOLE = 10
EVIDENCE_DIRTY_PRIORITY_PRESENCE = 20
EVIDENCE_DIRTY_PRIORITY_SCOPE = 30
EVIDENCE_DIRTY_PRIORITY_BASELINE = 40
EVIDENCE_DIRTY_REASON_CONSOLE = "console_changed"
EVIDENCE_DIRTY_REASON_PASSIVE = "passive_changed"
EVIDENCE_DIRTY_REASON_RUNTIME = "runtime_changed"
EVIDENCE_DIRTY_REASON_SCOPE = "scope_changed"
EVIDENCE_DIRTY_REASON_PROFILE = "profile_changed"
EVIDENCE_DIRTY_REASON_MANUAL = "manual_changed"
EVIDENCE_EVENT_TYPE_PRESENCE_GAINED = "presence_gained"
EVIDENCE_EVENT_TYPE_PRESENCE_LOST = "presence_lost"
EVIDENCE_EVENT_TYPE_OPERABILITY_DEGRADED = "operability_degraded"
EVIDENCE_EVENT_TYPE_OPERABILITY_RECOVERED = "operability_recovered"
EVIDENCE_EVENT_TYPE_FRESHNESS_STALE = "freshness_became_stale"
EVIDENCE_EVENT_TYPE_SCOPE_CHANGED = "scope_changed"
EVIDENCE_EVENT_SOURCE_EVALUATOR = "evaluator"
EVIDENCE_EVENT_LOG_LIMIT = 8
EVIDENCE_DIRTY_EMPTY_REASONS: List[str] = []
EVIDENCE_PRESENCE_STATE_PRESENT = "present"
EVIDENCE_PRESENCE_STATE_MISSING = "missing"
EVIDENCE_PRESENCE_STATE_UNKNOWN = "unknown"
EVIDENCE_PRESENCE_STATE_CONFLICT = "conflict"
EVIDENCE_FRESHNESS_FRESH = "fresh"
EVIDENCE_FRESHNESS_AGING = "aging"
EVIDENCE_FRESHNESS_STALE = "stale"
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
COLOR_KEY_GEOMETRY = "460x520"
COLOR_KEY_MIN_WIDTH = 420
COLOR_KEY_MIN_HEIGHT = 460
COLOR_SWATCH_WIDTH = 3
COLOR_SWATCH_RELIEF = "solid"
COLOR_SWATCH_BORDER = 1
COLOR_KEY_SECTION_RUNTIME = "Runtime Lens"
COLOR_KEY_SECTION_VISIBILITY = "CAN Visibility Lens"
COLOR_KEY_SECTION_EVIDENCE = "Evidence Lens"
COLOR_KEY_SECTION_BASE = "Base Topology Fallback"
COLOR_KEY_SECTION_OVERLAYS = "Overlays"
COLOR_KEY_SECTION_ANALYZER = "Analyzer Availability"
COLOR_KEY_PRESENCE_HIGH = "#2f7a2f"
COLOR_KEY_PRESENCE_LOW = "#f59e0b"
COLOR_KEY_PRESENCE_NONE = "#dc2626"
COLOR_KEY_VIS_ALL = "#16a34a"
COLOR_KEY_VIS_SOME = "#f59e0b"
COLOR_KEY_VIS_NONE = "#dc2626"
COLOR_KEY_VIS_UNKNOWN = "#9ca3af"
COLOR_KEY_EVIDENCE_OK = "#2f7a2f"
COLOR_KEY_EVIDENCE_DEGRADED = "#d97706"
COLOR_KEY_EVIDENCE_FAILED = "#dc2626"
COLOR_KEY_EVIDENCE_UNKNOWN = "#9ca3af"
COLOR_KEY_EVIDENCE_IDENTITY = "#c2410c"
COLOR_KEY_BASE_REV = "#ffd5a6"
COLOR_KEY_BASE_NI = "#e7e7e7"
COLOR_KEY_BASE_ANALYZER = "#cbd5f5"
COLOR_KEY_OVERLAY_SELECTED = "#ffffff"
COLOR_KEY_OVERLAY_GROUP = "#dbeafe"
COLOR_KEY_ANALYZER_OK = "#16a34a"
COLOR_KEY_ANALYZER_UNKNOWN = "#9ca3af"
COLOR_KEY_TEXT_RUNTIME_HIGH = "Green: runtime presence is high confidence or recently seen."
COLOR_KEY_TEXT_RUNTIME_LOW = "Amber: runtime presence is low confidence or stale (> 2s since last seen / last update)."
COLOR_KEY_TEXT_RUNTIME_NONE = "Red: runtime presence explicitly missing / none."
COLOR_KEY_TEXT_VIS_ALL = "Green: fresh device-emitted CAN evidence is proving presence."
COLOR_KEY_TEXT_VIS_SOME = "Amber: passive CAN evidence exists but presence is weak or low-confidence."
COLOR_KEY_TEXT_VIS_NONE = "Red: no device-emitted CAN evidence currently proves presence (traffic-only or none)."
COLOR_KEY_TEXT_VIS_UNKNOWN = "Gray: no passive CAN verdict is available yet."
COLOR_KEY_TEXT_EVIDENCE_OK = "Green: interpreted evidence says OK."
COLOR_KEY_TEXT_EVIDENCE_DEGRADED = "Amber: interpreted evidence says degraded."
COLOR_KEY_TEXT_EVIDENCE_FAILED = "Red: interpreted evidence says failed or missing."
COLOR_KEY_TEXT_EVIDENCE_UNKNOWN = "Gray: interpreted evidence is unknown."
COLOR_KEY_TEXT_EVIDENCE_IDENTITY = "Orange-red: identity mismatch / identity-specific issue."
COLOR_KEY_TEXT_BASE_REV = "Light orange: base REV vendor/category fill when no active lens color overrides it."
COLOR_KEY_TEXT_BASE_NI = "Light gray: base NI/roboRIO or other fallback topology fill when no active lens color overrides it."
COLOR_KEY_TEXT_BASE_ANALYZER = "Light blue: base analyzer/category fill when no active lens color overrides it."
COLOR_KEY_TEXT_OVERLAY_SELECTED = "White dashed selection box: current selected device."
COLOR_KEY_TEXT_OVERLAY_GROUP = "Blue group boxes/labels: topology group overlays, not lens node colors."
COLOR_KEY_TEXT_ANALYZER_OK = "Green: analyzer node in CAN Visibility lens when the source is available."
COLOR_KEY_TEXT_ANALYZER_UNKNOWN = "Gray: analyzer node in CAN Visibility lens when the source is unavailable."
COLOR_KEY_TEXT_HEADER = (
    "This window is a reference for all Live Topology color modes. "
    "The Lens dropdown selects which lens colors are active for CAN nodes."
)
COLOR_KEY_TEXT_TIME_NOTE = (
    "Truth note: when the active lens does not provide a live color for a node, the diagram falls back to base topology "
    "vendor/category colors. Overlays such as selection boxes and group outlines are separate from node fill colors. "
    "Runtime lens stale timing is about 2.0 s without a fresh last-seen update; the CAN Visibility table Last Seen column "
    "shows the same recency in age form."
)
COLOR_KEY_SECTION_PAD = (10, 8)
COLOR_KEY_ROW_PADY = 2
COLOR_KEY_ROW_PADX = 8
CAN_FRAME_FAMILY_HELP_ATTR = "_can_frame_family_help_window"
CAN_FRAME_FAMILY_HELP_TITLE = "CAN Frame Family Help"
CAN_FRAME_FAMILY_HELP_MENU_LABEL = "CAN Frame Family Help"
CAN_FRAME_FAMILY_HELP_GEOMETRY = "780x620"
CAN_FRAME_FAMILY_HELP_MIN_WIDTH = 620
CAN_FRAME_FAMILY_HELP_MIN_HEIGHT = 440
CAN_FRAME_FAMILY_HELP_PADDING = 10
CAN_FRAME_FAMILY_HELP_WRAP = "word"
CAN_FRAME_FAMILY_HELP_STATE_NORMAL = "normal"
CAN_FRAME_FAMILY_HELP_STATE_DISABLED = "disabled"
CAN_FRAME_FAMILY_HELP_INSERT_END = "end"
TK_PROTOCOL_WINDOW_DELETE = "WM_DELETE_WINDOW"
HELP_LINE_SEPARATOR = "\n"
HELP_TAB_CAN_VISIBILITY = "CAN Visibility"
CAN_FRAME_FAMILY_HELP_LINES = (
    "Purpose:",
    "  Explain the raw CAN frame-family evidence shown in CAN Visibility and Evidence details.",
    "",
    "What api=12/3 means:",
    "  - api=12/3 is shorthand for apiClass=12 and apiIndex=3.",
    "  - These numbers are decoded from the 29-bit FRC extended CAN arbitration ID.",
    "  - apiClass is bits 10..15; apiIndex is bits 6..9.",
    "  - The full passive grouping key is manufacturer + deviceType + deviceId + apiClass + apiIndex.",
    "  - It is a vendor frame family, not a DSL test API, fault code, or direct sensor value.",
    "",
    "How to read one evidence line:",
    "  api=12/3 | role=DEVICE_EMITTED_SECONDARY_STATUS | rate=115.5Hz | count=393 | countsForPresence=yes",
    "  - api=12/3 identifies the raw frame family.",
    "  - role says how the passive classifier currently interprets that family.",
    "  - rate is how often the observer is seeing that family.",
    "  - count is the number of packets seen in the active observation window.",
    "  - countsForPresence=yes means this family contributes to passive device-presence confidence.",
    "",
    "Role meanings:",
    "  - DEVICE_EMITTED_PRIMARY_STATUS: strong recurring device status evidence, usually high rate.",
    "  - DEVICE_EMITTED_SECONDARY_STATUS: companion recurring device status evidence.",
    "  - DEVICE_EMITTED_HEARTBEAT_HOUSEKEEPING: recurring heartbeat/housekeeping evidence.",
    "  - CONTROLLER_EMITTED_COMMAND or CONTROLLER_EMITTED_POLL: controller traffic; not proof the device is alive.",
    "  - SHARED_BUS_CONTROL: bus-level traffic; not proof of one specific device.",
    "  - UNKNOWN: retained for inspection only; do not use as a confident operator conclusion.",
    "",
    "Presence meaning:",
    "  - Present/high rate means the passive CAN observer sees recurring device-emitted traffic.",
    "  - This is good evidence that the device is powered and talking on CAN.",
    "  - It does not prove the mechanism is connected, calibrated, healthy, or mapped to the correct robot function.",
    "",
    "Absence or stale meaning:",
    "  - The observer is not seeing a recent expected device-emitted family.",
    "  - Possible causes: device power loss, CAN wiring break, wrong CAN ID/profile, observer/CANable issue,",
    "    very slow configured status period, or a vendor frame family the classifier does not know yet.",
    "",
    "Low rate meaning:",
    "  - The observer sees the family, but not at the expected recurring rate.",
    "  - Possible causes: high bus load, dropped observer frames, slow configured status period, intermittent wiring,",
    "    boot/recovery transitions, or a classifier expectation that needs adjustment for that device.",
    "",
    "Operator rule:",
    "  Use the plain evidence summary first: present/missing, rate, age, and whether it counts for presence.",
    "  Use apiClass/apiIndex only as advanced raw evidence when comparing captures or debugging the passive decoder.",
)
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
VIS_HEADER_BUTTON_PAD = (0, 8)
VIS_COL_DEVICE_WIDTH = 240
VIS_COL_IDENTITY_WIDTH = 110
VIS_COL_LAST_SEEN_WIDTH = 90
VIS_COL_PACKETS_WIDTH = 80
VIS_COL_EXISTENCE_PACKETS_WIDTH = 84
VIS_COL_RATE_WIDTH = 80
VIS_COL_PROBE_BUCKET_WIDTH = 90
VIS_COL_PROBE_SCORE_WIDTH = 92
VIS_COL_SOURCE_WIDTH = 72
EVIDENCE_TAB_LABEL = "Evidence"
EVIDENCE_SUMMARY_DEFAULT = "Select a device to inspect interpreted evidence."
EVIDENCE_TITLE_TEXT = "Device Evidence"
EVIDENCE_ENGINE_BANNER_DEFAULT = "Evidence Engine: LEGACY"
EVIDENCE_BUS_HEALTH_TEXT = "CAN Bus Health (System Console)"
EVIDENCE_BUS_HEALTH_EMPTY_TEXT = (
    "Overall Health=OK | Active Events=0\n"
    "No active system-level CAN-bus warning events are currently surfaced."
)
EVIDENCE_BUS_HEALTH_OK_IMPACT = (
    "No active system-level CAN-bus warning conditions are currently surfaced."
)
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
EVIDENCE_TOPOLOGY_WEIGHT = 1
EVIDENCE_INSPECTOR_WEIGHT = 3
EVIDENCE_TOPOLOGY_FRAME_WIDTH = 560
EVIDENCE_TOPOLOGY_FRAME_HEIGHT = 340
EVIDENCE_SUMMARY_TABLE_HEIGHT = 4
EVIDENCE_TEXT_HEIGHT_DEFAULT = 4
EVIDENCE_TEXT_HEIGHT_PROBE = 8
EVIDENCE_TEXT_HEIGHT_MANUAL = 8
EVIDENCE_TEXT_HEIGHT_ENRICHMENT = 6
EVIDENCE_TEXT_HEIGHT_NOTES = 5
EVIDENCE_PROBE_DETAIL_LIMIT = 4
EVIDENCE_INSPECTOR_PANED_WEIGHT_DEFAULT = 2
EVIDENCE_INSPECTOR_PANED_WEIGHT_PROBE = 2
EVIDENCE_INSPECTOR_PANED_WEIGHT_MANUAL = 2
EVIDENCE_INSPECTOR_PANED_WEIGHT_NOTES = 2
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
EVIDENCE_PRESENCE_TEXT = "Robot Runtime Scope Check (Local Snapshot Lens)"
EVIDENCE_PASSIVE_TEXT = "Passive CAN Evidence (CANable Observer)"
EVIDENCE_CONSOLE_TEXT = "Console Evidence (Robot/Host)"
EVIDENCE_PROBE_TEXT = "Full Probe (Manual One-Shot)"
EVIDENCE_MANUAL_TEXT = "Manual Test (Operator / Motion)"
EVIDENCE_ENRICHMENT_TEXT = "Enrichment Evidence (Host Corroboration)"
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
CMD_RUNTIME_ACTIVATE = "runtimeActivate"
CMD_RUNTIME_DEACTIVATE = "runtimeDeactivate"
CMD_LIFECYCLE_ACTIVATE = "lifecycleActivate"
CMD_LIFECYCLE_DEACTIVATE_ACTIVE = "lifecycleDeactivateActive"
KEY_COMMAND_MODE = "mode"
KEY_COMMAND_MEMBERSHIP_MODE = "membershipMode"
LIFECYCLE_DEFAULT_MODE = "READ_ONLY"
ACTIVATION_MEMBERSHIP_MODE_STRICT = "STRICT"
ACTIVATION_MEMBERSHIP_MODE_PARTIAL = "PARTIAL"
ACTIVATION_MEMBERSHIP_MODE_FORCE = "FORCE"
ACTIVATION_MEMBERSHIP_MODE_VALUES = (
    ACTIVATION_MEMBERSHIP_MODE_PARTIAL,
    ACTIVATION_MEMBERSHIP_MODE_STRICT,
    ACTIVATION_MEMBERSHIP_MODE_FORCE,
)
ACTIVATION_MEMBERSHIP_MODE_DEFAULT = ACTIVATION_MEMBERSHIP_MODE_FORCE
ACTIVATION_MEMBERSHIP_LABEL = "Activation Mode"
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
TEST_FAILURE_PREFIX = "Test failure detail:"
TEST_SUCCESS_PREFIX = "Test success detail:"
TEST_FAILURE_REQUIRE_PREFIX = "require not satisfied:"
TEST_FAILURE_SIGNAL_SET_PREFIX = "signal fallback active:"
TEST_FAILURE_LAST_SAMPLES_PREFIX = "last samples:"
TEST_FAILURE_SAMPLE_LIMIT = 3
TEST_LIBRARY_STATUS_INACTIVE_PREFIX = "selected test inactive - "
TEST_LIBRARY_STATUS_READY = SHARED_TEST_SCOPE_STATUS_READY_DETAIL
TEST_LIBRARY_STATUS_NO_SELECTED_TEST = TEST_LIBRARY_STATUS_INACTIVE_PREFIX + OUTPUT_NO_SELECTED_TEST
TEST_LIBRARY_STATUS_LOADED_NOT_ACTIVATED = SHARED_SELECTED_TEST_STATUS_LOADED_NOT_ACTIVATED
TEST_LIBRARY_STATUS_MANUAL_RESTORED = SHARED_SELECTED_TEST_STATUS_MANUAL_RESTORED
TEST_LIBRARY_STATUS_SCOPE_SWAP_REQUIRED = SHARED_SELECTED_TEST_STATUS_SCOPE_SWAP_REQUIRED
TEST_LIBRARY_STATUS_BLOCKED_ESTOP = SHARED_SELECTED_TEST_STATUS_BLOCKED_ESTOP
TEST_LIBRARY_STATUS_BLOCKED_DISABLED = SHARED_SELECTED_TEST_STATUS_BLOCKED_DISABLED
TEST_LIBRARY_STATUS_BLOCKED_NOT_TELEOP = SHARED_SELECTED_TEST_STATUS_BLOCKED_NOT_TELEOP
TEST_SCOPE_DETAIL_NO_SELECTION = SHARED_TEST_SCOPE_STATUS_NO_SELECTION_DETAIL
TEST_SCOPE_DETAIL_LOADED_NOT_ACTIVATED = SHARED_TEST_SCOPE_STATUS_LOADED_NOT_ACTIVATED_DETAIL
TEST_SCOPE_DETAIL_MANUAL_RESTORED = SHARED_TEST_SCOPE_STATUS_MANUAL_RESTORED_DETAIL
RUNNABLE_SCOPE_DETAIL_MANUAL_NOT_ACTIVATED = SHARED_RUNNABLE_SCOPE_DETAIL_MANUAL_NOT_ACTIVATED
RUNNABLE_SCOPE_DETAIL_SELECTED_TEST_NOT_ACTIVATED = SHARED_RUNNABLE_SCOPE_DETAIL_SELECTED_TEST_NOT_ACTIVATED
RUNNABLE_SCOPE_DETAIL_MANUAL_NOT_TELEOP = SHARED_RUNNABLE_SCOPE_DETAIL_MANUAL_NOT_TELEOP
RUNNABLE_SCOPE_DETAIL_SELECTED_TEST_NOT_TELEOP = SHARED_RUNNABLE_SCOPE_DETAIL_SELECTED_TEST_NOT_TELEOP
RUNNABLE_SCOPE_DETAIL_MANUAL_EMPTY = SHARED_RUNNABLE_SCOPE_DETAIL_MANUAL_EMPTY
RUNNABLE_SCOPE_DETAIL_SELECT_PROFILE = SHARED_RUNNABLE_SCOPE_DETAIL_SELECT_PROFILE
TEST_SCOPE_DETAIL_MISSING_DEVICE_PREFIX = SHARED_TEST_SCOPE_STATUS_MISSING_DEVICE_PREFIX
TEST_SCOPE_DETAIL_REQUIRED_UNAVAILABLE = SHARED_TEST_SCOPE_STATUS_REQUIRED_UNAVAILABLE_DETAIL
TEST_SCOPE_DETAIL_SCOPE_SWAP_REQUIRED = SHARED_TEST_SCOPE_STATUS_SCOPE_SWAP_REQUIRED_DETAIL
TEST_SCOPE_DETAIL_NOT_LOADED_ON_ROBOT = (
    "This test exists locally, but the robot has not loaded it into the current runnable test set."
)
TEST_SCOPE_DETAIL_BLOCKED_ESTOP = SHARED_TEST_SCOPE_STATUS_BLOCKED_ESTOP_DETAIL
TEST_SCOPE_DETAIL_BLOCKED_DISABLED = SHARED_TEST_SCOPE_STATUS_BLOCKED_DISABLED_DETAIL
TEST_SCOPE_DETAIL_BLOCKED_NOT_TELEOP = SHARED_TEST_SCOPE_STATUS_BLOCKED_NOT_TELEOP_DETAIL
TEST_LIBRARY_LOCAL_SCOPE_PROFILE = "profile"
TEST_LIBRARY_LOCAL_SCOPE_CONFIG = "config"
TEST_LIBRARY_LOCAL_SCOPE_GLOBAL = "global"
TEST_SCOPE_PANEL_TITLE = "Test State"
TEST_SCOPE_PANEL_READY_HEADLINE = "READY TO RUN"
TEST_SCOPE_PANEL_INACTIVE_HEADLINE = "NOT RUNNABLE"
TEST_SCOPE_PANEL_NO_SELECTION_HEADLINE = "NO TEST SELECTED"
TEST_SCOPE_PANEL_WAITING_HEADLINE = "WAITING FOR STATE"
RUNNABLE_SCOPE_PANEL_TITLE = "Runnable State"
RUNNABLE_SCOPE_PANEL_READY_DETAIL = SHARED_RUNNABLE_SCOPE_PANEL_READY_DETAIL
RUNNABLE_SCOPE_PANEL_WAITING_DETAIL = SHARED_RUNNABLE_SCOPE_PANEL_WAITING_DETAIL
RUNNABLE_SCOPE_PANEL_DISCONNECTED_DETAIL = SHARED_RUNNABLE_SCOPE_PANEL_DISCONNECTED_DETAIL
TEST_SCOPE_PANEL_READY_BG = "#dcfce7"
TEST_SCOPE_PANEL_READY_FG = "#166534"
TEST_SCOPE_PANEL_INACTIVE_BG = "#fef3c7"
TEST_SCOPE_PANEL_INACTIVE_FG = "#92400e"
TEST_SCOPE_PANEL_NEUTRAL_BG = "#fef3c7"
TEST_SCOPE_PANEL_NEUTRAL_FG = "#92400e"
TEST_SCOPE_PANEL_ERROR_BG = "#fee2e2"
TEST_SCOPE_PANEL_ERROR_FG = "#991b1b"
TEST_SCOPE_PANEL_BORDER = "#cbd5e1"
TEST_SCOPE_PANEL_WRAP = 320
TEST_SCOPE_PANEL_PAD_X = 12
TEST_SCOPE_PANEL_PAD_Y = 8
TEST_SCOPE_PANEL_HEADLINE_FONT = ("Segoe UI", 11, "bold")
TEST_SCOPE_PANEL_DETAIL_FONT = ("Segoe UI", 10, "normal")
TEST_RESULT_PASS_FG = "#166534"
TEST_RESULT_FAIL_FG = "#991b1b"
TEST_RESULT_RUNNING_FG = "#1d4ed8"
TEST_RESULT_PASS_PREFIX = "PASS"
TEST_RESULT_NEUTRAL_FG = "#374151"
TEST_ACTIVE_GROUP_TITLE = "Selected Test Devices"
TEST_ACTIVE_GROUP_STATUS_LOCKED = SHARED_TEST_ACTIVE_GROUP_STATUS_LOCKED
TEST_ACTIVE_GROUP_STATUS_INVALID = SHARED_TEST_ACTIVE_GROUP_STATUS_INVALID
TEST_ACTIVE_GROUP_STATUS_ENABLED = SHARED_TEST_ACTIVE_GROUP_STATUS_ENABLED
TEST_ACTIVE_GROUP_PANEL_EMPTY = "No selected-test devices."
TEST_ACTIVE_GROUP_COL_LABEL = "Label"
TEST_ACTIVE_GROUP_COL_ENABLED = "Enabled"
TEST_ACTIVE_GROUP_COL_LOCKED = "Locked"
TEST_ACTIVE_GROUP_COL_INSTANTIATED = "Instantiated"
TEST_ACTIVE_GROUP_COL_SCOPE_ACTIVE = "Scope Active"
TEST_ACTIVE_GROUP_COL_NOTE = "Note"
TEST_ACTIVE_GROUP_EMPTY_VALUE = ""
TEST_LIBRARY_NOTE_TEXT = (
    "The Tests tab has three sources: external Global Library, config-shared Config Library, "
    "and selected-profile Profile Tests. Selecting a test shows the devices required by that DSL test. "
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
    "addMotor",
    "addAll",
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
    "activepresenceprobe",
    "dumpreport",
    "printcancoder",
    "printcandiag",
    "printhealth",
    "printinputs",
    "printprofiledevices",
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
    "showruntimestate",
    "showsources",
    "showstatus",
    "showversion",
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


def _normalize_loaded_command_metadata(
    actions_by_name: Dict[str, Dict[str, Any]],
    sections: List[Dict[str, Any]],
) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    """
    NAME
        _normalize_loaded_command_metadata - Apply host-owned command ownership overrides.
    """
    normalized_actions = {
        str(name): dict(row) for name, row in actions_by_name.items() if isinstance(row, dict)
    }
    can_row = normalized_actions.get(CMD_PRINT_CAN_DIAG)
    if isinstance(can_row, dict):
        can_row[INVENTORY_KEY_ACTION_KIND] = ACTION_KIND_HOST_LOCAL
        can_row[INVENTORY_KEY_SOURCE] = ACTION_SOURCE_HOST
        normalized_actions[CMD_PRINT_CAN_DIAG] = can_row
    normalized_sections: List[Dict[str, Any]] = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        commands = section.get("commands")
        if not isinstance(commands, list):
            normalized_sections.append(dict(section))
            continue
        filtered_commands: List[Dict[str, Any]] = []
        for row in commands:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name", "")).strip()
            if name == CMD_PRINT_CAN_DIAG and name in normalized_actions:
                filtered_commands.append(dict(normalized_actions[name]))
                continue
            filtered_commands.append(dict(row))
        new_section = dict(section)
        new_section["commands"] = filtered_commands
        normalized_sections.append(new_section)
    return normalized_actions, normalized_sections


def _load_generated_command_metadata() -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    """
    NAME
        _load_generated_command_metadata - Load merged robot and host UI action metadata.
    """
    actions_by_name, sections = load_host_ui_command_metadata(
        HOST_UI_ACTIONS,
        ACTION_SOURCE_ROBOT,
        ACTION_SOURCE_HOST,
        ACTION_KIND_HOST_LOCAL,
    )
    return _normalize_loaded_command_metadata(actions_by_name, sections)


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


def _startup_selected_profile(
    profile_names: List[str],
    auto_select_default: bool,
    default_profile_name: object = None,
) -> str:
    """
    NAME
        _startup_selected_profile - Resolve the startup-selected profile for the UI.
    """
    default_profile = (
        str(default_profile_name).strip()
        if isinstance(default_profile_name, str) and str(default_profile_name).strip()
        else get_default_profile()
    )
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


def _load_ui_theme_pref() -> str:
    """
    NAME
        _load_ui_theme_pref - Return the configured UI theme identifier.
    """

    payload = _load_ui_prefs_payload()
    theme_name = str(payload.get(UI_PREFS_KEY_THEME, UI_THEME_DEFAULT) or UI_THEME_DEFAULT)
    if theme_name not in set(list_ui_theme_names()):
        return UI_THEME_DEFAULT
    return theme_name


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
        if get_device_interface(device) != INTERFACE_CAN:
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


def _rename_topology_device_refs_in_payload(
    payload: Dict[str, Any],
    old_label: str,
    new_label: str,
) -> None:
    """
    NAME
        _rename_topology_device_refs_in_payload - Update saved topology deviceRef labels across all profiles.
    """
    if not old_label or not new_label:
        return
    topology_root = payload.get("topology")
    if not isinstance(topology_root, dict):
        return
    topology_profiles = topology_root.get("profiles")
    if not isinstance(topology_profiles, dict):
        return
    old_lower = old_label.lower()
    for topology_entry in topology_profiles.values():
        if not isinstance(topology_entry, dict):
            continue
        nodes = topology_entry.get("nodes")
        if not isinstance(nodes, list):
            continue
        for node in nodes:
            if not isinstance(node, dict):
                continue
            device_ref = str(node.get(KEY_DEVICE_REF, NT_VALUE_EMPTY)).strip()
            if device_ref.lower() == old_lower:
                node[KEY_DEVICE_REF] = new_label


def _repair_missing_topology_nodes_in_payload(payload: Dict[str, Any]) -> None:
    """
    NAME
        _repair_missing_topology_nodes_in_payload - Materialize missing saved topology device nodes from profile membership before save.
    """
    if not isinstance(payload, dict):
        return
    profiles = payload.get(KEY_PROFILES)
    devices = payload.get(KEY_DEVICES)
    if not isinstance(profiles, dict) or not isinstance(devices, list):
        return
    registry: Dict[str, Dict[str, Any]] = {}
    for entry in devices:
        if not isinstance(entry, dict):
            continue
        label = str(entry.get(PROFILE_KEY_LABEL, NT_VALUE_EMPTY)).strip()
        if not label:
            continue
        registry[label.lower()] = entry
    topology_root = payload.get(KEY_TOPOLOGY)
    if not isinstance(topology_root, dict):
        topology_root = {
            KEY_TOPOLOGY_VERSION: TOPOLOGY_REPAIR_VERSION,
            KEY_TOPOLOGY_SOURCE: TOPOLOGY_REPAIR_SOURCE_LOCAL,
            KEY_TOPOLOGY_PROFILES: {},
        }
        payload[KEY_TOPOLOGY] = topology_root
    topology_profiles = topology_root.get(KEY_TOPOLOGY_PROFILES)
    if not isinstance(topology_profiles, dict):
        topology_profiles = {}
        topology_root[KEY_TOPOLOGY_PROFILES] = topology_profiles
    for profile_name, profile_payload in profiles.items():
        if not isinstance(profile_payload, dict):
            continue
        profile_devices = profile_payload.get(KEY_PROFILE_DEVICES)
        if not isinstance(profile_devices, list):
            continue
        topology_entry = topology_profiles.get(profile_name)
        if not isinstance(topology_entry, dict):
            topology_entry = {
                KEY_TOPOLOGY_NODES: [],
                TOPOLOGY_KEY_EDGES: [],
                KEY_TOPOLOGY_VIEW: {},
            }
            topology_profiles[profile_name] = topology_entry
        nodes = topology_entry.get(KEY_TOPOLOGY_NODES)
        if not isinstance(nodes, list):
            nodes = []
            topology_entry[KEY_TOPOLOGY_NODES] = nodes
        kept_nodes: List[Dict[str, Any]] = []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_type = str(node.get(KEY_OBJECT_TYPE, node.get(KEY_NODE_TYPE, NT_VALUE_EMPTY))).strip().lower()
            if node_type != TOPOLOGY_REPAIR_NODE_DEVICE:
                kept_nodes.append(node)
                continue
            device_ref = str(node.get(KEY_DEVICE_REF, NT_VALUE_EMPTY)).strip()
            if not device_ref:
                continue
            if device_ref.lower() not in registry:
                continue
            kept_nodes.append(node)
        if len(kept_nodes) != len(nodes):
            nodes = kept_nodes
            topology_entry[KEY_TOPOLOGY_NODES] = nodes
        existing_refs = {
            str(node.get(KEY_DEVICE_REF, NT_VALUE_EMPTY)).strip().lower()
            for node in nodes
            if isinstance(node, dict)
            and str(node.get(KEY_OBJECT_TYPE, node.get(KEY_NODE_TYPE, NT_VALUE_EMPTY))).strip().lower()
            == TOPOLOGY_REPAIR_NODE_DEVICE
            and str(node.get(KEY_DEVICE_REF, NT_VALUE_EMPTY)).strip()
        }
        next_key = max(
            [
                int(node.get(KEY_NODE_KEY))
                for node in nodes
                if isinstance(node, dict) and isinstance(node.get(KEY_NODE_KEY), int)
            ],
            default=0,
        ) + 1
        max_x = max(
            [
                float(layout.get(LAYOUT_KEY_X))
                for node in nodes
                if isinstance(node, dict)
                and isinstance(node.get(KEY_LAYOUT), dict)
                and isinstance(node.get(KEY_LAYOUT).get(LAYOUT_KEY_X), (int, float))
                for layout in [node.get(KEY_LAYOUT)]
            ],
            default=TOPOLOGY_REPAIR_X_START - TOPOLOGY_REPAIR_X_STEP,
        )
        next_x = max_x + TOPOLOGY_REPAIR_X_STEP
        for label_entry in profile_devices:
            label = str(label_entry or NT_VALUE_EMPTY).strip()
            if not label or label.lower() in existing_refs:
                continue
            if label.lower() not in registry:
                continue
            nodes.append(
                {
                    KEY_NODE_KEY: next_key,
                    KEY_OBJECT_TYPE: TOPOLOGY_REPAIR_NODE_DEVICE,
                    KEY_NODE_TYPE: TOPOLOGY_REPAIR_NODE_DEVICE,
                    KEY_NODE_CLASS: TOPOLOGY_REPAIR_NODE_CLASS_DEVICE,
                    KEY_DEVICE_REF: label,
                    KEY_LAYOUT: {
                        KEY_BUS: TOPOLOGY_REPAIR_BUS_INDEX,
                        LAYOUT_KEY_ROW: (
                            TOPOLOGY_REPAIR_ROW_EVEN
                            if next_key % TOPOLOGY_REPAIR_ROW_MOD == TOPOLOGY_REPAIR_ROW_EVEN
                            else TOPOLOGY_REPAIR_ROW_ODD
                        ),
                        LAYOUT_KEY_X: next_x,
                    },
                }
            )
            existing_refs.add(label.lower())
            next_key += 1
            next_x += TOPOLOGY_REPAIR_X_STEP


def _payload_requires_topology_repair(payload: Dict[str, Any]) -> bool:
    """
    NAME
        _payload_requires_topology_repair - Return whether topology repair would materially change one payload.
    """
    candidate = deepcopy(payload)
    _repair_missing_topology_nodes_in_payload(candidate)
    return candidate != payload


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


def _format_test_detail_value(value: object) -> str:
    """
    NAME
        _format_test_detail_value - Format one test detail sample value for concise UI display.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _presence_override_from_runtime_device(runtime_device: Dict[str, Any]) -> str:
    """
    NAME
        _presence_override_from_runtime_device - Convert runtime presence confidence into a topology override bucket.
    """
    presence_value = runtime_device.get("presenceConfidence")
    if not isinstance(presence_value, (int, float)):
        return NT_VALUE_EMPTY
    if float(presence_value) <= 0.05:
        return "NONE"
    if float(presence_value) >= 0.5:
        return "HIGH"
    return "LOW"


def _build_console_snapshot_from_entries(entries: List[object], now_s: Optional[float] = None) -> Dict[str, Any]:
    """
    NAME
        _build_console_snapshot_from_entries - Build the Evidence console snapshot from host-side console entries.
    """
    return build_console_snapshot_from_entries_shared(entries, now_s)


class BringupControlUI(tk.Tk):
    """
    NAME
        BringupControlUI - Bringup command UI with a fixed action panel.

    DESCRIPTION
        Builds a fixed action list and a scrolling output panel. Commands are
        sent over the shared REST bridge session.
    """

    def __init__(
        self,
        ui_table,
        tests_table,
        rio_host: str,
        tcp_port: int,
        is_connected: Optional[Callable[[], bool]] = None,
        on_close: Optional[Callable[[], None]] = None,
        visibility_provider: Optional[object] = None,
        console_monitor: Optional[object] = None,
        restart_can_sniffer: Optional[Callable[[], bool]] = None,
    ) -> None:
        super().__init__()
        self._print_version_banner()
        self.title("Bringup Control")
        self.geometry("1100x720")
        self.minsize(900, 600)
        self._ui_table = ui_table
        self._tests_table = tests_table
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
        self._console_monitor = console_monitor
        self._restart_can_sniffer = restart_can_sniffer
        self._visibility_last_update = 0.0
        self._visibility_sources: List[Dict[str, object]] = []
        self._visibility_columns: List[str] = []
        self._visibility_table: Optional[ttk.Treeview] = None
        self._visibility_unrecognized_table: Optional[ttk.Treeview] = None
        self._visibility_ctre_raw_table: Optional[ttk.Treeview] = None
        self._visibility_passive_detail_text: Optional[tk.Text] = None
        self._visibility_row_meta: Dict[str, Dict[str, object]] = {}
        self._visibility_selected_label = NT_VALUE_EMPTY
        self._visibility_selected_unexpected = False
        self._visibility_summary_var = tk.StringVar(value=VIS_SOURCE_COUNT_UNKNOWN)
        self._latest_visibility_snapshot: Dict[str, Any] = {}
        self._latest_visibility_summary: Dict[str, Any] = {}
        self._latest_passive_result = None
        self._fault_finder_status_var = tk.StringVar(value=CAN_FAULT_FINDER_STATUS_NOT_RUN)
        self._fault_finder_text: Optional[tk.Text] = None
        self._fault_finder_last_run_at = 0.0
        self._fault_finder_run_count = 0
        self._fault_finder_result: Dict[str, Any] = {}
        self._evidence_panel: Optional[ttk.Frame] = None
        self._evidence_live_view: Optional[LiveTopologyView] = None
        self._evidence_table: Optional[ttk.Treeview] = None
        self._evidence_engine_status: Dict[str, Any] = default_evidence_engine_status()
        self._evidence_engine_banner_var = tk.StringVar(
            value=evidence_engine_banner_text(self._evidence_engine_status)
        )
        self._evidence_enrichment_snapshot: Dict[str, Any] = default_enrichment_run_snapshot()
        self._evidence_enrichment_status_var = tk.StringVar(
            value=enrichment_run_status_text(self._evidence_enrichment_snapshot)
        )
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
        self._evidence_eval_budget = 2
        self._evidence_eval_class_order = [
            DEVICE_CLASS_MOTION,
            DEVICE_CLASS_INFRASTRUCTURE,
            DEVICE_CLASS_UNPROFILED,
        ]
        self._evidence_eval_cursor_class_index = 0
        self._evidence_eval_cursor_device_index = 0
        self._evidence_eval_generation = NT_VALUE_EMPTY
        self._evidence_eval_cache: Dict[str, Dict[str, Any]] = {}
        self._evidence_eval_dirty_labels: Dict[str, Dict[str, Any]] = {}
        self._evidence_eval_source_fingerprints: Dict[str, Tuple[Any, ...]] = {}
        self._evidence_last_probe_at = 0.0
        self._evidence_probe_pending = False
        self._evidence_probe_run_count = 0
        self._evidence_probe_complete_count = 0
        self._evidence_last_probe_completed_at = 0.0
        self._evidence_last_probe_complete_seq: Optional[int] = None
        self._evidence_probe_results_by_label: Dict[str, Dict[str, Any]] = {}
        self._last_selected_test = None
        self._last_ui_selected_test_intent = ""
        self._last_robot_selected_test_name = ""
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
        self._live_topology_lens_var = tk.StringVar(value=LIVE_LENS_DEFAULT)
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
        self._pending_runtime_active_expected: Optional[bool] = None
        self._pending_controlled_lifecycle_expected: Optional[bool] = None
        self._pending_scope_member_labels_expected: Tuple[str, ...] = tuple()
        self._scope_transition_started_at = 0.0
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
        self._latest_tests_state_payload: Dict[str, Any] = {}
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
        self._manual_duty_block_reason = MANUAL_DUTY_BLOCK_REASON_NONE
        self._manual_duty_block_since = 0.0
        self._manual_duty_diag_signature_by_label: Dict[str, Tuple[object, ...]] = {}
        self._manual_motion_checks: Dict[str, Dict[str, Any]] = {}
        self._manual_test_observations: Dict[str, Dict[str, Any]] = {}
        self._profile_devices: Dict[str, Dict[str, Any]] = {}
        self._pending_profile_device_definitions: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._profile_active_group_member_labels: Tuple[str, ...] = tuple()
        self._test_profile_devices: Dict[str, Dict[str, Any]] = {}
        self._remembered_manual_active_group_members: List[Dict[str, Any]] = []
        self._tests_active_group_rows: List[Dict[str, Any]] = []
        self._tests_active_group_membership_key: Tuple[str, ...] = tuple()
        self._config_path_override: Optional[Path] = None
        self._local_profiles_payload_override: Optional[Dict[str, object]] = None
        self._config_session_dirty = False
        self._config_session_in_memory_only = False
        self._group_owner_mode = GROUP_SOURCE_MANUAL
        self._last_right_tab_text = NT_VALUE_EMPTY
        self._pending_tests_boundary_transition: Optional[Tuple[str, str]] = None
        self._robot_selected_profile = PROFILE_NONE
        self._robot_active_runtime_profile = PROFILE_NONE
        self._pending_robot_profile_selection = PROFILE_NONE
        self._last_profile_context = PROFILE_NONE
        self._last_profile_mismatch_prompt: Optional[Tuple[str, str]] = None
        self._suppress_host_profile_context_sync = HOST_PROFILE_SYNC_NOT_SUPPRESSED
        self._last_test_result_signature: Optional[Tuple[int, str, str]] = None
        self._ui_command_prefs = _load_ui_command_prefs()
        self._ui_auto_select_default_profile = _load_ui_auto_select_default_pref()
        self._ui_show_visibility_tab = _load_ui_show_visibility_tab_pref()
        self._ui_show_wall_clock = _load_ui_show_wall_clock_pref()
        self._ui_theme_name = _load_ui_theme_pref()
        self._theme_palette = get_ui_theme_palette(self._ui_theme_name)
        self._ttk_style = ttk.Style(self)
        self._ui_pref_vars: Dict[str, tk.BooleanVar] = {}
        self._build_menu()
        self._build_ui()
        self._apply_ui_theme()
        self._apply_profile_selection(self._profile_box.get(), reload_views=True)
        self.after_idle(self._poll_runtime_ui_state)
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
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label=BUTTON_NEW_BLANK_CONFIG, command=self._new_blank_config_from_ui)
        file_menu.add_command(label=BUTTON_OPEN_CONFIG, command=self._open_config_from_ui)
        file_menu.add_command(label=BUTTON_SAVE_CONFIG, command=self._save_config_from_ui)
        file_menu.add_command(label=BUTTON_SAVE_CONFIG_AS, command=self._save_config_as_from_ui)
        file_menu.add_command(label=BUTTON_RENAME_PROFILE, command=self._rename_profile_from_ui)
        prefs_menu = tk.Menu(menubar, tearoff=False)
        self._ui_theme_var = tk.StringVar(value=self._ui_theme_name)
        theme_menu = tk.Menu(prefs_menu, tearoff=False)
        for theme_name in list_ui_theme_names():
            palette = get_ui_theme_palette(theme_name)
            theme_menu.add_radiobutton(
                label=palette.display_name,
                value=theme_name,
                variable=self._ui_theme_var,
                command=self._set_ui_theme_pref,
            )
        prefs_menu.add_cascade(label="Theme", menu=theme_menu)
        prefs_menu.add_separator()
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
            label="Show CAN Visibility Tab",
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
        prefs_menu.add_command(label=BUTTON_SAVE_CONFIG, command=self._save_config_from_ui)
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
        help_menu.add_command(
            label=CAN_FRAME_FAMILY_HELP_MENU_LABEL,
            command=self._show_can_frame_family_help,
        )
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="File", menu=file_menu)
        menubar.add_cascade(label="Preferences", menu=prefs_menu)
        menubar.add_cascade(label="Help", menu=help_menu)
        self._file_menu = file_menu
        self._menubar = menubar
        self._prefs_menu = prefs_menu
        self._theme_menu = theme_menu
        self._help_menu = help_menu
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

        try:
            profile_payload = self._load_local_profiles_payload()
        except Exception:
            profile_payload = {}
        profile_names = self._profile_names_from_payload(profile_payload)
        profiles = self._selectable_profiles_from_payload(profile_payload)
        active_profile = _startup_selected_profile(
            profile_names,
            self._ui_auto_select_default_profile,
            default_profile_name=self._default_profile_name_from_payload(profile_payload),
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
            header, text=BUTTON_SAVE_CONFIG, command=self._save_config_from_ui
        ).pack(side="left", padx=(6, 0))
        ttk.Button(
            header, text=BUTTON_DOWNLOAD_CONFIG, command=self._download_current_config_from_ui
        ).pack(side="left", padx=(6, 0))
        self._build_runtime_scope_buttons(header)
        ttk.Button(
            header, text=BUTTON_SHOW_RUNTIME_STATE, command=self._show_runtime_state_from_ui
        ).pack(side="left", padx=(6, 0))
        self._activation_membership_mode_var = tk.StringVar(
            value=ACTIVATION_MEMBERSHIP_MODE_DEFAULT
        )
        ttk.Label(header, text=ACTIVATION_MEMBERSHIP_LABEL).pack(
            side="left", padx=(10, 4)
        )
        activation_membership_box = ttk.Combobox(
            header,
            values=ACTIVATION_MEMBERSHIP_MODE_VALUES,
            state="readonly",
            width=8,
            textvariable=self._activation_membership_mode_var,
        )
        activation_membership_box.pack(side="left")
        self._activation_membership_mode_box = activation_membership_box
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
        self._pending_label = ttk.Label(
            header,
            text="",
            foreground=self._theme_palette.status_warn_fg,
        )
        self._pending_label.pack(side="left", padx=(16, 4))

        status = ttk.Label(
            header,
            text="REST Disconnected",
            foreground=self._theme_palette.status_error_fg,
        )
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

        fault_finder_panel = ttk.Frame(notebook)
        notebook.add(fault_finder_panel, text=CAN_FAULT_FINDER_TAB_LABEL)
        self._build_can_fault_finder_panel(fault_finder_panel)

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
        ttk.Label(controls, text=LIVE_LENS_LABEL).pack(side="left", padx=(12, 4))
        lens_menu = ttk.OptionMenu(
            controls,
            self._live_topology_lens_var,
            LIVE_LENS_DEFAULT,
            *LIVE_LENS_OPTION_LABELS,
            command=lambda _value: self._apply_live_topology_lens(),
        )
        lens_menu.pack(side="left")
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
            manage_runtime_notice_internally=False,
            theme_name=self._ui_theme_name,
        )
        self._sync_live_view_action_states()
        self._live_view.set_show_groups(self._live_groups_var.get())
        self._apply_live_topology_lens()
        self._live_view.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _build_runtime_scope_buttons(self, parent: tk.Widget) -> None:
        """
        NAME
            _build_runtime_scope_buttons - Create and retain the top-bar runtime scope buttons.

        DESCRIPTION
            The shared button-state logic updates these retained widget references
            in `_update_action_enabled()`. The buttons must therefore be stored on
            the UI instance rather than created as anonymous temporaries.
        """
        activate_scope_button = ttk.Button(
            parent,
            text=BUTTON_RUNTIME_ACTIVATE,
            command=self._runtime_activate_from_ui,
        )
        activate_scope_button.pack(side="left", padx=(6, 0))
        deactivate_scope_button = ttk.Button(
            parent,
            text=BUTTON_RUNTIME_DEACTIVATE,
            command=self._runtime_deactivate_from_ui,
        )
        deactivate_scope_button.pack(side="left", padx=(6, 0))
        self._activate_scope_button = activate_scope_button
        self._deactivate_scope_button = deactivate_scope_button

    def _build_can_fault_finder_panel(self, parent: tk.Widget) -> None:
        """
        NAME
            _build_can_fault_finder_panel - Build the dedicated CAN fault-finder tab.
        """
        header = ttk.Frame(parent)
        header.pack(fill=VIS_FILL_X, padx=8, pady=(8, 4))
        ttk.Label(header, text=CAN_FAULT_FINDER_TITLE, font=("Trebuchet MS", 13)).pack(
            side=VIS_PACK_SIDE_LEFT
        )
        ttk.Button(
            header,
            text=CAN_FAULT_FINDER_RUN_BUTTON,
            command=self._run_can_fault_check,
        ).pack(side=VIS_PACK_SIDE_RIGHT)
        ttk.Label(header, textvariable=self._fault_finder_status_var).pack(
            side=VIS_PACK_SIDE_RIGHT,
            padx=(0, 8),
        )
        body = ttk.Frame(parent)
        body.pack(fill=VIS_FILL_BOTH, expand=True, padx=8, pady=(0, 8))
        text = tk.Text(body, height=20, wrap="word", state="normal")
        text.insert("1.0", CAN_FAULT_FINDER_TEXT_NOT_RUN)
        text.configure(state="disabled")
        text.pack(side=VIS_PACK_SIDE_LEFT, fill=VIS_FILL_BOTH, expand=True)
        scroll = ttk.Scrollbar(body, command=text.yview)
        scroll.pack(side=VIS_PACK_SIDE_RIGHT, fill="y")
        text.configure(yscrollcommand=scroll.set)
        self._fault_finder_text = text

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
        active_group_table = ttk.Treeview(
            active_group_body,
            columns=(
                TEST_ACTIVE_GROUP_COL_LABEL,
                TEST_ACTIVE_GROUP_COL_ENABLED,
                TEST_ACTIVE_GROUP_COL_LOCKED,
                TEST_ACTIVE_GROUP_COL_INSTANTIATED,
                TEST_ACTIVE_GROUP_COL_SCOPE_ACTIVE,
                TEST_ACTIVE_GROUP_COL_NOTE,
            ),
            show="headings",
            height=TEST_LIBRARY_LISTBOX_HEIGHT,
        )
        active_group_table.heading(TEST_ACTIVE_GROUP_COL_LABEL, text=TEST_ACTIVE_GROUP_COL_LABEL)
        active_group_table.heading(TEST_ACTIVE_GROUP_COL_ENABLED, text=TEST_ACTIVE_GROUP_COL_ENABLED)
        active_group_table.heading(TEST_ACTIVE_GROUP_COL_LOCKED, text=TEST_ACTIVE_GROUP_COL_LOCKED)
        active_group_table.heading(TEST_ACTIVE_GROUP_COL_INSTANTIATED, text=TEST_ACTIVE_GROUP_COL_INSTANTIATED)
        active_group_table.heading(TEST_ACTIVE_GROUP_COL_SCOPE_ACTIVE, text=TEST_ACTIVE_GROUP_COL_SCOPE_ACTIVE)
        active_group_table.heading(TEST_ACTIVE_GROUP_COL_NOTE, text=TEST_ACTIVE_GROUP_COL_NOTE)
        active_group_table.column(TEST_ACTIVE_GROUP_COL_LABEL, width=150, anchor="w")
        active_group_table.column(TEST_ACTIVE_GROUP_COL_ENABLED, width=70, anchor="center")
        active_group_table.column(TEST_ACTIVE_GROUP_COL_LOCKED, width=70, anchor="center")
        active_group_table.column(TEST_ACTIVE_GROUP_COL_INSTANTIATED, width=90, anchor="center")
        active_group_table.column(TEST_ACTIVE_GROUP_COL_SCOPE_ACTIVE, width=90, anchor="center")
        active_group_table.column(TEST_ACTIVE_GROUP_COL_NOTE, width=160, anchor="w")
        active_group_table.pack(side="left", fill="both", expand=True)
        active_group_scroll = ttk.Scrollbar(active_group_body, command=active_group_table.yview)
        active_group_scroll.pack(side="right", fill="y")
        active_group_table.configure(yscrollcommand=active_group_scroll.set)
        self._tests_active_group_table = active_group_table
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
        restart_button = ttk.Button(
            header,
            text=VIS_RESTART_SNIFFER_BUTTON,
            command=self._restart_visibility_can_sniffer,
        )
        restart_button.pack(side=VIS_PACK_SIDE_RIGHT, padx=VIS_HEADER_BUTTON_PAD)
        if not callable(self._restart_can_sniffer):
            restart_button.state(["disabled"])
        self._visibility_restart_sniffer_button = restart_button
        ttk.Button(
            header,
            text=VIS_FRAME_FAMILY_HELP_BUTTON,
            command=self._show_can_frame_family_help,
        ).pack(side=VIS_PACK_SIDE_RIGHT, padx=VIS_HEADER_BUTTON_PAD)

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
            manage_runtime_notice_internally=False,
            theme_name=self._ui_theme_name,
        )
        self._sync_live_view_action_states()
        self._visibility_live_view.set_show_groups(self._live_groups_var.get())
        self._visibility_live_view.set_overlay_lens(TOPOLOGY_LENS_VISIBILITY)
        self._visibility_live_view.pack(fill="both", expand=True)

        table_panel = ttk.Panedwindow(body, orient=VIS_TABLE_SPLIT_ORIENT)
        body.add(table_panel, weight=2)

        defined_frame = ttk.LabelFrame(table_panel, text=VIS_DEFINED_SECTION_LABEL, padding=VIS_PAD_TABLE)
        table_panel.add(defined_frame, weight=3)
        self._visibility_table = self._build_visibility_table_widget(defined_frame)
        self._visibility_table.bind("<Double-1>", self._on_visibility_row_double_click)
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
        self._visibility_unrecognized_table.bind("<Button-3>", self._on_visibility_unrecognized_right_click)

        ctre_raw_frame = ttk.LabelFrame(
            table_panel,
            text=VIS_CTRE_RAW_SECTION_LABEL,
            padding=VIS_PAD_TABLE,
        )
        table_panel.add(ctre_raw_frame, weight=2)
        ctre_raw_body = ttk.Panedwindow(ctre_raw_frame, orient="vertical")
        ctre_raw_body.pack(fill=VIS_FILL_BOTH, expand=True)
        raw_table_frame = ttk.Frame(ctre_raw_body)
        ctre_raw_body.add(raw_table_frame, weight=2)
        self._visibility_ctre_raw_table = self._build_visibility_ctre_raw_table_widget(raw_table_frame)
        passive_detail_frame = ttk.LabelFrame(
            ctre_raw_body,
            text=VIS_PASSIVE_DEEP_DIVE_SECTION_LABEL,
            padding=6,
        )
        ctre_raw_body.add(passive_detail_frame, weight=3)
        passive_detail_text = tk.Text(passive_detail_frame, height=VIS_DETAIL_TEXT_HEIGHT, wrap="word")
        passive_detail_text.pack(fill=VIS_FILL_BOTH, expand=True)
        passive_detail_text.configure(state="disabled")
        self._visibility_passive_detail_text = passive_detail_text

        if self._visibility_provider is None:
            self._visibility_table.insert(VIS_TREE_ROOT, VIS_TREE_END, values=[VIS_EMPTY_MESSAGE])
        elif self._visibility_ctre_raw_table is not None:
            self._visibility_ctre_raw_table.insert(VIS_TREE_ROOT, VIS_TREE_END, values=[VIS_RAW_EMPTY_MESSAGE])
        self._set_visibility_passive_detail_text(EVIDENCE_SOURCE_NONE)

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
        self._set_visibility_passive_detail_text(EVIDENCE_SOURCE_NONE)

    def _reset_scratch_visibility_state(self) -> None:
        """
        NAME
            _reset_scratch_visibility_state - Clear passive observer memory for scratch-config starts.
        """
        provider = self.__dict__.get("_visibility_provider")
        if provider is not None:
            if hasattr(provider, "set_allow_suggested_labels_for_unexpected"):
                provider.set_allow_suggested_labels_for_unexpected(False)
            if hasattr(provider, "reset_observed_state"):
                provider.reset_observed_state()
        self._latest_visibility_snapshot = {}
        self._latest_visibility_summary = {}
        self._latest_passive_result = None
        self._visibility_sources = []
        self._visibility_columns = []
        self._visibility_row_meta = {}
        self._visibility_selected_label = NT_VALUE_EMPTY
        self._visibility_selected_unexpected = False
        self._clear_visibility_panels()
        self._update_visibility_summary({})
        self._refresh_evidence_view()

    def _set_visibility_passive_detail_text(self, text_value: str) -> None:
        """
        NAME
            _set_visibility_passive_detail_text - Replace the shared passive CAN deep-dive block for the selected visibility row.
        """
        widget = self.__dict__.get("_visibility_passive_detail_text")
        if widget is None:
            return
        self._replace_readonly_text_preserve_scroll(widget, text_value or EVIDENCE_SOURCE_NONE)

    def _build_evidence_panel(self, parent: tk.Widget) -> None:
        """
        NAME
            _build_evidence_panel - Build the topology-first device evidence tab.
        """
        header = ttk.Frame(parent)
        header.pack(fill=VIS_FILL_X, padx=8, pady=(8, 0))
        ttk.Button(
            header,
            text=ENRICHMENT_RUN_LABEL,
            command=self._run_evidence_enrichment,
        ).pack(side=VIS_PACK_SIDE_RIGHT)
        ttk.Label(
            header,
            textvariable=self._evidence_enrichment_status_var,
        ).pack(side=VIS_PACK_SIDE_RIGHT, padx=(0, 8))

        body = ttk.Panedwindow(parent, orient="vertical")
        body.pack(fill=VIS_FILL_BOTH, expand=True, padx=8, pady=8)

        top = ttk.Panedwindow(body, orient="horizontal")
        body.add(top, weight=EVIDENCE_LAYOUT_TOP_WEIGHT)

        left_column = ttk.Frame(top)
        top.add(left_column, weight=EVIDENCE_TOPOLOGY_WEIGHT)

        topology_frame = ttk.Frame(left_column)
        topology_frame.configure(
            width=EVIDENCE_TOPOLOGY_FRAME_WIDTH,
            height=EVIDENCE_TOPOLOGY_FRAME_HEIGHT,
        )
        topology_frame.pack_propagate(False)
        topology_frame.pack(fill=VIS_FILL_X, expand=False)
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
            show_runnable_panel=False,
            manage_runtime_notice_internally=False,
            title_text=evidence_overall_title(
                EVIDENCE_TITLE_TEXT,
                self._evidence_engine_status,
            ),
            fit_on_load=True,
            theme_name=self._ui_theme_name,
        )
        self._sync_live_view_action_states()
        self._evidence_live_view.set_show_groups(self._live_groups_var.get())
        self._evidence_live_view.set_overlay_lens(TOPOLOGY_LENS_EVIDENCE)
        self._evidence_live_view.pack(fill=VIS_FILL_BOTH, expand=True)

        left_sections = ttk.Panedwindow(left_column, orient="vertical")
        left_sections.pack(fill=VIS_FILL_BOTH, expand=True, pady=(8, 0))

        inspector = ttk.Frame(top, padding=(8, 0, 0, 0))
        top.add(inspector, weight=EVIDENCE_INSPECTOR_WEIGHT)
        self._build_evidence_inspector(inspector, left_sections)

        table_frame = ttk.LabelFrame(body, text="Device Summary", padding=VIS_PAD_TABLE)
        body.add(table_frame, weight=EVIDENCE_LAYOUT_BOTTOM_WEIGHT)
        table_header = ttk.Frame(table_frame)
        table_header.pack(fill=VIS_FILL_X, pady=(0, 6))
        ttk.Label(table_header, textvariable=self._evidence_summary_var).pack(side=VIS_PACK_SIDE_LEFT)
        ttk.Label(
            table_header,
            textvariable=self._evidence_engine_banner_var,
        ).pack(side=VIS_PACK_SIDE_LEFT, padx=(12, 0))
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

    def _build_evidence_inspector(
        self,
        parent: tk.Widget,
        left_sections: Optional[ttk.Panedwindow] = None,
    ) -> None:
        """
        NAME
            _build_evidence_inspector - Build the selected-device evidence inspector.
        """
        self._evidence_scope_headline_var = tk.StringVar(value=TEST_SCOPE_PANEL_WAITING_HEADLINE)
        self._evidence_scope_detail_var = tk.StringVar(value=RUNNABLE_SCOPE_PANEL_WAITING_DETAIL)
        status_row = ttk.Frame(parent)
        status_row.pack(fill=VIS_FILL_X, pady=(0, 8))
        evidence_status_panel = tk.Frame(
            status_row,
            bg=TEST_SCOPE_PANEL_NEUTRAL_BG,
            highlightbackground=TEST_SCOPE_PANEL_BORDER,
            highlightthickness=1,
            bd=0,
            padx=TEST_SCOPE_PANEL_PAD_X,
            pady=TEST_SCOPE_PANEL_PAD_Y,
        )
        evidence_status_panel.pack(side=VIS_PACK_SIDE_RIGHT, anchor="e")
        self._evidence_scope_panel = evidence_status_panel
        self._evidence_scope_title_label = tk.Label(
            evidence_status_panel,
            text=RUNNABLE_SCOPE_PANEL_TITLE,
            bg=TEST_SCOPE_PANEL_NEUTRAL_BG,
            fg=TEST_SCOPE_PANEL_NEUTRAL_FG,
            anchor="w",
            font=TEST_SCOPE_PANEL_DETAIL_FONT,
        )
        self._evidence_scope_title_label.pack(anchor="w")
        self._evidence_scope_headline_label = tk.Label(
            evidence_status_panel,
            textvariable=self._evidence_scope_headline_var,
            bg=TEST_SCOPE_PANEL_NEUTRAL_BG,
            fg=TEST_SCOPE_PANEL_NEUTRAL_FG,
            anchor="w",
            justify="left",
            font=TEST_SCOPE_PANEL_HEADLINE_FONT,
        )
        self._evidence_scope_headline_label.pack(anchor="w", pady=(2, 0))
        self._evidence_scope_detail_label = tk.Label(
            evidence_status_panel,
            textvariable=self._evidence_scope_detail_var,
            bg=TEST_SCOPE_PANEL_NEUTRAL_BG,
            fg=TEST_SCOPE_PANEL_NEUTRAL_FG,
            anchor="w",
            justify="left",
            wraplength=TEST_SCOPE_PANEL_WRAP,
            font=TEST_SCOPE_PANEL_DETAIL_FONT,
        )
        self._evidence_scope_detail_label.pack(anchor="w", pady=(2, 0))
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
        interpretation = ttk.LabelFrame(
            parent,
            text=evidence_section_title(
                EVIDENCE_INTERPRETATION_TEXT,
                self._evidence_engine_status,
                SECTION_INTERPRETATION,
            ),
            padding=8,
        )
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
        self._build_evidence_text_section(
            left_sections if left_sections is not None else parent,
            EVIDENCE_BUS_HEALTH_TEXT,
            section_key=SECTION_CONSOLE,
            text_height=EVIDENCE_TEXT_HEIGHT_DEFAULT,
            paned_weight=EVIDENCE_INSPECTOR_PANED_WEIGHT_DEFAULT,
            pack_pady=(0, 8),
        )
        sections = ttk.Panedwindow(parent, orient="vertical")
        sections.pack(fill=VIS_FILL_BOTH, expand=True)
        for title in (
            EVIDENCE_ENRICHMENT_TEXT,
            EVIDENCE_CONSOLE_TEXT,
            EVIDENCE_PROBE_TEXT,
            EVIDENCE_MANUAL_TEXT,
            EVIDENCE_NOTES_TEXT,
        ):
            section_weight = EVIDENCE_INSPECTOR_PANED_WEIGHT_DEFAULT
            if title == EVIDENCE_ENRICHMENT_TEXT:
                section_weight = EVIDENCE_INSPECTOR_PANED_WEIGHT_DEFAULT
            elif title == EVIDENCE_PROBE_TEXT:
                section_weight = EVIDENCE_INSPECTOR_PANED_WEIGHT_PROBE
            elif title == EVIDENCE_MANUAL_TEXT:
                section_weight = EVIDENCE_INSPECTOR_PANED_WEIGHT_MANUAL
            elif title == EVIDENCE_NOTES_TEXT:
                section_weight = EVIDENCE_INSPECTOR_PANED_WEIGHT_NOTES
            text_height = EVIDENCE_TEXT_HEIGHT_DEFAULT
            if title == EVIDENCE_ENRICHMENT_TEXT:
                text_height = EVIDENCE_TEXT_HEIGHT_ENRICHMENT
            elif title == EVIDENCE_PROBE_TEXT:
                text_height = EVIDENCE_TEXT_HEIGHT_PROBE
            elif title == EVIDENCE_MANUAL_TEXT:
                text_height = EVIDENCE_TEXT_HEIGHT_MANUAL
            elif title == EVIDENCE_NOTES_TEXT:
                text_height = EVIDENCE_TEXT_HEIGHT_NOTES
            self._build_evidence_text_section(
                sections,
                title,
                section_key=self._evidence_section_key_for_title(title),
                text_height=text_height,
                paned_weight=section_weight,
                include_manual_buttons=(title == EVIDENCE_MANUAL_TEXT),
            )
        if left_sections is not None:
            self._build_evidence_text_section(
                left_sections,
                EVIDENCE_PRESENCE_TEXT,
                section_key=SECTION_PRESENCE_CHECK,
                text_height=EVIDENCE_TEXT_HEIGHT_DEFAULT,
                paned_weight=EVIDENCE_INSPECTOR_PANED_WEIGHT_DEFAULT,
            )
            self._build_evidence_text_section(
                left_sections,
                EVIDENCE_PASSIVE_TEXT,
                section_key=SECTION_PASSIVE,
                text_height=EVIDENCE_TEXT_HEIGHT_DEFAULT,
                paned_weight=EVIDENCE_INSPECTOR_PANED_WEIGHT_DEFAULT,
            )

    def _build_evidence_text_section(
        self,
        parent: tk.Widget,
        title: str,
        *,
        section_key: str,
        text_height: int,
        paned_weight: int,
        include_manual_buttons: bool = False,
        pack_pady: tuple[int, int] = (0, 0),
    ) -> None:
        """
        NAME
            _build_evidence_text_section - Build one Evidence read-only text section.
        """
        frame = ttk.LabelFrame(
            parent,
            text=evidence_section_title(
                title,
                self._evidence_engine_status,
                section_key,
            ),
            padding=6,
        )
        if isinstance(parent, ttk.Panedwindow):
            parent.add(frame, weight=paned_weight)
        else:
            frame.pack(fill=VIS_FILL_X, pady=pack_pady)
        if include_manual_buttons:
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
        text = tk.Text(frame, height=text_height, wrap="word")
        text.pack(fill=VIS_FILL_BOTH, expand=True)
        text.configure(state="disabled")
        self._evidence_text_widgets[title] = text

    def _evidence_section_key_for_title(self, title: str) -> str:
        """
        NAME
            _evidence_section_key_for_title - Map one Evidence inspector title to its engine-ownership section key.
        """
        if title == EVIDENCE_PRESENCE_TEXT:
            return SECTION_PRESENCE_CHECK
        if title == EVIDENCE_PASSIVE_TEXT:
            return SECTION_PASSIVE
        if title == EVIDENCE_CONSOLE_TEXT:
            return SECTION_CONSOLE
        if title == EVIDENCE_ENRICHMENT_TEXT:
            return SECTION_ENRICHMENT
        if title == EVIDENCE_PROBE_TEXT:
            return SECTION_PROBE
        if title == EVIDENCE_MANUAL_TEXT:
            return SECTION_MANUAL
        if title == EVIDENCE_NOTES_TEXT:
            return SECTION_INTERPRETATION
        return SECTION_INTERPRETATION

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
        self._fit_current_topology_tab()
        if self._evidence_tab_active():
            self._refresh_evidence_view()

    def _fit_current_topology_tab(self) -> None:
        """
        NAME
            _fit_current_topology_tab - Fit the current diagram-backed tab to its window.
        """
        current_tab = self._current_right_tab_text()
        live_view = None
        if current_tab == LIVE_TOPOLOGY_TAB_LABEL:
            live_view = self.__dict__.get("_live_view")
        elif current_tab == VIS_TAB_LABEL:
            live_view = self.__dict__.get("_visibility_live_view")
        elif current_tab == EVIDENCE_TAB_LABEL:
            live_view = self.__dict__.get("_evidence_live_view")
        if live_view is not None:
            try:
                live_view.schedule_fit_to_window()
            except Exception:
                pass

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
        self._last_ui_selected_test_intent = selected_name
        tests_tab_active = self._current_right_tab_text() == TEST_LIBRARY_TAB_LABEL
        if not tests_tab_active:
            self._selected_test_var.set(selected_name)
            self._refresh_selected_test_scope_status()
            return
        if not self._tcp_connected:
            self._selected_test_var.set(selected_name)
            self._sync_selected_test_devices_panel_local()
            self._refresh_selected_test_scope_status()
            return
        if self._tracker.is_pending():
            self._sync_selected_test_devices_panel_local()
            self._refresh_selected_test_scope_status()
            return
        if not self._robot_knows_test_name(selected_name):
            self._sync_selected_test_devices_panel_local()
            self._append_output(TEST_SCOPE_DETAIL_NOT_LOADED_ON_ROBOT)
            self._append_test_output(TEST_SCOPE_DETAIL_NOT_LOADED_ON_ROBOT)
            self._refresh_selected_test_scope_status()
            return
        self._selected_test_var.set(selected_name)
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
        if (
            self._scope_context_kind() == GROUP_SOURCE_SELECTED_TEST
            and self.__dict__.get("_controlled_lifecycle_active_known") is True
        ):
            requires_scope_swap = self._selected_test_membership_change_requires_scope_swap()
            self._sync_selected_test_devices_panel_local(
                loaded_to_robot=not requires_scope_swap
            )
            if requires_scope_swap:
                self._append_output(TEST_SCOPE_DETAIL_SCOPE_SWAP_REQUIRED)
                self._append_test_output(TEST_SCOPE_DETAIL_SCOPE_SWAP_REQUIRED)
            self._refresh_selected_test_scope_status()
            return
        self._sync_selected_test_devices_panel_local(
            loaded_to_robot=self._selected_test_required_membership_loaded_to_robot()
        )
        self._refresh_selected_test_scope_status()

    def _robot_knows_test_name(self, name: str) -> bool:
        """
        NAME
            _robot_knows_test_name - Return whether the robot currently reports one test name in /tests/state rows.
        """
        target = str(name or "").strip()
        if not target:
            return False
        for candidate in self._resolve_test_names_from_rows():
            if str(candidate or "").strip() == target:
                return True
        return False

    def _handle_tests_boundary_transition(self, previous_tab: str, current_tab: str) -> None:
        """
        NAME
            _handle_tests_boundary_transition - Switch Tests/manual ownership without tearing down the shared active-group scope.
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
            self._group_owner_mode = GROUP_SOURCE_MANUAL
            return
        self._group_owner_mode = GROUP_SOURCE_SELECTED_TEST
        self._load_selected_test_into_active_group(force_replace=True)

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
        if self.__dict__.get("_profile_box") is not None and self._selected_profile_name() == PROFILE_NONE:
            return False
        if self.__dict__.get("_controlled_lifecycle_active_known") is True:
            return False
        if self._runtime_active_group_members():
            return False
        return not bool(self.__dict__.get("_profile_active_group_member_labels", tuple()))

    def _send_and_wait(self, command: str, args: Dict[str, Any]) -> bool:
        """
        NAME
            _send_and_wait - Send one tracked command and block briefly until its terminal OUT result arrives.
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
        ack_status = ""
        while time.time() < deadline:
            events = self._session.poll_events()
            if not events:
                self.update_idletasks()
                time.sleep(0.02)
                continue
            for event in events:
                if int(event.seq) == int(seq) and event.type == "ack":
                    ack_status = str(event.status or "").strip().lower()
                self._handle_tcp_response(event)
                if int(event.seq) == int(seq) and event.type == "out":
                    final_status = ack_status or str(event.status or "").strip().lower()
                    return final_status == "ok"
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

    def _deactivate_selected_test_scope_blocking(self) -> bool:
        """
        NAME
            _deactivate_selected_test_scope_blocking - Deactivate the selected-test lifecycle scope when leaving Tests.
        """
        ts = timestamp_hms()
        self._append_output(f"{ts} CMD deactivateSelectedTestDevices")
        self._last_cmd = ("deactivateSelectedTestDevices", {})
        ok = self._send_and_wait("deactivateSelectedTestDevices", {})
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
            _selected_test_required_rows - Build ordered Tests-tab scope rows from robot-required devices with local fallback.
        """
        selected_test_var = self.__dict__.get("_selected_test_var")
        selected_name = (
            str(selected_test_var.get() or "").strip()
            if selected_test_var is not None and hasattr(selected_test_var, "get")
            else NT_VALUE_EMPTY
        )
        selected_row = self._selected_test_row(selected_name)
        required_devices = list(selected_row.get("requiredDevices", [])) if isinstance(selected_row, dict) else []
        if not required_devices:
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
                    "locked": False,
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
            payload = self._current_materialized_profiles_payload()
            store = robot_test_dsl_store_from_root_payload(payload)
        except Exception:
            return []
        tests_by_name = getattr(store, "tests_by_name", {})
        entry = tests_by_name.get(clean_name) if isinstance(tests_by_name, dict) else None
        normalized = getattr(entry, "normalized", None)
        current_source_name = str(self.__dict__.get("_selected_test_source_name", "") or "").strip()
        if normalized is None and current_source_name == clean_name:
            try:
                normalized = compile_source(clean_name, self._current_test_source_text())
            except Exception:
                normalized = None
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

    def _sync_selected_test_devices_panel_local(
        self,
        loaded_to_robot: Optional[bool] = None,
    ) -> None:
        """
        NAME
            _sync_selected_test_devices_panel_local - Refresh Selected Test Devices from the local selected-test DSL model.
        """
        rows = self._selected_test_required_rows()
        self._tests_active_group_rows = rows
        self._tests_active_group_membership_key = self._tests_active_group_membership_key_for_rows(
            rows
        )
        self._tests_active_group_loaded_to_robot = loaded_to_robot
        self._refresh_tests_active_group_panel()

    def _load_selected_test_into_active_group(self, force_replace: bool = False) -> None:
        """
        NAME
            _load_selected_test_into_active_group - Replace robot active-group membership with the selected test devices.
        """
        rows = self._selected_test_required_rows()
        membership_key = self._tests_active_group_membership_key_for_rows(rows)
        changed = membership_key != tuple(self.__dict__.get("_tests_active_group_membership_key", tuple()))
        if not force_replace and not changed:
            self._tests_active_group_rows = rows
            self._refresh_tests_active_group_panel()
            return
        self._tests_active_group_rows = rows
        self._tests_active_group_membership_key = membership_key
        self._tests_active_group_loaded_to_robot = None
        if self._tcp_connected and not self._tracker.is_pending():
            replace_ok = self._replace_active_group_members(rows)
            self._tests_active_group_loaded_to_robot = bool(replace_ok)
            if replace_ok:
                self.after_idle(self._request_runtime_state_refresh)
        self._refresh_tests_active_group_panel()

    def _restore_manual_active_group_members(self) -> None:
        """
        NAME
            _restore_manual_active_group_members - Restore the remembered manual active-group membership after leaving Tests.
        """
        members = list(self.__dict__.get("_remembered_manual_active_group_members", []))
        self._tests_active_group_loaded_to_robot = None
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
        if self._runtime_active_group_members():
            return True
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

    def _runtime_ui_actions_ready(self) -> bool:
        """
        NAME
            _runtime_ui_actions_ready - Return whether top-bar runtime actions should be allowed to evaluate normally.

        DESCRIPTION
            Some REST sessions can temporarily lose the explicit handshake-ready
            flag while still polling fresh runtime state successfully. When that
            happens, disabling both scope buttons is misleading because the UI
            still has a live robot state view and can safely continue using the
            runtime-backed action gates.
        """
        if not self._tcp_connected:
            return False
        if bool(self.__dict__.get("_handshake_done", False)):
            return True
        return bool(self.__dict__.get("_runtime_state_seen", False))

    def _selected_test_has_invalid_members(self) -> bool:
        """
        NAME
            _selected_test_has_invalid_members - Return whether the current Selected Test Devices rows contain invalid members.
        """
        return any(
            SHARED_TEST_ACTIVE_GROUP_STATUS_INVALID in state.statuses
            for state in self._tests_active_group_member_row_states()
        )

    def _scope_control_state(self):
        """
        NAME
            _scope_control_state - Return shared scope-control ownership gates for top-level host actions.
        """
        current_scope_member_labels = [
            str(row.get("label", "")).strip()
            for row in self._runtime_active_group_members()
            if isinstance(row, dict) and bool(row.get("enabled", True)) and str(row.get("label", "")).strip()
        ]
        return resolve_scope_control_state(
            scope_kind=self._runnable_scope_kind(),
            runtime_ui_ready=self._runtime_ui_actions_ready(),
            tracker_pending=self._tracker.is_pending(),
            stale_state=bool(self.__dict__.get("_state_stale", False)),
            runtime_state_seen=bool(self.__dict__.get("_runtime_state_seen", False)),
            runtime_profile_active=bool(self.__dict__.get("_runtime_active_known", False)),
            controlled_lifecycle_active=self.__dict__.get("_controlled_lifecycle_active_known") is True,
            transition_pending=self._scope_transition_pending(),
            runnable_scope_state=self._runnable_scope_state(
                stale_state=bool(self.__dict__.get("_state_stale", False))
            ),
            current_scope_member_labels=current_scope_member_labels,
            desired_scope_member_labels=self._current_scope_expected_member_labels(),
            selected_test_name=self._selected_test_name(),
            selected_test_ready=self._selected_test_ready(),
            selected_test_invalid=self._selected_test_has_invalid_members(),
            selected_test_running=self._selected_test_running(),
            selected_test_runtime_block_reason=self._test_runtime_block_reason(),
        )

    def _manual_duty_action_state(self, targets: List[str]) -> HostActionAccessState:
        """
        NAME
            _manual_duty_action_state - Return shared popup-entry policy for manual-duty actions.
        """
        return resolve_manual_duty_action_state(
            tcp_connected=bool(self._tcp_connected),
            runtime_state_seen=bool(self.__dict__.get("_runtime_state_seen", False)),
            stale_state=bool(self.__dict__.get("_state_stale", False)),
            robot_estopped=bool(self.__dict__.get("_robot_estopped_known", False)),
            robot_enabled=bool(self.__dict__.get("_robot_enabled_known", True)),
            tracker_pending=bool(self._tracker.is_pending()),
            transition_pending=self._scope_transition_pending(),
            target_labels=list(targets or []),
            runtime_state_by_label=dict(self.__dict__.get("_latest_runtime_devices", {})),
            controlled_lifecycle_active=self.__dict__.get("_controlled_lifecycle_active_known") is True,
            runtime_groups=self._latest_runtime_state_payload_groups(),
        )

    def _active_group_edit_action_state(self) -> HostActionAccessState:
        """
        NAME
            _active_group_edit_action_state - Return shared edit policy for active-group membership actions.
        """
        return resolve_active_group_edit_action_state(
            tcp_connected=bool(self._tcp_connected),
            tracker_pending=bool(self._tracker.is_pending()),
            controlled_lifecycle_active=self.__dict__.get("_controlled_lifecycle_active_known") is True,
            scope_control_state=self._scope_control_state(),
        )

    def _override_action_state(self) -> HostActionAccessState:
        """
        NAME
            _override_action_state - Return shared entry policy for live override actions.
        """
        return resolve_override_action_state(
            tcp_connected=bool(self._tcp_connected),
            tracker_pending=bool(self._tracker.is_pending()),
        )

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
        return resolve_scope_activation_notice(
            scope_kind=self._runnable_scope_kind(),
            local_selected_profile=self._selected_profile_name(),
            local_profile_required=self.__dict__.get("_profile_box") is not None,
            robot_mode=str(self.__dict__.get("_robot_mode_known", "") or "").strip().lower(),
        )

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
        self._pending_robot_profile_selection = name
        if name == PROFILE_NONE:
            return
        self._maybe_send_pending_robot_profile_selection()

    def _can_send_profile_selection_now(self) -> bool:
        """
        NAME
            _can_send_profile_selection_now - Return whether the UI can send selectProfile immediately.
        """
        if not self._tcp_connected or not self._handshake_done:
            return False
        tracker = getattr(self, "_tracker", None)
        if tracker is not None and tracker.is_pending():
            return False
        return True

    def _maybe_send_pending_robot_profile_selection(self) -> bool:
        """
        NAME
            _maybe_send_pending_robot_profile_selection - Flush one deferred selectProfile request when transport is ready.
        """
        pending_name = _normalize_profile_name(
            self.__dict__.get("_pending_robot_profile_selection", PROFILE_NONE)
        )
        if pending_name == PROFILE_NONE:
            return False
        if not self._can_send_profile_selection_now():
            return False
        if _normalize_profile_name(self.__dict__.get("_robot_selected_profile", PROFILE_NONE)) == pending_name:
            self._pending_robot_profile_selection = PROFILE_NONE
            return False
        seq = send_command(self._session, "selectProfile", {"name": pending_name})
        if seq is None:
            return False
        self._last_sent_seq = seq
        self._tracker.start("selectProfile", {"name": pending_name}, seq, now=time.time())
        self._pending_robot_profile_selection = PROFILE_NONE
        return True

    def _selected_profile_name(self) -> str:
        """
        NAME
            _selected_profile_name - Return the current UI-selected profile or PROFILE_NONE.
        """
        profile_box = self.__dict__.get("_profile_box")
        if profile_box is None:
            return PROFILE_NONE
        return _normalize_profile_name(profile_box.get())

    def _ui_context_state(self) -> UiContextState:
        """
        NAME
            _ui_context_state - Return the shared UI context snapshot for current host/robot state.
        """
        owner_mode = str(self.__dict__.get("_group_owner_mode", "") or "").strip().lower()
        scope_kind = RUNNABLE_SCOPE_KIND_MANUAL
        if owner_mode == GROUP_SOURCE_SELECTED_TEST:
            scope_kind = RUNNABLE_SCOPE_KIND_SELECTED_TEST
        elif owner_mode == GROUP_SOURCE_MANUAL:
            scope_kind = RUNNABLE_SCOPE_KIND_MANUAL
        elif self._scope_context_kind() == GROUP_SOURCE_SELECTED_TEST:
            scope_kind = RUNNABLE_SCOPE_KIND_SELECTED_TEST
        selected_test_var = self.__dict__.get("_selected_test_var")
        selected_test_name = NT_VALUE_EMPTY
        if selected_test_var is not None and hasattr(selected_test_var, "get"):
            selected_test_name = str(selected_test_var.get() or "").strip()
        return resolve_ui_context_state(
            local_selected_profile=self._selected_profile_name(),
            robot_selected_profile=self.__dict__.get("_robot_selected_profile", PROFILE_NONE),
            robot_active_runtime_profile=self.__dict__.get(
                "_robot_active_runtime_profile", PROFILE_NONE
            ),
            selected_test_name=selected_test_name,
            scope_kind=scope_kind,
            transport_connected=bool(self.__dict__.get("_tcp_connected", True)),
            handshake_ready=bool(self.__dict__.get("_handshake_done", False)),
            has_robot_runtime_state=bool(self.__dict__.get("_runtime_state_seen", False)),
        )

    def _diagnostic_profile_state(self) -> DiagnosticProfileState:
        """
        NAME
            _diagnostic_profile_state - Return the shared diagnostic profile context state.
        """
        context = self._ui_context_state()
        return resolve_diagnostic_profile_state(
            context.local_selected_profile,
            context.robot_selected_profile,
            context.robot_active_runtime_profile,
            local_profile_required=self.__dict__.get("_profile_box") is not None,
        )

    def _runnable_scope_kind(self) -> str:
        """
        NAME
            _runnable_scope_kind - Return normalized shared runnable-scope kind text.
        """
        return self._ui_context_state().scope_kind

    def _runnable_scope_state(self, stale_state: bool) -> RunnableScopeState:
        """
        NAME
            _runnable_scope_state - Return the shared runnable-scope decision state.
        """
        context = self._ui_context_state()
        return resolve_runnable_scope_state(
            scope_kind=context.scope_kind,
            local_selected_profile=context.local_selected_profile,
            local_profile_required=self.__dict__.get("_profile_box") is not None,
            tcp_connected=context.transport_connected,
            runtime_state_seen=context.has_robot_runtime_state,
            stale_state=bool(stale_state),
            robot_enabled=bool(self.__dict__.get("_robot_enabled_known", True)),
            robot_estopped=bool(self.__dict__.get("_robot_estopped_known", False)),
            robot_mode=str(self.__dict__.get("_robot_mode_known", "") or "").strip().lower(),
            manual_group_empty=self._manual_active_group_is_empty(),
            scope_active=self._scope_is_currently_active(),
            transition_pending=self._scope_transition_pending(),
        )

    def _scope_transition_pending(self) -> bool:
        """
        NAME
            _scope_transition_pending - Return whether a scope/runtime transition is awaiting runtime confirmation.
        """
        pending = (
            self.__dict__.get("_pending_runtime_active_expected") is not None
            or self.__dict__.get("_pending_controlled_lifecycle_expected") is not None
            or bool(self.__dict__.get("_pending_scope_member_labels_expected", tuple()))
        )
        if not pending:
            return False
        started_at = float(self.__dict__.get("_scope_transition_started_at", 0.0) or 0.0)
        if started_at <= 0.0:
            self._scope_transition_started_at = time.time()
            return True
        if (time.time() - started_at) > SCOPE_TRANSITION_WAIT_TIMEOUT_SEC:
            self._clear_scope_transition_wait()
            return False
        return True

    def _begin_scope_transition_wait(
        self,
        *,
        runtime_active_expected: Optional[bool] = None,
        controlled_lifecycle_expected: Optional[bool] = None,
        expected_member_labels: Optional[List[str]] = None,
    ) -> None:
        """
        NAME
            _begin_scope_transition_wait - Record one accepted command that still needs a confirming runtime snapshot.
        """
        if runtime_active_expected is not None:
            self._pending_runtime_active_expected = bool(runtime_active_expected)
        if controlled_lifecycle_expected is not None:
            self._pending_controlled_lifecycle_expected = bool(controlled_lifecycle_expected)
        if expected_member_labels is not None:
            self._pending_scope_member_labels_expected = tuple(
                sorted(
                    {
                        str(label or NT_VALUE_EMPTY).strip().lower()
                        for label in expected_member_labels
                        if str(label or NT_VALUE_EMPTY).strip()
                    }
                )
            )
        if self._scope_transition_pending():
            self._scope_transition_started_at = time.time()

    def _clear_scope_transition_wait(self) -> None:
        """
        NAME
            _clear_scope_transition_wait - Clear all pending scope/runtime transition wait state.
        """
        self._pending_runtime_active_expected = None
        self._pending_controlled_lifecycle_expected = None
        self._pending_scope_member_labels_expected = tuple()
        self._scope_transition_started_at = 0.0

    def _current_scope_expected_member_labels(self) -> List[str]:
        """
        NAME
            _current_scope_expected_member_labels - Return expected device labels for the current scope activation.
        """
        if self._scope_context_kind() == GROUP_SOURCE_SELECTED_TEST:
            return [
                str(row.get("label", "")).strip()
                for row in self.__dict__.get("_tests_active_group_rows", [])
                if isinstance(row, dict) and bool(row.get("enabled", True)) and str(row.get("label", "")).strip()
            ]
        return [
            str(row.get("label", "")).strip()
            for row in self._runtime_active_group_members()
            if isinstance(row, dict) and bool(row.get("enabled", True)) and str(row.get("label", "")).strip()
        ]

    def _runtime_device_confirms_scope_member(
        self,
        runtime_device: Optional[Dict[str, Any]],
    ) -> bool:
        """
        NAME
            _runtime_device_confirms_scope_member - Return whether one runtime device row confirms active-scope membership.
        """
        if not isinstance(runtime_device, dict):
            return False
        lifecycle_state = str(runtime_device.get("lifecycleState", NT_VALUE_EMPTY)).strip().lower()
        if lifecycle_state == "controlled-active":
            return True
        if bool(runtime_device.get("testable", False)):
            return True
        if bool(runtime_device.get("instantiated", False)):
            return True
        active_group_label = str(runtime_device.get("activeGroupLabel", NT_VALUE_EMPTY)).strip().lower()
        return active_group_label == GROUP_ACTIVE_NAME

    def _maybe_complete_scope_transition_wait(self, payload: Dict[str, Any]) -> None:
        """
        NAME
            _maybe_complete_scope_transition_wait - Clear transition wait entries once runtime state confirms them.
        """
        runtime_active_expected = self.__dict__.get("_pending_runtime_active_expected")
        if runtime_active_expected is not None:
            runtime_active = payload.get("runtimeActive")
            if isinstance(runtime_active, bool) and runtime_active == bool(runtime_active_expected):
                self._pending_runtime_active_expected = None
        controlled_expected = self.__dict__.get("_pending_controlled_lifecycle_expected")
        if controlled_expected is not None:
            controlled_active = payload.get("controlledLifecycleActive")
            if isinstance(controlled_active, bool) and controlled_active == bool(controlled_expected):
                self._pending_controlled_lifecycle_expected = None
        expected_labels = tuple(self.__dict__.get("_pending_scope_member_labels_expected", tuple()))
        if expected_labels:
            latest_runtime_devices = self.__dict__.get("_latest_runtime_devices", {})
            if isinstance(latest_runtime_devices, dict) and all(
                self._runtime_device_confirms_scope_member(
                    latest_runtime_devices.get(label_key)
                )
                for label_key in expected_labels
            ):
                self._pending_scope_member_labels_expected = tuple()
        current_scope_labels = tuple(
            sorted(
                {
                    str(label or NT_VALUE_EMPTY).strip().lower()
                    for label in self._current_scope_expected_member_labels()
                    if str(label or NT_VALUE_EMPTY).strip()
                }
            )
        )
        if current_scope_labels:
            latest_runtime_devices = self.__dict__.get("_latest_runtime_devices", {})
            current_scope_confirmed = isinstance(latest_runtime_devices, dict) and all(
                self._runtime_device_confirms_scope_member(
                    latest_runtime_devices.get(label_key)
                )
                for label_key in current_scope_labels
            )
            if current_scope_confirmed and self._scope_is_currently_active():
                self._pending_runtime_active_expected = None
                self._pending_controlled_lifecycle_expected = None
                self._pending_scope_member_labels_expected = tuple()
        if (
            self.__dict__.get("_pending_runtime_active_expected") is None
            and self.__dict__.get("_pending_controlled_lifecycle_expected") is None
            and not self.__dict__.get("_pending_scope_member_labels_expected", tuple())
        ):
            self._clear_scope_transition_wait()

    def _diagnostic_profile_context_name(self) -> str:
        """
        NAME
            _diagnostic_profile_context_name - Return the profile context used by diagnostics views.

        DESCRIPTION
            Diagnostics remain blank until the operator selects a local profile.
            After that, prefer the robot's active runtime profile, then the
            robot's selected profile, then the local UI selection.
        """
        return self._diagnostic_profile_state().effective_profile

    def _topology_scene_state(self) -> TopologySceneState:
        """
        NAME
            _topology_scene_state - Return the shared topology scene decision for live topology consumers.
        """
        profile_state = self._diagnostic_profile_state()
        return resolve_topology_scene_state(
            effective_profile=profile_state.effective_profile,
            show_blank_profile_state=profile_state.show_blank_profile_state,
            blank_reason=profile_state.blank_reason,
            current_profile_name=self.__dict__.get("_last_profile_context", PROFILE_NONE),
        )

    def _sync_diagnostic_profile_context(self, reload_views: bool) -> None:
        """
        NAME
            _sync_diagnostic_profile_context - Re-anchor diagnostics surfaces to one profile context.
        """
        state = self._diagnostic_profile_state()
        topology_scene_state = self._topology_scene_state()
        name = state.effective_profile
        self._refresh_profile_devices(name)
        if reload_views and name != self._last_profile_context:
            for live_view in self._iter_live_views():
                if hasattr(live_view, "apply_topology_scene_state"):
                    live_view.apply_topology_scene_state(topology_scene_state)
                elif hasattr(live_view, "apply_diagnostic_profile_state"):
                    live_view.apply_diagnostic_profile_state(state)
                else:
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
        available_profiles = tuple(str(value) for value in self._profile_box.cget("values"))
        if name not in available_profiles:
            return
        self._profile_box.set(name)
        self._last_selected_profile = name
        self._apply_profile_selection(name, reload_views=reload_views)

    def _maybe_prompt_host_profile_context_sync(self) -> None:
        """
        NAME
            _maybe_prompt_host_profile_context_sync - Offer to align local UI context to the robot-selected profile.
        """
        if bool(self.__dict__.get("_suppress_host_profile_context_sync", HOST_PROFILE_SYNC_NOT_SUPPRESSED)):
            return
        if _normalize_profile_name(self.__dict__.get("_pending_robot_profile_selection", PROFILE_NONE)) != PROFILE_NONE:
            return
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
            messagebox.showwarning(
                PROFILE_CONTEXT_MISSING_LOCAL_TITLE,
                PROFILE_CONTEXT_MISSING_LOCAL_FMT.format(
                    robot=robot_selected,
                    host=local_selected,
                ),
                parent=self,
            )
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

    def _uses_noncanonical_local_config_session(self) -> bool:
        """
        NAME
            _uses_noncanonical_local_config_session - Return whether the UI is bound to a non-canonical local config session.
        """
        return bool(self.__dict__.get("_config_session_in_memory_only", False)) or isinstance(
            self.__dict__.get("_local_profiles_payload_override"),
            dict,
        ) or self.__dict__.get("_config_path_override") is not None

    def _local_runnable_test_names(self, profile_name: object) -> List[str]:
        """
        NAME
            _local_runnable_test_names - Resolve runnable test names for one profile from the active local config session.
        """
        name = _normalize_profile_name(profile_name)
        if name == PROFILE_NONE:
            return []
        if not self._uses_noncanonical_local_config_session():
            try:
                return LocalConfigQueryService().test_names_for_profile(name)
            except Exception:
                return []
        payload = self._current_materialized_profiles_payload()
        if not isinstance(payload.get(KEY_DSL_TESTS), dict):
            return []
        return resolve_runnable_profile_test_names(payload, name)

    def _local_test_library_state(self, profile_name: object) -> Dict[str, Any]:
        """
        NAME
            _local_test_library_state - Resolve Tests-tab library state for the active local config session.
        """
        selected_profile = _normalize_profile_name(profile_name)
        if not self._uses_noncanonical_local_config_session():
            query = LocalConfigQueryService()
            return {
                "global_names": list_external_library_test_names(),
                "global_runnable_map": (
                    query.external_library_test_runnable_map(selected_profile)
                    if selected_profile != PROFILE_NONE
                    else {}
                ),
                "config_names": query.global_test_names(),
                "profile_names": (
                    query.profile_test_names(selected_profile)
                    if selected_profile != PROFILE_NONE
                    else []
                ),
                "config_runnable_map": (
                    query.config_library_test_runnable_map(selected_profile)
                    if selected_profile != PROFILE_NONE
                    else {}
                ),
                "runnable_map": (
                    query.profile_test_runnable_map(selected_profile)
                    if selected_profile != PROFILE_NONE
                    else {}
                ),
                "test_profile_devices": (
                    query.profile_device_catalog(selected_profile)
                    if selected_profile != PROFILE_NONE
                    else {}
                ),
                "profile_set_name": (
                    query.profile_test_set_name(selected_profile)
                    if selected_profile != PROFILE_NONE
                    else ""
                ),
            }
        payload = self._current_materialized_profiles_payload()
        dsl_present = isinstance(payload.get(KEY_DSL_TESTS), dict)
        return {
            "global_names": list_external_library_test_names(),
            "global_runnable_map": (
                external_library_test_runnable_map(payload, selected_profile)
                if selected_profile != PROFILE_NONE and dsl_present
                else {}
            ),
            "config_names": resolve_global_library_test_names(payload) if dsl_present else [],
            "profile_names": (
                resolve_profile_test_names(payload, selected_profile)
                if selected_profile != PROFILE_NONE and dsl_present
                else []
            ),
            "config_runnable_map": (
                config_library_test_runnable_map(payload, selected_profile)
                if selected_profile != PROFILE_NONE and dsl_present
                else {}
            ),
            "runnable_map": (
                profile_test_runnable_map(payload, selected_profile)
                if selected_profile != PROFILE_NONE and dsl_present
                else {}
            ),
            "test_profile_devices": (
                device_catalog(payload, selected_profile)
                if selected_profile != PROFILE_NONE
                else {}
            ),
            "profile_set_name": (
                resolve_profile_test_set_name(payload, selected_profile)
                if selected_profile != PROFILE_NONE and dsl_present
                else ""
            ),
        }

    def _pending_profile_device_map(self, profile_name: object) -> Dict[str, Dict[str, Any]]:
        """
        NAME
            _pending_profile_device_map - Return pending in-memory device definitions for one profile.
        """
        name = _normalize_profile_name(profile_name)
        pending = self.__dict__.get("_pending_profile_device_definitions", {})
        if not isinstance(pending, dict) or not name or name == PROFILE_NONE:
            return {}
        profile_pending = pending.get(name, {})
        if not isinstance(profile_pending, dict):
            return {}
        return {
            str(label).strip().lower(): dict(device)
            for label, device in profile_pending.items()
            if isinstance(label, str) and label.strip() and isinstance(device, dict)
        }

    def _overlay_pending_profile_device_definitions(
        self,
        profile_name: object,
        mapping: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        """
        NAME
            _overlay_pending_profile_device_definitions - Overlay one profile's pending in-memory device definitions.
        """
        merged = {
            str(label).strip().lower(): dict(device)
            for label, device in mapping.items()
            if isinstance(label, str) and label.strip() and isinstance(device, dict)
        }
        merged.update(self._pending_profile_device_map(profile_name))
        return merged

    def _parse_visibility_identity_triplet(
        self, identity_text: object
    ) -> Optional[Tuple[int, int, int]]:
        """
        NAME
            _parse_visibility_identity_triplet - Parse one visibility identity key into manufacturer, device type, and id.
        """
        clean_identity = str(identity_text or NT_VALUE_EMPTY).strip()
        if not clean_identity:
            return None
        parts = [part.strip() for part in clean_identity.split(VIS_IDENTITY_SEPARATOR)]
        if len(parts) < 3:
            return None
        try:
            return (int(parts[0]), int(parts[1]), int(parts[2]))
        except Exception:
            return None

    def _identity_triplet_for_visibility_item(
        self,
        label: str,
        identity_text: str,
    ) -> Optional[Tuple[int, int, int]]:
        """
        NAME
            _identity_triplet_for_visibility_item - Resolve one visibility row to manufacturer, device type, and id.
        """
        parsed = self._parse_visibility_identity_triplet(identity_text)
        if parsed is not None:
            return parsed
        passive_device = resolve_passive_visibility_device_record(
            label=label,
            passive_result=self.__dict__.get("_latest_passive_result"),
            visibility_identity_text=identity_text,
        )
        if passive_device is None:
            passive_device = resolve_passive_visibility_device_record(
                label=label,
                passive_result=self._current_passive_result(),
                visibility_identity_text=identity_text,
            )
        if passive_device is None:
            return None
        identity = getattr(passive_device, "identity", None)
        if identity is None:
            return None
        try:
            return (
                int(getattr(identity, "manufacturer")),
                int(getattr(identity, "device_type")),
                int(getattr(identity, "device_id")),
            )
        except Exception:
            return None

    def _logical_type_for_passive_guess(
        self,
        device_type: int,
        passive_type_name: str,
    ) -> str:
        """
        NAME
            _logical_type_for_passive_guess - Resolve one conservative logical device type for a passive unrecognized row.
        """
        clean_name = str(passive_type_name or VIS_MODEL_EMPTY).strip().lower()
        if device_type == VIS_DEVICE_TYPE_CAN_MOTOR:
            return TYPE_MOTOR
        if device_type == VIS_DEVICE_TYPE_CAN_ENCODER:
            return TYPE_ENCODER_EXTERNAL
        if (
            VIS_PASSIVE_TYPE_TOKEN_SPARK in clean_name
            or VIS_PASSIVE_TYPE_TOKEN_TALON in clean_name
            or VIS_PASSIVE_TYPE_TOKEN_FALCON in clean_name
            or VIS_PASSIVE_TYPE_TOKEN_KRAKEN in clean_name
            or VIS_PASSIVE_TYPE_TOKEN_MOTOR in clean_name
        ):
            return TYPE_MOTOR
        if (
            VIS_PASSIVE_TYPE_TOKEN_CANCODER in clean_name
            or VIS_PASSIVE_TYPE_TOKEN_ENCODER in clean_name
        ):
            return TYPE_ENCODER_EXTERNAL
        return VIS_LOGICAL_TYPE_EMPTY

    def _all_known_config_device_labels(self) -> List[str]:
        """
        NAME
            _all_known_config_device_labels - Return current canonical plus pending device labels.
        """
        labels: List[str] = []
        seen: set[str] = set()
        try:
            payload = self._load_local_profiles_payload()
        except Exception:
            payload = {}
        devices = payload.get(KEY_DEVICES) if isinstance(payload, dict) else []
        if isinstance(devices, list):
            for entry in devices:
                if not isinstance(entry, dict):
                    continue
                label = str(entry.get(PROFILE_KEY_LABEL, NT_VALUE_EMPTY)).strip()
                label_key = label.lower()
                if not label or label_key in seen:
                    continue
                seen.add(label_key)
                labels.append(label)
        pending = self.__dict__.get("_pending_profile_device_definitions", {})
        if isinstance(pending, dict):
            for profile_pending in pending.values():
                if not isinstance(profile_pending, dict):
                    continue
                for entry in profile_pending.values():
                    if not isinstance(entry, dict):
                        continue
                    label = str(entry.get(PROFILE_KEY_LABEL, NT_VALUE_EMPTY)).strip()
                    label_key = label.lower()
                    if not label or label_key in seen:
                        continue
                    seen.add(label_key)
                    labels.append(label)
        return labels

    def _unique_guessed_device_label(self, base_label: object) -> str:
        """
        NAME
            _unique_guessed_device_label - Return a non-conflicting label for one guessed device definition.
        """
        clean_label = str(base_label or NT_VALUE_EMPTY).strip()
        if not clean_label:
            clean_label = VIS_UNRECOGNIZED_SECTION_LABEL
        existing = {str(label).strip().lower() for label in self._all_known_config_device_labels()}
        if clean_label.lower() not in existing:
            return clean_label
        suffix = VIS_LABEL_SUFFIX_START
        while True:
            candidate = (
                clean_label
                + VIS_LABEL_SUFFIX_SEPARATOR
                + str(suffix)
            )
            if candidate.lower() not in existing:
                return candidate
            suffix += 1

    def _guessed_device_label(self, base_label: object) -> str:
        """
        NAME
            _guessed_device_label - Return the initial guessed label for one discovered device before conflict resolution.
        """
        clean_label = str(base_label or NT_VALUE_EMPTY).strip()
        if not clean_label:
            return VIS_UNRECOGNIZED_SECTION_LABEL
        return clean_label

    def _resolve_discovered_device_label_conflict(
        self,
        device_definition: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        NAME
            _resolve_discovered_device_label_conflict - Resolve one discovered-device label collision by reusing, renaming, or cancelling.
        """
        label = str(device_definition.get(PROFILE_KEY_LABEL, NT_VALUE_EMPTY)).strip()
        if not label:
            return None
        existing_labels = {
            str(existing_label).strip().lower(): str(existing_label).strip()
            for existing_label in self._all_known_config_device_labels()
            if str(existing_label).strip()
        }
        existing_label = existing_labels.get(label.lower())
        if not existing_label:
            return dict(device_definition)
        choice = messagebox.askyesnocancel(
            CONFIG_LABEL_CONFLICT_TITLE,
            CONFIG_LABEL_CONFLICT_PROMPT_FMT.format(label=label),
            parent=self,
            default=messagebox.CANCEL,
        )
        if choice is None:
            self._append_output(CONFIG_LABEL_RENAME_CANCELLED)
            return None
        if choice:
            resolved = dict(device_definition)
            resolved[PROFILE_KEY_LABEL] = existing_label
            return resolved
        renamed = simpledialog.askstring(
            CONFIG_LABEL_RENAME_TITLE,
            CONFIG_LABEL_RENAME_PROMPT_FMT.format(label=label),
            parent=self,
            initialvalue=self._unique_guessed_device_label(label),
        )
        if renamed is None:
            self._append_output(CONFIG_LABEL_RENAME_CANCELLED)
            return None
        renamed_text = str(renamed).strip()
        if not renamed_text:
            self._append_output(CONFIG_LABEL_RENAME_EMPTY)
            return None
        if renamed_text.lower() in existing_labels:
            self._append_output(CONFIG_LABEL_RENAME_DUPLICATE)
            return None
        resolved = dict(device_definition)
        resolved[PROFILE_KEY_LABEL] = renamed_text
        return resolved

    def _build_pending_unrecognized_device_definition(
        self,
        label: str,
        identity: Tuple[int, int, int],
    ) -> Dict[str, Any]:
        """
        NAME
            _build_pending_unrecognized_device_definition - Build one in-memory device definition proposal from one passive unrecognized row.
        """
        manufacturer, device_type, device_id = identity
        passive_result = self._current_passive_result()
        passive_rows = index_run_result_by_identity(passive_result)
        passive_device = passive_rows.get(identity)
        passive_type_name = str(
            getattr(passive_device, "device_type_name", VIS_MODEL_EMPTY) or VIS_MODEL_EMPTY
        ).strip()
        resolved_label = self._guessed_device_label(label)
        logical_type = self._logical_type_for_passive_guess(device_type, passive_type_name)
        tags = [VIS_TAG_GUESSED_LABEL]
        if passive_type_name:
            tags.append(VIS_TAG_GUESSED_MODEL)
        if logical_type:
            tags.append(VIS_TAG_GUESSED_TYPE)
        return {
            PROFILE_KEY_LABEL: resolved_label,
            KEY_INTERFACE: INTERFACE_CAN,
            KEY_MANUFACTURER: manufacturer,
            KEY_DEVICE_TYPE: device_type,
            KEY_ID: device_id,
            KEY_MODEL: passive_type_name or VIS_MODEL_EMPTY,
            KEY_TYPE: logical_type or VIS_LOGICAL_TYPE_EMPTY,
            KEY_TAGS: tags,
        }

    def _refresh_profile_devices(self, profile_name: object) -> None:
        """
        NAME
            _refresh_profile_devices - Refresh label->device mapping for the profile.
        """
        def _catalog_from_payload(
            payload: Dict[str, Any],
            selected_profile_name: str,
        ) -> Dict[str, Dict[str, Any]]:
            if not isinstance(payload, dict) or not selected_profile_name:
                return {}
            devices_section = payload.get(KEY_DEVICES)
            profiles_section = payload.get(KEY_PROFILES)
            if not isinstance(devices_section, list) or not isinstance(profiles_section, dict):
                return {}
            profile_payload = profiles_section.get(selected_profile_name)
            if not isinstance(profile_payload, dict):
                return {}
            selected_labels = profile_payload.get(KEY_PROFILE_DEVICES)
            if not isinstance(selected_labels, list):
                return {}
            labels_lower = {
                str(label).strip().lower()
                for label in selected_labels
                if isinstance(label, str) and str(label).strip()
            }
            mapping: Dict[str, Dict[str, Any]] = {}
            for device in devices_section:
                if not isinstance(device, dict):
                    continue
                label = str(device.get(DEVICE_KEY_LABEL, NT_VALUE_EMPTY)).strip()
                if not label:
                    continue
                label_key = label.lower()
                if label_key not in labels_lower:
                    continue
                mapping[label_key] = dict(device)
            return mapping

        def _catalog_fingerprint(mapping: Dict[str, Dict[str, Any]]) -> Tuple[Tuple[Any, ...], ...]:
            rows: List[Tuple[Any, ...]] = []
            for key, device in sorted(mapping.items()):
                if not isinstance(device, dict):
                    continue
                rows.append(
                    (
                        str(key).strip().lower(),
                        str(device.get(DEVICE_KEY_LABEL, NT_VALUE_EMPTY)).strip(),
                        int(device.get(KEY_MANUFACTURER, 0) or 0),
                        int(device.get(KEY_DEVICE_TYPE, 0) or 0),
                        int(device.get(KEY_ID, 0) or 0),
                    )
                )
            return tuple(rows)

        name = _normalize_profile_name(profile_name)
        self._refresh_profile_active_group_members(name)
        previous_profile_name = _normalize_profile_name(
            self.__dict__.get("_evidence_enrichment_profile_name", PROFILE_NONE)
        )
        previous_fingerprint = self.__dict__.get(
            "_evidence_enrichment_profile_fingerprint", ()
        )
        if name == PROFILE_NONE:
            self._profile_devices = {}
            if previous_profile_name != PROFILE_NONE:
                self._evidence_enrichment_snapshot = default_enrichment_run_snapshot()
            self._evidence_enrichment_profile_name = PROFILE_NONE
            self._evidence_enrichment_profile_fingerprint = ()
            self._set_evidence_engine_section_label(SECTION_PROFILE_INVENTORY, ENGINE_LABEL_NEW)
            self._set_evidence_engine_section_label(SECTION_ENRICHMENT, ENGINE_LABEL_NEW)
            self._set_evidence_engine_section_label(SECTION_TOPOLOGY_VIEW, ENGINE_LABEL_NEW)
            self._set_evidence_engine_section_label(SECTION_INTERPRETATION, ENGINE_LABEL_NEW)
            if self._visibility_provider is not None:
                if hasattr(self._visibility_provider, "set_allow_suggested_labels_for_unexpected"):
                    self._visibility_provider.set_allow_suggested_labels_for_unexpected(False)
                self._visibility_provider.set_expected_devices([])
            return
        mapping: Dict[str, Dict[str, Any]] = {}
        loaded_from_passive_discovery = False
        try:
            mapping = _catalog_from_payload(self._current_materialized_profiles_payload(), name)
        except Exception:
            mapping = {}
        try:
            if not mapping:
                mapping = load_profile_device_catalog(name)
                loaded_from_passive_discovery = True
        except Exception:
            try:
                if mapping:
                    devices = list(mapping.values())
                    _expected = set()
                else:
                    devices, _expected = get_profile(name)
            except Exception:
                self._profile_devices = {}
                if previous_profile_name != name:
                    self._evidence_enrichment_snapshot = default_enrichment_run_snapshot()
                self._evidence_enrichment_profile_name = name
                self._evidence_enrichment_profile_fingerprint = ()
                self._set_evidence_engine_section_label(SECTION_PROFILE_INVENTORY, ENGINE_LABEL_LEGACY)
                if self._visibility_provider is not None:
                    if hasattr(self._visibility_provider, "set_allow_suggested_labels_for_unexpected"):
                        self._visibility_provider.set_allow_suggested_labels_for_unexpected(True)
                    self._visibility_provider.set_expected_devices([])
                return
            if not mapping:
                for device in devices:
                    if not isinstance(device, dict):
                        continue
                    label = str(device.get(DEVICE_KEY_LABEL, NT_VALUE_EMPTY)).strip()
                    if not label:
                        continue
                    mapping[label.lower()] = device
        self._profile_devices = self._overlay_pending_profile_device_definitions(name, mapping)
        current_fingerprint = _catalog_fingerprint(self._profile_devices)
        if previous_profile_name != name or previous_fingerprint != current_fingerprint:
            self._evidence_enrichment_snapshot = default_enrichment_run_snapshot()
        self._evidence_enrichment_profile_name = name
        self._evidence_enrichment_profile_fingerprint = current_fingerprint
        self._set_evidence_engine_section_label(
            SECTION_PROFILE_INVENTORY,
            ENGINE_LABEL_NEW if loaded_from_passive_discovery else ENGINE_LABEL_LEGACY,
        )
        if loaded_from_passive_discovery:
            self._set_evidence_engine_section_label(
                SECTION_PRESENCE_CHECK,
                ENGINE_LABEL_NEW,
            )
            self._set_evidence_engine_section_label(
                SECTION_CONSOLE,
                ENGINE_LABEL_NEW,
            )
            self._set_evidence_engine_section_label(
                SECTION_PROBE,
                ENGINE_LABEL_NEW,
            )
            self._set_evidence_engine_section_label(
                SECTION_MANUAL,
                ENGINE_LABEL_NEW,
            )
            self._set_evidence_engine_section_label(
                SECTION_ENRICHMENT,
                ENGINE_LABEL_NEW,
            )
            self._set_evidence_engine_section_label(
                SECTION_TOPOLOGY_VIEW,
                ENGINE_LABEL_NEW,
            )
            self._set_evidence_engine_section_label(
                SECTION_INTERPRETATION,
                ENGINE_LABEL_NEW,
            )
        if self._visibility_provider is not None:
            if hasattr(self._visibility_provider, "set_allow_suggested_labels_for_unexpected"):
                self._visibility_provider.set_allow_suggested_labels_for_unexpected(True)
            self._visibility_provider.set_expected_devices(
                _build_visibility_expected_devices(list(self._profile_devices.values()))
            )
            self._visibility_last_update = 0.0

    def _refresh_profile_active_group_members(self, profile_name: object) -> None:
        """
        NAME
            _refresh_profile_active_group_members - Cache configured active-group members for the selected profile.

        DESCRIPTION
            Runtime Activate rebuilds the selected profile before activating
            active-group. A missing runtime group snapshot is therefore not the
            same thing as an empty configured active-group.
        """
        name = _normalize_profile_name(profile_name)
        if name == PROFILE_NONE:
            self._profile_active_group_member_labels = tuple()
            return
        labels: Tuple[str, ...] = tuple()
        try:
            groups = parse_bridge_groups(self._load_local_profiles_payload(), name)
            group = find_group_by_name(groups, GROUP_ACTIVE_NAME)
            if group is not None:
                labels = tuple(group_member_labels(group, enabled_only=True))
        except Exception:
            labels = tuple()
        self._profile_active_group_member_labels = labels
        for live_view in self._iter_live_views():
            if hasattr(live_view, "set_configured_active_group_member_labels"):
                live_view.set_configured_active_group_member_labels(list(labels))

    def _set_evidence_engine_section_label(self, section_key: str, label: str) -> None:
        """
        NAME
            _set_evidence_engine_section_label - Update one Evidence-tab engine section label and refresh the banner.
        """
        engine_status = getattr(self, "_evidence_engine_status", None)
        if not isinstance(engine_status, dict):
            return
        if not isinstance(engine_status.get("sections"), dict):
            engine_status["sections"] = {}
        engine_status["sections"][section_key] = label
        normalize_evidence_engine_status(engine_status)
        banner_var = getattr(self, "_evidence_engine_banner_var", None)
        if banner_var is not None:
            banner_var.set(evidence_engine_banner_text(engine_status))
        live_view = self.__dict__.get("_evidence_live_view")
        if live_view is not None:
            live_view.set_title_text(
                evidence_overall_title(
                    EVIDENCE_TITLE_TEXT,
                    engine_status,
                )
            )

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
        live_view = self.__dict__.get("_live_view")
        visibility_live_view = self.__dict__.get("_visibility_live_view")
        evidence_live_view = self.__dict__.get("_evidence_live_view")
        if live_view is not None:
            views.append(live_view)
        if visibility_live_view is not None:
            views.append(visibility_live_view)
        if evidence_live_view is not None:
            views.append(evidence_live_view)
        return views

    def _sync_live_view_action_states(self) -> None:
        """
        NAME
            _sync_live_view_action_states - Push shared action-access states into all topology views.
        """
        if "_tracker" not in self.__dict__ or "_tcp_connected" not in self.__dict__:
            return
        active_group_state = self._active_group_edit_action_state()
        override_state = self._override_action_state()
        for live_view in self._iter_live_views():
            if hasattr(live_view, "set_active_group_edit_action_state"):
                live_view.set_active_group_edit_action_state(active_group_state)
            if hasattr(live_view, "set_override_action_state"):
                live_view.set_override_action_state(override_state)

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
        self._pending_runtime_active_expected = None
        self._pending_controlled_lifecycle_expected = None
        self._pending_scope_member_labels_expected = tuple()
        self._scope_transition_started_at = 0.0
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
        self._evidence_eval_cursor_class_index = 0
        self._evidence_eval_cursor_device_index = 0
        self._evidence_eval_generation = NT_VALUE_EMPTY
        self._evidence_eval_cache = {}
        self._evidence_eval_dirty_labels = {}
        self._evidence_eval_source_fingerprints = {}
        self._manual_motion_checks = {}
        self._manual_test_observations = {}
        self._remembered_manual_active_group_members = []
        self._tests_active_group_rows = []
        self._tests_active_group_membership_key = tuple()
        self._tests_active_group_loaded_to_robot = None
        self._group_owner_mode = GROUP_SOURCE_MANUAL
        self._manual_duty_last_sent_value = None
        self._manual_duty_last_sent_at = 0.0
        self._manual_duty_pending_after = None
        self._manual_duty_block_reason = MANUAL_DUTY_BLOCK_REASON_NONE
        self._manual_duty_block_since = 0.0
        self._manual_duty_diag_signature_by_label = {}
        self._manual_duty_targets = []
        self._manual_duty_group_name = MANUAL_DUTY_NO_LABEL
        self._tracker.clear()
        if self._manual_duty_popup is not None:
            self._dismiss_manual_duty_popup(
                "Manual duty popup closed: UI session/runtime context reset.",
                stop_motor=True,
            )
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
        return resolve_manual_duty_scope_state(
            label=label,
            runtime_state_by_label=dict(self.__dict__.get("_latest_runtime_devices", {})),
            controlled_lifecycle_active=self._controlled_lifecycle_active_known is True,
        ).allowed

    def _manual_duty_scope_block_message_for_targets(self, targets: List[str]) -> str:
        """
        NAME
            _manual_duty_scope_block_message_for_targets - Return a lifecycle-scope block reason for manual duty targets.
        """
        if self._scope_transition_pending():
            return MANUAL_DUTY_BLOCKED_TRANSITION_TEXT
        if self._controlled_lifecycle_active_known is not True:
            return NT_VALUE_EMPTY
        for label in targets:
            state = resolve_manual_duty_scope_state(
                label=label,
                runtime_state_by_label=dict(self.__dict__.get("_latest_runtime_devices", {})),
                controlled_lifecycle_active=True,
            )
            if not state.allowed:
                return state.blocked_reason
        return NT_VALUE_EMPTY

    def _manual_duty_binding_block_message_for_targets(self, targets: List[str]) -> str:
        """
        NAME
            _manual_duty_binding_block_message_for_targets - Return one binding-ownership block reason for manual duty targets.
        """
        state = resolve_manual_duty_binding_state(
            target_labels=list(targets or []),
            runtime_groups=self._latest_runtime_state_payload_groups(),
        )
        return NT_VALUE_EMPTY if state.allowed else state.blocked_reason

    def _is_manual_motor_node(self, node: object) -> bool:
        """
        NAME
            _is_manual_motor_node - Return whether the live node is a motor-like device.
        """
        if node is None:
            return False
        device_type = str(getattr(node, "device_type", NT_VALUE_EMPTY)).strip()
        if device_type == DEVICE_TYPE_MOTOR:
            return True
        category = str(getattr(node, "category", NT_VALUE_EMPTY)).strip()
        return shape_kind_for_category(category) == "motor"

    def _on_live_node_right_click(self, node: object, event: tk.Event) -> None:
        """
        NAME
            _on_live_node_right_click - Open the manual motor popup for a motor node.
        """
        if not self._is_manual_motor_node(node):
            return
        label = str(getattr(node, DEVICE_KEY_LABEL, NT_VALUE_EMPTY)).strip()
        if not label:
            label = str(getattr(node, "label", NT_VALUE_EMPTY)).strip()
        if not label:
            return
        access_state = self._manual_duty_action_state([label])
        if not access_state.allowed:
            self._append_output(
                MANUAL_DUTY_BUSY_TEXT
                if access_state.blocked_reason == RUNTIME_FETCH_BLOCK_BUSY
                else access_state.blocked_reason
            )
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
        if group_name.strip().lower() == GROUP_ACTIVE_NAME:
            group_payload = self._runtime_active_group_payload()
        else:
            group_payload = group.get(GROUP_KEY_GROUP)
        if not isinstance(group_payload, dict):
            self._append_output(f"Group payload not available for {group_name}.")
            return
        targets = self._resolved_group_motor_targets(group_payload)
        if not targets:
            self._append_output(f"Group has no motor targets: {group_name}")
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
        action_state = self._active_group_edit_action_state()
        if not action_state.allowed:
            self._append_output(action_state.blocked_reason or ACTIVE_GROUP_WAITING_TEXT)
            if action_state.refresh_when_blocked:
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
            if action_state.refresh_after_action:
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
        action_state = self._override_action_state()
        if not action_state.allowed:
            self._append_output(action_state.blocked_reason)
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
            if action_state.refresh_after_action:
                self.after_idle(self._request_runtime_state_refresh)

    def _open_manual_duty_targets(self, label: str, targets: List[str], x_root: int, y_root: int) -> None:
        """
        NAME
            _open_manual_duty_targets - Validate manual-duty preconditions then open the shared popup for one or more targets.
        """
        action_state = self._manual_duty_action_state(targets)
        if not action_state.allowed:
            self._append_output(
                MANUAL_DUTY_BUSY_TEXT
                if action_state.blocked_reason == RUNTIME_FETCH_BLOCK_BUSY
                else action_state.blocked_reason
            )
            return
        if action_state.refresh_before_action:
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
        filtered_targets = [
            target for target in list(targets or []) if self._is_manual_duty_target_allowed(target)
        ]
        if filtered_targets:
            targets = filtered_targets
        action_state = self._manual_duty_action_state(targets)
        if not action_state.allowed:
            self._append_output(
                MANUAL_DUTY_BUSY_TEXT
                if action_state.blocked_reason == RUNTIME_FETCH_BLOCK_BUSY
                else action_state.blocked_reason
            )
            return
        if action_state.refresh_before_action:
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
            self._dismiss_manual_duty_popup(
                "Manual duty popup closed: outside click in live view.",
                stop_motor=True,
            )

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
        if self._manual_duty_popup is not None:
            self._dismiss_manual_duty_popup(
                "Manual duty popup closed: replaced by a new manual-duty popup.",
                stop_motor=True,
            )
        popup = tk.Toplevel(self)
        popup.title(MANUAL_DUTY_POPUP_TITLE)
        popup.transient(self)
        popup.resizable(False, False)
        popup.geometry(
            f"{MANUAL_DUTY_POPUP_SIZE}+{x_root + MANUAL_DUTY_POPUP_OFFSET_X}+{y_root + MANUAL_DUTY_POPUP_OFFSET_Y}"
        )
        popup.bind(
            "<Destroy>",
            lambda event, expected_popup=popup: self._on_manual_duty_popup_destroy(event, expected_popup),
            add="+",
        )
        popup.protocol(
            "WM_DELETE_WINDOW",
            lambda: self._dismiss_manual_duty_popup(
                "Manual duty popup closed: popup window dismissed.",
                stop_motor=True,
            ),
        )
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
        self._clear_manual_duty_block_tracking()
        self._clear_manual_duty_diag_tracking()
        scale.focus_set()

    def _emit_manual_duty_popup_reason(self, reason: str) -> None:
        """
        NAME
            _emit_manual_duty_popup_reason - Mirror one popup-close reason to the UI log and stdout.
        """
        clean_reason = str(reason or NT_VALUE_EMPTY).strip()
        if not clean_reason:
            return
        self._append_output(clean_reason)
        try:
            print(clean_reason, flush=True)
        except Exception:
            pass

    def _on_manual_duty_popup_destroy(self, event: tk.Event, expected_popup: tk.Toplevel) -> None:
        """
        NAME
            _on_manual_duty_popup_destroy - Log popup destruction that bypasses the normal dismiss helper.
        """
        if event is None or getattr(event, "widget", None) is not expected_popup:
            return
        reason = str(self.__dict__.pop("_manual_duty_popup_close_reason", NT_VALUE_EMPTY) or NT_VALUE_EMPTY).strip()
        if reason:
            return
        if self._manual_duty_popup is expected_popup:
            unexpected_reason = "Manual duty popup closed: popup destroyed unexpectedly."
            self._manual_duty_popup_close_reason = unexpected_reason
            self._emit_manual_duty_popup_reason(unexpected_reason)
            self._close_manual_duty_popup(stop_motor=True)

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
        self._clear_manual_duty_block_tracking()
        self._clear_manual_duty_diag_tracking()
        for live_view in self._iter_live_views():
            live_view.clear_group_run_inspector()
        if popup is not None:
            try:
                popup.destroy()
            except Exception:
                pass
        if stop_motor and targets:
            self._send_manual_duty_clear(label, targets, group_name)

    def _dismiss_manual_duty_popup(self, reason: str, stop_motor: bool) -> None:
        """
        NAME
            _dismiss_manual_duty_popup - Log one operator-facing reason, then close the manual-duty popup.
        """
        if self._manual_duty_popup is None:
            return
        clean_reason = str(reason or NT_VALUE_EMPTY).strip()
        if clean_reason:
            self._manual_duty_popup_close_reason = clean_reason
            self._emit_manual_duty_popup_reason(clean_reason)
        self._close_manual_duty_popup(stop_motor=stop_motor)

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
            _poll_presence_overrides - Apply any host-side presence override source.
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
        overrides: Dict[str, str] = {}
        runtime_devices = self.__dict__.get("_latest_runtime_devices", {})
        if isinstance(runtime_devices, dict):
            for device in runtime_devices.values():
                if not isinstance(device, dict):
                    continue
                label = str(device.get(DEVICE_KEY_LABEL, "")).strip()
                if not label:
                    continue
                value = _presence_override_from_runtime_device(device)
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
        passive_result = self._current_passive_result()
        existence_packet_counts = self._visibility_existence_packet_counts(passive_result)
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
                self._format_visibility_existence_packet_count(
                    existence_packet_counts.get(label.strip().lower())
                ),
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
                VIS_ROW_META_IDENTITY: self._format_visibility_identity(device),
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
            self._apply_visibility_selection(
                str(meta.get(VIS_ROW_META_LABEL, NT_VALUE_EMPTY)).strip(),
                passive_result=passive_result,
            )
        elif selected_unrecognized_item:
            self._visibility_unrecognized_table.selection_set(selected_unrecognized_item)
            self._visibility_unrecognized_table.focus(selected_unrecognized_item)
            self._visibility_unrecognized_table.see(selected_unrecognized_item)
            meta = self._visibility_row_meta.get(selected_unrecognized_item, {})
            raw_ids = meta.get(VIS_ROW_META_RAW_IDS, [])
            self._populate_ctre_raw_table(raw_ids if isinstance(raw_ids, list) else [])
            self._apply_visibility_selection(
                str(meta.get(VIS_ROW_META_LABEL, NT_VALUE_EMPTY)).strip(),
                passive_result=passive_result,
            )
        else:
            self._populate_ctre_raw_table([])
            self._set_visibility_passive_detail_text(EVIDENCE_SOURCE_NONE)
        self._update_visibility_summary(scoped_summary)
        for live_view in self._iter_live_views():
            live_view.set_visibility_snapshot(snapshot)
        self._refresh_evidence_view()

    def _restart_visibility_can_sniffer(self) -> None:
        """
        NAME
            _restart_visibility_can_sniffer - Restart the passive CAN sniffer source from the CAN Visibility tab.
        """
        callback = getattr(self, "_restart_can_sniffer", None)
        if not callable(callback):
            self._append_output(VIS_RESTART_SNIFFER_UNAVAILABLE)
            return
        self._append_output(VIS_RESTART_SNIFFER_REQUESTED)
        try:
            restarted = bool(callback())
        except Exception as exc:
            self._append_output(VIS_RESTART_SNIFFER_FAILED_FMT.format(error=exc))
            return
        if not restarted:
            self._append_output(VIS_RESTART_SNIFFER_UNAVAILABLE)
            return
        self._append_output(VIS_RESTART_SNIFFER_DONE)
        self._visibility_last_update = 0.0
        self._poll_visibility_snapshot(time.time())

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
            VIS_COL_EXISTENCE_PACKETS,
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
        table.heading(VIS_COL_EXISTENCE_PACKETS, text=VIS_COL_EXISTENCE_PACKETS, anchor=VIS_TREE_ANCHOR_CENTER)
        table.column(
            VIS_COL_EXISTENCE_PACKETS,
            width=VIS_COL_EXISTENCE_PACKETS_WIDTH,
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
            _collect_console_snapshot - Read the current host-side console-diagnostics summary.
        """
        console_monitor = self.__dict__.get("_console_monitor")
        snapshot_now = time.time()
        if console_monitor is None:
            return _build_console_snapshot_from_entries([], snapshot_now)
        try:
            entries = console_monitor.snapshot_entries(snapshot_now)
        except Exception:
            entries = []
        return _build_console_snapshot_from_entries(entries, snapshot_now)

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
            return EVIDENCE_BUS_HEALTH_EMPTY_TEXT
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
            impact = EVIDENCE_BUS_HEALTH_OK_IMPACT
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
        manual_results = self.__dict__.get("_evidence_manual_results", {})
        entry = manual_results.get(clean_label) if isinstance(manual_results, dict) else None
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
        presence_entry: Optional[Dict[str, Any]],
        passive_device: Optional[Any],
        visibility_device: Optional[Dict[str, Any]],
        runtime_device: Optional[Dict[str, Any]],
        console_entry: Optional[Dict[str, Any]],
        system_console: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        NAME
            _infer_device_evidence - Build one first-pass interpreted evidence row.
        """
        manual_entry = self._manual_evidence_for_label(label)
        manual_test_observations = self.__dict__.get("_manual_test_observations", {})
        manual_motion_checks = self.__dict__.get("_manual_motion_checks", {})
        clean_label = str(label or NT_VALUE_EMPTY).strip().lower()
        manual_observation = manual_test_observations.get(clean_label) if isinstance(manual_test_observations, dict) else None
        manual_motion = manual_motion_checks.get(clean_label) if isinstance(manual_motion_checks, dict) else None
        metrics = visibility_device.get(VIS_KEY_METRICS) if isinstance(visibility_device, dict) and isinstance(visibility_device.get(VIS_KEY_METRICS), dict) else {}
        return build_interpreted_evidence_row(
            label=label,
            presence_entry=presence_entry,
            passive_device=passive_device,
            enrichment_snapshot=self._evidence_enrichment_snapshot,
            visibility_device=visibility_device,
            runtime_device=runtime_device,
            console_entry=console_entry,
            system_console=system_console,
            manual_entry=manual_entry,
            manual_observation=manual_observation,
            manual_motion=manual_motion,
            probe_pending=bool(self.__dict__.get("_evidence_probe_pending", False)),
            last_probe_completed_at=float(self.__dict__.get("_evidence_last_probe_completed_at", 0.0) or 0.0),
            probe_run_count=int(self.__dict__.get("_evidence_probe_run_count", 0) or 0),
            now_s=time.time(),
            visibility_identity_text=self._format_visibility_identity(visibility_device or {}),
            visibility_last_seen_text=self._format_visibility_last_seen(metrics),
            visibility_packet_count_text=self._format_visibility_packet_count(metrics),
            visibility_packet_rate_text=self._format_visibility_packet_rate(metrics),
        )

    def _current_output_text(self) -> str:
        """
        NAME
            _current_output_text - Return the current output-pane text for console-log enrichment parsing.
        """
        output_widget = self.__dict__.get("_output")
        if output_widget is None:
            return NT_VALUE_EMPTY
        try:
            return str(output_widget.get("1.0", "end")).strip()
        except Exception:
            return NT_VALUE_EMPTY

    def _ctre_enrichment_rows_from_snapshot(self) -> Dict[Tuple[int, int, int], Dict[str, Any]]:
        """
        NAME
            _ctre_enrichment_rows_from_snapshot - Rebuild CTRE device-enrichment rows from the cached enrichment snapshot.
        """
        result: Dict[Tuple[int, int, int], Dict[str, Any]] = {}
        devices = self._evidence_enrichment_snapshot.get(ENRICHMENT_RUN_DEVICES_KEY, {})
        if not isinstance(devices, dict):
            return result
        for label_key, profile_device in self._profile_devices.items():
            if not isinstance(profile_device, dict):
                continue
            try:
                identity = (
                    int(profile_device.get(KEY_MANUFACTURER)),
                    int(profile_device.get(KEY_DEVICE_TYPE)),
                    int(profile_device.get(KEY_ID)),
                )
            except Exception:
                continue
            device_snapshot = devices.get(label_key)
            if not isinstance(device_snapshot, dict):
                continue
            ctre_entry = device_snapshot.get(ENRICHMENT_DEVICE_KEY_CTRE)
            if isinstance(ctre_entry, dict):
                result[identity] = dict(ctre_entry)
        return result

    def _run_evidence_enrichment(self) -> None:
        """
        NAME
            _run_evidence_enrichment - Run host-side enrichment sources and refresh the Evidence view.
        """
        profile_name = str(self._profile_box.get()).strip()
        rio_host = str(getattr(self, "_rio_host", NT_VALUE_EMPTY)).strip()
        self._append_output(
            f"{timestamp_hms()} "
            + OUTPUT_EVIDENCE_ENRICHMENT_RUN_FMT.format(
                profile=profile_name or PROFILE_NONE,
                rio=rio_host or NT_VALUE_EMPTY,
                devices=len(self._profile_devices),
            )
        )
        self._evidence_enrichment_snapshot = build_enrichment_run_snapshot(
            profile_devices=self._profile_devices,
            profile_name=profile_name,
            rio_host=rio_host,
            output_log_text=self._current_output_text(),
        )
        snapshot_devices = self._evidence_enrichment_snapshot.get(ENRICHMENT_RUN_DEVICES_KEY, {})
        snapshot_warnings = self._evidence_enrichment_snapshot.get(ENRICHMENT_RUN_WARNINGS_KEY, ())
        self._append_output(
            OUTPUT_EVIDENCE_ENRICHMENT_RESULT_FMT.format(
                devices=len(snapshot_devices) if isinstance(snapshot_devices, dict) else 0,
                warnings=len(tuple(snapshot_warnings)) if isinstance(snapshot_warnings, (list, tuple)) else 0,
            )
        )
        metadata = self._evidence_enrichment_snapshot.get(ENRICHMENT_RUN_METADATA_KEY, {})
        if isinstance(metadata, dict):
            for source_name in OUTPUT_EVIDENCE_ENRICHMENT_SOURCES:
                source_entry = metadata.get(source_name, {})
                if not isinstance(source_entry, dict):
                    continue
                self._append_output(
                    OUTPUT_EVIDENCE_ENRICHMENT_SOURCE_FMT.format(
                        source=source_name or OUTPUT_EVIDENCE_ENRICHMENT_SOURCE_UNKNOWN,
                        status=str(
                            source_entry.get(ENRICHMENT_RUN_STATUS_KEY, OUTPUT_EVIDENCE_ENRICHMENT_SOURCE_UNKNOWN)
                        ).strip()
                        or OUTPUT_EVIDENCE_ENRICHMENT_SOURCE_UNKNOWN,
                        summary=str(
                            source_entry.get(ENRICHMENT_RUN_SUMMARY_KEY, OUTPUT_EVIDENCE_ENRICHMENT_SOURCE_UNKNOWN)
                        ).strip()
                        or OUTPUT_EVIDENCE_ENRICHMENT_SOURCE_UNKNOWN,
                    )
                )
        self._evidence_eval_source_fingerprints = {}
        for label_key in self._profile_devices.keys():
            self._mark_evidence_dirty(
                label_key,
                EVIDENCE_DIRTY_PRIORITY_SCOPE,
                EVIDENCE_DIRTY_REASON_PROFILE,
            )
        self._refresh_evidence_enrichment_status()
        self._refresh_evidence_view()
        selected_label = str(self._evidence_selected_title_var.get()).strip()
        if selected_label:
            self._apply_evidence_selection(selected_label)

    def _refresh_evidence_enrichment_status(self) -> None:
        """
        NAME
            _refresh_evidence_enrichment_status - Refresh the shared Evidence-tab enrichment run status line.
        """
        status_var = self.__dict__.get("_evidence_enrichment_status_var")
        if status_var is None:
            return
        status_var.set(
            enrichment_run_status_text(
                self.__dict__.get("_evidence_enrichment_snapshot"),
                now_s=time.time(),
            )
        )

    def _set_fault_finder_text(self, text_value: str) -> None:
        """
        NAME
            _set_fault_finder_text - Replace the read-only CAN Fault Finder text output.
        """
        widget = self.__dict__.get("_fault_finder_text")
        if widget is None:
            return
        self._replace_readonly_text_preserve_scroll(widget, text_value or CAN_FAULT_FINDER_TEXT_NOT_RUN)

    def _current_topology_profile(self) -> Dict[str, object]:
        """
        NAME
            _current_topology_profile - Return the selected profile's local topology graph.
        """
        profile_name = self._selected_real_profile()
        if not profile_name:
            return {}
        try:
            payload = self._load_local_profiles_payload()
        except Exception:
            return {}
        topology_profile = topology_profile_from_payload(payload, profile_name)
        return dict(topology_profile) if isinstance(topology_profile, dict) else {}

    def _run_can_fault_check(self) -> None:
        """
        NAME
            _run_can_fault_check - Freeze current evidence and rank CAN fault candidates.
        """
        now_s = time.time()
        self._fault_finder_status_var.set(CAN_FAULT_FINDER_STATUS_RUNNING)
        try:
            profile_devices = self.__dict__.get("_profile_devices", {})
            if (
                isinstance(profile_devices, dict)
                and profile_devices
                and isinstance(self.__dict__.get("_evidence_eval_cache"), dict)
            ):
                self._update_evidence_cache_incremental(max_devices=len(profile_devices))
            rows = self._build_evidence_rows()
            snapshot = build_evidence_fault_snapshot(
                evidence_rows=rows,
                console_snapshot=self._collect_console_snapshot(),
                topology_profile=self._current_topology_profile(),
                now_s=now_s,
            )
        except Exception as exc:
            self._fault_finder_last_run_at = now_s
            self._fault_finder_result = {}
            self._fault_finder_status_var.set(CAN_FAULT_FINDER_STATUS_NOT_RUN)
            self._set_fault_finder_text(CAN_FAULT_FINDER_TEXT_ERROR_FMT.format(error=exc))
            return
        self._fault_finder_last_run_at = float(snapshot.get(FAULT_SNAPSHOT_KEY_RAN_AT, now_s) or now_s)
        run_count = int(self.__dict__.get("_fault_finder_run_count", 0) or 0) + 1
        self._fault_finder_run_count = run_count
        self._fault_finder_result = dict(snapshot.get(FAULT_SNAPSHOT_KEY_RESULT, {}))
        candidate_count = int(snapshot.get(FAULT_SNAPSHOT_KEY_CANDIDATE_COUNT, 0) or 0)
        clock_text = timestamp_hms()
        self._fault_finder_status_var.set(
            CAN_FAULT_FINDER_STATUS_FMT.format(
                age=_format_age_seconds(0.0),
                clock=clock_text,
                run_count=run_count,
                count=candidate_count,
            )
        )
        rendered_text = str(snapshot.get(FAULT_SNAPSHOT_KEY_RENDERED_TEXT, TEXT_EMPTY))
        self._set_fault_finder_text(
            CAN_FAULT_FINDER_TEXT_RUN_STAMP_FMT.format(
                run_count=run_count,
                clock=clock_text,
                body=rendered_text or TEXT_EMPTY,
            )
        )

    def _evidence_profile_generation(self) -> str:
        """
        NAME
            _evidence_profile_generation - Return one stable generation key for the current evidence profile set.
        """
        labels = sorted(str(label).strip().lower() for label in self._profile_devices.keys())
        return "|".join(labels)

    def _mark_evidence_dirty(self, label_key: str, priority: int, reason: str) -> None:
        """
        NAME
            _mark_evidence_dirty - Mark one device for prioritized reevaluation.
        """
        clean_label = str(label_key or NT_VALUE_EMPTY).strip().lower()
        clean_reason = str(reason or NT_VALUE_EMPTY).strip() or EVIDENCE_DIRTY_REASON_SCOPE
        if not clean_label:
            return
        dirty_labels = self.__dict__.setdefault("_evidence_eval_dirty_labels", {})
        current_entry = dirty_labels.get(clean_label)
        reasons = [] if not isinstance(current_entry, dict) else list(current_entry.get("reasons", EVIDENCE_DIRTY_EMPTY_REASONS))
        if clean_reason not in reasons:
            reasons.append(clean_reason)
        dirty_labels[clean_label] = {
            "priority": min(int(priority), int(current_entry.get("priority", priority))) if isinstance(current_entry, dict) else int(priority),
            "reasons": reasons,
            "at": time.time(),
        }

    def _clear_evidence_dirty(self, label_key: str) -> List[str]:
        """
        NAME
            _clear_evidence_dirty - Remove one device from the prioritized dirty queue and return its reasons.
        """
        clean_label = str(label_key or NT_VALUE_EMPTY).strip().lower()
        dirty_labels = self.__dict__.get("_evidence_eval_dirty_labels", {})
        if not isinstance(dirty_labels, dict):
            return []
        entry = dirty_labels.pop(clean_label, None)
        if isinstance(entry, dict):
            return list(entry.get("reasons", EVIDENCE_DIRTY_EMPTY_REASONS))
        return []

    def _latest_visibility_seen_ms(self, visibility_device: Optional[Dict[str, Any]]) -> float:
        """
        NAME
            _latest_visibility_seen_ms - Return the freshest passive observer timestamp for one visibility device row.
        """
        if not isinstance(visibility_device, dict):
            return 0.0
        metrics = visibility_device.get(VIS_KEY_METRICS)
        if not isinstance(metrics, dict):
            return 0.0
        latest_seen_ms = 0.0
        for metric_entry in metrics.values():
            if not isinstance(metric_entry, dict):
                continue
            last_seen_ms = metric_entry.get(VIS_KEY_LAST_SEEN_MS)
            if isinstance(last_seen_ms, (int, float)):
                latest_seen_ms = max(latest_seen_ms, float(last_seen_ms))
        return latest_seen_ms

    def _evidence_source_fingerprint(
        self,
        *,
        label_key: str,
        presence_entry: Optional[Dict[str, Any]],
        passive_device: Optional[Any],
        visibility_device: Optional[Dict[str, Any]],
        runtime_device: Optional[Dict[str, Any]],
        console_entry: Optional[Dict[str, Any]],
        manual_entry: Optional[Dict[str, Any]],
    ) -> Tuple[Any, ...]:
        """
        NAME
            _evidence_source_fingerprint - Build one compact per-device raw-source fingerprint for dirty detection.
        """
        del label_key
        passive_score = int(getattr(passive_device, "presence_score", 0) or 0) if passive_device is not None else 0
        passive_expected = str(getattr(passive_device, "expected_status", NT_VALUE_EMPTY)).strip().lower() if passive_device is not None else NT_VALUE_EMPTY
        presence_bucket = NT_VALUE_EMPTY
        presence_existence = NT_VALUE_EMPTY
        presence_updated_at = 0.0
        if isinstance(presence_entry, dict):
            presence_bucket = str(presence_entry.get(PRESENCE_KEY_BUCKET, NT_VALUE_EMPTY)).strip().lower()
            presence_existence = str(presence_entry.get(PRESENCE_KEY_EXISTENCE, NT_VALUE_EMPTY)).strip().upper()
            raw_updated_at = presence_entry.get("updatedAtMs")
            if isinstance(raw_updated_at, (int, float)):
                presence_updated_at = float(raw_updated_at)
        runtime_last_seen_ms = 0.0
        runtime_presence_conf = 0.0
        runtime_lifecycle = NT_VALUE_EMPTY
        if isinstance(runtime_device, dict):
            raw_last_seen_ms = runtime_device.get(VIS_KEY_LAST_SEEN_MS)
            if isinstance(raw_last_seen_ms, (int, float)):
                runtime_last_seen_ms = float(raw_last_seen_ms)
            raw_presence_conf = runtime_device.get("presenceConfidence")
            if isinstance(raw_presence_conf, (int, float)):
                runtime_presence_conf = float(raw_presence_conf)
            runtime_lifecycle = str(runtime_device.get("lifecycleState", NT_VALUE_EMPTY)).strip().lower()
        console_summary = NT_VALUE_EMPTY
        console_has_error = False
        console_has_warn = False
        console_event_count = 0
        if isinstance(console_entry, dict):
            console_summary = str(console_entry.get(CONSOLE_KEY_SUMMARY, NT_VALUE_EMPTY)).strip().lower()
            console_has_error = bool(console_entry.get(CONSOLE_KEY_HAS_ERROR))
            console_has_warn = bool(console_entry.get(CONSOLE_KEY_HAS_WARN))
            events = console_entry.get("events")
            if isinstance(events, list):
                console_event_count = len(events)
        manual_outcome = NT_VALUE_EMPTY
        if isinstance(manual_entry, dict):
            manual_outcome = str(manual_entry.get("outcome", NT_VALUE_EMPTY)).strip().lower()
        return (
            passive_score,
            passive_expected,
            presence_bucket,
            presence_existence,
            presence_updated_at,
            self._latest_visibility_seen_ms(visibility_device),
            runtime_last_seen_ms,
            runtime_presence_conf,
            runtime_lifecycle,
            console_summary,
            console_has_error,
            console_has_warn,
            console_event_count,
            manual_outcome,
        )

    def _dirty_priority_for_fingerprint_change(
        self,
        previous_fingerprint: Optional[Tuple[Any, ...]],
        current_fingerprint: Tuple[Any, ...],
    ) -> Tuple[Optional[int], str]:
        """
        NAME
            _dirty_priority_for_fingerprint_change - Classify one raw-source fingerprint change for reevaluation priority.
        """
        if previous_fingerprint is None:
            return EVIDENCE_DIRTY_PRIORITY_SCOPE, EVIDENCE_DIRTY_REASON_PROFILE
        if previous_fingerprint == current_fingerprint:
            return None, NT_VALUE_EMPTY
        if previous_fingerprint[9:13] != current_fingerprint[9:13]:
            return EVIDENCE_DIRTY_PRIORITY_CONSOLE, EVIDENCE_DIRTY_REASON_CONSOLE
        if previous_fingerprint[0:6] != current_fingerprint[0:6]:
            return EVIDENCE_DIRTY_PRIORITY_PRESENCE, EVIDENCE_DIRTY_REASON_PASSIVE
        if previous_fingerprint[6:9] != current_fingerprint[6:9]:
            return EVIDENCE_DIRTY_PRIORITY_PRESENCE, EVIDENCE_DIRTY_REASON_RUNTIME
        if previous_fingerprint[13] != current_fingerprint[13]:
            return EVIDENCE_DIRTY_PRIORITY_SCOPE, EVIDENCE_DIRTY_REASON_MANUAL
        return EVIDENCE_DIRTY_PRIORITY_SCOPE, EVIDENCE_DIRTY_REASON_SCOPE

    def _update_evidence_dirty_from_sources(
        self,
        *,
        grouped_labels: Dict[str, List[str]],
        presence_entries_by_label: Dict[str, Dict[str, Any]],
        passive_devices_by_identity: Dict[Tuple[int, int, int], Any],
        visibility_devices: Dict[str, Dict[str, Any]],
        console_devices: Dict[str, Dict[str, Any]],
    ) -> None:
        """
        NAME
            _update_evidence_dirty_from_sources - Compare raw-source fingerprints and mark changed devices dirty.
        """
        fingerprints = self.__dict__.setdefault("_evidence_eval_source_fingerprints", {})
        for labels in grouped_labels.values():
            for label_key in labels:
                profile_device = self._profile_devices.get(label_key, {})
                passive_device = passive_devices_by_identity.get(
                    (
                        int(profile_device.get(DEVICE_KEY_MFG, 0)),
                        int(profile_device.get(DEVICE_KEY_TYPE, 0)),
                        int(profile_device.get(DEVICE_KEY_ID, 0)),
                    )
                )
                current_fingerprint = self._evidence_source_fingerprint(
                    label_key=label_key,
                    presence_entry=presence_entries_by_label.get(label_key),
                    passive_device=passive_device,
                    visibility_device=visibility_devices.get(label_key),
                    runtime_device=self._latest_runtime_devices.get(label_key),
                    console_entry=console_devices.get(label_key),
                    manual_entry=self._manual_evidence_for_label(str(profile_device.get(DEVICE_KEY_LABEL, label_key)).strip() or label_key),
                )
                previous_fingerprint = fingerprints.get(label_key)
                priority, reason = self._dirty_priority_for_fingerprint_change(previous_fingerprint, current_fingerprint)
                if priority is not None:
                    self._mark_evidence_dirty(label_key, priority, reason)
                fingerprints[label_key] = current_fingerprint

    def _build_evidence_event(
        self,
        *,
        event_type: str,
        old_value: str,
        new_value: str,
        reason: str,
        at: float,
    ) -> Dict[str, Any]:
        """
        NAME
            _build_evidence_event - Build one normalized interpreted-device event entry.
        """
        return {
            "at": float(at),
            "source": EVIDENCE_EVENT_SOURCE_EVALUATOR,
            "eventType": event_type,
            "oldValue": old_value,
            "newValue": new_value,
            "reason": reason,
        }

    def _finalize_evidence_row_state(
        self,
        *,
        previous_row: Optional[Dict[str, Any]],
        row: Dict[str, Any],
        dirty_reasons: List[str],
        now_s: float,
    ) -> Dict[str, Any]:
        """
        NAME
            _finalize_evidence_row_state - Merge transition metadata and event history into one evaluated row.
        """
        result = dict(row)
        previous = previous_row if isinstance(previous_row, dict) else {}
        previous_presence = str(previous.get(INTERPRET_KEY_PRESENCE_STATE, EVIDENCE_PRESENCE_STATE_UNKNOWN)).strip().lower()
        current_presence = str(result.get(INTERPRET_KEY_PRESENCE_STATE, EVIDENCE_PRESENCE_STATE_UNKNOWN)).strip().lower()
        previous_operability = str(previous.get(INTERPRET_KEY_OPERABILITY, EVIDENCE_STATUS_UNKNOWN)).strip().upper()
        current_operability = str(result.get(INTERPRET_KEY_OPERABILITY, EVIDENCE_STATUS_UNKNOWN)).strip().upper()
        previous_freshness = str(previous.get("freshness", EVIDENCE_FRESHNESS_STALE)).strip().lower()
        current_freshness = str(result.get("freshness", EVIDENCE_FRESHNESS_STALE)).strip().lower()
        reason_parts = list(dirty_reasons)
        presence_reasons = result.get(INTERPRET_KEY_PRESENCE_REASONS)
        if isinstance(presence_reasons, list):
            for reason in presence_reasons:
                clean_reason = str(reason or NT_VALUE_EMPTY).strip()
                if clean_reason and clean_reason not in reason_parts:
                    reason_parts.append(clean_reason)
                    if len(reason_parts) >= 3:
                        break
        change_reason = reason_parts[0] if reason_parts else str(result.get(INTERPRET_KEY_NOTES_TEXT, EVIDENCE_SOURCE_NONE)).strip() or EVIDENCE_SOURCE_NONE
        events = list(previous.get(INTERPRET_KEY_EVENT_LOG, [])) if isinstance(previous.get(INTERPRET_KEY_EVENT_LOG), list) else []
        if previous_presence != current_presence:
            event_type = EVIDENCE_EVENT_TYPE_PRESENCE_GAINED
            if current_presence in (EVIDENCE_PRESENCE_STATE_MISSING, EVIDENCE_PRESENCE_STATE_CONFLICT):
                event_type = EVIDENCE_EVENT_TYPE_PRESENCE_LOST
            events.append(
                self._build_evidence_event(
                    event_type=event_type,
                    old_value=previous_presence,
                    new_value=current_presence,
                    reason=change_reason,
                    at=now_s,
                )
            )
            result[INTERPRET_KEY_LAST_STATE_CHANGE_AT] = float(now_s)
        else:
            result[INTERPRET_KEY_LAST_STATE_CHANGE_AT] = previous.get(INTERPRET_KEY_LAST_STATE_CHANGE_AT)
        if previous_operability != current_operability:
            event_type = EVIDENCE_EVENT_TYPE_OPERABILITY_DEGRADED
            if current_operability == EVIDENCE_STATUS_OK:
                event_type = EVIDENCE_EVENT_TYPE_OPERABILITY_RECOVERED
            events.append(
                self._build_evidence_event(
                    event_type=event_type,
                    old_value=previous_operability,
                    new_value=current_operability,
                    reason=change_reason,
                    at=now_s,
                )
            )
            if result.get(INTERPRET_KEY_LAST_STATE_CHANGE_AT) is None:
                result[INTERPRET_KEY_LAST_STATE_CHANGE_AT] = float(now_s)
        if previous_freshness != current_freshness and current_freshness == EVIDENCE_FRESHNESS_STALE:
            events.append(
                self._build_evidence_event(
                    event_type=EVIDENCE_EVENT_TYPE_FRESHNESS_STALE,
                    old_value=previous_freshness,
                    new_value=current_freshness,
                    reason=change_reason,
                    at=now_s,
                )
            )
        current_present = current_presence == EVIDENCE_PRESENCE_STATE_PRESENT
        current_missing = current_presence in (EVIDENCE_PRESENCE_STATE_MISSING, EVIDENCE_PRESENCE_STATE_CONFLICT)
        result[INTERPRET_KEY_LAST_EVALUATION_AT] = float(now_s)
        result[INTERPRET_KEY_LAST_KNOWN_GOOD_AT] = (
            float(now_s) if (current_present and current_operability == EVIDENCE_STATUS_OK) else previous.get(INTERPRET_KEY_LAST_KNOWN_GOOD_AT)
        )
        result[INTERPRET_KEY_LAST_SEEN_PRESENT_AT] = (
            float(now_s) if current_present else previous.get(INTERPRET_KEY_LAST_SEEN_PRESENT_AT)
        )
        result[INTERPRET_KEY_LAST_SEEN_MISSING_AT] = (
            float(now_s) if current_missing else previous.get(INTERPRET_KEY_LAST_SEEN_MISSING_AT)
        )
        if result.get(INTERPRET_KEY_LAST_STATE_CHANGE_AT) is None and not previous:
            result[INTERPRET_KEY_LAST_STATE_CHANGE_AT] = float(now_s)
        result[INTERPRET_KEY_CHANGE_REASON] = change_reason
        result[INTERPRET_KEY_DIRTY] = False
        result[INTERPRET_KEY_DIRTY_REASONS] = []
        result[INTERPRET_KEY_EVENT_LOG] = events[-EVIDENCE_EVENT_LOG_LIMIT:]
        return result

    def _empty_evidence_row(self, label: str, device_type: str) -> Dict[str, Any]:
        """
        NAME
            _empty_evidence_row - Build one placeholder interpreted row before the incremental evaluator reaches a device.
        """
        return {
            INTERPRET_KEY_LABEL: label,
            INTERPRET_KEY_DEVICE_TYPE: device_type,
            INTERPRET_KEY_PASSIVE: EVIDENCE_SOURCE_NONE,
            INTERPRET_KEY_CONSOLE: EVIDENCE_SOURCE_NONE,
            INTERPRET_KEY_PROBE: EVIDENCE_SOURCE_NONE,
            INTERPRET_KEY_PROBE_SCORE: EVIDENCE_SOURCE_NONE,
            INTERPRET_KEY_MANUAL: EVIDENCE_MANUAL_PLACEHOLDER,
            INTERPRET_KEY_EXISTENCE: EVIDENCE_STATUS_UNKNOWN,
            INTERPRET_KEY_OPERABILITY: EVIDENCE_STATUS_UNKNOWN,
            INTERPRET_KEY_IDENTITY: EVIDENCE_STATUS_UNKNOWN,
            INTERPRET_KEY_CONFIDENCE: EVIDENCE_CONFIDENCE_LOW,
            INTERPRET_KEY_PRESENCE_TEXT: EVIDENCE_SOURCE_NONE,
            INTERPRET_KEY_PASSIVE_TEXT: EVIDENCE_SOURCE_NONE,
            INTERPRET_KEY_CONSOLE_TEXT: EVIDENCE_SOURCE_NONE,
            INTERPRET_KEY_PROBE_TEXT: EVIDENCE_SOURCE_NONE,
            INTERPRET_KEY_MANUAL_TEXT: EVIDENCE_MANUAL_PLACEHOLDER,
            INTERPRET_KEY_ENRICHMENT_TEXT: EVIDENCE_SOURCE_NONE,
            INTERPRET_KEY_NOTES_TEXT: "Evaluator has not reached this device in the current incremental pass yet.",
            INTERPRET_KEY_STATE: EVIDENCE_STATE_UNKNOWN,
            INTERPRET_KEY_CONFLICTED: False,
            INTERPRET_KEY_PRESENCE_SCORE: 25,
            INTERPRET_KEY_PRESENCE_STATE: "unknown",
            INTERPRET_KEY_PRESENCE_REASONS: ["Evaluator has not reached this device in the current incremental pass yet."],
            "freshness": "stale",
            INTERPRET_KEY_SOURCE_SCORES: {},
            INTERPRET_KEY_DIRTY: True,
            INTERPRET_KEY_DIRTY_REASONS: [EVIDENCE_DIRTY_REASON_PROFILE],
            INTERPRET_KEY_LAST_KNOWN_GOOD_AT: None,
            INTERPRET_KEY_LAST_SEEN_PRESENT_AT: None,
            INTERPRET_KEY_LAST_SEEN_MISSING_AT: None,
            INTERPRET_KEY_LAST_STATE_CHANGE_AT: None,
            INTERPRET_KEY_LAST_EVALUATION_AT: None,
            INTERPRET_KEY_CHANGE_REASON: EVIDENCE_SOURCE_NONE,
            INTERPRET_KEY_EVENT_LOG: [],
        }

    def _evidence_labels_by_device_type(self) -> Dict[str, List[str]]:
        """
        NAME
            _evidence_labels_by_device_type - Group current profile labels by device class for incremental evaluation.
        """
        grouped: Dict[str, List[str]] = {
            DEVICE_CLASS_MOTION: [],
            DEVICE_CLASS_INFRASTRUCTURE: [],
            DEVICE_CLASS_UNPROFILED: [],
        }
        for label_key, profile_device in self._profile_devices.items():
            device_type = classify_device_type(
                label_key,
                profile_device if isinstance(profile_device, dict) else None,
                self._latest_runtime_devices.get(label_key),
                None,
            )
            grouped.setdefault(device_type, []).append(label_key)
        for labels in grouped.values():
            labels.sort()
        return grouped

    def _reset_evidence_evaluator_if_needed(self, grouped_labels: Dict[str, List[str]]) -> None:
        """
        NAME
            _reset_evidence_evaluator_if_needed - Reset cache/cursor when the current evidence profile set changes.
        """
        generation = self._evidence_profile_generation()
        if generation == str(self.__dict__.get("_evidence_eval_generation", NT_VALUE_EMPTY)):
            return
        self._evidence_eval_generation = generation
        self._evidence_eval_cursor_class_index = 0
        self._evidence_eval_cursor_device_index = 0
        class_order = list(
            self.__dict__.get(
                "_evidence_eval_class_order",
                [DEVICE_CLASS_MOTION, DEVICE_CLASS_INFRASTRUCTURE, DEVICE_CLASS_UNPROFILED],
            )
        )
        cache: Dict[str, Dict[str, Any]] = {}
        for device_type in class_order:
            for label_key in grouped_labels.get(device_type, []):
                profile_device = self._profile_devices.get(label_key, {})
                display_label = str(profile_device.get(DEVICE_KEY_LABEL, label_key)).strip() or label_key
                cache[label_key] = self._empty_evidence_row(display_label, device_type)
        self._evidence_eval_cache = cache
        self._evidence_eval_dirty_labels = {}
        self._evidence_eval_source_fingerprints = {}
        for labels in grouped_labels.values():
            for label_key in labels:
                self._mark_evidence_dirty(label_key, EVIDENCE_DIRTY_PRIORITY_SCOPE, EVIDENCE_DIRTY_REASON_PROFILE)

    def _next_evidence_eval_target(
        self,
        grouped_labels: Dict[str, List[str]],
    ) -> Optional[Tuple[str, str]]:
        """
        NAME
            _next_evidence_eval_target - Return the next device-class/label pair for the incremental evaluator.
        """
        dirty_labels = self.__dict__.get("_evidence_eval_dirty_labels", {})
        if isinstance(dirty_labels, dict) and dirty_labels:
            best_label = NT_VALUE_EMPTY
            best_priority = None
            for labels in grouped_labels.values():
                for label_key in labels:
                    dirty_entry = dirty_labels.get(label_key)
                    if not isinstance(dirty_entry, dict):
                        continue
                    priority = int(dirty_entry.get("priority", EVIDENCE_DIRTY_PRIORITY_SCOPE))
                    if best_priority is None or priority < best_priority:
                        best_label = label_key
                        best_priority = priority
            if best_label:
                for device_type, labels in grouped_labels.items():
                    if best_label in labels:
                        return device_type, best_label
        class_order = list(self.__dict__.get("_evidence_eval_class_order", []))
        if not class_order:
            return None
        class_index = int(self.__dict__.get("_evidence_eval_cursor_class_index", 0) or 0)
        device_index = int(self.__dict__.get("_evidence_eval_cursor_device_index", 0) or 0)
        while class_index < len(class_order):
            device_type = class_order[class_index]
            labels = grouped_labels.get(device_type, [])
            if device_index < len(labels):
                label_key = labels[device_index]
                self._evidence_eval_cursor_class_index = class_index
                self._evidence_eval_cursor_device_index = device_index + 1
                return device_type, label_key
            class_index += 1
            device_index = 0
            self._evidence_eval_cursor_class_index = class_index
            self._evidence_eval_cursor_device_index = 0
        self._evidence_eval_cursor_class_index = 0
        self._evidence_eval_cursor_device_index = 0
        return None

    def _update_evidence_cache_incremental(self, max_devices: Optional[int] = None) -> None:
        """
        NAME
            _update_evidence_cache_incremental - Recompute only a small fixed number of interpreted device rows.
        """
        budget = int(max_devices if isinstance(max_devices, int) else self.__dict__.get("_evidence_eval_budget", 2) or 2)
        if budget <= 0:
            return
        grouped_labels = self._evidence_labels_by_device_type()
        self._reset_evidence_evaluator_if_needed(grouped_labels)
        passive_result = build_live_passive_result(
            self._visibility_provider,
            self._profile_devices,
            ctre_enrichment=self._ctre_enrichment_rows_from_snapshot(),
            enrichment_records=tuple(
                self.__dict__.get("_evidence_enrichment_snapshot", {}).get(ENRICHMENT_RUN_RECORDS_KEY, ()) or ()
            ),
        )
        passive_devices_by_identity = index_run_result_by_identity(passive_result)
        presence_entries_by_label = build_runtime_presence_catalog(
            self._latest_runtime_devices,
            self._profile_devices,
        )
        visibility_devices: Dict[str, Dict[str, Any]] = {}
        devices = self._latest_visibility_snapshot.get(VIS_KEY_DEVICES)
        if isinstance(devices, list):
            for device in devices:
                if not isinstance(device, dict):
                    continue
                label = str(device.get(VIS_KEY_LABEL, NT_VALUE_EMPTY)).strip()
                if label:
                    visibility_devices[label.lower()] = device
        console_snapshot = self._collect_console_snapshot()
        console_devices = {}
        if isinstance(console_snapshot, dict):
            raw_console_devices = console_snapshot.get(EVIDENCE_CONSOLE_SCOPE_DEVICES)
            if isinstance(raw_console_devices, dict):
                console_devices = raw_console_devices
        self._update_evidence_dirty_from_sources(
            grouped_labels=grouped_labels,
            presence_entries_by_label=presence_entries_by_label,
            passive_devices_by_identity=passive_devices_by_identity,
            visibility_devices=visibility_devices,
            console_devices=console_devices,
        )
        processed = 0
        while processed < budget:
            target = self._next_evidence_eval_target(grouped_labels)
            if target is None:
                break
            _device_type, label_key = target
            profile_device = self._profile_devices.get(label_key, {})
            display_label = str(profile_device.get(DEVICE_KEY_LABEL, label_key)).strip() or label_key
            previous_row = self._evidence_eval_cache.get(label_key)
            passive_device = passive_devices_by_identity.get(
                (
                    int(profile_device.get(DEVICE_KEY_MFG, 0)),
                    int(profile_device.get(DEVICE_KEY_TYPE, 0)),
                    int(profile_device.get(DEVICE_KEY_ID, 0)),
                )
            )
            new_row = self._infer_device_evidence(
                display_label,
                presence_entries_by_label.get(label_key),
                passive_device,
                visibility_devices.get(label_key),
                self._latest_runtime_devices.get(label_key),
                console_devices.get(label_key),
                console_snapshot,
            )
            dirty_reasons = self._clear_evidence_dirty(label_key)
            self._evidence_eval_cache[label_key] = self._finalize_evidence_row_state(
                previous_row=previous_row,
                row=new_row,
                dirty_reasons=dirty_reasons,
                now_s=time.time(),
            )
            processed += 1

    def _build_evidence_rows(self) -> List[Dict[str, Any]]:
        """
        NAME
            _build_evidence_rows - Build interpreted evidence rows for the current profile.
        """
        self._update_evidence_cache_incremental()
        dirty_labels = self.__dict__.get("_evidence_eval_dirty_labels", {})
        rows: List[Dict[str, Any]] = []
        for label_key, row in self.__dict__.get("_evidence_eval_cache", {}).items():
            row_copy = dict(row)
            dirty_entry = dirty_labels.get(label_key) if isinstance(dirty_labels, dict) else None
            if isinstance(dirty_entry, dict):
                row_copy[INTERPRET_KEY_DIRTY] = True
                row_copy[INTERPRET_KEY_DIRTY_REASONS] = list(dirty_entry.get("reasons", EVIDENCE_DIRTY_EMPTY_REASONS))
            rows.append(row_copy)
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
        self._replace_readonly_text_preserve_scroll(widget, text_value or EVIDENCE_SOURCE_NONE)

    def _replace_readonly_text_preserve_scroll(self, widget: tk.Text, text_value: str) -> None:
        """
        NAME
            _replace_readonly_text_preserve_scroll - Rewrite one read-only text pane without snapping its scroll position to the top.
        """
        scroll_top = 0.0
        try:
            yview_state = widget.yview()
            if isinstance(yview_state, tuple) and yview_state:
                scroll_top = float(yview_state[0])
        except Exception:
            scroll_top = 0.0
        configure = getattr(widget, "configure", None)
        if callable(configure):
            configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text_value)
        if callable(configure):
            configure(state="disabled")
        try:
            widget.yview_moveto(scroll_top)
        except Exception:
            pass

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
        self._set_evidence_text(EVIDENCE_ENRICHMENT_TEXT, str(row.get("enrichmentText", EVIDENCE_SOURCE_NONE)))
        self._set_evidence_text(EVIDENCE_PROBE_TEXT, str(row.get("probeText", EVIDENCE_SOURCE_NONE)))
        self._set_evidence_text(EVIDENCE_MANUAL_TEXT, str(row.get("manualText", EVIDENCE_MANUAL_PLACEHOLDER)))
        self._set_evidence_text(EVIDENCE_NOTES_TEXT, str(row.get("notesText", EVIDENCE_NOTE_NONE)))

    def _refresh_evidence_view(self) -> None:
        """
        NAME
            _refresh_evidence_view - Rebuild the Evidence table, topology overlay, and inspector.
        """
        self._refresh_evidence_enrichment_status()
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
        evidence_detail_snapshot = {
            str(row.get("label", NT_VALUE_EMPTY)).strip().lower(): build_interpreted_device_detail_snapshot(row)
            for row in rows
            if str(row.get("label", NT_VALUE_EMPTY)).strip()
        }
        for topology_view in self._iter_live_views():
            if hasattr(topology_view, "set_evidence_snapshot"):
                topology_view.set_evidence_snapshot(evidence_snapshot)
            if hasattr(topology_view, "set_evidence_detail_snapshot"):
                topology_view.set_evidence_detail_snapshot(evidence_detail_snapshot)
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
            f"[{self._evidence_engine_status.get('engineLabel', ENGINE_LABEL_LEGACY)}] Devices: {len(rows)} | Showing: {len(shown_rows)} | Filter: {EVIDENCE_FILTER_LABELS.get(filter_key, EVIDENCE_FILTER_LABELS[EVIDENCE_FILTER_ALL])}"
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

    def _format_visibility_existence_packet_count(self, packet_count: Optional[int]) -> str:
        """
        NAME
            _format_visibility_existence_packet_count - Format the count of direct device-emitted packets supporting existence.
        """
        if not isinstance(packet_count, int):
            return VIS_PACKETS_UNKNOWN
        return str(max(0, int(packet_count)))

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

    def _current_passive_result(self):
        """
        NAME
            _current_passive_result - Build and cache the shared passive CAN analyzer result for the current profile and visibility window.
        """
        passive_result = build_live_passive_result(
            self._visibility_provider,
            self._profile_devices,
            ctre_enrichment=self._ctre_enrichment_rows_from_snapshot(),
            enrichment_records=tuple(self._evidence_enrichment_snapshot.get(ENRICHMENT_RUN_RECORDS_KEY, ()) or ()),
        )
        self._latest_passive_result = passive_result
        visibility_devices = {}
        latest_visibility_snapshot = self.__dict__.get("_latest_visibility_snapshot", {})
        devices = latest_visibility_snapshot.get(VIS_KEY_DEVICES) if isinstance(latest_visibility_snapshot, dict) else None
        if isinstance(devices, list):
            for device in devices:
                if not isinstance(device, dict):
                    continue
                device_label = str(device.get(VIS_KEY_LABEL, NT_VALUE_EMPTY)).strip()
                if device_label:
                    visibility_devices[device_label.lower()] = device
        passive_detail_snapshot = {
            str(getattr(device, "profile_label", NT_VALUE_EMPTY)).strip().lower(): build_passive_device_detail_snapshot(
                str(getattr(device, "profile_label", NT_VALUE_EMPTY)).strip(),
                passive_result=passive_result,
                visibility_device=visibility_devices.get(
                    str(getattr(device, "profile_label", NT_VALUE_EMPTY)).strip().lower()
                ),
            )
            for device in getattr(passive_result, "device_records", ())
            if str(getattr(device, "profile_label", NT_VALUE_EMPTY)).strip()
        }
        for visibility_label, visibility_device in visibility_devices.items():
            if visibility_label in passive_detail_snapshot:
                continue
            passive_detail_snapshot[visibility_label] = build_passive_device_detail_snapshot(
                visibility_label,
                passive_result=passive_result,
                visibility_device=visibility_device,
            )
        for topology_view in self._iter_live_views():
            if hasattr(topology_view, "set_passive_detail_snapshot"):
                topology_view.set_passive_detail_snapshot(passive_detail_snapshot)
        return passive_result

    def _visibility_existence_packet_counts(self, passive_result=None) -> Dict[str, int]:
        """
        NAME
            _visibility_existence_packet_counts - Build per-label counts of passive device-emitted packets that support existence.
        """
        if passive_result is None:
            passive_result = self._current_passive_result()
        if passive_result is None:
            return {}
        family_counts = {}
        for family in getattr(passive_result, "family_records", ()):
            family_key = getattr(family, "key", None)
            family_role = str(getattr(family, "role", NT_VALUE_EMPTY)).strip()
            metrics = getattr(family, "metrics", None)
            count_value = getattr(metrics, "count", None)
            if family_key is None or not family_role.startswith("DEVICE_EMITTED_") or not isinstance(count_value, (int, float)):
                continue
            family_counts[family_key] = max(0, int(count_value))
        counts_by_label: Dict[str, int] = {}
        for device in getattr(passive_result, "device_records", ()):
            label_key = str(getattr(device, "profile_label", NT_VALUE_EMPTY)).strip().lower()
            if not label_key:
                continue
            total = 0
            for family_key in tuple(getattr(device, "evidence_family_keys", ()) or ()):
                total += int(family_counts.get(family_key, 0) or 0)
            counts_by_label[label_key] = total
        return counts_by_label

    def _apply_visibility_selection(self, label: str, *, passive_result=None) -> None:
        """
        NAME
            _apply_visibility_selection - Update the CAN Visibility deep-dive panel for one selected row.
        """
        clean_label = str(label or NT_VALUE_EMPTY).strip()
        visibility_live_view = self.__dict__.get("_visibility_live_view")
        if not clean_label:
            if visibility_live_view is not None and hasattr(visibility_live_view, "select_node_by_label"):
                visibility_live_view.select_node_by_label(None)
            if visibility_live_view is not None and hasattr(visibility_live_view, "set_synthetic_selection_detail"):
                visibility_live_view.set_synthetic_selection_detail(None)
            self._set_visibility_passive_detail_text(EVIDENCE_SOURCE_NONE)
            return
        visibility_device = None
        devices = self._latest_visibility_snapshot.get(VIS_KEY_DEVICES)
        if isinstance(devices, list):
            for device in devices:
                if not isinstance(device, dict):
                    continue
                device_label = str(device.get(VIS_KEY_LABEL, NT_VALUE_EMPTY)).strip()
                if device_label.lower() == clean_label.lower():
                    visibility_device = device
                    break
        metrics = (
            visibility_device.get(VIS_KEY_METRICS)
            if isinstance(visibility_device, dict) and isinstance(visibility_device.get(VIS_KEY_METRICS), dict)
            else {}
        )
        if passive_result is None:
            passive_result = self.__dict__.get("_latest_passive_result")
        if passive_result is None:
            passive_result = self._current_passive_result()
        self._set_visibility_passive_detail_text(
            build_passive_visibility_deep_dive_text(
                label=clean_label,
                passive_result=passive_result,
                visibility_device=visibility_device,
                visibility_identity_text=self._format_visibility_identity(visibility_device or {}),
                visibility_last_seen_text=self._format_visibility_last_seen(metrics),
                visibility_packet_count_text=self._format_visibility_packet_count(metrics),
                visibility_packet_rate_text=self._format_visibility_packet_rate(metrics),
            )
        )
        if visibility_live_view is not None and hasattr(visibility_live_view, "select_node_by_label"):
            visibility_live_view.select_node_by_label(clean_label)
        if visibility_live_view is not None and hasattr(visibility_live_view, "set_synthetic_selection_detail"):
            if clean_label.lower() not in dict(self.__dict__.get("_profile_devices", {})):
                visibility_live_view.set_synthetic_selection_detail(
                    self._visibility_unrecognized_selection_detail(
                        clean_label,
                        visibility_device if isinstance(visibility_device, dict) else {},
                        metrics if isinstance(metrics, dict) else {},
                    )
                )
            else:
                visibility_live_view.set_synthetic_selection_detail(None)

    def _visibility_identity_can_id_text(self, identity_text: object) -> str:
        """
        NAME
            _visibility_identity_can_id_text - Return the device-id segment from one passive identity key when available.
        """
        clean_identity = str(identity_text or NT_VALUE_EMPTY).strip()
        if not clean_identity:
            return NT_VALUE_EMPTY
        parts = [part.strip() for part in clean_identity.split(VIS_IDENTITY_SEPARATOR)]
        if len(parts) < 3:
            return NT_VALUE_EMPTY
        return str(parts[-1] or NT_VALUE_EMPTY).strip()

    def _visibility_unrecognized_selection_detail(
        self,
        label: str,
        visibility_device: Dict[str, Any],
        metrics: Dict[str, Any],
    ) -> Dict[str, str]:
        """
        NAME
            _visibility_unrecognized_selection_detail - Build one synthetic Selection-pane payload for an unrecognized passive row.
        """
        passive_snapshot = build_passive_device_detail_snapshot(
            label,
            passive_result=self.__dict__.get("_latest_passive_result"),
            visibility_device=visibility_device,
            now_s=time.time(),
        )
        identity_text = self._format_visibility_identity(visibility_device)
        return {
            "label": str(label or NT_VALUE_EMPTY).strip() or "--",
            "can_id": self._visibility_identity_can_id_text(identity_text) or "--",
            "presence": passive_snapshot.get("presence", "--") or "--",
            "presence_status": passive_snapshot.get("presenceStatus", VIS_SELECTION_STATUS_UNRECOGNIZED) or VIS_SELECTION_STATUS_UNRECOGNIZED,
            "presence_age": passive_snapshot.get("presenceAge", "--") or "--",
            "presence_source": passive_snapshot.get("presenceSource", "--") or "--",
            "full_probe_bucket": "--",
            "full_probe_age": "--",
            "full_probe_score": "--",
            "full_probe_status": "--",
            "full_probe_message": identity_text or "--",
            "group_member": "--",
            "scope_active": "--",
            "instantiated": "--",
            "lifecycle_state": VIS_SELECTION_STATUS_UNRECOGNIZED,
            "testable": "--",
            "override_active": "--",
            "override_originated": "--",
            "override_failure": "--",
            "not_testable_reason": VIS_SELECTION_REASON_UNRECOGNIZED,
            "last_seen": self._format_visibility_last_seen(metrics),
            "current_a": "--",
            "current_avg_a": "--",
            "current_peak_a": "--",
            "current_nonzero": "--",
            "current_samples": "--",
            "cmd_duty": "--",
            "applied_duty": "--",
            "vel_rpm": "--",
            "position_rot": "--",
            "position_delta_rot": "--",
            "temp_c": "--",
            "selected": VIS_SELECTION_SELECTED_PASSIVE_ONLY,
        }

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
            _on_visibility_row_double_click - Prompt to rename a visibility row from either section.
        """
        widget = _event.widget
        if not isinstance(widget, ttk.Treeview) or self._visibility_provider is None:
            return
        selection = widget.selection()
        if not selection:
            return
        meta = self._visibility_row_meta.get(selection[0], {})
        if bool(meta.get(VIS_ROW_META_UNEXPECTED, False)):
            self._rename_unrecognized_visibility_row(meta)
            return
        self._rename_defined_visibility_row(meta)

    def _rename_unrecognized_visibility_row(self, meta: Dict[str, object]) -> None:
        """
        NAME
            _rename_unrecognized_visibility_row - Rename one passive unrecognized visibility row.
        """
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

    def _rename_defined_visibility_row(self, meta: Dict[str, object]) -> None:
        """
        NAME
            _rename_defined_visibility_row - Rename one defined visibility row in the current local config session.
        """
        old_label = str(meta.get(VIS_ROW_META_LABEL, NT_VALUE_EMPTY)).strip()
        if not old_label:
            return
        new_label = simpledialog.askstring(
            VIS_RENAME_DEFINED_DIALOG_TITLE,
            VIS_RENAME_DEFINED_PROMPT_FMT.format(label=old_label),
            parent=self,
            initialvalue=old_label,
        )
        if new_label is None:
            return
        clean_label = new_label.strip()
        if not clean_label:
            messagebox.showerror(VIS_RENAME_DEFINED_DIALOG_TITLE, VIS_RENAME_EMPTY_TEXT, parent=self)
            return
        existing_labels = {
            str(label).strip().lower()
            for label in self._all_known_config_device_labels()
            if str(label).strip()
        }
        if clean_label.lower() != old_label.lower() and clean_label.lower() in existing_labels:
            messagebox.showerror(VIS_RENAME_DEFINED_DIALOG_TITLE, VIS_RENAME_DUPLICATE_TEXT, parent=self)
            return
        if clean_label.lower() == old_label.lower():
            return
        payload = self._current_materialized_profiles_payload()
        devices = payload.get(KEY_DEVICES)
        profiles = payload.get(KEY_PROFILES)
        if not isinstance(devices, list) or not isinstance(profiles, dict):
            return
        renamed_any = False
        for device in devices:
            if not isinstance(device, dict):
                continue
            device_label = str(device.get(PROFILE_KEY_LABEL, NT_VALUE_EMPTY)).strip()
            if device_label.lower() != old_label.lower():
                continue
            device[PROFILE_KEY_LABEL] = clean_label
            renamed_any = True
        if not renamed_any:
            return
        for profile_payload in profiles.values():
            if not isinstance(profile_payload, dict):
                continue
            profile_devices = profile_payload.get(KEY_PROFILE_DEVICES)
            if not isinstance(profile_devices, list):
                continue
            for index, existing_label in enumerate(list(profile_devices)):
                if str(existing_label).strip().lower() == old_label.lower():
                    profile_devices[index] = clean_label
        _rename_topology_device_refs_in_payload(payload, old_label, clean_label)
        current_path = self._current_profiles_path() if self._has_file_backed_local_config_session() else None
        self._apply_local_config_session(
            payload,
            current_path,
            dirty=True,
            in_memory_only=not self._has_file_backed_local_config_session(),
            output_line=VIS_RENAME_DEFINED_SUCCESS_FMT.format(
                old_label=old_label,
                new_label=clean_label,
            ),
        )
        self._visibility_last_update = 0.0
        self._poll_visibility_snapshot(time.time())

    def _on_visibility_unrecognized_right_click(self, event: tk.Event) -> None:
        """
        NAME
            _on_visibility_unrecognized_right_click - Open the explicit create-device action for one unrecognized visibility row.
        """
        widget = event.widget
        if not isinstance(widget, ttk.Treeview):
            return
        row_id = widget.identify_row(event.y)
        if not row_id:
            return
        widget.selection_set(row_id)
        widget.focus(row_id)
        meta = self._visibility_row_meta.get(row_id, {})
        label = str(meta.get(VIS_ROW_META_LABEL, NT_VALUE_EMPTY)).strip()
        identity_text = str(meta.get(VIS_ROW_META_IDENTITY, NT_VALUE_EMPTY)).strip()
        menu = tk.Menu(self, tearoff=False)
        menu.add_command(
            label=VIS_CREATE_DEVICE_MENU_LABEL,
            command=lambda captured_label=label, captured_identity=identity_text: self._create_device_definition_from_visibility_row(
                captured_label,
                captured_identity,
            ),
        )
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _create_device_definition_from_visibility_item(self, item_id: str) -> None:
        """
        NAME
            _create_device_definition_from_visibility_item - Confirm and stage one in-memory device definition from one unrecognized row.
        """
        meta = self._visibility_row_meta.get(item_id, {})
        self._create_device_definition_from_visibility_row(
            str(meta.get(VIS_ROW_META_LABEL, NT_VALUE_EMPTY)).strip(),
            str(meta.get(VIS_ROW_META_IDENTITY, NT_VALUE_EMPTY)).strip(),
        )

    def _create_device_definition_from_visibility_row(
        self,
        label: str,
        identity_text: str,
    ) -> None:
        """
        NAME
            _create_device_definition_from_visibility_row - Confirm and stage one in-memory device definition from captured visibility-row data.
        """
        profile_name = self._selected_real_profile()
        if not profile_name:
            profile_name = self._ensure_default_profile_for_local_config_session()
            if profile_name:
                self._profile_box.set(profile_name)
                self._last_selected_profile = profile_name
        identity = self._identity_triplet_for_visibility_item(label, identity_text)
        if not identity:
            self._append_output(VIS_CREATE_DEVICE_IDENTITY_MISSING_TEXT)
            return
        device_definition = self._build_pending_unrecognized_device_definition(label, identity)
        device_definition = self._resolve_discovered_device_label_conflict(device_definition)
        if not isinstance(device_definition, dict):
            return
        display = self._format_device_definition_confirmation(device_definition)
        if not messagebox.askyesno(
            VIS_CREATE_DEVICE_DIALOG_TITLE,
            VIS_CREATE_DEVICE_CONFIRM_FMT.format(
                profile=profile_name,
                label=display[PROFILE_KEY_LABEL],
                interface=display[KEY_INTERFACE],
                manufacturer=display[KEY_MANUFACTURER],
                device_type=display[KEY_DEVICE_TYPE],
                device_id=display[KEY_ID],
                model=display[KEY_MODEL],
                logical_type=display[KEY_TYPE],
            ),
            parent=self,
            default=messagebox.NO,
        ):
            return
        pending = self.__dict__.setdefault("_pending_profile_device_definitions", {})
        if not isinstance(pending, dict):
            pending = {}
            self._pending_profile_device_definitions = pending
        profile_pending = pending.setdefault(profile_name, {})
        if not isinstance(profile_pending, dict):
            profile_pending = {}
            pending[profile_name] = profile_pending
        self._config_session_dirty = True
        profile_pending[str(device_definition.get(PROFILE_KEY_LABEL, NT_VALUE_EMPTY)).strip().lower()] = dict(
            device_definition
        )
        self._append_output(
            VIS_CREATE_DEVICE_OUTPUT_FMT.format(
                profile=profile_name,
                label=str(device_definition.get(PROFILE_KEY_LABEL, NT_VALUE_EMPTY)).strip(),
            )
        )
        self._refresh_profile_devices(profile_name)
        self._refresh_test_library_view(profile_name)
        self._visibility_last_update = 0.0
        self._poll_visibility_snapshot(time.time())

    def _format_device_definition_confirmation(
        self, device_definition: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        NAME
            _format_device_definition_confirmation - Format one pending device-definition proposal for confirmation display.
        """
        tags = device_definition.get(KEY_TAGS, [])
        guessed = set(tags) if isinstance(tags, list) else set()

        def _render(key: str, guess_tag: str) -> str:
            value = str(device_definition.get(key, NT_VALUE_EMPTY)).strip() or NT_VALUE_EMPTY
            if guess_tag in guessed:
                return value + VIS_DIALOG_FIELD_GUESS_SUFFIX
            return value

        return {
            PROFILE_KEY_LABEL: _render(PROFILE_KEY_LABEL, VIS_TAG_GUESSED_LABEL),
            KEY_INTERFACE: str(device_definition.get(KEY_INTERFACE, NT_VALUE_EMPTY)).strip() or NT_VALUE_EMPTY,
            KEY_MANUFACTURER: str(device_definition.get(KEY_MANUFACTURER, NT_VALUE_EMPTY)).strip() or NT_VALUE_EMPTY,
            KEY_DEVICE_TYPE: str(device_definition.get(KEY_DEVICE_TYPE, NT_VALUE_EMPTY)).strip() or NT_VALUE_EMPTY,
            KEY_ID: str(device_definition.get(KEY_ID, NT_VALUE_EMPTY)).strip() or NT_VALUE_EMPTY,
            KEY_MODEL: _render(KEY_MODEL, VIS_TAG_GUESSED_MODEL),
            KEY_TYPE: _render(KEY_TYPE, VIS_TAG_GUESSED_TYPE),
        }

    def _on_visibility_row_selected(self, event: tk.Event) -> None:
        """
        NAME
            _on_visibility_row_selected - Update the raw-ID and shared passive CAN detail panes from the selected visibility row.
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
        self._apply_visibility_selection(self._visibility_selected_label)

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

    def _apply_live_topology_lens(self) -> None:
        """
        NAME
            _apply_live_topology_lens - Apply the explicit shared-lens selection to the main live-topology view.
        """
        if self._live_view is None:
            return
        selected = str(self._live_topology_lens_var.get() or LIVE_LENS_DEFAULT).strip()
        lens_key = LIVE_LENS_TOPOLOGY_KEYS.get(selected, TOPOLOGY_LENS_EVIDENCE)
        self._live_view.set_overlay_lens(lens_key)

    def _apply_visibility_mode_toggle(self) -> None:
        """
        NAME
            _apply_visibility_mode_toggle - Compatibility wrapper for older visibility-toggle callers.
        """
        self._live_topology_lens_var.set(LIVE_LENS_OPTION_VISIBILITY)
        self._apply_live_topology_lens()
        if self._visibility_live_view is not None:
            self._visibility_live_view.set_overlay_lens(TOPOLOGY_LENS_VISIBILITY)

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

    def _set_ui_theme_pref(self) -> None:
        """
        NAME
            _set_ui_theme_pref - Persist the selected UI theme and apply it.
        """

        self._ui_theme_name = str(self._ui_theme_var.get() or UI_THEME_DEFAULT)
        self._theme_palette = get_ui_theme_palette(self._ui_theme_name)
        self._save_ui_command_prefs()
        self._apply_ui_theme()

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
                UI_PREFS_KEY_THEME: self._ui_theme_name,
            },
        )

    def _current_theme_palette(self) -> UiThemePalette:
        """
        NAME
            _current_theme_palette - Resolve the active palette with a test-safe fallback.
        """

        palette = self.__dict__.get("_theme_palette")
        if isinstance(palette, UiThemePalette):
            return palette
        theme_name = str(self.__dict__.get("_ui_theme_name", UI_THEME_DEFAULT) or UI_THEME_DEFAULT)
        palette = get_ui_theme_palette(theme_name)
        self.__dict__["_theme_palette"] = palette
        return palette

    def _apply_ui_theme(self) -> None:
        """
        NAME
            _apply_ui_theme - Apply the selected desktop theme to the Tk shell and subviews.
        """

        palette = self._current_theme_palette()
        apply_ttk_theme(self, self._ttk_style, palette)
        self._apply_theme_to_widget(self)
        for menu_name in ("_menubar", "_prefs_menu", "_theme_menu", "_help_menu"):
            menu = getattr(self, menu_name, None)
            if menu is not None:
                menu.configure(
                    background=palette.panel_bg,
                    foreground=palette.text_primary,
                    activebackground=palette.selection_bg,
                    activeforeground=palette.text_primary,
                )
        for view_name in ("_live_view", "_visibility_live_view", "_evidence_live_view"):
            view = getattr(self, view_name, None)
            if view is not None and hasattr(view, "set_theme"):
                view.set_theme(self._ui_theme_name)
        self._apply_output_scope_palette()
        self._apply_header_status_palette()

    def _apply_theme_to_widget(self, widget: tk.Widget) -> None:
        """
        NAME
            _apply_theme_to_widget - Recursively apply theme colors to Tk-native widgets.
        """

        palette = self._current_theme_palette()
        if isinstance(widget, tk.Text):
            background = palette.text_widget_bg
            foreground = palette.text_widget_fg
            if widget is getattr(self, "_test_source_line_numbers", None):
                background = palette.line_number_bg
                foreground = palette.line_number_fg
            widget.configure(
                background=background,
                foreground=foreground,
                insertbackground=palette.text_widget_insert,
                selectbackground=palette.selection_bg,
                highlightbackground=palette.border,
            )
        elif isinstance(widget, tk.Canvas):
            widget.configure(background=palette.canvas_bg, highlightbackground=palette.border)
        elif isinstance(widget, tk.Label):
            widget.configure(background=palette.panel_bg, foreground=palette.text_primary)
        elif isinstance(widget, tk.Frame):
            widget.configure(background=palette.panel_bg, highlightbackground=palette.border)
        for child in widget.winfo_children():
            if isinstance(child, tk.Widget):
                self._apply_theme_to_widget(child)

    def _apply_output_scope_palette(self) -> None:
        """
        NAME
            _apply_output_scope_palette - Refresh the output status card colors for the active theme.
        """

        panel = getattr(self, "_output_scope_panel", None)
        title_label = getattr(self, "_output_scope_title_label", None)
        headline_label = getattr(self, "_output_scope_headline_label", None)
        detail_label = getattr(self, "_output_scope_detail_label", None)
        if panel is None or title_label is None or headline_label is None or detail_label is None:
            return
        palette = self._current_theme_palette()
        background = palette.runnable_neutral_bg
        foreground = palette.runnable_neutral_fg
        panel.configure(bg=background, highlightbackground=palette.runnable_border)
        title_label.configure(bg=background, fg=foreground)
        headline_label.configure(bg=background, fg=foreground)
        detail_label.configure(bg=background, fg=foreground)

    def _apply_header_status_palette(self) -> None:
        """
        NAME
            _apply_header_status_palette - Refresh header status labels for the active theme.
        """

        pending_label = getattr(self, "_pending_label", None)
        status_label = getattr(self, "_status_label", None)
        if pending_label is not None:
            pending_label.configure(foreground=self._current_theme_palette().status_warn_fg)
        if status_label is not None:
            palette = self._current_theme_palette()
            status_label.configure(
                foreground=(
                    palette.status_success_fg
                    if self._tcp_connected
                    else palette.status_error_fg
                )
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

    def _show_can_frame_family_help(self) -> None:
        """
        NAME
            _show_can_frame_family_help - Display advanced passive-CAN frame-family help.
        """
        window = self.__dict__.get(CAN_FRAME_FAMILY_HELP_ATTR)
        if window is not None and window.winfo_exists():
            window.deiconify()
            window.lift()
            window.focus_set()
            return
        window = self._build_can_frame_family_help_window()
        self.__dict__[CAN_FRAME_FAMILY_HELP_ATTR] = window
        window.lift()
        window.focus_set()

    def _build_can_frame_family_help_window(self) -> tk.Toplevel:
        """
        NAME
            _build_can_frame_family_help_window - Build the raw CAN frame-family help popup.
        """
        window = tk.Toplevel(self)
        window.title(CAN_FRAME_FAMILY_HELP_TITLE)
        window.geometry(CAN_FRAME_FAMILY_HELP_GEOMETRY)
        window.minsize(CAN_FRAME_FAMILY_HELP_MIN_WIDTH, CAN_FRAME_FAMILY_HELP_MIN_HEIGHT)
        window.protocol(TK_PROTOCOL_WINDOW_DELETE, window.destroy)

        body = ttk.Frame(window, padding=CAN_FRAME_FAMILY_HELP_PADDING)
        body.pack(fill=VIS_FILL_BOTH, expand=True)
        text_widget = tk.Text(
            body,
            wrap=CAN_FRAME_FAMILY_HELP_WRAP,
            state=CAN_FRAME_FAMILY_HELP_STATE_NORMAL,
        )
        text_widget.pack(side=VIS_PACK_SIDE_LEFT, fill=VIS_FILL_BOTH, expand=True)
        scroll = ttk.Scrollbar(body, command=text_widget.yview)
        scroll.pack(side=VIS_PACK_SIDE_RIGHT, fill=VIS_FILL_Y)
        text_widget.configure(yscrollcommand=scroll.set)
        text_widget.insert(
            CAN_FRAME_FAMILY_HELP_INSERT_END,
            self._build_can_frame_family_help_text(),
        )
        text_widget.configure(state=CAN_FRAME_FAMILY_HELP_STATE_DISABLED)
        return window

    def _build_can_frame_family_help_text(self) -> str:
        """
        NAME
            _build_can_frame_family_help_text - Build user-facing help for passive CAN frame-family evidence.
        """
        return HELP_LINE_SEPARATOR.join(CAN_FRAME_FAMILY_HELP_LINES)

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

        ttk.Label(
            body,
            text=COLOR_KEY_TEXT_HEADER,
            wraplength=400,
            justify="left",
        ).pack(anchor="w", pady=(0, 8))

        self._add_color_key_section(
            body,
            COLOR_KEY_SECTION_RUNTIME,
            [
                (COLOR_KEY_PRESENCE_HIGH, COLOR_KEY_TEXT_RUNTIME_HIGH),
                (COLOR_KEY_PRESENCE_LOW, COLOR_KEY_TEXT_RUNTIME_LOW),
                (COLOR_KEY_PRESENCE_NONE, COLOR_KEY_TEXT_RUNTIME_NONE),
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
            COLOR_KEY_SECTION_EVIDENCE,
            [
                (COLOR_KEY_EVIDENCE_OK, COLOR_KEY_TEXT_EVIDENCE_OK),
                (COLOR_KEY_EVIDENCE_DEGRADED, COLOR_KEY_TEXT_EVIDENCE_DEGRADED),
                (COLOR_KEY_EVIDENCE_FAILED, COLOR_KEY_TEXT_EVIDENCE_FAILED),
                (COLOR_KEY_EVIDENCE_UNKNOWN, COLOR_KEY_TEXT_EVIDENCE_UNKNOWN),
                (COLOR_KEY_EVIDENCE_IDENTITY, COLOR_KEY_TEXT_EVIDENCE_IDENTITY),
            ],
        )
        self._add_color_key_section(
            body,
            COLOR_KEY_SECTION_BASE,
            [
                (COLOR_KEY_BASE_REV, COLOR_KEY_TEXT_BASE_REV),
                (COLOR_KEY_BASE_NI, COLOR_KEY_TEXT_BASE_NI),
                (COLOR_KEY_BASE_ANALYZER, COLOR_KEY_TEXT_BASE_ANALYZER),
            ],
        )
        self._add_color_key_section(
            body,
            COLOR_KEY_SECTION_OVERLAYS,
            [
                (COLOR_KEY_OVERLAY_SELECTED, COLOR_KEY_TEXT_OVERLAY_SELECTED),
                (COLOR_KEY_OVERLAY_GROUP, COLOR_KEY_TEXT_OVERLAY_GROUP),
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
            (HELP_TAB_CAN_VISIBILITY, self._build_can_frame_family_help_text()),
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
        window.resizable(True, True)
        window.protocol("WM_DELETE_WINDOW", window.destroy)

        body = ttk.Frame(window, padding=10)
        body.pack(fill="both", expand=True)
        paned = ttk.Panedwindow(body, orient="horizontal")
        paned.pack(fill="both", expand=True)

        tree_frame = ttk.Frame(paned)
        detail_frame = ttk.Frame(paned)
        paned.add(tree_frame, weight=1)
        paned.add(detail_frame, weight=3)

        tree = ttk.Treeview(tree_frame, show="tree", selectmode="browse")
        tree.pack(side="left", fill="both", expand=True)
        tree_scroll = ttk.Scrollbar(tree_frame, command=tree.yview)
        tree_scroll.pack(side="right", fill="y")
        tree.configure(yscrollcommand=tree_scroll.set)

        text_widget = tk.Text(detail_frame, wrap="word", state="normal")
        text_widget.pack(side="left", fill="both", expand=True)
        detail_scroll = ttk.Scrollbar(detail_frame, command=text_widget.yview)
        detail_scroll.pack(side="right", fill="y")
        text_widget.configure(yscrollcommand=detail_scroll.set)

        topics = dsl_reference_topics()
        topic_map = collect_dsl_reference_topic_map(topics)
        self._test_source_reference_topic_map = topic_map
        self._test_source_reference_tree = tree
        self._test_source_reference_text = text_widget

        def _add_topics(parent_id: str, nodes: List[Dict[str, object]]) -> None:
            for node in nodes:
                topic_id = str(node.get("id", "")).strip()
                title = str(node.get("title", "")).strip()
                if not topic_id or not title:
                    continue
                tree.insert(parent_id, "end", iid=topic_id, text=title, open=True)
                children = node.get("children")
                if isinstance(children, list):
                    _add_topics(topic_id, [child for child in children if isinstance(child, dict)])

        _add_topics("", topics)
        tree.bind("<<TreeviewSelect>>", self._on_test_source_reference_selected)
        if tree.exists(TEST_SOURCE_REFERENCE_OVERVIEW):
            tree.selection_set(TEST_SOURCE_REFERENCE_OVERVIEW)
            tree.focus(TEST_SOURCE_REFERENCE_OVERVIEW)
            self._show_test_source_reference_topic(TEST_SOURCE_REFERENCE_OVERVIEW)
        return window

    def _show_test_source_reference_topic(self, topic_id: str) -> None:
        """
        NAME
            _show_test_source_reference_topic - Render one DSL reference topic into the detail pane.
        """
        topic_map = getattr(self, "_test_source_reference_topic_map", {})
        text_widget = getattr(self, "_test_source_reference_text", None)
        if text_widget is None or not isinstance(topic_map, dict):
            return
        topic = topic_map.get(topic_id)
        if not isinstance(topic, dict):
            return
        text_widget.configure(state="normal")
        text_widget.delete("1.0", "end")
        text_widget.insert("end", render_dsl_reference_detail(topic))
        text_widget.configure(state="disabled")

    def _on_test_source_reference_selected(self, _event=None) -> None:
        """
        NAME
            _on_test_source_reference_selected - Update detail text when the DSL reference tree selection changes.
        """
        tree = getattr(self, "_test_source_reference_tree", None)
        if tree is None:
            return
        selection = tree.selection()
        if not selection:
            return
        self._show_test_source_reference_topic(str(selection[0]))

    def _build_help_text(self) -> str:
        """
        NAME
            _build_help_text - Build the Overview tab text.
        """
        lines = [
            "Purpose:",
            "  Send bringup commands to the roboRIO over the shared REST control session.",
            "",
            "Basics:",
            "  - Select a test from the dropdown to send selectTestByName.",
            "  - Use Actions to print reports or run tests.",
            "  - Output shows ACK/OUT messages from the robot.",
            "  - Live Topology tab shows read-only runtime overlays.",
            "",
            "Connection:",
            "  - Status shows the REST session state to the RIO.",
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
            "  Manage selected profile, config sync, and group-based controlled activation.",
            "",
            "Toggle Profile:",
            "  Switches to the next profile defined in bringup_system.json.",
            "  The active profile controls which CAN IDs and labels the robot expects.",
            "  Use this before group activation so commands target the correct devices.",
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
            "File Menu:",
            "  Open Config... switches the local editing session to another bringup_system.json.",
            "  Save Config writes pending local edits to the current local config path.",
            "  Save Config As... writes the full current config payload to a new path and keeps using it.",
            "",
            "Runtime Activate:",
            "  Instantiates the selected profile through the shared robot runtime.",
            "  Use this when non-Test surfaces need live runtime-owned device handles",
            "  such as PDP/PDH probing or full runtime-state inspection.",
            "",
            "Runtime Deactivate:",
            "  Releases the active runtime profile and instantiated runtime devices.",
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
            "Active Group:",
            "  Group membership determines what Activate Group, manual controls, and tests operate on.",
            "  The main UI now uses a group-based model instead of incremental Add Motor/Add All actions.",
            "",
            "Refresh:",
            "  Reloads the current local config path and updates the dropdown list.",
        ]
        return "\n".join(lines)

    def _refresh_profiles(self) -> None:
        """
        NAME
            _refresh_profiles - Reload profile names from the current local config path.
        """
        self._sync_shared_profiles_path_override()
        payload = self._load_local_profiles_payload()
        self._suppress_host_profile_context_sync = self._is_blank_local_config_payload(payload)
        profile_names = self._profile_names_from_payload(payload)
        profiles = self._selectable_profiles_from_payload(payload)
        current = self._selected_profile_name()
        self._profile_box["values"] = profiles
        if current in profiles:
            self._profile_box.set(current)
        else:
            self._profile_box.set(
                _startup_selected_profile(
                    profile_names,
                    self._ui_auto_select_default_profile,
                    default_profile_name=self._default_profile_name_from_payload(payload),
                )
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
        tests = self._local_runnable_test_names(name) or [PROFILE_NONE]
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
            state = self._local_test_library_state(selected_profile)
            global_names = list(state.get("global_names", []))
            global_runnable_map = dict(state.get("global_runnable_map", {}))
            config_names = list(state.get("config_names", []))
            profile_names = list(state.get("profile_names", []))
            config_runnable_map = dict(state.get("config_runnable_map", {}))
            runnable_map = dict(state.get("runnable_map", {}))
            test_profile_devices = dict(state.get("test_profile_devices", {}))
            profile_set_name = str(state.get("profile_set_name", "") or "")
        except Exception as exc:
            self._test_profile_devices = {}
            self._replace_test_library_list(self._test_library_global_list, [], "")
            self._replace_test_library_list(self._test_library_config_list, [], "")
            self._replace_test_library_list(self._test_library_profile_list, [], "")
            self._refresh_test_library_available_devices()
            self._test_library_status_var.set(str(exc))
            return
        self._test_profile_devices = self._overlay_pending_profile_device_definitions(
            selected_profile,
            {
            str(label).strip().lower(): entry
            for label, entry in test_profile_devices.items()
            if isinstance(label, str) and label.strip() and isinstance(entry, dict)
            },
        )
        authoritative_selected = self._selected_test_name()
        if authoritative_selected == PROFILE_NONE:
            authoritative_selected = str(
                getattr(self, "_last_ui_selected_test_intent", "") or ""
            ).strip()
        if not authoritative_selected:
            authoritative_selected = str(
                getattr(self, "_last_selected_test", "") or ""
            ).strip()
        if not authoritative_selected:
            authoritative_selected = str(
                getattr(self, "_last_robot_selected_test_name", "") or ""
            ).strip()
        current_global = self._selected_test_library_global_name()
        current_config = self._selected_test_library_config_name()
        current_profile = self._selected_test_library_profile_name()
        if authoritative_selected in profile_names:
            current_profile = authoritative_selected
            current_config = ""
            current_global = ""
        elif authoritative_selected in config_names:
            current_config = authoritative_selected
            current_profile = ""
            current_global = ""
        elif authoritative_selected in global_names:
            current_global = authoritative_selected
            current_profile = ""
            current_config = ""
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
            "  Use this after verifying the selected active group and scope state.",
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
            "  Show the shared topology diagram with an explicit live lens.",
            "",
            "Enable Live Overlay:",
            "  Starts polling runtime state from the roboRIO REST command server.",
            "  Live overlay is read-only and does not send commands.",
            "",
            "Lens:",
            "  - Evidence: interpreted device-state lens shared with the Evidence tab.",
            "  - Runtime: direct runtime/presence lens from robot-local state.",
            "  - CAN Visibility: passive observer visibility lens.",
            "",
            "Show Groups:",
            "  Toggles group boxes/labels from bridgeConfig by-profile groups.",
            "  Useful for visualizing CLI groups in the live view.",
            "",
            "Source:",
            "  - rest: Fetch runtime state from the roboRIO REST server (default).",
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
            "CAN visibility mismatch:",
            "  Start the PC tool: tools\\can_nt\\run_can_nt.cmd --profile <profile>",
            "  Use --channel COMx if auto-detect fails, then compare CAN Bus and CAN Visibility.",
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
        self._fetch_runtime_state_snapshot(show_output=False, log_blocked=False)

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
        self._reset_ui_session_runtime_context()
        self._send_handshake(reset=True, force=True, log=True)

    def _dispatch_host_local_action(self, command: str) -> bool:
        """
        NAME
            _dispatch_host_local_action - Execute a host-local UI action.
        """
        if command == CMD_PRINT_CAN_DIAG:
            self._show_host_can_bus_report()
            return True
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
        if command == CMD_PRINT_CAN_DIAG:
            return bool(self._tcp_connected) and not self._tracker.is_pending()
        if command == HOST_ACTION_RECONNECT_UI_SESSION:
            return not self._tracker.is_pending()
        if command in (HOST_ACTION_DSL_TEST_IMPORT, HOST_ACTION_DSL_TEST_VALIDATE):
            return not self._tracker.is_pending()
        return not self._tracker.is_pending()

    def _show_host_can_bus_report(self) -> None:
        """
        NAME
            _show_host_can_bus_report - Build the host-owned combined CAN bus report.
        """
        if not self._tcp_connected:
            self._append_output(OUTPUT_NOT_CONNECTED)
            return
        if self._tracker.is_pending():
            self._append_output(OUTPUT_BUSY)
            self._append_test_output(OUTPUT_BUSY)
            return
        command_line = f"{timestamp_hms()} CMD {CMD_PRINT_CAN_DIAG}"
        self._append_output(command_line)
        self._append_test_output(command_line)
        report = build_host_can_bus_report(self._session, self._visibility_provider)
        for line in report.splitlines():
            self._append_output(line)
            self._append_test_output(line)

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
        if str(command or "").strip().lower() == CMD_SHOW_RUNTIME_STATE.lower():
            self._show_runtime_state_from_ui()
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
        return self._selected_test_scope_state().inactive_reason

    def _selected_test_name(self) -> str:
        """
        NAME
            _selected_test_name - Return the current selected-test name or PROFILE_NONE.
        """
        selected_test_var = self.__dict__.get("_selected_test_var")
        if selected_test_var is None or not hasattr(selected_test_var, "get"):
            return PROFILE_NONE
        name = str(selected_test_var.get() or "").strip()
        return name if name else PROFILE_NONE

    def _tests_active_group_scope_active(self) -> bool:
        """
        NAME
            _tests_active_group_scope_active - Return whether the Tests-tab scope rows should render as active.
        """
        if self._scope_context_kind() == GROUP_SOURCE_SELECTED_TEST:
            return self._scope_is_currently_active()
        return self._active_group_is_currently_active()

    def _tests_active_group_member_row_states(self) -> List[ActiveGroupMemberRowState]:
        """
        NAME
            _tests_active_group_member_row_states - Return shared Selected Test Devices row states.
        """
        return resolve_tests_active_group_member_rows(
            rows=list(self.__dict__.get("_tests_active_group_rows", [])),
            runtime_state_by_label=dict(self.__dict__.get("_latest_runtime_devices", {})),
            scope_active=self._tests_active_group_scope_active(),
        )

    def _selected_test_scope_state(self) -> SelectedTestScopeState:
        """
        NAME
            _selected_test_scope_state - Return the shared selected-test readiness state.
        """
        selected_name = self._selected_test_name()
        loaded_to_robot = self.__dict__.get("_tests_active_group_loaded_to_robot")
        derived_loaded_to_robot = self._selected_test_required_membership_loaded_to_robot()
        if derived_loaded_to_robot is not None and not (
            loaded_to_robot is True and derived_loaded_to_robot is False
        ):
            loaded_to_robot = derived_loaded_to_robot
            self._tests_active_group_loaded_to_robot = derived_loaded_to_robot
        return resolve_selected_test_scope_state(
            selected_name=selected_name,
            active_group_rows=list(self.__dict__.get("_tests_active_group_rows", [])),
            runtime_block_reason=self._test_runtime_block_reason(),
            scope_active=self._scope_is_currently_active(),
            loaded_to_robot=loaded_to_robot,
            selected_row=self._selected_test_row(selected_name),
        )

    def _selected_test_panel_state(self) -> SelectedTestPanelState:
        """
        NAME
            _selected_test_panel_state - Return shared Tests-tab presentation state for the selected test.
        """
        return resolve_selected_test_panel_state(self._selected_test_scope_state())

    def _test_runtime_block_reason(self) -> str:
        """
        NAME
            _test_runtime_block_reason - Return robot-state blocker text for activation/test execution.
        """
        return resolve_selected_test_runtime_block_reason(
            tcp_connected=bool(self.__dict__.get("_tcp_connected", True)),
            robot_estopped=bool(self.__dict__.get("_robot_estopped_known", False)),
            robot_enabled=bool(self.__dict__.get("_robot_enabled_known", True)),
            robot_mode=str(self.__dict__.get("_robot_mode_known", "") or "").strip().lower(),
        )

    def _selected_test_row(self, selected_name: str) -> Optional[Dict[str, Any]]:
        """
        NAME
            _selected_test_row - Return the robot-published metadata row for one selected test.
        """
        tests_table = self.__dict__.get("_tests_table")
        if tests_table is None or not selected_name:
            return None
        total = int(tests_table.getEntry("totalCount").getDouble(0.0))
        rows = tests_table.getSubTable("rows")
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
        return self._selected_test_scope_state().ready

    def _selected_test_running(self) -> bool:
        """
        NAME
            _selected_test_running - Return whether the selected test currently has an active run in progress.
        """
        run_payload = self._latest_test_run_payload()
        run_state = str(run_payload.get("state", "") or "").strip().lower()
        if run_state == "running":
            return True
        table = self.__dict__.get("_tests_table")
        if table is None:
            return False
        try:
            return str(table.getEntry("runState").getString("") or "").strip().lower() == "running"
        except Exception:
            return False

    def _latest_test_run_payload(self) -> Dict[str, Any]:
        """
        NAME
            _latest_test_run_payload - Return the latest raw run payload from /tests/state.
        """
        payload = self.__dict__.get("_latest_tests_state_payload", {})
        if not isinstance(payload, dict):
            return {}
        run_payload = payload.get("run")
        return run_payload if isinstance(run_payload, dict) else {}

    def _format_test_last_samples(self, details: Dict[str, Any]) -> str:
        """
        NAME
            _format_test_last_samples - Format a short last-samples summary for a failed test.
        """
        last_samples = details.get("lastSamples")
        if not isinstance(last_samples, dict) or not last_samples:
            return ""
        parts: List[str] = []
        for key in sorted(last_samples.keys()):
            value = last_samples.get(key)
            parts.append(f"{key}={_format_test_detail_value(value)}")
            if len(parts) >= TEST_FAILURE_SAMPLE_LIMIT:
                break
        return f"{TEST_FAILURE_LAST_SAMPLES_PREFIX} " + ", ".join(parts) if parts else ""

    def _format_test_failure_reason(self, run_payload: Dict[str, Any]) -> str:
        """
        NAME
            _format_test_failure_reason - Build a concise human-readable reason for one failed test run.
        """
        if not isinstance(run_payload, dict):
            return ""
        run_message = str(run_payload.get("message", "") or "").strip()
        details = run_payload.get("details")
        if not isinstance(details, dict):
            return run_message
        requires = details.get("requires")
        if isinstance(requires, list):
            for require in requires:
                if not isinstance(require, dict):
                    continue
                if bool(require.get("satisfied", False)):
                    continue
                require_text = str(require.get("text", "") or "").strip()
                reason = (
                    f"{TEST_FAILURE_REQUIRE_PREFIX} {require_text}"
                    if require_text
                    else TEST_FAILURE_REQUIRE_PREFIX
                )
                sample_value = require.get("sampleValue")
                if sample_value is not None:
                    reason += f" (last={_format_test_detail_value(sample_value)})"
                sample_summary = self._format_test_last_samples(details)
                if sample_summary:
                    reason += f"; {sample_summary}"
                return reason
        signal_fallbacks = details.get("signalSetFallbacks")
        if isinstance(signal_fallbacks, list) and signal_fallbacks:
            fallback = signal_fallbacks[0]
            if isinstance(fallback, dict):
                fallback_text = str(fallback.get("text", "") or fallback.get("id", "") or "").strip()
                if fallback_text:
                    return f"{TEST_FAILURE_SIGNAL_SET_PREFIX} {fallback_text}"
        sample_summary = self._format_test_last_samples(details)
        if run_message and sample_summary:
            return f"{run_message}; {sample_summary}"
        if sample_summary:
            return sample_summary
        return run_message

    def _format_test_success_reason(self, run_payload: Dict[str, Any]) -> str:
        """
        NAME
            _format_test_success_reason - Build a concise human-readable reason for one passed test run.
        """
        if not isinstance(run_payload, dict):
            return ""
        run_status = str(run_payload.get("status", "") or "").strip()
        if run_status:
            return run_status
        run_message = str(run_payload.get("message", "") or "").strip()
        if run_message:
            return run_message
        return str(run_payload.get("test", "") or "").strip()

    def _maybe_log_test_result_detail(self, run_payload: Dict[str, Any], detail: str) -> None:
        """
        NAME
            _maybe_log_test_result_detail - Append one detailed test-result line when a terminal result changes.
        """
        if not isinstance(run_payload, dict):
            return
        run_state = str(run_payload.get("state", "") or "").strip()
        if run_state not in ("passed", "failed", "blocked", "aborted", "interrupted"):
            return
        run_id = int(run_payload.get("runId", 0) or 0)
        run_test = str(run_payload.get("test", "") or "").strip()
        signature = (run_id, run_state, run_test)
        if signature == self.__dict__.get("_last_test_result_signature"):
            return
        self._last_test_result_signature = signature
        if not detail:
            return
        prefix = TEST_SUCCESS_PREFIX if run_state == "passed" else TEST_FAILURE_PREFIX
        line = f"{prefix} {detail}"
        self._append_output(line)
        self._append_test_output(line)

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
            run_payload = self._latest_test_run_payload()
            if run_state == "running" and run_test:
                result_text = f"Last Result: RUNNING - {run_test}"
                result_color = TEST_RESULT_RUNNING_FG
            elif run_state == "passed" and run_test:
                detail = self._format_test_success_reason(run_payload) or run_message or run_test
                display_result = run_result or TEST_RESULT_PASS_PREFIX
                result_text = f"Last Result: {display_result} - {detail}"
                result_color = TEST_RESULT_PASS_FG
                self._maybe_log_test_result_detail(run_payload, detail)
            elif run_state == "failed" and run_test:
                detail = self._format_test_failure_reason(run_payload) or run_message or run_test
                display_result = run_result or "FAIL"
                result_text = f"Last Result: {display_result} - {detail}"
                result_color = TEST_RESULT_FAIL_FG
                self._maybe_log_test_result_detail(run_payload, detail)
            elif run_state in ("blocked", "aborted", "interrupted"):
                detail = self._format_test_failure_reason(run_payload) or run_message or run_test or run_state.upper()
                display_result = run_result or run_state.upper()
                result_text = f"Last Result: {display_result} - {detail}"
                result_color = TEST_RESULT_FAIL_FG
                self._maybe_log_test_result_detail(run_payload, detail)
            elif run_result and run_test:
                result_text = f"Last Result: {run_result} - {run_test}"
                result_color = (
                    TEST_RESULT_PASS_FG
                    if run_result.upper().startswith(TEST_RESULT_PASS_PREFIX)
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
        table = self.__dict__.get("_tests_active_group_table")
        if table is None:
            return
        for item_id in table.get_children():
            table.delete(item_id)
        rows = list(self.__dict__.get("_tests_active_group_rows", []))
        if not rows:
            table.insert(
                "",
                "end",
                values=(
                    TEST_ACTIVE_GROUP_PANEL_EMPTY,
                    TEST_ACTIVE_GROUP_EMPTY_VALUE,
                    TEST_ACTIVE_GROUP_EMPTY_VALUE,
                    TEST_ACTIVE_GROUP_EMPTY_VALUE,
                    TEST_ACTIVE_GROUP_EMPTY_VALUE,
                    TEST_ACTIVE_GROUP_EMPTY_VALUE,
                ),
            )
            return
        for state in self._tests_active_group_member_row_states():
            table.insert(
                "",
                "end",
                values=(
                    state.label,
                    state.enabled_text,
                    state.locked_text,
                    state.instantiated_text,
                    state.scope_active_text,
                    state.note_text,
                ),
            )

    def _refresh_selected_test_scope_status(self) -> None:
        """
        NAME
            _refresh_selected_test_scope_status - Refresh the Tests-tab selected-test readiness label.
        """
        status_var = self.__dict__.get("_selected_test_scope_status_var")
        headline_var = self.__dict__.get("_selected_test_scope_headline_var")
        if status_var is None:
            return
        palette = self._current_theme_palette()
        panel_bg = palette.runnable_neutral_bg
        panel_fg = palette.runnable_neutral_fg
        state = self._selected_test_panel_state()
        if state.level == TEST_SCOPE_PANEL_NEUTRAL_LEVEL:
            status_var.set(state.detail)
            if headline_var is not None:
                headline_var.set(state.headline)
            panel_bg = palette.runnable_neutral_bg
            panel_fg = palette.runnable_neutral_fg
        elif state.level == RUNNABLE_STATE_LEVEL_READY:
            status_var.set(state.detail)
            if headline_var is not None:
                headline_var.set(state.headline)
            panel_bg = palette.runnable_ready_bg
            panel_fg = palette.runnable_ready_fg
        else:
            status_var.set(state.detail)
            if headline_var is not None:
                headline_var.set(state.headline)
            panel_bg = palette.runnable_inactive_bg
            panel_fg = palette.runnable_inactive_fg
        self._apply_selected_test_scope_panel_colors(panel_bg, panel_fg)

    def _format_selected_test_scope_status_detail(self, inactive_reason: str) -> str:
        """
        NAME
            _format_selected_test_scope_status_detail - Convert one internal blocked reason into clearer operator guidance.
        """
        state = SelectedTestScopeState(
            selected_name=PROFILE_NONE,
            inactive_reason=str(inactive_reason or "").strip(),
            ready=not str(inactive_reason or "").strip(),
            headline=TEST_SCOPE_PANEL_READY_HEADLINE if not str(inactive_reason or "").strip() else TEST_SCOPE_PANEL_INACTIVE_HEADLINE,
            detail_reason=str(inactive_reason or "").strip(),
            level=RUNNABLE_STATE_LEVEL_READY if not str(inactive_reason or "").strip() else RUNNABLE_STATE_LEVEL_WARN,
        )
        return resolve_selected_test_panel_state(state).detail

    def _apply_selected_test_scope_panel_colors(self, background: str, foreground: str) -> None:
        """
        NAME
            _apply_selected_test_scope_panel_colors - Apply the current Tests-tab scope status panel colors.
        """
        panel = self.__dict__.get("_selected_test_scope_panel")
        if panel is not None:
            panel.configure(
                bg=background,
                highlightbackground=self._current_theme_palette().runnable_border,
            )
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

    def _current_profiles_path(self) -> Path:
        """
        NAME
            _current_profiles_path - Return the currently loaded config path or the canonical default.
        """
        override = self.__dict__.get("_config_path_override")
        if isinstance(override, Path):
            return override
        return ConfigRepository().canonical_path()

    def _sync_shared_profiles_path_override(self) -> None:
        """
        NAME
            _sync_shared_profiles_path_override - Align shared host-side profile loaders to the current UI config path.
        """
        repository = ConfigRepository()
        current_path = self._current_profiles_path().resolve()
        canonical_path = repository.canonical_path().resolve()
        set_profiles_path_override(None if current_path == canonical_path else current_path)
        reload_profiles()

    def _default_profiles_path(self) -> Path:
        """
        NAME
            _default_profiles_path - Return the canonical bringup_system.json path.
        """
        return ConfigRepository().canonical_path()

    def _profile_names_from_payload(self, payload: Dict[str, object]) -> List[str]:
        """
        NAME
            _profile_names_from_payload - Return sorted profile names from one config payload.
        """
        profiles = payload.get(KEY_PROFILES) if isinstance(payload, dict) else None
        if not isinstance(profiles, dict):
            return []
        return sorted(
            str(name).strip()
            for name in profiles.keys()
            if isinstance(name, str) and str(name).strip()
        )

    def _selectable_profiles_from_payload(self, payload: Dict[str, object]) -> List[str]:
        """
        NAME
            _selectable_profiles_from_payload - Return profile dropdown values for one config payload.
        """
        return [PROFILE_NONE] + self._profile_names_from_payload(payload)

    def _default_profile_name_from_payload(self, payload: Dict[str, object]) -> str:
        """
        NAME
            _default_profile_name_from_payload - Return the payload default profile name when present.
        """
        value = payload.get(KEY_DEFAULT_PROFILE) if isinstance(payload, dict) else None
        if isinstance(value, str) and value.strip():
            return value.strip()
        return ""

    def _is_blank_local_config_payload(self, payload: Dict[str, object]) -> bool:
        """
        NAME
            _is_blank_local_config_payload - Return whether one payload is a truly blank local config session.
        """
        profiles = payload.get(KEY_PROFILES) if isinstance(payload, dict) else None
        if not isinstance(profiles, dict) or profiles:
            return False
        return not self._default_profile_name_from_payload(payload)

    def _load_local_profiles_payload(self) -> Dict[str, object]:
        """
        NAME
            _load_local_profiles_payload - Load the currently selected local bringup_system.json payload.
        """
        override_payload = self.__dict__.get("_local_profiles_payload_override")
        if isinstance(override_payload, dict):
            return override_payload
        path = self._current_profiles_path()
        repository = ConfigRepository()
        canonical_path_getter = getattr(repository, "canonical_path", None)
        load_path_getter = getattr(repository, "load_path", None)
        if (
            callable(canonical_path_getter)
            and path.resolve() == canonical_path_getter().resolve()
        ):
            return repository.load_canonical().to_payload()
        if callable(load_path_getter):
            return load_path_getter(path).to_payload()
        return repository.load_canonical().to_payload()

    def _begin_local_profiles_edit(self) -> ConfigEditSession:
        """
        NAME
            _begin_local_profiles_edit - Open a mutable edit session for the currently selected local bringup config.
        """
        path = self._current_profiles_path()
        repository = ConfigRepository()
        override_payload = self.__dict__.get("_local_profiles_payload_override")
        if isinstance(override_payload, dict):
            return repository.session_for_payload(path, deepcopy(override_payload))
        if path.resolve() == repository.canonical_path().resolve():
            return repository.begin_canonical_edit()
        return repository.begin_path_edit(path)

    def _has_file_backed_local_config_session(self) -> bool:
        """
        NAME
            _has_file_backed_local_config_session - Return whether the current local config session already has a disk path.
        """
        return not bool(self.__dict__.get("_config_session_in_memory_only", False))

    def _clear_local_config_session_overrides(self) -> None:
        """
        NAME
            _clear_local_config_session_overrides - Clear unsaved local-config session override state after load or save.
        """
        self._local_profiles_payload_override = None
        self._config_session_dirty = False
        self._config_session_in_memory_only = False

    def _blank_profiles_payload(self) -> Dict[str, object]:
        """
        NAME
            _blank_profiles_payload - Build one truly empty blank config payload for a new local session.
        """
        return {
            KEY_DEVICES: [],
            KEY_PROFILES: {},
        }

    def _has_pending_local_config_changes(self) -> bool:
        """
        NAME
            _has_pending_local_config_changes - Return whether the local config session has unsaved work.
        """
        pending = self.__dict__.get("_pending_profile_device_definitions", {})
        return bool(self.__dict__.get("_config_session_dirty", False)) or (
            isinstance(pending, dict) and bool(pending)
        )

    def _apply_pending_profile_device_definitions_to_payload(
        self,
        payload: Dict[str, object],
    ) -> Dict[str, object]:
        """
        NAME
            _apply_pending_profile_device_definitions_to_payload - Merge staged in-memory discovered devices into one config payload.
        """
        merged = deepcopy(payload)
        pending = self.__dict__.get("_pending_profile_device_definitions", {})
        if not isinstance(pending, dict) or not pending:
            return merged
        profiles = merged.get(KEY_PROFILES)
        if not isinstance(profiles, dict):
            profiles = {}
            merged[KEY_PROFILES] = profiles
        devices = merged.get(KEY_DEVICES)
        if not isinstance(devices, list):
            devices = []
            merged[KEY_DEVICES] = devices
        existing_by_label = {
            str(entry.get(PROFILE_KEY_LABEL, NT_VALUE_EMPTY)).strip().lower(): entry
            for entry in devices
            if isinstance(entry, dict) and str(entry.get(PROFILE_KEY_LABEL, NT_VALUE_EMPTY)).strip()
        }
        for profile_name, profile_pending in pending.items():
            if not isinstance(profile_pending, dict):
                continue
            profile_payload = profiles.get(profile_name)
            if not isinstance(profile_payload, dict):
                profile_payload = {}
                profiles[profile_name] = profile_payload
            profile_devices = profile_payload.get(KEY_PROFILE_DEVICES)
            if not isinstance(profile_devices, list):
                profile_devices = []
                profile_payload[KEY_PROFILE_DEVICES] = profile_devices
            for device in profile_pending.values():
                if not isinstance(device, dict):
                    continue
                label = str(device.get(PROFILE_KEY_LABEL, NT_VALUE_EMPTY)).strip()
                if not label:
                    continue
                label_key = label.lower()
                if label_key not in existing_by_label:
                    copied = dict(device)
                    devices.append(copied)
                    existing_by_label[label_key] = copied
                if label not in profile_devices:
                    profile_devices.append(label)
        return merged

    def _current_materialized_profiles_payload(self) -> Dict[str, object]:
        """
        NAME
            _current_materialized_profiles_payload - Return the full local config payload including staged discovery edits.
        """
        return self._apply_pending_profile_device_definitions_to_payload(
            self._load_local_profiles_payload()
        )

    def _apply_local_config_session(
        self,
        payload: Dict[str, object],
        path: Optional[Path],
        *,
        dirty: bool,
        in_memory_only: bool,
        output_line: str = NT_VALUE_EMPTY,
    ) -> None:
        """
        NAME
            _apply_local_config_session - Replace the active local config session and refresh profile-dependent UI state.
        """
        repository = ConfigRepository()
        canonical_path = repository.canonical_path().resolve()
        clean_path = path.resolve() if isinstance(path, Path) else None
        current_selected_profile = _normalize_profile_name(self._selected_profile_name())
        self._config_path_override = None if clean_path is None or clean_path == canonical_path else clean_path
        self._local_profiles_payload_override = deepcopy(payload)
        self._config_session_dirty = bool(dirty)
        self._config_session_in_memory_only = bool(in_memory_only)
        self._pending_profile_device_definitions = {}
        self._suppress_host_profile_context_sync = self._is_blank_local_config_payload(payload)
        self._last_profile_mismatch_prompt = None
        self._pending_robot_profile_selection = PROFILE_NONE
        self._sync_shared_profiles_path_override()
        profile_names = self._profile_names_from_payload(payload)
        profiles = self._selectable_profiles_from_payload(payload)
        if current_selected_profile in profile_names:
            selected_profile = current_selected_profile
        else:
            selected_profile = _startup_selected_profile(
                profile_names,
                self._ui_auto_select_default_profile,
                default_profile_name=self._default_profile_name_from_payload(payload),
            )
        self._profile_box["values"] = profiles
        self._profile_box.set(selected_profile)
        self._last_selected_profile = self._selected_profile_name()
        if output_line:
            self._append_output(output_line)
        self._apply_profile_selection(self._selected_profile_name(), reload_views=True)

    def _ensure_default_profile_for_local_config_session(self) -> str:
        """
        NAME
            _ensure_default_profile_for_local_config_session - Ensure one default profile exists for discovery-first local authoring.
        """
        payload = deepcopy(self._load_local_profiles_payload())
        profiles = payload.get(KEY_PROFILES)
        if not isinstance(profiles, dict):
            profiles = {}
            payload[KEY_PROFILES] = profiles
        changed = False
        default_name = self._default_profile_name_from_payload(payload)
        if not default_name or default_name not in profiles:
            default_name = CONFIG_DISCOVERY_DEFAULT_PROFILE
            profile_payload = profiles.get(default_name)
            if not isinstance(profile_payload, dict):
                profile_payload = {}
                profiles[default_name] = profile_payload
            if not isinstance(profile_payload.get(KEY_PROFILE_DEVICES), list):
                profile_payload[KEY_PROFILE_DEVICES] = []
            payload[KEY_DEFAULT_PROFILE] = default_name
            changed = True
        else:
            profile_payload = profiles.get(default_name)
            if isinstance(profile_payload, dict) and not isinstance(profile_payload.get(KEY_PROFILE_DEVICES), list):
                profile_payload[KEY_PROFILE_DEVICES] = []
                changed = True
        devices = payload.get(KEY_DEVICES)
        if not isinstance(devices, list):
            payload[KEY_DEVICES] = []
            changed = True
        if changed:
            self._local_profiles_payload_override = payload
            self._config_session_dirty = True
            self._suppress_host_profile_context_sync = HOST_PROFILE_SYNC_NOT_SUPPRESSED
            self._append_output(CONFIG_CREATE_DEFAULT_PROFILE_FMT.format(profile=default_name))
            profile_names = self._profile_names_from_payload(payload)
            self._profile_box["values"] = self._selectable_profiles_from_payload(payload)
            if default_name in profile_names:
                self._profile_box.set(default_name)
                self._last_selected_profile = default_name
        return default_name

    def _persist_local_profiles_payload(self, payload: Dict[str, object]) -> None:
        """
        NAME
            _persist_local_profiles_payload - Persist a local bringup_system.json payload with canonical sync or explicit-path save semantics.
        """
        if self.__dict__.get("_config_session_in_memory_only", False) or isinstance(
            self.__dict__.get("_local_profiles_payload_override"), dict
        ):
            self._local_profiles_payload_override = deepcopy(payload)
            self._config_session_dirty = True
            return
        repository = ConfigRepository()
        path = self._current_profiles_path()
        if path.resolve() == repository.canonical_path().resolve():
            session = repository.begin_canonical_edit()
            session.to_payload().clear()
            session.to_payload().update(payload)
            session.mark_dirty()
            repository.sync(session)
            return
        session = repository.session_for_payload(path, payload)
        session.to_payload().clear()
        session.to_payload().update(payload)
        session.mark_dirty()
        repository.save(session, path=path)

    def _persist_local_profiles_edit(self, session: ConfigEditSession) -> None:
        """
        NAME
            _persist_local_profiles_edit - Persist a mutable local config edit session through canonical sync or explicit-path save semantics.
        """
        if self.__dict__.get("_config_session_in_memory_only", False) or isinstance(
            self.__dict__.get("_local_profiles_payload_override"), dict
        ):
            self._local_profiles_payload_override = deepcopy(session.to_payload())
            self._config_session_dirty = True
            return
        repository = ConfigRepository()
        path = self._current_profiles_path()
        if path.resolve() == repository.canonical_path().resolve():
            repository.sync(session)
            return
        repository.save(session, path=path)

    def _save_payload_to_config_path(self, payload: Dict[str, object], path: Path) -> Path:
        """
        NAME
            _save_payload_to_config_path - Persist one fully materialized config payload to disk and update the active local session.
        """
        repository = ConfigRepository()
        clean_path = path.expanduser().resolve()
        _repair_missing_topology_nodes_in_payload(payload)
        if clean_path == repository.canonical_path().resolve():
            session = repository.begin_canonical_edit()
            session.to_payload().clear()
            session.to_payload().update(payload)
            session.mark_dirty()
            repository.sync(session)
        else:
            session = repository.session_for_payload(clean_path, payload)
            session.mark_dirty()
            repository.save(session, path=clean_path)
        self._clear_local_config_session_overrides()
        self._pending_profile_device_definitions = {}
        self._config_path_override = None if clean_path == repository.canonical_path().resolve() else clean_path
        return clean_path

    def _save_config_as_from_ui(self) -> bool:
        """
        NAME
            _save_config_as_from_ui - Save the current config payload to an explicit alternate path and keep using that path.
        """
        initial_path = self._current_profiles_path()
        initial_name = initial_path.name if self._has_file_backed_local_config_session() else "bringup_system.json"
        try:
            selected = filedialog.asksaveasfilename(
                title=BUTTON_SAVE_CONFIG_AS,
                initialdir=str(initial_path.parent),
                initialfile=initial_name,
                defaultextension=CONFIG_FILE_DEFAULT_EXTENSION,
                filetypes=CONFIG_FILE_TYPES,
            )
            if not selected:
                self._append_output(CONFIG_SAVE_AS_CANCELLED)
                return False
            payload = self._current_materialized_profiles_payload()
            path = self._save_payload_to_config_path(payload, Path(selected))
        except Exception as exc:
            self._append_output(CONFIG_SAVE_AS_FAILED_FMT.format(error=exc))
            return False
        self._append_output(CONFIG_SAVE_AS_SAVED_FMT.format(path=str(path)))
        self._refresh_profiles()
        return True

    def _save_config_from_ui(self) -> bool:
        """
        NAME
            _save_config_from_ui - Persist staged local config edits into the current bringup config path.
        """
        payload = self._current_materialized_profiles_payload()
        has_pending_changes = self._has_pending_local_config_changes()
        repair_needed = _payload_requires_topology_repair(payload)
        if not has_pending_changes and not repair_needed:
            self._append_output(VIS_SAVE_CONFIG_NO_PENDING_TEXT)
            return True
        if not self._has_file_backed_local_config_session():
            return self._save_config_as_from_ui()
        try:
            path = self._save_payload_to_config_path(
                payload,
                self._current_profiles_path(),
            )
        except Exception as exc:
            self._append_output(VIS_SAVE_CONFIG_FAILED_FMT.format(error=exc))
            return False
        self._pending_profile_device_definitions = {}
        self._append_output(VIS_SAVE_CONFIG_SAVED_FMT.format(path=str(path)))
        self._apply_profile_selection(self._selected_profile_name(), reload_views=True)
        self._visibility_last_update = 0.0
        self._poll_visibility_snapshot(time.time())
        return True

    def _rename_profile_from_ui(self) -> None:
        """
        NAME
            _rename_profile_from_ui - Rename the selected profile in the current local config session.
        """
        payload = deepcopy(self._current_materialized_profiles_payload())
        profiles = payload.get(KEY_PROFILES)
        if not isinstance(profiles, dict) or not profiles:
            self._append_output(CONFIG_RENAME_PROFILE_NO_PROFILES)
            return
        old_name = self._selected_real_profile()
        if not old_name:
            self._append_output(CONFIG_RENAME_PROFILE_NO_SELECTION)
            return
        new_name = simpledialog.askstring(
            CONFIG_RENAME_PROFILE_TITLE,
            CONFIG_RENAME_PROFILE_PROMPT,
            initialvalue=old_name,
            parent=self,
        )
        if new_name is None:
            return
        new_name = str(new_name).strip()
        if not new_name:
            self._append_output(CONFIG_RENAME_PROFILE_EMPTY)
            return
        if new_name == old_name:
            return
        if new_name in profiles:
            self._append_output(CONFIG_RENAME_PROFILE_DUPLICATE)
            return
        rename_profile_payload(payload, old_name, new_name)
        current_path = self._current_profiles_path() if self._has_file_backed_local_config_session() else None
        self._apply_local_config_session(
            payload,
            current_path,
            dirty=True,
            in_memory_only=not self._has_file_backed_local_config_session(),
            output_line=CONFIG_RENAME_PROFILE_SAVED_FMT.format(
                old_name=old_name,
                new_name=new_name,
            ),
        )
        self._profile_box.set(new_name)
        self._last_selected_profile = new_name
        self._apply_profile_selection(new_name, reload_views=True)

    def _discard_pending_local_config_changes(self) -> None:
        """
        NAME
            _discard_pending_local_config_changes - Drop unsaved local config overrides and staged discovery edits.
        """
        self._clear_local_config_session_overrides()
        self._pending_profile_device_definitions = {}

    def _confirm_local_config_session_switch(self) -> bool:
        """
        NAME
            _confirm_local_config_session_switch - Prompt to save, discard, or cancel when leaving a dirty local config session.
        """
        if not self._has_pending_local_config_changes():
            return True
        answer = messagebox.askyesnocancel(
            CONFIG_DIRTY_TITLE,
            CONFIG_DIRTY_PROMPT,
            parent=self,
        )
        if answer is None:
            return False
        if answer:
            if not self._save_config_from_ui():
                self._append_output(CONFIG_DIRTY_SAVE_FAILED)
                return False
            return True
        self._discard_pending_local_config_changes()
        return True

    def _new_blank_config_from_ui(self) -> None:
        """
        NAME
            _new_blank_config_from_ui - Start a new blank local config session in memory or at a chosen file path.
        """
        mode = messagebox.askyesnocancel(
            CONFIG_NEW_BLANK_TITLE,
            CONFIG_NEW_BLANK_PROMPT,
            parent=self,
        )
        if mode is None:
            self._append_output(CONFIG_NEW_BLANK_CANCELLED)
            return
        if not self._confirm_local_config_session_switch():
            return
        payload = self._blank_profiles_payload()
        self._reset_scratch_visibility_state()
        if mode:
            self._apply_local_config_session(
                payload,
                None,
                dirty=True,
                in_memory_only=True,
                output_line=CONFIG_NEW_BLANK_CREATED_IN_MEMORY,
            )
            return
        selected = filedialog.asksaveasfilename(
            title=BUTTON_NEW_BLANK_CONFIG,
            initialdir=str(self._default_profiles_path().parent),
            initialfile="bringup_system.json",
            defaultextension=CONFIG_FILE_DEFAULT_EXTENSION,
            filetypes=CONFIG_FILE_TYPES,
        )
        if not selected:
            self._append_output(CONFIG_NEW_BLANK_CANCELLED)
            return
        try:
            path = self._save_payload_to_config_path(payload, Path(selected))
        except Exception as exc:
            self._append_output(CONFIG_SAVE_AS_FAILED_FMT.format(error=exc))
            return
        self._apply_local_config_session(
            payload,
            path,
            dirty=False,
            in_memory_only=False,
            output_line=CONFIG_NEW_BLANK_CREATED_FMT.format(path=str(path)),
        )

    def _open_config_from_ui(self) -> None:
        """
        NAME
            _open_config_from_ui - Select and load an alternate bringup_system.json for the current UI session.
        """
        selected = filedialog.askopenfilename(
            title=BUTTON_OPEN_CONFIG,
            initialdir=str(self._current_profiles_path().parent),
            filetypes=CONFIG_FILE_TYPES,
        )
        if not selected:
            self._append_output(CONFIG_OPEN_CANCELLED)
            return
        if not self._confirm_local_config_session_switch():
            return
        try:
            path = Path(selected).expanduser().resolve()
            payload = ConfigRepository().load_path(path).to_payload()
        except Exception as exc:
            self._append_output(CONFIG_OPEN_FAILED_FMT.format(error=exc))
            return
        repository = ConfigRepository()
        canonical_path = repository.canonical_path().resolve()
        self._clear_local_config_session_overrides()
        self._config_path_override = None if path == canonical_path else path
        self._pending_profile_device_definitions = {}
        self._apply_local_config_session(
            payload,
            path,
            dirty=False,
            in_memory_only=False,
            output_line=CONFIG_OPENED_FMT.format(path=str(path)),
        )

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
        path = self._current_profiles_path()
        if not self._has_file_backed_local_config_session():
            return (path.parent, "bringup_system.json")
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

    def _append_push_status_line(self, detail: str) -> None:
        """
        NAME
            _append_push_status_line - Append one Push Config progress/status line and flush the UI.
        """
        line = OUTPUT_PUSH_PROGRESS_FMT.format(detail=str(detail or "").strip())
        self._append_output(line)
        self.update_idletasks()

    def _append_profiles_apply_stage_lines(self, payload: Optional[Dict[str, object]]) -> None:
        """
        NAME
            _append_profiles_apply_stage_lines - Append staged profilesApply results from robot JSON.
        """
        if not isinstance(payload, dict):
            return
        for label, key in PROFILES_APPLY_STAGE_KEYS:
            stage_payload = payload.get(key)
            if not isinstance(stage_payload, dict):
                continue
            ok = bool(stage_payload.get("ok", False))
            self._append_output(
                OUTPUT_PUSH_PROGRESS_FMT.format(
                    detail=f"{label}: {'OK' if ok else 'FAILED'}"
                )
            )
            detail = str(stage_payload.get("message", "") or "").strip()
            if detail:
                self._append_output(detail)

    def _runtime_activate_from_ui(self) -> None:
        """
        NAME
            _runtime_activate_from_ui - Activate selected-profile runtime and current UI-owned scope.
        """
        self._activate_runtime_from_ui()

    def _selected_test_membership_change_requires_scope_swap(self) -> bool:
        """
        NAME
            _selected_test_membership_change_requires_scope_swap - Return whether the selected test needs a different active-group membership while a controlled scope is active.
        """
        if self._scope_context_kind() != GROUP_SOURCE_SELECTED_TEST:
            return False
        if self.__dict__.get("_controlled_lifecycle_active_known") is not True:
            return False
        current_labels = {
            str(row.get("label", "")).strip().lower()
            for row in self._runtime_active_group_members()
            if isinstance(row, dict) and bool(row.get("enabled", True)) and str(row.get("label", "")).strip()
        }
        desired_labels = {
            str(row.get("label", "")).strip().lower()
            for row in self._selected_test_required_rows()
            if isinstance(row, dict) and bool(row.get("enabled", True)) and str(row.get("label", "")).strip()
        }
        if not desired_labels:
            return False
        return not desired_labels.issubset(current_labels)

    def _selected_test_required_membership_loaded_to_robot(self) -> Optional[bool]:
        """
        NAME
            _selected_test_required_membership_loaded_to_robot - Return whether the current active-group membership already contains all devices required by the selected test.
        """
        if not bool(self.__dict__.get("_tcp_connected", False)):
            return None
        current_labels = {
            str(row.get("label", "")).strip().lower()
            for row in self._runtime_active_group_members()
            if isinstance(row, dict) and bool(row.get("enabled", True)) and str(row.get("label", "")).strip()
        }
        desired_labels = {
            str(row.get("label", "")).strip().lower()
            for row in self._selected_test_required_rows()
            if isinstance(row, dict) and bool(row.get("enabled", True)) and str(row.get("label", "")).strip()
        }
        if not desired_labels:
            return None
        return desired_labels.issubset(current_labels)

    def _runtime_deactivate_from_ui(self) -> None:
        """
        NAME
            _runtime_deactivate_from_ui - Deactivate selected-profile runtime and current UI-owned scope.
        """
        if not self._tcp_connected:
            self._append_output(OUTPUT_NOT_CONNECTED)
            return
        if self._tracker.is_pending():
            self._append_output(OUTPUT_BUSY)
            return
        self._append_output(f"{timestamp_hms()} {OUTPUT_RUNTIME_DEACTIVATE}")
        self._last_cmd = (CMD_RUNTIME_DEACTIVATE, {})
        seq = send_tracked_command(
            self._session,
            self._tracker,
            CMD_RUNTIME_DEACTIVATE,
            {},
            sender=lambda session, _command_name, _command_args: runtime_deactivate(
                session
            ),
            now=time.time(),
        )
        if seq is not None:
            self._last_sent_seq = seq

    def _show_runtime_state_from_ui(self) -> None:
        """
        NAME
            _show_runtime_state_from_ui - Request the runtime-state payload through the top-bar control.
        """
        self._append_output(f"{timestamp_hms()} {OUTPUT_RUNTIME_STATE_FETCH}")
        self._last_cmd = (CMD_SHOW_RUNTIME_STATE, {"source": "rest_runtime_state"})
        self._fetch_runtime_state_snapshot(show_output=True, log_blocked=True)

    def _runtime_state_fetch_state(self) -> RuntimeStateFetchState:
        """
        NAME
            _runtime_state_fetch_state - Return the shared runtime-state fetch gate for the current UI session.
        """
        tracker = self.__dict__.get("_tracker")
        tracker_pending = bool(tracker.is_pending()) if tracker is not None else False
        return resolve_runtime_state_fetch_state(
            tcp_connected=bool(self._tcp_connected),
            handshake_done=bool(self._handshake_done),
            tracker_pending=tracker_pending,
            log_poll_inflight=bool(self._log_poll_inflight),
        )

    def _fetch_runtime_state_snapshot(
        self,
        *,
        show_output: bool,
        log_blocked: bool,
    ) -> bool:
        """
        NAME
            _fetch_runtime_state_snapshot - Fetch and apply runtime-state JSON through the shared REST runtime path.
        """
        fetch_state = self._runtime_state_fetch_state()
        if not fetch_state.allowed:
            if log_blocked and fetch_state.blocked_reason:
                self._append_output(fetch_state.blocked_reason)
            return False
        runtime_snapshot = self._session.fetch_runtime_state()
        if not isinstance(runtime_snapshot, dict) or not runtime_snapshot:
            if log_blocked:
                self._append_output(OUTPUT_RUNTIME_STATE_FETCH_EMPTY)
            return False
        self._runtime_state_pending_seq = None
        self._runtime_state_pending_at = 0.0
        self._apply_runtime_state_payload(runtime_snapshot)
        if show_output:
            self._append_output(f"{timestamp_hms()} {OUTPUT_RUNTIME_STATE_FETCH_OUT}")
            self._append_output(f"  json: {json.dumps(runtime_snapshot)}")
        return True

    def _selected_activation_membership_mode(self) -> str:
        """
        NAME
            _selected_activation_membership_mode - Return the current top-bar activation membership mode.
        """
        mode_var = self.__dict__.get("_activation_membership_mode_var")
        raw_mode = str(mode_var.get() if mode_var is not None else "" or "").strip().upper()
        if raw_mode in ACTIVATION_MEMBERSHIP_MODE_VALUES:
            return raw_mode
        return ACTIVATION_MEMBERSHIP_MODE_DEFAULT

    def _activate_scope_from_ui(self) -> None:
        """
        NAME
            _activate_scope_from_ui - Activate the current scope from the current context.
        """
        if not self._tcp_connected:
            self._append_output(OUTPUT_NOT_CONNECTED)
            return
        if self._tracker.is_pending():
            self._append_output(OUTPUT_BUSY)
            return
        membership_mode = self._selected_activation_membership_mode()
        if self._scope_context_kind() == GROUP_SOURCE_SELECTED_TEST:
            args = {
                PROFILE_KEY_LABEL: GROUP_ACTIVE_NAME,
                KEY_COMMAND_MODE: LIFECYCLE_DEFAULT_MODE,
                KEY_COMMAND_MEMBERSHIP_MODE: membership_mode,
            }
            if self._selected_test_membership_change_requires_scope_swap():
                self._append_output(TEST_SCOPE_DETAIL_SCOPE_SWAP_REQUIRED)
                return
            required_loaded = self._selected_test_required_membership_loaded_to_robot()
            if required_loaded is False:
                self._load_selected_test_into_active_group(force_replace=True)
                required_loaded = self.__dict__.get("_tests_active_group_loaded_to_robot")
                if required_loaded is not True:
                    required_loaded = self._selected_test_required_membership_loaded_to_robot()
                if required_loaded is not True:
                    self._append_output(TEST_SCOPE_DETAIL_REQUIRED_UNAVAILABLE)
                    return
            self._append_output(
                f"{timestamp_hms()} {OUTPUT_LIFECYCLE_ACTIVATE_FMT.format(label=GROUP_ACTIVE_NAME, mode=LIFECYCLE_DEFAULT_MODE, membership_mode=membership_mode)}"
            )
            self._last_cmd = (CMD_LIFECYCLE_ACTIVATE, args)
            seq = send_tracked_command(
                self._session,
                self._tracker,
                CMD_LIFECYCLE_ACTIVATE,
                args,
                sender=lambda session, _command_name, _command_args: lifecycle_activate(
                    session,
                    GROUP_ACTIVE_NAME,
                    LIFECYCLE_DEFAULT_MODE,
                    membership_mode,
                ),
                now=time.time(),
            )
            if seq is not None:
                self._last_sent_seq = seq
            return
        mode = LIFECYCLE_DEFAULT_MODE
        label = GROUP_ACTIVE_NAME
        args = {
            PROFILE_KEY_LABEL: label,
            KEY_COMMAND_MODE: mode,
            KEY_COMMAND_MEMBERSHIP_MODE: membership_mode,
        }
        self._append_output(
            f"{timestamp_hms()} {OUTPUT_LIFECYCLE_ACTIVATE_FMT.format(label=label, mode=mode, membership_mode=membership_mode)}"
        )
        self._last_cmd = (CMD_LIFECYCLE_ACTIVATE, args)
        seq = send_tracked_command(
            self._session,
            self._tracker,
            CMD_LIFECYCLE_ACTIVATE,
            args,
            sender=lambda session, _command_name, _command_args: lifecycle_activate(
                session, label, mode, membership_mode
            ),
            now=time.time(),
        )
        if seq is not None:
            self._last_sent_seq = seq

    def _activate_runtime_from_ui(self) -> None:
        """
        NAME
            _activate_runtime_from_ui - Activate the robot runtime path for the current UI-owned scope.

        DESCRIPTION
            The top-bar Runtime Activate action must exercise the robot-side
            runtimeActivate command because that command rebuilds/stages the
            selected profile before activating the shared active-group scope.
            Direct lifecycle activation is reserved for lower-level lifecycle
            helpers.
        """
        if not self._tcp_connected:
            self._append_output(OUTPUT_NOT_CONNECTED)
            return
        if self._tracker.is_pending():
            self._append_output(OUTPUT_BUSY)
            return
        membership_mode = self._selected_activation_membership_mode()
        if self._scope_context_kind() == GROUP_SOURCE_SELECTED_TEST:
            if self._selected_test_membership_change_requires_scope_swap():
                self._append_output(TEST_SCOPE_DETAIL_SCOPE_SWAP_REQUIRED)
                return
            required_loaded = self._selected_test_required_membership_loaded_to_robot()
            if required_loaded is False:
                self._load_selected_test_into_active_group(force_replace=True)
                required_loaded = self.__dict__.get("_tests_active_group_loaded_to_robot")
                if required_loaded is not True:
                    required_loaded = self._selected_test_required_membership_loaded_to_robot()
                if required_loaded is not True:
                    self._append_output(TEST_SCOPE_DETAIL_REQUIRED_UNAVAILABLE)
                    return
        profile_name = self._selected_real_profile()
        args = {}
        if profile_name:
            args[KEY_NAME] = profile_name
        args[KEY_COMMAND_MEMBERSHIP_MODE] = membership_mode
        self._append_output(
            f"{timestamp_hms()} {OUTPUT_RUNTIME_ACTIVATE_FMT.format(profile=profile_name)}"
        )
        self._last_cmd = (CMD_RUNTIME_ACTIVATE, args)
        seq = send_tracked_command(
            self._session,
            self._tracker,
            CMD_RUNTIME_ACTIVATE,
            args,
            sender=lambda session, _command_name, _command_args: runtime_activate(
                session,
                profile_name,
                membership_mode,
            ),
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
            _deactivate_scope_from_ui - Deactivate the current scope session from the top bar.
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
        self._last_cmd = (CMD_LIFECYCLE_DEACTIVATE_ACTIVE, {})
        seq = send_tracked_command(
            self._session,
            self._tracker,
            CMD_LIFECYCLE_DEACTIVATE_ACTIVE,
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
        self._last_cmd = (CMD_LIFECYCLE_DEACTIVATE_ACTIVE, {})
        seq = send_tracked_command(
            self._session,
            self._tracker,
            CMD_LIFECYCLE_DEACTIVATE_ACTIVE,
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
        if self._has_pending_local_config_changes():
            if not self._save_config_from_ui():
                if self._config_session_in_memory_only:
                    self._append_output(CONFIG_PUSH_SAVE_FIRST_CANCELLED)
                else:
                    self._append_output(CONFIG_PUSH_SAVE_FIRST_FAILED)
                return
        selected = str(self._current_profiles_path())

        def _operation() -> object:
            return push_config(
                self._session,
                selected,
                profile_name,
                status_callback=self._append_push_status_line,
            )

        result = self._run_blocking_status_operation(
            OUTPUT_PUSH_START_FMT.format(path=selected, profile=profile_name),
            _operation,
        )
        payload = getattr(result, "payload", None) if result is not None else None
        apply_payload = payload.get("apply") if isinstance(payload, dict) else None
        self._append_profiles_apply_stage_lines(apply_payload)
        message = getattr(result, "message", "") if result is not None else ""
        if result is not None and getattr(result, "ok", lambda: False)():
            self._append_output(OUTPUT_PUSH_SUCCESS)
        else:
            self._append_output(OUTPUT_PUSH_FAILURE)
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

    def _poll_runtime_ui_state(self) -> None:
        """
        NAME
            _poll_runtime_ui_state - Poll REST session/runtime inputs and update output log.
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
                self._reset_ui_session_runtime_context()
                self._robot_ui_session_id = None
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
            self._ui_table = None
            self._tests_table = None
        for event in self._session.poll_events():
            self._handle_tcp_response(event)

        session_snapshot: Dict[str, Any] = {}
        runtime_snapshot: Dict[str, Any] = {}
        tests_snapshot: Dict[str, Any] = {}
        runtime_state_available = False
        if self._tcp_connected:
            session_snapshot = self._session.fetch_session_snapshot()
            runtime_snapshot = self._session.fetch_runtime_state()
            tests_snapshot = self._session.fetch_tests_state()
            fetched_at_ms = time.time() * 1000.0
            self._latest_tests_state_payload = dict(tests_snapshot or {})
            cached_runtime_snapshot = self.__dict__.get("_latest_runtime_state_payload", {})
            if not isinstance(cached_runtime_snapshot, dict):
                cached_runtime_snapshot = {}
            runtime_table_payload: Dict[str, Any] = {}
            if isinstance(runtime_snapshot, dict) and runtime_snapshot:
                runtime_table_payload = dict(runtime_snapshot)
            elif cached_runtime_snapshot:
                runtime_table_payload = dict(cached_runtime_snapshot)
            if runtime_table_payload:
                self._ui_table = _RestTableAdapter.from_runtime_state(
                    session_snapshot,
                    runtime_table_payload,
                    fetched_at_ms=fetched_at_ms,
                )
            self._tests_table = _RestTableAdapter.from_tests_state(tests_snapshot)
            if isinstance(runtime_snapshot, dict) and runtime_snapshot:
                runtime_state_available = True
                self._apply_runtime_state_payload(runtime_snapshot)
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
            if self._robot_selected_profile == _normalize_profile_name(
                self.__dict__.get("_pending_robot_profile_selection", PROFILE_NONE)
            ):
                self._pending_robot_profile_selection = PROFILE_NONE
            self._maybe_send_pending_robot_profile_selection()
            self._sync_diagnostic_profile_context(reload_views=True)
            self._maybe_prompt_host_profile_context_sync()
            nt_connected = self._tcp_connected
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
            current_ui_selected_var = self.__dict__.get("_selected_test_var")
            if current_ui_selected_var is not None and hasattr(
                current_ui_selected_var, "get"
            ):
                current_ui_selected = str(
                    current_ui_selected_var.get() or ""
                ).strip()
            else:
                current_ui_selected = ""
            last_ui_intent = str(
                self.__dict__.get("_last_ui_selected_test_intent", "") or ""
            ).strip()
            robot_selected_changed = selected_name != str(
                self.__dict__.get("_last_robot_selected_test_name", "") or ""
            )
            ui_selection_drifted_from_robot = bool(
                selected_name
                and current_ui_selected != selected_name
                and current_ui_selected != last_ui_intent
            )
            self._last_robot_selected_test_name = selected_name
            if selected_name and (robot_selected_changed or ui_selection_drifted_from_robot):
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
        if not runtime_state_available and self._is_connected is not None:
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
        label = (
            f"REST Connected (rio={self._rio_host})"
            if self._tcp_connected
            else f"REST Disconnected (rio={self._rio_host})"
        )
        self._status_label.configure(
            text=label,
            foreground=(
                self._current_theme_palette().status_success_fg
                if self._tcp_connected
                else self._current_theme_palette().status_error_fg
            ),
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
        self._apply_live_runtime_notice_from_runtime_state(enabled, estopped, stale_state)
        blocked = self._manual_duty_block_message()
        if self._manual_duty_popup is not None:
            if blocked and self._should_confirm_manual_duty_popup_block(blocked, now):
                self._dismiss_manual_duty_popup(
                    f"Manual duty popup closed: {blocked}",
                    stop_motor=True,
                )
            elif not blocked:
                self._clear_manual_duty_block_tracking()
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
        self.after(int(interval * 1000), self._poll_runtime_ui_state)

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
        self._fetch_runtime_state_snapshot(show_output=False, log_blocked=False)

    def _manual_runtime_refresh_active(self) -> bool:
        """
        NAME
            _manual_runtime_refresh_active - Return whether runtime-state polling should run at fast manual-test cadence.
        """
        if self._manual_duty_popup is not None:
            return True
        return bool(self._manual_motion_checks)

    def _clear_manual_duty_block_tracking(self) -> None:
        """
        NAME
            _clear_manual_duty_block_tracking - Clear transient popup auto-close confirmation state.
        """
        self._manual_duty_block_reason = MANUAL_DUTY_BLOCK_REASON_NONE
        self._manual_duty_block_since = 0.0

    def _clear_manual_duty_diag_tracking(self) -> None:
        """
        NAME
            _clear_manual_duty_diag_tracking - Clear last-emitted manual-duty runtime mismatch signatures.
        """
        self._manual_duty_diag_signature_by_label = {}

    def _format_manual_duty_diag_value(self, value: object) -> str:
        """
        NAME
            _format_manual_duty_diag_value - Format one manual-duty diagnostic value for compact logging.
        """
        if isinstance(value, (int, float)):
            return str(round(float(value), MANUAL_DUTY_DIAG_FLOAT_PRECISION))
        clean = str(value or "").strip()
        return clean if clean else MANUAL_DUTY_DIAG_LABEL_NONE

    def _log_manual_duty_runtime_mismatch(self) -> None:
        """
        NAME
            _log_manual_duty_runtime_mismatch - Emit one diagnostic line when runtime duty diverges from the active popup request.
        """
        if self.__dict__.get("_manual_duty_popup") is None:
            self._clear_manual_duty_diag_tracking()
            return
        requested = self.__dict__.get("_manual_duty_last_sent_value")
        if not isinstance(requested, (int, float)):
            self._clear_manual_duty_diag_tracking()
            return
        requested_value = float(requested)
        if abs(requested_value) < MANUAL_DUTY_DIAG_ACTIVE_REQUEST_THRESHOLD:
            self._clear_manual_duty_diag_tracking()
            return
        active_targets = [
            str(target or "").strip().lower()
            for target in list(self.__dict__.get("_manual_duty_targets", []) or [])
            if str(target or "").strip()
        ]
        if not active_targets:
            self._clear_manual_duty_diag_tracking()
            return
        current_signatures: Dict[str, Tuple[object, ...]] = {}
        for target_key in active_targets:
            runtime_device = self._latest_runtime_devices.get(target_key, {})
            if not isinstance(runtime_device, dict):
                continue
            cmd_duty = _runtime_device_field(runtime_device, EVIDENCE_FIELD_CMD_DUTY)
            applied_duty = _runtime_device_field(runtime_device, EVIDENCE_FIELD_APPLIED_DUTY)
            velocity_rpm = _runtime_device_field(runtime_device, EVIDENCE_FIELD_VEL_RPM)
            motor_current = _runtime_device_field(runtime_device, EVIDENCE_FIELD_MOTOR_CURRENT_A)
            lifecycle_state = str(runtime_device.get("lifecycleState", "") or "").strip()
            cmd_mismatch = (
                isinstance(cmd_duty, (int, float))
                and abs(float(cmd_duty) - requested_value) >= MANUAL_DUTY_DIAG_MISMATCH_THRESHOLD
            )
            applied_mismatch = (
                isinstance(applied_duty, (int, float))
                and abs(float(applied_duty) - requested_value) >= MANUAL_DUTY_DIAG_MISMATCH_THRESHOLD
            )
            applied_zero = (
                isinstance(applied_duty, (int, float))
                and abs(float(applied_duty)) <= MANUAL_DUTY_DIAG_ZERO_APPLIED_THRESHOLD
            )
            if not (cmd_mismatch or applied_mismatch or applied_zero):
                continue
            signature = (
                round(requested_value, MANUAL_DUTY_DIAG_FLOAT_PRECISION),
                round(float(cmd_duty), MANUAL_DUTY_DIAG_FLOAT_PRECISION)
                if isinstance(cmd_duty, (int, float))
                else MANUAL_DUTY_DIAG_LABEL_NONE,
                round(float(applied_duty), MANUAL_DUTY_DIAG_FLOAT_PRECISION)
                if isinstance(applied_duty, (int, float))
                else MANUAL_DUTY_DIAG_LABEL_NONE,
                round(float(velocity_rpm), MANUAL_DUTY_DIAG_FLOAT_PRECISION)
                if isinstance(velocity_rpm, (int, float))
                else MANUAL_DUTY_DIAG_LABEL_NONE,
                round(float(motor_current), MANUAL_DUTY_DIAG_FLOAT_PRECISION)
                if isinstance(motor_current, (int, float))
                else MANUAL_DUTY_DIAG_LABEL_NONE,
                lifecycle_state or MANUAL_DUTY_DIAG_LABEL_NONE,
            )
            current_signatures[target_key] = signature
            if self._manual_duty_diag_signature_by_label.get(target_key) == signature:
                continue
            label = str(runtime_device.get("label", "") or "").strip() or target_key
            self._append_output(
                MANUAL_DUTY_DIAG_FMT.format(
                    label=label,
                    requested=self._format_manual_duty_diag_value(signature[0]),
                    cmd=self._format_manual_duty_diag_value(signature[1]),
                    applied=self._format_manual_duty_diag_value(signature[2]),
                    vel=self._format_manual_duty_diag_value(signature[3]),
                    current=self._format_manual_duty_diag_value(signature[4]),
                    lifecycle=self._format_manual_duty_diag_value(signature[5]),
                )
            )
        self._manual_duty_diag_signature_by_label = current_signatures

    def _should_confirm_manual_duty_popup_block(self, blocked_reason: str, now: float) -> bool:
        """
        NAME
            _should_confirm_manual_duty_popup_block - Return whether one poll-time block reason is stable enough to auto-close the popup.
        """
        reason = str(blocked_reason or MANUAL_DUTY_BLOCK_REASON_NONE).strip()
        if not reason:
            self._clear_manual_duty_block_tracking()
            return False
        if reason == MANUAL_DUTY_BLOCKED_TEXT or reason not in MANUAL_DUTY_DEBOUNCED_BLOCK_REASONS:
            self._manual_duty_block_reason = reason
            self._manual_duty_block_since = float(now)
            return True
        previous_reason = str(self.__dict__.get("_manual_duty_block_reason", MANUAL_DUTY_BLOCK_REASON_NONE) or "").strip()
        previous_since = float(self.__dict__.get("_manual_duty_block_since", 0.0) or 0.0)
        if reason != previous_reason:
            self._manual_duty_block_reason = reason
            self._manual_duty_block_since = float(now)
            return False
        if previous_since <= 0.0:
            self._manual_duty_block_since = float(now)
            return False
        return (float(now) - previous_since) >= MANUAL_DUTY_AUTO_CLOSE_CONFIRM_SEC

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
        self._refresh_scope_notice_panel(
            panel_attr="_output_scope_panel",
            title_attr="_output_scope_title_label",
            headline_attr="_output_scope_headline_label",
            detail_attr="_output_scope_detail_label",
            headline_var_attr="_output_scope_headline_var",
            detail_var_attr="_output_scope_detail_var",
        )
        self._refresh_scope_notice_panel(
            panel_attr="_evidence_scope_panel",
            title_attr="_evidence_scope_title_label",
            headline_attr="_evidence_scope_headline_label",
            detail_attr="_evidence_scope_detail_label",
            headline_var_attr="_evidence_scope_headline_var",
            detail_var_attr="_evidence_scope_detail_var",
        )

    def _refresh_scope_notice_panel(
        self,
        *,
        panel_attr: str,
        title_attr: str,
        headline_attr: str,
        detail_attr: str,
        headline_var_attr: str,
        detail_var_attr: str,
    ) -> None:
        """
        NAME
            _refresh_scope_notice_panel - Render one runnable-state panel using the shared host status rules.
        """
        panel = self.__dict__.get(panel_attr)
        headline_var = self.__dict__.get(headline_var_attr)
        detail_var = self.__dict__.get(detail_var_attr)
        if panel is None or headline_var is None or detail_var is None:
            return
        palette = self._current_theme_palette()
        state = self._runnable_scope_state(
            stale_state=bool(self.__dict__.get("_state_stale", False))
        )
        if self._runtime_state_notice_text:
            headline = TEST_SCOPE_PANEL_INACTIVE_HEADLINE
            if self._runtime_state_notice_level == "error":
                bg = palette.runnable_error_bg
                fg = palette.runnable_error_fg
            else:
                bg = palette.runnable_inactive_bg
                fg = palette.runnable_inactive_fg
            detail = self._runtime_state_notice_text
        elif self._runtime_event_notice_text:
            headline = TEST_SCOPE_PANEL_INACTIVE_HEADLINE
            if self._runtime_event_notice_level == "error":
                bg = palette.runnable_error_bg
                fg = palette.runnable_error_fg
            else:
                bg = palette.runnable_inactive_bg
                fg = palette.runnable_inactive_fg
            detail = self._runtime_event_notice_text
        else:
            headline = state.headline
            detail = state.detail
            if state.level == RUNNABLE_STATE_LEVEL_READY:
                bg = palette.runnable_ready_bg
                fg = palette.runnable_ready_fg
            elif state.level == RUNNABLE_STATE_LEVEL_ERROR:
                bg = palette.runnable_error_bg
                fg = palette.runnable_error_fg
            elif state.level == RUNNABLE_STATE_LEVEL_NEUTRAL:
                bg = palette.runnable_neutral_bg
                fg = palette.runnable_neutral_fg
            else:
                bg = palette.runnable_inactive_bg
                fg = palette.runnable_inactive_fg
        headline_var.set(headline)
        detail_var.set(detail)
        panel.configure(bg=bg, highlightbackground=palette.runnable_border)
        for attr_name in (title_attr, headline_attr, detail_attr):
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
        self._maybe_complete_scope_transition_wait(payload)
        self._merge_cached_active_probe_results_into_runtime_devices()
        derived_loaded_to_robot = self._selected_test_required_membership_loaded_to_robot()
        if derived_loaded_to_robot is not None:
            self._tests_active_group_loaded_to_robot = derived_loaded_to_robot
        self._log_manual_duty_runtime_mismatch()
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

    def _apply_live_runtime_notice_from_runtime_state(
        self,
        enabled: bool,
        estopped: bool,
        stale_state: bool,
    ) -> None:
        """
        NAME
            _apply_live_runtime_notice_from_runtime_state - Surface current runtime state directly in Live Topology.
        """
        state = resolve_runnable_scope_state(
            scope_kind=self._runnable_scope_kind(),
            local_selected_profile=self._selected_profile_name(),
            local_profile_required=self.__dict__.get("_profile_box") is not None,
            tcp_connected=bool(self.__dict__.get("_tcp_connected", True)),
            runtime_state_seen=True,
            stale_state=bool(stale_state),
            robot_enabled=bool(enabled),
            robot_estopped=bool(estopped),
            robot_mode=str(self.__dict__.get("_robot_mode_known", "") or "").strip().lower(),
            manual_group_empty=self._manual_active_group_is_empty(),
            scope_active=self._scope_is_currently_active(),
            transition_pending=self._scope_transition_pending(),
        )
        if should_clear_runtime_event_notice(
            self.__dict__.get("_runtime_event_notice_text", NT_VALUE_EMPTY),
            state,
        ):
            self._clear_runtime_event_notice()
            for live_view in self._iter_live_views():
                if hasattr(live_view, "clear_runtime_notice"):
                    live_view.clear_runtime_notice()
        if state.level == "ready":
            self._clear_runtime_state_notice()
        else:
            self._set_runtime_state_notice(state.detail, state.level)
        for live_view in self._iter_live_views():
            if hasattr(live_view, "apply_runnable_scope_state"):
                live_view.apply_runnable_scope_state(state)
                continue
            if state.level == "ready":
                live_view.clear_runtime_state_notice()
            else:
                live_view.set_runtime_state_notice(state.detail, state.level)
        self._sync_live_view_action_states()

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
        if selected_profile == _normalize_profile_name(
            self.__dict__.get("_pending_robot_profile_selection", PROFILE_NONE)
        ):
            self._pending_robot_profile_selection = PROFILE_NONE
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
                "addmotor",
                "addall",
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
            self._begin_scope_transition_wait(runtime_active_expected=True)
            self._clear_runtime_event_notice()
        elif command == "runtimedeactivate" and state == "ok":
            self._begin_scope_transition_wait(runtime_active_expected=False, expected_member_labels=[])
            self._clear_runtime_event_notice()
        elif command == "lifecycleactivate" and state == "ok":
            self._begin_scope_transition_wait(
                controlled_lifecycle_expected=True,
                expected_member_labels=self._current_scope_expected_member_labels(),
            )
            self._clear_runtime_event_notice()
        elif command == "activateselectedtestdevices" and state == "ok":
            self._begin_scope_transition_wait(
                controlled_lifecycle_expected=True,
                expected_member_labels=self._current_scope_expected_member_labels(),
            )
            self._clear_runtime_event_notice()
        elif command in {
            "lifecycledeactivate",
            "lifecycledeactivateactive",
            "deactivateselectedtestdevices",
        } and state == "ok":
            self._begin_scope_transition_wait(
                controlled_lifecycle_expected=False,
                expected_member_labels=[],
            )
            self._clear_runtime_event_notice()

    def _update_action_enabled(self) -> None:
        """
        NAME
            _update_action_enabled - Enable/disable UI actions based on state.
        """
        self._refresh_scope_context_label()
        self._refresh_selected_test_scope_status()
        scope_control_state = self._scope_control_state()
        allow = (
            self._runtime_ui_actions_ready()
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
            activate_scope_button.state(
                ["!disabled"] if scope_control_state.activate_allowed else ["disabled"]
            )
        deactivate_scope_button = getattr(self, "_deactivate_scope_button", None)
        if deactivate_scope_button is not None:
            deactivate_scope_button.state(
                ["!disabled"] if scope_control_state.deactivate_allowed else ["disabled"]
            )
        run_selected_button = getattr(self, "_tests_run_selected_button", None)
        if run_selected_button is not None:
            run_selected_button.state(
                ["!disabled"] if scope_control_state.run_selected_allowed else ["disabled"]
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
            preferred = str(
                getattr(self, "_last_ui_selected_test_intent", "") or ""
            ).strip()
            if not preferred:
                preferred = str(getattr(self, "_last_selected_test", "") or "").strip()
            if not preferred:
                preferred = str(
                    getattr(self, "_last_robot_selected_test_name", "") or ""
                ).strip()
            selected_value = preferred if preferred in values else values[0]
            self._selected_test_var.set(selected_value)
            self._last_selected_test = selected_value

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
            self._sync_selected_test_devices_panel_local(
                loaded_to_robot=self._selected_test_required_membership_loaded_to_robot()
            )
        self._refresh_selected_test_scope_status()

    def _handle_close(self) -> None:
        """
        NAME
            _handle_close - Handle UI close and notify caller.
        """
        if not self._confirm_local_config_session_switch():
            return
        self._dismiss_manual_duty_popup(
            "Manual duty popup closed: UI shutdown.",
            stop_motor=True,
        )
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
