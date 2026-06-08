from __future__ import annotations

"""
NAME
    live_topology_view.py - Read-only topology view with live overlays.

SYNOPSIS
    from tools.can_topology.live_topology_view import LiveTopologyView

DESCRIPTION
    Provides a Tkinter Frame that renders a read-only topology diagram from
    bringup_system.json and applies live runtime-state overlays.
"""

from dataclasses import dataclass
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import tkinter as tk
from tkinter import ttk

from tools.common.json_io import read_json
from tools.common.paths import (
    legacy_profiles_canonical_path,
    profiles_canonical_path,
    repo_root,
)
import tkinter.font as tkfont

from tools.common.profile_constants import (
    KEY_CATEGORY,
    INTERFACE_CAN,
    KEY_DEFAULT_PROFILE,
    KEY_DEVICE_TYPE,
    KEY_DEVICES,
    KEY_ID,
    KEY_INTERFACE,
    KEY_LABEL,
    KEY_LAYOUT,
    KEY_MANUFACTURER,
    KEY_MODEL,
    KEY_NODE_CLASS,
    KEY_OBJECT_TYPE,
    KEY_NODE_TYPE,
    KEY_PROFILES,
    KEY_PROFILE_DEVICES,
    KEY_TOPOLOGY_VIEW,
    get_device_interface,
    get_node_class,
    LAYOUT_KEY_Y,
    NODE_CLASS_INFRASTRUCTURE,
    get_object_type,
)
from tools.config.schema_store import ConfigSchemaStore
from tools.common.topology_render import (
    fill_color_for_vendor,
    outline_color_for_vendor,
    shape_kind_for_category,
    text_color_for_fill,
    vendor_key_for_category,
    CATEGORY_ANALYZER,
)
from tools.common.topology_layout import (
    bus_ys,
    node_box_dims,
    node_box_y,
    node_center_y_unscaled,
    effective_bus_bounds,
)
from tools.common.topology_text import (
    fit_font_size,
    wrap_label_lines,
)
from tools.common.topology_parse import (
    parse_bridge_groups,
    parse_diagram_aux_links,
    parse_diagram_links,
    parse_diagram_nodes,
    topology_profile_from_payload,
)
from tools.common.topology_draw import (
    draw_bus_segments,
    draw_canvas_shape_for_kind,
    draw_group_overlays,
    draw_links,
    render_topology_canvas_common,
)
from tools.common.motor_runtime_verdict import (
    infer_motor_runtime_verdict,
    runtime_motor_attachment,
    RESULT_CONFLICT,
    RESULT_ELECTRICAL,
    RESULT_MISSING,
    RESULT_NOT_COMMANDED,
    RESULT_ROTATING,
    RESULT_STALLED,
)
from tools.can_nt.visibility_constants import (
    VIS_KEY_AVAILABLE,
    VIS_KEY_DEVICES,
    VIS_KEY_ID,
    VIS_KEY_LABEL,
    VIS_KEY_SOURCES,
    VIS_KEY_VISIBILITY,
    VIS_VISIBLE_TRUE,
)

# Constants (presence confidence values and colors).
PRESENCE_CONF_HIGH = "HIGH"
PRESENCE_CONF_LOW = "LOW"
PRESENCE_CONF_NONE = "NONE"
PRESENCE_COLOR_HIGH = "#2f7a2f"
PRESENCE_COLOR_LOW = "#f59e0b"
PRESENCE_COLOR_NONE = "#dc2626"
NOTICE_COLOR_INFO_BG = "#eff6ff"
NOTICE_COLOR_INFO_FG = "#1d4ed8"
NOTICE_COLOR_WARN_BG = "#fff7ed"
NOTICE_COLOR_WARN_FG = "#c2410c"
NOTICE_COLOR_ERROR_BG = "#fef2f2"
NOTICE_COLOR_ERROR_FG = "#b91c1c"
PRESENCE_STALE_MS = 2000
RECENT_SEEN_NOW_MS = 100
RECENT_SEEN_MS_SWITCH = 1000
RECENT_SEEN_SEC_SWITCH = 10000
PRESENCE_MIN_CONF = 0.05
PRESENCE_HIGH_CONF = 0.5
EMPTY_STRING = ""
LEGACY_NODE_TYPE_DIAGRAM = "diagram"
LEGACY_NODE_TYPE_CALLOUT = "callout"
NODE_BOX_BASE_W = 140.0
NODE_BOX_BASE_H = 60.0
SWYFT_PORT_BOX_W = 6.0
SWYFT_PORT_BOX_H = 10.0
SWYFT_PORT_INSET = 12.0
SWYFT_PORT_LINE_HALF_WIDTH = 3.0
SWYFT_PORT_LINE_LEN = 10.0
SWYFT_POWER_LABEL_Y = 10.0
SWYFT_FONT_BASE_PX = 7
POWER_LINE_COLOR = "#c05000"
ATTACH_LINE_COLOR = "#7a5d00"
VIEW_KEY_BUS_CONNECTOR_SIDES = "busConnectorSides"
WIRE_LINE_COLOR = "#1f6feb"
LINK_LINE_WIDTH = 2
LINK_DASH = (6, 4)
CANVAS_FIT_MARGIN = 24.0
CANVAS_PAN_GAIN = 1
ZOOM_MIN = 0.1
ZOOM_MAX = 2.0
ZOOM_STEP = 0.1
SCROLLREGION_FIELD_COUNT = 4
SCROLLREGION_MIN_INDEX = 0
SCROLLREGION_MAX_INDEX = 2
SCROLLREGION_MIN_SPAN = 1.0

# Constants (visibility overlay).
VIS_STATE_ALL = "all"
VIS_STATE_SOME = "some"
VIS_STATE_NONE = "none"
VIS_STATE_UNKNOWN = "unknown"
VIS_COLOR_ALL = "#16a34a"
VIS_COLOR_SOME = "#f59e0b"
VIS_COLOR_NONE = "#dc2626"
VIS_COLOR_UNKNOWN = "#9ca3af"
EVIDENCE_STATE_OK = "ok"
EVIDENCE_STATE_DEGRADED = "degraded"
EVIDENCE_STATE_MISSING = "missing"
EVIDENCE_STATE_UNKNOWN = "unknown"
EVIDENCE_STATE_IDENTITY = "identity"
EVIDENCE_COLOR_OK = "#2f7a2f"
EVIDENCE_COLOR_DEGRADED = "#d97706"
EVIDENCE_COLOR_MISSING = "#dc2626"
EVIDENCE_COLOR_UNKNOWN = "#9ca3af"
EVIDENCE_COLOR_IDENTITY = "#c2410c"
FILTER_CAN = "can"
FILTER_POWER = "power"
FILTER_DIO = "dio"
FILTER_PWM = "pwm"
FILTER_ANALOG = "analog"
FILTER_VIRTUAL = "virtual"
CONNECTION_FILTERS_ORDER = (
    FILTER_CAN,
    FILTER_POWER,
    FILTER_DIO,
    FILTER_PWM,
    FILTER_ANALOG,
    FILTER_VIRTUAL,
)
CONNECTION_FILTER_LABELS = {
    FILTER_CAN: "CAN",
    FILTER_POWER: "Power",
    FILTER_DIO: "DIO",
    FILTER_PWM: "PWM",
    FILTER_ANALOG: "Analog",
    FILTER_VIRTUAL: "Virtual",
}

CATEGORY_NEOS = "neos"
CATEGORY_NEO550S = "neo550s"
CATEGORY_FLEXES = "flexes"
CATEGORY_KRAKENS = "krakens"
CATEGORY_FALCONS = "falcons"
CATEGORY_CANCODERS = "cancoders"
CATEGORY_CANDLES = "candles"
CATEGORY_PDH = "pdh"
CATEGORY_PDP = "pdp"
CATEGORY_PIGEON = "pigeon"
CATEGORY_ROBORIO = "roborio"
CATEGORY_DEVICES = "devices"

VENDOR_CTRE = "CTRE"
VENDOR_REV = "REV"
VENDOR_NI = "NI"

MODEL_NEO_550 = "NEO 550"
MODEL_FLEX = "VORTEX"
MODEL_KRAKEN = "KRAKEN"
MODEL_FALCON = "FALCON"

MFG_NI = 1
MFG_CTRE = 4
MFG_REV = 5

DEVTYPE_ROBORIO = 1
DEVTYPE_MOTOR = 2
DEVTYPE_GYRO = 4
DEVTYPE_ENCODER = 7
DEVTYPE_POWER = 8
DEVTYPE_MISC = 10

NODE_X_STEP = 120.0
NODE_ROW_MOD = 2
NODE_ROW_EVEN = 0
NODE_ROW_ODD = 1
NODE_CAN_ID_DEFAULT = -1
ATTACHMENT_KEY_TYPE = "type"
ATTACHMENT_TYPE_REV_MOTOR = "revMotor"
ATTACHMENT_TYPE_CTRE_MOTOR = "ctreMotor"
ATTACHMENT_TYPE_PRESENCE_CHECK = "presenceCheck"
ATTACHMENT_TYPE_ACTIVE_PRESENCE_PROBE = "activePresenceProbe"
RUNTIME_KEY_MOTOR_CURRENT_A = "motorCurrentA"
RUNTIME_KEY_CURRENT_INSTANT_A = "currentInstantA"
RUNTIME_KEY_CURRENT_AVG_A = "currentAvgA"
RUNTIME_KEY_CURRENT_PEAK_A = "currentPeakA"
RUNTIME_KEY_CURRENT_NONZERO_RATIO = "currentNonzeroRatio"
RUNTIME_KEY_CURRENT_SAMPLE_COUNT = "currentSampleCount"
RUNTIME_KEY_POSITION_ROT = "positionRot"
RUNTIME_CURRENT_DISPLAY_MIN_A = 0.05
RUNTIME_KEY_ACTIVE_PROBE_CODE = "code"
RUNTIME_KEY_ACTIVE_PROBE_STATUS = "status"
RUNTIME_KEY_ACTIVE_PROBE_MESSAGE = "message"
RUNTIME_KEY_ACTIVE_PROBE_BUCKET = "bucket"
RUNTIME_KEY_ACTIVE_PROBE_SCORE = "score"
RUNTIME_KEY_ACTIVE_PROBE_MAX_SCORE = "maxScore"
RUNTIME_KEY_ACTIVE_PROBE_UPDATED_AT_MS = "updatedAtMs"
RUNTIME_KEY_PRESENCE_CHECK_STATUS = "status"
RUNTIME_KEY_PRESENCE_CHECK_SOURCE = "source"
RUNTIME_KEY_PRESENCE_CHECK_UPDATED_AT_MS = "updatedAtMs"
RUNTIME_PROBE_AGE_FRESH_SEC = 15.0
RUNTIME_PROBE_AGE_AGING_SEC = 60.0
RUNTIME_PROBE_AGE_STALE = "stale"
RUNTIME_PROBE_AGE_AGING = "aging"
RUNTIME_PROBE_AGE_FRESH = "fresh"
TITLE_TEXT_DEFAULT = "Live Topology"
SELECTION_FRAME_TEXT = "Selection"
ACTIVE_GROUP_NAME = "active-group"
ACTIVE_GROUP_FRAME_TEXT = "Active Group"
ACTIVE_GROUP_EMPTY_TEXT = "(empty)"
ACTIVE_GROUP_NONE_TEXT = "(not present)"
ACTIVE_GROUP_ELIGIBLE_EMPTY_TEXT = "(no eligible motors)"
ACTIVE_GROUP_RULES_TEXT = "Rules: Active Add appends next created motor in profile order. Active Next rotates the primary member."
ACTIVE_GROUP_MEMBER_ENABLED = "enabled"
ACTIVE_GROUP_MEMBER_DISABLED = "disabled"
ACTIVE_GROUP_MEMBER_ABSENT = "not in group"
ACTIVE_GROUP_PRIMARY_YES = "PRIMARY"
ACTIVE_GROUP_SELECTED_YES = "selected"
ACTIVE_GROUP_SELECTED_NO = "not selected"
ACTIVE_GROUP_ELIGIBLE_DEVICE_TYPE = "2"
ACTIVE_GROUP_PRESENT_PREFIX = "presence="
ACTIVE_GROUP_FULL_PROBE_PREFIX = "fullProbe="
ACTIVE_GROUP_VEL_RPM_PREFIX = "vel="
ACTIVE_GROUP_POSITION_ROT_PREFIX = "position="
ACTIVE_GROUP_POSITION_DELTA_ROT_PREFIX = "delta="
GROUP_INSPECTOR_SUMMARY_NONE = "--"
GROUP_INSPECTOR_MODE_DEVICE = "device"
GROUP_INSPECTOR_MODE_GROUP = "group"
GROUP_INSPECTOR_FRAME_TEXT = "Group Run"
GROUP_INSPECTOR_MODE_PREFIX = "Mode: "
GROUP_INSPECTOR_MODE_MANUAL_DUTY = "manual group duty"
GROUP_INSPECTOR_GROUP_PREFIX = "Group: "
GROUP_INSPECTOR_MEMBERS_PREFIX = "Members: "
GROUP_INSPECTOR_ENABLED_PREFIX = "Enabled: "
GROUP_INSPECTOR_PRIMARY_PREFIX = "Primary: "
GROUP_INSPECTOR_PRESENT_SUMMARY_PREFIX = "Present: "
GROUP_INSPECTOR_ROTATING_SUMMARY_PREFIX = "Rotating: "
GROUP_INSPECTOR_NO_MOTION_SUMMARY_PREFIX = "Commanded no motion: "
GROUP_INSPECTOR_MISSING_SUMMARY_PREFIX = "Missing: "
GROUP_INSPECTOR_CONFLICT_SUMMARY_PREFIX = "Conflict: "
GROUP_INSPECTOR_ROW_PRESENT = "present"
GROUP_INSPECTOR_ROW_MISSING = RESULT_MISSING
GROUP_INSPECTOR_ROW_ROTATING = RESULT_ROTATING
GROUP_INSPECTOR_ROW_NO_MOTION = RESULT_ELECTRICAL
GROUP_INSPECTOR_ROW_ELECTRICAL = RESULT_ELECTRICAL
GROUP_INSPECTOR_ROW_NOT_COMMANDED = RESULT_NOT_COMMANDED
GROUP_INSPECTOR_ROW_CONFLICT = RESULT_CONFLICT
GROUP_INSPECTOR_ROW_STALLED = RESULT_STALLED
GROUP_INSPECTOR_ROW_UNKNOWN = "unknown"
GROUP_INSPECTOR_CMD_DUTY_PREFIX = "cmd="
GROUP_INSPECTOR_APPLIED_DUTY_PREFIX = "applied="
GROUP_INSPECTOR_VEL_RPM_PREFIX = "vel="
GROUP_INSPECTOR_POSITION_ROT_PREFIX = "position="
GROUP_INSPECTOR_POSITION_DELTA_ROT_PREFIX = "delta="
GROUP_INSPECTOR_CURRENT_A_PREFIX = "current="
GROUP_INSPECTOR_FULL_PROBE_BUCKET_PREFIX = "fullProbe="
GROUP_INSPECTOR_RPM_SUFFIX = " rpm"
GROUP_INSPECTOR_CURRENT_SUFFIX = " A"
GROUP_INSPECTOR_ROT_SUFFIX = " rot"
GROUP_INSPECTOR_PRIMARY_MARKER = "PRIMARY"
GROUP_INSPECTOR_TARGET_COUNT_FMT = "{count}/{total}"
GROUP_INSPECTOR_DUTY_THRESHOLD = 0.15
GROUP_INSPECTOR_MOTION_MIN_RPM = 5.0
GROUP_INSPECTOR_MOTION_MIN_POSITION_DELTA_ROT = 0.05
DETAILS_PANEL_INITIAL_WIDTH = 360
DETAILS_PANEL_MIN_WIDTH = 260
SELECTION_FRAME_HEIGHT = 360
ROWS_SCROLL_HEIGHT = 220
ROW_WRAP_MIN = 120
ROW_WRAP_PAD = 36
MANUAL_AUTO_RESULT_RUNNING = "test_running"
MANUAL_AUTO_RESULT_ROTATION = "rotation_detected"
MANUAL_AUTO_RESULT_NO_ROTATION = "no_rotation_detected"
MANUAL_OBSERVATION_LIVE_WINDOW_SEC = 3.0
DETAIL_KEY_LABEL = "label"
DETAIL_KEY_CAN_ID = "can_id"
DETAIL_KEY_PRESENCE = "presence"
DETAIL_KEY_PRESENCE_STATUS = "presence_status"
DETAIL_KEY_PRESENCE_AGE = "presence_age"
DETAIL_KEY_PRESENCE_SOURCE = "presence_source"
DETAIL_KEY_FULL_PROBE_BUCKET = "full_probe_bucket"
DETAIL_KEY_FULL_PROBE_AGE = "full_probe_age"
DETAIL_KEY_FULL_PROBE_SCORE = "full_probe_score"
DETAIL_KEY_FULL_PROBE_STATUS = "full_probe_status"
DETAIL_KEY_FULL_PROBE_MESSAGE = "full_probe_message"
DETAIL_KEY_LIFECYCLE_STATE = "lifecycle_state"
DETAIL_KEY_TESTABLE = "testable"
DETAIL_KEY_OVERRIDE_ACTIVE = "override_active"
DETAIL_KEY_OVERRIDE_ORIGINATED = "override_originated"
DETAIL_KEY_OVERRIDE_FAILURE = "override_failure"
DETAIL_KEY_NOT_TESTABLE_REASON = "not_testable_reason"
DETAIL_KEY_LAST_SEEN = "last_seen"
DETAIL_KEY_CURRENT_A = "current_a"
DETAIL_KEY_CURRENT_AVG_A = "current_avg_a"
DETAIL_KEY_CURRENT_PEAK_A = "current_peak_a"
DETAIL_KEY_CURRENT_NONZERO = "current_nonzero"
DETAIL_KEY_CURRENT_SAMPLES = "current_samples"
DETAIL_KEY_CMD_DUTY = "cmd_duty"
DETAIL_KEY_APPLIED_DUTY = "applied_duty"
DETAIL_KEY_VEL_RPM = "vel_rpm"
DETAIL_KEY_POSITION_ROT = "position_rot"
DETAIL_KEY_POSITION_DELTA_ROT = "position_delta_rot"
DETAIL_KEY_TEMP_C = "temp_c"
DETAIL_KEY_SELECTED = "selected"
DETAIL_TITLE_LABEL = "Label"
DETAIL_TITLE_CAN_ID = "CAN ID"
DETAIL_TITLE_PRESENCE = "Presence"
DETAIL_TITLE_PRESENCE_STATUS = "Presence Status"
DETAIL_TITLE_PRESENCE_AGE = "Presence Age"
DETAIL_TITLE_PRESENCE_SOURCE = "Presence Source"
DETAIL_TITLE_FULL_PROBE_BUCKET = "Full Probe Bucket"
DETAIL_TITLE_FULL_PROBE_AGE = "Full Probe Age"
DETAIL_TITLE_FULL_PROBE_SCORE = "Full Probe Score"
DETAIL_TITLE_FULL_PROBE_STATUS = "Full Probe Status"
DETAIL_TITLE_FULL_PROBE_MESSAGE = "Full Probe Message"
DETAIL_TITLE_LIFECYCLE_STATE = "Lifecycle State"
DETAIL_TITLE_TESTABLE = "Testable"
DETAIL_TITLE_OVERRIDE_ACTIVE = "Override Active"
DETAIL_TITLE_OVERRIDE_ORIGINATED = "Override Originated"
DETAIL_TITLE_OVERRIDE_FAILURE = "Override Failure"
DETAIL_TITLE_NOT_TESTABLE_REASON = "Not Testable Reason"
DETAIL_TITLE_LAST_SEEN = "Last Seen"
DETAIL_TITLE_CURRENT_A = "Current (A)"
DETAIL_TITLE_CURRENT_AVG_A = "Current Avg (A)"
DETAIL_TITLE_CURRENT_PEAK_A = "Current Peak (A)"
DETAIL_TITLE_CURRENT_NONZERO = "Current Nonzero"
DETAIL_TITLE_CURRENT_SAMPLES = "Current Window Samples"
DETAIL_TITLE_CMD_DUTY = "Cmd Duty"
DETAIL_TITLE_APPLIED_DUTY = "Applied Duty"
DETAIL_TITLE_VEL_RPM = "Vel (RPM)"
DETAIL_TITLE_POSITION_ROT = "Position (rot)"
DETAIL_TITLE_POSITION_DELTA_ROT = "Position Delta (rot)"
DETAIL_TITLE_TEMP_C = "Temp (C)"
DETAIL_TITLE_SELECTED = "Selected"


