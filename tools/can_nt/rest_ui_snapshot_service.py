from __future__ import annotations

"""
NAME
    rest_ui_snapshot_service.py - Pure REST-to-typed UI snapshot normalization.

DESCRIPTION
    Converts raw REST payload dictionaries into immutable typed UI snapshot
    records. This module is intentionally stateless: every normalization call
    reflects only the payloads supplied to that call.
"""

from collections.abc import Iterable, Mapping
from typing import Any, Dict, Tuple

from tools.can_nt.rest_ui_state_models import (
    EMPTY_LABEL,
    EMPTY_MODE_NAME,
    EMPTY_PROFILE_NAME,
    EMPTY_SESSION_ID,
    EMPTY_SOURCE_NAME,
    EMPTY_STATUS_NAME,
    EMPTY_TEST_NAME,
    BOOLEAN_FALSE,
    RestUiSnapshots,
    RuntimeDeviceSnapshot,
    RuntimeGroupMemberSnapshot,
    RuntimeGroupSnapshot,
    RuntimeSnapshot,
    SessionSnapshot,
    TestRowSnapshot,
    TestsRunSnapshot,
    TestsSnapshot,
    ZERO_TIME_MS,
)


SOURCE_NAME_SESSION = "rest_session"
SOURCE_NAME_RUNTIME = "rest_runtime_state"
SOURCE_NAME_TESTS = "rest_tests_state"
KEY_SESSION_ID = "sessionId"
KEY_GENERATED_AT_MS = "generatedAtMs"
KEY_LAST_ACTIVITY_MS = "lastActivityMs"
KEY_CONNECTED = "connected"
KEY_OWNER_CLIENT_ID = "ownerClientId"
KEY_ENABLED = "enabled"
KEY_ESTOPPED = "estopped"
KEY_MODE = "mode"
KEY_SELECTED_PROFILE = "selectedProfile"
KEY_ACTIVE_RUNTIME_PROFILE = "activeRuntimeProfile"
KEY_RUNTIME_ACTIVE = "runtimeActive"
KEY_CONTROLLED_LIFECYCLE_ACTIVE = "controlledLifecycleActive"
KEY_LAST_ACK_MS = "lastAckMs"
KEY_DEVICES = "devices"
KEY_GROUPS = "groups"
KEY_LABEL = "label"
KEY_PRESENT = "present"
KEY_INSTANTIATED = "instantiated"
KEY_SCOPE_ACTIVE = "scopeActive"
KEY_TESTABLE = "testable"
KEY_MANUAL_OPERABLE = "manualOperable"
KEY_TEST_OPERABLE = "testOperable"
KEY_LIFECYCLE_STATE = "lifecycleState"
KEY_ACTIVE_GROUP_LABEL = "activeGroupLabel"
KEY_IDENTITY = "identity"
KEY_TELEMETRY = "telemetry"
KEY_NAME = "name"
KEY_BINDING_ACTIVE = "bindingActive"
KEY_MEMBER_COUNT = "memberCount"
KEY_MEMBERS = "members"
KEY_PRIMARY_LABEL = "primaryLabel"
KEY_LOCKED = "locked"
KEY_INVALID = "invalid"
KEY_RUNTIME_PRESENT = "runtimePresent"
KEY_NOTE = "note"
KEY_ROWS = "rows"
KEY_SELECTED = "selected"
KEY_STATUS = "status"
KEY_REQUIRED_DEVICES = "requiredDevices"
KEY_EXISTS_LOCALLY = "existsLocally"
KEY_RUNNABLE_KNOWN = "runnableKnown"
KEY_RUNNABLE_NOW = "runnableNow"
KEY_BLOCKED_REASON = "blockedReason"
KEY_RUN = "run"
KEY_RUN_ID = "runId"
KEY_STATE = "state"
KEY_TEST = "test"
KEY_RESULT = "result"
KEY_MESSAGE = "message"
KEY_STARTED_AT_MS = "startedAtMs"
KEY_FINISHED_AT_MS = "finishedAtMs"
STATUS_RUNNING = "running"
TOKEN_TRUE = "true"
TOKEN_ONE = "1"
TOKEN_YES = "yes"
TOKEN_ON = "on"
TOKEN_FALSE = "false"
TOKEN_ZERO = "0"
TOKEN_NO = "no"
TOKEN_OFF = "off"
TOKEN_COMMA = ","


