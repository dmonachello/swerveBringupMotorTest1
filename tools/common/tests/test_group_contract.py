from __future__ import annotations

import unittest

from tools.common.group_contract import (
    device_entry_is_motor,
    find_device_entry_by_label,
    find_group_by_name,
    group_member_labels,
    group_member_map,
    group_primary_label,
    merge_effective_groups,
    resolve_group_motor_targets,
)


class GroupContractTests(unittest.TestCase):
    """
    NAME
        GroupContractTests - Validate shared host-side group normalization and resolution.
    """

    def test_group_member_labels_accept_dict_and_string_shapes(self) -> None:
        group = {
            "name": "motors",
            "members": [
                {"label": "SPARKMAX/NEO 25", "enabled": True},
                {"device": "FALCON 9", "enabled": True},
                "controller0",
            ],
        }

        self.assertEqual(
            ["SPARKMAX/NEO 25", "FALCON 9", "controller0"],
            group_member_labels(group, enabled_only=False),
        )

    def test_group_member_labels_respect_enabled_only(self) -> None:
        group = {
            "name": "motors",
            "members": [
                {"label": "SPARKMAX/NEO 25", "enabled": True},
                {"label": "FALCON 9", "enabled": False},
                "controller0",
            ],
        }

        self.assertEqual(
            ["SPARKMAX/NEO 25", "controller0"],
            group_member_labels(group, enabled_only=True),
        )

    def test_group_member_map_returns_dict_entries_for_dict_and_string_members(self) -> None:
        group = {
            "name": "motors",
            "members": [
                {"label": "SPARKMAX/NEO 25", "enabled": True},
                "FALCON 9",
            ],
        }

        self.assertEqual(
            {
                "sparkmax/neo 25": {"label": "SPARKMAX/NEO 25", "enabled": True},
                "falcon 9": {"label": "FALCON 9", "enabled": True},
            },
            group_member_map(group, enabled_only=False),
        )

    def test_group_primary_label_returns_first_enabled_label(self) -> None:
        group = {
            "name": "motors",
            "members": [
                {"label": "SPARKMAX/NEO 25", "enabled": False},
                {"label": "FALCON 9", "enabled": True},
            ],
        }

        self.assertEqual("SPARKMAX/NEO 25", group_primary_label(group, enabled_only=False))
        self.assertEqual("FALCON 9", group_primary_label(group, enabled_only=True))

    def test_merge_effective_groups_preserves_static_members_when_runtime_only_has_counts(self) -> None:
        merged = merge_effective_groups(
            [
                {
                    "name": "motors",
                    "enabled": True,
                    "members": [
                        {"label": "SPARKMAX/NEO 25", "enabled": True},
                        {"label": "FALCON 9", "enabled": True},
                    ],
                    "bindings": [{"input": "controller0.rightY", "kind": "analog"}],
                }
            ],
            [
                {
                    "name": "motors",
                    "enabled": True,
                    "memberCount": 2,
                    "bindingCount": 1,
                }
            ],
        )

        self.assertEqual(1, len(merged))
        self.assertEqual(
            [
                {"label": "SPARKMAX/NEO 25", "enabled": True},
                {"label": "FALCON 9", "enabled": True},
            ],
            merged[0]["members"],
        )
        self.assertEqual(
            [{"input": "controller0.rightY", "kind": "analog"}],
            merged[0]["bindings"],
        )

    def test_find_group_by_name_matches_normalized_name(self) -> None:
        groups = [
            {"name": "motors", "members": []},
            {"name": "active-group", "members": []},
        ]

        self.assertEqual({"name": "motors", "members": []}, find_group_by_name(groups, "MOTORS"))
        self.assertIsNone(find_group_by_name(groups, "missing"))

    def test_find_device_entry_by_label_checks_catalogs_then_fallback_lists(self) -> None:
        catalogs = [
            {"sparkmax/neo 25": {"label": "SPARKMAX/NEO 25", "deviceType": 2}},
            {},
        ]
        fallback_lists = [
            [
                {"label": "FALCON 9", "deviceType": 2},
            ]
        ]

        self.assertEqual(
            {"label": "SPARKMAX/NEO 25", "deviceType": 2},
            find_device_entry_by_label("SPARKMAX/NEO 25", catalogs),
        )
        self.assertEqual(
            {"label": "FALCON 9", "deviceType": 2},
            find_device_entry_by_label("FALCON 9", catalogs, fallback_device_lists=fallback_lists),
        )

    def test_device_entry_is_motor_accepts_numeric_and_symbolic_shapes(self) -> None:
        self.assertTrue(device_entry_is_motor({"deviceType": 2}))
        self.assertTrue(device_entry_is_motor({"type": "motor"}))
        self.assertFalse(device_entry_is_motor({"type": "limitSwitch"}))

    def test_resolve_group_motor_targets_uses_shared_member_and_device_contract(self) -> None:
        group = {
            "name": "motors",
            "members": [
                {"label": "SPARKMAX/NEO 25", "enabled": True},
                {"device": "FALCON 9", "enabled": True},
                {"label": "controller0", "enabled": True},
                {"label": "disabled motor", "enabled": False},
            ],
        }
        catalogs = [
            {
                "sparkmax/neo 25": {"label": "SPARKMAX/NEO 25", "deviceType": 2},
                "controller0": {"label": "controller0", "type": "xboxController"},
            }
        ]
        fallback_lists = [
            [
                {"label": "FALCON 9", "type": "motor"},
                {"label": "disabled motor", "type": "motor"},
            ]
        ]

        self.assertEqual(
            ["SPARKMAX/NEO 25", "FALCON 9"],
            resolve_group_motor_targets(group, catalogs, fallback_device_lists=fallback_lists),
        )


if __name__ == "__main__":
    unittest.main()
