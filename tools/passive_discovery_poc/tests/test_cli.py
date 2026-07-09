from __future__ import annotations

import unittest
from unittest.mock import patch

from tools.passive_discovery_poc.passive_discovery import main


class PassiveDiscoveryCliTests(unittest.TestCase):
    """
    NAME
        PassiveDiscoveryCliTests - Validate CLI-facing error behavior.
    """

    def test_missing_profile_path_fails_cleanly_without_traceback_message(self) -> None:
        with patch(
            "sys.argv",
            [
                "passive_discovery.py",
                "--input",
                "tools/vendor_diag/usbCap8_socketcan.pcapng",
                "--profile-path",
                "does_not_exist.json",
            ],
        ):
            with self.assertRaises(SystemExit) as raised:
                main()

        self.assertEqual("ERROR: profile file not found: does_not_exist.json", str(raised.exception))

    def test_multiple_passive_sources_fail_cleanly(self) -> None:
        with patch(
            "sys.argv",
            [
                "passive_discovery.py",
                "--input",
                "tools/vendor_diag/usbCap8_socketcan.pcapng",
                "--live-slcan",
                "--channel",
                "COM3",
            ],
        ):
            with self.assertRaises(SystemExit) as raised:
                main()

        self.assertEqual(
            "ERROR: Select only one passive source: --input, --live-slcan, or --live-rev-serial.",
            str(raised.exception),
        )


if __name__ == "__main__":
    unittest.main()
