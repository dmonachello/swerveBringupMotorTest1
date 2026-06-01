from __future__ import annotations

import unittest

from tools.can_topology import live_topology_view as live_view_module


class _BoolVarStub:
    def __init__(self, value: bool) -> None:
        self.value = value

    def get(self) -> bool:
        return self.value

    def set(self, value: bool) -> None:
        self.value = bool(value)


class _LabelStub:
    def __init__(self) -> None:
        self.text = ""

    def configure(self, **kwargs) -> None:
        if "text" in kwargs:
            self.text = str(kwargs["text"])


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

    def xview_moveto(self, fraction: float) -> None:
        self.xview = fraction

    def yview_moveto(self, fraction: float) -> None:
        self.yview = fraction


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
