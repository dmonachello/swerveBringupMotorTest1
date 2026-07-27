"""
NAME
    test_host_ui_state_service.py - Unit tests for shared host-side UI context state.
"""

from __future__ import annotations

import unittest

from tools.can_nt.host_ui_state_service import (
    ACTIVE_GROUP_EDIT_BLOCKED_LOCKED_TEXT,
    ACTIVE_GROUP_STATUS_EDITABLE_TEXT,
    ACTIVE_GROUP_STATUS_EMPTY_TEXT,
    ACTIVE_GROUP_STATUS_LOCKED_TEXT,
    ACTIVE_GROUP_STATUS_RESYNC_TEXT,
    BLANK_REASON_LOCAL_PROFILE_REQUIRED,
    HOST_ACTION_BLOCKED_BUSY_TEXT,
    HOST_ACTION_BLOCKED_NOT_CONNECTED_TEXT,
    MANUAL_DUTY_BLOCKED_TRANSITION_TEXT,
    MANUAL_DUTY_BLOCKED_WAITING_TEXT,
    MANUAL_DUTY_BLOCKED_BINDING_ACTIVE_TEXT,
    MANUAL_DUTY_BLOCKED_CONTROLLED_SCOPE_TEXT,
    PROFILE_CONTEXT_SOURCE_BLANK,
    PROFILE_CONTEXT_SOURCE_ROBOT_ACTIVE_RUNTIME,
    PROFILE_NONE,
    RUNTIME_FETCH_BLOCK_BUSY,
    RUNTIME_FETCH_SOURCE_REST,
    RUNNABLE_PANEL_INACTIVE_HEADLINE,
    RUNNABLE_PANEL_READY_HEADLINE,
    RUNNABLE_PANEL_WAITING_HEADLINE,
    RUNNABLE_SCOPE_DETAIL_DISABLED,
    RUNNABLE_SCOPE_DETAIL_SELECT_PROFILE,
    RUNNABLE_SCOPE_KIND_MANUAL,
    RUNNABLE_SCOPE_KIND_SELECTED_TEST,
    RUNNABLE_SCOPE_PANEL_RESYNC_DETAIL,
    RUNNABLE_SCOPE_PANEL_WAITING_DETAIL,
    TEST_SCOPE_STATUS_NO_SELECTION_DETAIL,
    TEST_SCOPE_STATUS_RUNNING_DETAIL,
    resolve_active_group_edit_action_state,
    resolve_manual_duty_access_state,
    resolve_manual_duty_action_state,
    resolve_active_scope_membership_state,
    resolve_diagnostic_profile_state,
    resolve_manual_duty_binding_state,
    resolve_manual_duty_scope_state,
    resolve_override_action_state,
    resolve_runtime_state_fetch_state,
    resolve_scope_control_state,
    resolve_runnable_scope_state,
    resolve_tests_active_group_member_rows,
    resolve_topology_scene_state,
    resolve_ui_context_state,
    should_clear_runtime_event_notice,
)