def _normalize_bool(value: Any, default: bool = BOOLEAN_FALSE) -> bool:
    """
    NAME
        _normalize_bool - Convert REST scalar values into a normalized boolean.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in (TOKEN_TRUE, TOKEN_ONE, TOKEN_YES, TOKEN_ON):
            return True
        if normalized in (TOKEN_FALSE, TOKEN_ZERO, TOKEN_NO, TOKEN_OFF, EMPTY_STATUS_NAME):
            return False
    return default


def _normalize_str(value: Any, default: str = EMPTY_STATUS_NAME) -> str:
    """
    NAME
        _normalize_str - Convert a REST scalar into a normalized string.
    """
    if value is None:
        return default
    return str(value)


def _normalize_float(value: Any, default: float = ZERO_TIME_MS) -> float:
    """
    NAME
        _normalize_float - Convert a REST scalar into a normalized float.
    """
    try:
        return float(value)
    except Exception:
        return default


def _normalize_mapping(value: Any) -> Mapping[str, Any]:
    """
    NAME
        _normalize_mapping - Return a mapping when the input is dict-like.
    """
    if isinstance(value, dict):
        return dict(value)
    return {}


def _normalize_runtime_device_snapshot(row: Any) -> RuntimeDeviceSnapshot:
    """
    NAME
        _normalize_runtime_device_snapshot - Normalize one runtime device row.
    """
    payload = row if isinstance(row, dict) else {}
    return RuntimeDeviceSnapshot(
        label=_normalize_str(payload.get(KEY_LABEL), EMPTY_LABEL),
        enabled=_normalize_bool(payload.get(KEY_ENABLED)),
        present=_normalize_bool(payload.get(KEY_PRESENT)),
        instantiated=_normalize_bool(payload.get(KEY_INSTANTIATED)),
        scope_active=_normalize_bool(payload.get(KEY_SCOPE_ACTIVE)),
        testable=_normalize_bool(payload.get(KEY_TESTABLE)),
        manual_operable=_normalize_bool(payload.get(KEY_MANUAL_OPERABLE)),
        test_operable=_normalize_bool(payload.get(KEY_TEST_OPERABLE)),
        lifecycle_state=_normalize_str(payload.get(KEY_LIFECYCLE_STATE), EMPTY_STATUS_NAME).strip().lower(),
        active_group_label=_normalize_str(payload.get(KEY_ACTIVE_GROUP_LABEL), EMPTY_LABEL),
        identity=_normalize_mapping(payload.get(KEY_IDENTITY)),
        telemetry=_normalize_mapping(payload.get(KEY_TELEMETRY)),
    )


def _normalize_runtime_group_member_snapshot(row: Any) -> RuntimeGroupMemberSnapshot:
    """
    NAME
        _normalize_runtime_group_member_snapshot - Normalize one runtime group-member row.
    """
    payload = row if isinstance(row, dict) else {}
    return RuntimeGroupMemberSnapshot(
        label=_normalize_str(payload.get(KEY_LABEL), EMPTY_LABEL),
        enabled=_normalize_bool(payload.get(KEY_ENABLED)),
        locked=_normalize_bool(payload.get(KEY_LOCKED)),
        invalid=_normalize_bool(payload.get(KEY_INVALID)),
        scope_active=_normalize_bool(payload.get(KEY_SCOPE_ACTIVE)),
        runtime_present=_normalize_bool(payload.get(KEY_RUNTIME_PRESENT)),
        instantiated=_normalize_bool(payload.get(KEY_INSTANTIATED)),
        testable=_normalize_bool(payload.get(KEY_TESTABLE)),
        note=_normalize_str(payload.get(KEY_NOTE), EMPTY_STATUS_NAME),
    )


def _normalize_runtime_group_snapshot(row: Any) -> RuntimeGroupSnapshot:
    """
    NAME
        _normalize_runtime_group_snapshot - Normalize one runtime group row.
    """
    payload = row if isinstance(row, dict) else {}
    members_payload = payload.get(KEY_MEMBERS)
    members: Tuple[RuntimeGroupMemberSnapshot, ...] = ()
    if isinstance(members_payload, list):
        members = tuple(
            _normalize_runtime_group_member_snapshot(member_row)
            for member_row in members_payload
        )
    return RuntimeGroupSnapshot(
        name=_normalize_str(payload.get(KEY_NAME), EMPTY_LABEL),
        enabled=_normalize_bool(payload.get(KEY_ENABLED)),
        primary_label=_normalize_str(payload.get(KEY_PRIMARY_LABEL), EMPTY_LABEL),
        binding_active=_normalize_bool(payload.get(KEY_BINDING_ACTIVE)),
        member_count=int(_normalize_float(payload.get(KEY_MEMBER_COUNT), 0.0)),
        members=members,
    )


def _normalize_required_devices(value: Any) -> Tuple[str, ...]:
    """
    NAME
        _normalize_required_devices - Normalize list or comma-string required device sets.
    """
    if isinstance(value, list):
        items = [_normalize_str(item, EMPTY_LABEL).strip() for item in value]
    elif isinstance(value, str):
        items = [part.strip() for part in value.split(TOKEN_COMMA)]
    else:
        items = []
    return tuple(item for item in items if item)


def _normalize_test_row_snapshot(row: Any) -> TestRowSnapshot:
    """
    NAME
        _normalize_test_row_snapshot - Normalize one tests-state row.
    """
    payload = row if isinstance(row, dict) else {}
    return TestRowSnapshot(
        name=_normalize_str(payload.get(KEY_NAME), EMPTY_TEST_NAME).strip(),
        selected=_normalize_bool(payload.get(KEY_SELECTED)),
        enabled=_normalize_bool(payload.get(KEY_ENABLED), True),
        status=_normalize_str(payload.get(KEY_STATUS), EMPTY_STATUS_NAME).strip().lower(),
        required_devices=_normalize_required_devices(payload.get(KEY_REQUIRED_DEVICES)),
        exists_locally=_normalize_bool(payload.get(KEY_EXISTS_LOCALLY)),
        runnable_known=_normalize_bool(payload.get(KEY_RUNNABLE_KNOWN)),
        runnable_now=_normalize_bool(payload.get(KEY_RUNNABLE_NOW)),
        blocked_reason=_normalize_str(payload.get(KEY_BLOCKED_REASON), EMPTY_STATUS_NAME).strip(),
    )


def normalize_session_snapshot(
    session_state: Mapping[str, Any] | None,
    *,
    received_at_ms: float,
    source_name: str = SOURCE_NAME_SESSION,
) -> SessionSnapshot:
    """
    NAME
        normalize_session_snapshot - Normalize raw session payload into SessionSnapshot.
    """
    payload = session_state if isinstance(session_state, Mapping) else {}
    session_id = _normalize_str(payload.get(KEY_SESSION_ID), EMPTY_SESSION_ID)
    owner_client_id = _normalize_str(payload.get(KEY_OWNER_CLIENT_ID), EMPTY_SESSION_ID).strip()
    return SessionSnapshot(
        received_at_ms=_normalize_float(received_at_ms),
        source_name=_normalize_str(source_name, EMPTY_SOURCE_NAME),
        session_id=session_id,
        generated_at_ms=_normalize_float(payload.get(KEY_GENERATED_AT_MS), ZERO_TIME_MS),
        last_activity_ms=_normalize_float(payload.get(KEY_LAST_ACTIVITY_MS), ZERO_TIME_MS),
        handshake_ready=bool(session_id.strip()),
        owner_known=bool(owner_client_id),
    )


def normalize_runtime_snapshot(
    runtime_state: Mapping[str, Any] | None,
    *,
    received_at_ms: float,
    source_name: str = SOURCE_NAME_RUNTIME,
) -> RuntimeSnapshot:
    """
    NAME
        normalize_runtime_snapshot - Normalize raw runtime payload into RuntimeSnapshot.
    """
    payload = runtime_state if isinstance(runtime_state, Mapping) else {}
    devices_by_label: Dict[str, RuntimeDeviceSnapshot] = {}
    device_order: list[str] = []
    for row in _iter_list(payload.get(KEY_DEVICES)):
        snapshot = _normalize_runtime_device_snapshot(row)
        if not snapshot.label:
            continue
        devices_by_label[snapshot.label] = snapshot
        if snapshot.label not in device_order:
            device_order.append(snapshot.label)
    groups_by_name: Dict[str, RuntimeGroupSnapshot] = {}
    group_order: list[str] = []
    for row in _iter_list(payload.get(KEY_GROUPS)):
        snapshot = _normalize_runtime_group_snapshot(row)
        if not snapshot.name:
            continue
        groups_by_name[snapshot.name] = snapshot
        if snapshot.name not in group_order:
            group_order.append(snapshot.name)
    return RuntimeSnapshot(
        received_at_ms=_normalize_float(received_at_ms),
        source_name=_normalize_str(source_name, EMPTY_SOURCE_NAME),
        selected_profile=_normalize_str(payload.get(KEY_SELECTED_PROFILE), EMPTY_PROFILE_NAME),
        active_runtime_profile=_normalize_str(
            payload.get(KEY_ACTIVE_RUNTIME_PROFILE),
            EMPTY_PROFILE_NAME,
        ),
        runtime_active=_normalize_bool(payload.get(KEY_RUNTIME_ACTIVE)),
        controlled_lifecycle_active=_normalize_bool(payload.get(KEY_CONTROLLED_LIFECYCLE_ACTIVE)),
        robot_enabled=_normalize_bool(payload.get(KEY_ENABLED)),
        robot_estopped=_normalize_bool(payload.get(KEY_ESTOPPED)),
        robot_mode=_normalize_str(payload.get(KEY_MODE), EMPTY_MODE_NAME).strip().lower(),
        last_ack_ms=_normalize_float(payload.get(KEY_LAST_ACK_MS), _normalize_float(received_at_ms)),
        devices_by_label=devices_by_label,
        groups_by_name=groups_by_name,
        device_order=tuple(device_order),
        group_order=tuple(group_order),
    )


def normalize_tests_snapshot(
    tests_state: Mapping[str, Any] | None,
    *,
    received_at_ms: float,
    source_name: str = SOURCE_NAME_TESTS,
) -> TestsSnapshot:
    """
    NAME
        normalize_tests_snapshot - Normalize raw tests payload into TestsSnapshot.
    """
    payload = tests_state if isinstance(tests_state, Mapping) else {}
    rows_by_name: Dict[str, TestRowSnapshot] = {}
    ordered_names: list[str] = []
    selected_name = _normalize_str(payload.get("selectedName"), EMPTY_TEST_NAME).strip()
    active_name = _normalize_str(payload.get("activeName"), EMPTY_TEST_NAME).strip()
    active_status = _normalize_str(payload.get("activeStatus"), EMPTY_STATUS_NAME).strip().lower()
    run_all_active = _normalize_bool(payload.get("runAllActive"))
    for row in _iter_list(payload.get(KEY_ROWS)):
        snapshot = _normalize_test_row_snapshot(row)
        if not snapshot.name:
            continue
        rows_by_name[snapshot.name] = snapshot
        if snapshot.name not in ordered_names:
            ordered_names.append(snapshot.name)
        if snapshot.selected and not selected_name:
            selected_name = snapshot.name
        if snapshot.status == STATUS_RUNNING and not active_name:
            active_name = snapshot.name
            active_status = snapshot.status
    run_payload = payload.get(KEY_RUN)
    run_mapping = run_payload if isinstance(run_payload, Mapping) else {}
    run_snapshot = TestsRunSnapshot(
        run_id=int(_normalize_float(run_mapping.get(KEY_RUN_ID), 0.0)),
        state=_normalize_str(run_mapping.get(KEY_STATE), EMPTY_STATUS_NAME).strip().lower(),
        test_name=_normalize_str(run_mapping.get(KEY_TEST), EMPTY_TEST_NAME).strip(),
        result=_normalize_str(run_mapping.get(KEY_RESULT), EMPTY_STATUS_NAME).strip(),
        status=_normalize_str(run_mapping.get(KEY_STATUS), EMPTY_STATUS_NAME).strip().lower(),
        message=_normalize_str(run_mapping.get(KEY_MESSAGE), EMPTY_STATUS_NAME).strip(),
        started_at_ms=_normalize_float(run_mapping.get(KEY_STARTED_AT_MS), ZERO_TIME_MS),
        finished_at_ms=_normalize_float(run_mapping.get(KEY_FINISHED_AT_MS), ZERO_TIME_MS),
    )
    return TestsSnapshot(
        received_at_ms=_normalize_float(received_at_ms),
        source_name=_normalize_str(source_name, EMPTY_SOURCE_NAME),
        generated_at_ms=_normalize_float(payload.get(KEY_GENERATED_AT_MS), ZERO_TIME_MS),
        selected_name=selected_name,
        active_name=active_name,
        active_status=active_status,
        run_all_active=run_all_active,
        rows_by_name=rows_by_name,
        ordered_names=tuple(ordered_names),
        run=run_snapshot,
    )


def build_rest_ui_snapshots(
    *,
    raw_session: Mapping[str, Any] | None,
    raw_runtime: Mapping[str, Any] | None,
    raw_tests: Mapping[str, Any] | None,
    received_at_ms: float,
) -> RestUiSnapshots:
    """
    NAME
        build_rest_ui_snapshots - Build the current typed REST snapshot bundle.
    """
    normalized_received_at_ms = _normalize_float(received_at_ms)
    return RestUiSnapshots(
        session=normalize_session_snapshot(
            raw_session,
            received_at_ms=normalized_received_at_ms,
        ),
        runtime=normalize_runtime_snapshot(
            raw_runtime,
            received_at_ms=normalized_received_at_ms,
        ),
        tests=normalize_tests_snapshot(
            raw_tests,
            received_at_ms=normalized_received_at_ms,
        ),
    )


def _iter_list(value: Any) -> Iterable[Any]:
    """
    NAME
        _iter_list - Yield list items when the payload field is a list.
    """
    if isinstance(value, list):
        return value
    return ()
