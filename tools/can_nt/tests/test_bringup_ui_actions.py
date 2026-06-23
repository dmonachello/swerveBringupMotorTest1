"""
NAME
    test_bringup_ui_actions.py - Unit tests for merged Bringup UI action metadata.
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from tools.can_nt.bringup_ui import (
    ACTION_KIND_REMOTE_COMMAND,
    ACTIONS_BY_NAME,
    ACTION_SOURCE_ROBOT,
    BringupControlUI,
    CMD_SHOW_LIFECYCLE_STATE,
    GROUP_ACTIVE_NAME,
    HIDDEN_LEFT_RAIL_COMMANDS,
    INVENTORY_KEY_ACTION_KIND,
    INVENTORY_KEY_SOURCE,
    KEY_TYPE,
    PROFILE_NONE,
    TEST_SOURCE_COMPLETION_MODE_CLEAR,
    TEST_SOURCE_COMPLETION_MODE_NONE,
    TEST_SOURCE_COMPLETION_MODE_READ,
    TEST_SOURCE_COMPLETION_MODE_WRITE,
    _load_tests_from_dsl_store,
    _action_sections,
    _merge_host_ui_actions,
)
from tools.can_nt.bridge_session import BridgeEvent
from tools.can_nt.host_ui_actions import (
    ACTION_KIND_HOST_LOCAL,
    ACTION_SOURCE_HOST,
    HOST_ACTION_DSL_TEST_IMPORT,
    HOST_ACTION_DSL_TEST_VALIDATE,
    HOST_ACTION_RECONNECT_UI_SESSION,
    HOST_UI_ACTIONS,
)


class _ProfileBoxStub:
    def __init__(self, value: str, values=()) -> None:
        self._value = value
        self._values = tuple(values)

    def get(self) -> str:
        return self._value

    def set(self, value: str) -> None:
        self._value = value

    def cget(self, key: str):
        if key == "values":
            return self._values
        raise KeyError(key)


class _StringVarStub:
    def __init__(self, value: str = "") -> None:
        self._value = value

    def get(self) -> str:
        return self._value

    def set(self, value: str) -> None:
        self._value = value


class _ComboBoxStub:
    def __init__(self, values=()) -> None:
        self._values = tuple(values)

    def cget(self, key: str):
        if key == "values":
            return self._values
        raise KeyError(key)

    def __setitem__(self, key: str, value) -> None:
        if key != "values":
            raise KeyError(key)
        self._values = tuple(value)


class _EntryStub:
    def __init__(self, value: str) -> None:
        self._value = value

    def getString(self, default: str) -> str:
        return self._value or default

    def getDouble(self, default: float) -> float:
        try:
            return float(self._value)
        except Exception:
            return default

    def getBoolean(self, default: bool) -> bool:
        return bool(self._value) if self._value is not None else default


class _SubTableStub:
    def __init__(self, entries=None, rows=None) -> None:
        self._entries = dict(entries or {})
        self._rows = dict(rows or {})

    def getEntry(self, key: str):
        return _EntryStub(self._entries.get(key))

    def getSubTable(self, key: str):
        return self._rows[key]


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
        for hidden_command in HIDDEN_LEFT_RAIL_COMMANDS:
            self.assertNotIn(hidden_command, flattened)

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

    def test_test_activity_classifier_recognizes_test_commands(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)

        self.assertTrue(ui._is_test_activity_command("runTest"))
        self.assertTrue(ui._is_test_activity_command("printTestsOverview"))
        self.assertFalse(ui._is_test_activity_command("runtimeActivate"))

    def test_selected_test_library_entry_prefers_profile_selection(self) -> None:
        class _Listbox:
            def __init__(self, items, selection):
                self._items = items
                self._selection = selection

            def curselection(self):
                return self._selection

            def get(self, index):
                return self._items[index]

        ui = BringupControlUI.__new__(BringupControlUI)
        ui._test_library_global_list = _Listbox(["global_a"], (0,))
        ui._test_library_profile_list = _Listbox(["profile_a"], (0,))

        self.assertEqual(("profile_a", "profile"), ui._selected_test_library_entry())

    def test_robot_tests_table_replaces_selected_test_dropdown_values(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._selected_test_var = _StringVarStub("local_only_test")
        ui._last_selected_test = "local_only_test"
        ui._test_box = _ComboBoxStub(("local_only_test", "other_local"))
        ui._tests_tab_test_box = _ComboBoxStub(("local_only_test", "other_local"))
        ui._tests_table = _SubTableStub(
            entries={"totalCount": "2"},
            rows={
                "rows": None,
                "0": _SubTableStub(entries={"name": "robot_test_a", "selected": False}),
                "1": _SubTableStub(entries={"name": "robot_test_b", "selected": True}),
            },
        )
        rows = {
            "0": _SubTableStub(entries={"name": "robot_test_a", "selected": False}),
            "1": _SubTableStub(entries={"name": "robot_test_b", "selected": True}),
        }
        ui._tests_table = _SubTableStub(entries={"totalCount": "2"}, rows={"rows": _SubTableStub(rows=rows)})

        ui._sync_test_dropdown_values(ui._resolve_test_names_from_rows())

        self.assertEqual(("robot_test_a", "robot_test_b"), ui._test_box.cget("values"))
        self.assertEqual(("robot_test_a", "robot_test_b"), ui._tests_tab_test_box.cget("values"))
        self.assertEqual("robot_test_a", ui._selected_test_var.get())

    def test_sync_test_dropdown_keeps_robot_selected_name_when_rows_are_empty(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._selected_test_var = _StringVarStub(PROFILE_NONE)
        ui._last_selected_test = PROFILE_NONE
        ui._test_box = _ComboBoxStub((PROFILE_NONE,))
        ui._tests_tab_test_box = _ComboBoxStub((PROFILE_NONE,))
        ui._tests_table = _SubTableStub(entries={"totalCount": "0"}, rows={"rows": _SubTableStub(rows={})})
        ui._sync_test_dropdown_values([])
        selected_name = "test_minimal_25_9_spark25_leftY"
        names = ui._resolve_test_names_from_rows()
        if selected_name and selected_name != PROFILE_NONE and selected_name not in names:
            names = names + [selected_name]
        ui._sync_test_dropdown_values(names)
        ui._sync_test_selection(selected_name)

        self.assertEqual((selected_name,), ui._test_box.cget("values"))
        self.assertEqual((selected_name,), ui._tests_tab_test_box.cget("values"))
        self.assertEqual(selected_name, ui._selected_test_var.get())

    def test_on_test_source_key_release_rechecks_completion_every_time(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._refresh_test_source_line_numbers = lambda: None
        called = []
        ui._show_test_source_completion_popup = lambda: called.append("show")

        ui._on_test_source_key_release(type("Event", (), {"char": "a"})())

        self.assertEqual(["show"], called)

    def test_test_source_completion_mode_for_line_is_context_sensitive(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)

        self.assertEqual(
            TEST_SOURCE_COMPLETION_MODE_WRITE,
            ui._test_source_completion_mode_for_line('    set "FALCON 9".'),
        )
        self.assertEqual(
            TEST_SOURCE_COMPLETION_MODE_WRITE,
            ui._test_source_completion_mode_for_line('unsafe-exit "FALCON 9".output_percent_cmd'),
        )
        self.assertEqual(
            TEST_SOURCE_COMPLETION_MODE_READ,
            ui._test_source_completion_mode_for_line('  require "FALCON 9".'),
        )
        self.assertEqual(
            TEST_SOURCE_COMPLETION_MODE_CLEAR,
            ui._test_source_completion_mode_for_line('clear "pdp".'),
        )
        self.assertEqual(
            TEST_SOURCE_COMPLETION_MODE_NONE,
            ui._test_source_completion_mode_for_line('device "FALCON 9"'),
        )

    def test_selected_profile_signal_names_for_device_label_filters_by_mode(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._test_profile_devices = {
            "falcon 9": {
                KEY_TYPE: "motor",
            }
        }
        fake_catalog = {
            "motor": {
                "position": {"readable": True, "writable": False, "clearable": False},
                "output_percent_cmd": {
                    "readable": True,
                    "writable": True,
                    "clearable": False,
                },
                "faults": {"readable": False, "writable": False, "clearable": True},
            }
        }

        with patch("tools.can_nt.bringup_ui.robot_test_dsl_signal_catalog", return_value=fake_catalog):
            self.assertEqual(
                ["output_percent_cmd", "position"],
                ui._selected_profile_signal_names_for_device_label(
                    "FALCON 9", TEST_SOURCE_COMPLETION_MODE_READ
                ),
            )
            self.assertEqual(
                ["output_percent_cmd"],
                ui._selected_profile_signal_names_for_device_label(
                    "FALCON 9", TEST_SOURCE_COMPLETION_MODE_WRITE
                ),
            )
            self.assertEqual(
                ["faults"],
                ui._selected_profile_signal_names_for_device_label(
                    "FALCON 9", TEST_SOURCE_COMPLETION_MODE_CLEAR
                ),
            )
            self.assertEqual(
                [],
                ui._selected_profile_signal_names_for_device_label(
                    "FALCON 9", TEST_SOURCE_COMPLETION_MODE_NONE
                ),
            )

    def test_selected_profile_signal_names_for_blank_typed_pdp_use_inferred_dsl_type(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._test_profile_devices = {
            "pdp": {
                "manufacturer": 4,
                "deviceType": 8,
                "model": "PDP",
                KEY_TYPE: "",
            }
        }
        fake_catalog = {
            "PDP": {
                "voltage": {"readable": True, "writable": False, "clearable": False},
                "faults": {"readable": False, "writable": False, "clearable": True},
            }
        }

        with patch("tools.can_nt.bringup_ui.robot_test_dsl_signal_catalog", return_value=fake_catalog):
            self.assertEqual(
                ["voltage"],
                ui._selected_profile_signal_names_for_device_label(
                    "pdp", TEST_SOURCE_COMPLETION_MODE_READ
                ),
            )

    def test_profile_device_type_display_prefers_readable_name_with_numeric_code(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)

        self.assertEqual(
            "PDP (8)",
            ui._profile_device_type_display(
                {
                    "manufacturer": 4,
                    "deviceType": 8,
                    "model": "PDP",
                    KEY_TYPE: "",
                }
            ),
        )
        self.assertEqual(
            "motor (2)",
            ui._profile_device_type_display(
                {
                    "manufacturer": 4,
                    "deviceType": 2,
                    "model": "Falcon 500",
                    KEY_TYPE: "motor",
                }
            ),
        )

    def test_lifecycle_activate_from_ui_uses_lifecycle_command_path(self) -> None:
        class _Tracker:
            def is_pending(self) -> bool:
                return False

        ui = BringupControlUI.__new__(BringupControlUI)
        lines = []
        ui._tcp_connected = True
        ui._tracker = _Tracker()
        ui._session = object()
        ui._last_sent_seq = None
        ui._append_output = lines.append

        with patch("tools.can_nt.bringup_ui.send_tracked_command", return_value=21):
            ui._lifecycle_activate_from_ui()

        self.assertEqual(ui._last_cmd[0], "lifecycleActivate")
        self.assertEqual(ui._last_cmd[1]["label"], GROUP_ACTIVE_NAME)
        self.assertEqual(ui._last_sent_seq, 21)
        self.assertTrue(any("lifecycleActivate" in line for line in lines))

    def test_lifecycle_deactivate_from_ui_uses_lifecycle_command_path(self) -> None:
        class _Tracker:
            def is_pending(self) -> bool:
                return False

        ui = BringupControlUI.__new__(BringupControlUI)
        lines = []
        ui._tcp_connected = True
        ui._tracker = _Tracker()
        ui._session = object()
        ui._last_sent_seq = None
        ui._append_output = lines.append

        with patch("tools.can_nt.bringup_ui.send_tracked_command", return_value=22):
            ui._lifecycle_deactivate_from_ui()

        self.assertEqual(ui._last_cmd[0], "lifecycleDeactivate")
        self.assertEqual(ui._last_cmd[1]["label"], GROUP_ACTIVE_NAME)
        self.assertEqual(ui._last_sent_seq, 22)
        self.assertTrue(any("lifecycleDeactivate" in line for line in lines))

    def test_show_lifecycle_state_from_ui_uses_lifecycle_show_command(self) -> None:
        class _Tracker:
            def is_pending(self) -> bool:
                return False

        ui = BringupControlUI.__new__(BringupControlUI)
        lines = []
        ui._tcp_connected = True
        ui._tracker = _Tracker()
        ui._session = object()
        ui._last_sent_seq = None
        ui._append_output = lines.append

        with patch("tools.can_nt.bringup_ui.send_tracked_command", return_value=23):
            ui._show_lifecycle_state_from_ui()

        self.assertEqual(ui._last_cmd[0], CMD_SHOW_LIFECYCLE_STATE)
        self.assertEqual(ui._last_sent_seq, 23)
        self.assertTrue(any(CMD_SHOW_LIFECYCLE_STATE in line for line in lines))

    def test_select_profile_ack_updates_robot_profile_context_immediately(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        synced = []
        ui._robot_selected_profile = "2026_no_swyfts"
        ui._robot_active_runtime_profile = "(none)"
        ui._sync_diagnostic_profile_context = lambda reload_views: synced.append(reload_views)

        ui._apply_robot_profile_context_from_command_event(
            "selectProfile",
            "ok",
            "Selected profile: test_minimal_25_9",
            "",
        )

        self.assertEqual("test_minimal_25_9", ui._robot_selected_profile)
        self.assertEqual([True], synced)

    def test_ui_prompts_to_sync_host_profile_context_to_robot_profile(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._robot_selected_profile = "test_minimal_25_9"
        ui._profile_box = _ProfileBoxStub(
            "2026_no_swyfts",
            values=("2026_no_swyfts", "test_minimal_25_9"),
        )
        ui._last_selected_profile = "2026_no_swyfts"
        ui._last_profile_mismatch_prompt = None
        applied = []
        ui._apply_profile_selection = lambda name, reload_views: applied.append((name, reload_views))

        with patch("tools.can_nt.bringup_ui.messagebox.askyesno", return_value=True) as mock_prompt:
            ui._maybe_prompt_host_profile_context_sync()

        self.assertEqual("test_minimal_25_9", ui._profile_box.get())
        self.assertEqual("test_minimal_25_9", ui._last_selected_profile)
        self.assertEqual([("test_minimal_25_9", True)], applied)
        mock_prompt.assert_called_once()

    def test_ui_adopts_robot_profile_without_prompt_when_local_context_is_empty(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._robot_selected_profile = "test_minimal_25_9"
        ui._profile_box = _ProfileBoxStub(
            "(none)",
            values=("2026_no_swyfts", "test_minimal_25_9", "(none)"),
        )
        ui._last_selected_profile = "(none)"
        ui._last_profile_mismatch_prompt = None
        applied = []
        ui._apply_profile_selection = lambda name, reload_views: applied.append((name, reload_views))

        with patch("tools.can_nt.bringup_ui.messagebox.askyesno") as mock_prompt:
            ui._maybe_prompt_host_profile_context_sync()

        self.assertEqual("test_minimal_25_9", ui._profile_box.get())
        self.assertEqual("test_minimal_25_9", ui._last_selected_profile)
        self.assertEqual([("test_minimal_25_9", True)], applied)
        mock_prompt.assert_not_called()

    def test_live_runtime_notice_suppresses_runtime_inactive_when_lifecycle_active(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        notices = []
        ui._runtime_active_known = False
        ui._controlled_lifecycle_active_known = True
        ui._set_runtime_state_notice = lambda message, level: notices.append((message, level))
        ui._clear_runtime_state_notice = lambda: notices.append(("clear", "clear"))
        ui._iter_live_views = lambda: []

        ui._apply_live_runtime_notice_from_nt_state(
            enabled=True, estopped=False, stale_state=False
        )

        self.assertEqual([("clear", "clear")], notices)

    def test_manual_duty_target_allowed_requires_controlled_active_when_lifecycle_active(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._controlled_lifecycle_active_known = True
        ui._latest_runtime_devices = {
            "falcon 9": {"label": "FALCON 9", "lifecycleState": "controlled-active", "testable": True},
            "sparkmax/neo 25": {
                "label": "SPARKMAX/NEO 25",
                "lifecycleState": "instantiated-present",
                "testable": True,
            },
        }

        self.assertTrue(ui._is_manual_duty_target_allowed("FALCON 9"))
        self.assertFalse(ui._is_manual_duty_target_allowed("SPARKMAX/NEO 25"))

    def test_manual_duty_scope_block_message_reports_outside_controlled_scope(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._controlled_lifecycle_active_known = True
        ui._latest_runtime_devices = {
            "sparkmax/neo 25": {
                "label": "SPARKMAX/NEO 25",
                "lifecycleState": "instantiated-present",
                "testable": True,
            }
        }

        self.assertIn(
            "outside the active controlled lifecycle scope",
            ui._manual_duty_scope_block_message_for_targets(["SPARKMAX/NEO 25"]),
        )

    def test_apply_runtime_state_payload_tracks_controlled_lifecycle_active(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._runtime_active_known = None
        ui._controlled_lifecycle_active_known = None
        ui._robot_selected_profile = ""
        ui._robot_active_runtime_profile = ""
        ui._sync_diagnostic_profile_context = lambda reload_views=True: None
        ui._manual_motion_checks = {}
        ui._manual_test_observations = {}
        ui._latest_runtime_devices = {}
        ui._update_manual_test_observation = lambda label_key, observation: None
        ui._iter_live_views = lambda: []

        ui._apply_runtime_state_payload(
            {
                "runtimeActive": False,
                "controlledLifecycleActive": True,
                "selectedProfile": "test_minimal_25_9",
                "activeRuntimeProfile": "",
                "devices": [],
            }
        )

        self.assertFalse(ui._runtime_active_known)
        self.assertTrue(ui._controlled_lifecycle_active_known)

    def test_active_group_toggle_is_blocked_while_controlled_lifecycle_active(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._controlled_lifecycle_active_known = True
        ui._tcp_connected = True
        ui._append_output_lines = []
        ui._append_output = ui._append_output_lines.append
        ui._request_runtime_state_refresh = lambda: None
        ui.after_idle = lambda callback: callback()
        ui._tracker = type(
            "TrackerStub",
            (),
            {"is_pending": staticmethod(lambda: False)},
        )()
        ui._last_cmd = None
        ui._send_tcp_command = lambda command, args: (_ for _ in ()).throw(
            AssertionError("should not send while controlled lifecycle is active")
        )

        ui._on_active_group_member_toggled("FALCON 9", True)

        self.assertTrue(
            any("locked while controlled lifecycle session is ACTIVE" in line for line in ui._append_output_lines)
        )

if __name__ == "__main__":
    unittest.main()
