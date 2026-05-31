"""
NAME
    test_bringup_ui_actions.py - Unit tests for merged Bringup UI action metadata.
"""

from __future__ import annotations

import unittest

from tools.can_nt.bringup_ui import (
    ACTION_KIND_REMOTE_COMMAND,
    ACTIONS_BY_NAME,
    ACTION_SOURCE_ROBOT,
    INVENTORY_KEY_ACTION_KIND,
    INVENTORY_KEY_SOURCE,
    _action_sections,
    _merge_host_ui_actions,
)
from tools.can_nt.host_ui_actions import (
    ACTION_KIND_HOST_LOCAL,
    ACTION_SOURCE_HOST,
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

    def test_action_sections_exclude_remote_commands_not_allowed_for_host_ui(self) -> None:
        sections = _action_sections()
        flattened = [command for _section, items in sections for _label, command in items]
        self.assertNotIn("canSweep", flattened)


if __name__ == "__main__":
    unittest.main()
