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
from tkinter import messagebox, ttk
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
        self._build_menu()
        self._build_ui()
        self._poll_nt()
        self.protocol("WM_DELETE_WINDOW", self._handle_close)

    def _build_menu(self) -> None:
        """
        NAME
            _build_menu - Create the main menubar with a Help menu.
        """
        menubar = tk.Menu(self)
        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="Help", command=self._show_help)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self._show_about)
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
                    self._attach_tooltip(btn, self._tooltip_text(command))
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

    def _tooltip_text(self, command: str) -> str:
        """
        NAME
            _tooltip_text - Return a short tooltip for a command.
        """
        tooltips = {
            "profileToggle": "Switch to the next bringup profile.",
            "addMotor": "Add the next motor from the active profile.",
            "addAll": "Add all motors from the active profile.",
            "printState": "Print current bringup state summary.",
            "printCANdiag": "Print local vendor API CAN diagnostics.",
            "printNTdiag": "Print PC tool NetworkTables diagnostics.",
            "printInputs": "Print controller and input status.",
            "printHealth": "Print local device health snapshot.",
            "dumpReport": "Print full bringup report (long).",
            "printBindings": "Print controller bindings and UI mappings.",
            "printCANcoder": "Print encoder status and readings.",
            "printTestsInfo": "Print details for selected test.",
            "printTestsOverview": "Print test list and enabled status.",
            "toggleTest": "Enable/disable the selected test.",
            "runTest": "Run the selected test once.",
            "runAllTests": "Run all enabled tests.",
            "printNextTest": "Print the next test that would run.",
            "canSweep": "Run a vendor API device sweep.",
            "fixedSpeed25": "Run motors at 25% output.",
            "fixedSpeed50": "Run motors at 50% output.",
            "fixedSpeed75": "Run motors at 75% output.",
            "fixedSpeed100": "Run motors at 100% output.",
            "toggleDashboard": "Toggle dashboard reporting output.",
            "clearFaults": "Clear latched device faults.",
        }
        return tooltips.get(command, "")

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
        messagebox.showinfo(
            "About Bringup Control",
            "Bringup Control UI\n"
            "PC-side NetworkTables command panel for RobotV2 bringup.\n"
            "Launch via tools/can_nt/run_can_nt.cmd --ui",
        )

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
            "  Manage which device profile is active and which motors are added.",
            "",
            "Toggle Profile:",
            "  Switches to the next profile defined in bringup_profiles.json.",
            "  The active profile controls which CAN IDs and labels the robot expects.",
            "  Use this before adding motors so commands target the correct devices.",
            "  If a profile has no devices, Add Motor/Add All will do nothing.",
            "  Output: ACK + OUT with the new profile name and device count.",
            "",
            "Add Motor:",
            "  Adds the next motor from the active profile to the bringup list.",
            "  The bringup list is the set of devices that tests and reports use.",
            "  Use this to step through devices one at a time and confirm behavior.",
            "  If the same motor is already added, it will be skipped.",
            "  Output: ACK + OUT showing the device label and ID that was added.",
            "",
            "Add All Motors:",
            "  Adds every motor from the active profile to the bringup list.",
            "  This is convenient but can start many devices at once during tests.",
            "  Prefer Add Motor for first bringup or when hardware is unverified.",
            "  Output: ACK + OUT listing all added devices (may stream in batches).",
        ]
        return "\n".join(lines)

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
            "Fixed Speed 25/50/75/100:",
            "  Runs motors at a fixed output for quick verification.",
            "  Use with caution: ensure the mechanism is safe to spin.",
            "  Output: ACK + OUT with the duty and duration.",
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
