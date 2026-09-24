"""
NAME
    model.py - Immutable host telemetry domain records.

DESCRIPTION
    Represents catalog and sample meaning without REST dictionaries, Tk
    widgets, or persistence-library objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class SignalDescriptor:
    """Typed identity, unit, and display metadata for one signal."""

    signal_definition_key: str
    signal_id: str
    source_instance_id: str
    subject_key: str
    device_label: str
    signal_name: str
    value_kind: str
    unit: str
    unit_symbol: str
    engineering_dimension: str
    nominal_cadence_us: int
    stale_after_us: int
    graphable: bool


@dataclass(frozen=True)
class ClockDescriptor:
    """Identity and tick rate of one source monotonic clock."""

    clock_id: str
    kind: str
    ticks_per_second: int


@dataclass(frozen=True)
class TelemetryCatalog:
    """One source-generation snapshot of available signals."""

    schema_version: int
    history_generation_id: str
    source_instance_id: str
    revision: int
    clock: ClockDescriptor
    signals: Tuple[SignalDescriptor, ...]


@dataclass(frozen=True)
class TelemetrySample:
    """One source-timestamped numeric telemetry observation."""

    sequence: int
    signal_id: str
    source_timestamp_us: int
    numeric_value: float
    quality: str
    receive_timestamp_ns: int = 0
    receive_monotonic_ns: int = 0
    source_age_at_receive_us: int = 0
    gap_before: bool = False


@dataclass(frozen=True)
class TelemetryHistoryPage:
    """Cursor-addressed sample page returned by the robot."""

    schema_version: int
    history_generation_id: str
    source_instance_id: str
    oldest_sequence: int
    next_sequence: int
    has_more: bool
    cursor_expired: bool
    robot_reply_us: int
    records: Tuple[TelemetrySample, ...]


@dataclass(frozen=True)
class TelemetryCaptureStatus:
    """Operator-facing state of the robot-local WPILOG recorder."""

    ok: bool
    recording: bool
    path: str
    storage: str
    dropped_records: int
    last_stop_reason: str
    message: str
    auto_match_enabled: bool
    auto_exception_enabled: bool