class HostUiStateServiceTests(unittest.TestCase):
    """
    NAME
        HostUiStateServiceTests - Validate shared host-side profile and runnable-state rules.
    """

    def test_resolve_diagnostic_profile_state_requires_local_selection(self) -> None:
        state = resolve_diagnostic_profile_state(
            PROFILE_NONE,
            "test_minimal_25_9",
            "test_minimal_25_9",
            local_profile_required=True,
        )

        self.assertTrue(state.show_blank_profile_state)
        self.assertEqual(PROFILE_NONE, state.effective_profile)
        self.assertEqual(BLANK_REASON_LOCAL_PROFILE_REQUIRED, state.blank_reason)
        self.assertEqual(PROFILE_CONTEXT_SOURCE_BLANK, state.profile_context_source)

    def test_resolve_ui_context_state_tracks_scope_and_transport_flags(self) -> None:
        state = resolve_ui_context_state(
            local_selected_profile="test_minimal_25_9",
            robot_selected_profile="robot_selected",
            robot_active_runtime_profile="robot_active",
            selected_test_name="smoke_test",
            scope_kind=RUNNABLE_SCOPE_KIND_SELECTED_TEST,
            transport_connected=True,
            handshake_ready=False,
            has_robot_runtime_state=True,
        )

        self.assertEqual("test_minimal_25_9", state.local_selected_profile)
        self.assertEqual("robot_selected", state.robot_selected_profile)
        self.assertEqual("robot_active", state.robot_active_runtime_profile)
        self.assertEqual("smoke_test", state.selected_test_name)
        self.assertEqual(RUNNABLE_SCOPE_KIND_SELECTED_TEST, state.scope_kind)
        self.assertTrue(state.has_local_profile_selection)
        self.assertTrue(state.transport_connected)
        self.assertFalse(state.handshake_ready)
        self.assertTrue(state.has_robot_runtime_state)

    def test_resolve_diagnostic_profile_state_prefers_robot_active_runtime(self) -> None:
        state = resolve_diagnostic_profile_state(
            "local_profile",
            "robot_selected",
            "robot_active",
            local_profile_required=True,
        )

        self.assertFalse(state.show_blank_profile_state)
        self.assertEqual("robot_active", state.effective_profile)
        self.assertEqual(PROFILE_CONTEXT_SOURCE_ROBOT_ACTIVE_RUNTIME, state.profile_context_source)

    def test_resolve_topology_scene_state_blanks_when_profile_context_is_blank(self) -> None:
        state = resolve_topology_scene_state(
            effective_profile=PROFILE_NONE,
            show_blank_profile_state=True,
            blank_reason=BLANK_REASON_LOCAL_PROFILE_REQUIRED,
            current_profile_name="test_minimal_25_9",
        )

        self.assertEqual(PROFILE_NONE, state.profile_name)
        self.assertTrue(state.is_blank)
        self.assertEqual(BLANK_REASON_LOCAL_PROFILE_REQUIRED, state.blank_reason)
        self.assertFalse(state.active_group_meaningful)
        self.assertTrue(state.should_reload)

    def test_resolve_topology_scene_state_skips_reload_when_profile_is_unchanged(self) -> None:
        state = resolve_topology_scene_state(
            effective_profile="test_minimal_25_9",
            show_blank_profile_state=False,
            blank_reason="",
            current_profile_name="test_minimal_25_9",
        )

        self.assertEqual("test_minimal_25_9", state.profile_name)
        self.assertFalse(state.is_blank)
        self.assertTrue(state.active_group_meaningful)
        self.assertFalse(state.should_reload)

    def test_resolve_runnable_scope_state_waits_before_runtime_arrives(self) -> None:
        state = resolve_runnable_scope_state(
            scope_kind=RUNNABLE_SCOPE_KIND_MANUAL,
            local_selected_profile="test_minimal_25_9",
            local_profile_required=True,
            tcp_connected=True,
            runtime_state_seen=False,
            stale_state=False,
            robot_enabled=True,
            robot_estopped=False,
            robot_mode="teleop",
            manual_group_empty=False,
            scope_active=False,
        )

        self.assertEqual(RUNNABLE_PANEL_WAITING_HEADLINE, state.headline)
        self.assertEqual(RUNNABLE_SCOPE_PANEL_WAITING_DETAIL, state.detail)
        self.assertFalse(state.activation_allowed)

    def test_resolve_runnable_scope_state_waits_for_post_transition_resync(self) -> None:
        state = resolve_runnable_scope_state(
            scope_kind=RUNNABLE_SCOPE_KIND_MANUAL,
            local_selected_profile="test_minimal_25_9",
            local_profile_required=True,
            tcp_connected=True,
            runtime_state_seen=True,
            stale_state=False,
            robot_enabled=True,
            robot_estopped=False,
            robot_mode="teleop",
            manual_group_empty=False,
            scope_active=False,
            transition_pending=True,
        )

        self.assertEqual(RUNNABLE_PANEL_WAITING_HEADLINE, state.headline)
        self.assertEqual(RUNNABLE_SCOPE_PANEL_RESYNC_DETAIL, state.detail)
        self.assertTrue(state.transition_pending)
        self.assertFalse(state.activation_allowed)

    def test_resolve_runnable_scope_state_blocks_manual_scope_without_profile(self) -> None:
        state = resolve_runnable_scope_state(
            scope_kind=RUNNABLE_SCOPE_KIND_MANUAL,
            local_selected_profile=PROFILE_NONE,
            local_profile_required=True,
            tcp_connected=True,
            runtime_state_seen=True,
            stale_state=False,
            robot_enabled=True,
            robot_estopped=False,
            robot_mode="teleop",
            manual_group_empty=False,
            scope_active=False,
        )

        self.assertEqual(RUNNABLE_PANEL_INACTIVE_HEADLINE, state.headline)
        self.assertEqual(RUNNABLE_SCOPE_DETAIL_SELECT_PROFILE, state.detail)
        self.assertFalse(state.activation_allowed)

    def test_resolve_runnable_scope_state_ready_when_scope_active(self) -> None:
        state = resolve_runnable_scope_state(
            scope_kind=RUNNABLE_SCOPE_KIND_MANUAL,
            local_selected_profile="test_minimal_25_9",
            local_profile_required=True,
            tcp_connected=True,
            runtime_state_seen=True,
            stale_state=False,
            robot_enabled=True,
            robot_estopped=False,
            robot_mode="teleop",
            manual_group_empty=False,
            scope_active=True,
        )

        self.assertEqual(RUNNABLE_PANEL_READY_HEADLINE, state.headline)
        self.assertEqual("ready", state.level)
        self.assertEqual("", state.blocked_reason)
        self.assertTrue(state.deactivation_allowed)

    def test_resolve_runtime_state_fetch_state_blocks_while_command_pending(self) -> None:
        state = resolve_runtime_state_fetch_state(
            tcp_connected=True,
            handshake_done=True,
            tracker_pending=True,
            log_poll_inflight=False,
        )

        self.assertFalse(state.allowed)
        self.assertEqual(RUNTIME_FETCH_BLOCK_BUSY, state.blocked_reason)

    def test_resolve_runtime_state_fetch_state_allows_rest_fetch_when_idle(self) -> None:
        state = resolve_runtime_state_fetch_state(
            tcp_connected=True,
            handshake_done=True,
            tracker_pending=False,
            log_poll_inflight=False,
        )

        self.assertTrue(state.allowed)
        self.assertEqual("", state.blocked_reason)
        self.assertEqual(RUNTIME_FETCH_SOURCE_REST, state.fetch_source)

    def test_resolve_scope_control_state_blocks_activation_during_transition(self) -> None:
        runnable_state = resolve_runnable_scope_state(
            scope_kind=RUNNABLE_SCOPE_KIND_MANUAL,
            local_selected_profile="test_minimal_25_9",
            local_profile_required=True,
            tcp_connected=True,
            runtime_state_seen=True,
            stale_state=False,
            robot_enabled=True,
            robot_estopped=False,
            robot_mode="teleop",
            manual_group_empty=False,
            scope_active=False,
        )

        state = resolve_scope_control_state(
            scope_kind=RUNNABLE_SCOPE_KIND_MANUAL,
            runtime_ui_ready=True,
            tracker_pending=False,
            stale_state=False,
            runtime_state_seen=True,
            controlled_lifecycle_active=False,
            transition_pending=True,
            runnable_scope_state=runnable_state,
            selected_test_name=PROFILE_NONE,
            selected_test_ready=False,
            selected_test_invalid=False,
            selected_test_running=False,
            selected_test_runtime_block_reason="",
        )

        self.assertFalse(state.activate_allowed)
        self.assertFalse(state.active_group_editable)
        self.assertEqual(RUNNABLE_SCOPE_PANEL_RESYNC_DETAIL, state.blocked_reason)

    def test_resolve_scope_control_state_requires_selected_test_before_tests_activation(self) -> None:
        runnable_state = resolve_runnable_scope_state(
            scope_kind=RUNNABLE_SCOPE_KIND_SELECTED_TEST,
            local_selected_profile="test_minimal_25_9",
            local_profile_required=True,
            tcp_connected=True,
            runtime_state_seen=True,
            stale_state=False,
            robot_enabled=True,
            robot_estopped=False,
            robot_mode="teleop",
            manual_group_empty=False,
            scope_active=False,
        )

        state = resolve_scope_control_state(
            scope_kind=RUNNABLE_SCOPE_KIND_SELECTED_TEST,
            runtime_ui_ready=True,
            tracker_pending=False,
            stale_state=False,
            runtime_state_seen=True,
            controlled_lifecycle_active=False,
            transition_pending=False,
            runnable_scope_state=runnable_state,
            selected_test_name=PROFILE_NONE,
            selected_test_ready=False,
            selected_test_invalid=False,
            selected_test_running=False,
            selected_test_runtime_block_reason="",
        )

        self.assertFalse(state.activate_allowed)
        self.assertFalse(state.run_selected_allowed)
        self.assertEqual(TEST_SCOPE_STATUS_NO_SELECTION_DETAIL, state.blocked_reason)

    def test_resolve_manual_duty_access_state_waits_for_runtime_state(self) -> None:
        state = resolve_manual_duty_access_state(
            tcp_connected=True,
            runtime_state_seen=False,
            stale_state=False,
            robot_estopped=False,
            robot_enabled=True,
            tracker_pending=False,
            transition_pending=False,
            target_labels=["FALCON 9"],
            runtime_state_by_label={},
            controlled_lifecycle_active=False,
            runtime_groups=[],
        )

        self.assertFalse(state.allowed)
        self.assertEqual(MANUAL_DUTY_BLOCKED_WAITING_TEXT, state.blocked_reason)

    def test_resolve_manual_duty_access_state_blocks_during_scope_transition(self) -> None:
        state = resolve_manual_duty_access_state(
            tcp_connected=True,
            runtime_state_seen=True,
            stale_state=False,
            robot_estopped=False,
            robot_enabled=True,
            tracker_pending=False,
            transition_pending=True,
            target_labels=["FALCON 9"],
            runtime_state_by_label={},
            controlled_lifecycle_active=False,
            runtime_groups=[],
        )

        self.assertFalse(state.allowed)
        self.assertEqual(MANUAL_DUTY_BLOCKED_TRANSITION_TEXT, state.blocked_reason)

    def test_resolve_manual_duty_access_state_allows_confirmed_target_even_when_busy_and_stale(self) -> None:
        state = resolve_manual_duty_access_state(
            tcp_connected=True,
            runtime_state_seen=True,
            stale_state=True,
            robot_estopped=False,
            robot_enabled=True,
            tracker_pending=True,
            transition_pending=False,
            target_labels=["SPARKMAX/NEO 25"],
            runtime_state_by_label={
                "sparkmax/neo 25": {
                    "label": "SPARKMAX/NEO 25",
                    "lifecycleState": "controlled-active",
                    "instantiated": True,
                    "testable": True,
                }
            },
            controlled_lifecycle_active=True,
            runtime_groups=[],
        )

        self.assertTrue(state.allowed)
        self.assertEqual("", state.blocked_reason)

    def test_resolve_manual_duty_action_state_requests_runtime_refresh_before_open(self) -> None:
        state = resolve_manual_duty_action_state(
            tcp_connected=True,
            runtime_state_seen=True,
            stale_state=False,
            robot_estopped=False,
            robot_enabled=True,
            tracker_pending=False,
            transition_pending=False,
            target_labels=["FALCON 9"],
            runtime_state_by_label={
                "falcon 9": {"label": "FALCON 9", "testable": True}
            },
            controlled_lifecycle_active=False,
            runtime_groups=[],
        )

        self.assertTrue(state.allowed)
        self.assertTrue(state.refresh_before_action)
        self.assertFalse(state.refresh_after_action)
        self.assertFalse(state.refresh_when_blocked)

    def test_resolve_active_group_edit_action_state_requests_refresh_when_scope_locked(self) -> None:
        scope_state = resolve_scope_control_state(
            scope_kind=RUNNABLE_SCOPE_KIND_MANUAL,
            runtime_ui_ready=True,
            tracker_pending=False,
            stale_state=False,
            runtime_state_seen=True,
            controlled_lifecycle_active=True,
            transition_pending=False,
            runnable_scope_state=resolve_runnable_scope_state(
                scope_kind=RUNNABLE_SCOPE_KIND_MANUAL,
                local_selected_profile="test_minimal_25_9",
                local_profile_required=True,
                tcp_connected=True,
                runtime_state_seen=True,
                stale_state=False,
                robot_enabled=True,
                robot_estopped=False,
                robot_mode="teleop",
                manual_group_empty=False,
                scope_active=True,
            ),
            selected_test_name=PROFILE_NONE,
            selected_test_ready=False,
            selected_test_invalid=False,
            selected_test_running=False,
            selected_test_runtime_block_reason="",
        )
        state = resolve_active_group_edit_action_state(
            tcp_connected=True,
            tracker_pending=False,
            controlled_lifecycle_active=True,
            scope_control_state=scope_state,
        )

        self.assertFalse(state.allowed)
        self.assertEqual(ACTIVE_GROUP_EDIT_BLOCKED_LOCKED_TEXT, state.blocked_reason)
        self.assertTrue(state.refresh_when_blocked)

    def test_resolve_active_group_edit_action_state_allows_edit_and_refresh_after_send(self) -> None:
        scope_state = resolve_scope_control_state(
            scope_kind=RUNNABLE_SCOPE_KIND_MANUAL,
            runtime_ui_ready=True,
            tracker_pending=False,
            stale_state=False,
            runtime_state_seen=True,
            controlled_lifecycle_active=False,
            transition_pending=False,
            runnable_scope_state=resolve_runnable_scope_state(
                scope_kind=RUNNABLE_SCOPE_KIND_MANUAL,
                local_selected_profile="test_minimal_25_9",
                local_profile_required=True,
                tcp_connected=True,
                runtime_state_seen=True,
                stale_state=False,
                robot_enabled=True,
                robot_estopped=False,
                robot_mode="teleop",
                manual_group_empty=False,
                scope_active=False,
            ),
            selected_test_name=PROFILE_NONE,
            selected_test_ready=False,
            selected_test_invalid=False,
            selected_test_running=False,
            selected_test_runtime_block_reason="",
        )

    def test_resolve_scope_control_state_keeps_selected_test_activate_allowed_while_scope_is_active(self) -> None:
        runnable_state = resolve_runnable_scope_state(
            scope_kind=RUNNABLE_SCOPE_KIND_SELECTED_TEST,
            local_selected_profile="test_minimal_25_9",
            local_profile_required=True,
            tcp_connected=True,
            runtime_state_seen=True,
            stale_state=False,
            robot_enabled=True,
            robot_estopped=False,
            robot_mode="teleop",
            manual_group_empty=False,
            scope_active=True,
        )

        state = resolve_scope_control_state(
            scope_kind=RUNNABLE_SCOPE_KIND_SELECTED_TEST,
            runtime_ui_ready=True,
            tracker_pending=False,
            stale_state=False,
            runtime_state_seen=True,
            controlled_lifecycle_active=True,
            transition_pending=False,
            runnable_scope_state=runnable_state,
            selected_test_name="smoke_test",
            selected_test_ready=True,
            selected_test_invalid=False,
            selected_test_running=False,
            selected_test_runtime_block_reason="",
        )

        self.assertTrue(state.activate_allowed)
        self.assertTrue(state.deactivate_allowed)
        self.assertTrue(state.run_selected_allowed)

    def test_resolve_scope_control_state_blocks_selected_test_activation_while_test_running(self) -> None:
        runnable_state = resolve_runnable_scope_state(
            scope_kind=RUNNABLE_SCOPE_KIND_SELECTED_TEST,
            local_selected_profile="test_minimal_25_9",
            local_profile_required=True,
            tcp_connected=True,
            runtime_state_seen=True,
            stale_state=False,
            robot_enabled=True,
            robot_estopped=False,
            robot_mode="teleop",
            manual_group_empty=False,
            scope_active=True,
        )

        state = resolve_scope_control_state(
            scope_kind=RUNNABLE_SCOPE_KIND_SELECTED_TEST,
            runtime_ui_ready=True,
            tracker_pending=False,
            stale_state=False,
            runtime_state_seen=True,
            controlled_lifecycle_active=True,
            transition_pending=False,
            runnable_scope_state=runnable_state,
            selected_test_name="smoke_test",
            selected_test_ready=True,
            selected_test_invalid=False,
            selected_test_running=True,
            selected_test_runtime_block_reason="",
        )

        self.assertFalse(state.activate_allowed)
        self.assertFalse(state.deactivate_allowed)
        self.assertFalse(state.run_selected_allowed)
        self.assertEqual(TEST_SCOPE_STATUS_RUNNING_DETAIL, state.blocked_reason)

    def test_resolve_override_action_state_uses_shared_transport_and_busy_messages(self) -> None:
        disconnected = resolve_override_action_state(
            tcp_connected=False,
            tracker_pending=False,
        )
        busy = resolve_override_action_state(
            tcp_connected=True,
            tracker_pending=True,
        )

        self.assertEqual(HOST_ACTION_BLOCKED_NOT_CONNECTED_TEXT, disconnected.blocked_reason)
        self.assertEqual(HOST_ACTION_BLOCKED_BUSY_TEXT, busy.blocked_reason)

    def test_should_clear_runtime_event_notice_when_disabled_conflicts_with_ready_state(self) -> None:
        state = resolve_runnable_scope_state(
            scope_kind=RUNNABLE_SCOPE_KIND_MANUAL,
            local_selected_profile="test_minimal_25_9",
            local_profile_required=True,
            tcp_connected=True,
            runtime_state_seen=True,
            stale_state=False,
            robot_enabled=True,
            robot_estopped=False,
            robot_mode="teleop",
            manual_group_empty=False,
            scope_active=True,
        )

        self.assertTrue(should_clear_runtime_event_notice("Robot disabled.", state))

    def test_should_keep_runtime_event_notice_when_disabled_matches_current_state(self) -> None:
        state = resolve_runnable_scope_state(
            scope_kind=RUNNABLE_SCOPE_KIND_MANUAL,
            local_selected_profile="test_minimal_25_9",
            local_profile_required=True,
            tcp_connected=True,
            runtime_state_seen=True,
            stale_state=False,
            robot_enabled=False,
            robot_estopped=False,
            robot_mode="teleop",
            manual_group_empty=False,
            scope_active=False,
        )

        self.assertEqual(RUNNABLE_SCOPE_DETAIL_DISABLED, state.detail)
        self.assertFalse(should_clear_runtime_event_notice("Robot disabled.", state))

    def test_resolve_active_scope_membership_state_keeps_sorted_eligible_labels(self) -> None:
        state = resolve_active_scope_membership_state(
            runtime_state_seen=True,
            controlled_lifecycle_active=False,
            member_map={},
            runtime_state_by_label={},
            primary_label="",
            eligible_labels=["SPARKMAX/NEO 25", "FALCON 9", "FALCON 9"],
        )

        self.assertEqual(["FALCON 9", "SPARKMAX/NEO 25"], state.eligible_labels)
        self.assertEqual(ACTIVE_GROUP_STATUS_EMPTY_TEXT, state.status_text)
        self.assertTrue(state.editable)

    def test_resolve_active_scope_membership_state_reports_locked_when_active_member_missing(self) -> None:
        state = resolve_active_scope_membership_state(
            runtime_state_seen=True,
            controlled_lifecycle_active=True,
            member_map={"falcon 9": {"label": "FALCON 9", "enabled": True}},
            runtime_state_by_label={"falcon 9": {"presenceConfidence": 0.0}},
            primary_label="FALCON 9",
            eligible_labels=["FALCON 9"],
        )

        self.assertEqual(ACTIVE_GROUP_STATUS_LOCKED_TEXT, state.status_text)
        self.assertFalse(state.editable)
        self.assertFalse(state.all_members_present)

    def test_resolve_active_scope_membership_state_waits_for_transition_resync(self) -> None:
        state = resolve_active_scope_membership_state(
            runtime_state_seen=True,
            controlled_lifecycle_active=True,
            member_map={"falcon 9": {"label": "FALCON 9", "enabled": True}},
            runtime_state_by_label={"falcon 9": {"presenceConfidence": 1.0}},
            primary_label="FALCON 9",
            eligible_labels=["FALCON 9"],
            transition_pending=True,
        )

        self.assertEqual(ACTIVE_GROUP_STATUS_RESYNC_TEXT, state.status_text)
        self.assertFalse(state.editable)
        self.assertFalse(state.all_members_present)
        self.assertTrue(state.transition_pending)

    def test_resolve_manual_duty_scope_state_requires_controlled_active_member_when_scope_active(self) -> None:
        allowed_state = resolve_manual_duty_scope_state(
            label="FALCON 9",
            runtime_state_by_label={
                "falcon 9": {
                    "label": "FALCON 9",
                    "lifecycleState": "controlled-active",
                    "testable": True,
                }
            },
            controlled_lifecycle_active=True,
        )
        blocked_state = resolve_manual_duty_scope_state(
            label="SPARKMAX/NEO 25",
            runtime_state_by_label={
                "sparkmax/neo 25": {
                    "label": "SPARKMAX/NEO 25",
                    "lifecycleState": "instantiated-present",
                    "testable": True,
                }
            },
            controlled_lifecycle_active=True,
        )

        self.assertTrue(allowed_state.allowed)
        self.assertEqual("", allowed_state.blocked_reason)
        self.assertFalse(blocked_state.allowed)
        self.assertEqual(
            MANUAL_DUTY_BLOCKED_CONTROLLED_SCOPE_TEXT,
            blocked_state.blocked_reason,
        )

    def test_resolve_manual_duty_scope_state_allows_testable_device_when_scope_inactive(self) -> None:
        state = resolve_manual_duty_scope_state(
            label="SPARKMAX/NEO 25",
            runtime_state_by_label={
                "sparkmax/neo 25": {
                    "label": "SPARKMAX/NEO 25",
                    "lifecycleState": "instantiated-present",
                    "testable": True,
                }
            },
            controlled_lifecycle_active=False,
        )

        self.assertTrue(state.allowed)
        self.assertEqual("", state.blocked_reason)

    def test_resolve_manual_duty_binding_state_allows_targets_when_runtime_group_binding_is_active(self) -> None:
        state = resolve_manual_duty_binding_state(
            target_labels=["FALCON 9"],
            runtime_groups=[
                {
                    "name": "motors",
                    "bindingActive": True,
                    "members": [
                        {"label": "FALCON 9", "enabled": True},
                        {"label": "SPARKMAX/NEO 25", "enabled": True},
                    ],
                }
            ],
        )

        self.assertTrue(state.allowed)
        self.assertEqual("", state.blocked_reason)

    def test_resolve_tests_active_group_member_rows_keeps_singleton_instantiated_when_scope_is_inactive(self) -> None:
        rows = resolve_tests_active_group_member_rows(
            rows=[{"label": "pdp", "enabled": True, "locked": False, "invalid": False}],
            runtime_state_by_label={"pdp": {"instantiated": True, "testable": True}},
            scope_active=False,
        )

        self.assertEqual(1, len(rows))
        self.assertEqual("yes", rows[0].locked_text)
        self.assertEqual("yes", rows[0].instantiated_text)
        self.assertEqual("no", rows[0].scope_active_text)
        self.assertIn("locked", rows[0].statuses)
        self.assertIn("instantiated", rows[0].statuses)
        self.assertIn("scope inactive", rows[0].statuses)


if __name__ == "__main__":
    unittest.main()
