from __future__ import annotations

import unittest

from tools.can_nt.can_nt_bridge import (
    _build_device_maps,
    _profile_context_poll_due,
    _resolve_profile_context_name_from_runtime_state,
)


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

    def test_resolve_profile_context_name_from_runtime_state_prefers_active_then_selected(self) -> None:
        self.assertEqual(
            "runtime_profile",
            _resolve_profile_context_name_from_runtime_state(
                {
                    "activeRuntimeProfile": "runtime_profile",
                    "selectedProfile": "selected_profile",
                },
                "fallback_profile",
            ),
        )
        self.assertEqual(
            "selected_profile",
            _resolve_profile_context_name_from_runtime_state(
                {
                    "activeRuntimeProfile": "",
                    "selectedProfile": "selected_profile",
                },
                "fallback_profile",
            ),
        )
        self.assertEqual(
            "fallback_profile",
            _resolve_profile_context_name_from_runtime_state({}, "fallback_profile"),
        )

    def test_profile_context_poll_due_obeys_tracking_flag_and_interval(self) -> None:
        self.assertFalse(_profile_context_poll_due(False, 5.0, 0.0))
        self.assertFalse(_profile_context_poll_due(True, 0.5, 0.0))
        self.assertTrue(_profile_context_poll_due(True, 1.0, 0.0))
        self.assertTrue(_profile_context_poll_due(True, 2.5, 1.0))


if __name__ == "__main__":
    unittest.main()
