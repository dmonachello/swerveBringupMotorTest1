from __future__ import annotations

"""
NAME
    bringup_ui.py - Bringup control UI for PC-side command dispatch.

SYNOPSIS
    from tools.can_nt.bringup_ui import BringupControlUI

DESCRIPTION
    Provides a Windows-friendly Tk UI that mirrors bringup commands with
    labeled on-screen buttons. Commands are sent over NetworkTables under
    bringup/ui, and output is displayed in a single scrolling panel.
"""

import json
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Callable, Dict, List, Optional, Tuple, Any


def _load_profiles() -> List[str]:
    """
    NAME
        _load_profiles - Load profile names from bringup_profiles.json.
    """
    try:
        root = Path(__file__).resolve().parents[2]
        path = root / "src" / "main" / "deploy" / "bringup_profiles.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        profiles = data.get("profiles", {})
        if isinstance(profiles, dict):
            return sorted(name for name in profiles.keys() if name)
    except Exception:
        pass
    return []


def _load_tests() -> List[str]:
    """
    NAME
        _load_tests - Load test names from bringup_tests.json.
    """
    try:
        root = Path(__file__).resolve().parents[2]
        path = root / "src" / "main" / "deploy" / "bringup_tests.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        tests = data.get("tests")
        if isinstance(tests, list):
            names = []
            for entry in tests:
                if isinstance(entry, dict):
                    name = entry.get("name")
                    if isinstance(name, str) and name:
                        names.append(name)
            return names
        test_sets = data.get("test_sets")
        if isinstance(test_sets, dict):
            default_set = data.get("default_test_set")
            if isinstance(default_set, str) and default_set in test_sets:
                tests = test_sets.get(default_set, [])
            else:
                tests = next(iter(test_sets.values()), [])
            if isinstance(tests, list):
                names = []
                for entry in tests:
                    if isinstance(entry, dict):
                        name = entry.get("name")
                        if isinstance(name, str) and name:
                            names.append(name)
                return names
    except Exception:
        pass
    return []


