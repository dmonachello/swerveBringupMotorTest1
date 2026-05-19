from __future__ import annotations

import unittest
from pathlib import Path

from tools.can_topology.can_top_editor import TopologyEditor
from tools.can_topology.can_top_models import INTERFACE_CAN, INTERFACE_DIO, Node


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


class _EntryStub:
    """
    NAME
        _EntryStub - Minimal editable text entry stand-in for headless tests.
    """

    def __init__(self, value: str = "") -> None:
        self.value = value

    def get(self) -> str:
        return self.value

    def delete(self, _start: int, _end: object = None) -> None:
        self.value = ""

    def insert(self, _index: int, value: str) -> None:
        self.value = value


class TopologyEditorProfileLoadTests(unittest.TestCase):
    """
    NAME
        TopologyEditorProfileLoadTests - Validate profile-to-node loading helpers.
    """

    def test_empty_diagram_snapshot_is_not_layout_content(self) -> None:
        self.assertFalse(TopologyEditor._diagram_has_saved_content({}))

    def test_minimal_diagram_snapshot_is_layout_content(self) -> None:
        self.assertTrue(TopologyEditor._diagram_has_saved_content({"nodes": [{"key": 1}]}))

    def test_schema_v4_label_list_profile_loads_registry_devices(self) -> None:
        editor = TopologyEditor.__new__(TopologyEditor)
        editor._next_key = 1
        editor._device_registry = {}
        editor._device_registry_list = []
        editor._bus_offsets = [0.0]
        editor._box_h = 40.0
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

    def test_topology_interface_devices_load_as_profile_nodes(self) -> None:
        editor = TopologyEditor.__new__(TopologyEditor)
        editor._next_key = 1
        editor._device_registry = {}
        editor._device_registry_list = []
        editor._bus_offsets = [0.0]
        editor._box_h = 40.0
        payload = {
            "profiles": {
                "robot_2026_swerve": {
                    "devices": [
                        "cannect 2",
                        "inject",
                    ]
                }
            },
            "devices": [
                {
                    "label": "cannect 2",
                    "deviceInterface": "TOPOLOGY",
                    "type": "cannectDirect",
                    "vendor": "SWYFT",
                    "model": "Wiring",
                },
                {
                    "label": "inject",
                    "deviceInterface": "TOPOLOGY",
                    "type": "cannectInject",
                    "vendor": "SWYFT",
                    "model": "",
                },
            ],
        }

        editor._load_device_registry(payload)
        nodes = editor._nodes_from_profile(payload["profiles"]["robot_2026_swerve"])

        self.assertEqual([node.label for node in nodes], ["cannect 2", "inject"])
        self.assertTrue(all(node.interface == "TOPOLOGY" for node in nodes))
        self.assertEqual([node.category for node in nodes], ["cannect_direct", "cannect_inject"])

    def test_neighbor_status_marks_existing_metadata_stale(self) -> None:
        editor = TopologyEditor.__new__(TopologyEditor)
        editor._neighbor_links = [{"a": 1, "b": 2}]
        editor._neighbor_ports = []
        editor._neighbors_dirty = False
        editor._neighbor_status_var = _StringVarStub()

        editor._mark_neighbors_stale()

        self.assertTrue(editor._neighbors_dirty)
        self.assertEqual(editor._neighbor_status_var.value, "Neighbors: stale")

    def test_profile_pick_cancel_restores_previous_save_target(self) -> None:
        editor = TopologyEditor.__new__(TopologyEditor)
        editor._profile_name = "dsl_demo_050426"
        editor._profile_source_path = ""
        editor._profile_pick_var = _StringVarStub()
        editor._profile_pick_var.set("robot_2026_swerve")
        editor.entry_profile = _EntryStub("dsl_demo_050426")
        editor._default_profiles_path = lambda: Path("src/main/deploy/bringup_system.json")
        editor._load_profile_from_path = lambda *args, **kwargs: None

        editor._on_profile_pick(None)

        self.assertEqual("dsl_demo_050426", editor.entry_profile.get())
        self.assertEqual("dsl_demo_050426", editor._profile_pick_var.value)


if __name__ == "__main__":
    unittest.main()
