from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.can_nt.scripts.regression_coverage_guard import find_coverage_issues


SCHEMA_VERSION = 1
KEY_SCHEMA_VERSION = "schemaVersion"
KEY_COMMANDS = "commands"
KEY_SUITES = "suites"
KEY_ARGV = "argv"
KEY_EXCLUSIONS = "exclusions"
KEY_PATH = "path"
KEY_REASON = "reason"
TOKEN_PYTHON = "{python}"
TOKEN_REPO = "{repo}"
SUITE_LOCAL = "local"
COMMAND_DISCOVERY = "python-unit-all"
COMMAND_REGRESSION = "sample-regression"
COMMAND_JAVA = "java-unit"
DISCOVERY_ROOT = "tools/sample/tests"
TEST_PATH = "tools/sample/tests/test_new_behavior.py"
UNREGISTERED_TEST_PATH = "tools/other/tests/test_unregistered.py"
NONMATCHING_TEST_PATH = "tools/sample/tests/new_behavior_test.py"
REGRESSION_PATH = "tools/sample/scripts/sample_regression.py"
JAVA_TEST_PATH = "src/test/java/frc/robot/SampleTest.java"
EXCLUSION_REASON = "Experimental tests have a separately approved execution gate."


def _manifest(commands: dict[str, dict[str, object]], command_ids: list[str]) -> dict[str, object]:
    return {
        KEY_SCHEMA_VERSION: SCHEMA_VERSION,
        KEY_COMMANDS: commands,
        KEY_SUITES: {SUITE_LOCAL: command_ids},
    }


def _discovery_command(root: str = DISCOVERY_ROOT) -> dict[str, object]:
    return {
        KEY_ARGV: [
            TOKEN_PYTHON,
            "-m",
            "unittest",
            "discover",
            "-s",
            root,
            "-p",
            "test_*.py",
        ]
    }


class RegressionCoverageGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _write(self, relative_path: str) -> None:
        path = self.repo_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

    def test_discovery_command_covers_new_test_file(self) -> None:
        self._write(TEST_PATH)
        manifest = _manifest(
            {COMMAND_DISCOVERY: _discovery_command()},
            [COMMAND_DISCOVERY],
        )

        issues = find_coverage_issues(self.repo_root, manifest, {KEY_EXCLUSIONS: []})

        self.assertEqual([], issues)

    def test_new_test_directory_fails_until_registered(self) -> None:
        self._write(UNREGISTERED_TEST_PATH)
        manifest = _manifest(
            {COMMAND_DISCOVERY: _discovery_command()},
            [COMMAND_DISCOVERY],
        )

        issues = find_coverage_issues(self.repo_root, manifest, {KEY_EXCLUSIONS: []})

        self.assertTrue(any(UNREGISTERED_TEST_PATH in issue for issue in issues))

    def test_discovery_pattern_must_match_test_filename(self) -> None:
        self._write(NONMATCHING_TEST_PATH)
        manifest = _manifest(
            {COMMAND_DISCOVERY: _discovery_command()},
            [COMMAND_DISCOVERY],
        )

        issues = find_coverage_issues(self.repo_root, manifest, {KEY_EXCLUSIONS: []})

        self.assertTrue(any(NONMATCHING_TEST_PATH in issue for issue in issues))

    def test_unassigned_command_does_not_count_as_coverage(self) -> None:
        self._write(TEST_PATH)
        manifest = _manifest(
            {COMMAND_DISCOVERY: _discovery_command()},
            [],
        )

        issues = find_coverage_issues(self.repo_root, manifest, {KEY_EXCLUSIONS: []})

        self.assertTrue(any(TEST_PATH in issue for issue in issues))

    def test_registered_standalone_regression_is_covered(self) -> None:
        self._write(REGRESSION_PATH)
        manifest = _manifest(
            {
                COMMAND_REGRESSION: {
                    KEY_ARGV: [TOKEN_PYTHON, f"{TOKEN_REPO}/{REGRESSION_PATH}"]
                }
            },
            [COMMAND_REGRESSION],
        )

        issues = find_coverage_issues(self.repo_root, manifest, {KEY_EXCLUSIONS: []})

        self.assertEqual([], issues)

    def test_exclusion_requires_a_reason(self) -> None:
        self._write(UNREGISTERED_TEST_PATH)
        manifest = _manifest({}, [])
        exclusions = {
            KEY_EXCLUSIONS: [{KEY_PATH: "tools/other/tests", KEY_REASON: ""}]
        }

        issues = find_coverage_issues(self.repo_root, manifest, exclusions)

        self.assertTrue(any("non-empty reason" in issue for issue in issues))
        self.assertTrue(any(UNREGISTERED_TEST_PATH in issue for issue in issues))

    def test_recursive_exclusion_with_reason_is_explicit_coverage(self) -> None:
        self._write(UNREGISTERED_TEST_PATH)
        manifest = _manifest({}, [])
        exclusions = {
            KEY_EXCLUSIONS: [
                {KEY_PATH: "tools/other/tests", KEY_REASON: EXCLUSION_REASON}
            ]
        }

        issues = find_coverage_issues(self.repo_root, manifest, exclusions)

        self.assertEqual([], issues)

    def test_java_tests_require_assigned_gradle_test_command(self) -> None:
        self._write(JAVA_TEST_PATH)
        manifest = _manifest({}, [])

        issues = find_coverage_issues(self.repo_root, manifest, {KEY_EXCLUSIONS: []})

        self.assertTrue(any(JAVA_TEST_PATH in issue for issue in issues))

    def test_assigned_gradle_command_covers_java_tests(self) -> None:
        self._write(JAVA_TEST_PATH)
        manifest = _manifest(
            {COMMAND_JAVA: {KEY_ARGV: ["{gradlew}", "test"]}},
            [COMMAND_JAVA],
        )

        issues = find_coverage_issues(self.repo_root, manifest, {KEY_EXCLUSIONS: []})

        self.assertEqual([], issues)


if __name__ == "__main__":
    unittest.main()
