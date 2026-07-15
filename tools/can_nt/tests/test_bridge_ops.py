"""
NAME
    test_bridge_ops.py - Unit tests for bridge command wrapper payloads.
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from tools.can_nt import bridge_ops


class BridgeOpsCommandPayloadTest(unittest.TestCase):
    def test_lifecycle_activate_includes_membership_mode_when_provided(self) -> None:
        session = object()
        with patch("tools.can_nt.bridge_ops._send", return_value=7) as mock_send:
            seq = bridge_ops.lifecycle_activate(
                session,
                "active-group",
                "READ_ONLY",
                "PARTIAL",
            )

        self.assertEqual(7, seq)
        mock_send.assert_called_once_with(
            session,
            "lifecycleActivate",
            {
                "label": "active-group",
                "mode": "READ_ONLY",
                "membershipMode": "PARTIAL",
            },
        )

    def test_activate_selected_test_devices_includes_membership_mode_when_provided(self) -> None:
        session = object()
        with patch("tools.can_nt.bridge_ops._send", return_value=9) as mock_send:
            seq = bridge_ops.activate_selected_test_devices(
                session,
                "READ_ONLY",
                "FORCE",
            )

        self.assertEqual(9, seq)
        mock_send.assert_called_once_with(
            session,
            "activateSelectedTestDevices",
            {
                "mode": "READ_ONLY",
                "membershipMode": "FORCE",
            },
        )


if __name__ == "__main__":
    unittest.main()
