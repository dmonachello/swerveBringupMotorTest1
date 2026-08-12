from __future__ import annotations

import unittest

from tools.can_nt.can_nt_bridge import (
    _build_device_maps,
    _profile_context_poll_due,
    _resolve_visibility_label_for_key,
    _resolve_profile_context_name_from_runtime_state,
)

TEST_UNPROFILED_IDENTITY = (4, 2, 6)
TEST_UNPROFILED_IDENTITY_TEXT = "4:2:6"
TEST_EXPECTED_IDENTITY = (4, 2, 9)
TEST_EXPECTED_IDENTITY_TEXT = "4:2:9"
TEST_EXPECTED_LABEL = "FALCON 9"
TEST_ALLOCATED_LABEL = "UNPROFILED_DEVICE_40206"


class _FakeVisibilityProvider:
    """
    NAME
        _FakeVisibilityProvider - Test double for visibility label allocation.
    """

    def __init__(self) -> None:
        self.calls = []

    def resolve_label(self, identity_key: str, suggested_label: str | None = None) -> str:
        """
        NAME
            resolve_label - Capture allocation requests from tests.
        """
        self.calls.append((identity_key, suggested_label))
        return suggested_label or TEST_ALLOCATED_LABEL


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

    def test_resolve_visibility_label_does_not_allocate_for_supporting_unknown(self) -> None:
        provider = _FakeVisibilityProvider()

        label = _resolve_visibility_label_for_key(
            TEST_UNPROFILED_IDENTITY,
            {},
            provider,
            allow_unexpected_create=False,
        )

        self.assertEqual(TEST_UNPROFILED_IDENTITY_TEXT, label)
        self.assertEqual([], provider.calls)

    def test_resolve_visibility_label_can_allocate_for_definite_unknown(self) -> None:
        provider = _FakeVisibilityProvider()

        label = _resolve_visibility_label_for_key(
            TEST_UNPROFILED_IDENTITY,
            {},
            provider,
            allow_unexpected_create=True,
        )

        self.assertEqual(TEST_ALLOCATED_LABEL, label)
        self.assertEqual([(TEST_UNPROFILED_IDENTITY_TEXT, None)], provider.calls)

    def test_resolve_visibility_label_uses_configured_label_without_allocating(self) -> None:
        provider = _FakeVisibilityProvider()

        label = _resolve_visibility_label_for_key(
            TEST_EXPECTED_IDENTITY,
            {TEST_EXPECTED_IDENTITY: TEST_EXPECTED_LABEL},
            provider,
            allow_unexpected_create=False,
        )

        self.assertEqual(TEST_EXPECTED_LABEL, label)
        self.assertEqual([], provider.calls)

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
