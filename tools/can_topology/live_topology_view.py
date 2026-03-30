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
from typing import Dict, List, Optional, Tuple

import tkinter as tk
from tkinter import ttk

from tools.common.json_io import read_json
from tools.common.paths import profiles_canonical_path, profiles_deploy_path, repo_root
import tkinter.font as tkfont

from tools.common.profile_constants import (
    INTERFACE_CAN,
    KEY_DEFAULT_PROFILE,
    KEY_DEVICE_TYPE,
    KEY_DEVICES,
    KEY_ID,
    KEY_INTERFACE,
    KEY_LABEL,
    KEY_MANUFACTURER,
    KEY_MODEL,
    KEY_PROFILES,
    KEY_PROFILE_DEVICES,
)
from tools.config.schema_store import ConfigSchemaStore
from tools.common.topology_render import (
    fill_color_for_vendor,
    outline_color_for_vendor,
    shape_kind_for_category,
    text_color_for_fill,
    vendor_key_for_category,
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
    parse_diagram_links,
    parse_diagram_nodes,
)
from tools.common.topology_draw import draw_bus_segments, draw_group_overlays, draw_links

# Constants (presence confidence values and colors).
PRESENCE_CONF_HIGH = "HIGH"
PRESENCE_CONF_LOW = "LOW"
PRESENCE_CONF_NONE = "NONE"
PRESENCE_COLOR_HIGH = "#2f7a2f"
PRESENCE_COLOR_LOW = "#f59e0b"
PRESENCE_COLOR_NONE = "#dc2626"
PRESENCE_STALE_MS = 2000
PRESENCE_MIN_CONF = 0.05
PRESENCE_HIGH_CONF = 0.5
EMPTY_STRING = ""

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
    y: Optional[float] = None
    free_y: Optional[float] = None


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
        path = profiles_deploy_path()
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
        if not entry or entry.get(KEY_INTERFACE) != INTERFACE_CAN:
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
    for entry in parse_diagram_nodes(diagram):
        if not isinstance(entry, dict):
            continue
        node_type = str(entry.get("nodeType") or "device")
        if entry.get("profileVisible") is False and node_type != "diagram":
            continue
        if node_type == "callout":
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
                    node_type="callout",
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
                bus_offset = float(diagram.get("busOffsets", [0.0])[bus_index]) if diagram.get("busOffsets") else 0.0
                free_y = free_y - bus_offset
        raw_key = entry.get("key")
        node_key = int(raw_key) if isinstance(raw_key, int) else key
        can_id = entry.get("id") if isinstance(entry.get("id"), int) else NODE_CAN_ID_DEFAULT
        registry_entry = registry.get(label.strip().lower())
        if can_id == NODE_CAN_ID_DEFAULT and registry_entry:
            reg_id = registry_entry.get(KEY_ID)
            if isinstance(reg_id, int):
                can_id = reg_id
        nodes.append(
            LiveNode(
                key=node_key,
                category=str(entry.get("category") or CATEGORY_DEVICES),
                label=label,
                can_id=int(can_id) if isinstance(can_id, int) else NODE_CAN_ID_DEFAULT,
                bus_index=bus_index,
                row=int(entry.get("row") or 0),
                x=float(entry.get("x") or 0.0),
                scale=float(entry.get("scale") or 1.0),
                node_type=node_type,
                free_y=free_y,
            )
        )
        key += 1
    return nodes, diagram


