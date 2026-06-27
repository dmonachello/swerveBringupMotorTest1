"""
NAME
    test_bringup_ui_actions.py - Unit tests for merged Bringup UI action metadata.
"""

from __future__ import annotations

import time
import unittest
from unittest.mock import patch

from tools.can_nt.bringup_ui import (
    ACTION_KIND_REMOTE_COMMAND,
    ACTIONS_BY_NAME,
    ACTION_SOURCE_ROBOT,
    ATTACHMENT_TYPE_ACTIVE_PRESENCE_PROBE,
    BringupControlUI,
    CMD_SHOW_LIFECYCLE_STATE,
    GROUP_ACTIVE_NAME,
    GROUP_RUN_ARG_GROUP,
    HIDDEN_LEFT_RAIL_COMMANDS,
    INVENTORY_KEY_ACTION_KIND,
    INVENTORY_KEY_SOURCE,
    KEY_TYPE,
    MANUAL_DUTY_ARG_DUTY,
    MANUAL_GROUP_DUTY_CMD_SET,
    PROFILE_NONE,
    TEST_ACTIVITY_COMMANDS,
    TEST_SOURCE_COMPLETION_MODE_CLEAR,
    TEST_SOURCE_COMPLETION_MODE_NONE,
    TEST_SOURCE_COMPLETION_MODE_READ,
    TEST_SOURCE_COMPLETION_MODE_WRITE,
    _load_tests_from_dsl_store,
    _action_sections,
    _format_runtime_probe_score,
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


class _ValueVarStub:
    def __init__(self, value=0.0) -> None:
        self._value = value

    def get(self):
        return self._value

    def set(self, value) -> None:
        self._value = value


class _ComboBoxStub:
    def __init__(self, values=()) -> None:
        self._values = tuple(values)
        self._state = "normal"

    def cget(self, key: str):
        if key == "values":
            return self._values
        raise KeyError(key)

    def __setitem__(self, key: str, value) -> None:
        if key != "values":
            raise KeyError(key)
        self._values = tuple(value)

    def configure(self, **kwargs) -> None:
        if "state" in kwargs:
            self._state = kwargs["state"]


class _ButtonStub:
    def __init__(self) -> None:
        self.disabled = False

    def state(self, states) -> None:
        self.disabled = "disabled" in tuple(states)


class _LabelStub:
    def __init__(self) -> None:
        self.foreground = None
        self.bg = None
        self.fg = None

    def configure(self, **kwargs) -> None:
        if "foreground" in kwargs:
            self.foreground = kwargs["foreground"]
        if "bg" in kwargs:
            self.bg = kwargs["bg"]
        if "fg" in kwargs:
            self.fg = kwargs["fg"]


class _PanelStub:
    def __init__(self) -> None:
        self.bg = None
        self.highlightbackground = None

    def configure(self, **kwargs) -> None:
        if "bg" in kwargs:
            self.bg = kwargs["bg"]
        if "highlightbackground" in kwargs:
            self.highlightbackground = kwargs["highlightbackground"]


class _ListboxStub:
    def __init__(self) -> None:
        self.cleared = False

    def selection_clear(self, *_args) -> None:
        self.cleared = True


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

    def test_test_source_command_hidden_from_left_rail_but_tracked_in_tests_activity(self) -> None:
        self.assertIn("printSelectedTestSource", HIDDEN_LEFT_RAIL_COMMANDS)
        self.assertIn("printselectedtestsource", TEST_ACTIVITY_COMMANDS)

    def test_print_next_command_hidden_from_left_rail_but_tracked_in_tests_activity(self) -> None:
        self.assertIn("printNextTest", HIDDEN_LEFT_RAIL_COMMANDS)
        self.assertIn("printnexttest", TEST_ACTIVITY_COMMANDS)

    def test_state_command_hidden_from_left_rail_but_tracked_in_tests_activity(self) -> None:
        self.assertIn("printState", HIDDEN_LEFT_RAIL_COMMANDS)
        self.assertIn("printstate", TEST_ACTIVITY_COMMANDS)

    def test_show_lifecycle_state_is_tracked_in_tests_activity(self) -> None:
        self.assertIn("showlifecyclestate", TEST_ACTIVITY_COMMANDS)

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
        self.assertTrue(ui._is_test_activity_command("lifecycleActivate"))
        self.assertTrue(ui._is_test_activity_command("groupReplaceMembers"))
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

    def test_robot_tests_table_tracks_robot_known_test_names(self) -> None:
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

        self.assertEqual(["robot_test_a", "robot_test_b"], ui._known_test_names)
        self.assertEqual("local_only_test", ui._selected_test_var.get())

    def test_sync_test_dropdown_values_preserves_none_selection(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._selected_test_var = _StringVarStub(PROFILE_NONE)
        ui._last_selected_test = PROFILE_NONE
        ui._test_box = _ComboBoxStub(("robot_test_a",))
        ui._tests_tab_test_box = _ComboBoxStub(("robot_test_a",))

        ui._sync_test_dropdown_values(["robot_test_a", "robot_test_b"])

        self.assertEqual(["robot_test_a", "robot_test_b"], ui._known_test_names)
        self.assertEqual(PROFILE_NONE, ui._selected_test_var.get())

    def test_scope_context_uses_tests_tab_when_selected(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._current_right_tab_text = lambda: "Tests"

        self.assertEqual("selected test", ui._scope_context_kind())

    def test_selected_test_inactive_reason_uses_loaded_not_activated_text(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._selected_test_var = _StringVarStub("falcon9_move_150_rotations")
        ui._tests_active_group_rows = [{"label": "FALCON 9", "enabled": True, "invalid": False}]
        ui._controlled_lifecycle_active_known = False
        ui._latest_runtime_devices = {}
        ui._tests_table = _SubTableStub(
            entries={"totalCount": "1"},
            rows={
                "rows": _SubTableStub(
                    rows={
                        "0": _SubTableStub(
                            entries={
                                "name": "falcon9_move_150_rotations",
                                "requiredDevices": "FALCON 9",
                                "runnableNow": False,
                                "blockedReason": "",
                            }
                        )
                    }
                )
            },
        )
        ui._active_group_is_currently_active = lambda: False

        self.assertEqual(
            "active-group loaded from selected test - not activated",
            ui._selected_test_inactive_reason(),
        )

    def test_selected_test_inactive_reason_reports_invalid_device_first(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._selected_test_var = _StringVarStub("falcon9_to_limit")
        ui._tests_active_group_rows = [
            {"label": "FALCON 9", "enabled": True, "invalid": False},
            {"label": "lmtSw0", "enabled": True, "invalid": True},
        ]

        self.assertEqual(
            "missing resource/device - lmtSw0",
            ui._selected_test_inactive_reason(),
        )

    def test_selected_test_required_rows_uses_test_profile_devices_for_controller_validation(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._selected_test_var = _StringVarStub("test_minimal_25_9_spark25_leftY")
        ui._test_profile_devices = {
            "sparkmax/neo 25": {"label": "SPARKMAX/NEO 25"},
            "controller0": {"label": "controller0"},
        }
        ui._profile_devices = {}
        ui._tests_table = _SubTableStub(
            entries={"totalCount": "1"},
            rows={
                "rows": _SubTableStub(
                    rows={
                        "0": _SubTableStub(
                            entries={
                                "name": "test_minimal_25_9_spark25_leftY",
                                "requiredDevices": "SPARKMAX/NEO 25,controller0",
                                "runnableNow": False,
                                "blockedReason": "",
                            }
                        )
                    }
                )
            },
        )

        rows = ui._selected_test_required_rows()

        self.assertEqual(2, len(rows))
        self.assertFalse(rows[0]["invalid"])
        self.assertFalse(rows[1]["invalid"])

    def test_clear_test_selection_ui_clears_current_test_and_lists(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._selected_test_var = _StringVarStub("robot_test_a")
        ui._last_selected_test = "robot_test_a"
        ui._test_box = _ComboBoxStub(("robot_test_a", "robot_test_b"))
        ui._tests_tab_test_box = _ComboBoxStub(("robot_test_a", "robot_test_b"))
        ui._test_library_global_list = _ListboxStub()
        ui._test_library_config_list = _ListboxStub()
        ui._test_library_profile_list = _ListboxStub()
        ui._selected_test_scope_status_var = _StringVarStub("")
        ui._latest_runtime_devices = {}
        ui._tests_table = None

        ui._clear_test_selection_ui()

        self.assertEqual(PROFILE_NONE, ui._selected_test_var.get())
        self.assertTrue(ui._test_library_global_list.cleared)
        self.assertTrue(ui._test_library_config_list.cleared)
        self.assertTrue(ui._test_library_profile_list.cleared)

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

        self.assertEqual([selected_name], ui._known_test_names)
        self.assertEqual(selected_name, ui._selected_test_var.get())

    def test_sync_test_selection_aligns_profile_list_and_source_editor_to_robot_selected_test(self) -> None:
        class _Listbox:
            def __init__(self, items, selection=()) -> None:
                self._items = list(items)
                self._selection = tuple(selection)

            def size(self):
                return len(self._items)

            def curselection(self):
                return self._selection

            def get(self, index):
                return self._items[index]

            def selection_clear(self, *_args) -> None:
                self._selection = ()

            def selection_set(self, index) -> None:
                self._selection = (index,)

            def see(self, _index) -> None:
                return None

        ui = BringupControlUI.__new__(BringupControlUI)
        ui._selected_test_var = _StringVarStub("test_minimal_25_9_spark25_leftY")
        ui._last_selected_test = "test_minimal_25_9_spark25_leftY"
        ui._test_library_global_list = _Listbox(["global_a"])
        ui._test_library_config_list = _Listbox(["config_a"])
        ui._test_library_profile_list = _Listbox(
            ["test_minimal_25_9_spark25_leftY", "mtrs_limit"],
            selection=(0,),
        )
        loaded = []
        ui._load_selected_test_source = lambda: loaded.append(ui._selected_test_library_entry())
        ui._current_right_tab_text = lambda: "Tests"
        ui._load_selected_test_into_active_group = lambda force_replace=False: None
        ui._refresh_selected_test_scope_status = lambda: None

        ui._sync_test_selection("mtrs_limit")

        self.assertEqual("mtrs_limit", ui._selected_test_var.get())
        self.assertEqual(("mtrs_limit", "profile"), ui._selected_test_library_entry())
        self.assertEqual([("mtrs_limit", "profile")], loaded)

    def test_sync_test_selection_realigns_editor_when_header_already_matches_robot_selection(self) -> None:
        class _Listbox:
            def __init__(self, items, selection=()) -> None:
                self._items = list(items)
                self._selection = tuple(selection)

            def size(self):
                return len(self._items)

            def curselection(self):
                return self._selection

            def get(self, index):
                return self._items[index]

            def selection_clear(self, *_args) -> None:
                self._selection = ()

            def selection_set(self, index) -> None:
                self._selection = (index,)

            def see(self, _index) -> None:
                return None

        ui = BringupControlUI.__new__(BringupControlUI)
        ui._selected_test_var = _StringVarStub("test_minimal_25_9_spark25_leftY")
        ui._last_selected_test = "test_minimal_25_9_spark25_leftY"
        ui._test_library_global_list = _Listbox(["global_a"])
        ui._test_library_config_list = _Listbox(["config_a"])
        ui._test_library_profile_list = _Listbox(
            ["test_minimal_25_9_spark25_leftY", "mtrs_limit"],
            selection=(1,),
        )
        loaded = []
        ui._load_selected_test_source = lambda: loaded.append(ui._selected_test_library_entry())
        ui._current_right_tab_text = lambda: "Tests"
        ui._load_selected_test_into_active_group = lambda force_replace=False: None
        ui._refresh_selected_test_scope_status = lambda: None

        ui._sync_test_selection("test_minimal_25_9_spark25_leftY")

        self.assertEqual(("test_minimal_25_9_spark25_leftY", "profile"), ui._selected_test_library_entry())
        self.assertEqual([("test_minimal_25_9_spark25_leftY", "profile")], loaded)

    def test_sync_test_selection_does_not_reload_source_when_already_aligned(self) -> None:
        class _Listbox:
            def __init__(self, items, selection=()) -> None:
                self._items = list(items)
                self._selection = tuple(selection)

            def size(self):
                return len(self._items)

            def curselection(self):
                return self._selection

            def get(self, index):
                return self._items[index]

            def selection_clear(self, *_args) -> None:
                self._selection = ()

            def selection_set(self, index) -> None:
                self._selection = (index,)

            def see(self, _index) -> None:
                return None

        ui = BringupControlUI.__new__(BringupControlUI)
        ui._selected_test_var = _StringVarStub("mtrs_limit")
        ui._last_selected_test = "mtrs_limit"
        ui._selected_test_source_name = "mtrs_limit"
        ui._test_library_global_list = _Listbox(["global_a"])
        ui._test_library_config_list = _Listbox(["config_a"])
        ui._test_library_profile_list = _Listbox(
            ["test_minimal_25_9_spark25_leftY", "mtrs_limit"],
            selection=(1,),
        )
        loaded = []
        ui._load_selected_test_source = lambda: loaded.append(ui._selected_test_library_entry())
        ui._current_right_tab_text = lambda: "Tests"
        ui._load_selected_test_into_active_group = lambda force_replace=False: None
        ui._refresh_selected_test_scope_status = lambda: None

        ui._sync_test_selection("mtrs_limit")

        self.assertEqual([], loaded)

    def test_selected_test_inactive_reason_uses_robot_blocked_reason(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._selected_test_var = _StringVarStub("spark25_leftY")
        ui._robot_enabled_known = True
        ui._robot_estopped_known = False
        ui._robot_mode_known = "teleop"
        ui._active_group_is_currently_active = lambda: True
        ui._tests_table = _SubTableStub(
            entries={"totalCount": "1"},
            rows={
                "rows": _SubTableStub(
                    rows={
                        "0": _SubTableStub(
                            entries={
                                "name": "spark25_leftY",
                                "runnableNow": False,
                                "blockedReason": "missing resource/device - controller0",
                                "requiredDevices": "SPARKMAX/NEO 25,controller0",
                            }
                        )
                    }
                )
            },
        )

        self.assertEqual(
            "missing resource/device - controller0",
            ui._selected_test_inactive_reason(),
        )

    def test_selected_test_inactive_reason_prefers_estop_over_activate_group_prompt(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._selected_test_var = _StringVarStub("spark25_leftY")
        ui._robot_enabled_known = False
        ui._robot_estopped_known = True
        ui._robot_mode_known = "disabled"
        ui._active_group_is_currently_active = lambda: False
        ui._tests_table = _SubTableStub(entries={"totalCount": "0"}, rows={"rows": _SubTableStub(rows={})})

        self.assertEqual("robot disabled (E-Stop)", ui._selected_test_inactive_reason())

    def test_format_selected_test_scope_status_detail_guides_activation(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)

        self.assertEqual(
            "This test has loaded its required devices into active-group. Press Activate Group, then run the test.",
            ui._format_selected_test_scope_status_detail(
                "active-group loaded from selected test - not activated"
            ),
        )

    def test_format_selected_test_scope_status_detail_expands_missing_device_reason(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)

        self.assertEqual(
            "This test cannot run because a required profile device is missing: controller0",
            ui._format_selected_test_scope_status_detail("missing resource/device - controller0"),
        )

    def test_format_selected_test_scope_status_detail_expands_disabled_reason(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)

        self.assertEqual(
            "This test cannot run because the robot is disabled. Enable teleop before activating the group or running the test.",
            ui._format_selected_test_scope_status_detail("robot disabled"),
        )

    def test_format_selected_test_scope_status_detail_expands_estop_reason(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)

        self.assertEqual(
            "This test cannot run because the robot is E-stopped. Clear the E-stop before activating the group or running the test.",
            ui._format_selected_test_scope_status_detail("robot disabled (E-Stop)"),
        )

    def test_build_evidence_probe_stats_text_reports_running_and_recent_completion(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._evidence_probe_pending = True
        ui._evidence_last_probe_completed_at = 0.0
        ui._evidence_probe_run_count = 0

        self.assertEqual("Full Probe is running now.", ui._build_evidence_probe_stats_text())

        ui._evidence_probe_pending = False
        ui._evidence_last_probe_completed_at = time.time() - 5.0

        self.assertIn(
            "Last Full Probe completed",
            ui._build_evidence_probe_stats_text(),
        )

    def test_build_evidence_probe_missing_text_distinguishes_session_without_device_result(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._evidence_last_probe_completed_at = time.time() - 4.0

        self.assertEqual(
            "This device was not part of the active runtime probe set when Full Probe ran.",
            ui._build_evidence_probe_missing_text(None),
        )
        self.assertEqual(
            "This device was not part of the active runtime probe set when Full Probe ran.",
            ui._build_evidence_probe_missing_text({"instantiated": False}),
        )
        self.assertEqual(
            "No device-specific full-probe result for this device.",
            ui._build_evidence_probe_missing_text({"instantiated": True}),
        )

    def test_cache_active_probe_results_from_command_builds_runtime_attachment_shape(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._evidence_probe_results_by_label = {}

        ui._cache_active_probe_results_from_command(
            {
                "devices": [
                    {
                        "label": "FALCON 9",
                        "bucket": "present",
                        "score": 95,
                        "maxScore": 100,
                        "message": "Device present: FALCON 9.",
                        "status": "ok",
                        "code": 1,
                        "warnings": [],
                        "errors": [],
                        "evidence": [
                            {"passed": False, "code": "STATUS_REFRESH_OK", "observedValue": "false"},
                            {"passed": True, "code": "BUS_VOLTAGE_VALID", "observedValue": "12.1"},
                        ],
                    }
                ]
            }
        )

        attachment = ui._evidence_probe_results_by_label["falcon 9"]
        self.assertEqual("activePresenceProbe", attachment["type"])
        self.assertEqual("present", attachment["bucket"])
        self.assertEqual(["STATUS_REFRESH_OK=false"], attachment["failedChecks"])

    def test_format_runtime_probe_score_hides_numeric_score_when_bucket_unknown(self) -> None:
        device = {
            "attachments": [
                {
                    "type": ATTACHMENT_TYPE_ACTIVE_PRESENCE_PROBE,
                    "bucket": "unknown",
                    "score": 100,
                    "maxScore": 100,
                }
            ]
        }

        self.assertEqual("--", _format_runtime_probe_score(device))

    def test_apply_runtime_state_payload_merges_cached_active_probe_result_when_runtime_attachment_missing(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._latest_runtime_state_payload = {}
        ui._runtime_active_known = False
        ui._controlled_lifecycle_active_known = False
        ui._robot_selected_profile = PROFILE_NONE
        ui._robot_active_runtime_profile = PROFILE_NONE
        ui._sync_diagnostic_profile_context = lambda reload_views=False: None
        ui._latest_runtime_devices = {}
        ui._manual_motion_checks = {}
        ui._manual_test_observations = {}
        ui._iter_live_views = lambda: []
        ui._refresh_tests_active_group_panel = lambda: None
        ui._refresh_selected_test_scope_status = lambda: None
        ui._refresh_evidence_view = lambda: None
        ui._runtime_state_backoff = 1.0
        ui._runtime_state_idle_count = 0
        ui._runtime_state_idle_pause_sec = 0.0
        ui._runtime_state_pause_until = None
        ui._evidence_probe_results_by_label = {
            "falcon 9": {
                "type": "activePresenceProbe",
                "bucket": "present",
                "score": 95,
                "maxScore": 100,
                "updatedAtMs": 123,
                "failedChecks": [],
                "warnings": [],
                "errors": [],
                "message": "Device present: FALCON 9.",
                "status": "ok",
                "code": 1,
            }
        }

        ui._apply_runtime_state_payload(
            {
                "selectedProfile": "test_minimal_25_9",
                "activeRuntimeProfile": "test_minimal_25_9",
                "runtimeActive": True,
                "controlledLifecycleActive": True,
                "devices": [
                    {
                        "label": "FALCON 9",
                        "instantiated": True,
                        "attachments": [],
                    }
                ],
            }
        )

        attachments = ui._latest_runtime_devices["falcon 9"]["attachments"]
        self.assertEqual("activePresenceProbe", attachments[0]["type"])
        self.assertEqual("present", attachments[0]["bucket"])

    def test_selected_test_ready_uses_robot_runnable_now(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._selected_test_var = _StringVarStub("mtrs_limit")
        ui._active_group_is_currently_active = lambda: True
        ui._tests_table = _SubTableStub(
            entries={"totalCount": "1"},
            rows={
                "rows": _SubTableStub(
                    rows={
                        "0": _SubTableStub(
                            entries={
                                "name": "mtrs_limit",
                                "runnableNow": True,
                                "blockedReason": "",
                                "requiredDevices": "FALCON 9,lmtSw0,SPARKMAX/NEO 25",
                            }
                        )
                    }
                )
            },
        )

        self.assertTrue(ui._selected_test_ready())

    def test_selected_test_required_rows_uses_local_dsl_declaration_not_robot_rows(self) -> None:
        class _DeviceRef:
            def __init__(self, name: str) -> None:
                self.name = name

        class _Normalized:
            def __init__(self, devices) -> None:
                self.devices = devices

        class _Entry:
            def __init__(self, normalized) -> None:
                self.normalized = normalized

        class _Store:
            def __init__(self) -> None:
                self.tests_by_name = {
                    "falcon9_to_limit": _Entry(
                        _Normalized([_DeviceRef("FALCON 9"), _DeviceRef("lmtSw0")])
                    )
                }

        ui = BringupControlUI.__new__(BringupControlUI)
        ui._selected_test_var = _StringVarStub("falcon9_to_limit")
        ui._tests_table = _SubTableStub(
            entries={"totalCount": "1"},
            rows={
                "rows": _SubTableStub(
                    rows={
                        "0": _SubTableStub(
                            entries={
                                "name": "falcon9_to_limit",
                                "requiredDevices": "",
                                "runnableNow": False,
                                "blockedReason": "",
                            }
                        )
                    }
                )
            },
        )
        ui._test_profile_devices = {
            "falcon 9": {"label": "FALCON 9"},
            "lmtsw0": {"label": "lmtSw0"},
        }
        ui._profile_devices = {}

        with patch("tools.can_nt.bringup_ui.LocalConfigQueryService") as service_cls, patch(
            "tools.can_nt.bringup_ui.robot_test_dsl_store_from_root_payload",
            return_value=_Store(),
        ):
            service_cls.return_value.load_canonical_payload.return_value = {"dslTests": {}}
            rows = ui._selected_test_required_rows()

        self.assertEqual(["FALCON 9", "lmtSw0"], [row["label"] for row in rows])

    def test_update_action_enabled_disables_run_selected_but_not_activate_scope(self) -> None:
        class _Tracker:
            def is_pending(self) -> bool:
                return False

        ui = BringupControlUI.__new__(BringupControlUI)
        ui._tcp_connected = True
        ui._handshake_done = True
        ui._state_stale = False
        ui._tracker = _Tracker()
        ui._refresh_scope_context_label = lambda: None
        ui._refresh_selected_test_scope_status = lambda: None
        ui._action_buttons = []
        ui._action_buttons_by_command = {}
        ui._host_local_action_enabled = lambda _command: True
        ui._selected_test_var = _StringVarStub("falcon9_move_150_rotations")
        ui._test_box = _ComboBoxStub(("falcon9_move_150_rotations",))
        ui._tests_tab_test_box = _ComboBoxStub(("falcon9_move_150_rotations",))
        ui._activate_scope_button = _ButtonStub()
        ui._deactivate_scope_button = _ButtonStub()
        ui._tests_run_selected_button = _ButtonStub()
        ui._reset_button = None
        ui._current_right_tab_text = lambda: "Tests"
        ui._tests_table = _SubTableStub(
            entries={"totalCount": "1"},
            rows={
                "rows": _SubTableStub(
                    rows={
                        "0": _SubTableStub(
                            entries={
                                "name": "falcon9_move_150_rotations",
                                "runnableNow": False,
                                "blockedReason": "missing resource/device - FALCON 9",
                                "requiredDevices": "FALCON 9",
                            }
                        )
                    }
                )
            },
        )

        ui._update_action_enabled()

        self.assertFalse(ui._activate_scope_button.disabled)
        self.assertTrue(ui._tests_run_selected_button.disabled)

    def test_update_action_enabled_disables_active_add_and_next_while_active_group_is_active(self) -> None:
        class _Tracker:
            def is_pending(self) -> bool:
                return False

        ui = BringupControlUI.__new__(BringupControlUI)
        ui._tcp_connected = True
        ui._handshake_done = True
        ui._state_stale = False
        ui._tracker = _Tracker()
        ui._refresh_scope_context_label = lambda: None
        ui._refresh_selected_test_scope_status = lambda: None
        ui._action_buttons = []
        ui._action_buttons_by_command = {
            "activeAdd": _ButtonStub(),
            "activeNext": _ButtonStub(),
            "printState": _ButtonStub(),
        }
        ui._host_local_action_enabled = lambda _command: True
        ui._selected_test_var = _StringVarStub("falcon9_move_150_rotations")
        ui._test_selection_boxes = lambda: []
        ui._activate_scope_button = _ButtonStub()
        ui._deactivate_scope_button = _ButtonStub()
        ui._tests_run_selected_button = _ButtonStub()
        ui._reset_button = None
        ui._current_right_tab_text = lambda: "Live Topology"
        ui._active_group_is_currently_active = lambda: True
        ui._selected_test_ready = lambda: False
        ui._manual_active_group_is_empty = lambda: False

        ui._update_action_enabled()

        self.assertTrue(ui._action_buttons_by_command["activeAdd"].disabled)
        self.assertTrue(ui._action_buttons_by_command["activeNext"].disabled)
        self.assertFalse(ui._action_buttons_by_command["printState"].disabled)

    def test_update_action_enabled_disables_activate_and_run_selected_when_robot_disabled(self) -> None:
        class _Tracker:
            def is_pending(self) -> bool:
                return False

        ui = BringupControlUI.__new__(BringupControlUI)
        ui._tcp_connected = True
        ui._handshake_done = True
        ui._state_stale = False
        ui._tracker = _Tracker()
        ui._refresh_scope_context_label = lambda: None
        ui._refresh_selected_test_scope_status = lambda: None
        ui._action_buttons = []
        ui._action_buttons_by_command = {}
        ui._host_local_action_enabled = lambda _command: True
        ui._selected_test_var = _StringVarStub("falcon9_move_150_rotations")
        ui._test_selection_boxes = lambda: []
        ui._activate_scope_button = _ButtonStub()
        ui._deactivate_scope_button = _ButtonStub()
        ui._tests_run_selected_button = _ButtonStub()
        ui._reset_button = None
        ui._current_right_tab_text = lambda: "Tests"
        ui._active_group_is_currently_active = lambda: True
        ui._selected_test_ready = lambda: True
        ui._scope_context_kind = lambda: GROUP_SOURCE_SELECTED_TEST
        ui._tests_active_group_rows = []
        ui._robot_enabled_known = False
        ui._robot_estopped_known = False
        ui._robot_mode_known = "disabled"
        ui._manual_active_group_is_empty = lambda: False

        ui._update_action_enabled()

        self.assertTrue(ui._activate_scope_button.disabled)
        self.assertTrue(ui._deactivate_scope_button.disabled)
        self.assertTrue(ui._tests_run_selected_button.disabled)

    def test_update_action_enabled_enables_deactivate_only_when_controlled_session_active(self) -> None:
        class _Tracker:
            def is_pending(self) -> bool:
                return False

        ui = BringupControlUI.__new__(BringupControlUI)
        ui._tcp_connected = True
        ui._handshake_done = True
        ui._state_stale = False
        ui._tracker = _Tracker()
        ui._refresh_scope_context_label = lambda: None
        ui._refresh_selected_test_scope_status = lambda: None
        ui._action_buttons = []
        ui._action_buttons_by_command = {}
        ui._host_local_action_enabled = lambda _command: True
        ui._selected_test_var = _StringVarStub("")
        ui._test_selection_boxes = lambda: []
        ui._activate_scope_button = _ButtonStub()
        ui._deactivate_scope_button = _ButtonStub()
        ui._tests_run_selected_button = _ButtonStub()
        ui._reset_button = None
        ui._current_right_tab_text = lambda: "Live Topology"
        ui._selected_test_ready = lambda: False
        ui._controlled_lifecycle_active_known = False
        ui._manual_active_group_is_empty = lambda: True

        ui._update_action_enabled()
        self.assertTrue(ui._deactivate_scope_button.disabled)

        ui._controlled_lifecycle_active_known = True
        ui._manual_active_group_is_empty = lambda: False
        ui._update_action_enabled()
        self.assertFalse(ui._deactivate_scope_button.disabled)

    def test_update_action_enabled_disables_manual_activate_when_active_group_empty(self) -> None:
        class _Tracker:
            def is_pending(self) -> bool:
                return False

        ui = BringupControlUI.__new__(BringupControlUI)
        ui._tcp_connected = True
        ui._handshake_done = True
        ui._state_stale = False
        ui._tracker = _Tracker()
        ui._refresh_scope_context_label = lambda: None
        ui._refresh_selected_test_scope_status = lambda: None
        ui._action_buttons = []
        ui._action_buttons_by_command = {}
        ui._host_local_action_enabled = lambda _command: True
        ui._selected_test_var = _StringVarStub("")
        ui._test_selection_boxes = lambda: []
        ui._activate_scope_button = _ButtonStub()
        ui._deactivate_scope_button = _ButtonStub()
        ui._tests_run_selected_button = _ButtonStub()
        ui._reset_button = None
        ui._current_right_tab_text = lambda: "Live Topology"
        ui._selected_test_ready = lambda: False
        ui._manual_active_group_is_empty = lambda: True

        ui._update_action_enabled()

        self.assertTrue(ui._activate_scope_button.disabled)

    def test_live_runtime_notice_suppresses_lifecycle_prompt_in_manual_mode(self) -> None:
        class _LiveView:
            def __init__(self) -> None:
                self.notice = None

            def set_runtime_state_notice(self, text, level) -> None:
                self.notice = (text, level)

            def clear_runtime_state_notice(self) -> None:
                self.notice = None

        ui = BringupControlUI.__new__(BringupControlUI)
        ui._group_owner_mode = "manual"
        ui._runtime_active_known = False
        ui._controlled_lifecycle_active_known = False
        ui._scope_is_currently_active = lambda: False
        ui._manual_active_group_is_empty = lambda: False
        recorded = []
        live_view = _LiveView()
        ui._set_runtime_state_notice = lambda text, level="warn": recorded.append((text, level))
        ui._clear_runtime_state_notice = lambda: recorded.append(("__clear__", "clear"))
        ui._iter_live_views = lambda: [live_view]

        ui._apply_live_runtime_notice_from_nt_state(True, False, False)

        self.assertEqual(
            [("Activate Group first.", "warn")],
            recorded,
        )
        self.assertEqual(
            ("Activate Group first.", "warn"),
            live_view.notice,
        )

    def test_live_runtime_notice_shows_lifecycle_prompt_for_selected_test_mode(self) -> None:
        class _LiveView:
            def __init__(self) -> None:
                self.notice = None

            def set_runtime_state_notice(self, text, level) -> None:
                self.notice = (text, level)

            def clear_runtime_state_notice(self) -> None:
                self.notice = None

        ui = BringupControlUI.__new__(BringupControlUI)
        ui._group_owner_mode = "selected test"
        ui._runtime_active_known = False
        ui._controlled_lifecycle_active_known = False
        ui._scope_is_currently_active = lambda: False
        ui._manual_active_group_is_empty = lambda: False
        recorded = []
        live_view = _LiveView()
        ui._set_runtime_state_notice = lambda text, level="warn": recorded.append((text, level))
        ui._clear_runtime_state_notice = lambda: recorded.append(("__clear__", "clear"))
        ui._iter_live_views = lambda: [live_view]

        ui._apply_live_runtime_notice_from_nt_state(True, False, False)

        self.assertEqual(
            [("Activate lifecycle first.", "warn")],
            recorded,
        )
        self.assertEqual(
            ("Activate lifecycle first.", "warn"),
            live_view.notice,
        )

    def test_scope_activation_notice_mentions_teleop_only_when_not_in_teleop(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._group_owner_mode = "manual"
        ui._robot_mode_known = "teleop"
        self.assertEqual("Activate Group first.", ui._scope_activation_notice_text())

        ui._robot_mode_known = "autonomous"
        self.assertEqual(
            "Switch to teleop, then Activate Group.",
            ui._scope_activation_notice_text(),
        )

    def test_live_runtime_notice_is_ready_when_manual_scope_is_active_even_if_runtime_flag_is_false(self) -> None:
        class _LiveView:
            def __init__(self) -> None:
                self.notice = None

            def set_runtime_state_notice(self, text, level) -> None:
                self.notice = (text, level)

            def clear_runtime_state_notice(self) -> None:
                self.notice = None

        ui = BringupControlUI.__new__(BringupControlUI)
        ui._group_owner_mode = "manual"
        ui._runtime_active_known = False
        ui._controlled_lifecycle_active_known = True
        ui._scope_is_currently_active = lambda: True
        ui._manual_active_group_is_empty = lambda: False
        recorded = []
        live_view = _LiveView()
        ui._set_runtime_state_notice = lambda text, level="warn": recorded.append((text, level))
        ui._clear_runtime_state_notice = lambda: recorded.append(("__clear__", "clear"))
        ui._iter_live_views = lambda: [live_view]

        ui._apply_live_runtime_notice_from_nt_state(True, False, False)

        self.assertEqual(
            [("__clear__", "clear")],
            recorded,
        )
        self.assertIsNone(live_view.notice)

    def test_live_runtime_notice_surfaces_empty_manual_active_group(self) -> None:
        class _LiveView:
            def __init__(self) -> None:
                self.notice = None

            def set_runtime_state_notice(self, text, level) -> None:
                self.notice = (text, level)

            def clear_runtime_state_notice(self) -> None:
                self.notice = None

        ui = BringupControlUI.__new__(BringupControlUI)
        ui._group_owner_mode = "manual"
        ui._runtime_active_known = False
        ui._controlled_lifecycle_active_known = False
        ui._scope_is_currently_active = lambda: False
        ui._manual_active_group_is_empty = lambda: True
        recorded = []
        live_view = _LiveView()
        ui._set_runtime_state_notice = lambda text, level="warn": recorded.append((text, level))
        ui._clear_runtime_state_notice = lambda: recorded.append(("__clear__", "clear"))
        ui._iter_live_views = lambda: [live_view]

        ui._apply_live_runtime_notice_from_nt_state(False, False, False)

        self.assertEqual(
            [("Active group is empty. Add devices before Activate Group.", "warn")],
            recorded,
        )
        self.assertEqual(
            ("Active group is empty. Add devices before Activate Group.", "warn"),
            live_view.notice,
        )

    def test_output_runtime_notice_waits_for_runtime_state_before_showing_ready(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._output_scope_panel = _PanelStub()
        ui._output_scope_headline_var = _StringVarStub("")
        ui._output_scope_detail_var = _StringVarStub("")
        ui._output_scope_title_label = _LabelStub()
        ui._output_scope_headline_label = _LabelStub()
        ui._output_scope_detail_label = _LabelStub()
        ui._tcp_connected = True
        ui._handshake_done = True
        ui._runtime_state_seen = False
        ui._runtime_state_notice_text = ""
        ui._runtime_event_notice_text = ""

        ui._refresh_output_runtime_notice()

        self.assertEqual("WAITING FOR STATE", ui._output_scope_headline_var.get())
        self.assertEqual(
            "waiting for robot runtime state",
            ui._output_scope_detail_var.get(),
        )

    def test_apply_runtime_state_payload_marks_runtime_state_seen(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._runtime_state_seen = False
        ui._latest_runtime_state_payload = {}
        ui._runtime_active_known = None
        ui._controlled_lifecycle_active_known = None
        ui._robot_selected_profile = ""
        ui._robot_active_runtime_profile = ""
        ui._sync_diagnostic_profile_context = lambda reload_views=False: None
        ui._merge_cached_active_probe_results_into_runtime_devices = lambda: None
        ui._manual_motion_checks = {}
        ui._latest_runtime_devices = {}
        ui._presence_overrides_file = {}
        ui._presence_timeline = []
        ui._presence_timeline_start = 0.0
        ui._presence_timeline_period = 0.0
        ui._runtime_group_members = []
        ui._runtime_group_primary = None
        ui._runtime_group_name = ""
        ui._group_owner_mode = "manual"
        ui._group_member_rows = []
        ui._active_group_rows = []
        ui._render_runtime_group_members = lambda: None
        ui._refresh_active_group_summary = lambda: None
        ui._refresh_test_device_rows = lambda: None
        ui._refresh_selected_test_scope_status = lambda: None
        ui._refresh_evidence_view = lambda: None
        ui._refresh_output_runtime_notice = lambda: None
        ui._iter_live_views = lambda: []
        ui._device_timeline_by_label = {}
        ui._active_probe_cache = {}
        ui._runtime_state_path = None
        ui._runtime_state_path_mtime = None
        ui._latest_runtime_presence_map = {}

        ui._apply_runtime_state_payload({"enabled": True, "devices": []})

        self.assertTrue(ui._runtime_state_seen)

    def test_apply_robot_ui_session_id_initial_value_does_not_reset_runtime_context(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._robot_ui_session_id = None
        called = []
        ui._reset_ui_session_runtime_context = lambda: called.append("reset")

        ui._apply_robot_ui_session_id("session-a")

        self.assertEqual([], called)
        self.assertEqual("session-a", ui._robot_ui_session_id)

    def test_apply_robot_ui_session_id_change_resets_runtime_context(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._robot_ui_session_id = "session-a"
        called = []
        ui._reset_ui_session_runtime_context = lambda: called.append("reset")

        ui._apply_robot_ui_session_id("session-b")

        self.assertEqual(["reset"], called)
        self.assertEqual("session-b", ui._robot_ui_session_id)

    def test_refresh_test_result_status_surfaces_pass_result_in_tests_header(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._last_result_text_var = _StringVarStub("")
        ui._last_result_label = _LabelStub()
        ui._tests_table = _SubTableStub(
            entries={
                "runState": "passed",
                "runTest": "falcon9_to_limit",
                "runResult": "PASS",
                "runMessage": "success success_1: success lmtSw0.pressed",
            }
        )

        ui._refresh_test_result_status()

        self.assertEqual(
            "Last Result: PASS - success success_1: success lmtSw0.pressed",
            ui._last_result_text_var.get(),
        )
        self.assertEqual("#166534", ui._last_result_label.foreground)

    def test_ui_poll_log_mirrors_print_state_report_lines_into_test_activity(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._log_poll_seq = 41
        ui._log_poll_inflight = True
        ui._last_cmd = ("printState", {})
        ui._recent_out_lines = {}
        ui._out_dedupe_window = 1.0
        output_lines = []
        test_lines = []
        ui._append_output = output_lines.append
        ui._append_test_output = test_lines.append
        ui._runtime_state_pending_seq = None
        ui._is_handshake_required = lambda _event: False
        ui._handle_handshake_required = lambda: None
        ui._is_owner_required = lambda _event: False
        ui._handle_owner_required = lambda: None
        ui._notify_ui_failure = lambda *_args, **_kwargs: None
        ui._tracker = type("TrackerStub", (), {"handle_event": staticmethod(lambda _event: None)})()
        ui._apply_runtime_group_command_payload = lambda _data: None
        ui._apply_robot_profile_context_from_command_event = lambda *_args: None
        ui._remember_out_line = lambda _line: None

        ui._handle_tcp_response(
            BridgeEvent(
                type="out",
                seq=41,
                name="uiPollLog",
                status="ok",
                message="",
                text="Test #2: falcon9_to_limit\nTest result #2: falcon9_to_limit = PASS",
                json_text="",
                ts=0.0,
                session_id="",
                state={},
                raw={},
            )
        )

        self.assertEqual(
            [
                "Test #2: falcon9_to_limit",
                "Test result #2: falcon9_to_limit = PASS",
            ],
            output_lines,
        )
        self.assertEqual(output_lines, test_lines)
        self.assertFalse(ui._log_poll_inflight)
        self.assertIsNone(ui._log_poll_seq)

    def test_ui_poll_log_mirrors_test_run_lines_into_test_activity_without_last_cmd_context(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._log_poll_seq = 52
        ui._log_poll_inflight = True
        ui._last_cmd = ("showRuntimeState", {})
        ui._recent_out_lines = {}
        ui._out_dedupe_window = 1.0
        output_lines = []
        test_lines = []
        ui._append_output = output_lines.append
        ui._append_test_output = test_lines.append
        ui._runtime_state_pending_seq = None
        ui._is_handshake_required = lambda _event: False
        ui._handle_handshake_required = lambda: None
        ui._is_owner_required = lambda _event: False
        ui._handle_owner_required = lambda: None
        ui._notify_ui_failure = lambda *_args, **_kwargs: None
        ui._tracker = type("TrackerStub", (), {"handle_event": staticmethod(lambda _event: None)})()
        ui._apply_runtime_group_command_payload = lambda _data: None
        ui._apply_robot_profile_context_from_command_event = lambda *_args: None
        ui._remember_out_line = lambda _line: None

        ui._handle_tcp_response(
            BridgeEvent(
                type="out",
                seq=52,
                name="uiPollLog",
                status="ok",
                message="",
                text=(
                    "Test started #2: mtrs_limit\n"
                    "Test #2: mtrs_limit\n"
                    "Test result #2: mtrs_limit = PASS (success success_1: success lmtSw0.pressed) time=0.52s"
                ),
                json_text="",
                ts=0.0,
                session_id="",
                state={},
                raw={},
            )
        )

        self.assertEqual(
            [
                "Test started #2: mtrs_limit",
                "Test #2: mtrs_limit",
                "Test result #2: mtrs_limit = PASS (success success_1: success lmtSw0.pressed) time=0.52s",
            ],
            output_lines,
        )
        self.assertEqual(output_lines, test_lines)
        self.assertFalse(ui._log_poll_inflight)
        self.assertIsNone(ui._log_poll_seq)

    def test_ui_poll_log_strips_hidden_prefix_chars_before_test_activity_detection(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._log_poll_seq = 53
        ui._log_poll_inflight = True
        ui._last_cmd = ("showRuntimeState", {})
        ui._recent_out_lines = {}
        ui._out_dedupe_window = 1.0
        output_lines = []
        test_lines = []
        ui._append_output = output_lines.append
        ui._append_test_output = test_lines.append
        ui._runtime_state_pending_seq = None
        ui._is_handshake_required = lambda _event: False
        ui._handle_handshake_required = lambda: None
        ui._is_owner_required = lambda _event: False
        ui._handle_owner_required = lambda: None
        ui._notify_ui_failure = lambda *_args, **_kwargs: None
        ui._tracker = type("TrackerStub", (), {"handle_event": staticmethod(lambda _event: None)})()
        ui._apply_runtime_group_command_payload = lambda _data: None
        ui._apply_robot_profile_context_from_command_event = lambda *_args: None
        ui._remember_out_line = lambda _line: None

        ui._handle_tcp_response(
            BridgeEvent(
                type="out",
                seq=53,
                name="uiPollLog",
                status="ok",
                message="",
                text=(
                    "\ufeff\u200bTest started #4: newTests_123\n"
                    "\ufeff\u200bTest #4: newTests_123\n"
                    "\ufeff\u200bTest result #4: newTests_123 = PASS"
                ),
                json_text="",
                ts=0.0,
                session_id="",
                state={},
                raw={},
            )
        )

        self.assertEqual(
            [
                "Test started #4: newTests_123",
                "Test #4: newTests_123",
                "Test result #4: newTests_123 = PASS",
            ],
            output_lines,
        )
        self.assertEqual(output_lines, test_lines)
        self.assertFalse(ui._log_poll_inflight)
        self.assertIsNone(ui._log_poll_seq)

    def test_active_presence_probe_ack_without_json_does_not_crash(self) -> None:
        refresh_calls = []

        class _Tracker:
            def __init__(self) -> None:
                self.events = []

            def handle_event(self, event) -> None:
                self.events.append(event)

            def is_pending(self) -> bool:
                return False

        ui = BringupControlUI.__new__(BringupControlUI)
        ui._runtime_state_pending_seq = None
        ui._is_handshake_required = lambda _event: False
        ui._handle_handshake_required = lambda: None
        ui._is_owner_required = lambda _event: False
        ui._handle_owner_required = lambda: None
        ui._notify_ui_failure = lambda *_args, **_kwargs: None
        ui._append_output = lambda _line: None
        ui._append_test_output = lambda _line: None
        ui._apply_runtime_group_command_payload = lambda _data: None
        ui._apply_robot_profile_context_from_command_event = lambda *_args: None
        ui._remember_out_line = lambda _line: None
        ui._cache_active_probe_results_from_command = lambda _data: refresh_calls.append("cache")
        ui._refresh_evidence_view = lambda: refresh_calls.append("refresh")
        ui.after_idle = lambda callback, *args, **kwargs: callback(*args, **kwargs)
        ui._tracker = _Tracker()
        ui._log_poll_seq = None
        ui._log_poll_inflight = False
        ui._last_cmd = ("activePresenceProbe", {})
        ui._evidence_probe_pending = True
        ui._evidence_last_probe_complete_seq = None
        ui._evidence_probe_complete_count = 0
        ui._evidence_last_probe_completed_at = None
        ui._pending_tests_boundary_transition = None
        ui._request_runtime_state_refresh = lambda: refresh_calls.append("runtime")

        ui._handle_tcp_response(
            BridgeEvent(
                type="ack",
                seq=136,
                name="activePresenceProbe",
                status="ok",
                message="Probe completed with warnings.",
                text="",
                json_text="",
                ts=0.0,
                session_id="",
                state={},
                raw={},
            )
        )

        self.assertFalse(ui._evidence_probe_pending)
        self.assertEqual(1, ui._evidence_probe_complete_count)
        self.assertIn("refresh", refresh_calls)
        self.assertIn("runtime", refresh_calls)

    def test_activate_scope_from_tests_uses_active_group_lifecycle_path(self) -> None:
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
        ui._selected_test_var = _StringVarStub("falcon9_move_150_rotations")
        ui._current_right_tab_text = lambda: "Tests"

        with patch("tools.can_nt.bringup_ui.send_tracked_command", return_value=31):
            ui._activate_scope_from_ui()

        self.assertEqual(ui._last_cmd[0], "lifecycleActivate")
        self.assertEqual(ui._last_cmd[1]["label"], GROUP_ACTIVE_NAME)
        self.assertEqual(ui._last_cmd[1]["mode"], "READ_ONLY")
        self.assertEqual(ui._last_sent_seq, 31)
        self.assertTrue(any("lifecycleActivate" in line for line in lines))

    def test_clear_test_output_clears_activity_widget(self) -> None:
        class _TextStub:
            def __init__(self) -> None:
                self.deleted = False
                self.states = []

            def configure(self, **kwargs) -> None:
                self.states.append(kwargs.get("state"))

            def delete(self, _start: str, _end: str) -> None:
                self.deleted = True

        ui = BringupControlUI.__new__(BringupControlUI)
        ui._test_lines = ["a", "b"]
        ui._test_output = _TextStub()

        ui._clear_test_output()

        self.assertEqual([], ui._test_lines)
        self.assertTrue(ui._test_output.deleted)
        self.assertEqual(["normal", "disabled"], ui._test_output.states)

    def test_handle_tests_boundary_transition_into_tests_remembers_manual_group(self) -> None:
        class _Tracker:
            def is_pending(self) -> bool:
                return False

        ui = BringupControlUI.__new__(BringupControlUI)
        ui._tcp_connected = True
        ui._tracker = _Tracker()
        ui._runtime_active_group_members = lambda: [{"label": "FALCON 9", "enabled": True}]
        calls = []
        ui._deactivate_group_blocking = lambda: calls.append("deactivate") or True
        ui._load_selected_test_into_active_group = lambda force_replace=False: calls.append(
            ("load", force_replace)
        )

        ui._handle_tests_boundary_transition("Live Topology", "Tests")

        self.assertEqual([{"label": "FALCON 9", "enabled": True}], ui._remembered_manual_active_group_members)
        self.assertEqual(["deactivate", ("load", True)], calls)

    def test_handle_tests_boundary_transition_leaving_tests_restores_manual_group(self) -> None:
        class _Tracker:
            def is_pending(self) -> bool:
                return False

        ui = BringupControlUI.__new__(BringupControlUI)
        ui._tcp_connected = True
        ui._tracker = _Tracker()
        ui._remembered_manual_active_group_members = [{"label": "SPARKMAX/NEO 25", "enabled": True}]
        calls = []
        ui._deactivate_group_blocking = lambda: calls.append("deactivate") or True
        ui._restore_manual_active_group_members = lambda: calls.append("restore")

        ui._handle_tests_boundary_transition("Tests", "Live Topology")

        self.assertEqual(["deactivate", "restore"], calls)

    def test_handle_tests_boundary_transition_defers_while_command_pending(self) -> None:
        class _Tracker:
            def is_pending(self) -> bool:
                return True

        ui = BringupControlUI.__new__(BringupControlUI)
        ui._tcp_connected = True
        ui._tracker = _Tracker()
        ui._pending_tests_boundary_transition = None

        ui._handle_tests_boundary_transition("Live Topology", "Tests")

        self.assertEqual(("Live Topology", "Tests"), ui._pending_tests_boundary_transition)

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
        ui._controlled_lifecycle_active_known = True

        with patch("tools.can_nt.bringup_ui.send_tracked_command", return_value=22):
            ui._lifecycle_deactivate_from_ui()

        self.assertEqual(ui._last_cmd[0], "lifecycleDeactivateActive")
        self.assertEqual(ui._last_cmd[1], {})
        self.assertEqual(ui._last_sent_seq, 22)
        self.assertTrue(any("lifecycleDeactivateActive" in line for line in lines))

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

    def test_live_runtime_notice_requires_activation_when_selected_test_scope_is_not_active(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        notices = []
        ui._group_owner_mode = "selected test"
        ui._runtime_active_known = False
        ui._controlled_lifecycle_active_known = True
        ui._scope_is_currently_active = lambda: False
        ui._manual_active_group_is_empty = lambda: False
        ui._set_runtime_state_notice = lambda message, level: notices.append((message, level))
        ui._clear_runtime_state_notice = lambda: notices.append(("clear", "clear"))
        ui._iter_live_views = lambda: []

        ui._apply_live_runtime_notice_from_nt_state(
            enabled=True, estopped=False, stale_state=False
        )

        self.assertEqual(
            [("Activate lifecycle first.", "warn")],
            notices,
        )

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

    def test_resolved_group_motor_targets_fall_back_to_selected_profile_catalog(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._profile_devices = {}
        ui._test_profile_devices = {
            "falcon 9": {"label": "FALCON 9", "deviceType": 2, KEY_TYPE: "motor"},
            "sparkmax/neo 25": {
                "label": "SPARKMAX/NEO 25",
                "deviceType": 2,
                KEY_TYPE: "motor",
            },
        }
        ui._latest_runtime_devices = {}

        self.assertEqual(
            ["SPARKMAX/NEO 25", "FALCON 9"],
            ui._resolved_group_motor_targets(
                {
                    "members": [
                        {"label": "SPARKMAX/NEO 25", "enabled": True},
                        {"label": "FALCON 9", "enabled": True},
                    ]
                }
            ),
        )

    def test_resolved_group_motor_targets_accept_type_only_motor_entries(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._profile_devices = {}
        ui._test_profile_devices = {
            "falcon 9": {"label": "FALCON 9", KEY_TYPE: "motor"},
        }
        ui._latest_runtime_devices = {}

        self.assertEqual(
            ["FALCON 9"],
            ui._resolved_group_motor_targets({"members": [{"label": "FALCON 9", "enabled": True}]}),
        )

    def test_resolved_group_motor_targets_fall_back_to_loaded_profiles_when_ui_catalogs_are_empty(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._profile_devices = {}
        ui._test_profile_devices = {}
        ui._latest_runtime_devices = {}

        with (
            patch("tools.can_nt.bringup_ui.list_profiles", return_value=["test_minimal_25_9"]),
            patch(
                "tools.can_nt.bringup_ui.get_profile",
                return_value=(
                    [
                        {"label": "SPARKMAX/NEO 25", "deviceType": 2, KEY_TYPE: "motor"},
                        {"label": "FALCON 9", "deviceType": 2, KEY_TYPE: "motor"},
                    ],
                    set(),
                ),
            ),
        ):
            self.assertEqual(
                ["SPARKMAX/NEO 25", "FALCON 9"],
                ui._resolved_group_motor_targets(
                    {
                        "members": [
                            {"label": "SPARKMAX/NEO 25", "enabled": True},
                            {"label": "FALCON 9", "enabled": True},
                        ]
                    }
                ),
            )

    def test_resolved_group_motor_targets_accept_string_members(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._profile_devices = {
            "sparkmax/neo 25": {"label": "SPARKMAX/NEO 25", "deviceType": 2, KEY_TYPE: "motor"},
            "falcon 9": {"label": "FALCON 9", "deviceType": 2, KEY_TYPE: "motor"},
        }
        ui._test_profile_devices = {}
        ui._latest_runtime_devices = {}

        self.assertEqual(
            ["SPARKMAX/NEO 25", "FALCON 9"],
            ui._resolved_group_motor_targets({"members": ["SPARKMAX/NEO 25", "FALCON 9"]}),
        )

    def test_live_group_right_click_uses_group_payload_targets(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._profile_devices = {
            "sparkmax/neo 25": {"label": "SPARKMAX/NEO 25", "deviceType": 2, KEY_TYPE: "motor"},
            "falcon 9": {"label": "FALCON 9", "deviceType": 2, KEY_TYPE: "motor"},
        }
        ui._test_profile_devices = {}
        ui._latest_runtime_devices = {}
        ui._controlled_lifecycle_active_known = False
        ui._tcp_connected = True
        ui._state_stale = False
        ui._robot_estopped_known = False
        ui._robot_enabled_known = True
        ui._tracker = type("TrackerStub", (), {"is_pending": staticmethod(lambda: False)})()
        ui._request_runtime_state_refresh = lambda: None
        opened = []
        lines = []
        ui._append_output = lines.append
        ui._open_manual_group_duty_targets = (
            lambda group_name, targets, x_root, y_root: opened.append(
                (group_name, list(targets), x_root, y_root)
            )
        )

        ui._on_live_group_right_click(
            {
                "name": "motors",
                "group": {
                    "name": "motors",
                    "members": [
                        {"label": "SPARKMAX/NEO 25", "enabled": True},
                        {"label": "FALCON 9", "enabled": True},
                    ],
                },
            },
            type("Event", (), {"x_root": 11, "y_root": 22})(),
        )

        self.assertEqual([("motors", ["SPARKMAX/NEO 25", "FALCON 9"], 11, 22)], opened)
        self.assertEqual([], lines)

    def test_open_manual_group_duty_targets_preserves_group_transport_for_static_groups(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._tcp_connected = True
        ui._state_stale = False
        ui._robot_estopped_known = False
        ui._robot_enabled_known = True
        ui._tracker = type("TrackerStub", (), {"is_pending": staticmethod(lambda: False)})()
        ui._append_output = lambda _line: None
        ui._request_runtime_state_refresh = lambda: None
        popup_calls = []
        live_view_calls = []
        ui._open_manual_duty_popup = (
            lambda label, targets, group_name, x_root, y_root: popup_calls.append(
                (label, list(targets), group_name, x_root, y_root)
            )
        )
        ui._iter_live_views = lambda: [
            type(
                "LiveViewStub",
                (),
                {
                    "set_group_run_inspector": lambda _self, group_name, targets: live_view_calls.append(
                        (group_name, list(targets))
                    )
                },
            )()
        ]

        ui._open_manual_group_duty_targets("motors", ["SPARKMAX/NEO 25", "FALCON 9"], 11, 22)

        self.assertEqual(
            [("motors", ["SPARKMAX/NEO 25", "FALCON 9"], "motors", 11, 22)],
            popup_calls,
        )
        self.assertEqual([("motors", ["SPARKMAX/NEO 25", "FALCON 9"])], live_view_calls)

    def test_open_manual_group_duty_targets_preserves_group_transport_for_active_group(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._tcp_connected = True
        ui._state_stale = False
        ui._robot_estopped_known = False
        ui._robot_enabled_known = True
        ui._tracker = type("TrackerStub", (), {"is_pending": staticmethod(lambda: False)})()
        ui._append_output = lambda _line: None
        ui._request_runtime_state_refresh = lambda: None
        popup_calls = []
        ui._open_manual_duty_popup = (
            lambda label, targets, group_name, x_root, y_root: popup_calls.append(
                (label, list(targets), group_name, x_root, y_root)
            )
        )
        ui._iter_live_views = lambda: []

        ui._open_manual_group_duty_targets(GROUP_ACTIVE_NAME, ["FALCON 9"], 11, 22)

        self.assertEqual(
            [(GROUP_ACTIVE_NAME, ["FALCON 9"], GROUP_ACTIVE_NAME, 11, 22)],
            popup_calls,
        )

    def test_flush_manual_duty_send_uses_group_command_for_static_multi_motor_group(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._manual_duty_pending_after = None
        ui._manual_duty_label = "motors"
        ui._manual_duty_targets = ["SPARKMAX/NEO 25", "FALCON 9"]
        ui._manual_duty_group_name = "motors"
        ui._manual_duty_var = _ValueVarStub(0.25)
        ui._manual_duty_last_sent_value = None
        ui._manual_duty_last_sent_at = 0.0
        ui._tcp_connected = True
        ui._state_stale = False
        ui._robot_estopped_known = False
        ui._robot_enabled_known = True
        ui._append_output = lambda _line: None
        ui._request_runtime_state_refresh = lambda: None
        ui.after_idle = lambda callback: callback()
        ui._record_manual_motion_command = lambda _label, _duty: None
        ui._iter_live_views = lambda: []
        sent = []
        ui._send_tcp_command = lambda name, args: sent.append((name, dict(args or {}))) or len(sent)

        ui._flush_manual_duty_send()

        self.assertEqual(
            [
                (
                    MANUAL_GROUP_DUTY_CMD_SET,
                    {
                        GROUP_RUN_ARG_GROUP: "motors",
                        MANUAL_DUTY_ARG_DUTY: 0.25,
                    },
                )
            ],
            sent,
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

    def test_active_group_toggle_is_blocked_until_runtime_state_is_loaded(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._controlled_lifecycle_active_known = False
        ui._tcp_connected = True
        ui._runtime_state_seen = False
        ui._append_output_lines = []
        ui._append_output = ui._append_output_lines.append
        refresh_calls = []
        ui._request_runtime_state_refresh = lambda: refresh_calls.append("refresh")
        ui.after_idle = lambda callback: callback()
        ui._tracker = type(
            "TrackerStub",
            (),
            {"is_pending": staticmethod(lambda: False)},
        )()
        ui._last_cmd = None
        ui._send_and_wait = lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("should not send before runtime state is loaded")
        )

        ui._on_active_group_member_toggled("FALCON 9", True)

        self.assertTrue(
            any("Runtime state not loaded yet" in line for line in ui._append_output_lines)
        )
        self.assertEqual(["refresh"], refresh_calls)

    def test_active_group_toggle_waits_for_command_result_before_refresh(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._controlled_lifecycle_active_known = False
        ui._tcp_connected = True
        ui._runtime_state_seen = True
        ui._append_output = lambda _line: None
        refresh_calls = []
        ui._request_runtime_state_refresh = lambda: refresh_calls.append("refresh")
        ui.after_idle = lambda callback: callback()
        ui._tracker = type(
            "TrackerStub",
            (),
            {"is_pending": staticmethod(lambda: False)},
        )()
        calls = []
        ui._send_and_wait = lambda command, args: calls.append((command, args)) or True

        ui._on_active_group_member_toggled("FALCON 9", True)

        self.assertEqual(
            [("groupAddDevice", {"group": "active-group", "device": "FALCON 9"})],
            calls,
        )
        self.assertEqual(["refresh"], refresh_calls)

if __name__ == "__main__":
    unittest.main()
