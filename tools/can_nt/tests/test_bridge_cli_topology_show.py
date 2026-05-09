from __future__ import annotations

"""
NAME
    test_bridge_cli_topology_show.py - Validate topology CLI commands.
"""

import io
import unittest
from contextlib import redirect_stdout

from tools.can_nt.bridge_cli import BridgeCli
from tools.can_nt.bridge_cli_parser import BridgeCliParser
from tools.can_nt.status import SS__CONFIG__VALID, SS__NORMAL
from tools.common.profile_constants import (
    EDGE_TYPE_CAN_TRUNK,
    KEY_DEVICES,
    KEY_DEVICE_REF,
    KEY_DEVICE_TYPE,
    KEY_EDGE_ID,
    KEY_EDGE_TYPE,
    KEY_ENABLED,
    KEY_FROM_NODE,
    KEY_FROM_PORT,
    KEY_ID,
    KEY_INTERFACE,
    KEY_INVERT,
    KEY_LABEL,
    KEY_LAYOUT,
    KEY_LINK_NEIGHBOR_PORT,
    KEY_LINK_PORT,
    KEY_MANUFACTURER,
    KEY_NODE_KEY,
    KEY_NODE_TYPE,
    KEY_PROFILE,
    KEY_PROFILES,
    KEY_SCHEMA_VERSION,
    KEY_TO_NODE,
    KEY_TO_PORT,
    KEY_TOPOLOGY,
    KEY_TOPOLOGY_EDGES,
    KEY_TOPOLOGY_NODES,
    KEY_TOPOLOGY_PROFILES,
    KEY_TOPOLOGY_SOURCE,
    KEY_TOPOLOGY_VERSION,
    KEY_DATA_VERSION,
    KEY_DATA_HASH,
    KEY_DEFAULT_PROFILE,
    PROFILE_SCHEMA_VERSION,
)
from tools.common.profile_io import compute_profiles_hash


PROFILE_NAME = "demo"
DEVICE_A = "A"
DEVICE_B = "B"
DEVICE_C = "C"
SHOW_TOPOLOGY_LOCAL = "show topology local"
SHOW_TOPOLOGY_NEIGHBORS_LOCAL = "show topology neighbors local"
SHOW_TOPOLOGY_NODE_B = "show topology node B"
SHOW_NEIGHBORS_B = "show neighbors B"
TOPOLOGY_SET = "topology neighbor-ports set A right B left"
TOPOLOGY_DELETE = "topology neighbor-ports delete A right"
TOPOLOGY_AUTO = "topology neighbor-auto node A"
VALIDATE_TOPOLOGY = "validate topology"
NODE_TYPE_DEVICE = "device"
INTERFACE_CAN = "CAN"
INTERFACE_DIO = "DIO"
KEY_DIO = "dio"
RIGHT = "right"
LEFT = "left"
BUILD_VERSION = "2026.05.09"
DEFAULT_PROFILE = PROFILE_NAME


