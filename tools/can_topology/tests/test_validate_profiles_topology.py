from __future__ import annotations

import unittest
from copy import deepcopy

from tools.can_topology.validate_profiles import Reporter, validate_profiles
from tools.common.profile_io import compute_profiles_hash


class ValidateProfilesTopologyTests(unittest.TestCase):
    """
    NAME
        ValidateProfilesTopologyTests - Validate topology graph error handling.
    """

    def _base_payload(self) -> dict:
        payload = {
            "schema_version": 4,
            "data_version": "2026-05-09_topology_test",
            "data_hash": "",
            "default_profile": "demo",
            "profiles": {
                "demo": {
                    "devices": ["roborio", "motor1"],
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
                    "label": "motor1",
                    "deviceInterface": "CAN",
                    "manufacturer": 5,
                    "deviceType": 2,
                    "id": 25,
                    "model": "REV NEO",
                },
            ],
            "topology": {
                "version": 1,
                "source": "local",
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
                                "layout": {"bus": 0, "row": 0, "x": 200.0},
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
                    }
                },
            },
        }
        payload["data_hash"] = compute_profiles_hash(payload)
        return payload

    def _validate(self, payload: dict) -> tuple[list[str], list[str]]:
        payload["data_hash"] = compute_profiles_hash(payload)
        return validate_profiles(payload, Reporter(False))

    def test_accepts_valid_topology_graph(self) -> None:
        errors, warnings = self._validate(self._base_payload())
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_rejects_duplicate_topology_node_keys(self) -> None:
        payload = self._base_payload()
        payload["topology"]["profiles"]["demo"]["nodes"].append(
            {
                "key": 2,
                "nodeType": "junction",
                "label": "CANnect A",
                "layout": {"bus": 0, "row": 1, "x": 100.0},
            }
        )

        errors, _warnings = self._validate(payload)

        self.assertTrue(any("duplicate node key" in error for error in errors))

    def test_rejects_missing_device_ref(self) -> None:
        payload = self._base_payload()
        del payload["topology"]["profiles"]["demo"]["nodes"][1]["deviceRef"]

        errors, _warnings = self._validate(payload)

        self.assertTrue(any("missing deviceRef" in error for error in errors))

    def test_rejects_unknown_edge_endpoint(self) -> None:
        payload = self._base_payload()
        payload["topology"]["profiles"]["demo"]["edges"][0]["toNode"] = 99

        errors, _warnings = self._validate(payload)

        self.assertTrue(any("references missing node endpoint" in error for error in errors))

    def test_warns_on_unknown_edge_type(self) -> None:
        payload = self._base_payload()
        payload["topology"]["profiles"]["demo"]["edges"][0]["edgeType"] = "mystery_link"

        errors, warnings = self._validate(payload)

        self.assertEqual(errors, [])
        self.assertTrue(any("unknown edgeType" in warning for warning in warnings))