def _runtime_device_field(device: Dict[str, object], key: str) -> object:
    """
    NAME
        _runtime_device_field - Read a runtime-state field from top-level or motor attachments.
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


def _runtime_active_probe_attachment(device: Dict[str, object]) -> Optional[Dict[str, object]]:
    """
    NAME
        _runtime_active_probe_attachment - Return the active-presence attachment when present.
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


def _runtime_presence_check_attachment(device: Dict[str, object]) -> Optional[Dict[str, object]]:
    """
    NAME
        _runtime_presence_check_attachment - Return the live presence-check attachment when present.
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


def _format_elapsed_age(elapsed_sec: float) -> str:
    """
    NAME
        _format_elapsed_age - Format one elapsed age in seconds for compact UI display.
    """
    if elapsed_sec < 0.0:
        elapsed_sec = 0.0
    return f"{elapsed_sec:.1f}s"


def _runtime_probe_age_seconds(device: Dict[str, object]) -> Optional[float]:
    """
    NAME
        _runtime_probe_age_seconds - Return the age in seconds of one cached active probe result.
    """
    attachment = _runtime_active_probe_attachment(device)
    if not isinstance(attachment, dict):
        return None
    updated_at_ms = attachment.get(RUNTIME_KEY_ACTIVE_PROBE_UPDATED_AT_MS)
    if not isinstance(updated_at_ms, (int, float)) or float(updated_at_ms) <= 0.0:
        return None
    return max(0.0, (time.time() * 1000.0 - float(updated_at_ms)) / 1000.0)


def _runtime_probe_age_bucket(device: Dict[str, object]) -> str:
    """
    NAME
        _runtime_probe_age_bucket - Classify one cached active probe result by age.
    """
    age_sec = _runtime_probe_age_seconds(device)
    if not isinstance(age_sec, (int, float)):
        return "--"
    if age_sec <= RUNTIME_PROBE_AGE_FRESH_SEC:
        return RUNTIME_PROBE_AGE_FRESH
    if age_sec <= RUNTIME_PROBE_AGE_AGING_SEC:
        return RUNTIME_PROBE_AGE_AGING
    return RUNTIME_PROBE_AGE_STALE


def _runtime_probe_age_text(device: Dict[str, object]) -> str:
    """
    NAME
        _runtime_probe_age_text - Return compact age text for one cached active probe result.
    """
    age_sec = _runtime_probe_age_seconds(device)
    if not isinstance(age_sec, (int, float)):
        return "not run"
    age_bucket = _runtime_probe_age_bucket(device)
    age_text = _format_elapsed_age(float(age_sec))
    return age_text if age_bucket == RUNTIME_PROBE_AGE_FRESH else f"{age_text} ({age_bucket})"


def _runtime_presence_age_seconds(device: Dict[str, object]) -> Optional[float]:
    """
    NAME
        _runtime_presence_age_seconds - Return the age in seconds of one live presence check.
    """
    attachment = _runtime_presence_check_attachment(device)
    if not isinstance(attachment, dict):
        return None
    updated_at_ms = attachment.get(RUNTIME_KEY_PRESENCE_CHECK_UPDATED_AT_MS)
    if not isinstance(updated_at_ms, (int, float)) or float(updated_at_ms) <= 0.0:
        return None
    return max(0.0, (time.time() * 1000.0 - float(updated_at_ms)) / 1000.0)


def _runtime_presence_age_text(device: Dict[str, object]) -> str:
    """
    NAME
        _runtime_presence_age_text - Return compact age text for one live presence check.
    """
    age_sec = _runtime_presence_age_seconds(device)
    if not isinstance(age_sec, (int, float)):
        return "--"
    return _format_elapsed_age(float(age_sec))


def _manual_observation_is_live(observation: object, now_sec: Optional[float] = None) -> bool:
    """
    NAME
        _manual_observation_is_live - Return whether one cached manual observation should override live runtime telemetry.
    """
    if not isinstance(observation, dict):
        return False
    recorded_at = observation.get("recordedAtEpochSec")
    if not isinstance(recorded_at, (int, float)):
        return False
    current_sec = float(now_sec) if isinstance(now_sec, (int, float)) else time.time()
    return (current_sec - float(recorded_at)) <= MANUAL_OBSERVATION_LIVE_WINDOW_SEC


def _manual_override_value(observation: object, key: str, fallback: object) -> object:
    """
    NAME
        _manual_override_value - Return one cached manual-observation field only when it has a real value.
    """
    if not isinstance(observation, dict) or not key:
        return fallback
    value = observation.get(key)
    return fallback if value is None else value


def _runtime_display_current_a(device: Dict[str, object]) -> object:
    """
    NAME
        _runtime_display_current_a - Choose the most useful current value for display.
    """
    avg_value = _runtime_device_field(device, RUNTIME_KEY_CURRENT_AVG_A)
    peak_value = _runtime_device_field(device, RUNTIME_KEY_CURRENT_PEAK_A)
    instant = _runtime_device_field(device, RUNTIME_KEY_CURRENT_INSTANT_A)
    raw_motor_current = _runtime_device_field(device, RUNTIME_KEY_MOTOR_CURRENT_A)
    if isinstance(avg_value, (int, float)) and float(avg_value) > RUNTIME_CURRENT_DISPLAY_MIN_A:
        return avg_value
    if isinstance(peak_value, (int, float)) and float(peak_value) > RUNTIME_CURRENT_DISPLAY_MIN_A:
        return peak_value
    if isinstance(instant, (int, float)) and float(instant) > RUNTIME_CURRENT_DISPLAY_MIN_A:
        return instant
    if isinstance(raw_motor_current, (int, float)) and float(raw_motor_current) > RUNTIME_CURRENT_DISPLAY_MIN_A:
        return raw_motor_current
    return instant


def _format_last_seen(last_seen_ms: object, now_ms: int) -> str:
    """
    NAME
        _format_last_seen - Render last-seen timestamps as useful recency text.
    """
    if not isinstance(last_seen_ms, (int, float)):
        return "--"
    age_ms = max(0, now_ms - int(last_seen_ms))
    if age_ms <= RECENT_SEEN_NOW_MS:
        return "now"
    if age_ms < RECENT_SEEN_MS_SWITCH:
        return f"{age_ms} ms ago"
    if age_ms < RECENT_SEEN_SEC_SWITCH:
        return f"{age_ms / 1000.0:.1f} s ago"
    return f"{age_ms / 1000.0:.0f} s ago"


@dataclass
class LiveNode:
    """
    NAME
        LiveNode - Minimal node data for read-only rendering.
    """

    key: int
    category: str
    label: str
    can_id: int
    bus_index: int
    row: int
    x: float
    scale: float = 1.0
    vendor: str = ""
    device_type: str = ""
    node_type: str = "device"
    node_class: str = "device"
    y: Optional[float] = None
    free_y: Optional[float] = None
    interface: str = INTERFACE_CAN


RIGHT_CLICK_BUTTON = "<Button-3>"


def _load_profiles_payload() -> Tuple[Optional[Dict[str, object]], str]:
    """
    NAME
        _load_profiles_payload - Load bringup_system.json payload.

    RETURNS
        (payload, error_message).
    """
    payload = _load_profiles_payload_from_store()
    if payload is not None:
        return payload, EMPTY_STRING
    path = profiles_canonical_path()
    if not path.exists():
        path = legacy_profiles_canonical_path()
    if not path.exists():
        return None, f"Profiles file not found at {path}"
    try:
        payload = read_json(path)
    except Exception as exc:
        return None, f"Failed to read profiles file: {exc}"
    if not isinstance(payload, dict):
        return None, "Profiles payload was not a JSON object."
    return payload, EMPTY_STRING


def _load_profiles_payload_from_store() -> Optional[Dict[str, object]]:
    """
    NAME
        _load_profiles_payload_from_store - Load profiles via config store.
    """
    store = ConfigSchemaStore()
    try:
        store.load(repo_root())
    except Exception:
        return None
    payload = store.root_payload()
    profiles = payload.get(KEY_PROFILES)
    if not isinstance(profiles, dict) or not profiles:
        return None
    return payload


def _load_device_registry(payload: Dict[str, object]) -> Dict[str, Dict[str, object]]:
    """
    NAME
        _load_device_registry - Load the label-based device registry.
    """
    registry: Dict[str, Dict[str, object]] = {}
    devices = payload.get(KEY_DEVICES)
    if not isinstance(devices, list):
        return registry
    for entry in devices:
        if not isinstance(entry, dict):
            continue
        label = str(entry.get(KEY_LABEL, "")).strip()
        if not label:
            continue
        registry[label.lower()] = entry
    return registry


def _vendor_for_device(entry: Dict[str, object]) -> str:
    manufacturer = entry.get(KEY_MANUFACTURER)
    if manufacturer == MFG_CTRE:
        return VENDOR_CTRE
    if manufacturer == MFG_REV:
        return VENDOR_REV
    if manufacturer == MFG_NI:
        return VENDOR_NI
    return ""


def _category_for_device(entry: Dict[str, object]) -> str:
    device_type = entry.get(KEY_DEVICE_TYPE)
    manufacturer = entry.get(KEY_MANUFACTURER)
    model = str(entry.get(KEY_MODEL, "")).upper()
    if device_type == DEVTYPE_ROBORIO:
        return CATEGORY_ROBORIO
    if device_type == DEVTYPE_POWER:
        return CATEGORY_PDP if manufacturer == MFG_CTRE else CATEGORY_PDH
    if device_type == DEVTYPE_GYRO:
        return CATEGORY_PIGEON
    if device_type == DEVTYPE_ENCODER:
        return CATEGORY_CANCODERS
    if device_type == DEVTYPE_MISC:
        return CATEGORY_CANDLES if manufacturer == MFG_CTRE else CATEGORY_DEVICES
    if device_type == DEVTYPE_MOTOR:
        if manufacturer == MFG_REV:
            if MODEL_NEO_550 in model:
                return CATEGORY_NEO550S
            if MODEL_FLEX in model:
                return CATEGORY_FLEXES
            return CATEGORY_NEOS
        if manufacturer == MFG_CTRE:
            if MODEL_FALCON in model:
                return CATEGORY_FALCONS
            return CATEGORY_KRAKENS
    return CATEGORY_DEVICES


def _profile_devices(
    raw: Dict[str, object],
    registry: Dict[str, Dict[str, object]],
) -> List[LiveNode]:
    """
    NAME
        _profile_devices - Extract device nodes from a profile payload.
    """
    nodes: List[LiveNode] = []
    if not isinstance(raw, dict):
        return nodes
    labels = raw.get(KEY_PROFILE_DEVICES) if isinstance(raw.get(KEY_PROFILE_DEVICES), list) else []
    key = 1
    for label_entry in labels:
        if not isinstance(label_entry, str):
            continue
        label = label_entry.strip()
        if not label:
            continue
        entry = registry.get(label.lower())
        if not entry or get_device_interface(entry) != INTERFACE_CAN:
            continue
        can_id = entry.get(KEY_ID)
        nodes.append(
            LiveNode(
                key=key,
                category=_category_for_device(entry),
                label=label,
                can_id=int(can_id) if isinstance(can_id, int) else NODE_CAN_ID_DEFAULT,
                bus_index=0,
                row=NODE_ROW_EVEN if key % NODE_ROW_MOD == 0 else NODE_ROW_ODD,
                x=float(key * NODE_X_STEP),
                vendor=_vendor_for_device(entry),
                device_type=str(entry.get(KEY_DEVICE_TYPE) or ""),
                node_type="device",
                interface=str(entry.get(KEY_INTERFACE) or INTERFACE_CAN),
            )
        )
        key += 1
    return nodes


def _diagram_nodes(
    diagram: Dict[str, object],
    registry: Dict[str, Dict[str, object]],
) -> Tuple[List[LiveNode], Dict[str, object]]:
    """
    NAME
        _diagram_nodes - Build nodes from a diagram snapshot.
    """
    nodes: List[LiveNode] = []
    key = 1
    view_dict = diagram.get(KEY_TOPOLOGY_VIEW)
    view_meta = view_dict if isinstance(view_dict, dict) else {}
    raw_bus_offsets = diagram.get("busOffsets")
    if not isinstance(raw_bus_offsets, list):
        raw_bus_offsets = view_meta.get("busOffsets")
    bus_offsets = raw_bus_offsets if isinstance(raw_bus_offsets, list) else []
    for entry in parse_diagram_nodes(diagram):
        if not isinstance(entry, dict):
            continue
        raw_node_type = get_object_type(entry) or "device"
        node_class = str(entry.get(KEY_NODE_CLASS) or get_node_class(entry)).strip() or "device"
        node_type = raw_node_type
        if node_class == NODE_CLASS_INFRASTRUCTURE:
            node_type = LEGACY_NODE_TYPE_DIAGRAM
        if entry.get("profileVisible") is False and node_type != "diagram":
            continue
        if node_type == LEGACY_NODE_TYPE_CALLOUT:
            text = str(entry.get("text") or "")
            if not text:
                continue
            raw_key = entry.get("key")
            node_key = int(raw_key) if isinstance(raw_key, int) else key
            nodes.append(
                LiveNode(
                    key=node_key,
                    category="callout",
                    label=text,
                    can_id=-1,
                    bus_index=int(entry.get("bus") or 0),
                    row=int(entry.get("row") or 0),
                    x=float(entry.get("x") or 0.0),
                    scale=float(entry.get("scale") or 1.0),
                    node_type=LEGACY_NODE_TYPE_CALLOUT,
                    node_class="callout",
                    y=float(entry.get("y")) if isinstance(entry.get("y"), (int, float)) else None,
                )
            )
            key += 1
            continue
        label = str(entry.get("label") or "")
        if not label:
            continue
        bus_index = int(entry.get("bus") or 0)
        free_y = None
        free_val = entry.get("freeY")
        free_rel = entry.get("freeYRelative")
        if isinstance(free_val, (int, float)):
            free_y = float(free_val)
            if not isinstance(free_rel, bool) or free_rel is False:
                bus_offset = float(bus_offsets[bus_index]) if bus_index < len(bus_offsets) else 0.0
                free_y = free_y - bus_offset
        raw_key = entry.get("key")
        node_key = int(raw_key) if isinstance(raw_key, int) else key
        can_id = entry.get("id") if isinstance(entry.get("id"), int) else NODE_CAN_ID_DEFAULT
        registry_entry = registry.get(label.strip().lower())
        if can_id == NODE_CAN_ID_DEFAULT and registry_entry:
            reg_id = registry_entry.get(KEY_ID)
            if isinstance(reg_id, int):
                can_id = reg_id
        category = str(entry.get(KEY_CATEGORY) or CATEGORY_DEVICES)
        vendor = str(entry.get("vendor") or "")
        device_type = str(entry.get(KEY_DEVICE_TYPE) or "")
        if isinstance(registry_entry, dict):
            if category == CATEGORY_DEVICES:
                category = _category_for_device(registry_entry)
            if not vendor:
                vendor = _vendor_for_device(registry_entry)
            if not device_type:
                device_type = str(registry_entry.get(KEY_DEVICE_TYPE) or "")
        interface = str(entry.get(KEY_INTERFACE) or INTERFACE_CAN)
        if isinstance(registry_entry, dict):
            interface = str(registry_entry.get(KEY_INTERFACE) or interface or INTERFACE_CAN)
        nodes.append(
            LiveNode(
                key=node_key,
                category=category,
                label=label,
                can_id=int(can_id) if isinstance(can_id, int) else NODE_CAN_ID_DEFAULT,
                bus_index=bus_index,
                row=int(entry.get("row") or 0),
                x=float(entry.get("x") or 0.0),
                scale=float(entry.get("scale") or 1.0),
                node_type=node_type,
                node_class=node_class,
                free_y=free_y,
                vendor=vendor,
                device_type=device_type,
                interface=interface,
            )
        )
        key += 1
    return nodes, diagram


class LiveTopologyView(ttk.Frame):
    """
    NAME
        LiveTopologyView - Read-only topology canvas with live overlays.
    """

    def __init__(
        self,
        parent: tk.Widget,
        profile_name: str,
        on_node_right_click: Optional[Callable[[LiveNode, tk.Event], None]] = None,
        on_group_right_click: Optional[Callable[[Dict[str, Any], tk.Event], None]] = None,
        on_active_group_member_toggled: Optional[Callable[[str, bool], None]] = None,
        on_override_action: Optional[Callable[[str, str], None]] = None,
        on_left_click: Optional[Callable[[Optional[LiveNode], tk.Event], None]] = None,
        on_selection_changed: Optional[Callable[[Optional[LiveNode]], None]] = None,
        show_selection_panel: bool = True,
        title_text: str = TITLE_TEXT_DEFAULT,
    ) -> None:
        super().__init__(parent)
        self._profile_name = profile_name
        self._title_text = str(title_text or TITLE_TEXT_DEFAULT)
        self._show_selection_panel = bool(show_selection_panel)
        self._nodes: List[LiveNode] = []
        self._diagram_meta: Dict[str, object] = {}
        self._runtime_state: Dict[str, Dict[str, object]] = {}
        self._presence_overrides: Dict[str, str] = {}
        self._visibility_enabled = False
        self._visibility_state: Dict[str, str] = {}
        self._visibility_sources: Dict[str, bool] = {}
        self._evidence_state: Dict[str, str] = {}
        self._visibility_fingerprint: Optional[Tuple[object, ...]] = None
        self._selected_label: Optional[str] = None
        self._selected_enabled: Optional[bool] = None
        self._bus_offsets: List[float] = [0.0]
        self._bus_spacing = 160.0
        self._bus_lefts: List[float] = []
        self._bus_rights: List[float] = []
        self._pan_y = 0.0
        self._zoom = 1.0
        self._node_bounds: Dict[int, Tuple[float, float, float, float]] = {}
        self._group_overlay_regions: List[Dict[str, object]] = []
        self._selected_node: Optional[LiveNode] = None
        self._use_diagram_layout = False
        self._ethernet_links: List[Tuple[int, int]] = []
        self._can_links: List[Dict[str, int]] = []
        self._device_links: List[Dict[str, int]] = []
        self._power_links: List[Tuple[int, int]] = []
        self._attachment_links: List[Tuple[int, int]] = []
        self._dio_links: List[Tuple[int, int]] = []
        self._bridge_groups: List[Dict[str, object]] = []
        self._runtime_groups: List[Dict[str, object]] = []
        self._show_groups = True
        self._runtime_fingerprint: Optional[Tuple[object, ...]] = None
        self._runtime_state_notice_text = EMPTY_STRING
        self._runtime_state_notice_level = "info"
        self._runtime_event_notice_text = EMPTY_STRING
        self._runtime_event_notice_level = "warn"
        self._manual_test_observations: Dict[str, Dict[str, object]] = {}
        self._on_node_right_click_cb = on_node_right_click
        self._on_group_right_click_cb = on_group_right_click
        self._on_active_group_member_toggled_cb = on_active_group_member_toggled
        self._on_override_action_cb = on_override_action
        self._on_left_click_cb = on_left_click
        self._on_selection_changed_cb = on_selection_changed
        self._group_inspector_name = EMPTY_STRING
        self._group_inspector_targets: List[str] = []
        self._selection_inspector_mode = GROUP_INSPECTOR_MODE_DEVICE
        self._group_inspector_row_widgets: Dict[str, Dict[str, object]] = {}
        self._active_group_row_widgets: Dict[str, Dict[str, object]] = {}
        self._active_group_empty_label: Optional[ttk.Label] = None
        self._connection_filter_vars = {
            key: tk.BooleanVar(value=True) for key in CONNECTION_FILTERS_ORDER
        }

        header = ttk.Frame(self)
        header.pack(fill="x", padx=8, pady=(8, 0))
        ttk.Label(header, text=self._title_text, font=("Trebuchet MS", 13)).pack(
            side="left"
        )
        self._status_label = ttk.Label(header, text="Profile: --")
        self._status_label.pack(side="left", padx=(12, 0))
        filter_frame = ttk.Frame(header)
        filter_frame.pack(side="right")
        ttk.Button(filter_frame, text="All", command=self._enable_all_connection_filters).pack(side="left")
        ttk.Button(filter_frame, text="None", command=self._disable_all_connection_filters).pack(side="left", padx=(4, 8))
        for filter_key in CONNECTION_FILTERS_ORDER:
            ttk.Checkbutton(
                filter_frame,
                text=CONNECTION_FILTER_LABELS[filter_key],
                variable=self._connection_filter_vars[filter_key],
                command=self._redraw,
            ).pack(side="left")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=8, pady=8)

        content_pane = ttk.Panedwindow(body, orient="horizontal")
        content_pane.pack(fill="both", expand=True)

        canvas_frame = ttk.Frame(content_pane)
        content_pane.add(canvas_frame, weight=5)
        self._canvas = tk.Canvas(canvas_frame, background="#ffffff", highlightthickness=1)
        self._canvas.pack(side="left", fill="both", expand=True)
        y_scroll = ttk.Scrollbar(canvas_frame, orient="vertical", command=self._canvas.yview)
        y_scroll.pack(side="right", fill="y")
        x_scroll = ttk.Scrollbar(body, orient="horizontal", command=self._canvas.xview)
        x_scroll.pack(side="bottom", fill="x")
        self._canvas.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        self._canvas.bind("<Configure>", self._redraw)
        self._canvas.bind("<Button-1>", self._on_canvas_click)
        self._canvas.bind(RIGHT_CLICK_BUTTON, self._on_canvas_right_click)
        self._canvas.bind("<ButtonPress-2>", self._on_canvas_pan_press)
        self._canvas.bind("<B2-Motion>", self._on_canvas_pan_drag)
        self._canvas.bind("<ButtonRelease-2>", self._on_canvas_pan_release)
        self._canvas.bind("<Control-MouseWheel>", self._on_mousewheel_zoom)
        self._canvas.bind("<Control-Button-4>", lambda _e: self._nudge_zoom(ZOOM_STEP))
        self._canvas.bind("<Control-Button-5>", lambda _e: self._nudge_zoom(-ZOOM_STEP))

        self._detail_vars: Dict[str, tk.StringVar] = {}
        self._active_group_summary_var: Optional[tk.StringVar] = None
        self._active_group_rows_frame: Optional[ttk.Frame] = None
        self._active_group_rows_canvas: Optional[tk.Canvas] = None
        self._active_group_member_vars: Dict[str, tk.BooleanVar] = {}
        self._active_group_member_update_in_progress = False
        if self._show_selection_panel:
            details_container = ttk.Frame(content_pane, width=DETAILS_PANEL_INITIAL_WIDTH)
            content_pane.add(details_container, weight=2)
            details = ttk.LabelFrame(details_container, text=SELECTION_FRAME_TEXT, padding=8)
            details.pack(side="top", fill="x")
            details.configure(height=SELECTION_FRAME_HEIGHT)
            details.pack_propagate(False)
            selection_rows_container = ttk.Frame(details)
            selection_rows_container.pack(fill="both", expand=True)
            selection_rows_canvas = tk.Canvas(
                selection_rows_container,
                highlightthickness=0,
            )
            selection_rows_canvas.pack(side="left", fill="both", expand=True)
            selection_rows_scroll = ttk.Scrollbar(
                selection_rows_container,
                orient="vertical",
                command=selection_rows_canvas.yview,
            )
            selection_rows_scroll.pack(side="right", fill="y")
            selection_rows_canvas.configure(yscrollcommand=selection_rows_scroll.set)
            selection_rows_frame = ttk.Frame(selection_rows_canvas)
            selection_rows_window = selection_rows_canvas.create_window(
                (0, 0), window=selection_rows_frame, anchor="nw"
            )

            def _sync_selection_scrollregion(_event=None) -> None:
                selection_rows_canvas.configure(
                    scrollregion=selection_rows_canvas.bbox("all")
                )

            def _sync_selection_rows_width(_event=None) -> None:
                width = max(int(selection_rows_canvas.winfo_width()), 1)
                selection_rows_canvas.itemconfigure(selection_rows_window, width=width)

            selection_rows_frame.bind("<Configure>", _sync_selection_scrollregion)
            selection_rows_canvas.bind("<Configure>", _sync_selection_rows_width)
            self._detail_device_frame = ttk.Frame(selection_rows_frame)
            self._detail_device_frame.pack(fill="x")
            self._group_inspector_frame = ttk.Frame(selection_rows_frame)
            self._group_inspector_summary_var = tk.StringVar(value=GROUP_INSPECTOR_SUMMARY_NONE)
            ttk.Label(
                self._group_inspector_frame,
                textvariable=self._group_inspector_summary_var,
                justify="left",
                anchor="nw",
            ).pack(fill="x")
            self._group_inspector_rows_frame = ttk.Frame(self._group_inspector_frame)
            self._group_inspector_rows_frame.pack(fill="x", pady=(8, 0))
            self._detail_vars = {
                DETAIL_KEY_LABEL: tk.StringVar(value="--"),
                DETAIL_KEY_CAN_ID: tk.StringVar(value="--"),
                DETAIL_KEY_PRESENCE: tk.StringVar(value="--"),
                DETAIL_KEY_PRESENCE_STATUS: tk.StringVar(value="--"),
                DETAIL_KEY_PRESENCE_AGE: tk.StringVar(value="--"),
                DETAIL_KEY_PRESENCE_SOURCE: tk.StringVar(value="--"),
                DETAIL_KEY_FULL_PROBE_BUCKET: tk.StringVar(value="--"),
                DETAIL_KEY_FULL_PROBE_AGE: tk.StringVar(value="--"),
                DETAIL_KEY_FULL_PROBE_SCORE: tk.StringVar(value="--"),
                DETAIL_KEY_FULL_PROBE_STATUS: tk.StringVar(value="--"),
                DETAIL_KEY_FULL_PROBE_MESSAGE: tk.StringVar(value="--"),
                DETAIL_KEY_LIFECYCLE_STATE: tk.StringVar(value="--"),
                DETAIL_KEY_TESTABLE: tk.StringVar(value="--"),
                DETAIL_KEY_OVERRIDE_ACTIVE: tk.StringVar(value="--"),
                DETAIL_KEY_OVERRIDE_ORIGINATED: tk.StringVar(value="--"),
                DETAIL_KEY_OVERRIDE_FAILURE: tk.StringVar(value="--"),
                DETAIL_KEY_NOT_TESTABLE_REASON: tk.StringVar(value="--"),
                DETAIL_KEY_LAST_SEEN: tk.StringVar(value="--"),
                DETAIL_KEY_CURRENT_A: tk.StringVar(value="--"),
                DETAIL_KEY_CURRENT_AVG_A: tk.StringVar(value="--"),
                DETAIL_KEY_CURRENT_PEAK_A: tk.StringVar(value="--"),
                DETAIL_KEY_CURRENT_NONZERO: tk.StringVar(value="--"),
                DETAIL_KEY_CURRENT_SAMPLES: tk.StringVar(value="--"),
                DETAIL_KEY_CMD_DUTY: tk.StringVar(value="--"),
                DETAIL_KEY_APPLIED_DUTY: tk.StringVar(value="--"),
                DETAIL_KEY_VEL_RPM: tk.StringVar(value="--"),
                DETAIL_KEY_POSITION_ROT: tk.StringVar(value="--"),
                DETAIL_KEY_POSITION_DELTA_ROT: tk.StringVar(value="--"),
                DETAIL_KEY_TEMP_C: tk.StringVar(value="--"),
                DETAIL_KEY_SELECTED: tk.StringVar(value="--"),
            }
            rows = [
                (DETAIL_TITLE_LABEL, DETAIL_KEY_LABEL),
                (DETAIL_TITLE_CAN_ID, DETAIL_KEY_CAN_ID),
                (DETAIL_TITLE_PRESENCE, DETAIL_KEY_PRESENCE),
                (DETAIL_TITLE_PRESENCE_STATUS, DETAIL_KEY_PRESENCE_STATUS),
                (DETAIL_TITLE_PRESENCE_AGE, DETAIL_KEY_PRESENCE_AGE),
                (DETAIL_TITLE_PRESENCE_SOURCE, DETAIL_KEY_PRESENCE_SOURCE),
                (DETAIL_TITLE_FULL_PROBE_BUCKET, DETAIL_KEY_FULL_PROBE_BUCKET),
                (DETAIL_TITLE_FULL_PROBE_AGE, DETAIL_KEY_FULL_PROBE_AGE),
                (DETAIL_TITLE_FULL_PROBE_SCORE, DETAIL_KEY_FULL_PROBE_SCORE),
                (DETAIL_TITLE_FULL_PROBE_STATUS, DETAIL_KEY_FULL_PROBE_STATUS),
                (DETAIL_TITLE_FULL_PROBE_MESSAGE, DETAIL_KEY_FULL_PROBE_MESSAGE),
                (DETAIL_TITLE_LIFECYCLE_STATE, DETAIL_KEY_LIFECYCLE_STATE),
                (DETAIL_TITLE_TESTABLE, DETAIL_KEY_TESTABLE),
                (DETAIL_TITLE_OVERRIDE_ACTIVE, DETAIL_KEY_OVERRIDE_ACTIVE),
                (DETAIL_TITLE_OVERRIDE_ORIGINATED, DETAIL_KEY_OVERRIDE_ORIGINATED),
                (DETAIL_TITLE_OVERRIDE_FAILURE, DETAIL_KEY_OVERRIDE_FAILURE),
                (DETAIL_TITLE_NOT_TESTABLE_REASON, DETAIL_KEY_NOT_TESTABLE_REASON),
                (DETAIL_TITLE_LAST_SEEN, DETAIL_KEY_LAST_SEEN),
                (DETAIL_TITLE_CURRENT_A, DETAIL_KEY_CURRENT_A),
                (DETAIL_TITLE_CURRENT_AVG_A, DETAIL_KEY_CURRENT_AVG_A),
                (DETAIL_TITLE_CURRENT_PEAK_A, DETAIL_KEY_CURRENT_PEAK_A),
                (DETAIL_TITLE_CURRENT_NONZERO, DETAIL_KEY_CURRENT_NONZERO),
                (DETAIL_TITLE_CURRENT_SAMPLES, DETAIL_KEY_CURRENT_SAMPLES),
                (DETAIL_TITLE_CMD_DUTY, DETAIL_KEY_CMD_DUTY),
                (DETAIL_TITLE_APPLIED_DUTY, DETAIL_KEY_APPLIED_DUTY),
                (DETAIL_TITLE_VEL_RPM, DETAIL_KEY_VEL_RPM),
                (DETAIL_TITLE_POSITION_ROT, DETAIL_KEY_POSITION_ROT),
                (DETAIL_TITLE_POSITION_DELTA_ROT, DETAIL_KEY_POSITION_DELTA_ROT),
                (DETAIL_TITLE_TEMP_C, DETAIL_KEY_TEMP_C),
                (DETAIL_TITLE_SELECTED, DETAIL_KEY_SELECTED),
            ]
            for idx, (title, key) in enumerate(rows):
                ttk.Label(self._detail_device_frame, text=f"{title}:").grid(row=idx, column=0, sticky="w", padx=4)
                ttk.Label(self._detail_device_frame, textvariable=self._detail_vars[key]).grid(
                    row=idx, column=1, sticky="w"
                )
            if self._on_override_action_cb is not None:
                override_row = ttk.Frame(self._detail_device_frame)
                override_row.grid(row=len(rows), column=0, columnspan=2, sticky="w", pady=(8, 0))
                ttk.Button(
                    override_row,
                    text="Override Instantiate",
                    command=lambda: self._invoke_override_action("instantiate"),
                ).pack(side="left")
                ttk.Button(
                    override_row,
                    text="Clear Override",
                    command=lambda: self._invoke_override_action("clear"),
                ).pack(side="left", padx=(8, 0))
            active_group_frame = ttk.LabelFrame(
                details_container,
                text=ACTIVE_GROUP_FRAME_TEXT,
                padding=8,
            )
            active_group_frame.pack(side="top", fill="both", expand=True, pady=(8, 0))
            self._active_group_summary_var = tk.StringVar(value=ACTIVE_GROUP_NONE_TEXT)
            ttk.Label(
                active_group_frame,
                textvariable=self._active_group_summary_var,
                justify="left",
                anchor="nw",
            ).pack(fill="x")
            rows_container = ttk.Frame(active_group_frame)
            rows_container.pack(fill="both", expand=True, pady=(8, 0))
            rows_canvas = tk.Canvas(rows_container, height=ROWS_SCROLL_HEIGHT, highlightthickness=0)
            rows_canvas.pack(side="left", fill="both", expand=True)
            rows_scroll = ttk.Scrollbar(rows_container, orient="vertical", command=rows_canvas.yview)
            rows_scroll.pack(side="right", fill="y")
            rows_canvas.configure(yscrollcommand=rows_scroll.set)
            rows_frame = ttk.Frame(rows_canvas)
            rows_window = rows_canvas.create_window((0, 0), window=rows_frame, anchor="nw")

            def _sync_active_group_scrollregion(_event=None) -> None:
                rows_canvas.configure(scrollregion=rows_canvas.bbox("all"))

            def _sync_active_group_rows_width(_event=None) -> None:
                width = max(int(rows_canvas.winfo_width()), 1)
                rows_canvas.itemconfigure(rows_window, width=width)

            rows_frame.bind("<Configure>", _sync_active_group_scrollregion)
            rows_canvas.bind("<Configure>", _sync_active_group_rows_width)
            self._active_group_rows_canvas = rows_canvas
            self._active_group_rows_frame = rows_frame
            ttk.Label(
                active_group_frame,
                text=ACTIVE_GROUP_RULES_TEXT,
                justify="left",
                anchor="nw",
            ).pack(fill="x", pady=(8, 0))

        self._notice_label = tk.Label(
            self,
            text=EMPTY_STRING,
            anchor="w",
            justify="left",
            padx=10,
            pady=6,
            bg=NOTICE_COLOR_INFO_BG,
            fg=NOTICE_COLOR_INFO_FG,
            font=("Segoe UI", 14, "bold"),
        )
        self._notice_label.pack_forget()

        self.reload_profile(profile_name)

    def reload_profile(self, profile_name: Optional[str] = None) -> None:
        """
        NAME
            reload_profile - Reload diagram/profile data for the view.
        """
        if profile_name:
            self._profile_name = profile_name
        payload, err = _load_profiles_payload()
        if payload is None:
            self._status_label.configure(text=f"Profile: {self._profile_name} (error)")
            self._nodes = []
            self._diagram_meta = {}
            self._bridge_groups = []
            self._redraw()
            return
        registry = _load_device_registry(payload)
        profiles = payload.get(KEY_PROFILES) if isinstance(payload.get(KEY_PROFILES), dict) else {}
        default_profile = str(payload.get(KEY_DEFAULT_PROFILE) or self._profile_name)
        profile_name = self._profile_name or default_profile
        raw_profile = profiles.get(profile_name)
        if not isinstance(raw_profile, dict):
            profile_name = default_profile
            raw_profile = profiles.get(profile_name, {})
        self._profile_name = profile_name
        self._status_label.configure(text=f"Profile: {self._profile_name}")

        diagram = payload.get("diagram") if isinstance(payload.get("diagram"), dict) else {}
        diagram_profiles = diagram.get("profiles") if isinstance(diagram.get("profiles"), dict) else {}
        diag = diagram_profiles.get(self._profile_name)
        if not isinstance(diag, dict):
            topology_profile = topology_profile_from_payload(payload, self._profile_name)
            diag = topology_profile if isinstance(topology_profile, dict) else None
        if isinstance(diag, dict):
            nodes, meta = _diagram_nodes(diag, registry)
            self._nodes = nodes
            self._diagram_meta = meta
            self._use_diagram_layout = True
            view_dict = meta.get(KEY_TOPOLOGY_VIEW)
            view_meta = view_dict if isinstance(view_dict, dict) else meta
            self._bus_spacing = float(view_meta.get("busSpacing") or 160.0)
            self._bus_offsets = [float(v) for v in (view_meta.get("busOffsets") or [0.0])]
            self._bus_lefts = [float(v) for v in (view_meta.get("busLefts") or [])]
            self._bus_rights = [float(v) for v in (view_meta.get("busRights") or [])]
            self._bus_connector_sides = [
                str(v).strip().lower()
                for v in (view_meta.get(VIEW_KEY_BUS_CONNECTOR_SIDES) or [])
                if isinstance(v, str)
            ]
            self._pan_y = float(view_meta.get("panY") or 0.0)
            self._zoom = float(view_meta.get("zoom") or 1.0)
            self._ethernet_links, self._can_links, self._device_links = parse_diagram_links(meta)
            self._power_links, self._attachment_links, self._dio_links = parse_diagram_aux_links(meta)
            if isinstance(view_meta, dict):
                saved_filters = view_meta.get("connectionFilters")
                if isinstance(saved_filters, list):
                    active = {
                        str(entry).strip().lower()
                        for entry in saved_filters
                        if isinstance(entry, str)
                    }
                    for filter_key, var in self._connection_filter_vars.items():
                        var.set(filter_key in active)
        else:
            self._nodes = _profile_devices(
                raw_profile if isinstance(raw_profile, dict) else {},
                registry,
            )
            self._diagram_meta = {}
            self._use_diagram_layout = False
            self._bus_offsets = [0.0]
            self._bus_spacing = 160.0
            self._bus_lefts = []
            self._bus_rights = []
            self._pan_y = 0.0
            self._zoom = 1.0
            self._ethernet_links = []
            self._can_links = []
            self._device_links = []
            self._power_links = []
            self._attachment_links = []
            self._dio_links = []
        self._bridge_groups = parse_bridge_groups(payload, self._profile_name)
        self._redraw()

    def set_show_groups(self, enabled: bool) -> None:
        """
        NAME
            set_show_groups - Toggle bridgeConfig by-profile group overlays.
        """
        enabled = bool(enabled)
        if enabled != self._show_groups:
            self._show_groups = enabled
            self._redraw()

    def set_presence_overrides(self, overrides: Dict[str, str]) -> None:
        """
        NAME
            set_presence_overrides - Apply NT-derived presence confidence overrides.
        """
        normalized: Dict[str, str] = {}
        for label, value in (overrides or {}).items():
            if not label:
                continue
            normalized[str(label).strip().lower()] = str(value).strip()
        if normalized == self._presence_overrides:
            return
        self._presence_overrides = normalized
        self._redraw()

    def set_visibility_enabled(self, enabled: bool) -> None:
        """
        NAME
            set_visibility_enabled - Toggle visibility overlay mode.
        """
        enabled = bool(enabled)
        if enabled == self._visibility_enabled:
            return
        self._visibility_enabled = enabled
        self._redraw()

    def set_evidence_snapshot(self, evidence_state: Optional[Dict[str, str]]) -> None:
        """
        NAME
            set_evidence_snapshot - Apply interpreted evidence states for node coloring.
        """
        normalized: Dict[str, str] = {}
        if isinstance(evidence_state, dict):
            for label, state in evidence_state.items():
                clean_label = str(label).strip().lower()
                clean_state = str(state).strip().lower()
                if clean_label and clean_state:
                    normalized[clean_label] = clean_state
        if normalized == self._evidence_state:
            return
        self._evidence_state = normalized
        self._redraw()

    def get_selected_label(self) -> str:
        """
        NAME
            get_selected_label - Return the currently selected node label or empty string.
        """
        if self._selected_node is None:
            return EMPTY_STRING
        return str(self._selected_node.label).strip()

    def select_node_by_label(self, label: Optional[str]) -> None:
        """
        NAME
            select_node_by_label - Select one node by label and refresh details.
        """
        clean_label = str(label or EMPTY_STRING).strip().lower()
        selected_node = None
        if clean_label:
            selected_node = next(
                (node for node in self._nodes if str(node.label).strip().lower() == clean_label),
                None,
            )
        self._selected_node = selected_node
        self._update_details()
        self._notify_selection_changed()
        self._redraw()

    def _active_connection_filters(self) -> set[str]:
        """
        NAME
            _active_connection_filters - Return enabled connection filter keys.
        """
        vars_map = getattr(self, "_connection_filter_vars", None)
        if not isinstance(vars_map, dict):
            return set(CONNECTION_FILTERS_ORDER)
        return {
            filter_key
            for filter_key, var in vars_map.items()
            if bool(var.get())
        }

    def _enable_all_connection_filters(self) -> None:
        """
        NAME
            _enable_all_connection_filters - Enable every connection filter.
        """
        for var in self._connection_filter_vars.values():
            var.set(True)
        self._redraw()

    def _disable_all_connection_filters(self) -> None:
        """
        NAME
            _disable_all_connection_filters - Disable every connection filter.
        """
        for var in self._connection_filter_vars.values():
            var.set(False)
        self._redraw()

    def set_visibility_snapshot(self, snapshot: Optional[Dict[str, object]]) -> None:
        """
        NAME
            set_visibility_snapshot - Apply a visibility snapshot for coloring.
        """
        if snapshot is None or not isinstance(snapshot, dict):
            if self._visibility_state or self._visibility_sources:
                self._visibility_state = {}
                self._visibility_sources = {}
                self._visibility_fingerprint = None
                self._redraw()
            return
        sources = snapshot.get(VIS_KEY_SOURCES)
        devices = snapshot.get(VIS_KEY_DEVICES)
        if not isinstance(sources, list) or not isinstance(devices, list):
            return
        source_map: Dict[str, bool] = {}
        for entry in sources:
            if not isinstance(entry, dict):
                continue
            src_id = str(entry.get(VIS_KEY_ID, EMPTY_STRING)).strip()
            src_label = str(entry.get(VIS_KEY_LABEL, EMPTY_STRING)).strip()
            available = bool(entry.get(VIS_KEY_AVAILABLE))
            if src_id:
                source_map[src_id.lower()] = available
            if src_label:
                source_map[src_label.lower()] = available
        state_map: Dict[str, str] = {}
        available_ids = [
            str(entry.get(VIS_KEY_ID, EMPTY_STRING)).strip()
            for entry in sources
            if isinstance(entry, dict) and bool(entry.get(VIS_KEY_AVAILABLE))
        ]
        for device in devices:
            if not isinstance(device, dict):
                continue
            label = str(device.get(VIS_KEY_LABEL, EMPTY_STRING)).strip()
            if not label:
                continue
            visibility = device.get(VIS_KEY_VISIBILITY)
            if not isinstance(visibility, dict):
                continue
            if not available_ids:
                state_map[label.lower()] = VIS_STATE_UNKNOWN
                continue
            vis_values = []
            for src_id in available_ids:
                value = visibility.get(src_id)
                vis_values.append(value is VIS_VISIBLE_TRUE)
            if all(vis_values):
                state_map[label.lower()] = VIS_STATE_ALL
            elif any(vis_values):
                state_map[label.lower()] = VIS_STATE_SOME
            else:
                state_map[label.lower()] = VIS_STATE_NONE
        fingerprint_items = sorted(state_map.items())
        fingerprint_sources = sorted(source_map.items())
        fingerprint: Tuple[object, ...] = (tuple(fingerprint_items), tuple(fingerprint_sources))
        if fingerprint == self._visibility_fingerprint:
            return
        self._visibility_fingerprint = fingerprint
        self._visibility_state = state_map
        self._visibility_sources = source_map
        self._redraw()

    def _presence_fill_from_confidence(self, value: str) -> Optional[str]:
        """
        NAME
            _presence_fill_from_confidence - Map HIGH/LOW/NONE to fill colors.
        """
        if value == PRESENCE_CONF_HIGH:
            return PRESENCE_COLOR_HIGH
        if value == PRESENCE_CONF_LOW:
            return PRESENCE_COLOR_LOW
        if value == PRESENCE_CONF_NONE:
            return PRESENCE_COLOR_NONE
        return None

    def update_runtime_state(self, payload: Optional[Dict[str, object]]) -> bool:
        """
        NAME
            update_runtime_state - Apply live runtime-state payload.
        """
        mapped: Dict[str, Dict[str, object]] = {}
        selected_label = None
        selected_enabled: Optional[bool] = None
        runtime_active: Optional[bool] = None
        robot_enabled: Optional[bool] = None
        robot_estopped: Optional[bool] = None
        runtime_groups: List[Dict[str, object]] = []
        if isinstance(payload, dict):
            active_raw = payload.get("runtimeActive")
            if isinstance(active_raw, bool):
                runtime_active = active_raw
            enabled_raw = payload.get("enabled")
            if isinstance(enabled_raw, bool):
                robot_enabled = enabled_raw
            estopped_raw = payload.get("estopped")
            if isinstance(estopped_raw, bool):
                robot_estopped = estopped_raw
            devices = payload.get("devices") if isinstance(payload.get("devices"), list) else []
            for device in devices:
                if not isinstance(device, dict):
                    continue
                label = str(device.get("label", "")).strip()
                if label:
                    mapped[label.lower()] = device
            selected = payload.get("selectedDevice")
            if isinstance(selected, dict):
                label = str(selected.get("device", "")).strip()
                if label:
                    selected_label = label.lower()
                enabled = selected.get("enabled")
                if isinstance(enabled, bool):
                    selected_enabled = enabled
            groups = payload.get("groups") if isinstance(payload.get("groups"), list) else []
            runtime_groups = [dict(group) for group in groups if isinstance(group, dict)]
        fingerprint_items: List[Tuple[object, ...]] = []
        for label, device in mapped.items():
            presence = device.get("presenceConfidence")
            probe = _runtime_active_probe_attachment(device)
            lifecycle_state = str(device.get("lifecycleState", EMPTY_STRING)).strip()
            testable = bool(device.get("testable"))
            override_active = bool(device.get("overrideActive"))
            override_originated = bool(device.get("overrideOriginated"))
            override_failure = bool(device.get("overrideFailure"))
            presence_bucket = None
            if isinstance(presence, (int, float)):
                if presence <= 0.05:
                    presence_bucket = "none"
                elif presence < 0.5:
                    presence_bucket = "low"
                else:
                    presence_bucket = "high"
            last_seen_bucket = None
            last_seen = device.get("lastSeenMs")
            if presence_bucket is None and isinstance(last_seen, (int, float)):
                last_seen_bucket = int(float(last_seen) // 1000)
            current_a = _runtime_display_current_a(device)
            if isinstance(current_a, (int, float)):
                current_a = round(float(current_a), 1)
            cmd_duty = _runtime_device_field(device, "cmdDuty")
            if isinstance(cmd_duty, (int, float)):
                cmd_duty = round(float(cmd_duty), 2)
            applied_duty = _runtime_device_field(device, "appliedDuty")
            if isinstance(applied_duty, (int, float)):
                applied_duty = round(float(applied_duty), 2)
            vel_rpm = _runtime_device_field(device, "velRpm")
            if isinstance(vel_rpm, (int, float)):
                vel_rpm = round(float(vel_rpm), 1)
            position_rot = _runtime_device_field(device, RUNTIME_KEY_POSITION_ROT)
            if isinstance(position_rot, (int, float)):
                position_rot = round(float(position_rot), 3)
            temp_c = _runtime_device_field(device, "tempC")
            if isinstance(temp_c, (int, float)):
                temp_c = round(float(temp_c), 1)
            probe_bucket = None
            probe_score = None
            probe_status = None
            if isinstance(probe, dict):
              probe_bucket = str(probe.get(RUNTIME_KEY_ACTIVE_PROBE_BUCKET, EMPTY_STRING)).strip()
              probe_status = str(probe.get(RUNTIME_KEY_ACTIVE_PROBE_STATUS, EMPTY_STRING)).strip()
              score_value = probe.get(RUNTIME_KEY_ACTIVE_PROBE_SCORE)
              if isinstance(score_value, (int, float)):
                  probe_score = round(float(score_value), 1)
            fingerprint_items.append(
                (
                    label,
                    presence_bucket,
                    last_seen_bucket,
                    current_a,
                    cmd_duty,
                    applied_duty,
                    vel_rpm,
                    position_rot,
                    temp_c,
                    probe_bucket,
                    probe_score,
                    probe_status,
                    lifecycle_state,
                    testable,
                    override_active,
                    override_originated,
                    override_failure,
                )
            )
        fingerprint_items.sort(key=lambda item: str(item[0]))
        fingerprint: Tuple[object, ...] = (
            tuple(fingerprint_items),
            selected_label,
            selected_enabled,
            runtime_active,
            robot_enabled,
            robot_estopped,
            tuple(
                (
                    str(group.get("name", EMPTY_STRING)).strip().lower(),
                    bool(group.get("enabled", True)),
                    tuple(
                        str(member.get("label", EMPTY_STRING)).strip().lower()
                        for member in group.get("members", [])
                        if isinstance(member, dict)
                    ),
                )
                for group in runtime_groups
            ),
        )
        self._runtime_state = mapped
        self._runtime_groups = runtime_groups
        self._selected_label = selected_label
        self._selected_enabled = selected_enabled
        self._apply_runtime_notice_from_state(runtime_active, robot_enabled, robot_estopped)
        self._update_details()
        if fingerprint == self._runtime_fingerprint:
            return False
        self._runtime_fingerprint = fingerprint
        self._redraw()
        return True

    def apply_runtime_group(self, group_payload: Optional[Dict[str, object]]) -> bool:
        """
        NAME
            apply_runtime_group - Merge one runtime group payload into the current runtime group set.
        """
        if not isinstance(group_payload, dict):
            return False
        name = str(group_payload.get("name", EMPTY_STRING)).strip()
        if not name:
            return False
        merged: List[Dict[str, object]] = []
        applied = False
        for existing in self._runtime_groups:
            if not isinstance(existing, dict):
                continue
            existing_name = str(existing.get("name", EMPTY_STRING)).strip().lower()
            if existing_name == name.lower():
                merged.append(dict(group_payload))
                applied = True
            else:
                merged.append(dict(existing))
        if not applied:
            merged.append(dict(group_payload))
        current_fingerprint = tuple(
            (
                str(group.get("name", EMPTY_STRING)).strip().lower(),
                bool(group.get("enabled", True)),
                tuple(
                    str(member.get("label", EMPTY_STRING)).strip().lower()
                    for member in group.get("members", [])
                    if isinstance(member, dict)
                ),
            )
            for group in self._runtime_groups
            if isinstance(group, dict)
        )
        next_fingerprint = tuple(
            (
                str(group.get("name", EMPTY_STRING)).strip().lower(),
                bool(group.get("enabled", True)),
                tuple(
                    str(member.get("label", EMPTY_STRING)).strip().lower()
                    for member in group.get("members", [])
                    if isinstance(member, dict)
                ),
            )
            for group in merged
        )
        if next_fingerprint == current_fingerprint:
            return False
        self._runtime_groups = merged
        self._update_details()
        self._redraw()
        return True

    def _effective_groups(self) -> List[Dict[str, object]]:
        """
        NAME
            _effective_groups - Merge static profile groups with runtime groups by name.
        """
        merged: Dict[str, Dict[str, object]] = {}
        for group in self._bridge_groups:
            if not isinstance(group, dict):
                continue
            name = str(group.get("name", EMPTY_STRING)).strip()
            if name:
                merged[name.lower()] = dict(group)
        for group in self._runtime_groups:
            if not isinstance(group, dict):
                continue
            name = str(group.get("name", EMPTY_STRING)).strip()
            if name:
                merged[name.lower()] = dict(group)
        return list(merged.values())

    def set_runtime_notice(self, text: str, level: str = "warn") -> None:
        """
        NAME
            set_runtime_notice - Display an operator-facing live-topology notice.
        """
        message = str(text).strip()
        if not message:
            self.clear_runtime_notice()
            return
        self._runtime_event_notice_text = message
        self._runtime_event_notice_level = level if level in {"info", "warn", "error"} else "warn"
        self._refresh_runtime_notice()

    def set_manual_test_observations(self, observations: Optional[Dict[str, Dict[str, object]]]) -> None:
        """
        NAME
            set_manual_test_observations - Apply cached manual-test motion observations for group inspector status.
        """
        normalized: Dict[str, Dict[str, object]] = {}
        if isinstance(observations, dict):
            for label, entry in observations.items():
                clean_label = str(label or EMPTY_STRING).strip().lower()
                if not clean_label or not isinstance(entry, dict):
                    continue
                normalized[clean_label] = dict(entry)
        if normalized == self._manual_test_observations:
            return
        self._manual_test_observations = normalized
        self._update_details()

    def set_runtime_state_notice(self, text: str, level: str = "warn") -> None:
        """
        NAME
            set_runtime_state_notice - Display a persistent state-derived live-topology notice.
        """
        message = str(text).strip()
        self._runtime_state_notice_text = message
        self._runtime_state_notice_level = level if level in {"info", "warn", "error"} else "warn"
        self._refresh_runtime_notice()

    def clear_runtime_state_notice(self) -> None:
        """
        NAME
            clear_runtime_state_notice - Clear the persistent state-derived notice.
        """
        self._runtime_state_notice_text = EMPTY_STRING
        self._refresh_runtime_notice()

    def clear_runtime_notice(self) -> None:
        """
        NAME
            clear_runtime_notice - Hide the event-driven live-topology notice banner.
        """
        self._runtime_event_notice_text = EMPTY_STRING
        self._refresh_runtime_notice()

    def _refresh_runtime_notice(self) -> None:
        """
        NAME
            _refresh_runtime_notice - Render the highest-priority live-topology notice.
        """
        if self._runtime_state_notice_text:
            message = self._runtime_state_notice_text
            level = self._runtime_state_notice_level
        elif self._runtime_event_notice_text:
            message = self._runtime_event_notice_text
            level = self._runtime_event_notice_level
        else:
            self._notice_label.configure(text=EMPTY_STRING)
            self._notice_label.pack_forget()
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
        self._notice_label.configure(text=message, bg=bg, fg=fg)
        self._notice_label.pack(side="bottom", fill="x", padx=8, pady=(0, 8))

    def _apply_runtime_notice_from_state(
        self,
        runtime_active: Optional[bool],
        robot_enabled: Optional[bool],
        robot_estopped: Optional[bool],
    ) -> None:
        """
        NAME
            _apply_runtime_notice_from_state - Derive a live-topology notice from runtime state.
        """
        if robot_estopped is True:
            self.set_runtime_state_notice("Robot E-Stop. Manual run blocked.", "error")
            return
        if runtime_active is False:
            self.set_runtime_state_notice("Runtime inactive. Click Runtime Activate.", "warn")
            return
        if robot_enabled is False:
            self.set_runtime_state_notice("Robot disabled. Enable teleop to run motors.", "info")
            return
        self.clear_runtime_state_notice()

    def _on_canvas_click(self, event: tk.Event) -> None:
        """
        NAME
            _on_canvas_click - Select node on click.
        """
        x = self._canvas.canvasx(event.x)
        y = self._canvas.canvasy(event.y)
        selected_node: Optional[LiveNode] = None
        for key, bounds in self._node_bounds.items():
            x0, y0, x1, y1 = bounds
            if x0 <= x <= x1 and y0 <= y <= y1:
                selected_node = next((n for n in self._nodes if n.key == key), None)
                self._selected_node = selected_node
                self._update_details()
                break
        if selected_node is None:
            self._selected_node = None
            self._update_details()
        self._notify_selection_changed()
        self._redraw()
        if callable(self._on_left_click_cb):
            self._on_left_click_cb(self._selected_node, event)

    def _on_canvas_right_click(self, event: tk.Event) -> None:
        """
        NAME
            _on_canvas_right_click - Route right-clicks on nodes to the owner callback.
        """
        x = self._canvas.canvasx(event.x)
        y = self._canvas.canvasy(event.y)
        for key, bounds in self._node_bounds.items():
            x0, y0, x1, y1 = bounds
            if x0 <= x <= x1 and y0 <= y <= y1:
                node = next((n for n in self._nodes if n.key == key), None)
                if node is None:
                    return
                self._selected_node = node
                self._update_details()
                self._notify_selection_changed()
                self._redraw()
                if callable(self._on_node_right_click_cb):
                    self._on_node_right_click_cb(node, event)
                return
        label_hits: List[Tuple[float, Dict[str, object]]] = []
        bounds_hits: List[Tuple[float, Dict[str, object]]] = []
        for region in self._group_overlay_regions:
            if not isinstance(region, dict):
                continue
            hit_type = self._group_region_hit_type(x, y, region)
            if hit_type is None:
                continue
            area = self._group_region_area(region, hit_type)
            hit_entry = (area, dict(region))
            if hit_type == "label_bounds":
                label_hits.append(hit_entry)
            else:
                bounds_hits.append(hit_entry)
        chosen_hits = label_hits or bounds_hits
        if chosen_hits and callable(self._on_group_right_click_cb):
            _area, region = min(chosen_hits, key=lambda item: item[0])
            self._on_group_right_click_cb(region, event)
            return

    def _point_in_group_region(self, x: float, y: float, region: Dict[str, object]) -> bool:
        """
        NAME
            _point_in_group_region - Return whether a canvas point hits one group overlay.
        """
        return self._group_region_hit_type(x, y, region) is not None

    def _group_region_hit_type(self, x: float, y: float, region: Dict[str, object]) -> Optional[str]:
        """
        NAME
            _group_region_hit_type - Return which group overlay region contains one canvas point.
        """
        for key in ("label_bounds", "bounds"):
            bounds = region.get(key)
            if not isinstance(bounds, tuple) or len(bounds) != 4:
                continue
            x0, y0, x1, y1 = bounds
            if x0 <= x <= x1 and y0 <= y <= y1:
                return key
        return None

    def _group_region_area(self, region: Dict[str, object], key: str) -> float:
        """
        NAME
            _group_region_area - Return one group overlay region area for overlap priority.
        """
        bounds = region.get(key)
        if not isinstance(bounds, tuple) or len(bounds) != 4:
            return float("inf")
        x0, y0, x1, y1 = bounds
        return max(0.0, float(x1) - float(x0)) * max(0.0, float(y1) - float(y0))

    def _notify_selection_changed(self) -> None:
        """
        NAME
            _notify_selection_changed - Forward node-selection changes to the owner callback.
        """
        if callable(self._on_selection_changed_cb):
            self._on_selection_changed_cb(self._selected_node)

    def _on_mousewheel_zoom(self, event: tk.Event) -> None:
        """
        NAME
            _on_mousewheel_zoom - Zoom with Ctrl + mouse wheel.
        """
        delta = ZOOM_STEP if event.delta > 0 else -ZOOM_STEP
        self._nudge_zoom(delta)

    def _nudge_zoom(self, delta: float) -> None:
        """
        NAME
            _nudge_zoom - Increment zoom with clamping.
        """
        new_zoom = max(ZOOM_MIN, min(ZOOM_MAX, self._zoom + delta))
        if abs(new_zoom - self._zoom) < 1e-6:
            return
        self._zoom = new_zoom
        self._redraw()

    def _reset_zoom(self) -> None:
        """
        NAME
            _reset_zoom - Reset zoom to 100%.
        """
        self._zoom = 1.0
        self._redraw()

    def _on_canvas_pan_press(self, event: tk.Event) -> str:
        """
        NAME
            _on_canvas_pan_press - Begin whole-diagram canvas panning.
        """
        self._canvas.scan_mark(event.x, event.y)
        return "break"

    def _on_canvas_pan_drag(self, event: tk.Event) -> str:
        """
        NAME
            _on_canvas_pan_drag - Pan the canvas with the middle mouse button.
        """
        self._canvas.scan_dragto(event.x, event.y, gain=CANVAS_PAN_GAIN)
        return "break"

    def _on_canvas_pan_release(self, _event: tk.Event) -> str:
        """
        NAME
            _on_canvas_pan_release - Finish whole-diagram canvas panning.
        """
        return "break"

    def _set_canvas_xview_left(self, desired_left: float) -> None:
        """
        NAME
            _set_canvas_xview_left - Position the canvas viewport at an X coordinate.
        """
        try:
            raw_region = self._canvas.cget("scrollregion")
        except Exception:
            return
        parts = str(raw_region).split()
        if len(parts) != SCROLLREGION_FIELD_COUNT:
            return
        try:
            region = [float(part) for part in parts]
        except ValueError:
            return
        width = max(float(self._canvas.winfo_width()), SCROLLREGION_MIN_SPAN)
        old_min_x = region[SCROLLREGION_MIN_INDEX]
        old_max_x = region[SCROLLREGION_MAX_INDEX]
        new_min_x = min(old_min_x, desired_left)
        new_max_x = max(old_max_x, desired_left + width)
        new_span = max(new_max_x - new_min_x, SCROLLREGION_MIN_SPAN)
        if new_min_x != old_min_x or new_max_x != old_max_x:
            region[SCROLLREGION_MIN_INDEX] = new_min_x
            region[SCROLLREGION_MAX_INDEX] = new_max_x
            self._canvas.configure(scrollregion=tuple(region))
        fraction = (desired_left - new_min_x) / new_span
        self._canvas.xview_moveto(max(0.0, min(1.0, fraction)))

    def _fit_to_window(self) -> None:
        """
        NAME
            _fit_to_window - Fit the diagram to the current canvas size.
        """
        width = max(self._canvas.winfo_width(), 1)
        height = max(self._canvas.winfo_height(), 1)
        nodes = list(self._nodes)
        if not nodes and not self._bus_offsets:
            return
        min_x = float("inf")
        max_x = float("-inf")
        min_y = float("inf")
        max_y = float("-inf")
        for node in nodes:
            node_scale = max(0.6, min(2.0, float(getattr(node, "scale", 1.0))))
            if node.node_type == LEGACY_NODE_TYPE_CALLOUT:
                half_w = (180.0 * node_scale) / 2.0
                half_h = (50.0 * node_scale) / 2.0
            else:
                half_w = (NODE_BOX_BASE_W * node_scale) / 2.0
                half_h = (NODE_BOX_BASE_H * node_scale) / 2.0
            center_y = node_center_y_unscaled(node, self._bus_offsets, NODE_BOX_BASE_H)
            min_x = min(min_x, node.x - half_w)
            max_x = max(max_x, node.x + half_w)
            min_y = min(min_y, center_y - half_h)
            max_y = max(max_y, center_y + half_h)
        if self._bus_offsets:
            bus_min = min(self._bus_offsets) - (NODE_BOX_BASE_H + 60.0)
            bus_max = max(self._bus_offsets) + (NODE_BOX_BASE_H + 60.0)
            min_y = min(min_y, bus_min)
            max_y = max(max_y, bus_max)
        max_node_x = max((n.x for n in nodes), default=0.0)
        bus_lefts = list(self._bus_lefts)
        bus_rights = list(self._bus_rights)
        if len(bus_lefts) < len(self._bus_offsets):
            bus_lefts.extend([40.0] * (len(self._bus_offsets) - len(bus_lefts)))
        if len(bus_rights) < len(self._bus_offsets):
            bus_rights.extend([max_node_x + 200.0] * (len(self._bus_offsets) - len(bus_rights)))
        if self._bus_offsets:
            min_x = min(min_x, min(bus_lefts, default=40.0))
            max_x = max(max_x, max(bus_rights, default=max_node_x + 200.0))
        max_x = max(max_x, max_node_x + 200.0)
        min_x = min(min_x, 0.0)
        if min_x == float("inf") or max_x == float("-inf"):
            min_x, max_x = 0.0, 400.0
        if min_y == float("inf") or max_y == float("-inf"):
            min_y, max_y = -200.0, 200.0
        content_w = max(1.0, max_x - min_x)
        content_h = max(1.0, max_y - min_y)
        zoom_x = (width - CANVAS_FIT_MARGIN * 2.0) / content_w
        zoom_y = (height - CANVAS_FIT_MARGIN * 2.0) / content_h
        self._zoom = max(ZOOM_MIN, min(ZOOM_MAX, min(zoom_x, zoom_y)))
        center_y = (min_y + max_y) / 2.0
        self._pan_y = -center_y * self._zoom
        self._redraw()
        self.update_idletasks()
        content_center_x = ((min_x + max_x) / 2.0) * self._zoom
        self._set_canvas_xview_left(content_center_x - width / 2.0)
        self._canvas.yview_moveto(0.0)

    def _update_details(self) -> None:
        """
        NAME
            _update_details - Refresh selection details panel.
        """
        self._update_active_group_summary()
        if not self._detail_vars:
            return
        if self._group_inspector_name and self._group_inspector_targets:
            self._show_group_inspector()
            self._update_group_inspector()
            return
        self._show_device_inspector()
        node = self._selected_node
        if node is None:
            for key in self._detail_vars:
                self._detail_vars[key].set("--")
            return
        self._detail_vars[DETAIL_KEY_LABEL].set(node.label)
        self._detail_vars[DETAIL_KEY_CAN_ID].set(str(node.can_id) if node.can_id >= 0 else "--")
        live = self._runtime_state.get(node.label.lower())
        manual_observation = self._manual_test_observations.get(node.label.strip().lower(), {})
        if live:
            now_ms = int(time.time() * 1000)
            presence = live.get("presenceConfidence")
            last_seen = live.get("lastSeenMs")
            presence_check = _runtime_presence_check_attachment(live)
            probe = _runtime_active_probe_attachment(live)
            lifecycle_state = str(live.get("lifecycleState", "--")).strip() or "--"
            testable = live.get("testable")
            override_active = live.get("overrideActive")
            override_originated = live.get("overrideOriginated")
            override_failure = live.get("overrideFailure")
            not_testable_reason = str(live.get("notTestableReason", "--")).strip() or "--"
            current_a = _runtime_display_current_a(live)
            current_avg_a = _runtime_device_field(live, RUNTIME_KEY_CURRENT_AVG_A)
            current_peak_a = _runtime_device_field(live, RUNTIME_KEY_CURRENT_PEAK_A)
            current_nonzero = _runtime_device_field(live, RUNTIME_KEY_CURRENT_NONZERO_RATIO)
            current_samples = _runtime_device_field(live, RUNTIME_KEY_CURRENT_SAMPLE_COUNT)
            cmd_duty = _runtime_device_field(live, "cmdDuty")
            applied_duty = _runtime_device_field(live, "appliedDuty")
            vel_rpm = _runtime_device_field(live, "velRpm")
            position_rot = _runtime_device_field(live, RUNTIME_KEY_POSITION_ROT)
            temp_c = _runtime_device_field(live, "tempC")
            position_delta_rot = None
            if _manual_observation_is_live(manual_observation):
                position_delta_rot = manual_observation.get("positionDeltaRot")
                max_abs_position_delta_rot = manual_observation.get("maxAbsPositionDeltaRot")
                if (
                    not isinstance(position_delta_rot, (int, float))
                    and isinstance(max_abs_position_delta_rot, (int, float))
                ):
                    position_delta_rot = max_abs_position_delta_rot
            self._detail_vars[DETAIL_KEY_PRESENCE].set(
                f"{float(presence):.2f}" if isinstance(presence, (int, float)) else "--"
            )
            presence_status = (
                str(presence_check.get(RUNTIME_KEY_PRESENCE_CHECK_STATUS, "--")).strip()
                if isinstance(presence_check, dict)
                else "--"
            )
            presence_source = (
                str(presence_check.get(RUNTIME_KEY_PRESENCE_CHECK_SOURCE, "--")).strip()
                if isinstance(presence_check, dict)
                else "--"
            )
            presence_age = _runtime_presence_age_text(live) if isinstance(live, dict) else "--"
            full_probe_bucket = (
                str(probe.get(RUNTIME_KEY_ACTIVE_PROBE_BUCKET, "--")).strip()
                if isinstance(probe, dict)
                else "--"
            )
            full_probe_age = _runtime_probe_age_text(live) if isinstance(live, dict) else "--"
            full_probe_status = (
                str(probe.get(RUNTIME_KEY_ACTIVE_PROBE_STATUS, "--")).strip()
                if isinstance(probe, dict)
                else "--"
            )
            full_probe_message = (
                str(probe.get(RUNTIME_KEY_ACTIVE_PROBE_MESSAGE, "--")).strip()
                if isinstance(probe, dict)
                else "--"
            )
            full_probe_score = "--"
            if isinstance(probe, dict):
                score_value = probe.get(RUNTIME_KEY_ACTIVE_PROBE_SCORE)
                max_score_value = probe.get(RUNTIME_KEY_ACTIVE_PROBE_MAX_SCORE)
                if isinstance(score_value, (int, float)) and isinstance(max_score_value, (int, float)):
                    full_probe_score = f"{int(score_value)}/{int(max_score_value)}"
                elif isinstance(score_value, (int, float)):
                    full_probe_score = str(int(score_value))
            self._detail_vars[DETAIL_KEY_PRESENCE_STATUS].set(presence_status or "--")
            self._detail_vars[DETAIL_KEY_PRESENCE_AGE].set(presence_age)
            self._detail_vars[DETAIL_KEY_PRESENCE_SOURCE].set(presence_source or "--")
            self._detail_vars[DETAIL_KEY_FULL_PROBE_BUCKET].set(full_probe_bucket or "--")
            self._detail_vars[DETAIL_KEY_FULL_PROBE_AGE].set(full_probe_age)
            self._detail_vars[DETAIL_KEY_FULL_PROBE_SCORE].set(full_probe_score)
            self._detail_vars[DETAIL_KEY_FULL_PROBE_STATUS].set(full_probe_status or "--")
            self._detail_vars[DETAIL_KEY_FULL_PROBE_MESSAGE].set(full_probe_message or "--")
            self._detail_vars[DETAIL_KEY_LIFECYCLE_STATE].set(lifecycle_state)
            self._detail_vars[DETAIL_KEY_TESTABLE].set("yes" if bool(testable) else "no")
            self._detail_vars[DETAIL_KEY_OVERRIDE_ACTIVE].set(
                "yes" if bool(override_active) else "no"
            )
            self._detail_vars[DETAIL_KEY_OVERRIDE_ORIGINATED].set(
                "yes" if bool(override_originated) else "no"
            )
            self._detail_vars[DETAIL_KEY_OVERRIDE_FAILURE].set(
                "yes" if bool(override_failure) else "no"
            )
            self._detail_vars[DETAIL_KEY_NOT_TESTABLE_REASON].set(not_testable_reason)
            self._detail_vars[DETAIL_KEY_LAST_SEEN].set(_format_last_seen(last_seen, now_ms))
            self._detail_vars[DETAIL_KEY_CURRENT_A].set(
                f"{float(current_a):.2f}" if isinstance(current_a, (int, float)) else "--"
            )
            self._detail_vars[DETAIL_KEY_CURRENT_AVG_A].set(
                f"{float(current_avg_a):.2f}"
                if isinstance(current_avg_a, (int, float))
                else "--"
            )
            self._detail_vars[DETAIL_KEY_CURRENT_PEAK_A].set(
                f"{float(current_peak_a):.2f}"
                if isinstance(current_peak_a, (int, float))
                else "--"
            )
            self._detail_vars[DETAIL_KEY_CURRENT_NONZERO].set(
                f"{float(current_nonzero):.2f}"
                if isinstance(current_nonzero, (int, float))
                else "--"
            )
            self._detail_vars[DETAIL_KEY_CURRENT_SAMPLES].set(
                str(int(current_samples))
                if isinstance(current_samples, (int, float))
                else "--"
            )
            self._detail_vars[DETAIL_KEY_CMD_DUTY].set(
                f"{float(cmd_duty):.2f}" if isinstance(cmd_duty, (int, float)) else "--"
            )
            self._detail_vars[DETAIL_KEY_APPLIED_DUTY].set(
                f"{float(applied_duty):.2f}" if isinstance(applied_duty, (int, float)) else "--"
            )
            self._detail_vars[DETAIL_KEY_VEL_RPM].set(self._format_group_rpm(vel_rpm))
            self._detail_vars[DETAIL_KEY_POSITION_ROT].set(self._format_group_rot(position_rot))
            self._detail_vars[DETAIL_KEY_POSITION_DELTA_ROT].set(self._format_group_rot(position_delta_rot))
            self._detail_vars[DETAIL_KEY_TEMP_C].set(
                f"{float(temp_c):.1f}" if isinstance(temp_c, (int, float)) else "--"
            )
        else:
            self._detail_vars[DETAIL_KEY_PRESENCE].set("--")
            self._detail_vars[DETAIL_KEY_PRESENCE_STATUS].set("--")
            self._detail_vars[DETAIL_KEY_PRESENCE_AGE].set("--")
            self._detail_vars[DETAIL_KEY_PRESENCE_SOURCE].set("--")
            self._detail_vars[DETAIL_KEY_FULL_PROBE_BUCKET].set("--")
            self._detail_vars[DETAIL_KEY_FULL_PROBE_AGE].set("--")
            self._detail_vars[DETAIL_KEY_FULL_PROBE_SCORE].set("--")
            self._detail_vars[DETAIL_KEY_FULL_PROBE_STATUS].set("--")
            self._detail_vars[DETAIL_KEY_FULL_PROBE_MESSAGE].set("--")
            self._detail_vars[DETAIL_KEY_LIFECYCLE_STATE].set("--")
            self._detail_vars[DETAIL_KEY_TESTABLE].set("--")
            self._detail_vars[DETAIL_KEY_OVERRIDE_ACTIVE].set("--")
            self._detail_vars[DETAIL_KEY_OVERRIDE_ORIGINATED].set("--")
            self._detail_vars[DETAIL_KEY_OVERRIDE_FAILURE].set("--")
            self._detail_vars[DETAIL_KEY_NOT_TESTABLE_REASON].set("--")
            self._detail_vars[DETAIL_KEY_LAST_SEEN].set("--")
            self._detail_vars[DETAIL_KEY_CURRENT_A].set("--")
            self._detail_vars[DETAIL_KEY_CURRENT_AVG_A].set("--")
            self._detail_vars[DETAIL_KEY_CURRENT_PEAK_A].set("--")
            self._detail_vars[DETAIL_KEY_CURRENT_NONZERO].set("--")
            self._detail_vars[DETAIL_KEY_CURRENT_SAMPLES].set("--")
            self._detail_vars[DETAIL_KEY_CMD_DUTY].set("--")
            self._detail_vars[DETAIL_KEY_APPLIED_DUTY].set("--")
            self._detail_vars[DETAIL_KEY_VEL_RPM].set("--")
            self._detail_vars[DETAIL_KEY_POSITION_ROT].set("--")
            self._detail_vars[DETAIL_KEY_POSITION_DELTA_ROT].set("--")
            self._detail_vars[DETAIL_KEY_TEMP_C].set("--")
        selected_text = "no"
        if self._selected_label:
            if node.label.strip().lower() == self._selected_label:
                if self._selected_enabled is True:
                    selected_text = "yes (enabled)"
                elif self._selected_enabled is False:
                    selected_text = "yes (disabled)"
                else:
                    selected_text = "yes"
        else:
            selected_text = "--"
        self._detail_vars[DETAIL_KEY_SELECTED].set(selected_text)

    def _invoke_override_action(self, action: str) -> None:
        """
        NAME
            _invoke_override_action - Forward one explicit override action for the selected device.
        """
        if self._on_override_action_cb is None or self._selected_node is None:
            return
        label = str(getattr(self._selected_node, "label", EMPTY_STRING)).strip()
        if not label:
            return
        self._on_override_action_cb(label, str(action or EMPTY_STRING).strip().lower())

    def set_group_run_inspector(self, group_name: str, targets: List[str]) -> None:
        """
        NAME
            set_group_run_inspector - Switch the selection panel into group-run inspector mode.
        """
        clean_name = str(group_name or EMPTY_STRING).strip()
        clean_targets = [str(target).strip() for target in (targets or []) if str(target).strip()]
        if clean_name == self._group_inspector_name and clean_targets == self._group_inspector_targets:
            return
        self._group_inspector_name = clean_name
        self._group_inspector_targets = clean_targets
        self._update_details()

    def clear_group_run_inspector(self) -> None:
        """
        NAME
            clear_group_run_inspector - Return the selection panel to single-device inspector mode.
        """
        if not self._group_inspector_name and not self._group_inspector_targets:
            return
        self._group_inspector_name = EMPTY_STRING
        self._group_inspector_targets = []
        self._update_details()

    def _show_device_inspector(self) -> None:
        """
        NAME
            _show_device_inspector - Show the normal single-device detail view.
        """
        if self._selection_inspector_mode == GROUP_INSPECTOR_MODE_DEVICE:
            return
        if getattr(self, "_group_inspector_frame", None) is not None:
            self._group_inspector_frame.pack_forget()
        if getattr(self, "_detail_device_frame", None) is not None:
            self._detail_device_frame.pack(fill="both", expand=True)
        self._selection_inspector_mode = GROUP_INSPECTOR_MODE_DEVICE

    def _show_group_inspector(self) -> None:
        """
        NAME
            _show_group_inspector - Show the group-run detail view.
        """
        if self._selection_inspector_mode == GROUP_INSPECTOR_MODE_GROUP:
            return
        if getattr(self, "_detail_device_frame", None) is not None:
            self._detail_device_frame.pack_forget()
        if getattr(self, "_group_inspector_frame", None) is not None:
            self._group_inspector_frame.pack(fill="both", expand=True)
        self._selection_inspector_mode = GROUP_INSPECTOR_MODE_GROUP

    def _update_group_inspector(self) -> None:
        """
        NAME
            _update_group_inspector - Render summary and per-member runtime rows for one active manual group run.
        """
        summary_var = getattr(self, "_group_inspector_summary_var", None)
        frame = getattr(self, "_group_inspector_rows_frame", None)
        if summary_var is None or frame is None:
            return
        group = self._runtime_group_by_name(self._group_inspector_name)
        group_member_map: Dict[str, Dict[str, object]] = {}
        primary_label = EMPTY_STRING
        if isinstance(group, dict):
            members = group.get("members")
            if isinstance(members, list):
                for member in members:
                    if not isinstance(member, dict):
                        continue
                    label = str(member.get("label", EMPTY_STRING)).strip()
                    if not label:
                        continue
                    if not primary_label:
                        primary_label = label
                    group_member_map[label.lower()] = dict(member)
        target_labels = list(self._group_inspector_targets)
        total_count = len(target_labels)
        enabled_count = 0
        present_count = 0
        rotating_count = 0
        no_motion_count = 0
        missing_count = 0
        conflict_count = 0
        summary_lines = [
            f"{GROUP_INSPECTOR_GROUP_PREFIX}{self._group_inspector_name}",
            f"{GROUP_INSPECTOR_MODE_PREFIX}{GROUP_INSPECTOR_MODE_MANUAL_DUTY}",
        ]
        member_rows: List[Tuple[str, str]] = []
        for label in target_labels:
            label_key = label.strip().lower()
            member = group_member_map.get(label_key, {})
            enabled = bool(member.get("enabled", True))
            if enabled:
                enabled_count += 1
            live = self._runtime_state.get(label_key, {})
            manual_observation = self._manual_test_observations.get(label_key, {})
            manual_auto_result = (
                str(manual_observation.get("autoResult", EMPTY_STRING)).strip()
                if isinstance(manual_observation, dict)
                else EMPTY_STRING
            )
            presence_value = live.get("presenceConfidence") if isinstance(live, dict) else None
            present = isinstance(presence_value, (int, float)) and float(presence_value) > PRESENCE_MIN_CONF
            if present:
                present_count += 1
            probe = _runtime_active_probe_attachment(live) if isinstance(live, dict) else None
            probe_bucket = (
                str(probe.get(RUNTIME_KEY_ACTIVE_PROBE_BUCKET, "--")).strip()
                if isinstance(probe, dict)
                else "--"
            )
            probe_age = _runtime_probe_age_text(live) if isinstance(live, dict) else "--"
            motor_attachment = runtime_motor_attachment(live) if isinstance(live, dict) else None
            cmd_duty = _runtime_device_field(live, "cmdDuty") if isinstance(live, dict) else None
            applied_duty = _runtime_device_field(live, "appliedDuty") if isinstance(live, dict) else None
            applied_v = _runtime_device_field(live, "appliedV") if isinstance(live, dict) else None
            bus_v = _runtime_device_field(live, "busV") if isinstance(live, dict) else None
            vel_rpm = _runtime_device_field(live, "velRpm") if isinstance(live, dict) else None
            position_rot = _runtime_device_field(live, RUNTIME_KEY_POSITION_ROT) if isinstance(live, dict) else None
            current_a = _runtime_display_current_a(live) if isinstance(live, dict) else None
            position_delta_rot = None
            if _manual_observation_is_live(manual_observation):
                max_abs_vel = manual_observation.get("maxAbsVelRpm")
                if not isinstance(vel_rpm, (int, float)) and isinstance(max_abs_vel, (int, float)):
                    vel_rpm = max_abs_vel
                position_delta_rot = manual_observation.get("positionDeltaRot", position_delta_rot)
                max_abs_position_delta_rot = manual_observation.get("maxAbsPositionDeltaRot")
                if (
                    not isinstance(position_delta_rot, (int, float))
                    and isinstance(max_abs_position_delta_rot, (int, float))
                ):
                    position_delta_rot = max_abs_position_delta_rot
            verdict = infer_motor_runtime_verdict(
                present=present,
                cmd_duty=cmd_duty,
                applied_duty=applied_duty,
                applied_v=applied_v,
                bus_v=bus_v,
                vel_rpm=vel_rpm,
                position_delta_rot=position_delta_rot,
                motor_current_a=current_a,
                attachment=motor_attachment,
                duty_threshold=GROUP_INSPECTOR_DUTY_THRESHOLD,
                rpm_threshold=GROUP_INSPECTOR_MOTION_MIN_RPM,
                position_delta_threshold=GROUP_INSPECTOR_MOTION_MIN_POSITION_DELTA_ROT,
                current_active_threshold=0.2,
                low_bus_v_threshold=7.0,
                applied_v_active_threshold=1.0,
            )
            if manual_auto_result == MANUAL_AUTO_RESULT_ROTATION:
                verdict["result"] = GROUP_INSPECTOR_ROW_ROTATING
            elif manual_auto_result == MANUAL_AUTO_RESULT_NO_ROTATION and verdict.get("commanded"):
                verdict["result"] = GROUP_INSPECTOR_ROW_NO_MOTION
            result = str(verdict.get("result", GROUP_INSPECTOR_ROW_UNKNOWN)).strip() or GROUP_INSPECTOR_ROW_UNKNOWN
            if result == GROUP_INSPECTOR_ROW_MISSING:
                missing_count += 1
            elif result == GROUP_INSPECTOR_ROW_ROTATING:
                rotating_count += 1
            elif result in (GROUP_INSPECTOR_ROW_NO_MOTION, GROUP_INSPECTOR_ROW_STALLED, GROUP_INSPECTOR_ROW_ELECTRICAL if 'GROUP_INSPECTOR_ROW_ELECTRICAL' in globals() else GROUP_INSPECTOR_ROW_NO_MOTION):
                no_motion_count += 1
            elif result == GROUP_INSPECTOR_ROW_CONFLICT:
                conflict_count += 1
            detail_parts = []
            if primary_label and label_key == primary_label.strip().lower():
                detail_parts.append(GROUP_INSPECTOR_PRIMARY_MARKER)
            detail_parts.append(ACTIVE_GROUP_MEMBER_ENABLED if enabled else ACTIVE_GROUP_MEMBER_DISABLED)
            detail_parts.append(GROUP_INSPECTOR_ROW_PRESENT if present else GROUP_INSPECTOR_ROW_MISSING)
            detail_parts.append(
                f"{GROUP_INSPECTOR_FULL_PROBE_BUCKET_PREFIX}{probe_bucket or '--'}/{probe_age}"
            )
            detail_parts.append(f"{GROUP_INSPECTOR_CMD_DUTY_PREFIX}{self._format_group_number(cmd_duty)}")
            detail_parts.append(f"{GROUP_INSPECTOR_APPLIED_DUTY_PREFIX}{self._format_group_number(applied_duty)}")
            detail_parts.append(f"{GROUP_INSPECTOR_VEL_RPM_PREFIX}{self._format_group_rpm(vel_rpm)}")
            detail_parts.append(f"{GROUP_INSPECTOR_POSITION_ROT_PREFIX}{self._format_group_rot(position_rot)}")
            detail_parts.append(f"{GROUP_INSPECTOR_POSITION_DELTA_ROT_PREFIX}{self._format_group_rot(position_delta_rot)}")
            detail_parts.append(f"{GROUP_INSPECTOR_CURRENT_A_PREFIX}{self._format_group_current(current_a)}")
            detail_parts.append(result)
            member_rows.append((label, " | ".join(detail_parts)))
        summary_lines.extend(
            [
                f"{GROUP_INSPECTOR_MEMBERS_PREFIX}{total_count}",
                f"{GROUP_INSPECTOR_ENABLED_PREFIX}{enabled_count}/{total_count}",
                f"{GROUP_INSPECTOR_PRIMARY_PREFIX}{primary_label or '--'}",
                f"{GROUP_INSPECTOR_PRESENT_SUMMARY_PREFIX}{present_count}/{total_count}",
                f"{GROUP_INSPECTOR_ROTATING_SUMMARY_PREFIX}{rotating_count}/{total_count}",
                f"{GROUP_INSPECTOR_NO_MOTION_SUMMARY_PREFIX}{no_motion_count}/{total_count}",
                f"{GROUP_INSPECTOR_MISSING_SUMMARY_PREFIX}{missing_count}/{total_count}",
                f"{GROUP_INSPECTOR_CONFLICT_SUMMARY_PREFIX}{conflict_count}/{total_count}",
            ]
        )
        summary_var.set("\n".join(summary_lines))
        expected_keys = {label.strip().lower() for label, _detail_text in member_rows}
        stale_keys = [
            key for key in self._group_inspector_row_widgets.keys() if key not in expected_keys
        ]
        for key in stale_keys:
            widgets = self._group_inspector_row_widgets.pop(key, {})
            row_widget = widgets.get("row")
            if isinstance(row_widget, tk.Widget):
                row_widget.destroy()
        for label, detail_text in member_rows:
            key = label.strip().lower()
            widgets = self._group_inspector_row_widgets.get(key)
            if not isinstance(widgets, dict):
                row = ttk.Frame(frame)
                row.pack(fill="x", pady=(0, 4))
                label_var = tk.StringVar(value=label)
                detail_var = tk.StringVar(value=detail_text)
                ttk.Label(row, textvariable=label_var, anchor="w").pack(fill="x")
                detail_label = ttk.Label(
                    row,
                    textvariable=detail_var,
                    anchor="w",
                    justify="left",
                )
                detail_label.pack(fill="x", padx=(12, 0))
                self._bind_wrapped_label(row, detail_label)
                widgets = {
                    "row": row,
                    "label_var": label_var,
                    "detail_var": detail_var,
                }
                self._group_inspector_row_widgets[key] = widgets
            label_var = widgets.get("label_var")
            detail_var = widgets.get("detail_var")
            if isinstance(label_var, tk.StringVar):
                label_var.set(label)
            if isinstance(detail_var, tk.StringVar):
                detail_var.set(detail_text)

    def _runtime_group_by_name(self, name: str) -> Optional[Dict[str, object]]:
        """
        NAME
            _runtime_group_by_name - Return one runtime group payload by normalized name.
        """
        clean_name = str(name or EMPTY_STRING).strip().lower()
        if not clean_name:
            return None
        for group in self._runtime_groups:
            if not isinstance(group, dict):
                continue
            group_name = str(group.get("name", EMPTY_STRING)).strip().lower()
            if group_name == clean_name:
                return group
        return None

    def _bind_wrapped_label(self, container: tk.Widget, label: ttk.Label) -> None:
        """
        NAME
            _bind_wrapped_label - Keep one detail label wrapped to its container width.
        """
        def _update_wrap(_event=None) -> None:
            width = max(int(container.winfo_width()) - ROW_WRAP_PAD, ROW_WRAP_MIN)
            label.configure(wraplength=width)

        container.bind("<Configure>", _update_wrap, add="+")
        _update_wrap()

    def _format_group_number(self, value: object) -> str:
        """
        NAME
            _format_group_number - Format one generic numeric group-inspector field.
        """
        if not isinstance(value, (int, float)):
            return "--"
        return f"{float(value):.2f}"

    def _format_group_rpm(self, value: object) -> str:
        """
        NAME
            _format_group_rpm - Format one velocity field for the group inspector.
        """
        if not isinstance(value, (int, float)):
            return "--"
        return f"{float(value):.1f}{GROUP_INSPECTOR_RPM_SUFFIX}"

    def _format_group_current(self, value: object) -> str:
        """
        NAME
            _format_group_current - Format one current field for the group inspector.
        """
        if not isinstance(value, (int, float)):
            return "--"
        return f"{float(value):.2f}{GROUP_INSPECTOR_CURRENT_SUFFIX}"

    def _format_group_rot(self, value: object) -> str:
        """
        NAME
            _format_group_rot - Format one rotations field for the group inspector.
        """
        if not isinstance(value, (int, float)):
            return "--"
        return f"{float(value):.3f}{GROUP_INSPECTOR_ROT_SUFFIX}"

    def _update_active_group_summary(self) -> None:
        """
        NAME
            _update_active_group_summary - Render a concise member/status summary for the runtime active-group.
        """
        if self._active_group_summary_var is None:
            return
        active_group = None
        for group in self._runtime_groups:
            if not isinstance(group, dict):
                continue
            name = str(group.get("name", EMPTY_STRING)).strip().lower()
            if name == ACTIVE_GROUP_NAME:
                active_group = group
                break
        if not isinstance(active_group, dict):
            self._active_group_summary_var.set(ACTIVE_GROUP_NONE_TEXT)
            self._render_active_group_rows({})
            return
        members = active_group.get("members")
        member_map: Dict[str, Dict[str, object]] = {}
        if isinstance(members, list):
            for member in members:
                if not isinstance(member, dict):
                    continue
                label = str(member.get("label", EMPTY_STRING)).strip()
                if label:
                    member_map[label.lower()] = dict(member)
        primary_label = EMPTY_STRING
        if isinstance(members, list):
            for member in members:
                if not isinstance(member, dict):
                    continue
                label = str(member.get("label", EMPTY_STRING)).strip()
                if label:
                    primary_label = label
                    break
        if primary_label:
            self._active_group_summary_var.set(f"Primary: {primary_label}")
        else:
            self._active_group_summary_var.set(ACTIVE_GROUP_EMPTY_TEXT)
        self._render_active_group_rows(member_map, primary_label)

    def _eligible_active_group_labels(self) -> List[str]:
        """
        NAME
            _eligible_active_group_labels - Return eligible motor labels for the active-group management panel.
        """
        labels: List[str] = []
        seen = set()
        for node in self._nodes:
            label = str(getattr(node, "label", EMPTY_STRING)).strip()
            device_type = str(getattr(node, "device_type", EMPTY_STRING)).strip()
            if not label or device_type != ACTIVE_GROUP_ELIGIBLE_DEVICE_TYPE:
                continue
            key = label.lower()
            if key in seen:
                continue
            seen.add(key)
            labels.append(label)
        labels.sort(key=lambda item: item.lower())
        return labels

    def _render_active_group_rows(
        self,
        member_map: Dict[str, Dict[str, object]],
        primary_label: str = EMPTY_STRING,
    ) -> None:
        """
        NAME
            _render_active_group_rows - Render eligible-device membership rows for active-group management.
        """
        frame = self._active_group_rows_frame
        if frame is None:
            return
        eligible_labels = self._eligible_active_group_labels()
        expected_keys = {label.lower() for label in eligible_labels}
        stale_keys = [
            key for key in self._active_group_row_widgets.keys() if key not in expected_keys
        ]
        for key in stale_keys:
            widgets = self._active_group_row_widgets.pop(key, {})
            row_widget = widgets.get("row")
            if isinstance(row_widget, tk.Widget):
                row_widget.destroy()
            self._active_group_member_vars.pop(key, None)
        if not eligible_labels:
            if self._active_group_empty_label is None:
                self._active_group_empty_label = ttk.Label(
                    frame,
                    text=ACTIVE_GROUP_ELIGIBLE_EMPTY_TEXT,
                    anchor="w",
                    justify="left",
                )
                self._active_group_empty_label.pack(fill="x")
            else:
                self._active_group_empty_label.configure(text=ACTIVE_GROUP_ELIGIBLE_EMPTY_TEXT)
            return
        if self._active_group_empty_label is not None:
            self._active_group_empty_label.destroy()
            self._active_group_empty_label = None
        self._active_group_member_update_in_progress = True
        try:
            for label in eligible_labels:
                label_key = label.lower()
                member = member_map.get(label_key, {})
                checked = label_key in member_map
                enabled = member.get("enabled")
                if not checked:
                    enabled_text = ACTIVE_GROUP_MEMBER_ABSENT
                else:
                    enabled_text = (
                        ACTIVE_GROUP_MEMBER_ENABLED
                        if enabled is not False
                        else ACTIVE_GROUP_MEMBER_DISABLED
                    )
                live = self._runtime_state.get(label_key, {})
                presence = live.get("presenceConfidence")
                presence_text = (
                    f"{float(presence):.2f}"
                    if isinstance(presence, (int, float))
                    else "--"
                )
                probe = _runtime_active_probe_attachment(live)
                probe_bucket = (
                    str(probe.get(RUNTIME_KEY_ACTIVE_PROBE_BUCKET, "--")).strip()
                    if isinstance(probe, dict)
                    else "--"
                )
                probe_age = _runtime_probe_age_text(live) if isinstance(live, dict) else "--"
                manual_observation = self._manual_test_observations.get(label_key, {})
                vel_rpm = _runtime_device_field(live, "velRpm") if isinstance(live, dict) else None
                position_rot = _runtime_device_field(live, RUNTIME_KEY_POSITION_ROT) if isinstance(live, dict) else None
                position_delta_rot = None
                if _manual_observation_is_live(manual_observation):
                    position_delta_rot = manual_observation.get("positionDeltaRot")
                    max_abs_position_delta_rot = manual_observation.get("maxAbsPositionDeltaRot")
                    if (
                        not isinstance(position_delta_rot, (int, float))
                        and isinstance(max_abs_position_delta_rot, (int, float))
                    ):
                        position_delta_rot = max_abs_position_delta_rot
                selected_text = (
                    ACTIVE_GROUP_SELECTED_YES
                    if self._selected_label and label_key == self._selected_label
                    else ACTIVE_GROUP_SELECTED_NO
                )
                primary_text = (
                    ACTIVE_GROUP_PRIMARY_YES
                    if checked and label_key == primary_label.strip().lower()
                    else EMPTY_STRING
                )
                detail_parts = []
                if primary_text:
                    detail_parts.append(primary_text)
                detail_parts.append(enabled_text)
                detail_parts.append(f"{ACTIVE_GROUP_PRESENT_PREFIX}{presence_text}")
                detail_parts.append(f"{ACTIVE_GROUP_FULL_PROBE_PREFIX}{probe_bucket or '--'}/{probe_age}")
                detail_parts.append(f"{ACTIVE_GROUP_VEL_RPM_PREFIX}{self._format_group_rpm(vel_rpm)}")
                detail_parts.append(f"{ACTIVE_GROUP_POSITION_ROT_PREFIX}{self._format_group_rot(position_rot)}")
                detail_parts.append(
                    f"{ACTIVE_GROUP_POSITION_DELTA_ROT_PREFIX}{self._format_group_rot(position_delta_rot)}"
                )
                detail_parts.append(selected_text)
                widgets = self._active_group_row_widgets.get(label_key)
                if not isinstance(widgets, dict):
                    row = ttk.Frame(frame)
                    row.pack(fill="x", pady=(0, 2))
                    variable = tk.BooleanVar(value=checked)
                    top_line = ttk.Frame(row)
                    top_line.pack(fill="x")
                    ttk.Checkbutton(
                        top_line,
                        variable=variable,
                        command=lambda row_label=label: self._on_active_group_member_checkbox_toggled(row_label),
                    ).pack(side="left")
                    label_var = tk.StringVar(value=label)
                    ttk.Label(top_line, textvariable=label_var, anchor="w").pack(side="left")
                    detail_var = tk.StringVar(value=" | ".join(detail_parts))
                    detail_label = ttk.Label(
                        row,
                        textvariable=detail_var,
                        anchor="w",
                        justify="left",
                    )
                    detail_label.pack(fill="x", padx=(24, 0))
                    self._bind_wrapped_label(row, detail_label)
                    widgets = {
                        "row": row,
                        "label_var": label_var,
                        "detail_var": detail_var,
                        "variable": variable,
                    }
                    self._active_group_row_widgets[label_key] = widgets
                    self._active_group_member_vars[label_key] = variable
                label_var = widgets.get("label_var")
                detail_var = widgets.get("detail_var")
                variable = widgets.get("variable")
                if isinstance(label_var, tk.StringVar):
                    label_var.set(label)
                if isinstance(detail_var, tk.StringVar):
                    detail_var.set(" | ".join(detail_parts))
                if isinstance(variable, tk.BooleanVar):
                    variable.set(checked)
                    self._active_group_member_vars[label_key] = variable
        finally:
            self._active_group_member_update_in_progress = False

    def _on_active_group_member_checkbox_toggled(self, label: str) -> None:
        """
        NAME
            _on_active_group_member_checkbox_toggled - Forward one active-group membership toggle to the owning UI.
        """
        if self._active_group_member_update_in_progress:
            return
        callback = self._on_active_group_member_toggled_cb
        if not callable(callback):
            return
        key = str(label or EMPTY_STRING).strip().lower()
        variable = self._active_group_member_vars.get(key)
        if variable is None:
            return
        callback(str(label).strip(), bool(variable.get()))

    def _live_fill(self, node: LiveNode, now_ms: int) -> Optional[str]:
        evidence_fill = self._evidence_fill(node)
        if evidence_fill:
            return evidence_fill
        if self._visibility_enabled:
            vis_fill = self._visibility_fill(node)
            if vis_fill:
                return vis_fill
        if getattr(node, "interface", INTERFACE_CAN) != INTERFACE_CAN:
            return None
        override = self._presence_overrides.get(node.label.lower())
        if override:
            fill = self._presence_fill_from_confidence(override)
            if fill:
                return fill
        live = self._runtime_state.get(node.label.lower())
        if not live:
            return None
        presence = live.get("presenceConfidence")
        last_seen = live.get("lastSeenMs")
        if isinstance(presence, (int, float)) and presence <= PRESENCE_MIN_CONF:
            return PRESENCE_COLOR_NONE
        if isinstance(last_seen, (int, float)) and now_ms - int(last_seen) > PRESENCE_STALE_MS:
            return PRESENCE_COLOR_LOW
        if isinstance(presence, (int, float)):
            return PRESENCE_COLOR_HIGH if presence >= PRESENCE_HIGH_CONF else PRESENCE_COLOR_LOW
        if isinstance(last_seen, (int, float)):
            return PRESENCE_COLOR_HIGH
        return None

    def _evidence_fill(self, node: LiveNode) -> Optional[str]:
        """
        NAME
            _evidence_fill - Resolve fill color from interpreted evidence state.
        """
        state = self._evidence_state.get(node.label.lower())
        if state == EVIDENCE_STATE_OK:
            return EVIDENCE_COLOR_OK
        if state == EVIDENCE_STATE_DEGRADED:
            return EVIDENCE_COLOR_DEGRADED
        if state == EVIDENCE_STATE_MISSING:
            return EVIDENCE_COLOR_MISSING
        if state == EVIDENCE_STATE_IDENTITY:
            return EVIDENCE_COLOR_IDENTITY
        if state == EVIDENCE_STATE_UNKNOWN:
            return EVIDENCE_COLOR_UNKNOWN
        return None

    def _visibility_fill(self, node: LiveNode) -> Optional[str]:
        """
        NAME
            _visibility_fill - Resolve fill color from visibility state.
        """
        if node.category.lower() == CATEGORY_ANALYZER:
            availability = self._visibility_sources.get(node.label.lower())
            if availability is True:
                return VIS_COLOR_ALL
            return VIS_COLOR_UNKNOWN
        state = self._visibility_state.get(node.label.lower())
        if state == VIS_STATE_ALL:
            return VIS_COLOR_ALL
        if state == VIS_STATE_SOME:
            return VIS_COLOR_SOME
        if state == VIS_STATE_NONE:
            return VIS_COLOR_NONE
        if state == VIS_STATE_UNKNOWN:
            return VIS_COLOR_UNKNOWN
        return None

    def _redraw(self, _event: Optional[tk.Event] = None) -> None:
        self._canvas.delete("all")
        self._node_bounds = {}
        self._group_overlay_regions = []
        if not self._nodes:
            self._canvas.create_text(
                20,
                20,
                text="No diagram data loaded.",
                anchor="nw",
                fill="#6b7280",
                font=("Segoe UI", 11),
            )
            return
        width = max(self._canvas.winfo_width(), 1)
        height = max(self._canvas.winfo_height(), 1)
        scale = self._zoom
        base_y = height * 0.5 + self._pan_y
        active_filters = self._active_connection_filters()
        show_can = FILTER_CAN in active_filters
        bus_count = max((n.bus_index for n in self._nodes), default=0) + 1
        while len(self._bus_offsets) < bus_count:
            self._bus_offsets.append(0.0)
        now_ms = int(time.time() * 1000)
        min_x = min((n.x for n in self._nodes), default=0.0)
        max_x = max((n.x for n in self._nodes), default=0.0)
        x_shift = 0.0 if self._use_diagram_layout else min_x
        bus_ys_list = bus_ys(base_y, self._bus_offsets, scale)

        _bus_lefts, _bus_rights, eff_lefts, eff_rights = effective_bus_bounds(
            list(self._bus_offsets),
            list(self._bus_lefts),
            list(self._bus_rights),
            max_x,
        )
        selected_keys = set()
        if self._selected_node is not None and getattr(self._selected_node, "key", None) is not None:
            selected_keys.add(self._selected_node.key)
        if self._selected_label:
            selected_keys.update(
                node.key
                for node in self._nodes
                if node.label.strip().lower() == self._selected_label
            )
        rendered = render_topology_canvas_common(
            canvas=self._canvas,
            nodes=self._nodes,
            bus_ys=bus_ys_list,
            base_y=base_y,
            scale=scale,
            x_shift=x_shift,
            eff_lefts=eff_lefts,
            eff_rights=eff_rights,
            show_can=show_can,
            show_dio=FILTER_DIO in active_filters,
            show_virtual=FILTER_VIRTUAL in active_filters,
            show_power=FILTER_POWER in active_filters,
            groups=self._effective_groups(),
            selected_node_keys=selected_keys,
            selected_bus_indices=set(),
            drag_free_y={},
            bus_connectors=[],
            bus_connector_sides=getattr(self, "_bus_connector_sides", []),
            bus_lefts=eff_lefts,
            bus_rights=eff_rights,
            min_x=min_x,
            max_x=max_x,
            bus_offsets=self._bus_offsets,
            box_w_base=NODE_BOX_BASE_W,
            box_h_base=NODE_BOX_BASE_H,
            linked_devices={int(link.get("device")) for link in self._device_links if "device" in link},
            can_bus_links=self._can_links,
            device_links=self._device_links,
            power_links=self._power_links,
            attachment_links=self._attachment_links,
            dio_links=self._dio_links,
            ethernet_links=self._ethernet_links,
            show_groups=self._show_groups,
            node_box_dims_fn=lambda node, scale_value: node_box_dims(node, NODE_BOX_BASE_W, NODE_BOX_BASE_H, scale_value),
            node_bus_y_fn=lambda _node, bus_y_value, _scale: bus_y_value,
            node_box_y_fn=node_box_y,
            node_center_y_unscaled_fn=lambda node: node_center_y_unscaled(node, self._bus_offsets, NODE_BOX_BASE_H),
            should_clamp_node_to_bus_fn=lambda _node: False,
            is_swyft_node_fn=lambda node: node.category in ("cannect_direct", "cannect_inject"),
            is_dio_node_fn=lambda node: getattr(node, "interface", INTERFACE_CAN) != INTERFACE_CAN,
            shape_kind_fn=lambda node: shape_kind_for_category(node.category),
            fill_color_fn=lambda node: self._live_fill(node, now_ms) or fill_color_for_vendor(vendor_key_for_category(node.category, node.vendor)),
            outline_color_fn=lambda node: outline_color_for_vendor(vendor_key_for_category(node.category, node.vendor)),
            text_color_fn=text_color_for_fill,
            label_text_fn=lambda node: node.label,
            fit_font_size_fn=fit_font_size,
            wrap_label_lines_fn=wrap_label_lines,
            is_callout_fn=lambda node: node.node_type == LEGACY_NODE_TYPE_CALLOUT,
            show_selection_box=True,
        )
        self._node_bounds = rendered["node_bounds"]
        self._group_overlay_regions = list(rendered.get("group_overlay_regions", []))
