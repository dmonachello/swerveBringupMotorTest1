from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.can_inventory.can_inventory import dump_api_inventory
from tools.can_nt.can_profiles_dump import dump_profile

KEY_DEVICES = "devices"
KEY_NON_DEVICE_TRAFFIC_FAMILIES = "nonDeviceTrafficFamilies"
KEY_LABEL = "label"
KEY_FAMILY_KEY = "familyKey"
KEY_CANONICAL_IDENTITY = "canonicalIdentity"
KEY_DEVICE_TYPE = "deviceType"


class CanDumpOutputTests(unittest.TestCase):
    """
    NAME
        CanDumpOutputTests - Validate profile and inventory dump output contracts.
    """

    def test_dump_api_inventory_includes_non_device_traffic_families(self) -> None:
        pairs = {
            ("KRAKEN 9", 11, 1): {"first": 0.0, "last": 1.0, "count": 100.0},
        }
        non_device_traffic = [
            {
                KEY_FAMILY_KEY: "mfg-4_kind-nonDeviceFamily_type-0_id-63_api-7-3_pf-4_ps-28",
                "manufacturer": 4,
                "trafficKind": "nonDeviceFamily",
                "trafficRole": "SHARED_BUS_CONTROL",
                "reason": "broadcastSystem",
            }
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "inventory.json"
            dump_api_inventory(
                str(path),
                "test_profile",
                "slcan",
                "COM3",
                1_000_000,
                pairs,
                non_device_traffic,
                source="can_nt_bridge",
                robot_ip="172.22.11.2",
            )
            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual("KRAKEN 9", payload[KEY_DEVICES][0][KEY_LABEL])
        self.assertEqual(
            "mfg-4_kind-nonDeviceFamily_type-0_id-63_api-7-3_pf-4_ps-28",
            payload[KEY_NON_DEVICE_TRAFFIC_FAMILIES][0][KEY_FAMILY_KEY],
        )

    def test_dump_profile_includes_non_device_traffic_families_and_canonical_device(self) -> None:
        seen_keys = [(4, 2, 9), (4, 7, 18)]
        non_device_traffic = [
            {
                KEY_FAMILY_KEY: "mfg-4_kind-nonDeviceFamily_type-0_id-63_api-7-3_pf-4_ps-28",
                "manufacturer": 4,
                "trafficKind": "nonDeviceFamily",
                KEY_CANONICAL_IDENTITY: {
                    "manufacturer": 4,
                    KEY_DEVICE_TYPE: 0,
                    "deviceId": 63,
                },
            }
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "profile.json"
            dump_profile(
                str(path),
                "sniffer_profile",
                seen_keys,
                True,
                non_device_traffic,
            )
            payload = json.loads(path.read_text(encoding="utf-8"))

        labels = [entry[KEY_LABEL] for entry in payload[KEY_DEVICES]]
        self.assertIn("KRAKEN 9", labels)
        self.assertIn("CANCoder 18", labels)
        self.assertEqual(
            "mfg-4_kind-nonDeviceFamily_type-0_id-63_api-7-3_pf-4_ps-28",
            payload[KEY_NON_DEVICE_TRAFFIC_FAMILIES][0][KEY_FAMILY_KEY],
        )

    def test_dump_profile_devices_are_explicit_seen_keys_only_not_supporting_references(self) -> None:
        seen_keys = [(4, 2, 9), (4, 7, 18), (4, 4, 19), (4, 8, 20)]

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "profile.json"
            dump_profile(
                str(path),
                "sniffer_profile",
                seen_keys,
                True,
                [],
            )
            payload = json.loads(path.read_text(encoding="utf-8"))

        device_keys = {
            (int(entry["manufacturer"]), int(entry["deviceType"]), int(entry["id"]))
            for entry in payload[KEY_DEVICES]
        }
        self.assertIn((4, 2, 9), device_keys)
        self.assertIn((4, 7, 18), device_keys)
        self.assertIn((4, 4, 19), device_keys)
        self.assertIn((4, 8, 20), device_keys)
        self.assertNotIn((4, 2, 8), device_keys)
        self.assertNotIn((4, 7, 7), device_keys)
        self.assertNotIn((4, 4, 9), device_keys)
        self.assertNotIn((4, 8, 6), device_keys)


if __name__ == "__main__":
    unittest.main()
