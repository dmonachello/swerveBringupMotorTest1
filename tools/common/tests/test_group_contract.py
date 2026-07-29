from __future__ import annotations

"""
NAME
    test_group_contract.py - Unit tests for shared group/member resolution helpers.
"""

import unittest

from tools.common.group_contract import (
    resolve_group_member_state,
    runtime_device_singleton_backed,
)


class GroupContractTests(unittest.TestCase):
    """
    NAME
        GroupContractTests - Validate shared runtime-backed group member rules.
    """

    def test_runtime_device_singleton_backed_uses_runtime_lifecycle_kind(self) -> None:
        self.assertTrue(runtime_device_singleton_backed({"lifecycleKind": "SINGLETON"}))
        self.assertFalse(runtime_device_singleton_backed({"lifecycleKind": "NORMAL"}))
        self.assertFalse(runtime_device_singleton_backed({"label": "pdp"}))

    def test_resolve_group_member_state_locks_instantiated_singleton_from_runtime_payload(self) -> None:
        state = resolve_group_member_state(
            label="pdp",
            enabled=True,
            locked=False,
            invalid=False,
            runtime_state_by_label={
                "pdp": {
                    "instantiated": False,
                    "lifecycleState": "controlled-instantiated",
                    "lifecycleKind": "SINGLETON",
                    "testable": True,
                    "presenceConfidence": 1.0,
                }
            },
            scope_active=False,
        )

        self.assertTrue(state.locked)
        self.assertTrue(state.instantiated)
        self.assertTrue(state.runtime_present)


if __name__ == "__main__":
    unittest.main()
