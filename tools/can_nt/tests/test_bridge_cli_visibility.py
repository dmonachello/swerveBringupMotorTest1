"""
NAME
    test_bridge_cli_visibility.py - Unit tests for CLI visibility and scope state.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.widgets import TextArea

from tools.can_nt.bridge_cli import (
    BridgeCli,
    CliMode,
    KEY_ACTIVE_GROUP,
    KEY_AT,
    KEY_BINDINGS,
    KEY_BRIDGE_BY_PROFILE,
    KEY_BRIDGE_CONFIG,
    KEY_BRIDGE_GENERATED_AT,
    KEY_BRIDGE_SCHEMA_VERSION,
    KEY_DATA_HASH,
    KEY_DATA_VERSION,
    KEY_DEFAULT_PROFILE,
    KEY_DEVICE,
    KEY_DEVICE_COUNT,
    KEY_DEVICE_TYPE,
    KEY_DEVICES,
    KEY_ENABLED,
    KEY_GLOBAL_BINDINGS,
    KEY_GROUPS,
    KEY_ID,
    KEY_IN_PROFILE,
    KEY_INTERFACE,
    KEY_LAST_MODIFIED_AT,
    KEY_LAST_PUSHED,
    KEY_LAST_SAVED,
    KEY_LABEL,
    KEY_MANUFACTURER,
    KEY_MODEL,
    KEY_PROFILE,
    KEY_PROFILES,
    KEY_PROFILE_DEVICES,
    KEY_PROFILE_INFO,
    KEY_PROVENANCE,
    KEY_RECOVERY_MODE,
    KEY_SCHEMA_VERSION,
    KEY_SELECTED_DEVICE,
    KEY_SIGNALS,
    KEY_SCOPE,
    KEY_SOURCE_PATH,
    KEY_TESTS,
    SOURCE_NAME_TESTS,
    KEY_TOPOLOGY,
    KEY_TOPOLOGY_EDGES,
    KEY_TOPOLOGY_NODES,
    KEY_VISIBILITY,
    KEY_TOPOLOGY_PROFILES,
    KEY_TOPOLOGY_SOURCE,
    KEY_TOPOLOGY_VERSION,
    PROMPT_DIRTY_MARK,
    PROFILE_SCHEMA_VERSION,
    BRIDGE_CONFIG_SCHEMA_VERSION,
)
from tools.can_nt.bridge_session import BridgeEvent
from tools.can_nt.bridge_cli_parser import BridgeCliParser, CliParseError
from tools.can_nt.status import SS__CONFIG__INVALID, SS__CONFIG__SAVED, SS__NORMAL, StatusResult
from tools.common.tests.config_api_test_helper import load_profiles_payload, write_profiles_payload


PROFILE_NAME = "demo"
TOPOLOGY_SOURCE_LOCAL = "local"
EMPTY_STRING = ""


class _FakeSession:
    def __init__(self, connected: bool = False) -> None:
        self.connected = connected
        self.disconnect_called = False

    def is_connected(self) -> bool:
        return self.connected

    def get_state_snapshot(self) -> dict:
        return {}

    def session_id(self) -> str:
        return EMPTY_STRING

    def handshake_done(self) -> bool:
        return False

    def ensure_handshake(self, reset: bool = False) -> bool:
        return True

    def send_command(self, _name: str, _args: dict | None = None):
        return None

    def disconnect(self) -> None:
        self.disconnect_called = True
        self.connected = False


class _FakeVisibilityProvider:
    def snapshot(self, _scope: str, _now_ms: int) -> dict:
        return {
            "devices": [
                {
                    "label": "motor1",
                    "visibility": {"src0": True},
                }
            ],
            "sources": [{"id": "src0", "label": "analyzer0", "available": True}],
        }

    def summary(self, _scope: str, _now_ms: int) -> dict:
        return {
            "devicesShown": 1,
            "visibleAll": 1,
            "visibleSome": 0,
            "visibleNone": 0,
        }


class _FakeBuffer:
    def __init__(self, text: str = "", cursor_position: int = 0) -> None:
        self._text = text
        self.text = text
        self.cursor_position = cursor_position
        self.document = self
        self.appended = False
        self.reset_calls: list[bool] = []

    def translate_row_col_to_index(self, row: int, _col: int) -> int:
        lines = self._text.splitlines() or [""]
        row = max(0, min(row, len(lines) - 1))
        return sum(len(line) + 1 for line in lines[:row])

    def cursor_up(self, count: int = 1) -> None:
        self.cursor_position = max(0, self.cursor_position - count)

    def cursor_down(self, count: int = 1) -> None:
        self.cursor_position += count

    def append_to_history(self) -> None:
        self.appended = True

    def reset(self, append_to_history: bool = False) -> None:
        self.reset_calls.append(append_to_history)
        if append_to_history:
            self.appended = True
        self.text = ""


class _FakeTextArea:
    def __init__(self, text: str = "", cursor_position: int = 0) -> None:
        self.text = text
        self.buffer = _FakeBuffer(text=text, cursor_position=cursor_position)
        self.window = type("WindowStub", (), {"vertical_scroll": 0})()


class BridgeCliVisibilityTests(unittest.TestCase):
    @staticmethod
    def _success_event(name: str) -> BridgeEvent:
        return BridgeEvent(
            type="out",
            seq=1,
            name=name,
            status="ok",
            message="",
            text="OK",
            json_text='{"success":true}',
            ts=0.0,
            session_id="",
            state={},
            raw={},
        )

    def _build_cli(self, connected: bool = False) -> BridgeCli:
        cli = BridgeCli(_FakeSession(connected=connected), batch=True)
        cli._local_root_payload = {
            KEY_SCHEMA_VERSION: PROFILE_SCHEMA_VERSION,
            KEY_DEFAULT_PROFILE: PROFILE_NAME,
            KEY_PROFILES: {
                PROFILE_NAME: {
                    KEY_PROFILE_DEVICES: [],
                }
            },
            KEY_DEVICES: [],
            KEY_TOPOLOGY: {
                KEY_TOPOLOGY_VERSION: 1,
                KEY_TOPOLOGY_SOURCE: TOPOLOGY_SOURCE_LOCAL,
                KEY_TOPOLOGY_PROFILES: {},
            },
            KEY_DATA_VERSION: "test-version",
            KEY_DATA_HASH: EMPTY_STRING,
        }
        cli._local_config = {
            KEY_BRIDGE_SCHEMA_VERSION: BRIDGE_CONFIG_SCHEMA_VERSION,
            KEY_BRIDGE_GENERATED_AT: None,
            KEY_BRIDGE_BY_PROFILE: {
                PROFILE_NAME: {
                    KEY_GROUPS: [],
                    KEY_SELECTED_DEVICE: {
                        KEY_DEVICE: EMPTY_STRING,
                        KEY_ENABLED: False,
                    },
                }
            },
        }
        cli._groups_profile = PROFILE_NAME
        cli._sync_store_from_local()
        return cli

    def test_prompt_marks_dirty_state(self) -> None:
        cli = self._build_cli()

        cli._mark_profiles_dirty()

        self.assertIn(PROMPT_DIRTY_MARK, cli._prompt())

    def test_ensure_default_profile_context_creates_blank_profile_through_shared_contract(self) -> None:
        cli = self._build_cli()
        cli._local_root_payload[KEY_DEFAULT_PROFILE] = EMPTY_STRING  # type: ignore[index]
        cli._local_root_payload[KEY_PROFILES] = {}  # type: ignore[index]
        cli._local_root_payload[KEY_TOPOLOGY][KEY_TOPOLOGY_PROFILES] = {}  # type: ignore[index]

        cli._ensure_default_profile_context()

        default_name = cli._local_root_payload[KEY_DEFAULT_PROFILE]
        self.assertIsInstance(default_name, str)
        self.assertIn(default_name, cli._local_root_payload[KEY_PROFILES])
        topology_entry = cli._local_root_payload[KEY_TOPOLOGY][KEY_TOPOLOGY_PROFILES][default_name]
        self.assertEqual([], topology_entry[KEY_TOPOLOGY_NODES])
        self.assertEqual([], topology_entry[KEY_TOPOLOGY_EDGES])

    def test_create_profile_creates_blank_topology_entry(self) -> None:
        cli = self._build_cli()

        result = cli._create_profile("alpha")

        self.assertEqual(SS__NORMAL, result.code)
        self.assertIn("alpha", cli._local_root_payload[KEY_PROFILES])
        topology_entry = cli._local_root_payload[KEY_TOPOLOGY][KEY_TOPOLOGY_PROFILES]["alpha"]
        self.assertEqual([], topology_entry[KEY_TOPOLOGY_NODES])
        self.assertEqual([], topology_entry[KEY_TOPOLOGY_EDGES])

    def test_delete_profile_rehomes_default_through_shared_contract(self) -> None:
        cli = self._build_cli()
        cli._local_root_payload[KEY_PROFILES]["alpha"] = {KEY_PROFILE_DEVICES: []}  # type: ignore[index]
        cli._local_root_payload[KEY_TOPOLOGY][KEY_TOPOLOGY_PROFILES]["alpha"] = {  # type: ignore[index]
            KEY_TOPOLOGY_NODES: [],
            KEY_TOPOLOGY_EDGES: [],
        }
        cli._local_root_payload[KEY_DEFAULT_PROFILE] = "alpha"  # type: ignore[index]

        result = cli._delete_profile("alpha")

        self.assertEqual(SS__NORMAL, result.code)
        self.assertEqual(PROFILE_NAME, cli._local_root_payload[KEY_DEFAULT_PROFILE])
        self.assertNotIn("alpha", cli._local_root_payload[KEY_PROFILES])
        self.assertNotIn("alpha", cli._local_root_payload[KEY_TOPOLOGY][KEY_TOPOLOGY_PROFILES])

    def test_active_topology_profile_create_bootstraps_shared_blank_topology(self) -> None:
        cli = self._build_cli()
        cli._local_root_payload[KEY_TOPOLOGY][KEY_TOPOLOGY_PROFILES] = {}  # type: ignore[index]

        topology_profile = cli._active_topology_profile(create=True)

        self.assertEqual([], topology_profile[KEY_TOPOLOGY_NODES])
        self.assertEqual([], topology_profile[KEY_TOPOLOGY_EDGES])
        self.assertIn(PROFILE_NAME, cli._local_root_payload[KEY_TOPOLOGY][KEY_TOPOLOGY_PROFILES])

    def test_show_workspace_json_includes_provenance(self) -> None:
        cli = self._build_cli()
        cli._last_modified_at = 1.0
        cli._last_saved_at = 2.0
        cli._last_saved_path = "src/main/deploy/bringup_system.json"
        cli._last_saved_hash = "abcd1234"
        cli._last_pushed_at = 3.0
        cli._last_pushed_path = "src/main/deploy/bringup_system.json"
        cli._last_pushed_hash = "abcd1234"
        cli._last_pushed_profile = PROFILE_NAME

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = cli._show_workspace(json_output=True, pretty=False)

        self.assertEqual(result.code, SS__NORMAL)
        payload = json.loads(output.getvalue())
        provenance = payload[KEY_PROVENANCE]
        self.assertEqual(provenance[KEY_LAST_MODIFIED_AT], 1.0)
        self.assertEqual(provenance[KEY_LAST_SAVED][KEY_AT], 2.0)
        self.assertEqual(
            provenance[KEY_LAST_SAVED][KEY_SOURCE_PATH],
            "src/main/deploy/bringup_system.json",
        )
        self.assertEqual(provenance[KEY_LAST_PUSHED][KEY_AT], 3.0)

    def test_shutdown_session_disconnects_owned_session(self) -> None:
        session = _FakeSession(connected=True)
        cli = BridgeCli(session, batch=True)

        cli._shutdown_session()

        self.assertTrue(session.disconnect_called)

    def test_save_without_target_uses_save_all(self) -> None:
        cli = self._build_cli()
        calls: list[tuple[bool, bool]] = []

        def _fake_save_all(prompt: bool, force: bool = False):
            calls.append((prompt, force))
            return SS__CONFIG__SAVED

        cli._save_all = _fake_save_all  # type: ignore[method-assign]

        result = cli._handle_save_command(["save"])

        self.assertEqual(result, SS__CONFIG__SAVED)
        self.assertEqual(calls, [(False, False)])

    def test_config_push_refuses_when_dirty(self) -> None:
        cli = self._build_cli(connected=True)
        cli._mark_profiles_dirty()

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = cli._config_push("src/main/deploy/bringup_system.json", PROFILE_NAME)

        self.assertEqual(result.code, SS__CONFIG__INVALID)
        self.assertIn("push config refused", output.getvalue())

    def test_save_unified_records_last_save_provenance(self) -> None:
        cli = self._build_cli()

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bringup_system.json"
            result = cli._save_unified_config(str(path), skip_validation=True)

        self.assertEqual(result.code, SS__CONFIG__SAVED)

    def test_reload_source_tests_refreshes_model_from_local_profile_config(self) -> None:
        cli = self._build_cli()
        cli._local_config[KEY_BRIDGE_BY_PROFILE][PROFILE_NAME][KEY_TESTS] = {
            "defaultSet": "demo_set",
            "testSets": {
                "demo_set": [
                    {
                        "name": "Spin Motor",
                        "enabled": True,
                        "motorLabels": ["motor1"],
                        "type": "fixed",
                    }
                ]
            },
        }
        cli._tests_model = None
        cli._tests_profile = None
        cli._tests_dirty = True

        result = cli._reload_source(SOURCE_NAME_TESTS, "src/main/deploy/bringup_system.json")

        self.assertEqual(result.code, SS__NORMAL)
        self.assertIsNotNone(cli._tests_model)
        self.assertEqual(cli._tests_profile, PROFILE_NAME)
        self.assertFalse(cli._tests_dirty)

    def test_save_profiles_does_not_mirror_when_canonical_matches_deploy(self) -> None:
        cli = self._build_cli()
        cli._local_devices_locked = True

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            deploy_path = repo_root / "src" / "main" / "deploy" / "bringup_system.json"
            deploy_path.parent.mkdir(parents=True, exist_ok=True)
            with patch("tools.can_nt.bridge_cli.profiles_canonical_path", return_value=deploy_path), patch(
                "tools.can_nt.bridge_cli.profiles_deploy_path", return_value=deploy_path
            ):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    result = cli._save_profiles(str(deploy_path), skip_validation=True)

            self.assertEqual(result.code, SS__CONFIG__SAVED)
            self.assertTrue(deploy_path.exists())
            self.assertIn("Wrote profiles to", output.getvalue())
            self.assertNotIn("Mirrored profiles to", output.getvalue())

    def test_save_bindings_does_not_mirror_when_canonical_matches_deploy(self) -> None:
        cli = self._build_cli()
        cli._bindings_payload = {
            "controllers": [{"name": "driver0", "type": "XBOX", "port": 0}],
            "bindings": [],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            deploy_path = repo_root / "src" / "main" / "deploy" / "bringup_bindings.json"
            deploy_path.parent.mkdir(parents=True, exist_ok=True)
            with patch("tools.can_nt.bridge_cli.bindings_canonical_path", return_value=deploy_path), patch(
                "tools.can_nt.bridge_cli.bindings_deploy_path", return_value=deploy_path
            ):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    result = cli._save_bindings_to_path(deploy_path)

            self.assertEqual(result.code, SS__CONFIG__SAVED)
            self.assertTrue(deploy_path.exists())
            self.assertIn("Wrote bindings to", output.getvalue())
            self.assertNotIn("Mirrored bindings to", output.getvalue())

    def test_show_active_json_reports_local_state(self) -> None:
        cli = self._build_cli()
        cli._runtime_details_provider = lambda: {"components": [{"name": "cli", "status": "running"}]}
        cli._visibility_provider = _FakeVisibilityProvider()

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = cli._show_active_local(json_output=True, pretty=False)

        self.assertEqual(result.code, SS__NORMAL)

    def test_show_devices_all_json_returns_full_shared_inventory(self) -> None:
        cli = self._build_cli()
        cli._local_root_payload[KEY_DEVICES] = [  # type: ignore[index]
            {
                KEY_LABEL: "motor1",
                KEY_INTERFACE: "CAN",
                KEY_MANUFACTURER: 5,
                KEY_DEVICE_TYPE: 2,
                KEY_ID: 1,
                KEY_MODEL: "REV NEO",
            },
            {
                KEY_LABEL: "controller0",
                KEY_INTERFACE: "USB",
                KEY_ID: 0,
                KEY_MODEL: "Xbox Controller",
                "type": "xboxController",
            },
        ]
        cli._local_root_payload[KEY_PROFILES][PROFILE_NAME][KEY_PROFILE_DEVICES] = ["motor1"]  # type: ignore[index]

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = cli._handle_show(["devices", "local", "--all", "--json"])

        self.assertEqual(result.code, SS__NORMAL)
        payload = json.loads(output.getvalue().splitlines()[-1])
        self.assertEqual(payload[KEY_SCOPE], "config")
        by_label = {entry[KEY_LABEL]: entry for entry in payload[KEY_DEVICES]}
        self.assertTrue(by_label["motor1"][KEY_IN_PROFILE])
        self.assertFalse(by_label["controller0"][KEY_IN_PROFILE])
        self.assertEqual(by_label["motor1"][KEY_MODEL], "REV NEO")
        self.assertEqual(by_label["controller0"][KEY_INTERFACE], "USB")

    def test_load_profiles_from_path_salvages_partial_config(self) -> None:
        cli = BridgeCli(_FakeSession(), batch=True)
        payload = {
            KEY_SCHEMA_VERSION: PROFILE_SCHEMA_VERSION,
            KEY_DATA_VERSION: "test",
            KEY_DATA_HASH: EMPTY_STRING,
            KEY_DEFAULT_PROFILE: PROFILE_NAME,
            KEY_DEVICES: [
                {
                    KEY_LABEL: "good",
                    "deviceInterface": "DIO",
                    "id": 0,
                    "invert": False,
                },
                {
                    KEY_LABEL: "bad",
                    "deviceInterface": "CAN",
                    "deviceType": 1,
                },
            ],
            KEY_PROFILES: {
                PROFILE_NAME: {
                    KEY_PROFILE_DEVICES: ["good", "bad", "missing"],
                }
            },
            KEY_BRIDGE_CONFIG: {
                KEY_BRIDGE_SCHEMA_VERSION: BRIDGE_CONFIG_SCHEMA_VERSION,
                KEY_BRIDGE_GENERATED_AT: None,
                KEY_BRIDGE_BY_PROFILE: {
                    PROFILE_NAME: {
                        KEY_GROUPS: [
                            {
                                "name": "drive",
                                KEY_ENABLED: True,
                                "members": [
                                    {KEY_LABEL: "good", KEY_ENABLED: True},
                                    {KEY_LABEL: "missing", KEY_ENABLED: True},
                                ],
                            }
                        ],
                        KEY_SELECTED_DEVICE: {KEY_DEVICE: "missing", KEY_ENABLED: True},
                    }
                },
            },
            KEY_TOPOLOGY: {
                KEY_TOPOLOGY_VERSION: 1,
                KEY_TOPOLOGY_PROFILES: {},
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bringup_system.json"
            write_profiles_payload(path, payload, stamp=False)

            with contextlib.redirect_stdout(io.StringIO()):
                result = cli._load_profiles_from_path(path, announce=False)

        self.assertEqual(result.code, SS__CONFIG__INVALID)
        self.assertTrue(cli._recovery_mode)
        self.assertTrue(cli._profiles_dirty)
        self.assertEqual([entry[KEY_LABEL] for entry in cli._local_root_payload[KEY_DEVICES]], ["good"])
        self.assertEqual(
            cli._local_root_payload[KEY_PROFILES][PROFILE_NAME][KEY_PROFILE_DEVICES],
            ["good"],
        )
        members = cli._local_config[KEY_BRIDGE_BY_PROFILE][PROFILE_NAME][KEY_GROUPS][0]["members"]
        self.assertEqual(members, [{KEY_LABEL: "good", KEY_ENABLED: True}])

    def test_auto_merge_default_profiles_recovers_from_bad_json(self) -> None:
        cli = BridgeCli(_FakeSession(), batch=True)

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bringup_system.json"
            path.write_text("{ bad json", encoding="utf-8")
            with patch("tools.can_nt.bridge_cli.profiles_canonical_path", return_value=path):
                with contextlib.redirect_stdout(io.StringIO()):
                    cli._auto_merge_default_profiles()

        self.assertTrue(cli._recovery_mode)
        self.assertIsInstance(cli._local_root_payload, dict)
        self.assertIsInstance(cli._local_root_payload[KEY_DEVICES], list)
        self.assertIsInstance(cli._local_root_payload[KEY_PROFILES], dict)
        self.assertIn(KEY_DEFAULT_PROFILE, cli._local_root_payload)

    def test_show_instantiated_json_reports_local_unavailable_state(self) -> None:
        cli = self._build_cli()
        cli._local_root_payload[KEY_PROFILES][PROFILE_NAME][KEY_PROFILE_DEVICES] = ["motor1"]  # type: ignore[index]
        cli._visibility_provider = _FakeVisibilityProvider()

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = cli._show_instantiated_local(json_output=True, pretty=False)

        self.assertEqual(result.code, SS__NORMAL)
        payload = json.loads(output.getvalue().splitlines()[-1])
        self.assertEqual(payload[KEY_DEVICES][0]["label"], "motor1")
        self.assertIsNone(payload[KEY_DEVICES][0]["instantiated"])

    def test_parser_accepts_new_show_targets(self) -> None:
        parser = BridgeCliParser()

        self.assertEqual(parser.parse("show active", mode="exec").tokens, ["show", "active"])
        self.assertEqual(parser.parse("show instantiated", mode="exec").tokens, ["show", "instantiated"])
        self.assertEqual(parser.parse("show faults", mode="exec").tokens, ["show", "faults"])
        self.assertEqual(parser.parse("show signals", mode="exec").tokens, ["show", "signals"])
        self.assertEqual(parser.parse("show signal motor1", mode="exec").tokens, ["show", "signal", "motor1"])
        self.assertEqual(parser.parse("tiu on", mode="exec").tokens, ["tiu", "on"])

    def test_show_active_robot_json_includes_device_count(self) -> None:
        cli = self._build_cli()
        cli._fetch_robot_runtime_payload = lambda: {  # type: ignore[method-assign]
            KEY_PROFILE: PROFILE_NAME,
            KEY_ENABLED: False,
            "estopped": False,
            "mode": "teleop",
            KEY_DEVICES: [{"label": "motor1"}],
            KEY_GROUPS: [{"name": "active-group"}],
            KEY_SELECTED_DEVICE: {KEY_DEVICE: EMPTY_STRING, KEY_ENABLED: False},
        }

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = cli._show_active_robot(json_output=True, pretty=False)

        self.assertEqual(result.code, SS__NORMAL)
        payload = json.loads(output.getvalue().splitlines()[-1])
        self.assertEqual(payload[KEY_DEVICE_COUNT], 1)

    def test_parser_accepts_runtime_commands(self) -> None:
        parser = BridgeCliParser()

        self.assertEqual(parser.parse("runtime activate", mode="exec").tokens, ["runtime", "activate"])
        self.assertEqual(
            parser.parse("runtime activate demo", mode="config").tokens,
            ["runtime", "activate", "demo"],
        )
        self.assertEqual(
            parser.parse("runtime deactivate", mode="exec").tokens,
            ["runtime", "deactivate"],
        )

    def test_parser_accepts_exec_profile_switch_and_show_all(self) -> None:
        parser = BridgeCliParser()

        self.assertEqual(parser.parse("profile demo", mode="exec").tokens, ["profile", "demo"])
        self.assertEqual(
            parser.parse("profile device show-all lmtSw0", mode="exec").tokens,
            ["profile", "device", "show-all", "lmtSw0"],
        )

    def test_parser_rejects_invalid_exec_profile_device_shorthand(self) -> None:
        parser = BridgeCliParser()

        with self.assertRaises(CliParseError):
            parser.parse("profile device lmtSw0", mode="exec")

    def test_exec_profile_completion_requires_show_all_before_device_name(self) -> None:
        cli = self._build_cli()

        self.assertIn("<name>", cli._suggest_next_args(["profile"]))
        self.assertEqual(["show-all"], cli._suggest_next_args(["profile", "device"]))
        self.assertEqual(
            ["<name>"],
            cli._suggest_next_args(["profile", "device", "show-all"]),
        )

    def test_parser_accepts_lifecycle_commands(self) -> None:
        parser = BridgeCliParser()

        self.assertEqual(
            parser.parse("lifecycle activate active-group", mode="exec").tokens,
            ["lifecycle", "activate", "active-group"],
        )
        self.assertEqual(
            parser.parse("lifecycle activate FALCON9 mode active", mode="config").tokens,
            ["lifecycle", "activate", "FALCON9", "mode", "active"],
        )
        self.assertEqual(
            parser.parse("lifecycle deactivate active-group", mode="exec").tokens,
            ["lifecycle", "deactivate", "active-group"],
        )
        self.assertEqual(
            parser.parse("lifecycle deactivate-active", mode="exec").tokens,
            ["lifecycle", "deactivate-active"],
        )
        self.assertEqual(
            parser.parse("show lifecycle-state", mode="exec").tokens,
            ["show", "lifecycle-state"],
        )

    def test_runtime_activate_uses_runtime_command_path(self) -> None:
        cli = self._build_cli(connected=True)
        cli._wait_for_seq = lambda seq, timeout_sec=None: object()  # type: ignore[method-assign]
        cli._event_failed = lambda event, command_name: False  # type: ignore[method-assign]

        with patch("tools.can_nt.bridge_cli.runtime_activate", return_value=7):
            result = cli._runtime_activate("demo")

        self.assertEqual(result.code, SS__NORMAL)

    def test_lifecycle_activate_uses_lifecycle_command_path(self) -> None:
        cli = self._build_cli(connected=True)
        cli._wait_for_seq = lambda seq, timeout_sec=None: self._success_event("lifecycleActivate")  # type: ignore[method-assign]
        cli._event_failed = lambda event, command_name: False  # type: ignore[method-assign]

        with patch("tools.can_nt.bridge_cli.lifecycle_activate", return_value=9):
            result = cli._lifecycle_activate("active-group", "READ_ONLY")

        self.assertEqual(result.code, SS__NORMAL)

    def test_lifecycle_command_dispatches_activate_keyword(self) -> None:
        cli = self._build_cli(connected=True)
        calls = []
        cli._lifecycle_activate = lambda label, mode="READ_ONLY": calls.append((label, mode)) or StatusResult(code=SS__NORMAL)  # type: ignore[method-assign]

        result = cli._lifecycle_command(["lifecycle", "activate", "active-group"])

        self.assertEqual(result.code, SS__NORMAL)
        self.assertEqual(calls, [("active-group", "READ_ONLY")])

    def test_lifecycle_deactivate_uses_lifecycle_command_path(self) -> None:
        cli = self._build_cli(connected=True)
        cli._wait_for_seq = lambda seq, timeout_sec=None: self._success_event("lifecycleDeactivate")  # type: ignore[method-assign]
        cli._event_failed = lambda event, command_name: False  # type: ignore[method-assign]

        with patch("tools.can_nt.bridge_cli.lifecycle_deactivate", return_value=10):
            result = cli._lifecycle_deactivate("active-group")

        self.assertEqual(result.code, SS__NORMAL)

    def test_lifecycle_deactivate_active_uses_lifecycle_command_path(self) -> None:
        cli = self._build_cli(connected=True)
        cli._wait_for_seq = lambda seq, timeout_sec=None: self._success_event("lifecycleDeactivateActive")  # type: ignore[method-assign]
        cli._event_failed = lambda event, command_name: False  # type: ignore[method-assign]

        with patch("tools.can_nt.bridge_cli.lifecycle_deactivate_active", return_value=11):
            result = cli._lifecycle_deactivate_active()

        self.assertEqual(result.code, SS__NORMAL)

    def test_show_lifecycle_state_routes_to_robot_command_path(self) -> None:
        cli = self._build_cli(connected=True)
        cli._wait_for_seq = lambda seq, timeout_sec=None: object()  # type: ignore[method-assign]
        cli._event_failed = lambda event, command_name: False  # type: ignore[method-assign]

        with patch("tools.can_nt.bridge_cli.show_lifecycle_state", return_value=12):
            result = cli._handle_show(["lifecycle-state"])

        self.assertEqual(result.code, SS__NORMAL)

    def test_lifecycle_event_error_reads_semantic_failure_payload(self) -> None:
        cli = self._build_cli()
        event = BridgeEvent(
            type="out",
            seq=1,
            name="lifecycleActivate",
            status="ok",
            message="Unknown label: active-group",
            text="Unknown label: active-group",
            json_text='{"operation":"activate","success":false,"errorCode":"UNKNOWN_LABEL","errorMessage":"Unknown label: active-group"}',
            ts=0.0,
            session_id="",
            state={},
            raw={},
        )

        self.assertEqual(
            "Unknown label: active-group",
            cli._lifecycle_event_error(event),
        )

    def test_lifecycle_event_error_ignores_success_payload(self) -> None:
        cli = self._build_cli()
        event = BridgeEvent(
            type="out",
            seq=1,
            name="lifecycleActivate",
            status="ok",
            message="Lifecycle activated: active-group",
            text="Lifecycle activated: active-group",
            json_text='{"operation":"activate","success":true,"requestedLabel":"active-group"}',
            ts=0.0,
            session_id="",
            state={},
            raw={},
        )

        self.assertEqual(EMPTY_STRING, cli._lifecycle_event_error(event))

    def test_lifecycle_activate_returns_executor_failed_on_semantic_failure(self) -> None:
        cli = self._build_cli(connected=True)
        event = BridgeEvent(
            type="out",
            seq=1,
            name="lifecycleActivate",
            status="ok",
            message="Unknown label: active-group",
            text="Unknown label: active-group",
            json_text='{"operation":"activate","success":false,"errorCode":"UNKNOWN_LABEL","errorMessage":"Unknown label: active-group"}',
            ts=0.0,
            session_id="",
            state={},
            raw={},
        )
        cli._wait_for_seq = lambda seq, timeout_sec=None: event  # type: ignore[method-assign]
        cli._event_failed = lambda returned, command_name: False  # type: ignore[method-assign]

        with patch("tools.can_nt.bridge_cli.lifecycle_activate", return_value=13):
            result = cli._lifecycle_activate("active-group", "READ_ONLY")

        self.assertNotEqual(result.code, SS__NORMAL)
        self.assertEqual("Unknown label: active-group", result.message)

    def test_lifecycle_activate_returns_normal_on_success_payload(self) -> None:
        cli = self._build_cli(connected=True)
        event = BridgeEvent(
            type="out",
            seq=1,
            name="lifecycleActivate",
            status="ok",
            message="Lifecycle activated: active-group",
            text="Lifecycle activated: active-group",
            json_text='{"operation":"activate","success":true,"requestedLabel":"active-group"}',
            ts=0.0,
            session_id="",
            state={},
            raw={},
        )
        cli._wait_for_seq = lambda seq, timeout_sec=None: event  # type: ignore[method-assign]
        cli._event_failed = lambda returned, command_name: False  # type: ignore[method-assign]

        with patch("tools.can_nt.bridge_cli.lifecycle_activate", return_value=13):
            result = cli._lifecycle_activate("active-group", "READ_ONLY")

        self.assertEqual(result.code, SS__NORMAL)

    def test_lifecycle_activate_returns_executor_failed_on_text_only_semantic_failure(self) -> None:
        cli = self._build_cli(connected=True)
        event = BridgeEvent(
            type="out",
            seq=1,
            name="lifecycleActivate",
            status="ok",
            message="Unknown label: active-group",
            text="Unknown label: active-group",
            json_text="",
            ts=0.0,
            session_id="",
            state={},
            raw={},
        )
        cli._wait_for_seq = lambda seq, timeout_sec=None: event  # type: ignore[method-assign]
        cli._event_failed = lambda returned, command_name: False  # type: ignore[method-assign]

        with patch("tools.can_nt.bridge_cli.lifecycle_activate", return_value=13):
            result = cli._lifecycle_activate("active-group", "READ_ONLY")

        self.assertNotEqual(result.code, SS__NORMAL)
        self.assertEqual("Unknown label: active-group", result.message)

    def test_set_active_profile_syncs_robot_when_connected(self) -> None:
        cli = self._build_cli(connected=True)
        cli._wait_for_seq = lambda seq, timeout_sec=None: self._success_event("selectProfile")  # type: ignore[method-assign]
        cli._event_failed = lambda returned, command_name: False  # type: ignore[method-assign]

        with patch("tools.can_nt.bridge_cli.select_profile", return_value=21) as mock_select:
            result = cli._set_active_profile(PROFILE_NAME)

        self.assertEqual(result.code, SS__NORMAL)
        mock_select.assert_called_once_with(cli._session, PROFILE_NAME)
        self.assertEqual(PROFILE_NAME, cli._groups_profile)
        self.assertEqual(PROFILE_NAME, cli._robot_selected_profile)

    def test_exec_profile_command_sets_current_profile_when_connected(self) -> None:
        cli = self._build_cli(connected=True)
        cli._wait_for_seq = lambda seq, timeout_sec=None: self._success_event("selectProfile")  # type: ignore[method-assign]
        cli._event_failed = lambda returned, command_name: False  # type: ignore[method-assign]

        with patch("tools.can_nt.bridge_cli.select_profile", return_value=21) as mock_select:
            result = cli._exec_command(["profile", PROFILE_NAME])

        self.assertEqual(result.code, SS__NORMAL)
        mock_select.assert_called_once_with(cli._session, PROFILE_NAME)
        self.assertEqual(PROFILE_NAME, cli._robot_selected_profile)

    def test_exec_prompt_prefers_robot_selected_profile_when_connected(self) -> None:
        cli = self._build_cli(connected=True)
        cli._groups_profile = "local-profile"
        cli._robot_selected_profile = PROFILE_NAME

        self.assertIn(f"-profile-{PROFILE_NAME}>", cli._prompt())

    def test_show_profiles_local_matches_local_profile_summary(self) -> None:
        cli = self._build_cli()
        cli._groups_profile = PROFILE_NAME

        profiles_output = io.StringIO()
        with contextlib.redirect_stdout(profiles_output):
            profiles_result = cli._show_local_profiles(json_output=False, pretty=False)

        profile_output = io.StringIO()
        with contextlib.redirect_stdout(profile_output):
            profile_result = cli._show_local_profile("", json_output=False, pretty=False)

        self.assertEqual(profiles_result.code, SS__NORMAL)
        self.assertEqual(profile_result.code, SS__NORMAL)
        self.assertEqual(profiles_output.getvalue(), profile_output.getvalue())
        self.assertIn("selected=demo", profiles_output.getvalue())

    def test_connect_batch_warns_and_keeps_host_context_when_robot_profile_differs(self) -> None:
        cli = self._build_cli(connected=False)
        cli._groups_profile = "local-profile"

        def _connect_stub(_session):
            cli._session.connected = True
            return True

        with (
            patch("tools.can_nt.bridge_cli.connect", side_effect=_connect_stub),
            patch.object(cli, "_query_robot_selected_profile_after_connect", return_value=PROFILE_NAME),
            patch("builtins.print") as mock_print,
        ):
            result = cli._exec_command(["connect"])

        self.assertEqual(result.code, SS__NORMAL)
        self.assertEqual("local-profile", cli._groups_profile)
        self.assertEqual(PROFILE_NAME, cli._robot_selected_profile)
        self.assertTrue(
            any(
                "Leaving host context unchanged." in str(call.args[0])
                for call in mock_print.call_args_list
                if call.args
            )
        )

    def test_connect_pushes_valid_host_profile_to_robot(self) -> None:
        cli = self._build_cli(connected=False)
        cli._groups_profile = PROFILE_NAME
        cli._wait_for_seq = lambda seq, timeout_sec=None: self._success_event("selectProfile")  # type: ignore[method-assign]
        cli._event_failed = lambda returned, command_name: False  # type: ignore[method-assign]

        def _connect_stub(_session):
            cli._session.connected = True
            return True

        with (
            patch("tools.can_nt.bridge_cli.connect", side_effect=_connect_stub),
            patch("tools.can_nt.bridge_cli.select_profile", return_value=31) as mock_select,
            patch.object(cli, "_query_robot_selected_profile_after_connect") as mock_query,
        ):
            result = cli._exec_command(["connect"])

        self.assertEqual(result.code, SS__NORMAL)
        mock_select.assert_called_once_with(cli._session, PROFILE_NAME)
        mock_query.assert_not_called()
        self.assertEqual(PROFILE_NAME, cli._groups_profile)
        self.assertEqual(PROFILE_NAME, cli._robot_selected_profile)

    def test_connect_pushes_default_host_profile_to_robot_when_no_explicit_selection(self) -> None:
        cli = self._build_cli(connected=False)
        cli._batch = False
        cli._groups_profile = None
        cli._wait_for_seq = lambda seq, timeout_sec=None: self._success_event("selectProfile")  # type: ignore[method-assign]
        cli._event_failed = lambda returned, command_name: False  # type: ignore[method-assign]

        def _connect_stub(_session):
            cli._session.connected = True
            return True

        with (
            patch("tools.can_nt.bridge_cli.connect", side_effect=_connect_stub),
            patch("tools.can_nt.bridge_cli.select_profile", return_value=21) as mock_select,
            patch.object(cli, "_query_robot_selected_profile_after_connect") as mock_query,
        ):
            result = cli._exec_command(["connect"])

        self.assertEqual(result.code, SS__NORMAL)
        self.assertEqual(PROFILE_NAME, cli._groups_profile)
        self.assertEqual(PROFILE_NAME, cli._robot_selected_profile)
        mock_select.assert_called_once_with(cli._session, PROFILE_NAME)
        mock_query.assert_not_called()

    def test_connect_silently_auto_loads_default_profiles_before_pushing_host_profile(self) -> None:
        cli = BridgeCli(_FakeSession(connected=False), batch=True)
        cli._wait_for_seq = lambda seq, timeout_sec=None: self._success_event("selectProfile")  # type: ignore[method-assign]
        cli._event_failed = lambda returned, command_name: False  # type: ignore[method-assign]

        def _connect_stub(_session):
            cli._session.connected = True
            return True

        payload = {
            KEY_SCHEMA_VERSION: PROFILE_SCHEMA_VERSION,
            KEY_DEFAULT_PROFILE: PROFILE_NAME,
            KEY_PROFILES: {PROFILE_NAME: {KEY_PROFILE_DEVICES: []}},
            KEY_DEVICES: [],
            KEY_TOPOLOGY: {
                KEY_TOPOLOGY_VERSION: 1,
                KEY_TOPOLOGY_SOURCE: TOPOLOGY_SOURCE_LOCAL,
                KEY_TOPOLOGY_PROFILES: {},
            },
            KEY_DATA_VERSION: "test-version",
            KEY_DATA_HASH: EMPTY_STRING,
        }
        bridge_config = {
            KEY_BRIDGE_SCHEMA_VERSION: BRIDGE_CONFIG_SCHEMA_VERSION,
            KEY_BRIDGE_GENERATED_AT: None,
            KEY_BRIDGE_BY_PROFILE: {
                PROFILE_NAME: {
                    KEY_GROUPS: [],
                    KEY_SELECTED_DEVICE: {KEY_DEVICE: EMPTY_STRING, KEY_ENABLED: False},
                }
            },
        }

        def _load_profiles_stub(_path, announce=True):
            cli._local_root_payload = payload
            cli._local_config = bridge_config
            cli._groups_profile = None
            cli._sync_store_from_local()
            return None

        with (
            patch("tools.can_nt.bridge_cli.connect", side_effect=_connect_stub),
            patch("tools.can_nt.bridge_cli.select_profile", return_value=21) as mock_select,
            patch.object(cli._config_repository, "canonical_path", return_value=Path("C:/fake/bringup_system.json")),
            patch("pathlib.Path.exists", return_value=True),
            patch.object(cli, "_load_profiles_from_path", side_effect=_load_profiles_stub) as mock_load,
            patch.object(cli, "_query_robot_selected_profile_after_connect") as mock_query,
        ):
            result = cli._exec_command(["connect"])

        self.assertEqual(SS__NORMAL, result.code)
        mock_load.assert_called_once()
        mock_select.assert_called_once_with(cli._session, PROFILE_NAME)
        mock_query.assert_not_called()
        self.assertEqual(PROFILE_NAME, cli._groups_profile)
        self.assertEqual(PROFILE_NAME, cli._robot_selected_profile)

    def test_connect_adopts_robot_profile_when_no_valid_local_profile_exists(self) -> None:
        cli = self._build_cli(connected=False)
        cli._batch = False
        cli._local_root_payload = {}
        cli._groups_profile = None

        def _connect_stub(_session):
            cli._session.connected = True
            return True

        with (
            patch("tools.can_nt.bridge_cli.connect", side_effect=_connect_stub),
            patch.object(cli, "_query_robot_selected_profile_after_connect", return_value=PROFILE_NAME),
            patch("builtins.print") as mock_print,
        ):
            result = cli._exec_command(["connect"])

        self.assertEqual(result.code, SS__NORMAL)
        self.assertEqual(PROFILE_NAME, cli._robot_selected_profile)
        self.assertIsNone(cli._groups_profile)
        self.assertFalse(
            any("local profiles" in str(call.args[0]) for call in mock_print.call_args_list if call.args)
        )
        self.assertFalse(
            any("keeping host context" in str(call.args[0]) for call in mock_print.call_args_list if call.args)
        )

    def test_connect_interactive_prompts_before_switching_host_context(self) -> None:
        cli = self._build_cli(connected=False)
        cli._batch = False
        cli._groups_profile = "local-profile"

        def _connect_stub(_session):
            cli._session.connected = True
            return True

        with (
            patch("tools.can_nt.bridge_cli.connect", side_effect=_connect_stub),
            patch.object(cli, "_query_robot_selected_profile_after_connect", return_value=PROFILE_NAME),
            patch.object(cli, "_confirm_yes_default", return_value=True) as mock_confirm,
        ):
            result = cli._exec_command(["connect"])

        self.assertEqual(result.code, SS__NORMAL)
        self.assertEqual(PROFILE_NAME, cli._groups_profile)
        self.assertEqual(PROFILE_NAME, cli._robot_selected_profile)
        mock_confirm.assert_called_once()

    def test_execute_line_connect_uses_ast_connect_and_pushes_default_host_profile(self) -> None:
        cli = self._build_cli(connected=False)
        cli._batch = False
        cli._groups_profile = None
        cli._wait_for_seq = lambda seq, timeout_sec=None: self._success_event("selectProfile")  # type: ignore[method-assign]
        cli._event_failed = lambda returned, command_name: False  # type: ignore[method-assign]

        def _connect_stub(_session):
            cli._session.connected = True
            return True

        with (
            patch("tools.can_nt.bridge_cli_ast.connect", side_effect=_connect_stub),
            patch.object(cli._session, "ensure_handshake", return_value=True),
            patch("tools.can_nt.bridge_cli.select_profile", return_value=21) as mock_select,
            patch.object(cli, "_query_robot_selected_profile_after_connect") as mock_query,
            patch("builtins.print") as mock_print,
        ):
            result = cli._execute_line("connect")

        self.assertEqual(SS__NORMAL, result.code)
        mock_select.assert_called_once_with(cli._session, PROFILE_NAME)
        mock_query.assert_not_called()
        self.assertEqual(PROFILE_NAME, cli._groups_profile)
        self.assertEqual(PROFILE_NAME, cli._robot_selected_profile)
        self.assertTrue(
            any("Connected." in str(call.args[0]) for call in mock_print.call_args_list if call.args)
        )

    def test_show_profiles_local_reports_no_selected_context_when_none_chosen(self) -> None:
        cli = self._build_cli()
        cli._groups_profile = None

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = cli._show_local_profiles(json_output=False, pretty=False)

        self.assertEqual(SS__NORMAL, result.code)
        self.assertIn("selected=(none)", output.getvalue())
        self.assertIn("active=(none)", output.getvalue())

    def test_execute_line_profile_in_exec_mode_reaches_profile_handler(self) -> None:
        cli = self._build_cli(connected=True)
        ok_event = BridgeEvent(
            type="out",
            seq=1,
            name="selectProfile",
            status="ok",
            message="Selected profile: demo",
            text="Selected profile: demo",
            json_text="",
            ts=0.0,
            session_id="",
            state={},
            raw={},
        )
        cli._wait_for_seq = lambda seq, timeout_sec=None: ok_event  # type: ignore[method-assign]
        cli._event_failed = lambda returned, command_name: False  # type: ignore[method-assign]

        with patch("tools.can_nt.bridge_cli.select_profile", return_value=21):
            result = cli._execute_line("profile demo")

        self.assertEqual(SS__NORMAL, result.code)
        self.assertEqual(PROFILE_NAME, cli._groups_profile)

    def test_set_active_profile_returns_failure_when_robot_blocks_profile_change(self) -> None:
        cli = self._build_cli(connected=True)
        cli._groups_profile = "local-profile"
        blocked_event = BridgeEvent(
            type="out",
            seq=1,
            name="selectProfile",
            status="ok",
            message="Profile change blocked: an active scope session is running. Deactivate scope first.",
            text="Profile change blocked: an active scope session is running. Deactivate scope first.",
            json_text="",
            ts=0.0,
            session_id="",
            state={},
            raw={},
        )
        cli._wait_for_seq = lambda seq, timeout_sec=None: blocked_event  # type: ignore[method-assign]
        cli._event_failed = lambda returned, command_name: False  # type: ignore[method-assign]

        with patch("tools.can_nt.bridge_cli.select_profile", return_value=21):
            result = cli._set_active_profile(PROFILE_NAME)

        self.assertNotEqual(SS__NORMAL, result.code)
        self.assertEqual("local-profile", cli._groups_profile)

    def test_group_mode_active_group_add_is_blocked_while_runtime_scope_is_active(self) -> None:
        cli = self._build_cli(connected=True)
        cli._modes.append(CliMode("group", "active"))
        cli._local_device_exists = lambda _label: True  # type: ignore[method-assign]
        cli._fetch_robot_runtime_payload = lambda print_events=False: {  # type: ignore[method-assign]
            "controlledLifecycleActive": True,
            KEY_ENABLED: True,
            "estopped": False,
            "mode": "teleop",
        }

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = cli._group_command(["add", "device", "FALCON 9"])

        self.assertNotEqual(SS__NORMAL, result.code)
        self.assertIn("Deactivate scope first", output.getvalue())

    def test_group_mode_active_group_add_is_blocked_until_runtime_state_is_loaded(self) -> None:
        cli = self._build_cli(connected=True)
        cli._modes.append(CliMode("group", "active"))
        cli._local_device_exists = lambda _label: True  # type: ignore[method-assign]
        cli._fetch_robot_runtime_payload = lambda print_events=False: None  # type: ignore[method-assign]

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = cli._group_command(["add", "device", "FALCON 9"])

        self.assertNotEqual(SS__NORMAL, result.code)
        self.assertIn("Runtime state not loaded yet", output.getvalue())

    def test_exec_profile_device_show_all_runs_in_exec_mode(self) -> None:
        cli = self._build_cli()
        cli._local_root_payload[KEY_DEVICES] = [  # type: ignore[index]
            {KEY_LABEL: "lmtSw0", KEY_DEVICE_TYPE: "limitSwitch", KEY_ID: 0},
            {KEY_LABEL: "motor1", KEY_DEVICE_TYPE: "motor", KEY_ID: 1},
        ]
        cli._local_root_payload[KEY_PROFILES][PROFILE_NAME][KEY_PROFILE_DEVICES] = [  # type: ignore[index]
            "lmtSw0",
            "lmtSw0",
        ]

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = cli._execute_line("profile device show-all lmtSw0")

        self.assertEqual(SS__NORMAL, result.code)
        text = output.getvalue()
        self.assertIn("Profile device entries:", text)
        self.assertIn("label=lmtSw0", text)
        self.assertIn("Profile device list:", text)
        self.assertIn("lmtSw0 x2", text)

    def test_query_robot_selected_profile_parses_text_fallback(self) -> None:
        cli = self._build_cli(connected=True)
        cli._fetch_robot_runtime_payload = lambda print_events=False: None  # type: ignore[method-assign]
        text_event = BridgeEvent(
            type="out",
            seq=1,
            name="showProfiles",
            status="ok",
            message="OK",
            text="Profile:\n  active=test_minimal_25_9 (inactive)\n  selected=test_minimal_25_9\n",
            json_text="",
            ts=0.0,
            session_id="",
            state={},
            raw={},
        )
        cli._wait_for_seq = lambda seq, timeout_sec=None, print_events=False, suppress_timeout_warning=True: text_event  # type: ignore[method-assign]
        cli._event_failed = lambda returned, command_name: False  # type: ignore[method-assign]

        with patch("tools.can_nt.bridge_cli.show_profiles", return_value=31):
            selected = cli._query_robot_selected_profile()

        self.assertEqual("test_minimal_25_9", selected)

    def test_query_robot_selected_profile_falls_back_to_runtime_state(self) -> None:
        cli = self._build_cli(connected=True)
        cli._fetch_robot_runtime_payload = lambda print_events=False: {"selectedProfile": "test_minimal_25_9"}  # type: ignore[method-assign]

        selected = cli._query_robot_selected_profile()

        self.assertEqual("test_minimal_25_9", selected)

    def test_runtime_deactivate_uses_runtime_command_path(self) -> None:
        cli = self._build_cli(connected=True)
        cli._wait_for_seq = lambda seq, timeout_sec=None: object()  # type: ignore[method-assign]
        cli._event_failed = lambda event, command_name: False  # type: ignore[method-assign]

        with patch("tools.can_nt.bridge_cli.runtime_deactivate", return_value=8):
            result = cli._runtime_deactivate()

        self.assertEqual(result.code, SS__NORMAL)

    def test_show_signals_lists_supported_signals(self) -> None:
        cli = self._build_cli()
        cli._local_root_payload[KEY_DEVICES] = [  # type: ignore[index]
            {"label": "motor1", "type": "motor"},
            {"label": "controller0", "type": "xboxController"},
        ]
        cli._local_root_payload[KEY_PROFILES][PROFILE_NAME][KEY_PROFILE_DEVICES] = ["motor1", "controller0"]  # type: ignore[index]

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = cli._show_local_signals(json_output=True, pretty=False)

        self.assertEqual(result.code, SS__NORMAL)
        payload = json.loads(output.getvalue().splitlines()[-1])
        by_label = {entry["label"]: entry for entry in payload[KEY_DEVICES]}
        self.assertTrue(any(item["name"] == "leftY" for item in by_label["controller0"][KEY_SIGNALS]))
        self.assertTrue(any(item["name"] == "output" for item in by_label["motor1"][KEY_SIGNALS]))
        self.assertTrue(any(item["name"] == "output_percent_cmd" for item in by_label["motor1"][KEY_SIGNALS]))
        self.assertTrue(any(item["name"] == "current_actual" for item in by_label["motor1"][KEY_SIGNALS]))
        self.assertTrue(any(item["name"] == "position_delta" for item in by_label["motor1"][KEY_SIGNALS]))

    def test_show_signal_device_reports_one_device_signals(self) -> None:
        cli = self._build_cli()
        cli._local_root_payload[KEY_DEVICES] = [{"label": "motor1", "type": "motor"}]  # type: ignore[index]

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = cli._show_local_signal_device("motor1", json_output=True, pretty=False)

        self.assertEqual(result.code, SS__NORMAL)
        payload = json.loads(output.getvalue().splitlines()[-1])
        self.assertEqual(payload["label"], "motor1")
        self.assertEqual(payload["type"], "motor")
        self.assertTrue(any(item["name"] == "current" for item in payload[KEY_SIGNALS]))
        self.assertTrue(any(item["name"] == "current_actual" for item in payload[KEY_SIGNALS]))
        self.assertTrue(any(item["name"] == "velocity_actual" for item in payload[KEY_SIGNALS]))
        self.assertTrue(any(item["name"] == "position_actual" for item in payload[KEY_SIGNALS]))

    def test_exec_bindings_show_works(self) -> None:
        cli = self._build_cli()
        cli._bindings_payload = {
            "schema_version": 5,
            "controllers": [{"name": "driver", "type": "XBOX", "port": 0}],
            "bindings": [],
        }

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = cli._exec_command(["bindings", "show"])

        self.assertEqual(result.code, SS__NORMAL)
        self.assertIn("Local bindings config:", output.getvalue())
        self.assertIn("controllers:", output.getvalue())

    def test_parser_accepts_bindings_in_exec_mode(self) -> None:
        parsed = BridgeCliParser().parse("bindings show", mode="exec")

        self.assertEqual(parsed.ast.verb, "bindings")
        self.assertEqual(parsed.ast.kind, "config_bindings")

    def test_exec_bindings_show_all_is_accepted(self) -> None:
        cli = self._build_cli()
        cli._bindings_payload = {
            "controllers": [{"name": "driver", "type": "XBOX", "port": 0}],
            "bindings": [],
        }

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = cli._exec_command(["bindings", "show", "--all"])

        self.assertEqual(result.code, SS__NORMAL)
        self.assertIn("Local bindings config:", output.getvalue())

    def test_bindings_show_question_does_not_suggest_remote_sources(self) -> None:
        cli = self._build_cli()

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            handled = cli._handle_question("bindings show ?")

        self.assertTrue(handled)
        text = output.getvalue()
        self.assertIn("--all", text)
        self.assertIn("--json", text)
        self.assertIn("--pretty", text)
        self.assertNotIn("robot", text)
        self.assertNotIn("local", text)
        self.assertNotIn("both", text)

    def test_exec_bindings_no_controller_form_works(self) -> None:
        cli = self._build_cli()
        cli._bindings_payload = {
            "controllers": [{"name": "driver", "type": "XBOX", "port": 0}],
            "bindings": [],
        }

        result = cli._exec_command(["bindings", "no", "controller", "driver"])

        self.assertEqual(result.code, SS__NORMAL)
        self.assertEqual(cli._bindings_payload["controllers"], [])

    def test_exec_bindings_controller_no_form_kept_for_compatibility(self) -> None:
        cli = self._build_cli()
        cli._bindings_payload = {
            "controllers": [{"name": "driver", "type": "XBOX", "port": 0}],
            "bindings": [],
        }

        result = cli._exec_command(["bindings", "controller", "no", "driver"])

        self.assertEqual(result.code, SS__NORMAL)
        self.assertEqual(cli._bindings_payload["controllers"], [])

    def test_show_bindings_controllers_alias_works(self) -> None:
        cli = self._build_cli()
        cli._bindings_payload = {
            "controllers": [{"name": "driver", "type": "XBOX", "port": 0}],
            "bindings": [],
        }

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = cli._handle_show(["bindings", "controllers"])

        self.assertEqual(result.code, SS__NORMAL)
        self.assertIn("Local bindings config:", output.getvalue())
        self.assertIn("driver", output.getvalue())

    def test_bindings_command_surface_regression(self) -> None:
        cli = self._build_cli()
        parser = BridgeCliParser()
        cli._bindings_payload = {
            "schema_version": 5,
            "controllers": [],
            "bindings": [],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            load_path = temp_path / "bindings_load.json"
            save_path = temp_path / "bindings_save.json"
            load_payload = {
                "schema_version": 5,
                "controllers": [{"name": "xbox1", "type": "XBOX", "port": 2}],
                "bindings": [
                    {
                        "command": "intake",
                        "controller": "xbox1",
                        "input": "button",
                        "id": "B",
                        "mode": "pressed",
                    },
                    {
                        "command": "turn",
                        "controller": "xbox1",
                        "input": "axis",
                        "id": "rightX",
                        "mode": "analog",
                        "invert": False,
                        "deadband": 0.15,
                    }
                ],
            }
            write_profiles_payload(load_path, load_payload, stamp=False)

            command_expectations = [
                ("bindings show", "Local bindings config:"),
                ("bindings show controllers", "controllers:"),
                ("bindings show bindings", "bindings:"),
                ("bindings show --all --json --pretty", "\"controllers\": []"),
                ("bindings controller add xbox0 xbox 0", None),
                ("bindings controller set xbox0 port 1", None),
                ("bindings controller rename xbox0 driver0", None),
                ("bindings binding add stop driver0 button A pressed", None),
                ("bindings binding set 1 mode released", None),
                ("bindings binding add drive driver0 axis leftY analog invert on deadband 0.12", None),
                ("bindings binding set 2 deadband 0.2", None),
                (f"bindings save {save_path}", "Wrote bindings to"),
                (f"bindings validate {save_path}", "OK: Config is valid."),
                ("bindings validate", "OK: Config is valid."),
                ("bindings binding delete 1", None),
                ("bindings binding delete 1", None),
                ("bindings no controller driver0", None),
                (f"bindings load {load_path}", "Loaded bindings:"),
                ("bindings validate", "OK: Config is valid."),
            ]

            for command, expected_text in command_expectations:
                parsed = parser.parse(command, mode="exec")
                self.assertEqual(parsed.ast.verb, "bindings", msg=command)

                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    result = cli._execute_line(command)

                self.assertTrue(result.ok(), msg=f"{command}: {result.code} {output.getvalue()}")
                if expected_text is not None:
                    self.assertIn(expected_text, output.getvalue(), msg=command)

            self.assertEqual(
                cli._bindings_payload,
                {
                    **load_payload,
                    "inputAliases": {},
                },
            )
            saved_payload = load_profiles_payload(save_path)
            self.assertEqual(
                saved_payload,
                {
                    "schema_version": 5,
                    "controllers": [{"name": "driver0", "type": "xbox", "port": 1}],
                    "bindings": [
                        {
                            "command": "stop",
                            "controller": "driver0",
                            "input": "button",
                            "id": "A",
                            "mode": "released",
                        },
                        {
                            "command": "drive",
                            "controller": "driver0",
                            "input": "axis",
                            "id": "leftY",
                            "mode": "analog",
                            "invert": True,
                            "deadband": 0.2,
                        }
                    ],
                    "inputAliases": {},
                },
            )

    def test_parser_accepts_group_bind_diagnostics_commands(self) -> None:
        parser = BridgeCliParser()

        self.assertEqual(parser.parse("bind list", mode="group").tokens, ["bind", "list"])
        self.assertEqual(
            parser.parse("bind explain controller0.leftY", mode="group").tokens,
            ["bind", "explain", "controller0.leftY"],
        )
        self.assertEqual(
            parser.parse("bind test 1", mode="group").tokens,
            ["bind", "test", "1"],
        )

    def test_group_bind_list_and_explain_work(self) -> None:
        cli = self._build_cli()
        cli._modes = [CliMode("group", group="motion")]
        cli._bindings_payload = {
            "controllers": [{"name": "controller0", "type": "XBOX", "port": 0}],
            "bindings": [],
        }
        cli._local_root_payload[KEY_DEVICES] = [{"label": "motor1", "type": "motor"}]  # type: ignore[index]
        cli._local_config[KEY_BRIDGE_BY_PROFILE][PROFILE_NAME][KEY_GROUPS] = [  # type: ignore[index]
            {
                "name": "motion",
                "enabled": True,
                "members": [{"label": "motor1", "enabled": True}],
                "bindings": [{"input": "controller0.leftY", "kind": "analog"}],
            }
        ]

        list_output = io.StringIO()
        with contextlib.redirect_stdout(list_output):
            list_result = cli._execute_line("bind list")

        explain_output = io.StringIO()
        with contextlib.redirect_stdout(explain_output):
            explain_result = cli._execute_line("bind explain 1")

        self.assertEqual(list_result.code, SS__NORMAL)
        self.assertIn("Binding diagnostics:", list_output.getvalue())
        self.assertIn("status=ACTIVE", list_output.getvalue())
        self.assertEqual(explain_result.code, SS__NORMAL)
        self.assertIn("Binding 1", explain_output.getvalue())
        self.assertIn("status: ACTIVE", explain_output.getvalue())

    def test_group_bind_test_fails_for_unresolved_binding(self) -> None:
        cli = self._build_cli()
        cli._modes = [CliMode("group", group="motion")]
        cli._bindings_payload = {
            "controllers": [],
            "bindings": [],
        }
        cli._local_config[KEY_BRIDGE_BY_PROFILE][PROFILE_NAME][KEY_GROUPS] = [  # type: ignore[index]
            {
                "name": "motion",
                "enabled": True,
                "members": [],
                "bindings": [{"input": "missing0.leftY", "kind": "analog"}],
            }
        ]

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = cli._execute_line("bind test 1")

        self.assertEqual(result.code, SS__CONFIG__INVALID)
        self.assertIn("Binding test result: FAIL", output.getvalue())
        self.assertIn("controller not found", output.getvalue())

    def test_group_bind_list_reports_blocked_when_all_members_disabled(self) -> None:
        cli = self._build_cli()
        cli._modes = [CliMode("group", group="motion")]
        cli._bindings_payload = {
            "controllers": [{"name": "controller0", "type": "XBOX", "port": 0}],
            "bindings": [],
        }
        cli._local_config[KEY_BRIDGE_BY_PROFILE][PROFILE_NAME][KEY_GROUPS] = [  # type: ignore[index]
            {
                "name": "motion",
                "enabled": True,
                "members": [{"label": "motor1", "enabled": False}],
                "bindings": [{"input": "controller0.leftY", "kind": "analog"}],
            }
        ]

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = cli._execute_line("bind list")

        self.assertEqual(result.code, SS__NORMAL)
        self.assertIn("status=BLOCKED", output.getvalue())
        self.assertIn("group has no enabled members", output.getvalue())

    def test_group_bind_question_help_uses_diagnostic_specific_suggestions(self) -> None:
        cli = self._build_cli()
        cli._modes = [CliMode("group", group="motion")]
        cli._bindings_payload = {
            "controllers": [{"name": "controller0", "type": "XBOX", "port": 0}],
            "bindings": [],
        }
        cli._local_config[KEY_BRIDGE_BY_PROFILE][PROFILE_NAME][KEY_GROUPS] = [  # type: ignore[index]
            {
                "name": "motion",
                "enabled": True,
                "members": [{"label": "motor1", "enabled": True}],
                "bindings": [{"input": "controller0.leftY", "kind": "analog"}],
            }
        ]

        list_output = io.StringIO()
        with contextlib.redirect_stdout(list_output):
            list_handled = cli._handle_question("bind list ?")

        explain_output = io.StringIO()
        with contextlib.redirect_stdout(explain_output):
            explain_handled = cli._handle_question("bind explain ?")

        test_output = io.StringIO()
        with contextlib.redirect_stdout(test_output):
            test_handled = cli._handle_question("bind test ?")

        self.assertTrue(list_handled)
        self.assertTrue(explain_handled)
        self.assertTrue(test_handled)
        self.assertIn("(none)", list_output.getvalue())
        self.assertNotIn("analog", explain_output.getvalue())
        self.assertIn("1", explain_output.getvalue())
        self.assertIn("controller0.leftY", explain_output.getvalue())
        self.assertNotIn("analog", test_output.getvalue())
        self.assertIn("1", test_output.getvalue())
        self.assertIn("controller0.leftY", test_output.getvalue())

    def test_group_bind_top_level_suggestions_include_input_placeholder(self) -> None:
        cli = self._build_cli()
        cli._modes = [CliMode("group", group="motion")]

        suggestions = cli._suggest_group_bind_args([])

        self.assertIn("list", suggestions)
        self.assertIn("explain", suggestions)
        self.assertIn("test", suggestions)
        self.assertIn("<input>", suggestions)

    def test_bindings_show_robot_is_rejected(self) -> None:
        cli = self._build_cli()
        cli._bindings_payload = {"controllers": [], "bindings": []}

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = cli._execute_line("bindings show robot")

        self.assertNotEqual(result.code, SS__NORMAL)
        self.assertIn("bindings show is local-only", output.getvalue())

    def test_bindings_invalid_controller_port_is_rejected(self) -> None:
        cli = self._build_cli()
        cli._bindings_payload = {
            "controllers": [{"name": "driver0", "type": "XBOX", "port": 0}],
            "bindings": [],
        }

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = cli._execute_line("bindings controller set driver0 port notanint")

        self.assertNotEqual(result.code, SS__NORMAL)
        self.assertIn("controller port must be an integer", output.getvalue())

    def test_bindings_invalid_deadband_is_rejected(self) -> None:
        cli = self._build_cli()
        cli._bindings_payload = {
            "controllers": [{"name": "driver0", "type": "XBOX", "port": 0}],
            "bindings": [],
        }

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = cli._execute_line("bindings binding add drive driver0 axis leftY analog invert on deadband 9.9")

        self.assertNotEqual(result.code, SS__NORMAL)
        self.assertIn("deadband must be 0.0 to 1.0", output.getvalue())

    def test_bindings_delete_referenced_controller_is_rejected(self) -> None:
        cli = self._build_cli()
        cli._bindings_payload = {
            "controllers": [{"name": "driver0", "type": "XBOX", "port": 0}],
            "bindings": [
                {
                    "command": "stop",
                    "controller": "driver0",
                    "input": "button",
                    "id": "A",
                    "mode": "pressed",
                }
            ],
        }

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = cli._execute_line("bindings no controller driver0")

        self.assertNotEqual(result.code, SS__NORMAL)
        self.assertIn("controller is referenced by bindings", output.getvalue())

    def test_bindings_load_malformed_json_is_rejected(self) -> None:
        cli = self._build_cli()
        cli._bindings_payload = {"controllers": [], "bindings": []}

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "broken_bindings.json"
            path.write_text("{not-json", encoding="utf-8")

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = cli._execute_line(f"bindings load {path}")

        self.assertNotEqual(result.code, SS__NORMAL)
        self.assertIn("Failed to read bindings", output.getvalue())

    def test_bindings_edit_marks_dirty_and_show_dirty_reports_it(self) -> None:
        cli = self._build_cli()
        cli._bindings_payload = {"controllers": [], "bindings": []}

        edit_result = cli._execute_line("bindings controller add driver0 XBOX 0")
        dirty_output = io.StringIO()
        with contextlib.redirect_stdout(dirty_output):
            show_result = cli._show_local_config_dirty(json_output=False, pretty=False)

        self.assertEqual(edit_result.code, SS__NORMAL)
        self.assertEqual(show_result.code, SS__NORMAL)
        self.assertIn("bindings=true", dirty_output.getvalue())

    def test_show_bindings_all_json_includes_global_bindings_payload(self) -> None:
        cli = self._build_cli()
        cli._bindings_payload = {
            "controllers": [{"name": "driver0", "type": "XBOX", "port": 0}],
            "bindings": [],
        }
        cli._local_config[KEY_BRIDGE_BY_PROFILE][PROFILE_NAME][KEY_GROUPS] = [  # type: ignore[index]
            {
                "name": "motion",
                "enabled": True,
                "members": [],
                "bindings": [{"input": "controller0.leftY", "kind": "analog"}],
            }
        ]

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = cli._handle_show(["bindings", "--all", "--json", "--pretty"])

        self.assertEqual(result.code, SS__NORMAL)
        payload = json.loads("\n".join(output.getvalue().splitlines()[1:]))
        self.assertIn(KEY_GLOBAL_BINDINGS, payload)
        self.assertEqual(payload[KEY_GLOBAL_BINDINGS]["controllers"][0]["name"], "driver0")

    def test_execute_line_tiu_on_enables_mode(self) -> None:
        cli = self._build_cli()

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = cli._execute_line("tiu on")

        self.assertEqual(result.code, SS__NORMAL)
        self.assertTrue(cli._tiu_enabled)
        self.assertIn("(tiu)", cli._prompt())
        self.assertIn("TIU mode enabled.", output.getvalue())

    def test_execute_line_tiu_off_disables_mode(self) -> None:
        cli = self._build_cli()
        cli._tiu_enabled = True

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = cli._execute_line("tiu off")

        self.assertEqual(result.code, SS__NORMAL)
        self.assertFalse(cli._tiu_enabled)
        self.assertNotIn("(tiu)", cli._prompt())
        self.assertIn("TIU mode disabled.", output.getvalue())

    def test_tiu_dashboard_includes_last_modified(self) -> None:
        cli = self._build_cli()
        cli._tiu_enabled = True
        cli._last_modified_at = 1.0

        lines = cli._tiu_dashboard_lines()
        joined = "\n".join(lines)

        self.assertIn("Last modified:", joined)
        self.assertIn("HOST", joined)
        self.assertIn("SAVE / PUSH", joined)

    def test_tiu_status_text_is_compact_summary(self) -> None:
        cli = self._build_cli()
        cli._tiu_enabled = True

        text = cli._tiu_status_text()

        self.assertIn("host:", text)
        self.assertIn("robot:", text)
        self.assertIn("runtime:", text)
        self.assertIn("devices:", text)
        self.assertIn("events:", text)

    def test_tiu_capture_keeps_command_output_in_dashboard_buffer(self) -> None:
        cli = self._build_cli()
        cli._tiu_enabled = True
        cli._render_tiu_if_needed = lambda: None  # type: ignore[method-assign]

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = cli._execute_line_with_tiu_capture("show workspace --json")

        self.assertEqual(result.code, SS__NORMAL)
        self.assertEqual(output.getvalue(), EMPTY_STRING)
        self.assertTrue(any("profiles" in line for line in cli._tiu_cli_output))

    def test_tiu_dashboard_respects_terminal_height(self) -> None:
        cli = self._build_cli()
        cli._tiu_enabled = True
        cli._tiu_recent_events = [f"event {idx}" for idx in range(10)]
        cli._tiu_cli_output = [f"output {idx}" for idx in range(20)]
        cli._tiu_runtime_cache = {
            KEY_PROFILE: PROFILE_NAME,
            KEY_DEVICES: [{"label": f"motor{idx}", "instantiated": True} for idx in range(10)],
        }
        cli._tiu_runtime_cache_at = 1.0

        original_get_terminal_size = shutil.get_terminal_size
        try:
            shutil.get_terminal_size = lambda _fallback=(80, 24): os.terminal_size((80, 18))  # type: ignore[assignment]
            lines = cli._tiu_dashboard_lines()
        finally:
            shutil.get_terminal_size = original_get_terminal_size  # type: ignore[assignment]

        self.assertLessEqual(len(lines), 12)

    def test_tiu_prompt_row_uses_terminal_bottom_margin(self) -> None:
        cli = self._build_cli()

        original_get_terminal_size = shutil.get_terminal_size
        try:
            shutil.get_terminal_size = lambda _fallback=(80, 24): os.terminal_size((80, 22))  # type: ignore[assignment]
            row = cli._tiu_prompt_row()
        finally:
            shutil.get_terminal_size = original_get_terminal_size  # type: ignore[assignment]

        self.assertEqual(row, 20)

    def test_tiu_refresh_preserves_output_cursor_when_not_following_tail(self) -> None:
        cli = self._build_cli()
        cli._tiu_output_view = _FakeTextArea(text="alpha\nbeta\ngamma", cursor_position=4)
        cli._tiu_cli_output = ["alpha", "beta", "gamma", "delta"]
        cli._tiu_output_follow_tail = False
        cli._tiu_output_view.window.vertical_scroll = 2

        cli._refresh_tiu_views()

        self.assertEqual(cli._tiu_output_view.buffer.cursor_position, 11)
        self.assertEqual(cli._tiu_output_view.window.vertical_scroll, 2)

    def test_tiu_refresh_moves_output_cursor_to_end_when_following_tail(self) -> None:
        cli = self._build_cli()
        cli._tiu_output_view = _FakeTextArea(text="alpha\nbeta", cursor_position=0)
        cli._tiu_cli_output = ["alpha", "beta", "gamma"]
        cli._tiu_output_follow_tail = True

        cli._refresh_tiu_views()

        self.assertEqual(cli._tiu_output_view.buffer.cursor_position, len(cli._tiu_output_view.text))
        self.assertEqual(cli._tiu_output_view.window.vertical_scroll, 2)

    def test_tiu_commit_input_line_resets_buffer_with_history(self) -> None:
        text_area = _FakeTextArea(text="  show devices  ")

        line = BridgeCli._tiu_commit_input_line(text_area)

        self.assertEqual(line, "show devices")
        self.assertTrue(text_area.buffer.appended)
        self.assertEqual(text_area.buffer.reset_calls, [True])

    def test_tiu_history_regression_preserves_most_recent_order(self) -> None:
        history = InMemoryHistory()
        text_area = TextArea(multiline=False, history=history)

        for command in ["show devices", "show groups", "show workspace"]:
            text_area.text = command
            BridgeCli._tiu_commit_input_line(text_area)

        buffer = text_area.buffer
        seen = []
        for _ in range(3):
            buffer.history_backward()
            seen.append(buffer.text)

        self.assertEqual(seen, ["show workspace", "show groups", "show devices"])

    def test_execute_line_revert_uses_reload_sources(self) -> None:
        cli = self._build_cli()
        cli._mark_profiles_dirty()
        calls: list[str] = []

        def _fake_load_sources():
            calls.append("load")
            cli._profiles_dirty = False
            return StatusResult(code=SS__NORMAL)

        cli._load_sources = _fake_load_sources  # type: ignore[method-assign]

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = cli._execute_line("revert")

        self.assertEqual(result.code, SS__NORMAL)
        self.assertEqual(calls, ["load"])
        self.assertIn("Revert complete", output.getvalue())


if __name__ == "__main__":
    unittest.main()
