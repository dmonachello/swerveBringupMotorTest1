from __future__ import annotations

import unittest

from tools.config.schema_store import ConfigSchemaStore


class ConfigSchemaStoreBindingsTests(unittest.TestCase):
    """
    NAME
        ConfigSchemaStoreBindingsTests - Validate unified bindings controller resolution.
    """

    def test_validate_bindings_rejects_unknown_controller_references(self) -> None:
        store = ConfigSchemaStore()
        profiles_payload = {
            "schema_version": 4,
            "default_profile": "demo",
            "profiles": {
                "demo": {
                    "devices": [
                        "controller0",
                    ]
                }
            },
            "devices": [
                {
                    "label": "controller0",
                    "deviceInterface": "USB",
                    "type": "xboxController",
                    "port": 0,
                }
            ],
            "bindings": {
                "bindings": [
                    {
                        "command": "runTest",
                        "controller": "driver_typo",
                        "input": "button",
                        "id": "A",
                        "mode": "hold",
                    }
                ],
                "axes": [
                    {
                        "command": "leftDrive",
                        "controller": "axis_typo",
                        "id": "leftY",
                        "invert": True,
                        "deadband": 0.12,
                    }
                ],
            },
        }
        store.set_profiles_payload(profiles_payload)
        store.set_bindings_payload(profiles_payload["bindings"])

        result = store.validate_bindings_only(strict=True)
        messages = [issue.message for issue in result.errors()]

        self.assertFalse(result.ok())
        self.assertIn("Controller name not found: driver_typo", messages)
        self.assertIn("Controller name not found: axis_typo", messages)


if __name__ == "__main__":
    unittest.main()
