from __future__ import annotations

import unittest
from unittest.mock import patch

from tools.common.bridge_config_io import (
    default_bridge_config,
    normalize_bridge_config,
    single_profile_bridge_config,
)


class BridgeConfigIoTests(unittest.TestCase):
    def test_default_bridge_config_uses_shared_empty_shape(self) -> None:
        payload = default_bridge_config()

        self.assertEqual(
            payload,
            {
                "schemaVersion": 2,
                "generatedAt": None,
                "byProfile": {},
            },
        )

    def test_normalize_bridge_config_stamps_generated_at(self) -> None:
        with patch(
            "tools.common.bridge_config_io.bridge_generated_at_now",
            return_value="2026-06-10T17:00:00Z",
        ):
            payload = normalize_bridge_config(
                {"byProfile": {"demo": {"groups": []}}},
                stamp_generated_at=True,
            )

        self.assertEqual(payload["schemaVersion"], 2)
        self.assertEqual(payload["generatedAt"], "2026-06-10T17:00:00Z")
        self.assertEqual(payload["byProfile"], {"demo": {"groups": []}})

    def test_single_profile_bridge_config_keeps_profile_scoped_payload(self) -> None:
        payload = single_profile_bridge_config(
            "demo",
            {"groups": [{"name": "drive"}]},
        )

        self.assertEqual(
            payload["byProfile"],
            {"demo": {"groups": [{"name": "drive"}]}},
        )


if __name__ == "__main__":
    unittest.main()
