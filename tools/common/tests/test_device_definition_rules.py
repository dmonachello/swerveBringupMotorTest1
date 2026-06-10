from __future__ import annotations

import unittest

from tools.common.device_definition_rules import (
    format_device_required_field_issue,
    invalid_required_fields_for_interface,
    missing_required_fields_for_interface,
    required_fields_for_interface,
)


class DeviceDefinitionRulesTests(unittest.TestCase):
    """
    NAME
        DeviceDefinitionRulesTests - Cover shared device-definition rules.
    """

    def test_required_fields_for_can_excludes_interface_by_default(self) -> None:
        self.assertEqual(
            required_fields_for_interface("CAN"),
            ("manufacturer", "deviceType", "id"),
        )

    def test_required_fields_for_can_can_include_interface(self) -> None:
        self.assertEqual(
            required_fields_for_interface("CAN", include_interface=True),
            ("deviceInterface", "manufacturer", "deviceType", "id"),
        )

    def test_missing_required_fields_lists_exact_missing_keys(self) -> None:
        entry = {
            "label": "FALCON 9",
            "deviceInterface": "CAN",
            "id": 9,
        }

        self.assertEqual(
            missing_required_fields_for_interface(entry),
            ["manufacturer", "deviceType"],
        )

    def test_invalid_required_fields_lists_wrong_type_keys(self) -> None:
        entry = {
            "label": "FALCON 9",
            "deviceInterface": "CAN",
            "manufacturer": "5",
            "deviceType": 2,
            "id": 9,
        }

        self.assertEqual(
            invalid_required_fields_for_interface(entry),
            ["manufacturer"],
        )

    def test_format_device_required_field_issue_reports_missing_and_invalid(self) -> None:
        entry = {
            "label": "lmtSw0",
            "deviceInterface": "DIO",
            "id": "0",
        }

        self.assertEqual(
            format_device_required_field_issue("lmtSw0", entry),
            "Device 'lmtSw0' missing DIO fields: invert; invalid DIO fields: id.",
        )


if __name__ == "__main__":
    unittest.main()
