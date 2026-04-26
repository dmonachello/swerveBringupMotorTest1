from __future__ import annotations

import unittest

from tools.can_nt.bridge_cli import BridgeCli


class BridgeCliTopologyShowTests(unittest.TestCase):
    """
    NAME
        BridgeCliTopologyShowTests - Validate local show-device topology metadata.
    """

    def test_local_device_topology_includes_neighbors_for_active_profile(self) -> None:
        cli = BridgeCli.__new__(BridgeCli)
        cli._active_profile_name = lambda: "demo"
        cli._local_root_payload = {
            "diagram": {
                "profiles": {
                    "demo": {
                        "nodes": [
                            {"key": 1, "label": "A", "bus": 0, "row": 0, "x": 10.0},
                            {"key": 2, "label": "B", "bus": 0, "row": 0, "x": 20.0},
                            {"key": 3, "label": "C", "bus": 0, "row": 0, "x": 30.0},
                        ],
                        "neighborLinks": [{"a": 1, "b": 2}, {"a": 2, "b": 3}],
                        "neighborPorts": [
                            {
                                "node": 2,
                                "port": "left",
                                "neighbor": 1,
                                "neighborPort": "right",
                            },
                            {
                                "node": 2,
                                "port": "right",
                                "neighbor": 3,
                                "neighborPort": "left",
                            },
                        ],
                    }
                }
            }
        }

        topology = cli._local_device_topology("B")

        self.assertEqual(topology["key"], 2)
        self.assertEqual(
            topology["neighborLinks"],
            [
                {"key": 1, "label": "A", "bus": 0, "row": 0, "x": 10.0},
                {"key": 3, "label": "C", "bus": 0, "row": 0, "x": 30.0},
            ],
        )
        self.assertEqual(
            topology["neighborPorts"],
            [
                {
                    "key": 1,
                    "label": "A",
                    "bus": 0,
                    "row": 0,
                    "x": 10.0,
                    "port": "left",
                    "neighborPort": "right",
                },
                {
                    "key": 3,
                    "label": "C",
                    "bus": 0,
                    "row": 0,
                    "x": 30.0,
                    "port": "right",
                    "neighborPort": "left",
                },
            ],
        )


if __name__ == "__main__":
    unittest.main()
