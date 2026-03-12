#!/usr/bin/env python3
"""
NAME
    can_topology_editor.py - Simple CAN bus topology editor (diagram -> profile).

SYNOPSIS
    python -m tools.can_topology.can_topology_editor

DESCRIPTION
    Opens a small GUI that lets you place CAN nodes on a shared bus line and
    export a bringup profile JSON. This tool is Windows-friendly and relies
    only on the Python standard library (tkinter).

SIDE EFFECTS
    Opens a GUI window and reads/writes JSON files.

ERRORS
    Shows dialog errors for invalid data and file I/O failures.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import tkinter as tk
from tkinter import ttk, filedialog, messagebox


BUCKET_CATEGORIES = [
    "neos",
    "neo550s",
    "flexes",
    "krakens",
    "falcons",
    "cancoders",
    "candles",
]
SINGLETON_CATEGORIES = ["pdh", "pdp", "pigeon", "roborio"]
GENERIC_CATEGORY = "devices"

DEFAULT_MANUFACTURERS = [
    "CTRE",
    "REV",
    "KauaiLabs",
    "PlayingWithFusion",
    "AndyMark",
]
DEFAULT_DEVICE_TYPES = [
    "MotorController",
    "Encoder",
    "GyroSensor",
    "PowerDistributionModule",
    "PneumaticsController",
    "Miscellaneous",
]


def _load_can_mappings() -> Tuple[List[str], List[str]]:
    """
    NAME
        _load_can_mappings - Load manufacturer and device type names.

    DESCRIPTION
        Attempts to read src/main/deploy/can_mappings.json to populate dropdowns.
        Falls back to a small built-in list if unavailable.

    RETURNS
        Tuple of (manufacturers, device_types) lists.
    """
    try:
        root = Path(__file__).resolve().parents[2]
        path = root / "src" / "main" / "deploy" / "can_mappings.json"
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        manufacturers = sorted(set(str(v) for v in data.get("manufacturers", {}).values()))
        device_types = sorted(set(str(v) for v in data.get("device_types", {}).values()))
        if manufacturers and device_types:
            return manufacturers, device_types
    except Exception:
        pass
    return DEFAULT_MANUFACTURERS, DEFAULT_DEVICE_TYPES


SUPPORTED_MANUFACTURERS, SUPPORTED_DEVICE_TYPES = _load_can_mappings()


@dataclass
class Node:
    """
    NAME
        Node - In-memory representation of a CAN node on the diagram.

    DESCRIPTION
        Holds diagram data and profile fields for one CAN device. The x
        coordinate is only used for display and is not saved into the profile.
    """

    key: int
    category: str
    label: str
    can_id: int
    vendor: str = ""
    device_type: str = ""
    motor: str = ""
    limits: Optional[Dict[str, int | bool]] = None
    terminator: Optional[bool] = None
    x: float = 0.0
    row: int = 0
    bus_index: int = 0

    def display_text(self) -> str:
        """
        NAME
            display_text - Build a short label for the canvas.

        RETURNS
            Text string used for the node box label.
        """
        if self.category == GENERIC_CATEGORY and self.vendor and self.device_type:
            return f"{self.vendor} {self.device_type}\n{self.label} (id {self.can_id})"
        return f"{self.category}\n{self.label} (id {self.can_id})"


class NodeDialog(tk.Toplevel):
    """
    NAME
        NodeDialog - Modal dialog for adding or editing a CAN node.

    DESCRIPTION
        Collects fields required for a bringup profile entry and returns a
        Node-like dict to the caller when confirmed.
    """

    def __init__(self, master: tk.Widget, title: str, initial: Optional[Node] = None):
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.result: Optional[Dict[str, object]] = None
        self._build_ui(initial)
        self.transient(master)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _build_ui(self, initial: Optional[Node]) -> None:
        """
        NAME
            _build_ui - Construct dialog widgets.
        """
        frame = ttk.Frame(self, padding=12)
        frame.grid(row=0, column=0, sticky="nsew")

        categories = BUCKET_CATEGORIES + [GENERIC_CATEGORY] + SINGLETON_CATEGORIES
        self.var_category = tk.StringVar(value=initial.category if initial else BUCKET_CATEGORIES[0])
        self.var_label = tk.StringVar(value=initial.label if initial else "")
        self.var_can_id = tk.StringVar(value=str(initial.can_id) if initial else "")
        self.var_vendor = tk.StringVar(value=initial.vendor if initial else "")
        self.var_type = tk.StringVar(value=initial.device_type if initial else "")
        self.var_motor = tk.StringVar(value=initial.motor if initial else "")
        self.var_fwd = tk.StringVar(
            value=str(initial.limits.get("fwdDio")) if initial and initial.limits else ""
        )
        self.var_rev = tk.StringVar(
            value=str(initial.limits.get("revDio")) if initial and initial.limits else ""
        )
        self.var_invert = tk.BooleanVar(
            value=bool(initial.limits.get("invert")) if initial and initial.limits else False
        )
        self.var_terminator = tk.BooleanVar(
            value=bool(initial.terminator) if initial and initial.terminator is not None else False
        )

        ttk.Label(frame, text="Category").grid(row=0, column=0, sticky="w")
        self.combo_category = ttk.Combobox(
            frame, textvariable=self.var_category, values=categories, state="readonly", width=22
        )
        self.combo_category.grid(row=0, column=1, sticky="w")
        self.combo_category.bind("<<ComboboxSelected>>", lambda _e: self._sync_fields())

        ttk.Label(frame, text="Label").grid(row=1, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.var_label, width=28).grid(row=1, column=1, sticky="w")

        ttk.Label(frame, text="CAN ID").grid(row=2, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.var_can_id, width=10).grid(row=2, column=1, sticky="w")

        self.label_vendor = ttk.Label(frame, text="Vendor")
        self.label_vendor.grid(row=3, column=0, sticky="w")
        self.entry_vendor = ttk.Combobox(
            frame,
            textvariable=self.var_vendor,
            values=SUPPORTED_MANUFACTURERS,
            width=26,
            state="normal",
        )
        self.entry_vendor.grid(row=3, column=1, sticky="w")

        self.label_type = ttk.Label(frame, text="Device Type")
        self.label_type.grid(row=4, column=0, sticky="w")
        self.entry_type = ttk.Combobox(
            frame,
            textvariable=self.var_type,
            values=SUPPORTED_DEVICE_TYPES,
            width=26,
            state="normal",
        )
        self.entry_type.grid(row=4, column=1, sticky="w")

        ttk.Label(frame, text="Motor (optional)").grid(row=5, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.var_motor, width=28).grid(row=5, column=1, sticky="w")

        ttk.Label(frame, text="Limit Fwd DIO").grid(row=6, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.var_fwd, width=10).grid(row=6, column=1, sticky="w")

        ttk.Label(frame, text="Limit Rev DIO").grid(row=7, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.var_rev, width=10).grid(row=7, column=1, sticky="w")

        ttk.Checkbutton(frame, text="Invert Limits", variable=self.var_invert).grid(
            row=8, column=1, sticky="w"
        )

        ttk.Checkbutton(frame, text="Bus Terminator", variable=self.var_terminator).grid(
            row=9, column=1, sticky="w"
        )

        button_row = ttk.Frame(frame)
        button_row.grid(row=10, column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(button_row, text="Cancel", command=self._on_cancel).grid(row=0, column=0, padx=4)
        ttk.Button(button_row, text="OK", command=self._on_ok).grid(row=0, column=1, padx=4)

        self._sync_fields()

    def _sync_fields(self) -> None:
        """
        NAME
            _sync_fields - Enable or disable vendor/type fields.
        """
        is_generic = self.var_category.get() == GENERIC_CATEGORY
        state = "normal" if is_generic else "disabled"
        for widget in (self.entry_vendor, self.entry_type):
            widget.configure(state=state)
        for widget in (self.label_vendor, self.label_type):
            widget.configure(state="normal")

    def _on_ok(self) -> None:
        """
        NAME
            _on_ok - Validate input and store result.
        """
        label = self.var_label.get().strip()
        can_id_raw = self.var_can_id.get().strip()
        category = self.var_category.get().strip()
        if not label:
            messagebox.showerror("Invalid", "Label is required.")
            return
        try:
            can_id = int(can_id_raw)
        except ValueError:
            messagebox.showerror("Invalid", "CAN ID must be an integer.")
            return
        if category == GENERIC_CATEGORY:
            vendor = self.var_vendor.get().strip()
            dev_type = self.var_type.get().strip()
            if not vendor or not dev_type:
                messagebox.showerror("Invalid", "Vendor and Device Type are required for devices.")
                return
        else:
            vendor = ""
            dev_type = ""

        motor = self.var_motor.get().strip()
        limits, ok = self._build_limits()
        if not ok:
            return

        self.result = {
            "category": category,
            "label": label,
            "can_id": can_id,
            "vendor": vendor,
            "device_type": dev_type,
            "motor": motor,
            "limits": limits,
            "terminator": self.var_terminator.get(),
        }
        self.destroy()

    def _build_limits(self) -> Tuple[Optional[Dict[str, int | bool]], bool]:
        """
        NAME
            _build_limits - Assemble optional limit switch data.

        RETURNS
            Tuple of (limits dict or None, ok flag).
        """
        raw_fwd = self.var_fwd.get().strip()
        raw_rev = self.var_rev.get().strip()
        invert = bool(self.var_invert.get())
        if not raw_fwd and not raw_rev and not invert:
            return None, True
        limits: Dict[str, int | bool] = {}
        if raw_fwd:
            try:
                limits["fwdDio"] = int(raw_fwd)
            except ValueError:
                messagebox.showerror("Invalid", "Limit Fwd DIO must be an integer.")
                return None, False
        if raw_rev:
            try:
                limits["revDio"] = int(raw_rev)
            except ValueError:
                messagebox.showerror("Invalid", "Limit Rev DIO must be an integer.")
                return None, False
        if invert:
            limits["invert"] = True
        return (limits if limits else None), True

    def _on_cancel(self) -> None:
        self.result = None
        self.destroy()


@dataclass
class Callout:
    """
    NAME
        Callout - Text label with a leader line to a bus or node.
    """

    key: int
    text: str
    target_type: str  # "bus" or "node"
    target_bus: int = 0
    target_node_key: Optional[int] = None
    x: float = 120.0
    y: float = 80.0


class CalloutDialog(tk.Toplevel):
    """
    NAME
        CalloutDialog - Modal dialog for adding or editing callouts.
    """

    def __init__(
        self,
        master: tk.Widget,
        title: str,
        nodes: List[Node],
        bus_count: int,
        initial: Optional[Callout] = None,
    ):
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.result: Optional[Dict[str, object]] = None
        self._nodes = nodes
        self._bus_count = bus_count
        self._build_ui(initial)
        self.transient(master)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _build_ui(self, initial: Optional[Callout]) -> None:
        frame = ttk.Frame(self, padding=12)
        frame.grid(row=0, column=0, sticky="nsew")

        self.var_text = tk.StringVar(value=initial.text if initial else "")
        target_type = initial.target_type if initial else "node"
        self.var_target_type = tk.StringVar(value=target_type)
        self.var_target_bus = tk.StringVar(value=str(initial.target_bus if initial else 0))
        self.var_target_node = tk.StringVar(value="")

        node_labels = [f"{n.key}: {n.label} (id {n.can_id})" for n in self._nodes]
        node_map = {f"{n.key}: {n.label} (id {n.can_id})": n.key for n in self._nodes}
        self._node_map = node_map
        if initial and initial.target_node_key is not None:
            for label, key in node_map.items():
                if key == initial.target_node_key:
                    self.var_target_node.set(label)
                    break

        ttk.Label(frame, text="Text").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.var_text, width=36).grid(row=0, column=1, sticky="w")

        ttk.Label(frame, text="Target").grid(row=1, column=0, sticky="w")
        self.combo_target = ttk.Combobox(
            frame, textvariable=self.var_target_type, values=["node", "bus"], state="readonly", width=10
        )
        self.combo_target.grid(row=1, column=1, sticky="w")
        self.combo_target.bind("<<ComboboxSelected>>", lambda _e: self._sync_fields())

        ttk.Label(frame, text="Node").grid(row=2, column=0, sticky="w")
        self.combo_node = ttk.Combobox(
            frame, textvariable=self.var_target_node, values=node_labels, width=34, state="readonly"
        )
        self.combo_node.grid(row=2, column=1, sticky="w")

        ttk.Label(frame, text="Bus Index").grid(row=3, column=0, sticky="w")
        bus_values = [str(i) for i in range(max(self._bus_count, 1))]
        self.combo_bus = ttk.Combobox(
            frame, textvariable=self.var_target_bus, values=bus_values, width=10, state="readonly"
        )
        self.combo_bus.grid(row=3, column=1, sticky="w")

        button_row = ttk.Frame(frame)
        button_row.grid(row=4, column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(button_row, text="Cancel", command=self._on_cancel).grid(row=0, column=0, padx=4)
        ttk.Button(button_row, text="OK", command=self._on_ok).grid(row=0, column=1, padx=4)

        self._sync_fields()

    def _sync_fields(self) -> None:
        is_node = self.var_target_type.get() == "node"
        self.combo_node.configure(state="readonly" if is_node else "disabled")
        self.combo_bus.configure(state="readonly" if not is_node else "disabled")

    def _on_ok(self) -> None:
        text = self.var_text.get().strip()
        if not text:
            messagebox.showerror("Invalid", "Text is required.")
            return
        target_type = self.var_target_type.get()
        target_bus = 0
        target_node = None
        if target_type == "node":
            label = self.var_target_node.get()
            if label not in self._node_map:
                messagebox.showerror("Invalid", "Select a target node.")
                return
            target_node = self._node_map[label]
        else:
            try:
                target_bus = int(self.var_target_bus.get())
            except ValueError:
                messagebox.showerror("Invalid", "Select a bus index.")
                return
        self.result = {
            "text": text,
            "target_type": target_type,
            "target_bus": target_bus,
            "target_node_key": target_node,
        }
        self.destroy()

    def _on_cancel(self) -> None:
        self.result = None
        self.destroy()

class TopologyEditor(tk.Tk):
    """
    NAME
        TopologyEditor - Main window for the CAN topology editor.

    DESCRIPTION
        Manages the node list, canvas rendering, and file export of a bringup
        profile JSON.
    """

    def __init__(self) -> None:
        super().__init__()
        self.title("CAN Topology Editor")
        self.geometry("980x600")
        self.minsize(760, 480)
        self._nodes: List[Node] = []
        self._next_key = 1
        self._selected_key: Optional[int] = None
        self._drag_state: Optional[Tuple[int, float]] = None
        self._profile_name = "drawn_profile"
        self._callouts: List[Callout] = []
        self._next_callout = 1
        self._selected_callout: Optional[int] = None
        self._callout_drag: Optional[Tuple[int, float, float]] = None
        self._layout_width = 0.0
        self._box_w = 140
        self._box_h = 60
        self._pan_y = 0.0
        self._pan_drag: Optional[Tuple[float, float]] = None
        self._bus_offsets: List[float] = [0.0]
        self._bus_spacing = 160.0
        self._zoom = 1.0
        self._draw_state = {"bus_ys": [], "y_shift": 0.0, "scale": 1.0}
        self._build_ui()
        self._load_default_profile_if_present()
        self._redraw_canvas()

    def _build_ui(self) -> None:
        """
        NAME
            _build_ui - Construct menus and main layout.
        """
        self._build_menu()
        container = ttk.Frame(self, padding=8)
        container.pack(fill="both", expand=True)

        left = ttk.Frame(container)
        left.pack(side="left", fill="y")
        right = ttk.Frame(container)
        right.pack(side="right", fill="both", expand=True)

        ttk.Label(left, text="Nodes").pack(anchor="w")
        self.listbox = tk.Listbox(left, width=36, height=18)
        self.listbox.pack(fill="both", expand=True, pady=(4, 6))
        self.listbox.bind("<<ListboxSelect>>", self._on_list_select)

        bottom = ttk.Frame(left)
        bottom.pack(fill="x", side="bottom", pady=(6, 0))

        ttk.Separator(bottom, orient="horizontal").pack(fill="x", pady=(0, 6))
        ttk.Label(bottom, text="Profile Name").pack(anchor="w")
        self.entry_profile = ttk.Entry(bottom)
        self.entry_profile.insert(0, self._profile_name)
        self.entry_profile.pack(fill="x", pady=(2, 0))
        self.var_set_default = tk.BooleanVar(value=False)
        ttk.Checkbutton(bottom, text="Set As Default", variable=self.var_set_default).pack(
            anchor="w", pady=(4, 8)
        )

        button_row = ttk.Frame(bottom)
        button_row.pack(fill="x")
        ttk.Button(button_row, text="Add", command=self._on_add).pack(fill="x", pady=2)
        ttk.Button(button_row, text="Edit", command=self._on_edit).pack(fill="x", pady=2)
        ttk.Button(button_row, text="Remove", command=self._on_remove).pack(fill="x", pady=2)
        ttk.Button(button_row, text="Layout", command=self._layout_even).pack(fill="x", pady=2)
        ttk.Button(button_row, text="Add Bus", command=self._on_add_bus).pack(fill="x", pady=2)
        ttk.Button(button_row, text="Add Callout", command=self._on_add_callout).pack(
            fill="x", pady=2
        )

        canvas_wrap = ttk.Frame(right)
        canvas_wrap.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(canvas_wrap, background="#ffffff")
        self.canvas.pack(fill="both", expand=True, side="top")
        self.h_scroll = ttk.Scrollbar(right, orient="horizontal", command=self.canvas.xview)
        self.h_scroll.pack(fill="x", side="bottom")
        self.v_scroll = ttk.Scrollbar(right, orient="vertical", command=self.canvas.yview)
        self.v_scroll.pack(fill="y", side="right")
        self.canvas.configure(xscrollcommand=self.h_scroll.set)
        self.canvas.configure(yscrollcommand=self.v_scroll.set)
        self.canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.canvas.bind("<Configure>", lambda _e: self._redraw_canvas())
        self.canvas.bind("<Control-MouseWheel>", self._on_zoom_wheel)

        self._build_details_panel(right)

    def _build_menu(self) -> None:
        """
        NAME
            _build_menu - Configure top-level menus.
        """
        menu = tk.Menu(self)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="New", command=self._new_diagram)
        file_menu.add_command(label="Open Profile...", command=self._open_profile)
        file_menu.add_command(label="Save Profile As...", command=self._save_profile_as)
        file_menu.add_command(label="Save to Deploy", command=self._on_save_to_deploy)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menu.add_cascade(label="File", menu=file_menu)
        view_menu = tk.Menu(menu, tearoff=False)
        view_menu.add_command(label="Zoom In", command=lambda: self._zoom_step(0.1))
        view_menu.add_command(label="Zoom Out", command=lambda: self._zoom_step(-0.1))
        view_menu.add_command(label="Zoom Reset", command=self._zoom_reset)
        menu.add_cascade(label="View", menu=view_menu)
        self.config(menu=menu)

    def _build_details_panel(self, parent: tk.Widget) -> None:
        """
        NAME
            _build_details_panel - Create the selected-node details area.
        """
        panel = ttk.LabelFrame(parent, text="Node Details", padding=8)
        panel.pack(fill="x", pady=(8, 0))

        self.detail_vars = {
            "category": tk.StringVar(value="—"),
            "label": tk.StringVar(value="—"),
            "can_id": tk.StringVar(value="—"),
            "vendor": tk.StringVar(value="—"),
            "type": tk.StringVar(value="—"),
            "motor": tk.StringVar(value="—"),
            "limits": tk.StringVar(value="—"),
            "terminator": tk.StringVar(value="—"),
        }

        rows = [
            ("Category", "category"),
            ("Label", "label"),
            ("CAN ID", "can_id"),
            ("Vendor", "vendor"),
            ("Device Type", "type"),
            ("Motor", "motor"),
            ("Limits", "limits"),
            ("Terminator", "terminator"),
        ]
        for idx, (title, key) in enumerate(rows):
            ttk.Label(panel, text=f"{title}:").grid(row=idx, column=0, sticky="w", padx=(0, 6))
            ttk.Label(panel, textvariable=self.detail_vars[key]).grid(
                row=idx, column=1, sticky="w"
            )

    def _update_details_panel(self, node: Optional[Node]) -> None:
        """
        NAME
            _update_details_panel - Refresh the details panel fields.
        """
        if node is None:
            for key in self.detail_vars:
                self.detail_vars[key].set("—")
            return

        limits_text = "—"
        if node.limits:
            fwd = node.limits.get("fwdDio", "—")
            rev = node.limits.get("revDio", "—")
            inv = node.limits.get("invert", False)
            limits_text = f"fwd={fwd}, rev={rev}, invert={inv}"

        term_text = "—" if node.terminator is None else ("on" if node.terminator else "off")

        self.detail_vars["category"].set(node.category)
        self.detail_vars["label"].set(node.label)
        self.detail_vars["can_id"].set(str(node.can_id))
        self.detail_vars["vendor"].set(node.vendor or "—")
        self.detail_vars["type"].set(node.device_type or "—")
        self.detail_vars["motor"].set(node.motor or "—")
        self.detail_vars["limits"].set(limits_text)
        self.detail_vars["terminator"].set(term_text)
    def _new_diagram(self) -> None:
        """
        NAME
            _new_diagram - Reset the editor to a blank diagram.
        """
        if not self._confirm_discard():
            return
        self._nodes.clear()
        self._next_key = 1
        self._selected_key = None
        self._callouts.clear()
        self._next_callout = 1
        self._selected_callout = None
        self._callout_drag = None
        self._layout_width = 0.0
        self._pan_y = 0.0
        self._zoom = 1.0
        self._bus_offsets = [0.0]
        self._refresh_list()
        self._update_details_panel(None)
        self._redraw_canvas()

    def _open_profile(self) -> None:
        """
        NAME
            _open_profile - Load nodes from an existing bringup profile file.
        """
        path = filedialog.askopenfilename(
            title="Open Bringup Profiles JSON",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        self._load_profile_from_path(path, ask_profile=True, confirm_discard=True)

    def _load_profile_from_path(
        self, path: str, ask_profile: bool, confirm_discard: bool
    ) -> None:
        """
        NAME
            _load_profile_from_path - Load a profile JSON and populate nodes.

        PARAMETERS
            path: Path to bringup_profiles.json.
            ask_profile: Whether to prompt for which profile to load.
            confirm_discard: Whether to prompt before discarding current nodes.
        """
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to open file: {exc}")
            return
        profiles = data.get("profiles")
        if not isinstance(profiles, dict) or not profiles:
            messagebox.showerror("Error", "No profiles found in JSON.")
            return
        names = sorted(profiles.keys())
        default_name = data.get("default_profile")
        if ask_profile:
            name = self._choose_profile_name(names, default_name)
            if not name:
                return
        else:
            name = default_name if default_name in profiles else names[0]
        profile = profiles.get(name)
        if not isinstance(profile, dict):
            messagebox.showerror("Error", "Profile data is not a JSON object.")
            return
        if confirm_discard and not self._confirm_discard():
            return
        self._nodes = self._nodes_from_profile(profile)
        self._callouts = []
        self._next_callout = 1
        self._selected_callout = None
        self._callout_drag = None
        self._layout_width = 0.0
        self._pan_y = 0.0
        self._zoom = 1.0
        self._bus_offsets = [0.0]
        diagram_applied = False
        diagram_profiles = {}
        diagram = data.get("diagram")
        if isinstance(diagram, dict):
            diagram_profiles = diagram.get("profiles") or {}
        if isinstance(diagram_profiles, dict):
            diag = diagram_profiles.get(name)
            if isinstance(diag, dict):
                self._apply_diagram_snapshot(diag)
                diagram_applied = True
        self._next_key = 1 + max([n.key for n in self._nodes], default=0)
        self._profile_name = name
        self.entry_profile.delete(0, tk.END)
        self.entry_profile.insert(0, name)
        self._refresh_list()
        self._update_details_panel(None)
        if not diagram_applied:
            self._layout_even()
        else:
            max_node_x = max((n.x for n in self._nodes), default=0.0)
            self._layout_width = max(self._layout_width, max_node_x + 200)
            self._redraw_canvas()
        self.update_idletasks()
        self.canvas.xview_moveto(0.0)
        self.canvas.yview_moveto(0.0)

    def _load_default_profile_if_present(self) -> None:
        """
        NAME
            _load_default_profile_if_present - Auto-load default profile on startup.

        DESCRIPTION
            Reads src/main/deploy/bringup_profiles.json and loads its
            default_profile into the diagram when available.
        """
        try:
            root = Path(__file__).resolve().parents[2]
            path = root / "src" / "main" / "deploy" / "bringup_profiles.json"
            if path.exists():
                self._load_profile_from_path(
                    str(path),
                    ask_profile=False,
                    confirm_discard=False,
                )
        except Exception:
            return

    def _choose_profile_name(self, names: List[str], default_name: Optional[str]) -> Optional[str]:
        """
        NAME
            _choose_profile_name - Ask the user which profile to load.
        """
        dialog = tk.Toplevel(self)
        dialog.title("Select Profile")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ttk.Label(dialog, text="Profile").pack(anchor="w", padx=10, pady=(10, 2))
        var = tk.StringVar(value=default_name or names[0])
        combo = ttk.Combobox(dialog, values=names, textvariable=var, state="readonly", width=30)
        combo.pack(padx=10, pady=4)

        result: List[Optional[str]] = [None]

        def _ok() -> None:
            result[0] = var.get()
            dialog.destroy()

        def _cancel() -> None:
            dialog.destroy()

        button_row = ttk.Frame(dialog)
        button_row.pack(padx=10, pady=(6, 10), anchor="e")
        ttk.Button(button_row, text="Cancel", command=_cancel).pack(side="left", padx=4)
        ttk.Button(button_row, text="OK", command=_ok).pack(side="left", padx=4)
        self.wait_window(dialog)
        return result[0]

    def _save_profile_as(self) -> None:
        """
        NAME
            _save_profile_as - Export the current diagram into a profile JSON.
        """
        profile_name = self.entry_profile.get().strip()
        if not profile_name:
            messagebox.showerror("Invalid", "Profile name is required.")
            return
        validation_error = self._validate_nodes()
        if validation_error:
            messagebox.showerror("Invalid", validation_error)
            return
        path = filedialog.asksaveasfilename(
            title="Save Bringup Profiles JSON",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        data = {
            "default_profile": profile_name,
            "profiles": {
                profile_name: self._profile_from_nodes(),
            },
            "diagram": {
                "profiles": {
                    profile_name: self._diagram_snapshot(),
                }
            },
        }
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)
                handle.write("\n")
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to write file: {exc}")
            return
        messagebox.showinfo("Saved", f"Wrote profile to {path}")

    def _on_save_to_deploy(self) -> None:
        """
        NAME
            _on_save_to_deploy - Append or replace a profile in bringup_profiles.json.
        """
        profile_name = self.entry_profile.get().strip()
        if not profile_name:
            messagebox.showerror("Invalid", "Profile name is required.")
            return
        validation_error = self._validate_nodes()
        if validation_error:
            messagebox.showerror("Invalid", validation_error)
            return
        root = Path(__file__).resolve().parents[2]
        path = root / "src" / "main" / "deploy" / "bringup_profiles.json"
        data = {}
        if path.exists():
            try:
                with path.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
            except Exception as exc:
                messagebox.showerror("Error", f"Failed to read {path}: {exc}")
                return
        if not isinstance(data, dict):
            data = {}
        profiles = data.get("profiles")
        if not isinstance(profiles, dict):
            profiles = {}
        diagram = data.get("diagram")
        if not isinstance(diagram, dict):
            diagram = {}
        diagram_profiles = diagram.get("profiles")
        if not isinstance(diagram_profiles, dict):
            diagram_profiles = {}

        if profile_name in profiles:
            replace = messagebox.askyesno(
                "Replace Profile",
                f"Profile '{profile_name}' exists. Replace it?",
            )
            if not replace:
                return

        profiles[profile_name] = self._profile_from_nodes()
        diagram_profiles[profile_name] = self._diagram_snapshot()
        data["profiles"] = profiles
        data["diagram"] = {"profiles": diagram_profiles}
        if self.var_set_default.get() or "default_profile" not in data:
            data["default_profile"] = profile_name

        try:
            with path.open("w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)
                handle.write("\n")
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to write {path}: {exc}")
            return
        messagebox.showinfo("Saved", f"Updated {path} with profile '{profile_name}'.")

    def _validate_nodes(self) -> Optional[str]:
        """
        NAME
            _validate_nodes - Enforce category constraints before save.

        RETURNS
            Error message or None when valid.
        """
        seen_singletons = {}
        for node in self._nodes:
            if node.category in SINGLETON_CATEGORIES:
                if node.category in seen_singletons:
                    return f"Only one {node.category} is allowed."
                seen_singletons[node.category] = node
            if node.category == GENERIC_CATEGORY:
                if not node.vendor or not node.device_type:
                    return "Generic devices require vendor and device type."
        return None

    def _profile_from_nodes(self) -> Dict[str, object]:
        """
        NAME
            _profile_from_nodes - Build a bringup profile object.

        RETURNS
            Dict compatible with bringup_profiles.json.
        """
        profile: Dict[str, object] = {}
        for category in BUCKET_CATEGORIES:
            entries = [self._node_to_entry(n) for n in self._nodes if n.category == category]
            if entries:
                profile[category] = entries
        for category in SINGLETON_CATEGORIES:
            entries = [self._node_to_entry(n) for n in self._nodes if n.category == category]
            if entries:
                profile[category] = entries[0]
        generic_entries = [self._node_to_entry(n) for n in self._nodes if n.category == GENERIC_CATEGORY]
        if generic_entries:
            profile[GENERIC_CATEGORY] = generic_entries
        return profile

    def _node_to_entry(self, node: Node) -> Dict[str, object]:
        """
        NAME
            _node_to_entry - Convert a Node into a profile entry dict.
        """
        entry: Dict[str, object] = {"label": node.label, "id": node.can_id}
        if node.category == GENERIC_CATEGORY:
            entry["vendor"] = node.vendor
            entry["type"] = node.device_type
        if node.motor:
            entry["motor"] = node.motor
        if node.limits:
            entry["limits"] = node.limits
        if node.terminator is not None:
            entry["terminator"] = node.terminator
        return entry

    def _nodes_from_profile(self, profile: Dict[str, object]) -> List[Node]:
        """
        NAME
            _nodes_from_profile - Convert a profile dict into Node objects.
        """
        nodes: List[Node] = []

        def _append(category: str, entry: Dict[str, object]) -> None:
            label = str(entry.get("label", "")).strip()
            can_id = int(entry.get("id", 0))
            vendor = str(entry.get("vendor", "")).strip()
            dev_type = str(entry.get("type", "")).strip()
            motor = str(entry.get("motor", "")).strip()
            limits = entry.get("limits")
            if isinstance(limits, dict):
                limits = dict(limits)
            terminator = entry.get("terminator")
            node = Node(
                key=self._next_key,
                category=category,
                label=label or f"{category.upper()} {can_id}",
                can_id=can_id,
                vendor=vendor,
                device_type=dev_type,
                motor=motor,
                limits=limits if isinstance(limits, dict) else None,
                terminator=bool(terminator) if isinstance(terminator, bool) else None,
                x=0.0,
                row=0,
            )
            self._next_key += 1
            nodes.append(node)

        for category in BUCKET_CATEGORIES:
            entries = profile.get(category, [])
            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, dict):
                        _append(category, entry)
        for category in SINGLETON_CATEGORIES:
            entry = profile.get(category)
            if isinstance(entry, dict):
                _append(category, entry)
        entries = profile.get(GENERIC_CATEGORY, [])
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict):
                    _append(GENERIC_CATEGORY, entry)
        return nodes

    def _diagram_snapshot(self) -> Dict[str, object]:
        """
        NAME
            _diagram_snapshot - Capture editor layout metadata for persistence.

        RETURNS
            Diagram metadata dict stored under the profile name.
        """
        nodes = []
        for node in self._nodes:
            nodes.append(
                {
                    "category": node.category,
                    "label": node.label,
                    "id": node.can_id,
                    "bus": node.bus_index,
                    "row": node.row,
                    "x": node.x,
                }
            )
        return {
            "busCount": len(self._bus_offsets),
            "busSpacing": self._bus_spacing,
            "panY": self._pan_y,
            "zoom": self._zoom,
            "nodes": nodes,
            "callouts": [
                {
                    "text": c.text,
                    "targetType": c.target_type,
                    "targetBus": c.target_bus,
                    "targetNodeKey": c.target_node_key,
                    "x": c.x,
                    "y": c.y,
                }
                for c in self._callouts
            ],
        }

    def _apply_diagram_snapshot(self, diagram: Dict[str, object]) -> None:
        """
        NAME
            _apply_diagram_snapshot - Restore editor layout metadata.
        """
        bus_count = diagram.get("busCount")
        if isinstance(bus_count, int) and bus_count > 0:
            self._bus_offsets = [i * self._bus_spacing for i in range(bus_count)]
        spacing = diagram.get("busSpacing")
        if isinstance(spacing, (int, float)) and spacing > 0:
            self._bus_spacing = float(spacing)
            self._bus_offsets = [i * self._bus_spacing for i in range(len(self._bus_offsets))]
        pan_y = diagram.get("panY")
        if isinstance(pan_y, (int, float)):
            self._pan_y = float(pan_y)
        zoom = diagram.get("zoom")
        if isinstance(zoom, (int, float)):
            self._zoom = max(0.6, min(2.0, float(zoom)))
        nodes = diagram.get("nodes")
        if isinstance(nodes, list):
            for entry in nodes:
                if not isinstance(entry, dict):
                    continue
                cat = entry.get("category")
                label = entry.get("label")
                node_id = entry.get("id")
                for node in self._nodes:
                    if node.category == cat and node.label == label and node.can_id == node_id:
                        bus = entry.get("bus")
                        row = entry.get("row")
                        x = entry.get("x")
                        if isinstance(bus, int):
                            node.bus_index = bus
                        if isinstance(row, int):
                            node.row = row
                        if isinstance(x, (int, float)):
                            node.x = float(x)
        callouts = diagram.get("callouts")
        if isinstance(callouts, list):
            for entry in callouts:
                if not isinstance(entry, dict):
                    continue
                text = str(entry.get("text", "")).strip()
                if not text:
                    continue
                target_type = str(entry.get("targetType", "bus"))
                target_bus = entry.get("targetBus", 0)
                target_node_key = entry.get("targetNodeKey")
                x = entry.get("x", 120.0)
                y = entry.get("y", 80.0)
                callout = Callout(
                    key=self._next_callout,
                    text=text,
                    target_type=target_type,
                    target_bus=int(target_bus) if isinstance(target_bus, int) else 0,
                    target_node_key=target_node_key if isinstance(target_node_key, int) else None,
                    x=float(x) if isinstance(x, (int, float)) else 120.0,
                    y=float(y) if isinstance(y, (int, float)) else 80.0,
                )
                self._next_callout += 1
                self._callouts.append(callout)

    def _confirm_discard(self) -> bool:
        """
        NAME
            _confirm_discard - Ask before discarding current diagram.
        """
        if not self._nodes:
            return True
        return messagebox.askyesno("Discard Changes", "Discard the current diagram?")

    def _on_add(self) -> None:
        """
        NAME
            _on_add - Add a new node to the diagram.
        """
        dialog = NodeDialog(self, "Add Node")
        self.wait_window(dialog)
        if not dialog.result:
            return
        data = dialog.result
        category = str(data["category"])
        if category in SINGLETON_CATEGORIES:
            if any(n.category == category for n in self._nodes):
                replace = messagebox.askyesno(
                    "Replace",
                    f"{category} already exists. Replace it?",
                )
                if not replace:
                    return
                self._nodes = [n for n in self._nodes if n.category != category]
        node = Node(
            key=self._next_key,
            category=category,
            label=str(data["label"]),
            can_id=int(data["can_id"]),
            vendor=str(data.get("vendor", "")),
            device_type=str(data.get("device_type", "")),
            motor=str(data.get("motor", "")),
            limits=data.get("limits") if isinstance(data.get("limits"), dict) else None,
            terminator=bool(data.get("terminator")) if data.get("terminator") is not None else None,
            x=self._next_x_position(),
            row=len(self._nodes) % 2,
            bus_index=len(self._nodes) % max(len(self._bus_offsets), 1),
        )
        self._next_key += 1
        self._nodes.append(node)
        self._layout_width = max(self._layout_width, node.x + 200)
        self._refresh_list()
        self._redraw_canvas()
        self._select_node(node.key)

    def _on_edit(self) -> None:
        """
        NAME
            _on_edit - Edit the currently selected node.
        """
        node = self._get_selected_node()
        if node is None:
            messagebox.showinfo("Edit", "Select a node to edit.")
            return
        dialog = NodeDialog(self, "Edit Node", initial=node)
        self.wait_window(dialog)
        if not dialog.result:
            return
        data = dialog.result
        category = str(data["category"])
        if category in SINGLETON_CATEGORIES:
            if any(n.category == category and n.key != node.key for n in self._nodes):
                messagebox.showerror("Invalid", f"Only one {category} is allowed.")
                return
        node.category = category
        node.label = str(data["label"])
        node.can_id = int(data["can_id"])
        node.vendor = str(data.get("vendor", ""))
        node.device_type = str(data.get("device_type", ""))
        node.motor = str(data.get("motor", ""))
        node.limits = data.get("limits") if isinstance(data.get("limits"), dict) else None
        node.terminator = (
            bool(data.get("terminator")) if data.get("terminator") is not None else None
        )
        self._refresh_list()
        self._redraw_canvas()
        self._select_node(node.key)

    def _on_remove(self) -> None:
        """
        NAME
            _on_remove - Remove the selected node.
        """
        node = self._get_selected_node()
        if node is None:
            messagebox.showinfo("Remove", "Select a node to remove.")
            return
        self._nodes = [n for n in self._nodes if n.key != node.key]
        self._selected_key = None
        self._refresh_list()
        self._update_details_panel(None)
        self._redraw_canvas()

    def _refresh_list(self) -> None:
        """
        NAME
            _refresh_list - Update the listbox contents.
        """
        self.listbox.delete(0, tk.END)
        for node in self._nodes:
            label = f"{node.category}: id {node.can_id} - {node.label}"
            self.listbox.insert(tk.END, label)

    def _layout_even(self) -> None:
        """
        NAME
            _layout_even - Spread nodes evenly across the canvas.
        """
        if not self._nodes:
            self._redraw_canvas()
            return
        width = max(self.canvas.winfo_width(), 1)
        if width < 200:
            self.after(80, self._layout_even)
            return
        left = 80
        desired_spacing = 180.0
        count = len(self._nodes)
        total_width = max(width, left * 2 + desired_spacing * max(count - 1, 1))
        spacing = (total_width - left * 2) / max(count - 1, 1)
        self._layout_width = total_width
        self._box_w = max(110, min(160, int(spacing - 30)))
        for idx, node in enumerate(self._nodes):
            node.x = left + spacing * idx
            node.row = idx % 2
            node.bus_index = idx % max(len(self._bus_offsets), 1)
        self._redraw_canvas()

    def _next_x_position(self) -> float:
        """
        NAME
            _next_x_position - Pick a reasonable x position for a new node.
        """
        width = max(self.canvas.winfo_width(), 1)
        if not self._nodes:
            return width * 0.2
        max_x = max(node.x for node in self._nodes)
        return max_x + 180

    def _on_list_select(self, _event: tk.Event) -> None:
        """
        NAME
            _on_list_select - Sync selection from the listbox.
        """
        index = self.listbox.curselection()
        if not index:
            return
        node = self._nodes[index[0]]
        self._select_node(node.key)

    def _select_node(self, key: int) -> None:
        """
        NAME
            _select_node - Mark a node as selected and update styles.
        """
        self._selected_key = key
        self._update_details_panel(self._get_selected_node())
        self._redraw_canvas()

    def _get_selected_node(self) -> Optional[Node]:
        """
        NAME
            _get_selected_node - Return the currently selected node.
        """
        if self._selected_key is None:
            return None
        for node in self._nodes:
            if node.key == self._selected_key:
                return node
        return None

    def _redraw_canvas(self) -> None:
        """
        NAME
            _redraw_canvas - Repaint the bus line and node boxes.
        """
        self.canvas.delete("all")
        width = max(self.canvas.winfo_width(), 1)
        height = max(self.canvas.winfo_height(), 1)
        scale = self._zoom
        max_node_x = max((n.x for n in self._nodes), default=0.0)
        total_width = max(
            width,
            int((self._layout_width or (max_node_x + 200)) * scale),
            int((max_node_x + 200) * scale),
        )
        base_y = height * 0.5 + self._pan_y
        bus_ys = [base_y + offset * scale for offset in self._bus_offsets]
        box_w = self._box_w * scale
        box_h = self._box_h * scale
        span = box_h + 60 * scale
        min_y = min((y - span for y in bus_ys), default=0.0)
        max_y = max((y + span for y in bus_ys), default=height)
        callout_ys = [c.y * scale for c in self._callouts]
        if callout_ys:
            min_y = min(min_y, min(callout_ys) - 40 * scale)
            max_y = max(max_y, max(callout_ys) + 40 * scale)
        margin = 20.0
        total_height = max(height, int(max_y - min_y + margin * 2))
        self.canvas.configure(scrollregion=(0, min_y - margin, total_width, max_y + margin))
        self._draw_state = {"bus_ys": bus_ys, "scale": scale}
        bridge_x = 50
        for idx, bus_y in enumerate(bus_ys):
            self.canvas.create_line(40, bus_y, total_width - 40, bus_y, width=4, fill="#444444")
            if idx + 1 < len(bus_ys):
                next_y = bus_ys[idx + 1]
                self.canvas.create_line(
                    bridge_x,
                    bus_y,
                    bridge_x,
                    next_y,
                    width=5,
                    fill="#444444",
                )
                for y in (bus_y, next_y):
                    r = 5 * scale
                    self.canvas.create_oval(
                        bridge_x - r,
                        y - r,
                        bridge_x + r,
                        y + r,
                        fill="#444444",
                        outline="#444444",
                    )

        for node in self._nodes:
            node_x = min(max(node.x * scale, 60), total_width - 60)
            bus_index = min(max(node.bus_index, 0), max(len(bus_ys) - 1, 0))
            node.bus_index = bus_index
            bus_y = bus_ys[bus_index] if bus_ys else base_y
            x0 = node_x - box_w / 2
            x1 = node_x + box_w / 2
            if node.row == 1:
                y0 = bus_y + 30 * scale
                y1 = y0 + box_h
                self.canvas.create_line(node_x, bus_y, node_x, y0, width=2, fill="#444444")
            else:
                y1 = bus_y - 30 * scale
                y0 = y1 - box_h
                self.canvas.create_line(node_x, y1, node_x, bus_y, width=2, fill="#444444")
            outline = "#1f6feb" if node.key == self._selected_key else "#222222"
            rect = self.canvas.create_rectangle(x0, y0, x1, y1, fill="#f7f7f7", outline=outline, width=2)
            text = self.canvas.create_text(
                node_x,
                (y0 + y1) / 2,
                text=node.display_text(),
                font=("Segoe UI", max(8, int(9 * scale))),
                justify="center",
                width=max(40, int(box_w - 10)),
            )
            self.canvas.addtag_withtag(f"node_{node.key}", rect)
            self.canvas.addtag_withtag(f"node_{node.key}", text)

        node_centers = {
            n.key: (min(max(n.x * scale, 60), total_width - 60), bus_ys[n.bus_index] if bus_ys else base_y)
            for n in self._nodes
        }
        for callout in self._callouts:
            cx = callout.x * scale
            cy = callout.y * scale
            box_w = 180 * scale
            box_h = 50 * scale
            x0 = cx - box_w / 2
            y0 = cy - box_h / 2
            x1 = cx + box_w / 2
            y1 = cy + box_h / 2
            if callout.target_type == "node" and callout.target_node_key in node_centers:
                tx, ty = node_centers[callout.target_node_key]
            else:
                bus_index = min(max(callout.target_bus, 0), max(len(bus_ys) - 1, 0))
                ty = bus_ys[bus_index] if bus_ys else base_y
                tx = cx
            self.canvas.create_line(cx, cy, tx, ty, width=2, fill="#666666")
            rect = self.canvas.create_rectangle(
                x0, y0, x1, y1, fill="#fffbe6", outline="#666666", width=2
            )
            text = self.canvas.create_text(
                cx,
                cy,
                text=callout.text,
                font=("Segoe UI", max(8, int(9 * scale))),
                justify="center",
                width=max(60, int(box_w - 10)),
            )
            self.canvas.addtag_withtag(f"callout_{callout.key}", rect)
            self.canvas.addtag_withtag(f"callout_{callout.key}", text)

    def _on_canvas_press(self, event: tk.Event) -> None:
        """
        NAME
            _on_canvas_press - Begin dragging a node if clicked.
        """
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        item = self.canvas.find_closest(cx, cy)
        if not item:
            return
        tags = self.canvas.gettags(item[0])
        key = self._tag_to_key(tags)
        callout_key = self._tag_to_callout(tags)
        if callout_key is not None:
            self._selected_callout = callout_key
            self._selected_key = None
            offset_x, offset_y = self._callout_drag_offset(callout_key, cx, cy)
            self._callout_drag = (callout_key, offset_x, offset_y)
            self._redraw_canvas()
            return
        if key is None:
            self._pan_drag = (cy, self._pan_y)
            return
        self._select_node(key)
        self._drag_state = (key, cx, cy)

    def _on_canvas_drag(self, event: tk.Event) -> None:
        """
        NAME
            _on_canvas_drag - Drag the selected node horizontally.
        """
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        if self._pan_drag is not None:
            start_y, start_pan = self._pan_drag
            dy = cy - start_y
            height = max(self.canvas.winfo_height(), 1)
            max_shift = height * 0.25
            self._pan_y = max(-max_shift, min(max_shift, start_pan + dy))
            self._redraw_canvas()
            return
        if self._callout_drag is not None:
            key, offset_x, offset_y = self._callout_drag
            callout = next((c for c in self._callouts if c.key == key), None)
            if callout is None:
                return
        scale = max(self._zoom, 0.01)
        callout.x = (cx - offset_x) / scale
        callout.y = (cy - offset_y) / scale
        self._callout_drag = (key, offset_x, offset_y)
        self._redraw_canvas()
        return
        if not self._drag_state:
            return
        key, last_x, _last_y = self._drag_state
        node = next((n for n in self._nodes if n.key == key), None)
        if node is None:
            return
        dx = cx - last_x
        node.x += dx / max(self._zoom, 0.01)
        self._layout_width = max(self._layout_width, node.x + 200)
        node.bus_index, node.row = self._nearest_bus_and_row(cy)
        self._drag_state = (key, cx, cy)
        self._redraw_canvas()

    def _on_canvas_release(self, _event: tk.Event) -> None:
        """
        NAME
            _on_canvas_release - End drag operation.
        """
        self._drag_state = None
        self._pan_drag = None
        self._callout_drag = None

    def _on_add_bus(self) -> None:
        """
        NAME
            _on_add_bus - Add a parallel bus segment connected to the first.
        """
        if not self._bus_offsets:
            self._bus_offsets = [0.0]
        next_offset = self._bus_offsets[-1] + self._bus_spacing
        self._bus_offsets.append(next_offset)
        self._redraw_canvas()

    def _on_add_callout(self) -> None:
        """
        NAME
            _on_add_callout - Add a callout label attached to a bus or node.
        """
        dialog = CalloutDialog(
            self,
            "Add Callout",
            nodes=self._nodes,
            bus_count=len(self._bus_offsets),
        )
        self.wait_window(dialog)
        if not dialog.result:
            return
        data = dialog.result
        callout = Callout(
            key=self._next_callout,
            text=str(data["text"]),
            target_type=str(data["target_type"]),
            target_bus=int(data.get("target_bus", 0)),
            target_node_key=data.get("target_node_key"),
            x=140.0,
            y=80.0,
        )
        self._next_callout += 1
        self._callouts.append(callout)
        self._selected_callout = callout.key
        self._redraw_canvas()

    def _nearest_bus_and_row(self, y: float) -> Tuple[int, int]:
        """
        NAME
            _nearest_bus_and_row - Pick the nearest bus and top/bottom row.

        RETURNS
            Tuple of (bus_index, row) where row 0 is above, 1 is below.
        """
        bus_ys = list(self._draw_state.get("bus_ys", []))
        if not bus_ys:
            height = max(self.canvas.winfo_height(), 1)
            base_y = height * 0.5 + self._pan_y
            bus_ys = [base_y]
        nearest = 0
        best = float("inf")
        for idx, bus_y in enumerate(bus_ys):
            dist = abs(y - bus_y)
            if dist < best:
                best = dist
                nearest = idx
        row = 0 if y < bus_ys[nearest] else 1
        return nearest, row

    def _on_zoom_wheel(self, event: tk.Event) -> None:
        """
        NAME
            _on_zoom_wheel - Handle Ctrl+MouseWheel zoom.
        """
        delta = 0.1 if event.delta > 0 else -0.1
        self._zoom_step(delta)

    def _zoom_step(self, delta: float) -> None:
        """
        NAME
            _zoom_step - Apply a zoom increment within bounds.
        """
        self._zoom = max(0.6, min(2.0, self._zoom + delta))
        self._redraw_canvas()

    def _zoom_reset(self) -> None:
        """
        NAME
            _zoom_reset - Reset zoom to 100%.
        """
        self._zoom = 1.0
        self._redraw_canvas()

    @staticmethod
    def _tag_to_key(tags: Tuple[str, ...]) -> Optional[int]:
        """
        NAME
            _tag_to_key - Extract node key from canvas tag list.
        """
        for tag in tags:
            if tag.startswith("node_"):
                try:
                    return int(tag.split("_", 1)[1])
                except ValueError:
                    return None
        return None

    @staticmethod
    def _tag_to_callout(tags: Tuple[str, ...]) -> Optional[int]:
        """
        NAME
            _tag_to_callout - Extract callout key from canvas tag list.
        """
        for tag in tags:
            if tag.startswith("callout_"):
                try:
                    return int(tag.split("_", 1)[1])
                except ValueError:
                    return None
        return None

    def _callout_drag_offset(self, key: int, cx: float, cy: float) -> Tuple[float, float]:
        """
        NAME
            _callout_drag_offset - Compute cursor offset from callout center.
        """
        callout = next((c for c in self._callouts if c.key == key), None)
        if callout is None:
            return 0.0, 0.0
        scale = max(self._zoom, 0.01)
        center_x = callout.x * scale
        center_y = callout.y * scale
        return cx - center_x, cy - center_y


def main() -> int:
    """
    NAME
        main - Launch the CAN topology editor GUI.

    RETURNS
        Process exit code (0).
    """
    app = TopologyEditor()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
