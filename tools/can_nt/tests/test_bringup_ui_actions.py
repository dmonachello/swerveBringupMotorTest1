"""
NAME
    test_bringup_ui_actions.py - Unit tests for merged Bringup UI action metadata.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tools.can_nt.bridge_session import BridgeEvent
from tools.can_nt.bringup_ui import (
    ACTION_KIND_REMOTE_COMMAND,
    ACTIONS_BY_NAME,
    ACTION_SOURCE_ROBOT,
    BringupControlUI,
    COMMAND_PRINT_SELECTED_TEST_SOURCE,
    INVENTORY_KEY_ACTION_KIND,
    INVENTORY_KEY_SOURCE,
    _load_tests_from_dsl_store,
    _action_sections,
    _merge_host_ui_actions,
)
from tools.can_nt.host_ui_actions import (
    ACTION_KIND_HOST_LOCAL,
    ACTION_SOURCE_HOST,
    HOST_ACTION_DSL_TEST_IMPORT,
    HOST_ACTION_DSL_TEST_VALIDATE,
    HOST_ACTION_RECONNECT_UI_SESSION,
    HOST_UI_ACTIONS,
)


class BringupUiActionMetadataTests(unittest.TestCase):
    """
    NAME
        BringupUiActionMetadataTests - Validate merged robot and host action metadata.
    """

    def test_merge_host_actions_preserves_both_sources(self) -> None:
        robot_actions = [
            {
                "name": "uiDisconnect",
                "showInHostUi": True,
                "uiSection": "Session",
                "uiLabel": "Release UI Lock",
                "uiDescription": "Release the active UI lock.",
            }
        ]

        actions_by_name, sections = _merge_host_ui_actions(robot_actions, HOST_UI_ACTIONS)

        self.assertEqual(
            actions_by_name["uiDisconnect"][INVENTORY_KEY_ACTION_KIND],
            ACTION_KIND_REMOTE_COMMAND,
        )
        self.assertEqual(
            actions_by_name["uiDisconnect"][INVENTORY_KEY_SOURCE], ACTION_SOURCE_ROBOT
        )
        self.assertEqual(
            actions_by_name[HOST_ACTION_RECONNECT_UI_SESSION][INVENTORY_KEY_ACTION_KIND],
            ACTION_KIND_HOST_LOCAL,
        )
        self.assertEqual(
            actions_by_name[HOST_ACTION_RECONNECT_UI_SESSION][INVENTORY_KEY_SOURCE],
            ACTION_SOURCE_HOST,
        )
        self.assertTrue(any(section.get("section") == "Session" for section in sections))

    def test_reconnect_action_is_present_in_loaded_action_metadata(self) -> None:
        self.assertIn(HOST_ACTION_RECONNECT_UI_SESSION, ACTIONS_BY_NAME)
        self.assertEqual(
            ACTIONS_BY_NAME[HOST_ACTION_RECONNECT_UI_SESSION][INVENTORY_KEY_ACTION_KIND],
            ACTION_KIND_HOST_LOCAL,
        )

    def test_dsl_host_actions_are_present_in_loaded_action_metadata(self) -> None:
        self.assertIn(HOST_ACTION_DSL_TEST_IMPORT, ACTIONS_BY_NAME)
        self.assertIn(HOST_ACTION_DSL_TEST_VALIDATE, ACTIONS_BY_NAME)
        self.assertEqual(
            ACTIONS_BY_NAME[HOST_ACTION_DSL_TEST_IMPORT][INVENTORY_KEY_ACTION_KIND],
            ACTION_KIND_HOST_LOCAL,
        )
        self.assertEqual(
            ACTIONS_BY_NAME[HOST_ACTION_DSL_TEST_VALIDATE][INVENTORY_KEY_ACTION_KIND],
            ACTION_KIND_HOST_LOCAL,
        )

    def test_action_sections_exclude_remote_commands_not_allowed_for_host_ui(self) -> None:
        sections = _action_sections()
        flattened = [command for _section, items in sections for _label, command in items]
        self.assertNotIn("canSweep", flattened)

    def test_load_tests_from_dsl_store_prefers_profile_test_set(self) -> None:
        payload = {
            "default_profile": "home",
            "profiles": {
                "home": {
                    "devices": [],
                    "dslTestSet": "pit",
                }
            },
            "dslTests": {
                "schemaVersion": 1,
                "defaultSet": "default",
                "testSets": {
                    "default": ["spin_default"],
                    "pit": ["pit_smoke", "pit_limit"],
                },
                "testsByName": {
                    "spin_default": {"source": "", "sourceHash": "", "normalized": {}},
                    "pit_smoke": {"source": "", "sourceHash": "", "normalized": {}},
                    "pit_limit": {"source": "", "sourceHash": "", "normalized": {}},
                },
            },
        }

        class _FakeSnapshot:
            def to_payload(self):
                return payload

        class _FakeRepository:
            def load_canonical(self):
                return _FakeSnapshot()

        with patch("tools.can_nt.bringup_ui.ConfigRepository", _FakeRepository):
            names = _load_tests_from_dsl_store("home")

        self.assertEqual(["pit_smoke", "pit_limit"], names)


class _FakeCombobox:
    def __init__(self, values: list[str], selected: str) -> None:
        self._values = list(values)
        self._selected = selected

    def get(self) -> str:
        return self._selected

    def set(self, value: str) -> None:
        self._selected = value

    def cget(self, key: str):
        if key == "values":
            return tuple(self._values)
        raise KeyError(key)

    def __setitem__(self, key: str, value) -> None:
        if key != "values":
            raise KeyError(key)
        self._values = list(value)


class _FakeTracker:
    def __init__(self) -> None:
        self.pending = False
        self.events: list[object] = []

    def is_pending(self) -> bool:
        return self.pending

    def handle_event(self, event: object) -> None:
        self.events.append(event)


class BringupUiSelectedTestSyncTests(unittest.TestCase):
    """
    NAME
        BringupUiSelectedTestSyncTests - Cover selected-test/profile sync behavior in the UI.
    """

    def _ui(self) -> BringupControlUI:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._test_box = _FakeCombobox(["spark25_leftY", "falcon9_leftY"], "spark25_leftY")
        ui._last_selected_test = "spark25_leftY"
        ui._robot_selected_test_name = "Swerve Krakens Left Joystick"
        ui._pending_selected_test_command = None
        ui._tcp_connected = True
        ui._tracker = _FakeTracker()
        ui._session = object()
        ui._last_sent_seq = None
        ui._last_cmd = None
        ui._test_log_followup_until = 0.0
        ui._runtime_state_pending_seq = None
        ui._log_poll_seq = None
        ui._log_poll_inflight = False
        ui._notify_ui_failure = lambda *_args, **_kwargs: None
        ui._apply_live_runtime_notice_from_ack = lambda *_args, **_kwargs: None
        ui._apply_runtime_group_command_payload = lambda *_args, **_kwargs: None
        ui._remember_out_line = lambda _line: None
        ui._request_runtime_state_refresh = lambda: None
        ui.after_idle = lambda func: func()
        ui._is_handshake_required = lambda _event: False
        ui._is_owner_required = lambda _event: False
        ui._runtime_state_pending_at = 0.0
        ui._handshake_done = True
        ui._append_output = lambda _line: None
        ui._send_tcp_command = lambda _command, _args: 99
        return ui

    def test_sync_test_selection_ignores_robot_test_outside_current_profile_choices(self) -> None:
        ui = self._ui()

        ui._sync_test_selection("Swerve Krakens Left Joystick")

        self.assertEqual("spark25_leftY", ui._test_box.get())
        self.assertEqual("spark25_leftY", ui._last_selected_test)

    def test_selected_test_action_defers_until_robot_selection_is_synced(self) -> None:
        ui = self._ui()
        sent_commands: list[tuple[str, object]] = []

        def _fake_send_tracked_command(_session, _tracker, command, args, sender, now):
            sent_commands.append((command, args))
            return 17

        with patch("tools.can_nt.bringup_ui.send_tracked_command", _fake_send_tracked_command):
            ui._on_action(COMMAND_PRINT_SELECTED_TEST_SOURCE)

        self.assertEqual(
            [( "selectTestByName", {"name": "spark25_leftY"})],
            sent_commands,
        )
        self.assertEqual(
            (COMMAND_PRINT_SELECTED_TEST_SOURCE, None),
            ui._pending_selected_test_command,
        )

    def test_dispatch_pending_selected_test_command_sends_deferred_command(self) -> None:
        ui = self._ui()
        ui._pending_selected_test_command = (COMMAND_PRINT_SELECTED_TEST_SOURCE, None)
        sent_commands: list[tuple[str, object]] = []

        def _fake_send_tracked_command(_session, _tracker, command, args, sender, now):
            sent_commands.append((command, args))
            return 23

        with patch("tools.can_nt.bringup_ui.send_tracked_command", _fake_send_tracked_command):
            dispatched = ui._dispatch_pending_selected_test_command()

        self.assertTrue(dispatched)
        self.assertEqual([(COMMAND_PRINT_SELECTED_TEST_SOURCE, None)], sent_commands)
        self.assertIsNone(ui._pending_selected_test_command)
        self.assertEqual((COMMAND_PRINT_SELECTED_TEST_SOURCE, None), ui._last_cmd)
        self.assertEqual(23, ui._last_sent_seq)

    def test_run_test_out_arms_followup_log_poll_window(self) -> None:
        ui = self._ui()
        requested: list[str] = []
        ui._request_ui_log_poll_now = lambda: requested.append("poll")
        event = BridgeEvent(
            type="out",
            seq=55,
            name="runTest",
            status="ok",
            message="OK",
            text="runTest",
            json_text="",
            ts=0.0,
            session_id="s",
            state={},
            raw={},
        )

        ui._handle_tcp_response(event)

        self.assertGreater(ui._test_log_followup_until, 0.0)
        self.assertEqual(["poll"], requested)


if __name__ == "__main__":
    unittest.main()
