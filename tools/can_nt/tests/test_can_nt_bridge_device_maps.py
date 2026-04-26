from __future__ import annotations

import unittest

from tools.can_nt.can_nt_bridge import _build_device_maps


class CanNtBridgeDeviceMapTests(unittest.TestCase):
    """
    NAME
        CanNtBridgeDeviceMapTests - Validate profile device CAN key mapping.
    """

    def test_build_device_maps_accepts_canonical_schema_keys(self) -> None:
        devices = [
            {
                "label": "SPARKMAX/NEO 25",
                "manufacturer": 5,
                "deviceType": 2,
                "id": 25,
            },
            {
                "label": "FALCON 9",
                "manufacturer": 4,
                "deviceType": 2,
                "id": 9,
            },
        ]

        can_to_label, id_to_labels = _build_device_maps(devices)

        self.assertEqual(can_to_label[(5, 2, 25)], "SPARKMAX/NEO 25")
        self.assertEqual(can_to_label[(4, 2, 9)], "FALCON 9")
        self.assertEqual(id_to_labels[25], ["SPARKMAX/NEO 25"])
        self.assertEqual(id_to_labels[9], ["FALCON 9"])


if __name__ == "__main__":
    unittest.main()
