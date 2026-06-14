from __future__ import annotations

import unittest

from tools.common.topology_query import topology_device_summary
from tools.common.topology_validate import validate_topology_payload
from tools.common.profile_constants import EDGE_TYPE_ETHERNET


class TopologySharedContractTests(unittest.TestCase):
    """
    NAME
        TopologySharedContractTests - Validate shared topology validation and query helpers.
    """

    def _payload(self) -> dict:
        return {
            "devices": [
                {"label": "A", "deviceInterface": "CAN", "manufacturer": 1, "deviceType": 1, "id": 1},
                {"label": "B", "deviceInterface": "CAN", "manufacturer": 1, "deviceType": 1, "id": 2},
            ],
            "topology": {
                "profiles": {
                    "demo": {
                        "nodes": [
                            {"key": 1, "nodeType": "device", "deviceRef": "A", "layout": {"bus": 0, "row": 0, "x": 10.0}},
                            {"key": 2, "nodeType": "device", "deviceRef": "B", "layout": {"bus": 0, "row": 0, "x": 20.0}},
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
                    }
                }
            },
        }

    def test_validate_topology_payload_reports_duplicate_node_keys(self) -> None:
        payload = self._payload()
        payload["topology"]["profiles"]["demo"]["nodes"].append(  # type: ignore[index]
            {"key": 2, "nodeType": "junction", "label": "dup"}
        )

        errors, warnings = validate_topology_payload(payload, {"a": {}, "b": {}})

        self.assertTrue(any("duplicate node key" in message for message in errors))
        self.assertEqual(warnings, [])

    def test_validate_topology_payload_reports_missing_edge_endpoint(self) -> None:
        payload = self._payload()
        payload["topology"]["profiles"]["demo"]["edges"][0]["toNode"] = 99  # type: ignore[index]

        errors, _warnings = validate_topology_payload(payload, {"a": {}, "b": {}})

        self.assertTrue(any("references missing node endpoint" in message for message in errors))

    def test_topology_device_summary_returns_neighbor_links_and_ports(self) -> None:
        payload = self._payload()
        registry = {"a": payload["devices"][0], "b": payload["devices"][1]}  # type: ignore[index]

        summary = topology_device_summary(payload, "demo", "B", registry)

        self.assertEqual(summary["label"], "B")
        self.assertEqual(summary["neighborLinks"][0]["label"], "A")
        self.assertEqual(summary["neighborPorts"][0]["neighborPort"], "right")
        self.assertEqual(summary["neighborPorts"][0]["port"], "left")

    def test_topology_device_summary_prefers_explicit_neighbor_graph_when_present(self) -> None:
        payload = self._payload()
        payload["topology"]["profiles"]["demo"]["neighborLinks"] = [  # type: ignore[index]
            {"a": 1, "b": 2}
        ]
        payload["topology"]["profiles"]["demo"]["neighborPorts"] = [  # type: ignore[index]
            {
                "node": 2,
                "port": "backbone",
                "neighbor": 1,
                "neighborPort": "backbone",
                "edgeType": EDGE_TYPE_ETHERNET,
                "id": "explicit_1",
            }
        ]
        registry = {"a": payload["devices"][0], "b": payload["devices"][1]}  # type: ignore[index]

        summary = topology_device_summary(payload, "demo", "B", registry)

        self.assertEqual(summary["neighborLinks"][0]["label"], "A")
        self.assertEqual(summary["neighborPorts"][0]["port"], "backbone")
        self.assertEqual(summary["neighborPorts"][0]["neighborPort"], "backbone")
        self.assertEqual(summary["neighborPorts"][0]["edgeType"], EDGE_TYPE_ETHERNET)
        self.assertEqual(summary["neighborPorts"][0]["id"], "explicit_1")
