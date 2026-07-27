from __future__ import annotations

"""
NAME
    test_cross_surface_runtime_agreement.py - Cross-surface runtime agreement regressions.
"""

import unittest

from tools.can_nt.bringup_ui import BringupControlUI
from tools.can_nt.host_ui_state_service import (
    resolve_active_group_summary_state,
    resolve_manual_duty_binding_state,
)
from tools.can_topology import live_topology_view as live_view_module


class CrossSurfaceRuntimeAgreementTests(unittest.TestCase):
    """
    NAME
        CrossSurfaceRuntimeAgreementTests - Validate shared runtime-state meaning across host surfaces.
    """

    def _make_live_view(self) -> live_view_module.LiveTopologyView:
        view = live_view_module.LiveTopologyView.__new__(live_view_module.LiveTopologyView)
        view._runtime_state_seen = True
        view._controlled_lifecycle_active = True
        view._scope_transition_pending = False
        view._runtime_state = {"falcon 9": {"presenceConfidence": 1.0}}
        view._nodes = []
        return view

    def test_active_group_status_matches_shared_host_resolver(self) -> None:
        member_map = {"falcon 9": {"label": "FALCON 9", "enabled": True}}
        runtime_state_by_label = {"falcon 9": {"presenceConfidence": 1.0}}
        shared = resolve_active_group_summary_state(
            runtime_state_seen=True,
            controlled_lifecycle_active=True,
            member_map=member_map,
            runtime_state_by_label=runtime_state_by_label,
            primary_label="FALCON 9",
        )
        view = self._make_live_view()

        status_text = view._active_group_status_text({"name": "active-group"}, member_map)

        self.assertEqual(shared.status_text, status_text)

    def test_binding_ownership_shared_gate_allows_manual_duty(self) -> None:
        runtime_groups = [
            {
                "name": "motors",
                "bindingActive": True,
                "members": [{"label": "FALCON 9", "enabled": True}],
            }
        ]
        shared = resolve_manual_duty_binding_state(
            target_labels=["FALCON 9"],
            runtime_groups=runtime_groups,
        )
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._latest_runtime_state_payload = {"groups": runtime_groups}

        ui_reason = ui._manual_duty_binding_block_message_for_targets(["FALCON 9"])

        self.assertTrue(shared.allowed)
        self.assertEqual("", shared.blocked_reason)
        self.assertEqual(shared.blocked_reason, ui_reason)

    def test_ui_group_popup_block_clears_when_runtime_binding_is_inactive(self) -> None:
        ui = BringupControlUI.__new__(BringupControlUI)
        ui._tcp_connected = True
        ui._runtime_state_seen = True
        ui._state_stale = False
        ui._robot_estopped_known = False
        ui._robot_enabled_known = True
        ui._controlled_lifecycle_active_known = False
        ui._tracker = type("TrackerStub", (), {"is_pending": staticmethod(lambda: False)})()
        ui._latest_runtime_devices = {
            "falcon 9": {"label": "FALCON 9", "testable": True},
        }
        ui._latest_runtime_state_payload = {
            "groups": [
                {
                    "name": "motors",
                    "bindingActive": False,
                    "members": [{"label": "FALCON 9", "enabled": True}],
                }
            ]
        }
        popup_calls = []
        output_lines = []
        ui._append_output = output_lines.append
        ui._request_runtime_state_refresh = lambda: None
        ui._open_manual_duty_popup = (
            lambda label, targets, group_name, x_root, y_root: popup_calls.append(
                (label, list(targets), group_name, x_root, y_root)
            )
        )
        ui._iter_live_views = lambda: []

        ui._open_manual_group_duty_targets("active-group", ["FALCON 9"], 11, 22)

        self.assertEqual(
            [("active-group", ["FALCON 9"], "active-group", 11, 22)],
            popup_calls,
        )
        self.assertEqual([], output_lines)


if __name__ == "__main__":
    unittest.main()
