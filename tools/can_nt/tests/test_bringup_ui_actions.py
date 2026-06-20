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
    HIDDEN_LEFT_RAIL_COMMANDS,
    INVENTORY_KEY_ACTION_KIND,
    INVENTORY_KEY_SOURCE,
    KEY_TYPE,
    TEST_SOURCE_COMPLETION_MODE_CLEAR,
    TEST_SOURCE_COMPLETION_MODE_NONE,
    TEST_SOURCE_COMPLETION_MODE_READ,
    TEST_SOURCE_COMPLETION_MODE_WRITE,
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

if __name__ == "__main__":
    unittest.main()
