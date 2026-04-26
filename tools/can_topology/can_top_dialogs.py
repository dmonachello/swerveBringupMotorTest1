"""
NAME
    can_top_dialogs.py - Tk dialogs for CAN topology editor.

SYNOPSIS
    from tools.can_topology.can_top_dialogs import NodeDialog, CalloutDialog

DESCRIPTION
    Provides modal dialogs used to add/edit nodes and callouts.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

import tkinter as tk
from tkinter import ttk, messagebox

from .can_top_models import (
    BUCKET_CATEGORIES,
    DIAGRAM_CATEGORIES,
    DIO_DEVICE_TYPES,
    GENERIC_CATEGORY,
    INTERFACE_CAN,
    INTERFACE_DIO,
    SINGLETON_CATEGORIES,
    SUPPORTED_DEVICE_TYPES,
    SUPPORTED_MANUFACTURERS,
    Node,
)

# Constants (dialog defaults and validation).
TEXT_EMPTY = ""
DIALOG_TITLE_INVALID = "Invalid"
ERR_LABEL_REQUIRED = "Label is required."
ERR_CAN_ID_REQUIRED = "CAN ID is required."
ERR_CAN_ID_INT = "CAN ID must be an integer."
ERR_CAN_ID_RANGE = "CAN ID must be -1 or in the range 0-62."
ERR_TARGET_NODE_REQUIRED = "Choose a node target."
ERR_TARGET_NOT_FOUND = "Target node not found."
ERR_CALLOUT_TEXT_REQUIRED = "Callout text is required."
ERR_BUS_INDEX_INT = "Bus index must be an integer."
ERR_BUS_INDEX_RANGE = "Bus index out of range."
ERR_LIMITS_INT = "Limit inputs must be integers."
ERR_DIO_INT = "{} must be an integer."
ERR_DIO_RANGE = "{} must be -1 or greater."
ERR_DIO_REQUIRED = "DIO channel is required."
ERR_DIO_TYPE_INVALID = "DIO device type must be limitSwitch or encoderExternal."
ERR_INT_FIELD = "{} must be an integer."
ERR_FLOAT_FIELD = "{} must be a number."
ERR_SCALE_RANGE = "Scale must be between 0.6 and 2.0."
CAN_ID_DIAGRAM_DEFAULT = -1
LABEL_INTERFACE = "Interface"
LABEL_DIO = "DIO"
LABEL_INVERT = "Invert"
LABEL_KEY = "Key"
LABEL_NODE_TYPE = "Node Type"
LABEL_BUS = "Bus"
LABEL_ROW = "Row"
LABEL_X = "X"
LABEL_SCALE = "Scale"
LABEL_FREE_Y = "Free Y"
LABEL_PROFILE_VISIBLE = "Profile Visible"
NODE_TYPE_DEVICE = "device"
NODE_TYPE_DIAGRAM = "diagram"


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

        categories = BUCKET_CATEGORIES + [GENERIC_CATEGORY] + SINGLETON_CATEGORIES + DIAGRAM_CATEGORIES
        self.var_category = tk.StringVar(value=initial.category if initial else BUCKET_CATEGORIES[0])
        self.var_interface = tk.StringVar(
            value=initial.interface if initial else INTERFACE_CAN
        )
        self.var_label = tk.StringVar(value=initial.label if initial else TEXT_EMPTY)
        self.var_can_id = tk.StringVar(value=str(initial.can_id) if initial else "")
        self.var_vendor = tk.StringVar(value=initial.vendor if initial else TEXT_EMPTY)
        self.var_type = tk.StringVar(value=initial.device_type if initial else TEXT_EMPTY)
        self.var_motor = tk.StringVar(value=initial.motor if initial else TEXT_EMPTY)
        self.var_tags = tk.StringVar(
            value=", ".join(initial.tags) if initial and initial.tags else ""
        )
        self.var_fwd = tk.StringVar(
            value=str(initial.limits.get("fwdDio")) if initial and initial.limits else TEXT_EMPTY
        )
        self.var_rev = tk.StringVar(
            value=str(initial.limits.get("revDio")) if initial and initial.limits else TEXT_EMPTY
        )
        self.var_limits_invert = tk.BooleanVar(
            value=bool(initial.limits.get("invert")) if initial and initial.limits else False
        )
        self.var_dio = tk.StringVar(
            value=str(initial.dio) if initial and initial.dio is not None else TEXT_EMPTY
        )
        self.var_dio_invert = tk.BooleanVar(
            value=bool(initial.invert) if initial and initial.invert is not None else False
        )
        self.var_terminator = tk.BooleanVar(
            value=bool(initial.terminator) if initial and initial.terminator is not None else False
        )
        self.var_key = tk.StringVar(value=str(initial.key) if initial else TEXT_EMPTY)
        self.var_node_type = tk.StringVar(
            value=initial.node_type if initial else NODE_TYPE_DEVICE
        )
        self.var_bus = tk.StringVar(value=str(initial.bus_index) if initial else "0")
        self.var_row = tk.StringVar(value=str(initial.row) if initial else "0")
        self.var_x = tk.StringVar(value=str(initial.x) if initial else "0.0")
        self.var_scale = tk.StringVar(value=str(initial.scale) if initial else "1.0")
        self.var_free_y = tk.StringVar(
            value=str(initial.free_y) if initial and initial.free_y is not None else TEXT_EMPTY
        )
        self.var_profile_visible = tk.BooleanVar(
            value=bool(initial.profile_visible) if initial else True
        )

        ttk.Label(frame, text=LABEL_KEY).grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.var_key, width=10, state="readonly").grid(
            row=0, column=1, sticky="w", pady=(0, 4)
        )

        ttk.Label(frame, text=LABEL_NODE_TYPE).grid(row=1, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.var_node_type, width=14, state="readonly").grid(
            row=1, column=1, sticky="w", pady=(0, 4)
        )

        ttk.Label(frame, text="Category").grid(row=2, column=0, sticky="w")
        self.combo_category = ttk.Combobox(
            frame, textvariable=self.var_category, values=categories, state="readonly", width=22
        )
        self.combo_category.grid(row=2, column=1, sticky="w", pady=(0, 4))

        ttk.Label(frame, text=LABEL_INTERFACE).grid(row=3, column=0, sticky="w")
        self.combo_interface = ttk.Combobox(
            frame, textvariable=self.var_interface, values=[INTERFACE_CAN, INTERFACE_DIO], state="readonly", width=22
        )
        self.combo_interface.grid(row=3, column=1, sticky="w", pady=(0, 4))

        ttk.Label(frame, text="Label").grid(row=4, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.var_label, width=24).grid(row=4, column=1, sticky="w")

        ttk.Label(frame, text="CAN ID").grid(row=5, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.var_can_id, width=10).grid(row=5, column=1, sticky="w")

        ttk.Label(frame, text=LABEL_DIO).grid(row=6, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.var_dio, width=10).grid(row=6, column=1, sticky="w")

        ttk.Checkbutton(frame, text=LABEL_INVERT, variable=self.var_dio_invert).grid(
            row=7, column=0, columnspan=2, sticky="w"
        )

        ttk.Label(frame, text="Vendor").grid(row=8, column=0, sticky="w")
        self.combo_vendor = ttk.Combobox(
            frame, textvariable=self.var_vendor, values=SUPPORTED_MANUFACTURERS, width=22
        )
        self.combo_vendor.grid(row=8, column=1, sticky="w")

        ttk.Label(frame, text="Device Type").grid(row=9, column=0, sticky="w")
        self.combo_type = ttk.Combobox(
            frame, textvariable=self.var_type, values=SUPPORTED_DEVICE_TYPES, width=22
        )
        self.combo_type.grid(row=9, column=1, sticky="w")

        ttk.Label(frame, text="Motor").grid(row=10, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.var_motor, width=24).grid(row=10, column=1, sticky="w")

        ttk.Label(frame, text="Fwd Limit").grid(row=11, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.var_fwd, width=12).grid(row=11, column=1, sticky="w")

        ttk.Label(frame, text="Rev Limit").grid(row=12, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.var_rev, width=12).grid(row=12, column=1, sticky="w")

        ttk.Checkbutton(frame, text="Invert Limits", variable=self.var_limits_invert).grid(
            row=13, column=0, columnspan=2, sticky="w"
        )
        ttk.Checkbutton(frame, text="Bus Terminator", variable=self.var_terminator).grid(
            row=14, column=0, columnspan=2, sticky="w"
        )

        ttk.Label(frame, text=LABEL_BUS).grid(row=15, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.var_bus, width=10).grid(row=15, column=1, sticky="w")

        ttk.Label(frame, text=LABEL_ROW).grid(row=16, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.var_row, width=10).grid(row=16, column=1, sticky="w")

        ttk.Label(frame, text=LABEL_X).grid(row=17, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.var_x, width=12).grid(row=17, column=1, sticky="w")

        ttk.Label(frame, text=LABEL_SCALE).grid(row=18, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.var_scale, width=12).grid(row=18, column=1, sticky="w")

        ttk.Label(frame, text=LABEL_FREE_Y).grid(row=19, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.var_free_y, width=12).grid(row=19, column=1, sticky="w")

        ttk.Checkbutton(frame, text=LABEL_PROFILE_VISIBLE, variable=self.var_profile_visible).grid(
            row=20, column=0, columnspan=2, sticky="w"
        )

        ttk.Label(frame, text="Tags").grid(row=21, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.var_tags, width=24).grid(row=21, column=1, sticky="w")

        button_row = ttk.Frame(frame)
        button_row.grid(row=22, column=0, columnspan=2, sticky="e", pady=(8, 0))
        ttk.Button(button_row, text="Cancel", command=self._on_cancel).pack(side="right", padx=(4, 0))
        ttk.Button(button_row, text="OK", command=self._on_ok).pack(side="right")
        self._sync_device_type_choices()
        self.var_interface.trace_add("write", self._on_interface_change)

    def _on_interface_change(self, *_args: object) -> None:
        """
        NAME
            _on_interface_change - Update device-type choices for interface.
        """
        self._sync_device_type_choices()

    def _sync_device_type_choices(self) -> None:
        """
        NAME
            _sync_device_type_choices - Update device type list for interface.
        """
        interface = self.var_interface.get().strip().upper()
        if interface == INTERFACE_DIO:
            self.combo_type["values"] = DIO_DEVICE_TYPES
            if self.var_type.get().strip() not in DIO_DEVICE_TYPES and DIO_DEVICE_TYPES:
                self.var_type.set(DIO_DEVICE_TYPES[0])
        else:
            self.combo_type["values"] = SUPPORTED_DEVICE_TYPES

    def _on_ok(self) -> None:
        """
        NAME
            _on_ok - Validate and commit dialog data.
        """
        label = self.var_label.get().strip()
        can_id_text = self.var_can_id.get().strip()
        if not label:
            messagebox.showerror(DIALOG_TITLE_INVALID, ERR_LABEL_REQUIRED)
            return
        category = self.var_category.get().strip()
        interface = self.var_interface.get().strip().upper()
        try:
            allow_empty = category in DIAGRAM_CATEGORIES or interface == INTERFACE_DIO
            can_id = self._parse_can_id(can_id_text, allow_empty=allow_empty)
        except ValueError as exc:
            messagebox.showerror(DIALOG_TITLE_INVALID, str(exc))
            return
        limits = None
        fwd_text = self.var_fwd.get().strip()
        rev_text = self.var_rev.get().strip()
        invert = bool(self.var_limits_invert.get())
        if fwd_text or rev_text or invert:
            try:
                limits = {
                    "fwdDio": self._parse_dio_value(fwd_text, "Forward DIO"),
                    "revDio": self._parse_dio_value(rev_text, "Reverse DIO"),
                    "invert": invert,
                }
            except ValueError:
                messagebox.showerror(DIALOG_TITLE_INVALID, ERR_LIMITS_INT)
                return
        dio_value = None
        dio_text = self.var_dio.get().strip()
        if interface == INTERFACE_DIO:
            if not dio_text:
                messagebox.showerror(DIALOG_TITLE_INVALID, ERR_DIO_REQUIRED)
                return
            try:
                dio_value = self._parse_dio_value(dio_text, LABEL_DIO)
            except ValueError as exc:
                messagebox.showerror(DIALOG_TITLE_INVALID, str(exc))
                return
            if dio_value < 0:
                messagebox.showerror(DIALOG_TITLE_INVALID, ERR_DIO_REQUIRED)
                return
            if self.var_type.get().strip() not in DIO_DEVICE_TYPES:
                messagebox.showerror(DIALOG_TITLE_INVALID, ERR_DIO_TYPE_INVALID)
                return
        try:
            bus_index = self._parse_int_field(self.var_bus.get().strip(), LABEL_BUS)
            row = self._parse_int_field(self.var_row.get().strip(), LABEL_ROW)
            x = self._parse_float_field(self.var_x.get().strip(), LABEL_X)
            scale = self._parse_float_field(self.var_scale.get().strip(), LABEL_SCALE)
            free_y = self._parse_optional_float_field(self.var_free_y.get().strip(), LABEL_FREE_Y)
        except ValueError as exc:
            messagebox.showerror(DIALOG_TITLE_INVALID, str(exc))
            return
        if scale < 0.6 or scale > 2.0:
            messagebox.showerror(DIALOG_TITLE_INVALID, ERR_SCALE_RANGE)
            return
        self.result = {
            "category": category,
            "interface": interface,
            "label": label,
            "can_id": can_id,
            "vendor": self.var_vendor.get().strip(),
            "device_type": self.var_type.get().strip(),
            "motor": self.var_motor.get().strip(),
            "limits": limits,
            "dio": dio_value,
            "dio_invert": bool(self.var_dio_invert.get()),
            "terminator": self.var_terminator.get(),
            "bus_index": bus_index,
            "row": row,
            "x": x,
            "scale": scale,
            "free_y": free_y,
            "profile_visible": bool(self.var_profile_visible.get()),
            "tags": self._parse_tags(self.var_tags.get()),
        }
        self.destroy()

    def _on_cancel(self) -> None:
        """
        NAME
            _on_cancel - Close the dialog without saving.
        """
        self.result = None
        self.destroy()

    @staticmethod
    def _parse_can_id(value: str, allow_empty: bool) -> int:
        """
        NAME
            _parse_can_id - Parse and validate a CAN ID entry.

        RETURNS
            Parsed CAN ID value.
        """
        if not value:
            if allow_empty:
                return CAN_ID_DIAGRAM_DEFAULT
            raise ValueError(ERR_CAN_ID_REQUIRED)
        if not re.fullmatch(r"-?\d+", value):
            raise ValueError(ERR_CAN_ID_INT)
        can_id = int(value)
        if can_id < -1 or can_id > 62:
            raise ValueError(ERR_CAN_ID_RANGE)
        return can_id

    @staticmethod
    def _parse_dio_value(value: str, label: str) -> int:
        """
        NAME
            _parse_dio_value - Normalize a DIO entry for limit switches.

        RETURNS
            Parsed DIO value, or -1 when left blank.
        """
        if not value:
            return -1
        if not re.fullmatch(r"-?\d+", value):
            raise ValueError(ERR_DIO_INT.format(label))
        dio = int(value)
        if dio < -1:
            raise ValueError(ERR_DIO_RANGE.format(label))
        return dio

    @staticmethod
    def _parse_int_field(text: str, label: str) -> int:
        """
        NAME
            _parse_int_field - Parse a required integer dialog field.
        """
        try:
            return int(text)
        except ValueError as exc:
            raise ValueError(ERR_INT_FIELD.format(label)) from exc

    @staticmethod
    def _parse_float_field(text: str, label: str) -> float:
        """
        NAME
            _parse_float_field - Parse a required numeric dialog field.
        """
        try:
            return float(text)
        except ValueError as exc:
            raise ValueError(ERR_FLOAT_FIELD.format(label)) from exc

    @staticmethod
    def _parse_optional_float_field(text: str, label: str) -> Optional[float]:
        """
        NAME
            _parse_optional_float_field - Parse an optional numeric field.
        """
        if not text:
            return None
        return NodeDialog._parse_float_field(text, label)

    @staticmethod
    def _parse_tags(value: str) -> List[str]:
        """
        NAME
            _parse_tags - Parse a comma-separated tag string.
        """
        if not value:
            return []
        tags = [tag.strip() for tag in value.split(",")]
        return [tag for tag in tags if tag]


class CalloutDialog(tk.Toplevel):
    """
    NAME
        CalloutDialog - Modal dialog for adding or editing callouts.

    DESCRIPTION
        Lets the user set callout text and choose a target bus or node.
    """

    def __init__(
        self,
        master: tk.Widget,
        title: str,
        nodes: List[Node],
        bus_count: int,
        initial: Optional[Node] = None,
    ) -> None:
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

    def _build_ui(self, initial: Optional[Node]) -> None:
        """
        NAME
            _build_ui - Build callout dialog controls.
        """
        frame = ttk.Frame(self, padding=12)
        frame.grid(row=0, column=0, sticky="nsew")

        self.var_text = tk.StringVar(value=initial.callout_text if initial else TEXT_EMPTY)
        target_type = initial.callout_target_type if initial else "node"
        self.var_target_type = tk.StringVar(value=target_type)
        self.var_target_bus = tk.StringVar(value=str(initial.callout_target_bus if initial else 0))
        self.var_target_node = tk.StringVar(value=TEXT_EMPTY)
        self.var_tags = tk.StringVar(
            value=", ".join(initial.tags) if initial and initial.tags else TEXT_EMPTY
        )
        self._node_label_map: Dict[str, int] = {}

        if initial and initial.callout_target_node_key is not None:
            for node in self._nodes:
                if node.key == initial.callout_target_node_key:
                    self.var_target_node.set(
                        f"{node.label} (id {node.can_id}) [key {node.key}]"
                    )
                    break

        ttk.Label(frame, text="Text").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.var_text, width=30).grid(row=0, column=1, sticky="w")

        ttk.Label(frame, text="Target").grid(row=1, column=0, sticky="w")
        target_row = ttk.Frame(frame)
        target_row.grid(row=1, column=1, sticky="w")
        ttk.Radiobutton(
            target_row, text="Node", variable=self.var_target_type, value="node"
        ).pack(side="left")
        ttk.Radiobutton(
            target_row, text="Bus", variable=self.var_target_type, value="bus"
        ).pack(side="left", padx=(4, 0))

        ttk.Label(frame, text="Node").grid(row=2, column=0, sticky="w")
        node_values = []
        for n in self._nodes:
            label = f"{n.label} (id {n.can_id}) [key {n.key}]"
            self._node_label_map[label] = n.key
            node_values.append(label)
        self.combo_node = ttk.Combobox(frame, textvariable=self.var_target_node, values=node_values, width=28)
        self.combo_node.grid(row=2, column=1, sticky="w")

        ttk.Label(frame, text="Bus").grid(row=3, column=0, sticky="w")
        bus_values = [str(i) for i in range(self._bus_count)]
        self.combo_bus = ttk.Combobox(frame, textvariable=self.var_target_bus, values=bus_values, width=10)
        self.combo_bus.grid(row=3, column=1, sticky="w")

        ttk.Label(frame, text="Tags").grid(row=4, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.var_tags, width=28).grid(row=4, column=1, sticky="w")

        button_row = ttk.Frame(frame)
        button_row.grid(row=5, column=0, columnspan=2, sticky="e", pady=(8, 0))
        ttk.Button(button_row, text="Cancel", command=self._on_cancel).pack(side="right", padx=(4, 0))
        ttk.Button(button_row, text="OK", command=self._on_ok).pack(side="right")

    def _on_ok(self) -> None:
        """
        NAME
            _on_ok - Validate and return callout selection.
        """
        text = self.var_text.get().strip()
        if not text:
            messagebox.showerror(DIALOG_TITLE_INVALID, ERR_CALLOUT_TEXT_REQUIRED)
            return
        target_type = self.var_target_type.get()
        target_node_key = None
        target_node_category = ""
        target_node_label = ""
        target_node_id = None
        if target_type == "node":
            label = self.var_target_node.get().strip()
            if not label:
                messagebox.showerror(DIALOG_TITLE_INVALID, ERR_TARGET_NODE_REQUIRED)
                return
            if label in self._node_label_map:
                key = self._node_label_map[label]
                for node in self._nodes:
                    if node.key == key:
                        target_node_key = node.key
                        target_node_category = node.category
                        target_node_label = node.label
                        target_node_id = node.can_id
                        break
            else:
                for node in self._nodes:
                    if f"{node.label} (id {node.can_id})" == label:
                        target_node_key = node.key
                        target_node_category = node.category
                        target_node_label = node.label
                        target_node_id = node.can_id
                        break
            if target_node_key is None:
                messagebox.showerror(DIALOG_TITLE_INVALID, ERR_TARGET_NOT_FOUND)
                return
        target_bus = 0
        if target_type == "bus":
            try:
                target_bus = int(self.var_target_bus.get())
            except ValueError:
                messagebox.showerror(DIALOG_TITLE_INVALID, ERR_BUS_INDEX_INT)
                return
            if target_bus < 0 or target_bus >= self._bus_count:
                messagebox.showerror(DIALOG_TITLE_INVALID, ERR_BUS_INDEX_RANGE)
                return
        self.result = {
            "text": text,
            "target_type": target_type,
            "target_bus": target_bus,
            "target_node_key": target_node_key,
            "target_node_category": target_node_category,
            "target_node_label": target_node_label,
            "target_node_id": target_node_id,
            "tags": NodeDialog._parse_tags(self.var_tags.get()),
        }
        self.destroy()

    def _on_cancel(self) -> None:
        """
        NAME
            _on_cancel - Close callout dialog without changes.
        """
        self.result = None
        self.destroy()
