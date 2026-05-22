from __future__ import annotations

import unittest

from tools.config.schema_store import ConfigSchemaStore, DOC_BINDINGS, DOC_PROFILES


class ConfigSchemaStoreProfilesTests(unittest.TestCase):
    """
    NAME
        ConfigSchemaStoreProfilesTests - Validate profile/device schema rules.
    """

    def _base_payload(self) -> dict:
        return {
            "schema_version": 4,
            "data_version": "test",
            "data_hash": "test",
            "default_profile": "demo",
            "profiles": {
                "demo": {
                    "devices": ["lmtSw0"],
                }
            },
            "devices": [
                {
                    "label": "lmtSw0",
                    "deviceInterface": "DIO",
                    "id": 0,
                    "invert": False,
                    "type": "limitSwitch",
                }
            ],
            "diagram": {
                "profiles": {
                    "demo": {
                        "nodes": [
                            {
                                "nodeType": "device",
                                "key": 1,
                                "label": "lmtSw0",
                            }
                        ]
                    }
                }
            },
        }

    def _validate(self, payload: dict):
        store = ConfigSchemaStore()
        store._db.set_payload(DOC_PROFILES, payload)
        return store.validate(strict=True)

    def test_dio_device_uses_id_not_dio(self) -> None:
        payload = self._base_payload()
        payload["devices"][0].pop("id")
        payload["devices"][0]["dio"] = 0

        result = self._validate(payload)

        self.assertFalse(result.ok())
        messages = [issue.message for issue in result.errors()]
        self.assertIn("Device lmtSw0: Missing required field: id", messages)

    def test_duplicate_labels_are_case_insensitive(self) -> None:
        payload = self._base_payload()
        payload["devices"].append(
            {
                "label": "LMTSW0",
                "deviceInterface": "DIO",
                "id": 1,
                "invert": False,
                "type": "limitSwitch",
            }
        )

        result = self._validate(payload)

        self.assertFalse(result.ok())
        messages = [issue.message for issue in result.errors()]
        self.assertIn("Duplicate device label: LMTSW0", messages)

    def test_diagram_device_node_id_is_forbidden(self) -> None:
        payload = self._base_payload()
        payload["diagram"]["profiles"]["demo"]["nodes"][0]["id"] = 0

        result = self._validate(payload)

        self.assertFalse(result.ok())
        messages = [issue.message for issue in result.errors()]
        self.assertIn("Profile demo diagram node 1: device id is not allowed: lmtSw0", messages)

    def test_diagram_device_node_label_must_resolve(self) -> None:
        payload = self._base_payload()
        payload["diagram"]["profiles"]["demo"]["nodes"][0]["label"] = "missing"

        result = self._validate(payload)

        self.assertFalse(result.ok())
        messages = [issue.message for issue in result.errors()]
        self.assertIn("Profile demo diagram node 1: device label not found: missing", messages)

    def test_topology_device_ref_error_names_profile_and_node(self) -> None:
        payload = self._base_payload()
        payload["topology"] = {
            "profiles": {
                "demo": {
                    "nodes": [
                        {
                            "key": 7,
                            "nodeType": "device",
                            "deviceRef": "missing",
                        }
                    ]
                }
            }
        }

        result = self._validate(payload)

        self.assertFalse(result.ok())
        messages = [issue.message for issue in result.errors()]
        self.assertIn("Profile demo topology node 7: deviceRef not found: missing", messages)

    def test_profile_devices_type_error_names_profile(self) -> None:
        payload = self._base_payload()
        payload["profiles"]["demo"]["devices"] = "lmtSw0"

        result = self._validate(payload)

        self.assertFalse(result.ok())
        messages = [issue.message for issue in result.errors()]
        self.assertIn("Profile demo: Invalid type for devices", messages)

    def test_sanitize_profiles_payload_drops_invalid_entries_and_refs(self) -> None:
        store = ConfigSchemaStore()
        payload = self._base_payload()
        payload["devices"].append(
            {
                "label": "badCan",
                "deviceInterface": "CAN",
                "deviceType": 1,
            }
        )
        payload["profiles"]["demo"]["devices"].extend(["badCan", "missing"])
        payload["bridgeConfig"] = {
            "schemaVersion": 2,
            "generatedAt": None,
            "byProfile": {
                "demo": {
                    "groups": [
                        {
                            "name": "drive",
                            "enabled": True,
                            "members": [
                                {"device": "lmtSw0", "enabled": True},
                                {"device": "missing", "enabled": True},
                            ],
                        }
                    ],
                    "selectedDevice": {"device": "missing", "enabled": True},
                }
            },
        }

        sanitized, warnings, changed = store.sanitize_profiles_payload(payload)

        self.assertTrue(changed)
        self.assertEqual([device["label"] for device in sanitized["devices"]], ["lmtSw0"])
        self.assertEqual(sanitized["profiles"]["demo"]["devices"], ["lmtSw0"])
        members = sanitized["bridgeConfig"]["byProfile"]["demo"]["groups"][0]["members"]
        self.assertEqual(members, [{"device": "lmtSw0", "enabled": True}])
        self.assertEqual(
            sanitized["bridgeConfig"]["byProfile"]["demo"]["selectedDevice"],
            {"device": "", "enabled": False},
        )
        joined = "\n".join(warnings)
        self.assertIn("Dropped invalid device 'badCan'", joined)
        self.assertIn("Dropped missing device 'missing' from profile 'demo'.", joined)

    def test_sanitize_bindings_payload_drops_invalid_entries(self) -> None:
        store = ConfigSchemaStore()
        payload = {
            "controllers": [
                {"name": "driver", "type": "xbox", "port": 0},
                {"name": "bad", "type": "xbox"},
            ],
            "bindings": [
                {
                    "command": "printState",
                    "controller": "driver",
                    "input": "button",
                    "id": "A",
                    "mode": "press",
                },
                {
                    "command": "bad",
                    "controller": "missing",
                    "input": "button",
                    "id": "B",
                    "mode": "press",
                },
            ],
            "axes": [
                {
                    "command": "leftDrive",
                    "controller": "driver",
                    "id": "leftY",
                    "invert": False,
                    "deadband": 0.1,
                },
                {
                    "command": "badAxis",
                    "controller": "missing",
                    "id": "rightY",
                    "invert": False,
                    "deadband": 0.1,
                },
            ],
        }

        sanitized, warnings, changed = store.sanitize_bindings_payload(payload)

        self.assertTrue(changed)
        self.assertEqual(len(sanitized["controllers"]), 1)
        self.assertEqual(len(sanitized["bindings"]), 1)
        self.assertEqual(len(sanitized["axes"]), 1)
        self.assertIn("Dropped invalid controller 'bad'", "\n".join(warnings))

    def test_bindings_validation_accepts_profile_owned_controller_names(self) -> None:
        store = ConfigSchemaStore()
        store._db.set_payload(
            DOC_PROFILES,
            {
                "schema_version": 4,
                "data_version": "test",
                "data_hash": "test",
                "default_profile": "demo",
                "profiles": {"demo": {"devices": ["controller0", "controller1"]}},
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
                ],
            },
        )
        store._db.set_payload(
            DOC_BINDINGS,
            {
                "controllers": [{"name": "controller0", "type": "XBOX", "port": 0}],
                "bindings": [
                    {
                        "command": "runTest",
                        "controller": "controller1",
                        "input": "button",
                        "id": "A",
                        "mode": "hold",
                    }
                ],
                "axes": [
                    {
                        "command": "rightDrive",
                        "controller": "controller1",
                        "id": "rightY",
                        "invert": False,
                        "deadband": 0.1,
                    }
                ],
            },
        )

        result = store.validate_bindings_only(strict=True)

        self.assertTrue(result.ok(), [issue.message for issue in result.errors()])

    def test_sanitize_bindings_payload_keeps_profile_owned_controller_refs(self) -> None:
        store = ConfigSchemaStore()
        store._db.set_payload(
            DOC_PROFILES,
            {
                "schema_version": 4,
                "data_version": "test",
                "data_hash": "test",
                "default_profile": "demo",
                "profiles": {"demo": {"devices": ["controller0", "controller1"]}},
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
                ],
            },
        )
        payload = {
            "controllers": [{"name": "controller0", "type": "XBOX", "port": 0}],
            "bindings": [
                {
                    "command": "runTest",
                    "controller": "controller1",
                    "input": "button",
                    "id": "A",
                    "mode": "hold",
                }
            ],
            "axes": [
                {
                    "command": "rightDrive",
                    "controller": "controller1",
                    "id": "rightY",
                    "invert": False,
                    "deadband": 0.1,
                }
            ],
        }

        sanitized, warnings, changed = store.sanitize_bindings_payload(payload)

        self.assertFalse(changed)
        self.assertEqual(warnings, [])
        self.assertEqual(len(sanitized["bindings"]), 1)
        self.assertEqual(len(sanitized["axes"]), 1)


if __name__ == "__main__":
    unittest.main()
