from __future__ import annotations

import unittest

from tools.can_topology import live_topology_view as live_view_module
from tools.common import topology_draw


class _BoolVarStub:
    def __init__(self, value: bool) -> None:
        self.value = value

    def get(self) -> bool:
        return self.value

    def set(self, value: bool) -> None:
        self.value = bool(value)


class _StringVarStub:
    def __init__(self, value: str = "") -> None:
        self.value = value

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = str(value)


class _LabelStub:
    def __init__(self) -> None:
        self.text = ""
        self.bg = None
        self.fg = None

    def configure(self, **kwargs) -> None:
        if "text" in kwargs:
            self.text = str(kwargs["text"])
        if "bg" in kwargs:
            self.bg = kwargs["bg"]
        if "fg" in kwargs:
            self.fg = kwargs["fg"]


class _PanelStub:
    def __init__(self) -> None:
        self.bg = None
        self.highlightbackground = None

    def configure(self, **kwargs) -> None:
        if "bg" in kwargs:
            self.bg = kwargs["bg"]
        if "highlightbackground" in kwargs:
            self.highlightbackground = kwargs["highlightbackground"]


class _CanvasStub:
    def __init__(self) -> None:
        self.mark = None
        self.drag = None
        self.xview = None
        self.yview = None
        self.scrollregion = "0 0 1000 1000"

    def scan_mark(self, x: int, y: int) -> None:
        self.mark = (x, y)

    def scan_dragto(self, x: int, y: int, gain: int = 1) -> None:
        self.drag = (x, y, gain)

    def cget(self, key: str) -> str:
        if key == "scrollregion":
            return self.scrollregion
        return ""

    def configure(self, **kwargs) -> None:
        if "scrollregion" in kwargs:
            region = kwargs["scrollregion"]
            self.scrollregion = " ".join(str(value) for value in region)

    def winfo_width(self) -> int:
        return 800

    def winfo_height(self) -> int:
        return 600

    def canvasx(self, value: int) -> float:
        return float(value)

    def canvasy(self, value: int) -> float:
        return float(value)

    def xview_moveto(self, fraction: float) -> None:
        self.xview = fraction

    def yview_moveto(self, fraction: float) -> None:
        self.yview = fraction


class _ShapeCanvasStub:
    def __init__(self) -> None:
        self.calls = []
        self._next_id = 1

    def _record(self, kind: str, *args, **kwargs) -> int:
        item_id = self._next_id
        self._next_id += 1
        self.calls.append((kind, args, kwargs))
        return item_id

    def create_polygon(self, *args, **kwargs) -> int:
        return self._record("polygon", *args, **kwargs)

    def create_rectangle(self, *args, **kwargs) -> int:
        return self._record("rectangle", *args, **kwargs)


