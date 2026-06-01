from __future__ import annotations

"""
NAME
    test_bridge_cli_topology_show.py - Validate topology CLI commands.
"""

import io
import unittest
from contextlib import redirect_stdout

from tools.can_nt.bridge_cli_ast import BridgeCliAstExecutor
from tools.can_nt.bridge_cli import BridgeCli
from tools.can_nt.bridge_cli_parser import BridgeCliParser
from tools.can_nt.status import SS__CONFIG__VALID, SS__NORMAL
from tools.common.test_authoring import TestAuthoringModel
from tools.config.schema_store import ConfigSchemaStore
from tools.common.profile_constants import (
    EDGE_TYPE_CAN_TAP,
    KEY_BRIDGE_BY_PROFILE,
    KEY_BRIDGE_GROUPS,
    KEY_BUS,
    KEY_DEVICE_LINKS,
    EDGE_TYPE_CAN_TRUNK,
    KEY_DEVICES,
    KEY_DEVICE,
    KEY_DEVICE_REF,
    KEY_DEVICE_TYPE,
    KEY_EDGE_ID,
    KEY_EDGE_TYPE,
    KEY_ENABLED,
    KEY_ETHERNET_LINKS,
    KEY_FROM_NODE,
    KEY_FROM_PORT,
    KEY_ID,
    KEY_INPUT_ALIASES,
    KEY_INTERFACE,
    KEY_INVERT,
    KEY_LABEL,
    KEY_LAYOUT,
    KEY_LINK_A,
    KEY_LINK_B,
    KEY_LINK_NODE,
    KEY_LINK_NEIGHBOR_PORT,
    KEY_LINK_PORT,
    KEY_MANUFACTURER,
    KEY_MEMBERS,
    KEY_NAME,
    KEY_NEIGHBOR_PORTS,
    KEY_NODE_CLASS,
    KEY_NODE_KEY,
    KEY_NODE_TYPE,
    KEY_OBJECT_TYPE,
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
    KEY_TOPOLOGY_VIEW,
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
SHOW_TOPOLOGY_LOCAL_GROUPED = "show topology --grouped local"
SHOW_TOPOLOGY_NEIGHBORS_LOCAL = "show topology neighbors local"
SHOW_TOPOLOGY_NODE_B = "show topology node B"
SHOW_NEIGHBORS_B = "show neighbors B"
TOPOLOGY_SET = "topology neighbor-ports set A right B left"
TOPOLOGY_DELETE = "topology neighbor-ports delete A right"
TOPOLOGY_AUTO = "topology neighbor-auto node A"
VALIDATE_TOPOLOGY = "validate topology"
VALIDATE_TOPOLOGY_VERBOSE = "validate topology --verbose"
VALIDATE_PROFILES_VERBOSE = "validate profiles --verbose"
VALIDATE_BINDINGS_VERBOSE = "validate bindings --verbose"
VALIDATE_ALL_VERBOSE = "validate all --verbose"
NODE_TYPE_DEVICE = "device"
NODE_TYPE_ANALYZER = "analyzer"
NODE_CLASS_DEVICE = "device"
NODE_CLASS_INFRASTRUCTURE = "infrastructure"
INTERFACE_CAN = "CAN"
INTERFACE_DIO = "DIO"
RIGHT = "right"
LEFT = "left"
BUILD_VERSION = "2026.05.09"
DEFAULT_PROFILE = PROFILE_NAME
VIEW_KEY_BUS_OFFSETS = "busOffsets"
VIEW_KEY_BUS_COUNT = "busCount"
VIEW_KEY_BUS_CONNECTORS = "busConnectors"
VIEW_KEY_BUS_CONNECTOR_SIDES = "busConnectorSides"


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
                KEY_ID: 0,
                KEY_INVERT: False,
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
    cli._local_config = {
        KEY_PROFILE: PROFILE_NAME,
        KEY_BRIDGE_BY_PROFILE: {
            PROFILE_NAME: {
                KEY_BRIDGE_GROUPS: [
                    {
                        KEY_NAME: "Front Left",
                        KEY_MEMBERS: [
                            {KEY_LABEL: DEVICE_A, KEY_ENABLED: True},
                            {KEY_LABEL: DEVICE_B, KEY_ENABLED: True},
                        ],
                    },
                    {
                        KEY_NAME: "driveTrain",
                        KEY_MEMBERS: [
                            {KEY_LABEL: DEVICE_B, KEY_ENABLED: True},
                            {KEY_LABEL: DEVICE_C, KEY_ENABLED: True},
                        ],
                    },
                ],
            }
        },
    }
    cli._profiles_dirty = False
    cli._groups_dirty = False
    cli._tests_dirty = False
    cli._bindings_dirty = False
    cli._can_mappings_dirty = False
    cli._groups_profile = PROFILE_NAME
    cli._active_group_members = []
    cli._bindings_payload = {
        KEY_SCHEMA_VERSION: PROFILE_SCHEMA_VERSION,
        "controllers": [],
        "bindings": [],
        KEY_INPUT_ALIASES: {},
    }
    cli._can_mappings = {
        "manufacturers": {},
        "device_types": {},
    }
    cli._tests_model = TestAuthoringModel()
    cli._tests_device_catalog = {}
    cli._tests_profile = PROFILE_NAME
    cli._store = ConfigSchemaStore()
    cli._store.set_profiles_payload(cli._local_root_payload)
    cli._store.set_bindings_payload(cli._bindings_payload)
    cli._store.set_mappings_payload(cli._can_mappings)
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
        self.assertEqual(topology[KEY_LABEL], DEVICE_B)
        self.assertEqual(topology[KEY_OBJECT_TYPE], NODE_TYPE_DEVICE)
        self.assertEqual(topology[KEY_NODE_CLASS], NODE_CLASS_DEVICE)
        self.assertEqual(
            topology["neighborLinks"],
            [
                {
                    "key": 1,
                    "label": DEVICE_A,
                    "bus": 0,
                    "row": 0,
                    "x": 10.0,
                    KEY_OBJECT_TYPE: NODE_TYPE_DEVICE,
                    KEY_NODE_TYPE: NODE_TYPE_DEVICE,
                    KEY_NODE_CLASS: NODE_CLASS_DEVICE,
                },
                {
                    "key": 3,
                    "label": DEVICE_C,
                    "bus": 0,
                    "row": 0,
                    "x": 30.0,
                    KEY_OBJECT_TYPE: NODE_TYPE_DEVICE,
                    KEY_NODE_TYPE: NODE_TYPE_DEVICE,
                    KEY_NODE_CLASS: NODE_CLASS_DEVICE,
                },
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
                    KEY_OBJECT_TYPE: NODE_TYPE_DEVICE,
                    KEY_NODE_TYPE: NODE_TYPE_DEVICE,
                    KEY_NODE_CLASS: NODE_CLASS_DEVICE,
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
                    KEY_OBJECT_TYPE: NODE_TYPE_DEVICE,
                    KEY_NODE_TYPE: NODE_TYPE_DEVICE,
                    KEY_NODE_CLASS: NODE_CLASS_DEVICE,
                    KEY_LINK_PORT: RIGHT,
                    KEY_LINK_NEIGHBOR_PORT: LEFT,
                    KEY_EDGE_TYPE: EDGE_TYPE_CAN_TRUNK,
                    KEY_EDGE_ID: "edge_2",
                },
            ],
        )

    def test_local_device_topology_treats_analyzer_as_first_class_graph_node(self) -> None:
        cli = _build_cli()
        topology_profile = cli._local_root_payload[KEY_TOPOLOGY][KEY_TOPOLOGY_PROFILES][PROFILE_NAME]
        topology_profile[KEY_TOPOLOGY_NODES] = [
            {KEY_NODE_KEY: 1, KEY_NODE_TYPE: NODE_TYPE_DEVICE, KEY_DEVICE_REF: DEVICE_A, KEY_LAYOUT: {"bus": 0, "row": 0, "x": 10.0}},
            {KEY_NODE_KEY: 7, KEY_NODE_TYPE: NODE_TYPE_ANALYZER, KEY_LABEL: "can analyzer 1", KEY_LAYOUT: {"bus": 0, "row": 0, "x": 20.0}},
            {KEY_NODE_KEY: 2, KEY_NODE_TYPE: NODE_TYPE_DEVICE, KEY_DEVICE_REF: DEVICE_B, KEY_LAYOUT: {"bus": 0, "row": 0, "x": 30.0}},
        ]
        topology_profile[KEY_TOPOLOGY_EDGES] = [
            {
                KEY_EDGE_ID: "edge_1",
                KEY_FROM_NODE: 1,
                KEY_FROM_PORT: RIGHT,
                KEY_TO_NODE: 7,
                KEY_TO_PORT: LEFT,
                KEY_EDGE_TYPE: EDGE_TYPE_CAN_TAP,
            },
            {
                KEY_EDGE_ID: "edge_2",
                KEY_FROM_NODE: 7,
                KEY_FROM_PORT: RIGHT,
                KEY_TO_NODE: 2,
                KEY_TO_PORT: LEFT,
                KEY_EDGE_TYPE: EDGE_TYPE_CAN_TAP,
            },
        ]

        topology = cli._local_device_topology("can analyzer 1")

        self.assertEqual(topology[KEY_LABEL], "can analyzer 1")
        self.assertEqual(topology[KEY_OBJECT_TYPE], NODE_TYPE_ANALYZER)
        self.assertEqual(topology[KEY_NODE_CLASS], NODE_CLASS_INFRASTRUCTURE)
        self.assertEqual(
            topology[KEY_NEIGHBOR_PORTS],
            [
                {
                    KEY_NODE_KEY: 1,
                    KEY_LABEL: DEVICE_A,
                    KEY_BUS: 0,
                    "row": 0,
                    "x": 10.0,
                    KEY_OBJECT_TYPE: NODE_TYPE_DEVICE,
                    KEY_NODE_TYPE: NODE_TYPE_DEVICE,
                    KEY_NODE_CLASS: NODE_CLASS_DEVICE,
                    KEY_LINK_PORT: LEFT,
                    KEY_LINK_NEIGHBOR_PORT: RIGHT,
                    KEY_EDGE_TYPE: EDGE_TYPE_CAN_TAP,
                    KEY_EDGE_ID: "edge_1",
                },
                {
                    KEY_NODE_KEY: 2,
                    KEY_LABEL: DEVICE_B,
                    KEY_BUS: 0,
                    "row": 0,
                    "x": 30.0,
                    KEY_OBJECT_TYPE: NODE_TYPE_DEVICE,
                    KEY_NODE_TYPE: NODE_TYPE_DEVICE,
                    KEY_NODE_CLASS: NODE_CLASS_DEVICE,
                    KEY_LINK_PORT: RIGHT,
                    KEY_LINK_NEIGHBOR_PORT: LEFT,
                    KEY_EDGE_TYPE: EDGE_TYPE_CAN_TAP,
                    KEY_EDGE_ID: "edge_2",
                },
            ],
        )

    def test_show_topology_local_json_resolves_node_class_for_infrastructure_nodes(self) -> None:
        cli = _build_cli()
        topology_profile = cli._local_root_payload[KEY_TOPOLOGY][KEY_TOPOLOGY_PROFILES][PROFILE_NAME]
        topology_profile[KEY_TOPOLOGY_NODES].append(
            {KEY_NODE_KEY: 7, KEY_NODE_TYPE: NODE_TYPE_ANALYZER, KEY_LABEL: "can analyzer 1", KEY_LAYOUT: {"bus": 0, "row": 0, "x": 25.0}}
        )
        stream = io.StringIO()

        with redirect_stdout(stream):
            result = cli._handle_show(["topology", "local", "--json", "--pretty"])

        output = stream.getvalue()
        self.assertEqual(result.code, SS__NORMAL)
        self.assertIn(f'"{KEY_NODE_CLASS}": "{NODE_CLASS_DEVICE}"', output)
        self.assertIn(f'"{KEY_NODE_CLASS}": "{NODE_CLASS_INFRASTRUCTURE}"', output)
        self.assertIn(f'"{KEY_OBJECT_TYPE}": "{NODE_TYPE_ANALYZER}"', output)

    def test_parser_accepts_topology_show_commands(self) -> None:
        parser = BridgeCliParser()

        parser.parse(SHOW_TOPOLOGY_LOCAL, mode="exec")
        parser.parse(SHOW_TOPOLOGY_LOCAL_GROUPED, mode="exec")
        parser.parse(SHOW_TOPOLOGY_NEIGHBORS_LOCAL + " --json", mode="exec")
        parser.parse(SHOW_TOPOLOGY_NODE_B, mode="exec")
        parsed = parser.parse(SHOW_NEIGHBORS_B, mode="exec")
        self.assertEqual(parsed.ast.show_target, "neighbors")
        self.assertEqual(parsed.ast.show_name, DEVICE_B)

    def test_show_topology_respects_explicit_bus_connector_side(self) -> None:
        cli = _build_cli()
        topology_profile = cli._local_root_payload[KEY_TOPOLOGY][KEY_TOPOLOGY_PROFILES][PROFILE_NAME]
        topology_profile[KEY_TOPOLOGY_NODES] = [
            {KEY_NODE_KEY: 1, KEY_NODE_TYPE: NODE_TYPE_DEVICE, KEY_DEVICE_REF: DEVICE_A, KEY_LAYOUT: {"bus": 0, "row": 0, "x": 10.0}},
            {KEY_NODE_KEY: 2, KEY_NODE_TYPE: NODE_TYPE_DEVICE, KEY_DEVICE_REF: DEVICE_B, KEY_LAYOUT: {"bus": 0, "row": 0, "x": 20.0}},
            {KEY_NODE_KEY: 3, KEY_NODE_TYPE: NODE_TYPE_DEVICE, KEY_DEVICE_REF: DEVICE_C, KEY_LAYOUT: {"bus": 1, "row": 0, "x": 10.0}},
        ]
        topology_profile[KEY_TOPOLOGY_VIEW] = {
            VIEW_KEY_BUS_OFFSETS: [0.0, 160.0],
            VIEW_KEY_BUS_COUNT: 2,
            VIEW_KEY_BUS_CONNECTORS: [True],
            VIEW_KEY_BUS_CONNECTOR_SIDES: [RIGHT],
        }
        node_map = {
            int(entry[KEY_NODE_KEY]): entry
            for entry in topology_profile[KEY_TOPOLOGY_NODES]
            if isinstance(entry, dict) and isinstance(entry.get(KEY_NODE_KEY), int)
        }

        right_side_edges = cli._topology_can_view_path_edges(
            topology_profile,
            node_map,
            PROFILE_NAME,
        )

        topology_profile[KEY_TOPOLOGY_VIEW][VIEW_KEY_BUS_CONNECTOR_SIDES] = [LEFT]
        left_side_edges = cli._topology_can_view_path_edges(
            topology_profile,
            node_map,
            PROFILE_NAME,
        )

        self.assertEqual(right_side_edges, [(DEVICE_A, DEVICE_B), (DEVICE_B, DEVICE_C)])
        self.assertEqual(left_side_edges, [(DEVICE_B, DEVICE_A), (DEVICE_A, DEVICE_C)])

    def test_parser_accepts_topology_config_commands(self) -> None:
        parser = BridgeCliParser()

        parser.parse(TOPOLOGY_SET, mode="config")
        parser.parse(TOPOLOGY_DELETE, mode="config")
        parser.parse(TOPOLOGY_AUTO, mode="config")
        parser.parse(VALIDATE_TOPOLOGY, mode="config")

    def test_show_topology_local_prints_collapsed_can_bus(self) -> None:
        cli = _build_cli()
        stream = io.StringIO()

        with redirect_stdout(stream):
            result = cli._handle_show(["topology", "local"])

        output = stream.getvalue()
        self.assertEqual(result.code, SS__NORMAL)
        self.assertIn("SOURCE: local", output)
        self.assertIn("CAN Bus", output)
        self.assertIn("A -> B", output)
        self.assertIn("B -> C", output)
        self.assertNotIn("Nodes:", output)
        self.assertNotIn("Edges:", output)

    def test_show_topology_grouped_duplicates_multi_group_edges(self) -> None:
        cli = _build_cli()
        stream = io.StringIO()

        with redirect_stdout(stream):
            result = cli._handle_show(["topology", "--grouped", "local"])

        output = stream.getvalue()
        self.assertEqual(result.code, SS__NORMAL)
        self.assertIn("CAN Bus", output)
        self.assertIn("  Front Left:", output)
        self.assertIn("  driveTrain:", output)
        self.assertIn("    A -> B", output)
        self.assertIn("    B -> C [listed multiple times: Front Left, driveTrain]", output)

    def test_show_topology_grouped_uses_swyft_names_when_device_links_exist(self) -> None:
        cli = BridgeCli.__new__(BridgeCli)
        payload = _build_root_payload()
        payload[KEY_DEVICES] = [
            {KEY_LABEL: "frontLeft Drive Motor", KEY_INTERFACE: INTERFACE_CAN, KEY_MANUFACTURER: 5, KEY_DEVICE_TYPE: 2, KEY_ID: 1},
            {KEY_LABEL: "frontLeft Angle Motor", KEY_INTERFACE: INTERFACE_CAN, KEY_MANUFACTURER: 5, KEY_DEVICE_TYPE: 2, KEY_ID: 2},
            {KEY_LABEL: "frontLeft Encoder", KEY_INTERFACE: INTERFACE_CAN, KEY_MANUFACTURER: 5, KEY_DEVICE_TYPE: 2, KEY_ID: 3},
        ]
        payload[KEY_PROFILES][PROFILE_NAME][KEY_DEVICES] = [
            "frontLeft Drive Motor",
            "frontLeft Angle Motor",
            "frontLeft Encoder",
        ]
        payload[KEY_TOPOLOGY][KEY_TOPOLOGY_PROFILES][PROFILE_NAME][KEY_TOPOLOGY_NODES] = [
            {KEY_NODE_KEY: 1, KEY_NODE_TYPE: NODE_TYPE_DEVICE, KEY_DEVICE_REF: "frontLeft Drive Motor", KEY_LAYOUT: {"bus": 0, "row": 0, "x": 10.0}},
            {KEY_NODE_KEY: 2, KEY_NODE_TYPE: NODE_TYPE_DEVICE, KEY_DEVICE_REF: "frontLeft Angle Motor", KEY_LAYOUT: {"bus": 0, "row": 0, "x": 20.0}},
            {KEY_NODE_KEY: 3, KEY_NODE_TYPE: NODE_TYPE_DEVICE, KEY_DEVICE_REF: "frontLeft Encoder", KEY_LAYOUT: {"bus": 0, "row": 0, "x": 30.0}},
            {KEY_NODE_KEY: 10, KEY_NODE_TYPE: "junction", KEY_LABEL: "cannect 3", KEY_LAYOUT: {"bus": 0, "row": 0, "x": 15.0}},
            {KEY_NODE_KEY: 11, KEY_NODE_TYPE: "junction", KEY_LABEL: "inject", KEY_LAYOUT: {"bus": 0, "row": 0, "x": 0.0}},
        ]
        payload[KEY_TOPOLOGY][KEY_TOPOLOGY_PROFILES][PROFILE_NAME][KEY_TOPOLOGY_VIEW] = {
            KEY_ETHERNET_LINKS: [{KEY_LINK_A: 11, KEY_LINK_B: 10}],
            KEY_DEVICE_LINKS: [
                {KEY_LINK_NODE: 10, KEY_DEVICE: 1, KEY_LINK_PORT: 1},
                {KEY_LINK_NODE: 10, KEY_DEVICE: 2, KEY_LINK_PORT: 2},
                {KEY_LINK_NODE: 10, KEY_DEVICE: 3, KEY_LINK_PORT: 3},
            ],
        }
        payload[KEY_DATA_HASH] = compute_profiles_hash(payload)
        cli._local_root_payload = payload
        cli._local_config = {
            KEY_PROFILE: PROFILE_NAME,
            KEY_BRIDGE_BY_PROFILE: {
                PROFILE_NAME: {
                    KEY_BRIDGE_GROUPS: [
                        {
                            KEY_NAME: "frontLeft",
                            KEY_MEMBERS: [
                                {KEY_LABEL: "frontLeft Drive Motor", KEY_ENABLED: True},
                                {KEY_LABEL: "frontLeft Angle Motor", KEY_ENABLED: True},
                                {KEY_LABEL: "frontLeft Encoder", KEY_ENABLED: True},
                            ],
                        }
                    ],
                }
            },
        }
        cli._profiles_dirty = False
        cli._groups_profile = PROFILE_NAME
        cli._active_group_members = []
        cli._batch = False
        cli._session = type("_Session", (), {"is_connected": lambda self: False})()
        cli._active_profile_name = lambda: PROFILE_NAME
        stream = io.StringIO()

        with redirect_stdout(stream):
            result = cli._handle_show(["topology", "--grouped", "local"])

        output = stream.getvalue()
        self.assertEqual(result.code, SS__NORMAL)
        self.assertIn("SWYFT Backbone:", output)
        self.assertIn("inject -> cannect 3", output)
        self.assertIn("frontLeft:", output)
        self.assertIn("cannect 3 -> frontLeft Drive Motor", output)
        self.assertIn("cannect 3 -> frontLeft Angle Motor", output)
        self.assertIn("cannect 3 -> frontLeft Encoder", output)
        self.assertNotIn("frontLeft Drive Motor -> frontLeft Angle Motor", output)

    def test_show_topology_local_uses_wrapped_bus_view_order_for_multi_segment_bus(self) -> None:
        cli = BridgeCli.__new__(BridgeCli)
        payload = _build_root_payload()
        payload[KEY_DEVICES] = [
            {KEY_LABEL: "roborio", KEY_INTERFACE: INTERFACE_CAN, KEY_MANUFACTURER: 1, KEY_DEVICE_TYPE: 1, KEY_ID: 0},
            {KEY_LABEL: "frontLeft Drive Motor", KEY_INTERFACE: INTERFACE_CAN, KEY_MANUFACTURER: 5, KEY_DEVICE_TYPE: 2, KEY_ID: 2},
            {KEY_LABEL: "frontLeft Angle Motor", KEY_INTERFACE: INTERFACE_CAN, KEY_MANUFACTURER: 5, KEY_DEVICE_TYPE: 2, KEY_ID: 1},
            {KEY_LABEL: "frontLeft Encoder", KEY_INTERFACE: INTERFACE_CAN, KEY_MANUFACTURER: 4, KEY_DEVICE_TYPE: 7, KEY_ID: 3},
            {KEY_LABEL: "frontRight Drive Motor", KEY_INTERFACE: INTERFACE_CAN, KEY_MANUFACTURER: 5, KEY_DEVICE_TYPE: 2, KEY_ID: 11},
            {KEY_LABEL: "frontRight Angle Motor", KEY_INTERFACE: INTERFACE_CAN, KEY_MANUFACTURER: 5, KEY_DEVICE_TYPE: 2, KEY_ID: 10},
            {KEY_LABEL: "frontRight Encoder", KEY_INTERFACE: INTERFACE_CAN, KEY_MANUFACTURER: 4, KEY_DEVICE_TYPE: 7, KEY_ID: 12},
            {KEY_LABEL: "backLeft Drive Motor", KEY_INTERFACE: INTERFACE_CAN, KEY_MANUFACTURER: 5, KEY_DEVICE_TYPE: 2, KEY_ID: 5},
            {KEY_LABEL: "backLeft Angle Motor", KEY_INTERFACE: INTERFACE_CAN, KEY_MANUFACTURER: 5, KEY_DEVICE_TYPE: 2, KEY_ID: 4},
            {KEY_LABEL: "backLeft Encoder", KEY_INTERFACE: INTERFACE_CAN, KEY_MANUFACTURER: 4, KEY_DEVICE_TYPE: 7, KEY_ID: 6},
            {KEY_LABEL: "backRight Drive Motor", KEY_INTERFACE: INTERFACE_CAN, KEY_MANUFACTURER: 5, KEY_DEVICE_TYPE: 2, KEY_ID: 8},
            {KEY_LABEL: "backRight Angle Motor", KEY_INTERFACE: INTERFACE_CAN, KEY_MANUFACTURER: 5, KEY_DEVICE_TYPE: 2, KEY_ID: 7},
            {KEY_LABEL: "backRight Encoder", KEY_INTERFACE: INTERFACE_CAN, KEY_MANUFACTURER: 4, KEY_DEVICE_TYPE: 7, KEY_ID: 9},
            {KEY_LABEL: "pdh", KEY_INTERFACE: INTERFACE_CAN, KEY_MANUFACTURER: 5, KEY_DEVICE_TYPE: 8, KEY_ID: 1},
        ]
        payload[KEY_PROFILES][PROFILE_NAME][KEY_DEVICES] = [
            "roborio",
            "frontLeft Drive Motor",
            "frontLeft Angle Motor",
            "frontLeft Encoder",
            "frontRight Drive Motor",
            "frontRight Angle Motor",
            "frontRight Encoder",
            "backLeft Drive Motor",
            "backLeft Angle Motor",
            "backLeft Encoder",
            "backRight Drive Motor",
            "backRight Angle Motor",
            "backRight Encoder",
            "pdh",
        ]
        payload[KEY_TOPOLOGY][KEY_TOPOLOGY_PROFILES][PROFILE_NAME][KEY_TOPOLOGY_NODES] = [
            {KEY_NODE_KEY: 34, KEY_NODE_TYPE: NODE_TYPE_DEVICE, KEY_DEVICE_REF: "roborio", KEY_LAYOUT: {"bus": 0, "row": 0, "x": 10.0}},
            {KEY_NODE_KEY: 3, KEY_NODE_TYPE: NODE_TYPE_DEVICE, KEY_DEVICE_REF: "frontLeft Drive Motor", KEY_LAYOUT: {"bus": 0, "row": 1, "x": 20.0}},
            {KEY_NODE_KEY: 4, KEY_NODE_TYPE: NODE_TYPE_DEVICE, KEY_DEVICE_REF: "frontLeft Angle Motor", KEY_LAYOUT: {"bus": 0, "row": 1, "x": 30.0}},
            {KEY_NODE_KEY: 5, KEY_NODE_TYPE: NODE_TYPE_DEVICE, KEY_DEVICE_REF: "frontLeft Encoder", KEY_LAYOUT: {"bus": 0, "row": 1, "x": 40.0}},
            {KEY_NODE_KEY: 6, KEY_NODE_TYPE: NODE_TYPE_DEVICE, KEY_DEVICE_REF: "frontRight Drive Motor", KEY_LAYOUT: {"bus": 0, "row": 1, "x": 70.0}},
            {KEY_NODE_KEY: 7, KEY_NODE_TYPE: NODE_TYPE_DEVICE, KEY_DEVICE_REF: "frontRight Angle Motor", KEY_LAYOUT: {"bus": 0, "row": 1, "x": 80.0}},
            {KEY_NODE_KEY: 8, KEY_NODE_TYPE: NODE_TYPE_DEVICE, KEY_DEVICE_REF: "frontRight Encoder", KEY_LAYOUT: {"bus": 0, "row": 1, "x": 90.0}},
            {KEY_NODE_KEY: 9, KEY_NODE_TYPE: NODE_TYPE_DEVICE, KEY_DEVICE_REF: "backLeft Drive Motor", KEY_LAYOUT: {"bus": 1, "row": 1, "x": 20.0}},
            {KEY_NODE_KEY: 10, KEY_NODE_TYPE: NODE_TYPE_DEVICE, KEY_DEVICE_REF: "backLeft Angle Motor", KEY_LAYOUT: {"bus": 1, "row": 1, "x": 30.0}},
            {KEY_NODE_KEY: 11, KEY_NODE_TYPE: NODE_TYPE_DEVICE, KEY_DEVICE_REF: "backLeft Encoder", KEY_LAYOUT: {"bus": 1, "row": 1, "x": 40.0}},
            {KEY_NODE_KEY: 12, KEY_NODE_TYPE: NODE_TYPE_DEVICE, KEY_DEVICE_REF: "backRight Drive Motor", KEY_LAYOUT: {"bus": 1, "row": 1, "x": 70.0}},
            {KEY_NODE_KEY: 13, KEY_NODE_TYPE: NODE_TYPE_DEVICE, KEY_DEVICE_REF: "backRight Angle Motor", KEY_LAYOUT: {"bus": 1, "row": 1, "x": 80.0}},
            {KEY_NODE_KEY: 14, KEY_NODE_TYPE: NODE_TYPE_DEVICE, KEY_DEVICE_REF: "backRight Encoder", KEY_LAYOUT: {"bus": 1, "row": 1, "x": 90.0}},
            {KEY_NODE_KEY: 18, KEY_NODE_TYPE: NODE_TYPE_DEVICE, KEY_DEVICE_REF: "pdh", KEY_LAYOUT: {"bus": 1, "row": 1, "x": 10.0}},
        ]
        payload[KEY_TOPOLOGY][KEY_TOPOLOGY_PROFILES][PROFILE_NAME][KEY_TOPOLOGY_EDGES] = [
            {KEY_EDGE_ID: "edge_1", KEY_FROM_NODE: 34, KEY_FROM_PORT: RIGHT, KEY_TO_NODE: 3, KEY_TO_PORT: LEFT, KEY_EDGE_TYPE: EDGE_TYPE_CAN_TRUNK},
            {KEY_EDGE_ID: "edge_2", KEY_FROM_NODE: 3, KEY_FROM_PORT: RIGHT, KEY_TO_NODE: 4, KEY_TO_PORT: LEFT, KEY_EDGE_TYPE: EDGE_TYPE_CAN_TRUNK},
            {KEY_EDGE_ID: "edge_3", KEY_FROM_NODE: 4, KEY_FROM_PORT: RIGHT, KEY_TO_NODE: 5, KEY_TO_PORT: LEFT, KEY_EDGE_TYPE: EDGE_TYPE_CAN_TRUNK},
            {KEY_EDGE_ID: "edge_4", KEY_FROM_NODE: 5, KEY_FROM_PORT: RIGHT, KEY_TO_NODE: 6, KEY_TO_PORT: LEFT, KEY_EDGE_TYPE: EDGE_TYPE_CAN_TRUNK},
            {KEY_EDGE_ID: "edge_5", KEY_FROM_NODE: 6, KEY_FROM_PORT: RIGHT, KEY_TO_NODE: 7, KEY_TO_PORT: LEFT, KEY_EDGE_TYPE: EDGE_TYPE_CAN_TRUNK},
            {KEY_EDGE_ID: "edge_6", KEY_FROM_NODE: 7, KEY_FROM_PORT: RIGHT, KEY_TO_NODE: 8, KEY_TO_PORT: LEFT, KEY_EDGE_TYPE: EDGE_TYPE_CAN_TRUNK},
            {KEY_EDGE_ID: "edge_7", KEY_FROM_NODE: 18, KEY_FROM_PORT: RIGHT, KEY_TO_NODE: 9, KEY_TO_PORT: LEFT, KEY_EDGE_TYPE: EDGE_TYPE_CAN_TRUNK},
        ]
        payload[KEY_TOPOLOGY][KEY_TOPOLOGY_PROFILES][PROFILE_NAME][KEY_TOPOLOGY_VIEW] = {
            VIEW_KEY_BUS_OFFSETS: [0.0, 160.0],
            VIEW_KEY_BUS_COUNT: 2,
            VIEW_KEY_BUS_CONNECTORS: [True],
        }
        payload[KEY_DATA_HASH] = compute_profiles_hash(payload)
        cli._local_root_payload = payload
        cli._local_config = {
            KEY_PROFILE: PROFILE_NAME,
            KEY_BRIDGE_BY_PROFILE: {
                PROFILE_NAME: {
                    KEY_BRIDGE_GROUPS: [
                        {KEY_NAME: "frontLeft", KEY_MEMBERS: [{KEY_LABEL: "frontLeft Drive Motor", KEY_ENABLED: True}, {KEY_LABEL: "frontLeft Angle Motor", KEY_ENABLED: True}, {KEY_LABEL: "frontLeft Encoder", KEY_ENABLED: True}]},
                        {KEY_NAME: "frontRight", KEY_MEMBERS: [{KEY_LABEL: "frontRight Drive Motor", KEY_ENABLED: True}, {KEY_LABEL: "frontRight Angle Motor", KEY_ENABLED: True}, {KEY_LABEL: "frontRight Encoder", KEY_ENABLED: True}]},
                        {KEY_NAME: "backRight", KEY_MEMBERS: [{KEY_LABEL: "backRight Drive Motor", KEY_ENABLED: True}, {KEY_LABEL: "backRight Angle Motor", KEY_ENABLED: True}, {KEY_LABEL: "backRight Encoder", KEY_ENABLED: True}]},
                        {KEY_NAME: "backLeft", KEY_MEMBERS: [{KEY_LABEL: "backLeft Drive Motor", KEY_ENABLED: True}, {KEY_LABEL: "backLeft Angle Motor", KEY_ENABLED: True}, {KEY_LABEL: "backLeft Encoder", KEY_ENABLED: True}]},
                    ]
                }
            },
        }
        cli._profiles_dirty = False
        cli._groups_profile = PROFILE_NAME
        cli._active_group_members = []
        cli._batch = False
        cli._session = type("_Session", (), {"is_connected": lambda self: False})()
        cli._active_profile_name = lambda: PROFILE_NAME
        stream = io.StringIO()

        with redirect_stdout(stream):
            result = cli._handle_show(["topology", "local"])

        output = stream.getvalue()
        self.assertEqual(result.code, SS__NORMAL)
        self.assertIn("roborio -> frontLeft Drive Motor", output)
        self.assertIn("frontRight Encoder -> backRight Drive Motor", output)
        self.assertIn("backRight Encoder -> backLeft Drive Motor", output)
        self.assertIn("backLeft Encoder -> pdh", output)
        self.assertNotIn("INFO: showing raw topology", output)

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

    def test_validate_topology_ast_command_succeeds_for_valid_payload(self) -> None:
        cli = _build_cli()
        ast = BridgeCliParser().parse(VALIDATE_TOPOLOGY, mode="config").ast
        stream = io.StringIO()

        with redirect_stdout(stream):
            result = BridgeCliAstExecutor(cli).execute(ast)

        self.assertEqual(result.code, SS__CONFIG__VALID)
        self.assertIn("OK: topology is valid.", stream.getvalue())

    def test_validate_topology_verbose_reports_checks(self) -> None:
        cli = _build_cli()
        ast = BridgeCliParser().parse(VALIDATE_TOPOLOGY_VERBOSE, mode="config").ast
        stream = io.StringIO()

        with redirect_stdout(stream):
            result = BridgeCliAstExecutor(cli).execute(ast)

        output = stream.getvalue()
        self.assertEqual(result.code, SS__CONFIG__VALID)
        self.assertIn("PASS: Root 'schema_version' matches expected version.", output)
        self.assertIn("PASS: Root 'data_hash' matches computed value.", output)
        self.assertIn("OK: topology is valid.", output)

    def test_validate_profiles_verbose_ast_command_succeeds(self) -> None:
        cli = _build_cli()
        ast = BridgeCliParser().parse(VALIDATE_PROFILES_VERBOSE, mode="config").ast
        stream = io.StringIO()

        with redirect_stdout(stream):
            result = BridgeCliAstExecutor(cli).execute(ast)

        output = stream.getvalue()
        self.assertEqual(result.code, SS__CONFIG__VALID)
        self.assertIn("PASS: profiles payload is valid.", output)
        self.assertIn("OK: Config is valid.", output)

    def test_validate_bindings_verbose_ast_command_succeeds(self) -> None:
        cli = _build_cli()
        ast = BridgeCliParser().parse(VALIDATE_BINDINGS_VERBOSE, mode="config").ast
        stream = io.StringIO()

        with redirect_stdout(stream):
            result = BridgeCliAstExecutor(cli).execute(ast)

        output = stream.getvalue()
        self.assertEqual(result.code, SS__CONFIG__VALID)
        self.assertIn("PASS: bindings payload is valid.", output)
        self.assertIn("OK: Config is valid.", output)

    def test_validate_all_verbose_ast_command_succeeds(self) -> None:
        cli = _build_cli()
        ast = BridgeCliParser().parse(VALIDATE_ALL_VERBOSE, mode="config").ast
        stream = io.StringIO()

        with redirect_stdout(stream):
            result = BridgeCliAstExecutor(cli).execute(ast)

        output = stream.getvalue()
        self.assertEqual(result.code, SS__CONFIG__VALID)
        self.assertIn("Validate all:", output)
        self.assertIn("PASS: profiles payload is valid.", output)
        self.assertIn("PASS: bindings payload is valid.", output)

    def test_topology_neighbor_auto_reuses_existing_can_edge_ids(self) -> None:
        cli = _build_cli()
        stream = io.StringIO()

        with redirect_stdout(stream):
            result = cli._config_command(["topology", "neighbor-auto", "all"])

        edges = cli._active_topology_profile(create=False)[KEY_TOPOLOGY_EDGES]
        can_edges = [
            edge for edge in edges
            if isinstance(edge, dict) and edge.get(KEY_EDGE_TYPE) == EDGE_TYPE_CAN_TRUNK
        ]

        self.assertEqual(result.code, SS__NORMAL)
        self.assertEqual(
            [edge.get(KEY_EDGE_ID) for edge in can_edges],
            ["edge_1", "edge_2"],
        )
        self.assertEqual(
            [
                (
                    edge.get(KEY_FROM_NODE),
                    edge.get(KEY_FROM_PORT),
                    edge.get(KEY_TO_NODE),
                    edge.get(KEY_TO_PORT),
                )
                for edge in can_edges
            ],
            [
                (1, RIGHT, 2, LEFT),
                (2, RIGHT, 3, LEFT),
            ],
        )


if __name__ == "__main__":
    unittest.main()