def _build_root_payload() -> dict[str, object]:
    payload: dict[str, object] = {
        KEY_SCHEMA_VERSION: PROFILE_SCHEMA_VERSION,
        KEY_DATA_VERSION: BUILD_VERSION,
        KEY_DEFAULT_PROFILE: DEFAULT_PROFILE,
        KEY_DEVICES: [
            {
                KEY_LABEL: DEVICE_A,
                KEY_INTERFACE: INTERFACE_CAN,
                KEY_MANUFACTURER: 5,
                KEY_DEVICE_TYPE: 2,
                KEY_ID: 1,
            },
            {
                KEY_LABEL: DEVICE_B,
                KEY_INTERFACE: INTERFACE_CAN,
                KEY_MANUFACTURER: 5,
                KEY_DEVICE_TYPE: 2,
                KEY_ID: 2,
            },
            {
                KEY_LABEL: DEVICE_C,
                KEY_INTERFACE: INTERFACE_CAN,
                KEY_MANUFACTURER: 5,
                KEY_DEVICE_TYPE: 2,
                KEY_ID: 3,
            },
            {
                KEY_LABEL: "limit0",
                KEY_INTERFACE: INTERFACE_DIO,
                KEY_DIO: 0,
                KEY_INVERT: False,
                KEY_ENABLED: True,
            },
        ],
        KEY_PROFILES: {
            PROFILE_NAME: {
                KEY_DEVICES: [DEVICE_A, DEVICE_B, DEVICE_C, "limit0"],
            }
        },
        KEY_TOPOLOGY: {
            KEY_TOPOLOGY_VERSION: 1,
            KEY_TOPOLOGY_SOURCE: "local",
            KEY_TOPOLOGY_PROFILES: {
                PROFILE_NAME: {
                    KEY_TOPOLOGY_NODES: [
                        {KEY_NODE_KEY: 1, KEY_NODE_TYPE: NODE_TYPE_DEVICE, KEY_DEVICE_REF: DEVICE_A, KEY_LAYOUT: {"bus": 0, "row": 0, "x": 10.0}},
                        {KEY_NODE_KEY: 2, KEY_NODE_TYPE: NODE_TYPE_DEVICE, KEY_DEVICE_REF: DEVICE_B, KEY_LAYOUT: {"bus": 0, "row": 0, "x": 20.0}},
                        {KEY_NODE_KEY: 3, KEY_NODE_TYPE: NODE_TYPE_DEVICE, KEY_DEVICE_REF: DEVICE_C, KEY_LAYOUT: {"bus": 0, "row": 0, "x": 30.0}},
                    ],
                    KEY_TOPOLOGY_EDGES: [
                        {
                            KEY_EDGE_ID: "edge_1",
                            KEY_FROM_NODE: 1,
                            KEY_FROM_PORT: RIGHT,
                            KEY_TO_NODE: 2,
                            KEY_TO_PORT: LEFT,
                            KEY_EDGE_TYPE: EDGE_TYPE_CAN_TRUNK,
                        },
                        {
                            KEY_EDGE_ID: "edge_2",
                            KEY_FROM_NODE: 2,
                            KEY_FROM_PORT: RIGHT,
                            KEY_TO_NODE: 3,
                            KEY_TO_PORT: LEFT,
                            KEY_EDGE_TYPE: EDGE_TYPE_CAN_TRUNK,
                        },
                    ],
                }
            },
        },
    }
    payload[KEY_DATA_HASH] = compute_profiles_hash(payload)
    return payload


def _build_cli() -> BridgeCli:
    cli = BridgeCli.__new__(BridgeCli)
    cli._local_root_payload = _build_root_payload()
    cli._local_config = {KEY_PROFILE: PROFILE_NAME}
    cli._profiles_dirty = False
    cli._active_group_members = []
    cli._batch = False
    cli._session = type(
        "_Session",
        (),
        {"is_connected": lambda self: False},
    )()
    cli._active_profile_name = lambda: PROFILE_NAME
    return cli


