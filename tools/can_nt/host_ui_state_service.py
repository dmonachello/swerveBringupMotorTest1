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
RUNNABLE_SCOPE_PANEL_DISCONNECTED_DETAIL = (
    "Robot connection unavailable. Power the robot and reconnect before running."
)
RUNNABLE_SCOPE_DETAIL_MANUAL_NOT_ACTIVATED = "Activate Group first."
RUNNABLE_SCOPE_DETAIL_SELECTED_TEST_NOT_ACTIVATED = "Activate scope first."
RUNNABLE_SCOPE_DETAIL_MANUAL_NOT_TELEOP = "Switch to teleop, then Activate Group."
RUNNABLE_SCOPE_DETAIL_SELECTED_TEST_NOT_TELEOP = "Switch to teleop, then Activate Scope."
RUNNABLE_SCOPE_DETAIL_MANUAL_EMPTY = "Active group is empty. Add devices before Activate Group."
RUNNABLE_SCOPE_DETAIL_SELECT_PROFILE = (
    "Select a profile before using manual/group controls."
)
RUNNABLE_SCOPE_DETAIL_STALE_STATE = "Robot state stale (code not running?)"
RUNNABLE_SCOPE_DETAIL_ESTOP = "Robot E-Stop. Manual run blocked."
RUNNABLE_SCOPE_DETAIL_DISABLED = "Robot disabled. Enable teleop to run motors."
RUNTIME_EVENT_NOTICE_TOKEN_DISABLED = "robot disabled"
RUNTIME_EVENT_NOTICE_TOKEN_ESTOP = "e-stop"
RUNTIME_EVENT_NOTICE_TOKEN_RUNTIME_INACTIVE = "runtime inactive"
RUNTIME_EVENT_NOTICE_TOKEN_ACTIVATE_GROUP = "activate group first"
RUNTIME_EVENT_NOTICE_TOKEN_ACTIVATE_SCOPE = "activate scope first"
RUNTIME_EVENT_NOTICE_TOKEN_GROUP_EMPTY = "active group is empty"
RUNTIME_EVENT_NOTICE_TOKEN_SELECT_PROFILE = "select a profile"
BLANK_REASON_LOCAL_PROFILE_REQUIRED = "Local profile selection required."
OUTPUT_NO_SELECTED_TEST = "no selected test"
SELECTED_TEST_STATUS_LOADED_NOT_ACTIVATED = "selected test scope ready - not activated"
SELECTED_TEST_STATUS_MANUAL_RESTORED = "manual active-group restored - not activated"
SELECTED_TEST_STATUS_BLOCKED_ESTOP = "robot disabled (E-Stop)"
SELECTED_TEST_STATUS_BLOCKED_DISABLED = "robot disabled"
SELECTED_TEST_STATUS_BLOCKED_NOT_TELEOP = "robot not in teleop"
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
    "This test requires the devices shown in Selected Test Devices. Press Activate Group, then run the test."
)
TEST_SCOPE_STATUS_MANUAL_RESTORED_DETAIL = (
    "The remembered manual active-group was restored after leaving Tests. Press Activate Group before running manual actions."
)
TEST_SCOPE_STATUS_MISSING_DEVICE_PREFIX = (
    "This test cannot run because a required profile device is missing: "
)
TEST_SCOPE_STATUS_REQUIRED_UNAVAILABLE_DETAIL = (
    "This test cannot run because one or more required devices are not available."
)
TEST_SCOPE_STATUS_BLOCKED_ESTOP_DETAIL = (
    "This test cannot run because the robot is E-stopped. Clear the E-stop before activating the group or running the test."
)
TEST_SCOPE_STATUS_BLOCKED_DISABLED_DETAIL = (
    "This test cannot run because the robot is disabled. Enable teleop before activating the group or running the test."
)
TEST_SCOPE_STATUS_BLOCKED_NOT_TELEOP_DETAIL = (
    "This test cannot run because the robot is not in teleop. Switch to teleop before activating the group or running the test."
)
TEST_SCOPE_STATUS_INACTIVE_PREFIX = "selected test inactive - "
TEST_ACTIVE_GROUP_STATUS_LOCKED = "locked"
TEST_ACTIVE_GROUP_STATUS_INVALID = "invalid"
TEST_ACTIVE_GROUP_STATUS_NOT_ACTIVATED = "not instantiated"
TEST_ACTIVE_GROUP_STATUS_ENABLED = "enabled"
TEST_ACTIVE_GROUP_SINGLETON_LABELS = {"controller0", "roborio", "pdp"}
ACTIVE_GROUP_STATUS_WAITING_TEXT = "waiting for robot runtime state"
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
RUNTIME_FETCH_SOURCE_REST = "rest_runtime_state"
RUNTIME_FETCH_BLOCK_NOT_CONNECTED = "Not connected: runtime state unavailable."
RUNTIME_FETCH_BLOCK_HANDSHAKE = "Runtime state unavailable: waiting for UI session handshake."
RUNTIME_FETCH_BLOCK_BUSY = "Busy: wait for current command to finish."
RUNTIME_FETCH_BLOCK_LOG_POLL = "Busy: wait for current log poll to finish."


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
    instantiated: bool
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
class ManualDutyScopeState:
    """
    NAME
        ManualDutyScopeState - Shared host-side manual-duty scope eligibility result.
    """

    allowed: bool
    blocked_reason: str


