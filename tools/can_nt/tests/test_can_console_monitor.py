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
