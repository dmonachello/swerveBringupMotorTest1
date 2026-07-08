from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.common.test_authoring.device_catalog import load_controller_names
from tools.common.tests.config_api_test_helper import write_profiles_payload


class DeviceCatalogControllerNamesTests(unittest.TestCase):
    """
    NAME
        DeviceCatalogControllerNamesTests - Validate controller-name discovery.
    """

    def test_load_controller_names_uses_sibling_profiles_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            deploy_dir = Path(temp_dir)
            profiles_path = deploy_dir / "bringup_system.json"
            bindings_path = deploy_dir / "bringup_bindings.json"
            write_profiles_payload(
                profiles_path,
                {
                    "schema_version": 5,
                    "data_version": "test",
                    "data_hash": "test",
                    "default_profile": "demo",
                    "profiles": {
                        "demo": {
                            "devices": ["controller0", "controller1", "motor1"]
                        }
                    },
                    "devices": [
                        {
                            "label": "controller0",
                            "deviceInterface": "USB",
                            "id": 0,
                            "type": "xboxController",
                        },
                        {
                            "label": "controller1",
                            "deviceInterface": "USB",
                            "id": 1,
                            "type": "xboxController",
                        },
                        {
                            "label": "controller2",
                            "deviceInterface": "USB",
                            "id": 2,
                            "type": "xboxController",
                        },
                        {
                            "label": "motor1",
                            "deviceInterface": "CAN",
                            "manufacturer": 5,
                            "deviceType": 2,
                            "id": 25,
                        },
                    ],
                },
                stamp=False,
            )
            bindings_path.write_text("{}", encoding="utf-8")

            names = load_controller_names(bindings_path)

            self.assertEqual(names, {"controller0", "controller1"})


if __name__ == "__main__":
    unittest.main()
