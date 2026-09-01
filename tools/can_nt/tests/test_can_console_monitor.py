from __future__ import annotations

"""
NAME
    test_can_console_monitor.py - Regressions for console-monitor rule matching.
"""

import unittest
from pathlib import Path

from tools.can_nt.can_console_monitor import ConsoleMonitor
from tools.can_nt.passive_discovery_integration_service import build_console_snapshot_from_entries


class ConsoleMonitorTests(unittest.TestCase):
    """
    NAME
        ConsoleMonitorTests - Verify console-monitor rule matching for device-targeted faults.
    """

    def test_pdp_reader_timeout_matches_power_distribution_access_stack_lines(self) -> None:
        rules_path = Path(__file__).resolve().parents[1] / "console_rules.json"
        monitor = ConsoleMonitor(
            rules_path=str(rules_path),
            inactivity_timeout=5.0,
            publish_rate_hz=5.0,
            debug_log_path="",
            debug_log_max_mb=1,
            debug_log_max_files=1,
            transport="tcp",
            host="127.0.0.1",
            port=0,
            device_label_resolver=None,
        )
        try:
            matched = monitor._process_line(
                "Error at frc.robot.manufacturers.ctre.util.PdpStatusReader$WpiPowerDistributionAccess.getCurrent(PdpStatusReader.java:200): HAL: CAN Receive has Timed Out",
                100.0,
            )

            self.assertTrue(matched)
            entries = monitor.snapshot_entries(now=100.0)
            self.assertEqual(1, len(entries))
            self.assertEqual("PDP_STATUS_READER_TIMEOUT", entries[0].event_type)
            self.assertEqual("pdp", entries[0].device_label)
            self.assertEqual("ERROR", entries[0].severity)

            snapshot = build_console_snapshot_from_entries(entries, now_s=100.0)
            self.assertIn("pdp", snapshot["devices"])
            self.assertTrue(snapshot["devices"]["pdp"]["hasError"])
            self.assertEqual("ctre_timeout", snapshot["devices"]["pdp"]["topFaultFamily"])
        finally:
            monitor.stop()

    def test_generic_can_frame_too_stale_line_matches_system_console_event(self) -> None:
        rules_path = Path(__file__).resolve().parents[1] / "console_rules.json"
        monitor = ConsoleMonitor(
            rules_path=str(rules_path),
            inactivity_timeout=5.0,
            publish_rate_hz=5.0,
            debug_log_path="",
            debug_log_max_mb=1,
            debug_log_max_files=1,
            transport="tcp",
            host="127.0.0.1",
            port=0,
            device_label_resolver=None,
        )
        try:
            matched = monitor._process_line(
                "CAN frame not received/too-stale. Check the CAN bus wiring, CAN bus utilization, and power to the device.",
                100.0,
            )

            self.assertTrue(matched)
            entries = monitor.snapshot_entries(now=100.0)
            self.assertEqual(1, len(entries))
            self.assertEqual("CAN_FRAME_TOO_STALE", entries[0].event_type)
            self.assertIsNone(entries[0].device_label)
            snapshot = build_console_snapshot_from_entries(entries, now_s=100.0)
            self.assertEqual(
                ["[WARN] CAN_FRAME_TOO_STALE: CAN frame not received/too-stale. Check the CAN bus wiring, CAN bus utilization, and power to the device."],
                snapshot["system"],
            )
            self.assertTrue(snapshot["systemConflict"])
        finally:
            monitor.stop()

    def test_can_frame_too_stale_line_with_device_tail_matches_targeted_device_event(self) -> None:
        rules_path = Path(__file__).resolve().parents[1] / "console_rules.json"
        monitor = ConsoleMonitor(
            rules_path=str(rules_path),
            inactivity_timeout=5.0,
            publish_rate_hz=5.0,
            debug_log_path="",
            debug_log_max_mb=1,
            debug_log_max_files=1,
            transport="tcp",
            host="127.0.0.1",
            port=0,
            device_label_resolver=lambda device_id: {19: "pigeon 2"}.get(device_id),
        )
        try:
            matched = monitor._process_line(
                'CAN frame not received/too-stale. Check the CAN bus wiring, CAN bus utilization, and power to the device. pigeon 2 19 ("") Status Signal StickyFaultField',
                100.0,
            )

            self.assertTrue(matched)
            entries = monitor.snapshot_entries(now=100.0)
            self.assertEqual(1, len(entries))
            self.assertEqual("CAN_FRAME_TOO_STALE", entries[0].event_type)
            self.assertEqual(19, entries[0].device_id)
            self.assertEqual("pigeon 2", entries[0].device_label)

            snapshot = build_console_snapshot_from_entries(entries, now_s=100.0)
            self.assertIn("pigeon 2", snapshot["devices"])
            self.assertEqual(1, snapshot["devices"]["pigeon 2"]["totalCount"])
            self.assertTrue(snapshot["devices"]["pigeon 2"]["hasWarn"])
            self.assertEqual(1, snapshot["stats"]["deviceEventCount"])
            self.assertEqual(0, snapshot["stats"]["systemEventCount"])
        finally:
            monitor.stop()

    def test_generic_device_firmware_query_failure_matches_system_console_event(self) -> None:
        rules_path = Path(__file__).resolve().parents[1] / "console_rules.json"
        monitor = ConsoleMonitor(
            rules_path=str(rules_path),
            inactivity_timeout=5.0,
            publish_rate_hz=5.0,
            debug_log_path="",
            debug_log_max_mb=1,
            debug_log_max_files=1,
            transport="tcp",
            host="127.0.0.1",
            port=0,
            device_label_resolver=None,
        )
        try:
            matched = monitor._process_line(
                "Device firmware could not be retrieved. Check that the device is running v6 firmware, the device ID is correct, the specified CAN bus is correct, and the device is powered.",
                100.0,
            )

            self.assertTrue(matched)
            entries = monitor.snapshot_entries(now=100.0)
            self.assertEqual(1, len(entries))
            self.assertEqual("DEVICE_FW_QUERY_FAIL", entries[0].event_type)
            snapshot = build_console_snapshot_from_entries(entries, now_s=100.0)
            self.assertEqual(
                ["[WARN] DEVICE_FW_QUERY_FAIL: Device firmware could not be retrieved. Check that the device is running v6 firmware, the device ID is correct, the specified CAN bus is correct, and the device is powered."],
                snapshot["system"],
            )
        finally:
            monitor.stop()

    def test_device_firmware_query_failure_line_with_device_tail_matches_targeted_device_event(self) -> None:
        rules_path = Path(__file__).resolve().parents[1] / "console_rules.json"
        monitor = ConsoleMonitor(
            rules_path=str(rules_path),
            inactivity_timeout=5.0,
            publish_rate_hz=5.0,
            debug_log_path="",
            debug_log_max_mb=1,
            debug_log_max_files=1,
            transport="tcp",
            host="127.0.0.1",
            port=0,
            device_label_resolver=lambda device_id: {9: "FALCON 9"}.get(device_id),
        )
        try:
            matched = monitor._process_line(
                'Device firmware could not be retrieved. Check that the device is running v6 firmware, the device ID is correct, the specified CAN bus is correct, and the device is powered. talon fx 9 ("")',
                100.0,
            )

            self.assertTrue(matched)
            entries = monitor.snapshot_entries(now=100.0)
            self.assertEqual(1, len(entries))
            self.assertEqual("DEVICE_FW_QUERY_FAIL", entries[0].event_type)
            self.assertEqual(9, entries[0].device_id)
            self.assertEqual("FALCON 9", entries[0].device_label)

            snapshot = build_console_snapshot_from_entries(entries, now_s=100.0)
            self.assertIn("falcon 9", snapshot["devices"])
            self.assertEqual(1, snapshot["devices"]["falcon 9"]["totalCount"])
            self.assertTrue(snapshot["devices"]["falcon 9"]["hasWarn"])
            self.assertEqual(1, snapshot["stats"]["deviceEventCount"])
            self.assertEqual(0, snapshot["stats"]["systemEventCount"])
        finally:
            monitor.stop()

    def test_can_message_not_found_matches_system_console_event(self) -> None:
        rules_path = Path(__file__).resolve().parents[1] / "console_rules.json"
        monitor = ConsoleMonitor(
            rules_path=str(rules_path),
            inactivity_timeout=5.0,
            publish_rate_hz=5.0,
            debug_log_path="",
            debug_log_max_mb=1,
            debug_log_max_files=1,
            transport="tcp",
            host="127.0.0.1",
            port=0,
            device_label_resolver=None,
        )
        try:
            matched = monitor._process_line(
                "CAN: Message not found",
                100.0,
            )

            self.assertTrue(matched)
            entries = monitor.snapshot_entries(now=100.0)
            self.assertEqual(1, len(entries))
            self.assertEqual("CAN_MESSAGE_NOT_FOUND", entries[0].event_type)
            snapshot = build_console_snapshot_from_entries(entries, now_s=100.0)
            self.assertEqual(
                ["[WARN] CAN_MESSAGE_NOT_FOUND: CAN: Message not found"],
                snapshot["system"],
            )
        finally:
            monitor.stop()

    def test_loop_overrun_is_captured_but_excluded_from_active_console_snapshot(self) -> None:
        rules_path = Path(__file__).resolve().parents[1] / "console_rules.json"
        monitor = ConsoleMonitor(
            rules_path=str(rules_path),
            inactivity_timeout=5.0,
            publish_rate_hz=5.0,
            debug_log_path="",
            debug_log_max_mb=1,
            debug_log_max_files=1,
            transport="tcp",
            host="127.0.0.1",
            port=0,
            device_label_resolver=None,
        )
        try:
            matched = monitor._process_line(
                "Warning at edu.wpi.first.wpilibj.IterativeRobotBase.printLoopOverrunMessage(IterativeRobotBase.java:436): Loop time of 0.02s overrun",
                100.0,
            )

            self.assertTrue(matched)
            entries = monitor.snapshot_entries(now=100.0)
            self.assertEqual(1, len(entries))
            self.assertEqual("LOOP_OVERRUN", entries[0].event_type)

            snapshot = build_console_snapshot_from_entries(entries, now_s=100.0)
            self.assertEqual([], snapshot["system"])
            self.assertEqual(0, snapshot["stats"]["totalCount"])
            self.assertEqual(0, snapshot["stats"]["systemEventCount"])
            self.assertEqual(1, len(snapshot["records"]))
            self.assertEqual("LOOP_OVERRUN", snapshot["records"][0]["summary"])
        finally:
            monitor.stop()
