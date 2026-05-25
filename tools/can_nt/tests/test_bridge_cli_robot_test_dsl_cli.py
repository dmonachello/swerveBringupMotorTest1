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
