from __future__ import annotations

import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from tools.can_nt.scripts.lib.regression_framework import (
    EXIT_OK,
    KEY_COMMANDS_TOTAL,
    KEY_EVENT_PATH,
    KEY_EVENT_TYPE,
    KEY_GIT,
    KEY_KNOWN_FAILURES,
    KEY_MATCHES,
    KEY_MISSING_BASELINE,
    KEY_REGRESSIONS,
    KEY_SUITES_STATE,
    EVENT_CHANGED_FAILURE,
    EVENT_FIRST_FAILURE,
    EVENT_RECOVERED,
    HISTORY_EVENTS_DIRECTORY_NAME,
    HISTORY_INDEX_FILE_NAME,
    HISTORY_LATEST_DIRECTORY_NAME,
    MANIFEST_RELATIVE_PATH,
    RegressionCommand,
    RegressionResult,
    STATUS_FIXED,
    STATUS_COMMAND_DRIFT,
    STATUS_MATCH,
    STATUS_MISSING_BASELINE,
    STATUS_REGRESSION,
    SUITE_CHANGELOG,
    SUITE_ALL,
    SUITE_CROSS_SURFACE,
    SUITE_DSL,
    SUITE_LOCAL,
    SUITE_ROBOT_NON_MOTION,
    SUITE_TOPOLOGY,
    _normalized_java_home,
    _argv_matches_portably,
    build_suite_commands,
    compare_results_to_baseline,
    load_manifest,
    refresh_suite_baseline,
    summarize_comparisons,
    summarize_results,
    write_history_for_run,
    write_json_report,
)
from tools.can_nt.scripts.run_regressions import main

LABEL_TEST = "test"
MODE_LOCAL = "local"
RIO_IP = "172.22.11.2"
TEXT_REFRESH = "--refresh-expected"
ARG_JSON_OUT = "--json-out"
ARG_NO_HISTORY = "--no-history"
KEY_ACTIVE_FAILURE = "activeFailure"
KEY_FAILURE_SIGNATURE = "failureSignature"
KEY_LAST_GREEN_COMMIT = "lastGreenCommit"
KEY_LAST_GREEN_PATH = "lastGreenPath"
KEY_LAST_RUN_PATH = "lastRunPath"
KEY_PREVIOUS_GREEN_COMMIT = "previousGreenCommit"


