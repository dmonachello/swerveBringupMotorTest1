from __future__ import annotations

"""
NAME
    test_can_table_import.py - Regression tests for CAN table import utility output.
"""

import tempfile
import unittest
from pathlib import Path

from tools.can_topology.can_table_import import main
from tools.common.tests.config_api_test_helper import load_profiles_payload


class CanTableImportTests(unittest.TestCase):
    def test_main_writes_profiles_payload_through_shared_config_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "table.txt"
            output_path = Path(temp_dir) / "bringup_system.json"
            input_path.write_text(
                "Subsystem  Device  CAN ID\n"
                "Drive  Falcon 9  9\n"
                "Sensors  Pigeon  12\n",
                encoding="utf-8",
            )

            exit_code = main(
                [
                    "--profile",
                    "demo",
                    "--input",
                    str(input_path),
                    "--output",
                    str(output_path),
                ]
            )

            payload = load_profiles_payload(output_path)

        self.assertEqual(0, exit_code)
        self.assertEqual("demo", payload["default_profile"])
        self.assertEqual(["Falcon 9", "Pigeon"], payload["profiles"]["demo"]["devices"])


if __name__ == "__main__":
    unittest.main()
