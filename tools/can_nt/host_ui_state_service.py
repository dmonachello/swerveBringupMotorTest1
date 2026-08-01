from __future__ import annotations

"""
NAME
    host_ui_state_service.py - Shared host-side UI context and runnable-state decisions.

SYNOPSIS
    from tools.can_nt.host_ui_state_service import (
        DiagnosticProfileState,
        RunnableScopeState,
        resolve_diagnostic_profile_state,
        resolve_runnable_scope_state,
    )

DESCRIPTION
    Centralizes host-side state decisions that must be shared across GUI,
    topology, CLI, and other operator surfaces when they express the same
    meaning. This module owns the initial shared contract for diagnostic
    profile context and runnable-scope status.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from tools.common.group_contract import (
    resolve_group_state_from_member_map,
    resolve_group_state_from_rows,
)

PROFILE_NONE = "(none)"
PROFILE_CONTEXT_SOURCE_BLANK = "blank"
PROFILE_CONTEXT_SOURCE_LOCAL = "local"
PROFILE_CONTEXT_SOURCE_ROBOT_SELECTED = "robot_selected"
PROFILE_CONTEXT_SOURCE_ROBOT_ACTIVE_RUNTIME = "robot_active_runtime"

RUNNABLE_SCOPE_KIND_MANUAL = "manual"
RUNNABLE_SCOPE_KIND_SELECTED_TEST = "selected_test"

RUNNABLE_STATE_LEVEL_READY = "ready"
RUNNABLE_STATE_LEVEL_INFO = "info"
RUNNABLE_STATE_LEVEL_WARN = "warn"
RUNNABLE_STATE_LEVEL_ERROR = "error"
RUNNABLE_STATE_LEVEL_NEUTRAL = "neutral"

RUNNABLE_PANEL_READY_HEADLINE = "READY TO RUN"
RUNNABLE_PANEL_INACTIVE_HEADLINE = "NOT RUNNABLE"
RUNNABLE_PANEL_WAITING_HEADLINE = "WAITING FOR STATE"

RUNNABLE_SCOPE_PANEL_READY_DETAIL = "manual/group controls available - ready to run"
RUNNABLE_SCOPE_PANEL_WAITING_DETAIL = "waiting for robot runtime state"
RUNNABLE_SCOPE_PANEL_RESYNC_DETAIL = "waiting for post-transition runtime resync"
RUNNABLE_SCOPE_PANEL_DISCONNECTED_DETAIL = (
    "Robot connection unavailable. Power the robot and reconnect before running."
)
RUNNABLE_SCOPE_DETAIL_MANUAL_NOT_ACTIVATED = "Press Runtime Activate."
RUNNABLE_SCOPE_DETAIL_SELECTED_TEST_NOT_ACTIVATED = "Press Runtime Activate."
RUNNABLE_SCOPE_DETAIL_MANUAL_NOT_TELEOP = "Switch to teleop, then press Runtime Activate."
RUNNABLE_SCOPE_DETAIL_SELECTED_TEST_NOT_TELEOP = "Switch to teleop, then press Runtime Activate."
RUNNABLE_SCOPE_DETAIL_MANUAL_EMPTY = "Active group is empty. Add devices before Runtime Activate."
RUNNABLE_SCOPE_DETAIL_SELECT_PROFILE = (
    "Select a profile before using manual/group controls."
)
RUNNABLE_SCOPE_DETAIL_STALE_STATE = "Robot state stale (code not running?)"
RUNNABLE_SCOPE_DETAIL_ESTOP = "Robot E-Stop. Manual run blocked."
RUNNABLE_SCOPE_DETAIL_DISABLED = "Robot disabled. Enable teleop to run motors."
RUNTIME_EVENT_NOTICE_TOKEN_DISABLED = "robot disabled"
RUNTIME_EVENT_NOTICE_TOKEN_ESTOP = "e-stop"
RUNTIME_EVENT_NOTICE_TOKEN_RUNTIME_INACTIVE = "runtime inactive"
RUNTIME_EVENT_NOTICE_TOKEN_ACTIVATE_GROUP = "press runtime activate"
RUNTIME_EVENT_NOTICE_TOKEN_ACTIVATE_SCOPE = "activate scope first"
RUNTIME_EVENT_NOTICE_TOKEN_GROUP_EMPTY = "active group is empty"
RUNTIME_EVENT_NOTICE_TOKEN_SELECT_PROFILE = "select a profile"
BLANK_REASON_LOCAL_PROFILE_REQUIRED = "Local profile selection required."
OUTPUT_NO_SELECTED_TEST = "no selected test"
SELECTED_TEST_STATUS_LOADED_NOT_ACTIVATED = "selected test scope ready - not activated"
SELECTED_TEST_STATUS_MANUAL_RESTORED = "manual active-group restored - not activated"
SELECTED_TEST_STATUS_SCOPE_SWAP_REQUIRED = "selected test scope swap required"
SELECTED_TEST_STATUS_BLOCKED_ESTOP = "robot disabled (E-Stop)"
SELECTED_TEST_STATUS_BLOCKED_DISABLED = "robot disabled"
SELECTED_TEST_STATUS_BLOCKED_NOT_TELEOP = "robot not in teleop"
SELECTED_TEST_STATUS_BLOCKED_NOT_CONNECTED = "robot not connected"
SELECTED_TEST_STATUS_REQUIRED_UNAVAILABLE = "required devices unavailable"
SELECTED_TEST_STATUS_MISSING_PREFIX = "missing resource/device - "
TEST_SCOPE_PANEL_READY_HEADLINE = "READY TO RUN"
TEST_SCOPE_PANEL_INACTIVE_HEADLINE = "NOT RUNNABLE"
TEST_SCOPE_PANEL_NO_SELECTION_HEADLINE = "NO TEST SELECTED"
TEST_SCOPE_PANEL_NEUTRAL_LEVEL = "neutral"
TEST_SCOPE_STATUS_READY_DETAIL = "selected test devices active - ready to run"
TEST_SCOPE_STATUS_NO_SELECTION_DETAIL = (
    "Select a test from one of the library lists to show the devices that test uses."
)
TEST_SCOPE_STATUS_LOADED_NOT_ACTIVATED_DETAIL = (
    "This test requires the devices shown in Selected Test Devices. Press Runtime Activate, then run the test."
)
TEST_SCOPE_STATUS_MANUAL_RESTORED_DETAIL = (
    "The remembered manual active-group was restored after leaving Tests. Press Runtime Activate before running manual actions."
)
TEST_SCOPE_STATUS_SCOPE_SWAP_REQUIRED_DETAIL = (
    "This test needs a different device scope than the currently active locked scope. "
    "Use Runtime Deactivate, then Runtime Activate to switch scope."
)
TEST_SCOPE_STATUS_MISSING_DEVICE_PREFIX = (
    "This test cannot run because a required profile device is missing: "
)
TEST_SCOPE_STATUS_REQUIRED_UNAVAILABLE_DETAIL = (
    "This test cannot run because one or more required devices are not available."
)
TEST_SCOPE_STATUS_BLOCKED_ESTOP_DETAIL = (
    "This test cannot run because the robot is E-stopped. Clear the E-stop before pressing Runtime Activate or running the test."
)
TEST_SCOPE_STATUS_BLOCKED_DISABLED_DETAIL = (
    "This test cannot run because the robot is disabled. Enable teleop before pressing Runtime Activate or running the test."
)
TEST_SCOPE_STATUS_BLOCKED_NOT_TELEOP_DETAIL = (
    "This test cannot run because the robot is not in teleop. Switch to teleop before pressing Runtime Activate or running the test."
)
TEST_SCOPE_STATUS_BLOCKED_NOT_CONNECTED_DETAIL = (
    "This test source is selected locally, but the robot is disconnected. Reconnect before Runtime Activate or running the test."
)
TEST_SCOPE_STATUS_RUNNING_DETAIL = (
    "This test is currently running. Wait for the run to finish before activating or deactivating scope."
)
TEST_SCOPE_STATUS_RUNNING_DETAIL = (
    "This test is currently running. Wait for the run to finish before activating or deactivating scope."
)
TEST_SCOPE_STATUS_INACTIVE_PREFIX = "selected test inactive - "
TEST_ACTIVE_GROUP_STATUS_LOCKED = "locked"
TEST_ACTIVE_GROUP_STATUS_INVALID = "invalid"
TEST_ACTIVE_GROUP_STATUS_ENABLED = "enabled"
TEST_ACTIVE_GROUP_STATUS_INSTANTIATED = "instantiated"
TEST_ACTIVE_GROUP_STATUS_NOT_INSTANTIATED = "not instantiated"
TEST_ACTIVE_GROUP_STATUS_SCOPE_ACTIVE = "scope active"
TEST_ACTIVE_GROUP_STATUS_SCOPE_INACTIVE = "scope inactive"
TEST_ACTIVE_GROUP_STATUS_NOT_ACTIVATED = TEST_ACTIVE_GROUP_STATUS_SCOPE_INACTIVE
TEST_ACTIVE_GROUP_COLUMN_YES = "yes"
TEST_ACTIVE_GROUP_COLUMN_NO = "no"
ACTIVE_GROUP_STATUS_WAITING_TEXT = "waiting for robot runtime state"
ACTIVE_GROUP_STATUS_RESYNC_TEXT = "waiting for active-scope membership resync"
ACTIVE_GROUP_STATUS_EMPTY_TEXT = "empty - add devices to activate"
ACTIVE_GROUP_STATUS_READY_TEXT = "active and ready to run"
ACTIVE_GROUP_STATUS_LOCKED_TEXT = "Status: locked by active scope session"
ACTIVE_GROUP_STATUS_EDITABLE_TEXT = "editable - activate to run"
ACTIVE_GROUP_STATUS_NONE_TEXT = "no active-group defined"
ACTIVE_GROUP_SUMMARY_EMPTY_TEXT = "(empty)"
SCOPE_MEMBERSHIP_RUNTIME_STATE_CONTROLLED_ACTIVE = "controlled-active"
MANUAL_DUTY_BLOCKED_CONTROLLED_SCOPE_TEXT = (
    "Manual motor control blocked: device is outside the active scope membership."
)
MANUAL_DUTY_BLOCKED_BINDING_ACTIVE_TEXT = (
    "Manual motor control blocked: overlapping group binding is already active."
)
MANUAL_DUTY_BLOCKED_NOT_CONNECTED_TEXT = "Manual motor control blocked: not connected."
MANUAL_DUTY_BLOCKED_STALE_TEXT = "Manual motor control blocked: robot state stale."
MANUAL_DUTY_BLOCKED_ESTOP_TEXT = "Manual motor control blocked: robot estopped."
MANUAL_DUTY_BLOCKED_DISABLED_TEXT = "Manual motor control blocked: robot disabled."
MANUAL_DUTY_BLOCKED_WAITING_TEXT = (
    "Manual motor control blocked: waiting for robot runtime state."
)
MANUAL_DUTY_BLOCKED_TRANSITION_TEXT = (
    "Manual motor control blocked: waiting for active-scope transition to finish."
)
SCOPE_CONTROL_BLOCKED_WAITING_TEXT = (
    "Runtime state not loaded yet. Wait for refresh before editing active-group."
)
HOST_ACTION_BLOCKED_NOT_CONNECTED_TEXT = "Not connected: command blocked."
HOST_ACTION_BLOCKED_BUSY_TEXT = "Busy: wait for current command to finish."
ACTIVE_GROUP_EDIT_BLOCKED_LOCKED_TEXT = (
    "Active group membership is locked while an active scope session is running. Deactivate scope first."
)
RUNTIME_GROUP_KEY_MEMBERS = "members"
RUNTIME_GROUP_KEY_LABEL = "label"
RUNTIME_GROUP_KEY_ENABLED = "enabled"
RUNTIME_GROUP_KEY_BINDING_ACTIVE = "bindingActive"
RUNTIME_FETCH_SOURCE_REST = "rest_runtime_state"
RUNTIME_FETCH_BLOCK_NOT_CONNECTED = "Not connected: runtime state unavailable."
RUNTIME_FETCH_BLOCK_HANDSHAKE = "Runtime state unavailable: waiting for UI session handshake."
RUNTIME_FETCH_BLOCK_BUSY = "Busy: wait for current command to finish."
RUNTIME_FETCH_BLOCK_LOG_POLL = "Busy: wait for current log poll to finish."


@dataclass(frozen=True)
class UiContextState:
    """
    NAME
        UiContextState - Shared host-side UI context snapshot.
    """

    local_selected_profile: str
    robot_selected_profile: str
    robot_active_runtime_profile: str
    selected_test_name: str
    scope_kind: str
    has_local_profile_selection: bool
    has_robot_runtime_state: bool
    transport_connected: bool
    handshake_ready: bool


@dataclass(frozen=True)
class DiagnosticProfileState:
    """
    NAME
        DiagnosticProfileState - Shared host-side diagnostic profile context.
    """

    local_selected_profile: str
    robot_selected_profile: str
    robot_active_runtime_profile: str
    effective_profile: str
    show_blank_profile_state: bool
    blank_reason: str
    local_profile_required: bool
    robot_profile_available: bool
    profile_context_source: str


@dataclass(frozen=True)
class RunnableScopeState:
    """
    NAME
        RunnableScopeState - Shared host-side runnable-scope decision result.
    """

    scope_kind: str
    headline: str
    detail: str
    level: str
    blocked_reason: str
    activation_notice: str
    activation_allowed: bool
    deactivation_allowed: bool
    scope_active: bool
    runtime_state_seen: bool
    transition_pending: bool


@dataclass(frozen=True)
class TopologySceneState:
    """
    NAME
        TopologySceneState - Shared host-side topology scene decision state.
    """

    profile_name: str
    is_blank: bool
    blank_reason: str
    active_group_meaningful: bool
    should_reload: bool


@dataclass(frozen=True)
class SelectedTestScopeState:
    """
    NAME
        SelectedTestScopeState - Shared host-side selected-test readiness state.
    """

    selected_name: str
    inactive_reason: str
    ready: bool
    headline: str
    detail_reason: str
    level: str


@dataclass(frozen=True)
class ActiveGroupSummaryState:
    """
    NAME
        ActiveGroupSummaryState - Shared host-side active-group summary state.
    """

    status_text: str
    summary_text: str
    editable: bool
    all_members_present: bool
    primary_label: str
    member_count: int
    transition_pending: bool


@dataclass(frozen=True)
class ActiveScopeMembershipState:
    """
    NAME
        ActiveScopeMembershipState - Shared host-side active-scope membership state.
    """

    eligible_labels: List[str]
    status_text: str
    summary_text: str
    editable: bool
    all_members_present: bool
    primary_label: str
    member_count: int
    has_scope_definition: bool
    transition_pending: bool


@dataclass(frozen=True)
class SelectedTestPanelState:
    """
    NAME
        SelectedTestPanelState - Shared host-side selected-test panel presentation state.
    """

    headline: str
    detail: str
    level: str


@dataclass(frozen=True)
class ActiveGroupMemberRowState:
    """
    NAME
        ActiveGroupMemberRowState - Shared host-side selected-test device row state.
    """

    label: str
    statuses: List[str]
    reason: str
    enabled: bool
    locked: bool
    invalid: bool
    instantiated: bool
    scope_active: bool
    enabled_text: str
    locked_text: str
    instantiated_text: str
    scope_active_text: str
    note_text: str
    line: str


@dataclass(frozen=True)
class RuntimeStateFetchState:
    """
    NAME
        RuntimeStateFetchState - Shared host-side runtime-state fetch gate.
    """

    allowed: bool
    blocked_reason: str
    fetch_source: str


@dataclass(frozen=True)
class ScopeControlState:
    """
    NAME
        ScopeControlState - Shared host-side activation and edit ownership gate.
    """

    scope_kind: str
    activate_allowed: bool
    deactivate_allowed: bool
    run_selected_allowed: bool
    active_group_editable: bool
    blocked_reason: str
    transition_pending: bool


@dataclass(frozen=True)
class ManualDutyScopeState:
    """
    NAME
        ManualDutyScopeState - Shared host-side manual-duty scope eligibility result.
    """

    allowed: bool
    blocked_reason: str


@dataclass(frozen=True)
class ManualDutyAccessState:
    """
    NAME
        ManualDutyAccessState - Shared host-side manual-duty access result.
    """

    allowed: bool
    blocked_reason: str


@dataclass(frozen=True)
class HostActionAccessState:
    """
    NAME
        HostActionAccessState - Shared host-side action-access contract for surface entry points.
    """

    allowed: bool
    blocked_reason: str
    refresh_before_action: bool
    refresh_after_action: bool
    refresh_when_blocked: bool


def resolve_manual_duty_binding_state(
    *,
    target_labels: List[object],
    runtime_groups: List[Dict[str, Any]],
) -> ManualDutyScopeState:
    """
    NAME
        resolve_manual_duty_binding_state - Return whether manual duty should be blocked by group binding ownership.
    """
    normalized_targets = {
        str(label or "").strip().lower()
        for label in list(target_labels or [])
        if str(label or "").strip()
    }
    if not normalized_targets:
        return ManualDutyScopeState(
            allowed=False,
            blocked_reason=MANUAL_DUTY_BLOCKED_BINDING_ACTIVE_TEXT,
        )
    return ManualDutyScopeState(allowed=True, blocked_reason="")


def _normalize_profile_name(value: object) -> str:
    """
    NAME
        _normalize_profile_name - Return one trimmed profile name or PROFILE_NONE.
    """
    clean = str(value or "").strip()
    return clean if clean else PROFILE_NONE


def _normalize_scope_kind(value: object) -> str:
    """
    NAME
        _normalize_scope_kind - Return one normalized runnable-scope kind.
    """
    clean = str(value or RUNNABLE_SCOPE_KIND_MANUAL).strip().lower()
    if clean == RUNNABLE_SCOPE_KIND_SELECTED_TEST:
        return RUNNABLE_SCOPE_KIND_SELECTED_TEST
    return RUNNABLE_SCOPE_KIND_MANUAL


def resolve_ui_context_state(
    *,
    local_selected_profile: object,
    robot_selected_profile: object,
    robot_active_runtime_profile: object,
    selected_test_name: object,
    scope_kind: object,
    transport_connected: bool,
    handshake_ready: bool,
    has_robot_runtime_state: bool,
) -> UiContextState:
    """
    NAME
        resolve_ui_context_state - Build one shared UI context snapshot from host and robot state.
    """
    local_selected = _normalize_profile_name(local_selected_profile)
    robot_selected = _normalize_profile_name(robot_selected_profile)
    robot_active_runtime = _normalize_profile_name(robot_active_runtime_profile)
    selected_test = str(selected_test_name or "").strip()
    normalized_scope = _normalize_scope_kind(scope_kind)
    return UiContextState(
        local_selected_profile=local_selected,
        robot_selected_profile=robot_selected,
        robot_active_runtime_profile=robot_active_runtime,
        selected_test_name=selected_test,
        scope_kind=normalized_scope,
        has_local_profile_selection=local_selected != PROFILE_NONE,
        has_robot_runtime_state=bool(has_robot_runtime_state),
        transport_connected=bool(transport_connected),
        handshake_ready=bool(handshake_ready),
    )


def resolve_diagnostic_profile_state(
    local_selected_profile: object,
    robot_selected_profile: object,
    robot_active_runtime_profile: object,
    local_profile_required: bool = True,
) -> DiagnosticProfileState:
    """
    NAME
        resolve_diagnostic_profile_state - Resolve the shared profile-backed diagnostic context.
    """
    local_selected = _normalize_profile_name(local_selected_profile)
    robot_selected = _normalize_profile_name(robot_selected_profile)
    robot_active_runtime = _normalize_profile_name(robot_active_runtime_profile)
    if local_profile_required and local_selected == PROFILE_NONE:
        return DiagnosticProfileState(
            local_selected_profile=local_selected,
            robot_selected_profile=robot_selected,
            robot_active_runtime_profile=robot_active_runtime,
            effective_profile=PROFILE_NONE,
            show_blank_profile_state=True,
            blank_reason=BLANK_REASON_LOCAL_PROFILE_REQUIRED,
            local_profile_required=True,
            robot_profile_available=robot_selected != PROFILE_NONE or robot_active_runtime != PROFILE_NONE,
            profile_context_source=PROFILE_CONTEXT_SOURCE_BLANK,
        )
    if robot_active_runtime != PROFILE_NONE:
        effective_profile = robot_active_runtime
        source = PROFILE_CONTEXT_SOURCE_ROBOT_ACTIVE_RUNTIME
    elif robot_selected != PROFILE_NONE:
        effective_profile = robot_selected
        source = PROFILE_CONTEXT_SOURCE_ROBOT_SELECTED
    else:
        effective_profile = local_selected
        source = PROFILE_CONTEXT_SOURCE_LOCAL
    return DiagnosticProfileState(
        local_selected_profile=local_selected,
        robot_selected_profile=robot_selected,
        robot_active_runtime_profile=robot_active_runtime,
        effective_profile=effective_profile,
        show_blank_profile_state=effective_profile == PROFILE_NONE,
        blank_reason=BLANK_REASON_LOCAL_PROFILE_REQUIRED if effective_profile == PROFILE_NONE else "",
        local_profile_required=local_profile_required,
        robot_profile_available=robot_selected != PROFILE_NONE or robot_active_runtime != PROFILE_NONE,
        profile_context_source=source if effective_profile != PROFILE_NONE else PROFILE_CONTEXT_SOURCE_BLANK,
    )


def resolve_topology_scene_state(
    *,
    effective_profile: object,
    show_blank_profile_state: bool,
    blank_reason: object,
    current_profile_name: object,
) -> TopologySceneState:
    """
    NAME
        resolve_topology_scene_state - Resolve one shared topology scene decision.
    """
    profile_name = _normalize_profile_name(effective_profile)
    current_profile = _normalize_profile_name(current_profile_name)
    scene_blank = bool(show_blank_profile_state) or profile_name == PROFILE_NONE
    if scene_blank:
        profile_name = PROFILE_NONE
    clean_blank_reason = str(blank_reason or "").strip()
    return TopologySceneState(
        profile_name=profile_name,
        is_blank=scene_blank,
        blank_reason=clean_blank_reason if scene_blank else "",
        active_group_meaningful=not scene_blank,
        should_reload=profile_name != current_profile,
    )


def resolve_runnable_scope_state(
    scope_kind: object,
    local_selected_profile: object,
    local_profile_required: bool,
    tcp_connected: bool,
    runtime_state_seen: bool,
    stale_state: bool,
    robot_enabled: bool,
    robot_estopped: bool,
    robot_mode: object,
    manual_group_empty: bool,
    scope_active: bool,
    transition_pending: bool = False,
) -> RunnableScopeState:
    """
    NAME
        resolve_runnable_scope_state - Resolve shared runnable-state messaging and actionability.
    """
    normalized_scope = str(scope_kind or RUNNABLE_SCOPE_KIND_MANUAL).strip().lower()
    local_selected = _normalize_profile_name(local_selected_profile)
    activation_notice = resolve_scope_activation_notice(
        scope_kind=normalized_scope,
        local_selected_profile=local_selected,
        local_profile_required=local_profile_required,
        robot_mode=robot_mode,
    )
    if not tcp_connected:
        return RunnableScopeState(
            scope_kind=normalized_scope,
            headline=RUNNABLE_PANEL_INACTIVE_HEADLINE,
            detail=RUNNABLE_SCOPE_PANEL_DISCONNECTED_DETAIL,
            level=RUNNABLE_STATE_LEVEL_ERROR,
            blocked_reason=RUNNABLE_SCOPE_PANEL_DISCONNECTED_DETAIL,
            activation_notice=activation_notice,
            activation_allowed=False,
            deactivation_allowed=False,
            scope_active=False,
            runtime_state_seen=runtime_state_seen,
            transition_pending=False,
        )
    if not runtime_state_seen:
        return RunnableScopeState(
            scope_kind=normalized_scope,
            headline=RUNNABLE_PANEL_WAITING_HEADLINE,
            detail=RUNNABLE_SCOPE_PANEL_WAITING_DETAIL,
            level=RUNNABLE_STATE_LEVEL_NEUTRAL,
            blocked_reason=RUNNABLE_SCOPE_PANEL_WAITING_DETAIL,
            activation_notice=activation_notice,
            activation_allowed=False,
            deactivation_allowed=False,
            scope_active=False,
            runtime_state_seen=False,
            transition_pending=False,
        )
    if transition_pending:
        return RunnableScopeState(
            scope_kind=normalized_scope,
            headline=RUNNABLE_PANEL_WAITING_HEADLINE,
            detail=RUNNABLE_SCOPE_PANEL_RESYNC_DETAIL,
            level=RUNNABLE_STATE_LEVEL_NEUTRAL,
            blocked_reason=RUNNABLE_SCOPE_PANEL_RESYNC_DETAIL,
            activation_notice=activation_notice,
            activation_allowed=False,
            deactivation_allowed=False,
            scope_active=scope_active,
            runtime_state_seen=True,
            transition_pending=True,
        )
    if stale_state:
        return RunnableScopeState(
            scope_kind=normalized_scope,
            headline=RUNNABLE_PANEL_INACTIVE_HEADLINE,
            detail=RUNNABLE_SCOPE_DETAIL_STALE_STATE,
            level=RUNNABLE_STATE_LEVEL_WARN,
            blocked_reason=RUNNABLE_SCOPE_DETAIL_STALE_STATE,
            activation_notice=activation_notice,
            activation_allowed=False,
            deactivation_allowed=False,
            scope_active=False,
            runtime_state_seen=True,
            transition_pending=False,
        )
    if robot_estopped:
        return RunnableScopeState(
            scope_kind=normalized_scope,
            headline=RUNNABLE_PANEL_INACTIVE_HEADLINE,
            detail=RUNNABLE_SCOPE_DETAIL_ESTOP,
            level=RUNNABLE_STATE_LEVEL_ERROR,
            blocked_reason=RUNNABLE_SCOPE_DETAIL_ESTOP,
            activation_notice=activation_notice,
            activation_allowed=False,
            deactivation_allowed=False,
            scope_active=scope_active,
            runtime_state_seen=True,
            transition_pending=False,
        )
    if not robot_enabled:
        return RunnableScopeState(
            scope_kind=normalized_scope,
            headline=RUNNABLE_PANEL_INACTIVE_HEADLINE,
            detail=RUNNABLE_SCOPE_DETAIL_DISABLED,
            level=RUNNABLE_STATE_LEVEL_INFO,
            blocked_reason=RUNNABLE_SCOPE_DETAIL_DISABLED,
            activation_notice=activation_notice,
            activation_allowed=False,
            deactivation_allowed=scope_active,
            scope_active=scope_active,
            runtime_state_seen=True,
            transition_pending=False,
        )
    mode = str(robot_mode or "").strip().lower()
    if mode and mode != "teleop":
        detail = (
            RUNNABLE_SCOPE_DETAIL_SELECTED_TEST_NOT_TELEOP
            if normalized_scope == RUNNABLE_SCOPE_KIND_SELECTED_TEST
            else RUNNABLE_SCOPE_DETAIL_MANUAL_NOT_TELEOP
        )
        return RunnableScopeState(
            scope_kind=normalized_scope,
            headline=RUNNABLE_PANEL_INACTIVE_HEADLINE,
            detail=detail,
            level=RUNNABLE_STATE_LEVEL_WARN,
            blocked_reason=detail,
            activation_notice=activation_notice,
            activation_allowed=False,
            deactivation_allowed=scope_active,
            scope_active=scope_active,
            runtime_state_seen=True,
            transition_pending=False,
        )
    if normalized_scope == RUNNABLE_SCOPE_KIND_MANUAL and local_profile_required and local_selected == PROFILE_NONE:
        return RunnableScopeState(
            scope_kind=normalized_scope,
            headline=RUNNABLE_PANEL_INACTIVE_HEADLINE,
            detail=RUNNABLE_SCOPE_DETAIL_SELECT_PROFILE,
            level=RUNNABLE_STATE_LEVEL_WARN,
            blocked_reason=RUNNABLE_SCOPE_DETAIL_SELECT_PROFILE,
            activation_notice=activation_notice,
            activation_allowed=False,
            deactivation_allowed=False,
            scope_active=False,
            runtime_state_seen=True,
            transition_pending=False,
        )
    if normalized_scope == RUNNABLE_SCOPE_KIND_MANUAL and manual_group_empty:
        return RunnableScopeState(
            scope_kind=normalized_scope,
            headline=RUNNABLE_PANEL_INACTIVE_HEADLINE,
            detail=RUNNABLE_SCOPE_DETAIL_MANUAL_EMPTY,
            level=RUNNABLE_STATE_LEVEL_WARN,
            blocked_reason=RUNNABLE_SCOPE_DETAIL_MANUAL_EMPTY,
            activation_notice=activation_notice,
            activation_allowed=False,
            deactivation_allowed=scope_active,
            scope_active=scope_active,
            runtime_state_seen=True,
            transition_pending=False,
        )
    if not scope_active:
        return RunnableScopeState(
            scope_kind=normalized_scope,
            headline=RUNNABLE_PANEL_INACTIVE_HEADLINE,
            detail=activation_notice,
            level=RUNNABLE_STATE_LEVEL_WARN,
            blocked_reason=activation_notice,
            activation_notice=activation_notice,
            activation_allowed=True,
            deactivation_allowed=False,
            scope_active=False,
            runtime_state_seen=True,
            transition_pending=False,
        )
    return RunnableScopeState(
        scope_kind=normalized_scope,
        headline=RUNNABLE_PANEL_READY_HEADLINE,
        detail=RUNNABLE_SCOPE_PANEL_READY_DETAIL,
        level=RUNNABLE_STATE_LEVEL_READY,
        blocked_reason="",
        activation_notice=activation_notice,
        activation_allowed=False,
        deactivation_allowed=True,
        scope_active=True,
        runtime_state_seen=True,
        transition_pending=False,
    )


def resolve_scope_activation_notice(
    scope_kind: object,
    local_selected_profile: object,
    local_profile_required: bool,
    robot_mode: object,
) -> str:
    """
    NAME
        resolve_scope_activation_notice - Return the next-step activation message for one scope.
    """
    normalized_scope = str(scope_kind or RUNNABLE_SCOPE_KIND_MANUAL).strip().lower()
    local_selected = _normalize_profile_name(local_selected_profile)
    mode = str(robot_mode or "").strip().lower()
    if normalized_scope == RUNNABLE_SCOPE_KIND_MANUAL and local_profile_required and local_selected == PROFILE_NONE:
        return RUNNABLE_SCOPE_DETAIL_SELECT_PROFILE
    if mode and mode != "teleop":
        return (
            RUNNABLE_SCOPE_DETAIL_SELECTED_TEST_NOT_TELEOP
            if normalized_scope == RUNNABLE_SCOPE_KIND_SELECTED_TEST
            else RUNNABLE_SCOPE_DETAIL_MANUAL_NOT_TELEOP
        )
    return (
        RUNNABLE_SCOPE_DETAIL_SELECTED_TEST_NOT_ACTIVATED
        if normalized_scope == RUNNABLE_SCOPE_KIND_SELECTED_TEST
        else RUNNABLE_SCOPE_DETAIL_MANUAL_NOT_ACTIVATED
    )


def should_clear_runtime_event_notice(
    event_text: object,
    state: RunnableScopeState,
) -> bool:
    """
    NAME
        should_clear_runtime_event_notice - Return whether one old event notice conflicts with current shared scope state.
    """
    detail = str(state.detail or "").strip().lower()
    message = str(event_text or "").strip().lower()
    if not message:
        return False
    if (
        RUNTIME_EVENT_NOTICE_TOKEN_DISABLED in message
        and detail != RUNNABLE_SCOPE_DETAIL_DISABLED.lower()
    ):
        return True
    if (
        RUNTIME_EVENT_NOTICE_TOKEN_ESTOP in message
        and detail != RUNNABLE_SCOPE_DETAIL_ESTOP.lower()
    ):
        return True
    if (
        RUNTIME_EVENT_NOTICE_TOKEN_ACTIVATE_GROUP in message
        and detail != RUNNABLE_SCOPE_DETAIL_MANUAL_NOT_ACTIVATED.lower()
    ):
        return True
    if (
        RUNTIME_EVENT_NOTICE_TOKEN_ACTIVATE_SCOPE in message
        and detail != RUNNABLE_SCOPE_DETAIL_SELECTED_TEST_NOT_ACTIVATED.lower()
    ):
        return True
    if (
        RUNTIME_EVENT_NOTICE_TOKEN_GROUP_EMPTY in message
        and detail != RUNNABLE_SCOPE_DETAIL_MANUAL_EMPTY.lower()
    ):
        return True
    if (
        RUNTIME_EVENT_NOTICE_TOKEN_SELECT_PROFILE in message
        and detail != RUNNABLE_SCOPE_DETAIL_SELECT_PROFILE.lower()
    ):
        return True
    if (
        RUNTIME_EVENT_NOTICE_TOKEN_RUNTIME_INACTIVE in message
        and state.scope_active
    ):
        return True
    return False


def resolve_selected_test_runtime_block_reason(
    tcp_connected: bool,
    robot_estopped: bool,
    robot_enabled: bool,
    robot_mode: object,
) -> str:
    """
    NAME
        resolve_selected_test_runtime_block_reason - Return robot-state blocker text for selected-test execution.
    """
    if not tcp_connected:
        return SELECTED_TEST_STATUS_BLOCKED_NOT_CONNECTED
    if robot_estopped:
        return SELECTED_TEST_STATUS_BLOCKED_ESTOP
    if not robot_enabled:
        return SELECTED_TEST_STATUS_BLOCKED_DISABLED
    mode = str(robot_mode or "").strip().lower()
    if mode and mode != "teleop":
        return SELECTED_TEST_STATUS_BLOCKED_NOT_TELEOP
    return ""


def resolve_selected_test_scope_state(
    selected_name: object,
    active_group_rows: List[Dict[str, Any]],
    runtime_block_reason: str,
    scope_active: bool,
    loaded_to_robot: Optional[bool],
    selected_row: Optional[Dict[str, Any]],
) -> SelectedTestScopeState:
    """
    NAME
        resolve_selected_test_scope_state - Return shared selected-test readiness state.
    """
    clean_name = str(selected_name or "").strip()
    if not clean_name or clean_name == PROFILE_NONE:
        return SelectedTestScopeState(
            selected_name=PROFILE_NONE,
            inactive_reason=OUTPUT_NO_SELECTED_TEST,
            ready=False,
            headline=TEST_SCOPE_PANEL_NO_SELECTION_HEADLINE,
            detail_reason=OUTPUT_NO_SELECTED_TEST,
            level=TEST_SCOPE_PANEL_NEUTRAL_LEVEL,
        )
    invalid_labels = [
        str(row.get("label", "")).strip()
        for row in active_group_rows
        if isinstance(row, dict) and bool(row.get("invalid"))
    ]
    if invalid_labels:
        reason = SELECTED_TEST_STATUS_MISSING_PREFIX + invalid_labels[0]
        return SelectedTestScopeState(
            selected_name=clean_name,
            inactive_reason=reason,
            ready=False,
            headline=TEST_SCOPE_PANEL_INACTIVE_HEADLINE,
            detail_reason=reason,
            level=RUNNABLE_STATE_LEVEL_WARN,
        )
    if runtime_block_reason:
        return SelectedTestScopeState(
            selected_name=clean_name,
            inactive_reason=runtime_block_reason,
            ready=False,
            headline=TEST_SCOPE_PANEL_INACTIVE_HEADLINE,
            detail_reason=runtime_block_reason,
            level=RUNNABLE_STATE_LEVEL_WARN,
        )
    if not scope_active:
        if not isinstance(selected_row, dict):
            reason = SELECTED_TEST_STATUS_REQUIRED_UNAVAILABLE
        else:
            reason = SELECTED_TEST_STATUS_LOADED_NOT_ACTIVATED
        return SelectedTestScopeState(
            selected_name=clean_name,
            inactive_reason=reason,
            ready=False,
            headline=TEST_SCOPE_PANEL_INACTIVE_HEADLINE,
            detail_reason=reason,
            level=RUNNABLE_STATE_LEVEL_WARN,
        )
    if loaded_to_robot is False:
        return SelectedTestScopeState(
            selected_name=clean_name,
            inactive_reason=SELECTED_TEST_STATUS_SCOPE_SWAP_REQUIRED,
            ready=False,
            headline=TEST_SCOPE_PANEL_INACTIVE_HEADLINE,
            detail_reason=SELECTED_TEST_STATUS_SCOPE_SWAP_REQUIRED,
            level=RUNNABLE_STATE_LEVEL_WARN,
        )
    if not isinstance(selected_row, dict):
        return SelectedTestScopeState(
            selected_name=clean_name,
            inactive_reason=SELECTED_TEST_STATUS_REQUIRED_UNAVAILABLE,
            ready=False,
            headline=TEST_SCOPE_PANEL_INACTIVE_HEADLINE,
            detail_reason=SELECTED_TEST_STATUS_REQUIRED_UNAVAILABLE,
            level=RUNNABLE_STATE_LEVEL_WARN,
        )
    blocked_reason = str(selected_row.get("blockedReason", "") or "").strip()
    if blocked_reason:
        return SelectedTestScopeState(
            selected_name=clean_name,
            inactive_reason=blocked_reason,
            ready=False,
            headline=TEST_SCOPE_PANEL_INACTIVE_HEADLINE,
            detail_reason=blocked_reason,
            level=RUNNABLE_STATE_LEVEL_WARN,
        )
    runnable_now = selected_row.get("runnableNow")
    if isinstance(runnable_now, bool) and not runnable_now:
        return SelectedTestScopeState(
            selected_name=clean_name,
            inactive_reason=SELECTED_TEST_STATUS_REQUIRED_UNAVAILABLE,
            ready=False,
            headline=TEST_SCOPE_PANEL_INACTIVE_HEADLINE,
            detail_reason=SELECTED_TEST_STATUS_REQUIRED_UNAVAILABLE,
            level=RUNNABLE_STATE_LEVEL_WARN,
        )
    return SelectedTestScopeState(
        selected_name=clean_name,
        inactive_reason="",
        ready=True,
        headline=TEST_SCOPE_PANEL_READY_HEADLINE,
        detail_reason="",
        level=RUNNABLE_STATE_LEVEL_READY,
    )


def resolve_selected_test_panel_state(state: SelectedTestScopeState) -> SelectedTestPanelState:
    """
    NAME
        resolve_selected_test_panel_state - Return shared operator-facing selected-test panel presentation.
    """
    reason = str(state.inactive_reason or "").strip()
    if not reason:
        return SelectedTestPanelState(
            headline=TEST_SCOPE_PANEL_READY_HEADLINE,
            detail=TEST_SCOPE_STATUS_READY_DETAIL,
            level=RUNNABLE_STATE_LEVEL_READY,
        )
    if reason == OUTPUT_NO_SELECTED_TEST:
        return SelectedTestPanelState(
            headline=TEST_SCOPE_PANEL_NO_SELECTION_HEADLINE,
            detail=TEST_SCOPE_STATUS_NO_SELECTION_DETAIL,
            level=TEST_SCOPE_PANEL_NEUTRAL_LEVEL,
        )
    if reason == SELECTED_TEST_STATUS_LOADED_NOT_ACTIVATED:
        detail = TEST_SCOPE_STATUS_LOADED_NOT_ACTIVATED_DETAIL
    elif reason == SELECTED_TEST_STATUS_MANUAL_RESTORED:
        detail = TEST_SCOPE_STATUS_MANUAL_RESTORED_DETAIL
    elif reason == SELECTED_TEST_STATUS_SCOPE_SWAP_REQUIRED:
        detail = TEST_SCOPE_STATUS_SCOPE_SWAP_REQUIRED_DETAIL
    elif reason == SELECTED_TEST_STATUS_BLOCKED_ESTOP:
        detail = TEST_SCOPE_STATUS_BLOCKED_ESTOP_DETAIL
    elif reason == SELECTED_TEST_STATUS_BLOCKED_DISABLED:
        detail = TEST_SCOPE_STATUS_BLOCKED_DISABLED_DETAIL
    elif reason == SELECTED_TEST_STATUS_BLOCKED_NOT_TELEOP:
        detail = TEST_SCOPE_STATUS_BLOCKED_NOT_TELEOP_DETAIL
    elif reason == SELECTED_TEST_STATUS_BLOCKED_NOT_CONNECTED:
        detail = TEST_SCOPE_STATUS_BLOCKED_NOT_CONNECTED_DETAIL
    elif reason.startswith(SELECTED_TEST_STATUS_MISSING_PREFIX):
        missing = reason.split(" - ", 1)[1].strip()
        detail = TEST_SCOPE_STATUS_MISSING_DEVICE_PREFIX + missing
    elif reason == SELECTED_TEST_STATUS_REQUIRED_UNAVAILABLE:
        detail = TEST_SCOPE_STATUS_REQUIRED_UNAVAILABLE_DETAIL
    else:
        detail = TEST_SCOPE_STATUS_INACTIVE_PREFIX + reason
    return SelectedTestPanelState(
        headline=state.headline,
        detail=detail,
        level=state.level,
    )


def resolve_tests_active_group_member_rows(
    rows: List[Dict[str, Any]],
    runtime_state_by_label: Dict[str, Dict[str, Any]],
    scope_active: bool,
) -> List[ActiveGroupMemberRowState]:
    """
    NAME
        resolve_tests_active_group_member_rows - Return shared Selected Test Devices row presentation state.
    """
    group_state = resolve_group_state_from_rows(
        name="selected-test-devices",
        rows=rows,
        runtime_state_by_label=runtime_state_by_label,
        primary_label="",
        scope_active=scope_active,
    )
    result: List[ActiveGroupMemberRowState] = []
    row_reason_by_label = {
        str(row.get("label", "")).strip(): str(row.get("reason", "")).strip()
        for row in rows
        if isinstance(row, dict) and str(row.get("label", "")).strip()
    }
    for member in group_state.members:
        statuses = [TEST_ACTIVE_GROUP_STATUS_ENABLED] if member.enabled else []
        if member.locked:
            statuses.append(TEST_ACTIVE_GROUP_STATUS_LOCKED)
        if member.invalid:
            statuses.append(TEST_ACTIVE_GROUP_STATUS_INVALID)
        statuses.append(
            TEST_ACTIVE_GROUP_STATUS_INSTANTIATED
            if member.instantiated
            else TEST_ACTIVE_GROUP_STATUS_NOT_INSTANTIATED
        )
        statuses.append(
            TEST_ACTIVE_GROUP_STATUS_SCOPE_ACTIVE
            if member.scope_active
            else TEST_ACTIVE_GROUP_STATUS_SCOPE_INACTIVE
        )
        reason = row_reason_by_label.get(member.label, "")
        note_text = reason or (TEST_ACTIVE_GROUP_STATUS_INVALID if member.invalid else "")
        enabled_text = TEST_ACTIVE_GROUP_COLUMN_YES if member.enabled else TEST_ACTIVE_GROUP_COLUMN_NO
        locked_text = TEST_ACTIVE_GROUP_COLUMN_YES if member.locked else TEST_ACTIVE_GROUP_COLUMN_NO
        instantiated_text = TEST_ACTIVE_GROUP_COLUMN_YES if member.instantiated else TEST_ACTIVE_GROUP_COLUMN_NO
        scope_active_text = TEST_ACTIVE_GROUP_COLUMN_YES if member.scope_active else TEST_ACTIVE_GROUP_COLUMN_NO
        line = (
            f"{member.label} | enabled={enabled_text} | locked={locked_text} | "
            f"instantiated={instantiated_text} | scopeActive={scope_active_text}"
        )
        if note_text:
            line += f" | {note_text}"
        result.append(
            ActiveGroupMemberRowState(
                label=member.label,
                statuses=statuses,
                reason=reason,
                enabled=member.enabled,
                locked=member.locked,
                invalid=member.invalid,
                instantiated=member.instantiated,
                scope_active=member.scope_active,
                enabled_text=enabled_text,
                locked_text=locked_text,
                instantiated_text=instantiated_text,
                scope_active_text=scope_active_text,
                note_text=note_text,
                line=line,
            )
        )
    return result


def resolve_active_group_summary_state(
    runtime_state_seen: bool,
    controlled_lifecycle_active: bool,
    member_map: Dict[str, Dict[str, Any]],
    runtime_state_by_label: Dict[str, Dict[str, Any]],
    primary_label: object,
    transition_pending: bool = False,
) -> ActiveGroupSummaryState:
    """
    NAME
        resolve_active_group_summary_state - Return shared active-group status and summary state.
    """
    group_state = resolve_group_state_from_member_map(
        name="active-group",
        member_map=member_map,
        runtime_state_by_label=runtime_state_by_label,
        primary_label=primary_label,
        scope_active=controlled_lifecycle_active,
    )
    clean_primary = group_state.primary_label
    member_count = group_state.member_count
    if not runtime_state_seen:
        return ActiveGroupSummaryState(
            status_text=ACTIVE_GROUP_STATUS_WAITING_TEXT,
            summary_text=f"Primary: {clean_primary}" if clean_primary else ACTIVE_GROUP_SUMMARY_EMPTY_TEXT,
            editable=False,
            all_members_present=False,
            primary_label=clean_primary,
            member_count=member_count,
            transition_pending=False,
        )
    if transition_pending:
        return ActiveGroupSummaryState(
            status_text=ACTIVE_GROUP_STATUS_RESYNC_TEXT,
            summary_text=f"Primary: {clean_primary}" if clean_primary else ACTIVE_GROUP_SUMMARY_EMPTY_TEXT,
            editable=False,
            all_members_present=False,
            primary_label=clean_primary,
            member_count=member_count,
            transition_pending=True,
        )
    if not group_state.has_members:
        return ActiveGroupSummaryState(
            status_text=ACTIVE_GROUP_STATUS_EMPTY_TEXT,
            summary_text=ACTIVE_GROUP_SUMMARY_EMPTY_TEXT,
            editable=not controlled_lifecycle_active,
            all_members_present=False,
            primary_label=clean_primary,
            member_count=0,
            transition_pending=False,
        )
    all_members_present = group_state.all_enabled_members_present
    if controlled_lifecycle_active:
        status_text = ACTIVE_GROUP_STATUS_READY_TEXT if all_members_present else ACTIVE_GROUP_STATUS_LOCKED_TEXT
        editable = False
    else:
        status_text = ACTIVE_GROUP_STATUS_EDITABLE_TEXT
        editable = True
    return ActiveGroupSummaryState(
        status_text=status_text,
        summary_text=f"Primary: {clean_primary}" if clean_primary else ACTIVE_GROUP_SUMMARY_EMPTY_TEXT,
        editable=editable,
        all_members_present=all_members_present,
        primary_label=clean_primary,
        member_count=member_count,
        transition_pending=False,
    )


def resolve_active_scope_membership_state(
    *,
    runtime_state_seen: bool,
    controlled_lifecycle_active: bool,
    member_map: Dict[str, Dict[str, Any]],
    runtime_state_by_label: Dict[str, Dict[str, Any]],
    primary_label: object,
    eligible_labels: List[str],
    transition_pending: bool = False,
) -> ActiveScopeMembershipState:
    """
    NAME
        resolve_active_scope_membership_state - Return shared active-scope membership state for editable host surfaces.
    """
    summary = resolve_active_group_summary_state(
        runtime_state_seen=runtime_state_seen,
        controlled_lifecycle_active=controlled_lifecycle_active,
        member_map=member_map,
        runtime_state_by_label=runtime_state_by_label,
        primary_label=primary_label,
        transition_pending=transition_pending,
    )
    normalized_labels = sorted(
        {
            str(label or "").strip()
            for label in eligible_labels
            if str(label or "").strip()
        },
        key=lambda item: item.lower(),
    )
    return ActiveScopeMembershipState(
        eligible_labels=normalized_labels,
        status_text=summary.status_text,
        summary_text=summary.summary_text,
        editable=summary.editable,
        all_members_present=summary.all_members_present,
        primary_label=summary.primary_label,
        member_count=summary.member_count,
        has_scope_definition=bool(member_map),
        transition_pending=summary.transition_pending,
    )


def resolve_runtime_state_fetch_state(
    tcp_connected: bool,
    handshake_done: bool,
    tracker_pending: bool,
    log_poll_inflight: bool,
) -> RuntimeStateFetchState:
    """
    NAME
        resolve_runtime_state_fetch_state - Return whether shared host code may fetch runtime state now.
    """
    if not tcp_connected:
        return RuntimeStateFetchState(
            allowed=False,
            blocked_reason=RUNTIME_FETCH_BLOCK_NOT_CONNECTED,
            fetch_source=RUNTIME_FETCH_SOURCE_REST,
        )
    if not handshake_done:
        return RuntimeStateFetchState(
            allowed=False,
            blocked_reason=RUNTIME_FETCH_BLOCK_HANDSHAKE,
            fetch_source=RUNTIME_FETCH_SOURCE_REST,
        )
    if tracker_pending:
        return RuntimeStateFetchState(
            allowed=False,
            blocked_reason=RUNTIME_FETCH_BLOCK_BUSY,
            fetch_source=RUNTIME_FETCH_SOURCE_REST,
        )
    if log_poll_inflight:
        return RuntimeStateFetchState(
            allowed=False,
            blocked_reason=RUNTIME_FETCH_BLOCK_LOG_POLL,
            fetch_source=RUNTIME_FETCH_SOURCE_REST,
        )
    return RuntimeStateFetchState(
        allowed=True,
        blocked_reason="",
        fetch_source=RUNTIME_FETCH_SOURCE_REST,
    )


def resolve_scope_control_state(
    *,
    scope_kind: object,
    runtime_ui_ready: bool,
    tracker_pending: bool,
    stale_state: bool,
    runtime_state_seen: bool,
    runtime_profile_active: bool = False,
    controlled_lifecycle_active: bool,
    transition_pending: bool,
    runnable_scope_state: RunnableScopeState,
    current_scope_member_labels: Optional[List[object]] = None,
    desired_scope_member_labels: Optional[List[object]] = None,
    selected_test_name: object,
    selected_test_ready: bool,
    selected_test_invalid: bool,
    selected_test_running: bool,
    selected_test_runtime_block_reason: object,
) -> ScopeControlState:
    """
    NAME
        resolve_scope_control_state - Return shared scope-control ownership gates for host actions.
    """
    normalized_scope = _normalize_scope_kind(scope_kind)
    base_allowed = bool(runtime_ui_ready) and not bool(tracker_pending) and not bool(stale_state)
    runtime_block_reason = str(selected_test_runtime_block_reason or "").strip()
    selected_test_selected = str(selected_test_name or "").strip() not in ("", PROFILE_NONE)
    current_scope_members = tuple(
        sorted(
            {
                str(label or "").strip().lower()
                for label in list(current_scope_member_labels or [])
                if str(label or "").strip()
            }
        )
    )
    desired_scope_members = tuple(
        sorted(
            {
                str(label or "").strip().lower()
                for label in list(desired_scope_member_labels or [])
                if str(label or "").strip()
            }
        )
    )
    membership_change_required = bool(desired_scope_members) and any(
        member not in current_scope_members for member in desired_scope_members
    )
    runtime_or_scope_active = bool(runtime_profile_active) or bool(controlled_lifecycle_active)
    activate_allowed = False
    deactivate_allowed = False
    run_selected_allowed = False
    active_group_editable = False
    blocked_reason = ""
    requires_runtime_state = normalized_scope == RUNNABLE_SCOPE_KIND_MANUAL
    if requires_runtime_state and not runtime_state_seen:
        blocked_reason = SCOPE_CONTROL_BLOCKED_WAITING_TEXT
    elif transition_pending:
        blocked_reason = RUNNABLE_SCOPE_PANEL_RESYNC_DETAIL
    elif normalized_scope == RUNNABLE_SCOPE_KIND_SELECTED_TEST and not selected_test_selected:
        blocked_reason = TEST_SCOPE_STATUS_NO_SELECTION_DETAIL
    elif normalized_scope == RUNNABLE_SCOPE_KIND_SELECTED_TEST and selected_test_invalid:
        blocked_reason = TEST_SCOPE_STATUS_REQUIRED_UNAVAILABLE_DETAIL
    elif normalized_scope == RUNNABLE_SCOPE_KIND_SELECTED_TEST and selected_test_running:
        blocked_reason = TEST_SCOPE_STATUS_RUNNING_DETAIL
    elif (
        normalized_scope == RUNNABLE_SCOPE_KIND_SELECTED_TEST
        and bool(controlled_lifecycle_active)
        and membership_change_required
    ):
        blocked_reason = TEST_SCOPE_STATUS_SCOPE_SWAP_REQUIRED_DETAIL
    elif runtime_block_reason:
        blocked_reason = runtime_block_reason
    else:
        blocked_reason = str(runnable_scope_state.blocked_reason or "").strip()
    if base_allowed and not transition_pending and not runtime_block_reason and not selected_test_running:
        if normalized_scope == RUNNABLE_SCOPE_KIND_SELECTED_TEST:
            activate_allowed = (
                selected_test_selected
                and not bool(selected_test_invalid)
                and not (bool(controlled_lifecycle_active) and membership_change_required)
            )
        else:
            activate_allowed = bool(runnable_scope_state.activation_allowed)
    deactivate_allowed = (
        base_allowed
        and not transition_pending
        and not bool(selected_test_running)
        and runtime_or_scope_active
    )
    run_selected_allowed = (
        bool(runtime_ui_ready)
        and normalized_scope == RUNNABLE_SCOPE_KIND_SELECTED_TEST
        and selected_test_selected
        and not bool(selected_test_running)
        and bool(selected_test_ready)
    )
    active_group_editable = (
        bool(runtime_state_seen)
        and not bool(controlled_lifecycle_active)
        and not bool(transition_pending)
    )
    return ScopeControlState(
        scope_kind=normalized_scope,
        activate_allowed=activate_allowed,
        deactivate_allowed=deactivate_allowed,
        run_selected_allowed=run_selected_allowed,
        active_group_editable=active_group_editable,
        blocked_reason=blocked_reason,
        transition_pending=bool(transition_pending),
    )


def resolve_manual_duty_scope_state(
    *,
    label: object,
    runtime_state_by_label: Dict[str, Dict[str, Any]],
    controlled_lifecycle_active: bool,
) -> ManualDutyScopeState:
    """
    NAME
        resolve_manual_duty_scope_state - Return whether one manual-duty target is allowed in the current scope state.
    """
    clean_label = str(label or "").strip().lower()
    if not clean_label:
        return ManualDutyScopeState(
            allowed=False,
            blocked_reason=MANUAL_DUTY_BLOCKED_CONTROLLED_SCOPE_TEXT,
        )
    runtime_device = runtime_state_by_label.get(clean_label, {})
    if not isinstance(runtime_device, dict):
        return ManualDutyScopeState(
            allowed=False,
            blocked_reason=MANUAL_DUTY_BLOCKED_CONTROLLED_SCOPE_TEXT,
        )
    if controlled_lifecycle_active:
        lifecycle_state = str(
            runtime_device.get("lifecycleState", "")
        ).strip()
        allowed = lifecycle_state == SCOPE_MEMBERSHIP_RUNTIME_STATE_CONTROLLED_ACTIVE
    else:
        allowed = bool(runtime_device.get("testable", False))
    return ManualDutyScopeState(
        allowed=allowed,
        blocked_reason="" if allowed else MANUAL_DUTY_BLOCKED_CONTROLLED_SCOPE_TEXT,
    )


def _runtime_device_confirms_manual_duty_ready(runtime_device: object) -> bool:
    """
    NAME
        _runtime_device_confirms_manual_duty_ready - Return whether one runtime payload already proves manual-duty readiness.
    """
    if not isinstance(runtime_device, dict):
        return False
    lifecycle_state = str(runtime_device.get("lifecycleState", "")).strip().lower()
    if lifecycle_state == SCOPE_MEMBERSHIP_RUNTIME_STATE_CONTROLLED_ACTIVE:
        return True
    if bool(runtime_device.get("testable", False)):
        return True
    return bool(runtime_device.get("instantiated", False))


def _all_targets_confirm_manual_duty_ready(
    target_labels: List[object],
    runtime_state_by_label: Dict[str, Dict[str, Any]],
) -> bool:
    """
    NAME
        _all_targets_confirm_manual_duty_ready - Return whether all requested targets already confirm ready state.
    """
    clean_targets = [str(label or "").strip().lower() for label in list(target_labels or []) if str(label or "").strip()]
    if not clean_targets:
        return False
    return all(
        _runtime_device_confirms_manual_duty_ready(runtime_state_by_label.get(label_key))
        for label_key in clean_targets
    )


def resolve_manual_duty_access_state(
    *,
    tcp_connected: bool,
    runtime_state_seen: bool,
    stale_state: bool,
    robot_estopped: bool,
    robot_enabled: bool,
    tracker_pending: bool,
    transition_pending: bool,
    target_labels: List[object],
    runtime_state_by_label: Dict[str, Dict[str, Any]],
    controlled_lifecycle_active: bool,
    runtime_groups: List[Dict[str, Any]],
) -> ManualDutyAccessState:
    """
    NAME
        resolve_manual_duty_access_state - Return shared manual-duty gating across popup entry points.
    """
    if not tcp_connected:
        return ManualDutyAccessState(False, MANUAL_DUTY_BLOCKED_NOT_CONNECTED_TEXT)
    if not runtime_state_seen:
        return ManualDutyAccessState(False, MANUAL_DUTY_BLOCKED_WAITING_TEXT)
    if transition_pending:
        return ManualDutyAccessState(False, MANUAL_DUTY_BLOCKED_TRANSITION_TEXT)
    targets_confirmed_ready = _all_targets_confirm_manual_duty_ready(
        target_labels,
        runtime_state_by_label,
    )
    if tracker_pending and not targets_confirmed_ready:
        return ManualDutyAccessState(False, RUNTIME_FETCH_BLOCK_BUSY)
    if stale_state and not targets_confirmed_ready:
        return ManualDutyAccessState(False, MANUAL_DUTY_BLOCKED_STALE_TEXT)
    if robot_estopped:
        return ManualDutyAccessState(False, MANUAL_DUTY_BLOCKED_ESTOP_TEXT)
    if not robot_enabled:
        return ManualDutyAccessState(False, MANUAL_DUTY_BLOCKED_DISABLED_TEXT)
    for label in list(target_labels or []):
        scope_state = resolve_manual_duty_scope_state(
            label=label,
            runtime_state_by_label=runtime_state_by_label,
            controlled_lifecycle_active=controlled_lifecycle_active,
        )
        if not scope_state.allowed:
            return ManualDutyAccessState(False, scope_state.blocked_reason)
    binding_state = resolve_manual_duty_binding_state(
        target_labels=target_labels,
        runtime_groups=runtime_groups,
    )
    if not binding_state.allowed:
        return ManualDutyAccessState(False, binding_state.blocked_reason)
    return ManualDutyAccessState(True, "")


def resolve_manual_duty_action_state(
    *,
    tcp_connected: bool,
    runtime_state_seen: bool,
    stale_state: bool,
    robot_estopped: bool,
    robot_enabled: bool,
    tracker_pending: bool,
    transition_pending: bool,
    target_labels: List[object],
    runtime_state_by_label: Dict[str, Dict[str, Any]],
    controlled_lifecycle_active: bool,
    runtime_groups: List[Dict[str, Any]],
) -> HostActionAccessState:
    """
    NAME
        resolve_manual_duty_action_state - Return shared popup-entry policy for manual-duty actions.
    """
    access_state = resolve_manual_duty_access_state(
        tcp_connected=tcp_connected,
        runtime_state_seen=runtime_state_seen,
        stale_state=stale_state,
        robot_estopped=robot_estopped,
        robot_enabled=robot_enabled,
        tracker_pending=tracker_pending,
        transition_pending=transition_pending,
        target_labels=target_labels,
        runtime_state_by_label=runtime_state_by_label,
        controlled_lifecycle_active=controlled_lifecycle_active,
        runtime_groups=runtime_groups,
    )
    return HostActionAccessState(
        allowed=access_state.allowed,
        blocked_reason=access_state.blocked_reason,
        refresh_before_action=access_state.allowed,
        refresh_after_action=False,
        refresh_when_blocked=False,
    )


def resolve_active_group_edit_action_state(
    *,
    tcp_connected: bool,
    tracker_pending: bool,
    controlled_lifecycle_active: bool,
    scope_control_state: ScopeControlState,
) -> HostActionAccessState:
    """
    NAME
        resolve_active_group_edit_action_state - Return shared edit-access policy for active-group membership actions.
    """
    if not tcp_connected:
        return HostActionAccessState(
            allowed=False,
            blocked_reason=HOST_ACTION_BLOCKED_NOT_CONNECTED_TEXT,
            refresh_before_action=False,
            refresh_after_action=False,
            refresh_when_blocked=False,
        )
    if tracker_pending:
        return HostActionAccessState(
            allowed=False,
            blocked_reason=HOST_ACTION_BLOCKED_BUSY_TEXT,
            refresh_before_action=False,
            refresh_after_action=False,
            refresh_when_blocked=False,
        )
    if controlled_lifecycle_active:
        return HostActionAccessState(
            allowed=False,
            blocked_reason=ACTIVE_GROUP_EDIT_BLOCKED_LOCKED_TEXT,
            refresh_before_action=False,
            refresh_after_action=False,
            refresh_when_blocked=True,
        )
    if not bool(scope_control_state.active_group_editable):
        return HostActionAccessState(
            allowed=False,
            blocked_reason=str(scope_control_state.blocked_reason or SCOPE_CONTROL_BLOCKED_WAITING_TEXT).strip(),
            refresh_before_action=False,
            refresh_after_action=False,
            refresh_when_blocked=True,
        )
    return HostActionAccessState(
        allowed=True,
        blocked_reason="",
        refresh_before_action=False,
        refresh_after_action=True,
        refresh_when_blocked=False,
    )


def resolve_override_action_state(
    *,
    tcp_connected: bool,
    tracker_pending: bool,
) -> HostActionAccessState:
    """
    NAME
        resolve_override_action_state - Return shared entry policy for explicit lifecycle override actions.
    """
    if not tcp_connected:
        return HostActionAccessState(
            allowed=False,
            blocked_reason=HOST_ACTION_BLOCKED_NOT_CONNECTED_TEXT,
            refresh_before_action=False,
            refresh_after_action=False,
            refresh_when_blocked=False,
        )
    if tracker_pending:
        return HostActionAccessState(
            allowed=False,
            blocked_reason=HOST_ACTION_BLOCKED_BUSY_TEXT,
            refresh_before_action=False,
            refresh_after_action=False,
            refresh_when_blocked=False,
        )
    return HostActionAccessState(
        allowed=True,
        blocked_reason="",
        refresh_before_action=False,
        refresh_after_action=True,
        refresh_when_blocked=False,
    )
