from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.can_nt.bridge_cli import BridgeCli, CliMode, MODE_CONFIG
from tools.can_nt.bridge_session import BridgeEvent
from tools.can_nt.status import SS__NORMAL, StatusResult
from tools.common.robot_test_dsl import (
    RobotTestDslEntry,
    RobotTestDslStore,
    compile_source as compile_robot_test_dsl_source,
    store_to_payload as robot_test_dsl_store_to_payload,
)


class _FakeSession:
    def __init__(self, connected: bool = False) -> None:
        self.connected = connected
        self.sent_commands: list[tuple[str, dict | None]] = []

    def is_connected(self) -> bool:
        return self.connected

    def send_command(self, _name: str, _args: dict | None = None) -> int:
        self.sent_commands.append((_name, _args))
        return 1

    def ensure_handshake(self) -> bool:
        return True

    def last_handshake_error(self) -> str:
        return ""


class BridgeCliRobotTestDslCliTests(unittest.TestCase):
    def _build_cli(self, connected: bool = False, include_controller: bool = False) -> BridgeCli:
        cli = BridgeCli(_FakeSession(connected=connected), batch=True)
        cli._modes = [CliMode(MODE_CONFIG)]
        cli._local_root_payload = {
            "schema_version": 5,
            "default_profile": "dsl_demo_050426",
            "profiles": {
                "dsl_demo_050426": {
                    "devices": ["FALCON 9", "SPARKMAX/NEO 25", "lmtSw0"],
                    "dslTestSet": "default",
                }
            },
            "devices": [
                {
                    "label": "FALCON 9",
                    "manufacturer": 4,
                    "deviceType": 2,
                    "id": 9,
                    "model": "FALCON 500",
                    "type": "motor",
                    "deviceInterface": "CAN",
                },
                {
                    "label": "SPARKMAX/NEO 25",
                    "manufacturer": 5,
                    "deviceType": 2,
                    "id": 25,
                    "model": "NEO",
                    "type": "motor",
                    "deviceInterface": "CAN",
                },
                {
                    "label": "lmtSw0",
                    "manufacturer": 1,
                    "deviceType": 1,
                    "id": 0,
                    "model": "DIO Limit Switch",
                    "type": "limitSwitch",
                    "deviceInterface": "DIO",
                },
                {
                    "label": "controller0",
                    "manufacturer": 1,
                    "deviceType": 1,
                    "id": 0,
                    "model": "Xbox Controller",
                    "type": "xboxController",
                    "deviceInterface": "USB",
                }
            ],
        }
        if include_controller:
            cli._local_root_payload["profiles"]["dsl_demo_050426"]["devices"].append("controller0")
        return cli

    def test_import_validate_and_show_normalized(self) -> None:
        cli = self._build_cli(include_controller=True)
        source = (
            'test "spin_up_motor1"\n'
            'device "FALCON 9"\n\n'
            'device "controller0"\n\n'
            "main:\n"
            '    set "FALCON 9".output = controller0.leftY scaled 0.25 default 0.0\n'
            "    until timer.elapsed >= 3.0\n"
            '    require "FALCON 9".velocity > 1000\n'
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "spin_up_motor1.dsl"
            source_path.write_text(source, encoding="utf-8")

            result = cli._dsl_test_command(["test", "import", "spin_up_motor1", str(source_path), "set", "default"])
            self.assertEqual(result.code, SS__NORMAL)

            entry = cli._local_root_payload["dslTests"]["testsByName"]["spin_up_motor1"]
            self.assertEqual(entry["normalized"]["name"], "spin_up_motor1")
            self.assertEqual(entry["normalized"]["devices"][1]["name"], "controller0")
            self.assertEqual(entry["normalized"]["main"]["sets"][0]["source"]["signal"], "leftY")

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                show_result = cli._dsl_show_command(["show", "test", "spin_up_motor1", "normalized"])
            self.assertEqual(show_result.code, SS__NORMAL)
            self.assertIn('"name": "spin_up_motor1"', output.getvalue())

    def test_validate_reports_unknown_profile(self) -> None:
        cli = self._build_cli()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = cli._dsl_validate_store(cli._dsl_store(), "missing_profile")
            cli._dsl_print_validation(result, False, False)
        self.assertFalse(result.ok())
        self.assertIn("unknown profile: missing_profile", output.getvalue())

    def test_import_accepts_controller_signal_device(self) -> None:
        cli = self._build_cli(include_controller=True)
        source = (
            'test "controller_confirm"\n'
            'device "controller0"\n\n'
            "main:\n"
            "    success controller0.A\n"
            "    abort timer.elapsed >= 5.0\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "controller_confirm.dsl"
            source_path.write_text(source, encoding="utf-8")

            result = cli._dsl_test_command(["test", "import", "controller_confirm", str(source_path)])

            self.assertEqual(result.code, SS__NORMAL)
            entry = cli._local_root_payload["dslTests"]["testsByName"]["controller_confirm"]
            self.assertEqual(entry["normalized"]["devices"][0]["name"], "controller0")
            self.assertEqual(
                cli._local_root_payload["profiles"]["dsl_demo_050426"]["dslTestSet"],
                "default",
            )

    def test_import_without_existing_profile_set_creates_profile_owned_runnable_set(self) -> None:
        cli = self._build_cli(include_controller=True)
        cli._local_root_payload["profiles"]["dsl_demo_050426"].pop("dslTestSet", None)
        source = (
            'test "controller_confirm"\n'
            'device "controller0"\n\n'
            "main:\n"
            "    success controller0.A\n"
            "    abort timer.elapsed >= 5.0\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "controller_confirm.dsl"
            source_path.write_text(source, encoding="utf-8")

            result = cli._dsl_test_command(["test", "import", "controller_confirm", str(source_path)])

        self.assertEqual(result.code, SS__NORMAL)
        self.assertEqual(
            cli._local_root_payload["profiles"]["dsl_demo_050426"]["dslTestSet"],
            "dsl_demo_050426",
        )
        self.assertEqual(
            cli._local_root_payload["dslTests"]["testSets"]["dsl_demo_050426"],
            ["controller_confirm"],
        )

    def test_new_creates_minimal_profile_owned_test(self) -> None:
        cli = self._build_cli(include_controller=True)
        cli._local_root_payload["profiles"]["dsl_demo_050426"].pop("dslTestSet", None)

        result = cli._dsl_test_command(["test", "new", "fresh_profile_test"])

        self.assertEqual(result.code, SS__NORMAL)
        self.assertEqual(
            cli._local_root_payload["profiles"]["dsl_demo_050426"]["dslTestSet"],
            "dsl_demo_050426",
        )
        self.assertEqual(
            cli._local_root_payload["dslTests"]["testSets"]["dsl_demo_050426"],
            ["fresh_profile_test"],
        )
        entry = cli._local_root_payload["dslTests"]["testsByName"]["fresh_profile_test"]
        self.assertIn('test "fresh_profile_test"', entry["source"])

    def test_import_accepts_signal_driven_set(self) -> None:
        cli = self._build_cli(include_controller=True)
        source = (
            'test "controller_drive"\n'
            'device "FALCON 9"\n'
            'device "controller0"\n\n'
            "init:\n"
            '    set "FALCON 9".output = controller0.leftY deadband 0.05 scaled 0.1 default 0.0\n'
            "main:\n"
            '    set "FALCON 9".output = controller0.leftY deadband 0.08 scaled 0.25 default 0.0\n'
            '    abort "FALCON 9".current > 35\n'
            '    abort controller0.B\n'
            '    require controller0.A\n'
            "    until timer.elapsed >= 3.0\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "controller_drive.dsl"
            source_path.write_text(source, encoding="utf-8")

            result = cli._dsl_test_command(["test", "import", "controller_drive", str(source_path)])

            self.assertEqual(result.code, SS__NORMAL)
            entry = cli._local_root_payload["dslTests"]["testsByName"]["controller_drive"]
            init_statement = entry["normalized"]["init"]["sets"][0]
            main_statement = entry["normalized"]["main"]["sets"][0]
            self.assertEqual(init_statement["deadband"], 0.05)
            self.assertEqual(init_statement["scale"], 0.1)
            self.assertEqual(main_statement["target"]["signal"], "output")
            self.assertEqual(main_statement["source"]["device"], "controller0")
            self.assertEqual(main_statement["source"]["signal"], "leftY")
            self.assertEqual(main_statement["deadband"], 0.08)
            self.assertEqual(main_statement["scale"], 0.25)
            self.assertEqual(main_statement["defaultLiteral"]["value"], 0.0)

    def test_import_accepts_qualified_motor_signal_names(self) -> None:
        cli = self._build_cli(include_controller=True)
        source = (
            'test "qualified_signals"\n'
            'device "FALCON 9"\n'
            'device "controller0"\n\n'
            "main:\n"
            '    set "FALCON 9".output_percent_cmd = controller0.leftY deadband 0.08 scaled 0.25 default 0.0\n'
            '    abort "FALCON 9".current_actual > 35\n'
            '    require "FALCON 9".velocity_actual > 1000\n'
            "    until timer.elapsed >= 3.0\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "qualified_signals.dsl"
            source_path.write_text(source, encoding="utf-8")

            result = cli._dsl_test_command(["test", "import", "qualified_signals", str(source_path)])

        self.assertEqual(result.code, SS__NORMAL)
        entry = cli._local_root_payload["dslTests"]["testsByName"]["qualified_signals"]
        main_statement = entry["normalized"]["main"]["sets"][0]
        self.assertEqual(main_statement["target"]["signal"], "output_percent_cmd")
        self.assertEqual(
            entry["normalized"]["main"]["aborts"][0]["reference"]["signal"],
            "current_actual",
        )
        self.assertEqual(
            entry["normalized"]["main"]["requires"][0]["reference"]["signal"],
            "velocity_actual",
        )

    def test_import_accepts_stable_and_range_conditions(self) -> None:
        cli = self._build_cli(include_controller=True)
        source = (
            'test "stable_range"\n'
            'device "FALCON 9"\n'
            'device "controller0"\n\n'
            "main:\n"
            '    abort "FALCON 9".current_actual outside 0 35 stable 0.2\n'
            '    require "FALCON 9".velocity_actual between 100 200 stable 0.1\n'
            "    success controller0.A stable 0.15\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "stable_range.dsl"
            source_path.write_text(source, encoding="utf-8")

            result = cli._dsl_test_command(["test", "import", "stable_range", str(source_path)])

        self.assertEqual(result.code, SS__NORMAL)
        entry = cli._local_root_payload["dslTests"]["testsByName"]["stable_range"]
        abort_condition = entry["normalized"]["main"]["aborts"][0]
        require_condition = entry["normalized"]["main"]["requires"][0]
        success_condition = entry["normalized"]["main"]["successes"][0]
        self.assertEqual("outside", abort_condition["mode"])
        self.assertEqual(0.2, abort_condition["stableSeconds"])
        self.assertEqual("between", require_condition["mode"])
        self.assertEqual(100, require_condition["lowLiteral"]["value"])
        self.assertEqual(200, require_condition["highLiteral"]["value"])
        self.assertEqual("bare", success_condition["mode"])
        self.assertEqual(0.15, success_condition["stableSeconds"])

    def test_import_validates_new_test_without_blocking_on_unrelated_invalid_store_entries(self) -> None:
        cli = self._build_cli(include_controller=True)
        cli._local_root_payload["dslTests"] = {
            "schemaVersion": 1,
            "defaultSet": "legacy",
            "testSets": {"legacy": ["bad_old_test"]},
            "testsByName": {
                "bad_old_test": {
                    "name": "bad_old_test",
                    "source": 'test "bad_old_test"\ndevice "Missing Device"\n\nmain:\n    abort timer.elapsed >= 1.0\n',
                    "normalized": {
                        "name": "bad_old_test",
                        "devices": [{"name": "Missing Device"}],
                        "unsafeExit": [],
                        "init": {"sets": [], "clears": [], "aborts": [], "successes": [], "untils": [], "requires": []},
                        "main": {"sets": [], "clears": [], "aborts": [{"reference": {"device": "timer", "signal": "elapsed"}, "operator": ">=", "literal": {"valueType": "number", "value": 1.0}, "kind": "abort", "text": "abort timer.elapsed >= 1.0"}], "successes": [], "untils": [], "requires": []},
                        "close": {"sets": [], "clears": [], "aborts": [], "successes": [], "untils": [], "requires": []},
                    },
                    "sourceHash": "",
                }
            },
        }
        source = (
            'test "spark25_leftY"\n'
            'device "SPARKMAX/NEO 25"\n'
            'device "controller0"\n\n'
            "main:\n"
            '    set "SPARKMAX/NEO 25".output = controller0.leftY deadband 0.08 scaled 0.25 default 0.0\n'
            "    until timer.elapsed >= 10.0\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "spark25_leftY.dsl"
            source_path.write_text(source, encoding="utf-8")

            result = cli._dsl_test_command(["test", "import", "spark25_leftY", str(source_path), "set", "default"])

        self.assertEqual(result.code, SS__NORMAL)
        self.assertIn("spark25_leftY", cli._local_root_payload["dslTests"]["testsByName"])
        self.assertIn("bad_old_test", cli._local_root_payload["dslTests"]["testsByName"])

    def test_import_validation_prints_statement_context_for_unknown_signal(self) -> None:
        cli = self._build_cli(include_controller=True)
        source = (
            'test "falcon9_leftY"\n'
            'device "FALCON 9"\n'
            'device "controller0"\n\n'
            "main:\n"
            '    set "FALCON 9".output = controller0.leftY deadband 0.08 scaled 0.25 default 0.0\n'
            "    until timer.elasped >= 10.0\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "falcon9_leftY.dsl"
            source_path.write_text(source, encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = cli._dsl_test_command(["test", "import", "falcon9_leftY", str(source_path), "set", "default"])

        self.assertNotEqual(result.code, SS__NORMAL)
        text = output.getvalue()
        self.assertIn("unknown signal", text)
        self.assertIn("line 7: until timer.elasped >= 10.0", text)

    def test_cleanup_stale_removes_invalid_tests_for_active_profile(self) -> None:
        cli = self._build_cli(include_controller=True)
        bad_source = 'test "bad_old_test"\ndevice "Missing Device"\n\nmain:\n    abort timer.elapsed >= 1.0\n'
        good_source = (
            'test "good_test"\n'
            'device "SPARKMAX/NEO 25"\n'
            'device "controller0"\n\n'
            "main:\n"
            '    set "SPARKMAX/NEO 25".output = controller0.leftY scaled 0.25 default 0.0\n'
            "    until timer.elapsed >= 1.0\n"
        )
        cli._local_root_payload["dslTests"] = robot_test_dsl_store_to_payload(
            RobotTestDslStore(
                tests_by_name={
                    "bad_old_test": RobotTestDslEntry(
                        name="bad_old_test",
                        source=bad_source,
                        normalized=compile_robot_test_dsl_source("bad_old_test", bad_source),
                        source_hash="",
                    ),
                    "good_test": RobotTestDslEntry(
                        name="good_test",
                        source=good_source,
                        normalized=compile_robot_test_dsl_source("good_test", good_source),
                        source_hash="",
                    ),
                },
                test_sets={"legacy": ["bad_old_test", "good_test"]},
                default_set="legacy",
            )
        )

        result = cli._dsl_test_command(["test", "cleanup", "stale"])

        self.assertEqual(result.code, SS__NORMAL)
        self.assertNotIn("bad_old_test", cli._local_root_payload["dslTests"]["testsByName"])
        self.assertIn("good_test", cli._local_root_payload["dslTests"]["testsByName"])
        self.assertEqual(cli._local_root_payload["dslTests"]["testSets"]["legacy"], ["good_test"])

    def test_copy_global_test_into_profile_creates_profile_owned_duplicate(self) -> None:
        cli = self._build_cli(include_controller=True)
        cli._local_root_payload["profiles"]["dsl_demo_050426"].pop("dslTestSet", None)
        source = (
            'test "swerve_global"\n'
            'device "FALCON 9"\n'
            'device "controller0"\n\n'
            "main:\n"
            '    set "FALCON 9".output = controller0.leftY scaled 0.25 default 0.0\n'
            "    until timer.elapsed >= 1.0\n"
        )
        cli._local_root_payload["dslTests"] = robot_test_dsl_store_to_payload(
            RobotTestDslStore(
                tests_by_name={
                    "swerve_global": RobotTestDslEntry(
                        name="swerve_global",
                        source=source,
                        normalized=compile_robot_test_dsl_source("swerve_global", source),
                        source_hash="",
                    )
                },
                test_sets={"global_library": ["swerve_global"]},
                default_set="global_library",
            )
        )

        result = cli._dsl_test_command(["test", "copy", "swerve_global", "demo_spin"])

        self.assertEqual(result.code, SS__NORMAL)
        self.assertEqual(
            cli._local_root_payload["profiles"]["dsl_demo_050426"]["dslTestSet"],
            "dsl_demo_050426",
        )
        self.assertEqual(
            cli._local_root_payload["dslTests"]["testSets"]["dsl_demo_050426"],
            ["demo_spin"],
        )
        self.assertEqual(
            cli._local_root_payload["dslTests"]["testSets"]["global_library"],
            ["swerve_global"],
        )
        self.assertEqual(
            cli._local_root_payload["dslTests"]["testsByName"]["demo_spin"]["normalized"]["name"],
            "demo_spin",
        )

    def test_show_test_library_reports_external_config_and_profile_scopes(self) -> None:
        cli = self._build_cli(include_controller=True)
        cli._local_root_payload["dslTests"] = {
            "schemaVersion": 1,
            "defaultSet": "global_library",
            "testSets": {
                "global_library": ["swerve_global"],
                "default": ["demo_spin"],
            },
            "testsByName": {
                "swerve_global": {"source": "", "sourceHash": "", "normalized": {}},
                "demo_spin": {"source": "", "sourceHash": "", "normalized": {}},
            },
        }
        output = io.StringIO()
        with patch(
            "tools.can_nt.bridge_cli.robot_test_dsl_list_external_library_test_names",
            return_value=["external_alpha"],
        ):
            with contextlib.redirect_stdout(output):
                result = cli._dsl_show_command(["show", "test", "library"])

        self.assertEqual(result.code, SS__NORMAL)
        text = output.getvalue()
        self.assertIn("external global library:", text)
        self.assertIn("external_alpha", text)
        self.assertIn("config library set: global_library", text)
        self.assertIn("profile test set: default", text)
        self.assertIn("swerve_global", text)
        self.assertIn("demo_spin", text)

    def test_test_rename_and_delete_archive_config_backed_test(self) -> None:
        cli = self._build_cli(include_controller=True)
        cli._local_root_payload["dslTests"] = {
            "schemaVersion": 1,
            "defaultSet": "global_library",
            "testSets": {
                "global_library": [],
                "default": ["demo_spin"],
            },
            "testsByName": {
                "demo_spin": {
                    "source": 'test "demo_spin"\nmain:\n    until timer.elapsed >= 1.0\n',
                    "sourceHash": "",
                    "normalized": {"name": "demo_spin", "devices": [], "unsafeExit": [], "init": {}, "main": {}, "close": {}},
                },
            },
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.can_nt.bridge_cli.robot_test_dsl_delete_test_from_root_payload") as delete_mock:
                delete_mock.return_value = Path(temp_dir) / "archive.dsl"
                rename_result = cli._dsl_test_command(["test", "rename", "demo_spin", "demo_spin_2"])
                delete_result = cli._dsl_test_command(["test", "delete", "demo_spin_2"])
        self.assertEqual(rename_result.code, SS__NORMAL)
        self.assertEqual(delete_result.code, SS__NORMAL)
        self.assertIn("demo_spin_2", cli._local_root_payload["dslTests"]["testsByName"])
        delete_mock.assert_called_once()

    def test_test_rename_global_and_delete_global(self) -> None:
        cli = self._build_cli(include_controller=True)
        with tempfile.TemporaryDirectory() as temp_dir:
            library_dir = Path(temp_dir)
            (library_dir / "external_alpha.dsl").write_text('test "external_alpha"\nmain:\n    until timer.elapsed >= 1.0\n', encoding="utf-8")
            with patch("tools.can_nt.bridge_cli.robot_test_dsl_rename_external_library_test") as rename_mock:
                rename_mock.return_value = library_dir / "external_beta.dsl"
                rename_result = cli._dsl_test_command(["test", "rename-global", "external_alpha", "external_beta"])
            with patch("tools.can_nt.bridge_cli.robot_test_dsl_delete_external_library_test") as delete_mock:
                delete_mock.return_value = library_dir / "_archive" / "external_beta.dsl"
                delete_result = cli._dsl_test_command(["test", "delete-global", "external_beta"])
        self.assertEqual(rename_result.code, SS__NORMAL)
        self.assertEqual(delete_result.code, SS__NORMAL)

    def test_config_mode_instantiate_all_uses_robot_path_when_not_in_group_context(self) -> None:
        cli = self._build_cli(connected=True)
        cli._wait_for_seq = lambda seq: object()
        cli._event_failed = lambda event, label: False

        result = cli._execute_line("instantiate all devices")

        self.assertEqual(result.code, SS__NORMAL)
        self.assertEqual(cli._session.sent_commands, [("addAll", {})])

    def test_group_context_member_assign_all_keeps_local_group_membership_behavior(self) -> None:
        cli = self._build_cli()
        create_result = cli._create_local_group("diag")
        self.assertEqual(create_result.code, SS__NORMAL)
        cli._modes.append(CliMode("group", group="diag"))

        result = cli._execute_line("member assign all")

        self.assertEqual(result.code, SS__NORMAL)
        self.assertEqual(cli._session.sent_commands, [])
        self.assertEqual(
            cli._list_target_group_members("diag"),
            ["FALCON 9", "SPARKMAX/NEO 25", "lmtSw0"],
        )

    def test_config_mode_group_member_assign_all_keeps_local_group_membership_behavior(self) -> None:
        cli = self._build_cli()
        create_result = cli._create_local_group("diag")
        self.assertEqual(create_result.code, SS__NORMAL)

        result = cli._execute_line("group member assign all diag")

        self.assertEqual(result.code, SS__NORMAL)
        self.assertEqual(cli._session.sent_commands, [])
        self.assertEqual(
            cli._list_target_group_members("diag"),
            ["FALCON 9", "SPARKMAX/NEO 25", "lmtSw0"],
        )

    def test_legacy_add_all_is_rejected(self) -> None:
        cli = self._build_cli(connected=True)
        cli._wait_for_seq = lambda seq: object()
        cli._event_failed = lambda event, label: False
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            result = cli._execute_line("add all")

        self.assertNotEqual(result.code, SS__NORMAL)
        self.assertIn("was removed", output.getvalue())
        self.assertEqual(cli._session.sent_commands, [])

    def test_tests_run_wait_dispatches_and_waits_for_summary(self) -> None:
        cli = self._build_cli(connected=True)
        event = BridgeEvent(
            type="ack",
            seq=1,
            name="runTest",
            status="ok",
            message="OK",
            text="",
            json_text='{"runId": 7}',
            ts=0.0,
            session_id="s",
            state={},
            raw={},
        )
        cli._wait_for_seq = lambda seq, print_events=True: event
        cli._event_failed = lambda incoming, label: False
        captured: list[tuple[int | None, float, bool]] = []
        cli._wait_for_test_run_completion = (
            lambda run_id, timeout_sec, run_all: captured.append((run_id, timeout_sec, run_all))
            or StatusResult(code=SS__NORMAL)
        )

        result = cli._execute_line("tests run --wait --timeout 12")

        self.assertEqual(result.code, SS__NORMAL)
        self.assertEqual(cli._session.sent_commands, [("runTest", {})])
        self.assertEqual(captured, [(7, 12.0, False)])

    def test_tests_run_all_wait_dispatches_and_waits_for_summary(self) -> None:
        cli = self._build_cli(connected=True)
        event = BridgeEvent(
            type="ack",
            seq=1,
            name="runAllTests",
            status="ok",
            message="OK",
            text="",
            json_text='{"runId": 11}',
            ts=0.0,
            session_id="s",
            state={},
            raw={},
        )
        cli._wait_for_seq = lambda seq, print_events=True: event
        cli._event_failed = lambda incoming, label: False
        captured: list[tuple[int | None, float, bool]] = []
        cli._wait_for_test_run_completion = (
            lambda run_id, timeout_sec, run_all: captured.append((run_id, timeout_sec, run_all))
            or StatusResult(code=SS__NORMAL)
        )

        result = cli._execute_line("tests run-all --wait")

        self.assertEqual(result.code, SS__NORMAL)
        self.assertEqual(cli._session.sent_commands, [("runAllTests", {})])
        self.assertEqual(captured, [(11, 10.0, True)])

    def test_finish_tests_wait_prints_detailed_summary(self) -> None:
        cli = self._build_cli()
        run = {
            "runId": 12,
            "state": "passed",
            "test": "spin_up_motor1",
            "result": "PASS",
            "status": 'until until_1: until timer.elapsed >= 3.0',
            "message": "",
            "startedAtMs": 1000,
            "finishedAtMs": 4200,
            "details": {
                "requires": [
                    {
                        "id": "require_1",
                        "text": 'require "FALCON 9".velocity > 1000',
                        "satisfied": True,
                        "satisfiedAtSec": 1.24,
                        "sampleValue": 1420,
                    }
                ],
                "lastSamples": {
                    "FALCON 9.velocity": 1420,
                    "timer.elapsed": 3.0,
                },
            },
        }
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = cli._finish_tests_wait(run)
        text = output.getvalue()
        self.assertEqual(result.code, SS__NORMAL)
        self.assertIn("Test run complete:", text)
        self.assertIn("elapsed: 3.20s", text)
        self.assertIn("require_1 PASS", text)
        self.assertIn("FALCON 9.velocity: 1420", text)

    def test_connect_surfaces_handshake_failure_detail(self) -> None:
        cli = self._build_cli()
        cli._modes = [CliMode("exec")]

        class _HandshakeFailSession(_FakeSession):
            def connect(self) -> bool:
                self.connected = True
                return True

            def ensure_handshake(self) -> bool:
                return False

            def last_handshake_error(self) -> str:
                return "uiHandshake ACK received but no OUT within 1.5s."

        cli._session = _HandshakeFailSession()
        output = io.StringIO()
        with patch("tools.can_nt.bridge_cli_ast.connect", return_value=True):
            with contextlib.redirect_stdout(output):
                result = cli._execute_line("connect")
        text = output.getvalue()
        self.assertNotEqual(result.code, SS__NORMAL)
        self.assertIn("Handshake failed: uiHandshake ACK received but no OUT within 1.5s.", text)
