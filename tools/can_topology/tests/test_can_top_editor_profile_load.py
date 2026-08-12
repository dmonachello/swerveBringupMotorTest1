from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import tools.can_topology.can_top_editor as can_top_editor
from tools.can_topology.can_top_editor import TopologyEditor
from tools.can_topology.can_top_models import GENERIC_CATEGORY, INTERFACE_CAN, INTERFACE_DIO, Node
from tools.common.profile_io import compute_profiles_hash
from tools.common.tests.config_api_test_helper import load_profiles_payload, write_profiles_payload
from tools.common.topology_draw import GROUP_OVERLAY_WIDTH, draw_group_overlays, draw_links
from tools.config.schema_store import ConfigSchemaStore, DOC_PROFILES


class _StringVarStub:
    """
    NAME
        _StringVarStub - Minimal StringVar stand-in for headless editor tests.
    """

    def __init__(self) -> None:
        self.value = ""

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = value

    def delete(self, *_args: object) -> None:
        self.value = ""

    def insert(self, _index: object, value: str) -> None:
        self.value = value

    def configure(self, **_kwargs: object) -> None:
        pass


class _BoolVarStub:
    def __init__(self, value: bool) -> None:
        self.value = value

    def get(self) -> bool:
        return self.value

    def set(self, value: bool) -> None:
        self.value = bool(value)


class _CanvasStub:
    """
    NAME
        _CanvasStub - Minimal canvas stand-in for viewport math tests.
    """

    def __init__(self, width: int = 1000, height: int = 500) -> None:
        self.width = width
        self.height = height
        self.xview_value = None
        self.yview_value = None
        self.xview_range = (0.2, 0.8)
        self.yview_range = (0.3, 0.9)
        self.scan_mark_args = None
        self.scan_dragto_args = None
        self.scrollregion = "0 0 1000 500"
        self.lines: list[dict[str, object]] = []
        self.texts: list[dict[str, object]] = []
        self.rectangles: list[dict[str, object]] = []
        self._next_item_id = 1

    def winfo_width(self) -> int:
        return self.width

    def winfo_height(self) -> int:
        return self.height

    def xview_moveto(self, value: float) -> None:
        self.xview_value = value

    def yview_moveto(self, value: float) -> None:
        self.yview_value = value

    def xview(self) -> tuple[float, float]:
        return self.xview_range

    def yview(self) -> tuple[float, float]:
        return self.yview_range

    def focus_set(self) -> None:
        pass

    def delete(self, _item: object) -> None:
        pass

    def create_rectangle(self, *_args: object, **_kwargs: object) -> int:
        item_id = self._next_item_id
        self._next_item_id += 1
        self.rectangles.append({"args": _args, "kwargs": _kwargs})
        return item_id

    def create_polygon(self, *_args: object, **_kwargs: object) -> int:
        item_id = self._next_item_id
        self._next_item_id += 1
        return item_id

    def create_text(self, *_args: object, **_kwargs: object) -> int:
        item_id = self._next_item_id
        self._next_item_id += 1
        self.texts.append({"args": _args, "kwargs": _kwargs})
        return item_id

    def create_line(self, *args: object, **kwargs: object) -> int:
        item_id = self._next_item_id
        self._next_item_id += 1
        self.lines.append({"args": args, "kwargs": kwargs})
        return item_id

    def addtag_withtag(self, *_args: object) -> None:
        pass

    def tag_lower(self, *_args: object) -> None:
        pass

    def tag_raise(self, *_args: object) -> None:
        pass

    def scan_mark(self, x: int, y: int) -> None:
        self.scan_mark_args = (x, y)

    def scan_dragto(self, x: int, y: int, gain: int = 10) -> None:
        self.scan_dragto_args = (x, y, gain)

    def cget(self, key: str) -> str:
        if key == "scrollregion":
            return self.scrollregion
        return ""

    def configure(self, **kwargs: object) -> None:
        if "scrollregion" in kwargs:
            value = kwargs["scrollregion"]
            if isinstance(value, tuple):
                self.scrollregion = " ".join(str(part) for part in value)
            else:
                self.scrollregion = str(value)

    def canvasx(self, value: float) -> float:
        return float(value)

    def canvasy(self, value: float) -> float:
        return float(value)

    def find_overlapping(self, *_args: object) -> tuple[()]:
        return ()

    def gettags(self, _item: object) -> tuple[()]:
        return ()


class _WheelEventStub:
    """
    NAME
        _WheelEventStub - Minimal mouse-wheel event stand-in.
    """

    def __init__(
        self, delta: int = 0, num: int | None = None, x: int = 0, y: int = 0
    ) -> None:
        self.delta = delta
        self.num = num
        self.x = x
        self.y = y


class _PointerEventStub:
    """
    NAME
        _PointerEventStub - Minimal pointer event stand-in.
    """

    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y


class _ReleaseEventStub:
    """
    NAME
        _ReleaseEventStub - Minimal mouse-release event stand-in.
    """

    pass


class _ComboStub:
    """
    NAME
        _ComboStub - Minimal combobox stand-in for profile choice tests.
    """

    def __init__(self) -> None:
        self.values: list[str] = []

    def __getitem__(self, key: str) -> list[str]:
        if key != "values":
            raise KeyError(key)
        return self.values

    def __setitem__(self, key: str, value: object) -> None:
        if key != "values":
            raise KeyError(key)
        self.values = list(value) if isinstance(value, list) else list(value or [])


class _ConfigSchemaStoreBlankStub:
    """
    NAME
        _ConfigSchemaStoreBlankStub - Store stub that returns synthesized blank profiles payload.
    """

    def load(self, _repo_root: Path | None = None) -> list[str]:
        return []

    def root_payload(self) -> dict[str, object]:
        return {
            "schema_version": 5,
            "data_version": "",
            "data_hash": "blank",
            "default_profile": "",
            "devices": [],
            "profiles": {},
            "topology": {"version": 1, "source": "local", "profiles": {}},
            "bridgeConfig": {"schema_version": 1, "generatedAt": None, "byProfile": {}},
        }


class _TreeviewStub:
    """
    NAME
        _TreeviewStub - Minimal Treeview stand-in for node list tests.
    """

    def __init__(self) -> None:
        self.columns = ("can_id", "type", "label", "group", "tags", "profiles")
        self.items: dict[str, tuple[object, ...]] = {}
        self.selected: list[str] = []

    def __getitem__(self, key: str) -> tuple[str, ...]:
        if key != "columns":
            raise KeyError(key)
        return self.columns

    def get_children(self) -> list[str]:
        return list(self.items.keys())

    def delete(self, item: str) -> None:
        self.items.pop(item, None)
        self.selected = [selected for selected in self.selected if selected != item]

    def insert(self, _parent: str, _index: str, iid: str, values: tuple[object, ...]) -> None:
        self.items[iid] = values

    def selection(self) -> tuple[str, ...]:
        return tuple(self.selected)

    def selection_add(self, item: str) -> None:
        if item not in self.selected:
            self.selected.append(item)

    def selection_remove(self, item: str) -> None:
        self.selected = [selected for selected in self.selected if selected != item]

    def exists(self, item: str) -> bool:
        return item in self.items

    def see(self, _item: str) -> None:
        pass

    def set(self, row_id: str, column_name: str) -> str:
        values = self.items[row_id]
        index = self.columns.index(column_name)
        return str(values[index])

    def identify_row(self, _y: object) -> str:
        return next(iter(self.items.keys()), "")


class _PanelStub:
    """
    NAME
        _PanelStub - Minimal details panel stand-in.
    """

    def __init__(self) -> None:
        self.pack_forget_calls = 0

    def pack_forget(self) -> None:
        self.pack_forget_calls += 1


class _MessageBoxStub:
    """
    NAME
        _MessageBoxStub - Non-interactive messagebox replacement.
    """

    @staticmethod
    def showinfo(*_args: object, **_kwargs: object) -> None:
        pass

    @staticmethod
    def showerror(*args: object, **_kwargs: object) -> None:
        message = args[1] if len(args) > 1 else "messagebox error"
        raise RuntimeError(str(message))

    @staticmethod
    def askyesno(*_args: object, **_kwargs: object) -> bool:
        return True


class _DialogStub:
    """
    NAME
        _DialogStub - Minimal toplevel stand-in for bulk-edit tests.
    """

    def title(self, *_args: object) -> None:
        pass

    def resizable(self, *_args: object) -> None:
        pass

    def transient(self, *_args: object) -> None:
        pass

    def grab_set(self) -> None:
        pass

    def destroy(self) -> None:
        pass


class _TkVarStub:
    """
    NAME
        _TkVarStub - Minimal Tk variable stand-in.
    """

    instances: list["_TkVarStub"] = []

    def __init__(self, value: object = "") -> None:
        self.value = value
        self.__class__.instances.append(self)

    def get(self) -> object:
        return self.value

    def set(self, value: object) -> None:
        self.value = value


class _WidgetStub:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        pass

    def grid(self, *_args: object, **_kwargs: object) -> None:
        pass

    def pack(self, *_args: object, **_kwargs: object) -> None:
        pass


class _ComboboxStub(_WidgetStub):
    """
    NAME
        _ComboboxStub - Minimal combobox stand-in for bulk-edit tests.
    """

    instances: list["_ComboboxStub"] = []

    def __init__(self, *_args: object, textvariable: object = None, **_kwargs: object) -> None:
        super().__init__()
        self.value = ""
        self.textvariable = textvariable
        self.__class__.instances.append(self)

    def set(self, value: str) -> None:
        self.value = value
        if self.textvariable is not None and hasattr(self.textvariable, "set"):
            self.textvariable.set(value)

    def get(self) -> str:
        if self.textvariable is not None and hasattr(self.textvariable, "get"):
            return str(self.textvariable.get())
        return self.value


class _ButtonStub(_WidgetStub):
    """
    NAME
        _ButtonStub - Minimal button stand-in that captures commands.
    """

    commands_by_text: dict[str, object] = {}

    def __init__(self, *_args: object, text: str = "", command: object = None, **_kwargs: object) -> None:
        super().__init__()
        self.commands_by_text[text] = command