class RunRegressionsTests(unittest.TestCase):
    def test_manifest_exists(self) -> None:
        manifest_path = Path(__file__).resolve().parents[3] / MANIFEST_RELATIVE_PATH
        self.assertTrue(manifest_path.exists())

    def test_build_suite_commands_local_contains_expected_labels(self) -> None:
        commands = build_suite_commands(SUITE_LOCAL)

        labels = [command.label for command in commands]
        self.assertEqual(
            [
                "dsl-unit",
                "cli-unit",
                "java-unit",
                "group-targeting-v1",
                "group-targeting-4m2g3t",
                "topology-editor",
                "cross-surface",
                "changelog-guard",
                "config-api-guard",
                "ui-runtime-rules-lockstep",
            ],
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

    def test_build_suite_commands_cross_surface_contains_regression_script(self) -> None:
        commands = build_suite_commands(SUITE_CROSS_SURFACE)

        self.assertEqual(1, len(commands))
        self.assertEqual("cross-surface", commands[0].label)
        self.assertIn("cross_surface_regression.py", commands[0].argv[1])

    def test_build_suite_commands_changelog_contains_guard_script(self) -> None:
        commands = build_suite_commands(SUITE_CHANGELOG)

        self.assertEqual(3, len(commands))
        self.assertEqual("changelog-guard", commands[0].label)
        self.assertIn("changelog_guard.py", commands[0].argv[1])
        self.assertEqual("config-api-guard", commands[1].label)
        self.assertIn("config_api_guard.py", commands[1].argv[1])
        self.assertEqual("ui-runtime-rules-lockstep", commands[2].label)
        self.assertEqual(
            ("-m", "unittest", "tools.can_nt.tests.test_ui_runtime_rules_lockstep"),
            tuple(commands[2].argv[1:]),
        )

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

    def test_argv_matches_portably_ignores_python_and_repo_locations(self) -> None:
        actual = (
            r"C:\Users\dmona\AppData\Local\Programs\Python\Python313\python.exe",
            r"C:\Users\dmona\swerveBringupMotorTest1-main\tools\can_nt\scripts\topology_editor_regression.py",
        )
        expected = (
            r"D:\Python312\python.exe",
            r"D:\checkout\swerveBringupMotorTest1\tools\can_nt\scripts\topology_editor_regression.py",
        )

        self.assertTrue(_argv_matches_portably(actual, expected))

    def test_argv_matches_portably_ignores_gradlew_checkout_root(self) -> None:
        actual = (r"C:\Users\dmona\swerveBringupMotorTest1-main\gradlew.bat", "test")
        expected = (r"D:\checkout\swerveBringupMotorTest1\gradlew.bat", "test")

        self.assertTrue(_argv_matches_portably(actual, expected))

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

    @patch("tools.can_nt.scripts.run_regressions.write_history_for_run")
    @patch("tools.can_nt.scripts.run_regressions.load_suite_baseline")
    @patch("tools.can_nt.scripts.run_regressions.build_suite_commands")
    @patch("tools.can_nt.scripts.run_regressions.run_commands")
    def test_main_prints_command_drift_reason(
        self,
        run_commands_mock,
        build_suite_commands_mock,
        load_suite_baseline_mock,
        write_history_mock,
    ) -> None:
        command = RegressionCommand(
            label="dsl-unit",
            argv=("python", "-m", "unittest", "tools.can_nt.tests.test_bridge_cli_facades"),
            mode=MODE_LOCAL,
            command_id="dsl-unit",
            features=(),
        )
        build_suite_commands_mock.return_value = [command]
        run_commands_mock.return_value = [
            RegressionResult(
                label="dsl-unit",
                argv=("python", "-m", "unittest", "tools.can_nt.tests.test_bridge_cli_facades"),
                mode=MODE_LOCAL,
                exit_code=0,
                duration_sec=0.1,
                stdout="",
                stderr="",
                command_id="dsl-unit",
                features=(),
            )
        ]
        load_suite_baseline_mock.return_value = {
            "results": [
                {
                    "commandId": "dsl-unit",
                    "argv": ["python", "-m", "unittest", "tools.can_nt.tests.test_robot_test_dsl"],
                    "expectedExitCode": 0,
                }
            ]
        }
        write_history_mock.return_value = {
            "runPath": "latest/dsl.latest.json",
            "event": {"eventType": "none", "eventPath": None},
        }
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["--suite", SUITE_DSL])

        text = output.getvalue()
        self.assertEqual(EXIT_OK, exit_code)
        self.assertIn("STATUS: command_drift", text)
        self.assertIn("STATUS_REASON: command argv differs from baseline", text)
        self.assertIn("EXPECTED_COMMAND: python -m unittest tools.can_nt.tests.test_robot_test_dsl", text)

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
        self.assertIn("no baseline", comparisons[0].status_reason)

    def test_compare_results_to_baseline_explains_command_drift(self) -> None:
        commands = [
            RegressionCommand(
                label="dsl-unit",
                argv=("python", "-m", "unittest", "tools.can_nt.tests.test_bridge_cli_facades"),
                mode=MODE_LOCAL,
                command_id="dsl-unit",
                features=(),
            )
        ]
        results = [
            RegressionResult(
                label="dsl-unit",
                argv=("python", "-m", "unittest", "tools.can_nt.tests.test_bridge_cli_facades"),
                mode=MODE_LOCAL,
                exit_code=0,
                duration_sec=0.1,
                stdout="",
                stderr="",
                command_id="dsl-unit",
                features=(),
            )
        ]
        baseline = {
            "results": [
                {
                    "commandId": "dsl-unit",
                    "argv": ["python", "-m", "unittest", "tools.can_nt.tests.test_robot_test_dsl"],
                    "expectedExitCode": 0,
                }
            ]
        }

        comparisons = compare_results_to_baseline(commands, results, baseline)

        self.assertEqual(STATUS_COMMAND_DRIFT, comparisons[0].status)
        self.assertEqual("command argv differs from baseline", comparisons[0].status_reason)
        self.assertEqual(
            ("python", "-m", "unittest", "tools.can_nt.tests.test_robot_test_dsl"),
            tuple(comparisons[0].expected_argv),
        )
        self.assertEqual(
            ("python", "-m", "unittest", "tools.can_nt.tests.test_bridge_cli_facades"),
            tuple(comparisons[0].actual_argv),
        )

    def test_compare_results_to_baseline_ignores_machine_specific_command_paths(self) -> None:
        commands = [
            RegressionCommand(
                label="topology-editor",
                argv=(
                    r"C:\Users\dmona\AppData\Local\Programs\Python\Python313\python.exe",
                    r"C:\Users\dmona\swerveBringupMotorTest1-main\tools\can_nt\scripts\topology_editor_regression.py",
                ),
                mode=MODE_LOCAL,
                command_id="topology-editor",
                features=(),
            )
        ]
        results = [
            RegressionResult(
                label="topology-editor",
                argv=commands[0].argv,
                mode=MODE_LOCAL,
                exit_code=0,
                duration_sec=0.1,
                stdout="",
                stderr="",
                command_id="topology-editor",
                features=(),
            )
        ]
        baseline = {
            "results": [
                {
                    "commandId": "topology-editor",
                    "argv": [
                        r"D:\Python312\python.exe",
                        r"D:\checkout\swerveBringupMotorTest1\tools\can_nt\scripts\topology_editor_regression.py",
                    ],
                    "expectedExitCode": 0,
                }
            ]
        }

        comparisons = compare_results_to_baseline(commands, results, baseline)

        self.assertEqual(STATUS_MATCH, comparisons[0].status)

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

    @patch("tools.can_nt.scripts.run_regressions.write_history_for_run")
    @patch("tools.can_nt.scripts.run_regressions.run_commands")
    def test_main_skips_history_when_requested(self, run_commands_mock, write_history_mock) -> None:
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

        exit_code = main(["--suite", SUITE_DSL, ARG_NO_HISTORY])

        self.assertEqual(EXIT_OK, exit_code)
        write_history_mock.assert_not_called()

    def test_write_history_for_run_records_first_failure_and_last_green(self) -> None:
        result = RegressionResult(
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
        command = RegressionCommand(label="dsl-unit", argv=("python",), mode=MODE_LOCAL, command_id="dsl-unit", features=())
        comparisons = compare_results_to_baseline([command], [result], {"results": [{"commandId": "dsl-unit", "argv": ["python"], "expectedExitCode": 0}]})
        metadata = {KEY_GIT: {"commit": "abc123", "branch": "main", "dirty": False, "changedFiles": []}}
        with tempfile.TemporaryDirectory() as temp_dir:
            history_root = Path(temp_dir)
            with patch("tools.can_nt.scripts.lib.regression_framework.history_root_path", return_value=history_root), patch(
                "tools.can_nt.scripts.lib.regression_framework._utc_timestamp", return_value="2026-05-08T16:00:00Z"
            ):
                history = write_history_for_run(
                    suite_name=SUITE_DSL,
                    results=[result],
                    summary={"passed": 0, "failed": 1, "total": 1},
                    comparisons=comparisons,
                    baseline_path=history_root / "dsl.expected.json",
                    metadata=metadata,
                )
            index = json.loads((history_root / HISTORY_INDEX_FILE_NAME).read_text(encoding="utf-8"))

        self.assertEqual(EVENT_FIRST_FAILURE, history["event"][KEY_EVENT_TYPE])
        self.assertTrue(history["event"][KEY_EVENT_PATH])
        suite_state = index[KEY_SUITES_STATE][SUITE_DSL]
        self.assertEqual(["dsl-unit:1:regression"], suite_state[KEY_ACTIVE_FAILURE][KEY_FAILURE_SIGNATURE])
        self.assertIsNone(suite_state[KEY_ACTIVE_FAILURE][KEY_PREVIOUS_GREEN_COMMIT])

    def test_write_history_for_run_uses_previous_green_and_records_recovery(self) -> None:
        command = RegressionCommand(label="dsl-unit", argv=("python",), mode=MODE_LOCAL, command_id="dsl-unit", features=())
        fail_result = RegressionResult(
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
        pass_result = RegressionResult(
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
        fail_comparisons = compare_results_to_baseline([command], [fail_result], {"results": [{"commandId": "dsl-unit", "argv": ["python"], "expectedExitCode": 0}]})
        pass_comparisons = compare_results_to_baseline([command], [pass_result], {"results": [{"commandId": "dsl-unit", "argv": ["python"], "expectedExitCode": 0}]})
        with tempfile.TemporaryDirectory() as temp_dir:
            history_root = Path(temp_dir)
            with patch("tools.can_nt.scripts.lib.regression_framework.history_root_path", return_value=history_root), patch(
                "tools.can_nt.scripts.lib.regression_framework._utc_timestamp",
                side_effect=[
                    "2026-05-08T15:00:00Z",
                    "2026-05-08T15:00:00Z",
                    "2026-05-08T15:00:00Z",
                    "2026-05-08T16:00:00Z",
                    "2026-05-08T16:00:00Z",
                ],
            ):
                write_history_for_run(
                    suite_name=SUITE_DSL,
                    results=[pass_result],
                    summary={"passed": 1, "failed": 0, "total": 1},
                    comparisons=pass_comparisons,
                    baseline_path=history_root / "dsl.expected.json",
                    metadata={KEY_GIT: {"commit": "good1", "branch": "main", "dirty": False, "changedFiles": []}},
                )
                failure_history = write_history_for_run(
                    suite_name=SUITE_DSL,
                    results=[fail_result],
                    summary={"passed": 0, "failed": 1, "total": 1},
                    comparisons=fail_comparisons,
                    baseline_path=history_root / "dsl.expected.json",
                    metadata={KEY_GIT: {"commit": "bad1", "branch": "main", "dirty": False, "changedFiles": []}},
                )
            with patch("tools.can_nt.scripts.lib.regression_framework.history_root_path", return_value=history_root), patch(
                "tools.can_nt.scripts.lib.regression_framework._utc_timestamp", return_value="2026-05-08T17:00:00Z"
            ):
                recovery_history = write_history_for_run(
                    suite_name=SUITE_DSL,
                    results=[pass_result],
                    summary={"passed": 1, "failed": 0, "total": 1},
                    comparisons=pass_comparisons,
                    baseline_path=history_root / "dsl.expected.json",
                    metadata={KEY_GIT: {"commit": "good2", "branch": "main", "dirty": False, "changedFiles": []}},
                )
            index = json.loads((history_root / HISTORY_INDEX_FILE_NAME).read_text(encoding="utf-8"))
            last_green_exists = (history_root / HISTORY_LATEST_DIRECTORY_NAME / f"{SUITE_DSL}.last_green.json").exists()

        self.assertEqual(EVENT_FIRST_FAILURE, failure_history["event"][KEY_EVENT_TYPE])
        suite_state = index[KEY_SUITES_STATE][SUITE_DSL]
        self.assertEqual("good2", suite_state[KEY_LAST_GREEN_COMMIT])
        self.assertNotIn(KEY_ACTIVE_FAILURE, suite_state)
        self.assertEqual(EVENT_RECOVERED, recovery_history["event"][KEY_EVENT_TYPE])
        self.assertTrue(last_green_exists)

    def test_write_history_for_run_does_not_duplicate_repeat_failure(self) -> None:
        command = RegressionCommand(label="dsl-unit", argv=("python",), mode=MODE_LOCAL, command_id="dsl-unit", features=())
        fail_result = RegressionResult(
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
        fail_comparisons = compare_results_to_baseline([command], [fail_result], {"results": [{"commandId": "dsl-unit", "argv": ["python"], "expectedExitCode": 0}]})
        with tempfile.TemporaryDirectory() as temp_dir:
            history_root = Path(temp_dir)
            with patch("tools.can_nt.scripts.lib.regression_framework.history_root_path", return_value=history_root), patch(
                "tools.can_nt.scripts.lib.regression_framework._utc_timestamp",
                side_effect=[
                    "2026-05-08T18:00:00Z",
                    "2026-05-08T18:00:00Z",
                    "2026-05-08T19:00:00Z",
                    "2026-05-08T19:00:00Z",
                ],
            ):
                first_history = write_history_for_run(
                    suite_name=SUITE_DSL,
                    results=[fail_result],
                    summary={"passed": 0, "failed": 1, "total": 1},
                    comparisons=fail_comparisons,
                    baseline_path=history_root / "dsl.expected.json",
                    metadata={KEY_GIT: {"commit": "bad1", "branch": "main", "dirty": False, "changedFiles": []}},
                )
                repeat_history = write_history_for_run(
                    suite_name=SUITE_DSL,
                    results=[fail_result],
                    summary={"passed": 0, "failed": 1, "total": 1},
                    comparisons=fail_comparisons,
                    baseline_path=history_root / "dsl.expected.json",
                    metadata={KEY_GIT: {"commit": "bad2", "branch": "main", "dirty": False, "changedFiles": []}},
                )
            event_files = list((history_root / HISTORY_EVENTS_DIRECTORY_NAME / SUITE_DSL).glob("*.json"))

        self.assertEqual(EVENT_FIRST_FAILURE, first_history["event"][KEY_EVENT_TYPE])
        self.assertEqual("none", repeat_history["event"][KEY_EVENT_TYPE])
        self.assertEqual(1, len(event_files))


if __name__ == "__main__":
    unittest.main()
