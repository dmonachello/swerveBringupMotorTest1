from __future__ import annotations

"""
NAME
    test_bridge_cli_robot_non_motion_regression.py - Tests for connected non-motion regression script.
"""

import io
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from tools.can_nt.scripts.bridge_cli_robot_non_motion_regression import (
    CheckResult,
    _parse_args,
    _print_results,
    _verbose_enabled,
    main,
)


class BridgeCliRobotNonMotionRegressionTests(unittest.TestCase):
    def test_parse_args_accepts_verbose_switch(self) -> None:
        args = _parse_args(["--verbose", "--rio", "10.0.0.2"])

        self.assertTrue(args.verbose)
        self.assertEqual("10.0.0.2", args.rio)

    def test_verbose_enabled_accepts_env_flag(self) -> None:
        args = _parse_args([])
        original = os.environ.get("BRINGUP_REGRESSION_VERBOSE")
        os.environ["BRINGUP_REGRESSION_VERBOSE"] = "1"
        try:
            enabled = _verbose_enabled(args)
        finally:
            if original is None:
                os.environ.pop("BRINGUP_REGRESSION_VERBOSE", None)
            else:
                os.environ["BRINGUP_REGRESSION_VERBOSE"] = original

        self.assertTrue(enabled)

    def test_print_results_reports_summary(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = _print_results(
                [
                    CheckResult(label="one", ok=True, details="ok"),
                    CheckResult(label="two", ok=False, details="bad"),
                ]
            )

        self.assertEqual(1, exit_code)
        text = output.getvalue()
        self.assertIn("[PASS] one: ok", text)
        self.assertIn("[FAIL] two: bad", text)
        self.assertIn("SUMMARY: passed=1 failed=1 total=2", text)

    @patch("tools.can_nt.scripts.bridge_cli_robot_non_motion_regression._run_regression")
    def test_main_passes_verbose_to_regression(self, run_regression_mock) -> None:
        run_regression_mock.return_value = [CheckResult(label="one", ok=True, details="ok")]

        exit_code = main(["--verbose", "--rio", "10.0.0.2"])

        self.assertEqual(0, exit_code)
        run_regression_mock.assert_called_once_with("10.0.0.2", 5805, verbose=True)


if __name__ == "__main__":
    unittest.main()
