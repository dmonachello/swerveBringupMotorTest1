from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.can_nt.scripts.lib.regression_framework import (
    EXIT_OK,
    KEY_COMMANDS_TOTAL,
    KEY_KNOWN_FAILURES,
    KEY_MATCHES,
    KEY_MISSING_BASELINE,
    KEY_REGRESSIONS,
    MANIFEST_RELATIVE_PATH,
    RegressionCommand,
    RegressionResult,
    STATUS_FIXED,
    STATUS_MATCH,
    STATUS_MISSING_BASELINE,
    STATUS_REGRESSION,
    SUITE_CHANGELOG,
    SUITE_ALL,
    SUITE_DSL,
    SUITE_LOCAL,
    SUITE_ROBOT_NON_MOTION,
    SUITE_TOPOLOGY,
    _normalized_java_home,
    build_suite_commands,
    compare_results_to_baseline,
    load_manifest,
    refresh_suite_baseline,
    summarize_comparisons,
    summarize_results,
    write_json_report,
)
from tools.can_nt.scripts.run_regressions import main

LABEL_TEST = "test"
MODE_LOCAL = "local"
RIO_IP = "172.22.11.2"
TEXT_REFRESH = "--refresh-expected"
ARG_JSON_OUT = "--json-out"


class RunRegressionsTests(unittest.TestCase):
    def test_manifest_exists(self) -> None:
        manifest_path = Path(__file__).resolve().parents[3] / MANIFEST_RELATIVE_PATH
        self.assertTrue(manifest_path.exists())

    def test_build_suite_commands_local_contains_expected_labels(self) -> None:
        commands = build_suite_commands(SUITE_LOCAL)

        labels = [command.label for command in commands]
        self.assertEqual(
            ["dsl-unit", "cli-unit", "java-unit", "group-targeting-v1", "group-targeting-4m2g3t", "topology-editor", "changelog-guard"],
            labels,
        )

    def test_build_suite_commands_dsl_uses_targeted_java_test(self) -> None:
        commands = build_suite_commands(SUITE_DSL)

        self.assertEqual(2, len(commands))
        self.assertIn("frc.robot.DslBringupTestTest", commands[1].argv)

    def test_build_suite_commands_topology_contains_regression_script(self) -> None:
        commands = build_suite_commands(SUITE_TOPOLOGY)

        self.assertEqual(1, len(commands))
        self.assertEqual("topology-editor", commands[0].label)
        self.assertIn("topology_editor_regression.py", commands[0].argv[1])

    def test_build_suite_commands_changelog_contains_guard_script(self) -> None:
        commands = build_suite_commands(SUITE_CHANGELOG)

        self.assertEqual(1, len(commands))
        self.assertEqual("changelog-guard", commands[0].label)
        self.assertIn("changelog_guard.py", commands[0].argv[1])

    def test_build_suite_commands_robot_suite_requires_rio(self) -> None:
        with self.assertRaises(ValueError):
            build_suite_commands(SUITE_ROBOT_NON_MOTION)

    def test_build_suite_commands_all_excludes_robot_without_flag(self) -> None:
        commands = build_suite_commands(SUITE_ALL, include_robot=False)

        labels = [command.label for command in commands]
        self.assertNotIn("robot-non-motion", labels)

    def test_build_suite_commands_all_includes_robot_with_flag(self) -> None:
        commands = build_suite_commands(SUITE_ALL, include_robot=True, rio=RIO_IP)

        labels = [command.label for command in commands]
        self.assertIn("robot-non-motion", labels)

    def test_summarize_results_counts_failures(self) -> None:
        results = [
            RegressionResult(
                label=LABEL_TEST,
                argv=("python",),
                mode=MODE_LOCAL,
                exit_code=EXIT_OK,
                duration_sec=0.1,
                stdout="",
                stderr="",
                command_id="one",
                features=(),
            ),
            RegressionResult(
                label=LABEL_TEST,
                argv=("python",),
                mode=MODE_LOCAL,
                exit_code=1,
                duration_sec=0.2,
                stdout="",
                stderr="",
                command_id="two",
                features=(),
            ),
        ]

        summary = summarize_results(results)

        self.assertEqual({"passed": 1, "failed": 1, "total": 2}, summary)

    def test_normalized_java_home_strips_bin_suffix(self) -> None:
        value = r"C:\Users\Public\wpilib\2024\jdk\bin"

        normalized = _normalized_java_home(value)

        self.assertEqual(r"C:\Users\Public\wpilib\2024\jdk", normalized)

    @patch("tools.can_nt.scripts.run_regressions.run_commands")
    def test_main_refresh_expected_returns_success(self, run_commands_mock) -> None:
        run_commands_mock.return_value = [
            RegressionResult(
                label="dsl-unit",
                argv=("python", "-m", "unittest"),
                mode=MODE_LOCAL,
                exit_code=EXIT_OK,
                duration_sec=0.1,
                stdout="ok",
                stderr="",
                command_id="dsl-unit",
                features=(),
            )
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            baseline_dir = Path(temp_dir)
            with patch("tools.can_nt.scripts.lib.regression_framework.suite_baseline_path", return_value=baseline_dir / "dsl.expected.json"):
                exit_code = main([TEXT_REFRESH, "--suite", SUITE_DSL])

        self.assertEqual(EXIT_OK, exit_code)
        run_commands_mock.assert_called_once()

    @patch("tools.can_nt.scripts.run_regressions.run_commands")
    def test_main_runs_and_reports_success(self, run_commands_mock) -> None:
        run_commands_mock.return_value = [
            RegressionResult(
                label="dsl-unit",
                argv=("python", "-m", "unittest"),
                mode=MODE_LOCAL,
                exit_code=EXIT_OK,
                duration_sec=0.1,
                stdout="ok",
                stderr="",
                command_id="dsl-unit",
                features=(),
            )
        ]

        exit_code = main(["--suite", SUITE_DSL])

        self.assertEqual(EXIT_OK, exit_code)
        run_commands_mock.assert_called_once()

    def test_execute_result_preserves_command_metadata(self) -> None:
        captured = []

        def fake_runner(command: RegressionCommand, _workdir):
            captured.append((command.label, command.mode, tuple(command.argv), command.command_id))
            return RegressionResult(
                label=command.label,
                argv=command.argv,
                mode=command.mode,
                exit_code=EXIT_OK,
                duration_sec=0.1,
                stdout="",
                stderr="",
                command_id=command.command_id,
                features=tuple(command.features),
            )

        commands = build_suite_commands(SUITE_DSL)
        from tools.can_nt.scripts.lib.regression_framework import run_commands

        results = run_commands(commands, runner=fake_runner)

        self.assertEqual(
            [
                ("dsl-unit", MODE_LOCAL, tuple(commands[0].argv), "dsl-unit"),
                ("java-unit", MODE_LOCAL, tuple(commands[1].argv), "java-dsl-unit"),
            ],
            captured,
        )
        self.assertEqual("dsl-unit", results[0].label)
        self.assertEqual("java-unit", results[1].label)
        self.assertTrue(commands[0].features)

    def test_compare_results_to_baseline_classifies_regression(self) -> None:
        commands = [RegressionCommand(label="dsl-unit", argv=("python",), mode=MODE_LOCAL, command_id="dsl-unit", features=())]
        results = [
            RegressionResult(
                label="dsl-unit",
                argv=("python",),
                mode=MODE_LOCAL,
                exit_code=1,
                duration_sec=0.1,
                stdout="",
                stderr="",
                command_id="dsl-unit",
                features=(),
            )
        ]
        baseline = {"results": [{"commandId": "dsl-unit", "argv": ["python"], "expectedExitCode": 0}]}

        comparisons = compare_results_to_baseline(commands, results, baseline)

        self.assertEqual(STATUS_REGRESSION, comparisons[0].status)

    def test_compare_results_to_baseline_classifies_fixed(self) -> None:
        commands = [RegressionCommand(label="dsl-unit", argv=("python",), mode=MODE_LOCAL, command_id="dsl-unit", features=())]
        results = [
            RegressionResult(
                label="dsl-unit",
                argv=("python",),
                mode=MODE_LOCAL,
                exit_code=0,
                duration_sec=0.1,
                stdout="",
                stderr="",
                command_id="dsl-unit",
                features=(),
            )
        ]
        baseline = {"results": [{"commandId": "dsl-unit", "argv": ["python"], "expectedExitCode": 1}]}

        comparisons = compare_results_to_baseline(commands, results, baseline)

        self.assertEqual(STATUS_FIXED, comparisons[0].status)

    def test_compare_results_to_baseline_reports_missing(self) -> None:
        commands = [RegressionCommand(label="dsl-unit", argv=("python",), mode=MODE_LOCAL, command_id="dsl-unit", features=())]
        results = [
            RegressionResult(
                label="dsl-unit",
                argv=("python",),
                mode=MODE_LOCAL,
                exit_code=0,
                duration_sec=0.1,
                stdout="",
                stderr="",
                command_id="dsl-unit",
                features=(),
            )
        ]

        comparisons = compare_results_to_baseline(commands, results, None)

        self.assertEqual(STATUS_MISSING_BASELINE, comparisons[0].status)

    def test_summarize_comparisons_counts_statuses(self) -> None:
        commands = [RegressionCommand(label="dsl-unit", argv=("python",), mode=MODE_LOCAL, command_id="dsl-unit", features=())]
        results = [
            RegressionResult(
                label="dsl-unit",
                argv=("python",),
                mode=MODE_LOCAL,
                exit_code=0,
                duration_sec=0.1,
                stdout="",
                stderr="",
                command_id="dsl-unit",
                features=(),
            )
        ]
        comparisons = compare_results_to_baseline(commands, results, {"results": [{"commandId": "dsl-unit", "argv": ["python"], "expectedExitCode": 0}]})

        summary = summarize_comparisons(comparisons)

        self.assertEqual(1, summary[KEY_COMMANDS_TOTAL])
        self.assertEqual(1, summary[KEY_MATCHES])
        self.assertEqual(0, summary[KEY_REGRESSIONS])
        self.assertEqual(0, summary[KEY_KNOWN_FAILURES])
        self.assertEqual(0, summary[KEY_MISSING_BASELINE])

    def test_refresh_suite_baseline_writes_expected_payload(self) -> None:
        commands = [RegressionCommand(label="dsl-unit", argv=("python",), mode=MODE_LOCAL, command_id="dsl-unit", features=())]
        results = [
            RegressionResult(
                label="dsl-unit",
                argv=("python",),
                mode=MODE_LOCAL,
                exit_code=0,
                duration_sec=0.1,
                stdout="",
                stderr="",
                command_id="dsl-unit",
                features=(),
            )
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            baseline_path = Path(temp_dir) / "dsl.expected.json"
            with patch("tools.can_nt.scripts.lib.regression_framework.suite_baseline_path", return_value=baseline_path):
                written_path = refresh_suite_baseline(SUITE_DSL, commands, results)
            payload = json.loads(baseline_path.read_text(encoding="utf-8"))

        self.assertEqual(baseline_path, written_path)
        self.assertEqual(SUITE_DSL, payload["suite"])
        self.assertEqual(0, payload["results"][0]["expectedExitCode"])

    def test_write_json_report_emits_machine_readable_output(self) -> None:
        results = [
            RegressionResult(
                label="dsl-unit",
                argv=("python",),
                mode=MODE_LOCAL,
                exit_code=0,
                duration_sec=0.1,
                stdout="",
                stderr="",
                command_id="dsl-unit",
                features=(),
            )
        ]
        comparisons = [
            compare_results_to_baseline(
                [RegressionCommand(label="dsl-unit", argv=("python",), mode=MODE_LOCAL, command_id="dsl-unit", features=())],
                results,
                {"results": [{"commandId": "dsl-unit", "argv": ["python"], "expectedExitCode": 0}]},
            )[0]
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "report.json"
            write_json_report(
                report_path,
                suite_name=SUITE_DSL,
                results=results,
                summary={"passed": 1, "failed": 0, "total": 1},
                comparisons=comparisons,
                baseline_path=Path(temp_dir) / "dsl.expected.json",
            )
            payload = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(SUITE_DSL, payload["suite"])
        self.assertEqual(STATUS_MATCH, payload["results"][0]["status"]["status"])

    @patch("tools.can_nt.scripts.run_regressions.run_commands")
    def test_main_writes_json_report(self, run_commands_mock) -> None:
        run_commands_mock.return_value = [
            RegressionResult(
                label="dsl-unit",
                argv=("python",),
                mode=MODE_LOCAL,
                exit_code=0,
                duration_sec=0.1,
                stdout="",
                stderr="",
                command_id="dsl-unit",
                features=(),
            )
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "report.json"
            exit_code = main(["--suite", SUITE_DSL, ARG_JSON_OUT, str(report_path)])
            payload = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(EXIT_OK, exit_code)
        self.assertEqual(SUITE_DSL, payload["suite"])


if __name__ == "__main__":
    unittest.main()