class LiveTopologyViewTests(unittest.TestCase):
    """
    NAME
        LiveTopologyViewTests - Validate live topology filter behavior.
    """

    def _make_view(self) -> live_view_module.LiveTopologyView:
        view = live_view_module.LiveTopologyView.__new__(live_view_module.LiveTopologyView)
        view._profile_name = "demo"
        view._nodes = []
        view._diagram_meta = {}
        view._bridge_groups = []
        view._runtime_state = {}
        view._presence_overrides = {}
        view._visibility_enabled = False
        view._visibility_state = {}
        view._visibility_sources = {}
        view._visibility_fingerprint = None
        view._selected_label = None
        view._selected_enabled = None
        view._bus_offsets = [0.0]
        view._bus_spacing = 160.0
        view._bus_lefts = []
        view._bus_rights = []
        view._pan_y = 0.0
        view._zoom = 1.0
        view._node_bounds = {}
        view._selected_node = None
        view._use_diagram_layout = False
        view._ethernet_links = []
        view._can_links = []
        view._device_links = []
        view._show_groups = True
        view._runtime_fingerprint = None
        view._runtime_state_seen = False
        view._runtime_state_notice_text = ""
        view._runtime_event_notice_text = ""
        view._active_group_summary_var = None
        view._active_group_status_var = None
        view._detail_vars = {}
        view._group_inspector_name = ""
        view._group_inspector_targets = []
        view._connection_filter_vars = {
            key: _BoolVarStub(True) for key in live_view_module.CONNECTION_FILTERS_ORDER
        }
        view._status_label = _LabelStub()
        view._canvas = _CanvasStub()
        view.update_idletasks = lambda: None
        view._redraw = lambda *_args, **_kwargs: None
        return view

    def test_filter_helpers_toggle_all_and_none(self) -> None:
        view = self._make_view()

        view._disable_all_connection_filters()
        self.assertEqual(view._active_connection_filters(), set())

        view._enable_all_connection_filters()
        self.assertEqual(
            view._active_connection_filters(),
            set(live_view_module.CONNECTION_FILTERS_ORDER),
        )

    def test_refresh_runtime_notice_waits_for_runtime_state_before_showing_ready(self) -> None:
        view = self._make_view()
        view._runtime_state_seen = False
        view._runtime_state_notice_text = ""
        view._runtime_event_notice_text = ""
        view._runnable_scope_headline_var = _StringVarStub("")
        view._runnable_scope_detail_var = _StringVarStub("")
        view._notice_panel = _PanelStub()
        view._notice_title_label = _LabelStub()
        view._notice_headline_label = _LabelStub()
        view._notice_detail_label = _LabelStub()

        view._refresh_runtime_notice()

        self.assertEqual("WAITING FOR STATE", view._runnable_scope_headline_var.get())
        self.assertEqual(
            "waiting for robot runtime state",
            view._runnable_scope_detail_var.get(),
        )

    def test_update_runtime_state_marks_runtime_state_seen(self) -> None:
        view = self._make_view()
        view._runtime_state_seen = False
        view._runnable_scope_headline_var = _StringVarStub("")
        view._runnable_scope_detail_var = _StringVarStub("")
        view._notice_panel = _PanelStub()
        view._notice_title_label = _LabelStub()
        view._notice_headline_label = _LabelStub()
        view._notice_detail_label = _LabelStub()
        view._update_details = lambda: None

        view.update_runtime_state({"enabled": True, "devices": []})

        self.assertTrue(view._runtime_state_seen)

    def test_active_group_members_not_editable_before_runtime_state(self) -> None:
        view = self._make_view()
        view._runtime_state_seen = False
        view._controlled_lifecycle_active = False

        self.assertFalse(view._active_group_members_editable())

    def test_active_group_members_not_editable_during_controlled_lifecycle(self) -> None:
        view = self._make_view()
        view._runtime_state_seen = True
        view._controlled_lifecycle_active = True

        self.assertFalse(view._active_group_members_editable())

    def test_active_group_members_editable_after_runtime_state_when_unlocked(self) -> None:
        view = self._make_view()
        view._runtime_state_seen = True
        view._controlled_lifecycle_active = False

        self.assertTrue(view._active_group_members_editable())

    def test_runtime_notice_requires_activation_before_manual_run(self) -> None:
        view = self._make_view()
        notices = []
        view.set_runtime_state_notice = lambda text, level="warn": notices.append((text, level))
        view.clear_runtime_state_notice = lambda: notices.append(("__clear__", "clear"))

        view._apply_runtime_notice_from_state(False, False, True, False)

        self.assertEqual(
            [("Activate Group first.", "warn")],
            notices,
        )

    def test_runtime_notice_is_ready_when_controlled_scope_is_active(self) -> None:
        view = self._make_view()
        notices = []
        view.set_runtime_state_notice = lambda text, level="warn": notices.append((text, level))
        view.clear_runtime_state_notice = lambda: notices.append(("__clear__", "clear"))

        view._apply_runtime_notice_from_state(False, True, True, False)

        self.assertEqual([("__clear__", "clear")], notices)

    def test_runtime_notice_prefers_disabled_over_activation_blocker(self) -> None:
        view = self._make_view()
        notices = []
        view.set_runtime_state_notice = lambda text, level="warn": notices.append((text, level))
        view.clear_runtime_state_notice = lambda: notices.append(("__clear__", "clear"))

        view._apply_runtime_notice_from_state(False, False, False, False)

        self.assertEqual(
            [("Robot disabled. Enable teleop to run motors.", "info")],
            notices,
        )

    def test_active_group_status_waits_for_runtime_state(self) -> None:
        view = self._make_view()
        view._runtime_state_seen = False

        self.assertEqual(
            live_view_module.ACTIVE_GROUP_STATUS_WAITING_TEXT,
            view._active_group_status_text({"name": "active-group"}, {"falcon 9": {}}),
        )

    def test_active_group_status_reports_empty_group(self) -> None:
        view = self._make_view()
        view._runtime_state_seen = True
        view._controlled_lifecycle_active = False

        self.assertEqual(
            live_view_module.ACTIVE_GROUP_STATUS_EMPTY_TEXT,
            view._active_group_status_text({"name": "active-group"}, {}),
        )

    def test_active_group_status_reports_editable_when_inactive(self) -> None:
        view = self._make_view()
        view._runtime_state_seen = True
        view._controlled_lifecycle_active = False

        self.assertEqual(
            live_view_module.ACTIVE_GROUP_STATUS_EDITABLE_TEXT,
            view._active_group_status_text({"name": "active-group"}, {"falcon 9": {}}),
        )

    def test_active_group_status_reports_ready_when_active_members_present(self) -> None:
        view = self._make_view()
        view._runtime_state_seen = True
        view._controlled_lifecycle_active = True
        view._runtime_state = {
            "falcon 9": {"presenceConfidence": 1.0},
            "sparkmax/neo 25": {"presenceConfidence": 1.0},
        }

        self.assertEqual(
            live_view_module.ACTIVE_GROUP_STATUS_READY_TEXT,
            view._active_group_status_text(
                {"name": "active-group"},
                {"falcon 9": {}, "sparkmax/neo 25": {}},
            ),
        )

    def test_active_group_status_reports_locked_when_active_members_not_present(self) -> None:
        view = self._make_view()
        view._runtime_state_seen = True
        view._controlled_lifecycle_active = True
        view._runtime_state = {"falcon 9": {"presenceConfidence": 0.0}}

        self.assertEqual(
            live_view_module.ACTIVE_GROUP_STATUS_LOCKED_TEXT,
            view._active_group_status_text({"name": "active-group"}, {"falcon 9": {}}),
        )

    def test_reload_profile_applies_saved_connection_filters(self) -> None:
        view = self._make_view()

        original_load_payload = live_view_module._load_profiles_payload
        original_load_registry = live_view_module._load_device_registry
        try:
            payload = {
                "default_profile": "demo",
                "profiles": {"demo": {"devices": ["roborio", "motor1"]}},
                "devices": [
                    {"label": "roborio", "deviceInterface": "CAN", "manufacturer": 1, "deviceType": 1, "id": 0},
                    {"label": "motor1", "deviceInterface": "CAN", "manufacturer": 5, "deviceType": 2, "id": 25},
                ],
                "topology": {
                    "profiles": {
                        "demo": {
                            "nodes": [
                                {
                                    "key": 1,
                                    "nodeType": "device",
                                    "deviceRef": "roborio",
                                    "layout": {"bus": 0, "row": 0, "x": 0.0},
                                },
                                {
                                    "key": 2,
                                    "nodeType": "device",
                                    "deviceRef": "motor1",
                                    "layout": {"bus": 0, "row": 0, "x": 100.0},
                                },
                            ],
                            "edges": [
                                {
                                    "id": "edge_1",
                                    "fromNode": 1,
                                    "fromPort": "right",
                                    "toNode": 2,
                                    "toPort": "left",
                                    "edgeType": "can_trunk",
                                }
                            ],
                            "view": {
                                "connectionFilters": ["can", "power"],
                            },
                        }
                    }
                },
            }
            live_view_module._load_profiles_payload = lambda: (payload, "")
            live_view_module._load_device_registry = lambda _payload: {
                "roborio": payload["devices"][0],
                "motor1": payload["devices"][1],
            }

            view.reload_profile("demo")

            self.assertEqual(view._active_connection_filters(), {"can", "power"})
            self.assertEqual(view._status_label.text, "Profile: demo")
        finally:
            live_view_module._load_profiles_payload = original_load_payload
            live_view_module._load_device_registry = original_load_registry

    def test_middle_button_pan_uses_canvas_scan(self) -> None:
        view = self._make_view()

        press_result = view._on_canvas_pan_press(type("Event", (), {"x": 10, "y": 20})())
        drag_result = view._on_canvas_pan_drag(type("Event", (), {"x": 40, "y": 60})())
        release_result = view._on_canvas_pan_release(None)

        self.assertEqual(press_result, "break")
        self.assertEqual(drag_result, "break")
        self.assertEqual(release_result, "break")
        self.assertEqual(view._canvas.mark, (10, 20))
        self.assertEqual(view._canvas.drag, (40, 60, live_view_module.CANVAS_PAN_GAIN))

    def test_fit_to_window_updates_zoom_pan_and_view(self) -> None:
        view = self._make_view()
        view._nodes = [
            live_view_module.LiveNode(
                key=1,
                category="roborio",
                label="roborio",
                can_id=0,
                bus_index=0,
                row=0,
                x=100.0,
            ),
            live_view_module.LiveNode(
                key=2,
                category="pdh",
                label="pdh",
                can_id=1,
                bus_index=0,
                row=1,
                x=900.0,
            ),
        ]
        redraw_calls = []
        view._redraw = lambda *_args, **_kwargs: redraw_calls.append(True)

        view._fit_to_window()

        self.assertTrue(redraw_calls)
        self.assertGreaterEqual(view._zoom, live_view_module.ZOOM_MIN)
        self.assertLessEqual(view._zoom, live_view_module.ZOOM_MAX)
        self.assertIsNotNone(view._canvas.xview)
        self.assertEqual(view._canvas.yview, 0.0)

    def test_selected_canvas_shape_overlay_draws_halo_and_outline(self) -> None:
        canvas = _ShapeCanvasStub()

        ids = topology_draw.draw_selected_canvas_shape_overlay(
            canvas,
            10.0,
            20.0,
            110.0,
            70.0,
            "motor",
            halo_color="#ffffff",
            outline_color="#1f6feb",
        )

        self.assertEqual(len(ids), 2)
        self.assertEqual(len(canvas.calls), 2)
        first_kind, _first_args, first_kwargs = canvas.calls[0]
        second_kind, _second_args, second_kwargs = canvas.calls[1]
        self.assertEqual(first_kind, "polygon")
        self.assertEqual(second_kind, "polygon")
        self.assertEqual(first_kwargs["fill"], "")
        self.assertEqual(first_kwargs["outline"], "#ffffff")
        self.assertEqual(
            first_kwargs["width"],
            topology_draw.SELECTION_SHAPE_HALO_WIDTH,
        )
        self.assertEqual(second_kwargs["fill"], "")
        self.assertEqual(second_kwargs["outline"], "#1f6feb")
        self.assertEqual(
            second_kwargs["width"],
            topology_draw.SELECTION_SHAPE_OUTLINE_WIDTH,
        )

    def test_canvas_click_selects_node_and_triggers_redraw(self) -> None:
        view = self._make_view()
        redraw_calls = []
        selection_events = []
        details_calls = []
        node = live_view_module.LiveNode(
            key=25,
            category="neos",
            label="SPARKMAX/NEO 25",
            can_id=25,
            bus_index=0,
            row=0,
            x=0.0,
        )
        view._nodes = [node]
        view._node_bounds = {25: (10.0, 20.0, 110.0, 70.0)}
        view._redraw = lambda *_args, **_kwargs: redraw_calls.append(True)
        view._update_details = lambda: details_calls.append(True)
        view._on_selection_changed_cb = lambda selected: selection_events.append(selected)
        view._on_left_click_cb = None

        view._on_canvas_click(type("Event", (), {"x": 50, "y": 40})())

        self.assertIs(view._selected_node, node)
        self.assertTrue(details_calls)
        self.assertTrue(redraw_calls)
        self.assertEqual(selection_events, [node])

    def test_diagram_nodes_preserve_topology_layout_y_and_registry_category(self) -> None:
        registry = {
            "frontleft encoder": {
                "label": "frontLeft Encoder",
                "deviceInterface": "CAN",
                "manufacturer": 4,
                "deviceType": 7,
                "id": 3,
            }
        }
        diagram = {
            "nodes": [
                {
                    "key": 5,
                    "nodeType": "device",
                    "deviceRef": "frontLeft Encoder",
                    "layout": {
                        "bus": 0,
                        "row": 1,
                        "x": 120.0,
                        "y": 64.0,
                        "yRelative": False,
                    },
                },
                {
                    "key": 16,
                    "nodeType": "junction",
                    "label": "cannect 3",
                    "category": "cannect_direct",
                    "vendor": "SWYFT",
                    "layout": {
                        "bus": 0,
                        "row": 1,
                        "x": 220.0,
                        "y": 180.0,
                        "yRelative": False,
                    },
                },
            ],
            "view": {
                "busOffsets": [-20.0],
            },
        }

        nodes, _meta = live_view_module._diagram_nodes(diagram, registry)

        self.assertEqual(len(nodes), 2)
        encoder = next(node for node in nodes if node.label == "frontLeft Encoder")
        cannect = next(node for node in nodes if node.label == "cannect 3")
        self.assertEqual(encoder.category, "cancoders")
        self.assertEqual(encoder.vendor, "CTRE")
        self.assertEqual(encoder.device_type, "7")
        self.assertEqual(encoder.free_y, 84.0)
        self.assertEqual(encoder.node_class, "device")
        self.assertEqual(cannect.category, "cannect_direct")
        self.assertEqual(cannect.node_type, "diagram")
        self.assertEqual(cannect.node_class, "infrastructure")
        self.assertEqual(cannect.free_y, 200.0)

    def test_diagram_nodes_accept_object_type_without_legacy_node_type(self) -> None:
        registry = {
            "roborio": {
                "label": "roborio",
                "deviceInterface": "CAN",
                "manufacturer": 1,
                "deviceType": 1,
                "id": 0,
            }
        }
        diagram = {
            "nodes": [
                {
                    "key": 1,
                    "objectType": "device",
                    "deviceRef": "roborio",
                    "layout": {"bus": 0, "row": 0, "x": 0.0},
                },
                {
                    "key": 2,
                    "objectType": "junction",
                    "label": "cannect 3",
                    "category": "cannect_direct",
                    "layout": {"bus": 0, "row": 0, "x": 100.0},
                },
            ]
        }

        nodes, _meta = live_view_module._diagram_nodes(diagram, registry)

        self.assertEqual([node.label for node in nodes], ["roborio", "cannect 3"])
        self.assertEqual(nodes[0].node_type, "device")
        self.assertEqual(nodes[0].node_class, "device")
        self.assertEqual(nodes[1].node_type, "diagram")
        self.assertEqual(nodes[1].node_class, "infrastructure")

    def test_reload_profile_preserves_canonical_layout_y_in_live_nodes(self) -> None:
        view = self._make_view()

        original_load_payload = live_view_module._load_profiles_payload
        original_load_registry = live_view_module._load_device_registry
        try:
            payload = {
                "default_profile": "demo",
                "profiles": {"demo": {"devices": ["roborio", "motor1"]}},
                "devices": [
                    {
                        "label": "roborio",
                        "deviceInterface": "CAN",
                        "manufacturer": 1,
                        "deviceType": 1,
                        "id": 0,
                    },
                    {
                        "label": "motor1",
                        "deviceInterface": "CAN",
                        "manufacturer": 5,
                        "deviceType": 2,
                        "id": 25,
                    },
                ],
                "topology": {
                    "profiles": {
                        "demo": {
                            "nodes": [
                                {
                                    "key": 1,
                                    "nodeType": "device",
                                    "deviceRef": "roborio",
                                    "layout": {
                                        "bus": 0,
                                        "row": 0,
                                        "x": 0.0,
                                        "y": -40.0,
                                        "yRelative": True,
                                    },
                                },
                                {
                                    "key": 2,
                                    "nodeType": "device",
                                    "deviceRef": "motor1",
                                    "layout": {
                                        "bus": 0,
                                        "row": 1,
                                        "x": 100.0,
                                        "y": 180.0,
                                        "yRelative": False,
                                    },
                                },
                            ],
                            "view": {
                                "busOffsets": [25.0],
                                "connectionFilters": ["can"],
                            },
                        }
                    }
                },
            }
            live_view_module._load_profiles_payload = lambda: (payload, "")
            live_view_module._load_device_registry = lambda _payload: {
                "roborio": payload["devices"][0],
                "motor1": payload["devices"][1],
            }

            view.reload_profile("demo")

            roborio = next(node for node in view._nodes if node.label == "roborio")
            motor = next(node for node in view._nodes if node.label == "motor1")
            self.assertEqual(roborio.free_y, -40.0)
            self.assertEqual(motor.free_y, 155.0)
            self.assertEqual(view._bus_offsets, [25.0])
        finally:
            live_view_module._load_profiles_payload = original_load_payload
            live_view_module._load_device_registry = original_load_registry

    def test_reload_profile_refreshes_active_group_details_immediately(self) -> None:
        view = self._make_view()
        view._update_details_calls = 0
        view._update_details = lambda: setattr(
            view, "_update_details_calls", view._update_details_calls + 1
        )

        original_load_payload = live_view_module._load_profiles_payload
        original_load_registry = live_view_module._load_device_registry
        original_parse_bridge_groups = live_view_module.parse_bridge_groups
        original_redraw = view._redraw

        try:
            live_view_module._load_profiles_payload = lambda: (
                {
                    "defaultProfile": "demo",
                    "profiles": {
                        "demo": {
                            "devices": [
                                {"label": "FALCON 9", "type": "motor", "deviceType": 2, "id": 9},
                            ]
                        }
                    },
                },
                "",
            )
            live_view_module._load_device_registry = lambda _payload: {}
            live_view_module.parse_bridge_groups = lambda _payload, _profile: []
            view._redraw = lambda *_args, **_kwargs: None

            view.reload_profile("demo")

            self.assertEqual(1, view._update_details_calls)
        finally:
            live_view_module._load_profiles_payload = original_load_payload
            live_view_module._load_device_registry = original_load_registry
            live_view_module.parse_bridge_groups = original_parse_bridge_groups
            view._redraw = original_redraw

    def test_reload_profile_error_clears_active_group_details_immediately(self) -> None:
        view = self._make_view()
        view._update_details_calls = 0
        view._update_details = lambda: setattr(
            view, "_update_details_calls", view._update_details_calls + 1
        )

        original_load_payload = live_view_module._load_profiles_payload
        original_redraw = view._redraw

        try:
            live_view_module._load_profiles_payload = lambda: (None, "load failed")
            view._redraw = lambda *_args, **_kwargs: None

            view.reload_profile("demo")

            self.assertEqual(1, view._update_details_calls)
        finally:
            live_view_module._load_profiles_payload = original_load_payload
            view._redraw = original_redraw

    def test_effective_groups_preserve_static_members_when_runtime_group_only_has_counts(self) -> None:
        view = self._make_view()
        view._bridge_groups = [
            {
                "name": "motors",
                "enabled": True,
                "members": [
                    {"label": "SPARKMAX/NEO 25", "enabled": True},
                    {"label": "FALCON 9", "enabled": True},
                ],
                "bindings": [{"input": "controller0.rightY", "kind": "analog"}],
            }
        ]
        view._runtime_groups = [
            {
                "name": "motors",
                "enabled": True,
                "memberCount": 2,
                "bindingCount": 1,
            }
        ]

        groups = view._effective_groups()

        self.assertEqual(1, len(groups))
        self.assertEqual("motors", groups[0]["name"])
        self.assertEqual(
            [
                {"label": "SPARKMAX/NEO 25", "enabled": True},
                {"label": "FALCON 9", "enabled": True},
            ],
            groups[0]["members"],
        )
        self.assertEqual(
            [{"input": "controller0.rightY", "kind": "analog"}],
            groups[0]["bindings"],
        )
