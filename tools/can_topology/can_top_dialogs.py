"""
NAME
    can_top_dialogs.py - Tk dialogs for CAN topology editor.

SYNOPSIS
    from tools.can_topology.can_top_dialogs import NodeDialog, CalloutDialog

DESCRIPTION
    Provides modal dialogs used to add/edit nodes and callouts.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import tkinter as tk
from tkinter import ttk, messagebox

from .can_top_models import (
    BUCKET_CATEGORIES,
    GENERIC_CATEGORY,
    SINGLETON_CATEGORIES,
    SUPPORTED_DEVICE_TYPES,
    SUPPORTED_MANUFACTURERS,
    Node,
)


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
        self.combo_category.grid(row=0, column=1, sticky="w", pady=(0, 4))

        ttk.Label(frame, text="Label").grid(row=1, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.var_label, width=24).grid(row=1, column=1, sticky="w")

        ttk.Label(frame, text="CAN ID").grid(row=2, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.var_can_id, width=10).grid(row=2, column=1, sticky="w")

        ttk.Label(frame, text="Vendor").grid(row=3, column=0, sticky="w")
        self.combo_vendor = ttk.Combobox(
            frame, textvariable=self.var_vendor, values=SUPPORTED_MANUFACTURERS, width=22
        )
        self.combo_vendor.grid(row=3, column=1, sticky="w")

        ttk.Label(frame, text="Device Type").grid(row=4, column=0, sticky="w")
        self.combo_type = ttk.Combobox(
            frame, textvariable=self.var_type, values=SUPPORTED_DEVICE_TYPES, width=22
        )
        self.combo_type.grid(row=4, column=1, sticky="w")

        ttk.Label(frame, text="Motor").grid(row=5, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.var_motor, width=24).grid(row=5, column=1, sticky="w")

        ttk.Label(frame, text="Fwd Limit").grid(row=6, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.var_fwd, width=12).grid(row=6, column=1, sticky="w")

        ttk.Label(frame, text="Rev Limit").grid(row=7, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.var_rev, width=12).grid(row=7, column=1, sticky="w")

        ttk.Checkbutton(frame, text="Invert Limits", variable=self.var_invert).grid(
            row=8, column=0, columnspan=2, sticky="w"
        )
        ttk.Checkbutton(frame, text="Bus Terminator", variable=self.var_terminator).grid(
            row=9, column=0, columnspan=2, sticky="w"
        )

        button_row = ttk.Frame(frame)
        button_row.grid(row=10, column=0, columnspan=2, sticky="e", pady=(8, 0))
        ttk.Button(button_row, text="Cancel", command=self._on_cancel).pack(side="right", padx=(4, 0))
        ttk.Button(button_row, text="OK", command=self._on_ok).pack(side="right")

    def _on_ok(self) -> None:
        """
        NAME
            _on_ok - Validate and commit dialog data.
        """
        label = self.var_label.get().strip()
        can_id = self.var_can_id.get().strip()
        if not label:
            messagebox.showerror("Invalid", "Label is required.")
            return
        if not can_id.isdigit():
            messagebox.showerror("Invalid", "CAN ID must be an integer.")
            return
        limits = None
        if self.var_fwd.get().strip() or self.var_rev.get().strip() or self.var_invert.get():
            try:
                limits = {
                    "fwdDio": int(self.var_fwd.get()) if self.var_fwd.get().strip() else "",
                    "revDio": int(self.var_rev.get()) if self.var_rev.get().strip() else "",
                    "invert": bool(self.var_invert.get()),
                }
            except ValueError:
                messagebox.showerror("Invalid", "Limit inputs must be integers.")
                return
        self.result = {
            "category": self.var_category.get(),
            "label": label,
            "can_id": int(can_id),
            "vendor": self.var_vendor.get().strip(),
            "device_type": self.var_type.get().strip(),
            "motor": self.var_motor.get().strip(),
            "limits": limits,
            "terminator": self.var_terminator.get(),
        }
        self.destroy()

    def _on_cancel(self) -> None:
        """
        NAME
            _on_cancel - Close the dialog without saving.
        """
        self.result = None
        self.destroy()


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

        self.var_text = tk.StringVar(value=initial.callout_text if initial else "")
        target_type = initial.callout_target_type if initial else "node"
        self.var_target_type = tk.StringVar(value=target_type)
        self.var_target_bus = tk.StringVar(value=str(initial.callout_target_bus if initial else 0))
        self.var_target_node = tk.StringVar()

        if initial and initial.callout_target_node_key is not None:
            for node in self._nodes:
                if node.key == initial.callout_target_node_key:
                    self.var_target_node.set(f"{node.label} (id {node.can_id})")
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
        node_values = [f"{n.label} (id {n.can_id})" for n in self._nodes]
        self.combo_node = ttk.Combobox(frame, textvariable=self.var_target_node, values=node_values, width=28)
        self.combo_node.grid(row=2, column=1, sticky="w")

        ttk.Label(frame, text="Bus").grid(row=3, column=0, sticky="w")
        bus_values = [str(i) for i in range(self._bus_count)]
        self.combo_bus = ttk.Combobox(frame, textvariable=self.var_target_bus, values=bus_values, width=10)
        self.combo_bus.grid(row=3, column=1, sticky="w")

        button_row = ttk.Frame(frame)
        button_row.grid(row=4, column=0, columnspan=2, sticky="e", pady=(8, 0))
        ttk.Button(button_row, text="Cancel", command=self._on_cancel).pack(side="right", padx=(4, 0))
        ttk.Button(button_row, text="OK", command=self._on_ok).pack(side="right")

    def _on_ok(self) -> None:
        """
        NAME
            _on_ok - Validate and return callout selection.
        """
        text = self.var_text.get().strip()
        if not text:
            messagebox.showerror("Invalid", "Callout text is required.")
            return
        target_type = self.var_target_type.get()
        target_node_key = None
        target_node_category = ""
        target_node_label = ""
        target_node_id = None
        if target_type == "node":
            label = self.var_target_node.get().strip()
            if not label:
                messagebox.showerror("Invalid", "Choose a node target.")
                return
            for node in self._nodes:
                if f"{node.label} (id {node.can_id})" == label:
                    target_node_key = node.key
                    target_node_category = node.category
                    target_node_label = node.label
                    target_node_id = node.can_id
                    break
            if target_node_key is None:
                messagebox.showerror("Invalid", "Target node not found.")
                return
        target_bus = 0
        if target_type == "bus":
            try:
                target_bus = int(self.var_target_bus.get())
            except ValueError:
                messagebox.showerror("Invalid", "Bus index must be an integer.")
                return
            if target_bus < 0 or target_bus >= self._bus_count:
                messagebox.showerror("Invalid", "Bus index out of range.")
                return
        self.result = {
            "text": text,
            "target_type": target_type,
            "target_bus": target_bus,
            "target_node_key": target_node_key,
            "target_node_category": target_node_category,
            "target_node_label": target_node_label,
            "target_node_id": target_node_id,
        }
        self.destroy()

    def _on_cancel(self) -> None:
        """
        NAME
            _on_cancel - Close callout dialog without changes.
        """
        self.result = None
        self.destroy()
