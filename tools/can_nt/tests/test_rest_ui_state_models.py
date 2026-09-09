"""
NAME
    test_rest_ui_state_models.py - Unit tests for typed REST UI snapshot models.
"""

from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError

from tools.can_nt.rest_ui_state_models import (
    RestUiSnapshots,
    RuntimeDeviceSnapshot,
    RuntimeGroupMemberSnapshot,
    RuntimeGroupSnapshot,
    RuntimeSnapshot,
    SessionSnapshot,
    TestRowSnapshot as UiTestRowSnapshot,
    TestsRunSnapshot as UiTestsRunSnapshot,
    TestsSnapshot as UiTestsSnapshot,
)


class RestUiStateModelsTests(unittest.TestCase):
    """
    NAME
        RestUiStateModelsTests - Validate additive typed REST UI snapshot containers.
    """

    def test_runtime_snapshot_preserves_device_and_group_maps(self) -> None:
        motor = RuntimeDeviceSnapshot(
            label="FALCON 9",
            enabled=True,
            present=True,
            instantiated=True,
            lifecycle_state="controlled-active",
        )
        member = RuntimeGroupMemberSnapshot(
            label="FALCON 9",
            enabled=True,
            instantiated=True,
            scope_active=True,
        )
        group = RuntimeGroupSnapshot(
            name="active-group",
            enabled=True,
            primary_label="FALCON 9",
            member_count=1,
            members=(member,),
        )

        snapshot = RuntimeSnapshot(
            received_at_ms=100.0,
            source_name="rest_runtime_state",
            selected_profile="test_minimal_25_9",
            active_runtime_profile="test_minimal_25_9",
            runtime_active=True,
            controlled_lifecycle_active=True,
            robot_enabled=True,
            robot_mode="teleop",
            last_ack_ms=99.0,
            devices_by_label={"FALCON 9": motor},
            groups_by_name={"active-group": group},
            device_order=("FALCON 9",),
            group_order=("active-group",),
        )

        self.assertTrue(snapshot.runtime_active)
        self.assertEqual("FALCON 9", snapshot.devices_by_label["FALCON 9"].label)
        self.assertEqual("active-group", snapshot.groups_by_name["active-group"].name)
        self.assertEqual("FALCON 9", snapshot.groups_by_name["active-group"].members[0].label)

    def test_tests_snapshot_preserves_order_and_run_state(self) -> None:
        selected = UiTestRowSnapshot(
            name="mtrs_limit",
            selected=True,
            enabled=True,
            status="idle",
            required_devices=("FALCON 9", "lmtSw0", "SPARKMAX/NEO 25"),
            exists_locally=True,
            runnable_known=True,
        )
        inactive = UiTestRowSnapshot(
            name="newTests_123",
            selected=False,
            enabled=True,
            status="idle",
            required_devices=("FALCON 9",),
            exists_locally=True,
            runnable_known=True,
        )
        run = UiTestsRunSnapshot(
            run_id=17,
            state="idle",
            test_name="mtrs_limit",
            result="PASS",
            status="complete",
            message="done",
            started_at_ms=10.0,
            finished_at_ms=20.0,
        )

        snapshot = UiTestsSnapshot(
            received_at_ms=100.0,
            source_name="rest_tests_state",
            generated_at_ms=95.0,
            selected_name="mtrs_limit",
            active_name="",
            active_status="",
            run_all_active=False,
            rows_by_name={"mtrs_limit": selected, "newTests_123": inactive},
            ordered_names=("mtrs_limit", "newTests_123"),
            run=run,
        )

        self.assertEqual(("mtrs_limit", "newTests_123"), snapshot.ordered_names)
        self.assertEqual(
            ("FALCON 9", "lmtSw0", "SPARKMAX/NEO 25"),
            snapshot.rows_by_name["mtrs_limit"].required_devices,
        )
        self.assertEqual("complete", snapshot.run.status)

    def test_bundle_defaults_are_constructible(self) -> None:
        bundle = RestUiSnapshots()

        self.assertIsInstance(bundle.session, SessionSnapshot)
        self.assertIsInstance(bundle.runtime, RuntimeSnapshot)
        self.assertIsInstance(bundle.tests, UiTestsSnapshot)
        self.assertEqual("", bundle.session.session_id)
        self.assertFalse(bundle.runtime.runtime_active)
        self.assertEqual((), bundle.tests.ordered_names)

    def test_models_are_frozen(self) -> None:
        snapshot = SessionSnapshot(session_id="session-1")

        with self.assertRaises(FrozenInstanceError):
            snapshot.session_id = "session-2"  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