def _action_sections() -> List[Tuple[str, List[Tuple[str, Optional[str]]]]]:
    """
    NAME
        _action_sections - Build action sections with labels and commands.
    """
    return [
        (
            "Profiles",
            [
                ("Toggle Profile", "profileToggle"),
                ("Add Motor", "addMotor"),
                ("Add All Motors", "addAll"),
            ],
        ),
        (
            "Reports",
            [
                ("State", "printState"),
                ("CAN Bus", "printCANdiag"),
                ("NT Diagnostics", "printNTdiag"),
                ("Inputs", "printInputs"),
                ("Health", "printHealth"),
                ("Dump", "dumpReport"),
                ("Bindings", "printBindings"),
                ("CANcoder", "printCANcoder"),
                ("Tests Info", "printTestsInfo"),
                ("Tests Overview", "printTestsOverview"),
            ],
        ),
        (
            "Scriptable Tests",
            [
                ("Toggle Enabled", "toggleTest"),
                ("Run Selected", "runTest"),
                ("Run All", "runAllTests"),
                ("Print Next", "printNextTest"),
            ],
        ),
        (
            "Fixed Tests",
            [
                ("CAN Sweep", "canSweep"),
                ("Fixed Speed 25%", "fixedSpeed25"),
                ("Fixed Speed 50%", "fixedSpeed50"),
                ("Fixed Speed 75%", "fixedSpeed75"),
                ("Fixed Speed 100%", "fixedSpeed100"),
            ],
        ),
        (
            "System",
            [
                ("Toggle Dashboard", "toggleDashboard"),
                ("Clear Faults", "clearFaults"),
            ],
        ),
        (
            "Drive Axes",
            [
                ("Left Drive (LY Axis)", None),
                ("Right Drive (RY Axis)", None),
            ],
        ),
    ]


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
        command_sender: Callable[[str, Optional[Dict[str, Any]]], Optional[int]],
        ui_table,
        tests_table,
        rio_host: str,
        is_connected: Optional[Callable[[], bool]] = None,
        on_close: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__()
        self.title("Bringup Control")
        self.geometry("1100x720")
        self.minsize(900, 600)
        self._command_sender = command_sender
        self._ui_table = ui_table
        self._tests_table = tests_table
        self._on_close = on_close
        self._rio_host = rio_host
        self._is_connected = is_connected
        self._max_lines = 500
        self._lines: List[str] = []
        self._last_ack_seq = None
        self._last_out_seq = None
        self._last_selected_test = None
        self._last_sent_seq: Optional[int] = None
        self._connected = False
        self._pending = False
        self._pending_ack = False
        self._pending_out = False
        self._build_ui()
        self._poll_nt()
        self.protocol("WM_DELETE_WINDOW", self._handle_close)

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

        profiles = _load_profiles() or ["(none)"]
        tests = _load_tests() or ["(none)"]

        profile_box = ttk.Combobox(header, values=profiles, state="readonly", width=18)
        profile_box.set(profiles[0])
        ttk.Label(header, text="Profile").pack(side="left", padx=(16, 4))
        profile_box.pack(side="left")

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
        for section, items in _action_sections():
            ttk.Label(action_panel, text=section, foreground="#5b6672").pack(
                anchor="w", pady=(8, 2)
            )
            for label, command in items:
                btn = ttk.Button(
                    action_panel,
                    text=label,
                    command=(lambda c=command: self._on_action(c)),
                )
                if command is None:
                    btn.state(["disabled"])
                else:
                    self._action_buttons.append(btn)
                btn.pack(fill="x", pady=2)

        def _on_actions_configure(_event=None) -> None:
            actions_canvas.configure(scrollregion=actions_canvas.bbox("all"))
            actions_canvas.configure(width=action_panel.winfo_reqwidth())

        action_panel.bind("<Configure>", _on_actions_configure)

        output_panel = ttk.LabelFrame(right, text="Output", padding=10)
        output_panel.pack(fill="both", expand=True)
        output_header = ttk.Frame(output_panel)
        output_header.pack(fill="x")
        ttk.Button(output_header, text="Clear Output", command=self._clear_output).pack(
            side="right"
        )
        self._output = tk.Text(output_panel, height=10, wrap="word", state="disabled")
        self._output.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(output_panel, command=self._output.yview)
        scroll.pack(side="right", fill="y")
        self._output.configure(yscrollcommand=scroll.set)

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
    
    def _clear_output(self) -> None:
        """
        NAME
            _clear_output - Clear the output log.
        """
        self._lines = []
        self._output.configure(state="normal")
        self._output.delete("1.0", "end")
        self._output.configure(state="disabled")

    def _on_action(self, command: Optional[str]) -> None:
        """
        NAME
            _on_action - Send a command when a button is pressed.
        """
        if not command:
            return
        if not self._connected:
            self._append_output("Not connected: command blocked.")
            return
        if self._pending:
            self._append_output("Busy: wait for current command to finish.")
            return
        ts = time.strftime("%H:%M:%S")
        self._append_output(f"{ts} CMD {command}")
        seq = self._command_sender(command, None)
        if seq is not None:
            self._pending = True
            self._last_sent_seq = seq
            self._pending_ack = True
            self._pending_out = True

    def _on_test_selected(self, _event=None) -> None:
        """
        NAME
            _on_test_selected - Send selectTestByName when dropdown changes.
        """
        if not hasattr(self, "_test_box"):
            return
        if not self._connected:
            self._append_output("Not connected: selection blocked.")
            return
        if self._pending:
            self._append_output("Busy: wait for current command to finish.")
            return
        name = self._test_box.get().strip()
        if not name or name == "(none)":
            return
        if name == self._last_selected_test:
            return
        self._last_selected_test = name
        ts = time.strftime("%H:%M:%S")
        self._append_output(f"{ts} CMD selectTestByName \"{name}\"")
        seq = self._command_sender("selectTestByName", {"name": name})
        if seq is not None:
            self._pending = True
            self._last_sent_seq = seq
            self._pending_ack = True
            self._pending_out = True

    def _poll_nt(self) -> None:
        """
        NAME
            _poll_nt - Poll NT ack/out entries and update output log.
        """
        if self._ui_table is not None:
            ack_seq = self._ui_table.getEntry("ack/seq").getInteger(-1)
            if ack_seq != self._last_ack_seq and ack_seq >= 0:
                status = self._ui_table.getEntry("ack/status").getString("")
                message = self._ui_table.getEntry("ack/message").getString("")
                ts = time.strftime("%H:%M:%S")
                self._append_output(f"{ts} ACK {ack_seq} {status} {message}".rstrip())
                self._last_ack_seq = ack_seq
                if self._last_sent_seq is not None and ack_seq >= self._last_sent_seq:
                    self._pending_ack = False
            out_seq = self._ui_table.getEntry("out/seq").getInteger(-1)
            if out_seq != self._last_out_seq and out_seq >= 0:
                name = self._ui_table.getEntry("out/name").getString("")
                text = self._ui_table.getEntry("out/text").getString("")
                ts = time.strftime("%H:%M:%S")
                header = f"{ts} OUT {out_seq} {name}".rstrip()
                self._append_output(header)
                if text:
                    for line in text.splitlines():
                        self._append_output(f"  {line}")
                self._last_out_seq = out_seq
                if self._last_sent_seq is not None and out_seq >= self._last_sent_seq:
                    self._pending_out = False

            connected = True
        else:
            connected = False
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
                connected = bool(self._is_connected())
            except Exception:
                connected = False
        self._connected = connected
        self._pending = self._pending_ack or self._pending_out
        if self._pending:
            if self._pending_ack and self._pending_out:
                pending_text = "Waiting: ACK + OUT"
            elif self._pending_ack:
                pending_text = "Waiting: ACK"
            else:
                pending_text = "Waiting: OUT"
        else:
            pending_text = ""
        self._pending_label.configure(text=pending_text)
        label = (
            f"NT Connected (rio={self._rio_host})"
            if connected
            else f"NT Disconnected (rio={self._rio_host})"
        )
        self._status_label.configure(
            text=label,
            foreground="#2f7a2f" if connected else "#b32323",
        )
        self._update_action_enabled()
        self.after(250, self._poll_nt)

    def _update_action_enabled(self) -> None:
        """
        NAME
            _update_action_enabled - Enable/disable UI actions based on state.
        """
        allow = self._connected and not self._pending
        state = "normal" if allow else "disabled"
        for btn in getattr(self, "_action_buttons", []):
            btn.state(["!disabled"] if allow else ["disabled"])
        if hasattr(self, "_test_box"):
            self._test_box.configure(state=state)

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
        if self._on_close:
            self._on_close()
        self.destroy()
