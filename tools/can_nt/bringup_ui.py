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

NOTES
    All UI command sends must go through tools.can_nt.bridge_ops wrappers.
"""

import json
import time
import tkinter as tk
import uuid
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Dict, List, Optional, Tuple, Any

from .bridge_cmd_tracker import CommandTracker
from .bridge_ops import (
    connect,
    disconnect,
    send_command,
    show_runtime_state,
    select_test_by_name,
    ui_disconnect,
    ui_handshake,
    ui_monitor,
    ui_poll_log,
    ui_ping,
)
from .bridge_session import BridgeEvent, BridgeSession
from tools.common.json_io import read_json
from tools.common.nt_labels import encode_label_for_nt
from tools.common.paths import tests_deploy_path
from tools.common.tests_io import extract_test_names
from tools.common.time_utils import timestamp_hms
from .can_profiles import get_profile, get_profiles_load_error, list_profiles, reload_profiles
from tools.can_topology.live_topology_view import LiveTopologyView

# Constants (NetworkTables paths and presence values).
NT_PATH_PRESENCE_FMT = "dev/{}/presenceConfidence"
NT_VALUE_EMPTY = ""
PRESENCE_VALUE_HIGH = "HIGH"
PRESENCE_VALUE_LOW = "LOW"
PRESENCE_VALUE_NONE = "NONE"
PRESENCE_VALUES = {
    PRESENCE_VALUE_HIGH,
    PRESENCE_VALUE_LOW,
    PRESENCE_VALUE_NONE,
}

# Constants (device dict keys).
DEVICE_KEY_LABEL = "label"

# Constants (file-based presence overrides).
PRESENCE_FILE_KEY_OVERRIDES = "presenceOverrides"
PRESENCE_FILE_KEY_TIMELINE = "presenceTimeline"
PRESENCE_FILE_KEY_AT_SEC = "atSec"
PRESENCE_FILE_KEY_OVERRIDES_BLOCK = "overrides"
PRESENCE_TIME_NONE = 0.0
PRESENCE_TIMELINE_MIN_STEP = 1.0
PRESENCE_TIMELINE_DEFAULT_STEP = 2.0
LIVE_SOURCE_TCP = "tcp"
LIVE_SOURCE_FILE = "file"
LIVE_CLOCK_FORMAT = "%H:%M:%S"
LIVE_CLOCK_LABEL = "Clock:"


def _load_profiles() -> List[str]:
    """
    NAME
        _load_profiles - Load profile names from bringup_system.json.
    """
    ok, _err = reload_profiles()
    if not ok:
        err = get_profiles_load_error()
        if err:
            print(f"ERROR: bringup_system.json load failed: {err}")
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
                ("Test Prev", "selectTestPrev"),
                ("Test Next", "selectTestNext"),
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
                ("Clear Stop Latch", "clearStopLatch"),
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
        diag_table,
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
        self._diag_table = diag_table
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
        self._timeout_sec = 1.5
        self._client_id = str(uuid.uuid4())
        self._session_id: Optional[str] = None
        self._handshake_done = False
        self._handshake_inflight = False
        self._last_handshake_attempt = 0.0
        self._handshake_min_interval = 2.0
        self._handshake_warn_last = 0.0
        self._keepalive_interval = 1.0
        self._last_keepalive = 0.0
        self._last_selected_profile = ""
        self._ui_fail_interval = 5.0
        self._ui_failures: Dict[str, Dict[str, Any]] = {}
        self._prev_tcp_connected = False
        self._log_poll_interval = 2.0
        self._last_log_poll = 0.0
        self._log_poll_inflight = False
        self._log_poll_seq: Optional[int] = None
        self._out_dedupe_window = 2.0
        self._recent_out_lines: Dict[str, float] = {}
        self._seq_seeded = False
        self._last_cmd: Optional[Tuple[str, Optional[Dict[str, Any]]]] = None
        self._max_retries = 1
        self._state_stale_sec = 2.0
        self._state_stale = False
        self._tracker = CommandTracker(timeout_sec=self._timeout_sec, max_retries=self._max_retries)
        self._live_enabled_var = tk.BooleanVar(value=False)
        self._live_source_var = tk.StringVar(value=LIVE_SOURCE_TCP)
        self._live_rate_var = tk.StringVar(value="5")
        self._live_groups_var = tk.BooleanVar(value=True)
        self._live_clock_var = tk.StringVar(value=NT_VALUE_EMPTY)
        self._live_rate_min = 0.2
        self._live_rate_max = 20.0
        self._runtime_state_hz = 5.0
        self._runtime_state_interval = 1.0 / self._runtime_state_hz
        self._runtime_state_last_poll = 0.0
        self._runtime_state_pending_seq: Optional[int] = None
        self._runtime_state_pending_at = 0.0
        self._runtime_state_timeout_sec = 0.6
        self._runtime_state_path: Optional[str] = None
        self._runtime_state_path_mtime: Optional[float] = None
        self._presence_overrides_file: Dict[str, str] = {}
        self._presence_timeline: List[Dict[str, Any]] = []
        self._presence_timeline_start = PRESENCE_TIME_NONE
        self._presence_timeline_period = PRESENCE_TIME_NONE
        self._runtime_state_backoff = 1.0
        self._runtime_state_idle_count = 0
        self._runtime_state_idle_pause_sec = 5.0
        self._runtime_state_pause_until: Optional[float] = None
        self._poll_interval_active = 0.25
        self._poll_interval_idle = 1.0
        self._live_view: Optional[LiveTopologyView] = None
        self._profile_devices: Dict[str, Dict[str, Any]] = {}
        self._build_menu()
        self._build_ui()
        self._refresh_profile_devices()
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
        profile_box.bind("<<ComboboxSelected>>", self._on_profile_selected)
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

        notebook = ttk.Notebook(right)
        notebook.pack(fill="both", expand=True)
        output_panel = ttk.Frame(notebook)
        notebook.add(output_panel, text="Output")
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

        live_panel = ttk.Frame(notebook)
        notebook.add(live_panel, text="Live Topology")
        self._build_live_panel(live_panel)

    def _build_live_panel(self, parent: tk.Widget) -> None:
        """
        NAME
            _build_live_panel - Build the live topology overlay tab.
        """
        controls = ttk.Frame(parent, padding=(8, 8, 8, 4))
        controls.pack(fill="x")
        ttk.Checkbutton(
            controls,
            text="Enable Live Overlay",
            variable=self._live_enabled_var,
        ).pack(side="left")
        ttk.Checkbutton(
            controls,
            text="Show Groups",
            variable=self._live_groups_var,
            command=self._apply_live_group_toggle,
        ).pack(side="left", padx=(8, 0))
        ttk.Label(controls, text="Source:").pack(side="left", padx=(12, 4))
        source_menu = ttk.OptionMenu(
            controls,
            self._live_source_var,
            LIVE_SOURCE_TCP,
            LIVE_SOURCE_TCP,
            LIVE_SOURCE_FILE,
        )
        source_menu.pack(side="left")
        ttk.Button(controls, text="Load File...", command=self._load_runtime_state_file).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(controls, text="Reload File", command=self._reload_runtime_state_file).pack(
            side="left", padx=(6, 0)
        )
        ttk.Label(controls, text="Rate (Hz):").pack(side="left", padx=(12, 4))
        rate_entry = ttk.Entry(controls, textvariable=self._live_rate_var, width=6)
        rate_entry.pack(side="left")
        ttk.Button(controls, text="Apply", command=self._apply_runtime_state_rate).pack(
            side="left", padx=(6, 0)
        )
        ttk.Label(controls, text=LIVE_CLOCK_LABEL).pack(side="left", padx=(12, 4))
        ttk.Label(controls, textvariable=self._live_clock_var).pack(side="left")
        ttk.Button(controls, text="Zoom -", command=self._zoom_out).pack(
            side="left", padx=(12, 0)
        )
        ttk.Button(controls, text="Zoom +", command=self._zoom_in).pack(
            side="left", padx=(4, 0)
        )
        ttk.Button(controls, text="Reset Zoom", command=self._zoom_reset).pack(
            side="left", padx=(4, 0)
        )

        profile_name = self._profile_box.get() if hasattr(self, "_profile_box") else ""
        self._live_view = LiveTopologyView(parent, profile_name)
        self._live_view.set_show_groups(self._live_groups_var.get())
        self._live_view.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _on_profile_selected(self, _event=None) -> None:
        """
        NAME
            _on_profile_selected - Update live topology view when profile changes.
        """
        name = self._profile_box.get().strip() if hasattr(self, "_profile_box") else ""
        self._refresh_profile_devices()
        if self._live_view is not None and name:
            self._live_view.reload_profile(name)
        if not name or name == self._last_selected_profile:
            return
        self._last_selected_profile = name
        if not self._tcp_connected or not self._handshake_done:
            return
        if self._tracker.is_pending():
            return
        seq = send_command(self._session, "selectProfile", {"name": name})
        if seq is not None:
            self._last_sent_seq = seq
            self._tracker.start("selectProfile", {"name": name}, seq, now=time.time())

    def _refresh_profile_devices(self) -> None:
        """
        NAME
            _refresh_profile_devices - Refresh label->device mapping for the profile.
        """
        name = self._profile_box.get().strip() if hasattr(self, "_profile_box") else ""
        if not name:
            self._profile_devices = {}
            return
        try:
            devices, _expected = get_profile(name)
        except Exception:
            self._profile_devices = {}
            return
        mapping: Dict[str, Dict[str, Any]] = {}
        for device in devices:
            if not isinstance(device, dict):
                continue
            label = str(device.get(DEVICE_KEY_LABEL, NT_VALUE_EMPTY)).strip()
            if not label:
                continue
            mapping[label.lower()] = device
        self._profile_devices = mapping

    def _poll_presence_overrides(self) -> None:
        """
        NAME
            _poll_presence_overrides - Read presence confidence from NT diagnostics.
        """
        if self._live_view is None:
            return
        if not self._live_enabled_var.get():
            self._live_view.set_presence_overrides({})
            return
        source = self._live_source_var.get()
        if source == LIVE_SOURCE_FILE:
            overrides = self._presence_overrides_file
            if self._presence_timeline:
                elapsed = max(PRESENCE_TIME_NONE, time.time() - self._presence_timeline_start)
                if self._presence_timeline_period > PRESENCE_TIME_NONE:
                    elapsed = elapsed % self._presence_timeline_period
                active = None
                for entry in self._presence_timeline:
                    at_sec = float(entry.get(PRESENCE_FILE_KEY_AT_SEC, PRESENCE_TIME_NONE))
                    if elapsed >= at_sec:
                        active = entry
                    else:
                        break
                if isinstance(active, dict):
                    overrides = dict(active.get(PRESENCE_FILE_KEY_OVERRIDES_BLOCK, {}))
            self._live_view.set_presence_overrides(overrides or {})
            return
        if self._diag_table is None:
            self._live_view.set_presence_overrides({})
            return
        overrides: Dict[str, str] = {}
        for label, device in self._profile_devices.items():
                label = str(device.get(DEVICE_KEY_LABEL, "")).strip()
                if not label:
                    continue
                label_key = encode_label_for_nt(label)
                path = NT_PATH_PRESENCE_FMT.format(label_key)
            value = self._diag_table.getEntry(path).getString(NT_VALUE_EMPTY)
            if value in PRESENCE_VALUES:
                overrides[label] = value
        self._live_view.set_presence_overrides(overrides)

    def _load_runtime_state_file(self) -> None:
        """
        NAME
            _load_runtime_state_file - Select a runtime-state JSON file.
        """
        path = filedialog.askopenfilename(
            title="Load Runtime State JSON",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        self._runtime_state_path = path
        self._runtime_state_path_mtime = None
        self._live_source_var.set(LIVE_SOURCE_FILE)
        self._reload_runtime_state_file()

    def _reload_runtime_state_file(self) -> None:
        """
        NAME
            _reload_runtime_state_file - Manually reload the runtime-state JSON file.
        """
        if not self._runtime_state_path:
            return
        try:
            payload = read_json(Path(self._runtime_state_path))
        except Exception:
            return
        if isinstance(payload, dict):
            self._apply_runtime_state_payload(payload)
            self._apply_presence_overrides_file(payload)

    def _apply_presence_overrides_file(self, payload: Dict[str, Any]) -> None:
        """
        NAME
            _apply_presence_overrides_file - Load presence overrides/timeline from file.
        """
        overrides: Dict[str, str] = {}
        raw_overrides = payload.get(PRESENCE_FILE_KEY_OVERRIDES)
        if isinstance(raw_overrides, dict):
            for label, value in raw_overrides.items():
                label_text = str(label).strip()
                value_text = str(value).strip()
                if label_text and value_text in PRESENCE_VALUES:
                    overrides[label_text.lower()] = value_text
        self._presence_overrides_file = overrides
        timeline: List[Dict[str, Any]] = []
        raw_timeline = payload.get(PRESENCE_FILE_KEY_TIMELINE)
        if isinstance(raw_timeline, list):
            for entry in raw_timeline:
                if not isinstance(entry, dict):
                    continue
                at_sec = entry.get(PRESENCE_FILE_KEY_AT_SEC)
                block = entry.get(PRESENCE_FILE_KEY_OVERRIDES_BLOCK)
                if not isinstance(at_sec, (int, float)) or not isinstance(block, dict):
                    continue
                mapped: Dict[str, str] = {}
                for label, value in block.items():
                    label_text = str(label).strip()
                    value_text = str(value).strip()
                    if label_text and value_text in PRESENCE_VALUES:
                        mapped[label_text.lower()] = value_text
                timeline.append({PRESENCE_FILE_KEY_AT_SEC: float(at_sec), PRESENCE_FILE_KEY_OVERRIDES_BLOCK: mapped})
        timeline.sort(
            key=lambda item: float(item.get(PRESENCE_FILE_KEY_AT_SEC, PRESENCE_TIME_NONE))
        )
        self._presence_timeline = timeline
        if timeline:
            max_at = max(
                float(item.get(PRESENCE_FILE_KEY_AT_SEC, PRESENCE_TIME_NONE))
                for item in timeline
            )
            prev_at = PRESENCE_TIME_NONE
            if len(timeline) > 1:
                prev_at = float(
                    timeline[-2].get(PRESENCE_FILE_KEY_AT_SEC, PRESENCE_TIME_NONE)
                )
            step = max(PRESENCE_TIMELINE_MIN_STEP, max_at - prev_at)
            if max_at <= PRESENCE_TIME_NONE:
                step = PRESENCE_TIMELINE_DEFAULT_STEP
            self._presence_timeline_period = max_at + step
            if self._presence_timeline_period <= PRESENCE_TIME_NONE:
                self._presence_timeline_period = PRESENCE_TIMELINE_DEFAULT_STEP
            self._presence_timeline_start = time.time()
        else:
            self._presence_timeline_start = PRESENCE_TIME_NONE
            self._presence_timeline_period = PRESENCE_TIME_NONE

    def _apply_runtime_state_rate(self) -> None:
        """
        NAME
            _apply_runtime_state_rate - Update the runtime-state polling rate.
        """
        try:
            rate = float(self._live_rate_var.get())
        except (TypeError, ValueError):
            rate = self._runtime_state_hz
        rate = max(self._live_rate_min, min(self._live_rate_max, rate))
        self._runtime_state_hz = rate
        self._runtime_state_interval = 1.0 / self._runtime_state_hz
        self._live_rate_var.set(f"{rate:g}")
        self._runtime_state_backoff = 1.0
        self._runtime_state_idle_count = 0
        self._runtime_state_pause_until = None

    def _apply_live_group_toggle(self) -> None:
        """
        NAME
            _apply_live_group_toggle - Toggle group overlays in the live view.
        """
        if self._live_view is None:
            return
        self._live_view.set_show_groups(self._live_groups_var.get())

    def _zoom_in(self) -> None:
        """
        NAME
            _zoom_in - Zoom in the live topology view.
        """
        if self._live_view is not None:
            self._live_view._nudge_zoom(0.1)

    def _zoom_out(self) -> None:
        """
        NAME
            _zoom_out - Zoom out the live topology view.
        """
        if self._live_view is not None:
            self._live_view._nudge_zoom(-0.1)

    def _zoom_reset(self) -> None:
        """
        NAME
            _zoom_reset - Reset zoom in the live topology view.
        """
        if self._live_view is not None:
            self._live_view._reset_zoom()

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
            "selectTestPrev": "Select the previous test in the list.",
            "selectTestNext": "Select the next test in the list.",
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
            "clearStopLatch": "Clear the safety stop latch.",
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
            ("Live Topology", self._build_live_help()),
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
            "  - Live Topology tab shows read-only runtime overlays.",
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
            "  Switches to the next profile defined in bringup_system.json.",
            "  The active profile controls which CAN IDs and labels the robot expects.",
            "  Use this before adding motors so commands target the correct devices.",
            "  If a profile has no devices, Add Motor/Add All will do nothing.",
            "  Output: ACK + OUT with the new profile name and device count.",
            "",
            "Profile Dropdown:",
            "  Selecting a profile updates the live topology view.",
            "  If TCP is connected, it also selects that profile on the robot",
            "  (no activation; Add Motor/Add All still required).",
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
            "  Reloads bringup_system.json and updates the dropdown list.",
        ]
        return "\n".join(lines)

    def _refresh_profiles(self) -> None:
        """
        NAME
            _refresh_profiles - Reload profile names from bringup_system.json.
        """
        profiles = _load_profiles() or ["(none)"]
        current = self._profile_box.get()
        self._profile_box["values"] = profiles
        if current in profiles:
            self._profile_box.set(current)
        else:
            self._profile_box.set(profiles[0])
        self._last_selected_profile = self._profile_box.get()
        if self._live_view is not None:
            self._live_view.reload_profile(self._profile_box.get())

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

    def _build_live_help(self) -> str:
        """
        NAME
            _build_live_help - Build the Live Topology tab text.
        """
        lines = [
            "Purpose:",
            "  Show live device presence and telemetry on the topology diagram.",
            "",
            "Enable Live Overlay:",
            "  Starts polling runtime state from the roboRIO TCP UI channel.",
            "  Live overlay is read-only and does not send commands.",
            "",
            "Show Groups:",
            "  Toggles group boxes/labels from bridgeConfig by-profile groups.",
            "  Useful for visualizing CLI groups in the live view.",
            "",
            "Source:",
            "  - tcp: Fetch runtime state from the roboRIO (default).",
            "  - file: Replay a saved JSON snapshot for offline testing.",
            "",
            "Rate:",
            "  Updates per second (default 5 Hz).",
            "  Higher rates add more TCP traffic; keep it modest.",
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
        seq = send_command(self._session, name, args or {})
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
        if self._tracker.is_pending() and not force:
            self._append_output("Busy: wait for current command to finish.")
            return
        if force and self._tracker.is_pending():
            self._append_output("Forcing UI session reset (clearing pending state).")
            self._tracker.clear_pending()
        payload = {"clientId": self._client_id, "reset": reset}
        if log:
            ts = timestamp_hms()
            label = "uiHandshake (reset)" if reset else "uiHandshake"
            self._append_output(f"{ts} CMD {label}")
        self._session.set_client_id(self._client_id)
        seq = ui_handshake(self._session, self._client_id, reset)
        if seq is not None:
            self._last_sent_seq = seq
            self._tracker.start("uiHandshake", payload, seq, now=time.time(), retryable=False)
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
        if self._tracker.is_pending() and not force:
            self._append_output("Busy: wait for current command to finish.")
            return
        if force and self._tracker.is_pending():
            self._append_output("Forcing UI disconnect (clearing pending state).")
            self._tracker.clear_pending()
        ts = timestamp_hms()
        self._append_output(f"{ts} CMD uiDisconnect")
        self._last_cmd = ("uiDisconnect", None)
        seq = ui_disconnect(self._session)
        if seq is not None:
            self._last_sent_seq = seq
            self._tracker.start("uiDisconnect", None, seq, now=time.time(), retryable=False)

    def _send_monitor(self, enabled: bool) -> None:
        """
        NAME
            _send_monitor - Toggle protocol monitor publishing on the robot.
        """
        if not self._tcp_connected:
            return
        if self._tracker.is_pending():
            self._append_output("Busy: wait for current command to finish.")
            return
        label = "uiMonitorEnable" if enabled else "uiMonitorDisable"
        ts = timestamp_hms()
        self._append_output(f"{ts} CMD {label}")
        args = {"enabled": enabled}
        self._last_cmd = (label, args)
        seq = ui_monitor(self._session, enabled)
        if seq is not None:
            self._last_sent_seq = seq
            self._tracker.start(label, args, seq, now=time.time())

    def _retry_last_command(self) -> None:
        """
        NAME
            _retry_last_command - Retry the last command after recovery.
        """
        cmd = self._tracker.take_retry()
        if cmd is None:
            return
        name, args = cmd
        if not name or name in ("uiHandshake", "uiDisconnect"):
            return
        ts = timestamp_hms()
        self._append_output(f"{ts} RETRY {name}")
        seq = self._send_tcp_command(name, args)
        if seq is not None:
            self._last_sent_seq = seq
            self._tracker.start(name, args, seq, now=time.time())

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
        if self._tracker.is_pending():
            self._append_output("Busy: wait for current command to finish.")
            return
        ts = timestamp_hms()
        self._append_output(f"{ts} CMD {command}")
        self._last_cmd = (command, None)
        seq = send_command(self._session, command, None)
        if seq is not None:
            self._last_sent_seq = seq
            self._tracker.start(command, None, seq, now=time.time())

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
        if self._tracker.is_pending():
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
        seq = select_test_by_name(self._session, name)
        if seq is not None:
            self._last_sent_seq = seq
            self._tracker.start("selectTestByName", {"name": name}, seq, now=time.time())

    def _poll_nt(self) -> None:
        """
        NAME
            _poll_nt - Poll TCP/NT inputs and update output log.
        """
        self._live_clock_var.set(time.strftime(LIVE_CLOCK_FORMAT))
        now = time.time()
        if not self._tcp_connected:
            if (now - self._last_connect_attempt) > 1.0:
                self._last_connect_attempt = now
                self._tcp_connected = connect(self._session)
        else:
            self._tcp_connected = connect(self._session)
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
            self._last_keepalive = 0.0
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
        if self._tracker.check_timeout(time.time()):
            self._notify_ui_failure(
                "cmd_timeout",
                True,
                "TIMEOUT waiting for ACK/OUT.",
                "Recovered: command responses received.",
            )
            self._handshake_inflight = False
        self._pending_label.configure(text=self._tracker.pending_text())
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
        if nt_connected and not self._tracker.is_pending():
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
            and not self._tracker.is_pending()
            and (time.time() - self._last_handshake_attempt) >= self._handshake_min_interval
        ):
            self._send_handshake(reset=False, log=False)
        if self._tcp_connected and not self._tracker.is_pending():
            if (now - self._last_keepalive) >= self._keepalive_interval:
                seq = ui_ping(self._session)
                if seq is not None:
                    self._last_keepalive = now
        if (
            self._tcp_connected
            and self._handshake_done
            and not self._log_poll_inflight
            and (now - self._last_log_poll) >= self._log_poll_interval
        ):
            seq = ui_poll_log(self._session)
            if seq is not None:
                self._log_poll_inflight = True
                self._log_poll_seq = seq
                self._last_log_poll = now
        self._poll_live_overlay(now)
        self._poll_presence_overrides()
        self._update_action_enabled()
        idle = (
            not self._tcp_connected
            and not self._nt_connected
            and not self._live_enabled_var.get()
            and not self._tracker.is_pending()
            and not self._log_poll_inflight
        )
        interval = self._poll_interval_idle if idle else self._poll_interval_active
        self.after(int(interval * 1000), self._poll_nt)

    def _poll_live_overlay(self, now: float) -> None:
        """
        NAME
            _poll_live_overlay - Poll runtime state for the live topology view.
        """
        if not self._live_enabled_var.get():
            return
        if self._runtime_state_pause_until is not None and now < self._runtime_state_pause_until:
            return
        if (now - self._runtime_state_last_poll) < (
            self._runtime_state_interval * self._runtime_state_backoff
        ):
            return
        self._runtime_state_last_poll = now
        source = self._live_source_var.get()
        if source == LIVE_SOURCE_FILE:
            return
        if not self._tcp_connected or not self._handshake_done:
            return
        if self._tracker.is_pending() or self._log_poll_inflight:
            return
        if self._runtime_state_pending_seq is None:
            seq = show_runtime_state(self._session, json_output=True)
            if seq is not None:
                self._runtime_state_pending_seq = int(seq)
                self._runtime_state_pending_at = now
        else:
            if (now - self._runtime_state_pending_at) > self._runtime_state_timeout_sec:
                self._runtime_state_pending_seq = None

    def _apply_runtime_state_payload(self, payload: Dict[str, Any]) -> None:
        """
        NAME
            _apply_runtime_state_payload - Apply live runtime-state JSON.
        """
        if self._live_view is None:
            return
        changed = self._live_view.update_runtime_state(payload)
        if changed:
            self._runtime_state_backoff = 1.0
            self._runtime_state_idle_count = 0
            self._runtime_state_pause_until = None
            return
        self._runtime_state_idle_count += 1
        if self._runtime_state_idle_count >= 3:
            self._runtime_state_backoff = min(8.0, self._runtime_state_backoff * 2.0)
            self._runtime_state_idle_count = 0
            self._runtime_state_pause_until = time.time() + self._runtime_state_idle_pause_sec

    def _handle_tcp_response(self, event: BridgeEvent) -> None:
        """
        NAME
            _handle_tcp_response - Handle an inbound TCP response payload.
        """
        msg_type = event.type
        name = event.name.strip()
        seq = event.seq
        if name.lower() == "uiping":
            return
        if msg_type in ("ack", "out") and self._is_handshake_required(event):
            self._handle_handshake_required()
            return
        if (
            self._runtime_state_pending_seq is not None
            and name.lower() == "showruntimestate"
            and int(seq) == int(self._runtime_state_pending_seq)
        ):
            if msg_type == "out":
                try:
                    payload = json.loads(event.json_text) if event.json_text else None
                except Exception:
                    payload = None
                if isinstance(payload, dict):
                    self._apply_runtime_state_payload(payload)
                self._runtime_state_pending_seq = None
                return
            if msg_type == "ack":
                return
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
            if name == "uiHandshake":
                self._handshake_done = True
                self._handshake_inflight = False
                self._retry_last_command()
        if msg_type in ("ack", "out"):
            self._tracker.handle_event(event)

    def _update_action_enabled(self) -> None:
        """
        NAME
            _update_action_enabled - Enable/disable UI actions based on state.
        """
        allow = (
            self._tcp_connected
            and self._handshake_done
            and not self._tracker.is_pending()
            and not self._state_stale
        )
        state = "normal" if allow else "disabled"
        for btn in getattr(self, "_action_buttons", []):
            btn.state(["!disabled"] if allow else ["disabled"])
        if hasattr(self, "_test_box"):
            self._test_box.configure(state=state)
        if self._reset_button is not None:
            self._reset_button.state(["!disabled"] if self._tcp_connected else ["disabled"])

    def _is_handshake_required(self, event: BridgeEvent) -> bool:
        """
        NAME
            _is_handshake_required - Check if a response indicates missing handshake.
        """
        if event is None:
            return False
        message = (event.message or "").strip()
        if message:
            return "UI handshake required before commands." in message
        text = (event.text or "").strip()
        if text:
            return "UI handshake required before commands." in text
        return False

    def _handle_handshake_required(self) -> None:
        """
        NAME
            _handle_handshake_required - Reset handshake state on server warning.
        """
        self._handshake_done = False
        self._handshake_inflight = False
        self._last_handshake_attempt = 0.0
        self._session.reset_handshake()
        self._log_poll_inflight = False
        self._log_poll_seq = None
        self._tracker.clear()
        now = time.time()
        if (now - self._handshake_warn_last) >= 2.0:
            self._handshake_warn_last = now
            self._notify_ui_failure(
                "handshake",
                True,
                "UI handshake required, resyncing.",
                "UI handshake OK.",
            )

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
            disconnect(self._session)