def _normalize_profile_name(value: object) -> str:
    """
    NAME
        _normalize_profile_name - Return one trimmed profile name or PROFILE_NONE.
    """
    clean = str(value or "").strip()
    return clean if clean else PROFILE_NONE


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
    robot_estopped: bool,
    robot_enabled: bool,
    robot_mode: object,
) -> str:
    """
    NAME
        resolve_selected_test_runtime_block_reason - Return robot-state blocker text for selected-test execution.
    """
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
        elif loaded_to_robot is False:
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
    elif reason == SELECTED_TEST_STATUS_BLOCKED_ESTOP:
        detail = TEST_SCOPE_STATUS_BLOCKED_ESTOP_DETAIL
    elif reason == SELECTED_TEST_STATUS_BLOCKED_DISABLED:
        detail = TEST_SCOPE_STATUS_BLOCKED_DISABLED_DETAIL
    elif reason == SELECTED_TEST_STATUS_BLOCKED_NOT_TELEOP:
        detail = TEST_SCOPE_STATUS_BLOCKED_NOT_TELEOP_DETAIL
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
    result: List[ActiveGroupMemberRowState] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        label = str(row.get("label", "")).strip()
        if not label:
            continue
        statuses = [TEST_ACTIVE_GROUP_STATUS_ENABLED]
        if bool(row.get("locked")) or scope_active:
            statuses.append(TEST_ACTIVE_GROUP_STATUS_LOCKED)
        if bool(row.get("invalid")):
            statuses.append(TEST_ACTIVE_GROUP_STATUS_INVALID)
        runtime_device = runtime_state_by_label.get(label.lower(), {})
        instantiated = False
        if isinstance(runtime_device, dict):
            if bool(runtime_device.get("instantiated", False)):
                instantiated = True
            elif label.lower() in TEST_ACTIVE_GROUP_SINGLETON_LABELS:
                instantiated = bool(runtime_device.get("testable", False))
        statuses.append(
            "instantiated"
            if scope_active and instantiated
            else TEST_ACTIVE_GROUP_STATUS_NOT_ACTIVATED
        )
        reason = str(row.get("reason", "")).strip()
        line = f"{label} | " + " | ".join(statuses)
        if reason:
            line += f" | {reason}"
        result.append(
            ActiveGroupMemberRowState(
                label=label,
                statuses=statuses,
                reason=reason,
                instantiated=instantiated,
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
) -> ActiveGroupSummaryState:
    """
    NAME
        resolve_active_group_summary_state - Return shared active-group status and summary state.
    """
    clean_primary = str(primary_label or "").strip()
    member_count = len(member_map)
    if not runtime_state_seen:
        return ActiveGroupSummaryState(
            status_text=ACTIVE_GROUP_STATUS_WAITING_TEXT,
            summary_text=f"Primary: {clean_primary}" if clean_primary else ACTIVE_GROUP_SUMMARY_EMPTY_TEXT,
            editable=False,
            all_members_present=False,
            primary_label=clean_primary,
            member_count=member_count,
        )
    if not member_map:
        return ActiveGroupSummaryState(
            status_text=ACTIVE_GROUP_STATUS_EMPTY_TEXT,
            summary_text=ACTIVE_GROUP_SUMMARY_EMPTY_TEXT,
            editable=not controlled_lifecycle_active,
            all_members_present=False,
            primary_label=clean_primary,
            member_count=0,
        )
    all_members_present = True
    for label_key in member_map.keys():
        live = runtime_state_by_label.get(str(label_key).strip().lower(), {})
        presence = live.get("presenceConfidence") if isinstance(live, dict) else None
        if not isinstance(presence, (int, float)) or float(presence) < 0.5:
            all_members_present = False
            break
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
    )


def resolve_active_scope_membership_state(
    *,
    runtime_state_seen: bool,
    controlled_lifecycle_active: bool,
    member_map: Dict[str, Dict[str, Any]],
    runtime_state_by_label: Dict[str, Dict[str, Any]],
    primary_label: object,
    eligible_labels: List[str],
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
