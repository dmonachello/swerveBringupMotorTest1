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
import uuid
from tkinter import messagebox, ttk
from typing import Callable, Dict, List, Optional, Tuple, Any

from .bridge_session import BridgeEvent, BridgeSession
from tools.common.json_io import read_json
from tools.common.paths import tests_deploy_path
from tools.common.tests_io import extract_test_names
from tools.common.time_utils import timestamp_hms
from .can_profiles import get_profiles_load_error, list_profiles, reload_profiles


def _load_profiles() -> List[str]:
    """
    NAME
        _load_profiles - Load profile names from bringup_profiles.json.
    """
    ok, _err = reload_profiles()
    if not ok:
        err = get_profiles_load_error()
        if err:
            print(f"ERROR: bringup_profiles.json load failed: {err}")
        return []
    return sorted(name for name in list_profiles() if name)


def _load_tests() -> List[str]:
    """
    NAME
        _load_tests - Load test names from bringup_tests.json.
    """
    try:
        path = tests_deploy_path()
        data = read_json(path)
        return extract_test_names(data)
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
                ("Summary", "printSummary"),
                ("Profile Devices", "printProfileDevices"),
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
                ("Reset UI Session", "uiHandshakeReset"),
                ("Release UI Lock", "uiDisconnect"),
                ("Protocol Monitor ON", "uiMonitorEnable"),
                ("Protocol Monitor OFF", "uiMonitorDisable"),
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
        ui_table,
        tests_table,
        rio_host: str,
        tcp_port: int,
        is_connected: Optional[Callable[[], bool]] = None,
        on_close: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__()
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
        self._last_selected_test = None
        self._last_sent_seq: Optional[int] = None
        self._nt_connected = False
        self._pending = False
        self._pending_ack = False
        self._pending_out = False
        self._pending_since: Optional[float] = None
        self._timeout_sec = 1.5
        self._client_id = str(uuid.uuid4())
        self._session_id: Optional[str] = None
        self._handshake_done = False
        self._handshake_inflight = False
        self._last_handshake_attempt = 0.0
        self._handshake_min_interval = 2.0
        self._ui_fail_interval = 5.0
        self._ui_failures: Dict[str, Dict[str, Any]] = {}
        self._prev_tcp_connected = False
        self._log_poll_interval = 0.5
        self._last_log_poll = 0.0
        self._log_poll_inflight = False
        self._log_poll_seq: Optional[int] = None
        self._out_dedupe_window = 2.0
        self._recent_out_lines: Dict[str, float] = {}
        self._seq_seeded = False
        self._last_cmd: Optional[Tuple[str, Optional[Dict[str, Any]]]] = None
        self._retry_pending = False
        self._retry_count = 0
        self._max_retries = 1
        self._state_stale_sec = 2.0
        self._state_stale = False
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
        self._profile_box = profile_box
        ttk.Label(header, text="Profile").pack(side="left", padx=(16, 4))
        profile_box.pack(side="left")
        ttk.Button(header, text="Refresh", command=self._refresh_profiles).pack(
            side="left", padx=(6, 0)
        )

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
        self._reset_button: Optional[ttk.Button] = None
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
                    if command == "uiHandshakeReset":
                        self._reset_button = btn
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
            "printSummary": "Print a concise system summary.",
            "printProfileDevices": "Print active profile devices.",
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
            "uiHandshakeReset": "Reset the UI session and resync seq.",
            "uiDisconnect": "Release the UI lock for this client.",
            "uiMonitorEnable": "Enable protocol status publishing to NT.",
            "uiMonitorDisable": "Disable protocol status publishing to NT.",
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
            "",
            "Refresh:",
            "  Reloads bringup_profiles.json and updates the dropdown list.",
        ]
        return "\n".join(lines)

    def _refresh_profiles(self) -> None:
        """
        NAME
            _refresh_profiles - Reload profile names from bringup_profiles.json.
        """
        profiles = _load_profiles() or ["(none)"]
        current = self._profile_box.get()
        self._profile_box["values"] = profiles
        if current in profiles:
            self._profile_box.set(current)
        else:
            self._profile_box.set(profiles[0])

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
            _send_tcp_command - Send a command over the TCP protocol.
        """
        if not self._tcp_connected:
            return None
        self._session.set_client_id(self._client_id)
        seq = self._session.send_command(name, args or {})
        if seq is None:
            self._tcp_connected = False
        return seq

    def _send_handshake(self, reset: bool, force: bool = False, log: bool = True) -> None:
        """
        NAME
            _send_handshake - Send a UI handshake command.
        """
        if not self._tcp_connected:
            return
        if self._pending and not force:
            self._append_output("Busy: wait for current command to finish.")
            return
        if force and self._pending:
            self._append_output("Forcing UI session reset (clearing pending state).")
            self._pending = False
            self._pending_ack = False
            self._pending_out = False
            self._pending_since = None
        payload = {"clientId": self._client_id, "reset": reset}
        if log:
            ts = timestamp_hms()
            label = "uiHandshake (reset)" if reset else "uiHandshake"
            self._append_output(f"{ts} CMD {label}")
        seq = self._send_tcp_command("uiHandshake", payload)
        if seq is not None:
            self._pending = True
            self._last_sent_seq = seq
            self._pending_ack = True
            self._pending_out = True
            self._pending_since = time.time()
            self._handshake_inflight = True
            self._last_handshake_attempt = time.time()
            self._last_cmd = ("uiHandshake", payload)

    def _send_disconnect(self, force: bool = False) -> None:
        """
        NAME
            _send_disconnect - Release the UI lock on the robot.
        """
        if not self._tcp_connected:
            return
        if self._pending and not force:
            self._append_output("Busy: wait for current command to finish.")
            return
        if force and self._pending:
            self._append_output("Forcing UI disconnect (clearing pending state).")
            self._pending = False
            self._pending_ack = False
            self._pending_out = False
            self._pending_since = None
        ts = timestamp_hms()
        self._append_output(f"{ts} CMD uiDisconnect")
        self._last_cmd = ("uiDisconnect", None)
        self._retry_pending = False
        self._retry_count = 0
        seq = self._send_tcp_command("uiDisconnect", None)
        if seq is not None:
            self._pending = True
            self._last_sent_seq = seq
            self._pending_ack = True
            self._pending_out = True
            self._pending_since = time.time()

    def _send_monitor(self, enabled: bool) -> None:
        """
        NAME
            _send_monitor - Toggle protocol monitor publishing on the robot.
        """
        if not self._tcp_connected:
            return
        if self._pending:
            self._append_output("Busy: wait for current command to finish.")
            return
        label = "uiMonitorEnable" if enabled else "uiMonitorDisable"
        ts = timestamp_hms()
        self._append_output(f"{ts} CMD {label}")
        args = {"enabled": enabled}
        self._last_cmd = (label, args)
        self._retry_pending = False
        self._retry_count = 0
        seq = self._send_tcp_command(label, args)
        if seq is not None:
            self._pending = True
            self._last_sent_seq = seq
            self._pending_ack = True
            self._pending_out = True
            self._pending_since = time.time()

    def _retry_last_command(self) -> None:
        """
        NAME
            _retry_last_command - Retry the last command after recovery.
        """
        if not self._retry_pending:
            return
        if self._retry_count >= self._max_retries:
            self._append_output("Retry limit reached; command dropped.")
            self._retry_pending = False
            return
        if self._pending:
            return
        if not self._last_cmd:
            self._retry_pending = False
            return
        name, args = self._last_cmd
        if name in ("uiHandshake", "uiDisconnect"):
            self._retry_pending = False
            return
        self._retry_count += 1
        ts = timestamp_hms()
        self._append_output(f"{ts} RETRY {name}")
        seq = self._send_tcp_command(name, args)
        if seq is not None:
            self._pending = True
            self._last_sent_seq = seq
            self._pending_ack = True
            self._pending_out = True
            self._pending_since = time.time()
            self._retry_pending = False
    def _on_action(self, command: Optional[str]) -> None:
        """
        NAME
            _on_action - Send a command when a button is pressed.
        """
        if not command:
            return
        if command == "uiHandshakeReset":
            self._send_handshake(reset=True, force=True, log=True)
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
            return
        if self._pending:
            self._append_output("Busy: wait for current command to finish.")
            return
        ts = timestamp_hms()
        self._append_output(f"{ts} CMD {command}")
        self._last_cmd = (command, None)
        self._retry_pending = False
        self._retry_count = 0
        seq = self._send_tcp_command(command, None)
        if seq is not None:
            self._pending = True
            self._last_sent_seq = seq
            self._pending_ack = True
            self._pending_out = True
            self._pending_since = time.time()

    def _on_test_selected(self, _event=None) -> None:
        """
        NAME
            _on_test_selected - Send selectTestByName when dropdown changes.
        """
        if not hasattr(self, "_test_box"):
            return
        if not self._tcp_connected:
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
        ts = timestamp_hms()
        self._append_output(f"{ts} CMD selectTestByName \"{name}\"")
        self._last_cmd = ("selectTestByName", {"name": name})
        self._retry_pending = False
        self._retry_count = 0
        seq = self._send_tcp_command("selectTestByName", {"name": name})
        if seq is not None:
            self._pending = True
            self._last_sent_seq = seq
            self._pending_ack = True
            self._pending_out = True
            self._pending_since = time.time()

    def _poll_nt(self) -> None:
        """
        NAME
            _poll_nt - Poll TCP/NT inputs and update output log.
        """
        now = time.time()
        if not self._tcp_connected and (now - self._last_connect_attempt) > 1.0:
            self._last_connect_attempt = now
        self._tcp_connected = self._session.connect()
        if self._tcp_connected:
            self._handshake_done = self._session.handshake_done()
        if self._tcp_connected != self._prev_tcp_connected:
            if self._tcp_connected:
                self._notify_ui_failure(
                    "tcp",
                    False,
                    "TCP disconnected.",
                    "TCP reconnected.",
                )
            else:
                self._notify_ui_failure(
                    "tcp",
                    True,
                    "TCP disconnected.",
                    "TCP reconnected.",
                )
            self._prev_tcp_connected = self._tcp_connected
        if not self._tcp_connected:
            self._handshake_done = False
            self._handshake_inflight = False
            self._session.reset_handshake()
        for event in self._session.poll_events():
            self._handle_tcp_response(event)

        if self._ui_table is not None:
            session_id = self._ui_table.getEntry("state/sessionId").getString("")
            if session_id and session_id != self._session_id:
                self._session_id = session_id
                self._handshake_done = False
                self._handshake_inflight = False
                self._last_handshake_attempt = 0.0
                self._session.reset_handshake()
            enabled = self._ui_table.getEntry("state/enabled").getBoolean(True)
            estopped = self._ui_table.getEntry("state/estopped").getBoolean(False)
            mode = self._ui_table.getEntry("state/mode").getString("disabled")
            last_ack_ms = self._ui_table.getEntry("state/lastAckMs").getDouble(0.0)
            nt_connected = True
        else:
            enabled = True
            estopped = False
            mode = "disabled"
            last_ack_ms = 0.0
            nt_connected = False
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
                nt_connected = bool(self._is_connected())
            except Exception:
                nt_connected = False
        self._nt_connected = nt_connected
        self._pending = self._pending_ack or self._pending_out
        if self._pending and self._pending_since is not None:
            if (time.time() - self._pending_since) > self._timeout_sec:
                self._notify_ui_failure(
                    "cmd_timeout",
                    True,
                    "TIMEOUT waiting for ACK/OUT.",
                    "Recovered: command responses received.",
                )
                self._pending = False
                self._pending_ack = False
                self._pending_out = False
                self._pending_since = None
                self._handshake_inflight = False
                if self._last_cmd is not None and not self._retry_pending:
                    self._retry_pending = True
        if not self._pending:
            self._pending_since = None
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
        stale_state = False
        if nt_connected:
            now_ms = time.time() * 1000.0
            if last_ack_ms > 0.0 and (now_ms - last_ack_ms) > (self._state_stale_sec * 1000.0):
                stale_state = True
        self._state_stale = stale_state
        nt_label = "NT OK" if nt_connected else "NT Disconnected"
        label = (
            f"TCP Connected ({nt_label}, rio={self._rio_host})"
            if self._tcp_connected
            else f"TCP Disconnected ({nt_label}, rio={self._rio_host})"
        )
        self._status_label.configure(
            text=label,
            foreground="#2f7a2f" if self._tcp_connected else "#b32323",
        )
        if nt_connected and not self._pending:
            if stale_state:
                self._pending_label.configure(text="Robot state stale (code not running?)")
            elif estopped:
                self._pending_label.configure(text="Robot E-Stop (disabled)")
            elif not enabled:
                self._pending_label.configure(text="Robot Disabled")
            elif mode:
                self._pending_label.configure(text=f"Robot: {mode}")
        if (
            self._tcp_connected
            and not stale_state
            and not self._handshake_done
            and not self._handshake_inflight
            and not self._pending
            and (time.time() - self._last_handshake_attempt) >= self._handshake_min_interval
        ):
            self._send_handshake(reset=False, log=False)
        if (
            self._tcp_connected
            and self._handshake_done
            and not self._pending
            and not self._log_poll_inflight
            and (now - self._last_log_poll) >= self._log_poll_interval
        ):
            seq = self._send_tcp_command("uiPollLog", None)
            if seq is not None:
                self._log_poll_inflight = True
                self._log_poll_seq = seq
                self._last_log_poll = now
        self._update_action_enabled()
        self.after(250, self._poll_nt)

    def _handle_tcp_response(self, event: BridgeEvent) -> None:
        """
        NAME
            _handle_tcp_response - Handle an inbound TCP response payload.
        """
        msg_type = event.type
        name = event.name.strip()
        seq = event.seq
        seq_match = self._log_poll_seq is not None and int(seq) == int(self._log_poll_seq)
        if msg_type in ("ack", "out") and (name.lower() == "uipolllog" or seq_match):
            if msg_type == "out":
                text = event.text
                if text:
                    for line in text.splitlines():
                        if self._should_skip_out_line(line):
                            continue
                        self._append_output(line)
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
            self._last_ack_seq = seq
            if self._last_sent_seq is not None and seq >= self._last_sent_seq:
                self._pending_ack = False
        elif msg_type == "out":
            seq = int(event.seq)
            name = event.name
            text = event.text
            json_payload = event.json_text
            ts = timestamp_hms()
            header = f"{ts} OUT {seq} {name}".rstrip()
            self._append_output(header)
            if text:
                for line in text.splitlines():
                    self._remember_out_line(line)
                    self._append_output(f"  {line}")
            if json_payload:
                self._append_output("  json: " + str(json_payload))
                try:
                    data = json.loads(json_payload)
                except Exception:
                    data = None
            if name == "uiHandshake" and isinstance(data, dict):
                min_next = data.get("minNextSeq")
                if isinstance(min_next, (int, float)):
                    self._seq = int(min_next) - 1
                    self._seq_seeded = True
                session_id = data.get("sessionId")
                session_id_value = session_id if isinstance(session_id, str) else ""
                min_seq = int(min_next) if isinstance(min_next, (int, float)) else None
                self._session.mark_handshake_done(session_id_value, min_seq)
            self._last_out_seq = seq
            if self._last_sent_seq is not None and seq >= self._last_sent_seq:
                self._pending_out = False
            if name == "uiHandshake":
                self._handshake_done = True
                self._handshake_inflight = False
                self._retry_last_command()

    def _update_action_enabled(self) -> None:
        """
        NAME
            _update_action_enabled - Enable/disable UI actions based on state.
        """
        allow = (
            self._tcp_connected
            and self._handshake_done
            and not self._pending
            and not self._state_stale
        )
        state = "normal" if allow else "disabled"
        for btn in getattr(self, "_action_buttons", []):
            btn.state(["!disabled"] if allow else ["disabled"])
        if hasattr(self, "_test_box"):
            self._test_box.configure(state=state)
        if self._reset_button is not None:
            self._reset_button.state(["!disabled"] if self._tcp_connected else ["disabled"])

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
            self._session.disconnect()
