from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.common.config_lifecycle import ConfigLifecycleService


KEY_BRIDGE_CONFIG = "bridgeConfig"
KEY_SCHEMA_VERSION = "schema_version"
KEY_PROFILES = "profiles"


class ConfigLifecycleServiceTests(unittest.TestCase):
    """Validate shared config lifecycle semantics."""

    def test_collect_source_entries_roundtrip(self) -> None:
        service = ConfigLifecycleService()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.json"
            path.write_text("{}", encoding="utf-8")
            entries = service.collect_source_entries([("profiles", path), ("tests", None)])
            as_dict = service.source_entries_to_dicts(entries)
            self.assertEqual(as_dict[0]["name"], "profiles")
            self.assertTrue(as_dict[0]["exists"])
            self.assertEqual(as_dict[1]["path"], "")

    def test_sync_profiles_payload_writes_both_outputs(self) -> None:
        service = ConfigLifecycleService()
        payload = {
            KEY_SCHEMA_VERSION: 1,
            KEY_PROFILES: {},
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            canonical = base / "data.json"
            deploy = base / "deploy" / "data.json"
            stamped = service.sync_profiles_payload(
                payload,
                canonical_path=canonical,
                deploy_path=deploy,
                stamp=True,
            )
            self.assertTrue(canonical.exists())
            self.assertTrue(deploy.exists())
            self.assertIn("data_hash", stamped)
            self.assertIn("data_version", stamped)

    def test_stamp_profiles_payload_normalizes_bridge_config(self) -> None:
        service = ConfigLifecycleService()
        payload = {
            KEY_SCHEMA_VERSION: 1,
            KEY_PROFILES: {},
            KEY_BRIDGE_CONFIG: {
                "byProfile": {
                    "demo": {
                        "groups": [],
                    }
                }
            },
        }

        with patch(
            "tools.common.bridge_config_io.bridge_generated_at_now",
            return_value="2026-06-10T17:15:00Z",
        ):
            stamped = service.stamp_profiles_payload(payload, stamp=True)

        self.assertEqual(stamped[KEY_BRIDGE_CONFIG]["schemaVersion"], 2)
        self.assertEqual(stamped[KEY_BRIDGE_CONFIG]["generatedAt"], "2026-06-10T17:15:00Z")


if __name__ == "__main__":
    unittest.main()

