from __future__ import annotations

import unittest
from unittest.mock import patch

from tools.can_nt.scripts.changelog_guard import (
    EXIT_FAILED,
    EXIT_OK,
    changelog_is_changed,
    git_changed_paths,
    main,
    major_change_paths,
)


class ChangelogGuardTests(unittest.TestCase):
    def test_major_change_paths_filters_expected_surfaces(self) -> None:
        paths = [
            "tools/can_nt/bridge_cli.py",
            "tools/common/robot_test_dsl/validator.py",
            "tools/can_topology/can_top_editor.py",
            "src/main/java/frc/robot/Robot.java",
            "src/main/deploy/bringup_system.json",
            "docs/examples/sample.dsl",
            "tests/regression/expected/runner_baselines/local.expected.json",
        ]

        major = major_change_paths(paths)

        self.assertEqual(
            [
                "docs/examples/sample.dsl",
                "src/main/deploy/bringup_system.json",
                "src/main/java/frc/robot/Robot.java",
                "tools/can_nt/bridge_cli.py",
                "tools/can_topology/can_top_editor.py",
                "tools/common/robot_test_dsl/validator.py",
            ],
            major,
        )

    def test_changelog_is_changed_detects_file(self) -> None:
        self.assertTrue(changelog_is_changed(["CHANGELOG.md", "tools/can_nt/bridge_cli.py"]))
        self.assertFalse(changelog_is_changed(["tools/can_nt/bridge_cli.py"]))

    @patch("tools.can_nt.scripts.changelog_guard.git_changed_paths")
    def test_main_passes_when_no_major_changes(self, changed_mock) -> None:
        changed_mock.return_value = ["tests/regression/expected/runner_baselines/local.expected.json"]

        exit_code = main([])

        self.assertEqual(EXIT_OK, exit_code)

    @patch("tools.can_nt.scripts.changelog_guard.git_changed_paths")
    def test_main_fails_when_major_change_missing_changelog(self, changed_mock) -> None:
        changed_mock.return_value = ["tools/can_nt/bridge_cli.py"]

        exit_code = main([])

        self.assertEqual(EXIT_FAILED, exit_code)

    @patch("tools.can_nt.scripts.changelog_guard.git_changed_paths")
    def test_main_passes_when_major_change_and_changelog_present(self, changed_mock) -> None:
        changed_mock.return_value = ["tools/can_nt/bridge_cli.py", "CHANGELOG.md"]

        exit_code = main([])

        self.assertEqual(EXIT_OK, exit_code)


if __name__ == "__main__":
    unittest.main()
