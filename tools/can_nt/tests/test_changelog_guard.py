from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.can_nt.scripts.changelog_guard import (
    EXIT_FAILED,
    EXIT_OK,
    CHANGELOG_HEADER,
    CHANGELOG_INTRO,
    build_auto_entry_text,
    changelog_is_changed,
    git_changed_paths,
    insert_latest_entry,
    main,
    major_change_paths,
    write_auto_changelog_entry,
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
    @patch("tools.can_nt.scripts.changelog_guard.write_auto_changelog_entry")
    def test_main_auto_updates_when_major_change_missing_changelog(self, write_mock, changed_mock) -> None:
        changed_mock.return_value = ["tools/can_nt/bridge_cli.py"]
        write_mock.return_value = Path("CHANGELOG.md")

        exit_code = main([])

        self.assertEqual(EXIT_OK, exit_code)
        write_mock.assert_called_once_with(["tools/can_nt/bridge_cli.py"])

    @patch("tools.can_nt.scripts.changelog_guard.git_changed_paths")
    def test_main_passes_when_major_change_and_changelog_present(self, changed_mock) -> None:
        changed_mock.return_value = ["tools/can_nt/bridge_cli.py", "CHANGELOG.md"]

        exit_code = main([])

        self.assertEqual(EXIT_OK, exit_code)

    @patch("tools.can_nt.scripts.changelog_guard.git_changed_paths")
    def test_main_fails_in_check_only_mode_when_major_change_missing_changelog(self, changed_mock) -> None:
        changed_mock.return_value = ["tools/can_nt/bridge_cli.py"]

        exit_code = main(["--check-only"])

        self.assertEqual(EXIT_FAILED, exit_code)

    def test_insert_latest_entry_adds_preamble_when_file_is_empty(self) -> None:
        entry_text = build_auto_entry_text(
            date_text="2026-08-25",
            major_paths=["tools/can_nt/bridge_cli.py"],
            newline="\n",
        )

        updated = insert_latest_entry(str(), entry_text, "\n")

        self.assertIn(CHANGELOG_HEADER, updated)
        self.assertIn(CHANGELOG_INTRO, updated)
        self.assertIn("## 2026-08-25", updated)
        self.assertIn("Touched major-change file: `tools/can_nt/bridge_cli.py`", updated)

    def test_write_auto_changelog_entry_inserts_new_latest_section(self) -> None:
        initial = "\n".join(
            [
                "# Changelog",
                "",
                "All notable user-facing changes are documented in this file.",
                "",
                "## 2026-08-17",
                "",
                "### Fixed - 2026-08-17",
                "",
                "- Existing entry.",
                "",
            ]
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            changelog_path = Path(temp_dir) / "CHANGELOG.md"
            changelog_path.write_text(initial, encoding="utf-8")

            write_auto_changelog_entry(
                major_paths=["src/main/java/frc/robot/Robot.java", "tools/can_nt/bridge_cli.py"],
                changelog_path=changelog_path,
                date_text="2026-08-25",
            )

            updated = changelog_path.read_text(encoding="utf-8")
            self.assertTrue(updated.index("## 2026-08-25") < updated.index("## 2026-08-17"))
            self.assertIn("### Changed - 2026-08-25", updated)
            self.assertIn("Touched major-change file: `src/main/java/frc/robot/Robot.java`", updated)
            self.assertIn("Touched major-change file: `tools/can_nt/bridge_cli.py`", updated)


if __name__ == "__main__":
    unittest.main()
