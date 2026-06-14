from __future__ import annotations

import unittest

from tools.common.runtime_state import (
    runtime_active_probe_attachment,
    runtime_attachment_age_seconds,
    runtime_device_field,
    runtime_device_index,
    runtime_presence_check_attachment,
)


class RuntimeStateSharedContractTests(unittest.TestCase):
    """
    NAME
        RuntimeStateSharedContractTests - Validate shared runtime-state helpers.
    """

    def _device(self) -> dict:
        return {
            "label": "motor1",
            "attachments": [
                {
                    "type": "ctreMotor",
                    "motorCurrentA": 4.2,
                    "cmdDuty": 0.3,
                },
                {
                    "type": "presenceCheck",
                    "updatedAtMs": 1_000,
                },
                {
                    "type": "activePresenceProbe",
                    "updatedAtMs": 2_000,
                    "bucket": "present",
                },
            ],
        }

    def test_runtime_device_field_falls_back_to_motor_attachment(self) -> None:
        self.assertEqual(runtime_device_field(self._device(), "cmdDuty"), 0.3)
        self.assertEqual(runtime_device_field(self._device(), "motorCurrentA"), 4.2)

    def test_runtime_attachment_helpers_resolve_expected_entries(self) -> None:
        device = self._device()

        self.assertEqual(runtime_presence_check_attachment(device)["type"], "presenceCheck")
        self.assertEqual(runtime_active_probe_attachment(device)["bucket"], "present")

    def test_runtime_attachment_age_seconds_uses_shared_clock_math(self) -> None:
        device = self._device()

        presence_age = runtime_attachment_age_seconds(
            device,
            "presenceCheck",
            now_epoch_sec=3.0,
        )
        probe_age = runtime_attachment_age_seconds(
            device,
            "activePresenceProbe",
            now_epoch_sec=3.0,
        )

        self.assertEqual(presence_age, 2.0)
        self.assertEqual(probe_age, 1.0)

    def test_runtime_device_index_normalizes_labels(self) -> None:
        payload = {"devices": [self._device(), {"label": " pdp "}]}

        indexed = runtime_device_index(payload)

        self.assertIn("motor1", indexed)
        self.assertIn("pdp", indexed)
