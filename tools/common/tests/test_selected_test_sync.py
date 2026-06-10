from __future__ import annotations

import unittest

from tools.common.selected_test_sync import (
    current_test_choices,
    plan_selected_test_command,
    should_accept_robot_selected_test,
)


class SelectedTestSyncTests(unittest.TestCase):
    def test_current_test_choices_normalizes_values(self) -> None:
        self.assertEqual(
            ["spark25_leftY", "falcon9_leftY"],
            current_test_choices([" spark25_leftY ", "", "falcon9_leftY"]),
        )

    def test_should_accept_robot_selected_test_requires_profile_choice_membership(self) -> None:
        self.assertTrue(
            should_accept_robot_selected_test(
                "spark25_leftY",
                ["spark25_leftY", "falcon9_leftY"],
            )
        )
        self.assertFalse(
            should_accept_robot_selected_test(
                "Swerve Krakens Left Joystick",
                ["spark25_leftY", "falcon9_leftY"],
            )
        )

    def test_plan_selected_test_command_requires_sync_when_robot_is_stale(self) -> None:
        plan = plan_selected_test_command(
            "printSelectedTestSource",
            "spark25_leftY",
            "Swerve Krakens Left Joystick",
            ("printSelectedTestSource", "runTest", "toggleTest"),
        )

        self.assertTrue(plan.requires_sync)
        self.assertEqual("spark25_leftY", plan.selected_name)


if __name__ == "__main__":
    unittest.main()
