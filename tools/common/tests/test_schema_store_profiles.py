from __future__ import annotations

import unittest

from tools.config.schema_store import ConfigSchemaStore, DOC_PROFILES


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
        self.assertIn("Diagram node device id is not allowed: lmtSw0", messages)

    def test_diagram_device_node_label_must_resolve(self) -> None:
        payload = self._base_payload()
        payload["diagram"]["profiles"]["demo"]["nodes"][0]["label"] = "missing"

        result = self._validate(payload)

        self.assertFalse(result.ok())
        messages = [issue.message for issue in result.errors()]
        self.assertIn("Diagram node device label not found: missing", messages)


if __name__ == "__main__":
    unittest.main()