class BridgeCliTopologyShowTests(unittest.TestCase):
    """
    NAME
        BridgeCliTopologyShowTests - Validate topology command parsing and execution.
    """

    def test_local_device_topology_includes_neighbors_for_active_profile(self) -> None:
        cli = _build_cli()

        topology = cli._local_device_topology(DEVICE_B)

        self.assertEqual(topology[KEY_NODE_KEY], 2)
        self.assertEqual(
            topology["neighborLinks"],
            [
                {"key": 1, "label": DEVICE_A, "bus": 0, "row": 0, "x": 10.0},
                {"key": 3, "label": DEVICE_C, "bus": 0, "row": 0, "x": 30.0},
            ],
        )
        self.assertEqual(
            topology["neighborPorts"],
            [
                {
                    "key": 1,
                    "label": DEVICE_A,
                    "bus": 0,
                    "row": 0,
                    "x": 10.0,
                    KEY_LINK_PORT: LEFT,
                    KEY_LINK_NEIGHBOR_PORT: RIGHT,
                    KEY_EDGE_TYPE: EDGE_TYPE_CAN_TRUNK,
                    KEY_EDGE_ID: "edge_1",
                },
                {
                    "key": 3,
                    "label": DEVICE_C,
                    "bus": 0,
                    "row": 0,
                    "x": 30.0,
                    KEY_LINK_PORT: RIGHT,
                    KEY_LINK_NEIGHBOR_PORT: LEFT,
                    KEY_EDGE_TYPE: EDGE_TYPE_CAN_TRUNK,
                    KEY_EDGE_ID: "edge_2",
                },
            ],
        )

    def test_parser_accepts_topology_show_commands(self) -> None:
        parser = BridgeCliParser()

        parser.parse(SHOW_TOPOLOGY_LOCAL, mode="exec")
        parser.parse(SHOW_TOPOLOGY_NEIGHBORS_LOCAL + " --json", mode="exec")
        parser.parse(SHOW_TOPOLOGY_NODE_B, mode="exec")
        parsed = parser.parse(SHOW_NEIGHBORS_B, mode="exec")

        self.assertEqual(parsed.ast.show_target, "neighbors")
        self.assertEqual(parsed.ast.show_name, DEVICE_B)

    def test_parser_accepts_topology_config_commands(self) -> None:
        parser = BridgeCliParser()

        parser.parse(TOPOLOGY_SET, mode="config")
        parser.parse(TOPOLOGY_DELETE, mode="config")
        parser.parse(TOPOLOGY_AUTO, mode="config")
        parser.parse(VALIDATE_TOPOLOGY, mode="config")

    def test_show_topology_local_prints_nodes_and_edges(self) -> None:
        cli = _build_cli()
        stream = io.StringIO()

        with redirect_stdout(stream):
            result = cli._handle_show(["topology", "local"])

        output = stream.getvalue()
        self.assertEqual(result.code, SS__NORMAL)
        self.assertIn("SOURCE: local", output)
        self.assertIn("Topology:", output)
        self.assertIn("Nodes:", output)
        self.assertIn("Edges:", output)
        self.assertIn(DEVICE_B, output)

    def test_show_neighbors_command_prints_one_node_neighbors(self) -> None:
        cli = _build_cli()
        stream = io.StringIO()

        with redirect_stdout(stream):
            result = cli._handle_show(["neighbors", DEVICE_B])

        output = stream.getvalue()
        self.assertEqual(result.code, SS__NORMAL)
        self.assertIn("Neighbors: B", output)
        self.assertIn("left -> A.right", output)
        self.assertIn("right -> C.left", output)

    def test_topology_neighbor_ports_set_updates_edge_graph(self) -> None:
        cli = _build_cli()
        stream = io.StringIO()

        with redirect_stdout(stream):
            result = cli._config_command(["topology", "neighbor-ports", "set", DEVICE_A, RIGHT, DEVICE_B, LEFT])

        edges = cli._active_topology_profile(create=False)[KEY_TOPOLOGY_EDGES]
        self.assertEqual(result.code, SS__NORMAL)
        self.assertTrue(cli._profiles_dirty)
        self.assertTrue(
            any(
                isinstance(edge, dict)
                and edge.get(KEY_FROM_NODE) == 1
                and edge.get(KEY_TO_NODE) == 2
                and edge.get(KEY_FROM_PORT) == RIGHT
                and edge.get(KEY_TO_PORT) == LEFT
                for edge in edges
            )
        )
        self.assertIn("INFO: topology neighbor port updated.", stream.getvalue())

    def test_validate_topology_command_succeeds_for_valid_payload(self) -> None:
        cli = _build_cli()
        stream = io.StringIO()

        with redirect_stdout(stream):
            result = cli._config_command(["validate", "topology"])

        self.assertEqual(result.code, SS__CONFIG__VALID)
        self.assertIn("OK: topology is valid.", stream.getvalue())


if __name__ == "__main__":
    unittest.main()
