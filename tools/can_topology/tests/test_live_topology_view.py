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
