from __future__ import annotations

"""
NAME
    rest_ui_state_models.py - Typed REST-backed UI snapshot models.

DESCRIPTION
    Defines immutable host-side snapshot records for REST-derived UI state.
    These types are additive scaffolding for the typed-state migration and do
    not change current UI behavior by themselves.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Tuple


def _empty_mapping() -> Dict[str, Any]:
    """
    NAME
        _empty_mapping - Return a new empty mapping for dataclass defaults.
    """
    return {}


def _empty_runtime_device_mapping() -> Dict[str, "RuntimeDeviceSnapshot"]:
    """
    NAME
        _empty_runtime_device_mapping - Return a new empty runtime-device map.
    """
    return {}


def _empty_runtime_group_mapping() -> Dict[str, "RuntimeGroupSnapshot"]:
    """
    NAME
        _empty_runtime_group_mapping - Return a new empty runtime-group map.
    """
    return {}


def _empty_test_row_mapping() -> Dict[str, "TestRowSnapshot"]:
    """
    NAME
        _empty_test_row_mapping - Return a new empty test-row map.
    """
    return {}


def _empty_runtime_group_members() -> Tuple["RuntimeGroupMemberSnapshot", ...]:
    """
    NAME
        _empty_runtime_group_members - Return an empty runtime group-member tuple.
    """
    return ()


EMPTY_LABEL = ""
EMPTY_SOURCE_NAME = ""
EMPTY_PROFILE_NAME = ""
EMPTY_MODE_NAME = ""
EMPTY_STATUS_NAME = ""
EMPTY_SESSION_ID = ""
EMPTY_TEST_NAME = ""
ZERO_TIME_MS = 0.0
BOOLEAN_FALSE = False
EMPTY_STRING_TUPLE: Tuple[str, ...] = ()


@dataclass(frozen=True)
class SessionSnapshot:
    """
    NAME
        SessionSnapshot - Normalized REST session snapshot.
    """

    received_at_ms: float = ZERO_TIME_MS
    source_name: str = EMPTY_SOURCE_NAME
    session_id: str = EMPTY_SESSION_ID
    generated_at_ms: float = ZERO_TIME_MS
    last_activity_ms: float = ZERO_TIME_MS
    handshake_ready: bool = BOOLEAN_FALSE
    owner_known: bool = BOOLEAN_FALSE


@dataclass(frozen=True)
class RuntimeDeviceSnapshot:
    """
    NAME
        RuntimeDeviceSnapshot - Normalized runtime device row.
    """

    label: str = EMPTY_LABEL
    enabled: bool = BOOLEAN_FALSE
    present: bool = BOOLEAN_FALSE
    instantiated: bool = BOOLEAN_FALSE
    scope_active: bool = BOOLEAN_FALSE
    testable: bool = BOOLEAN_FALSE
    manual_operable: bool = BOOLEAN_FALSE
    test_operable: bool = BOOLEAN_FALSE
    lifecycle_state: str = EMPTY_STATUS_NAME
    active_group_label: str = EMPTY_LABEL
    identity: Mapping[str, Any] = field(default_factory=_empty_mapping)
    telemetry: Mapping[str, Any] = field(default_factory=_empty_mapping)


@dataclass(frozen=True)
class RuntimeGroupMemberSnapshot:
    """
    NAME
        RuntimeGroupMemberSnapshot - Normalized runtime group-member row.
    """

    label: str = EMPTY_LABEL
    enabled: bool = BOOLEAN_FALSE
    locked: bool = BOOLEAN_FALSE
    invalid: bool = BOOLEAN_FALSE
    scope_active: bool = BOOLEAN_FALSE
    runtime_present: bool = BOOLEAN_FALSE
    instantiated: bool = BOOLEAN_FALSE
    testable: bool = BOOLEAN_FALSE
    note: str = EMPTY_STATUS_NAME


@dataclass(frozen=True)
class RuntimeGroupSnapshot:
    """
    NAME
        RuntimeGroupSnapshot - Normalized runtime group row.
    """

    name: str = EMPTY_LABEL
    enabled: bool = BOOLEAN_FALSE
    primary_label: str = EMPTY_LABEL
    binding_active: bool = BOOLEAN_FALSE
    member_count: int = 0
    members: Tuple[RuntimeGroupMemberSnapshot, ...] = field(
        default_factory=_empty_runtime_group_members
    )


@dataclass(frozen=True)
class RuntimeSnapshot:
    """
    NAME
        RuntimeSnapshot - Normalized REST runtime snapshot.
    """

    received_at_ms: float = ZERO_TIME_MS
    source_name: str = EMPTY_SOURCE_NAME
    selected_profile: str = EMPTY_PROFILE_NAME
    active_runtime_profile: str = EMPTY_PROFILE_NAME
    runtime_active: bool = BOOLEAN_FALSE
    controlled_lifecycle_active: bool = BOOLEAN_FALSE
    robot_enabled: bool = BOOLEAN_FALSE
    robot_estopped: bool = BOOLEAN_FALSE
    robot_mode: str = EMPTY_MODE_NAME
    last_ack_ms: float = ZERO_TIME_MS
    devices_by_label: Mapping[str, RuntimeDeviceSnapshot] = field(
        default_factory=_empty_runtime_device_mapping
    )
    groups_by_name: Mapping[str, RuntimeGroupSnapshot] = field(
        default_factory=_empty_runtime_group_mapping
    )
    device_order: Tuple[str, ...] = EMPTY_STRING_TUPLE
    group_order: Tuple[str, ...] = EMPTY_STRING_TUPLE


@dataclass(frozen=True)
class TestRowSnapshot:
    """
    NAME
        TestRowSnapshot - Normalized REST tests-table row.
    """

    name: str = EMPTY_TEST_NAME
    selected: bool = BOOLEAN_FALSE
    enabled: bool = BOOLEAN_FALSE
    status: str = EMPTY_STATUS_NAME
    required_devices: Tuple[str, ...] = EMPTY_STRING_TUPLE
    exists_locally: bool = BOOLEAN_FALSE
    runnable_known: bool = BOOLEAN_FALSE
    runnable_now: bool = BOOLEAN_FALSE
    blocked_reason: str = EMPTY_STATUS_NAME


@dataclass(frozen=True)
class TestsRunSnapshot:
    """
    NAME
        TestsRunSnapshot - Normalized REST test-run summary.
    """

    run_id: int = 0
    state: str = EMPTY_STATUS_NAME
    test_name: str = EMPTY_TEST_NAME
    result: str = EMPTY_STATUS_NAME
    status: str = EMPTY_STATUS_NAME
    message: str = EMPTY_STATUS_NAME
    started_at_ms: float = ZERO_TIME_MS
    finished_at_ms: float = ZERO_TIME_MS


@dataclass(frozen=True)
class TestsSnapshot:
    """
    NAME
        TestsSnapshot - Normalized REST tests snapshot.
    """

    received_at_ms: float = ZERO_TIME_MS
    source_name: str = EMPTY_SOURCE_NAME
    generated_at_ms: float = ZERO_TIME_MS
    selected_name: str = EMPTY_TEST_NAME
    active_name: str = EMPTY_TEST_NAME
    active_status: str = EMPTY_STATUS_NAME
    run_all_active: bool = BOOLEAN_FALSE
    rows_by_name: Mapping[str, TestRowSnapshot] = field(default_factory=_empty_test_row_mapping)
    ordered_names: Tuple[str, ...] = EMPTY_STRING_TUPLE
    run: TestsRunSnapshot = field(default_factory=TestsRunSnapshot)


@dataclass(frozen=True)
class RestUiSnapshots:
    """
    NAME
        RestUiSnapshots - Aggregated typed REST snapshot bundle.
    """

    session: SessionSnapshot = field(default_factory=SessionSnapshot)
    runtime: RuntimeSnapshot = field(default_factory=RuntimeSnapshot)
    tests: TestsSnapshot = field(default_factory=TestsSnapshot)
