from __future__ import annotations

"""
NAME
    test_bridge_cli_groups.py - Validate local CLI group output uses shared group-state fields.
"""

import io
import json
import unittest
from contextlib import redirect_stdout

from tools.can_nt.bridge_cli import BridgeCli
from tools.can_nt.status import SS__NORMAL
from tools.common.profile_constants import (
    KEY_BRIDGE_BINDINGS,
    KEY_BRIDGE_BY_PROFILE,
    KEY_BRIDGE_GROUPS,
    KEY_DEVICES,
    KEY_ENABLED,
    KEY_LABEL,
    KEY_MEMBERS,
    KEY_NAME,
    KEY_PROFILE,
)


PROFILE_NAME = "demo"
GROUP_NAME = "Front Left"
DEVICE_A = "A"
DEVICE_B = "B"
SHOW_TARGET_GROUPS = "groups"
SHOW_TARGET_GROUP = "group"
KEY_PRIMARY_LABEL = "primaryLabel"
KEY_MEMBER_COUNT = "memberCount"
KEY_ENABLED_MEMBER_COUNT = "enabledMemberCount"
KEY_HAS_MEMBERS = "hasMembers"
KEY_ALL_ENABLED_MEMBERS_PRESENT = "allEnabledMembersPresent"
KEY_LOCKED = "locked"
KEY_INVALID = "invalid"
KEY_SCOPE_ACTIVE = "scopeActive"
KEY_RUNTIME_PRESENT = "runtimePresent"
KEY_INSTANTIATED = "instantiated"
KEY_TESTABLE = "testable"
MESSAGE_SOURCE_LOCAL = "SOURCE: local"


def _build_cli() -> BridgeCli:
    cli = BridgeCli.__new__(BridgeCli)
    cli._local_root_payload = {}
    cli._local_config = {
        KEY_PROFILE: PROFILE_NAME,
        KEY_DEVICES: [],
        KEY_BRIDGE_BY_PROFILE: {
            PROFILE_NAME: {
                KEY_BRIDGE_GROUPS: [
                    {
                        KEY_NAME: GROUP_NAME,
                        KEY_ENABLED: True,
                        KEY_MEMBERS: [
                            {KEY_LABEL: DEVICE_A, KEY_ENABLED: True},
                            {KEY_LABEL: DEVICE_B, KEY_ENABLED: False},
                        ],
                        KEY_BRIDGE_BINDINGS: [],
                    }
                ]
            }
        },
    }
    cli._groups_profile = PROFILE_NAME
    cli._active_group_members = []
    cli._can_mappings = {}
    cli._active_profile_name = lambda: PROFILE_NAME
    cli._local_groups = BridgeCli._local_groups.__get__(cli, BridgeCli)
    cli._active_group_payload = BridgeCli._active_group_payload.__get__(cli, BridgeCli)
    cli._resolved_local_group_state = BridgeCli._resolved_local_group_state.__get__(cli, BridgeCli)
    cli._resolved_local_group_payload = BridgeCli._resolved_local_group_payload.__get__(cli, BridgeCli)
    return cli


def _json_line(output: str) -> dict[str, object]:
    lines = [line for line in output.splitlines() if line.strip()]
    if lines and lines[0].strip() == MESSAGE_SOURCE_LOCAL:
        lines = lines[1:]
    return json.loads(lines[-1])


class BridgeCliGroupsTests(unittest.TestCase):
    def test_show_groups_local_json_uses_shared_group_summary_fields(self) -> None:
        cli = _build_cli()

        output = io.StringIO()
        with redirect_stdout(output):
            result = cli._show_local(
                SHOW_TARGET_GROUPS,
                ["show"],
                json_output=True,
                pretty=False,
                grouped=False,
            )

        self.assertEqual(result.code, SS__NORMAL)
        payload = _json_line(output.getvalue())
        groups = payload[KEY_BRIDGE_GROUPS]
        self.assertEqual(groups[1][KEY_NAME], GROUP_NAME)
        self.assertEqual(groups[1][KEY_PRIMARY_LABEL], DEVICE_A)
        self.assertEqual(groups[1][KEY_MEMBER_COUNT], 2)
        self.assertEqual(groups[1][KEY_ENABLED_MEMBER_COUNT], 1)
        self.assertTrue(groups[1][KEY_HAS_MEMBERS])
        self.assertFalse(groups[1][KEY_ALL_ENABLED_MEMBERS_PRESENT])

    def test_show_group_local_json_uses_shared_member_fact_fields(self) -> None:
        cli = _build_cli()

        output = io.StringIO()
        with redirect_stdout(output):
            result = cli._show_local(
                SHOW_TARGET_GROUP,
                ["show", GROUP_NAME],
                json_output=True,
                pretty=False,
                grouped=False,
            )

        self.assertEqual(result.code, SS__NORMAL)
        payload = _json_line(output.getvalue())
        self.assertEqual(payload[KEY_PRIMARY_LABEL], DEVICE_A)
        members = payload[KEY_MEMBERS]
        self.assertEqual(members[0][KEY_LABEL], DEVICE_A)
        self.assertTrue(members[0][KEY_ENABLED])
        self.assertFalse(members[0][KEY_LOCKED])
        self.assertFalse(members[0][KEY_INVALID])
        self.assertFalse(members[0][KEY_SCOPE_ACTIVE])
        self.assertFalse(members[0][KEY_RUNTIME_PRESENT])
        self.assertFalse(members[0][KEY_INSTANTIATED])
        self.assertFalse(members[0][KEY_TESTABLE])


if __name__ == "__main__":
    unittest.main()