class TopologyEditorProfileLoadTests(unittest.TestCase):
    """
    NAME
        TopologyEditorProfileLoadTests - Validate profile-to-node loading helpers.
    """

    def test_empty_diagram_snapshot_is_not_layout_content(self) -> None:
        self.assertFalse(TopologyEditor._diagram_has_saved_content({}))

    def test_minimal_diagram_snapshot_is_layout_content(self) -> None:
        self.assertTrue(TopologyEditor._diagram_has_saved_content({"nodes": [{"key": 1}]}))

    def test_minimal_topology_snapshot_is_layout_content(self) -> None:
        self.assertTrue(
            TopologyEditor._topology_has_saved_content(
                {
                    "nodes": [
                        {"key": 1, "objectType": "device", "nodeType": "device", "deviceRef": "motor1"}
                    ],
                    "edges": [],
                }
            )
        )

    @staticmethod
    def _repo_root() -> Path:
        return Path(__file__).resolve().parents[3]

    @classmethod
    def _regression_fixture_path(cls, profile_name: str, filename: str) -> Path:
        return (
            cls._repo_root()
            / "tests"
            / "regression"
            / "fixtures"
            / "config_catalog"
            / profile_name
            / filename
        )

    @staticmethod
    def _canonical_roundtrip_payload(editor: TopologyEditor) -> dict[str, object]:
        payload = {
            "profile": editor._profile_from_nodes(),
            "topology": editor._topology_snapshot(),
            "devices": editor._device_registry_list,
            "default": editor._default_profile_name,
        }
        return json.loads(json.dumps(payload, sort_keys=True, separators=(",", ":")))

    @staticmethod
    def _headless_editor(profile_name: str) -> TopologyEditor:
        editor = TopologyEditor.__new__(TopologyEditor)
        editor._node_details_panel = _PanelStub()
        editor._callout_details_panel = _PanelStub()
        editor.entry_profile = _StringVarStub()
        editor.entry_profile.set(profile_name)
        editor.profile_combo = _ComboStub()
        editor._profile_pick_var = _StringVarStub()
        editor._profile_pick_var.set(profile_name)
        editor.node_list = _TreeviewStub()
        editor._callout_scale_var = _StringVarStub()
        editor._zoom_label_var = _StringVarStub()
        editor.var_set_default = _BoolVarStub(True)
        editor._list_scope_var = _StringVarStub()
        editor._list_scope_var.set("Current Profile")
        editor.canvas = _CanvasStub(width=1600, height=900)
        editor._connection_filter_vars = {
            key: _BoolVarStub(True)
            for key in ("can", "power", "dio", "pwm", "analog", "virtual")
        }
        editor._ethernet_links = []
        editor._can_bus_links = []
        editor._cannect_device_links = []
        editor._attachment_links = []
        editor._power_links = []
        editor._neighbor_links = []
        editor._neighbor_ports = []
        editor._dio_wiring_links = []
        editor._root_extras = {}
        editor._nodes = []
        editor._device_registry = {}
        editor._device_registry_list = []
        editor._non_topology_profile_labels = []
        editor._pending_global_device_deletions = set()
        editor._selected_inventory_label = None
        editor._next_key = 1
        editor._next_callout = 1
        editor._selected_nodes = set()
        editor._selected_buses = set()
        editor._selected_key = None
        editor._profile_name = profile_name
        editor._default_profile_name = profile_name
        editor._profile_source_path = ""
        editor._profile_names = []
        editor._dirty = False
        editor._inline_editor = None
        editor._tag_filter_fn = None
        editor._list_sort_var = _StringVarStub()
        editor._list_sort_var.set("can_id")
        editor._bus_offsets = [0.0]
        editor._bus_lefts = [40.0]
        editor._bus_rights = [520.0]
        editor._bus_connectors = []
        editor._bus_connector_sides = []
        editor._bus_spacing = 160.0
        editor._layout_width = 0.0
        editor._pan_y = 0.0
        editor._zoom = 1.0
        editor._box_w = 90
        editor._box_h = 34
        editor._last_base_y = None
        editor._details_layout_shift = False
        editor._neighbors_dirty = False
        editor._pending_fit_to_window = False
        editor._drag_free_y = {}
        editor._bus_connector_regions = []
        editor._syncing_selection = False
        editor._refresh_list = lambda: None
        editor._update_details_panel = lambda _node: None
        editor._layout_even = lambda: None
        editor._redraw_canvas = lambda: None
        editor._refresh_neighbor_status = lambda: None
        editor._refresh_profile_choices = lambda keep_selection=True: None
        editor._confirm_can_id_collisions = lambda nodes=None: True
        editor._confirm_terminators = lambda nodes=None: True
        editor._confirm_dio_warnings = lambda: True
        editor._confirm_neighbors_current_for_save = lambda: True
        editor.state = lambda *_args: None
        editor.update_idletasks = lambda: None
        return editor

    def test_canvas_release_without_drag_does_not_redraw(self) -> None:
        editor = self._headless_editor("robot_2026_swerve")
        redraw_calls: list[str] = []
        mark_neighbors_calls: list[str] = []
        maybe_link_calls: list[object] = []
        editor._selection_rect = None
        editor._selection_start = None
        editor._dragging_active = False
        editor._drag_state = None
        editor._pan_drag = None
        editor._bus_drag = None
        editor._bus_resize = None
        editor._bus_connector_drag = None
        editor._multi_drag = None
        editor._drag_undo_pending = False
        editor._drag_free_y = {}
        editor._selected_key = None
        editor._clear_guides = lambda: None
        editor._mark_neighbors_stale = lambda: mark_neighbors_calls.append("mark")
        editor._maybe_link_dragged_device_to_cannect = (
            lambda key: maybe_link_calls.append(key)
        )
        editor._redraw_canvas = lambda: redraw_calls.append("redraw")

        editor._on_canvas_release(_ReleaseEventStub())

        self.assertEqual([], redraw_calls)
        self.assertEqual([], mark_neighbors_calls)
        self.assertEqual([], maybe_link_calls)

    def test_zoom_step_preserves_anchor_point(self) -> None:
        editor = self._headless_editor("robot_2026_swerve")
        editor.canvas = _CanvasStub(width=1000, height=500)
        editor._zoom = 1.0
        editor._pan_y = 0.0
        editor._zoom_label_var = _StringVarStub()
        editor._redraw_canvas = lambda: None

        editor._zoom_step(0.1, anchor_x=250.0, anchor_y=125.0)

        self.assertEqual(editor._zoom, 1.1)
        self.assertIsNotNone(editor.canvas.xview_value)
        self.assertIsNotNone(editor.canvas.yview_value)

    def test_robot_2026_swerve_save_restart_roundtrip_retains_values(self) -> None:
        profile_name = "robot_2026_swerve"
        source_path = self._regression_fixture_path(profile_name, "bringup_system.json")
        if not source_path.exists():
            self.skipTest(f"Missing regression fixture: {source_path}")
        original_messagebox = can_top_editor.messagebox
        can_top_editor.messagebox = _MessageBoxStub
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir) / "bringup_system.json"
                shutil.copy2(source_path, temp_path)
                before_editor = self._headless_editor(profile_name)
                before_editor._load_profile_from_path(
                    str(source_path),
                    ask_profile=False,
                    confirm_discard=False,
                    selected_name=profile_name,
                )
                before_payload = self._canonical_roundtrip_payload(before_editor)

                before_editor.entry_profile.set(profile_name)
                before_editor.var_set_default.set(True)
                before_editor._save_profile_to_path(
                    temp_path,
                    prompt_replace=False,
                    update_source=True,
                )

                after_editor = self._headless_editor(profile_name)
                after_editor._load_profile_from_path(
                    str(temp_path),
                    ask_profile=False,
                    confirm_discard=False,
                    selected_name=profile_name,
                )
                after_payload = self._canonical_roundtrip_payload(after_editor)
        finally:
            can_top_editor.messagebox = original_messagebox

        self.assertEqual(before_payload, after_payload)

    def test_save_profile_preserves_dsl_test_set_metadata(self) -> None:
        profile_name = "test_minimal_25_9"
        payload = {
            "schema_version": 5,
            "data_version": "test_fixture",
            "data_hash": "",
            "default_profile": profile_name,
            "profiles": {
                profile_name: {
                    "devices": ["SPARKMAX/NEO 25", "controller0"],
                    "dslTestSet": "test_minimal_25_9",
                }
            },
            "devices": [
                {
                    "label": "SPARKMAX/NEO 25",
                    "deviceInterface": "CAN",
                    "manufacturer": 5,
                    "deviceType": 2,
                    "id": 25,
                    "model": "REV NEO",
                    "type": "motor",
                },
                {
                    "label": "controller0",
                    "deviceInterface": "USB",
                    "id": 0,
                    "model": "Xbox Controller",
                    "type": "xboxController",
                },
            ],
        }
        payload["data_hash"] = compute_profiles_hash(payload)
        original_messagebox = can_top_editor.messagebox
        can_top_editor.messagebox = _MessageBoxStub
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir) / "bringup_system.json"
                write_profiles_payload(temp_path, payload, stamp=False)
                editor = self._headless_editor(profile_name)
                editor._load_profile_from_path(
                    str(temp_path),
                    ask_profile=False,
                    confirm_discard=False,
                    selected_name=profile_name,
                )
                editor.entry_profile.set(profile_name)
                editor.var_set_default.set(True)
                editor._save_profile_to_path(
                    temp_path,
                    prompt_replace=False,
                    update_source=True,
                )
                saved = load_profiles_payload(temp_path)
        finally:
            can_top_editor.messagebox = original_messagebox

        self.assertEqual(
            "test_minimal_25_9",
            saved["profiles"][profile_name]["dslTestSet"],
        )

    def test_editor_set_component_values_validate_and_roundtrip(self) -> None:
        profile_name = "component_values"
        original_messagebox = can_top_editor.messagebox
        can_top_editor.messagebox = _MessageBoxStub
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir) / "bringup_system.json"
                editor = self._headless_editor(profile_name)
                editor._nodes = [
                    Node(
                        key=1,
                        category="roborio",
                        label="roborio",
                        can_id=0,
                        interface=INTERFACE_CAN,
                        vendor="NI",
                        device_type="RobotController",
                        motor="NI roboRIO",
                        terminator=True,
                        x=100.0,
                        free_y=-75.0,
                        tags=["controller"],
                    ),
                    Node(
                        key=2,
                        category="krakens",
                        label="driveMotor",
                        can_id=7,
                        interface=INTERFACE_CAN,
                        vendor="CTRE",
                        device_type="Kraken X60",
                        motor="Kraken X60",
                        terminator=False,
                        x=250.0,
                        free_y=125.0,
                        tags=["swerve", "drive"],
                    ),
                    Node(
                        key=3,
                        category="devices",
                        label="limit0",
                        can_id=-1,
                        interface=INTERFACE_DIO,
                        device_type="limitSwitch",
                        dio=4,
                        invert=True,
                        x=350.0,
                        free_y=175.0,
                        tags=["limit"],
                    ),
                ]
                editor._bus_offsets = [0.0]
                editor._bus_lefts = [40.0]
                editor._bus_rights = [520.0]
                editor._bus_connectors = []
                editor._pan_y = 22.0
                editor._zoom = 1.25
                editor.entry_profile.set(profile_name)
                editor.var_set_default.set(True)

                editor._save_profile_to_path(temp_path, prompt_replace=False, update_source=True)
                saved_payload = load_profiles_payload(temp_path)
                store = ConfigSchemaStore()
                store._db.set_payload(DOC_PROFILES, saved_payload)
                validation = store.validate(strict=True)
                self.assertTrue(validation.ok(), [issue.message for issue in validation.errors()])

                reloaded = self._headless_editor(profile_name)
                reloaded._load_profile_from_path(
                    str(temp_path),
                    ask_profile=False,
                    confirm_discard=False,
                    selected_name=profile_name,
                )
                entries = {entry["label"]: entry for entry in reloaded._device_registry_list}
                topology_nodes = {
                    node["deviceRef"]: node
                    for node in reloaded._topology_snapshot()["nodes"]
                    if node.get("nodeType") == "device"
                }
        finally:
            can_top_editor.messagebox = original_messagebox

        self.assertEqual(entries["roborio"]["deviceInterface"], "CAN")
        self.assertEqual(entries["roborio"]["manufacturer"], 1)
        self.assertEqual(entries["roborio"]["deviceType"], 1)
        self.assertEqual(entries["roborio"]["id"], 0)
        self.assertEqual(entries["roborio"]["model"], "NI roboRIO")
        self.assertTrue(entries["roborio"]["terminator"])
        self.assertEqual(entries["driveMotor"]["deviceInterface"], "CAN")
        self.assertEqual(entries["driveMotor"]["manufacturer"], 4)
        self.assertEqual(entries["driveMotor"]["deviceType"], 2)
        self.assertEqual(entries["driveMotor"]["id"], 7)
        self.assertEqual(entries["driveMotor"]["model"], "Kraken X60")
        self.assertFalse(entries["driveMotor"]["terminator"])
        self.assertEqual(entries["driveMotor"]["tags"], ["swerve", "drive"])
        self.assertEqual(entries["limit0"]["deviceInterface"], "DIO")
        self.assertEqual(entries["limit0"]["id"], 4)
        self.assertTrue(entries["limit0"]["invert"])
        self.assertEqual(entries["limit0"]["type"], "limitSwitch")
        self.assertEqual(entries["limit0"]["tags"], ["limit"])
        self.assertEqual(topology_nodes["driveMotor"]["layout"]["x"], 250.0)
        self.assertEqual(topology_nodes["driveMotor"]["layout"]["y"], 125.0)
        self.assertTrue(topology_nodes["driveMotor"]["layout"]["yRelative"])

    def test_topology_view_and_callouts_roundtrip_retains_links_and_filters(self) -> None:
        profile_name = "view_and_callouts"
        original_messagebox = can_top_editor.messagebox
        can_top_editor.messagebox = _MessageBoxStub
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir) / "bringup_system.json"
                editor = self._headless_editor(profile_name)
                can_filter = editor._connection_filter_vars["can"]
                power_filter = editor._connection_filter_vars["power"]
                dio_filter = editor._connection_filter_vars["dio"]
                pwm_filter = editor._connection_filter_vars["pwm"]
                analog_filter = editor._connection_filter_vars["analog"]
                virtual_filter = editor._connection_filter_vars["virtual"]
                can_filter.set(True)
                power_filter.set(True)
                dio_filter.set(False)
                pwm_filter.set(False)
                analog_filter.set(False)
                virtual_filter.set(False)
                editor._nodes = [
                    Node(
                        key=1,
                        category="roborio",
                        label="roborio",
                        can_id=0,
                        interface=INTERFACE_CAN,
                        vendor="NI",
                        device_type="RobotController",
                        motor="NI roboRIO",
                        x=100.0,
                    ),
                    Node(
                        key=2,
                        category="krakens",
                        label="driveMotor",
                        can_id=7,
                        interface=INTERFACE_CAN,
                        vendor="CTRE",
                        device_type="Kraken X60",
                        motor="Kraken X60",
                        x=280.0,
                    ),
                    Node(
                        key=3,
                        category="cannect_direct",
                        label="cannect 2",
                        can_id=-1,
                        node_type="diagram",
                        interface=INTERFACE_CAN,
                        vendor="SWYFT",
                        motor="Wiring",
                        x=180.0,
                        row=1,
                        bus_index=0,
                        profile_visible=False,
                    ),
                    Node(
                        key=4,
                        category="callout",
                        label="Check CAN",
                        can_id=-1,
                        node_type="callout",
                        x=320.0,
                        row=1,
                        bus_index=1,
                        callout_text="Check CAN",
                        callout_target_type="node",
                        callout_target_node_key=2,
                        callout_target_category="krakens",
                        callout_target_label="driveMotor",
                        callout_target_id=7,
                        callout_y=210.0,
                        free_y=210.0,
                        scale=1.2,
                        tags=["note"],
                        profile_visible=False,
                    ),
                ]
                editor._bus_offsets = [0.0, 170.0]
                editor._bus_lefts = [40.0, 80.0]
                editor._bus_rights = [420.0, 460.0]
                editor._bus_connectors = [True]
                editor._pan_y = 31.0
                editor._zoom = 1.4
                editor._ethernet_links = [(1, 3)]
                editor._can_bus_links = [
                    {"node": 3, "bus": 0, "port": 1},
                    {"node": 3, "bus": 1, "port": 2},
                ]
                editor._cannect_device_links = [{"node": 3, "device": 2, "port": 2}]
                editor._attachment_links = []
                editor._power_links = []
                editor._neighbor_links = [{"a": 1, "b": 2}]
                editor._neighbor_ports = [
                    {"node": 1, "port": "right", "neighbor": 2, "neighborPort": "left"},
                    {"node": 2, "port": "left", "neighbor": 1, "neighborPort": "right"},
                ]
                editor._dio_wiring_links = []
                editor.entry_profile.set(profile_name)
                editor.var_set_default.set(True)

                editor._save_profile_to_path(temp_path, prompt_replace=False, update_source=True)

                reloaded = self._headless_editor(profile_name)
                reloaded._load_profile_from_path(
                    str(temp_path),
                    ask_profile=False,
                    confirm_discard=False,
                    selected_name=profile_name,
                )
                topology = reloaded._topology_snapshot()
                view = topology["view"]
                callouts = view["callouts"]
        finally:
            can_top_editor.messagebox = original_messagebox

        self.assertEqual(reloaded._bus_offsets, [0.0, 170.0])
        self.assertEqual(reloaded._bus_lefts, [40.0, 80.0])
        self.assertEqual(reloaded._bus_rights, [420.0, 460.0])
        self.assertEqual(reloaded._bus_connectors, [True])
        self.assertEqual(reloaded._pan_y, 31.0)
        self.assertEqual(reloaded._zoom, 1.4)
        self.assertEqual(reloaded._ethernet_links, [(1, 3)])
        self.assertEqual(
            reloaded._can_bus_links,
            [{"node": 3, "bus": 0, "port": 1}, {"node": 3, "bus": 1, "port": 2}],
        )
        self.assertEqual(reloaded._cannect_device_links, [{"node": 3, "device": 2, "port": 2}])
        self.assertEqual(reloaded._active_connection_filters(), {"can", "power"})
        self.assertEqual(len(callouts), 1)
        self.assertEqual(callouts[0]["text"], "Check CAN")
        self.assertEqual(callouts[0]["targetNodeKey"], 2)
        self.assertEqual(callouts[0]["targetLabel"], "driveMotor")
        self.assertEqual(callouts[0]["targetId"], 7)
        self.assertEqual(callouts[0]["freeY"], 210.0)
        self.assertTrue(callouts[0]["freeYRelative"])

    def test_set_bus_connector_side_updates_saved_view_metadata(self) -> None:
        editor = self._headless_editor("bus_connector_side")
        editor._bus_offsets = [0.0, 160.0]
        editor._bus_lefts = [40.0, 60.0]
        editor._bus_rights = [420.0, 440.0]
        editor._bus_connectors = [True]
        editor._bus_connector_sides = []

        editor._ensure_bus_connector_sides(len(editor._bus_offsets))
        self.assertEqual(editor._bus_connector_side(0), "right")

        editor._set_bus_connector_side(0, "left")
        snapshot = editor._topology_snapshot()
        view = snapshot["view"]

        self.assertEqual(editor._bus_connector_side(0), "left")
        self.assertEqual(view["busConnectorSides"], ["left"])
        self.assertEqual(editor._bus_lefts[0], editor._bus_lefts[1])

    def test_validate_nodes_names_generic_device_missing_vendor_type(self) -> None:
        editor = self._headless_editor("generic_validation")
        editor._nodes = [
            Node(
                key=1,
                category=GENERIC_CATEGORY,
                label="mysteryThing",
                can_id=9,
                interface=INTERFACE_CAN,
                vendor="",
                device_type="",
            )
        ]

        validation_error = editor._validate_nodes()

        self.assertEqual(
            validation_error,
            "Generic device 'mysteryThing' requires vendor and device type.",
        )

    def test_bulk_edit_names_generic_device_missing_vendor_type(self) -> None:
        editor = self._headless_editor("bulk_generic_validation")
        editor._nodes = [
            Node(
                key=1,
                category="krakens",
                label="mysteryThing",
                can_id=9,
                interface=INTERFACE_CAN,
                vendor="",
                device_type="",
            )
        ]
        editor._selected_nodes = {1}
        editor._push_undo = lambda: None
        editor._device_nodes = TopologyEditor._device_nodes.__get__(editor, TopologyEditor)
        editor._normalize_tags = lambda value: list(value) if isinstance(value, list) else []
        editor._normalize_limits = lambda value: value

        original_toplevel = can_top_editor.tk.Toplevel
        original_boolvar = can_top_editor.tk.BooleanVar
        original_stringvar = can_top_editor.tk.StringVar
        original_frame = can_top_editor.ttk.Frame
        original_label = can_top_editor.ttk.Label
        original_checkbutton = can_top_editor.ttk.Checkbutton
        original_combobox = can_top_editor.ttk.Combobox
        original_entry = can_top_editor.ttk.Entry
        original_button = can_top_editor.ttk.Button
        original_messagebox = can_top_editor.messagebox
        _TkVarStub.instances = []
        _ComboboxStub.instances = []
        _ButtonStub.commands_by_text = {}
        can_top_editor.tk.Toplevel = lambda *_args, **_kwargs: _DialogStub()
        can_top_editor.tk.BooleanVar = _TkVarStub
        can_top_editor.tk.StringVar = _TkVarStub
        can_top_editor.ttk.Frame = _WidgetStub
        can_top_editor.ttk.Label = _WidgetStub
        can_top_editor.ttk.Checkbutton = _WidgetStub
        can_top_editor.ttk.Combobox = _ComboboxStub
        can_top_editor.ttk.Entry = _WidgetStub
        can_top_editor.ttk.Button = _ButtonStub
        can_top_editor.messagebox = _MessageBoxStub
        try:

            def wait_window(_dialog: object) -> None:
                _TkVarStub.instances[0].set(True)
                _ComboboxStub.instances[0].set(GENERIC_CATEGORY)
                ok = _ButtonStub.commands_by_text["OK"]
                ok()

            editor.wait_window = wait_window

            with self.assertRaisesRegex(
                RuntimeError,
                "Generic device 'mysteryThing' requires vendor and device type.",
            ):
                editor._bulk_edit_selection()
        finally:
            can_top_editor.tk.Toplevel = original_toplevel
            can_top_editor.tk.BooleanVar = original_boolvar
            can_top_editor.tk.StringVar = original_stringvar
            can_top_editor.ttk.Frame = original_frame
            can_top_editor.ttk.Label = original_label
            can_top_editor.ttk.Checkbutton = original_checkbutton
            can_top_editor.ttk.Combobox = original_combobox
            can_top_editor.ttk.Entry = original_entry
            can_top_editor.ttk.Button = original_button
            can_top_editor.messagebox = original_messagebox

    def test_node_groups_by_label_maps_bridge_group_memberships(self) -> None:
        editor = self._headless_editor("group_memberships")
        editor._root_extras = {
            "bridgeConfig": {
                "byProfile": {
                    "group_memberships": {
                        "groups": [
                            {
                                "name": "leftModule",
                                "members": [{"label": "frontLeft Drive Motor", "enabled": True}],
                            },
                            {
                                "name": "rightModule",
                                "members": ["frontRight Drive Motor"],
                            },
                            {
                                "name": "drive",
                                "members": [
                                    {"label": "frontLeft Drive Motor", "enabled": True},
                                    {"label": "frontRight Drive Motor", "enabled": True},
                                ],
                            },
                        ]
                    }
                }
            }
        }
        editor._profile_name = "group_memberships"

        groups = editor._node_groups_by_label()

        self.assertEqual(groups["frontLeft Drive Motor"], ["leftModule", "drive"])
        self.assertEqual(groups["frontRight Drive Motor"], ["rightModule", "drive"])

    def test_profile_from_nodes_preserves_non_topology_controller_labels(self) -> None:
        editor = self._headless_editor("controller_profile")
        editor._nodes = [
            Node(
                key=1,
                category="krakens",
                label="frontLeft Drive Motor",
                can_id=2,
                interface=INTERFACE_CAN,
            )
        ]
        editor._non_topology_profile_labels = ["controller0"]

        profile = TopologyEditor._profile_from_nodes(editor)

        self.assertEqual(profile["devices"], ["frontLeft Drive Motor", "controller0"])

    def test_refresh_list_includes_non_topology_controller_rows(self) -> None:
        editor = self._headless_editor("controller_list")
        editor._refresh_list = TopologyEditor._refresh_list.__get__(editor, TopologyEditor)
        editor._device_nodes = TopologyEditor._device_nodes.__get__(editor, TopologyEditor)
        editor._node_groups_by_label = TopologyEditor._node_groups_by_label.__get__(editor, TopologyEditor)
        editor._tags_to_string = TopologyEditor._tags_to_string.__get__(editor, TopologyEditor)
        editor._normalize_tags = TopologyEditor._normalize_tags.__get__(editor, TopologyEditor)
        editor._inventory_entry_for_label = TopologyEditor._inventory_entry_for_label.__get__(editor, TopologyEditor)
        editor._destroy_inline_editor = lambda: None
        editor._nodes = []
        editor._device_registry_list = [
            {
                "label": "controller0",
                "deviceInterface": "USB",
                "id": 0,
                "model": "Xbox Controller",
                "type": "xboxController",
            }
        ]
        editor._device_registry = {"controller0": editor._device_registry_list[0]}
        editor._non_topology_profile_labels = ["controller0"]

        editor._refresh_list()

        self.assertIn("inventory:controller0", editor.node_list.items)
        self.assertEqual(
            editor.node_list.items["inventory:controller0"][2],
            "controller0",
        )

    def test_refresh_list_includes_out_of_profile_registry_device_rows(self) -> None:
        editor = self._headless_editor("inventory_scope")
        editor._refresh_list = TopologyEditor._refresh_list.__get__(editor, TopologyEditor)
        editor._device_nodes = TopologyEditor._device_nodes.__get__(editor, TopologyEditor)
        editor._node_groups_by_label = TopologyEditor._node_groups_by_label.__get__(editor, TopologyEditor)
        editor._profiles_by_label = TopologyEditor._profiles_by_label.__get__(editor, TopologyEditor)
        editor._tags_to_string = TopologyEditor._tags_to_string.__get__(editor, TopologyEditor)
        editor._normalize_tags = TopologyEditor._normalize_tags.__get__(editor, TopologyEditor)
        editor._inventory_entry_for_label = TopologyEditor._inventory_entry_for_label.__get__(editor, TopologyEditor)
        editor._destroy_inline_editor = lambda: None
        editor._nodes = [
            Node(
                key=1,
                category="krakens",
                label="frontLeft Drive Motor",
                can_id=2,
                interface=INTERFACE_CAN,
            )
        ]
        editor._device_registry_list = [
            {
                "label": "frontLeft Drive Motor",
                "deviceInterface": "CAN",
                "id": 2,
                "manufacturer": 4,
                "deviceType": 2,
                "model": "Kraken X60",
            },
            {
                "label": "backLeft Drive Motor",
                "deviceInterface": "CAN",
                "id": 5,
                "manufacturer": 4,
                "deviceType": 2,
                "model": "Kraken X60",
            },
        ]
        editor._device_registry = {
            entry["label"]: entry for entry in editor._device_registry_list
        }
        editor._list_scope_var.set("Full Config")
        editor._profile_source_path = ""
        editor._profile_name = "inventory_scope"
        editor._default_profiles_path = lambda: Path("does_not_exist.json")
        editor._non_topology_profile_labels = []

        editor._refresh_list()

        self.assertIn("1", editor.node_list.items)
        self.assertIn("inventory:backLeft Drive Motor", editor.node_list.items)
        self.assertEqual(
            editor.node_list.items["inventory:backLeft Drive Motor"][0],
            "5",
        )
        self.assertEqual(
            editor.node_list.items["1"][5],
            "inventory_scope",
        )
        self.assertEqual(
            editor.node_list.items["inventory:backLeft Drive Motor"][5],
            "",
        )

    def test_refresh_list_full_config_shows_profiles_column_for_shared_inventory(self) -> None:
        editor = self._headless_editor("inventory_profiles_column")
        editor._refresh_list = TopologyEditor._refresh_list.__get__(editor, TopologyEditor)
        editor._device_nodes = TopologyEditor._device_nodes.__get__(editor, TopologyEditor)
        editor._node_groups_by_label = TopologyEditor._node_groups_by_label.__get__(editor, TopologyEditor)
        editor._profiles_by_label = TopologyEditor._profiles_by_label.__get__(editor, TopologyEditor)
        editor._topology_inventory_entries = TopologyEditor._topology_inventory_entries.__get__(editor, TopologyEditor)
        editor._full_config_inventory_entries = TopologyEditor._full_config_inventory_entries.__get__(
            editor, TopologyEditor
        )
        editor._tags_to_string = TopologyEditor._tags_to_string.__get__(editor, TopologyEditor)
        editor._normalize_tags = TopologyEditor._normalize_tags.__get__(editor, TopologyEditor)
        editor._inventory_entry_for_label = TopologyEditor._inventory_entry_for_label.__get__(editor, TopologyEditor)
        editor._destroy_inline_editor = lambda: None
        editor._nodes = []
        editor._device_registry_list = [
            {
                "label": "Motor 25",
                "deviceInterface": "CAN",
                "id": 25,
                "manufacturer": 5,
                "deviceType": 2,
                "model": "REV NEO",
            }
        ]
        editor._device_registry = {"Motor 25": editor._device_registry_list[0]}
        editor._list_scope_var.set("Full Config")
        editor._profile_name = "current_profile"
        editor._non_topology_profile_labels = []
        editor._profile_source_path = ""
        editor._default_profiles_path = lambda: Path("does_not_exist.json")
        original_load_config_payload = TopologyEditor._load_config_payload
        TopologyEditor._load_config_payload = lambda self, _path: {
            "profiles": {
                "current_profile": {"devices": []},
                "alpha": {"devices": ["Motor 25"]},
                "beta": {"devices": ["Motor 25"]},
            }
        }
        try:
            editor._profile_source_path = str(Path(__file__))
            editor._refresh_list()
        finally:
            TopologyEditor._load_config_payload = original_load_config_payload

        self.assertEqual(
            editor.node_list.items["inventory:Motor 25"][5],
            "alpha, beta",
        )

    def test_refresh_list_full_config_includes_topology_only_nodes_from_other_profiles(self) -> None:
        editor = self._headless_editor("inventory_topology_only")
        editor._refresh_list = TopologyEditor._refresh_list.__get__(editor, TopologyEditor)
        editor._device_nodes = TopologyEditor._device_nodes.__get__(editor, TopologyEditor)
        editor._node_groups_by_label = TopologyEditor._node_groups_by_label.__get__(editor, TopologyEditor)
        editor._profiles_by_label = TopologyEditor._profiles_by_label.__get__(editor, TopologyEditor)
        editor._topology_inventory_entries = TopologyEditor._topology_inventory_entries.__get__(editor, TopologyEditor)
        editor._full_config_inventory_entries = TopologyEditor._full_config_inventory_entries.__get__(
            editor, TopologyEditor
        )
        editor._tags_to_string = TopologyEditor._tags_to_string.__get__(editor, TopologyEditor)
        editor._normalize_tags = TopologyEditor._normalize_tags.__get__(editor, TopologyEditor)
        editor._inventory_entry_for_label = TopologyEditor._inventory_entry_for_label.__get__(editor, TopologyEditor)
        editor._destroy_inline_editor = lambda: None
        editor._nodes = []
        editor._device_registry_list = []
        editor._device_registry = {}
        editor._list_scope_var.set("Full Config")
        payload = {
            "profiles": {
                "inventory_topology_only": {"devices": []},
                "beta": {"devices": []},
            },
            "topology": {
                "version": 1,
                "source": "local",
                "profiles": {
                    "beta": {
                        "nodes": [
                            {
                                "key": 10,
                                "objectType": "diagram",
                                "nodeType": "diagram",
                                "category": "cannect_direct",
                                "label": "cannect 3",
                                "profileVisible": False,
                                "layout": {"bus": 0, "row": 0, "x": 20.0},
                            }
                        ],
                        "edges": [],
                        "view": {},
                    }
                },
            },
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / "bringup_system.json"
            write_profiles_payload(temp_path, payload, stamp=False)
            editor._profile_source_path = str(temp_path)
            editor._default_profiles_path = lambda: temp_path
            editor._refresh_list()

        self.assertIn("inventory:cannect 3", editor.node_list.items)
        self.assertEqual(editor.node_list.items["inventory:cannect 3"][1], "cannect_direct")
        self.assertEqual(editor.node_list.items["inventory:cannect 3"][5], "beta")

    def test_refresh_list_current_profile_scope_hides_out_of_profile_registry_rows(self) -> None:
        editor = self._headless_editor("inventory_scope_profile")
        editor._refresh_list = TopologyEditor._refresh_list.__get__(editor, TopologyEditor)
        editor._device_nodes = TopologyEditor._device_nodes.__get__(editor, TopologyEditor)
        editor._node_groups_by_label = TopologyEditor._node_groups_by_label.__get__(editor, TopologyEditor)
        editor._tags_to_string = TopologyEditor._tags_to_string.__get__(editor, TopologyEditor)
        editor._normalize_tags = TopologyEditor._normalize_tags.__get__(editor, TopologyEditor)
        editor._inventory_entry_for_label = TopologyEditor._inventory_entry_for_label.__get__(editor, TopologyEditor)
        editor._destroy_inline_editor = lambda: None
        editor._nodes = [
            Node(
                key=1,
                category="krakens",
                label="frontLeft Drive Motor",
                can_id=2,
                interface=INTERFACE_CAN,
            )
        ]
        editor._device_registry_list = [
            {
                "label": "frontLeft Drive Motor",
                "deviceInterface": "CAN",
                "id": 2,
                "manufacturer": 4,
                "deviceType": 2,
                "model": "Kraken X60",
            },
            {
                "label": "backLeft Drive Motor",
                "deviceInterface": "CAN",
                "id": 5,
                "manufacturer": 4,
                "deviceType": 2,
                "model": "Kraken X60",
            },
        ]
        editor._device_registry = {
            entry["label"]: entry for entry in editor._device_registry_list
        }
        editor._list_scope_var.set("Current Profile")

        editor._refresh_list()

        self.assertIn("1", editor.node_list.items)
        self.assertNotIn("inventory:backLeft Drive Motor", editor.node_list.items)

    def test_add_inventory_label_to_canvas_adds_device_to_profile_nodes(self) -> None:
        editor = self._headless_editor("inventory_drop")
        editor._add_inventory_label_to_canvas = TopologyEditor._add_inventory_label_to_canvas.__get__(editor, TopologyEditor)
        editor._inventory_entry_for_label = TopologyEditor._inventory_entry_for_label.__get__(editor, TopologyEditor)
        editor._is_topology_capable_inventory_entry = TopologyEditor._is_topology_capable_inventory_entry.__get__(editor, TopologyEditor)
        editor._is_can_device_entry = TopologyEditor._is_can_device_entry.__get__(editor, TopologyEditor)
        editor._is_dio_device_entry = TopologyEditor._is_dio_device_entry.__get__(editor, TopologyEditor)
        editor._node_from_device_def = TopologyEditor._node_from_device_def.__get__(editor, TopologyEditor)
        editor._nearest_bus_and_row = TopologyEditor._nearest_bus_and_row.__get__(editor, TopologyEditor)
        editor._device_nodes = TopologyEditor._device_nodes.__get__(editor, TopologyEditor)
        editor._refresh_list = lambda: None
        editor._mark_neighbors_stale = lambda: None
        editor._redraw_canvas = lambda: None
        editor._select_node = lambda key: setattr(editor, "_selected_key", key)
        editor._push_undo = lambda: None
        editor._prune_attachment_links = lambda: None
        editor._prune_power_links = lambda: None
        editor._prune_dio_wiring_links = lambda: None
        editor._ensure_dio_wiring_links = lambda: None
        editor._nodes = []
        editor._device_registry_list = [
            {
                "label": "backLeft Drive Motor",
                "deviceInterface": "CAN",
                "id": 5,
                "manufacturer": 4,
                "deviceType": 2,
                "model": "Kraken X60",
            }
        ]
        editor._device_registry = {
            "backLeft Drive Motor": editor._device_registry_list[0]
        }
        editor._non_topology_profile_labels = []
        editor._draw_state = {"bus_ys": [100.0], "y_shift": 0.0, "scale": 1.0}

        editor._add_inventory_label_to_canvas("backLeft Drive Motor", 250.0, 120.0)

        self.assertEqual(len(editor._nodes), 1)
        self.assertEqual(editor._nodes[0].label, "backLeft Drive Motor")
        self.assertEqual(editor._selected_key, editor._nodes[0].key)

    def test_nodes_from_profile_ignores_usb_controller_but_tracks_label(self) -> None:
        editor = self._headless_editor("controller_load")
        editor._device_registry_list = [
            {
                "label": "controller0",
                "deviceInterface": "USB",
                "id": 0,
                "model": "Xbox Controller",
                "type": "xboxController",
            }
        ]
        editor._device_registry = {"controller0": editor._device_registry_list[0]}
        profile = {"devices": ["controller0"]}

        editor._nodes = TopologyEditor._nodes_from_profile(editor, profile)
        TopologyEditor._sync_non_topology_profile_labels(editor, profile)

        self.assertEqual(editor._nodes, [])
        self.assertEqual(editor._non_topology_profile_labels, ["controller0"])

    def test_add_xbox_controller_reuses_existing_global_controller_for_profile(self) -> None:
        editor = self._headless_editor("controller_add_existing")
        editor._device_registry_list = [
            {
                "label": "controller0",
                "deviceInterface": "USB",
                "id": 0,
                "manufacturer": 1,
                "deviceType": 1,
                "model": "Xbox Controller",
                "type": "xboxController",
            }
        ]
        editor._device_registry = {"controller0": editor._device_registry_list[0]}
        editor._non_topology_profile_labels = []
        editor._selected_nodes = set()
        editor._selected_buses = set()
        editor._refresh_list = TopologyEditor._refresh_list.__get__(editor, TopologyEditor)
        editor._device_nodes = TopologyEditor._device_nodes.__get__(editor, TopologyEditor)
        editor._node_groups_by_label = TopologyEditor._node_groups_by_label.__get__(editor, TopologyEditor)
        editor._tags_to_string = TopologyEditor._tags_to_string.__get__(editor, TopologyEditor)
        editor._normalize_tags = TopologyEditor._normalize_tags.__get__(editor, TopologyEditor)
        editor._inventory_entry_for_label = TopologyEditor._inventory_entry_for_label.__get__(editor, TopologyEditor)
        editor._matching_xbox_controller_entry = TopologyEditor._matching_xbox_controller_entry.__get__(editor, TopologyEditor)
        editor._controller_port_in_use = TopologyEditor._controller_port_in_use.__get__(editor, TopologyEditor)
        editor._sync_selection_state = lambda: None

        editor._prompt_xbox_controller_dialog = lambda *args, **kwargs: {
            "Count": 1,
            "Starting Port": 0,
        }

        TopologyEditor._on_add_xbox_controller(editor)

        self.assertEqual(editor._non_topology_profile_labels, ["controller0"])
        self.assertIn("inventory:controller0", editor.node_list.items)

    def test_remove_selected_inventory_item_only_removes_from_current_profile(self) -> None:
        original_messagebox = can_top_editor.messagebox
        can_top_editor.messagebox = _MessageBoxStub
        try:
            editor = self._headless_editor("controller_remove_local")
            editor._device_registry_list = [
                {
                    "label": "controller0",
                    "deviceInterface": "USB",
                    "id": 0,
                    "manufacturer": 1,
                    "deviceType": 1,
                    "model": "Xbox Controller",
                    "type": "xboxController",
                }
            ]
            editor._device_registry = {"controller0": editor._device_registry_list[0]}
            editor._non_topology_profile_labels = ["controller0"]
            editor._selected_inventory_label = "controller0"
            editor._root_extras = {
                "bridgeConfig": {
                    "byProfile": {
                        "controller_remove_local": {
                            "groups": [
                                {
                                    "name": "drivers",
                                    "members": [{"label": "controller0", "enabled": True}],
                                }
                            ]
                        },
                        "other_profile": {
                            "groups": [
                                {
                                    "name": "drivers",
                                    "members": [{"label": "controller0", "enabled": True}],
                                }
                            ]
                        },
                    }
                }
            }
            editor._inventory_entry_for_label = TopologyEditor._inventory_entry_for_label.__get__(editor, TopologyEditor)
            editor._is_xbox_controller_entry = TopologyEditor._is_xbox_controller_entry.__get__(editor, TopologyEditor)
            editor._prune_current_profile_bridge_config_label = TopologyEditor._prune_current_profile_bridge_config_label.__get__(editor, TopologyEditor)
            editor._prune_bridge_config_entry_label = TopologyEditor._prune_bridge_config_entry_label.__get__(editor, TopologyEditor)
            editor._refresh_list = lambda: None
            editor._update_details_panel = lambda _node: None
            editor._update_selection_overlays = lambda: None

            result = TopologyEditor._remove_selected_inventory_item(editor)
        finally:
            can_top_editor.messagebox = original_messagebox

        self.assertTrue(result)
        self.assertEqual(editor._non_topology_profile_labels, [])
        self.assertIn("controller0", editor._device_registry)
        self.assertEqual(editor._pending_global_device_deletions, set())
        self.assertEqual(
            editor._root_extras["bridgeConfig"]["byProfile"]["controller_remove_local"]["groups"][0]["members"],
            [],
        )
        self.assertEqual(
            editor._root_extras["bridgeConfig"]["byProfile"]["other_profile"]["groups"][0]["members"],
            [{"label": "controller0", "enabled": True}],
        )

    def test_remove_selected_inventory_can_device_deletes_from_shared_config(self) -> None:
        original_messagebox = can_top_editor.messagebox
        can_top_editor.messagebox = _MessageBoxStub
        try:
            editor = self._headless_editor("inventory_global_remove")
            editor._device_registry_list = [
                {
                    "label": "Motor 25",
                    "deviceInterface": "CAN",
                    "manufacturer": 5,
                    "deviceType": 2,
                    "id": 25,
                    "model": "REV NEO",
                    "type": "motor",
                }
            ]
            editor._device_registry = {"Motor 25": editor._device_registry_list[0]}
            editor._non_topology_profile_labels = []
            editor._selected_inventory_label = "Motor 25"
            editor._root_extras = {
                "bridgeConfig": {
                    "byProfile": {
                        "inventory_global_remove": {
                            "groups": [],
                        },
                        "other_profile": {
                            "groups": [
                                {
                                    "name": "spares",
                                    "members": [{"label": "Motor 25", "enabled": True}],
                                }
                            ]
                        },
                    }
                }
            }
            editor._inventory_entry_for_label = TopologyEditor._inventory_entry_for_label.__get__(editor, TopologyEditor)
            editor._is_xbox_controller_entry = TopologyEditor._is_xbox_controller_entry.__get__(editor, TopologyEditor)
            editor._delete_inventory_entry_globally = TopologyEditor._delete_inventory_entry_globally.__get__(editor, TopologyEditor)
            editor._remove_registry_entry_by_label = TopologyEditor._remove_registry_entry_by_label.__get__(editor, TopologyEditor)
            editor._profile_references_for_label = lambda _label: ["other_profile"]
            editor._prune_bridge_config_label = TopologyEditor._prune_bridge_config_label.__get__(editor, TopologyEditor)
            editor._prune_bridge_config_entry_label = TopologyEditor._prune_bridge_config_entry_label.__get__(editor, TopologyEditor)
            editor._refresh_list = lambda: None
            editor._update_details_panel = lambda _node: None
            editor._update_selection_overlays = lambda: None

            result = TopologyEditor._remove_selected_inventory_item(editor)
        finally:
            can_top_editor.messagebox = original_messagebox

        self.assertTrue(result)
        self.assertNotIn("Motor 25", editor._device_registry)
        self.assertEqual(editor._device_registry_list, [])
        self.assertEqual(editor._pending_global_device_deletions, {"Motor 25"})
        self.assertEqual(
            editor._root_extras["bridgeConfig"]["byProfile"]["other_profile"]["groups"][0]["members"],
            [],
        )

    def test_remove_selected_node_only_prunes_current_profile_bridge_refs(self) -> None:
        original_messagebox = can_top_editor.messagebox
        can_top_editor.messagebox = _MessageBoxStub
        try:
            editor = self._headless_editor("node_remove_local")
            editor._nodes = [
                Node(
                    key=1,
                    category="krakens",
                    label="frontLeft Drive Motor",
                    can_id=2,
                    interface=INTERFACE_CAN,
                )
            ]
            editor._selected_nodes = {1}
            editor._root_extras = {
                "bridgeConfig": {
                    "byProfile": {
                        "node_remove_local": {
                            "groups": [
                                {
                                    "name": "driveTrain",
                                    "members": [{"label": "frontLeft Drive Motor", "enabled": True}],
                                }
                            ]
                        },
                        "other_profile": {
                            "groups": [
                                {
                                    "name": "driveTrain",
                                    "members": [{"label": "frontLeft Drive Motor", "enabled": True}],
                                }
                            ]
                        },
                    }
                }
            }
            editor._push_undo = lambda: None
            editor._clear_selection = lambda: editor._selected_nodes.clear()
            editor._prune_current_profile_bridge_config_label = TopologyEditor._prune_current_profile_bridge_config_label.__get__(editor, TopologyEditor)
            editor._prune_bridge_config_entry_label = TopologyEditor._prune_bridge_config_entry_label.__get__(editor, TopologyEditor)
            editor._prune_attachment_links = lambda: None
            editor._prune_power_links = lambda: None
            editor._prune_dio_wiring_links = lambda: None
            editor._refresh_list = lambda: None
            editor._update_details_panel = lambda _node: None
            editor._mark_neighbors_stale = lambda: None
            editor._redraw_canvas = lambda: None

            TopologyEditor._on_remove_selected(editor)
        finally:
            can_top_editor.messagebox = original_messagebox

        self.assertEqual(editor._nodes, [])
        self.assertEqual(
            editor._root_extras["bridgeConfig"]["byProfile"]["node_remove_local"]["groups"][0]["members"],
            [],
        )
        self.assertEqual(
            editor._root_extras["bridgeConfig"]["byProfile"]["other_profile"]["groups"][0]["members"],
            [{"label": "frontLeft Drive Motor", "enabled": True}],
        )

    def test_duplicate_rename_keeps_original_inventory_device_for_full_config(self) -> None:
        editor = self._headless_editor("duplicate_rename")
        editor._apply_node_label_change = TopologyEditor._apply_node_label_change.__get__(editor, TopologyEditor)
        editor._should_split_device_on_rename = TopologyEditor._should_split_device_on_rename.__get__(editor, TopologyEditor)
        editor._rename_registry_label = TopologyEditor._rename_registry_label.__get__(editor, TopologyEditor)
        editor._profile_references_for_label = lambda _label: ["duplicate_rename"]
        editor._update_bridge_config_label_refs = lambda *_args: (_ for _ in ()).throw(RuntimeError("global rename should not happen"))
        editor._update_callout_target_labels = lambda *_args: (_ for _ in ()).throw(RuntimeError("callout relabel should not happen"))
        node_original = Node(
            key=1,
            category="krakens",
            label="frontLeft Drive Motor",
            can_id=2,
            interface=INTERFACE_CAN,
        )
        node_duplicate = Node(
            key=2,
            category="krakens",
            label="frontLeft Drive Motor",
            can_id=22,
            interface=INTERFACE_CAN,
        )
        editor._nodes = [node_original, node_duplicate]
        editor._device_registry_list = [
            {
                "label": "frontLeft Drive Motor",
                "deviceInterface": "CAN",
                "id": 2,
                "manufacturer": 4,
                "deviceType": 2,
                "model": "Kraken X60",
            }
        ]
        editor._device_registry = {"frontLeft Drive Motor": editor._device_registry_list[0]}
        editor._non_topology_profile_labels = []

        node_duplicate.label = "frontLeft Drive Motor Copy"
        editor._apply_node_label_change(
            node_duplicate,
            "frontLeft Drive Motor",
            "frontLeft Drive Motor Copy",
        )

        self.assertIn("frontLeft Drive Motor", editor._device_registry)
        self.assertNotIn("frontLeft Drive Motor Copy", editor._device_registry)

    def test_clamp_node_x_to_current_bus_bounds_preserves_bus_length(self) -> None:
        editor = self._headless_editor("drag_clamp_bus")
        editor._should_clamp_node_to_bus = TopologyEditor._should_clamp_node_to_bus.__get__(editor, TopologyEditor)
        editor._clamp_node_x_to_current_bus_bounds = TopologyEditor._clamp_node_x_to_current_bus_bounds.__get__(editor, TopologyEditor)
        editor._node_box_dims = TopologyEditor._node_box_dims.__get__(editor, TopologyEditor)
        node = Node(
            key=1,
            category="krakens",
            label="frontLeft Drive Motor",
            can_id=2,
            interface=INTERFACE_CAN,
            x=100.0,
            bus_index=0,
        )
        editor._nodes = [node]
        editor._bus_lefts = [40.0]
        editor._bus_rights = [240.0]
        editor._draw_state = {"bus_lefts": [40.0], "bus_rights": [240.0]}

        clamped = editor._clamp_node_x_to_current_bus_bounds(node, 260.0)

        self.assertLess(clamped, 260.0)
        self.assertEqual(editor._bus_rights[0], 240.0)

    def test_create_group_from_selection_refreshes_list(self) -> None:
        editor = self._headless_editor("group_create_refresh")
        editor._nodes = [
            Node(
                key=1,
                category="devices",
                label="frontLeft Drive Motor",
                can_id=2,
                x=0.0,
            )
        ]
        editor._selected_nodes = {1}
        calls: list[str] = []
        editor._refresh_list = lambda: calls.append("refresh")
        editor._redraw_canvas = lambda: calls.append("redraw")

        with patch.object(can_top_editor.simpledialog, "askstring", return_value="Front Left"):
            editor._create_group_from_selection()

        self.assertEqual(calls, ["refresh", "redraw"])
        groups = editor._bridge_groups()
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["name"], "Front Left")

    def test_create_group_from_selection_includes_infrastructure_nodes(self) -> None:
        editor = self._headless_editor("group_create_infra")
        editor._nodes = [
            Node(
                key=0,
                category="cannect_direct",
                label="cannect 3",
                can_id=-1,
                node_type="diagram",
                interface=INTERFACE_CAN,
                x=60.0,
            ),
            Node(
                key=1,
                category="devices",
                label="frontLeft Drive Motor",
                can_id=2,
                x=0.0,
            ),
        ]
        editor._selected_nodes = {0, 1}
        editor._refresh_list = lambda: None
        editor._redraw_canvas = lambda: None

        with patch.object(can_top_editor.simpledialog, "askstring", return_value="Front Left"):
            editor._create_group_from_selection()

        members = editor._bridge_groups()[0]["members"]
        self.assertEqual(
            members,
            [
                {"label": "cannect 3", "enabled": True},
                {"label": "frontLeft Drive Motor", "enabled": True},
            ],
        )

    def test_remove_group_refreshes_list(self) -> None:
        editor = self._headless_editor("group_remove_refresh")
        editor._root_extras = {
            "bridgeConfig": {
                "byProfile": {
                    "group_remove_refresh": {
                        "groups": [
                            {"name": "Front Left", "members": [{"label": "frontLeft Drive Motor", "enabled": True}]}
                        ]
                    }
                }
            }
        }
        editor._profile_name = "group_remove_refresh"
        calls: list[str] = []
        editor._refresh_list = lambda: calls.append("refresh")
        editor._redraw_canvas = lambda: calls.append("redraw")

        with patch.object(can_top_editor.simpledialog, "askstring", return_value="Front Left"):
            editor._remove_bridge_group()

        self.assertEqual(calls, ["refresh", "redraw"])
        self.assertEqual(editor._bridge_groups(), [])

    def test_group_overlay_label_bounds_are_above_group_box(self) -> None:
        canvas = _CanvasStub()
        overlays = draw_group_overlays(
            canvas,
            {"drive": (100.0, 200.0, 180.0, 240.0)},
            [{"name": "leftModule", "members": [{"label": "drive"}]}],
            zoom=1.0,
        )

        self.assertEqual(len(overlays), 1)
        bounds = overlays[0]["bounds"]
        label_bounds = overlays[0]["label_bounds"]
        self.assertLess(label_bounds[3], bounds[1])

    def test_group_overlay_uses_solid_outline_style(self) -> None:
        canvas = _CanvasStub()

        draw_group_overlays(
            canvas,
            {"drive": (100.0, 200.0, 180.0, 240.0)},
            [{"name": "leftModule", "members": [{"label": "drive"}]}],
            zoom=1.0,
        )

        outline_rect = canvas.rectangles[0]
        self.assertEqual(outline_rect["kwargs"].get("width"), GROUP_OVERLAY_WIDTH)
        self.assertNotIn("dash", outline_rect["kwargs"])

    def test_group_overlay_stacks_overlapping_labels(self) -> None:
        canvas = _CanvasStub()

        overlays = draw_group_overlays(
            canvas,
            {
                "leftA": (100.0, 200.0, 180.0, 240.0),
                "leftB": (110.0, 202.0, 190.0, 242.0),
            },
            [
                {"name": "krakens", "members": [{"label": "leftA"}]},
                {"name": "neos", "members": [{"label": "leftB"}]},
            ],
            zoom=1.0,
        )

        first_label = overlays[0]["label_bounds"]
        second_label = overlays[1]["label_bounds"]
        self.assertLess(second_label[3], first_label[1])

    def test_group_overlay_skips_groups_without_placeable_members(self) -> None:
        canvas = _CanvasStub()

        overlays = draw_group_overlays(
            canvas,
            {"motor1": (100.0, 200.0, 180.0, 240.0)},
            [{"name": "unknownGroup", "members": [{"label": "missingMotor"}]}],
            zoom=1.0,
        )

        self.assertEqual([], overlays)
        self.assertEqual([], canvas.rectangles)

    def test_draw_links_uses_distinct_dash_patterns_by_link_family(self) -> None:
        canvas = _CanvasStub()

        draw_links(
            canvas,
            {1: (100.0, 100.0), 2: (200.0, 100.0)},
            {1: (80.0, 80.0, 120.0, 120.0), 2: (180.0, 80.0, 220.0, 120.0)},
            [40.0],
            [(1, 2)],
            [{"node": 1, "bus": 0, "port": 1}],
            [{"node": 1, "device": 2, "port": 1}],
            [],
        )

        self.assertEqual(canvas.lines[0]["kwargs"].get("dash"), (8, 4))
        self.assertEqual(canvas.lines[1]["kwargs"].get("dash"), (2, 2))
        self.assertEqual(canvas.lines[2]["kwargs"].get("dash"), (8, 3, 2, 3))

    def test_group_overlay_press_selects_and_starts_group_drag(self) -> None:
        editor = self._headless_editor("group_drag")
        editor._nodes = [
            Node(
                key=0,
                category="cannect_direct",
                label="cannect 3",
                can_id=-1,
                node_type="diagram",
                interface=INTERFACE_CAN,
                x=60.0,
                row=1,
                bus_index=0,
                profile_visible=False,
            ),
            Node(
                key=1,
                category="krakens",
                label="frontLeft Drive Motor",
                can_id=2,
                interface=INTERFACE_CAN,
                x=100.0,
                free_y=100.0,
            ),
            Node(
                key=2,
                category="neos",
                label="frontLeft Angle Motor",
                can_id=1,
                interface=INTERFACE_CAN,
                x=200.0,
                free_y=100.0,
            ),
        ]
        editor._root_extras = {
            "bridgeConfig": {
                "byProfile": {
                    "group_drag": {
                        "groups": [
                            {
                                "name": "frontLeft",
                                "members": [
                                    {"label": "frontLeft Drive Motor", "enabled": True},
                                    {"label": "frontLeft Angle Motor", "enabled": True},
                                ],
                            }
                        ]
                    }
                }
            }
        }
        editor._cannect_device_links = [
            {"node": 0, "device": 1, "port": 1},
            {"node": 0, "device": 2, "port": 2},
        ]
        editor.canvas = _CanvasStub()
        editor._clear_guides = lambda: None
        editor._selection_rect = None
        editor._selection_start = None
        editor._add_bus_mode = False
        editor._selected_nodes = set()
        editor._selected_buses = set()
        editor._bus_hit_test = lambda _cy: None
        editor._shift_held = TopologyEditor._shift_held.__get__(editor, TopologyEditor)
        editor._sync_selection_state = lambda: None
        editor._push_undo = lambda: None
        editor._tag_to_key = TopologyEditor._tag_to_key
        editor._device_nodes = TopologyEditor._device_nodes.__get__(editor, TopologyEditor)
        editor._node_center_y_unscaled = TopologyEditor._node_center_y_unscaled.__get__(editor, TopologyEditor)
        editor._bus_offsets = [0.0]
        editor._box_h = 34
        editor._group_overlay_regions = [
            {
                "name": "frontLeft",
                "bounds": (50.0, 50.0, 260.0, 180.0),
                "label_bounds": (56.0, 56.0, 130.0, 76.0),
            }
        ]

        editor._on_canvas_press(_PointerEventStub(60, 60))

        self.assertEqual(editor._selected_nodes, {1, 2})
        self.assertIsNotNone(editor._multi_drag)
        self.assertEqual(editor._multi_drag.get("anchor"), 1)

    def test_group_selection_includes_explicit_infrastructure_member_only(self) -> None:
        editor = self._headless_editor("group_drag_infra_explicit")
        editor._nodes = [
            Node(
                key=0,
                category="cannect_direct",
                label="cannect 3",
                can_id=-1,
                node_type="diagram",
                interface=INTERFACE_CAN,
                x=60.0,
                row=1,
                bus_index=0,
                profile_visible=False,
            ),
            Node(
                key=1,
                category="krakens",
                label="frontLeft Drive Motor",
                can_id=2,
                interface=INTERFACE_CAN,
                x=100.0,
                free_y=100.0,
            ),
        ]
        editor._root_extras = {
            "bridgeConfig": {
                "byProfile": {
                    "group_drag_infra_explicit": {
                        "groups": [
                            {
                                "name": "frontLeft",
                                "members": [
                                    {"label": "cannect 3", "enabled": True},
                                    {"label": "frontLeft Drive Motor", "enabled": True},
                                ],
                            }
                        ]
                    }
                }
            }
        }

        member_keys = editor._group_member_keys_by_name("frontLeft")

        self.assertEqual(member_keys, {0, 1})

    def test_group_overlay_label_click_takes_precedence_over_underlying_node(self) -> None:
        editor = self._headless_editor("group_drag_priority")
        editor._nodes = [
            Node(
                key=1,
                category="krakens",
                label="frontLeft Drive Motor",
                can_id=2,
                interface=INTERFACE_CAN,
                x=100.0,
                free_y=100.0,
            ),
            Node(
                key=2,
                category="neos",
                label="frontLeft Angle Motor",
                can_id=1,
                interface=INTERFACE_CAN,
                x=200.0,
                free_y=100.0,
            ),
        ]
        editor._root_extras = {
            "bridgeConfig": {
                "byProfile": {
                    "group_drag_priority": {
                        "groups": [
                            {
                                "name": "krakens",
                                "members": [
                                    {"label": "frontLeft Drive Motor", "enabled": True},
                                    {"label": "frontLeft Angle Motor", "enabled": True},
                                ],
                            }
                        ]
                    }
                }
            }
        }
        editor._selected_nodes = set()
        editor._selected_buses = set()
        editor._clear_guides = lambda: None
        editor._selection_rect = None
        editor._selection_start = None
        editor._add_bus_mode = False
        editor._shift_held = TopologyEditor._shift_held.__get__(editor, TopologyEditor)
        editor._sync_selection_state = lambda: None
        editor._push_undo = lambda: None
        editor._bus_hit_test = lambda _cy: None
        editor._group_overlay_regions = [
            {
                "name": "krakens",
                "bounds": (50.0, 50.0, 260.0, 180.0),
                "label_bounds": (56.0, 56.0, 130.0, 76.0),
            }
        ]
        editor._bus_offsets = [0.0]
        editor._box_h = 34
        editor.canvas = _CanvasStub()
        editor.canvas.find_overlapping = lambda *_args: (99,)
        editor.canvas.gettags = lambda _item: ("node_1",)

        editor._on_canvas_press(_PointerEventStub(60, 60))

        self.assertEqual(editor._selected_nodes, {1, 2})
        self.assertIsNotNone(editor._multi_drag)

    def test_schema_v4_label_list_profile_loads_registry_devices(self) -> None:
        editor = TopologyEditor.__new__(TopologyEditor)
        editor._next_key = 1
        editor._device_registry = {}
        editor._device_registry_list = []
        payload = {
            "profiles": {
                "demo_board_042526": {
                    "devices": [
                        "roborio",
                        "PDP",
                        "SPARKMAX/NEO 25",
                    ]
                }
            },
            "devices": [
                {
                    "label": "roborio",
                    "deviceInterface": "CAN",
                    "manufacturer": 1,
                    "deviceType": 1,
                    "id": 0,
                    "model": "NI roboRIO",
                },
                {
                    "label": "PDP",
                    "deviceInterface": "CAN",
                    "manufacturer": 4,
                    "deviceType": 8,
                    "id": 0,
                    "model": "CTRE PDP",
                },
                {
                    "label": "SPARKMAX/NEO 25",
                    "deviceInterface": "CAN",
                    "manufacturer": 5,
                    "deviceType": 2,
                    "id": 25,
                    "model": "REV NEO",
                },
            ],
        }

        editor._load_device_registry(payload)
        nodes = editor._nodes_from_profile(payload["profiles"]["demo_board_042526"])

        self.assertEqual([node.label for node in nodes], ["roborio", "PDP", "SPARKMAX/NEO 25"])
        self.assertEqual([node.can_id for node in nodes], [0, 0, 25])

    def test_layout_neighbors_follow_bus_x_order_and_skip_dio(self) -> None:
        nodes = [
            Node(key=1, category="roborio", label="roborio", can_id=0, x=300.0, bus_index=0),
            Node(key=2, category="devices", label="lsw1", can_id=-1, interface=INTERFACE_DIO, x=200.0, bus_index=0),
            Node(key=3, category="neos", label="NEO", can_id=25, interface=INTERFACE_CAN, x=100.0, bus_index=0),
            Node(key=4, category="falcons", label="FALCON", can_id=9, interface=INTERFACE_CAN, x=500.0, bus_index=0),
            Node(key=5, category="neo550s", label="NEO550", can_id=7, interface=INTERFACE_CAN, x=100.0, bus_index=1),
        ]

        neighbor_links, neighbor_ports = TopologyEditor._build_layout_neighbor_metadata(nodes)

        self.assertEqual(neighbor_links, [{"a": 1, "b": 3}, {"a": 1, "b": 4}])
        self.assertEqual(
            neighbor_ports,
            [
                {"node": 3, "port": "right", "neighbor": 1, "neighborPort": "left"},
                {"node": 1, "port": "left", "neighbor": 3, "neighborPort": "right"},
                {"node": 1, "port": "right", "neighbor": 4, "neighborPort": "left"},
                {"node": 4, "port": "left", "neighbor": 1, "neighborPort": "right"},
            ],
        )

    def test_neighbor_status_marks_existing_metadata_stale(self) -> None:
        editor = TopologyEditor.__new__(TopologyEditor)
        editor._neighbor_links = [{"a": 1, "b": 2}]
        editor._neighbor_ports = []
        editor._neighbors_dirty = False
        editor._neighbor_status_var = _StringVarStub()

        editor._mark_neighbors_stale()

        self.assertTrue(editor._neighbors_dirty)
        self.assertEqual(editor._neighbor_status_var.value, "Neighbors: stale")

    def test_topology_snapshot_uses_device_refs_without_duplicate_labels(self) -> None:
        editor = TopologyEditor.__new__(TopologyEditor)
        editor._neighbor_links = []
        editor._neighbor_ports = [
            {"node": 1, "port": "right", "neighbor": 2, "neighborPort": "left"},
        ]
        editor._ethernet_links = []
        editor._can_bus_links = []
        editor._cannect_device_links = []
        editor._attachment_links = [{"device": 2, "attachment": 3}]
        editor._power_links = [{"a": 1, "b": 2}]
        editor._dio_wiring_links = []
        editor._bus_offsets = [0.0]
        editor._bus_lefts = []
        editor._bus_rights = []
        editor._bus_connectors = [True]
        editor._bus_spacing = 160.0
        editor._pan_y = 0.0
        editor._zoom = 1.0
        editor._connection_filter_vars = {
            "can": _BoolVarStub(True),
            "power": _BoolVarStub(True),
            "dio": _BoolVarStub(True),
            "pwm": _BoolVarStub(True),
            "analog": _BoolVarStub(True),
            "virtual": _BoolVarStub(True),
        }
        editor._node_from_device_label = lambda label: object() if label in ("roborio", "motor1", "lsw1") else None
        nodes = [
            Node(key=1, category="roborio", label="roborio", can_id=0, x=10.0, bus_index=0),
            Node(key=2, category="neos", label="motor1", can_id=25, x=30.0, bus_index=0),
            Node(key=3, category="devices", label="lsw1", can_id=-1, interface=INTERFACE_DIO, x=50.0, row=1, bus_index=0),
        ]

        topology = editor._topology_snapshot_from_nodes(nodes)

        self.assertEqual(
            topology["nodes"],
            [
                {
                    "key": 1,
                    "objectType": "device",
                    "nodeType": "device",
                    "nodeClass": "device",
                    "deviceRef": "roborio",
                    "layout": {"bus": 0, "row": 0, "x": 10.0},
                },
                {
                    "key": 2,
                    "objectType": "device",
                    "nodeType": "device",
                    "nodeClass": "device",
                    "deviceRef": "motor1",
                    "layout": {"bus": 0, "row": 0, "x": 30.0},
                },
                {
                    "key": 3,
                    "objectType": "device",
                    "nodeType": "device",
                    "nodeClass": "device",
                    "deviceRef": "lsw1",
                    "layout": {"bus": 0, "row": 1, "x": 50.0},
                },
            ],
        )
        self.assertEqual(
            topology["edges"],
            [
                {
                    "id": "edge_1",
                    "fromNode": 1,
                    "fromPort": "right",
                    "toNode": 2,
                    "toPort": "left",
                    "edgeType": "can_trunk",
                },
                {
                    "id": "edge_2",
                    "fromNode": 1,
                    "fromPort": "power",
                    "toNode": 2,
                    "toPort": "power",
                    "edgeType": "power",
                },
                {
                    "id": "edge_3",
                    "fromNode": 2,
                    "fromPort": "attachment",
                    "toNode": 3,
                    "toPort": "attachment",
                    "edgeType": "virtual",
                },
            ],
        )
        self.assertEqual(
            topology["view"]["connectionFilters"],
            ["analog", "can", "dio", "power", "pwm", "virtual"],
        )

    def test_registry_generation_from_empty_file_preserves_required_fields(self) -> None:
        editor = TopologyEditor.__new__(TopologyEditor)
        editor._device_registry = {}
        editor._device_registry_list = []
        editor._attachment_links = []
        editor._nodes = [
            Node(
                key=1,
                category="neos",
                label="driveMotor",
                can_id=2,
                interface=INTERFACE_CAN,
                vendor="REV",
                device_type="NEO",
                motor="REV NEO",
            ),
            Node(
                key=2,
                category="devices",
                label="limit0",
                can_id=-1,
                interface=INTERFACE_DIO,
                device_type="limitSwitch",
                dio=0,
                invert=False,
            ),
        ]
        editor._device_nodes = TopologyEditor._device_nodes.__get__(editor, TopologyEditor)
        editor._is_registry_device_node = TopologyEditor._is_registry_device_node.__get__(editor, TopologyEditor)
        editor._is_infrastructure_node = TopologyEditor._is_infrastructure_node.__get__(editor, TopologyEditor)
        editor._is_infrastructure_category = TopologyEditor._is_infrastructure_category
        editor._sync_attachment_links_to_registry = lambda: None

        editor._apply_node_updates_to_registry()

        entries = {entry["label"]: entry for entry in editor._device_registry_list}
        self.assertEqual(entries["driveMotor"]["manufacturer"], 5)
        self.assertEqual(entries["driveMotor"]["deviceType"], 2)
        self.assertEqual(entries["driveMotor"]["id"], 2)
        self.assertEqual(entries["limit0"]["deviceInterface"], "DIO")
        self.assertEqual(entries["limit0"]["id"], 0)
        self.assertNotIn("dio", entries["limit0"])

    def test_validate_nodes_rejects_can_device_missing_required_registry_fields(self) -> None:
        editor = self._headless_editor("missing_can_registry_fields")
        editor._nodes = [
            Node(
                key=1,
                category="falcons",
                label="Falcon 9",
                can_id=9,
                interface=INTERFACE_CAN,
                vendor="",
                device_type="",
                motor="CTRE Falcon 500",
            ),
        ]

        validation_error = editor._validate_nodes()

        self.assertEqual(
            validation_error,
            "Device 'Falcon 9' missing CAN fields: id/manufacturer/deviceType.",
        )

    def test_validate_nodes_accepts_generic_motor_controller_type_from_editor_dropdown(self) -> None:
        editor = self._headless_editor("generic_motor_controller_type")
        editor._nodes = [
            Node(
                key=1,
                category="neos",
                label="SPARKMAX/NEO 25",
                can_id=25,
                interface=INTERFACE_CAN,
                vendor="REV",
                device_type="MotorController",
                motor="REV NEO",
            ),
        ]

        validation_error = editor._validate_nodes()

        self.assertIsNone(validation_error)

    def test_new_profile_topology_snapshot_uses_device_ref_before_registry_exists(self) -> None:
        editor = TopologyEditor.__new__(TopologyEditor)
        editor._device_registry = {}
        editor._device_registry_list = []
        editor._neighbor_links = []
        editor._neighbor_ports = []
        editor._ethernet_links = []
        editor._can_bus_links = []
        editor._cannect_device_links = []
        editor._attachment_links = []
        editor._power_links = []
        editor._dio_wiring_links = []
        editor._bus_offsets = [0.0]
        editor._bus_lefts = []
        editor._bus_rights = []
        editor._bus_connectors = []
        editor._bus_spacing = 160.0
        editor._pan_y = 0.0
        editor._zoom = 1.0
        editor._connection_filter_vars = {
            "can": _BoolVarStub(True),
            "power": _BoolVarStub(True),
            "dio": _BoolVarStub(True),
            "pwm": _BoolVarStub(True),
            "analog": _BoolVarStub(True),
            "virtual": _BoolVarStub(True),
        }
        editor._nodes = [
            Node(
                key=1,
                category="neos",
                label="driveMotor",
                can_id=2,
                interface=INTERFACE_CAN,
                vendor="REV",
                device_type="NEO",
                motor="REV NEO",
            )
        ]
        editor._is_registry_device_node = TopologyEditor._is_registry_device_node.__get__(editor, TopologyEditor)
        editor._is_infrastructure_node = TopologyEditor._is_infrastructure_node.__get__(editor, TopologyEditor)
        editor._is_infrastructure_category = TopologyEditor._is_infrastructure_category
        editor._topology_node_type_for_editor_node = (
            TopologyEditor._topology_node_type_for_editor_node.__get__(editor, TopologyEditor)
        )

        topology = editor._topology_snapshot()

        self.assertEqual(topology["nodes"][0]["objectType"], "device")
        self.assertEqual(topology["nodes"][0]["nodeType"], "device")
        self.assertEqual(topology["nodes"][0]["nodeClass"], "device")
        self.assertEqual(topology["nodes"][0]["deviceRef"], "driveMotor")

    def test_prune_topology_entry_device_refs_removes_deleted_nodes_edges_and_callouts(self) -> None:
        editor = TopologyEditor.__new__(TopologyEditor)
        topology_entry = {
            "nodes": [
                {"key": 1, "nodeType": "device", "deviceRef": "Motor 25"},
                {"key": 2, "nodeType": "device", "deviceRef": "Other Motor"},
                {"key": 3, "nodeType": "callout", "targetNodeKey": 1},
            ],
            "edges": [
                {"fromNode": 1, "toNode": 2},
                {"fromNode": 2, "toNode": 2},
            ],
        }

        TopologyEditor._prune_topology_entry_device_refs(editor, topology_entry, {"Motor 25"})

        self.assertEqual(
            topology_entry["nodes"],
            [{"key": 2, "nodeType": "device", "deviceRef": "Other Motor"}],
        )
        self.assertEqual(
            topology_entry["edges"],
            [{"fromNode": 2, "toNode": 2}],
        )

    def test_apply_topology_snapshot_accepts_object_type_without_legacy_node_type(self) -> None:
        editor = TopologyEditor.__new__(TopologyEditor)
        editor._nodes = [
            Node(key=10, category="roborio", label="roborio", can_id=0, x=0.0, bus_index=0),
            Node(key=11, category="pdp", label="PDP", can_id=1, x=20.0, bus_index=0),
        ]
        editor._connection_filter_vars = {
            "can": _BoolVarStub(True),
            "power": _BoolVarStub(True),
            "dio": _BoolVarStub(True),
            "pwm": _BoolVarStub(True),
            "analog": _BoolVarStub(True),
            "virtual": _BoolVarStub(True),
        }
        editor._ensure_bus_connectors = lambda _count: None
        editor._editor_category_for_topology_node = lambda entry: "devices"
        editor._normalize_tags = lambda value: []
        editor._mark_neighbors_current = lambda: None
        editor._prune_attachment_links = lambda: False
        editor._prune_power_links = lambda: False
        editor._prune_dio_wiring_links = lambda: False
        editor._ensure_dio_wiring_links = lambda: False
        editor._rebuild_attachment_links_from_registry = lambda: None
        editor._restore_missing_cannect_bus_links = lambda: None
        editor._restore_legacy_cannect_free_y_mode = lambda: None
        editor._fix_cannect_conflicts = lambda notify=False: None
        editor._apply_cannect_free_float = lambda: None
        editor._resolve_overlaps = lambda: None
        editor._device_nodes = TopologyEditor._device_nodes.__get__(editor, TopologyEditor)

        editor._apply_topology_snapshot(
            {
                "nodes": [
                    {"key": 1, "objectType": "device", "deviceRef": "roborio", "layout": {"bus": 0, "row": 0, "x": 0.0}},
                    {"key": 2, "objectType": "device", "deviceRef": "PDP", "layout": {"bus": 0, "row": 0, "x": 20.0}},
                ],
                "edges": [],
                "view": {},
            }
        )

        self.assertEqual([node.key for node in editor._nodes], [1, 2])

    def test_apply_topology_snapshot_rekeys_new_profile_devices_not_in_saved_topology(self) -> None:
        editor = TopologyEditor.__new__(TopologyEditor)
        editor._nodes = [
            Node(key=1, category="roborio", label="roborio", can_id=0, x=0.0, bus_index=0),
            Node(key=2, category="pdp", label="pdp", can_id=20, x=20.0, bus_index=0),
            Node(key=3, category="neos", label="SPARKMAX/NEO 25", can_id=25, x=40.0, bus_index=0),
            Node(key=4, category="devices", label="lmtSw0", can_id=-1, interface=INTERFACE_DIO, x=60.0, bus_index=0),
            Node(key=5, category="falcons", label="FALCON 9", can_id=9, x=80.0, bus_index=0),
            Node(key=6, category="pigeons", label="pigeon 2", can_id=19, x=100.0, bus_index=0),
            Node(key=7, category="cancoders", label="cancoder", can_id=18, x=120.0, bus_index=0),
            Node(key=8, category="neos", label="UNPROFILED_DEVICE_50207", can_id=7, x=140.0, bus_index=0),
        ]
        editor._connection_filter_vars = {
            "can": _BoolVarStub(True),
            "power": _BoolVarStub(True),
            "dio": _BoolVarStub(True),
            "pwm": _BoolVarStub(True),
            "analog": _BoolVarStub(True),
            "virtual": _BoolVarStub(True),
        }
        editor._ensure_bus_connectors = lambda _count: None
        editor._ensure_bus_connector_sides = lambda _count: None
        editor._editor_category_for_topology_node = lambda entry: "devices"
        editor._normalize_tags = lambda value: []
        editor._mark_neighbors_current = lambda: None
        editor._prune_attachment_links = lambda: False
        editor._prune_power_links = lambda: False
        editor._prune_dio_wiring_links = lambda: False
        editor._ensure_dio_wiring_links = lambda: False
        editor._rebuild_attachment_links_from_registry = lambda: None
        editor._restore_missing_cannect_bus_links = lambda: None
        editor._restore_legacy_cannect_free_y_mode = lambda: None
        editor._fix_cannect_conflicts = lambda notify=False: None
        editor._apply_cannect_free_float = lambda: None
        editor._resolve_overlaps = lambda: None
        editor._device_nodes = TopologyEditor._device_nodes.__get__(editor, TopologyEditor)
        editor._is_registry_device_node = TopologyEditor._is_registry_device_node.__get__(editor, TopologyEditor)
        editor._is_infrastructure_node = TopologyEditor._is_infrastructure_node.__get__(editor, TopologyEditor)
        editor._bus_offsets = [0.0]
        editor._bus_lefts = []
        editor._bus_rights = []
        editor._bus_connectors = []
        editor._bus_connector_sides = []
        editor._bus_spacing = 160.0
        editor._pan_y = 0.0
        editor._zoom = 1.0
        editor._ethernet_links = []
        editor._can_bus_links = []
        editor._cannect_device_links = []
        editor._attachment_links = []
        editor._dio_wiring_links = []
        editor._power_links = []
        editor._neighbor_links = []
        editor._neighbor_ports = []

        editor._apply_topology_snapshot(
            {
                "nodes": [
                    {"key": 1, "objectType": "device", "deviceRef": "roborio", "layout": {"bus": 0, "row": 0, "x": 0.0}},
                    {"key": 2, "objectType": "device", "deviceRef": "pdp", "layout": {"bus": 0, "row": 0, "x": 20.0}},
                    {"key": 4, "objectType": "device", "deviceRef": "SPARKMAX/NEO 25", "layout": {"bus": 0, "row": 0, "x": 40.0}},
                    {"key": 5, "objectType": "device", "deviceRef": "lmtSw0", "layout": {"bus": 0, "row": 1, "x": 60.0}},
                    {"key": 6, "objectType": "device", "deviceRef": "FALCON 9", "layout": {"bus": 0, "row": 0, "x": 80.0}},
                    {"key": 8, "objectType": "device", "deviceRef": "pigeon 2", "layout": {"bus": 0, "row": 0, "x": 100.0}},
                    {"key": 9, "objectType": "device", "deviceRef": "cancoder", "layout": {"bus": 0, "row": 0, "x": 120.0}},
                ],
                "edges": [],
                "view": {},
            }
        )

        keys_by_label = {node.label: node.key for node in editor._nodes if node.node_type != "callout"}
        self.assertEqual(8, keys_by_label["pigeon 2"])
        self.assertEqual(9, keys_by_label["cancoder"])
        self.assertGreater(keys_by_label["UNPROFILED_DEVICE_50207"], 9)
        self.assertEqual(len(keys_by_label), len({node.key for node in editor._nodes if node.node_type != "callout"}))

    def test_generated_profile_payload_validates_after_registry_update(self) -> None:
        editor = TopologyEditor.__new__(TopologyEditor)
        editor._device_registry = {}
        editor._device_registry_list = []
        editor._attachment_links = []
        editor._nodes = [
            Node(
                key=1,
                category="pdh",
                label="pdh",
                can_id=1,
                interface=INTERFACE_CAN,
                vendor="REV",
                device_type="PowerDistributionModule",
                motor="PDH",
                terminator=True,
            ),
            Node(
                key=2,
                category="devices",
                label="limit0",
                can_id=-1,
                interface=INTERFACE_DIO,
                device_type="limitSwitch",
                dio=0,
                invert=False,
            ),
        ]
        editor._device_nodes = TopologyEditor._device_nodes.__get__(editor, TopologyEditor)
        editor._profile_device_nodes = TopologyEditor._profile_device_nodes.__get__(editor, TopologyEditor)
        editor._is_registry_device_node = TopologyEditor._is_registry_device_node.__get__(editor, TopologyEditor)
        editor._is_infrastructure_node = TopologyEditor._is_infrastructure_node.__get__(editor, TopologyEditor)
        editor._is_infrastructure_category = TopologyEditor._is_infrastructure_category
        editor._sync_attachment_links_to_registry = lambda: None
        editor._apply_node_updates_to_registry()
        payload = {
            "schema_version": 5,
            "data_version": "test",
            "data_hash": "test",
            "default_profile": "demo",
            "profiles": {"demo": editor._profile_from_nodes()},
            "devices": editor._device_registry_list,
        }
        store = ConfigSchemaStore()
        store._db.set_payload(DOC_PROFILES, payload)

        result = store.validate(strict=True)

        self.assertTrue(result.ok(), [issue.message for issue in result.errors()])

    def test_new_blank_profile_creates_empty_profile_in_existing_config(self) -> None:
        profile_name = "blank_new"
        original_messagebox = can_top_editor.messagebox
        original_askstring = can_top_editor.simpledialog.askstring
        can_top_editor.messagebox = _MessageBoxStub
        can_top_editor.simpledialog.askstring = lambda *_args, **_kwargs: profile_name
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir) / "bringup_system.json"
                payload = {
                    "schema_version": 5,
                    "data_version": "test",
                    "data_hash": "test",
                    "default_profile": "robot_2026_swerve",
                    "profiles": {
                        "robot_2026_swerve": {
                            "devices": ["roborio"]
                        }
                    },
                    "devices": [
                        {
                            "label": "roborio",
                            "deviceInterface": "CAN",
                            "id": 0,
                            "manufacturer": 1,
                            "deviceType": 1,
                            "model": "NI roboRIO",
                        }
                    ],
                    "topology": {
                        "version": 1,
                        "source": "local",
                        "profiles": {
                            "robot_2026_swerve": {
                                "version": 1,
                                "source": "local",
                                "nodes": [],
                                "edges": [],
                                "view": {
                                    "busOffsets": [0.0],
                                    "busCount": 1,
                                    "busSpacing": 160.0,
                                    "busLefts": [],
                                    "busRights": [],
                                    "busConnectors": [],
                                    "busConnectorSides": [],
                                    "panY": 0.0,
                                    "zoom": 1.0,
                                    "ethernetLinks": [],
                                    "canLinks": [],
                                    "deviceLinks": [],
                                    "connectionFilters": ["analog", "can", "dio", "power", "pwm", "virtual"],
                                    "callouts": [],
                                },
                            }
                        },
                    },
                }
                write_profiles_payload(temp_path, payload, stamp=False)
                editor = self._headless_editor("robot_2026_swerve")
                editor._profile_source_path = str(temp_path)
                editor._confirm_discard = lambda: True

                editor._new_blank_profile()

                saved = load_profiles_payload(temp_path)
        finally:
            can_top_editor.messagebox = original_messagebox
            can_top_editor.simpledialog.askstring = original_askstring

        self.assertIn(profile_name, saved["profiles"])
        self.assertEqual(saved["profiles"][profile_name]["devices"], [])
        self.assertIn(profile_name, saved["topology"]["profiles"])
        self.assertEqual(editor._profile_name, profile_name)
        self.assertEqual(editor._nodes, [])

    def test_new_blank_profile_accepts_schema_v4_without_prompt(self) -> None:
        profile_name = "blank_from_v4"
        original_messagebox = can_top_editor.messagebox
        original_askstring = can_top_editor.simpledialog.askstring
        can_top_editor.messagebox = _MessageBoxStub
        can_top_editor.simpledialog.askstring = lambda *_args, **_kwargs: profile_name
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir) / "bringup_system.json"
                payload = {
                    "schema_version": 4,
                    "data_version": "test",
                    "data_hash": "test",
                    "default_profile": "robot_2026_swerve",
                    "profiles": {
                        "robot_2026_swerve": {
                            "devices": ["roborio"]
                        }
                    },
                    "devices": [
                        {
                            "label": "roborio",
                            "deviceInterface": "CAN",
                            "id": 0,
                            "manufacturer": 1,
                            "deviceType": 1,
                            "model": "NI roboRIO",
                        }
                    ],
                    "topology": {
                        "version": 1,
                        "source": "local",
                        "profiles": {
                            "robot_2026_swerve": {
                                "version": 1,
                                "source": "local",
                                "nodes": [],
                                "edges": [],
                                "view": {
                                    "busOffsets": [0.0],
                                    "busCount": 1,
                                    "busSpacing": 160.0,
                                    "busLefts": [],
                                    "busRights": [],
                                    "busConnectors": [],
                                    "busConnectorSides": [],
                                    "panY": 0.0,
                                    "zoom": 1.0,
                                    "ethernetLinks": [],
                                    "canLinks": [],
                                    "deviceLinks": [],
                                    "connectionFilters": ["analog", "can", "dio", "power", "pwm", "virtual"],
                                    "callouts": [],
                                },
                            }
                        },
                    },
                }
                write_profiles_payload(temp_path, payload, stamp=False)
                editor = self._headless_editor("robot_2026_swerve")
                editor._profile_source_path = str(temp_path)
                editor._confirm_discard = lambda: True
                prompted = {"schema": False}

                def _unexpected_prompt(title: str, message: str) -> bool:
                    if title == "Schema Mismatch":
                        prompted["schema"] = True
                    return True

                can_top_editor.messagebox.askyesno = _unexpected_prompt

                editor._new_blank_profile()

                saved = load_profiles_payload(temp_path)
        finally:
            can_top_editor.messagebox = original_messagebox
            can_top_editor.simpledialog.askstring = original_askstring

        self.assertFalse(prompted["schema"])
        self.assertIn(profile_name, saved["profiles"])
        self.assertEqual(saved["profiles"][profile_name]["devices"], [])

    def test_load_profiles_payload_falls_back_to_requested_file_when_store_returns_blank(self) -> None:
        original_messagebox = can_top_editor.messagebox
        original_store = can_top_editor.ConfigSchemaStore
        original_repo_root = can_top_editor.repo_root
        can_top_editor.messagebox = _MessageBoxStub
        can_top_editor.ConfigSchemaStore = _ConfigSchemaStoreBlankStub
        can_top_editor.repo_root = lambda: Path.cwd()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir) / "bringup_system.json"
                payload = {
                    "schema_version": 4,
                    "data_version": "real",
                    "data_hash": "realhash",
                    "default_profile": "robot_2026_swerve",
                    "profiles": {"robot_2026_swerve": {"devices": ["roborio"]}},
                    "devices": [
                        {
                            "label": "roborio",
                            "deviceInterface": "CAN",
                            "id": 0,
                            "manufacturer": 1,
                            "deviceType": 1,
                            "model": "NI roboRIO",
                        }
                    ],
                    "topology": {"version": 1, "source": "local", "profiles": {}},
                }
                write_profiles_payload(temp_path, payload, stamp=False)
                editor = self._headless_editor("robot_2026_swerve")
                editor._default_profiles_path = lambda: temp_path

                loaded = editor._load_profiles_payload(temp_path)
        finally:
            can_top_editor.messagebox = original_messagebox
            can_top_editor.ConfigSchemaStore = original_store
            can_top_editor.repo_root = original_repo_root

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["data_version"], "real")
        self.assertEqual(loaded["default_profile"], "robot_2026_swerve")

    def test_fit_to_window_uses_free_y_device_bounds(self) -> None:
        editor = TopologyEditor.__new__(TopologyEditor)
        editor.canvas = _CanvasStub(width=1000, height=500)
        editor._box_w = 90
        editor._box_h = 34
        editor._bus_offsets = [0.0]
        editor._bus_lefts = [40.0]
        editor._bus_rights = [400.0]
        editor._zoom = 1.0
        editor._pan_y = 0.0
        editor._layout_width = 1000
        editor._dirty = False
        editor._zoom_label_var = _StringVarStub()
        editor._redraw_canvas = lambda: None
        editor.update_idletasks = lambda: None
        editor._device_nodes = TopologyEditor._device_nodes.__get__(editor, TopologyEditor)
        editor._callout_nodes = TopologyEditor._callout_nodes.__get__(editor, TopologyEditor)
        editor._node_center_y_unscaled = TopologyEditor._node_center_y_unscaled.__get__(
            editor,
            TopologyEditor,
        )
        editor._nodes = [
            Node(
                key=1,
                category="neos",
                label="driveMotor",
                can_id=2,
                interface=INTERFACE_CAN,
                vendor="REV",
                device_type="NEO",
                motor="REV NEO",
                free_y=1000.0,
            )
        ]

        editor._fit_to_window()

        self.assertLess(editor._pan_y, -100.0)
        self.assertIsNotNone(editor.canvas.xview_value)
        self.assertEqual(editor.canvas.yview_value, 0.0)

    def test_swyft_power_label_is_placed_at_power_port(self) -> None:
        editor = self._headless_editor("swyft_ports")
        editor.canvas = _CanvasStub(width=1000, height=500)
        editor._box_w = 90
        editor._box_h = 34
        editor._bus_offsets = [0.0]
        editor._bus_lefts = [40.0]
        editor._bus_rights = [400.0]
        editor._bus_connectors = []
        editor._layout_width = 600.0
        editor._zoom = 1.0
        editor._pan_y = 0.0
        editor._dirty = False
        editor._selected_nodes = set()
        editor._selected_buses = set()
        editor._show_group_overlays_var = _BoolVarStub(False)
        editor._show_warn_badges_var = _BoolVarStub(False)
        editor._smart_guides_var = _BoolVarStub(False)
        editor._guide_x = None
        editor._guide_bus = None
        editor._draw_state = {"bus_ys": [], "y_shift": 0.0, "scale": 1.0}
        editor._node_bounds = {}
        editor._bus_ys = []
        editor._group_overlay_regions = []
        editor._connection_filter_vars = {
            key: _BoolVarStub(True)
            for key in ("can", "power", "dio", "pwm", "analog", "virtual")
        }
        editor._draw_device_shape_on = TopologyEditor._draw_device_shape_on.__get__(editor, TopologyEditor)
        editor._shape_kind_for_node = TopologyEditor._shape_kind_for_node.__get__(editor, TopologyEditor)
        editor._fill_color_for_node = TopologyEditor._fill_color_for_node.__get__(editor, TopologyEditor)
        editor._text_color_for_fill = TopologyEditor._text_color_for_fill
        editor._device_nodes = TopologyEditor._device_nodes.__get__(editor, TopologyEditor)
        editor._callout_nodes = TopologyEditor._callout_nodes.__get__(editor, TopologyEditor)
        editor._node_center_y_unscaled = TopologyEditor._node_center_y_unscaled.__get__(editor, TopologyEditor)
        editor._node_box_dims = TopologyEditor._node_box_dims.__get__(editor, TopologyEditor)
        editor._node_bus_y = TopologyEditor._node_bus_y.__get__(editor, TopologyEditor)
        editor._node_box_y = TopologyEditor._node_box_y.__get__(editor, TopologyEditor)
        editor._should_clamp_node_to_bus = TopologyEditor._should_clamp_node_to_bus.__get__(editor, TopologyEditor)
        editor._is_swyft_node = TopologyEditor._is_swyft_node
        editor._is_dio_node = TopologyEditor._is_dio_node.__get__(editor, TopologyEditor)
        editor._connection_filter_allows = TopologyEditor._connection_filter_allows.__get__(editor, TopologyEditor)
        editor._dup_key_for_node = TopologyEditor._dup_key_for_node.__get__(editor, TopologyEditor)
        editor._fit_font_size = lambda _text, _max_w, _max_h, base_size: base_size
        editor._wrap_label_lines = lambda text, _font, _width: [text]
        editor._draw_error_badge = lambda _x, _y: []
        editor._draw_warning_badge = lambda _x, _y: []
        editor._draw_group_overlays = lambda: None
        editor._clear_guides = lambda: None
        editor._redraw_canvas = TopologyEditor._redraw_canvas.__get__(editor, TopologyEditor)
        editor._nodes = [
            Node(
                key=1,
                category="cannect_inject",
                label="inject",
                can_id=-1,
                node_type="diagram",
                interface=INTERFACE_CAN,
                x=200.0,
                row=1,
                bus_index=0,
                profile_visible=False,
            ),
            Node(
                key=2,
                category="cannect_direct",
                label="direct",
                can_id=-1,
                node_type="diagram",
                interface=INTERFACE_CAN,
                x=320.0,
                row=1,
                bus_index=0,
                profile_visible=False,
            ),
        ]

        editor._redraw_canvas()

        power_texts = [entry for entry in editor.canvas.texts if entry["kwargs"].get("text") in {"Power In", "Power Out"}]
        labels = {entry["kwargs"].get("text"): entry["args"][:2] for entry in power_texts}
        inject_bounds = editor._node_bounds[1]
        direct_bounds = editor._node_bounds[2]
        self.assertEqual(labels["Power In"], (200.0, inject_bounds[3] + 10.0))
        self.assertEqual(labels["Power Out"], (320.0, direct_bounds[3] + 10.0))

    def test_topology_snapshot_persists_free_y_relative_mode(self) -> None:
        editor = TopologyEditor.__new__(TopologyEditor)
        editor._device_registry = {}
        editor._device_registry_list = []
        editor._neighbor_links = []
        editor._neighbor_ports = []
        editor._ethernet_links = []
        editor._can_bus_links = []
        editor._cannect_device_links = []
        editor._attachment_links = []
        editor._power_links = []
        editor._dio_wiring_links = []
        editor._bus_offsets = [0.0]
        editor._bus_lefts = []
        editor._bus_rights = []
        editor._bus_connectors = []
        editor._bus_spacing = 160.0
        editor._pan_y = 0.0
        editor._zoom = 1.0
        editor._connection_filter_vars = {
            "can": _BoolVarStub(True),
            "power": _BoolVarStub(True),
            "dio": _BoolVarStub(True),
            "pwm": _BoolVarStub(True),
            "analog": _BoolVarStub(True),
            "virtual": _BoolVarStub(True),
        }
        node = Node(
            key=1,
            category="cannect_direct",
            label="cannect 2",
            can_id=-1,
            x=100.0,
            free_y=450.0,
            profile_visible=False,
        )
        node.free_y_relative = False
        editor._nodes = [node]
        editor._is_registry_device_node = TopologyEditor._is_registry_device_node.__get__(editor, TopologyEditor)
        editor._is_infrastructure_node = TopologyEditor._is_infrastructure_node.__get__(editor, TopologyEditor)
        editor._is_infrastructure_category = TopologyEditor._is_infrastructure_category
        editor._topology_node_type_for_editor_node = (
            TopologyEditor._topology_node_type_for_editor_node.__get__(editor, TopologyEditor)
        )

        topology = editor._topology_snapshot()

        self.assertEqual(topology["nodes"][0]["layout"]["y"], 450.0)
        self.assertFalse(topology["nodes"][0]["layout"]["yRelative"])

    def test_resolve_overlaps_keeps_vertically_separated_nodes_in_place(self) -> None:
        editor = TopologyEditor.__new__(TopologyEditor)
        editor._box_w = 90
        editor._box_h = 34
        editor._bus_offsets = [0.0]
        editor._bus_lefts = [40.0]
        editor._bus_rights = [400.0]
        editor._node_center_y_unscaled = TopologyEditor._node_center_y_unscaled.__get__(
            editor,
            TopologyEditor,
        )
        editor._nodes = [
            Node(key=1, category="neos", label="a", can_id=1, x=100.0, free_y=0.0),
            Node(key=2, category="neos", label="b", can_id=2, x=100.0, free_y=200.0),
        ]

        editor._resolve_overlaps()

        self.assertEqual([node.x for node in editor._nodes], [100.0, 100.0])

    def test_legacy_cannect_free_y_loads_as_absolute(self) -> None:
        editor = TopologyEditor.__new__(TopologyEditor)
        editor._cannect_device_links = [{"node": 1, "device": 2, "port": 1}]
        editor._nodes = [
            Node(
                key=1,
                category="cannect_direct",
                label="cannect 2",
                can_id=-1,
                free_y=900.0,
                profile_visible=False,
            ),
            Node(key=2, category="neos", label="motor1", can_id=1, free_y=920.0),
        ]
        editor._is_swyft_node = TopologyEditor._is_swyft_node
        editor._is_cannect_linked_device = TopologyEditor._is_cannect_linked_device.__get__(
            editor,
            TopologyEditor,
        )
        editor._is_cannect_cluster_member = TopologyEditor._is_cannect_cluster_member.__get__(
            editor,
            TopologyEditor,
        )

        editor._restore_legacy_cannect_free_y_mode()

        self.assertFalse(editor._nodes[0].free_y_relative)
        self.assertFalse(editor._nodes[1].free_y_relative)

    def test_bus_resize_clamps_cannect_diagram_nodes(self) -> None:
        editor = TopologyEditor.__new__(TopologyEditor)
        editor._box_w = 90
        editor._box_h = 34
        editor._bus_offsets = [0.0]
        editor._bus_lefts = [100.0]
        editor._bus_rights = [400.0]
        editor._nodes = [
            Node(
                key=1,
                category="cannect_inject",
                label="inject",
                can_id=-1,
                x=40.0,
                bus_index=0,
                profile_visible=False,
            ),
            Node(
                key=2,
                category="cannect_direct",
                label="cannect 2",
                can_id=-1,
                x=500.0,
                bus_index=0,
                profile_visible=False,
            ),
        ]
        editor._device_nodes = TopologyEditor._device_nodes.__get__(editor, TopologyEditor)
        editor._is_swyft_node = TopologyEditor._is_swyft_node

        editor._clamp_nodes_to_bus_bounds({0})

        self.assertEqual(editor._nodes[0].x, 120.0)
        self.assertEqual(editor._nodes[1].x, 380.0)

    def test_disable_all_connection_filters_hides_ethernet_links(self) -> None:
        editor = TopologyEditor.__new__(TopologyEditor)
        editor.canvas = _CanvasStub(width=1200, height=700)
        editor._nodes = [
            Node(
                key=1,
                category="cannect_direct",
                label="cannect 2",
                can_id=-1,
                node_type="diagram",
                interface=INTERFACE_CAN,
                vendor="SWYFT",
                motor="Wiring",
                x=150.0,
                row=1,
                bus_index=0,
                profile_visible=False,
            ),
            Node(
                key=2,
                category="cannect_direct",
                label="cannect 3",
                can_id=-1,
                node_type="diagram",
                interface=INTERFACE_CAN,
                vendor="SWYFT",
                motor="Wiring",
                x=450.0,
                row=1,
                bus_index=0,
                profile_visible=False,
            ),
        ]
        editor._box_w = 90
        editor._box_h = 34
        editor._layout_width = 600.0
        editor._bus_offsets = [0.0]
        editor._bus_lefts = [40.0]
        editor._bus_rights = [520.0]
        editor._bus_connectors = []
        editor._details_layout_shift = False
        editor._last_base_y = None
        editor._last_canvas_height = None
        editor._pan_y = 0.0
        editor._zoom = 1.0
        editor._draw_state = {}
        editor._drag_free_y = {}
        editor._selected_nodes = set()
        editor._selected_buses = set()
        editor._node_bounds = {}
        editor._guide_x = None
        editor._show_group_overlays_var = _BoolVarStub(False)
        editor._smart_guides_var = _BoolVarStub(False)
        editor._show_warn_badges_var = _BoolVarStub(False)
        editor._connection_filter_vars = {
            "can": _BoolVarStub(False),
            "power": _BoolVarStub(False),
            "dio": _BoolVarStub(False),
            "pwm": _BoolVarStub(False),
            "analog": _BoolVarStub(False),
            "virtual": _BoolVarStub(False),
        }
        editor._ethernet_links = [(1, 2)]
        editor._can_bus_links = []
        editor._cannect_device_links = []
        editor._attachment_links = []
        editor._dio_wiring_links = []
        editor._power_links = []
        editor._neighbor_links = []
        editor._neighbor_ports = []
        editor._show_group_overlays = lambda: None
        editor._draw_group_overlays = lambda: None
        editor._node_bounds = {}
        editor._bus_ys = []
        editor._device_nodes = TopologyEditor._device_nodes.__get__(editor, TopologyEditor)
        editor._callout_nodes = TopologyEditor._callout_nodes.__get__(editor, TopologyEditor)
        editor._connection_filter_allows = TopologyEditor._connection_filter_allows.__get__(
            editor, TopologyEditor
        )
        editor._should_clamp_node_to_bus = TopologyEditor._should_clamp_node_to_bus.__get__(
            editor, TopologyEditor
        )
        editor._node_box_dims = TopologyEditor._node_box_dims.__get__(editor, TopologyEditor)
        editor._node_bus_y = TopologyEditor._node_bus_y.__get__(editor, TopologyEditor)
        editor._node_box_y = TopologyEditor._node_box_y.__get__(editor, TopologyEditor)
        editor._is_dio_node = TopologyEditor._is_dio_node.__get__(editor, TopologyEditor)
        editor._is_swyft_node = TopologyEditor._is_swyft_node
        editor._fill_color_for_node = TopologyEditor._fill_color_for_node.__get__(editor, TopologyEditor)
        editor._text_color_for_fill = TopologyEditor._text_color_for_fill
        editor._shape_kind_for_node = TopologyEditor._shape_kind_for_node.__get__(editor, TopologyEditor)
        editor._draw_device_shape_on = TopologyEditor._draw_device_shape_on.__get__(editor, TopologyEditor)
        editor._dup_key_for_node = TopologyEditor._dup_key_for_node.__get__(editor, TopologyEditor)
        editor._node_center_y_unscaled = TopologyEditor._node_center_y_unscaled.__get__(editor, TopologyEditor)
        editor._fit_font_size = lambda _text, _max_w, _max_h, base_size: base_size

        editor._redraw_canvas()

        ethernet_lines = [
            line
            for line in editor.canvas.lines
            if line["kwargs"].get("fill") == "#1c6ba8"
        ]
        self.assertEqual(ethernet_lines, [])

    def test_mouse_wheel_zooms_without_ctrl_modifier(self) -> None:
        editor = TopologyEditor.__new__(TopologyEditor)
        calls: list[tuple[float, float, float]] = []
        editor.canvas = _CanvasStub(width=1000, height=500)
        editor._zoom_step = lambda delta, anchor_x=None, anchor_y=None: calls.append(
            (delta, float(anchor_x), float(anchor_y))
        )

        result = editor._on_zoom_wheel(_WheelEventStub(delta=120, x=123, y=234))

        self.assertEqual(result, "break")
        self.assertEqual(calls, [(0.1, 123.0, 234.0)])

    def test_linux_mouse_wheel_buttons_zoom(self) -> None:
        editor = TopologyEditor.__new__(TopologyEditor)
        calls: list[tuple[float, float, float]] = []
        editor.canvas = _CanvasStub(width=1000, height=500)
        editor._zoom_step = lambda delta, anchor_x=None, anchor_y=None: calls.append(
            (delta, float(anchor_x), float(anchor_y))
        )

        result_up = editor._on_zoom_wheel(_WheelEventStub(num=4, x=111, y=222))
        result_down = editor._on_zoom_wheel(_WheelEventStub(num=5, x=333, y=444))

        self.assertEqual(result_up, "break")
        self.assertEqual(result_down, "break")
        self.assertEqual(calls, [(0.1, 111.0, 222.0), (-0.1, 333.0, 444.0)])

    def test_middle_mouse_drag_pans_canvas(self) -> None:
        editor = TopologyEditor.__new__(TopologyEditor)
        editor.canvas = _CanvasStub()
        editor._pan_drag = (1.0, 2.0)
        editor._drag_state = (1, 2.0, 3.0)
        editor._multi_drag = {"start": (0.0, 0.0)}
        editor._bus_drag = (0, 1.0, 2.0)
        editor._bus_resize = (0, "left", 1.0, 2.0, 3.0)
        editor._selection_start = (4.0, 5.0)

        press_result = editor._on_canvas_pan_press(_PointerEventStub(12, 34))
        drag_result = editor._on_canvas_pan_drag(_PointerEventStub(56, 78))
        release_result = editor._on_canvas_pan_release(_PointerEventStub(56, 78))

        self.assertEqual(press_result, "break")
        self.assertEqual(drag_result, "break")
        self.assertEqual(release_result, "break")
        self.assertEqual(editor.canvas.scan_mark_args, (12, 34))
        self.assertEqual(editor.canvas.scan_dragto_args, (56, 78, 1))
        region = [float(part) for part in editor.canvas.scrollregion.split()]
        self.assertLess(region[0], 0.0)
        self.assertGreater(region[2], 1000.0)
        self.assertIsNotNone(editor.canvas.xview_value)
        self.assertIsNone(editor._pan_drag)
        self.assertIsNone(editor._drag_state)
        self.assertIsNone(editor._multi_drag)
        self.assertIsNone(editor._bus_drag)
        self.assertIsNone(editor._bus_resize)
        self.assertIsNone(editor._selection_start)

    def test_empty_canvas_click_clears_selection_without_pan(self) -> None:
        editor = TopologyEditor.__new__(TopologyEditor)
        editor.canvas = _CanvasStub()
        editor._clear_guides = lambda: None
        editor._selection_rect = None
        editor._selection_start = None
        editor._add_bus_mode = False
        editor._selected_nodes = {1}
        editor._selected_buses = set()
        editor._bus_hit_test = lambda _cy: None
        editor._pan_drag = None
        editor._tag_to_key = TopologyEditor._tag_to_key
        editor._shift_held = TopologyEditor._shift_held.__get__(editor, TopologyEditor)
        clear_calls: list[bool] = []

        def clear_selection() -> None:
            clear_calls.append(True)
            editor._selected_nodes = set()
            editor._selected_buses = set()

        editor._clear_selection = clear_selection

        editor._on_canvas_press(_PointerEventStub(20, 30))

        self.assertIsNone(editor._pan_drag)
        self.assertEqual(clear_calls, [True])
        self.assertEqual(editor._selected_nodes, set())

    def test_empty_canvas_click_with_no_selection_is_no_op(self) -> None:
        editor = TopologyEditor.__new__(TopologyEditor)
        editor.canvas = _CanvasStub()
        editor._clear_guides = lambda: None
        editor._selection_rect = None
        editor._selection_start = None
        editor._add_bus_mode = False
        editor._selected_nodes = set()
        editor._selected_buses = set()
        editor._bus_hit_test = lambda _cy: None
        editor._pan_drag = None
        editor._tag_to_key = TopologyEditor._tag_to_key
        editor._shift_held = TopologyEditor._shift_held.__get__(editor, TopologyEditor)
        clear_calls: list[bool] = []
        editor._clear_selection = lambda: clear_calls.append(True)

        editor._on_canvas_press(_PointerEventStub(20, 30))

        self.assertEqual(clear_calls, [])

    def test_clicking_already_selected_single_node_does_not_reselect(self) -> None:
        editor = TopologyEditor.__new__(TopologyEditor)
        editor.canvas = _CanvasStub()
        editor._clear_guides = lambda: None
        editor._selection_rect = None
        editor._selection_start = None
        editor._add_bus_mode = False
        editor._selected_nodes = {7}
        editor._selected_buses = set()
        editor._bus_hit_test = lambda _cy: None
        editor._pan_drag = None
        editor._shift_held = TopologyEditor._shift_held.__get__(editor, TopologyEditor)
        editor._tag_to_key = lambda _tags: 7
        editor.canvas.find_overlapping = lambda *_args: (1,)
        editor.canvas.gettags = lambda _item: ("node_7",)
        editor._nodes = [Node(key=7, category="krakens", label="motor7", can_id=7)]
        selection_calls: list[int] = []
        editor._set_single_node_selection = lambda key: selection_calls.append(key)
        editor._is_swyft_node = lambda _node: False
        editor._push_undo = lambda: None
        editor._drag_undo_pending = False

        editor._on_canvas_press(_PointerEventStub(20, 30))

        self.assertEqual(selection_calls, [])
        self.assertEqual(editor._drag_state, (7, 20.0, 30.0))

    def test_drag_start_does_not_hide_node_details_panel(self) -> None:
        editor = self._headless_editor("robot_2026_swerve")
        panel = _PanelStub()
        editor._node_details_panel = panel
        editor._dragging_active = False
        editor._selection_start = None
        editor._selection_rect = None
        editor._multi_drag = None
        editor._pan_drag = None
        editor._bus_drag = None
        editor._bus_resize = None
        editor._bus_connector_drag = None
        editor._drag_state = (7, 20.0, 30.0)
        editor._nodes = [Node(key=7, category="krakens", label="motor7", can_id=7, x=100.0)]
        editor._selected_nodes = {7}
        editor._guide_x = None
        editor._guide_bus = None
        editor._snap_to_grid_var = _BoolVarStub(False)
        editor._apply_smart_guides = lambda node, x, _selected: (x, None)
        editor._is_dio_node = lambda _node: False
        editor._redraw_canvas = lambda: None

        editor._on_canvas_drag(_PointerEventStub(30, 30))

        self.assertEqual(panel.pack_forget_calls, 0)
        self.assertTrue(editor._dragging_active)

    def test_preserve_canvas_view_restores_view_after_layout_change(self) -> None:
        editor = TopologyEditor.__new__(TopologyEditor)
        editor.canvas = _CanvasStub()
        editor.update_idletasks = lambda: None
        start_left = editor.canvas.canvasx(0.0)
        start_top = editor.canvas.canvasy(0.0)

        def shift_view() -> None:
            editor.canvas.xview_range = (0.45, 0.95)
            editor.canvas.yview_range = (0.55, 1.0)

        editor._preserve_canvas_view(shift_view)

        self.assertAlmostEqual(editor.canvas.canvasx(0.0), start_left)
        self.assertAlmostEqual(editor.canvas.canvasy(0.0), start_top)

    def test_fit_to_window_then_empty_click_preserves_view_and_clears_selection(self) -> None:
        editor = TopologyEditor.__new__(TopologyEditor)
        editor.canvas = _CanvasStub(width=1000, height=500)
        editor._box_w = 90
        editor._box_h = 34
        editor._bus_offsets = [0.0]
        editor._bus_lefts = [40.0]
        editor._bus_rights = [400.0]
        editor._zoom = 1.0
        editor._pan_y = 0.0
        editor._layout_width = 1000
        editor._dirty = False
        editor._zoom_label_var = _StringVarStub()
        editor._clear_guides = lambda: None
        editor._selection_rect = None
        editor._selection_start = None
        editor._add_bus_mode = False
        editor._selected_nodes = {1}
        editor._selected_buses = set()
        editor._bus_hit_test = lambda _cy: None
        editor._pan_drag = None
        editor._tag_to_key = TopologyEditor._tag_to_key
        editor._shift_held = TopologyEditor._shift_held.__get__(editor, TopologyEditor)
        editor._redraw_canvas = lambda: None
        editor.update_idletasks = lambda: None
        editor._device_nodes = TopologyEditor._device_nodes.__get__(editor, TopologyEditor)
        editor._callout_nodes = TopologyEditor._callout_nodes.__get__(editor, TopologyEditor)
        editor._node_center_y_unscaled = TopologyEditor._node_center_y_unscaled.__get__(
            editor,
            TopologyEditor,
        )
        editor._nodes = [
            Node(
                key=1,
                category="neos",
                label="driveMotor",
                can_id=2,
                interface=INTERFACE_CAN,
                vendor="REV",
                device_type="NEO",
                motor="REV NEO",
                free_y=1000.0,
            )
        ]

        editor._fit_to_window()
        fit_xview = editor.canvas.xview_value
        fit_yview = editor.canvas.yview_value
        fit_left = editor.canvas.canvasx(0.0)
        fit_top = editor.canvas.canvasy(0.0)
        editor.canvas.xview_range = (fit_xview, min(1.0, fit_xview + 0.5))
        editor.canvas.yview_range = (fit_yview, min(1.0, fit_yview + 0.5))

        def clear_selection() -> None:
            editor._selected_nodes = set()
            editor._selected_buses = set()
            editor._preserve_canvas_view(
                lambda: (
                    setattr(editor.canvas, "xview_range", (0.7, 1.0)),
                    setattr(editor.canvas, "yview_range", (0.6, 1.0)),
                )
            )

        editor._clear_selection = clear_selection

        editor._on_canvas_press(_PointerEventStub(20, 30))

        self.assertEqual(editor._selected_nodes, set())
        self.assertAlmostEqual(editor.canvas.canvasx(0.0), fit_left)
        self.assertAlmostEqual(editor.canvas.canvasy(0.0), fit_top)

    def test_apply_topology_snapshot_restores_attachment_links(self) -> None:
        editor = TopologyEditor.__new__(TopologyEditor)
        editor._nodes = [
            Node(key=10, category="roborio", label="roborio", can_id=0, x=0.0, bus_index=0),
            Node(key=11, category="pdp", label="PDP", can_id=1, x=20.0, bus_index=0),
            Node(
                key=12,
                category="devices",
                label="lsw1",
                can_id=-1,
                interface=INTERFACE_DIO,
                x=40.0,
                bus_index=0,
            ),
        ]
        editor._connection_filter_vars = {
            "can": _BoolVarStub(True),
            "power": _BoolVarStub(True),
            "dio": _BoolVarStub(True),
            "pwm": _BoolVarStub(True),
            "analog": _BoolVarStub(True),
            "virtual": _BoolVarStub(True),
        }
        editor._ensure_bus_connectors = lambda _count: None
        editor._editor_category_for_topology_node = lambda entry: "devices"
        editor._normalize_tags = lambda value: []
        editor._mark_neighbors_current = lambda: None
        editor._prune_attachment_links = lambda: False
        editor._prune_power_links = lambda: False
        editor._prune_dio_wiring_links = lambda: False
        editor._ensure_dio_wiring_links = lambda: False
        editor._fix_cannect_conflicts = lambda notify=False: None
        editor._apply_cannect_free_float = lambda: None
        editor._resolve_overlaps = lambda: None
        editor._device_nodes = TopologyEditor._device_nodes.__get__(editor, TopologyEditor)

        editor._apply_topology_snapshot(
            {
                "nodes": [
                    {"key": 1, "nodeType": "device", "deviceRef": "roborio", "layout": {"bus": 0, "row": 0, "x": 0.0}},
                    {"key": 2, "nodeType": "device", "deviceRef": "PDP", "layout": {"bus": 0, "row": 0, "x": 20.0}},
                    {"key": 3, "nodeType": "device", "deviceRef": "lsw1", "layout": {"bus": 0, "row": 1, "x": 40.0}},
                ],
                "edges": [
                    {
                        "id": "edge_1",
                        "fromNode": 1,
                        "fromPort": "power",
                        "toNode": 2,
                        "toPort": "power",
                        "edgeType": "power",
                    },
                    {
                        "id": "edge_2",
                        "fromNode": 2,
                        "fromPort": "attachment",
                        "toNode": 3,
                        "toPort": "attachment",
                        "edgeType": "virtual",
                    }
                ],
                "view": {},
            }
        )

        self.assertEqual(editor._attachment_links, [{"device": 2, "attachment": 3}])
        self.assertEqual(editor._power_links, [{"a": 1, "b": 2}])

    def test_print_or_open_pdf_opens_when_pdf_print_handler_missing(self) -> None:
        editor = TopologyEditor.__new__(TopologyEditor)
        editor._windows_pdf_print_handler_available = lambda: False
        startfile_calls: list[tuple[object, ...]] = []
        info_calls: list[tuple[object, ...]] = []

        def _startfile_stub(*args: object) -> None:
            startfile_calls.append(args)

        messagebox_stub = type(
            "_PrintMessageBoxStub",
            (),
            {
                "showinfo": staticmethod(lambda *args, **_kwargs: info_calls.append(args)),
                "showerror": staticmethod(lambda *args, **_kwargs: (_ for _ in ()).throw(RuntimeError(str(args)))),
            },
        )
        original_startfile = os.startfile
        original_messagebox = can_top_editor.messagebox
        os.startfile = _startfile_stub
        can_top_editor.messagebox = messagebox_stub
        try:
            editor._print_or_open_pdf("C:\\temp\\diagram.pdf", can_top_editor.MSG_PRINTED_DIAGRAM)
        finally:
            os.startfile = original_startfile
            can_top_editor.messagebox = original_messagebox

        self.assertEqual(startfile_calls, [("C:\\temp\\diagram.pdf",)])
        self.assertEqual(info_calls, [("Print", can_top_editor.MSG_PRINT_NO_HANDLER)])

    def test_print_or_open_pdf_uses_print_verb_when_handler_exists(self) -> None:
        editor = TopologyEditor.__new__(TopologyEditor)
        editor._windows_pdf_print_handler_available = lambda: True
        startfile_calls: list[tuple[object, ...]] = []
        info_calls: list[tuple[object, ...]] = []

        def _startfile_stub(*args: object) -> None:
            startfile_calls.append(args)

        messagebox_stub = type(
            "_PrintMessageBoxStub",
            (),
            {
                "showinfo": staticmethod(lambda *args, **_kwargs: info_calls.append(args)),
                "showerror": staticmethod(lambda *args, **_kwargs: (_ for _ in ()).throw(RuntimeError(str(args)))),
            },
        )
        original_startfile = os.startfile
        original_messagebox = can_top_editor.messagebox
        os.startfile = _startfile_stub
        can_top_editor.messagebox = messagebox_stub
        try:
            editor._print_or_open_pdf("C:\\temp\\diagram.pdf", can_top_editor.MSG_PRINTED_DIAGRAM)
        finally:
            os.startfile = original_startfile
            can_top_editor.messagebox = original_messagebox

        self.assertEqual(startfile_calls, [("C:\\temp\\diagram.pdf", "print")])
        self.assertEqual(
            info_calls,
            [("Printed", can_top_editor.MSG_PRINTED_DIAGRAM.format("C:\\temp\\diagram.pdf"))],
        )

    def test_export_pdf_handles_attachment_links_without_name_error(self) -> None:
        editor = self._headless_editor("pdf_export")
        editor._zoom = 1.0
        editor._pan_y = 0.0
        editor._box_w = 90
        editor._box_h = 34
        editor._bus_offsets = [0.0]
        editor._bus_lefts = [40.0]
        editor._bus_rights = [500.0]
        editor._show_warn_badges_var = _BoolVarStub(False)
        editor._node_bounds = {}
        editor._redraw_canvas = lambda: None
        editor._tags_to_string = lambda tags: ",".join(tags or [])
        editor._list_sort_var.set("can_id")
        editor._attachment_links = [{"device": 1, "attachment": 2}]
        editor._power_links = []
        editor._dio_wiring_links = []
        editor._ethernet_links = []
        editor._cannect_device_links = []
        editor._can_bus_links = []
        editor._nodes = [
            Node(
                key=1,
                category="krakens",
                label="driveMotor",
                can_id=2,
                interface=INTERFACE_CAN,
                vendor="CTRE",
                device_type="Kraken X60",
                motor="Kraken X60",
                x=120.0,
                free_y=100.0,
            ),
            Node(
                key=2,
                category="devices",
                label="limit0",
                can_id=-1,
                interface=INTERFACE_DIO,
                device_type="limitSwitch",
                dio=0,
                x=260.0,
                free_y=160.0,
            ),
        ]
        original_messagebox = can_top_editor.messagebox
        can_top_editor.messagebox = _MessageBoxStub
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                path = Path(temp_dir) / "diagram.pdf"
                editor._export_pdf(print_after=False, path_override=str(path))
                self.assertTrue(path.exists())
                self.assertGreater(path.stat().st_size, 0)
        finally:
            can_top_editor.messagebox = original_messagebox


if __name__ == "__main__":
    unittest.main()
