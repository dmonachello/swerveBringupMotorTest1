#!/usr/bin/env python3
"""
NAME
    can_top_editor.py - Simple CAN bus topology editor (diagram -> profile).

SYNOPSIS
    python -m tools.can_topology.can_top_editor

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
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, filedialog, messagebox

try:
    from .can_top_models import (
        BUCKET_CATEGORIES,
        GENERIC_CATEGORY,
        SINGLETON_CATEGORIES,
        Node,
    )
    from .can_top_dialogs import CalloutDialog, NodeDialog
except ImportError:  # Allow running as a script from this folder.
    import sys
    from pathlib import Path as _Path

    sys.path.append(str(_Path(__file__).resolve().parents[1]))
    from can_topology.can_top_models import (  # type: ignore
        BUCKET_CATEGORIES,
        GENERIC_CATEGORY,
        SINGLETON_CATEGORIES,
        Node,
    )
    from can_topology.can_top_dialogs import CalloutDialog, NodeDialog  # type: ignore


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
        self._drag_state: Optional[Tuple[int, float, float]] = None
        self._drag_free_y: Dict[int, float] = {}
        self._profile_name = "drawn_profile"
        self._profile_source_path: Optional[str] = None
        self._suppress_profile_select = False
        self._profile_names: List[str] = []
        self._callout_scale_var = tk.StringVar(value="1.00")
        self._layout_width = 0.0
        self._box_w = 140
        self._box_h = 60
        self._pan_y = 0.0
        self._pan_drag: Optional[Tuple[float, float]] = None
        self._bus_offsets: List[float] = [0.0]
        self._bus_lefts: List[float] = []
        self._bus_rights: List[float] = []
        self._bus_spacing = 160.0
        self._add_bus_mode = False
        self._bus_drag: Optional[Tuple[int, float, float]] = None
        self._bus_resize: Optional[Tuple[int, str, float, float, float]] = None
        self._undo_stack: List[Dict[str, object]] = []
        self._undo_limit = 20
        self._drag_undo_pending = False
        self._dirty = False
        self._zoom_label_var = tk.StringVar(value="Zoom: 100%")
        self._selected_nodes: set[int] = set()
        self._selected_buses: set[int] = set()
        self._selection_rect: Optional[int] = None
        self._selection_start: Optional[Tuple[float, float]] = None
        self._node_bounds: Dict[int, Tuple[float, float, float, float]] = {}
        self._bus_ys: List[float] = []
        self._dragging_active = False
        self._redraw_pending = False
        self._clipboard: Optional[Dict[str, object]] = None
        self._multi_drag: Optional[Dict[str, object]] = None
        self._last_base_y: Optional[float] = None
        self._details_layout_shift = False
        self._last_canvas_height: Optional[int] = None
        self._suppress_list_select = False
        self._syncing_selection = False
        self._zoom = 1.0
        self._draw_state = {"bus_ys": [], "y_shift": 0.0, "scale": 1.0}
        self._snap_to_grid_var = tk.BooleanVar(value=True)
        self._smart_guides_var = tk.BooleanVar(value=False)
        self._grid_size_var = tk.IntVar(value=20)
        self._guide_x: Optional[float] = None
        self._guide_bus: Optional[int] = None
        self._guide_snap_px = 6.0
        self.protocol("WM_DELETE_WINDOW", self._on_close)
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
        list_frame = ttk.Frame(left)
        list_frame.pack(fill="both", expand=True, pady=(4, 6))
        self.node_list = ttk.Treeview(
            list_frame,
            columns=("can_id", "type", "label"),
            show="headings",
            height=12,
            selectmode="browse",
        )
        self.node_list.heading("can_id", text="CAN ID")
        self.node_list.heading("type", text="Type")
        self.node_list.heading("label", text="Label")
        self.node_list.column("can_id", width=60, anchor="center")
        self.node_list.column("type", width=80, anchor="w")
        self.node_list.column("label", width=160, anchor="w")
        self.node_list.pack(side="left", fill="both", expand=True)
        node_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.node_list.yview)
        node_scroll.pack(side="right", fill="y")
        self.node_list.configure(yscrollcommand=node_scroll.set)
        self.node_list.bind("<<TreeviewSelect>>", self._on_list_select)

        bottom = ttk.Frame(left)
        bottom.pack(fill="x", side="bottom", pady=(6, 0))

        ttk.Separator(bottom, orient="horizontal").pack(fill="x", pady=(0, 6))
        ttk.Label(bottom, text="Profile Name").pack(anchor="w")
        self.entry_profile = ttk.Combobox(bottom, values=self._profile_names, state="normal")
        self.entry_profile.set(self._profile_name)
        self.entry_profile.pack(fill="x", pady=(2, 0))
        self.entry_profile.bind("<<ComboboxSelected>>", self._on_profile_select)
        self.var_set_default = tk.BooleanVar(value=False)
        ttk.Checkbutton(bottom, text="Set As Default", variable=self.var_set_default).pack(
            anchor="w", pady=(4, 8)
        )
        ttk.Label(bottom, textvariable=self._zoom_label_var).pack(anchor="w", pady=(2, 6))

        button_row = ttk.Frame(bottom)
        button_row.pack(fill="x")
        ttk.Button(button_row, text="Add", command=self._on_add).pack(fill="x", pady=2)
        ttk.Button(button_row, text="Edit Selected", command=self._on_edit_selected).pack(
            fill="x", pady=2
        )
        ttk.Button(button_row, text="Remove Selected", command=self._on_remove_selected).pack(
            fill="x", pady=2
        )
        ttk.Button(button_row, text="Tidy All", command=self._tidy_all).pack(fill="x", pady=2)
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
        self.canvas.bind("<Control-c>", lambda _e: self._on_copy())
        self.canvas.bind("<Control-v>", lambda _e: self._on_paste())
        self.bind_all("<Control-z>", lambda _e: self._undo_last())
        self.bind_all("<Control-Z>", lambda _e: self._undo_last())
        self.bind_all("<Control-a>", lambda _e: self._select_all_nodes())
        self.bind_all("<Control-A>", lambda _e: self._select_all_nodes())
        self.bind_all("<Control-plus>", lambda _e: self._zoom_step(0.1))
        self.bind_all("<Control-minus>", lambda _e: self._zoom_step(-0.1))
        self.bind_all("<Control-underscore>", lambda _e: self._zoom_step(-0.1))
        self.bind_all("<Control-equal>", lambda _e: self._zoom_step(0.1))
        self.bind_all("<Control-0>", lambda _e: self._zoom_reset())
        self.bind_all("<Control-Shift-L>", lambda _e: self._layout_even())
        self.bind_all("<Control-Shift-l>", lambda _e: self._layout_even())
        self.bind_all("<Control-l>", lambda _e: self._tidy_selection())
        self.bind_all("<Control-L>", lambda _e: self._tidy_selection())
        self.bind_all("<Control-d>", lambda _e: self._duplicate_selection())
        self.bind_all("<Control-D>", lambda _e: self._duplicate_selection())
        self.bind_all("<Control-g>", lambda _e: self._toggle_snap_to_grid())
        self.bind_all("<Control-G>", lambda _e: self._toggle_snap_to_grid())
        self.bind_all("<Control-Shift-G>", lambda _e: self._toggle_smart_guides())
        self.bind_all("<Control-Shift-g>", lambda _e: self._toggle_smart_guides())
        self.bind_all("<Control-s>", lambda _e: self._save_shortcut())
        self.bind_all("<Control-S>", lambda _e: self._save_shortcut())
        self.bind_all("<Delete>", lambda _e: self._on_remove_selected())
        self.bind_all("<BackSpace>", lambda _e: self._on_remove_selected())
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
        file_menu.add_command(label="Export PDF...", command=self._on_export_pdf)
        file_menu.add_command(label="Export Java Constants...", command=self._on_export_java_constants)
        file_menu.add_command(label="Undo", command=self._undo_last)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close)
        menu.add_cascade(label="File", menu=file_menu)
        edit_menu = tk.Menu(menu, tearoff=False)
        edit_menu.add_command(label="Copy", command=self._on_copy)
        edit_menu.add_command(label="Paste", command=self._on_paste)
        menu.add_cascade(label="Edit", menu=edit_menu)
        layout_menu = tk.Menu(menu, tearoff=False)
        layout_menu.add_command(label="Align Left", command=lambda: self._align_selected("left"))
        layout_menu.add_command(label="Align Center", command=lambda: self._align_selected("center"))
        layout_menu.add_command(label="Align Right", command=lambda: self._align_selected("right"))
        layout_menu.add_separator()
        layout_menu.add_command(
            label="Distribute Horizontally", command=self._distribute_selected_horizontally
        )
        layout_menu.add_separator()
        layout_menu.add_command(label="Tidy All", command=self._tidy_all)
        layout_menu.add_command(label="Tidy Selection", command=self._tidy_selection)
        layout_menu.add_separator()
        layout_menu.add_command(label="Reset Layout", command=self._layout_even)
        menu.add_cascade(label="Layout", menu=layout_menu)
        view_menu = tk.Menu(menu, tearoff=False)
        view_menu.add_command(label="Zoom In", command=lambda: self._zoom_step(0.1))
        view_menu.add_command(label="Zoom Out", command=lambda: self._zoom_step(-0.1))
        view_menu.add_command(label="Zoom Reset", command=self._zoom_reset)
        view_menu.add_command(label="Fit to Window", command=self._fit_to_window)
        view_menu.add_separator()
        view_menu.add_checkbutton(label="Snap to Grid", variable=self._snap_to_grid_var)
        view_menu.add_checkbutton(label="Smart Guides", variable=self._smart_guides_var)
        grid_menu = tk.Menu(view_menu, tearoff=False)
        for size in (10, 20, 40):
            grid_menu.add_radiobutton(
                label=f"{size}px", value=size, variable=self._grid_size_var
            )
        view_menu.add_cascade(label="Grid Size", menu=grid_menu)
        view_menu.add_command(label="Legend...", command=self._show_legend_dialog)
        menu.add_cascade(label="View", menu=view_menu)
        help_menu = tk.Menu(menu, tearoff=False)
        help_menu.add_command(label="Help...", command=self._show_help_dialog)
        help_menu.add_command(label="Keyboard Shortcuts...", command=self._show_shortcuts_dialog)
        menu.add_cascade(label="Help", menu=help_menu)
        self.config(menu=menu)

    def _build_details_panel(self, parent: tk.Widget) -> None:
        """
        NAME
            _build_details_panel - Create the selected-node details area.
        """
        panel = ttk.LabelFrame(parent, text="Node Details", padding=8)
        self._node_details_panel = panel

        self.detail_vars = {
            "category": tk.StringVar(value="—"),
            "label": tk.StringVar(value="—"),
            "can_id": tk.StringVar(value="—"),
            "vendor": tk.StringVar(value="—"),
            "type": tk.StringVar(value="—"),
            "motor": tk.StringVar(value="—"),
            "limits": tk.StringVar(value="—"),
            "terminator": tk.StringVar(value="—"),
            "scale": tk.StringVar(value="1.00"),
        }
        self._terminator_status_var = tk.StringVar(value="???")


        rows = [
            ("Category", "category"),
            ("Label", "label"),
            ("CAN ID", "can_id"),
            ("Vendor", "vendor"),
            ("Device Type", "type"),
            ("Motor", "motor"),
            ("Limits", "limits"),
            ("Terminator", "terminator"),
            ("Scale", "scale"),
        ]
        for idx, (title, key) in enumerate(rows):
            ttk.Label(panel, text=f"{title}:").grid(row=idx, column=0, sticky="w", padx=(0, 6))
            ttk.Label(panel, textvariable=self.detail_vars[key]).grid(
                row=idx, column=1, sticky="w"
            )
        scale_row = len(rows)
        scale_controls = ttk.Frame(panel)
        scale_controls.grid(row=scale_row, column=1, sticky="w", pady=(4, 0))
        ttk.Button(scale_controls, text="-", width=3, command=lambda: self._nudge_scale(-0.1)).pack(
            side="left"
        )
        ttk.Button(scale_controls, text="+", width=3, command=lambda: self._nudge_scale(0.1)).pack(
            side="left", padx=(4, 0)
        )
        status_row = scale_row + 1
        self._terminator_status_label = ttk.Label(
            panel, textvariable=self._terminator_status_var
        )
        self._terminator_status_label.grid(
            row=status_row, column=0, columnspan=2, sticky="w", pady=(6, 0)
        )

        callout_panel = ttk.LabelFrame(parent, text="Callout Details", padding=8)
        self._callout_details_panel = callout_panel
        ttk.Label(callout_panel, text="Scale:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        ttk.Label(callout_panel, textvariable=self._callout_scale_var).grid(
            row=0, column=1, sticky="w"
        )
        callout_controls = ttk.Frame(callout_panel)
        callout_controls.grid(row=1, column=1, sticky="w", pady=(4, 0))
        ttk.Button(
            callout_controls, text="-", width=3, command=lambda: self._nudge_callout_scale(-0.1)
        ).pack(side="left")
        ttk.Button(
            callout_controls, text="+", width=3, command=lambda: self._nudge_callout_scale(0.1)
        ).pack(side="left", padx=(4, 0))
        self._node_details_panel.pack_forget()
        self._callout_details_panel.pack_forget()

    def _update_details_panel(self, node: Optional[Node]) -> None:
        """
        NAME
            _update_details_panel - Refresh the details panel fields.
        """
        self._refresh_terminator_status()
        if node is None:
            for key in self.detail_vars:
                self.detail_vars[key].set("—")
            self._callout_scale_var.set("—")
            if hasattr(self, "_node_details_panel"):
                self._preserve_canvas_view(self._node_details_panel.pack_forget)
            return
        if node.node_type == "callout":
            return
        if node.node_type == "callout":
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
        self.detail_vars["scale"].set(f"{node.scale:.2f}")
        if hasattr(self, "_node_details_panel"):
            self._preserve_canvas_view(lambda: self._node_details_panel.pack(fill="x", pady=(8, 0)))

    def _terminator_count(self) -> int:
        """
        NAME
            _terminator_count - Count nodes marked as CAN bus terminators.
        """
        return sum(1 for n in self._nodes if n.terminator is True)

    def _refresh_terminator_status(self) -> None:
        """
        NAME
            _refresh_terminator_status - Update the terminator count warning text.
        """
        count = self._terminator_count()
        if count == 2:
            text = "Terminator nodes: 2 (ok)"
            color = "#1a7f37"
        else:
            text = f"Terminator nodes: {count} (expected 2)"
            color = "#b42318"
        self._terminator_status_var.set(text)
        if hasattr(self, "_terminator_status_label"):
            try:
                self._terminator_status_label.configure(foreground=color)
            except tk.TclError:
                pass

    def _confirm_terminators(self) -> bool:
        """
        NAME
            _confirm_terminators - Warn when terminator count is not two.
        """
        count = self._terminator_count()
        if count == 2:
            return True
        return messagebox.askyesno(
            "Terminator Warning",
            f"Terminator nodes: {count} (expected 2).\n\nSave anyway?",
        )

    def _nudge_scale(self, delta: float) -> None:
        """
        NAME
            _nudge_scale - Adjust the selected node scale.
        """
        node = self._get_selected_node()
        if node is None:
            return
        node.scale = max(0.6, min(2.0, node.scale + delta))
        self._update_details_panel(node)
        self._redraw_canvas()

    def _preserve_canvas_view(self, action) -> None:
        """
        NAME
            _preserve_canvas_view - Run an action without shifting canvas view.
        """
        action()

    def _nudge_callout_scale(self, delta: float) -> None:
        """
        NAME
            _nudge_callout_scale - Adjust the selected callout scale.
        """
        node = self._get_selected_node()
        if node is None or node.node_type != "callout":
            return
        node.scale = max(0.6, min(2.0, node.scale + delta))
        self._dirty = True
        self._callout_scale_var.set(f"{node.scale:.2f}")
        self._redraw_canvas()

    def _push_undo(self) -> None:
        """
        NAME
            _push_undo - Save a snapshot for undo.
        """
        self._dirty = True
        snapshot = {
            "nodes": [
                {
                    "key": n.key,
                    "node_type": n.node_type,
                    "category": n.category,
                    "label": n.label,
                    "can_id": n.can_id,
                    "vendor": n.vendor,
                    "device_type": n.device_type,
                    "motor": n.motor,
                    "limits": n.limits,
                    "terminator": n.terminator,
                    "x": n.x,
                    "row": n.row,
                    "bus_index": n.bus_index,
                    "scale": n.scale,
                    "callout_text": n.callout_text,
                    "callout_target_type": n.callout_target_type,
                    "callout_target_bus": n.callout_target_bus,
                    "callout_target_node_key": n.callout_target_node_key,
                    "callout_y": self._node_center_y_unscaled(n)
                    if n.node_type == "callout"
                    else n.callout_y,
                    "free_y": n.free_y,
                }
                for n in self._nodes
            ],
            "bus_offsets": list(self._bus_offsets),
            "bus_lefts": list(self._bus_lefts),
            "bus_rights": list(self._bus_rights),
            "layout_width": self._layout_width,
            "pan_y": self._pan_y,
            "zoom": self._zoom,
            "next_key": self._next_key,
        }
        self._undo_stack.append(snapshot)
        if len(self._undo_stack) > self._undo_limit:
            self._undo_stack.pop(0)

    def _undo_last(self) -> None:
        """
        NAME
            _undo_last - Restore the last snapshot.
        """
        if not self._undo_stack:
            messagebox.showinfo("Undo", "Nothing to undo.")
            return
        snap = self._undo_stack.pop()
        self._nodes = [
            Node(
                key=n["key"],
                category=n["category"],
                label=n["label"],
                can_id=n["can_id"],
                node_type=n.get("node_type", "device"),
                vendor=n.get("vendor", ""),
                device_type=n.get("device_type", ""),
                motor=n.get("motor", ""),
                limits=n.get("limits"),
                terminator=n.get("terminator"),
                x=n.get("x", 0.0),
                row=n.get("row", 0),
                bus_index=n.get("bus_index", 0),
                scale=n.get("scale", 1.0),
                callout_text=n.get("callout_text", ""),
                callout_target_type=n.get("callout_target_type", "node"),
                callout_target_bus=n.get("callout_target_bus", 0),
                callout_target_node_key=n.get("callout_target_node_key"),
                callout_y=n.get("callout_y", 0.0),
                free_y=n.get("free_y"),
            )
            for n in snap["nodes"]
        ]
        self._bus_offsets = snap["bus_offsets"]
        self._bus_lefts = snap.get("bus_lefts", [])
        self._bus_rights = snap.get("bus_rights", [])
        self._layout_width = snap["layout_width"]
        self._pan_y = snap["pan_y"]
        self._zoom = snap["zoom"]
        self._next_key = snap["next_key"]
        
        self._refresh_list()
        self._update_details_panel(None)
        if hasattr(self, "_node_details_panel"):
            self._node_details_panel.pack_forget()
        if hasattr(self, "_callout_details_panel"):
            self._callout_details_panel.pack_forget()
        self._redraw_canvas()
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
        self._callout_scale_var.set("—")
        if hasattr(self, "_node_details_panel"):
            self._preserve_canvas_view(self._node_details_panel.pack_forget)
        if hasattr(self, "_callout_details_panel"):
            self._preserve_canvas_view(self._callout_details_panel.pack_forget)
        self._layout_width = 0.0
        self._pan_y = 0.0
        self._zoom = 1.0
        self._zoom_label_var.set("Zoom: 100%")
        self._bus_offsets = [0.0]
        self._bus_lefts = []
        self._bus_rights = []
        self._last_base_y = None
        self._details_layout_shift = False
        self._dirty = False
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
        self,
        path: str,
        ask_profile: bool,
        confirm_discard: bool,
        selected_name: Optional[str] = None,
    ) -> None:
        """
        NAME
            _load_profile_from_path - Load a profile JSON and populate nodes.

        PARAMETERS
            path: Path to bringup_profiles.json.
            ask_profile: Whether to prompt for which profile to load.
            confirm_discard: Whether to prompt before discarding current nodes.
            selected_name: Optional profile name to load.
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
        if selected_name:
            if selected_name not in profiles:
                messagebox.showerror("Error", f"Profile '{selected_name}' not found in JSON.")
                return
            name = selected_name
        elif ask_profile:
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
        self._next_callout = 1
        self._callout_scale_var.set("—")
        if hasattr(self, "_node_details_panel"):
            self._preserve_canvas_view(self._node_details_panel.pack_forget)
        if hasattr(self, "_callout_details_panel"):
            self._preserve_canvas_view(self._callout_details_panel.pack_forget)
        self._layout_width = 0.0
        self._pan_y = 0.0
        self._zoom = 1.0
        self._zoom_label_var.set("Zoom: 100%")
        self._bus_offsets = [0.0]
        self._bus_lefts = []
        self._bus_rights = []
        self._last_base_y = None
        self._details_layout_shift = False
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
                self._zoom_label_var.set(f"Zoom: {int(self._zoom * 100)}%")
        self._next_key = 1 + max([n.key for n in self._nodes], default=0)
        self._profile_name = name
        self._profile_source_path = path
        self._set_profile_names(names)
        self._suppress_profile_select = True
        self.entry_profile.set(name)
        self._suppress_profile_select = False
        self._refresh_list()
        self._update_details_panel(None)
        if not diagram_applied:
            self._layout_even()
        else:
            max_node_x = max((n.x for n in self._nodes), default=0.0)
            self._layout_width = max(self._layout_width, max_node_x + 200)
            self._redraw_canvas()
        self._dirty = False
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

    def _on_profile_select(self, _event: tk.Event) -> None:
        """
        NAME
            _on_profile_select - Load the selected profile from the dropdown.
        """
        if self._suppress_profile_select:
            return
        selected = self.entry_profile.get().strip()
        if not selected or selected == self._profile_name:
            return
        path = self._profile_source_path
        if not path:
            root = Path(__file__).resolve().parents[2]
            path = str(root / "src" / "main" / "deploy" / "bringup_profiles.json")
        self._load_profile_from_path(path, ask_profile=False, confirm_discard=True, selected_name=selected)

    def _set_profile_names(self, names: List[str]) -> None:
        """
        NAME
            _set_profile_names - Update the profile dropdown values.
        """
        unique = sorted({name for name in names if name})
        self._profile_names = unique
        if hasattr(self, "entry_profile"):
            try:
                self.entry_profile.configure(values=self._profile_names)
            except tk.TclError:
                pass

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
        if not self._confirm_can_id_collisions():
            return
        if not self._confirm_terminators():
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
        self._dirty = False
        self._set_profile_names(self._profile_names + [profile_name])
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
        if not self._confirm_can_id_collisions():
            return
        if not self._confirm_terminators():
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
        self._dirty = False
        self._set_profile_names(sorted(profiles.keys()))
        messagebox.showinfo("Saved", f"Updated {path} with profile '{profile_name}'.")

    def _validate_nodes(self) -> Optional[str]:
        """
        NAME
            _validate_nodes - Enforce category constraints before save.

        RETURNS
            Error message or None when valid.
        """
        seen_singletons = {}
        seen_strict: Dict[Tuple[str, str, int], Node] = {}
        for node in self._device_nodes():
            if node.category in SINGLETON_CATEGORIES:
                if node.category in seen_singletons:
                    return f"Only one {node.category} is allowed."
                seen_singletons[node.category] = node
            if node.category == GENERIC_CATEGORY:
                if not node.vendor or not node.device_type:
                    return "Generic devices require vendor and device type."
            if not self._is_valid_can_id(node.can_id):
                return f"Invalid CAN ID {node.can_id} for {node.label}."
            strict_key = self._dup_key_for_node(node)
            if strict_key is not None:
                vendor, dev_type, can_id = strict_key
                strict_key = (vendor, dev_type, can_id)
                if strict_key in seen_strict:
                    other = seen_strict[strict_key]
                    return (
                        f"Duplicate CAN address (vendor/type/id) {can_id} "
                        f"({other.label}, {node.label})."
                    )
                seen_strict[strict_key] = node
            if node.limits is not None:
                try:
                    self._normalize_limits(node.limits)
                except ValueError as exc:
                    return f"Invalid limits for {node.label}: {exc}"
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
            entries = [self._node_to_entry(n) for n in self._device_nodes() if n.category == category]
            if entries:
                profile[category] = entries
        for category in SINGLETON_CATEGORIES:
            entries = [self._node_to_entry(n) for n in self._device_nodes() if n.category == category]
            if entries:
                profile[category] = entries[0]
        generic_entries = [self._node_to_entry(n) for n in self._device_nodes() if n.category == GENERIC_CATEGORY]
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
            entry["limits"] = self._normalize_limits(node.limits)
        if node.terminator is not None:
            entry["terminator"] = node.terminator
        return entry

    @staticmethod
    def _is_valid_can_id(value: int) -> bool:
        """
        NAME
            _is_valid_can_id - Validate a CAN ID for compatibility.

        RETURNS
            True when the ID is -1 or in the 0-62 range.
        """
        return isinstance(value, int) and value >= -1 and value <= 62

    @staticmethod
    def _normalize_limits(limits: Dict[str, object]) -> Dict[str, object]:
        """
        NAME
            _normalize_limits - Normalize limit switch fields for JSON output.

        RETURNS
            Limits dict with integer DIO values and boolean invert.
        """
        if not isinstance(limits, dict):
            raise ValueError("limits must be an object")
        fwd = limits.get("fwdDio", -1)
        rev = limits.get("revDio", -1)
        invert = bool(limits.get("invert", False))

        def _coerce_dio(value: object, label: str) -> int:
            if value is None or value == "":
                return -1
            if isinstance(value, bool):
                raise ValueError(f"{label} must be an integer")
            if isinstance(value, (int,)):
                dio = int(value)
            elif isinstance(value, str) and re.fullmatch(r"-?\d+", value.strip()):
                dio = int(value.strip())
            else:
                raise ValueError(f"{label} must be an integer")
            if dio < -1:
                raise ValueError(f"{label} must be -1 or greater")
            return dio

        return {
            "fwdDio": _coerce_dio(fwd, "fwdDio"),
            "revDio": _coerce_dio(rev, "revDio"),
            "invert": invert,
        }

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
                scale=1.0,
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
        nodes: List[Dict[str, object]] = []
        for node in self._nodes:
            if node.node_type == "callout":
                nodes.append(
                    {
                        "nodeType": "callout",
                        "text": node.callout_text,
                        "targetType": node.callout_target_type,
                        "targetBus": node.callout_target_bus,
                        "targetNodeKey": node.callout_target_node_key,
                        "targetCategory": node.callout_target_category,
                        "targetLabel": node.callout_target_label,
                        "targetId": node.callout_target_id,
                        "x": node.x,
                        "y": self._node_center_y_unscaled(node),
                        "freeY": self._node_center_y_unscaled(node),
                        "bus": node.bus_index,
                        "row": node.row,
                        "scale": node.scale,
                    }
                )
            else:
                nodes.append(
                    {
                        "nodeType": "device",
                    "category": node.category,
                    "label": node.label,
                    "id": node.can_id,
                    "bus": node.bus_index,
                    "row": node.row,
                    "x": node.x,
                    "freeY": self._node_center_y_unscaled(node),
                    "scale": node.scale,
                }
                )
        return {
            "busOffsets": list(self._bus_offsets),
            "busCount": len(self._bus_offsets),
            "busSpacing": self._bus_spacing,
            "busLefts": list(self._bus_lefts),
            "busRights": list(self._bus_rights),
            "panY": self._pan_y,
            "zoom": self._zoom,
            "nodes": nodes,
        }

    def _apply_diagram_snapshot(self, diagram: Dict[str, object]) -> None:
        """
        NAME
            _apply_diagram_snapshot - Restore editor layout metadata.
        """
        bus_offsets = diagram.get("busOffsets")
        if isinstance(bus_offsets, list) and bus_offsets:
            self._bus_offsets = [float(x) for x in bus_offsets if isinstance(x, (int, float))]
        else:
            bus_count = diagram.get("busCount")
            if isinstance(bus_count, int) and bus_count > 0:
                self._bus_offsets = [i * self._bus_spacing for i in range(bus_count)]
        spacing = diagram.get("busSpacing")
        if isinstance(spacing, (int, float)) and spacing > 0:
            self._bus_spacing = float(spacing)
            self._bus_offsets = [i * self._bus_spacing for i in range(len(self._bus_offsets))]
        bus_lefts = diagram.get("busLefts")
        bus_rights = diagram.get("busRights")
        if isinstance(bus_lefts, list):
            self._bus_lefts = [float(x) for x in bus_lefts if isinstance(x, (int, float))]
        if isinstance(bus_rights, list):
            self._bus_rights = [float(x) for x in bus_rights if isinstance(x, (int, float))]
        pan_y = diagram.get("panY")
        if isinstance(pan_y, (int, float)):
            self._pan_y = float(pan_y)
        zoom = diagram.get("zoom")
        if isinstance(zoom, (int, float)):
            self._zoom = max(0.6, min(2.0, float(zoom)))

        # Drop existing callout nodes before applying snapshot data.
        self._nodes = [n for n in self._nodes if n.node_type == "device"]
        device_keys = {n.key for n in self._nodes}

        nodes = diagram.get("nodes")
        loaded_callouts = False
        if isinstance(nodes, list):
            for entry in nodes:
                if not isinstance(entry, dict):
                    continue
                node_type = entry.get("nodeType") or entry.get("node_type") or "device"
                if node_type == "callout" or ("text" in entry and "targetType" in entry):
                    callout_y = float(entry.get("y", entry.get("callout_y", 0.0)))
                    free_y = entry.get("freeY")
                    bus_index = entry.get("bus")
                    row = entry.get("row")
                    if not isinstance(bus_index, int) or not isinstance(row, int):
                        bus_index, row = self._nearest_bus_and_row_from_offset(callout_y)
                    free_val = None
                    if isinstance(free_y, (int, float)):
                        # TODO(major-refactor): Remove legacy freeY absolute->relative migration after re-saving profiles.
                        free_val = float(free_y)
                        if self._bus_offsets:
                            bus_offset = self._bus_offsets[min(max(int(bus_index), 0), len(self._bus_offsets) - 1)]
                            if abs(free_val) > 200.0 or abs(free_val - callout_y) < 0.5:
                                free_val = free_val - bus_offset
                    callout = Node(
                        key=self._next_key,
                        category="callout",
                        label=str(entry.get("text", "")),
                        can_id=-1,
                        node_type="callout",
                        x=float(entry.get("x", 0.0)),
                        row=int(row),
                        bus_index=int(bus_index),
                        scale=float(entry.get("scale", 1.0)),
                        callout_text=str(entry.get("text", "")),
                        callout_target_type=str(entry.get("targetType", entry.get("callout_target_type", "node"))),
                        callout_target_bus=int(entry.get("targetBus", entry.get("callout_target_bus", 0)) or 0),
                        callout_target_node_key=entry.get("targetNodeKey", entry.get("callout_target_node_key")),
                        callout_target_category=str(entry.get("targetCategory", "")),
                        callout_target_label=str(entry.get("targetLabel", "")),
                        callout_target_id=entry.get("targetId"),
                        callout_y=callout_y,
                        free_y=free_val,
                    )
                    if callout.callout_target_type == "node":
                        if callout.callout_target_node_key not in device_keys:
                            resolved = None
                            if callout.callout_target_category or callout.callout_target_label:
                                for node in self._device_nodes():
                                    if callout.callout_target_category and node.category != callout.callout_target_category:
                                        continue
                                    if callout.callout_target_id is not None and node.can_id != callout.callout_target_id:
                                        continue
                                    if callout.callout_target_label and node.label != callout.callout_target_label:
                                        continue
                                    resolved = node
                                    break
                            if resolved is not None:
                                callout.callout_target_node_key = resolved.key
                                callout.callout_target_category = resolved.category
                                callout.callout_target_label = resolved.label
                                callout.callout_target_id = resolved.can_id
                            else:
                                # Fallback: snap to nearest node on the same bus (or overall).
                                nearest = None
                                best = float("inf")
                                target_bus = int(entry.get("targetBus", entry.get("callout_target_bus", 0)) or 0)
                                for node in self._device_nodes():
                                    if node.bus_index != target_bus:
                                        continue
                                    dist = abs(node.x - callout.x)
                                    if dist < best:
                                        best = dist
                                        nearest = node
                                if nearest is None:
                                    for node in self._device_nodes():
                                        dist = abs(node.x - callout.x)
                                        if dist < best:
                                            best = dist
                                            nearest = node
                                if nearest is not None:
                                    callout.callout_target_type = "node"
                                    callout.callout_target_node_key = nearest.key
                                    callout.callout_target_category = nearest.category
                                    callout.callout_target_label = nearest.label
                                    callout.callout_target_id = nearest.can_id
                                else:
                                    callout.callout_target_type = "bus"
                                    callout.callout_target_bus = target_bus
                                    callout.callout_target_node_key = None
                    self._next_key += 1
                    self._nodes.append(callout)
                    loaded_callouts = True
                    continue
                cat = entry.get("category")
                label = entry.get("label")
                node_id = entry.get("id")
                for node in self._device_nodes():
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
                        scale = entry.get("scale")
                    if isinstance(scale, (int, float)):
                        node.scale = max(0.6, min(2.0, float(scale)))
                    free_y = entry.get("freeY")
                    if isinstance(free_y, (int, float)):
                        # TODO(major-refactor): Remove legacy freeY absolute->relative migration after re-saving profiles.
                        free_val = float(free_y)
                        if self._bus_offsets:
                            bus_offset = self._bus_offsets[min(max(node.bus_index, 0), len(self._bus_offsets) - 1)]
                            if abs(free_val) > 200.0:
                                free_val = free_val - bus_offset
                        node.free_y = free_val

        # Legacy format: convert callouts list into callout nodes.
        callouts = diagram.get("callouts")
        if not loaded_callouts and isinstance(callouts, list):
            for entry in callouts:
                if not isinstance(entry, dict):
                    continue
                callout_y = float(entry.get("y", 0.0))
                free_y = entry.get("freeY")
                bus_index = entry.get("bus")
                row = entry.get("row")
                if not isinstance(bus_index, int) or not isinstance(row, int):
                    bus_index, row = self._nearest_bus_and_row_from_offset(callout_y)
                free_val = None
                if isinstance(free_y, (int, float)):
                    # TODO(major-refactor): Remove legacy freeY absolute->relative migration after re-saving profiles.
                    free_val = float(free_y)
                    if self._bus_offsets:
                        bus_offset = self._bus_offsets[min(max(int(bus_index), 0), len(self._bus_offsets) - 1)]
                        if abs(free_val) > 200.0 or abs(free_val - callout_y) < 0.5:
                            free_val = free_val - bus_offset
                callout = Node(
                    key=self._next_key,
                    category="callout",
                    label=str(entry.get("text", "")),
                    can_id=-1,
                    node_type="callout",
                    x=float(entry.get("x", 0.0)),
                    row=int(row),
                    bus_index=int(bus_index),
                    scale=float(entry.get("scale", 1.0)),
                    callout_text=str(entry.get("text", "")),
                    callout_target_type=str(entry.get("targetType", entry.get("target_type", "node"))),
                    callout_target_bus=int(entry.get("targetBus", entry.get("target_bus", 0)) or 0),
                    callout_target_node_key=entry.get("targetNodeKey", entry.get("target_node_key")),
                    callout_target_category=str(entry.get("targetCategory", "")),
                    callout_target_label=str(entry.get("targetLabel", "")),
                    callout_target_id=entry.get("targetId"),
                    callout_y=callout_y,
                    free_y=free_val,
                )
                if callout.callout_target_type == "node":
                    if callout.callout_target_node_key not in device_keys:
                        resolved = None
                        if callout.callout_target_category or callout.callout_target_label:
                            for node in self._device_nodes():
                                if callout.callout_target_category and node.category != callout.callout_target_category:
                                    continue
                                if callout.callout_target_id is not None and node.can_id != callout.callout_target_id:
                                    continue
                                if callout.callout_target_label and node.label != callout.callout_target_label:
                                    continue
                                resolved = node
                                break
                        if resolved is not None:
                            callout.callout_target_node_key = resolved.key
                            callout.callout_target_category = resolved.category
                            callout.callout_target_label = resolved.label
                            callout.callout_target_id = resolved.can_id
                        else:
                            # Fallback: snap to nearest node on the same bus (or overall).
                            nearest = None
                            best = float("inf")
                            target_bus = int(entry.get("targetBus", entry.get("target_bus", 0)) or 0)
                            for node in self._device_nodes():
                                if node.bus_index != target_bus:
                                    continue
                                dist = abs(node.x - callout.x)
                                if dist < best:
                                    best = dist
                                    nearest = node
                            if nearest is None:
                                for node in self._device_nodes():
                                    dist = abs(node.x - callout.x)
                                    if dist < best:
                                        best = dist
                                        nearest = node
                            if nearest is not None:
                                callout.callout_target_type = "node"
                                callout.callout_target_node_key = nearest.key
                                callout.callout_target_category = nearest.category
                                callout.callout_target_label = nearest.label
                                callout.callout_target_id = nearest.can_id
                            else:
                                callout.callout_target_type = "bus"
                                callout.callout_target_bus = target_bus
                                callout.callout_target_node_key = None
                self._next_key += 1
                self._nodes.append(callout)

        self._resolve_overlaps()

    def _confirm_discard(self) -> bool:
        """
        NAME
            _confirm_discard - Ask before discarding current diagram.
        """
        if not self._dirty:
            return True
        return messagebox.askyesno("Discard Changes", "Discard the current diagram?")

    def _on_close(self) -> None:
        """
        NAME
            _on_close - Confirm before closing when there are unsaved changes.
        """
        if not self._confirm_discard():
            return
        self.destroy()

    def _on_add(self) -> None:
        """
        NAME
            _on_add - Add a new node to the diagram.
        """
        dialog = NodeDialog(self, "Add Node")
        self.wait_window(dialog)
        if not dialog.result:
            return
        self._push_undo()
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
            scale=1.0,
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
        self._push_undo()
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
        self._push_undo()
        self._nodes = [n for n in self._nodes if n.key != node.key]
        self._selected_key = None
        self._refresh_list()
        self._update_details_panel(None)
        self._redraw_canvas()

    def _on_edit_selected(self) -> None:
        """
        NAME
            _on_edit_selected - Edit the selected node or callout.
        """
        if self._selected_buses:
            messagebox.showinfo("Edit", "Bus segments are not editable.")
            return
        if len(self._selected_nodes) == 1:
            node = self._get_selected_node()
            if node is not None and node.node_type == "callout":
                self._on_edit_callout()
            else:
                self._on_edit()
            return
        messagebox.showinfo("Edit", "Select a single node or callout to edit.")

    def _on_remove_selected(self) -> None:
        """
        NAME
            _on_remove_selected - Remove selected nodes and callouts.
        """
        if self._selected_buses and not self._selected_nodes:
            if not self._remove_selected_buses():
                return
            self._refresh_list()
            self._update_details_panel(None)
            self._redraw_canvas()
            return
        if not self._selected_nodes:
            messagebox.showinfo("Remove", "Select nodes or callouts to remove.")
            return
        if not messagebox.askyesno("Remove", "Remove selected nodes/callouts?"):
            return
        self._push_undo()
        self._nodes = [n for n in self._nodes if n.key not in self._selected_nodes]
        self._clear_selection()
        self._refresh_list()
        self._update_details_panel(None)
        if hasattr(self, "_callout_details_panel"):
            self._preserve_canvas_view(self._callout_details_panel.pack_forget)
        self._redraw_canvas()

    def _remove_selected_buses(self) -> bool:
        """
        NAME
            _remove_selected_buses - Remove selected empty bus segments.

        RETURNS
            True when buses were removed, False when blocked.
        """
        indices = sorted(set(idx for idx in self._selected_buses if 0 <= idx < len(self._bus_offsets)))
        if not indices:
            messagebox.showinfo("Remove", "Select bus segments to remove.")
            return False
        if len(self._bus_offsets) - len(indices) < 1:
            messagebox.showinfo("Remove", "At least one bus segment is required.")
            return False
        device_nodes = self._device_nodes()
        callouts = self._callout_nodes()
        for idx in indices:
            if any(node.bus_index == idx for node in device_nodes):
                messagebox.showinfo("Remove", "Bus segment has nodes attached and cannot be removed.")
                return False
            if any(
                callout.callout_target_type == "bus" and callout.callout_target_bus == idx
                for callout in callouts
            ):
                messagebox.showinfo("Remove", "Bus segment has callouts attached and cannot be removed.")
                return False
        if not messagebox.askyesno("Remove", "Remove selected empty bus segments?"):
            return False
        self._push_undo()
        for idx in reversed(indices):
            del self._bus_offsets[idx]
            if idx < len(self._bus_lefts):
                del self._bus_lefts[idx]
            if idx < len(self._bus_rights):
                del self._bus_rights[idx]
        def _shift_index(old: int) -> int:
            return old - sum(1 for removed in indices if removed < old)
        for node in device_nodes:
            if node.bus_index in indices:
                node.bus_index = 0
            else:
                node.bus_index = _shift_index(node.bus_index)
        for callout in callouts:
            if callout.callout_target_type != "bus":
                continue
            if callout.callout_target_bus in indices:
                callout.callout_target_bus = 0
            else:
                callout.callout_target_bus = _shift_index(callout.callout_target_bus)
        self._clear_selection()
        return True

    def _refresh_list(self) -> None:
        """
        NAME
            _refresh_list - Update the listbox contents.
        """
        for item in self.node_list.get_children():
            self.node_list.delete(item)
        nodes = sorted(self._device_nodes(), key=lambda n: int(n.can_id))
        for node in nodes:
            self.node_list.insert(
                "",
                "end",
                iid=str(node.key),
                values=(str(node.can_id), node.category, node.label),
            )

    def _layout_even(self) -> None:
        """
        NAME
            _layout_even - Reset layout per bus without reassigning buses/rows.
        """
        if not self._nodes:
            self._redraw_canvas()
            return
        self._push_undo()
        width = max(self.canvas.winfo_width(), 1)
        if width < 200:
            self.after(80, self._layout_even)
            return
        eff_lefts, eff_rights = self._effective_bus_bounds()
        groups: Dict[int, List[Node]] = {}
        for node in self._device_nodes():
            groups.setdefault(node.bus_index, []).append(node)
        margin = 12.0
        for bus_index, group in groups.items():
            if not group:
                continue
            group.sort(key=lambda n: n.x)
            left = eff_lefts[bus_index] if bus_index < len(eff_lefts) else 40.0
            right = eff_rights[bus_index] if bus_index < len(eff_rights) else left + 400.0
            avail_left = left + margin
            avail_right = right - margin
            count = len(group)
            if count == 1:
                pos = (avail_left + avail_right) / 2.0
                node = group[0]
                half_w = self._node_half_width(node)
                node.x = max(left + half_w + margin, min(right - half_w - margin, pos))
                if self._snap_to_grid_var.get():
                    node.x = self._snap_value(node.x)
                continue
            spacing = (avail_right - avail_left) / max(count - 1, 1)
            for idx, node in enumerate(group):
                target = avail_left + spacing * idx
                half_w = self._node_half_width(node)
                min_bound = left + half_w + margin
                max_bound = right - half_w - margin
                if min_bound > max_bound:
                    min_bound = max_bound = (left + right) / 2.0
                node.x = max(min_bound, min(max_bound, target))
                if self._snap_to_grid_var.get():
                    node.x = self._snap_value(node.x)
        max_x = max((n.x for n in self._nodes), default=0.0)
        self._layout_width = max(self._layout_width, max_x + 200)
        self._clear_guides()
        self._redraw_canvas()

    def _selected_device_nodes(self) -> List[Node]:
        """
        NAME
            _selected_device_nodes - Return selected device nodes only.
        """
        return [n for n in self._device_nodes() if n.key in self._selected_nodes]

    def _effective_bus_bounds(self) -> Tuple[List[float], List[float]]:
        """
        NAME
            _effective_bus_bounds - Compute bus left/right bounds with connectors.

        RETURNS
            Tuple of (effective_lefts, effective_rights) per bus segment.
        """
        max_node_x = max((n.x for n in self._nodes), default=0.0)
        if len(self._bus_lefts) < len(self._bus_offsets):
            self._bus_lefts.extend([40.0] * (len(self._bus_offsets) - len(self._bus_lefts)))
        if len(self._bus_rights) < len(self._bus_offsets):
            self._bus_rights.extend(
                [max_node_x + 200.0] * (len(self._bus_offsets) - len(self._bus_rights))
            )
        if len(self._bus_lefts) > len(self._bus_offsets):
            self._bus_lefts = self._bus_lefts[: len(self._bus_offsets)]
        if len(self._bus_rights) > len(self._bus_offsets):
            self._bus_rights = self._bus_rights[: len(self._bus_offsets)]
        eff_lefts = list(self._bus_lefts)
        eff_rights = list(self._bus_rights)
        for idx in range(len(eff_lefts) - 1):
            if idx % 2 == 0:
                eff_rights[idx + 1] = eff_rights[idx]
            else:
                eff_lefts[idx + 1] = eff_lefts[idx]
        return eff_lefts, eff_rights

    def _node_half_width(self, node: Node) -> float:
        """
        NAME
            _node_half_width - Compute half the node width in diagram units.
        """
        node_scale = max(0.6, min(2.0, node.scale))
        base_w = 180.0 if node.node_type == "callout" else float(self._box_w)
        return base_w * node_scale / 2.0

    def _snap_value(self, value: float) -> float:
        """
        NAME
            _snap_value - Snap a value to the current grid size.
        """
        size = max(1, int(self._grid_size_var.get() or 1))
        return round(value / size) * size

    def _clear_guides(self) -> None:
        """
        NAME
            _clear_guides - Clear any active smart guide lines.
        """
        self._guide_x = None
        self._guide_bus = None

    def _apply_smart_guides(
        self,
        node: Node,
        candidate_x: float,
        exclude_keys: set[int],
    ) -> Tuple[float, Optional[float]]:
        """
        NAME
            _apply_smart_guides - Snap to nearby node centers on the same bus.

        RETURNS
            Tuple of (new_x, guide_x or None).
        """
        if not self._smart_guides_var.get():
            return candidate_x, None
        scale = max(self._zoom, 0.01)
        threshold = self._guide_snap_px / scale
        nearest: Optional[float] = None
        nearest_score = float("inf")
        for other in self._device_nodes():
            if other.key in exclude_keys:
                continue
            dist = abs(other.x - candidate_x)
            if dist <= threshold:
                same_bus = 0.0 if other.bus_index == node.bus_index else 0.5
                score = dist + same_bus
                if score < nearest_score:
                    nearest = other.x
                    nearest_score = score
        if nearest is None:
            return candidate_x, None
        return nearest, nearest

    def _align_selected(self, mode: str) -> None:
        """
        NAME
            _align_selected - Align selected nodes horizontally.

        PARAMETERS
            mode - "left", "center", or "right".
        """
        nodes = self._selected_device_nodes()
        if not nodes:
            messagebox.showinfo("Align", "Select one or more device nodes to align.")
            return
        eff_lefts, eff_rights = self._effective_bus_bounds()
        grouped: Dict[int, List[Node]] = {}
        for node in nodes:
            grouped.setdefault(node.bus_index, []).append(node)
        self._push_undo()
        margin = 10.0
        for bus_index, group in grouped.items():
            if not group:
                continue
            xs = [n.x for n in group]
            if mode == "left":
                target = min(xs)
            elif mode == "right":
                target = max(xs)
            else:
                target = (min(xs) + max(xs)) / 2.0
            left = eff_lefts[bus_index] if bus_index < len(eff_lefts) else 40.0
            right = eff_rights[bus_index] if bus_index < len(eff_rights) else target + 200.0
            for node in group:
                half_w = self._node_half_width(node)
                min_x = left + half_w + margin
                max_x = right - half_w - margin
                if min_x > max_x:
                    min_x = max_x = (left + right) / 2.0
                node.x = max(min_x, min(max_x, target))
                if self._snap_to_grid_var.get():
                    node.x = self._snap_value(node.x)
        max_x = max((n.x for n in self._nodes), default=0.0)
        self._layout_width = max(self._layout_width, max_x + 200)
        self._clear_guides()
        self._redraw_canvas()

    def _distribute_selected_horizontally(self) -> None:
        """
        NAME
            _distribute_selected_horizontally - Evenly space selected nodes.
        """
        nodes = self._selected_device_nodes()
        if len(nodes) < 3:
            messagebox.showinfo(
                "Distribute",
                "Select at least three device nodes to distribute.",
            )
            return
        eff_lefts, eff_rights = self._effective_bus_bounds()
        grouped: Dict[int, List[Node]] = {}
        for node in nodes:
            grouped.setdefault(node.bus_index, []).append(node)
        self._push_undo()
        margin = 10.0
        for bus_index, group in grouped.items():
            if len(group) < 3:
                continue
            group.sort(key=lambda n: n.x)
            left = eff_lefts[bus_index] if bus_index < len(eff_lefts) else 40.0
            right = eff_rights[bus_index] if bus_index < len(eff_rights) else group[-1].x + 200.0
            min_x = max(left + margin, group[0].x)
            max_x = min(right - margin, group[-1].x)
            spacing = (max_x - min_x) / max(len(group) - 1, 1)
            for idx, node in enumerate(group):
                target = min_x + spacing * idx
                half_w = self._node_half_width(node)
                min_bound = left + half_w + margin
                max_bound = right - half_w - margin
                if min_bound > max_bound:
                    min_bound = max_bound = (left + right) / 2.0
                node.x = max(min_bound, min(max_bound, target))
                if self._snap_to_grid_var.get():
                    node.x = self._snap_value(node.x)
        max_x = max((n.x for n in self._nodes), default=0.0)
        self._layout_width = max(self._layout_width, max_x + 200)
        self._clear_guides()
        self._redraw_canvas()

    def _tidy_selection(self) -> None:
        """
        NAME
            _tidy_selection - Tidy selected nodes within bus bounds.
        """
        nodes = self._selected_device_nodes()
        if not nodes:
            messagebox.showinfo("Tidy Selection", "Select one or more device nodes to tidy.")
            return
        eff_lefts, eff_rights = self._effective_bus_bounds()
        grouped: Dict[int, List[Node]] = {}
        for node in nodes:
            grouped.setdefault(node.bus_index, []).append(node)
        self._push_undo()
        margin = 12.0
        bus_indices = [idx for idx in grouped.keys() if 0 <= idx < len(eff_lefts)]
        max_columns = max((len(group) for group in grouped.values()), default=0)
        use_columns = len(bus_indices) > 1 and max_columns >= 2
        shared_left = max((eff_lefts[idx] for idx in bus_indices), default=40.0)
        shared_right = min(
            (eff_rights[idx] for idx in bus_indices),
            default=max((n.x for n in nodes), default=0.0) + 200.0,
        )
        max_half = max((self._node_half_width(n) for n in nodes), default=0.0)
        if use_columns:
            left_bound = shared_left + max_half + margin
            right_bound = shared_right - max_half - margin
            if right_bound - left_bound < 40.0:
                use_columns = False
        for bus_index, group in grouped.items():
            if not group:
                continue
            group.sort(key=lambda n: n.x)
            left = eff_lefts[bus_index] if bus_index < len(eff_lefts) else 40.0
            right = eff_rights[bus_index] if bus_index < len(eff_rights) else group[-1].x + 200.0
            if use_columns:
                left_bound = shared_left + max_half + margin
                right_bound = shared_right - max_half - margin
                columns = max_columns
                if columns <= 1 or right_bound <= left_bound:
                    use_columns = False
                else:
                    spacing = (right_bound - left_bound) / max(columns - 1, 1)
                    col_positions = [left_bound + spacing * idx for idx in range(columns)]
                    count = len(group)
                    for idx, node in enumerate(group):
                        if count <= 1:
                            col_idx = (columns - 1) // 2
                        else:
                            col_idx = int(round(idx * (columns - 1) / (count - 1)))
                        col_idx = max(0, min(columns - 1, col_idx))
                        pos = col_positions[col_idx]
                        half_w = self._node_half_width(node)
                        min_bound = left + half_w + margin
                        max_bound = right - half_w - margin
                        if min_bound > max_bound:
                            min_bound = max_bound = (left + right) / 2.0
                        node.x = max(min_bound, min(max_bound, pos))
                        if self._snap_to_grid_var.get():
                            node.x = self._snap_value(node.x)
                    continue
            left_bound = left + margin
            right_bound = right - margin
            widths = [self._node_half_width(n) * 2 for n in group]
            total_width = sum(widths)
            count = len(group)
            available = max(1.0, right_bound - left_bound)
            gap = 20.0
            if count > 1:
                gap = max(0.0, (available - total_width) / (count - 1))
            positions: List[float] = []
            cursor = left_bound
            for node, width in zip(group, widths):
                half_w = width / 2.0
                cursor = cursor + half_w
                positions.append(cursor)
                cursor = cursor + half_w + gap
            if positions:
                first_half = widths[0] / 2.0
                last_half = widths[-1] / 2.0
                min_edge = positions[0] - first_half
                max_edge = positions[-1] + last_half
                if max_edge > right_bound:
                    shift = max_edge - right_bound
                    positions = [p - shift for p in positions]
                if positions[0] - first_half < left_bound:
                    shift = left_bound - (positions[0] - first_half)
                    positions = [p + shift for p in positions]
            for node, pos in zip(group, positions):
                half_w = self._node_half_width(node)
                min_bound = left + half_w + margin
                max_bound = right - half_w - margin
                if min_bound > max_bound:
                    min_bound = max_bound = (left + right) / 2.0
                node.x = max(min_bound, min(max_bound, pos))
                if self._snap_to_grid_var.get():
                    node.x = self._snap_value(node.x)
        max_x = max((n.x for n in self._nodes), default=0.0)
        self._layout_width = max(self._layout_width, max_x + 200)
        self._clear_guides()
        self._redraw_canvas()

    def _tidy_all(self) -> None:
        """
        NAME
            _tidy_all - Tidy all device nodes while preserving bus assignments.
        """
        device_nodes = self._device_nodes()
        if not device_nodes:
            messagebox.showinfo("Tidy All", "No device nodes to tidy.")
            return
        prior_nodes = set(self._selected_nodes)
        prior_buses = set(self._selected_buses)
        try:
            self._selected_nodes = {n.key for n in device_nodes}
            self._selected_buses = set()
            self._tidy_selection()
        finally:
            self._selected_nodes = prior_nodes
            self._selected_buses = prior_buses
            self._sync_selection_state()

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
        if self._suppress_list_select or self._syncing_selection:
            return
        selection = self.node_list.selection()
        if not selection:
            return
        try:
            key = int(selection[0])
        except ValueError:
            return
        self._set_single_node_selection(key)

    def _select_node(self, key: int) -> None:
        """
        NAME
            _select_node - Mark a node as selected and update styles.
        """
        self._set_single_node_selection(key)

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

    def _confirm_can_id_collisions(self) -> bool:
        """
        NAME
            _confirm_can_id_collisions - Warn about duplicate CAN IDs.

        RETURNS
            True when ok to proceed, False to cancel save.
        """
        nodes = self._device_nodes()
        by_loose: Dict[int, List[Node]] = {}
        by_strict: Dict[Tuple[str, str, int], List[Node]] = {}
        for node in nodes:
            if not isinstance(node.can_id, int) or node.can_id < 0:
                continue
            can_id = int(node.can_id)
            by_loose.setdefault(can_id, []).append(node)
            vendor = self._vendor_key_for_node(node) or ""
            dev_type = self._device_type_key_for_node(node) or ""
            key = (vendor, dev_type, can_id)
            by_strict.setdefault(key, []).append(node)
        loose = {cid: items for cid, items in by_loose.items() if len(items) > 1}
        strict = {key: items for key, items in by_strict.items() if len(items) > 1}
        if not loose and not strict:
            return True
        lines = []
        if loose:
            lines.append("Loose collisions (same CAN ID, any device):")
            for cid, items in sorted(loose.items(), key=lambda item: item[0]):
                names = ", ".join(self._format_node_identity(n) for n in items)
                lines.append(f"  ID {cid}: {names}")
            lines.append("")
        if strict:
            lines.append("Strict collisions (same vendor + type + CAN ID):")
            for key, items in sorted(strict.items(), key=lambda item: item[0]):
                vendor, dev_type, cid = key
                details = f"{vendor}/{dev_type}"
                names = ", ".join(self._format_node_identity(n) for n in items)
                lines.append(f"  ID {cid} {details}: {names}")
            lines.append("")
        if loose and not strict:
            lines.append("Loose collisions may be intentional if vendor/type disambiguates IDs.")
        if strict:
            lines.append("Strict collisions indicate exact ID conflicts for the same device type.")
        lines.append("")
        lines.append("Save anyway?")
        return messagebox.askyesno("CAN ID Collision", "\n".join(lines))

    def _format_node_identity(self, node: Node) -> str:
        """
        NAME
            _format_node_identity - Build a short label for collision dialogs.
        """
        details = self._format_strict_descriptor(node)
        return f"{node.label} ({details})"

    def _format_strict_descriptor(self, node: Node) -> str:
        """
        NAME
            _format_strict_descriptor - Format category/vendor/type for strict collisions.
        """
        parts = [node.category]
        if node.vendor:
            parts.append(node.vendor)
        if node.device_type:
            parts.append(node.device_type)
        return "/".join(parts)

    def _device_nodes(self) -> List[Node]:
        """
        NAME
            _device_nodes - Return device nodes only.
        """
        return [n for n in self._nodes if n.node_type == "device"]

    def _callout_nodes(self) -> List[Node]:
        """
        NAME
            _callout_nodes - Return callout nodes only.
        """
        return [n for n in self._nodes if n.node_type == "callout"]

    def _node_box_dims(self, node: Node, scale: float) -> Tuple[float, float]:
        """
        NAME
            _node_box_dims - Return box width/height for a node at a scale.
        """
        node_scale = max(0.6, min(2.0, node.scale))
        if node.node_type == "callout":
            return 180 * scale * node_scale, 50 * scale * node_scale
        return self._box_w * scale * node_scale, self._box_h * scale * node_scale

    def _node_box_y(self, node: Node, bus_y: float, box_h: float, scale: float) -> Tuple[float, float]:
        """
        NAME
            _node_box_y - Return top/bottom Y coordinates for a node box.
        """
        if node.row == 1:
            y0 = bus_y + 30 * scale
            y1 = y0 + box_h
        else:
            y1 = bus_y - 30 * scale
            y0 = y1 - box_h
        return y0, y1

    def _node_center_y_unscaled(self, node: Node) -> float:
        """
        NAME
            _node_center_y_unscaled - Compute unscaled center Y for a node.
        """
        if node.free_y is not None:
            if not self._bus_offsets:
                return node.free_y
            bus_index = min(max(node.bus_index, 0), max(len(self._bus_offsets) - 1, 0))
            return self._bus_offsets[bus_index] + node.free_y
        if not self._bus_offsets:
            bus_offset = 0.0
        else:
            bus_index = min(max(node.bus_index, 0), max(len(self._bus_offsets) - 1, 0))
            bus_offset = self._bus_offsets[bus_index]
        node_scale = max(0.6, min(2.0, node.scale))
        if node.node_type == "callout":
            box_h = 50.0 * node_scale
        else:
            box_h = float(self._box_h) * node_scale
        if node.row == 1:
            return bus_offset + 30.0 + box_h / 2.0
        return bus_offset - 30.0 - box_h / 2.0

    def _nearest_bus_and_row_from_offset(self, y_offset: float) -> Tuple[int, int]:
        """
        NAME
            _nearest_bus_and_row_from_offset - Pick nearest bus/row from an offset.
        """
        if not self._bus_offsets:
            return 0, 0
        nearest = 0
        best = float("inf")
        for idx, bus_offset in enumerate(self._bus_offsets):
            dist = abs(y_offset - bus_offset)
            if dist < best:
                best = dist
                nearest = idx
        row = 0 if y_offset < self._bus_offsets[nearest] else 1
        return nearest, row

    def _resolve_overlaps(self) -> None:
        """
        NAME
            _resolve_overlaps - Nudge overlapping nodes so they render distinctly.
        """
        if not self._nodes:
            return
        if len(self._bus_lefts) < len(self._bus_offsets):
            self._bus_lefts.extend([40.0] * (len(self._bus_offsets) - len(self._bus_lefts)))
        if len(self._bus_rights) < len(self._bus_offsets):
            max_node_x = max((n.x for n in self._nodes), default=0.0)
            self._bus_rights.extend(
                [max_node_x + 200.0] * (len(self._bus_offsets) - len(self._bus_rights))
            )
        min_gap = 10.0
        groups: Dict[Tuple[int, int], List[Node]] = {}
        for node in self._nodes:
            groups.setdefault((node.bus_index, node.row), []).append(node)
        for (bus_index, _row), nodes in groups.items():
            nodes.sort(key=lambda n: (n.x, n.key))
            prev_x = None
            prev_w = 0.0
            for node in nodes:
                node_scale = max(0.6, min(2.0, node.scale))
                base_w = 180.0 if node.node_type == "callout" else float(self._box_w)
                cur_w = base_w * node_scale
                if prev_x is not None:
                    min_spacing = prev_w / 2 + cur_w / 2 + min_gap
                    if node.x - prev_x < min_spacing:
                        node.x = prev_x + min_spacing
                prev_x = node.x
                prev_w = cur_w
            if 0 <= bus_index < len(self._bus_rights):
                max_x = max(n.x for n in nodes)
                self._bus_rights[bus_index] = max(self._bus_rights[bus_index], max_x + 120.0)

    def _set_single_node_selection(self, key: int) -> None:
        """
        NAME
            _set_single_node_selection - Select one node and clear other selections.
        """
        self._selected_nodes = {key}
        self._selected_buses = set()
        self._sync_selection_state()

    def _clear_selection(self) -> None:
        """
        NAME
            _clear_selection - Clear all current selections.
        """
        self._selected_nodes = set()
        self._selected_buses = set()
        self._sync_selection_state()

    def _select_all_nodes(self) -> None:
        """
        NAME
            _select_all_nodes - Select all nodes (devices + callouts), no buses.
        """
        self._selected_nodes = {n.key for n in self._nodes}
        self._selected_buses = set()
        self._sync_selection_state()

    def _duplicate_selection(self) -> None:
        """
        NAME
            _duplicate_selection - Duplicate the current selection.
        """
        self._on_copy()
        self._on_paste()

    def _toggle_snap_to_grid(self) -> None:
        """
        NAME
            _toggle_snap_to_grid - Toggle snap-to-grid behavior.
        """
        current = bool(self._snap_to_grid_var.get())
        self._snap_to_grid_var.set(not current)

    def _toggle_smart_guides(self) -> None:
        """
        NAME
            _toggle_smart_guides - Toggle smart guide display.
        """
        current = bool(self._smart_guides_var.get())
        self._smart_guides_var.set(not current)
        if not self._smart_guides_var.get():
            self._clear_guides()
            self._redraw_canvas()

    def _save_shortcut(self) -> None:
        """
        NAME
            _save_shortcut - Save using the default flow for the editor.
        """
        self._on_save_to_deploy()

    def _toggle_node_selection(self, key: int) -> None:
        """
        NAME
            _toggle_node_selection - Toggle a node in the multi-selection set.
        """
        if key in self._selected_nodes:
            self._selected_nodes.remove(key)
        else:
            self._selected_nodes.add(key)
        self._sync_selection_state()

    def _toggle_bus_selection(self, index: int) -> None:
        """
        NAME
            _toggle_bus_selection - Toggle a bus segment in the multi-selection set.
        """
        if index in self._selected_buses:
            self._selected_buses.remove(index)
        else:
            self._selected_buses.add(index)
        self._sync_selection_state()

    def _sync_selection_state(self) -> None:
        """
        NAME
            _sync_selection_state - Update selection-dependent UI and details panels.
        """
        if self._syncing_selection:
            return
        self._syncing_selection = True
        selected_nodes = list(self._selected_nodes)
        if len(selected_nodes) == 1 and not self._selected_buses:
            self._selected_key = selected_nodes[0]
            self._suppress_list_select = True
            try:
                current = self.node_list.selection()
                desired = (str(self._selected_key),)
                if current != desired:
                    for item in current:
                        self.node_list.selection_remove(item)
                    if self.node_list.exists(str(self._selected_key)):
                        self.node_list.selection_add(str(self._selected_key))
                        self.node_list.see(str(self._selected_key))
            finally:
                self._suppress_list_select = False
            node = self._get_selected_node()
            if node is not None and node.node_type == "callout":
                self._callout_scale_var.set(f"{node.scale:.2f}")
                if hasattr(self, "_callout_details_panel"):
                    self._details_layout_shift = True
                    self._preserve_canvas_view(
                        lambda: self._callout_details_panel.pack(fill="x", pady=(8, 0))
                    )
                if hasattr(self, "_node_details_panel"):
                    self._details_layout_shift = True
                    self._preserve_canvas_view(self._node_details_panel.pack_forget)
            else:
                if hasattr(self, "_callout_details_panel"):
                    self._details_layout_shift = True
                    self._preserve_canvas_view(self._callout_details_panel.pack_forget)
                self._callout_scale_var.set("?")
                self._update_details_panel(self._get_selected_node())
        else:
            self._selected_key = None
            self._suppress_list_select = True
            try:
                current = self.node_list.selection()
                if current:
                    for item in current:
                        self.node_list.selection_remove(item)
            finally:
                self._suppress_list_select = False
            if hasattr(self, "_node_details_panel"):
                self._details_layout_shift = True
                self._preserve_canvas_view(self._node_details_panel.pack_forget)
            if hasattr(self, "_callout_details_panel"):
                self._details_layout_shift = True
                self._preserve_canvas_view(self._callout_details_panel.pack_forget)
        self._redraw_canvas()
        self._syncing_selection = False

    def _shift_held(self, event: tk.Event) -> bool:
        """
        NAME
            _shift_held - Return True when the shift key is pressed.
        """
        return bool(getattr(event, "state", 0) & 0x0001)

    def _apply_marquee_selection(
        self, x0: float, y0: float, x1: float, y1: float, additive: bool
    ) -> None:
        """
        NAME
            _apply_marquee_selection - Select nodes/callouts/buses within a rectangle.
        """
        if not additive:
            self._selected_nodes = set()
            self._selected_buses = set()
        left, right = sorted((x0, x1))
        top, bottom = sorted((y0, y1))
        for key, bounds in self._node_bounds.items():
            bx0, by0, bx1, by1 = bounds
            if not (bx1 < left or bx0 > right or by1 < top or by0 > bottom):
                self._selected_nodes.add(key)
        for idx, bus_y in enumerate(self._bus_ys):
            if top <= bus_y <= bottom:
                self._selected_buses.add(idx)
        self._sync_selection_state()

    def _start_multi_drag(self, cx: float, cy: float) -> None:
        """
        NAME
            _start_multi_drag - Begin dragging all selected nodes/callouts together.
        """
        node_start: Dict[int, Tuple[float, int, int, float, float]] = {}
        for node in self._nodes:
            if node.key in self._selected_nodes:
                start_center = self._node_center_y_unscaled(node)
                node_start[node.key] = (node.x, node.bus_index, node.row, node.scale, start_center)
        self._push_undo()
        self._drag_undo_pending = True
        self._multi_drag = {
            "start": (cx, cy),
            "nodes": node_start,
            "last": (cx, cy),
            "anchor": min(self._selected_nodes) if self._selected_nodes else None,
        }
    def _redraw_canvas(self) -> None:
        """
        NAME
            _redraw_canvas - Repaint the bus line and node boxes.
        """
        self.canvas.delete("all")
        self._node_bounds = {}
        self._bus_ys = []
        width = max(self.canvas.winfo_width(), 1)
        height = max(self.canvas.winfo_height(), 1)
        scale = self._zoom
        max_node_x = max((n.x for n in self._nodes), default=0.0)
        if len(self._bus_lefts) < len(self._bus_offsets):
            self._bus_lefts.extend([40.0] * (len(self._bus_offsets) - len(self._bus_lefts)))
        if len(self._bus_rights) < len(self._bus_offsets):
            self._bus_rights.extend([max_node_x + 200.0] * (len(self._bus_offsets) - len(self._bus_rights)))
        if len(self._bus_lefts) > len(self._bus_offsets):
            self._bus_lefts = self._bus_lefts[: len(self._bus_offsets)]
        if len(self._bus_rights) > len(self._bus_offsets):
            self._bus_rights = self._bus_rights[: len(self._bus_offsets)]
        eff_lefts = list(self._bus_lefts)
        eff_rights = list(self._bus_rights)
        for idx in range(len(eff_lefts) - 1):
            if idx % 2 == 0:
                shared = eff_rights[idx]
                eff_rights[idx + 1] = shared
            else:
                shared = eff_lefts[idx]
                eff_lefts[idx + 1] = shared
        min_left = min(eff_lefts, default=40.0)
        max_right = max(eff_rights, default=max_node_x + 200.0)
        total_width = max(
            width,
            int((self._layout_width or max_right) * scale),
            int((max_right) * scale),
        )
        base_y = height * 0.5 + self._pan_y
        if (
            self._details_layout_shift
            and self._last_base_y is not None
            and (self._last_canvas_height is None or height != self._last_canvas_height)
        ):
            self._details_layout_shift = False
        self._last_base_y = base_y
        self._last_canvas_height = height
        bus_ys = [base_y + offset * scale for offset in self._bus_offsets]
        box_w = self._box_w * scale
        box_h = self._box_h * scale
        span = box_h + 60 * scale
        min_y = min((y - span for y in bus_ys), default=0.0)
        max_y = max((y + span for y in bus_ys), default=height)
        for node in self._nodes:
            if not bus_ys:
                break
            bus_index = min(max(node.bus_index, 0), max(len(bus_ys) - 1, 0))
            bus_y = bus_ys[bus_index]
            _, node_box_h = self._node_box_dims(node, scale)
            y0, y1 = self._node_box_y(node, bus_y, node_box_h, scale)
            min_y = min(min_y, y0)
            max_y = max(max_y, y1)
        margin = 20.0
        total_height = max(height, int(max_y - min_y + margin * 2))
        self.canvas.configure(scrollregion=(0, min_y - margin, total_width, max_y + margin))
        self._draw_state = {
            "bus_ys": bus_ys,
            "scale": scale,
            "bus_lefts": eff_lefts,
            "bus_rights": eff_rights,
        }
        x_left = min_left * scale
        x_right = max_right * scale
        turn_radius = max(8.0, 18 * scale)
        self._bus_ys = list(bus_ys)
        for idx, bus_y in enumerate(bus_ys):
            bus_color = "#1f6feb" if idx in self._selected_buses else "#444444"
            bus_width = 5 if idx in self._selected_buses else 4
            seg_left = eff_lefts[idx] * scale
            seg_right = eff_rights[idx] * scale
            if idx % 2 == 0:
                start_x, end_x = seg_left, seg_right
            else:
                start_x, end_x = seg_right, seg_left
            self.canvas.create_line(
                start_x, bus_y, end_x, bus_y, width=bus_width, fill=bus_color
            )
            if idx + 1 < len(bus_ys):
                next_y = bus_ys[idx + 1]
                connector_x = end_x
                offset = turn_radius if idx % 2 == 0 else -turn_radius
                self.canvas.create_line(
                    connector_x,
                    bus_y,
                    connector_x + offset,
                    bus_y + turn_radius,
                    connector_x + offset,
                    next_y - turn_radius,
                    connector_x,
                    next_y,
                    width=bus_width,
                    fill="#444444",
                    smooth=True,
                    splinesteps=12,
                )

        dup_keys: set[Tuple[str, str, int]] = set()
        key_counts: Dict[Tuple[str, str, int], int] = {}
        numeric_counts: Dict[int, int] = {}
        for node in self._device_nodes():
            key = self._dup_key_for_node(node)
            if key is None:
                continue
            key_counts[key] = key_counts.get(key, 0) + 1
            numeric_counts[key[2]] = numeric_counts.get(key[2], 0) + 1
        dup_keys = {key for key, count in key_counts.items() if count > 1}
        warn_ids = {can_id for can_id, count in numeric_counts.items() if count > 1}
        for node in self._device_nodes():
            node_x = min(max(node.x * scale, x_left + 20), x_right - 20)
            bus_index = min(max(node.bus_index, 0), max(len(bus_ys) - 1, 0))
            node.bus_index = bus_index
            bus_y = bus_ys[bus_index] if bus_ys else base_y
            node_scale = max(0.6, min(2.0, node.scale))
            node_box_w = box_w * node_scale
            node_box_h = box_h * node_scale
            seg_left = eff_lefts[bus_index] * scale
            seg_right = eff_rights[bus_index] * scale
            node_x = min(max(node.x * scale, seg_left + 20), seg_right - 20)
            x0 = node_x - node_box_w / 2
            x1 = node_x + node_box_w / 2
            if node.key in self._drag_free_y:
                center_y = base_y + self._drag_free_y[node.key] * scale
                y0 = center_y - node_box_h / 2
                y1 = center_y + node_box_h / 2
                line_y = y0 if center_y > bus_y else y1
                self.canvas.create_line(node_x, bus_y, node_x, line_y, width=2, fill="#444444")
            else:
                if node.free_y is not None:
                    center_y = base_y + self._node_center_y_unscaled(node) * scale
                    y0 = center_y - node_box_h / 2
                    y1 = center_y + node_box_h / 2
                    line_y = y0 if center_y > bus_y else y1
                    self.canvas.create_line(node_x, bus_y, node_x, line_y, width=2, fill="#444444")
                else:
                    if node.row == 1:
                        y0 = bus_y + 30 * scale
                        y1 = y0 + node_box_h
                        self.canvas.create_line(node_x, bus_y, node_x, y0, width=2, fill="#444444")
                    else:
                        y1 = bus_y - 30 * scale
                        y0 = y1 - node_box_h
                        self.canvas.create_line(node_x, y1, node_x, bus_y, width=2, fill="#444444")
            outline = "#1f6feb" if node.key in self._selected_nodes else "#222222"
            shape_kind = self._shape_kind_for_node(node)
            fill = self._fill_color_for_node(node)
            text_color = self._text_color_for_fill(fill)
            shape_ids = self._draw_device_shape_on(
                self.canvas, x0, y0, x1, y1, shape_kind, fill=fill, outline=outline, width=2
            )
            text = node.display_text()
            font_size = self._fit_font_size(
                text, node_box_w - 10, node_box_h - 10, int(9 * scale * node_scale)
            )
            text = self.canvas.create_text(
                node_x,
                (y0 + y1) / 2,
                text=text,
                font=("Segoe UI", font_size),
                fill=text_color,
                justify="center",
                width=max(40, int(node_box_w - 10)),
            )
            self._node_bounds[node.key] = (x0, y0, x1, y1)
            for shape_id in shape_ids:
                self.canvas.addtag_withtag(f"node_{node.key}", shape_id)
            self.canvas.addtag_withtag(f"node_{node.key}", text)
            dup_key = self._dup_key_for_node(node)
            if dup_key in dup_keys:
                badge = self._draw_error_badge(x1 - 12, y0 + 12)
                for badge_id in badge:
                    self.canvas.addtag_withtag(f"node_{node.key}", badge_id)
            elif dup_key and dup_key[2] in warn_ids:
                badge = self._draw_warning_badge(x1 - 12, y0 + 12)
                for badge_id in badge:
                    self.canvas.addtag_withtag(f"node_{node.key}", badge_id)

        node_centers = {}
        for n in self._device_nodes():
            seg_left = eff_lefts[n.bus_index] * scale
            seg_right = eff_rights[n.bus_index] * scale
            node_centers[n.key] = (
                min(max(n.x * scale, seg_left + 20), seg_right - 20),
                bus_ys[n.bus_index] if bus_ys else base_y,
            )
        for callout in self._callout_nodes():
            cx = callout.x * scale
            bus_index = min(max(callout.bus_index, 0), max(len(bus_ys) - 1, 0))
            bus_y = bus_ys[bus_index] if bus_ys else base_y
            box_w, box_h = self._node_box_dims(callout, scale)
            if callout.key in self._drag_free_y:
                cy = base_y + self._drag_free_y[callout.key] * scale
                y0 = cy - box_h / 2
                y1 = cy + box_h / 2
            else:
                if callout.free_y is not None:
                    cy = base_y + self._node_center_y_unscaled(callout) * scale
                    y0 = cy - box_h / 2
                    y1 = cy + box_h / 2
                else:
                    y0, y1 = self._node_box_y(callout, bus_y, box_h, scale)
                    cy = (y0 + y1) / 2.0
            x0 = cx - box_w / 2
            x1 = cx + box_w / 2
            if (
                callout.callout_target_type == "node"
                and callout.callout_target_node_key in node_centers
            ):
                tx, ty = node_centers[callout.callout_target_node_key]
            else:
                bus_index = min(
                    max(callout.callout_target_bus, 0), max(len(bus_ys) - 1, 0)
                )
                ty = bus_ys[bus_index] if bus_ys else base_y
                tx = cx
            self.canvas.create_line(cx, cy, tx, ty, width=2, fill="#666666")
            outline = "#1f6feb" if callout.key in self._selected_nodes else "#666666"
            rect = self.canvas.create_rectangle(
                x0, y0, x1, y1, fill="#fffbe6", outline=outline, width=2
            )
            text_id = self.canvas.create_text(
                cx,
                cy,
                text=callout.callout_text,
                font=("Segoe UI", max(8, int(9 * scale * max(0.6, min(2.0, callout.scale))))),
                justify="center",
                width=max(60, int(box_w - 10)),
            )
            self._node_bounds[callout.key] = (x0, y0, x1, y1)
            self.canvas.addtag_withtag(f"node_{callout.key}", rect)
            self.canvas.addtag_withtag(f"node_{callout.key}", text_id)

        if self._guide_x is not None and self._smart_guides_var.get():
            guide_x = self._guide_x * scale
            self.canvas.create_line(
                guide_x,
                min_y - margin,
                guide_x,
                max_y + margin,
                fill="#1f6feb",
                dash=(4, 4),
                width=1,
            )

        # Legend is optional via View -> Legend.

    def _shape_kind_for_node(self, node: Node) -> str:
        """
        NAME
            _shape_kind_for_node - Map node categories to a shape kind.
        """
        category = (node.category or "").lower()
        if category in ("neos", "neo550s", "flexes", "krakens", "falcons"):
            return "motor"
        if category in ("cancoders", "pigeon"):
            return "sensor"
        if category in ("pdh", "pdp"):
            return "power"
        if category in ("roborio",):
            return "controller"
        if category in ("candles",):
            return "misc"
        if category == GENERIC_CATEGORY:
            return "misc"
        return "misc"

    def _fill_color_for_node(self, node: Node) -> str:
        """
        NAME
            _fill_color_for_node - Resolve fill color based on manufacturer.
        """
        vendor = self._vendor_key_for_node(node)
        if not vendor:
            category = (node.category or "").lower()
            if category in ("neos", "neo550s", "flexes", "pdh"):
                vendor = "REV"
            elif category in ("krakens", "falcons", "cancoders", "candles", "pdp", "pigeon"):
                vendor = "CTRE"
            elif category in ("roborio",):
                vendor = "NI"
        palette = {
            "CTRE": "#b7e1b2",  # green
            "REV": "#ffd5a6",  # orange
            "KAUAILABS": "#bfe7ff",
            "PLAYINGWITHFUSION": "#c8f2c3",
            "ANDYMARK": "#c9d2ff",
            "NI": "#e7e7e7",
        }
        return palette.get(vendor, "#f7f7f7")

    def _outline_color_for_node(self, node: Node) -> str:
        """
        NAME
            _outline_color_for_node - Resolve outline color by manufacturer.
        """
        vendor = self._vendor_key_for_node(node)
        palette = {
            "CTRE": "#1d6b1a",
            "REV": "#b26200",
            "KAUAILABS": "#1c6ba8",
            "PLAYINGWITHFUSION": "#2f7a2f",
            "ANDYMARK": "#3b4aa0",
            "NI": "#6a6a6a",
        }
        return palette.get(vendor, "#222222")

    def _vendor_key_for_node(self, node: Node) -> str:
        """
        NAME
            _vendor_key_for_node - Normalize vendor key for a node.
        """
        vendor = (node.vendor or "").strip().upper().replace(" ", "")
        if vendor:
            return vendor
        category = (node.category or "").lower()
        if category in ("neos", "neo550s", "flexes", "pdh"):
            return "REV"
        if category in ("krakens", "falcons", "cancoders", "candles", "pdp", "pigeon"):
            return "CTRE"
        if category in ("roborio",):
            return "NI"
        return ""

    def _device_type_key_for_node(self, node: Node) -> str:
        """
        NAME
            _device_type_key_for_node - Normalize device type key for a node.
        """
        category = (node.category or "").lower()
        if category in ("neos", "neo550s", "flexes", "krakens", "falcons"):
            return "MOTORCONTROLLER"
        if category in ("cancoders",):
            return "ENCODER"
        if category in ("pigeon",):
            return "GYROSENSOR"
        if category in ("pdh", "pdp"):
            return "POWERDISTRIBUTIONMODULE"
        if category in ("candles",):
            return "MISCELLANEOUS"
        if category in ("roborio",):
            return "ROBOTCONTROLLER"
        if category == GENERIC_CATEGORY:
            return (node.device_type or "").strip().upper().replace(" ", "") or "UNKNOWN"
        return "UNKNOWN"

    def _dup_key_for_node(self, node: Node) -> Optional[Tuple[str, str, int]]:
        """
        NAME
            _dup_key_for_node - Build a duplicate-detection key.
        """
        if not isinstance(node.can_id, int) or node.can_id < 0:
            return None
        vendor = self._vendor_key_for_node(node) or "UNKNOWN"
        dev_type = self._device_type_key_for_node(node)
        return (vendor, dev_type, int(node.can_id))

    @staticmethod
    def _text_color_for_fill(fill: str) -> str:
        """
        NAME
            _text_color_for_fill - Choose readable text color for a fill.
        """
        if not fill.startswith("#") or len(fill) != 7:
            return "#111111"
        try:
            r = int(fill[1:3], 16)
            g = int(fill[3:5], 16)
            b = int(fill[5:7], 16)
        except ValueError:
            return "#111111"
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        return "#111111" if luminance > 150 else "#ffffff"

    def _draw_legend(self, x: float, y: float) -> None:
        """
        NAME
            _draw_legend - Draw a shape/color legend in the top-left.
        """
        padding = 8
        line_h = 16
        shape_h = 14
        shape_w = 24
        text_x = x + padding + shape_w + 8
        legend_items = [
            ("Motors", "motor"),
            ("Sensors", "sensor"),
            ("Power", "power"),
            ("Controller", "controller"),
            ("Misc", "misc"),
        ]
        color_items = [
            ("CTRE", "CTRE"),
            ("REV", "REV"),
            ("KauaiLabs", "KAUAILABS"),
            ("PlayingWithFusion", "PLAYINGWITHFUSION"),
            ("AndyMark", "ANDYMARK"),
            ("NI", "NI"),
        ]
        height = padding * 2 + line_h * (len(legend_items) + len(color_items) + 2)
        width = 220
        self.canvas.create_rectangle(
            x,
            y,
            x + width,
            y + height,
            fill="#ffffff",
            outline="#d0d0d0",
            width=1,
        )
        cy = y + padding
        self.canvas.create_text(
            x + padding,
            cy,
            text="Legend",
            anchor="nw",
            font=("Segoe UI", 9, "bold"),
            fill="#333333",
        )
        cy += line_h
        for label, kind in legend_items:
            sx0 = x + padding
            sy0 = cy + 2
            sx1 = sx0 + shape_w
            sy1 = sy0 + shape_h
            self._draw_device_shape(sx0, sy0, sx1, sy1, kind, "#f7f7f7", "#555555", 1)
            self.canvas.create_text(
                text_x,
                cy,
                text=label,
                anchor="nw",
                font=("Segoe UI", 9),
                fill="#333333",
            )
            cy += line_h
        cy += 4
        for label, vendor in color_items:
            sx0 = x + padding
            sy0 = cy + 2
            sx1 = sx0 + shape_w
            sy1 = sy0 + shape_h
            fill = self._fill_color_for_vendor(vendor)
            outline = self._outline_color_for_vendor(vendor)
            self.canvas.create_rectangle(
                sx0, sy0, sx1, sy1, fill=fill, outline=outline, width=1
            )
            self.canvas.create_text(
                text_x,
                cy,
                text=label,
                anchor="nw",
                font=("Segoe UI", 9),
                fill="#333333",
            )
            cy += line_h

    def _draw_error_badge(self, cx: float, cy: float) -> List[int]:
        """
        NAME
            _draw_error_badge - Draw a red exclamation badge.
        """
        r = 7
        badge = self.canvas.create_oval(
            cx - r,
            cy - r,
            cx + r,
            cy + r,
            fill="#cc0000",
            outline="#aa0000",
            width=1,
        )
        text = self.canvas.create_text(
            cx,
            cy - 0.5,
            text="!",
            font=("Segoe UI", 9, "bold"),
            fill="#ffffff",
        )
        return [badge, text]

    def _draw_warning_badge(self, cx: float, cy: float) -> List[int]:
        """
        NAME
            _draw_warning_badge - Draw a yellow warning triangle badge.
        """
        r = 8
        points = [
            cx,
            cy - r,
            cx + r,
            cy + r,
            cx - r,
            cy + r,
        ]
        badge = self.canvas.create_polygon(
            points,
            fill="#f5c542",
            outline="#c28b00",
            width=1,
        )
        text = self.canvas.create_text(
            cx,
            cy + 1,
            text="!",
            font=("Segoe UI", 9, "bold"),
            fill="#5a3b00",
        )
        return [badge, text]

    def _show_legend_dialog(self) -> None:
        """
        NAME
            _show_legend_dialog - Show a legend popup dialog.
        """
        if getattr(self, "_legend_window", None):
            try:
                self._legend_window.lift()
                return
            except tk.TclError:
                self._legend_window = None
        dialog = tk.Toplevel(self)
        self._legend_window = dialog
        dialog.title("Legend")
        dialog.resizable(False, False)
        dialog.transient(self)

        canvas = tk.Canvas(dialog, width=260, height=280, background="#ffffff")
        canvas.pack(padx=8, pady=8)

        def _draw_on(canvas_obj: tk.Canvas) -> None:
            padding = 8
            line_h = 18
            shape_h = 14
            shape_w = 24
            text_x = padding + shape_w + 8
            legend_items = [
                ("Motors", "motor"),
                ("Sensors", "sensor"),
                ("Power", "power"),
                ("Controller", "controller"),
                ("Misc", "misc"),
            ]
            color_items = [
                ("CTRE", "CTRE"),
                ("REV", "REV"),
                ("KauaiLabs", "KAUAILABS"),
                ("PlayingWithFusion", "PLAYINGWITHFUSION"),
                ("AndyMark", "ANDYMARK"),
                ("NI", "NI"),
            ]
            cy = padding
            canvas_obj.create_text(
                padding,
                cy,
                text="Legend",
                anchor="nw",
                font=("Segoe UI", 10, "bold"),
                fill="#333333",
            )
            cy += line_h
            for label, kind in legend_items:
                sx0 = padding
                sy0 = cy + 2
                sx1 = sx0 + shape_w
                sy1 = sy0 + shape_h
                self._draw_device_shape_on(
                    canvas_obj, sx0, sy0, sx1, sy1, kind, "#f7f7f7", "#555555", 1
                )
                canvas_obj.create_text(
                    text_x,
                    cy,
                    text=label,
                    anchor="nw",
                    font=("Segoe UI", 9),
                    fill="#333333",
                )
                cy += line_h
            cy += 6
            for label, vendor in color_items:
                sx0 = padding
                sy0 = cy + 2
                sx1 = sx0 + shape_w
                sy1 = sy0 + shape_h
                fill = self._fill_color_for_vendor(vendor)
                outline = self._outline_color_for_vendor(vendor)
                canvas_obj.create_rectangle(
                    sx0, sy0, sx1, sy1, fill=fill, outline=outline, width=1
                )
                canvas_obj.create_text(
                    text_x,
                    cy,
                    text=label,
                    anchor="nw",
                    font=("Segoe UI", 9),
                    fill="#333333",
                )
                cy += line_h

        _draw_on(canvas)

        button_row = ttk.Frame(dialog)
        button_row.pack(pady=(0, 8))
        ttk.Button(button_row, text="Close", command=dialog.destroy).pack()
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        dialog.bind(
            "<Destroy>",
            lambda _e: setattr(self, "_legend_window", None),
        )

    def _help_topics(self) -> Dict[str, str]:
        """
        NAME
            _help_topics - Build help topic text blocks.
        """
        return {
            "Overview": (
                "Purpose: Sketch CAN nodes on a shared bus and export a bringup profile.\n"
                "\n"
                "Quick steps:\n"
                "1) Add nodes and labels.\n"
                "2) Drag nodes onto bus segments.\n"
                "3) Save profile or export.\n"
            ),
            "Keyboard Shortcuts": (
                "Purpose: Speed up common actions.\n"
                "\n"
                "Selection:\n"
                "- Ctrl+A: Select all nodes (devices + callouts).\n"
                "- Shift+Click: Multi-select nodes or buses.\n"
                "\n"
                "Edit:\n"
                "- Ctrl+C: Copy selection.\n"
                "- Ctrl+D: Duplicate selection.\n"
                "- Ctrl+V: Paste.\n"
                "- Delete / Backspace: Remove selected nodes/callouts.\n"
                "- Ctrl+Z: Undo.\n"
                "\n"
                "Layout:\n"
                "- Ctrl+L: Tidy selection within bus bounds.\n"
                "- Ctrl+Shift+L: Reset layout (per-bus even spacing).\n"
                "- Layout -> Tidy All: Align all buses into shared columns.\n"
                "\n"
                "View:\n"
                "- Ctrl+0: Reset zoom.\n"
                "- Ctrl++ / Ctrl+=: Zoom in.\n"
                "- Ctrl+- / Ctrl+_: Zoom out.\n"
                "- Ctrl+MouseWheel: Zoom.\n"
                "- Ctrl+G: Toggle snap-to-grid.\n"
                "- Ctrl+Shift+G: Toggle smart guides.\n"
                "\n"
                "Save:\n"
                "- Ctrl+S: Save to deploy.\n"
            ),
            "Layout Tips": (
                "Purpose: Keep diagrams tidy and readable.\n"
                "\n"
                "- Use Snap to Grid for consistent spacing.\n"
                "- Use Smart Guides to align nodes on a bus segment.\n"
                "- Tidy Selection aligns selected nodes into shared columns.\n"
                "- Reset Layout preserves bus/row and evens per-bus spacing.\n"
                "- Align/Distribute tools are under the Layout menu.\n"
            ),
            "Bus Segments": (
                "Purpose: Understand bus segment editing.\n"
                "\n"
                "- Add Bus, then click to place a new segment.\n"
                "- Drag a bus line to move it; nodes follow.\n"
                "- Drag the curved end of a segment to resize it.\n"
            ),
            "Profiles & Export": (
                "Purpose: Save or export diagram data.\n"
                "\n"
                "- Save to Deploy writes to src/main/deploy/bringup_profiles.json.\n"
                "- Save Profile As... exports a single profile JSON.\n"
                "- Export PDF requires reportlab.\n"
            ),
        }

    def _show_help_dialog(self) -> None:
        """
        NAME
            _show_help_dialog - Show the help topics dialog.
        """
        if getattr(self, "_help_window", None):
            try:
                self._help_window.lift()
                return
            except tk.TclError:
                self._help_window = None
        dialog = tk.Toplevel(self)
        self._help_window = dialog
        dialog.title("Help")
        dialog.geometry("640x420")
        dialog.minsize(520, 320)
        dialog.transient(self)

        container = ttk.Frame(dialog, padding=8)
        container.pack(fill="both", expand=True)

        left = ttk.Frame(container)
        left.pack(side="left", fill="y")
        right = ttk.Frame(container)
        right.pack(side="right", fill="both", expand=True)

        ttk.Label(left, text="Topics").pack(anchor="w")
        topics = list(self._help_topics().keys())
        listbox = tk.Listbox(left, height=12, exportselection=False)
        for item in topics:
            listbox.insert("end", item)
        listbox.pack(fill="y", expand=True, pady=(4, 0))

        text = tk.Text(right, wrap="word", height=12)
        text.pack(fill="both", expand=True)
        text.configure(state="disabled")

        def _set_topic(name: str) -> None:
            content = self._help_topics().get(name, "")
            text.configure(state="normal")
            text.delete("1.0", "end")
            text.insert("1.0", content)
            text.configure(state="disabled")

        def _on_select(_event: tk.Event) -> None:
            selection = listbox.curselection()
            if not selection:
                return
            _set_topic(topics[selection[0]])

        listbox.bind("<<ListboxSelect>>", _on_select)
        if topics:
            listbox.selection_set(0)
            _set_topic(topics[0])

    def _show_shortcuts_dialog(self) -> None:
        """
        NAME
            _show_shortcuts_dialog - Show keyboard shortcuts only.
        """
        text = self._help_topics().get("Keyboard Shortcuts", "")
        messagebox.showinfo("Keyboard Shortcuts", text)

    def _fill_color_for_vendor(self, vendor: str) -> str:
        """
        NAME
            _fill_color_for_vendor - Resolve fill color for a vendor key.
        """
        palette = {
            "CTRE": "#b7e1b2",
            "REV": "#ffd5a6",
            "KAUAILABS": "#bfe7ff",
            "PLAYINGWITHFUSION": "#c8f2c3",
            "ANDYMARK": "#c9d2ff",
            "NI": "#e7e7e7",
        }
        return palette.get(vendor, "#f7f7f7")

    def _outline_color_for_vendor(self, vendor: str) -> str:
        """
        NAME
            _outline_color_for_vendor - Resolve outline color for a vendor key.
        """
        palette = {
            "CTRE": "#1d6b1a",
            "REV": "#b26200",
            "KAUAILABS": "#1c6ba8",
            "PLAYINGWITHFUSION": "#2f7a2f",
            "ANDYMARK": "#3b4aa0",
            "NI": "#6a6a6a",
        }
        return palette.get(vendor, "#222222")

    def _draw_device_shape_on(
        self,
        canvas: tk.Canvas,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        kind: str,
        fill: str,
        outline: str,
        width: int,
    ) -> List[int]:
        """
        NAME
            _draw_device_shape - Draw a device shape for the given kind.

        RETURNS
            List of canvas item ids.
        """
        if kind == "motor":
            return [self._draw_chamfer_rect(canvas, x0, y0, x1, y1, fill, outline, width)]
        if kind == "sensor":
            return [self._draw_hexagon(canvas, x0, y0, x1, y1, fill, outline, width)]
        if kind == "power":
            return [self._draw_diamond(canvas, x0, y0, x1, y1, fill, outline, width)]
        if kind == "controller":
            return [self._draw_tabbed_rect(canvas, x0, y0, x1, y1, fill, outline, width)]
        return [canvas.create_rectangle(x0, y0, x1, y1, fill=fill, outline=outline, width=width)]

    def _draw_chamfer_rect(
        self,
        canvas: tk.Canvas,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        fill: str,
        outline: str,
        width: int,
    ) -> int:
        """
        NAME
            _draw_chamfer_rect - Draw a rectangle with chamfered corners.
        """
        inset = max(6.0, min(14.0, (x1 - x0) * 0.08, (y1 - y0) * 0.25))
        points = [
            x0 + inset,
            y0,
            x1 - inset,
            y0,
            x1,
            y0 + inset,
            x1,
            y1 - inset,
            x1 - inset,
            y1,
            x0 + inset,
            y1,
            x0,
            y1 - inset,
            x0,
            y0 + inset,
        ]
        return canvas.create_polygon(
            points, fill=fill, outline=outline, width=width, joinstyle="round"
        )

    def _draw_hexagon(
        self,
        canvas: tk.Canvas,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        fill: str,
        outline: str,
        width: int,
    ) -> int:
        """
        NAME
            _draw_hexagon - Draw a horizontally stretched hexagon.
        """
        inset = max(8.0, min(18.0, (x1 - x0) * 0.18))
        yc = (y0 + y1) / 2.0
        points = [
            x0 + inset,
            y0,
            x1 - inset,
            y0,
            x1,
            yc,
            x1 - inset,
            y1,
            x0 + inset,
            y1,
            x0,
            yc,
        ]
        return canvas.create_polygon(
            points, fill=fill, outline=outline, width=width, joinstyle="round"
        )

    def _draw_diamond(
        self,
        canvas: tk.Canvas,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        fill: str,
        outline: str,
        width: int,
    ) -> int:
        """
        NAME
            _draw_diamond - Draw a diamond shape.
        """
        xc = (x0 + x1) / 2.0
        yc = (y0 + y1) / 2.0
        points = [xc, y0, x1, yc, xc, y1, x0, yc]
        return canvas.create_polygon(
            points, fill=fill, outline=outline, width=width, joinstyle="round"
        )

    def _draw_tabbed_rect(
        self,
        canvas: tk.Canvas,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        fill: str,
        outline: str,
        width: int,
    ) -> int:
        """
        NAME
            _draw_tabbed_rect - Draw a rectangle with a top-center tab.
        """
        tab_w = max(18.0, min(42.0, (x1 - x0) * 0.35))
        tab_h = max(10.0, min(18.0, (y1 - y0) * 0.25))
        xc = (x0 + x1) / 2.0
        points = [
            x0,
            y1,
            x1,
            y1,
            x1,
            y0 + tab_h,
            xc + tab_w / 2.0,
            y0 + tab_h,
            xc + tab_w / 2.0,
            y0,
            xc - tab_w / 2.0,
            y0,
            xc - tab_w / 2.0,
            y0 + tab_h,
            x0,
            y0 + tab_h,
        ]
        return canvas.create_polygon(
            points, fill=fill, outline=outline, width=width, joinstyle="round"
        )

    def _on_canvas_press(self, event: tk.Event) -> None:
        """
        NAME
            _on_canvas_press - Begin dragging a node if clicked.
        """
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        self.canvas.focus_set()
        self._clear_guides()
        if self._selection_rect is not None:
            self.canvas.delete(self._selection_rect)
            self._selection_rect = None
            self._selection_start = None
        if self._add_bus_mode:
            self._add_bus_at(cy)
            self._add_bus_mode = False
            return
        items = self.canvas.find_overlapping(cx, cy, cx, cy)
        item = items[-1] if items else None
        tags = self.canvas.gettags(item) if item else ()
        key = self._tag_to_key(tags)
        total_selected = len(self._selected_nodes)
        if self._shift_held(event):
            if key is not None:
                self._toggle_node_selection(key)
                return
            bus_index = self._bus_hit_test(cy)
            if bus_index is not None:
                self._toggle_bus_selection(bus_index)
                return
            self._selection_start = (cx, cy)
            self._selection_rect = self.canvas.create_rectangle(
                cx, cy, cx, cy, outline="#1f6feb", dash=(4, 2)
            )
            return
        if key is None:
            # Check if we clicked near a bus line to drag it.
            bus_index = self._bus_hit_test(cy)
            if bus_index is not None:
                end = self._bus_end_hit_test(bus_index, cx, cy)
                if end:
                    self._push_undo()
                    self._drag_undo_pending = True
                    self._bus_resize = (
                        bus_index,
                        end,
                        self._bus_lefts[bus_index],
                        self._bus_rights[bus_index],
                        cx,
                    )
                    return
                self._selected_buses = {bus_index}
                self._selected_nodes = set()
                self._sync_selection_state()
                self._push_undo()
                bus_ys = list(self._draw_state.get("bus_ys", []))
                bus_y = bus_ys[bus_index] if bus_ys else cy
                self._bus_drag = (bus_index, bus_y, self._bus_offsets[bus_index])
            else:
                self._pan_drag = (cy, self._pan_y)
            if bus_index is None:
                self._clear_selection()
            return
        if key in self._selected_nodes and total_selected > 1:
            self._start_multi_drag(cx, cy)
        else:
            self._set_single_node_selection(key)
            self._push_undo()
            self._drag_undo_pending = True
            self._drag_state = (key, cx, cy)

    def _on_canvas_drag(self, event: tk.Event) -> None:
        """
        NAME
            _on_canvas_drag - Drag the selected node horizontally.
        """
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        if not self._dragging_active:
            self._dragging_active = True
            if hasattr(self, "_node_details_panel"):
                self._preserve_canvas_view(self._node_details_panel.pack_forget)
        if self._selection_start is not None and self._selection_rect is not None:
            x0, y0 = self._selection_start
            self.canvas.coords(self._selection_rect, x0, y0, cx, cy)
            return
        if self._multi_drag is not None:
            start_cx, start_cy = self._multi_drag.get("start", (cx, cy))
            dx = cx - start_cx
            dy = cy - start_cy
            scale = max(self._zoom, 0.01)
            nodes_start = self._multi_drag.get("nodes", {})
            base_y = max(self.canvas.winfo_height(), 1) * 0.5 + self._pan_y
            dx_unscaled = dx / scale
            anchor_key = self._multi_drag.get("anchor")
            if anchor_key in nodes_start:
                anchor_start_x = nodes_start[anchor_key][0]
                if self._snap_to_grid_var.get():
                    dx_unscaled = self._snap_value(anchor_start_x + dx_unscaled) - anchor_start_x
                anchor_node = next((n for n in self._nodes if n.key == anchor_key), None)
                if anchor_node is not None:
                    candidate_x = anchor_start_x + dx_unscaled
                    candidate_x, guide_x = self._apply_smart_guides(
                        anchor_node, candidate_x, self._selected_nodes
                    )
                    dx_unscaled = candidate_x - anchor_start_x
                    self._guide_x = guide_x
                    self._guide_bus = anchor_node.bus_index if guide_x is not None else None
                else:
                    self._clear_guides()
            else:
                self._clear_guides()
            for node in self._nodes:
                if node.key not in nodes_start:
                    continue
                start_x, start_bus, start_row, start_scale, start_center = nodes_start[node.key]
                node.x = start_x + dx_unscaled
                self._drag_free_y[node.key] = start_center + dy / scale
            self._redraw_canvas()
            return
        if self._pan_drag is not None:
            start_y, start_pan = self._pan_drag
            dy = cy - start_y
            height = max(self.canvas.winfo_height(), 1)
            max_shift = height * 0.25
            self._pan_y = max(-max_shift, min(max_shift, start_pan + dy))
            self._dirty = True
            self._redraw_canvas()
            return
        if self._bus_drag is not None:
            bus_index, start_bus_y, start_offset = self._bus_drag
            scale = max(self._zoom, 0.01)
            dy_canvas = cy - start_bus_y
            delta = dy_canvas / scale
            self._bus_offsets[bus_index] = start_offset + delta
            self._redraw_canvas()
            return
        if self._bus_resize is not None:
            bus_index, end, start_left, start_right, start_cx = self._bus_resize
            scale = max(self._zoom, 0.01)
            dx = (cx - start_cx) / scale
            left = start_left
            right = start_right
            min_len = 120.0

            is_even = bus_index % 2 == 0
            connector_with_next = (end == "right" and is_even) or (end == "left" and not is_even)
            connector_with_prev = (end == "left" and is_even) or (end == "right" and not is_even)

            new_pos = (start_left + dx) if end == "left" else (start_right + dx)
            min_allowed = float("-inf")
            max_allowed = float("inf")

            # Clamp for the current segment.
            if end == "left":
                max_allowed = min(max_allowed, right - min_len)
            else:
                min_allowed = max(min_allowed, left + min_len)

            # If we are dragging a connector, also clamp against the neighbor segment.
            if connector_with_next and bus_index + 1 < len(self._bus_offsets):
                next_left = self._bus_lefts[bus_index + 1]
                next_right = self._bus_rights[bus_index + 1]
                if (bus_index + 1) % 2 == 0:
                    # Next segment starts on the left.
                    max_allowed = min(max_allowed, next_right - min_len)
                else:
                    # Next segment starts on the right.
                    min_allowed = max(min_allowed, next_left + min_len)
            if connector_with_prev and bus_index - 1 >= 0:
                prev_left = self._bus_lefts[bus_index - 1]
                prev_right = self._bus_rights[bus_index - 1]
                if (bus_index - 1) % 2 == 0:
                    # Previous segment ends on the right.
                    min_allowed = max(min_allowed, prev_left + min_len)
                else:
                    # Previous segment ends on the left.
                    max_allowed = min(max_allowed, prev_right - min_len)

            if min_allowed != float("-inf") or max_allowed != float("inf"):
                new_pos = max(min_allowed, min(max_allowed, new_pos))

            if end == "left":
                left = new_pos
            else:
                right = new_pos

            # Apply to neighbors when dragging a connector end.
            if connector_with_next and bus_index + 1 < len(self._bus_offsets):
                if (bus_index + 1) % 2 == 0:
                    self._bus_lefts[bus_index + 1] = new_pos
                else:
                    self._bus_rights[bus_index + 1] = new_pos
            if connector_with_prev and bus_index - 1 >= 0:
                if (bus_index - 1) % 2 == 0:
                    self._bus_rights[bus_index - 1] = new_pos
                else:
                    self._bus_lefts[bus_index - 1] = new_pos

            self._bus_lefts[bus_index] = left
            self._bus_rights[bus_index] = right
            self._layout_width = max(self._layout_width, right + 200)
            self._dirty = True
            self._redraw_canvas()
            return
        if not self._drag_state:
            return
        key, last_x, last_y = self._drag_state
        node = next((n for n in self._nodes if n.key == key), None)
        if node is None:
            return
        dx = cx - last_x
        dy = cy - last_y
        scale = max(self._zoom, 0.01)
        candidate_x = node.x + dx / scale
        if self._snap_to_grid_var.get():
            candidate_x = self._snap_value(candidate_x)
        candidate_x, guide_x = self._apply_smart_guides(node, candidate_x, self._selected_nodes)
        node.x = candidate_x
        self._guide_x = guide_x
        self._guide_bus = node.bus_index if guide_x is not None else None
        self._layout_width = max(self._layout_width, node.x + 200)
        base_y = max(self.canvas.winfo_height(), 1) * 0.5 + self._pan_y
        self._drag_free_y[key] = (cy - base_y) / scale
        self._drag_state = (key, cx, cy)
        self._redraw_canvas()

    def _on_canvas_release(self, _event: tk.Event) -> None:
        """
        NAME
            _on_canvas_release - End drag operation.
        """
        if self._selection_rect is not None:
            x0, y0, x1, y1 = self.canvas.coords(self._selection_rect)
            self.canvas.delete(self._selection_rect)
            self._selection_rect = None
            self._selection_start = None
            self._apply_marquee_selection(x0, y0, x1, y1, additive=True)
            return
        if self._bus_drag is not None:
            self._reorder_buses_by_y()
        if self._drag_free_y:
            for key, free_y in list(self._drag_free_y.items()):
                node = next((n for n in self._nodes if n.key == key), None)
                if node is None:
                    continue
                node.bus_index, node.row = self._nearest_bus_and_row_from_offset(free_y)
                if self._bus_offsets:
                    bus_offset = self._bus_offsets[min(max(node.bus_index, 0), len(self._bus_offsets) - 1)]
                    node.free_y = free_y - bus_offset
                else:
                    node.free_y = free_y
            self._drag_free_y.clear()
        self._drag_state = None
        self._pan_drag = None
        self._bus_drag = None
        self._bus_resize = None
        self._multi_drag = None
        self._drag_undo_pending = False
        self._dragging_active = False
        self._clear_guides()
        if self._selected_key is not None:
            self._update_details_panel(self._get_selected_node())
        self._redraw_canvas()

    def _on_add_bus(self) -> None:
        """
        NAME
            _on_add_bus - Add a parallel bus segment connected to the first.
        """
        self._add_bus_mode = True
        messagebox.showinfo("Add Bus", "Click on the canvas where you want the new bus.")

    def _add_bus_at(self, cy: float) -> None:
        """
        NAME
            _add_bus_at - Add a bus segment at a specific canvas Y position.
        """
        height = max(self.canvas.winfo_height(), 1)
        base_y = height * 0.5 + self._pan_y
        offset = cy - base_y
        self._push_undo()
        if not self._bus_offsets:
            self._bus_offsets = [0.0]
        # Preserve insertion order; do not sort so existing buses don't shift.
        if offset not in self._bus_offsets:
            self._bus_offsets.append(offset)
            max_node_x = max((n.x for n in self._nodes), default=0.0)
            default_right = max(max_node_x + 200.0, 400.0)
            default_left = 40.0
            new_index = len(self._bus_offsets) - 1
            if new_index > 0 and new_index - 1 < len(self._bus_lefts):
                prev_index = new_index - 1
                if prev_index % 2 == 0:
                    connector_x = self._bus_rights[prev_index]
                else:
                    connector_x = self._bus_lefts[prev_index]
                if new_index % 2 == 0:
                    default_left = connector_x
                else:
                    default_right = connector_x
            self._bus_lefts.append(default_left)
            self._bus_rights.append(default_right)
        self._redraw_canvas()

    def _on_add_callout(self) -> None:
        """
        NAME
            _on_add_callout - Add a callout label attached to a bus or node.
        """
        dialog = CalloutDialog(
            self,
            "Add Callout",
            nodes=self._device_nodes(),
            bus_count=len(self._bus_offsets),
        )
        self.wait_window(dialog)
        if not dialog.result:
            return
        self._push_undo()
        data = dialog.result
        bus_index = int(data.get("target_bus", 0))
        row = 1
        x_pos = self._next_x_position()
        if str(data.get("target_type")) == "node":
            target_key = data.get("target_node_key")
            target_node = next((n for n in self._nodes if n.key == target_key), None)
            if target_node is not None:
                bus_index = target_node.bus_index
                row = target_node.row
                x_pos = target_node.x
        node = Node(
            key=self._next_key,
            category="callout",
            label=str(data["text"]),
            can_id=-1,
            node_type="callout",
            x=x_pos,
            row=row,
            bus_index=bus_index,
            scale=1.0,
            callout_text=str(data["text"]),
            callout_target_type=str(data["target_type"]),
            callout_target_bus=int(data.get("target_bus", 0)),
            callout_target_node_key=data.get("target_node_key"),
            callout_target_category=str(data.get("target_node_category", "")),
            callout_target_label=str(data.get("target_node_label", "")),
            callout_target_id=data.get("target_node_id"),
            callout_y=0.0,
        )
        node.callout_y = self._node_center_y_unscaled(node)
        self._next_key += 1
        self._nodes.append(node)
        self._set_single_node_selection(node.key)
        self._redraw_canvas()

    def _on_edit_callout(self) -> None:
        """
        NAME
            _on_edit_callout - Edit the selected callout target/text.
        """
        node = self._get_selected_node()
        if node is None or node.node_type != "callout":
            messagebox.showinfo("Edit Callout", "Select a callout to edit.")
            return
        dialog = CalloutDialog(
            self,
            "Edit Callout",
            nodes=self._device_nodes(),
            bus_count=len(self._bus_offsets),
            initial=node,
        )
        self.wait_window(dialog)
        if not dialog.result:
            return
        self._push_undo()
        data = dialog.result
        node.callout_text = str(data["text"])
        node.label = node.callout_text
        node.callout_target_type = str(data["target_type"])
        node.callout_target_bus = int(data.get("target_bus", 0))
        node.callout_target_node_key = data.get("target_node_key")
        node.callout_target_category = str(data.get("target_node_category", ""))
        node.callout_target_label = str(data.get("target_node_label", ""))
        node.callout_target_id = data.get("target_node_id")
        self._redraw_canvas()

    def _on_remove_callout(self) -> None:
        """
        NAME
            _on_remove_callout - Remove the selected callout.
        """
        node = self._get_selected_node()
        if node is None or node.node_type != "callout":
            messagebox.showinfo("Remove Callout", "Select a callout to remove.")
            return
        self._push_undo()
        self._nodes = [n for n in self._nodes if n.key != node.key]
        self._selected_key = None
        self._callout_scale_var.set("?")
        if hasattr(self, "_callout_details_panel"):
            self._preserve_canvas_view(self._callout_details_panel.pack_forget)
        self._redraw_canvas()

    def _on_copy(self) -> None:
        """
        NAME
            _on_copy - Copy the current selection into an internal clipboard.
        """
        if not (self._selected_nodes or self._selected_buses):
            messagebox.showinfo("Copy", "Select nodes or buses to copy.")
            return
        nodes = [n for n in self._nodes if n.key in self._selected_nodes]
        buses = sorted(self._selected_buses)
        self._clipboard = {
            "nodes": [self._node_snapshot(n) for n in nodes],
            "buses": [(idx, self._bus_offsets[idx]) for idx in buses if idx < len(self._bus_offsets)],
        }

    def _on_paste(self) -> None:
        """
        NAME
            _on_paste - Paste items from the internal clipboard.
        """
        if not self._clipboard:
            messagebox.showinfo("Paste", "Clipboard is empty.")
            return
        clip_nodes = list(self._clipboard.get("nodes", []))
        clip_buses = list(self._clipboard.get("buses", []))
        if not (clip_nodes or clip_buses):
            return

        existing_ids = {(n.category, n.can_id) for n in self._device_nodes()}
        pending_ids = {
            (n["category"], n["can_id"])
            for n in clip_nodes
            if n.get("node_type", "device") == "device"
        }
        if existing_ids.intersection(pending_ids):
            if not messagebox.askyesno(
                "CAN ID Conflict",
                "One or more pasted nodes share a category/CAN ID with existing nodes.\n\n"
                "Paste anyway?",
            ):
                return

        self._push_undo()
        delta = 40.0
        bus_map: Dict[int, int] = {}
        new_bus_indices: List[int] = []
        for old_index, offset in clip_buses:
            new_offset = offset + delta
            self._bus_offsets.append(new_offset)
            new_index = len(self._bus_offsets) - 1
            bus_map[old_index] = new_index
            new_bus_indices.append(new_index)

        new_nodes: List[int] = []
        node_map: Dict[int, int] = {}
        pending_callout_targets: List[Tuple[Node, Optional[int]]] = []
        for data in clip_nodes:
            new_key = self._next_key
            self._next_key += 1
            node_type = str(data.get("node_type", "device"))
            bus_index = int(data.get("bus_index", 0))
            if bus_index in bus_map:
                bus_index = bus_map[bus_index]
            node = Node(
                key=new_key,
                category=str(data.get("category", "callout")),
                label=str(data.get("label", "")),
                can_id=int(data.get("can_id", -1)),
                node_type=node_type,
                vendor=str(data.get("vendor", "")),
                device_type=str(data.get("device_type", "")),
                motor=str(data.get("motor", "")),
                limits=data.get("limits"),
                terminator=data.get("terminator"),
                x=float(data.get("x", 0.0)) + delta,
                row=int(data.get("row", 0)),
                bus_index=bus_index,
                scale=float(data.get("scale", 1.0)),
                callout_text=str(data.get("callout_text", "")),
                callout_target_type=str(data.get("callout_target_type", "node")),
                callout_target_bus=int(data.get("callout_target_bus", 0)),
                callout_target_node_key=data.get("callout_target_node_key"),
                callout_y=float(data.get("callout_y", 0.0)),
                free_y=data.get("free_y"),
            )
            if self._snap_to_grid_var.get():
                node.x = self._snap_value(node.x)
            if node.node_type == "callout":
                node.callout_y = self._node_center_y_unscaled(node)
                if node.callout_target_type == "bus" and node.callout_target_bus in bus_map:
                    node.callout_target_bus = bus_map[node.callout_target_bus]
                pending_callout_targets.append((node, node.callout_target_node_key))
            self._nodes.append(node)
            new_nodes.append(node.key)
            node_map[int(data.get("key", new_key))] = node.key

        for node, old_target in pending_callout_targets:
            if old_target in node_map:
                node.callout_target_node_key = node_map[old_target]

        if new_nodes:
            max_x = max((n.x for n in self._nodes if n.node_type == "device"), default=0.0)
            self._layout_width = max(self._layout_width, max_x + 200)

        self._selected_nodes = set(new_nodes)
        self._selected_buses = set(new_bus_indices)
        self._sync_selection_state()
        self._redraw_canvas()

    def _node_snapshot(self, node: Node) -> Dict[str, object]:
        """
        NAME
            _node_snapshot - Capture node data for clipboard transfer.
        """
        return {
            "key": node.key,
            "node_type": node.node_type,
            "category": node.category,
            "label": node.label,
            "can_id": node.can_id,
            "vendor": node.vendor,
            "device_type": node.device_type,
            "motor": node.motor,
            "limits": node.limits,
            "terminator": node.terminator,
            "x": node.x,
            "row": node.row,
            "bus_index": node.bus_index,
            "scale": node.scale,
            "callout_text": node.callout_text,
            "callout_target_type": node.callout_target_type,
            "callout_target_bus": node.callout_target_bus,
            "callout_target_node_key": node.callout_target_node_key,
            "callout_target_category": node.callout_target_category,
            "callout_target_label": node.callout_target_label,
            "callout_target_id": node.callout_target_id,
            "callout_y": self._node_center_y_unscaled(node)
            if node.node_type == "callout"
            else node.callout_y,
            "free_y": self._node_center_y_unscaled(node),
        }

    def _on_export_pdf(self) -> None:
        """
        NAME
            _on_export_pdf - Export the current diagram to a PDF file.
        """
        try:
            from reportlab.pdfgen import canvas as pdfcanvas  # type: ignore
            from reportlab.lib.colors import Color  # type: ignore
            from reportlab.pdfbase import pdfmetrics  # type: ignore
        except Exception:
            messagebox.showerror(
                "Missing Dependency",
                "PDF export requires the 'reportlab' package.\n\n"
                "Install with: pip install reportlab",
            )
            return
        path = filedialog.asksaveasfilename(
            title="Export PDF",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf"), ("All files", "*.*")],
        )
        if not path:
            return

        # Ensure draw state is up to date
        self._redraw_canvas()

        width = max(self.canvas.winfo_width(), 1)
        height = max(self.canvas.winfo_height(), 1)
        scale = self._zoom
        max_node_x = max((n.x for n in self._nodes), default=0.0)
        if len(self._bus_lefts) < len(self._bus_offsets):
            self._bus_lefts.extend([40.0] * (len(self._bus_offsets) - len(self._bus_lefts)))
        if len(self._bus_rights) < len(self._bus_offsets):
            self._bus_rights.extend(
                [max_node_x + 200.0] * (len(self._bus_offsets) - len(self._bus_rights))
            )
        if len(self._bus_lefts) > len(self._bus_offsets):
            self._bus_lefts = self._bus_lefts[: len(self._bus_offsets)]
        if len(self._bus_rights) > len(self._bus_offsets):
            self._bus_rights = self._bus_rights[: len(self._bus_offsets)]
        eff_lefts = list(self._bus_lefts)
        eff_rights = list(self._bus_rights)
        for idx in range(len(eff_lefts) - 1):
            if idx % 2 == 0:
                shared = eff_rights[idx]
                eff_rights[idx + 1] = shared
            else:
                shared = eff_lefts[idx]
                eff_lefts[idx + 1] = shared
        min_left = min(eff_lefts, default=40.0)
        max_right = max(eff_rights, default=max_node_x + 200.0)
        total_width = max(
            width,
            int(max(max_right, max_node_x + 200.0) * scale),
        )
        base_y = height * 0.5 + self._pan_y
        bus_ys = [base_y + offset * scale for offset in self._bus_offsets]
        box_w = self._box_w * scale
        box_h = self._box_h * scale
        span = box_h + 60 * scale
        min_y = min((y - span for y in bus_ys), default=0.0)
        max_y = max((y + span for y in bus_ys), default=height)
        for node in self._nodes:
            if not bus_ys:
                break
            bus_index = min(max(node.bus_index, 0), max(len(bus_ys) - 1, 0))
            bus_y = bus_ys[bus_index]
            _, node_box_h = self._node_box_dims(node, scale)
            y0, y1 = self._node_box_y(node, bus_y, node_box_h, scale)
            min_y = min(min_y, y0)
            max_y = max(max_y, y1)
        margin = 20.0
        min_y -= margin
        max_y += margin
        # Fit to 11x9 inch landscape page (in points)
        page_w = 11 * 72
        page_h = 9 * 72
        margin = 36.0
        content_w = max(total_width, 1)
        content_h = max(max_y - min_y, 1)
        fit_scale = min(
            (page_w - margin * 2) / content_w,
            (page_h - margin * 2) / content_h,
        )

        def _to_pdf(x: float, y: float) -> Tuple[float, float]:
            px = margin + (x - 0.0) * fit_scale
            py = margin + (y - min_y) * fit_scale
            return px, page_h - py

        def _wrap_pdf_lines(text: str, size: int, max_w: float) -> List[str]:
            if max_w <= 0:
                return [text]
            words = text.split()
            if not words:
                return [""]
            lines: List[str] = []
            current = words[0]
            for word in words[1:]:
                test = f"{current} {word}"
                if pdfmetrics.stringWidth(test, "Helvetica", size) <= max_w:
                    current = test
                else:
                    lines.append(current)
                    current = word
            lines.append(current)
            final_lines: List[str] = []
            for line in lines:
                if pdfmetrics.stringWidth(line, "Helvetica", size) <= max_w:
                    final_lines.append(line)
                    continue
                chunk = ""
                for ch in line:
                    test = chunk + ch
                    if pdfmetrics.stringWidth(test, "Helvetica", size) <= max_w:
                        chunk = test
                    else:
                        if chunk:
                            final_lines.append(chunk)
                        chunk = ch
                if chunk:
                    final_lines.append(chunk)
            return final_lines

        def _fit_pdf_font(
            text: str, max_w: float, max_h: float, base_size: float
        ) -> Tuple[int, float, float, float, List[str]]:
            max_w = max_w * 0.88
            max_h = max_h * 0.82
            size = max(6, int(base_size))
            while size >= 6:
                ascent = pdfmetrics.getAscent("Helvetica") * size / 1000.0
                descent = abs(pdfmetrics.getDescent("Helvetica") * size / 1000.0)
                ascent_adj = ascent * 1.05
                descent_adj = descent * 1.2
                line_h = (ascent_adj + descent_adj) * 1.1
                lines = _wrap_pdf_lines(text, size, max_w)
                total_h = line_h * len(lines)
                if total_h > max_h:
                    size -= 1
                    continue
                if total_h <= max_h:
                    return size, line_h, ascent_adj, descent_adj, lines
                size -= 1
            ascent = pdfmetrics.getAscent("Helvetica") * 6 / 1000.0
            descent = abs(pdfmetrics.getDescent("Helvetica") * 6 / 1000.0)
            ascent_adj = ascent * 1.05
            descent_adj = descent * 1.2
            return 6, (ascent_adj + descent_adj) * 1.1, ascent_adj, descent_adj, _wrap_pdf_lines(
                text, 6, max_w
            )

        def _fit_lines_exact(
            text: str, max_w: float, max_h: float, base_size: float
        ) -> Tuple[int, float, float, List[str]]:
            """
            NAME
                _fit_lines_exact - Fit lines strictly within a height/width box.
            """
            size = max(6, int(base_size))
            while size >= 6:
                lines = _wrap_pdf_lines(text, size, max_w)
                ascent = pdfmetrics.getAscent("Helvetica") * size / 1000.0
                descent = abs(pdfmetrics.getDescent("Helvetica") * size / 1000.0)
                line_h = (ascent + descent) * 1.2
                if line_h * len(lines) <= max_h:
                    return size, line_h, ascent, lines
                size -= 1
            ascent = pdfmetrics.getAscent("Helvetica") * 6 / 1000.0
            descent = abs(pdfmetrics.getDescent("Helvetica") * 6 / 1000.0)
            return 6, (ascent + descent) * 1.2, ascent, _wrap_pdf_lines(text, 6, max_w)

        c = pdfcanvas.Canvas(path, pagesize=(page_w, page_h))
        gray = Color(0.27, 0.27, 0.27)
        light = Color(0.97, 0.97, 0.97)
        callout_fill = Color(1.0, 0.98, 0.90)

        x_left = min_left * scale
        x_right = max_right * scale
        turn_radius = max(8.0, 18 * scale)
        c.setStrokeColor(gray)
        c.setLineWidth(4 * fit_scale)
        for idx, bus_y in enumerate(bus_ys):
            seg_left = eff_lefts[idx] * scale
            seg_right = eff_rights[idx] * scale
            if idx % 2 == 0:
                start_x, end_x = seg_left, seg_right
            else:
                start_x, end_x = seg_right, seg_left
            x0, y0 = _to_pdf(start_x, bus_y)
            x1, y1 = _to_pdf(end_x, bus_y)
            c.line(x0, y0, x1, y1)
            if idx + 1 < len(bus_ys):
                next_y = bus_ys[idx + 1]
                connector_x = end_x
                offset = turn_radius if idx % 2 == 0 else -turn_radius
                path_obj = c.beginPath()
                p0 = _to_pdf(connector_x, bus_y)
                p1 = _to_pdf(connector_x + offset, bus_y + turn_radius)
                p2 = _to_pdf(connector_x + offset, next_y - turn_radius)
                p3 = _to_pdf(connector_x, next_y)
                path_obj.moveTo(p0[0], p0[1])
                path_obj.curveTo(p1[0], p1[1], p2[0], p2[1], p3[0], p3[1])
                c.setLineWidth(5 * fit_scale)
                c.drawPath(path_obj)
                c.setLineWidth(4 * fit_scale)

        node_centers = {}
        for node in self._device_nodes():
            bus_index = min(max(node.bus_index, 0), max(len(bus_ys) - 1, 0))
            bus_y = bus_ys[bus_index] if bus_ys else base_y
            node_scale = max(0.6, min(2.0, node.scale))
            node_box_w = box_w * node_scale
            node_box_h = box_h * node_scale
            seg_left = eff_lefts[bus_index] * scale
            seg_right = eff_rights[bus_index] * scale
            node_x = min(max(node.x * scale, seg_left + 20), seg_right - 20)
            x0 = node_x - node_box_w / 2
            x1 = node_x + node_box_w / 2
            if node.row == 1:
                y0 = bus_y + 30 * scale
                y1 = y0 + node_box_h
                x0l, y0l = _to_pdf(node_x, bus_y)
                x1l, y1l = _to_pdf(node_x, y0)
            else:
                y1 = bus_y - 30 * scale
                y0 = y1 - node_box_h
                x0l, y0l = _to_pdf(node_x, y1)
                x1l, y1l = _to_pdf(node_x, bus_y)
            c.setLineWidth(2 * fit_scale)
            c.line(x0l, y0l, x1l, y1l)

            rx0, ry0 = _to_pdf(x0, y0)
            rx1, ry1 = _to_pdf(x1, y1)
            c.setFillColor(light)
            c.setStrokeColor(Color(0.13, 0.13, 0.13))
            c.rect(min(rx0, rx1), min(ry0, ry1), abs(rx1 - rx0), abs(ry1 - ry0), fill=1)

            text = node.display_text_pdf()
            left = min(rx0, rx1) + 3
            right = max(rx0, rx1) - 3
            top = max(ry0, ry1) - 3
            bottom = min(ry0, ry1) + 3
            avail_w = max(1.0, right - left)
            avail_h = max(1.0, top - bottom)
            pdf_font, line_h, ascent, lines = _fit_lines_exact(
                text, avail_w, avail_h, 9 * scale * node_scale * fit_scale
            )
            c.setFillColor(Color(0, 0, 0))
            c.setFont("Helvetica", pdf_font)
            y = bottom + avail_h - ascent
            for line in lines:
                c.drawCentredString((left + right) / 2, y, line)
                y -= line_h

            node_centers[node.key] = (node_x, bus_y)

        for callout in self._callout_nodes():
            cx = callout.x * scale
            bus_index = min(max(callout.bus_index, 0), max(len(bus_ys) - 1, 0))
            bus_y = bus_ys[bus_index] if bus_ys else base_y
            box_w, box_h = self._node_box_dims(callout, scale)
            y0, y1 = self._node_box_y(callout, bus_y, box_h, scale)
            cy = (y0 + y1) / 2.0
            x0 = cx - box_w / 2
            x1 = cx + box_w / 2
            if (
                callout.callout_target_type == "node"
                and callout.callout_target_node_key in node_centers
            ):
                tx, ty = node_centers[callout.callout_target_node_key]
            else:
                bus_index = min(
                    max(callout.callout_target_bus, 0), max(len(bus_ys) - 1, 0)
                )
                ty = bus_ys[bus_index] if bus_ys else base_y
                tx = cx
            x0l, y0l = _to_pdf(cx, cy)
            x1l, y1l = _to_pdf(tx, ty)
            c.setStrokeColor(Color(0.4, 0.4, 0.4))
            c.setLineWidth(2 * fit_scale)
            c.line(x0l, y0l, x1l, y1l)
            rx0, ry0 = _to_pdf(x0, y0)
            rx1, ry1 = _to_pdf(x1, y1)
            c.setFillColor(callout_fill)
            c.setStrokeColor(Color(0.4, 0.4, 0.4))
            c.rect(min(rx0, rx1), min(ry0, ry1), abs(rx1 - rx0), abs(ry1 - ry0), fill=1)
            left = min(rx0, rx1) + 3
            right = max(rx0, rx1) - 3
            top = max(ry0, ry1) - 3
            bottom = min(ry0, ry1) + 3
            avail_w = max(1.0, right - left)
            avail_h = max(1.0, top - bottom)
            node_scale = max(0.6, min(2.0, callout.scale))
            pdf_font, line_h, ascent, lines = _fit_lines_exact(
                callout.callout_text, avail_w, avail_h, 9 * scale * node_scale * fit_scale
            )
            c.setFillColor(Color(0, 0, 0))
            c.setFont("Helvetica", pdf_font)
            y = bottom + avail_h - ascent
            for line in lines:
                c.drawCentredString((left + right) / 2, y, line)
                y -= line_h

        c.showPage()
        c.save()
        messagebox.showinfo("Exported", f"Wrote PDF to {path}")

    def _on_export_java_constants(self) -> None:
        """
        NAME
            _on_export_java_constants - Export CAN IDs into a Java constants class.
        """
        profile_name = self.entry_profile.get().strip() or "Bringup"
        default_name = "BringupConstants.java"
        root = Path(__file__).resolve().parents[2]
        default_dir = root / "src" / "main" / "java"
        path = filedialog.asksaveasfilename(
            title="Export Java Constants",
            initialdir=str(default_dir) if default_dir.exists() else None,
            initialfile=default_name,
            defaultextension=".java",
            filetypes=[("Java", "*.java"), ("All files", "*.*")],
        )
        if not path:
            return
        class_name = Path(path).stem or "BringupConstants"
        package = self._derive_java_package(path, default_dir)
        constants: List[Tuple[str, int]] = []
        used_names: Dict[str, int] = {}
        for node in self._device_nodes():
            name = self._sanitize_java_identifier(node.label)
            name = f"CAN_ID_{name}"
            if name in used_names:
                used_names[name] += 1
                name = f"{name}_{node.can_id}"
            else:
                used_names[name] = 1
            constants.append((name, int(node.can_id)))
        constants.sort(key=lambda item: item[0])
        lines: List[str] = []
        if package:
            lines.append(f"package {package};")
            lines.append("")
        lines.append("/**")
        lines.append(" * Auto-generated CAN ID constants.")
        lines.append(f" * Profile: {profile_name}")
        lines.append(" */")
        lines.append(f"public final class {class_name} {{")
        lines.append(f"    private {class_name}() {{}}")
        lines.append("")
        if not constants:
            lines.append("    // No device nodes available.")
        else:
            for name, can_id in constants:
                lines.append(f"    public static final int {name} = {can_id};")
        lines.append("}")
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("\n".join(lines))
                handle.write("\n")
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to write {path}: {exc}")
            return
        messagebox.showinfo("Exported", f"Wrote Java constants to {path}")

    def _sanitize_java_identifier(self, label: str) -> str:
        """
        NAME
            _sanitize_java_identifier - Convert a label into a Java identifier suffix.
        """
        cleaned = re.sub(r"[^A-Za-z0-9]+", "_", label.strip().upper())
        cleaned = re.sub(r"_+", "_", cleaned).strip("_")
        if not cleaned:
            cleaned = "NODE"
        if not cleaned[0].isalpha():
            cleaned = f"NODE_{cleaned}"
        return cleaned

    def _derive_java_package(self, path: str, root_dir: Path) -> str:
        """
        NAME
            _derive_java_package - Infer package name from a Java source path.
        """
        try:
            file_path = Path(path).resolve()
            root_path = root_dir.resolve()
            rel = file_path.relative_to(root_path)
        except Exception:
            return ""
        parts = list(rel.parts[:-1])
        if not parts:
            return ""
        return ".".join(parts)

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

    def _nearest_callout_target(self, cx: float, cy: float) -> Tuple[str, int, Optional[int]]:
        """
        NAME
            _nearest_callout_target - Choose nearest node or bus for callouts.
        """
        scale = max(self._zoom, 0.01)
        bus_ys = list(self._draw_state.get("bus_ys", []))
        if not bus_ys:
            height = max(self.canvas.winfo_height(), 1)
            base_y = height * 0.5 + self._pan_y
            bus_ys = [base_y]
        # Find nearest node center in canvas coords.
        nearest_node = None
        nearest_node_dist = float("inf")
        for node in self._nodes:
            nx = node.x * scale
            bus_index = min(max(node.bus_index, 0), max(len(bus_ys) - 1, 0))
            ny = bus_ys[bus_index]
            dx = cx - nx
            dy = cy - ny
            dist = (dx * dx + dy * dy) ** 0.5
            if dist < nearest_node_dist:
                nearest_node_dist = dist
                nearest_node = node
        # Snap to node if within threshold, else to nearest bus.
        node_snap = 40 * scale
        if nearest_node is not None and nearest_node_dist <= node_snap:
            return "node", nearest_node.bus_index, nearest_node.key
        nearest_bus = 0
        best = float("inf")
        for idx, bus_y in enumerate(bus_ys):
            dist = abs(cy - bus_y)
            if dist < best:
                best = dist
                nearest_bus = idx
        return "bus", nearest_bus, None

    def _bus_hit_test(self, cy: float) -> Optional[int]:
        """
        NAME
            _bus_hit_test - Return bus index if click is near a bus line.
        """
        bus_ys = list(self._draw_state.get("bus_ys", []))
        if not bus_ys:
            height = max(self.canvas.winfo_height(), 1)
            base_y = height * 0.5 + self._pan_y
            bus_ys = [base_y]
        threshold = 6.0
        for idx, bus_y in enumerate(bus_ys):
            if abs(cy - bus_y) <= threshold:
                return idx
        return None

    def _bus_end_hit_test(self, bus_index: int, cx: float, cy: float) -> Optional[str]:
        """
        NAME
            _bus_end_hit_test - Return "left" or "right" when near a segment end.
        """
        if bus_index < 0 or bus_index >= len(self._bus_offsets):
            return None
        bus_ys = list(self._draw_state.get("bus_ys", []))
        if not bus_ys:
            return None
        scale = max(self._zoom, 0.01)
        bus_y = bus_ys[bus_index]
        bus_lefts = self._draw_state.get("bus_lefts", self._bus_lefts)
        bus_rights = self._draw_state.get("bus_rights", self._bus_rights)
        if bus_index >= len(bus_lefts) or bus_index >= len(bus_rights):
            return None
        left_x = bus_lefts[bus_index] * scale
        right_x = bus_rights[bus_index] * scale
        if abs(cy - bus_y) > 10:
            return None
        if abs(cx - left_x) <= 10:
            return "left"
        if abs(cx - right_x) <= 10:
            return "right"
        return None

    def _reorder_buses_by_y(self) -> None:
        """
        NAME
            _reorder_buses_by_y - Reindex bus segments by vertical order.
        """
        bus_ys = list(self._draw_state.get("bus_ys", []))
        if not bus_ys or len(self._bus_offsets) <= 1:
            return
        ordering = sorted(range(len(bus_ys)), key=lambda idx: bus_ys[idx])
        if ordering == list(range(len(bus_ys))):
            return
        new_offsets = [self._bus_offsets[idx] for idx in ordering]
        if self._bus_lefts:
            self._bus_lefts = [self._bus_lefts[idx] for idx in ordering if idx < len(self._bus_lefts)]
        if self._bus_rights:
            self._bus_rights = [self._bus_rights[idx] for idx in ordering if idx < len(self._bus_rights)]
        index_map = {old: new for new, old in enumerate(ordering)}
        for node in self._nodes:
            node.bus_index = index_map.get(node.bus_index, node.bus_index)
        for callout in self._callout_nodes():
            if callout.callout_target_type == "bus":
                callout.callout_target_bus = index_map.get(
                    callout.callout_target_bus, callout.callout_target_bus
                )
        self._bus_offsets = new_offsets
        self._redraw_canvas()

    def _fit_font_size(self, text: str, max_w: float, max_h: float, base_size: int) -> int:
        """
        NAME
            _fit_font_size - Shrink font size until text fits inside a box.
        """
        size = max(6, base_size)
        lines = text.splitlines() or [text]
        while size >= 6:
            font = tkfont.Font(family="Segoe UI", size=size)
            line_h = font.metrics("linespace")
            total_h = line_h * len(lines)
            if total_h <= max_h:
                widest = max(font.measure(line) for line in lines)
                if widest <= max_w:
                    return size
            size -= 1
        return 6

    def _schedule_redraw(self) -> None:
        """
        NAME
            _schedule_redraw - Coalesce redraws during drag operations.
        """
        if self._dragging_active:
            return
        if self._redraw_pending:
            return
        self._redraw_pending = True
        self.after(16, self._flush_redraw)

    def _flush_redraw(self) -> None:
        """
        NAME
            _flush_redraw - Execute a queued redraw.
        """
        self._redraw_pending = False
        self._redraw_canvas()

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
        self._dirty = True
        self._zoom_label_var.set(f"Zoom: {int(self._zoom * 100)}%")
        self._redraw_canvas()

    def _zoom_reset(self) -> None:
        """
        NAME
            _zoom_reset - Reset zoom to 100%.
        """
        self._zoom = 1.0
        self._dirty = True
        self._zoom_label_var.set("Zoom: 100%")
        self._redraw_canvas()

    def _fit_to_window(self) -> None:
        """
        NAME
            _fit_to_window - Fit the diagram to the current canvas size.
        """
        width = max(self.canvas.winfo_width(), 1)
        height = max(self.canvas.winfo_height(), 1)
        margin = 24.0
        device_nodes = self._device_nodes()
        callouts = self._callout_nodes()
        if not device_nodes and not callouts and not self._bus_offsets:
            return

        min_x = float("inf")
        max_x = float("-inf")
        min_y = float("inf")
        max_y = float("-inf")

        for node in device_nodes:
            node_scale = max(0.6, min(2.0, node.scale))
            half_w = (self._box_w * node_scale) / 2.0
            bus_offset = self._bus_offsets[node.bus_index] if self._bus_offsets else 0.0
            if node.row == 1:
                y0 = bus_offset + 30.0
                y1 = y0 + self._box_h * node_scale
            else:
                y1 = bus_offset - 30.0
                y0 = y1 - self._box_h * node_scale
            min_x = min(min_x, node.x - half_w)
            max_x = max(max_x, node.x + half_w)
            min_y = min(min_y, y0)
            max_y = max(max_y, y1)

        for callout in callouts:
            callout_scale = max(0.6, min(2.0, callout.scale))
            half_w = (180 * callout_scale) / 2.0
            half_h = (50 * callout_scale) / 2.0
            min_x = min(min_x, callout.x - half_w)
            max_x = max(max_x, callout.x + half_w)
            center_y = self._node_center_y_unscaled(callout)
            min_y = min(min_y, center_y - half_h)
            max_y = max(max_y, center_y + half_h)

        if self._bus_offsets:
            bus_min = min(self._bus_offsets) - (self._box_h + 60.0)
            bus_max = max(self._bus_offsets) + (self._box_h + 60.0)
            min_y = min(min_y, bus_min)
            max_y = max(max_y, bus_max)

        max_node_x = max((n.x for n in device_nodes), default=0.0)
        if len(self._bus_lefts) < len(self._bus_offsets):
            self._bus_lefts.extend([40.0] * (len(self._bus_offsets) - len(self._bus_lefts)))
        if len(self._bus_rights) < len(self._bus_offsets):
            self._bus_rights.extend(
                [max_node_x + 200.0] * (len(self._bus_offsets) - len(self._bus_rights))
            )
        if len(self._bus_lefts) > len(self._bus_offsets):
            self._bus_lefts = self._bus_lefts[: len(self._bus_offsets)]
        if len(self._bus_rights) > len(self._bus_offsets):
            self._bus_rights = self._bus_rights[: len(self._bus_offsets)]
        if self._bus_offsets:
            min_left = min(self._bus_lefts, default=40.0)
            max_right = max(self._bus_rights, default=max_node_x + 200.0)
            min_x = min(min_x, min_left)
            max_x = max(max_x, max_right)
        max_x = max(max_x, max_node_x + 200.0)
        min_x = min(min_x, 0.0)

        if min_x == float("inf") or max_x == float("-inf"):
            min_x, max_x = 0.0, 400.0
        if min_y == float("inf") or max_y == float("-inf"):
            min_y, max_y = -200.0, 200.0

        content_w = max(1.0, max_x - min_x)
        content_h = max(1.0, max_y - min_y)

        zoom_x = (width - margin * 2) / content_w
        zoom_y = (height - margin * 2) / content_h
        self._zoom = max(0.1, min(2.0, min(zoom_x, zoom_y)))
        self._zoom_label_var.set(f"Zoom: {int(self._zoom * 100)}%")

        center_y = (min_y + max_y) / 2.0
        self._pan_y = -center_y * self._zoom
        self._dirty = True
        self._redraw_canvas()
        self.update_idletasks()
        self.canvas.xview_moveto(0.0)

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
