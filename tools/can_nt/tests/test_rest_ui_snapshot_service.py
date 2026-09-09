"""
NAME
    test_rest_ui_snapshot_service.py - Unit tests for pure REST UI snapshot normalization.
"""

from __future__ import annotations

import unittest

from tools.can_nt.rest_ui_snapshot_service import (
    build_rest_ui_snapshots,
    normalize_runtime_snapshot,
    normalize_session_snapshot,
    normalize_tests_snapshot,
)


class RestUiSnapshotServiceTests(unittest.TestCase):
    """
    NAME
        RestUiSnapshotServiceTests - Validate raw REST payload normalization without UI wiring.
    """

    def test_normalize_session_snapshot_derives_handshake_and_owner_flags(self) -> None:
        snapshot = normalize_session_snapshot(
            {
                "sessionId": "session-1",
                "lastActivityMs": 321.0,
                "ownerClientId": "client-1",
            },
            received_at_ms=500.0,
        )

        self.assertEqual("session-1", snapshot.session_id)
        self.assertEqual(321.0, snapshot.last_activity_ms)
        self.assertTrue(snapshot.handshake_ready)
        self.assertTrue(snapshot.owner_known)
        self.assertEqual(500.0, snapshot.received_at_ms)

    def test_normalize_runtime_snapshot_maps_devices_and_groups(self) -> None:
        snapshot = normalize_runtime_snapshot(
            {
                "runtimeActive": True,
                "controlledLifecycleActive": True,
                "enabled": True,
                "estopped": False,
                "mode": "teleop",
                "selectedProfile": "test_minimal_25_9",
                "activeRuntimeProfile": "test_minimal_25_9",
                "devices": [
                    {
                        "label": "FALCON 9",
                        "enabled": True,
                        "present": True,
                        "instantiated": True,
                        "scopeActive": True,
                        "manualOperable": True,
                        "testOperable": False,
                        "testable": True,
                        "lifecycleState": "controlled-active",
                        "activeGroupLabel": "active-group",
                        "identity": {"manufacturer": 4, "deviceType": 2, "id": 9},
                        "telemetry": {"velRpm": 42.0},
                    }
                ],
                "groups": [
                    {
                        "name": "active-group",
                        "enabled": True,
                        "primaryLabel": "FALCON 9",
                        "bindingActive": False,
                        "memberCount": 1,
                        "members": [
                            {
                                "label": "FALCON 9",
                                "enabled": True,
                                "locked": True,
                                "runtimePresent": True,
                                "instantiated": True,
                                "scopeActive": True,
                                "testable": True,
                            }
                        ],
                    }
                ],
            },
            received_at_ms=1000.0,
        )

        self.assertTrue(snapshot.runtime_active)
        self.assertTrue(snapshot.controlled_lifecycle_active)
        self.assertEqual("teleop", snapshot.robot_mode)
        self.assertEqual(("FALCON 9",), snapshot.device_order)
        self.assertEqual(("active-group",), snapshot.group_order)
        self.assertTrue(snapshot.devices_by_label["FALCON 9"].manual_operable)
        self.assertEqual(42.0, snapshot.devices_by_label["FALCON 9"].telemetry["velRpm"])
        self.assertEqual(
            "FALCON 9",
            snapshot.groups_by_name["active-group"].members[0].label,
        )

    def test_normalize_runtime_snapshot_uses_received_time_for_missing_last_ack(self) -> None:
        snapshot = normalize_runtime_snapshot(
            {"selectedProfile": "test_minimal_25_9", "devices": []},
            received_at_ms=2500.0,
        )

        self.assertEqual(2500.0, snapshot.last_ack_ms)

    def test_normalize_tests_snapshot_handles_list_and_csv_required_devices(self) -> None:
        snapshot = normalize_tests_snapshot(
            {
                "rows": [
                    {
                        "name": "newTests_123",
                        "selected": True,
                        "enabled": True,
                        "status": "idle",
                        "requiredDevices": ["SPARKMAX/NEO 25", "FALCON 9", "controller0"],
                        "runnableKnown": True,
                        "runnableNow": True,
                        "blockedReason": "",
                    },
                    {
                        "name": "mtrs_limit",
                        "selected": False,
                        "enabled": True,
                        "status": "running",
                        "requiredDevices": "FALCON 9,lmtSw0,SPARKMAX/NEO 25",
                        "runnableKnown": True,
                        "runnableNow": False,
                        "blockedReason": "missing resource/device - lmtSw0",
                    },
                ],
                "run": {
                    "runId": 7,
                    "state": "running",
                    "test": "mtrs_limit",
                    "result": "",
                    "status": "running",
                    "message": "busy",
                    "startedAtMs": 10.0,
                    "finishedAtMs": 0.0,
                },
            },
            received_at_ms=800.0,
        )

        self.assertEqual("newTests_123", snapshot.selected_name)
        self.assertEqual("mtrs_limit", snapshot.active_name)
        self.assertEqual("running", snapshot.active_status)
        self.assertEqual(
            ("SPARKMAX/NEO 25", "FALCON 9", "controller0"),
            snapshot.rows_by_name["newTests_123"].required_devices,
        )
        self.assertTrue(snapshot.rows_by_name["newTests_123"].runnable_known)
        self.assertTrue(snapshot.rows_by_name["newTests_123"].runnable_now)
        self.assertEqual(
            ("FALCON 9", "lmtSw0", "SPARKMAX/NEO 25"),
            snapshot.rows_by_name["mtrs_limit"].required_devices,
        )
        self.assertEqual(
            "missing resource/device - lmtSw0",
            snapshot.rows_by_name["mtrs_limit"].blocked_reason,
        )
        self.assertEqual("mtrs_limit", snapshot.run.test_name)
        self.assertEqual("running", snapshot.run.status)

    def test_build_rest_ui_snapshots_constructs_all_three_snapshots(self) -> None:
        snapshots = build_rest_ui_snapshots(
            raw_session={"sessionId": "session-1"},
            raw_runtime={"selectedProfile": "test_minimal_25_9", "devices": []},
            raw_tests={"rows": [{"name": "spark25_leftY", "selected": True}]},
            received_at_ms=600.0,
        )

        self.assertEqual("session-1", snapshots.session.session_id)
        self.assertEqual("test_minimal_25_9", snapshots.runtime.selected_profile)
        self.assertEqual(("spark25_leftY",), snapshots.tests.ordered_names)


if __name__ == "__main__":
    unittest.main()
