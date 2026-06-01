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
from typing import Callable, Dict, List, Optional, Tuple

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
RUNTIME_KEY_MOTOR_CURRENT_A = "motorCurrentA"
RUNTIME_KEY_CURRENT_INSTANT_A = "currentInstantA"
RUNTIME_KEY_CURRENT_AVG_A = "currentAvgA"
RUNTIME_KEY_CURRENT_PEAK_A = "currentPeakA"
RUNTIME_KEY_CURRENT_NONZERO_RATIO = "currentNonzeroRatio"
RUNTIME_KEY_CURRENT_SAMPLE_COUNT = "currentSampleCount"
RUNTIME_CURRENT_DISPLAY_MIN_A = 0.05


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
        on_left_click: Optional[Callable[[Optional[LiveNode], tk.Event], None]] = None,
    ) -> None:
        super().__init__(parent)
        self._profile_name = profile_name
        self._nodes: List[LiveNode] = []
        self._diagram_meta: Dict[str, object] = {}
        self._runtime_state: Dict[str, Dict[str, object]] = {}
        self._presence_overrides: Dict[str, str] = {}
        self._visibility_enabled = False
        self._visibility_state: Dict[str, str] = {}
        self._visibility_sources: Dict[str, bool] = {}
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
        self._selected_node: Optional[LiveNode] = None
        self._use_diagram_layout = False
        self._ethernet_links: List[Tuple[int, int]] = []
        self._can_links: List[Dict[str, int]] = []
        self._device_links: List[Dict[str, int]] = []
        self._power_links: List[Tuple[int, int]] = []
        self._attachment_links: List[Tuple[int, int]] = []
        self._dio_links: List[Tuple[int, int]] = []
        self._bridge_groups: List[Dict[str, object]] = []
        self._show_groups = True
        self._runtime_fingerprint: Optional[Tuple[object, ...]] = None
        self._runtime_state_notice_text = EMPTY_STRING
        self._runtime_state_notice_level = "info"
        self._runtime_event_notice_text = EMPTY_STRING
        self._runtime_event_notice_level = "warn"
        self._on_node_right_click_cb = on_node_right_click
        self._on_left_click_cb = on_left_click
        self._connection_filter_vars = {
            key: tk.BooleanVar(value=True) for key in CONNECTION_FILTERS_ORDER
        }

        header = ttk.Frame(self)
        header.pack(fill="x", padx=8, pady=(8, 0))
        ttk.Label(header, text="Live Topology", font=("Trebuchet MS", 13)).pack(
            side="left"
        )
        self._status_label = ttk.Label(header, text="Profile: --")
        self._status_label.pack(side="left", padx=(12, 0))
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
        self._notice_label.pack(fill="x", padx=8, pady=(6, 0))
        self._notice_label.pack_forget()
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

        canvas_frame = ttk.Frame(body)
        canvas_frame.pack(side="left", fill="both", expand=True)
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

        details = ttk.LabelFrame(body, text="Selection", padding=8)
        details.pack(side="right", fill="y")
        self._detail_vars = {
            "label": tk.StringVar(value="--"),
            "can_id": tk.StringVar(value="--"),
            "presence": tk.StringVar(value="--"),
            "last_seen": tk.StringVar(value="--"),
            "current_a": tk.StringVar(value="--"),
            "current_avg_a": tk.StringVar(value="--"),
            "current_peak_a": tk.StringVar(value="--"),
            "current_nonzero": tk.StringVar(value="--"),
            "current_samples": tk.StringVar(value="--"),
            "cmd_duty": tk.StringVar(value="--"),
            "applied_duty": tk.StringVar(value="--"),
            "temp_c": tk.StringVar(value="--"),
            "selected": tk.StringVar(value="--"),
        }
        rows = [
            ("Label", "label"),
            ("CAN ID", "can_id"),
            ("Presence", "presence"),
            ("Last Seen", "last_seen"),
            ("Current (A)", "current_a"),
            ("Current Avg (A)", "current_avg_a"),
            ("Current Peak (A)", "current_peak_a"),
            ("Current Nonzero", "current_nonzero"),
            ("Current Window Samples", "current_samples"),
            ("Cmd Duty", "cmd_duty"),
            ("Applied Duty", "applied_duty"),
            ("Temp (C)", "temp_c"),
            ("Selected", "selected"),
        ]
        for idx, (title, key) in enumerate(rows):
            ttk.Label(details, text=f"{title}:").grid(row=idx, column=0, sticky="w", padx=4)
            ttk.Label(details, textvariable=self._detail_vars[key]).grid(
                row=idx, column=1, sticky="w"
            )

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
        fingerprint_items: List[Tuple[object, ...]] = []
        for label, device in mapped.items():
            presence = device.get("presenceConfidence")
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
            temp_c = _runtime_device_field(device, "tempC")
            if isinstance(temp_c, (int, float)):
                temp_c = round(float(temp_c), 1)
            fingerprint_items.append(
                (
                    label,
                    presence_bucket,
                    last_seen_bucket,
                    current_a,
                    cmd_duty,
                    applied_duty,
                    temp_c,
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
        )
        if fingerprint == self._runtime_fingerprint:
            return False
        self._runtime_fingerprint = fingerprint
        self._runtime_state = mapped
        self._selected_label = selected_label
        self._selected_enabled = selected_enabled
        self._apply_runtime_notice_from_state(runtime_active, robot_enabled, robot_estopped)
        self._update_details()
        self._redraw()
        return True

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
        self._notice_label.pack(fill="x", padx=8, pady=(6, 0))

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
                if callable(self._on_node_right_click_cb):
                    self._on_node_right_click_cb(node, event)
                return

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
        node = self._selected_node
        if node is None:
            for key in self._detail_vars:
                self._detail_vars[key].set("--")
            return
        self._detail_vars["label"].set(node.label)
        self._detail_vars["can_id"].set(str(node.can_id) if node.can_id >= 0 else "--")
        live = self._runtime_state.get(node.label.lower())
        if live:
            now_ms = int(time.time() * 1000)
            presence = live.get("presenceConfidence")
            last_seen = live.get("lastSeenMs")
            current_a = _runtime_display_current_a(live)
            current_avg_a = _runtime_device_field(live, RUNTIME_KEY_CURRENT_AVG_A)
            current_peak_a = _runtime_device_field(live, RUNTIME_KEY_CURRENT_PEAK_A)
            current_nonzero = _runtime_device_field(live, RUNTIME_KEY_CURRENT_NONZERO_RATIO)
            current_samples = _runtime_device_field(live, RUNTIME_KEY_CURRENT_SAMPLE_COUNT)
            cmd_duty = _runtime_device_field(live, "cmdDuty")
            applied_duty = _runtime_device_field(live, "appliedDuty")
            temp_c = _runtime_device_field(live, "tempC")
            self._detail_vars["presence"].set(
                f"{float(presence):.2f}" if isinstance(presence, (int, float)) else "--"
            )
            self._detail_vars["last_seen"].set(_format_last_seen(last_seen, now_ms))
            self._detail_vars["current_a"].set(
                f"{float(current_a):.2f}" if isinstance(current_a, (int, float)) else "--"
            )
            self._detail_vars["current_avg_a"].set(
                f"{float(current_avg_a):.2f}"
                if isinstance(current_avg_a, (int, float))
                else "--"
            )
            self._detail_vars["current_peak_a"].set(
                f"{float(current_peak_a):.2f}"
                if isinstance(current_peak_a, (int, float))
                else "--"
            )
            self._detail_vars["current_nonzero"].set(
                f"{float(current_nonzero):.2f}"
                if isinstance(current_nonzero, (int, float))
                else "--"
            )
            self._detail_vars["current_samples"].set(
                str(int(current_samples))
                if isinstance(current_samples, (int, float))
                else "--"
            )
            self._detail_vars["cmd_duty"].set(
                f"{float(cmd_duty):.2f}" if isinstance(cmd_duty, (int, float)) else "--"
            )
            self._detail_vars["applied_duty"].set(
                f"{float(applied_duty):.2f}" if isinstance(applied_duty, (int, float)) else "--"
            )
            self._detail_vars["temp_c"].set(
                f"{float(temp_c):.1f}" if isinstance(temp_c, (int, float)) else "--"
            )
        else:
            self._detail_vars["presence"].set("--")
            self._detail_vars["last_seen"].set("--")
            self._detail_vars["current_a"].set("--")
            self._detail_vars["current_avg_a"].set("--")
            self._detail_vars["current_peak_a"].set("--")
            self._detail_vars["current_nonzero"].set("--")
            self._detail_vars["current_samples"].set("--")
            self._detail_vars["cmd_duty"].set("--")
            self._detail_vars["applied_duty"].set("--")
            self._detail_vars["temp_c"].set("--")
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
        self._detail_vars["selected"].set(selected_text)

    def _live_fill(self, node: LiveNode, now_ms: int) -> Optional[str]:
        if self._visibility_enabled:
            vis_fill = self._visibility_fill(node)
            if vis_fill:
                return vis_fill
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
        selected_keys = {
            node.key
            for node in self._nodes
            if self._selected_label and node.label.strip().lower() == self._selected_label
        }
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
            groups=self._bridge_groups,
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
