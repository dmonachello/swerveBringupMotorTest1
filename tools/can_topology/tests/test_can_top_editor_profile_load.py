from __future__ import annotations

import unittest

from tools.can_topology.can_top_editor import TopologyEditor
from tools.can_topology.can_top_models import INTERFACE_CAN, INTERFACE_DIO, Node


class _StringVarStub:
    """
    NAME
        _StringVarStub - Minimal StringVar stand-in for headless editor tests.
    """

    def __init__(self) -> None:
        self.value = ""

    def set(self, value: str) -> None:
        self.value = value


class _BoolVarStub:
    def __init__(self, value: bool) -> None:
        self.value = value

    def get(self) -> bool:
        return self.value

    def set(self, value: bool) -> None:
        self.value = bool(value)


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
                {"nodes": [{"key": 1, "nodeType": "device", "deviceRef": "motor1"}], "edges": []}
            )
        )

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
                {"key": 1, "nodeType": "device", "deviceRef": "roborio", "layout": {"bus": 0, "row": 0, "x": 10.0}},
                {"key": 2, "nodeType": "device", "deviceRef": "motor1", "layout": {"bus": 0, "row": 0, "x": 30.0}},
                {"key": 3, "nodeType": "device", "deviceRef": "lsw1", "layout": {"bus": 0, "row": 1, "x": 50.0}},
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


if __name__ == "__main__":
    unittest.main()