class LiveTopologyView(ttk.Frame):
    """
    NAME
        LiveTopologyView - Read-only topology canvas with live overlays.
    """

    def __init__(self, parent: tk.Widget, profile_name: str) -> None:
        super().__init__(parent)
        self._profile_name = profile_name
        self._nodes: List[LiveNode] = []
        self._diagram_meta: Dict[str, object] = {}
        self._runtime_state: Dict[str, Dict[str, object]] = {}
        self._presence_overrides: Dict[str, str] = {}
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
        self._bridge_groups: List[Dict[str, object]] = []
        self._show_groups = True
        self._runtime_fingerprint: Optional[Tuple[object, ...]] = None

        header = ttk.Frame(self)
        header.pack(fill="x", padx=8, pady=(8, 0))
        ttk.Label(header, text="Live Topology", font=("Trebuchet MS", 13)).pack(
            side="left"
        )
        self._status_label = ttk.Label(header, text="Profile: --")
        self._status_label.pack(side="left", padx=(12, 0))

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
        self._canvas.bind("<Control-MouseWheel>", self._on_mousewheel_zoom)
        self._canvas.bind("<Control-Button-4>", lambda _e: self._nudge_zoom(0.1))
        self._canvas.bind("<Control-Button-5>", lambda _e: self._nudge_zoom(-0.1))

        details = ttk.LabelFrame(body, text="Selection", padding=8)
        details.pack(side="right", fill="y")
        self._detail_vars = {
            "label": tk.StringVar(value="--"),
            "can_id": tk.StringVar(value="--"),
            "presence": tk.StringVar(value="--"),
            "last_seen": tk.StringVar(value="--"),
            "current_a": tk.StringVar(value="--"),
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
        if isinstance(diag, dict):
            nodes, meta = _diagram_nodes(diag, registry)
            self._nodes = nodes
            self._diagram_meta = meta
            self._use_diagram_layout = True
            self._bus_spacing = float(meta.get("busSpacing") or 160.0)
            self._bus_offsets = [float(v) for v in (meta.get("busOffsets") or [0.0])]
            self._bus_lefts = [float(v) for v in (meta.get("busLefts") or [])]
            self._bus_rights = [float(v) for v in (meta.get("busRights") or [])]
            self._pan_y = float(meta.get("panY") or 0.0)
            self._zoom = float(meta.get("zoom") or 1.0)
            self._ethernet_links, self._can_links, self._device_links = parse_diagram_links(meta)
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
        if isinstance(payload, dict):
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
            current_a = device.get("motorCurrentA")
            if isinstance(current_a, (int, float)):
                current_a = round(float(current_a), 1)
            cmd_duty = device.get("cmdDuty")
            if isinstance(cmd_duty, (int, float)):
                cmd_duty = round(float(cmd_duty), 2)
            applied_duty = device.get("appliedDuty")
            if isinstance(applied_duty, (int, float)):
                applied_duty = round(float(applied_duty), 2)
            temp_c = device.get("tempC")
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
        )
        if fingerprint == self._runtime_fingerprint:
            return False
        self._runtime_fingerprint = fingerprint
        self._runtime_state = mapped
        self._selected_label = selected_label
        self._selected_enabled = selected_enabled
        self._update_details()
        self._redraw()
        return True

    def _on_canvas_click(self, event: tk.Event) -> None:
        """
        NAME
            _on_canvas_click - Select node on click.
        """
        x = self._canvas.canvasx(event.x)
        y = self._canvas.canvasy(event.y)
        for key, bounds in self._node_bounds.items():
            x0, y0, x1, y1 = bounds
            if x0 <= x <= x1 and y0 <= y <= y1:
                self._selected_node = next((n for n in self._nodes if n.key == key), None)
                self._update_details()
                return
        self._selected_node = None
        self._update_details()

    def _on_mousewheel_zoom(self, event: tk.Event) -> None:
        """
        NAME
            _on_mousewheel_zoom - Zoom with Ctrl + mouse wheel.
        """
        delta = 0.1 if event.delta > 0 else -0.1
        self._nudge_zoom(delta)

    def _nudge_zoom(self, delta: float) -> None:
        """
        NAME
            _nudge_zoom - Increment zoom with clamping.
        """
        new_zoom = max(0.1, min(2.0, self._zoom + delta))
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
            presence = live.get("presenceConfidence")
            last_seen = live.get("lastSeenMs")
            current_a = live.get("motorCurrentA")
            cmd_duty = live.get("cmdDuty")
            applied_duty = live.get("appliedDuty")
            temp_c = live.get("tempC")
            self._detail_vars["presence"].set(
                f"{float(presence):.2f}" if isinstance(presence, (int, float)) else "--"
            )
            self._detail_vars["last_seen"].set(
                str(int(last_seen)) if isinstance(last_seen, (int, float)) else "--"
            )
            self._detail_vars["current_a"].set(
                f"{float(current_a):.2f}" if isinstance(current_a, (int, float)) else "--"
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
        draw_bus_segments(
            self._canvas,
            bus_ys_list,
            eff_lefts,
            eff_rights,
            scale=scale,
            min_x=min_x,
            max_x=max_x,
            x_shift=x_shift,
        )

        bounds = []
        node_centers: Dict[int, Tuple[float, float]] = {}
        for node in self._nodes:
            base_w = 140.0
            base_h = 60.0
            box_w, box_h = node_box_dims(node, base_w, base_h, scale)
            node_x = (node.x - x_shift) * scale
            bus_index = min(max(node.bus_index, 0), max(len(bus_ys_list) - 1, 0))
            bus_y = bus_ys_list[bus_index] if bus_ys_list else base_y
            if node.node_type == "callout" and node.y is not None:
                center_y = base_y + node.y * scale
            elif node.free_y is not None:
                center_y = base_y + node_center_y_unscaled(node, self._bus_offsets, base_h) * scale
            else:
                y0, y1 = node_box_y(node, bus_y, box_h, scale)
                center_y = (y0 + y1) / 2.0
            x0 = node_x - box_w / 2
            x1 = node_x + box_w / 2
            y0 = center_y - box_h / 2
            y1 = center_y + box_h / 2
            node_centers[node.key] = (node_x, center_y)
            vendor_key = vendor_key_for_category(node.category, node.vendor)
            base_fill = fill_color_for_vendor(vendor_key)
            outline = outline_color_for_vendor(vendor_key)
            live_fill = self._live_fill(node, now_ms)
            fill = live_fill or base_fill
            text_color = text_color_for_fill(fill)
            kind = shape_kind_for_category(node.category)
            if node.node_type == "callout":
                self._canvas.create_text(
                    (x0 + x1) / 2,
                    (y0 + y1) / 2,
                    text=node.label,
                    fill="#1f2937",
                    font=("Segoe UI", 9),
                    justify="center",
                )
            elif kind == "motor":
                self._canvas.create_polygon(
                    x0 + 10,
                    y0,
                    x1 - 10,
                    y0,
                    x1,
                    y0 + 10,
                    x1,
                    y1 - 10,
                    x1 - 10,
                    y1,
                    x0 + 10,
                    y1,
                    x0,
                    y1 - 10,
                    x0,
                    y0 + 10,
                    fill=fill,
                    outline=outline,
                    width=2,
                )
            else:
                self._canvas.create_rectangle(x0, y0, x1, y1, fill=fill, outline=outline, width=2)
            if node.node_type == "diagram":
                font_size = fit_font_size(
                    node.label, box_w - 10, box_h - 10, int(9 * scale * max(0.6, min(2.0, node.scale)))
                )
                self._canvas.create_text(
                    (x0 + x1) / 2,
                    (y0 + y1) / 2,
                    text=node.label,
                    fill=text_color,
                    font=("Segoe UI", font_size),
                    justify="center",
                    width=max(40, int(box_w - 10)),
                )
            elif node.node_type != "callout":
                label_text = node.label
                if isinstance(node.can_id, int) and node.can_id >= 0:
                    id_font_size = max(6, int(8 * scale * max(0.6, min(2.0, node.scale))))
                    id_font = tkfont.Font(family="Segoe UI", size=id_font_size)
                    id_line_h = id_font.metrics("linespace")
                    label_max_h = max(8.0, box_h - id_line_h - 6 * scale)
                    label_font_size = max(6, int(9 * scale * max(0.6, min(2.0, node.scale))))
                    label_font = tkfont.Font(family="Segoe UI", size=label_font_size)
                    label_lines = wrap_label_lines(label_text, label_font, box_w - 12)
                    label_text_wrapped = "\n".join(label_lines)
                    label_font_size = fit_font_size(
                        label_text_wrapped, box_w - 12, label_max_h, label_font_size
                    )
                    label_y = (y0 + y1) / 2 - id_line_h * 0.4
                    self._canvas.create_text(
                        node_x,
                        label_y,
                        text=label_text_wrapped,
                        font=("Segoe UI", label_font_size),
                        fill=text_color,
                        justify="center",
                        width=max(40, int(box_w - 12)),
                    )
                    id_text = f"ID {node.can_id}"
                    self._canvas.create_text(
                        node_x,
                        y1 - id_line_h * 0.6,
                        text=id_text,
                        font=("Segoe UI", id_font_size),
                        fill=text_color,
                        justify="center",
                    )
                else:
                    font_size = fit_font_size(
                        label_text, box_w - 10, box_h - 10, int(9 * scale * max(0.6, min(2.0, node.scale)))
                    )
                    self._canvas.create_text(
                        (x0 + x1) / 2,
                        (y0 + y1) / 2,
                        text=label_text,
                        fill=text_color,
                        font=("Segoe UI", font_size),
                        justify="center",
                        width=max(40, int(box_w - 10)),
                    )
            if self._selected_label and node.label.strip().lower() == self._selected_label:
                self._canvas.create_rectangle(
                    x0 - 4, y0 - 4, x1 + 4, y1 + 4, outline="#2563eb", width=2
                )
            self._node_bounds[node.key] = (x0, y0, x1, y1)
            bounds.append((x0, y0, x1, y1))

        if self._show_groups and self._bridge_groups:
            label_bounds: Dict[str, Tuple[float, float, float, float]] = {}
            for node in self._nodes:
                node_bounds = self._node_bounds.get(node.key)
                if node_bounds:
                    label_bounds[node.label] = node_bounds
            draw_group_overlays(
                self._canvas,
                label_bounds,
                self._bridge_groups,
                zoom=scale,
            )

        if bounds:
            min_x0 = min(b[0] for b in bounds) - 40
            min_y0 = min(b[1] for b in bounds) - 40
            max_x1 = max(b[2] for b in bounds) + 40
            max_y1 = max(b[3] for b in bounds) + 40
            self._canvas.configure(scrollregion=(min_x0, min_y0, max_x1, max_y1))

        linked_devices = {int(link.get("device")) for link in self._device_links if "device" in link}
        cannect_nodes = [
            {
                "node": node.key,
                "bus": node.bus_index,
                "kind": "inject" if node.category == "cannect_inject" else "direct",
            }
            for node in self._nodes
            if node.category in ("cannect_direct", "cannect_inject")
        ]
        if self._ethernet_links or self._can_links or self._device_links or cannect_nodes:
            draw_links(
                self._canvas,
                node_centers,
                self._node_bounds,
                bus_ys_list,
                self._ethernet_links,
                self._can_links,
                self._device_links,
                cannect_nodes,
            )

        for node in self._nodes:
            if node.node_type != "device":
                continue
            if node.key in linked_devices:
                continue
            if node.key not in node_centers or not bus_ys_list:
                continue
            bus_index = min(max(node.bus_index, 0), max(len(bus_ys_list) - 1, 0))
            bus_y = bus_ys_list[bus_index]
            cx, cy = node_centers[node.key]
            bounds = self._node_bounds.get(node.key)
            if bounds is None:
                continue
            x0, y0, x1, y1 = bounds
            line_y = y0 if cy > bus_y else y1
            self._canvas.create_line(cx, bus_y, cx, line_y, width=2, fill="#444444")
